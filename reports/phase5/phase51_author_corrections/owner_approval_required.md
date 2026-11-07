# Owner approval required

Nothing below is decided by this phase. Where no answer is given the active baseline (Phase 3.6) is unchanged.

| # | decision | options | evidence / reach | default |
|---|---|---|---|---|
| O1 | Adopt the ORB colour rule (NR1) as the baseline? | yes (long needs green, short red) / only the pin-bar route / no | opt-in variant exists and is tested; changes 3 ORB confirmations (2025-11-27, 2026-01-05, 2026-04-24) | no change |
| O2 | IRF EMA-space rule (NR2): skip or defer? | skip the signal / defer until a close below the EMA (and for how long) / no rule | 9 of 109 executed IRF trades touched; both dated examples confirmed | no change |
| O3 | IRF at the day's low (NR3) | define 'at' (close below the prior session low?) and whether the day then ends / no rule | 0 executed trades touched; signals on 2025-11-12 and 2025-12-11 touched | no change |
| O4 | IRF Method 2 reference candle (NR4) | first red candle outside the range - fully above or close above; support break by any candle or only by a red one / no rule | differs from the engine on 37 of 42 executed Method-2 trades | no change |
| O5 | IRF entry-candle body threshold (NR5) | 60 / 50 / 40 / none | 55 / 35 / 28 of 109 executed IRF trades have a smaller body | no change |
| O6 | PDR / PDS confirmation: first candle vs pattern thresholds (NR6) | keep PDR-A04 with the proposed numbers / loosen the numbers / first green candle with no threshold; PDS same | first-green earlier on 19 of 25 PDR trades; conflicts with PDS-M-001 | no change |
| O7 | May the green candle that tests the zone be the PDR confirmation? (AC02) | yes (pdr_green_may_be_interaction_candle = True) / no | an existing switch; PDR-A07 is a proposal | no change |
| O8 | RF-004 (open above yesterday's high) | keep / redefine 'yesterday's range' | AC05, AC36 (opens 41.6 and 24.7 points above the previous high) | keep |
| O9 | ORB inner level, trend and candle-strength definitions | author to supply objective definitions | 13 'ORB should have activated' remarks | no change |
| O10 | PDR failed-zone policy (AC36) | unchanged / invalidate after a close below the zone floor | open since Phase 3.4; closes below the floor preceded the 10:45 entry | unchanged |
| O11 | Same-day second trade (AC22, AC30) | keep DAY-SL-001 / forbid | the approved portfolio rule allows it | keep |
| O12 | Incomplete / unclear remarks | the sentence after 'PDR/PDS should activate only before' (G01); AC35 label (PDS or PDR) and meaning of 'trap'; AC16 'IRF activation is also wrong' | see the transcription | no change |

