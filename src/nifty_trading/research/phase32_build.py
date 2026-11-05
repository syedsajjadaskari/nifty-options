"""Phase 3.2: assemble the explainable backtest bundle (trades, entry checks, exits, candles, signals, manual comparison, daily rows, issues).

The baseline is re-run through exactly the Phase 3.0 code path and every re-run ledger row is compared field by field with the frozen
``reports/phase3/baseline/trades.csv``; any difference is reported (and a test fails). Nothing here changes a rule, a parameter or a ledger.
"""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import subprocess
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from nifty_trading.core.execution_eligibility import (
    ENTRY_CUTOFF,
    bars_from_frame,
    entry_within_cutoff,
)
from nifty_trading.data.sessions import (
    build_session_contexts,
    load_daily_official,
    load_one_minute,
    load_warmup_one_minute,
)
from nifty_trading.research import phase3 as P
from nifty_trading.research import phase31 as R
from nifty_trading.research import phase32 as X
from nifty_trading.strategies.definitions import prev_candles, prev_high_low, to_candles
from nifty_trading.strategies.rules import RULE_BY_ID
from nifty_trading.strategies.selection import is_valid

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "reports" / "phase3" / "phase32"
P30 = ROOT / "reports" / "phase3" / "baseline" / "trades.csv"
P31 = ROOT / "reports" / "phase3" / "phase31"
STRATS = P.STRATEGIES


@dataclass
class Bundle:
    scenario: Any
    cfg_id: str
    days: list[date]
    timelines: dict[date, Any]
    infos: dict
    trades: list[dict] = field(default_factory=list)
    checks: list[dict] = field(default_factory=list)
    legs: list[dict] = field(default_factory=list)
    candles: list[dict] = field(default_factory=list)
    signals: list[dict] = field(default_factory=list)
    ignored: list[dict] = field(default_factory=list)
    rejected: list[dict] = field(default_factory=list)
    daily: list[dict] = field(default_factory=list)
    manual_cmp: list[dict] = field(default_factory=list)
    manual_norm: list[dict] = field(default_factory=list)
    issues: list[dict] = field(default_factory=list)
    explanations: dict[str, Any] = field(default_factory=dict)  # trade_id -> Explanation
    inputs: dict[date, Any] = field(default_factory=dict)  # day -> DayInputs
    trade_objs: dict[str, Any] = field(default_factory=dict)  # trade_id -> TradeRecord
    ledger_check: dict = field(default_factory=dict)
    ledger: list[dict] = field(default_factory=list)
    provenance: dict = field(default_factory=dict)
    prior_counts: dict = field(default_factory=dict)
    phase_label: str = "Phase 3.2"  # shown in the workbook title and the daily journals
    banner: str = "Automated, read-only reconstruction of the Phase 3.0 baseline."
    pdr_engine: str = "LEGACY"
    has_journal: bool = True  # False for periods without a manual journal (Phase 4 historical windows): no journal comparison, no 'extra automated trade' labels
    revised_pdr: bool = False  # True when the Phase 3.4 revised PDR engine fed the controller (the Phase 3.0 ledger is then expected to differ)


def partition_of(day: date) -> str:
    return f"data/processed/nifty50/year={day.year}/month={day.month:02d}/candles.parquet"


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
    ledgers = {f"reports/phase3/{s}/trades.csv": sha256(ROOT / "reports" / "phase3" / s / "trades.csv") for s in ("baseline", "ema_structure", "pdr_shelf", "sl40")
               if (ROOT / "reports" / "phase3" / s / "trades.csv").exists()}
    return {"python": platform.python_version(), "timezone": "Asia/Kolkata", "calendar": "NSE calendar 2025-26 (data/metadata/nse_calendar_2025_2026.json)",
            "git_head": git("rev-parse", "HEAD"), "git_dirty_files": len(git("status", "--short").splitlines()), "src_sha256": src_hash.hexdigest(),
            "src_snapshot_note": "the working tree holds uncommitted Phase 2.x-3.x work; src_sha256 is the hash of every src/**/*.py file used for this run",
            "data_files_sha256": data, "metadata_sha256": meta, "phase30_ledgers_sha256": ledgers,
            "price_source": "original NIFTY 50 one-minute bars (timestamp = bar START, IST); 5-minute candles built causally from them; first 1-minute open is the session open",
            "period": "2025-09-01 .. 2026-08-31"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def ledger_matches_phase30(rows: list[dict]) -> dict:
    """Field-by-field comparison of the re-run ledger with the frozen Phase 3.0 baseline trades.csv."""
    with open(P30, newline="") as f:
        frozen = list(csv.DictReader(f))
    diffs = []
    if len(frozen) != len(rows):
        diffs.append(f"row count {len(rows)} != frozen {len(frozen)}")
    key = lambda r: (r["date"], str(r["trade_no"]))  # noqa: E731
    fz = {key(r): r for r in frozen}
    for r in rows:
        f = fz.get(key(r))
        if f is None:
            diffs.append(f"{key(r)} missing in frozen ledger")
            continue
        for k, v in r.items():
            if k == "scenario":
                continue  # the scenario LABEL differs by construction (baseline vs phase35_*); every numeric/time/outcome field is compared
            if k in f and _s(v) != f[k]:
                try:
                    if abs(float(v) - float(f[k])) < 1e-9:
                        continue
                except (TypeError, ValueError):
                    pass
                diffs.append(f"{key(r)} {k}: {_s(v)} != {f[k]}")
    return {"frozen_rows": len(frozen), "rerun_rows": len(rows), "identical": not diffs, "differences": diffs[:50], "n_differences": len(diffs),
            "frozen_sha256": sha256(P30)}


def load_manual(sessions: dict[str, str]):
    p21 = json.loads((ROOT / "reports" / "phase21" / "journal_reconciliation.json").read_text())
    alt = {}
    for k, v in p21["attribution_hypotheses"].items():
        if "candidate_rows" in v:
            for c in v["candidate_rows"]:
                alt[int(c["sheet_row"])] = "PDR" if k == "feb_2026" else ("ORB" if k == "jun_2026" else "")
    alt = {k: v for k, v in alt.items() if v}
    return R.normalize_journal(R.load_journal(), p21["rows"], alt, sessions)


def chart_inputs(tr, ex, sig, r) -> dict:
    lv = sig.reference_levels
    hl: list[tuple[str, float | None, str]] = []
    for key, label, col in (("IRH", "IRH", "#1565c0"), ("IRL", "IRL", "#1565c0"), ("RF_High", "RF High", "#1565c0"), ("RF_Low", "RF Low", "#1565c0"), ("prev_day_high", "prev-day high", "#b71c1c"),
                            ("prev_day_low", "prev-day low", "#1b5e20"), ("level_broken", "ORB level broken", "#6a1b9a"), ("inner_level", "ORB inner level", "#6a1b9a"),
                            ("recent_support", "recent support", "#00838f"), ("recent_resistance", "recent resistance", "#ad1457"), ("small_support", "PDS small support", "#00838f")):
        v = lv.get(key)
        if isinstance(v, (int, float)):
            hl.append((label, float(v), col))
    zones = []
    if "zone" in ex.levels:
        lo, hi, name = ex.levels["zone"]
        zones.append((name, lo, hi, "#ef6c00" if sig.strategy == "PDS" else "#1565c0"))
    return {"hlines": hl, "zones": zones}


def build(progress=None, scenario=None, *, data=None, journal: bool = True, partition_fn=None, provenance_override: dict | None = None) -> Bundle:  # noqa: C901
    """``data`` = None reads the Phase 1 dataset exactly as before. A Phase 4 caller passes an object with ``ctxs``, ``infos``, ``bars`` (built from another source and calendar) and ``journal=False``
    (no manual journal exists for that period); ``partition_fn(date)`` names the source partition of a bar (default: the Phase 1 layout) and ``provenance_override`` replaces the data hashes."""
    if data is None:
        m1 = load_one_minute()
        ctxs, infos = build_session_contexts(m1, daily_df=load_daily_official(), warmup_1m=load_warmup_one_minute())
        m1 = m1.assign(_d=m1.timestamp.dt.date)
        bars = {d: bars_from_frame(g) for d, g in m1.groupby("_d")}
    else:
        ctxs, infos, bars = data.ctxs, data.infos, data.bars
    partition_of = partition_fn or globals()["partition_of"]  # noqa: F841 - shadows the module function inside this build only
    sc = scenario or P.scenarios()["baseline"]
    revised = sc.pdr_engine in P.NON_LEGACY_PDR
    body = sc.pdr_engine == "BODY_BASED_PHASE36"
    tls = R.run_timelines(sc, ctxs, bars)
    cfg_id = X.config_id(sc.proposals, sc.trade, sc.key, sc.pdr_revision if revised else None)
    b = Bundle(sc, cfg_id, sorted(tls), tls, infos)
    b.pdr_engine = sc.pdr_engine
    if body:
        b.phase_label = "Phase 3.6"
        b.banner = ("Automated reconstruction of the Phase 3.6 combined backtest: the Phase 3.0 controller, stops, targets and sizing with PDR = the body-based engine (wicks ignored; open strictly above the zone; "
                    "numeric pattern thresholds and zone-lower-boundary conventions are provisional research assumptions, NOT approved by the strategy author).")
        b.revised_pdr = True
    elif revised:
        b.phase_label = "Phase 3.5"
        b.banner = ("Automated reconstruction of the Phase 3.5 combined backtest: the Phase 3.0 controller, stops, targets and sizing with PDR = the Phase 3.4 revised engine "
                    "(provisional pattern thresholds and open-above-zone assumption, NOT approved by the strategy author).")
        b.revised_pdr = True
    b.provenance = provenance_override if provenance_override is not None else provenance()
    b.has_journal = journal
    # ------------------------------------------------------------------ manual journal and matching (Phase 3.1 methodology, unchanged)
    sessions = {str(d): infos[d].quality.value for d in infos}
    manual = load_manual(sessions) if journal else []
    b.manual_norm = manual
    matched_rows, used = R.match_manual_to_automated(manual, tls, sc.proposals)
    for r in matched_rows:
        r["root_cause_primary"], r["root_cause_secondary"] = R.root_cause_manual(r)
    by_trade: dict[tuple[str, int], dict] = {(r["date"], int(r["auto_trade_no"])): r for r in matched_rows if r["classification"] in ("EXACT_MATCH", "TIME_SHIFTED_MATCH")}
    manual_by_day: dict[str, list[dict]] = defaultdict(list)
    for m in manual:
        manual_by_day[m["date"]].append(m)
    # ------------------------------------------------------------------ per-day, per-trade
    ledger_rows: list[dict] = []
    for d in b.days:
        tl = tls[d]
        inp = X.DayInputs(d, tl.ctx, to_candles(tl.ctx.candles), tl.records, tl.result, bars[d], sc.proposals, sc.trade)
        b.inputs[d] = inp
        for tr in tl.result.trades:
            ex = X.explain_trade(d, tr, inp)
            legs, narrative, prog = X.explain_exits(d, tr, bars[d], sc.trade)
            row = X.trade_row(d, tr, inp, ex, legs, narrative, prog, cfg_id, partition_of(d))
            mrow = by_trade.get((str(d), tr.trade_no))
            row.update({"manual_journal_row": mrow["journal_row"] if mrow else "", "manual_match_class": mrow["classification"] if mrow else ("NO_MANUAL_COUNTERPART" if journal else "NOT_APPLICABLE_NO_JOURNAL_FOR_PERIOD"),
                        "manual_time_label": mrow["entry_time_label"] if mrow else "", "manual_outcome": mrow["exit_classification_entered"] if mrow else ""})
            b.trades.append(row)
            b.explanations[ex.trade_id] = ex
            b.trade_objs[ex.trade_id] = tr
            ledger_rows.append(P.ledger_row(sc.key, d, tr, tl.result))
            for c in ex.checks:
                b.checks.append(asdict(c))
            for lg in legs:
                bar = lg.source_bar
                b.legs.append({
                    "trade_id": lg.trade_id, "leg": lg.leg, "quantity": lg.qty, "entry_price": lg.entry_price, "exit_time": f"{lg.exit_ts:%Y-%m-%d %H:%M}" if lg.exit_ts else "",
                    "exit_price": lg.exit_price, "exit_reason": lg.reason, "exit_trigger_evidence": lg.trigger_text,
                    "exit_source_partition": partition_of(d) if bar else "", "exit_source_bar_ts": f"{bar.ts:%Y-%m-%d %H:%M}" if bar else "", "exit_bar_interval": "1-minute" if bar else "",
                    "exit_bar_open": bar.o if bar else None, "exit_bar_high": bar.h if bar else None, "exit_bar_low": bar.l if bar else None, "exit_bar_close": bar.c if bar else None,
                    "exit_execution_rule": ("stop fills at the worse of the level and the bar open (gap = adverse slippage logged); targets fill at their level; stop tested before target inside a 1-minute bar"
                                            if bar else "none"),
                    "original_stop": tr.result.stop_level, "target_1": tr.result.t1_level, "target_2": tr.result.t2_level,
                    "post_t1_stop": tr.result.post_t1_stop_level, "t1_booked_before_this_leg": bool(tr.result.post_t1_stop_level is not None and lg.reason != "TARGET_1"),
                    "stop_change_time": f"{tr.result.leg1_ts:%Y-%m-%d %H:%M}" if tr.result.post_t1_stop_level is not None and lg.leg == 2 else "",
                    "gross_pnl_points": None if lg.gross_pnl_rs is None else lg.gross_pnl_rs / lg.qty, "gross_pnl_rs": lg.gross_pnl_rs, "adverse_slippage_points": lg.slippage_points,
                    "flags": ";".join(lg.flags), "provisional_rule": "FORCED_EXIT_1514_OPEN is an implementer assumption awaiting owner approval" if "PROVISIONAL" in lg.reason else ""})
            for cr in ex.candles:
                m = X.candle_metrics(cr.candle, sc.proposals)
                b.candles.append({"trade_id": ex.trade_id, "role": cr.role, "session": cr.session, "used_for": cr.used_for, "candle_start": f"{cr.candle.start:%Y-%m-%d %H:%M}",
                                  "candle_end": f"{cr.candle.end:%Y-%m-%d %H:%M}", "available_at": f"{cr.candle.end:%Y-%m-%d %H:%M}", "source_partition": partition_of(cr.candle.start.date()),
                                  **{k: (None if v is None else (round(v, 4) if isinstance(v, float) else v)) for k, v in m.items()}})
    b.ledger_check = ledger_matches_phase30(ledger_rows)
    b.ledger = ledger_rows
    # ------------------------------------------------------------------ signals (every engine record), ignored, rejected
    for d in b.days:
        tl = tls[d]
        rows = R.timeline_rows(tl, "baseline", [])
        conf_rows: dict[tuple, list[dict]] = defaultdict(list)
        for x in rows:
            if x["signal_status"] == "CONFIRMED":
                conf_rows[(x["strategy"], x["method"], x["direction"], x["time"])].append(x)
        executed = {(t.signal.signal_timestamp, t.signal.strategy, t.signal.method, t.signal.direction): X.trade_id_of(d, t) for t in tl.result.trades}
        n = 0
        for r in sorted((r for r in tl.records if r.signal_status == "CONFIRMED" and r.signal_timestamp is not None), key=lambda r: (r.signal_timestamp, r.strategy, r.method)):
            n += 1
            lst = conf_rows.get((r.strategy, r.method, r.direction, f"{r.signal_timestamp:%H:%M}"), [])
            x = lst.pop(0) if lst else {"event": "NOT_LOGGED", "disposition_reason": "", "blocked_by": "", "portfolio_state": ""}
            valid, why = is_valid(r)
            row = {"signal_id": f"{d:%Y%m%d}-S{n:03d}", "date": str(d), "time": f"{r.signal_timestamp:%H:%M}", "candle_start": f"{r.signal_candle_start:%H:%M}", "strategy": r.strategy,
                   "method": r.method, "direction": r.direction, "reference_close": r.signal_candle_close, "entry_rule_status": r.execution_config.get("entry_rule_status", ""),
                   "verification_status": r.verification_status, "fully_valid_for_execution": bool(valid), "validity_note": "" if valid else why,
                   "within_13_00_cutoff": bool(entry_within_cutoff(r.signal_timestamp, ENTRY_CUTOFF)), "portfolio_state_at_signal": x["portfolio_state"],
                   "controller_event": x["event"], "controller_reason": x["disposition_reason"], "blocked_by": x["blocked_by"],
                   "trade_id": executed.get((r.signal_timestamp, r.strategy, r.method, r.direction), ""),
                   "competing_signals_same_minute": "; ".join(f"{o.strategy} {o.method} {o.direction}" for o in tl.records if o is not r and o.signal_status == "CONFIRMED" and o.signal_timestamp == r.signal_timestamp),
                   "rules_satisfied": ";".join(r.rule_ids_satisfied), "rules_unresolved": ";".join(r.rule_ids_unresolved), "reference_levels": json.dumps(r.reference_levels, default=str),
                   "state_trace": " | ".join(r.state_trace)}
            b.signals.append(row)
            if x["event"] == "IGNORED":
                b.ignored.append({k: row[k] for k in ("signal_id", "date", "time", "strategy", "method", "direction", "portfolio_state_at_signal", "controller_reason", "blocked_by", "competing_signals_same_minute")})
            elif x["event"] in ("REJECTED", "CONFLICT"):
                b.rejected.append({"record_id": row["signal_id"], "category": "CONTROLLER_REJECTED" if x["event"] == "REJECTED" else "CONTROLLER_CONFLICT", "date": str(d), "time": row["time"],
                                   "strategy": r.strategy, "method": r.method, "direction": r.direction, "failure_reason": x["disposition_reason"], "failed_rule_ids": "", "failed_rule_names": "",
                                   "rules_satisfied_count": len(r.rule_ids_satisfied), "rules_satisfied": ";".join(r.rule_ids_satisfied), "rules_unresolved": ";".join(r.rule_ids_unresolved),
                                   "last_state": r.state_trace[-1] if r.state_trace else "", "reference_levels": row["reference_levels"]})
        m_ = 0
        for r in tl.records:
            if r.signal_status == "CONFIRMED":
                continue
            m_ += 1
            names = "; ".join(f"{rid}: {RULE_BY_ID[rid]['description']}" for rid in r.rule_ids_failed if rid in RULE_BY_ID)
            cat = {"INVALIDATED": "ENGINE_SETUP_INVALIDATED", "INCOMPLETE_AT_EOD": "ENGINE_SETUP_INCOMPLETE_AT_EOD", "NOT_EVALUATED": "ENGINE_NOT_EVALUATED"}[r.signal_status]
            b.rejected.append({"record_id": f"{d:%Y%m%d}-R{m_:03d}", "category": cat, "date": str(d), "time": f"{r.signal_candle_start:%H:%M}" if r.signal_candle_start else "",
                               "strategy": r.strategy, "method": r.method, "direction": r.direction, "failure_reason": r.invalidation_reason or "", "failed_rule_ids": ";".join(r.rule_ids_failed),
                               "failed_rule_names": names, "rules_satisfied_count": len(r.rule_ids_satisfied), "rules_satisfied": ";".join(r.rule_ids_satisfied), "rules_unresolved": ";".join(r.rule_ids_unresolved),
                               "last_state": r.state_trace[-1] if r.state_trace else "", "reference_levels": json.dumps(r.reference_levels, default=str)})
    # ------------------------------------------------------------------ manual comparison (190 manual rows + the extra automated trades)
    trade_by_key = {(t["date"], t["trade_no_of_day"]): t for t in b.trades}
    for r in matched_rows:
        t = trade_by_key.get((r["date"], int(r["auto_trade_no"]))) if r.get("auto_trade_no") not in (None, "") else None
        matched = r["classification"] in ("EXACT_MATCH", "TIME_SHIFTED_MATCH")
        if matched:
            expl = (f"{r['classification']}: manual {r['strategy_normalized']} labelled {r['entry_time_label']} (candle start) vs automated {t['strategy']} {t['method']} {t['direction']} candle {t['signal_candle_start']}, "
                    f"filled {t['fill_timestamp'][-5:]} at {t['entry_price']:,.2f}; time difference {r['delta_minutes']} minutes"
                    + ("; matched under the alternate (Phase 2.1 attribution) strategy label" if r["matched_via_alternate_label"] else "")
                    + f". Journal outcome {r['exit_classification_entered']} vs automated {t['outcome']} ({'same outcome class' if r['outcome_agrees_loosely'] else 'different outcome class - the stop rules may differ'}). The journal records no entry or exit price.")
        else:
            why = f"{r['classification']}: {r.get('chain', '')}" + (f" - {r['detail']}" if r.get("detail") else "")
            rc = r.get("root_cause_primary") or "UNKNOWN"
            expl = why + f". Heuristic primary cause: {rc}" + (" (the evidence does not decide - UNKNOWN)" if rc == "UNKNOWN" else "") + f"; blocked by: {r.get('blocked_by') or 'n/a'}"
        b.manual_cmp.append({
            "comparison_id": f"M{int(r['journal_row']):03d}", "journal_row": r["journal_row"], "date": r["date"], "weekday": date.fromisoformat(r["date"]).strftime("%A"),
            "journal_strategy_entered": next(m["strategy_entered"] for m in manual if m["journal_row"] == r["journal_row"]), "journal_strategy": r["strategy_normalized"],
            "manual_entry_time_label": r["entry_time_label"], "manual_direction": r["direction"], "manual_entry_price": "NOT_RECORDED", "manual_outcome": r["exit_classification_entered"],
            "manual_exit_price": "NOT_RECORDED", "match_classification": r["classification"], "trade_id": t["trade_id"] if t else "", "auto_strategy": t["strategy"] if t else "",
            "auto_method": t["method"] if t else "", "auto_direction": t["direction"] if t else "", "auto_entry_time": t["fill_timestamp"][-5:] if t else "", "auto_entry_price": t["entry_price"] if t else None,
            "auto_outcome": t["outcome"] if t else "", "auto_leg1_exit": f"{t['leg1_exit_time']} @ {t['leg1_exit_price']}" if t else "", "auto_leg2_exit": f"{t['leg2_exit_time']} @ {t['leg2_exit_price']}" if t else "",
            "delta_minutes": r.get("delta_minutes", ""), "matched_via_alternate_label": r.get("matched_via_alternate_label", False), "outcome_agrees_loosely": r.get("outcome_agrees_loosely", ""),
            "chain": r.get("chain", ""), "blocked_by": r.get("blocked_by", ""), "detail": r.get("detail", ""), "root_cause_primary": r.get("root_cause_primary", ""),
            "root_cause_secondary": r.get("root_cause_secondary", ""), "explanation": expl, "phase21_status": r["phase21_status"], "conforms_to_approved_rules": r["conforms_to_approved_rules"],
            "nonconformity": r["nonconformity"], "owner_review_status": ""})
    matched_keys = {(r["date"], int(r["auto_trade_no"])) for r in matched_rows if r["classification"] in ("EXACT_MATCH", "TIME_SHIFTED_MATCH")}
    n_extra = 0
    for t in b.trades:
        if not journal or (t["date"], t["trade_no_of_day"]) in matched_keys:
            continue
        n_extra += 1
        md = manual_by_day.get(t["date"], [])
        same = [m for m in md if m["strategy_normalized"] == t["strategy"]]
        other = [m for m in md if m["strategy_normalized"] != t["strategy"]]
        ctxs_ = "SAME_STRATEGY_MANUAL_TRADE_AT_ANOTHER_TIME" if same else ("MANUAL_TRADED_ONLY_OTHER_STRATEGIES" if other else "NO_MANUAL_TRADE_THAT_DAY")
        expl = (f"EXTRA_AUTOMATED_TRADE: the automated system took {t['strategy']} {t['method']} {t['direction']} at {t['fill_timestamp'][-5:]} ({ctxs_.replace('_', ' ').lower()}"
                + (": " + "; ".join(f"{m['strategy_normalized']} {m['entry_time_label']} {m['exit_classification_entered']}" for m in (same or other)) if md else "")
                + "). The setup rests on: " + (t["unresolved_items"] or "no unresolved rule") + ". The journal shows no corresponding entry.")
        b.manual_cmp.append({
            "comparison_id": f"E{n_extra:03d}", "journal_row": "", "date": t["date"], "weekday": t["weekday"], "journal_strategy_entered": "", "journal_strategy": "", "manual_entry_time_label": "",
            "manual_direction": "", "manual_entry_price": "", "manual_outcome": "", "manual_exit_price": "", "match_classification": "EXTRA_AUTOMATED_TRADE", "trade_id": t["trade_id"],
            "auto_strategy": t["strategy"], "auto_method": t["method"], "auto_direction": t["direction"], "auto_entry_time": t["fill_timestamp"][-5:], "auto_entry_price": t["entry_price"],
            "auto_outcome": t["outcome"], "auto_leg1_exit": f"{t['leg1_exit_time']} @ {t['leg1_exit_price']}", "auto_leg2_exit": f"{t['leg2_exit_time']} @ {t['leg2_exit_price']}", "delta_minutes": "",
            "matched_via_alternate_label": False, "outcome_agrees_loosely": "", "chain": ctxs_, "blocked_by": "", "detail": "", "root_cause_primary": "", "root_cause_secondary": "",
            "explanation": expl, "phase21_status": "", "conforms_to_approved_rules": "", "nonconformity": "", "owner_review_status": ""})
    # ------------------------------------------------------------------ daily rows
    trades_by_day: dict[str, list[dict]] = defaultdict(list)
    for t in b.trades:
        trades_by_day[t["date"]].append(t)
    cmp_by_day: dict[str, list[dict]] = defaultdict(list)
    for c in b.manual_cmp:
        cmp_by_day[c["date"]].append(c)
    for d in b.days:
        tl, info, ctx = tls[d], infos[d], tls[d].ctx
        ts = trades_by_day.get(str(d), [])
        cm = cmp_by_day.get(str(d), [])
        man = manual_by_day.get(str(d), [])
        prev = ctx.previous
        ph, pl = prev_high_low(prev, sc.proposals) if prev is not None else (None, None)
        confirmed = [r for r in tl.records if r.signal_status == "CONFIRMED"]
        valid = [r for r in confirmed if is_valid(r)[0]]
        unmatched = [c for c in cm if c["journal_row"] != "" and c["match_classification"] not in ("EXACT_MATCH", "TIME_SHIFTED_MATCH")]
        extras = [c for c in cm if c["match_classification"] == "EXTRA_AUTOMATED_TRADE"]
        shifted = [c for c in cm if c["match_classification"] == "TIME_SHIFTED_MATCH"]
        flags = []
        if unmatched:
            flags.append("UNMATCHED_MANUAL")
        if extras:
            flags.append("EXTRA_AUTOMATED")
        if shifted:
            flags.append("TIME_SHIFTED")
        if any(t["execution_ambiguities"] for t in ts):
            flags.append("EXECUTION_AMBIGUITY")
        if any(t["outcome"] == "FORCED_EXIT" for t in ts):
            flags.append("PROVISIONAL_FORCED_EXIT")
        if any(t["recomputation_mismatches"] for t in ts):
            flags.append("EXPLANATION_MISMATCH")
        if any(x.event == "CONFLICT" for x in tl.result.diagnostics) or tl.result.final_state.value == "UNRESOLVED_EXECUTION":
            flags.append("SIMULTANEOUS_SIGNAL_CONFLICT" if any(x.event == "CONFLICT" for x in tl.result.diagnostics) else "UNRESOLVED_EXECUTION")
        if any(not m["conforms_to_approved_rules"] for m in man):
            flags.append("JOURNAL_NONCONFORMING")
        not_eval = sorted({f"{r.strategy}: {r.invalidation_reason or ''}" for r in tl.records if r.signal_status == "NOT_EVALUATED"})
        if not_eval:
            flags.append("PARTIAL_STRATEGY_COVERAGE")
        triage = (("REVIEW: " + "+".join(flags)) if flags else ("NO_TRADE_BOTH" if not ts and not man else ("MATCHED_EXACT_NO_FLAGS" if ts else "NO_FLAGS"))) if journal else \
            (("REVIEW: " + "+".join(flags)) if flags else ("TRADED_NO_FLAGS" if ts else "NO_TRADE"))
        gross = sum(t["gross_pnl_rs"] for t in ts)
        net = sum(t["illustrative_net_pnl_rs"] for t in ts)
        b.daily.append({
            "date": str(d), "weekday": f"{d:%A}", "session_type": f"{info.status.value} / {info.quality.value}" + (" / CLOSING_AUCTION_REGIME" if info.cas_regime else "") + (" / WEEKEND_SPECIAL_SESSION" if d.weekday() >= 5 else ""),
            "original_session_open": ctx.open_price, "previous_session": str(prev.date) if prev else "", "prev_day_high": ph, "prev_day_low": pl, "prev_day_official_close": prev.close_official if prev else None,
            "prev_day_last_5m_close": prev.last_5m_close if prev else None, "raw_engine_records": len(tl.records), "confirmed_signals": len(confirmed), "fully_valid_signals": len(valid),
            "setups_not_confirmed": sum(1 for r in tl.records if r.signal_status in ("INVALIDATED", "INCOMPLETE_AT_EOD")), "executed_trades": len(ts),
            "trade_ids": ";".join(t["trade_id"] for t in ts), "strategies_traded": ";".join(t["strategy"] for t in ts), "gross_pnl_rs": gross, "illustrative_net_pnl_rs": net,
            "strategies_not_evaluated": " | ".join(not_eval), "day_end_portfolio_state": tl.result.final_state.value, "manual_journal_trades": len(man), "manual_matched": sum(1 for c in cm if c["journal_row"] != "" and c["match_classification"] in ("EXACT_MATCH", "TIME_SHIFTED_MATCH")),
            "manual_unmatched": len(unmatched), "extra_automated_trades": len(extras), "automated_review_flag": triage, "owner_review_status": ""})
        if b.pdr_engine == "BODY_BASED_PHASE36" and prev is not None:  # the PDR ceiling of this engine is the highest BODY high, not the wick high shown above
            b.daily[-1]["prev_day_highest_body_high"] = max(max(c.o, c.c) for c in to_candles(prev_candles(prev, sc.proposals)))
    # ------------------------------------------------------------------ verification issues
    iss = b.issues
    ino = 0

    def add(sev, cat, d, tid, jr, strat, desc, evid, action=""):
        nonlocal ino
        ino += 1
        iss.append({"issue_id": f"I{ino:04d}", "severity": sev, "category": cat, "date": d, "trade_id": tid, "journal_row": jr, "strategy": strat, "description": desc, "evidence": evid,
                    "suggested_owner_action": action, "owner_status": "", "owner_comment": ""})
    for m in manual:
        if not m["conforms_to_approved_rules"]:
            add("HIGH", "JOURNAL_NONCONFORMING", m["date"], "", m["journal_row"], m["strategy_normalized"], f"journal row does not conform to the approved portfolio rules: {m['nonconformity']}",
                f"{m['strategy_entered']} {m['entry_time_label']} {m['exit_classification_entered']}", "decide whether to keep, correct or exclude this row in comparisons")
    for c in b.manual_cmp:
        if c["journal_row"] != "" and c["match_classification"] not in ("EXACT_MATCH", "TIME_SHIFTED_MATCH"):
            unknown = (c["root_cause_primary"] or "UNKNOWN") == "UNKNOWN"
            add("HIGH" if unknown else "MEDIUM", "UNMATCHED_MANUAL_TRADE", c["date"], "", c["journal_row"], c["journal_strategy"],
                f"manual trade without an automated counterpart ({c['match_classification']}); primary cause: {c['root_cause_primary'] or 'UNKNOWN'}", c["explanation"],
                "owner to say which discretionary condition differed" if unknown else "")
        elif c["match_classification"] == "TIME_SHIFTED_MATCH":
            add("INFO", "TIME_SHIFTED_MATCH", c["date"], c["trade_id"], c["journal_row"], c["journal_strategy"], f"matched with a {c['delta_minutes']}-minute difference (tolerance 15)", c["explanation"],
                "confirm that the journal label refers to this automated trade")
        if c["matched_via_alternate_label"]:
            add("MEDIUM", "ALTERNATE_LABEL_MATCH", c["date"], c["trade_id"], c["journal_row"], c["journal_strategy"], "matched under the alternate strategy label from the Phase 2.1 attribution hypotheses", c["explanation"],
                "confirm the strategy of this journal row")
        if c["match_classification"] == "EXTRA_AUTOMATED_TRADE":
            add("MEDIUM", "EXTRA_AUTOMATED_TRADE", c["date"], c["trade_id"], "", c["auto_strategy"], "automated trade with no journal counterpart", c["explanation"], "")
    for t in b.trades:
        ex = b.explanations[t["trade_id"]]
        if t["execution_ambiguities"]:
            add("MEDIUM", "EXECUTION_AMBIGUITY", t["date"], t["trade_id"], t["manual_journal_row"], t["strategy"], "stop/target touched in the same 1-minute bar or in a non-executable bar; resolved adversely",
                t["exit_narrative"][-300:], "")
        if t["outcome"] == "FORCED_EXIT":
            add("MEDIUM", "PROVISIONAL_FORCED_EXIT", t["date"], t["trade_id"], t["manual_journal_row"], t["strategy"], "position closed by the provisional 15:14 minute-open forced exit", t["exit_narrative"][-300:],
                "approve or replace the forced-exit convention")
        if not t["resolved"]:
            add("HIGH", "UNRESOLVED_EXIT", t["date"], t["trade_id"], t["manual_journal_row"], t["strategy"], "exit could not be resolved from fillable bars", t["exit_narrative"][-300:], "")
        if t["recomputation_mismatches"]:
            add("HIGH", "EXPLANATION_RECOMPUTATION_MISMATCH", t["date"], t["trade_id"], t["manual_journal_row"], t["strategy"], "a recomputed number disagrees with the engine's record", t["recomputation_mismatches"], "")
        for c in ex.checks:
            if c.rule_id == "PDR-007" and c.group == "NOTE" and "BELOW the zone floor" in c.observed:
                add("INFO", "PDR_ZONE_DID_NOT_HOLD_BUT_ENTERED", t["date"], t["trade_id"], t["manual_journal_row"], "PDR", "the confirmation candle closed below the zone floor; the engine does not test that the zone held", c.observed, "owner decision on the PDR hold test")
            if c.rule_id == "PDS-M3-001" and "distance below the zone floor" in c.observed:
                dist = float(c.observed.split("distance below the zone floor ")[1].split(" ")[0].replace(",", ""))
                if dist > 10:
                    add("INFO", "PDS_M3_SUPPORT_FAR_FROM_ZONE", t["date"], t["trade_id"], t["manual_journal_row"], "PDS", f"Method 3 small support is {dist:.2f} points below the zone floor (the guide defines no 'near' distance)", c.observed, "owner decision on 'near'")
    for d in b.days:
        for x in tls[d].result.diagnostics:
            if x.event == "CONFLICT":
                add("HIGH", "SIMULTANEOUS_SIGNAL_CONFLICT", str(d), "", "", x.strategy, "different strategies signalled in the same minute; no approved tie-break, the day is marked unresolved and nothing is traded", x.reason, "approve a tie-break policy or keep the convention")
    b.prior_counts = json.loads((P31 / "reconciliation_counts.json").read_text()) if (P31 / "reconciliation_counts.json").exists() else {}
    for name in ("trades", "checks", "legs", "candles", "signals", "ignored", "rejected", "daily", "manual_cmp", "manual_norm", "issues"):
        for row in getattr(b, name):
            for k, v in row.items():
                if isinstance(v, float):
                    row[k] = round(v, 6)  # removes binary float noise (26.150000000001455) from the exports; the frozen-ledger comparison above used the unrounded values
    return b


def counts_vs_phase31(b: Bundle) -> dict:
    """Re-verify the Phase 3.1 headline figures from the freshly built bundle."""
    p = b.prior_counts
    cls = Counter(c["match_classification"] for c in b.manual_cmp if c["journal_row"] != "")
    out = {"manual_rows": sum(cls.values()), "exact": cls["EXACT_MATCH"], "time_shifted": cls["TIME_SHIFTED_MATCH"], "extras": sum(1 for c in b.manual_cmp if c["match_classification"] == "EXTRA_AUTOMATED_TRADE"),
           "automated_trades": len(b.trades), "classification": dict(cls)}
    out["phase31"] = {k: p.get(k) for k in ("manual_rows", "exact", "time_shifted", "extra_automated", "automated_trades_baseline")}
    out["classification_equal_to_phase31"] = {k: v for k, v in (p.get("classification_baseline") or {}).items()} == {k: v for k, v in cls.items()}
    return out
