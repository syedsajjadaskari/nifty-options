"""PDR - Previous Day Resistance, BODY-BASED resistance zone (Phase 3.6). Source: ``PDR_Strategy_Guide.pdf`` plus the strategy author's clarifications.

This is a separate, versioned engine (``PDR_BODY_PHASE36``). The legacy engine (``pdr.py``) and the Phase 3.4 / 3.5 engine (``pdr_revised.py``, wick-based ceiling) are NOT modified, so every earlier
result stays reproducible. It changes zone construction and the opening condition only; the three confirmation patterns, the strict close rule and the sequence logic are the Phase 3.4 functions
(imported, not copied). Stops, targets, sizing, cutoff and the portfolio controller are untouched.

Author statements (AUTHOR_APPROVED, quoted from the strategy author):
  "The high should be considered, day's high should be considered and a zone should be drawn. If there are multiple highs, then a zone which connects all should be considered."
  "Wick should be ignored, but body should be considered. If a price is only a wick, it should be ignored. If it is a body high, that should be considered when drawing the zone."
  The next session's open must be strictly above the previous day's resistance zone (not inside it).
  One good green body candle OR lower price rejection candle OR hammer candle is required; fixed body-percentage / wick-size thresholds are not required.
  "The candle should close above the zone."

The author did NOT give: how many body highs make 'multiple', how close they must be, how the lower boundary is drawn, and any numeric shape of the three candle patterns. Every such choice here is a
labelled research parameter (PROPOSED_FOR_REVIEW), recorded on every signal. Nothing is chosen by profit or by agreement with the manual journal.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
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
from nifty_trading.strategies.definitions import Candle, gap_info, prev_candles, to_candles
from nifty_trading.strategies.params import ProposalConfig
from nifty_trading.strategies.pdr_revised import PROFILES, PDRRevisionConfig, classify_confirmation

AA, PR, UA, PRESERVED, OI, SV = "AUTHOR_APPROVED", "PROPOSED_FOR_REVIEW", "USER_APPROVED", "PRESERVED_FROM_PHASE2", "OWNER_INTERPRETATION", "SOURCE_VERIFIED"
VERSION = "PDR_BODY_PHASE36"
CANDIDATES = ("A_HIGHEST_BODY_HIGH", "B_MULTIPLE_BODY_HIGH_CLUSTER")
SPIKE_POLICIES = ("ALWAYS_INCLUDE_HIGHEST_BODY_HIGH", "EXCLUDE_ISOLATED_BODY_SPIKE_ABOVE_SHELF")  # the second is a diagnostic only
ZERO_HEIGHT_POLICIES = ("UNRESOLVED_NO_SETUP", "TREAT_AS_LINE")


@dataclass(frozen=True)
class PDRBodyConfig:
    zone_candidate: str = "A_HIGHEST_BODY_HIGH"
    # multiple-body-high research parameters (the author gave none of these numbers)
    b_local_high_k: int = 1  # a body-high pivot is not lower than the k candles on each side
    b_min_touches: int = 2  # distinct touch groups needed to call it 'multiple highs'
    b_tolerance_points: float = 5.0  # a body-high pivot within this distance of the highest body high joins the cluster
    b_min_separation_candles: int = 2  # members closer than this (in candles) count as ONE touch
    b_spike_policy: str = "ALWAYS_INCLUDE_HIGHEST_BODY_HIGH"
    zero_height_policy: str = "UNRESOLVED_NO_SETUP"  # a zone with no height is not a zone: the setup is left unresolved (TREAT_AS_LINE is a sensitivity option)
    # confirmation: the Phase 3.4 pattern functions, with a research profile (never author-approved)
    pattern_profile: str = "RESEARCH_DEFAULT"
    patterns_enabled: tuple[str, ...] = ("GOOD_GREEN_BODY", "LOWER_PRICE_REJECTION", "HAMMER")
    proximity_points: float = 0.0
    open_vs_zone: str = "ABOVE_ZONE"  # AUTHOR_APPROVED; "ANY" exists only as a labelled sensitivity
    confirmation_may_be_interaction_candle: bool = False
    wait_policy: str = "WAIT_FOR_QUALIFYING_CANDLE"

    def __post_init__(self) -> None:
        if self.zone_candidate not in CANDIDATES:
            raise ValueError(self.zone_candidate)
        if self.pattern_profile not in PROFILES:
            raise ValueError(self.pattern_profile)
        if self.b_spike_policy not in SPIKE_POLICIES:
            raise ValueError(self.b_spike_policy)
        if self.zero_height_policy not in ZERO_HEIGHT_POLICIES:
            raise ValueError(self.zero_height_policy)
        if self.open_vs_zone not in ("ABOVE_ZONE", "ANY"):
            raise ValueError(self.open_vs_zone)

    @property
    def thresholds(self) -> dict[str, float]:
        return PROFILES[self.pattern_profile]

    def pattern_config(self) -> PDRRevisionConfig:
        """The Phase 3.4 configuration object the imported pattern functions read (only its pattern fields are used)."""
        return PDRRevisionConfig(pattern_profile=self.pattern_profile, patterns_enabled=self.patterns_enabled, proximity_points=self.proximity_points)

    def config_id(self, proposals: ProposalConfig | None = None) -> str:
        blob = json.dumps({"c": asdict(self), "p": (proposals.to_dict() if proposals else None), "v": VERSION}, sort_keys=True, default=str)
        return f"PDRBODY-{self.zone_candidate[0]}-{self.pattern_profile}-{hashlib.sha256(blob.encode()).hexdigest()[:8]}"


# ---------------------------------------------------------------------------------------------------- the rules of this revision
def _rule(rule_id, status, text, source, **kw) -> dict[str, Any]:
    return {"rule_id": rule_id, "status": status, "text": text, "source": source, **kw}


AUTHOR = "strategy author's clarification (Phase 3.6 brief)"
GUIDE = "PDR_Strategy_Guide.pdf"
PDR_BODY_RULES: list[dict[str, Any]] = [
    _rule("PDR-B01", AA, "The previous trading day's high is considered and a zone is drawn (author: \"the high should be considered, day's high should be considered and a zone should be drawn\").", AUTHOR,
          implemented_by="build_zone_a / build_zone_b"),
    _rule("PDR-B01a", AA, "Wick should be ignored, but body should be considered: a price that is only a wick is ignored; a body high is considered when drawing the zone.", AUTHOR,
          supersedes=["PDR guide p.2 'upper boundary: the highest point of the upper wick'", "PDR-A01 (Phase 3.4: ceiling = wick high)"], implemented_by="body_high(); zone ceiling = highest body high"),
    _rule("PDR-B01b", OI, "Reading of B01a: for every completed previous-session 5-minute candle body_high = max(open, close); the principal reference is the highest body_high; the wick-only high is never the active ceiling "
                          "(it is kept as a diagnostic).", "Phase 3.6 brief interpretation of the author's words", implemented_by="body_high / anchor_index"),
    _rule("PDR-B02", AA, "If there are multiple highs, a zone that connects all of them is considered (principle only; the author gave no numbers).", AUTHOR, implemented_by="build_zone_b"),
    _rule("PDR-B02a", PR, "How many body highs make 'multiple': distinct touch groups >= b_min_touches (default 2).", "research parameter", parameter="b_min_touches"),
    _rule("PDR-B02b", PR, "Maximum difference between body highs: a body-high pivot within b_tolerance_points (default 5.0) of the highest body high joins the cluster.", "research parameter", parameter="b_tolerance_points"),
    _rule("PDR-B02c", PR, "Minimum candle separation: members closer than b_min_separation_candles (default 2) count as one touch.", "research parameter", parameter="b_min_separation_candles"),
    _rule("PDR-B02d", PR, "What counts as a body high of the cluster: a body-high pivot not lower than its b_local_high_k (default 1) neighbours on each side (non-strict).", "research parameter", parameter="b_local_high_k"),
    _rule("PDR-B02e", PR, "A lone body spike above repeated body highs is never discarded (ALWAYS_INCLUDE_HIGHEST_BODY_HIGH); excluding it is a diagnostic option only. A wick-only spike is ignored by B01a, not by this policy.",
          "research parameter", parameter="b_spike_policy"),
    _rule("PDR-B02f", PR, "Lower boundary: the zone is the hull of the member candles' bodies - floor = the lowest body_low among the members; for candidate A the member is the highest-body-high candle alone, so the floor is "
                          "its body low. The author gave no lower-boundary rule.", "research parameter", parameter="(fixed in build_zone_a / build_zone_b)"),
    _rule("PDR-B02g", PR, "Equal highest body highs: the first candle anchors the zone.", "research parameter", parameter="(fixed in anchor_index)"),
    _rule("PDR-B02h", PR, "A zone with zero height (ceiling == floor) is detected and flagged ZERO_HEIGHT_ZONE; by default the setup is left UNRESOLVED (no signal) instead of inventing a width; TREAT_AS_LINE is a sensitivity option.",
          "research parameter", parameter="zero_height_policy"),
    _rule("PDR-B03", AA, "The next session's opening price must be strictly above the previous day's resistance-zone ceiling (session_open > zone_upper); an open inside the zone, below it or exactly at the ceiling rejects the setup.",
          AUTHOR, implemented_by="PDRBodyStrategy._scan (open_vs_zone=ABOVE_ZONE)"),
    _rule("PDR-B03a", SV, "The next day must also open gap up (open above the official previous close).", f"{GUIDE} p.1 'Market must open gap up'", implemented_by="gap_info"),
    _rule("PDR-B03b", PRESERVED, "Price must return to / interact with the zone (any candle whose range overlaps the zone +/- proximity) before the confirmation candle; the confirmation comes strictly after the test candle.",
          f"{GUIDE} pp.1-3; legacy PDR-005/006", parameter="proximity_points / confirmation_may_be_interaction_candle"),
    _rule("PDR-B04", AA, "A LONG entry needs one good green body candle OR a lower price rejection candle OR a hammer candle.", AUTHOR, implemented_by="pdr_revised.classify_confirmation"),
    _rule("PDR-B04a", AA, "Fixed body-percentage and wick-size thresholds are not required by the author.", AUTHOR, implemented_by="(thresholds are research parameters, B04c)"),
    _rule("PDR-B04b", OI, "Reading of B04: OR logic; every pattern that passes is recorded; one signal per candle; rejection and hammer need no particular colour.", "Phase 3.6 brief interpretation of the author's words",
          implemented_by="classify_confirmation / _scan"),
    _rule("PDR-B04c", PR, "A deterministic research classification is unavoidable: profile RESEARCH_DEFAULT (carried from Phase 3.5 for comparability: good green body = bullish, body >= 60% and upper wick <= 20% of the range; "
                          "rejection = lower wick >= 2x body, close in the top 30% of the range, low reached the zone ceiling; hammer = lower wick >= 2x body, upper wick <= 10%, body bottom at >= 60% of the range). "
                          "NOT author-approved; chosen neither by profit nor by journal agreement.", "research parameter", parameter="pattern_profile"),
    _rule("PDR-B05", AA, "The confirmation candle should close above the zone.", AUTHOR, implemented_by="classify_confirmation"),
    _rule("PDR-B05a", OI, "Reading of B05: close > the zone CEILING, strictly; equal, inside the zone or below the floor is invalid; a lower wick may penetrate the zone.", "Phase 3.6 brief interpretation of the author's words",
          implemented_by="classify_confirmation (close > zone_ceiling)"),
    _rule("PDR-B06", UA, "Entry only after the confirmation candle has completed; fill = open of the 1-minute bar that starts when it ends (existing EXE-FILL-001 convention).", "existing execution convention",
          implemented_by="signal timestamp = candle end"),
    _rule("PDR-B07", PR, "The test stays armed until a candle qualifies or the session ends (wait_policy); the confirmation may not be the test candle (preserved legacy rule).", "research parameter", parameter="wait_policy"),
]
RULE_STATUS = {r["rule_id"]: r["status"] for r in PDR_BODY_RULES}


# ---------------------------------------------------------------------------------------------------- body geometry and zones
def body_high(c: Candle) -> float:
    return max(c.o, c.c)


def body_low(c: Candle) -> float:
    return min(c.o, c.c)


def anchor_index(cs: list[Candle]) -> int:
    """First candle that made the previous session's highest BODY high (a wick-only high is ignored)."""
    top = max(body_high(c) for c in cs)
    return next(i for i, c in enumerate(cs) if body_high(c) == top)


@dataclass
class BodyZone:
    candidate: str
    kind: str  # HIGHEST_BODY_HIGH_CANDLE | ISOLATED_BODY_HIGH | MULTIPLE_BODY_HIGH_CLUSTER | SHELF_EXCLUDING_BODY_SPIKE
    floor: float
    ceiling: float
    previous_day_body_high: float
    previous_day_wick_high: float  # diagnostic only: never the ceiling
    members: tuple[int, ...]
    source_starts: tuple[datetime, ...]
    member_body_highs: tuple[float, ...]
    touches: int
    notes: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)

    @property
    def width(self) -> float:
        return self.ceiling - self.floor

    @property
    def zero_height(self) -> bool:
        return self.ceiling <= self.floor


def _flags(cs: list[Candle], ceiling: float, floor: float, flags: list[str]) -> list[str]:
    wick = max(c.h for c in cs)
    out = list(flags)
    if ceiling < wick:
        out.append("CEILING_BELOW_WICK_HIGH")  # the highest wick was ignored (PDR-B01a)
    if ceiling <= floor:
        out.append("ZERO_HEIGHT_ZONE")
    return out


def build_zone_a(cs: list[Candle]) -> BodyZone:
    """Candidate A: the body of the candle that made the previous session's highest body high. Ceiling = that body high; floor = that candle's body low."""
    j = anchor_index(cs)
    c = cs[j]
    wick = max(x.h for x in cs)
    z = BodyZone("A_HIGHEST_BODY_HIGH", "HIGHEST_BODY_HIGH_CANDLE", body_low(c), body_high(c), body_high(c), wick, (j,), (c.start,), (body_high(c),), 1,
                 ["ceiling = the previous session's highest body high (wicks ignored); floor = body low of that candle"])
    z.flags = _flags(cs, z.ceiling, z.floor, [])
    return z


def body_pivots(cs: list[Candle], k: int) -> list[int]:
    out = []
    for j in range(len(cs)):
        if all(body_high(cs[j]) >= body_high(cs[m]) for m in range(max(0, j - k), min(len(cs), j + k + 1)) if m != j):
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


def build_zone_b(cs: list[Candle], cfg: PDRBodyConfig) -> BodyZone:
    """Candidate B: connect the highest body high with the body-high pivots within ``b_tolerance_points`` of it (at least ``b_min_touches`` distinct touches); otherwise it is an isolated body high
    (the same zone as candidate A). The highest body high is never discarded; wick-only prices never take part."""
    dh = anchor_index(cs)
    top = body_high(cs[dh])
    wick = max(c.h for c in cs)
    piv = body_pivots(cs, cfg.b_local_high_k)
    tol = cfg.b_tolerance_points + 1e-9
    members = sorted({j for j in piv if body_high(cs[j]) >= top - tol} | {dh})
    groups = _groups(members, cfg.b_min_separation_candles)
    flags: list[str] = []
    notes: list[str] = []
    below = sorted((j for j in piv if body_high(cs[j]) < top - tol), key=lambda j: body_high(cs[j]), reverse=True)  # a shelf of repeated body highs under a lone body spike
    shelf: list[int] = []
    for j0 in below:
        shelf = [j for j in below if abs(body_high(cs[j]) - body_high(cs[j0])) <= tol]
        if len(_groups(shelf, cfg.b_min_separation_candles)) >= cfg.b_min_touches:
            break
        shelf = []
    if shelf:
        flags.append("BODY_SPIKE_ABOVE_SHELF")
        notes.append(f"the highest body high {top:.2f} is {top - max(body_high(cs[j]) for j in shelf):.2f} points above a shelf of {len(shelf)} repeated body highs; policy {cfg.b_spike_policy}")
    if len(groups) >= cfg.b_min_touches:
        floor = min(body_low(cs[j]) for j in members)
        notes.append(f"{len(groups)} touches within {cfg.b_tolerance_points:g} points of the highest body high {top:.2f}; zone = hull of the member bodies")
        z = BodyZone("B_MULTIPLE_BODY_HIGH_CLUSTER", "MULTIPLE_BODY_HIGH_CLUSTER", floor, top, top, wick, tuple(members), tuple(cs[j].start for j in members), tuple(body_high(cs[j]) for j in members), len(groups), notes)
    else:
        z = BodyZone("B_MULTIPLE_BODY_HIGH_CLUSTER", "ISOLATED_BODY_HIGH", body_low(cs[dh]), top, top, wick, (dh,), (cs[dh].start,), (top,), 1,
                     notes + ["no other body high within tolerance: isolated body high (identical to candidate A)"])
    if cfg.b_spike_policy == "EXCLUDE_ISOLATED_BODY_SPIKE_ABOVE_SHELF" and shelf and z.kind == "ISOLATED_BODY_HIGH":
        sm = sorted(shelf)
        z = BodyZone("B_MULTIPLE_BODY_HIGH_CLUSTER", "SHELF_EXCLUDING_BODY_SPIKE", min(body_low(cs[j]) for j in sm), max(body_high(cs[j]) for j in sm), top, wick, tuple(sm), tuple(cs[j].start for j in sm),
                     tuple(body_high(cs[j]) for j in sm), len(_groups(sm, cfg.b_min_separation_candles)), notes + ["DIAGNOSTIC policy: the body spike is excluded; the ceiling is BELOW the previous-day body high"])
        flags.append("HIGHEST_BODY_HIGH_EXCLUDED_BY_POLICY")
    z.flags = _flags(cs, z.ceiling, z.floor, flags)
    return z


def build_zone(cs: list[Candle], cfg: PDRBodyConfig) -> BodyZone:
    return build_zone_a(cs) if cfg.zone_candidate == "A_HIGHEST_BODY_HIGH" else build_zone_b(cs, cfg)


# ---------------------------------------------------------------------------------------------------- the engine
class PDRBodyStrategy(SignalEngine):
    STRATEGY = "PDR"
    METHODS = ("PDR",)
    REQUIRES_PREVIOUS_SESSION = True

    def __init__(self, name=None, params=None, proposals=None, trade=None, revision: PDRBodyConfig | None = None):
        super().__init__(name, params, proposals, trade)
        self.rev = revision or PDRBodyConfig()

    def _default_direction(self) -> str:
        return Direction.LONG.value

    def _record(self, ctx: SessionContext, c: Candle, status: SignalStatus, why: str | None, levels: dict[str, Any], trace: list[str], flags: list[str]) -> SignalRecord:
        """A SignalRecord without the legacy registry lookups (the rules live in PDR_BODY_RULES); a signal is never VERIFIED here."""
        ver = VerificationStatus.RESEARCH_VARIANT if status is SignalStatus.CONFIRMED else VerificationStatus.NOT_READY
        sat = ["PDR-B01", "PDR-B01a", "PDR-B02", "PDR-B03", "PDR-B03a", "PDR-B03b", "PDR-B04", "PDR-B05", "PDR-B06"] if status is SignalStatus.CONFIRMED else []
        rec = SignalRecord(
            strategy=self.STRATEGY, method="PDR", direction=Direction.LONG.value, signal_date=ctx.date, signal_timestamp=c.end, signal_candle_start=c.start, signal_candle_open=c.o, signal_candle_high=c.h,
            signal_candle_low=c.l, signal_candle_close=c.c, reference_levels=levels, rule_ids_satisfied=sat, rule_ids_failed=[],
            signal_status=status.value, invalidation_reason=why, verification_status=ver.value,
            rule_ids_unresolved=[r for r, st in RULE_STATUS.items() if st in (PR, OI)],
            proposals_used={"pdr_body": asdict(self.rev), "thresholds": self.rev.thresholds}, state_trace=trace, flags=list(ctx.data_flags) + flags,
            execution_config=self.exec_config("PDR", {"VERIFIED": "VERIFIED_EXPLICIT"}.get(ver.value, ver.value) if status is SignalStatus.CONFIRMED else "NOT_A_CONFIRMED_SIGNAL",
                                              self._execution_status(c.end) if status is SignalStatus.CONFIRMED else "NOT_A_CONFIRMED_SIGNAL"))
        rec.execution_config["pdr_body"] = {"config_id": self.rev.config_id(self.p), "zone_candidate": self.rev.zone_candidate, "pattern_profile": self.rev.pattern_profile,
                                            "rule_status": dict(RULE_STATUS), "version": VERSION}
        return rec

    def _scan(self, ctx: SessionContext, cs: list[Candle], gap_before: list[bool]) -> list[SignalRecord]:
        g = gap_info(ctx, self.p)
        if g.direction != "UP":
            return []  # PDR-B03a: no gap up, no setup
        prev = ctx.previous
        pcs = to_candles(prev_candles(prev, self.p))
        zone = build_zone(pcs, self.rev)
        base = {"zone_candidate": self.rev.zone_candidate, "zone_kind": zone.kind, "zone_floor": zone.floor, "zone_ceiling": zone.ceiling, "zone_low": zone.floor, "zone_high": zone.ceiling, "zone_width": zone.width,
                "zone_member_candle_starts": [f"{s:%Y-%m-%d %H:%M}" for s in zone.source_starts], "zone_member_body_highs": list(zone.member_body_highs), "zone_touches": zone.touches, "zone_notes": zone.notes,
                "zone_flags": zone.flags, "previous_day_body_high": zone.previous_day_body_high, "previous_day_wick_high_diagnostic": zone.previous_day_wick_high,
                "wick_ignored_points": zone.previous_day_wick_high - zone.ceiling, "gap_points": g.points, "session_open": ctx.open_price, "prev_close": prev.close_official,
                "config_id": self.rev.config_id(self.p), "pattern_profile": self.rev.pattern_profile}
        flags = [f"ZONE_CANDIDATE={self.rev.zone_candidate}", f"PATTERN_PROFILE={self.rev.pattern_profile}", "PDR_BODY_PHASE36_RESEARCH_CANDIDATE"] + [f"ZONE_{f}" for f in zone.flags]
        if zone.zero_height and self.rev.zero_height_policy == "UNRESOLVED_NO_SETUP":
            return [self._record(ctx, cs[0], SignalStatus.INVALIDATED, "ZERO_HEIGHT_ZONE_UNRESOLVED", base, [], flags)]
        if self.rev.open_vs_zone == "ABOVE_ZONE" and not ctx.open_price > zone.ceiling:
            return [self._record(ctx, cs[0], SignalStatus.INVALIDATED, "OPEN_NOT_STRICTLY_ABOVE_ZONE", base, [], flags)]
        pcfg = self.rev.pattern_config()
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
                    fsm = SetupFSM(f"PDR body test@{c.end:%H:%M}")
                    fsm.to(State.SETUP_DETECTED, c.end, f"range [{c.l}, {c.h}] intersects zone [{zone.floor}, {zone.ceiling}] (+/- {prox})")
                    fsm.to(State.WAITING_FOR_CONFIRMATION, c.end, "waiting for a confirmation candle that closes above the zone")
                    if not self.rev.confirmation_may_be_interaction_candle:
                        continue
                else:
                    continue
            res = classify_confirmation(c, zone.floor, zone.ceiling, pcfg)
            ev = {"candle_start": f"{c.start:%H:%M}", "open": c.o, "high": c.h, "low": c.l, "close": c.c, "close_minus_ceiling": res["close_minus_ceiling"], "close_above_ceiling": res["close_above_ceiling"],
                  "patterns_passed": res["patterns_passed"], "pattern_details": {k: {a: b for a, b in v.items() if not isinstance(b, float) or not math.isnan(b)} for k, v in res["patterns"].items()},
                  "qualifies": res["qualifies"]}
            evals.append(ev)
            if res["qualifies"] and (i > j or self.rev.confirmation_may_be_interaction_candle):
                fsm.to(State.SIGNAL_CONFIRMED, c.end, f"patterns {res['patterns_passed']} and close {c.c} > zone ceiling {zone.ceiling} (test candle {cs[j].end:%H:%M})")
                lv = {**base, "entry_reference_price": c.c, "interaction_candle_start": f"{cs[j].start:%H:%M}", "patterns_passed": res["patterns_passed"], "close_minus_ceiling": res["close_minus_ceiling"],
                      "close_minus_floor": res["close_minus_floor"], "evaluations": evals}
                out.append(self._record(ctx, c, SignalStatus.CONFIRMED, None, lv, fsm.trace, flags))
                fsm, j, evals = None, None, []
        if fsm is not None and not fsm.terminal:
            out.append(self._record(ctx, cs[j], SignalStatus.INCOMPLETE_AT_EOD, "NO_QUALIFYING_CONFIRMATION_BEFORE_SESSION_END",
                                    {**base, "interaction_candle_start": f"{cs[j].start:%H:%M}", "evaluations": evals}, fsm.trace, flags))
        return out
