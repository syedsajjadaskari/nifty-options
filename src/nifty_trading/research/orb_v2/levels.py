"""Previous-day support / resistance (independent research module).

Only COMPLETED previous-session 5-minute candles are used (never today's candles). MAJOR levels are the previous day's high / low (single prices). INNER levels have no mechanical
definition in the rulebook ("how levels are found ... is not yet defined"), so each construction below is an independently selectable, objectively defined, PROVISIONAL candidate. None is
claimed to be the author's method and none was chosen by profitability or journal agreement.

  SWING_FRACTAL_WICK_ZONE  every confirmed swing high / low (k candles each side) other than the day extreme; resistance zone = [body top, high], support zone = [low, body bottom] of the swing candle
  CLUSTER_ZONE             repeated rejection: swing extremes of the same side within ``cluster_tol_points`` of each other form one zone [min, max]; needs >= ``cluster_min_members``
"""

from __future__ import annotations

import pandas as pd

from nifty_trading.research.orb_v2.config import OrbV2Config
from nifty_trading.research.orb_v2.models import Level


def _t(ts) -> str:
    return pd.Timestamp(ts).strftime("%H:%M")


def major_levels(prev: pd.DataFrame) -> list[Level]:
    hi, lo = float(prev["high"].max()), float(prev["low"].min())
    hs = tuple(_t(s) for s in prev.loc[(prev["high"] - hi).abs() < 1e-9, "start"])
    ls = tuple(_t(s) for s in prev.loc[(prev["low"] - lo).abs() < 1e-9, "start"])
    return [Level("RESISTANCE", "MAJOR", "PREV_DAY_HIGH", hi, hi, hs, f"previous-day high {hi:.2f}"), Level("SUPPORT", "MAJOR", "PREV_DAY_LOW", lo, lo, ls, f"previous-day low {lo:.2f}")]


def swing_points(prev: pd.DataFrame, k: int) -> tuple[list[int], list[int]]:
    """Indices of confirmed swing highs / lows (k candles each side, all inside the previous session): strictly beyond the k earlier candles, at least equal to the k later ones."""
    h, l = prev["high"].to_numpy(float), prev["low"].to_numpy(float)
    hs, ls = [], []
    for i in range(k, len(prev) - k):
        if h[i] > h[i - k:i].max() and h[i] >= h[i + 1:i + k + 1].max():
            hs.append(i)
        if l[i] < l[i - k:i].min() and l[i] <= l[i + 1:i + k + 1].min():
            ls.append(i)
    return hs, ls


def inner_levels(prev: pd.DataFrame, cfg: OrbV2Config) -> list[Level]:
    hi, lo = float(prev["high"].max()), float(prev["low"].min())
    hs, ls = swing_points(prev, cfg.swing_k)
    hs = [i for i in hs if abs(prev["high"].iloc[i] - hi) > 1e-9]   # the day extreme is the MAJOR level
    ls = [i for i in ls if abs(prev["low"].iloc[i] - lo) > 1e-9]
    out: list[Level] = []
    if cfg.inner_method == "SWING_FRACTAL_WICK_ZONE":
        for i in hs:
            r = prev.iloc[i]
            out.append(Level("RESISTANCE", "INNER", cfg.inner_method, float(max(r["open"], r["close"])), float(r["high"]), (_t(r["start"]),), f"swing high k={cfg.swing_k} at {_t(r['start'])}"))
        for i in ls:
            r = prev.iloc[i]
            out.append(Level("SUPPORT", "INNER", cfg.inner_method, float(r["low"]), float(min(r["open"], r["close"])), (_t(r["start"]),), f"swing low k={cfg.swing_k} at {_t(r['start'])}"))
        return out
    if cfg.inner_method == "CLUSTER_ZONE":
        for side, idxs, col in (("RESISTANCE", hs, "high"), ("SUPPORT", ls, "low")):
            pts = sorted(((float(prev[col].iloc[i]), i) for i in idxs))
            cl: list[list[tuple[float, int]]] = []
            for p in pts:
                if cl and p[0] - cl[-1][0][0] <= cfg.cluster_tol_points:
                    cl[-1].append(p)
                else:
                    cl.append([p])
            for c in cl:
                if len(c) >= cfg.cluster_min_members:
                    px = [x[0] for x in c]
                    out.append(Level(side, "INNER", cfg.inner_method, min(px), max(px), tuple(_t(prev["start"].iloc[x[1]]) for x in c), f"{len(c)} swing {col}s within {cfg.cluster_tol_points:g} pts"))
        return out
    raise ValueError(cfg.inner_method)


def all_levels(prev: pd.DataFrame, cfg: OrbV2Config) -> list[Level]:
    return major_levels(prev) + inner_levels(prev, cfg)
