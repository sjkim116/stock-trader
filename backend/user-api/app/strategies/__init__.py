"""
Trading strategies.

A strategy is a pure decision function: given a snapshot of market data
+ account state, return at most one BUY or SELL decision. Strategies
never touch the broker or DB directly — the StrategyRunner threads the
plumbing so individual strategies stay small and testable.

Flow:
    runner.tick()
      ├─ for each strategy:
      │    ├─ build StrategyContext (history + position + cash)
      │    ├─ strategy.decide(ctx) → Optional[Decision]
      │    └─ if decision: SafetyGuard.submit_order(...)
"""

from app.strategies.base import BaseStrategy, Decision, StrategyContext
from app.strategies.ma_cross import MACrossoverParams, MACrossoverStrategy
from app.strategies.market_history import MarketDataHistory
from app.strategies.runner import StrategyRunner, TickResult

__all__ = [
    "BaseStrategy",
    "Decision",
    "MACrossoverParams",
    "MACrossoverStrategy",
    "MarketDataHistory",
    "StrategyContext",
    "StrategyRunner",
    "TickResult",
]
