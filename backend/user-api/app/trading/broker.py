"""
Broker abstraction.

Any execution endpoint — paper, KIS, Xing, Alpaca — implements this
Protocol. The trading layer (and strategies above it) only talk to this
interface, so swapping execution venues is a constructor change.
"""

from __future__ import annotations

from typing import List, Optional, Protocol

from app.trading.types import AccountInfo, Order, Position


class BrokerError(Exception):
    """Base class for all broker-side failures."""


class OrderRejectedError(BrokerError):
    """The broker refused the order (validation, insufficient funds,
    market closed, kill switch, etc.). The original Order is attached
    so callers can log and route to error handlers."""

    def __init__(self, order: Order, reason: str) -> None:
        super().__init__(
            f"{order.symbol} {order.side.value} x{order.quantity}: {reason}"
        )
        self.order = order
        self.reason = reason


class Broker(Protocol):
    """Execution endpoint contract.

    Implementations:
    * PaperBroker — in-memory simulation (this PR)
    * BrokerKIS / BrokerXing / ... — real broker adapters (later)
    """

    async def submit_order(self, order: Order) -> Order:
        """Place an order. Returns the order with status updated
        (FILLED / PARTIALLY_FILLED / REJECTED / SUBMITTED) and
        broker_order_id set. Raises OrderRejectedError on hard rejection."""

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a working order. Returns True if cancellation was
        accepted (idempotent — already-cancelled is True too)."""

    async def get_position(self, symbol: str) -> Optional[Position]:
        """Current net position in a symbol, or None if flat."""

    async def get_positions(self) -> List[Position]:
        """All non-flat positions."""

    async def get_account(self) -> AccountInfo:
        """Current account snapshot."""
