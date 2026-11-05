# Data source discovery (Phase 4)

**Written for:** the strategy owner. Question: can reliable one-minute NIFTY 50 history be obtained for 2022-09..2025-08 (Window B), 2018 (Window C) and 2019 (Window D)? Every row below was tested by retrieving real candles and checking the returned timestamps and prices, not by HTTP status.

## Answer in one table

| period | 5paisa 1-minute (authenticated API) | secondary source (technovusin repository) | what was run |
|---|---|---|---|
| 2018-01-01 .. 2018-12-31 (C) | **UNAVAILABLE**: every monthly request returned an empty response (no error, no rows) | available, 245 sessions | secondary vendor only, EXPLORATORY (nothing to check it against) |
| 2019-01-01 .. 2019-02-28 (D, part) | **UNAVAILABLE** (empty) | available | secondary vendor only |
| 2019-03-01 .. 2019-12-31 (D, part) | AVAILABLE, but **5 sessions missing** (2019-06-27, 06-28, 07-01, 07-02, 07-03) | available, all 244 sessions of the year | both, reported separately: 5paisa PARTIAL YEAR and secondary full year |
| 2022-09-01 .. 2025-08-31 (B) | AVAILABLE, 743 of 744 expected sessions (the missing one, 2022-10-24, has a daily candle but no minute rows in either vendor; consistent with an evening Muhurat session) | available, 743 sessions | 5paisa (main result); secondary vendor as a sensitivity run |
| 2025-09-01 .. 2026-08-31 (A) | Phase 1 dataset (unchanged) | available (overlap audit only) | the existing Phase 3.6 backtest, not rerun |

5paisa **daily** candles are available back to at least 2017-01-02 (requested 2017-01-01 .. 2025-08-31: 18 requests, 2,143 daily bars), which supplies the official daily close, the 200-day averages the strategies need and an independent trading-day reference for every window.

## 5paisa historical API

Documentation: https://xstream.5paisa.com/dev-docs/market-data-system/historical-candles (one-minute interval, at most six months per request). Retrieval used the project's authenticated, read-only `BrokerClient` (order methods are disabled in that class) and the project's verified NIFTY 50 index mapping (`data/metadata/nifty50_instrument.json`: exchange N, segment C, scrip code 999920000). Credentials were never printed or written to any report. Requests were monthly (1-minute) or six-monthly (daily), rate-limited, retried, resumable (`data/raw/phase4_5paisa/manifest.json`), and every response was saved **unmodified** with its SHA-256.

| outcome class | count |
|---|---|
| COMPLETED 1-minute months | 47 |
| COMPLETED daily spans | 18 |
| EMPTY (API answered with no rows) | 14 |
| RATE_LIMITED | 0 |
| ACCESS_DENIED | 0 |
| FAILED | 0 |

Empty monthly requests: 2018-01, 2018-02, 2018-03, 2018-04, 2018-05, 2018-06, 2018-07, 2018-08, 2018-09, 2018-10, 2018-11, 2018-12, 2019-01, 2019-02 (all of 2018 and 2019-01 / 2019-02). The first returned bar is **2019-03-01 09:15** (a request spanning 2019-02-09..2019-03-01 returned exactly the 376 bars of 2019-03-01). The empty answers are not errors: the API accepts the request and returns nothing, so supported request syntax does not imply data exists for every year. The initial exploratory probes (before the resumable fetcher) are kept in `reports/phase4/data/probe_5paisa_initial.json`:

| window | rows | first bar |
|---|---|---|
| 2025-09-01..2025-09-05 | 1880 | 2025-09-01T09:15:00 |
| 2025-01-02..2025-01-08 | 1880 | 2025-01-02T09:15:00 |
| 2024-06-03..2024-06-07 | 1880 | 2024-06-03T09:15:00 |
| 2023-06-01..2023-06-07 | 1880 | 2023-06-01T09:15:00 |
| 2022-09-01..2022-09-07 | 1880 | 2022-09-01T09:15:00 |
| 2022-01-03..2022-01-07 | 1880 | 2022-01-03T09:15:00 |
| 2021-01-04..2021-01-08 | 1879 | 2021-01-04T09:15:00 |
| 2020-01-01..2020-01-08 | 2256 | 2020-01-01T09:15:00 |
| 2019-06-03..2019-06-07 | 1504 | 2019-06-03T09:15:00 |
| 2019-01-01..2019-01-08 | 0 |  |
| 2018-06-01..2018-06-07 | 0 |  |
| 2018-01-01..2018-01-08 | 0 |  |

Provider quirks found in the retrieved data: identical duplicated blocks inside the responses of 2022-10-10 and 2023-09-27 (660 duplicate rows removed, no conflicting values); a frozen-price feed on 2023-10-19 (the session is excluded by the quality gate); the DAILY candles carry float32 noise (for example 8210.0996), removed by rounding to 2 decimals in the processed copy only, while the 1-minute responses carry none (maximum deviation from 2 decimals recorded in `data_provenance_build.json`: 0.0); a 15:30 closing-print stub on 99% of sessions; Volume is always 0.

## Secondary source: github.com/technovusin/nifty50-historical-data

* Repository verified to exist; pinned commit **f1e07e7d236c1860bab6f5b7002fd46f0739595c** (2026-11-04T10:05:16Z: "Add NIFTY data for 04 November 2026"). Files downloaded from `raw.githubusercontent.com` at that commit into `data/raw/phase4_technovusin/f1e07e7d236c1860bab6f5b7002fd46f0739595c/` (a separate namespace) with SHA-256 and the repository's own git blob SHA-1, which was recomputed from the downloaded bytes and matched for all 20 files (an integrity check against the repository, **not** an independent check of the market data).
* Files used: 1-minute CSVs for 2017 (warm-up only), 2018, 2019, 2022, 2023, 2024, 2025 and the monthly 2026 files (overlap audit). Columns: Epoch, Timestamp (ISO, IST), Open, High, Low, Close (Volume only in 2026).
* Licence: the repository carries an MIT licence. **The underlying data vendor is not named, and nothing establishes the licence of the data itself**; the repository was created on 2026-09-09 and is updated daily. Treat it as an unattributed convenience dataset.
* The README discloses cleaning that changes the data: bars outside 09:15-15:29 removed (so there is no 15:30 stub); duplicate bars with stray seconds removed (Aug-Sep 2021); **three bad first candles of 2022 were edited (High / Low adjusted to include Open: 25 Mar, 30 Mar, 7 Apr)**; suspicious partial or spurious sessions removed (7 Aug 2021 ... 30 Apr 2022); prices rounded to 2 decimals. The README keeps the Muhurat evening bars (12 Nov 2023, 1 Nov 2024) as an exception to its 09:15-15:29 rule and says **nothing about cleaning for 2018-2019, so whether those years were edited is unverifiable**. Known remaining quirks per the README: some single minutes missing, a few frozen-price stretches (24 Feb 2021 outage, March 2020 circuit breakers). Those edited dates lie outside the Phase 4 windows, but they show the files are curated, not raw.
* Timestamp convention verified against the 5paisa data by a one-minute shift test: agreement is highest at zero shift in every overlap (below), so both vendors label a bar by its START.

### Vendor-overlap audit (bar by bar, regular window 09:15-15:29)

| overlap | dates in both | only secondary | bars compared | OHLC identical | close within 0.05 | mean |close diff| | p99 |close diff| | max |close diff| | days with a diff > 1 point |
|---|---|---|---|---|---|---|---|---|---|
| 2019-03..2019-12 | 196 | 5 | 73,444 | 0.0% | 26.3% | 0.3969 | 4.85 | 65.15 | 195 |
| 2022-08..2025-08 | 761 | 0 | 284,776 | 39.8% | 53.6% | 0.3212 | 2.4 | 76.7 | 599 |
| 2025-09..2026-08 | 248 | 0 | 92,685 | 74.3% | 87.5% | 0.0888 | 1.45 | 52.85 | 152 |

**The vendors' minute bars are not equivalent.** They agree on which sessions exist and on the timestamp convention, but the prices differ systematically, most in 2019 and 2022-25 and least in 2025-26. The 09:15 bar differs most (the first-bar open differs by about 4 points in 2019 and 6 points in 2022-25 on average; see the first-bar table below): IRF, ORB and the gap-based strategies are built on that first candle. The effect on the trades is quantified in `vendor_sensitivity.csv` and below. **No provider equivalence is claimed.** For 2018 there is no overlap at all, so the secondary data cannot be checked against another vendor for that year.

### The 09:15 bar: each vendor's first-minute open against the 5paisa DAILY open

| source | sessions | within 0.05 | within 0.5 | mean absolute difference (points) |
|---|---|---|---|---|
| B: 5paisa minutes (own daily) | 739 | 29% | 32% | 5.95 |
| B: secondary minutes (vs 5paisa daily) | 739 | 99% | 99% | 0.06 |
| D 2019-03..12: 5paisa minutes | 196 | 38% | 43% | 2.23 |
| D 2019 full: secondary minutes | 244 | 5% | 23% | 2.27 |
| C 2018: secondary minutes | 245 | 2% | 18% | 2.39 |
| A 2025-26 (Phase 3.6 baseline): 5paisa Phase 1 minutes | 247 | 31% | 36% | 6.66 |

The relationship **reverses with the period**: in 2022-25 the secondary vendor's first open matches the 5paisa daily open almost always while 5paisa's own first minute rarely does; in 2019 it is the other way round. The Phase 3.6 baseline (Window A) rests on 5paisa's first-minute convention, which in 2022-25 differs from its own daily open by about 6 points on average. **Which first-bar convention matches the exchange is not established**; the vendor-sensitivity result (same strategies, same window, different bars: Rs 509k vs Rs 626k gross, 71.5% signal agreement) is the practical consequence, and neither vendor can be called right on the evidence available.

## Reconciliation policy (nothing is silently merged)

| input | source | role |
|---|---|---|
| 1-minute candles | ONE source per run: 5paisa or the secondary vendor, never mixed within a run | signals, entries, exits |
| daily candles | always the 5paisa daily series (a separately identified input) | official previous close (gap), daily 200-day averages, trading-day reference; **not** used to price any entry or exit |
| calendar | derived (see `data_quality_by_year.md`) | holidays and special sessions |

The 5paisa daily close is the official close; the last 15:29 minute close differs from it by 6-13 points on average (it is not the official close), which is why the official daily series is needed. Using 5paisa daily data with the secondary vendor's minutes is a documented mixed-source run; every trade carries both source ids and the partition SHA-256.

## Contract sizes (disclosure; not used in any P&L)

The fixed 390-unit multiplier (6 lots x 65) is a comparison device, **not** a claim that six lots of 65 units were executable in any year. Public reporting (secondary sources; the primary NSE circulars were not retrieved and the dates below are unverified) indicates NIFTY lot sizes changed several times: 75 until 2021 (NSE circular NSE/FAOP/47854 dated 2021-03-31 reduced it to 50), 50 until 2024, then 25 (from 2024-04-26 per reports), 75 for contracts introduced from 2024-11-20, and 65 from NSE circular NSE/FAOP/70616 of 2025-10-03. Sources: [Angel One](https://www.angelone.in/news/market-updates/nse-reduces-lot-sizes-in-nifty-and-bank-nifty-derivatives), [Business Standard 2021-04-01](https://www.business-standard.com/amp/article/markets/national-stock-exchange-cuts-mkt-lot-size-for-nifty-50-derivative-contracts-121040100377_1.html), [NSE circular archive](https://archives.nseindia.com/content/circulars/FAOP47854.pdf). Reliable per-day contract specifications were **not** established, so no result is expressed in actual lots. The NIFTY 50 cash index is not tradable; futures or options would add basis, premium decay, margin and spread that this synthetic series ignores.
