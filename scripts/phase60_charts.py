"""Phase 6.0 stage 7: SVG charts (every executed ORB V2 trade, previously missing dates, handwritten disputes, ORB-vs-IRF dates, rulebook examples with the original screenshots embedded)."""

from __future__ import annotations

import json
import pickle
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd  # noqa: E402
from phase60_common import CACHE, OUT, ROOT, get_window  # noqa: E402

from nifty_trading.research.orb_v2 import config as C  # noqa: E402
from nifty_trading.research.orb_v2 import data_access as DA  # noqa: E402
from nifty_trading.research.orb_v2 import journal as J  # noqa: E402
from nifty_trading.research.orb_v2 import levels as L  # noqa: E402
from nifty_trading.research.orb_v2.reporting import embed_png, svg_chart  # noqa: E402

CIDS = ("ORB-V2-A", "ORB-V2-B", "ORB-V2-C", "ORB-V2-D")
MEDIA = Path("/private/tmp/claude-501/-Users-syedaskari-algo-nifty-options/dc8ac295-6b01-4d30-b811-e11236c4316e/scratchpad/docx/word/media")
P55 = ROOT / "reports" / "phase5" / "phase55_combined_backtest"


def pct(x):
    return "n/a" if x in (None, "") or (isinstance(x, float) and pd.isna(x)) else f"{100 * float(x):.1f}%"


def cond_lines(s: dict) -> list[str]:
    if not s or not s.get("evaluable"):
        return [f"NOT EVALUATED: {s.get('not_evaluated_reason', '') if s else 'no session'}"]
    f = set((s.get("failed") or "").split(";")) - {""}
    mk = lambda ok, text: ("PASS  " if ok else "FAIL  ") + text  # noqa: E731
    out = [mk("GAP_TOO_LARGE" not in f, f"gap {s['gap_points']:+.1f} pts (limit +/-{s.get('gap_limit', 250):g}; open {s['open_1m']:.2f} vs prev close {s['prev_close']:.2f} [{s['prev_close_source']}])"),
           mk("EMA_EQUAL" not in f, f"EMA(200) {s['ema_now']:.2f}; 09:20 close {s['candle_close']:.2f}; direction {s['direction_by_ema'] or 'none'}; scenario {s.get('ema_scenario', '')}")]
    if s.get("direction_by_ema"):
        out += [mk("LEVEL_NOT_BROKEN" not in f, f"previous-day level break: {s['levels_broken_n']} of {s['levels_total']} broken ({s['qualifying_category'] or 'none'}); primary: {s['primary_level'] or 'none'}"),
                mk("COLOUR_MISMATCH" not in f, f"candle colour {s['colour']}"),
                mk("NO_PATTERN" not in f, f"pattern: {s['patterns_matched'] or 'none'} (pin {s['pin_bar']}, engulfing {s['engulfing']}, full-body {s['full_body']})"),
                mk("WRONG_SIDE_WICK" not in f, f"wrong-side wick {pct(s['wrong_side_wick_pct'])} (limit 20%)")]
    out.append(mk("ZERO_RANGE_CANDLE" not in f, f"candle O {s['candle_open']:.2f} H {s['candle_high']:.2f} L {s['candle_low']:.2f} C {s['candle_close']:.2f}; body {pct(s['body_pct'])}, upper wick {pct(s['upper_wick_pct'])}, lower wick {pct(s['lower_wick_pct'])}"))
    return out


def build(inp, d, cfg, s, t, title, header, panel, extra_markers=(), visual_zones=(), label_inner=False):
    sd, why = DA.session_data(inp, d)
    if sd is None:
        return None
    prev, today = sd.prev_candles, inp.chain[d]
    stop = (t["exit_time"] + pd.Timedelta(minutes=40)) if t and t.get("exit_time") is not None else pd.Timestamp(d) + pd.Timedelta(hours=11)
    cand = pd.concat([prev, today[today["start"] < stop]], ignore_index=True)
    trade = None
    if t:
        trade = {k: t.get(k) for k in ("direction", "entry_time", "entry_price", "stop", "target", "exit_time", "exit_price", "exit_reason", "gross_points")}
    spec = {"title": title, "header": header + ["Yellow column = 09:15-09:20 signal candle (usable only at 09:20). Purple bands = previous-day levels (dark = major, light = inner swing zones). Blue = EMA(200) of 5-minute closes."],
            "candles": cand, "open_start": today["start"].iloc[0], "levels": L.all_levels(prev, cfg), "trade": trade, "panel": panel, "extra_markers": list(extra_markers), "visual_zones": list(visual_zones), "label_inner": label_inner}
    return svg_chart(spec)


def main() -> int:  # noqa: C901
    results = pickle.loads((CACHE / "results.pkl").read_bytes())
    jr = J.read_journal()
    orb = {r["date"]: r for r in J.orb_rows(jr)}
    others = {}
    for r in jr:
        others.setdefault(r["date"], set()).add(r["strategy"])
    tr55 = pd.read_csv(P55 / "all_executed_trades.csv")
    tr55["date"] = pd.to_datetime(tr55["date"]).dt.date
    tr55A = tr55[tr55.config == "A"]
    hw = pd.read_csv(ROOT / "reports/phase5/phase58_codex_orb_forensic_audit/orb_13_handwritten_disputes.csv")
    hw = hw[hw.config == "A"]
    hw_dates = {pd.Timestamp(x).date(): c for x, c in zip(hw["date"], hw["comment"], strict=True)}
    miss50 = [r["date"] for r in json.loads("[]")] if False else []
    rows50 = pd.read_csv(OUT / "orb_50_previously_missing_dates.csv")
    miss50 = [pd.Timestamp(x).date() for x in rows50["date"]]
    cfgs = C.CONFIGS
    cntA = {"trades": 0, "missing": 0, "irf": 0, "ex": 0}
    for sub in ("charts_all_trades", "charts_missing_orb", "charts_orb_vs_irf", "charts_examples"):
        (OUT / sub).mkdir(parents=True, exist_ok=True)
    inps = {"A": get_window("A"), "B": get_window("B")}

    def journal_panel(d, tr_by_cfg):
        r = orb.get(d)
        if inps_key != "A":
            return ["JOURNAL: not applicable (the manual journal covers 2025-09..2026-08 only)."]
        if r is None:
            return [f"JOURNAL: no manual ORB row on this date (manual strategies: {', '.join(sorted(others.get(d, []))) or 'none'}) -> AUTOMATED_ONLY.",
                    "Journal evidence limit: date / time label / strategy / outcome only."]
        cls = {c: J.classify(r, tr_by_cfg.get(c)) for c in CIDS}
        return [f"JOURNAL row {r['sheet_row']}: ORB, time label {r['time']}, outcome {r['outcome']}.", "Match class: " + "; ".join(f"{c[-1]}={cls[c]}" for c in CIDS),
                "Evidence limit: no direction / price / level in the journal - a strict match is date + strategy + time label only, never an exact trade match."]

    # ---------------------------------------------------------------- all executed trades (unique date/direction across A-D, both windows)
    for key in ("A", "B"):
        inps_key = key
        inp = inps[key]
        seen = {}
        for c in CIDS:
            for t in results[(key, c)].trades:
                seen.setdefault((t["date"], t["direction"]), []).append(c)
        for (d, direction), cs in sorted(seen.items()):
            cA = cs[0]
            rr = {x["date"]: x for x in results[(key, cA)].trades}
            t = rr[d]
            s = next(x for x in results[(key, cA)].sessions if x["date"] == d)
            s = {**s, "gap_limit": cfgs[cA].max_gap_points}
            trb = {c: next((x for x in results[(key, c)].trades if x["date"] == d), None) for c in CIDS}
            panel = [f"Configs that traded this: {', '.join(c[-1] for c in cs)} (entry/stop/target/exit are identical; only the eligibility differs)."] + cond_lines(s) + [
                f"Execution: entry = open of the 09:20 1-min bar {t['entry_price']:.2f} (candle close {s['candle_close']:.2f}; rulebook 'close of the 9:15 candle' is TO CONFIRM). Stop {t['stop']:.2f} (-30), target {t['target']:.2f} (+60).",
                f"Exit: {t['exit_reason']} at {t['exit_price']:.2f} ({t['exit_time']:%H:%M}); gross {t['gross_points']:+.2f} index points = Rs {t['gross_points'] * 75:+,.0f} at the declared synthetic quantity 75. Synthetic index P&L, not option P&L."] + journal_panel(d, trb)
            frozen = tr55A[tr55A["date"] == d]
            if key == "A" and len(frozen):
                panel.append("Frozen Phase 3.6/5.5 config A executed on this date: " + "; ".join(f"{r.strategy} {r.direction} @{str(r.fill_timestamp)[11:16]}" for r in frozen.itertuples()))
            svg = build(inp, d, cfgs[cA], s, t, f"ORB V2 {direction} {d:%d %b %Y} - {t['trade_id']}", [f"Trade ID {t['trade_id']} | window {key} (5paisa) | {'/'.join(c[-1] for c in cs)} | {t['ema_scenario']} | level: {t['qualifying_category']}"], panel)
            if svg:
                (OUT / "charts_all_trades" / f"{t['trade_id']}.svg").write_text(svg)
                cntA["trades"] += 1
    # ---------------------------------------------------------------- previously missing dates + handwritten disputes (window A)
    inps_key = "A"
    inp = inps["A"]
    sA = {x["date"]: x for x in results[("A", "ORB-V2-A")].sessions}
    tA = {x["date"]: x for x in results[("A", "ORB-V2-A")].trades}
    trb_all = {c: {x["date"]: x for x in results[("A", c)].trades} for c in CIDS}
    for tag, dates in (("missing", miss50), ("dispute", sorted(hw_dates))):
        for d in dates:
            s = {**sA[d], "gap_limit": 250}
            t = tA.get(d)
            panel = ([("HANDWRITTEN AUTHOR NOTE: " + hw_dates[d])] if d in hw_dates else []) + (["Previously missing: the frozen Phase 3.6 ORB produced no signal on this journal ORB date."] if d in miss50 else []) + \
                [("V2-A SIGNAL: " + s["signal"]) if s.get("signal") else "V2-A: NO SIGNAL - rejection conditions below (no entry marker is invented)"] + cond_lines(s) + \
                ["Config B/C/D: " + " | ".join(f"{c[-1]}={sessions_sig(results, c, d)}" for c in CIDS[1:])] + journal_panel(d, {c: trb_all[c].get(d) for c in CIDS})
            fz = tr55A[tr55A["date"] == d]
            em = [(pd.Timestamp(r.fill_timestamp), float(r.entry_price), f"frozen {r.strategy} {r.direction} {r.entry_price:.1f}", "#e67e22") for r in fz.itertuples()]
            svg = build(inp, d, cfgs["ORB-V2-A"], s, t, f"{'Handwritten dispute' if tag == 'dispute' else 'Previously missing ORB date'} {d:%d %b %Y}", [f"ORB V2-A | {'SIGNAL ' + s['signal'] if s.get('signal') else 'no signal: ' + (s.get('failed') or s.get('not_evaluated_reason', ''))}"], panel, extra_markers=em)
            if svg:
                dest = OUT / ("charts_examples" if tag == "dispute" else "charts_missing_orb") / f"{'dispute_' if tag == 'dispute' else ''}{d}.svg"
                dest.write_text(svg)
                cntA["missing"] += 1
    # ---------------------------------------------------------------- dates where the frozen IRF executed on a manual ORB date
    irf_dates = sorted({r.date for r in tr55A[tr55A.strategy == "IRF"].itertuples()} & set(orb) & set(sA))
    for d in irf_dates:
        s = {**sA[d], "gap_limit": 250}
        t = tA.get(d)
        fz = tr55A[(tr55A["date"] == d)]
        em = [(pd.Timestamp(r.fill_timestamp), float(r.entry_price), f"frozen {r.strategy} {r.direction} {r.entry_price:.1f} @{str(r.fill_timestamp)[11:16]}", "#e67e22") for r in fz.itertuples()]
        panel = ["ORB V2-A vs the frozen IRF entry (orange marker, read-only comparison; the portfolio controller is untouched).", ("V2-A would enter at 09:20 (earlier than the IRF fill)." if t else "V2-A: no ORB signal this date.")] + cond_lines(s) + journal_panel(d, {c: trb_all[c].get(d) for c in CIDS})
        svg = build(inp, d, cfgs["ORB-V2-A"], s, t, f"ORB V2-A vs frozen IRF {d:%d %b %Y}", [f"V2-A {'SIGNAL ' + s['signal'] if s.get('signal') else 'no signal'} | frozen: " + ", ".join(f"{r.strategy} {r.direction}@{str(r.fill_timestamp)[11:16]}" for r in fz.itertuples())], panel, extra_markers=em)
        if svg:
            (OUT / "charts_orb_vs_irf" / f"{d}.svg").write_text(svg)
            cntA["irf"] += 1
    # ---------------------------------------------------------------- rulebook examples (both vendors) with screenshots
    (OUT / "charts_examples" / "doc_images").mkdir(exist_ok=True)
    zones = {"2025-09-16": ([(25092.2, 25095.8, "lower purple zone (pixel estimate +/-1.5)"), (25111.8, 25114.8, "upper purple zone (pixel estimate +/-1.5)")], MEDIA / "image1.png", (25107.45, 25076.60, 25168.00)),
             "2025-09-17": ([], MEDIA / "image3.png", (25296.80, 25265.25, 25351.25)),
             "2025-09-24": ([(25177.4, 25182.6, "top purple zone"), (25135.7, 25140.4, "middle purple zone"), (25084.0, 25087.0, "lower purple zone")], MEDIA / "image4.png", (25090.50, 25120.50, 25031.15))}
    for ds, (vz, img, tags) in zones.items():
        shutil.copy(img, OUT / "charts_examples" / "doc_images" / f"{ds}_{img.name}")
        d = pd.Timestamp(ds).date()
        for vendor in ("5P", "TV"):
            inpv = get_window("A", vendor)
            sv, why = DA.session_data(inpv, d)
            from nifty_trading.research.orb_v2 import execution as EX
            from nifty_trading.research.orb_v2 import signal_engine as SE
            dec = SE.evaluate_session(sv, cfgs["ORB-V2-A"])
            s = {"evaluable": True, "signal": dec.signal, "failed": ";".join(dec.failed), "gap_limit": 250, **dec.detail}
            t = None
            if dec.signal:
                ex = EX.simulate(sv, dec.signal, cfgs["ORB-V2-A"], inpv.cal)
                t = {**ex, "direction": dec.signal} if ex.get("traded") else None
            em = [(pd.Timestamp(d) + pd.Timedelta(hours=9, minutes=20), tags[0], f"author chart entry ~{tags[0]:.2f}", "#e67e22"), (pd.Timestamp(d) + pd.Timedelta(hours=9, minutes=20), tags[1], f"author SL ~{tags[1]:.2f}", "#e67e22"),
                  (pd.Timestamp(d) + pd.Timedelta(hours=9, minutes=20), tags[2], f"author TP ~{tags[2]:.2f}", "#e67e22")]
            panel = [f"Data feed: {'5paisa (primary)' if vendor == '5P' else 'secondary vendor (the feed the rulebook screenshots match)'}", "V2-A decision: " + (dec.signal or "NO SIGNAL") + (" | failed: " + ", ".join(dec.failed) if dec.failed else "")] + cond_lines(s) + \
                ["Orange dashed boxes = author's purple zones read from the screenshot by pixel position (visual evidence only, +/-1.5 points). Orange triangles = the author's chart entry / SL / TP tags (approximate)."]
            svg = build(inpv, d, cfgs["ORB-V2-A"], s, t, f"Rulebook example {ds} [{vendor}]", [f"{'SIGNAL ' + dec.signal if dec.signal else 'NO SIGNAL'} under the written-rule reference (ORB-V2-A)"], panel, extra_markers=em, visual_zones=vz, label_inner=True)
            png = embed_png(img)
            from PIL import Image
            w, h = Image.open(img).size
            sh = int(1500 * h / w)
            comp = (f'<svg xmlns="http://www.w3.org/2000/svg" width="1500" height="{sh + 830}"><rect width="1500" height="{sh + 830}" fill="#fff"/>'
                    f'<text x="10" y="18" font-family="Helvetica" font-size="14" font-weight="bold">Original rulebook screenshot (native image, scaled) - {ds}</text>'
                    f'<image x="0" y="24" width="1500" height="{sh}" href="data:image/png;base64,{png}"/>'
                    f'<svg x="0" y="{sh + 30}" width="1500" height="800">{svg}</svg></svg>')
            (OUT / "charts_examples" / f"example_{ds}_{vendor}.svg").write_text(comp)
            cntA["ex"] += 1
    print(cntA)
    return 0


def sessions_sig(results, c, d):
    s = next((x for x in results[("A", c)].sessions if x["date"] == d), None)
    return (s.get("signal") or "none") if s and s["evaluable"] else "n/a"


if __name__ == "__main__":
    sys.exit(main())
