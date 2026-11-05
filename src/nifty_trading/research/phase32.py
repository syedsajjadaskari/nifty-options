"""Phase 3.2: a fully explainable view of the Phase 3.0 baseline - for every executed trade the setup, the numerical evidence behind each entry
condition, the portfolio selection, the exit of both legs and the comparison with the manual journal.

READ-ONLY with respect to trading logic. The engines, the controller and the exit model are not touched: the baseline is re-run through the very same
code path as Phase 3.0 and every explanation is computed from (a) the signal record the engine returned (levels, rule ids, state trace, extra fields),
(b) the same definition functions the engine calls (``strategies/definitions.py``) with the same ``ProposalConfig``, and (c) the raw 1-minute bars.
Every recomputed number is cross-checked against the value the engine stored on its record; a disagreement is reported as a ``FAIL`` of that check
(``RECOMPUTATION_MISMATCH``), never silently adjusted. A condition the engine does NOT test is reported as such (``UNRESOLVED``), never as passed.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from nifty_trading.core.execution_eligibility import ENTRY_CUTOFF, entry_within_cutoff
from nifty_trading.core.exit_policy import Bar, select_stop_distance
from nifty_trading.research.phase3 import ledger_row
from nifty_trading.strategies.base import SignalRecord
from nifty_trading.strategies.definitions import (
    EPS,
    Candle,
    bearish_pin,
    bullish_pin,
    compression_ok,
    confirmed_swing_highs,
    confirmed_swing_lows,
    gap_info,
    is_green,
    is_red,
    is_small,
    lower_rejection,
    lower_wick,
    pdr_zone,
    pds_zone,
    pivot_highs,
    pivot_lows,
    prev_candles,
    prev_high_low,
    recent_resistance,
    recent_support,
    strong_bearish,
    strong_bullish,
    to_candles,
    trend_check,
    upper_rejection,
    upper_wick,
    wick_share_outside,
)
from nifty_trading.strategies.params import ProposalConfig, TradeConfig
from nifty_trading.strategies.pdr_body import PDR_BODY_RULES, PDRBodyConfig, body_high
from nifty_trading.strategies.pdr_body import build_zone as build_body_zone
from nifty_trading.strategies.pdr_revised import (
    PDR_REVISION_RULES,
    PDRRevisionConfig,
    build_zone,
    build_zone_b,
    classify_confirmation,
)
from nifty_trading.strategies.rules import RULE_BY_ID
from nifty_trading.strategies.trading_day import TradeRecord

RESULTS = ("PASS", "FAIL", "NOT_APPLICABLE", "UNRESOLVED")
# the Phase 3.4 revision rules (PDR-A01 ...) are not in the Phase 2 registry; they carry their own statuses
PDR_REV_STATUS = {r["rule_id"]: r["status"] for r in PDR_REVISION_RULES}
PDR_REV_STATUS["PDR-A04x"] = "PROPOSED_FOR_REVIEW"  # disclosure row of the provisional parameters
PDR_REV_STATUS.update({r["rule_id"]: r["status"] for r in PDR_BODY_RULES})  # Phase 3.6 body-based rules (PDR-B..), disjoint ids
PDR_REV_STATUS["PDR-B04x"] = "PROPOSED_FOR_REVIEW"
PDR_REV_DEFINITION = {"SOURCE_VERIFIED": "SOURCE_VERIFIED_IN_THE_GUIDE", "AUTHOR_APPROVED": "AUTHOR_STATEMENT_NUMERIC_DETAILS_ARE_SEPARATE_PROPOSED_ROWS", "OWNER_INTERPRETATION": "OWNER_INTERPRETATION_OF_AUTHOR_WORDS",
                      "PROPOSED_FOR_REVIEW": "NUMERIC_DEFINITION_PROPOSED_FOR_REVIEW", "USER_APPROVED": "USER_APPROVED", "PRESERVED_FROM_PHASE2": "PRESERVED_FROM_PHASE2"}
STATUS_MAP = {"VERIFIED_EXPLICIT": "SOURCE_VERIFIED", "VERIFIED_QUALITATIVE": "SOURCE_VERIFIED", "USER_APPROVED": "USER_APPROVED",
              "PROPOSED_FOR_REVIEW": "PROPOSED_FOR_REVIEW", "CONFLICTING": "CONFLICTING", "UNRESOLVED": "UNRESOLVED"}
STRATEGY_ORDER = ("IRF", "ORB", "PDR", "PDS", "RF")
HEADLINE_COST = (500.0, 0.5)  # illustrative net P&L: Rs 500 per trade + 0.5 index point adverse on every fill (the Phase 3.0 headline assumption)


def px(x: float | None, nd: int = 2) -> str:
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:,.{nd}f}"


def hm(ts: datetime | None) -> str:
    return "" if ts is None else f"{ts:%H:%M}"


def rule_status(rule_id: str) -> str:
    if rule_id in PDR_REV_STATUS:
        return PDR_REV_STATUS[rule_id]
    r = RULE_BY_ID.get(rule_id)
    return "NOT_A_RULE" if r is None else STATUS_MAP[r["classification"]]


def definition_status(rule_id: str) -> str:
    """What kind of numerical definition the code uses for this rule (the source wording may be qualitative)."""
    if rule_id in PDR_REV_STATUS:
        return PDR_REV_DEFINITION[PDR_REV_STATUS[rule_id]]
    r = RULE_BY_ID.get(rule_id)
    if r is None:
        return "NOT_A_REGISTRY_RULE"
    c, impl = r["classification"], r["implementation_status"]
    if c == "VERIFIED_EXPLICIT":
        return "EXPLICIT_IN_SOURCE" if impl in ("IMPLEMENTED_VERIFIED", "SPECIFICATION_ONLY") else "EXPLICIT_WORDING_DETAIL_PROPOSED_FOR_REVIEW"
    if c == "VERIFIED_QUALITATIVE":
        return "QUALITATIVE_SOURCE_NUMERIC_DEFINITION_PROPOSED_FOR_REVIEW"
    return STATUS_MAP[c]


def rule_source(rule_id: str) -> str:
    if rule_id in PDR_REV_STATUS:
        body = next((x for x in PDR_BODY_RULES if x["rule_id"] == rule_id), None)
        if body is not None:
            return "PDR body-based rules (Phase 3.6): " + body["source"]
        if rule_id.startswith("PDR-B"):  # the PDR-B04x disclosure row
            return "PDR body-based rules (Phase 3.6): disclosure of the provisional parameters"
        return "PDR revision rules (Phase 3.4): " + next((x["source"] for x in PDR_REVISION_RULES if x["rule_id"] == rule_id), "disclosure of the provisional parameters")
    r = RULE_BY_ID.get(rule_id)
    if r is None:
        return "(not a registry rule)"
    page = r["source_page"]
    return f"{r['source_document']}" + (f" p.{page}" if page and page != "n/a" else "")


# ====================================================================================================== candle geometry
def candle_metrics(c: Candle, p: ProposalConfig) -> dict[str, Any]:
    """Every number the prompt asks for, from the same definitions the engine uses. Zero-range candle: ratios are undefined (None); the engine's convention
    is that every ratio is 0 and no strong/pin shape qualifies, while ``is_small`` is True."""
    rng_ = c.h - c.l
    body_ = abs(c.c - c.o)
    uw, lw = upper_wick(c), lower_wick(c)
    zero = rng_ <= 0.0

    def pct(x: float) -> float | None:
        return None if zero else 100.0 * x / rng_
    wick_to_body_bear = None if body_ <= EPS else uw / body_
    wick_to_body_bull = None if body_ <= EPS else lw / body_
    return {
        "open": c.o, "high": c.h, "low": c.l, "close": c.c, "range": rng_, "body": body_, "body_pct": pct(body_),
        "upper_wick": uw, "upper_wick_pct": pct(uw), "lower_wick": lw, "lower_wick_pct": pct(lw),
        "direction": "BULLISH" if c.c > c.o else ("BEARISH" if c.c < c.o else "DOJI"), "zero_range": zero,
        "ema200_5m": None if math.isnan(c.ema) else c.ema,
        "close_position_from_low_pct": pct(c.c - c.l), "close_position_from_high_pct": pct(c.h - c.c),
        "bearish_pin_wick_to_body": wick_to_body_bear, "bullish_pin_wick_to_body": wick_to_body_bull,
        "strong_bullish": bool(strong_bullish(c, p)), "strong_bearish": bool(strong_bearish(c, p)),
        "bullish_pin": bool(bullish_pin(c, p)), "bearish_pin": bool(bearish_pin(c, p)), "small_body_le_30pct": bool(is_small(c, p)),
    }


def orb_route_text(c0: Candle, p: ProposalConfig, long: bool) -> tuple[str, bool]:
    """Which candle-quality route admitted an ORB candle: the strong-body test, or the conditional pin-bar alternative. Returns (sentence, pin_route_used)."""
    m = candle_metrics(c0, p)
    thr = p.strong
    strong = strong_bullish(c0, p) if long else strong_bearish(c0, p)
    opp = m["upper_wick_pct"] if long else m["lower_wick_pct"]
    body_txt = f"its body occupied {m['body_pct']:.2f}% of its range and its {'upper' if long else 'lower'} wick {opp:.2f}% (thresholds {thr['body_ratio_min'] * 100:g}% / {thr['opposite_wick_ratio_max'] * 100:g}%)"
    if strong:
        return f"{body_txt}: the strong-{'bullish' if long else 'bearish'} candle test passed", False
    wick = m["lower_wick"] if long else m["upper_wick"]
    ratio = m["bullish_pin_wick_to_body"] if long else m["bearish_pin_wick_to_body"]
    close_pos = m["close_position_from_high_pct"] if long else m["close_position_from_low_pct"]
    knife = ratio is not None and abs(ratio - p.pin["wick_to_body_min"]) < 0.005
    colour = m["direction"].lower()
    odd = (long and m["direction"] != "BULLISH") or ((not long) and m["direction"] != "BEARISH")
    return (f"{body_txt}: the strong-candle test FAILED; the candle was admitted through the conditional PIN-BAR alternative instead (the {'lower' if long else 'upper'} wick {wick:.2f} points is "
            f"{'undefined' if ratio is None else f'{ratio:.2f}'} x the body, required {p.pin['wick_to_body_min']:g}x{' - an exact-threshold pass' if knife else ''}; the close is {close_pos:.2f}% of the range from the "
            f"{'high' if long else 'low'}, allowed {p.pin['close_fraction_max'] * 100:g}%)" + (f". Note: the candle is {colour}, i.e. against the trade direction; the pin route accepts it because the level break and close beyond it carry the direction" if odd else "")), True


def _fid(ex: "Explanation", rule_ids: tuple[str, ...], pin_used: bool) -> None:
    for c in ex.checks:
        if c.rule_id in rule_ids and c.group == "CONFIRMATION":
            c.source_fidelity = "PIN_BAR_ROUTE_USED (strong-candle test failed)" if pin_used else "PROXY_FOR_QUALITATIVE_SOURCE"


def describe_candle(c: Candle, p: ProposalConfig) -> str:
    m = candle_metrics(c, p)

    def f(v):
        return "undefined (zero-range candle)" if v is None else f"{v:.2f}%"
    return (f"{hm(c.start)}-{hm(c.end)} O {px(c.o)} H {px(c.h)} L {px(c.l)} C {px(c.c)}; range {px(m['range'])}, body {px(m['body'])} ({f(m['body_pct'])}), "
            f"upper wick {px(m['upper_wick'])} ({f(m['upper_wick_pct'])}), lower wick {px(m['lower_wick'])} ({f(m['lower_wick_pct'])}), {m['direction'].lower()}")


# ====================================================================================================== checks
@dataclass
class Check:
    trade_id: str
    seq: int
    group: str  # SELECTION | SETUP | TREND | ZONE | CONFIRMATION | EXECUTION | NOTE
    rule_id: str
    rule_name: str
    source: str
    calculation: str
    observed: str
    required: str
    result: str  # PASS | FAIL | NOT_APPLICABLE | UNRESOLVED
    rule_status: str
    definition_status: str
    available_at: str
    why_it_matters: str
    candle_roles: str = ""
    source_fidelity: str = ""  # how the engine's reading compares with the source wording: FAITHFUL / ENGINE_RELAXES_SOURCE / ENGINE_STRICTER_THAN_SOURCE / PROXY_FOR_QUALITATIVE_SOURCE / ... (blank = not assessed)


@dataclass
class CandleRef:
    role: str
    candle: Candle
    session: str  # TODAY | PREVIOUS
    used_for: str


@dataclass
class Explanation:
    trade_id: str
    checks: list[Check] = field(default_factory=list)
    candles: list[CandleRef] = field(default_factory=list)
    setup_summary: str = ""
    selection_summary: str = ""
    unresolved: list[str] = field(default_factory=list)
    mismatches: list[str] = field(default_factory=list)
    levels: dict[str, Any] = field(default_factory=dict)  # for the charts: named levels / zones recomputed from the engine's definitions

    def add(self, group: str, rule_id: str, calculation: str, observed: str, required: str, result: str, available_at: datetime | str | None, why: str,
            candles: str = "", name: str | None = None, fidelity: str = "") -> Check:
        assert result in RESULTS, result
        r = RULE_BY_ID.get(rule_id)
        ch = Check(self.trade_id, len(self.checks) + 1, group, rule_id,
                   name or (r["description"] if r else rule_id), rule_source(rule_id), calculation, observed, required, result,
                   rule_status(rule_id), definition_status(rule_id), available_at if isinstance(available_at, str) else (f"{available_at:%Y-%m-%d %H:%M}" if available_at else ""),
                   why, candles, fidelity)
        self.checks.append(ch)
        if result == "UNRESOLVED":
            self.unresolved.append(f"{rule_id}: {name or ch.rule_name[:80]}")
        if result == "FAIL":
            self.mismatches.append(f"{rule_id}: {observed}")
        return ch

    def ref(self, role: str, candle: Candle, used_for: str, session: str = "TODAY") -> str:
        for r in self.candles:
            if r.role == role:
                return role
        self.candles.append(CandleRef(role, candle, session, used_for))
        return role


def _close(a: float | None, b: float | None, tol: float = 1e-6) -> bool:
    return a is not None and b is not None and abs(a - b) <= tol


def trade_id_of(day, tr: TradeRecord) -> str:
    return f"{day:%Y%m%d}-{tr.trade_no}-{tr.signal.strategy}"


def config_id(proposals: ProposalConfig, trade: TradeConfig, label: str = "baseline", pdr_revision: Any = None) -> str:
    import hashlib
    import json
    d = {"p": proposals.to_dict(), "t": asdict(trade)}
    if pdr_revision is not None:  # only the revised-PDR scenario adds a key, so every earlier configuration id is unchanged
        d["pdr_revision"] = asdict(pdr_revision)
    blob = json.dumps(d, sort_keys=True, default=str)
    return f"CFG-{label}-{hashlib.sha256(blob.encode()).hexdigest()[:10]}"


# ====================================================================================================== shared context
@dataclass
class DayInputs:
    day: Any
    ctx: Any
    cs: list[Candle]
    records: list[SignalRecord]
    result: Any  # DayResult
    bars: list[Bar]
    proposals: ProposalConfig
    trade: TradeConfig

    def idx(self, start) -> int:
        for k, c in enumerate(self.cs):
            if c.start == start:
                return k
        raise KeyError(start)

    def idx_by_end_label(self, label: str) -> int:
        for k, c in enumerate(self.cs):
            if hm(c.end) == label:
                return k
        raise KeyError(label)


def trace_time(rec: SignalRecord, token: str) -> str | None:
    """HH:MM stamp of the first state-trace line containing ``token`` (the engine's own record of when a transition happened)."""
    for line in rec.state_trace:
        if token in line:
            return line.split(" ", 1)[0]
    return None


def prev_cs(inp: DayInputs) -> list[Candle]:
    return to_candles(prev_candles(inp.ctx.previous, inp.proposals))


# ====================================================================================================== selection and execution checks (all strategies)
def explain_selection(inp: DayInputs, tr: TradeRecord, ex: Explanation) -> None:
    sig = tr.signal
    ts = sig.signal_timestamp
    confirmed = sorted((r for r in inp.records if r.signal_status == "CONFIRMED" and r.signal_timestamp is not None), key=lambda r: (r.signal_timestamp, r.strategy, r.method))
    earlier = [r for r in confirmed if r.signal_timestamp < ts]
    same = [r for r in confirmed if r.signal_timestamp == ts and r is not sig]
    diag = {(d.timestamp, d.strategy, d.method, d.direction): d for d in inp.result.diagnostics}

    def label(r):
        d = diag.get((r.signal_timestamp, r.strategy, r.method, r.direction))
        return f"{r.strategy} {r.method} {r.direction} @{hm(r.signal_timestamp)}" + (f" [{d.event}: {d.reason.split(' (')[0]}]" if d else "")
    if tr.trade_no == 1:
        unexecuted_earlier = [r for r in earlier if diag.get((r.signal_timestamp, r.strategy, r.method, r.direction)) is not None
                              and diag[(r.signal_timestamp, r.strategy, r.method, r.direction)].event in ("REJECTED", "CONFLICT")]
        ok = len(earlier) == len(unexecuted_earlier)
        ex.add("SELECTION", "SEL-FIRST-001", "earliest CONFIRMED signal of the day across IRF/ORB/PDR/PDS/RF that passed the controller's checks",
               (f"{len(earlier)} confirmed signal(s) earlier today" + (": " + "; ".join(label(r) for r in earlier) if earlier else "") +
                f"; {len(confirmed)} confirmed signals in the day in total, this one at {hm(ts)}"), "no earlier executable signal", "PASS" if ok else "FAIL", ts,
               "the shared controller trades only the first valid signal; the five strategies are not independent positions")
        ex.add("SELECTION", "SEL-TIE-001", "other CONFIRMED signals with exactly the same confirmation timestamp",
               ("none" if not same else "; ".join(label(r) for r in same)) + (f"; merged same-strategy methods: {', '.join(tr.concurrent_methods)}" if tr.concurrent_methods else ""),
               "no different-strategy / opposite-direction signal in the same minute (otherwise an unresolved conflict, no trade)",
               "PASS" if not any(r.strategy != sig.strategy or r.direction != sig.direction for r in same) else "FAIL", ts,
               "an unresolved same-minute collision would have produced no trade at all")
    else:
        first = next(t for t in inp.result.trades if t.trade_no == 1)
        end = first.position_end
        ok2 = first.classification == "INITIAL_FULL_STOP" and sig.strategy in ("PDR", "PDS") and end is not None and ts >= end
        ex.add("SELECTION", "DAY-SL-001", "first trade outcome, strategy of this signal, position-close time vs this signal's timestamp",
               f"first trade {first.signal.strategy} {first.signal.method} closed as {first.classification} at {hm(first.result.leg2_ts)}; position free from {hm(end)}; "
               f"this {sig.strategy} signal confirmed {hm(ts)}", "first trade INITIAL_FULL_STOP before Target 1, and a NEWLY confirmed PDR/PDS signal after the first position closed",
               "PASS" if ok2 else "FAIL", ts, "the only way a second trade is allowed")
        ignored_during = [r for r in confirmed if first.fill_timestamp <= r.signal_timestamp < (end or ts) and r is not sig]
        ex.add("SELECTION", "DAY-NOREUSE-001", "signals confirmed while the first position was open",
               f"{len(ignored_during)} signal(s) were ignored during the first trade (never reused)" + (": " + "; ".join(label(r) for r in ignored_during[:6]) if ignored_during else ""),
               "this trade comes from a signal confirmed after the first exit, not from an ignored one", "PASS" if ts >= (end or ts) else "FAIL", ts,
               "an ignored signal can never become the second trade")
    fill_bar = next((b for b in inp.bars if b.ts == tr.fill_timestamp), None)
    ex.add("SELECTION", "ENTRY-CUTOFF-001", "fill timestamp vs 13:00:00 IST",
           f"signal confirmed {hm(ts)}; fill {hm(tr.fill_timestamp)}", "fill at or before 13:00:00 IST",
           "PASS" if entry_within_cutoff(tr.fill_timestamp, ENTRY_CUTOFF) else "FAIL", tr.fill_timestamp, "no new position may be entered with a fill after 13:00 IST")
    ex.add("SELECTION", "EXE-FILL-001", "fill = open of the 1-minute bar that starts at the signal candle's end",
           (f"bar {hm(fill_bar.ts)} O {px(fill_bar.o)} H {px(fill_bar.h)} L {px(fill_bar.l)} C {px(fill_bar.c)}; executable={fill_bar.executable}; entry {px(tr.entry_price)}"
            if fill_bar else "fill bar not found"), "fill bar exists, starts exactly at the signal end, is fillable; entry = its open",
           "PASS" if fill_bar and fill_bar.executable and _close(fill_bar.o, tr.entry_price) and fill_bar.ts == ts else "FAIL", tr.fill_timestamp,
           "a 5-minute signal is known only when its candle closes; the first price that can be traded is the next minute's open")
    ex.add("SELECTION", "DAY-MAX-001", "number of entries today", f"trade {tr.trade_no} of at most 2", "<= 2 entries per day", "PASS" if tr.trade_no <= 2 else "FAIL", ts,
           "daily trade cap")
    def other_engines() -> str:
        parts = []
        for st in STRATEGY_ORDER:
            if st == sig.strategy:
                continue
            seen = [r for r in inp.records if r.strategy == st and r.signal_candle_start is not None and r.signal_candle_start < ts]
            conf = [r for r in seen if r.signal_status == "CONFIRMED" and r.signal_timestamp <= ts]
            bad = {}
            for r in seen:
                if r.signal_status in ("INVALIDATED", "NOT_EVALUATED"):
                    bad.setdefault(f"{r.method} {r.signal_status.lower()} at {hm(r.signal_candle_start)}: {(r.invalidation_reason or '')[:70]}", 1)
            if conf:
                parts.append(f"{st}: {len(conf)} confirmed signal(s) up to this time ({', '.join(f'{r.method}@{hm(r.signal_timestamp)}' for r in conf)})")
            elif bad:
                parts.append(f"{st}: " + "; ".join(list(bad)[:2]))
            else:
                parts.append(f"{st}: no setup record before this time (a base condition was not met, or nothing triggered)")
        return " ".join(f"[{x}]" for x in parts)
    others = [r for r in confirmed if r is not sig and r.signal_timestamp > ts]
    by_strat = {}
    for r in others:
        by_strat[r.strategy] = by_strat.get(r.strategy, 0) + 1
    if tr.trade_no == 1:
        ex.selection_summary = (f"This {sig.strategy if sig.method == sig.strategy else f'{sig.strategy} {sig.method}'} signal was the earliest executable signal of the day: {len(earlier)} confirmed signal(s) earlier"
                                + (f" ({'; '.join(label(r) for r in earlier)})" if earlier else "") + f", {len(same)} other in the same minute. "
                                + (f"{len(others)} later confirmed signal(s) ({', '.join(f'{k} x{v}' for k, v in sorted(by_strat.items()))}) are logged as ignored or rejected." if others else "No later signal was generated.")
                                + " State of the other four engines at that moment: " + other_engines())
    else:
        first = next(t for t in inp.result.trades if t.trade_no == 1)
        ex.selection_summary = (f"The first trade ({first.signal.strategy} {first.signal.method}) was stopped out before Target 1 at {hm(first.result.leg2_ts)}; this newly confirmed {sig.strategy} signal at {hm(ts)} is the "
                                f"first PDR/PDS signal after that exit, so it is the day's permitted second trade. State of the other engines at that moment: " + other_engines())


def explain_execution_levels(inp: DayInputs, tr: TradeRecord, ex: Explanation) -> None:
    sig, r = tr.signal, tr.result
    long = sig.direction == "LONG"
    sgn = 1 if long else -1
    st = sig.strategy
    stop_pts = inp.trade.stop_points(st)
    t2_pts = inp.trade.t2_points(st)
    stop_rule = "ORB-GLOBAL-003" if st == "ORB" else "EXE-STOP-001"
    ex.add("EXECUTION", stop_rule, f"initial stop = entry {'-' if long else '+'} {stop_pts:g} points",
           f"entry {px(tr.entry_price)} -> stop {px(r.stop_level)}", f"stop {stop_pts:g} index points ({inp.trade.stop_variant})",
           "PASS" if _close(r.stop_level, tr.entry_price - sgn * stop_pts) else "FAIL", tr.fill_timestamp,
           "defines the loss if the setup fails before Target 1")
    if st in ("IRF", "PDS"):
        ref = sig.reference_levels.get("recent_green_high")
        implied = select_stop_distance(tr.entry_price, ref) if ref is not None else None
        ex.add("NOTE", "IRF-SL-001" if st == "IRF" else "PDS-SL-001", "the guide's 35-or-40 rule: 35 if the most recent green candle's high is within 35 points of entry, else 40",
               (f"most recent green candle high {px(ref)} is {px(abs(ref - tr.entry_price))} points from the entry {px(tr.entry_price)}: the guide's rule would select {implied:g} points; "
                f"the baseline applies a fixed {stop_pts:g} (USER_APPROVED research baseline; the 35-vs-40 selection and the 40-point variant are separate labelled scenarios)") if implied is not None else "no green candle reference recorded",
               "source selection rule", "NOT_APPLICABLE", tr.fill_timestamp, "the stop distance is a modelling choice and changes losses, not entries", name="35/40 stop selection (not applied in the baseline)",
               fidelity=("SOURCE_RULE_WOULD_SELECT_40 (baseline uses 35)" if implied == 40 else "SOURCE_RULE_WOULD_SELECT_35 (same as the baseline)") if implied is not None else "")
    elif st == "PDR":
        ex.add("NOTE", "PDR-009", "stop 35 or 40 'depending on the situation'", f"the guide gives no selection rule; baseline fixed {stop_pts:g} points", "unresolved in the source", "UNRESOLVED", tr.fill_timestamp,
               "PDR stop selection is left to the owner", name="PDR stop selection rule is not defined")
    ex.add("EXECUTION", "EXE-T1-001", "Target 1 = entry +/- 27 points", f"T1 {px(r.t1_level)}", "27 points",
           "PASS" if _close(r.t1_level, tr.entry_price + sgn * inp.trade.t1_points) else "FAIL", tr.fill_timestamp, "Leg 1 (3 lots) is booked at Target 1")
    t2_rule = {"IRF": "IRF-TGT-001", "ORB": "ORB-GLOBAL-003", "PDR": "PDR-008", "PDS": "PDS-TGT-001", "RF": "RF-011"}[st]
    res = "PASS" if _close(r.t2_level, tr.entry_price + sgn * (t2_pts or 0)) else "FAIL"
    if st == "RF" and res == "PASS":
        res = "UNRESOLVED"  # the RF target is a research proposal, not in the source
    note = {"PDR": " (the guide says 70; the performance report's winners suggest 60 - CONFLICTING, recorded)", "PDS": " (the guide says 70; the report suggests 60 - CONFLICTING)",
            "RF": " (the RF guide leaves the target OPEN: 60 is a research proposal)"}.get(st, "")
    ex.add("EXECUTION", t2_rule, f"Target 2 = entry +/- {t2_pts:g} points", f"T2 {px(r.t2_level)}{note}", f"{t2_pts:g} points", res, tr.fill_timestamp,
           "Leg 2 (3 lots) is booked at Target 2", fidelity={"PDR": "SOURCE_70_CONFLICTS_WITH_REPORT_60", "PDS": "SOURCE_70_CONFLICTS_WITH_REPORT_60", "RF": "RESEARCH_PROPOSAL_NOT_IN_SOURCE"}.get(st, ""))
    ex.add("EXECUTION", "POST-T1-STOP-006", f"after T1 the Leg-2 stop = entry {'-' if long else '+'} 6 (no trailing)",
           f"post-T1 stop {px(r.post_t1_stop_level if r.post_t1_stop_level is not None else tr.entry_price - sgn * inp.trade.post_t1_buffer_points)}",
           "entry -6 (LONG) / +6 (SHORT)", "PASS", tr.fill_timestamp, "protects the remaining three lots once the first three are booked")
    ex.add("EXECUTION", "SIZE-LOT-001", "6 lots x 65 = 390, Leg 1 = 3 lots = 195, Leg 2 = 195", f"{inp.trade.total_lots} lots, lot size {inp.trade.lot_size}, legs {inp.trade.leg1_lots}+{inp.trade.total_lots - inp.trade.leg1_lots}",
           "6 lots in two equal legs", "PASS", tr.fill_timestamp, "position size for the synthetic P&L")
    # execution status of the entry rule itself (what the signal depends on)
    unres = ", ".join(sig.rule_ids_unresolved) or "none"
    ex.add("NOTE", "NOTE-UNRESOLVED-DEPENDENCIES", "rules the signal depends on that the sources leave unresolved", f"engine-recorded unresolved rule ids: {unres}; verification status {sig.verification_status}",
           "n/a (disclosure)", "UNRESOLVED" if sig.rule_ids_unresolved else "NOT_APPLICABLE", ex_ts(sig), "the entry is only as verified as the rules it rests on",
           name="Disclosure of unresolved source rules behind this signal")


def ex_ts(sig: SignalRecord):
    return sig.signal_timestamp


# ====================================================================================================== trend / gap helpers shared by ORB, RF
def explain_trend(inp: DayInputs, ex: Explanation, direction: str, rule_ids: tuple[str, str], strategy: str) -> bool | None:
    """EMA(200) trend of the active research variant, from PREVIOUS-session information. Returns the engine's trend_check result."""
    p, ctx = inp.proposals, inp.ctx
    t = trend_check(ctx, 0, direction, p.trend_mode, p)
    pcs = prev_cs(inp)
    mode = p.trend_mode
    if mode in ("EMA_PREV_SESSION_CLOSE", "STRUCTURE_EMA_SWING2") and pcs:
        last = pcs[-1]
        ex.ref("prev_session_last_candle", last, "trend: previous session's last 5-minute close vs its EMA(200)", "PREVIOUS")
        dist = last.c - last.ema
        side = "above" if dist > 0 else "below"
        req = "close > EMA(200)" if direction == "LONG" else "close < EMA(200)"
        ok = (last.c > last.ema) if direction == "LONG" else (last.c < last.ema)
        label = "bullish" if direction == "LONG" else "bearish"
        ex.add("TREND", rule_ids[0], "previous session's final completed 5-minute candle: close vs its EMA(200 of 5-minute closes)",
               f"previous session {ctx.previous.date} last candle {hm(last.start)}-{hm(last.end)} close {px(last.c)} vs EMA(200) {px(last.ema)}: {px(abs(dist))} points {side} the EMA "
               f"-> trend {label if ok else 'not ' + label} ({mode}; research variant {'A, EMA-only' if mode == 'EMA_PREV_SESSION_CLOSE' else 'B, EMA + confirmed swings'})",
               req, "PASS" if ok else "FAIL", f"{last.end:%Y-%m-%d %H:%M}",
               "the opening gap can never create the trend: only information that existed before today's open is used", "prev_session_last_candle",
               fidelity="EMA_ONLY_PROXY (the sources say the EMA is a basic filter, never the sole proof of a trend)" if mode == "EMA_PREV_SESSION_CLOSE" else "PROXY_FOR_QUALITATIVE_SOURCE")
        if not _close(t.ma_value, last.ema):
            ex.mismatches.append(f"{rule_ids[0]}: engine EMA {t.ma_value} vs recomputed {last.ema}")
        if strategy == "ORB":
            ex.add("TREND", rule_ids[1], "price location versus the 200 EMA is the basic confirmation; structure is only 'supporting'",
                   f"{px(abs(dist))} points {side} the EMA(200) on the previous session's last 5-minute close; swing structure "
                   + ("checked below (variant B)" if mode == "STRUCTURE_EMA_SWING2" else "not used in variant A"), "price on the trend side of the 200 EMA", "PASS" if ok else "FAIL",
                   f"{last.end:%Y-%m-%d %H:%M}", "the rulebook calls EMA position 'a basic confirmation, supported by bullish structure'; the structure part has no numeric definition", "prev_session_last_candle")
        else:
            ex.add("TREND", rule_ids[1], "the uptrend must exist BEFORE the gap (a gap cannot create it)", f"trend measured on the previous session only ({ctx.previous.date}); today's gap is not used",
                   "established uptrend, not a sudden gap above the EMA", "PASS" if ok else "FAIL", f"{last.end:%Y-%m-%d %H:%M}",
                   "RF rejects a previous downtrend followed by a sudden large gap above the EMA", "prev_session_last_candle")
        if mode == "STRUCTURE_EMA_SWING2":
            sh = confirmed_swing_highs(pcs, len(pcs) - 1, p.swing_k)
            sl = confirmed_swing_lows(pcs, len(pcs) - 1, p.swing_k)
            desc = "; ".join(f"SH {hm(pcs[j].start)} {px(pcs[j].h)}" for j in sh[-2:]) + " | " + "; ".join(f"SL {hm(pcs[j].start)} {px(pcs[j].l)}" for j in sl[-2:])
            enough = len(sh) >= 2 and len(sl) >= 2
            ok2 = False
            if enough:
                ok2 = (pcs[sh[-1]].h > pcs[sh[-2]].h and pcs[sl[-1]].l > pcs[sl[-2]].l) if direction == "LONG" else (pcs[sh[-1]].h < pcs[sh[-2]].h and pcs[sl[-1]].l < pcs[sl[-2]].l)
            ex.add("TREND", "TREND-STRUCT-001", f"last two confirmed swing highs and lows of the previous session (k={p.swing_k} candles each side, strict)",
                   desc if enough else f"fewer than two confirmed swings (SH {len(sh)}, SL {len(sl)})", "HH+HL (LONG) or LH+LL (SHORT)", "PASS" if ok2 else "FAIL",
                   f"{pcs[-1].end:%Y-%m-%d %H:%M}", "each swing was confirmed by the later candles of the previous session, so none uses future data")
        else:
            ex.add("TREND", "TREND-SWING-001", "confirmed swing structure", "not required by the active trend variant (variant A is the EMA price location only)",
                   "n/a", "NOT_APPLICABLE", f"{last.end:%Y-%m-%d %H:%M}", "variant B would additionally require higher-high/higher-low swings; it is a separate labelled scenario")
    else:
        ex.add("TREND", rule_ids[0], f"trend_mode {mode}", t.reason, "trend in the trade direction", "PASS" if t.ok else "FAIL", "", "trend filter")
    return t.ok


def explain_gap(inp: DayInputs, ex: Explanation, rule_id: str, want: str, extra_why: str = "") -> Any:
    ctx, p = inp.ctx, inp.proposals
    g = gap_info(ctx, p)
    prev = ctx.previous
    ok = g.evaluable and g.direction == want
    ex.add("SETUP", rule_id, "gap = first 1-minute open of today - previous session's OFFICIAL close", f"today's open {px(ctx.open_price)} (first 1-minute bar 09:15) - previous close {px(prev.close_official)} "
           f"({prev.close_source}, {prev.date}) = {g.points:+.2f} points -> gap {g.direction}", f"gap {want} (more than {p.gap_min_points:g} points)",
           "PASS" if ok else "FAIL", f"{ctx.date} 09:15", "approved convention: the original first-minute open, never the vendor daily open" + extra_why)
    return g


# ====================================================================================================== IRF
def explain_irf(inp: DayInputs, tr: TradeRecord, ex: Explanation) -> None:
    sig, cs, p = tr.signal, inp.cs, inp.proposals
    i = inp.idx(sig.signal_candle_start)
    irh, irl = cs[0].h, cs[0].l
    lv = sig.reference_levels
    m = sig.method
    ex.ref("initial_range_candle", cs[0], "initial range = high/low of the 09:15 candle")
    ex.add("SETUP", "IRF-GLOBAL-001", "initial range = high and low (wicks included) of the first completed 5-minute candle", f"{hm(cs[0].start)}-{hm(cs[0].end)} IRH {px(irh)}, IRL {px(irl)} "
           f"(range {px(irh - irl)}; engine recorded IRH {px(lv.get('IRH'))}, IRL {px(lv.get('IRL'))})", "high/low of the 09:15-09:20 candle",
           "PASS" if _close(irh, lv.get("IRH")) and _close(irl, lv.get("IRL")) else "FAIL", cs[0].end, "all three IRF methods measure price against this range", "initial_range_candle")
    ex.add("SETUP", "IRF-GLOBAL-003", "closes confirm, wicks do not: every trigger is evaluated on a completed 5-minute candle",
           f"trigger candle {hm(cs[i].start)}-{hm(cs[i].end)} was complete when the signal was stamped {hm(sig.signal_timestamp)}; decision uses its close {px(cs[i].c)}", "completed candle close, not an intra-candle wick",
           "PASS" if sig.signal_timestamp == cs[i].end else "FAIL", cs[i].end, "an intra-candle wick can reverse before the candle closes", "signal_candle")
    ex.add("SETUP", "IRF-GLOBAL-002", "direction", "SHORT (IRF trades short only)", "short only", "PASS" if sig.direction == "SHORT" else "FAIL", sig.signal_timestamp, "IRF fades failed upside breakouts")
    b_label = trace_time(sig, "->SETUP_DETECTED")
    b = inp.idx_by_end_label(b_label) if m != "Method 3" else i
    sig_c = cs[i]
    ex.ref("signal_candle", sig_c, "candle whose close completed the trigger")
    ups = sum(1 for j in range(1, b + 1) if cs[j].c > irh and cs[j - 1].c <= irh) if m != "Method 3" else 0
    if m != "Method 3":
        bc = cs[b]
        ex.ref("breakout_candle", bc, "breakout candle: a completed candle closing above IRH")
        ex.add("SETUP", "IRF-M1-001" if m == "Method 1" else "IRF-M2-001", "breakout candle close vs IRH",
               f"{describe_candle(bc, p)}; close {px(bc.c)} is {px(bc.c - irh)} points above IRH {px(irh)}", "close > IRH (a wick above IRH is not a breakout)",
               "PASS" if bc.c > irh else "FAIL", bc.end, "starts every IRF setup", "breakout_candle")
    if m == "Method 1":
        inside = irl <= sig_c.c < irh
        ex.add("CONFIRMATION", "IRF-M1-002", "candle after the breakout closes back inside [IRL, IRH)", f"{describe_candle(sig_c, p)}; close {px(sig_c.c)} vs range [{px(irl)}, {px(irh)})",
               "IRL <= close < IRH", "PASS" if inside else "FAIL", sig_c.end, "the failed breakout: price could not hold above the opening range", "signal_candle")
        ex.add("CONFIRMATION", "IRF-M1-004", "failure candle is the candle immediately after the breakout (k = 1)", f"breakout {hm(cs[b].start)}, failure candle {hm(sig_c.start)}: k = {i - b}",
               "k = 1 (pp.5, 6, 13); the p.14 'next or following' reading (IRF-M1-C001) is CONFLICTING and not used in the baseline", "PASS" if i - b == 1 else "FAIL", sig_c.end,
               "the guide's worked example enters at the close of the very next candle; no support/resistance break is required")
    elif m in ("Method 2A", "Method 2B"):
        e, rr = lv.get("extension_index"), lv.get("red_candle_index")
        nxt = cs[b + 1]
        ex.add("SETUP", "IRF-M2-004", "the candle after the breakout must NOT close back inside the range (else the setup is Method 1)", f"{hm(nxt.start)} close {px(nxt.c)} vs [{px(irl)}, {px(irh)})",
               "not (IRL <= close < IRH)", "PASS" if not (irl <= nxt.c < irh) else "FAIL", nxt.end, "separates Method 2 (price holds above) from Method 1 (immediate failure)")
        if e is not None:
            ec = cs[e]
            ex.ref("extension_candle", ec, "extension: first later candle trading above the breakout candle's high")
            ex.add("SETUP", "IRF-M2-002", "extension = a later candle whose high exceeds the breakout candle's high (research definition E1)", f"{hm(ec.start)} high {px(ec.h)} vs breakout candle high {px(cs[b].h)}"
                   f" (+{px(ec.h - cs[b].h)})", "high > breakout candle high", "PASS" if ec.h > cs[b].h and e > b else "FAIL", ec.end,
                   "the guide says price 'extends further upward'; the numeric test is a proposal", "extension_candle")
        if rr is not None:
            rc = cs[rr]
            ex.ref("red_candle", rc, "first red candle during the extension")
            ex.add("SETUP", "IRF-M2-003", "a red candle (close < open) forms after the extension", f"{describe_candle(rc, p)}", "close < open, at or after the candle following the extension",
                   "PASS" if is_red(rc) and rr > (e or 0) else "FAIL", rc.end, "the red candle shows the first pause/reversal inside the extension", "red_candle")
        expiry = p.m2_expiry_candles
        ex.add("NOTE", "IRF-M2-006", "delay between the breakout candle and this trigger; expiry rule", f"{i - b} candles after the breakout; expiry {'none configured' if expiry is None else expiry}",
               "the source states no expiry", "UNRESOLVED", sig_c.end, "an old breakout can still trigger hours later", name="No expiry / validity window for a Method 2 attempt")
        later = [cs[j] for j in range(b + 1, i) if cs[j].c <= irh]
        ex.add("NOTE", "IRF-M2-006", "did price stay above IRH between the breakout and the trigger?", f"{len(later)} closes at or below IRH between {hm(cs[b].end)} and {hm(sig_c.start)}; trigger close {px(sig_c.c)} "
               f"{'above' if sig_c.c > irh else 'at/below'} IRH {px(irh)}", "the engine does not require price to stay above IRH", "UNRESOLVED", sig_c.end,
               "the guide describes price 'holding above IRH and keeping rising'; the code only needs the level break", name="Engine does not test that price held above IRH")
    if m == "Method 2A":
        sup = recent_support(cs, b + 1, i, p)
        jj = lv.get("support_candle_index")
        if sup is not None:
            sj, slevel = sup
            ex.ref("support_pivot", cs[sj], "recent support: latest 3-candle fractal low formed after the breakout")
            ok = _close(slevel, lv.get("recent_support")) and sj == jj
            nb = (cs[sj - 1], cs[sj + 1])
            ex.add("CONFIRMATION", "IRF-M2A-001", "recent support = latest 3-candle fractal low (k=1) among candles b+1 ... i-2", f"{hm(cs[sj].start)} low {px(slevel)}; neighbours' lows {px(nb[0].l)} ({hm(nb[0].start)}) "
                   f"and {px(nb[1].l)} ({hm(nb[1].start)}) are not lower; engine recorded support {px(lv.get('recent_support'))}", "pivot low known before the trigger candle",
                   "PASS" if ok else "FAIL", cs[sj + 1].end, "the support is the level whose break completes Method 2A (the exact 'pullback low' definition is a proposal)", "support_pivot")
            ex.add("CONFIRMATION", "IRF-M2A-002", "trigger candle closes below recent support", f"{hm(sig_c.start)} close {px(sig_c.c)} vs support {px(slevel)}: {px(slevel - sig_c.c)} points below",
                   "close < support (close, not wick)", "PASS" if sig_c.c < slevel else "FAIL", sig_c.end, "completes Method 2A", "signal_candle")
        else:
            ex.add("CONFIRMATION", "IRF-M2A-001", "recent support", "no support recomputed", "support exists", "FAIL", sig_c.end, "completes Method 2A")
        ex.add("CONFIRMATION", "IRF-M2-005", "chronology: the red candle precedes the break candle", f"red candle {hm(cs[rr].start) if rr is not None else 'n/a'}, break candle {hm(sig_c.start)}",
               "red candle index < break candle index (m2a_break_may_be_red_candle = False)", "PASS" if rr is not None and rr < i else "FAIL", sig_c.end,
               "a red candle alone is not confirmation; a level break is required", fidelity="ENGINE_STRICTER_THAN_SOURCE (the source does not require the break candle to be a later candle than the red one)")
    if m == "Method 2B":
        ex.add("CONFIRMATION", "IRF-M2-005", "a red candle alone is not confirmation: a level break is required", f"red trigger candle {hm(sig_c.start)} also closes below the resistance (see IRF-M2B-003)",
               "a red candle plus a closing break of the level", "PASS" if is_red(sig_c) and "recent_resistance" in lv and sig_c.c < lv["recent_resistance"] else "FAIL", sig_c.end,
               "a red candle with no level break does not qualify", "signal_candle")
        res = recent_resistance(cs, b, i, p)
        if res is not None:
            rj, rlevel = res
            ex.ref("first_push_top", cs[rj], "recent resistance = top of the first push after the breakout")
            ok = _close(rlevel, lv.get("recent_resistance")) and rj == lv.get("resistance_candle_index")
            ex.add("CONFIRMATION", "IRF-M2B-001", "recent resistance = first 3-candle fractal high (k=1) at/after the breakout candle (FIRST_PUSH_TOP)", f"{hm(cs[rj].start)} high {px(rlevel)}; "
                   f"engine recorded {px(lv.get('recent_resistance'))}" + (" (the first push top IS the breakout candle itself)" if rj == b else ""), "first push top", "PASS" if ok else "FAIL", cs[rj + 1].end if rj + 1 < len(cs) else cs[rj].end,
                   "the level whose retake-and-fail completes Method 2B (definition is a proposal)", "first_push_top")
            push = next((m_ for m_ in range(rj + 1, i + 1) if cs[m_].h > rlevel), None)
            only_on_signal = push == i
            ex.add("CONFIRMATION", "IRF-M2B-002", "price trades back above the resistance after the first push", (f"first candle with high above {px(rlevel)}: {hm(cs[push].start)} high {px(cs[push].h)}"
                   + (" - this IS the trigger candle itself (the push and the red close back below happen on the same candle)" if only_on_signal else "")) if push is not None else "no candle above the resistance",
                   "some candle after the first push has high > resistance (the push may be the trigger candle: m2b_push_must_precede_red_candle = False)", "PASS" if push is not None else "FAIL", sig_c.end,
                   "the guide's figure shows three separate candles; the engine also accepts a single candle", "signal_candle",
                   fidelity="ENGINE_RELAXES_SOURCE (push and red close on the same candle)" if only_on_signal else "FAITHFUL_TO_SOURCE_SEQUENCE")
            ex.add("CONFIRMATION", "IRF-M2B-003", "trigger = a red candle closing back below the resistance", f"{describe_candle(sig_c, p)}; close {px(sig_c.c)} vs resistance {px(rlevel)}",
                   "red candle and close < resistance", "PASS" if is_red(sig_c) and sig_c.c < rlevel else "FAIL", sig_c.end, "completes Method 2B", "signal_candle")
    if m == "Method 3":
        n = p.m3_compression_n
        comp = cs[i - n:i]
        for k, cc in enumerate(comp):
            ex.ref(f"compression_{k + 1}", cc, "compression candle inside the initial range")
        ex.add("SETUP", "IRF-M3-001", f"the {n} candles before the sweep lie inside the initial range (definition {p.m3_compression_def}; 'small' is NOT enforced unless C2/C3)",
               "; ".join(f"{hm(cc.start)} H {px(cc.h)} L {px(cc.l)}" for cc in comp), f"every compression candle within [{px(irl)}, {px(irh)}]",
               "PASS" if compression_ok(cs, i, irl, irh, p) else "FAIL", sig_c.start, "the guide asks for small candles inside the range; the active rule is containment only")
        ex.add("SETUP", "IRF-M3-002", "sweep candle: red with a high above IRH", describe_candle(sig_c, p), "close < open and high > IRH", "PASS" if is_red(sig_c) and sig_c.h > irh else "FAIL", sig_c.end,
               "the upper-wick sweep above the range", "signal_candle")
        sh = wick_share_outside(sig_c, irh)
        ex.add("SETUP", "IRF-M3-003", "share of the upper wick above IRH = (high - IRH) / (high - body top)", f"({px(sig_c.h)} - {px(irh)}) / {px(upper_wick(sig_c))} = {sh:.4f}" if sh is not None else "no upper wick",
               f"within the active band {p.m3_wick_share_band}", "PASS" if sh is not None and abs(sh - lv.get("wick_share_outside_irh", -1)) < 1e-9 else "FAIL", sig_c.end,
               "the guide says 'approximately 60-70%'; the closed band is a proposal")
        if "recent_support" in lv:
            ex.add("CONFIRMATION", "IRF-M3-005", "sweep candle closes below recent support (compulsory)", f"close {px(sig_c.c)} vs support {px(lv['recent_support'])}", "close < support",
                   "PASS" if sig_c.c < lv["recent_support"] else "FAIL", sig_c.end, "a sweep alone is never enough", "signal_candle")
    # repeats and the unresolved global rule
    if m != "Method 3":
        ex.add("NOTE", "IRF-GLOBAL-004", "which close above IRH of the session produced this attempt; repeat setups", f"this breakout is upward crossing no. {ups} of the session (a close above IRH after a close at/below it)",
               "the source states no first-breakout-only, re-arming, expiry or trades-per-day rule", "UNRESOLVED", sig_c.end, "IRF re-arms on every later breakout in the code, producing many raw setups; the controller keeps only the first",
               name="IRF trades per day / time window / re-arming are not stated in the guide")
    later_irf = [r for r in inp.records if r.strategy == "IRF" and r.signal_status == "CONFIRMED" and r.signal_timestamp > sig.signal_timestamp]
    ex.add("NOTE", "NOTE-IRF-REPEATED-SETUPS", "other IRF signals later in the session (not traded)", f"{len(later_irf)} further confirmed IRF signal(s): " + ", ".join(f"{r.method}@{hm(r.signal_timestamp)}" for r in later_irf[:8]) +
           (" ..." if len(later_irf) > 8 else "") + (f"; concurrent methods merged in this minute: {', '.join(tr.concurrent_methods)}" if tr.concurrent_methods else ""), "disclosure of repeated raw setups",
           "NOT_APPLICABLE", sig_c.end, "repeated raw IRF setups are not hidden; they are logged as ignored")
    extra = f" Entry reference close {px(sig_c.c)} is {px(abs(sig_c.c - irh))} points {'above' if sig_c.c > irh else 'below'} IRH {px(irh)}."
    brk = cs[b] if m != "Method 3" else None
    if m == "Method 1":
        ex.setup_summary = (f"IRF Method 1 SHORT: the completed {hm(brk.start)} candle closed at {px(brk.c)}, {px(brk.c - irh)} points above the initial range high {px(irh)} (range [{px(irl)}, {px(irh)}] "
                            f"from the 09:15 candle); the immediately following completed {hm(sig_c.start)} candle closed at {px(sig_c.c)}, back inside the range. The short signal was confirmed at {hm(sig_c.end)} on that close.{extra}")
    elif m in ("Method 2A", "Method 2B"):
        what = ("a completed candle closed below the recent pullback-low support" if m == "Method 2A" else "a red candle closed back below the first-push resistance after price had traded above it")
        n_back = sum(1 for j in range(b + 1, i) if cs[j].c <= irh)
        held = ("and price stayed above it until the trigger" if n_back == 0 else f"but price closed back at or below IRH {n_back} time(s) before the trigger (the engine does not require it to hold)")
        lab = lambda j: f"{hm(cs[j].start)}-{hm(cs[j].end)}"  # noqa: E731  (every candle is named by its start-end range)
        ex.setup_summary = (f"IRF {m} SHORT: the {lab(b)} candle closed at {px(brk.c)}, above IRH {px(irh)}, and the next candle did not close back inside the range, so the setup is Method 2 {held}. "
                            f"Extension candle {lab(lv['extension_index']) if lv.get('extension_index') is not None else 'n/a'}, red candle {lab(lv['red_candle_index']) if lv.get('red_candle_index') is not None else 'n/a'}. "
                            f"The trigger came {i - b} candles after the breakout candle: {what} ({lab(i)}); confirmed at {hm(sig_c.end)} with close {px(sig_c.c)}.{extra}")
    else:
        ex.setup_summary = f"IRF Method 3 SHORT: a red sweep candle {hm(sig_c.start)} (high {px(sig_c.h)}) pierced IRH {px(irh)} after compression inside the range and closed below recent support; confirmed {hm(sig_c.end)}.{extra}"


# ====================================================================================================== ORB
def explain_orb(inp: DayInputs, tr: TradeRecord, ex: Explanation) -> None:
    sig, cs, p, ctx = tr.signal, inp.cs, inp.proposals, inp.ctx
    c0 = cs[0]
    lv, m = sig.reference_levels, sig.method
    long = sig.direction == "LONG"
    ex.ref("first_candle", c0, "the 09:15 first five-minute candle - the ORB decision candle")
    prev = ctx.previous
    pcs = prev_cs(inp)
    ph, pl = prev_high_low(prev, p)
    ex.add("SETUP", "ORB-GLOBAL-001", "decision is taken once the first 5-minute candle (09:15-09:20) has closed", f"candle {hm(c0.start)}-{hm(c0.end)}; signal confirmed {hm(sig.signal_timestamp)}",
           "decision at 09:20, never before the close", "PASS" if hm(sig.signal_timestamp) == "09:20" else "FAIL", c0.end, "the close of the first candle is unknown before 09:20", "first_candle")
    ex.add("SETUP", "ORB-GLOBAL-002", "direction", f"{sig.direction}", "same rules in both directions", "PASS", c0.end, "ORB trades the side of the break")
    ex.add("SETUP", "ORB-GLOBAL-004", "entry at 09:20, after the first-candle close", f"signal confirmed {hm(sig.signal_timestamp)}; fill {hm(tr.fill_timestamp)} at the open of that minute", "09:20 entry",
           "PASS" if hm(tr.fill_timestamp) == "09:20" else "FAIL", c0.end, "the guide enters at 9:20; the fill price convention (next minute open) is a proposal")
    ex.add("NOTE", "ORB-MA-001", "which moving average the code uses", f"EMA(200) of 5-minute closes (the guide says '200 DMA' in some places and '200 EMA' in others); active ma_mode {p.ma_mode}", "the source terminology conflicts",
           "UNRESOLVED", c0.end, "a daily 200 DMA would give different values", name="200 DMA versus 200 EMA terminology conflict")
    mq = candle_metrics(c0, p)

    def quality(rule_strong: str, rule_pin: str | None):
        thr = p.strong
        shape_ok = (strong_bullish(c0, p) if long else strong_bearish(c0, p))
        pin_ok = (bullish_pin(c0, p) if long else bearish_pin(c0, p))
        opp = mq["upper_wick_pct"] if long else mq["lower_wick_pct"]
        opp_name = "upper" if long else "lower"
        obs = (f"{describe_candle(c0, p)}. Strong-{'bullish' if long else 'bearish'} test: {'bullish' if long else 'bearish'} close, body >= {thr['body_ratio_min'] * 100:g}% "
               f"(observed {mq['body_pct']:.2f}%), {opp_name} wick <= {thr['opposite_wick_ratio_max'] * 100:g}% (observed {opp:.2f}%) -> {'PASS' if shape_ok else 'not met'}")
        if not shape_ok:
            obs += f"; pin-bar alternative: wick >= {p.pin['wick_to_body_min']:g} x body and close within the favourable {p.pin['close_fraction_max'] * 100:g}% -> {'met' if pin_ok else 'not met'}"
        return obs, shape_ok, pin_ok
    if m == "Method 1":
        level = lv["level_broken"]
        kind = lv["level_kind"]
        idx_h = max(range(len(pcs)), key=lambda k: pcs[k].h) if long else min(range(len(pcs)), key=lambda k: pcs[k].l)
        src = pcs[idx_h]
        ex.ref("prev_day_extreme_candle", src, "candle that made the previous session's high/low used as the level", "PREVIOUS")
        ex.add("SETUP", "ORB-M1-LONG-001" if long else "ORB-M1-SHORT-001", f"{kind} = the {'highest high' if long else 'lowest low'} of all 5-minute candles of the previous session {prev.date}",
               f"previous-day {'high' if long else 'low'} {px(level)} (set by the {hm(src.start)} candle; previous session range {px(pl)} - {px(ph)}; engine recorded {px(lv['prev_day_high' if long else 'prev_day_low'])})",
               "previous-day resistance (long) / support (short)", "PASS" if _close(level, ph if long else pl) else "FAIL", f"{prev.date} {hm(src.end)}",
               "a mechanical proxy for the guide's hand-drawn previous-day level; the source charts show multi-session boxes (documented difference)", "prev_day_extreme_candle")
        dist = (c0.c - level) if long else (level - c0.c)
        ex.add("SETUP", "ORB-M1-LONG-002" if long else "ORB-M1-SHORT-002", "the first candle breaks and closes beyond the level", f"high {px(c0.h)} / low {px(c0.l)}, close {px(c0.c)}: {px(dist)} points beyond {px(level)}",
               f"{'high and close > level' if long else 'low and close < level'}", "PASS" if (c0.h > level and c0.c > level if long else c0.l < level and c0.c < level) else "FAIL", c0.end,
               "a wick alone is not a breakout; the close decides", "first_candle")
        explain_trend(inp, ex, sig.direction, ("ORB-TREND-001", "ORB-TREND-002"), "ORB")
        obs, shape_ok, pin_ok = quality("ORB-M1-LONG-003", None)
        route, pin_used = orb_route_text(c0, p, long)
        ex.add("CONFIRMATION", "ORB-M1-LONG-003" if long else "ORB-M1-SHORT-003", "candle quality: strong body and limited opposite wick (or the conditional pin bar)", obs,
               "strong candle (research thresholds) or pin bar", "PASS" if shape_ok or pin_ok else "FAIL", c0.end,
               "the guide asks for a 'strong body, small wick' but gives no numbers; the thresholds are proposals", "first_candle",
               fidelity="PIN_BAR_ROUTE_USED (strong-candle test failed)" if pin_used else "PROXY_FOR_QUALITATIVE_SOURCE")
        ex.setup_summary = (f"ORB Method 1 {sig.direction}: the first completed 5-minute candle ({hm(c0.start)}-{hm(c0.end)}) closed at {px(c0.c)}, {px(dist)} points {'above' if long else 'below'} the previous-day "
                            f"{'high' if long else 'low'} {px(level)}; {route}; the EMA-only trend filter passed. Entry decision at 09:20.")
    elif m == "Method 2":
        level = lv["inner_level"]
        piv = [j for j in pivot_highs(pcs, 0, len(pcs), 2) if pcs[j].h < ph] if long else [j for j in pivot_lows(pcs, 0, len(pcs), 2) if pcs[j].l > pl]
        pj = piv[-1]
        ex.ref("inner_level_candle", pcs[pj], "inner level: latest 5-candle fractal extreme of the previous session inside its range", "PREVIOUS")
        ex.add("SETUP", "ORB-M2-LONG-001" if long else "ORB-M2-SHORT-001", "inner level = latest fractal (k=2) extreme of the previous session below the day's high / above the day's low",
               f"inner {'resistance' if long else 'support'} {px(level)} from the {hm(pcs[pj].start)} candle of {prev.date} (previous range {px(pl)} - {px(ph)}; engine recorded {px(lv['inner_level'])})",
               "an inner level inside yesterday's range", "PASS" if _close(level, lv["inner_level"]) else "FAIL", f"{prev.date} {hm(pcs[min(pj + 2, len(pcs) - 1)].end)}",
               "the source gives NO objective construction for the inner level: this is a research variant", "inner_level_candle")
        ex.add("SETUP", "ORB-M2-LONG-002" if long else "ORB-M2-SHORT-002", "first candle breaks and closes beyond the inner level", f"close {px(c0.c)} vs inner level {px(level)}: {px(abs(c0.c - level))} points beyond",
               "high/low and close beyond the level", "PASS" if (c0.h > level and c0.c > level if long else c0.l < level and c0.c < level) else "FAIL", c0.end, "the breakout itself", "first_candle")
        explain_trend(inp, ex, sig.direction, ("ORB-TREND-001", "ORB-TREND-002"), "ORB")
        tl_idx = pivot_lows(pcs, 0, len(pcs), 2) if long else pivot_highs(pcs, 0, len(pcs), 2)
        j1, j2 = tl_idx[-2], tl_idx[-1]
        y1, y2 = (pcs[j1].l, pcs[j2].l) if long else (pcs[j1].h, pcs[j2].h)
        slope = (y2 - y1) / (j2 - j1)
        line_now = y2 + slope * (len(pcs) - j2)
        ex.ref("trendline_point_1", pcs[j1], "first fractal point of the trendline", "PREVIOUS")
        ex.ref("trendline_point_2", pcs[j2], "second fractal point of the trendline", "PREVIOUS")
        ok_dir = slope > 0 if long else slope < 0
        on_side = c0.c > line_now if long else c0.c < line_now
        ex.add("CONFIRMATION", "ORB-M2-LONG-001" if long else "ORB-M2-SHORT-001", "trendline through the last two fractal lows (long) / highs (short) of the previous session",
               f"points {hm(pcs[j1].start)} {px(y1)} and {hm(pcs[j2].start)} {px(y2)} ({j2 - j1} candles apart): slope {slope:+.4f} per candle; line value at the 09:15 candle {px(line_now)}; "
               f"first-candle close {px(c0.c)} is {'on' if on_side else 'off'} the supportive side (engine recorded {px(lv.get('trendline_value_at_open'))})",
               "rising (long) / falling (short) line with price on the trend side", "PASS" if ok_dir and on_side and _close(line_now, lv.get("trendline_value_at_open")) else "FAIL",
               f"{prev.date} {hm(pcs[j2].end)}", "the guide requires a trendline but defines no construction or 'near' distance: research variant", "trendline_point_1,trendline_point_2")
        obs, shape_ok, pin_ok = quality("ORB-M2-LONG-003", None)
        ex.add("CONFIRMATION", "ORB-M2-LONG-003" if long else "ORB-M2-SHORT-003", "candle quality: strong body and limited opposite wick (or pin bar)", obs, "strong candle or pin bar",
               "PASS" if shape_ok or pin_ok else "FAIL", c0.end, "same proposed thresholds as Method 1", "first_candle")
        ema = float(ctx.candles["ema200_5m"].iloc[0]) if p.trend_mode in ("STRUCTURE_EMA_SWING2", "EMA_PREV_SESSION_CLOSE") else trend_check(ctx, 0, sig.direction, p.trend_mode, p).ma_value
        near = abs(c0.c - ema) <= p.ma_near_band_points
        beyond_pts = (c0.c - ema) if long else (ema - c0.c)
        ex.add("CONFIRMATION", "ORB-M2-LONG-004" if long else "ORB-M2-SHORT-004", "if the close is near the 5-minute EMA(200) a convincing close beyond it is needed",
               f"EMA(200) at the 09:15 candle {px(ema)}; close {px(c0.c)} is {px(abs(c0.c - ema))} points {'above' if c0.c > ema else 'below'} it; 'near' band {p.ma_near_band_points:g} points -> "
               f"{'near: margin ' + px((c0.c - ema) if long else (ema - c0.c)) + ' vs required ' + px(p.ma_close_margin_points) if near else 'not near, test not applicable'}",
               f"outside the {p.ma_near_band_points:g}-point band, or beyond the EMA by >= {p.ma_close_margin_points:g}", "PASS" if (not near or beyond_pts >= p.ma_close_margin_points) else "FAIL", c0.end, "ORB p.5: 'if the breakout is near the EMA, wait for a convincing close'")
        route, pin_used = orb_route_text(c0, p, long)
        _fid(ex, ("ORB-M2-LONG-003", "ORB-M2-SHORT-003"), pin_used)
        ex.setup_summary = (f"ORB Method 2 {sig.direction} (research variant): the first candle closed at {px(c0.c)}, beyond the inner {'resistance' if long else 'support'} {px(level)} built from the "
                            f"previous session's latest fractal ({hm(pcs[pj].start)}), with a supportive trendline ({px(line_now)}); {route}. "
                            f"The source gives no construction for the inner level or the trendline.")
    else:  # Gap/200DMA
        g = explain_gap(inp, ex, "ORB-GAP-LONG-001" if long else "ORB-GAP-SHORT-001", "UP" if long else "DOWN")
        ma, ma_prev = lv["ma_value"], lv["ma_prev"]
        pc = prev.close_official
        crossed = (pc < ma_prev and ctx.open_price > ma) if long else (pc > ma_prev and ctx.open_price < ma)
        ex.ref("prev_session_last_candle", pcs[-1], "previous session's last candle: the EMA(200) before the gap", "PREVIOUS")
        ex.add("SETUP", "ORB-GAP-LONG-002" if long else "ORB-GAP-SHORT-002", f"the gap carries the open through the moving average ({p.ma_mode}: EMA(200) of 5-minute closes)",
               f"previous close {px(pc)} {'<' if long else '>'} previous-session EMA {px(ma_prev)}; today's open {px(ctx.open_price)} {'>' if long else '<'} today's first-candle EMA {px(ma)} (engine recorded {px(ma)} / {px(ma_prev)})",
               "previous close on one side, open on the other", "PASS" if crossed and _close(ma, float(ctx.candles['ema200_5m'].iloc[0])) else "FAIL", c0.end,
               "the Gap/200 DMA setup needs the gap to push price through the MA (the source text vs figures is a documented conflict: ORB-MA-001)", "first_candle,prev_session_last_candle")
        ex.add("CONFIRMATION", "ORB-GAP-LONG-003" if long else "ORB-GAP-SHORT-003", "first candle closes beyond the moving average", f"close {px(c0.c)} vs EMA {px(ma)}: {px(abs(c0.c - ma))} points {'above' if c0.c > ma else 'below'}",
               "close above (long) / below (short) the MA", "PASS" if (c0.c > ma if long else c0.c < ma) else "FAIL", c0.end, "a candle that only crosses the line does not qualify", "first_candle")
        obs, shape_ok, pin_ok = quality("ORB-GAP-LONG-004", None)
        rej = mq["upper_wick_pct"] if long else mq["lower_wick_pct"]
        rejected = bool(upper_rejection(c0, p) if long else lower_rejection(c0, p))
        ex.add("CONFIRMATION", "ORB-GAP-LONG-004" if long else "ORB-GAP-SHORT-003", "candle quality (strong body or pin bar) and no strong rejection wick", f"{obs}; rejection wick {rej:.2f}% vs limit {p.reject['wick_ratio_min'] * 100:g}%",
               "strong body or pin bar, and the rejection wick below the limit", "PASS" if (shape_ok or pin_ok) and not rejected else "FAIL", c0.end,
               "the thresholds are proposals", "first_candle")
        ex.add("NOTE", "ORB-GAP-LONG-005" if long else "ORB-GAP-SHORT-004", "'excessively extended' opening move", f"gap {g.points:+.2f} points; maximum gap configured: {p.gap_max_points}",
               "the source gives no number, so no limit is applied", "UNRESOLVED" if p.gap_max_points is None else "PASS", c0.end, "a very large gap would be rejected by a human; the engine has no defined limit")
        route, pin_used = orb_route_text(c0, p, long)
        _fid(ex, ("ORB-GAP-LONG-004", "ORB-GAP-SHORT-003"), pin_used)
        ex.setup_summary = (f"ORB Gap/200 DMA {sig.direction}: the open {px(ctx.open_price)} gapped {g.points:+.2f} points from the previous close {px(pc)}, through the EMA(200) ({px(ma_prev)} -> {px(ma)}); the first candle closed at "
                            f"{px(c0.c)}, beyond the average; {route}. The 'excessively extended' filter has no numeric definition and was not applied.")
    ex.levels.update({"ema": True})


# ====================================================================================================== PDR
def explain_pdr(inp: DayInputs, tr: TradeRecord, ex: Explanation) -> None:
    sig, cs, p, ctx = tr.signal, inp.cs, inp.proposals, inp.ctx
    lv = sig.reference_levels
    prev = ctx.previous
    pcs = prev_cs(inp)
    sig_i = inp.idx(sig.signal_candle_start)
    sc = cs[sig_i]
    g = explain_gap(inp, ex, "PDR-004", "UP")
    z = pdr_zone(prev, p)
    ph, pl = prev_high_low(prev, p)
    ex.add("ZONE", "PDR-001", "direction", "LONG (PDR is long only)", "long-only", "PASS" if sig.direction == "LONG" else "FAIL", sig.signal_timestamp, "PDR buys a retest of previous-day resistance after a gap up")
    zj = z.candle_index
    zc = pcs[zj]
    ex.ref("zone_source_candle", zc, f"swing-high candle that defines the zone ({p.pdr_zone_method})", "PREVIOUS")
    day_high_idx = max(range(len(pcs)), key=lambda k: pcs[k].h)
    ex.ref("prev_day_high_candle", pcs[day_high_idx], "candle of the previous session's absolute high (for comparison)", "PREVIOUS")
    ok_z = z is not None and _close(z.low, lv["zone_low"]) and _close(z.high, lv["zone_high"])
    confirmed_at = pcs[min(zj + p.swing_k, len(pcs) - 1)].end
    ex.add("ZONE", "PDR-002", f"zone = [body top, wick high] of the latest confirmed swing high (k={p.swing_k}) that has a red candle among the peak and the next {p.swing_k} candles (method {p.pdr_zone_method})",
           f"zone [{px(z.low)}, {px(z.high)}] from the {hm(zc.start)} candle of {prev.date} (body top {px(max(zc.o, zc.c))}, wick high {px(zc.h)}; {describe_candle(zc, p)}); engine recorded [{px(lv['zone_low'])}, {px(lv['zone_high'])}]. "
           f"Previous session's absolute high {px(ph)} (candle {hm(pcs[day_high_idx].start)}) - {'the zone is NOT the day high' if not _close(z.high, ph) else 'the zone coincides with the day high'} (distance {px(ph - z.high)} points). "
           f"Swing confirmed once candle {hm(pcs[min(zj + p.swing_k, len(pcs) - 1)].start)} closed.", "previous-day high where price peaked and reversed", "PASS" if ok_z else "FAIL", f"{prev.date} {hm(confirmed_at)}",
           "the source says 'previous day's high/reversal'; which candle marks the zone is an owner-approved research candidate, not a source rule", "zone_source_candle,prev_day_high_candle",
           fidelity="ZONE_IS_THE_DAY_HIGH" if _close(z.high, ph) else f"ZONE_IS_NOT_THE_DAY_HIGH ({px(ph - z.high)} points below it; owner-approved research candidate B)")
    ex.levels["zone"] = (z.low, z.high, "PDR zone (reversal swing high)")
    ex.levels["prev_high"] = ph
    ex.add("ZONE", "PDR-003", "the zone is an area, not a single price", f"zone height {px(z.high - z.low)} points [{px(z.low)}, {px(z.high)}]", "a rectangle with positive height", "PASS" if z.high > z.low else "FAIL",
           f"{prev.date} {hm(confirmed_at)}", "price may touch any part of the area", "zone_source_candle")
    ex.add("ZONE", "PDR-010", "reversal-quality filter ('clear high and reversal identified')", f"filter setting {p.pdr_reversal_filter}", "checklist item: a clear previous-day high and reversal",
           "UNRESOLVED" if p.pdr_reversal_filter == "OFF" else "PASS", prev.date.isoformat(), "the engine does not test reversal depth in the baseline (filter OFF)", name="Reversal-quality filter is OFF in the baseline")
    op = ctx.open_price
    ex.add("SETUP", "PDR-011", "open relative to the zone (ABOVE_ZONE)", f"today's open {px(op)} vs zone high {px(z.high)}: {px(op - z.high)} points above", "open > zone high",
           "PASS" if op > z.high else "FAIL", f"{ctx.date} 09:15", "the guide has price 'pull back into the zone', so the gap-up open is above it; this exclusion is a proposal")
    interaction = lv.get("interaction_candle_start")
    ji = inp.idx(interaction)
    jc = cs[ji]
    ex.ref("interaction_candle", jc, "first candle whose range intersects the zone")
    ex.ref("confirmation_candle", sc, "first green candle after the interaction candle")
    prox = p.zone_proximity_points
    inter = jc.l <= z.high + prox and jc.h >= z.low - prox
    prior_idx = [inp.idx(r.signal_candle_start) for r in inp.records if r.strategy == "PDR" and r.signal_status == "CONFIRMED" and r.signal_timestamp < sig.signal_timestamp]
    scan_from = (max(prior_idx) + 1) if prior_idx else 0
    dist_close = jc.l - z.high
    ex.add("CONFIRMATION", "PDR-006", "the first candle whose [low, high] intersects the zone (+/- proximity)", f"{describe_candle(jc, p)}; low {px(jc.l)} vs zone high {px(z.high)} ({px(abs(dist_close))} points "
           f"{'inside/below' if dist_close <= 0 else 'above'} the zone top), high {px(jc.h)} vs zone low {px(z.low)}; proximity {prox:g}", "range intersects the zone",
           "PASS" if inter and all(not (c.l <= z.high + prox and c.h >= z.low - prox) for c in cs[scan_from:ji]) else "FAIL", jc.end,
           "the retest of the previous-day resistance" + (f" (the engine re-arms after an earlier signal: scanning restarted after the {hm(cs[scan_from - 1].start)} candle)" if scan_from else ""), "interaction_candle",
           fidelity="INTERACTION_CANDLE_CLOSED_BELOW_ZONE_FLOOR (price traded through the zone, not a hold)" if jc.c < z.low else "")
    ex.add("CONFIRMATION", "PDR-007", "the first GREEN candle after the interaction candle", f"{describe_candle(sc, p)}; interaction candle {hm(jc.start)}, confirmation candle {hm(sc.start)}",
           "close > open, strictly after the interaction candle", "PASS" if is_green(sc) and sig_i > ji and all(not is_green(cs[k]) for k in range(ji + 1, sig_i)) else "FAIL", sc.end,
           "the guide asks for 'a green candle' after the test; it gives no size or position test", "confirmation_candle")
    ex.add("CONFIRMATION", "PDR-005", "no entry at the open: price must first come back toward the zone", f"interaction candle {hm(jc.start)} (candle no. {ji + 1} of the session) precedes the entry candle {hm(sc.start)}; fill {hm(tr.fill_timestamp)}",
           "interaction before the entry; fill after 09:20", "PASS" if ji < sig_i and tr.fill_timestamp.hour * 60 + tr.fill_timestamp.minute > 9 * 60 + 20 - 1 else "FAIL", sc.end,
           "if price keeps rising without returning to the zone there is no setup", "interaction_candle")
    held = sc.c >= z.low
    ex.add("NOTE", "PDR-007", "did the zone hold? (is the confirmation candle's close back at/above the zone floor?)", f"confirmation close {px(sc.c)} vs zone floor {px(z.low)} / top {px(z.high)}: "
           f"{'above the zone top' if sc.c > z.high else ('inside the zone' if sc.c >= z.low else 'BELOW the zone floor by ' + px(z.low - sc.c))}; interaction low {px(jc.l)}",
           "the engine does NOT test that resistance-turned-support held", "UNRESOLVED", sc.end,
           "a later green candle is accepted even after price traded through the zone; a human would normally check the hold" + ("" if held else " (here the close is below the zone floor)"),
           name="Engine does not test whether the zone held")
    ex.add("NOTE", "PDR-012", "repeated PDR signals today", f"{sum(1 for r in inp.records if r.strategy == 'PDR' and r.signal_status == 'CONFIRMED')} confirmed PDR signal(s) in the session", "n/a (disclosure)", "NOT_APPLICABLE",
           sc.end, "the per-session cap is lifted for the controller runs; the controller trades only the first")
    ex.setup_summary = (f"PDR LONG: the session opened {g.points:.2f} points above the previous close and {px(op - z.high)} points above the resistance zone [{px(z.low)}, {px(z.high)}] taken from the {hm(zc.start)} swing-high candle "
                        f"of {prev.date}. The {hm(jc.start)} candle ({px(jc.l)} - {px(jc.h)}) " + (f"traded through the zone and closed at {px(jc.c)}, {px(z.low - jc.c)} points BELOW its floor" if jc.c < z.low else "retested the zone")
                        + f", and the {hm(sc.start)} candle closed green at {px(sc.c)}, confirming the entry at {hm(sc.end)}. "
                        f"The engine does not check that the zone held (confirmation close {'inside/above' if held else 'BELOW'} the zone floor).")


# ====================================================================================================== PDR (Phase 3.4 revised engine)
def _pat_text(name: str, d: dict[str, Any], th: dict[str, float], ceiling: float) -> tuple[str, str]:
    """(observed, required) text of one revised confirmation pattern, from the numbers the engine used."""
    def pc(v):
        return "undefined" if v is None else f"{100 * v:.2f}%"
    if name == "GOOD_GREEN_BODY":
        return (f"colour {'green' if d.get('bullish') else 'NOT green'}; body {pc(d.get('body_pct'))}; upper wick {pc(d.get('upper_wick_pct'))}",
                f"green, body >= {100 * th['green_body_min']:g}% and upper wick <= {100 * th['green_upper_wick_max']:g}% of the range")
    if name == "LOWER_PRICE_REJECTION":
        wb = d.get("wick_to_body")
        return (f"lower wick {px(d.get('lower_wick'))} = {'undefined' if wb is None else f'{wb:.2f}'} x body {px(d.get('body'))}; close {pc(d.get('close_from_high_pct'))} below the high; low {px(d.get('low'))}"
                f"{'' if d.get('low_reached_zone') is None else ('; low reached the zone ceiling ' + px(ceiling) if d['low_reached_zone'] else '; low did NOT reach the zone ceiling ' + px(ceiling))}",
                f"lower wick >= {th['reject_wick_to_body_min']:g} x body, close within the top {100 * th['reject_close_fraction_max']:g}% of the range, low <= zone ceiling (colour not required)")
    wb = d.get("wick_to_body")
    return (f"lower wick {px(d.get('lower_wick'))} = {'undefined' if wb is None else f'{wb:.2f}'} x body; upper wick {pc(d.get('upper_wick_pct'))}; body bottom at {pc(d.get('body_position'))} of the range",
            f"lower wick >= {th['hammer_wick_to_body_min']:g} x body, upper wick <= {100 * th['hammer_upper_wick_max']:g}%, body bottom >= {100 * th['hammer_body_position_min']:g}% of the range (colour not required)")


def explain_pdr_revised(inp: DayInputs, tr: TradeRecord, ex: Explanation) -> None:  # noqa: C901
    sig, cs, p, ctx = tr.signal, inp.cs, inp.proposals, inp.ctx
    lv = sig.reference_levels
    prev = ctx.previous
    pcs = prev_cs(inp)
    cfg = PDRRevisionConfig(**{**sig.proposals_used["pdr_revision"], "patterns_enabled": tuple(sig.proposals_used["pdr_revision"]["patterns_enabled"])})
    th = cfg.thresholds
    sig_i = inp.idx(sig.signal_candle_start)
    sc = cs[sig_i]
    g = explain_gap(inp, ex, "PDR-004", "UP")
    z = build_zone(pcs, cfg)
    ph, pl = prev_high_low(prev, p)
    ex.add("ZONE", "PDR-001", "direction", "LONG (PDR is long only)", "long-only", "PASS" if sig.direction == "LONG" else "FAIL", sig.signal_timestamp, "PDR buys a retest of previous-day resistance after a gap up")
    dh = pcs[z.members[0]]
    ex.ref("zone_source_candle", dh, f"previous-day-high candle that anchors the zone ({cfg.zone_candidate})", "PREVIOUS")
    ok_z = _close(z.floor, lv["zone_floor"]) and _close(z.ceiling, lv["zone_ceiling"])
    ex.add("ZONE", "PDR-A01", "zone ceiling = the previous session's highest high; the zone is drawn from the body top to the wick high of that candle",
           f"previous session {prev.date}: highest high {px(ph)} made by the {hm(dh.start)} candle (O {px(dh.o)} H {px(dh.h)} L {px(dh.l)} C {px(dh.c)}); zone [{px(z.floor)} (body top), {px(z.ceiling)} (wick high)]; "
           f"engine recorded [{px(lv['zone_floor'])}, {px(lv['zone_ceiling'])}]", "ceiling = previous-day high (author: the day's high should be considered and a zone drawn)",
           "PASS" if ok_z and _close(z.ceiling, ph) else "FAIL", f"{prev.date} 15:30", "the zone is anchored on the previous day's high, never on a lower swing high", "zone_source_candle",
           name="Zone ceiling is the previous-day high (zone drawn from body top to wick high)", fidelity="AUTHOR_STATEMENT; floor convention (body top) is PROPOSED")
    ex.levels["zone"] = (z.floor, z.ceiling, "PDR zone (previous-day-high anchored)")
    ex.levels["prev_high"] = ph
    zb = build_zone_b(pcs, PDRRevisionConfig(zone_candidate="B_MULTIPLE_HIGH_CLUSTER"))
    ex.add("ZONE", "PDR-A02", "multiple highs connected into one zone (author principle; candidate B)",
           f"candidate A (used): [{px(z.floor)}, {px(z.ceiling)}] from the day-high candle only. Candidate B (multiple-high cluster, tolerance {PDRRevisionConfig().b_tolerance_points:g} points) would be [{px(zb.floor)}, {px(zb.ceiling)}] "
           f"({zb.kind}, {zb.touches} touch(es)); ceiling difference {px(zb.ceiling - z.ceiling)} points", "a zone that connects all relevant highs (numbers not given by the author)",
           "UNRESOLVED", f"{prev.date} 15:30", "candidate B has the same ceiling by construction, so this signal is unaffected by the choice; the lower boundary is a research parameter",
           name="Multiple-high zone not applied (candidate A used); the numeric details are research parameters")
    flat = z.ceiling <= z.floor
    ex.add("ZONE", "PDR-003", "the zone is an area, not a single price", f"zone height {px(z.ceiling - z.floor)} points [{px(z.floor)}, {px(z.ceiling)}]"
           + ("; the previous-day-high candle closed on its high (no upper wick above its body), so the zone from body top to wick high degenerates to a LINE at the previous-day high" if flat else ""),
           "a rectangle with positive height (the author gave no rule for a zero-height zone)", "UNRESOLVED" if flat else "PASS", f"{prev.date} 15:30",
           "price may touch any part of the area; a line zone is touched when a candle's range includes that price", "zone_source_candle",
           name="Zone is an area (zero-height zone: undefined by the author)" if flat else None, fidelity="ZERO_HEIGHT_ZONE_NOT_DEFINED_BY_THE_AUTHOR" if flat else "")
    op = ctx.open_price
    ex.add("SETUP", "PDR-A03a", "open relative to the zone ceiling (preserved legacy PDR-011, a research assumption)", f"today's open {px(op)} vs zone ceiling {px(z.ceiling)}: {px(op - z.ceiling)} points above",
           "open > zone ceiling", "PASS" if op > z.ceiling else "FAIL", f"{ctx.date} 09:15", "the guide has price pull back into the zone after a gap up; requiring the open above the previous-day high is NOT an author rule",
           name="Open above the zone ceiling (research assumption, not author-approved)", fidelity="RESEARCH_ASSUMPTION_PRESERVED_FROM_PHASE2")
    jstart = lv.get("interaction_candle_start")
    ji = next(k for k, c in enumerate(cs) if hm(c.start) == jstart)
    jc = cs[ji]
    prior_idx = [inp.idx(r.signal_candle_start) for r in inp.records if r.strategy == "PDR" and r.signal_status == "CONFIRMED" and r.signal_timestamp < sig.signal_timestamp]
    scan_from = (max(prior_idx) + 1) if prior_idx else 0
    prox = cfg.proximity_points
    first_touch = next((k for k in range(scan_from, len(cs)) if cs[k].l <= z.ceiling + prox and cs[k].h >= z.floor - prox), None)
    ex.ref("interaction_candle", jc, "first candle whose range overlaps the zone (the test)")
    ex.ref("confirmation_candle", sc, "candle that satisfies one of the three patterns and closes above the zone ceiling")
    ex.add("CONFIRMATION", "PDR-A03", "the first candle whose [low, high] overlaps the zone (+/- proximity) is the test; the confirmation must come strictly after it",
           f"{describe_candle(jc, p)}; low {px(jc.l)} vs zone ceiling {px(z.ceiling)}, high {px(jc.h)} vs zone floor {px(z.floor)}; proximity {prox:g}; confirmation candle {hm(sc.start)} is candle no. {sig_i + 1}, the test candle no. {ji + 1}",
           "range overlaps the zone; confirmation after the test", "PASS" if first_touch == ji and ji < sig_i else "FAIL", jc.end,
           "the retest of the previous-day resistance" + (f" (re-armed after the earlier signal: scanning restarted after the {hm(cs[scan_from - 1].start)} candle)" if scan_from else ""), "interaction_candle", name="Test candle: the zone is revisited")
    res = classify_confirmation(sc, z.floor, z.ceiling, cfg)
    names = {"GOOD_GREEN_BODY": ("PDR-A04a", "Pattern 1: good green body"), "LOWER_PRICE_REJECTION": ("PDR-A04b", "Pattern 2: lower-price rejection candle"), "HAMMER": ("PDR-A04c", "Pattern 3: hammer candle")}
    for pname, (rid, title) in names.items():
        d = dict(res["patterns"][pname])
        d.setdefault("low", sc.l)
        obs, req = _pat_text(pname, d, th, z.ceiling)
        passed = bool(res["patterns"][pname]["passed"])
        ex.add("CONFIRMATION", rid, f"{title} on the {hm(sc.start)}-{hm(sc.end)} candle (O {px(sc.o)} H {px(sc.h)} L {px(sc.l)} C {px(sc.c)}); thresholds are PROVISIONAL ({cfg.pattern_profile})", obs + (" -> PASSES" if passed else " -> does not pass"),
               req, "PASS" if passed else "NOT_APPLICABLE", sc.end, "one of the three patterns is enough (author: one good green body OR lower price rejection OR hammer); a pattern that does not pass is not an error",
               "confirmation_candle", name=title + " (provisional thresholds)", fidelity="THRESHOLDS_PROPOSED_FOR_REVIEW_NOT_AUTHOR_APPROVED")
    rec_patterns = list(lv.get("patterns_passed", []))
    ex.add("CONFIRMATION", "PDR-A04", "at least one of the three patterns passes (OR logic; every passing pattern is recorded)", f"patterns passed: {', '.join(res['patterns_passed']) or 'NONE'} (engine recorded: {', '.join(rec_patterns) or 'none'})",
           "at least one pattern", "PASS" if res["patterns_passed"] and res["patterns_passed"] == rec_patterns else "FAIL", sc.end, "the author's entry candle requirement", "confirmation_candle",
           name="At least one confirmation pattern passes")
    ex.add("CONFIRMATION", "PDR-A05", "the confirmation candle must close above the zone", f"close {px(sc.c)} vs zone ceiling {px(z.ceiling)}: {sc.c - z.ceiling:+.2f} points (floor {px(z.floor)}; low {px(sc.l)} {'dipped into/below the zone' if sc.l <= z.ceiling else 'stayed above the zone'})",
           "close > zone ceiling, strictly (lower wick may penetrate the zone)", "PASS" if sc.c > z.ceiling and res["close_above_ceiling"] else "FAIL", sc.end,
           "no pattern overrides the close rule", "confirmation_candle", name="Confirmation candle closes strictly above the zone ceiling",
           fidelity="AUTHOR_STATEMENT 'the candle should close above the zone'; 'strictly' and 'the ceiling' are OWNER_INTERPRETATION")
    ex.add("CONFIRMATION", "PDR-A06", "no entry at the open and no look-ahead: the order is placed only after the confirmation candle has completed",
           f"test candle {hm(jc.start)} (no. {ji + 1}) precedes the confirmation candle {hm(sc.start)}-{hm(sc.end)}; signal stamped {hm(sig.signal_timestamp)}; fill {hm(tr.fill_timestamp)} at the open of that 1-minute bar = {px(tr.entry_price)}",
           "interaction before the confirmation; fill after the confirmation candle's end", "PASS" if ji < sig_i and tr.fill_timestamp == sig.signal_timestamp else "FAIL", sc.end,
           "existing causal fill convention (EXE-FILL-001)", "interaction_candle", name="Causal entry: fill at the next 1-minute open after the confirmation candle")
    ex.add("NOTE", "PDR-A04x", "provisional parameters this signal rests on", f"pattern thresholds {cfg.pattern_profile}: {th}; open-above-zone rule {cfg.open_vs_zone}; test-candle confirmation allowed: {cfg.confirmation_may_be_interaction_candle}; wait policy {cfg.wait_policy}",
           "n/a (disclosure)", "UNRESOLVED", sc.end, "the strategy author has NOT approved these numbers or the open-above-zone assumption; the signal is a RESEARCH_VARIANT, never VERIFIED",
           name="PDR revised: thresholds, open rule and wait policy are provisional research assumptions")
    ex.add("NOTE", "PDR-012", "repeated PDR signals today", f"{sum(1 for r in inp.records if r.strategy == 'PDR' and r.signal_status == 'CONFIRMED')} confirmed PDR signal(s) in the session",
           "n/a (disclosure)", "NOT_APPLICABLE", sc.end, "the per-session cap is lifted for the controller runs; the controller trades only the first (and a PDR/PDS second trade after an initial full stop)")
    ex.setup_summary = (f"PDR LONG (revised engine, {cfg.zone_candidate}, provisional thresholds): the session opened {g.points:.2f} points above the previous close and {px(op - z.ceiling)} points above the previous-day high "
                        f"{px(z.ceiling)} (zone [{px(z.floor)}, {px(z.ceiling)}] from the {hm(dh.start)} candle of {prev.date}). The {hm(jc.start)} candle ({px(jc.l)} - {px(jc.h)}) tested the zone; the {hm(sc.start)} candle "
                        f"({'green' if sc.c > sc.o else 'not green'}, O {px(sc.o)} H {px(sc.h)} L {px(sc.l)} C {px(sc.c)}) passed {', '.join(res['patterns_passed'])} and closed {sc.c - z.ceiling:.2f} points above the zone ceiling, "
                        f"confirming the entry at {hm(sc.end)}. The pattern thresholds and the open-above-zone requirement are provisional research assumptions, not approved by the strategy author.")


# ====================================================================================================== PDR (Phase 3.6 body-based engine)
def explain_pdr_body(inp: DayInputs, tr: TradeRecord, ex: Explanation) -> None:  # noqa: C901
    sig, cs, p, ctx = tr.signal, inp.cs, inp.proposals, inp.ctx
    lv = sig.reference_levels
    prev = ctx.previous
    pcs = prev_cs(inp)
    cfg = PDRBodyConfig(**{**sig.proposals_used["pdr_body"], "patterns_enabled": tuple(sig.proposals_used["pdr_body"]["patterns_enabled"])})
    th = cfg.thresholds
    sig_i = inp.idx(sig.signal_candle_start)
    sc = cs[sig_i]
    g = explain_gap(inp, ex, "PDR-004", "UP")
    z = build_body_zone(pcs, cfg)
    ph, pl = prev_high_low(prev, p)
    ex.add("ZONE", "PDR-001", "direction", "LONG (PDR is long only)", "long-only", "PASS" if sig.direction == "LONG" else "FAIL", sig.signal_timestamp, "PDR buys a retest of previous-day resistance after a gap up")
    dh = pcs[z.members[0]]
    wick_idx = max(range(len(pcs)), key=lambda k: pcs[k].h)
    ex.ref("zone_source_candle", dh, f"candle of the previous session's highest BODY high ({cfg.zone_candidate})", "PREVIOUS")
    ex.ref("prev_day_wick_high_candle", pcs[wick_idx], "candle of the previous session's highest WICK (ignored by the author's rule; shown for comparison)", "PREVIOUS")
    top = sorted(((body_high(c), c) for c in pcs), key=lambda t: -t[0])[:4]
    ok_z = _close(z.floor, lv["zone_floor"]) and _close(z.ceiling, lv["zone_ceiling"]) and _close(z.ceiling, max(body_high(c) for c in pcs))
    ex.add("ZONE", "PDR-B01a", "wicks ignored, bodies considered: body_high = max(open, close) of every completed previous-session 5-minute candle; ceiling = the highest body_high; floor = body low of that candle",
           f"previous session {prev.date}: highest body high {px(z.ceiling)} on the {hm(dh.start)} candle (O {px(dh.o)} C {px(dh.c)}; wick high of that candle {px(dh.h)}, ignored); four highest body highs: "
           + "; ".join(f"{px(v)} ({hm(c.start)})" for v, c in top) + f". Highest WICK of the session {px(ph)} ({hm(pcs[wick_idx].start)} candle) is {px(ph - z.ceiling)} points above the ceiling and plays no part. "
           f"Zone [{px(z.floor)} (body low), {px(z.ceiling)} (body high)]; engine recorded [{px(lv['zone_floor'])}, {px(lv['zone_ceiling'])}]",
           "ceiling = highest body high of the previous session (author: wick ignored, body considered)", "PASS" if ok_z else "FAIL", f"{prev.date} 15:30",
           "a wick-only price never becomes resistance; the zone is drawn from candle bodies", "zone_source_candle,prev_day_wick_high_candle",
           name="Zone ceiling is the previous-day highest BODY high (wicks ignored)", fidelity="AUTHOR_STATEMENT; the exact body-high reading and the floor are PROPOSED / OWNER_INTERPRETATION")
    ex.levels["zone"] = (z.floor, z.ceiling, "PDR zone (previous-day highest body high)")
    ex.levels["prev_high"] = z.ceiling
    zb = build_body_zone(pcs, PDRBodyConfig(zone_candidate="B_MULTIPLE_BODY_HIGH_CLUSTER"))
    ex.add("ZONE", "PDR-B02", "multiple highs connected into one zone (author principle; candidate B)",
           f"candidate A (used): [{px(z.floor)}, {px(z.ceiling)}]. Candidate B (multiple-body-high cluster, tolerance {PDRBodyConfig().b_tolerance_points:g} points) would be [{px(zb.floor)}, {px(zb.ceiling)}] "
           f"({zb.kind}, {zb.touches} touch(es), member body highs {', '.join(px(v) for v in zb.member_body_highs)}); ceiling difference {px(zb.ceiling - z.ceiling)} points",
           "a zone that connects all relevant highs (numbers not given by the author)", "UNRESOLVED", f"{prev.date} 15:30",
           "candidate B has the same ceiling by construction, so this signal is unaffected by the choice; the lower boundary and the cluster numbers are research parameters",
           name="Multiple-body-high zone not applied (candidate A used); the numeric details are research parameters")
    ex.add("ZONE", "PDR-003", "the zone is an area, not a single price", f"zone height {px(z.ceiling - z.floor)} points [{px(z.floor)}, {px(z.ceiling)}]", "a rectangle with positive height (a zero-height zone is left unresolved by the engine)",
           "PASS" if z.ceiling > z.floor else "FAIL", f"{prev.date} 15:30", "price may touch any part of the area", "zone_source_candle")
    op = ctx.open_price
    ex.add("SETUP", "PDR-B03", "the session opens strictly above the previous day's resistance zone (author-approved)", f"today's first 1-minute open {px(op)} vs zone ceiling {px(z.ceiling)}: {px(op - z.ceiling)} points above (open - ceiling = {op - z.ceiling:+.2f})",
           "open > zone ceiling (equal or inside the zone rejects the setup)", "PASS" if op > z.ceiling else "FAIL", f"{ctx.date} 09:15", "the original first-minute open is used, never a vendor daily open",
           name="Open strictly above the zone ceiling (author-approved)")
    jstart = lv.get("interaction_candle_start")
    ji = next(k for k, c in enumerate(cs) if hm(c.start) == jstart)
    jc = cs[ji]
    prior_idx = [inp.idx(r.signal_candle_start) for r in inp.records if r.strategy == "PDR" and r.signal_status == "CONFIRMED" and r.signal_timestamp < sig.signal_timestamp]
    scan_from = (max(prior_idx) + 1) if prior_idx else 0
    prox = cfg.proximity_points
    first_touch = next((k for k in range(scan_from, len(cs)) if cs[k].l <= z.ceiling + prox and cs[k].h >= z.floor - prox), None)
    ex.ref("interaction_candle", jc, "first candle whose range overlaps the zone (the test)")
    ex.ref("confirmation_candle", sc, "candle that satisfies one of the three patterns and closes above the zone ceiling")
    ex.add("CONFIRMATION", "PDR-B03b", "the first candle whose [low, high] overlaps the zone (+/- proximity) is the test; the confirmation must come strictly after it",
           f"{describe_candle(jc, p)}; low {px(jc.l)} vs zone ceiling {px(z.ceiling)}, high {px(jc.h)} vs zone floor {px(z.floor)}; proximity {prox:g}; confirmation candle {hm(sc.start)} is candle no. {sig_i + 1}, the test candle no. {ji + 1}",
           "range overlaps the zone; confirmation after the test", "PASS" if first_touch == ji and ji < sig_i else "FAIL", jc.end,
           "the retest of the previous-day resistance" + (f" (re-armed after the earlier signal: scanning restarted after the {hm(cs[scan_from - 1].start)} candle)" if scan_from else ""), "interaction_candle", name="Test candle: the zone is revisited")
    res = classify_confirmation(sc, z.floor, z.ceiling, cfg.pattern_config())
    names = {"GOOD_GREEN_BODY": "Pattern 1: good green body", "LOWER_PRICE_REJECTION": "Pattern 2: lower-price rejection candle", "HAMMER": "Pattern 3: hammer candle"}
    for pname, title in names.items():
        d = dict(res["patterns"][pname])
        d.setdefault("low", sc.l)
        obs, req = _pat_text(pname, d, th, z.ceiling)
        passed = bool(res["patterns"][pname]["passed"])
        ex.add("CONFIRMATION", "PDR-B04c", f"{title} on the {hm(sc.start)}-{hm(sc.end)} candle (O {px(sc.o)} H {px(sc.h)} L {px(sc.l)} C {px(sc.c)}); the numeric thresholds are PROVISIONAL ({cfg.pattern_profile}), not author-approved",
               obs + (" -> PASSES" if passed else " -> does not pass"), req, "PASS" if passed else "NOT_APPLICABLE", sc.end,
               "one of the three patterns is enough (author: one good green body OR lower price rejection OR hammer); fixed thresholds are not required by the author, so the numbers are a research convention; a pattern that does not pass is not an error",
               "confirmation_candle", name=title + " (provisional research thresholds)", fidelity="THRESHOLDS_PROPOSED_FOR_REVIEW_NOT_AUTHOR_APPROVED")
    rec_patterns = list(lv.get("patterns_passed", []))
    ex.add("CONFIRMATION", "PDR-B04", "at least one of the three patterns passes (OR logic; every passing pattern is recorded)", f"patterns passed: {', '.join(res['patterns_passed']) or 'NONE'} (engine recorded: {', '.join(rec_patterns) or 'none'})",
           "at least one pattern", "PASS" if res["patterns_passed"] and res["patterns_passed"] == rec_patterns else "FAIL", sc.end, "the author's entry candle requirement", "confirmation_candle",
           name="At least one confirmation pattern passes")
    ex.add("CONFIRMATION", "PDR-B05", "the confirmation candle must close above the zone", f"close {px(sc.c)} vs zone ceiling {px(z.ceiling)}: {sc.c - z.ceiling:+.2f} points (floor {px(z.floor)}; low {px(sc.l)} {'dipped into/below the zone' if sc.l <= z.ceiling else 'stayed above the zone'})",
           "close > zone ceiling, strictly (lower wick may penetrate the zone)", "PASS" if sc.c > z.ceiling and res["close_above_ceiling"] else "FAIL", sc.end, "no pattern overrides the close rule", "confirmation_candle",
           name="Confirmation candle closes strictly above the zone ceiling", fidelity="AUTHOR_STATEMENT 'the candle should close above the zone'; 'strictly' and 'the ceiling' are OWNER_INTERPRETATION")
    ex.add("CONFIRMATION", "PDR-B06", "no entry at the open and no look-ahead: the order is placed only after the confirmation candle has completed",
           f"test candle {hm(jc.start)} (no. {ji + 1}) precedes the confirmation candle {hm(sc.start)}-{hm(sc.end)}; signal stamped {hm(sig.signal_timestamp)}; fill {hm(tr.fill_timestamp)} at the open of that 1-minute bar = {px(tr.entry_price)}",
           "interaction before the confirmation; fill after the confirmation candle's end", "PASS" if ji < sig_i and tr.fill_timestamp == sig.signal_timestamp else "FAIL", sc.end,
           "existing causal fill convention (EXE-FILL-001)", "interaction_candle", name="Causal entry: fill at the next 1-minute open after the confirmation candle")
    ex.add("NOTE", "PDR-B04x", "provisional parameters this signal rests on", f"pattern thresholds {cfg.pattern_profile}: {th}; zone lower boundary = hull of the member bodies; zero-height policy {cfg.zero_height_policy}; wait policy {cfg.wait_policy}; "
           f"cluster parameters (candidate B only) tolerance {cfg.b_tolerance_points:g}, touches {cfg.b_min_touches}, separation {cfg.b_min_separation_candles}",
           "n/a (disclosure)", "UNRESOLVED", sc.end, "the strategy author has NOT approved these numbers or conventions; the signal is a RESEARCH_VARIANT, never VERIFIED",
           name="PDR body-based: numeric thresholds and zone conventions are provisional research assumptions")
    ex.add("NOTE", "PDR-012", "repeated PDR signals today", f"{sum(1 for r in inp.records if r.strategy == 'PDR' and r.signal_status == 'CONFIRMED')} confirmed PDR signal(s) in the session",
           "n/a (disclosure)", "NOT_APPLICABLE", sc.end, "this engine reports EVERY qualifying signal (the per-session cap is lifted); the controller trades only the first (and a PDR/PDS second trade after an initial full stop)",
           name="Repeated PDR signals today (disclosure: all are reported, the controller takes the first)")
    broke = [c for c in cs[ji:sig_i] if c.c < z.floor]
    ex.add("NOTE", "PDR-B07", "state of the zone between the test and the confirmation (the author and the guide are silent on price crossing below the zone)",
           f"test candle {hm(jc.start)} (no. {ji + 1}), confirmation candle {hm(sc.start)} (no. {sig_i + 1}): {sig_i - ji} candle(s) later; "
           + (f"{len(broke)} candle(s) in between CLOSED BELOW the zone floor {px(z.floor)} (lowest close {px(min(c.c for c in broke))}) before price returned above the ceiling" if broke else "no candle in between closed below the zone floor"),
           "n/a (disclosure; the wait policy is a research parameter)", "UNRESOLVED" if broke else "NOT_APPLICABLE", sc.end,
           "the engine keeps a tested setup armed until a candle qualifies; whether a zone that price has closed through should still count is an owner decision",
           name="Wait policy / zone that price closed through before the confirmation (research assumption)")
    ex.setup_summary = (f"PDR LONG (body-based engine, {cfg.zone_candidate}): the session opened {g.points:.2f} points above the previous close and {px(op - z.ceiling)} points above the previous-day highest BODY high "
                        f"{px(z.ceiling)} (zone [{px(z.floor)}, {px(z.ceiling)}] from the {hm(dh.start)} candle of {prev.date}; the highest wick {px(ph)} is ignored). The {hm(jc.start)} candle ({px(jc.l)} - {px(jc.h)}) tested the zone; "
                        f"the {hm(sc.start)} candle ({'green' if sc.c > sc.o else 'not green'}, O {px(sc.o)} H {px(sc.h)} L {px(sc.l)} C {px(sc.c)}) passed {', '.join(res['patterns_passed'])} and closed {sc.c - z.ceiling:.2f} points above the zone ceiling, "
                        f"confirming the entry at {hm(sc.end)}. The pattern thresholds and the zone's lower boundary are provisional research assumptions, not approved by the strategy author.")


# ====================================================================================================== PDS
def explain_pds(inp: DayInputs, tr: TradeRecord, ex: Explanation) -> None:
    sig, cs, p, ctx = tr.signal, inp.cs, inp.proposals, inp.ctx
    lv, m = sig.reference_levels, sig.method
    prev = ctx.previous
    pcs = prev_cs(inp)
    i = inp.idx(sig.signal_candle_start)
    sc = cs[i]
    explain_gap(inp, ex, "PDS-003", "DOWN")
    z = pds_zone(prev, p)
    zj = z.candle_index
    zc = pcs[zj]
    ex.ref("zone_source_candle", zc, f"previous-day low candle that defines the zone ({z.method})", "PREVIOUS")
    ex.add("ZONE", "PDS-001", "direction", "SHORT (PDS is short only)", "short-only", "PASS" if sig.direction == "SHORT" else "FAIL", sig.signal_timestamp, "PDS sells a retest of previous-day support from below")
    ok_z = _close(z.low, lv["zone_low"]) and _close(z.high, lv["zone_high"])
    ex.add("ZONE", "PDS-002", f"zone = [lowest low, body top] of the previous session's absolute-low candle (method {z.method}; the lower wick is part of the zone)",
           f"zone [{px(z.low)}, {px(z.high)}] from the {hm(zc.start)} candle of {prev.date} ({describe_candle(zc, p)}); engine recorded [{px(lv['zone_low'])}, {px(lv['zone_high'])}]",
           "previous trading day's low where price took support (body + lower wick)", "PASS" if ok_z else "FAIL", f"{prev.date} {hm(zc.end)}", "the reference level of the strategy; the exact candle(s) are a research choice (PDS-ZONE-002)", "zone_source_candle")
    ex.levels["zone"] = (z.low, z.high, "PDS zone (previous-day low)")
    op = ctx.open_price
    ex.add("SETUP", "PDS-006", "gap-down open below the zone", f"today's open {px(op)} vs zone low {px(z.low)}: {px(z.low - op)} points below", "open < zone low", "PASS" if op < z.low else "FAIL", f"{ctx.date} 09:15",
           "the guide: 'price is trading below the previous day's support zone' after the gap; a PROPOSED strict reading")
    prox = p.zone_proximity_points

    def at_zone(c):
        return c.h >= z.low - prox and c.l <= z.high + prox
    sig_i_ = i
    prior_idx = [inp.idx(r.signal_candle_start) for r in inp.records if r.strategy == "PDS" and r.signal_status == "CONFIRMED" and r.signal_timestamp < sig.signal_timestamp]
    scan_from = (max(prior_idx) + 1) if prior_idx else 0
    j0 = next(k for k in range(scan_from, len(cs)) if at_zone(cs[k]))
    c0 = cs[j0]
    ex.ref("zone_retest_candle", c0, "first candle whose range reaches the zone from below")
    ex.add("SETUP", "PDS-004", "PDS is not a breakdown strategy: the zone must be tested from below first", f"open {px(op)} below the zone floor {px(z.low)}; the first candle to reach the zone is {hm(cs[next(k for k in range(scan_from, len(cs)) if at_zone(cs[k]))].start)}",
           "price rises to the zone before any short", "PASS" if sig_i_ >= next(k for k in range(scan_from, len(cs)) if at_zone(cs[k])) else "FAIL", ctx.date.isoformat() + " 09:15", "a short below the level without a retest is not this strategy")
    ex.add("SETUP", "PDS-005", "price comes up to the zone: first candle whose [low, high] intersects it (+/- proximity)", f"{describe_candle(c0, p)}; high {px(c0.h)} vs zone low {px(z.low)}",
           "range intersects the zone", "PASS", c0.end, "PDS is not a breakdown strategy: the zone must be tested from below first", "zone_retest_candle")
    ex.ref("signal_candle", sc, "trigger candle")
    ex.add("NOTE", "PDS-007", "repeated PDS signals today", f"{sum(1 for r in inp.records if r.strategy == 'PDS' and r.signal_status == 'CONFIRMED')} confirmed PDS signal(s) in the session", "n/a (disclosure)", "NOT_APPLICABLE",
           sc.end, "the per-session cap is lifted for the controller runs; the controller trades only the first (or the permitted second) trade")
    mq = candle_metrics(sc, p)
    if m in ("Method 1", "Method 2"):
        first_red = next((k for k in range(j0, len(cs)) if is_red(cs[k]) and at_zone(cs[k])), None)
        ex.add("CONFIRMATION", "PDS-M-001", "Methods 1/2 apply to the FIRST red candle at the zone", f"first red candle at the zone: {hm(cs[first_red].start) if first_red is not None else 'n/a'}; signal candle {hm(sc.start)}",
               "the trigger is the first red candle at the zone", "PASS" if first_red == i else "FAIL", sc.end, "a later red candle would only qualify through Method 3", "signal_candle")
        thr = p.strong
        if m == "Method 1":
            ex.add("CONFIRMATION", "PDS-M1-001", "good red candle: bearish close, body >= %g%% of range, lower wick <= %g%% of range" % (thr["body_ratio_min"] * 100, thr["opposite_wick_ratio_max"] * 100),
                   f"{describe_candle(sc, p)} -> body {mq['body_pct']:.2f}% / lower wick {mq['lower_wick_pct']:.2f}%", "strong bearish candle (research thresholds)",
                   "PASS" if strong_bearish(sc, p) else "FAIL", sc.end, "the guide: 'a red candle with a good body' - body size is explicitly not numerically defined", "signal_candle")
        else:
            pt = p.pin
            ex.add("CONFIRMATION", "PDS-M2-001", f"red higher-price-rejection pin bar: upper wick >= {pt['wick_to_body_min']:g} x body, close within the lowest {pt['close_fraction_max'] * 100:g}% of the range, high reaches the zone",
                   f"{describe_candle(sc, p)}; upper wick / body = {px(mq['bearish_pin_wick_to_body'])}; close position from the low {px(mq['close_position_from_low_pct'])}% of range; high {px(sc.h)} vs zone low {px(z.low)}",
                   "bearish pin bar and high >= zone low", "PASS" if bearish_pin(sc, p) and sc.h >= z.low and is_red(sc) else "FAIL", sc.end,
                   "the guide: wick-to-body ratio 'not specified'; these thresholds are an owner recommendation (proposal)", "signal_candle")
        ex.setup_summary = (f"PDS {m} SHORT: the session opened {px(z.low - op)} points below the previous-day-low zone [{px(z.low)}, {px(z.high)}]; price rose to the zone at {hm(c0.start)} and the first red candle at the zone "
                            f"({hm(sc.start)}, close {px(sc.c)}) {'had a good body' if m == 'Method 1' else 'was a higher-price-rejection pin bar'}; confirmed {hm(sc.end)}.")
    else:
        weak_label = next((ln.split(" ", 1)[0] for ln in sig.state_trace if "weak first red candle" in ln), None)
        wi = inp.idx_by_end_label(weak_label)
        wc = cs[wi]
        ex.ref("weak_first_red_candle", wc, "first red candle at the zone that failed the quality rule")
        ex.add("CONFIRMATION", "PDS-M-001", "Method 3 is used when the first red candle at the zone is not satisfying", f"first red candle at the zone: {describe_candle(wc, p)}; strong-bearish test body >= {p.strong['body_ratio_min'] * 100:g}%, "
               f"lower wick <= {p.strong['opposite_wick_ratio_max'] * 100:g}% -> {'met' if strong_bearish(wc, p) else 'not met'}; pin bar -> {'met' if bearish_pin(wc, p) else 'not met'}",
               "first red candle is neither strong nor a pin bar", "PASS" if is_red(wc) and not strong_bearish(wc, p) and not bearish_pin(wc, p) else "FAIL", wc.end,
               "the quality rule keeps weak candles out; Method 3 waits for a support break instead", "weak_first_red_candle")
        near_ceiling = z.high + prox
        js = [j for j in pivot_lows(cs, wi, i, 1) if cs[j].l <= near_ceiling]
        sup_j = js[-1] if js else None
        sup = cs[sup_j].l if sup_j is not None else None
        if sup_j is not None:
            ex.ref("small_support_pivot", cs[sup_j], "small support: latest 3-candle fractal low after the weak candle")
        dist_zone = None if sup is None else z.low - sup
        ex.add("CONFIRMATION", "PDS-M3-001", f"small support = latest 3-candle fractal low (k=1) formed at/after the weak candle with low <= zone high ({px(near_ceiling)}); definition {p.pds_small_support_def}",
               (f"support {px(sup)} from the {hm(cs[sup_j].start)} candle; engine recorded {px(lv.get('small_support'))}; distance below the zone floor {px(dist_zone)} points"
                + (" (negative: the support lies ABOVE the floor)" if dist_zone < 0 else "") + f" (zone floor {px(z.low)}); "
                "the guide says 'near the zone' but defines no distance - the code has no lower bound") if sup is not None else "no support", "a small support near the zone",
               "PASS" if sup is not None and _close(sup, lv.get("small_support")) else "FAIL", cs[sup_j + 1].end if sup_j is not None else sc.end,
               "'near' and the size of the small support are undefined in the guide", "small_support_pivot")
        ex.add("CONFIRMATION", "PDS-M3-001", f"trigger: candle closes below the small support (break basis {p.pds_m3_break_basis})", f"{hm(sc.start)} close {px(sc.c)} vs support {px(sup)}: {px(sup - sc.c)} points below" if sup is not None else "",
               "close < support", "PASS" if sup is not None and sc.c < sup else "FAIL", sc.end, "the guide does not say close or touch; the close is used", "signal_candle")
        ex.add("NOTE", "PDS-MISSING-001", "entry timing", "signal on the candle close; fill at the next minute's open", "the guide does not say whether entry is intra-candle or after the close", "UNRESOLVED", sc.end,
               "causal convention: nothing is entered before the trigger candle has closed", name="PDS entry timing is not specified in the guide")
        ex.setup_summary = (f"PDS Method 3 SHORT: the session opened {px(z.low - op)} points below the previous-day-low zone [{px(z.low)}, {px(z.high)}]; the first red candle at the zone ({hm(wc.start)}) was weak (body {candle_metrics(wc, p)['body_pct']:.2f}%), "
                            f"so the engine waited for a small support; the {hm(cs[sup_j].start)} candle's low {px(sup)} ({px(dist_zone)} points below the zone floor) was broken by the close of the {hm(sc.start)} candle ({px(sc.c)}); confirmed {hm(sc.end)}.")


# ====================================================================================================== RF
def explain_rf(inp: DayInputs, tr: TradeRecord, ex: Explanation) -> None:
    sig, cs, p, ctx = tr.signal, inp.cs, inp.proposals, inp.ctx
    lv = sig.reference_levels
    prev = ctx.previous
    c0 = cs[0]
    rf_h, rf_l = c0.h, c0.l
    ph, pl = prev_high_low(prev, p)
    i = inp.idx(sig.signal_candle_start)
    sc = cs[i]
    ex.ref("rf_range_candle", c0, "first 5-minute candle: RF High / RF Low")
    ex.add("SETUP", "RF-002", "RF High / Low = high / low (wicks included) of the first 5-minute candle", f"{hm(c0.start)}-{hm(c0.end)} RF High {px(rf_h)}, RF Low {px(rf_l)} (engine recorded {px(lv['RF_High'])} / {px(lv['RF_Low'])})",
           "first-candle range", "PASS" if _close(rf_h, lv["RF_High"]) and _close(rf_l, lv["RF_Low"]) else "FAIL", c0.end, "the zone price must dip below and return into", "rf_range_candle")
    explain_trend(inp, ex, "LONG", ("RF-001", "RF-008"), "RF")
    g = explain_gap(inp, ex, "RF-003", "UP")
    within = pl <= ctx.open_price <= ph
    ex.add("SETUP", "RF-004", "gap-up open inside yesterday's trading range", f"open {px(ctx.open_price)} vs previous session {prev.date} range [{px(pl)}, {px(ph)}]: {'inside' if within else 'outside'}"
           f" (previous close {px(prev.close_official)}, gap {g.points:+.2f})", "previous low <= open <= previous high", "PASS" if within else "FAIL", f"{ctx.date} 09:15",
           "a huge gap beyond yesterday's range is rejected; the source gives no number, the test is the previous session's high/low")
    cb = next(k for k in range(1, len(cs)) if cs[k].c < rf_l)
    cbc = cs[cb]
    ex.ref("close_below_candle", cbc, "first candle closing below RF Low")
    ex.ref("return_inside_candle", sc, "first later candle closing back inside the first-candle range")
    ex.add("CONFIRMATION", "RF-005", "a candle CLOSES below RF Low (a wick is not enough)", f"{describe_candle(cbc, p)}; close {px(cbc.c)} vs RF Low {px(rf_l)}: {px(rf_l - cbc.c)} points below", "close < RF Low",
           "PASS" if cbc.c < rf_l and cb == inp.idx(lv["close_below_candle_start"]) else "FAIL", cbc.end, "the failed-breakdown leg of the setup", "close_below_candle")
    back = next(k for k in range(cb + 1, len(cs)) if rf_l <= cs[k].c <= rf_h)
    ex.add("CONFIRMATION", "RF-006", f"price returns inside the first-candle range - definition {p.rf_return_inside_def} (first later candle whose CLOSE is within [RF Low, RF High])",
           f"{describe_candle(sc, p)}; close {px(sc.c)} within [{px(rf_l)}, {px(rf_h)}]; {i - cb} candle(s) after the close-below candle ({hm(cbc.start)})", "RF Low <= close <= RF High",
           "PASS" if back == i else "FAIL", sc.end, "completes the activation; the source does not say 'close' vs 'touch' nor any time limit", "return_inside_candle")
    ex.add("CONFIRMATION", "RF-007", "order of the four steps", f"trend (previous session) -> gap {hm(c0.start)} open -> close below {hm(cbc.start)} -> return {hm(sc.start)}", "uptrend, gap up in range, close below, return",
           "PASS" if cb < i else "FAIL", sc.end, "the source requires this order")
    ex.add("CONFIRMATION", "RF-013", "gap up without the break-and-return sequence gives no RF activation", f"sequence complete: close below {hm(cbc.start)}, return inside {hm(sc.start)}", "both steps present",
           "PASS" if cb < i else "FAIL", sc.end, "the gap alone never activates RF")
    ex.add("NOTE", "RF-014", "first activation per session", "only the first completed sequence of the session is reported", "n/a (engineering proposal)", "NOT_APPLICABLE", sc.end, "the source is silent on re-activation")
    ex.add("NOTE", "RF-009", "stop selection", f"baseline stop {inp.trade.stop_points('RF'):g} points (USER_APPROVED research baseline)", "the guide: 35-40 'depending on what is logical', fixed vs candle-extreme not stated",
           "UNRESOLVED", sc.end, "the source does not define the RF stop rule", name="RF stop selection rule is not defined")
    ex.add("NOTE", "RF-012", "trade direction", "LONG (implied: 'opposite of IRF', 'uptrend only' and the long-position reference screenshots; the word long never appears)", "the guide does not state the direction", "UNRESOLVED", sc.end,
           "the direction is a labelled research proposal, not source-verified", name="RF trade direction is implied, not stated")
    ex.add("NOTE", "RF-010", "entry price", f"signal reference = close of the return candle {px(sc.c)}; fill = next minute open {px(tr.entry_price)}", "the guide's rule-readiness table lists the exact entry price as OPEN, i.e. unspecified", "UNRESOLVED", sc.end,
           "causal convention applied to every strategy", name="RF entry price is not specified")
    ex.setup_summary = (f"RF LONG (research proposal for direction/target): the session gapped {g.points:+.2f} points up inside yesterday's range [{px(pl)}, {px(ph)}] after an EMA-only uptrend; the {hm(cbc.start)} candle closed at {px(cbc.c)}, "
                        f"{px(rf_l - cbc.c)} points below RF Low {px(rf_l)}, and the {hm(sc.start)} candle closed back inside the range at {px(sc.c)}, activating the setup at {hm(sc.end)}.")


EXPLAINERS = {"IRF": explain_irf, "ORB": explain_orb, "PDR": explain_pdr, "PDS": explain_pds, "RF": explain_rf}


def explain_trade(day, tr: TradeRecord, inp: DayInputs) -> Explanation:
    ex = Explanation(trade_id_of(day, tr))
    explain_selection(inp, tr, ex)
    if tr.signal.strategy == "PDR" and tr.signal.execution_config.get("pdr_body"):
        explain_pdr_body(inp, tr, ex)  # Phase 3.6 body-based engine
    elif tr.signal.strategy == "PDR" and tr.signal.execution_config.get("pdr_revision"):
        explain_pdr_revised(inp, tr, ex)  # Phase 3.4 revised engine
    else:
        EXPLAINERS[tr.signal.strategy](inp, tr, ex)
    explain_execution_levels(inp, tr, ex)
    order = {"SELECTION": 0, "SETUP": 1, "TREND": 2, "ZONE": 3, "CONFIRMATION": 4, "EXECUTION": 5, "NOTE": 6}
    ex.checks.sort(key=lambda c: (order[c.group], c.seq))
    for k, c in enumerate(ex.checks, 1):
        c.seq = k
    return ex


# ====================================================================================================== exits
@dataclass
class LegExit:
    trade_id: str
    leg: int
    qty: int
    entry_price: float
    exit_ts: datetime | None
    exit_price: float | None
    reason: str
    trigger_text: str
    source_bar: Bar | None
    gross_pnl_rs: float | None
    slippage_points: float
    flags: list[str]


def _bar_at(bars: list[Bar], ts) -> Bar | None:
    return next((b for b in bars if b.ts == ts), None)


def explain_exits(day, tr: TradeRecord, bars: list[Bar], trade_cfg: TradeConfig) -> tuple[list[LegExit], str, dict]:
    r = tr.result
    tid = trade_id_of(day, tr)
    long = tr.signal.direction == "LONG"
    sgn = 1 if long else -1
    q1 = trade_cfg.leg1_lots * trade_cfg.lot_size
    q2 = trade_cfg.total_lots * trade_cfg.lot_size - q1
    entry = tr.entry_price

    def pnl(px_, q):
        return None if px_ is None else (px_ - entry) * sgn * q

    def bar_txt(b: Bar | None) -> str:
        return "no source bar" if b is None else f"1-minute bar {hm(b.ts)} O {px(b.o)} H {px(b.h)} L {px(b.l)} C {px(b.c)}"
    cls = tr.classification
    amb = list(r.ambiguities)
    flags_common = ["SAME_BAR_AMBIGUITY" for a in amb if "both touched" in a][:1]
    t1_done = cls in ("TARGET", "T1_THEN_BUFFER_STOP", "BREAKEVEN") or (cls == "FORCED_EXIT" and r.post_t1_stop_level is not None) or (cls == "INCOMPLETE_EOD" and r.leg1_exit is not None and r.leg2_exit is None)
    b1 = _bar_at(bars, r.leg1_ts) if r.leg1_ts is not None else None
    b2 = _bar_at(bars, r.leg2_ts) if r.leg2_ts is not None else None
    legs: list[LegExit] = []
    narrative = ""
    if cls == "INITIAL_FULL_STOP":
        slip = r.adverse_slippage_points
        trig = (f"{bar_txt(b1)}: {'low' if long else 'high'} {px(b1.l if long else b1.h)} reached the original stop {px(r.stop_level)} before Target 1 {px(r.t1_level)} was touched; both legs exit"
                + (f" at {px(r.leg1_exit)} (gap through the stop: bar open {px(b1.o)} is worse than the stop; adverse slippage {slip:.2f} points)" if slip > 0 else f" at the stop level {px(r.leg1_exit)}"))
        for leg, q in ((1, q1), (2, q2)):
            legs.append(LegExit(tid, leg, q, entry, r.leg1_ts, r.leg1_exit, "ORIGINAL_STOP_BEFORE_T1", trig, b1, pnl(r.leg1_exit, q), slip, list(flags_common)))
        narrative = (f"At {hm(r.leg1_ts)} price reached the original stop {px(r.stop_level)} before Target 1 {px(r.t1_level)}, so all six lots exited together at {px(r.leg1_exit)}"
                     f"{f' (gap through the stop, slippage {slip:.2f} points)' if slip > 0 else ''}. This is an INITIAL_FULL_STOP: one more trade is allowed that day, only a newly confirmed PDR/PDS signal.")
    else:
        if t1_done:
            trig1 = f"{bar_txt(b1)}: {'high' if long else 'low'} {px(b1.h if long else b1.l)} reached Target 1 {px(r.t1_level)}; Leg 1 booked at the target level"
            legs.append(LegExit(tid, 1, q1, entry, r.leg1_ts, r.leg1_exit, "TARGET_1", trig1, b1, pnl(r.leg1_exit, q1), 0.0, []))
            stopmsg = (f"At {hm(r.leg1_ts)} the remaining three lots' protective stop was set to {px(r.post_t1_stop_level)} (entry {'-' if long else '+'} 6; no trailing, no further change); "
                       f"the engine applies it from the Target-1 bar onward and tests it within that same bar.")
        if cls == "TARGET":
            trig2 = f"{bar_txt(b2)}: {'high' if long else 'low'} {px(b2.h if long else b2.l)} reached Target 2 {px(r.t2_level)}; Leg 2 booked at the target level"
            legs.append(LegExit(tid, 2, q2, entry, r.leg2_ts, r.leg2_exit, "TARGET_2", trig2, b2, pnl(r.leg2_exit, q2), 0.0, list(flags_common)))
            narrative = (f"At {hm(r.leg1_ts)} price reached Target 1 {px(r.t1_level)} and three lots exited. {stopmsg} At {hm(r.leg2_ts)} price reached Target 2 {px(r.t2_level)} and the remaining three lots exited. "
                         f"No further trade that day (DAY-T2-001).")
        elif cls in ("T1_THEN_BUFFER_STOP", "BREAKEVEN"):
            slip = r.adverse_slippage_points
            trig2 = (f"{bar_txt(b2)}: {'low' if long else 'high'} {px(b2.l if long else b2.h)} reached the post-T1 stop {px(r.post_t1_stop_level)}; Leg 2 exits at {px(r.leg2_exit)}"
                     + (f" (adverse slippage {slip:.2f} points: the bar opened beyond the stop)" if slip > 0 else " at the stop level"))
            legs.append(LegExit(tid, 2, q2, entry, r.leg2_ts, r.leg2_exit, "POST_T1_STOP_ENTRY_MINUS_PLUS_6", trig2, b2, pnl(r.leg2_exit, q2), slip, list(flags_common)))
            same_bar = r.leg1_ts == r.leg2_ts
            narrative = (f"At {hm(r.leg1_ts)} price reached Target 1 {px(r.t1_level)} and three lots exited. {stopmsg} At {hm(r.leg2_ts)}{' (the SAME 1-minute bar: its intra-minute order is unknown, so the engine resolves it adversely)' if same_bar else ''} "
                         f"the remaining three lots stopped out at {px(r.leg2_exit)}{f' (slippage {slip:.2f} points)' if slip > 0 else ''}. T1_THEN_BUFFER_STOP: no second trade that day (DAY-BUF-001).")
        elif cls == "FORCED_EXIT":
            fl = ["PROVISIONAL_FORCED_EXIT_15_14_OPEN"]
            trig2 = (f"{bar_txt(b2)}: provisional forced exit at the OPEN of the 15:14 minute ({px(r.leg2_exit)}); neither Target 2 nor the stop was reached" + (f"; sensitivity close of that minute {px(r.forced_exit_reference_close)} (not used)"
                     if r.forced_exit_reference_close is not None else ""))
            if t1_done:
                legs.append(LegExit(tid, 2, q2, entry, r.leg2_ts, r.leg2_exit, "FORCED_EXIT_1514_OPEN_PROVISIONAL", trig2, b2, pnl(r.leg2_exit, q2), 0.0, fl))
                narrative = f"At {hm(r.leg1_ts)} Target 1 booked three lots. {stopmsg} Neither the stop nor Target 2 was reached; at {hm(r.leg2_ts)} the remaining lots were closed by the PROVISIONAL forced exit at the minute open {px(r.leg2_exit)}."
            else:
                for leg, q in ((1, q1), (2, q2)):
                    legs.append(LegExit(tid, leg, q, entry, r.leg2_ts, r.leg2_exit, "FORCED_EXIT_1514_OPEN_PROVISIONAL", trig2, b2, pnl(r.leg2_exit, q), 0.0, fl))
                narrative = f"Neither the stop, Target 1 nor Target 2 was reached; at {hm(r.leg2_ts)} all six lots were closed by the PROVISIONAL forced exit at the minute open {px(r.leg2_exit)}."
        else:  # INCOMPLETE_EOD / NOT_EVALUABLE
            legs.append(LegExit(tid, 2, q2, entry, None, None, "UNRESOLVED_NO_FILLABLE_EXIT", "no fillable exit bar exists; nothing is invented", None, None, 0.0, ["UNRESOLVED_EXIT"]))
            if not t1_done:
                legs.insert(0, LegExit(tid, 1, q1, entry, None, None, "UNRESOLVED_NO_FILLABLE_EXIT", "no fillable exit bar exists; nothing is invented", None, None, 0.0, ["UNRESOLVED_EXIT"]))
            narrative = "The position had no fillable exit (end of data / closing auction); the exit is unresolved and no price was invented."
    # trade progress from the 1-minute bars
    end_ts = r.leg2_ts or r.leg1_ts
    walk = [b for b in bars if b.ts >= tr.fill_timestamp and (end_ts is None or b.ts <= end_ts)]
    prog: dict[str, Any] = {}
    if walk:
        fav = max(walk, key=lambda b: (b.h - entry) if long else (entry - b.l))
        adv = max(walk, key=lambda b: (entry - b.l) if long else (b.h - entry))
        prog = {"bars_held": len(walk), "max_favourable_points": ((fav.h - entry) if long else (entry - fav.l)), "max_favourable_at": hm(fav.ts),
                "max_adverse_points": ((entry - adv.l) if long else (adv.h - entry)), "max_adverse_at": hm(adv.ts)}
        narrative = (f"Between the {hm(walk[0].ts)} entry bar and the final exit ({len(walk)} one-minute bars) the best excursion in favour was {prog['max_favourable_points']:.2f} points at {prog['max_favourable_at']} and the worst against "
                     f"was {prog['max_adverse_points']:.2f} points at {prog['max_adverse_at']}. ") + narrative
    total = sum(x.gross_pnl_rs for x in legs if x.gross_pnl_rs is not None)
    if all(x.gross_pnl_rs is not None for x in legs) and abs(total - r.pnl_rupees) > 1e-6:
        for x in legs:
            x.flags.append("PNL_MISMATCH_WITH_ENGINE")
    if amb:
        narrative += " Execution ambiguity flagged: " + " | ".join(amb)
    return legs, narrative, prog


def trade_row(day, tr: TradeRecord, inp: DayInputs, ex: Explanation, legs: list[LegExit], narrative: str, prog: dict, cfg_id: str, partition: str) -> dict[str, Any]:
    """The flat trade record (one per executed trade), joined with the Phase 3.0 ledger fields."""
    led = ledger_row("baseline", day, tr, inp.result)
    sig = tr.signal
    fill_bar = _bar_at(inp.bars, tr.fill_timestamp)
    fixed, slip_pts = HEADLINE_COST
    net = led["gross_pnl_rs"] - fixed - slip_pts * 2 * led["qty_total"]
    return {
        "trade_id": ex.trade_id, "date": str(day), "weekday": f"{day:%A}", "chart_file": f"charts/{ex.trade_id}.svg", "daily_journal": f"daily/{day:%Y-%m}/{day}.md", "strategy": sig.strategy, "method": sig.method, "direction": sig.direction,
        "trade_no_of_day": tr.trade_no, "first_or_second": "FIRST" if tr.trade_no == 1 else "SECOND", "rule_configuration_id": cfg_id,
        "signal_candle_start": f"{sig.signal_candle_start:%H:%M}", "signal_candle_end": f"{sig.signal_timestamp:%H:%M}",
        "signal_confirmed_at": f"{sig.signal_timestamp:%Y-%m-%d %H:%M}", "fill_timestamp": f"{tr.fill_timestamp:%Y-%m-%d %H:%M}", "entry_price": tr.entry_price,
        "entry_source_partition": partition, "entry_source_bar_ts": f"{fill_bar.ts:%Y-%m-%d %H:%M}" if fill_bar else "", "entry_bar_interval": "1-minute",
        "entry_bar_open": fill_bar.o if fill_bar else None, "entry_bar_high": fill_bar.h if fill_bar else None, "entry_bar_low": fill_bar.l if fill_bar else None, "entry_bar_close": fill_bar.c if fill_bar else None,
        "entry_fill_assumption": "open of the 1-minute bar starting at the signal candle's end (EXE-FILL-001, PROPOSED causal convention)", "entry_eligibility": "ELIGIBLE (continuous session, <= 13:00 IST)",
        "signal_reference_close": sig.signal_candle_close, "initial_stop": led["stop_level"], "target_1": led["t1_level"], "target_2": led["t2_level"],
        "post_t1_stop": tr.entry_price - (1 if sig.direction == "LONG" else -1) * inp.trade.post_t1_buffer_points,
        "post_t1_stop_status": "APPLIED_AFTER_TARGET_1" if led["post_t1_stop_level"] is not None else "NOT_REACHED (Target 1 was not booked)",
        "qty_total": led["qty_total"], "qty_leg1": led["qty_leg1"], "qty_leg2": led["qty_leg2"], "lots": inp.trade.total_lots, "lot_multiplier": inp.trade.lot_size,
        "setup_explanation": ex.setup_summary, "selection_explanation": ex.selection_summary,
        "checks_pass": sum(c.result == "PASS" for c in ex.checks), "checks_fail": sum(c.result == "FAIL" for c in ex.checks),
        "checks_unresolved": sum(c.result == "UNRESOLVED" for c in ex.checks), "checks_not_applicable": sum(c.result == "NOT_APPLICABLE" for c in ex.checks),
        "unresolved_items": " | ".join(ex.unresolved), "recomputation_mismatches": " | ".join(ex.mismatches), "signal_verification_status": sig.verification_status,
        "outcome": tr.classification, "exit_narrative": narrative,
        "leg1_exit_time": legs[0].exit_ts.strftime("%H:%M") if legs and legs[0].exit_ts else "", "leg1_exit_price": legs[0].exit_price if legs else None,
        "leg2_exit_time": legs[-1].exit_ts.strftime("%H:%M") if legs and legs[-1].exit_ts else "", "leg2_exit_price": legs[-1].exit_price if legs else None,
        "leg1_pnl_rs": legs[0].gross_pnl_rs if legs else None, "leg2_pnl_rs": legs[-1].gross_pnl_rs if legs else None,
        "gross_pnl_points_weighted": led["gross_points_weighted"], "gross_pnl_rs": led["gross_pnl_rs"], "illustrative_cost_rs": fixed, "illustrative_slippage_rs": slip_pts * 2 * led["qty_total"],
        "illustrative_net_pnl_rs": net, "adverse_slippage_points": led["adverse_slippage_points"], "execution_ambiguities": len(tr.result.ambiguities),
        "target2_status": led["target2_status"], "bars_held": prog.get("bars_held"), "max_favourable_points": prog.get("max_favourable_points"), "max_favourable_at": prog.get("max_favourable_at"),
        "max_adverse_points": prog.get("max_adverse_points"), "max_adverse_at": prog.get("max_adverse_at"),
        "day_final_state": led["day_final_state"], "resolved": led["resolved"],
    }
