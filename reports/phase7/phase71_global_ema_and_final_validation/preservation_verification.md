# Preservation verification (Phase 7.1)

Run at 2026-11-18 20:17. HEAD `9d7f5af87148a4db7d6c502c2a73295a5bcdd0c6` (nothing committed, staged or pushed by this task).

## 1. Tracked files modified (`git diff --name-only`)
**0**

## 2. Protected paths modified after Phase 7.1 started
Start marker: 2026-11-18 16:17:33 (creation of `scripts/phase71_fetch_nov2026.py`). Protected paths: `src/nifty_trading/strategies`, `src/nifty_trading/research/orb_v2`, `src/nifty_trading/research/irf_v3`, `src/nifty_trading/broker`, `src/nifty_trading/core`, `src/nifty_trading/config`, `src/nifty_trading/data`, `src/nifty_trading/instruments`, `data/processed`, `data/phase4`, `data/metadata`, `data/archive`, `docs/trading journal`, `docs/strategy_docs`, `reports/phase3`, `reports/phase5`, `reports/phase6/phase62_combined_backtest`, `reports/phase6/phase61_irf_support_break`, `reports/phase6/phase63_manual_reconciliation`, `reports/phase7/phase70_complete_irf_rebuild`.
**0 file(s) modified**

## 3. Untracked files
* Created by Phase 7.1 (1515): `reports/phase7/phase71_global_ema_and_final_validation/`, `src/nifty_trading/research/phase71/`, `tests/test_phase71_global_ema.py`, `scripts/phase71_*.py`, `data/phase71/` (processed November store) and `data/raw/phase71_5paisa_nov2026/` (new raw namespace; the frozen stores were not touched).
* Phase 7.0 files (untouched by 7.1; untracked since 7.0): 1416.
* The two IRF rulebook PDFs (still untracked, never added): `docs/strategy_docs/IRF_Inverse_Retest_Failure_Rulebook.pdf`, `docs/strategy_docs/IRF_Method2_First_Red_Candle_Rulebook.pdf`.
* Files created by OTHER workers (Phase 6.5 / 6.5b author-feedback work; not read for modification, not edited): 594 e.g. `reports/phase6/phase65_author_feedback/PHASE65_FINAL_REPORT.md`, `reports/phase6/phase65_author_feedback/Phase65_Author_Feedback_Complete.xlsx`, `reports/phase6/phase65_author_feedback/README.md`, `reports/phase6/phase65_author_feedback/annual_performance.csv`, `reports/phase6/phase65_author_feedback/automated_only_comparison.csv`, `reports/phase6/phase65_author_feedback/before_snapshot.json`.

## 4. Integrity of protected evidence
* Manual journal SHA-256 `97a9ad4dfb5520619bb979770115d7b6f4e3e37e649af255c543f5fce9694781` (data rows 190, summary 189, weekend rows 5) - identical to the hash recorded by Phases 6.3 and 7.0 (`97a9ad4d...`).
* IRF PDFs SHA-256: {'IRF_Inverse_Retest_Failure_Rulebook.pdf': '39b9dd226c5dabd321a57855e23317e101f49e5a76f56ee4a5180ec10a69cec2', 'IRF_Method2_First_Red_Candle_Rulebook.pdf': '5ad283df82c81eefaf2bef7277318ad38cafa7d4d5e8ad5147fbf98ec8276dc4'}.
* Frozen configuration A re-run through the unchanged controller reproduces the saved Phase 6.2 'A' exactly (window A 196 trades / Rs +297,765; window B 609 / Rs +509,398) - evidence that the frozen engines, controller and data are unchanged.
* No Phase 7.1 module is imported by any frozen or paper-trading code (the new package is only imported by `scripts/phase71_*.py` and its tests); no order or broker-order call exists in it. The only broker use is the read-only historical-candle request in `scripts/phase71_fetch_nov2026.py` (BrokerClient order methods are disabled).

## 5. Full test suite
`960 passed, 1 skipped, 1 xfailed in 496.83s (0:08:16)`
