"""Strategy module interfaces and signal models for future rulebooks."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import pandas as pd


class SignalType(str, Enum):
    """Trading action types."""
    BUY = "BUY"
    SELL = "SELL"
    EXIT = "EXIT"
    HOLD = "HOLD"


class OrderType(str, Enum):
    """Order execution types."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"


@dataclass
class Signal:
    """Trading signal emitted by a strategy."""
    strategy_id: str
    instrument: str
    signal_type: SignalType
    timestamp: datetime
    price: float | None = None
    quantity: int = 1
    stop_loss: float | None = None
    target: float | None = None
    order_type: OrderType = OrderType.MARKET
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyContext:
    """Context passed to strategy during backtesting or live execution."""
    current_time: datetime
    current_candle: pd.Series
    historical_candles: pd.DataFrame
    current_positions: list[Any] = field(default_factory=list)
    available_capital: float = 0.0


class BaseStrategy(ABC):
    """Abstract base class for all NIFTY option strategies (IRF, ORB, PDR, PDS, RF)."""

    def __init__(self, name: str, params: dict[str, Any] | None = None):
        self.name = name
        self.params = params or {}
        self.is_active = True

    @abstractmethod
    def on_candle(self, context: StrategyContext) -> list[Signal]:
        """Evaluate strategy logic on incoming 1-minute candle and emit signals."""
        pass

    def on_order_fill(self, order: Any) -> None:  # noqa: B027
        """Callback invoked when an order associated with this strategy is filled."""
        pass
