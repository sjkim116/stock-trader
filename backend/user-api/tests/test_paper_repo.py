"""Integration tests for PaperRepository + PaperBroker persistence.

Uses the ``engines`` fixture from conftest.py — short-lived sessions
against the real OLTP postgres (docker-compose locally, service
container in CI).

Each test seeds a fresh users row so the FK from paper_account /
paper_position / paper_fill resolves, then cleans up on the way out.
"""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from app.trading.market_data import FixedPriceSource
from app.trading.paper import PaperBroker, PaperBrokerConfig
from app.trading.paper_repo import PaperRepository
from app.trading.types import Order, OrderSide, OrderType


async def _insert_user(session, user_id: UUID) -> None:
    await session.execute(
        text(
            "INSERT INTO users (user_id, email, password_hash) "
            "VALUES (:uid, :em, 'x') ON CONFLICT DO NOTHING"
        ),
        {"uid": str(user_id), "em": f"paper-{user_id}@test.local"},
    )
    await session.commit()


async def _delete_user(session, user_id: UUID) -> None:
    # paper_* rows cascade via ON DELETE CASCADE so deleting the user
    # is enough cleanup.
    await session.execute(
        text("DELETE FROM users WHERE user_id = :uid"), {"uid": str(user_id)}
    )
    await session.commit()


def _md() -> FixedPriceSource:
    return FixedPriceSource(prices={"005930": Decimal("70000")})


def _broker(repo: PaperRepository, user_id: UUID) -> PaperBroker:
    return PaperBroker(
        market_data=_md(),
        config=PaperBrokerConfig(
            starting_cash=Decimal("10000000"),
            slippage_bps=Decimal("0"),
            commission_rate=Decimal("0"),
            sell_tax_rate=Decimal("0"),
        ),
        repo=repo,
        user_id=user_id,
    )


@pytest.mark.asyncio
async def test_load_state_returns_empty_for_unknown_user(engines):
    user_id = uuid4()
    async with engines.OltpSession() as s:
        await _insert_user(s, user_id)
    try:
        repo = PaperRepository(engines.OltpSession)
        state = await repo.load_state(user_id)
        assert state.account is None
        assert state.positions == {}
    finally:
        async with engines.OltpSession() as s:
            await _delete_user(s, user_id)


@pytest.mark.asyncio
async def test_persist_fill_creates_account_position_and_fill_rows(engines):
    user_id = uuid4()
    async with engines.OltpSession() as s:
        await _insert_user(s, user_id)
    try:
        repo = PaperRepository(engines.OltpSession)
        broker = _broker(repo, user_id)
        await broker.submit_order(
            Order(
                symbol="005930",
                side=OrderSide.BUY,
                quantity=Decimal("10"),
                order_type=OrderType.MARKET,
            )
        )
        # Read directly to verify the row layout, not just the in-memory state.
        async with engines.OltpSession() as s:
            acct = (
                await s.execute(
                    text("SELECT cash FROM paper_account WHERE user_id = :uid"),
                    {"uid": str(user_id)},
                )
            ).first()
            pos = (
                await s.execute(
                    text(
                        "SELECT quantity, avg_entry_price FROM paper_position "
                        "WHERE user_id = :uid AND symbol = '005930'"
                    ),
                    {"uid": str(user_id)},
                )
            ).first()
            fills = (
                await s.execute(
                    text("SELECT count(*) AS n FROM paper_fill WHERE user_id = :uid"),
                    {"uid": str(user_id)},
                )
            ).first()
        assert acct is not None
        assert Decimal(str(acct.cash)) == Decimal("9300000")
        assert pos is not None
        assert Decimal(str(pos.quantity)) == Decimal("10")
        assert Decimal(str(pos.avg_entry_price)) == Decimal("70000")
        assert fills is not None and fills.n == 1
    finally:
        async with engines.OltpSession() as s:
            await _delete_user(s, user_id)


@pytest.mark.asyncio
async def test_state_survives_broker_restart(engines):
    """The actual user value of this PR — close the broker (simulated
    process exit), build a fresh one, and verify cash + position
    survive."""
    user_id = uuid4()
    async with engines.OltpSession() as s:
        await _insert_user(s, user_id)
    try:
        repo = PaperRepository(engines.OltpSession)

        # First "process": buy 10 shares.
        broker_a = _broker(repo, user_id)
        await broker_a.submit_order(
            Order(
                symbol="005930",
                side=OrderSide.BUY,
                quantity=Decimal("10"),
                order_type=OrderType.MARKET,
            )
        )
        assert broker_a.cash == Decimal("9300000")

        # Second "process": new broker, load state, confirm restoration.
        broker_b = _broker(repo, user_id)
        # Sanity: fresh broker starts at starting_cash before load.
        assert broker_b.cash == Decimal("10000000")
        await broker_b.load_from_db()
        assert broker_b.cash == Decimal("9300000")
        pos = await broker_b.get_position("005930")
        assert pos is not None
        assert pos.quantity == Decimal("10")
        assert pos.avg_entry_price == Decimal("70000")
    finally:
        async with engines.OltpSession() as s:
            await _delete_user(s, user_id)


@pytest.mark.asyncio
async def test_sell_persists_zeroed_position_and_realized_pnl(engines):
    user_id = uuid4()
    async with engines.OltpSession() as s:
        await _insert_user(s, user_id)
    try:
        repo = PaperRepository(engines.OltpSession)
        md = FixedPriceSource(prices={"005930": Decimal("70000")})
        broker = PaperBroker(
            market_data=md,
            config=PaperBrokerConfig(
                starting_cash=Decimal("10000000"),
                slippage_bps=Decimal("0"),
                commission_rate=Decimal("0"),
                sell_tax_rate=Decimal("0"),
            ),
            repo=repo,
            user_id=user_id,
        )
        await broker.submit_order(
            Order(
                symbol="005930",
                side=OrderSide.BUY,
                quantity=Decimal("10"),
                order_type=OrderType.MARKET,
            )
        )
        md.set_price("005930", Decimal("75000"))
        await broker.submit_order(
            Order(
                symbol="005930",
                side=OrderSide.SELL,
                quantity=Decimal("10"),
                order_type=OrderType.MARKET,
            )
        )

        # Position should be flat in memory and zeroed in DB (not deleted).
        assert await broker.get_position("005930") is None

        async with engines.OltpSession() as s:
            pos_row = (
                await s.execute(
                    text(
                        "SELECT quantity, realized_pnl FROM paper_position "
                        "WHERE user_id = :uid AND symbol = '005930'"
                    ),
                    {"uid": str(user_id)},
                )
            ).first()
            fills = (
                await s.execute(
                    text(
                        "SELECT side FROM paper_fill "
                        "WHERE user_id = :uid ORDER BY executed_at"
                    ),
                    {"uid": str(user_id)},
                )
            ).all()

        assert pos_row is not None
        assert Decimal(str(pos_row.quantity)) == Decimal("0")
        # Realized PnL = (75000 - 70000) * 10 = 50000
        assert Decimal(str(pos_row.realized_pnl)) == Decimal("50000")
        assert [r.side for r in fills] == ["buy", "sell"]
    finally:
        async with engines.OltpSession() as s:
            await _delete_user(s, user_id)


def test_broker_rejects_partial_repo_config():
    """repo without user_id (or vice versa) is a programmer error."""
    with pytest.raises(ValueError):
        PaperBroker(market_data=_md(), repo=None, user_id=uuid4())
    with pytest.raises(ValueError):
        PaperBroker(
            market_data=_md(),
            repo=PaperRepository(lambda: None),
            user_id=None,
        )
