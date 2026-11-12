# Phase 5.9 independent audit

Completed 8 November 2026. This verifies the author-review package technically. It does not confirm an author's intended trade, approve an implementation, or establish that every ORB journal label should become an automated trade.

## Reproduced baseline and overlap

The original workbook was opened read-only and its literal rows recounted before accepting Phase 5.8. Its source-row numbers, date values, time labels and strategy classifications are preserved in `journal_recount_rows.csv` and the workbook's OriginalJournal sheet. Excel time objects in the original final rows are represented by their string values; no execution timestamp is inferred from a journal label.

| Evidence | Independently reproduced |
|---|---:|
| Original journal data rows | 190 |
| ORB-labelled rows | 89 |
| Unique ORB-labelled dates | 89 |
| Evaluable ORB-journal dates | 85 |
| ORB signal dates / executed ORB dates | 35 / 35 |
| Evaluable dates with no ORB signal | 50 |
| ORB-journal dates executing IRF | 34 |
| Handwritten disputed ORB observations | 13 |
| Handwritten overlap with the 50 | 11 |
| Unique author-review cases | 52 |

Four literal Saturday labels have no session: 2025-10-11, 2026-08-15, 2026-08-22 and 2026-08-29. They remain in the original recount. The handwritten-only dates are 2025-10-17 (no journal row) and 2025-11-21 (journal strategy IRF).

The 34 IRF dates are a subset of the 50 missing-signal dates. Within those 50, five dates have another strategy and 12 have no trade; these categories overlap because 2025-11-07 executes IRF and later PDS. No earlier confirmed frozen ORB was bypassed. The union workbook has 52 rows, not 63.

## Candle, indicator and rejection checks

`scripts/phase59_run.py` rebuilds session contexts using the existing quality/calendar policy, warmup and official daily closes. It evaluates the frozen configuration A ORB on all available evaluable sessions without simulating new trades. Independent predicate reconstruction describes both directions for Method 1, Method 2 and the gap setup; its eligibility agrees with the current engine. All six paths fail on every one of the 52 review cases. `gate_evidence.csv` retains every failed predicate, including later conditions that code short-circuiting would otherwise hide, together with observations, source page and authority classification. Original source PDFs and the correction PDF were visually reviewed; qualitative source wording is distinguished from numerical/construction proposals.

The separate final verifier, `scripts/phase59_verify.py`, imports neither chart-generation functions nor strategy engines. It reads source Parquet files and uses a separate pandas resampling calculation and explicit EMA recurrence:

- 46,852 stored minute/five-minute/context candle comparisons passed with OHLC tolerance 1e-7.
- 27,300 EMA samples matched the independently calculated alpha 2/201 recurrence, with an SMA seed of the first 200 complete five-minute closes. The history begins 2025-07-01. No future close contributes to an earlier sample.
- Only complete five-minute buckets are used. One incomplete warmup bucket is excluded; a non-standard-start special session is excluded from the normal-session EMA sequence. The 15:30 print is retained in raw evidence but is not an extra five-minute trading candle.
- Opening-range lines begin at 09:20. Five-minute EMA samples are drawn at completion; the one-minute detail uses only EMA samples already completed at that minute. Inner pivots and trendline anchors come from prior-session candles with their confirmation requirements met.
- Original first-candle OHLC, body/wicks, previous-session extrema, official prior close and directional gap calculations were verified. Source-drawn zones, exact author entries and author trendline anchors remain unknown.

The separate fresh reviewer independently reproduced these candle/EMA comparisons. Its source review and qualifications are in `fresh_reviewer_findings.md`.

## Chart and execution-ledger verification

All 62 canonical SVGs and their 3400 × 2125 PNGs were checked. There are 52 overview charts plus five opening-minute and five five-session-context charts. Subset directories contain copies of the corresponding canonical charts, verified by hash.

The verifier parses actual SVG primitives, rather than trusting metadata alone. It compares all 7,016 drawn candles to raw/reaggregated OHLC and checks wick/body coordinates against the declared scale. It checks rendered reference-line positions, all 132 rendered trade markers and their ledger prices, and all 41 case-level executed trade displays against configuration A's original ledger. Entry prices also match the raw minute open. Initial stops, T1/T2 and both exit times/prices are preserved. The fresh reviewer additionally checked all 214 displayed trend-anchor circles against their source candles and geometry.

All 52 cases have no confirmed current ORB signal. Every author entry object contains null time, price and direction. Every chart has **AUTHOR ORB ENTRY — TO BE MARKED** in an annotation area outside the price/time plot; no author or candidate entry marker is drawn. No hypothetical ORB stop, target or exit appears. Existing portfolio fills are simulated ledger values, not brokerage fills; conservative target-gap model fills may lie outside a minute's observed range and are labelled accordingly.

`source_to_chart_traceability.csv` and SVG metadata identify every plotted partition, causal EMA/warmup input, official daily file, source-page reference, ledger and trade ID. Fourteen minute partitions plus one daily file are referenced across the charts. The complete data hash manifest contains 352 processed-data entries; all hashes were verified. `chart_verification.csv` provides one check result per chart.

## PDF and workbook readback

The final PDF has 34 pages. All pages were rendered and reviewed through page previews/contact sheets; the separate reviewer checked all 13 handwritten overviews, priority details/forms and the final summary layout. Its 24 embedded chart images match the latest canonical PNGs pixel-for-pixel. There is no text outside a page boundary. All 50 missing dates occur once in the two-page summary. The five priority cases have overview, minute detail, five-session context and an A–G question sheet; the remaining eight have charts/blank annotation areas, with corresponding Markdown sheets. A separate 2026-07-15 gap exhibit is clearly distinguished from the handwritten disputes.

The XLSX was authored with artifact-tool, exported, recalculated and independently read back with openpyxl without saving through that reader. All five sheets have rendered previews. Baseline formula caches match 190/89/89/85/35/35/50/34/13/52/5. CaseReview has 52 unique cases, a native table and input validations. All 468 cells in D5:L56 are genuinely blank; the six general-rule response rows are blank too. Expected author direction and candle are UNKNOWN. No error cells were found.

A temporary workflow probe confirmed that an author trade confirmation increments the response count without granting engineering approval; the probe was restored to blank before export. Final response and approval counters are zero and 52 cases await author confirmation. Native Microsoft Excel was not opened, so native-app rendering/recalculation is not claimed. The PDF uses printable blank space; the workbook is the editable response channel.

See `pdf_quality_checks.json`, `pdf_pages.json`, `workbook_checks.json`, `workbook_previews/` and `independent_audit_results.json` for machine-readable evidence.

## Optional-wrapper metadata defect

The existing colour wrapper can invalidate a signal while leaving inherited execution/config/verification labels and a 09:15 trace timestamp stale. The canonical strategy still reads ORB, and portfolio validity rejects INVALIDATED. Configurations A/B instantiate ORBStrategy and C instantiates ORBCandidateStrategy; none uses this optional wrapper. This package reads canonical signal status and the original A ledger. Therefore the defect does not alter its counts, chart labels or manual comparison. No active or wrapper change was needed. The strict expected failure remains visible. `optional_wrapper_defect_review.md` contains the probe and the separate maintenance recommendation.

## Tests and original-file integrity

- Full requested suite: **784 passed, 1 skipped, 1 xfailed in 105.80 seconds** (`pytest_full.log`). The skip is the existing superseded Phase 3.4 snapshot test. The strict expected failure is the existing Phase 5.8 optional-wrapper metadata defect. The three Phase 5.9 tests cover blank/independent approvals, missing/duplicate-minute aggregation and ledger/case-union invariants.
- Final Ruff over `src tests scripts`: **all checks passed** (`ruff_full.log`).
- Independent artifact verifier: **all checks passed**, including the original-file snapshot, journal recount, raw candles, indicator recurrence, ledger displays, SVG coordinates, blank fields and PDF hash/readback.
- **12,123 original files retain their pre-work SHA256 hashes.** Snapshot scope includes existing source/tests/scripts, original strategy documents and journal, processed data, the frozen Phase 3.6 report and all previous Phase 5 reports including Phase 5.7/5.8. `.DS_Store`, caches and the new Phase 5.9 outputs are explicitly excluded. Existing unrelated `.DS_Store` working-tree changes were not altered or reverted.

The full pytest suite includes existing historical baseline regression tests because the user explicitly required the full suite. No new candidate profitability backtest, parameter search or optimization was run. Prior candidate eligibility is presented only as disabled Phase 5.8 diagnostic evidence, with no candidate outcome used to select the five cases.

## Fresh read-only review and completion boundary

The required separate reviewer returned: **“Final read-only review passed. No unresolved correctness or layout findings identified.”** It independently verified the data mappings and numerical values. An initial medium provenance finding, a low EMA wording finding and two low layout findings were fixed and rechecked before final signoff. See `fresh_reviewer_findings.md` for the full findings and resolutions.

No active strategy, stop, target, controller, original data or prior report changed. No live/paper order, commit or push was made. No new ORB rule is implemented. Phase 5.9 stops here until the author returns marked levels, exact candles and general definitions, followed by separate source-evidence and engineering decisions.
