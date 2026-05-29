"""
Pre-trade risk limits.

These mirror the per-strategy fields already in the OLTP
``user_strategies`` table (max_position_size, max_positions, etc.) plus
account-level limits that are independent of any strategy. Loading
from the DB lives in the user_strategies service layer (not this file)
so this module stays pure and testable.

Convention: when a limit is set to None the check is skipped. That
lets callers compose partial limits — strategies may opt out of some
checks but never opt out of the kill switch.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from app.trading.types import Order, OrderSide, Position


@dataclass(frozen=True)
class RiskLimits:
    """All limits are inclusive upper bounds. None ⇒ no limit."""

    max_position_size: Optional[Decimal] = None  # per-symbol notional cap
    max_order_notional: Optional[Decimal] = None  # cap per single order
    max_positions: Optional[int] = None  # how many open symbols at once
    daily_loss_limit: Optional[Decimal] = None  # halts when -|loss| hit
    allowed_symbols: Optional[frozenset] = None  # whitelist (None ⇒ all)


@dataclass(frozen=True)
class LimitViolation:
    """A single failed check. ``check_limits`` returns a list so the
    caller can log every reason an order was refused, not just the
    first one — useful when tuning a strategy that's hitting multiple
    walls."""

    code: str
    message: str


def check_limits(
    order: Order,
    *,
    limits: RiskLimits,
    positions: List[Position],
    realized_pnl_today: Decimal,
    fill_price_estimate: Decimal,
) -> List[LimitViolation]:
    """Pure function: given the inputs, return all violations.

    Empty list ⇒ trade is allowed by the limit checks. (The KillSwitch
    is a separate gate — checked by SafetyGuard before calling this.)
    """
    violations: List[LimitViolation] = []

    if (
        limits.allowed_symbols is not None
        and order.symbol not in limits.allowed_symbols
    ):
        violations.append(
            LimitViolation(
                "symbol_not_allowed",
                f"{order.symbol} is not in the strategy's allowed_symbols whitelist",
            )
        )

    order_notional = fill_price_estimate * order.quantity
    if (
        limits.max_order_notional is not None
        and order_notional > limits.max_order_notional
    ):
        violations.append(
            LimitViolation(
                "order_notional_exceeded",
                f"order notional {order_notional} > limit {limits.max_order_notional}",
            )
        )

    # max_position_size applies to the post-trade position, not the order alone.
    if limits.max_position_size is not None and order.side == OrderSide.BUY:
        current_qty = Decimal("0")
        avg_price = fill_price_estimate
        for p in positions:
            if p.symbol == order.symbol:
                current_qty = p.quantity
                avg_price = p.avg_entry_price
                break
        post_qty = current_qty + order.quantity
        # Approximate post-trade weighted price for the notional check.
        if current_qty > 0:
            post_avg = (
                (avg_price * current_qty) + (fill_price_estimate * order.quantity)
            ) / post_qty
        else:
            post_avg = fill_price_estimate
        post_notional = post_qty * post_avg
        if post_notional > limits.max_position_size:
            violations.append(
                LimitViolation(
                    "position_size_exceeded",
                    (
                        f"post-trade notional {post_notional} > "
                        f"max_position_size {limits.max_position_size}"
                    ),
                )
            )

    if limits.max_positions is not None and order.side == OrderSide.BUY:
        # Buying a symbol we don't already hold = opening a new position.
        already_holding = any(
            p.symbol == order.symbol and p.quantity > 0 for p in positions
        )
        open_positions = sum(1 for p in positions if p.quantity > 0)
        if not already_holding and open_positions >= limits.max_positions:
            violations.append(
                LimitViolation(
                    "max_positions_exceeded",
                    (
                        f"already holding {open_positions} positions "
                        f"(max {limits.max_positions})"
                    ),
                )
            )

    if limits.daily_loss_limit is not None:
        # daily_loss_limit is a positive number; the actual P&L is allowed
        # down to -daily_loss_limit.
        if realized_pnl_today <= -limits.daily_loss_limit:
            violations.append(
                LimitViolation(
                    "daily_loss_limit_hit",
                    (
                        f"realized P&L today {realized_pnl_today} "
                        f"≤ -{limits.daily_loss_limit}"
                    ),
                )
            )

    return violations
