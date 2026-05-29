"""
StrategyRunner — single-tick driver for registered strategies.

The runner threads everything together:

  for each (strategy, symbol) registration:
    1. Load recent closes from market history.
    2. Build a StrategyContext (history + position + cash).
    3. strategy.decide(ctx) → Optional[Decision].
    4. If a Decision came back, submit through SafetyGuard.

Each strategy's exceptions are caught and logged so one broken
strategy doesn't take the whole tick down. A scheduled loop wrapper
(asyncio.sleep + tick) lives in a follow-up PR — for now ``tick`` is
called manually via the HTTP endpoint.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional
from uuid import UUID

from app.strategies.base import BaseStrategy, Decision, StrategyContext
from app.strategies.market_history import HistorySource
from app.trading.broker import OrderRejectedError
from app.trading.safety import SafetyGuard
from app.trading.types import Order, OrderType

logger = logging.getLogger(__name__)


@dataclass
class StrategyRegistration:
    """One strategy bound to one symbol. Multi-symbol traders register
    one entry per symbol so per-symbol state stays scoped to the
    instance."""

    strategy: BaseStrategy
    symbol: str
    interval: str = "1m"
    history_length: int = 60  # bars pulled per tick; ≥ longest MA window


@dataclass
class TickOutcome:
    """What happened to one strategy on one tick. Successful and failed
    decisions are both recorded — the HTTP endpoint surfaces both for
    debugging."""

    strategy_name: str
    symbol: str
    decision: Optional[Decision] = None
    order: Optional[Order] = None
    error: Optional[str] = None


@dataclass
class TickResult:
    """Summary of all strategies ticked at once. ``submitted`` is the
    count of orders that made it past SafetyGuard."""

    outcomes: List[TickOutcome] = field(default_factory=list)
    submitted: int = 0


class StrategyRunner:
    def __init__(
        self,
        safety_guard: SafetyGuard,
        history: HistorySource,
    ) -> None:
        self._guard = safety_guard
        self._history = history
        self._registrations: List[StrategyRegistration] = []

    def register(self, registration: StrategyRegistration) -> None:
        self._registrations.append(registration)
        logger.info(
            "Registered strategy=%s symbol=%s interval=%s",
            registration.strategy.name,
            registration.symbol,
            registration.interval,
        )

    @property
    def registrations(self) -> List[StrategyRegistration]:
        return list(self._registrations)

    async def tick(self, *, user_id: Optional[UUID] = None) -> TickResult:
        result = TickResult()
        for reg in self._registrations:
            outcome = await self._tick_one(reg, user_id=user_id)
            result.outcomes.append(outcome)
            if outcome.order is not None:
                result.submitted += 1
        return result

    async def _tick_one(
        self, reg: StrategyRegistration, *, user_id: Optional[UUID]
    ) -> TickOutcome:
        outcome = TickOutcome(strategy_name=reg.strategy.name, symbol=reg.symbol)
        try:
            closes = await self._history.recent_closes(
                reg.symbol, reg.interval, reg.history_length
            )
            if not closes:
                # No data yet — silently skip.
                return outcome
            current_price = closes[-1]
            position = await self._guard.get_position(reg.symbol)
            account = await self._guard.get_account()

            ctx = StrategyContext(
                symbol=reg.symbol,
                current_price=current_price,
                recent_prices=closes,
                cash=account.cash,
                current_position=position,
                user_id=user_id,
            )

            decision = reg.strategy.decide(ctx)
            outcome.decision = decision
            if decision is None:
                return outcome

            order = Order(
                symbol=reg.symbol,
                side=decision.side,
                quantity=decision.quantity,
                order_type=OrderType.MARKET,
                user_id=user_id,
            )
            try:
                filled = await self._guard.submit_order(order)
                outcome.order = filled
                logger.info(
                    "strategy=%s symbol=%s decided=%s qty=%s reason=%s",
                    reg.strategy.name,
                    reg.symbol,
                    decision.side.value,
                    decision.quantity,
                    decision.reason,
                )
            except OrderRejectedError as exc:
                outcome.error = exc.reason
                logger.warning(
                    "strategy=%s symbol=%s decision_rejected=%s reason=%s",
                    reg.strategy.name,
                    reg.symbol,
                    decision.side.value,
                    exc.reason,
                )
        except Exception as exc:  # noqa: BLE001 — one strategy mustn't kill the tick
            outcome.error = f"unexpected: {exc!r}"
            logger.exception(
                "strategy=%s symbol=%s crashed during tick",
                reg.strategy.name,
                reg.symbol,
            )
        return outcome

    # Pure helper — exposed for tests that want to drive a synthetic
    # context without going through HistorySource.
    async def submit_decision(
        self,
        symbol: str,
        decision: Decision,
        *,
        user_id: Optional[UUID] = None,
    ) -> Optional[Order]:
        order = Order(
            symbol=symbol,
            side=decision.side,
            quantity=decision.quantity,
            order_type=OrderType.MARKET,
            user_id=user_id,
        )
        try:
            return await self._guard.submit_order(order)
        except OrderRejectedError as exc:
            logger.warning("submit_decision rejected: %s", exc.reason)
            return None


__all__ = [
    "StrategyRegistration",
    "StrategyRunner",
    "TickOutcome",
    "TickResult",
]
