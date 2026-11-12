"""EMA(period) of 5-minute closes, recursive from the first value (alpha = 2 / (period + 1)), TradingView-style. Independent of data/sessions.causal_ema (which seeds with a
200-value SMA and returns NaN for the first 199 values); the two converge after a few hundred candles and the audit measures the residual difference."""

from __future__ import annotations

import numpy as np


def ema_series(closes: np.ndarray, period: int = 200) -> np.ndarray:
    alpha = 2.0 / (period + 1.0)
    out = np.empty(len(closes))
    if len(closes) == 0:
        return out
    out[0] = closes[0]
    for i in range(1, len(closes)):
        out[i] = alpha * closes[i] + (1.0 - alpha) * out[i - 1]
    return out
