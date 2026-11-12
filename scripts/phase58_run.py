"""Reconstruct signals and inspect EXISTING ledgers. No controller or P&L backtest.

Run: .venv/bin/python scripts/phase58_run.py
Only writes Phase 5.8. Original workbook is read-only; journal labels stay literal.
"""

from __future__ import annotations

import csv
import hashlib
import inspect
import json
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import phase58_charts as CH  # noqa: E402

from nifty_trading.core.execution_eligibility import entry_executable  # noqa: E402
from nifty_trading.data.sessions import (  # noqa: E402
    build_session_contexts,
    load_daily_official,
    load_one_minute,
    load_warmup_one_minute,
)
from nifty_trading.research import phase3 as P  # noqa: E402
from nifty_trading.research import phase58 as F  # noqa: E402
from nifty_trading.research.phase55 import engines_for  # noqa: E402
from nifty_trading.strategies.base import SignalEngine  # noqa: E402
from nifty_trading.strategies.orb import ORBStrategy  # noqa: E402
from nifty_trading.strategies.orb_candidates import ORBCandidateStrategy  # noqa: E402
from nifty_trading.strategies.orb_colour import ORBColourStrategy  # noqa: E402

OUT = ROOT / "reports/phase5/phase58_codex_orb_forensic_audit"
P55 = ROOT / "reports/phase5/phase55_combined_backtest"
JOURNAL = ROOT / "docs/trading journal/Trading_Journal_Sep2025_Aug2026 REPORT.xlsx"


def read(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def write(name, rows, fields=None):
    rows = list(rows)
    if fields is None:
        fields = list(dict.fromkeys(k for r in rows for k in r))
    with open(OUT / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: json.dumps(v, ensure_ascii=False, default=str) if isinstance(v, (list, dict)) else v for k, v in r.items()})


def mdtable(rows, fields):
    def clean(v):
        return str(v).replace("|", ";").replace("\n", " ")
    return "\n".join(["| " + " | ".join(fields) + " |", "|" + "---|" * len(fields)] + ["| " + " | ".join(clean(r.get(k, "")) for k in fields) + " |" for r in rows])


def signature(records):
    return {(r.method, r.direction) for r in records if r.signal_status == "CONFIRMED"}


def transcribe_journal():
    wb = openpyxl.load_workbook(JOURNAL, read_only=True, data_only=True)
    rows = []
    for i, values in enumerate(wb["Trading Journal"].iter_rows(values_only=True), 1):
        if len(values) < 5 or not isinstance(values[0], (int, float)) or not isinstance(values[1], datetime):
            continue
        serial, day, tm, strategy, outcome = values[:5]
        rows.append({"sheet_row": i, "serial": int(serial), "date": day.date().isoformat(),
                     "weekday": day.strftime("%A"), "manual_time_raw": str(tm),
                     "manual_strategy": strategy, "manual_outcome": outcome})
    wb.close()
    return rows


def verify_candles(ctxs, minute, warmup, daily):
    failures = []
    max_error = 0.0
    # Independent group-by clock-floor aggregation. Missing buckets stay missing.
    full = pd.concat([warmup, minute], ignore_index=True).sort_values("timestamp") if warmup is not None else minute
    clocks = full.timestamp.dt.hour * 60 + full.timestamp.dt.minute
    selected = full[(clocks >= 555) & (clocks < 930)].copy()
    selected["bucket"] = selected.timestamp.dt.floor("5min")
    grouped = selected.groupby("bucket").agg(open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"), count=("timestamp", "nunique"))
    independent = grouped[grouped["count"] == 5]
    verified = 0
    for d, ctx in ctxs.items():
        for r in ctx.candles.itertuples(index=False):
            x = independent.loc[r.bar_start]
            error = max(abs(float(getattr(r, k)) - float(x[k])) for k in ("open", "high", "low", "close"))
            max_error = max(max_error, error)
            if error > 1e-8:
                failures.append(f"OHLC {r.bar_start}: {error}")
            verified += 1
        if f'{ctx.candles.bar_start.iloc[0]:%H:%M}' != "09:15" or f'{ctx.candles.bar_end.iloc[0]:%H:%M}' != "09:20":
            failures.append(f"Opening timestamp {d}")
    # Independent EMA recurrence over exactly the accepted warm-up and analysis
    # sessions. Classifier is separately inspected; do not include corrupt sessions.
    analysis_min = minute.timestamp.dt.date.min()
    if warmup is not None:
        pre_ctx, _ = build_session_contexts(warmup, daily_df=daily)
    else:
        pre_ctx = {}
    sequence = [pre_ctx[d].candles for d in sorted(pre_ctx) if d < analysis_min] + [ctxs[d].candles for d in sorted(ctxs)]
    frame = pd.concat(sequence, ignore_index=True)
    vals = frame.close.to_numpy(dtype=float)
    e = np.full(len(vals), np.nan)
    if len(vals) >= 200:
        e[199] = sum(vals[:200]) / 200
        for i in range(200, len(vals)):
            e[i] = e[i-1] + 2 / 201 * (vals[i] - e[i-1])
    actual = frame.ema200_5m.to_numpy(dtype=float)
    ema_error = float(np.nanmax(np.abs(e - actual)))
    if not np.allclose(e, actual, equal_nan=True, atol=1e-8, rtol=0):
        failures.append(f"EMA mismatch {ema_error}")
    return {"ohlc_candles_checked": verified, "ohlc_max_error": max_error,
            "ema_max_error": ema_error, "failures": failures}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "daily").mkdir(exist_ok=True)
    (OUT / "charts").mkdir(exist_ok=True)
    sc = P.combined_scenario("BODY_BASED_PHASE36")
    p = sc.proposals
    minute, warmup, daily = load_one_minute(), load_warmup_one_minute(), load_daily_official()
    ctxs, infos = build_session_contexts(minute, daily_df=daily, warmup_1m=warmup)
    minute_days = {str(d): f.drop(columns="_date") for d, f in minute.assign(_date=minute.timestamp.dt.date).groupby("_date")}
    journal = transcribe_journal()
    manual = [r for r in journal if str(r["manual_strategy"]).strip().upper() == "ORB"]
    jdates = {r["date"] for r in manual}
    hand = read(OUT / "handwritten_source_transcription.csv")
    for h in hand:
        h["date"] = datetime.strptime(h["trade_id_as_written"][:8], "%Y%m%d").date().isoformat()
    hby = {h["date"]: h for h in hand}
    focus = sorted(jdates | set(hby))
    # Re-evaluate signals only. Explicitly do not call B.build, run_timelines,
    # run_trading_day, simulate_exit, evaluate_exit, or any P&L metric.
    records = {k: {} for k in ("A", "B", "C")}
    for k in records:
        engines = engines_for(k, p, sc.trade, sc.pdr_engine, sc.pdr_revision)
        for d, ctx in sorted(ctxs.items()):
            records[k][str(d)] = [r for engine in engines for r in engine.evaluate_session(ctx)]
            for engine in engines:
                if hasattr(engine, "rejections"):
                    engine.rejections.clear()
    reconstruction = {str(d): F.reconstruct(ctx, p) for d, ctx in ctxs.items()}
    parity = []
    prefix_failures = []
    frozen = ORBStrategy(proposals=p, trade=sc.trade)
    gap_engine = ORBCandidateStrategy(proposals=p, trade=sc.trade, gap_crossing_def="CANDLE_CROSSES_AVERAGE")
    colour_engine = ORBColourStrategy(proposals=p, trade=sc.trade)
    nearest_engine = ORBCandidateStrategy(proposals=p, trade=sc.trade, inner_level_def="NEAREST_FRACTAL_FROM_OPEN_K2")
    for d, ctx in ctxs.items():
        predicted = {(r["method"], r["direction"]) for r in reconstruction[str(d)] if r["eligible"]}
        observed = signature(r for r in records["A"][str(d)] if r.strategy == "ORB")
        if predicted != observed:
            parity.append({"date": str(d), "independent": sorted(predicted), "engine": sorted(observed)})
        if frozen.evaluate_session(ctx) != frozen.evaluate_session(ctx.prefix(1)):
            prefix_failures.append(str(d))
    if parity or prefix_failures:
        raise AssertionError({"signal_parity": parity, "prefix": prefix_failures})
    alternatives = {}
    diffs, impact = [], []
    for variant, (rationale, authority) in F.VARIANTS.items():
        changed_dates, adds, removes = set(), 0, 0
        alternatives[variant] = {}
        for d, ctx in ctxs.items():
            old = {(r["method"], r["direction"]) for r in reconstruction[str(d)] if r["eligible"]}
            new_rows = F.reconstruct(ctx, p, variant)
            new = {(r["method"], r["direction"]) for r in new_rows if r["eligible"]}
            alternatives[variant][str(d)] = new
            if variant in ("gap_candle", "colour", "inner_nearest"):
                check = {"gap_candle": gap_engine, "colour": colour_engine, "inner_nearest": nearest_engine}[variant]
                if new != signature(check.evaluate_session(ctx)):
                    raise AssertionError((variant, d, new))
            for action, signals in (("ADDED", new - old), ("REMOVED", old - new)):
                for method, direction in sorted(signals):
                    changed_dates.add(str(d))
                    adds += action == "ADDED"
                    removes += action == "REMOVED"
                    source_issue = "Not established: exact author level/shape unavailable; candidate is not a validated author trade"
                    if variant == "colour" and action == "REMOVED":
                        source_issue = "Author rejects wrong-colour long; short mirror source p.1"
                    diffs.append({"variant": variant, "date": str(d), "action": action, "method": method, "direction": direction,
                                  "time": "09:20", "manual_orb_date": str(d) in jdates, "handwritten_dispute": str(d) in hby,
                                  "rationale": rationale, "authority": authority, "future_information": False,
                                  "false_positive_assessment": source_issue})
        impact.append({"variant": variant, "added_method_direction_signals": adds, "removed_method_direction_signals": removes,
                       "changed_unique_dates": len(changed_dates), "changed_handwritten_dates": sorted(changed_dates & set(hby)),
                       "changed_manual_orb_dates": sorted(changed_dates & jdates), "authority": authority, "rationale": rationale})
    ledger = read(P55 / "all_executed_trades.csv")
    tby = {k: defaultdict(list) for k in records}
    for t in ledger:
        tby[t["config"]][t["date"]].append(t)
    ledger_checks, chronology_checks, signal_file_checks = [], [], []
    prior_signals = read(P55 / "all_confirmed_signals.csv")
    for k in records:
        for d, recs in records[k].items():
            fresh = {(r.strategy, r.method, r.direction, f'{r.signal_timestamp:%H:%M}') for r in recs if r.signal_status == "CONFIRMED"}
            stored = {(r["strategy"], r["method"], r["direction"], r["time"]) for r in prior_signals if r["config"] == k and r["date"] == d}
            if fresh != stored:
                signal_file_checks.append({"config": k, "date": d, "fresh_only": sorted(fresh-stored), "stored_only": sorted(stored-fresh)})
            # First-entry chronological verification does not require an exit walk.
            fillable = [r for r in recs if r.signal_status == "CONFIRMED" and r.signal_timestamp.strftime("%H:%M") <= "13:00"
                        and entry_executable(r.signal_timestamp)
                        and any(minute_days[d].timestamp == r.signal_timestamp)]
            earliest = min((r.signal_timestamp for r in fillable), default=None)
            firsts = [r for r in fillable if r.signal_timestamp == earliest]
            first_trades = [t for t in tby[k][d] if t["trade_no_of_day"] == "1"]
            conflict = len({(r.strategy, r.direction) for r in firsts}) > 1
            if first_trades:
                t = first_trades[0]
                ok = not conflict and earliest is not None and t["fill_timestamp"][-5:] == earliest.strftime("%H:%M") and any(r.strategy == t["strategy"] and r.direction == t["direction"] for r in firsts)
            else:
                ok = earliest is None or conflict
            chronology_checks.append({"config": k, "date": d, "first_signal": earliest.strftime("%H:%M") if earliest else "",
                                      "first_strategies": sorted({r.strategy for r in firsts}), "conflict": conflict,
                                      "ledger_first": first_trades[0]["strategy"] if first_trades else "", "passed": ok})
        for t in [t for t in ledger if t["config"] == k]:
            matches = [r for r in records[k].get(t["date"], []) if r.signal_status == "CONFIRMED" and r.strategy == t["strategy"]
                       and r.method == t["method"] and r.direction == t["direction"] and r.signal_timestamp.strftime("%H:%M") == t["fill_timestamp"][-5:]]
            raw = minute_days[t["date"]]
            fillrow = raw[raw.timestamp.dt.strftime("%H:%M") == t["fill_timestamp"][-5:]]
            price_ok = len(fillrow) == 1 and abs(float(fillrow.open.iloc[0]) - float(t["entry_price"])) < 1e-7
            ledger_checks.append({"config": k, "trade_id": t["trade_id"], "date": t["date"], "signal_found": bool(matches), "fill_raw_open_matches": price_ok})
    if signal_file_checks:
        raise AssertionError({"stored_signal_disagreement": signal_file_checks[:5]})
    flat, pathrows = [], []
    for d in focus:
        for r in reconstruction.get(d, []):
            pathrows.append({k: v for k, v in r.items() if k not in ("gates", "geometry")})
            for i, gate in enumerate(r["gates"]):
                remaining = [g["predicate"] for j, g in enumerate(r["gates"]) if j != i and g["passed"] is not True]
                flat.append({"date": d, "method": r["method"], "direction": r["direction"], "order": i + 1, **gate,
                             "single_gate_removal_qualifies": r["precheck"] and not remaining,
                             "other_failures_if_removed": remaining,
                             "manual_direction": "UNKNOWN", "manual_orb_date": d in jdates, "handwritten_dispute": d in hby})
    all_dates, timeline, roots, disputes = [], [], [], []
    for d in focus:
        ctx = ctxs.get(date.fromisoformat(d))
        paths = reconstruction.get(d, [])
        opening = paths[0]["geometry"] if paths else {}
        source_rows = [r for r in manual if r["date"] == d]
        path_desc = " | ".join(f'{r["direction"]} {r["method"]}: {", ".join(r["failed"]) or "PASS"}' for r in paths)
        for k in records:
            recs = records[k].get(d, [])
            orb = [r for r in recs if r.strategy == "ORB" and r.signal_status == "CONFIRMED"]
            irf = [r for r in recs if r.strategy == "IRF" and r.signal_status == "CONFIRMED"]
            first_irf = min(irf, key=lambda r: r.signal_timestamp, default=None)
            trades = sorted(tby[k][d], key=lambda t: int(t["trade_no_of_day"]))
            orb_executed = any(t["strategy"] == "ORB" for t in trades)
            irf_executed = any(t["strategy"] == "IRF" for t in trades)
            others = sorted({t["strategy"] for t in trades if t["strategy"] not in ("ORB", "IRF")})
            row = {"config": k, "date": d, "manual_orb_date": d in jdates,
                   "manual_rows_on_date": len(source_rows), "manual_sheet_rows": [r["sheet_row"] for r in source_rows],
                   "manual_time_labels": [r["manual_time_raw"] for r in source_rows],
                   "manual_direction": "UNKNOWN", "manual_level": "UNKNOWN",
                   "session_status": ctx.info.status.value if ctx else (infos[date.fromisoformat(d)].status.value if date.fromisoformat(d) in infos else "NO_SESSION_IN_DATA"),
                   "weekday": date.fromisoformat(d).strftime("%A"),
                   "method1_signal": any(r.method == "Method 1" for r in orb),
                   "method2_signal": any(r.method == "Method 2" for r in orb),
                   "gap_signal": any(r.method == "Gap/200DMA" for r in orb),
                   "orb_signal": bool(orb), "orb_signal_details": [f'{r.method} {r.direction} {r.signal_timestamp:%H:%M}' for r in orb],
                   "orb_executed": orb_executed, "irf_executed": irf_executed, "other_executed": others,
                   "no_automated_trade": not trades,
                   "first_executed_strategy": trades[0]["strategy"] if trades else "",
                   "first_executed_time": trades[0]["fill_timestamp"][-5:] if trades else "",
                   "entry_absence": "DATA_OR_JOURNAL_INCONSISTENCY" if not ctx else ("ENTRY_QUALIFICATION" if not orb else ("NONE" if orb_executed else "PORTFOLIO_CONSTRAINT")),
                   "source_definition_insufficient": True,
                   "all_paths": path_desc, **opening}
            if d in jdates:
                all_dates.append(row)
            why = ("ORB has no confirmed 09:20 signal; " + path_desc) if not orb else ("ORB confirmed at 09:20; check simultaneous strategies and ledger selection")
            if not ctx:
                why = "No evaluable historical session for literal journal date; no date correction inferred"
            timeline.append({"config": k, "date": d, "manual_orb_date": d in jdates, "handwritten_dispute": d in hby,
                             "orb_first_possible_source_time": "09:20" if ctx else "UNAVAILABLE",
                             "orb_actual_signal_time": "09:20" if orb else "",
                             "orb_earliest_executable_entry": "09:20" if orb and any(minute_days[d].timestamp.dt.strftime("%H:%M") == "09:20") else "",
                             "irf_first_signal_time": first_irf.signal_timestamp.strftime("%H:%M") if first_irf else "",
                             "irf_first_signal_method": first_irf.method if first_irf else "",
                             "irf_earliest_executable_entry": first_irf.signal_timestamp.strftime("%H:%M") if first_irf and entry_executable(first_irf.signal_timestamp) and any(minute_days[d].timestamp == first_irf.signal_timestamp) and first_irf.signal_timestamp.strftime("%H:%M") <= "13:00" else "",
                             "irf_first_signal_levels": first_irf.reference_levels if first_irf else {},
                             "irf_first_signal_trace": first_irf.state_trace if first_irf else [],
                             "irf_executed": irf_executed,
                             "ledger_trades": [f'{t["strategy"]} {t["method"]} {t["fill_timestamp"][-5:]} @ {t["entry_price"]}' for t in trades],
                             "why": why,
                             "gap_candidate_signal": bool(alternatives["gap_candle"].get(d, set())),
                             "objectively_proven_missing_orb": False,
                             "author_setup_recoverability": "UNRESOLVED_NO_LEVEL_OR_DIRECTION"})
            if not orb_executed:
                categories = {c for r in paths for c in r["causes"]}
                categories.add("AUTHOR_DISCRETION_UNRESOLVED")
                if not ctx:
                    categories.add("JOURNAL_INCONSISTENCY")
                if irf_executed and not orb:
                    categories.add("IRF_SELECTED_AFTER_ORB_FAILED")
                if orb:
                    categories.add("PORTFOLIO_CONSTRAINT")
                roots.append({"config": k, "date": d, "manual_orb_date": d in jdates,
                              "categories_union_both_directions": sorted(categories),
                              "first_failure_each_path": {f'{r["direction"]} {r["method"]}': r["first_failure"] for r in paths},
                              "all_failed_predicates": path_desc,
                              "single_decisive_author_failure": "UNIDENTIFIABLE_AUTHOR_DIRECTION_AND_METHOD_NOT_RECORDED",
                              "orb_signal_present": bool(orb), "irf_executed": irf_executed,
                              "causality_note": "Union contains mutually opposite paths; frequencies by method/direction are in predicate_frequency.csv; not a count of proven invalid manual trades"})
            if d in hby:
                disputes.append({**hby[d], **row, "author_direction": "UNKNOWN", "author_method": "UNKNOWN",
                                 "exact_author_level": "UNKNOWN", "exact_author_candle": "UNKNOWN",
                                 "classification": "UNRESOLVED_SOURCE_SETUP", "earliest_rulebook_decision": "09:20",
                                 "candidate_additions": {v: sorted(alternatives[v].get(d, set())) for v in alternatives}})
        if ctx:
            combined_trades = [t for k in records for t in tby[k][d]]
            note = []
            for r in paths:
                note.append(f'{r["direction"]} {r["method"]}: {", ".join(r["failed"]) or "PASS"}; close-to-level {r["signed_breakout_distance"]:.2f}' if r["signed_breakout_distance"] is not None else f'{r["direction"]} {r["method"]}: level undefined')
            svg = CH.chart(ctx, minute_days[d], paths, records["A"][d], combined_trades, note)
            (OUT / "charts" / f"{d}.svg").write_text(svg)
            # Raw evidence: all prior-session 5m candles and current 1m / 5m.
            ctx.previous.candles.to_csv(OUT / "daily" / f"{d}_previous_5m.csv", index=False)
            ctx.candles.to_csv(OUT / "daily" / f"{d}_5m.csv", index=False)
            minute_days[d].to_csv(OUT / "daily" / f"{d}_1m.csv", index=False)
            # Preserve five earlier evaluated sessions for multi-session scrutiny.
            earlier = [x for x in sorted(ctxs) if x < ctx.date][-5:]
            pd.concat([ctxs[x].candles.assign(session_date=str(x)) for x in earlier], ignore_index=True).to_csv(OUT / "daily" / f"{d}_prior5_sessions.csv", index=False)
            events = []
            for candle in ctx.candles.itertuples(index=False):
                tm = candle.bar_end.strftime("%H:%M")
                irf_cols = {}
                for k in records:
                    ev = [r for r in records[k][d] if r.strategy == "IRF" and r.signal_timestamp == candle.bar_end]
                    irf_cols[f"irf_{k}_condition"] = [f'{r.method}: {r.signal_status}; {r.invalidation_reason or r.reference_levels}' for r in ev]
                    irf_cols[f"irf_{k}_result"] = "CONFIRMED" if any(r.signal_status == "CONFIRMED" for r in ev) else ("NO_CONFIRMED_EVENT" if not ev else "REJECTED_OR_INCOMPLETE")
                events.append({"time": tm, "candle": f'{candle.bar_start:%H:%M}-{candle.bar_end:%H:%M}',
                               "open": candle.open, "high": candle.high, "low": candle.low, "close": candle.close,
                               "orb_condition": path_desc if tm == "09:20" else "Outside source ORB decision; engine does not rescan later candles",
                               "orb_result": "; ".join(f'{r["direction"]} {r["method"]}={r["eligible"]}' for r in paths) if tm == "09:20" else "NOT_ELIGIBLE_TIME",
                               **irf_cols})
            write(f"daily/{d}_events.csv", events)
            text = [f"# {d} ORB forensic evidence", "", f"Journal ORB rows: {[r['sheet_row'] for r in source_rows]}. Direction and level UNKNOWN.",
                    f"Handwritten comment: {hby.get(d, {}).get('comment', 'None for this date')}",
                    f"[Chart](../charts/{d}.svg) | [1m candles]({d}_1m.csv) | [5m candles]({d}_5m.csv) | [prior five sessions]({d}_prior5_sessions.csv) | [all chronological events]({d}_events.csv)",
                    "", "## Opening evidence", "", mdtable([opening], list(opening)), "", "## Both directions, all method paths", ""]
            for r in paths:
                text += [f'### {r["direction"]} {r["method"]}', "", f'Level {r["level"]}; signed close distance {r["signed_breakout_distance"]}; earliest failure {r["first_failure"]}.', "",
                         mdtable(r["gates"], ["predicate", "passed", "reached_in_code", "observed", "source", "authority"]), ""]
            text += ["## Chronology", "", mdtable(events, ["time", "candle", "orb_condition", "orb_result", "irf_A_condition", "irf_A_result", "irf_B_condition", "irf_B_result"]), "", "## Existing ledger entries", "",
                     mdtable(combined_trades, ["config", "strategy", "method", "fill_timestamp", "entry_price", "initial_stop", "target_1", "target_2", "leg1_exit_time", "leg1_exit_price", "leg2_exit_time", "leg2_exit_price"]),
                     "", "## Conclusion", "", "No author-drawn level or direction survives in the journal/dated ORB comment. Engine eligibility is fully reconstructible; the author's exact trade remains unresolved. A hypothetical candidate signal is not an executed trade."]
            (OUT / "daily" / f"{d}.md").write_text("\n".join(text))
        else:
            (OUT / "daily" / f"{d}.md").write_text(f"# {d}\n\nLiteral journal date has no evaluable historical session. No chart, direction, price or corrected date is invented.\n")
    # Every original ORB row survives independently of date-level aggregation.
    manual_rows = []
    by_date_cfg = {(r["config"], r["date"]): r for r in all_dates}
    for r in manual:
        for k in records:
            manual_rows.append({**by_date_cfg[k, r["date"]], **r})
    write("orb_all_manual_journal_dates.csv", all_dates)
    write("orb_manual_journal_rows.csv", manual_rows)
    write("orb_13_handwritten_disputes.csv", disputes)
    write("orb_vs_irf_selection_timeline.csv", timeline)
    write("orb_missing_trade_root_causes.csv", roots)
    write("orb_predicate_observations.csv", flat)
    write("orb_method_paths.csv", pathrows)
    write("orb_candidate_signal_differences.csv", diffs, ["variant", "date", "action", "method", "direction", "time", "manual_orb_date", "handwritten_dispute", "rationale", "authority", "future_information", "false_positive_assessment"])
    write("orb_candidate_impact.csv", impact)
    write("ledger_fill_verification.csv", ledger_checks)
    write("first_selection_verification.csv", chronology_checks)
    frequencies = []
    for method in ORBStrategy.METHODS:
        for direction in ("LONG", "SHORT"):
            obs = [r for r in flat if r["manual_orb_date"] and r["method"] == method and r["direction"] == direction]
            for predicate in dict.fromkeys(r["predicate"] for r in obs):
                sub = [r for r in obs if r["predicate"] == predicate]
                frequencies.append({"method": method, "direction": direction, "predicate": predicate,
                                    "failed_dates": sum(r["passed"] is not True for r in sub), "evaluated_dates": len(sub),
                                    "reached_and_failed_dates": sum(r["reached_in_code"] and r["passed"] is not True for r in sub),
                                    "sole_failed_gate_dates": sum(r["passed"] is not True and r["single_gate_removal_qualifies"] for r in sub),
                                    "interpretation": "Direction is a diagnostic path; unknown author direction. Do not sum across paths."})
    write("predicate_frequency.csv", frequencies)
    summary = {"journal_total_rows": len(journal), "journal_strategy_rows": dict(Counter(r["manual_strategy"] for r in journal)),
               "journal_weekend_rows": [r for r in journal if date.fromisoformat(r["date"]).weekday() >= 5],
               "orb_journal_rows": len(manual), "orb_unique_dates": len(jdates),
               "orb_evaluable_unique_dates": sum(date.fromisoformat(d) in ctxs for d in jdates),
               "orb_unevaluable_dates": sorted(d for d in jdates if date.fromisoformat(d) not in ctxs),
               "handwritten_unique_disputes": len(hby), "focus_unique_dates": len(focus),
               "charts": len(list((OUT / "charts").glob("*.svg"))), "contexts": len(ctxs), "session_infos": len(infos),
               "independent_signal_parity_failures": parity, "orb_prefix_failures": prefix_failures,
               "nearest_inner_independent_parity_sessions": len(ctxs),
               "stored_signal_disagreements": signal_file_checks,
               "ledger_signal_or_fill_failures": [r for r in ledger_checks if not r["signal_found"] or not r["fill_raw_open_matches"]],
               "first_selection_failures": [r for r in chronology_checks if not r["passed"]],
               "data_verification": verify_candles(ctxs, minute, warmup, daily), "configurations": {}, "candidate_impact": impact}
    for k in records:
        sub = [r for r in all_dates if r["config"] == k]
        ev = [r for r in sub if r["session_status"].startswith("USABLE")]
        summary["configurations"][k] = {
            "evaluable_journal_dates": len(ev), "orb_signal_dates": sum(r["orb_signal"] for r in sub),
            "no_orb_signal_evaluable_dates": sum(not r["orb_signal"] for r in ev),
            "no_orb_signal_including_no_session": sum(not r["orb_signal"] for r in sub),
            "orb_executed_dates": sum(r["orb_executed"] for r in sub),
            "orb_signal_no_orb_execution": sum(r["orb_signal"] and not r["orb_executed"] for r in sub),
            "irf_executed_dates": sum(r["irf_executed"] for r in sub),
            "another_strategy_executed_dates": sum(bool(r["other_executed"]) for r in sub),
            "no_automated_trade_dates": sum(r["no_automated_trade"] for r in sub),
            "first_executed_strategy_counts": dict(Counter(r["first_executed_strategy"] or "NONE" for r in sub)),
            "fresh_all_orb_method_signals": sum(r.strategy == "ORB" and r.signal_status == "CONFIRMED" for recs in records[k].values() for r in recs),
            "fresh_all_orb_unique_signal_dates": sum(any(r.strategy == "ORB" and r.signal_status == "CONFIRMED" for r in recs) for recs in records[k].values()),
            "handwritten_orb_signal_dates": [d for d in hby if any(r.strategy == "ORB" and r.signal_status == "CONFIRMED" for r in records[k].get(d, []))],
        }
    (OUT / "audit_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    # Inventory source and code hashes. The metadata contains no credentials.
    inventory = []
    paths = [ROOT / "docs/strategy_docs/ORB_Strategy_Rulebook-2.pdf", ROOT / "docs/strategy_docs/corrected/Adobe Scan Nov 05, 2026.pdf", JOURNAL]
    paths += list((ROOT / "src/nifty_trading/strategies").glob("*.py"))
    paths += [ROOT / "src/nifty_trading/data/sessions.py", ROOT / "src/nifty_trading/research/phase3.py", ROOT / "src/nifty_trading/research/phase55.py"]
    paths += list((ROOT / "data/processed").rglob("*.parquet"))
    paths += [P55 / "all_executed_trades.csv", P55 / "all_confirmed_signals.csv", P55 / "configuration_manifest.json"]
    for path in paths:
        inventory.append({"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size})
    write("source_inventory.csv", inventory)
    # Indexed source appendix includes every line, not just selected conditions.
    sections = []
    for path in ["src/nifty_trading/strategies/orb.py", "src/nifty_trading/strategies/orb_candidates.py", "src/nifty_trading/strategies/orb_colour.py", "src/nifty_trading/strategies/base.py", "src/nifty_trading/strategies/definitions.py", "src/nifty_trading/strategies/params.py", "src/nifty_trading/data/sessions.py", "src/nifty_trading/strategies/trading_day.py", "src/nifty_trading/strategies/irf.py", "src/nifty_trading/strategies/irf_phase53.py"]:
        sections += [f"## {path}", "", "```python"] + [f"{i:4}: {line}" for i, line in enumerate((ROOT / path).read_text().splitlines(), 1)] + ["```", ""]
    (OUT / "source_code_numbered.md").write_text("\n".join(sections))
    functions = [ORBStrategy._scan, ORBStrategy._base_levels, ORBStrategy._quality, ORBStrategy._near_ma_value,
                 ORBStrategy._trend_gate, ORBStrategy._method1, ORBStrategy._method2, ORBStrategy._gap_setup,
                 SignalEngine.evaluate_session, SignalEngine._precheck, SignalEngine._rec, SignalEngine.on_candle]
    write("code_function_index.csv", [{"function": fn.__qualname__, "path": str(Path(inspect.getsourcefile(fn)).relative_to(ROOT)), "line": inspect.getsourcelines(fn)[1]} for fn in functions])
    print(json.dumps({"counts": summary["configurations"], "journal_rows": len(journal), "manual_orb_rows": len(manual), "data_checks": summary["data_verification"], "selection_failures": summary["first_selection_failures"]}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
