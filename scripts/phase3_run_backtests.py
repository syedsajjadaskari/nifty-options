"""Phase 3.0: run the four labelled research scenarios over 2025-09-01..2026-08-31 and write reports/phase3/<scenario>/ plus the comparison.

No parameter is tuned and the scenarios are never combined. Everything printed is SYNTHETIC index-point P&L x quantity.
"""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nifty_trading.core.execution_eligibility import bars_from_frame  # noqa: E402
from nifty_trading.data.sessions import (  # noqa: E402
    build_session_contexts,
    load_daily_official,
    load_one_minute,
    load_warmup_one_minute,
)
from nifty_trading.research import phase3 as P  # noqa: E402

OUT = ROOT / "reports" / "phase3"
COST_GRID = (0.0, 500.0, 1000.0, 1500.0)
SLIP_GRID = (0.0, 0.5, 1.0, 2.0)
HEADLINE = (500.0, 0.5)  # illustrative net: Rs 500 per trade (the manual report's mildest tier) + 0.5 index point adverse per fill
MANUAL = {"trades": 189, "net": 769860, "pf": 1.93, "win_pct_excl_be": 55.17, "max_dd": 68055, "avg": 4073, "target": 80, "sl": 65, "be": 44,
          "by_strategy": {"IRF": 72, "ORB": 88, "PDR": 9, "PDS": 3, "RF": 17}}


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def provenance() -> dict:
    def git(*a):
        try:
            return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, timeout=30).stdout.strip()
        except Exception:  # noqa: BLE001
            return "unavailable"
    src_hash = hashlib.sha256()
    for f in sorted((ROOT / "src").rglob("*.py")):
        src_hash.update(f.relative_to(ROOT).as_posix().encode())
        src_hash.update(f.read_bytes())
    data = {}
    for pat in ("data/processed/nifty50/**/*.parquet", "data/processed/nifty50_daily/*.parquet", "data/processed/nifty50_warmup/**/*.parquet"):
        for f in sorted(ROOT.glob(pat)):
            data[f.relative_to(ROOT).as_posix()] = sha256(f)
    meta = {k: sha256(ROOT / k) for k in ("data/metadata/nse_calendar_2025_2026.json", "data/metadata/session_quality_manifest.json") if (ROOT / k).exists()}
    return {"python": platform.python_version(), "git_head": git("rev-parse", "HEAD"), "git_dirty_files": len(git("status", "--short").splitlines()),
            "src_sha256": src_hash.hexdigest(), "data_files_sha256": data, "metadata_sha256": meta,
            "note": "the working tree holds uncommitted Phase 2.x/3.0 work; src_sha256 is the hash of every src/**/*.py file used for this run"}


def jdump(o):
    return json.dumps(o, indent=2, default=str)


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    fields = fields or (list(rows[0]) if rows else [])
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def fmt(x, pct=False, rs=False):
    if x is None:
        return "-"
    if isinstance(x, float) and x == float("inf"):
        return "inf"
    if rs:
        return f"{x:,.0f}"
    return f"{x:,.2f}" if isinstance(x, float) else str(x)


def summary_table(s: dict) -> list[str]:
    rows = [("Entries", s["entries"]), ("Days with a trade", s["days_traded"]), ("First / second trades", f"{s['first_trades']} / {s['second_trades']}"),
            ("Gross P&L (Rs, synthetic)", fmt(s["total_pnl_rs"], rs=True)), ("Win rate (P&L > 0)", f"{s['win_rate_pct']:.2f}%"),
            ("Profit factor", fmt(s["profit_factor"])), ("Average trade (Rs)", fmt(s["avg_trade_rs"], rs=True)),
            ("Max drawdown (Rs)", fmt(s["max_drawdown_rs"], rs=True)), ("Max consecutive losses", s["max_consecutive_losses"]),
            ("Target 2", s["target2"]), ("T1 then post-T1 stop", s["t1_then_buffer_stop"]), ("Initial full stop", s["initial_full_stop"]),
            ("Forced exits (15:14)", s["forced_exit"]), ("Unresolved executions", s["unresolved"]),
            ("Average holding (minutes)", fmt(s["avg_holding_minutes"]))]
    return ["| metric | value |", "|---|---|"] + [f"| {a} | {b} |" for a, b in rows]


def main() -> None:
    m1 = load_one_minute()
    daily, warm = load_daily_official(), load_warmup_one_minute()
    ctxs, infos = build_session_contexts(m1, daily_df=daily, warmup_1m=warm)
    m1 = m1.assign(_d=m1.timestamp.dt.date)
    bars_by_day = {d: bars_from_frame(g) for d, g in m1.groupby("_d")}
    prov = provenance()
    results, summaries = {}, {}
    for key, sc in P.scenarios().items():
        res = P.run_scenario(sc, ctxs, infos, bars_by_day)
        results[key] = res
        d = OUT / key
        d.mkdir(parents=True, exist_ok=True)
        rows = sorted(res.ledger, key=P.sequence_key)
        gross = [r["gross_pnl_rs"] for r in rows]
        net = P.apply_costs(rows, *HEADLINE)
        all_days = [str(x.day) for x in res.days]
        s_gross, s_net = P.summarize(rows, gross), P.summarize(rows, net)
        by_strategy = {}
        for st in P.STRATEGIES:
            sub = [r for r in rows if r["strategy"] == st]
            by_strategy[st] = (P.summarize(sub, [r["gross_pnl_rs"] for r in sub]), P.summarize(sub, P.apply_costs(sub, *HEADLINE)))
        sigc = P.signal_counts(res.signals_log)
        states = P.day_state_counts(res.days)
        grid = {f"cost{c:g}_slip{sl:g}": P.summarize(rows, P.apply_costs(rows, c, sl)) for c in COST_GRID for sl in SLIP_GRID}
        summaries[key] = {"title": sc.title, "gross": s_gross, "net": s_net, "by_strategy": {k: v[0] for k, v in by_strategy.items()}, "signals": sigc,
                          "day_states": dict(states), "sessions_evaluated": len(res.days), "sessions_excluded": [(str(a), b) for a, b in res.excluded],
                          "sessions_partially_evaluated": [(str(a), b) for a, b in res.partial_coverage],
                          "monthly_gross": P.monthly(rows, gross), "grid": grid,
                          "forced_exit_close_sensitivity_rs": sum((r["forced_exit_reference_close"] - r["leg2_exit_price"]) * (1 if r["direction"] == "LONG" else -1) *
                                                                  (r["qty_leg2"] if r["t1_booked"] else r["qty_total"])
                                                                  for r in rows if r["outcome"] == "FORCED_EXIT" and r["forced_exit_reference_close"] is not None)}
        # ---- files
        write_csv(d / "trades.csv", rows)
        write_csv(d / "rejected_ignored_signals.csv", res.signals_log, ["date", "time", "strategy", "method", "direction", "event", "reason"])
        write_csv(d / "equity_curve.csv", P.equity_curve(rows, gross, all_days))
        mg, mn = P.monthly(rows, gross), P.monthly(rows, net)
        write_csv(d / "monthly_pnl.csv", [{"month": k, "gross_pnl_rs": mg[k], "net_illustrative_pnl_rs": mn.get(k, 0.0), "gross_pct_of_100k_base": 100 * mg[k] / P.CAPITAL_BASE} for k in mg])
        sp = []
        total_g = s_gross["total_pnl_rs"] or 1.0
        for st, (g, n) in by_strategy.items():
            sp.append({"strategy": st, "entries": g["entries"], "first_trades": g["first_trades"], "second_trades": g["second_trades"], "gross_pnl_rs": g["total_pnl_rs"],
                       "net_illustrative_pnl_rs": n["total_pnl_rs"], "win_rate_pct": round(g["win_rate_pct"], 2), "profit_factor": g["profit_factor"],
                       "avg_trade_rs": round(g["avg_trade_rs"], 1), "max_drawdown_rs": g["max_drawdown_rs"], "max_consecutive_losses": g["max_consecutive_losses"],
                       "target2": g["target2"], "t1_then_buffer_stop": g["t1_then_buffer_stop"], "initial_full_stop": g["initial_full_stop"], "forced_exit": g["forced_exit"],
                       "unresolved": g["unresolved"], "avg_holding_minutes": g["avg_holding_minutes"], "contribution_pct_of_gross": round(100 * g["total_pnl_rs"] / total_g, 1)})
        write_csv(d / "strategy_performance.csv", sp)
        snap = {"scenario": key, "title": sc.title, "proposals": asdict(sc.proposals), "trade": asdict(sc.trade), "per_strategy_levels": {st: {"initial_stop_points": sc.trade.stop_points(st), "target1_points": sc.trade.t1_points, "target2_points": sc.trade.t2_points(st),
                                                           "target2_status": sc.trade.t2_status(st), "post_t1_stop": f"LONG: entry - {sc.trade.post_t1_buffer_points:g}; SHORT: entry + {sc.trade.post_t1_buffer_points:g}"}
                                                   for st in P.STRATEGIES},
                "lots": {"total": sc.trade.total_lots, "leg1": sc.trade.leg1_lots, "lot_size": sc.trade.lot_size},
                "previous_day_level_window": sc.proposals.prev_day_level_window, "day_rules": {"entry_cutoff": "13:00 IST", "max_entries": 2,
                "second_trade_strategies": ["PDR", "PDS"], "tie_break": None}, "period": ["2025-09-01", "2026-08-31"], "forced_exit": "15:14 IST at the bar OPEN (assumption FORCED-EXIT-002)",
                "cost_headline": {"cost_per_trade_rs": HEADLINE[0], "slippage_points_per_fill": HEADLINE[1]}, "cost_grid": {"cost_per_trade_rs": COST_GRID, "slippage_points_per_fill": SLIP_GRID}}
        (d / "config_snapshot.json").write_text(jdump(snap))
        (d / "provenance.json").write_text(jdump(prov))
        amb = [f"# Execution ambiguity report - {key}\n", f"{len(res.ambiguities)} ambiguities were resolved by the conservative rule (stop before target; post-T1 stop before Target 2). "
               f"{sum(1 for r in rows if r['adverse_slippage_points'] > 0)} trades had a gap through a stop (adverse slippage logged).\n",
               "| date | trade | strategy | note |", "|---|---|---|---|"] + [f"| {a['date']} | {a['trade_no']} | {a['strategy']} | {a['note'].replace('|', '/')} |" for a in res.ambiguities]
        slip = [r for r in rows if r["adverse_slippage_points"] > 0]
        amb += ["\n## Gap-through-stop fills (worse than the stop level)\n", "| date | trade | strategy | outcome | adverse slippage (points) |", "|---|---|---|---|---|"] + [
            f"| {r['date']} | {r['trade_no']} | {r['strategy']} | {r['outcome']} | {r['adverse_slippage_points']:.2f} |" for r in slip]
        (d / "execution_ambiguity_report.md").write_text("\n".join(amb) + "\n")
        # ---- summary markdown
        md = [f"# {sc.title}\n", "**Exploratory research result. Synthetic index-point P&L x quantity; the NIFTY 50 index is not tradable. Not optimised, not approved, not a forecast.**\n",
              f"Period 2025-09-01..2026-08-31; sessions evaluated {len(res.days)}; wholly excluded {len(res.excluded)}; evaluated only partially {len(res.partial_coverage)} (listed at the end).\n", "## Combined strategy - gross (zero cost)\n", *summary_table(s_gross),
              f"\n## Illustrative net (Rs {HEADLINE[0]:,.0f} per trade + {HEADLINE[1]} point slippage per fill)\n", f"Net P&L Rs {fmt(s_net['total_pnl_rs'], rs=True)}; profit factor {fmt(s_net['profit_factor'])}; "
              f"max drawdown Rs {fmt(s_net['max_drawdown_rs'], rs=True)}; win rate {s_net['win_rate_pct']:.2f}%.\n",
              "## Signals and days\n", "| item | count |", "|---|---|"] + [f"| {k} | {v} |" for k, v in sigc["total"].items()] + [f"| day final state {k} | {v} |" for k, v in sorted(states.items())] + [
              "\n## By strategy (gross)\n", "| strategy | entries | 1st/2nd | gross P&L | win % | PF | avg | max DD | max consec. losses | contribution |", "|---|---|---|---|---|---|---|---|---|---|"]
        for r in sp:
            md.append(f"| {r['strategy']} | {r['entries']} | {r['first_trades']}/{r['second_trades']} | {fmt(r['gross_pnl_rs'], rs=True)} | {r['win_rate_pct']} | {fmt(r['profit_factor'])} | {fmt(r['avg_trade_rs'], rs=True)} | {fmt(r['max_drawdown_rs'], rs=True)} | {r['max_consecutive_losses']} | {r['contribution_pct_of_gross']}% |")
        md += ["\n## Monthly gross P&L (Rs; % of the report's assumed Rs 1,00,000 base)\n", "| month | gross P&L | % of base |", "|---|---|---|"] + [f"| {k} | {fmt(v, rs=True)} | {100 * v / P.CAPITAL_BASE:.1f}% |" for k, v in mg.items()]
        md += ["\n## Cost x slippage sensitivity (net P&L Rs / profit factor)\n", "| cost per trade \\ slippage per fill | " + " | ".join(f"{x:g} pt" for x in SLIP_GRID) + " |", "|---|" + "---|" * len(SLIP_GRID)]
        for c in COST_GRID:
            md.append(f"| Rs {c:,.0f} | " + " | ".join(f"{fmt(grid[f'cost{c:g}_slip{sl:g}']['total_pnl_rs'], rs=True)} / {fmt(grid[f'cost{c:g}_slip{sl:g}']['profit_factor'])}" for sl in SLIP_GRID) + " |")
        md += ["\nCost assumptions: a fixed Rs per round trip (the manual report's illustrative tiers) plus an adverse slippage of s points on every fill (entry of all units, exits of all units = 2 x quantity x s). These are placeholders: the index is not directly tradable, so no real brokerage/charges apply to it.\n",
               f"Forced exits: {s_gross['forced_exit']} trades. " + ("With no forced exit in this run the forced-exit price assumption (15:14 open) had no effect; this is a statement about an empty set, not a robustness result."
                if not s_gross["forced_exit"] else f"Using the CLOSE of the 15:14 minute instead of its open would change their gross P&L by Rs {summaries[key]['forced_exit_close_sensitivity_rs']:,.0f} in total."),
               "\n## Research settings and statuses behind these numbers (none is a verified original rule)\n",
               f"* trend: `{sc.proposals.trend_mode}`; PDR zone: `{sc.proposals.pdr_zone_method}`; candle thresholds: strong `{sc.proposals.strong_candle}`, pin bar `{sc.proposals.pin_bar}`; zone proximity {sc.proposals.zone_proximity_points:g} (strict overlap); IRF Method 1: {sc.proposals.m1_max_candles_after_breakout} candle after the breakout.",
               f"* previous-day levels and zones use `{sc.proposals.prev_day_level_window}`: on closing-auction days the previous session's auction print is part of its high/low (it moved the previous-day level on 5 of the 19 sessions that follow an auction day).",
               "* Target 2: IRF 60 and ORB 60 source-verified; PDR/PDS 70 are CONFLICTING (the manual report has winners at 60); RF 60 is a PROPOSAL. Stops: 35 are USER_APPROVED research values; ORB 30 is source-verified.",
               "* ORB Method 2 and the Gap/200DMA setup are research variants; the forced exit (15:14 open) and the unresolved-collision day are implementer assumptions awaiting the owner.",
               "* In the second-trade state only PDR/PDS signals are considered, so another strategy's signal in the same minute as a PDR/PDS signal is rejected, not logged as a conflict.",
               "\n## Sessions excluded\n"] + ([f"* {a}: {b}" for a, b in res.excluded] or ["* none"]) + ["\n## Sessions evaluated only partially\n"] + (
                   [f"* {a}: {b}" for a, b in res.partial_coverage] or ["* none"])
        (d / "summary.md").write_text("\n".join(md) + "\n")
        (d / "summary.json").write_text(jdump(summaries[key]))
        print(key, s_gross["entries"], round(s_gross["total_pnl_rs"]), round(s_gross["profit_factor"], 2), dict(states))
    (OUT / "all_summaries.json").write_text(jdump(summaries))


if __name__ == "__main__":
    main()
