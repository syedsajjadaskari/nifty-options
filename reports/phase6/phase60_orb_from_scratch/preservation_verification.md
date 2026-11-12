# Preservation verification

Method: `scripts/phase60_snapshot.py before` hashed (SHA-256) every file under data/, reports/, docs/, src/, tests/, scripts/, pyproject.toml and README.md **before any Phase 6.0 file was written**; `verify` re-hashed everything afterwards.

| check | result |
|---|---|
| files before | 18961 |
| pre-existing files changed | 0 |
| pre-existing files removed | 0 |
| new files outside the Phase 6.0 prefixes | 0 |
| new files (Phase 6.0) | 26 |
| PRESERVED | True |


New files by prefix: {"reports/phase6/phase60_orb_from_scratch/": 0, "src/nifty_trading/research/orb_v2/": 16, "tests/test_phase60_": 1, "scripts/phase60_": 9}

Not modified: Phase 3.6 frozen strategies, Phase 4.0 data and reports, Phase 5.3 strategy code, Phase 5.5 ledgers, Phase 5.6 reconciliation, Phase 5.7 charts, Phase 5.8 and 5.9 packages, the manual journal, raw/processed market data, the five-strategy controller. The old ORB engines and the shared controller were only read (the Phase 5.5 ledgers were read for the comparison). Nothing was committed or pushed; no orders were placed. `.DS_Store` files are excluded from the hash set.