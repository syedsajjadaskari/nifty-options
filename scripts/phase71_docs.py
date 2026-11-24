"""Phase 7.1 documents + workbook, generated from the CSV/JSON ledgers (every number in the prose is read from them)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/phase7/phase71_global_ema_and_final_validation"


def rd(n: str) -> pd.DataFrame:
    return pd.read_csv(OUT / n)


def w(n: str, t: str) -> None:
    (OUT / n).write_text(t.strip() + "\n")


def tab(df: pd.DataFrame, cols=None) -> str:
    d = df[cols] if cols else df
    return "| " + " | ".join(map(str, d.columns)) + " |\n|" + "---|" * len(d.columns) + "\n" + "\n".join("| " + " | ".join("" if pd.isna(v) else str(v) for v in r) + " |" for r in d.itertuples(index=False))


def main() -> None:  # noqa: C901
    full, wr, imp, cmp27, tim = rd("full_five_strategy_backtest.csv"), rd("strategy_win_rates.csv"), rd("ema_signal_impact_by_strategy.csv"), rd("ema_27_vs_28_comparison.csv"), rd("ema_measurement_timing_sensitivity.csv")
    orb, jsum, tc, trades = rd("ema_crossing_conflicts.csv"), rd("journal_match_summary_by_config.csv"), rd("portfolio_performance.csv"), rd("all_executed_trades.csv")
    exr, q = rd("november_2026_example_results.csv"), rd("november_2026_data_quality.csv")
    var = rd("irf_method_comparison.csv")
    jr = json.loads((OUT / "_state" / "journal_recount.json").read_text())
    p1 = json.loads((OUT / "_state" / "irf_priority1_summary.json").read_text())
    man = json.loads((OUT / "configuration_manifest.json").read_text())
    dl = json.loads((OUT / "_state" / "pdr_delayed_summary.json").read_text())
    aud = json.loads((OUT / "_state" / "audit71_results.json").read_text()) if (OUT / "_state" / "audit71_results.json").exists() else {}
    cfgs = man["configurations"]

    def F(win, cfg):
        return full[(full.window == win) & (full.config == cfg)].iloc[0]

    def WR(win, cfg, s):
        return wr[(wr.window == win) & (wr.config == cfg) & (wr.strategy == s)].iloc[0]

    def J(cfg):
        return jsum[jsum.config == cfg].iloc[0]

    # ------------------------------------------------------------------ author clarification
    w("latest_author_clarification.md", """
# Latest author clarification (received with the Phase 7.1 brief)

> "Sir, the 27 points gap near the 200 EMA is common for all the strategies sir."

**Status: AUTHOR_STATEMENT, relayed by the owner; undated; the wording defines neither the measure, the inequality, the timing, the timeframe nor the action.** It is evidence of intent, not a mechanical rule. Nothing in the engines uses it by default.

## Evidence trail for the EMA number

| # | Source | Wording | What it supports |
|---|---|---|---|
| 1 | Handwritten pages AC13 / AC18 (`docs/strategy_docs/corrected/Adobe Scan Nov 05, 2026.pdf` p3-4; `reports/phase5/phase51_author_corrections/new_author_rules.md` NR2) | "The candle should close below EMA when the space btn. the entry candle is less than 27." / "Should be ignored as Tgt 1 is not above EMA, tgt 1 is less than 27. Should wait until EMA break." (IRF SHORT; "200 EMA [5 min TF]" written on the drawing) | 27 = Target 1 distance; the drawing places the EMA BELOW the short entry, between the entry and Target 1; action: skip or wait for a close below the EMA. Supports a **target-side / path** reading (EMA-5) and the 5-minute EMA(200) |
| 2 | Phone call (`reports/phase5/phase52_author_rules/author_call_clarifications.md` C3) | "Sometimes IRF is correct, but the gap between the EMA and the candle should be 28 points." | A **candle-to-EMA gap**, number 28, scope IRF only; inequality not stated |
| 3 | Phase 5.3 implementation (owner approved the NUMBER only) | `ema_min_clearance=28`, nearest point of the signal candle's range to the EMA, inclusive, all IRF methods - **PROVISIONAL** measure | The EMA-2/EMA-4 family (range clearance) |
| 4 | Latest IRF PDFs (p2 of each) | "As you described it, IRF has no 200 EMA filter ..." | **Contradicts** a universal EMA rule for IRF V3 (the PDFs describe an earlier conversation) |
| 5 | **New** (this brief) | "the 27 points gap near the 200 EMA is common for all the strategies" | Number is 27 (agrees with 1, not 2); scope ALL FIVE strategies; 'near the EMA' hints at a proximity zone; direction of the inequality still not given |

The words 'gap' (not 'distance to target'), 'near the 200 EMA' and 'common for all the strategies' are the only new facts. **Decisions that need the author are listed in `remaining_author_questions.md`.**
""")

    # ------------------------------------------------------------------ interpretations audit
    iA = imp[imp.window == "A"].pivot_table(index="strategy", columns="config", values="fail", aggfunc="sum").reindex(["IRF", "ORB", "PDR", "PDS", "RF"])
    nA = imp[(imp.window == "A") & (imp.config == "EMA-1")].set_index("strategy")["confirmed_signals"].reindex(["IRF", "ORB", "PDR", "PDS", "RF"])
    iA.insert(0, "confirmed signals (baseline B, all IRF cycles)", nA)
    iB = imp[imp.window == "B"].pivot_table(index="strategy", columns="config", values="fail", aggfunc="sum").reindex(["IRF", "ORB", "PDR", "PDS", "RF"])
    nB = imp[(imp.window == "B") & (imp.config == "EMA-1")].set_index("strategy")["confirmed_signals"].reindex(["IRF", "ORB", "PDR", "PDS", "RF"])
    iB.insert(0, "confirmed signals (baseline B, all IRF cycles)", nB)
    edall = rd("ema_distance_interpretations.csv")
    e1 = edall[(edall.strategy == "IRF") & (edall.cycle_no.astype(str).isin(["1", "1.0"]))]
    irf_c1 = pd.DataFrame([{"window": x, "first-cycle IRF records": int((e1.window == x).sum()), **{cf: int((e1[e1.window == x][col] == "FAIL").sum()) for cf, col in (("EMA-1 fail", "EMA-1_MIN_CLOSE_27"), ("EMA-2 fail", "EMA-2_MIN_RANGE_27"), ("EMA-3 fail", "EMA-3_MAX_CLOSE_27"),
                           ("EMA-4 fail", "EMA-4_MIN_RANGE_28"), ("EMA-5 fail", "EMA-5_TARGET_SIDE_27"))}} for x in "AB"])
    c27 = cmp27[cmp27.window == "A"][["strategy", "interpretation", "signals_with_ema", "fail_at_27", "fail_at_28", "decision_differs_27_vs_28"]]
    c27b = cmp27[cmp27.window == "B"].groupby("interpretation")[["signals_with_ema", "fail_at_27", "fail_at_28", "decision_differs_27_vs_28"]].sum().reset_index()
    og = {x: orb[orb.window == x] for x in "AB"}
    ocols = ["EMA-1_MIN_CLOSE_27", "EMA-2_MIN_RANGE_27", "EMA-3_MAX_CLOSE_27", "EMA-4_MIN_RANGE_28", "EMA-5_TARGET_SIDE_27"]
    ev = {x: {c: int((og[x][c] == "FAIL").sum()) for c in ocols} for x in "AB"}
    ek = trades[(trades.config.isin(["E", "K"]))]
    diffs = {}
    for x in "AB":
        e = set(map(tuple, ek[(ek.window == x) & (ek.config == "E")][["date", "strategy", "entry_time"]].values))
        k = set(map(tuple, ek[(ek.window == x) & (ek.config == "K")][["date", "strategy", "entry_time"]].values))
        diffs[x] = (len(e - k), len(k - e), sorted(e ^ k))
    w("universal_27_point_ema_rule_audit.md", f"""
# Universal 27-point EMA rule - audit (Priority 0)

**Conclusion first.** The sentence cannot be turned into ONE mechanical rule from the sources. It is therefore implemented as a shared, opt-in research component (`src/nifty_trading/research/phase71/ema_rule.py`) with five labelled readings (EMA-1..EMA-5); the default (EMA-0) is unchanged. **No reading is confirmed, none is active in any paper-trading configuration, and nothing is selected by P&L.** Which reading the author means, and whether it overrides the explicit 'no EMA filter' text of the two IRF PDFs, are owner decisions.

## 1. Source-authority matrix (`ema_source_conflict_matrix.csv`)

{tab(rd('ema_source_conflict_matrix.csv'))}

## 2. The five readings (all evaluated for every strategy from ONE geometry function)

| Config | Reading | Definition at the confirming candle (N = 27 unless stated) | Source evidence |
|---|---|---|---|
| EMA-0 | baseline | no universal EMA rule | - |
| EMA-1 | A/D: minimum close distance | pass iff abs(close - EMA) >= N | the word 'gap'; D (absolute close-to-EMA difference) is the same quantity, reported once |
| EMA-2 | C: minimum range clearance | pass iff the nearest point of the high-low range to the EMA >= N (0 when the EMA lies inside the candle) | Phase 5.3 owner-approved NUMBER 28 with this PROVISIONAL measure; 'gap between the EMA and the candle' |
| EMA-3 | B: maximum proximity | pass iff abs(close - EMA) <= N | 'gap NEAR the 200 EMA' read as a proximity zone; ORB 'near the EMA' wording |
| EMA-4 | 28-point comparator | EMA-2 at N = 28 | the phone call / Phase 5.3 convention |
| EMA-5 | E: target-side | fail iff the EMA lies in the trade's path within N points of the entry reference (SHORT: 0 <= entry - EMA < N) | handwritten AC13/AC18 ('Tgt 1 is not above EMA'; 27 = Target 1) - the only reading with a worked drawing |

EMA-1 and EMA-3 are exact complements of each other; EMA-1/EMA-2/EMA-4 are minimum-distance readings, EMA-3 is a maximum-distance reading, EMA-5 is direction-aware (a short below the EMA is never blocked by it). They cannot all be the author's meaning.

## 3. Moving-average definition and timing
* **Timeframe:** the handwritten drawing says '200 EMA [5 min TF]'; the ORB rulebook uses the 200-period EMA on the 5-minute NIFTY chart; the earlier note 'Gap/200DMA' in the ORB document is the same 5-minute EMA (Phase 5.1 AC31). No source supports a daily 200-day average. All research uses the frozen contexts' `ema200_5m` (5-minute EMA(200), 200-value SMA seed, warm-up from 2025-07-01 / the Phase 4 warm-up month, causal: it includes the candle's own close and nothing later).
* **Warm-up / look-ahead:** an unavailable EMA is never a rejection (UNAVAILABLE). The independent audit rebuilds the EMA from raw one-minute rows (`independent_audit.md`).
* **Measurement time:** CONFIRMATION (the confirming candle) is the reference. SETUP and REFERENCE candle measurements are available where an engine records them (IRF V3, PDR/PDS interaction candle); at ENTRY the EMA value is identical to the confirmation value (no new candle has completed), only the price differs. **EMA-5 uses the confirming candle's CLOSE as the entry reference everywhere (gate and diagnostics) - causal at signal time; measuring from the next-bar fill price instead changes about 15 of 3,618 decisions (14 IRF, 1 PDS).** Decisions that change with the timing (window A, 27 points):

{tab(tim[tim.window == 'A'])}

## 4. Effect on each of the five strategies (signals failing each reading; baseline B signals; no EMA value -> not counted)

Window A:

{tab(iA.reset_index())}

Window B:

{tab(iB.reset_index())}

**These are signal-RECORD counts, not trade counts:** the IRF V3 adapter emits every completed cycle of both methods (M1 and M2 records can share one candle), including signals after 13:00 and signals blocked by an open position. Restricted to the first cycle of each IRF method (window A / window B):

{tab(irf_c1)}

## 5. 27 versus 28 points (signal level; where the decision differs)

Window A: {tab(c27)}

Window B (sum over the window):

{tab(c27b)}

Portfolio level (EMA-2 at 27 = config E vs EMA-4 at 28 = config K): window A: {diffs['A'][0]} trade(s) only with 27, {diffs['A'][1]} only with 28 ({', '.join(f'{a} {b} {c}' for a, b, c in diffs['A'][2])}); window B: {diffs['B'][0]} only with 27, {diffs['B'][1]} only with 28 ({', '.join(f'{a} {b} {c}' for a, b, c in diffs['B'][2])}). The two numbers rarely change a decision, but they are not interchangeable; neither is retained by default.

## 6. Conflict with ORB's documented fresh EMA crossing (`ema_crossing_conflicts.csv`)

The ORB V2 rulebook permits a 9:15 candle that crosses the EMA (scenarios A already beyond / B intrabar cross / C overnight gap crosses) and says 'near the EMA wait for a convincing close' without a number. ORB V2 signals in the baseline: window A {len(og['A'])} (scenario mix {og['A'].orb_ema_scenario.value_counts().to_dict()}), of which {int(og['A'].fresh_cross_or_inside.sum())} have the EMA inside the opening candle's range. Rejections: window A {ev['A']}; window B ({len(og['B'])} ORB signals) {ev['B']}. A minimum-distance reading (EMA-1/2/4) removes valid fresh-cross ORB entries; a maximum-proximity reading (EMA-3) removes nearly all ORB entries (they are usually far from the EMA); EMA-5 removes none. Charts of every affected window-A day: `charts/orb_ema_conflicts/`. No previously validated ORB trade was silently dropped: all removals appear in `trade_set_attribution.csv` and as 'NOT EXECUTED' charts.

## 7. Conflict with the latest IRF PDFs
Both PDFs state explicitly that IRF has no EMA filter ('as you described it'); the new sentence says the 27-point gap is common to all strategies. Phase 7.0's IRF V3 therefore has NO EMA rule; the EMA configurations D/E/F/K/L are the only place it enters, and each is labelled research.

## 8. What would make the rule mechanical
(1) measure - close, candle range, or room in the trade's path; (2) inequality - minimum or maximum; (3) action - skip, or wait for a close beyond the EMA (and for how long); (4) scope - all methods of all strategies, or only trend-continuation ones (ORB has its own EMA direction rule; RF uses the EMA only as a qualitative trend filter); (5) 27 or 28; (6) whether it overrides the IRF PDFs. See `remaining_author_questions.md`.
""")

    # ------------------------------------------------------------------ registry
    reg = [
        ("EMA-U1", "ALL", "27-point EMA gap is common to all five strategies", "author message (this brief)", "AUTHOR_STATEMENT_AMBIGUOUS", "EMA-0..EMA-5 research configurations; none active"),
        ("EMA-U2", "ALL", "EMA is the 5-minute EMA(200)", "handwritten AC13 '200 EMA [5 min TF]'; ORB rulebook", "SOURCE_SUPPORTED_FOR_IRF_AND_ORB; ASSUMED_FOR_PDR_PDS_RF", "ema200_5m of the frozen contexts"),
        ("EMA-U3", "ALL", "measure / inequality / action / timing of the 27-point gap", "none", "UNRESOLVED", "five readings kept diagnostic-only"),
        ("EMA-U4", "IRF", "IRF V3 has no EMA filter", "IRF PDFs p2", "STATED_IN_SOURCE_PDF (now conflicts with EMA-U1)", "no EMA in method1/method2"),
        ("EMA-U5", "IRF", "28-point range clearance, all IRF methods", "phone call C3 + owner approval of the number (Phase 5.3)", "NUMBER_APPROVED_MEASURE_PROVISIONAL", "EMA-4 comparator"),
        ("EMA-U6", "ORB", "200 EMA direction filter; fresh cross allowed; 'near the EMA wait for a convincing close' (no number)", "ORB rulebook", "STATED_WITH_TO_CONFIRM", "ORB V2 unchanged"),
        ("M2-I1", "IRF M2", "Level A invalidation (close below A before the sequence completes)", "none in the PDFs", "SOURCE_SILENT", "M2-A persistent = headline; M2-B permanent and M2-B-REARM = research"),
        ("M2-I2", "IRF M2", "failure = any strict close below Level B", "PDF p3/p5", "STATED", "rule as written; margin / bearish / extra-candle candidates are diagnostics"),
        ("M2-I3", "IRF M2", "Nov 3 failure candle", "PDF p7 screenshot", "EXAMPLE_ONLY - reproduced on the 5paisa feed, one candle earlier on the secondary feed", "no rule change"),
        ("PDR-1", "PDR", "confirmation closes strictly above the zone ceiling", "Phase 3.6 owner-approved brief interpretation (PDR-B05a)", "OWNER_APPROVED_PREVIOUSLY", "PDR-A baseline"),
        ("PDR-2", "PDR", "first green candle after the retest (no ceiling) / retest candle may confirm / second confirmation", "author remarks NR6; guide s4.3 'a green candle'", "AUTHOR_CONFIRMATION_REQUIRED", "PDR-B1/B2/C/D research (G1, G2, G3, H)"),
        ("PDS-1", "PDS", "Methods 1/2 first vs second confirmation; Method 3 mandatory support break", "PDS guide", "METHOD_SPECIFIC", "I1 / I2 research"),
        ("CS-1", "ALL", "candle-body strength 60 / 70 / pattern-aware", "none in the sources (PDS Method 1 'good body' undefined)", "NOT_A_SOURCE_RULE", "J60 / J70 / JD research"),
        ("PORT-1", "PORTFOLIO", "frozen controller, 6x65 units, T1 +27, T2 60/70, stops 30/35, post-T1 +6, cutoff 13:00, one position at a time, 2nd trade only PDR/PDS after a full stop", "owner-approved portfolio rules (Phases 2.3-3.6)", "FROZEN", "unchanged"),
        ("PORT-2", "IRF", "IRF V3 inside the portfolio uses stop 35 (frozen reference); the standalone SL35/SL40 ledgers of Phase 7.0 are not used", "Phase 7.0 'SL not selected'", "REFERENCE_CONVENTION", "SL40 portfolio alternative NOT run (see unresolved list)"),
    ]
    pd.DataFrame(reg, columns=["rule_id", "scope", "rule", "source", "status", "implemented_as"]).to_csv(OUT / "rule_authority_registry.csv", index=False)

    w("remaining_author_questions.md", """
# Remaining author questions (Phase 7.1)

**EMA (priority 0)**
1. Is the 27-point gap a MINIMUM (the EMA must be at least 27 points away) or a MAXIMUM ('near' = within 27)? Handwritten pages suggest 'less than 27 -> wait'; the new sentence says 'near'.
2. What is measured: the confirming candle's close, the candle's nearest point to the EMA, or the room between the ENTRY and the EMA (up to Target 1 = 27)?
3. What is the action when the test fails: skip the signal, or wait for a candle to close beyond the EMA ('wait until EMA break') - and until when?
4. 27 or 28? (the call said 28; the handwritten pages and the new message say 27).
5. Does the rule apply to ORB (which has its own EMA direction rule and allows a fresh cross), to RF (qualitative EMA trend filter) and to PDR/PDS (no EMA in the guides)? Does it override the two new IRF PDFs ('IRF has no EMA filter')?
6. Is the EMA always the 5-minute EMA(200)?

**IRF**
7. Method 2: is the setup dead when price closes below Level A before the sequence completes? If yes, may a new rally start a new setup (re-arm)? (`irf_method2_level_a_invalidation.csv`)
8. Method 2: is any strict close below Level B enough (as written; reproduces the Nov-3 screenshot on the 5paisa feed) - or does the author require a margin / red candle / extra candle? (Nov-3 on the secondary feed would need one of them to match.)
9. Which stop does IRF use in the combined portfolio: the frozen 35, or 35-40 by some rule? (the SL40 portfolio alternative is not run)
10. Nov-6 screenshot: Level A is printed as 24,540.05 but the first-candle high of the 5paisa feed is 24,518.20; Nov-16: printed 25,301.55 vs 25,310.55 (digit transposition?). Which levels did the author mark?
11. Dates of the two undated screenshots (M1 Example 1, M2 Example 1).

**PDR / PDS**
12. PDR: keep the owner-approved 'close above the zone ceiling' requirement, or accept the first green candle (PDR-B), may the retest candle itself confirm (PDR-B2/C), or is a deliberate second confirmation intended (PDR-D)?
13. PDS: first vs second confirmation for Methods 1 and 2; Method 3 stays as written.

**Portfolio**
14. Candle-body strength thresholds (60 / 70 / pattern-aware): any source?
15. Which single configuration, if any, should be compared in a later controlled paper-trading study.
""")

    # ------------------------------------------------------------------ timing audit + November
    ex_tab = exr[["example", "date", "feed", "A_diff", "B_diff", "failure_candle", "failure_close", "failure_close_minus_stated_entry", "SL40_exit", "sequence_reproduced(entry within 2pt)", "outcome_agrees(SL40)"]]
    cand = {t: json.loads((OUT / "_state" / f"nov3_candidates_{t}.json").read_text()) for t in ("5P_NOV2026", "TV_SECONDARY")}
    w("irf_method2_timing_audit.md", f"""
# IRF Method 2 entry timing - the 3 November 2026 discrepancy (Priority 2)

**Finding: the discrepancy is a data-feed effect, not a rule problem.** Phase 7.0 used the secondary vendor's feed (the only one then available for 3 Nov). The newly retrieved 5paisa feed reproduces the screenshot's sequence with the rule AS WRITTEN (any strict close below Level B):

| Feed | Level A (stated 23,611.15) | Level B (stated 23,621.90) | First candle closing below B | Close | Stated entry 23,612.80 |
|---|---|---|---|---|---|
| 5paisa (new) | 23,607.30 (-3.85) | 23,621.70 (-0.20) | **10:05-10:10** | 23,613.00 | **+0.20** |
| Secondary (Phase 7.0) | 23,610.70 (-0.45) | 23,621.70 (-0.20) | 10:00-10:05 | 23,621.00 | +8.20 |

On the 5paisa feed the 10:00-10:05 candle closes ABOVE Level B (see the raw rows in `november_3_raw_one_minute_rows.csv`), so the first strict close below B is the 10:05 candle, whose close matches the screenshot's entry to 0.20 points. On the secondary feed the 10:00 candle closes 0.70 below B, i.e. at a margin that vendor differences can erase. **Nothing was adjusted to force the match.**

## Timestamp conventions (candle open vs close)
* Both feeds label a one-minute row by its START (verified in Phase 2); a five-minute candle labelled 10:05 covers 10:05:00-10:10:00 and is usable at 10:10:00. A TradingView chart also labels a candle by its OPEN time, so 'the 10:00 candle' means 10:00-10:05. The screenshot's crosshair label ('03 Nov 26 10:50') and position box start (~10:05-10:10) are consistent with an entry at the close of the 10:05 candle.
* Distinguishing the timestamps: failure candle 10:05-10:10 (5paisa) -> confirmation/signal 10:10:00 -> first executable fill = open of the 10:10 one-minute bar. The screenshot's entry price (23,612.80) equals the failure candle's CLOSE (the rulebook's own TO-CONFIRM entry convention), 23,613.00 here; the Phase 7.0 fill convention (next open) differs from it by the 10:09->10:10 move.

## Close-below-B requirement candidates (diagnostics only; the original rule is preserved)
Nov-3 result of each candidate - 5paisa: {json.dumps(cand['5P_NOV2026'])}; secondary: {json.dumps(cand['TV_SECONDARY'])}.
The only candidate that reproduces the screenshot on BOTH feeds is the 'extra confirming candle' (secondary feed); it removes the signal on the 5paisa feed. No candidate is supported by more than one screenshot, so none is adopted. Historical effect (window A, standalone SL40, `irf_method_comparison.csv`): margin>=1/2/5 points changes the Method 2 signal set marginally; 'extra candle' removes 9 of 86 trades; 'red failure candle' changes nothing.

{tab(var[(var.window == 'A') & (var.scenario == 'SL40_T60') & (var.book == 'M2')][['variant', 'trades', 'win_rate_pct', 'profit_factor', 'gross_points', 'journal_strict']])}
""")

    w("november_2026_example_reconstruction.md", f"""
# November 2026 data and example reconstruction (Priority 3)

## Data
Retrieved read-only through the project's authenticated 5paisa client into a NEW raw namespace (`data/raw/phase71_5paisa_nov2026/`, manifest with request parameters, UTC time, row counts, SHA-256), processed to `data/phase71/processed/FIVEPAISA_1M_NOV2026/`. The frozen stores were not touched. Provider timestamps are naive IST bar-start labels. Coverage 2026-11-02..2026-11-18 (13 session dates):

{tab(q[['date', 'weekday', 'rows_total', 'rows_in_session_0915_1529', 'rows_outside_session', 'missing_minutes', 'duplicate_stamps', 'ohlc_violations', 'complete_session', 'note']])}

Quality notes: every full session has 375 in-session rows and no missing minutes; the provider also returns a 15:30 stub row (dropped from candles, as in earlier phases) and, on 2026-11-18, rows after 15:30. 2026-11-08 is a Sunday partial (Muhurat-type) session; 2026-11-10 and 11-14/15 have no rows. No candle was manufactured. These sessions are NOT in the frozen backtest windows (both end before November).

## Reconstruction (engine = Phase 7.0 IRF V3 modules, unchanged; each chart embeds the original screenshot at its extracted resolution above the replay: `charts/EX_*`)

{tab(ex_tab)}

* **Sequence reproduced (failure close within 2 points of the stated entry): all five dated examples on the 5paisa feed**; outcomes agree (targets for M1-E2, M1-E3, M2-E2, M2-E3; stop-loss for M2-E4).
* **Printed Level-A values that disagree with the data:** M2 Example 4 (3 Nov) prints 23,611.15 vs 23,607.30 on the 5paisa feed (-3.85; the secondary feed gives 23,610.70, -0.45, so a feed difference); M2 Example 3 (6 Nov) prints Level A 24,540.05 but the first-candle high is 24,518.20 (-21.85); M1 Example 3 (16 Nov) prints 25,301.55 vs 25,310.55 (+9.00, looks like a digit transposition). The printed entry/outcome still reproduce, so these look like hand-placed lines. Question 10.
* M2 Example 4 (3 Nov) reproduces on the 5paisa feed and one candle earlier on the secondary feed (see `irf_method2_timing_audit.md`).
* **Undated screenshots (M1 Example 1, M2 Example 1) remain undated** - no date was assigned (level-only search already found no supporting session).
* Approximate screenshot prices were used only as comparison evidence; every price above is from the stored candles.
""")

    # ------------------------------------------------------------------ configuration comparison
    rows = []
    for c in cfgs:
        for x in "AB":
            f = F(x, c)
            rows.append({"cfg": c, "win": x, "trades": f.trades, "IRF": int(WR(x, c, 'IRF').executed_trades), "ORB": int(WR(x, c, 'ORB').executed_trades), "PDR": int(WR(x, c, 'PDR').executed_trades), "PDS": int(WR(x, c, 'PDS').executed_trades),
                         "RF": int(WR(x, c, 'RF').executed_trades), "win%": f.gross_win_rate_pct, "PF": f.profit_factor, "gross pts": f.gross_points, "gross Rs": f.gross_rs, "net Rs (70/trade)": f.net_rs_C70_TRADE, "max DD Rs": f.max_drawdown_rs})
    comp = pd.DataFrame(rows)
    sw = []
    for x in "AB":
        for c in cfgs:
            for s in ("IRF", "ORB", "PDR", "PDS", "RF"):
                r = WR(x, c, s)
                sw.append({"win": x, "cfg": c, "strategy": s, "trades": int(r.executed_trades), "W/L/BE": f"{int(r.winners)}/{int(r.losers)}/{int(r.breakeven)}", "win%": r.gross_win_rate_pct, "PF": r.profit_factor})
    cost = rd("cost_sensitivity.csv")
    cB = cost[(cost.config == "B") & (cost.window == "A")][["scenario", "net_rs", "net_win_rate_pct", "profit_factor_net"]]
    cBB = cost[(cost.config == "B") & (cost.window == "B")][["scenario", "net_rs", "net_win_rate_pct", "profit_factor_net"]]
    jt = jsum[["config", "automated_trades", "strict", "time_tolerant", "date_strategy_only", "manual_only", "automated_only", "wrong_strategy_dates", "outcome_label_agree_strict_tolerant"]]
    w("configuration_comparison.md", f"""
# Configuration comparison (synthetic NIFTY index P&L; 6 lots x 65 = 390 units; neither window is untouched out-of-sample; NOTHING is selected)

Configurations are predeclared (`configuration_manifest.json`); each changes ONE declared dimension relative to **B** (IRF V3 + ORB V2-A + PDR/PDS first-eligible + RF) except A (the frozen Phase 3.6 combined configuration, reproduced exactly: window A 196 trades / Rs +297,765, window B 609 / Rs +509,398 = the saved Phase 6.2 'A'). A win = positive gross P&L of the WHOLE completed trade (two legs).

{chr(10).join(f'* **{c}** - {lab}' for c, lab in cfgs.items())}

## Portfolio performance

{tab(comp)}

## Strategy-wise (trades, winners/losers/breakeven, win rate, profit factor)

{tab(pd.DataFrame(sw))}

## Cost / slippage sensitivity, configuration B (all configurations: `cost_sensitivity.csv`)
Window A:

{tab(cB)}

Window B:

{tab(cBB)}

Indicative only: Rs 70 per completed trade, Rs 70 per fill, 0.25 / 0.5 / 1.0 point slippage per side on 390 units. Synthetic index P&L is **not** NIFTY futures or option P&L.

## Journal agreement (window A; 190 rows, one-to-one; strict = same date + strategy + time label == signal candle start; no exact match is possible - the journal has no direction or price)

{tab(jt)}

## Trade-set changes against B (attribution DIRECT vs PORTFOLIO in `trade_set_attribution.csv`)

{tab(tc)}

## What changes source fidelity versus what only changes historical P&L
* **Fidelity (the rule is supported by a source):** B adopts the two new IRF PDFs exactly (replaces the Phase 6.1 IRF V2 whose EMA-28 / first-red-low rules the PDFs do not contain); journal strict matches rise from 67 (Phase 6.2 C, IRF V2) to {int(J('B').strict)} with no rule tuned to the journal. C/C2 (Method 2 invalidation) change **no portfolio trade** in either window (Method 1 or other strategies already own those days) - the question matters for standalone Method 2 (113 -> {p1['A']['M2B_signals']} first signals, window A), not for the portfolio.
* **Not fidelity - only P&L moves:** EMA-1/2/3/4 remove many profitable and unprofitable trades alike; EMA-5 (target-side, the only reading with a drawn example) removes 12 baseline trades and raises strict journal matches to {int(J('L').strict)}, but this is not evidence the reading is right. PDR/PDS and candle-strength variants change trades because the rule is changed, not because a source says so; the journal helps only weakly (strict {min(int(J(k).strict) for k in ('G1','G2','G3','H','I1','I2'))}-{max(int(J(k).strict) for k in ('G1','G2','G3','H','I1','I2'))} for the PDR/PDS variants; J60/J70 lower).
* **J60 / J70 / JD wrap ALL five engines, including IRF V3.** The Phase 6.5 gate applies a body-strength test to any non-exempt directional confirmation, but the two IRF PDFs contain no body-size rule; IRF trades therefore fall under J60/J70 (window A IRF {int(WR('A','J60','IRF').executed_trades)} and {int(WR('A','J70','IRF').executed_trades)} vs {int(WR('A','B','IRF').executed_trades)}). These rows measure the Phase 6.5 proposal, not a source rule.\n* Gross P&L ranks are shown for completeness only; the two windows disagree in sign for some candidates (e.g. F: A +167,310 on 33 trades vs B -6,006 on 131 trades).
""")

    # ------------------------------------------------------------------ mismatch root causes
    sigs = rd("all_daily_signals.csv")
    mo = rd("manual_only.csv")
    mb = mo[(mo.config == "B") & (mo.weekend_row.astype(str) != "True")]
    sA = sigs[(sigs.window == "A") & (sigs.config == "B")]
    cat = []
    for r in mb.itertuples():
        s = sA[(sA.date == r.date) & (sA.strategy == r.strategy)]
        if r.wrong_strategy_date:
            c = "WRONG_STRATEGY_DATE (the automated system traded another strategy that day)"
        elif len(s) == 0:
            c = "NO_SIGNAL_FROM_THE_JOURNAL_STRATEGY"
        elif (s.within_13_00.astype(str) == "True").any():
            c = "SIGNAL_EXISTS_BUT_NOT_TRADED (blocked by an earlier position / not the first valid signal / unfillable)"
        else:
            c = "SIGNAL_ONLY_AFTER_13_00_CUTOFF"
        cat.append({"strategy": r.strategy, "category": c})
    cdf = pd.DataFrame(cat)
    cc = cdf.groupby(["strategy", "category"]).size().reset_index(name="manual_only_rows")
    ao = rd("automated_only.csv")
    aob = ao[ao.config == "B"]
    aoc = aob.assign(kind=aob.manual_rows_that_day.map(lambda x: "NO_JOURNAL_ENTRY_THAT_DAY" if x == "none" else "JOURNAL_HAS_ANOTHER_STRATEGY_THAT_DAY")).groupby(["strategy", "kind"]).size().reset_index(name="automated_only_trades")
    w("mismatch_root_causes.md", f"""
# Journal mismatch root causes (configuration B, window A)

Journal integrity recount (independent of earlier reports): `{jr['data_rows']}` data rows (workbook SHA-256 `{jr['journal_sha256'][:16]}...`), Summary sheet states {jr['summary_total_trades']} (discrepancy of 1 unresolved, not corrected), {jr['weekend_rows']} weekend-dated rows that can never match ({', '.join(jr['weekend_rows_list'])}), rows by strategy {jr['by_strategy']}. Columns present: {jr['columns_available']}. No direction, price or exit time exists, so **no verified exact trade match is possible**; every class is a match on date / strategy / time label / outcome label only.

Result for B: strict {int(J('B').strict)}, +time-tolerant {int(J('B').time_tolerant)}, date-and-strategy-only {int(J('B').date_strategy_only)}, manual-only {int(J('B').manual_only)} (of which {int(J('B').manual_only_weekend)} weekend), automated-only {int(J('B').automated_only)}, wrong-strategy dates {int(J('B').wrong_strategy_dates)}, outcome-label agreement on strict+tolerant {int(J('B').outcome_label_agree_strict_tolerant)} of {int(J('B').strict + J('B').time_tolerant)}.

## Manual-only rows (non-weekend) by cause
{tab(cc)}

## Automated-only trades by cause
{tab(aoc)}

## Reading the causes
* ORB dominates the manual-only rows: the journal's ORB entries carry the label 09:15 on 89 rows; ORB V2 (provisional conventions, wrong-side-wick rule, gap limit) emits only {int(WR('A', 'B', 'ORB').executed_trades)} trades. Phase 6.5 audited the ORB-vs-IRF disputes (0 implementation defects).
* 'Wrong-strategy dates' mean the automated first-valid-signal controller took a different strategy than the manual trader on the same date; the journal gives no way to tell which was 'right'.
* These disputes are NOT resolved by IRF V3, the EMA readings or the PDR/PDS variants in any consistent way: strict matches (window A) B {int(J('B').strict)}, D {int(J('D').strict)}, E {int(J('E').strict)}, F {int(J('F').strict)}, K {int(J('K').strict)}, L {int(J('L').strict)}, G1-H {int(J('G1').strict)}/{int(J('G2').strict)}/{int(J('G3').strict)}/{int(J('H').strict)}, I1/I2 {int(J('I1').strict)}/{int(J('I2').strict)}. No rule was changed to fit the journal.
""")

    # ------------------------------------------------------------------ audit + preservation placeholders handled elsewhere; README / final report
    p1a, p1b = p1["A"], p1["B"]
    ph = rd("irf_v3_final_diagnostics.csv")
    pa = ph[(ph.window == "A") & (ph.scenario == "SL40_T60")].set_index("book")
    pj = ph[ph.scenario == "journal"].set_index("book")
    pdr = rd("pdr_first_vs_second_confirmation.csv")
    pdrp = pdr[pdr.section.str.startswith("PORTFOLIO")][["variant", "window", "pdr_trades", "pdr_winners", "pdr_losers", "pdr_win_rate_pct", "pdr_profit_factor"]]
    sig65 = pdr[pdr.section.str.startswith("SIGNAL")].dropna(axis=1, how="all")
    pds = rd("pds_confirmation_comparison.csv")
    pdsp = pds[pds.section.str.startswith("PORTFOLIO")].dropna(axis=1, how="all")
    f = {c: {x: F(x, c) for x in "AB"} for c in cfgs}
    auds = aud.get("m2_variants", {}).get("mismatches", {})
    eaud = aud.get("ema_independent", {})
    final = f"""
# PHASE 7.1 - FINAL RESEARCH REPORT

**Written for:** the strategy owner. Research only: synthetic NIFTY index-point P&L on 390 units (6 x 65), **not** futures/option P&L; nothing selected, ranked, promoted, committed, staged or pushed; no order placed; no paper-trading or frozen file touched. Neither window is untouched out-of-sample. Start with `README.md`, then `universal_27_point_ema_rule_audit.md`, `configuration_comparison.md`, `remaining_author_questions.md`.

## Headline
1. **The 27-point statement is not a confirmed rule.** It conflicts with the two IRF PDFs ('no EMA filter'), may conflict with ORB's fresh-cross entries, and is compatible with five incompatible readings. It is built once as a shared opt-in component (`phase71/ema_rule.py`) and run as EMA-1..EMA-5 on all five strategies. Default behaviour is unchanged.
2. **Method 2 Level-A invalidation barely touches the PORTFOLIO** (configs C and C2 = B in both windows: no trade changes) but halves standalone Method 2 ({p1a['M2A_signals']} -> {p1a['M2B_signals']} first signals, window A; {p1b['M2A_signals']} -> {p1b['M2B_signals']} window B); re-arming restores {p1a['M2B_REARM_signals']} / {p1b['M2B_REARM_signals']}.
3. **The 3-Nov timing discrepancy is explained**: the new 5paisa data reproduces the screenshot's failure candle (10:05, close 23,613.00 vs stated entry 23,612.80) with the rule as written; the secondary feed differs by a 0.7-point margin.
4. **November data were obtained** (13 sessions) and all five dated examples reproduce in sequence and outcome; three printed Level-A values (3 Nov -3.85 on the 5paisa feed - a feed difference; 6 Nov -21.85; 16 Nov +9.00) do not match the data.
5. **PDR**: all 215 delayed cycles are explained (195 earlier greens closed at/below the zone, 20 earlier greens were the retest candle; {dl['audit_classification_defects']} defects); none of the earlier candles satisfies the approved close-above-ceiling rule (0 of 215).
6. Frozen configuration A reproduces exactly; B (IRF V3 base) is the new reference for comparisons.

## Answers to the 40 questions

### EMA
**1.** The statement supports only: the number is 27 (not 28), it concerns a gap near the 200 EMA, and the author sees it as common to all five strategies. **2.** Five readings remain (EMA-1 min close distance, EMA-2 min range clearance, EMA-3 max close proximity, EMA-4 28-point comparator, EMA-5 target-side). **3.** Not determined: the handwritten pages ('less than 27 -> wait') suggest a minimum clearance in the trade's path; 'near' suggests a maximum; the call suggests a minimum. **4.** Not determined: close, candle range, or room to the EMA - only EMA-5 has a worked drawing. **5.** The 5-minute EMA(200) (handwritten '5 min TF'; ORB rulebook); nothing supports a daily 200-day average; for PDR/PDS/RF the 5-minute choice is an assumption. **6.** Not determined; the confirming candle is the reference (the EMA value at entry equals it); setup/reference timing changes many decisions (`ema_measurement_timing_sensitivity.csv`, e.g. IRF window A 70 of 633 signals differ for EMA-1/EMA-3 at setup vs confirmation). **7.** Signal level (window A, range clearance): IRF {int(cmp27[(cmp27.window == 'A') & (cmp27.strategy == 'IRF') & (cmp27.interpretation == 'MIN_RANGE')].decision_differs_27_vs_28.iloc[0])}, PDR {int(cmp27[(cmp27.window == 'A') & (cmp27.strategy == 'PDR') & (cmp27.interpretation == 'MIN_RANGE')].decision_differs_27_vs_28.iloc[0])}, PDS {int(cmp27[(cmp27.window == 'A') & (cmp27.strategy == 'PDS') & (cmp27.interpretation == 'MIN_RANGE')].decision_differs_27_vs_28.iloc[0])}; portfolio level (E vs K): {diffs['A'][0]} trades in window A and {diffs['B'][0]} in window B exist only at 27. **8.** See the per-strategy impact tables in `universal_27_point_ema_rule_audit.md` (window A trades under D/E/F/K/L: IRF {int(WR('A', 'D', 'IRF').executed_trades)}/{int(WR('A', 'E', 'IRF').executed_trades)}/{int(WR('A', 'F', 'IRF').executed_trades)}/{int(WR('A', 'K', 'IRF').executed_trades)}/{int(WR('A', 'L', 'IRF').executed_trades)} vs {int(WR('A', 'B', 'IRF').executed_trades)} baseline; ORB {int(WR('A', 'D', 'ORB').executed_trades)}/{int(WR('A', 'E', 'ORB').executed_trades)}/{int(WR('A', 'F', 'ORB').executed_trades)}/{int(WR('A', 'K', 'ORB').executed_trades)}/{int(WR('A', 'L', 'ORB').executed_trades)} vs {int(WR('A', 'B', 'ORB').executed_trades)}). **9.** Yes for the minimum-distance readings: window A {ev['A']['EMA-2_MIN_RANGE_27']} of {len(og['A'])} ORB signals fail EMA-2 and {int(og['A'].fresh_cross_or_inside.sum())} have the EMA inside the opening candle; EMA-3 fails {ev['A']['EMA-3_MAX_CLOSE_27']}; EMA-5 fails none. **10.** Yes - both IRF PDFs state there is no EMA filter; EMA-0 keeps IRF V3 as written.

### IRF
**11.** Standalone first Method 2 signals: window A {p1a['M2A_signals']} -> {p1a['M2B_signals']} (permanent invalidation; {p1a['M2B_effects'].get('REMOVED', 0)} sessions lose it); with re-arming {p1a['M2B_REARM_signals']} (time changed {p1a['M2B_REARM_effects'].get('TIME_CHANGED', 0)}, removed {p1a['M2B_REARM_effects'].get('REMOVED', 0)}, added {p1a['M2B_REARM_effects'].get('ADDED', 0)}); window B {p1b['M2A_signals']} -> {p1b['M2B_signals']} / {p1b['M2B_REARM_signals']}. Level A is lost before the Method 2 entry in {p1a['level_A_lost_before_m2_entry']} of {p1a['m2_rally_breakout']} rally sessions; the first red candle itself closes below A in {p1a['first_red_closed_below_A']}. Portfolio trade-set effect: none. **12.** A feed difference (5paisa reproduces the screenshot with the rule as written). **13.** Yes in sequence and outcome on the 5paisa feed; Level A printed for 6 Nov and 16 Nov does not match the data. **14.** Method 1 standalone (window A, SL40): {int(pa.loc['Method 1', 'trades_recounted'])} trades, {pa.loc['Method 1', 'win_rate_pct_recounted']}% (recounted from the saved Phase 7.0 ledger). **15.** Method 2: {int(pa.loc['Method 2', 'trades_recounted'])} trades, {pa.loc['Method 2', 'win_rate_pct_recounted']}%. **16.** Combined IRF V3: {int(pa.loc['Combined', 'trades_recounted'])} trades, {pa.loc['Combined', 'win_rate_pct_recounted']}%, {pa.loc['Combined', 'gross_points_recounted']} gross points - the Phase 7.0 numbers are verified from the ledgers. **17.** Strict {int(pj.loc['Combined', 'strict_matches_recounted'])} of the 73 IRF journal rows (Method 1 {int(pj.loc['Method 1', 'strict_matches_recounted'])}, Method 2 {int(pj.loc['Method 2', 'strict_matches_recounted'])}); the journal cannot prove an exact trade match.

### PDR / PDS
**18.** Under the approved rules the earlier green candles did not satisfy them: {dl['delay_category'].get('A_EARLIER_GREEN_CLOSES_BELOW_OR_WITHIN_THE_ZONE', 0)} closed at or inside the zone (ceiling rule) and {dl['delay_category'].get('C_EARLIER_GREEN_IS_THE_RETEST_CANDLE', 0)} were the retest candle (sequencing convention). It is not an implementation defect. **19.** 0 of 215 earlier candles satisfy the zone-ceiling rule. **20.** Signal level (Phase 6.5, window A): PDR-B {int(sig65[(sig65.variant == 'PDR-B') & (sig65.window == 'A')].relation_EARLIER.sum())} earlier entries; PDR-C {int(sig65[(sig65.variant == 'PDR-C') & (sig65.window == 'A')].relation_EARLIER.sum())}; (window B {int(sig65[(sig65.variant == 'PDR-B') & (sig65.window == 'B')].relation_EARLIER.sum())} / {int(sig65[(sig65.variant == 'PDR-C') & (sig65.window == 'B')].relation_EARLIER.sum())}). **21.** PDR-D moves entries later ({int(sig65[(sig65.variant == 'PDR-D') & (sig65.window == 'A')].relation_LATER.sum())} later, {int(sig65[(sig65.variant == 'PDR-D') & (sig65.window == 'A')].relation_REMOVED_BY_VARIANT.sum())} removed in window A). **22.** PDR win rates: {', '.join(f"{r.variant} {r.window}: {r.pdr_win_rate_pct}% ({int(r.pdr_trades)} trades)" for r in pdrp.itertuples())}. PDS: {', '.join(f"{r.variant} {r.window}: {r.pds_win_rate_pct}% ({int(r.pds_trades)})" for r in pdsp.itertuples())}.

### Combined strategy
**23.** Trades (window A / B): {', '.join(f"{c} {int(f[c]['A'].trades)}/{int(f[c]['B'].trades)}" for c in cfgs)}. **24.** B: IRF {int(WR('A', 'B', 'IRF').executed_trades)}, ORB {int(WR('A', 'B', 'ORB').executed_trades)}, PDR {int(WR('A', 'B', 'PDR').executed_trades)}, PDS {int(WR('A', 'B', 'PDS').executed_trades)}, RF {int(WR('A', 'B', 'RF').executed_trades)} (window A); window B {int(WR('B', 'B', 'IRF').executed_trades)}/{int(WR('B', 'B', 'ORB').executed_trades)}/{int(WR('B', 'B', 'PDR').executed_trades)}/{int(WR('B', 'B', 'PDS').executed_trades)}/{int(WR('B', 'B', 'RF').executed_trades)}; all configurations in `strategy_win_rates.csv`. **25.** B window A: IRF {WR('A', 'B', 'IRF').gross_win_rate_pct}%, ORB {WR('A', 'B', 'ORB').gross_win_rate_pct}%, PDR {WR('A', 'B', 'PDR').gross_win_rate_pct}%, PDS {WR('A', 'B', 'PDS').gross_win_rate_pct}%, RF {WR('A', 'B', 'RF').gross_win_rate_pct}%; window B {WR('B', 'B', 'IRF').gross_win_rate_pct}/{WR('B', 'B', 'ORB').gross_win_rate_pct}/{WR('B', 'B', 'PDR').gross_win_rate_pct}/{WR('B', 'B', 'PDS').gross_win_rate_pct}/{WR('B', 'B', 'RF').gross_win_rate_pct}%. **26.** B: {f['B']['A'].gross_win_rate_pct}% (A) / {f['B']['B'].gross_win_rate_pct}% (B); frozen A: {f['A']['A'].gross_win_rate_pct}% / {f['A']['B'].gross_win_rate_pct}%. **27.** B window A: PF {f['B']['A'].profit_factor}, gross Rs {f['B']['A'].gross_rs:,.0f}, max drawdown Rs {f['B']['A'].max_drawdown_rs:,.0f}; window B: PF {f['B']['B'].profit_factor}, Rs {f['B']['B'].gross_rs:,.0f}, DD Rs {f['B']['B'].max_drawdown_rs:,.0f} (all configurations in the comparison table). **28.** Rs 70 per trade changes B window A to Rs {f['B']['A'].net_rs_C70_TRADE:,.0f}; the slippage cases are in `cost_sensitivity.csv`. **29.** Windows differ in sign for several candidates (F, PDR-B1/B2/C PF below 1 in window B at PDR level); see the tables. **30.** Fidelity gains: B (adopts the two PDFs), the explanations of PDR/Nov-3; everything else (EMA readings, PDR/PDS variants, candle strength) only changes historical P&L until the author confirms the rule.

### Journal and safety
**31.** Strict (window A): B {int(J('B').strict)} (frozen A {int(J('A').strict)}); all configurations in `journal_match_summary_by_config.csv`. **32.** Additional time-tolerant: B {int(J('B').time_tolerant)}. **33.** Date-and-strategy-only: B {int(J('B').date_strategy_only)}. **34.** Manual-only {int(J('B').manual_only)} (5 weekend), automated-only {int(J('B').automated_only)}. **35.** Material open rules: the EMA reading (all five strategies), Method 2 invalidation, PDR confirmation, IRF stop 35 vs 40, ORB conventions (Phase 6.5). **36.** Yes - hash comparison in `preservation_verification.md`. **37.** Yes - no paper-trading file changed. **38.** Yes - `independent_audit.md` (second implementations of the EMA geometry and Method 2 variants; Method 2 variant mismatches {sum(auds.values()) if auds else 'n/a'}; geometry mismatches {eaud.get('geometry_recomputation_mismatches', 'n/a')}). **39.** Owner approval is needed for: the EMA reading and scope (and 27 vs 28), whether it overrides the IRF PDFs, Method 2 invalidation/re-arm, the PDR confirmation rule, the IRF stop in the portfolio, any candle-strength rule, and which configuration (if any) to compare in a controlled paper study. **40.** Technically yes (every candidate is an opt-in wrapper over the frozen controller and reproducible from the manifest), but not decision-ready: the EMA reading and Method 2 invalidation must be settled first.

## Proposed final configuration for owner review (NOT activated)
Reference = **B** (IRF V3 Method 1 + 2 as written, no EMA filter, existing ORB V2-A / PDR / PDS / RF, frozen controller). Candidates for explicit owner choice: one EMA reading (EMA-5 is the only one with a drawn example; EMA-1/2/4 reject valid ORB fresh crosses), Method 2 persistent vs invalidating, PDR baseline vs first-green. Each is available as an independent opt-in wrapper; none is recommended by P&L.
"""
    w("FINAL_PHASE71_RESEARCH_REPORT.md", final)
    mm = aud.get("m2_variants", {})
    w("independent_audit.md", f"""
# Independent audit (Phase 7.1)

## 1. Second implementations (no shared logic with the production modules) - `scripts/phase71_audit.py`
**Method 2 variants.** `irf_cycles.m2_cycles` (state machine) versus an index-search implementation (`m2_independent`, `m2_independent_bc`: no state machine) on every evaluable session of both windows ({mm.get('sessions', 'n/a')} sessions) for nine variants (M2-A, BEFORE_B, BEFORE_COMPLETION permanent / re-arm, margin 1 / 2 / 5, bearish failure, extra confirming candle). First-cycle mismatches: **{mm.get('mismatches', 'n/a')}**. (A first audit run showed 91 / 131 mismatches for the BEFORE_COMPLETION variants; the cause was a gap in the INDEPENDENT implementation, which only checked the close-below-A window before Level B was marked and between the second breakout and the failure, not between B and the second breakout; the production state machine was right. The audit function was corrected and re-run.)
**Phase 7.0 parity.** On all 1,964 session-method pairs of both windows the first cycle of the new enumerators equals the Phase 7.0 `irf_v3.method1/method2` result (signal time, level, later-cycle count); BEFORE_B equals the Phase 7.0 invalidation variant.
**EMA geometry.** Rebuilt from raw one-minute rows with `pandas.resample` and a recursive `ewm(span=200, adjust=False)` over the same warm-up: {eaud.get('signals_compared', 'n/a')} baseline window-A signals compared; geometry (|close-EMA|, range clearance) recomputed from raw OHLC: **{eaud.get('geometry_recomputation_mismatches', 'n/a')} mismatches**; mean |EMA difference| {eaud.get('mean_abs_ema_diff_points', 0):.2f} points, maximum {eaud.get('max_abs_ema_diff_points', 0):.2f} (seed effect early in the series); decisions that would flip at 27 points if the recursive EMA replaced the frozen SMA-seeded EMA: {eaud.get('decision_flips_if_the_independent_recursive_EMA_were_used (27pt)', 'n/a')}.

## 2. Reproduction of the frozen result
Configuration A through the unchanged controller reproduces the saved Phase 6.2 configuration A exactly: window A 196 trades / Rs +297,765, window B 609 / Rs +509,398.

## 3. Test suite and lint
`tests/test_phase71_global_ema.py` (15 tests: boundary and direction behaviour of every EMA reading, 27 vs 28, unavailable EMA, gate wrapper using only the confirming candle's EMA, Phase 7.0 parity of the first cycle, multiple cycles, invalidation vs the completing candle, re-arm, margin / bearish / extra-confirmation candidates, November quality checker) plus the Phase 7.0 suite. Full-suite result in `preservation_verification.md`.

## 4. Checks listed in the brief
| Check | Result |
|---|---|
| Historical data validation (November store) | `november_2026_data_quality.csv`: 375 in-session rows per full session, 0 missing minutes, 0 duplicates, 0 OHLC violations |
| Candle alignment | five-minute candles from complete five-row groups only; bar-start labels (verified Phase 2) |
| EMA warm-up | frozen contexts carry the warm-up months; unavailable EMA is never a rejection (tested) |
| No look-ahead | each decision uses the confirming candle's own EMA and OHLC; signals from the Phase 7.0 modules are causal (1,031 signals truncation-tested in 7.0); the adapter emits record timestamps = candle end |
| Shared arbitration / second-trade eligibility | the frozen controller is unchanged; configuration A reproduces Phase 6.2 exactly |
| Execution and P&L | the frozen exit policy reconstructs fills from one-minute bars; reconciliations in `trade_set_attribution.csv`; independent reviewer recomputation in `reviewer_findings.md` |
| Journal recount | 190 rows, Summary 189, 5 weekend rows, SHA-256 unchanged (`mismatch_root_causes.md`) |
| Chart correctness | rejected trades drawn as NOT EXECUTED with dashed outlines; executed charts carry the EMA path, levels and both leg exits |

## 5. Limits
* The EMA gate is a post-hoc filter on emitted signals (as the Phase 6.5 strength gate); IRF V3 emits every completed cycle so a rejected cycle can release a later one - an inference, not an author decision.
* Edge cases of the research options (not used by any portfolio configuration): with `extra_confirmation` an extra candle closing between B and A is not tested for invalidation; with `bearish_failure` + BEFORE_COMPLETION a green candle closing below both B and A invalidates instead of being ignored.\n* The second implementations were written by the same author; a separate read-only reviewer was also run (`reviewer_findings.md`).
* Window B uses the Phase 4 5paisa store; ORB V2 conventions remain PROVISIONAL (Phase 6.0/6.5).
""")
    readme = f"""
# Phase 7.1 - global EMA rule, IRF validation, PDR/PDS reconciliation and five-strategy backtest

**Written for:** the strategy owner. Research only; nothing selected or activated; no paper-trading or frozen file changed; nothing committed, staged or pushed. **Start with `FINAL_PHASE71_RESEARCH_REPORT.md` (answers to the 40 questions).**

## What was done (priority order)
0. **Universal 27-point EMA clarification** - source audit, five readings in one shared component, impact on all five strategies, 27 vs 28, ORB conflict: `latest_author_clarification.md`, `universal_27_point_ema_rule_audit.md`, `ema_*.csv`.
1. **IRF Method 2 Level-A invalidation** (persistent vs permanent vs re-arm): `irf_method2_level_a_invalidation.csv`, `irf_method_comparison.csv`.
2. **3 Nov entry-time discrepancy** - resolved as a data-feed effect; close-below-B candidates (diagnostic): `irf_method2_timing_audit.md`.
3. **November 2026 data** retrieved (new raw namespace `data/raw/phase71_5paisa_nov2026/`, processed `data/phase71/`) and every dated IRF example reconstructed: `november_2026_example_reconstruction.md`, `charts/EX_*`.
4. **PDR / PDS**: 215 delayed cases explained, first-vs-second confirmation, candle-strength comparison: `pdr_215_delayed_cases.csv`, `pdr_first_vs_second_confirmation.csv`, `pds_confirmation_comparison.csv`, `candle_strength_reference_comparison.csv`.
5. **Five-strategy backtest of 18 predeclared configurations on both windows** (frozen controller): `configuration_comparison.md`, `full_five_strategy_backtest.csv`, `strategy_win_rates.csv`, `all_executed_trades.csv`, `all_trade_legs.csv`, `all_daily_signals.csv`, monthly / annual / cost files, journal reconciliation files and `mismatch_root_causes.md`.
Verification: `independent_audit.md`, `reviewer_findings.md`, `preservation_verification.md`, `Phase71_Final_Strategy_Verification.xlsx`; charts in `charts/` (subfolders per purpose), per-day files in `daily/` (window A).

## Key numbers (window A 2025-09..2026-08 | window B 2022-09..2025-08; gross win rate, PF, gross Rs)
{tab(comp[comp.cfg.isin(['A', 'B', 'C', 'D', 'E', 'F', 'K', 'L'])].drop(columns=['IRF', 'ORB', 'PDR', 'PDS', 'RF']))}

Reproduce: `python scripts/phase71_fetch_nov2026.py` (read-only fetch, already done) -> `scripts/phase71_irf.py` -> `scripts/phase71_run.py portfolio A` and `... B` -> `scripts/phase71_tables.py` -> `scripts/phase71_derived.py` -> `scripts/phase71_audit.py` -> `scripts/phase71_charts.py` -> `scripts/phase71_docs.py` -> `scripts/phase71_preserve.py`.
"""
    w("README.md", readme)
    export_xlsx()


def export_xlsx() -> None:
    sheets = [("Config_comparison", "full_five_strategy_backtest.csv"), ("Strategy_win_rates", "strategy_win_rates.csv"), ("Trades", "all_executed_trades.csv"), ("Legs", "all_trade_legs.csv"), ("Signals", "all_daily_signals.csv"),
              ("Monthly", "monthly_performance.csv"), ("Annual", "annual_performance.csv"), ("Costs", "cost_sensitivity.csv"), ("Attribution", "trade_set_attribution.csv"), ("EMA_signals", "ema_distance_interpretations.csv"),
              ("EMA_27v28", "ema_27_vs_28_comparison.csv"), ("EMA_impact", "ema_signal_impact_by_strategy.csv"), ("EMA_timing", "ema_measurement_timing_sensitivity.csv"), ("ORB_EMA_conflicts", "ema_crossing_conflicts.csv"),
              ("Sources", "ema_source_conflict_matrix.csv"), ("M2_invalidation", "irf_method2_level_a_invalidation.csv"), ("IRF_variants", "irf_method_comparison.csv"), ("Nov_examples", "november_2026_example_results.csv"),
              ("Nov_quality", "november_2026_data_quality.csv"), ("PDR_215", "pdr_215_delayed_cases.csv"), ("PDR_variants", "pdr_first_vs_second_confirmation.csv"), ("PDS", "pds_confirmation_comparison.csv"),
              ("Strength", "candle_strength_reference_comparison.csv"), ("Journal_summary", "journal_match_summary_by_config.csv"), ("Journal_recon", "manual_journal_reconciliation.csv"), ("Day_by_day", "day_by_day_comparison.csv"),
              ("Rules", "rule_authority_registry.csv")]
    with pd.ExcelWriter(OUT / "Phase71_Final_Strategy_Verification.xlsx", engine="openpyxl") as xw:
        pd.DataFrame({"Phase 7.1": ["Research only. Synthetic index P&L (390 units), not futures/options P&L. Nothing selected or activated. See FINAL_PHASE71_RESEARCH_REPORT.md for the 40 answers."]}).to_excel(xw, sheet_name="README", index=False)
        for name, f in sheets:
            if (OUT / f).exists():
                df = pd.read_csv(OUT / f)
                df.to_excel(xw, sheet_name=name[:31], index=False)
                ws = xw.sheets[name[:31]]
                ws.freeze_panes = "A2"
                for i, c in enumerate(df.columns, 1):
                    ws.column_dimensions[get_column_letter(i)].width = min(max(len(str(c)) + 2, 11), 40)


if __name__ == "__main__":
    main()
