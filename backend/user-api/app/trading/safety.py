"""
SafetyGuard — wraps a Broker with pre-trade checks.

Strategies should always submit through SafetyGuard, never to a raw
broker. The guard:

  1. Refuses if the per-user KillSwitch is enabled.
  2. Refuses if any RiskLimit is violated.
  3. (Optional) Triggers the KillSwitch when daily_loss_limit is hit, so
     subsequent orders are blocked even if the strategy keeps trying.

Implementation note: the guard delegates *all* state (positions, P&L)
to the wrapped broker. It owns the gate but not the books. This keeps
PaperBroker and a future real-broker adapter swappable without
re-implementing limit math.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from app.trading.broker import Broker, OrderRejectedError
from app.trading.killswitch import KillSwitch
from app.trading.limits import LimitViolation, RiskLimits, check_limits
from app.trading.market_data import MarketDataSource, MissingPriceError
from app.trading.types import AccountInfo, Order, Position

logger = logging.getLogger(__name__)


class SafetyGuard:
    """Wraps a Broker and refuses orders that violate limits or run
    while the KillSwitch is engaged."""

    def __init__(
        self,
        broker: Broker,
        market_data: MarketDataSource,
        limits: RiskLimits,
        kill_switch: Optional[KillSwitch] = None,
        *,
        auto_trip_on_daily_loss: bool = True,
    ) -> None:
        self._broker = broker
        self._md = market_data
        self._limits = limits
        self._kill = kill_switch
        self._auto_trip_on_daily_loss = auto_trip_on_daily_loss

    async def submit_order(self, order: Order) -> Order:
        await self._check_kill_switch(order)
        await self._check_limits(order)
        try:
            result = await self._broker.submit_order(order)
        except OrderRejectedError:
            raise

        # After a successful fill, re-check daily P&L and trip the switch
        # if we've crossed the line. This is the belt-and-braces step:
        # the next order will be refused at the kill-switch gate above,
        # even if its own limit check would have passed.
        if (
            self._auto_trip_on_daily_loss
            and self._kill is not None
            and self._limits.daily_loss_limit is not None
            and order.user_id is not None
        ):
            account = await self._broker.get_account()
            if account.realized_pnl_today <= -self._limits.daily_loss_limit:
                await self._kill.trigger(
                    order.user_id,
                    reason=(
                        f"daily_loss_limit_hit: realized={account.realized_pnl_today} "
                        f"limit=-{self._limits.daily_loss_limit}"
                    ),
                )
                logger.warning(
                    "KillSwitch tripped for user_id=%s — daily loss limit reached",
                    order.user_id,
                )
        return result

    async def cancel_order(self, order_id: str) -> bool:
        return await self._broker.cancel_order(order_id)

    async def get_position(self, symbol: str) -> Optional[Position]:
        return await self._broker.get_position(symbol)

    async def get_positions(self) -> List[Position]:
        return await self._broker.get_positions()

    async def get_account(self) -> AccountInfo:
        return await self._broker.get_account()

    # ------------------------------------------------------------- checks
    async def _check_kill_switch(self, order: Order) -> None:
        if self._kill is None or order.user_id is None:
            return
        if await self._kill.is_enabled(order.user_id):
            raise OrderRejectedError(order, "kill switch is engaged")

    async def _check_limits(self, order: Order) -> None:
        try:
            price = await self._md.get_price(order.symbol)
        except MissingPriceError as exc:
            raise OrderRejectedError(order, str(exc)) from exc

        positions = await self._broker.get_positions()
        account = await self._broker.get_account()

        violations: List[LimitViolation] = check_limits(
            order,
            limits=self._limits,
            positions=positions,
            realized_pnl_today=account.realized_pnl_today,
            fill_price_estimate=price,
        )
        if violations:
            reason = "; ".join(v.message for v in violations)
            raise OrderRejectedError(order, reason)
