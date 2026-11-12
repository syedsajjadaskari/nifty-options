"""Source-anchored diagnostic checks; active strategy behaviour is untouched."""

from dataclasses import replace

import numpy as np
import pandas as pd
import pytest
from synthetic import ctx, minute_rows

from nifty_trading.data.sessions import _day_5m, causal_ema
from nifty_trading.research.phase58 import geometry, pivots, reconstruct
from nifty_trading.strategies.orb import ORBStrategy
from nifty_trading.strategies.orb_candidates import ORBCandidateStrategy
from nifty_trading.strategies.orb_colour import ORBColourStrategy
from nifty_trading.strategies.params import DEFAULT_PROPOSALS

P = replace(DEFAULT_PROPOSALS, trend_mode="EMA_PREV_SESSION_CLOSE")


def confirmed(engine, context, method=None):
    return [r for r in engine.evaluate_session(context) if r.signal_status == "CONFIRMED"
            and (method is None or r.method == method)]


@pytest.mark.parametrize("long", [True, False])
def test_pdf_pages_8_9_body_crosses_average_while_open_stays_on_old_side(long):
    # Geometry copied semantically from the diagrams, not measured chart pixels.
    # Prior close 100, MA 110: gap-up open 105 still below MA, green close 125.
    c0 = (105, 126, 104, 125) if long else (115, 116, 94, 95)
    prior = 100 if long else 120
    context = ctx([c0], prev={"cands": [(prior, prior+1, prior-1, prior)] * 5,
                                "close": prior, "ema_last": 110}, ema=110)
    baseline = ORBStrategy(proposals=P)
    candidate = ORBCandidateStrategy(proposals=P, gap_crossing_def="CANDLE_CROSSES_AVERAGE")
    assert not confirmed(baseline, context, "Gap/200DMA")
    events = confirmed(candidate, context, "Gap/200DMA")
    assert len(events) == 1
    assert events[0].signal_timestamp.strftime("%H:%M") == "09:20"
    assert events[0].direction == ("LONG" if long else "SHORT")
    # Independent diagnostics agree and retain the exact narrow gate that differs.
    old = next(r for r in reconstruct(context, P) if r["method"] == "Gap/200DMA" and r["direction"] == events[0].direction)
    new = next(r for r in reconstruct(context, P, "gap_candle") if r["method"] == old["method"] and r["direction"] == old["direction"])
    assert old["failed"] == ["gap_crossing"] and new["eligible"]


def colour_context():
    # Red first candle with lower rejection wick: frozen pin rule admits a long.
    return ctx([(122, 123, 110, 120)], prev={"cands": [(100, 115, 90, 110)] * 5,
                                            "close": 110, "ema_last": 100}, ema=100)


def test_handwritten_page_5_long_colour_clarification_is_absent_from_frozen():
    context = colour_context()
    assert any(r.direction == "LONG" for r in confirmed(ORBStrategy(proposals=P), context))
    assert not confirmed(ORBColourStrategy(proposals=P), context)


@pytest.mark.xfail(strict=True, reason="Confirmed metadata defect in existing opt-in colour wrapper; audit must not modify strategy files")
def test_invalidated_colour_record_must_not_retain_confirmed_execution_metadata():
    records = ORBColourStrategy(proposals=P).evaluate_session(colour_context())
    invalid = [r for r in records if r.invalidation_reason == "FIRST_CANDLE_COLOUR_AGAINST_DIRECTION"]
    assert invalid
    assert all(r.execution_config["entry_rule_status"] == "NOT_A_CONFIRMED_SIGNAL" for r in invalid)


def test_source_page_2_first_five_minutes_exclude_0920_and_incomplete_bucket():
    raw = minute_rows([(100, 110, 90, 108), (108, 999, 107, 998)])
    frame, _ = _day_5m(raw)
    assert tuple(frame.iloc[0][["open", "high", "low", "close"]]) == (100, 110, 90, 108)
    assert frame.bar_end.iloc[0] == raw.timestamp.iloc[5]
    partial, _ = _day_5m(raw.drop(index=1))
    assert not any(partial.bar_start.dt.strftime("%H:%M") == "09:15")


def test_ema_200_seed_and_future_changes_do_not_change_completed_values():
    prices = np.linspace(100, 300, 250)
    result = causal_ema(prices, 200)
    assert np.isnan(result[:199]).all()
    assert result[199] == pytest.approx(sum(prices[:200]) / 200)
    prices[220:] = -100000
    assert np.array_equal(result[:220], causal_ema(prices, 200)[:220], equal_nan=True)


def test_report_preserves_both_directions_and_geometry_without_inventing_a_trade():
    context = colour_context()
    paths = reconstruct(context, P)
    assert len(paths) == 6 and {r["direction"] for r in paths} == {"LONG", "SHORT"}
    g = geometry(context.candles.iloc[0])
    assert g["body_points"] + g["upper_wick"] + g["lower_wick"] == g["range_points"]
    assert not any("entry_price" in r for r in paths)


def test_pivots_need_two_later_candles_before_session_open():
    f = pd.DataFrame({"high": [1, 2, 8, 3, 4], "low": [0, 1, 2, 1, 0]})
    assert pivots(f.iloc[:4], True) == []
    assert pivots(f, True) == [2]


def test_orb_opening_evaluation_is_identical_after_future_intraday_rows_change():
    context = ctx([(116, 128, 115, 127), (127, 129, 120, 125)],
                  prev={"cands": [(100, 115, 90, 110)] * 5, "close": 110, "ema_last": 100}, ema=100)
    before = ORBStrategy(proposals=P).evaluate_session(context)
    assert confirmed(ORBStrategy(proposals=P), context)
    context.candles.loc[1, ["open", "high", "low", "close", "ema200_5m"]] = [1000, 2000, 1, 2, -1000]
    assert ORBStrategy(proposals=P).evaluate_session(context) == before
