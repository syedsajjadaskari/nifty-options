"""Candle geometry, swings, wick share, trend filter (Tasks 5, 6)."""

import math

import pytest
from synthetic import ctx

from nifty_trading.strategies.definitions import (
    Candle,
    bearish_pin,
    bullish_pin,
    gap_info,
    pivot_highs,
    pivot_lows,
    strong_bearish,
    strong_bullish,
    trend_check,
    wick_share_in_band,
    wick_share_outside,
)
from nifty_trading.strategies.params import ConfigError, ProposalConfig

NAN = math.nan
T = None


def C(o, h, l, c, ema=NAN):  # noqa: E741
    return Candle(T, T, o, h, l, c, ema)


P = ProposalConfig()


def test_zero_range_candle_never_qualifies_and_does_not_divide_by_zero():
    z = C(100, 100, 100, 100)
    assert not strong_bullish(z, P) and not strong_bearish(z, P) and not bullish_pin(z, P) and not bearish_pin(z, P)


def test_strong_and_pin_shapes():
    assert strong_bullish(C(100, 110, 99.5, 109.5), P)  # body 9.5/10.5, upper wick 0.5
    assert not strong_bullish(C(100, 110, 100, 103), P)  # small body, big upper wick
    assert strong_bearish(C(110, 110.5, 100, 100.5), P)
    assert bearish_pin(C(100, 110, 99, 100.5), P)  # long upper wick, tiny body
    assert bullish_pin(C(105, 105.5, 95, 104.5), P)  # long lower wick


@pytest.mark.rules("IRF-M3-003")
def test_irf_page12_wick_share_illustration():
    """IRH=100; red candle opens 92, high 115, close 82 -> 15/23 = 65%."""
    c = C(92, 115, 80, 82)
    share = wick_share_outside(c, 100)
    assert share == pytest.approx(15 / 23) and round(share * 100) == 65
    assert wick_share_in_band(share, P)  # literal 60-70% band


@pytest.mark.rules("IRF-M3-003")
def test_wick_share_band_boundaries_and_candidates():
    assert wick_share_in_band(0.60, P) and wick_share_in_band(0.70, P)
    assert not wick_share_in_band(0.5999, P) and not wick_share_in_band(0.7001, P)
    assert wick_share_in_band(0.90, ProposalConfig(m3_wick_share_band="MIN_60"))
    assert wick_share_in_band(0.56, ProposalConfig(m3_wick_share_band="BAND_55_75"))
    assert wick_share_outside(C(100, 100, 90, 95), 100) is None  # no upper wick


def test_pivots_are_confirmed_only_by_candles_before_the_evaluation_index():
    lows = [10, 9, 8, 9, 10, 11]
    cs = [C(l + 1, l + 2, l, l + 1) for l in lows]
    assert pivot_lows(cs, 0, 3, 1) == []  # evaluating candle 3: only candles 0..2 are known, pivot at 2 unconfirmed
    assert pivot_lows(cs, 0, 4, 1) == [2]  # evaluating candle 4: candle 3 confirms the pivot at 2
    highs = [1, 3, 2, 1]
    ch = [C(h, h, h - 1, h) for h in highs]
    assert pivot_highs(ch, 0, 4, 1) == [1]


def test_proposal_config_rejects_overlapping_strong_and_pin_thresholds(monkeypatch):
    from nifty_trading.strategies import params

    for s_ in ("STRICT", "MODERATE", "LOOSE"):
        for p_ in ("STRICT", "MODERATE", "LOOSE"):
            ProposalConfig(strong_candle=s_, pin_bar=p_)  # every shipped combination is mutually exclusive
    monkeypatch.setitem(params.STRONG_CANDLE, "LOOSE", {"body_ratio_min": 0.40, "opposite_wick_ratio_max": 0.25})
    with pytest.raises(ConfigError):
        ProposalConfig(strong_candle="LOOSE", pin_bar="LOOSE")  # 0.40 + 0.55 <= 1: a candle could be both
    with pytest.raises(ConfigError):
        ProposalConfig(trend_mode="NOPE")


@pytest.mark.rules("ORB-TREND-001", "ORB-TREND-002", "RF-008")
def test_trend_modes_and_warmup_are_explicit_not_silent():
    base = [(100, 101, 99, 100.5)]
    c = ctx(base, ema=90.0, prior_above=(True, True, True))
    assert trend_check(c, 0, "LONG", "EMA5M_BASIC").ok is True
    assert trend_check(c, 0, "SHORT", "EMA5M_BASIC").ok is False
    # previous session was BELOW its EMA (RF p.5 invalid example): sudden gap above the EMA is not an established uptrend
    c2 = ctx(base, ema=90.0, prior_above=(False, False, False))
    assert trend_check(c2, 0, "LONG", "EMA5M_BASIC").ok is True
    assert trend_check(c2, 0, "LONG", "EMA5M_PREV_SESSION").ok is False
    assert trend_check(c2, 0, "LONG", "EMA5M_PREV_3_SESSIONS").ok is False
    assert trend_check(c2, 0, "SHORT", "EMA5M_PREV_SESSION").ok is False  # basic fails (close above ema)
    # warm-up: EMA NaN -> None, never True
    c3 = ctx(base, ema=NAN)
    r = trend_check(c3, 0, "LONG", "EMA5M_PREV_SESSION")
    assert r.ok is None and "WARMUP" in r.reason
    # history too short for the 3-session variant
    c4 = ctx(base, ema=90.0, prior_above=(True,))
    assert trend_check(c4, 0, "LONG", "EMA5M_PREV_3_SESSIONS").ok is None


@pytest.mark.rules("DATA-WARM-001", "ORB-MA-001")
def test_daily_200_ma_needs_200_prior_daily_bars():
    base = [(100, 101, 99, 100.5)]
    short_hist = ctx(base, ema=90.0, daily_count=47)
    assert trend_check(short_hist, 0, "LONG", "SMA200_DAILY").ok is None
    ok = ctx(base, ema=90.0, daily_sma=95.0, daily_count=200)
    assert trend_check(ok, 0, "LONG", "SMA200_DAILY").ok is True
    # 200 EMA(5m) and 200 DMA are NOT equated: same bar, opposite answers
    both = ctx(base, ema=90.0, daily_sma=120.0, daily_count=200)
    assert trend_check(both, 0, "LONG", "EMA5M_BASIC").ok is True
    assert trend_check(both, 0, "LONG", "SMA200_DAILY").ok is False


@pytest.mark.rules("ORB-GAP-LONG-001", "PDR-004", "PDS-003", "RF-003")
def test_gap_info_direction_and_unverified_previous_session():
    base = [(105, 106, 104, 105)]
    up = gap_info(ctx(base, prev={"cands": [(100, 101, 99, 100)], "close": 100.0}), P)
    assert up.direction == "UP" and up.points == 5
    flat = gap_info(ctx([(100, 101, 99, 100)], prev={"cands": [(100, 101, 99, 100)], "close": 100.0}), P)
    assert flat.direction == "NONE"
    unv = gap_info(ctx(base, prev={"cands": [(100, 101, 99, 100)], "close": 100.0, "unverified": True}), P)
    assert not unv.evaluable and unv.reason == "PREV_SESSION_UNVERIFIED"
    allowed = gap_info(ctx(base, prev={"cands": [(100, 101, 99, 100)], "close": 100.0, "unverified": True}),
                       ProposalConfig(allow_unverified_prev_session=True))
    assert allowed.evaluable
    assert not gap_info(ctx(base), P).evaluable  # no previous session at all


@pytest.mark.rules("IRF-SL-001", "PDS-SL-001")
def test_green_refs_include_the_signal_candle_and_respect_the_setup_start():
    from nifty_trading.strategies.definitions import green_refs
    cs = [C(10, 11, 9, 10.5), C(10.5, 12, 10, 10.2), C(10.2, 15, 10, 14)]  # green, red, green
    r = green_refs(cs, 2)
    assert r["recent_green_high"] == 15 and r["recent_green_close"] == 14 and r["setup_green_high"] == 15
    r1 = green_refs(cs, 1)  # the signal candle is red: the most recent green is candle 0
    assert r1["recent_green_high"] == 11
    assert green_refs(cs, 2, setup_start=1)["setup_green_high"] == 15 and green_refs(cs, 1, setup_start=1)["setup_green_high"] is None
