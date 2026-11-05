"""Phase 3.5: the complete five-strategy NIFTY 50 backtest with the Phase 3.4 revised PDR engine.

No new backtesting engine exists here. The run is the Phase 3.2 explainable-backtest framework (``phase32_build`` / ``phase32_render`` / ``phase32_excel``) over the Phase 3.0 shared trading-day
controller, with exactly one change of input: the PDR slot of ``phase3.make_engines`` holds ``PDRRevisedStrategy`` (``--pdr-engine revised``, the default) instead of the legacy ``PDRStrategy``.
``--pdr-engine legacy`` re-runs the Phase 3.0 baseline unchanged and must reproduce its frozen ledger (a regression check of the framework).

IRF, ORB, PDS and RF are constructed exactly as in Phase 3.0; stops, targets, sizing, cutoff, forced exit and the controller are untouched. Nothing is tuned. All P&L is SYNTHETIC index-point P&L x
quantity (the index is not tradable); the PDR pattern thresholds and the open-above-zone requirement are provisional research assumptions that the strategy author has NOT approved.
"""

from __future__ import annotations

import csv
import json
import shutil
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from nifty_trading.research import phase3 as P
from nifty_trading.research import phase32 as X
from nifty_trading.research import phase32_build as B
from nifty_trading.research import phase32_render as RN
from nifty_trading.research.phase32_excel import write_workbook
from nifty_trading.strategies.pdr_revised import PDR_REVISION_RULES

ROOT = B.ROOT
OUT_COMBINED = ROOT / "reports" / "phase3" / "phase35_combined"
OUT_LEGACY_CHECK = ROOT / "reports" / "phase3" / "phase35_legacy_check"
P30_DIR = ROOT / "reports" / "phase3" / "baseline"
P32_DIR = ROOT / "reports" / "phase3" / "phase32"
HEADLINE_COST, HEADLINE_SLIP = X.HEADLINE_COST
CSV_NAMES = {"daily_summary.csv": "daily", "all_trades_detailed.csv": "trades", "trade_entry_conditions.csv": "checks", "trade_exits_detailed.csv": "legs", "candle_analysis.csv": "candles",
             "all_strategy_signals.csv": "signals", "ignored_signals.csv": "ignored", "rejected_signals.csv": "rejected", "manual_journal_comparison.csv": "manual_cmp",
             "manual_verification_issues.csv": "issues", "manual_journal_normalized.csv": "manual_norm"}
PROVISIONAL = ("The PDR pattern thresholds (good green body 60%/20%, rejection 2x wick / top 30%, hammer 2x wick / 10% / 60%), the previous-day-high anchored zone floor (body top), the open-above-zone requirement "
               "(legacy PDR-011) and the wait policy are provisional research assumptions. Only the three author sentences (the day's high is considered and a zone drawn; one of green body / lower-price rejection / "
               "hammer; the candle should close above the zone) are author statements. No signal is VERIFIED.")


def read_csv(p: Path) -> list[dict]:
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def write_csv(p: Path, rows: list[dict]) -> None:
    RN.write_csv(p, rows)


# ------------------------------------------------------------------------------------------------------------------------------ performance
def perf_row(label: str, rows: list[dict]) -> dict:
    rows = sorted(rows, key=P.sequence_key)
    gross = [r["gross_pnl_rs"] for r in rows]
    net = P.apply_costs(rows, HEADLINE_COST, HEADLINE_SLIP)
    sg, sn = P.summarize(rows, gross), P.summarize(rows, net)
    return {"strategy": label, "entries": sg["entries"], "first_trades": sg["first_trades"], "second_trades": sg["second_trades"], "days_traded": sg["days_traded"],
            "gross_pnl_rs": round(sg["total_pnl_rs"], 2), "net_illustrative_pnl_rs": round(sn["total_pnl_rs"], 2), "win_rate_pct": round(sg["win_rate_pct"], 2),
            "profit_factor": round(sg["profit_factor"], 4) if sg["profit_factor"] != float("inf") else "inf", "avg_trade_rs": round(sg["avg_trade_rs"], 2),
            "max_drawdown_rs": round(sg["max_drawdown_rs"], 2), "max_consecutive_losses": sg["max_consecutive_losses"], "target2": sg["target2"],
            "t1_then_buffer_stop": sg["t1_then_buffer_stop"], "initial_full_stop": sg["initial_full_stop"], "forced_exit": sg["forced_exit"], "unresolved": sg["unresolved"],
            "avg_holding_minutes": None if sg["avg_holding_minutes"] is None else round(sg["avg_holding_minutes"], 2)}


def strategy_performance(ledger: list[dict]) -> list[dict]:
    out = [perf_row(s, [r for r in ledger if r["strategy"] == s]) for s in P.STRATEGIES]
    total = sum(r["gross_pnl_rs"] for r in out)
    for r in out:
        r["contribution_pct_of_gross"] = round(100.0 * r["gross_pnl_rs"] / total, 1) if total else None
    all_ = perf_row("ALL", ledger)
    all_["contribution_pct_of_gross"] = 100.0
    return out + [all_]


def engine_contribution(b: B.Bundle) -> list[dict]:
    """How much each of the five engines fed the shared controller: raw engine records, confirmed signals, fully valid signals, executed trades, ignored / rejected."""
    out = []
    for s in P.STRATEGIES:
        rec = [r for tl in b.timelines.values() for r in tl.records if r.strategy == s]
        conf = [x for x in b.signals if x["strategy"] == s]
        out.append({"strategy": s, "engine": ("PDRRevisedStrategy (Phase 3.4, candidate A, provisional thresholds)" if s == "PDR" and b.revised_pdr else
                                              "PDRStrategy (legacy reversal-swing zone)" if s == "PDR" else f"{s}Strategy (unchanged)"),
                    "raw_engine_records": len(rec), "confirmed_signals": len(conf), "fully_valid_signals": sum(1 for x in conf if x["fully_valid_for_execution"]),
                    "signals_within_13_00_cutoff": sum(1 for x in conf if x["within_13_00_cutoff"]), "executed_trades": sum(1 for t in b.trades if t["strategy"] == s),
                    "ignored_signals": sum(1 for x in b.ignored if x["strategy"] == s), "rejected_by_controller": sum(1 for x in b.rejected if x["strategy"] == s and x["category"].startswith("CONTROLLER")),
                    "setups_not_completed": sum(1 for x in b.rejected if x["strategy"] == s and x["category"].startswith("ENGINE")),
                    "contributed_signals_to_controller": len(conf) > 0})
    return out


# ------------------------------------------------------------------------------------------------------------------------------ comparison with Phase 3.0
def _tkey(r: dict) -> tuple:
    return (r["date"], int(r["trade_no"]), r["strategy"], r["method"], r["direction"], r["signal_time"], r["entry_time"])


def compare_with_phase30(b: B.Bundle) -> tuple[list[dict], list[dict], dict]:
    old = read_csv(P30_DIR / "trades.csv")
    for r in old:  # the frozen CSV holds text; the metric helpers need numbers
        r["gross_pnl_rs"] = float(r["gross_pnl_rs"])
        r["qty_total"] = float(r["qty_total"])
        r["trade_no"] = int(r["trade_no"])
        r["holding_minutes"] = float(r["holding_minutes"]) if r["holding_minutes"] not in ("", None) else None
    new = b.ledger
    net_o = dict(zip((_tkey(r) for r in sorted(old, key=P.sequence_key)), P.apply_costs(sorted(old, key=P.sequence_key), HEADLINE_COST, HEADLINE_SLIP), strict=True))
    net_n = dict(zip((_tkey(r) for r in sorted(new, key=P.sequence_key)), P.apply_costs(sorted(new, key=P.sequence_key), HEADLINE_COST, HEADLINE_SLIP), strict=True))
    ko = {_tkey(r): r for r in old}
    kn = {_tkey(r): r for r in new}
    days = sorted({k[0] for k in ko} | {k[0] for k in kn})
    by_day = []
    for d in days:
        o = sorted(k for k in ko if k[0] == d)
        n = sorted(k for k in kn if k[0] == d)
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
        fmt = lambda k, src: f"{k[2]}{'' if k[3] == k[2] else ' ' + k[3]} {k[4]} #{k[1]} signal {k[5]} entry {k[6]} -> {src[k]['outcome']} gross Rs {float(src[k]['gross_pnl_rs']):,.0f}"  # noqa: E731
        why = []
        for k in rem:
            why.append(f"removed {fmt(k, ko)}" + (" (no revised PDR signal reproduces it)" if k[2] == "PDR" else " (its slot was taken by a different controller sequence)"))
        for k in add:
            why.append(f"added {fmt(k, kn)}" + (" (revised PDR signal)" if k[2] == "PDR" else " (this signal existed before but the earlier trade/slot no longer blocks it)"))
        by_day.append({"date": d, "phase30_trades": " | ".join(f"{k[2]} {k[5]}" for k in o), "phase35_trades": " | ".join(f"{k[2]} {k[5]}" for k in n),
                       "phase30_gross_rs": round(sum(float(ko[k]["gross_pnl_rs"]) for k in o), 2), "phase35_gross_rs": round(sum(float(kn[k]["gross_pnl_rs"]) for k in n), 2),
                       "delta_gross_rs": round(sum(float(kn[k]["gross_pnl_rs"]) for k in n) - sum(float(ko[k]["gross_pnl_rs"]) for k in o), 2),
                       "phase30_net_rs": round(sum(net_o[k] for k in o), 2), "phase35_net_rs": round(sum(net_n[k] for k in n), 2), "tags": ";".join(tags), "explanation": " ; ".join(why)})
    cls30 = Counter(c["match_classification"] for c in read_csv(P32_DIR / "manual_vs_automated.csv") if c["journal_row"] != "")
    cls35 = Counter(c["match_classification"] for c in b.manual_cmp if c["journal_row"] != "")
    p_old, p_new = {r["strategy"]: r for r in strategy_performance(old)}, {r["strategy"]: r for r in strategy_performance(new)}
    rows = []
    for s in (*P.STRATEGIES, "ALL"):
        rows.append({"strategy": s, "phase30_trades": p_old[s]["entries"], "phase35_trades": p_new[s]["entries"], "delta_trades": p_new[s]["entries"] - p_old[s]["entries"],
                     "phase30_gross_rs": p_old[s]["gross_pnl_rs"], "phase35_gross_rs": p_new[s]["gross_pnl_rs"], "delta_gross_rs": round(p_new[s]["gross_pnl_rs"] - p_old[s]["gross_pnl_rs"], 2),
                     "phase30_net_rs": p_old[s]["net_illustrative_pnl_rs"], "phase35_net_rs": p_new[s]["net_illustrative_pnl_rs"],
                     "delta_net_rs": round(p_new[s]["net_illustrative_pnl_rs"] - p_old[s]["net_illustrative_pnl_rs"], 2),
                     "phase30_share_of_trades_pct": round(100.0 * p_old[s]["entries"] / p_old["ALL"]["entries"], 1), "phase35_share_of_trades_pct": round(100.0 * p_new[s]["entries"] / p_new["ALL"]["entries"], 1)})
    manual = {"phase30_exact": cls30["EXACT_MATCH"], "phase30_time_shifted": cls30["TIME_SHIFTED_MATCH"], "phase35_exact": cls35["EXACT_MATCH"], "phase35_time_shifted": cls35["TIME_SHIFTED_MATCH"],
              "manual_rows": sum(cls35.values()), "phase30_unmatched": sum(cls30.values()) - cls30["EXACT_MATCH"] - cls30["TIME_SHIFTED_MATCH"],
              "phase35_unmatched": sum(cls35.values()) - cls35["EXACT_MATCH"] - cls35["TIME_SHIFTED_MATCH"], "phase30_extra_automated": sum(1 for c in read_csv(P32_DIR / "manual_vs_automated.csv") if c["match_classification"] == "EXTRA_AUTOMATED_TRADE"),
              "phase35_extra_automated": sum(1 for c in b.manual_cmp if c["match_classification"] == "EXTRA_AUTOMATED_TRADE")}
    return rows, by_day, manual


def manual_pdr_rows(b: B.Bundle) -> list[dict]:
    """Journal rows of PDR (and the disputed ones) under the old and the new run - the part of the journal agreement that this phase can change."""
    old = {c["journal_row"]: c for c in read_csv(P32_DIR / "manual_vs_automated.csv") if c["journal_row"] != ""}
    out = []
    for c in b.manual_cmp:
        if c["journal_row"] == "":
            continue
        o = old.get(str(c["journal_row"]))
        if c["journal_strategy"] != "PDR" and not (o and o["auto_strategy"] == "PDR") and c["auto_strategy"] != "PDR":
            continue
        out.append({"journal_row": c["journal_row"], "date": c["date"], "journal_strategy": c["journal_strategy"], "manual_time": c["manual_entry_time_label"], "manual_outcome": c["manual_outcome"],
                    "phase30_match": o["match_classification"] if o else "", "phase30_auto": f"{o['auto_strategy']} {o['auto_entry_time']}" if o and o["trade_id"] else "",
                    "phase35_match": c["match_classification"], "phase35_auto": f"{c['auto_strategy']} {c['auto_entry_time']}" if c["trade_id"] else "", "phase35_explanation": c["explanation"][:600]})
    return out


# ------------------------------------------------------------------------------------------------------------------------------ writing
def clean_generated(out: Path) -> None:
    """Remove only the generated per-trade charts and per-day journals of this output directory (never anything else, never another phase's directory)."""
    assert out.name.startswith("phase35"), out
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
    snap = json.loads((out / "configuration_snapshot.json").read_text())
    sc = b.scenario
    snap.update({"phase": "3.5", "pdr_engine": sc.pdr_engine, "pdr_engine_module": "src/nifty_trading/strategies/pdr_revised.py" if b.revised_pdr else "src/nifty_trading/strategies/pdr.py",
                 "pdr_revision_config": asdict(sc.pdr_revision) if sc.pdr_revision else None, "pdr_revision_rule_status": {r["rule_id"]: r["status"] for r in PDR_REVISION_RULES} if b.revised_pdr else None,
                 "pdr_provisional_assumptions": PROVISIONAL if b.revised_pdr else "legacy engine: Phase 3.0 research candidate B (reversal swing high)", "other_engines": "IRF, ORB, PDS, RF constructed exactly as in Phase 3.0 (unchanged)",
                 "signal_construction": "original NIFTY 50 one-minute candles; five-minute candles built causally; 1-minute rows labelled by their START; a signal is stamped at the candle end; fill = open of the next 1-minute bar",
                 "controller": {**snap["controller"], "first_valid_signal_gets_first_trade": True, "second_trade": "only PDR/PDS, only after the first trade's ORIGINAL full stop before Target 1, only from a newly confirmed signal",
                                "simultaneous_signals": "preserved: different strategies in the same minute mark the day UNRESOLVED_EXECUTION (no approved tie-break)"}})
    (out / "configuration_snapshot.json").write_text(json.dumps(snap, indent=2, default=str))
    write_workbook(b, out / "NIFTY_Daily_Trade_Verification.xlsx")
    perf = strategy_performance(b.ledger)
    write_csv(out / "strategy_performance.csv", perf)
    contrib = engine_contribution(b)
    write_csv(out / "engine_contribution.csv", contrib)
    cmp_rows, by_day, manual = compare_with_phase30(b)
    write_csv(out / "comparison_vs_phase30.csv", cmp_rows)
    write_csv(out / "comparison_vs_phase30_by_day.csv", by_day)
    write_csv(out / "manual_pdr_rows_phase30_vs_phase35.csv", manual_pdr_rows(b))
    counts = {"trading_days": len(b.days), "trades": len(b.trades), "daily_journals": n_days, "charts": n_charts, "checks": len(b.checks), "confirmed_signals": len(b.signals), "ignored": len(b.ignored),
              "rejected_or_incomplete": len(b.rejected), "manual_rows": manual["manual_rows"], "issues": len(b.issues), "recomputation_mismatches": sum(1 for t in b.trades if t["recomputation_mismatches"]),
              "ledger_identical_to_phase30": b.ledger_check["identical"], "ledger_differences_vs_phase30": b.ledger_check["n_differences"]}
    (out / "build_counts.json").write_text(json.dumps(counts, indent=2))
    return {"counts": counts, "perf": perf, "contrib": contrib, "cmp": cmp_rows, "by_day": by_day, "manual": manual}


def run(pdr_engine: str = "REVISED_PHASE34", out: Path | None = None) -> dict:
    t0 = time.time()
    sc = P.combined_scenario(pdr_engine)
    out = out or (OUT_COMBINED if pdr_engine != "LEGACY" else OUT_LEGACY_CHECK)
    b = B.build(scenario=sc)
    res = write_all(b, out)
    res.update({"bundle": b, "out": out, "seconds": time.time() - t0})
    return res


def by_strategy_text(perf: list[dict]) -> str:
    return ", ".join(f"{r['strategy']} {r['entries']}" for r in perf if r["strategy"] != "ALL")
