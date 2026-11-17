"""Phase 6.2: combined five-strategy backtests (configurations A, B, C and the diagnostics D1 / D2) through the FROZEN controller and exit policy, primary window 2025-09-01..2026-08-31 and robustness window
2022-09-01..2025-08-31 (5paisa only). SYNTHETIC index-point P&L; no orders. Stops with an error if configuration A or B does not reproduce the Phase 5.5 ledgers, or if D1 is not identical to B (IRF V2 == Phase 5.3 IRF)."""

from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import json
import pickle
import platform
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase60_common as P60  # noqa: E402
from phase61_common import R62, ROOT, SCRATCH, window_data, write_csv  # noqa: E402

from nifty_trading.core.exit_policy import FORCED_EXIT_LIMIT  # noqa: E402
from nifty_trading.research import phase3 as P  # noqa: E402
from nifty_trading.research import phase55 as X  # noqa: E402
from nifty_trading.research import phase62 as X2  # noqa: E402
from nifty_trading.research.orb_v2 import config as OC  # noqa: E402
from nifty_trading.strategies import orb_v2_adapter as OA  # noqa: E402
from nifty_trading.strategies.trading_day import DayRules  # noqa: E402

CUTOFF = "13:00"
COSTS = (("GROSS", "Gross synthetic index P&L (no cost)", 0.0, 0.0, False), ("C70_TRADE", "Rs 70 per completed trade", 70.0, 0.0, False), ("C70_FILL", "Rs 70 per order fill (entry + each exit leg)", 70.0, 0.0, True),
         ("C70_S025", "Rs 70 per trade + 0.25 pt slippage per side", 70.0, 0.25, False), ("C70_S05", "Rs 70 per trade + 0.5 pt slippage per side", 70.0, 0.5, False), ("C70_S1", "Rs 70 per trade + 1 pt slippage per side", 70.0, 1.0, False))
P55 = ROOT / "reports" / "phase5" / "phase55_combined_backtest"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def fnum(x) -> float:
    return float(str(x).replace(",", "")) if str(x) not in ("", "None", "nan") else 0.0


def metrics_cost(rows, fixed, slip, per_fill):
    m = X.metrics(rows, 0.0, 0.0)
    seq = [X.net_pnl(r, fixed, slip, per_fill) for r in X.trade_order(rows)]
    pf = X.profit_factor(seq)
    wins = [x for x in seq if x > 0]
    m.update({"net_pnl_rs": round(sum(seq), 2), "win_rate_pct": round(100 * len(wins) / len(seq), 2) if seq else None, "winning_trades": len(wins), "losing_trades": sum(1 for x in seq if x < 0),
              "profit_factor": None if pf is None else ("inf" if pf == float("inf") else round(pf, 3)), "max_drawdown_rs": round(X.max_drawdown(seq), 2)})
    return m


def signal_rows(key: str, tls: dict) -> list[dict]:
    rows = []
    for d in sorted(tls):
        tl = tls[d]
        used = {id(tr.signal): tr for tr in tl.result.trades}
        diag = defaultdict(list)
        for x in tl.result.diagnostics:
            diag[(x.timestamp, x.strategy, x.method, x.direction)].append(f"{x.event}: {x.reason}")
        for r in tl.records:
            if r.signal_status != "CONFIRMED":
                continue
            tr = used.get(id(r))
            lv = r.reference_levels
            rows.append({"config": key, "date": str(d), "time": f"{r.signal_timestamp:%H:%M}", "candle_start": f"{r.signal_candle_start:%H:%M}", "strategy": r.strategy, "method": r.method, "direction": r.direction,
                         "reference_close": r.signal_candle_close, "within_13_00_cutoff": f"{r.signal_timestamp:%H:%M}" <= CUTOFF, "verification_status": r.verification_status,
                         "controller_event": "EXECUTED" if tr else ("; ".join(diag.get((r.signal_timestamp, r.strategy, r.method, r.direction), [])) or "NOT_SELECTED"), "trade_id": f"{d:%Y%m%d}-{tr.trade_no}-{r.strategy}" if tr else "",
                         "level_or_support": lv.get("recent_support") or lv.get("primary_level") or lv.get("recent_resistance") or lv.get("zone") or "", "flags": ";".join(f for f in r.flags if not f.startswith(("PREV", "SESSION")))})
    return rows


def day_rows(tls: dict, key: str) -> dict:
    out = {}
    for d, tl in tls.items():
        ctx = tl.ctx
        c0 = ctx.candles.iloc[0]
        out[d] = {"final_state": tl.result.final_state.value, "state_trace": list(tl.result.state_trace), "diagnostics": [(f"{x.timestamp:%H:%M}" if x.timestamp is not None else "", x.strategy, x.method, x.direction, x.event, x.reason) for x in tl.result.diagnostics],
                  "open_1m": float(ctx.open_price), "prev_date": str(ctx.previous.date) if ctx.previous else "", "prev_open": float(ctx.previous.open) if ctx.previous else None, "prev_high": float(ctx.previous.high) if ctx.previous else None,
                  "prev_low": float(ctx.previous.low) if ctx.previous else None, "prev_close": ctx.prev_close, "gap": (float(ctx.open_price) - ctx.prev_close) if ctx.prev_close is not None else None, "ema_0920": float(c0["ema200_5m"]),
                  "or_high": float(c0["high"]), "or_low": float(c0["low"]), "or_open": float(c0["open"]), "or_close": float(c0["close"]), "session_flags": list(ctx.data_flags)}
    return out


def run_window(win: str, sc, with_d: bool):
    ctxs, infos, bars, cal, label = window_data(win)
    inp = P60.get_window(win, "5P")
    orb = OA.ORBV2Strategy(OA.build_decisions(inp, OC.A), OC.A, proposals=sc.proposals, trade=sc.trade)
    keys = X2.KEYS if with_d else ("A", "B", "C")
    tls = {}
    for k in keys:
        orb.rejections.clear()
        orb.integration_checks.clear()
        tls[k] = X2.run_timelines_cfg(k, sc, ctxs, bars, orb)
        if k == "C":
            tls["_orb_rejections"] = list(orb.rejections)
            tls["_orb_checks"] = list(orb.integration_checks)
        print(win, k, "sessions", len(tls[k]), "trades", sum(len(t.result.trades) for t in tls[k].values()), flush=True)
    return tls, infos, label, inp


def main() -> int:  # noqa: C901
    R62.mkdir(parents=True, exist_ok=True)
    sc = P.combined_scenario("BODY_BASED_PHASE36")
    res: dict = {}
    state: dict = {"git_head": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()}
    for win, with_d in (("A", True), ("B", True)):
        tls, infos, label, inp = run_window(win, sc, with_d)
        led = {k: X.ledger_rows(k, tls[k]) for k in tls if not k.startswith("_")}
        levels_map = {k: {(str(d), f"{r.signal_timestamp:%H:%M}", r.strategy, r.method, r.direction): (dict(r.reference_levels), list(r.state_trace), list(r.rule_ids_satisfied))
                          for d, tl in tls[k].items() for r in tl.records if r.signal_status == "CONFIRMED"} for k in led}
        res[win] = {"levels": levels_map, "label": label, "ledgers": led, "signals": {k: signal_rows(k, tls[k]) for k in led}, "days": {k: day_rows(tls[k], k) for k in led}, "orb_rejections": tls["_orb_rejections"], "orb_checks": tls["_orb_checks"],
                    "sessions": {k: X.sessions_summary(tls[k]) for k in led}, "signal_counts": {k: X.signal_counts(tls[k]) for k in led}, "provenance": inp.provenance, "n_infos": len(infos)}
    # ------------------------------------------------------------------ reproduction checks (stop on failure)
    ref55 = list(csv.DictReader(open(P55 / "all_executed_trades.csv", newline="")))
    chk = {}
    for k in ("A", "B"):
        ref = {r["trade_id"]: r for r in ref55 if r["config"] == k}
        got = {r["trade_id"]: r for r in res["A"]["ledgers"][k]}
        bad = [t for t in ref if t not in got or abs(fnum(ref[t]["gross_pnl_rs"]) - fnum(got[t]["gross_pnl_rs"])) > 1e-6 or str(ref[t]["entry_price"]) != str(got[t]["entry_price"]) and abs(fnum(ref[t]["entry_price"]) - fnum(got[t]["entry_price"])) > 1e-9]
        chk[k] = {"phase55_trades": len(ref), "reproduced_trades": len(got), "mismatches": len(bad) + len(set(got) - set(ref)), "gross_phase55": round(sum(fnum(r["gross_pnl_rs"]) for r in ref.values()), 2), "gross_now": round(sum(fnum(r["gross_pnl_rs"]) for r in got.values()), 2)}
        if chk[k]["mismatches"] or abs(chk[k]["gross_phase55"] - chk[k]["gross_now"]) > 1e-6:
            raise SystemExit(f"CONFIG {k} DOES NOT REPRODUCE PHASE 5.5: {chk[k]}")
    refB = {r["trade_id"]: r for r in csv.DictReader(open(ROOT / "reports/phase4/windows/B/all_trades_detailed.csv", newline=""))}
    gotB = {r["trade_id"]: r for r in res["B"]["ledgers"]["A"]}
    chk["window_B_A_vs_phase4"] = {"phase4_trades": len(refB), "now": len(gotB), "same_ids": set(refB) == set(gotB), "gross_equal": abs(sum(fnum(r["gross_pnl_rs"]) for r in refB.values()) - sum(fnum(r["gross_pnl_rs"]) for r in gotB.values())) < 1e-6}
    if not (chk["window_B_A_vs_phase4"]["same_ids"] and chk["window_B_A_vs_phase4"]["gross_equal"]):
        raise SystemExit(f"WINDOW B CONFIGURATION A DOES NOT REPRODUCE PHASE 4: {chk['window_B_A_vs_phase4']}")
    for w in ("A", "B"):
        da = {(r["trade_id"], r["entry_price"], r["gross_pnl_rs"]) for r in res[w]["ledgers"]["D1"]}
        db = {(r["trade_id"], r["entry_price"], r["gross_pnl_rs"]) for r in res[w]["ledgers"]["B"]}
        chk[f"D1_equals_B_{w}"] = da == db
    state["reproduction"] = chk
    print(json.dumps(chk, indent=1), flush=True)
    (SCRATCH / "results62.pkl").write_bytes(pickle.dumps(res, protocol=4))
    # ------------------------------------------------------------------ tables (primary window A is the headline; window B is robustness)
    trades_out, legs_out, perf, monthly, annual, cost, amb, sigs = [], [], [], [], [], [], [], []
    for w in ("A", "B"):
        for k, rows in res[w]["ledgers"].items():
            sigs += [{"window": w, **r} for r in res[w]["signals"][k]]
            for r in rows:
                r["window"] = w
                sgn = 1 if r["direction"] == "LONG" else -1
                trades_out.append({"window": w, "config": k, **{c: r.get(c) for c in ("trade_id", "date", "trade_no", "strategy", "method", "direction", "signal_time", "entry_time", "entry_price", "stop_level", "t1_level", "t2_level", "post_t1_stop_level", "qty_total",
                                                                                          "qty_leg1", "qty_leg2", "leg1_exit_time", "leg1_exit_price", "leg2_exit_time", "leg2_exit_price", "outcome", "reason_code", "gross_points_weighted", "gross_pnl_rs", "holding_minutes", "ambiguities", "day_final_state")}})
                for leg, qty, tm, px in ((1, r["qty_leg1"], r["leg1_exit_time"], r["leg1_exit_price"]), (2, r["qty_leg2"], r["leg2_exit_time"], r["leg2_exit_price"])):
                    legs_out.append({"window": w, "config": k, "trade_id": r["trade_id"], "leg": leg, "qty": qty, "entry_price": r["entry_price"], "exit_time": tm, "exit_price": px,
                                     "leg_gross_points": (sgn * (float(px) - float(r["entry_price"]))) if px not in (None, "") else "", "leg_gross_rs": (sgn * (float(px) - float(r["entry_price"])) * float(qty)) if px not in (None, "") else ""})
                if int(r.get("ambiguities") or 0) > 0:
                    amb.append({"window": w, "config": k, "trade_id": r["trade_id"], "date": r["date"], "strategy": r["strategy"], "outcome": r["outcome"], "gross_pnl_rs": r["gross_pnl_rs"], "ambiguity_notes": r.get("ambiguity_notes", "")})
            for cid, lab, fx, sl, pf in COSTS:
                m = metrics_cost(rows, fx, sl, pf)
                cost.append({"window": w, "config": k, "scenario": cid, "label": lab, **{x: m[x] for x in ("trades", "win_rate_pct", "net_pnl_rs", "profit_factor", "max_drawdown_rs")}})
            for strat in ("ALL",) + P.STRATEGIES:
                sel = rows if strat == "ALL" else [r for r in rows if r["strategy"] == strat]
                if not sel:
                    perf.append({"window": w, "config": k, "strategy": strat, "trades": 0})
                    continue
                m = metrics_cost(sel, 0.0, 0.0, False)
                m70 = metrics_cost(sel, 70.0, 0.0, False)
                perf.append({"window": w, "config": k, "strategy": strat, **{x: m[x] for x in ("trades", "first_trades", "second_trades", "winning_trades", "losing_trades", "win_rate_pct", "profit_factor", "gross_points_total", "avg_points_per_trade", "net_pnl_rs",
                                                                                              "max_drawdown_rs", "t1_hits", "t2_hits", "t1_then_post_t1_stop", "initial_full_stops", "forced_exits", "unresolved_exits", "avg_holding_minutes", "ambiguous_trades")},
                             "gross_synthetic_rs": m["net_pnl_rs"], "net_rs_70_per_trade": m70["net_pnl_rs"], "initial_stop_pct": round(100 * m["initial_full_stops"] / m["trades"], 1), "t1_pct": round(100 * m["t1_hits"] / m["trades"], 1),
                             "t2_pct": round(100 * m["t2_hits"] / m["trades"], 1), "post_t1_stop_pct": round(100 * m["t1_then_post_t1_stop"] / m["trades"], 1), "forced_exit_pct": round(100 * m["forced_exits"] / m["trades"], 1)})
            for lab, fn in (("month", lambda r: r["date"][:7]), ("calendar_year", lambda r: r["date"][:4])):
                for kk, sel in X.group(rows, fn).items():
                    m = metrics_cost(sel, 0.0, 0.0, False)
                    m70 = metrics_cost(sel, 70.0, 0.0, False)
                    (monthly if lab == "month" else annual).append({"window": w, "config": k, lab: kk, "trades": m["trades"], "winning_trades": m["winning_trades"], "gross_points": m["gross_points_total"], "gross_rs": m["net_pnl_rs"], "net_rs_70": m70["net_pnl_rs"]})
    write_csv(R62 / "all_signals.csv", sigs)
    write_csv(R62 / "all_executed_trades.csv", trades_out)
    write_csv(R62 / "all_trade_legs.csv", legs_out)
    write_csv(R62 / "strategy_performance.csv", perf)
    write_csv(R62 / "monthly_performance.csv", monthly)
    write_csv(R62 / "annual_performance.csv", annual)
    write_csv(R62 / "cost_sensitivity.csv", cost)
    write_csv(R62 / "intrabar_ambiguities.csv", amb, ["window", "config", "trade_id", "date", "strategy", "outcome", "gross_pnl_rs", "ambiguity_notes"])
    write_csv(R62 / "orb_v2_rejections_config_c.csv", [{"window": w, **r} for w in ("A", "B") for r in res[w]["orb_rejections"]])
    write_csv(R62 / "orb_v2_integration_checks.csv", [{"window": w, **r} for w in ("A", "B") for r in res[w]["orb_checks"]])
    # ------------------------------------------------------------------ signal funnel per strategy (standalone diagnostics, separate from portfolio contributions)
    funnel = []
    for w in ("A", "B"):
        for k, sg in res[w]["signals"].items():
            for strat in P.STRATEGIES:
                s = [x for x in sg if x["strategy"] == strat]
                ev = Counter(("EXECUTED" if x["controller_event"] == "EXECUTED" else x["controller_event"].split(":")[0].split(";")[0].strip() or "NOT_SELECTED") for x in s)
                funnel.append({"window": w, "config": k, "strategy": strat, "confirmed_signals": len(s), "within_13_00": sum(1 for x in s if x["within_13_00_cutoff"]), "executed": ev.get("EXECUTED", 0), "ignored_or_rejected": len(s) - ev.get("EXECUTED", 0),
                               "controller_event_breakdown": json.dumps(dict(ev))})
    write_csv(R62 / "strategy_signal_funnel.csv", funnel)
    # ------------------------------------------------------------------ manifest
    ob = OC.A.to_manifest()
    fr = json.loads((ROOT / "reports/phase4/strategy_freeze.json").read_text())
    sc_trade = sc.trade
    manifest = {"phase": "6.2", "synthetic_pnl_only": True, "git_head_at_run": state["git_head"], "configurations": {k: {"title": X2.TITLES[k], "engines": [type(e).__name__ for e in X2.engines_for(k, sc.proposals, sc.trade, sc.pdr_engine, sc.pdr_revision, OA.ORBV2Strategy({}, OC.A))]} for k in X2.KEYS},
                "new_combined_configuration_id": X2.C_ID, "orb_v2": {"config_id": "ORB-V2-A", "selection": "PROVISIONAL REFERENCE: no owner-selected ORB V2 variant exists; B/C/D were not selected and no relaxed variants were combined", "manifest": ob,
                                                                    "unresolved_assumptions": list(OA.UNRESOLVED), "import_scope": "entry signals only; the standalone 30/60 ledger is not used"},
                "irf_v2": {"version": "IRF-V2-SUPPORT-BREAK", "rule": "OWNER_APPROVED first red candle wick low, strict close below, no retest; search start AFTER_EXTENSION (PROVISIONAL); 28-pt EMA range clearance (PROVISIONAL measure), all methods; day's-low restriction NOT applied"},
                "pdr_pds": "Phase 5.3 first-eligible engines (PROVISIONAL conventions), unchanged; RF unchanged frozen", "frozen_identity_phase4": {k: fr.get(k) for k in ("strategy_freeze_id",) if k in fr},
                "controller": asdict(DayRules()) | {"tie_break": None}, "entry_cutoff_ist": CUTOFF, "forced_exit_limit": str(FORCED_EXIT_LIMIT),
                "position": {"lots": 6, "units_per_lot": 65, "total_units": 390, "legs": "3 + 3 lots (195 + 195)"}, "exit_rules": {"stops": {s: sc_trade.stop_points(s) for s in P.STRATEGIES}, "target_1_points": sc_trade.t1_points, "targets_2": {s: sc_trade.t2_points(s) for s in P.STRATEGIES},
                                                                                                           "post_t1_stop": "entry -/+ 6 points; no trailing", "forced_exit": "open of the 15:14 one-minute bar (provisional); never at/after 15:15; no closing-auction fills", "intrabar": "stop before target inside a 1-minute bar; flagged"},
                "cost_scenarios": [{"id": i, "label": lab, "fixed_rs": fx, "slip_pts_per_side": sl, "per_fill": pf} for i, lab, fx, sl, pf in COSTS], "old_fixed_500_assumption": "NOT USED",
                "data": {"primary": res["A"]["provenance"], "robustness": res["B"]["provenance"]}, "reproduction_checks": chk,
                "environment": {"python": platform.python_version(), "packages": {p: importlib.metadata.version(p) for p in ("pandas", "numpy", "openpyxl", "pytest", "ruff")}},
                "file_hashes": {p: sha(ROOT / p) for p in ("src/nifty_trading/strategies/irf_v2.py", "src/nifty_trading/strategies/orb_v2_adapter.py", "src/nifty_trading/research/phase62.py", "src/nifty_trading/strategies/trading_day.py", "src/nifty_trading/core/exit_policy.py")}}
    (R62 / "configuration_manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    state["summary"] = {w: {k: {"signals": res[w]["signal_counts"][k], "sessions": res[w]["sessions"][k], "gross": metrics_cost(res[w]["ledgers"][k], 0, 0, False)} for k in res[w]["ledgers"]} for w in ("A", "B")}
    (R62 / "phase62_state.json").write_text(json.dumps(state, indent=1, default=str))
    for w in ("A", "B"):
        print(w, {k: (v["gross"]["trades"], v["gross"]["net_pnl_rs"], v["gross"]["profit_factor"]) for k, v in state["summary"][w].items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
