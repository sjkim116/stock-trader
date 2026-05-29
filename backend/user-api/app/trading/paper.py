"""
PaperBroker — in-memory paper-trading execution.

Fills are simulated against MarketDataSource.get_price(symbol) with
configurable slippage and commission. State (cash, positions, fills)
lives in the broker instance — strategies that need it across restarts
will persist trades through the OLTP schema in a later PR.

Intentionally conservative:
* No shorts (sell with no position raises OrderRejectedError)
* No partial fills — every order is filled in full or rejected
* No latency simulation — fills are synchronous

These limits exist so the paper broker can't accidentally model a more
favourable environment than reality.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from app.trading.broker import OrderRejectedError
from app.trading.market_data import MarketDataSource, MissingPriceError
from app.trading.paper_repo import PaperAccountState, PaperRepo
from app.trading.types import (
    AccountInfo,
    Fill,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
)

logger = logging.getLogger(__name__)


@dataclass
class PaperBrokerConfig:
    starting_cash: Decimal = Decimal("10000000")  # 10M KRW default
    slippage_bps: Decimal = Decimal("5")  # 5 bp = 0.05% adverse fill
    commission_rate: Decimal = Decimal("0.00015")  # 0.015% (KIS-ish)
    sell_tax_rate: Decimal = Decimal("0.0018")  # KOSPI sell tax 0.18%


class PaperBroker:
    """Simulated execution against a MarketDataSource.

    All methods are async to match the Broker Protocol. Internal state
    is guarded by an asyncio.Lock so concurrent strategies running in
    the same event loop can't race on position updates.
    """

    def __init__(
        self,
        market_data: MarketDataSource,
        config: Optional[PaperBrokerConfig] = None,
        *,
        repo: Optional[PaperRepo] = None,
        user_id: Optional[UUID] = None,
    ) -> None:
        # repo + user_id are paired — one without the other is a misconfig.
        if (repo is None) != (user_id is None):
            raise ValueError("repo and user_id must be set together (or both None)")
        self._md = market_data
        self._cfg = config or PaperBrokerConfig()
        self._cash: Decimal = self._cfg.starting_cash
        self._positions: Dict[str, Position] = {}
        self._fills: List[Fill] = []
        self._realized_pnl_today: Decimal = Decimal("0")
        self._lock = asyncio.Lock()
        self._broker_seq = 0
        self._repo: Optional[PaperRepo] = repo
        self._user_id: Optional[UUID] = user_id

    async def load_from_db(self) -> None:
        """Restore cash + positions from the repository. Idempotent — if
        no row exists for the user (first-ever run) we keep the
        starting_cash from config so the next fill writes a fresh row."""
        if self._repo is None or self._user_id is None:
            return
        async with self._lock:
            state = await self._repo.load_state(self._user_id)
            if state.account is not None:
                self._cash = state.account.cash
                self._realized_pnl_today = state.account.realized_pnl_today
                logger.info(
                    "Restored paper account for user_id=%s: cash=%s pnl_today=%s",
                    self._user_id,
                    self._cash,
                    self._realized_pnl_today,
                )
            self._positions = dict(state.positions)
            logger.info(
                "Restored %d position(s) for user_id=%s",
                len(self._positions),
                self._user_id,
            )

    # ---------------------------------------------------------------- Broker
    async def submit_order(self, order: Order) -> Order:
        async with self._lock:
            return await self._submit_locked(order)

    async def _submit_locked(self, order: Order) -> Order:
        if order.order_type != OrderType.MARKET:
            # Limit/stop simulation needs a real tick stream — out of scope
            # for this PR. Strategies should send MARKET in the paper layer
            # and translate to limit at the real-broker adapter level.
            raise OrderRejectedError(order, "paper broker only supports MARKET orders")

        if order.quantity <= 0:
            raise OrderRejectedError(order, "quantity must be positive")

        try:
            mark = await self._md.get_price(order.symbol)
        except MissingPriceError as exc:
            raise OrderRejectedError(order, str(exc)) from exc

        fill_price = self._apply_slippage(mark, order.side)
        notional = fill_price * order.quantity
        commission = (notional * self._cfg.commission_rate).quantize(Decimal("0.01"))
        sell_tax = (
            (notional * self._cfg.sell_tax_rate).quantize(Decimal("0.01"))
            if order.side == OrderSide.SELL
            else Decimal("0")
        )

        if order.side == OrderSide.BUY:
            total_cost = notional + commission
            if total_cost > self._cash:
                raise OrderRejectedError(
                    order,
                    f"insufficient cash: need {total_cost}, have {self._cash}",
                )
            self._cash -= total_cost
            self._apply_buy(order.symbol, order.quantity, fill_price, order.user_id)
        else:
            position = self._positions.get(order.symbol)
            if position is None or position.quantity < order.quantity:
                have = Decimal("0") if position is None else position.quantity
                raise OrderRejectedError(
                    order,
                    (
                        f"insufficient position to sell: need {order.quantity}, "
                        f"have {have} (shorts disabled)"
                    ),
                )
            proceeds = notional - commission - sell_tax
            realized = self._apply_sell(order.symbol, order.quantity, fill_price)
            self._cash += proceeds
            self._realized_pnl_today += realized - commission - sell_tax

        self._broker_seq += 1
        order.broker_order_id = f"PAPER-{self._broker_seq:08d}"
        order.status = OrderStatus.FILLED
        order.submitted_at = order.created_at

        fill = Fill(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=fill_price,
            commission=commission + sell_tax,
        )
        self._fills.append(fill)

        if self._repo is not None and self._user_id is not None:
            # Write-through after the in-memory mutation succeeded so the
            # DB always reflects the broker's truth. If the DB write
            # fails the in-memory state is still consistent — the next
            # restart will see the older snapshot until catch-up logic
            # is added (out of scope for this PR).
            await self._repo.persist_fill(
                user_id=self._user_id,
                fill=fill,
                broker_order_id=order.broker_order_id,
                account_after=PaperAccountState(
                    cash=self._cash,
                    realized_pnl_today=self._realized_pnl_today,
                ),
                position_after=self._positions.get(order.symbol),
            )

        return order

    async def cancel_order(self, order_id: str) -> bool:
        # Paper fills are synchronous → nothing to cancel. Returning True
        # keeps cancellation idempotent for callers that retry on timeout.
        return True

    async def get_position(self, symbol: str) -> Optional[Position]:
        async with self._lock:
            pos = self._positions.get(symbol)
            return None if pos is None or pos.is_flat else pos

    async def get_positions(self) -> List[Position]:
        async with self._lock:
            return [p for p in self._positions.values() if not p.is_flat]

    async def get_account(self) -> AccountInfo:
        async with self._lock:
            unrealized = Decimal("0")
            equity = self._cash
            for pos in self._positions.values():
                if pos.is_flat:
                    continue
                try:
                    mark = await self._md.get_price(pos.symbol)
                    market_value = mark * pos.quantity
                    unrealized += (mark - pos.avg_entry_price) * pos.quantity
                    equity += market_value
                except MissingPriceError:
                    # Stale price — fall back to entry, conservative for risk.
                    equity += pos.notional
            return AccountInfo(
                cash=self._cash,
                equity=equity,
                realized_pnl_today=self._realized_pnl_today,
                unrealized_pnl=unrealized,
            )

    # ----------------------------------------------- helpers (sync, locked)
    def _apply_slippage(self, mark: Decimal, side: OrderSide) -> Decimal:
        bps = self._cfg.slippage_bps / Decimal("10000")
        return (
            (mark * (Decimal("1") + bps))
            if side == OrderSide.BUY
            else (mark * (Decimal("1") - bps))
        )

    def _apply_buy(
        self,
        symbol: str,
        qty: Decimal,
        price: Decimal,
        user_id,
    ) -> None:
        existing = self._positions.get(symbol)
        if existing is None or existing.is_flat:
            self._positions[symbol] = Position(
                symbol=symbol,
                quantity=qty,
                avg_entry_price=price,
                user_id=user_id,
            )
            return
        new_qty = existing.quantity + qty
        # Weighted average entry — keeps avg_entry_price accurate across pyramiding.
        new_avg = (
            (existing.avg_entry_price * existing.quantity) + (price * qty)
        ) / new_qty
        existing.quantity = new_qty
        existing.avg_entry_price = new_avg

    def _apply_sell(self, symbol: str, qty: Decimal, price: Decimal) -> Decimal:
        """Reduces the long position by qty. Returns realized PnL on the
        sold portion (gross of commission/tax — those are subtracted by
        the caller)."""
        existing = self._positions[symbol]
        realized = (price - existing.avg_entry_price) * qty
        existing.quantity -= qty
        existing.realized_pnl += realized
        if existing.is_flat:
            # Keep avg_entry_price for reference; quantity == 0 marks closed.
            existing.quantity = Decimal("0")
        return realized

    # -------------------------------------------------------------- testing
    @property
    def cash(self) -> Decimal:
        return self._cash

    @property
    def fills(self) -> List[Fill]:
        return list(self._fills)

    @property
    def realized_pnl_today(self) -> Decimal:
        return self._realized_pnl_today
