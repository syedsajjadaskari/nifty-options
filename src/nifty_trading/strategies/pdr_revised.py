"""PDR - Previous Day Resistance, REVISED entry rules (Phase 3.4). Source: ``PDR_Strategy_Guide.pdf`` plus the strategy author's later clarifications.

The legacy engine (``pdr.py``, Phase 2.3 / Phase 3.0 research candidates) is NOT modified: it keeps producing the historical signals. This engine is a separate, versioned
implementation so that every earlier result stays reproducible. It changes entry QUALIFICATION and ZONE SELECTION only; stops, targets, sizing, cutoff and the portfolio
controller are untouched (they live in ``core.exit_policy`` / ``strategies.trading_day``).

Author clarifications (AUTHOR_APPROVED, quoted from the strategy author):
  "The high should be considered, day's high should be considered and a zone should be drawn. If there are multiple highs, then a zone which connects all should be considered."
  "One good green body candle or lower price rejection candle or hammer candle is required for entry."
  "The candle should close above the zone."

Everything the author did not define (how many highs, tolerance, separation, width, spike handling, lower boundary, the numeric shape of the three candle patterns, candle colour of
the rejection/hammer, how long the setup stays armed) is a labelled research parameter (PROPOSED_FOR_REVIEW) recorded on every signal; no candidate is source-verified.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
from typing import Any

from nifty_trading.data.sessions import SessionContext
from nifty_trading.strategies.base import (
    Direction,
    SetupFSM,
    SignalEngine,
    SignalRecord,
    SignalStatus,
    State,
    VerificationStatus,
)
from nifty_trading.strategies.definitions import (
    EPS,
    Candle,
    gap_info,
    lower_wick,
    pdr_zone,
    prev_candles,
    to_candles,
    upper_wick,
)
from nifty_trading.strategies.params import ProposalConfig

AA, PR, UA, PRESERVED = "AUTHOR_APPROVED", "PROPOSED_FOR_REVIEW", "USER_APPROVED", "PRESERVED_FROM_PHASE2"
OI = "OWNER_INTERPRETATION"  # the brief's reading of the author's words: not a separate author sentence, still unconfirmed by the author

CANDIDATES = ("A_DAY_HIGH_ANCHORED", "B_MULTIPLE_HIGH_CLUSTER")
PROFILES = {
    # RESEARCH_DEFAULT reuses the documented Phase 2.2 definitions (strong candle 60% / 20%, pin 2x wick and close in the favourable 30%) and adds a hammer shape; ALL are PROPOSED_FOR_REVIEW.
    "RESEARCH_DEFAULT": {"green_body_min": 0.60, "green_upper_wick_max": 0.20, "reject_wick_to_body_min": 2.0, "reject_close_fraction_max": 0.30,
                         "hammer_wick_to_body_min": 2.0, "hammer_upper_wick_max": 0.10, "hammer_body_position_min": 0.60},
    # EXAMPLE_LENIENT is a SENSITIVITY profile whose numbers were read off the four dated entry candles of the PDR guide (Examples 1-4); it is diagnostic only, never the active default.
    "EXAMPLE_LENIENT": {"green_body_min": 0.40, "green_upper_wick_max": 0.25, "reject_wick_to_body_min": 1.5, "reject_close_fraction_max": 0.40,
                        "hammer_wick_to_body_min": 1.5, "hammer_upper_wick_max": 0.15, "hammer_body_position_min": 0.55},
}


@dataclass(frozen=True)
class PDRRevisionConfig:
    zone_candidate: str = "A_DAY_HIGH_ANCHORED"
    # Candidate B research parameters (the author gave none of these numbers)
    b_local_high_k: int = 1  # a local high is not lower than the k candles on each side
    b_min_touches: int = 2  # distinct touch groups needed to call it 'multiple highs'
    b_tolerance_points: float = 5.0  # a local high within this distance of the day's high joins the cluster (the Phase 2.3 shelf tolerance)
    b_min_separation_candles: int = 2  # members closer than this (in candles) count as ONE touch (one push)
    b_lower_bound: str = "MIN_MEMBER_BODY_TOP"  # | DAY_HIGH_CANDLE_BODY_TOP
    b_spike_policy: str = "ALWAYS_INCLUDE_DAY_HIGH"  # | EXCLUDE_ISOLATED_SPIKE_ABOVE_SHELF (diagnostic only)
    # confirmation patterns
    pattern_profile: str = "RESEARCH_DEFAULT"
    patterns_enabled: tuple[str, ...] = ("GOOD_GREEN_BODY", "LOWER_PRICE_REJECTION", "HAMMER")
    # sequence (preserved from the legacy engine unless an author clarification contradicts it)
    proximity_points: float = 0.0
    open_vs_zone: str = "ABOVE_ZONE"
    confirmation_may_be_interaction_candle: bool = False
    wait_policy: str = "WAIT_FOR_QUALIFYING_CANDLE"  # the setup stays armed after the test until a candle qualifies or the session ends

    def __post_init__(self) -> None:
        if self.zone_candidate not in CANDIDATES:
            raise ValueError(self.zone_candidate)
        if self.pattern_profile not in PROFILES:
            raise ValueError(self.pattern_profile)
        if self.b_lower_bound not in ("MIN_MEMBER_BODY_TOP", "DAY_HIGH_CANDLE_BODY_TOP"):
            raise ValueError(self.b_lower_bound)
        if self.b_spike_policy not in ("ALWAYS_INCLUDE_DAY_HIGH", "EXCLUDE_ISOLATED_SPIKE_ABOVE_SHELF"):
            raise ValueError(self.b_spike_policy)
        if self.open_vs_zone not in ("ABOVE_ZONE", "ANY"):
            raise ValueError(self.open_vs_zone)

    @property
    def thresholds(self) -> dict[str, float]:
        return PROFILES[self.pattern_profile]

    def config_id(self, proposals: ProposalConfig | None = None) -> str:
        blob = json.dumps({"c": asdict(self), "p": (proposals.to_dict() if proposals else None)}, sort_keys=True, default=str)
        return f"PDRREV-{self.zone_candidate[0]}-{self.pattern_profile}-{hashlib.sha256(blob.encode()).hexdigest()[:8]}"


# ---------------------------------------------------------------------------------------------------- the rules of this revision
def _rule(rule_id, status, text, source, **kw) -> dict[str, Any]:
    return {"rule_id": rule_id, "status": status, "text": text, "source": source, **kw}


AUTHOR = "strategy author's clarification (Phase 3.4 brief)"
PDR_REVISION_RULES: list[dict[str, Any]] = [
    _rule("PDR-A01", AA, "The previous trading day's high must be considered when identifying the resistance area (author: \"day's high should be considered and a zone should be drawn\").", AUTHOR,
          supersedes=["PDR-ZONE-002 candidate B (reversal swing high)"], implemented_by="build_zone_a / build_zone_b (ceiling = the previous session's maximum high)"),
    _rule("PDR-A01a", OI, "Reading of A01: the zone ceiling IS the previous session's highest high, and an unrelated lower swing high may not replace it.", "Phase 3.4 brief interpretation of the author's words", implemented_by="build_zone_a / build_zone_b"),
    _rule("PDR-A02", AA, "If the previous session contains multiple highs, a zone connecting all of them is considered (principle only; the author gave no numbers).", AUTHOR, implemented_by="build_zone_b"),
    _rule("PDR-A02a", PR, "How many highs make 'multiple highs': distinct touch groups >= b_min_touches (default 2).", "research parameter", parameter="b_min_touches"),
    _rule("PDR-A02b", PR, "Maximum difference between highs: a local high within b_tolerance_points (default 5.0) of the day's high joins the cluster.", "research parameter", parameter="b_tolerance_points"),
    _rule("PDR-A02c", PR, "Minimum candle separation: members closer than b_min_separation_candles (default 2) count as one touch.", "research parameter", parameter="b_min_separation_candles"),
    _rule("PDR-A02d", PR, "Maximum cluster width: NOT limited; the width is recorded and the day-high spike is never discarded.", "research parameter (none)", parameter="(none)"),
    _rule("PDR-A02e", PR, "Isolated spikes: the day's high is always part of the zone (b_spike_policy ALWAYS_INCLUDE_DAY_HIGH); excluding a spike above a shelf is a diagnostic option only.", "research parameter", parameter="b_spike_policy"),
    _rule("PDR-A02f", PR, "Candidate B lower boundary: the lowest body top among the cluster members (default) or the body top of the day-high candle (the 'wick-only' convention of the PDR charts).", "research parameter", parameter="b_lower_bound"),
    _rule("PDR-A02g", PR, "Candidate A lower boundary: the body top of the day-high candle (zone = body top to wick high, the guide's 'candle body to upper wick'). The author gave no number.", "research parameter; PDR guide p.2", parameter="(fixed in build_zone_a)"),
    _rule("PDR-A02h", PR, "What counts as a 'high' of the cluster: a local high not lower than its b_local_high_k (default 1) neighbours on each side (non-strict).", "research parameter", parameter="b_local_high_k"),
    _rule("PDR-A02i", PR, "Equal day highs: the first candle that made the session's highest high anchors the zone.", "research parameter", parameter="(fixed in day_high_index)"),
    _rule("PDR-A03", PRESERVED, "The next session must open gap up and the price must return to / interact with the selected zone (any candle whose range overlaps the zone +/- proximity); the confirmation candle comes after the interaction candle.",
          "PDR guide pp.1-3; legacy PDR-004/005/006", parameter="proximity_points / open_vs_zone / confirmation_may_be_interaction_candle"),
    _rule("PDR-A03a", PR, "Open must lie above the zone ceiling (legacy PDR-011, a proposal) - preserved, not an author rule. With the ceiling at the previous-day high this requires the gap to clear the whole previous range; the open_vs_zone=ANY sensitivity is reported beside it.", "legacy PDR-011", parameter="open_vs_zone"),
    _rule("PDR-A03b", PR, "Gap up means the open is above the official previous close by more than gap_min_points (0).", "legacy gap definition", parameter="gap_min_points (0)"),
    _rule("PDR-A04", AA, "A LONG entry needs one good green body candle OR a lower price rejection candle OR a hammer candle (author: \"One good green body candle or lower price rejection candle or hammer candle is required for entry\").", AUTHOR, implemented_by="classify_confirmation"),
    _rule("PDR-A04z", OI, "Reading of A04: OR logic; every pattern that passes is recorded; one signal per candle.", "Phase 3.4 brief interpretation of the author's words", implemented_by="classify_confirmation / _scan"),
    _rule("PDR-A04a", PR, "Good green body: bullish close, body >= green_body_min of the range, upper wick <= green_upper_wick_max of the range (thresholds from the Phase 2.2 owner recommendation, not from the author).", "research parameter", parameter="green_body_min / green_upper_wick_max"),
    _rule("PDR-A04b", PR, "Lower-price rejection: lower wick >= reject_wick_to_body_min x body, close within the top reject_close_fraction_max of the range, and the low reached the zone (low <= zone ceiling + proximity). Candle colour is NOT required (author silent).", "research parameter", parameter="reject_*"),
    _rule("PDR-A04c", PR, "Hammer: lower wick >= hammer_wick_to_body_min x body, upper wick <= hammer_upper_wick_max of the range, body in the upper part of the range (body bottom at >= hammer_body_position_min of the range). Candle colour is NOT required (author silent).", "research parameter", parameter="hammer_*"),
    _rule("PDR-A05", AA, "The confirmation candle should close above the zone (author: \"The candle should close above the zone\").", AUTHOR, implemented_by="classify_confirmation"),
    _rule("PDR-A05a", OI, "Reading of A05: close > the zone CEILING, strictly. Equal, inside the zone or below the floor is invalid. A lower wick may penetrate the zone; the whole candle need not stay above it.", "Phase 3.4 brief interpretation of the author's words", implemented_by="classify_confirmation (close > zone_ceiling)"),
    _rule("PDR-A05b", PR, "Numerical tolerance of the threshold comparisons: EPS = 1e-9 on >=/<= boundaries (never applied to the strict close > ceiling).", "implementation detail", parameter="EPS"),
    _rule("PDR-A06", UA, "Entry only after the confirmation candle has completed; fill = open of the 1-minute bar that starts when it ends (existing EXE-FILL-001 convention).", "existing execution convention", implemented_by="signal timestamp = candle end"),
    _rule("PDR-A07", PR, "The test stays armed until a candle qualifies or the session ends (wait_policy); the confirmation may not be the interaction candle (preserved legacy rule).", "research parameter", parameter="wait_policy"),
]
RULE_STATUS = {r["rule_id"]: r["status"] for r in PDR_REVISION_RULES}


# ---------------------------------------------------------------------------------------------------- candle geometry and patterns
def _ratios(c: Candle) -> dict[str, float | None]:
    rg = c.h - c.l
    b = abs(c.c - c.o)
    uw, lw = upper_wick(c), lower_wick(c)
    if rg <= 0.0:
        return {"range": rg, "body": b, "body_pct": None, "upper_wick": uw, "upper_wick_pct": None, "lower_wick": lw, "lower_wick_pct": None, "body_position": None, "close_from_high_pct": None}
    return {"range": rg, "body": b, "body_pct": b / rg, "upper_wick": uw, "upper_wick_pct": uw / rg, "lower_wick": lw, "lower_wick_pct": lw / rg,
            "body_position": (min(c.o, c.c) - c.l) / rg, "close_from_high_pct": (c.h - c.c) / rg}


def good_green_body(c: Candle, th: dict[str, float]) -> dict[str, Any]:
    r = _ratios(c)
    if r["body_pct"] is None:
        return {"passed": False, "reason": "zero-range candle", **r}
    ok_colour, ok_body, ok_wick = c.c > c.o, r["body_pct"] >= th["green_body_min"] - EPS, r["upper_wick_pct"] <= th["green_upper_wick_max"] + EPS
    return {"passed": ok_colour and ok_body and ok_wick, "bullish": ok_colour, "body_ok": ok_body, "upper_wick_ok": ok_wick, **r}


def lower_price_rejection(c: Candle, zone_ceiling: float, proximity: float, th: dict[str, float]) -> dict[str, Any]:
    r = _ratios(c)
    if r["body_pct"] is None:
        return {"passed": False, "reason": "zero-range candle", **r}
    wick_ok = r["lower_wick"] > EPS and r["lower_wick"] >= th["reject_wick_to_body_min"] * r["body"] - EPS
    close_ok = r["close_from_high_pct"] <= th["reject_close_fraction_max"] + EPS
    reached = c.l <= zone_ceiling + proximity
    return {"passed": bool(wick_ok and close_ok and reached), "wick_to_body": None if r["body"] <= EPS else r["lower_wick"] / r["body"], "wick_ok": wick_ok, "close_location_ok": close_ok, "low_reached_zone": reached,
            "bullish": c.c > c.o, "colour_required": False, **r}


def hammer(c: Candle, th: dict[str, float]) -> dict[str, Any]:
    """A bullish hammer: small real body at the TOP of the range and a long LOWER wick (the mirror of a bearish upper-wick pin bar, not a reuse of it)."""
    r = _ratios(c)
    if r["body_pct"] is None:
        return {"passed": False, "reason": "zero-range candle", **r}
    wick_ok = r["lower_wick"] > EPS and r["lower_wick"] >= th["hammer_wick_to_body_min"] * r["body"] - EPS
    upper_ok = r["upper_wick_pct"] <= th["hammer_upper_wick_max"] + EPS
    pos_ok = r["body_position"] >= th["hammer_body_position_min"] - EPS
    return {"passed": bool(wick_ok and upper_ok and pos_ok), "wick_to_body": None if r["body"] <= EPS else r["lower_wick"] / r["body"], "wick_ok": wick_ok, "upper_wick_ok": upper_ok, "body_position_ok": pos_ok,
            "bullish": c.c > c.o, "colour_required": False, **r}


def classify_confirmation(c: Candle, zone_floor: float, zone_ceiling: float, cfg: PDRRevisionConfig) -> dict[str, Any]:
    """All three patterns plus the mandatory close rule. ``qualifies`` = (at least one pattern) AND close > ceiling; no pattern may override the close rule."""
    th = cfg.thresholds
    res = {"GOOD_GREEN_BODY": good_green_body(c, th), "LOWER_PRICE_REJECTION": lower_price_rejection(c, zone_ceiling, cfg.proximity_points, th), "HAMMER": hammer(c, th)}
    passed = [k for k in cfg.patterns_enabled if res[k]["passed"]]
    close_above = c.c > zone_ceiling  # strictly above: a close equal to the ceiling is not enough
    return {"patterns": res, "patterns_passed": passed, "close_above_ceiling": close_above, "close_minus_ceiling": c.c - zone_ceiling, "close_minus_floor": c.c - zone_floor,
            "qualifies": bool(passed) and close_above}


# ---------------------------------------------------------------------------------------------------- zones
@dataclass
class RevisedZone:
    candidate: str
    kind: str  # DAY_HIGH_CANDLE | ISOLATED_DAY_HIGH | MULTIPLE_HIGH_CLUSTER
    floor: float
    ceiling: float
    previous_day_high: float
    members: tuple[int, ...]
    source_starts: tuple[datetime, ...]
    touches: int
    notes: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)

    @property
    def width(self) -> float:
        return self.ceiling - self.floor


def _body_top(c: Candle) -> float:
    return max(c.o, c.c)


def day_high_index(cs: list[Candle]) -> int:
    top = max(c.h for c in cs)
    return next(i for i, c in enumerate(cs) if c.h == top)


def build_zone_a(cs: list[Candle]) -> RevisedZone:
    """Candidate A: [body top, wick high] of the candle that made the previous session's highest high (first occurrence)."""
    j = day_high_index(cs)
    return RevisedZone("A_DAY_HIGH_ANCHORED", "DAY_HIGH_CANDLE", _body_top(cs[j]), cs[j].h, cs[j].h, (j,), (cs[j].start,), 1,
                       ["ceiling = the previous session's highest high; floor = body top of that candle (wick-only convention of the PDR charts)"])


def local_highs(cs: list[Candle], k: int) -> list[int]:
    out = []
    for j in range(len(cs)):
        if all(cs[j].h >= cs[m].h for m in range(max(0, j - k), min(len(cs), j + k + 1)) if m != j):
            out.append(j)
    return out


def _groups(idx: list[int], sep: int) -> list[list[int]]:
    g: list[list[int]] = []
    for j in sorted(idx):
        if g and j - g[-1][-1] < sep:
            g[-1].append(j)
        else:
            g.append([j])
    return g


def build_zone_b(cs: list[Candle], cfg: PDRRevisionConfig) -> RevisedZone:
    """Candidate B: connect the day's high with the local highs within ``b_tolerance_points`` of it (at least ``b_min_touches`` distinct touches), otherwise it is an isolated day high.
    The day's high is never discarded. If a shelf of repeated highs lies BELOW a distant spike, the spike policy is recorded (flag SPIKE_ABOVE_SHELF) - the discrepancy is documented."""
    dh = day_high_index(cs)
    high = cs[dh].h
    piv = local_highs(cs, cfg.b_local_high_k)
    members = sorted({j for j in piv if cs[j].h >= high - cfg.b_tolerance_points - 1e-9} | {dh})
    groups = _groups(members, cfg.b_min_separation_candles)
    flags: list[str] = []
    notes: list[str] = []
    # a shelf of repeated highs below the spike (the PDR Example 3 shape)
    below = sorted((j for j in piv if cs[j].h < high - cfg.b_tolerance_points - 1e-9), key=lambda j: cs[j].h, reverse=True)
    shelf: list[int] = []
    for j0 in below:
        shelf = [j for j in below if abs(cs[j].h - cs[j0].h) <= cfg.b_tolerance_points + 1e-9]
        if len(_groups(shelf, cfg.b_min_separation_candles)) >= cfg.b_min_touches:
            break
        shelf = []
    if shelf:
        flags.append("SPIKE_ABOVE_SHELF")
        notes.append(f"the day's high {high:.2f} is {high - max(cs[j].h for j in shelf):.2f} points above a shelf of {len(shelf)} repeated highs "
                     f"({min(cs[j].h for j in shelf):.2f}-{max(cs[j].h for j in shelf):.2f}); policy {cfg.b_spike_policy}")
    if len(groups) >= cfg.b_min_touches:
        kind = "MULTIPLE_HIGH_CLUSTER"
        tops = [_body_top(cs[j]) for j in members]
        floor = min(tops) if cfg.b_lower_bound == "MIN_MEMBER_BODY_TOP" else _body_top(cs[dh])
        notes.append(f"{len(groups)} touches within {cfg.b_tolerance_points:g} points of the day's high; ceiling {high:.2f}, floor {floor:.2f} ({cfg.b_lower_bound})")
        z = RevisedZone("B_MULTIPLE_HIGH_CLUSTER", kind, floor, high, high, tuple(members), tuple(cs[j].start for j in members), len(groups), notes, flags)
    else:
        z = RevisedZone("B_MULTIPLE_HIGH_CLUSTER", "ISOLATED_DAY_HIGH", _body_top(cs[dh]), high, high, (dh,), (cs[dh].start,), 1, notes + ["no other high within tolerance: isolated day high (identical to candidate A)"], flags)
    if cfg.b_spike_policy == "EXCLUDE_ISOLATED_SPIKE_ABOVE_SHELF" and shelf and z.kind == "ISOLATED_DAY_HIGH":
        sm = sorted(shelf)
        z = RevisedZone("B_MULTIPLE_HIGH_CLUSTER", "SHELF_EXCLUDING_SPIKE", min(_body_top(cs[j]) for j in sm), max(cs[j].h for j in sm), high, tuple(sm), tuple(cs[j].start for j in sm), len(_groups(sm, cfg.b_min_separation_candles)),
                        notes + ["DIAGNOSTIC policy: the spike is excluded; the zone ceiling is BELOW the previous-day high (contradicts PDR-A01)"], flags + ["DAY_HIGH_EXCLUDED_BY_POLICY"])
    return z


def build_zone(cs: list[Candle], cfg: PDRRevisionConfig) -> RevisedZone:
    return build_zone_a(cs) if cfg.zone_candidate == "A_DAY_HIGH_ANCHORED" else build_zone_b(cs, cfg)


# ---------------------------------------------------------------------------------------------------- the engine
class PDRRevisedStrategy(SignalEngine):
    STRATEGY = "PDR"
    METHODS = ("PDR",)
    REQUIRES_PREVIOUS_SESSION = True

    def __init__(self, name=None, params=None, proposals=None, trade=None, revision: PDRRevisionConfig | None = None):
        super().__init__(name, params, proposals, trade)
        self.rev = revision or PDRRevisionConfig()

    def _default_direction(self) -> str:
        return Direction.LONG.value

    def _record(self, ctx: SessionContext, c: Candle, status: SignalStatus, why: str | None, levels: dict[str, Any], trace: list[str], flags: list[str]) -> SignalRecord:
        """Build a SignalRecord without the legacy registry lookups (the revision rules live in PDR_REVISION_RULES); a signal is never VERIFIED here."""
        ver = VerificationStatus.RESEARCH_VARIANT if status is SignalStatus.CONFIRMED else VerificationStatus.NOT_READY
        sat = ["PDR-A01", "PDR-A02", "PDR-A03", "PDR-A04", "PDR-A05", "PDR-A06"] if status is SignalStatus.CONFIRMED else []
        rec = SignalRecord(
            strategy=self.STRATEGY, method="PDR", direction=Direction.LONG.value, signal_date=ctx.date, signal_timestamp=c.end, signal_candle_start=c.start, signal_candle_open=c.o, signal_candle_high=c.h,
            signal_candle_low=c.l, signal_candle_close=c.c, reference_levels=levels, rule_ids_satisfied=sat, rule_ids_failed=[],
            signal_status=status.value, invalidation_reason=why, verification_status=ver.value,
            rule_ids_unresolved=[r for r, st in RULE_STATUS.items() if st in (PR, OI)],
            proposals_used={"pdr_revision": asdict(self.rev), "thresholds": self.rev.thresholds}, state_trace=trace, flags=list(ctx.data_flags) + flags,
            execution_config=self.exec_config("PDR", {"VERIFIED": "VERIFIED_EXPLICIT"}.get(ver.value, ver.value) if status is SignalStatus.CONFIRMED else "NOT_A_CONFIRMED_SIGNAL", self._execution_status(c.end) if status is SignalStatus.CONFIRMED else "NOT_A_CONFIRMED_SIGNAL"))
        rec.execution_config["pdr_revision"] = {"config_id": self.rev.config_id(self.p), "zone_candidate": self.rev.zone_candidate, "pattern_profile": self.rev.pattern_profile,
                                                "rule_status": {k: v for k, v in RULE_STATUS.items()}, "version": "PDR_REVISED_PHASE34"}
        return rec

    def _scan(self, ctx: SessionContext, cs: list[Candle], gap_before: list[bool]) -> list[SignalRecord]:
        g = gap_info(ctx, self.p)
        if g.direction != "UP":
            return []  # PDR-004: no gap up, no setup (unchanged)
        prev = ctx.previous
        pcs = to_candles(prev_candles(prev, self.p))
        zone = build_zone(pcs, self.rev)
        legacy = pdr_zone(prev, replace(self.p, pdr_zone_method="B_SWING_HIGH_REVERSAL"))  # DIAGNOSTIC only: the retired reversal-swing zone is never traded
        base = {"zone_candidate": self.rev.zone_candidate, "zone_kind": zone.kind, "zone_floor": zone.floor, "zone_ceiling": zone.ceiling, "zone_low": zone.floor, "zone_high": zone.ceiling, "zone_width": zone.width,
                "zone_member_candle_starts": [f"{s:%Y-%m-%d %H:%M}" for s in zone.source_starts], "zone_touches": zone.touches, "zone_notes": zone.notes, "zone_flags": zone.flags,
                "previous_day_high": zone.previous_day_high, "legacy_reversal_zone_diagnostic": None if legacy is None else [legacy.low, legacy.high], "gap_points": g.points, "session_open": ctx.open_price,
                "prev_close": prev.close_official, "config_id": self.rev.config_id(self.p), "pattern_profile": self.rev.pattern_profile}
        flags = [f"ZONE_CANDIDATE={self.rev.zone_candidate}", f"PATTERN_PROFILE={self.rev.pattern_profile}", "PDR_REVISION_PHASE34_RESEARCH_CANDIDATE"] + [f"ZONE_{f}" for f in zone.flags]
        if self.rev.open_vs_zone == "ABOVE_ZONE" and not ctx.open_price > zone.ceiling:
            return [self._record(ctx, cs[0], SignalStatus.INVALIDATED, "GAP_UP_OPEN_NOT_ABOVE_ZONE", base, [], flags)]
        out: list[SignalRecord] = []
        fsm: SetupFSM | None = None
        j: int | None = None
        evals: list[dict[str, Any]] = []
        prox = self.rev.proximity_points
        for i, c in enumerate(cs):
            if gap_before[i] and fsm is not None:
                fsm.to(State.SETUP_INVALIDATED, c.start, "DATA_GAP")
                out.append(self._record(ctx, cs[j], SignalStatus.INVALIDATED, "DATA_GAP", {**base, "evaluations": evals}, fsm.trace, flags))
                fsm, j, evals = None, None, []
            if j is None:
                if c.l <= zone.ceiling + prox and c.h >= zone.floor - prox:
                    j = i
                    fsm = SetupFSM(f"PDR revised test@{c.end:%H:%M}")
                    fsm.to(State.SETUP_DETECTED, c.end, f"range [{c.l}, {c.h}] intersects zone [{zone.floor}, {zone.ceiling}] (+/- {prox})")
                    fsm.to(State.WAITING_FOR_CONFIRMATION, c.end, "waiting for a confirmation candle that closes above the zone")
                    if not self.rev.confirmation_may_be_interaction_candle:
                        continue
                else:
                    continue
            res = classify_confirmation(c, zone.floor, zone.ceiling, self.rev)
            ev = {"candle_start": f"{c.start:%H:%M}", "open": c.o, "high": c.h, "low": c.l, "close": c.c, "close_minus_ceiling": res["close_minus_ceiling"], "close_above_ceiling": res["close_above_ceiling"],
                  "patterns_passed": res["patterns_passed"], "pattern_details": {k: {a: b for a, b in v.items() if not isinstance(b, float) or not math.isnan(b)} for k, v in res["patterns"].items()}, "qualifies": res["qualifies"]}
            evals.append(ev)
            if res["qualifies"] and (i > j or self.rev.confirmation_may_be_interaction_candle):
                fsm.to(State.SIGNAL_CONFIRMED, c.end, f"patterns {res['patterns_passed']} and close {c.c} > zone ceiling {zone.ceiling} (test candle {cs[j].end:%H:%M})")
                lv = {**base, "entry_reference_price": c.c, "interaction_candle_start": f"{cs[j].start:%H:%M}", "patterns_passed": res["patterns_passed"], "close_minus_ceiling": res["close_minus_ceiling"],
                      "close_minus_floor": res["close_minus_floor"], "evaluations": evals}
                out.append(self._record(ctx, c, SignalStatus.CONFIRMED, None, lv, fsm.trace, flags))
                fsm, j, evals = None, None, []
        if fsm is not None and not fsm.terminal:
            out.append(self._record(ctx, cs[j], SignalStatus.INCOMPLETE_AT_EOD, "NO_QUALIFYING_CONFIRMATION_BEFORE_SESSION_END", {**base, "interaction_candle_start": f"{cs[j].start:%H:%M}", "evaluations": evals},
                                    fsm.trace, flags))
        return out
