# ORB - why the expected signals were missing (audit)

Signal-level evidence only: no controller, no fills, no P&L and no revised backtest were run. Candidates are NOT approved rules.

The Phase 5.1 audit found that on all 13 'ORB should have activated' dates the engine produced NO valid ORB signal; the controller therefore skipped nothing, and **no priority override of IRF was added**. This audit reconstructs each date and names the first failing rule.

Causes (colour direction of the first candle): {'METHOD2_TRENDLINE': 2, 'LEVEL_CONSTRUCTION (no previous-day level broken; Method 2 inner level undefined in the source)': 6, 'STRONG_CANDLE_THRESHOLD': 3, 'EMA_REQUIREMENT': 2}

| date | first candle O/H/L/C | colour | body % | uw % | lw % | prev high / low | EMA - close | Method 1 | Method 2 | Gap / 200 average | cause |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2025-09-11 | 24945.5/25002.1/24945.5/25000.8 | GREEN | 97.7 | 2.3 | 0.0 | 25035.35 / 24915.35 | -99.4 | NO_SETUP: first candle did not break and close beyond the previous-day | TRENDLINE_NOT_SUPPORTIVE | NO_SETUP: no gap in this direction | METHOD2_TRENDLINE |
| 2025-09-16 | 25079.5/25110.25/25072.25/25106.75 | GREEN | 71.7 | 9.2 | 19.1 | 25137.45 / 25049.0 | -43.9 | NO_SETUP: first candle did not break and close beyond the previous-day | NO_SETUP: first candle did not break and close beyond the in | NO_SETUP: the gap did not push price through the 200 average | LEVEL_CONSTRUCTION |
| 2025-10-08 | 25079.75/25146.95/25079.75/25146.05 | GREEN | 98.7 | 1.3 | 0.0 | 25220.35 / 25077.1 | -102.3 | NO_SETUP: first candle did not break and close beyond the previous-day | NO_SETUP: first candle did not break and close beyond the in | NO_SETUP: no gap in this direction | LEVEL_CONSTRUCTION |
| 2025-10-16 | 25401.0/25424.65/25382.85/25412.15 | GREEN | 26.7 | 29.9 | 43.4 | 25364.35 / 25163.2 | -165.2 | CANDLE_QUALITY(not a strong body / wick too large) | TRENDLINE_NOT_SUPPORTIVE | NO_SETUP: the gap did not push price through the 200 average | STRONG_CANDLE_THRESHOLD |
| 2025-10-17 | 25541.3/25564.7/25508.95/25554.05 | GREEN | 22.9 | 19.1 | 58.0 | 25624.8 / 25382.85 | -166.9 | NO_SETUP: first candle did not break and close beyond the previous-day | NO_SETUP: first candle did not break and close beyond the in | NO_SETUP: no gap in this direction | LEVEL_CONSTRUCTION |
| 2025-10-27 | 25851.95/25877.6/25828.1/25861.4 | GREEN | 19.1 | 32.7 | 48.2 | 25939.3 / 25718.65 | -22.3 | NO_SETUP: first candle did not break and close beyond the previous-day | TREND:EMA_PREV_SESSION_CLOSE wrong side | CANDLE_QUALITY_OR_REJECTION_WICK | EMA_REQUIREMENT |
| 2025-11-21 | 26116.2/26141.85/26096.5/26138.75 | GREEN | 49.7 | 6.8 | 43.4 | 26246.2 / 26064.05 | -66.8 | NO_SETUP: first candle did not break and close beyond the previous-day | NO_SETUP: first candle did not break and close beyond the in | NO_SETUP: no gap in this direction | LEVEL_CONSTRUCTION |
| 2025-11-28 | 26237.45/26246.9/26172.9/26242.15 | GREEN | 6.4 | 6.4 | 87.2 | 26310.05 / 26142.15 | -79.2 | NO_SETUP: first candle did not break and close beyond the previous-day | TRENDLINE_NOT_SUPPORTIVE | NO_SETUP: the gap did not push price through the 200 average | METHOD2_TRENDLINE |
| 2025-12-05 | 26001.15/26050.6/25991.85/26050.6 | GREEN | 84.2 | 0.0 | 15.8 | 26097.8 / 25940.1 | -24.8 | NO_SETUP: first candle did not break and close beyond the previous-day | NO_SETUP: first candle did not break and close beyond the in | NO_SETUP: no gap in this direction | LEVEL_CONSTRUCTION |
| 2025-12-12 | 25982.75/26002.8/25964.9/26002.55 | GREEN | 52.2 | 0.7 | 47.1 | 25921.75 / 25693.3 | -136.7 | CANDLE_QUALITY(not a strong body / wick too large) | TRENDLINE_NOT_SUPPORTIVE | NO_SETUP: the gap did not push price through the 200 average | STRONG_CANDLE_THRESHOLD |
| 2025-12-24 | 26183.75/26201.55/26142.0/26198.25 | GREEN | 24.3 | 5.5 | 70.1 | 26233.55 / 26120.0 | -86.6 | NO_SETUP: first candle did not break and close beyond the previous-day | NO_SETUP: first candle did not break and close beyond the in | NO_SETUP: the gap did not push price through the 200 average | LEVEL_CONSTRUCTION |
| 2025-12-30 | 25951.0/25951.0/25894.6/25908.05 | RED | 76.2 | 0.0 | 23.8 | 26102.75 / 25922.25 | 123.5 | CANDLE_QUALITY(not a strong body / wick too large) | CANDLE_QUALITY | NO_SETUP: no gap in this direction | STRONG_CANDLE_THRESHOLD |
| 2025-12-31 | 25975.45/26026.85/25975.45/26013.65 | GREEN | 74.3 | 25.7 | 0.0 | 25976.75 / 25878.0 | -38.1 | TREND:EMA_PREV_SESSION_CLOSE wrong side | TREND:EMA_PREV_SESSION_CLOSE wrong side | NO_SETUP: the gap did not push price through the 200 average | EMA_REQUIREMENT |

Both directions, the strength verdicts under the STRICT / MODERATE (active) / LOOSE profiles, the Method 2 inner level and trendline values, the trend result and the Gap setup values are in `orb_missing_signal_audit.csv` and `orb_missing_signal_audit.json`.

## Reading the causes

* **Level construction (no previous-day level broken):** the first candle neither broke nor closed beyond the previous-day high or low, and Method 2's inner level is a RESEARCH VARIANT (the latest fractal of the previous session inside its range) that the source does not define (orb.py says so). The engine has nothing to evaluate; the author sees an ORB from a hand-drawn level.
* **Method 2 trendline:** a proposed fractal trendline decided it; no objective construction exists in the source.
* **Strength threshold:** a proposed body / wick profile (MODERATE: body >= 60%, opposite wick <= 20%) rejected the candle; the LOOSE profile (body >= 50%, wick <= 25%) would pass some of them (columns `strength_*`).
* **EMA requirement:** the approved trend variant (previous close against its EMA) rejected it.

The handwritten pages contain no ORB drawings, so the check against the author's chart is the remark text only. No cause is a single wrong rule: most are proposals or undefined constructions, which is an owner decision (O8), not a defect.

## ORB colour candidate (Phase 5.1, preserved and selectable)

`phase52-cand-orb-colour`: long needs a green first candle, short a red one. The author wrote 'for long' (AC27); the short side is a source interpretation (ORB-GLOBAL-002 'same rules in both directions'), recorded as such. It changes 3 confirmed ORB signals: 2025-11-27 LONG, 2026-01-05 LONG, 2026-04-24 SHORT. The frozen ORB is not modified.
