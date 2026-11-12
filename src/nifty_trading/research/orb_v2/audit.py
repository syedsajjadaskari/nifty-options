"""Second, independent ORB V2 implementation used ONLY to audit the engine (Phase 6.0 Part 15).

Deliberately different in method: candles via pandas ``resample`` (the engine groups by minute-offset), EMA via ``Series.ewm(span, adjust=False)`` (the engine uses an explicit recursion), swing
points via vectorised neighbour comparisons, wick tests by cross-multiplication (``wick * 5 <= range``), the trade simulated on NumPy arrays (the engine uses Bar objects + the repo's bar classifier).
It imports NOTHING from the engine modules (config values arrive as a plain dict); it shares only the raw one-minute frame, the usable-session list and the official closes with the engine.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def candles_by_day(minutes: pd.DataFrame, usable: list) -> dict:
    out = {}
    for d in usable:
        g = minutes[minutes["_d"] == d].set_index("ts").sort_index()
        g = g[(g.index.time >= pd.Timestamp("09:15").time()) & (g.index.time < pd.Timestamp("15:30").time())]
        origin = pd.Timestamp(d) + pd.Timedelta(hours=9, minutes=15)
        r = g.resample("5min", origin=origin, label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last"})
        r["n"] = g["close"].resample("5min", origin=origin, label="left", closed="left").count()
        r = r[r["n"] == 5].dropna()
        r.index.name = "start"
        out[d] = r.reset_index()
    return out


def add_ema(cbd: dict, usable: list, period: int = 200) -> None:
    allc = pd.concat([cbd[d].assign(_d=d) for d in usable], ignore_index=True)
    allc["ema"] = allc["close"].ewm(span=period, adjust=False).mean()
    for d in usable:
        cbd[d]["ema"] = allc.loc[allc["_d"] == d, "ema"].to_numpy()


def _swings(h: np.ndarray, l: np.ndarray, k: int):
    n = len(h)
    hi, lo = [], []
    for i in range(k, n - k):
        before_h, after_h = h[i - k:i], h[i + 1:i + 1 + k]
        before_l, after_l = l[i - k:i], l[i + 1:i + 1 + k]
        if (h[i] > before_h).all() and (h[i] >= after_h).all():
            hi.append(i)
        if (l[i] < before_l).all() and (l[i] <= after_l).all():
            lo.append(i)
    return hi, lo


def _zones(prev: pd.DataFrame, cfg: dict):
    """(resistance zones [(floor, ceiling)], support zones) including the two majors, per the configured inner construction."""
    h, l = prev["high"].to_numpy(), prev["low"].to_numpy()
    o, c = prev["open"].to_numpy(), prev["close"].to_numpy()
    top, bot = h.max(), l.min()
    res, sup = [(top, top)], [(bot, bot)]
    hi, lo = _swings(h, l, cfg["swing_k"])
    hi = [i for i in hi if abs(h[i] - top) > 1e-9]
    lo = [i for i in lo if abs(l[i] - bot) > 1e-9]
    if cfg["inner_method"] == "SWING_FRACTAL_WICK_ZONE":
        res += [(max(o[i], c[i]), h[i]) for i in hi]
        sup += [(l[i], min(o[i], c[i])) for i in lo]
    else:
        for pts, store in ((sorted(h[i] for i in hi), res), (sorted(l[i] for i in lo), sup)):
            grp: list[list[float]] = []
            for p in pts:
                (grp[-1].append(p) if grp and p - grp[-1][0] <= cfg["cluster_tol_points"] else grp.append([p]))
            store += [(min(g), max(g)) for g in grp if len(g) >= cfg["cluster_min_members"]]
    return res, sup


def _candle(o, h, l, c):
    rng = h - l
    return {"o": o, "h": h, "l": l, "c": c, "rng": rng, "up": h - max(o, c), "lo": min(o, c) - l, "body": abs(c - o), "bl": min(o, c), "bh": max(o, c)}


def decide(day_rows: pd.DataFrame, cdays: pd.DataFrame, prev: pd.DataFrame, prev_full: pd.DataFrame, prev_close: float, cfg: dict) -> dict:
    """Recompute one session's decision. ``cdays`` = today's candles (only row 0 is used); ``prev`` = previous session's continuous candles; ``prev_full`` = all of them (for the EMA)."""
    first = cdays.iloc[0]
    o, h, l, c = float(first["open"]), float(first["high"]), float(first["low"]), float(first["close"])
    m = _candle(o, h, l, c)
    open1 = float(day_rows["open"].iloc[0])
    gap = open1 - prev_close
    ema_now = float(first["ema"])
    failed = []
    if abs(gap) > cfg["max_gap_points"] + 1e-9:
        failed.append("GAP_TOO_LARGE")
    side = "BUY" if c - ema_now > 1e-9 else ("SELL" if ema_now - c > 1e-9 else None)
    zero = m["rng"] <= 1e-9
    if side is None:
        failed.append("EMA_EQUAL")
    if zero:
        failed.append("ZERO_RANGE_CANDLE")
    res = {"direction": side or "", "gap": gap, "ema_now": ema_now}
    if side is None:
        res.update(failed=failed, signal="")
        return res
    resz, supz = _zones(prev, cfg)
    strict = cfg["boundary"] == "STRICT"
    brk = 0
    if side == "BUY":
        for _fl, ce in resz:
            ok = (c > ce) if strict else (c >= ce)
            if ok and (cfg["break_mode"] == "CLOSE_BEYOND" or o <= ce):
                brk += 1
    else:
        for fl, _ce in supz:
            ok = (c < fl) if strict else (c <= fl)
            if ok and (cfg["break_mode"] == "CLOSE_BEYOND" or o >= fl):
                brk += 1
    if brk == 0:
        failed.append("LEVEL_NOT_BROKEN")
    colour = "G" if c > o else ("R" if c < o else "D")
    if colour != ("G" if side == "BUY" else "R"):
        failed.append("COLOUR_MISMATCH")
    good = colour == ("G" if side == "BUY" else "R") and not zero
    lim = cfg["max_bad_wick_pct"]
    bad = m["up"] if side == "BUY" else m["lo"]
    wick_pass = (not zero) and bad <= lim * m["rng"] + 1e-9
    full = good and (m["up"] + m["lo"]) <= cfg["full_body_max_total_wick_pct"] * m["rng"] + 1e-9
    longw, oppw = (m["lo"], m["up"]) if side == "BUY" else (m["up"], m["lo"])
    pin = good and m["body"] > 0 and longw >= cfg["hammer_min_pin_wick_to_body"] * m["body"] - 1e-9 and oppw <= cfg["hammer_max_opposite_wick_pct"] * m["rng"] + 1e-9
    eng = False
    if good and cfg["engulf_reference"] != "NONE":
        r = prev_full if False else prev  # continuous candles only
        po, ph, pl, pc = (float(r[k].iloc[-1]) for k in ("open", "high", "low", "close"))
        pb = abs(pc - po)
        if pb > 0:
            if cfg["engulf_requires_opposite_colour"] and ((pc > po) == (c > o)):
                eng = False
            else:
                eng = m["bl"] <= min(po, pc) + 1e-9 and m["bh"] >= max(po, pc) - 1e-9 and m["body"] > pb
    if not (pin or eng or full):
        failed.append("NO_PATTERN")
    if not zero and not wick_pass:
        failed.append("WRONG_SIDE_WICK")
    res.update(failed=failed, signal=(side if not failed else ""), n_broken=brk, pin=pin, eng=eng, full=full)
    return res


def simulate(day_rows: pd.DataFrame, side: str, cfg: dict, cas_start: str | None) -> dict | None:
    """Independent trade: NumPy arrays, explicit clock arithmetic. Executable = before 15:30 and (no auction regime or before 15:15)."""
    d = day_rows.sort_values("ts")
    mins = (d["ts"].dt.hour * 60 + d["ts"].dt.minute).to_numpy()
    op, hi, lo = d["open"].to_numpy(float), d["high"].to_numpy(float), d["low"].to_numpy(float)
    cut = 15 * 60 + 15 if cas_start else 15 * 60 + 30
    exe = mins < cut
    i0 = np.where(mins == 9 * 60 + 20)[0]
    if len(i0) == 0 or not exe[i0[0]]:
        return None
    i0 = int(i0[0])
    e = op[i0]
    s = 1 if side == "BUY" else -1
    sl, tp = e - s * cfg["stop_points"], e + s * cfg["target_points"]
    fh, fm = (int(x) for x in cfg["forced_exit_clock"].split(":"))
    fmin = fh * 60 + fm
    for i in range(i0, len(d)):
        if mins[i] >= fmin:
            break
        if not exe[i]:
            continue
        hit_sl = (lo[i] <= sl) if s == 1 else (hi[i] >= sl)
        hit_tp = (hi[i] >= tp) if s == 1 else (lo[i] <= tp)
        gap_sl = (op[i] <= sl) if s == 1 else (op[i] >= sl)
        gap_tp = (op[i] >= tp) if s == 1 else (op[i] <= tp)
        if i != i0 and gap_tp and not gap_sl:
            return {"entry": e, "exit": tp, "reason": "TARGET", "gross": s * (tp - e), "exit_min": int(mins[i])}
        if i != i0 and gap_sl:
            return {"entry": e, "exit": op[i], "reason": "STOP", "gross": s * (op[i] - e), "exit_min": int(mins[i])}
        if hit_sl:  # stop first when both are touched in the same minute
            return {"entry": e, "exit": sl, "reason": "STOP", "gross": s * (sl - e), "exit_min": int(mins[i])}
        if hit_tp:
            return {"entry": e, "exit": tp, "reason": "TARGET", "gross": s * (tp - e), "exit_min": int(mins[i])}
    j = np.where((mins == fmin) & exe)[0]
    if len(j) == 0 or fmin >= 15 * 60 + 15:
        return {"entry": e, "exit": None, "reason": "UNRESOLVED_EXIT", "gross": None, "exit_min": None}
    return {"entry": e, "exit": op[j[0]], "reason": "FORCED_EXIT", "gross": s * (op[j[0]] - e), "exit_min": fmin}
