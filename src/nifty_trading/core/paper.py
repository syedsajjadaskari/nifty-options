"""Paper execution engine completely decoupled from live broker order endpoints."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from nifty_trading.core.strategy import Signal, SignalType


class PaperOrderStatus(str, Enum):
    NEW = "NEW"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


@dataclass
class PaperOrder:
    order_id: str
    strategy_id: str
    instrument: str
    side: str
    quantity: int
    requested_price: float | None
    fill_price: float | None = None
    status: PaperOrderStatus = PaperOrderStatus.NEW
    created_at: datetime = field(default_factory=datetime.now)
    fill_time: datetime | None = None


class PaperExecutionEngine:
    """Simulates realistic order matching, fills, and slippage in paper mode."""

    def __init__(self, slippage_points: float = 0.5):
        self.slippage_points = slippage_points
        self.orders: list[PaperOrder] = []

    def execute_signal(self, signal: Signal, current_market_price: float) -> PaperOrder:
        order_id = str(uuid.uuid4())[:8]

        # Apply slippage
        if signal.signal_type == SignalType.BUY:
            fill_price = current_market_price + self.slippage_points
            side = "BUY"
        else:
            fill_price = max(0.05, current_market_price - self.slippage_points)
            side = "SELL"

        order = PaperOrder(
            order_id=order_id,
            strategy_id=signal.strategy_id,
            instrument=signal.instrument,
            side=side,
            quantity=signal.quantity,
            requested_price=signal.price or current_market_price,
            fill_price=fill_price,
            status=PaperOrderStatus.FILLED,
            fill_time=datetime.now(),
        )

        self.orders.append(order)
        return order
