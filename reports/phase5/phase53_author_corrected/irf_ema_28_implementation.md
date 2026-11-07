# IRF - minimum 28-point distance from EMA(200) (implementation)

Signal-level evidence only: no controller, no fills, no P&L and no profitability backtest were run. Conventions marked PROVISIONAL are not confirmed as the author's meaning.

## The rule as implemented (`PROVISIONAL_EMA_RANGE_DISTANCE`)

* `E` = the EMA(200) of completed five-minute candles (with the existing historical warm-up) **including the signal candle's own close** - available when that candle ends, which is the decision time. No later value is used (audit-verified); the previous candle's EMA gives a different decision for 1 signal(s).
* distance = `L - E` if `E < L`; `E - H` if `E > H`; `0` if the EMA lies inside the candle's high-low range. A candidate passes only if distance **>= 28.0** (inclusive; a distance of exactly 28.0 passes). A candidate with a smaller clearance is REJECTED and logged (`irf_ema_rejections.csv`).
* **Scope:** all four IRF methods (the clarification speaks of IRF as a whole and the guide has no EMA text, so no method is excluded; `phase53-var-irf-ema28-method2-only` is the scope variant). For Method 2 a rejected candidate does not end the attempt (a later candle of the same attempt may qualify); Method 1 and Method 3 are history-independent per candle.
* Unknown EMA (warm-up) does not reject; no signal in the history is affected (EMA unavailable: 0).
* EMA construction: SMA seed of the first 200 completed candles, then the standard EMA across the concatenated sessions (warm-up from 2025-07-01); the 2025-10-21 Muhurat session (12 candles) is excluded by the repo's session filter - including it would move the EMA by up to ~18 points on some rows but changes no pass/fail decision (independent reviewer's test).
* After a Method 2 rejection the attempt stays alive, so a later candle closing below the same support can fire as a delayed entry (the reviewer counted 40 such signals in the combined configuration). This is an inference, not an author decision (O2: skip versus wait).

## How many IRF signals fail the 28-point rule

| reading | Phase 3.6 IRF signals failing | of which executed trades | within 13:00 | first-red-low IRF signals failing | within 13:00 |
|---|---|---|---|---|---|
| range >= 28 (the Phase 5.3 convention) | 167 | 30 | 102 | 189 | 117 |
| range >= 27 (handwritten number) | 164 | 29 | 100 | 185 | 114 |
| /close - EMA/ >= 28 | 116 | 19 | 70 | 126 | 79 |
| /close - EMA/ >= 27 | 109 | 17 | 66 | 118 | 74 |

Out of 874 Phase 3.6 IRF signals (115 are the executed trades). 27 versus 28 changes the answer for 3 signals (range) - the boundary is not a rounding detail, but it is rarely decisive. The comparison is diagnostic only; no variant was chosen by outcome.

By method (Phase 3.6 signals failing the range rule): Method 1 82, Method 2B 48, Method 2A 37.

## Signal changes

| configuration | IRF added | IRF removed | earlier | later | total IRF signals |
|---|---|---|---|---|---|
| phase53-irf-ema28 | 10 | 139 | 1 | 51 | 745 |
| phase53-var-irf-ema28-method2-only | 10 | 57 | 1 | 44 | 827 |
| phase53-var-irf-ema27 | 10 | 134 | 2 | 52 | 750 |
| phase53-var-irf-ema28-close | 10 | 91 | 3 | 39 | 793 |
| phase53-author-corrected | 144 | 232 | 128 | 85 | 786 |

Rejection events (a candidate candle rejected; one signal can be rejected on several candles of an attempt): EMA-28 alone 407 ({'Method 1': 82, 'Method 2B': 167, 'Method 2A': 158}); combined 514. Net effect of the 28-point rule alone: IRF 874 -> 745 confirmed signals (139 removed, 10 newly generated because a rejected attempt stays alive, 51 later).

## Where the EMA lies (the directional audit)

| Phase 3.6 IRF signals failing the range rule | signals | of which executed |
|---|---|---|
| EMA ABOVE the full candle (within 28 above) | 55 | 10 |
| EMA INSIDE the candle's range | 52 | 9 |
| EMA BELOW the full candle (within 28 below) | 60 | 11 |
| EMA between the entry and Target 1 (entry - 27) | 66 | 10 |
| EMA NOT between the entry and Target 1 | 101 | 20 |

**Discrepancy to record.** The range distance is symmetric, but the author's handwritten reasons (AC13, AC18; Phase 5.1 transcription: 'the space between the entry candle and the EMA is less than 27 ... wait until the EMA is broken'; 'should be ignored as Tgt 1 is not above EMA, tgt 1 is less than 27') are directional: they concern an EMA BELOW the entry within the target distance. Of the Phase 3.6 signals rejected by the convention, only 66 of 167 have the EMA between entry and Target 1; 55 are rejected only because the EMA lies within 28 points ABOVE the candle (it does not obstruct a short's target), and 52 because it lies inside the candle (its relation to the target depends on the close). Conversely, in this history no signal passes the 28-point range rule while the EMA lies between its entry and Target 1 (0), because Target 1 is only 27 points away; so in this history the convention never lets through a signal whose first target is blocked (the entry is the next one-minute open, so a gap beyond the candle could in principle do so), but it also rejects signals that are not blocked. A directional rule ('EMA at least 28 below the candle' or 'EMA not between entry and Target 1') is a separate owner decision.

## Handwritten examples

| correction | date | measurements | status |
|---|---|---|---|
| AC13 | 2025-10-09 | EMA EMA_INSIDE_CANDLE; range distance 0.0; close distance 2.92640380451121; EMA between entry and T1: True | PARTIAL_REJECTED_NOT_DELAYED |
| AC18 | 2025-11-10 | EMA EMA_BELOW_CANDLE; range distance 22.21967170071366; close distance 25.269671700712934; EMA between entry and T1: True | PARTIAL_REJECTED_NOT_DELAYED |

Both signals are rejected (partly reconciled): the author's alternative 'wait for the EMA break' (a delayed entry) has no defined rule and is not modelled.

## Remaining decisions

O2: confirm the measure (range / close / entry / low), whether the EMA must be BELOW (directional), skip versus wait for the EMA break, and the method scope; 27 versus 28 is settled by the owner's 28.
