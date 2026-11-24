"""Phase 6.5 continuation, stage 3: charts of materially changed trades (PDR / PDS variants) and of trade-set REPLACEMENT (candle-strength variants: a rejected weak-candle trade lets ANOTHER strategy enter). Primary window only.
No execution is fabricated: every marker is an entry from a configuration's own ledger; levels and exits are quoted from that ledger."""

from __future__ import annotations

import pickle
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd  # noqa: E402
import phase62_charts as CH  # noqa: E402
from phase61_common import SCRATCH, window_data  # noqa: E402

R65 = Path(__file__).resolve().parents[1] / "reports" / "phase6" / "phase65_author_feedback"
CFG_COL = {"BASE": "#e67e22", "S60": "#2f80ed", "S70": "#8e44ad", "SD": "#16a085", "PDR_B1": "#2f80ed", "PDR_B2": "#8e44ad", "PDR_C": "#c0392b", "PDR_D": "#6d4c41", "PDS_FROZEN": "#16a085", "PDS_SECOND": "#c0392b"}


def trade_line(r):
    return (f"{r['strategy']}/{r['method']} {r['direction']} entry {r['entry_time']} @ {r['entry_price']} | SL {r['stop_level']} T1 {r['t1_level']} T2 {r['t2_level']} post-T1 {r['post_t1_stop_level']} | leg1 {r['leg1_exit_time'] or '-'} @ {r['leg1_exit_price']}, "
            f"leg2 {r['leg2_exit_time'] or '-'} @ {r['leg2_exit_price']} -> {r['outcome']} ({float(r['gross_points_weighted']):+.1f} pts, Rs {float(r['gross_pnl_rs']):+,.0f})")


def main() -> int:
    runs = pickle.loads((SCRATCH / "runs65b.pkl").read_bytes())["A"]
    ctxs = window_data("A")[0]
    attrib = pd.read_csv(R65 / "trade_set_attribution.csv", dtype=str, keep_default_na=False)
    attrib = attrib[attrib.window == "A"]
    jr = pd.read_csv(R65 / "manual_journal_reconciliation.csv", dtype=str, keep_default_na=False)
    for sub in ("charts_changed_trades", "charts_trade_set_replacement"):
        (R65 / sub).mkdir(exist_ok=True)

    def stage(cfg, date, strat):
        g = jr[(jr.config == cfg) & (jr.date == date) & ((jr.manual_strategy == strat) | (jr.auto_strategy == strat))]
        return ", ".join(sorted(set(g.stage))) or "no journal row for that strategy"

    def day_chart(cfg, d, sub, head):
        ctx = ctxs[pd.Timestamp(d).date()]
        tz = ctx.candles["bar_start"].iloc[0].tz
        c = ctx.candles.rename(columns={"bar_start": "start", "bar_end": "end", "ema200_5m": "ema"})[["start", "end", "open", "high", "low", "close", "ema"]].reset_index(drop=True)
        mk, panel = [], [head]
        for k in ("BASE", cfg):
            rows = [r for r in runs[k]["ledger"] if r["date"] == d]
            for r in sorted(rows, key=lambda x: x["entry_time"]):
                mk.append((pd.Timestamp(f"{d} {r['entry_time']}").tz_localize(tz), float(r["entry_price"]), f"{k}: {r['strategy']} {r['direction']} {r['entry_time']} -> {r['outcome']}", CFG_COL[k]))
                panel.append(f"[{k}] " + trade_line(r) + f" | journal ({k}): {stage(k, d, r['strategy'])}")
            if not rows:
                panel.append(f"[{k}] no trade")
        for _, a in attrib[(attrib.config == cfg) & (attrib.date == d)].iterrows():
            panel.append(f"{a.kind} {a.strategy} {a.entry_time}: {a.effect}")
        man = jr[(jr.date == d) & (jr.stage == "MANUAL_ONLY") & (jr.config == cfg)]
        panel.append("Manual journal rows that day: " + ("; ".join(f"{r.manual_strategy}@{r.manual_time_label}" for r in jr[(jr.config == cfg) & (jr.date == d) & jr.manual_strategy.ne("")].itertuples()) or "none") + (" (some unmatched)" if len(man) else ""))
        hl = [(float(ctx.previous.high), "prev-day high", "#777"), (float(ctx.previous.low), "prev-day low", "#777")] if ctx.previous else []
        (R65 / sub / f"{cfg}_{d}.svg").write_text(CH.chart(f"{d} | BASE (orange) vs {cfg}", ["Markers are entries from each configuration's own ledger; nothing is fabricated. Variants are research candidates, not selected."], c, panel, markers=mk, hlines=hl))

    n1 = n2 = 0
    for cfg in ("PDR_B1", "PDR_B2", "PDR_C", "PDR_D", "PDS_FROZEN", "PDS_SECOND"):
        dates = sorted(set(attrib[attrib.config == cfg].date))
        for d in dates:
            day_chart(cfg, d, "charts_changed_trades", f"Changed trade set ({cfg}): direct = the rule changed the signal; portfolio = the controller selected differently")
            n1 += 1
    byd = defaultdict(dict)
    for _, a in attrib[attrib.config.isin(["S60", "S70", "SD"])].iterrows():
        byd[(a.config, a.date)].setdefault(a.kind, []).append(a)
    for (cfg, d), kinds in sorted(byd.items()):
        rem = kinds.get("REMOVED_BASELINE_TRADE", [])
        add = kinds.get("ADDED_TRADE", [])
        if any(r.effect.startswith("DIRECT") for r in rem) and any(x.effect.startswith("PORTFOLIO") and x.strategy not in {r.strategy for r in rem} for x in add):
            day_chart(cfg, d, "charts_trade_set_replacement", f"REPLACEMENT ({cfg}): a weak-candle signal was rejected (direct effect) and ANOTHER strategy entered later (portfolio effect)")
            n2 += 1
    print({"changed_trade_charts": n1, "replacement_charts": n2})
    return 0


if __name__ == "__main__":
    sys.exit(main())
