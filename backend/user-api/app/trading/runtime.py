"""
Process-wide trading runtime.

The HTTP layer needs a *shared* PaperBroker — state (cash, positions,
fills) must persist across requests within a process. A new instance
per request would reset everything. This module owns the singleton and
exposes typed accessors so handlers don't reach into module globals.

Init/dispose live alongside the DB engine lifecycle in
``app.core.db`` and are called from the FastAPI ``lifespan``.

Note: in-memory state is per-process. Multi-worker deployments will
need DB-backed persistence (next PR) before they're safe.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.core import db as db_module
from app.core.config import settings
from app.trading.killswitch import KillSwitch
from app.trading.limits import RiskLimits
from app.trading.market_data import LatestPriceFromDB, MarketDataSource
from app.trading.paper import PaperBroker, PaperBrokerConfig
from app.trading.paper_repo import PaperRepository
from app.trading.safety import SafetyGuard

logger = logging.getLogger(__name__)

_broker: Optional[PaperBroker] = None
_safety: Optional[SafetyGuard] = None
_killswitch: Optional[KillSwitch] = None
_market_data: Optional[MarketDataSource] = None


async def init_runtime(
    *,
    market_data: Optional[MarketDataSource] = None,
    broker_config: Optional[PaperBrokerConfig] = None,
    limits: Optional[RiskLimits] = None,
) -> None:
    """Build the singleton broker / safety / killswitch.

    Must be called after ``db.init_engines`` because both the
    MarketDataSource and KillSwitch read through the TS / OLTP sessions.

    When ``settings.PAPER_TRADING_USER_ID`` is set, the PaperBroker is
    backed by ``PaperRepository`` — cash and positions are loaded from
    the DB on startup and persisted on every fill, so restarts don't
    wipe state.
    """
    global _broker, _safety, _killswitch, _market_data

    if _broker is not None:
        logger.warning("init_runtime called twice; ignoring second call")
        return

    if db_module.TsSession is None or db_module.OltpSession is None:
        raise RuntimeError(
            "DB engines must be initialised before init_runtime — "
            "did the lifespan call db.init_engines first?"
        )

    _market_data = market_data or LatestPriceFromDB(db_module.TsSession)
    _killswitch = KillSwitch(db_module.OltpSession)

    user_id = settings.PAPER_TRADING_USER_ID
    if user_id is not None:
        repo = PaperRepository(db_module.OltpSession)
        _broker = PaperBroker(
            market_data=_market_data,
            config=broker_config,
            repo=repo,
            user_id=user_id,
        )
        await _broker.load_from_db()
        logger.info(
            "Trading runtime initialised with DB persistence (user_id=%s)",
            user_id,
        )
    else:
        _broker = PaperBroker(market_data=_market_data, config=broker_config)
        logger.info("Trading runtime initialised (in-memory PaperBroker)")

    # Limits start fully permissive — callers tighten via POST /trading/limits
    # in a later PR. Kill switch stays wired regardless.
    _safety = SafetyGuard(
        broker=_broker,
        market_data=_market_data,
        limits=limits or RiskLimits(),
        kill_switch=_killswitch,
    )


def dispose_runtime() -> None:
    """Tear down the singleton so a subsequent init starts clean.
    Safe to call multiple times."""
    global _broker, _safety, _killswitch, _market_data
    _broker = None
    _safety = None
    _killswitch = None
    _market_data = None


def get_broker() -> PaperBroker:
    if _broker is None:
        raise RuntimeError("trading runtime not initialised")
    return _broker


def get_safety_guard() -> SafetyGuard:
    if _safety is None:
        raise RuntimeError("trading runtime not initialised")
    return _safety


def get_killswitch() -> KillSwitch:
    if _killswitch is None:
        raise RuntimeError("trading runtime not initialised")
    return _killswitch


def get_market_data() -> MarketDataSource:
    if _market_data is None:
        raise RuntimeError("trading runtime not initialised")
    return _market_data
