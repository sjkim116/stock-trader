"""
Domain types shared across the trading layer.

These mirror the OLTP schema (orders / positions) but are deliberately
plain dataclasses — they're for in-process passing between strategy,
safety, and broker code. Persistence lives in the SQLAlchemy models
that will be added when strategies start producing real trade data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class Order:
    """A trading order pre-submission. After Broker.submit_order it gets
    a broker_order_id and one or more Fills."""

    symbol: str
    side: OrderSide
    quantity: Decimal
    order_type: OrderType = OrderType.MARKET
    price: Optional[Decimal] = None  # limit price (None for market)
    stop_price: Optional[Decimal] = None
    user_id: Optional[UUID] = None
    user_strategy_id: Optional[UUID] = None

    # Populated by the broker after submission.
    order_id: UUID = field(default_factory=uuid4)
    broker_order_id: Optional[str] = None
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    submitted_at: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class Fill:
    """A single execution. An Order may produce one Fill (full fill) or
    many (partial fills)."""

    order_id: UUID
    symbol: str
    side: OrderSide
    quantity: Decimal
    price: Decimal
    commission: Decimal = Decimal("0")
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    fill_id: UUID = field(default_factory=uuid4)


@dataclass
class Position:
    """Net position in a symbol. Quantity is signed: positive = long,
    negative = short. For the paper broker shorts are disallowed by
    default."""

    symbol: str
    quantity: Decimal
    avg_entry_price: Decimal
    user_id: Optional[UUID] = None
    realized_pnl: Decimal = Decimal("0")
    opened_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def notional(self) -> Decimal:
        return abs(self.quantity) * self.avg_entry_price

    @property
    def is_long(self) -> bool:
        return self.quantity > 0

    @property
    def is_flat(self) -> bool:
        return self.quantity == 0


@dataclass
class AccountInfo:
    """Snapshot of account state at a point in time."""

    cash: Decimal
    equity: Decimal  # cash + market value of positions
    realized_pnl_today: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    as_of: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
