"""Manual-journal reconciliation for IRF V3 - READ-ONLY, after the engine is frozen; it never feeds back into any rule.

The journal (docs/trading journal/Trading_Journal_Sep2025_Aug2026 REPORT.xlsx) holds only: serial, date, entry-time label, strategy, outcome (Target / SL / BE). No direction, price, level, stop,
target or exit time -> an exact trade match can never be shown; every class below is a match on those four fields only.
Staged one-to-one matching on the SIGNAL-candle start (same convention as Phase 5.6/6.3): STRICT label == candle start; TIME_TOLERANT |delta| <= 15 min; DATE_STRATEGY_ONLY same date, further apart.
"""

from __future__ import annotations

import hashlib

import pandas as pd

from nifty_trading.research.orb_v2 import journal as J

TOL = 15
ROOT = J.ROOT


def mins(hhmm: str) -> int | None:
    return None if not hhmm else int(hhmm[:2]) * 60 + int(hhmm[3:5])


def load_journal() -> tuple[list[dict], str, int]:
    rows = J.read_journal()
    sha = hashlib.sha256(J.XLSX.read_bytes()).hexdigest()
    return rows, sha, len(rows)


def earlier_phase_signals() -> dict[str, dict]:
    """First confirmed IRF signal per date within the 13:00 cutoff (earliest signal time) from three earlier research ledgers (signal level, not trades). Window A only."""
    out: dict[str, dict] = {}
    a = pd.read_csv(ROOT / "reports/phase3/phase36_body_based_pdr/all_strategy_signals.csv")
    a = a[(a.strategy == "IRF") & (a.within_13_00_cutoff.astype(str) == "True")].sort_values(["date", "time"]).groupby("date").first()
    out["PHASE_3_6"] = {str(d): (r.candle_start, r.method) for d, r in a.iterrows()}
    b = pd.read_csv(ROOT / "reports/phase5/phase53_author_corrected/all_confirmed_signals.csv")
    b = b[(b.config == "phase53-author-corrected") & (b.strategy == "IRF") & (b.within_13_00_cutoff.astype(str) == "True")].sort_values(["date", "signal_time"]).groupby("date").first()
    out["PHASE_5_3"] = {str(d): (r.signal_candle_start, r.method) for d, r in b.iterrows()}
    c = pd.read_csv(ROOT / "reports/phase6/phase62_combined_backtest/all_signals.csv")
    c = c[(c.window == "A") & (c.config == "C") & (c.strategy == "IRF") & (c.within_13_00_cutoff.astype(str) == "True")].sort_values(["date", "time"]).groupby("date").first()
    out["PHASE_6_1"] = {str(d): (r.candle_start, r.method) for d, r in c.iterrows()}
    return out


def stage_match(manual: list[dict], auto: list[dict]) -> dict:
    """manual: journal rows; auto: dicts {date, candle_start}. One-to-one, strict -> tolerant -> date-only. Returns {sheet_row: (stage, auto_index, delta)}."""
    used_m, used_a, res = set(), set(), {}
    for stage, tol in (("STRICT", 0), ("TIME_TOLERANT", TOL), ("DATE_STRATEGY_ONLY", None)):
        cands = []
        for m in manual:
            if m["sheet_row"] in used_m or m["weekday"] in ("Sat", "Sun"):
                continue
            for i, a in enumerate(auto):
                if i in used_a or str(a["date"]) != str(m["date"]):
                    continue
                am, mm = mins(a["candle_start"]), mins(m["time"])
                if am is None or mm is None:
                    if tol is None:
                        cands.append((9999, m["sheet_row"], i, None))
                    continue
                d = am - mm
                if tol is None or abs(d) <= tol:
                    cands.append((abs(d), m["sheet_row"], i, d))
        for _ad, r, i, d in sorted(cands, key=lambda x: (x[0], x[1], x[2])):
            if r in used_m or i in used_a:
                continue
            used_m.add(r)
            used_a.add(i)
            res[r] = (stage, i, d)
    return res


OUT_MAP = {"Target": "TARGET", "SL": "STOP"}


def outcome_vs_journal(j_out: str, a_out: str | None) -> str:
    if a_out is None:
        return ""
    if j_out == "BE":
        return "JOURNAL_BE_HAS_NO_COUNTERPART_IN_FIXED_STOP_TARGET"
    return "AGREES" if OUT_MAP.get(j_out) == a_out else "DIFFERS"
