# Execution ambiguity report - baseline

0 ambiguities were resolved by the conservative rule (stop before target; post-T1 stop before Target 2). 6 trades had a gap through a stop (adverse slippage logged).

| date | trade | strategy | note |
|---|---|---|---|

## Gap-through-stop fills (worse than the stop level)

| date | trade | strategy | outcome | adverse slippage (points) |
|---|---|---|---|---|
| 2025-09-22 | 1 | IRF | T1_THEN_BUFFER_STOP | 0.45 |
| 2025-11-13 | 1 | PDR | T1_THEN_BUFFER_STOP | 0.85 |
| 2025-11-14 | 1 | PDS | INITIAL_FULL_STOP | 0.45 |
| 2025-12-10 | 1 | PDR | T1_THEN_BUFFER_STOP | 0.05 |
| 2026-03-12 | 1 | ORB | INITIAL_FULL_STOP | 3.45 |
| 2026-07-10 | 1 | IRF | T1_THEN_BUFFER_STOP | 0.05 |
