"""Proposal parameters for rules that the source documents state only qualitatively.

EVERYTHING here is an engineering interpretation labelled ``PROPOSED_FOR_REVIEW``. None of it is
an original strategy rule, and none of it was selected by looking at historical profitability
(Phase 2 forbids that). Each family lists separated candidate interpretations. Defaults follow the source
wording where it gives any; numeric thresholds are mid-range placeholders, discussed in ``ambiguous_rules.md``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

PROPOSAL_LABEL = "PROPOSED_FOR_REVIEW"


class ConfigError(ValueError):
    pass


# --- candle-shape candidates: name -> thresholds ---------------------------------------------
# body_ratio = |C-O| / (H-L); wick ratios are wick / (H-L); zero-range candles never qualify.
STRONG_CANDLE = {
    "STRICT": {"body_ratio_min": 0.70, "opposite_wick_ratio_max": 0.15},
    "MODERATE": {"body_ratio_min": 0.60, "opposite_wick_ratio_max": 0.20},
    "LOOSE": {"body_ratio_min": 0.50, "opposite_wick_ratio_max": 0.25},
}
PIN_BAR = {
    "STRICT": {"wick_ratio_min": 0.70, "body_ratio_max": 0.25, "opposite_wick_ratio_max": 0.10},
    "MODERATE": {"wick_ratio_min": 0.60, "body_ratio_max": 0.33, "opposite_wick_ratio_max": 0.15},
    "LOOSE": {"wick_ratio_min": 0.55, "body_ratio_max": 0.40, "opposite_wick_ratio_max": 0.20},
}
REJECTION_WICK = {  # wick/range at or above this counts as "strong rejection"
    "STRICT": {"wick_ratio_min": 0.25},
    "MODERATE": {"wick_ratio_min": 0.33},
    "LOOSE": {"wick_ratio_min": 0.40},
}
M3_WICK_SHARE_BAND = {  # share of the upper wick that lies above IRH
    "BAND_60_70": (0.60, 0.70),  # literal "approximately 60-70%"
    "MIN_60": (0.60, 1.00),
    "BAND_55_75": (0.55, 0.75),
}
# per-candidate descriptions used by the documentation generator
CANDIDATE_NOTES: dict[str, dict[str, str]] = {
    "strong_candle": {"STRICT": "body>=70% of range, opposite wick<=15%", "MODERATE": "body>=60%, opposite wick<=20%",
                      "LOOSE": "body>=50%, opposite wick<=25%"},
    "pin_bar": {"STRICT": "wick>=70%, body<=25%, opposite wick<=10%", "MODERATE": "wick>=60%, body<=33%, opp<=15%",
                "LOOSE": "wick>=55%, body<=40%, opp<=20%"},
    "rejection_wick": {"STRICT": "wick>=25% of range", "MODERATE": "wick>=33%", "LOOSE": "wick>=40%"},
    "trend_mode": {
        "EMA5M_BASIC": "close of the first 5m candle vs EMA(200) of completed 5m closes (the 'basic filter' only)",
        "EMA5M_PREV_SESSION": "BASIC + previous session's last 5m close already on the trend side of its EMA (encodes RF p.5 invalid example)",
        "EMA5M_PREV_3_SESSIONS": "BASIC + each of the previous 3 sessions closed on the trend side of its EMA",
        "SMA200_DAILY": "first-candle close vs SMA(200) of daily official closes up to the previous session (needs 200 prior daily bars)",
        "EMA200_DAILY": "as SMA200_DAILY but exponential",
    },
    "irf_support_def": {
        "SWING_K1": "latest 3-candle fractal low confirmed before the signal candle",
        "SWING_K2": "latest 5-candle fractal low (2 each side)",
        "LAST_N3": "lowest low of the 3 candles immediately before the signal candle",
    },
    "irf_resistance_def": {
        "FIRST_PUSH_TOP": "earliest 3-candle fractal high at/after the breakout candle",
        "LATEST_SWING_HIGH": "latest confirmed 3-candle fractal high after the breakout candle",
    },
    "m2b_push_must_precede_red_candle": {"False": "the candle that closes back below resistance may itself be the one that traded above it",
                                         "True": "a EARLIER candle must have traded back above the resistance"},
    "m2_extension_definition": {"E1": "a later candle makes a higher high than the breakout candle",
                                "E2": "a later candle also closes above IRH"},
    "m3_compression_def": {"C1": "previous N candles lie fully inside [IRL, IRH]",
                           "C2": "C1 and every one of them has range <= 50% of the initial-range height"},
    "m3_wick_share_band": {"BAND_60_70": "0.60 <= share <= 0.70 (literal)", "MIN_60": "share >= 0.60",
                           "BAND_55_75": "0.55 <= share <= 0.75"},
    "stop_distance_measure": {
        "GREEN_HIGH": "distance = high of the most recent green candle - entry (short)",
        "GREEN_CLOSE": "distance = close of the most recent green candle - entry (short)",
        "GREEN_SETUP_HIGH": "distance = highest high among green candles since the setup began - entry",
    },
    "zone_lower_boundary": {"ZONE_FULL": "PDR zone = [body bottom, wick top] (mirrors PDS text 'body and wick')",
                            "ZONE_WICK": "PDR zone = [body top, wick top] (wick only)"},
    "zone_proximity_points": {"0": "touch only", "5": "within 5 index points", "10": "within 10 index points"},
    "rf_return_inside_def": {"R1": "first later candle that CLOSES back inside [RF_L, RF_H]",
                             "R2": "first later candle whose range touches RF_L (High >= RF_L)",
                             "R3": "only the very next candle after the close-below, closing inside"},
    "pds_small_support_def": {"SWING_K1_NEAR_ZONE": "fractal low formed after the weak red candle within the zone band",
                              "LAST_N2": "lowest low of the 2 candles before the signal candle"},
    "pds_m3_break_basis": {"CLOSE": "a candle CLOSES below the small support", "TOUCH": "a candle's low trades below it"},
    "orb_prev_day_level_def": {"PREV_DAY_HL": "previous session high (resistance) / low (support)"},
}


@dataclass(frozen=True)
class ProposalConfig:
    """Selected interpretation of each ambiguous rule. All values are PROPOSED_FOR_REVIEW."""

    label: str = PROPOSAL_LABEL
    strong_candle: str = "MODERATE"
    pin_bar: str = "MODERATE"
    rejection_wick: str = "MODERATE"
    trend_mode: str = "EMA5M_PREV_SESSION"
    ma_mode: str = "EMA200_5M"  # ORB gap setup: EMA200_5M | SMA200_DAILY | EMA200_DAILY
    # IRF
    irf_support_def: str = "SWING_K1"
    irf_resistance_def: str = "FIRST_PUSH_TOP"
    m1_max_candles_after_breakout: int = 1
    m1_close_below_irl_counts_as_inside: bool = False
    m2_extension_definition: str = "E1"
    m2_red_may_be_extension_candle: bool = False
    m2b_push_must_precede_red_candle: bool = False  # IRF p.9 steps 3-5: may the push above and the closing red candle be one candle?
    m2a_break_may_be_red_candle: bool = False
    m2_expiry_candles: int | None = None
    m3_compression_def: str = "C1"
    m3_compression_n: int = 2
    m3_compression_size_frac: float = 0.5
    m3_wick_share_band: str = "BAND_60_70"
    stop_distance_measure: str = "GREEN_HIGH"
    stop_boundary_inclusive_35: bool = True  # d == 35 -> 35
    # gap / zones
    gap_min_points: float = 0.0
    gap_max_points: float | None = None
    zone_lower_boundary: str = "ZONE_FULL"
    zone_tie_break: str = "FIRST"  # which candle when several share the day's high/low
    zone_proximity_points: float = 5.0
    pdr_green_may_be_interaction_candle: bool = False
    pdr_reversal_filter: str = "OFF"  # OFF | DEPTH_25PCT
    pds_small_support_def: str = "SWING_K1_NEAR_ZONE"
    pds_m3_break_basis: str = "CLOSE"
    pds_m3_standalone: bool = False
    # RF
    rf_return_inside_def: str = "R1"
    rf_direction: str = "LONG"
    # ORB
    ma_near_band_points: float = 15.0
    ma_close_margin_points: float = 5.0
    entry_reference_price: str = "SIGNAL_CANDLE_CLOSE"
    orb_pin_bar_in_methods_1_2: bool = True  # ORB pp.9-10: the conditional pin bar applies 'across all three setups'
    require_open_clear_of_zone: bool = True  # PROPOSED (PDR-011 / PDS-006)
    max_signals_per_session: int = 1  # PROPOSED (PDR-012 / PDS-007 / RF-014)
    # data hygiene
    allow_unverified_prev_session: bool = False
    signal_window_end: str | None = None  # "HH:MM" latest bar_end allowed; None = no cutoff (MISSING in docs)

    def __post_init__(self) -> None:
        for fam, val in (("strong_candle", self.strong_candle), ("pin_bar", self.pin_bar),
                         ("rejection_wick", self.rejection_wick)):
            table = {"strong_candle": STRONG_CANDLE, "pin_bar": PIN_BAR, "rejection_wick": REJECTION_WICK}[fam]
            if val not in table:
                raise ConfigError(f"{fam}={val!r} not in {sorted(table)}")
        if self.m3_wick_share_band not in M3_WICK_SHARE_BAND:
            raise ConfigError(f"m3_wick_share_band={self.m3_wick_share_band!r}")
        if self.trend_mode not in CANDIDATE_NOTES["trend_mode"]:
            raise ConfigError(f"trend_mode={self.trend_mode!r}")
        if self.ma_mode not in ("EMA200_5M", "SMA200_DAILY", "EMA200_DAILY"):
            raise ConfigError(f"ma_mode={self.ma_mode!r}")
        if self.m1_max_candles_after_breakout < 1:
            raise ConfigError("m1_max_candles_after_breakout must be >= 1")
        if self.rf_direction not in ("LONG",):
            raise ConfigError("rf_direction: only LONG is implemented (direction is implied, RF-012)")
        # Exclusivity guarantee for PDS M1 (good body) vs M2 (pin bar): a candle cannot hold
        # body_ratio >= a and upper_wick_ratio >= b when a + b > 1.
        a = STRONG_CANDLE[self.strong_candle]["body_ratio_min"]
        b = PIN_BAR[self.pin_bar]["wick_ratio_min"]
        if a + b <= 1.0:
            raise ConfigError(f"strong_candle/pin_bar overlap possible ({a}+{b}<=1): methods would not be exclusive")

    @property
    def strong(self) -> dict[str, float]:
        return STRONG_CANDLE[self.strong_candle]

    @property
    def pin(self) -> dict[str, float]:
        return PIN_BAR[self.pin_bar]

    @property
    def reject(self) -> dict[str, float]:
        return REJECTION_WICK[self.rejection_wick]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_PROPOSALS = ProposalConfig()


@dataclass(frozen=True)
class SourceConstants:
    """Numbers that ARE stated in the documents (VERIFIED_EXPLICIT), with their sources."""

    irf_target_points: float = 60.0  # IRF p.2
    irf_stop_choices: tuple[float, float] = (35.0, 40.0)  # IRF p.2
    orb_stop_points: float = 30.0  # ORB p.1
    orb_target_points: float = 60.0  # ORB p.1
    pdr_target_points: float = 70.0  # PDR p.1
    pds_target_points: float = 70.0  # PDS p.1
    pdr_pds_stop_choices: tuple[float, float] = (35.0, 40.0)
    rf_stop_range: tuple[float, float] = (35.0, 40.0)  # RF p.2 (selection rule absent)
    rf_target_points: float | None = None  # RF p.8: OPEN -> RF_TARGET_STATUS = UNRESOLVED
    t1_points: float = 27.0  # performance report
    lots_total: int = 6
    lot_size: int = 65
    t2_choices: tuple[float, float] = (60.0, 70.0)  # report: "60 or 70, as recorded"


SOURCE = SourceConstants()
RF_TARGET_STATUS = "UNRESOLVED"
