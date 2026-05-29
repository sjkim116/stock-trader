"""
MarketDataSource — read-only "last known price" lookup.

PaperBroker uses it to simulate fills; SafetyGuard uses it to compute
notional value for limit checks. Kept as a Protocol so tests can swap
in FixedPriceSource without touching the database.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Protocol

from sqlalchemy import text


class MissingPriceError(LookupError):
    """No price available for the requested symbol. Callers should
    treat this as a hard rejection — better to refuse the trade than
    to fill it at a guessed price."""

    def __init__(self, symbol: str) -> None:
        super().__init__(f"no recent price for symbol {symbol!r}")
        self.symbol = symbol


class MarketDataSource(Protocol):
    """Source of last-known close prices keyed by symbol."""

    async def get_price(self, symbol: str) -> Decimal:
        """Return latest price for symbol. Raises MissingPriceError
        when no row is available."""


@dataclass
class FixedPriceSource:
    """Deterministic in-memory source. Used in tests and for offline
    backtests where prices come from a fixture rather than the DB."""

    prices: Dict[str, Decimal]

    async def get_price(self, symbol: str) -> Decimal:
        try:
            return self.prices[symbol]
        except KeyError as exc:
            raise MissingPriceError(symbol) from exc

    def set_price(self, symbol: str, price: Decimal) -> None:
        self.prices[symbol] = price


class LatestPriceFromDB:
    """Reads the most recent close from the time-series database.

    Held intentionally simple — one query per call. Strategies that
    fetch many symbols at once should batch via a future
    ``get_prices`` helper rather than looping this method.
    """

    def __init__(self, session_factory):
        # session_factory is an async_sessionmaker bound to the TS engine.
        # We accept the factory (not a live session) so each call gets a
        # fresh short-lived session — long-lived sessions in this code
        # path tend to leak connections under partial failures.
        self._session_factory = session_factory

    async def get_price(self, symbol: str) -> Decimal:
        async with self._session_factory() as session:
            row = (
                await session.execute(
                    text(
                        "SELECT close FROM market_data "
                        "WHERE symbol = :symbol "
                        "ORDER BY time DESC LIMIT 1"
                    ),
                    {"symbol": symbol},
                )
            ).first()
        if row is None or row.close is None:
            raise MissingPriceError(symbol)
        return Decimal(str(row.close))
