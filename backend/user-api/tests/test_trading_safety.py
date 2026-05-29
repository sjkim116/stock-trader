"""Tests for the SafetyGuard + RiskLimits combination."""

from decimal import Decimal
from uuid import uuid4

import pytest

from app.trading.broker import OrderRejectedError
from app.trading.killswitch import KillSwitch
from app.trading.limits import RiskLimits
from app.trading.market_data import FixedPriceSource
from app.trading.paper import PaperBroker, PaperBrokerConfig
from app.trading.safety import SafetyGuard
from app.trading.types import Order, OrderSide, OrderType


def _md(price=Decimal("70000")) -> FixedPriceSource:
    return FixedPriceSource(prices={"005930": price})


def _broker(md=None) -> PaperBroker:
    return PaperBroker(
        market_data=md or _md(),
        config=PaperBrokerConfig(
            starting_cash=Decimal("100000000"),
            slippage_bps=Decimal("0"),
            commission_rate=Decimal("0"),
            sell_tax_rate=Decimal("0"),
        ),
    )


def _buy(qty="10", user_id=None) -> Order:
    return Order(
        symbol="005930",
        side=OrderSide.BUY,
        quantity=Decimal(qty),
        order_type=OrderType.MARKET,
        user_id=user_id,
    )


@pytest.mark.asyncio
async def test_passes_through_when_no_limits_violated():
    md = _md()
    guard = SafetyGuard(
        broker=_broker(md),
        market_data=md,
        limits=RiskLimits(),
    )
    result = await guard.submit_order(_buy(qty="1"))
    assert result.broker_order_id is not None


@pytest.mark.asyncio
async def test_rejects_when_order_notional_exceeds_cap():
    md = _md(Decimal("70000"))
    guard = SafetyGuard(
        broker=_broker(md),
        market_data=md,
        limits=RiskLimits(max_order_notional=Decimal("100000")),
    )
    # 70,000 * 10 = 700,000 > 100,000 cap
    with pytest.raises(OrderRejectedError, match="order notional"):
        await guard.submit_order(_buy(qty="10"))


@pytest.mark.asyncio
async def test_rejects_when_post_trade_position_exceeds_max():
    md = _md(Decimal("70000"))
    guard = SafetyGuard(
        broker=_broker(md),
        market_data=md,
        limits=RiskLimits(max_position_size=Decimal("500000")),
    )
    # 70,000 * 10 = 700,000 post-trade notional > 500,000 cap
    with pytest.raises(OrderRejectedError, match="max_position_size"):
        await guard.submit_order(_buy(qty="10"))


@pytest.mark.asyncio
async def test_rejects_when_max_positions_reached():
    md = FixedPriceSource(
        prices={"005930": Decimal("70000"), "000660": Decimal("130000")}
    )
    broker = _broker(md)
    guard = SafetyGuard(
        broker=broker,
        market_data=md,
        limits=RiskLimits(max_positions=1),
    )
    # First buy is allowed.
    await guard.submit_order(
        Order(
            symbol="005930",
            side=OrderSide.BUY,
            quantity=Decimal("1"),
            order_type=OrderType.MARKET,
        )
    )
    # Second buy on a new symbol exceeds max_positions=1.
    with pytest.raises(OrderRejectedError, match="max 1"):
        await guard.submit_order(
            Order(
                symbol="000660",
                side=OrderSide.BUY,
                quantity=Decimal("1"),
                order_type=OrderType.MARKET,
            )
        )


@pytest.mark.asyncio
async def test_rejects_symbol_not_in_whitelist():
    md = FixedPriceSource(prices={"000660": Decimal("130000")})
    guard = SafetyGuard(
        broker=_broker(md),
        market_data=md,
        limits=RiskLimits(allowed_symbols=frozenset({"005930"})),
    )
    with pytest.raises(
        OrderRejectedError, match="not in the strategy's allowed_symbols"
    ):
        await guard.submit_order(
            Order(
                symbol="000660",
                side=OrderSide.BUY,
                quantity=Decimal("1"),
                order_type=OrderType.MARKET,
            )
        )


class _FakeKillSwitch:
    """In-memory KillSwitch substitute — same shape as the real one but
    no DB. Lets us test SafetyGuard's gate logic in isolation."""

    def __init__(self) -> None:
        self._enabled: dict = {}

    async def is_enabled(self, user_id) -> bool:
        return self._enabled.get(user_id, False)

    async def trigger(self, user_id, *, reason: str) -> None:
        self._enabled[user_id] = True

    async def reset(self, user_id) -> None:
        self._enabled[user_id] = False


@pytest.mark.asyncio
async def test_kill_switch_blocks_all_orders():
    md = _md()
    kill = _FakeKillSwitch()
    user = uuid4()
    await kill.trigger(user, reason="manual stop for testing")

    guard = SafetyGuard(
        broker=_broker(md),
        market_data=md,
        limits=RiskLimits(),
        kill_switch=kill,
    )
    with pytest.raises(OrderRejectedError, match="kill switch is engaged"):
        await guard.submit_order(_buy(qty="1", user_id=user))


@pytest.mark.asyncio
async def test_kill_switch_only_affects_target_user():
    md = _md()
    kill = _FakeKillSwitch()
    user_a, user_b = uuid4(), uuid4()
    await kill.trigger(user_a, reason="just user_a")

    guard = SafetyGuard(
        broker=_broker(md),
        market_data=md,
        limits=RiskLimits(),
        kill_switch=kill,
    )
    with pytest.raises(OrderRejectedError):
        await guard.submit_order(_buy(qty="1", user_id=user_a))

    # user_b's order goes through.
    ok = await guard.submit_order(_buy(qty="1", user_id=user_b))
    assert ok.broker_order_id is not None
