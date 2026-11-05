"""Phase 3.2: write CSVs, the per-day Markdown journals, the SVG charts and the JSON snapshots from a built :class:`Bundle`."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import date
from pathlib import Path

from nifty_trading.research import phase32 as X
from nifty_trading.research.phase32_build import Bundle, counts_vs_phase31
from nifty_trading.research.phase32_charts import trade_chart_svg
from nifty_trading.strategies.rules import RULE_BY_ID

CSV_FILES = {
    "daily_summary.csv": "daily", "automated_trades_detailed.csv": "trades", "trade_entry_conditions.csv": "checks", "trade_exits_detailed.csv": "legs", "candle_analysis.csv": "candles",
    "all_strategy_signals.csv": "signals", "ignored_signals.csv": "ignored", "rejected_signals.csv": "rejected", "manual_vs_automated.csv": "manual_cmp",
    "manual_verification_issues.csv": "issues", "manual_journal_normalized.csv": "manual_norm"}


def write_csv(path: Path, rows: list[dict]) -> None:
    fields: list[str] = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in fields})


def write_all_csv(b: Bundle, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, attr in CSV_FILES.items():
        write_csv(out / name, getattr(b, attr))


# ====================================================================================================== charts
LEG_LABEL = {"TARGET_1": "Target 1 booked", "TARGET_2": "Target 2 booked", "ORIGINAL_STOP_BEFORE_T1": "original stop", "POST_T1_STOP_ENTRY_MINUS_PLUS_6": "post-T1 stop (entry -/+ 6)",
             "FORCED_EXIT_1514_OPEN_PROVISIONAL": "provisional forced exit", "UNRESOLVED_NO_FILLABLE_EXIT": "unresolved"}
ROLE_MARK = {"initial_range_candle": "IR", "first_candle": "C0", "rf_range_candle": "RF", "breakout_candle": "BRK", "extension_candle": "EXT", "red_candle": "RED", "support_pivot": "SUP",
             "first_push_top": "PUSH", "signal_candle": "SIGNAL", "interaction_candle": "TEST", "confirmation_candle": "CONFIRM", "close_below_candle": "CLOSE<LOW", "return_inside_candle": "RETURN",
             "weak_first_red_candle": "WEAK RED", "small_support_pivot": "SMALL SUP", "zone_retest_candle": "ZONE TOUCH"}


def trade_chart(b: Bundle, trade_id: str, manual_by_day: dict[str, list[dict]]) -> str:
    tr = b.trade_objs[trade_id]
    ex = b.explanations[trade_id]
    row = next(t for t in b.trades if t["trade_id"] == trade_id)
    d = date.fromisoformat(row["date"])
    inp = b.inputs[d]
    legs = [lg for lg in b.legs if lg["trade_id"] == trade_id]
    r = tr.result
    exits = []
    if legs:
        a, c = legs[0], legs[-1]
        if len(legs) == 1 or (a["exit_time"] == c["exit_time"] and a["exit_price"] == c["exit_price"]):
            if a["exit_time"]:
                exits.append((tr.result.leg1_ts if r.leg1_ts is not None else None, a["exit_price"], f"Legs 1+2: {LEG_LABEL.get(a['exit_reason'], a['exit_reason'])}"))
        else:
            exits.append((r.leg1_ts, a["exit_price"], f"Leg 1: {LEG_LABEL.get(a['exit_reason'], a['exit_reason'])}"))
            if c["exit_time"]:
                exits.append((r.leg2_ts, c["exit_price"], f"Leg 2: {LEG_LABEL.get(c['exit_reason'], c['exit_reason'])}"))
    td = {"entry_ts": tr.fill_timestamp, "entry": tr.entry_price, "direction": tr.signal.direction, "stop": r.stop_level, "t1": r.t1_level, "t2": r.t2_level, "post_t1": r.post_t1_stop_level, "post_t1_from": r.leg1_ts if r.post_t1_stop_level is not None else None, "exits": exits}
    from nifty_trading.research.phase32_build import chart_inputs
    lv = chart_inputs(tr, ex, tr.signal, r)
    man = [{"label": m["entry_time_label"], "text": f"{m['strategy_normalized']} {m['exit_classification_entered']} (row {m['journal_row']})"} for m in manual_by_day.get(row["date"], [])]
    what = tr.signal.strategy if tr.signal.method == tr.signal.strategy else f"{tr.signal.strategy} {tr.signal.method}"
    title = f"{trade_id}  {what} {tr.signal.direction}  {row['date']}  -> {tr.classification}  gross Rs {row['gross_pnl_rs']:,.0f}"
    marks = [(cr.candle.start, ROLE_MARK[cr.role]) for cr in ex.candles if cr.session == "TODAY" and cr.role in ROLE_MARK] + \
            [(cr.candle.start, f"CMP{k + 1}") for k, cr in enumerate(c for c in ex.candles if c.role.startswith("compression_"))]
    return trade_chart_svg(title, inp.cs, td, lv, man, marks=marks)


def write_charts(b: Bundle, out: Path) -> int:
    d = out / "charts"
    d.mkdir(parents=True, exist_ok=True)
    mb: dict[str, list[dict]] = defaultdict(list)
    for m in b.manual_norm:
        mb[m["date"]].append(m)
    n = 0
    for t in b.trades:
        (d / f"{t['trade_id']}.svg").write_text(trade_chart(b, t["trade_id"], mb))
        n += 1
    return n


# ====================================================================================================== daily journals
def cell(v) -> str:
    if v is None:
        return ""
    s = f"{v:,.2f}" if isinstance(v, float) else str(v)
    return s.replace("|", "\\|").replace("\n", " ")


def table(headers: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(cell(x) for x in r) + " |" for r in rows]
    return "\n".join(out)


def day_conclusion(b: Bundle, d: date, trades: list[dict], cmp_rows: list[dict], sigs: list[dict], daily: dict) -> str:
    tl = b.timelines[d]
    out = []
    if trades:
        for t in trades:
            out.append(f"* **Traded:** {t['trade_id']} - {t['strategy']} {t['method']} {t['direction']} at {t['fill_timestamp'][-5:]} (entry {t['entry_price']:,.2f}), outcome {t['outcome']}, gross Rs {t['gross_pnl_rs']:,.2f}, "
                       f"illustrative net Rs {t['illustrative_net_pnl_rs']:,.2f}. **Why:** {t['selection_explanation']} **How it ended:** " + t["exit_narrative"].split(". ", 1)[-1][:400])
    else:
        reasons = Counter((r.strategy, (r.invalidation_reason or r.signal_status).split("(")[0][:60]) for r in tl.records if r.signal_status != "CONFIRMED")
        conf = [s for s in sigs]
        out.append("* **Traded:** nothing. " + (f"{len(conf)} confirmed signal(s) exist but none became a trade (see section B)." if conf else
                                                    "No engine produced a confirmed signal that day."))
        if reasons:
            out.append("* **Engine setups that did not complete:** " + "; ".join(f"{s} {w} x{n}" for (s, w), n in reasons.most_common(8)))
        if any(x.event == "CONFLICT" for x in tl.result.diagnostics):
            out.append("* **Simultaneous-signal conflict:** different strategies signalled in the same minute; the day was marked unresolved and nothing was traded.")
    ign = [s for s in sigs if s["controller_event"] in ("IGNORED", "REJECTED", "CONFLICT", "MERGED_SAME_STRATEGY_METHOD")]
    if ign:
        c = Counter((s["strategy"], s["controller_event"], s["controller_reason"].split("(")[0].strip()) for s in ign)
        out.append("* **Ignored / rejected signals:** " + "; ".join(f"{s} {e} {w} x{n}" for (s, e, w), n in c.most_common(8)))
    un = [c for c in cmp_rows if c["journal_row"] != "" and c["match_classification"] not in ("EXACT_MATCH", "TIME_SHIFTED_MATCH")]
    for c in un:
        out.append(f"* **Unmatched manual trade (row {c['journal_row']}, {c['journal_strategy']} {c['manual_entry_time_label']} {c['manual_outcome']}):** {c['explanation']}")
    for c in [c for c in cmp_rows if c["match_classification"] == "EXTRA_AUTOMATED_TRADE"]:
        out.append(f"* **Extra automated trade {c['trade_id']}:** {c['explanation']}")
    if daily.get("strategies_not_evaluated"):
        extra = (" The previous session is separated from this one by the excluded 2025-10-21 Diwali Muhurat session (a one-hour special session), so the previous-day levels of ORB/PDR/PDS/RF cannot be verified."
                 if "EXCLUDED_SESSION" in daily["strategies_not_evaluated"] else "")
        out.append("* **Partial strategy coverage:** some engines could not be evaluated on this day (" + daily["strategies_not_evaluated"] + "); no signal from them can exist, so a missing signal is not evidence of a non-setup." + extra)
    open_rules = sorted({u.split(":")[0] for t in trades for u in b.explanations[t["trade_id"]].unresolved})
    if open_rules:
        out.append("* **Open strategy-definition issues that affected this day:** " + ", ".join(f"{r} ({RULE_BY_ID[r]['description'].split('. ')[0].rstrip('.')})" if r in RULE_BY_ID else r for r in open_rules))
    out.append(f"* **Automated triage (not an approval; the owner's review status stays blank):** {daily['automated_review_flag']}")
    return "\n".join(out)


def render_day(b: Bundle, d: date, rel_charts: str = "../../charts") -> str:  # noqa: C901
    daily = next(x for x in b.daily if x["date"] == str(d))
    trades = [t for t in b.trades if t["date"] == str(d)]
    sigs = [s for s in b.signals if s["date"] == str(d)]
    cmp_rows = [c for c in b.manual_cmp if c["date"] == str(d)]
    tl = b.timelines[d]
    L: list[str] = [f"# Trading journal - {d} ({d:%A})", "",
                    f"> {b.banner} Synthetic NIFTY 50 index-point P&L (the index is not tradable). The owner's review status is intentionally blank.", ""]
    # A
    L += ["## A. Trading day overview", "", table(["item", "value"], [
        ["Date / weekday", f"{d} / {d:%A}"], ["Session type", daily["session_type"]], ["Original session open (first 1-minute open)", daily["original_session_open"]],
        ["Previous session", daily["previous_session"]], ["Previous-day high / low (wicks included)", f"{cell(daily['prev_day_high'])} / {cell(daily['prev_day_low'])}"],
        *([["Previous-day highest BODY high (the body-based PDR ceiling; wicks ignored)", cell(daily["prev_day_highest_body_high"])]] if daily.get("prev_day_highest_body_high") not in (None, "") else []),
        ["Previous-day official close / last 5-minute close", f"{cell(daily['prev_day_official_close'])} / {cell(daily['prev_day_last_5m_close'])}"],
        ["Raw engine records / confirmed signals / fully valid signals", f"{daily['raw_engine_records']} / {daily['confirmed_signals']} / {daily['fully_valid_signals']}"],
        ["Setups that did not complete (invalidated / incomplete)", daily["setups_not_confirmed"]], ["Executed trades", f"{daily['executed_trades']} {daily['trade_ids']}"],
        ["Gross P&L (Rs, synthetic)", daily["gross_pnl_rs"]], ["Illustrative net P&L (Rs; Rs 500/trade + 0.5 pt/fill)", daily["illustrative_net_pnl_rs"]],
        ["Day-end portfolio status", daily["day_end_portfolio_state"]], ["Manual journal trades (matched / unmatched)", f"{daily['manual_journal_trades']} ({daily['manual_matched']} / {daily['manual_unmatched']})"],
        ["Extra automated trades", daily["extra_automated_trades"]]]), ""]
    # B
    L += ["## B. Daily strategy signal timeline (confirmed signals, chronological)", ""]
    if sigs:
        L += [table(["time", "strategy", "method", "dir", "entry-rule status", "valid for execution", "<= 13:00", "portfolio state", "accepted / ignored", "specific reason", "competing (same minute)"],
                    [[s["time"], s["strategy"], s["method"], s["direction"], s["entry_rule_status"], s["fully_valid_for_execution"], s["within_13_00_cutoff"], s["portfolio_state_at_signal"],
                      ("ACCEPTED -> " + s["trade_id"]) if s["trade_id"] else s["controller_event"],
                      ((("first eligible signal of the day" if s["trade_id"].split("-")[1] == "1" else "permitted second trade: newly confirmed PDR/PDS after the original full stop") + "; " + s["controller_reason"]) if s["trade_id"]
                       else (s["controller_reason"] or s["validity_note"] or "")) + (f" [blocked by {s['blocked_by']}]" if s["blocked_by"] else ""),
                      s["competing_signals_same_minute"]] for s in sigs]), ""]
    else:
        L += ["No engine produced a confirmed signal on this day.", ""]
    nc = [r for r in tl.records if r.signal_status != "CONFIRMED"]
    if nc:
        L += [f"Engine setups that did not complete ({len(nc)}); the complete list with failed rule ids is in `rejected_signals.csv`:", "",
              table(["candle", "strategy", "method", "dir", "status", "precise reason", "failed rules"],
                    [[f"{r.signal_candle_start:%H:%M}" if r.signal_candle_start else "", r.strategy, r.method, r.direction, r.signal_status, r.invalidation_reason or "", ";".join(r.rule_ids_failed)] for r in nc[:25]]),
              ("" if len(nc) <= 25 else f"\n... and {len(nc) - 25} more in `rejected_signals.csv`."), ""]
    # C
    L += ["## C. Detailed trade journals", ""]
    if not trades:
        L += ["No trade was executed.", ""]
    for t in trades:
        tid = t["trade_id"]
        ex = b.explanations[tid]
        legs = [x for x in b.legs if x["trade_id"] == tid]
        cand = [c for c in b.candles if c["trade_id"] == tid]
        cm = next((c for c in cmp_rows if c["trade_id"] == tid), None)
        what = t["strategy"] if t["method"] == t["strategy"] else f"{t['strategy']} {t['method']}"
        L += [f"### {tid}: {what} {t['direction']} ({t['first_or_second']} trade)", "", f"Chart: ![{tid}]({rel_charts}/{tid}.svg)", "",
              f"**Rule configuration:** {t['rule_configuration_id']} - signal verification status **{t['signal_verification_status']}** (never VERIFIED while a rule rests on a proposal).", "",
              "#### 1. Setup identification", "", t["setup_explanation"], "", "#### 2. Candle and indicator calculations", "",
              table(["role", "session", "candle", "O", "H", "L", "C", "range", "body %", "upper wick %", "lower wick %", "direction", "EMA(200)", "strong bull / bear", "pin bull / bear", "small (body<=30%)", "used for"],
                    [[c["role"], c["session"], f"{c['candle_start'][-5:]}-{c['candle_end'][-5:]}", c["open"], c["high"], c["low"], c["close"], c["range"],
                      "undef." if c["body_pct"] in (None, "") else f"{c['body_pct']:.2f}", "undef." if c["upper_wick_pct"] in (None, "") else f"{c['upper_wick_pct']:.2f}",
                      "undef." if c["lower_wick_pct"] in (None, "") else f"{c['lower_wick_pct']:.2f}", c["direction"], c["ema200_5m"], f"{c['strong_bullish']} / {c['strong_bearish']}",
                      f"{c['bullish_pin']} / {c['bearish_pin']}", c["small_body_le_30pct"], c["used_for"]] for c in cand]), "",
              "Every condition, with the rule, the calculation, the observed values and the result:", "",
              table(["#", "group", "rule", "result", "status / numeric definition", "calculation", "observed", "required", "available at", "why it matters"],
                    [[c.seq, c.group, c.rule_id, c.result, f"{c.rule_status} / {c.definition_status}", c.calculation, c.observed, c.required, c.available_at, c.why_it_matters] for c in ex.checks]), "",
              "#### 3. Entry decision and explanation", "", t["setup_explanation"], "", f"**Why this trade ahead of the other strategies:** {t['selection_explanation']}", "",
              "#### 4. Actual entry execution", "", table(["item", "value"], [
                  ["Signal candle", f"{t['signal_candle_start']}-{t['signal_candle_end']}"], ["Signal confirmed", t["signal_confirmed_at"]], ["Fill timestamp", t["fill_timestamp"]], ["Entry price", t["entry_price"]],
                  ["Source partition / 1-minute bar", f"{t['entry_source_partition']} / {t['entry_source_bar_ts']}"],
                  ["Source bar O / H / L / C", f"{cell(t['entry_bar_open'])} / {cell(t['entry_bar_high'])} / {cell(t['entry_bar_low'])} / {cell(t['entry_bar_close'])}"],
                  ["Fill assumption", t["entry_fill_assumption"]], ["Initial stop / T1 / T2 / post-T1 stop", f"{cell(t['initial_stop'])} / {cell(t['target_1'])} / {cell(t['target_2'])} / {cell(t['post_t1_stop'])}"],
                  ["Position", f"{t['lots']} lots x {t['lot_multiplier']} = {t['qty_total']} units (Leg 1 {t['qty_leg1']}, Leg 2 {t['qty_leg2']})"]]), "",
              "#### 5-8. Trade progress, Target 1, post-T1 stop and final exit", "", t["exit_narrative"], ""]
        L += [table(["leg", "qty", "exit time", "exit price", "reason", "source 1-minute bar", "O / H / L / C", "gross points", "gross Rs", "slippage pts", "flags"],
                    [[g["leg"], g["quantity"], g["exit_time"][-5:] if g["exit_time"] else "", g["exit_price"], g["exit_reason"], g["exit_source_bar_ts"][-5:] if g["exit_source_bar_ts"] else "",
                      f"{cell(g['exit_bar_open'])} / {cell(g['exit_bar_high'])} / {cell(g['exit_bar_low'])} / {cell(g['exit_bar_close'])}", g["gross_pnl_points"], g["gross_pnl_rs"], g["adverse_slippage_points"], g["flags"]]
                     for g in legs]), "",
              "Exit evidence per leg:", ""] + [f"* Leg {g['leg']}: {g['exit_trigger_evidence']}" for g in legs] + [""]
        L += ["#### 9. Gross and illustrative net P&L", "", table(["item", "value (Rs)"], [
            ["Leg 1 gross", t["leg1_pnl_rs"]], ["Leg 2 gross", t["leg2_pnl_rs"]], ["Trade gross (= Leg 1 + Leg 2)", t["gross_pnl_rs"]], ["Illustrative fixed cost", -t["illustrative_cost_rs"]],
            ["Illustrative slippage (0.5 pt on every fill, entry + exits, all units)", -t["illustrative_slippage_rs"]], ["Illustrative net", t["illustrative_net_pnl_rs"]]]), "",
            "#### 10. Manual journal comparison", "", ("No manual journal exists for this period; no comparison." if not b.has_journal else (cm["explanation"] if cm else "No journal counterpart.")), ""]
    # D
    L += ["## D. Manual journal comparison", ""]
    if not b.has_journal:
        L += ["No manual journal exists for this period (the manual journal covers 2025-09-01 .. 2026-08-31 only); no comparison is made and no automated trade is labelled 'extra'.", ""]
    elif cmp_rows:
        L += [table(["comparison", "journal row", "journal strategy", "manual time", "manual direction", "manual outcome", "match class", "trade", "auto entry", "auto outcome", "explanation"],
                    [[c["comparison_id"], c["journal_row"], c["journal_strategy"], c["manual_entry_time_label"], c["manual_direction"], c["manual_outcome"], c["match_classification"], c["trade_id"],
                      f"{c['auto_entry_time']} @ {cell(c['auto_entry_price'])}" if c["trade_id"] else "", c["auto_outcome"], c["explanation"]] for c in cmp_rows]), "",
              "The journal records no entry price and no exit price (NOT_RECORDED); matching uses date, strategy and candle start only - never P&L.", ""]
    else:
        L += ["No manual journal trade and no automated trade on this day.", ""]
    # E
    L += ["## E. Daily conclusion", "", day_conclusion(b, d, trades, cmp_rows, sigs, daily), ""]
    return "\n".join(L)


def write_daily(b: Bundle, out: Path) -> int:
    n = 0
    for d in b.days:
        p = out / "daily" / f"{d:%Y-%m}" / f"{d}.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(render_day(b, d))
        n += 1
    return n


# ====================================================================================================== json snapshots
def configuration_snapshot(b: Bundle) -> dict:
    sc = b.scenario
    return {"phase": b.phase_label.replace("Phase ", ""), "scenario": sc.key, "title": sc.title, "rule_configuration_id": b.cfg_id, "proposal_config": sc.proposals.to_dict(), "trade_config": asdict(sc.trade),
            "controller": {"collision_policy": "MARK_DAY_UNRESOLVED", "entry_cutoff": "13:00:00 IST", "max_entries_per_day": 2, "second_trade_strategies": ["PDR", "PDS"], "tie_break": None},
            "stops": {s: sc.trade.stop_points(s) for s in X.STRATEGY_ORDER}, "targets_1": sc.trade.t1_points, "targets_2": {s: sc.trade.t2_points(s) for s in X.STRATEGY_ORDER},
            "target_2_status": {s: sc.trade.t2_status(s) for s in X.STRATEGY_ORDER}, "post_t1_stop": "entry -6 (LONG) / +6 (SHORT), no trailing", "forced_exit": "15:14 minute open - PROVISIONAL implementer assumption",
            "lots": {"total": sc.trade.total_lots, "leg1": sc.trade.leg1_lots, "lot_size": sc.trade.lot_size}, "illustrative_costs": {"fixed_rs_per_trade": X.HEADLINE_COST[0], "adverse_slippage_points_per_fill": X.HEADLINE_COST[1]},
            "calendar_timezone": "Asia/Kolkata", "period": "2025-09-01 .. 2026-08-31", "matching": {"tolerance_minutes": 15, "label_convention": "journal Entry Time = START of the 5-minute entry candle", "pnl_used_for_matching": False}}


def data_provenance(b: Bundle) -> dict:
    return {**b.provenance, "phase30_ledger_check": b.ledger_check, "prior_figures_reverified": counts_vs_phase31(b),
            "per_price_provenance": "every trade row carries the source partition, 1-minute bar timestamp and OHLC of its entry fill; every exit leg row carries the same for its exit bar (trade_exits_detailed.csv)"}


def write_json(b: Bundle, out: Path) -> None:
    (out / "configuration_snapshot.json").write_text(json.dumps(configuration_snapshot(b), indent=2, default=str))
    (out / "data_provenance.json").write_text(json.dumps(data_provenance(b), indent=2, default=str))
