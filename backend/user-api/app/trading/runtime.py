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

from typing import TYPE_CHECKING

from app.core import db as db_module
from app.core.config import settings
from app.trading.broker import Broker
from app.trading.killswitch import KillSwitch
from app.trading.kis.broker import KISBroker
from app.trading.limits import RiskLimits
from app.trading.market_data import LatestPriceFromDB, MarketDataSource
from app.trading.paper import PaperBroker, PaperBrokerConfig
from app.trading.paper_repo import PaperRepository
from app.trading.safety import SafetyGuard

if TYPE_CHECKING:
    from app.strategies.runner import StrategyRunner

logger = logging.getLogger(__name__)

_broker: Optional[Broker] = None
_safety: Optional[SafetyGuard] = None
_killswitch: Optional[KillSwitch] = None
_market_data: Optional[MarketDataSource] = None

# Strategy runner is built lazily and may stay None for ops-only
# deployments that just expose the trading HTTP API without running
# strategies. Importable through ``app.trading.runtime.get_strategy_runner``.
_strategy_runner: Optional["StrategyRunner"] = None


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

    if settings.kis_configured:
        # KIS branch — orders go to 한국투자증권. SafetyGuard wraps it
        # the same way it wraps PaperBroker; kill switch + risk limits
        # still apply. KIS owns cash/positions, so PAPER_TRADING_USER_ID
        # is intentionally ignored on this path.
        _broker = KISBroker(
            base_url=settings.kis_base_url,
            app_key=settings.KIS_APP_KEY,
            app_secret=settings.KIS_APP_SECRET,
            account_number=settings.KIS_ACCOUNT_NUMBER,
            account_product_code=settings.KIS_ACCOUNT_PRODUCT_CODE,
            paper_mode=settings.KIS_PAPER_MODE,
            timeout_seconds=settings.KIS_HTTP_TIMEOUT_SECONDS,
        )
        logger.info(
            "Trading runtime initialised with KISBroker (paper_mode=%s)",
            settings.KIS_PAPER_MODE,
        )
    else:
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
    """Clear singleton references. Does NOT close the broker — call
    ``aclose_broker()`` first if the broker holds I/O resources (KIS
    httpx client). Kept synchronous so sync test fixtures can reset
    state without an event loop."""
    global _broker, _safety, _killswitch, _market_data, _strategy_runner
    _broker = None
    _safety = None
    _killswitch = None
    _market_data = None
    _strategy_runner = None


async def aclose_broker() -> None:
    """Close external resources the current broker owns (e.g. KIS
    httpx client + token cache). Idempotent."""
    if isinstance(_broker, KISBroker):
        await _broker.aclose()


def set_strategy_runner(runner) -> None:
    """Register the StrategyRunner singleton. Kept as a setter rather
    than baked into init_runtime because strategy registration is
    user-configured and shouldn't block trading-only deployments from
    booting."""
    global _strategy_runner
    _strategy_runner = runner


def get_strategy_runner():
    if _strategy_runner is None:
        raise RuntimeError("strategy runner not initialised")
    return _strategy_runner


def has_strategy_runner() -> bool:
    return _strategy_runner is not None


def get_broker() -> Broker:
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
