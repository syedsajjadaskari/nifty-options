# Strategy rules - final draft for author review

> **PARTLY SUPERSEDED BY PHASE 2.2** (see `phase22_final_rule_matrix.md`, `phase22_rule_verification.md`): stop baseline 35 (ORB 30) is USER_APPROVED; RF target 60 is PROPOSED_FOR_REVIEW; PDR zone = body top to wick tip; strict zone intersection; structure trend default; pin-bar/strong-candle thresholds per the owner's recommendation; closing-auction bars are non-fillable. Where this file differs, Phase 2.2 wins.

**Status: DRAFT. No rule here is APPROVED.** Labels: **[VE]** verified explicit · **[VQ]** verified, needs a number · **[CF]** conflicting · **[UN]** unresolved · **[PR]** proposed for review (engineering placeholder, not an original rule). `D-nn` inside a strategy's section = that strategy's decision record (e.g. `D-02` under IRF = `IRF-D02`), listed in `strategy_rule_resolution.md`; `author_decisions_required.md` lists what only you can settle.

Common conventions (all strategies): NIFTY 50 index points, 5-minute candles from 1-minute rows labelled by their **start** minute (the 09:15 candle = rows 09:15-09:19, usable at 09:20) [VE data]; IRF/ORB/RF entry triggers are evaluated on a **completed candle close**, never a wick [VE IRF p.14] (PDR/PDS zone *interaction* and IRF Method 3's sweep are wick-based by their own definitions); entry reference price = the close of the trigger candle (fill price is never stated) [PR]; "previous close" = the official NSE close (vendor daily close) [VQ DATA-D01]; from 2026-08-03 the index is frozen 15:15-15:29 (Closing Auction Session) and those candles are real [VQ DATA-D02]. A signal is never a fill.

## IRF - Initial Range Failure (short only [VE])

**Initial range:** IRH/IRL = high/low of the 09:15 candle, wicks included, final only at 09:20 [VE]. Red = close<open, green = close>open [VE].

| Method | Verified entry conditions | Verified rejection conditions | Open items |
|---|---|---|---|
| **M1** breakout & failure | candle *b* closes > IRH [VE]; the very next candle closes back inside the range, IRL <= close < IRH [VE core / UN edges D-02]; enter at that close; no S/R break needed [VE] | wick above IRH without a close above; next candle closes above IRH (even if its wick dips inside) [VE] | next-vs-following candle [CF D-01]; edges [UN D-02] |
| **M2A** support break | close above IRH [VE]; price extends further [PR D-04]; a red candle forms [VQ D-05]; a later candle closes below recent support [VE close / PR support D-06] | a red candle alone; no close above IRH; an immediate close back inside (that is Method 1) [VE] | support, extension, order, expiry [D-04..08] |
| **M2B** resistance break | close above IRH [VE]; resistance = top of the first push [VQ D-07]; price pulls back then trades back above it [VQ D-09]; a red candle closes back below it, at that close [VE] | price still holding above the resistance [VE] | push on the same candle? [PR D-09] |
| **M3** liquidity sweep | small candles inside the range [PR D-10]; a red candle with high > IRH and (High-IRH)/(High-Open) approx 60-70% [VQ D-11]; it **closes below recent support - compulsory** [VE] | the sweep alone; a wick barely clearing IRH; a trending advance instead of compression [VE] | compression, band, 'HPR candle' [D-10..12] |

**Exit:** target **60** from entry, all methods [VE]; stop **35 or 40** by the distance to the most recent green candle [VQ D-13]; never widen the stop [VE]; the report's overlay: 3 lots at Target 1 = 27, stop on the rest moves to entry [VE report].
**Unresolved and blocking:** trades per day / time window / re-arming [UN D-03]. Every IRF signal carries `IRF-GLOBAL-004` unresolved.

## ORB - Opening Range Breakout (long and short [VE])

Decision at **09:20** after the first candle closes [VE]. Stop **30**, target **60** (index points - verified by the report's arithmetic [VQ D-09]).

| Setup | Verified entry conditions | Rejection | Open items |
|---|---|---|---|
| **M1** previous-day level | established trend in the trade direction [VQ D-02]; the 09:15 candle breaks **and closes** beyond the previous-day resistance (long) / support (short) [VE]; strong body or conditional pin bar [PR D-04/05] | wick-only break; strong wick against the trade [VQ] | trend, level, thresholds [D-02..04] |
| **M2** inner level + trendline | break+close beyond the inner level [VE]; trendline supportive; near the EMA wait for a convincing close | a trendline alone is never a signal [VE] | **no objective construction [UN D-06/07]: research variant only** |
| **Gap / 200 MA** | a gap in the trade direction [VE]; the gap brings price through the MA and the first candle **closes beyond it** (a candle that only crosses it does not qualify) [VE]; strong body or bullish/bearish pin bar [VQ] | rejection wick; "excessively extended" gap [**UN, mandatory D-08**] | cap undefined: research variant only |

**MA identity:** EMA(200) of 5-minute closes - verified on both PDR chart legends to 0.005 point [CF wording D-01, evidence HIGH]. Exit: as above; no end-of-day rule in the guide.

## PDR - Previous Day Resistance, gap-up support retest (long [VE])

| Verified entry conditions | Verified rejection | Open items |
|---|---|---|
| zone = a previous-day high/reversal candle, body to upper-wick tip, extended forward [VQ, but the candle choice is **PR PDR-D09**]; next day opens **gap up** [VE]; the open is **above** the zone ('pulls back into the zone') [VQ D-02]; do not enter at the open [VE]; price returns to the zone: wick, body, inside, or very close [VQ D-03]; **then** a green candle, entry on it [VQ D-04] | price keeps rising without returning to the zone [VE] | **which candle marks the zone [PR PDR-D09]**; "clear high and reversal" [UN D-05, mandatory checklist]; proximity [PR D-03] |

**Worked examples (source cases):** with the text default (open above the zone) 2025-09-02 (09:25 candle) and 2025-10-06 (09:30) reproduce. **2025-10-07 (Example 3) does not reproduce under the text default**, but it also does not contradict the text: the zone the author drew is only about 4-5 points tall (about 25,080.5-25,084.5; the open lies ~3 points above it, so with the drawn zone the example matches the text) while the engine's zone from the day's highest-high candle (a 14:50 spike) is 38.6 points tall (PDR-D09). It reproduces (09:20 candle, +69.90 reached, 40.60 stop untouched) only under the weaker open readings *with the engine's zone*, so it is **not** evidence for them.
**Exit:** target **70** [VE; conflicts with 1 report winner at 60, D-07]; stop **35 or 40 "depending on the situation" - no rule [UN D-06]** -> exits not evaluable.

## PDS - Previous Day Support, gap-down resistance retest (short [VE])

| Method | Verified entry conditions | Open items |
|---|---|---|
| zone | previous day's low candle, body **and** lower wick [VQ]; next day opens **gap down**, price below the zone [VQ D-04]; price rises into the zone: wick/body/inside/very close [VQ] | open inside the zone? [VQ D-04] |
| **M1** good red candle | the first red candle at the zone has a good body [VQ] | body threshold [PR D-01] |
| **M2** red HPR pin bar | the first red candle is a pin bar with a long upper wick pushing into/above the zone [VQ] | ratios [PR D-02] |
| **M3** small support break | if the first red candle is not satisfying, wait for a small support to form and break [VQ] | size, close vs touch, stand-alone - the author's own open items [UN D-03] |

**Exit:** target **70**, all methods [VE; conflicts with 2 of 3 report winners at 60, D-06]; stop **35 or 40** by the recent green candle's distance [VQ, measurement UN D-05]. Entry timing unstated [UN D-07] -> at the candle close.

## RF - Reverse Failure (long, implied [PR D-01])

| Verified entry conditions (in this order [VE]) | Rejection [VE] | Open items |
|---|---|---|
| already-established uptrend [VQ D-02]; gap **up** with the open within yesterday's range [VE]; after the first-candle range is marked, a candle **closes below RF Low** (a wick is not enough) [VE]; then price returns inside the original range [VQ D-02] | gap down; gap above yesterday's high; previous downtrend + sudden large gap above the EMA; gap up without the break-and-return [VE] | direction [PR]; return-inside definition [D-02]; "established" [D-02 ORB] |

**Exit - ALL UNRESOLVED:** entry price [UN D-04]; stop "35-40, what is logical" [UN D-05]; **target OPEN - `RF_TARGET_STATUS = UNRESOLVED` [UN D-06]** (evidence points to 60: chart box 60.80 and the report's arithmetic, but neither is a rule). Signal detection does not depend on them.

## Mathematical definitions (formulas)

| Quantity | Definition | Status |
|---|---|---|
| body / range / wicks | `B=|C-O|`, `R=H-L`, `UW=H-max(O,C)`, `LW=min(O,C)-L`; ratios divide by `R` (all 0 if `R=0`) | exact |
| strong bullish / bearish | colour, `B/R >= a`, opposite wick `/R <= b`; (a,b) in {STRICT .70/.15, **MODERATE .60/.20**, LOOSE .50/.25} | PR |
| pin bar | `wick/R >= w`, `B/R <= beta`, opposite wick `/R <= o`; {STRICT .70/.25/.10, **MODERATE .60/.33/.15**, LOOSE .55/.40/.20} | PR |
| wick share (IRF M3) | `(H - IRH) / (H - top of body)` | exact formula [VE]; band PR |
| swing low/high (k) | `L[j] <= L[j+-m]` for m<=k, confirmed only when candle j+k has closed | PR (k=1) |
| gap | `Open[09:15] - PreviousOfficialClose` | VQ |
| zone | PDR `[min(O,C), H]` of the previous-high candle; PDS `[L, max(O,C)]` of the previous-low candle | VQ |
| EMA(200) | EMA of completed 5-minute closes, SMA-seeded, NaN until 200 candles (warm-up data loaded, never evaluated) | exact; identity verified |
| daily SMA/EMA(200) | official daily closes strictly before the session (248 bars precede the first session) | research alternative |
| zone test | PDR `Low <= zone_high + prox`; PDS `High >= zone_low - prox`; prox 5 points (0/5/10) | PR |

## Verification status of what the engines emit
Every emitted signal is `PROPOSAL_DEPENDENT` or `RESEARCH_VARIANT`; **none is `VERIFIED`**, because every strategy has at least one unresolved item above.
