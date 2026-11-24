# Preservation verification (Phase 6.5)

Method: `scripts/phase65_snapshot.py before` hashed (SHA-256) every file under data/, reports/, docs/, src/, tests/, scripts/, pyproject.toml and README.md (20,436 files) **before any Phase 6.5 file was written**; `verify` re-hashed afterwards.

| check | result |
|---|---|
| pre-existing files changed | **0** |
| pre-existing files removed | **0** |
| new files from Phase 6.5 | 5 source/test/script files + `reports/phase6/phase65_author_feedback/` (+ the copied IRF Method 1 rulebook PDF) |
| new files NOT created by this phase | **10** under `src/nifty_trading/research/irf_v3/` (see below) |

**Not mine:** `src/nifty_trading/research/irf_v3/` (`config.py`, `method1.py`, `method2.py`, `signal_engine.py`, `backtest.py`, `execution.py`, `data_access.py`, `audit.py`, `models.py`, `__init__.py`) appeared in the working tree at 13:56-13:59 on 2026-11-18, while this phase was running. It was not created, read or edited by Phase 6.5 and is outside this phase's allow-list, which is why the script's own flag reads `preserved: false`. It looks like another process implementing the two newer IRF methods; Phase 6.5 only contains detector-level code for them (`research/phase65.py`), so the two efforts overlap and should be reconciled by the owner.

Also unchanged: the Phase 3.6 frozen results, Phases 4-6.3 reports and ledgers, the manual journal, all market data, `core/paper.py` and every configuration module. The IRF Method 2 rulebook PDF (`IRF_Method2_First_Red_Candle_Rulebook.pdf`) was added to `docs/strategy_docs/` by the owner before the snapshot was taken. Nothing was committed or pushed.
