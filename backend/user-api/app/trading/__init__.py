"""
Trading layer for AlgoTrader Pro user-api.

Composition (innermost → outermost):

    Strategy → SafetyGuard → Broker

* Broker — abstract execution endpoint. PaperBroker is the default
  implementation; future BrokerKIS / BrokerXing etc. plug in here.
* SafetyGuard — wraps any Broker. Refuses orders that breach RiskLimits
  or when the per-user KillSwitch is enabled. Strategies should never
  talk to a raw broker; they go through this wrapper.
* MarketDataSource — read-only source of "last known price" used by
  PaperBroker to simulate fills and by SafetyGuard for notional checks.

Nothing in this package places real orders. Real-broker adapters land
in follow-up PRs once the safety layer is verified end-to-end.
"""

from app.trading.broker import Broker, BrokerError, OrderRejectedError
from app.trading.killswitch import KillSwitch, KillSwitchState
from app.trading.limits import LimitViolation, RiskLimits, check_limits
from app.trading.market_data import (
    FixedPriceSource,
    LatestPriceFromDB,
    MarketDataSource,
    MissingPriceError,
)
from app.trading.paper import PaperBroker
from app.trading.safety import SafetyGuard
from app.trading.types import (
    AccountInfo,
    Fill,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
)

__all__ = [
    "AccountInfo",
    "Broker",
    "BrokerError",
    "Fill",
    "FixedPriceSource",
    "KillSwitch",
    "KillSwitchState",
    "LatestPriceFromDB",
    "LimitViolation",
    "MarketDataSource",
    "MissingPriceError",
    "Order",
    "OrderRejectedError",
    "OrderSide",
    "OrderStatus",
    "OrderType",
    "PaperBroker",
    "Position",
    "RiskLimits",
    "SafetyGuard",
    "check_limits",
]
