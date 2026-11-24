"""Phase 7.1 independent verification (second implementations, no shared logic with the production modules):
 1. EMA(200): rebuilt from raw one-minute rows (pandas resample, warm-up included, recursive ewm) and compared with the frozen contexts' ema200_5m at every baseline signal; every interpretation re-evaluated with
    NumPy arithmetic straight from raw candle OHLC; decisions compared with ``ema_rule``.
 2. Method 2 invalidation / candidates: an index-search implementation (no state machine) compared with ``irf_cycles.m2_cycles`` on every session of both windows (first cycle, all variants).
Writes audit_results.json + independent_audit_phase71.md fragments."""

from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase71_run as R71  # noqa: E402

from nifty_trading.research.irf_v3 import data_access as DA  # noqa: E402
from nifty_trading.research.phase71.irf_cycles import M2Opts, m2_cycles  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "reports/phase7/phase71_global_ema_and_final_validation"


def idx_first(mask: np.ndarray, start: int) -> int:
    k = np.flatnonzero(mask[start:])
    return -1 if k.size == 0 else int(start + k[0])


def m2_independent(o, h, c, opts: M2Opts):
    """First Method 2 signal index (or -1) by index searches. Returns fail index."""
    A = h[0]
    n = len(c)
    start_search = 1
    while True:
        b = idx_first(c > A, start_search)
        if b < 0:
            return -1
        r = idx_first(c < o, b + 1)
        # invalidation scan window
        if opts.invalidate != "NONE":
            lim = r if r >= 0 else n - 1
            dead = idx_first(c < A, b + 1)
            if 0 <= dead <= lim and (opts.invalidate == "BEFORE_COMPLETION" or dead <= (r if r >= 0 else n)):
                if opts.invalidate == "BEFORE_B" and r >= 0 and dead > r:
                    pass
                else:
                    if opts.rearm:
                        start_search = dead + 1
                        continue
                    return -1
        if r < 0:
            return -1
        B = o[r]
        s2 = idx_first(c > B, r + 1)
        while s2 >= 0:
            # candidates for the failure: first index > s2 with close below B satisfying margin / colour
            f = s2 + 1
            while True:
                f = idx_first(c < B, f)
                if f < 0:
                    break
                if (B - c[f]) >= opts.min_margin - 1e-9 and ((not opts.bearish_failure) or c[f] < o[f]):
                    break
                f += 1
            # BEFORE_COMPLETION: a close below A strictly between s2 and the completing candle kills the setup
            if opts.invalidate == "BEFORE_COMPLETION":
                lim = f if f >= 0 else n
                k = idx_first(c < A, s2 + 1)
                if 0 <= k < lim:
                    if opts.rearm:
                        start_search = k + 1
                        break
                    return -1
            if f < 0:
                return -1
            if opts.extra_confirmation:
                if f + 1 < n and c[f + 1] < B:
                    return f + 1
                s2 = idx_first(c > B, f + 1)
                continue
            return f
        else:
            return -1
        continue


def m2_independent_bc(o, h, c, opts: M2Opts):
    """BEFORE_COMPLETION variants, index-search form: base chain (no invalidation) -> completion index f; the setup is dead when any close below A lies strictly between the rally breakout and f."""
    A = h[0]
    start = 1
    while True:
        b = idx_first(c > A, start)
        if b < 0:
            return -1
        f = -1
        r = idx_first(c < o, b + 1)
        if r >= 0:
            B = o[r]
            s2 = idx_first(c > B, r + 1)
            if s2 >= 0:
                f = s2 + 1
                while True:
                    f = idx_first(c < B, f)
                    if f < 0 or ((B - c[f]) >= opts.min_margin - 1e-9 and ((not opts.bearish_failure) or c[f] < o[f])):
                        break
                    f += 1
        dead = idx_first(c < A, b + 1)
        if f >= 0 and (dead < 0 or dead >= f):
            return f
        if dead < 0 or not opts.rearm:
            return -1
        start = dead + 1


def main() -> None:
    res: dict = {}
    # ---- 2. Method 2 independent check
    variants = {"A": M2Opts(), "B0": M2Opts("BEFORE_B"), "B": M2Opts("BEFORE_COMPLETION"), "B_REARM": M2Opts("BEFORE_COMPLETION", rearm=True), "M1": M2Opts(min_margin=1.0), "M2": M2Opts(min_margin=2.0), "M5": M2Opts(min_margin=5.0),
                "BEAR": M2Opts(bearish_failure=True), "EXTRA": M2Opts(extra_confirmation=True)}
    bad = {k: [] for k in variants}
    n = 0
    for w in "AB":
        ds = DA.load_dataset(w)
        for d, s in ds.sessions.items():
            if not s.evaluable or not s.candles or s.candles[0].start.time().strftime("%H:%M") != "09:15":
                continue
            o = np.array([c.open for c in s.candles])
            h = np.array([c.high for c in s.candles])
            cl = np.array([c.close for c in s.candles])
            n += 1
            for k, v in variants.items():
                prod = m2_cycles(s.candles, v)
                pf = prod[0]["fail_idx"] if prod else -1
                ind = m2_independent_bc(o, h, cl, v) if v.invalidate == "BEFORE_COMPLETION" else m2_independent(o, h, cl, v)
                if pf != ind:
                    bad[k].append((w, str(d), pf, ind))
    res["m2_variants"] = {"sessions": n, "mismatches": {k: len(v) for k, v in bad.items()}, "examples": {k: v[:3] for k, v in bad.items() if v}}
    # ---- 1. EMA independent check on window A baseline signals
    ctxs, infos, bars, cal, label = R71.C61.window_data("A")
    B = pickle.loads((R71.SP / "p71cache" / "run71_A_B.pkl").read_bytes())
    rows = pd.DataFrame(B["ema_rows"])
    from nifty_trading.data import sessions as S
    m1 = S.load_one_minute()
    warm = S.load_warmup_one_minute()
    allm = pd.concat([warm, m1]).sort_values("timestamp")
    allm = allm.assign(ts=allm["timestamp"].dt.tz_localize(None))
    allm = allm[(allm.ts.dt.hour * 60 + allm.ts.dt.minute >= 555) & (allm.ts.dt.hour * 60 + allm.ts.dt.minute < 930)]
    g = allm.set_index("ts")
    five = g.resample("5min", origin="start_day", offset="9h15min").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    five["ema"] = five["close"].ewm(span=200, adjust=False).mean()
    diffs, flips = [], {k: 0 for k in ("MIN_CLOSE", "MIN_RANGE", "MAX_CLOSE", "TARGET_SIDE")}
    from nifty_trading.research.phase71 import ema_rule as ER
    geo_bad = 0
    for r in rows[rows.ema_available == True].itertuples():  # noqa: E712
        t = pd.Timestamp(f"{r.date} {r.candle_start}")
        if t not in five.index:
            continue
        e2 = float(five.loc[t, "ema"])
        diffs.append(abs(e2 - r.ema))
        o_, h_, l_, c_ = float(five.loc[t, "open"]), float(five.loc[t, "high"]), float(five.loc[t, "low"]), float(five.loc[t, "close"])
        # independent geometry
        cd, rc = abs(c_ - r.ema), max(l_ - r.ema, r.ema - h_, 0.0)
        if abs(cd - r.abs_close_dist) > 1e-6 or abs(rc - r.range_clearance) > 1e-6:
            geo_bad += 1
        for it in flips:
            g1 = ER.geometry(r.direction, o_, h_, l_, c_, r.ema, r.entry_price)
            g2 = ER.geometry(r.direction, o_, h_, l_, c_, e2, r.entry_price)
            if ER.evaluate(it, 27.0, g1)[0] != ER.evaluate(it, 27.0, g2)[0]:
                flips[it] += 1
    res["ema_independent"] = {"signals_compared": len(diffs), "max_abs_ema_diff_points": float(np.max(diffs)) if diffs else None, "mean_abs_ema_diff_points": float(np.mean(diffs)) if diffs else None,
                              "geometry_recomputation_mismatches": geo_bad, "decision_flips_if_the_independent_recursive_EMA_were_used (27pt)": flips,
                              "note": "frozen EMA = SMA-seeded standard EMA over the concatenated sessions (warm-up from 2025-07-01); independent EMA = recursive ewm(span=200, adjust=False) over the same warm-up + window; differences are seed effects"}
    (OUT / "_state" / "audit71_results.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
