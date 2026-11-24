"""IRF_V3_METHOD_2 - First Red Candle Resistance Failure (SHORT). Built only from IRF_Method2_First_Red_Candle_Rulebook.pdf.

State machine over COMPLETE 5-minute candles (used only at their ``end``):
  S0 AWAIT_A_BREAKOUT   Level A = 09:15 candle HIGH incl. wick (R02). A later candle CLOSING strictly above A = rally breakout, any colour (R03). Red candles before it are ignored (R06).
  S1 AWAIT_FIRST_RED    the FIRST red candle (close < open) AFTER the breakout candle sets Level B = its OPEN (top of the body, wick ignored) (R05, R07). Later red candles are ignored.
  S2 AWAIT_B_BREAKOUT   a LATER candle CLOSING strictly above B = second breakout, no entry (R08).
  S3 AWAIT_FAILURE      a later candle CLOSING strictly below B -> SHORT signal at that candle's end (R09, R11).
Closes exactly on a level are ignored (R13). Nothing invalidates an armed setup (R18, source silent). No EMA / gap / S-R / body filter (R12, R19).
"""

from __future__ import annotations

from datetime import time

from nifty_trading.research.irf_v3.models import M2, Candle, MethodTrace

FIRST_START = time(9, 15)


def run_method2(d, candles: list[Candle], *, red_breakout_candle_counts: bool = False, invalidate_close_below_a: bool = False) -> MethodTrace:
    t = MethodTrace(method=M2, date=d, status="NO_SIGNAL")
    if not candles or candles[0].start.time() != FIRST_START:
        t.no_signal_reason = "FIRST_CANDLE_MISSING"
        t.failed_conditions = ["first 09:15-09:20 candle complete"]
        return t
    first = candles[0]
    A = first.high
    t.first_candle = first
    t.initial_range_high, t.initial_range_low = first.high, first.low
    t.reached.append("FIRST_CANDLE_CLOSED")
    t.events.append((first.end, f"first candle closed; Level A = its high {A:.2f}"))
    state = "AWAIT_A_BREAKOUT"
    B = None
    for c in candles[1:]:
        if state == "AWAIT_A_BREAKOUT":
            if c.close > A:
                t.breakout_candle = c
                t.reached.append("RALLY_BREAKOUT_ABOVE_LEVEL_A")
                t.events.append((c.end, f"close {c.close:.2f} > Level A: rally breakout"))
                state = "AWAIT_FIRST_RED"
                if red_breakout_candle_counts and c.is_red:
                    B, t.reference_candle = c.open, c
                    t.reference_level = B
                    t.reached.append("LEVEL_B_MARKED")
                    t.events.append((c.end, f"breakout candle is red (variant): Level B = its open {B:.2f}"))
                    state = "AWAIT_B_BREAKOUT"
            elif c.is_red:
                t.ignored_red_before_breakout += 1
                t.events.append((c.end, "red candle before the rally breakout: ignored (R06)"))
        elif state == "DEAD":
            continue
        elif state == "AWAIT_FIRST_RED":
            if invalidate_close_below_a and c.close < A:  # VARIANT only (not in the source)
                state = "DEAD"
                t.events.append((c.end, f"close {c.close:.2f} < Level A before Level B was marked: setup invalidated (variant)"))
            elif c.is_red:
                B, t.reference_candle = c.open, c
                t.reference_level = B
                t.reached.append("LEVEL_B_MARKED")
                t.events.append((c.end, f"first red candle of the rally: Level B = body top (open) {B:.2f}"))
                state = "AWAIT_B_BREAKOUT"
        elif state == "AWAIT_B_BREAKOUT":
            if c.close > B:
                if t.second_breakout_candle is None:
                    t.second_breakout_candle = c
                    t.reached.append("SECOND_BREAKOUT_ABOVE_LEVEL_B")
                t.events.append((c.end, ("[after first signal, not traded] " if t.status == "SIGNAL" else "") + f"close {c.close:.2f} > Level B: second breakout, no entry"))
                state = "AWAIT_FAILURE"
        else:  # AWAIT_FAILURE
            if c.close < B:
                if t.status == "NO_SIGNAL":
                    t.status, t.confirmation_candle, t.signal_time = "SIGNAL", c, c.end
                    t.reached.append("FAILURE_CLOSE_BELOW_LEVEL_B")
                    t.events.append((c.end, f"close {c.close:.2f} < Level B after the second breakout: failure confirmed -> SHORT signal"))
                else:
                    t.later_cycles += 1
                state = "AWAIT_B_BREAKOUT"
    if t.status == "SIGNAL":
        t.rule_ids = ["M2-R02", "M2-R03", "M2-R05", "M2-R08", "M2-R09", "M2-R11"]
        return t
    if state == "DEAD":
        t.no_signal_reason = "SETUP_INVALIDATED_BELOW_LEVEL_A_VARIANT"
        t.failed_conditions = ["variant: close below Level A before Level B was marked"]
    elif state == "AWAIT_A_BREAKOUT":
        t.no_signal_reason = "NO_CLOSE_ABOVE_LEVEL_A"
        t.failed_conditions = ["rally breakout: close above Level A", "first red candle of the rally", "second breakout above Level B", "failure below Level B"]
    elif state == "AWAIT_FIRST_RED":
        t.no_signal_reason = "NO_RED_CANDLE_AFTER_RALLY_BREAKOUT"
        t.failed_conditions = ["first red candle after the rally breakout", "second breakout above Level B", "failure below Level B"]
    elif state == "AWAIT_B_BREAKOUT":
        t.no_signal_reason = "NO_CLOSE_ABOVE_LEVEL_B"
        t.failed_conditions = ["second breakout: close above Level B", "failure below Level B"]
    else:
        t.no_signal_reason = "SECOND_BREAKOUT_WITHOUT_FAILURE"
        t.failed_conditions = ["failure: close back below Level B"]
    return t
