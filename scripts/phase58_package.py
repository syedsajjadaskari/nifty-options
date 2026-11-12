"""Prepare the verification workbook input and refresh verified evidence charts."""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/phase5/phase58_codex_orb_forensic_audit"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import phase58_charts as CH  # noqa: E402

from nifty_trading.research.phase58 import geometry  # noqa: E402


def rd(name):
    with open(OUT / name, newline="") as f:
        return list(csv.DictReader(f))


def truth(v):
    return int(v == "True")


def prepare():
    s = json.loads((OUT / "audit_summary.json").read_text())
    journal = rd("orb_all_manual_journal_dates.csv")
    observations = rd("orb_predicate_observations.csv")
    disputes = rd("orb_13_handwritten_disputes.csv")
    timeline = rd("orb_vs_irf_selection_timeline.csv")
    sources = rd("orb_source_to_code_mapping.csv")
    candidates = rd("orb_candidate_signal_differences.csv")
    metrics = ["evaluable_journal_dates", "orb_signal_dates", "no_orb_signal_evaluable_dates", "orb_executed_dates", "orb_signal_no_orb_execution", "irf_executed_dates", "another_strategy_executed_dates", "no_automated_trade_dates"]
    sheets = [
        {"name": "Overview", "title": "ORB forensic verification | Phase 5.8", "subtitle": "Independent source audit | Signal and existing-ledger evidence | 8 November 2026",
         "headers": ["Configuration", "Evaluable dates", "ORB signal", "No signal evaluable", "ORB executed", "Signal, no ORB fill", "IRF executed", "Other executed", "No trade"],
         "rows": [[k] + [s["configurations"][k][m] for m in metrics] for k in "ABC"], "numericColumns": list(range(1, 9))},
        {"name": "Journal", "title": "Every literal ORB journal date", "subtitle": "Source: original Trading Journal sheet; raw workbook has no direction, entry price or level. 1=yes, 0=no.",
         "headers": ["Config", "Date", "Session", "ORB signal", "ORB fill", "IRF fill", "Other fill", "No trade", "Signal/no ORB fill", "Evaluable", "Source sheet row", "Manual label", "Entry absence", "Other strategies"],
         "rows": [[r["config"], r["date"], r["session_status"], truth(r["orb_signal"]), truth(r["orb_executed"]), truth(r["irf_executed"]), int(r["other_executed"] != "[]"), truth(r["no_automated_trade"]), int(r["orb_signal"] == "True" and r["orb_executed"] != "True"), int(r["session_status"].startswith("USABLE")), json.loads(r["manual_sheet_rows"])[0], "; ".join(json.loads(r["manual_time_labels"])), r["entry_absence"], r["other_executed"]] for r in journal],
         "widths": [12, 16, 31, 15, 15, 15, 15, 15, 22, 15, 20, 18, 35, 25], "numericColumns": list(range(3, 11)), "dateColumns": [1]},
        {"name": "Disputes", "title": "All 13 handwritten ORB disputes | A/B/C", "subtitle": "Source: six-page correction PDF; physical page and written trade ID preserved. Unknown direction/method are not inferred.",
         "headers": ["Config", "Date", "PDF page", "Written trade ID", "Author comment", "ORB signal", "IRF fill", "Classification", "Body %", "Open", "High", "Low", "Close", "Candidate signals"],
         "rows": [[r["config"], r["date"], int(r["pdf_page"]), r["trade_id_as_written"], r["comment"], truth(r["orb_signal"]), truth(r["irf_executed"]), r["classification"], float(r["body_pct"]), float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]), r["candidate_additions"]] for r in disputes],
         "widths": [12, 16, 12, 23, 74, 15, 15, 40, 16, 17, 17, 17, 17, 80], "dateColumns": [1], "numericColumns": [2, 5, 6]},
        {"name": "Chronology", "title": "ORB versus IRF chronological evidence", "subtitle": "Source: fresh engine signals joined to existing Phase 5.5 ledger; no exit simulation; full gates in Predicates and daily reports.",
         "headers": ["Config", "Date", "Journal ORB", "Hand dispute", "ORB signal", "First IRF", "IRF method", "IRF fill", "Ledger trades", "Reason", "Author setup status"],
         "rows": [[r["config"], r["date"], truth(r["manual_orb_date"]), truth(r["handwritten_dispute"]), r["orb_actual_signal_time"], r["irf_first_signal_time"], r["irf_first_signal_method"], truth(r["irf_executed"]), r["ledger_trades"], r["why"], r["author_setup_recoverability"]] for r in timeline],
         "widths": [12, 16, 16, 16, 18, 18, 23, 15, 85, 110, 55], "numericColumns": [2, 3, 7], "dateColumns": [1]},
        {"name": "Predicates", "title": "All method/direction predicates, including hidden failures", "subtitle": "Source: independently reconstructed six paths; UNKNOWN author direction. Removing a gate is diagnostic sensitivity only.",
         "headers": ["Date", "Method", "Direction", "Gate", "Pass", "Reached", "Observed", "Authority", "Source", "Other failures if removed", "Removal qualifies", "Cause"],
         "rows": [[r["date"], r["method"], r["direction"], r["predicate"], "UNKNOWN" if r["passed"] == "" else truth(r["passed"]), truth(r["reached_in_code"]), r["observed"], r["authority"], r["source"], r["other_failures_if_removed"], truth(r["single_gate_removal_qualifies"]), r["cause"]] for r in observations],
         "widths": [16, 23, 16, 28, 15, 15, 85, 65, 75, 65, 22, 48], "numericColumns": [4, 5, 10], "dateColumns": [0]},
        {"name": "Sources", "title": "Original source to code traceability", "subtitle": "Source PDF: docs/strategy_docs/ORB_Strategy_Rulebook-2.pdf. Full filenames and SHA256 values are in source_inventory.csv.",
         "headers": ["ID", "Physical page / exact locator", "Source meaning", "Code path", "Function", "Line", "Authority", "Assessment"],
         "rows": [[r["id"], r["pdf_page_and_exact_locator"], r["source_rule"], r["code_path"], r["function"], int(r["line"]), r["authority"], r["source_to_code_assessment"]] for r in sources],
         "widths": [12, 66, 75, 80, 36, 12, 65, 100], "numericColumns": [5]},
        {"name": "Candidates", "title": "Isolated diagnostic signal differences | disabled", "subtitle": "Source rationale stated per row; method/direction records, not trades. No variants combined, no outcomes used.",
         "headers": ["Variant", "Date", "Change", "Method", "Direction", "Time", "Journal ORB", "Hand dispute", "Authority", "Rationale", "False-positive assessment"],
         "rows": [[r["variant"], r["date"], r["action"], r["method"], r["direction"], r["time"], truth(r["manual_orb_date"]), truth(r["handwritten_dispute"]), r["authority"], r["rationale"], r["false_positive_assessment"]] for r in candidates],
         "widths": [28, 16, 16, 23, 16, 15, 16, 16, 65, 100, 100], "dateColumns": [1], "numericColumns": [6, 7]},
    ]
    expected = {k: [s["configurations"][k][m] for m in metrics] for k in "ABC"}
    checks = [["Independent signal parity failures", len(s["independent_signal_parity_failures"])],
              ["ORB prefix failures", len(s["orb_prefix_failures"])],
              ["Stored signal differences", len(s["stored_signal_disagreements"])],
              ["Ledger signal / raw-fill failures", len(s["ledger_signal_or_fill_failures"])],
              ["First-selection chronology failures", len(s["first_selection_failures"])],
              ["OHLC bars checked (zero differences)", s["data_verification"]["ohlc_candles_checked"]]]
    (OUT / "workbook_data.json").write_text(json.dumps({"sheets": sheets, "expected": expected, "checks": checks}))
    if "--workbook-only" in sys.argv:
        print(f"Prepared {len(sheets)} workbook sheets without chart refresh")
        return
    # Charts reloaded from audited CSVs, preserving all measured values. This
    # refresh does not rerun strategies or the ledger/controller.
    pathrows = rd("orb_method_paths.csv")
    ledger = []
    with open(ROOT / "reports/phase5/phase55_combined_backtest/all_executed_trades.csv", newline="") as f:
        ledger = list(csv.DictReader(f))
    with open(ROOT / "reports/phase5/phase55_combined_backtest/all_confirmed_signals.csv", newline="") as f:
        signals = list(csv.DictReader(f))
    for d in sorted({r["date"] for r in pathrows}):
        import pandas as pd

        today = pd.read_csv(OUT / "daily" / f"{d}_5m.csv", parse_dates=["bar_start", "bar_end"])
        prev = pd.read_csv(OUT / "daily" / f"{d}_previous_5m.csv", parse_dates=["bar_start", "bar_end"])
        raw = pd.read_csv(OUT / "daily" / f"{d}_1m.csv", parse_dates=["timestamp"])
        paths = []
        for r in [r for r in pathrows if r["date"] == d]:
            for k in ("level", "inner_level", "trendline", "trendline_slope", "ema", "signed_breakout_distance"):
                r[k] = float(r[k]) if r[k] else None
            r["failed"] = json.loads(r["failed"])
            r["trendline_anchors"] = json.loads(r["trendline_anchors"])
            r["geometry"] = geometry(today.iloc[0])
            paths.append(r)
        # Original daily SMA value from audit context was included in chart; raw
        # daily history recomputation is isolated here and strictly prior.
        from nifty_trading.data.sessions import load_daily_official

        daily = load_daily_official()
        earlier = daily[daily.date < datetime.fromisoformat(d).date()]
        sma = float(earlier.close.iloc[-200:].mean()) if len(earlier) >= 200 else float("nan")
        context = SimpleNamespace(date=d, candles=today, previous=SimpleNamespace(candles=prev, ema_at_last_candle=float(prev.ema200_5m.iloc[-1])), daily_sma200_prev=sma, daily_history_count=len(earlier))
        recs = [SimpleNamespace(strategy=r["strategy"], signal_status="CONFIRMED", signal_timestamp=datetime.fromisoformat(d + "T" + r["time"]), direction=r["direction"]) for r in signals if r["date"] == d and r["config"] == "A"]
        notes = [f'{r["direction"]} {r["method"]}: {", ".join(r["failed"]) or "PASS"}; signed close distance {r["signed_breakout_distance"]:.2f}' if r["signed_breakout_distance"] is not None else f'{r["direction"]} {r["method"]}: undefined level' for r in paths]
        (OUT / "charts" / f"{d}.svg").write_text(CH.chart(context, raw, paths, recs, [t for t in ledger if t["date"] == d], notes))
    print(f"Prepared {len(sheets)} workbook sheets; refreshed {s['charts']} charts")


if __name__ == "__main__":
    prepare()
