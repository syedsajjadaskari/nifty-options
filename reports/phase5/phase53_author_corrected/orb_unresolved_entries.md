# ORB - the disputed entries (diagnostic; no priority override, no new rule)

Signal-level evidence only: no controller, no fills, no P&L and no profitability backtest were run. Conventions marked PROVISIONAL are not confirmed as the author's meaning.

The author reports that ORB was often not taken and IRF was selected. On all 13 disputed dates the engine produced **no ORB signal at all** (Phase 3.6: 0; Phase 5.3: 0), so the controller's first-valid-signal rule skipped nothing and **no priority was added**. The ORB engine is identical in every Phase 5.3 configuration (audit-verified; the colour rule is a separate opt-in).

| date | colour / body / wicks % | failing: Method 1 | Method 2 | cause | first signal now | precise definition missing |
|---|---|---|---|---|---|---|
| 2025-09-11 | GREEN / 97.7 / 2.3 / 0.0 | NO_SETUP: first candle did not break and close beyond the previous-day | TRENDLINE_NOT_SUPPORTIVE | METHOD2_TRENDLINE | 09:30 IRF/Method 1 | an objective construction of the Method 2 trendline (which fractals, how many touches, slope tolerance) - the source only draws it |
| 2025-09-16 | GREEN / 71.7 / 9.2 / 19.1 | NO_SETUP: first candle did not break and close beyond the previous-day | NO_SETUP: first candle did not break and close bey | LEVEL_CONSTRUCTION | none | the level the author drew: Method 2's inner support/resistance is not defined in the rulebook (the engine has no level to break when the first candle  |
| 2025-10-08 | GREEN / 98.7 / 1.3 / 0.0 | NO_SETUP: first candle did not break and close beyond the previous-day | NO_SETUP: first candle did not break and close bey | LEVEL_CONSTRUCTION | 09:50 IRF/Method 2A | the level the author drew: Method 2's inner support/resistance is not defined in the rulebook (the engine has no level to break when the first candle  |
| 2025-10-16 | GREEN / 26.7 / 29.9 / 43.4 | CANDLE_QUALITY(not a strong body / wick too large) | TRENDLINE_NOT_SUPPORTIVE | STRONG_CANDLE_THRESHOLD | 09:40 IRF/Method 1 | the ORB strong-candle definition (body %, opposite-wick %) or an approval of a looser profile - the rulebook gives no numbers |
| 2025-10-17 | GREEN / 22.9 / 19.1 / 58.0 | NO_SETUP: first candle did not break and close beyond the previous-day | NO_SETUP: first candle did not break and close bey | LEVEL_CONSTRUCTION | none | the level the author drew: Method 2's inner support/resistance is not defined in the rulebook (the engine has no level to break when the first candle  |
| 2025-10-27 | GREEN / 19.1 / 32.7 / 48.2 | NO_SETUP: first candle did not break and close beyond the previous-day | TREND:EMA_PREV_SESSION_CLOSE wrong side | EMA_REQUIREMENT | 10:00 IRF/Method 2B | the exact trend filter (previous-session close against its EMA, or the first candle's close against EMA(200), or none) |
| 2025-11-21 | GREEN / 49.7 / 6.8 / 43.4 | NO_SETUP: first candle did not break and close beyond the previous-day | NO_SETUP: first candle did not break and close bey | LEVEL_CONSTRUCTION | 09:40 IRF/Method 2A | the level the author drew: Method 2's inner support/resistance is not defined in the rulebook (the engine has no level to break when the first candle  |
| 2025-11-28 | GREEN / 6.4 / 6.4 / 87.2 | NO_SETUP: first candle did not break and close beyond the previous-day | TRENDLINE_NOT_SUPPORTIVE | METHOD2_TRENDLINE | 09:40 IRF/Method 1 | an objective construction of the Method 2 trendline (which fractals, how many touches, slope tolerance) - the source only draws it |
| 2025-12-05 | GREEN / 84.2 / 0.0 / 15.8 | NO_SETUP: first candle did not break and close beyond the previous-day | NO_SETUP: first candle did not break and close bey | LEVEL_CONSTRUCTION | 10:25 IRF/Method 2B | the level the author drew: Method 2's inner support/resistance is not defined in the rulebook (the engine has no level to break when the first candle  |
| 2025-12-12 | GREEN / 52.2 / 0.7 / 47.1 | CANDLE_QUALITY(not a strong body / wick too large) | TRENDLINE_NOT_SUPPORTIVE | STRONG_CANDLE_THRESHOLD | 09:50 IRF/Method 2A | the ORB strong-candle definition (body %, opposite-wick %) or an approval of a looser profile - the rulebook gives no numbers |
| 2025-12-24 | GREEN / 24.3 / 5.5 / 70.1 | NO_SETUP: first candle did not break and close beyond the previous-day | NO_SETUP: first candle did not break and close bey | LEVEL_CONSTRUCTION | 09:50 IRF/Method 2A | the level the author drew: Method 2's inner support/resistance is not defined in the rulebook (the engine has no level to break when the first candle  |
| 2025-12-30 | RED / 76.2 / 0.0 / 23.8 | CANDLE_QUALITY(not a strong body / wick too large) | CANDLE_QUALITY | STRONG_CANDLE_THRESHOLD | 10:40 IRF/Method 2A | the ORB strong-candle definition (body %, opposite-wick %) or an approval of a looser profile - the rulebook gives no numbers |
| 2025-12-31 | GREEN / 74.3 / 25.7 / 0.0 | TREND:EMA_PREV_SESSION_CLOSE wrong side | TREND:EMA_PREV_SESSION_CLOSE wrong side | EMA_REQUIREMENT | 09:50 PDR/PDR | the exact trend filter (previous-session close against its EMA, or the first candle's close against EMA(200), or none) |

Causes: {'METHOD2_TRENDLINE': 2, 'LEVEL_CONSTRUCTION': 6, 'STRONG_CANDLE_THRESHOLD': 3, 'EMA_REQUIREMENT': 2}. The handwritten pages contain no ORB drawings (checked in Phase 5.1/5.2), so the author's levels cannot be compared; the author-expected signals cannot be reproduced without the definitions below. IRF's first signal changes on 8 of the 13 dates under the Phase 5.3 IRF rules, but ORB still does not activate on any.

## Missing definitions required to reproduce the 13 expected signals

1. **Method 2 inner level** (6 dates): the rulebook defines Method 1 by the previous-day high/low only; the inner support/resistance (an earlier fractal of the previous session) is a research variant not in the source. Needed: how the author chooses the level.
2. **Method 2 trendline** (the dates where the trendline decided): a deterministic construction (which fractals, how many touches, tolerance).
3. **Strong-candle thresholds** (the dates failing the body/wick profile): numbers or an approved looser profile (STRICT / MODERATE / LOOSE exist; MODERATE is active).
4. **Trend filter** (the dates failing the EMA requirement): whether the previous-session close against its EMA, or another reference, is required.
5. **Gap / 200-average set-up** numbers where it is the intended route.

Still unresolved: **13 of 13**. The Phase 5.1 ORB colour rule (long needs green, short red) remains selectable as `phase53-var-orb-colour` and removes 3 confirmed ORB signals; it is not part of the combined configuration.
