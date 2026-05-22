"""Integration tests for the dual-DB engine lifecycle."""

import pytest


@pytest.mark.asyncio
async def test_init_creates_both_engines_and_session_factories(engines):
    assert engines.oltp_engine is not None
    assert engines.ts_engine is not None
    assert engines.OltpSession is not None
    assert engines.TsSession is not None


@pytest.mark.asyncio
async def test_ping_both_engines(engines):
    assert await engines.ping_oltp() is True
    assert await engines.ping_ts() is True


@pytest.mark.asyncio
async def test_oltp_session_yields_working_connection(engines):
    from sqlalchemy import text

    async with engines.OltpSession() as session:
        result = await session.execute(text("SELECT 42 AS answer"))
        row = result.first()
        assert row is not None
        assert row.answer == 42


@pytest.mark.asyncio
async def test_ts_session_yields_working_connection(engines):
    from sqlalchemy import text

    async with engines.TsSession() as session:
        result = await session.execute(text("SELECT 7 AS lucky"))
        row = result.first()
        assert row is not None
        assert row.lucky == 7
