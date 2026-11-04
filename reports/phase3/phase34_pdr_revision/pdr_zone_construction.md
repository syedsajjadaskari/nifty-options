# PDR zone construction (research candidates A and B)

**Written for:** the strategy owner. Neither candidate is source-verified: the author fixed the principle (the previous-day high is considered, multiple highs are connected) but not the algorithm.

## Candidate A - day-high anchored

The candle that made the previous session's highest high (first occurrence). Zone = [body top, wick high] of that candle - the wick-only convention that fits the guide's Examples 1, 2 and 4. The ceiling is the previous-day high (PDR-A01). Zone width over the 247 sessions: median 8.25 points, maximum 82.25.

## Candidate B - multiple-high zone

| research parameter | default | why / status |
|---|---|---|
| local high | a candle whose high is not lower than its 1 neighbour on each side | PROPOSED_FOR_REVIEW |
| touches | >= 2 distinct touches | PROPOSED (PDR-A02a) |
| tolerance | a local high within 5.0 points of the day's high joins (the Phase 2.3 shelf tolerance) | PROPOSED (PDR-A02b) |
| separation | members closer than 2 candles count as one touch (one push) | PROPOSED (PDR-A02c) |
| cluster width | not limited; recorded | PROPOSED (PDR-A02d) |
| spike policy | the day's high is ALWAYS included; a shelf below a distant spike is flagged SPIKE_ABOVE_SHELF | PROPOSED (PDR-A02e) |
| lower boundary (B) | lowest body top among the members | PROPOSED (PDR-A02f) |
| lower boundary (A) | body top of the day-high candle | PROPOSED (PDR-A02g) |
| what is a 'high' | non-strict local high, k = 1 | PROPOSED (PDR-A02h) |
| equal day highs | the first candle anchors the zone | PROPOSED (PDR-A02i) |

**A and B are signal-equivalent by construction:** the day's high is always a member of B, so B's ceiling equals A's ceiling on every day; only the floor differs, and under the active rules the floor does not enter any signal decision. The A/B split therefore carries no information about signals; options that would invent no numbers are an exactly-repeated-highs variant or an author-hand-marked zone file for the ~31 signal days.

Over the 247 sessions the zone kind is: ISOLATED_DAY_HIGH 168, MULTIPLE_HIGH_CLUSTER 79. Zone width: median 10.60, maximum 82.25 points. B differs from A on 53 days (floor only); the ceiling is identical on every day. 14 days (A) / 17 days (B) are wider than 30 points (maximum 82.25), which stretches the guide's 'small box'.

## The legacy reversal-swing zone (diagnostic only)

Every record carries the zone the retired Phase 2.3 candidate would have used; it is drawn in grey on the charts and never traded.

## Discrepancy with the guide's figures (documented, not hidden)

* **Example 3 (2025-10-07).** The author's drawn box is a 3.6-point shelf of equal highs (about 25,081-25,084) that excludes the single 14:50 spike (25,095.70); it is not stated whether the exclusion was intended. Candidate A/B keep the spike, as the author asked, so the zone is [25,077.25, 25,095.70] (18.45 points); the open (25,087.55) lies inside it and the preserved open-above-zone rule rejects the day. See `charts/EXAMPLE_3_shelf_vs_spike.svg`.
* **Examples 1, 2 and 4** are day-high zones: the revised zones coincide with the engine's old zones there (within a few points of the drawn boxes).
* Representative multiple-high constructions are in `charts/MULTIHIGH_*.svg`.
