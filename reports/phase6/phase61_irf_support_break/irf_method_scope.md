# IRF method scope

| method | uses the first-red-candle support break? | why | V2 treatment |
|---|---|---|---|
| Method 1 | No | source: the very next candle closing back inside the range is the trigger; 'no support or resistance break is required' | frozen mechanism |
| Method 2A | YES | source: support = a low formed during the extension; the owner approved the first red candle's wick low as that support | explicit state machine |
| Method 2B | No | its reference is a RESISTANCE (top of the first push); the red candle confirms the failure, it does not create a level; extending the rule needs owner approval | frozen mechanism |
| Method 3 | No | its support is 'formed by the preceding candles' and the sweep candle itself must close below it; a separate compulsory break | frozen mechanism |


28-point EMA clearance: applied to all four methods (provisional scope; the guide has no EMA text). Rejected candidates in the primary window: 514 (by method {'Method 1': 82, 'Method 2A': 265, 'Method 2B': 167}). Dated handwritten cases outside the approved scope (Method 2B) are reported as out of scope, not reconciled (`irf_handwritten_cases.csv`).