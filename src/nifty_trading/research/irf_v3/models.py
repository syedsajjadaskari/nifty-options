"""Plain data structures for IRF V3 (no logic)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

M1 = "IRF_V3_METHOD_1"
M2 = "IRF_V3_METHOD_2"


@dataclass(frozen=True)
class Candle:
    """A COMPLETE 5-minute candle. ``start`` = HH:MM label, ``end`` = start + 5 min = the earliest instant the candle may be used."""
    start: pd.Timestamp
    end: pd.Timestamp
    open: float
    high: float
    low: float
    close: float

    @property
    def is_red(self) -> bool:
        return self.close < self.open

    @property
    def is_green(self) -> bool:
        return self.close > self.open


@dataclass
class MethodTrace:
    """Everything one method state machine concluded for one session (signal or the reason there is none)."""
    method: str
    date: date
    status: str                                    # SIGNAL | NO_SIGNAL
    no_signal_reason: str = ""                     # set when status == NO_SIGNAL
    first_candle: Candle | None = None
    initial_range_high: float | None = None        # Level A (M2) / marked level (M1) - the first-candle high incl. wick
    initial_range_low: float | None = None
    reference_level: float | None = None           # M1: marked level; M2: Level B
    reference_candle: Candle | None = None         # M1: the first candle; M2: the first red candle of the rally
    breakout_candle: Candle | None = None          # M1: first close above the level; M2: first close above Level A
    second_breakout_candle: Candle | None = None   # M2 only: first close above Level B
    confirmation_candle: Candle | None = None      # the failure candle
    signal_time: pd.Timestamp | None = None        # == confirmation_candle.end (causal instant)
    failed_conditions: list = field(default_factory=list)   # milestones NOT reached (for NO_SIGNAL days)
    reached: list = field(default_factory=list)             # milestones reached, in order
    rule_ids: list = field(default_factory=list)
    ignored_red_before_breakout: int = 0           # M2: red candles that formed before the rally breakout
    later_cycles: int = 0                          # diagnostic: further completed cycles after the first signal (never traded: 1 trade/day)
    events: list = field(default_factory=list)     # chronological (timestamp, text)
