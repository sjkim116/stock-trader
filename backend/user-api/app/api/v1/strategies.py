"""
HTTP endpoints for the strategy engine.

The runner singleton is created in the lifespan; this router only
exposes it. Strategies are registered via HTTP rather than baked into
code so testing different parameter sets stays a hot-reload affair,
not a redeploy.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from app.api.v1.strategies_schemas import (
    RegisterMACrossoverRequest,
    StrategiesListResponse,
    StrategyRegistrationView,
    TickOutcomeView,
    TickResponse,
)
from app.strategies.ma_cross import MACrossoverParams, MACrossoverStrategy
from app.strategies.runner import StrategyRegistration
from app.trading import runtime
from uuid import UUID

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/strategies", tags=["Strategies"])


@router.get("", response_model=StrategiesListResponse)
async def list_strategies() -> StrategiesListResponse:
    if not runtime.has_strategy_runner():
        return StrategiesListResponse(strategies=[])
    runner = runtime.get_strategy_runner()
    return StrategiesListResponse(
        strategies=[
            StrategyRegistrationView(
                strategy_name=r.strategy.name,
                symbol=r.symbol,
                interval=r.interval,
                history_length=r.history_length,
            )
            for r in runner.registrations
        ]
    )


@router.post(
    "/register",
    response_model=StrategyRegistrationView,
    status_code=201,
)
async def register_strategy(
    body: RegisterMACrossoverRequest,
) -> StrategyRegistrationView:
    if not runtime.has_strategy_runner():
        raise HTTPException(status_code=503, detail="strategy runner not initialised")
    try:
        params = MACrossoverParams(
            short_period=body.short_period,
            long_period=body.long_period,
            position_size=body.position_size,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    strategy = MACrossoverStrategy(params=params)
    reg = StrategyRegistration(
        strategy=strategy,
        symbol=body.symbol,
        interval=body.interval,
        history_length=body.history_length,
    )
    runtime.get_strategy_runner().register(reg)
    return StrategyRegistrationView(
        strategy_name=strategy.name,
        symbol=reg.symbol,
        interval=reg.interval,
        history_length=reg.history_length,
    )


@router.post("/tick", response_model=TickResponse)
async def tick(
    user_id: UUID
    | None = Query(
        default=None,
        description="Attribute submitted orders to this user (kill switch + audit).",
    ),
) -> TickResponse:
    if not runtime.has_strategy_runner():
        raise HTTPException(status_code=503, detail="strategy runner not initialised")
    result = await runtime.get_strategy_runner().tick(user_id=user_id)

    outcomes_view = []
    for o in result.outcomes:
        view = TickOutcomeView(strategy_name=o.strategy_name, symbol=o.symbol)
        if o.decision is not None:
            view.decided_side = o.decision.side.value
            view.decided_quantity = o.decision.quantity
            view.decided_reason = o.decision.reason
        if o.order is not None:
            view.order_id = str(o.order.order_id)
            view.broker_order_id = o.order.broker_order_id
            # Paper fills go straight to FILLED, so the fill price lives
            # on the broker's fills list rather than the order; surfacing
            # the order's price-if-any is enough for the dashboard.
            view.fill_price = o.order.price
        if o.error is not None:
            view.error = o.error
        outcomes_view.append(view)

    return TickResponse(
        submitted=result.submitted,
        outcomes=outcomes_view,
        ticked_at=datetime.now(timezone.utc),
    )
