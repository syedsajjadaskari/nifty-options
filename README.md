# NIFTY Options Trading Automation — Phase 1

Production-grade algorithmic trading architecture for NIFTY options using the 5paisa Developer API.

## Overview

This repository houses Phase 1 of the NIFTY options trading platform, focusing on:
- Secure broker authentication via 5paisa TOTP session flow
- Instrument discovery and resolution for NIFTY 50 spot index
- Resilient historical 1-minute OHLCV data downloading with rate limiting and exponential backoff
- High-performance columnar Parquet storage partitioned by Year/Month with ZSTD compression
- DuckDB analytical query layer for fast zero-overhead queries
- Comprehensive data quality validation against the NSE trading calendar
- Extensible, modular architecture for future strategy implementation, backtesting, paper trading, and live execution

## Architecture

```
nifty-options/
├── src/
│   └── nifty_trading/
│       ├── broker/             # 5paisa API client, session management, and rate limiting
│       ├── config/             # Pydantic Settings, environment config, project paths
│       ├── core/               # Strategy, backtest, paper execution, and risk interfaces
│       ├── data/               # Downloader, NSE calendar, Parquet storage, DuckDB interface
│       └── instruments/        # 5paisa Scrip Master downloader and instrument resolver
├── scripts/
│   ├── verify_5paisa.py        # Connection verification and read-only broker API checks
│   ├── download_nifty50.py     # Resumable historical 1-minute data downloader
│   ├── verify_data.py          # Data quality validation & audit report generator
│   └── query_candles.py        # DuckDB interactive query helper
├── tests/                      # Comprehensive unit tests with mocked broker endpoints
├── data/
│   ├── metadata/               # Instrument master and download manifest
│   └── processed/nifty50/      # Partitioned Parquet files (year=YYYY/month=MM)
└── reports/
    └── data_quality/           # Audit reports (JSON & Markdown)
```

## Quick Start

### 1. Environment Setup

Create virtual environment and install dependencies:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Configure Credentials

Copy `.env.example` to `.env` and fill in your 5paisa developer API keys and TOTP secret:
```bash
cp .env.example .env
```

### 3. Verify Broker Connection

Run read-only verification:
```bash
python scripts/verify_5paisa.py
```

### 4. Download Historical Data

Download 1-minute NIFTY 50 index candles:
```bash
python scripts/download_nifty50.py
```

### 5. Validate Dataset

Run comprehensive data audit:
```bash
python scripts/verify_data.py
```

### 6. Query with DuckDB

Run sample queries:
```bash
python scripts/query_candles.py
```


---

## Phase 2 / 2.1 — Strategy rule verification, data revalidation and signal engines (index-price signals only)

Phase 2 reads the five strategy PDFs and the performance report, builds a rule registry, and implements **signal detection only** for
IRF, ORB, PDR, PDS and RF on NIFTY 50 index candles. It places no orders, downloads no options data and enables no live execution. Index-point P&L is synthetic.
**Phase 2.1** revalidated the whole dataset: the "frozen feed" seen from 2026-08-03 is NSE's Closing Auction Session (real market structure), not corruption.

```bash
pytest                                          # Phase 1 + Phase 2/2.1 tests
python scripts/phase21_redownload.py LABEL TF FROM TO ...   # READ-ONLY fresh download, saved raw under data/raw/ (never overwrites)
python scripts/phase21_build_data.py            # official daily series + warm-up-only minutes (new files only)
python scripts/phase21_compare.py               # fresh-vs-stored, vendor 5m/daily, external closes, archive integrity
python scripts/phase21_build_manifests.py       # data/metadata/session_quality_manifest.json
python scripts/phase21_reconcile.py             # journal vs performance report (workbook untouched)
python scripts/phase21_decisions.py             # decision records + author questions
python scripts/phase2_build_docs.py             # rule_registry.yaml/.md and source_traceability.md
python scripts/phase2_signal_counts.py          # descriptive record counts per interpretation (not for tuning)
```

Start with `docs/phase2/phase3_readiness.md`, then `author_decisions_required.md`, `data_repair_report.md`.
Code: `src/nifty_trading/strategies/` (engines, rule registry, proposals, `runner.evaluate_dataset`),
`src/nifty_trading/data/sessions.py` + `market_calendar.py` (5-minute candles, quality status, warm-up), `src/nifty_trading/core/exit_policy.py` (exit specification).
Timestamps are start-of-minute labels: the 09:15 five-minute candle is rows 09:15-09:19 and is usable at 09:20.

## Phase 2.2 — rule finalisation (still signal detection + exit specification only)

Phase 2.2 re-read the five PDFs independently, set the owner's **stop-loss research baseline** (IRF/PDR/PDS/RF 35, ORB 30; 40 as a later sensitivity variant, all in `strategies/params.py::TradeConfig`),
recorded target statuses (RF 60 is a *proposal*), added a prior-session **structure trend** and swing definitions (proposals), PDR/PDS zone candidates, strict zone intersection, owner candle thresholds, a **closing-auction execution-eligibility layer**
(`core/execution_eligibility.py`: 15:15–15:29 bars on/after 2026-08-03 are real data but non-fillable) and repeated-signal evaluation policies (`strategies/selection.py`). Nothing is approved except the stop baseline; no profit backtest was run.

```bash
python scripts/phase22_signal_counts.py   # counts only -> reports/phase22/
python scripts/phase22_build_docs.py      # docs/phase2/phase22_final_rule_matrix.md
```
Read `docs/phase2/phase22_rule_verification.md`, `phase22_author_decisions.md` and `phase3_readiness.md` first.

## Phase 2.3 — owner-approved execution rules (still no backtest)

A shared trading-day controller (`strategies/trading_day.py`) selects trades across the five strategies: first valid signal, at most 2 entries, the second only PDR/PDS after a full stop,
strict 13:00 IST entry cutoff, 6 lots in two legs, Target 1 = 27, and a post-T1 stop **6 points against the entry** (replacing the report's exact-entry breakeven, which stays in the registry as superseded).
Same-timestamp collisions between strategies are logged, not resolved (no approved tie-break). The five entry engines were not rewritten.

```bash
python scripts/phase23_signal_diagnostics.py   # selection-level counts only -> reports/phase23/
python scripts/phase23_build_docs.py           # docs/phase2/phase23_user_approved_rules.md from the registry
```
Read `docs/phase2/phase23_user_approved_rules.md`, `phase23_trade_state_machine.md`, `phase23_exit_policy.md`, `phase23_signal_selection.md`, `phase23_source_conflicts.md` and `phase3_readiness.md`.

## Phase 3.0 — exploratory historical backtest (research only)

`scripts/phase3_run_backtests.py` runs four fixed, labelled scenarios (A baseline, B structure trend, C PDR shelf, D 40-point stop) over 2025-09-01..2026-08-31 through the shared day controller
(`research/phase3.py`), with a forced exit at the open of the 15:14 minute (an implementer assumption awaiting the owner). Output: `reports/phase3/<scenario>/` and `reports/phase3/phase3_comparison.md`.
Synthetic index-point P&L x quantity on a non-tradable index; nothing was optimised, combined or approved.

## Phase 3.1 — trade-by-trade reconciliation and independent audit (research only)

`src/nifty_trading/research/phase31.py` with `scripts/phase31_reconcile.py`, `phase31_analysis.py`, `phase31_traces.py`, `phase31_report.py` normalises the manual journal and matches every row one-to-one to the Phase 3.0 baseline (P&L is never a matching criterion), classifies every unmatched row and every extra automated trade, and builds per-day signal timelines and a strategy-interference matrix. Start with `reports/phase3/phase31/reconciliation_summary.md`, then `root_cause_analysis.md`, `source_to_code_audit.md`, `confirmed_software_defects.md` and `owner_decisions_required.md`. No rule or parameter was changed and the Phase 3.0 ledgers are untouched (hashes in `phase30_ledger_hashes.json`); the only code change besides diagnostics is the optional `DayRules.collision_policy` diagnostic and the D-IRF-1 fix (non-default IRF variant only).

## Phase 3.2 — explainable backtest, trade journals and daily verification (research only)

`scripts/phase32_build.py` re-runs the Phase 3.0 baseline unchanged and writes `reports/phase3/phase32/`: a journal for every one of the 247 evaluable sessions (`daily/`), a full entry/exit explanation with numeric evidence for each of the 213 trades, 213 charts on the real candles, the CSV exports and `NIFTY_Daily_Trade_Verification.xlsx`. `scripts/phase32_audit.py` is an independent audit that re-implements candles, EMA, exits and P&L from the raw data. Read `reports/phase3/phase32/README.md` first. No rule or parameter was changed and nothing is marked as reviewed.
