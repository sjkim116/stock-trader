"""Tests for StrategyRunner — strategy → runner → SafetyGuard → broker."""

from decimal import Decimal
from typing import List

import pytest

from app.strategies.base import BaseStrategy, Decision, StrategyContext
from app.strategies.market_history import StaticHistory
from app.strategies.runner import StrategyRegistration, StrategyRunner
from app.trading.limits import RiskLimits
from app.trading.market_data import FixedPriceSource
from app.trading.paper import PaperBroker, PaperBrokerConfig
from app.trading.safety import SafetyGuard
from app.trading.types import OrderSide


class _ScriptedStrategy(BaseStrategy):
    """Returns a pre-baked list of decisions, one per tick."""

    name = "scripted"

    def __init__(self, decisions: List[Decision | None]) -> None:
        self._decisions = list(decisions)
        self.observed_contexts: List[StrategyContext] = []

    def decide(self, ctx: StrategyContext):
        self.observed_contexts.append(ctx)
        if not self._decisions:
            return None
        return self._decisions.pop(0)


def _build():
    md = FixedPriceSource(prices={"005930": Decimal("100")})
    broker = PaperBroker(
        market_data=md,
        config=PaperBrokerConfig(
            starting_cash=Decimal("100000000"),
            slippage_bps=Decimal("0"),
            commission_rate=Decimal("0"),
            sell_tax_rate=Decimal("0"),
        ),
    )
    guard = SafetyGuard(broker=broker, market_data=md, limits=RiskLimits())
    history = StaticHistory(bars={"005930": [Decimal(str(i)) for i in range(50)]})
    runner = StrategyRunner(safety_guard=guard, history=history)
    return runner, broker, history


@pytest.mark.asyncio
async def test_tick_with_no_registrations_returns_empty_result():
    runner, _, _ = _build()
    result = await runner.tick()
    assert result.submitted == 0
    assert result.outcomes == []


@pytest.mark.asyncio
async def test_tick_passes_history_and_position_into_context():
    runner, _, history = _build()
    scripted = _ScriptedStrategy(decisions=[None])
    runner.register(
        StrategyRegistration(strategy=scripted, symbol="005930", history_length=10)
    )
    await runner.tick()
    assert len(scripted.observed_contexts) == 1
    ctx = scripted.observed_contexts[0]
    assert ctx.symbol == "005930"
    assert ctx.recent_prices == history.bars["005930"][-10:]
    assert ctx.current_price == ctx.recent_prices[-1]
    assert ctx.current_position is None  # broker is flat


@pytest.mark.asyncio
async def test_buy_decision_results_in_order_submitted():
    runner, broker, _ = _build()
    decision = Decision(side=OrderSide.BUY, quantity=Decimal("3"), reason="test buy")
    runner.register(
        StrategyRegistration(
            strategy=_ScriptedStrategy(decisions=[decision]),
            symbol="005930",
            history_length=5,
        )
    )
    result = await runner.tick()
    assert result.submitted == 1
    outcome = result.outcomes[0]
    assert outcome.decision is decision
    assert outcome.order is not None
    assert outcome.order.broker_order_id.startswith("PAPER-")
    # Broker reflects the fill.
    pos = await broker.get_position("005930")
    assert pos is not None
    assert pos.quantity == Decimal("3")


@pytest.mark.asyncio
async def test_safety_guard_rejection_lands_in_outcome_error():
    md = FixedPriceSource(prices={"005930": Decimal("100")})
    broker = PaperBroker(
        market_data=md,
        config=PaperBrokerConfig(
            starting_cash=Decimal("100000000"),
            slippage_bps=Decimal("0"),
            commission_rate=Decimal("0"),
            sell_tax_rate=Decimal("0"),
        ),
    )
    # Hard cap on order notional → any buy exceeding 100 KRW notional fails.
    guard = SafetyGuard(
        broker=broker,
        market_data=md,
        limits=RiskLimits(max_order_notional=Decimal("100")),
    )
    history = StaticHistory(bars={"005930": [Decimal("100")] * 10})
    runner = StrategyRunner(safety_guard=guard, history=history)
    runner.register(
        StrategyRegistration(
            strategy=_ScriptedStrategy(
                decisions=[
                    Decision(
                        side=OrderSide.BUY,
                        quantity=Decimal("10"),  # 100 * 10 = 1000 > cap 100
                        reason="exceeds cap",
                    )
                ]
            ),
            symbol="005930",
            history_length=5,
        )
    )
    result = await runner.tick()
    assert result.submitted == 0
    assert result.outcomes[0].order is None
    assert "order notional" in (result.outcomes[0].error or "")


@pytest.mark.asyncio
async def test_no_history_skips_strategy_without_error():
    md = FixedPriceSource(prices={})
    broker = PaperBroker(market_data=md)
    guard = SafetyGuard(broker=broker, market_data=md, limits=RiskLimits())
    history = StaticHistory(bars={})  # empty everywhere
    runner = StrategyRunner(safety_guard=guard, history=history)
    runner.register(
        StrategyRegistration(
            strategy=_ScriptedStrategy(
                decisions=[
                    Decision(side=OrderSide.BUY, quantity=Decimal("1"), reason="x")
                ]
            ),
            symbol="000660",
            history_length=10,
        )
    )
    result = await runner.tick()
    outcome = result.outcomes[0]
    assert outcome.order is None
    assert outcome.decision is None
    assert outcome.error is None  # silent skip, not a failure
