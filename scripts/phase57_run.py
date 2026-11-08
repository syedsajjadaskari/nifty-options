"""Phase 5.7: enhanced trade charts and the exact journal-match report. PRESENTATION AND VERIFICATION ONLY.

  python scripts/phase57_run.py

No backtest is run, no strategy rule and no matching rule is touched. Every number on a chart (entry, stop, targets, post-T1 stop, exits, P&L) is read from the verified Phase 5.5 ledgers (all_executed_trades.csv, all_trade_legs.csv) and every match label
from the verified Phase 5.6 files (manual_vs_automated_matching.csv, mismatch_root_causes.csv); the only thing taken from the engines is the CONTEXT already drawn in Phase 3.6 (the five-minute candles, EMA, reference levels, zones and role marks), obtained by
re-instantiating the three verified configurations through the same unchanged pipeline, and every trade of that re-instantiation is asserted equal to the ledger before its chart is written. Nothing from Phase 3.6, 5.5 or 5.6 is overwritten or modified
(their file hashes are recorded before the first write and re-verified by the audit).
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sys
import warnings
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from nifty_trading.research import phase3 as P  # noqa: E402
from nifty_trading.research import phase32_build as B  # noqa: E402
from nifty_trading.research import phase55 as X  # noqa: E402
from nifty_trading.research import phase57 as V  # noqa: E402
from nifty_trading.research.phase32_build import chart_inputs  # noqa: E402
from nifty_trading.research.phase32_render import ROLE_MARK  # noqa: E402

P55 = ROOT / "reports" / "phase5" / "phase55_combined_backtest"
P56 = ROOT / "reports" / "phase5" / "phase56_manual_reconciliation"
OUT = ROOT / "reports" / "phase5" / "phase57_trade_visualization"
K = ("A", "B", "C")
CFG_NAME = {"A": "A - frozen Phase 3.6", "B": "B - Phase 5.3 author-corrected", "C": "C - B + ORB gap crossing (provisional)"}
STATUS = {"STRICT": "EXACT_MATCH", "TIME_TOLERANT": "TIME_TOLERANT_MATCH", "DATE_STRATEGY_ONLY": "DATE_STRATEGY_ONLY", "AUTOMATED_ONLY": "AUTOMATED_ONLY"}
STATUS_NOTE = {"EXACT_MATCH": "counted match (same date and strategy, journal label = signal candle start)", "TIME_TOLERANT_MATCH": "counted match (same date and strategy, label within 15 minutes of the signal candle start)",
               "DATE_STRATEGY_ONLY": "NOT a match: same date and strategy, time more than 15 minutes apart", "AUTOMATED_ONLY": "no journal row with this date and strategy was left for this trade"}
REASON = {"TARGET_1": "T1 hit", "TARGET_2": "T2 hit", "ORIGINAL_STOP_BEFORE_T1": "Initial SL", "POST_T1_STOP_ENTRY_MINUS_PLUS_6": "Post-T1 stop", "FORCED_EXIT_1514_OPEN_PROVISIONAL": "Forced exit (15:14 open, provisional)"}
OUTCOME_OF = {"Target": "TARGET", "SL": "INITIAL_FULL_STOP", "BE": "T1_THEN_BUFFER_STOP"}
SUBSETS = ("charts_all", "charts_exact_matches", "charts_time_tolerant", "charts_automated_only", "charts_date_strategy_only", "charts_orb_focus", "charts_handwritten_dates", "charts_config_differences")


def rd(p: Path) -> list[dict]:
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def wr(p: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    fields = fields or list({k: 0 for r in rows for k in r})
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in fields})


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dts(s: str) -> datetime:
    return datetime.strptime(s[:16], "%Y-%m-%d %H:%M")


def f(x) -> float:
    return float(str(x).replace(",", ""))


def sgn(v: float, d: int = 2) -> str:
    return f"{v:+,.{d}f}"


def short(text: str, n: int) -> str:
    text = " ".join(text.split())
    if len(text) <= n:
        return text
    cut = text[:n].rsplit(" ", 1)[0]
    return cut + " ..."


# ------------------------------------------------------------------------------------------------------------------------------ the trade specification (ledger values only)
def trade_exits(legs: list[dict]) -> list[dict]:
    """Exit markers from the leg rows of the ledger: one FULL exit when both legs close together on the same stop / forced exit, otherwise one per leg."""
    l1 = next(x for x in legs if x["leg"] == "1")
    l2 = next(x for x in legs if x["leg"] == "2")
    same = (l1["exit_time"] == l2["exit_time"] and l1["exit_price"] == l2["exit_price"] and l1["exit_reason"] == l2["exit_reason"] and l1["exit_reason"] in ("ORIGINAL_STOP_BEFORE_T1", "FORCED_EXIT_1514_OPEN_PROVISIONAL"))
    out = []
    if same:
        px, tm = V.money(f(l1["exit_price"])), l1["exit_time"][-5:]
        label = f"FORCED EXIT — {tm} @ {px}" if l1["exit_reason"].startswith("FORCED") else f"FULL EXIT — {REASON[l1['exit_reason']]}, {tm} @ {px}"
        out.append({"leg": "FULL", "reason": l1["exit_reason"], "ts": dts(l1["exit_time"]), "price": f(l1["exit_price"]), "label": label})
    else:
        for g, tag in ((l1, "LEG1"), (l2, "LEG2")):
            out.append({"leg": g["leg"], "reason": g["exit_reason"], "ts": dts(g["exit_time"]), "price": f(g["exit_price"]), "label": f"{tag} EXIT — {REASON[g['exit_reason']]}, {g['exit_time'][-5:]} @ {V.money(f(g['exit_price']))}"})
    return out


def match_of(cfg: str, tid: str, mt_by_trade: dict, cause_by_trade: dict) -> dict:
    r = mt_by_trade.get((cfg, tid))
    if r is None or r["match_stage"] == "AUTOMATED_ONLY":
        c = cause_by_trade.get((cfg, tid), {})
        return {"status": "AUTOMATED_ONLY", "row": None, "cause": c.get("root_cause_primary", ""), "cause2": c.get("root_cause_secondary", ""), "evidence": c.get("evidence", "")}
    c = cause_by_trade.get((cfg, tid), {})
    return {"status": STATUS[r["match_stage"]], "row": r, "cause": c.get("root_cause_primary", ""), "cause2": c.get("root_cause_secondary", ""), "evidence": c.get("evidence", "")}


def build_spec(cfg: str, t: dict, legs: list[dict], mt_rows_day: list[dict], match: dict, ctx: dict) -> dict:
    """``t``: the ledger row; ``legs``: its leg rows; ``ctx``: candles / hlines / zones / marks of the bundle (context only)."""
    entry, stop, t1, t2 = f(t["entry_price"]), f(t["initial_stop"]), f(t["target_1"]), f(t["target_2"])
    exits = trade_exits(legs)
    l1 = next(x for x in legs if x["leg"] == "1")
    t1_hit = l1["exit_reason"] == "TARGET_1"
    post = f(t["post_t1_stop"]) if t1_hit and t["post_t1_stop"] not in ("", None) else None
    direction = t["direction"]
    what = t["strategy"] if t["method"] == t["strategy"] else f"{t['strategy']} {t['method']}"
    jr = match["row"]
    status = match["status"]
    # manual journal lines of the day (the journal rows as written; the one matched to this trade is emphasised)
    manual = []
    for r in mt_rows_day:
        mine = jr is not None and r["journal_row"] == jr["journal_row"]
        manual.append({"label": r["manual_time_label"], "row": r["journal_row"], "matched": mine,
                       "text": f"JOURNAL #{r['journal_row']} {r['manual_strategy']} {r['manual_time_label']} {r['manual_outcome']}" + (f"  [{status}]" if mine else "")})
    if jr is not None:
        l4 = f"journal row #{jr['journal_row']} (sheet row {jr['sheet_row']}): {jr['manual_strategy']} {jr['manual_time_label']} {jr['manual_outcome']}"
    else:
        l4 = "journal row: none (no journal match)"
    header = {"l1": f"TRADE {t['trade_id']}   {what} {direction}", "l2": f"Date {t['date']} ({t['weekday']})   |   Configuration {CFG_NAME[cfg]}   |   {t['first_or_second'].title()} trade of the day   |   outcome {t['outcome']}",
              "l3": f"Signal candle {t['signal_candle_start']}-{t['signal_candle_end']} (5-min)   |   Entry {t['fill_timestamp'][-5:]} @ {V.money(entry)}   |   Gross Rs {sgn(f(t['gross_pnl_rs']), 0)}   |   {STATUS_NOTE[status]}", "l4": l4}
    q1, q2, mult = f(t["qty_leg1"]), f(t["qty_leg2"]), f(t["lot_multiplier"])
    lots1, lots2 = int(round(q1 / mult)), int(round(q2 / mult))
    reason_txt = short(t["setup_explanation"], 330)
    entry_block = [(f"Entry timestamp: {t['fill_timestamp']}", "b"), (f"Entry price: {V.money(entry)}   (open of the 1-minute bar that starts when the signal candle ends; rule EXE-FILL-001)", ""), (f"Signal candle: {t['signal_candle_start']}-{t['signal_candle_end']} (5-min), confirmed {t['signal_confirmed_at'][-5:]}", ""),
                   (f"Fill candle (1-min bar {t['entry_source_bar_ts'][-5:]}): O {V.money(f(t['entry_bar_open']))}  H {V.money(f(t['entry_bar_high']))}  L {V.money(f(t['entry_bar_low']))}  C {V.money(f(t['entry_bar_close']))}", ""),
                   (f"Trigger: {t['strategy']} / {t['method']} ({direction})", "b"), (f"Reason: {reason_txt}", "g")]
    lvl_lines = [(f"Initial stop (SL): {V.money(stop)}   [{abs(entry - stop):.1f} pts]", ""), (f"Target 1 (T1): {V.money(t1)}   [{abs(entry - t1):.1f} pts]", ""), (f"Target 2 (T2): {V.money(t2)}   [{abs(entry - t2):.1f} pts]", "")]
    if post is not None:
        lvl_lines.append((f"Post-T1 stop: {V.money(post)}   [entry {'-' if direction == 'LONG' else '+'}6; active from {l1['exit_time'][-5:]}]", ""))
    else:
        lvl_lines.append(("Post-T1 stop: not active (Target 1 was not hit)", "g"))
    for g in legs:
        lvl_lines.append((f"Leg {g['leg']} ({int(f(g['quantity']))} units) EXIT: {REASON[g['exit_reason']]} - {g['exit_time'][-5:]} @ {V.money(f(g['exit_price']))}", "b"))
    lvl_lines.append((f"Automated exit class: {t['outcome']}", ""))
    pnl = [(f"Position: {lots1} + {lots2} lots ({int(q1)} + {int(q2)} units; {int(f(t['lots']))} x {int(mult)})", "")]
    for g in legs:
        pnl.append((f"Leg {g['leg']}: {sgn(f(g['gross_pnl_points']))} pts x {int(f(g['quantity']))} = Rs {sgn(f(g['gross_pnl_rs']), 0)}", ""))
    pnl += [(f"Gross: {sgn(f(t['gross_pnl_points_weighted']), 3)} pts (per-unit average) = Rs {sgn(f(t['gross_pnl_rs']), 0)}", "b"),
            (f"Net, Rs 70/trade, no slippage (report headline): Rs {sgn(f(t['net_pnl_rs_scenario_B']), 0)}", ""),
            (f"Net with slippage per side 0.25 / 0.5 / 1.0 pt: Rs {sgn(f(t['net_pnl_rs_scenario_C']), 0)} / {sgn(f(t['net_pnl_rs_scenario_D']), 0)} / {sgn(f(t['net_pnl_rs_scenario_E']), 0)}", "")]
    if f(t["adverse_slippage_points"]) > 0:
        pnl.append((f"Adverse gap slippage logged on a stop fill: {f(t['adverse_slippage_points']):.2f} pts", "g"))
    pnl.append(("SYNTHETIC index-point P&L; not option P&L. Rs 70 coverage is unconfirmed.", "g"))
    if jr is not None:
        agree = jr["outcome_class_agrees_descriptive"] == "True"
        jb = [(f"Match type: {status}  ({ {'EXACT_MATCH': 'strict, delta 0 min', 'TIME_TOLERANT_MATCH': 'within 15 min', 'DATE_STRATEGY_ONLY': 'not counted'}[status] })", "b"), (STATUS_NOTE[status], "g"), (f"Journal row #{jr['journal_row']} (sheet row {jr['sheet_row']}): {jr['manual_strategy']} at {jr['manual_time_label']} (candle-start label)", ""),
              (f"Journal outcome label: {jr['manual_outcome']} (~{OUTCOME_OF.get(jr['manual_outcome'], '?')}); automated exit class: {t['outcome']}", ""),
              (f"Outcome agreement: {'YES' if agree else 'NO'}", "ok" if agree else "r"), (f"Time difference (automated signal candle start - journal label): {jr['delta_minutes_vs_signal_candle_start']} min", "")]
        if status == "DATE_STRATEGY_ONLY":
            jb.append(("Not counted as a match (outside the 15-minute tolerance).", "r"))
    else:
        jb = [("Journal match: NO", "r"), ("Match type: AUTOMATED_ONLY", "b"), (f"Root cause: {match['cause']}" + (f" (secondary {match['cause2']})" if match["cause2"] else ""), ""), (f"Evidence: {short(match['evidence'], 300)}", "g")]
    others = [r for r in mt_rows_day if jr is None or r["journal_row"] != jr["journal_row"]]
    jb.append(("Other journal rows on this date: " + ("; ".join(f"#{r['journal_row']} {r['manual_strategy']} {r['manual_time_label']} {r['manual_outcome']}" for r in others) if others else "none"), "g"))
    meta = {"kind": "TRADE", "config": cfg, "trade_id": t["trade_id"], "date": t["date"], "strategy": t["strategy"], "method": t["method"], "direction": direction, "entry_ts": t["fill_timestamp"], "entry": entry, "stop": stop, "t1": t1, "t2": t2,
            "post_t1": post, "exits": [{"leg": e["leg"], "reason": e["reason"], "ts": f"{e['ts']:%Y-%m-%d %H:%M}", "price": e["price"], "label": e["label"]} for e in exits], "match_status": status,
            "journal_row": None if jr is None else jr["journal_row"], "journal_label": None if jr is None else jr["manual_time_label"], "journal_outcome": None if jr is None else jr["manual_outcome"], "gross_pnl_rs": f(t["gross_pnl_rs"]),
            "outcome": t["outcome"]}
    return {"header": header, "badge": (status, status), "candles": ctx["candles"], "hlines": ctx["hlines"], "zones": ctx["zones"], "marks": ctx["marks"], "manual": manual, "meta": meta,
            "trade": {"direction": direction, "entry_ts": dts(t["fill_timestamp"]), "entry": entry, "stop": stop, "t1": t1, "t2": t2, "post_t1": post, "t1_hit_ts": dts(l1["exit_time"]) if t1_hit else None, "exits": exits},
            "blocks": [("ENTRY", entry_block), ("LEVELS AND EXITS", lvl_lines), ("P&L (gross synthetic, then illustrative net)", pnl), ("JOURNAL COMPARISON", jb)],
            "note": "real 5-minute candles (IST); markers sit at their exact 1-minute positions; synthetic NIFTY 50 index points, not a tradable price; every number comes from the verified Phase 5.5 ledger"}


# ------------------------------------------------------------------------------------------------------------------------------ context of the bundles (candles, levels, zones, marks)
def context_of(b, tid: str) -> dict:
    tr = b.trade_objs[tid]
    ex = b.explanations[tid]
    row = next(t for t in b.trades if t["trade_id"] == tid)
    inp = b.inputs[date.fromisoformat(row["date"])]
    lv = chart_inputs(tr, ex, tr.signal, tr.result)
    marks = [(cr.candle.start, ROLE_MARK[cr.role]) for cr in ex.candles if cr.session == "TODAY" and cr.role in ROLE_MARK]
    return {"candles": [{"start": c.start, "o": c.o, "h": c.h, "l": c.l, "c": c.c, "ema": c.ema} for c in inp.cs], "hlines": lv["hlines"], "zones": lv["zones"], "marks": marks, "bundle_row": row, "trade_obj": tr}


def day_context(b, d: str) -> dict:
    inp = b.inputs[date.fromisoformat(d)]
    drow = next(x for x in b.daily if x["date"] == d)
    hl = []
    for key, lab, col in (("prev_day_high", "prev-day high", "#1b5e20"), ("prev_day_low", "prev-day low", "#1b5e20")):
        v = drow.get(key)
        if isinstance(v, (int, float)):
            hl.append((lab, float(v), col))
    cs = [{"start": c.start, "o": c.o, "h": c.h, "l": c.l, "c": c.c, "ema": c.ema} for c in inp.cs]
    first = cs[0]
    hl += [("first-candle high", first["h"], "#6a1b9a"), ("first-candle low", first["l"], "#6a1b9a")]
    return {"candles": cs, "hlines": hl, "zones": [], "marks": [(first["start"], "C0")]}


def main() -> int:  # noqa: C901
    OUT.mkdir(parents=True, exist_ok=True)
    # ---------------------------------------------------------------- hashes of every earlier result BEFORE anything is written
    before = {}
    for base in (P55, P56, ROOT / "reports" / "phase3" / "phase36_body_based_pdr"):
        for p in sorted(base.rglob("*")):
            if p.is_file() and p.name != ".DS_Store":
                before[p.relative_to(ROOT).as_posix()] = sha(p)
    if not (OUT / "before_hashes.json").exists():
        (OUT / "before_hashes.json").write_text(json.dumps(before, indent=0))
    else:
        prior = json.loads((OUT / "before_hashes.json").read_text())
        changed = [k for k, h in prior.items() if before.get(k) != h]
        if changed:
            raise SystemExit(f"earlier results changed since the Phase 5.7 baseline was recorded: {changed[:5]}")
    # ---------------------------------------------------------------- verified inputs
    trades = rd(P55 / "all_executed_trades.csv")
    legs_all = rd(P55 / "all_trade_legs.csv")
    mt = rd(P56 / "manual_vs_automated_matching.csv")
    causes = rd(P56 / "mismatch_root_causes.csv")
    hw = rd(P56 / "handwritten_author_corrections_comparison.csv")
    mo = rd(P56 / "manual_only_trades.csv")
    legs_by = defaultdict(list)
    for g in legs_all:
        legs_by[(g["config"], g["trade_id"])].append(g)
    mt_by_trade = {(r["config"], r["trade_id"]): r for r in mt if r["trade_id"]}
    cause_by_trade = {(r["config"], r["trade_id"]): r for r in causes if r["side"] == "AUTOMATED_ONLY" and r["trade_id"]}
    for r in causes:  # date-and-strategy-only partners: their cause is attached to the manual row; keep it by trade id as well
        if r["trade_id"] and r["side"] == "MANUAL_ONLY" and (r["config"], r["trade_id"]) not in cause_by_trade:
            cause_by_trade[(r["config"], r["trade_id"])] = r
    journal_day = defaultdict(list)  # (config, date) -> journal rows as listed in the matching file
    for r in mt:
        if r["journal_row"]:
            journal_day[(r["config"], r["date"])].append(r)
    # ---------------------------------------------------------------- bundles: context only (no new results)
    sc = P.combined_scenario("BODY_BASED_PHASE36")
    bundles = {}
    for k in K:
        with X.patched_engines(k):
            bundles[k] = B.build(scenario=sc, journal=False)
    for d in (OUT / n for n in SUBSETS):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    # ---------------------------------------------------------------- differing trades between the configurations (ledger keys)
    sig = {(t["config"], t["trade_id"]): (t["method"], t["direction"], t["signal_candle_start"], t["entry_price"], t["outcome"], t["gross_pnl_rs"]) for t in trades}
    differs = set()
    for t in trades:
        keys = [sig.get((c, t["trade_id"])) for c in K]
        if len({k for k in keys}) > 1:
            differs.add((t["config"], t["trade_id"]))
    hw_dates: dict = {}
    for r in hw:
        if r["date"][:2] == "20":  # general remarks carry no date
            hw_dates.setdefault(r["date"], []).append(r["correction_id"])
    index, bad = [], []
    n_by_dir: Counter = Counter()

    def put(fname: str, svg: str, subs: list[str], cfg_trade=None) -> None:
        for s in subs:
            (OUT / s / fname).write_text(svg)
            n_by_dir[s] += 1

    for t in trades:
        cfg, tid = t["config"], t["trade_id"]
        b = bundles[cfg]
        ctx = context_of(b, tid)
        br = ctx["bundle_row"]
        # the re-instantiated trade must equal the ledger (otherwise the chart would show something else than the verified result)
        for a, c in (("entry_price", "entry_price"), ("initial_stop", "initial_stop"), ("target_1", "target_1"), ("target_2", "target_2"), ("gross_pnl_rs", "gross_pnl_rs")):
            if abs(f(br[a]) - f(t[c])) > 1e-6:
                bad.append((cfg, tid, a, br[a], t[c]))
        for a in ("fill_timestamp", "outcome", "strategy", "method", "direction"):
            if str(br[a]) != str(t[a]):
                bad.append((cfg, tid, a, br[a], t[a]))
        if bad:
            raise SystemExit(f"the context re-instantiation differs from the verified ledger: {bad[:5]}")
        match = match_of(cfg, tid, mt_by_trade, cause_by_trade)
        spec = build_spec(cfg, t, legs_by[(cfg, tid)], journal_day.get((cfg, t["date"]), []), match, ctx)
        svg = V.render(spec)
        fname = f"{cfg}_{tid}.svg"
        subs = ["charts_all"]
        st = match["status"]
        subs.append({"EXACT_MATCH": "charts_exact_matches", "TIME_TOLERANT_MATCH": "charts_time_tolerant", "AUTOMATED_ONLY": "charts_automated_only", "DATE_STRATEGY_ONLY": "charts_date_strategy_only"}[st])
        if t["strategy"] == "ORB":
            subs.append("charts_orb_focus")
        if t["date"] in hw_dates:
            subs.append("charts_handwritten_dates")
        if (cfg, tid) in differs:
            subs.append("charts_config_differences")
        put(fname, svg, subs)
        jr = match["row"]
        index.append({"config": cfg, "trade_id": tid, "date": t["date"], "strategy": t["strategy"], "method": t["method"], "direction": t["direction"], "match_status": st, "journal_row": "" if jr is None else jr["journal_row"],
                      "journal_label": "" if jr is None else jr["manual_time_label"], "journal_outcome": "" if jr is None else jr["manual_outcome"], "chart_file": f"charts_all/{fname}", "also_in": ";".join(s for s in subs if s != "charts_all"),
                      "handwritten_correction_ids": ";".join(hw_dates.get(t["date"], []))})
    # ---------------------------------------------------------------- journal-day charts (no executed trade to draw): ORB rows without a counted match; handwritten-correction dates with no trade in any configuration
    day_files = []

    def day_chart(d: str, title_kind: str, rows_by_cfg: dict, subs: list[str]) -> None:
        ctx = day_context(bundles["A"], d)
        jrows = sorted({(r["journal_row"], r["manual_time_label"], r["manual_strategy"], r["manual_outcome"]) for k in K for r in journal_day.get((k, d), [])}, key=lambda x: int(x[0]))
        man = [{"label": lab, "row": rid, "matched": False, "text": f"JOURNAL #{rid} {s} {lab} {oc}"} for rid, lab, s, oc in jrows]
        b1 = [(f"{rid}: {s} at {lab} (outcome {oc})", "") for rid, lab, s, oc in jrows] or [("no journal row on this date", "g")]
        b2 = []
        for k in K:
            for r in mo:
                if r["config"] == k and r["date"] == d and (title_kind != "ORB" or r["manual_strategy"] == "ORB"):
                    b2.append((f"{k}: row #{r['journal_row']} {r['manual_strategy']} - {r['match_stage']} - {r['root_cause_primary']}" + (f" / {r['root_cause_secondary']}" if r["root_cause_secondary"] else ""), "b"))
                    b2.append((short(r["evidence"], 150), "g"))
        b3 = []
        for k in K:
            ts = [t for t in trades if t["config"] == k and t["date"] == d]
            b3.append((f"{k}: " + ("; ".join(f"{t['trade_id']} {t['strategy']} {t['method']} {t['direction']} {t['fill_timestamp'][-5:]} @ {V.money(f(t['entry_price']))} -> {t['outcome']}" for t in ts) if ts else "no executed trade"), ""))
        hwc = hw_dates.get(d, [])
        b4 = [("Handwritten correction(s) on this date: " + ", ".join(f"{r['correction_id']} ({short(r['author_comment'], 80)})" for r in hw if r["date"] == d) if hwc else "No handwritten correction on this date", "")]
        mins = max([int(lab[:2]) * 60 + int(lab[3:5]) for _r, lab, _s, _o in jrows] + [V.T_OPEN + 60])
        spec = {"header": {"l1": f"JOURNAL DAY {d}   {title_kind} journal row(s) without a counted automated match", "l2": f"Date {d}   |   configurations A / B / C   |   no trade is drawn on this chart", "l3": "Manual entries are drawn at the candle START of the journal label (the journal records no price).", "l4": ""},
                "badge": ("MANUAL-ONLY / NO TRADE DRAWN", "NO_TRADE_JOURNAL_DAY"), "candles": ctx["candles"], "hlines": ctx["hlines"], "zones": ctx["zones"], "marks": ctx["marks"], "manual": man, "trade": None, "min_end": mins + 25,
                "meta": {"kind": "DAY", "date": d, "journal_rows": [r[0] for r in jrows], "title_kind": title_kind},
                "blocks": [("JOURNAL ROWS OF THE DAY", b1), ("WHY NO COUNTED MATCH (Phase 5.6 causes)", b2 or [("no unmatched journal row", "g")]), ("AUTOMATED TRADES THAT DAY", b3), ("HANDWRITTEN CORRECTIONS", b4)],
                "note": "real 5-minute candles (IST); synthetic NIFTY 50 index points; causes are quoted from the verified Phase 5.6 file mismatch_root_causes.csv"}
        svg = V.render(spec)
        fname = f"DAY_{d}_{title_kind}.svg"
        put(fname, svg, subs)
        day_files.append({"date": d, "kind": title_kind, "files": ";".join(f"{s}/{fname}" for s in subs)})

    orb_dates = sorted({r["date"] for r in mo if r["manual_strategy"] == "ORB" and "WEEKEND" not in r["journal_flags"]})
    for d in orb_dates:
        day_chart(d, "ORB", {}, ["charts_orb_focus"])
    traded_any = {t["date"] for t in trades}
    for d in sorted(hw_dates):
        if d not in traded_any:
            day_chart(d, "HANDWRITTEN", {}, ["charts_handwritten_dates"])
    wr(OUT / "journal_day_charts_index.csv", day_files)
    wr(OUT / "all_executed_trades_visual_index.csv", index)
    wr(OUT / "handwritten_correction_chart_index.csv", [{"correction_id": r["correction_id"], "date": r["date"], "topic": r["topic"], "trade_charts": ";".join(f"charts_all/{i['config']}_{i['trade_id']}.svg" for i in index if i["date"] == r["date"]) or "none (no executed trade in A, B or C)",
                                                        "day_chart": next((x["files"] for x in day_files if x["date"] == r["date"] and x["kind"] == "HANDWRITTEN"), "")} for r in hw])
    state = {"charts": dict(n_by_dir), "executed_trades": len(trades), "journal_day_charts": len(day_files), "orb_dates": len(orb_dates), "differing_trades": len(differs)}
    (OUT / "phase57_state.json").write_text(json.dumps(state, indent=1))
    print(json.dumps(state, indent=1))
    write_reports(trades, legs_by, mt, causes, mo, hw, index, state)
    return 0


# ------------------------------------------------------------------------------------------------------------------------------ the exact-match report and the verification workbook
def write_reports(trades, legs_by, mt, causes, mo, hw, index, state) -> None:  # noqa: C901
    jr_rows = {k: [r for r in mt if r["config"] == k and r["journal_row"]] for k in K}
    stage = {k: Counter(r["match_stage"] for r in jr_rows[k]) for k in K}
    n_tr = {k: sum(1 for t in trades if t["config"] == k) for k in K}
    strict_by = {k: Counter(r["manual_strategy"] for r in jr_rows[k] if r["match_stage"] == "STRICT") for k in K}
    tol_by = {k: Counter(r["manual_strategy"] for r in jr_rows[k] if r["match_stage"] == "TIME_TOLERANT") for k in K}
    rows = []
    summary = {}
    for k in K:
        counted = [r for r in jr_rows[k] if r["match_stage"] in ("STRICT", "TIME_TOLERANT")]
        strict = [r for r in jr_rows[k] if r["match_stage"] == "STRICT"]
        same = sum(1 for r in counted if r["outcome_class_agrees_descriptive"] == "True")
        same_s = sum(1 for r in strict if r["outcome_class_agrees_descriptive"] == "True")
        auto_only = sum(1 for r in mt if r["config"] == k and r["match_stage"] == "AUTOMATED_ONLY")
        manual_unmatched_all = len(jr_rows[k]) - len(counted)
        manual_no_partner = stage[k]["UNMATCHED_MANUAL"]
        s = {"config": k, "automated_trades": n_tr[k], "strict": stage[k]["STRICT"], "time_tolerant": stage[k]["TIME_TOLERANT"], "date_strategy_only": stage[k]["DATE_STRATEGY_ONLY"], "counted_matches": len(counted),
             "manual_rows_total": len(jr_rows[k]), "manual_only_rows_no_counted_match": manual_unmatched_all, "manual_only_rows_without_any_same_date_strategy_trade": manual_no_partner,
             "automated_only_trades_no_same_date_strategy_row": auto_only, "automated_trades_without_counted_match": n_tr[k] - len(counted), "counted_same_outcome": same, "counted_different_outcome": len(counted) - same,
             "strict_same_outcome": same_s, "strict_different_outcome": len(strict) - same_s, "strict_pct_of_automated_trades": round(100 * stage[k]["STRICT"] / n_tr[k], 2), "strict_pct_of_190_journal_rows": round(100 * stage[k]["STRICT"] / 190, 2),
             "counted_pct_of_automated_trades": round(100 * len(counted) / n_tr[k], 2), "counted_pct_of_190_journal_rows": round(100 * len(counted) / 190, 2)}
        for sname in ("IRF", "ORB", "PDR", "PDS", "RF"):
            s[f"strict_{sname}"] = strict_by[k][sname]
            s[f"time_tolerant_{sname}"] = tol_by[k][sname]
        summary[k] = s
        rows.append(s)
    wr(OUT / "exact_match_summary.csv", rows)
    # breakdown by strategy
    br = []
    for k in K:
        for sname in ("IRF", "ORB", "PDR", "PDS", "RF"):
            jr = [r for r in jr_rows[k] if r["manual_strategy"] == sname]
            tt = [t for t in trades if t["config"] == k and t["strategy"] == sname]
            c = Counter(r["match_stage"] for r in jr)
            counted = [r for r in jr if r["match_stage"] in ("STRICT", "TIME_TOLERANT")]
            ids_counted = {r["trade_id"] for r in counted}
            br.append({"config": k, "strategy": sname, "journal_rows": len(jr), "automated_trades": len(tt), "strict": c["STRICT"], "time_tolerant": c["TIME_TOLERANT"], "date_strategy_only": c["DATE_STRATEGY_ONLY"],
                       "manual_only_no_counted_match": len(jr) - len(counted), "manual_only_no_same_date_strategy_trade": c["UNMATCHED_MANUAL"], "automated_trades_without_counted_match": sum(1 for t in tt if t["trade_id"] not in ids_counted),
                       "automated_only_no_same_date_strategy_row": sum(1 for r in mt if r["config"] == k and r["match_stage"] == "AUTOMATED_ONLY" and r["auto_strategy"] == sname),
                       "counted_same_outcome": sum(1 for r in counted if r["outcome_class_agrees_descriptive"] == "True"), "counted_different_outcome": sum(1 for r in counted if r["outcome_class_agrees_descriptive"] != "True"),
                       "strict_pct_of_journal_rows_of_strategy": round(100 * c["STRICT"] / len(jr), 2) if jr else "", "strict_pct_of_automated_trades_of_strategy": round(100 * c["STRICT"] / len(tt), 2) if tt else ""})
    wr(OUT / "manual_match_breakdown.csv", br)
    (OUT / "exact_match_numbers.json").write_text(json.dumps(summary, indent=1))
    # ---------------------------------------------------------------- the workbook
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    idx = {(i["config"], i["trade_id"]): i for i in index}
    mtt = {(r["config"], r["trade_id"]): r for r in mt if r["trade_id"] and r["match_stage"] != "AUTOMATED_ONLY"}

    def sheet(name: str, header: list[str], data: list[list], link_col: int | None = None) -> None:
        ws = wb.create_sheet(name[:31])
        ws.append(header)
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="37474F")
        for r in data:
            ws.append(r)
        if link_col is not None:
            for row in ws.iter_rows(min_row=2, min_col=link_col, max_col=link_col):
                for c in row:
                    if c.value:
                        c.hyperlink = str(c.value)
                        c.font = Font(color="0563C1", underline="single")
        ws.freeze_panes = "A2"
        for i, h in enumerate(header, 1):
            ws.column_dimensions[get_column_letter(i)].width = min(max(len(h) + 2, 12), 48)
    th = ["configuration", "trade_id", "date", "strategy", "method", "direction", "signal_time (candle end)", "entry_time", "entry_price", "stop_loss", "T1", "T2", "post_T1_stop", "leg1_exit_time", "leg1_exit_price", "leg1_exit_reason", "leg2_exit_time",
          "leg2_exit_price", "leg2_exit_reason", "gross_points (weighted per unit)", "gross_synthetic_pnl_rs", "journal_match_type", "journal_row", "journal_outcome_label", "automated_exit_class", "outcome_agreement", "chart_file"]
    data = []
    for t in trades:
        k, tid = t["config"], t["trade_id"]
        lg = {g["leg"]: g for g in legs_by[(k, tid)]}
        i = idx[(k, tid)]
        m = mtt.get((k, tid))
        data.append([k, tid, t["date"], t["strategy"], t["method"], t["direction"], t["signal_confirmed_at"][-5:], t["fill_timestamp"][-5:], f(t["entry_price"]), f(t["initial_stop"]), f(t["target_1"]), f(t["target_2"]),
                     f(t["post_t1_stop"]) if lg["1"]["exit_reason"] == "TARGET_1" and t["post_t1_stop"] else "", lg["1"]["exit_time"][-5:], f(lg["1"]["exit_price"]), lg["1"]["exit_reason"], lg["2"]["exit_time"][-5:], f(lg["2"]["exit_price"]), lg["2"]["exit_reason"],
                     f(t["gross_pnl_points_weighted"]), f(t["gross_pnl_rs"]), i["match_status"], i["journal_row"], i["journal_outcome"], t["outcome"], "" if m is None else ("YES" if m["outcome_class_agrees_descriptive"] == "True" else "NO"),
                     i["chart_file"]])
    sheet("All executed trades", th, data, link_col=len(th))
    sheet("Exact matches only", th, [r for r in data if r[21] == "EXACT_MATCH"], link_col=len(th))
    sheet("Time-tolerant matches", th, [r for r in data if r[21] == "TIME_TOLERANT_MATCH"], link_col=len(th))
    sheet("Date+strategy only", th, [r for r in data if r[21] == "DATE_STRATEGY_ONLY"], link_col=len(th))
    sheet("Automated-only trades", th, [r for r in data if r[21] == "AUTOMATED_ONLY"], link_col=len(th))
    mh = list(mo[0].keys())
    sheet("Manual-only rows", mh, [[r.get(c, "") for c in mh] for r in mo])
    sheet("ORB mismatches", mh, [[r.get(c, "") for c in mh] for r in mo if r["manual_strategy"] == "ORB"])
    sh = list(rows[0].keys())
    sheet("Exact-match summary", sh, [[r[c] for c in sh] for r in rows])
    bh = list(br[0].keys())
    sheet("Breakdown by strategy", bh, [[r[c] for c in bh] for r in br])
    wb.save(OUT / "Phase57_Trade_Verification.xlsx")
    _ = (causes, hw, state)


if __name__ == "__main__":
    sys.exit(main())
