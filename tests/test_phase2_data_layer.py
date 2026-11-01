"""Value-level tests of build_session_contexts, frozen-feed handling and previous-session reliability."""

import math
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import pytest
from synthetic import IST, minute_rows

from nifty_trading.data.sessions import build_session_contexts, stale_row_mask
from nifty_trading.strategies import IRFStrategy, PDRStrategy


def _stub(day, close):
    t = datetime(day.year, day.month, day.day, 15, 30, tzinfo=IST)
    return pd.DataFrame([{"timestamp": t, "open": close, "high": close, "low": close, "close": close, "volume": 0}])


def session(day, cands, stub_close):
    return pd.concat([minute_rows(cands, day), _stub(day, stub_close)], ignore_index=True)


# ------------------------------------------------------------------ previous-session wiring
@pytest.mark.rules("DATA-TIME-001", "PDR-004", "PDS-003")
def test_previous_session_values_are_the_immediately_preceding_session_and_exact():
    d1, d2, d3 = date(2026, 1, 5), date(2026, 1, 6), date(2026, 1, 7)
    s1 = session(d1, [(100, 110, 95, 105), (105, 120, 104, 118)], 777.0)
    s2 = session(d2, [(200, 230, 190, 210), (210, 215, 180, 185)], 888.0)  # high 230, low 180, last close 185, official 888
    s3 = session(d3, [(300, 301, 299, 300)], 999.0)
    ctxs, _ = build_session_contexts(pd.concat([s1, s2, s3]), verified_holidays=set())
    p = ctxs[d3].previous
    assert p.date == d2 and (p.high, p.low) == (230.0, 180.0)  # not two sessions back; high/low not swapped
    assert p.last_5m_close == 185.0 and p.close_official == 888.0 and p.open == 200.0
    assert ctxs[d3].open_price == 300.0 and ctxs[d2].open_price == 200.0  # the first OPEN, not a close
    assert ctxs[d2].previous.date == d1 and ctxs[d2].previous.close_official == 777.0
    assert ctxs[d1].previous is None


@pytest.mark.rules("RF-001", "RF-008")
def test_prior_session_ema_flags_are_newest_first_and_use_each_sessions_last_candle():
    days = list(pd.bdate_range("2026-01-05", periods=6).date)
    frames = []
    for i, d in enumerate(days):
        last = {3: (100, 101, 49, 50), 4: (100, 151, 99, 150)}.get(i, (100, 101, 99, 100.5))  # session 3 ends far below, 4 far above
        frames.append(session(d, [(100, 101, 99, 100)] * 74 + [last], 100.0))
    ctxs, _ = build_session_contexts(pd.concat(frames), verified_holidays=set())
    c = ctxs[days[5]]
    assert c.prior_session_ema_above[0] is True and c.prior_session_ema_above[1] is False  # newest first: s4 above, s3 below
    assert days[4].weekday() == 4 and days[5].weekday() == 0
    assert not c.previous.gap_to_this_session_unverified  # an ordinary Friday -> Monday weekend is never an unexplained gap
    assert c.previous.ema_at_last_candle == pytest.approx(float(ctxs[days[4]].candles["ema200_5m"].iloc[-1]))


@pytest.mark.rules("DATA-WARM-001", "ORB-MA-001")
def test_daily_sma_uses_only_closes_strictly_before_the_session_and_the_right_divisor():
    days = list(pd.bdate_range("2025-01-01", periods=206).date)
    hol = set(pd.bdate_range("2025-01-01", periods=300).date)
    frames = [session(d, [(1000.0 + i, 1001.0 + i, 999.0 + i, 1000.0 + i)] * 2, 5000.0 + i) for i, d in enumerate(days)]
    ctxs, _ = build_session_contexts(pd.concat(frames), verified_holidays=hol)
    official = np.array([5000.0 + i for i in range(206)])
    assert math.isnan(ctxs[days[199]].daily_sma200_prev) and ctxs[days[199]].daily_history_count == 199
    for k in (200, 205):
        c = ctxs[days[k]]
        assert c.daily_history_count == k
        assert c.daily_sma200_prev == pytest.approx(official[k - 200:k].mean())  # excludes session k's own close
        assert not math.isnan(c.daily_ema200_prev)
    frames2 = list(frames)
    frames2[205] = session(days[205], [(1000.0, 1001.0, 999.0, 1000.0)] * 2, 1.0)  # change ONLY today's close
    c2, _ = build_session_contexts(pd.concat(frames2), verified_holidays=hol)
    assert c2[days[205]].daily_sma200_prev == ctxs[days[205]].daily_sma200_prev  # no look-ahead


# ------------------------------------------------------------------ frozen feed
def _frozen_day(day, base=24500.0, run=14):
    """A normal session whose 15:15.. rows are frozen at one price, then a 201-point catch-up bar at 15:29."""
    cands = [(base + k % 3, base + 6 + k % 3, base - 4 + k % 3, base + 1 + k % 3) for k in range(75)]
    df = minute_rows(cands, day)
    t0 = datetime(day.year, day.month, day.day, 15, 15, tzinfo=IST)
    frozen = base + 73.35
    idx = df.index[(df.timestamp >= t0) & (df.timestamp <= t0 + timedelta(minutes=run - 1))]
    df.loc[idx, ["open", "high", "low", "close"]] = frozen
    last = df.index[df.timestamp == datetime(day.year, day.month, day.day, 15, 29, tzinfo=IST)][0]
    df.loc[last, ["open", "high", "low", "close"]] = [frozen, frozen + 201, frozen, frozen + 201]
    return pd.concat([df, _stub(day, frozen + 201)], ignore_index=True)


@pytest.mark.rules("DATA-QUAL-001")
def test_frozen_feed_rows_are_excluded_and_their_candles_dropped_not_repaired():
    d = date(2026, 8, 3)
    ctxs, infos = build_session_contexts(_frozen_day(d), verified_holidays=set())
    c = ctxs[d].candles
    starts = set(c.bar_start.dt.strftime("%H:%M"))
    assert len(c) == 72 and {"15:15", "15:20", "15:25"}.isdisjoint(starts)
    assert c.bar_start.iloc[-1].strftime("%H:%M") == "15:10"
    assert c.high.max() < 24500 + 100  # the 201-point catch-up bar is in none of the candles
    assert any(f.startswith("STALE_FEED_ROWS_EXCLUDED:14") for f in infos[d].flags)


@pytest.mark.rules("DATA-QUAL-001")
def test_stale_mask_needs_a_run_of_identical_consecutive_flat_rows():
    t0 = datetime(2026, 1, 5, 10, 0, tzinfo=IST)

    def rows(prices, step=1):
        return pd.DataFrame([{"timestamp": t0 + timedelta(minutes=step * i), "open": p, "high": p, "low": p, "close": p}
                             for i, p in enumerate(prices)])

    assert stale_row_mask(rows([5] * 5)).all()
    assert not stale_row_mask(rows([5] * 4)).any()  # four flat rows can be a quiet market
    assert not stale_row_mask(rows([5, 5, 6, 6, 5])).any()  # flat, but not one frozen price
    assert not stale_row_mask(rows([5] * 6, step=2)).any()  # not consecutive minutes


@pytest.mark.rules("DATA-QUAL-001", "PDR-002")
def test_session_after_a_frozen_tail_is_not_evaluated_for_previous_day_strategies():
    d1, d2 = date(2026, 8, 3), date(2026, 8, 4)
    nxt = session(d2, [(24800, 24810, 24790, 24805), (24805, 24830, 24800, 24825)], 24825.0)
    ctxs, _ = build_session_contexts(pd.concat([_frozen_day(d1), nxt]), verified_holidays=set())
    c = ctxs[d2]
    assert c.previous.gap_to_this_session_unverified and any(f.startswith("PREV_CLOSE_UNRELIABLE") for f in c.data_flags)
    [r] = PDRStrategy().evaluate_session(c)
    assert r.signal_status == "NOT_EVALUATED" and "PREV_SESSION_UNVERIFIED" in r.invalidation_reason
    assert IRFStrategy().evaluate_session(c) is not None  # IRF needs no previous day and still runs on the real candles


@pytest.mark.rules("DATA-QUAL-001")
def test_special_session_between_and_post_close_prints_make_the_previous_close_unverified():
    d1, d2 = date(2025, 10, 20), date(2025, 10, 23)
    t0 = datetime(2025, 10, 21, 13, 45, tzinfo=IST)
    muhurat = pd.DataFrame([{"timestamp": t0 + timedelta(minutes=k), "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 0}
                            for k in range(61)])
    a = session(d1, [(100, 101, 99, 100)] * 3, 100.0)
    b = session(d2, [(100, 101, 99, 100)] * 3, 100.0)
    ctxs, _ = build_session_contexts(pd.concat([a, muhurat, b]), verified_holidays={date(2025, 10, 22)})
    assert date(2025, 10, 21) not in ctxs
    assert any(f.startswith("PREV_SESSION_SKIPS_EXCLUDED_SESSION") for f in ctxs[d2].data_flags)
    assert ctxs[d2].previous.gap_to_this_session_unverified
    e1, e2 = date(2026, 3, 10), date(2026, 3, 11)  # a previous session with records after 15:30 has an ambiguous close
    late = pd.DataFrame([{"timestamp": datetime(2026, 3, 10, 15, 31 + k, tzinfo=IST), "open": 90.0, "high": 90.0, "low": 90.0,
                          "close": 90.0, "volume": 0} for k in range(3)])
    c2, _ = build_session_contexts(pd.concat([session(e1, [(100, 101, 99, 100)] * 3, 100.0), late,
                                              session(e2, [(95, 96, 94, 95)] * 3, 95.0)]), verified_holidays=set())
    assert c2[e2].previous.gap_to_this_session_unverified and any("EXTENDED_RECORDS" in f for f in c2[e2].data_flags)


@pytest.mark.rules("DATA-TIME-001")
def test_official_close_is_the_close_of_the_1530_print_not_its_open():
    day = date(2026, 1, 5)
    stub = pd.DataFrame([{"timestamp": datetime(2026, 1, 5, 15, 30, tzinfo=IST), "open": 100.0, "high": 103.0, "low": 99.0, "close": 101.5, "volume": 0}])
    _, infos = build_session_contexts(pd.concat([minute_rows([(100, 101, 99, 100)] * 3, day), stub], ignore_index=True), verified_holidays=set())
    assert infos[day].official_close == 101.5 and infos[day].close_source == "STUB_1530"
