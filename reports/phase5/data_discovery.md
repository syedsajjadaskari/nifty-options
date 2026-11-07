# Phase 5 - data discovery (BANKNIFTY and SENSEX index candles)

HISTORICAL RESEARCH ONLY. The strategy was developed using later NIFTY data; nothing here is a validation of the strategy, a forecast, or advice. Every result is an INDEX-POINT result; no option premium is used or estimated, and an index-point gain is not an option-premium gain.

## 1. Instruments (resolved from the broker's current instrument master, never copied from NIFTY)

| index | exchange | segment | scrip code | master name | master full name | index it should be | look-alike rows (ETF / fund, not the index) rejected |
|---|---|---|---|---|---|---|---|
| BANKNIFTY | NSE (N) | C (cash / index) | 999920005 | BANKNIFTY | BANKNIFTY | Nifty Bank | 0 |
| SENSEX | BSE (B) | C (cash / index) | 999901 | SENSEX | (blank in the master) | S&P BSE Sensex | 0 |

Master copy: `data/raw/phase5_instrument_master/scrip_master_20261105T024711Z.csv` (SHA-256 `85054710c0b40552...`), downloaded from the broker's public ScripMaster endpoint during this phase; the Phase 1 copy (2026-11-01) was not touched. Selection rule: exchange, cash/index segment, exact name, and an index-range scrip code (>= 999000) - a unique row in both cases. Look-alike names in the same segment (ETFs and funds such as `BANKBEES`, `SENSEXBEES`, `BANKNIFTY1`) are listed in each instrument JSON as rejected. The master gives no full name for SENSEX, so its identity as the S&P BSE Sensex rests on the BSE index code, the exchange, and the price level: probes returned closes of 26,600-31,300 (2017), 32,600-38,900 (2018), 35,400-41,700 (2019), 56,400-60,600 (2022-08..09) and 76,900-81,300 (2025-26), which are the Sensex's levels, and the minute and daily series agree with each other (see `data_quality_report.md`). The same level argument holds for BANKNIFTY (23,700-28,300 in 2018, 37,600-41,500 in 2022-08..09, 57,000-58,000 in 2026). NIFTY's own identifiers (exchange N, code 999920000) were not reused: BANKNIFTY happens to be NSE index code 999920005 and SENSEX is on a different exchange (BSE, 999901).

## 2. 5paisa historical-candle API: what was verified

Official reference: <https://xstream.5paisa.com/dev-docs/market-data-system/historical-candles> (read for this phase). It states: intervals 1, 5, 10, 15, 30, 60 minutes and 1 day; at most 6 months per request for intraday intervals; a candle carries timestamp, open, high, low, close and volume only (no bid, ask or open interest); identification by scrip code only; the timestamp convention, the timezone and any lookback limit are **not stated**; no licence or redistribution terms are stated on the page (the site's Terms and Conditions were not read). The purpose given is 'strategy deployment'.

What the API actually returned (small probes, saved unmodified under `data/raw/<index>/5paisa/probe/`, summary in `reports/phase5/<index>/probe_results.json`):

| index | probe | interval | requested | status | rows | first | last | dates |
|---|---|---|---|---|---|---|---|---|
| BANKNIFTY | recent_week | 1m | 2026-08-24..2026-08-28 | COMPLETED | 1880 | 2026-08-24T09:15 | 2026-08-28T15:30 | 5 |
| BANKNIFTY | window_a_start | 1m | 2025-09-01..2025-09-05 | COMPLETED | 1880 | 2025-09-01T09:15 | 2025-09-05T15:30 | 5 |
| BANKNIFTY | main_start | 1m | 2022-09-01..2022-09-07 | COMPLETED | 1880 | 2022-09-01T09:15 | 2022-09-07T15:30 | 5 |
| BANKNIFTY | pre_main_2022_01 | 1m | 2022-01-03..2022-01-07 | COMPLETED | 1880 | 2022-01-03T09:15 | 2022-01-07T15:30 | 5 |
| BANKNIFTY | 2021_12 | 1m | 2021-12-01..2021-12-07 | COMPLETED | 1880 | 2021-12-01T09:15 | 2021-12-07T15:30 | 5 |
| BANKNIFTY | 2019_06 | 1m | 2019-06-03..2019-06-07 | COMPLETED | 1504 | 2019-06-03T09:15 | 2019-06-07T15:30 | 4 |
| BANKNIFTY | 2019_03 | 1m | 2019-03-01..2019-03-08 | COMPLETED | 1878 | 2019-03-01T09:15 | 2019-03-08T15:30 | 5 |
| BANKNIFTY | 2019_01 | 1m | 2019-01-01..2019-01-31 | EMPTY | 0 |  |  |  |
| BANKNIFTY | 2018_06 | 1m | 2018-06-04..2018-06-08 | EMPTY | 0 |  |  |  |
| BANKNIFTY | 2018_01 | 1m | 2018-01-01..2018-01-31 | EMPTY | 0 |  |  |  |
| BANKNIFTY | 2017 | 1m | 2017-06-01..2017-06-30 | EMPTY | 0 |  |  |  |
| BANKNIFTY | interval_check | 1d | 2026-08-24..2026-08-28 | COMPLETED | 5 | 2026-08-24T00:00 | 2026-08-28T00:00 | 5 |
| BANKNIFTY | daily_2018 | 1d | 2018-01-01..2018-12-31 | COMPLETED | 246 | 2018-01-01T00:00 | 2018-12-31T00:00 | 246 |
| BANKNIFTY | daily_2019 | 1d | 2019-01-01..2019-12-31 | COMPLETED | 244 | 2019-01-01T00:00 | 2019-12-31T00:00 | 244 |
| BANKNIFTY | daily_2017 | 1d | 2017-01-01..2017-06-30 | COMPLETED | 123 | 2017-01-02T00:00 | 2017-06-30T00:00 | 123 |
| BANKNIFTY | daily_2022_09 | 1d | 2022-08-01..2022-09-30 | COMPLETED | 42 | 2022-08-01T00:00 | 2022-09-30T00:00 | 42 |
| SENSEX | recent_week | 1m | 2026-08-24..2026-08-28 | COMPLETED | 1880 | 2026-08-24T09:15 | 2026-08-28T15:30 | 5 |
| SENSEX | window_a_start | 1m | 2025-09-01..2025-09-05 | COMPLETED | 1880 | 2025-09-01T09:15 | 2025-09-05T15:30 | 5 |
| SENSEX | main_start | 1m | 2022-09-01..2022-09-07 | COMPLETED | 1880 | 2022-09-01T09:15 | 2022-09-07T15:30 | 5 |
| SENSEX | pre_main_2022_01 | 1m | 2022-01-03..2022-01-07 | COMPLETED | 1880 | 2022-01-03T09:15 | 2022-01-07T15:30 | 5 |
| SENSEX | 2021_12 | 1m | 2021-12-01..2021-12-07 | COMPLETED | 1880 | 2021-12-01T09:15 | 2021-12-07T15:30 | 5 |
| SENSEX | 2019_06 | 1m | 2019-06-03..2019-06-07 | COMPLETED | 1504 | 2019-06-03T09:15 | 2019-06-07T15:30 | 4 |
| SENSEX | 2019_03 | 1m | 2019-03-01..2019-03-08 | COMPLETED | 1880 | 2019-03-01T09:15 | 2019-03-08T15:30 | 5 |
| SENSEX | 2019_01 | 1m | 2019-01-01..2019-01-31 | EMPTY | 0 |  |  |  |
| SENSEX | 2018_06 | 1m | 2018-06-04..2018-06-08 | EMPTY | 0 |  |  |  |
| SENSEX | 2018_01 | 1m | 2018-01-01..2018-01-31 | EMPTY | 0 |  |  |  |
| SENSEX | 2017 | 1m | 2017-06-01..2017-06-30 | EMPTY | 0 |  |  |  |
| SENSEX | interval_check | 1d | 2026-08-24..2026-08-28 | COMPLETED | 5 | 2026-08-24T00:00 | 2026-08-28T00:00 | 5 |
| SENSEX | daily_2018 | 1d | 2018-01-01..2018-12-31 | COMPLETED | 246 | 2018-01-01T00:00 | 2018-12-31T00:00 | 246 |
| SENSEX | daily_2019 | 1d | 2019-01-01..2019-12-31 | COMPLETED | 245 | 2019-01-01T00:00 | 2019-12-31T00:00 | 245 |
| SENSEX | daily_2017 | 1d | 2017-01-01..2017-06-30 | COMPLETED | 123 | 2017-01-02T00:00 | 2017-06-30T00:00 | 123 |
| SENSEX | daily_2022_09 | 1d | 2022-08-01..2022-09-30 | COMPLETED | 42 | 2022-08-01T00:00 | 2022-09-30T00:00 | 42 |

Intervals 5m, 10m, 15m, 30m, 60m and 1d were all served for both indices (recent week). One-minute bars start at 09:15 and the series ends at **15:30**: each session has 376 rows - 375 regular bars labelled 09:15-15:29 and one **15:30 stub** bar - exactly like the NIFTY series; the stub is not a tradable bar and is handled by the frozen session logic. Bars are labelled by their START in IST (the overlap test below shows the secondary source uses the same convention). **One-minute data do not exist on 5paisa before 2019-03-01 for either index**: every monthly request for 2018-01..2019-02 returned EMPTY (the API accepts the request and returns nothing), exactly as for NIFTY.

## 3. Retrieval and coverage actually obtained

| index | 1-minute monthly requests | daily requests (6-month spans) | minute months retrieved | daily span | failed / rate-limited / denied |
|---|---|---|---|---|---|
| BANKNIFTY | 59 completed / 14 empty (2018-01..2019-02) | 20 completed | 2019-03..2019-12 and 2022-08..2026-08 | 2017-01-01..2026-08-31 | 0 |
| SENSEX | 59 completed / 14 empty (2018-01..2019-02) | 20 completed | 2019-03..2019-12 and 2022-08..2026-08 | 2017-01-01..2026-08-31 | 0 |

Requests were monthly (1-minute) or six-monthly (daily), rate-limited, retried, resumable and each response saved unmodified with its SHA-256 and a classified status (`data/raw/<index>/5paisa/manifest.json`). 2020-2021 minute data were not requested (not needed by any window).

## 4. Secondary sources for the years 5paisa cannot supply (2018 and 2019-01..02)

Searches for a legitimate source found two GitHub repositories (both MIT-licensed, by the same author) that carry one-minute index files; the licence is that of the repository, the files are described only as 'extracted from a reliable financial data provider' - **the data vendor is not named and the licence of the underlying data is not established**. Other candidates were not used: a repository with no licence shown (`aeron7/nifty-banknifty-intraday-data`), paid vendors, and Kaggle datasets that need an account. Everything from these repositories is therefore labelled EXPLORATORY and is never merged with 5paisa data.

| index | repository | pinned commit | commit date | licence | file SHA-256 | bytes | rows | duplicate rows removed | conflicting duplicates |
|---|---|---|---|---|---|---|---|---|---|
| BANKNIFTY | https://github.com/sandeepkapri/BankNifty-Data | 6bdda6e571dd | 2026-04-23 | MIT | 5826b09aa9149440 | 67,508,825 | 1046599 | 3690 | 0 |
| SENSEX | https://github.com/sandeepkapri/Sensex-Minute-Data | e385abcde715 | 2024-04-09 | MIT | 68f696ac420bbe57 | 34,628,664 | 554948 | 0 | 0 |

Each file's git blob SHA-1 was recomputed from the downloaded bytes and equals the repository's tree listing (an integrity check against the repository, **not** a check of the market data). Coverage and quirks found:

* **BANKNIFTY** file: 2015-01-09 .. 2026-04-22, 375 bars per session (09:15-15:29), no 15:30 stub, covers all of 2018 and 2019. From 2023-11-28 to 2024-03-22 (82 sessions) it contains an exactly duplicated block of rows (3,690 rows in all); the duplicates are identical (zero conflicting) and were removed, keeping the last. Evening Muhurat sessions are present as 60-row sessions and are excluded by the session gate.
* **SENSEX** file: 2018-03-08 .. 2024-03-22 - **2018-01-01..2018-03-07 is not in it**, so 2018 is a partial year (about 200 of 246 sessions); the first two sessions (2018-03-08: 7 bars, 2018-03-09: 62 bars) are truncated at the file start. 2019-01-23..2019-02-04 carries a single placeholder row per session (nine sessions) that the session gate excludes (no opening candle).

## 5. Do the two vendors agree? (overlap audit, regular bars 09:15-15:29, bar by bar)

| index | overlap | dates in both | bars compared | identical (all four prices) | close within 0.05 | mean abs close diff | p99 | max | days with a diff > 1 pt | timestamp-shift test (share equal at -1/0/+1 min) |
|---|---|---|---|---|---|---|---|---|---|---|
| BANKNIFTY | 2019-03..2019-12 | 196 | 73,448 | 0.2513 | 0.4102 | 1.5588 | 19.05 | 368.85 | 196 | {"-1": 0.0054, "0": 0.4102, "1": 0.0064} |
| BANKNIFTY | 2022-08..2026-04-22 | 919 | 343,698 | 0.458 | 0.5785 | 1.0141 | 8.6 | 365.8 | 918 | {"-1": 0.0048, "0": 0.5785, "1": 0.0047} |
| SENSEX | 2019-03..2019-12 | 201 | 75,345 | 0.6836 | 0.8418 | 0.2005 | 3.33 | 72.39 | 201 | {"-1": 0.0048, "0": 0.8418, "1": 0.0047} |
| SENSEX | 2022-08..2024-03-22 | 406 | 151,931 | 0.777 | 0.8817 | 0.3141 | 4.9 | 250.61 | 406 | {"-1": 0.0031, "0": 0.8817, "1": 0.0031} |

The timestamp convention is identical (shifting by one minute destroys agreement), but **the two vendors' bars are not the same data**: BANKNIFTY agrees exactly on well under half of the bars with differences up to hundreds of points; SENSEX agrees much better but still differs. No provider equivalence is claimed. For 2018 there is no overlap at all, so that year cannot be checked against anything.

### The 09:15 bar: each source's first one-minute open against the 5paisa DAILY open

| index | window (minute source) | sessions | within 0.05 | within 0.5 | mean abs diff (points) |
|---|---|---|---|---|---|
| BANKNIFTY | M | 987 | 21% | 23% | 20.08 |
| BANKNIFTY | MS | 385 | 100% | 100% | 0.0 |
| BANKNIFTY | D_5P | 196 | 36% | 36% | 9.89 |
| BANKNIFTY | D_TV | 244 | 100% | 100% | 0.0 |
| BANKNIFTY | C | 245 | 100% | 100% | 0.0 |
| SENSEX | M | 983 | 40% | 41% | 26.43 |
| SENSEX | MS | 385 | 88% | 89% | 3.76 |
| SENSEX | D_5P | 201 | 52% | 52% | 13.88 |
| SENSEX | D_TV | 244 | 97% | 98% | 0.6 |
| SENSEX | C | 199 | 16% | 17% | 23.45 |

IRF, ORB and the gap-based logic are built on the first candle, so a vendor difference here moves signals. Which vendor's first bar matches the exchange's is **not established**.

## 6. Policy (nothing is silently merged)

* One minute source per run; never mixed. Raw responses, processed Parquet (ZSTD) and manifests live in per-index namespaces (`data/raw/<index>/5paisa`, `data/raw/<index>/secondary_kapri/<commit>`, `data/processed/<index>/<source id>`), separate from NIFTY.
* The 5paisa **daily** series of the same index is always used for the official close, the daily moving averages and the trading-day reference (a disclosed mixed-source run for the secondary-source windows, as in Phase 4); its role is recorded in every trade (`daily_source_id`).
* Windows: **M** main 2022-09-01..2026-08-31 (5paisa), **MS** 2022-09-01..2024-03-22 with the secondary source (vendor sensitivity, the dates where both secondary files exist), **C** 2018 (secondary, EXPLORATORY), **D_5P** 2019-03-01..2019-12-31 (5paisa, PARTIAL YEAR), **D_TV** 2019 (secondary, EXPLORATORY).
* Exchange rules by period: the closing-auction regime is applied only from the date and only for the index whose own data show it (section 3 of `data_quality_report.md`); no later rule is applied to earlier sessions.

## 7. Licensing and permitted use

5paisa's data are used through the account's own API for research, read-only. The documentation page states no redistribution terms and the Terms and Conditions were not read; the raw and processed vendor data are therefore **kept under `data/` (raw is git-ignored) and should not be published or committed without checking the terms**. The two repositories are MIT-licensed as repositories; the licence of the data they carry is unknown, so the secondary-source results are exploratory research only.
