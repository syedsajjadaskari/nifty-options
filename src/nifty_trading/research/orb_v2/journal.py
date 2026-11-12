"""Manual-journal reading and ORB reconciliation (journal evidence only: Sl No, Date, Entry Time, Strategy, Outcome - NO direction, price, level or exit time).

Match classes (never upgrade a weaker agreement to a stronger one):
  STRICT_TIMING     same date, journal strategy ORB, journal time label == the V2 signal candle's start (09:15); one-to-one
  TIME_TOLERANT     same date and strategy, journal time within ``TOL_MIN`` minutes of the candle start but not equal
  DATE_STRATEGY_ONLY same date and ORB on both sides but the journal time is further away (or unreadable)
  MANUAL_ONLY       a manual ORB row with no V2 ORB trade that date
  AUTOMATED_ONLY    a V2 ORB trade on a date without a manual ORB row
A strict match is a match on the FIELDS THE JOURNAL HAS; direction, entry price and level are not recorded, so it is never an exact trade match.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[4]
XLSX = ROOT / "docs" / "trading journal" / "Trading_Journal_Sep2025_Aug2026 REPORT.xlsx"
TOL_MIN = 10


def _hhmm(v) -> str:
    if v is None:
        return ""
    if hasattr(v, "hour"):
        return f"{v.hour:02d}:{v.minute:02d}"
    s = str(v).strip()
    try:
        h, m = s.split(":")[:2]
        return f"{int(h):02d}:{int(m):02d}"
    except Exception:
        return ""


def minutes(hhmm: str) -> int | None:
    return None if not hhmm else int(hhmm[:2]) * 60 + int(hhmm[3:5])


def read_journal() -> list[dict]:
    ws = openpyxl.load_workbook(str(XLSX), data_only=True)["Trading Journal"]
    out = []
    for i, r in enumerate(ws.iter_rows(values_only=True), start=1):
        if i <= 2 or r[0] is None or not isinstance(r[0], (int, float)):
            continue
        d = r[1].date() if isinstance(r[1], datetime) else r[1]
        out.append({"sheet_row": i, "sl_no": int(r[0]), "date": d, "time_raw": r[2], "time": _hhmm(r[2]), "strategy": str(r[3]).strip().upper(), "outcome": str(r[4]).strip(), "weekday": d.strftime("%a")})
    return out


def orb_rows(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r["strategy"] == "ORB"]


def classify(manual: dict | None, trade: dict | None) -> str:
    if manual is None:
        return "AUTOMATED_ONLY"
    if trade is None:
        return "MANUAL_ONLY"
    t0 = trade["signal_confirmed_at"] - __import__("pandas").Timedelta(minutes=5)
    cand = f"{t0.hour:02d}:{t0.minute:02d}"
    m, a = minutes(manual["time"]), minutes(cand)
    if m is None:
        return "DATE_STRATEGY_ONLY"
    if m == a:
        return "STRICT_TIMING"
    return "TIME_TOLERANT" if abs(m - a) <= TOL_MIN else "DATE_STRATEGY_ONLY"


OUTCOME_MAP = {"TARGET": "Target", "STOP": "SL", "FORCED_EXIT": "BE"}


def outcome_descriptive(manual: dict, trade: dict) -> str:
    """Descriptive only: journal outcome vocabulary (Target / SL / BE) against the standalone 30/60 result. A journal 'BE' has no counterpart in a fixed 30/60 exit."""
    m = manual["outcome"]
    a = trade["exit_reason"]
    if m == "Target":
        return "AGREES" if a == "TARGET" else "DIFFERS"
    if m == "SL":
        return "AGREES" if a == "STOP" else "DIFFERS"
    return "NO_COUNTERPART_IN_30_60" if m == "BE" else "UNKNOWN"
