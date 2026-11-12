# Test results

## New Phase 6.0 tests (`tests/test_phase60_orb_v2.py`)

```
.....................................................                    [100%]
53 passed in 51.46s
```

## Full repository suite

```
........................................................................ [ 68%]
........................................................................ [ 77%]
........................................................................ [ 85%]
...............................x........................................ [ 94%]
...............................................                          [100%]
837 passed, 1 skipped, 1 xfailed in 137.26s (0:02:17)
```

## ruff (whole repository)

```
All checks passed!
```

Coverage of the required list: 09:15-09:20 aggregation and 09:20 availability, session boundaries (incomplete candles, 15:30 stub), EMA calculation and prefix invariance, EMA crossing and already-beyond scenarios, gap above the previous high and below the previous low, inner support/resistance, multiple qualifying levels, candle direction, wrong-side wick formulas (incl. the rulebook's worked examples), hammer / shooting star / engulfing / full-body, zero-range and doji, gap limits 250 and 300 (boundary and both directions), stop and target calculation, no late entry, no re-entry, forced exit, closing-auction bars, no look-ahead, same-minute stop/target ambiguity, journal match classification, configuration selection and manifests, engine-vs-audit parity, legacy-engine independence and preservation of earlier results.