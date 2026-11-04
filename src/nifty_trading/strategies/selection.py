"""Evaluation policies for repeated signals (Phase 2.2). NONE OF THEM IS A SOURCE RULE.

The IRF guide (and the other guides) never say how many trades per day are allowed, whether a failed setup may re-arm, or
whether a new signal may be taken while a position is open (``IRF-GLOBAL-004``). The engines therefore emit the COMPLETE
event log. These policies only decide which of those events a later simulation would take; they are labelled research
evaluation policies, are never chosen to match the report's trade count, and none is approved.

  ALL_VALID_SIGNALS            every confirmed, entry-executable signal
  FIRST_VALID_SIGNAL_PER_DAY   the earliest one per calendar day (and per strategy when several strategies are passed)
  ONE_ACTIVE_POSITION_AT_A_TIME a signal is skipped while an earlier accepted position is still open; the position's end time
                               comes from a caller-supplied function (typically the exit-policy simulation). An accepted position
                               that never closes (``None``) blocks the rest of that day and is reported, not hidden. The scope is one
                               (strategy, day): positions of different strategies never block each other. A signal whose entry cannot
                               be filled (``NO_POSITION``) is skipped with a reason and blocks nothing. Ties at one timestamp are ordered
                               by strategy then method name.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum

from nifty_trading.core.exit_policy import Bar, ExitResult, evaluate_exit, policy_for
from nifty_trading.strategies.base import SignalRecord, SignalStatus
from nifty_trading.strategies.params import DEFAULT_TRADE, TradeConfig
from nifty_trading.strategies.rules import implements

#: returned by a ``position_end`` function when the signal could not be filled at all (no position was ever opened)
NO_POSITION = object()


class SelectionPolicy(str, Enum):
    ALL_VALID_SIGNALS = "ALL_VALID_SIGNALS"
    FIRST_VALID_SIGNAL_PER_DAY = "FIRST_VALID_SIGNAL_PER_DAY"
    ONE_ACTIVE_POSITION_AT_A_TIME = "ONE_ACTIVE_POSITION_AT_A_TIME"


@dataclass
class Selection:
    policy: str
    accepted: list[SignalRecord] = field(default_factory=list)
    skipped: list[tuple[SignalRecord, str]] = field(default_factory=list)  # (record, reason)
    status: str = "RESEARCH_POLICY_NOT_APPROVED"


def is_valid(rec: SignalRecord) -> tuple[bool, str]:
    """A 'valid' event: CONFIRMED and its entry bar is fillable (not a closing-auction reference bar)."""
    if rec.signal_status != SignalStatus.CONFIRMED.value:
        return False, f"NOT_CONFIRMED({rec.signal_status})"
    st = rec.execution_config.get("execution_status", "RESEARCH_ONLY")
    if st.startswith("ENTRY_BLOCKED") or st.startswith("DIAGNOSTIC_ONLY"):
        return False, st
    return True, ""


@implements("EXE-SEL-001")
def apply_policy(records: Sequence[SignalRecord], policy: SelectionPolicy | str,
                 position_end: Callable[[SignalRecord], datetime | None] | None = None) -> Selection:
    """Select events under ``policy``. ``records`` may mix strategies; ordering is by signal timestamp (stable)."""
    pol = SelectionPolicy(policy)
    sel = Selection(pol.value)
    ordered = sorted(records, key=lambda r: (r.signal_timestamp is None, r.signal_timestamp or 0, r.strategy, r.method))
    busy_until: dict[tuple[str, date], datetime | None] = {}  # per (scope, day): when the open position ends; None = never
    taken_day: set[tuple[str, date]] = set()
    if pol is SelectionPolicy.ONE_ACTIVE_POSITION_AT_A_TIME and position_end is None:
        raise ValueError("ONE_ACTIVE_POSITION_AT_A_TIME needs a position_end function")
    for r in ordered:
        ok, why = is_valid(r)
        if not ok:
            sel.skipped.append((r, why))
            continue
        key = (r.strategy, r.signal_date)
        if pol is SelectionPolicy.ALL_VALID_SIGNALS:
            sel.accepted.append(r)
        elif pol is SelectionPolicy.FIRST_VALID_SIGNAL_PER_DAY:
            if key in taken_day:
                sel.skipped.append((r, "LATER_SIGNAL_SAME_DAY"))
            else:
                taken_day.add(key)
                sel.accepted.append(r)
        else:
            if key in busy_until:
                end = busy_until[key]
                if end is None:
                    sel.skipped.append((r, "EARLIER_POSITION_NEVER_CLOSED_THIS_SESSION(unresolved)"))
                    continue
                if r.signal_timestamp < end:
                    sel.skipped.append((r, f"POSITION_STILL_OPEN_UNTIL_{end:%H:%M}"))
                    continue
            end = position_end(r)
            if end is NO_POSITION:
                sel.skipped.append((r, "ENTRY_NOT_FILLABLE(no position opened)"))
                continue
            sel.accepted.append(r)
            busy_until[key] = end
    return sel


# ------------------------------------------------------------------ helpers that connect signals to the exit model
def fill_from_next_bar(day_bars: Sequence[Bar], signal_ts: datetime) -> tuple[float, list[Bar]] | None:
    """PROPOSED causal fill (EXE-FILL-001): the open of the first 1-minute bar that STARTS at/after the signal candle's end.
    Returns ``(entry_price, bars_from_that_bar_on)`` or None when that bar does not exist or is not executable (entry blocked)."""
    rest = sorted((b for b in day_bars if b.ts >= signal_ts), key=lambda b: b.ts)
    if not rest or rest[0].ts != signal_ts or not rest[0].executable:  # the exact next bar must exist: never fill at a later bar
        return None
    return rest[0].o, rest


def simulate_exit(rec: SignalRecord, day_bars: Sequence[Bar], trade: TradeConfig = DEFAULT_TRADE) -> ExitResult | None:
    """Exit simulation of one signal under the configured stops/targets; None when the entry cannot be filled."""
    f = fill_from_next_bar(day_bars, rec.signal_timestamp)
    if f is None:
        return None
    entry, bars = f
    ref = rec.reference_levels.get("recent_green_high")  # only the SOURCE_35_40_BY_DISTANCE research variant reads it
    pol = policy_for(rec.strategy, reference_price=ref, entry=entry, trade=trade)
    return evaluate_exit(rec.direction, entry, bars, pol, entry_at_first_bar_open=True)


def position_end_from_result(res: ExitResult | None):
    """When the position stops being open: the minute after the final exit bar; None if it is still open at the end of data;
    ``NO_POSITION`` when the entry could not be filled (``res is None``) or the policy was NOT_EVALUABLE."""
    if res is None or res.outcome.value == "NotEvaluable":
        return NO_POSITION
    if res.leg2_ts is None:
        return None
    return res.leg2_ts + timedelta(minutes=1)
