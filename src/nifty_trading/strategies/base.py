"""Signal records, setup state machine and the BaseStrategy-compatible engine base class.

Signal detection only. A :class:`SignalRecord` is never a fill: it carries the candle on which the
documented trigger completed and a *reference* price (that candle's close). Stop/target/quantity
live in ``nifty_trading.core.exit_policy`` and are applied downstream.
"""

from __future__ import annotations

import math
from abc import abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any

import pandas as pd

from nifty_trading.core.execution_eligibility import classify_bar
from nifty_trading.core.strategy import BaseStrategy, Signal, SignalType, StrategyContext
from nifty_trading.data.sessions import SessionContext, build_session_contexts
from nifty_trading.strategies.definitions import Candle, to_candles
from nifty_trading.strategies.params import (
    DEFAULT_PROPOSALS,
    DEFAULT_TRADE,
    T2_CONFLICTS,
    ProposalConfig,
    TradeConfig,
)
from nifty_trading.strategies.rule_data import IMPL_P, IMPL_R, NOT, VE
from nifty_trading.strategies.rules import RULE_BY_ID, implements

INSTRUMENT = "NIFTY 50 (index, not directly tradable; points are synthetic)"


class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class SignalStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    INVALIDATED = "INVALIDATED"
    INCOMPLETE_AT_EOD = "INCOMPLETE_AT_EOD"
    NOT_EVALUATED = "NOT_EVALUATED"


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"  # every satisfied rule is VERIFIED_EXPLICIT; nothing unresolved
    PROPOSAL_DEPENDENT = "PROPOSAL_DEPENDENT"  # relies on a PROPOSED_FOR_REVIEW interpretation
    RESEARCH_VARIANT = "RESEARCH_VARIANT"  # relies on a rule the documents do not define (labelled variant)
    NOT_READY = "NOT_READY"  # could not be evaluated / blocked


class State(str, Enum):
    WAITING_FOR_SETUP = "WAITING_FOR_SETUP"
    SETUP_DETECTED = "SETUP_DETECTED"
    WAITING_FOR_CONFIRMATION = "WAITING_FOR_CONFIRMATION"
    SIGNAL_CONFIRMED = "SIGNAL_CONFIRMED"
    SETUP_INVALIDATED = "SETUP_INVALIDATED"


_ALLOWED = {
    State.WAITING_FOR_SETUP: {State.SETUP_DETECTED},
    State.SETUP_DETECTED: {State.WAITING_FOR_CONFIRMATION, State.SIGNAL_CONFIRMED, State.SETUP_INVALIDATED},
    State.WAITING_FOR_CONFIRMATION: {State.SIGNAL_CONFIRMED, State.SETUP_INVALIDATED},
    State.SIGNAL_CONFIRMED: set(),
    State.SETUP_INVALIDATED: set(),
}


class IllegalTransition(RuntimeError):
    pass


class SetupFSM:
    """One setup attempt. Chronology is enforced: transitions must not go backwards in time."""

    def __init__(self, label: str):
        self.label = label
        self.state = State.WAITING_FOR_SETUP
        self.trace: list[str] = []
        self._last_t: datetime | None = None

    def to(self, new: State, t: datetime, why: str) -> None:
        if new not in _ALLOWED[self.state]:
            raise IllegalTransition(f"{self.label}: {self.state.value} -> {new.value} ({why})")
        if self._last_t is not None and t < self._last_t:
            raise IllegalTransition(f"{self.label}: event at {t} precedes previous event at {self._last_t}")
        self._last_t = t
        self.trace.append(f"{t:%H:%M} {self.state.value}->{new.value}: {why}")
        self.state = new

    @property
    def terminal(self) -> bool:
        return self.state in (State.SIGNAL_CONFIRMED, State.SETUP_INVALIDATED)


@dataclass
class SignalRecord:
    strategy: str
    method: str
    direction: str
    signal_date: date
    signal_timestamp: datetime | None  # bar_end of the trigger candle = earliest actionable time
    signal_candle_start: datetime | None
    signal_candle_open: float | None
    signal_candle_high: float | None
    signal_candle_low: float | None
    signal_candle_close: float | None
    reference_levels: dict[str, Any]
    rule_ids_satisfied: list[str]
    rule_ids_failed: list[str]
    signal_status: str
    invalidation_reason: str | None
    verification_status: str  # for a record that is NOT a CONFIRMED signal this only describes the rules satisfied before the setup ended; it carries no signal meaning (see execution_config.entry_rule_status)
    rule_ids_unresolved: list[str] = field(default_factory=list)
    proposals_used: dict[str, Any] = field(default_factory=dict)
    state_trace: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    concurrent_methods: list[str] = field(default_factory=list)
    reference_price_is_fill: bool = False  # always False: a signal is not a filled trade
    instrument: str = INSTRUMENT
    execution_config: dict[str, Any] = field(default_factory=dict)  # which rule configuration produced this signal (Phase 2.2)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def verification_for(satisfied: list[str], unresolved: list[str]) -> VerificationStatus:
    """Never reports VERIFIED when any satisfied rule rests on a proposal or any mandatory rule is unresolved."""
    if any(RULE_BY_ID[r]["implementation_status"] == IMPL_R for r in list(satisfied) + list(unresolved)):
        return VerificationStatus.RESEARCH_VARIANT
    if unresolved:
        return VerificationStatus.PROPOSAL_DEPENDENT
    needs_proposal = any(
        RULE_BY_ID[r]["classification"] != VE or RULE_BY_ID[r]["implementation_status"] in (IMPL_P, NOT)
        for r in satisfied
    )
    return VerificationStatus.PROPOSAL_DEPENDENT if needs_proposal else VerificationStatus.VERIFIED


class SignalEngine(BaseStrategy):
    """Base class: ``evaluate_session`` -> structured signals; ``on_candle`` adapts to BaseStrategy."""

    STRATEGY = ""
    METHODS: tuple[str, ...] = ()
    REQUIRES_PREVIOUS_SESSION = False
    TREND_METHODS: tuple[str, ...] = ()  # methods that apply the trend_mode proposal ("*" = all); others report NOT_APPLICABLE

    def __init__(self, name: str | None = None, params: dict[str, Any] | None = None,
                 proposals: ProposalConfig | None = None, trade: TradeConfig | None = None):
        super().__init__(name or self.STRATEGY, params)
        self.p = proposals or DEFAULT_PROPOSALS
        self.trade = trade or DEFAULT_TRADE

    # ---------------------------------------------------------------- public API
    @implements("DATA-TIME-001")
    def evaluate_session(self, ctx: SessionContext) -> list[SignalRecord]:
        block = self._precheck(ctx)
        if block:
            return [self._blocked(ctx, block)]
        cs = to_candles(ctx.candles)
        if not cs:
            return [self._blocked(ctx, "NO_COMPLETE_5M_CANDLES")]
        gap_before = [False] + [cs[k].start != cs[k - 1].end for k in range(1, len(cs))]
        out = self._scan(ctx, cs, gap_before)
        cutoff = self.p.signal_window_end
        if cutoff:
            out = [r for r in out if r.signal_status != SignalStatus.CONFIRMED.value
                   or r.signal_timestamp is None or f"{r.signal_timestamp:%H:%M}" <= cutoff]
        self._mark_concurrent(out)
        return out

    @abstractmethod
    def _scan(self, ctx: SessionContext, cs: list[Candle], gap_before: list[bool]) -> list[SignalRecord]: ...

    # ---------------------------------------------------------------- helpers
    @implements("DATA-QUAL-001")
    def _precheck(self, ctx: SessionContext) -> str | None:
        if not ctx.info.usable:
            return f"SESSION_NOT_EVALUABLE:{ctx.info.quality.value}:{ctx.info.status.value}" + (
                f"({'; '.join(ctx.info.reasons)})" if ctx.info.reasons else "")
        if self.REQUIRES_PREVIOUS_SESSION:
            if ctx.previous is None:
                return "NO_PREVIOUS_SESSION_IN_DATASET"
            if ctx.previous.gap_to_this_session_unverified and not self.p.allow_unverified_prev_session:
                why = "; ".join(f for f in ctx.data_flags if f.startswith("PREV")) or "previous session not verifiable"
                return f"PREV_SESSION_UNVERIFIED({why})"
        return None

    def exec_config(self, method: str, status: str, execution: str, signal_ts: datetime | None = None) -> dict[str, Any]:
        """The rule configuration that produced a signal. Never says VERIFIED just because some components are verified:
        ``entry_rule_status`` is VERIFIED_EXPLICIT only when every satisfied rule is explicit and nothing is unresolved."""
        t, st = self.trade, self.STRATEGY
        uses_trend = "*" in self.TREND_METHODS or method in self.TREND_METHODS
        return {
            "strategy": st, "method": method, "entry_rule_status": status,
            "stop_distance": t.stop_points(st), "stop_variant": t.stop_variant, "stop_status": t.stop_status(st) if t.stop_points(st) is not None else "UNRESOLVED",
            "target_1": t.t1_points, "target_2": t.t2_points(st), "target_2_status": t.t2_status(st),
            "target_2_conflict": T2_CONFLICTS.get(st),
            "proposal_config": self.p.to_dict(),  # every PROPOSED_FOR_REVIEW setting in force: two signals under different settings are distinguishable
            "trade_config": asdict(t),
            "trend_mode": self.p.trend_mode if uses_trend else "NOT_APPLICABLE",
            "fill_convention": "NEXT_1M_BAR_OPEN_AFTER_SIGNAL_CANDLE (PROPOSED; the reference price is not a fill)",
            "execution_status": execution,
        }

    def _execution_status(self, signal_ts: datetime | None) -> str:
        if signal_ts is None:
            return "NOT_EVALUATED"
        return "RESEARCH_ONLY" if classify_bar(signal_ts).value == "CONTINUOUS" else "ENTRY_BLOCKED_" + classify_bar(signal_ts).value

    def _blocked(self, ctx: SessionContext, reason: str, method: str = "ALL") -> SignalRecord:
        return SignalRecord(
            strategy=self.STRATEGY, method=method, direction=self._default_direction(), signal_date=ctx.date,
            signal_timestamp=None, signal_candle_start=None, signal_candle_open=None, signal_candle_high=None,
            signal_candle_low=None, signal_candle_close=None, reference_levels={}, rule_ids_satisfied=[],
            rule_ids_failed=[], signal_status=SignalStatus.NOT_EVALUATED.value, invalidation_reason=reason,
            verification_status=VerificationStatus.NOT_READY.value, flags=list(ctx.data_flags),
            execution_config=self.exec_config(method, VerificationStatus.NOT_READY.value, "NOT_EVALUATED"),
        )

    def _default_direction(self) -> str:
        return Direction.SHORT.value

    def _rec(self, ctx: SessionContext, c: Candle, method: str, direction: Direction, levels: dict[str, Any],
             satisfied: list[str], failed: list[str] | None = None, unresolved: list[str] | None = None,
             status: SignalStatus = SignalStatus.CONFIRMED, why: str | None = None,
             trace: list[str] | None = None, proposals: dict[str, Any] | None = None,
             flags: list[str] | None = None) -> SignalRecord:
        unresolved = unresolved or []
        sat = list(dict.fromkeys(satisfied))
        if status is SignalStatus.CONFIRMED:
            ver = verification_for(sat, unresolved)
        else:
            ver = VerificationStatus.NOT_READY if status is SignalStatus.NOT_EVALUATED else verification_for(sat, unresolved)
        return SignalRecord(
            strategy=self.STRATEGY, method=method, direction=direction.value, signal_date=ctx.date,
            signal_timestamp=c.end, signal_candle_start=c.start, signal_candle_open=c.o, signal_candle_high=c.h,
            signal_candle_low=c.l, signal_candle_close=c.c, reference_levels=_clean(levels),
            rule_ids_satisfied=sat, rule_ids_failed=failed or [], signal_status=status.value,
            invalidation_reason=why, verification_status=ver.value, rule_ids_unresolved=unresolved,
            proposals_used=proposals or {}, state_trace=trace or [], flags=list(ctx.data_flags) + (flags or []),
            execution_config=self.exec_config(
                method, ({"VERIFIED": "VERIFIED_EXPLICIT"}.get(ver.value, ver.value) if status is SignalStatus.CONFIRMED else "NOT_A_CONFIRMED_SIGNAL"),
                self._execution_status(c.end) if status is SignalStatus.CONFIRMED else "NOT_A_CONFIRMED_SIGNAL"),
        )

    @staticmethod
    def _mark_concurrent(recs: list[SignalRecord]) -> None:
        confirmed = [r for r in recs if r.signal_status == SignalStatus.CONFIRMED.value]
        for r in confirmed:
            r.concurrent_methods = sorted(o.method for o in confirmed
                                          if o is not r and o.signal_timestamp == r.signal_timestamp
                                          and o.direction == r.direction)

    # ---------------------------------------------------------------- BaseStrategy adapter
    def on_candle(self, context: StrategyContext) -> list[Signal]:
        """Emit newly confirmed signals when the 1-minute row just received completes a 5m candle.

        ``historical_candles`` must hold 1-minute rows up to and including ``current_time`` only;
        rows after ``current_time`` are discarded here as a look-ahead guard. This adapter rebuilds
        contexts from history and is meant for correctness, not speed.
        """
        hist = context.historical_candles
        now = pd.Timestamp(context.current_time)
        hist = hist[hist["timestamp"] <= now]
        minute_of_day = now.hour * 60 + now.minute
        if (minute_of_day - (9 * 60 + 15)) % 5 != 4:
            return []
        ctxs, _ = build_session_contexts(hist)
        today = now.date()
        if today not in ctxs:
            return []
        bar_end = now + pd.Timedelta(minutes=1)
        out: list[Signal] = []
        for r in self.evaluate_session(ctxs[today]):
            if r.signal_status == SignalStatus.CONFIRMED.value and r.signal_timestamp == bar_end:
                out.append(Signal(
                    strategy_id=self.name, instrument="NIFTY 50", timestamp=r.signal_timestamp,
                    signal_type=SignalType.SELL if r.direction == Direction.SHORT.value else SignalType.BUY,
                    price=r.signal_candle_close, stop_loss=None, target=None, metadata=r.to_dict(),
                ))
        return out


def _clean(d: dict[str, Any]) -> dict[str, Any]:
    return {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in d.items()}
