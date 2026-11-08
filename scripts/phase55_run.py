"""Phase 5.5: complete five-strategy backtest of configurations A (frozen Phase 3.6), B (Phase 5.3 author-corrected) and C (B + ORB gap crossing) through the FROZEN controller and exit policy. SYNTHETIC index-point P&L; no real option P&L.

  python scripts/phase55_run.py                  primary window 2025-09-01..2025-08-31 + the 2022-09-01..2025-08-31 robustness window
  python scripts/phase55_run.py --skip-robustness

Stops with an error (nothing is written as 'verified') if configuration A does not reproduce the Phase 3.6 results, if B's or C's signal totals differ from the expected references, or if the signal differences between configurations are not
confined to the rules each configuration changes. Writes reports/phase5/phase55_combined_backtest/ (tables, daily reports, charts, workbook) and phase55_state.json (the numbers the documentation generator reads).
The old Rs 500 fixed-cost model is NOT used anywhere here: costs are the owner's indicative Rs 70 per trade plus slippage scenarios (see research/phase55.py).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import platform
import sys
import warnings
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from nifty_trading.core.exit_policy import FORCED_EXIT_LIMIT  # noqa: E402
from nifty_trading.research import phase3 as P  # noqa: E402
from nifty_trading.research import phase4 as P4  # noqa: E402
from nifty_trading.research import phase4_data as D4  # noqa: E402
from nifty_trading.research import phase32_build as B  # noqa: E402
from nifty_trading.research import phase32_render as RN  # noqa: E402
from nifty_trading.research import phase55 as X  # noqa: E402
from nifty_trading.research.phase35 import write_csv  # noqa: E402
from nifty_trading.strategies.trading_day import DayRules  # noqa: E402

OUT = ROOT / "reports" / "phase5" / "phase55_combined_backtest"
P36 = ROOT / "reports" / "phase3" / "phase36_body_based_pdr"
FREEZE = ROOT / "reports" / "phase4" / "strategy_freeze.json"
CUTOFF = "13:00"
FROZEN_ID = "FROZEN-PHASE36-42cea2600bd4"
NEW_FILES = ("src/nifty_trading/strategies/irf_candidates.py", "src/nifty_trading/strategies/irf_phase53.py", "src/nifty_trading/strategies/first_eligible_phase53.py", "src/nifty_trading/strategies/orb_candidates.py",
             "src/nifty_trading/strategies/orb_colour.py", "src/nifty_trading/research/phase53.py", "src/nifty_trading/research/phase55.py")
PROVISIONAL = {
    "A": ["PDR body-based numeric pattern thresholds (PROPOSED, RESEARCH_DEFAULT)", "forced exit at the open of the 15:14 minute (implementer assumption)", "RF Target 2 of 60 (research assumption)", "PDR / PDS Target 2 of 70 versus the report's 60 (recorded source conflict)",
          "no approved tie-break: simultaneous signals of different strategies leave the day unresolved", "stop before target inside a 1-minute bar (conservative convention, not a source rule)", "ORB Method 2 inner level / trendline and strength profile (research constructions)"],
    "B": ["everything provisional in A", "IRF Method 2A support = LOW of the first red candle, searched after the extension candle (level owner-approved; search start and method scope provisional)",
          "IRF minimum 28-point EMA(200) clearance measured to the nearest point of the signal candle's range, inclusive, all IRF methods (PROVISIONAL_EMA_RANGE_DISTANCE; the author's measure and directionality are unconfirmed)",
          "PDR earliest eligible confirmation: green candle or dominant-lower-wick rejection, retest candle excluded (PROVISIONAL_PDR_MINIMAL_CONFIRMATION)", "PDS earliest eligible confirmation via structural dominance tests; weak first red candle still goes to Method 3 (PROVISIONAL_PDS_MINIMAL_QUALITY)",
          "IRF day's-low restriction NOT applied (PENDING_OWNER_DEFINITION)"],
    "C": ["everything provisional in B", "ORB Gap / 200 DMA: the first CANDLE (not only the open) may cross the average (Phase 5.4 candidate; the rulebook's figures draw it, the frozen engine requires the open beyond it)",
          "indicator = the repository's EMA(200) of completed five-minute closes; the rulebook mixes '200 DMA' and '200 EMA' (ORB-MA-001): UNRESOLVED, so C is a labelled provisional research scenario, not the author's confirmed method"]}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def fnum(x) -> float:
    return float(str(x).replace(",", "")) if x not in (None, "") else 0.0


def verify_frozen_identity() -> dict:
    """Recompute the frozen configuration id and verify the implementation: the id formula over the stored hashes / parameters / costs, the live hashes of the 26 active files, and the live parameters."""
    fr = json.loads(FREEZE.read_text())
    blob = json.dumps({"hashes": fr["active_file_hashes"], "params": fr["parameters"], "costs": fr["costs_and_slippage"]}, sort_keys=True, default=str)
    recomputed = "FROZEN-PHASE36-" + hashlib.sha256(blob.encode()).hexdigest()[:12]
    bad = [p for p, h in fr["active_file_hashes"].items() if sha(ROOT / p) != h]
    sc = P.combined_scenario("BODY_BASED_PHASE36")
    live = {"proposal_config": sc.proposals.to_dict(), "trade_config": asdict(sc.trade), "pdr_body_config": asdict(sc.pdr_revision), "day_rules": asdict(DayRules()), "targets_2": {s: sc.trade.t2_points(s) for s in P.STRATEGIES},
            "stops": {s: sc.trade.stop_points(s) for s in P.STRATEGIES}, "target_1_points": sc.trade.t1_points, "post_t1_buffer_points": sc.trade.post_t1_buffer_points,
            "lots": {"total": sc.trade.total_lots, "leg1": sc.trade.leg1_lots, "lot_size_fixed_multiplier": sc.trade.lot_size}, "forced_exit_time": str(sc.trade.forced_exit_time), "entry_cutoff": "13:00 IST", "scenario_key": sc.key, "pdr_engine": sc.pdr_engine}
    live_json = json.loads(json.dumps(live, sort_keys=True, default=str))
    stored = json.loads(json.dumps(fr["parameters"], sort_keys=True, default=str))
    ok = recomputed == fr["frozen_configuration_id"] == FROZEN_ID and not bad and live_json == stored
    if not ok:
        raise SystemExit(f"FROZEN CONFIGURATION VERIFICATION FAILED: id {recomputed} vs {fr['frozen_configuration_id']}; hash mismatches {bad}; live parameters equal stored: {live_json == stored}")
    return {"frozen_configuration_id": fr["frozen_configuration_id"], "id_recomputed_from_stored_blob": recomputed, "active_files_verified": len(fr["active_file_hashes"]), "live_parameters_equal_the_frozen_parameters": True,
            "source_snapshot": fr["source_snapshot"], "git_head_at_freeze": fr["git_head"]}


def config_ids(frozen: dict) -> tuple[dict, dict]:
    fr = json.loads(FREEZE.read_text())
    hashes = dict(fr["active_file_hashes"])
    extra = {f: sha(ROOT / f) for f in NEW_FILES}
    cfgs = {}
    for k in ("B", "C"):
        blob = json.dumps({"frozen_hashes": hashes, "phase5_files": extra, "params": fr["parameters"], "config": k, "provisional": PROVISIONAL[k], "costs": [list(c) for c in X.COST_SCENARIOS]}, sort_keys=True, default=str)
        cfgs[k] = f"PHASE55-{k}-" + hashlib.sha256(blob.encode()).hexdigest()[:12]
    cfgs["A"] = FROZEN_ID
    return cfgs, extra


# entry checks of the Phase 3.2 explainer encode the FROZEN rules; where a configuration deliberately replaces a rule the corresponding check fails by design. Every failure must be explained by the configuration's own change.
_IRF = {"B": "IRF Method 2A support = LOW of the first red candle (Phase 5.3) replaces the frozen swing-low support the check encodes", "C": "IRF Method 2A support = LOW of the first red candle (Phase 5.3) replaces the frozen swing-low support the check encodes"}
EXPLAINED_FAILS = {("IRF", "IRF-M2A-001"): _IRF, ("IRF", "IRF-M2A-002"): _IRF,
                   ("PDR", "PDR-B04"): {k: "PDR minimal confirmation (Phase 5.3) replaces the frozen numeric pattern thresholds the check encodes" for k in ("B", "C")},
                   ("PDS", "PDS-M1-001"): {k: "PDS structural dominance test (Phase 5.3) replaces the frozen numeric good-red thresholds the check encodes" for k in ("B", "C")},
                   ("PDS", "PDS-M2-001"): {k: "PDS structural dominance test (Phase 5.3) replaces the frozen numeric pin-bar thresholds the check encodes" for k in ("B", "C")},
                   ("ORB", "ORB-GAP-LONG-002"): {"C": "ORB gap candle-crossing candidate (Phase 5.4): the candle, not the open, crosses the average; the frozen check requires the open beyond it"},
                   ("ORB", "ORB-GAP-SHORT-002"): {"C": "ORB gap candle-crossing candidate (Phase 5.4): the candle, not the open, crosses the average; the frozen check requires the open beyond it"}}


def sig_key(s: dict) -> tuple:
    return (s["date"], s["strategy"], s["method"], s["direction"], s["time"])


def build_bundles() -> dict:
    sc = P.combined_scenario("BODY_BASED_PHASE36")
    bs = {}
    for k in X.KEYS:
        with X.patched_engines(k):
            bs[k] = B.build(scenario=sc, journal=False)
    return bs


def check_reproduction(bs: dict) -> dict:
    """Configuration A must equal the Phase 3.6 results field for field (trades, signals, ledger totals). Anything else stops the run."""
    ref = {r["trade_id"]: r for r in csv.DictReader(open(P36 / "all_trades_detailed.csv", newline=""))}
    skip = {"rule_configuration_id", "entry_source_partition", "chart_file", "daily_journal", "manual_journal_row", "manual_match_class", "manual_time_label", "manual_outcome"}
    cols = [c for c in next(iter(ref.values())) if c in bs["A"].trades[0] and c not in skip]
    bad = []
    got = {t["trade_id"]: t for t in bs["A"].trades}
    if set(got) != set(ref):
        bad.append(("trade id sets differ", len(got), len(ref)))
    for tid, r in ref.items():
        t = got.get(tid)
        if t is None:
            continue
        for c in cols:
            a, b = str(t[c]), str(r[c])
            if a != b:
                try:
                    if abs(float(a.replace(",", "")) - float(b.replace(",", ""))) < 1e-6:
                        continue
                except ValueError:
                    pass
                bad.append((tid, c, a, b))
                break
    sref = sorted((s["date"], s["time"], s["strategy"], s["method"], s["direction"]) for s in csv.DictReader(open(P36 / "all_strategy_signals.csv", newline="")))
    sa = sorted((s["date"], s["time"], s["strategy"], s["method"], s["direction"]) for s in bs["A"].signals)
    sig_ok = sref == sa
    gross_ref = sum(fnum(r["gross_pnl_rs"]) for r in ref.values())
    gross_a = sum(fnum(r["gross_pnl_rs"]) for r in bs["A"].trades)
    out = {"phase36_trades": len(ref), "configuration_A_trades": len(got), "compared_columns": len(cols), "trade_mismatches": len(bad), "signals_equal": sig_ok, "phase36_signals": len(sref), "configuration_A_signals": len(sa),
           "gross_pnl_rs_phase36": round(gross_ref, 2), "gross_pnl_rs_configuration_A": round(gross_a, 2), "first_mismatches": [list(map(str, b)) for b in bad[:5]]}
    if bad or not sig_ok or len(got) != 196 or len(sa) != 1083 or abs(gross_ref - gross_a) > 1e-6:
        raise SystemExit(f"CONFIGURATION A DOES NOT REPRODUCE PHASE 3.6: {out}")
    return out


def signal_validation(bs: dict, ids: dict) -> tuple[dict, list[dict]]:
    """Per configuration: counts versus expectation, duplicates, timestamps, cutoff split, simultaneous signals; the signal differences between configurations (must be confined to the rules each configuration changes)."""
    out: dict = {}
    diffs: list[dict] = []
    failed_rows: list[dict] = []
    for k, b in bs.items():
        sg = b.signals
        by_s = Counter(s["strategy"] for s in sg)
        by_m = Counter(f"{s['strategy']}/{s['method']}" for s in sg)
        keys = Counter(sig_key(s) for s in sg)
        dups = {str(kk): n for kk, n in keys.items() if n > 1}
        grid = [s for s in sg if int(s["time"][-2:]) % 5 != 0]
        early = [s for s in sg if s["time"] < "09:20"]
        pre = sum(1 for s in sg if s["time"] <= CUTOFF)
        by_min: dict = defaultdict(list)
        for s in sg:
            by_min[(s["date"], s["time"])].append(s)
        simult = [(dt, sorted({f"{x['strategy']}/{x['method']}/{x['direction']}" for x in v})) for dt, v in sorted(by_min.items()) if len({x["strategy"] for x in v}) > 1]
        # same-strategy / same-direction concurrent methods are one trade (identical entry), not a conflict
        conflicts = [(dt, v) for dt, v in simult]
        strat_of = {t["trade_id"]: t["strategy"] for t in b.trades}
        failed = [c for c in b.checks if c["result"] == "FAIL"]
        for c in failed:
            why = EXPLAINED_FAILS.get((strat_of[c["trade_id"]], c["rule_id"]), {}).get(k)
            if why is None:
                raise SystemExit(f"UNEXPLAINED FAILED ENTRY CHECK in configuration {k}: {c['trade_id']} {c['rule_id']} {c['observed']}")
            failed_rows.append({"config": k, "trade_id": c["trade_id"], "strategy": strat_of[c["trade_id"]], "rule_id": c["rule_id"], "rule_name": c["rule_name"], "calculation": c["calculation"], "observed": c["observed"], "required": c["required"],
                                "explained_by": why})
        exp = X.EXPECTED_SIGNALS.get(k)
        ok = None if exp is None else (len(sg) == exp["total"] and all(by_s.get(s, 0) == exp[s] for s in P.STRATEGIES))
        out[k] = {"config_id": ids[k], "confirmed_signals": len(sg), "by_strategy": {s: by_s.get(s, 0) for s in P.STRATEGIES}, "by_method": dict(sorted(by_m.items())), "expected": exp, "matches_expected": ok,
                  "duplicate_signal_keys": len(dups), "off_5_minute_grid": len(grid), "before_09_20": len(early), "signals_at_or_before_13_00": pre, "signals_after_13_00": len(sg) - pre,
                  "same_minute_multi_strategy_groups": len(conflicts), "same_minute_groups": [[f"{d} {t}", v] for (d, t), v in conflicts[:30]],
                  "failed_entry_checks": len([r for r in failed_rows if r["config"] == k]), "failed_entry_checks_by_rule": dict(Counter(f"{r['strategy']} {r['rule_id']}" for r in failed_rows if r["config"] == k)),
                  "trades_with_failed_entry_checks": sum(1 for t in b.trades if int(t["checks_fail"] or 0) > 0), "trades_with_unresolved_checks": sum(1 for t in b.trades if int(t["checks_unresolved"] or 0) > 0)}
        if exp is not None and not ok:
            raise SystemExit(f"CONFIGURATION {k} SIGNAL TOTALS DIFFER FROM THE EXPECTED REFERENCE: {out[k]['by_strategy']} vs {exp}")
        if dups or grid or early:
            raise SystemExit(f"CONFIGURATION {k}: invalid signal timestamps or duplicates {len(dups)}/{len(grid)}/{len(early)}")
    sets = {k: {sig_key(s): s for s in b.signals} for k, b in bs.items()}
    for a, c in (("A", "B"), ("A", "C"), ("B", "C")):
        only_a = {k: v for k, v in sets[a].items() if k not in sets[c]}
        only_c = {k: v for k, v in sets[c].items() if k not in sets[a]}
        for cat, src, cfg in (("ONLY_IN_" + a, only_a, a), ("ONLY_IN_" + c, only_c, c)):
            for kk, s in src.items():
                shifted = any((x[0], x[1], x[2], x[3]) == (kk[0], kk[1], kk[2], kk[3]) for x in (only_c if cfg == a else only_a))
                diffs.append({"comparison": f"{a}_vs_{c}", "category": cat + ("_TIME_SHIFTED_COUNTERPART_EXISTS" if shifted else ""), "date": kk[0], "strategy": kk[1], "method": kk[2], "direction": kk[3], "time": kk[4],
                              "within_13_00_cutoff": kk[4] <= CUTOFF, "levels": s.get("reference_levels", "")[:300]})
    ab = [d for d in diffs if d["comparison"] == "A_vs_B"]
    ac = [d for d in diffs if d["comparison"] == "B_vs_C"]
    if any(d["strategy"] in ("ORB", "RF") for d in ab):
        raise SystemExit("UNEXPLAINED SIGNAL DIFFERENCE: A vs B differs in ORB or RF, which Phase 5.3 did not change")
    if any(not (d["strategy"] == "ORB" and d["method"] == "Gap/200DMA") or d["category"].startswith("ONLY_IN_B") for d in ac):
        raise SystemExit("UNEXPLAINED SIGNAL DIFFERENCE: B vs C differs outside the ORB Gap / 200 DMA setup")
    write_csv(OUT / "failed_entry_checks.csv", failed_rows)
    out["difference_summary"] = {f"{c}": dict(Counter((d["strategy"], d["category"].split("_TIME")[0]) for d in diffs if d["comparison"] == c)) for c in ("A_vs_B", "A_vs_C", "B_vs_C")}
    out["difference_summary"] = {c: {f"{s}:{cat}": n for (s, cat), n in v.items()} for c, v in out["difference_summary"].items()}
    return out, diffs


def trade_tables(bs: dict, ids: dict) -> tuple[list[dict], list[dict], dict]:
    """Executed trades and legs of every configuration with the new cost scenarios (the old Rs 500 columns are dropped) and per-config ledger rows."""
    trades, legs, ledgers = [], [], {}
    drop = {"rule_configuration_id", "illustrative_cost_rs", "illustrative_slippage_rs", "illustrative_net_pnl_rs", "manual_journal_row", "manual_match_class", "manual_time_label", "manual_outcome", "chart_file", "daily_journal"}
    for k, b in bs.items():
        led = {(r["date"], int(r["trade_no"])): r for r in X.ledger_rows(k, b.timelines)}
        ledgers[k] = list(led.values())
        for t in b.trades:
            lr = led[(t["date"], int(t["trade_no_of_day"]))]
            row = {"config": k, "config_id": ids[k], **{c: v for c, v in t.items() if c not in drop}, "reason_code": lr["reason_code"], "t1_booked": lr["t1_booked"], "holding_minutes": lr["holding_minutes"],
                   "forced_exit_reference_close": lr["forced_exit_reference_close"], "ambiguity_count": lr["ambiguities"], "entry_units": X.filled_units(lr)[0], "exit_units": X.filled_units(lr)[1],
                   "signal_timeframe": "5-minute", "first_eligible_execution_timestamp": t["fill_timestamp"], "simulated_entry_timestamp": t["fill_timestamp"]}
            for cid, _label, fx, sl in X.COST_SCENARIOS:
                row[f"net_pnl_rs_scenario_{cid}"] = round(X.net_pnl(lr, fx, sl), 2)
            row["net_pnl_rs_alt_70_per_fill_zero_slippage"] = round(X.net_pnl(lr, X.FIXED_COST_RS, 0.0, per_fill=True), 2)
            trades.append(row)
        for g in b.legs:
            legs.append({"config": k, "config_id": ids[k], **g})
    return trades, legs, ledgers


def perf_rows(ledgers: dict) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    strat, monthly, annual, cost = [], [], [], []
    for k, rows in ledgers.items():
        for s in P.STRATEGIES:
            sub = [r for r in rows if r["strategy"] == s]
            base = {"config": k, "strategy": s}
            for cid, label, fx, sl in X.COST_SCENARIOS:
                m = X.metrics(sub, fx, sl)
                strat.append({**base, "cost_scenario": f"{cid}: {label}", **m})
        for cid, label, fx, sl in X.COST_SCENARIOS:
            m = X.metrics(rows, fx, sl)
            cost.append({"config": k, "cost_scenario": f"{cid}: {label}", "fixed_cost_rs_per_trade": fx, "slippage_points_per_side": sl, **m})
        m = X.metrics(rows, X.FIXED_COST_RS, 0.0)
        alt = [X.net_pnl(r, X.FIXED_COST_RS, 0.0, per_fill=True) for r in X.trade_order(rows)]
        cost.append({"config": k, "cost_scenario": "ALT: Rs 70 per order fill (entry + each exit leg), zero slippage - interpretation sensitivity", "fixed_cost_rs_per_trade": "70 per fill", "slippage_points_per_side": 0.0, **{**m, "net_pnl_rs": round(sum(alt), 2),
                     "max_drawdown_rs": round(X.max_drawdown(alt), 2), "win_rate_pct": round(100 * sum(1 for v in alt if v > 0) / len(alt), 2)}})
        for label, keyfn, store in (("month", lambda r: r["date"][:7], monthly), ("calendar_year", lambda r: r["date"][:4], annual)):
            for per, sub in X.group(rows, keyfn).items():
                for s in (None, *P.STRATEGIES):
                    ss = sub if s is None else [r for r in sub if r["strategy"] == s]
                    if not ss and s is not None:
                        continue
                    g, a = X.metrics(ss, 0.0, 0.0), X.metrics(ss, X.FIXED_COST_RS, 0.0)
                    store.append({"config": k, label: per, "strategy": s or "ALL", "trades": g["trades"], "gross_points": g["gross_points_total"], "gross_pnl_rs": g["net_pnl_rs"], "net_pnl_rs_70_zero_slippage": a["net_pnl_rs"],
                                  "net_pnl_rs_70_slip_0_25": X.metrics(ss, X.FIXED_COST_RS, 0.25)["net_pnl_rs"], "net_pnl_rs_70_slip_0_5": X.metrics(ss, X.FIXED_COST_RS, 0.5)["net_pnl_rs"],
                                  "net_pnl_rs_70_slip_1_0": X.metrics(ss, X.FIXED_COST_RS, 1.0)["net_pnl_rs"], "win_rate_pct": g["win_rate_pct"], "profit_factor_gross": g["profit_factor"], "max_drawdown_rs_gross": g["max_drawdown_rs"]})
    return strat, monthly, annual, cost


def strategy_extra(bs: dict, ledgers: dict) -> list[dict]:
    """Raw / first-valid / executed counts per configuration and strategy (the signal funnel)."""
    out = []
    for k, b in bs.items():
        for s in P.STRATEGIES:
            sg = [x for x in b.signals if x["strategy"] == s]
            ex = [r for r in ledgers[k] if r["strategy"] == s]
            first_valid = len({x["date"] for x in sg if x["time"] <= CUTOFF})
            out.append({"config": k, "strategy": s, "raw_confirmed_signals": len(sg), "signals_at_or_before_13_00": sum(1 for x in sg if x["time"] <= CUTOFF), "sessions_with_a_signal_before_the_cutoff": first_valid,
                        "executed_trades": len(ex), "first_trades": sum(1 for r in ex if int(r["trade_no"]) == 1), "second_trades": sum(1 for r in ex if int(r["trade_no"]) == 2),
                        "ignored_position_active": sum(1 for x in b.ignored if x["strategy"] == s), "rejected_by_controller": sum(1 for x in b.rejected if x["strategy"] == s and x["category"].startswith("CONTROLLER"))})
    return out


def comparison_rows(bs: dict, ledgers: dict) -> list[dict]:
    """Trade-by-trade differences between configurations per session, attributed to the earliest differing signal or portfolio selection."""
    out = []
    seq = {k: defaultdict(list) for k in X.KEYS}
    for k in X.KEYS:
        for r in X.trade_order(ledgers[k]):
            seq[k][r["date"]].append(r)
    sigs = {k: {sig_key(s): s for s in bs[k].signals} for k in X.KEYS}
    days = sorted({d for k in X.KEYS for d in seq[k]})
    for a, c in (("A", "B"), ("A", "C"), ("B", "C")):
        for d in days:
            ta, tc = seq[a].get(d, []), seq[c].get(d, [])
            sa = [(r["strategy"], r["method"], r["direction"], r["entry_time"], r["outcome"], round(float(r["gross_pnl_rs"]), 2)) for r in ta]
            sc_ = [(r["strategy"], r["method"], r["direction"], r["entry_time"], r["outcome"], round(float(r["gross_pnl_rs"]), 2)) for r in tc]
            if sa == sc_:
                continue
            da = {k: v for k, v in sigs[a].items() if k[0] == d}
            dc = {k: v for k, v in sigs[c].items() if k[0] == d}
            diff = sorted([(k[4], k[1], k[2], k[3], "only_" + a) for k in da if k not in dc] + [(k[4], k[1], k[2], k[3], "only_" + c) for k in dc if k not in da])
            first = diff[0] if diff else None
            if not ta or not tc:
                kind = "TRADED_ONLY_IN_" + (a if ta else c)
            elif (ta[0]["strategy"], ta[0]["entry_time"]) != (tc[0]["strategy"], tc[0]["entry_time"]):
                kind = "FIRST_TRADE_CHANGED"
            elif len(ta) != len(tc):
                kind = "SECOND_TRADE_DIFFERS"
            else:
                kind = "SAME_ENTRIES_DIFFERENT_EXIT_OR_PNL"
            out.append({"comparison": f"{a}_vs_{c}", "date": d, "kind": kind, f"trades_{a}": " | ".join(f"{x[0]}/{x[1]} {x[2]} {x[3]} {x[4]} {x[5]}" for x in sa) or "none",
                        f"trades_{c}": " | ".join(f"{x[0]}/{x[1]} {x[2]} {x[3]} {x[4]} {x[5]}" for x in sc_) or "none", f"gross_pnl_rs_{a}": round(sum(x[5] for x in sa), 2), f"gross_pnl_rs_{c}": round(sum(x[5] for x in sc_), 2),
                        "pnl_difference_rs": round(sum(x[5] for x in sc_) - sum(x[5] for x in sa), 2), "earliest_differing_signal": "" if not first else f"{first[0]} {first[1]}/{first[2]} {first[3]} ({first[4]})",
                        "differing_signals_that_day": len(diff)})
    return out


def windows_run(sc, ids: dict) -> dict:
    """The robustness window 2022-09-01..2025-08-31 (5paisa one-minute data) for A, B, C through the frozen controller; each calendar year separately. A is checked against the Phase 4 reference."""
    spec = P4.SPECS["B"]
    minutes = D4.load_processed_minutes(spec.minute_source)
    daily = D4.load_processed_daily(spec.daily_source)
    from nifty_trading.data.market_calendar import load_market_calendar
    cal = load_market_calendar(D4.CAL_DIR / "phase4_calendar_derived.json")
    wd = D4.build_window_data(spec.window_id, minutes, daily, cal, spec.start, spec.end, spec.minute_source, spec.daily_source)
    res: dict = {"window": spec.label, "status": spec.status, "sessions_evaluated": len(wd.ctxs), "minute_source": spec.minute_source}
    rows_all = {}
    for k in X.KEYS:
        tls = X.run_timelines_cfg(k, sc, wd.ctxs, wd.bars)
        led = X.ledger_rows(k, tls)
        rows_all[k] = led
        res[k] = {"signals": X.signal_counts(tls), "sessions": X.sessions_summary(tls), "gross": X.metrics(led, 0.0, 0.0), "net_70": X.metrics(led, X.FIXED_COST_RS, 0.0), "net_70_slip_1": X.metrics(led, X.FIXED_COST_RS, 1.0),
                  "by_year": {y: {"gross": X.metrics(sub, 0.0, 0.0), "net_70": X.metrics(sub, X.FIXED_COST_RS, 0.0)} for y, sub in X.group(led, lambda r: r["date"][:4]).items()},
                  "by_strategy": {s: X.metrics([r for r in led if r["strategy"] == s], 0.0, 0.0) for s in P.STRATEGIES}}
    ref = list(csv.DictReader(open(ROOT / "reports" / "phase4" / "windows" / "B" / "all_trades_detailed.csv", newline="")))
    a = X.trade_order(rows_all["A"])
    same = len(ref) == len(a) and abs(sum(fnum(r["gross_pnl_rs"]) for r in ref) - sum(float(r["gross_pnl_rs"]) for r in a)) < 1e-6
    res["A_reproduces_phase4_window_B"] = {"phase4_trades": len(ref), "configuration_A_trades": len(a), "gross_equal": same}
    if not same:
        raise SystemExit(f"CONFIGURATION A DOES NOT REPRODUCE THE PHASE 4 WINDOW B: {res['A_reproduces_phase4_window_B']}")
    flat = []
    for k in X.KEYS:
        for r in rows_all[k]:
            flat.append({"config": k, "config_id": ids[k], **{c: r[c] for c in ("date", "trade_no", "strategy", "method", "direction", "signal_time", "entry_time", "entry_price", "outcome", "gross_points_weighted", "gross_pnl_rs", "qty_total", "qty_leg1", "qty_leg2",
                                                                              "leg1_exit_price", "leg2_exit_price")}, "net_pnl_rs_70": round(X.net_pnl(r, X.FIXED_COST_RS, 0.0), 2)})
    write_csv(OUT / "multi_year_trades.csv", flat)
    yr = []
    for k in X.KEYS:
        for y, v in res[k]["by_year"].items():
            for s in ("gross", "net_70"):
                yr.append({"config": k, "calendar_year": y, "cost_scenario": s, **v[s]})
    write_csv(OUT / "multi_year_by_year.csv", yr)
    return res


def main() -> int:  # noqa: C901
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--skip-robustness", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "daily").mkdir(exist_ok=True)
    (OUT / "charts").mkdir(exist_ok=True)
    state: dict = {}
    ident = verify_frozen_identity()
    ids, extra_hashes = config_ids(ident)
    state["frozen_identity"] = ident
    sc = P.combined_scenario("BODY_BASED_PHASE36")
    bs = build_bundles()
    state["reproduction"] = check_reproduction(bs)
    sv, diffs = signal_validation(bs, ids)
    state["signal_validation"] = sv
    write_csv(OUT / "signal_differences.csv", diffs)
    write_csv(OUT / "all_confirmed_signals.csv", [{"config": k, "date": s["date"], "time": s["time"], "candle_start": s["candle_start"], "strategy": s["strategy"], "method": s["method"], "direction": s["direction"], "reference_close": s["reference_close"],
                                                    "within_13_00_cutoff": s["within_13_00_cutoff"], "fully_valid_for_execution": s["fully_valid_for_execution"], "controller_event": s["controller_event"], "controller_reason": s["controller_reason"], "blocked_by": s["blocked_by"],
                                                    "trade_id": s["trade_id"], "competing_signals_same_minute": s["competing_signals_same_minute"]} for k, b in bs.items() for s in b.signals])
    trades, legs, ledgers = trade_tables(bs, ids)
    write_csv(OUT / "all_executed_trades.csv", trades)
    write_csv(OUT / "all_trade_legs.csv", legs)
    strat, monthly, annual, cost = perf_rows(ledgers)
    funnel = strategy_extra(bs, ledgers)
    write_csv(OUT / "strategy_performance.csv", strat)
    write_csv(OUT / "strategy_signal_funnel.csv", funnel)
    write_csv(OUT / "monthly_performance.csv", monthly)
    write_csv(OUT / "annual_performance.csv", annual)
    write_csv(OUT / "cost_sensitivity.csv", cost)
    amb = [{"config": r["config"], "trade_id": r["trade_id"], "date": r["date"], "strategy": r["strategy"], "outcome": r["outcome"], "gross_pnl_rs": r["gross_pnl_rs"], "ambiguity_notes": r["ambiguity_notes"]} for k in X.KEYS for r in ledgers[k] if int(r["ambiguities"]) > 0]
    write_csv(OUT / "intrabar_ambiguities.csv", amb)
    cmp_rows = comparison_rows(bs, ledgers)
    write_csv(OUT / "trade_differences_between_configurations.csv", cmp_rows)
    state["summary"] = {k: {"signals": X.signal_counts(bs[k].timelines), "sessions": X.sessions_summary(bs[k].timelines), **{sc_id: X.metrics(ledgers[k], fx, sl) for sc_id, _l, fx, sl in X.COST_SCENARIOS}} for k in X.KEYS}
    state["ambiguous_trades"] = {k: sum(1 for r in amb if r["config"] == k) for k in X.KEYS}
    state["comparison_kinds"] = {c: dict(Counter(r["kind"] for r in cmp_rows if r["comparison"] == c)) for c in ("A_vs_B", "A_vs_C", "B_vs_C")}
    state["unresolved_exits"] = {k: sum(1 for r in ledgers[k] if r["outcome"] in ("INCOMPLETE_EOD", "NOT_EVALUABLE")) for k in X.KEYS}
    # ------------------------------------------------------------------ manifest
    fr = json.loads(FREEZE.read_text())
    manifest = {"phase": "5.5", "synthetic_pnl_only": True, "configurations": {k: {"id": ids[k], "title": X.TITLES[k], "engines": [type(e).__name__ for e in X.engines_for(k, sc.proposals, sc.trade, sc.pdr_engine, sc.pdr_revision)], "provisional_assumptions": PROVISIONAL[k]} for k in X.KEYS},
                "frozen_identity_verification": ident, "frozen_active_file_hashes": fr["active_file_hashes"], "phase5_candidate_file_hashes": extra_hashes, "parameters_common_to_all": fr["parameters"],
                "cost_model": {"fixed_cost_rs_per_trade": X.FIXED_COST_RS, "status": "owner's indicative estimate (brokerage ~Rs 30 + other charges ~Rs 40); NOT a verified broker bill; coverage of entry / partial exits UNCONFIRMED; applied once per executed trade",
                               "slippage_points_per_side": list(X.SLIPPAGE_POINTS), "slippage_application": "adverse points on every unit of every actual fill: entry once (entry units), each exited leg once (its own units); no unit is charged twice; legs without a fillable exit have no exit fill",
                               "scenarios": [{"id": i, "label": lab, "fixed_rs": fx, "slip_points_per_side": sl} for i, lab, fx, sl in X.COST_SCENARIOS], "old_fixed_500_assumption": "NOT USED"},
                "position": {"lots": 6, "units_per_lot": 65, "total_units": 390, "legs": "3 + 3 lots (195 + 195 units)", "note": "synthetic comparison multiplier: the index is not tradable and historical lot sizes differ"},
                "exit_rules": {"stops": {s: sc.trade.stop_points(s) for s in P.STRATEGIES}, "target_1_points": sc.trade.t1_points, "targets_2": {s: sc.trade.t2_points(s) for s in P.STRATEGIES}, "post_t1_stop": "entry -/+ 6 points; no trailing",
                               "forced_exit": "open of the 15:14 one-minute bar (provisional implementer assumption; before 15:15 IST; never a closing-auction fill)", "intrabar": "stop before target inside a 1-minute bar (conservative, not a source rule); stops fill at the worse of the level and the bar open"},
                "controller": asdict(DayRules()) | {"tie_break": None}, "entry_cutoff_ist": CUTOFF, "forced_exit_limit": str(FORCED_EXIT_LIMIT),
                "data": {"primary_window": "2025-09-01..2026-08-31 (Phase 1 5paisa one-minute NIFTY 50)", "provenance": bs["A"].provenance, "robustness_window": "2022-09-01..2025-08-31 (Phase 4 5paisa window B)"},
                "environment": {"python": platform.python_version(), "platform": platform.platform(), "packages": {p: importlib.metadata.version(p) for p in ("pandas", "numpy", "openpyxl", "pytest", "ruff")}},
                "journal_workbook_sha256": sha(ROOT / "docs" / "trading journal" / "Trading_Journal_Sep2025_Aug2026 REPORT.xlsx"), "reproduce": "cd /Users/syedaskari/algo/nifty-options && source .venv/bin/activate && python scripts/phase55_run.py"}
    (OUT / "configuration_manifest.json").write_text(json.dumps(manifest, indent=2, default=str))
    # ------------------------------------------------------------------ daily reports and charts
    n_daily = write_daily(bs, ledgers, ids)
    state["daily_reports"] = n_daily
    # ------------------------------------------------------------------ robustness window
    if not a.skip_robustness:
        state["robustness"] = windows_run(sc, ids)
    (OUT / "phase55_state.json").write_text(json.dumps(state, indent=1, default=str))
    write_workbook(trades, strat, monthly, annual, cost, amb, cmp_rows, diffs, funnel, state)
    print(json.dumps({"reproduction": state["reproduction"], "summary": {k: {"trades": v["A"]["trades"], "gross_rs": v["A"]["net_pnl_rs"], "net70_rs": v["B"]["net_pnl_rs"]} for k, v in state["summary"].items()}}, indent=1, default=str))
    return 0


def write_daily(bs: dict, ledgers: dict, ids: dict) -> dict:
    """One report per trading day on which any configuration traded (each configuration's signals, controller decisions, entries, exits and P&L); charts for every trade that is not identical in configuration A."""
    by = {k: defaultdict(list) for k in X.KEYS}
    for k in X.KEYS:
        for r in X.trade_order(ledgers[k]):
            by[k][r["date"]].append(r)
    days = sorted({d for k in X.KEYS for d in by[k]})
    tid = {k: {(t["date"], int(t["trade_no_of_day"])): t for t in bs[k].trades} for k in X.KEYS}
    a_sig = {(r["date"], r["trade_no"]): (r["strategy"], r["method"], r["direction"], r["entry_time"], r["outcome"], r["gross_pnl_rs"]) for r in ledgers["A"]}
    n_ch = 0
    for d in days:
        md = [f"# {d} - five-strategy backtest, configurations A / B / C", "", "> SYNTHETIC index-point P&L (390 units); costs are illustrative (Rs 70 per trade + slippage scenarios); no real option P&L.", ""]
        for k in X.KEYS:
            b = bs[k]
            md += [f"## Configuration {k}: {X.TITLES[k]}", ""]
            sg = [s for s in b.signals if s["date"] == d]
            md += ["Confirmed signals: " + ("; ".join(f"{s['time']} {s['strategy']}/{s['method']} {s['direction']} [{s['controller_event'] or 'n/a'}: {s['controller_reason'] or ''}]" for s in sg) or "none"), ""]
            rows = by[k].get(d, [])
            if not rows:
                md += ["No trade this day.", ""]
                continue
            md += ["| trade | strategy / method | dir | signal -> fill | entry | stop / T1 / T2 | leg 1 exit | leg 2 exit | outcome | gross Rs | net Rs (70, 0 slip) | net Rs (70, 1.0 slip) | ambiguities |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
            for r in rows:
                md.append(f"| {r['trade_no']} | {r['strategy']}/{r['method']} | {r['direction']} | {r['signal_time']} -> {r['entry_time']} | {r['entry_price']} | {r['stop_level']} / {r['t1_level']} / {r['t2_level']} | {r['leg1_exit_time']} @ {r['leg1_exit_price']} | "
                          f"{r['leg2_exit_time']} @ {r['leg2_exit_price']} | {r['outcome']} | {float(r['gross_pnl_rs']):,.0f} | {X.net_pnl(r, X.FIXED_COST_RS, 0.0):,.0f} | {X.net_pnl(r, X.FIXED_COST_RS, 1.0):,.0f} | {r['ambiguities']} |")
                t = tid[k][(d, int(r["trade_no"]))]
                md += ["", f"* Setup: {t['setup_explanation']}", f"* Selection: {t['selection_explanation']}", f"* Exit: {t['exit_narrative']}"]
                changed = k != "A" and a_sig.get((d, r["trade_no"])) != (r["strategy"], r["method"], r["direction"], r["entry_time"], r["outcome"], r["gross_pnl_rs"])
                if changed:
                    (OUT / "charts" / f"{k}_{t['trade_id']}.svg").write_text(RN.trade_chart(b, t["trade_id"], defaultdict(list)))
                    md.append(f"* Chart (this trade differs from configuration A): ../charts/{k}_{t['trade_id']}.svg")
                    n_ch += 1
                md.append("")
        (OUT / "daily" / f"{d}.md").write_text("\n".join(md) + "\n")
    return {"daily_reports": len(days), "charts_for_changed_trades": n_ch}


def write_workbook(trades, strat, monthly, annual, cost, amb, cmp_rows, diffs, funnel, state) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    wb = Workbook()
    ws = wb.active
    ws.title = "README"
    for n, line in enumerate(["Phase 5.5 - complete five-strategy backtest, configurations A / B / C (SYNTHETIC index-point P&L x 390 units; not real option P&L)",
                              "A = frozen Phase 3.6 (FROZEN-PHASE36-42cea2600bd4); B = Phase 5.3 author-corrected (provisional conventions); C = B + ORB gap crossing (provisional research scenario). Costs: Rs 70 per trade (owner's indicative estimate, not a broker bill) + slippage scenarios; the old Rs 500 fee is not used.",
                              "Sheets: Executed Trades, Strategy Performance, Signal Funnel, Monthly, Annual, Cost Sensitivity, Intrabar Ambiguities, Config Differences, Signal Differences."], 1):
        ws.cell(row=n, column=1, value=line)
    ws["A1"].font = Font(bold=True, size=13)
    ws.column_dimensions["A"].width = 170

    def add(name, rows_):
        w = wb.create_sheet(name[:31])
        if not rows_:
            w["A1"] = "(no rows)"
            return
        cols = []
        for r in rows_:
            for k in r:
                if k not in cols:
                    cols.append(k)
        w.append(cols)
        for r in rows_:
            w.append([("" if r.get(c) is None else (str(r[c]) if isinstance(r[c], (dict, list)) else r[c])) for c in cols])
        for cell in w[1]:
            cell.fill, cell.font = PatternFill("solid", fgColor="1F3864"), Font(bold=True, color="FFFFFF")
        w.freeze_panes = "B2"
    short = [{k: v for k, v in t.items() if k not in ("setup_explanation", "selection_explanation", "exit_narrative", "checks_pass", "checks_fail", "checks_unresolved", "checks_not_applicable", "unresolved_items")} for t in trades]
    add("Executed Trades", short)
    add("Strategy Performance", strat)
    add("Signal Funnel", funnel)
    add("Monthly", monthly)
    add("Annual", annual)
    add("Cost Sensitivity", cost)
    add("Intrabar Ambiguities", amb)
    add("Config Differences", cmp_rows)
    add("Signal Differences", diffs)
    wb.save(OUT / "Combined_Strategy_Backtest.xlsx")


if __name__ == "__main__":
    raise SystemExit(main())
