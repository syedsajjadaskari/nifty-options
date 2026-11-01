"""Core trading, execution, and strategy interfaces."""

from nifty_trading.core.backtest import BacktestConfig, BacktestEngine, BacktestResult
from nifty_trading.core.journal import JournalEntry, TradingJournal
from nifty_trading.core.paper import PaperExecutionEngine, PaperOrder, PaperOrderStatus
from nifty_trading.core.position import Position, PositionSide, PositionTracker
from nifty_trading.core.risk import RiskCheckResult, RiskLimits, RiskManager
from nifty_trading.core.strategy import (
    BaseStrategy,
    OrderType,
    Signal,
    SignalType,
    StrategyContext,
)

__all__ = [
    "BaseStrategy",
    "Signal",
    "SignalType",
    "OrderType",
    "StrategyContext",
    "BacktestConfig",
    "BacktestResult",
    "BacktestEngine",
    "PaperExecutionEngine",
    "PaperOrder",
    "PaperOrderStatus",
    "Position",
    "PositionSide",
    "PositionTracker",
    "RiskLimits",
    "RiskCheckResult",
    "RiskManager",
    "JournalEntry",
    "TradingJournal",
]

