"""Phase 6.2 independent execution audit: re-derives the entry, the levels, both exit legs and the gross rupee P&L of EVERY executed trade (all configurations, both windows) from the RAW one-minute bars with a separate
NumPy simulator that does not call exit_policy / trading_day. Declared shared inputs: the raw bars, the ledger's signal time / direction / strategy / quantities, and the documented conventions (stop before target in one bar,
a stop gapped through fills at the worse of level and open, a target fills at its level, post-T1 stop = entry -/+ 6, forced exit at the 15:14 open, nothing fills at/after 15:15 or on closing-auction bars)."""

from __future__ import annotations

import json
import pickle
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import phase60_common as P60  # noqa: E402
from phase61_common import R62, SCRATCH, write_csv  # noqa: E402

STOP = {"IRF": 35.0, "ORB": 30.0, "PDR": 35.0, "PDS": 35.0, "RF": 35.0}
T2 = {"IRF": 60.0, "ORB": 60.0, "PDR": 70.0, "PDS": 70.0, "RF": 60.0}
T1 = 27.0
POST = 6.0
OUTCOME = {"TARGET": "TARGET", "T1_STOP": "T1_THEN_BUFFER_STOP", "FULL_STOP": "INITIAL_FULL_STOP", "FORCED": "FORCED_EXIT"}


def sim(day: pd.DataFrame, direction: str, strat: str, entry_min: int, q1: int, q2: int, cas: bool):
    d = day.sort_values("ts")
    mins = (d["ts"].dt.hour * 60 + d["ts"].dt.minute).to_numpy()
    o, h, lo = d["open"].to_numpy(float), d["high"].to_numpy(float), d["low"].to_numpy(float)
    exe = mins < (15 * 60 + 15 if cas else 15 * 60 + 30)
    i0 = np.where(mins == entry_min)[0]
    if len(i0) == 0:
        return None
    i0 = int(i0[0])
    e = o[i0]
    s = 1 if direction == "LONG" else -1
    sl, t1, t2, st2 = e - s * STOP[strat], e + s * T1, e + s * T2[strat], e - s * POST
    adverse = (lambda i, lv: (lo[i] <= lv) if s == 1 else (h[i] >= lv))  # noqa: E731
    favour = (lambda i, lv: (h[i] >= lv) if s == 1 else (lo[i] <= lv))  # noqa: E731
    fill = (lambda i, lv: min(lv, o[i]) if s == 1 else max(lv, o[i]))  # noqa: E731
    pts = lambda x: s * (x - e)  # noqa: E731
    t1_done, l1, l1_min, amb = False, None, None, 0
    for i in range(i0, len(d)):
        if mins[i] >= 15 * 60 + 14:
            break
        if not exe[i]:
            continue
        if not t1_done:
            sh, th = adverse(i, sl), favour(i, t1)
            amb += bool(sh and th)
            if sh:
                px = fill(i, sl)
                return {"entry": e, "outcome": "INITIAL_FULL_STOP", "l1": px, "l1_min": int(mins[i]), "l2": px, "l2_min": int(mins[i]), "pnl": pts(px) * (q1 + q2), "amb": amb}
            if not th:
                continue
            t1_done, l1, l1_min = True, t1, int(mins[i])
            if adverse(i, st2):
                amb += 1
                return {"entry": e, "outcome": "T1_THEN_BUFFER_STOP", "l1": l1, "l1_min": l1_min, "l2": st2, "l2_min": int(mins[i]), "pnl": pts(l1) * q1 + pts(st2) * q2, "amb": amb}
            if favour(i, t2):
                return {"entry": e, "outcome": "TARGET", "l1": l1, "l1_min": l1_min, "l2": t2, "l2_min": int(mins[i]), "pnl": pts(l1) * q1 + pts(t2) * q2, "amb": amb}
            continue
        bh, t2h = adverse(i, st2), favour(i, t2)
        amb += bool(bh and t2h)
        if bh:
            px = fill(i, st2)
            return {"entry": e, "outcome": "T1_THEN_BUFFER_STOP", "l1": l1, "l1_min": l1_min, "l2": px, "l2_min": int(mins[i]), "pnl": pts(l1) * q1 + pts(px) * q2, "amb": amb}
        if t2h:
            return {"entry": e, "outcome": "TARGET", "l1": l1, "l1_min": l1_min, "l2": t2, "l2_min": int(mins[i]), "pnl": pts(l1) * q1 + pts(t2) * q2, "amb": amb}
    j = np.where((mins == 15 * 60 + 14) & exe)[0]
    if len(j) == 0:
        return {"entry": e, "outcome": "INCOMPLETE_EOD", "l1": l1, "l1_min": l1_min, "l2": None, "l2_min": None, "pnl": None, "amb": amb}
    px = o[j[0]]
    pnl = (pts(l1) * q1 + pts(px) * q2) if t1_done else pts(px) * (q1 + q2)
    return {"entry": e, "outcome": "FORCED_EXIT", "l1": l1 if t1_done else px, "l1_min": l1_min if t1_done else 15 * 60 + 14, "l2": px, "l2_min": 15 * 60 + 14, "pnl": pnl, "amb": amb}


def fnum(x):
    return None if x in ("", None) else float(x)


def hm(x: str) -> int:
    return int(x[:2]) * 60 + int(x[3:5])


def main() -> int:
    res = pickle.loads((SCRATCH / "results62.pkl").read_bytes())
    summary, bad_rows = {}, []
    for win in ("A", "B"):
        inp = P60.get_window(win, "5P")
        for cfg, rows in res[win]["ledgers"].items():
            n = ok = 0
            checks = Counter()
            for r in rows:
                d = pd.Timestamp(r["date"]).date()
                day = inp.day_frames[d]
                sg = hm(r["signal_time"])
                out = sim(day, r["direction"], r["strategy"], hm(r["entry_time"]), int(r["qty_leg1"]), int(r["qty_leg2"]), inp.infos[d].cas_regime)
                n += 1
                if out is None:
                    bad_rows.append({"window": win, "config": cfg, "trade_id": r["trade_id"], "problem": "no raw bar at the entry minute"})
                    continue
                prob = []
                if hm(r["entry_time"]) != sg:
                    prob.append("fill is not the bar starting at the signal candle's end")
                if r["entry_time"] > "13:00":
                    prob.append("entry after the 13:00 cutoff")
                if abs(out["entry"] - float(r["entry_price"])) > 1e-9:
                    prob.append(f"entry price {r['entry_price']} != raw open {out['entry']}")
                s = 1 if r["direction"] == "LONG" else -1
                lv = {"stop_level": float(r["entry_price"]) - s * STOP[r["strategy"]], "t1_level": float(r["entry_price"]) + s * T1, "t2_level": float(r["entry_price"]) + s * T2[r["strategy"]], "post_t1_stop_level": float(r["entry_price"]) - s * POST}
                for k, v in lv.items():
                    g = fnum(r.get(k))
                    if g is not None and abs(g - v) > 1e-9:
                        prob.append(f"{k} {g} != {v}")
                if int(r["qty_total"]) != 390 or int(r["qty_leg1"]) != 195 or int(r["qty_leg2"]) != 195:
                    prob.append("position split is not 195 + 195")
                if out["outcome"] != r["outcome"]:
                    prob.append(f"outcome {r['outcome']} != independent {out['outcome']}")
                else:
                    for lab, px, mn in (("leg1", r["leg1_exit_price"], r["leg1_exit_time"]), ("leg2", r["leg2_exit_price"], r["leg2_exit_time"])):
                        want, wmin = out["l1" if lab == "leg1" else "l2"], out["l1_min" if lab == "leg1" else "l2_min"]
                        if want is None:
                            continue
                        if abs(float(px) - want) > 1e-9 or hm(mn) != wmin:
                            prob.append(f"{lab} exit {mn} @ {px} != independent {wmin // 60:02d}:{wmin % 60:02d} @ {want}")
                    if out["pnl"] is not None and abs(float(r["gross_pnl_rs"]) - out["pnl"]) > 1e-6:
                        prob.append(f"gross P&L {r['gross_pnl_rs']} != independent {out['pnl']}")
                if bool(out["amb"]) != (int(r.get("ambiguities") or 0) > 0):
                    checks["ambiguity_flag_differs"] += 1
                    prob.append("same-minute ambiguity flag differs")
                if prob:
                    bad_rows.append({"window": win, "config": cfg, "trade_id": r["trade_id"], "problem": "; ".join(prob)})
                else:
                    ok += 1
            summary[f"{win}|{cfg}"] = {"trades": n, "fully_verified": ok, "problems": n - ok}
    write_csv(R62 / "execution_audit_problems.csv", bad_rows, ["window", "config", "trade_id", "problem"])
    (R62 / "execution_audit_summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))
    print(bad_rows[:5])
    return 0


if __name__ == "__main__":
    sys.exit(main())
