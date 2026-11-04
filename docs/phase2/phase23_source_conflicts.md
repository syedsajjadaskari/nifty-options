# Phase 2.3 - source conflicts, supersessions and what is still not in any document

Authority vocabulary: SOURCE_VERIFIED · USER_APPROVED · PROPOSED_FOR_REVIEW · CONFLICTING · UNRESOLVED. The strategy owner's newer instructions override the older performance-report conventions where they conflict; a change is **never** presented as a rule written in the PDFs.

## A. Superseded by the owner (history kept)
| item | what the documents say | what the owner approved | handling |
|---|---|---|---|
| Stop on the remaining legs after Target 1 | report `[P7] [P11]`, table 3: "once Target 1 is booked, the stop on Leg 2 moves to the entry price" (`BE` = +Rs 5,265) | entry -/+ 6 index points, fixed, no trailing | `EXE-BE-001` -> `SUPERSEDED_BY_USER_APPROVED_RULE`; `POST-T1-STOP-006` supersedes it; legacy mode `post_t1_stop_mode='ENTRY_BREAKEVEN'` kept for reconciliation only. The report's `BE` P&L is therefore not reproducible under the new rule |
| One trade / many independent engines | the guides describe each strategy alone; the report/journal show 189-190 trades on 180-185 dates | one shared controller, first valid signal, at most 2 entries, second only PDR/PDS after a full stop | `SEL-*`, `DAY-*`; `EXE-SEL-001` demoted to research diagnostics |
| Trades per day / time window / re-arming (`IRF-GLOBAL-004`, "not stated in any guide") | not stated | covered at portfolio level by `SEL-*`, `DAY-*`, `ENTRY-CUTOFF-001` | the IRF engine still emits every event; the registry classification of `IRF-GLOBAL-004` is unchanged until the owner confirms that these rules settle it |
| Session open price (`DATA-OPEN-001`) | PDR chart 1 shows the vendor's daily open (a green first candle on 2025-09-02) | use the ORIGINAL first 1-minute open for the gap, the first candle and all signals | USER_APPROVED; the conflict with chart 1 stays on record (10 gap directions and 13 first-candle colours would differ under the other choice) |

## B. Conflicts that remain (not resolved by anyone)
| item | sources | status / handling |
|---|---|---|
| PDR and PDS Target 2 | guides: 70; report: 1 of 6 PDR winners and 2 of 3 PDS winners at 60 | **CONFLICTING**. 70 is used; every signal carries `target_2_conflict`. Not tuned to the report |
| RF target | RF guide p.8 "Target - OPEN"; chart box 60.80; report arithmetic | 60 is **PROPOSED_FOR_REVIEW**, never source-verified or owner-approved; `rf_t2_points=None` -> exits unresolved |
| IRF Method 1: the failure candle | detailed pages (p.1, 5, 6, 9, 13): "the very next candle"; quick-reference card p.14: "next or following candle" | **CONFLICTING**, not resolved; the detailed pages are used; `m1_max_candles_after_breakout=2` is the variant |
| Stops 35 / 40 | IRF/PDS guides: 35 or 40 by the recent green candle's distance (threshold open); PDR/RF: 35 or 40, no rule | owner baseline 35 (40 later) is **USER_APPROVED research**, not the author's selection rule; ORB 30 is source-verified |
| Tie-break between strategies at one timestamp | not in any document; owner: unresolved | **UNRESOLVED**: logged conflict, day unresolved; 3 occurrences in the year (see `phase23_signal_selection.md`) |
| Trend (ORB Methods 1-2, RF) | "established trend", "bullish price structure" - no numbers; ORB p.7's own uptrend example has falling recent swing highs | two owner-approved research variants (A: EMA(200) location; B: EMA + confirmed swings); neither claimed to reproduce the discretionary rule; variant B's "rising swing highs" is partly contradicted by that chart |
| PDR zone | "the high where price reached a peak and then reversed": candle not specified; charts 1, 2, 4 sit on the previous day's high candle, chart 3 on a shelf | two owner-approved candidates; neither reproduces chart 3 (`PDR-D09`) |
| RF entry price, direction, "return inside" | RF p.8 "Exact entry price - OPEN"; direction never stated | proposals (close of the return candle; long; a close back inside) |
| ORB: fill price, Method 2 construction, "excessively extended" gap | no number / no construction | unresolved; Method 2 and the gap setup remain research variants |
| End-of-day exit | not in any document; owner: do not invent a fill | an open position at the end of continuous trading / at the closing auction is `UNRESOLVED_EXECUTION` |
| The 13:00 IST cutoff | not in any PDF (the latest journal entry label is 12:20 for IRF, 11:00 RF, 10:30 PDS) | **USER_APPROVED** |

## C. Journal vs the new day rules (structure only; no profit figure used)
180 dates with one trade, 5 with two. Four of the five two-trade days follow the permitted pattern (first `SL`, second PDR/PDS). 2026-05-19 (ORB `BE`, then PDR `BE`) does not: under the new rules a first trade that booked Target 1 ends the day. The journal also has 5 Saturday-dated rows and one row more than the report's Summary (see the Phase 2.1 reconciliation); nothing here claims a verified replication of the report.
