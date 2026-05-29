"""
PaperRepository — async persistence layer for the PaperBroker.

Translates between the in-process dataclasses (Position, Fill) and the
``paper_account`` / ``paper_position`` / ``paper_fill`` tables in the
OLTP DB. Lives behind a Protocol so tests can swap a fake in
(``tests/test_paper_repo.py``) without spinning up Postgres for every
unit test.

Lifecycle:
* On startup the runtime calls ``load_state`` to restore cash + open
  positions for the configured user.
* On every fill the broker calls ``persist_fill`` inside the same
  ``async with`` — atomic insert + upsert for account/position.

The repository deliberately writes the *post-trade* account and
position snapshots alongside the fill. Recomputing them from the
fill log on startup is possible but slow once the log grows; storing
the snapshot keeps load_state O(1) per row regardless of history.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Optional, Protocol
from uuid import UUID

from sqlalchemy import text

from app.trading.types import Fill, Position

logger = logging.getLogger(__name__)


@dataclass
class PaperAccountState:
    cash: Decimal
    realized_pnl_today: Decimal


@dataclass
class PaperState:
    """Snapshot returned by ``load_state``."""

    account: Optional[PaperAccountState]
    positions: Dict[str, Position]


class PaperRepo(Protocol):
    async def load_state(self, user_id: UUID) -> PaperState:
        ...

    async def persist_fill(
        self,
        *,
        user_id: UUID,
        fill: Fill,
        broker_order_id: str,
        account_after: PaperAccountState,
        position_after: Optional[Position],
    ) -> None:
        ...


class PaperRepository:
    """Async OLTP-backed implementation. Takes a session_factory (async
    sessionmaker) — short-lived sessions per call avoid pool exhaustion
    and keep concurrent calls from sharing transactions."""

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    async def load_state(self, user_id: UUID) -> PaperState:
        async with self._session_factory() as session:
            acct_row = (
                await session.execute(
                    text(
                        "SELECT cash, realized_pnl_today "
                        "FROM paper_account WHERE user_id = :uid"
                    ),
                    {"uid": str(user_id)},
                )
            ).first()

            pos_rows = (
                await session.execute(
                    text(
                        "SELECT symbol, quantity, avg_entry_price, "
                        "       realized_pnl, opened_at "
                        "FROM paper_position WHERE user_id = :uid "
                        "  AND quantity > 0"
                    ),
                    {"uid": str(user_id)},
                )
            ).all()

        account = (
            PaperAccountState(
                cash=Decimal(str(acct_row.cash)),
                realized_pnl_today=Decimal(str(acct_row.realized_pnl_today)),
            )
            if acct_row is not None
            else None
        )

        positions: Dict[str, Position] = {}
        for r in pos_rows:
            positions[r.symbol] = Position(
                symbol=r.symbol,
                quantity=Decimal(str(r.quantity)),
                avg_entry_price=Decimal(str(r.avg_entry_price)),
                realized_pnl=Decimal(str(r.realized_pnl)),
                user_id=user_id,
                opened_at=r.opened_at,
            )

        return PaperState(account=account, positions=positions)

    async def persist_fill(
        self,
        *,
        user_id: UUID,
        fill: Fill,
        broker_order_id: str,
        account_after: PaperAccountState,
        position_after: Optional[Position],
    ) -> None:
        async with self._session_factory() as session:
            # 1. append the immutable fill row
            await session.execute(
                text(
                    """
                    INSERT INTO paper_fill (
                        fill_id, user_id, order_id, broker_order_id,
                        symbol, side, quantity, price, commission, executed_at
                    ) VALUES (
                        :fill_id, :uid, :order_id, :broker_order_id,
                        :symbol, :side, :qty, :price, :commission, :executed_at
                    )
                    """
                ),
                {
                    "fill_id": str(fill.fill_id),
                    "uid": str(user_id),
                    "order_id": str(fill.order_id),
                    "broker_order_id": broker_order_id,
                    "symbol": fill.symbol,
                    "side": fill.side.value,
                    "qty": fill.quantity,
                    "price": fill.price,
                    "commission": fill.commission,
                    "executed_at": fill.executed_at,
                },
            )

            # 2. upsert account snapshot
            await session.execute(
                text(
                    """
                    INSERT INTO paper_account (user_id, cash, realized_pnl_today)
                    VALUES (:uid, :cash, :pnl)
                    ON CONFLICT (user_id) DO UPDATE
                    SET cash = EXCLUDED.cash,
                        realized_pnl_today = EXCLUDED.realized_pnl_today
                    """
                ),
                {
                    "uid": str(user_id),
                    "cash": account_after.cash,
                    "pnl": account_after.realized_pnl_today,
                },
            )

            # 3. upsert position snapshot (or zero it if flat)
            if position_after is None or position_after.quantity == 0:
                # Closed: keep the row for history but zero quantity. Strategies
                # can DELETE if they really want; we just track quantity.
                await session.execute(
                    text(
                        """
                        UPDATE paper_position
                        SET quantity = 0,
                            realized_pnl = COALESCE(:realized, realized_pnl)
                        WHERE user_id = :uid AND symbol = :symbol
                        """
                    ),
                    {
                        "uid": str(user_id),
                        "symbol": fill.symbol,
                        "realized": (
                            position_after.realized_pnl
                            if position_after is not None
                            else None
                        ),
                    },
                )
            else:
                await session.execute(
                    text(
                        """
                        INSERT INTO paper_position (
                            user_id, symbol, quantity, avg_entry_price, realized_pnl
                        ) VALUES (
                            :uid, :symbol, :qty, :avg_price, :realized
                        )
                        ON CONFLICT (user_id, symbol) DO UPDATE
                        SET quantity = EXCLUDED.quantity,
                            avg_entry_price = EXCLUDED.avg_entry_price,
                            realized_pnl = EXCLUDED.realized_pnl
                        """
                    ),
                    {
                        "uid": str(user_id),
                        "symbol": position_after.symbol,
                        "qty": position_after.quantity,
                        "avg_price": position_after.avg_entry_price,
                        "realized": position_after.realized_pnl,
                    },
                )

            await session.commit()
