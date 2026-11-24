"""Phase 6.5 continuation, stage 1: full portfolio backtests of ten declared configurations on both windows through the FROZEN controller / exit policy (synthetic index P&L), win rates, costs, trade-set attribution
(DIRECT vs PORTFOLIO effect), day-by-day comparison and the manual-journal reconciliation. Each configuration changes the declared rule dimension(s) relative to BASE (= configuration C of Phase 6.2): S60 / S70 / SD one (the body gate), PDR_D one (second eligible confirmation), PDS_FROZEN / PDS_SECOND one (the PDS quality test / confirmation), but PDR_B1 / B2 / C TWO (green-only confirmation, which also drops the lower-price-rejection route, together with the ceiling / retest-candle change in the owner's definitions).
Net figures use Rs 70 per trade (the C70_TRADE scenario) unless a column says otherwise; gross figures are labelled gross. `--reuse` rebuilds the tables from the cached ledgers (runs65b.pkl) without re-simulating.
Configurations: BASE; S60 / S70 / SD (candle-strength variants B / C / D of the checkpoint); PDR_B1, PDR_B2, PDR_C, PDR_D; PDS_FROZEN (the frozen numeric-threshold PDS); PDS_SECOND. PDS first-eligible == BASE."""

from __future__ import annotations

import json
import pickle
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd  # noqa: E402
import phase60_common as P60  # noqa: E402
from phase61_common import JOURNAL, SCRATCH, window_data, write_csv  # noqa: E402

from nifty_trading.research import phase3 as P  # noqa: E402
from nifty_trading.research import phase31 as P31  # noqa: E402
from nifty_trading.research import phase55 as X  # noqa: E402
from nifty_trading.research import phase56 as M  # noqa: E402
from nifty_trading.research import phase62 as X2  # noqa: E402
from nifty_trading.research.orb_v2 import config as OC  # noqa: E402
from nifty_trading.strategies import orb_v2_adapter as OA  # noqa: E402
from nifty_trading.strategies.first_eligible_phase53 import (  # noqa: E402
    PDRFirstEligibleStrategy,
    PDSFirstEligibleStrategy,
)
from nifty_trading.strategies.pdr_variants import PDRVariantStrategy  # noqa: E402
from nifty_trading.strategies.pds import PDSStrategy  # noqa: E402
from nifty_trading.strategies.pds_variants import PDSSecondConfirmationStrategy  # noqa: E402
from nifty_trading.strategies.strength_gate import StrengthGateEngine  # noqa: E402

R65 = Path(__file__).resolve().parents[1] / "reports" / "phase6" / "phase65_author_feedback"
SC = P.combined_scenario("BODY_BASED_PHASE36")
CONFIGS = {"BASE": "Baseline (Phase 6.2 configuration C: IRF V2 + ORB V2-A + PDR/PDS first-eligible + RF)", "S60": "Candle-strength variant: 60% body (checkpoint variant B)", "S70": "Candle-strength variant: 70% body (checkpoint variant C)",
           "SD": "Candle-strength variant: pattern-aware 60% (checkpoint variant D)", "PDR_B1": "PDR-B1: first green candle after the retest, no ceiling requirement", "PDR_B2": "PDR-B2: first green candle, retest candle may confirm, no ceiling requirement",
           "PDR_C": "PDR-C: first green candle closing above the ceiling, retest candle may confirm", "PDR_D": "PDR-D: second eligible confirmation", "PDS_FROZEN": "PDS: frozen numeric-threshold engine (source-consistent reference)", "PDS_SECOND": "PDS: second eligible bearish confirmation (Methods 1/2 only)"}
COSTS = (("GROSS", 0.0, 0.0, False), ("C70_TRADE", 70.0, 0.0, False), ("C70_FILL", 70.0, 0.0, True), ("C70_S025", 70.0, 0.25, False), ("C70_S05", 70.0, 0.5, False), ("C70_S1", 70.0, 1.0, False))
STRATS = P.STRATEGIES


def build_engines(key, orb):
    base = X2.engines_for("C", SC.proposals, SC.trade, SC.pdr_engine, SC.pdr_revision, orb)
    if key == "BASE":
        return base
    if key in ("S60", "S70", "SD"):
        v = {"S60": "B", "S70": "C", "SD": "D"}[key]
        return [StrengthGateEngine(e, v) for e in base]
    out = []
    for e in base:
        if key.startswith("PDR_") and isinstance(e, PDRFirstEligibleStrategy):
            e = PDRVariantStrategy(key.split("_")[1], proposals=SC.proposals, trade=SC.trade, revision=e.rev)
        elif key == "PDS_FROZEN" and isinstance(e, PDSFirstEligibleStrategy):
            e = PDSStrategy(proposals=SC.proposals, trade=SC.trade)
        elif key == "PDS_SECOND" and isinstance(e, PDSFirstEligibleStrategy):
            e = PDSSecondConfirmationStrategy(proposals=SC.proposals, trade=SC.trade)
        out.append(e)
    return out


def metrics(rows, fixed=70.0, slip=0.0, per_fill=False):                  # default = the Rs 70 per trade scenario; gross_* keys are always gross
    rows = X.trade_order(rows)
    n = len(rows)
    g = [float(r["gross_pnl_rs"]) for r in rows]
    net = [X.net_pnl(r, fixed, slip, per_fill) for r in rows]
    wins, loss, be = sum(1 for x in g if x > 0), sum(1 for x in g if x < 0), sum(1 for x in g if x == 0)
    nw = sum(1 for x in net if x > 0)
    pf = X.profit_factor(net)
    oc = Counter(r["outcome"] for r in rows)
    wsum = [x for x in net if x > 0]
    lsum = [x for x in net if x < 0]
    return {"trades": n, "winners_gross": wins, "losers_gross": loss, "breakeven_gross": be, "gross_win_rate_pct": round(100 * wins / n, 2) if n else None, "winners_net": nw, "net_win_rate_pct": round(100 * nw / n, 2) if n else None,
            "profit_factor": None if pf is None else ("inf" if pf == float("inf") else round(pf, 3)), "avg_win_rs": round(sum(wsum) / len(wsum), 0) if wsum else None, "avg_loss_rs": round(sum(lsum) / len(lsum), 0) if lsum else None,
            "gross_points": round(sum(float(r["gross_points_weighted"]) for r in rows), 2), "gross_rs": round(sum(g), 0), "net_rs": round(sum(net), 0), "max_drawdown_rs": round(X.max_drawdown(net), 0),
            "t1_hit": sum(1 for r in rows if str(r.get("t1_booked")) == "True"), "t2_hit": oc.get("TARGET", 0), "initial_stop": oc.get("INITIAL_FULL_STOP", 0), "post_t1_stop": oc.get("T1_THEN_BUFFER_STOP", 0), "forced_exit": oc.get("FORCED_EXIT", 0),
            "t1_pct": round(100 * sum(1 for r in rows if str(r.get("t1_booked")) == "True") / n, 1) if n else None, "t2_pct": round(100 * oc.get("TARGET", 0) / n, 1) if n else None, "initial_stop_pct": round(100 * oc.get("INITIAL_FULL_STOP", 0) / n, 1) if n else None,
            "post_t1_stop_pct": round(100 * oc.get("T1_THEN_BUFFER_STOP", 0) / n, 1) if n else None, "forced_exit_pct": round(100 * oc.get("FORCED_EXIT", 0) / n, 1) if n else None}


def key_of(r):
    return (r["date"], r["strategy"], r["entry_time"], r["direction"])


def main() -> int:  # noqa: C901
    saved = pd.read_csv(R65 / "candle_strength_variant_ledgers.csv", dtype={"entry_time": str})
    pkl = SCRATCH / "runs65b.pkl"
    reuse = "--reuse" in sys.argv and pkl.exists()
    runs: dict = pickle.loads(pkl.read_bytes()) if reuse else {}
    for w in (() if reuse else ("A", "B")):
        ctxs, infos, bars, cal, label = window_data(w)
        inp = P60.get_window(w, "5P")
        orb = OA.ORBV2Strategy(OA.build_decisions(inp, OC.A), OC.A, proposals=SC.proposals, trade=SC.trade)
        runs[w] = {}
        for k in CONFIGS:
            engines = build_engines(k, orb)
            saved_fn = (P31.make_engines, P.make_engines)
            P31.make_engines = lambda p, t, pe="LEGACY", pr=None, _e=engines: _e
            try:
                tls = P31.run_timelines(SC, ctxs, bars)
            finally:
                P31.make_engines, P.make_engines = saved_fn
            led = X.ledger_rows(k, tls)
            sigs, pds_pdr = [], []
            for d, tl in tls.items():
                used = {id(tr.signal): tr for tr in tl.result.trades}
                for r in tl.records:
                    if r.signal_status != "CONFIRMED":
                        continue
                    row = {"date": str(d), "time": f"{r.signal_timestamp:%H:%M}", "candle_start": f"{r.signal_candle_start:%H:%M}", "strategy": r.strategy, "method": r.method, "direction": r.direction, "ref_close": r.signal_candle_close, "executed": id(r) in used}
                    sigs.append(row)
                    if r.strategy in ("PDR", "PDS"):
                        lv = r.reference_levels
                        pds_pdr.append({**row, "interaction_start": lv.get("interaction_candle_start") or lv.get("first_red_candle_start") and f"{lv['first_red_candle_start']:%H:%M}" or "", "zone_floor": lv.get("zone_floor") or lv.get("zone_low"), "zone_ceiling": lv.get("zone_ceiling") or lv.get("zone_high"),
                                         "patterns": "+".join(lv.get("patterns_passed") or []), "green_is_retest": lv.get("green_candle_is_retest_candle"), "first_eligible_start": lv.get("first_eligible_candle_start", ""), "second_eligible_start": lv.get("second_eligible_candle_start", ""),
                                         "zone_flags": ";".join(map(str, lv.get("zone_flags") or []))})
            days = {str(d): {"final_state": tl.result.final_state.value, "n_trades": len(tl.result.trades)} for d, tl in tls.items()}
            runs[w][k] = {"ledger": led, "signals": sigs, "pdr_pds": pds_pdr, "days": days, "gate_log": [x for e in engines for x in getattr(e, "log", [])], "records_pdr": None}
            print(w, k, len(led), round(sum(float(r["gross_pnl_rs"]) for r in led)), flush=True)
    # ---------------------------------------------------------------- validation: the strength configurations reproduce the checkpoint's saved ledgers
    val = {}
    for k, v in (("BASE", "A"), ("S60", "B"), ("S70", "C"), ("SD", "D")):
        for w in ("A", "B"):
            sv = saved[(saved.window == w) & (saved.variant == v)]
            cur = runs[w][k]["ledger"]
            sset = {(r.date, r.strategy, r.entry_time, r.direction, round(float(r.gross_pnl_rs), 2)) for r in sv.itertuples()}
            cset = {(r["date"], r["strategy"], r["entry_time"], r["direction"], round(float(r["gross_pnl_rs"]), 2)) for r in cur}
            val[f"{k}|{w}"] = {"saved_trades": len(sset), "rerun_trades": len(cset), "identical": sset == cset}
    if not reuse:
        pkl.write_bytes(pickle.dumps(runs, protocol=4))
    print("validation", val, flush=True)
    # ---------------------------------------------------------------- tables
    full, wr, monthly, annual, cost, sigcmp, tradecmp, attrib, daybyday = [], [], [], [], [], [], [], [], []
    for w in ("A", "B"):
        base_led = {key_of(r): r for r in runs[w]["BASE"]["ledger"]}
        base_sig = {(s["date"], s["time"], s["strategy"], s["method"], s["direction"]): s for s in runs[w]["BASE"]["signals"]}
        for k in CONFIGS:
            led = runs[w][k]["ledger"]
            m = metrics(led)
            sg = runs[w][k]["signals"]
            full.append({"window": w, "config": k, "label": CONFIGS[k], "confirmed_signals": len(sg), "net_basis": "net_rs / winners_net / net_win_rate_pct / profit_factor / avg_win_rs / avg_loss_rs / max_drawdown_rs are net of Rs 70 per trade; gross_* are gross", **m, **{f"net_rs_{c}": round(sum(X.net_pnl(r, fx, sl, pf) for r in led), 0) for c, fx, sl, pf in COSTS}})
            for s in STRATS:
                sel = [r for r in led if r["strategy"] == s]
                ms = metrics(sel)
                wr.append({"window": w, "config": k, "strategy": s, "confirmed_signals": sum(1 for x in sg if x["strategy"] == s), "executed_trades": ms["trades"], "winners": ms["winners_gross"], "losers": ms["losers_gross"], "breakeven": ms["breakeven_gross"],
                           "gross_win_rate_pct": ms["gross_win_rate_pct"], "net_win_rate_pct_70_per_trade": ms["net_win_rate_pct"], "profit_factor": ms["profit_factor"], "avg_win_rs": ms["avg_win_rs"], "avg_loss_rs": ms["avg_loss_rs"], "gross_points": ms["gross_points"],
                           "gross_rs": ms["gross_rs"], "net_rs_70_per_trade": ms["net_rs"], "net_basis": "profit_factor / avg_win_rs / avg_loss_rs are net of Rs 70 per trade", "t1_pct": ms["t1_pct"], "t2_pct": ms["t2_pct"], "initial_stop_pct": ms["initial_stop_pct"], "post_t1_stop_pct": ms["post_t1_stop_pct"], "forced_exit_pct": ms["forced_exit_pct"], "label": "contribution inside the combined portfolio"})
            for lab, fn, tgt in (("month", lambda r: r["date"][:7], monthly), ("calendar_year", lambda r: r["date"][:4], annual)):
                for kk, sel in X.group(led, fn).items():
                    ms = metrics(sel)
                    tgt.append({"window": w, "config": k, lab: kk, "trades": ms["trades"], "winners": ms["winners_gross"], "losers": ms["losers_gross"], "gross_win_rate_pct": ms["gross_win_rate_pct"], "gross_points": ms["gross_points"], "gross_rs": ms["gross_rs"], "net_rs_70": ms["net_rs"]})
            for c, fx, sl, pf in COSTS:
                mm = metrics(led, fx, sl, pf)
                cost.append({"window": w, "config": k, "scenario": c, "fixed_rs": fx, "slippage_pts_per_side": sl, "per_fill": pf, "trades": mm["trades"], "winners_net": mm["winners_net"], "net_win_rate_pct": mm["net_win_rate_pct"], "net_rs": mm["net_rs"], "profit_factor": mm["profit_factor"], "max_drawdown_rs": mm["max_drawdown_rs"]})
            vs = {(s["date"], s["time"], s["strategy"], s["method"], s["direction"]): s for s in sg}
            for s in STRATS:
                b_, v_ = {x for x in base_sig if x[2] == s}, {x for x in vs if x[2] == s}
                sigcmp.append({"window": w, "config": k, "strategy": s, "baseline_signals": len(b_), "config_signals": len(v_), "same": len(b_ & v_), "removed": len(b_ - v_), "added": len(v_ - b_),
                               "same_time_different_candle_or_method": len({(x[0], x[1], x[2]) for x in b_} & {(x[0], x[1], x[2]) for x in v_}) - len(b_ & v_)})
            if k == "BASE":
                continue
            cur = {key_of(r): r for r in led}
            kept = [x for x in cur if x in base_led]
            rem = sorted(set(base_led) - set(cur))
            add = sorted(set(cur) - set(base_led))
            for t, tag in ((x, "REMOVED_BASELINE_TRADE") for x in rem):
                r = base_led[t]
                sk = (r["date"], r["signal_time"], r["strategy"], r["method"], r["direction"])
                direct = sk not in vs
                attrib.append({"window": w, "config": k, "kind": tag, "date": t[0], "strategy": t[1], "entry_time": t[2], "direction": t[3], "outcome": r["outcome"], "gross_pnl_rs": r["gross_pnl_rs"], "effect": "DIRECT (the rule rejected or changed this signal)" if direct else "PORTFOLIO (the signal still exists but the controller selected something else)"})
            for t in add:
                r = cur[t]
                sk = (r["date"], r["signal_time"], r["strategy"], r["method"], r["direction"])
                direct = sk not in base_sig
                attrib.append({"window": w, "config": k, "kind": "ADDED_TRADE", "date": t[0], "strategy": t[1], "entry_time": t[2], "direction": t[3], "outcome": r["outcome"], "gross_pnl_rs": r["gross_pnl_rs"], "effect": "DIRECT (the rule created this signal)" if direct else "PORTFOLIO (an existing signal became selectable after an earlier trade was removed or changed)"})
            earlier = later = outcome_chg = second_chg = strat_chg = 0
            bd, cd = defaultdict(list), defaultdict(list)
            for r in base_led.values():
                bd[r["date"]].append(r)
            for r in cur.values():
                cd[r["date"]].append(r)
            for d in set(bd) | set(cd):
                b_, c_ = sorted(bd.get(d, []), key=lambda r: r["entry_time"]), sorted(cd.get(d, []), key=lambda r: r["entry_time"])
                if len(b_) != len(c_):
                    second_chg += 1
                for i in range(min(len(b_), len(c_))):
                    if b_[i]["strategy"] != c_[i]["strategy"]:
                        strat_chg += 1
                    elif b_[i]["entry_time"] != c_[i]["entry_time"]:
                        earlier += c_[i]["entry_time"] < b_[i]["entry_time"]
                        later += c_[i]["entry_time"] > b_[i]["entry_time"]
                    elif b_[i]["outcome"] != c_[i]["outcome"]:
                        outcome_chg += 1
            dir_rem = sum(1 for x in attrib if x["window"] == w and x["config"] == k and x["kind"] == "REMOVED_BASELINE_TRADE" and x["effect"].startswith("DIRECT"))
            dir_add = sum(1 for x in attrib if x["window"] == w and x["config"] == k and x["kind"] == "ADDED_TRADE" and x["effect"].startswith("DIRECT"))
            tradecmp.append({"window": w, "config": k, "baseline_trades": len(base_led), "config_trades": len(cur), "kept_identical": len(kept), "baseline_trades_removed": len(rem), "removed_direct_effect": dir_rem, "removed_portfolio_effect": len(rem) - dir_rem,
                             "new_trades_added": len(add), "added_direct_effect": dir_add, "added_portfolio_effect": len(add) - dir_add, "same_day_strategy_changed": strat_chg, "earlier_entry_same_strategy": earlier, "later_entry_same_strategy": later,
                             "changed_second_trade_eligibility_days": second_chg, "changed_outcome_same_entry": outcome_chg, "net_gross_change_rs": round(sum(float(r["gross_pnl_rs"]) for r in cur.values()) - sum(float(r["gross_pnl_rs"]) for r in base_led.values()), 0)})
        dates = sorted(set(runs[w]["BASE"]["days"]))
        for d in dates:
            row = {"window": w, "date": d}
            for k in CONFIGS:
                ts = sorted([r for r in runs[w][k]["ledger"] if r["date"] == d], key=lambda r: r["entry_time"])
                row[k] = "; ".join(f"{r['strategy']}@{r['entry_time']} {r['outcome']} {float(r['gross_pnl_rs']):+.0f}" for r in ts) or "no trade"
            row["differs_from_BASE"] = any(row[k] != row["BASE"] for k in CONFIGS if k != "BASE")
            daybyday.append(row)
    for fn, rows in (("full_backtest_comparison.csv", full), ("strategy_win_rates.csv", wr), ("monthly_performance.csv", monthly), ("annual_performance.csv", annual), ("cost_slippage_sensitivity.csv", cost), ("configuration_signal_comparison.csv", sigcmp),
                     ("configuration_trade_comparison.csv", tradecmp), ("trade_set_attribution.csv", attrib), ("day_by_day_comparison.csv", daybyday)):
        write_csv(R65 / fn, rows)
    # ---------------------------------------------------------------- journal reconciliation (primary window; the journal covers 2025-09..2026-08)
    jrows, summ = M.load_journal(JOURNAL)
    pairs, jsum, wrong_rows, auto_rows, man_rows = [], [], [], [], []
    for k in CONFIGS:
        led = [dict(r) for r in runs["A"][k]["ledger"]]
        for r in led:
            mm_ = int(r["signal_time"][:2]) * 60 + int(r["signal_time"][3:]) - 5
            r["signal_candle_start"] = f"{mm_ // 60:02d}:{mm_ % 60:02d}"
        mt = M.match(jrows, led)
        tbd = defaultdict(list)
        for r in led:
            tbd[r["date"]].append(r)
        stage = {}
        for st, ps in (("STRICT", mt["strict"]), ("TIME_TOLERANT", mt["tolerant"]), ("DATE_STRATEGY_ONLY", mt["date_strategy_only"])):
            for p in ps:
                stage[p.manual.row_id] = (st, p)
                pairs.append({"config": k, "stage": st, "journal_row": p.manual.row_id, "date": p.manual.date, "manual_strategy": p.manual.strategy, "manual_time_label": p.manual.time_label, "manual_outcome": p.manual.outcome, "trade_id": p.trade["trade_id"],
                              "auto_strategy": p.trade["strategy"], "auto_signal_candle_start": p.trade["signal_candle_start"], "auto_outcome": p.trade["outcome"], "outcome_label_agrees": M.outcome_agrees(p.manual.outcome, p.trade["outcome"]) if st != "DATE_STRATEGY_ONLY" else "n/a", "verified_exact_trade_match": False})
        for r in mt["manual_unmatched"]:
            ts = tbd.get(r.date, [])
            wrong = (not r.weekend) and bool(ts) and not any(t["strategy"] == r.strategy for t in ts)
            pairs.append({"config": k, "stage": "MANUAL_ONLY", "journal_row": r.row_id, "date": r.date, "manual_strategy": r.strategy, "manual_time_label": r.time_label, "manual_outcome": r.outcome})
            man_rows.append({"config": k, "journal_row": r.row_id, "date": r.date, "strategy": r.strategy, "time_label": r.time_label, "outcome": r.outcome, "weekend_row": r.weekend, "wrong_strategy_date": wrong})
            if wrong:
                wrong_rows.append({"config": k, "journal_row": r.row_id, "date": r.date, "manual_strategy": r.strategy, "automated_that_day": "/".join(f"{t['strategy']}@{t['entry_time']}" for t in ts)})
        for t in mt["trades_unmatched"]:
            pairs.append({"config": k, "stage": "AUTOMATED_ONLY", "trade_id": t["trade_id"], "date": t["date"], "auto_strategy": t["strategy"], "auto_signal_candle_start": t["signal_candle_start"], "auto_outcome": t["outcome"]})
            auto_rows.append({"config": k, "trade_id": t["trade_id"], "date": t["date"], "strategy": t["strategy"], "entry_time": t["entry_time"], "outcome": t["outcome"], "manual_rows_that_day": "; ".join(f"{r.strategy}@{r.time_label}" for r in jrows if r.date == t["date"]) or "none"})
        jsum.append({"config": k, "automated_trades": len(led), "strict": len(mt["strict"]), "time_tolerant": len(mt["tolerant"]), "date_strategy_only": len(mt["date_strategy_only"]), "manual_only": len(mt["manual_unmatched"]), "manual_only_weekend": sum(1 for r in mt["manual_unmatched"] if r.weekend),
                     "automated_only": len(mt["trades_unmatched"]), "wrong_strategy_dates": sum(1 for x in wrong_rows if x["config"] == k), "outcome_label_agree_strict_tolerant": sum(1 for p in mt["strict"] + mt["tolerant"] if M.outcome_agrees(p.manual.outcome, p.trade["outcome"])),
                     "strict_tolerant_total": len(mt["strict"]) + len(mt["tolerant"]), **{f"strict_{s}": sum(1 for p in mt["strict"] if p.manual.strategy == s) for s in STRATS}, **{f"tolerant_{s}": sum(1 for p in mt["tolerant"] if p.manual.strategy == s) for s in STRATS},
                     **{f"manual_rows_{s}": sum(1 for r in jrows if r.strategy == s) for s in STRATS}, "journal_rows": len(jrows)})
    write_csv(R65 / "manual_journal_reconciliation.csv", pairs)
    write_csv(R65 / "strict_match_comparison.csv", jsum)
    write_csv(R65 / "time_tolerant_match_comparison.csv", [{"config": r["config"], "time_tolerant_additional": r["time_tolerant"], **{f"tolerant_{s}": r[f"tolerant_{s}"] for s in STRATS}} for r in jsum])
    write_csv(R65 / "date_strategy_agreement.csv", [{"config": r["config"], "date_strategy_only": r["date_strategy_only"], "note": "NOT a match; same date and strategy but the time is outside the 15-minute tolerance"} for r in jsum])
    write_csv(R65 / "manual_only_comparison.csv", man_rows)
    write_csv(R65 / "automated_only_comparison.csv", auto_rows)
    write_csv(R65 / "wrong_strategy_comparison.csv", wrong_rows, ["config", "journal_row", "date", "manual_strategy", "automated_that_day"])
    (R65 / "continuation_state.json").write_text(json.dumps({"validation": val, "journal_rows": len(jrows), "journal_summary_total": summ.get("Total trades"), "weekend_rows": sum(1 for r in jrows if r.weekend)}, indent=1, default=str))
    print("tables done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
