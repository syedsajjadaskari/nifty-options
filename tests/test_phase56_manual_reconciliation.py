"""Phase 5.6: unit tests of the one-to-one staged matcher on hand-built journal rows and trades (strict, time-tolerant, date-and-strategy-only, weekend rows, tie-breaks, outcome flags), read-only checks of the ORIGINAL journal workbook
(190 data rows, 189 in the Summary, 89 ORB, five Saturday-dated rows kept as written), and file-level tests on the delivered bundle (one-to-one use, vocabulary, nothing invented)."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

from nifty_trading.research import phase56 as R

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "phase5" / "phase56_manual_reconciliation"
JOURNAL = ROOT / "docs" / "trading journal" / "Trading_Journal_Sep2025_Aug2026 REPORT.xlsx"
needs_bundle = pytest.mark.skipif(not (OUT / "phase56_state.json").exists(), reason="Phase 5.6 bundle not generated")
needs_journal = pytest.mark.skipif(not JOURNAL.exists(), reason="journal workbook absent")


def jr(i, date, label, strat, outcome="Target", weekend=False):
    return R.JournalRow(i, i + 3, date, "Mon", label, label, strat, outcome, weekend=weekend)


def tr(tid, date, strat, start, outcome="TARGET"):
    return {"trade_id": tid, "date": date, "strategy": strat, "signal_candle_start": start, "outcome": outcome}


def test_strict_then_tolerant_then_date_only_are_separate_stages():
    manual = [jr(1, "2026-01-05", "09:15", "ORB"), jr(2, "2026-01-06", "10:00", "IRF"), jr(3, "2026-01-07", "11:00", "IRF")]
    trades = [tr("t1", "2026-01-05", "ORB", "09:15"), tr("t2", "2026-01-06", "IRF", "10:10"), tr("t3", "2026-01-07", "IRF", "13:00")]
    m = R.match(manual, trades)
    assert [(p.manual.row_id, p.trade["trade_id"], p.delta_minutes) for p in m["strict"]] == [(1, "t1", 0)]
    assert [(p.manual.row_id, p.trade["trade_id"], p.delta_minutes) for p in m["tolerant"]] == [(2, "t2", 10)]
    assert [(p.manual.row_id, p.stage) for p in m["date_strategy_only"]] == [(3, "DATE_STRATEGY_ONLY")]
    assert m["manual_unmatched"] == []  # `manual_unmatched` = rows with no same-date same-strategy trade at all; a date-only pair is reported in its own stage and never counted as a match (the runner adds it to the unmatched totals)


def test_tolerance_boundary_is_fifteen_minutes_inclusive():
    m = R.match([jr(1, "2026-01-05", "10:00", "IRF"), jr(2, "2026-01-06", "10:00", "IRF")], [tr("a", "2026-01-05", "IRF", "10:15"), tr("b", "2026-01-06", "IRF", "10:20")])
    assert [p.trade["trade_id"] for p in m["tolerant"]] == ["a"] and [p.trade["trade_id"] for p in m["date_strategy_only"]] == ["b"]


def test_one_to_one_closest_pair_wins_and_nothing_is_reused():
    manual = [jr(1, "2026-01-05", "10:00", "IRF"), jr(2, "2026-01-05", "10:30", "IRF")]
    trades = [tr("a", "2026-01-05", "IRF", "10:05"), tr("b", "2026-01-05", "IRF", "10:25")]
    m = R.match(manual, trades)
    pairs = {(p.manual.row_id, p.trade["trade_id"]) for p in m["strict"] + m["tolerant"] + m["date_strategy_only"]}
    assert pairs == {(1, "a"), (2, "b")}
    one = R.match([jr(1, "2026-01-05", "10:00", "IRF")], trades)
    assert len(one["tolerant"]) == 1 and one["tolerant"][0].trade["trade_id"] == "a" and [t["trade_id"] for t in one["trades_unmatched"]] == ["b"]


def test_strategy_and_date_must_agree_and_weekend_rows_never_match():
    manual = [jr(1, "2026-01-05", "09:15", "ORB"), jr(2, "2026-01-10", "09:15", "ORB", weekend=True)]
    trades = [tr("x", "2026-01-05", "IRF", "09:15"), tr("y", "2026-01-10", "ORB", "09:15")]
    m = R.match(manual, trades)
    assert not (m["strict"] or m["tolerant"] or m["date_strategy_only"])
    assert {x.row_id for x in m["manual_unmatched"]} == {1, 2} and len(m["trades_unmatched"]) == 2


def test_outcome_flag_is_descriptive_only():
    assert R.outcome_agrees("Target", "TARGET") and R.outcome_agrees("SL", "INITIAL_FULL_STOP") and R.outcome_agrees("BE", "T1_THEN_BUFFER_STOP")
    assert not R.outcome_agrees("Target", "INITIAL_FULL_STOP") and not R.outcome_agrees("BE", "FORCED_EXIT")
    m = R.match([jr(1, "2026-01-05", "09:15", "ORB", "SL")], [tr("t", "2026-01-05", "ORB", "09:15", "TARGET")])
    assert len(m["strict"]) == 1  # a different outcome never prevents the match


def test_minutes_and_vocabulary():
    assert R.minutes("09:15") == 555 and R.minutes("15:00") == 900
    assert len(R.CAUSES) == len(set(R.CAUSES)) == 16 and "MANUAL_JOURNAL_INCONSISTENCY" in R.CAUSES
    assert (R.TOL_STRICT, R.TOL_TIME) == (0, 15)


@needs_journal
def test_original_journal_is_read_exactly_as_written():
    rows, summ = R.load_journal(JOURNAL)
    assert len(rows) == 190 and [r.row_id for r in rows] == list(range(1, 191))
    assert str(summ["Total trades"]) == "189"
    assert Counter(r.strategy for r in rows)["ORB"] == 89
    assert Counter(r.outcome for r in rows) == {"Target": 81, "SL": 65, "BE": 44}
    wk = [r for r in rows if r.weekend]
    assert [(r.row_id, r.date) for r in wk] == [(23, "2025-10-11"), (82, "2026-02-14"), (181, "2026-08-15"), (185, "2026-08-22"), (189, "2026-08-29")]
    assert all("WEEKEND_DATE_NOT_AN_EXCHANGE_SESSION" in r.flags for r in wk)
    assert sum(1 for n in Counter(r.date for r in rows).values() if n == 2) == 5


@needs_bundle
def test_bundle_is_one_to_one_and_counts_are_consistent():
    st = json.loads((OUT / "phase56_state.json").read_text())
    with open(OUT / "manual_vs_automated_matching.csv", newline="") as f:
        mt = list(csv.DictReader(f))
    for k in "ABC":
        rows = [r for r in mt if r["config"] == k and r["journal_row"]]
        assert sorted(int(r["journal_row"]) for r in rows) == list(range(1, 191))
        used = [r["trade_id"] for r in rows if r["trade_id"] and r["match_stage"] in ("STRICT", "TIME_TOLERANT", "DATE_STRATEGY_ONLY")]
        assert len(used) == len(set(used))
        c = Counter(r["match_stage"] for r in rows)
        m = st["matching"][k]
        assert (c["STRICT"], c["TIME_TOLERANT"], c["DATE_STRATEGY_ONLY"]) == (m["strict"], m["time_tolerant"], m["date_strategy_only"])
        assert c["STRICT"] + c["TIME_TOLERANT"] + c["DATE_STRATEGY_ONLY"] + c["UNMATCHED_MANUAL"] == 190
        assert all(r["delta_minutes_vs_signal_candle_start"] == "0" for r in rows if r["match_stage"] == "STRICT")


@needs_bundle
def test_root_causes_use_the_specified_vocabulary_and_carry_evidence():
    with open(OUT / "mismatch_root_causes.csv", newline="") as f:
        rc = list(csv.DictReader(f))
    assert rc
    assert all(r["root_cause_primary"] in R.CAUSES and (not r["root_cause_secondary"] or r["root_cause_secondary"] in R.CAUSES) and r["evidence"].strip() for r in rc)


@needs_bundle
@needs_journal
def test_delivered_journal_rows_equal_the_original_and_the_workbook_is_unchanged():
    rows, _s = R.load_journal(JOURNAL)
    orig = {str(r.row_id): (r.date, r.time_label, r.strategy, r.outcome) for r in rows}
    with open(OUT / "manual_vs_automated_matching.csv", newline="") as f:
        for r in csv.DictReader(f):
            if r["journal_row"]:
                assert orig[r["journal_row"]] == (r["date"], r["manual_time_label"], r["manual_strategy"], r["manual_outcome"])
    snap = json.loads((ROOT / "reports" / "phase5" / "phase55_combined_backtest" / "before_snapshot.json").read_text())
    key = "docs/trading journal/Trading_Journal_Sep2025_Aug2026 REPORT.xlsx"
    assert hashlib.sha256(JOURNAL.read_bytes()).hexdigest() == snap["hashes"][key]


@needs_bundle
def test_weekend_rows_are_manual_journal_inconsistencies_in_every_configuration():
    with open(OUT / "mismatch_root_causes.csv", newline="") as f:
        rc = list(csv.DictReader(f))
    wk = [r for r in rc if r["date"] in {"2025-10-11", "2026-02-14", "2026-08-15", "2026-08-22", "2026-08-29"} and r["side"] == "MANUAL_ONLY"]
    assert len(wk) == 15 and {r["root_cause_primary"] for r in wk} == {"MANUAL_JOURNAL_INCONSISTENCY"}


@needs_bundle
def test_idle_day_count_and_second_trade_explanations_are_consistent_with_the_csvs():
    st = json.loads((OUT / "phase56_state.json").read_text())
    with open(ROOT / "reports" / "phase5" / "phase55_combined_backtest" / "all_executed_trades.csv", newline="") as f:
        tr = list(csv.DictReader(f))
    with open(OUT / "manual_vs_automated_matching.csv", newline="") as f:
        mt = [r for r in csv.DictReader(f) if r["journal_row"]]
    with open(OUT / "automated_only_trades.csv", newline="") as f:
        ao = list(csv.DictReader(f))
    for k in "ABC":
        days = {t["date"] for t in tr if t["config"] == k}
        idle = sum(1 for r in mt if r["config"] == k and r["date"] not in days and "WEEKEND_DATE_NOT_AN_EXCHANGE_SESSION" not in r["journal_flags"])
        assert idle == st["matching"][k]["manual_rows_on_dates_with_no_automated_trade"] > 0
    assert all("first valid signal" not in r["evidence"] for r in ao if r["trade_id"].split("-")[1] == "2")


def test_tolerant_stage_requires_nonzero_difference_within_fifteen_minutes():
    m = R.match([jr(1, "2026-01-05", "10:00", "IRF")], [tr("a", "2026-01-05", "IRF", "09:50")])
    assert not m["strict"] and [(p.delta_minutes, p.stage) for p in m["tolerant"]] == [(-10, "TIME_TOLERANT")]
