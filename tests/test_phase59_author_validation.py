"""Author-review boundaries, not a new trading strategy."""

import pandas as pd
import pytest
from synthetic import minute_rows

from nifty_trading.research.phase59 import (
    AUTHOR_FIELDS,
    aggregate_five_minutes,
    blank_author_response,
    exact_entry_known,
    review_union,
    trade_display,
)


def test_review_responses_and_approvals_are_blank_and_journal_label_is_not_exact_entry():
    response = blank_author_response()
    assert set(response) == set(AUTHOR_FIELDS)
    assert all(v is None for v in response.values())
    assert not exact_entry_known({"manual_time_label": "09:15", "strategy": "ORB"})


def test_review_aggregation_excludes_next_bucket_and_rejects_missing_or_duplicate_minutes():
    raw = minute_rows([(100, 110, 90, 108), (108, 999, 107, 998)])
    bars = aggregate_five_minutes(raw)
    assert tuple(bars.iloc[0][["open", "high", "low", "close"]]) == (100, 110, 90, 108)
    assert bars.end.iloc[0] == raw.timestamp.iloc[5]
    assert len(aggregate_five_minutes(raw.drop(index=1))) == 1
    with pytest.raises(ValueError, match="Duplicate"):
        aggregate_five_minutes(pd.concat([raw, raw.iloc[:1]], ignore_index=True))


def test_trade_annotations_require_existing_ledger_prices_and_case_union_deduplicates():
    with pytest.raises(ValueError, match="requires ledger"):
        trade_display({"strategy": "IRF"})
    assert review_union({"session_a", "session_b"}, {"session_b", "session_c"}) == ["session_a", "session_b", "session_c"]
