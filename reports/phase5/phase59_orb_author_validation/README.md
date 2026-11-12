# Phase 5.9 - ORB author chart validation

This is an annotation package, not a new strategy or profitability study. Frozen configuration A is used consistently because the requested 35/50/34 baseline belongs to that configuration. Current engine reference lines are labelled provisional; author entries and approvals remain blank.

## Reproduced baseline

Original workbook: **190 data rows**, **89 ORB rows on 89 unique dates**. Of these, **85 dates are evaluable: 35 generated/executed ORB and 50 generated no ORB**. IRF executed on 34 ORB-labelled dates; none had a confirmed earlier ORB.

The 13 handwritten dates overlap the 50 missing-signal dates on 11 dates. The union is **52 unique cases**, all charted. 2025-10-17 has no journal row; 2025-11-21 has an IRF journal label, so both remain handwritten-only ORB observations. Four literal ORB Saturday dates are retained in the recount and excluded from the 50 evaluable missing dates.

Within the 50 dates, 34 have IRF, five have another strategy and 12 have no trade. These counts overlap: 2025-11-07 contains IRF followed by PDS. They are not a partition. No original journal date, time label or classification was changed. The four unevaluable ORB labels are 2025-10-11, 2026-08-15, 2026-08-22 and 2026-08-29.

## Five priority cases

| date | topic | selection reason |
|---|---|---|
| 2025-12-24 | Inner-level selection | The latest inner level is unbroken while a smaller pre-open inner level is possible. Ask the author to mark the level, not to approve the nearest-level heuristic. |
| 2025-10-08 | Multi-session support/resistance context | A 98.66% opening body does not break the current major or inner resistance. Multi-session history makes the missing level definition the useful question; no author zone is inferred. |
| 2025-11-28 | Trendline anchor selection | The inner breakout and conditional pin pass, but the last-two-pivot line fails. The author can identify relevant anchors without changing candle quality. |
| 2025-12-12 | Numerical candle-body threshold | The major level and trend pass; a 52.24% body fails the proposed 60% minimum. This isolates a quantitative approximation of qualitative source wording. |
| 2025-12-05 | EMA/gap interpretation - negative control | The green opening candle and EMA relationship do not by themselves make a gap-long setup: the gap is down. No isolated candle-crossing candidate rescues a handwritten dispute, so this honest negative control is paired with the separate 2026-07-15 missing-journal exhibit. |

The gap case is deliberately a negative control: none of the 13 handwritten disputes gains a signal from candle-crossing alone. The separate existing missing-journal case 2026-07-15 demonstrates that source conflict without inventing a handwritten dispute.

## Author workflow and outputs

1. Open `ORB_Author_Review_Package.pdf`: it contains the five priority overviews, one-minute details, prior-session context and a question sheet for each; all eight remaining handwritten charts; a gap contrast and all 50 missing-date records in summary.
2. Draw the intended level/zone, entry candle and direction. Use the blank area marked **AUTHOR ORB ENTRY — TO BE MARKED**. No label is placed at a guessed price or timestamp.
3. Enter general definitions and case-specific responses in `ORB_Author_Review.xlsx`, which has one row per unique case and blank author response/approval columns. `author_response_template.md` provides a printable alternative.
4. Use the six grouped questions in `author_interview_questions.md`. A marked trade, source support and engineering approval are separate decisions. No rule activates automatically.

The package includes **52 overview charts plus 10 priority detail/context charts**, as SVG and 3400-pixel PNG files at 300 DPI. `priority_five/`, `remaining_eight/` and `all_missing_orb/` contain explicit subsets. The 50 missing dates and 34 IRF dates have dedicated CSVs. Every path failure, including hidden later failures, is preserved in `gate_evidence.csv` and `daily/`. `source_to_chart_traceability.csv` maps all 62 charts to original data, source pages and actual ledger IDs.

Chart prices and markers are read from actual one-minute data and existing Phase 5.5 ledger A. Original SL, T1/T2 and exits are shown only for existing simulated trades. Target-gap fills may be conservative model levels outside that minute's range; they are not represented as observed brokerage fills. No hypothetical ORB price, stop, target or exit is drawn.

## Findings and limits

The engine's unbroken previous-day extreme is a source-supported Method 1 exclusion, not proof that Method 2 is impossible. Its latest-fractal inner level, last-two-pivot line, numerical body/wick thresholds and prior-session trend are mechanical assumptions. The source's gap drawings and some wording conflict. The author must define exact levels, anchors, colour/strength, average/timeframe, crossing, trend and entry timing before a general correction can be implemented.

Each count below is out of the 50 missing dates, calculated separately for LONG and SHORT diagnostic paths. It includes later failures hidden by an earlier rejection. Columns and rows overlap; the author's intended method and direction remain unknown.

| Failed predicate | LONG dates | SHORT dates |
|---|---:|---:|
| Method 1: close beyond previous-day extreme | 42 | 38 |
| Method 1/2: established trend | 29 | 21 |
| Method 1/2: candle quality | 36 | 44 |
| Method 2: close beyond latest inner level | 28 | 35 |
| Method 2: last-two-pivot trendline | 42 | 41 |
| Method 2: near-MA extra close condition | 0 | 1 |
| Gap: directional overnight gap | 16 | 34 |
| Gap: current crossing interpretation | 42 | 47 |
| Gap: close beyond average | 20 | 30 |

No missing date lacks a mechanically calculated inner level or EMA, and none fails the gap extension cap. An available inner price does not establish that the engine chose the author's intended level. [rejection_frequency.csv](rejection_frequency.csv) also distinguishes reached failures from all failures and sole failed gates; [gate_evidence.csv](gate_evidence.csv) records observed values and source authority.

For all 34 IRF dates, [orb_vs_irf_34_dates.csv](orb_vs_irf_34_dates.csv) preserves the actual method, signal, entry, initial stop, targets and both exits. There is no confirmed earlier frozen ORB to replace it. Disabled hypothetical candidates and unverified author expectations are separate fields. An eventual author-marked, source-qualified entry must be checked against the original timing/collision rules before any replacement; its time is currently unknown.

The interview has six questions, with exact wording and related dates in [author_interview_questions.md](author_interview_questions.md): define inner/multi-session levels; candle strength/colour; trendline anchors/breakout; average/timeframe/gap crossing; established trend; and exact method/entry/rejection. Ask the level and entry questions first. Candle quality is the sole failed gate on at least one diagnostic path for 22 dates, trendline for eight, and inner selection for two. These overlapping counts prioritize clarification; they do not predict newly valid trades.

The optional colour-wrapper metadata defect is reproduced and documented separately. It does not affect A/B/C strategy identity, actual ledger selection, this package's labels or the verified manual counts. No fix to active behaviour was necessary.

## Verification and scope

Fresh recount, independent one-minute to five-minute aggregation, current ORB/predicate parity and IRF signal/raw-fill checks were performed before accepting Phase 5.8 as an input. [independent_audit.md](independent_audit.md) records chart-to-candle, ledger, original-file, PDF and workbook checks. Full pytest: **784 passed, one skipped, one expected failure**. Ruff: **all checks passed**. The fresh read-only reviewer signed off with no unresolved correctness or layout findings; its initial provenance and presentation findings were resolved. Author confirmation remains necessary even after technical review.

All **12,123 original files** in the pre-work snapshot retain their SHA256 hashes, including source documents, journal, active code, data and previous Phase 5 reports. The PDF has **34 pages** and 24 embedded chart images matching current PNGs exactly. The workbook has **52 unique cases**, 468 blank case author/approval cells and separate blank general-rule responses. Native Microsoft Excel was not opened; formulas, blanks, tables, validations and previews were checked through artifact-tool export and an independent readback.

No five-strategy implementation, stop, target, controller, data or previous report was modified. Phase 5.7 was read as a visual reference and never written. No candidate profitability backtest, parameter search, live/paper order, commit or push was made. The full pytest suite includes existing baseline historical-regression tests as explicitly requested.

## Reproduction

```sh
.venv/bin/python scripts/phase59_snapshot.py  # once only; refuses to replace the original snapshot
.venv/bin/python scripts/phase59_run.py
.venv/bin/python scripts/phase59_charts.py
node reports/phase5/phase59_orb_author_validation/render_charts.mjs
.venv/bin/python scripts/phase59_docs.py
.venv/bin/python scripts/phase59_workbook_data.py
node reports/phase5/phase59_orb_author_validation/build_workbook.mjs
# Use a Python environment with reportlab, pypdf, pdfplumber, pypdfium2 and Pillow:
python scripts/phase59_pdf.py
python scripts/phase59_pdf_qa.py
.venv/bin/python scripts/phase59_verify.py
.venv/bin/ruff check src tests scripts
.venv/bin/pytest -q
```

Primary deliverables are [ORB_Author_Review_Package.pdf](ORB_Author_Review_Package.pdf) and [ORB_Author_Review.xlsx](ORB_Author_Review.xlsx), under `/Users/syedaskari/algo/nifty-options/reports/phase5/phase59_orb_author_validation/`. The required CSVs, Markdown guides and chart/daily directories are in this same directory. [fresh_reviewer_findings.md](fresh_reviewer_findings.md) records the separate review; [source_to_chart_traceability.csv](source_to_chart_traceability.csv) provides chart provenance.

Author responses are not available. Stop here until the author returns the annotated charts; do not implement or backtest a new rule from this package.
