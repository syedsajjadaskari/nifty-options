"""Phase 3.1: journal normalisation, deterministic one-to-one matching, the rejection chain, the interference matrix and the root-cause mapping.
Synthetic days only (the real-data run is audited separately)."""

from __future__ import annotations

import pytest
import test_phase23_day_controller as T
from synthetic import ctx

from nifty_trading.research import phase31 as R
from nifty_trading.strategies import ProposalConfig
from nifty_trading.strategies.trading_day import DayRules, run_trading_day

D = T.DAY  # 2026-01-12, an ordinary Monday
PROPS = ProposalConfig()


def jrow(sheet_row, hhmm, strat, outcome, day="2026-01-12"):
    return {"sheet_row": sheet_row, "sl_no": sheet_row - 2, "date": day, "time_raw": hhmm, "time_cell_type": "str", "time": hhmm, "strategy_entered": strat, "outcome_entered": outcome}


def norm(rows, alt=None, sessions=None):
    return R.normalize_journal(rows, [], alt or {}, sessions or {r["date"]: "VALID" for r in rows})


def timeline(records, over=None, rules=None, day=D):
    c = ctx([(100, 101, 99, 100)] * 3)
    res = run_trading_day(day, records, T.bars(over), T.TradeConfig(), rules or DayRules())
    return R.DayTimeline(day, c, records, res)


SHORT_PATH = {"10:00": (T.E, T.E, T.E - 27, T.E - 27), "10:40": (T.E, T.E, T.E - 60, T.E - 60)}  # an IRF SHORT filled at 09:30 reaches Target 2
LONG_SL30 = T.LONG_SL30


# ======================================================================= the journal is normalised without silently changing anything
@pytest.mark.rules("EXE-SEL-001")
def test_normalisation_preserves_original_values_and_flags_nonconforming_rows():
    rows = [jrow(3, "09:15", "ORB", "BE"), jrow(4, "10:20", "pdr ", "BE"), jrow(5, "09:25", "IRF", "SL", "2026-01-13"), jrow(6, "09:25", "IRF", "SL", "2026-01-13"),
            jrow(7, "12:56", "IRF", "Target", "2026-01-14"), jrow(8, "09:15", "ORB", "SL", "2026-01-17")]
    n = {r["journal_row"]: r for r in norm(rows, sessions={"2026-01-12": "VALID", "2026-01-13": "VALID", "2026-01-14": "VALID"})}
    assert n[4]["strategy_entered"] == "pdr " and n[4]["strategy_normalized"] == "PDR"  # the entered label survives next to the normalised one
    assert n[3]["conforms_to_approved_rules"] and not n[4]["conforms_to_approved_rules"] and "SECOND_TRADE_NOT_ALLOWED(first_trade_outcome=BE)" in n[4]["nonconformity"]
    assert n[5]["duplicate_flag"] and n[6]["duplicate_flag"] and n[5]["trade_no_in_day"] == 1 and n[6]["trade_no_in_day"] == 2
    assert "SECOND_TRADE_NOT_ALLOWED" in n[6]["nonconformity"] or "SECOND_TRADE_NOT_PDR_PDS" in n[6]["nonconformity"]
    assert n[7]["estimated_fill_time"] == "13:01" and "ENTRY_AFTER_13_00_CUTOFF" in n[7]["nonconformity"]  # label 12:56 + 5 min fill
    assert n[8]["session_status"] == "NO_SESSION" and "DATE_HAS_NO_VENDOR_SESSION" in n[8]["nonconformity"] and n[8]["weekday"] == "Sat"
    assert n[3]["direction"] == "UNKNOWN" and n[4]["direction"] == "LONG" and n[3]["entry_level"] == ""  # nothing is invented
    assert (n[3]["derived_pnl_rs_low"], n[3]["derived_pnl_rs_high"]) == (27 * 195, 27 * 195)  # BE under the report's rule
    assert (n[7]["derived_pnl_rs_low"], n[7]["derived_pnl_rs_high"]) == (27 * 195 + 60 * 195,) * 2


@pytest.mark.rules("EXE-SEL-001")
def test_the_second_trade_after_a_full_stop_must_be_pdr_or_pds():
    ok = {r["journal_row"]: r for r in norm([jrow(3, "09:15", "ORB", "SL"), jrow(4, "10:20", "PDR", "Target")])}
    assert ok[4]["conforms_to_approved_rules"]
    bad = {r["journal_row"]: r for r in norm([jrow(3, "09:15", "ORB", "SL"), jrow(4, "10:20", "IRF", "Target")])}
    assert "SECOND_TRADE_NOT_PDR_PDS(IRF)" in bad[4]["nonconformity"]
    third = {r["journal_row"]: r for r in norm([jrow(3, "09:15", "ORB", "SL"), jrow(4, "10:20", "PDR", "SL"), jrow(5, "11:20", "PDS", "SL")])}
    assert "THIRD_TRADE_NOT_ALLOWED" in third[5]["nonconformity"]


# ======================================================================= deterministic one-to-one matching
@pytest.mark.rules("SEL-FIRST-001")
def test_exact_then_time_shifted_matching_is_one_to_one_and_never_uses_pnl():
    tl = {D: timeline([T.sig("IRF", "09:35")], SHORT_PATH)}  # automated IRF: candle 09:30-09:35, filled 09:35
    # a manual label equal to the candle START (09:30) is an exact match
    rows, used = R.match_manual_to_automated(norm([jrow(3, "09:30", "IRF", "Target")]), tl, PROPS)
    assert rows[0]["classification"] == "EXACT_MATCH" and rows[0]["delta_minutes"] == 0 and len(used) == 1
    # 10 minutes later is a labelled time-shifted match; 20 minutes later is not a match at all
    near, _ = R.match_manual_to_automated(norm([jrow(3, "09:40", "IRF", "SL")]), tl, PROPS)
    assert near[0]["classification"] == "TIME_SHIFTED_MATCH" and near[0]["delta_minutes"] == -10
    far, _ = R.match_manual_to_automated(norm([jrow(3, "09:50", "IRF", "Target")]), tl, PROPS)
    assert far[0]["classification"] not in ("EXACT_MATCH", "TIME_SHIFTED_MATCH")
    # an outcome mismatch never prevents a match (the P&L / outcome is not a matching criterion)
    assert near[0]["outcome_agrees_loosely"] is False and rows[0]["outcome_agrees_loosely"] is True


@pytest.mark.rules("SEL-FIRST-001")
def test_two_manual_rows_can_never_share_one_automated_trade_and_exact_beats_shifted():
    tl = {D: timeline([T.sig("IRF", "09:35")], SHORT_PATH)}
    rows, used = R.match_manual_to_automated(norm([jrow(3, "09:35", "IRF", "SL"), jrow(4, "09:30", "IRF", "Target")]), tl, PROPS)
    by = {r["journal_row"]: r for r in rows}
    assert by[4]["classification"] == "EXACT_MATCH"  # the exact candidate takes the trade even though it is listed later
    assert by[3]["classification"] != "TIME_SHIFTED_MATCH" and len(used) == 1  # the other row cannot reuse it


@pytest.mark.rules("SEL-FIRST-001")
def test_the_matching_is_deterministic_and_independent_of_the_input_order():
    tl = {D: timeline([T.sig("IRF", "09:35"), T.sig("IRF", "10:05")], {**SHORT_PATH, "10:40": (T.E, T.E, T.E, T.E)})}
    rows_in = [jrow(3, "09:30", "IRF", "SL"), jrow(4, "10:00", "IRF", "Target")]
    a, _ = R.match_manual_to_automated(norm(rows_in), tl, PROPS)
    b, _ = R.match_manual_to_automated(norm(list(reversed(rows_in))), tl, PROPS)
    key = lambda rs: sorted((r["journal_row"], r["classification"], r["auto_candle_start"]) for r in rs)  # noqa: E731
    assert key(a) == key(b)


@pytest.mark.rules("SEL-FIRST-001")
def test_an_alternate_label_match_is_flagged_and_only_tried_after_the_entered_label():
    tl = {D: timeline([T.sig("PDR", "09:35", "LONG")], {"10:00": (T.E, T.E + 27, T.E, T.E + 27), "10:20": (T.E, T.E + 70, T.E, T.E + 70)})}
    rows, _ = R.match_manual_to_automated(norm([jrow(3, "09:30", "ORB", "Target")], alt={3: "PDR"}), tl, PROPS)
    assert rows[0]["classification"] == "EXACT_MATCH" and rows[0]["matched_via_alternate_label"] is True and rows[0]["matched_strategy"] == "PDR"
    direct, _ = R.match_manual_to_automated(norm([jrow(3, "09:30", "PDR", "Target")], alt={3: "ORB"}), tl, PROPS)
    assert direct[0]["matched_via_alternate_label"] is False


# ======================================================================= the rejection chain of a manual trade that has no executed counterpart
def cls(rows):
    return rows[0]["classification"], rows[0].get("blocked_by", ""), str(rows[0].get("detail", ""))


@pytest.mark.rules("SEL-ACTIVE-001")
def test_a_manual_trade_whose_signal_was_ignored_while_a_position_was_active_is_portfolio_rejected_with_the_blocker():
    tl = {D: timeline([T.sig("IRF", "09:35"), T.sig("RF", "09:50", "LONG")], {"12:00": (T.E, T.E, T.E - 60, T.E - 60)})}  # IRF still open at 09:50
    rows, _ = R.match_manual_to_automated(norm([jrow(3, "09:45", "RF", "Target")]), tl, PROPS)
    c, blocker, detail = cls(rows)
    assert c == "SIGNAL_REJECTED_BY_PORTFOLIO_CONTROLLER" and blocker == "IRF#1" and detail.startswith("POSITION_ACTIVE")
    assert R.root_cause_manual(rows[0])[0] == "PORTFOLIO_COMPETITION"


@pytest.mark.rules("DAY-SL-001")
def test_after_a_day_finished_and_in_the_second_trade_state_the_blockers_are_named():
    tl = {D: timeline([T.sig("ORB", "09:25", "LONG", "Method 1"), T.sig("IRF", "11:30")], {**LONG_SL30})}  # ORB stopped out at 09:40; only a PDR/PDS signal may follow
    rows, _ = R.match_manual_to_automated(norm([jrow(3, "11:25", "IRF", "Target")]), tl, PROPS)
    c, blocker, detail = cls(rows)
    assert c == "SIGNAL_REJECTED_BY_PORTFOLIO_CONTROLLER" and detail.startswith("SECOND_TRADE_RESTRICTED") and blocker.startswith("ORB")


@pytest.mark.rules("SEL-TIE-001")
def test_a_collision_is_reported_as_such_for_both_colliding_manual_candidates():
    tl = {D: timeline([T.sig("PDR", "09:35", "LONG"), T.sig("RF", "09:35", "LONG")])}
    for strat in ("PDR", "RF"):
        rows, _ = R.match_manual_to_automated(norm([jrow(3, "09:30", strat, "SL")]), tl, PROPS)
        c, blocker, detail = cls(rows)
        assert c == "SIGNAL_REJECTED_BY_PORTFOLIO_CONTROLLER" and blocker == "COLLISION" and "SIMULTANEOUS_SIGNAL_CONFLICT" in detail
    ev = {x["strategy"]: x["event"] for x in R.timeline_rows(tl[D], "t", []) if x["signal_status"] == "CONFIRMED"}
    assert ev == {"PDR": "CONFLICT", "RF": "CONFLICT"}


@pytest.mark.rules("ENTRY-CUTOFF-001")
def test_cutoff_rejection_and_missing_signal_and_journal_conflict_classes():
    tl = {D: timeline([T.sig("IRF", "13:05")])}
    late, _ = R.match_manual_to_automated(norm([jrow(3, "13:00", "IRF", "Target")]), tl, PROPS)
    assert cls(late)[0] == "SIGNAL_REJECTED_BY_CUTOFF"
    none, _ = R.match_manual_to_automated(norm([jrow(3, "09:15", "IRF", "Target")]), {D: timeline([])}, PROPS)
    assert cls(none)[0] == "MISSING_AUTOMATED_SIGNAL" and none[0]["chain"].startswith("NO_CONFIRMED_SIGNAL_WITHIN_TOLERANCE")
    sat, _ = R.match_manual_to_automated(norm([jrow(3, "09:15", "ORB", "SL", "2026-01-17")], sessions={}), tl, PROPS)
    assert cls(sat)[0] == "MANUAL_JOURNAL_CONFLICT" and R.root_cause_manual(sat[0])[0] == "JOURNAL_INCONSISTENCY"


@pytest.mark.rules("SEL-FIRST-001")
def test_a_failed_setup_is_an_entry_rule_rejection_with_all_failed_methods_listed():
    from nifty_trading.strategies.base import SignalRecord
    base = T.sig("ORB", "09:20", "LONG", "Method 1")
    f1 = SignalRecord(**{**base.__dict__, "signal_status": "INVALIDATED", "invalidation_reason": "TREND:EMA_PREV_SESSION_CLOSE wrong side", "rule_ids_failed": ["ORB-TREND-001"]})
    f2 = SignalRecord(**{**base.__dict__, "method": "Method 2", "signal_status": "INVALIDATED", "invalidation_reason": "TRENDLINE_NOT_SUPPORTIVE"})
    tl = {D: timeline([f1, f2])}
    rows, _ = R.match_manual_to_automated(norm([jrow(3, "09:15", "ORB", "Target")]), tl, PROPS)
    assert rows[0]["classification"] == "SIGNAL_REJECTED_BY_ENTRY_RULE" and "Method 1:TREND" in rows[0]["all_failed_setups"] and "Method 2:TRENDLINE" in rows[0]["all_failed_setups"]
    assert R.root_cause_manual(rows[0]) == ("TREND_FILTER", "")


# ======================================================================= root causes, interference, portfolio state
@pytest.mark.rules("SEL-ACTIVE-001")
def test_root_cause_mapping_covers_the_documented_categories():
    f = R.root_cause_manual
    assert f({"classification": "SIGNAL_REJECTED_BY_ENTRY_RULE", "detail": "CANDLE_QUALITY(x)"})[0] == "PROPOSED_NUMERICAL_THRESHOLD"
    assert f({"classification": "SIGNAL_REJECTED_BY_ENTRY_RULE", "detail": "GAP_UP_OPEN_NOT_ABOVE_ZONE; failed=PDR-011"})[0] == "ZONE_SELECTION"
    assert f({"classification": "SIGNAL_REJECTED_BY_ENTRY_RULE", "detail": "NO_RETURN_INSIDE_BEFORE_SESSION_END"})[0] == "ENTRY_SEQUENCE"
    assert f({"classification": "MISSING_AUTOMATED_SIGNAL", "detail": "FIRST_CANDLE_DID_NOT_CLOSE_BEYOND_PREV_DAY_HIGH_OR_LOW"})[0] == "SOURCE_AMBIGUITY"
    assert f({"classification": "MISSING_AUTOMATED_SIGNAL", "detail": "SOMETHING_NEW"})[0] == "UNKNOWN"
    assert f({"classification": "EXACT_MATCH"}) == ("", "")
    assert f({"classification": "MISSING_AUTOMATED_SIGNAL", "detail": "NO_GAP_UP", "phase21_status": "UNRESOLVED"}) == ("SOURCE_AMBIGUITY", "OPEN_PRICE_CONVENTION;JOURNAL_INCONSISTENCY")


@pytest.mark.rules("SEL-ACTIVE-001")
def test_interference_matrix_counts_come_from_the_timeline_not_from_estimates():
    tl = {D: timeline([T.sig("ORB", "09:25", "LONG", "Method 1"), T.sig("IRF", "09:40"), T.sig("IRF", "09:55"), T.sig("PDR", "10:05", "LONG")], {"12:00": (T.E, T.E + 30, T.E, T.E + 30)})}
    sig, days = R.interference_matrix(tl)
    assert sig[("ORB", "IRF", "IGNORED")] == 2 and sig[("ORB", "PDR", "IGNORED")] == 1 and days[("ORB", "IRF", "IGNORED")] == 1
    assert not any(k[1] == "ORB" for k in sig)  # nothing can block ORB: it is the earliest strategy of the session


@pytest.mark.rules("SEL-ACTIVE-001")
def test_portfolio_state_replay_matches_the_controller():
    tl = timeline([T.sig("ORB", "09:25", "LONG", "Method 1")], LONG_SL30)
    ts = lambda hhmm: T.at(hhmm)  # noqa: E731
    assert R.state_at(tl, ts("09:20")) == "READY_FOR_FIRST_TRADE"
    assert R.state_at(tl, ts("09:30")) == "FIRST_TRADE_ACTIVE"
    assert R.state_at(tl, ts("09:40")) == "FIRST_TRADE_ACTIVE"  # the exit happens inside the 09:40 bar
    assert R.state_at(tl, ts("09:41")) == "SECOND_TRADE_ELIGIBLE"
    done = timeline([T.sig("IRF", "09:35")], SHORT_PATH)
    assert R.state_at(done, ts("11:00")) == "DAY_FINISHED"


@pytest.mark.rules("DATA-TIME-001")
def test_the_candle_label_convention_signal_time_is_the_candle_end():
    """A journal 'entry time' is the START of the entry candle: the automated signal time (candle end) is 5 minutes later and the fill is that minute's open."""
    tl = timeline([T.sig("IRF", "09:35")], SHORT_PATH)
    t = tl.result.trades[0]
    assert f"{t.signal.signal_candle_start:%H:%M}" == "09:30" and f"{t.fill_timestamp:%H:%M}" == "09:35"
    assert R._cstart(t.signal) == R._minutes("09:30")


@pytest.mark.rules("DATA-TIME-001")
def test_probe_pdr_reports_when_the_zone_is_never_intersected():
    from synthetic import ctx as sctx
    prev = {"cands": [(23960, 23970, 23950, 23965), (23980, 24000, 23970, 23975), (23975, 23985, 23960, 23962)] * 4, "close": 23950.0}
    c = sctx([(24050, 24060, 24040, 24055)] * 6, prev=prev)  # gap up, price stays far above any zone
    tl = R.DayTimeline(D, c, [], T.run_trading_day(D, [], T.bars(), T.TradeConfig(), DayRules()))
    p = R.probe("PDR", tl, PROPS)
    assert p["code"] in ("NO_ZONE_CANDIDATE", "ZONE_NEVER_INTERSECTED_BY_ANY_CANDLE") and p["gap_dir"] == "UP"


# ======================================================================= the delivered files reconcile with each other and with the audited Phase 3.0 ledgers
ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
P31 = ROOT / "reports" / "phase3" / "phase31"
needs_outputs = pytest.mark.skipif(not (P31 / "manual_vs_automated.csv").exists(), reason="Phase 3.1 outputs not generated")


@needs_outputs
@pytest.mark.rules("EXE-SEL-001")
def test_phase30_ledgers_are_untouched():
    import hashlib
    import json
    h = json.loads((P31 / "phase30_ledger_hashes.json").read_text())["hashes"]
    for rel, digest in h.items():
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == digest, rel


@needs_outputs
@pytest.mark.rules("SEL-FIRST-001")
def test_the_output_counts_reconcile_exactly():
    import pandas as pd
    m = pd.read_csv(P31 / "manual_vs_automated.csv")
    e = pd.read_csv(P31 / "extra_automated_trades.csv")
    j = pd.read_csv(P31 / "manual_journal_normalized.csv")
    led = pd.read_csv(ROOT / "reports" / "phase3" / "baseline" / "trades.csv")
    matched = m[m.classification.isin(["EXACT_MATCH", "TIME_SHIFTED_MATCH"])]
    assert len(m) == len(j) == 190 and m.journal_row.is_unique
    assert len(matched) + len(e) == len(led) == 213  # every automated trade is either matched or an extra
    assert len(matched) + (len(m) - len(matched)) == len(m)
    # one-to-one: no automated trade is matched twice
    assert not matched.duplicated(["date", "matched_strategy", "auto_candle_start", "matched_method"]).any()
    # the extras and the matched trades are disjoint and together cover the ledger
    def key(df, s, c):
        return set(zip(df.date, df[s], df[c], strict=True))
    assert not key(matched, "matched_strategy", "auto_candle_start") & key(e, "strategy", "candle_start")
    start = led.signal_time.map(lambda t: f"{(int(t[:2]) * 60 + int(t[3:]) - 5) // 60:02d}:{(int(t[:2]) * 60 + int(t[3:]) - 5) % 60:02d}")
    ledger_keys = set(zip(led.date, led.strategy, start, strict=True))
    assert key(matched, "matched_strategy", "auto_candle_start") | key(e, "strategy", "candle_start") == ledger_keys  # matched + extras == the ledger, exactly
    # every journal row has exactly one classification from the documented list
    assert set(m.classification) <= set(R.CLASSES)


@needs_outputs
@pytest.mark.rules("SEL-ACTIVE-001")
def test_every_timeline_execution_is_a_ledger_trade_and_every_ledger_trade_is_in_the_timeline():
    import pandas as pd
    t = pd.read_csv(P31 / "daily_signal_timelines.csv")
    led = pd.read_csv(ROOT / "reports" / "phase3" / "baseline" / "trades.csv")
    ex = t[t.event == "EXECUTED"]
    assert len(ex) == len(led)
    assert sorted(zip(ex.date, ex.strategy, strict=True)) == sorted(zip(led.date, led.strategy, strict=True))


# ======================================================================= QA hardening (independent review findings)
@pytest.mark.rules("SEL-FIRST-001")
def test_the_time_tolerance_boundary_is_inclusive_at_15_minutes_and_a_tie_goes_to_the_earlier_candle():
    tl = {D: timeline([T.sig("IRF", "09:35")], SHORT_PATH)}  # candle start 09:30
    at15, _ = R.match_manual_to_automated(norm([jrow(3, "09:45", "IRF", "Target")]), tl, PROPS)
    at16, _ = R.match_manual_to_automated(norm([jrow(3, "09:46", "IRF", "Target")]), tl, PROPS)
    assert at15[0]["classification"] == "TIME_SHIFTED_MATCH" and at15[0]["delta_minutes"] == -15
    assert at16[0]["classification"] not in ("EXACT_MATCH", "TIME_SHIFTED_MATCH")
    # two executed PDR trades whose candles (09:15 and 09:45) are both exactly 15 minutes from the label 09:30: the earlier one is taken
    tie = {D: timeline([T.sig("PDR", "09:20"), T.sig("PDR", "09:50")], {"09:40": (T.E, T.E, T.E - 35, T.E - 35)})}
    assert [t.signal.signal_candle_start.strftime("%H:%M") for t in tie[D].result.trades] == ["09:15", "09:45"]
    rows, _ = R.match_manual_to_automated(norm([jrow(3, "09:30", "PDR", "SL")]), tie, PROPS)
    assert rows[0]["classification"] == "TIME_SHIFTED_MATCH" and rows[0]["auto_candle_start"] == "09:15"


@pytest.mark.rules("SEL-ACTIVE-001")
def test_blockers_and_states_never_use_information_from_after_the_signal_time():
    tl = timeline([T.sig("PDR", "09:35", "LONG"), T.sig("RF", "09:35", "LONG")])  # same-minute collision at 09:35 leaves the day unresolved, no trade
    early, late = T.at("09:20"), T.at("09:40")
    assert R.blocker_of(tl, early, "DAY_FINISHED") == ""  # the 09:35 collision is in the future of a 09:20 signal
    assert R.blocker_of(tl, late, "DAY_FINISHED") == "COLLISION"
    assert R.state_at(tl, early) == "READY_FOR_FIRST_TRADE" and R.state_at(tl, late) == "UNRESOLVED_EXECUTION"
    tr = timeline([T.sig("ORB", "09:20", method="Method 1")], T.LONG_SL30)
    assert R.blocker_of(tr, T.at("09:10"), "DAY_FINISHED") == ""  # trade 1 is filled only at 09:20
    assert R.blocker_of(tr, T.at("10:00"), "DAY_FINISHED") == "ORB#1"


@pytest.mark.rules("SEL-FIRST-001")
def test_an_end_of_session_pending_setup_does_not_explain_an_earlier_manual_decision():
    from nifty_trading.strategies.base import SignalRecord
    base = T.sig("IRF", "14:55")
    pending = SignalRecord(**{**base.__dict__, "signal_status": "INCOMPLETE_AT_EOD", "invalidation_reason": "SESSION_ENDED_BEFORE_CONFIRMATION"})
    rows, _ = R.match_manual_to_automated(norm([jrow(3, "09:45", "IRF", "Target")]), {D: timeline([pending])}, PROPS)
    assert rows[0]["classification"] == "MISSING_AUTOMATED_SIGNAL" and "SETUP_PENDING_NEVER_CONFIRMED" in rows[0]["chain"]
    near, _ = R.match_manual_to_automated(norm([jrow(3, "14:50", "IRF", "Target")]), {D: timeline([pending])}, PROPS)
    assert near[0]["classification"] == "SIGNAL_REJECTED_BY_ENTRY_RULE"  # within the tolerance of its stamp it does count
    far_signal, _ = R.match_manual_to_automated(norm([jrow(3, "09:15", "IRF", "Target")]), {D: timeline([T.sig("IRF", "13:05")])}, PROPS)
    assert far_signal[0]["classification"] == "MISSING_AUTOMATED_SIGNAL" and "NEAREST_CONFIRMED" in far_signal[0]["chain"]  # not "no signal at all"


@pytest.mark.rules("SEL-FIRST-001")
def test_trendline_is_not_a_trend_filter_and_an_unmapped_detail_is_unknown_not_a_default_cause():
    row = {"classification": "SIGNAL_REJECTED_BY_ENTRY_RULE", "detail": "TRENDLINE_NOT_SUPPORTIVE; failed=", "phase21_status": "VALID"}
    assert R.root_cause_manual(row)[0] == "SOURCE_AMBIGUITY"
    assert R.root_cause_manual({**row, "detail": "TREND:EMA_PREV_SESSION_CLOSE wrong side"})[0] == "TREND_FILTER"
    primary, secondary = R.root_cause_manual({**row, "detail": "SOMETHING_NEW"})
    assert primary == "UNKNOWN" and "UNMAPPED_ENTRY_RULE_DETAIL" in secondary
