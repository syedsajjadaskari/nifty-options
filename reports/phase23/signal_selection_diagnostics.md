# Phase 2.3 signal-selection diagnostics (counts only)

> No exit simulated, no profit computed, nothing tuned. Shows how often the unresolved tie-break rule would bite.

| item | value |
|---|---|
| confirmed_signals | 1345 |
| rejected_ENTRY_BLOCKED_CLOSING_AUCTION_ | 2 |
| rejected_ENTRY_BLOCKED_POST_CLOSE | 14 |
| rejected_after_13:00_cutoff | 484 |
| sessions | 247 |
| sessions_with_an_eligible_first_signal | 191 |
| sessions_with_signals_but_none_eligible | 13 |
| sessions_without_any_signal | 43 |

## Which strategy gives the first eligible signal of the session

| strategy | sessions |
|---|---|
| COLLISION | 3 |
| IRF | 113 |
| ORB | 21 |
| PDR | 47 |
| PDS | 7 |

## Same-timestamp collisions among the FIRST eligible signals (3)

| date | time | signals |
|---|---|---|
| 2026-02-18 | 09:30 | PDR/PDR/LONG, RF/RF/LONG |
| 2026-06-23 | 10:30 | IRF/Method 2A/SHORT, PDS/Method 3/SHORT |
| 2026-07-13 | 10:55 | IRF/Method 2A/SHORT, IRF/Method 2B/SHORT, PDS/Method 3/SHORT |
