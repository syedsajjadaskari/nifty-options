"""NIFTY 50 index-price signal engines (Phase 2). Signal detection only: no orders, no fills."""

from nifty_trading.strategies.base import (
    Direction,
    SignalEngine,
    SignalRecord,
    SignalStatus,
    VerificationStatus,
)
from nifty_trading.strategies.irf import IRFStrategy
from nifty_trading.strategies.orb import ORBStrategy
from nifty_trading.strategies.params import DEFAULT_PROPOSALS, RF_TARGET_STATUS, ProposalConfig
from nifty_trading.strategies.pdr import PDRStrategy
from nifty_trading.strategies.pds import PDSStrategy
from nifty_trading.strategies.rf import RFStrategy

ALL_STRATEGIES = (IRFStrategy, ORBStrategy, PDRStrategy, PDSStrategy, RFStrategy)

__all__ = [
    "ALL_STRATEGIES", "DEFAULT_PROPOSALS", "Direction", "IRFStrategy", "ORBStrategy", "PDRStrategy", "PDSStrategy",
    "ProposalConfig", "RFStrategy", "RF_TARGET_STATUS", "SignalEngine", "SignalRecord", "SignalStatus",
    "VerificationStatus",
]
