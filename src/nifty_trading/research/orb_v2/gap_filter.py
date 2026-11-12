"""Opening-gap filter. gap = first 1-minute open of the session - previous trading day's OFFICIAL close (vendor daily close; not a vendor daily open). Reject when |gap| > max_gap_points
(both directions, BUY and SELL). A gap exactly equal to the limit passes ("more than 250 or 300" is the rejection wording)."""

from __future__ import annotations


def gap_points(open_1m: float, prev_close: float) -> float:
    return open_1m - prev_close


def gap_ok(gap: float, max_gap_points: float) -> bool:
    return abs(gap) <= max_gap_points + 1e-9
