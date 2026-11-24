"""IRF_V3_METHOD_1 - High Breakout Failure (SHORT). Built only from IRF_Inverse_Retest_Failure_Rulebook.pdf.

State machine over COMPLETE 5-minute candles in chronological order (a candle is used only at its ``end``):
  S0 AWAIT_FIRST_CANDLE  -> the 09:15 candle closes (09:20:00); marked level = its HIGH incl. wick (R02)
  S1 AWAIT_BREAKOUT      -> a later candle CLOSES strictly above the level, any colour (R03); no entry (R04)
  S2 AWAIT_FAILURE       -> a later candle CLOSES strictly below the SAME level (R05); SHORT signal at that candle's end (R07)
A close below the level in S1 is ignored (R06); a close exactly on the level is ignored in both states (R10).
NO other condition exists: no EMA, gap, previous-day structure, trend, colour or body-size test (R08).
"""

from __future__ import annotations

from datetime import time

from nifty_trading.research.irf_v3.models import M1, Candle, MethodTrace

FIRST_START = time(9, 15)


def run_method1(d, candles: list[Candle]) -> MethodTrace:
    t = MethodTrace(method=M1, date=d, status="NO_SIGNAL")
    if not candles or candles[0].start.time() != FIRST_START:
        t.no_signal_reason = "FIRST_CANDLE_MISSING"
        t.failed_conditions = ["first 09:15-09:20 candle complete"]
        return t
    first = candles[0]
    level = first.high
    t.first_candle, t.reference_candle = first, first
    t.initial_range_high, t.initial_range_low, t.reference_level = first.high, first.low, level
    t.reached.append("FIRST_CANDLE_CLOSED")
    t.events.append((first.end, f"first candle closed; level marked at its high {level:.2f}"))
    state = "AWAIT_BREAKOUT"
    cycles_done = 0
    for c in candles[1:]:
        if state == "AWAIT_BREAKOUT":
            if c.close > level:
                state = "AWAIT_FAILURE"
                if t.breakout_candle is None:
                    t.breakout_candle = c
                    t.reached.append("BREAKOUT_CLOSE_ABOVE_LEVEL")
                t.events.append((c.end, ("[after first signal, not traded] " if t.status == "SIGNAL" else "") + f"close {c.close:.2f} > level: breakout recorded, no entry"))
            elif c.close < level and t.breakout_candle is None:
                t.events.append((c.end, f"close {c.close:.2f} < level without an earlier breakout close: ignored (R06)"))
            elif c.close == level:
                t.events.append((c.end, "close exactly on the level: ignored (R10)"))
        else:  # AWAIT_FAILURE
            if c.close < level:
                cycles_done += 1
                if t.status == "NO_SIGNAL":
                    t.status, t.confirmation_candle, t.signal_time = "SIGNAL", c, c.end
                    t.reached.append("FAILURE_CLOSE_BELOW_LEVEL")
                    t.events.append((c.end, f"close {c.close:.2f} < level after a breakout: failure confirmed -> SHORT signal"))
                else:
                    t.later_cycles += 1
                state = "AWAIT_BREAKOUT"
            elif c.close == level:
                t.events.append((c.end, "close exactly on the level: ignored (R10)"))
    if t.status == "SIGNAL":
        t.rule_ids = ["M1-R02", "M1-R03", "M1-R05", "M1-R06", "M1-R07"]
        return t
    if t.breakout_candle is None:
        t.no_signal_reason = "NO_CLOSE_ABOVE_LEVEL"
        t.failed_conditions = ["breakout: a candle closing above the first-candle high", "failure: later close below the level"]
    else:
        t.no_signal_reason = "BREAKOUT_WITHOUT_FAILURE"
        t.failed_conditions = ["failure: a later candle closing back below the level"]
    return t
