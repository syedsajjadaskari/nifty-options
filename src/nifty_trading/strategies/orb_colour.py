"""Phase 5.1 (opt-in research variant, NOT part of the frozen baseline): ORB with the author's colour clarification.

Author (handwritten corrections, Phase 5.1, AC27, 2025-11-27): "ORB is activated on a red candle for long side, which is wrong. ORB for long should be in green closing."
The frozen ORB engine admits a bearish first candle for a long through the conditional PIN-BAR alternative (its own explanation for 20251127-1-ORB says: "the candle is bearish, i.e. against the trade direction; the
pin route accepts it because the level break and close beyond it carry the direction").

``ORBColourStrategy`` = the frozen ``ORBStrategy`` unchanged, plus ONE post-condition applied to every CONFIRMED ORB record (all three setups): a LONG needs a green first candle (close > open); by the existing
mirror rule ORB-GLOBAL-002 ("same rules in both directions") a SHORT needs a red first candle (close < open). A confirmed record that fails is returned as INVALIDATED with the reason
``FIRST_CANDLE_COLOUR_AGAINST_DIRECTION``; nothing else (levels, trend filter, strength thresholds, stop, target) is touched. The frozen module ``orb.py`` is not edited: the baseline stays byte-identical and this class is
used only by an explicit Phase 5.1 configuration (``research/phase51.py``).
"""

from __future__ import annotations

from nifty_trading.strategies.base import Direction, SignalStatus
from nifty_trading.strategies.orb import ORBStrategy

REASON = "FIRST_CANDLE_COLOUR_AGAINST_DIRECTION"
RULE_NOTE = "AUTHOR_CLARIFICATION_PHASE51_AC27: ORB long needs a green close; short (mirror, ORB-GLOBAL-002) a red close"


def colour_ok(direction: str, open_: float | None, close: float | None) -> bool:
    if open_ is None or close is None:
        return False
    return close > open_ if direction == Direction.LONG.value else close < open_


class ORBColourStrategy(ORBStrategy):
    """ORBStrategy + the colour post-condition (see the module docstring)."""

    def _scan(self, ctx, cs, gap_before):  # noqa: ANN001 - signature of the frozen engine
        out = []
        for r in super()._scan(ctx, cs, gap_before):
            if r.signal_status == SignalStatus.CONFIRMED.value and not colour_ok(r.direction, r.signal_candle_open, r.signal_candle_close):
                r.signal_status = SignalStatus.INVALIDATED.value
                r.invalidation_reason = REASON
                r.rule_ids_failed = list(r.rule_ids_failed) + ["AUTHOR-PHASE51-ORB-COLOUR"]
                r.state_trace = list(r.state_trace) + [f"{r.signal_candle_start:%H:%M} SIGNAL_CONFIRMED->SETUP_INVALIDATED: {RULE_NOTE}"]
                r.flags = list(r.flags) + ["PHASE51_COLOUR_RULE_APPLIED"]
            out.append(r)
        return out
