"""
BaseStrategy contract + context/decision types.

Kept deliberately small. Anything a strategy needs beyond the
StrategyContext (e.g. external data feeds, ML model weights) should be
injected through its constructor — never pulled from globals.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from app.trading.types import OrderSide, Position


@dataclass(frozen=True)
class StrategyContext:
    """Read-only snapshot passed to ``decide``.

    ``recent_prices`` is ordered oldest → newest so a strategy can do
    ``recent_prices[-N:]`` to take the latest window. Empty list means
    no history yet — strategies should return None in that case
    rather than trade blind.
    """

    symbol: str
    current_price: Decimal
    recent_prices: List[Decimal]
    cash: Decimal
    current_position: Optional[Position] = None
    user_id: Optional[UUID] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class Decision:
    """A strategy's intent. The runner translates this into an Order
    through the SafetyGuard — strategies don't build Orders themselves.

    ``reason`` flows into logs and (later) the audit trail; keep it
    short and specific enough that someone reading a quiet-day log can
    tell why each order fired.
    """

    side: OrderSide
    quantity: Decimal
    reason: str


class BaseStrategy(ABC):
    """Pure decision function with optional internal state.

    Each strategy instance is single-symbol — multi-symbol strategies
    register one instance per symbol so per-symbol state (e.g. last
    signal) stays clean.

    The class attribute ``name`` is used for logging and to key
    strategy registrations; subclasses must set it.
    """

    name: str = "unnamed"

    @abstractmethod
    def decide(self, ctx: StrategyContext) -> Optional[Decision]:
        """Return BUY / SELL Decision or None to skip this tick."""
