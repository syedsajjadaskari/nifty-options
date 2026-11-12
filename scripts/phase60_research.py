"""Phase 6.0: research analyses (signal funnel, EMA scenarios, gap thresholds, inner levels, pattern attribution, configuration comparison) -> Markdown + state JSON. Neutral reporting: no configuration is ranked or selected."""

from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd  # noqa: E402
from phase60_common import CACHE, OUT  # noqa: E402

from nifty_trading.research.orb_v2 import backtest as BT  # noqa: E402
from nifty_trading.research.orb_v2.reporting import md_table  # noqa: E402

CIDS = ("ORB-V2-A", "ORB-V2-B", "ORB-V2-C", "ORB-V2-D")
T = lambda b: bool(b) and str(b) != "False"  # noqa: E731


def df_for(results, win, cid):
    return pd.DataFrame([s for s in results[(win, cid)].sessions if s["evaluable"]])


def funnel(df):
    n = len(df)
    d = df[df["direction_by_ema"].astype(str).isin(["BUY", "SELL"])]
    steps = [("evaluable sessions", n), ("close not on the EMA (direction defined)", len(d))]
    cur = d
    for col, label in (("gap_ok", "gap within limit"), ("level_ok", "previous-day level broken"), ("colour_ok", "candle colour matches"), ("pattern_ok", "at least one pattern"), ("wick_ok", "wrong-side wick <= 20%")):
        cur = cur[cur[col].map(T)]
        steps.append((label, len(cur)))
    return steps


def main() -> int:  # noqa: C901
    results = pickle.loads((CACHE / "results.pkl").read_bytes())
    state: dict = {}
    # ------------------------------------------------------------------------------------------------ funnel + single-gate
    fun_rows, single = [], []
    for win in ("A", "B", "A_TV", "B_TV"):
        df = df_for(results, win, "ORB-V2-A")
        for i, (lab, n) in enumerate(funnel(df)):
            fun_rows.append({"window": win, "step": i, "condition (cumulative, in rulebook order)": lab, "sessions_remaining": n})
        sole = df[df["n_failed"] == 1]["failed"].value_counts().to_dict()
        single.append({"window": win, **{k: sole.get(k, 0) for k in ("GAP_TOO_LARGE", "LEVEL_NOT_BROKEN", "COLOUR_MISMATCH", "NO_PATTERN", "WRONG_SIDE_WICK")}, "signals": int((df["signal"].astype(str) != "nan").sum() - (df["signal"].fillna("") == "").sum())})
    # ------------------------------------------------------------------------------------------------ EMA scenarios
    ema_rows = []
    for win in ("A", "B"):
        df = df_for(results, win, "ORB-V2-A")
        d = df[df["direction_by_ema"].isin(["BUY", "SELL"])]
        g = d.groupby(["direction_by_ema", "ema_scenario"]).agg(sessions=("date", "size"), signals=("signal", lambda x: int((x.fillna("") != "").sum()))).reset_index()
        for r in g.itertuples():
            ema_rows.append({"window": win, "direction": r.direction_by_ema, "scenario": r.ema_scenario, "sessions": r.sessions, "signals": r.signals})
    # ------------------------------------------------------------------------------------------------ gap thresholds
    gap_rows, gap_diff = [], []
    for win in ("A", "B"):
        df = df_for(results, win, "ORB-V2-A")
        ag = df["gap_points"].abs()
        gap_rows.append({"window": win, "sessions": len(df), "abs_gap>250": int((ag > 250).sum()), "abs_gap>300": int((ag > 300).sum()), "250<abs_gap<=300": int(((ag > 250) & (ag <= 300)).sum()), "max_abs_gap": round(float(ag.max()), 1),
                         "gap_up_above_prev_high": int((df["open_1m"] > df["prev_high"]).sum()), "gap_down_below_prev_low": int((df["open_1m"] < df["prev_low"]).sum())})
        a = {s["date"]: s for s in results[(win, "ORB-V2-A")].sessions}
        b = {s["date"]: s for s in results[(win, "ORB-V2-B")].sessions}
        for d, s in a.items():
            if s["evaluable"] and s["signal"] != b[d]["signal"]:
                gap_diff.append({"window": win, "date": d, "gap_points": round(s["gap_points"], 1), "A(250)": s["signal"] or "-", "B(300)": b[d]["signal"] or "-"})
    # ------------------------------------------------------------------------------------------------ inner-level analysis
    lvl_rows = []
    for win in ("A", "B"):
        for cid in CIDS + ("DIAG-A-OLDSIDE",):
            df = df_for(results, win, cid)
            d = df[df["direction_by_ema"].isin(["BUY", "SELL"])]
            ok = d[d["level_ok"].map(T)]
            lvl_rows.append({"window": win, "config": cid, "sessions_with_direction": len(d), "level_test_passed": len(ok), "pass_rate_pct": round(100 * len(ok) / max(len(d), 1), 1), "MAJOR_ONLY": int((ok["qualifying_category"] == "MAJOR_ONLY").sum()),
                             "INNER_ONLY": int((ok["qualifying_category"] == "INNER_ONLY").sum()), "MAJOR_AND_INNER": int((ok["qualifying_category"] == "MAJOR_AND_INNER").sum()), "avg_levels_per_side": round(float(pd.to_numeric(d["levels_total"], errors="coerce").mean()), 1),
                             "sole_failed_gate_is_LEVEL": int(((df["n_failed"] == 1) & (df["failed"] == "LEVEL_NOT_BROKEN")).sum()), "signals": int((df["signal"].fillna("") != "").sum())})
    sig = {(w, c): {s["date"]: s["signal"] for s in results[(w, c)].sessions if s["evaluable"]} for w in ("A", "B") for c in CIDS + ("DIAG-A-OLDSIDE",)}
    diff_rows = []
    for w in ("A", "B"):
        for c in ("ORB-V2-B", "ORB-V2-C", "ORB-V2-D", "DIAG-A-OLDSIDE"):
            a = sig[(w, "ORB-V2-A")]
            o = sig[(w, c)]
            only_a = sorted(d for d in a if (a[d] or "") and not (o.get(d) or ""))
            only_o = sorted(d for d in a if (o.get(d) or "") and not (a[d] or ""))
            diff_rows.append({"window": w, "versus_A": c, "signals_only_in_A": len(only_a), "signals_only_in_other": len(only_o), "dates_only_in_A": ", ".join(map(str, only_a[:12])) + (" ..." if len(only_a) > 12 else ""), "dates_only_in_other": ", ".join(map(str, only_o[:12])) + (" ..." if len(only_o) > 12 else "")})
    # ------------------------------------------------------------------------------------------------ pattern attribution
    pat_rows = []
    for win in ("A", "B", "A_TV", "B_TV"):
        df = df_for(results, win, "ORB-V2-A")
        d = df[df["direction_by_ema"].isin(["BUY", "SELL"]) & df["colour_ok"].map(T)]
        rows = {"window": win, "colour_ok_sessions": len(d), "full_body": int(d["full_body"].map(T).sum()), "pin_bar": int(d["pin_bar"].map(T).sum()), "engulfing": int(d["engulfing"].map(T).sum()), "none_of_the_three": int((~d["pattern_ok"].map(T)).sum()),
                "wrong_side_wick_fail_among_colour_ok": int((~d["wick_ok"].map(T)).sum())}
        sg = df[df["signal"].fillna("") != ""]
        rows.update({"signals": len(sg), "signal_route_full_body_only": int((sg["patterns_matched"] == "full_body").sum()), "signal_route_engulfing_only": int((sg["patterns_matched"] == "engulfing").sum()), "signal_route_pin_only": int((sg["patterns_matched"] == "pin_bar").sum()),
                     "signal_multiple_patterns": int(sg["patterns_matched"].astype(str).str.contains(r"\+").sum())})
        pat_rows.append(rows)
    # wick distribution
    dist = []
    for win in ("A", "B"):
        df = df_for(results, win, "ORB-V2-A")
        d = df[df["direction_by_ema"].isin(["BUY", "SELL"]) & df["colour_ok"].map(T)]
        w = pd.to_numeric(d["wrong_side_wick_pct"], errors="coerce") * 100
        dist.append({"window": win, "n": len(w), "<=10%": int((w <= 10).sum()), "10-20%": int(((w > 10) & (w <= 20)).sum()), "20-25%": int(((w > 20) & (w <= 25)).sum()), "25-30%": int(((w > 25) & (w <= 30)).sum()), ">30%": int((w > 30).sum()),
                     "zero_range_sessions": int(df["failed"].astype(str).str.contains("ZERO_RANGE").sum())})
    route = []
    for win in ("A", "B"):
        tr = results[(win, "ORB-V2-A")].trades
        for label, sel in (("explicit full-body rule matched (alone or with others)", [t for t in tr if "full_body" in t["patterns_matched"]]), ("provisional-only: hammer/shooting-star and/or engulfing, no full-body", [t for t in tr if "full_body" not in t["patterns_matched"]])):
            m = BT.metrics(sel, 75)
            route.append({"window": win, "pattern basis": label, "trades": m["trades"], "win_rate_pct": m["win_rate_pct"], "total_points": m["total_points"], "profit_factor": m["profit_factor"]})
    state.update({"funnel": fun_rows, "single_gate": single, "ema": ema_rows, "gap": gap_rows, "gap_diff": gap_diff, "levels": lvl_rows, "config_diffs": diff_rows, "patterns": pat_rows, "wick_dist": dist, "pattern_route": route})
    (OUT / "phase60_state_research.json").write_text(json.dumps(state, indent=1, default=str))
    perf = pd.read_csv(OUT / "configuration_performance.csv")

    def md_cols(rows, cols=None):
        return md_table(rows, cols)

    (OUT / "ema_gap_research.md").write_text("\n".join([
        "# EMA and gap research (ORB V2)", "", "All counts use the primary 5paisa windows (A = 2025-09..2026-08, B = 2022-09..2025-08) and config ORB-V2-A unless stated. EMA(200) is the independent 5-minute recursion; it agrees with the TradingView/FYERS screenshot labels within 0.25 point.", "",
        "## The three EMA-opening scenarios", "", "Direction is close-based, exactly as the rulebook states. The scenario label records how the candle relates to the EMA: **A** already beyond it with the previous session on the same side; **B** the candle opens on the wrong side/at the EMA and closes beyond it (intrabar cross); "
        "**C** an overnight gap carries the open across the EMA. All three pass the close-based filter. The rulebook does not require the candle to stay on one side, so none is rejected; whether an intrabar cross and an overnight-gap cross should be treated alike is recorded as a source interpretation (not decided here).", "", md_cols(ema_rows), "",
        "## Gap filter (250 versus 300 points)", "", md_cols(gap_rows), "", "Sessions where the two limits change the decision (A = 250, B = 300): ", md_cols(gap_diff) if gap_diff else "_none: the 250/300 choice changes no signal in this window_", "",
        "Both limits are fixed research scenarios; neither is preferred. The gap is the first one-minute open minus the previous trading day's OFFICIAL daily close (vendor daily series). The opening print differs between feeds (see `candle_pattern_validation.md`), so the gap itself is feed-dependent."]))
    (OUT / "inner_levels_research.md").write_text("\n".join([
        "# Previous-day levels research (ORB V2)", "", "The rulebook says breaking ANY one previous-day resistance/support, major or inner, is enough, but states that how levels are found 'is not yet defined'. Therefore:", "",
        "* **Major** = the previous trading day's high / low (single prices, from completed previous-session candles).",
        "* **Inner, SWING_FRACTAL_WICK_ZONE** (configs A, B, D): every confirmed swing high/low (2 candles each side) except the day extreme; resistance zone = [body top, high], support zone = [low, body bottom].",
        "* **Inner, CLUSTER_ZONE** (config C): repeated rejection - at least two swing extremes of the same side within 10 points form one zone [min, max].", "",
        "Both are PROVISIONAL mechanical constructions; neither is claimed to be the author's method and neither was chosen on profitability or journal agreement. Other source-plausible constructions (body-only zones, multi-candle consolidation boundaries, trendline-like levels) were not built.", "",
        "## How binding is the level filter?", "", md_cols(lvl_rows), "",
        "Reading (this follows from the PROVISIONAL construction: every k=2 swing counts as an inner level, giving roughly eight levels per side, so almost any close beyond the lowest swing passes; under a 'major level only' reading the filter would be far more selective): with the literal 'close beyond the level' wording, a BUY close only has to exceed ONE previous-day swing high / zone ceiling, so the filter rejects mainly days that open and close below almost every previous-day level. "
        "The **old-side diagnostic** (DIAG-A-OLDSIDE: the candle must open at or beyond the old side and close beyond the level - i.e. actually *cross* it) is far more selective. Which reading the author means is the largest source of difference in trade count and is unresolved; it is deliberately NOT chosen on results.", "",
        "## Signal differences versus config A", "", md_cols(diff_rows), "",
        "## Gap-ups above the previous day's high", "", "Under the literal wording a candle that opens above yesterday's high and closes higher IS recognised (the close is beyond the major resistance): Example 2 (17 Sep 2025) is such a case (open 25,276.6 > previous high 25,260.5; this is why the screenshot draws no level). "
        "Interpretation A (the candle must start on the old side) would reject it. Counts of such sessions are in `ema_gap_research.md`; trades that fire through this route are tabulated in `performance_by_eligibility_category.csv` (dimension 'open beyond previous-day range')."]))
    (OUT / "candle_pattern_validation.md").write_text("\n".join([
        "# Candle pattern validation (ORB V2)", "", "Independent functions compute colour, range, body, wicks, percentages, hammer / shooting star, engulfing and full-body, with zero-range, doji and floating-point handling (`patterns.py`; unit-tested). "
        "Wrong-side wick uses the WHOLE candle range as the denominator; the 20% limit is a setting (`max_bad_wick_pct`), never silently changed.", "",
        "## What is explicit and what is provisional", "", "| item | status |", "|---|---|", "| colour matches direction | EXPLICIT |", "| wrong-side wick <= 20% of range | EXPLICIT (adjustable) |", "| full-body: green/red with (upper+lower wick) <= 20% of range | EXPLICIT |",
        "| hammer / shooting star proportions | NOT DEFINED -> PROVISIONAL: long-side wick >= 2 x body and opposite wick <= 10% of range |", "| engulfing: body engulfs previous candle body | pattern EXPLICIT, REFERENCE CANDLE at 09:20 UNDEFINED -> A/B/C use the previous session's last continuous 5-minute candle (labelled), D disables engulfing |", "",
        "## Pattern attribution (colour-matching sessions)", "", md_cols(pat_rows), "", "## Wrong-side wick distribution (colour-matching sessions)", "", md_cols(dist), "",
        "## How much of config A rests on provisional pattern conventions?", "", md_cols(route), "", "The explicit full-body rule and the provisional hammer / shooting-star / engulfing conventions are reported separately because only the first is defined by the rulebook. Config A is a reference reading, not a purely written-rule result.", "", "## Feed dependence", "", "The first one-minute bar of a session can carry an opening print that the secondary feed does not (e.g. 24 Sep 2025: open 25,142.55 on 5paisa vs 25,108.75). Because the opening candle's wicks and body are measured from that open, the wick rule, the full-body test and the pin-bar test are feed-dependent. "
        "Funnel counts on the secondary feed are in the table below (labelled sensitivity; never mixed with the primary result).", "", md_cols([r for r in fun_rows if r["window"] in ("A", "A_TV", "B", "B_TV")]), "",
        "Examples 1-3 are validated in `original_examples_reconstruction.md`."]))
    # configuration comparison (neutral)
    comp = perf[["window", "config_id", "signals", "buy", "sell", "executed_trades", "win_rate_pct", "profit_factor", "avg_points_per_trade", "total_points", "total_rs", "max_drawdown_rs", "longest_losing_streak", "target_hits", "stop_hits", "forced_exits"]].to_dict("records")
    (OUT / "configuration_comparison.md").write_text("\n".join([
        "# Configuration comparison (neutral)", "", "These are four research INTERPRETATIONS of one rulebook, not four strategies and not a ranking. **No configuration is selected, preferred or recommended; none was tuned to history.** "
        "The windows are not untouched out-of-sample evidence: the 2025-26 window informed earlier ORB research and the 2022-25 window was used in Phase 4/5 validation. P&L is synthetic NIFTY index-point P&L x 75 units; the index is not tradable.", "",
        "| id | definition | differs from A by |", "|---|---|---|", "| ORB-V2-A | written-rule reference (250-pt gap limit, swing-zone inner levels, previous-session candle as engulfing reference) | - |", "| ORB-V2-B | 300-pt gap limit | gap limit only |",
        "| ORB-V2-C | clustered repeated-rejection inner zones | inner construction only |", "| ORB-V2-D | engulfing disabled at 09:20 | pattern convention only |", "| DIAG-A-OLDSIDE | break = candle crosses the level (open on old side) | break reading only; DIAGNOSTIC, not a candidate |", "",
        "## Results (5paisa = primary; `_TV` = secondary-vendor sensitivity)", "", md_cols(comp), "", "## Where the configurations disagree", "", md_cols(diff_rows), "",
        "Differences in P&L between rows are small-sample effects of a few dates (see the lists above) and must not be read as evidence for one interpretation."]))
    # standalone summary
    first = perf[perf.window.isin(["A", "B"])]
    ann = pd.read_csv(OUT / "annual_performance.csv")
    ann = ann[(ann.window.isin(["A", "B"])) & (ann.config_id == "ORB-V2-A")]
    cost = pd.read_csv(OUT / "trade_cost_sensitivity.csv")
    cost = cost[(cost.window.isin(["A", "B"])) & (cost.config_id == "ORB-V2-A")]
    (OUT / "standalone_orb_backtest_summary.md").write_text("\n".join([
        "# Standalone ORB V2 backtest (30-point stop / 60-point target, one trade per session)", "",
        "**Synthetic research result.** P&L = NIFTY 50 index points x a declared 75 units; the index cannot be traded and nothing here is CE/PE option P&L (that would need historical strike, expiry, premium and lot data, which are not invented). Not optimised, not approved, not a forecast. "
        "No configuration is selected. Neither period is untouched out-of-sample.", "",
        "Execution conventions (provisional, declared before results): entry at the open of the 09:20 one-minute bar; stop first when both are touched in one minute (none occurred); a bar that opens through the stop fills at its open; targets fill at the target price; "
        "forced exit at the open of the 15:14 bar (never at/after 15:15, never on closing-auction bars). Costs: owner's indicative Rs 70 per trade (not a verified brokerage bill) and slippage per side.", "",
        "## Headline by configuration", "", md_cols(first[["window", "config_id", "evaluable_sessions", "signals", "executed_trades", "buy", "sell", "wins", "losses", "win_rate_pct", "profit_factor", "avg_win_rs", "avg_loss_rs", "avg_points_per_trade", "total_points", "total_rs", "max_drawdown_rs", "longest_losing_streak", "target_pct", "stop_pct", "forced_pct", "avg_hold_minutes"]].to_dict("records")), "",
        "## ORB-V2-A by calendar year", "", md_cols(ann.to_dict("records")), "", "## ORB-V2-A cost and slippage scenarios", "", md_cols(cost[["window", "cost_rs_per_trade", "slippage_points_per_side", "trades", "win_rate_pct", "profit_factor", "total_points", "total_rs", "max_drawdown_rs"]].to_dict("records")), "",
        "## Signal funnel (config A, cumulative in rulebook order)", "", md_cols([r for r in fun_rows if r["window"] in ("A", "B")]), "", "Sole failed gate (sessions failing exactly one condition):", md_cols(single), "",
        "Eligibility categories overlap (one trade can satisfy several rules); see `performance_by_eligibility_category.csv`. One combined, non-double-counted result per configuration is the headline table above. Monthly results: `monthly_performance.csv`; annual: `annual_performance.csv`; "
        "alternative same-minute stop/target ordering: column `alt_policy_total_points_if_same_bar_resolved_target_first` in `configuration_performance.csv` (no same-minute collision occurred in the primary run)."]))
    print(json.dumps({"funnel_A": [r for r in fun_rows if r["window"] == "A"], "single": single, "gap": gap_rows, "gapdiff": gap_diff, "levels": [r for r in lvl_rows if r["config"] in ("ORB-V2-A", "DIAG-A-OLDSIDE")]}, indent=0, default=str)[:3800])
    return 0


if __name__ == "__main__":
    sys.exit(main())
