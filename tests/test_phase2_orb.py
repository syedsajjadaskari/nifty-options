"""ORB signal engine (decision at 09:20)."""

import math

import pytest
from synthetic import ctx

from nifty_trading.strategies import ORBStrategy, ProposalConfig

PREV = {"cands": [(23900, 24000, 23800, 23900)], "close": 23900.0, "ema_last": 23950.0}  # PDH 24000 / PDL 23800
STRONG_UP = (24005, 24060, 24000, 24055)  # body 50/60, upper wick 5/60
STRONG_DN = (23795, 23800, 23740, 23745)  # mirror below PDL


def run(c0, *, prev=PREV, ema=23950.0, prior=(True,), **prop):
    prop.setdefault("trend_mode", "EMA5M_PREV_SESSION")  # these fixtures test other logic with the Phase 2.1 trend proposal; the structure mode is tested in test_phase22_rules
    c = ctx([c0, (c0[3], c0[3] + 1, c0[3] - 1, c0[3])], prev=prev, ema=ema, prior_above=prior)
    return ORBStrategy(proposals=ProposalConfig(**prop)).evaluate_session(c)


def pick(recs, method, direction):
    return [r for r in recs if r.method == method and r.direction == direction]


@pytest.mark.rules("ORB-GLOBAL-004", "ORB-GLOBAL-001", "ORB-M1-LONG-001", "ORB-M1-LONG-002", "ORB-M1-LONG-003", "ORB-TREND-001", "ORB-TREND-002")
def test_m1_long_confirms_at_0920_after_the_first_candle_closes():
    [r] = pick(run(STRONG_UP), "Method 1", "LONG")
    assert r.signal_status == "CONFIRMED" and r.signal_timestamp.strftime("%H:%M") == "09:20"
    assert r.reference_levels["level_broken"] == 24000 and r.reference_levels["entry_reference_price"] == 24055
    assert "ORB-MA-001" in r.rule_ids_unresolved and r.verification_status == "PROPOSAL_DEPENDENT"  # 200 EMA/DMA wording conflict


@pytest.mark.rules("ORB-GLOBAL-002", "ORB-M1-SHORT-001", "ORB-M1-SHORT-002", "ORB-M1-SHORT-003")
def test_m1_short_mirror():
    [r] = pick(run(STRONG_DN, ema=24000.0, prior=(False,)), "Method 1", "SHORT")
    assert r.signal_status == "CONFIRMED" and r.reference_levels["level_broken"] == 23800


@pytest.mark.rules("ORB-M1-LONG-002")
def test_m1_wick_above_level_without_a_close_above_is_not_a_breakout():
    assert not pick(run((23990, 24060, 23985, 23995)), "Method 1", "LONG")  # high > PDH but close < PDH
    assert not pick(run((24000, 24060, 23990, 24000)), "Method 1", "LONG")  # close == level is not 'above'


@pytest.mark.rules("ORB-M1-LONG-003", "ORB-CANDLE-001")
def test_m1_weak_or_rejected_candle_is_invalidated():
    [r] = pick(run((24005, 24060, 24000, 24020)), "Method 1", "LONG")  # body 15/60: not a strong body
    assert r.signal_status == "INVALIDATED" and "CANDLE_QUALITY" in r.invalidation_reason and "ORB-M1-LONG-003" in r.rule_ids_failed
    [r2] = pick(run((24005, 24100, 24000, 24060)), "Method 1", "LONG")  # long upper wick (40/100): rejection
    assert r2.signal_status == "INVALIDATED"


@pytest.mark.rules("ORB-TREND-001", "ORB-TREND-002", "RF-008")
def test_m1_trend_filter_blocks_and_modes_are_distinct():
    [r] = pick(run(STRONG_UP, ema=24100.0), "Method 1", "LONG")  # close below the EMA
    assert r.signal_status == "INVALIDATED" and r.invalidation_reason.startswith("TREND:")
    # price above the EMA but the previous session was below it: only the stricter mode rejects
    assert pick(run(STRONG_UP, prior=(False,), trend_mode="EMA5M_BASIC"), "Method 1", "LONG")[0].signal_status == "CONFIRMED"
    assert pick(run(STRONG_UP, prior=(False,), trend_mode="EMA5M_PREV_SESSION"), "Method 1", "LONG")[0].signal_status == "INVALIDATED"


@pytest.mark.rules("DATA-WARM-001", "ORB-TREND-001")
def test_indicator_warmup_gives_not_evaluated_never_a_signal():
    [r] = pick(run(STRONG_UP, ema=math.nan), "Method 1", "LONG")
    assert r.signal_status == "NOT_EVALUATED" and "WARMUP" in r.invalidation_reason and r.verification_status == "NOT_READY"
    # the daily-200 candidate cannot be evaluated with fewer than 200 prior daily bars
    [d] = pick(run(STRONG_UP, trend_mode="SMA200_DAILY"), "Method 1", "LONG")
    assert d.signal_status == "NOT_EVALUATED" and "DAILY_MA_WARMUP" in d.invalidation_reason


@pytest.mark.rules("ORB-GLOBAL-001")
def test_data_quality_unverified_previous_session_blocks_evaluation():
    [r] = run(STRONG_UP, prev={**PREV, "unverified": True})
    assert r.signal_status == "NOT_EVALUATED" and "PREV_SESSION_UNVERIFIED" in r.invalidation_reason
    [r2] = ORBStrategy().evaluate_session(ctx([STRONG_UP], prev=None, ema=1.0))
    assert r2.invalidation_reason == "NO_PREVIOUS_SESSION_IN_DATASET"


# ------------------------------------------------------------------ Gap + 200 MA
GAP_PREV = {"cands": [(23900, 24200, 23800, 23900)], "close": 23900.0, "ema_last": 23950.0}  # PDH 24200: M1 not triggered


@pytest.mark.rules("ORB-GAP-LONG-001", "ORB-GAP-LONG-002", "ORB-GAP-LONG-003", "ORB-GAP-LONG-004", "ORB-GAP-LONG-005")
def test_gap_long_crosses_ma_and_closes_beyond_it():
    [g] = pick(run(STRONG_UP, prev=GAP_PREV, prior=(False,)), "Gap/200DMA", "LONG")  # no established trend needed
    assert g.signal_status == "CONFIRMED" and g.reference_levels["gap_points"] == 105
    assert "ORB-GAP-LONG-005" in g.rule_ids_unresolved and g.verification_status == "RESEARCH_VARIANT"  # 'excessively extended' undefined


@pytest.mark.rules("ORB-GAP-LONG-003")
def test_gap_long_candle_that_only_crosses_the_ma_but_closes_below_does_not_qualify():
    [g] = pick(run((23960, 23970, 23900, 23930), prev=GAP_PREV), "Gap/200DMA", "LONG")
    assert g.signal_status == "INVALIDATED" and g.invalidation_reason == "CLOSE_NOT_BEYOND_MA"


@pytest.mark.rules("ORB-GAP-LONG-002")
def test_gap_that_does_not_cross_the_ma_is_not_this_setup():
    above = {**GAP_PREV, "close": 24000.0}  # previous close already above the MA: no crossing
    assert not pick(run(STRONG_UP, prev=above), "Gap/200DMA", "LONG")


@pytest.mark.rules("ORB-GAP-LONG-005", "ORB-GAP-SHORT-004")
def test_gap_excess_filter_is_off_by_default_and_applies_only_as_a_labelled_proposal():
    capped = run(STRONG_UP, prev=GAP_PREV, gap_max_points=50.0)
    [g] = pick(capped, "Gap/200DMA", "LONG")
    assert g.signal_status == "INVALIDATED" and g.invalidation_reason == "GAP_EXCEEDS_PROPOSED_CAP"


@pytest.mark.rules("ORB-GAP-LONG-004", "ORB-CANDLE-001")
def test_gap_long_rejects_strong_upper_wick_candle():
    [g] = pick(run((24005, 24100, 24000, 24040), prev=GAP_PREV), "Gap/200DMA", "LONG")
    assert g.signal_status == "INVALIDATED"


@pytest.mark.rules("ORB-GAP-SHORT-001", "ORB-GAP-SHORT-002", "ORB-GAP-SHORT-003")
def test_gap_short_mirror():
    prev = {"cands": [(24100, 24200, 23900, 24100)], "close": 24100.0, "ema_last": 24050.0}  # previous close above the MA
    [g] = pick(run((24000, 24005, 23940, 23945), prev=prev, ema=24050.0), "Gap/200DMA", "SHORT")
    assert g.signal_status == "CONFIRMED"


# ------------------------------------------------------------------ Method 2 (research variant)
def _prev_session_with_trendline():
    """Previous session: rising k=2 fractal lows (25 @2, 29 @7), PDH 70 @5, inner k=2 fractal high 60 @10 (prices = 23900 + 2x)."""
    lows = [30, 28, 25, 28, 31, 33, 32, 29, 31, 34, 36, 37, 38, 40]
    highs = [40, 38, 35, 38, 41, 70, 42, 39, 41, 44, 60, 47, 48, 50]
    cands = []
    for lo, hi in zip(lows, highs, strict=True):
        l, h = 23900 + 2 * lo, 23900 + 2 * hi
        cands.append((l + 0.4 * (h - l), h, l, l + 0.6 * (h - l)))
    return {"cands": cands, "close": 23980.0, "ema_last": 23900.0}


@pytest.mark.rules("ORB-M2-LONG-001", "ORB-M2-LONG-002", "ORB-M2-LONG-003", "ORB-M2-LONG-004", "ORB-M2-LONG-005")
def test_m2_inner_level_break_with_supportive_trendline_is_only_a_research_variant():
    recs = run((24010, 24070, 24005, 24065), prev=_prev_session_with_trendline(), ema=23900.0)
    [r] = pick(recs, "Method 2", "LONG")
    assert r.signal_status == "CONFIRMED" and r.reference_levels["inner_level"] == 24020.0
    assert r.reference_levels["trendline_value_at_open"] == pytest.approx(23900 + 2 * 34.6)
    assert r.verification_status == "RESEARCH_VARIANT" and "ORB-M2-LONG-001" in r.rule_ids_unresolved  # never presented as verified


@pytest.mark.rules("ORB-M2-LONG-004")
def test_m2_near_the_ma_without_a_convincing_close_is_rejected():
    recs = run((24010, 24070, 24005, 24065), prev=_prev_session_with_trendline(), ema=24062.0)  # close only 3 pts above the EMA
    [r] = pick(recs, "Method 2", "LONG")
    assert r.signal_status == "INVALIDATED" and r.invalidation_reason == "NEAR_MA_NOT_CONVINCING"


@pytest.mark.rules("ORB-M2-LONG-001", "ORB-M2-LONG-005")
def test_m2_without_a_constructible_trendline_does_not_signal():
    prev = {"cands": [(23900, 24000, 23880, 23950)] * 6 + [(23950, 24010, 23940, 24000)] * 6, "close": 24000.0, "ema_last": 23900.0}
    recs = run((24005, 24070, 24001, 24065), prev=prev, ema=23900.0)
    assert not [r for r in recs if r.method == "Method 2" and r.signal_status == "CONFIRMED"]


@pytest.mark.rules("ORB-M2-SHORT-001", "ORB-M2-SHORT-002", "ORB-M2-SHORT-003", "ORB-M2-SHORT-004", "ORB-GLOBAL-002")
def test_m2_short_mirror_is_a_research_variant_too():
    mirror = _prev_session_with_trendline()
    cands = [(47800 - c, 47800 - l, 47800 - h, 47800 - o) for (o, h, l, c) in mirror["cands"]]  # reflect every price about 23,900
    prev = {"cands": cands, "close": 47800 - 23980.0, "ema_last": 23900.0}
    recs = run((23790, 23795, 23730, 23735), prev=prev, ema=23900.0, prior=(False,))
    [r] = pick(recs, "Method 2", "SHORT")
    assert r.signal_status == "CONFIRMED" and r.reference_levels["inner_level"] == 23780.0
    assert r.reference_levels["trendline_value_at_open"] == pytest.approx(23830.8)
    assert r.verification_status == "RESEARCH_VARIANT" and "ORB-M2-SHORT-001" in r.rule_ids_unresolved
    far = run((23790, 23795, 23730, 23735), prev=prev, ema=23737.0, prior=(False,))  # close only 2 below the EMA: not convincing
    assert pick(far, "Method 2", "SHORT")[0].invalidation_reason == "NEAR_MA_NOT_CONVINCING"
