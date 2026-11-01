# Source document inventory

Authority for every original strategy rule is the set of documents below. Documents were identified **by content**, not by filename.
`docs/extracted_text/*.txt` already existed in the repository (produced by an earlier extraction); they were **not used** as evidence — every
PDF/DOCX was re-extracted from the original file during Phase 2.

## Identification by content

| # | Expected document | File found | Identified by (content) | Pages | Embedded images |
|---|---|---|---|---|---|
| 1 | IRF Strategy Guide | `docs/strategy_docs/IRF_Strategy_Guide Updated.pdf` | p.1 "IRF Strategy — Initial Range Failure / Inverse Retest Failure", three entry methods, short-only, ₹60 target | 17 | 12 |
| 2 | ORB Strategy Rulebook | `docs/strategy_docs/ORB_Strategy_Rulebook-2.pdf` | no title line in the text; p.2 "The Opening Range Breakout (ORB) is an intraday method…"; p.1 "Complete Rulebook — Setups, Candle Filters, Trade Parameters & Pre-Trade Checklist" | 13 | 16 |
| 3 | PDR Strategy Guide | `docs/strategy_docs/PDR_Strategy_Guide.pdf` | p.1 "PDR STRATEGY — Previous Day Resistance – Gap-Up Support Retest" | 4 | 5 |
| 4 | PDS Strategy Guide | `docs/strategy_docs/PDS strategy.pdf` | p.1 "PDS — Previous Day Support — a rule-based short-selling playbook for the gap-down session" | 7 | 7 |
| 5 | RF Strategy Guide | `docs/strategy_docs/RF strategy.pdf` | p.1 "RF Strategy — Reverse Failure – Rules & Setup" | 9 | 9 |
| 6 | System performance report | `docs/trading journal/NIFTY_System_Trading_Strategy_Performance.docx` (**a DOCX, not a PDF**) | "System Trading Strategy Performance — … NIFTY intraday execution strategy … 189 logged trades" | no fixed pagination | 3 (charts) |
| — | *(not in the expected list)* | `docs/trading journal/Trading_Journal_Sep2025_Aug2026 REPORT.xlsx` | sheet "Trading Journal": Sl No., Date, Entry Time, Strategy, Outcome; sheet "Summary" | 2 sheets | — |

All six expected documents are present. The performance report was located in `docs/trading journal/`, not `docs/strategy_docs/`.

## What was read

| Document | Text of every page extracted and read | Rendered pages looked at (visually) | Notes |
|---|---|---|---|
| IRF | all 17 pages | pp. 5, 8, 11, 14, 15, 16, 17 | Reference Charts 1–6 (pp.15–17) carry empty "Notes:" fields. Chart 4's position box reads Stop 35.05 and Target 61.35 (target label partly cropped); Chart 6 reads Stop 35.00 and Target 60.00. These are drawing-tool annotations, not rules. |
| ORB | all 13 pages | pp. 7, 10, 12, 13 | Section numbers jump 2 → 4 (no section 3). "▶ Animation" captions are static placeholders (the animations are not in the PDF). |
| PDR | all 4 pages | pp. 3, 4 (+ zoomed chart legends) | Chart legends read `NIFTY50-INDEX · 5 · NSE` and `EMA 200 close` — see *200 EMA vs 200 DMA* below. |
| PDS | all 7 pages | pp. 4, 7 | pp. 5–6 contain the author's own list of open items. |
| RF | all 9 pages | pp. 4, 6, 9 (+ zoomed annotation) | p.8 contains the author's "Rule readiness" table (Entry price OPEN, Target OPEN). |
| Performance report | all paragraphs, all 11 tables (in document order), headers/footers | — | Figure 1 caption: *"Reproduced from the supplied photograph; individual trade-level values were not provided."* The 3 embedded images are charts of aggregates. |
| Journal xlsx | all rows (190) + Summary sheet | — | See *Journal reliability*. |

Pages with purely schematic/animation figures that I read as text but did **not** inspect visually: IRF pp.1, 4, 9; ORB pp.1–6, 8, 9, 11; PDS pp.1–3, 5–6; RF pp.1–3, 5, 7. The independent reviewer's coverage of these pages is
recorded in `agent_review_report.md`. No rule was taken from a figure alone; where a figure carries a number (e.g. TradingView position boxes) it is cited as an *annotation*, not as a rule.

## Evidence found only in rendered pages (not in extracted text)

| Where | Evidence | Used for |
|---|---|---|
| PDR p.3 Example 1; p.4 Example 3 | TradingView legend `NIFTY50-INDEX · 5 · NSE` / `EMA 200 close 0 24,582.02` / `…MA 200 close 0 24,925.18` | The plotted 200-period line on these **5-minute** charts is an EMA of closes. Strongest single piece of evidence on the 200 EMA/DMA question. |
| PDR p.4 Example 3, Example 5 | position boxes "Target: 69.90", "Stop: 40.60"; "Target: 70.40", "Stop: 35.00" | PDR target ≈ 70, stop 35/40 (annotations, consistent with the text). |
| PDS p.7 | "Stop: 35.50", "Target: 70.10" | PDS target ≈ 70. |
| RF p.9 | long-position box: "Target: 60.80 … Stop: 40.65 … Closed P&L −40.65" (stopped out) | Evidence the RF reference chart is a **long** trade with a ≈60-point target box. **An example annotation, not a rule** (RF p.8 says Target is OPEN). |
| IRF pp.16–17 | "Stop: 35.05", "Stop: 35.00", "Target: 60.00" | IRF stop 35, target 60. |
| ORB pp.12–13 | gap examples in which price jumps through a smooth curved line; the only moving-average-like line drawn on these charts | The line the text calls "200 DMA" (p.8–9, 12) appears as a curved line at 5-minute scale. The charts carry no legend naming it, so this is circumstantial evidence only (see `ambiguous_rules.md` AMB-ORB-01). |
| IRF p.14 (image + text) | "Method 1 trigger: The next candle **or following candle** closes back inside the range"; "Method 3 … Or an Higher price rejection candle also works" | Two items that conflict with / are undefined elsewhere in the same guide (rules IRF-M1-C001, IRF-M3-C001). |

## Journal reliability (descriptive; nothing was tuned to it)

The journal has **190** rows but its own Summary sheet says **189**; strategy attribution differs from the report (IRF 73 vs 72, ORB 89 vs 88,
PDR 8 vs 9); August 2026 has 19 rows vs 18 in the report; **5 rows are dated on Saturdays** (2025-10-11, 2026-02-14, 2026-08-15, -08-22, -08-29) on which the
dataset has no session; 185 distinct trade dates vs "180 trading days"; one date is out of order. It records no direction, method, entry/exit price, stop distance or Target-2 distance.
It is therefore **not** a usable trade list for validating signals until the author reconciles it. Details: `reports/phase2/performance_report_verification.md`.

## Earlier attempt

A previous pass in this repository had already created `src/nifty_trading/strategies/`, `core/exit_policy.py`, `docs/phase2/*` and four failing tests
(its `resample_1m_to_5m` used right-closed bins and mis-binned start-labelled bars; it defaulted `rf_target_status="RESOLVED"` and labelled proposals as verified).
Those files were **not trusted**: they were backed up outside the repository and replaced by this implementation. Phase 1 files were not modified.

## Dataset caveat that affects every document's rules
The Phase 1 NIFTY 1-minute data contains a **frozen-feed tail on 21 sessions (2026-08-03 … 2026-08-31)** that Phase 1's audit did not catch and the first pass of this phase also missed; the independent review found it.
Details, handling and the required re-download are in `reports/phase2/dataset_verification.md` (`feed_quality`) and `agent_review_report.md` (C-1). Phase 1's calendar also lists four dates as holidays that have full sessions (2026-02-17, 03-20, 03-27, 05-27) and its instrument metadata contains a leaked `MagicMock` string; Phase 1 files were **not** modified.
