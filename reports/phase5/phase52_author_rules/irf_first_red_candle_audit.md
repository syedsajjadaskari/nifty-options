# IRF - 'the first red candle that creates the support level' (audit and candidates)

Signal-level evidence only: no controller, no fills, no P&L and no revised backtest were run. Candidates are NOT approved rules.

## Which methods use a red-candle support reference

| method | reference in the guide | uses a support created by a red candle? | candidate applied? |
|---|---|---|---|
| Method 1 | the failure candle closes back inside the initial range | no | no |
| Method 2A | 'recent support' = a pullback low left behind by the extension; a red candle must form first; entry when a candle closes below the support (IRF-M2A-001/002) | YES - the red candle is a precondition and the support is the pullback low | YES: support taken from the first red candle |
| Method 2B | 'recent resistance' = the top of the first push; a red candle closes back below it | no (a resistance, not a support) | no (a resistance-side wording would be a separate decision) |
| Method 3 | 'recent support formed by the preceding candles'; the red sweep candle itself must close below it | no (the support precedes the sweep candle) | no |

## What is established and what is not

Established: the engine already tracks the FIRST red candle after the extension (`red_candle_index`) and never replaces it with a later one. The Phase 3.6 engine does not tie the support level to that candle: it takes the latest swing-low fractal (SWING_K1).
NOT established (the author's wording and the guide are silent): whether the level is the red candle's LOW, its BODY LOW, or a broader local support. Per the brief nothing is invented: both candle-based levels are offered as candidates and the active rule is unchanged.

## Candidate engines (`IRFFirstRedStrategy`, opt-in)

Support for Method 2A = the first red candle's low (`phase52-cand-irf-first-red-low`) or its body low (`phase52-cand-irf-first-red-body-low`); the entry is the first LATER candle that closes below it, activated at that close. In `BASELINE_SWING` mode the class reproduces the frozen engine exactly (asserted on all 247 sessions and on synthetic candles).

## Signal changes (confirmed IRF signals, 2025-09-01..2026-08-31)

| configuration | earlier | later | added | removed | involving a Phase 3.6 executed signal |
|---|---|---|---|---|---|
| phase52-cand-irf-first-red-low | 156 | 69 | 163 | 98 | 17 |
| phase52-cand-irf-first-red-body-low | 197 | 68 | 242 | 91 | 21 |

Confirmed IRF signals: frozen 874, low candidate 939, body-low candidate 1025 (re-arming after a confirmation lets more attempts complete; signal counts do not predict executed trades). Method 2B signals can also change because an earlier or later 2A confirmation changes when an attempt ends; Methods 1 and 3 are history-independent and identical (audit check).

## The 42 executed Method-2 trades (the Phase 5.1 '37 reading disagreements' are the 37 flagged rows)

For each trade `irf_first_red_comparison.csv` shows the old reference (swing support candle / push-top candle and level), the first qualifying red candle with its OHLC, the support level under both definitions, the candidate break confirmation and the signal-time change. The first IRF signal of the session changes for 17 of 42 trades under the LOW candidate and 25 of 42 under the BODY_LOW candidate; the two definitions give a different answer on 12 trades, which is why the level cannot be chosen by default.

### Dated handwritten examples (source evidence)

| date | example | author's stated direction | baseline signal | old reference | first red candle (OHLC) | LOW candidate | BODY_LOW candidate | LOW vs the author's direction |
|---|---|---|---|---|---|---|---|---|
| 2025-09-01 | AC01 | earlier (at the resistance itself) | 09:50 Method 2B | resistance 24546.55 (09:35) | 09:35 24540.9/24546.55/24532.15/24536.75 | same time and method | earlier (09:50 -> 09:45 Method 2A) | does not agree |
| 2025-09-10 | AC03 | not stated | 10:40 Method 2B | resistance 25017.1 (09:45) | 09:45 25012.85/25017.1/24992.7/25003.7 | same time and method | earlier (10:40 -> 09:55 Method 2A) | direction not stated by the author |
| 2025-09-22 | AC08 | earlier | 11:10 Method 2A | support 25298.4 (10:50) | 09:50 25315.25/25317.35/25284.65/25305.1 | later (11:10 -> 11:25 Method 2A) | earlier (11:10 -> 11:05 Method 2A) | does not agree |
| 2025-09-29 | AC09 | earlier | 10:40 Method 2B | resistance 24767.05 (10:00) | 10:00 24758.0/24767.05/24751.85/24753.15 | earlier (10:40 -> 10:10 Method 2A) | earlier (10:40 -> 10:10 Method 2A) | agrees |
| 2025-11-13 | AC20 | not stated | 12:35 Method 2A | support 25976.15 (12:15) | 10:35 25925.4/25928.85/25920.25/25924.2 | later (12:35 -> 14:05 Method 2A) | later (12:35 -> 14:05 Method 2A) | direction not stated by the author |
| 2025-11-26 | AC26 | not stated | 10:30 Method 2A | support 26074.75 (10:10) | 09:35 26011.45/26015.75/25999.1/26003.1 | no IRF signal | no IRF signal | direction not stated by the author |
| 2025-12-15 | AC34 | not stated | 12:15 Method 2B | resistance 26021.05 (11:55) | 12:00 26016.2/26019.2/26010.15/26013.05 | same time and method | same time and method | direction not stated by the author |

The remaining executed Method-2 trades have only the call statement as source evidence. **Source supports the change? Partly**: the author's intent (a first-red-candle reference) is stated by the call and by repeated handwritten remarks; the level and the method scope are not. No outcome (profit) was compared.

## Remaining decisions

O4: the level (low / body low / local support), the scope (2A only, or also 2B / Method 3), whether the break must be by a red candle, and what 'first' means: the first red candle after the EXTENSION (the engine's reading) or after the BREAKOUT (differs on many Method-2 signals; the independent reviewer counted 13 of the 42 executed Method-2 trades). The guide itself orders the steps pullback low, then red candle, then close below the support, so 'support = the first red candle' is a re-reading of the guide.
