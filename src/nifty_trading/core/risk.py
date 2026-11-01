"""Pre-trade risk management, drawdown controls, and kill switches."""

from dataclasses import dataclass
from typing import Any

from nifty_trading.core.strategy import Signal


@dataclass
class RiskLimits:
    """Configurable risk boundaries."""
    max_daily_loss: float = 10000.0
    max_position_size: int = 1800  # 50 lots of NIFTY
    max_loss_per_trade: float = 2500.0
    max_open_orders: int = 10
    emergency_stop_triggered: bool = False


@dataclass
class RiskCheckResult:
    """Pre-trade evaluation result."""
    allowed: bool
    reason: str | None = None


class RiskManager:
    """Enforces pre-trade limits and portfolio-level circuit breakers."""

    def __init__(self, limits: RiskLimits | None = None):
        self.limits = limits or RiskLimits()
        self.current_daily_realized_loss: float = 0.0

    def evaluate_signal(self, signal: Signal, current_positions: list[Any]) -> RiskCheckResult:
        """Pre-trade risk evaluation."""
        if self.limits.emergency_stop_triggered:
            return RiskCheckResult(allowed=False, reason="Emergency kill-switch is active.")

        if self.current_daily_realized_loss >= self.limits.max_daily_loss:
            return RiskCheckResult(
                allowed=False,
                reason=f"Max daily loss limit exceeded: ₹{self.current_daily_realized_loss} >= ₹{self.limits.max_daily_loss}",
            )

        if signal.quantity > self.limits.max_position_size:
            return RiskCheckResult(
                allowed=False,
                reason=f"Order quantity {signal.quantity} exceeds max permitted position size {self.limits.max_position_size}",
            )

        return RiskCheckResult(allowed=True)

    def trigger_emergency_stop(self) -> None:
        """Immediately block all future orders."""
        self.limits.emergency_stop_triggered = True

