# Source and implementation inventory (Phase 6.5)

Git HEAD when the work started: `9d7f5af87148a4db7d6c502c2a73295a5bcdd0c6` (Phases 6.1-6.3 committed). Working tree otherwise clean except the two newer IRF rulebooks (untracked PDFs; one copied by me from `~/Downloads`, one added by the owner).

## Source documents (SHA-256)

| document | path | sha256 |
|---|---|---|
| IRF guide (3 methods) | docs/strategy_docs/IRF_Strategy_Guide Updated.pdf | 5106469ebc0f53ac... |
| IRF new Method 1 'High Breakout Failure' | docs/strategy_docs/IRF_Inverse_Retest_Failure_Rulebook.pdf | 39b9dd226c5dabd3... |
| IRF new Method 2 'First Red Candle Resistance Failure' | docs/strategy_docs/IRF_Method2_First_Red_Candle_Rulebook.pdf | 5ad283df82c81eef... |
| ORB latest rulebook (DOCX) | docs/strategy_docs/Nifty_920_ORB_Rulebook (2) (1).docx | 8504fb6fca64a7e1... |
| PDR guide | docs/strategy_docs/PDR_Strategy_Guide.pdf | c68665564e2ca6ce... |
| PDS guide | docs/strategy_docs/PDS strategy.pdf | 1288146e3fca6559... |
| RF guide | docs/strategy_docs/RF strategy.pdf | 5e94263800e73f3c... |
| handwritten corrections (6 pages) | docs/strategy_docs/corrected/Adobe Scan Nov 05, 2026.pdf | 601711a505e4c7f8... |
| manual journal | docs/trading journal/Trading_Journal_Sep2025_Aug2026 REPORT.xlsx | 97a9ad4dfb552061... |


## Implementation versions actually in force (not proposed names)

| file | sha256 |
|---|---|
| src/nifty_trading/strategies/irf.py | d0e103a1b5044ea7... |
| src/nifty_trading/strategies/irf_phase53.py | 5584aa6fa0f5406f... |
| src/nifty_trading/strategies/irf_v2.py | 080427fecea315a8... |
| src/nifty_trading/strategies/orb_v2_adapter.py | 8b96079366b771cd... |
| src/nifty_trading/research/orb_v2/signal_engine.py | 548276b4358b702f... |
| src/nifty_trading/strategies/first_eligible_phase53.py | 3bd07efcddfcc358... |
| src/nifty_trading/strategies/pdr_body.py | 59ff807afc881312... |
| src/nifty_trading/strategies/pds.py | 4496061195624a1d... |
| src/nifty_trading/strategies/rf.py | ede1ec29cefa897e... |
| src/nifty_trading/strategies/trading_day.py | c8ffc42771edac4d... |
| src/nifty_trading/core/exit_policy.py | f98d9ff3ee84ef6e... |
| src/nifty_trading/research/phase62.py | 32fab6d480142fbb... |
| src/nifty_trading/core/paper.py | d83de1125e050f60... |


| role | implementation actually used here |
|---|---|
| IRF | `IRFV2SupportBreakStrategy` (IRF-V2-SUPPORT-BREAK; emits the same signals as `IRFPhase53Strategy`); frozen `IRFStrategy` for reference |
| ORB | ORB V2 adapter wrapping Phase 6.0 `ORB-V2-A` (provisional reference; no owner selection exists) |
| PDR / PDS | `PDRFirstEligibleStrategy` / `PDSFirstEligibleStrategy` (Phase 5.3 first-eligible, provisional conventions) |
| RF | frozen `RFStrategy` |
| controller | frozen `trading_day.run_trading_day` (first valid signal, max 2 trades, 13:00 cutoff, no tie-break policy) |
| combined configuration | `phase62-irfv2-orbv2-combined` (configuration C of Phase 6.2) |

## Paper-trading configuration

`src/nifty_trading/core/paper.py` is a paper execution engine decoupled from broker order endpoints. The repository contains **no record selecting a live-market paper-trading configuration**, and this phase did not touch `core/paper.py`, `config/`, the broker modules or any frozen configuration (before/after hash check in `preservation_verification.md`). Everything produced here is a research variant; none is activated anywhere.

## Reproduce

`python scripts/phase65_snapshot.py before` (before any change), `python scripts/phase65_run.py`, `python scripts/phase65_docs.py`, `python -m pytest -q`, `python scripts/phase65_snapshot.py verify`.