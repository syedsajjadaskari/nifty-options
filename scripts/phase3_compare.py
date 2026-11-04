"""Phase 3.0: consolidated comparison (reports/phase3/phase3_comparison.md) and the comparison with the manual performance report.

Also runs ONE labelled DIAGNOSTIC (not a scenario, never combined): the baseline entries/selection with the superseded exact-entry breakeven stop,
only to separate how much of the difference with the manual report is the new post-T1 stop. Nothing here changes a trading rule."""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import pandas as pd

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
MANUAL = {"trades": 189, "days": 180, "net": 769860, "pf": 1.93, "win_pct_excl_be": 55.17, "max_dd": 68055, "avg": 4073, "target": 80, "sl": 65, "be": 44,
          "by_strategy": {"IRF": 72, "ORB": 88, "PDR": 9, "PDS": 3, "RF": 17}, "target_total": 1368900, "be_total": 231660, "sl_total": -830700}
NAMES = {"baseline": "A baseline", "ema_structure": "B structure trend", "pdr_shelf": "C PDR shelf", "sl40": "D 40-pt stop"}


def f(x, rs=False):
    if x is None:
        return "-"
    if isinstance(x, float) and x == float("inf"):
        return "inf"
    return f"{x:,.0f}" if rs else (f"{x:,.2f}" if isinstance(x, float) else str(x))


def main() -> None:
    S = json.loads((OUT / "all_summaries.json").read_text())
    L = {k: pd.read_csv(OUT / k / "trades.csv") for k in S}
    keys = list(S)
    md = ["# Phase 3.0 - comparison of the four exploratory scenarios and of the manual report\n",
          "**Exploratory research, not optimised, not approved.** Synthetic index-point P&L x quantity (6 lots = 390 units at 65); the NIFTY 50 index is not tradable. Each scenario is a fixed, labelled configuration; "
          "the scenarios are **not** combined and no scenario was chosen because of its result. Settings that are research assumptions, not verified rules: EMA-only trend, the PDR zone candidates, candle thresholds, "
          "the RF 60-point target, the forced-exit time and price (15:14 open), and the unresolved-collision treatment.\n",
          "## 1. Side by side (gross = zero cost)\n", "| metric | " + " | ".join(NAMES[k] for k in keys) + " |", "|---|" + "---|" * len(keys)]
    rows = [("Sessions evaluated", lambda s: s["sessions_evaluated"]), ("Days with a trade", lambda s: s["gross"]["days_traded"]), ("Entries", lambda s: s["gross"]["entries"]),
            ("First / second trades", lambda s: f"{s['gross']['first_trades']} / {s['gross']['second_trades']}"),
            ("Gross P&L (Rs)", lambda s: f(s["gross"]["total_pnl_rs"], True)), ("Illustrative net P&L (Rs 500/trade + 0.5 pt/fill)", lambda s: f(s["net"]["total_pnl_rs"], True)),
            ("Win rate (P&L > 0), gross", lambda s: f"{s['gross']['win_rate_pct']:.1f}%"), ("Profit factor, gross", lambda s: f(s["gross"]["profit_factor"])),
            ("Profit factor, illustrative net", lambda s: f(s["net"]["profit_factor"])), ("Average trade (Rs), gross", lambda s: f(s["gross"]["avg_trade_rs"], True)),
            ("Max drawdown (Rs), gross", lambda s: f(s["gross"]["max_drawdown_rs"], True)), ("Max drawdown (Rs), illustrative net", lambda s: f(s["net"]["max_drawdown_rs"], True)),
            ("Max consecutive losses", lambda s: s["gross"]["max_consecutive_losses"]), ("Target 2", lambda s: s["gross"]["target2"]),
            ("T1 then post-T1 stop", lambda s: s["gross"]["t1_then_buffer_stop"]), ("Initial full stop", lambda s: s["gross"]["initial_full_stop"]),
            ("Forced exits", lambda s: s["gross"]["forced_exit"]), ("Unresolved executions (trades)", lambda s: s["gross"]["unresolved"]),
            ("Avg holding (min)", lambda s: f(s["gross"]["avg_holding_minutes"])),
            ("Signals rejected by the 13:00 cutoff", lambda s: s["signals"]["total"].get("rejected_cutoff_13_00", 0)),
            ("Signals ignored: another position active", lambda s: s["signals"]["total"].get("ignored_position_active", 0)),
            ("Simultaneous-signal conflicts (days left unresolved)", lambda s: s["signals"]["total"].get("simultaneous_conflicts", 0)),
            ("Months with positive gross P&L (of 12)", lambda s: sum(1 for v in s["monthly_gross"].values() if v > 0))]
    for name, fn in rows:
        md.append(f"| {name} | " + " | ".join(str(fn(S[k])) for k in keys) + " |")
    md += ["\n## 2. Strategy-wise gross P&L (Rs) and entries\n", "| strategy | " + " | ".join(f"{NAMES[k]} (n / P&L / PF)" for k in keys) + " |", "|---|" + "---|" * len(keys)]
    for st in P.STRATEGIES:
        md.append(f"| {st} | " + " | ".join(f"{S[k]['by_strategy'][st]['entries']} / {f(S[k]['by_strategy'][st]['total_pnl_rs'], True)} / {f(S[k]['by_strategy'][st]['profit_factor'])}" for k in keys) + " |")
    md += ["\n## 3. Monthly gross P&L (Rs)\n", "| month | " + " | ".join(NAMES[k] for k in keys) + " |", "|---|" + "---|" * len(keys)]
    for m in S["baseline"]["monthly_gross"]:
        md.append(f"| {m} | " + " | ".join(f(S[k]["monthly_gross"].get(m, 0.0), True) for k in keys) + " |")
    md += ["\n## 4. Cost and slippage sensitivity (net P&L Rs, profit factor) - illustrative\n",
           "Fixed cost per trade (the manual report's own tiers) and adverse slippage per fill on every unit in and out. The index is not directly tradable: these are placeholders, not confirmed product costs.\n"]
    for k in keys:
        md += [f"\n**{NAMES[k]}**\n", "| cost \\ slippage | 0 pt | 0.5 pt | 1 pt | 2 pt |", "|---|---|---|---|---|"]
        for c in (0, 500, 1000, 1500):
            md.append(f"| Rs {c:,} | " + " | ".join(f"{f(S[k]['grid'][f'cost{c}_slip{sl}']['total_pnl_rs'], True)} / {f(S[k]['grid'][f'cost{c}_slip{sl}']['profit_factor'])}" for sl in ("0", "0.5", "1", "2")) + " |")
    # ---------------------------------------------------------------- manual report comparison
    b, g = L["baseline"], S["baseline"]["gross"]
    n = len(b)
    md += ["\n## 5. Comparison with the manual performance report (baseline scenario)\n",
           "The manual report (189 trades on 180 days, Rs 7,69,860, profit factor 1.93) used an exact-entry breakeven stop, discretionary trade selection, and its own entries. The automated system uses the owner's rules "
           "(entry -/+ 6 post-T1 stop, first-signal priority, 13:00 cutoff, forced exit) and *mechanical* proxies for discretionary judgments. **Nothing was changed to force a match**; differences below are descriptive.\n",
           "| item | manual report | automated baseline |", "|---|---|---|",
           f"| trades (entries) | {MANUAL['trades']} | {n} |", f"| days with a trade | {MANUAL['days']} | {g['days_traded']} |", f"| gross P&L (Rs) | {MANUAL['net']:,} | {f(g['total_pnl_rs'], True)} |",
           f"| profit factor | {MANUAL['pf']} | {f(g['profit_factor'])} |", f"| average trade (Rs) | {MANUAL['avg']:,} | {f(g['avg_trade_rs'], True)} |",
           f"| max drawdown (Rs) | {MANUAL['max_dd']:,} | {f(g['max_drawdown_rs'], True)} |",
           f"| Target (T1 + T2) | {MANUAL['target']} | {g['target2']} |", f"| exact-entry breakeven / post-T1 stop | {MANUAL['be']} (BE, +Rs 5,265 each) | {g['t1_then_buffer_stop']} (entry -/+ 6) |",
           f"| full stop-loss | {MANUAL['sl']} | {g['initial_full_stop']} |",
           f"| win rate excluding BE / post-T1 stops: Target / (Target + SL) | {MANUAL['win_pct_excl_be']}% | {100 * g['target2'] / max(1, g['target2'] + g['initial_full_stop']):.2f}% |",
           "\n### Strategy allocation\n", "| strategy | manual trades | automated entries | automated gross P&L (Rs) |", "|---|---|---|---|"]
    for st in P.STRATEGIES:
        md.append(f"| {st} | {MANUAL['by_strategy'][st]} | {S['baseline']['by_strategy'][st]['entries']} | {f(S['baseline']['by_strategy'][st]['total_pnl_rs'], True)} |")
    tgt = b[b.outcome == "TARGET"].gross_pnl_rs
    md += ["\n### Average P&L per outcome class (Rs)\n", "| class | manual | automated |", "|---|---|---|",
           f"| Target | {MANUAL['target_total'] / MANUAL['target']:,.0f} (80 trades) | {tgt.mean():,.0f} ({len(tgt)} trades) |",
           f"| exact-entry BE / post-T1 stop | 5,265 (44) | {b[b.outcome == 'T1_THEN_BUFFER_STOP'].gross_pnl_rs.mean():,.0f} ({(b.outcome == 'T1_THEN_BUFFER_STOP').sum()}) |",
           f"| full stop | {MANUAL['sl_total'] / MANUAL['sl']:,.0f} (65) | {b[b.outcome == 'INITIAL_FULL_STOP'].gross_pnl_rs.mean():,.0f} ({(b.outcome == 'INITIAL_FULL_STOP').sum()}) |"]
    # ---------------------------------------------------------------- labelled diagnostic: legacy exact-entry breakeven
    m1 = load_one_minute()
    ctxs, infos = build_session_contexts(m1, daily_df=load_daily_official(), warmup_1m=load_warmup_one_minute())
    m1 = m1.assign(_d=m1.timestamp.dt.date)
    bars_by_day = {d: bars_from_frame(gp) for d, gp in m1.groupby("_d")}
    sc = P.scenarios()["baseline"]
    diag = P.run_scenario(P.Scenario("diag_legacy_be", "DIAGNOSTIC: baseline entries with the superseded exact-entry breakeven stop", sc.proposals,
                                     replace(sc.trade, post_t1_stop_mode="ENTRY_BREAKEVEN")), ctxs, infos, bars_by_day)
    rows = sorted(diag.ledger, key=P.sequence_key)
    sd = P.summarize(rows, [r["gross_pnl_rs"] for r in rows])
    (OUT / "_diagnostic_legacy_breakeven.json").write_text(json.dumps(sd, indent=2, default=str))
    md += ["\n### Diagnostic (not a scenario): the same baseline with the superseded exact-entry breakeven stop\n",
           "Isolates how much of the gap to the manual report comes from the owner's new post-T1 stop. Not a result to rely on, not combined with anything.\n",
           "| metric | baseline (entry -/+ 6) | diagnostic (exact-entry BE) |", "|---|---|---|",
           f"| entries | {g['entries']} | {sd['entries']} |", f"| gross P&L (Rs) | {f(g['total_pnl_rs'], True)} | {f(sd['total_pnl_rs'], True)} |",
           f"| Target | {g['target2']} | {sd['target2']} |", f"| exact-entry BE (legacy class) / entry -/+ 6 class | {g['legacy_breakeven']} / {g['t1_then_buffer_stop']} | {sd['legacy_breakeven']} / {sd['t1_then_buffer_stop']} |",
           f"| full stop | {g['initial_full_stop']} | {sd['initial_full_stop']} |"]
    notes = OUT / "_analysis_notes.md"
    md += ["\n## 6. Why the results differ (analysis)\n", notes.read_text() if notes.exists() else "(analysis pending)"]
    md += ["\n## 7. Limits\n", "* One 12-month in-sample window, parameters fixed beforehand, no out-of-sample test, no significance testing: nothing here is evidence of an edge.",
           "* Synthetic point P&L x quantity on a non-tradable index; costs/slippage are placeholders; no margin, financing or liquidity model.",
           "* The forced-exit time/price (15:14 open) and the treatment of simultaneous signals (the day is left unresolved) are implementer assumptions awaiting the owner; no trade was force-exited in any scenario, so that assumption did not matter for these numbers.",
           "* 2025-10-23 is evaluated only for IRF (its previous session, the Muhurat day, is not verifiable), so ORB/PDR/PDS/RF could not trade that day; 2025-10-21 (Muhurat) is excluded.",
           "* Previous-day levels use all candles of the previous session, including the closing-auction print on auction days (`prev_day_level_window=ALL_CANDLES`).",
           "* In the second-trade state only PDR/PDS signals are considered, so another strategy's same-minute signal is rejected rather than logged as a conflict (1 of 16 second trades in each scenario).",
           "* Independent audit: all 839 trades of the four ledgers were re-simulated from the raw 1-minute data with 0 mismatches (`phase3_audit.md`)."]
    (OUT / "phase3_comparison.md").write_text("\n".join(md) + "\n")
    print("written; diagnostic gross", round(sd["total_pnl_rs"]), "entries", sd["entries"])


if __name__ == "__main__":
    main()
