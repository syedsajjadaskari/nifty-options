"""Phase 5.2: PDS with the co-confirmed methods RECORDED (the 'first eligible confirmation candle' requirement, section 5.2 of the brief).

The frozen ``PDSStrategy`` already activates each method on the first candle that satisfies every mandatory condition of that method (Methods 1 and 2 on the FIRST red candle at the zone; Method 3 only after a weak
first red candle, on the earliest candle that completes the small-support break). The brief adds one requirement the frozen engine only partly records: when several methods confirm on the same candle, record all of them
and produce ONE actionable signal. In the frozen engine a candle that is both a strong bearish candle (Method 1) and a higher-price-rejection pin bar (Method 2) is reported as Method 1 only.

``PDSCoConfirmStrategy`` = ``PDSStrategy`` unchanged, plus a post-step (after the base class has marked concurrent records) that adds the other methods that the same candle also satisfies to the record's ``concurrent_methods`` and a flag. Signals (strategy, method, direction,
timestamp, status) are identical to the frozen engine's; a regression test asserts this over the whole history. No threshold, zone, sequence or entry timing is touched.
"""

from __future__ import annotations

from nifty_trading.strategies.definitions import bearish_pin, pds_zone, strong_bearish, to_candles
from nifty_trading.strategies.pds import PDSStrategy

FLAG = "PHASE52_CO_CONFIRMED_METHODS_RECORDED"


class PDSCoConfirmStrategy(PDSStrategy):
    def evaluate_session(self, ctx):  # noqa: ANN001 - the annotation is applied after the base class has marked concurrent records
        out = super().evaluate_session(ctx)
        if not any(r.signal_status == "CONFIRMED" and r.method in ("Method 1", "Method 2") for r in out):
            return out
        p = self.p
        zone = pds_zone(ctx.previous, p)
        by_end = {c.end: c for c in to_candles(ctx.candles)}
        for r in out:
            if r.signal_status != "CONFIRMED" or r.method not in ("Method 1", "Method 2"):
                continue
            c = by_end.get(r.signal_timestamp)
            if c is None:
                continue
            others = []
            if r.method == "Method 1" and bearish_pin(c, p) and c.h >= zone.low and c.c < c.o:
                others.append("Method 2")
            if r.method == "Method 2" and strong_bearish(c, p):
                others.append("Method 1")  # cannot happen in the frozen sequence (Method 1 is tested first); kept so the record is complete if the order ever changes
            if others:
                r.concurrent_methods = sorted(set(list(r.concurrent_methods) + others))
                r.flags = list(r.flags) + [FLAG]
        return out
