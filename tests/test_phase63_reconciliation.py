"""Phase 6.3 reconciliation tests: original-journal integrity, one-to-one staged matching, count identities, no invented journal fields, an independent strict recount, tolerances unchanged, classification vocabulary."""

from __future__ import annotations

import hashlib
from collections import Counter
from pathlib import Path

import pandas as pd
import pytest

from nifty_trading.research import phase56 as M

ROOT = Path(__file__).resolve().parents[1]
R62 = ROOT / "reports" / "phase6" / "phase62_combined_backtest"
R63 = ROOT / "reports" / "phase6" / "phase63_manual_reconciliation"
JOURNAL = ROOT / "docs" / "trading journal" / "Trading_Journal_Sep2025_Aug2026 REPORT.xlsx"
needs = pytest.mark.skipif(not (R63 / "manual_vs_automated_matching.csv").exists(), reason="Phase 6.3 outputs not generated")
CFG = ("A", "B", "C")


def test_the_original_journal_is_intact_and_unchanged_in_its_known_shape():
    rows, summ = M.load_journal(JOURNAL)
    assert len(rows) == 190 and Counter(r.strategy for r in rows)["ORB"] == 89 and sum(1 for r in rows if r.weekend) == 5
    assert summ.get("Total trades") == 189                                                 # the Summary sheet's 189 is NOT the data-row count: the discrepancy is carried, not corrected
    assert M.TOL_STRICT == 0 and M.TOL_TIME == 15                                         # the Phase 5.6 tolerances are unchanged
    assert hashlib.sha256(JOURNAL.read_bytes()).hexdigest() in (R63 / "manual_journal_source_audit.md").read_text()


def test_the_matcher_is_one_to_one_and_staged_on_a_small_example():
    jr = [M.JournalRow(1, 3, "2025-09-01", "Mon", "09:15", "'09:15'", "ORB", "SL"), M.JournalRow(2, 4, "2025-09-01", "Mon", "09:20", "'09:20'", "ORB", "Target"), M.JournalRow(3, 5, "2025-09-02", "Tue", "10:00", "'10:00'", "IRF", "BE")]
    tr = [{"trade_id": "a", "date": "2025-09-01", "strategy": "ORB", "signal_candle_start": "09:15"}, {"trade_id": "b", "date": "2025-09-02", "strategy": "IRF", "signal_candle_start": "10:10"}]
    m = M.match(jr, tr)
    assert [p.manual.row_id for p in m["strict"]] == [1] and [p.manual.row_id for p in m["tolerant"]] == [3]
    assert [r.row_id for r in m["manual_unmatched"]] == [2] and m["trades_unmatched"] == []                 # row 2 cannot reuse trade 'a'; a 10-minute offset is time-tolerant


@pytest.fixture(scope="module")
def pairs():
    if not (R63 / "manual_vs_automated_matching.csv").exists():
        pytest.skip("Phase 6.3 outputs not generated")
    return pd.read_csv(R63 / "manual_vs_automated_matching.csv", dtype=str, keep_default_na=False)


@needs
def test_one_to_one_and_count_identities_for_every_configuration(pairs):
    led = pd.read_csv(R62 / "all_executed_trades.csv")
    for k in CFG:
        p = pairs[pairs.config == k]
        matched = p[p.stage.isin(["STRICT", "TIME_TOLERANT", "DATE_STRATEGY_ONLY"])]
        assert matched.journal_row.is_unique and matched.trade_id.is_unique                         # no journal row and no trade is used twice
        n_trades = len(led[(led.window == "A") & (led.config == k)])
        by = Counter(p.stage)
        assert by["STRICT"] + by["TIME_TOLERANT"] + by["DATE_STRATEGY_ONLY"] + by["MANUAL_ONLY"] == 190
        assert by["STRICT"] + by["TIME_TOLERANT"] + by["DATE_STRATEGY_ONLY"] + by["AUTOMATED_ONLY"] == n_trades
        assert (matched.verified_exact_trade_match == "False").all()                                 # no verified exact match is ever claimed
    s = pd.read_csv(R63 / "match_summary_by_strategy.csv")
    c = pd.read_csv(R63 / "match_summary_by_config.csv")
    for k in CFG:
        assert s[s.config == k].strict.sum() == c[c.config == k].strict_matches.iloc[0] and s[s.config == k].manual_rows.sum() == 190


@needs
def test_independent_strict_recount_with_a_separate_multiset_method(pairs):
    rows, _ = M.load_journal(JOURNAL)
    led = pd.read_csv(R62 / "all_executed_trades.csv", dtype={"signal_time": str})
    for k in CFG:
        a = led[(led.window == "A") & (led.config == k)]
        def start(t):  # noqa: E306
            m = int(t[:2]) * 60 + int(t[3:]) - 5
            return f"{m // 60:02d}:{m % 60:02d}"
        auto = Counter((d, s, start(t)) for d, s, t in zip(a.date, a.strategy, a.signal_time, strict=True))
        man = Counter((r.date, r.strategy, r.time_label) for r in rows if not r.weekend)
        strict = sum(min(n, auto.get(key, 0)) for key, n in man.items())
        assert strict == len(pairs[(pairs.config == k) & (pairs.stage == "STRICT")])


@needs
def test_no_journal_field_is_invented_in_the_matching_output(pairs):
    forbidden = {"manual_direction", "manual_entry_price", "manual_level", "manual_exit_time", "manual_stop"}
    assert not (forbidden & set(pairs.columns))
    j = pairs[pairs.stage == "MANUAL_ONLY"]
    assert (j.auto_entry_price == "").all() and (j.trade_id == "").all()


@needs
def test_orb_vs_irf_classification_vocabulary_and_resolution_flag():
    o = pd.read_csv(R63 / "orb_vs_irf_comparison.csv", dtype=str, keep_default_na=False)
    allowed = {"ORB NOW SELECTED", "IRF STILL SELECTED", "ORB SIGNAL PRESENT BUT LATER", "ORB SIGNAL PRESENT, NOT SELECTED (controller)", "ORB SIGNAL REJECTED", "SAME-MINUTE CONFLICT", "NO ELIGIBLE TRADE", "SOURCE RULE UNRESOLVED", "NO ELIGIBLE TRADE (non-session journal date)"}
    assert set(o.classification) <= allowed and len(o) == 89
    assert set(o[o.resolved == "True"].classification) == {"ORB NOW SELECTED"}                      # a journal label alone never resolves a dispute


@needs
def test_every_per_strategy_row_adds_up_and_rows_by_strategy_match_the_journal():
    s = pd.read_csv(R63 / "match_summary_by_strategy.csv")
    rows, _ = M.load_journal(JOURNAL)
    by = Counter(r.strategy for r in rows)
    for r in s.itertuples():
        assert r.manual_rows == by[r.strategy] and r.strict + r.time_tolerant + r.date_strategy_only + r.manual_only == r.manual_rows
