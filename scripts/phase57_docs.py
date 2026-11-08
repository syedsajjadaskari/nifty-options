"""Phase 5.7: the markdown deliverables of reports/phase5/phase57_trade_visualization/, written from the CSV / JSON files produced by scripts/phase57_run.py and scripts/phase57_independent_audit.py (numbers are read, not typed).

  python scripts/phase57_docs.py --tests "<pytest result>" --ruff "<ruff result>"
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "phase5" / "phase57_trade_visualization"
K = ("A", "B", "C")
NAMES = {"A": "A - frozen Phase 3.6", "B": "B - Phase 5.3 author-corrected", "C": "C - B + ORB gap crossing (provisional)"}
WARN = ("SYNTHETIC NIFTY 50 index-point P&L (6 lots x 65 units); not option P&L. The journal records no price, direction or exit time, so 'exact' below means exact on DATE, STRATEGY and the entry-time LABEL only - "
        "never on price or outcome.")


def rd(p: Path) -> list[dict]:
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def tab(head: list[str], rows: list[list]) -> str:
    esc = lambda v: str(v).replace("|", "/").replace("\n", " ")  # noqa: E731
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(esc(c) for c in r) + " |" for r in rows])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--tests", default="not recorded in this run")
    ap.add_argument("--ruff", default="not recorded in this run")
    a = ap.parse_args()
    S = {r["config"]: r for r in rd(OUT / "exact_match_summary.csv")}
    BR = rd(OUT / "manual_match_breakdown.csv")
    st = json.loads((OUT / "phase57_state.json").read_text())
    ar = json.loads((OUT / "independent_audit_results.json").read_text()) if (OUT / "independent_audit_results.json").exists() else {"checks": {}, "all_pass": False}
    idx = rd(OUT / "all_executed_trades_visual_index.csv")
    hw_idx = rd(OUT / "handwritten_correction_chart_index.csv")
    n = {k: int(S[k]["automated_trades"]) for k in K}
    g = lambda k, f: int(S[k][f])  # noqa: E731
    strategies = ("IRF", "ORB", "PDR", "PDS", "RF")

    # ============================================================================================ exact_match_summary.md
    EM = ["# Exact journal-match summary (Phase 5.7)", "", f"> {WARN}", "",
          "## The answer: how many executed trades exactly match the manual journal?", "",
          tab(["configuration", "automated executed trades", "EXACT (strict) matches", "% of automated trades", "% of the 190 journal rows"],
              [[NAMES[k], n[k], g(k, "strict"), f"{S[k]['strict_pct_of_automated_trades']} %", f"{S[k]['strict_pct_of_190_journal_rows']} %"] for k in K]), "",
          "An EXACT match is a one-to-one pair with the same date, the same strategy and a journal entry-time label equal to the automated signal CANDLE START (the journal labels the five-minute candle start). Time-tolerant matches (within 15 minutes) are NOT mixed into this number, "
          "and date-and-strategy-only pairs are never counted as matches. The matching is the verified Phase 5.6 matching, unchanged.", "",
          "## Full table", "",
          tab(["measure", *[NAMES[k] for k in K]], [
              ["total automated executed trades", *[n[k] for k in K]], ["strict / EXACT matches", *[g(k, "strict") for k in K]], ["time-tolerant matches (0 < |delta| <= 15 min)", *[g(k, "time_tolerant") for k in K]],
              ["date-and-strategy-only pairs (time more than 15 min apart; NOT matches)", *[g(k, "date_strategy_only") for k in K]], ["total counted matches (strict + time-tolerant ONLY)", *[g(k, "counted_matches") for k in K]],
              ["counted matches as % of automated trades", *[f"{S[k]['counted_pct_of_automated_trades']} %" for k in K]], ["counted matches as % of the 190 journal rows", *[f"{S[k]['counted_pct_of_190_journal_rows']} %" for k in K]],
              ["manual-only rows - no counted match (includes the date-and-strategy-only pairs and the 5 Saturday rows)", *[g(k, "manual_only_rows_no_counted_match") for k in K]],
              ["  of which with no automated trade of the same date and strategy at all (journal-row view of 'manual only')", *[g(k, "manual_only_rows_without_any_same_date_strategy_trade") for k in K]],
              ["automated-only trades - no counted match (includes the date-and-strategy-only pairs)", *[g(k, "automated_trades_without_counted_match") for k in K]],
              ["  of which with no journal row of the same date and strategy left for them (AUTOMATED_ONLY on the charts)", *[g(k, "automated_only_trades_no_same_date_strategy_row") for k in K]],
              ["counted matches whose journal outcome label agrees with the automated exit class", *[g(k, "counted_same_outcome") for k in K]], ["counted matches whose outcome label differs", *[g(k, "counted_different_outcome") for k in K]],
              ["exact (strict) matches with the same outcome label", *[g(k, "strict_same_outcome") for k in K]], ["exact (strict) matches with a different outcome label", *[g(k, "strict_different_outcome") for k in K]]]), "",
          "Outcome labels are compared AFTER matching and never choose a pair (Target ~ TARGET, SL ~ INITIAL_FULL_STOP, BE ~ T1_THEN_BUFFER_STOP); what the journal's 'BE' meant is undocumented.", "",
          "## Exact (strict) matches by strategy", "",
          tab(["configuration", *strategies, "total"], [[NAMES[k], *[g(k, f"strict_{s}") for s in strategies], g(k, "strict")] for k in K]), "",
          "## Time-tolerant matches by strategy (reported separately)", "", tab(["configuration", *strategies, "total"], [[NAMES[k], *[g(k, f"time_tolerant_{s}") for s in strategies], g(k, "time_tolerant")] for k in K]), "",
          "## Per strategy: journal rows, automated trades and match stages", "",
          tab(["cfg", "strategy", "journal rows", "automated trades", "strict", "time-tolerant", "date + strategy only", "manual-only (no counted match)", "automated trades without counted match", "strict % of journal rows", "strict % of automated trades"],
              [[r["config"], r["strategy"], r["journal_rows"], r["automated_trades"], r["strict"], r["time_tolerant"], r["date_strategy_only"], r["manual_only_no_counted_match"], r["automated_trades_without_counted_match"], r["strict_pct_of_journal_rows_of_strategy"], r["strict_pct_of_automated_trades_of_strategy"]] for r in BR]), "",
          "## Reading the numbers", "",
          "* The 190 journal rows include 5 Saturday-dated rows that can never match; the maximum possible number of matches is therefore below 190.",
          f"* 'Exact' says the journal and the automated system started the SAME strategy on the SAME day with the SAME candle label. It does not say that prices or exits agree (the journal records neither). Of the exact matches, {sum(g(k, 'strict_same_outcome') for k in K)} of {sum(g(k, 'strict') for k in K)} (A + B + C) carry the same outcome label.",
          "* No configuration is selected or ranked here; the counts are descriptive. They come unchanged from `reports/phase5/phase56_manual_reconciliation/` (audited again by `independent_audit.md`).", "",
          "Files: `exact_match_summary.csv`, `manual_match_breakdown.csv`, `all_executed_trades_visual_index.csv` (one row per trade with its match status), `Phase57_Trade_Verification.xlsx`."]
    (OUT / "exact_match_summary.md").write_text("\n".join(EM) + "\n")

    # ============================================================================================ trade_visualization_summary.md
    ch = st["charts"]
    TV = ["# Trade visualization summary (Phase 5.7)", "", f"> {WARN}", "",
          "Every executed trade of configurations A, B and C has an enhanced chart in the visual spirit of the Phase 3.6 trade chart (real five-minute candles, EMA(200), reference levels and zones, role marks, dashed manual-journal lines) with the information needed for manual verification added next to the price action. "
          "No backtest was run and no rule or matching logic was touched: the numbers on the charts are read from the verified Phase 5.5 ledgers and the match labels from the verified Phase 5.6 files.", "",
          "## What each chart shows", "",
          tab(["element", "how it is drawn"], [
              ["header", "trade id, strategy, method, direction, configuration, date, first / second trade, outcome, signal candle, entry time and price, gross Rs; match-status badge (EXACT_MATCH green, TIME_TOLERANT_MATCH blue, DATE_STRATEGY_ONLY orange, AUTOMATED_ONLY grey) and the journal row reference"],
              ["entry", "black triangle at the exact one-minute position and price, labelled `ENTRY hh:mm @ price` next to it and in the right margin; the fill candle (one-minute bar) and the signal candle are listed in the ENTRY block together with the setup explanation and the trigger (strategy / method)"],
              ["initial stop, T1, T2", "named and priced lines (`SL @`, `T1 @`, `T2 @`) from the entry; the stop and T1 lines end when T1 is hit (the stop is then replaced), T2 runs to the last exit; each line continues faintly to its name in the right margin"],
              ["post-T1 stop", "orange dotted line `POST-T1 STOP @ price`, drawn ONLY from the moment T1 was booked (never before it; absent when T1 was not hit)"],
              ["exits", "leg 1: circle `LEG1 EXIT - T1 hit, hh:mm @ price`; leg 2: square `LEG2 EXIT - T2 hit / Post-T1 stop / Forced exit`; both legs on the same stop: one double ring `FULL EXIT - Initial SL`; the provisional 15:14 forced exit: `FORCED EXIT - 15:14 @ price`"],
              ["journal", "dashed magenta vertical line at the candle START of every journal row of the day (bold for the row matched to this trade); the journal records no price, so no manual price is drawn"],
              ["blocks", "ENTRY | LEVELS AND EXITS (with points from entry, both legs with reason, time, price) | P&L (3 + 3 lots, 195 + 195 units, points and rupees per leg, gross, net Rs 70 per trade and net with 0.25 / 0.5 / 1.0 point slippage per side) | JOURNAL COMPARISON (match type, journal row, journal label and outcome, agreement, time difference; for AUTOMATED_ONLY the Phase 5.6 root cause and evidence)"],
              ["context", "EMA(200) when in range, reference levels of the strategy (opening range, previous-day high / low, support / resistance, small support), the PDR / PDS zone, and the Phase 3.6 role marks (IR, C0, BRK, SIGNAL, CONFIRM, ...); levels far outside the price range are listed above the chart instead of squeezing the candles"]]), "",
          "Labels in the right margin are spread vertically so that no two overlap; labels next to markers avoid each other. The time axis starts at 09:15 and ends shortly after the last exit (at least 50 minutes after the entry) so that the candles stay readable.", "",
          "## Folders", "",
          tab(["folder", "charts", "content"], [
              ["`charts_all/`", ch["charts_all"], "every executed trade of A, B and C (`<config>_<trade id>.svg`)"], ["`charts_exact_matches/`", ch["charts_exact_matches"], "EXACT (strict) matches"], ["`charts_time_tolerant/`", ch["charts_time_tolerant"], "time-tolerant matches"],
              ["`charts_automated_only/`", ch["charts_automated_only"], "AUTOMATED_ONLY trades (no journal row of the same date and strategy left)"], ["`charts_date_strategy_only/`", ch["charts_date_strategy_only"], "date-and-strategy-only pairs (not matches; an extra folder so that every status has one)"],
              ["`charts_orb_focus/`", ch["charts_orb_focus"], f"all executed ORB trades plus {st['journal_day_charts']} journal-day charts (`DAY_<date>_ORB.svg`) for every ORB journal date without a counted match (weekend rows excluded)"],
              ["`charts_handwritten_dates/`", ch["charts_handwritten_dates"], "trades on the dates of the handwritten author corrections (index: `handwritten_correction_chart_index.csv`)"],
              ["`charts_config_differences/`", ch["charts_config_differences"], "trades that are not identical in A, B and C (method, direction, signal candle, entry, outcome or P&L differ, or the trade exists in only some configurations)"]]), "",
          "The subset folders hold byte-identical copies of the charts in `charts_all/`; the earlier Phase 3.6 / 5.5 / 5.6 charts were not touched.", "",
          "## How to verify a trade manually", "",
          "1. Open the chart; read the header for the trade, the configuration and the match status. 2. Check the `ENTRY` marker against the one-minute fill candle printed in the ENTRY block (open of the bar that starts when the signal candle ends). 3. Read the SL / T1 / T2 distances (35 or 30 / 27 / 60 or 70 points). "
          "4. Follow the price to the first exit: leg 1 at T1 (27 points) or the stop; after T1 the stop moves to entry -/+ 6. 5. Compare with the journal block. 6. Row-level numbers are in `Phase57_Trade_Verification.xlsx` and `all_executed_trades_visual_index.csv`.", "",
          "## Limits", "",
          "* Markers are drawn at their exact one-minute position on a five-minute candle chart; a one-minute entry or exit sits inside its candle.", "* The journal label is the candle start; the journal records no price, direction or exit, so only dates, strategies and times can be compared.",
          "* The 15:14 forced exit, the stop-first convention, the Rs 70 cost and the 390-unit position are provisional assumptions of the backtest; B and C rest on provisional conventions.", "* Synthetic index points only: no option premium, strike or expiry is drawn.", ""]
    (OUT / "trade_visualization_summary.md").write_text("\n".join(TV) + "\n")

    # ============================================================================================ independent_audit.md
    IA = ["# Independent audit (Phase 5.7)", "",
          f"`scripts/phase57_independent_audit.py` parses every rendered SVG (visible text, `data-*` attributes, embedded metadata and the geometry of the lines and markers) and compares it with the ledgers and the Phase 5.6 files; it recomputes the match counts with the independent staged matcher "
          f"of `phase56_independent_audit.py` from the original journal workbook (no `src/` imports). Result: **{'ALL ' + str(len(ar['checks'])) + ' CHECKS PASS' if ar['all_pass'] else 'FAILURES PRESENT'}**.", "",
          tab(["#", "check", "n", "result", "detail"], [[i + 1, nm, v["n"], "PASS" if v["pass"] else "FAIL", str(v["detail"])[:140]] for i, (nm, v) in enumerate(ar["checks"].items())]), "",
          "**The audit can fail.** A deliberate corruption of one chart (a changed label price and a moved line) made three checks fail (visible label, price geometry, byte-identity of the subset copy); the chart was then restored and the audit passes again.", "",
          "**Visual inspection.** Eight charts covering a T1-then-post-T1-stop trade, a full stop, a forced exit, a T2 trade, a second trade, a gap-slippage stop, an automated-only trade and a journal-day chart were rendered in a browser and read for overlaps and wrong labels; "
          "the badge width, the clipped zone name and the cut-off entry-price note found that way were fixed.", "",
          "**Independence caveat.** The audit script is a second implementation written in the same session as the charts; it shares no code with the chart generator other than the independent matcher of the Phase 5.6 audit.", "",
          "## Tests and lint", "", f"* Full suite: **{a.tests}**", f"* `ruff check src tests scripts`: **{a.ruff}**", "",
          "## What this phase did not do", "", "No backtest, no rule change, no change to the journal matching, no regeneration of earlier ledgers; no paper or live order; nothing committed or pushed."]
    (OUT / "independent_audit.md").write_text("\n".join(IA) + "\n")

    # ============================================================================================ README
    R = ["# Phase 5.7 - enhanced trade visualization and exact journal-match report", "", f"> {WARN}", "",
         tab(["configuration", "automated trades", "EXACT matches", "time-tolerant", "date + strategy only", "automated-only", "manual-only rows (no counted match)"],
             [[NAMES[k], n[k], g(k, "strict"), g(k, "time_tolerant"), g(k, "date_strategy_only"), g(k, "automated_only_trades_no_same_date_strategy_row"), g(k, "manual_only_rows_no_counted_match")] for k in K]), "",
         f"{st['executed_trades']} enhanced trade charts (`charts_all/`) plus subset folders and {st['journal_day_charts']} journal-day charts; every drawn value equals the verified ledgers, every match label equals the verified Phase 5.6 files.", "",
         "## Files", "", "`exact_match_summary.md` / `.csv`, `manual_match_breakdown.csv`, `trade_visualization_summary.md`, `all_executed_trades_visual_index.csv`, `Phase57_Trade_Verification.xlsx`, `handwritten_correction_chart_index.csv`, `journal_day_charts_index.csv`, `independent_audit.md`, "
         "`charts_all/`, `charts_exact_matches/`, `charts_time_tolerant/`, `charts_automated_only/`, `charts_date_strategy_only/`, `charts_orb_focus/`, `charts_handwritten_dates/`, `charts_config_differences/`, `before_hashes.json` (hashes of the earlier results, taken before the first write).", "",
         "## Reproduce", "", "```", "cd /Users/syedaskari/algo/nifty-options && source .venv/bin/activate", "python scripts/phase57_run.py              # charts, index, summary CSVs, workbook (no backtest)", "python scripts/phase57_independent_audit.py", "python scripts/phase57_docs.py --tests \"...\" --ruff \"...\"", "```", "",
         f"Audit: {'all checks pass' if ar['all_pass'] else 'NOT all checks pass - see independent_audit.md'}. Handwritten-correction index rows: {len(hw_idx)}; visual-index rows: {len(idx)}."]
    (OUT / "README.md").write_text("\n".join(R) + "\n")
    print("phase 5.7 docs written; audit:", "ALL PASS" if ar["all_pass"] else "FAILURES / not run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
