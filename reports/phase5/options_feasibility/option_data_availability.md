# Phase 5 - historical option-data availability (BANKNIFTY and SENSEX)

HISTORICAL RESEARCH ONLY. The strategy was developed using later NIFTY data; nothing here is a validation of the strategy, a forecast, or advice. Every result is an INDEX-POINT result; no option premium is used or estimated, and an index-point gain is not an option-premium gain.

**Conclusion: a historical option-premium backtest is NOT possible with the data available to this project, and none was run.** The strategy's signals, stops and targets come from the underlying index; the option leg would need the premium history of the contract that existed on each signal date. That history cannot be requested because the contract's identifier is unavailable (below). No option price was estimated, interpolated, modelled or inferred from index points; no journal contains an option execution.

## 1. What the broker offers (verified by probes of this phase, `option_probe_results.json`)

| index | CE contracts listed | PE contracts listed | expiries listed | earliest expiry listed | latest expiry listed | lot sizes in the master | any expired contract listed? |
|---|---|---|---|---|---|---|---|
| BANKNIFTY | 1109 | 1109 | 4 | 2026-11-23 | 2027-03-30 | [30] | no |
| SENSEX | 2026 | 2025 | 20 | 2026-11-05 | 2031-06-26 | [20, 25] | no |

* **The instrument master lists only live contracts** (earliest listed expiry is after the download date for both indices). The scrip code of a contract that existed on, say, 2023-03-15 is not in it, and no archive of earlier masters exists in this project (the Phase 1 copy of 2026-11-01 differs from the 2026-11-05 copy only by newly listed contracts and one delisted far-OTM SENSEX contract).
* The historical-candle API is keyed by scrip code only (no symbol, strike or expiry parameters), so an expired contract cannot be requested without a code. The documentation does not say whether expired contracts are served: **not stated**; it could not be tested because no expired code is available (the one contract that left the master, `SENSEX 31 DEC 2026 CE 87000`, returned EMPTY - it is a far-dated illiquid strike that was delisted before expiry, so this is not conclusive). A recheck can be made after the next SENSEX weekly expiry has passed (the codes of the 2026-11-05 expiry are saved in `option_probe_results.json`).
* For **live** contracts, one-minute premium candles are served (timestamp, open, high, low, close, volume): see the table below. There is **no bid, ask, spread or open interest** in the response (the documentation lists none and none was returned), so a premium-OHLC simulation could only be a lower-confidence model even where it exists.

| index | type | expiry | strike | status | 1-min rows (6-month request) | first bar | dates | bars with volume | share of flat bars |
|---|---|---|---|---|---|---|---|---|---|
| BANKNIFTY | CE | 2026-11-23 | 57,800 | COMPLETED | 3086 | 2026-09-11T11:17 | 34 | 3086 | 0.4637 |
| BANKNIFTY | PE | 2026-11-23 | 57,800 | COMPLETED | 73 | 2026-09-29T14:58 | 14 | 72 | 0.8767 |
| BANKNIFTY | CE | 2026-11-23 | 58,200 | COMPLETED | 2732 | 2026-09-17T09:36 | 33 | 2732 | 0.5673 |
| BANKNIFTY | PE | 2026-11-23 | 58,200 | COMPLETED | 9 | 2026-09-22T14:15 | 5 | 9 | 0.8889 |
| BANKNIFTY | CE | 2026-11-23 | 58,000 | COMPLETED | 11242 | 2026-08-26T09:26 | 48 | 11228 | 0.2661 |
| BANKNIFTY | PE | 2026-11-23 | 58,000 | COMPLETED | 5680 | 2026-08-28T14:11 | 46 | 5675 | 0.4613 |
| BANKNIFTY | CE | 2026-12-29 | 57,800 | COMPLETED | 550 | 2026-10-09T09:36 | 18 | 550 | 0.8564 |
| BANKNIFTY | PE | 2026-12-29 | 57,800 | COMPLETED | 18 | 2026-10-05T14:07 | 9 | 18 | 0.8333 |
| BANKNIFTY | CE | 2026-12-29 | 58,200 | EMPTY | 0 |  |  |  |  |
| BANKNIFTY | PE | 2026-12-29 | 58,200 | COMPLETED | 9 | 2026-10-15T15:28 | 4 | 9 | 1.0 |
| BANKNIFTY | CE | 2026-12-29 | 58,000 | COMPLETED | 3384 | 2026-10-07T12:16 | 20 | 3384 | 0.6271 |
| BANKNIFTY | PE | 2026-12-29 | 58,000 | COMPLETED | 1000 | 2026-09-30T13:45 | 24 | 1000 | 0.677 |
| SENSEX | CE | 2026-11-05 | 76,800 | COMPLETED | 1540 | 2026-10-30T09:16 | 4 | 1540 | 0.0006 |
| SENSEX | PE | 2026-11-05 | 76,800 | COMPLETED | 779 | 2026-11-02T12:03 | 3 | 779 | 0.0103 |
| SENSEX | CE | 2026-11-05 | 77,200 | COMPLETED | 1538 | 2026-10-30T09:15 | 4 | 1538 | 0.0065 |
| SENSEX | PE | 2026-11-05 | 77,200 | COMPLETED | 753 | 2026-11-03T09:17 | 2 | 753 | 0.0412 |
| SENSEX | CE | 2026-11-05 | 77,000 | COMPLETED | 3225 | 2026-10-14T13:07 | 13 | 3225 | 0.1594 |
| SENSEX | PE | 2026-11-05 | 77,000 | COMPLETED | 1232 | 2026-10-23T11:51 | 9 | 1232 | 0.2451 |
| SENSEX | CE | 2026-11-12 | 76,800 | COMPLETED | 586 | 2026-10-30T15:11 | 3 | 586 | 0.3072 |
| SENSEX | PE | 2026-11-12 | 76,800 | COMPLETED | 562 | 2026-11-02T12:47 | 3 | 562 | 0.3256 |
| SENSEX | CE | 2026-11-12 | 77,200 | COMPLETED | 382 | 2026-11-02T09:37 | 2 | 382 | 0.1021 |
| SENSEX | PE | 2026-11-12 | 77,200 | COMPLETED | 514 | 2026-11-03T09:17 | 2 | 514 | 0.284 |
| SENSEX | CE | 2026-11-12 | 77,000 | COMPLETED | 1521 | 2026-10-23T11:16 | 9 | 1521 | 0.1834 |
| SENSEX | PE | 2026-11-12 | 77,000 | COMPLETED | 767 | 2026-10-29T13:34 | 4 | 767 | 0.1591 |
| SENSEX | CE | 2026-12-31 | 87,000 | EMPTY | 0 |  |  |  |  |

Strikes were chosen near the index's last daily close in the 5paisa daily file (BANKNIFTY 58,025 on 2026-08-31, SENSEX 76,957 on 2026-08-31), **not** near the spot on the probe date (2026-11-05), so 'near the money' means near those closes. What the table shows: history exists only from roughly when a contract became active (days for SENSEX weeklies, up to about ten weeks for a BANKNIFTY monthly), and out-of-the-money strikes are very illiquid (a handful of bars in months). Liquidity, not data format, would limit any simulation.

## 2. Overlap of live contracts with the backtest window

Contracts live today with a minute history starting inside the main window exist only for its last days (BANKNIFTY monthly contracts from late 2026-08). They are not the contracts a nearest-expiry policy would have chosen then, and using them would be a policy choice that has not been made, so they were not used.

## 3. Legitimate sources that would make it possible (none acquired; none purchased)

* **Daily end-of-day option data** (NSE/BSE F&O bhavcopy): free archives exist, but they are one price per contract per day - not usable to simulate a minute-level entry and exit. Terms of use of the free archive were not confirmed; NSE also sells official end-of-day data.
* **Minute-level expired-option data**: some brokers' data APIs advertise rolling expired-option data by strike offset (for example Dhan: minute data for up to five years, ATM +/- offsets; documentation seen only second-hand, coverage of SENSEX unconfirmed); Zerodha's forum states its API does not serve expired option candles; commercial vendors sell one-minute option history. Any of these needs an account, a licence check and an owner decision before use.
* **Forward collection**: store the broker master and the live contracts' minute candles every day from now on. This is the only route that uses the current broker connection and produces an auditable record; it would take months to be useful.

## 4. Exchange rules that a future option backtest must respect (NOT verified against exchange circulars)

The figures below come from broker and news summaries found by search, not from NSE/BSE circulars, and must be verified before use. They show that nothing about contract size or expiry may be assumed constant:

| period (as reported) | BANKNIFTY (NSE) | SENSEX (BSE) |
|---|---|---|
| 2018-2019 | lot size and expiry structure for 2018-19 not established by the searches; weekly and monthly expiries existed | options existed but were very thinly traded; contract details not established |
| 2020-07 | lot 20 -> 25 for contracts expiring on/after 2020-07-30 | - |
| 2023 | lot 25 -> 15 for contracts after the June 2023 monthly expiry; weekly expiry day moved to Wednesday in 2023 | weekly SENSEX options introduced in 2023 (Friday expiry) |
| 2024-11 | lot 15 -> 30 for contracts introduced from 2024-11-20; **weekly BANKNIFTY options discontinued** (last weekly around 2024-11-13); monthly/quarterly only | lot 10 -> 20 for contracts introduced after 2024-11-20 |
| 2025 | lot 30 -> 35 (reported effective 2025-04-25), then back to 30 (circular FAOP70616, 2025-10-03, from the contracts after 2025-12-30); monthly expiry moved to the last Tuesday | weekly expiry Friday -> Tuesday from 2025-01 (reported), later Thursday (the 2026-11 master shows Thursday expiries) |
| 2026-11 (the live master) | monthly expiries only; lot 30; expiry dates are Mondays/Tuesdays (a holiday moves the last Tuesday to the previous trading day) | 20 weekly expiries listed (Thursday), lot 20, and 25 for contracts from 2027-01 |

Sources (secondary, to be verified): [Fyers notice](https://fyers.in/notice-board/revision-in-index-derivatives-contracts-lot-size/), [Angel One](https://www.angelone.in/announcements/market/revision-in-lot-size-of-index-derivative), [5paisa news](https://www.5paisa.com/news/nse-revises-lot-sizes-for-key-index-derivatives-starting-november-2024), [Groww](https://groww.in/blog/important-updates-from-nse-and-bse-regarding-index-derivatives), [Business Standard](https://www.business-standard.com/markets/stock-market-news/sensex-bankex-sensex-50-expiry-days-to-change-from-january-1-bse-124112801317_1.html). Conflicting reports exist (for example the SENSEX weekly day after 2025-09), which is why none of this is used as a rule.

## 5. Technical requirements before any option paper trading

1. A source of historical premiums with bid/ask (or an owner-accepted lower-confidence OHLC model) for expired contracts, with a licence check. 2. A daily archive of the broker's instrument master. 3. A verified contract-specification table per date (lot size, expiry day, strike step, trading hours). 4. An option execution model (entry at which price, spread, slippage, liquidity limits, exit on index triggers) approved by the owner. 5. The infrastructure gaps recorded in Phase 4 (streaming prices, order state, risk and duplicate-order controls).
