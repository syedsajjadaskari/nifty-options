"""Phase 6.0 stages 4-5: ORB V2 signals + standalone 30/60 backtest for all configurations on both periods (5paisa = primary; secondary vendor = labelled sensitivity), plus the
independent audit recomputation. Writes CSV tables into reports/phase6/phase60_orb_from_scratch/ and a results pickle for the later stages. SYNTHETIC index-point P&L; no orders."""

from __future__ import annotations

import json
import pickle
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase60_common import CACHE, OUT, WINDOW_KEYS, get_window, write_csv  # noqa: E402

from nifty_trading.research.orb_v2 import audit as AU  # noqa: E402
from nifty_trading.research.orb_v2 import backtest as BT  # noqa: E402
from nifty_trading.research.orb_v2 import config as C  # noqa: E402


def main() -> int:
    results: dict = {}
    for w, v in WINDOW_KEYS:
        inp = get_window(w, v)
        cfgs = list(C.CONFIGS.values()) + (list(C.DIAGNOSTICS.values()) if v == "5P" else [])
        for cfg in cfgs:
            rr = BT.run(inp, cfg)
            results[(inp.window, cfg.config_id)] = rr
            print(inp.window, cfg.config_id, BT.signal_counts(rr)["signals"], BT.metrics(rr.trades, cfg.quantity)["total_points"], flush=True)
    (CACHE / "results.pkl").write_bytes(pickle.dumps(results, protocol=4))

    # ---------------------------------------------------------------- tables (primary = 5paisa; vendor sensitivity written separately)
    def rows_for(vendor_suffix: str, kind: str, cfg_filter=None):
        out = []
        for (win, cid), rr in results.items():
            if win.endswith("_TV") != (vendor_suffix == "TV"):
                continue
            if cfg_filter and cid not in cfg_filter:
                continue
            out += (rr.sessions if kind == "sessions" else rr.trades)
        return out

    for suffix, tag in (("5P", ""), ("TV", "vendor_sensitivity_")):
        sess = rows_for(suffix, "sessions")
        trades = rows_for(suffix, "trades")
        write_csv(OUT / f"{tag}all_orb_signals.csv", sess)
        entry_cols = ["trade_id", "config_id", "window", "date", "weekday", "direction", "signal_confirmed_at", "entry_time", "entry_price", "stop", "target", "entry_bar_open", "entry_bar_high",
                      "entry_bar_low", "entry_bar_close", "entry_vs_candle_close", "ema_scenario", "qualifying_category", "major_broken", "inner_broken_n", "gap_beyond_prev_range", "gap_points", "patterns_matched", "primary_level"]
        exit_cols = ["trade_id", "config_id", "window", "date", "direction", "entry_price", "exit_status", "exit_time", "exit_price", "exit_reason", "gross_points", "bars_held", "mfe_points", "mae_points",
                     "ambiguous_same_bar", "alt_exit_reason", "alt_exit_price", "alt_gross_points", "gap_through_stop", "missing_minutes_while_open"]
        write_csv(OUT / f"{tag}all_orb_trades.csv", trades, entry_cols)
        write_csv(OUT / f"{tag}all_orb_exits.csv", trades, exit_cols)

    # ---------------------------------------------------------------- performance tables (5paisa windows; synthetic points x qty)
    perf, cost, monthly, annual, cats = [], [], [], [], []
    for (win, cid), rr in results.items():
        qty = rr.config.quantity
        sc = BT.signal_counts(rr)
        m0 = BT.metrics(rr.trades, qty)
        perf.append({"window": win, "config_id": cid, "vendor": "SECONDARY(sensitivity)" if win.endswith("_TV") else "5paisa(primary)", **{k: sc[k] for k in ("sessions_in_window", "evaluable_sessions", "not_evaluated", "signals", "buy", "sell", "executed_trades")},
                     **{k: v for k, v in m0.items() if k not in ("trades", "long", "short")}, "alt_policy_total_points_if_same_bar_resolved_target_first": round(BT.alt_policy_points(rr.trades), 2)})
        for g in BT.cost_grid(rr.trades, qty):
            cost.append({"window": win, "config_id": cid, **g})
        by_m, by_y = {}, {}
        for t in rr.trades:
            by_m.setdefault(f"{t['date']:%Y-%m}", []).append(t)
            by_y.setdefault(f"{t['date']:%Y}", []).append(t)
        for k, ts in sorted(by_m.items()):
            m = BT.metrics(ts, qty)
            monthly.append({"window": win, "config_id": cid, "month": k, "trades": m["trades"], "wins": m["wins"], "total_points": m["total_points"], "total_rs_gross_qty%d" % qty: m["total_rs"]})
        for k, ts in sorted(by_y.items()):
            m = BT.metrics(ts, qty)
            annual.append({"window": win, "config_id": cid, "calendar_year": k, **{x: m[x] for x in ("trades", "wins", "win_rate_pct", "profit_factor", "total_points", "total_rs", "max_drawdown_rs", "longest_losing_streak")}})
        for key, label in (("qualifying_category", "level eligibility"), ("gap_beyond_prev_range", "open beyond previous-day range"), ("ema_scenario", "EMA scenario"), ("direction", "direction"), ("patterns_matched", "pattern route")):
            for k, m in BT.grouped(rr.trades, key, qty).items():
                cats.append({"window": win, "config_id": cid, "dimension": label, "category": k, "trades": m["trades"], "win_rate_pct": m["win_rate_pct"], "total_points": m["total_points"], "profit_factor": m["profit_factor"]})
    write_csv(OUT / "configuration_performance.csv", perf)
    write_csv(OUT / "trade_cost_sensitivity.csv", cost)
    write_csv(OUT / "monthly_performance.csv", monthly)
    write_csv(OUT / "annual_performance.csv", annual)
    write_csv(OUT / "performance_by_eligibility_category.csv", cats)

    # ---------------------------------------------------------------- independent audit recomputation (5paisa windows, every config)
    audit_rows, summary = [], {}
    for w in ("A", "B"):
        inp = get_window(w, "5P")
        usable = inp.order
        cbd = AU.candles_by_day(inp.minutes, usable)
        AU.add_ema(cbd, usable)
        for cid, cfg in {**C.CONFIGS, **C.DIAGNOSTICS}.items():
            rr = results[(inp.window, cid)]
            eng = {s["date"]: s for s in rr.sessions}
            tr = {t["date"]: t for t in rr.trades}
            d = asdict(cfg)
            n_sig_mismatch = n_trade_mismatch = n_fail_mismatch = n_checked = 0
            for dt, s in eng.items():
                if not s["evaluable"]:
                    continue
                k = inp.order.index(dt)
                prev_d = inp.order[k - 1]
                pinfo = inp.infos[prev_d]
                prev_full = cbd[prev_d]
                prev = prev_full[prev_full["start"].dt.hour * 60 + prev_full["start"].dt.minute + 5 <= (15 * 60 + 15)] if pinfo.cas_regime else prev_full
                prev_close = pinfo.official_close if pinfo.official_close is not None else float(prev["close"].iloc[-1])
                a = AU.decide(inp.day_frames[dt], cbd[dt], prev.reset_index(drop=True), prev_full, prev_close, d)
                n_checked += 1
                ok_sig = a["signal"] == s["signal"]
                ok_fail = sorted(a["failed"]) == sorted(s["failed"].split(";") if s["failed"] else [])
                n_sig_mismatch += not ok_sig
                n_fail_mismatch += not ok_fail
                ok_tr = True
                if a["signal"]:
                    sim = AU.simulate(inp.day_frames[dt], a["signal"], d, "CAS" if inp.infos[dt].cas_regime else None)
                    t = tr.get(dt)
                    if sim is None or t is None:
                        ok_tr = (sim is None) == (t is None)
                    else:
                        g = sim["gross"]
                        ok_tr = (abs(sim["entry"] - t["entry_price"]) < 1e-9 and sim["reason"] == t["exit_reason"] and
                                 ((g is None and t.get("gross_points") is None) or (g is not None and t.get("gross_points") is not None and abs(g - t["gross_points"]) < 1e-9)))
                n_trade_mismatch += not ok_tr
                if not (ok_sig and ok_fail and ok_tr):
                    audit_rows.append({"window": inp.window, "config_id": cid, "date": dt, "engine_signal": s["signal"], "audit_signal": a["signal"], "engine_failed": s["failed"], "audit_failed": ";".join(a["failed"]), "trade_match": ok_tr})
            summary[f"{inp.window}|{cid}"] = {"sessions_checked": n_checked, "signal_mismatches": n_sig_mismatch, "failed_condition_set_mismatches": n_fail_mismatch, "trade_mismatches": n_trade_mismatch}
            print("AUDIT", inp.window, cid, summary[f"{inp.window}|{cid}"], flush=True)
    write_csv(OUT / "audit_discrepancies.csv", audit_rows)
    (OUT / "audit_recomputation_summary.json").write_text(json.dumps(summary, indent=1))
    manifest = {cid: c.to_manifest() for cid, c in {**C.CONFIGS, **C.DIAGNOSTICS}.items()}
    (OUT / "orb_v2_configuration_manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    print("configs:", {k: v["config_sha256"][:12] for k, v in manifest.items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
