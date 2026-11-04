"""Phase 3.1: trade-by-trade reconciliation of the manual journal with the automated engines. READ-ONLY diagnostics.

Nothing here changes a strategy rule, a parameter, a stop, a target, the cutoff or the selection policy, and nothing is fitted to the manual report.
The journal is not ground truth: its inconsistencies (Phase 2.1) are carried through as flags, not corrected.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path

from nifty_trading.research.phase3 import Scenario, make_engines
from nifty_trading.strategies.base import SignalRecord
from nifty_trading.strategies.definitions import (
    gap_info,
    pdr_zone,
    pds_zone,
    prev_high_low,
    to_candles,
    trend_check,
)
from nifty_trading.strategies.trading_day import DayResult, DayRules, run_trading_day

ROOT = Path(__file__).resolve().parents[3]
XLSX = ROOT / "docs" / "trading journal" / "Trading_Journal_Sep2025_Aug2026 REPORT.xlsx"
REPORT_TXT = ROOT / "docs" / "extracted_text" / "Performance_Report.txt"
CUTOFF = time(13, 0)
TOL_MIN = 15  # a manual entry label and an automated signal candle start within this many minutes are a labelled TIME_SHIFTED_MATCH (3 candles)
IMPLIED_DIRECTION = {"IRF": "SHORT", "PDS": "SHORT", "PDR": "LONG", "RF": "LONG", "ORB": "UNKNOWN"}  # journal has no direction column; RF long is implied (PROPOSED)
T2_CANDIDATES = {"IRF": (60,), "ORB": (60,), "PDR": (60, 70), "PDS": (60, 70), "RF": (60,)}
STOP_CANDIDATES = {"IRF": (35, 40), "ORB": (30,), "PDR": (35, 40), "PDS": (35, 40), "RF": (35, 40)}
OUTCOME_ANALOGUE = {"Target": "TARGET", "BE": "T1_THEN_EXACT_ENTRY_EXIT(old rule) ~ T1_THEN_BUFFER_STOP", "SL": "INITIAL_FULL_STOP"}


def hhmm(v) -> str:
    return v.strftime("%H:%M") if isinstance(v, time) else str(v)[:5]


def _minutes(s: str) -> int:
    h, m = s.split(":")
    return int(h) * 60 + int(m)


# ================================================================================================ the manual journal
def load_journal() -> list[dict]:
    """Every journal row exactly as entered (original values preserved)."""
    import openpyxl
    ws = openpyxl.load_workbook(str(XLSX), data_only=True)["Trading Journal"]
    out = []
    for i, r in enumerate(ws.iter_rows(values_only=True), start=1):
        if i <= 2 or r[0] is None or not isinstance(r[0], (int, float)):
            continue
        d = r[1].date() if isinstance(r[1], datetime) else r[1]
        out.append({"sheet_row": i, "sl_no": int(r[0]), "date": str(d), "time_raw": r[2], "time_cell_type": type(r[2]).__name__, "time": hhmm(r[2]),
                    "strategy_entered": str(r[3]), "outcome_entered": str(r[4])})
    return out


def report_listed_pnl() -> dict[tuple[str, str, str], list[int]]:
    """The only per-trade P&L figures printed in the report (its drawdown-window table): (date, strategy, outcome) -> [Rs]."""
    out: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    mon = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
    for line in REPORT_TXT.read_text().splitlines():
        m = re.match(r"^\s*(\d+) \| (\d{2}) (\w{3}) (\d{4}) \| (\w+) \| (\w+) \| ([–\-]?)₹([\d,]+) \|", line)
        if not m:
            continue
        _, dd, mm, yy, strat, outc, neg, amt = m.groups()
        d = f"{yy}-{mon[mm]:02d}-{dd}"
        out[(d, strat, outc)].append(-int(amt.replace(",", "")) if neg else int(amt.replace(",", "")))
    return dict(out)


def normalize_journal(rows: list[dict], phase21_rows: list[dict], alt_candidates: dict[int, str], session_status: dict[str, str]) -> list[dict]:
    """The normalized table. Original values stay in the *_entered / *_raw columns; nothing is silently changed."""
    p21 = {r["sheet_row"]: r for r in phase21_rows}
    listed = report_listed_pnl()
    by_day: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_day[r["date"]].append(r)
    out = []
    for d, rs in by_day.items():
        rs.sort(key=lambda x: (_minutes(x["time"]), x["sheet_row"]))
        for k, r in enumerate(rs, start=1):
            s = r["strategy_entered"].strip().upper()
            fill = datetime(2000, 1, 1) + timedelta(minutes=_minutes(r["time"]) + 5)  # entry time label = candle START; the fill is at its end
            late = (fill.time() > CUTOFF)
            dow = date.fromisoformat(d).strftime("%a")
            sess = session_status.get(d)
            reasons = []
            if sess is None:
                reasons.append("DATE_HAS_NO_VENDOR_SESSION")
            if late:
                reasons.append("ENTRY_AFTER_13_00_CUTOFF")
            if k == 2:
                first = rs[0]
                if first["outcome_entered"] != "SL":
                    reasons.append(f"SECOND_TRADE_NOT_ALLOWED(first_trade_outcome={first['outcome_entered']})")
                elif s not in ("PDR", "PDS"):
                    reasons.append(f"SECOND_TRADE_NOT_PDR_PDS({s})")
            elif k > 2:
                reasons.append("THIRD_TRADE_NOT_ALLOWED")
            t2c, scn = T2_CANDIDATES.get(s, ()), STOP_CANDIDATES.get(s, ())
            if r["outcome_entered"] == "Target":
                pnl = [27 * 195 + t * 195 for t in t2c]
            elif r["outcome_entered"] == "BE":
                pnl = [27 * 195]
            else:
                pnl = [-x * 390 for x in scn]
            p21r = p21.get(r["sheet_row"], {})
            dup = sum(1 for x in rs if x["time"] == r["time"] and x["strategy_entered"] == r["strategy_entered"]) > 1
            lst = listed.get((d, s, r["outcome_entered"]))
            out.append({
                "journal_row": r["sheet_row"], "sl_no": r["sl_no"], "date": d, "weekday": dow, "entry_time_label": r["time"], "entry_time_original": str(r["time_raw"]),
                "entry_time_cell_type": r["time_cell_type"], "estimated_fill_time": f"{fill:%H:%M}", "strategy_entered": r["strategy_entered"], "strategy_normalized": s,
                "alt_strategy_candidate": alt_candidates.get(r["sheet_row"], ""), "direction": IMPLIED_DIRECTION.get(s, "UNKNOWN"),
                "direction_basis": "strategy-implied (PROPOSED for RF)" if s in ("IRF", "PDS", "PDR", "RF") else "not recorded (ORB trades both ways)",
                "entry_level": "", "entry_level_note": "not recorded in the journal", "original_stop_points": "|".join(map(str, scn)), "target1_points": 27,
                "target2_points": "|".join(map(str, t2c)), "exit_classification_entered": r["outcome_entered"], "exit_class_under_current_rules": OUTCOME_ANALOGUE.get(r["outcome_entered"], "?"),
                "report_listed_pnl_rs": ("|".join(map(str, lst)) if lst else ""), "derived_pnl_rs_low": min(pnl) if pnl else "", "derived_pnl_rs_high": max(pnl) if pnl else "",
                "pnl_basis": "listed in the report's table 7" if lst else "DERIVED from the outcome with the report's payoff rules (stop/T2 candidates), not recorded per trade",
                "trade_no_in_day": k, "trades_that_day": len(rs), "session_status": sess or "NO_SESSION", "conforms_to_approved_rules": not reasons,
                "nonconformity": ";".join(reasons), "duplicate_flag": dup, "phase21_status": p21r.get("status", ""), "phase21_reasons": ";".join(p21r.get("reasons", [])),
                "source_reference": f"Trading Journal!A{r['sheet_row']}:E{r['sheet_row']} (sheet row {r['sheet_row']})",
                "confidence": "HIGH" if p21r.get("status") == "VALID" and not dup else ("LOW" if p21r.get("status") in ("INVALID", "UNRESOLVED") else "MEDIUM"),
            })
    out.sort(key=lambda x: x["journal_row"])
    return out


# ================================================================================================ the automated timeline
@dataclass
class DayTimeline:
    day: date
    ctx: object
    records: list[SignalRecord]
    result: DayResult


def run_timelines(sc: Scenario, ctxs: dict, bars_by_day: dict, rules: DayRules | None = None) -> dict[date, DayTimeline]:
    engines = make_engines(sc.proposals, sc.trade)
    out = {}
    for d in sorted(ctxs):
        recs = [r for e in engines for r in e.evaluate_session(ctxs[d])]
        out[d] = DayTimeline(d, ctxs[d], recs, run_trading_day(d, recs, bars_by_day[d], sc.trade, rules or DayRules()))
    return out


def _key(r: SignalRecord):
    return (r.signal_timestamp, r.strategy, r.method, r.direction)


def state_at(tl: DayTimeline, ts: datetime) -> str:
    """The portfolio state a signal confirmed at ``ts`` meets (replayed from the executed trades)."""
    trades = tl.result.trades
    collision_before = any(d.event == "CONFLICT" and d.timestamp is not None and d.timestamp <= ts for d in tl.result.diagnostics)
    if not trades or ts < trades[0].fill_timestamp:
        # causal: a collision AT OR BEFORE ts under the default policy leaves the day unresolved (final_state only says which policy applied)
        return "UNRESOLVED_EXECUTION" if collision_before and tl.result.final_state.value == "UNRESOLVED_EXECUTION" else "READY_FOR_FIRST_TRADE"
    for i, t in enumerate(trades):
        end = t.position_end
        if ts >= t.fill_timestamp and (end is None or ts < end):
            return "FIRST_TRADE_ACTIVE" if i == 0 else "SECOND_TRADE_ACTIVE"
        if end is not None and ts >= end:
            last = i == len(trades) - 1
            nxt_ts = trades[i + 1].fill_timestamp if not last else None
            if nxt_ts is not None and ts >= nxt_ts:
                continue
            if t.classification == "INITIAL_FULL_STOP" and i == 0:
                return "SECOND_TRADE_ELIGIBLE"
            if t.classification in ("INCOMPLETE_EOD", "NOT_EVALUABLE"):
                return "UNRESOLVED_EXECUTION"
            return "DAY_FINISHED"
    return tl.result.final_state.value


def blocker_of(tl: DayTimeline, ts: datetime, reason: str) -> str:
    """Which earlier trade / rule consumed the opportunity of a signal that was ignored or rejected."""
    trades = tl.result.trades
    if reason.startswith("POSITION_ACTIVE"):
        for i, t in enumerate(trades):
            if t.fill_timestamp <= ts and (t.position_end is None or ts < t.position_end):
                return f"{t.signal.strategy}#{i + 1}"
    if reason in ("DAY_FINISHED", "DAY_UNRESOLVED_EXECUTION") or reason.startswith("SECOND_TRADE_RESTRICTED"):
        prior = [t for t in trades if t.position_end is not None and t.position_end <= ts]
        if prior:
            return f"{prior[-1].signal.strategy}#{trades.index(prior[-1]) + 1}"
        if any(d.event == "CONFLICT" and d.timestamp is not None and d.timestamp <= ts for d in tl.result.diagnostics):
            return "COLLISION"
        if trades and trades[0].fill_timestamp <= ts:
            return f"{trades[0].signal.strategy}#1"
    if reason.startswith("ENTRY_CUTOFF"):
        return "CUTOFF_13_00"
    if reason.startswith("ENTRY_NOT_FILLABLE") or reason.startswith("ENTRY_BLOCKED"):
        return "NO_FILLABLE_BAR"
    return ""


def timeline_rows(tl: DayTimeline, scenario: str, manual_today: list[dict]) -> list[dict]:
    """Chronological events of one session: every engine record (confirmed signals with their portfolio disposition, failed/incomplete setups),
    the executions and the manual journal entries."""
    diag = defaultdict(list)
    for x in tl.result.diagnostics:
        diag[(x.timestamp, x.strategy, x.method, x.direction)].append(x)
    executed = {(t.signal.signal_timestamp, t.signal.strategy, t.signal.method, t.signal.direction): t for t in tl.result.trades}
    conflicts = [(d.timestamp, set(d.strategy.split("+")), d.reason) for d in tl.result.diagnostics if d.event == "CONFLICT"]

    def conflict_at(ts, strat):
        for cts, strats, why in conflicts:
            if cts == ts and strat in strats:
                return why
        return ""

    rows = []
    for r in tl.records:
        ts = r.signal_timestamp
        base = {"scenario": scenario, "date": str(tl.day), "strategy": r.strategy, "method": r.method, "direction": r.direction,
                "candle_start": f"{r.signal_candle_start:%H:%M}" if r.signal_candle_start else "", "signal_status": r.signal_status,
                "invalidation_reason": r.invalidation_reason or "", "rules_unresolved": ";".join(r.rule_ids_unresolved), "rules_failed": ";".join(r.rule_ids_failed)}
        if r.signal_status == "CONFIRMED" and ts is not None:
            k = _key(r)
            if k in executed:
                t = executed[k]
                ev, why, blocker = "EXECUTED", f"trade {t.trade_no}: {t.classification}", ""
            else:
                ds = [d for d in diag.get(k, []) if d.event != "NOTE"]
                if ds:
                    ev, why = ds[0].event, ds[0].reason
                    blocker = blocker_of(tl, ts, why)
                elif conflict_at(ts, r.strategy):
                    ev, why, blocker = "CONFLICT", conflict_at(ts, r.strategy), "COLLISION"
                elif any(d.event == "NOTE" for d in diag.get(k, [])):
                    ev, why, blocker = "MERGED_SAME_STRATEGY_METHOD", "traded as another method of the same strategy/direction in the same minute", ""
                else:
                    ev, why, blocker = "NOT_LOGGED", "", ""
            base.update({"time": f"{ts:%H:%M}", "event": ev, "disposition_reason": why, "blocked_by": blocker, "portfolio_state": state_at(tl, ts)})
        else:
            base.update({"time": f"{r.signal_candle_start:%H:%M}" if r.signal_candle_start else "", "event": "SETUP_" + r.signal_status, "disposition_reason": r.invalidation_reason or "",
                         "blocked_by": "", "portfolio_state": ""})
        rows.append(base)
    for m in manual_today:
        rows.append({"scenario": scenario, "date": str(tl.day), "strategy": m["strategy_normalized"], "method": "", "direction": m["direction"], "candle_start": m["entry_time_label"],
                     "signal_status": "MANUAL", "invalidation_reason": "", "rules_unresolved": "", "rules_failed": "", "time": m["entry_time_label"], "event": "MANUAL_ENTRY",
                     "disposition_reason": f"journal row {m['journal_row']}: {m['exit_classification_entered']}" + (f" [{m['nonconformity']}]" if m["nonconformity"] else ""),
                     "blocked_by": "", "portfolio_state": ""})
    rows.sort(key=lambda x: (x["time"] or "99:99", 0 if x["event"] == "MANUAL_ENTRY" else 1, x["strategy"], x["method"]))
    return rows


# ================================================================================================ probes: why is there no setup?
def probe(strategy: str, tl: DayTimeline, props) -> dict:
    """Base conditions of a strategy on a session, computed straight from the candles (diagnostic, not a signal)."""
    ctx = tl.ctx
    out: dict = {"open": ctx.open_price}
    if ctx.candles.empty:
        return {"code": "NO_CANDLES"}
    cs = to_candles(ctx.candles)
    c0 = cs[0]
    rng = c0.h - c0.l
    out.update({"c0_o": c0.o, "c0_h": c0.h, "c0_l": c0.l, "c0_c": c0.c, "c0_body_ratio": round(abs(c0.c - c0.o) / rng, 3) if rng else 0.0})
    if strategy == "IRF":
        irh, irl = c0.h, c0.l
        up = [c for c in cs[1:] if c.c > irh and c.end.time() <= time(13, 0)]
        out.update({"irh": irh, "irl": irl, "breakout_closes_before_13": len(up)})
        out["code"] = "NO_CLOSE_ABOVE_IRH_BEFORE_13_00" if not up else "BREAKOUT_EXISTS"
        return out
    prev = ctx.previous
    if prev is None:
        out["code"] = "NO_PREVIOUS_SESSION"
        return out
    ph, pl = prev_high_low(prev, props)
    g = gap_info(ctx, props)
    out.update({"prev_high": ph, "prev_low": pl, "gap_points": g.points, "gap_dir": g.direction, "gap_ok": g.evaluable})
    if strategy == "ORB":
        beyond_hi, beyond_lo = c0.c > ph and c0.h > ph, c0.c < pl and c0.l < pl
        touch_only = (c0.h > ph and not beyond_hi) or (c0.l < pl and not beyond_lo)
        c0_ema = float(ctx.candles["ema200_5m"].iloc[0])
        out.update({"c0_close_beyond_prev_high": bool(beyond_hi), "c0_close_beyond_prev_low": bool(beyond_lo), "wick_only_break": bool(touch_only), "ema_c0": c0_ema})
        if beyond_hi or beyond_lo:
            out["code"] = "LEVEL_BROKEN_BUT_FILTERED"
        else:
            out["code"] = "FIRST_CANDLE_DID_NOT_CLOSE_BEYOND_PREV_DAY_HIGH_OR_LOW"
        return out
    if strategy == "PDR":
        from dataclasses import replace as _rep
        z = pdr_zone(prev, props)
        out.update({"zone": None if z is None else [z.low, z.high]})
        # closest approach of any candle low to the zone top (<= 0: the candle range intersected the zone); for each candidate zone, for evidence only
        approach = {}
        for nm, meth in (("reversal_swing_high", "B_SWING_HIGH_REVERSAL"), ("repeated_shelf", "C_REPEATED_TOUCHES"), ("diagnostic_highest_high", "A_HIGHEST_HIGH")):
            zz = pdr_zone(prev, _rep(props, pdr_zone_method=meth))
            approach[nm] = None if zz is None else (round(min(min(c.l for c in cs) - zz.high, 0.0) if min(c.l for c in cs) <= zz.high else min(c.l for c in cs) - zz.high, 2),
                                                    bool(any(c.l <= zz.high and c.h >= zz.low for c in cs)))
        out["closest_low_minus_zone_high_and_intersected"] = approach
        if g.direction != "UP":
            out["code"] = "NO_GAP_UP"
        elif z is None:
            out["code"] = "NO_ZONE_CANDIDATE"
        elif ctx.open_price <= z.high:
            out["code"] = "GAP_UP_BUT_OPEN_NOT_ABOVE_ZONE"
        elif not any(c.l <= z.high and c.h >= z.low for c in cs):
            out["code"] = "ZONE_NEVER_INTERSECTED_BY_ANY_CANDLE"
        else:
            out["code"] = "GAP_UP_ZONE_TOUCHED"
        return out
    if strategy == "PDS":
        z = pds_zone(prev, props)
        out.update({"zone": [z.low, z.high]})
        out["code"] = "NO_GAP_DOWN" if g.direction != "DOWN" else "GAP_DOWN_AND_ZONE_EXIST"
        return out
    if strategy == "RF":
        within = prev.low <= ctx.open_price <= prev.high if hasattr(prev, "low") else (pl <= ctx.open_price <= ph)
        closes_below = [c for c in cs[1:] if c.c < c0.l]
        returned = False
        if closes_below:
            i0 = cs.index(closes_below[0])
            returned = any(c0.l <= c.c <= c0.h for c in cs[i0 + 1:])
        t = trend_check(ctx, 0, "LONG", props.trend_mode, props)
        out.update({"open_within_prev_range": bool(within), "close_below_rf_low": bool(closes_below), "returned_inside": bool(returned), "trend_ok": t.ok, "trend_reason": t.reason})
        if g.direction != "UP":
            out["code"] = "NO_GAP_UP"
        elif not within:
            out["code"] = "GAP_UP_OUTSIDE_PREV_RANGE"
        elif not closes_below:
            out["code"] = "NO_CLOSE_BELOW_RF_LOW"
        elif not returned:
            out["code"] = "NO_RETURN_INSIDE"
        elif t.ok is not True:
            out["code"] = "TREND_NOT_ESTABLISHED"
        else:
            out["code"] = "SEQUENCE_COMPLETE"
        return out
    out["code"] = "UNKNOWN"
    return out


# ================================================================================================ matching
CLASSES = ("EXACT_MATCH", "TIME_SHIFTED_MATCH", "PRICE_DIFFERENCE", "MISSING_AUTOMATED_SIGNAL", "SIGNAL_GENERATED_BUT_BLOCKED", "SIGNAL_REJECTED_BY_ENTRY_RULE",
           "SIGNAL_REJECTED_BY_CUTOFF", "SIGNAL_REJECTED_BY_PORTFOLIO_CONTROLLER", "SOURCE_RULE_AMBIGUITY", "MANUAL_JOURNAL_CONFLICT", "DATA_DIFFERENCE", "UNRESOLVED")


def _cstart(sig: SignalRecord) -> int:
    return sig.signal_candle_start.hour * 60 + sig.signal_candle_start.minute


def match_manual_to_automated(manual: list[dict], timelines: dict[date, DayTimeline], props, tol: int = TOL_MIN) -> tuple[list[dict], set]:
    """Deterministic one-to-one matching of manual trades to EXECUTED automated trades, then a rejection-chain classification of what is left.

    Order: manual rows by (date, entry label, journal row). Pass 1 exact (same date, strategy, signal-candle start == label); pass 2 time-shifted
    (nearest candle start within ``tol`` minutes, ties to the earlier); pass 3 the same under the row's alternate strategy label (Phase 2.1 attribution
    candidates), flagged. An automated trade is matched at most once. P&L is never used to match."""
    used: set[tuple] = set()  # (date, strategy, signal_timestamp, method, direction) of matched automated trades
    results: dict[int, dict] = {}
    order = sorted(manual, key=lambda m: (m["date"], _minutes(m["entry_time_label"]), m["journal_row"]))

    def cands(day: date, strat: str):
        tl = timelines.get(day)
        return [] if tl is None else [t for t in tl.result.trades if t.signal.strategy == strat and (str(day), strat, t.signal.signal_timestamp, t.signal.method, t.signal.direction) not in used]

    def try_pass(m, strat, label_tol, tag, alt):
        day = date.fromisoformat(m["date"])
        lab = _minutes(m["entry_time_label"])
        best = None
        for t in cands(day, strat):
            dt = _cstart(t.signal) - lab
            if abs(dt) <= label_tol and (best is None or (abs(dt), dt) < (abs(best[1]), best[1])):
                best = (t, dt)
        if best is None:
            return False
        t, dt = best
        used.add((m["date"], strat, t.signal.signal_timestamp, t.signal.method, t.signal.direction))
        results[m["journal_row"]] = {"classification": tag if dt else "EXACT_MATCH", "matched_trade": t, "delta_minutes": dt, "alt_label_used": alt}
        return True

    for tol_pass, name in ((0, "EXACT_MATCH"), (tol, "TIME_SHIFTED_MATCH")):
        for m in order:
            if m["journal_row"] in results or m["session_status"] == "NO_SESSION":
                continue
            if try_pass(m, m["strategy_normalized"], tol_pass, name, False):
                continue
        for m in order:
            if m["journal_row"] in results or m["session_status"] == "NO_SESSION" or not m["alt_strategy_candidate"]:
                continue
            try_pass(m, m["alt_strategy_candidate"], tol_pass, name, True)
    rows = []
    for m in order:
        day = date.fromisoformat(m["date"])
        tl = timelines.get(day)
        row = {k: m[k] for k in ("journal_row", "date", "entry_time_label", "strategy_normalized", "alt_strategy_candidate", "direction", "exit_classification_entered",
                                 "conforms_to_approved_rules", "nonconformity", "phase21_status", "confidence", "trade_no_in_day", "trades_that_day")}
        res = results.get(m["journal_row"])
        if res:
            t = res["matched_trade"]
            row.update({"classification": res["classification"], "matched_via_alternate_label": res["alt_label_used"],
                        "matched_strategy": t.signal.strategy, "matched_method": t.signal.method, "matched_direction": t.signal.direction,
                        "auto_candle_start": f"{t.signal.signal_candle_start:%H:%M}", "auto_entry_time": f"{t.fill_timestamp:%H:%M}", "auto_entry_price": t.entry_price,
                        "delta_minutes": res["delta_minutes"], "auto_trade_no": t.trade_no, "auto_outcome": t.classification,
                        "outcome_agrees_loosely": _loose_agree(m["exit_classification_entered"], t.classification), "chain": "EXECUTED", "blocked_by": "", "detail": ""})
            rows.append(row)
            continue
        row.update({"matched_via_alternate_label": False, "matched_strategy": "", "matched_method": "", "matched_direction": "", "auto_candle_start": "", "auto_entry_time": "",
                    "auto_entry_price": "", "delta_minutes": "", "auto_trade_no": "", "auto_outcome": "", "outcome_agrees_loosely": ""})
        row.update(_classify_unmatched(m, tl, props))
        rows.append(row)
    return rows, used


def _loose_agree(manual: str, auto: str) -> bool:
    """Descriptive only: Target~TARGET, BE~T1 then a stop, SL~INITIAL_FULL_STOP (different stop rules, so not expected to be identical)."""
    return (manual, auto) in (("Target", "TARGET"), ("BE", "T1_THEN_BUFFER_STOP"), ("SL", "INITIAL_FULL_STOP"))


def _classify_unmatched(m: dict, tl: DayTimeline | None, props) -> dict:
    """The rejection chain of a manual trade that no executed automated trade matches."""
    if m["session_status"] == "NO_SESSION" or tl is None:
        return {"classification": "MANUAL_JOURNAL_CONFLICT", "chain": "NO_SESSION", "blocked_by": "", "detail": "DATE_HAS_NO_VENDOR_SESSION (" + (m["weekday"]) + ")"}
    s, lab = m["strategy_normalized"], _minutes(m["entry_time_label"])
    # 1) raw CONFIRMED signals of that strategy that session, nearest to the manual label
    raw = [r for r in tl.records if r.strategy == s and r.signal_status == "CONFIRMED" and r.signal_candle_start is not None]
    near = sorted(raw, key=lambda r: abs(_cstart(r) - lab))
    if near and abs(_cstart(near[0]) - lab) <= TOL_MIN:
        r = near[0]
        rows = timeline_rows(tl, "x", [])
        mine = [x for x in rows if x["event"] not in ("MANUAL_ENTRY",) and x["strategy"] == s and x["method"] == r.method and x["time"] == f"{r.signal_timestamp:%H:%M}" and x["signal_status"] == "CONFIRMED"]
        ev = mine[0] if mine else {"event": "NOT_LOGGED", "disposition_reason": "", "blocked_by": ""}
        reason = ev["disposition_reason"]
        if reason.startswith("ENTRY_CUTOFF"):
            cl = "SIGNAL_REJECTED_BY_CUTOFF"
        elif reason.startswith(("ENTRY_NOT_FILLABLE", "ENTRY_BLOCKED", "DIAGNOSTIC_ONLY")):
            cl = "SIGNAL_GENERATED_BUT_BLOCKED"
        elif ev["event"] in ("IGNORED", "REJECTED", "CONFLICT", "MERGED_SAME_STRATEGY_METHOD"):
            cl = "SIGNAL_REJECTED_BY_PORTFOLIO_CONTROLLER"
        else:
            cl = "UNRESOLVED"
        return {"classification": cl, "chain": f"RAW_CONFIRMED_SIGNAL {r.method} {r.signal_timestamp:%H:%M} -> {ev['event']}", "blocked_by": ev["blocked_by"],
                "detail": reason, "nearest_signal_delta_minutes": _cstart(r) - lab}
    # 2) a setup that started and failed (INVALIDATED / INCOMPLETE) for that strategy
    # time-anchored: a setup explains the manual row only if it failed at or before the manual label (+ tolerance); an INCOMPLETE_AT_EOD record is
    # stamped with the LAST candle of the session, so it counts only when the manual label lies within the tolerance of that stamp (otherwise it is
    # reported as a pending setup that was never confirmed, which is end-of-day information and not an explanation of an earlier decision)
    def _anchored(r):
        st = _cstart(r) if r.signal_candle_start is not None else None
        if r.signal_status == "INVALIDATED":
            return st is None or st <= lab + TOL_MIN
        return st is not None and abs(st - lab) <= TOL_MIN

    fails = [r for r in tl.records if r.strategy == s and r.signal_status in ("INVALIDATED", "INCOMPLETE_AT_EOD") and _anchored(r)]
    pending = [r for r in tl.records if r.strategy == s and r.signal_status == "INCOMPLETE_AT_EOD" and r not in fails]
    if fails:
        # every failed setup of that strategy that session, the closest to the manual label first; for ORB the first-listed method (Method 1) leads the cause
        order_pref = {"Method 1": 0, "Gap/200DMA": 1, "Method 2": 2}
        fs = sorted(fails, key=lambda r: (order_pref.get(r.method, 9), abs((_cstart(r) if r.signal_candle_start else lab) - lab)))
        lead = fs[0]
        allr = " | ".join(f"{r.method}:{r.invalidation_reason}" for r in fs)
        return {"classification": "SIGNAL_REJECTED_BY_ENTRY_RULE", "chain": f"SETUP_{lead.signal_status} {lead.method}", "blocked_by": "",
                "detail": f"{lead.invalidation_reason}; failed={';'.join(lead.rule_ids_failed)}", "all_failed_setups": allr}
    ne = [r for r in tl.records if r.strategy == s and r.signal_status == "NOT_EVALUATED"]
    if ne:
        return {"classification": "DATA_DIFFERENCE", "chain": "NOT_EVALUATED", "blocked_by": "", "detail": ne[0].invalidation_reason or ""}
    p = probe(s, tl, props)
    out = {"classification": "MISSING_AUTOMATED_SIGNAL", "chain": "NO_CONFIRMED_SIGNAL_WITHIN_TOLERANCE_AND_NO_ANCHORED_SETUP_RECORD", "blocked_by": "", "detail": p.get("code", ""),
           "probe": {k: v for k, v in p.items() if k != "code"}}
    if near:
        out["nearest_signal_delta_minutes"] = _cstart(near[0]) - lab  # a confirmed signal exists that day, but outside the tolerance
        out["chain"] += f"; NEAREST_CONFIRMED_{near[0].method}_{near[0].signal_timestamp:%H:%M}"
    if pending:
        out["chain"] += "; SETUP_PENDING_NEVER_CONFIRMED_AT_" + ",".join(f"{r.signal_timestamp:%H:%M}" for r in pending)
    return out


# ================================================================================================ root causes
def root_cause_manual(row: dict) -> tuple[str, str]:
    """(primary, secondary) cause of a manual trade the automated ledger does not contain. Heuristic mapping from the evidence column; 'UNKNOWN' when the evidence does not decide."""
    cl, detail = row["classification"], str(row.get("detail", ""))
    sec = ""
    if row.get("phase21_status") in ("UNRESOLVED", "INVALID"):
        sec = "JOURNAL_INCONSISTENCY"
    if cl.startswith("EXACT") or cl.startswith("TIME_SHIFTED"):
        return "", ""
    if cl == "MANUAL_JOURNAL_CONFLICT":
        return "JOURNAL_INCONSISTENCY", ""
    if cl == "SIGNAL_REJECTED_BY_PORTFOLIO_CONTROLLER":
        return "PORTFOLIO_COMPETITION", sec
    if cl == "SIGNAL_REJECTED_BY_CUTOFF":
        return "EXECUTION_CONVENTION", sec
    if cl == "SIGNAL_GENERATED_BUT_BLOCKED":
        return "EXECUTION_CONVENTION", sec
    if cl == "DATA_DIFFERENCE":
        return "DATA_DIFFERENCE", sec
    if cl == "SIGNAL_REJECTED_BY_ENTRY_RULE":
        d = detail.upper()
        if d.startswith("TREND:"):
            return "TREND_FILTER", sec
        if d.startswith("TRENDLINE"):
            return "SOURCE_AMBIGUITY", ("ORB_INNER_LEVEL_TRENDLINE_NOT_IN_SOURCE;" + sec).strip(";")  # Method 2 construction is not defined by the guide
        if "CANDLE_QUALITY" in d:
            return "PROPOSED_NUMERICAL_THRESHOLD", sec
        if "ZONE" in d or "GAP_UP_OPEN" in d or "GAP_DOWN_OPEN" in d:
            return "ZONE_SELECTION", sec
        if any(k in d for k in ("NO_GREEN", "NO_RETURN", "SUPPORT_NOT", "NEAR_MA", "NO_RECENT", "NO_QUALIFYING", "NOT_INSIDE", "EXPIR")):
            return "ENTRY_SEQUENCE", sec
        if d.startswith(("GAP_NOT_UP", "GAP_UP_OUTSIDE", "GAP_DOWN_OUTSIDE")):
            return "SOURCE_AMBIGUITY", ("OPEN_PRICE_CONVENTION;" + sec).strip(";")  # which open / previous close / range the author used is not fixed by the guide
        if d.startswith("CLOSE_NOT_BEYOND_MA"):
            return "SOURCE_AMBIGUITY", ("MA_DEFINITION_UNRESOLVED;" + sec).strip(";")  # ORB-MA-001: 200 DMA vs 5-minute EMA is not settled
        return "UNKNOWN", ("UNMAPPED_ENTRY_RULE_DETAIL;" + sec).strip(";")  # no heuristic covers this detail: do not default it to a cause
    if cl == "MISSING_AUTOMATED_SIGNAL":
        code = detail
        if code in ("NO_GAP_UP", "NO_GAP_DOWN", "GAP_UP_OUTSIDE_PREV_RANGE"):
            return "SOURCE_AMBIGUITY", ("OPEN_PRICE_CONVENTION;" + sec).strip(";")  # the gap depends on which open / previous close the author used
        if code == "FIRST_CANDLE_DID_NOT_CLOSE_BEYOND_PREV_DAY_HIGH_OR_LOW":
            return "SOURCE_AMBIGUITY", sec  # what 'previous-day resistance/support' is (a zone? an inner level?) is not mechanical in the guide
        if code in ("NO_CLOSE_ABOVE_IRH_BEFORE_13_00",):
            return "TIME_ALIGNMENT", sec
        if code in ("NO_CLOSE_BELOW_RF_LOW", "NO_RETURN_INSIDE"):
            return "ENTRY_SEQUENCE", sec
        if code == "TREND_NOT_ESTABLISHED":
            return "TREND_FILTER", sec
        if code in ("NO_ZONE_CANDIDATE", "ZONE_NEVER_INTERSECTED_BY_ANY_CANDLE"):
            return "ZONE_SELECTION", sec
        return "UNKNOWN", sec
    return "UNKNOWN", sec


def interference_matrix(timelines: dict[date, DayTimeline]) -> tuple[Counter, Counter]:
    """(signals, distinct days) counted per (selected/blocking trade strategy, blocked strategy) from the ACTUAL timeline of the CONFIRMED signals."""
    sig: Counter = Counter()
    days: dict[tuple, set] = defaultdict(set)
    for d, tl in timelines.items():
        for x in timeline_rows(tl, "x", []):
            if x["signal_status"] != "CONFIRMED" or x["event"] in ("EXECUTED", "MERGED_SAME_STRATEGY_METHOD"):
                continue
            b = x["blocked_by"] or x["disposition_reason"][:28] or x["event"]
            key = (b.split("#")[0] if "#" in b else b, x["strategy"], x["event"])
            sig[key] += 1
            days[key].add(str(d))
    return sig, Counter({k: len(v) for k, v in days.items()})
