"""Read-only author-review utilities. No signal engine, fills or rule activation."""

from __future__ import annotations

import pandas as pd

AUTHOR_LABEL = "AUTHOR ORB ENTRY — TO BE MARKED"
AUTHOR_FIELDS = (
    "author_reviewed_entry_time", "author_reviewed_entry_price",
    "author_reviewed_support_resistance", "author_reviewed_method",
    "author_reviewed_direction", "author_explanation", "author_confirms_trade",
    "source_supports_general_rule", "engineering_implementation_approved",
)


def blank_author_response() -> dict:
    """Unknown author evidence stays genuinely blank, including approval fields."""
    return dict.fromkeys(AUTHOR_FIELDS)


def aggregate_five_minutes(raw: pd.DataFrame) -> pd.DataFrame:
    """Independent start-labelled aggregation; no incomplete bar or interpolation."""
    frame = raw.sort_values("timestamp").copy()
    if frame.timestamp.duplicated().any():
        raise ValueError("Duplicate one-minute timestamps")
    clock = frame.timestamp.dt.hour * 60 + frame.timestamp.dt.minute
    frame = frame[(clock >= 555) & (clock < 930)].copy()
    frame["start"] = frame.timestamp.dt.floor("5min")
    bars = frame.groupby("start", sort=True).agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"),
        close=("close", "last"), minute_count=("timestamp", "nunique"),
    ).reset_index()
    bars = bars[bars.minute_count == 5].copy()
    bars["end"] = bars.start + pd.Timedelta(minutes=5)
    return bars.reset_index(drop=True)


def trade_display(ledger: dict) -> dict:
    """Only existing ledger numbers. No outcome/P&L field is selected or derived."""
    required = ("entry_price", "initial_stop", "target_1", "target_2")
    if any(ledger.get(k) in (None, "") for k in required):
        raise ValueError("An executed-trade display requires ledger prices")
    return {
        "trade_id": ledger["trade_id"], "strategy": ledger["strategy"],
        "method": ledger["method"], "direction": ledger["direction"],
        "signal_time": ledger["signal_confirmed_at"][-5:],
        "entry_time": ledger["fill_timestamp"][-5:],
        "entry": float(ledger["entry_price"]), "stop": float(ledger["initial_stop"]),
        "t1": float(ledger["target_1"]), "t2": float(ledger["target_2"]),
        "exits": [{"leg": leg, "time": ledger.get(f"leg{leg}_exit_time") or None,
                   "price": float(ledger[f"leg{leg}_exit_price"]) if ledger.get(f"leg{leg}_exit_price") else None}
                  for leg in (1, 2)],
    }


def review_union(missing_dates: set[str], handwritten_dates: set[str]) -> list[str]:
    """Cases are evidence records, not dates inserted into a strategy."""
    return sorted(missing_dates | handwritten_dates)


def exact_entry_known(journal_row: dict) -> bool:
    """The original label alone supplies neither candle convention nor price."""
    return bool(journal_row.get("explicit_execution_timestamp") and journal_row.get("entry_price"))
