"""Timing, 5-minute aggregation, warm-up and data-quality behaviour (Tasks 7, 11 #11/#13/#20)."""

import math
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import pytest
from synthetic import DAY, IST, minute_rows

from nifty_trading.data.sessions import (
    SessionStatus,
    build_session_contexts,
    causal_ema,
    causal_sma,
    classify_session,
)

pytestmark = pytest.mark.rules("DATA-TIME-001")


def _day_rows(day, n_candles=75, base=100.0, stub=True, extra_after=0):
    cands = [(base + k, base + k + 2, base + k - 1, base + k + 1) for k in range(n_candles)]
    df = minute_rows(cands, day)
    if stub:
        t = datetime(day.year, day.month, day.day, 15, 30, tzinfo=IST)
        last = df.close.iloc[-1]
        df = pd.concat([df, pd.DataFrame([{"timestamp": t, "open": last, "high": last + 0.5, "low": last,
                                           "close": last + 0.5, "volume": 0}])])
    for k in range(extra_after):
        t = datetime(day.year, day.month, day.day, 15, 31, tzinfo=IST) + timedelta(minutes=k)
        df = pd.concat([df, pd.DataFrame([{"timestamp": t, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 0}])])
    return df.reset_index(drop=True)


def test_first_candle_aggregates_rows_0915_to_0919_and_closes_at_0920():
    df = _day_rows(DAY)
    info, c = classify_session(df)
    first = c.iloc[0]
    rows = df[(df.timestamp >= first.bar_start) & (df.timestamp < first.bar_start + timedelta(minutes=5))]
    assert first.bar_start.strftime("%H:%M") == "09:15" and first.bar_end.strftime("%H:%M") == "09:20"
    assert first.open == rows.open.iloc[0] and first.close == rows.close.iloc[-1]
    assert first.high == rows.high.max() and first.low == rows.low.min() and len(rows) == 5
    assert (c.bar_end - c.bar_start == pd.Timedelta(minutes=5)).all()


def test_75_candles_and_1530_stub_is_not_part_of_any_candle():
    info, c = classify_session(_day_rows(DAY))
    assert len(c) == 75 and c.bar_start.iloc[-1].strftime("%H:%M") == "15:25"
    assert c.bar_end.iloc[-1].strftime("%H:%M") == "15:30"
    assert info.official_close is not None and info.close_source == "STUB_1530"


def test_missing_minute_drops_the_whole_candle_no_synthetic_fill():
    df = _day_rows(DAY)
    drop_ts = datetime(DAY.year, DAY.month, DAY.day, 10, 2, tzinfo=IST)  # inside the 10:00 candle
    info, c = classify_session(df[df.timestamp != drop_ts])
    assert len(c) == 74 and "10:00" not in set(c.bar_start.dt.strftime("%H:%M"))
    assert any(f.startswith("INCOMPLETE_5M_CANDLES_DROPPED") for f in info.flags)


def test_missing_opening_minute_makes_session_unusable():
    df = _day_rows(DAY)
    first = datetime(DAY.year, DAY.month, DAY.day, 9, 15, tzinfo=IST)
    info, _ = classify_session(df[df.timestamp != first])
    assert info.status is SessionStatus.EXCLUDED_NON_STANDARD_START  # first row is 09:16 -> not a standard start
    df2 = _day_rows(DAY)
    mid = datetime(DAY.year, DAY.month, DAY.day, 9, 17, tzinfo=IST)
    info2, _ = classify_session(df2[df2.timestamp != mid])
    assert info2.status is SessionStatus.EXCLUDED_NO_OPENING_CANDLE and not info2.usable


def test_special_muhurat_style_session_is_excluded():
    t0 = datetime(2025, 10, 21, 13, 45, tzinfo=IST)
    df = pd.DataFrame([{"timestamp": t0 + timedelta(minutes=k), "open": 1, "high": 1, "low": 1, "close": 1, "volume": 0} for k in range(61)])
    info, c = classify_session(df)
    assert info.status is SessionStatus.EXCLUDED_NON_STANDARD_START and c.empty


def test_records_after_1530_are_clipped_and_flagged():
    info, c = classify_session(_day_rows(DAY, extra_after=10))
    assert len(c) == 75 and c.bar_end.max().strftime("%H:%M") == "15:30"
    assert any(f.startswith("POST_CLOSE_RECORDS_CLIPPED:10") for f in info.flags)


def test_missing_close_stub_is_flagged_and_falls_back_to_last_bar():
    df = _day_rows(DAY, stub=False)
    info, _ = classify_session(df)
    assert "MISSING_1530_CLOSE_STUB" in info.flags and info.close_source == "LAST_1529"
    last = df[df.timestamp.dt.strftime("%H:%M") == "15:29"].iloc[0]
    assert last.open != last.close and info.official_close == last.close  # the fallback is the 15:29 CLOSE, not its open


def test_causal_ema_is_nan_until_200_observations_and_seeded_with_sma():
    v = np.arange(1.0, 301.0)
    e = causal_ema(v, 200)
    assert np.isnan(e[:199]).all() and not np.isnan(e[199])
    assert e[199] == pytest.approx(v[:200].mean())
    a = 2 / 201
    assert e[200] == pytest.approx(a * v[200] + (1 - a) * e[199])


def test_causal_ema_does_not_change_when_future_values_change():
    rng = np.random.default_rng(1)
    v = rng.normal(100, 1, 400)
    w = v.copy()
    w[300:] += 50
    assert np.allclose(causal_ema(v, 200)[:300], causal_ema(w, 200)[:300], equal_nan=True)
    assert np.allclose(causal_sma(v, 50)[:300], causal_sma(w, 50)[:300], equal_nan=True)


def test_warmup_first_sessions_have_no_ema_and_daily_ma_is_unavailable():
    days = [date(2026, 1, 5) + timedelta(days=k) for k in range(5)]  # Mon..Fri
    df = pd.concat([_day_rows(d, base=100 + 10 * i) for i, d in enumerate(days)])
    ctxs, _ = build_session_contexts(df, verified_holidays=set())
    assert ctxs[days[0]].candles["ema200_5m"].isna().all()  # 75 < 200
    assert ctxs[days[2]].candles["ema200_5m"].isna().sum() == 49  # global candles 150..198 precede the first valid EMA (index 199)
    assert ctxs[days[3]].candles["ema200_5m"].notna().all()  # >= 225 prior candles
    assert all(math.isnan(c.daily_sma200_prev) for c in ctxs.values())  # needs 200 daily bars, 5 exist
    assert ctxs[days[0]].data_flags == ("NO_PREVIOUS_SESSION_IN_DATASET",)


def test_unexplained_weekday_gap_between_sessions_is_flagged_not_silent():
    d1, d2 = date(2026, 1, 12), date(2026, 1, 14)  # Tue 13th has no data and is not a known holiday
    df = pd.concat([_day_rows(d1), _day_rows(d2)])
    c, _ = build_session_contexts(df, verified_holidays=set())
    assert c[d2].previous.gap_to_this_session_unverified
    assert any(f.startswith("PREV_SESSION_GAP_UNVERIFIED") for f in c[d2].data_flags)
    c2, _ = build_session_contexts(df, verified_holidays={date(2026, 1, 13)})
    assert not c2[d2].previous.gap_to_this_session_unverified


def test_context_prefix_keeps_earlier_ema_values_unchanged():
    days = [date(2026, 1, 5) + timedelta(days=k) for k in range(5)]
    df = pd.concat([_day_rows(d, base=100 + 10 * i) for i, d in enumerate(days)])
    ctxs, _ = build_session_contexts(df, verified_holidays=set())
    c = ctxs[days[4]]
    assert np.allclose(c.prefix(30).candles["ema200_5m"], c.candles["ema200_5m"].iloc[:30])


def test_weekend_sessions_must_be_known_special_sessions():
    from nifty_trading.data.market_calendar import load_market_calendar
    cal = load_market_calendar()
    info, c = classify_session(_day_rows(date(2026, 2, 1)), cal)  # Union Budget Sunday: in the calendar, normal hours
    assert info.usable and info.quality.value == "VALID_SPECIAL_SESSION" and "WEEKEND_SPECIAL_SESSION" in info.flags and len(c) == 75
    sat, c2 = classify_session(_day_rows(date(2026, 1, 10)), cal)  # an unknown Saturday session is never silently evaluated
    assert not sat.usable and sat.quality.value == "UNVERIFIED" and "WEEKEND_SESSION_NOT_IN_CALENDAR" in sat.reasons and c2.empty
    sun, _ = classify_session(_day_rows(date(2026, 2, 1)))  # no calendar supplied: same conservative answer
    assert not sun.usable
    assert "WEEKEND_SPECIAL_SESSION" not in classify_session(_day_rows(DAY))[0].flags  # DAY is a Monday


def test_quality_statuses_cover_the_defined_vocabulary():
    from nifty_trading.data.sessions import SessionQuality
    assert {q.value for q in SessionQuality} == {"VALID", "VALID_SPECIAL_SESSION", "PARTIAL", "CORRUPT", "MISSING", "UNVERIFIED"}
    info, _ = classify_session(_day_rows(DAY))
    assert info.quality is SessionQuality.VALID and info.reasons == ()
    partial, _ = classify_session(_day_rows(DAY)[lambda x: x.timestamp.dt.strftime("%H:%M") != "10:02"])
    assert partial.quality is SessionQuality.PARTIAL and partial.usable  # one candle dropped, the rest evaluable and flagged
    bad = _day_rows(DAY)
    bad.loc[10, "high"] = bad.loc[10, "low"] - 1  # high below low
    corrupt, _ = classify_session(bad)
    assert corrupt.quality is SessionQuality.CORRUPT and not corrupt.usable and corrupt.reasons[0].startswith("OHLC_INCONSISTENT")
    dup = pd.concat([_day_rows(DAY), _day_rows(DAY).iloc[[5]]], ignore_index=True)
    assert classify_session(dup)[0].reasons == ("DUPLICATE_TIMESTAMPS",)
