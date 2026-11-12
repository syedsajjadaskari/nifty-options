"""Phase 5.9 baseline recount and author-case data. Signal-only; no exit walk."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from nifty_trading.data.sessions import (  # noqa: E402
    build_session_contexts,
    load_daily_official,
    load_one_minute,
    load_warmup_one_minute,
)
from nifty_trading.research import phase58 as F  # noqa: E402
from nifty_trading.research.phase3 import combined_scenario  # noqa: E402
from nifty_trading.research.phase55 import engines_for  # noqa: E402
from nifty_trading.research.phase59 import (  # noqa: E402
    aggregate_five_minutes,
    blank_author_response,
    review_union,
    trade_display,
)
from nifty_trading.strategies.irf import IRFStrategy  # noqa: E402
from nifty_trading.strategies.orb import ORBStrategy  # noqa: E402
from nifty_trading.strategies.orb_colour import ORBColourStrategy  # noqa: E402
from nifty_trading.strategies.selection import is_valid  # noqa: E402

OUT = ROOT / "reports/phase5/phase59_orb_author_validation"
P58 = ROOT / "reports/phase5/phase58_codex_orb_forensic_audit"
P55 = ROOT / "reports/phase5/phase55_combined_backtest"
JOURNAL = ROOT / "docs/trading journal/Trading_Journal_Sep2025_Aug2026 REPORT.xlsx"

# Evidence selection only, kept outside trading code. No outcomes were consulted.
PRIORITY = [
    {"date": "2025-12-24", "topic": "Inner-level selection", "why": "The latest inner level is unbroken while a smaller pre-open inner level is possible. Ask the author to mark the level, not to approve the nearest-level heuristic.", "source_pages": "4-7"},
    {"date": "2025-10-08", "topic": "Multi-session support/resistance context", "why": "A 98.66% opening body does not break the current major or inner resistance. Multi-session history makes the missing level definition the useful question; no author zone is inferred.", "source_pages": "4-7,12-13"},
    {"date": "2025-11-28", "topic": "Trendline anchor selection", "why": "The inner breakout and conditional pin pass, but the last-two-pivot line fails. The author can identify relevant anchors without changing candle quality.", "source_pages": "5-7,10"},
    {"date": "2025-12-12", "topic": "Numerical candle-body threshold", "why": "The major level and trend pass; a 52.24% body fails the proposed 60% minimum. This isolates a quantitative approximation of qualitative source wording.", "source_pages": "3,9-10"},
    {"date": "2025-12-05", "topic": "EMA/gap interpretation - negative control", "why": "The green opening candle and EMA relationship do not by themselves make a gap-long setup: the gap is down. No isolated candle-crossing candidate rescues a handwritten dispute, so this honest negative control is paired with the separate 2026-07-15 missing-journal exhibit.", "source_pages": "7-9,12"},
]


def rd(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def wr(name, rows):
    rows = list(rows)
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with open(OUT / name, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, default=str) if isinstance(v, (dict, list)) else v for k, v in row.items()})


def frame_records(frame, time_col):
    result = []
    for row in frame.to_dict("records"):
        for key in list(row):
            if isinstance(row[key], (pd.Timestamp, datetime)):
                row[key] = row[key].isoformat()
        row["time"] = pd.Timestamp(row[time_col]).strftime("%H:%M")
        result.append(row)
    return result


def record_view(record):
    return {"strategy": record.strategy, "method": record.method, "direction": record.direction,
            "status": record.signal_status, "time": record.signal_timestamp.strftime("%H:%M") if record.signal_timestamp else None,
            "reason": record.invalidation_reason, "levels": record.reference_levels,
            "trace": record.state_trace}


def source_questions(paths):
    failed = {gate["predicate"] for path in paths for gate in path["gates"] if gate["passed"] is not True}
    questions = ["Q6"]  # Author method, candle convention and exact timing remain unknown.
    if {"inner_defined", "inner_close", "previous_level_close"} & failed:
        questions.append("Q1")
    if "quality" in failed:
        questions.append("Q2")
    if "trendline" in failed:
        questions.append("Q3")
    if {"gap_crossing", "gap_direction", "ma_close", "near_ma"} & failed:
        questions.append("Q4")
    if "trend" in failed:
        questions.append("Q5")
    return sorted(questions)


def main():
    for folder in ("author_review_charts", "priority_five", "remaining_eight", "all_missing_orb", "daily", "source_reference"):
        (OUT / folder).mkdir(parents=True, exist_ok=True)
    # Read every requested Phase5.8 evidence table before accepting its results.
    for name in ("orb_all_entry_predicates.csv", "orb_13_handwritten_disputes.csv", "orb_all_manual_journal_dates.csv",
                 "orb_vs_irf_selection_timeline.csv", "orb_missing_trade_root_causes.csv"):
        rd(P58 / name)
    for name in ("README.md", "orb_original_source_rules.md", "orb_required_author_clarifications.md"):
        (P58 / name).read_text()
    old_book = openpyxl.load_workbook(P58 / "ORB_Forensic_Verification.xlsx", read_only=True, data_only=True)
    workbook_baseline = [list(r) for r in old_book["Overview"].iter_rows(min_row=5, max_row=7, values_only=True)]
    old_book.close()
    original = openpyxl.load_workbook(JOURNAL, read_only=True, data_only=True)
    journal = []
    for sheet_row, values in enumerate(original["Trading Journal"].iter_rows(values_only=True), 1):
        if not isinstance(values[0], (int, float)) or not isinstance(values[1], datetime):
            continue
        journal.append({"sheet_row": sheet_row, "serial": int(values[0]), "date": values[1].date().isoformat(),
                        "time_label": str(values[2]), "strategy_as_written": values[3], "outcome_as_written": values[4]})
    original.close()
    manual = [r for r in journal if str(r["strategy_as_written"]).strip().upper() == "ORB"]
    manual_dates = {r["date"] for r in manual}
    journal_by_date = {d: [r for r in journal if r["date"] == d] for d in {r["date"] for r in journal}}
    raw, warm, daily = load_one_minute(), load_warmup_one_minute(), load_daily_official()
    ctxs, infos = build_session_contexts(raw, warmup_1m=warm, daily_df=daily)
    warm_contexts, _ = build_session_contexts(warm, daily_df=daily)
    all_contexts = {**warm_contexts, **ctxs}
    sc = combined_scenario("BODY_BASED_PHASE36")
    orb = ORBStrategy(proposals=sc.proposals, trade=sc.trade)
    current_orb = {str(d): orb.evaluate_session(ctx) for d, ctx in sorted(ctxs.items())}
    actual_signal_dates = {d for d, rows in current_orb.items() if any(r.signal_status == "CONFIRMED" for r in rows)}
    evaluable = {d for d in manual_dates if datetime.fromisoformat(d).date() in ctxs}
    missing = evaluable - actual_signal_dates
    ledger_all = rd(P55 / "all_executed_trades.csv")
    ledger = [r for r in ledger_all if r["config"] == "A"]
    orb_execution_dates = {r["date"] for r in ledger if r["strategy"] == "ORB"} & manual_dates
    irf_execution_dates = {r["date"] for r in ledger if r["strategy"] == "IRF"} & manual_dates
    hand = rd(P58 / "handwritten_source_transcription.csv")
    for row in hand:
        row["date"] = datetime.strptime(row["trade_id_as_written"][:8], "%Y%m%d").date().isoformat()
    handwritten = {r["date"]: r for r in hand}
    baseline = {"journal_rows": len(journal), "orb_journal_rows": len(manual), "orb_unique_dates": len(manual_dates),
                "evaluable_orb_dates": len(evaluable), "orb_signal_dates": len(evaluable & actual_signal_dates),
                "orb_executed_dates": len(orb_execution_dates), "missing_orb_dates": len(missing),
                "irf_executed_dates": len(irf_execution_dates), "handwritten_unique_dates": len(handwritten),
                "signal_but_no_orb_execution": sorted((evaluable & actual_signal_dates) - orb_execution_dates),
                "journal_no_session_dates": sorted(manual_dates-evaluable),
                "irf_and_orb_execution_overlap": sorted(irf_execution_dates & orb_execution_dates),
                "irf_is_subset_of_missing": irf_execution_dates <= missing,
                "phase58_workbook_summary": workbook_baseline}
    expected = {"journal_rows": 190, "orb_journal_rows": 89, "orb_unique_dates": 89, "evaluable_orb_dates": 85,
                "orb_signal_dates": 35, "orb_executed_dates": 35, "missing_orb_dates": 50, "irf_executed_dates": 34,
                "handwritten_unique_dates": 13}
    if any(baseline[k] != v for k, v in expected.items()):
        raise AssertionError({"actual": baseline, "expected": expected})
    old_dates = rd(P58 / "orb_all_manual_journal_dates.csv")
    old_missing = {r["date"] for r in old_dates if r["config"] == "A" and r["orb_signal"] == "False" and r["session_status"].startswith("USABLE")}
    if old_missing != missing:
        raise AssertionError("Phase5.8 missing-date set differs from fresh reconstruction")
    cases = review_union(missing, set(handwritten))
    priority = {r["date"]: {"order": i, **r} for i, r in enumerate(PRIORITY, 1)}
    if not set(priority) <= set(handwritten):
        raise AssertionError("Priority cases must be handwritten observations")
    old_diffs = rd(P58 / "orb_candidate_signal_differences.csv")
    raw_days = {str(d): frame.drop(columns="_date") for d, frame in raw.assign(_date=raw.timestamp.dt.date).groupby("_date")}
    all_cases, first_irf_table, gate_rows, agg_checks = [], [], [], []
    case_payload = {}
    source_files = [JOURNAL, ROOT / "docs/strategy_docs/ORB_Strategy_Rulebook-2.pdf", ROOT / "docs/strategy_docs/corrected/Adobe Scan Nov 05, 2026.pdf",
                    P55 / "all_executed_trades.csv", P55 / "all_confirmed_signals.csv"]
    source_hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
    for d in cases:
        ctx = ctxs[datetime.fromisoformat(d).date()]
        independent = aggregate_five_minutes(raw_days[d])
        max_error = max(float((independent[k].to_numpy()-ctx.candles[k].to_numpy()).max()) for k in ("open", "high", "low", "close"))
        abs_error = max(float(abs(independent[k].to_numpy()-ctx.candles[k].to_numpy()).max()) for k in ("open", "high", "low", "close"))
        if len(independent) != len(ctx.candles) or abs_error > 1e-8:
            raise AssertionError((d, len(independent), len(ctx.candles), abs_error))
        agg_checks.append({"date": d, "bars": len(independent), "max_abs_ohlc_error": abs_error, "max_signed_error": max_error,
                           "first_start": str(independent.start.iloc[0]), "first_end": str(independent.end.iloc[0])})
        paths = F.reconstruct(ctx, sc.proposals)
        predicted = {(p["method"], p["direction"]) for p in paths if p["eligible"]}
        observed = {(r.method, r.direction) for r in current_orb[d] if r.signal_status == "CONFIRMED"}
        if predicted != observed or observed:
            raise AssertionError((d, predicted, observed))
        irf_records = IRFStrategy(proposals=sc.proposals, trade=sc.trade).evaluate_session(ctx)
        irf_signals = sorted([r for r in irf_records if r.signal_status == "CONFIRMED"], key=lambda r: r.signal_timestamp)
        trades = [r for r in ledger if r["date"] == d]
        displays = [trade_display(r) for r in trades]
        for trade in trades:
            available = irf_records if trade["strategy"] == "IRF" else []
            if trade["strategy"] == "IRF" and not any(r.signal_status == "CONFIRMED" and r.method == trade["method"] and r.signal_timestamp.strftime("%H:%M") == trade["signal_confirmed_at"][-5:] for r in available):
                raise AssertionError((d, "ledger IRF signal not reproduced"))
            fill = raw_days[d][raw_days[d].timestamp.dt.strftime("%H:%M") == trade["fill_timestamp"][-5:]]
            if len(fill) != 1 or abs(float(fill.open.iloc[0])-float(trade["entry_price"])) > 1e-7:
                raise AssertionError((d, "ledger fill/raw open mismatch"))
        alternatives = []
        for change in old_diffs:
            if change["date"] == d and change["action"] == "ADDED":
                candidate = F.reconstruct(ctx, sc.proposals, change["variant"])
                path = next(p for p in candidate if p["method"] == change["method"] and p["direction"] == change["direction"])
                if not path["eligible"]:
                    raise AssertionError((d, change["variant"], "candidate not reproduced"))
                alternatives.append({"variant": change["variant"], "method": change["method"], "direction": change["direction"],
                                     "time": "09:20", "level": path["level"], "trendline": path["trendline"],
                                     "authority": change["authority"], "status": "DISABLED_DIAGNOSTIC_NOT_AUTHOR_CONFIRMED"})
        path_fails = {f'{p["direction"]} {p["method"]}': p["failed"] for p in paths}
        first_fails = {f'{p["direction"]} {p["method"]}': p["first_failure"] for p in paths}
        for path in paths:
            for gate in path["gates"]:
                gate_rows.append({"date": d, "method": path["method"], "direction": path["direction"], **gate,
                                  "sole_failed_gate": gate["passed"] is not True and len(path["failed"]) == 1})
        manual_rows = [r for r in manual if r["date"] == d]
        source_rows = journal_by_date.get(d, [])
        info = {"case_id": "ORB-"+d.replace("-", ""), "date": d, "priority": d in priority,
                "priority_order": priority.get(d, {}).get("order"), "priority_topic": priority.get(d, {}).get("topic", ""),
                "priority_reason": priority.get(d, {}).get("why", ""), "handwritten_dispute": d in handwritten,
                "missing_journal_orb": d in missing, "journal_sheet_rows": [r["sheet_row"] for r in source_rows],
                "orb_journal_sheet_rows": [r["sheet_row"] for r in manual_rows], "journal_strategy_as_written": [r["strategy_as_written"] for r in source_rows],
                "journal_time_labels": [r["time_label"] for r in source_rows],
                "handwritten_reference": f'Correction PDF p.{handwritten[d]["pdf_page"]}, {handwritten[d]["trade_id_as_written"]}' if d in handwritten else "",
                "author_original_comment": handwritten.get(d, {}).get("comment", ""),
                "current_orb_result": "NO_CONFIRMED_SIGNAL", "method1_verdict": {p["direction"]: p["failed"] for p in paths if p["method"] == "Method 1"},
                "method2_verdict": {p["direction"]: p["failed"] for p in paths if p["method"] == "Method 2"},
                "gap_verdict": {p["direction"]: p["failed"] for p in paths if p["method"] == "Gap/200DMA"},
                "first_failing_conditions": first_fails, "all_failed_conditions": path_fails,
                "all_additional_failures": {key: values[1:] for key, values in path_fails.items()},
                "irf_executed": any(r["strategy"] == "IRF" for r in trades),
                "another_strategy_executed": sorted({r["strategy"] for r in trades if r["strategy"] != "IRF"}),
                "selected_portfolio_strategy": "; ".join(r["strategy"] for r in trades) or "NO_TRADE",
                "no_automated_trade": not trades, "first_irf_signal_time": irf_signals[0].signal_timestamp.strftime("%H:%M") if irf_signals else "",
                "provisional_candidate_could_qualify": bool(alternatives), "candidate_alternatives": alternatives,
                "expected_entry_known": False, "expected_orb_direction": "UNKNOWN", "expected_entry_candle": "UNKNOWN",
                "manual_exact_execution_timestamp_known": False, "author_clarifications_required": source_questions(paths),
                "source_pdf_pages": "2-10,12-13; per-gate physical page in gate_evidence.csv",
                "chart": f"author_review_charts/{d}_overview.png", **blank_author_response()}
        all_cases.append(info)
        earlier = [day for day in sorted(all_contexts) if day < ctx.date][-5:]
        history = pd.concat([all_contexts[day].candles.assign(session_date=str(day)) for day in earlier], ignore_index=True)
        payload = {"case": info, "paths": paths, "geometry": paths[0]["geometry"], "trades": displays,
                   "orb_records": [record_view(r) for r in current_orb[d]],
                   "irf_records": [record_view(r) for r in irf_records],
                   "previous_date": str(ctx.previous.date), "previous_close": ctx.previous.close_official,
                   "previous_high": float(ctx.previous.candles.high.max()), "previous_low": float(ctx.previous.candles.low.min()),
                   "ema_at_opening_close": float(ctx.candles.ema200_5m.iloc[0]),
                   "daily_sma200_prev": ctx.daily_sma200_prev, "gap": paths[0]["gap"],
                   "one_minute": frame_records(raw_days[d], "timestamp"),
                   "five_minute": frame_records(ctx.candles, "bar_start"),
                   "previous_five_minute": frame_records(ctx.previous.candles, "bar_start"),
                   "history_five_minute": frame_records(history, "bar_start"),
                   "source_hashes": source_hashes, "config": "A", "author_entry": {"time": None, "price": None, "direction": None}}
        case_payload[d] = payload
        (OUT / "daily" / f"{d}.json").write_text(json.dumps(payload, indent=2, default=str))
        independent.to_csv(OUT / "daily" / f"{d}_independent_5m.csv", index=False)
        if d in irf_execution_dates:
            irf_trade = next(r for r in trades if r["strategy"] == "IRF")
            first_irf_table.append({"date": d, "journal_sheet_rows": info["orb_journal_sheet_rows"], "strategy": "IRF", "method": irf_trade["method"],
                                    "direction": irf_trade["direction"], "signal_time": irf_trade["signal_confirmed_at"], "entry_time": irf_trade["fill_timestamp"],
                                    "entry_price": irf_trade["entry_price"], "initial_stop": irf_trade["initial_stop"], "target_1": irf_trade["target_1"], "target_2": irf_trade["target_2"],
                                    "leg1_exit_time": irf_trade["leg1_exit_time"], "leg1_exit_price": irf_trade["leg1_exit_price"], "leg2_exit_time": irf_trade["leg2_exit_time"], "leg2_exit_price": irf_trade["leg2_exit_price"],
                                    "confirmed_earlier_orb": False, "hypothetical_candidates": alternatives,
                                    "author_expected_unverified": True, "author_approved_entry_identified": False,
                                    "orb_rejection": path_fails, "conditional_timing": "A source-qualified, author-marked09:20 ORB would precede this later IRF if no simultaneous collision; no ORB is invented or selected."})
    wr("journal_recount_rows.csv", journal)
    wr("all_cases.csv", all_cases)
    wr("all_13_handwritten_cases.csv", [r for r in all_cases if r["handwritten_dispute"]])
    wr("all_50_missing_orb_dates.csv", [r for r in all_cases if r["missing_journal_orb"]])
    wr("orb_vs_irf_34_dates.csv", first_irf_table)
    wr("gate_evidence.csv", gate_rows)
    wr("independent_aggregation_checks.csv", agg_checks)
    question_coverage = []
    question_predicates = {"Q1": {"inner_defined", "inner_close"}, "Q2": {"quality"}, "Q3": {"trendline"},
                           "Q4": {"gap_direction", "gap_crossing", "ma_close", "near_ma"}, "Q5": {"trend"}, "Q6": set()}
    for question, predicates in question_predicates.items():
        rows = [g for g in gate_rows if g["date"] in missing and g["predicate"] in predicates and g["passed"] is not True]
        question_coverage.append({"question": question, "failed_path_date_coverage": len({g["date"] for g in rows}) if predicates else len(missing),
                                  "reached_gate_date_coverage": len({g["date"] for g in rows if g["reached_in_code"]}) if predicates else len(missing),
                                  "sole_failed_gate_dates": sorted({g["date"] for g in rows if g["sole_failed_gate"]}),
                                  "all_relevant_dates": sorted({g["date"] for g in rows}) if predicates else sorted(missing),
                                  "interpretation": "Overlapping diagnostic paths, not known author causes. Unknown direction and method remain unresolved."})
    wr("question_coverage.csv", question_coverage)
    frequencies = []
    for method in ("Method 1", "Method 2", "Gap/200DMA"):
        for direction in ("LONG", "SHORT"):
            group = [g for g in gate_rows if g["date"] in missing and g["method"] == method and g["direction"] == direction]
            for predicate in dict.fromkeys(g["predicate"] for g in group):
                sub = [g for g in group if g["predicate"] == predicate]
                frequencies.append({"method": method, "direction": direction, "predicate": predicate,
                                    "failed_dates": sum(g["passed"] is not True for g in sub),
                                    "reached_failures": sum(g["passed"] is not True and g["reached_in_code"] for g in sub),
                                    "sole_failed_gate_dates": sum(g["sole_failed_gate"] for g in sub), "denominator": len(missing)})
    wr("rejection_frequency.csv", frequencies)
    baseline["case_union_dates"] = len(cases)
    baseline["handwritten_in_missing_journal"] = len(set(handwritten) & missing)
    baseline["handwritten_outside_orb_journal"] = sorted(set(handwritten)-manual_dates)
    baseline["no_trade_missing_dates"] = sum(r["no_automated_trade"] for r in all_cases if r["missing_journal_orb"])
    baseline["other_strategy_missing_dates"] = sum(bool(r["another_strategy_executed"]) for r in all_cases if r["missing_journal_orb"])
    baseline["other_and_irf_missing_overlap"] = [r["date"] for r in all_cases if r["missing_journal_orb"] and r["another_strategy_executed"] and r["irf_executed"]]
    baseline["original_source_hashes"] = source_hashes
    (OUT / "baseline_recount.json").write_text(json.dumps(baseline, indent=2))
    (OUT / "priority_cases.json").write_text(json.dumps(PRIORITY, indent=2))
    (OUT / "case_data.json").write_text(json.dumps(case_payload, default=str))
    # Demonstrate the optional defect without changing its class or active logic.
    from synthetic import ctx as synthetic_context

    demo = synthetic_context([(122, 123, 110, 120)], prev={"cands": [(100, 115, 90, 110)]*5, "close": 110, "ema_last": 100}, ema=100)
    wrapper_records = ORBColourStrategy(proposals=sc.proposals).evaluate_session(demo)
    invalid = [r for r in wrapper_records if r.invalidation_reason == "FIRST_CANDLE_COLOUR_AGAINST_DIRECTION"]
    defect = [{"strategy": r.strategy, "method": r.method, "signal_status": r.signal_status,
               "execution_entry_status": r.execution_config["entry_rule_status"], "selection_is_valid": is_valid(r)[0],
               "trace": r.state_trace} for r in invalid]
    (OUT / "optional_wrapper_probe.json").write_text(json.dumps({"records": defect,
        "orb_engine_classes": {k: [type(e).__name__ for e in engines_for(k, sc.proposals, sc.trade, sc.pdr_engine, sc.pdr_revision) if e.STRATEGY == "ORB"] for k in "ABC"},
        "phase59_uses_signal_status_not_execution_entry_label": True, "active_change": False}, indent=2))
    print(json.dumps({k:v for k,v in baseline.items() if k not in ("original_source_hashes", "phase58_workbook_summary")}, indent=2))
    print("No exit simulation, controller override or profitability calculation was called.")


if __name__ == "__main__":
    main()
