# Combined five-strategy backtest (Phase 6.2)

**Synthetic NIFTY index-point P&L x 390 units (6 lots x 65; legs 195 + 195); the index is not tradable and this is NOT option profit. Research only: no orders, no configuration selected, not optimised, not out-of-sample.** The shared controller, exit policy, stops (IRF/PDR/PDS/RF 35, ORB 30), T1 27, T2 (IRF/ORB/RF 60, PDR/PDS 70), post-T1 stop entry -/+ 6, 13:00 cutoff and 15:14-open forced exit are the frozen ones; nothing was edited.

A = Phase 3.6 frozen; B = Phase 5.3 author-corrected (legacy ORB); C = IRF V2 + ORB V2 (provisional ORB-V2-A; the standalone 30/60 exits are NOT used) + PDR/PDS first-eligible + RF; D1 = IRF V2 + legacy ORB (diagnostic: identical to B because IRF V2 == Phase 5.3 IRF); D2 = frozen IRF + ORB V2 (diagnostic attribution of the ORB change). D is attribution only, not a selection device.

## Primary window 2025-09-01 .. 2026-08-31 (5paisa)

| config | trades | win_rate_pct | profit_factor | gross_points | gross_rs | net_rs_70 | max_drawdown_rs |
|---|---|---|---|---|---|---|---|
| A | 196 | 59.69 | 1.284 | 763.5 | 297765.0 | 284045.0 | 130650.0 |
| B | 188 | 58.51 | 1.25 | 662.95 | 258550.5 | 245390.5 | 204145.5 |
| C | 183 | 53.55 | 1.033 | 95.95 | 37420.5 | 24610.5 | 239830.5 |
| D1 | 188 | 58.51 | 1.25 | 662.95 | 258550.5 | 245390.5 | 204145.5 |
| D2 | 200 | 54.5 | 1.065 | 199.525 | 77814.75 | 63814.75 | 167680.5 |


Confirmed signals A/B/C: 1083 / 1109 / 1095 (IRF 874 / 786 / 786; ORB 53 / 53 / 39; PDR 87 / 147 / 147; PDS 57 / 111 / 111; RF 12 / 12 / 12).

## Strategy contributions inside each portfolio (NOT standalone profits; they must not be added to a portfolio figure)

| config | strategy | trades | win_rate_pct | profit_factor | gross_points_total | max_drawdown_rs | avg_holding_minutes | gross_synthetic_rs | net_rs_70_per_trade | initial_stop_pct | t1_pct | t2_pct | post_t1_stop_pct | forced_exit_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | ALL | 196 | 59.69 | 1.284 | 763.5 | 130650.0 | 49.9 | 297765.0 | 284045.0 | 39.8 | 59.7 | 33.2 | 26.5 | 0.5 |
| A | IRF | 109 | 55.05 | 0.983 | -29.25 | 163215.0 | 43.2 | -11407.5 | -19037.5 | 45.0 | 55.0 | 29.4 | 25.7 | 0.0 |
| A | ORB | 41 | 65.85 | 1.838 | 355.05 | 36445.5 | 38.9 | 138469.5 | 135599.5 | 34.1 | 65.9 | 36.6 | 29.3 | 0.0 |
| A | PDR | 25 | 64.0 | 1.792 | 242.15 | 35685.0 | 67.3 | 94438.5 | 92688.5 | 32.0 | 64.0 | 40.0 | 24.0 | 4.0 |
| A | PDS | 11 | 72.73 | 2.959 | 206.55 | 27475.5 | 79.8 | 80554.5 | 79784.5 | 27.3 | 72.7 | 54.5 | 18.2 | 0.0 |
| A | RF | 10 | 60.0 | 0.921 | -11.0 | 36855.0 | 92.9 | -4290.0 | -4990.0 | 40.0 | 60.0 | 20.0 | 40.0 | 0.0 |
| B | ALL | 188 | 58.51 | 1.25 | 662.95 | 204145.5 | 52.5 | 258550.5 | 245390.5 | 41.0 | 58.5 | 33.0 | 25.0 | 1.1 |
| B | IRF | 90 | 52.22 | 0.942 | -87.825 | 204555.0 | 45.0 | -34251.75 | -40551.75 | 47.8 | 52.2 | 31.1 | 21.1 | 0.0 |
| B | ORB | 41 | 65.85 | 1.838 | 355.05 | 36445.5 | 38.9 | 138469.5 | 135599.5 | 34.1 | 65.9 | 36.6 | 29.3 | 0.0 |
| B | PDR | 28 | 67.86 | 1.925 | 278.5 | 35490.0 | 64.9 | 108615.0 | 106655.0 | 28.6 | 67.9 | 35.7 | 32.1 | 3.6 |
| B | PDS | 19 | 57.89 | 1.457 | 128.225 | 64155.0 | 78.2 | 50007.75 | 48677.75 | 42.1 | 57.9 | 36.8 | 15.8 | 5.3 |
| B | RF | 10 | 60.0 | 0.921 | -11.0 | 36855.0 | 92.9 | -4290.0 | -4990.0 | 40.0 | 60.0 | 20.0 | 40.0 | 0.0 |
| C | ALL | 183 | 53.55 | 1.033 | 95.95 | 239830.5 | 51.6 | 37420.5 | 24610.5 | 45.9 | 53.6 | 30.1 | 23.0 | 1.1 |
| C | IRF | 85 | 48.24 | 0.794 | -317.825 | 207684.75 | 45.4 | -123951.75 | -129901.75 | 51.8 | 48.2 | 28.2 | 20.0 | 0.0 |
| C | ORB | 39 | 48.72 | 0.932 | -40.95 | 83245.5 | 26.2 | -15970.5 | -18700.5 | 51.3 | 48.7 | 28.2 | 20.5 | 0.0 |
| C | PDR | 31 | 67.74 | 1.9 | 302.5 | 35490.0 | 69.7 | 117975.0 | 115805.0 | 29.0 | 67.7 | 35.5 | 32.3 | 3.2 |
| C | PDS | 19 | 57.89 | 1.457 | 128.225 | 64155.0 | 78.2 | 50007.75 | 48677.75 | 42.1 | 57.9 | 36.8 | 15.8 | 5.3 |
| C | RF | 9 | 66.67 | 1.229 | 24.0 | 36855.0 | 102.7 | 9360.0 | 8730.0 | 33.3 | 66.7 | 22.2 | 44.4 | 0.0 |


ORB V2 inside configuration C: 39 trades, gross -40.95 weighted points (Rs -15,970), profit factor 0.932; the frozen ORB inside A: 41 trades, +355.05 points (Rs +138,470), profit factor 1.838. The standalone ORB V2 backtest of Phase 6.0 (30/60 on one lot, 75 units) is a different exit model and is unchanged; the two must not be compared as if they were the same trades.

## Cost scenarios, primary window (net synthetic Rs)

| label | A | B | C |
|---|---|---|---|
| Gross synthetic index P&L (no cost) | 297765.0 | 258550.5 | 37420.5 |
| Rs 70 per completed trade | 284045.0 | 245390.5 | 24610.5 |
| Rs 70 per order fill (entry + each exit leg) | 256605.0 | 219070.5 | -1009.5 |
| Rs 70 per trade + 0.25 pt slippage per side | 245825.0 | 208730.5 | -11074.5 |
| Rs 70 per trade + 0.5 pt slippage per side | 207605.0 | 172070.5 | -46759.5 |
| Rs 70 per trade + 1 pt slippage per side | 131165.0 | 98750.5 | -118129.5 |


Rs 70 is the owner's indicative estimate (brokerage ~Rs 30 + charges ~Rs 40), not a verified bill. 'Per order fill' = Rs 70 on the entry and on each exit leg actually filled; slippage is adverse points on every unit of every fill (no unit charged twice). The old Rs 500 assumption is not used.

## Robustness window 2022-09-01 .. 2025-08-31 (5paisa, Phase 4 store)

| config | trades | win_rate_pct | profit_factor | gross_points | gross_rs | net_rs_70 | max_drawdown_rs |
|---|---|---|---|---|---|---|---|
| A | 609 | 57.8 | 1.149 | 1306.15 | 509398.5 | 466768.5 | 188340.75 |
| B | 598 | 56.86 | 1.044 | 391.125 | 152538.75 | 110678.75 | 282798.75 |
| C | 603 | 57.21 | 1.082 | 721.525 | 281394.75 | 239184.75 | 283793.25 |
| D1 | 598 | 56.86 | 1.044 | 391.125 | 152538.75 | 110678.75 | 282798.75 |
| D2 | 633 | 57.82 | 1.155 | 1410.35 | 550036.5 | 505726.5 | 215494.5 |


| label | A | B | C |
|---|---|---|---|
| Gross synthetic index P&L (no cost) | 509398.5 | 152538.75 | 281394.75 |
| Rs 70 per completed trade | 466768.5 | 110678.75 | 239184.75 |
| Rs 70 per order fill (entry + each exit leg) | 381508.5 | 26958.75 | 154764.75 |
| Rs 70 per trade + 0.25 pt slippage per side | 348013.5 | -5931.25 | 121599.75 |
| Rs 70 per trade + 0.5 pt slippage per side | 229258.5 | -122541.25 | 4014.75 |
| Rs 70 per trade + 1 pt slippage per side | -8251.5 | -355761.25 | -231155.25 |


## Gross Rs by calendar year

| window | calendar_year | A | B | C |
|---|---|---|---|---|
| A | 2025 | 221061.75 | 245602.5 | 105787.5 |
| A | 2026 | 76703.25 | 12948.0 | -68367.0 |
| B | 2022 | -96690.75 | -148083.0 | -146932.5 |
| B | 2023 | 462949.5 | 232586.25 | 149847.75 |
| B | 2024 | 6483.75 | -8024.25 | 130074.75 |
| B | 2025 | 136656.0 | 76059.75 | 148404.75 |


Neither window is untouched out-of-sample (the 2025-26 window shaped earlier research; the 2022-25 window was used in Phases 4-5). Results differ strongly year to year in every configuration.

## Controller states (primary window)

| config | DAY_FINISHED | SECOND_TRADE_ELIGIBLE | READY_FOR_FIRST_TRADE | UNRESOLVED_EXECUTION | sessions_with_a_trade |
|---|---|---|---|---|---|
| A | 123 | 65 | 57 | 2 | 188 |
| B | 115 | 60 | 71 | 1 | 175 |
| C | 103 | 68 | 74 | 2 | 171 |

