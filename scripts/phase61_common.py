"""Shared helpers for the Phase 6.1-6.3 scripts: paths, cached window data (contexts + bars + ORB V2 decisions), CSV writer."""

from __future__ import annotations

import csv
import pickle
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
R61 = ROOT / "reports" / "phase6" / "phase61_irf_support_break"
R62 = ROOT / "reports" / "phase6" / "phase62_combined_backtest"
R63 = ROOT / "reports" / "phase6" / "phase63_manual_reconciliation"
SCRATCH = Path("/private/tmp/claude-501/-Users-syedaskari-algo-nifty-options/dc8ac295-6b01-4d30-b811-e11236c4316e/scratchpad")
CACHE = SCRATCH / "phase61_cache"
JOURNAL = ROOT / "docs" / "trading journal" / "Trading_Journal_Sep2025_Aug2026 REPORT.xlsx"


def write_csv(path: Path, rows: list[dict], cols: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text(",".join(cols) + "\n" if cols else "")
        return
    cols = cols or list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else (f"{r[k]:.6f}".rstrip("0").rstrip(".") if isinstance(r.get(k), float) else r.get(k))) for k in cols})


def window_data(window: str):
    """(ctxs, infos, bars, cal, label) for 'A' (2025-09..2026-08, Phase 1 store) or 'B' (2022-09..2025-08, Phase 4 5paisa). Cached outside the repository."""
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"wd_{window}.pkl"
    if p.exists():
        return pickle.loads(p.read_bytes())
    from nifty_trading.core.execution_eligibility import bars_from_frame
    from nifty_trading.data.market_calendar import load_market_calendar
    from nifty_trading.data.sessions import (
        build_session_contexts,
        load_daily_official,
        load_one_minute,
        load_warmup_one_minute,
    )
    if window == "A":
        m1 = load_one_minute()
        ctxs, infos = build_session_contexts(m1, daily_df=load_daily_official(), warmup_1m=load_warmup_one_minute())
        m1 = m1.assign(_d=m1.timestamp.dt.date)
        cal = load_market_calendar()
        bars = {d: bars_from_frame(g) for d, g in m1.groupby("_d")}
        out = (ctxs, infos, bars, cal, "A 2025-09-01..2026-08-31 (5paisa, Phase 1 store)")
    else:
        from nifty_trading.research import phase4 as P4
        from nifty_trading.research import phase4_data as D4
        spec = P4.SPECS["B"]
        minutes = D4.load_processed_minutes(spec.minute_source)
        daily = D4.load_processed_daily(spec.daily_source)
        cal = load_market_calendar(D4.CAL_DIR / "phase4_calendar_derived.json")
        wd = D4.build_window_data(spec.window_id, minutes, daily, cal, spec.start, spec.end, spec.minute_source, spec.daily_source)
        out = (wd.ctxs, wd.infos, wd.bars, cal, "B 2022-09-01..2025-08-31 (5paisa, Phase 4 store)")
    p.write_bytes(pickle.dumps(out, protocol=4))
    return out
