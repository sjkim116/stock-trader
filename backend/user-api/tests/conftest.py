"""Pytest configuration for the user-api test suite."""

import pytest_asyncio

from app.core import db as db_module


@pytest_asyncio.fixture
async def engines():
    """Initialise the dual-DB engines for a test and dispose them after.

    Requires DATABASE_* and TIMESCALEDB_* env vars to point at a reachable
    PostgreSQL. In CI the workflow stands up a single TimescaleDB container
    that backs both.
    """
    await db_module.init_engines()
    try:
        yield db_module
    finally:
        await db_module.dispose_engines()
