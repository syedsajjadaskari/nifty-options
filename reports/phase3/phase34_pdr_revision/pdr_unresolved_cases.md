# PDR revision - unresolved cases

**Written for:** the strategy owner. Each item is something the author's three clarifications do not settle. The engine records the chosen research setting on every signal; none is source-verified. No item was resolved by looking at profit.

| # | unresolved point | what the engine does (research setting) | evidence / size of the effect | decision needed |
|---|---|---|---|---|
| 1 | Numeric shape of GOOD GREEN BODY, LOWER-PRICE REJECTION and HAMMER (and the candle colour of the last two) | default: body >= 60% with upper wick <= 20%; rejection = lower wick >= 2 x body with the close in the top 30% and the low reaching the zone; hammer = lower wick >= 2 x body, upper wick <= 10%, body in the upper part; colour not required for the last two | all four dated guide entry candles fail every default pattern; the example-read profile passes all four. Signals: 81 (default) vs 103 (example-read); patterns alone: green body 72, rejection 15, hammer 30 | numbers for the three patterns (and whether a rejection/hammer may be red) |
| 2 | How many highs are 'multiple', how close, how far apart, how wide; which bodies set the lower boundary; whether an isolated spike is always included | touches >= 2 within 5 points of the day high, members closer than 2 candles count once, floor = lowest member body top, the day high is ALWAYS included | B differs from A on 53 days (floor only; the ceiling is identical on every day); the B zone changes with the tolerance (5/10/15) on 107 days; the tag UNRESOLVED_ZONE (135 days) is the union of the two and concerns the drawn FLOOR only. The signal count stays 81 for every tolerance and equals A | the cluster parameters and the lower-boundary rule |
| 3 | Example 3 (PDF p.4, 2025-10-07): the author's drawn box is a thin shelf of equal highs and excludes the 14:50 spike | the spike (25,095.70) is kept as the ceiling, as the author asked ('day's high should be considered'); the zone becomes [25,077.25, 25,095.70] | the open (25,087.55) is inside that zone, so the preserved open-above-zone rule rejects the day; excluding the spike when it lies above a shelf (diagnostic only, contradicts PDR-A01) gives 82 signals instead of 81; the journal has a PDR entry on that date at 09:20 | is a spike above a shelf part of the zone, or is the shelf the zone? |
| 4 | Must the session open ABOVE the zone? (legacy PDR-011, a proposal, preserved) | yes (open > zone ceiling = previous-day high) | anywhere-open sensitivity: 158 (A) / 159 (B) signals instead of 81. PDR-011 was tuned for a swing-high zone BELOW the day's high; with the ceiling at the previous-day high it requires the gap to clear yesterday's whole range. The guide only says 'open gap up' and 'do not enter at the open'. It also explains journal rows 22 and 134 (see the 2x2 table in the summary). In the author's own Example 3 drawing the shelf ceiling (25,084.40) lies BELOW the 09:15 open (25,087.55), so PDR-011 would pass on the drawn zone; the conflict arises from including the spike. Example 5 may open at/inside the zone (low-resolution reading) | whether the gap must clear yesterday's high |
| 5 | May the confirmation be the test candle itself? (legacy rule: no) | no, the confirmation comes after the test candle | sensitivity: 88 signals | same-candle test-and-confirm |
| 6 | How long does a tested setup stay armed? | until a candle qualifies or the session ends (the old engine re-armed the same way) | no cut-off other than the approved 13:00 entry cutoff, applied by the controller | an expiry |
| 7 | Which zone floor? the guide says 'the relevant candle-body level' | body top of the source candle(s) (the wick-only convention that fits Examples 1, 2 and 4) | the floor does not enter the close rule, the rejection pattern (which uses the ceiling) or, while the open must lie above the ceiling, the interaction test; it matters only in the open-anywhere sensitivity (A 158 vs B 159). It does change the drawn box and the chart | body top vs body bottom |
| 8 | Session 2025-10-23 (previous session is the unverifiable Muhurat day) | the engine cannot evaluate it (NOT_EVALUATED) | one session; tagged DATA_OR_IMPLEMENTATION_ISSUE in the daily comparison | none (data) |
| 9 | Example 5 (undated) and the figures' candles differ slightly from the repository data at the open | not used as evidence | see `pdr_source_rule_verification.md` of Phase 3.3 | owner to look at Example 5 |
| 10 | How wide may a 'small box' be? (guide p.2: a small box, not the whole surrounding move) | no limit (width recorded) | widths above 30 points: 14 days (A) / 17 days (B); maximum 82.25 points | a maximum width, or acceptance |
| 11 | Journal rows 67 (2025-12-31 09:45) and 147 (2026-06-05 09:25) | no signal within tolerance under the active setting (row 147 shifted +15 under the example-read thresholds) | see `pdr_journal_agreement_2x2.csv` | none: stays unexplained, no discretionary decision is inferred |

## Days where the choice of thresholds changes the signals (default vs example-read, candidate A)

| date | default signals | example-read signals |
|---|---|---|
| 2025-11-20 | 1 | 2 |
| 2025-11-27 | 1 | 3 |
| 2025-12-01 | 2 | 3 |
| 2025-12-23 | 6 | 8 |
| 2026-01-28 | 3 | 4 |
| 2026-02-23 | 7 | 8 |
| 2026-03-05 | 5 | 6 |
| 2026-03-24 | 2 | 3 |
| 2026-04-01 | 1 | 2 |
| 2026-05-04 | 4 | 5 |
| 2026-05-06 | 3 | 5 |
| 2026-05-07 | 4 | 9 |
| 2026-06-05 | 0 | 2 |
| 2026-07-07 | 5 | 6 |

## Days where candidate B's zone is unresolved

135 days carry the tag UNRESOLVED_ZONE (see `pdr_daily_signal_comparison.csv`, candidate B rows): 2025-09-01, 2025-09-02, 2025-09-03, 2025-09-09, 2025-09-10, 2025-09-11, 2025-09-12, 2025-09-15, 2025-09-17, 2025-09-18, 2025-09-19, 2025-09-23, 2025-09-24, 2025-09-25, 2025-09-26, 2025-10-03, 2025-10-06, 2025-10-07, 2025-10-08, 2025-10-13, 2025-10-16, 2025-10-17, 2025-10-20, 2025-10-24, 2025-10-28, 2025-10-30, 2025-11-10, 2025-11-11, 2025-11-12, 2025-11-13, 2025-11-17, 2025-11-18, 2025-11-20, 2025-11-24, 2025-11-25, 2025-11-26, 2025-11-27, 2025-11-28, 2025-12-01, 2025-12-02 ...
