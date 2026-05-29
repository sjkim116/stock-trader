"""
MarketDataHistory — read the last N closes from the TimescaleDB hypertable.

Single-purpose, no caching at this layer. Strategies that need a wider
window will pull longer histories; the hypertable's index on
(symbol, time DESC) makes the LIMIT-N query cheap regardless of total
row count.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Protocol

from sqlalchemy import text


class HistorySource(Protocol):
    async def recent_closes(
        self, symbol: str, interval: str, limit: int
    ) -> List[Decimal]:
        ...


@dataclass
class StaticHistory:
    """In-memory deterministic source for tests. Holds a per-symbol
    list of closes ordered oldest → newest. ``recent_closes`` returns
    the tail in oldest→newest order to match the contract."""

    bars: dict

    async def recent_closes(
        self, symbol: str, interval: str, limit: int
    ) -> List[Decimal]:
        series = self.bars.get(symbol, [])
        return list(series[-limit:])


class MarketDataHistory:
    """Reads the TimescaleDB ``market_data`` hypertable."""

    def __init__(self, ts_session_factory) -> None:
        # ts_session_factory is the TsSession async_sessionmaker bound
        # to the time-series engine (see app.core.db).
        self._session_factory = ts_session_factory

    async def recent_closes(
        self, symbol: str, interval: str, limit: int
    ) -> List[Decimal]:
        """Return the last ``limit`` closes for symbol+interval, oldest
        → newest. Empty list when there's no data — callers must treat
        that as "skip this tick" not "fill at zero"."""
        if limit <= 0:
            return []
        async with self._session_factory() as session:
            rows = (
                await session.execute(
                    text(
                        """
                        SELECT close FROM (
                            SELECT time, close
                            FROM market_data
                            WHERE symbol = :symbol
                              AND interval = :interval
                              AND close IS NOT NULL
                            ORDER BY time DESC
                            LIMIT :limit
                        ) t
                        ORDER BY time ASC
                        """
                    ),
                    {"symbol": symbol, "interval": interval, "limit": limit},
                )
            ).all()
        return [Decimal(str(r.close)) for r in rows]
