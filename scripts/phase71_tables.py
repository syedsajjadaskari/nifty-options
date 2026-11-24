"""Phase 7.1 driver, stage 'tables': tabulates the cached portfolio runs (both windows): performance, strategy win rates, monthly / annual, cost sensitivity, trade-set attribution against B, EMA diagnostics
(all five strategies, all interpretations), 27-vs-28 comparison, ORB crossing conflicts, and the manual-journal reconciliation (one-to-one, Phase 5.6 matcher unchanged)."""

from __future__ import annotations

import json
import pickle
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd  # noqa: E402
import phase65b_run as B65  # noqa: E402  (read-only reuse of its pure helper functions)
import phase71_run as R71  # noqa: E402
from phase61_common import JOURNAL  # noqa: E402

from nifty_trading.research import phase55 as X  # noqa: E402
from nifty_trading.research import phase56 as M  # noqa: E402

SP = R71.SP
OUT = Path(__file__).resolve().parents[1] / "reports/phase7/phase71_global_ema_and_final_validation"
CONFIGS = R71.CONFIGS
STRATS = ["IRF", "ORB", "PDR", "PDS", "RF"]
COSTS = B65.COSTS


def load(w, k):
    return pickle.loads((SP / "p71cache" / f"run71_{w}_{k}.pkl").read_bytes())


def wcsv(rows, name):
    pd.DataFrame(rows).to_csv(OUT / name, index=False)


def main() -> int:  # noqa: C901
    runs = {w: {k: load(w, k) for k in CONFIGS if (SP / "p71cache" / f"run71_{w}_{k}.pkl").exists()} for w in "AB"}
    full, wr, monthly, annual, cost, trades_all, legs, sigs_all, attrib, tradecmp = [], [], [], [], [], [], [], [], [], []
    for w in "AB":
        base = {B65.key_of(r): r for r in runs[w]["B"]["ledger"]}
        base_sig = {(s["date"], s["time"], s["strategy"], s["method"], s["direction"]) for s in runs[w]["B"]["signals"]}
        for k, run in runs[w].items():
            led = run["ledger"]
            m = B65.metrics(led)
            nsig = len(run["signals"])
            nsig_first = sum(1 for s in run["signals"] if s["strategy"] != "IRF" or s["cycle_no"] in (1, "1", ""))
            full.append({"window": w, "config": k, "label": CONFIGS[k], "confirmed_signal_records": nsig, "confirmed_signals_irf_first_cycle_only": nsig_first, **m,
                         **{f"net_rs_{c}": round(sum(X.net_pnl(r, fx, sl, pf) for r in led), 0) for c, fx, sl, pf in COSTS}})
            for s in STRATS:
                sel = [r for r in led if r["strategy"] == s]
                ms = B65.metrics(sel)
                wr.append({"window": w, "config": k, "strategy": s, "executed_trades": ms["trades"], "winners": ms["winners_gross"], "losers": ms["losers_gross"], "breakeven": ms["breakeven_gross"], "gross_win_rate_pct": ms["gross_win_rate_pct"],
                           "profit_factor": ms["profit_factor"], "avg_win_rs": ms["avg_win_rs"], "avg_loss_rs": ms["avg_loss_rs"], "gross_points": ms["gross_points"], "gross_rs": ms["gross_rs"], "t1_hits": ms["t1_hit"], "t2_hits": ms["t2_hit"],
                           "initial_stops": ms["initial_stop"], "post_t1_stops": ms["post_t1_stop"], "forced_exits": ms["forced_exit"]})
            for lab, fn, tgt in (("month", lambda r: r["date"][:7], monthly), ("calendar_year", lambda r: r["date"][:4], annual)):
                for kk, sel in X.group(led, fn).items():
                    ms = B65.metrics(sel)
                    tgt.append({"window": w, "config": k, lab: kk, "trades": ms["trades"], "winners": ms["winners_gross"], "losers": ms["losers_gross"], "gross_points": ms["gross_points"], "gross_rs": ms["gross_rs"], "net_rs_70_per_trade": ms["net_rs"]})
            for c, fx, sl, pf in COSTS:
                mm = B65.metrics(led, fx, sl, pf)
                cost.append({"window": w, "config": k, "scenario": c, "fixed_rs": fx, "slippage_pts_per_side": sl, "per_fill": pf, "trades": mm["trades"], "net_win_rate_pct": mm["net_win_rate_pct"], "net_rs": mm["net_rs"],
                             "profit_factor_net": mm["profit_factor"], "max_dd_net_rs": mm["max_drawdown_rs"]})
            for r in led:
                trades_all.append({"window": w, "config": k, **{kk: r.get(kk) for kk in ("trade_id", "date", "strategy", "method", "direction", "signal_time", "entry_time", "entry_price", "stop_level", "t1_level", "t2_level", "post_t1_stop_level",
                                                                                           "outcome", "reason_code", "gross_points_weighted", "gross_pnl_rs", "holding_minutes")}})
                legs.append({"window": w, "config": k, "trade_id": r.get("trade_id"), "date": r["date"], "strategy": r["strategy"], "leg": "T1 leg (3 lots = 195 units)", "exit_time": r.get("leg1_exit_time"), "exit_price": r.get("leg1_exit_price"), "units": r.get("qty_leg1")})
                legs.append({"window": w, "config": k, "trade_id": r.get("trade_id"), "date": r["date"], "strategy": r["strategy"], "leg": "T2 leg (3 lots = 195 units)", "exit_time": r.get("leg2_exit_time"), "exit_price": r.get("leg2_exit_price"), "units": r.get("qty_leg2")})
            for s_ in run["signals"]:
                sigs_all.append({"window": w, "config": k, **s_})
            if k == "B":
                continue
            cur = {B65.key_of(r): r for r in led}
            rem, add = sorted(set(base) - set(cur)), sorted(set(cur) - set(base))
            dsig = {(s["date"], s["time"], s["strategy"], s["method"], s["direction"]) for s in run["signals"]}
            for t in rem:
                r = base[t]
                sk = (r["date"], r["signal_time"], r["strategy"], r["method"], r["direction"])
                attrib.append({"window": w, "config": k, "kind": "REMOVED_B_TRADE", "date": t[0], "strategy": t[1], "entry_time": t[2], "outcome": r["outcome"], "gross_pnl_rs": r["gross_pnl_rs"],
                               "effect": "DIRECT (the rule rejected / changed this signal)" if sk not in dsig else "PORTFOLIO (the signal still exists; the day's trade set changed)"})
            for t in add:
                r = cur[t]
                sk = (r["date"], r["signal_time"], r["strategy"], r["method"], r["direction"])
                attrib.append({"window": w, "config": k, "kind": "ADDED_TRADE", "date": t[0], "strategy": t[1], "entry_time": t[2], "outcome": r["outcome"], "gross_pnl_rs": r["gross_pnl_rs"],
                               "effect": "DIRECT (the rule created this signal)" if sk not in base_sig else "PORTFOLIO (existing signal released by a rejected earlier one)"})
            tradecmp.append({"window": w, "config": k, "B_trades": len(base), "config_trades": len(cur), "kept_identical": len(set(base) & set(cur)), "removed": len(rem), "added": len(add),
                             "removed_direct": sum(1 for x in attrib if x["window"] == w and x["config"] == k and x["kind"] == "REMOVED_B_TRADE" and x["effect"].startswith("DIRECT")),
                             "added_direct": sum(1 for x in attrib if x["window"] == w and x["config"] == k and x["kind"] == "ADDED_TRADE" and x["effect"].startswith("DIRECT")),
                             "net_gross_change_rs": round(sum(float(r["gross_pnl_rs"]) for r in cur.values()) - sum(float(r["gross_pnl_rs"]) for r in base.values()), 0)})
    wcsv(full, "full_five_strategy_backtest.csv")
    wcsv(wr, "strategy_win_rates.csv")
    wcsv(monthly, "monthly_performance.csv")
    wcsv(annual, "annual_performance.csv")
    wcsv(cost, "cost_sensitivity.csv")
    wcsv(trades_all, "all_executed_trades.csv")
    wcsv(legs, "all_trade_legs.csv")
    wcsv(sigs_all, "all_daily_signals.csv")
    wcsv(attrib, "trade_set_attribution.csv")
    wcsv(tradecmp, "portfolio_performance.csv")
    # ------------------------------------------------------------------ EMA diagnostics (baseline B signals, every strategy)
    ema_rows = []
    for w in "AB":
        for r in runs[w]["B"]["ema_rows"]:
            ema_rows.append({"window": w, **r})
    ed = pd.DataFrame(ema_rows)
    ed.to_csv(OUT / "ema_distance_interpretations.csv", index=False)
    cmp_rows = []
    for it in ("MIN_CLOSE", "MIN_RANGE", "MAX_CLOSE", "TARGET_SIDE"):
        a, b = f"R_{it}_27", f"R_{it}_28"
        for (w, s), g in ed.groupby(["window", "strategy"]):
            avail = g[g.ema_available == True]  # noqa: E712
            diff = avail[avail[a] != avail[b]]
            cmp_rows.append({"window": w, "strategy": s, "interpretation": it, "signals_with_ema": len(avail), "fail_at_27": int((avail[a] == "FAIL").sum()), "fail_at_28": int((avail[b] == "FAIL").sum()), "decision_differs_27_vs_28": len(diff),
                             "dates_times_that_differ": "; ".join(f"{r.date} {r.time} {r.method}" for r in diff.itertuples())[:600]})
    wcsv(cmp_rows, "ema_27_vs_28_comparison.csv")
    imp = []
    for cfg, (it, n) in ((k, v) for k, v in __import__("nifty_trading.research.phase71.ema_rule", fromlist=["x"]).CONFIG_OF.items() if v):
        col = f"{cfg}_{it}_{n:g}"
        for (w, s), g in ed.groupby(["window", "strategy"]):
            avail = g[g.ema_available == True]  # noqa: E712
            imp.append({"window": w, "strategy": s, "config": cfg, "interpretation": f"{it}@{n:g}", "confirmed_signals": len(g), "ema_available": len(avail), "fail": int((g[col] == "FAIL").sum()), "pass": int((g[col] == "PASS").sum()),
                        "fail_within_13_00": int(((g[col] == "FAIL") & (g.within_13_00 == True)).sum())})  # noqa: E712
    wcsv(imp, "ema_signal_impact_by_strategy.csv")
    # timing sensitivity (setup / reference / confirmation)
    trows = []
    for (w, s), g in ed.groupby(["window", "strategy"]):
        for it in ("MIN_CLOSE", "MIN_RANGE", "MAX_CLOSE", "TARGET_SIDE"):
            conf = g[f"R_{it}_27"]
            for tag in ("SETUP", "REFERENCE"):
                col = f"{tag}_{it}_27"
                rec = g[g[col] != "NOT_RECORDED"]
                if len(rec):
                    trows.append({"window": w, "strategy": s, "interpretation": it, "timing_compared": f"{tag} vs CONFIRMATION", "signals_with_both": len(rec), "decision_differs": int((rec[col] != conf.loc[rec.index]).sum())})
    wcsv(trows, "ema_measurement_timing_sensitivity.csv")
    # ORB crossing conflicts
    orb = ed[(ed.strategy == "ORB")].copy()
    orb["fresh_cross_or_inside"] = orb.candle_touches_or_crosses_ema == True  # noqa: E712
    keep = ["window", "date", "time", "method", "direction", "orb_ema_scenario", "ema", "open", "high", "low", "close", "close_minus_ema", "abs_close_dist", "range_clearance", "relation", "fresh_cross_or_inside",
            "EMA-1_MIN_CLOSE_27", "EMA-2_MIN_RANGE_27", "EMA-3_MAX_CLOSE_27", "EMA-4_MIN_RANGE_28", "EMA-5_TARGET_SIDE_27"]
    wcsv(orb[[c for c in keep if c in orb.columns]], "ema_crossing_conflicts.csv")
    # ------------------------------------------------------------------ manual journal
    jrows, summ = M.load_journal(JOURNAL)
    pairs, jsum, strict_r, tol_r, date_r, man_r, auto_r, wrong_r = [], [], [], [], [], [], [], []
    for k in CONFIGS:
        if k not in runs["A"]:
            continue
        led = [dict(r) for r in runs["A"][k]["ledger"]]
        for r in led:
            mm_ = int(r["signal_time"][:2]) * 60 + int(r["signal_time"][3:]) - 5
            r["signal_candle_start"] = f"{mm_ // 60:02d}:{mm_ % 60:02d}"
        mt = M.match(jrows, led)
        tbd = defaultdict(list)
        for r in led:
            tbd[r["date"]].append(r)
        for st, ps, bucket in (("STRICT", mt["strict"], strict_r), ("TIME_TOLERANT", mt["tolerant"], tol_r), ("DATE_STRATEGY_ONLY", mt["date_strategy_only"], date_r)):
            for p in ps:
                row = {"config": k, "stage": st, "journal_row": p.manual.row_id, "date": p.manual.date, "manual_strategy": p.manual.strategy, "manual_time_label": p.manual.time_label, "manual_outcome": p.manual.outcome,
                       "trade_id": p.trade["trade_id"], "auto_strategy": p.trade["strategy"], "auto_method": p.trade.get("method"), "auto_signal_candle_start": p.trade["signal_candle_start"], "auto_entry_time": p.trade["entry_time"],
                       "auto_entry_price": p.trade["entry_price"], "auto_outcome": p.trade["outcome"], "auto_gross_pnl_rs": p.trade["gross_pnl_rs"], "delta_min": p.delta_minutes,
                       "outcome_label_agrees": M.outcome_agrees(p.manual.outcome, p.trade["outcome"]) if st != "DATE_STRATEGY_ONLY" else ""}
                pairs.append(row)
                bucket.append(row)
        for r in mt["manual_unmatched"]:
            ts = tbd.get(r.date, [])
            wrong = (not r.weekend) and bool(ts) and not any(t["strategy"] == r.strategy for t in ts)
            row = {"config": k, "journal_row": r.row_id, "date": r.date, "strategy": r.strategy, "time_label": r.time_label, "outcome": r.outcome, "weekend_row": r.weekend, "wrong_strategy_date": wrong,
                   "automated_that_day": "/".join(f"{t['strategy']}@{t['entry_time']}" for t in ts)}
            man_r.append(row)
            pairs.append({"config": k, "stage": "MANUAL_ONLY", "journal_row": r.row_id, "date": r.date, "manual_strategy": r.strategy, "manual_time_label": r.time_label, "manual_outcome": r.outcome})
            if wrong:
                wrong_r.append(row)
        for t in mt["trades_unmatched"]:
            auto_r.append({"config": k, "trade_id": t["trade_id"], "date": t["date"], "strategy": t["strategy"], "method": t.get("method"), "entry_time": t["entry_time"], "outcome": t["outcome"],
                           "manual_rows_that_day": "; ".join(f"{x.strategy}@{x.time_label}" for x in jrows if x.date == t["date"]) or "none"})
            pairs.append({"config": k, "stage": "AUTOMATED_ONLY", "trade_id": t["trade_id"], "date": t["date"], "auto_strategy": t["strategy"], "auto_signal_candle_start": t["signal_candle_start"], "auto_outcome": t["outcome"]})
        jsum.append({"config": k, "automated_trades": len(led), "strict": len(mt["strict"]), "time_tolerant": len(mt["tolerant"]), "date_strategy_only": len(mt["date_strategy_only"]), "manual_only": len(mt["manual_unmatched"]),
                     "manual_only_weekend": sum(1 for r in mt["manual_unmatched"] if r.weekend), "automated_only": len(mt["trades_unmatched"]), "wrong_strategy_dates": sum(1 for r in wrong_r if r["config"] == k),
                     "outcome_label_agree_strict_tolerant": sum(1 for p in mt["strict"] + mt["tolerant"] if M.outcome_agrees(p.manual.outcome, p.trade["outcome"])), **{f"strict_{s}": sum(1 for p in mt["strict"] if p.manual.strategy == s) for s in STRATS},
                     "journal_rows": len(jrows)})
    wcsv(pairs, "manual_journal_reconciliation.csv")
    wcsv(strict_r, "strict_matches.csv")
    wcsv(tol_r, "time_tolerant_matches.csv")
    wcsv(date_r, "date_only_matches.csv")
    wcsv(man_r, "manual_only.csv")
    wcsv(auto_r, "automated_only.csv")
    wcsv(wrong_r, "wrong_strategy_dates.csv")
    wcsv(jsum, "journal_match_summary_by_config.csv")
    # journal integrity recount (independent of earlier reports)
    import hashlib
    wk = [r for r in jrows if r.weekend]
    st = {"journal_sha256": hashlib.sha256(Path(JOURNAL).read_bytes()).hexdigest(), "data_rows": len(jrows), "summary_total_trades": summ.get("Total trades"), "weekend_rows": len(wk),
          "weekend_rows_list": [f"{r.date} {r.strategy}" for r in wk], "by_strategy": dict(Counter(r.strategy for r in jrows)), "columns_available": "sl no, date, entry-time label, strategy, outcome (no direction / price / exit time)"}
    (OUT / "_state" / "journal_recount.json").write_text(json.dumps(st, indent=1, default=str))
    # day-by-day
    dbd = []
    for d in sorted(runs["A"]["B"]["days"]):
        row = {"window": "A", "date": d}
        for k in CONFIGS:
            if k in runs["A"]:
                ts = sorted([r for r in runs["A"][k]["ledger"] if r["date"] == d], key=lambda r: r["entry_time"])
                row[k] = "; ".join(f"{r['strategy']}@{r['entry_time']} {r['outcome']} {float(r['gross_pnl_rs']):+.0f}" for r in ts) or "no trade"
        row["differs_from_B"] = any(row.get(k) != row["B"] for k in CONFIGS if k in row and k != "B")
        dbd.append(row)
    wcsv(dbd, "day_by_day_comparison.csv")
    print("tables ok", {w: len(runs[w]) for w in "AB"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
