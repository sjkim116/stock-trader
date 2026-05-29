"""
KIS (한국투자증권) OpenAPI integration.

Two-layer split:
* ``auth.KISTokenManager`` — OAuth2 access token caching + refresh.
* ``broker.KISBroker`` — Broker Protocol implementation. SafetyGuard
  wraps it the same way it wraps PaperBroker, so kill switch + risk
  limits + audit all keep working.

Mode is controlled by ``settings.KIS_PAPER_MODE`` (default True →
모의투자 sandbox URL + V*-prefixed tr_id). Real-mode orders place
actual trades; the runtime never enables it implicitly.
"""

from app.trading.kis.auth import KISTokenManager
from app.trading.kis.broker import KISBroker
from app.trading.kis.errors import KISError, KISOrderRejectedError

__all__ = [
    "KISBroker",
    "KISError",
    "KISOrderRejectedError",
    "KISTokenManager",
]
