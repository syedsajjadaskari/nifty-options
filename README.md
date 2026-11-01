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

## Phase 2 — Strategy rule verification and signal engines (index-price signals only)

Phase 2 reads the five strategy PDFs and the performance report, builds a rule registry, and implements **signal detection only** for
IRF, ORB, PDR, PDS and RF on NIFTY 50 index candles. It places no orders, downloads no options data and enables no live execution. Index-point P&L is synthetic.

```bash
pytest                                  # Phase 1 + Phase 2 tests
python scripts/phase2_verify_report.py  # re-derive every number in the performance report
python scripts/phase2_audit_data.py     # independent dataset / timestamp audit
python scripts/phase2_build_docs.py     # regenerate rule_registry.yaml/.md and source_traceability.md
python scripts/phase2_signal_counts.py  # descriptive record counts per interpretation (not for tuning)
```

Start with `docs/phase2/agent_review_report.md`, then `ambiguous_rules.md`. Code: `src/nifty_trading/strategies/` (engines, rule registry, proposals),
`src/nifty_trading/data/sessions.py` (5-minute candles, warm-up), `src/nifty_trading/core/exit_policy.py` (exit specification).
Timestamps are start-of-minute labels: the 09:15 five-minute candle is rows 09:15–09:19 and is usable at 09:20.
