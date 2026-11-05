"""Phase 4: the FROZEN Phase 3.6 five-strategy portfolio run over other historical windows, plus the multi-year metrics.

No new backtesting engine: this is the Phase 3.6 scenario (``phase3.combined_scenario("BODY_BASED_PHASE36")``: IRF, ORB, PDR body-based, PDS, RF through the shared Phase 3.0 controller) through the Phase 3.2
explainable-backtest framework, fed by a different data source and a date-aware derived calendar (``phase4_data``). Nothing about a strategy, a stop, a target, the cutoff, the lot split or the controller is configurable here.
All P&L is SYNTHETIC index-point P&L x a fixed 390-unit comparison multiplier (the NIFTY 50 index is not tradable; historical lot sizes differ).
"""

from __future__ import annotations

import json
import math
import statistics
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from nifty_trading.research import phase3 as P
from nifty_trading.research import phase4_data as D
from nifty_trading.research import phase32_build as B
from nifty_trading.research import phase32_render as RN
from nifty_trading.research.phase35 import write_csv

ROOT = D.ROOT
OUT = ROOT / "reports" / "phase4"
FROZEN_SCENARIO_ENGINE = "BODY_BASED_PHASE36"
FIXED_MULTIPLIER = 390  # 6 lots x 65 units: a fixed comparison multiplier, NOT a claim about historical contract sizes
BASE_COST = (500.0, 0.5)  # Phase 3.6 headline illustrative cost: Rs 500 per trade + 0.5 index point adverse slippage on every fill
COST_GRID_FIXED = (0.0, 500.0, 1000.0, 1500.0)
COST_GRID_SLIP = (0.0, 0.5, 1.0, 2.0)
HYPOTHETICAL_CAPITAL = (100000.0, 500000.0)  # stated hypothetical levels for drawdown context only; neither is claimed sufficient for six derivative lots


@dataclass(frozen=True)
class RunSpec:
    window_id: str
    label: str
    start: date
    end: date
    minute_source: str
    daily_source: str = D.SRC_5P_DAILY
    status: str = "DATA_VALIDATED"  # DATA_VALIDATED (the data window passed the quality gate; says nothing about the strategy) | EXPLORATORY | PARTIAL_YEAR | VENDOR_SENSITIVITY | CUSTOM
    note: str = ""


SPECS = {
    "B": RunSpec("B", "Window B 2022-09-01..2025-08-31 (5paisa minutes)", date(2022, 9, 1), date(2025, 8, 31), D.SRC_5P_MIN, status="DATA_VALIDATED",
                 note="same provider as the Phase 3.6 baseline; the vendor-overlap audit shows the minute bars differ from the secondary vendor"),
    "B_TV": RunSpec("B_TV", "Window B 2022-09-01..2025-08-31 (secondary vendor minutes)", date(2022, 9, 1), date(2025, 8, 31), D.SRC_TV_MIN, status="VENDOR_SENSITIVITY",
                    note="the same window with the secondary vendor's minute bars (daily series still 5paisa): quantifies sensitivity to the data source; not a second independent result"),
    "C": RunSpec("C", "Window C 2018-01-01..2018-12-31 (secondary vendor minutes)", date(2018, 1, 1), date(2018, 12, 31), D.SRC_TV_MIN, status="EXPLORATORY",
                 note="the only minute source for 2018 is the secondary vendor; 5paisa returns no minute data before 2019-03-01, so there is NO overlap with another vendor to check it against"),
    "D_5P": RunSpec("D_5P", "Window D 2019-03-01..2019-12-31 (5paisa minutes, PARTIAL YEAR)", date(2019, 3, 1), date(2019, 12, 31), D.SRC_5P_MIN, status="PARTIAL_YEAR",
                    note="5paisa minute coverage starts 2019-03-01 and lacks five sessions (2019-06-27, 06-28, 07-01, 07-02, 07-03); no minute warm-up exists before the first session"),
    "D_TV": RunSpec("D_TV", "Window D 2019-01-01..2019-12-31 (secondary vendor minutes)", date(2019, 1, 1), date(2019, 12, 31), D.SRC_TV_MIN, status="EXPLORATORY",
                    note="full calendar year from the secondary vendor only; overlap with 5paisa (2019-03..12) shows systematically different bars"),
}


def frozen_scenario():
    return P.combined_scenario(FROZEN_SCENARIO_ENGINE)


def provenance_for(spec: RunSpec) -> dict:
    mm, dm = D.source_manifest(spec.minute_source), D.source_manifest(spec.daily_source)
    return {"window_id": spec.window_id, "minute_source_id": spec.minute_source, "daily_source_id": spec.daily_source, "minute_source_manifest": f"data/phase4/processed/{spec.minute_source}/source_manifest.json",
            "daily_source_manifest": f"data/phase4/processed/{spec.daily_source}/source_manifest.json", "minute_partitions_sha256": {k: v["sha256"] for k, v in mm["partitions"].items()},
            "daily_partitions_sha256": {k: v["sha256"] for k, v in dm["partitions"].items()}, "minute_raw_files_sha256": mm.get("raw_files", {}), "daily_raw_files_sha256": dm.get("raw_files", {}),
            "calendar": "data/phase4/calendar/phase4_calendar_derived.json (derived; see data_quality_by_year.md)", "period": f"{spec.start}..{spec.end}", "status": spec.status, "note": spec.note,
            "price_source": "original one-minute NIFTY 50 index bars (timestamp = bar START, IST); 5-minute candles built causally from them; first 1-minute open is the session open; official close = 5paisa DAILY close"}


def run_window(spec: RunSpec) -> tuple[B.Bundle, D.WindowData]:
    minutes = D.load_processed_minutes(spec.minute_source)
    daily = D.load_processed_daily(spec.daily_source)
    from nifty_trading.data.market_calendar import load_market_calendar
    cal = load_market_calendar(D.CAL_DIR / "phase4_calendar_derived.json")
    wd = D.build_window_data(spec.window_id, minutes, daily, cal, spec.start, spec.end, spec.minute_source, spec.daily_source)
    prov = provenance_for(spec)
    b = B.build(scenario=frozen_scenario(), data=wd, journal=False, partition_fn=lambda d: D.partition_path(spec.minute_source, d), provenance_override=prov)
    b.phase_label = f"Phase 4 ({spec.window_id})"
    b.banner = (f"Phase 4 historical validation, window {spec.window_id} ({spec.label}; status {spec.status}). The FROZEN Phase 3.6 configuration (IRF, ORB, PDR body-based, PDS, RF; shared controller) on a different data source. "
                "HISTORICAL RESEARCH ONLY: the strategy was developed using later data. " + spec.note)
    mm = D.source_manifest(spec.minute_source)
    part_sha = {k: v for k, v in mm["partitions"].items()}
    raw_sha = mm.get("raw_files", {})

    def src_cols(day_str: str) -> dict:
        d = date.fromisoformat(day_str)
        pp = D.partition_path(spec.minute_source, d)
        rf = part_sha.get(pp, {}).get("raw_files", [])
        return {"data_window_id": spec.window_id, "data_source_id": spec.minute_source, "daily_source_id": spec.daily_source, "data_source_partition": pp, "data_source_partition_sha256": part_sha.get(pp, {}).get("sha256", ""),
                "raw_source_files": ";".join(rf), "raw_source_sha256": ";".join(raw_sha.get(f, "") for f in rf), "window_status": spec.status}
    for t in b.trades:
        t.update(src_cols(t["date"]))
    for g in b.legs:
        g.update({k: v for k, v in src_cols(g["trade_id"][:4] + "-" + g["trade_id"][4:6] + "-" + g["trade_id"][6:8]).items() if k in ("data_window_id", "data_source_id", "data_source_partition_sha256")})
    for r in b.daily:
        r.update({"data_window_id": spec.window_id, "data_source_id": spec.minute_source, "window_status": spec.status})
    return b, wd


# ------------------------------------------------------------------------------------------------------------------------------ writing
def write_window(b: B.Bundle, spec: RunSpec, base: Path = OUT) -> dict:
    wdir = base / "windows" / spec.window_id
    wdir.mkdir(parents=True, exist_ok=True)
    names = {"daily_summary.csv": "daily", "all_trades_detailed.csv": "trades", "trade_entry_conditions.csv": "checks", "trade_exits_detailed.csv": "legs", "candle_analysis.csv": "candles",
             "all_strategy_signals.csv": "signals", "ignored_signals.csv": "ignored", "rejected_signals.csv": "rejected", "verification_issues.csv": "issues"}
    for n, attr in names.items():
        write_csv(wdir / n, getattr(b, attr))
    import shutil
    for sub in (base / "daily" / spec.window_id, base / "charts" / spec.window_id):
        if sub.exists():
            shutil.rmtree(sub)
    n_days = 0
    for d in b.days:
        p = base / "daily" / spec.window_id / f"{d:%Y-%m}" / f"{d}.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(RN.render_day(b, d, rel_charts=f"../../../charts/{spec.window_id}"))
        n_days += 1
    (base / "charts" / spec.window_id).mkdir(parents=True, exist_ok=True)
    for t in b.trades:
        (base / "charts" / spec.window_id / f"{t['trade_id']}.svg").write_text(RN.trade_chart(b, t["trade_id"], defaultdict(list)))
    RN.write_json(b, wdir)
    snap = json.loads((wdir / "configuration_snapshot.json").read_text())
    snap.update({"phase": "4", "window": asdict(spec), "frozen_scenario": "phase3.combined_scenario('BODY_BASED_PHASE36')", "no_parameter_changed": True})
    (wdir / "configuration_snapshot.json").write_text(json.dumps(snap, indent=2, default=str))
    return {"days": n_days, "trades": len(b.trades), "charts": len(b.trades)}


# ------------------------------------------------------------------------------------------------------------------------------ metrics (all from trade tables, so the Phase 3.6 reference can be included unchanged)
def fnum(x) -> float:
    return float(str(x).replace(",", "")) if x not in (None, "") else 0.0


def pnl_seq(trades: list[dict], key: str = "gross_pnl_rs") -> list[float]:
    return [fnum(t[key]) for t in sorted(trades, key=lambda t: (t["date"], t["fill_timestamp"], int(t["trade_no_of_day"])))]


def max_drawdown(seq: list[float]) -> tuple[float, int]:
    cum = peak = worst = 0.0
    at = -1
    for i, v in enumerate(seq):
        cum += v
        peak = max(peak, cum)
        if peak - cum > worst:
            worst, at = peak - cum, i
    return worst, at


def max_losing_streak(seq: list[float]) -> int:
    best = cur = 0
    for v in seq:
        cur = cur + 1 if v < 0 else 0
        best = max(best, cur)
    return best


def profit_factor(seq: list[float]) -> float | None:
    gp = sum(v for v in seq if v > 0)
    gl = -sum(v for v in seq if v < 0)
    if gl > 0:
        return gp / gl
    return None if gp == 0 else math.inf


def window_metrics(trades: list[dict], daily: list[dict], label: str) -> dict:
    """Every metric of section 9 of the brief, for one trade table and its sessions table."""
    seq = pnl_seq(trades)
    net = pnl_seq(trades, "illustrative_net_pnl_rs")
    pts = [fnum(t["gross_pnl_points_weighted"]) for t in sorted(trades, key=lambda t: (t["date"], t["fill_timestamp"], int(t["trade_no_of_day"])))]
    n = len(trades)
    oc = Counter(t["outcome"] for t in trades)
    months: dict[str, float] = defaultdict(float)
    months_net: dict[str, float] = defaultdict(float)
    for t in trades:
        months[t["date"][:7]] += fnum(t["gross_pnl_rs"])
        months_net[t["date"][:7]] += fnum(t["illustrative_net_pnl_rs"])
    all_months = sorted({d["date"][:7] for d in daily})
    sessions = len(daily)
    valid = sum(1 for d in daily if str(d.get("session_type", "")).startswith("USABLE"))
    hold = [fnum(t["bars_held"]) for t in trades if t.get("bars_held") not in (None, "")]
    dd, _ = max_drawdown(seq)
    dd_n, _ = max_drawdown(net)
    dd_pts, _ = max_drawdown(pts)
    pf, pfn = profit_factor(seq), profit_factor(net)
    by_s = {s: [t for t in trades if t["strategy"] == s] for s in P.STRATEGIES}
    conflicts = sum(1 for d in daily if d.get("day_end_portfolio_state") == "UNRESOLVED_EXECUTION")
    return {
        "label": label, "sessions_evaluated": sessions, "sessions_valid_or_flagged": valid, "sessions_excluded_from_daily": sessions - valid, "trades": n, "first_trades": sum(1 for t in trades if t["trade_no_of_day"] == "1"),
        "second_trades": sum(1 for t in trades if t["trade_no_of_day"] == "2"), **{f"trades_{s}": len(v) for s, v in by_s.items()}, "total_index_points_weighted": round(sum(pts), 2),
        "gross_pnl_rs_fixed_390": round(sum(seq), 2), "net_pnl_rs_illustrative": round(sum(net), 2), "win_rate_pct": round(100.0 * sum(1 for v in seq if v > 0) / n, 2) if n else None,
        "profit_factor_gross": None if pf is None else ("inf" if pf == math.inf else round(pf, 4)), "profit_factor_net": None if pfn is None else ("inf" if pfn == math.inf else round(pfn, 4)),
        "max_drawdown_rs_gross": round(dd, 2), "max_drawdown_rs_net": round(dd_n, 2), "max_drawdown_index_points": round(dd_pts, 2), "max_consecutive_losses": max_losing_streak(seq),
        "avg_trade_rs": round(statistics.mean(seq), 2) if n else None, "median_trade_rs": round(statistics.median(seq), 2) if n else None, "largest_win_rs": round(max(seq), 2) if n else None,
        "largest_loss_rs": round(min(seq), 2) if n else None, "target2": oc.get("TARGET", 0), "t1_then_buffer_stop": oc.get("T1_THEN_BUFFER_STOP", 0), "initial_full_stop": oc.get("INITIAL_FULL_STOP", 0),
        "forced_exit": oc.get("FORCED_EXIT", 0), "unresolved_executions": oc.get("INCOMPLETE_EOD", 0) + oc.get("NOT_EVALUABLE", 0), "simultaneous_signal_conflict_days": conflicts,
        "positive_months": sum(1 for m in all_months if months.get(m, 0.0) > 0), "negative_months": sum(1 for m in all_months if months.get(m, 0.0) < 0), "flat_months": sum(1 for m in all_months if months.get(m, 0.0) == 0),
        "months": len(all_months), "trades_per_session": round(n / sessions, 4) if sessions else None, "avg_holding_minutes": round(statistics.mean(hold), 2) if hold else None,
        "strategy_gross_rs": {s: round(sum(fnum(t["gross_pnl_rs"]) for t in v), 2) for s, v in by_s.items()}, "monthly_gross_rs": {m: round(months.get(m, 0.0), 2) for m in all_months},
        "monthly_net_rs": {m: round(months_net.get(m, 0.0), 2) for m in all_months},
    }


def cost_scenarios(trades: list[dict], legs: list[dict]) -> list[dict]:
    """Costs at the FILL level, consistent with the exit model: one entry fill (all 390 units) and one fill per exit leg (195 + 195 units; a leg without a fillable exit has no fill). Fixed cost per fill = fixed per trade / 3;
    slippage = ``slip`` index points adverse on every unit of every fill. The base scenario (Rs 500 per trade, 0.5 point) equals the Phase 3.6 headline exactly. Illustrative: no specific instrument, no taxes schedule."""
    by_trade: dict[str, list[dict]] = defaultdict(list)
    for g in legs:
        by_trade[g["trade_id"]].append(g)
    rows = []
    for fx in COST_GRID_FIXED:
        for sl in COST_GRID_SLIP:
            seq = []
            for t in sorted(trades, key=lambda t: (t["date"], t["fill_timestamp"], int(t["trade_no_of_day"]))):
                ls = [g for g in by_trade[t["trade_id"]] if g.get("exit_price") not in (None, "")]
                fills = 1 + len(ls)
                units = fnum(t["qty_total"]) + sum(fnum(g["quantity"]) for g in ls)
                seq.append(fnum(t["gross_pnl_rs"]) - fx / 3.0 * fills - sl * units)
            dd, _ = max_drawdown(seq)
            pf = profit_factor(seq)
            rows.append({"fixed_cost_rs_per_trade": fx, "slippage_points_per_fill": sl, "net_pnl_rs": round(sum(seq), 2), "profit_factor": None if pf is None else ("inf" if pf == math.inf else round(pf, 4)),
                         "win_rate_pct": round(100.0 * sum(1 for v in seq if v > 0) / len(seq), 2) if seq else None, "max_drawdown_rs": round(dd, 2), "is_phase36_headline_assumption": (fx, sl) == BASE_COST})
    return rows
