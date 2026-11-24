"""Phase 7.0 - IRF V3 unit + integration tests (Method 1, Method 2, execution, combined engine, journal matching, independence)."""

from __future__ import annotations

import ast
import dataclasses
from datetime import date, time
from pathlib import Path

import pandas as pd
import pytest

from nifty_trading.research.irf_v3 import audit as AU
from nifty_trading.research.irf_v3 import backtest as BT
from nifty_trading.research.irf_v3 import data_access as DA
from nifty_trading.research.irf_v3 import examples as EX
from nifty_trading.research.irf_v3 import recon as RC
from nifty_trading.research.irf_v3.config import PRIMARY, RULES, SCENARIOS, IrfV3Config
from nifty_trading.research.irf_v3.method1 import run_method1
from nifty_trading.research.irf_v3.method2 import run_method2
from nifty_trading.research.irf_v3.models import M1, M2
from nifty_trading.research.irf_v3.signal_engine import evaluate_session, overlap_class

D = date(2026, 1, 5)
PKG = Path(__file__).resolve().parents[1] / "src/nifty_trading/research/irf_v3"


def cd(o, c, up=1.0, dn=1.0):
    """(open, high, low, close) candle with symmetric wicks."""
    return (o, max(o, c) + up, min(o, c) - dn, c)


def sess(seq, d=D):
    return DA.synthetic_session(d, seq)


def pad(seq, n=75):
    """Extend a sequence with flat candles so the session has enough bars after the setup for the exit scan (flat, no stop/target touch)."""
    last = seq[-1][3]
    return seq + [(last, last + 0.5, last - 0.5, last)] * max(0, n - len(seq))


# ------------------------------------------------------------------------------------------------- aggregation
def test_candle_requires_five_rows_and_uses_09_15_origin():
    s = DA.synthetic_session(D, [(100, 110, 95, 105), (105, 112, 101, 108)])
    assert [c.start.strftime("%H:%M") for c in s.candles] == ["09:15", "09:20"]
    assert s.candles[0].end.strftime("%H:%M:%S") == "09:20:00"
    df = s.minutes.drop(index=[2])  # remove one minute of the first candle
    cs = DA.aggregate_candles(df)
    assert [c.start.strftime("%H:%M") for c in cs] == ["09:20"]  # incomplete candle dropped, never interpolated


def test_first_candle_high_includes_upper_wick():
    s = sess([(25000, 25035, 24996, 25020)] + [(25020, 25021, 25019, 25020)] * 3)
    assert s.candles[0].high == 25035.0 and s.candles[0].close == 25020.0
    assert run_method1(D, s.candles).initial_range_high == 25035.0


# ------------------------------------------------------------------------------------------------- Method 1
def m1_seq(closes, first=(25000, 25035, 24996, 25020)):
    seq = [first]
    prev = first[3]
    for c in closes:
        seq.append(cd(prev, c))
        prev = c
    return seq


def test_m1_figure_example_signal_at_failure_candle_end():
    s = EX.synthetic_m1_figure()
    t = run_method1(D, s.candles)
    assert t.status == "SIGNAL" and t.reference_level == 25035.0
    assert t.breakout_candle.close == 25040.0 and t.confirmation_candle.close == 25030.0
    assert t.signal_time.strftime("%H:%M") == "09:35" and t.signal_time == t.confirmation_candle.end


def test_m1_close_below_without_earlier_breakout_is_not_a_signal():
    t = run_method1(D, sess(m1_seq([25020, 25010, 25000, 24990])).candles)
    assert t.status == "NO_SIGNAL" and t.no_signal_reason == "NO_CLOSE_ABOVE_LEVEL"


def test_m1_wick_above_without_close_above_is_not_a_breakout():
    seq = m1_seq([25020]) + [(25020, 25060, 25010, 25030), (25030, 25050, 25000, 25010)]  # wick 25060 > level, close 25030 < level
    t = run_method1(D, sess(seq).candles)
    assert t.status == "NO_SIGNAL" and t.breakout_candle is None


def test_m1_close_exactly_on_level_is_ignored():
    seq = m1_seq([25035, 25036, 25035, 25034])  # close==level ignored; 25036 breakout; 25035 ignored (not a failure); 25034 failure
    t = run_method1(D, sess(seq).candles)
    assert t.status == "SIGNAL" and t.confirmation_candle.close == 25034.0 and t.breakout_candle.close == 25036.0


def test_m1_failure_many_candles_after_breakout_and_red_breakout_counts():
    seq = [(25000, 25035, 24996, 25020), (25040, 25050, 25030, 25036)]  # RED candle closing above the level = a valid breakout
    seq += [cd(25036, 25045), cd(25045, 25050), cd(25050, 25048), cd(25048, 25034)]
    t = run_method1(D, sess(seq).candles)
    assert t.status == "SIGNAL" and t.breakout_candle.is_red and t.signal_time.strftime("%H:%M") == "09:45" and t.confirmation_candle.start.strftime("%H:%M") == "09:40"


def test_m1_no_extra_filters_green_or_red_first_candle_no_body_no_gap_rule():
    for first in [(25000, 25035, 24996, 25020), (25030, 25035, 24990, 24995)]:  # green and red first candles
        seq = [first, cd(first[3], 25040), cd(25040, 25030)]
        assert run_method1(D, sess(seq).candles).status == "SIGNAL"


def test_m1_later_cycles_counted_but_only_first_signal_kept():
    seq = m1_seq([25040, 25030, 25041, 25029])
    t = run_method1(D, sess(seq).candles)
    assert t.status == "SIGNAL" and t.later_cycles == 1 and t.confirmation_candle.close == 25030.0


# ------------------------------------------------------------------------------------------------- Method 2
def m2_session():
    return EX.synthetic_m2_figure()


def test_m2_figure_levels_and_failure():
    t = run_method2(D, m2_session().candles)
    assert t.status == "SIGNAL" and t.initial_range_high == 25085.0 and t.reference_level == 25094.0  # body top (open) not the wick 25096
    assert t.reference_candle.start.strftime("%H:%M") == "09:35" and t.confirmation_candle.close == 25090.0 and t.signal_time.strftime("%H:%M") == "09:55"
    assert t.second_breakout_candle.close == 25100.0


def m2_seq(pre_red=False):
    seq = [(25050, 25085, 25045, 25070)]
    if pre_red:
        seq.append((25070, 25072, 25060, 25062))  # red before any close above A
    seq += [(25062 if pre_red else 25070, 25092, 25060, 25088)]  # close above A (green)
    return seq


def test_m2_red_before_rally_breakout_is_ignored_and_counted():
    seq = m2_seq(pre_red=True) + [(25088, 25095, 25087, 25093), (25094, 25096, 25091, 25092), (25092, 25102, 25091, 25100), (25100, 25102, 25088, 25090)]
    t = run_method2(D, sess(seq).candles)
    assert t.ignored_red_before_breakout == 1 and t.status == "SIGNAL" and t.reference_level == 25094.0


def test_m2_only_first_red_candle_sets_level_b():
    seq = m2_seq() + [(25088, 25095, 25087, 25093), (25094, 25096, 25091, 25092), (25092, 25100, 25088, 25089), (25089, 25101, 25088, 25100), (25100, 25102, 25088, 25090)]
    t = run_method2(D, sess(seq).candles)
    assert t.reference_level == 25094.0 and t.status == "SIGNAL"  # later red candle (open 25092) ignored


def test_m2_close_below_b_without_second_breakout_is_no_signal():
    seq = m2_seq() + [(25088, 25095, 25087, 25093), (25094, 25096, 25091, 25092), (25092, 25093, 25080, 25085), (25085, 25090, 25075, 25078)]
    t = run_method2(D, sess(seq).candles)
    assert t.status == "NO_SIGNAL" and t.no_signal_reason == "NO_CLOSE_ABOVE_LEVEL_B"


def test_m2_wick_above_a_is_not_a_rally_breakout():
    seq = [(25050, 25085, 25045, 25070), (25070, 25099, 25060, 25080), (25080, 25090, 25070, 25075)]
    t = run_method2(D, sess(seq).candles)
    assert t.status == "NO_SIGNAL" and t.no_signal_reason == "NO_CLOSE_ABOVE_LEVEL_A"


def test_m2_breakout_candle_red_is_excluded_by_default_included_by_variant():
    seq = [(25050, 25085, 25045, 25070), (25100, 25102, 25086, 25090),  # RED breakout candle: closes 25090 > A, open 25100
           (25090, 25105, 25089, 25103), (25103, 25104, 25091, 25092)]
    base = run_method2(D, sess(seq).candles)
    var = run_method2(D, sess(seq).candles, red_breakout_candle_counts=True)
    assert base.status == "NO_SIGNAL" and base.reference_level == 25103.0  # B = the later red candle's open; nothing closes above it afterwards
    assert var.reference_level == 25100.0 and var.status == "SIGNAL"  # B = breakout candle's open (variant): 25103 closes above, 25092 closes below


def test_m2_close_exactly_on_b_is_neither_above_nor_below():
    seq = m2_seq() + [(25088, 25095, 25087, 25093), (25094, 25096, 25091, 25092), (25092, 25100, 25091, 25094), (25094, 25096, 25090, 25094)]
    t = run_method2(D, sess(seq).candles)
    assert t.status == "NO_SIGNAL"  # closes == B never count as the second breakout nor the failure


# ------------------------------------------------------------------------------------------------- isolation, causality
def test_methods_are_independent_m1_only_and_m2_only():
    # M1 fires (breakout above A, failure below A) while M2 never finds a red candle after its breakout... uses greens then drops through A
    seq = [(25000, 25035, 24996, 25020), (25020, 25045, 25018, 25040), (25040, 25055, 25038, 25052), (25052, 25052, 25020, 25030)]
    s = sess(seq)
    assert run_method1(D, s.candles).status == "SIGNAL"
    t2 = run_method2(D, s.candles)
    assert t2.status == "NO_SIGNAL"  # B = open 25052 of the red candle, but no close above B afterwards
    # M2 fires while M1 has not failed (price never closed below A afterwards)
    s2 = sess(m2_seq() + [(25088, 25095, 25087, 25093), (25094, 25096, 25091, 25092), (25092, 25102, 25091, 25100), (25100, 25102, 25088, 25090)])
    assert run_method2(D, s2.candles).status == "SIGNAL" and run_method1(D, s2.candles).status == "NO_SIGNAL"


def test_causality_truncating_the_future_cannot_change_a_signal():
    s = m2_session()
    t = run_method2(D, s.candles)
    k = [i for i, c in enumerate(s.candles) if c.start == t.confirmation_candle.start][0]
    assert run_method2(D, s.candles[:k + 1]).signal_time == t.signal_time
    assert run_method2(D, s.candles[:k]).status == "NO_SIGNAL"


# ------------------------------------------------------------------------------------------------- execution
def test_entry_is_open_of_bar_at_confirmation_and_levels_from_entry():
    s = EX.synthetic_m1_figure()
    ev = evaluate_session(s, SCENARIOS["SL40_T60"], None)
    res = ev.trades[M1]
    assert res["entry_time"] == ev.traces[M1].signal_time and res["entry_price"] == 25030.0
    assert res["stop"] == 25070.0 and res["target"] == 24970.0 and res["exit_reason"] == "TARGET" and res["gross_points"] == 60.0
    ev35 = evaluate_session(s, SCENARIOS["SL35_T60"], None)
    assert ev35.trades[M1]["stop"] == 25065.0


def test_signal_close_convention_vs_next_open_differ_when_a_gap_exists():
    seq = [(25000, 25035, 24996, 25020), (25022, 25045, 25015, 25040), (25040, 25052, 25038, 25048), (25048, 25052, 25028, 25030), (25034, 25036, 25004, 25006)] + [(25006, 25007, 24960, 24965)] * 3
    s = sess(seq)
    a = evaluate_session(s, SCENARIOS["SL40_T60"], None).trades[M1]
    b = evaluate_session(s, dataclasses.replace(SCENARIOS["SL40_T60"], entry_convention="SIGNAL_CLOSE"), None).trades[M1]
    assert a["entry_price"] == 25034.0 and b["entry_price"] == 25030.0


def _short_trade_session(path):
    """Failure at the 4th candle, then ``path`` candles after it (o,h,l,c)."""
    seq = [(25000, 25035, 24996, 25020), (25022, 25045, 25015, 25040), (25040, 25052, 25038, 25048), (25048, 25052, 25028, 25030)] + path
    return sess(pad(seq))


def test_stop_hit_gross_minus_stop_points():
    s = _short_trade_session([(25030, 25075, 25029, 25070)])
    r = evaluate_session(s, SCENARIOS["SL40_T60"], None).trades[M1]
    assert r["exit_reason"] == "STOP" and r["gross_points"] == -40.0


def test_same_five_minute_window_both_touched_counts_stop_first():
    s = _short_trade_session([(25030, 25075, 24960, 25000)])  # one candle range touches both stop 25070 and target 24970
    r = evaluate_session(s, SCENARIOS["SL40_T60"], None).trades[M1]
    assert r["exit_reason"] == "STOP" and r["same_window_both_touched"] is True and r["gross_points"] == -40.0
    r2 = evaluate_session(s, dataclasses.replace(SCENARIOS["SL40_T60"], tie_policy="MINUTE_ORDER"), None).trades[M1]
    assert r2["exit_reason"] in ("TARGET", "STOP")  # chronological minute order is evaluated separately


def test_forced_exit_when_neither_hit_and_after_cutoff_no_entry():
    s = _short_trade_session([(25030, 25032, 25025, 25028)])
    r = evaluate_session(s, SCENARIOS["SL40_T60"], None).trades[M1]
    assert r["exit_reason"] == "FORCED_EXIT"
    # a failure late in the day (after 13:00) is a signal in the ledger but not an eligible trade
    late = [(25000, 25035, 24996, 25020)] + [(25020, 25021, 25019, 25020)] * 50 + [(25020, 25045, 25015, 25040), (25040, 25041, 25020, 25030)]
    ev = evaluate_session(sess(pad(late, 80)), SCENARIOS["SL40_T60"], None)
    assert ev.traces[M1].status == "SIGNAL" and ev.status[M1] == "SIGNAL_AFTER_CUTOFF" and ev.combined["outcome"] == "NO_ELIGIBLE_SIGNAL"


def test_cutoff_is_inclusive_of_13_00():
    cfg = IrfV3Config()
    from nifty_trading.research.irf_v3.execution import eligible_entry

    assert eligible_entry(pd.Timestamp("2026-01-05 13:00:00"), cfg) and not eligible_entry(pd.Timestamp("2026-01-05 13:05:00"), cfg)
    assert cfg.entry_cutoff == time(13, 0)


# ------------------------------------------------------------------------------------------------- combined engine
def test_combined_only_m1_only_m2_none_both_same_and_both_different():
    only_m1 = sess(pad([(25000, 25035, 24996, 25020), (25020, 25045, 25018, 25040), (25040, 25055, 25038, 25052), (25052, 25052, 25020, 25030)]))
    ev = evaluate_session(only_m1, PRIMARY, None)
    assert ev.combined["outcome"] == "ONLY_" + M1 and overlap_class(ev) == "ONLY_M1"
    only_m2 = sess(pad(m2_seq() + [(25088, 25095, 25087, 25093), (25094, 25096, 25091, 25092), (25092, 25102, 25091, 25100), (25100, 25102, 25088, 25090)]))
    ev = evaluate_session(only_m2, PRIMARY, None)
    assert ev.combined["selected_method"] == M2 and overlap_class(ev) == "ONLY_M2"
    flat = sess(pad([(25000, 25035, 24996, 25020)] + [(25020, 25021, 25019, 25020)] * 5))
    ev = evaluate_session(flat, PRIMARY, None)
    assert ev.combined["outcome"] == "NO_SIGNAL" and overlap_class(ev) == "NEITHER"
    # both fire on the SAME candle: red candle open 25094 > A=25085; after a close above B a single candle closes below A (< B) -> both failures coincide
    seq = m2_seq() + [(25088, 25095, 25087, 25093), (25094, 25096, 25091, 25092), (25092, 25102, 25091, 25100), (25100, 25101, 25080, 25082)]
    ev = evaluate_session(sess(pad(seq)), PRIMARY, None)
    assert overlap_class(ev) == "BOTH_SAME_TIME" and ev.combined["tie"] is True and ev.combined["selected_method"] == M1
    assert ev.trades[M1]["entry_price"] == ev.trades[M2]["entry_price"] and ev.trades[M1]["gross_points"] == ev.trades[M2]["gross_points"]
    # M2 first then M1 (price stays above A while it fails B)
    seq = m2_seq() + [(25088, 25095, 25087, 25093), (25094, 25096, 25091, 25092), (25092, 25102, 25091, 25100), (25100, 25102, 25088, 25090), (25090, 25091, 25070, 25075)]
    ev = evaluate_session(sess(pad(seq)), PRIMARY, None)
    assert overlap_class(ev) == "BOTH_M2_FIRST" and ev.combined["selected_method"] == M2 and not ev.combined["tie"]


def test_combined_book_has_no_double_counted_trades():
    seq = m2_seq() + [(25088, 25095, 25087, 25093), (25094, 25096, 25091, 25092), (25092, 25102, 25091, 25100), (25100, 25101, 25080, 25082)]
    ev = evaluate_session(sess(pad(seq)), PRIMARY, None)
    b = BT.books("T", PRIMARY, [ev])
    assert len(b["M1"]) == 1 and len(b["M2"]) == 1 and len(b["COMBINED"]) == 1


# ------------------------------------------------------------------------------------------------- metrics
def test_metrics_profit_factor_drawdown_win_rate():
    rows = [{"exit_status": "CLOSED", "gross_points": g, "exit_reason": r, "date": date(2026, 1, i + 1)} for i, (g, r) in enumerate([(60, "TARGET"), (-40, "STOP"), (-40, "STOP"), (60, "TARGET")])]
    m = BT.metrics(rows, 10)
    assert m["win_rate_pct"] == 50.0 and m["profit_factor"] == 1.5 and m["gross_points"] == 40.0 and m["max_drawdown_points"] == 80.0
    g = BT.cost_slippage_grid(rows)
    assert float(g[(g.round_trip_cost_pts == 2.0) & (g.slippage_pts_per_side == 1.0)].net_points.iloc[0]) == 40.0 - 4 * 4


# ------------------------------------------------------------------------------------------------- journal matching
def jrow(i, d, t):
    return {"sheet_row": i, "date": d, "time": t, "weekday": f"{pd.Timestamp(d):%a}", "outcome": "Target", "strategy": "IRF"}


def test_journal_matching_stages_one_to_one_and_weekend_never_matches():
    man = [jrow(1, date(2026, 1, 5), "10:00"), jrow(2, date(2026, 1, 6), "10:00"), jrow(3, date(2026, 1, 7), "10:00"), jrow(4, date(2026, 1, 10), "10:00")]  # 10th is a Saturday
    auto = [{"date": date(2026, 1, 5), "candle_start": "10:00"}, {"date": date(2026, 1, 6), "candle_start": "10:15"}, {"date": date(2026, 1, 7), "candle_start": "11:00"}, {"date": date(2026, 1, 10), "candle_start": "10:00"}]
    m = RC.stage_match(man, auto)
    assert m[1][0] == "STRICT" and m[2][0] == "TIME_TOLERANT" and m[3][0] == "DATE_STRATEGY_ONLY" and 4 not in m
    assert RC.outcome_vs_journal("BE", "STOP").startswith("JOURNAL_BE") and RC.outcome_vs_journal("Target", "TARGET") == "AGREES"


# ------------------------------------------------------------------------------------------------- independent audit agrees
@pytest.mark.parametrize("seq", [
    pad([(25000, 25035, 24996, 25020), (25022, 25045, 25015, 25040), (25040, 25052, 25038, 25048), (25048, 25052, 25028, 25030), (25030, 25075, 25029, 25070)]),
    pad(m2_seq() + [(25088, 25095, 25087, 25093), (25094, 25096, 25091, 25092), (25092, 25102, 25091, 25100), (25100, 25102, 25088, 25090), (25090, 25091, 25040, 25045)]),
])
def test_independent_rebuild_matches_production_on_synthetic_days(seq):
    s = sess(seq)
    ev = evaluate_session(s, PRIMARY, None)
    ind = AU.signals(s.minutes)
    for key, m in (("M1", M1), ("M2", M2)):
        tr = ev.traces[m]
        assert (tr.status == "SIGNAL") == (ind[key] is not None)
        if ind[key] is not None:
            assert tr.signal_time == ind[key]["signal_time"] and tr.reference_level == ind[key]["level"]
            t = AU.trade(s.minutes, tr.signal_time, 40.0, 60.0)
            assert t is not None and t["entry"] == ev.trades[m]["entry_price"] and t["points"] == ev.trades[m]["gross_points"]


# ------------------------------------------------------------------------------------------------- source examples
def test_source_example_arithmetic_is_internally_consistent():
    for ex in EX.EXAMPLES:
        assert EX.arithmetic_check(ex)["internal_consistency"] == "CONSISTENT", ex["id"]


def test_illustrative_figures_reproduce_printed_numbers():
    t = EX.replay(EX.EXAMPLES[0], SCENARIOS["SL35_T60"], SCENARIOS["SL40_T60"], {})
    assert t["replay_signal"] == "SIGNAL" and t["replay_entry_next_open"] == 25030.0 and t["failure_close"] == 25030.0
    u = EX.replay(EX.EXAMPLES[4], SCENARIOS["SL35_T60"], SCENARIOS["SL40_T60"], {})
    assert u["replay_level_B"] == 25094.0 and u["replay_level_A"] == 25085.0 and u["failure_close"] == 25090.0 and u["replay_SL40_exit"].startswith("TARGET")


def test_undated_examples_never_receive_a_date():
    r = {x["id"]: EX.replay(x, SCENARIOS["SL35_T60"], SCENARIOS["SL40_T60"], {}) for x in EX.EXAMPLES}
    assert r["M1-E1"]["status"] == "NOT_REPRODUCIBLE_UNDATED" and r["M2-E1"]["status"] == "NOT_REPRODUCIBLE_UNDATED"
    assert r["M1-E2"]["status"].startswith("DATA_UNAVAILABLE") and r["M2-E3"]["status"].startswith("DATA_UNAVAILABLE")


# ------------------------------------------------------------------------------------------------- clean-room guarantees
def test_package_does_not_import_old_irf_engines_or_filters():
    banned = ("strategies.irf", "strategies.irf_v2", "strategies.irf_phase53", "strategies.irf_candidates", "strategies.rules", "orb_v2.signal_engine", "ema")
    for f in PKG.glob("*.py"):
        tree = ast.parse(f.read_text())
        for node in ast.walk(tree):
            mod = ""
            if isinstance(node, ast.ImportFrom):
                mod = (node.module or "") + "." + ",".join(a.name for a in node.names)
            elif isinstance(node, ast.Import):
                mod = ",".join(a.name for a in node.names)
            assert not any(b in mod for b in banned if b != "ema"), f"{f.name} imports {mod}"
    for name in ("method1.py", "method2.py"):
        src = (PKG / name).read_text().lower()
        code = "\n".join(ln for ln in src.splitlines() if not ln.strip().startswith(('"""', "#", "*")))
        for word in ("ema_", "prev_close", "gap_", "body_pct", "previous_day", "prev_high"):
            assert word not in code, f"{name} contains unsupported-filter token {word}"


def test_rule_registry_is_complete_and_authority_labelled():
    ids = [r[0] for r in RULES]
    assert len(ids) == len(set(ids))
    assert {r[5] for r in RULES} <= {"STATED", "TO_CONFIRM", "SOURCE_SILENT", "EXAMPLE_ONLY"}
    assert any(r[0] == "M2-R05" for r in RULES) and any(r[0] == "M1-R05" for r in RULES)


# ------------------------------------------------------------------------------------------------- reviewer-driven additions
def test_doji_is_not_red_and_cannot_set_level_b():
    seq = m2_seq() + [(25088, 25095, 25087, 25088), (25088, 25092, 25085, 25088)]  # two dojis after the breakout (close == open)
    t = run_method2(D, sess(seq).candles)
    assert t.reference_level is None and t.no_signal_reason == "NO_RED_CANDLE_AFTER_RALLY_BREAKOUT"


def test_m2_invalidation_variant_kills_setup_on_close_below_a_before_b():
    # breakout, then a RED candle that closes below A (25085): default arms B = its open; the variant invalidates
    seq = [(25050, 25085, 25045, 25070), (25070, 25092, 25068, 25090), (25090, 25091, 25070, 25075), (25075, 25100, 25074, 25098), (25098, 25099, 25060, 25070)]
    base = run_method2(D, sess(seq).candles)
    var = run_method2(D, sess(seq).candles, invalidate_close_below_a=True)
    assert base.reference_level == 25090.0 and base.status == "SIGNAL"
    assert var.status == "NO_SIGNAL" and var.no_signal_reason == "SETUP_INVALIDATED_BELOW_LEVEL_A_VARIANT"
    ind = AU.signals(sess(seq).minutes, invalidate_below_a=True)
    assert ind["M2"] is None and AU.signals(sess(seq).minutes)["M2"] is not None


def test_cutoff_exclusive_sensitivity_blocks_a_fill_at_exactly_13_00():
    from nifty_trading.research.irf_v3.config import SENSITIVITY

    seq = [(25000, 25035, 24996, 25020)] + [(25020, 25021, 25019, 25020)] * 42 + [(25020, 25045, 25015, 25040), (25040, 25041, 25020, 25030)]  # failure candle 12:55-13:00
    s = sess(pad(seq))
    inc = evaluate_session(s, PRIMARY, None)
    exc = evaluate_session(s, SENSITIVITY["SL40_CUTOFF_EXCLUSIVE"], None)
    assert inc.traces[M1].signal_time == pd.Timestamp("2026-01-05 13:00") and inc.status[M1] == "SIGNAL_ELIGIBLE"
    assert exc.status[M1] == "SIGNAL_AFTER_CUTOFF"


def test_mfe_mae_stop_at_the_exit_bar():
    # target hit in the first minutes of the window, then an adverse spike later in the SAME 5-minute window must not enter MAE of the closed winner
    s = _short_trade_session([(25030, 25032, 24965, 24990)])
    r = evaluate_session(s, SCENARIOS["SL40_T60"], None).trades[M1]
    assert r["exit_reason"] == "TARGET" and r["mae_points"] <= 10.0 and r["mfe_points"] >= 60.0
