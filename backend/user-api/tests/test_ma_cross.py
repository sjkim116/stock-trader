"""Unit tests for MovingAverageCrossover — pure decision logic, no DB."""

from decimal import Decimal

import pytest

from app.strategies.base import StrategyContext
from app.strategies.ma_cross import MACrossoverParams, MACrossoverStrategy
from app.trading.types import OrderSide, Position


def _ctx(prices, position=None, cash="1000000") -> StrategyContext:
    return StrategyContext(
        symbol="005930",
        current_price=Decimal(str(prices[-1])) if prices else Decimal("0"),
        recent_prices=[Decimal(str(p)) for p in prices],
        cash=Decimal(cash),
        current_position=position,
    )


def _long_pos(qty="10", avg="100") -> Position:
    return Position(
        symbol="005930",
        quantity=Decimal(qty),
        avg_entry_price=Decimal(avg),
    )


def test_no_signal_before_long_period_filled():
    strat = MACrossoverStrategy(MACrossoverParams(short_period=2, long_period=4))
    # Only 3 prices — long window is 4, so no signal possible yet.
    assert strat.decide(_ctx([10, 10, 10])) is None


def test_priming_tick_returns_no_signal():
    strat = MACrossoverStrategy(MACrossoverParams(short_period=2, long_period=4))
    # First tick with enough history just establishes the sign — no
    # crossover yet because there's nothing to cross from.
    assert strat.decide(_ctx([10, 11, 12, 13])) is None


def test_golden_cross_fires_buy_when_flat():
    strat = MACrossoverStrategy(
        MACrossoverParams(short_period=2, long_period=4, position_size=Decimal("5"))
    )
    # Establish a downward state first (short < long).
    assert strat.decide(_ctx([20, 19, 18, 17])) is None  # priming
    # Now flip: latest prices push short MA above long MA.
    decision = strat.decide(_ctx([20, 19, 25, 30]))
    assert decision is not None
    assert decision.side == OrderSide.BUY
    assert decision.quantity == Decimal("5")
    assert "golden cross" in decision.reason


def test_death_cross_fires_sell_when_long():
    strat = MACrossoverStrategy(
        MACrossoverParams(short_period=2, long_period=4, position_size=Decimal("5"))
    )
    # Prime in an upward state.
    assert strat.decide(_ctx([10, 12, 14, 16])) is None
    # Flip downward; we're holding 5 shares so a SELL should fire.
    decision = strat.decide(_ctx([10, 12, 8, 6], position=_long_pos(qty="5", avg="12")))
    assert decision is not None
    assert decision.side == OrderSide.SELL
    assert decision.quantity == Decimal("5")
    assert "death cross" in decision.reason


def test_golden_cross_does_not_fire_when_already_long():
    strat = MACrossoverStrategy(MACrossoverParams(short_period=2, long_period=4))
    strat.decide(_ctx([20, 19, 18, 17]))  # priming (down)
    # Crossover up, but we're already holding — strategy refuses to pyramid here.
    decision = strat.decide(
        _ctx([20, 19, 25, 30], position=_long_pos(qty="10", avg="20"))
    )
    assert decision is None


def test_death_cross_does_not_fire_when_flat():
    strat = MACrossoverStrategy(MACrossoverParams(short_period=2, long_period=4))
    strat.decide(_ctx([10, 12, 14, 16]))  # priming (up)
    decision = strat.decide(_ctx([10, 12, 8, 6]))  # no position
    # Shorts disabled in paper — nothing to sell.
    assert decision is None


def test_no_repeat_signal_while_state_unchanged():
    strat = MACrossoverStrategy(MACrossoverParams(short_period=2, long_period=4))
    strat.decide(_ctx([20, 19, 18, 17]))  # priming (down)
    first = strat.decide(_ctx([20, 19, 25, 30]))  # golden cross
    assert first is not None and first.side == OrderSide.BUY
    # Same up state on the next tick — no fresh crossover.
    second = strat.decide(_ctx([19, 25, 30, 35], position=_long_pos(qty="10")))
    assert second is None


def test_invalid_params_raise_at_construction():
    with pytest.raises(ValueError):
        MACrossoverParams(short_period=0, long_period=10)
    with pytest.raises(ValueError):
        MACrossoverParams(short_period=10, long_period=5)
    with pytest.raises(ValueError):
        MACrossoverParams(position_size=Decimal("0"))
