"""Unit tests for Phase 1 core architecture interfaces (strategy, risk, paper, position, journal)."""

from datetime import datetime

import pandas as pd

from nifty_trading.core.journal import JournalEntry, TradingJournal
from nifty_trading.core.paper import PaperExecutionEngine, PaperOrderStatus
from nifty_trading.core.position import PositionSide, PositionTracker
from nifty_trading.core.risk import RiskLimits, RiskManager
from nifty_trading.core.strategy import BaseStrategy, Signal, SignalType, StrategyContext


class DummyStrategy(BaseStrategy):
    """Test strategy implementation."""
    def on_candle(self, context: StrategyContext) -> list[Signal]:
        return [
            Signal(
                strategy_id=self.name,
                instrument="NIFTY",
                signal_type=SignalType.BUY,
                timestamp=context.current_time,
                price=float(context.current_candle["close"]),
                quantity=50,
            )
        ]


def test_strategy_and_context_interface():
    strategy = DummyStrategy("TEST_ORB")
    candle_series = pd.Series({"open": 24500.0, "high": 24550.0, "low": 24490.0, "close": 24540.0})
    ctx = StrategyContext(
        current_time=datetime.now(),
        current_candle=candle_series,
        historical_candles=pd.DataFrame(),
    )
    signals = strategy.on_candle(ctx)
    assert len(signals) == 1
    assert signals[0].signal_type == SignalType.BUY
    assert signals[0].price == 24540.0


def test_risk_manager_limits():
    risk = RiskManager(limits=RiskLimits(max_daily_loss=5000.0, max_position_size=100))
    valid_sig = Signal(
        strategy_id="TEST",
        instrument="NIFTY",
        signal_type=SignalType.BUY,
        timestamp=datetime.now(),
        quantity=50,
    )
    res = risk.evaluate_signal(valid_sig, [])
    assert res.allowed is True

    # Oversized order
    oversized_sig = Signal(
        strategy_id="TEST",
        instrument="NIFTY",
        signal_type=SignalType.BUY,
        timestamp=datetime.now(),
        quantity=500,
    )
    res2 = risk.evaluate_signal(oversized_sig, [])
    assert res2.allowed is False
    assert "exceeds max permitted position size" in res2.reason

    # Emergency kill-switch
    risk.trigger_emergency_stop()
    res3 = risk.evaluate_signal(valid_sig, [])
    assert res3.allowed is False
    assert "Emergency kill-switch is active" in res3.reason


def test_paper_execution_and_position_tracker():
    paper = PaperExecutionEngine(slippage_points=0.5)
    tracker = PositionTracker()

    sig = Signal(
        strategy_id="TEST",
        instrument="NIFTY_CE",
        signal_type=SignalType.BUY,
        timestamp=datetime.now(),
        quantity=50,
        price=120.0,
    )
    order = paper.execute_signal(sig, current_market_price=120.0)
    assert order.status == PaperOrderStatus.FILLED
    assert order.fill_price == 120.5  # Includes 0.5 slippage

    tracker.record_fill("NIFTY_CE", PositionSide.LONG, 50, order.fill_price)
    pos = tracker.get_position("NIFTY_CE")
    assert pos.quantity == 50
    assert pos.average_entry_price == 120.5

    # Update market price and check unrealized PnL
    tracker.update_price("NIFTY_CE", 130.5)
    assert pos.unrealized_pnl == (130.5 - 120.5) * 50  # +500.0


def test_trading_journal():
    journal = TradingJournal()
    entry = JournalEntry(
        entry_id="trade_1",
        timestamp=datetime.now().isoformat(),
        strategy_name="ORB",
        instrument="NIFTY_24500_CE",
        side="BUY",
        quantity=50,
        entry_price=120.0,
        exit_price=135.0,
        realized_pnl=750.0,
        rationale="15-min range breakout",
    )
    journal.record_trade(entry)
    df = journal.to_dataframe()
    assert len(df) == 1
    assert df["realized_pnl"].iloc[0] == 750.0
