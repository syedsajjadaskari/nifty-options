"""Shared portfolio-level trading-day controller (Phase 2.3, USER_APPROVED rules).

The five strategy engines stay exactly as they are: they emit signals. THIS module decides which signal becomes a trade, in strict
chronological order, for the whole day:

  * the FIRST valid signal of any strategy opens the first trade (SEL-FIRST-001);
  * while a position is active every later signal is ignored for execution and kept in a diagnostic log (SEL-ACTIVE-001);
  * signals of different strategies (or opposite directions) at the same timestamp are a logged CONFLICT; no strategy is chosen unless a
    TieBreakPolicy explicitly marked ``approved`` is configured (SEL-TIE-001/002) - otherwise the day is UNRESOLVED_EXECUTION;
  * first trade -> Target 2: the day is finished (DAY-T2-001); first trade -> Target 1 then the post-T1 buffer stop: finished (DAY-BUF-001);
  * first trade -> ORIGINAL full stop before Target 1: ONE more trade, only PDR or PDS, only from a signal confirmed after the first
    position has fully closed - an earlier ignored signal is never reused (DAY-SL-001, DAY-NOREUSE-001);
  * first trade closed by end of day / unresolved execution / not evaluable: no second trade (DAY-UNRES-001);
  * at most 2 entries per day (DAY-MAX-001); no entry with a fill later than 13:00:00 IST (ENTRY-CUTOFF-001).

It consumes signal records and 1-minute bars of ONE session and returns the trades and the complete diagnostic log. It does not
download, place orders or run a profitability backtest; the P&L it carries is synthetic index-point P&L of the exit model.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import date, datetime, time
from enum import Enum
from zoneinfo import ZoneInfo

from nifty_trading.core.execution_eligibility import ENTRY_CUTOFF, entry_within_cutoff
from nifty_trading.core.exit_policy import Bar, ExitResult, TradeOutcome
from nifty_trading.strategies.base import SignalRecord, SignalStatus
from nifty_trading.strategies.params import DEFAULT_TRADE, TradeConfig
from nifty_trading.strategies.rules import implements
from nifty_trading.strategies.selection import (
    NO_POSITION,
    fill_from_next_bar,
    is_valid,
    position_end_from_result,
    simulate_exit,
)

IST = ZoneInfo("Asia/Kolkata")


class DayState(str, Enum):
    READY_FOR_FIRST_TRADE = "READY_FOR_FIRST_TRADE"
    FIRST_TRADE_ACTIVE = "FIRST_TRADE_ACTIVE"
    SECOND_TRADE_ELIGIBLE = "SECOND_TRADE_ELIGIBLE"
    SECOND_TRADE_ACTIVE = "SECOND_TRADE_ACTIVE"
    DAY_FINISHED = "DAY_FINISHED"
    UNRESOLVED_EXECUTION = "UNRESOLVED_EXECUTION"


@dataclass(frozen=True)
class TieBreakPolicy:
    """Priority between strategies that signal at the same timestamp. ``approved`` must be True to be applied: NO such policy is approved
    today, so the default ``DayRules.tie_break`` is None. (Tests use a policy marked approved only to exercise the machinery.)"""

    priority: tuple[str, ...]
    approved: bool = False
    source: str = ""


@dataclass(frozen=True)
class DayRules:
    entry_cutoff: time = ENTRY_CUTOFF
    max_entries: int = 2
    second_trade_strategies: tuple[str, ...] = ("PDR", "PDS")
    tie_break: TieBreakPolicy | None = None
    # What an UNRESOLVED same-minute collision does. MARK_DAY_UNRESOLVED (default, the Phase 2.3/3.0 convention): no trade and the day ends.
    # SKIP_COLLISION_EVENT_CONTINUE_DAY: a DIAGNOSTIC counterfactual (Phase 3.1) - the colliding signals are skipped, the conflict is logged and later
    # signals may still trade. Neither is an approved policy.
    collision_policy: str = "MARK_DAY_UNRESOLVED"

    def __post_init__(self) -> None:
        if self.collision_policy not in ("MARK_DAY_UNRESOLVED", "SKIP_COLLISION_EVENT_CONTINUE_DAY"):
            raise ValueError(f"collision_policy={self.collision_policy!r}")


@dataclass
class DiagnosticEntry:
    timestamp: datetime | None
    strategy: str
    method: str
    direction: str
    event: str  # IGNORED | REJECTED | CONFLICT | NOTE
    reason: str


@dataclass
class TradeRecord:
    trade_no: int
    signal: SignalRecord
    fill_timestamp: datetime
    entry_price: float
    result: ExitResult
    classification: str  # TARGET | T1_THEN_BUFFER_STOP | INITIAL_FULL_STOP | BREAKEVEN(legacy) | INCOMPLETE_EOD | NOT_EVALUABLE
    position_end: object  # datetime | None (never closed) - NO_POSITION cannot occur for an accepted trade
    concurrent_methods: list[str] = field(default_factory=list)


@dataclass
class DayResult:
    day: date
    final_state: DayState
    trades: list[TradeRecord] = field(default_factory=list)
    diagnostics: list[DiagnosticEntry] = field(default_factory=list)
    state_trace: list[str] = field(default_factory=list)

    @property
    def conflicts(self) -> list[DiagnosticEntry]:
        return [d for d in self.diagnostics if d.event == "CONFLICT"]

    def reasons(self) -> list[str]:
        return [d.reason for d in self.diagnostics]


_CLASS = {TradeOutcome.TARGET: "TARGET", TradeOutcome.T1_THEN_BUFFER_STOP: "T1_THEN_BUFFER_STOP", TradeOutcome.INITIAL_FULL_STOP: "INITIAL_FULL_STOP",
          TradeOutcome.BREAKEVEN: "BREAKEVEN", TradeOutcome.FORCED_EXIT: "FORCED_EXIT", TradeOutcome.INCOMPLETE_EOD: "INCOMPLETE_EOD", TradeOutcome.NOT_EVALUABLE: "NOT_EVALUABLE"}


@implements("SEL-FIRST-001", "SEL-ACTIVE-001", "SEL-TIE-001", "SEL-TIE-002", "SEL-TIE-003", "DAY-T2-001", "DAY-BUF-001", "DAY-SL-001", "DAY-NOREUSE-001",
            "DAY-UNRES-001", "DAY-MAX-001", "ENTRY-CUTOFF-001")
def run_trading_day(day: date, records: Sequence[SignalRecord], day_bars: Sequence[Bar], trade: TradeConfig = DEFAULT_TRADE,
                    rules: DayRules | None = None) -> DayResult:
    """Run the state machine over one session. ``records`` may mix all five strategies; only CONFIRMED ones are considered.
    ``day_bars`` are the session's 1-minute bars (with their ``executable`` flags). Deterministic and causal: a decision at time t
    reads only signals confirmed at or before t and bars from the fill bar onwards (the exit model walks forward from the fill)."""
    rules = rules or DayRules()
    res = DayResult(day, DayState.READY_FOR_FIRST_TRADE)
    state = DayState.READY_FOR_FIRST_TRADE
    res.state_trace.append(f"{state.value} (start of day)")

    def set_state(new: DayState, why: str, ts=None) -> DayState:
        stamp = f"{ts:%H:%M} " if ts is not None else ""
        res.state_trace.append(f"{stamp}{state.value} -> {new.value}: {why}")
        return new

    def log(ts, r: SignalRecord, event: str, reason: str) -> None:
        res.diagnostics.append(DiagnosticEntry(ts, r.strategy, r.method, r.direction, event, reason))

    usable: list[SignalRecord] = []
    for r in records:
        if r.signal_status != SignalStatus.CONFIRMED.value or r.signal_timestamp is None:
            continue
        if r.signal_date != day:  # a record of another session must never leak into this day
            log(r.signal_timestamp, r, "REJECTED", f"RECORD_FOR_ANOTHER_DAY({r.signal_date})")
            continue
        if r.signal_timestamp.tzinfo is None:  # a naive timestamp is exchange (IST) wall-clock time
            r = replace(r, signal_timestamp=r.signal_timestamp.replace(tzinfo=IST))
        usable.append(r)
    confirmed = sorted(usable, key=lambda r: (r.signal_timestamp, r.strategy, r.method))
    groups: list[tuple[datetime, list[SignalRecord]]] = []
    for r in confirmed:
        if groups and groups[-1][0] == r.signal_timestamp:
            groups[-1][1].append(r)
        else:
            groups.append((r.signal_timestamp, [r]))

    active: TradeRecord | None = None

    def settle(at: datetime | None) -> None:
        """The active position has closed (or the data ended): move to the state its outcome dictates."""
        nonlocal state, active
        assert active is not None
        cls = active.classification
        first = active.trade_no == 1
        if cls in ("TARGET", "T1_THEN_BUFFER_STOP", "BREAKEVEN", "FORCED_EXIT"):
            new, why = DayState.DAY_FINISHED, f"first trade {cls}" if first else f"second trade {cls}"
        elif cls == "INITIAL_FULL_STOP":
            new, why = (DayState.SECOND_TRADE_ELIGIBLE, "first trade INITIAL_FULL_STOP: one PDR/PDS trade allowed") if first else (
                DayState.DAY_FINISHED, "second trade INITIAL_FULL_STOP")
        else:  # INCOMPLETE_EOD / NOT_EVALUABLE
            new, why = DayState.UNRESOLVED_EXECUTION, f"trade {active.trade_no} {cls}: exit unresolved (nothing is invented)"
        state = set_state(new, why, at)
        active = None

    for ts, recs in groups:
        # 1) a position that has closed by now settles first
        if active is not None and active.position_end is not None and ts >= active.position_end:
            settle(active.position_end)
        # 2) terminal states and active positions only log
        if state in (DayState.DAY_FINISHED, DayState.UNRESOLVED_EXECUTION):
            for r in recs:
                log(ts, r, "IGNORED", "DAY_FINISHED" if state is DayState.DAY_FINISHED else "DAY_UNRESOLVED_EXECUTION")
            continue
        if state in (DayState.FIRST_TRADE_ACTIVE, DayState.SECOND_TRADE_ACTIVE):
            for r in recs:
                log(ts, r, "IGNORED", "POSITION_ACTIVE (signal kept for diagnostics only; never reused)")
            continue
        # 3) READY_FOR_FIRST_TRADE or SECOND_TRADE_ELIGIBLE: look for an executable candidate
        second = state is DayState.SECOND_TRADE_ELIGIBLE
        cands: list[SignalRecord] = []
        for r in recs:
            if second and r.strategy not in rules.second_trade_strategies:
                log(ts, r, "REJECTED", "SECOND_TRADE_RESTRICTED_TO_" + "_".join(rules.second_trade_strategies))
                continue
            ok, why = is_valid(r)
            if not ok:
                log(ts, r, "REJECTED", why)
                continue
            if not entry_within_cutoff(ts, rules.entry_cutoff):
                log(ts, r, "REJECTED", f"ENTRY_CUTOFF_EXCEEDED(fill {ts:%H:%M} IST > {rules.entry_cutoff:%H:%M})")
                continue
            if fill_from_next_bar(day_bars, ts) is None:
                log(ts, r, "REJECTED", "ENTRY_NOT_FILLABLE(no fillable bar starts at the signal candle's end)")
                continue
            cands.append(r)
        if not cands:
            continue
        chosen, concurrent = _choose(cands, rules, ts, res, log)
        if chosen is None:  # unresolved collision
            if rules.collision_policy == "SKIP_COLLISION_EVENT_CONTINUE_DAY":
                res.state_trace.append(f"{ts:%H}:{ts:%M} {state.value}: collision skipped, day continues (diagnostic counterfactual policy)")
                continue
            state = set_state(DayState.UNRESOLVED_EXECUTION, "simultaneous signals without an approved tie-break policy", ts)
            continue
        for r in cands:
            if r is not chosen and r.strategy == chosen.strategy and r.direction == chosen.direction:
                log(ts, r, "NOTE", f"SAME_STRATEGY_CONCURRENT_METHOD (traded as {chosen.method}; identical entry/stop/target)")
        sim = simulate_exit(chosen, day_bars, trade)
        assert sim is not None  # fill_from_next_bar succeeded above
        fill = fill_from_next_bar(day_bars, ts)
        end = position_end_from_result(sim)
        if end is NO_POSITION:  # NOT_EVALUABLE exit policy: the entry happened but its exit cannot be simulated -> unresolved, never closes
            end = None
        no = len(res.trades) + 1
        if no > rules.max_entries:  # defensive: the state machine already prevents it
            log(ts, chosen, "REJECTED", "MAX_ENTRIES_PER_DAY")
            continue
        tr = TradeRecord(no, chosen, ts, fill[0], sim, _CLASS[sim.outcome], end, concurrent)
        res.trades.append(tr)
        active = tr
        state = set_state(DayState.SECOND_TRADE_ACTIVE if second else DayState.FIRST_TRADE_ACTIVE,
                          f"{chosen.strategy} {chosen.method} {chosen.direction} entered at {fill[0]}", ts)

    # end of the signal list: the last position resolves
    if active is not None:
        settle(active.position_end)
    res.final_state = state
    return res


def _choose(cands: list[SignalRecord], rules: DayRules, ts, res: DayResult, log) -> tuple[SignalRecord | None, list[str]]:
    """One candidate, or several of the same strategy and direction (identical trade): that trade. Otherwise a conflict."""
    strategies = {r.strategy for r in cands}
    directions = {r.direction for r in cands}
    if len(strategies) == 1 and len(directions) == 1:
        first = cands[0]
        return first, [r.method for r in cands[1:]]
    detail = ", ".join(f"{r.strategy}/{r.method}/{r.direction}" for r in cands)
    pol = rules.tie_break
    if pol is not None and pol.approved:
        for name in pol.priority:
            hit = [r for r in cands if r.strategy == name]
            if hit:
                if len({r.direction for r in hit}) > 1:  # the winner itself signals both ways at once: still a conflict, never method-name order
                    break
                for r in cands:
                    if r is not hit[0]:
                        log(ts, r, "IGNORED", f"LOST_APPROVED_TIE_BREAK_TO_{name}")
                res.diagnostics.append(DiagnosticEntry(ts, name, hit[0].method, hit[0].direction, "NOTE", f"TIE_BREAK_APPLIED({pol.source or 'approved policy'}): {detail}"))
                return hit[0], []
    res.diagnostics.append(DiagnosticEntry(ts, "+".join(sorted(strategies)), "ALL", "+".join(sorted(directions)), "CONFLICT",
                                           f"SIMULTANEOUS_SIGNAL_CONFLICT_UNRESOLVED: {detail}"))
    return None, []
