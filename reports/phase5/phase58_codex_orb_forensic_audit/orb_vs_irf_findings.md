# ORB versus IRF: explicit per-date chronology

Every row below is a literal manual ORB date on which the existing portfolio ledger executed IRF. `orb_vs_irf_selection_timeline.csv` gives all methods/directions and full first-IRF levels/state traces; each daily page expands the failed ORB gates and every5m event. No author direction is inferred. No valid author trade is proved by merely removing one gate.

| config | date | orb_actual_signal_time | irf_first_signal_time | irf_first_signal_method | ledger_trades | gap_candidate_signal |
|---|---|---|---|---|---|---|
| A | 2025-09-11 |  | 09:30 | Method 1 | ["IRF Method 1 09:30 @ 24985.2"] | False |
| B | 2025-09-11 |  | 09:30 | Method 1 | ["IRF Method 1 09:30 @ 24985.2"] | False |
| C | 2025-09-11 |  | 09:30 | Method 1 | ["IRF Method 1 09:30 @ 24985.2"] | False |
| A | 2025-09-16 |  | 10:25 | Method 2A | ["IRF Method 2A 10:25 @ 25161.5"] | False |
| A | 2025-10-01 |  | 10:05 | Method 1 | ["IRF Method 1 10:05 @ 24639.55"] | False |
| B | 2025-10-01 |  | 10:10 | Method 2A | ["IRF Method 2A 10:10 @ 24649.7"] | False |
| C | 2025-10-01 |  | 10:10 | Method 2A | ["IRF Method 2A 10:10 @ 24649.7"] | False |
| A | 2025-10-08 |  | 09:50 | Method 2A | ["IRF Method 2A 09:50 @ 25155.1"] | False |
| B | 2025-10-08 |  | 09:50 | Method 2A | ["IRF Method 2A 09:50 @ 25155.1"] | False |
| C | 2025-10-08 |  | 09:50 | Method 2A | ["IRF Method 2A 09:50 @ 25155.1"] | False |
| A | 2025-10-16 |  | 09:40 | Method 1 | ["IRF Method 1 09:40 @ 25414.1"] | False |
| B | 2025-10-16 |  | 09:40 | Method 1 | ["IRF Method 1 09:40 @ 25414.1"] | False |
| C | 2025-10-16 |  | 09:40 | Method 1 | ["IRF Method 1 09:40 @ 25414.1"] | False |
| A | 2025-10-27 |  | 10:00 | Method 2B | ["IRF Method 2B 10:00 @ 25935.75"] | False |
| B | 2025-10-27 |  | 10:00 | Method 2B | ["IRF Method 2B 10:00 @ 25935.75"] | False |
| C | 2025-10-27 |  | 10:00 | Method 2B | ["IRF Method 2B 10:00 @ 25935.75"] | False |
| A | 2025-11-07 |  | 11:50 | Method 1 | ["IRF Method 1 11:50 @ 25434.7", "PDS Method 2 12:55 @ 25478.7"] | False |
| B | 2025-11-07 |  | 11:45 | Method 2A | ["IRF Method 2A 11:45 @ 25447.85", "PDS Method 2 12:55 @ 25478.7"] | False |
| C | 2025-11-07 |  | 11:45 | Method 2A | ["IRF Method 2A 11:45 @ 25447.85", "PDS Method 2 12:55 @ 25478.7"] | False |
| A | 2025-11-28 |  | 09:40 | Method 1 | ["IRF Method 1 09:40 @ 26211.0"] | False |
| B | 2025-11-28 |  | 09:40 | Method 1 | ["IRF Method 1 09:40 @ 26211.0"] | False |
| C | 2025-11-28 |  | 09:40 | Method 1 | ["IRF Method 1 09:40 @ 26211.0"] | False |
| A | 2025-12-04 |  | 10:05 | Method 2B | ["IRF Method 2B 10:05 @ 26025.4"] | False |
| B | 2025-12-04 |  | 12:55 | Method 2A | ["IRF Method 2A 12:55 @ 25992.85"] | False |
| C | 2025-12-04 |  | 12:55 | Method 2A | ["IRF Method 2A 12:55 @ 25992.85"] | False |
| A | 2025-12-05 |  | 09:55 | Method 1 | ["IRF Method 1 09:55 @ 26042.15"] | False |
| B | 2025-12-05 |  | 10:25 | Method 2B | ["IRF Method 2B 10:25 @ 26085.25"] | False |
| C | 2025-12-05 |  | 10:25 | Method 2B | ["IRF Method 2B 10:25 @ 26085.25"] | False |
| A | 2025-12-12 |  | 10:00 | Method 2A | ["IRF Method 2A 10:00 @ 26006.5"] | False |
| B | 2025-12-12 |  | 09:50 | Method 2A | ["IRF Method 2A 09:50 @ 26016.3"] | False |
| C | 2025-12-12 |  | 09:50 | Method 2A | ["IRF Method 2A 09:50 @ 26016.3"] | False |
| A | 2025-12-24 |  | 10:20 | Method 2B | ["IRF Method 2B 10:20 @ 26225.3"] | False |
| B | 2025-12-24 |  | 09:50 | Method 2A | ["IRF Method 2A 09:50 @ 26206.4"] | False |
| C | 2025-12-24 |  | 09:50 | Method 2A | ["IRF Method 2A 09:50 @ 26206.4"] | False |
| A | 2025-12-30 |  | 10:45 | Method 1 | ["IRF Method 1 10:45 @ 25949.1"] | False |
| B | 2025-12-30 |  | 10:40 | Method 2A | ["IRF Method 2A 10:40 @ 25953.9"] | False |
| C | 2025-12-30 |  | 10:40 | Method 2A | ["IRF Method 2A 10:40 @ 25953.9"] | False |
| A | 2026-01-02 |  | 11:10 | Method 2A | ["IRF Method 2A 11:10 @ 26251.85"] | False |
| A | 2026-01-16 |  | 10:00 | Method 1 | ["IRF Method 1 10:00 @ 25739.25"] | False |
| B | 2026-01-16 |  | 10:45 | Method 2B | ["IRF Method 2B 10:45 @ 25844.55"] | False |
| C | 2026-01-16 |  | 10:45 | Method 2B | ["IRF Method 2B 10:45 @ 25844.55"] | False |
| A | 2026-01-27 |  | 10:00 | Method 1 | ["IRF Method 1 10:00 @ 25111.0"] | False |
| B | 2026-01-27 |  | 10:00 | Method 1 | ["IRF Method 1 10:00 @ 25111.0"] | False |
| C | 2026-01-27 |  | 10:00 | Method 1 | ["IRF Method 1 10:00 @ 25111.0"] | False |
| A | 2026-02-17 |  | 10:45 | Method 2B | ["IRF Method 2B 10:45 @ 25661.6"] | False |
| B | 2026-02-17 |  | 10:40 | Method 2A | ["IRF Method 2A 10:40 @ 25692.45"] | False |
| C | 2026-02-17 |  | 10:40 | Method 2A | ["IRF Method 2A 10:40 @ 25692.45"] | False |
| A | 2026-02-25 |  | 09:35 | Method 1 | ["IRF Method 1 09:35 @ 25578.8"] | False |
| B | 2026-02-25 |  | 10:45 | Method 2A | ["IRF Method 2A 10:45 @ 25619.05"] | False |
| C | 2026-02-25 |  | 10:45 | Method 2A | ["IRF Method 2A 10:45 @ 25619.05"] | False |
| A | 2026-04-10 |  | 10:05 | Method 2B | ["IRF Method 2B 10:05 @ 23971.85"] | False |
| B | 2026-04-10 |  | 10:05 | Method 2B | ["IRF Method 2B 10:05 @ 23971.85"] | False |
| C | 2026-04-10 |  | 10:05 | Method 2B | ["IRF Method 2B 10:05 @ 23971.85"] | False |
| A | 2026-04-13 |  | 10:45 | Method 2B | ["IRF Method 2B 10:45 @ 23723.2"] | False |
| B | 2026-04-13 |  | 10:45 | Method 2B | ["IRF Method 2B 10:45 @ 23723.2"] | False |
| C | 2026-04-13 |  | 10:45 | Method 2B | ["IRF Method 2B 10:45 @ 23723.2"] | False |
| A | 2026-04-17 |  | 09:35 | Method 1 | ["IRF Method 1 09:35 @ 24195.05"] | False |
| B | 2026-04-17 |  | 09:35 | Method 1 | ["IRF Method 1 09:35 @ 24195.05"] | False |
| C | 2026-04-17 |  | 09:35 | Method 1 | ["IRF Method 1 09:35 @ 24195.05"] | False |
| A | 2026-04-21 |  | 09:45 | Method 1 | ["IRF Method 1 09:45 @ 24466.6"] | False |
| B | 2026-04-21 |  | 09:45 | Method 1 | ["IRF Method 1 09:45 @ 24466.6"] | False |
| C | 2026-04-21 |  | 09:45 | Method 1 | ["IRF Method 1 09:45 @ 24466.6"] | False |
| A | 2026-05-18 |  | 12:00 | Method 1 | ["IRF Method 1 12:00 @ 23474.75"] | False |
| B | 2026-05-18 |  | 12:00 | Method 1 | ["IRF Method 1 12:00 @ 23474.75"] | False |
| C | 2026-05-18 |  | 12:00 | Method 1 | ["IRF Method 1 12:00 @ 23474.75"] | False |
| A | 2026-05-22 |  | 10:05 | Method 2B | ["IRF Method 2B 10:05 @ 23766.5"] | False |
| B | 2026-05-22 |  | 09:50 | Method 2A | ["IRF Method 2A 09:50 @ 23740.95"] | False |
| C | 2026-05-22 |  | 09:50 | Method 2A | ["IRF Method 2A 09:50 @ 23740.95"] | False |
| A | 2026-05-25 |  | 11:00 | Method 1 | ["IRF Method 1 11:00 @ 23979.55"] | False |
| B | 2026-05-25 |  | 11:00 | Method 1 | ["IRF Method 1 11:00 @ 23979.55"] | False |
| C | 2026-05-25 |  | 11:00 | Method 1 | ["IRF Method 1 11:00 @ 23979.55"] | False |
| A | 2026-06-16 |  | 09:40 | Method 1 | ["IRF Method 1 09:40 @ 23934.4"] | False |
| B | 2026-06-16 |  | 09:40 | Method 1 | ["IRF Method 1 09:40 @ 23934.4"] | False |
| C | 2026-06-16 |  | 09:40 | Method 1 | ["IRF Method 1 09:40 @ 23934.4"] | False |
| A | 2026-07-02 |  | 10:10 | Method 2A | ["IRF Method 2A 10:10 @ 24099.8"] | False |
| B | 2026-07-02 |  | 09:55 | Method 2A | ["IRF Method 2A 09:55 @ 24136.15"] | False |
| C | 2026-07-02 |  | 09:55 | Method 2A | ["IRF Method 2A 09:55 @ 24136.15"] | False |
| A | 2026-07-06 |  | 10:15 | Method 2A | ["IRF Method 2A 10:15 @ 24370.15"] | False |
| B | 2026-07-06 |  | 10:15 | Method 2B | ["IRF Method 2B 10:15 @ 24370.15"] | False |
| C | 2026-07-06 |  | 10:15 | Method 2B | ["IRF Method 2B 10:15 @ 24370.15"] | False |
| A | 2026-07-10 |  | 10:05 | Method 2B | ["IRF Method 2B 10:05 @ 24209.5"] | False |
| B | 2026-07-10 |  | 10:05 | Method 2B | ["IRF Method 2B 10:05 @ 24209.5"] | False |
| C | 2026-07-10 |  | 10:05 | Method 2B | ["IRF Method 2B 10:05 @ 24209.5"] | False |
| A | 2026-07-15 |  | 10:00 | Method 2A | ["IRF Method 2A 10:00 @ 24185.0"] | True |
| B | 2026-07-15 |  | 09:50 | Method 2A | ["IRF Method 2A 09:50 @ 24192.1"] | True |
| A | 2026-07-16 |  | 11:15 | Method 1 | ["IRF Method 1 11:15 @ 24159.1"] | False |
| A | 2026-07-30 |  | 09:40 | Method 1 | ["IRF Method 1 09:40 @ 24258.7"] | False |
| B | 2026-07-30 |  | 09:40 | Method 1 | ["IRF Method 1 09:40 @ 24258.7"] | False |
| C | 2026-07-30 |  | 09:40 | Method 1 | ["IRF Method 1 09:40 @ 24258.7"] | False |
| A | 2026-08-10 |  | 12:25 | Method 1 | ["IRF Method 1 12:25 @ 24602.8"] | False |
| A | 2026-08-28 |  | 09:35 | Method 1 | ["IRF Method 1 09:35 @ 24149.15"] | False |
| B | 2026-08-28 |  | 09:35 | Method 1 | ["IRF Method 1 09:35 @ 24149.15"] | False |
| C | 2026-08-28 |  | 09:35 | Method 1 | ["IRF Method 1 09:35 @ 24149.15"] | False |

For each no-ORB row, the exact preventing predicates are in `why` in the CSV and the both-direction method tables in daily/. IRF occurs after09:20; sourceORB only offers that opening decision. If confirmedORB is absent, the controller cannot select it. A signal-only candidate at09:20 would precede a laterIRF causally if no simultaneous other-strategy conflict exists; that is a candidate counterfactual, not a verified author correction or simulated trade.
