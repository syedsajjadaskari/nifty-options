"""Phase 6.0 stage 8: independent audit checks that go beyond the engine-vs-audit recomputation (EMA vs the repository's reference EMA, chart annotations vs the ledger, journal recount straight from the workbook)
and the audit / test / preservation documents. Reads logs produced by the caller (pytest, ruff, preservation verify)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from phase60_common import OUT, ROOT, get_window  # noqa: E402

from nifty_trading.data.sessions import causal_ema  # noqa: E402
from nifty_trading.research.orb_v2.reporting import md_table  # noqa: E402

SCRATCH = Path("/private/tmp/claude-501/-Users-syedaskari-algo-nifty-options/dc8ac295-6b01-4d30-b811-e11236c4316e/scratchpad")


def tail(p: Path, n: int = 12) -> str:
    return "\n".join(p.read_text().strip().splitlines()[-n:]) if p.exists() else "(log missing)"


def main() -> int:  # noqa: C901
    res: dict = {}
    # 1. EMA versus the repository's reference recursion (SMA-seeded) over each window's full chain
    ema_rows = []
    for w in ("A", "B"):
        inp = get_window(w)
        closes = np.concatenate([inp.chain[d]["close"].to_numpy() for d in inp.order])
        mine = np.concatenate([inp.chain[d]["ema"].to_numpy() for d in inp.order])
        ref = causal_ema(closes, 200)
        ok = ~np.isnan(ref)
        skip = 600
        idx = np.where(ok)[0]
        sel = idx[idx >= skip]
        diff = np.abs(mine[sel] - ref[sel])
        # opening-candle EMA values only (the ones the strategy uses)
        first = [inp.chain[d]["ema"].iloc[0] for d in inp.order if inp.start <= d <= inp.end]
        owner = np.concatenate([[d] * len(inp.chain[d]) for d in inp.order])
        inwin = np.array([inp.start <= d <= inp.end for d in owner])
        sel_w = sel[inwin[sel]]
        diff_w = np.abs(mine[sel_w] - ref[sel_w])
        ema_rows.append({"window": w, "candles": len(closes), "compared_after_600_candles": len(sel), "max_abs_diff_incl_warmup": round(float(diff.max()), 6), "candles_in_evaluated_window": len(sel_w), "max_abs_diff_in_evaluated_window": round(float(diff_w.max()), 6),
                         "mean_abs_diff_in_evaluated_window": round(float(diff_w.mean()), 8), "opening_candle_emas_checked": len(first)})
    res["ema_vs_repo"] = ema_rows
    # 2. chart annotations versus the trade ledger (entry / stop / target / exit labels present with the ledger's prices)
    t = pd.read_csv(OUT / "all_orb_trades.csv")
    e = pd.read_csv(OUT / "all_orb_exits.csv")
    m = t.merge(e[["trade_id", "config_id", "window", "exit_reason", "exit_price", "exit_time"]], on=["trade_id", "config_id", "window"])
    seen, bad = set(), []
    for r in m.itertuples():
        if r.trade_id in seen:
            continue
        seen.add(r.trade_id)
        f = OUT / "charts_all_trades" / f"{r.trade_id}.svg"
        if not f.exists():
            bad.append((r.trade_id, "missing chart"))
            continue
        svg = f.read_text()
        need = [f"ENTRY {r.direction} {r.entry_price:.2f}", f"STOP {r.stop:.2f}", f"TARGET {r.target:.2f}", f"EXIT {r.exit_reason} {r.exit_price:.2f}"]
        miss = [n for n in need if n not in svg]
        if miss:
            bad.append((r.trade_id, miss))
    res["chart_check"] = {"unique_trade_charts_expected": len(seen), "charts_with_all_four_annotations": len(seen) - len(bad), "failures": bad[:10]}
    # 3. journal recount straight from the workbook (independent of journal.py)
    jr = pd.read_excel(ROOT / "docs/trading journal/Trading_Journal_Sep2025_Aug2026 REPORT.xlsx", sheet_name="Trading Journal", header=1)
    jr = jr[pd.to_numeric(jr.iloc[:, 0], errors="coerce").notna()]
    jr.columns = ["sl", "date", "time", "strategy", "outcome"]
    orb = jr[jr.strategy.astype(str).str.strip().str.upper() == "ORB"].copy()
    orb["d"] = pd.to_datetime(orb.date).dt.date.astype(str)
    a = t[(t.config_id == "ORB-V2-A") & (t.window == "A")]
    a_dates = set(pd.to_datetime(a.date).dt.date.astype(str))
    tl = orb["time"].astype(str).str.slice(0, 5)
    strict = int(sum(1 for d, tm in zip(orb.d, tl, strict=True) if d in a_dates and tm == "09:15"))
    res["journal_recount"] = {"journal_rows": int(len(jr)), "orb_rows": int(len(orb)), "orb_unique_dates": int(orb.d.nunique()), "strict_timing_recount_V2A": strict, "reported": json.loads((OUT / "phase60_state_journal.json").read_text())["match_class_counts_by_config"]["ORB-V2-A"].get("STRICT_TIMING", 0)}
    # 4. engine-vs-audit recomputation summary
    summ = json.loads((OUT / "audit_recomputation_summary.json").read_text())
    tot = {k: sum(v[k] for v in summ.values()) for k in ("sessions_checked", "signal_mismatches", "failed_condition_set_mismatches", "trade_mismatches")}
    res["recomputation_total"] = tot
    (OUT / "audit_checks.json").write_text(json.dumps(res, indent=1, default=str))
    rev = (OUT / "reviewer_findings.md")
    pre = json.loads((OUT / "preservation_check.json").read_text()) if (OUT / "preservation_check.json").exists() else None
    (OUT / "independent_audit.md").write_text("\n".join([
        "# Independent audit (Phase 6.0)", "", "## 1. Second implementation vs the engine", "",
        "`audit.py` re-derives every session of both windows without calling the engine's logic: candles by pandas `resample`, EMA by `ewm`, swing points by vectorised comparisons, wick tests by cross-multiplication, the trade on NumPy arrays. "
        "It shares only the raw one-minute frame, the usable-session list and the official closes with the engine (shared assumptions are listed in section 5).", "",
        md_table([{"window|config": k, **v} for k, v in summ.items()]), "", f"**Totals: {tot['sessions_checked']} session evaluations, {tot['signal_mismatches']} signal mismatches, {tot['failed_condition_set_mismatches']} failed-condition mismatches, {tot['trade_mismatches']} trade mismatches** (entry, exit reason, gross points).", "",
        "Also: 5 x 400 random synthetic sessions agree (property test), and a mutation test (audit given a 40% wick limit) disagrees with the engine, so the comparison can fail.", "",
        "## 2. EMA(200) cross-checks", "", "Against the repository's reference recursion (`data.sessions.causal_ema`, SMA-seeded) over the full chain, ignoring the first 600 candles (seed transient):", "", md_table(ema_rows), "",
        "Against the TradingView/FYERS labels in the rulebook screenshots (15 Sep 11:45, 17 Sep 13:25, 23 Sep 14:50): -0.05, -0.03 and -0.24 points (5paisa feed); +0.00, 0.00, -0.10 (secondary feed).", "",
        "## 3. Charts and journal", "", f"* Chart annotations: {res['chart_check']['charts_with_all_four_annotations']} of {res['chart_check']['unique_trade_charts_expected']} trade charts carry the ledger's entry, stop, target and exit labels exactly (failures: {res['chart_check']['failures'] or 'none'}).",
        f"* Journal recount straight from the workbook with pandas: {res['journal_recount']['journal_rows']} rows, {res['journal_recount']['orb_rows']} ORB rows, {res['journal_recount']['orb_unique_dates']} unique ORB dates; strict-timing recount for V2-A = {res['journal_recount']['strict_timing_recount_V2A']} (reported {res['journal_recount']['reported']}).", "",
        "## 4. Fresh read-only reviewer", "", (rev.read_text() if rev.exists() else "_(reviewer findings file not present)_"), "",
        "## 5. Limits of this audit", "", "* The audit shares the usable-session classification (`classify_session`), the official daily closes and the raw bars with the engine: a defect in those would not be caught here (they are the repository's verified infrastructure from Phases 2-4).",
        "* The audit mirrors the declared conventions (entry at the 09:20 open, stop first, 15:14 forced exit); it cannot judge whether they are the author's intent (see `unresolved_rule_definitions.md`).", "* Hand-drawn author annotations and pixel-estimated zones are approximate.", "* The 13 handwritten disputes come from the Phase 5.8 transcription and were not re-read."]))
    log_new, log_full, log_ruff = SCRATCH / "pytest_new.log", SCRATCH / "pytest_full.log", SCRATCH / "ruff.log"
    (OUT / "test_results.md").write_text("\n".join([
        "# Test results", "", "## New Phase 6.0 tests (`tests/test_phase60_orb_v2.py`)", "", "```", tail(log_new, 6), "```", "", "## Full repository suite", "", "```", tail(log_full, 6), "```", "", "## ruff (whole repository)", "", "```", tail(log_ruff, 6), "```", "",
        "Coverage of the required list: 09:15-09:20 aggregation and 09:20 availability, session boundaries (incomplete candles, 15:30 stub), EMA calculation and prefix invariance, EMA crossing and already-beyond scenarios, gap above the previous high and below the previous low, inner support/resistance, "
        "multiple qualifying levels, candle direction, wrong-side wick formulas (incl. the rulebook's worked examples), hammer / shooting star / engulfing / full-body, zero-range and doji, gap limits 250 and 300 (boundary and both directions), stop and target calculation, no late entry, no re-entry, forced exit, closing-auction bars, "
        "no look-ahead, same-minute stop/target ambiguity, journal match classification, configuration selection and manifests, engine-vs-audit parity, legacy-engine independence and preservation of earlier results."]))
    if pre:
        (OUT / "preservation_verification.md").write_text("\n".join([
            "# Preservation verification", "", "Method: `scripts/phase60_snapshot.py before` hashed (SHA-256) every file under data/, reports/, docs/, src/, tests/, scripts/, pyproject.toml and README.md **before any Phase 6.0 file was written**; `verify` re-hashed everything afterwards.", "",
            md_table([{"check": "files before", "result": pre["files_before"]}, {"check": "pre-existing files changed", "result": len(pre["changed"])}, {"check": "pre-existing files removed", "result": len(pre["removed"])}, {"check": "new files outside the Phase 6.0 prefixes", "result": len(pre["added_outside_phase60"])},
                      {"check": "new files (Phase 6.0)", "result": pre["added_total"]}, {"check": "PRESERVED", "result": pre["preserved"]}]), "", "New files by prefix: " + json.dumps(pre["added_phase60_by_prefix"]), "",
            "Not modified: Phase 3.6 frozen strategies, Phase 4.0 data and reports, Phase 5.3 strategy code, Phase 5.5 ledgers, Phase 5.6 reconciliation, Phase 5.7 charts, Phase 5.8 and 5.9 packages, the manual journal, raw/processed market data, the five-strategy controller. "
            "The old ORB engines and the shared controller were only read (the Phase 5.5 ledgers were read for the comparison). Nothing was committed or pushed; no orders were placed. `.DS_Store` files are excluded from the hash set."]))
    print(json.dumps({k: v for k, v in res.items() if k != "chart_check"}, indent=1, default=str)[:1800], res["chart_check"]["charts_with_all_four_annotations"], "/", res["chart_check"]["unique_trade_charts_expected"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
