# Paper-trading readiness assessment (Phase 4)

**Written for:** the strategy owner. This is an assessment only. No live order was placed, no paper trading was deployed, and no market monitoring was started.

## Verdict

**Not recommended to begin paper-trading engineering on the strength of this historical evidence.** The frozen strategy is technically reproducible and its machinery is reliable, but the evidence is inconsistent across years, fragile to realistic costs, and sensitive to the data source. If the owner decides to proceed anyway, the first work item should be the missing live-data and execution infrastructure below, with the unresolved author decisions closed first.

## Evidence from the historical tests

| criterion | finding | assessment |
|---|---|---|
| Consistency across years | gross Rs: 2018 -102,063 (exploratory), 2019 301,314 (exploratory, secondary vendor) / 352,609 (5paisa, 10 months), 2022-23 288,454, 2023-24 -3,851, 2024-25 224,796, 2025-26 297,765; of the six distinct years one is clearly negative (2018, exploratory) and one is flat (2023-24, profit factor 0.9971); the years also differ in scale (fixed-point stops against an index that was ~2.3x lower in 2018-19: see `robustness_report.md` section 11) | NOT consistent |
| Costs | gross edge about Rs 836 per trade vs about Rs 890 of illustrative cost per trade; three-year net Rs -32,612; negative at every higher cost / slippage tested | FRAGILE |
| Drawdown | worst drawdown Rs 188,341 gross (three years) against a three-year gross profit of Rs 509,398; longest losing streak 7 | LARGE relative to the edge |
| Data reliability | the two vendors' minute bars differ (OHLC identical on 40% of 2022-25 bars; first-bar open differs by ~6 points); the same three-year window is Rs 509k vs Rs 626k gross with 71.5% signal agreement; 2018 cannot be checked at all | MATERIAL sensitivity: a live feed's bars will differ again |
| Unresolved author rules | numeric definitions of the three PDR candle patterns (thresholds are PROPOSED_FOR_REVIEW, profile RESEARCH_DEFAULT); whether the clarification (wicks ignored) supersedes the PDF's wick-topped example boxes; PDR wait policy for a zone that price has closed through; PDR zone lower boundary and multiple-body-high numbers; zero-height zone policy; same-candle test-and-confirm; ... | OPEN (10 listed in `strategy_freeze.json`) |
| Development bias | the strategy was developed on 2025-26 data and tuned in conversation with that year's journal; none of the older windows is strictly out-of-sample | CAVEAT on every result |

## Engineering readiness (what exists in the repository today)

| capability | state | gap |
|---|---|---|
| Market-data streaming | none: only the historical-candle endpoint of the read-only `BrokerClient` exists; no websocket / tick consumer | build a live 1-minute bar builder that reproduces the research bar convention (bar START label, first bar semantics) and detect gaps / stalls; validate live bars against the historical vendor (they will not be identical) |
| Trading-session calendar | historical: evidence calendar 2025-26 + derived multi-year calendar; the closing-auction regime is date-aware (2026-08-03) | a live calendar source for holidays, special sessions and revised timings; the derived calendar was not checked against NSE circulars |
| Broker API | authentication (TOTP, cached daily token) and read-only endpoints work; order, modify, cancel and square-off raise `PermissionError` by design | order APIs untested; instrument mapping for options / futures (the research uses the cash index, which is not tradable) not built |
| Paper-order simulation | `core/paper.py` is a 63-line Phase 1 skeleton (order dataclass and statuses), not connected to the Phase 3 controller or exit model | an executable paper engine that reuses `trading_day.py` / `exit_policy.py` and an option / futures price model |
| State persistence | none for a live day (the backtest controller is stateless across days and re-runs the day) | durable per-day state: open positions, leg status, stops, signals seen, so a restart cannot re-enter or lose a position |
| Duplicate-order prevention | none | idempotent order keys per signal, a single writer, reconciliation with broker positions |
| Emergency stops / risk | `core/risk.py` is a 55-line skeleton (daily loss limit Rs 10,000, which is below the strategy's own single-trade loss of Rs 13,650; position size of 1,800 = 50 lots; kill-switch flag) that does not match the 6-lot / 390-unit design | kill switch wired to the order path, daily loss and position limits derived from the strategy, a market-data-stall halt |
| Logging and monitoring | research reports are rich; no runtime logging / alerting for a live process | structured logs, heartbeat, alerts on stalls, rejected orders and state mismatches |
| Forced exit / end of day | the research uses a provisional exit at the open of the 15:14 minute; the owner has not approved it | an approved end-of-day liquidation policy that also covers the closing-auction regime |

## If the owner wants to continue

1. Decide the open author questions (candle-pattern definitions, PDR wait policy, zero-height zones, tie-break for simultaneous signals, RF target, forced exit) **before** any further testing, so that no later result can influence them.
2. Decide the instrument (futures or options) and build a realistic cost and fill model; the cost sensitivity above shows the cost model decides whether the system has any edge.
3. Choose ONE live data feed, record its bars alongside the research vendor's for a period, and measure how far its signals diverge before trusting any rule that depends on the 09:15 bar.
4. Only then build the persistence / duplicate-order / kill-switch layer and a paper engine; paper results would test mechanics and fills, not the edge.
