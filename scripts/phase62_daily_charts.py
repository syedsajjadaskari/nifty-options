"""Phase 6.2 / 6.3 visual layer: a daily report for EVERY evaluable session of configuration C (primary window), a full chart for EVERY executed C trade, journal-focused daily files and the focused chart sets. Charts use actual
five-minute candles; no trade marker is ever drawn for a day on which a configuration did not trade."""

from __future__ import annotations

import pickle
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd  # noqa: E402
import phase62_charts as CH  # noqa: E402
from phase61_common import R61, R62, R63, SCRATCH, window_data, write_csv  # noqa: E402

CFG = ("A", "B", "C")


def candles_of(ctx, until: str | None = None) -> pd.DataFrame:
    c = ctx.candles.rename(columns={"bar_start": "start", "bar_end": "end", "ema200_5m": "ema"})[["start", "end", "open", "high", "low", "close", "ema"]]
    if until:
        c = c[c["start"].dt.strftime("%H:%M") <= until]
    return c.reset_index(drop=True)


def ts(d: str, hm: str, tz) -> pd.Timestamp:
    return pd.Timestamp(f"{d} {hm}").tz_localize(tz)


def reasons(r) -> tuple[str, str]:
    o = r["outcome"]
    return {"INITIAL_FULL_STOP": ("STOP", "STOP"), "T1_THEN_BUFFER_STOP": ("T1", "POST-T1 STOP"), "TARGET": ("T1", "T2"), "FORCED_EXIT": ("T1" if r.get("post_t1_stop_level") not in ("", None) else "FORCED", "FORCED 15:14 OPEN")}.get(o, (o, o))


def main() -> int:  # noqa: C901
    res = pickle.loads((SCRATCH / "results62.pkl").read_bytes())["A"]
    r63 = pickle.loads((SCRATCH / "results63.pkl").read_bytes())
    ctxs, infos, bars, cal, label = window_data("A")
    rows = r63["rows"]
    jr_by_id = {r.row_id: r for r in rows}
    jr_by_date = defaultdict(list)
    for r in rows:
        jr_by_date[r.date].append(r)
    stage_of = {k: {} for k in CFG}
    for k in CFG:
        for st, key in (("STRICT", "strict"), ("TIME_TOLERANT", "tolerant"), ("DATE_STRATEGY_ONLY", "date_only")):
            for jid, tid in r63["detail_stage"][k][key]:
                stage_of[k][tid] = (st, jr_by_id[jid])
    led = {k: res["ledgers"][k] for k in CFG}
    sigs = {k: defaultdict(list) for k in CFG}
    for k in CFG:
        for s in res["signals"][k]:
            sigs[k][s["date"]].append(s)
    att = pd.read_csv(R61 / "irf_reference_candle_audit.csv", dtype=str, keep_default_na=False)
    att = att[att.window == "A"]
    orb_rej = {r["date"]: r for r in res["orb_rejections"]}
    levels = res["levels"]["C"]
    orb_rows = {r["date"]: r for r in r63["orb_rows"]}
    tr_by_date = {k: defaultdict(list) for k in CFG}
    for k in CFG:
        for r in led[k]:
            tr_by_date[k][r["date"]].append(r)
    for sub in ("charts", "daily"):
        (R62 / sub).mkdir(parents=True, exist_ok=True)
    (R63 / "daily").mkdir(exist_ok=True)
    for sub in ("manual_only", "orb_vs_irf", "handwritten", "changed_days", "trade_links"):
        (R63 / "charts" / sub).mkdir(parents=True, exist_ok=True)
    chart_index = []
    # ------------------------------------------------------------------ one full chart per executed C trade
    n_tr = 0
    for r in led["C"]:
        d = pd.Timestamp(r["date"]).date()
        ctx = ctxs[d]
        tz = ctx.candles["bar_start"].iloc[0].tz
        end = r["leg2_exit_time"] or "15:25"
        until = f"{min(int(end[:2]) * 60 + int(end[3:5]) + 45, 15 * 60 + 25) // 60:02d}:{min(int(end[:2]) * 60 + int(end[3:5]) + 45, 15 * 60 + 25) % 60:02d}"
        c = candles_of(ctx, until)
        key = (r["date"], r["signal_time"], r["strategy"], r["method"], r["direction"])
        lv, trace, rules = levels.get(key, ({}, [], []))
        l1r, l2r = reasons(r)
        trade = {"direction": r["direction"], "entry_time": ts(r["date"], r["entry_time"], tz), "entry_price": float(r["entry_price"]), "stop": float(r["stop_level"]), "t1": float(r["t1_level"]), "t2": float(r["t2_level"]),
                 "post_t1_stop": float(r["post_t1_stop_level"]) if r.get("post_t1_stop_level") not in ("", None) and r["outcome"] in ("T1_THEN_BUFFER_STOP", "TARGET", "FORCED_EXIT") else None,
                 "leg1_time": ts(r["date"], r["leg1_exit_time"], tz) if r["leg1_exit_time"] else None, "leg1_price": float(r["leg1_exit_price"]) if r["leg1_exit_price"] not in ("", None) else None, "leg1_reason": l1r,
                 "leg2_time": ts(r["date"], r["leg2_exit_time"], tz) if r["leg2_exit_time"] else None, "leg2_price": float(r["leg2_exit_price"]) if r["leg2_exit_price"] not in ("", None) else None, "leg2_reason": l2r}
        st = stage_of["C"].get(r["trade_id"])
        jtxt = (f"JOURNAL: {st[0]} match with row {st[1].row_id} ({st[1].strategy} @ {st[1].time_label}, outcome {st[1].outcome}); outcome label {'agrees' if st[1].outcome and ({'Target': 'TARGET', 'SL': 'INITIAL_FULL_STOP', 'BE': 'T1_THEN_BUFFER_STOP'}.get(st[1].outcome) == r['outcome']) else 'differs/not comparable'}"
                if st else "JOURNAL: AUTOMATED_ONLY (no qualifying journal row; manual rows that day: " + (", ".join(f"{x.strategy}@{x.time_label} {x.outcome}" for x in jr_by_date.get(r["date"], [])) or "none") + ")")
        status = (st[0] if st else "AUTOMATED_ONLY")
        gp, rs = float(r["gross_points_weighted"]), float(r["gross_pnl_rs"])
        panel = [f"{r['strategy']} {r['method']} {r['direction']} | signal {r['signal_time']} (candle end) | entry {r['entry_time']} @ {r['entry_price']}", "Reason for entry: " + ("; ".join(trace[-4:]) if trace else "see signals"),
                 "Evidence: " + ", ".join(f"{k}={v:.2f}" if isinstance(v, float) else f"{k}={v}" for k, v in list(lv.items())[:14] if v not in (None, "", False) and k not in ("unresolved_assumptions", "orb_v2_config_sha256")),
                 f"Levels: stop {r['stop_level']} | T1 {r['t1_level']} (3 lots / 195) | T2 {r['t2_level']} (3 lots / 195) | post-T1 stop {r['post_t1_stop_level']}", f"Leg 1 exit {r['leg1_exit_time'] or '-'} @ {r['leg1_exit_price']} ({l1r}); Leg 2 exit {r['leg2_exit_time'] or '-'} @ {r['leg2_exit_price']} ({l2r})",
                 f"Outcome {r['outcome']} ({r['reason_code']}); gross {gp:+.2f} weighted index points = Rs {rs:+,.0f} on 390 units; net Rs {rs - 70:+,.0f} after the indicative Rs 70/trade (synthetic index P&L, not option P&L)", jtxt,
                 "Day state: " + res["days"]["C"][d]["final_state"]] + ([] if r["ambiguities"] in (0, "0", "") else [f"AMBIGUITY: {r['ambiguity_notes'] if 'ambiguity_notes' in r else 'same-minute stop/target resolved adversely'}"])
        hl = CH._lines_from_levels(lv)
        if ctx.previous:
            hl += [(float(ctx.previous.high), "prev-day high", "#777"), (float(ctx.previous.low), "prev-day low", "#777")]
        svg = CH.chart(f"{r['trade_id']} | config C | {r['strategy']} {r['method']} {r['direction']}", [f"{r['date']} | configuration C ({r['strategy']} / {r['method']}) | trade {r['trade_no']} of the day | journal status: {status}",
                                                                                                         "Yellow = 09:15 candle; blue = EMA(200); dark markers = entry and the two leg exits; dashed lines = stop / T1 / T2 / post-T1 stop."], c, panel, trade=trade, hlines=hl)
        f = R62 / "charts" / f"{r['trade_id']}.svg"
        f.write_text(svg)
        chart_index.append({"trade_id": r["trade_id"], "date": r["date"], "strategy": r["strategy"], "journal_status_C": status, "chart": f"../../phase62_combined_backtest/charts/{r['trade_id']}.svg"})
        n_tr += 1
    write_csv(R63 / "charts" / "trade_links" / "index_all_C_trades_with_journal_status.csv", chart_index)
    for fn, sts in (("strict", ("STRICT",)), ("time_tolerant", ("TIME_TOLERANT",)), ("automated_only", ("AUTOMATED_ONLY",))):
        write_csv(R63 / "charts" / "trade_links" / f"index_{fn}.csv", [x for x in chart_index if x["journal_status_C"] in sts])
    # ------------------------------------------------------------------ day charts (no invented markers)
    def day_chart(d: str, sub: str, note: list[str]):
        dd = pd.Timestamp(d).date()
        if dd not in ctxs:
            return
        ctx = ctxs[dd]
        tz = ctx.candles["bar_start"].iloc[0].tz
        c = candles_of(ctx, "15:25")
        mk, panel = [], list(note)
        cols = {"A": "#e67e22", "B": "#8e44ad", "C": "#c0392b"}
        for k in CFG:
            for r in tr_by_date[k].get(d, []):
                mk.append((ts(d, r["entry_time"], tz), float(r["entry_price"]), f"{k}: {r['strategy']} {r['method']} {r['direction']} {r['entry_time']} @ {r['entry_price']} -> {r['outcome']}", cols[k]))
        for k in CFG:
            panel.append(f"{k} trades: " + ("; ".join(f"{r['strategy']}/{r['method']} {r['direction']} {r['entry_time']} -> {r['outcome']} ({float(r['gross_points_weighted']):+.1f} pts)" for r in tr_by_date[k].get(d, [])) or "none"))
        if d in orb_rej:
            panel.append(f"ORB V2 (provisional ORB-V2-A) rejected: {orb_rej[d]['failed']} | gap {orb_rej[d].get('gap_points')} | scenario {orb_rej[d].get('ema_scenario')} | wrong-side wick {orb_rej[d].get('wrong_side_wick_pct')}")
        a = att[att.date == d]
        if len(a):
            panel.append("IRF V2 attempts: " + " | ".join(f"breakout {x.breakout_candle_start}, reference {x.reference_candle_start or '-'}, support {x.support_wick_low or '-'}, first close below {x.first_close_below_support or 'none'}" for x in a.itertuples()))
        jr = jr_by_date.get(d, [])
        panel.append("MANUAL JOURNAL: " + ("; ".join(f"{x.strategy}@{x.time_label} {x.outcome}" for x in jr) or "no row"))
        hl = [(float(ctx.previous.high), "prev-day high", "#777"), (float(ctx.previous.low), "prev-day low", "#777")] if ctx.previous else []
        (R63 / "charts" / sub / f"{d}.svg").write_text(CH.chart(f"{d} | configurations A (orange) / B (purple) / C (red)", ["Actual five-minute candles; markers are the executed entries of each configuration (none are drawn where a configuration did not trade)."], c, panel, hlines=hl, markers=mk))
    mo = sorted({p["date"] for p in r63["pairs"] if p["config"] == "C" and p["stage"] == "MANUAL_ONLY" and p["date"] in {str(x) for x in ctxs}})
    for d in mo:
        day_chart(d, "manual_only", [f"MANUAL-ONLY date (config C): journal {', '.join(f'{x.strategy}@{x.time_label}' for x in jr_by_date.get(d, []))}; no qualifying automated counterpart. Engine rejection reasons below; no trade marker is invented."])
    for d, r in sorted(orb_rows.items()):
        if r.get("classification", "").startswith("NO ELIGIBLE TRADE (non"):
            continue
        day_chart(d, "orb_vs_irf", [f"ORB vs IRF: {r['classification']} | ORB V2 signal: {r.get('orb_v2_signal')} | IRF V2 first signal (C): {r.get('irf_v2_first_signal_C')} | frozen IRF executed (A): {r.get('irf_executed_A')}"])
    hw = pd.read_csv(R63 / "handwritten_corrections_comparison.csv", dtype=str, keep_default_na=False)
    for x in hw.itertuples():
        day_chart(x.date, "handwritten", [f"HANDWRITTEN {x.correction_id} (page {x.pdf_page}, {x.topic}): {x.author_comment} | status C: {x.status_C}"])
    changed = []
    for d in sorted({str(x) for x in ctxs}):
        sig = {k: sorted((r["strategy"], r["method"], r["entry_time"], r["outcome"]) for r in tr_by_date[k].get(d, [])) for k in CFG}
        if not (sig["A"] == sig["B"] == sig["C"]):
            changed.append(d)
            day_chart(d, "changed_days", ["Configurations differ on this date (A frozen / B Phase 5.3 / C IRF V2 + ORB V2)."])
    # ------------------------------------------------------------------ daily reports: every evaluable session, configuration C (journal-aware)
    n_daily = 0
    for d in sorted(res["days"]["C"]):
        D = res["days"]["C"][d]
        ds = str(d)
        sg = sorted(sigs["C"].get(ds, []), key=lambda s: (s["time"], s["strategy"]))
        tr = sorted(tr_by_date["C"].get(ds, []), key=lambda t: (t["entry_time"], int(t["trade_no"])))
        jr = jr_by_date.get(ds, [])
        L_ = [f"# {ds} - configuration C (IRF V2 + ORB V2 + PDR/PDS first-eligible + RF)", "", f"**Final day state:** {D['final_state']}. Synthetic index P&L; 390 units; no real orders.", "", "## Market context", "",
              f"| item | value |\n|---|---|\n| previous session | {D['prev_date']} O {D['prev_open']} H {D['prev_high']} L {D['prev_low']} C(official) {D['prev_close']} |\n| 09:15 open (first 1-min open) | {D['open_1m']} |\n| opening gap | {D['gap']:+.2f} |\n| EMA(200) at 09:20 | {D['ema_0920']:.2f} |\n| opening range (09:15-09:20) | O {D['or_open']} H {D['or_high']} L {D['or_low']} C {D['or_close']} |",
              "", "## Signals (all confirmed signals of the day, in time order)", ""]
        L_ += ["| time | strategy | method | direction | level / support | controller event |\n|---|---|---|---|---|---|"] + [f"| {s['time']} | {s['strategy']} | {s['method']} | {s['direction']} | {s['level_or_support']} | {s['controller_event'][:90]} |" for s in sg] if sg else ["_no confirmed signal from any strategy_"]
        if ds in orb_rej:
            L_ += ["", f"ORB V2 evaluated and rejected: **{orb_rej[ds]['failed']}**."]
        a = att[att.date == ds]
        if len(a):
            L_ += ["", "IRF V2 Method 2 attempts: " + " | ".join(f"breakout {x.breakout_candle_start}, extension {x.extension_candle_start or '-'}, reference red candle {x.reference_candle_start or '-'} (support {x.support_wick_low or '-'}), first close below {x.first_close_below_support or 'none'}, EMA-28 rejected a break: {x.ema_28_rejected_a_break}" for x in a.itertuples())]
        L_ += ["", "## Earliest eligible signal and selection", ""]
        L_ += [f"Earliest confirmed signal: {sg[0]['time']} {sg[0]['strategy']} {sg[0]['method']}. Selected first trade: " + (f"{tr[0]['strategy']} {tr[0]['method']} at {tr[0]['entry_time']}." if tr else "none.")] if sg else ["No signal, no trade."]
        L_ += ["", "## Trades", ""]
        if tr:
            L_ += ["| trade | strategy | dir | entry | stop | T1 | T2 | post-T1 | leg 1 exit | leg 2 exit | outcome | gross pts | gross Rs | net Rs (70) | journal |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
            for r in tr:
                st = stage_of["C"].get(r["trade_id"])
                L_.append(f"| {r['trade_id']} | {r['strategy']}/{r['method']} | {r['direction']} | {r['entry_time']} @ {r['entry_price']} | {r['stop_level']} | {r['t1_level']} | {r['t2_level']} | {r['post_t1_stop_level']} | {r['leg1_exit_time']} @ {r['leg1_exit_price']} | {r['leg2_exit_time']} @ {r['leg2_exit_price']} | {r['outcome']} | {float(r['gross_points_weighted']):+.2f} | {float(r['gross_pnl_rs']):+,.0f} | {float(r['gross_pnl_rs']) - 70:+,.0f} | {st[0] if st else 'AUTOMATED_ONLY'} |")
            L_ += ["", "Charts: " + ", ".join(f"[{r['trade_id']}](../../charts/{r['trade_id']}.svg)" for r in tr)]
        else:
            L_ += ["_no trade_"]
        L_ += ["", "## Manual journal", "", ("; ".join(f"row {x.row_id}: {x.strategy} @ {x.time_label}, outcome {x.outcome}" for x in jr) or "no journal row on this date"), "",
               "Comparison with A / B: " + " | ".join(f"{k}: " + ("; ".join(f"{r['strategy']}@{r['entry_time']} {r['outcome']}" for r in tr_by_date[k].get(ds, [])) or "no trade") for k in ("A", "B"))]
        if ds in changed:
            L_ += ["", "**Configurations differ on this date** (see `charts/changed_days` in Phase 6.3 and `configuration_comparison.md`)."]
        L_ += ["", "State trace:", "", "```"] + D["state_trace"][:12] + ["```"]
        (R62 / "daily" / f"{ds[:7]}").mkdir(parents=True, exist_ok=True)
        (R62 / "daily" / f"{ds[:7]}" / f"{ds}.md").write_text("\n".join(L_))
        n_daily += 1
        if jr:
            (R63 / "daily" / f"{ds}.md").write_text("\n".join([f"# {ds} - manual journal reconciliation (A / B / C)", "", "Journal rows: " + "; ".join(f"row {x.row_id}: {x.strategy} @ {x.time_label}, outcome {x.outcome}" for x in jr), ""] + [
                f"- **{k}**: " + ("; ".join(f"{r['strategy']}/{r['method']} {r['direction']} {r['entry_time']} -> {r['outcome']} [{(stage_of[k].get(r['trade_id']) or ('AUTOMATED_ONLY',))[0]}]" for r in tr_by_date[k].get(ds, [])) or "no trade") for k in CFG] + [
                "", "Journal evidence is date, time label, strategy and outcome only; no direction or price: no exact trade match is verifiable."]))
    print({"trade_charts": n_tr, "daily": n_daily, "manual_only_charts": len(mo), "changed_days": len(changed)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
