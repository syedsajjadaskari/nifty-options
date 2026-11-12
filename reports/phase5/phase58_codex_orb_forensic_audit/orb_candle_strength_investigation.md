# Candle confirmation investigation

Original pp.3-7 require convincing directional body and limited adverse wick; pp.9-10 allow a suitably positioned pin. The figures illustrate shape qualitatively. No source gives60%,20%,33%,2x or30%. Pixel measurement of an illustrative PDF candle cannot establish a historical OHLC ratio or a numerical trading threshold.

Reference strong-body threshold is MODERATE: body/range>=60%, opposite wick/range<=20% with1e-9 ratio tolerance. Pin: favourable wick>=2x body and close in favourable30%, also tolerance1e-9 in price geometry. Gap separately rejects adverse wick>=33%. Methods1/2 do not run that33% flag, but their baseline strong/pin routes already cap it below33%; that omission has no extra baseline acceptance effect. Original pin predicate can admit a red long, explicitly rejected by handwritten p.5. Colour candidate removes such signals; it cannot repair missing trades.

Every examined opening candle has O,H,L,C, absolute body/range, body percentage, upper/lower wick and close location in `orb_all_manual_journal_dates.csv`, `orb_13_handwritten_disputes.csv` and daily files. Every method/direction also has signed distance beyond its actual level in `orb_method_paths.csv`; negative means close stayed short of level. Both directions remain visible: a green candle does not prove the author wanted a long. The handwritten source supplies no author candle/level, so exact source-example ratio matching is unavailable.

LOOSE50%/25% replaces one numerical profile only. It is a sensitivity analysis of an unspecified numeric family, not evidence that50%/25% is correct. Removing quality altogether would contradict an explicit qualitative source filter and is not proposed. Thin/doji first candles and large rejection do not become proven valid simply because a cutoff has no printed percentage.

Failure counts below are directional paths on evaluable journal-ORB dates, including gates not reached because a prior gate failed. They overlap. Opposite-direction failures are not proof the author's unknown-direction trade was invalid. `sole_failed_gate_dates` identifies where a numerical gate alone prevents that path; it still does not validate the counterfactual trade.

| method | direction | failed_dates | evaluated_dates | reached_and_failed_dates | sole_failed_gate_dates |
|---|---|---|---|---|---|
| Method 1 | LONG | 54 | 85 | 3 | 3 |
| Method 1 | SHORT | 61 | 85 | 9 | 9 |
| Method 2 | LONG | 54 | 85 | 0 | 0 |
| Method 2 | SHORT | 61 | 85 | 7 | 7 |
| Gap/200DMA | LONG | 54 | 85 | 8 | 8 |
| Gap/200DMA | SHORT | 61 | 85 | 2 | 2 |

| variant | added_method_direction_signals | removed_method_direction_signals | changed_handwritten_dates | authority |
|---|---|---|---|---|
| strength_loose | 13 | 0 | ['2025-12-12', '2025-12-30'] | NUMERIC_SENSITIVITY_ONLY |
| colour | 0 | 3 | [] | AUTHOR_CLARIFIED_LONG_MIRRORED_SHORT |