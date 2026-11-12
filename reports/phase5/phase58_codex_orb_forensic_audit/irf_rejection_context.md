# IRF selection context: author rejection rules are not assumed

ORB absence does not prove that the later IRF conforms to every handwritten intention. The frozen/Phase53 IRF engines have their own failure-pattern gates; they do not use ORB's universal strong-body filter.

Handwritten p.1 (20250901-1) says '60+ body candle in the entry side'; p.2 (20250917-1) rejects a40%-body/60%-wick IRF candle; p.5 (20251211) rejects a body below50%. Percent interpretation and universal method scope are not fully defined by the first phrase. No universal60%-body veto is present in baseline or Phase53 IRF. These notes are separate from ORB shape rules and must not be silently transferred between strategies.

Handwritten p.4 (20251112-1) and p.5 (20251211) reject IRF at the day's low. Both reference engines omit that veto. The author did not define which low, distance or timing. The CSV measures running lows strictly before the trigger candle and through its completed close; no later low is consulted. Equality/below comparisons are context, not an invented rejection rule.

| Config | Journal-ORB dates executing IRF | First IRF body below60% (diagnostic only) | First IRF close <= known low before trigger (diagnostic only) |
|---|---|---|---|
| A | 34 | 17 | 0 |
| B | 30 | 14 | 0 |
| C | 29 | 13 | 0 |

Every exact signal candle and known-low value is in `irf_first_signal_context.csv` and the extended selection timeline. No IRF change or counterfactual rejection/backtest was run. A source-complete IRF fidelity audit would require resolving the method scope, percentages and reference-low definition; this ORB audit stops at documenting the absent gates and actual selection evidence.
