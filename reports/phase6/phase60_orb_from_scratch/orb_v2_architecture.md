# ORB V2 architecture

Package `src/nifty_trading/research/orb_v2/` (clean-room; nothing imports the legacy ORB engines, enforced by a test):

| module | role |
|---|---|
| config.py | OrbV2Config (every setting + authority label + SHA-256), configs A-D and the diagnostic |
| models.py | Level, SessionData, Decision |
| data_access.py | window loading (5paisa / secondary), session assembly using the repo loaders, calendar and classify_session |
| opening_candle.py | five-minute aggregation from raw minutes; the 09:15-09:20 candle (confirmed at 09:20) |
| ema.py | EMA(200) recursion |
| levels.py / zones.py | previous-day major and inner levels; zone-aware break test |
| patterns.py | candle metrics and pattern conventions |
| gap_filter.py | opening gap |
| signal_engine.py | one decision, every failed condition recorded |
| execution.py | entry, 30/60, forced exit, ambiguity |
| backtest.py | runner, metrics, costs |
| journal.py | manual-journal reading and classification |
| audit.py | SECOND implementation (imports nothing from the engine) used only to audit it |
| reporting.py | SVG charts, tables, workbooks |


Reused verified infrastructure only: processed-parquet loaders, `MarketCalendar`, `classify_session` (usable sessions, official close, closing-auction regime) and `bars_from_frame` (bar executability). All ORB-specific logic is new. Scripts: `phase60_run.py` (signals, backtest, audit recomputation), `phase60_examples.py`, `phase60_journal.py`, `phase60_charts.py`, `phase60_research.py`, `phase60_workbooks.py`, `phase60_docs.py`, `phase60_snapshot.py` (preservation). Tests: `tests/test_phase60_orb_v2.py`.

## Independence evidence

* No import of `strategies.orb*`, `phase53/54/58/59`, the runner or the controller (AST test).
* `audit.py` re-derives candles (pandas resample), EMA (`ewm`), swings, patterns (cross-multiplied ratios) and the trade (NumPy arrays) and agrees with the engine on every evaluated session of both windows for all five configurations (see `audit_recomputation_summary.json`) and on 2,000 random synthetic sessions; a mutation test proves the comparison can fail.