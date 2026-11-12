# Moving-average investigation

PDF pp.2,3,5,7 use EMA or DMA/EMA; pp.8-9 use DMA. In ordinary literal daily terminology SMA200 daily would use200 daily closes, a different horizon from200 five-minute closes. The ORB source does not define a daily formula or say that DMA must literally be daily. Axes-free real screenshots do not identify exact indicator settings. Handwritten p.3 explicitly labels IRF's chart average200 EMA,5min TF; this supports the author's intraday chart convention but does not independently settle ORB.

Reference: EMA200 of concatenated completed5m closes, including the opening close at09:20; alpha2/201, SMA-seeded at candle200. Trend gate uses previous session's last completed5m close against that candle's EMA. Gap prior-close gate uses **official daily close** against the prior last5m EMA, not the prior last5m close used by trend. These two can differ without an arithmetic defect. Current opening average is known only at09:20; no09:15 precomputed-open trade is claimed. Excluding overnight elapsed minutes is standard bar-count computation here, a defined research convention.

Daily SMA200/EMA200 are separately computed from strictly prior official daily closes. Insufficient daily bars produce NaN, never zero or a partly warmed indicator. Their omission from a chart is explicitly labelled unavailable or off scale. No evidence supports replacing the EMA with daily SMA as a confirmed correction. The `gap_daily_sma` sensitivity changes the gap indicator only; Method1/2 trend remains the reference, deliberately isolating the family.

Gap mismatch: frozen open-beyond gate cannot reproduce pp.8-9 schematic geometry where first body spans the line. Isolated gap-candle alternative allows prior-old-side plus directional gap plus (open already beyond OR first range reaches average), with completed close beyond and original quality. It is additive relative to baseline for a fixed indicator. The directional gap and previous-old-side conditions are retained; this is not every first-candle EMA cross.

Fresh independent OHLC aggregation and EMA recurrence results are recorded below. Causal prefix and future-mutation tests supplement arithmetic equality. A fully formed day's classification still uses offline day-quality checks; live adapter parity has not been claimed.

{
  "ohlc_candles_checked": 18525,
  "ohlc_max_error": 0.0,
  "ema_max_error": 1.6370904631912708e-10,
  "failures": []
}

| variant | added_method_direction_signals | removed_method_direction_signals | changed_handwritten_dates | authority |
|---|---|---|---|---|
| gap_candle | 3 | 0 | [] | SOURCE_SUPPORTED_CONFLICTING_TEXT |
| trend_current | 13 | 0 | [] | BASIC_FILTER_ONLY_STRUCTURE_UNRESOLVED |
| gap_daily_sma | 0 | 10 | [] | INDICATOR_SENSITIVITY_NOT_CORRECTION |