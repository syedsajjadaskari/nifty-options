# Phase 3 readiness (Phase 2.3)

**Phase 3 has not been started and must not start until the owner authorises it.** This file replaces the Phase 2.2 version.

## Verdict
| Question | Answer |
|---|---|
| Is the **data foundation** ready? | Yes. 248 sessions, 247 evaluable; closing-auction bars kept and non-fillable; the original first 1-minute open is the session open (owner-approved). |
| Are the signal engines deterministic and causal? | Yes (prefix-invariance tests; the controller reads bars only from the fill onwards). The five entry engines were not rewritten in Phase 2.3. |
| Is the **execution framework** ready? | **Yes, as an owner-approved research framework**: shared day controller, first-signal priority, at most 2 entries, PDR/PDS-only second trade, 13:00 IST cutoff, six lots in two legs, the entry -/+ 6 post-T1 stop, T1_THEN_BUFFER_STOP / INITIAL_FULL_STOP classes, adverse gap fills with logged slippage, non-fillable auction bars, 46 new controller/exit/eligibility tests (plus edits to older ones). |
| Is a **full backtest** ready to begin? | **Not yet.** The framework is ready, but several rules a backtest would silently depend on are still not approved (below). Phase 2.3 ran **no** profit backtest. |

## Per strategy (statuses: `READY_VERIFIED` · `READY_WITH_APPROVED_ASSUMPTIONS` · `BLOCKED_BY_UNRESOLVED_RULES`)
Nothing is `READY_VERIFIED`: every signal still depends on at least one proposal or an unresolved source rule (`verification_status` is never `VERIFIED`).

| Strategy | Status | Execution side (approved) | Still unresolved on the signal side |
|---|---|---|---|
| IRF | `BLOCKED_BY_UNRESOLVED_RULES` | stop 35, T2 60, post-T1 stop, cutoff, first-signal priority | Method 1 "very next" vs the p.14 card; M2 extension/expiry; M3 compression size (M3 gives 0 signals); `IRF-GLOBAL-004` confirmation |
| ORB | `BLOCKED_BY_UNRESOLVED_RULES` | stop 30 / T2 60 verified, 09:20 decision | trend (two owner-approved research variants, neither source-exact); candle thresholds; fill price; Method 2 construction; "excessively extended" gap |
| PDR | `BLOCKED_BY_UNRESOLVED_RULES` | stop 35, T2 70 (conflicts with the report), second-trade eligibility | which candle marks the zone (two approved candidates; neither reproduces chart 3); "very close"; "clear high and reversal" |
| PDS | `BLOCKED_BY_UNRESOLVED_RULES` | stop 35, T2 70 (conflict), second-trade eligibility | candle thresholds (the guide calls them undefined); Method 3 details; zone body+wick vs wick-only |
| RF | `BLOCKED_BY_UNRESOLVED_RULES` | stop 35 | **target (60 is only a proposal), entry price, direction, "return inside"**; trend variants |

## What is still needed from the owner before a backtest (plain English, most important first)
1. **Who wins when two strategies signal in the same minute?** (3 cases in the year; today the day is left unresolved and nothing is traded.)
2. **What happens to a position still open when continuous trading ends or the closing auction starts?** (Today: left unresolved, no exit price invented; in the Phase 2.2 reviewer's measurement over all IRF events, 10 events still open on the 21 closing-auction days and 75 on ordinary days were left open at the end of fillable bars.)
3. **The PDR zone:** which candle? Two approved candidates reproduce charts 1, 2 and 4 or none; chart 3 is reproduced by neither.
4. **Trend variants:** run both A and B side by side, or decide? (Variant B's "rising swing highs" is contradicted by your ORB page-7 chart.)
5. **RF:** target, entry price, direction and what counts as "back inside".
6. **PDR/PDS Target 2:** 70 (guides) or 60 (some report winners)?
7. **IRF Method 1:** the very next candle only, or "next or following"?
8. **Candle thresholds** (strong, pin, small) and "very close" to a zone.
9. **Do the new portfolio rules settle `IRF-GLOBAL-004`** (trades per day, time window, re-arming)?
10. **A corrected trade list**, now that the stop after Target 1 has changed (the report's `BE` outcome no longer exists).

## Suggested order (not started)
Resolve 1-2 -> confirm 9 -> run the unrestricted *signal-level* study of the two PDR candidates and both trend variants (no P&L ranking) -> only then add costs and run the full backtest with the 35-vs-40 comparison.
