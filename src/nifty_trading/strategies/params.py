"""Proposal parameters for rules that the source documents state only qualitatively.

EVERYTHING here is an engineering interpretation labelled ``PROPOSED_FOR_REVIEW``. None of it is
an original strategy rule, and none of it was selected by looking at historical profitability
(Phase 2 forbids that). Each family lists separated candidate interpretations. Defaults follow the source
wording where it gives any; numeric thresholds are mid-range placeholders, discussed in ``ambiguous_rules.md``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import time
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
    # Phase 2.2 owner recommendation: rejection wick >= 2x the body AND the close inside the favourable 30% of the range.
    "OWNER_2X_CLOSE30": {"wick_to_body_min": 2.0, "close_fraction_max": 0.30},
}
SMALL_CANDLE_BODY_RATIO_MAX = 0.30  # Phase 2.2 owner recommendation (PROPOSED): a "small" candle has body <= 30% of its range
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
                "LOOSE": "wick>=55%, body<=40%, opp<=20%",
                "OWNER_2X_CLOSE30": "rejection wick >= 2x body and close within the favourable 30% of the range (owner recommendation)"},
    "rejection_wick": {"STRICT": "wick>=25% of range", "MODERATE": "wick>=33%", "LOOSE": "wick>=40%"},
    "trend_mode": {
        "EMA5M_BASIC": "close of the first 5m candle vs EMA(200) of completed 5m closes (the 'basic filter' only)",
        "EMA5M_PREV_SESSION": "BASIC + previous session's last 5m close already on the trend side of its EMA (encodes RF p.5 invalid example)",
        "EMA5M_PREV_3_SESSIONS": "BASIC + each of the previous 3 sessions closed on the trend side of its EMA",
        "SMA200_DAILY": "first-candle close vs SMA(200) of daily official closes up to the previous session (needs 200 prior daily bars)",
        "EMA200_DAILY": "as SMA200_DAILY but exponential",
        "EMA_PREV_SESSION_CLOSE": "VARIANT A (owner-approved research variant): PREVIOUS-session only - its last 5m close vs its own EMA(200); no swing structure",
        "STRUCTURE_EMA_SWING2": "VARIANT B (owner-approved research variant): PREVIOUS-session only: last close vs its EMA(200) AND the last two confirmed swing highs AND the last two swing lows rising (up) / falling (down); swing = strictly beyond 2 candles each side",
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
                           "C2": "C1 and every one of them has range <= 50% of the initial-range height",
                           "C3": "C1 and every one of them is a small candle (body <= 30% of its range)"},
    "m3_wick_share_band": {"BAND_60_70": "0.60 <= share <= 0.70 (literal)", "MIN_60": "share >= 0.60",
                           "BAND_55_75": "0.55 <= share <= 0.75"},
    "stop_distance_measure": {
        "GREEN_HIGH": "distance = high of the most recent green candle - entry (short)",
        "GREEN_CLOSE": "distance = close of the most recent green candle - entry (short)",
        "GREEN_SETUP_HIGH": "distance = highest high among green candles since the setup began - entry",
    },
    "pdr_open_vs_zone": {"ABOVE_ZONE": "open > zone high (the guide's text; default)", "NOT_BELOW_ZONE": "open >= zone low (price at/above the zone, so it can act as support)",
                         "ANY": "no condition on the open beyond the gap-up (55% of its signals open BELOW the zone: not recommended)"},
    "pds_open_vs_zone": {"BELOW_ZONE": "open < zone low (the guide's text, p.3; default)", "NOT_ABOVE_ZONE": "open <= zone high", "ANY": "no condition beyond the gap-down"},
    "prev_close_source": {"OFFICIAL_DAILY": "previous close = the vendor daily close = the published NSE closing value (verified on 9 of 9 external closes)",
                          "LAST_PRINT_1530": "previous close = the last 1-minute print at 15:30 (equal to the official close only from 2026-08-03)"},
    "prev_day_level_window": {"ALL_CANDLES": "previous-day high/low/zone use every complete 5m candle, as a chart shows them (default)",
                              "CONTINUOUS_ONLY": "on closing-auction days (>= 2026-08-03) use only candles that ended by 15:15"},
    "zone_lower_boundary": {"ZONE_FULL": "PDR zone = [body bottom, wick top] (mirrors PDS text 'body and wick')",
                            "ZONE_WICK": "PDR zone = [body top, wick top] (wick only)"},
    "zone_proximity_points": {"0": "actual zone intersection (strict research version)", "5": "within 5 index points (near-touch proposal)",
                              "10": "within 10 index points"},
    "pdr_zone_method": {"A_HIGHEST_HIGH": "DIAGNOSTIC REFERENCE ONLY (Phase 2.3): the previous session's absolute highest-high candle; signals built on it are marked DIAGNOSTIC_ONLY_NOT_TRADABLE",
                        "B_SWING_HIGH_REVERSAL": "owner-approved research candidate 1 (confirmed reversal swing high): the LATEST confirmed swing high (swing_k each side) with a red candle at/after the peak; no such swing = no PDR setup",
                        "C_REPEATED_TOUCHES": "owner-approved research candidate 2 (repeated resistance shelf): the highest cluster of >=2 confirmed swing highs within the tolerance; the zone spans the cluster; no cluster = no PDR setup"},
    "pds_zone_method": {"A_LOWEST_LOW": "the previous session's absolute lowest-low candle",
                        "B_SWING_LOW_REVERSAL": "the LATEST confirmed swing low with a green candle at/after the trough (bullish reversal)",
                        "C_REPEATED_TOUCHES": "the lowest cluster of >=2 confirmed swing lows within the tolerance; zone spans the cluster"},
    "pds_zone_upper_boundary": {"ZONE_FULL": "PDS zone = [wick tip, body TOP]", "ZONE_WICK": "PDS zone = [wick tip, body BOTTOM] (wick only)"},
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
    strong_candle: str = "MODERATE"  # body >= 60%, opposite wick <= 20% (= the owner's Phase 2.2 recommendation)
    pin_bar: str = "OWNER_2X_CLOSE30"
    rejection_wick: str = "MODERATE"
    trend_mode: str = "STRUCTURE_EMA_SWING2"  # Phase 2.2 owner recommendation (PROPOSED). Caveat: ORB p.7's own uptrend chart has falling recent swing highs
    ma_mode: str = "EMA200_5M"  # ORB gap setup: EMA200_5M | SMA200_DAILY | EMA200_DAILY
    swing_k: int = 2  # candles on each side of a swing point (PROPOSED, TREND-SWING-001)
    small_candle_body_ratio_max: float = SMALL_CANDLE_BODY_RATIO_MAX
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
    zone_lower_boundary: str = "ZONE_WICK"  # Phase 2.2: PDR charts 2 and 4 (and, within 5 points, chart 1) draw [body TOP, wick tip]; ZONE_FULL is the candidate
    prev_day_level_window: str = "ALL_CANDLES"  # ALL_CANDLES | CONTINUOUS_ONLY (excludes the closing-auction candles on/after 2026-08-03)
    pdr_zone_method: str = "B_SWING_HIGH_REVERSAL"  # Phase 2.3: A_HIGHEST_HIGH is a DIAGNOSTIC reference only and never yields a tradable signal
    pds_zone_method: str = "A_LOWEST_LOW"
    pds_zone_upper_boundary: str = "ZONE_FULL"
    zone_cluster_tolerance_points: float = 5.0  # repeated-touch clustering (method C), PROPOSED
    zone_cluster_min_touches: int = 2
    zone_tie_break: str = "FIRST"  # which candle when several share the day's high/low
    zone_proximity_points: float = 0.0  # Phase 2.2: strict zone intersection is the initial research version; 5 is the labelled near-touch variant
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
    # PDR: the guide's TEXT says the market 'pulls back into the marked zone' (p.1) and 'come back toward the marked zone' (p.2): the open is
    # above the zone. Example 3 (2025-10-07) does NOT settle it: the zone the author DREW on that chart is only ~4-5 points tall (about 25,080.5-25,084.5; the open is ~3 points above it), whereas the engine's
    # zone (highest-high candle, 14:50 spike) is 38.6 points tall, so 'the open is inside the zone' was an artefact of the engine's zone.
    # ABOVE_ZONE (open > zone high: the text; default) | NOT_BELOW_ZONE (open >= zone low) | ANY (WARNING: 55% of its signals have the open BELOW the zone,
    # i.e. the zone is overhead resistance, not support).
    pdr_open_vs_zone: str = "ABOVE_ZONE"
    # PDS: the guide's text says price 'is trading below the previous support zone' after the open (p.3); no contrary example.
    # BELOW_ZONE (open < zone low: the text) | NOT_ABOVE_ZONE (open <= zone high) | ANY
    pds_open_vs_zone: str = "BELOW_ZONE"
    prev_close_source: str = "OFFICIAL_DAILY"  # OFFICIAL_DAILY (vendor daily close = published NSE close) | LAST_PRINT_1530
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
        if self.pdr_open_vs_zone not in ("ABOVE_ZONE", "NOT_BELOW_ZONE", "ANY"):
            raise ConfigError(f"pdr_open_vs_zone={self.pdr_open_vs_zone!r}")
        if self.pds_open_vs_zone not in ("BELOW_ZONE", "NOT_ABOVE_ZONE", "ANY"):
            raise ConfigError(f"pds_open_vs_zone={self.pds_open_vs_zone!r}")
        if self.prev_close_source not in ("OFFICIAL_DAILY", "LAST_PRINT_1530"):
            raise ConfigError(f"prev_close_source={self.prev_close_source!r}")
        if self.prev_day_level_window not in ("ALL_CANDLES", "CONTINUOUS_ONLY"):
            raise ConfigError(f"prev_day_level_window={self.prev_day_level_window!r}")
        if self.m3_wick_share_band not in M3_WICK_SHARE_BAND:
            raise ConfigError(f"m3_wick_share_band={self.m3_wick_share_band!r}")
        if self.trend_mode not in CANDIDATE_NOTES["trend_mode"]:
            raise ConfigError(f"trend_mode={self.trend_mode!r}")
        if self.ma_mode not in ("EMA200_5M", "SMA200_DAILY", "EMA200_DAILY"):
            raise ConfigError(f"ma_mode={self.ma_mode!r}")
        for fam, val in (("pdr_zone_method", self.pdr_zone_method), ("pds_zone_method", self.pds_zone_method),
                         ("pds_zone_upper_boundary", self.pds_zone_upper_boundary)):
            if val not in CANDIDATE_NOTES[fam]:
                raise ConfigError(f"{fam}={val!r}")
        if self.zone_proximity_points < 0 or self.zone_cluster_tolerance_points < 0 or self.zone_cluster_min_touches < 2:
            raise ConfigError("zone proximity/tolerance must be >= 0 and zone_cluster_min_touches >= 2")
        if self.swing_k < 1:
            raise ConfigError("swing_k must be >= 1")
        if self.m3_compression_def not in CANDIDATE_NOTES["m3_compression_def"]:
            raise ConfigError(f"m3_compression_def={self.m3_compression_def!r}")
        if self.m1_max_candles_after_breakout < 1:
            raise ConfigError("m1_max_candles_after_breakout must be >= 1")
        if self.rf_direction not in ("LONG",):
            raise ConfigError("rf_direction: only LONG is implemented (direction is implied, RF-012)")
        # Exclusivity guarantee for PDS M1 (good body) vs M2 (pin bar): a candle cannot hold
        # body_ratio >= a and upper_wick_ratio >= b when a + b > 1.
        a = STRONG_CANDLE[self.strong_candle]["body_ratio_min"]
        pb = PIN_BAR[self.pin_bar]
        if "wick_ratio_min" in pb:
            b = pb["wick_ratio_min"]
            if a + b <= 1.0:
                raise ConfigError(f"strong_candle/pin_bar overlap possible ({a}+{b}<=1): methods would not be exclusive")
        elif a + a * pb["wick_to_body_min"] <= 1.0:  # wick >= k*body >= k*a*range must not fit beside a body of a*range
            raise ConfigError("strong_candle/pin_bar overlap possible: methods would not be exclusive")

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
# Phase 2.2: the RF guide still says the target is OPEN (RF p.8). The owner asked for a CONFIGURABLE research value of 60 (the report's
# arithmetic and the p.9 chart box 60.80 point to it). It is a proposal: never VERIFIED_EXPLICIT, never USER_APPROVED.
RF_TARGET_STATUS = "PROPOSED_FOR_REVIEW"
RF_TARGET_RESEARCH_POINTS = 60.0


# --- trade parameters: stops and targets ------------------------------------------------------------------------
VERIFIED_EXPLICIT = "VERIFIED_EXPLICIT"
USER_APPROVED = "USER_APPROVED"
CONFLICTING = "CONFLICTING"  # the guide states the value but the performance report's recorded winners disagree
STRATEGIES = ("IRF", "ORB", "PDR", "PDS", "RF")

#: User-approved provisional RESEARCH baseline (Phase 2.2). Not the historical manual trader's stop-selection rule, which the
#: sources still do not define for IRF/PDR/PDS/RF (they say "35 or 40"). ORB keeps its documented 30 (ORB p.1, VERIFIED_EXPLICIT).
STOP_BASELINE: dict[str, float] = {"IRF": 35.0, "ORB": 30.0, "PDR": 35.0, "PDS": 35.0, "RF": 35.0}
#: Future sensitivity test (Phase 3 compares them; Phase 2.2 does NOT). ORB is deliberately unchanged.
STOP_ALTERNATE: dict[str, float] = {"IRF": 40.0, "ORB": 30.0, "PDR": 40.0, "PDS": 40.0, "RF": 40.0}
STOP_STATUS: dict[str, str] = {"IRF": USER_APPROVED, "ORB": VERIFIED_EXPLICIT, "PDR": USER_APPROVED, "PDS": USER_APPROVED, "RF": USER_APPROVED}
#: Target 2 per strategy, with the status of the value. PDR/PDS: the guides say 70 while the performance report records winners at 60
#: (PDR 1 of 6, PDS 2 of 3): the conflict is preserved in ``T2_CONFLICTS`` and never silently overwritten.
T2_TABLE: dict[str, tuple[float, str]] = {
    "IRF": (60.0, VERIFIED_EXPLICIT), "ORB": (60.0, VERIFIED_EXPLICIT), "PDR": (70.0, CONFLICTING),
    "PDS": (70.0, CONFLICTING), "RF": (RF_TARGET_RESEARCH_POINTS, PROPOSAL_LABEL),
}
T2_CONFLICTS: dict[str, str] = {
    "PDR": "PDR guide p.1 says 70; the performance report's arithmetic records 1 of its 6 PDR winners at 60",
    "PDS": "PDS guide p.1 says 70; the performance report's arithmetic records 2 of its 3 PDS winners at 60",
}
STOP_VARIANTS = ("BASELINE", "ALTERNATE_40", "SOURCE_35_40_BY_DISTANCE")


@dataclass(frozen=True)
class TradeConfig:
    """Stop / target configuration for the exit policy and for the ``execution_config`` carried by every signal.

    ``stop_variant``: BASELINE (35; ORB 30), ALTERNATE_40 (40; ORB 30) or SOURCE_35_40_BY_DISTANCE (the Phase 2 research
    reading: 35 or 40 by the distance to the most recent opposite candle; ORB 30). Stop distances live ONLY here.
    """

    stop_variant: str = "BASELINE"
    t1_points: float = 27.0
    rf_t2_points: float | None = RF_TARGET_RESEARCH_POINTS  # None => RF target unresolved (exits NOT_EVALUABLE)
    # Phase 2.3 (USER_APPROVED): 6 lots in two equal legs of 3; the historical report used 65 units per lot (390 total, 195 per leg).
    total_lots: int = 6
    leg1_lots: int = 3
    lot_size: int = 65  # configurable multiplier; index points are the research unit, this only scales synthetic P&L
    # Phase 2.3 (USER_APPROVED): after Target 1 the remaining legs are protected by a stop 6 index points AGAINST the entry. No trailing.
    post_t1_stop_mode: str = "BUFFER"  # "ENTRY_BREAKEVEN" is the SUPERSEDED performance-report rule, kept only for reconciliation
    post_t1_buffer_points: float = 6.0
    # Phase 3 (USER_APPROVED: positions are closed before 15:15; the price convention is a PROPOSAL): still open at this IST minute -> closed at that bar's open.
    forced_exit_time: time | None = None  # None = Phase 2.3 behaviour (a position open at the end of the fillable bars is left unresolved)

    def __post_init__(self) -> None:
        if self.stop_variant not in STOP_VARIANTS:
            raise ConfigError(f"stop_variant={self.stop_variant!r} not in {STOP_VARIANTS}")
        if self.total_lots < 2 or self.total_lots % 2 or self.leg1_lots * 2 != self.total_lots:
            raise ConfigError("the position must be split into two EQUAL legs (total_lots even, leg1_lots = total_lots / 2)")
        if self.lot_size < 1:
            raise ConfigError("lot_size must be >= 1")
        if self.post_t1_stop_mode not in ("BUFFER", "ENTRY_BREAKEVEN"):
            raise ConfigError(f"post_t1_stop_mode={self.post_t1_stop_mode!r}")
        if self.post_t1_buffer_points < 0:
            raise ConfigError("post_t1_buffer_points must be >= 0")
        if self.post_t1_buffer_points > min(STOP_BASELINE.values()):
            raise ConfigError("the post-T1 stop may never be wider than the smallest initial stop (no widening)")

    def stop_points(self, strategy: str) -> float | None:
        """The configured stop distance; None when the variant needs a per-trade measurement."""
        if self.stop_variant == "BASELINE":
            return STOP_BASELINE[strategy]
        if self.stop_variant == "ALTERNATE_40":
            return STOP_ALTERNATE[strategy]
        return STOP_BASELINE["ORB"] if strategy == "ORB" else None

    def stop_status(self, strategy: str) -> str:
        if strategy == "ORB":
            return VERIFIED_EXPLICIT
        return USER_APPROVED if self.stop_variant == "BASELINE" else PROPOSAL_LABEL

    def t2_points(self, strategy: str) -> float | None:
        if strategy == "RF":
            return self.rf_t2_points
        return T2_TABLE[strategy][0]

    def t2_status(self, strategy: str) -> str:
        return T2_TABLE[strategy][1] if (strategy != "RF" or self.rf_t2_points is not None) else "UNRESOLVED"


DEFAULT_TRADE = TradeConfig()
