"""Phase 5: the FROZEN Phase 3.6 five-strategy portfolio run on the BANKNIFTY and SENSEX index prices (signals and index-point results only).

No new backtesting engine and no strategy change: this is the same ``phase3.combined_scenario("BODY_BASED_PHASE36")`` through the same Phase 3.2 explainable-backtest framework that Phase 4 used for NIFTY,
fed by an index-specific data source and a calendar derived from that index's own data. The stops, targets, cutoff and sizing are the NIFTY index-POINT values, deliberately NOT adjusted to the index level
(a rule-transfer diagnostic). All results here are INDEX results: option premiums are never estimated (see ``phase5_options``). The fixed 390-unit multiplier is a per-index comparison device, not a contract size.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from nifty_trading.research import phase4 as F4
from nifty_trading.research import phase4_data as D4
from nifty_trading.research import phase5_data as D5
from nifty_trading.research import phase32_build as B
from nifty_trading.research import phase32_render as RN
from nifty_trading.research.phase35 import write_csv

ROOT = D4.ROOT
OUT = ROOT / "reports" / "phase5"
SECONDARY_END = {"BANKNIFTY": date(2026, 4, 22), "SENSEX": date(2024, 3, 22)}  # last day of the secondary repositories' 1-minute files
COMMON_OVERLAP_END = date(2024, 3, 22)  # the vendor-sensitivity window ends where BOTH secondary files end, so both indices are compared over the same dates
SENSEX_SECONDARY_START = date(2018, 3, 8)


@dataclass(frozen=True)
class RunSpec5:
    index: str
    window_id: str
    label: str
    start: date
    end: date
    minute_source: str  # "5paisa" | "secondary"
    status: str = "DATA_VALIDATED"  # DATA_VALIDATED | VENDOR_SENSITIVITY | EXPLORATORY | PARTIAL_YEAR | CUSTOM
    note: str = ""

    @property
    def run_id(self) -> str:
        return f"{self.index}:{self.window_id}"


def specs_for(index: str) -> dict[str, RunSpec5]:
    ix = D5.INDEXES[index]
    out = {
        "M": RunSpec5(index, "M", "Main window 2022-09-01..2026-08-31 (5paisa minutes)", date(2022, 9, 1), date(2026, 8, 31), "5paisa", "DATA_VALIDATED",
                      "same provider and download path as the NIFTY Phase 4 / Phase 3.6 runs; the status only says the DATA window passed the quality gate"),
        "MS": RunSpec5(index, "MS", f"Vendor sensitivity 2022-09-01..{COMMON_OVERLAP_END} (secondary-source minutes)", date(2022, 9, 1), COMMON_OVERLAP_END, "secondary", "VENDOR_SENSITIVITY",
                       "the same dates with the secondary repository's minute bars (daily series still 5paisa); quantifies sensitivity to the data source, not a second independent result"),
        "C": RunSpec5(index, "C", "Window C 2018-01-01..2018-12-31 (secondary-source minutes)", date(2018, 1, 1), date(2018, 12, 31), "secondary", "EXPLORATORY",
                      "5paisa returns no minute data before 2019-03-01, so this year rests on one unattributed vendor with nothing to check it against" + ("; the SENSEX file only starts on 2018-03-08 (about 200 of ~246 sessions)" if index == "SENSEX" else "")),
        "D_5P": RunSpec5(index, "D_5P", "Window D 2019-03-01..2019-12-31 (5paisa minutes, PARTIAL YEAR)", date(2019, 3, 1), date(2019, 12, 31), "5paisa", "PARTIAL_YEAR",
                         "5paisa minute coverage starts 2019-03-01; no minute warm-up exists before the first session"),
        "D_TV": RunSpec5(index, "D_TV", "Window D 2019-01-01..2019-12-31 (secondary-source minutes)", date(2019, 1, 1), date(2019, 12, 31), "secondary", "EXPLORATORY",
                         "full calendar year from the secondary repository only; its bars differ from 5paisa's where both exist"),
    }
    assert ix.name == index
    return out


def minute_source_id(ix: D5.IndexSpec, spec: RunSpec5) -> str:
    return ix.src_5p_min if spec.minute_source == "5paisa" else ix.src_sec_min


def relabel(s: str, ix: D5.IndexSpec) -> str:
    """The frozen framework's rendered texts say 'NIFTY 50' (the instrument it was written for). In Phase 5 outputs the instrument is the index being run. Only the instrument phrases are replaced; names of source
    documents (``NIFTY_System_Trading_Strategy_Performance.docx``) and rule texts that quote that document stay as they are, because they are the provenance of the frozen rules."""
    s = s.replace("NIFTY 50 (index, not directly tradable; points are synthetic)", f"{ix.name} ({ix.display} index, not directly tradable; points are synthetic)")
    s = re.sub(r"NIFTY 50 index-point", f"{ix.name} index-point", s)
    s = re.sub(r"\bNIFTY 50\b(?! one-minute)", ix.name, s)
    s = s.replace("NIFTY spot points", f"{ix.name} index points").replace("NIFTY spot", f"{ix.name} index")
    s = s.replace("original NIFTY 50 one-minute", f"original {ix.name} one-minute")
    return s


def provenance_for(ix: D5.IndexSpec, spec: RunSpec5) -> dict:
    src = minute_source_id(ix, spec)
    mm, dm = D5.source_manifest(ix, src), D5.source_manifest(ix, ix.src_5p_daily)
    inst = json.loads(ix.instrument_file.read_text())
    return {"index": ix.name, "window_id": spec.window_id, "minute_source_id": src, "daily_source_id": ix.src_5p_daily, "minute_source_manifest": f"data/processed/{ix.key}/{src}/source_manifest.json",
            "daily_source_manifest": f"data/processed/{ix.key}/{ix.src_5p_daily}/source_manifest.json", "minute_partitions_sha256": {k: v["sha256"] for k, v in mm["partitions"].items()},
            "daily_partitions_sha256": {k: v["sha256"] for k, v in dm["partitions"].items()}, "minute_raw_files_sha256": mm.get("raw_files", {}), "daily_raw_files_sha256": dm.get("raw_files", {}),
            "instrument": {k: inst[k] for k in ("symbol", "exchange", "exchange_label", "exchange_segment", "scrip_code", "master_file", "master_sha256")},
            "calendar": f"data/processed/{ix.key}/calendar_derived.json (derived from this index's own data; see data_quality_report.md)", "period": f"{spec.start}..{spec.end}", "status": spec.status, "note": spec.note,
            "price_source": f"original one-minute {ix.name} index bars (timestamp = bar START, IST); 5-minute candles built causally from them; first 1-minute open is the session open; official close = 5paisa DAILY close"}


def run_window(ix: D5.IndexSpec, spec: RunSpec5) -> tuple[B.Bundle, D4.WindowData]:
    from nifty_trading.data.market_calendar import load_market_calendar
    src = minute_source_id(ix, spec)
    minutes = D5.load_processed_minutes(ix, src)
    daily = D5.load_processed_daily(ix, ix.src_5p_daily)
    cal = load_market_calendar(ix.calendar_file)
    wd = D4.build_window_data(spec.window_id, minutes, daily, cal, spec.start, spec.end, src, ix.src_5p_daily)
    prov = provenance_for(ix, spec)
    b = B.build(scenario=F4.frozen_scenario(), data=wd, journal=False, partition_fn=lambda d: ix.partition_path(src, d), provenance_override=prov)
    b.phase_label = f"Phase 5 ({ix.name} {spec.window_id})"
    b.banner = (f"Phase 5 cross-index test, {ix.name} window {spec.window_id} ({spec.label}; status {spec.status}). The FROZEN Phase 3.6 configuration (IRF, ORB, PDR body-based, PDS, RF; shared controller) with the NIFTY index-point "
                f"stops and targets UNCHANGED on the {ix.name} index price. INDEX-POINT RESULTS ONLY: no option premium is used or estimated. HISTORICAL RESEARCH ONLY: the strategy was developed using later NIFTY data. " + spec.note)
    mm = D5.source_manifest(ix, src)
    part = dict(mm["partitions"])
    raw_sha = mm.get("raw_files", {})

    def src_cols(day_str: str) -> dict:
        d = date.fromisoformat(day_str)
        pp = ix.partition_path(src, d)
        rf = part.get(pp, {}).get("raw_files", [])
        return {"index": ix.name, "data_window_id": spec.window_id, "data_source_id": src, "daily_source_id": ix.src_5p_daily, "data_source_partition": pp, "data_source_partition_sha256": part.get(pp, {}).get("sha256", ""),
                "raw_source_files": ";".join(rf), "raw_source_sha256": ";".join(raw_sha.get(f, "") for f in rf), "window_status": spec.status}
    for t in b.trades:
        t.update(src_cols(t["date"]))
    for g in b.legs:
        s = src_cols(f"{g['trade_id'][:4]}-{g['trade_id'][4:6]}-{g['trade_id'][6:8]}")
        g.update({k: s[k] for k in ("index", "data_window_id", "data_source_id", "data_source_partition_sha256")})
    for r in b.daily:
        r.update({"index": ix.name, "data_window_id": spec.window_id, "data_source_id": src, "window_status": spec.status})
    return b, wd


def _rl_rows(rows: list[dict], ix: D5.IndexSpec) -> list[dict]:
    return [{k: (relabel(v, ix) if isinstance(v, str) else v) for k, v in r.items()} for r in rows]


def write_window(b: B.Bundle, ix: D5.IndexSpec, spec: RunSpec5, base: Path | None = None, option_note=None) -> dict:
    """Write the window's CSVs, one journal per session (no-trade days included) and one chart per trade under reports/phase5/<index>/. ``option_note(trade_row) -> str`` adds the option-feasibility block."""
    base = base or (OUT / ix.key)
    wdir = base / "windows" / spec.window_id
    wdir.mkdir(parents=True, exist_ok=True)
    names = {"daily_summary.csv": "daily", "all_trades_detailed.csv": "trades", "trade_entry_conditions.csv": "checks", "trade_exits_detailed.csv": "legs", "candle_analysis.csv": "candles",
             "all_strategy_signals.csv": "signals", "ignored_signals.csv": "ignored", "rejected_signals.csv": "rejected", "verification_issues.csv": "issues"}
    for n, attr in names.items():
        write_csv(wdir / n, _rl_rows(getattr(b, attr), ix))
    import shutil
    for sub in (base / "daily" / spec.window_id, base / "charts" / spec.window_id):
        if sub.exists():
            shutil.rmtree(sub)
    by_day: dict[str, list[dict]] = defaultdict(list)
    for t in b.trades:
        by_day[t["date"]].append(t)
    n_days = 0
    for d in b.days:
        txt = relabel(RN.render_day(b, d, rel_charts=f"../../../charts/{spec.window_id}"), ix)
        if option_note is not None:
            txt = txt.rstrip("\n") + "\n\n" + option_note(by_day.get(str(d), []), ix, spec)
        p = base / "daily" / spec.window_id / f"{d:%Y-%m}" / f"{d}.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt)
        n_days += 1
    (base / "charts" / spec.window_id).mkdir(parents=True, exist_ok=True)
    for t in b.trades:
        (base / "charts" / spec.window_id / f"{t['trade_id']}.svg").write_text(relabel(RN.trade_chart(b, t["trade_id"], defaultdict(list)), ix))
    RN.write_json(b, wdir)
    snap = json.loads((wdir / "configuration_snapshot.json").read_text())
    snap.update({"phase": "5", "index": ix.name, "window": asdict(spec), "frozen_scenario": "phase3.combined_scenario('BODY_BASED_PHASE36')", "no_parameter_changed": True,
                 "stops_targets_unit": "index points, NOT scaled to the index level", "multiplier_note": "390 units is a fixed comparison multiplier, not a contract size"})
    (wdir / "configuration_snapshot.json").write_text(json.dumps(snap, indent=2, default=str))
    return {"days": n_days, "trades": len(b.trades), "charts": len(b.trades)}
