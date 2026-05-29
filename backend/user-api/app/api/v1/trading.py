"""
HTTP endpoints for the trading layer.

No auth yet — ``user_id`` is passed explicitly by the caller (query
param for reads, body for writes). When Cognito wiring lands, this
will move into a ``Depends(get_current_user)`` and ``user_id`` will
disappear from request schemas.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.v1.trading_schemas import (
    AccountResponse,
    KillSwitchStateResponse,
    OrderResponse,
    PositionResponse,
    PositionsResponse,
    ResetKillSwitchRequest,
    SubmitOrderRequest,
    TriggerKillSwitchRequest,
)
from app.trading import runtime
from app.trading.broker import OrderRejectedError
from app.trading.types import Order, OrderSide, OrderType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trading", tags=["Trading"])


# ---------------------------------------------------------------- account
@router.get("/account", response_model=AccountResponse)
async def get_account() -> AccountResponse:
    broker = runtime.get_broker()
    account = await broker.get_account()
    return AccountResponse(
        cash=account.cash,
        equity=account.equity,
        realized_pnl_today=account.realized_pnl_today,
        unrealized_pnl=account.unrealized_pnl,
        as_of=account.as_of,
    )


# --------------------------------------------------------------- positions
def _to_position_response(p) -> PositionResponse:
    return PositionResponse(
        symbol=p.symbol,
        quantity=p.quantity,
        avg_entry_price=p.avg_entry_price,
        realized_pnl=p.realized_pnl,
        notional=p.notional,
        opened_at=p.opened_at,
    )


@router.get("/positions", response_model=PositionsResponse)
async def list_positions() -> PositionsResponse:
    broker = runtime.get_broker()
    positions = await broker.get_positions()
    return PositionsResponse(positions=[_to_position_response(p) for p in positions])


@router.get("/positions/{symbol}", response_model=PositionResponse)
async def get_position(symbol: str) -> PositionResponse:
    broker = runtime.get_broker()
    p = await broker.get_position(symbol)
    if p is None:
        raise HTTPException(status_code=404, detail=f"no open position in {symbol}")
    return _to_position_response(p)


# ------------------------------------------------------------------ orders
@router.post(
    "/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_order(body: SubmitOrderRequest) -> OrderResponse:
    try:
        side = OrderSide(body.side.lower())
        order_type = OrderType(body.order_type.lower())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if body.quantity <= Decimal("0"):
        raise HTTPException(status_code=422, detail="quantity must be positive")

    order = Order(
        symbol=body.symbol,
        side=side,
        quantity=body.quantity,
        order_type=order_type,
        price=body.price,
        user_id=body.user_id,
        user_strategy_id=body.user_strategy_id,
    )

    guard = runtime.get_safety_guard()
    try:
        result = await guard.submit_order(order)
    except OrderRejectedError as exc:
        # 422 because the rejection is the caller's input failing a
        # business rule, not a 500-class server fault.
        logger.info("order rejected: %s", exc.reason)
        raise HTTPException(status_code=422, detail=exc.reason) from exc

    return OrderResponse(
        order_id=result.order_id,
        broker_order_id=result.broker_order_id,
        symbol=result.symbol,
        side=result.side.value,
        order_type=result.order_type.value,
        quantity=result.quantity,
        status=result.status.value,
        price=result.price,
        submitted_at=result.submitted_at,
        error_message=result.error_message,
    )


# -------------------------------------------------------------- kill switch
@router.get("/killswitch", response_model=KillSwitchStateResponse)
async def get_killswitch(
    user_id: UUID = Query(..., description="User UUID"),
) -> KillSwitchStateResponse:
    kill = runtime.get_killswitch()
    state = await kill.get(user_id)
    if state is None:
        # Treat absence as disabled — caller doesn't need to seed the
        # table just to read state.
        from datetime import datetime, timezone

        return KillSwitchStateResponse(
            user_id=user_id,
            enabled=False,
            reason=None,
            triggered_at=None,
            updated_at=datetime.now(timezone.utc),
        )
    return KillSwitchStateResponse(
        user_id=state.user_id,
        enabled=state.enabled,
        reason=state.reason,
        triggered_at=state.triggered_at,
        updated_at=state.updated_at,
    )


@router.post(
    "/killswitch/trigger",
    response_model=KillSwitchStateResponse,
    status_code=status.HTTP_200_OK,
)
async def trigger_killswitch(body: TriggerKillSwitchRequest) -> KillSwitchStateResponse:
    kill = runtime.get_killswitch()
    await kill.trigger(body.user_id, reason=body.reason)
    state = await kill.get(body.user_id)
    assert state is not None  # just wrote it
    return KillSwitchStateResponse(
        user_id=state.user_id,
        enabled=state.enabled,
        reason=state.reason,
        triggered_at=state.triggered_at,
        updated_at=state.updated_at,
    )


@router.post(
    "/killswitch/reset",
    response_model=KillSwitchStateResponse,
    status_code=status.HTTP_200_OK,
)
async def reset_killswitch(body: ResetKillSwitchRequest) -> KillSwitchStateResponse:
    kill = runtime.get_killswitch()
    await kill.reset(body.user_id)
    state = await kill.get(body.user_id)
    assert state is not None
    return KillSwitchStateResponse(
        user_id=state.user_id,
        enabled=state.enabled,
        reason=state.reason,
        triggered_at=state.triggered_at,
        updated_at=state.updated_at,
    )
