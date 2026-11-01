"""Lightweight backtesting framework interface for strategy rulebook evaluation."""

from dataclasses import dataclass, field

import pandas as pd

from nifty_trading.core.strategy import BaseStrategy


@dataclass
class BacktestConfig:
    """Backtesting simulation configuration."""
    start_date: str
    end_date: str
    initial_capital: float = 500000.0  # ₹5 Lakhs default
    slippage_points: float = 0.5
    brokerage_per_order: float = 20.0  # 5paisa flat rate


@dataclass
class BacktestResult:
    """Performance metrics from backtest run."""
    strategy_name: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    net_pnl: float
    max_drawdown: float
    sharpe_ratio: float
    trades_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    equity_curve: pd.DataFrame = field(default_factory=pd.DataFrame)


class BacktestEngine:
    """Historical simulation engine executing strategies against 1-minute Parquet candles."""

    def __init__(self, config: BacktestConfig):
        self.config = config

    def run(self, strategy: BaseStrategy, candles_df: pd.DataFrame) -> BacktestResult:
        """Run backtest simulation over candles."""
        # Stub implementation ready for Phase 2 strategy rulebooks
        return BacktestResult(
            strategy_name=strategy.name,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate_pct=0.0,
            net_pnl=0.0,
            max_drawdown=0.0,
            sharpe_ratio=0.0,
        )
