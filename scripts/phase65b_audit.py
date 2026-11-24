"""Phase 6.5 continuation, independent audit. (1) every PDR variant signal (B1, B2, C, D) re-derived from RAW five-minute candles (Phase 6.0 chain: pandas resample) with an independent selection loop; (2) PDS second-confirmation
signals likewise; (3) P&L / exits of EVERY ledger of every configuration reconstructed from raw one-minute bars (separate NumPy simulator of Phase 6.2); (4) journal strict / tolerant counts recounted with a multiset method; (5) trade-set
reconciliation (baseline + added - removed = variant); (6) look-ahead: prefix truncation of sessions. DECLARED SHARED INPUTS: the previous-day zone construction (`build_zone` / `pds_zone`), the gap qualification (`gap_info`) and the
zone-height conventions, which are the repository's verified Phase 3-5 infrastructure; everything after the zone (retest, eligibility, selection, sequencing) is re-implemented here."""

from __future__ import annotations

import json
import pickle
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase60_common as P60  # noqa: E402
import phase62_audit as EA  # noqa: E402
from phase61_common import JOURNAL, SCRATCH, window_data  # noqa: E402

from nifty_trading.research import phase3 as P  # noqa: E402
from nifty_trading.research import phase56 as M  # noqa: E402
from nifty_trading.strategies.definitions import gap_info, pds_zone, prev_candles, to_candles  # noqa: E402
from nifty_trading.strategies.first_eligible_phase53 import (  # noqa: E402
    PDRFirstEligibleStrategy,
    PDSFirstEligibleStrategy,
)
from nifty_trading.strategies.pdr_body import build_zone  # noqa: E402
from nifty_trading.strategies.pdr_variants import PDRVariantStrategy  # noqa: E402
from nifty_trading.strategies.pds_variants import PDSSecondConfirmationStrategy  # noqa: E402

R65 = Path(__file__).resolve().parents[1] / "reports" / "phase6" / "phase65_author_feedback"
SC = P.combined_scenario("BODY_BASED_PHASE36")


def pdr_independent(mode, rows, floor, ceiling):
    """rows: list of (start 'HH:MM', o, h, l, c) 5-minute candles of one session. Returns [(retest, signal)] for the variant."""
    out, j, first = [], None, None
    may = mode in ("B2", "C")
    for i, (st, o, h, lo, c) in enumerate(rows):
        if j is None:
            if lo <= ceiling and h >= floor:
                j = i
                if not may:
                    continue
            else:
                continue
        body, up, lw = abs(c - o), h - max(o, c), min(o, c) - lo
        green = c > o
        rej = lw > body and lw > up and lo <= ceiling
        if mode in ("B1", "B2"):
            ok = green
        elif mode == "C":
            ok = green and c > ceiling
        else:
            ok = (green or rej) and c > ceiling
        if not ok or not (i > j or may):
            continue
        if mode == "D" and first is None:
            first = i
            continue
        out.append((rows[j][0], st))
        j, first = None, None
    return out


def pds_independent(rows, zlo, zhi, prox, m3_candles=frozenset()):
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
                weak = i
            elif first is None:
                first = (i, meth)
                continue
            else:
                out.append((st, meth, rows[first[0]][0]))
                j0, weak, first = None, None, None
                continue
        if st in m3_candles:                           # DECLARED SHARED INPUT: Method 3 (unchanged) triggered on this candle, which ends the cycle; its own trigger is not re-derived here
            j0, weak, first = None, None, None
    return out


def main() -> int:  # noqa: C901
    runs = pickle.loads((SCRATCH / "runs65b.pkl").read_bytes())
    res: dict = {}
    for w in ("A", "B"):
        inp = P60.get_window(w, "5P")
        ctxs = window_data(w)[0]
        mism = {m: 0 for m in ("B1", "B2", "C", "D", "PDS_SECOND")}
        compared = {m: 0 for m in mism}
        sig_eng = {}
        for m in ("B1", "B2", "C", "D"):
            sig_eng[m] = {(r["date"], r["interaction_start"], r["candle_start"]) for r in runs[w][f"PDR_{m}"]["pdr_pds"] if r["strategy"] == "PDR"}
        sec_eng = {(r["date"], r["candle_start"], r["method"], r["first_eligible_start"]) for r in runs[w]["PDS_SECOND"]["pdr_pds"] if r["strategy"] == "PDS" and r["method"] in ("Method 1", "Method 2")}
        ind = {m: set() for m in mism}
        m3_by_date: dict = {}
        for r in runs[w]["PDS_SECOND"]["pdr_pds"]:
            if r["strategy"] == "PDS" and r["method"] == "Method 3":
                m3_by_date.setdefault(r["date"], set()).add(r["candle_start"])
        pdr_base = PDRFirstEligibleStrategy(proposals=SC.proposals, trade=SC.trade, revision=SC.pdr_revision)
        for d, ctx in sorted(ctxs.items()):
            if d not in inp.chain:
                continue
            c5 = inp.chain[d]
            rows = [(f"{r.start:%H:%M}", r.open, r.high, r.low, r.close) for r in c5.itertuples()]
            cs = to_candles(ctx.candles)
            g = gap_info(ctx, SC.proposals)
            if g.direction == "UP":
                zone = build_zone(to_candles(prev_candles(ctx.previous, SC.proposals)), pdr_base.rev)
                if ctx.open_price > zone.ceiling and not (zone.zero_height and pdr_base.rev.zero_height_policy == "UNRESOLVED_NO_SETUP"):
                    for m in ("B1", "B2", "C", "D"):
                        ind[m] |= {(str(d), a, b) for a, b in pdr_independent(m, rows, zone.floor, zone.ceiling)}
            if g.direction == "DOWN":
                z = pds_zone(ctx.previous, SC.proposals)
                bad = {"BELOW_ZONE": not ctx.open_price < z.low, "NOT_ABOVE_ZONE": ctx.open_price > z.high, "ANY": False}[SC.proposals.pds_open_vs_zone]
                if not bad:
                    ind["PDS_SECOND"] |= {(str(d), a, b, c) for a, b, c in pds_independent(rows, z.low, z.high, SC.proposals.zone_proximity_points, m3_by_date.get(str(d), frozenset()))}
            _ = cs
        for m in ("B1", "B2", "C", "D"):
            compared[m] = len(sig_eng[m])
            mism[m] = len(ind[m] ^ sig_eng[m])
        compared["PDS_SECOND"] = len(sec_eng)
        mism["PDS_SECOND"] = len(ind["PDS_SECOND"] ^ sec_eng)
        res[f"signals_{w}"] = {"engine_signals": compared, "symmetric_difference": mism, "independent_signals": {k: len(v) for k, v in ind.items()}}
        print(w, res[f"signals_{w}"], flush=True)
    # ---------------------------------------------------------------- execution reconstruction for every ledger
    exe, bad = {}, []
    for w in ("A", "B"):
        inp = P60.get_window(w, "5P")
        for k, v in runs[w].items():
            ok = 0
            for r in v["ledger"]:
                d = __import__("pandas").Timestamp(r["date"]).date()
                hm = lambda t: int(t[:2]) * 60 + int(t[3:])  # noqa: E731
                out = EA.sim(inp.day_frames[d], r["direction"], r["strategy"], hm(r["entry_time"]), int(r["qty_leg1"]), int(r["qty_leg2"]), inp.infos[d].cas_regime)
                good = out is not None and out["outcome"] == r["outcome"] and abs(out["entry"] - float(r["entry_price"])) < 1e-9 and (out["pnl"] is None or abs(out["pnl"] - float(r["gross_pnl_rs"])) < 1e-6) and r["entry_time"] == r["signal_time"] and r["entry_time"] <= "13:00"
                ok += bool(good)
                if not good:
                    bad.append({"window": w, "config": k, "trade_id": r["trade_id"]})
            exe[f"{w}|{k}"] = {"trades": len(v["ledger"]), "verified": ok}
    res["execution"] = exe
    res["execution_problems"] = bad[:20]
    # ---------------------------------------------------------------- journal recount (multiset) + trade-set reconciliation
    jrows, _ = M.load_journal(JOURNAL)
    man = Counter((r.date, r.strategy, r.time_label) for r in jrows if not r.weekend)
    import pandas as pd
    summ = pd.read_csv(R65 / "strict_match_comparison.csv")
    jr = {}
    for k, v in runs["A"].items():
        def start(t):  # noqa: E306,B023
            m = int(t[:2]) * 60 + int(t[3:]) - 5
            return f"{m // 60:02d}:{m % 60:02d}"
        auto = Counter((r["date"], r["strategy"], start(r["signal_time"])) for r in v["ledger"])
        strict = sum(min(n, auto.get(kk, 0)) for kk, n in man.items())
        jr[k] = {"independent_strict": strict, "reported_strict": int(summ[summ.config == k].strict.iloc[0])}
    res["journal_recount"] = jr
    att = pd.read_csv(R65 / "trade_set_attribution.csv", dtype=str, keep_default_na=False)
    rec = {}
    for w in ("A", "B"):
        for k in runs[w]:
            if k == "BASE":
                continue
            a = att[(att.window == w) & (att.config == k)]
            nb, nv = len(runs[w]["BASE"]["ledger"]), len(runs[w][k]["ledger"])
            rec[f"{w}|{k}"] = {"baseline": nb, "removed": int((a.kind == "REMOVED_BASELINE_TRADE").sum()), "added": int((a.kind == "ADDED_TRADE").sum()), "variant": nv, "reconciles": nb - int((a.kind == "REMOVED_BASELINE_TRADE").sum()) + int((a.kind == "ADDED_TRADE").sum()) == nv}
    res["trade_set_reconciliation"] = rec
    # ---------------------------------------------------------------- look-ahead: prefix truncation
    ctxs = window_data("A")[0]
    la = {"sessions": 0, "violations": 0}
    engs = {m: PDRVariantStrategy(m, proposals=SC.proposals, trade=SC.trade, revision=SC.pdr_revision) for m in ("B1", "B2", "C", "D")}
    engs["PDS_SECOND"] = PDSSecondConfirmationStrategy(proposals=SC.proposals, trade=SC.trade)
    engs["PDS_FIRST"] = PDSFirstEligibleStrategy(proposals=SC.proposals, trade=SC.trade)
    for d in sorted(ctxs)[::4]:
        ctx = ctxs[d]
        n = len(ctx.candles)
        for e in engs.values():
            full = [(r.signal_timestamp, r.method) for r in e.evaluate_session(ctx) if r.signal_status == "CONFIRMED"]
            for cut in (15, 30, 45, 60):
                if cut >= n:
                    continue
                pre = ctx.prefix(cut)
                got = sorted((r.signal_timestamp, r.method) for r in e.evaluate_session(pre) if r.signal_status == "CONFIRMED")
                want = sorted(x for x in full if x[0] <= ctx.candles["bar_end"].iloc[cut - 1])
                la["sessions"] += 1
                la["violations"] += got != want
    res["look_ahead_prefix_test"] = la
    (R65 / "continuation_independent_audit.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: v for k, v in res.items() if k not in ("execution",)}, indent=1, default=str)[:2500])
    return 0


if __name__ == "__main__":
    sys.exit(main())
