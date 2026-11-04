"""Execution-eligibility layer: which index observations may be treated as fillable.

The historical NIFTY 50 candles are market DATA and are never altered. Whether a simulated order may FILL on a
given observation is a separate question. From 2026-08-03 NSE runs a Closing Auction Session: continuous trading in the
index constituents ends at 15:15, the index does not move continuously during the auction and the official close appears
when it completes (see ``data_repair_report.md``). Those 15:15-15:29 observations are real index prints but are
reference values, not prices at which an order could have been executed.

Convention (PROPOSED, ``phase22_execution_policy.md``):
  * ``CONTINUOUS``                 fillable.
  * ``CLOSING_AUCTION_REFERENCE``  NOT fillable: on closing-auction days, bars starting 15:15 up to (excluding) 15:30.
  * ``POST_CLOSE``                 NOT fillable: bars starting at/after 15:30 (closing-print stub and later).
  * ``SPECIAL_SESSION_NONSTANDARD`` NOT fillable: special sessions the calendar marks as non-standard hours (Muhurat).
  * ``NON_TRADING``                NOT fillable: confirmed holidays, weekends without a special session, pre-open bars.
The exact auction matching mechanics are not modelled and no closing price is invented: a position that is still open when
the auction starts is reported as unresolved for explicit treatment in Phase 3.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, time
from enum import Enum
from functools import lru_cache
from zoneinfo import ZoneInfo

from nifty_trading.data.market_calendar import MarketCalendar, load_market_calendar

IST = ZoneInfo("Asia/Kolkata")
SESSION_OPEN = time(9, 15)
AUCTION_REGIME_DATE = date(2026, 8, 3)  # NSE Closing Auction Session start; a calendar without the regime must not be used after it
ENTRY_CUTOFF = time(13, 0)  # USER_APPROVED (Phase 2.3): strict, inclusive of 13:00:00 itself; evaluated in IST
REGULAR_CLOSE = time(15, 30)  # bars labelled >= this are the closing-print stub / post-close rows


@lru_cache(maxsize=1)
def _default_calendar() -> MarketCalendar:
    return load_market_calendar()


def _cal(calendar: MarketCalendar | None) -> MarketCalendar:
    return calendar if calendar is not None else _default_calendar()


class BarEligibility(str, Enum):
    CONTINUOUS = "CONTINUOUS"
    CLOSING_AUCTION_REFERENCE = "CLOSING_AUCTION_REFERENCE"
    POST_CLOSE = "POST_CLOSE"
    SPECIAL_SESSION_NONSTANDARD = "SPECIAL_SESSION_NONSTANDARD"
    NON_TRADING = "NON_TRADING"


def classify_bar(start: datetime, calendar: MarketCalendar | None = None) -> BarEligibility:
    """Eligibility of the 1-minute bar labelled ``start`` (naive or tz-aware; only the wall-clock date and time are used)."""
    cal = _cal(calendar)
    if start.tzinfo is not None:  # the rules are in exchange (IST) wall-clock time
        start = start.astimezone(IST)
    d, t = start.date(), start.time()
    if cal.closing_auction is None and d >= AUCTION_REGIME_DATE:
        raise RuntimeError("closing-auction calendar missing: refusing to classify post-2026-08-03 bars (they would silently count as fillable)")
    if cal.is_confirmed_holiday(d):
        return BarEligibility.NON_TRADING
    special = cal.special_sessions.get(d)
    if special is not None and not special.evaluable_by_strategies:
        return BarEligibility.SPECIAL_SESSION_NONSTANDARD
    if d.weekday() >= 5 and special is None:
        return BarEligibility.NON_TRADING
    if t < SESSION_OPEN:
        return BarEligibility.NON_TRADING
    if t >= REGULAR_CLOSE:
        return BarEligibility.POST_CLOSE
    ca = cal.closing_auction
    if ca is not None and ca.applies(d) and t >= ca.frozen_start:
        return BarEligibility.CLOSING_AUCTION_REFERENCE
    return BarEligibility.CONTINUOUS


def is_executable(start: datetime, calendar: MarketCalendar | None = None) -> bool:
    return classify_bar(start, calendar) is BarEligibility.CONTINUOUS


def entry_executable(signal_timestamp: datetime, calendar: MarketCalendar | None = None) -> bool:
    """A signal confirmed at ``signal_timestamp`` (= its candle's end) can only be acted on from the NEXT 1-minute bar,
    which starts at that timestamp. If that bar is not fillable the entry is blocked (no auction fill is invented)."""
    return is_executable(signal_timestamp, calendar)


def eligibility_summary(starts: Iterable[datetime], calendar: MarketCalendar | None = None) -> dict[str, int]:
    cal = _cal(calendar)
    out: dict[str, int] = {}
    for s in starts:
        k = classify_bar(s, cal).value
        out[k] = out.get(k, 0) + 1
    return out


def session_has_auction(d: date, calendar: MarketCalendar | None = None) -> bool:
    cal = _cal(calendar)
    return cal.closing_auction is not None and cal.closing_auction.applies(d)


def bars_from_frame(df, calendar: MarketCalendar | None = None) -> list:
    """Convert 1-minute rows (columns timestamp/open/high/low/close, label = bar start) into exit-policy ``Bar`` objects whose
    ``executable`` flag comes from :func:`classify_bar`. The data itself is never altered."""
    from nifty_trading.core.exit_policy import (
        Bar,  # local import: exit_policy does not depend on this module
    )

    cal = _cal(calendar)
    out = []
    for r in df.sort_values("timestamp").itertuples(index=False):
        k = classify_bar(r.timestamp, cal)
        out.append(Bar(r.timestamp, float(r.open), float(r.high), float(r.low), float(r.close), k is BarEligibility.CONTINUOUS, k.value))
    return out


def entry_within_cutoff(fill_start: datetime, cutoff: time = ENTRY_CUTOFF) -> bool:
    """ENTRY-CUTOFF-001: a fill at ``fill_start`` (the START of the 1-minute bar whose open is the fill) is eligible only if its exchange
    (Asia/Kolkata) clock time is not later than ``cutoff``. A naive timestamp is taken to be IST already; an aware one is converted,
    so the machine's timezone never matters."""
    if fill_start.tzinfo is not None:
        fill_start = fill_start.astimezone(IST)
    return fill_start.time() <= cutoff
