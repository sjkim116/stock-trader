"""
Pydantic request/response models for the /api/v1/trading router.

Money fields are serialised as strings, not floats. Float precision is
fine for chart pixels but not for cash balances — a $0.01 round-trip
error compounding across trades is a real bug class. Clients should
parse with Decimal too.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


def _decimal_as_str(v: Decimal) -> str:
    return format(v, "f")


class _Money(BaseModel):
    model_config = ConfigDict(
        json_encoders={Decimal: _decimal_as_str},
        arbitrary_types_allowed=True,
    )


class AccountResponse(_Money):
    cash: Decimal
    equity: Decimal
    realized_pnl_today: Decimal
    unrealized_pnl: Decimal
    as_of: datetime


class PositionResponse(_Money):
    symbol: str
    quantity: Decimal
    avg_entry_price: Decimal
    realized_pnl: Decimal
    notional: Decimal
    opened_at: datetime


class PositionsResponse(_Money):
    positions: List[PositionResponse]


class SubmitOrderRequest(BaseModel):
    """Order placement. user_id is required so the kill switch can be
    keyed correctly; in a multi-user future this comes from the auth
    context, not the request body."""

    symbol: str
    side: str  # "buy" | "sell" — string at the API boundary, parsed inside
    quantity: Decimal
    order_type: str = "market"
    price: Optional[Decimal] = None
    user_id: Optional[UUID] = None
    user_strategy_id: Optional[UUID] = None


class OrderResponse(_Money):
    order_id: UUID
    broker_order_id: Optional[str]
    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    status: str
    price: Optional[Decimal]
    submitted_at: Optional[datetime]
    error_message: Optional[str]


class KillSwitchStateResponse(BaseModel):
    user_id: UUID
    enabled: bool
    reason: Optional[str]
    triggered_at: Optional[datetime]
    updated_at: datetime


class TriggerKillSwitchRequest(BaseModel):
    user_id: UUID
    reason: str = Field(..., min_length=1, max_length=500)


class ResetKillSwitchRequest(BaseModel):
    user_id: UUID
