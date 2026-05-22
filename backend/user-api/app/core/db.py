"""
Async SQLAlchemy engines for the OLTP and time-series databases.

Two pools rather than one because the two databases are physically separate
in cloud deployments (RDS + EC2 TimescaleDB). See ``core/config.py`` for the
endpoint config and ``database/`` for the schemas each one owns.

Routes use the FastAPI ``Depends(get_oltp_session)`` / ``Depends(get_ts_session)``
generators to get a per-request ``AsyncSession``. The engines themselves are
created once on app startup and disposed on shutdown.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

# Module-level engines + session factories. Initialised in ``init_engines``
# and disposed in ``dispose_engines`` to keep the lifespan explicit.
oltp_engine: AsyncEngine | None = None
ts_engine: AsyncEngine | None = None

OltpSession: async_sessionmaker[AsyncSession] | None = None
TsSession: async_sessionmaker[AsyncSession] | None = None


def _make_engine(url: str, *, label: str) -> AsyncEngine:
    return create_async_engine(
        url,
        echo=settings.DB_ECHO,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT_SECONDS,
        pool_recycle=settings.DB_POOL_RECYCLE_SECONDS,
        pool_pre_ping=True,
        connect_args={"server_settings": {"application_name": f"user-api/{label}"}},
    )


async def init_engines() -> None:
    """Create the two engines and their session factories."""
    global oltp_engine, ts_engine, OltpSession, TsSession

    if oltp_engine is not None or ts_engine is not None:
        logger.warning("init_engines called twice; ignoring second call")
        return

    oltp_engine = _make_engine(settings.oltp_async_url, label="oltp")
    ts_engine = _make_engine(settings.ts_async_url, label="ts")

    OltpSession = async_sessionmaker(
        oltp_engine, expire_on_commit=False, class_=AsyncSession
    )
    TsSession = async_sessionmaker(
        ts_engine, expire_on_commit=False, class_=AsyncSession
    )

    logger.info(
        "Initialised DB engines: oltp=%s:%s/%s ts=%s:%s/%s",
        settings.DATABASE_HOST,
        settings.DATABASE_PORT,
        settings.DATABASE_NAME,
        settings.TIMESCALEDB_HOST,
        settings.TIMESCALEDB_PORT,
        settings.TIMESCALEDB_NAME,
    )


async def dispose_engines() -> None:
    """Dispose both engine pools. Safe to call multiple times."""
    global oltp_engine, ts_engine, OltpSession, TsSession

    if oltp_engine is not None:
        await oltp_engine.dispose()
        oltp_engine = None
    if ts_engine is not None:
        await ts_engine.dispose()
        ts_engine = None
    OltpSession = None
    TsSession = None
    logger.info("Disposed DB engines")


async def get_oltp_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding an OLTP ``AsyncSession``."""
    if OltpSession is None:
        raise RuntimeError("OLTP engine not initialised; call init_engines() first")
    async with OltpSession() as session:
        yield session


async def get_ts_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a time-series ``AsyncSession``."""
    if TsSession is None:
        raise RuntimeError(
            "Time-series engine not initialised; call init_engines() first"
        )
    async with TsSession() as session:
        yield session


async def _ping(engine: AsyncEngine | None) -> bool:
    if engine is None:
        return False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001 — health check intentionally broad
        logger.warning("DB ping failed: %s", exc)
        return False


async def ping_oltp() -> bool:
    return await _ping(oltp_engine)


async def ping_ts() -> bool:
    return await _ping(ts_engine)
