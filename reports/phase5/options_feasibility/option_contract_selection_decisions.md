# Phase 5 - option contract selection: DECISIONS REQUIRING OWNER APPROVAL

HISTORICAL RESEARCH ONLY. The strategy was developed using later NIFTY data; nothing here is a validation of the strategy, a forecast, or advice. Every result is an INDEX-POINT result; no option premium is used or estimated, and an index-point gain is not an option-premium gain.

**Nothing in this file is an approved rule, and no option result is presented as a strategy.** The mapping 'bullish index signal -> buy CALL (CE); bearish index signal -> buy PUT (PE)' is the owner's stated intent; everything else below is an open question, listed with a *candidate* only so the question is concrete. No candidate was run, tuned or chosen for its historical return, and no strike, expiry or days-to-expiry was selected by looking at results.

| # | decision needed | candidate (NOT approved) | why it matters / what must be verified first |
|---|---|---|---|
| D1 | Long options only? (an index short signal = buy PE; never sell a naked option) | yes, long CE/PE only, as stated | defines risk (premium paid) and margin; owner to confirm no spreads or hedges |
| D2 | Strike selection | nearest-to-the-money strike to the signal-minute index price (ties: owner to say) | delta, premium and liquidity change sharply with moneyness; far strikes are illiquid (see the probe); the strike step differs by index and period |
| D3 | Expiry selection | a stated rule such as 'the nearest expiry with at least N trading days left' - N and the rule are open | BANKNIFTY weeklies existed until 2024-11 and monthlies only after; SENSEX weeklies exist from 2023; expiry weekdays changed; near-expiry premiums behave very differently |
| D4 | Lot size per date | the exchange lot in force for the contract on the trade date (from circulars, verified) | lot sizes changed several times (BANKNIFTY 20, 25, 15, 30, 35, 30); the frozen 390-unit sizing (6 x 65) is a NIFTY device and does not apply |
| D5 | Position sizing | owner to define lots per signal and how the two exit legs (3 + 3 lots in the index model) map to option lots | minimum lot granularity; the leg split needs an even lot count |
| D6 | Entry price | the option's own next traded price after the index signal; requires bid/ask or a stated lower-confidence OHLC model | premium-candle open is not a price at which an order is certain to fill |
| D7 | Exit trigger and price | exit when the INDEX hits its stop / T1 / T2 / post-T1 stop / 15:14 (as frozen), at the option's price at that minute | the index stop of 35 points is a different (smaller or larger) move in premium depending on delta |
| D8 | Costs and slippage | brokerage, exchange charges, STT on options, stamp duty, GST, plus spread and slippage per fill - owner to approve the schedule | premium is small; fixed costs matter more than for the index model |
| D9 | Liquidity filter | skip a signal if the chosen contract has no volume in the entry minute - threshold open | illiquid strikes would make fills fictional |
| D10 | Index-point parameters | unchanged in this phase (the brief forbids optimising); whether to rescale them to the index level in a later phase is an owner decision | at 0.04-0.07% of the index, a 35-point stop is inside ordinary noise for BANKNIFTY and SENSEX |
| D11 | Historical data source | which licensed source supplies expired-option minute data (see `option_data_availability.md`) | without it there is no backtest |

Only after D1-D11 are answered, and a premium source exists, can a clearly labelled option-premium research run be designed (Report B of the brief). Until then Report B does not exist.
