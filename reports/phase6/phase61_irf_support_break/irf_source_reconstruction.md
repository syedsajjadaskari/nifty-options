# IRF source reconstruction (Phase 6.1)

Source: `IRF_Strategy_Guide Updated.pdf` (14 pages; text in `docs/extracted_text/`). The worked examples in the guide use illustrative prices (the guide says so: 'Prices are illustrative only'; the resistance-break example quotes levels 'taken from a NIFTY 50 five-minute session' without a date), so they cannot be tied to a historical session; the dated evidence is the author's handwritten correction pages (Phase 5.3 transcription; not re-read here).

Fixed parameters: first 5-minute candle 09:15-09:20 = initial range (IRH/IRL, wicks included); short only; target 60; stop 35 or 40 by the distance to the most recent green candle (the repository's baseline uses 35). Closes confirm; wicks never do.

| method | sequence | level | entry |
|---|---|---|---|
| Method 1 | close above IRH; the very next candle closes back inside the range | none (no support/resistance break required) | close of the failure candle |
| Method 2A | close above IRH -> extension -> red candle -> a candle closes below recent support | 'a low formed by recent candles during the extension, such as a pullback low' | close below that support |
| Method 2B | close above IRH -> first push tops out (resistance) -> price trades back above it -> red candle -> a red candle closes back below the resistance | a RESISTANCE (top of the first push) | close of that red candle |
| Method 3 | small candles inside the range -> red sweep candle with ~60-70% of its upper wick above IRH -> closes below recent support (compulsory) | 'recent support formed by the preceding candles' | close of the sweep candle |


Trend / EMA: the guide contains no EMA or trend condition. The 28-point EMA clearance is an owner clarification (number approved; measure provisional). Rejections: a red candle alone, a wick-only break, no close above IRH, an immediate close back inside (that is Method 1), insisting on a support break for Method 2.

Execution / risk: unresolved in the guide (trades per day, time window, re-arming: IRF-GLOBAL-004) are handled by the shared controller (one trade, second trade only after a full stop and only PDR/PDS, 13:00 cutoff).