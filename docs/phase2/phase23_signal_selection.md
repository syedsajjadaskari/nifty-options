# Phase 2.3 - signal selection across the five strategies

The strategies are **not** five independent positions. `strategies/trading_day.py` selects, chronologically, across IRF, ORB, PDR, PDS and RF (`SEL-FIRST-001`, `SEL-ACTIVE-001`, `SEL-TIE-001/002`, USER_APPROVED except the unresolved tie-break). The entry engines are untouched.

## Rules in force
1. **First valid signal wins.** Chronological order of signal confirmation (candle end). A 09:20 ORB signal beats a 09:35 IRF signal.
2. **Valid** = CONFIRMED, not diagnostic-only (the absolute highest-high PDR zone), entry bar fillable (not a closing-auction reference bar), fill not later than 13:00:00 IST (`ENTRY-CUTOFF-001`).
3. **Active position:** later signals are ignored for execution and logged (`IGNORED: POSITION_ACTIVE`); they are never reused.
4. **Second trade:** only after an `INITIAL_FULL_STOP`, only PDR or PDS, only from a signal confirmed after the first position closed; at most 2 entries per day.
5. **Same timestamp, different strategies or directions:** a `SIMULTANEOUS_SIGNAL_CONFLICT` is logged and **no strategy is chosen**. `DayRules.tie_break` is `None`; a `TieBreakPolicy` is applied only if its `approved` flag is True. No policy is approved, so today a collision makes the day `UNRESOLVED_EXECUTION` (nothing traded, later signals logged). Same strategy and direction at one timestamp (several methods) is one trade.
6. **Cutoff:** 13:00 IST inclusive of the 13:00:00 fill; a candle that closes after 13:00 (fill after 13:00) is rejected `ENTRY_CUTOFF_EXCEEDED`; a 13:00 confirmation with no 13:00 bar (fill would come later) is rejected `ENTRY_NOT_FILLABLE`. The check converts to Asia/Kolkata, so the machine timezone never matters. Open positions are not affected.

## The PDR zone under the controller (owner-approved research candidates)
Candidate 1 = confirmed reversal swing high (`B_SWING_HIGH_REVERSAL`, the default); candidate 2 = repeated resistance shelf (`C_REPEATED_TOUCHES`); the **absolute highest-high candle is a diagnostic reference only** (`A_HIGHEST_HIGH`: records carry `execution_status = DIAGNOSTIC_ONLY_NOT_TRADABLE` and the controller rejects them). A candidate that finds no zone means **no PDR setup** (`NO_ZONE_CANDIDATE`), never a fallback to the highest high. Every PDR record also carries the diagnostic zone for comparison.

Verification against the four dated PDR charts (candle geometry only; zone bottom = body top):
| chart | drawn zone | candidate 1 (reversal swing high) | candidate 2 (repeated shelf) | diagnostic highest high |
|---|---|---|---|---|
| 1: 2025-09-02 | 24,632.0-24,640.0 | 24,632.25-24,635.00 (max error 5.0) | 24,617.10-24,623.00 (17.0) | same as candidate 1 |
| 2: 2025-10-06 | 24,901.9-24,905.6 | 24,899.80-24,904.75 (2.1) | 24,842.15-24,850.75 (59.8) | same as candidate 1 |
| 3: 2025-10-07 | 25,080.8-25,084.4 | 25,077.25-25,095.70 (**11.3**) | 25,072.20-25,088.20 (**8.6**) | same as candidate 1 |
| 4: 2025-11-20 | 26,061.8-26,074.2 | 26,061.50-26,074.55 (0.35) | 26,025.35-26,031.45 (42.8) | same as candidate 1 |

"Reproduces" here means: bottom edge within about 2.5 points and top edge within about 5.5 points of the drawn zone (chart 1's drawn top overshoots its wick tip by ~5). Candidate 1 reproduces charts 1, 2 and 4; candidate 2 reproduces none; **neither reproduces chart 3** (a shelf of equal highs). The mismatch is preserved and reported (decision `PDR-D09`). Nothing was chosen by profitability.

## Selection-level diagnostics (counts only; `scripts/phase23_signal_diagnostics.py`, `reports/phase23/signal_selection_diagnostics.md`)
Engines run with the per-session cap lifted. No exit simulated, no profit computed, nothing tuned.
| item | value |
|---|---|
| evaluable sessions | 247 |
| confirmed signals from the five engines | 1,345 |
| rejected: fill after 13:00 IST | 484 |
| rejected: entry bar is a closing-auction reference bar / post-close row | 2 / 14 |
| sessions with an eligible first signal | 191 |
| sessions with signals but none eligible | 13 |
| sessions with no signal at all | 43 |
| first eligible signal by strategy | IRF 113 · PDR 47 · ORB 21 · PDS 7 · **simultaneous collision 3** |

The 3 unresolved first-signal collisions: 2026-02-18 09:30 (PDR + RF, both long), 2026-06-23 10:30 (IRF Method 2A + PDS Method 3, both short), 2026-07-13 10:55 (IRF 2A + 2B + PDS Method 3). They are why the tie-break question is on the owner's list; they are not used to pick a priority.

## Is the journal consistent with these rules? (structure only, no P&L)
The journal has 190 rows on 185 dates: 180 dates with one trade, 5 dates with two. In 4 of those 5 the first trade is an `SL` and the second is a PDR/PDS trade (2025-12-31, 2026-06-02, 2026-06-12, 2026-07-23) - exactly the permitted pattern. On the fifth (2026-05-19: ORB `BE`, then PDR `BE`) the first trade booked Target 1, which under the owner's rules would end the day. No journal entry is labelled after 13:00 (latest IRF label 12:20). The journal cannot show which other signals were ignored while a position was open, so the first-signal priority itself cannot be checked against it.
