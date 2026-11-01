"""Trading journal for execution recording and audit tracking."""

from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd


@dataclass
class JournalEntry:
    entry_id: str
    timestamp: str
    strategy_name: str
    instrument: str
    side: str
    quantity: int
    entry_price: float
    exit_price: float | None = None
    realized_pnl: float = 0.0
    rationale: str = ""
    tags: str = ""


class TradingJournal:
    """Maintains a persistent trading journal for review and performance analytics."""

    def __init__(self, log_path: Path | None = None):
        self.log_path = log_path
        self.entries: list[JournalEntry] = []

    def record_trade(self, entry: JournalEntry) -> None:
        self.entries.append(entry)

    def to_dataframe(self) -> pd.DataFrame:
        if not self.entries:
            return pd.DataFrame()
        return pd.DataFrame([asdict(e) for e in self.entries])
