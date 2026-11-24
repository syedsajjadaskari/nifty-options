# Phase 6.5 - author feedback validation (sections 1-4)

**Written for:** the strategy owner. Research only; nothing selected, activated, committed or traded; the paper-trading modules and every frozen configuration are untouched.

**Scope note (checkpoint record - superseded: the held sections 5-14 were completed afterwards, see the continuation index below and `PHASE65_FINAL_REPORT.md`).** Your prompt was cut off in section 5 ("PDR-B: First green candle satisfying the..."). As agreed, sections 1-4 are done; **PDR-B and later variants, the section-5 comparative backtests, the output list and the final questions are held** until you resend the rest.

## Findings against the author's four observations

1. **'ORB is missed and IRF is taken instead.'** 39 disputed dates. ORB V2 is valid on 12 and is selected on all of them (0 defects; no priority added). On the other 27 it is rejected: 12 fail only PROVISIONAL gates (pattern convention / level construction: new author rules to settle, not implementation defects), 14 fail the explicit 20% wrong-side-wick rule (source-supported; the rulebook's own Examples 2/3 conflict with it) and 1 the gap limit; 2 would signal on the secondary data feed. No implementation defect was found. Of the 12 valid ORB days, 12 rest on at least one PROVISIONAL element (the engulfing / pin-bar pattern route, an inner swing-zone level, or a result that changes under another ORB V2 configuration), so 'valid' is itself convention-dependent. The author's 'rejected ORB would have hit target while the executed IRF hit its stop' pattern appears in 8 hypothetical paths, but an invalid ORB must not replace IRF. See `orb_vs_irf_dispute_report.md` and the paired charts.
2. **'Weak confirmation candles are accepted.'** True in the sense that no source defines a body-strength rule for IRF, PDR, PDS Method 2/3 or RF; the only source-supported quality requirement is PDS Method 1's undefined 'good body'. ORB V2's full-body route already implies body >= 80%. The variants are DIFFERENT PORTFOLIOS, not the baseline trades minus the weak ones: the controller trades one position at a time, so a rejected signal frees the day for a later signal. Primary window, trades of the baseline (config C, 183): B removes 65 and adds 41 new trades (net -24; gross of the removed trades Rs -43,232, of the added Rs +43,192); C removes 83 and adds 49 new trades (net -34; gross of the removed trades Rs -60,976, of the added Rs -46,430); D removes 5 and adds 4 new trades (net -1; gross of the removed trades Rs +10,403, of the added Rs +40,365). Variant D (pattern-aware; PDS Method 1 only) rejects 31 signals; its net gross change comes from the removed and the re-sequenced-in trades listed above. Everything is in-sample and nothing is selected. Results by variant: A: 183 trades, win rate 53.55%, gross Rs +37,420; B: 159 trades, win rate 55.35%, gross Rs +123,844; C: 149 trades, win rate 53.69%, gross Rs +51,967; D: 182 trades, win rate 54.4%, gross Rs +67,382. No global filter is active by default and none is recommended. `candle_strength_report.md`.
3. **'PDR selects a later confirmation candle.'** Of 702 audited PDR cycles (600 confirmed + 102 incomplete at end of day; the continuation run's 600 are the confirmed ones) the audit finds **0 implementation defects relative to the engine's own rules** - but those rules include two conventions the guide does not state, so this is NOT a refutation of the author. The guide (s.4.3) asks only for 'a green candle' after the zone test; the engine additionally requires a close strictly above the zone ceiling (PDR-B05a, a Phase 3.6 brief interpretation) and bars the retest candle from confirming (unresolved convention). Under those conventions 215 of 600 confirmed cycles skipped an earlier green candle (median delay 20 min, mean 44.5, max 340), and in 232 cycles the retest candle itself was green and closed above the ceiling. Under a literal reading of the guide the author's observation is substantively true: the delays come from the two conventions, which are NEW AUTHOR RULES to confirm, not from a coding error. `pdr_audit_report.md`.
4. **'Two updated IRF methods.'** Both rulebooks are present and were read. New Method 1 (any later close back below the first-candle high) and new Method 2 (body top of the first red candle in the rally as a resistance with a second breakout) differ from the existing Methods 1 / 2A / 2B; detector-level comparison and a standalone hypothetical diagnostic are in `irf_new_methods_source_audit.md`. They are NOT integrated into any portfolio (no instruction to do so).

## Files

`source_inventory.md`, `irf_new_methods_source_audit.md`, `irf_new_methods_vs_existing.csv`, `irf_new_methods_standalone_diagnostic.csv`, `orb_vs_irf_dispute_report.md`, `orb_vs_irf_disputed_days.csv`, `charts_orb_vs_irf/`, `candle_strength_report.md`, `candle_strength_signals.csv`, `candle_strength_authority_matrix.csv`, `candle_strength_distribution_by_method.csv`, `candle_strength_variants_performance.csv`, `candle_strength_signals_gated.csv`, `candle_strength_variants_journal.csv`, `candle_strength_winrate_by_body_bucket_DIAGNOSTIC.csv`, `pdr_audit_report.md`, `pdr_setup_audit.csv`, `independent_audit.md`, `preservation_verification.md`.

## Verification (checkpoint record, historical)

```
........................................................................ [ 97%]
.......................                                                  [100%]
885 passed, 1 skipped, 1 xfailed in 232.65s (0:03:52)
Found 3 errors.
[*] 2 fixable with `--fix` (1 unsafe fix available with `--fix --unsafe-fixes`).
```

## Verification (final, after the continuation and the reviewer fixes)

Full repository `pytest`: 945 passed, 1 skipped, 1 xfailed, 0 failed; `ruff check .`: all checks passed (details in `continuation_test_results.md` and `final_independent_audit.md`). The checkpoint block above is kept as the historical record.

## Continuation (sections 5-14): output index

**Status:** sections 5-14 were completed after the checkpoint above (nothing above was discarded). Start with `PHASE65_FINAL_REPORT.md`.

* PDR / PDS: `pdr_rule_authority_matrix.md`, `pdr_215_delayed_cycles.csv`, `pdr_first_eligible_audit.csv`, `pdr_variant_B_signals.csv`, `pdr_variant_C_signals.csv`, `pdr_variant_D_signals.csv`, `pdr_first_vs_second_confirmation.md`, `pds_confirmation_method_audit.md`, `pds_confirmation_variants.csv`
* Backtests: `complete_configuration_manifest.json`, `configuration_signal_comparison.csv`, `configuration_trade_comparison.csv`, `full_backtest_comparison.csv`, `strategy_win_rates.csv`, `monthly_performance.csv`, `annual_performance.csv`, `cost_slippage_sensitivity.csv`, `trade_set_attribution.csv`, `day_by_day_comparison.csv`
* Journal: `manual_journal_reconciliation.csv`, `strict_match_comparison.csv`, `time_tolerant_match_comparison.csv`, `date_strategy_agreement.csv`, `manual_only_comparison.csv`, `automated_only_comparison.csv`, `wrong_strategy_comparison.csv`, `mismatch_root_causes.md`
* Charts: `charts_pdr/`, `charts_pds/`, `charts_changed_trades/`, `charts_trade_set_replacement/` (and `charts_orb_vs_irf/` from the checkpoint)
* Audit / handoff: `phase7_irf_overlap_inventory.md`, `phase7_signal_comparison.csv`, `final_independent_audit.md`, `final_preservation_verification.md`, `remaining_author_decisions.md`, `continuation_reviewer_findings.md`, `continuation_test_results.md`, `pds_second_weak_red_interplay.json`, `continuation_independent_audit.json`, `continuation_preservation_check.json`, `PHASE65_FINAL_REPORT.md`, `Phase65_Author_Feedback_Complete.xlsx`
