"""Value-level tests of build_session_contexts, frozen-feed handling and previous-session reliability."""

import math
from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd
import pytest
from synthetic import IST, minute_rows

from nifty_trading.data.market_calendar import ClosingAuction, MarketCalendar
from nifty_trading.data.sessions import build_session_contexts, stale_row_mask
from nifty_trading.strategies import PDRStrategy


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


CAS = MarketCalendar(closing_auction=ClosingAuction(date(2026, 8, 3), time(15, 15), time(15, 29)))


@pytest.mark.rules("DATA-QUAL-001", "DATA-CAS-001")
def test_frozen_tail_inside_the_closing_auction_window_is_real_market_structure_and_is_kept():
    d = date(2026, 8, 3)
    ctxs, infos = build_session_contexts(_frozen_day(d), verified_holidays=set(), calendar=CAS)
    c = ctxs[d].candles
    assert len(c) == 75 and {"15:15", "15:20", "15:25"} <= set(c.bar_start.dt.strftime("%H:%M"))  # nothing dropped
    assert infos[d].quality.value == "VALID" and infos[d].cas_regime and infos[d].usable
    assert any(f.startswith("CAS_FROZEN_WINDOW_KEPT:14") for f in infos[d].flags)
    assert c.high.max() == 24500 + 73.35 + 201  # the step to the official close is a real (auction) print, kept as in a chart


@pytest.mark.rules("DATA-QUAL-001", "DATA-CAS-001")
def test_the_same_frozen_pattern_is_still_an_anomaly_before_the_regime_date_or_outside_the_window():
    before = date(2026, 7, 31)  # one trading day before the auction regime
    _, infos = build_session_contexts(_frozen_day(before), verified_holidays=set(), calendar=CAS)
    assert infos[before].quality.value == "CORRUPT" and not infos[before].usable
    assert infos[before].reasons[0].startswith("FROZEN_FEED_OUTSIDE_AUCTION_WINDOW")
    d = date(2026, 8, 5)  # on a regime date, a frozen run at 11:00-11:10 is NOT the auction
    df = minute_rows([(24500 + k % 3, 24506 + k % 3, 24496 + k % 3, 24501 + k % 3) for k in range(75)], d)
    idx = df.index[(df.timestamp >= datetime(2026, 8, 5, 11, 0, tzinfo=IST)) & (df.timestamp <= datetime(2026, 8, 5, 11, 9, tzinfo=IST))]
    df.loc[idx, ["open", "high", "low", "close"]] = 24500.0
    _, infos2 = build_session_contexts(pd.concat([df, _stub(d, 24501.0)], ignore_index=True), verified_holidays=set(), calendar=CAS)
    assert infos2[d].quality.value == "CORRUPT" and not infos2[d].usable


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


@pytest.mark.rules("DATA-QUAL-001", "PDR-002", "DATA-OFFICIAL-CLOSE-001", "DATA-CAS-001")
def test_session_after_an_auction_day_is_evaluable_and_uses_the_official_daily_close():
    d1, d2 = date(2026, 8, 3), date(2026, 8, 4)
    nxt = session(d2, [(24800, 24810, 24790, 24805), (24805, 24830, 24800, 24825)], 24825.0)
    daily = pd.DataFrame({"date": [d1, d2], "open": [1.0, 1.0], "high": [1.0, 1.0], "low": [1.0, 1.0], "close": [24774.30, 24825.0]})
    ctxs, _ = build_session_contexts(pd.concat([_frozen_day(d1), nxt]), verified_holidays=set(), calendar=CAS, daily_df=daily)
    c = ctxs[d2]
    assert not c.previous.gap_to_this_session_unverified and c.previous.close_official == 24774.30
    assert c.previous.close_source == "DAILY_VENDOR" and not any(f.startswith("PREV_") for f in c.data_flags)
    # the previous-day candles include the auction step by default; the proposal 'CONTINUOUS_ONLY' excludes the 15:15+ candles
    assert c.previous.candles.bar_start.iloc[-1].strftime("%H:%M") == "15:25"
    assert c.previous.continuous_candles.bar_start.iloc[-1].strftime("%H:%M") == "15:10"
    assert c.previous.high == 24500 + 73.35 + 201 and c.previous.high_continuous < 24600
    recs = PDRStrategy().evaluate_session(c)
    assert all(r.signal_status != "NOT_EVALUATED" for r in recs)  # no longer blocked


@pytest.mark.rules("PDR-002", "ORB-M1-LONG-001", "DATA-CAS-001")
def test_prev_day_level_window_proposal_changes_only_the_levels_it_names():
    from nifty_trading.strategies import ORBStrategy, ProposalConfig
    from nifty_trading.strategies.definitions import prev_high_low
    d1, d2 = date(2026, 8, 3), date(2026, 8, 4)
    daily = pd.DataFrame({"date": [d1, d2], "open": [1.0, 1.0], "high": [1.0, 1.0], "low": [1.0, 1.0], "close": [24774.30, 24825.0]})
    ctxs, _ = build_session_contexts(pd.concat([_frozen_day(d1), session(d2, [(24800, 24810, 24790, 24805)] * 2, 24825.0)]),
                                     verified_holidays=set(), calendar=CAS, daily_df=daily)
    prev = ctxs[d2].previous
    assert prev_high_low(prev, ProposalConfig())[0] == prev.high
    assert prev_high_low(prev, ProposalConfig(prev_day_level_window="CONTINUOUS_ONLY"))[0] == prev.high_continuous < prev.high
    levels = ORBStrategy(proposals=ProposalConfig(prev_day_level_window="CONTINUOUS_ONLY"))
    assert levels.p.prev_day_level_window == "CONTINUOUS_ONLY"


@pytest.mark.rules("DATA-QUAL-001")
def test_special_session_between_makes_the_previous_close_day_unverified_and_post_close_prints_matter_only_without_a_daily_close():
    d1, d2 = date(2025, 10, 20), date(2025, 10, 23)
    t0 = datetime(2025, 10, 21, 13, 45, tzinfo=IST)
    muhurat = pd.DataFrame([{"timestamp": t0 + timedelta(minutes=k), "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 0}
                            for k in range(61)])
    a = session(d1, [(100, 101, 99, 100)] * 3, 100.0)
    b = session(d2, [(100, 101, 99, 100)] * 3, 100.0)
    ctxs, _ = build_session_contexts(pd.concat([a, muhurat, b]), verified_holidays={date(2025, 10, 22)}, calendar=MarketCalendar())
    assert date(2025, 10, 21) not in ctxs
    assert any(f.startswith("PREV_SESSION_SKIPS_EXCLUDED_SESSION") for f in ctxs[d2].data_flags)
    assert ctxs[d2].previous.gap_to_this_session_unverified
    # with the official daily series the previous CLOSE day (the Muhurat date) differs from the previous full session: still unverified
    daily = pd.DataFrame({"date": [d1, date(2025, 10, 21), d2], "open": 1.0, "high": 1.0, "low": 1.0, "close": [100.0, 101.0, 100.0]})
    c3, _ = build_session_contexts(pd.concat([a, muhurat, b]), verified_holidays={date(2025, 10, 22)}, calendar=MarketCalendar(), daily_df=daily)
    assert any(f.startswith("PREV_CLOSE_DAY_DIFFERS_FROM_PREV_SESSION") for f in c3[d2].data_flags)
    # post-close prints: ambiguous only when no official daily close exists
    e1, e2 = date(2026, 3, 10), date(2026, 3, 11)
    late = pd.DataFrame([{"timestamp": datetime(2026, 3, 10, 15, 31 + k, tzinfo=IST), "open": 90.0, "high": 90.0, "low": 90.0,
                          "close": 90.0, "volume": 0} for k in range(3)])
    frames = pd.concat([session(e1, [(100, 101, 99, 100)] * 3, 100.0), late, session(e2, [(95, 96, 94, 95)] * 3, 95.0)])
    c4, _ = build_session_contexts(frames, verified_holidays=set(), calendar=MarketCalendar())
    assert c4[e2].previous.gap_to_this_session_unverified and any("POST_CLOSE_RECORDS" in f for f in c4[e2].data_flags)
    daily2 = pd.DataFrame({"date": [e1, e2], "open": 1.0, "high": 1.0, "low": 1.0, "close": [90.0, 95.0]})
    c5, _ = build_session_contexts(frames, verified_holidays=set(), calendar=MarketCalendar(), daily_df=daily2)
    assert not c5[e2].previous.gap_to_this_session_unverified and c5[e2].previous.close_official == 90.0  # the official close settles it


@pytest.mark.rules("DATA-WARM-001")
def test_warmup_data_seeds_the_ema_and_the_previous_session_but_is_never_evaluated():
    warm_days = list(pd.bdate_range("2026-01-01", periods=4).date)
    main_day = date(2026, 1, 7)
    warm = pd.concat([session(d, [(100 + i, 101 + i, 99 + i, 100 + i)] * 75, 100.0 + i) for i, d in enumerate(warm_days)], ignore_index=True)
    main = session(main_day, [(110, 111, 109, 110)] * 75, 110.0)
    without, _ = build_session_contexts(main, verified_holidays={date(2026, 1, 1)}, calendar=MarketCalendar())
    with_w, infos = build_session_contexts(main, verified_holidays={date(2026, 1, 1)}, calendar=MarketCalendar(), warmup_1m=warm)
    assert without[main_day].candles["ema200_5m"].isna().all() and with_w[main_day].candles["ema200_5m"].notna().all()
    assert set(with_w) == {main_day} and set(infos) == {main_day}  # no context and no info for warm-up sessions
    assert with_w[main_day].previous.date == warm_days[-1]  # the first evaluated session now has a previous session


@pytest.mark.rules("DATA-CAS-001", "DATA-QUAL-001")
def test_a_frozen_run_that_ends_exactly_at_1529_is_still_inside_the_auction_window():
    d = date(2026, 8, 3)
    df = _frozen_day(d)
    row = df.index[df.timestamp == datetime(2026, 8, 3, 15, 29, tzinfo=IST)][0]
    df.loc[row, ["open", "high", "low", "close"]] = 24573.35  # freeze the 15:29 minute too: the run is 15:15..15:29 inclusive
    ctxs, infos = build_session_contexts(df, verified_holidays=set(), calendar=CAS)
    assert infos[d].quality.value == "VALID" and any(f.startswith("CAS_FROZEN_WINDOW_KEPT:15") for f in infos[d].flags)
    assert ctxs[d].info.usable


@pytest.mark.rules("DATA-WARM-001", "ORB-MA-001")
def test_daily_ma_with_a_supplied_daily_series_never_includes_the_sessions_own_close():
    days = list(pd.bdate_range("2025-01-01", periods=206).date)
    hol = set(pd.bdate_range("2025-01-01", periods=300).date)
    frames = [session(d, [(1000.0 + i, 1001.0 + i, 999.0 + i, 1000.0 + i)] * 2, 5000.0 + i) for i, d in enumerate(days)]
    official = np.array([5000.0 + i for i in range(206)])
    daily = pd.DataFrame({"date": days, "open": official, "high": official, "low": official, "close": official})
    ctxs, _ = build_session_contexts(pd.concat(frames), verified_holidays=hol, calendar=MarketCalendar(), daily_df=daily)
    for k in (200, 205):
        assert ctxs[days[k]].daily_history_count == k
        assert ctxs[days[k]].daily_sma200_prev == pytest.approx(official[k - 200:k].mean())  # not official[k-199:k+1]
    assert math.isnan(ctxs[days[199]].daily_sma200_prev)


@pytest.mark.rules("DATA-OFFICIAL-CLOSE-001")
def test_official_close_difference_from_the_1530_print_is_flagged_with_a_tolerance_and_the_print_is_wired_into_the_previous_session():
    day, nxt = date(2026, 1, 5), date(2026, 1, 6)
    s1 = session(day, [(100, 101, 99, 100)] * 3, 100.0)  # 15:30 print 100.0
    s2 = session(nxt, [(100, 101, 99, 100)] * 3, 100.0)
    near = pd.DataFrame({"date": [day, nxt], "open": 1.0, "high": 1.0, "low": 1.0, "close": [100.04, 100.0]})  # within the 0.05 tolerance
    far = pd.DataFrame({"date": [day, nxt], "open": 1.0, "high": 1.0, "low": 1.0, "close": [95.0, 100.0]})
    _, i_near = build_session_contexts(pd.concat([s1, s2]), verified_holidays=set(), calendar=MarketCalendar(), daily_df=near)
    c_far, i_far = build_session_contexts(pd.concat([s1, s2]), verified_holidays=set(), calendar=MarketCalendar(), daily_df=far)
    assert not any(f.startswith("OFFICIAL_CLOSE_DIFFERS") for f in i_near[day].flags)
    assert any(f == "OFFICIAL_CLOSE_DIFFERS_FROM_1530_PRINT:-5.00" for f in i_far[day].flags)
    prev = c_far[nxt].previous
    assert prev.close_official == 95.0 and prev.close_1530_print == 100.0  # the print is the 15:30 row, not the official close


@pytest.mark.rules("DATA-QUAL-001", "DATA-OFFICIAL-CLOSE-001")
def test_a_missing_daily_row_makes_the_next_sessions_previous_close_unverified_instead_of_silently_using_the_print():
    day, nxt = date(2026, 1, 5), date(2026, 1, 6)
    s1, s2 = session(day, [(100, 101, 99, 100)] * 3, 100.0), session(nxt, [(100, 101, 99, 100)] * 3, 100.0)
    daily = pd.DataFrame({"date": [nxt], "open": 1.0, "high": 1.0, "low": 1.0, "close": [100.0]})  # no row for `day`
    ctxs, _ = build_session_contexts(pd.concat([s1, s2]), verified_holidays=set(), calendar=MarketCalendar(), daily_df=daily)
    assert ctxs[nxt].previous.gap_to_this_session_unverified
    assert any(f.startswith("PREV_CLOSE_FALLBACK_TO_1530_PRINT") for f in ctxs[nxt].data_flags)


@pytest.mark.rules("DATA-CAS-001", "DATA-QUAL-001")
def test_a_frozen_run_inside_the_window_that_starts_late_is_not_the_auction_freeze():
    d = date(2026, 8, 5)
    df = minute_rows([(24500 + k % 3, 24506 + k % 3, 24496 + k % 3, 24501 + k % 3) for k in range(75)], d)
    idx = df.index[(df.timestamp >= datetime(2026, 8, 5, 15, 20, tzinfo=IST)) & (df.timestamp <= datetime(2026, 8, 5, 15, 27, tzinfo=IST))]
    df.loc[idx, ["open", "high", "low", "close"]] = 24500.0  # frozen 15:20..15:27: inside the window, but it did not start at 15:15/15:16
    _, infos = build_session_contexts(pd.concat([df, _stub(d, 24501.0)], ignore_index=True), verified_holidays=set(), calendar=CAS)
    assert infos[d].quality.value == "UNVERIFIED" and not infos[d].usable
    assert infos[d].reasons == ("FROZEN_RUN_INSIDE_AUCTION_WINDOW_STARTS_AFTER_1516",)


@pytest.mark.rules("RF-001", "RF-008")
def test_a_session_closing_exactly_at_its_ema_is_not_counted_as_above_it():
    days = list(pd.bdate_range("2026-01-05", periods=5).date)
    frames = [session(d, [(100, 101, 99, 100)] * 75, 100.0) for d in days]  # every close == the constant EMA(100)
    ctxs, _ = build_session_contexts(pd.concat(frames), verified_holidays=set(), calendar=MarketCalendar())
    assert ctxs[days[4]].prior_session_ema_above[0] is False  # close == EMA -> not above (strict)
