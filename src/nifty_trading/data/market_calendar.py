"""Evidence-backed NSE calendar and market-structure facts used by the data-quality layer.

Loaded from ``data/metadata/nse_calendar_2025_2026.json`` (machine-readable, with evidence per entry). It supersedes
the Phase 1 ``NSE_HOLIDAYS`` list for quality decisions: that list was found to be wrong on four dates (see the file's
``phase1_calendar_errors``) and to omit four real closures. The Phase 1 module itself is left untouched.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, time
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[3] / "data" / "metadata" / "nse_calendar_2025_2026.json"


@dataclass(frozen=True)
class CalendarEntry:
    date: date
    name: str
    evidence_tier: str
    evidence: tuple[str, ...] = ()
    evaluable_by_strategies: bool = True


@dataclass(frozen=True)
class ClosingAuction:
    """NSE Closing Auction Session regime: the index is frozen inside ``frozen_window`` on/after ``effective_date``."""

    effective_date: date
    frozen_start: time
    frozen_end: time

    def applies(self, d: date) -> bool:
        return d >= self.effective_date


@dataclass(frozen=True)
class MarketCalendar:
    holidays: dict[date, CalendarEntry] = field(default_factory=dict)
    special_sessions: dict[date, CalendarEntry] = field(default_factory=dict)
    closing_auction: ClosingAuction | None = None
    source: str = "NONE"

    def is_confirmed_holiday(self, d: date) -> bool:
        return d in self.holidays

    def is_special_session(self, d: date) -> bool:
        return d in self.special_sessions


def _hhmm(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


def load_market_calendar(path: str | Path | None = None) -> MarketCalendar:
    p = Path(path) if path else DEFAULT_PATH
    if not p.exists():
        return MarketCalendar(source="MISSING_FILE")
    raw = json.loads(p.read_text())
    hol = {date.fromisoformat(h["date"]): CalendarEntry(date.fromisoformat(h["date"]), h["name"], h.get("evidence_tier", "?"),
                                                        tuple(h.get("evidence", ()))) for h in raw.get("holidays", [])}
    spc = {date.fromisoformat(s["date"]): CalendarEntry(date.fromisoformat(s["date"]), s["name"], s.get("evidence_tier", "?"),
                                                        tuple(s.get("evidence", ())), bool(s.get("evaluable_by_strategies", True)))
           for s in raw.get("special_sessions", [])}
    cas = None
    for ch in raw.get("market_structure_changes", []):
        if ch.get("id") == "NSE_CLOSING_AUCTION_SESSION":
            a, b = ch["index_frozen_window_hhmm"]
            cas = ClosingAuction(date.fromisoformat(ch["effective_date"]), _hhmm(a), _hhmm(b))
    return MarketCalendar(hol, spc, cas, source=str(p))
