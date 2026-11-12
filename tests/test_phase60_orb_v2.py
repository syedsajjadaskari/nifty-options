"""Phase 6.0 ORB V2 tests: candle aggregation, 09:20 availability, EMA, scenarios, levels/zones, gap, patterns, signal engine (every failed condition recorded), execution (stop/target/forced exit/
ambiguity/no late entry), look-ahead invariance, journal classification, configuration manifests, engine-vs-independent-audit parity (property test), independence from the legacy ORB engines and
preservation of the pre-existing project files."""

from __future__ import annotations

import ast
import hashlib
import json
import random
from dataclasses import fields, replace
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from nifty_trading.data.market_calendar import load_market_calendar
from nifty_trading.research.orb_v2 import audit as AU
from nifty_trading.research.orb_v2 import backtest as BT
from nifty_trading.research.orb_v2 import config as C
from nifty_trading.research.orb_v2 import execution as EX
from nifty_trading.research.orb_v2 import gap_filter as G
from nifty_trading.research.orb_v2 import journal as J
from nifty_trading.research.orb_v2 import levels as L
from nifty_trading.research.orb_v2 import opening_candle as OC
from nifty_trading.research.orb_v2 import patterns as P
from nifty_trading.research.orb_v2 import signal_engine as SE
from nifty_trading.research.orb_v2 import zones as Z
from nifty_trading.research.orb_v2.ema import ema_series
from nifty_trading.research.orb_v2.models import Level, SessionData

ROOT = Path(__file__).resolve().parents[1]
D0 = date(2025, 9, 16)
T0 = pd.Timestamp("2025-09-16 09:15")
CAL = load_market_calendar()


def minutes_frame(rows: dict[str, tuple[float, float, float, float]], day: str = "2025-09-16") -> pd.DataFrame:
    recs = [{"ts": pd.Timestamp(f"{day} {hm}"), "open": o, "high": h, "low": l, "close": c} for hm, (o, h, l, c) in rows.items()]
    df = pd.DataFrame(recs)
    df["timestamp"] = df["ts"].dt.tz_localize("Asia/Kolkata")
    return df


def flat_day(price: float = 100.0, start="09:15", end="15:29") -> dict:
    out = {}
    for t in pd.date_range(f"2025-09-16 {start}", f"2025-09-16 {end}", freq="1min"):
        out[t.strftime("%H:%M")] = (price, price, price, price)
    return out


def sd_for(opening=(25000.0, 25040.0, 24995.0, 25036.0), ema_now=24900.0, ema_prev=24899.0, prev_close=24990.0, prev_candles=None, day_rows=None, prev_last_close=24950.0, prev_ema_last=24899.0) -> SessionData:
    if prev_candles is None:
        starts = [pd.Timestamp("2025-09-15 09:15") + pd.Timedelta(minutes=5 * i) for i in range(75)]
        base = 24950 + 15 * np.sin(np.arange(75) / 6.0)
        prev_candles = pd.DataFrame({"start": starts, "end": [s + pd.Timedelta(minutes=5) for s in starts], "open": base, "high": base + 6, "low": base - 6, "close": base + 1, "ema": 24899.0})
    o, h, l, c = opening
    return SessionData(date=D0, day_minutes=day_rows if day_rows is not None else pd.DataFrame(), opening={"start": T0, "confirmed_at": T0 + pd.Timedelta(minutes=5), "open": o, "high": h, "low": l, "close": c}, open_1m=o,
                       ema_now=ema_now, ema_prev=ema_prev, prev_date=date(2025, 9, 15), prev_high=float(prev_candles["high"].max()), prev_low=float(prev_candles["low"].min()), prev_close=prev_close, prev_close_source="DAILY_VENDOR",
                       prev_last_5m_close=prev_last_close, prev_candles=prev_candles, prev_ema_last=prev_ema_last, prev_engulf_candle={k: (prev_candles[k].iloc[-1] if k in ("start", "end") else float(prev_candles[k].iloc[-1])) for k in ("start", "end", "open", "high", "low", "close")})


# ---------------------------------------------------------------------------------------------------------------- aggregation and 09:20 availability
def test_five_minute_candle_aggregates_rows_0915_to_0919_and_is_confirmed_at_0920():
    rows = {"09:15": (100, 105, 99, 103), "09:16": (103, 108, 102, 107), "09:17": (107, 107, 101, 104), "09:18": (104, 106, 100, 105), "09:19": (105, 109, 104, 108)}
    df = minutes_frame(rows)
    c = OC.opening_candle(df)
    assert (c["open"], c["high"], c["low"], c["close"]) == (100, 109, 99, 108)
    assert c["start"] == T0 and c["confirmed_at"] == T0 + pd.Timedelta(minutes=5)


def test_opening_candle_is_unavailable_if_any_of_its_five_minutes_is_missing():
    rows = {"09:15": (100, 105, 99, 103), "09:16": (103, 108, 102, 107), "09:17": (107, 107, 101, 104), "09:19": (105, 109, 104, 108)}
    assert OC.opening_candle(minutes_frame(rows)) is None


def test_candle_aggregation_drops_incomplete_candles_and_the_1530_stub():
    rows = flat_day()
    rows.pop("15:27")                       # makes the 15:25 candle incomplete
    rows["15:30"] = (100, 100, 100, 100)    # closing-print stub
    cs = OC.aggregate_5m(minutes_frame(rows))
    assert len(cs) == 74 and cs["start"].iloc[-1] == pd.Timestamp("2025-09-16 15:20")
    assert (cs["n"] == 5).all()


def test_signal_engine_never_touches_post_0920_minutes_prefix_invariance():
    sd = sd_for()
    base = SE.evaluate_session(sd, C.A)
    class Forbidden:
        def __getattr__(self, name):
            raise AssertionError(f"the signal engine touched the intraday minutes ({name})")

        def __getitem__(self, k):
            raise AssertionError("the signal engine touched the intraday minutes")

    sd2 = sd_for(day_rows=Forbidden())          # any access to post-0920 minutes would raise: the engine must not need them
    again = SE.evaluate_session(sd2, C.A)
    assert (base.signal, base.failed) == (again.signal, again.failed)


# ---------------------------------------------------------------------------------------------------------------- EMA
def test_ema_recursion_matches_pandas_and_depends_only_on_earlier_values():
    x = np.random.default_rng(1).normal(25000, 30, 600)
    e = ema_series(x, 200)
    assert e[0] == x[0]
    assert np.allclose(e, pd.Series(x).ewm(span=200, adjust=False).mean().to_numpy())
    assert np.allclose(ema_series(x[:350], 200), e[:350])            # prefix invariance: no future bars


def test_ema_scenarios_a_b_c():
    sd = sd_for(opening=(25000, 25050, 24990, 25040), ema_now=24900, ema_prev=24900, prev_last_close=24950, prev_ema_last=24900)
    assert SE.ema_scenario(sd, "BUY") == "A_ALREADY_BEYOND_EMA"
    sd = sd_for(opening=(24890, 24950, 24880, 24940), ema_now=24900, ema_prev=24900, prev_last_close=24950, prev_ema_last=24900)
    assert SE.ema_scenario(sd, "BUY") == "B_INTRABAR_CROSS_OF_EMA"
    sd = sd_for(opening=(25000, 25050, 24990, 25040), ema_now=24900, ema_prev=24900, prev_last_close=24800, prev_ema_last=24900)
    assert SE.ema_scenario(sd, "BUY") == "C_OVERNIGHT_GAP_CROSSES_EMA"


def test_close_exactly_on_ema_is_no_trade_and_both_directions_are_filtered_by_close_side():
    sd = sd_for(opening=(24990, 25012, 24988, 25000), ema_now=25000.0)
    d = SE.evaluate_session(sd, C.A)
    assert d.signal == "" and "EMA_EQUAL" in d.failed
    below = SE.evaluate_session(sd_for(opening=(25040, 25045, 24990, 24995), ema_now=25100.0), C.A)
    assert below.detail["direction_by_ema"] == "SELL"


# ---------------------------------------------------------------------------------------------------------------- levels, zones, gap
def _prev(highs, lows=None, opens=None, closes=None):
    n = len(highs)
    lows = lows or [h - 10 for h in highs]
    opens = opens or [h - 6 for h in highs]
    closes = closes or [h - 4 for h in highs]
    st = [pd.Timestamp("2025-09-15 09:15") + pd.Timedelta(minutes=5 * i) for i in range(n)]
    return pd.DataFrame({"start": st, "end": [s + pd.Timedelta(minutes=5) for s in st], "open": opens, "high": highs, "low": lows, "close": closes, "ema": 100.0})


def test_major_levels_are_the_previous_day_extremes_and_swings_exclude_the_extreme():
    p = _prev([10, 12, 15, 12, 11, 13, 20, 14, 12, 11], lows=[9, 8, 6, 7, 9, 10, 12, 4, 6, 7])
    maj = L.major_levels(p)
    assert (maj[0].ceiling, maj[1].floor) == (20, 4)
    hs, ls = L.swing_points(p, 2)
    assert 6 in hs and 7 in ls and 2 in ls
    inner = L.inner_levels(p, C.A)
    assert all(abs(x.ceiling - 20) > 1e-9 for x in inner if x.side == "RESISTANCE")   # the day high is MAJOR, never inner
    assert any(x.kind == "INNER" and x.side == "SUPPORT" and x.floor == 6 for x in inner)
    assert all(abs(x.floor - 4) > 1e-9 for x in inner if x.side == "SUPPORT")          # the day low is MAJOR, never inner


def test_zone_break_uses_ceiling_for_buy_and_floor_for_sell_and_strict_boundary():
    lv = Level("RESISTANCE", "INNER", "X", 100.0, 105.0, ("10:00",), "t")
    assert not Z.broken(lv, "BUY", 90, 105.0, C.A)            # equal to the ceiling is not a break (STRICT)
    assert Z.broken(lv, "BUY", 90, 105.05, C.A)
    assert not Z.broken(lv, "BUY", 90, 103.0, C.A)            # inside the zone is not a break (the zone is not collapsed to its floor)
    assert Z.broken(lv, "BUY", 90, 105.0, replace(C.A, boundary="INCLUSIVE"))
    sup = Level("SUPPORT", "INNER", "X", 95.0, 100.0, ("10:00",), "t")
    assert Z.broken(sup, "SELL", 110, 94.9, C.A) and not Z.broken(sup, "SELL", 110, 97.0, C.A)


def test_break_modes_gap_open_beyond_the_level():
    lv = Level("RESISTANCE", "MAJOR", "M", 100.0, 100.0, (), "t")
    assert Z.broken(lv, "BUY", 110, 120, C.A)                                    # literal reading: close beyond is enough (gap-up recognised)
    assert not Z.broken(lv, "BUY", 110, 120, C.DIAG_OLDSIDE)                    # diagnostic reading: the candle must start on the old side
    assert Z.broken(lv, "BUY", 95, 120, C.DIAG_OLDSIDE)


def test_cluster_construction_needs_repeated_rejection():
    p = _prev([10, 12, 15, 12, 11, 13, 20, 14, 12, 15.5, 12, 11, 10, 9], lows=[5, 6, 8, 7, 4, 9, 12, 8, 6, 8, 7, 5, 4, 3])
    single = [x for x in L.inner_levels(p, C.A) if x.side == "RESISTANCE"]
    cl = [x for x in L.inner_levels(p, C.C) if x.side == "RESISTANCE"]
    assert len(single) >= 2 and len(cl) == 1 and cl[0].is_zone and cl[0].floor == 15 and cl[0].ceiling == 15.5


@pytest.mark.parametrize("gap,limit,ok", [(250.0, 250.0, True), (250.01, 250.0, False), (-250.0, 250.0, True), (-250.5, 250.0, False), (280.0, 250.0, False), (280.0, 300.0, True), (-300.0, 300.0, True), (300.4, 300.0, False)])
def test_gap_limit_250_and_300_apply_in_both_directions(gap, limit, ok):
    assert G.gap_ok(gap, limit) is ok


def test_gap_uses_first_open_minus_previous_official_close():
    assert G.gap_points(25280, 25000) == 280


# ---------------------------------------------------------------------------------------------------------------- candle patterns
def test_rulebook_worked_wick_examples_buy_and_sell():
    m = P.metrics(25130, 25140, 25096, 25136)
    assert m["range"] == 44 and round(m["upper_pct"], 4) == round(4 / 44, 4) and P.wick_ok(m, "BUY", C.A)
    bad = P.metrics(25102, 25140, 25100, 25120)
    assert round(bad["upper_pct"], 2) == 0.5 and not P.wick_ok(bad, "BUY", C.A)
    sell_bad = P.metrics(25120, 25122, 25080, 25102)   # red; lower wick 22/42
    assert not P.wick_ok(sell_bad, "SELL", C.A)
    sell_ok = P.metrics(25140, 25150, 25096, 25100)    # red; lower wick 4/54, long upper wick is fine
    assert P.wick_ok(sell_ok, "SELL", C.A) and P.bad_wick_pct(sell_ok, "SELL") == sell_ok["lower_pct"]


def test_zero_range_and_doji_are_handled_without_error():
    m = P.metrics(100, 100, 100, 100)
    assert m["zero_range"] and m["upper_pct"] is None and not P.wick_ok(m, "BUY", C.A) and not P.full_body(m, "BUY", C.A)
    d = P.metrics(100, 105, 95, 100)
    assert d["colour"] == "DOJI" and not P.colour_ok(d, "BUY") and not P.colour_ok(d, "SELL")


def test_wick_limit_is_inclusive_and_configurable_not_silently_25():
    m = P.metrics(100, 110, 90, 108)         # upper wick 2/20 = 10 %
    edge = P.metrics(100, 120, 100, 116)     # upper wick 4/20 = 20 % exactly (green)
    assert P.wick_ok(edge, "BUY", C.A)
    over = P.metrics(100, 120.1, 100, 116)   # 4.1/20.1 > 20 %
    assert not P.wick_ok(over, "BUY", C.A) and P.wick_ok(over, "BUY", replace(C.A, max_bad_wick_pct=0.25))
    assert P.wick_ok(m, "BUY", C.A)


def test_full_body_hammer_shooting_star_and_engulfing_conventions():
    full = P.metrics(100, 110.5, 99.5, 110)
    assert P.full_body(full, "BUY", C.A) and not P.full_body(full, "SELL", C.A)
    ham = P.metrics(108, 110, 100, 109.5)     # long lower wick, small body near the top
    assert P.pin_bar(ham, "BUY", C.A) and not P.pin_bar(ham, "SELL", C.A)
    star = P.metrics(102, 110, 100, 100.5)    # red, long upper wick
    assert P.pin_bar(star, "SELL", C.A)
    ref = {"open": 104, "high": 106, "low": 102, "close": 105}
    big = P.metrics(103, 112, 102, 111)
    assert P.engulfing(big, ref, "BUY", C.A) is True
    assert P.engulfing(big, None, "BUY", C.A) is None                      # unevaluable without a reference candle: never silently true
    assert P.evaluate(big, ref, "BUY", C.D)["patterns"]["engulfing"] is None   # config D disables engulfing at 09:20
    flat_ref = {"open": 105, "high": 106, "low": 104, "close": 105}
    assert P.engulfing(big, flat_ref, "BUY", C.A) is False               # a doji reference body carries no information


# ---------------------------------------------------------------------------------------------------------------- signal engine
def test_a_clean_buy_is_signalled_and_a_clean_sell_mirrors_it():
    prev = _prev([24990 - i % 3 for i in range(75)])
    sd = sd_for(opening=(25000, 25040.5, 24999.5, 25040), ema_now=24900, prev_candles=prev, prev_close=24990)
    d = SE.evaluate_session(sd, C.A)
    assert d.signal == "BUY" and d.failed == [] and d.detail["signal_confirmed_at"] == T0 + pd.Timedelta(minutes=5)
    sd = sd_for(opening=(25000, 25000.5, 24959.5, 24960), ema_now=25100, prev_candles=_prev([25100 - i % 3 for i in range(75)], lows=[25080 - i % 3 for i in range(75)], opens=[25090] * 75, closes=[25090] * 75), prev_close=25010,
                prev_last_close=25090, prev_ema_last=25100)
    s = SE.evaluate_session(sd, C.A)
    assert s.signal == "SELL" and s.failed == []


def test_every_failed_condition_is_recorded_not_only_the_first():
    # red candle below... BUY direction (close above EMA) but red, big upper wick, gap too large, level not broken
    sd = sd_for(opening=(25400, 25460, 25395, 25398), ema_now=24900, prev_close=24990)
    d = SE.evaluate_session(sd, C.A)
    assert d.signal == ""
    assert {"GAP_TOO_LARGE", "COLOUR_MISMATCH"} <= set(d.failed) and len(d.failed) >= 2


def test_zero_range_candle_is_rejected_and_reported():
    sd = sd_for(opening=(25000, 25000, 25000, 25000), ema_now=24900)
    d = SE.evaluate_session(sd, C.A)
    assert "ZERO_RANGE_CANDLE" in d.failed and d.signal == ""


def test_gap_250_versus_300_changes_only_the_gap_condition():
    prev = _prev([24990 - i % 3 for i in range(75)])
    sd = sd_for(opening=(25270, 25310.5, 25269.5, 25310), ema_now=24900, prev_candles=prev, prev_close=24990)   # gap +280
    a, b = SE.evaluate_session(sd, C.A), SE.evaluate_session(sd, C.B)
    assert "GAP_TOO_LARGE" in a.failed and "GAP_TOO_LARGE" not in b.failed
    assert (set(a.failed) - {"GAP_TOO_LARGE"}) == set(b.failed)


def test_gap_up_entirely_above_the_previous_high_is_recognised_by_the_literal_break_rule():
    prev = _prev([24990 - i % 3 for i in range(75)])
    sd = sd_for(opening=(25100, 25140.5, 25099.5, 25140), ema_now=24900, prev_candles=prev, prev_close=25090, prev_last_close=24988)
    d = SE.evaluate_session(sd, C.A)
    assert d.detail["gap_beyond_prev_range"] is True and d.detail["major_broken"] is True and d.signal == "BUY"
    assert SE.evaluate_session(sd, C.DIAG_OLDSIDE).signal == ""    # the stricter diagnostic reading would reject it


# ---------------------------------------------------------------------------------------------------------------- execution
def _day(entry=(100, 101, 99.5, 100.5), after=None, forced=True):
    rows = {t: (100.0, 100.5, 99.5, 100.0) for t in pd.date_range("2025-09-16 09:15", "2025-09-16 15:29", freq="1min").strftime("%H:%M")}
    rows["09:20"] = entry
    for hm, v in (after or {}).items():
        rows[hm] = v
    if not forced:
        rows.pop("15:14")
    return minutes_frame(rows)


def _sd_exec(df, direction="BUY"):
    sd = sd_for(day_rows=df)
    return sd


def test_entry_is_the_open_of_the_0920_bar_with_30_point_stop_and_60_point_target():
    ex = EX.simulate(_sd_exec(_day(entry=(100.0, 101, 99.5, 100.5))), "BUY", C.A, CAL)
    assert ex["entry_price"] == 100.0 and ex["stop"] == 70.0 and ex["target"] == 160.0 and ex["entry_time"] == pd.Timestamp("2025-09-16 09:20")
    sx = EX.simulate(_sd_exec(_day()), "SELL", C.A, CAL)
    assert sx["stop"] == 130.0 and sx["target"] == 40.0


def test_target_stop_and_forced_exit_prices():
    tg = EX.simulate(_sd_exec(_day(after={"10:00": (120, 161, 119, 150)})), "BUY", C.A, CAL)
    assert tg["exit_reason"] == "TARGET" and tg["exit_price"] == 160.0 and tg["gross_points"] == 60.0
    st = EX.simulate(_sd_exec(_day(after={"10:00": (80, 81, 69, 70)})), "BUY", C.A, CAL)
    assert st["exit_reason"] == "STOP" and st["exit_price"] == 70.0 and st["gross_points"] == -30.0
    fe = EX.simulate(_sd_exec(_day(after={"15:14": (103.0, 104, 102, 103)})), "BUY", C.A, CAL)
    assert fe["exit_reason"] == "FORCED_EXIT" and fe["exit_price"] == 103.0 and fe["exit_time"] == pd.Timestamp("2025-09-16 15:14")


def test_forced_exit_never_fills_at_or_after_1515_and_a_missing_1514_bar_is_unresolved():
    ex = EX.simulate(_sd_exec(_day(forced=False)), "BUY", C.A, CAL)
    assert ex["exit_status"] == "UNRESOLVED_EXIT" and ex["exit_reason"] == "UNRESOLVED_EXIT"
    late = EX.simulate(_sd_exec(_day(after={"15:16": (500, 900, 400, 600)})), "BUY", C.A, CAL)   # a huge late bar must not be used
    assert late["exit_reason"] == "FORCED_EXIT" and late["exit_time"] == pd.Timestamp("2025-09-16 15:14")


def test_same_minute_stop_and_target_is_resolved_stop_first_and_flagged():
    ex = EX.simulate(_sd_exec(_day(after={"10:00": (100, 170, 60, 100)})), "BUY", C.A, CAL)
    assert ex["exit_reason"] == "STOP" and ex["ambiguous_same_bar"] is True and ex["alt_exit_reason"] == "TARGET" and ex["alt_gross_points"] == 60.0
    tf = EX.simulate(_sd_exec(_day(after={"10:00": (100, 170, 60, 100)})), "BUY", replace(C.A, same_bar_policy="TARGET_FIRST"), CAL)
    assert tf["exit_reason"] == "TARGET" and tf["alt_exit_reason"] == "STOP"


def test_a_bar_that_opens_through_the_stop_fills_at_its_open():
    ex = EX.simulate(_sd_exec(_day(after={"10:00": (60, 61, 58, 59)})), "BUY", C.A, CAL)
    assert ex["exit_reason"] == "STOP" and ex["exit_price"] == 60.0 and ex["gap_through_stop"] is True


def test_one_trade_per_day_the_simulation_ends_at_the_first_exit_and_has_no_reentry():
    df = _day(after={"10:00": (80, 81, 69, 70), "10:30": (100, 170, 99, 160)})
    ex = EX.simulate(_sd_exec(df), "BUY", C.A, CAL)
    assert ex["exit_reason"] == "STOP" and ex["exit_time"] == pd.Timestamp("2025-09-16 10:00")
    assert ex["entry_time"] == pd.Timestamp("2025-09-16 09:20")          # there is no second entry anywhere in the model


def test_no_entry_bar_or_non_executable_entry_bar_means_no_trade():
    df = _day()
    df = df[df["ts"] != pd.Timestamp("2025-09-16 09:20")]
    assert EX.simulate(_sd_exec(df), "BUY", C.A, CAL)["traded"] is False


def test_closing_auction_bars_are_never_executable_after_2026_08_03():
    day = "2026-08-04"
    rows = {t: (100.0, 100.5, 99.5, 100.0) for t in pd.date_range(f"{day} 09:15", f"{day} 15:29", freq="1min").strftime("%H:%M")}
    rows["15:14"] = (101.0, 101.5, 100.5, 101.0)
    rows["15:16"] = (500.0, 900.0, 100.0, 300.0)
    df = minutes_frame(rows, day)
    sd = sd_for(day_rows=df)
    sd.opening["confirmed_at"] = pd.Timestamp(f"{day} 09:20")
    ex = EX.simulate(sd, "BUY", C.A, CAL)
    assert ex["exit_reason"] == "FORCED_EXIT" and ex["exit_price"] == 101.0


# ---------------------------------------------------------------------------------------------------------------- metrics
def _t(date_, pts, reason="TARGET"):
    return {"date": date_, "exit_status": "CLOSED", "gross_points": pts, "direction": "BUY", "exit_reason": reason, "bars_held": 30}


def test_metrics_costs_and_slippage():
    ts = [_t(date(2025, 9, 1), 60.0), _t(date(2025, 9, 2), -30.0, "STOP"), _t(date(2025, 9, 3), -30.0, "STOP")]
    m0 = BT.metrics(ts, 75)
    assert m0["trades"] == 3 and m0["wins"] == 1 and m0["total_points"] == 0.0 and m0["longest_losing_streak"] == 2 and m0["profit_factor"] == round(4500 / 4500, 3)
    m = BT.metrics(ts, 75, 70.0, 0.5)
    assert m["total_points"] == -3.0 and m["total_rs"] == round(-3.0 * 75 - 3 * 70, 1)


# ---------------------------------------------------------------------------------------------------------------- journal
def test_journal_match_classes_never_upgrade_a_date_only_agreement():
    tr = {"signal_confirmed_at": pd.Timestamp("2025-09-16 09:20"), "exit_reason": "TARGET"}
    m = {"time": "09:15", "outcome": "Target"}
    assert J.classify(m, tr) == "STRICT_TIMING"
    assert J.classify({"time": "09:20", "outcome": "SL"}, tr) == "TIME_TOLERANT"
    assert J.classify({"time": "11:00", "outcome": "SL"}, tr) == "DATE_STRATEGY_ONLY"
    assert J.classify({"time": "", "outcome": "SL"}, tr) == "DATE_STRATEGY_ONLY"
    assert J.classify(m, None) == "MANUAL_ONLY" and J.classify(None, tr) == "AUTOMATED_ONLY"
    assert J.outcome_descriptive(m, tr) == "AGREES" and J.outcome_descriptive({"time": "09:15", "outcome": "BE"}, tr) == "NO_COUNTERPART_IN_30_60"


# ---------------------------------------------------------------------------------------------------------------- configurations
def test_configurations_differ_from_a_by_exactly_one_setting_and_carry_authority_and_hash():
    base = C.A.to_manifest()["settings"]
    expect = {"ORB-V2-B": {"max_gap_points"}, "ORB-V2-C": {"inner_method"}, "ORB-V2-D": {"engulf_reference"}}
    for cid, keys in expect.items():
        other = C.CONFIGS[cid].to_manifest()
        diff = {k for k in base if k not in ("config_id", "title") and base[k] != other["settings"][k]}
        assert diff == keys, cid
        assert len(other["config_sha256"]) == 64
    assert C.A.max_gap_points == 250 and C.B.max_gap_points == 300 and C.A.stop_points == 30 and C.A.target_points == 60 and C.A.max_bad_wick_pct == 0.20
    assert {f.name for f in fields(C.OrbV2Config)} - {"config_id", "title"} == set(C.A.to_manifest()["authority"])
    assert C.A.to_manifest()["authority"]["max_gap_points"] == C.TO_CONFIRM and C.A.to_manifest()["authority"]["stop_points"] == C.EXPLICIT
    assert len({c.to_manifest()["config_sha256"] for c in list(C.CONFIGS.values()) + [C.DIAG_OLDSIDE]}) == 5
    assert C.A.entry_convention == "OPEN_OF_0920_1M_BAR" and C.A.forced_exit_clock == "15:14"


# ---------------------------------------------------------------------------------------------------------------- engine versus independent audit implementation
def _random_session(rng: random.Random):
    n = 75
    walk = np.cumsum([rng.gauss(0, 6) for _ in range(n)]) + 25000
    o = walk + np.array([rng.uniform(-3, 3) for _ in range(n)])
    c = walk + np.array([rng.uniform(-3, 3) for _ in range(n)])
    h = np.maximum(o, c) + np.array([rng.uniform(0, 5) for _ in range(n)])
    lo = np.minimum(o, c) - np.array([rng.uniform(0, 5) for _ in range(n)])
    st = [pd.Timestamp("2025-09-15 09:15") + pd.Timedelta(minutes=5 * i) for i in range(n)]
    prev = pd.DataFrame({"start": st, "end": [s + pd.Timedelta(minutes=5) for s in st], "open": o, "high": h, "low": lo, "close": c, "ema": walk.mean()})
    base = float(c[-1]) + rng.uniform(-90, 90)
    op = base + rng.uniform(-20, 20)
    cl = op + rng.uniform(-45, 45)
    hi = max(op, cl) + rng.uniform(0, 25)
    lw = min(op, cl) - rng.uniform(0, 25)
    ema = float(prev["ema"].iloc[0]) + rng.uniform(-150, 150)
    return prev, (op, hi, lw, cl), ema


@pytest.mark.parametrize("cid", ["ORB-V2-A", "ORB-V2-B", "ORB-V2-C", "ORB-V2-D", "DIAG-A-OLDSIDE"])
def test_engine_and_independent_audit_implementation_agree_on_random_sessions(cid):
    cfg = {**C.CONFIGS, **C.DIAGNOSTICS}[cid]
    rng = random.Random(60)
    agree = n_sig = 0
    for _ in range(400):
        prev, (op, hi, lw, cl), ema = _random_session(rng)
        pc = float(prev["close"].iloc[-1]) + rng.uniform(-60, 60)
        sd = sd_for(opening=(op, hi, lw, cl), ema_now=ema, ema_prev=ema, prev_candles=prev, prev_close=pc, prev_last_close=float(prev["close"].iloc[-1]), prev_ema_last=ema)
        eng = SE.evaluate_session(sd, cfg)
        today = pd.DataFrame({"start": [T0], "open": [op], "high": [hi], "low": [lw], "close": [cl], "ema": [ema]})
        day_rows = pd.DataFrame({"open": [op]})
        from dataclasses import asdict
        aud = AU.decide(day_rows, today, prev, prev, pc, asdict(cfg))
        assert sorted(eng.failed) == sorted(aud["failed"]), (cid, eng.failed, aud["failed"])
        assert eng.signal == aud["signal"]
        agree += 1
        n_sig += bool(eng.signal)
    assert agree == 400 and n_sig > 0          # the generator produces real signals, so agreement is not vacuous


def test_audit_detects_a_deliberately_wrong_rule():
    """Mutation check: if the audit used a 25 % wick limit it would disagree with the engine somewhere (the comparison has teeth)."""
    from dataclasses import asdict
    rng = random.Random(61)
    differs = 0
    for _ in range(600):
        prev, (op, hi, lw, cl), ema = _random_session(rng)
        pc = float(prev["close"].iloc[-1])
        sd = sd_for(opening=(op, hi, lw, cl), ema_now=ema, ema_prev=ema, prev_candles=prev, prev_close=pc, prev_last_close=pc, prev_ema_last=ema)
        eng = SE.evaluate_session(sd, C.A)
        today = pd.DataFrame({"start": [T0], "open": [op], "high": [hi], "low": [lw], "close": [cl], "ema": [ema]})
        aud = AU.decide(pd.DataFrame({"open": [op]}), today, prev, prev, pc, {**asdict(C.A), "max_bad_wick_pct": 0.40})
        differs += sorted(eng.failed) != sorted(aud["failed"])
    assert differs > 0


# ---------------------------------------------------------------------------------------------------------------- independence and preservation
def test_orb_v2_does_not_import_the_legacy_orb_engines():
    banned = ("nifty_trading.strategies.orb", "nifty_trading.strategies.orb_candidates", "nifty_trading.strategies.orb_colour", "nifty_trading.research.phase54_orb", "nifty_trading.research.phase53",
              "nifty_trading.research.phase58", "nifty_trading.research.phase59", "nifty_trading.strategies.runner", "nifty_trading.strategies.trading_day")
    pkg = ROOT / "src" / "nifty_trading" / "research" / "orb_v2"
    for f in pkg.glob("*.py"):
        tree = ast.parse(f.read_text())
        for node in ast.walk(tree):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else ([node.module or ""] + [f"{node.module}.{a.name}" for a in node.names]) if isinstance(node, ast.ImportFrom) else []
            assert not any(n == b or n.startswith(b + ".") for n in names for b in banned), (f.name, names)


def test_audit_module_imports_nothing_from_the_engine():
    tree = ast.parse((ROOT / "src" / "nifty_trading" / "research" / "orb_v2" / "audit.py").read_text())
    mods = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)] + [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
    assert not [m for m in mods if m and "orb_v2" in m]


SNAP = ROOT / "reports" / "phase6" / "phase60_orb_from_scratch" / "before_snapshot.json"


@pytest.mark.skipif(not SNAP.exists(), reason="the Phase 6.0 before-snapshot has not been taken")
def test_phase_3_to_5_baselines_and_raw_data_are_byte_identical_to_the_phase60_before_snapshot():
    before = json.loads(SNAP.read_text())["files"]
    watched = [k for k in before if k.startswith(("reports/phase3/baseline/", "reports/phase3/phase32/", "reports/phase5/phase55_combined_backtest/all_executed_trades.csv", "reports/phase4/strategy_freeze.json", "data/metadata/"))]
    assert len(watched) > 100
    for k in watched:
        assert hashlib.sha256((ROOT / k).read_bytes()).hexdigest() == before[k], k


def test_the_latest_rulebook_file_is_present_and_unchanged():
    p = ROOT / "docs" / "strategy_docs" / "Nifty_920_ORB_Rulebook (2) (1).docx"
    assert hashlib.sha256(p.read_bytes()).hexdigest() == "8504fb6fca64a7e168928826970e1735b1aab14d6b2c4c6b3cf567282aac75a7"


# ---------------------------------------------------------------------------------------------------------------- data assembly causality, metrics, swings, journal reader
def _synthetic_window(scale_after_0920: dict | None = None):
    """Three consecutive synthetic sessions assembled through data_access (candles, EMA chain, previous-session selection). ``scale_after_0920`` = {date: factor} multiplies every price from 09:20 on."""
    from nifty_trading.research.orb_v2 import data_access as DA
    rng = np.random.default_rng(5)
    frames = []
    for day in ("2025-09-10", "2025-09-11", "2025-09-12"):
        idx = pd.date_range(f"{day} 09:15", f"{day} 15:29", freq="1min")
        px = 25000 + np.cumsum(rng.normal(0, 2.0, len(idx)))
        df = pd.DataFrame({"open": px, "high": px + 1.5, "low": px - 1.5, "close": px + 0.3}, index=idx)
        if scale_after_0920 and pd.Timestamp(day).date() in {pd.Timestamp(k).date() for k in scale_after_0920}:
            f = scale_after_0920[day]
            m = df.index >= pd.Timestamp(f"{day} 09:20")
            df.loc[m, ["open", "high", "low", "close"]] *= f
        df["ts"] = df.index
        df["timestamp"] = df["ts"].dt.tz_localize("Asia/Kolkata")
        df["_d"] = df["ts"].dt.date
        frames.append(df.reset_index(drop=True))
    m = pd.concat(frames, ignore_index=True)
    closes = {d: float(g["close"].iloc[-1]) for d, g in m.groupby("_d")}
    inp = DA.WindowInputs("T", "synthetic", date(2025, 9, 10), date(2025, 9, 12), m, closes, CAL)
    DA._build_chain(inp)
    DA.index_positions(inp)
    return inp


def test_data_assembly_is_causal_a_change_after_0920_never_reaches_that_days_decision_or_earlier_days():
    from nifty_trading.research.orb_v2 import data_access as DA
    base, alt = _synthetic_window(), _synthetic_window({"2025-09-12": 1.04})
    d = date(2025, 9, 12)
    sb, why = DA.session_data(base, d)
    sa, _ = DA.session_data(alt, d)
    assert sb is not None, why
    assert sb.ema_now == sa.ema_now and sb.opening == sa.opening and sb.open_1m == sa.open_1m          # the 09:15-09:20 candle and its EMA do not see 09:20+ prices
    assert (SE.evaluate_session(sb, C.A).failed, SE.evaluate_session(sb, C.A).signal) == (SE.evaluate_session(sa, C.A).failed, SE.evaluate_session(sa, C.A).signal)
    for earlier in (date(2025, 9, 10), date(2025, 9, 11)):
        assert np.array_equal(base.chain[earlier]["ema"].to_numpy(), alt.chain[earlier]["ema"].to_numpy())
    assert sb.prev_date == date(2025, 9, 11) and len(sb.prev_candles) == 75 and sb.prev_high == float(base.chain[date(2025, 9, 11)]["high"].max())
    assert sb.ema_prev == float(base.chain[date(2025, 9, 11)]["ema"].iloc[-1])                           # EMA continues across sessions (no reset)
    assert DA.session_data(base, date(2025, 9, 10))[0] is None                                           # the first session has no previous session


def test_drawdown_and_swing_edge_cases():
    assert BT.drawdown([10, -5, -5, 20, -30, 5]) == 30 and BT.drawdown([5, 5]) == 0 and BT.longest_losing_streak([1, -1, 0, -2, 3, -1]) == 3
    p = _prev([10, 12, 12, 11, 9, 8, 7], lows=[1, 2, 2, 3, 4, 5, 6])           # a tie: 12 == 12
    hs, _ = L.swing_points(p, 2)
    assert hs == []                                                          # strict on the left, non-strict on the right: the first of two equal highs fails the left test, the second is not above the first
    q = _prev([10, 11, 13, 11, 10, 9, 8])
    assert L.swing_points(q, 2)[0] == [2]
    assert L.swing_points(_prev([1, 2]), 2) == ([], [])                      # too short for any confirmed swing


def test_journal_reader_counts_match_the_verified_references():
    rows = J.read_journal()
    orb = J.orb_rows(rows)
    assert len(rows) == 190 and len(orb) == 89 and len({r["date"] for r in orb}) == 89
    assert all(r["time"] == "09:15" for r in orb)                            # every ORB label is the candle start: a 'strict' match is therefore a date + strategy match
