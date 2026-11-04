# Phase 2.2 - rule verification against the original documents

**Status: nothing in this file is APPROVED by the strategy owner except the stop-loss research baseline (section 1).** Labels: **VE** verified explicit · **VQ** verified, needs a number · **CF** conflicting · **UN** unresolved · **PR** proposed for review · **UA** user-approved.

## 0. What was inspected, and by whom

* **Independent reading.** A separate agent read the five strategy PDFs *before* it looked at any earlier AI interpretation, extracted every embedded chart at native resolution, measured candle shapes and drawn zones by pixel (price axis tags, position boxes, and candle prices from the repo's 1-minute data), and only then compared itself with `decision_records.yaml`. Its full report is kept verbatim: `phase22_source_research_raw.md`.
* **PDFs actually read:** IRF (17 pp.), ORB (13 pp.), PDR (4 pp.), PDS (7 pp.), RF (9 pp.), including the figures on every page; the performance report (as extracted text; paragraphs `[P1]-[P50]`); journal rows for times and counts only.
* **Not inspected (limits of that reading):** the report DOCX and journal XLSX were not compared cell by cell in this phase (Phase 2.1's reconciliation stands); IRF p.1/p.4 and Fig 3-4 only skimmed; ORB p.7/12/13 charts have no price axis so HH/HL there was judged visually; PDS examples are dated only tentatively; PDR example 5 is undated.
* **Not re-opened:** the closing-auction data question (owner-confirmed; the data is untouched).

## 1. The owner's confirmed decisions (USER_APPROVED)

| item | value | note |
|---|---|---|
| Stop IRF / PDR / PDS / RF | **35 index points** (research baseline) | **not** the author's selection rule. IRF and PDS guides say 35-or-40 *by the distance of the recent green candle* (threshold and measurement left open by the guide itself, PDS p.6); PDR and RF give no rule. 35 overrides that conditional rule for research. |
| Stop sensitivity variant | **40 points** for those four | compared only in Phase 3; not compared here |
| Stop ORB | **30** (VERIFIED_EXPLICIT, ORB p.1) | preserved in every variant |
| Closing-auction data | legitimate market structure | candles kept; execution treats them as non-fillable (`phase22_execution_policy.md`) |

All stop distances live only in `params.TradeConfig` (`STOP_BASELINE`, `STOP_ALTERNATE`); `policy_for` reads them from there.

## 2. Verdict on each recommendation in the Phase 2.2 brief

| recommendation | verdict from the PDFs | what the code does |
|---|---|---|
| Trade management: 6 lots x 65, T1 27 on 3 lots, rest at T2, stop to entry after T1 | **VE** performance report `[P2] [P7] [P11]`. "T2 60 or 70, as recorded" - **no per-strategy rule in the report** | implemented as stated |
| T2: IRF 60, ORB 60 | **VE** (IRF p.1-2, 13-14; ORB p.1-2, 11-12) | 60 |
| T2: PDR 70, PDS 70 | **VE** in the guides (PDR p.1-2; PDS p.1-5) **but CF** with the report: 1 of its 6 PDR winners and 2 of its 3 PDS winners are at 60 | 70, status **`CONFLICTING`**; the conflict text is carried in `ExitPolicyConfig.conflicts` and in every signal's `execution_config.target_2_conflict`, never overwritten |
| T2: RF 60 | **NOT STATED**: RF p.8 "Target - OPEN". Weak support: the p.9 chart box reads 60.80, the report's arithmetic | 60 as a *configurable research value*, `RF_TARGET_STATUS = PROPOSED_FOR_REVIEW`; `rf_t2_points=None` restores "unresolved" |
| 200 **EMA** of 5-minute closes | supported only by the PDR chart legends (`EMA 200 ... 24,582.02`, `24,925.18` on a 5-minute chart, reproduced to 0.005 point in Phase 2.1). ORB writes "200 DMA", "200 EMA" and "200 DMA / EMA" | EMA(200), 5-minute, SMA-seeded, warm-up from 2025-07/08 |
| **Trend = close > EMA200 and the last two confirmed swing highs rising and the last two swing lows rising** | close > EMA: stated as a *basic filter that is never sufficient* (RF p.5 "never the only proof"; ORB p.3-4 "supported by bullish price structure"). Rising swing **lows**: partly (ORB p.5, p.7: the trendline connects swing lows). **Rising swing highs / HH-HL as the test: NOT STATED. The 2-before/2-after swing: NOT STATED. Figures partly CONTRADICT it**: in ORB p.7's annotated Method-2 long chart (also p.12 image 1) the inner resistance broken at 09:20 sits far *below* a flat plateau of earlier highs, i.e. the recent swing highs are lower while the swing lows rise - the author's own "established uptrend" example would fail a strict HH rule. RF p.3/p.5 clip-art staircases (HH+HL) illustrate it but state no rule. | implemented exactly as recommended and made the default `trend_mode="STRUCTURE_EMA_SWING2"`, **PR**; it uses *previous-session information only*; the older EMA-only modes remain selectable. **Decision for the owner** (phase22_author_decisions.md #2). |
| Swing definition k=2 strictly beyond, known only after 2 more candles close | **NOT STATED**. IRF's own worked examples (p.6, p.10) reproduce with the *3-candle* swing, not k=2 | `swing_k=2` for the trend; IRF support/resistance keep the 3-candle swing (`SWING_K1`) because switching to k=2 breaks the IRF worked-example fixtures; k=2 stays a selectable candidate |
| Strong candle body >= 60%, opposing wick <= 20% | **NOT STATED** anywhere (ORB: "strong green body, small upper wick"; PDS: "good body", numerically undefined by the guide itself, p.5). Consistent with, and looser than, every drawn strong candle (ORB p.10 ~93% body; PDS Fig 3 83%; real PDS entries 71-76%) | `MODERATE` preset = the recommendation |
| Small candle body <= 30% of range | **NOT STATED and NOT SUPPORTED as a body/range rule**: IRF Fig 5's "small candles" have bodies of 23%, 37%, 23%, 37% of their own range (their *ranges* are only ~17-19% of the initial range); PDS "weak" candles have bodies of 68-83% - "small" means small *absolute size* | available as variant `m3_compression_def="C3"`; **default stays C1** (candles inside the initial range) |
| Pin bar: rejection wick >= 2x body and close in the favourable 30% | **NOT STATED** (PDS p.5: "wick-to-body ratio is not specified"). Consistent with every drawn pin bar (3.6x-3.9x body, close in the lowest 6-8%) - the 2x/30% limits are the lenient edge | `OWNER_2X_CLOSE30` is the default; the older ratio presets remain |
| IRF M1: very next candle vs the quick-reference card | detailed pages say "very next candle" (p.1, 5, 6, 9, 13); **only the p.14 card** says "next candle or following candle". No figure or example shows a following-candle case | detailed pages used; conflict **CF, not resolved**; `m1_max_candles_after_breakout=2` is the variant |
| IRF M2: A (support) and B (resistance) independent | **VE** p.8-9 ("either break"; "insisting on a support break only" does not qualify) | separate methods, not both required |
| IRF M3: compression, sweep, ~60-70% of the upper wick above IRH, **compulsory** support break | **VE** p.11-12; the number of small candles is not stated | support break not weakened; zero confirmed signals is reported as is |
| IRF repeated entries / time limit / re-arming | **NOT STATED in any guide** | complete event log + three labelled evaluation policies |
| ORB three setups kept separate; 09:20 decision; stop 30 / target 60 | **VE** (ORB p.1-2, 11-12). Fill price **not stated** | separate methods; causal fill convention in `phase22_execution_policy.md` |
| ORB gap setup: "excessively extended" gap | **NOT STATED** (no number, p.9) | stays unresolved; `gap_max_points` is only an off-by-default research knob |
| PDR zone = confirmed reversal structure rather than the absolute high | The guide says only "the high where price reached a peak and then reversed ... note the candle's body and upper wick" (p.1), "upper boundary: highest point of the upper wick; lower boundary: the relevant candle-body level" (p.2). **Charts 1, 2 and 4 each sit on the previous session's highest-high candle; chart 3 sits on a shelf of equal highs and skips the lone 14:50 spike.** See section 3. | candidate A (default), B, C implemented; none reproduces chart 3 |
| PDR zone lower edge | the drawn zones are **[body top, wick tip]**, not [body bottom, wick tip] (chart 4: 26,061.8-26,074.2 vs candle body top 26,061.50 / high 26,074.55, within ~1 point - but chart 4 has no price axis and is dated only by shape-matching to the journal, so treat it as consistent, not exact; a second reviewer measured charts 1 and 2 from pixels and also found the bottom edge at the body top, +1.4 and +2.1 points) | `zone_lower_boundary="ZONE_WICK"` is now the default; the earlier `ZONE_FULL` is a candidate |
| PDR entry: strict zone intersection first, near-touch as a separate proposal | the guide lists wick/body touch, entering the zone, or "very close" with **no number** (PDR p.2, PDS p.4); all four dated PDR charts actually *entered* the zone before the green entry candle, so none needs the "very close" clause | `zone_proximity_points=0` (true range intersection, both sides); 5 is the labelled near-touch variant |
| PDR entry candle quality | **the guide asks only for "a green candle"**; a body>=60% rule would reject 3 of the 4 author entries (body 57%, 32%, 63%, 45%) | PDR uses colour only |
| PDS: strong red / red HPR pin bar / small-support break kept separate; zone body + lower wick; not a perfect mirror of PDR | **VE/VQ** PDS p.2-5. Differences from PDR: quality-qualified entry, an explicit 35/40-by-distance stop rule, an explicit "not a breakdown strategy" rule | three methods kept; `pds_zone_upper_boundary=ZONE_FULL` (text: "both the body and the lower wick belong to the zone"). The three PDS example zones look thin (3.6-10 pt, i.e. wick-only) but are dated tentatively - low confidence, so the text wins |
| RF sequence: uptrend before the gap -> gap up -> open inside yesterday's range -> close below RF Low -> return inside | **VE** (RF p.2, 4, 6-7). **Direction is never stated in words** (long is inferred); "return inside" does not say close vs touch; entry price **OPEN**; stop "35 or 40 depending on what is logical" (no rule) | sequence as written; return = a candle *close* back inside the range (`R1`, PR); entry reference = that close (PR); long (PR) |

## 3. PDR zone: how the candidates compare with the author's drawn zones

Drawn zones are the researcher's pixel measurements (+-1 to 1.5 points); candidates are computed by `definitions.pdr_zone` from the *previous session only*. Chart 5 is undated and is not used. Profit was not used.

| chart (trade day / zone day) | drawn [bottom, top] | A + ZONE_WICK | A + ZONE_FULL | B (either boundary) | C |
|---|---|---|---|---|---|
| 1: 2025-09-02 / 09-01 | [24,632.0, 24,640.0] | [24,632.25, 24,635.00] **(max error 5.0, top only)** | [24,625.10, 24,635.00] (6.9) | = A | 17.0-19.3 off |
| 2: 2025-10-06 / 10-03 | [24,901.9, 24,905.6] | [24,899.80, 24,904.75] **(2.1)** | [24,896.10, 24,904.75] (5.8) | = A | ~60 off |
| 3: 2025-10-07 / 10-06 | [25,080.8, 25,084.4] | [25,077.25, 25,095.70] (**11.3**) | [25,057.10, 25,095.70] (23.7) | = A (the 14:50 spike is a confirmed swing high with a red candle after it) | 8.6-14.6 off |
| 4: 2025-11-20 / 11-19 | [26,061.8, 26,074.2] | [26,061.50, 26,074.55] **(0.35)** | [26,049.40, 26,074.55] (12.4) | = A | ~43-49 off |

Findings: (1) `A + ZONE_WICK` reproduces charts 1, 2 and 4; (2) B coincides with A on all four, C reproduces none; (3) **no mechanical candidate reproduces chart 3's shelf**, so *which candle marks the zone* stays open (PDR-D09, owner question #1); (4) with the strict defaults the engine emits a CONFIRMED PDR signal on the same candle the journal labels for charts 1, 2 and 4 (09:25, 09:30, 09:45) and an INVALIDATED record on chart 3 (open 25,087.55 lies inside the engine's 18.5-point zone). Dataset-wide, B differs from A on 198 of 247 sessions and C on 217 (C falls back to A on 16), so the choice matters for the signal list.

## 4. Corrections to earlier Phase 2.1 statements

1. `PDR-D01` / the master rule table said the zone runs from the body **bottom** to the wick; the guide's charts show body **top** to wick tip. Corrected (default and registry text).
2. `PDR-D09` said "Examples 1 and 2 are consistent with the engine's zone within chart-reading error"; that holds for the top edge but **not for the bottom edge** of the body-bottom zone (5.8-7 points off). With `ZONE_WICK` it holds.
3. `PDR-D06` listed drawn stops of 40.60 (chart 3) and 35.00 (chart 5) only; the dated charts also show ~30.6 (chart 1), 35.35 (chart 2) and ~35-36 (chart 4). A drawn stop of ~30.6 is neither 35 nor 40.
4. Entry-time convention (not recorded before): in all four dated PDR charts the entry tag equals the **close** of the 5-minute candle whose *start* label is the journal's Entry Time (09:25 / 09:30 / 09:20 / 09:45). So the journal time is the candle's start label and the reference price is that candle's close - consistent with the engine's signal candle.
5. The Phase 2.1 master said "entry at the close in all methods" citing IRF p.11 and p.14 for Method 3; neither page says "at the close" for M3 (p.12: "closes below recent support"; p.1: "on the support break").
6. `ORB-D01`..: "bullish structure" is "bullish price structure" in the PDF (p.3) - wording only.
7. **New data observation (`DATA-OPEN-001`, not resolved, nothing changed):** the vendor *daily* open differs from the first 1-minute open by more than 5 points on 98 of 247 sessions (up to 64), and equals the open drawn on the guide's own chart 1 (2025-09-02: daily open 24,653.00 vs first-minute open 24,683.25; the author's first candle is green, ours is red). Using the daily open would change the gap direction on 10 sessions and the first-candle colour on 13. This is separate from the closing-auction question and needs the owner (phase22_author_decisions.md #3).

## 5. Still not resolvable from the documents

Trades per day / time window / re-arming (all guides) · "very close" distance · "excessively extended" gap · the PDR rule for choosing 35 vs 40 and how the green-candle distance is measured for IRF/PDS (guides list this as open) · RF stop selection, entry price, target, direction, close-vs-touch for the return · PDS entry timing and small-support size · ORB fill price and Method-2 construction · which strategies use Target 2 = 60 vs 70 in the report · numeric definitions of the candle vocabulary · trend look-back and swing definition.
