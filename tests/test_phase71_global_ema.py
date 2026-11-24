"""Phase 7.1 tests: shared EMA research component, IRF V3 cycle enumerators / Method 2 options, the EMA gate wrapper and the November-data quality check."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pandas as pd

from nifty_trading.research.irf_v3 import data_access as DA
from nifty_trading.research.irf_v3.method1 import run_method1
from nifty_trading.research.irf_v3.method2 import run_method2
from nifty_trading.research.phase71 import ema_rule as ER
from nifty_trading.research.phase71 import nov2026 as NV
from nifty_trading.research.phase71.irf_cycles import M2Opts, m1_cycles, m2_cycles

D = date(2026, 1, 5)


def sess(seq):
    return DA.synthetic_session(D, seq)


def cand(o, c, up=1.0, dn=1.0):
    return (o, max(o, c) + up, min(o, c) - dn, c)


# ------------------------------------------------------------------------------------------------ EMA geometry / interpretations
def g(direction="SHORT", o=100.0, h=105.0, lo=95.0, c=100.0, ema=60.0, entry=None):
    return ER.geometry(direction, o, h, lo, c, ema, entry)


def test_min_close_boundary_inclusive():
    assert ER.evaluate("MIN_CLOSE", 27, g(c=100, ema=73.0))[0] == "PASS"       # exactly 27
    assert ER.evaluate("MIN_CLOSE", 27, g(c=100, ema=73.01))[0] == "FAIL"      # 26.99
    assert ER.evaluate("MIN_CLOSE", 27, g(c=100, ema=127.0))[0] == "PASS"      # EMA above, 27


def test_max_close_is_the_complement_except_at_equality():
    assert ER.evaluate("MAX_CLOSE", 27, g(c=100, ema=73.0))[0] == "PASS"       # exactly 27 passes both min and max (inclusive)
    assert ER.evaluate("MAX_CLOSE", 27, g(c=100, ema=72.9))[0] == "FAIL"
    assert ER.evaluate("MAX_CLOSE", 27, g(c=100, ema=90.0))[0] == "PASS"


def test_range_clearance_uses_nearest_point_and_zero_inside():
    geo = g(o=100, h=105, lo=95, c=100, ema=60.0)          # EMA below the low: 95-60 = 35
    assert geo["range_clearance"] == 35.0 and geo["relation"] == "EMA_BELOW_CANDLE"
    assert ER.evaluate("MIN_RANGE", 27, geo)[0] == "PASS" and ER.evaluate("MIN_RANGE", 36, geo)[0] == "FAIL"
    inside = g(ema=100.0)
    assert inside["range_clearance"] == 0.0 and inside["candle_touches_or_crosses_ema"] and ER.evaluate("MIN_RANGE", 27, inside)[0] == "FAIL"
    above = g(ema=140.0)                                   # EMA above the high: 140-105
    assert above["range_clearance"] == 35.0 and above["relation"] == "EMA_ABOVE_CANDLE"


def test_28_vs_27_differ_for_a_clearance_between():
    geo = g(o=100, h=105, lo=95, c=100, ema=67.5)          # clearance 27.5
    assert ER.evaluate("MIN_RANGE", 27, geo)[0] == "PASS" and ER.evaluate("MIN_RANGE", 28, geo)[0] == "FAIL"


def test_target_side_is_direction_aware():
    short_blocked = g("SHORT", c=100, ema=80.0, entry=100.0)    # EMA 20 below the entry: inside the 27-point path
    assert ER.evaluate("TARGET_SIDE", 27, short_blocked)[0] == "FAIL"
    assert ER.evaluate("TARGET_SIDE", 27, g("SHORT", c=100, ema=73.0, entry=100.0))[0] == "PASS"      # exactly 27 of room
    assert ER.evaluate("TARGET_SIDE", 27, g("SHORT", c=100, ema=130.0, entry=100.0))[0] == "PASS"     # EMA above a short: not in its path
    long_blocked = g("LONG", c=100, ema=120.0, entry=100.0)
    assert ER.evaluate("TARGET_SIDE", 27, long_blocked)[0] == "FAIL"
    assert ER.evaluate("TARGET_SIDE", 27, g("LONG", c=100, ema=70.0, entry=100.0))[0] == "PASS"


def test_unavailable_ema_is_never_a_failure():
    for it in ER.INTERPS:
        assert ER.evaluate(it, 27, ER.geometry("SHORT", 1, 2, 0, 1, None))[0] == "UNAVAILABLE"
        assert ER.evaluate(it, 27, ER.geometry("SHORT", 1, 2, 0, 1, float("nan")))[0] == "UNAVAILABLE"


def test_config_table_matches_the_brief():
    assert ER.CONFIG_OF["EMA-0"] is None
    assert ER.CONFIG_OF["EMA-1"] == ("MIN_CLOSE", 27.0) and ER.CONFIG_OF["EMA-2"] == ("MIN_RANGE", 27.0)
    assert ER.CONFIG_OF["EMA-3"] == ("MAX_CLOSE", 27.0) and ER.CONFIG_OF["EMA-4"] == ("MIN_RANGE", 28.0)


class _Rec(SimpleNamespace):
    pass


class _Inner:
    STRATEGY = "XXX"

    def __init__(self, recs):
        self.recs = recs

    def evaluate_session(self, ctx):
        return self.recs


def test_gate_invalidates_only_failures_and_uses_the_confirming_candles_own_ema():
    start = pd.Timestamp("2026-01-05 09:15")
    candles = pd.DataFrame({"bar_start": [start, start + pd.Timedelta(minutes=5)], "bar_end": [start + pd.Timedelta(minutes=5), start + pd.Timedelta(minutes=10)], "open": [100.0, 100.0], "high": [105.0, 105.0],
                            "low": [95.0, 95.0], "close": [100.0, 100.0], "ema200_5m": [90.0, 60.0]})
    ctx = SimpleNamespace(candles=candles)
    mk = lambda s: _Rec(signal_status="CONFIRMED", signal_candle_start=s, direction="SHORT", signal_date=D, signal_timestamp=s + pd.Timedelta(minutes=5), strategy="XXX", method="m", invalidation_reason=None)  # noqa: E731
    r1, r2 = mk(start), mk(start + pd.Timedelta(minutes=5))
    gate = ER.EmaGateEngine(_Inner([r1, r2]), "EMA-2")
    out = gate.evaluate_session(ctx)
    assert out[0].signal_status == "INVALIDATED" and "EMA_RULE_EMA-2" in out[0].invalidation_reason      # clearance 5 < 27
    assert out[1].signal_status == "CONFIRMED"                                                         # clearance 35 >= 27
    assert gate.STRATEGY == "XXX" and len(gate.log) == 2


# ------------------------------------------------------------------------------------------------ IRF cycles
def m2_fig():
    return [(25050, 25085, 25045, 25070), (25072, 25090, 25068, 25088), (25088, 25092, 25086, 25091), (25091, 25095, 25090, 25093), (25094, 25096, 25091, 25092), (25092, 25102, 25091, 25100),
            (25100, 25104, 25098, 25102), (25102, 25104, 25088, 25090)] + [(25090, 25092, 25070, 25072)] * 3


def test_default_first_cycle_equals_phase70_modules():
    s = sess(m2_fig())
    c2, t2 = m2_cycles(s.candles), run_method2(D, s.candles)
    assert c2 and s.candles[c2[0]["fail_idx"]].end == t2.signal_time and c2[0]["level"] == t2.reference_level == 25094.0
    c1, t1 = m1_cycles(s.candles), run_method1(D, s.candles)
    assert (not c1) == (t1.status != "SIGNAL")


def test_m1_multiple_cycles_are_enumerated():
    seq = [(25000, 25035, 24996, 25020), cand(25020, 25040), cand(25040, 25030), cand(25030, 25041), cand(25041, 25029)]
    cyc = m1_cycles(sess(seq).candles)
    assert [c["cycle"] for c in cyc] == [1, 2] and cyc[0]["fail_idx"] == 2 and cyc[1]["fail_idx"] == 4


def test_invalidation_before_completion_is_permanent_and_rearm_restarts():
    # breakout, a red candle closing below A (open 25090), re-breakout and a full second sequence afterwards
    seq = [(25050, 25085, 25045, 25070), (25070, 25092, 25068, 25090), (25090, 25091, 25070, 25075),        # red, closes below A: first red candle (B = 25090)
           (25075, 25080, 25060, 25065),                                                                  # closes below A again
           (25065, 25100, 25064, 25098), (25098, 25099, 25092, 25095), (25095, 25110, 25094, 25108), (25108, 25109, 25090, 25092)]
    # persistent: B = 25090 (first red), second breakout at 25098, but the last close 25092 is still above B: no signal. Re-arm: the close below A restarts the search, a new rally breakout
    # (25098), a NEW first red candle (open 25098 = new Level B), a second breakout (25108) and a failure (25092 < 25098) -> one NEW signal.
    base = m2_cycles(sess(seq).candles)
    perm = m2_cycles(sess(seq).candles, M2Opts("BEFORE_COMPLETION"))
    rearm = m2_cycles(sess(seq).candles, M2Opts("BEFORE_COMPLETION", rearm=True))
    assert base == [] and perm == []
    assert [(c["ref_idx"], c["level"], c["fail_idx"]) for c in rearm] == [(5, 25098.0, 7)]


def test_completing_candle_below_a_is_not_an_invalidation():
    # second breakout above B, then ONE candle closes below both B and A: it completes the setup
    seq = [(25050, 25085, 25045, 25070), (25072, 25092, 25068, 25088), (25088, 25092, 25086, 25091), (25094, 25096, 25091, 25092), (25092, 25102, 25091, 25100), (25100, 25101, 25070, 25075)]
    assert len(m2_cycles(sess(seq).candles, M2Opts("BEFORE_COMPLETION"))) == 1


def test_margin_bearish_and_extra_confirmation_candidates():
    seq = m2_fig()
    s = sess(seq)
    assert m2_cycles(s.candles, M2Opts(min_margin=3.0))      # failure close 25090 is 4 below B=25094
    assert m2_cycles(s.candles, M2Opts(min_margin=5.0)) == [] or m2_cycles(s.candles, M2Opts(min_margin=5.0))[0]["fail_idx"] > m2_cycles(s.candles)[0]["fail_idx"]
    assert m2_cycles(s.candles, M2Opts(bearish_failure=True))[0]["fail_idx"] == m2_cycles(s.candles)[0]["fail_idx"]          # the failure candle is red
    ex = m2_cycles(s.candles, M2Opts(extra_confirmation=True))
    assert ex and ex[0]["fail_idx"] == m2_cycles(s.candles)[0]["fail_idx"] + 1 and ex[0]["first_break_idx"] == m2_cycles(s.candles)[0]["fail_idx"]


def test_option_tags_are_distinct():
    tags = {M2Opts().tag(), M2Opts("BEFORE_B").tag(), M2Opts("BEFORE_COMPLETION").tag(), M2Opts("BEFORE_COMPLETION", rearm=True).tag(), M2Opts(min_margin=2).tag(), M2Opts(bearish_failure=True).tag(), M2Opts(extra_confirmation=True).tag()}
    assert len(tags) == 7


# ------------------------------------------------------------------------------------------------ November data
def test_quality_flags_missing_minutes_and_outside_rows():
    ts = list(pd.date_range("2026-11-03 09:15", "2026-11-03 15:29", freq="min"))
    ts.remove(pd.Timestamp("2026-11-03 10:00"))
    ts += [pd.Timestamp("2026-11-03 15:30")]
    d = pd.DataFrame({"ts": ts, "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 0})
    d["_d"] = d["ts"].dt.date
    q = NV.quality(d).iloc[0]
    assert q.missing_minutes == 1 and q.rows_outside_session == 1 and not q.complete_session and q.ohlc_violations == 0
