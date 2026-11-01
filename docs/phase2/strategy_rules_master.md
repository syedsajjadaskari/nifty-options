# Strategy rules master

Scope: **NIFTY 50 index-price signals only** — no options, no orders, no live execution. NIFTY 50 is an index: every point/₹ figure is **synthetic**.
Tags: **[VE]** verified explicit · **[VQ]** verified, needs interpretation · **[CF]** conflicting · **[MS]** missing · **[PR]** proposed (engineering interpretation, *not* a source rule).
Rule IDs link to `rule_registry.md`; ambiguity IDs (`AMB-…`) link to `ambiguous_rules.md`. Page numbers are PDF pages.
Every qualitative threshold below is `PROPOSED_FOR_REVIEW` and lives in `src/nifty_trading/strategies/params.py`; defaults follow the source wording where it gives any and are otherwise mid-range placeholders — they were **not** chosen for performance.

---

## 1. IRF — Initial Range Failure *(IRF_Strategy_Guide Updated.pdf)*

| # | Item | Content |
|---|---|---|
| 1 | Concept | Short after price pushes above the opening range and the push **fails** (p.1). It "does not try to predict reversals". |
| 2 | Direction | **Short only** [VE] `IRF-GLOBAL-002` p.2 |
| 3 | Context | NSE, NIFTY 50, intraday, 5-minute chart [VE] p.2 |
| 4 | Trend conditions | **None stated.** No trend/MA filter appears anywhere in the IRF guide. |
| 5 | Reference levels | IRH/IRL = high/low of the 09:15–09:20 candle **wicks included**, final only at 09:20 [VE] `IRF-GLOBAL-001` pp.2–4. Recent support / recent resistance [VQ] pp.3, 8, 11. |
| 6 | Previous-day requirements | None. |
| 7 | Opening conditions | None beyond the first candle defining the range. |
| 8 | Candle formation | Red = close<open; green = close>open [VE] p.3. M3 sweep candle: red, high>IRH, ≈60–70 % of its upper wick above IRH [VQ] p.12. |
| 9 | Exact entry confirmation | **M1** candle *b* closes > IRH, *the very next* candle closes back inside the range [VE] pp.5–6. **M2A** a later candle closes < recent support [VE]. **M2B** a red candle closes back < recent resistance after price traded above it [VE]. **M3** red sweep candle closes < recent support — *compulsory* [VE] pp.11–12. |
| 10 | Entry timing | At the **close** of the trigger candle in all methods (pp.5, 8, 9, 11, 14). "Closes confirm; wicks do not" (p.14). |
| 11 | Invalidation | M1: next candle closes ≥ IRH (p.6). M2: red candle alone, price still above resistance, no close above IRH, immediate close back inside ⇒ it is M1 (p.9). M3: sweep that closes above support, wick that barely clears IRH, trending advance instead of compression (p.12). No expiry stated [MS]. |
| 12 | Stop-loss | 35 or 40 "according to the most recent opposite (green) candle" (p.2; p.14: 35 if distance below 35, 40 if above) [VQ]; worked example p.10: green candle within 35 ⇒ 35. Distance measurement and d = 35 not defined [MS]. Never widen (p.14) [VE]. |
| 13 | Target | **60 from entry, identical for all three methods** [VE] pp.1, 2, 13, 14. Units: price distance on the instrument (p.2). |
| 14 | Trade management | Not in the IRF guide; the performance report adds T1 = 27 / breakeven (see `execution_rules.md`). |
| 15 | Alternative entry methods | M1, M2 (A: support break, B: resistance break), M3. Kept separate in code (`IRFStrategy._method1/_m2_step/_method3`). |
| 16 | Exceptions | p.14 card says M1 triggers on "the next candle **or following candle**" [CF `IRF-M1-C001`]; p.14 card adds "Or an Higher price rejection candle also works" to M3 [MS `IRF-M3-C001`]. |
| 17 | Missing definitions | recent support/resistance numerics; "small candles" & how many; "extends further"; Method 2 expiry; scope of M1 (first breakout only vs every pair); 35-vs-40 measurement; trades/day; time window. → `AMB-IRF-01…13` |
| 18 | Mathematical specification | §6 below. M1: `Close[b]>IRH ∧ IRL ≤ Close[b+1] < IRH`. M2A: `Close[i] < S`. M2B: `Red[i] ∧ Close[i] < R ∧ ∃m∈(j,i]: High[m]>R`. M3: `Red[s] ∧ High[s]>IRH ∧ share∈band ∧ Close[s] < S`. |
| 19 | State machine | `WAITING_FOR_SETUP → SETUP_DETECTED (breakout close) → WAITING_FOR_CONFIRMATION (M1 window passed; M2 path) → SIGNAL_CONFIRMED / SETUP_INVALIDATED`; M3 is a one-candle sweep attempt. Illegal order or time-reversal raises `IllegalTransition`. |
| 20 | Tests required | p.6 M1 worked example; p.10 M2B example (24,081.75 / 24,128.75 / 24,123.50 → SL 24,158.50, T 24,063.50); p.12 wick illustration (65 %); every "What does not qualify" bullet; look-ahead; gaps; EOD-incomplete → `tests/test_phase2_irf.py` (29 tests) and the boundary tests in `tests/test_phase2_boundaries.py`. |

Method 2 vs Method 3 (p.13): M2 needs a **close** above IRH and accepts support *or* resistance; M3 involves a **wick** above IRH, a 60–70 % criterion and a *compulsory* support break. They are never merged.

## 2. ORB — Opening Range Breakout *(ORB_Strategy_Rulebook-2.pdf)*

| # | Item | Content |
|---|---|---|
| 1 | Concept | Take the 09:20 close of the first candle as a confirmed breakout through a key level, in an established trend (pp.1–2). |
| 2 | Direction | **Both**; mirrored rules [VE] `ORB-GLOBAL-002` p.1 |
| 3 | Context | NIFTY 50, decision at **09:20** after the first candle closes; "never pre-empt the close" [VE] pp.2–3 |
| 4 | Trend | Established up/downtrend required for M1 and M2; **not** for the Gap/200 DMA setup "if conditions qualify" (pp.1, 12). Price above/below the **200 EMA** is "a basic confirmation, supported by bullish structure" (pp.3–4) [VQ]. |
| 5 | Reference levels | M1: previous-day resistance (long)/support (short) [VQ — "resistance" undefined]. M2: inner level inside the previous day's range + trendline [MS]. Gap setup: the **200 DMA** [CF terminology]. |
| 6 | Previous-day requirements | Previous-day level (M1); previous close for the gap (Gap setup); previous day's range (M2). |
| 7 | Opening conditions | Gap **required** only for the Gap/200 DMA setup (p.12). |
| 8 | Candle formation | Preferred: large body, close near the extreme, small wick against the trade; Conditional: pin bar (right position & close); Reject: strong wick against the trade (p.10) [VQ]. |
| 9 | Exact entry confirmation | 09:15 candle **breaks and closes beyond** the level [VE] pp.3–4, 12; Gap: closes beyond the MA (a candle that only crosses it does not qualify) [VE] p.8. |
| 10 | Entry timing | 09:20, after the first-candle close (pp.3, 11). Fill price not stated [VQ → reference = close]. |
| 11 | Invalidation | Wick-only break; weak/rejection candle; near the EMA without a convincing close (M2); "excessively extended" gap / strong rejection wicks (Gap) (pp.9, 10). |
| 12 | Stop-loss | **30** fixed [VE] pp.1, 2, 11, 12 |
| 13 | Target | **60** fixed (RR 1:2) [VE] same pages |
| 14 | Trade management | None in the rulebook. |
| 15 | Alternative methods | Method 1 (previous-day level), Method 2 (inner level + trendline), Gap/200 DMA — separate (`ORBStrategy._method1/_method2/_gap_setup`). |
| 16 | Exceptions | Gap setup is an exception to the established-trend rule (p.9); not every gap through the DMA qualifies. |
| 17 | Missing definitions | "established trend"; previous-day resistance; inner level; trendline construction; "near" and "convincing"; "excessively extended"; strong/pin/rejection thresholds; units of 30/60 (p.11 asks the user to decide). → `AMB-ORB-01…09` |
| 18 | Mathematical specification | M1 long: `High[0]>L ∧ Close[0]>L ∧ StrongBull(c0) ∧ Trend(LONG)` with `L = previous-session high` (PROPOSED level). Gap long: `PrevClose < MA_prev ∧ Open > MA ∧ Close[0] > MA ∧ (StrongBull ∨ BullPin) ∧ ¬UpperRejection`. |
| 19 | State machine | One decision at 09:20: `SETUP_DETECTED` (level broken) → `SIGNAL_CONFIRMED` / `SETUP_INVALIDATED` (trend / quality / MA gates). |
| 20 | Tests required | breakout vs wick-only; close == level; weak/rejection candle; trend modes; warm-up; unverified previous session; gap crossing vs not; excess-gap filter; M2 research variant (long & short) → `tests/test_phase2_orb.py`. |

**Readiness caveat.** ORB Method 2 has no objective inner-level or trendline definition in the source ("inner level drawn approximately", p.7). It is implemented **only as a labelled `RESEARCH_VARIANT`**. The Gap setup carries an unresolved *mandatory* rule (excessive extension) and is also `RESEARCH_VARIANT`.

## 3. PDR — Previous Day Resistance, gap-up support retest *(PDR_Strategy_Guide.pdf)*

| # | Item | Content |
|---|---|---|
| 1 | Concept | Yesterday's resistance zone acts as support after a gap-up (p.1). |
| 2 | Direction | **Long** [VE] p.1 |
| 3 | Context | 5-minute candles; NIFTY 50 |
| 4 | Trend | None stated (the example charts show a 200 EMA but no rule uses it). |
| 5 | Reference level | A **zone**, not a line: previous day's high where price peaked and reversed; box from the candle body to the top of the upper wick; extended to the next day (pp.1–2) [VQ] |
| 6 | Previous-day requirement | "Clear high and reversal identified" (checklist p.3) [VQ — unmeasurable] |
| 7 | Opening | Must open **gap up**; do not enter at the open (pp.1–3) [VE] |
| 8 | Candle formation | Green candle after the zone test [VE] |
| 9 | Exact entry confirmation | Zone tested (wick touches / body touches / enters / very close) **then** a green candle → long on that confirmation (pp.2–3) [VQ] |
| 10 | Entry timing | "on that confirmation" — during vs after the candle close **not stated** [MS] → signal at candle close (only time colour is known) |
| 11 | Invalidation | Price keeps rising without returning to the zone ⇒ no setup (p.2) [VE]. Nothing else stated. |
| 12 | Stop-loss | 35 **or** 40 "depending on the situation"; choose before entering, don't move (pp.1–2). **Selection criterion absent** [MS] ⇒ `PDR_STOP_SELECTION = UNRESOLVED` |
| 13 | Target | **70 points** fixed [VE] pp.1, 2, 3. (Conflict with the performance report: see `execution_rules.md`.) |
| 14 | Management | none |
| 15 | Alternative methods | none (single method) |
| 16 | Exceptions | none |
| 17 | Missing | body-side boundary of the zone; tie-break among candles sharing the high; "very close"; reversal clarity; same-candle green; entry timing; stop selection; re-entries. → `AMB-PDR-01…07` |
| 18 | Mathematical specification | `Z=[zl,zh]`, `zh=High(pdh candle)`, `zl=min(O,C)` (ZONE_FULL) ; `Open[0]>PrevClose`; `Open[0]>zh` (PROPOSED PDR-011); interaction `Low[j] ≤ zh + prox`; signal at first `k>j` with `Close[k]>Open[k]`. |
| 19 | State machine | `WAITING_FOR_SETUP → SETUP_DETECTED (zone test) → WAITING_FOR_CONFIRMATION → SIGNAL_CONFIRMED` |
| 20 | Tests | gap-up/test/green; no-return; gap-down; open not above zone; same-candle green; proximity candidates; zone boundary candidates; reversal filter; single-signal-per-session → `tests/test_phase2_pdr_pds_rf.py` |

## 4. PDS — Previous Day Support, gap-down resistance retest *(PDS strategy.pdf)*

| # | Item | Content |
|---|---|---|
| 1 | Concept | A level that held as support yesterday acts as resistance after a gap-down; **not a breakdown strategy** (p.2) |
| 2 | Direction | **Short** [VE] |
| 3 | Context | NIFTY 50, 5-minute, intraday (p.1) |
| 4 | Trend | None stated |
| 5 | Reference level | Rectangle covering the relevant candle **body and lower wick** of yesterday's low; "do not use a single horizontal line" (p.3) [VQ] |
| 6 | Previous-day requirement | previous-day low where price took support and moved up |
| 7 | Opening | Must open **gap down**; do not enter on the gap alone (pp.3–4) [VE] |
| 8 | Candle formation | M1 good red candle; M2 red pin bar with higher-price rejection; M3 break of a small support (pp.4–5) [VQ] |
| 9 | Exact confirmation | Price rises from below and **tests** the zone (touch / enter / very close), then: **M1** the *first red candle at the zone* is a good candle; **M2** it is a red HPR pin bar (long upper wick into/above the zone); **M3** if the first red candle is not satisfying, wait for a small support to form and break (pp.4–5) |
| 10 | Entry timing | not specified [MS] (author's own open item p.6) → signal at candle close |
| 11 | Invalidation | No rally into the zone ⇒ no trade; weak red candle ⇒ not taken (quality rule p.5) |
| 12 | Stop-loss | 35 or 40 "based on the recent green candle's distance" (p.2, p.5) [VQ]; measurement and d = 35 are the author's own open items (p.6) |
| 13 | Target | **70 points**, all three methods [VE] pp.1, 2, 4, 5, 6 |
| 14 | Management | none |
| 15 | Alternatives | **Method 1 / Method 2 / Method 3**, separate (`PDSStrategy._scan`) |
| 16 | Exceptions | M3 only "when the first red candle is not satisfying" (stand-alone use is an author open item) |
| 17 | Missing | all author-listed items on pp.5–6: good-candle body, HPR ratio, small-support size, close vs touch, M3 trigger scope, d = 35, distance measure, entry timing. → `AMB-PDS-01…08` |
| 18 | Mathematical specification | `Z=[low(pdl candle), max(O,C)]`; `Open[0]<PrevClose`; `Open[0]<zl` (PROPOSED PDS-006); at zone: `High ≥ zl−prox ∧ Low ≤ zh+prox`; M1 `StrongBear(r)`; M2 `BearPin(r) ∧ High[r]≥zl`; M3 `Close[i] < S` (CLOSE) / `Low[i] < S` (TOUCH). |
| 19 | State machine | `WAITING_FOR_SETUP → SETUP_DETECTED (first test) → WAITING_FOR_CONFIRMATION (M1/M2 on first red; else weak → M3 path) → SIGNAL_CONFIRMED` |
| 20 | Tests | M1, M2, M3, touch-vs-close, not-a-breakdown, gap-up day, only-first-red, stand-alone variant, open-not-below-zone, single-signal → `tests/test_phase2_pdr_pds_rf.py` |

## 5. RF — Reverse Failure *(RF strategy.pdf)*

| # | Item | Content |
|---|---|---|
| 1 | Concept | "The opposite of the IRF strategy" (p.2): gap up, dip **below** the opening candle's low, close below it, come back inside. |
| 2 | Direction | **Never stated.** Implied **long** by "uptrend only" + "opposite of IRF" + the p.9 long-position chart [PR `RF-012`] |
| 3 | Context | 5-minute; NIFTY 50 |
| 4 | Trend | Strictly an **already-established** uptrend; trading above the 200 EMA is a basic filter, "never the only proof" (pp.2, 4, 5) [VQ]; previous downtrend + sudden gap above the EMA ⇒ reject (p.5) |
| 5 | Reference levels | RF High/Low = first 5-min candle high/low **wicks included** [VE] pp.2–3 |
| 6 | Previous-day requirement | Yesterday's high/low: the gap-up **open** must be within yesterday's range; above yesterday's high ⇒ reject [VE] pp.2, 7 |
| 7 | Opening | Gap **up** required; gap down ⇒ reject; "No gap up, no RF" (pp.4, 6) [VE] |
| 8 | Candle formation | a **proper close** below RF Low (a wick is not enough) [VE] p.2 |
| 9 | Exact confirmation | in order: uptrend → gap-up within range → close below RF Low → price returns **inside** the original range (p.4) [VQ for "returns inside"] |
| 10 | Entry timing | **OPEN** (p.8) [MS] → reference = close of the return-inside candle |
| 11 | Invalidation | gap down; gap beyond yesterday's range; previous downtrend + sudden gap; gap up with no break-and-return (pp.6–8) |
| 12 | Stop-loss | 35–40, "what is logical"; fixed vs candle-extreme not stated — rated PARTIAL by the author (p.8) [MS] |
| 13 | Target | **OPEN** (p.8) ⇒ **`RF_TARGET_STATUS = UNRESOLVED`**; not defaulted to 60 or 70 anywhere in code |
| 14 | Management | none |
| 15 | Alternatives | none (single method) |
| 16 | Exceptions | none beyond the rejection table |
| 17 | Missing | direction; entry price; target; stop selection; "established uptrend" structure; return-inside definition; (derived) the report implies some RF stops below 35. → `AMB-RF-01…07` |
| 18 | Mathematical specification | `RF_H=High[0]`, `RF_L=Low[0]`; `c0 = min{c≥1: Close[c] < RF_L}`; return `k>c0` with `RF_L ≤ Close[k] ≤ RF_H` (R1); gates `Open>PrevClose ∧ PrevLow ≤ Open ≤ PrevHigh ∧ Trend(LONG)`. |
| 19 | State machine | `WAITING_FOR_SETUP → SETUP_DETECTED (close below) → WAITING_FOR_CONFIRMATION → SIGNAL_CONFIRMED`; gates evaluated in document order at activation. |
| 20 | Tests | full sequence; unresolved target; wick-only; wrong order; gap down; gap above yesterday's high; previous downtrend; warm-up; return-inside candidates; EOD-incomplete |

**A missing RF target does not block RF signal detection** — the signal record carries `RF_TARGET_STATUS: UNRESOLVED` and `rule_ids_unresolved: [RF-009, RF-011]`.

---

## 6. Mathematical definitions

Candle `c = (O, H, L, C)`, all on completed 5-minute bars built from 1-minute rows labelled by their start minute.

| Quantity | Definition | Status |
|---|---|---|
| Body, range | `B=|C−O|`, `R=H−L` | exact |
| Upper / lower wick | `UW=H−max(O,C)`, `LW=min(O,C)−L` | exact |
| Ratios | `B/R`, `UW/R`, `LW/R`; if `R=0` all ratios are 0 and no shape qualifies | exact (safe zero-range) |
| Red / green | `C<O` / `C>O`; `C=O` is neither | [VE] IRF p.3 |
| Opening range | `IRH=H₀`, `IRL=L₀` of the 09:15 candle, usable at 09:20 | [VE] |
| Strong bullish | green ∧ `B/R ≥ a` ∧ `UW/R ≤ b` | PR: (a,b) ∈ STRICT (.70,.15) · **MODERATE (.60,.20)** · LOOSE (.50,.25) |
| Strong bearish | red ∧ `B/R ≥ a` ∧ `LW/R ≤ b` | PR (same table) |
| Bearish pin (HPR) | `UW/R ≥ w ∧ B/R ≤ β ∧ LW/R ≤ o` | PR: STRICT (.70,.25,.10) · **MODERATE (.60,.33,.15)** · LOOSE (.55,.40,.20) |
| Bullish pin | mirror using `LW` | PR |
| Rejection wick | long trade: `UW/R ≥ r`; short: `LW/R ≥ r` | PR: STRICT .25 · **MODERATE .33** · LOOSE .40 |
| Higher-price rejection | = bearish pin / upper rejection above | PR |
| Swing low/high (k) | `L[j] ≤ L[j±m]` ∀ m≤k (resp. `H`); **confirmed only when candle j+k has closed** | PR: k=1 default, k=2 candidate |
| Recent support (IRF) | latest confirmed swing low after the breakout / last-N lows | PR: **SWING_K1** · SWING_K2 · LAST_N3 |
| Recent resistance (IRF M2B) | earliest swing high at/after the breakout candle | PR: **FIRST_PUSH_TOP** · LATEST_SWING_HIGH |
| Support/resistance *zone* (PDR/PDS) | PDR `[min(O,C), H]` of the previous-day-high candle; PDS `[L, max(O,C)]` of the previous-day-low candle | PDS [VQ]; PDR-lower-boundary PR: **ZONE_FULL** · ZONE_WICK |
| Gap | `Open[09:15] − PrevClose`; UP if `> g`, DOWN if `< −g`, `g = 0` default; `PrevClose` = official 15:30 print | PR |
| Trend | see `TrendMode`: **EMA5M_PREV_SESSION** · EMA5M_BASIC · EMA5M_PREV_3_SESSIONS · SMA200_DAILY · EMA200_DAILY | PR |
| Breakout confirmation | `Close` beyond level (not `High`) | [VE] |
| Retest / zone test | `Low ≤ zh + prox` (PDR) / `High ≥ zl − prox` (PDS), `prox` 5 pts default (candidates 0 / 5 / 10) | PR |
| Liquidity sweep | red candle with `High>IRH`, wick share `(H−IRH)/(H−O)` in band | formula [VE] p.12; band PR: **BAND_60_70** · MIN_60 · BAND_55_75 |
| Compression | previous `N` candles inside `[IRL, IRH]` (`N=2`); variant C2 adds `range ≤ 0.5·(IRH−IRL)` | PR |
| Price extension (IRF M2) | E1: a later `High > High[b]`; E2: a later `Close > IRH` | PR: **E1** · E2 |
| Moving average | EMA(200) of completed 5-min closes, SMA-seeded, NaN until 200 candles; daily SMA/EMA(200) of official closes up to the **previous** session | exact; which one the author means is `AMB-ORB-01` |

### 200 EMA vs 200 DMA (Task 6)
* ORB uses "200 DMA / EMA" (p.2), "200 EMA" (pp.3, 5, 7) and "200 DMA" (pp.1, 8, 9, 12) for the line plotted on its 5-minute charts. RF uses "200 EMA" throughout.
* **Hard evidence:** the PDR example charts (pp.3–4) carry a TradingView legend `NIFTY50-INDEX · 5 · NSE` with the indicator **`EMA 200 close`** on the 5-minute timeframe. A 200-period EMA of 5-minute closes spans ≈ 2.7 sessions; it is not a 200-day average.
* **Conclusion:** the author is using "DMA/EMA" loosely for a 200-period EMA on the 5-minute chart. This is **evidence, not proof**; the two readings give different answers on the same bar (tested), so both are implemented as separately labelled candidates and **none is equated with the other**. Default `EMA5M_*`.
* **Warm-up:** EMA(200) of 5-min bars needs 200 completed candles (≈ 3 sessions). A daily 200-day average needs 200 prior daily bars — with Phase 1 data it exists for only the **last 47 of 247 sessions** (from 2026-06-25). No partial initialisation is ever used.
* "Established uptrend/downtrend" is not numerically defined in any document (ORB p.3 "supported by bullish price structure"; RF p.5 "must already be demonstrated"). The default `EMA5M_PREV_SESSION` encodes only RF p.5's explicit *invalid* example (previous session below the EMA); stronger structure tests are not invented.

## 7. Data caveat found by the independent review
From 2026-08-03 every session's last ~14 minutes are a frozen feed (identical price, then a 150–200-point catch-up bar). Those rows are excluded, the 15:15/15:20/15:25 candles are dropped, and the following session is not evaluated by strategies that need a previous-day close or zone. See `agent_review_report.md` (C-1) and `reports/phase2/dataset_verification.md` (`feed_quality`).

## 8. Engine behaviour under the default proposals (descriptive only)
See `reports/phase2/signal_counts_default.md` — counts of emitted records per method. They are **not** used to choose interpretations and **must not** be compared to the 189-trade report to tune thresholds.
