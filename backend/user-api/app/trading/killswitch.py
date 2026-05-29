"""
KillSwitch — per-user emergency stop persisted in the OLTP DB.

When enabled, SafetyGuard refuses every order regardless of limits or
strategy state. Use cases:

* Manual: user hits "STOP ALL" in the UI.
* Automatic: SafetyGuard trips it when daily_loss_limit is reached so
  the next order doesn't even try.
* Operational: ops/admin can flip the flag with a single UPDATE if
  something looks wrong, without restarting the app.

Backed by ``database/schema_oltp.sql``'s ``kill_switch`` table.
Reset is intentionally manual — auto-reset on midnight would defeat
the purpose. Users must explicitly turn it back on after they've
checked what tripped it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import text


@dataclass(frozen=True)
class KillSwitchState:
    user_id: UUID
    enabled: bool
    reason: Optional[str]
    triggered_at: Optional[datetime]
    updated_at: datetime


class KillSwitch:
    """Reads and writes the per-user kill_switch flag.

    Takes a session_factory (async_sessionmaker) rather than a live
    session — each call uses a short-lived session, so a tripped switch
    is immediately visible to the next read even from a different task.
    """

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    async def is_enabled(self, user_id: UUID) -> bool:
        async with self._session_factory() as session:
            row = (
                await session.execute(
                    text("SELECT enabled FROM kill_switch WHERE user_id = :uid"),
                    {"uid": str(user_id)},
                )
            ).first()
        return bool(row.enabled) if row is not None else False

    async def get(self, user_id: UUID) -> Optional[KillSwitchState]:
        async with self._session_factory() as session:
            row = (
                await session.execute(
                    text(
                        "SELECT user_id, enabled, reason, triggered_at, updated_at "
                        "FROM kill_switch WHERE user_id = :uid"
                    ),
                    {"uid": str(user_id)},
                )
            ).first()
        if row is None:
            return None
        return KillSwitchState(
            user_id=UUID(str(row.user_id)),
            enabled=bool(row.enabled),
            reason=row.reason,
            triggered_at=row.triggered_at,
            updated_at=row.updated_at,
        )

    async def trigger(self, user_id: UUID, *, reason: str) -> None:
        """Enable the kill switch for a user. Idempotent — calling it
        on an already-enabled switch updates the reason and timestamp."""
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO kill_switch (user_id, enabled, reason, triggered_at)
                    VALUES (:uid, TRUE, :reason, NOW())
                    ON CONFLICT (user_id) DO UPDATE
                    SET enabled = TRUE,
                        reason = EXCLUDED.reason,
                        triggered_at = NOW()
                    """
                ),
                {"uid": str(user_id), "reason": reason},
            )
            await session.commit()

    async def reset(self, user_id: UUID) -> None:
        """Disable the kill switch. Deliberately requires explicit
        action — no auto-reset on day rollover."""
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO kill_switch (user_id, enabled, reason, triggered_at)
                    VALUES (:uid, FALSE, NULL, NULL)
                    ON CONFLICT (user_id) DO UPDATE
                    SET enabled = FALSE,
                        reason = NULL,
                        triggered_at = NULL
                    """
                ),
                {"uid": str(user_id)},
            )
            await session.commit()
