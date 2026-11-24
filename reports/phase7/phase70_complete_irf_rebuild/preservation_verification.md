# Preservation verification (Phase 7.0)

HEAD before: `9d7f5af87148a4db7d6c502c2a73295a5bcdd0c6` - HEAD now: `9d7f5af87148a4db7d6c502c2a73295a5bcdd0c6` (unchanged). Nothing was committed, staged or pushed by this task.

## Protected content (SHA-256 over every file path + content; `__pycache__` excluded)

| Path | Result | Size |
|---|---|---|
| `src/nifty_trading/strategies` | **CHANGED** | 25 files |
| `src/nifty_trading/research/orb_v2` | **UNCHANGED** | 16 files |
| `src/nifty_trading/broker` | **UNCHANGED** | 4 files |
| `src/nifty_trading/core` | **UNCHANGED** | 9 files |
| `src/nifty_trading/config` | **UNCHANGED** | 3 files |
| `data/processed` | **UNCHANGED** | 352 files |
| `data/phase4` | **UNCHANGED** | 144 files |
| `data/metadata` | **UNCHANGED** | 8 files |
| `docs/trading journal` | **UNCHANGED** | 2 files |
| `reports/phase6/PHASE61_63_FINAL_RESEARCH_REPORT.md` | **UNCHANGED** | 1 files |
| `reports/phase6/phase62_combined_backtest` | **UNCHANGED** | 453 files |
| `reports/phase5/phase55_combined_backtest` | **UNCHANGED** | 332 files |

**Why `src/nifty_trading/strategies` shows CHANGED:** the hash covers every file on disk, tracked or not. `git diff --name-only` shows 0 modified tracked files, so no tracked file there was edited; the difference is 2 NEW untracked file(s) that appeared after this task's first snapshot and were not written by this task (they belong to the concurrent Phase 6.5/6.5b work): `src/nifty_trading/strategies/pdr_variants.py`, `src/nifty_trading/strategies/pds_variants.py`.

## Tracked files modified (`git diff --name-only`): 0

* none

## Untracked files
* Created by Phase 7.0 (1416): the package `src/nifty_trading/research/irf_v3/`, `tests/test_phase70_irf_v3.py`, `scripts/phase70_run.py|docs.py|preserve.py`, and `reports/phase7/phase70_complete_irf_rebuild/`.
* The two new rulebook PDFs (still untracked, not added): `docs/strategy_docs/IRF_Inverse_Retest_Failure_Rulebook.pdf`, `docs/strategy_docs/IRF_Method2_First_Red_Candle_Rulebook.pdf`.
* Other untracked files that existed when this task's first snapshot was taken (102; Phase 6.5 author-feedback work - `reports/phase6/phase65_author_feedback/`, `scripts/phase65_*.py`, `src/nifty_trading/research/phase65.py`, `src/nifty_trading/strategies/strength_gate.py`, `tests/test_phase65_author_feedback.py`). **They were not created or edited by this task**; they appeared in the working tree after the session started (the session-start git status listed only the two PDFs), i.e. another process is working in the same repository.
* Untracked files that appeared AFTER this task's first snapshot and are not Phase 7.0 outputs: 255: `reports/phase6/phase65_author_feedback/annual_performance.csv`, `reports/phase6/phase65_author_feedback/automated_only_comparison.csv`, `reports/phase6/phase65_author_feedback/candle_strength_variant_ledgers.csv`, `reports/phase6/phase65_author_feedback/candle_strength_variants_trade_set_changes.csv`, `reports/phase6/phase65_author_feedback/charts_pdr/A_2025-09-04_1420.svg`, `reports/phase6/phase65_author_feedback/charts_pdr/A_2025-09-04_1510.svg`, `reports/phase6/phase65_author_feedback/charts_pdr/A_2025-11-17_1035.svg`, `reports/phase6/phase65_author_feedback/charts_pdr/A_2025-11-17_1125.svg`, `reports/phase6/phase65_author_feedback/charts_pdr/A_2025-11-27_1310.svg`, `reports/phase6/phase65_author_feedback/charts_pdr/A_2025-11-27_1440.svg`

## Systems explicitly not touched
* Older IRF engines (`strategies/irf*.py`), ORB V2, PDR, PDS, RF, the five-strategy portfolio controller (`strategies/runner.py`, `selection.py`, ...), `broker/`, `core/`, `config/` (paper-trading configuration): hash-compared above.
* Historical market datasets (`data/processed`, `data/phase4`, `data/metadata`), the manual journal (`docs/trading journal`), earlier backtest results (Phases 5.5 and 6.2/6.3 reports): hash-compared above.
* No import of IRF V3 exists outside `irf_v3/`, `tests/test_phase70_irf_v3.py` and `scripts/phase70_*.py`; no order or paper-order call exists in the package.

## Full existing test suite (all tests in `tests/`)
`924 passed, 1 skipped, 1 xfailed in 1523.69s (0:25:23)`
