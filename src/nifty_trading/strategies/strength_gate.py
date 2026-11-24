"""Phase 6.5 candle-strength RESEARCH gate (opt-in wrapper, never active by default; no live or paper configuration uses it).

Wraps ANY signal engine and invalidates (post hoc, per signal) confirmations whose confirming candle fails a body-strength threshold. Variants:
  A  original rules (no gate)
  B  minimum 60 % body on otherwise eligible DIRECTIONAL body-candle confirmations (colour matches the trade direction); separately defined patterns are exempt
  C  same at 70 %
  D  pattern-aware: 60 % body only for the methods whose SOURCE calls for a strong-body candle (PDS Method 1 'good red candle'; ORB's full-body route); everything else untouched
Exempt patterns (never rejected for a small body): IRF Method 3 (a wick-based sweep; its 60-70 % is the share of the UPPER WICK outside IRH, not a body requirement); PDR confirmations that qualify as a lower-price rejection / hammer;
PDS Method 2 (pin bar) and Method 3 (small-support break); ORB V2 confirmations matched by a pin-bar or engulfing route. Zero-range candles have no body percentage: where the gate applies they are rejected and logged.
LIMITATION (stated everywhere it is used): this is a filter on the signals an engine already emitted; an engine does not keep searching for a stronger LATER candle after the gate rejects one.
"""

from __future__ import annotations

from nifty_trading.research.phase65 import candle_metrics

THRESHOLD = {"B": 60.0, "C": 70.0, "D": 60.0}
VARIANTS = ("A", "B", "C", "D")


def gate_decision(variant: str, rec, m: dict) -> tuple[bool, str, str]:
    """(applies, passes, reason) for a CONFIRMED record and its confirming-candle metrics."""
    if variant == "A":
        return False, True, "original rules"
    lv = rec.reference_levels
    s, meth = rec.strategy, rec.method
    if variant == "D":
        if s == "PDS" and meth == "Method 1":
            scope = True
        elif s == "ORB" and str(lv.get("patterns_matched", "")) == "full_body":
            scope = True
        else:
            return False, True, "D: the source does not call for a strong-body candle for this method"
    else:
        want = "GREEN" if rec.direction == "LONG" else "RED"
        if m["colour"] != want:
            return False, True, "confirming candle is not a directional body candle (colour against the trade direction): gate not applicable"
        if s == "IRF" and meth == "Method 3":
            return False, True, "exempt: IRF Method 3 sweep is wick-based (60-70% is the UPPER-WICK share, not a body rule)"
        if s == "PDR" and "LOWER_PRICE_REJECTION" in (lv.get("patterns_passed") or []):
            return False, True, "exempt: PDR lower-price-rejection / hammer route"
        if s == "PDS" and meth in ("Method 2", "Method 3"):
            return False, True, f"exempt: PDS {meth} is a pin-bar / small-support-break route"
        if s == "ORB" and any(p in str(lv.get("patterns_matched", "")) for p in ("pin_bar", "engulfing")):
            return False, True, "exempt: ORB confirmation matched by a separately defined pin-bar / engulfing pattern"
        scope = True
    if not scope:
        return False, True, "out of scope"
    if m["zero_range"]:
        return True, False, "zero-range candle: no body percentage"
    th = THRESHOLD[variant]
    ok = m["body_pct"] >= th - 1e-9
    return True, ok, f"body {m['body_pct']:.1f}% {'>=' if ok else '<'} {th:.0f}%"


class StrengthGateEngine:
    """Wrapper engine: ``evaluate_session`` returns the inner engine's records with gate-rejected confirmations turned INVALIDATED (reason BODY_STRENGTH_...)."""

    def __init__(self, inner, variant: str):
        if variant not in VARIANTS:
            raise ValueError(variant)
        self.inner, self.variant = inner, variant
        self.STRATEGY = inner.STRATEGY
        self.log: list[dict] = []

    def __getattr__(self, name):
        return getattr(self.inner, name)

    def evaluate_session(self, ctx):
        recs = self.inner.evaluate_session(ctx)
        if self.variant == "A":
            return recs
        cand = ctx.candles.set_index("bar_start")
        for r in recs:
            if r.signal_status != "CONFIRMED" or r.signal_candle_start not in cand.index:
                continue
            row = cand.loc[r.signal_candle_start]
            m = candle_metrics(float(row["open"]), float(row["high"]), float(row["low"]), float(row["close"]))
            applies, ok, why = gate_decision(self.variant, r, m)
            self.log.append({"date": str(r.signal_date), "time": f"{r.signal_timestamp:%H:%M}", "strategy": r.strategy, "method": r.method, "direction": r.direction, "body_pct": m["body_pct"], "gate_applies": applies, "kept": ok, "why": why})
            if not ok:
                r.signal_status = "INVALIDATED"
                r.invalidation_reason = f"BODY_STRENGTH_VARIANT_{self.variant}: {why}"
        return recs
