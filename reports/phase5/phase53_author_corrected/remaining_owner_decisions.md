# Remaining owner decisions (Phase 5.3)

Nothing below is decided here. Provisional conventions stay labelled PROVISIONAL; the combined configuration is separately selectable and the frozen Phase 3.6 default is untouched.

| # | decision | options | evidence |
|---|---|---|---|
| O1 | Adopt the ORB colour rule? short mirror? | adopt both / long only / no | removes 3 confirmed ORB signals |
| O2 | IRF EMA clearance: confirm the range measure; directional (EMA below only / not between entry and Target 1) or symmetric; skip versus wait for the EMA break; scope | see irf_ema_28_implementation.md | 167 of 874 Phase 3.6 IRF signals fail; only 66 of them have the EMA between entry and Target 1 |
| O3 | IRF day's-low restriction: the predicate and the response | D1-D8 readings | irf_day_low_unresolved.md |
| O4 | IRF first red candle: extend to Method 2B / Method 3? search start (after the extension or after the breakout)? | 2A only (current) / also 2B / also Method 3 | 4 of 42 executed trades differ by search start; AC08 moves against the stated direction |
| O5 | IRF entry-candle body threshold (60 / 50 / 40 %) | 60 / 50 / 40 / none | AC07, AC32 (not addressed) |
| O6 | PDR / PDS conventions: green-candle and rejection tests; PDS structural quality tests; may a weak first red be taken directly (AC38)? | keep provisional / change | pdr_first_eligible_implementation.md, pds_first_eligible_implementation.md |
| O7 | May the PDR retest candle itself confirm? | yes / no | 16 armed setups would qualify; AC02 depends on it |
| O8 | ORB inner level, trendline, strength profile, trend filter definitions; ORB priority over IRF (not approved) | author to supply | orb_unresolved_entries.md |
| O9 | RF-004 (open above yesterday's high) and the PDR failed-zone policy | unchanged unless redefined | Phase 5.1 AC05, AC36 |
| O10 | Where in the documents is 'IRF should not be activated at the day's low'? | author to point to the page | not found in the five guides |

A revised profitability backtest has NOT been run and requires the owner's go-ahead after these decisions.
