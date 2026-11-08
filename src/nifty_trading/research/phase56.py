"""Phase 5.6: reconciliation of the automated trades with the ORIGINAL manual trading journal.

The journal workbook has five source columns only: serial number, date, entry-time label, strategy and outcome (Target / SL / BE). It records NO direction, price, stop, target or exit time, and nothing is invented here:
the loader keeps every row exactly as written (the five weekend-dated rows are flagged, not corrected; the Phase 2.1 attribution hypotheses that relabel strategies are NOT applied) and the matcher uses only those fields.

Matching is one-to-one and staged (a journal row and an automated trade are each used at most once):
  Stage A  STRICT          same date, same strategy, the entry-time label equals the automated SIGNAL CANDLE START (the label convention of the Phase 3.1 analysis: the journal labels the five-minute candle)
  Stage B  TIME_TOLERANT   same date, same strategy, the label within 15 minutes (three candles: the pre-existing Phase 3.1 tolerance, not widened) of the signal candle start
  Stage C  DATE_STRATEGY_ONLY   same date and strategy but the time is outside the tolerance: reported separately and NOT counted as a match
Outcome labels are compared descriptively (Target ~ TARGET, SL ~ INITIAL_FULL_STOP, BE ~ T1_THEN_BUFFER_STOP) and never used to choose a pair.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

TOL_STRICT = 0
TOL_TIME = 15
OUTCOME_CLASS = {"Target": "TARGET", "SL": "INITIAL_FULL_STOP", "BE": "T1_THEN_BUFFER_STOP"}
CAUSES = ("MISSING_STRATEGY_SIGNAL", "DIFFERENT_STRATEGY_SELECTED", "EARLIER_SIGNAL", "LATER_SIGNAL", "LEVEL_CONSTRUCTION_MISMATCH", "CANDLE_STRENGTH_MISMATCH", "EMA_FILTER_MISMATCH", "TRENDLINE_MISMATCH", "OPENING_GAP_MISMATCH",
          "CONFIRMATION_CANDLE_MISMATCH", "PORTFOLIO_CONTROLLER_CONSTRAINT", "ENTRY_TIME_MISMATCH", "EXIT_MANAGEMENT_MISMATCH", "DATA_PROVIDER_DIFFERENCE", "MANUAL_JOURNAL_INCONSISTENCY", "UNRESOLVED_DISCRETIONARY_SELECTION")


@dataclass
class JournalRow:
    row_id: int  # the journal's own serial number (Sl No.)
    sheet_row: int
    date: str  # exactly as in the workbook (YYYY-MM-DD)
    weekday: str
    time_label: str  # HH:MM as written (strings and time objects are both rendered HH:MM; seconds are dropped)
    time_label_raw: str
    strategy: str
    outcome: str
    weekend: bool = False
    flags: list[str] = field(default_factory=list)


def minutes(hhmm: str) -> int:
    return int(hhmm[:2]) * 60 + int(hhmm[3:5])


def load_journal(path: Path) -> tuple[list[JournalRow], dict]:
    """(rows, summary sheet) from the ORIGINAL workbook, read-only. Nothing is corrected or relabelled."""
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.worksheets[0]
    rows: list[JournalRow] = []
    for i, r in enumerate(ws.iter_rows(min_row=1, values_only=True), 1):
        if r[0] is None or r[1] is None or isinstance(r[0], str):
            continue
        t = r[2]
        label = t.strftime("%H:%M") if hasattr(t, "strftime") else str(t)[:5]
        jr = JournalRow(int(r[0]), i, r[1].strftime("%Y-%m-%d"), r[1].strftime("%a"), label, repr(t), str(r[3]), str(r[4]), weekend=r[1].weekday() >= 5)
        if jr.weekend:
            jr.flags.append("WEEKEND_DATE_NOT_AN_EXCHANGE_SESSION")
        rows.append(jr)
    summ = {}
    if len(wb.worksheets) > 1:
        for r in wb.worksheets[1].iter_rows(values_only=True):
            if r[0] and r[1] is not None and r[0] != "Metric":
                summ[str(r[0])] = r[1]
    return rows, summ


@dataclass
class Pair:
    manual: JournalRow
    trade: dict
    stage: str  # STRICT | TIME_TOLERANT | DATE_STRATEGY_ONLY
    delta_minutes: int  # automated signal candle start minus the manual label


def _assign(manual: list[JournalRow], trades: list[dict], used_m: set, used_t: set, tol: int | None, stage: str) -> list[Pair]:
    cands = []
    for m in manual:
        if m.row_id in used_m:
            continue
        for t in trades:
            tid = t["trade_id"]
            if tid in used_t or t["date"] != m.date or t["strategy"] != m.strategy:
                continue
            dt = minutes(t["signal_candle_start"]) - minutes(m.time_label)
            if tol is None or abs(dt) <= tol:
                cands.append((abs(dt), m.row_id, tid, m, t, dt))
    cands.sort(key=lambda x: (x[0], x[1], x[2]))
    out = []
    for _a, _mid, tid, m, t, dt in cands:
        if m.row_id in used_m or tid in used_t:
            continue
        used_m.add(m.row_id)
        used_t.add(tid)
        out.append(Pair(m, t, stage, dt))
    return out


def match(manual: list[JournalRow], trades: list[dict]) -> dict:
    """Staged one-to-one matching of journal rows with the executed trades of ONE configuration (``trades``: dicts with trade_id, date, strategy, signal_candle_start 'HH:MM'). Weekend-dated rows can never match."""
    used_m: set = set()
    used_t: set = set()
    pool = [m for m in manual if not m.weekend]
    strict = _assign(pool, trades, used_m, used_t, TOL_STRICT, "STRICT")
    tolerant = _assign(pool, trades, used_m, used_t, TOL_TIME, "TIME_TOLERANT")
    date_only = _assign(pool, trades, used_m, used_t, None, "DATE_STRATEGY_ONLY")
    return {"strict": strict, "tolerant": tolerant, "date_strategy_only": date_only, "manual_unmatched": [m for m in manual if m.row_id not in used_m], "trades_unmatched": [t for t in trades if t["trade_id"] not in used_t]}


def outcome_agrees(manual_outcome: str, auto_outcome: str) -> bool:
    return OUTCOME_CLASS.get(manual_outcome) == auto_outcome
