"""
Pydantic models for the /api/v1/strategies router.

Decimal is serialised as string (matching the trading schemas) so
position quantities and prices don't lose precision through float.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


def _decimal_as_str(v: Decimal) -> str:
    return format(v, "f")


class _Money(BaseModel):
    model_config = ConfigDict(
        json_encoders={Decimal: _decimal_as_str},
        arbitrary_types_allowed=True,
    )


class RegisterMACrossoverRequest(BaseModel):
    """Register a Moving Average Crossover strategy. Only strategy
    type wired for Stage 3 — additional types land in follow-up PRs."""

    strategy_type: Literal["ma_crossover"] = "ma_crossover"
    symbol: str
    interval: str = "1m"
    history_length: int = 60
    short_period: int = 5
    long_period: int = 20
    position_size: Decimal = Field(default=Decimal("10"))


class StrategyRegistrationView(BaseModel):
    strategy_name: str
    symbol: str
    interval: str
    history_length: int


class StrategiesListResponse(BaseModel):
    strategies: List[StrategyRegistrationView]


class TickOutcomeView(_Money):
    strategy_name: str
    symbol: str
    decided_side: Optional[str] = None
    decided_quantity: Optional[Decimal] = None
    decided_reason: Optional[str] = None
    order_id: Optional[str] = None
    broker_order_id: Optional[str] = None
    fill_price: Optional[Decimal] = None
    error: Optional[str] = None


class TickResponse(_Money):
    submitted: int
    outcomes: List[TickOutcomeView]
    ticked_at: datetime
