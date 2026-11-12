"""Plain data structures for ORB V2 (no logic)."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass(frozen=True)
class Level:
    """A previous-day support/resistance level or zone. ``floor <= ceiling``; a single price has floor == ceiling."""
    side: str                   # RESISTANCE | SUPPORT
    kind: str                   # MAJOR | INNER
    method: str                 # construction method id
    floor: float
    ceiling: float
    source_times: tuple[str, ...]  # start times of the previous-session 5-minute candles that define it
    evidence: str               # human-readable provenance

    @property
    def is_zone(self) -> bool:
        return self.ceiling - self.floor > 1e-9


@dataclass
class SessionData:
    """Everything known at/after 09:20 of one session (candles of the current day: only the opening candle)."""
    date: object
    day_minutes: pd.DataFrame            # all 1-minute rows of the day (executed AFTER 09:20 only, by execution.py)
    opening: dict                        # o,h,l,c of the 09:15-09:20 candle (aggregated from the five 1-minute rows)
    open_1m: float                       # first 1-minute open
    ema_now: float                       # EMA(200) of 5-minute closes including the opening candle
    ema_prev: float                      # EMA after the previous session's last candle
    prev_date: object
    prev_high: float
    prev_low: float
    prev_close: float                    # official daily close
    prev_close_source: str
    prev_last_5m_close: float
    prev_candles: pd.DataFrame           # previous session's 5-minute candles (continuous trading only)
    prev_ema_last: float                 # EMA at the previous session's last 5-minute candle
    prev_engulf_candle: dict | None
    flags: tuple[str, ...] = ()


@dataclass
class Decision:
    date: object
    config_id: str
    evaluable: bool
    not_evaluated_reason: str = ""
    signal: str = ""                     # BUY | SELL | ""
    failed: list = field(default_factory=list)
    detail: dict = field(default_factory=dict)
