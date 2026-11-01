"""Position tracking and portfolio state models."""

from dataclasses import dataclass
from enum import Enum


class PositionSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


@dataclass
class Position:
    """Represents an active or closed position in an instrument."""
    instrument: str
    side: PositionSide
    quantity: int
    average_entry_price: float
    current_market_price: float = 0.0
    realized_pnl: float = 0.0

    @property
    def unrealized_pnl(self) -> float:
        if self.side == PositionSide.LONG:
            return (self.current_market_price - self.average_entry_price) * self.quantity
        elif self.side == PositionSide.SHORT:
            return (self.average_entry_price - self.current_market_price) * self.quantity
        return 0.0


class PositionTracker:
    """Tracks active positions across all strategies."""

    def __init__(self):
        self._positions: dict[str, Position] = {}

    def get_position(self, instrument: str) -> Position:
        return self._positions.get(
            instrument,
            Position(instrument=instrument, side=PositionSide.FLAT, quantity=0, average_entry_price=0.0),
        )

    def update_price(self, instrument: str, price: float) -> None:
        if instrument in self._positions:
            self._positions[instrument].current_market_price = price

    def record_fill(self, instrument: str, side: PositionSide, qty: int, price: float) -> None:
        pos = self.get_position(instrument)
        if pos.side == PositionSide.FLAT:
            self._positions[instrument] = Position(
                instrument=instrument,
                side=side,
                quantity=qty,
                average_entry_price=price,
                current_market_price=price,
            )
        elif pos.side == side:
            # Add to position
            new_qty = pos.quantity + qty
            new_avg = ((pos.average_entry_price * pos.quantity) + (price * qty)) / new_qty
            pos.quantity = new_qty
            pos.average_entry_price = new_avg
            pos.current_market_price = price
        else:
            # Reduce or reverse position
            if qty <= pos.quantity:
                pnl = (price - pos.average_entry_price) * qty if pos.side == PositionSide.LONG else (pos.average_entry_price - price) * qty
                pos.realized_pnl += pnl
                pos.quantity -= qty
                if pos.quantity == 0:
                    pos.side = PositionSide.FLAT
            else:
                # Reversal
                remaining = qty - pos.quantity
                pnl = (price - pos.average_entry_price) * pos.quantity if pos.side == PositionSide.LONG else (pos.average_entry_price - price) * pos.quantity
                pos.realized_pnl += pnl
                pos.side = side
                pos.quantity = remaining
                pos.average_entry_price = price
                pos.current_market_price = price

