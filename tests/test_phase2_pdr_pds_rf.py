"""PDR, PDS and RF signal engines."""

import pytest
from synthetic import ctx

from nifty_trading.strategies import (
    RF_TARGET_STATUS,
    PDRStrategy,
    PDSStrategy,
    ProposalConfig,
    RFStrategy,
)


def conf(recs, method=None):
    return [r for r in recs if r.signal_status == "CONFIRMED" and (method is None or r.method == method)]


# ------------------------------------------------------------------------------- PDR
PDR_PREV = {"cands": [(23960, 23970, 23950, 23965), (23980, 24000, 23970, 23975), (23975, 23985, 23960, 23962)], "close": 23950.0}
# previous-day high 24000 on candle 2: body 23975-23980, zone (ZONE_FULL) = [23975, 24000]


def pdr(cands, prev=PDR_PREV, **prop):
    prop.setdefault("pdr_zone_method", "A_HIGHEST_HIGH")  # fixtures use the highest-high candle, a DIAGNOSTIC reference since Phase 2.3
    prop.setdefault("zone_lower_boundary", "ZONE_FULL")  # fixtures written for the full-body candidate; the Phase 2.2 default (ZONE_WICK) is tested in test_phase22_rules
    prop.setdefault("zone_proximity_points", 5.0)  # these fixtures exercise the near-touch variant; the strict default is tested in test_phase22_rules
    return PDRStrategy(proposals=ProposalConfig(**prop)).evaluate_session(ctx(cands, prev=prev))


@pytest.mark.rules("PDR-002", "PDR-003", "PDR-004", "PDR-006", "PDR-007", "PDR-001")
def test_pdr_gap_up_return_to_zone_then_green_candle():
    cands = [(24050, 24060, 24040, 24055), (24055, 24058, 24001, 24003), (24003, 24030, 24002, 24025)]  # c1 tests zone (red), c2 green
    [s] = conf(pdr(cands))
    assert s.direction == "LONG" and s.signal_candle_start.strftime("%H:%M") == "09:25" and s.signal_candle_close == 24025
    assert s.reference_levels["zone_low"] == 23975 and s.reference_levels["zone_high"] == 24000
    assert s.verification_status == "PROPOSAL_DEPENDENT" and "PDR-010" in s.rule_ids_unresolved  # reversal clarity undefined


@pytest.mark.rules("PDR-005")
def test_pdr_price_that_keeps_rising_without_returning_gives_no_setup():
    assert pdr([(24050, 24060, 24040, 24055), (24055, 24080, 24050, 24075), (24075, 24100, 24070, 24095)]) == []


@pytest.mark.rules("PDR-004")
def test_pdr_gap_down_or_flat_open_is_never_evaluated():
    assert pdr([(23940, 23960, 23930, 23955), (23955, 24010, 23950, 24005)]) == []  # open 23940 < previous close 23950: gap down


@pytest.mark.rules("PDR-011", "PDR-004")
def test_pdr_gap_up_that_does_not_clear_the_zone_is_invalidated():
    [r] = pdr([(23990, 24010, 23985, 24005), (24005, 24020, 24000, 24015)], pdr_open_vs_zone="ABOVE_ZONE")  # gap up but open inside the zone
    assert r.signal_status == "INVALIDATED" and r.invalidation_reason == "GAP_UP_OPEN_NOT_ABOVE_ZONE"


@pytest.mark.rules("PDR-007")
def test_pdr_green_candle_must_come_after_the_interaction_candle_by_default():
    cands = [(24050, 24060, 24040, 24055), (24003, 24058, 24001, 24030), (24030, 24040, 24020, 24038)]  # c1 touches the zone AND is green
    assert [r.signal_candle_start.strftime("%H:%M") for r in conf(pdr(cands))] == ["09:25"]  # waits for the NEXT green candle
    assert [r.signal_candle_start.strftime("%H:%M") for r in conf(pdr(cands, pdr_green_may_be_interaction_candle=True))] == ["09:20"]


@pytest.mark.rules("PDR-006")
def test_pdr_zone_proximity_candidates_change_what_counts_as_a_test():
    cands = [(24050, 24060, 24040, 24055), (24055, 24058, 24006, 24010), (24010, 24030, 24008, 24025)]  # low 24006: 6 pts above the zone
    assert not conf(pdr(cands))  # default proximity 5
    assert conf(pdr(cands, zone_proximity_points=10.0))


@pytest.mark.rules("PDR-002")
def test_pdr_zone_lower_boundary_candidates():
    z_full = conf(pdr([(24050, 24060, 24040, 24055), (24055, 24058, 24001, 24003), (24003, 24030, 24002, 24025)]))[0].reference_levels
    z_wick = conf(pdr([(24050, 24060, 24040, 24055), (24055, 24058, 24001, 24003), (24003, 24030, 24002, 24025)],
                      zone_lower_boundary="ZONE_WICK"))[0].reference_levels
    assert z_full["zone_low"] == 23975 and z_wick["zone_low"] == 23980


@pytest.mark.rules("PDR-012")
def test_pdr_reports_only_the_first_signal_per_session_unless_configured():
    cands = [(24050, 24060, 24040, 24055), (24055, 24058, 24001, 24003), (24003, 24030, 24002, 24025),
             (24060, 24070, 24055, 24065), (24065, 24068, 24002, 24005), (24005, 24030, 24003, 24025)]
    assert len(conf(pdr(cands))) == 1
    assert len(conf(pdr(cands, max_signals_per_session=2))) == 2


@pytest.mark.rules("PDR-010")
def test_pdr_reversal_filter_is_off_by_default_and_clear_reversal_passes_when_on():
    cands = [(24050, 24060, 24040, 24055), (24055, 24058, 24001, 24003), (24003, 24030, 24002, 24025)]
    [off] = conf(pdr(cands))
    assert off.rule_ids_unresolved == ["PDR-010"]  # filter OFF: the mandatory 'clear reversal' checklist item is reported unresolved
    [on] = conf(pdr(cands, pdr_reversal_filter="DEPTH_25PCT"))  # high fell 40 of a 50-point day after the peak (>= 25%)
    assert on.rule_ids_unresolved == []


@pytest.mark.rules("PDR-010")
def test_pdr_previous_day_high_with_no_reversal_is_invalidated_when_filter_is_on():
    prev = {"cands": [(23960, 23970, 23950, 23965), (23975, 24000, 23970, 23995)], "close": 23950.0}  # high on the last candle
    cands = [(24050, 24060, 24040, 24055), (24055, 24058, 24001, 24003), (24003, 24030, 24002, 24025)]
    [r] = pdr(cands, prev=prev, pdr_reversal_filter="DEPTH_25PCT")
    assert r.signal_status == "INVALIDATED" and r.invalidation_reason.startswith("PREV_DAY_REVERSAL_NOT_CLEAR")


# ------------------------------------------------------------------------------- PDS
PDS_PREV = {"cands": [(24040, 24050, 24030, 24045), (24020, 24030, 24000, 24010), (24010, 24060, 24005, 24055)], "close": 24100.0}
# previous-day low 24000 on candle 1: zone = [24000 (low), 24020 (body top)]


def pds(cands, prev=PDS_PREV, **prop):
    return PDSStrategy(proposals=ProposalConfig(**prop)).evaluate_session(ctx(cands, prev=prev))


@pytest.mark.rules("PDS-001", "PDS-002", "PDS-MISSING-001", "PDS-003", "PDS-005", "PDS-M-001", "PDS-M1-001")
def test_pds_method1_first_red_candle_at_zone_is_a_good_red_candle():
    cands = [(23950, 23960, 23940, 23945), (24010, 24015, 23960, 23965)]
    [s] = conf(pds(cands), "Method 1")
    assert s.direction == "SHORT" and s.signal_timestamp.strftime("%H:%M") == "09:25" and s.reference_levels["zone_high"] == 24020
    assert s.reference_levels["zone_low"] == 24000  # PDS-002: lower wick tip .. body top of the previous-day-low candle
    assert s.verification_status == "PROPOSAL_DEPENDENT"  # 'good body' is not numerically defined in the source


@pytest.mark.rules("PDS-M2-001")
def test_pds_method2_red_pin_bar_with_higher_price_rejection():
    cands = [(23950, 23960, 23940, 23945), (24005, 24030, 24000, 24002)]
    recs = pds(cands)
    assert [r.method for r in conf(recs)] == ["Method 2"]


@pytest.mark.rules("PDS-M3-001", "PDS-M-001")
def test_pds_method3_after_a_weak_first_red_candle_wait_for_small_support_break():
    cands = [(23950, 23960, 23940, 23945), (24010, 24012, 24004, 24006), (24006, 24008, 24000, 24005),
             (24005, 24010, 24003, 24009), (24009, 24010, 23980, 23985)]
    recs = pds(cands)
    [s] = conf(recs)
    assert s.method == "Method 3" and s.signal_candle_close == 23985 and s.reference_levels["small_support"] == 24000
    assert not conf(recs, "Method 1") and not conf(recs, "Method 2")


@pytest.mark.rules("PDS-M3-001")
def test_pds_method3_touch_basis_fires_earlier_than_close_basis():
    cands = [(23950, 23960, 23940, 23945), (24010, 24012, 24004, 24006), (24006, 24008, 24000, 24005),
             (24005, 24010, 24003, 24009), (24009, 24010, 23995, 24002)]  # low pierces 24000, closes above it
    assert not conf(pds(cands))
    assert [r.method for r in conf(pds(cands, pds_m3_break_basis="TOUCH"))] == ["Method 3"]


@pytest.mark.rules("PDS-004")
def test_pds_is_not_a_breakdown_strategy_no_entry_without_a_rally_into_the_zone():
    assert pds([(23950, 23960, 23940, 23945), (23945, 23955, 23920, 23925), (23925, 23940, 23900, 23905)]) == []


@pytest.mark.rules("PDS-003")
def test_pds_gap_up_day_is_not_evaluated():
    assert pds([(24120, 24130, 24110, 24125), (24125, 24135, 24115, 24120)]) == []


@pytest.mark.rules("PDS-M-001")
def test_pds_only_the_first_red_candle_counts_for_methods_1_and_2():
    # first red candle at the zone is weak; a later strong red candle must NOT be taken as Method 1
    cands = [(23950, 23960, 23940, 23945), (24010, 24012, 24004, 24006), (24010, 24015, 23960, 23965)]
    assert not conf(pds(cands), "Method 1")


@pytest.mark.rules("PDS-006")
def test_pds_gap_down_that_does_not_clear_the_zone_is_invalidated():
    [r] = pds([(24010, 24015, 24000, 24005), (24005, 24010, 23990, 23995)])  # gap down vs 24,100 close, but the open (24,010) is inside the zone
    assert r.signal_status == "INVALIDATED" and r.invalidation_reason == "GAP_DOWN_OPEN_NOT_BELOW_ZONE"
    assert pds([(24010, 24015, 24000, 24005)], pds_open_vs_zone="ANY") != []  # the proposal can be switched off


@pytest.mark.rules("PDS-007")
def test_pds_reports_only_the_first_signal_per_session_unless_configured():
    cands = [(23950, 23960, 23940, 23945), (24010, 24015, 23960, 23965), (23965, 23970, 23930, 23935),
             (23935, 23940, 23920, 23925), (24010, 24015, 23960, 23965)]
    assert len(conf(pds(cands))) == 1
    assert len(conf(pds(cands, max_signals_per_session=2))) == 2


@pytest.mark.rules("PDS-M3-001")
def test_pds_method3_standalone_is_off_by_default_and_available_as_variant():
    # green candles at the zone (no red candle at all), then a close below the small support (24,001)
    cands = [(23950, 23960, 23940, 23945), (24005, 24015, 24003, 24012), (24012, 24016, 24001, 24014),
             (24014, 24018, 24002, 24016), (23990, 23995, 23985, 23992)]
    assert not conf(pds(cands))  # Method 3 only follows a weak first red candle
    [s] = conf(pds(cands, pds_m3_standalone=True))
    assert s.method == "Method 3" and s.reference_levels["small_support"] == 24001


# -------------------------------------------------------------------------------- RF
RF_PREV = {"cands": [(24000, 24100, 23900, 24000)], "close": 24000.0, "ema_last": 23950.0}  # yesterday's range 23900-24100


def rf(cands, prev=RF_PREV, ema=23950.0, prior=(True,), **prop):
    prop.setdefault("trend_mode", "EMA5M_PREV_SESSION")  # these fixtures test other logic with the Phase 2.1 trend proposal; the structure mode is tested in test_phase22_rules
    return RFStrategy(proposals=ProposalConfig(**prop)).evaluate_session(ctx(cands, prev=prev, ema=ema, prior_above=prior))


RF_OK = [(24020, 24040, 24000, 24030), (24030, 24032, 23985, 23990), (23990, 24020, 23988, 24015)]


@pytest.mark.rules("RF-002", "RF-005", "RF-006", "RF-007", "RF-001", "RF-003", "RF-004", "RF-012")
def test_rf_full_sequence_close_below_then_return_inside():
    [s] = conf(rf(RF_OK))
    assert s.direction == "LONG" and s.signal_timestamp.strftime("%H:%M") == "09:30" and s.signal_candle_close == 24015
    assert s.reference_levels["RF_High"] == 24040 and s.reference_levels["RF_Low"] == 24000
    assert "RF_DIRECTION_IMPLIED_NOT_STATED" in s.flags and s.verification_status == "PROPOSAL_DEPENDENT"


@pytest.mark.rules("RF-011", "RF-009", "RF-010")
def test_rf_target_stays_a_proposal_and_does_not_block_signal_detection():
    [s] = conf(rf(RF_OK))
    assert RF_TARGET_STATUS == "PROPOSED_FOR_REVIEW" and s.reference_levels["RF_TARGET_STATUS"] == "PROPOSED_FOR_REVIEW"
    assert {"RF-009", "RF-011"} <= set(s.rule_ids_unresolved)
    assert "target_points" not in s.reference_levels  # no silent 60 / 70


@pytest.mark.rules("RF-005", "RF-013")
def test_rf_wick_below_rf_low_without_a_close_below_does_nothing():
    assert rf([(24020, 24040, 24000, 24030), (24030, 24032, 23985, 24005), (24005, 24020, 24001, 24015)]) == []


@pytest.mark.rules("RF-007")
def test_rf_wrong_order_return_inside_before_close_below_does_not_activate():
    cands = [(24020, 24040, 24000, 24030), (24030, 24035, 24010, 24020), (24020, 24022, 23980, 23985)]  # inside first, closes below last
    recs = rf(cands)
    assert not conf(recs) and all(r.signal_status == "INCOMPLETE_AT_EOD" for r in recs)


@pytest.mark.rules("RF-003")
def test_rf_gap_down_invalidates_even_though_the_price_sequence_completes():
    prev = {**RF_PREV, "close": 24060.0}  # open 24020 is BELOW the previous close -> gap down
    [r] = rf(RF_OK, prev=prev)
    assert r.signal_status == "INVALIDATED" and r.invalidation_reason.startswith("GAP_NOT_UP") and "RF-003" in r.rule_ids_failed


@pytest.mark.rules("RF-004")
def test_rf_gap_beyond_yesterdays_high_is_rejected():
    prev = {"cands": [(24000, 24010, 23900, 24000)], "close": 24000.0, "ema_last": 23950.0}  # PDH 24010 < today's open 24020
    [r] = rf(RF_OK, prev=prev)
    assert r.signal_status == "INVALIDATED" and r.invalidation_reason == "GAP_UP_OUTSIDE_YESTERDAYS_RANGE"


@pytest.mark.rules("RF-001", "RF-008")
def test_rf_previous_downtrend_with_sudden_gap_above_the_ema_is_rejected():
    [r] = rf(RF_OK, prior=(False,))
    assert r.signal_status == "INVALIDATED" and r.invalidation_reason.startswith("TREND:")
    assert conf(rf(RF_OK, prior=(False,), trend_mode="EMA5M_BASIC"))  # the weaker 'above the EMA only' candidate would accept it


@pytest.mark.rules("RF-001")
def test_rf_ema_warmup_gives_not_evaluated():
    [r] = rf(RF_OK, ema=float("nan"))
    assert r.signal_status == "NOT_EVALUATED" and r.verification_status == "NOT_READY"


@pytest.mark.rules("RF-006")
def test_rf_return_inside_candidates_are_distinct():
    cands = [(24020, 24040, 24000, 24030), (24030, 24032, 23985, 23990), (23990, 23999, 23980, 23995), (23995, 24020, 23990, 24015)]
    assert [r.signal_candle_start.strftime("%H:%M") for r in conf(rf(cands))] == ["09:30"]  # R1: first CLOSE back inside
    assert [r.signal_candle_start.strftime("%H:%M") for r in conf(rf(cands, rf_return_inside_def="R3"))] == []  # R3: must be the very next candle
    touch = cands[:2] + [(23990, 24001, 23980, 23995)] + cands[3:]
    assert [r.signal_candle_start.strftime("%H:%M") for r in conf(rf(touch, rf_return_inside_def="R2"))] == ["09:25"]  # R2: touch counts


@pytest.mark.rules("RF-014")
def test_rf_incomplete_sequence_at_end_of_day_is_reported():
    [r] = rf([(24020, 24040, 24000, 24030), (24030, 24032, 23985, 23990), (23990, 23995, 23980, 23985)])
    assert r.signal_status == "INCOMPLETE_AT_EOD"


@pytest.mark.rules("PDS-006")
def test_pds_any_mode_does_not_block_and_the_default_does_block_an_open_inside_the_zone():
    inside = [(24010, 24015, 24000, 24005), (24005, 24010, 23990, 23995)]  # gap down vs 24,100 but open inside [24000, 24020]
    assert [r.invalidation_reason for r in pds(inside)] == ["GAP_DOWN_OPEN_NOT_BELOW_ZONE"]
    assert all(r.invalidation_reason is None or not r.invalidation_reason.startswith("GAP_DOWN_OPEN") for r in pds(inside, pds_open_vs_zone="ANY"))


@pytest.mark.rules("PDR-011")
def test_pdr_records_pdr_011_as_satisfied_only_when_an_open_condition_is_active():
    cands = [(24050, 24060, 24040, 24055), (24055, 24058, 24001, 24003), (24003, 24030, 24002, 24025)]
    assert "PDR-011" in conf(pdr(cands))[0].rule_ids_satisfied  # default ABOVE_ZONE
    assert "PDR-011" not in conf(pdr(cands, pdr_open_vs_zone="ANY"))[0].rule_ids_satisfied
