# Independent audit (Phase 6.5)

Checks inside this phase: variant A equals configuration C exactly (wrapper is neutral); every executed disputed-day scenario equals the committed ledger; the new-IRF detectors are covered by unit tests built from the rulebooks' own worked examples; the full test suite and ruff are in the README.

## Fresh read-only reviewer

A fresh read-only subagent reviewed Phase 6.5. It re-derived, independently from raw 1-minute bars: both new IRF detectors on all 247 primary-window sessions (0 mismatches in signal times, Level B and first-red candles); eight disputed-day condition checks and its own exit simulator that reproduced 121/124 ledger trades (3 differences are stop-gap slip fills) and every disputed-day path; `body_pct` for all 3,287 signal rows (0 mismatches); the gate rules and authority-matrix claims against the source texts; and the PDR cycle structure for all 42 window-A days.

| # | severity | finding | disposition |
|---|---|---|---|
| 1 | HIGH | The README described variants B / C / D by net trade-count changes ("remove 24 and 34", "1 trade"); the real changes are larger: B rejects 65 and C 83 of the 183 baseline trades, and D changes at least three trades (two PDS trades removed, one IRF trade added); the "one removed signal re-sequences the day" explanation was wrong | ACCEPTED. The variants are described as different portfolios; true trade-set changes (kept / removed / added, with the gross of each) are now computed and published in `candle_strength_variants_trade_set_changes.csv` and the README |
| 2 | MEDIUM | PDR '0 defects' is only relative to the engine's own conventions (strict close above the ceiling = PDR-B05a, a Phase 3.6 interpretation; the retest candle may not confirm), so it cannot test the author's complaint; 215 of 600 confirmed cycles skipped an earlier green candle (median delay 20 min); the guide asks only for 'a green candle' | ACCEPTED. README and PDR report now say the author's observation is substantively true under a literal reading and that the cause is two unconfirmed conventions (new author rules), with the counts |
| 3 | MEDIUM | The 'earlier green candle' label was wrong on 8 rows (the engine picked a red lower-wick rejection before the first green) | ACCEPTED and fixed in `pdr_cycle_audit` |
| 4 | MEDIUM | '10 ORB-target / IRF-stop paths' was overstated: 2 were days where a valid ORB was executed (IRF counterfactual); the author's pattern holds on 8 | ACCEPTED: the flag now requires a REJECTED ORB counterfactual against an EXECUTED IRF stop |
| 5 | MEDIUM | Several 'valid ORB' days are valid only through provisional conventions (engulfing reference; a 0.4-point break of an inner swing zone) | ACCEPTED: a `valid_orb_depends_on_provisional_convention` flag and the count are reported |
| 6 | LOW | README listed files that did not yet exist; its verification block read '(log missing)' | ACCEPTED: `independent_audit.md` is generated; README regenerated after the final test run |
| 7 | LOW | The standalone new-IRF diagnostic uses the portfolio exit rules, not the rulebooks' single 60-point target / 35-40 stop and not a 13:00 exit; time columns are candle END times | ACCEPTED: stated as limitations in the source audit |
| 8 | LOW | Weak tests (a `DEFECT_` class accepted by the 'no defect' test; a controller-independent selection test; an always-true zero-range assertion; no Method 2 gap / cutoff test) | ACCEPTED: tests tightened, gap / cutoff test added |

Not checked by the reviewer: window B for IRF, ORB and the variants; ORB level construction beyond the cases listed; the secondary-feed 'would signal' flags; the journal-match numbers (variant ledgers were not saved at that time and are now).

Also noted by the reviewer: `ruff` reports one error in `src/nifty_trading/research/irf_v3/examples.py` - an untracked directory created by another process during this session, not part of Phase 6.5.
