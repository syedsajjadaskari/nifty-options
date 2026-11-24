"""Phase 6.5 continuation: how often does a WEAK red candle between the first and the second eligible PDS candle block the second-confirmation variant? (A convention interplay found in review: the PDS-SECOND engine
keeps the frozen 'a weak first red candle sends the setup to Method 3' branch, so a weak red candle after the registered first eligible candle ends the Method 1/2 path of that cycle.) This is a measurement on
the independent re-derivation; it does NOT change any engine, ledger or configuration. Output: pds_second_weak_red_interplay.json."""

from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase60_common as P60  # noqa: E402
import phase65b_audit as AU  # noqa: E402
from phase61_common import SCRATCH, window_data  # noqa: E402

from nifty_trading.strategies.definitions import gap_info  # noqa: E402
from nifty_trading.strategies.pds import pds_zone  # noqa: E402

R65 = AU.R65


def variant(rows, zlo, zhi, prox, m3, skip_weak_after_first):
    out, j0, weak, first = [], None, None, None
    near = lambda h, lo: h >= zlo - prox and lo <= zhi + prox  # noqa: E731
    for i, (st, o, h, lo, c) in enumerate(rows):
        if j0 is None:
            if not near(h, lo):
                continue
            j0 = i
        if first is not None and c > zhi + prox:
            j0, weak, first = None, None, None
            continue
        if weak is None and c < o and near(h, lo):
            body, up, lw = abs(c - o), h - o, c - lo
            meth = "Method 1" if (body > up and body > lw) else ("Method 2" if (up > body and up > lw and h >= zlo) else None)
            if meth is None:
                if not (skip_weak_after_first and first is not None):
                    weak = i
            elif first is None:
                first = (i, meth)
                continue
            else:
                out.append((st, meth))
                j0, weak, first = None, None, None
                continue
        if st in m3:
            j0, weak, first = None, None, None
    return out


def main() -> int:
    runs = pickle.loads((SCRATCH / "runs65b.pkl").read_bytes())
    res = {}
    for w in ("A", "B"):
        inp = P60.get_window(w, "5P")
        ctxs = window_data(w)[0]
        m3d: dict = {}
        for r in runs[w]["PDS_SECOND"]["pdr_pds"]:
            if r["strategy"] == "PDS" and r["method"] == "Method 3":
                m3d.setdefault(r["date"], set()).add(r["candle_start"])
        a = b = 0
        extra = []
        for d, ctx in sorted(ctxs.items()):
            if d not in inp.chain:
                continue
            g = gap_info(ctx, AU.SC.proposals)
            if g.direction != "DOWN":
                continue
            z = pds_zone(ctx.previous, AU.SC.proposals)
            bad = {"BELOW_ZONE": not ctx.open_price < z.low, "NOT_ABOVE_ZONE": ctx.open_price > z.high, "ANY": False}[AU.SC.proposals.pds_open_vs_zone]
            if bad:
                continue
            rows = [(f"{r.start:%H:%M}", r.open, r.high, r.low, r.close) for r in inp.chain[d].itertuples()]
            m3 = m3d.get(str(d), set())
            x = variant(rows, z.low, z.high, AU.SC.proposals.zone_proximity_points, m3, False)
            y = variant(rows, z.low, z.high, AU.SC.proposals.zone_proximity_points, m3, True)
            a += len(x)
            b += len(y)
            extra += [{"date": str(d), "signal_candle": st, "method": m} for st, m in y if (st, m) not in x]
        res[w] = {"second_signals_as_implemented": a, "second_signals_if_a_weak_red_between_were_ignored": b, "additional": len(extra), "examples": extra[:8]}
        print(w, res[w]["second_signals_as_implemented"], res[w]["second_signals_if_a_weak_red_between_were_ignored"], flush=True)
    res["note"] = "Measured on the independent re-derivation (it reproduces the engine's second-confirmation signals exactly in the as-implemented mode). Method 3 candle starts are taken from the engine (declared shared input). No ledger was re-simulated for the alternative reading."
    (R65 / "pds_second_weak_red_interplay.json").write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
