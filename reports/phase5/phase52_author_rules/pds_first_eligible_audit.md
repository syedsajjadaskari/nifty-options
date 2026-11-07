# PDS - first eligible confirmation candle (audit)

Signal-level evidence only: no controller, no fills, no P&L and no revised backtest were run. Candidates are NOT approved rules.

**Result: no late entry relative to the PRESERVED rules (PDS-M-001 quality rule, Method 3 sequence).** 106 sessions had a gap-down; 27 armed setups (zone touched; sessions that opened below the zone but never touched it are ARMED_NO_ZONE_RETEST); 23 produced a signal ({'Method 3': 14, 'Method 2': 1, 'Method 1': 8}), every one on the first eligible candle (verdicts: {'NO_SIGNAL_EITHER': 83, 'ENGINE_ON_FIRST_ELIGIBLE_CANDLE': 23}). `LATE_ENTRY_DEFECT`: **0**. Re-derived independently from the raw candles for every session.

## Sequences preserved

* Methods 1 and 2 apply to the FIRST red candle at the zone: a strong bearish body (Method 1) or a higher-price-rejection pin bar (Method 2) activates the signal at that candle's close; the engine does not wait for another bearish candle.
* If that first red candle is weak it is NOT taken (quality rule PDS-M-001): Method 3 then waits for a small support near the zone and activates on the earliest completed candle that closes below it. Entering on the weak first candle would skip the mandatory sequence (the first-eligible principle does not override it).
* Convention to note: for PDS the first red candle at the zone may be the first interaction candle itself (no retest-first requirement as in PDR); this is the existing engine behaviour and is preserved.

## Several methods on one candle

The frozen engine reports only one record per candle. `PDSCoConfirmStrategy` (configuration `phase52-approved`) records any other method the same candle satisfies in `concurrent_methods` and produces one actionable signal. With the current thresholds this never happens (a strong body needs body >= 60% of the range, a pin bar needs an upper wick >= 2x the body: mutually exclusive; Method 3 cannot coincide with Methods 1 and 2 by sequence): sessions with a co-confirmed method: 0. A test forces the second method to prove the recording path and that the signal count does not change.

## The handwritten PDS examples

| date | correction | evidence | remaining decision |
|---|---|---|---|
| 2025-12-26 | AC38 | zone [26124.2, 26141.05], first eligible Method 3 at 09:55, engine 09:55, verdict ENGINE_ON_FIRST_ELIGIBLE_CANDLE | O6 (the weak-first-red-candle quality rule) |

AC38 ('First candle entry', 2025-12-26) asks for entry on the first candle; the engine entered on the Method 3 support break. The report reads 'first candle' as the weak first red candle at the zone (body 10.4%), which the preserved quality rule rejects; an alternative reading (a later strong red candle at the zone, listed below) is also possible. **The author's example is NOT satisfied; the principle is satisfied only under the preserved quality rule.** AC21 / AC22 / AC35 are not about timing and are unchanged (zone construction and the second-trade rule).

## Later strong red candles after a weak first red candle (owner decision O6)

The preserved rule (PDS guide: 'Methods 1 and 2 apply to the first red candle ... if that red candle is not satisfying, use Method 3') does not use a LATER red candle at the zone that meets the Method 1 / 2 numbers. In 20 sessions such a candle exists before or at the engine's Method 3 entry (or with no entry at all). Under a literal 'first eligible candle' reading these could be earlier or additional entries; they are listed, not activated:

| date | engine first signal | later strong red candles at the zone |
|---|---|---|
| 2025-09-22 | 11:25 | 11:15 (signal 11:20); 11:55 (signal 12:00); 13:15 (signal 13:20) |
| 2025-11-03 | 12:15 | 10:10 (signal 10:15); 12:10 (signal 12:15) |
| 2025-11-07 | 12:55 | 13:55 (signal 14:00); 14:00 (signal 14:05); 14:50 (signal 14:55); 15:20 (signal 15:25) |
| 2025-11-14 | 09:25 | 11:15 (signal 11:20); 12:30 (signal 12:35); 12:35 (signal 12:40); 12:50 (signal 12:55); 12:55 (signal 13:00) |
| 2025-12-09 | 12:40 | 12:25 (signal 12:30); 12:35 (signal 12:40); 14:00 (signal 14:05) |
| 2025-12-18 | 09:30 | 09:40 (signal 09:45); 14:20 (signal 14:25); 14:35 (signal 14:40); 14:55 (signal 15:00) |
| 2025-12-26 | 09:55 | 09:30 (signal 09:35) |
| 2026-01-06 | 10:40 | 10:35 (signal 10:40) |
| 2026-01-21 | 10:25 | 09:35 (signal 09:40); 10:05 (signal 10:10); 13:15 (signal 13:20); 13:30 (signal 13:35) |
| 2026-02-16 | none | 09:40 (signal 09:45); 09:45 (signal 09:50) |
| 2026-04-02 | none | 14:35 (signal 14:40); 14:40 (signal 14:45) |
| 2026-04-13 | 15:05 | 14:05 (signal 14:10) |
| 2026-05-18 | 13:10 | 13:35 (signal 13:40); 14:05 (signal 14:10); 14:20 (signal 14:25) |
| 2026-05-20 | 12:10 | 12:00 (signal 12:05); 12:05 (signal 12:10); 12:45 (signal 12:50); 13:00 (signal 13:05); 13:10 (signal 13:15) |
| 2026-05-27 | 13:20 | 13:10 (signal 13:15); 13:15 (signal 13:20); 13:40 (signal 13:45); 14:10 (signal 14:15); 14:25 (signal 14:30) |
| 2026-06-11 | 14:45 | 10:45 (signal 10:50); 10:50 (signal 10:55); 11:10 (signal 11:15); 14:40 (signal 14:45); 14:50 (signal 14:55) |
| 2026-06-23 | 10:30 | 10:40 (signal 10:45); 11:25 (signal 11:30); 11:30 (signal 11:35); 11:40 (signal 11:45) |
| 2026-07-13 | 10:55 | 10:35 (signal 10:40) |
| 2026-07-23 | 10:15 | 10:50 (signal 10:55); 11:10 (signal 11:15); 11:15 (signal 11:20); 12:10 (signal 12:15) |
| 2026-08-18 | 10:50 | 09:40 (signal 09:45); 10:05 (signal 10:10); 10:35 (signal 10:40) |

Per-setup candidate lists are in `pds_first_eligible_setups.csv` and `pds_setup_diagnostics.json`.
