"""Phase 3.6: the complete five-strategy NIFTY 50 backtest with the author-corrected, BODY-BASED PDR engine (``strategies/pdr_body.py``).

Exactly like Phase 3.5 there is no new backtesting engine: this is the Phase 3.2 explainable-backtest framework over the Phase 3.0 shared trading-day controller, with one change of input - the PDR
slot of ``phase3.make_engines`` holds ``PDRBodyStrategy``. IRF, ORB, PDS and RF are constructed exactly as before; stops, targets, sizing, cutoff, forced exit and the controller are untouched.
The Phase 3.5 module (``phase35.py``) and its output directory are not modified; ``--pdr-engine revised`` keeps meaning the Phase 3.5 (wick-ceiling) configuration.

All P&L is SYNTHETIC index-point P&L x quantity (the index is not tradable). The body-based zone, the strictly-above opening and the three confirmation alternatives are author statements; every numeric
threshold and zone-boundary convention is a provisional research assumption that the strategy author has NOT approved.
"""

from __future__ import annotations

import json
import shutil
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from nifty_trading.research import phase3 as P
from nifty_trading.research import phase32_build as B
from nifty_trading.research import phase32_render as RN
from nifty_trading.research.phase32_excel import write_workbook
from nifty_trading.research.phase35 import (
    HEADLINE_COST,
    HEADLINE_SLIP,
    engine_contribution,
    read_csv,
    strategy_performance,
    write_csv,
)
from nifty_trading.strategies.pdr_body import PDR_BODY_RULES

ROOT = B.ROOT
OUT_BODY = ROOT / "reports" / "phase3" / "phase36_body_based_pdr"
P30_DIR = ROOT / "reports" / "phase3" / "baseline"
P32_DIR = ROOT / "reports" / "phase3" / "phase32"
P35_DIR = ROOT / "reports" / "phase3" / "phase35_combined"
CSV_NAMES = {"daily_summary.csv": "daily", "all_trades_detailed.csv": "trades", "entry_condition_details.csv": "checks", "exit_details.csv": "legs", "candle_analysis.csv": "candles",
             "all_strategy_signals.csv": "signals", "ignored_signals.csv": "ignored", "rejected_signals.csv": "rejected", "manual_journal_comparison.csv": "manual_cmp",
             "manual_verification_issues.csv": "issues", "manual_journal_normalized.csv": "manual_norm"}
PROVISIONAL = ("Author statements: the previous day's high is considered and a zone drawn (multiple highs connected); wicks are ignored and bodies considered; the session must open strictly above the zone; "
               "one good green body OR lower price rejection OR hammer candle is required (no fixed percentage / wick-size threshold is required); the candle should close above the zone. "
               "Provisional research assumptions (NOT approved by the author): the numeric thresholds of the three patterns (RESEARCH_DEFAULT, carried from Phase 3.5 for comparability), reading 'body high' as "
               "max(open, close), the zone lower boundary (hull of the member bodies), the multiple-body-high cluster parameters, the zero-height policy and the wait policy. No signal is VERIFIED.")


# ------------------------------------------------------------------------------------------------------------------------------ ledgers of the earlier phases
def load_phase30_ledger() -> list[dict]:
    rows = read_csv(P30_DIR / "trades.csv")
    for r in rows:
        r["gross_pnl_rs"] = float(r["gross_pnl_rs"])
        r["qty_total"] = float(r["qty_total"])
        r["trade_no"] = int(r["trade_no"])
        r["holding_minutes"] = float(r["holding_minutes"]) if r["holding_minutes"] not in ("", None) else None
    return rows


def load_phase35_ledger() -> list[dict]:
    """The Phase 3.5 trades re-shaped into ledger rows (the same fields the metric helpers read)."""
    out = []
    for r in read_csv(P35_DIR / "all_trades_detailed.csv"):
        out.append({"date": r["date"], "trade_no": int(r["trade_no_of_day"]), "strategy": r["strategy"], "method": r["method"], "direction": r["direction"], "signal_time": r["signal_candle_end"],
                    "entry_time": r["fill_timestamp"][-5:], "entry_price": r["entry_price"], "outcome": r["outcome"], "gross_pnl_rs": float(r["gross_pnl_rs"]), "qty_total": float(r["qty_total"]),
                    "holding_minutes": None})
    return out


def _tkey(r: dict) -> tuple:
    return (r["date"], int(r["trade_no"]), r["strategy"], r["method"], r["direction"], r["signal_time"], r["entry_time"])


def compare_ledgers(old: list[dict], new: list[dict], old_label: str, new_label: str) -> tuple[list[dict], list[dict]]:
    """Per-strategy table and per-session list of changed trade sets between two ledgers (same trade = same day, number, strategy, method, direction, signal time, entry time)."""
    ko, kn = {_tkey(r): r for r in old}, {_tkey(r): r for r in new}
    days = sorted({k[0] for k in ko} | {k[0] for k in kn})
    by_day = []
    for d in days:
        o, n = sorted(k for k in ko if k[0] == d), sorted(k for k in kn if k[0] == d)
        if o == n and all(abs(float(ko[k]["gross_pnl_rs"]) - float(kn[k]["gross_pnl_rs"])) < 1e-6 for k in o):
            continue
        rem, add = [k for k in o if k not in kn], [k for k in n if k not in ko]
        tags = []
        if any(k[2] == "PDR" for k in rem + add):
            tags.append("PDR_TRADE_CHANGED")
        if any(k[2] != "PDR" for k in rem + add):
            tags.append("DOWNSTREAM_CONTROLLER_EFFECT")
        if any(k[1] == 2 for k in rem + add):
            tags.append("SECOND_TRADE_AFFECTED")
        if not o and n:
            tags.append("NEW_TRADING_DAY")
        if o and not n:
            tags.append("TRADING_DAY_REMOVED")

        def fmt(k, src):
            return f"{k[2]}{'' if k[3] == k[2] else ' ' + k[3]} {k[4]} #{k[1]} signal {k[5]} entry {k[6]} @ {src[k]['entry_price']} -> {src[k]['outcome']} gross Rs {float(src[k]['gross_pnl_rs']):,.0f}"
        why = [f"removed {fmt(k, ko)}" for k in rem] + [f"added {fmt(k, kn)}" for k in add]
        net_o = sum(float(ko[k]["gross_pnl_rs"]) - HEADLINE_COST - HEADLINE_SLIP * 2 * float(ko[k]["qty_total"]) for k in o)
        net_n = sum(float(kn[k]["gross_pnl_rs"]) - HEADLINE_COST - HEADLINE_SLIP * 2 * float(kn[k]["qty_total"]) for k in n)
        go, gn = sum(float(ko[k]["gross_pnl_rs"]) for k in o), sum(float(kn[k]["gross_pnl_rs"]) for k in n)
        by_day.append({"date": d, f"{old_label}_trades": " | ".join(f"{k[2]} {k[5]}" for k in o), f"{new_label}_trades": " | ".join(f"{k[2]} {k[5]}" for k in n), f"{old_label}_gross_rs": round(go, 2),
                       f"{new_label}_gross_rs": round(gn, 2), "delta_gross_rs": round(gn - go, 2), f"{old_label}_net_rs": round(net_o, 2), f"{new_label}_net_rs": round(net_n, 2), "tags": ";".join(tags), "explanation": " ; ".join(why)})
    po, pn = {r["strategy"]: r for r in strategy_performance(old)}, {r["strategy"]: r for r in strategy_performance(new)}
    rows = []
    for s in (*P.STRATEGIES, "ALL"):
        rows.append({"strategy": s, f"{old_label}_trades": po[s]["entries"], f"{new_label}_trades": pn[s]["entries"], "delta_trades": pn[s]["entries"] - po[s]["entries"],
                     f"{old_label}_gross_rs": po[s]["gross_pnl_rs"], f"{new_label}_gross_rs": pn[s]["gross_pnl_rs"], "delta_gross_rs": round(pn[s]["gross_pnl_rs"] - po[s]["gross_pnl_rs"], 2),
                     f"{old_label}_net_rs": po[s]["net_illustrative_pnl_rs"], f"{new_label}_net_rs": pn[s]["net_illustrative_pnl_rs"], "delta_net_rs": round(pn[s]["net_illustrative_pnl_rs"] - po[s]["net_illustrative_pnl_rs"], 2)})
    return rows, by_day


def three_way(p30: list[dict], p35: list[dict], p36: list[dict]) -> list[dict]:
    a, b, c = ({r["strategy"]: r for r in strategy_performance(x)} for x in (p30, p35, p36))
    rows = []
    for s in (*P.STRATEGIES, "ALL"):
        rows.append({"strategy": s, "phase30_trades": a[s]["entries"], "phase35_trades": b[s]["entries"], "phase36_trades": c[s]["entries"], "phase30_gross_rs": a[s]["gross_pnl_rs"],
                     "phase35_gross_rs": b[s]["gross_pnl_rs"], "phase36_gross_rs": c[s]["gross_pnl_rs"], "phase30_net_rs": a[s]["net_illustrative_pnl_rs"], "phase35_net_rs": b[s]["net_illustrative_pnl_rs"],
                     "phase36_net_rs": c[s]["net_illustrative_pnl_rs"]})
    return rows


def monthly_rows(p30: list[dict], p35: list[dict], p36: list[dict]) -> list[dict]:
    def mo(rows):
        rows = sorted(rows, key=P.sequence_key)
        return P.monthly(rows, [r["gross_pnl_rs"] for r in rows]), P.monthly(rows, P.apply_costs(rows, HEADLINE_COST, HEADLINE_SLIP))
    (g30, n30), (g35, n35), (g36, n36) = mo(p30), mo(p35), mo(p36)
    months = sorted(set(g30) | set(g35) | set(g36))
    return [{"month": m, "phase30_gross_rs": round(g30.get(m, 0.0), 2), "phase35_gross_rs": round(g35.get(m, 0.0), 2), "phase36_gross_rs": round(g36.get(m, 0.0), 2), "phase30_net_rs": round(n30.get(m, 0.0), 2),
             "phase35_net_rs": round(n35.get(m, 0.0), 2), "phase36_net_rs": round(n36.get(m, 0.0), 2)} for m in months]


def manual_pdr_rows_three(b: B.Bundle) -> list[dict]:
    o30 = {c["journal_row"]: c for c in read_csv(P32_DIR / "manual_vs_automated.csv") if c["journal_row"]}
    o35 = {c["journal_row"]: c for c in read_csv(P35_DIR / "manual_journal_comparison.csv") if c["journal_row"]}
    out = []
    for c in b.manual_cmp:
        if not c["journal_row"]:
            continue
        r = str(c["journal_row"])
        touched = [c["journal_strategy"], o30[r]["journal_strategy"], o30[r]["auto_strategy"], o35[r]["auto_strategy"], c["auto_strategy"]]
        if "PDR" not in touched:
            continue

        def cell(x):
            return f"{x['match_classification']} {x['auto_strategy']} {x['auto_entry_time']}".strip() if x["trade_id"] else x["match_classification"]
        out.append({"journal_row": r, "date": c["date"], "journal_strategy": c["journal_strategy"], "manual_time": c["manual_entry_time_label"], "manual_outcome": c["manual_outcome"], "phase30": cell(o30[r]),
                    "phase35": cell(o35[r]), "phase36": cell(c), "phase36_explanation": c["explanation"][:700]})
    return out


# ------------------------------------------------------------------------------------------------------------------------------ writing
def clean_generated(out: Path) -> None:
    assert out.name.startswith("phase36"), out
    for sub in ("charts", "daily"):
        if (out / sub).exists():
            shutil.rmtree(out / sub)


def write_all(b: B.Bundle, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    clean_generated(out)
    for name, attr in CSV_NAMES.items():
        write_csv(out / name, getattr(b, attr))
    n_days = RN.write_daily(b, out)
    n_charts = RN.write_charts(b, out)
    RN.write_json(b, out)
    sc = b.scenario
    snap = json.loads((out / "configuration_snapshot.json").read_text())
    snap.update({"phase": "3.6", "pdr_engine": sc.pdr_engine, "pdr_engine_module": "src/nifty_trading/strategies/pdr_body.py (version PDR_BODY_PHASE36)", "pdr_body_config": asdict(sc.pdr_revision),
                 "pdr_body_rule_status": {r["rule_id"]: r["status"] for r in PDR_BODY_RULES}, "pdr_provisional_assumptions": PROVISIONAL,
                 "earlier_pdr_engines_preserved": {"legacy": "src/nifty_trading/strategies/pdr.py (Phase 3.0)", "revised": "src/nifty_trading/strategies/pdr_revised.py (Phase 3.4 / 3.5; --pdr-engine revised)"},
                 "other_engines": "IRF, ORB, PDS, RF constructed exactly as in Phase 3.0 (unchanged)",
                 "signal_construction": "original NIFTY 50 one-minute candles; five-minute candles built causally; 1-minute rows labelled by their START; a signal is stamped at the candle end; fill = open of the next 1-minute bar",
                 "controller": {**snap["controller"], "first_valid_signal_gets_first_trade": True, "second_trade": "only PDR/PDS, only after the first trade's ORIGINAL full stop before Target 1, only from a newly confirmed signal",
                                "simultaneous_signals": "preserved: different strategies in the same minute mark the day UNRESOLVED_EXECUTION (no approved tie-break; no profit-based priority)"},
                 "end_of_day": "provisional forced exit at the open of the 15:14 minute (FORCED-EXIT-002), unchanged from Phase 3.0"})
    (out / "configuration_snapshot.json").write_text(json.dumps(snap, indent=2, default=str))
    write_workbook(b, out / "NIFTY_Daily_Trade_Verification.xlsx")
    perf = strategy_performance(b.ledger)
    write_csv(out / "strategy_performance.csv", perf)
    contrib = engine_contribution(b)
    for r in contrib:
        if r["strategy"] == "PDR":
            r["engine"] = "PDRBodyStrategy (Phase 3.6, body-based zone, open strictly above, provisional thresholds)"
    write_csv(out / "engine_contribution.csv", contrib)
    p30, p35, p36 = load_phase30_ledger(), load_phase35_ledger(), b.ledger
    write_csv(out / "comparison_3way_by_strategy.csv", three_way(p30, p35, p36))
    rows35, days35 = compare_ledgers(p35, p36, "phase35", "phase36")
    rows30, days30 = compare_ledgers(p30, p36, "phase30", "phase36")
    write_csv(out / "comparison_vs_phase35_by_strategy.csv", rows35)
    write_csv(out / "comparison_vs_phase35_by_day.csv", days35)
    write_csv(out / "comparison_vs_phase30_by_strategy.csv", rows30)
    write_csv(out / "comparison_vs_phase30_by_day.csv", days30)
    write_csv(out / "monthly_pnl.csv", monthly_rows(p30, p35, p36))
    write_csv(out / "manual_pdr_rows_three_phases.csv", manual_pdr_rows_three(b))
    cls = Counter(c["match_classification"] for c in b.manual_cmp if c["journal_row"] != "")
    conflicts = sum(1 for d in b.daily if d["day_end_portfolio_state"] == "UNRESOLVED_EXECUTION")
    counts = {"trading_days": len(b.days), "trades": len(b.trades), "daily_journals": n_days, "charts": n_charts, "checks": len(b.checks), "confirmed_signals": len(b.signals), "ignored": len(b.ignored),
              "rejected_or_incomplete": len(b.rejected), "manual_rows": sum(cls.values()), "journal_exact": cls["EXACT_MATCH"], "journal_time_shifted": cls["TIME_SHIFTED_MATCH"], "issues": len(b.issues),
              "simultaneous_conflict_days": conflicts, "recomputation_mismatches": sum(1 for t in b.trades if t["recomputation_mismatches"]),
              "ledger_identical_to_phase30": b.ledger_check["identical"], "ledger_differences_vs_phase30": b.ledger_check["n_differences"]}
    (out / "build_counts.json").write_text(json.dumps(counts, indent=2))
    return {"counts": counts, "perf": perf, "rows35": rows35, "days35": days35, "rows30": rows30, "days30": days30, "manual": cls}


def run(out: Path | None = None) -> dict:
    t0 = time.time()
    sc = P.combined_scenario("BODY_BASED_PHASE36")
    out = out or OUT_BODY
    b = B.build(scenario=sc)
    res = write_all(b, out)
    res.update({"bundle": b, "out": out, "seconds": time.time() - t0})
    return res
