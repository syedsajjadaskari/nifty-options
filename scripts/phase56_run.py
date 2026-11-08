"""Phase 5.6: reconcile the automated trades of configurations A, B and C (Phase 5.5) with the ORIGINAL manual trading journal.

  python scripts/phase56_run.py

Reads the original workbook read-only (five source columns; nothing is corrected or relabelled; weekend-dated rows are flagged), runs the staged ONE-TO-ONE matching (strict / time-tolerant / date-and-strategy-only) separately for A, B and C, classifies every
mismatch by its earliest cause with the evidence (the diagnostics re-run the strategy engines on the actual candles), compares the 42 handwritten corrections with the three configurations and writes one explanation per evaluable session plus charts for the material
mismatches. Strategy rules are not changed anywhere; no outcome is used to choose a pair.
"""

from __future__ import annotations

import csv
import json
import sys
import warnings
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import date
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import phase56_charts as CH  # noqa: E402

from nifty_trading.research import phase3 as P  # noqa: E402
from nifty_trading.research import phase32_build as B  # noqa: E402
from nifty_trading.research import phase52_diag as D52  # noqa: E402
from nifty_trading.research import phase53 as F53  # noqa: E402
from nifty_trading.research import phase53_diag as D53  # noqa: E402
from nifty_trading.research import phase54_orb as O54  # noqa: E402
from nifty_trading.research import phase55 as X  # noqa: E402
from nifty_trading.research import phase56 as J  # noqa: E402
from nifty_trading.research.phase35 import write_csv  # noqa: E402

OUT = ROOT / "reports" / "phase5" / "phase56_manual_reconciliation"
P55 = ROOT / "reports" / "phase5" / "phase55_combined_backtest"
P53 = ROOT / "reports" / "phase5" / "phase53_author_corrected"
JOURNAL = ROOT / "docs" / "trading journal" / "Trading_Journal_Sep2025_Aug2026 REPORT.xlsx"
K = ("A", "B", "C")
ORB_CAUSE = {"level_broken": "LEVEL_CONSTRUCTION_MISMATCH", "inner_level_broken": "LEVEL_CONSTRUCTION_MISMATCH", "trendline": "TRENDLINE_MISMATCH", "trend": "EMA_FILTER_MISMATCH", "near_ema_close": "EMA_FILTER_MISMATCH",
             "candle_quality": "CANDLE_STRENGTH_MISMATCH", "candle_shape": "CANDLE_STRENGTH_MISMATCH", "gap_in_direction": "OPENING_GAP_MISMATCH", "gap_crosses_200_average": "OPENING_GAP_MISMATCH", "first_candle_closes_beyond_average": "OPENING_GAP_MISMATCH"}


def rd(p: Path) -> list[dict]:
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def fnum(x) -> float:
    return float(str(x).replace(",", "")) if x not in ("", None) else 0.0


def hm(ts) -> str:
    return f"{ts:%H:%M}"


class Ctx:
    """All the per-configuration material the explanations need."""

    def __init__(self) -> None:
        sc = P.combined_scenario("BODY_BASED_PHASE36")
        self.sc = sc
        self.bs = {}
        for k in K:
            with X.patched_engines(k):
                self.bs[k] = B.build(scenario=sc, journal=False)
        self.days = self.bs["A"].days
        self.ctx = {d: self.bs["A"].timelines[d].ctx for d in self.days}
        self.trades = {k: rd(P55 / "all_executed_trades.csv") for k in K}
        self.trades = {k: [t for t in v if t["config"] == k] for k, v in self.trades.items()}
        allsig = rd(P55 / "all_confirmed_signals.csv")
        self.sigs = {k: defaultdict(list) for k in K}
        for s in allsig:
            self.sigs[s["config"]][s["date"]].append(s)
        self.tby: dict = {k: {} for k in K}  # plain dicts: a lookup must never insert an empty day
        for k in K:
            for t in self.trades[k]:
                self.tby[k].setdefault(t["date"], []).append(t)
        self.rej: list = []
        F53.signals_for(self.ctx, sc, F53.COMBINED_KEY, self.rej)  # EMA-28 rejected IRF candidates (configurations B and C share the IRF engine)
        self.rej_by = defaultdict(list)
        for r in self.rej:
            self.rej_by[r["date"]].append(r)

    def records(self, k: str, d: str, strategy: str, confirmed: bool = False) -> list:
        tl = self.bs[k].timelines[date.fromisoformat(d)]
        return [r for r in tl.records if r.strategy == strategy and ((r.signal_status == "CONFIRMED") == confirmed)]

    def first_candle(self, d: str) -> dict:
        c = self.ctx[date.fromisoformat(d)]
        f = c.candles.iloc[0]
        rg = f.high - f.low
        return {"open": f.open, "high": f.high, "low": f.low, "close": f.close, "colour": "GREEN" if f.close > f.open else ("RED" if f.close < f.open else "DOJI"), "body_pct": round(100 * abs(f.close - f.open) / rg, 1) if rg else None}


# ------------------------------------------------------------------------------------------------------------------------------ strategy-specific "why was there no signal" diagnostics
def why_no_orb(cx: Ctx, k: str, d: str) -> tuple[str, str, str]:
    c = cx.ctx[date.fromisoformat(d)]
    p = cx.sc.proposals
    fc = cx.first_candle(d)
    long_c = fc["colour"] != "RED"
    pm = O54.predicate_matrix(c, p, long_c)
    if k == "C":  # the candidate engine reads the Gap crossing with the candle: adjust that predicate
        gr = O54.gap_crossing_readings(c, p, long_c)
        for r in pm["Gap/200DMA"]:
            if r["name"] == "gap_crosses_200_average" and gr["gap_in_direction"]:
                r["pass"] = bool(gr["alt_candle_crossing"])
    summ = {m: (sum(1 for r in rows if r["pass"] is False), O54.first_failing(rows)) for m, rows in pm.items()}
    order = ("Method 1", "Method 2", "Gap/200DMA")
    least = min(n for n, _f in summ.values())
    tied = [m for m in order if summ[m][0] == least]
    causes_tied = []
    for m in tied:
        cz = ORB_CAUSE.get(summ[m][1], "UNRESOLVED_DISCRETIONARY_SELECTION")
        if cz not in causes_tied:
            causes_tied.append(cz)
    best = tied[0]
    pred = summ[best][1]
    row = next((r for r in pm[best] if r["name"] == pred), None)
    cause = causes_tied[0]
    sec = causes_tied[1] if len(causes_tied) > 1 else ""
    tie = (f"TIE-BROKEN BY METHOD ORDER: {len(tied)} methods tie at {least} failing predicate(s) ({'; '.join(f'{m}: {summ[m][1]}' for m in tied)}) - the evidence does not single out one cause, the secondary cause is the other tied one; " if len(tied) > 1 else "")
    ev = (f"first candle {fc['colour']} O{fc['open']} H{fc['high']} L{fc['low']} C{fc['close']} (body {fc['body_pct']}%); direction ASSUMED from the colour (the journal has no direction); " + tie + f"closest method {best} "
          f"({least} failing predicate(s)): first failing '{pred}'" + (f" - {str(row['observed'])[:140]}" if row else "") + "; all methods: " + "; ".join(f"{m}: {n} fail ({f})" for m, (n, f) in summ.items()))
    return cause, sec, ev


def why_no_irf(cx: Ctx, k: str, d: str, m: J.JournalRow) -> tuple[str, str, str]:
    lab = J.minutes(m.time_label)
    near_a = [s for s in cx.sigs["A"][d] if s["strategy"] == "IRF" and abs(J.minutes(s["candle_start"]) - lab) <= J.TOL_TIME]
    if k in ("B", "C"):
        rj = [r for r in cx.rej_by[d] if abs(J.minutes(r["signal_time"]) - 5 - lab) <= J.TOL_TIME]
        if rj:
            r = rj[0]
            return "EMA_FILTER_MISMATCH", "", f"an IRF {r['method']} candidate at {r['signal_time']} was REJECTED by the 28-point EMA clearance (range distance {r.get('distance', 0):.1f}, EMA {r.get('relation')}) - PROVISIONAL_EMA_RANGE_DISTANCE"
        if near_a:
            s = near_a[0]
            return "LEVEL_CONSTRUCTION_MISMATCH", "", f"configuration A has IRF {s['method']} at {s['time']} but B / C do not: the first-red-candle LOW support replaces the swing-low support, which moves or removes the Method 2A signal (Method 2B / 1 / 3 unchanged)"
    recs = cx.records(k, d, "IRF")
    why = "; ".join(sorted({f"{r.method}: {r.invalidation_reason}" for r in recs if r.invalidation_reason}))[:200]
    return "UNRESOLVED_DISCRETIONARY_SELECTION", "", ("the engine produced no IRF signal near the manual entry" + (f" (setup records: {why})" if why else " (no IRF breakout / failure setup was seen)") + "; the journal gives no reason for the manual entry (rule points that are discretionary or unresolved: IRF Method 1 boundary IRF-M1-003, Method 3 wick share, the day's-low rule)")


def why_no_pdr_pds(cx: Ctx, k: str, d: str, strategy: str) -> tuple[str, str, str]:
    c = cx.ctx[date.fromisoformat(d)]
    sc = cx.sc
    if strategy == "PDR":
        g = D52.pdr_setup_diagnostics(c, sc) if k == "A" else D53.pdr_phase53_setup(c, sc)
        st = g["status"]
        if st == "NO_SETUP_NO_GAP_UP":
            return "OPENING_GAP_MISMATCH", "", f"PDR needs a gap up; the session opened {g.get('gap_direction')} (gap {g.get('gap_points')} points)"
        if st.startswith("NOT_ARMED"):
            return "LEVEL_CONSTRUCTION_MISMATCH", "", f"the open {g.get('session_open')} is not strictly above the previous-day body-based zone ceiling {g.get('zone_ceiling')} ({st})"
        if st == "ARMED_NO_ZONE_RETEST":
            return "LEVEL_CONSTRUCTION_MISMATCH", "", f"price never retested the previous-day body-based zone [{g.get('zone_floor')}, {g.get('zone_ceiling')}] after the gap up"
        return "CONFIRMATION_CANDLE_MISMATCH", "", f"the zone was retested but no confirmation candle qualified under the {'frozen numeric patterns' if k == 'A' else 'minimal earliest-confirmation convention'}"
    g = D52.pds_setup_diagnostics(c, sc) if k == "A" else D53.pds_phase53_first_red(c, sc)
    st = g["status"]
    if st == "NO_SETUP_NO_GAP_DOWN":
        return "OPENING_GAP_MISMATCH", "", f"PDS needs a gap down; the session opened {g.get('gap_direction')}"
    if st.startswith("NOT_ARMED"):
        return "LEVEL_CONSTRUCTION_MISMATCH", "", f"the open is not below the previous-day support zone ({st})"
    if st == "ARMED_NO_ZONE_RETEST":
        return "LEVEL_CONSTRUCTION_MISMATCH", "", "price never rose back into the previous-day support zone after the gap down"
    return "CONFIRMATION_CANDLE_MISMATCH", "", f"the zone was tested but no qualifying red-candle confirmation or small-support break followed ({st}; first red candle verdict {g.get('phase53_verdict', g.get('first_eligible_method', 'n/a'))})"


def why_no_rf(cx: Ctx, k: str, d: str) -> tuple[str, str, str]:
    recs = cx.records(k, d, "RF")
    reasons = sorted({f"{r.invalidation_reason}" for r in recs if r.invalidation_reason})
    why = "; ".join(reasons)[:200]
    found = []
    if any("TREND" in x or "EMA" in x for x in reasons):
        found.append(("EMA_FILTER_MISMATCH", "the trend / EMA condition"))
    if any("GAP" in x for x in reasons):
        found.append(("OPENING_GAP_MISMATCH", "the opening-gap condition (RF-004)"))
    if found:
        return found[0][0], (found[1][0] if len(found) > 1 else ""), f"RF setup rejected by {' and '.join(f[1] for f in found)} ({why})"
    return "UNRESOLVED_DISCRETIONARY_SELECTION", "", "the engine recorded no RF setup or invalidation reason" + (f" ({why})" if why else "") + "; the journal gives no reason for the manual RF entry"


def cause_manual(cx: Ctx, k: str, m: J.JournalRow, stage: str, pair) -> tuple[str, str, str]:
    d = m.date
    if m.weekend:
        return "MANUAL_JOURNAL_INCONSISTENCY", "", "the journal date is a Saturday: no exchange session and no market data exist for it; the row is kept as written (not relabelled)"
    if date.fromisoformat(d) not in cx.ctx:
        return "DATA_PROVIDER_DIFFERENCE", "", "the session is not in the evaluated dataset"
    if stage == "DATE_STRATEGY_ONLY":
        dt = pair.delta_minutes
        t = pair.trade
        return ("EARLIER_SIGNAL" if dt < 0 else "LATER_SIGNAL"), "ENTRY_TIME_MISMATCH", f"the automated {t['strategy']} trade has its signal candle at {t['signal_candle_start']} versus the manual label {m.time_label} ({dt:+d} minutes; outside the 15-minute tolerance)"
    S = [s for s in cx.sigs[k][d] if s["strategy"] == m.strategy]
    lab = J.minutes(m.time_label)
    near = [s for s in S if abs(J.minutes(s["candle_start"]) - lab) <= J.TOL_TIME]
    day = cx.tby[k].get(d, [])
    if near:
        s = min(near, key=lambda x: abs(J.minutes(x["candle_start"]) - lab))
        other = [t for t in day if t["strategy"] != m.strategy]
        why = f"the {m.strategy} signal at {s['time']} was {s['controller_event'] or 'not logged'}: {s['controller_reason'] or s['blocked_by'] or 'no reason logged'}"
        if other:
            return "DIFFERENT_STRATEGY_SELECTED", "PORTFOLIO_CONTROLLER_CONSTRAINT", f"the controller took {other[0]['strategy']} {other[0]['method']} (signal {other[0]['signal_candle_end'] if 'signal_candle_end' in other[0] else other[0]['fill_timestamp'][-5:]}) first; {why}"
        return "PORTFOLIO_CONTROLLER_CONSTRAINT", "", why
    if S:
        s = min(S, key=lambda x: abs(J.minutes(x["candle_start"]) - lab))
        early = J.minutes(s["candle_start"]) < lab
        gap_min = abs(J.minutes(s["candle_start"]) - lab)
        if gap_min > 60:  # a signal this far away is not the same trade: classify by why the engine has no signal near the manual entry
            fn = {"ORB": lambda: why_no_orb(cx, k, d), "IRF": lambda: why_no_irf(cx, k, d, m), "PDR": lambda: why_no_pdr_pds(cx, k, d, "PDR"), "PDS": lambda: why_no_pdr_pds(cx, k, d, "PDS"), "RF": lambda: why_no_rf(cx, k, d)}[m.strategy]
            c1, c2, evid = fn()
            return c1, c2, f"no automated {m.strategy} signal within 60 minutes of the manual label {m.time_label} (nearest: {s['time']}, candle {s['candle_start']}, {gap_min} minutes {'earlier' if early else 'later'}); " + evid
        return ("EARLIER_SIGNAL" if early else "LATER_SIGNAL"), "ENTRY_TIME_MISMATCH", f"the nearest automated {m.strategy} signal is at {s['time']} (candle {s['candle_start']}) versus the manual label {m.time_label}; it was {s['controller_event'] or 'not logged'}: {s['controller_reason']}"
    if m.strategy == "ORB":
        return why_no_orb(cx, k, d)
    if m.strategy == "IRF":
        return why_no_irf(cx, k, d, m)
    if m.strategy in ("PDR", "PDS"):
        return why_no_pdr_pds(cx, k, d, m.strategy)
    if m.strategy == "RF":
        return why_no_rf(cx, k, d)
    return "UNRESOLVED_DISCRETIONARY_SELECTION", "", "no automated signal of this strategy"


def main() -> int:  # noqa: C901
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "daily").mkdir(exist_ok=True)
    (OUT / "charts").mkdir(exist_ok=True)
    jrows, jsum = J.load_journal(JOURNAL)
    cx = Ctx()
    ev_days = {str(d) for d in cx.days}
    state: dict = {"journal": {"rows": len(jrows), "summary_sheet": {k: str(v) for k, v in jsum.items()}, "by_strategy": dict(Counter(r.strategy for r in jrows)), "weekend_rows": [(r.row_id, r.sheet_row, r.date, r.weekday, r.strategy) for r in jrows if r.weekend],
                               "rows_on_evaluated_sessions": sum(1 for r in jrows if r.date in ev_days), "rows_not_on_evaluated_sessions": [(r.row_id, r.date) for r in jrows if r.date not in ev_days], "time_label_types": dict(Counter(r.time_label_raw[:8].split("(")[0] for r in jrows)),
                               "outcomes": dict(Counter(r.outcome for r in jrows)), "dates_with_two_rows": sum(1 for v in Counter(r.date for r in jrows).values() if v == 2), "dates_with_three_or_more_rows": sum(1 for v in Counter(r.date for r in jrows).values() if v > 2)}}
    matches = {k: J.match(jrows, cx.trades[k]) for k in K}
    match_rows, strict_rows, tol_rows, manual_only, auto_only, causes = [], [], [], [], [], []
    delta_dist = Counter()
    for k in K:
        m_ = matches[k]
        pair_of = {p.manual.row_id: p for stage in ("strict", "tolerant", "date_strategy_only") for p in m_[stage]}
        for jr in jrows:
            pr = pair_of.get(jr.row_id)
            stage = pr.stage if pr else "UNMATCHED_MANUAL"
            base = {"config": k, "journal_row": jr.row_id, "sheet_row": jr.sheet_row, "date": jr.date, "weekday": jr.weekday, "manual_time_label": jr.time_label, "manual_strategy": jr.strategy, "manual_outcome": jr.outcome, "journal_flags": ";".join(jr.flags), "match_stage": stage}
            if pr:
                t = pr.trade
                agree = J.outcome_agrees(jr.outcome, t["outcome"])
                base.update({"trade_id": t["trade_id"], "auto_strategy": t["strategy"], "auto_method": t["method"], "auto_direction": t["direction"], "auto_signal_candle_start": t["signal_candle_start"], "auto_fill_time": t["fill_timestamp"][-5:], "auto_entry_price": t["entry_price"],
                             "delta_minutes_vs_signal_candle_start": pr.delta_minutes, "auto_outcome": t["outcome"], "outcome_class_agrees_descriptive": agree, "auto_leg1_exit": f"{t['leg1_exit_time']} @ {t['leg1_exit_price']}", "auto_leg2_exit": f"{t['leg2_exit_time']} @ {t['leg2_exit_price']}", "auto_gross_pnl_rs": t["gross_pnl_rs"]})
                delta_dist[(k, pr.stage, pr.delta_minutes)] += 1
            match_rows.append(base)
            if stage == "STRICT":
                strict_rows.append(base)
            elif stage == "TIME_TOLERANT":
                tol_rows.append(base)
            if stage in ("STRICT", "TIME_TOLERANT"):
                if not base["outcome_class_agrees_descriptive"]:
                    causes.append({**{c: base[c] for c in ("config", "journal_row", "date", "manual_strategy", "manual_time_label", "manual_outcome", "match_stage", "trade_id")}, "side": "MATCHED_DIFFERENT_OUTCOME", "root_cause_primary": "EXIT_MANAGEMENT_MISMATCH",
                                   "root_cause_secondary": "", "evidence": f"manual outcome '{jr.outcome}' (~{J.OUTCOME_CLASS.get(jr.outcome)}) versus automated {base['auto_outcome']}: legs {base['auto_leg1_exit']} / {base['auto_leg2_exit']}; the journal records no exit price or time, so the exit cannot be compared further"})
                continue
            c1, c2, evid = cause_manual(cx, k, jr, stage, pr)
            row = {**{c: base[c] for c in ("config", "journal_row", "sheet_row", "date", "weekday", "manual_time_label", "manual_strategy", "manual_outcome", "journal_flags", "match_stage")}, "trade_id": base.get("trade_id", ""), "root_cause_primary": c1, "root_cause_secondary": c2, "evidence": evid,
                   "automated_trades_that_day": " | ".join(f"{t['strategy']}/{t['method']} {t['signal_candle_start']} {t['outcome']}" for t in cx.tby[k].get(jr.date, [])) or "none", "confirmed_signals_of_the_manual_strategy_that_day": " | ".join(f"{s['time']} {s['method']} [{s['controller_event']}]" for s in cx.sigs[k][jr.date] if s["strategy"] == jr.strategy) or "none"}
            manual_only.append(row)
            causes.append({**{c: row[c] for c in ("config", "journal_row", "date", "manual_strategy", "manual_time_label", "manual_outcome", "match_stage", "trade_id")}, "side": "MANUAL_ONLY", "root_cause_primary": c1, "root_cause_secondary": c2, "evidence": evid})
        strong_ids = {p.manual.row_id for st_ in ("strict", "tolerant") for p in m_[st_]}
        for t in m_["trades_unmatched"] + [p.trade for p in m_["date_strategy_only"]]:
            md = [r for r in jrows if r.date == t["date"]]
            free = [r for r in md if r.row_id not in strong_ids]  # journal rows of the day not already matched to another trade
            sameday_other = [r for r in free if r.strategy != t["strategy"]]
            sameday_same = [r for r in free if r.strategy == t["strategy"]]
            first_of_day = next((x for x in cx.tby[k].get(t["date"], []) if x["trade_no_of_day"] == "1"), None)
            if t["trade_no_of_day"] == "2" and first_of_day is not None:
                c1, c2 = "PORTFOLIO_CONTROLLER_CONSTRAINT", ""
                evid = (f"second trade of the day: the controller allows a PDR / PDS re-entry after the original full stop of trade 1 ({first_of_day['strategy']} {first_of_day['method']}, signal candle {first_of_day['signal_candle_start']}); "
                        + ("the journal rows of the day not matched to another trade: " + ", ".join(f"{r.strategy} {r.time_label}" for r in free) if free else "the journal has no unmatched row that day"))
            elif sameday_same:
                c1 = "EARLIER_SIGNAL" if J.minutes(t["signal_candle_start"]) < J.minutes(sameday_same[0].time_label) else "LATER_SIGNAL"
                c2, evid = "ENTRY_TIME_MISMATCH", f"the journal has {t['strategy']} at {sameday_same[0].time_label}; the automated trade's signal candle is {t['signal_candle_start']}"
            elif sameday_other:
                c1, c2 = "DIFFERENT_STRATEGY_SELECTED", ""
                evid = "the journal traded " + ", ".join(f"{r.strategy} {r.time_label}" for r in sameday_other) + f"; the automated controller took {t['strategy']} {t['method']} (candle {t['signal_candle_start']}) as the first valid signal"
            elif not md:
                c1, c2, evid = "UNRESOLVED_DISCRETIONARY_SELECTION", "", f"the journal records no trade this day; the automated system took {t['strategy']} {t['method']} {t['direction']} (candle {t['signal_candle_start']}) mechanically"
            else:
                c1, c2, evid = "UNRESOLVED_DISCRETIONARY_SELECTION", "", "every journal row of the day is already matched to another automated trade; this trade has no manual counterpart"
            stage = "DATE_STRATEGY_ONLY" if any(p.trade is t for p in m_["date_strategy_only"]) else "UNMATCHED_AUTOMATED"
            row = {"config": k, "trade_id": t["trade_id"], "date": t["date"], "strategy": t["strategy"], "method": t["method"], "direction": t["direction"], "signal_candle_start": t["signal_candle_start"], "fill_time": t["fill_timestamp"][-5:], "entry_price": t["entry_price"],
                   "outcome": t["outcome"], "gross_pnl_rs": t["gross_pnl_rs"], "match_stage": stage, "manual_rows_that_day": " | ".join(f"{r.strategy} {r.time_label} {r.outcome}" for r in md) or "none", "root_cause_primary": c1, "root_cause_secondary": c2, "evidence": evid}
            auto_only.append(row)
            if stage == "UNMATCHED_AUTOMATED":
                match_rows.append({"config": k, "journal_row": "", "date": t["date"], "match_stage": "AUTOMATED_ONLY", "trade_id": t["trade_id"], "auto_strategy": t["strategy"], "auto_method": t["method"], "auto_signal_candle_start": t["signal_candle_start"], "auto_outcome": t["outcome"]})
            causes.append({"config": k, "journal_row": "", "date": t["date"], "manual_strategy": "", "manual_time_label": "", "manual_outcome": "", "match_stage": stage, "trade_id": t["trade_id"], "side": "AUTOMATED_ONLY", "root_cause_primary": c1, "root_cause_secondary": c2, "evidence": evid})
    write_csv(OUT / "manual_vs_automated_matching.csv", match_rows)
    write_csv(OUT / "strict_matches.csv", strict_rows)
    write_csv(OUT / "time_tolerant_matches.csv", tol_rows)
    write_csv(OUT / "manual_only_trades.csv", manual_only)
    write_csv(OUT / "automated_only_trades.csv", auto_only)
    write_csv(OUT / "mismatch_root_causes.csv", causes)
    # ------------------------------------------------------------------ wrong-strategy dates and per-strategy unmatched views
    wrong = []
    for k in K:
        for d in sorted({r.date for r in jrows} | set(cx.tby[k])):
            ms = [r for r in jrows if r.date == d and not r.weekend]
            ats = cx.tby[k].get(d, [])
            if ms and ats and not ({r.strategy for r in ms} & {t["strategy"] for t in ats}):
                wrong.append({"config": k, "date": d, "manual": " | ".join(f"{r.strategy} {r.time_label} {r.outcome}" for r in ms), "automated": " | ".join(f"{t['strategy']}/{t['method']} {t['signal_candle_start']} {t['outcome']}" for t in ats),
                              "first_automated_signal_chronologically": min((s for s in cx.sigs[k][d]), key=lambda s: s["time"])["time"] + " " + min((s for s in cx.sigs[k][d]), key=lambda s: s["time"])["strategy"] if cx.sigs[k][d] else ""})
    write_csv(OUT / "wrong_strategy_dates.csv", wrong)
    for name, strategies in (("orb_unmatched_dates.csv", ("ORB",)), ("irf_unmatched_dates.csv", ("IRF",)), ("pdr_pds_unmatched_dates.csv", ("PDR", "PDS"))):
        rows = [{"side": "MANUAL_ONLY", "config": r["config"], "date": r["date"], "strategy": r["manual_strategy"], "time_label_or_signal_candle": r["manual_time_label"], "match_stage": r["match_stage"], "root_cause_primary": r["root_cause_primary"],
                 "root_cause_secondary": r["root_cause_secondary"], "evidence": r["evidence"]} for r in manual_only if r["manual_strategy"] in strategies] + [
            {"side": "AUTOMATED_ONLY", "config": r["config"], "date": r["date"], "strategy": r["strategy"], "time_label_or_signal_candle": r["signal_candle_start"], "match_stage": r["match_stage"], "root_cause_primary": r["root_cause_primary"],
             "root_cause_secondary": r["root_cause_secondary"], "evidence": r["evidence"]} for r in auto_only if r["strategy"] in strategies]
        write_csv(OUT / name, rows)
    # ------------------------------------------------------------------ state
    st = {}
    for k in K:
        m_ = matches[k]
        by = lambda lst, key: dict(Counter(key(x) for x in lst))  # noqa: E731
        st[k] = {"automated_trades": len(cx.trades[k]), "strict": len(m_["strict"]), "time_tolerant": len(m_["tolerant"]), "date_strategy_only": len(m_["date_strategy_only"]),
                 "manual_rows_unmatched_total": len(m_["manual_unmatched"]) + len(m_["date_strategy_only"]), "manual_rows_no_trade_same_date_strategy": len(m_["manual_unmatched"]), "automated_unmatched_total": len(m_["trades_unmatched"]) + len(m_["date_strategy_only"]),
                 "automated_no_manual_counterpart": len(m_["trades_unmatched"]), "strict_by_strategy": by(m_["strict"], lambda p: p.manual.strategy), "tolerant_by_strategy": by(m_["tolerant"], lambda p: p.manual.strategy),
                 "manual_only_by_strategy": by([r for r in manual_only if r["config"] == k], lambda r: r["manual_strategy"]), "automated_only_by_strategy": by([r for r in auto_only if r["config"] == k], lambda r: r["strategy"]),
                 "manual_only_causes": by([r for r in manual_only if r["config"] == k], lambda r: r["root_cause_primary"]), "automated_only_causes": by([r for r in auto_only if r["config"] == k], lambda r: r["root_cause_primary"]),
                 "outcome_agreement_matched": {"agree": sum(1 for p in m_["strict"] + m_["tolerant"] if J.outcome_agrees(p.manual.outcome, p.trade["outcome"])), "total": len(m_["strict"]) + len(m_["tolerant"])},
                 "wrong_strategy_dates": sum(1 for w in wrong if w["config"] == k), "manual_rows_on_dates_with_no_automated_trade": sum(1 for r in jrows if not r.weekend and r.date not in cx.tby[k])}
    state["matching"] = st
    state["delta_distribution"] = {f"{k}|{s}|{d}": n for (k, s, d), n in sorted(delta_dist.items())}
    state["cause_counts"] = {k: dict(Counter(c["root_cause_primary"] for c in causes if c["config"] == k)) for k in K}
    (OUT / "phase56_state.json").write_text(json.dumps(state, indent=1, default=str))
    # ------------------------------------------------------------------ handwritten corrections
    corr = rd(P53 / "dated_author_corrections.csv")
    hw = []
    for r in corr:
        d = r["trading_date"]
        row = {"correction_id": r["correction_id"], "date": d, "pdf_page": r["handwritten_pdf_page"], "author_comment": r["original_author_comment"], "topic": r["topic"], "author_expected": r["expected_strategy_or_candle"], "phase53_reconciliation_status": r["reconciliation_status"],
               "manual_journal_rows": " | ".join(f"{j.strategy} {j.time_label} {j.outcome}" for j in jrows if j.date == d) or ("general remark (no date)" if not d else "none")}
        for k in K:
            ts = cx.tby[k].get(d, []) if d else []
            row[f"automated_{k}"] = " | ".join(f"{t['strategy']}/{t['method']} {t['signal_candle_start']} {t['outcome']}" for t in ts) or ("n/a" if not d else "no trade")
            topic = r["topic"]
            if not d:
                stt = "GENERAL_REMARK"
            elif topic == "ORB_MISSING":
                stt = "ORB_NOW_TRADED" if any(t["strategy"] == "ORB" for t in ts) else "ORB_STILL_NOT_TRADED"
            elif topic == "ORB_COLOUR":
                stt = "STILL_TRADED_RED_CANDLE_LONG" if any(t["strategy"] == "ORB" for t in ts) else "NOT_TRADED"
            elif topic == "IRF_EMA_28":
                a_irf = [t for t in cx.tby["A"].get(d, []) if t["strategy"] == "IRF"]
                stt = "IRF_SIGNAL_REJECTED_OR_CHANGED" if a_irf and not any(t["strategy"] == "IRF" and t["signal_candle_start"] == a_irf[0]["signal_candle_start"] for t in ts) else ("IRF_UNCHANGED" if a_irf else "n/a")
            elif topic in ("IRF_FIRST_RED_CANDLE", "IRF_ENTRY_BODY (not in the call)", "IRF_DAY_LOW"):
                a_irf = [t for t in cx.tby["A"].get(d, []) if t["strategy"] == "IRF"]
                stt = ("PENDING_OWNER_DEFINITION" if topic == "IRF_DAY_LOW" else ("IRF_TRADE_UNCHANGED" if [(x["signal_candle_start"], x["outcome"]) for x in a_irf] == [(x["signal_candle_start"], x["outcome"]) for x in ts if x["strategy"] == "IRF"] else "IRF_TRADE_CHANGED"))
            elif topic in ("PDR_FIRST_ELIGIBLE", "PDS_FIRST_ELIGIBLE"):
                s = topic[:3]
                a_t = [x for x in cx.tby["A"].get(d, []) if x["strategy"] == s]
                c_t = [x for x in ts if x["strategy"] == s]
                stt = "ENTRY_EARLIER_THAN_A" if c_t and a_t and c_t[0]["signal_candle_start"] < a_t[0]["signal_candle_start"] else ("ENTRY_UNCHANGED" if [x["signal_candle_start"] for x in c_t] == [x["signal_candle_start"] for x in a_t] else "ENTRY_CHANGED")
            else:
                stt = "NOT_ADDRESSED_BY_THE_CONFIGURATIONS"
            row[f"status_{k}"] = stt
        hw.append(row)
    write_csv(OUT / "handwritten_author_corrections_comparison.csv", hw)
    # ------------------------------------------------------------------ daily explanations and charts for material mismatches
    mism_dates = {r["date"] for r in manual_only} | {r["date"] for r in auto_only} | {c["date"] for c in causes if c["side"] == "MATCHED_DIFFERENT_OUTCOME"}
    n_ch = 0
    by_k_manual = {k: {r["journal_row"]: r for r in match_rows if r["config"] == k and r["journal_row"] != ""} for k in K}
    cause_by = {(c["config"], str(c["journal_row"]), c["side"]): c for c in causes if c["side"] != "AUTOMATED_ONLY"}
    cause_auto = {(c["config"], c["trade_id"]): c for c in causes if c["side"] == "AUTOMATED_ONLY"}
    for dd in cx.days:
        d = str(dd)
        c = cx.ctx[dd]
        fc = cx.first_candle(d)
        pv = c.previous
        ema0 = float(c.candles["ema200_5m"].iloc[0])
        md = [f"# {d} ({dd:%A}) - manual journal versus the automated configurations", "", "> SYNTHETIC index-point P&L; no real option P&L; costs illustrative (Rs 70 per trade + slippage scenarios). Configurations A / B / C are never combined.", "",
              "## Session", "", f"* Open {c.open_price}; previous official close {pv.close_official}; gap {c.open_price - pv.close_official:+.2f}; previous-day high / low {pv.high} / {pv.low}",
              f"* First 5-minute candle (09:15-09:20): O{fc['open']} H{fc['high']} L{fc['low']} C{fc['close']}, {fc['colour']}, body {fc['body_pct']}%; EMA(200) at the first candle {ema0:.2f}; previous session's last close {pv.candles.iloc[-1].close} vs its EMA {pv.ema_at_last_candle:.2f}", ""]
        mrows = [j for j in jrows if j.date == d]
        md += ["## Manual journal", "", ("; ".join(f"row {j.row_id}: {j.strategy} labelled {j.time_label}, outcome {j.outcome}" for j in mrows) or "no manual trade recorded"), ""]
        for k in K:
            tl = cx.bs[k].timelines[dd]
            md += [f"## Configuration {k}", ""]
            sgs = cx.sigs[k][d]
            md += ["Candidate signals (confirmed): " + ("; ".join(f"{s['time']} {s['strategy']}/{s['method']} {s['direction']} [{s['controller_event'] or 'n/a'}: {s['controller_reason'] or ''}]" for s in sorted(sgs, key=lambda s: s["time"])) or "none"), ""]
            none = [s for s in ("IRF", "ORB", "PDR", "PDS", "RF") if not any(x["strategy"] == s for x in sgs)]
            if none:
                reasons = []
                for s in none:
                    recs = [r for r in tl.records if r.strategy == s and r.signal_status != "CONFIRMED"]
                    reasons.append(f"{s}: " + ("; ".join(sorted({f"{r.method} {r.signal_status} {r.invalidation_reason or ''}".strip() for r in recs}))[:160] or "no setup record (the strategy's trigger event never occurred)"))
                md += ["Strategies with no confirmed signal: " + " | ".join(reasons), ""]
            ts = cx.tby[k].get(d, [])
            if ts:
                md += ["| trade | strategy / method | dir | signal -> fill | entry | stop / T1 / T2 | leg 1 | leg 2 | outcome | gross Rs | net Rs (70, 0) | net Rs (70, 1.0) |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
                for t in ts:
                    md.append(f"| {t['trade_no_of_day']} | {t['strategy']}/{t['method']} | {t['direction']} | {t['signal_candle_end'] if 'signal_candle_end' in t else ''} -> {t['fill_timestamp'][-5:]} | {t['entry_price']} | {t['initial_stop']} / {t['target_1']} / {t['target_2']} | {t['leg1_exit_time']} @ {t['leg1_exit_price']} | "
                              f"{t['leg2_exit_time']} @ {t['leg2_exit_price']} | {t['outcome']} | {fnum(t['gross_pnl_rs']):,.0f} | {fnum(t['net_pnl_rs_scenario_B']):,.0f} | {fnum(t['net_pnl_rs_scenario_E']):,.0f} |")
                md += ["", f"Selection: {ts[0]['selection_explanation']}", ""]
            else:
                md += [f"No trade: final day state {tl.result.final_state.value}." + (" Signals existed but none became a trade (see the dispositions above)." if sgs else " No strategy qualified."), ""]
            for j in mrows:
                mr = by_k_manual[k].get(j.row_id)
                if mr is None:
                    continue
                if mr["match_stage"] in ("STRICT", "TIME_TOLERANT"):
                    agree = mr["outcome_class_agrees_descriptive"]
                    md.append(f"* Journal row {j.row_id} ({j.strategy} {j.time_label}): **{mr['match_stage']}** match with {mr['trade_id']} (delta {mr['delta_minutes_vs_signal_candle_start']:+d} min); outcome {j.outcome} vs automated {mr['auto_outcome']} ({'same class' if agree else 'different class: EXIT_MANAGEMENT_MISMATCH; the journal has no exit price / time'})")
                else:
                    cz = cause_by.get((k, str(j.row_id), "MANUAL_ONLY"))
                    md.append(f"* Journal row {j.row_id} ({j.strategy} {j.time_label}): **{mr['match_stage']}**; earliest cause {cz['root_cause_primary'] if cz else ''}" + (f" (+ {cz['root_cause_secondary']})" if cz and cz['root_cause_secondary'] else "") + f": {cz['evidence'] if cz else ''}")
            for t in ts:
                cz = cause_auto.get((k, t["trade_id"]))
                if cz:
                    md.append(f"* Automated {t['strategy']} {t['signal_candle_start']} has no strict / time-tolerant journal counterpart: {cz['root_cause_primary']} - {cz['evidence']}")
            md.append("")
        ex = [h for h in hw if h["date"] == d]
        if ex:
            md += ["## Handwritten author corrections for this date", ""] + [f"* {h['correction_id']} (page {h['pdf_page']}): \"{h['author_comment']}\" - status A / B / C: {h['status_A']} / {h['status_B']} / {h['status_C']}" for h in ex] + [""]
        if d in mism_dates:
            ncand = min(len(c.candles), 54)
            today = [{"start": r.bar_start, "open": r.open, "high": r.high, "low": r.low, "close": r.close, "ema": r.ema200_5m} for r in c.candles.iloc[:ncand].itertuples()]
            pc = pv.candles
            prev = [{"start": r.bar_start, "open": r.open, "high": r.high, "low": r.low, "close": r.close, "ema": r.ema200_5m} for r in pc.iloc[-12:].itertuples()]
            marks = []
            for j in mrows:
                idx = next((i for i, r in enumerate(today) if hm(r["start"]) == j.time_label), None)
                if idx is not None:
                    marks.append({"idx": len(prev) + idx, "price": today[idx]["open"], "label": f"manual {j.strategy} {j.time_label} {j.outcome}", "kind": "MANUAL"})
            for k in K:
                for t in cx.tby[k].get(d, []):
                    idx = next((i for i, r in enumerate(today) if hm(r["start"]) == t["signal_candle_start"]), None)
                    if idx is not None:
                        marks.append({"idx": len(prev) + idx, "price": fnum(t["entry_price"]), "label": f"{k}: {t['strategy']} {t['signal_candle_start']}", "kind": k})
            (OUT / "charts" / f"{d}.svg").write_text(CH.render(f"{d} - manual journal versus automated entries (A / B / C)", prev, today, [("prev-day high", pv.high), ("prev-day low", pv.low)], marks, "manual entries are drawn at the candle OPEN of the journal's label (the journal records no price)"))
            md += ["## Chart", "", f"![{d}](../charts/{d}.svg)", ""]
            n_ch += 1
        (OUT / "daily" / f"{d}.md").write_text("\n".join(md) + "\n")
    state["daily_reports"] = len(cx.days)
    state["charts"] = n_ch
    state["material_mismatch_dates"] = len(mism_dates)
    (OUT / "phase56_state.json").write_text(json.dumps(state, indent=1, default=str))
    write_workbook(jrows, match_rows, manual_only, auto_only, causes, hw, wrong, state)
    print(json.dumps({k: {x: v for x, v in st[k].items() if not isinstance(v, dict)} for k in K}, indent=1))
    print("manual-only causes", {k: state["cause_counts"][k] for k in K})
    return 0


def write_workbook(jrows, match_rows, manual_only, auto_only, causes, hw, wrong, state) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    wb = Workbook()
    ws = wb.active
    ws.title = "README"
    for n, line in enumerate(["Phase 5.6 - manual journal versus automated trades (A frozen Phase 3.6, B Phase 5.3 author-corrected, C B + ORB gap crossing)",
                              "The journal has five original columns (no direction / price / exit); nothing was relabelled; weekend rows are flagged. Matching is one-to-one: STRICT (same candle label), TIME_TOLERANT (<= 15 minutes), DATE_STRATEGY_ONLY (not counted as a match).",
                              "Sheets: Journal, Matching, Manual Only, Automated Only, Root Causes, Wrong Strategy Dates, Handwritten Corrections."], 1):
        ws.cell(row=n, column=1, value=line)
    ws["A1"].font = Font(bold=True, size=13)
    ws.column_dimensions["A"].width = 170

    def add(name, rows_):
        w = wb.create_sheet(name[:31])
        if not rows_:
            w["A1"] = "(no rows)"
            return
        cols = []
        for r in rows_:
            for k in r:
                if k not in cols:
                    cols.append(k)
        w.append(cols)
        for r in rows_:
            w.append([("" if r.get(c) is None else (str(r[c]) if isinstance(r[c], (dict, list)) else r[c])) for c in cols])
        for cell in w[1]:
            cell.fill, cell.font = PatternFill("solid", fgColor="1F3864"), Font(bold=True, color="FFFFFF")
        w.freeze_panes = "B2"
    add("Journal", [asdict(j) for j in jrows])
    add("Matching", match_rows)
    add("Manual Only", manual_only)
    add("Automated Only", auto_only)
    add("Root Causes", causes)
    add("Wrong Strategy Dates", wrong)
    add("Handwritten Corrections", hw)
    wb.save(OUT / "Manual_vs_Automated_Trading_Audit.xlsx")


if __name__ == "__main__":
    raise SystemExit(main())
