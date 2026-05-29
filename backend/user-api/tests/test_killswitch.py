"""Integration tests for the DB-backed KillSwitch.

These require a real PostgreSQL with the kill_switch table — the
``engines`` fixture in conftest.py wires up the OLTP engine and the
docker-compose / CI postgres service provides the schema.

Tests insert and clean up a temporary users row because kill_switch.user_id
has an FK to users.user_id.
"""

from uuid import uuid4

import pytest
from sqlalchemy import text

from app.trading.killswitch import KillSwitch


async def _insert_user(session, user_id) -> None:
    await session.execute(
        text(
            "INSERT INTO users (user_id, email, password_hash) "
            "VALUES (:uid, :email, 'x') ON CONFLICT DO NOTHING"
        ),
        {"uid": str(user_id), "email": f"ks-{user_id}@test.local"},
    )
    await session.commit()


async def _delete_user(session, user_id) -> None:
    await session.execute(
        text("DELETE FROM users WHERE user_id = :uid"), {"uid": str(user_id)}
    )
    await session.commit()


@pytest.mark.asyncio
async def test_trigger_then_is_enabled_returns_true(engines):
    user_id = uuid4()
    async with engines.OltpSession() as s:
        await _insert_user(s, user_id)
    try:
        kill = KillSwitch(engines.OltpSession)
        assert await kill.is_enabled(user_id) is False

        await kill.trigger(user_id, reason="unit test")
        assert await kill.is_enabled(user_id) is True

        state = await kill.get(user_id)
        assert state is not None
        assert state.enabled is True
        assert state.reason == "unit test"
        assert state.triggered_at is not None
    finally:
        async with engines.OltpSession() as s:
            await _delete_user(s, user_id)


@pytest.mark.asyncio
async def test_reset_disables_the_switch(engines):
    user_id = uuid4()
    async with engines.OltpSession() as s:
        await _insert_user(s, user_id)
    try:
        kill = KillSwitch(engines.OltpSession)
        await kill.trigger(user_id, reason="will reset")
        assert await kill.is_enabled(user_id) is True

        await kill.reset(user_id)
        assert await kill.is_enabled(user_id) is False
        state = await kill.get(user_id)
        assert state is not None
        assert state.enabled is False
        assert state.reason is None
        assert state.triggered_at is None
    finally:
        async with engines.OltpSession() as s:
            await _delete_user(s, user_id)


@pytest.mark.asyncio
async def test_trigger_is_idempotent_and_updates_reason(engines):
    user_id = uuid4()
    async with engines.OltpSession() as s:
        await _insert_user(s, user_id)
    try:
        kill = KillSwitch(engines.OltpSession)
        await kill.trigger(user_id, reason="first reason")
        await kill.trigger(user_id, reason="second reason")
        state = await kill.get(user_id)
        assert state is not None
        assert state.reason == "second reason"
    finally:
        async with engines.OltpSession() as s:
            await _delete_user(s, user_id)
