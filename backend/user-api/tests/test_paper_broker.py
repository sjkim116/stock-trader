"""Unit tests for PaperBroker — all in-memory, no DB required."""

from decimal import Decimal

import pytest

from app.trading.broker import OrderRejectedError
from app.trading.market_data import FixedPriceSource
from app.trading.paper import PaperBroker, PaperBrokerConfig
from app.trading.types import Order, OrderSide, OrderStatus, OrderType


def _md(prices=None) -> FixedPriceSource:
    return FixedPriceSource(prices=dict(prices or {"005930": Decimal("70000")}))


def _buy(symbol="005930", qty="10") -> Order:
    return Order(
        symbol=symbol,
        side=OrderSide.BUY,
        quantity=Decimal(qty),
        order_type=OrderType.MARKET,
    )


def _sell(symbol="005930", qty="10") -> Order:
    return Order(
        symbol=symbol,
        side=OrderSide.SELL,
        quantity=Decimal(qty),
        order_type=OrderType.MARKET,
    )


@pytest.mark.asyncio
async def test_buy_then_sell_round_trip_settles_pnl():
    md = _md({"005930": Decimal("70000")})
    broker = PaperBroker(
        market_data=md,
        config=PaperBrokerConfig(
            starting_cash=Decimal("10000000"),
            slippage_bps=Decimal("0"),
            commission_rate=Decimal("0"),
            sell_tax_rate=Decimal("0"),
        ),
    )

    buy = await broker.submit_order(_buy(qty="10"))
    assert buy.status == OrderStatus.FILLED
    assert broker.cash == Decimal("10000000") - Decimal("700000")

    md.set_price("005930", Decimal("75000"))
    sell = await broker.submit_order(_sell(qty="10"))
    assert sell.status == OrderStatus.FILLED
    # 5,000 * 10 = 50,000 KRW realized PnL, no costs in this config
    assert broker.realized_pnl_today == Decimal("50000")
    # position closed
    assert await broker.get_position("005930") is None


@pytest.mark.asyncio
async def test_slippage_widens_fill_against_trader():
    md = _md({"005930": Decimal("70000")})
    broker = PaperBroker(
        market_data=md,
        config=PaperBrokerConfig(
            starting_cash=Decimal("10000000"),
            slippage_bps=Decimal("10"),  # 0.1%
            commission_rate=Decimal("0"),
            sell_tax_rate=Decimal("0"),
        ),
    )
    await broker.submit_order(_buy(qty="1"))
    fill = broker.fills[0]
    # Buy fills 10 bp above the mark: 70000 * 1.001 = 70070
    assert fill.price == Decimal("70070.000")


@pytest.mark.asyncio
async def test_buy_rejected_when_cash_insufficient():
    broker = PaperBroker(
        market_data=_md({"005930": Decimal("70000")}),
        config=PaperBrokerConfig(
            starting_cash=Decimal("100"), slippage_bps=Decimal("0")
        ),
    )
    with pytest.raises(OrderRejectedError, match="insufficient cash"):
        await broker.submit_order(_buy(qty="10"))


@pytest.mark.asyncio
async def test_sell_without_position_is_rejected_no_shorts():
    broker = PaperBroker(market_data=_md())
    with pytest.raises(OrderRejectedError, match="insufficient position"):
        await broker.submit_order(_sell(qty="1"))


@pytest.mark.asyncio
async def test_missing_price_rejects_order():
    broker = PaperBroker(market_data=FixedPriceSource(prices={}))
    with pytest.raises(OrderRejectedError, match="no recent price"):
        await broker.submit_order(_buy(qty="1"))


@pytest.mark.asyncio
async def test_limit_order_is_rejected_in_paper_mode():
    broker = PaperBroker(market_data=_md())
    limit_order = Order(
        symbol="005930",
        side=OrderSide.BUY,
        quantity=Decimal("1"),
        order_type=OrderType.LIMIT,
        price=Decimal("60000"),
    )
    with pytest.raises(OrderRejectedError, match="only supports MARKET"):
        await broker.submit_order(limit_order)


@pytest.mark.asyncio
async def test_pyramiding_keeps_weighted_avg_price():
    md = _md({"005930": Decimal("70000")})
    broker = PaperBroker(
        market_data=md,
        config=PaperBrokerConfig(
            starting_cash=Decimal("10000000"),
            slippage_bps=Decimal("0"),
            commission_rate=Decimal("0"),
            sell_tax_rate=Decimal("0"),
        ),
    )
    await broker.submit_order(_buy(qty="10"))  # 10 @ 70,000
    md.set_price("005930", Decimal("80000"))
    await broker.submit_order(_buy(qty="10"))  # 10 @ 80,000
    pos = await broker.get_position("005930")
    assert pos is not None
    assert pos.quantity == Decimal("20")
    # Weighted avg: (70000*10 + 80000*10) / 20 = 75,000
    assert pos.avg_entry_price == Decimal("75000")
