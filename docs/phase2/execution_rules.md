# Execution rules (Task 3 verification + Task 9 specification)

Source: `NIFTY_System_Trading_Strategy_Performance.docx`. Every printed number was re-derived by `scripts/phase2_verify_report.py` (41 arithmetic checks, **all pass**; output in
`reports/phase2/performance_report_verification.md`). **Nothing here was fitted to reproduce the report**, and the report's aggregates do *not* prove that any signal rule is correct.
All P&L is in NIFTY spot **points** × quantity; NIFTY 50 is an index, so every figure is **synthetic**.

## 1. Verified statements (quoted/paraphrased from the report, with the section they sit in)

| Item | What the report says | Section | Verified |
|---|---|---|---|
| Period | 189 logged trades, September 2025 – August 2026, 180 trading days | intro; Calculation Basis | stated |
| Total position | 6 lots = **390 quantity at 65 per lot**; two equal legs of 3 lots (**195 qty each**) | intro; Strategy Framework | 6×65 = 390 ✔ |
| Target 1 | **27 points**, Leg 1 (3 lots) booked there | intro | 27×195 = ₹5,265 ✔ (matches the stated BE profit) |
| Target 2 | "**60 or 70 points, as recorded**", Leg 2 (3 lots) | intro | **no assignment rule given** → AMB-EXE-01 |
| Initial stop | not stated in the report; "SL = stop distance × 390" | Calculation Basis | per-strategy stops come from the strategy guides (IRF 35/40, ORB 30) |
| Breakeven | "once Target 1 is booked, the stop on Leg 2 **moves to the entry price**" | Strategy Framework | ✔ (BE trade = ₹5,265) |
| Outcomes | Target (T1+T2) · Breakeven (T1, then entry) · Stop-loss (both legs, full 390) | Strategy Framework | counts 80 / 44 / 65 = 189 ✔ |
| P&L | points × quantity: Target = 27×195 + T2×195; BE = 27×195; SL = stop distance × 390 | Calculation Basis | ✔ |
| Costs | brokerage, taxes, slippage **excluded**; ₹1,00,000 capital is an assumption | Calculation Basis | stated |
| Drawdown | on **cumulative P&L after each trade**, trades ordered by date and entry time | Calculation Basis | ₹68,055 = 5,85,000 − 5,16,945 ✔; June-2026 anatomy sums ✔ |
| Win-rate / profit factor definitions | win rate = Target ÷ (Target + SL) = 80/145 = 55.17 %; PF = (Target + BE) ÷ SL = 1.93 | Calculation Basis | ✔ |

## 2. Derived from the report's own tables (**DERIVED — not source rules**)

* All payoffs are integer multiples of 195 qty-points, so each cell decomposes uniquely.
* **Target-2 mix:** the Target total ₹13,68,900 over 80 winners solves uniquely to **74 trades at T2 = 60 and 6 at T2 = 70**. Decomposing the PDR/PDS monthly cells (every cell has a unique decomposition) puts all six 70s in **PDR (5 of 6 winners) and PDS (1 of 3)**; the other **74 winners (IRF 30, ORB 35, RF 6, PDR 1, PDS 2) used 60**.
  *Consequence:* the PDR/PDS guides' "70 fixed" was not what the report records on three winners.
* **Stop distances implied by totals:** ORB 36 stops = ₹4,21,200 ⇒ exactly 30 each ✔ (matches ORB p.1). IRF 21 stops = ₹3,06,150 ⇒ 11×35 + 10×40 if only 35/40 are used ✔ (matches IRF p.2).
  **RF 8 stops = ₹1,03,350 ⇒ average 33.1 points; impossible with only 35/40** (needs ≥ 3 stops of 30). The RF guide says 35–40.
* The journal cannot supply per-trade stop or Target-2 distances; see `source_document_inventory.md` for why it is not reliable.

## 3. Exit-policy model (implemented in `src/nifty_trading/core/exit_policy.py`, unit-tested in `tests/test_phase2_exit_policy.py`)

| Parameter | Value / source | Status |
|---|---|---|
| Quantity | 390 = 6 lots × 65; Leg 1 = Leg 2 = 195 | verified |
| Target 1 | entry ± 27 (long +, short −), Leg 1 | verified |
| Target 2 | long `entry + T2`, short `entry − T2`; **IRF 60 · ORB 60 · PDR 70* · PDS 70* · RF unresolved** | *guide value; conflicts with the report (AMB-EXE-01) |
| Initial stop | long `entry − SL`, short `entry + SL`; **ORB 30 (verified) · IRF 35/40 by the green-candle rule (proposal for the measurement) · PDS 35/40 same · PDR unresolved · RF unresolved** | mixed |
| After Target 1 | Leg 2 stop → entry (breakeven). `breakeven_after_t1=False` is rejected: no source defines it | verified |
| End of day | **not defined by the source**; default `LEAVE_OPEN` ⇒ outcome `Incomplete` (never counted as a win); `EXIT_AT_LAST_CLOSE` exists only as a labelled research option | unresolved |
| Costs / slippage | excluded (as in the report) | verified |

`RF_TARGET_STATUS = UNRESOLVED`: `policy_for("RF")` returns `t2_points=None`, `stop_points=None`, and `evaluate_exit` returns `NotEvaluable` rather than guessing.
`policy_for("PDR")` has a 70 target but **no stop** (selection rule absent) ⇒ also `NotEvaluable`.

### Worked checks (all are unit tests)
| Case | Result |
|---|---|
| Long, T1 then T2=60 | `Target`, ₹16,965 (= 27×195 + 60×195) |
| Long, T1 then back to entry | `BE`, ₹5,265 |
| Long, stop 30 | `SL`, −₹11,700 (= 30×390); short mirrored |
| IRF p.10 example | entry 24,123.50 → SL 24,158.50 (35), T1 24,096.50, T2 24,063.50 |
| Breakeven gapped through | opens 20 below entry ⇒ Leg 2 at the open, ₹1,365 (not ₹5,265) |
| 35/40 boundary | d = 34.99 → 35; d = 35.00 → 35 (≤, PROPOSED); d = 35.01 → 40; no green candle → unresolved (never guessed) |

## 4. Event ordering and partial fills (PROPOSED_CONSERVATIVE — 1-minute bars do not reveal intrabar order)

Bars start at the 1-minute row labelled with the signal candle's `bar_end` (the first minute after the entry reference).

1. **Before Target 1** (stop = initial stop): if one bar touches both the stop and T1 ⇒ record an **ambiguity**, resolve as **STOP** (full 390 qty at the stop).
2. T1 touched alone ⇒ Leg 1 (195) books at exactly T1; the Leg 2 stop moves to entry.
3. **Same bar** touches T1 and the breakeven level ⇒ ambiguity, resolved as **BREAKEVEN** (Leg 2 out at entry), even if T2 was also touched.
4. T1 and T2 in the same bar with no breakeven touch ⇒ both booked (a continuous path must cross T1 first).
5. **After Target 1**: a bar touching both Leg-2 stop and T2 ⇒ ambiguity, resolved as **STOP/BE**.
6. **No favourable fills:** a stop **or breakeven stop** gapped through fills at the *worse* of (level, bar open) — e.g. long entry 24,000, T1 booked, next bar opens 23,980 ⇒ Leg 2 out at 23,980 (₹1,365, not ₹5,265); a target fills at its level, never at a better open. (Found by the independent review, M-1.)
7. Bars exhausted with the position open ⇒ `Incomplete` (only a booked Leg 1 is realised). No assumption is made about an end-of-day exit.
8. Every ambiguity is returned in `ExitResult.ambiguities`; none is hidden or resolved in the strategy's favour.

## 5. What would be needed to validate historical execution
A per-trade record of: date; **entry timestamp (candle label convention stated)**; strategy **and method**; direction; entry price; stop distance; Target-2 distance used; exit timestamps and prices for each leg (or at least which of T1/T2/BE/SL was hit and when). The current journal has only date, entry time, strategy and outcome — and contradicts the report on counts and dates.
The aggregate report **cannot** validate or reproduce the signals, and no reproduction is claimed.
