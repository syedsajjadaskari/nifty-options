"""Configuration + manifest for ORB V2. Every setting carries its authority label (never silently promoted to author-confirmed)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace

# authority vocabulary (task Part 1)
EXPLICIT = "EXPLICIT_LATEST_RULEBOOK"
TO_CONFIRM = "TO_CONFIRM"
PROVISIONAL = "PROVISIONAL_MECHANICAL_CONVENTION"
SOURCE_CONFLICT = "SOURCE_CONFLICT"
OWNER = "OWNER_APPROVED"
LEGACY = "LEGACY_IMPLEMENTATION_ASSUMPTION"

EPS = 1e-9  # floating-point tolerance for ratio comparisons only (never for price comparisons)


@dataclass(frozen=True)
class OrbV2Config:
    config_id: str
    title: str
    # --- indicator
    ema_period: int = 200                                  # EXPLICIT: 200-period EMA on the 5-minute chart
    # --- gap filter
    max_gap_points: float = 250.0                          # TO_CONFIRM: rulebook says "250 or 300"; both are fixed scenarios
    # --- level filter
    break_mode: str = "CLOSE_BEYOND"                       # CLOSE_BEYOND (literal wording) | OPEN_ON_OLD_SIDE_AND_CLOSE_BEYOND (diagnostic: the candle must cross the level)
    boundary: str = "STRICT"                               # TO_CONFIRM: close must be STRICTLY beyond the level / zone edge
    inner_method: str = "SWING_FRACTAL_WICK_ZONE"          # PROVISIONAL: SWING_FRACTAL_WICK_ZONE | CLUSTER_ZONE
    swing_k: int = 2                                       # PROVISIONAL: candles each side of a confirmed swing
    cluster_tol_points: float = 10.0                       # PROVISIONAL (CLUSTER_ZONE only): swing extremes within this many points form one zone
    cluster_min_members: int = 2                           # PROVISIONAL (CLUSTER_ZONE only): repeated rejection
    # --- candle filter
    max_bad_wick_pct: float = 0.20                         # EXPLICIT (MAX_BAD_WICK_PCT = 20 adjustable): wrong-side wick / whole range
    full_body_max_total_wick_pct: float = 0.20             # EXPLICIT: (upper+lower)/range <= 20 %
    hammer_min_pin_wick_to_body: float = 2.0               # PROVISIONAL: long-side wick >= 2 x body
    hammer_max_opposite_wick_pct: float = 0.10             # PROVISIONAL: opposite wick <= 10 % of the range ("little or no" wick)
    engulf_reference: str = "PREV_SESSION_LAST_CONTINUOUS_5M"  # PROVISIONAL/TO_CONFIRM: reference candle for engulfing at 09:20 | NONE
    engulf_requires_opposite_colour: bool = False          # rulebook: "body engulfs the previous candle body" (no colour demanded)
    # --- trade
    stop_points: float = 30.0                              # EXPLICIT
    target_points: float = 60.0                            # EXPLICIT
    entry_convention: str = "OPEN_OF_0920_1M_BAR"          # PROVISIONAL: first causally executable fill (rulebook entry reference "close of the 9:15 candle" is TO CONFIRM)
    same_bar_policy: str = "STOP_FIRST"                    # rulebook conservative default (TO CONFIRM); the alternative is reported as sensitivity
    forced_exit_clock: str = "15:14"                       # PROVISIONAL: repo FORCED-EXIT-001, open of the 15:14 bar (< 15:15); rulebook leaves EOD time open
    quantity: int = 75                                     # declared synthetic quantity (the rulebook's own example)

    def to_manifest(self) -> dict:
        d = asdict(self)
        authority = {
            "ema_period": EXPLICIT, "max_gap_points": TO_CONFIRM, "break_mode": SOURCE_CONFLICT, "boundary": TO_CONFIRM, "inner_method": PROVISIONAL, "swing_k": PROVISIONAL,
            "cluster_tol_points": PROVISIONAL, "cluster_min_members": PROVISIONAL, "max_bad_wick_pct": EXPLICIT, "full_body_max_total_wick_pct": EXPLICIT,
            "hammer_min_pin_wick_to_body": PROVISIONAL, "hammer_max_opposite_wick_pct": PROVISIONAL, "engulf_reference": TO_CONFIRM, "engulf_requires_opposite_colour": PROVISIONAL,
            "stop_points": EXPLICIT, "target_points": EXPLICIT, "entry_convention": TO_CONFIRM, "same_bar_policy": TO_CONFIRM, "forced_exit_clock": PROVISIONAL, "quantity": PROVISIONAL}
        body = {"settings": d, "authority": authority}
        h = hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()
        return {**body, "config_sha256": h}


A = OrbV2Config("ORB-V2-A", "Written-rule reference: explicit rulebook rules plus labelled provisional conventions (250-point gap limit)")
B = replace(A, config_id="ORB-V2-B", title="Gap-limit alternative (300 points)", max_gap_points=300.0)
C = replace(A, config_id="ORB-V2-C", title="Level-construction alternative (clustered repeated-rejection zones instead of single swing zones)", inner_method="CLUSTER_ZONE")
D = replace(A, config_id="ORB-V2-D", title="Candle-interpretation diagnostic (no engulfing at 09:20: there is no earlier candle in the session)", engulf_reference="NONE")
CONFIGS = {c.config_id: c for c in (A, B, C, D)}
# diagnostic-only (NOT a candidate configuration): the stricter reading of "break" (the opening candle must cross the level from the old side)
DIAG_OLDSIDE = replace(A, config_id="DIAG-A-OLDSIDE", title="Diagnostic: break = candle opens on the old side of the level and closes beyond it", break_mode="OPEN_ON_OLD_SIDE_AND_CLOSE_BEYOND")
DIAGNOSTICS = {DIAG_OLDSIDE.config_id: DIAG_OLDSIDE}
