"""
Moving Average Crossover — the canonical demo strategy.

Logic (long-only, intraday-friendly):

* BUY when short MA crosses above long MA from below AND we're flat.
* SELL when short MA crosses below long MA from above AND we're long.

A crossover is detected by comparing the previous and current
short-vs-long relation, so a strategy that's already long doesn't fire
a second BUY just because the gap widened. ``last_signal`` is the
in-memory de-dup.

These are textbook MA mechanics — the bigger point of having this
implementation in the codebase is to exercise the Strategy → Runner →
SafetyGuard → PaperBroker pipeline end to end. Profitability claims
about this strategy are not made anywhere; see the project's "real
expectations" notes.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from app.strategies.base import BaseStrategy, Decision, StrategyContext
from app.trading.types import OrderSide


@dataclass(frozen=True)
class MACrossoverParams:
    short_period: int = 5
    long_period: int = 20
    position_size: Decimal = Decimal("10")  # shares per signal

    def __post_init__(self):
        if self.short_period <= 0 or self.long_period <= 0:
            raise ValueError("MA periods must be positive")
        if self.short_period >= self.long_period:
            raise ValueError("short_period must be less than long_period")
        if self.position_size <= 0:
            raise ValueError("position_size must be positive")


def _mean(values: List[Decimal]) -> Decimal:
    return sum(values, start=Decimal("0")) / Decimal(len(values))


class MACrossoverStrategy(BaseStrategy):
    name = "ma_crossover"

    def __init__(self, params: Optional[MACrossoverParams] = None) -> None:
        self.params = params or MACrossoverParams()
        # Sign of (short_ma - long_ma) on the previous tick. None means
        # "not initialised yet" — first observed sign just primes the
        # detector, doesn't fire a signal.
        self._prev_sign: Optional[int] = None

    def decide(self, ctx: StrategyContext) -> Optional[Decision]:
        p = self.params
        # Need enough history to compute the long MA, plus one extra
        # bar to detect a crossover vs the prior state.
        if len(ctx.recent_prices) < p.long_period:
            return None

        short_ma = _mean(ctx.recent_prices[-p.short_period :])
        long_ma = _mean(ctx.recent_prices[-p.long_period :])
        cur_sign = 1 if short_ma > long_ma else (-1 if short_ma < long_ma else 0)

        prev = self._prev_sign
        self._prev_sign = cur_sign

        if prev is None or cur_sign == 0:
            return None  # priming tick / no clear direction
        if cur_sign == prev:
            return None  # no crossover this tick

        # Golden cross: short MA crossed above long MA → buy if flat.
        if prev < 0 and cur_sign > 0:
            if ctx.current_position is not None and ctx.current_position.quantity > 0:
                return None  # already long, don't pyramid here
            return Decision(
                side=OrderSide.BUY,
                quantity=p.position_size,
                reason=(
                    f"golden cross: short_ma={short_ma:.2f} > long_ma={long_ma:.2f}"
                ),
            )

        # Death cross: short crossed below long → sell if holding.
        if prev > 0 and cur_sign < 0:
            if ctx.current_position is None or ctx.current_position.quantity <= 0:
                return None  # nothing to sell, shorts disabled in paper
            qty = min(p.position_size, ctx.current_position.quantity)
            return Decision(
                side=OrderSide.SELL,
                quantity=qty,
                reason=(
                    f"death cross: short_ma={short_ma:.2f} < long_ma={long_ma:.2f}"
                ),
            )

        return None
