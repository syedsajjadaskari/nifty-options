## src/nifty_trading/strategies/orb.py

```python
   1: """ORB - Opening Range Breakout (both directions). Source: ``ORB_Strategy_Rulebook-2.pdf``.
   2: 
   3: Decision time is 09:20, after the first 5-minute candle closes (ORB-GLOBAL-001). Setups:
   4:   Method 1      previous-day level break (long: resistance, short: support)
   5:   Method 2      inner level + trendline  -> RESEARCH_VARIANT only: the source gives no objective
   6:                 construction for the inner level or the trendline (rules ORB-M2-*-001 are MISSING)
   7:   Gap/200 MA    gap through the 200-period MA with the first candle closing beyond it
   8: 
   9: Records are emitted only when the *trigger event* occurred (level broken / gap crossed the MA);
  10: days on which nothing triggered produce no record.
  11: """
  12: 
  13: from __future__ import annotations
  14: 
  15: import math
  16: 
  17: from nifty_trading.data.sessions import SessionContext
  18: from nifty_trading.strategies.base import (
  19:     Direction,
  20:     SetupFSM,
  21:     SignalEngine,
  22:     SignalRecord,
  23:     SignalStatus,
  24:     State,
  25: )
  26: from nifty_trading.strategies.definitions import (
  27:     Candle,
  28:     bearish_pin,
  29:     bullish_pin,
  30:     gap_info,
  31:     lower_rejection,
  32:     ma_value,
  33:     pivot_highs,
  34:     pivot_lows,
  35:     prev_candles,
  36:     prev_high_low,
  37:     strong_bearish,
  38:     strong_bullish,
  39:     to_candles,
  40:     trend_check,
  41:     upper_rejection,
  42: )
  43: from nifty_trading.strategies.rules import implements
  44: 
  45: _G = ["ORB-GLOBAL-001", "ORB-GLOBAL-002"]
  46: 
  47: 
  48: class ORBStrategy(SignalEngine):
  49:     STRATEGY = "ORB"
  50:     METHODS = ("Method 1", "Method 2", "Gap/200DMA")
  51:     TREND_METHODS = ("Method 1", "Method 2")
  52:     REQUIRES_PREVIOUS_SESSION = True
  53: 
  54:     def _default_direction(self) -> str:
  55:         return "BOTH"
  56: 
  57:     @implements("ORB-GLOBAL-001", "ORB-GLOBAL-002")
  58:     def _scan(self, ctx: SessionContext, cs: list[Candle], gap_before: list[bool]) -> list[SignalRecord]:
  59:         out: list[SignalRecord] = []
  60:         for d in (Direction.LONG, Direction.SHORT):
  61:             for fn in (self._method1, self._method2, self._gap_setup):
  62:                 r = fn(ctx, cs[0], d)
  63:                 if r is not None:
  64:                     out.append(r)
  65:         return out
  66: 
  67:     # ------------------------------------------------------------------ helpers
  68:     def _base_levels(self, ctx: SessionContext, c: Candle) -> dict:
  69:         prev = ctx.previous
  70:         ph, pl = prev_high_low(prev, self.p)
  71:         return {"entry_reference_price": c.c, "first_candle_high": c.h, "first_candle_low": c.l,
  72:                 "prev_day_high": ph, "prev_day_low": pl, "prev_close": prev.close_official}
  73: 
  74:     def _quality(self, c: Candle, d: Direction) -> bool:
  75:         """Strong body, or (ORB pp.9-10 'across all three setups') the conditional pin bar. The pin bar's
  76:         'position and close must support the breakout' is already guaranteed: the level was broken and closed beyond."""
  77:         if d is Direction.LONG:
  78:             return strong_bullish(c, self.p) or (self.p.orb_pin_bar_in_methods_1_2 and bullish_pin(c, self.p))
  79:         return strong_bearish(c, self.p) or (self.p.orb_pin_bar_in_methods_1_2 and bearish_pin(c, self.p))
  80: 
  81:     def _near_ma_value(self, ctx: SessionContext, t) -> float:
  82:         """The moving average for the Method-2 'near the MA' test. The structure trend reports the PREVIOUS session's EMA in
  83:         ``t.ma_value``; 'near the MA' concerns the EMA at the opening candle, so that mode uses today's first-candle EMA."""
  84:         if self.p.trend_mode in ("STRUCTURE_EMA_SWING2", "EMA_PREV_SESSION_CLOSE"):
  85:             return float(ctx.candles["ema200_5m"].iloc[0])
  86:         return t.ma_value
  87: 
  88:     def _trend_gate(self, ctx, c, d, method, levels, sat, fsm, props):
  89:         """Returns (record_or_None_to_stop, trend_result)."""
  90:         t = trend_check(ctx, 0, d.value, self.p.trend_mode, self.p)
  91:         props["trend_mode"] = self.p.trend_mode
  92:         if t.ok is None:
  93:             fsm.to(State.SETUP_INVALIDATED, c.end, f"trend not evaluable: {t.reason}")
  94:             return self._rec(ctx, c, method, d, levels, sat, [], ["ORB-TREND-001"], SignalStatus.NOT_EVALUATED, t.reason,
  95:                              fsm.trace, props), t
  96:         if not t.ok:
  97:             fsm.to(State.SETUP_INVALIDATED, c.end, f"trend filter failed: {t.reason}")
  98:             return self._rec(ctx, c, method, d, levels, sat, ["ORB-TREND-001", "ORB-TREND-002"], [], SignalStatus.INVALIDATED,
  99:                              f"TREND:{t.reason}", fsm.trace, props), t
 100:         return None, t
 101: 
 102:     # ------------------------------------------------------------------ Method 1
 103:     @implements("ORB-M1-LONG-001", "ORB-M1-LONG-002", "ORB-M1-LONG-003", "ORB-M1-SHORT-001", "ORB-M1-SHORT-002",
 104:                 "ORB-M1-SHORT-003", "ORB-TREND-001", "ORB-TREND-002", "ORB-GLOBAL-004")
 105:     def _method1(self, ctx: SessionContext, c: Candle, d: Direction) -> SignalRecord | None:
 106:         long = d is Direction.LONG
 107:         pre = "ORB-M1-LONG" if long else "ORB-M1-SHORT"
 108:         ph, pl = prev_high_low(ctx.previous, self.p)
 109:         level = ph if long else pl
 110:         broke = (c.h > level and c.c > level) if long else (c.l < level and c.c < level)
 111:         if not broke:
 112:             return None
 113:         levels = {**self._base_levels(ctx, c), "level_broken": level, "level_kind": "prev_day_high" if long else "prev_day_low"}
 114:         props = {"orb_prev_day_level_def": "PREV_DAY_HL", "strong_candle": self.p.strong_candle,
 115:                  "rejection_wick": self.p.rejection_wick}
 116:         fsm = SetupFSM(f"ORB M1 {d.value}")
 117:         fsm.to(State.SETUP_DETECTED, c.end, f"09:15 candle broke and closed beyond {level}")
 118:         sat = _G + [f"{pre}-001", f"{pre}-002", "ORB-GLOBAL-004"]
 119:         stop, _ = self._trend_gate(ctx, c, d, "Method 1", levels, sat, fsm, props)
 120:         if stop:
 121:             return stop
 122:         sat += ["ORB-TREND-001", "ORB-TREND-002"]
 123:         if not self._quality(c, d):
 124:             fsm.to(State.SETUP_INVALIDATED, c.end, "candle quality not strong")
 125:             return self._rec(ctx, c, "Method 1", d, levels, sat, [f"{pre}-003"], [], SignalStatus.INVALIDATED,
 126:                              "CANDLE_QUALITY(not a strong body / wick too large)", fsm.trace, props)
 127:         fsm.to(State.SIGNAL_CONFIRMED, c.end, "level broken, trend ok, candle strong")
 128:         return self._rec(ctx, c, "Method 1", d, levels, sat + [f"{pre}-003"], [], ["ORB-MA-001"], SignalStatus.CONFIRMED, None,
 129:                          fsm.trace, props)
 130: 
 131:     # ------------------------------------------------------------------ Method 2 (research variant)
 132:     @implements("ORB-M2-LONG-001", "ORB-M2-LONG-002", "ORB-M2-LONG-003", "ORB-M2-LONG-004", "ORB-M2-LONG-005",
 133:                 "ORB-M2-SHORT-001", "ORB-M2-SHORT-002", "ORB-M2-SHORT-003", "ORB-M2-SHORT-004")
 134:     def _method2(self, ctx: SessionContext, c: Candle, d: Direction) -> SignalRecord | None:
 135:         """RESEARCH VARIANT. Inner level = latest 5-candle fractal extreme of the previous session inside its
 136:         range; trendline = line through the last two previous-session fractal lows (long) / highs (short).
 137:         Neither construction is in the source documents."""
 138:         long = d is Direction.LONG
 139:         pre = "ORB-M2-LONG" if long else "ORB-M2-SHORT"
 140:         prev = ctx.previous
 141:         pcs = to_candles(prev_candles(prev, self.p))
 142:         n = len(pcs)
 143:         ph, pl = prev_high_low(prev, self.p)
 144:         if long:
 145:             piv = [j for j in pivot_highs(pcs, 0, n, 2) if pcs[j].h < ph]
 146:             lvl = pcs[piv[-1]].h if piv else None
 147:             tl_idx = pivot_lows(pcs, 0, n, 2)
 148:         else:
 149:             piv = [j for j in pivot_lows(pcs, 0, n, 2) if pcs[j].l > pl]
 150:             lvl = pcs[piv[-1]].l if piv else None
 151:             tl_idx = pivot_highs(pcs, 0, n, 2)
 152:         if lvl is None:
 153:             return None
 154:         broke = (c.h > lvl and c.c > lvl) if long else (c.l < lvl and c.c < lvl)
 155:         if not broke:
 156:             return None
 157:         levels = {**self._base_levels(ctx, c), "inner_level": lvl, "inner_level_def": "latest fractal(k=2) of previous session"}
 158:         props = {"orb_inner_level_def": "LATEST_FRACTAL_K2", "orb_trendline_def": "LAST_TWO_FRACTALS_K2"}
 159:         fsm = SetupFSM(f"ORB M2 {d.value}")
 160:         fsm.to(State.SETUP_DETECTED, c.end, f"09:15 candle broke and closed beyond inner level {lvl}")
 161:         sat = _G + [f"{pre}-002"]
 162:         unresolved = [f"{pre}-001"]
 163:         stop, t = self._trend_gate(ctx, c, d, "Method 2", levels, sat, fsm, props)
 164:         if stop:
 165:             stop.rule_ids_unresolved = unresolved
 166:             return stop
 167:         # trendline: rising (long) / falling (short) line through the last two fractals; price must be on the trend side
 168:         if len(tl_idx) < 2:
 169:             fsm.to(State.SETUP_INVALIDATED, c.end, "no trendline constructible")
 170:             return self._rec(ctx, c, "Method 2", d, levels, sat, [f"{pre}-001"], unresolved, SignalStatus.INVALIDATED,
 171:                              "NO_TRENDLINE", fsm.trace, props)
 172:         j1, j2 = tl_idx[-2], tl_idx[-1]
 173:         y1, y2 = (pcs[j1].l, pcs[j2].l) if long else (pcs[j1].h, pcs[j2].h)
 174:         slope = (y2 - y1) / (j2 - j1)
 175:         line_now = y2 + slope * (n - j2)  # candle 0 of today sits at index n of the concatenated sequence
 176:         levels["trendline_value_at_open"] = line_now
 177:         ok_dir = slope > 0 if long else slope < 0
 178:         on_side = c.c > line_now if long else c.c < line_now
 179:         if not (ok_dir and on_side):
 180:             fsm.to(State.SETUP_INVALIDATED, c.end, "trendline direction/side not supportive")
 181:             return self._rec(ctx, c, "Method 2", d, levels, sat, [f"{pre}-001"], unresolved, SignalStatus.INVALIDATED,
 182:                              "TRENDLINE_NOT_SUPPORTIVE", fsm.trace, props)
 183:         if not self._quality(c, d):
 184:             fsm.to(State.SETUP_INVALIDATED, c.end, "candle quality not strong")
 185:             return self._rec(ctx, c, "Method 2", d, levels, sat, [f"{pre}-003"], unresolved, SignalStatus.INVALIDATED,
 186:                              "CANDLE_QUALITY", fsm.trace, props)
 187:         ema = self._near_ma_value(ctx, t)
 188:         if not math.isnan(ema) and abs(c.c - ema) <= self.p.ma_near_band_points:
 189:             beyond = (c.c - ema) if long else (ema - c.c)
 190:             if beyond < self.p.ma_close_margin_points:
 191:                 fsm.to(State.SETUP_INVALIDATED, c.end, "near the MA without a convincing close")
 192:                 return self._rec(ctx, c, "Method 2", d, levels, sat, [f"{pre}-004"], unresolved, SignalStatus.INVALIDATED,
 193:                                  "NEAR_MA_NOT_CONVINCING", fsm.trace, {**props, "ma_near_band_points": self.p.ma_near_band_points})
 194:         fsm.to(State.SIGNAL_CONFIRMED, c.end, "inner level broken, trendline supportive, candle strong")
 195:         return self._rec(ctx, c, "Method 2", d, levels,
 196:                          sat + [f"{pre}-003", f"{pre}-004", "ORB-TREND-001", "ORB-TREND-002", f"{pre}-001"],
 197:                          [], unresolved + ["ORB-MA-001"], SignalStatus.CONFIRMED, None, fsm.trace, props)
 198: 
 199:     # ------------------------------------------------------------------ Gap + 200 MA
 200:     @implements("ORB-GAP-LONG-001", "ORB-GAP-LONG-002", "ORB-GAP-LONG-003", "ORB-GAP-LONG-004", "ORB-GAP-LONG-005",
 201:                 "ORB-GAP-SHORT-001", "ORB-GAP-SHORT-002", "ORB-GAP-SHORT-003", "ORB-GAP-SHORT-004", "ORB-MA-001")
 202:     def _gap_setup(self, ctx: SessionContext, c: Candle, d: Direction) -> SignalRecord | None:
 203:         long = d is Direction.LONG
 204:         pre = "ORB-GAP-LONG" if long else "ORB-GAP-SHORT"
 205:         g = gap_info(ctx, self.p)
 206:         if not g.evaluable or g.direction != ("UP" if long else "DOWN"):
 207:             return None
 208:         mode = self.p.ma_mode
 209:         ma = ma_value(ctx, 0, mode)
 210:         ma_prev = ctx.previous.ema_at_last_candle if mode == "EMA200_5M" else ma
 211:         levels = {**self._base_levels(ctx, c), "gap_points": g.points, "ma_mode": mode, "ma_value": ma, "ma_prev": ma_prev}
 212:         props = {"ma_mode": mode, "strong_candle": self.p.strong_candle, "pin_bar": self.p.pin_bar,
 213:                  "rejection_wick": self.p.rejection_wick, "gap_min_points": self.p.gap_min_points,
 214:                  "gap_max_points": self.p.gap_max_points}
 215:         fsm = SetupFSM(f"ORB GAP {d.value}")
 216:         sat = _G + [f"{pre}-001"]
 217:         if math.isnan(ma) or math.isnan(ma_prev):
 218:             fsm.to(State.SETUP_DETECTED, c.end, "gap in direction")
 219:             fsm.to(State.SETUP_INVALIDATED, c.end, "MA warm-up incomplete")
 220:             return self._rec(ctx, c, "Gap/200DMA", d, levels, sat, [], [f"{pre}-002"], SignalStatus.NOT_EVALUATED,
 221:                              f"MA_WARMUP({mode})", fsm.trace, props)
 222:         prev_close = ctx.previous.close_official
 223:         crossed = (prev_close < ma_prev and ctx.open_price > ma) if long else (prev_close > ma_prev and ctx.open_price < ma)
 224:         closed_beyond = c.c > ma if long else c.c < ma
 225:         if not crossed:
 226:             return None  # the gap did not push price through the MA: the special setup does not apply
 227:         fsm.to(State.SETUP_DETECTED, c.end, f"gap {g.points:+.2f} crosses MA {ma:.2f}")
 228:         sat.append(f"{pre}-002")
 229:         if not closed_beyond:
 230:             fsm.to(State.SETUP_INVALIDATED, c.end, "first candle did not close beyond the MA")
 231:             return self._rec(ctx, c, "Gap/200DMA", d, levels, sat, ["ORB-GAP-LONG-003" if long else f"{pre}-003"], ["ORB-MA-001"],
 232:                              SignalStatus.INVALIDATED, "CLOSE_NOT_BEYOND_MA", fsm.trace, props)
 233:         if long:
 234:             shape_ok = strong_bullish(c, self.p) or bullish_pin(c, self.p)
 235:             rejected = upper_rejection(c, self.p)  # with the default MODERATE rejection (33%) an owner-style pin's upper wick (<= 30%) never trips it; STRICT (25%) could
 236:         else:
 237:             shape_ok = strong_bearish(c, self.p) or bearish_pin(c, self.p)
 238:             rejected = lower_rejection(c, self.p)
 239:         qid = f"{pre}-004" if long else f"{pre}-003"
 240:         if not shape_ok or rejected:
 241:             fsm.to(State.SETUP_INVALIDATED, c.end, "candle quality / rejection wick")
 242:             return self._rec(ctx, c, "Gap/200DMA", d, levels, sat + ["ORB-GAP-LONG-003" if long else f"{pre}-003"], [qid],
 243:                              ["ORB-MA-001"], SignalStatus.INVALIDATED, "CANDLE_QUALITY_OR_REJECTION_WICK", fsm.trace, props)
 244:         ext_id = "ORB-GAP-LONG-005" if long else "ORB-GAP-SHORT-004"
 245:         if self.p.gap_max_points is not None and abs(g.points) > self.p.gap_max_points:
 246:             fsm.to(State.SETUP_INVALIDATED, c.end, "gap excessively extended (proposed cap)")
 247:             return self._rec(ctx, c, "Gap/200DMA", d, levels, sat, [ext_id], ["ORB-MA-001"], SignalStatus.INVALIDATED,
 248:                              "GAP_EXCEEDS_PROPOSED_CAP", fsm.trace, props)
 249:         fsm.to(State.SIGNAL_CONFIRMED, c.end, "gap crossed MA, close beyond, quality ok")
 250:         unresolved = ["ORB-MA-001"]
 251:         if self.p.gap_max_points is None:
 252:             unresolved.append(ext_id)  # mandatory 'not excessively extended' filter has no definition -> not applied
 253:         return self._rec(ctx, c, "Gap/200DMA", d, levels, sat + ["ORB-GAP-LONG-003" if long else f"{pre}-003", qid], [], unresolved,
 254:                          SignalStatus.CONFIRMED, None, fsm.trace, props)
```

## src/nifty_trading/strategies/orb_candidates.py

```python
   1: """Phase 5.4 (CANDIDATES, DISABLED BY DEFAULT): alternative constructions of the ORB Method 2 inner level and trendline.
   2: 
   3: The ORB rulebook (pp.4-7) defines Method 2 only in words and schematic / annotated charts: *the inner resistance (support) is a smaller level inside the previous day's range - a minor swing high or consolidation top - near
   4: a rising (falling) trendline through swing lows (highs)*; no algorithm is given (rules ORB-M2-*-001 are MISSING in the registry). The frozen engine (``orb.ORBStrategy._method2``) uses ONE research construction: the latest
   5: 5-candle fractal of the previous session inside its range, and a trendline through the last two previous-session fractal lows (highs). This module exposes the other deterministic readings of the same words as selectable
   6: variants so that their historical signal impact can be measured; NONE of them is source-defined or approved, and the default arguments reproduce the frozen engine exactly (asserted by a regression test over every session).
   7: 
   8:   inner_level_def  LATEST_FRACTAL_K2 (frozen) | HIGHEST_FRACTAL_K2 (the inner swing nearest the major level) | NEAREST_FRACTAL_FROM_OPEN_K2 (the first inner swing the price must cross from the open)
   9:                    | HIGHEST_BROKEN_FRACTAL_K2 (the most distant inner swing the first candle broke and closed beyond)
  10:   trendline_def    LAST_TWO_FRACTALS_K2 (frozen) | ANY_RISING_PAIR_OF_LAST_THREE_K2 (any two of the last three fractals) | NONE (the unresolved trendline condition is not applied: a diagnostic, not a proposal)
  11: 
  12:   gap_crossing_def OPEN_BEYOND_AVERAGE (frozen: the OPEN must already be beyond the 200 average) | CANDLE_CROSSES_AVERAGE (the first CANDLE may cross it: previous close on the wrong side, the candle closes beyond the
  13:                    average and its range reaches it). The rulebook's p.8 / p.9 schematics and the real gap-up chart on p.12 draw the candle opening on the old side of the average, crossing it and closing beyond; the text ('the gap
  14:                    must bring price above [the average]'; 'a candle that only crosses the line but closes below it does not qualify') does not settle it.
  15: 
  16: Everything else - Method 1, the trend gate, the strength gate, the near-EMA rule, the 09:20 timing, stops and targets - is the frozen code (inherited). The candidate overrides carry no ``@implements`` tags on purpose: they are research variants and
  17: must never be counted as implementers of the source rules. With the default arguments the produced records equal the frozen engine's records field for field (a regression test compares every record of every session).
  18: """
  19: 
  20: from __future__ import annotations
  21: 
  22: import math
  23: 
  24: from nifty_trading.data.sessions import SessionContext
  25: from nifty_trading.strategies.base import Direction, SetupFSM, SignalRecord, SignalStatus, State
  26: from nifty_trading.strategies.definitions import (
  27:     Candle,
  28:     bearish_pin,
  29:     bullish_pin,
  30:     gap_info,
  31:     lower_rejection,
  32:     ma_value,
  33:     pivot_highs,
  34:     pivot_lows,
  35:     prev_candles,
  36:     prev_high_low,
  37:     strong_bearish,
  38:     strong_bullish,
  39:     to_candles,
  40:     upper_rejection,
  41: )
  42: from nifty_trading.strategies.orb import _G, ORBStrategy
  43: 
  44: INNER_LEVEL_DEFS = ("LATEST_FRACTAL_K2", "HIGHEST_FRACTAL_K2", "NEAREST_FRACTAL_FROM_OPEN_K2", "HIGHEST_BROKEN_FRACTAL_K2")
  45: TRENDLINE_DEFS = ("LAST_TWO_FRACTALS_K2", "ANY_RISING_PAIR_OF_LAST_THREE_K2", "NONE")
  46: GAP_CROSSING_DEFS = ("OPEN_BEYOND_AVERAGE", "CANDLE_CROSSES_AVERAGE")
  47: 
  48: 
  49: def inner_levels(pcs: list[Candle], ph: float, pl: float, long: bool) -> list[float]:
  50:     """The k=2 fractal levels of the previous session lying INSIDE its range (long: swing highs below the day's high; short: swing lows above the day's low), oldest first."""
  51:     n = len(pcs)
  52:     if long:
  53:         return [pcs[j].h for j in pivot_highs(pcs, 0, n, 2) if pcs[j].h < ph]
  54:     return [pcs[j].l for j in pivot_lows(pcs, 0, n, 2) if pcs[j].l > pl]
  55: 
  56: 
  57: def select_inner_level(levels: list[float], c: Candle, long: bool, definition: str) -> float | None:
  58:     """The inner level the first candle ``c`` is tested against, or None when the definition yields no level."""
  59:     if not levels:
  60:         return None
  61:     if definition == "LATEST_FRACTAL_K2":
  62:         return levels[-1]
  63:     if definition == "HIGHEST_FRACTAL_K2":
  64:         return max(levels) if long else min(levels)
  65:     if definition == "NEAREST_FRACTAL_FROM_OPEN_K2":
  66:         ahead = [x for x in levels if (x > c.o if long else x < c.o)]
  67:         return (min(ahead) if long else max(ahead)) if ahead else None
  68:     if definition == "HIGHEST_BROKEN_FRACTAL_K2":
  69:         broken = [x for x in levels if ((c.h > x and c.c > x) if long else (c.l < x and c.c < x))]
  70:         return (max(broken) if long else min(broken)) if broken else None
  71:     raise ValueError(definition)
  72: 
  73: 
  74: def trendline_supportive(pcs: list[Candle], tl_idx: list[int], c: Candle, long: bool, definition: str) -> tuple[bool, str, float | None]:
  75:     """(supportive, reason, line value at the open). ``tl_idx`` are the previous session's fractal lows (long) / highs (short). The line value is the extrapolation to candle index n (today's first candle)."""
  76:     n = len(pcs)
  77:     if definition == "NONE":
  78:         return True, "TRENDLINE_NOT_APPLIED(diagnostic)", None
  79: 
  80:     def test(j1: int, j2: int) -> tuple[bool, float]:
  81:         y1, y2 = (pcs[j1].l, pcs[j2].l) if long else (pcs[j1].h, pcs[j2].h)
  82:         slope = (y2 - y1) / (j2 - j1)
  83:         line_now = y2 + slope * (n - j2)
  84:         ok_dir = slope > 0 if long else slope < 0
  85:         on_side = c.c > line_now if long else c.c < line_now
  86:         return bool(ok_dir and on_side), line_now
  87:     if definition == "LAST_TWO_FRACTALS_K2":
  88:         if len(tl_idx) < 2:
  89:             return False, "NO_TRENDLINE", None
  90:         ok, line = test(tl_idx[-2], tl_idx[-1])
  91:         return ok, "TRENDLINE_SUPPORTIVE" if ok else "TRENDLINE_NOT_SUPPORTIVE", line
  92:     if definition == "ANY_RISING_PAIR_OF_LAST_THREE_K2":
  93:         last3 = tl_idx[-3:]
  94:         if len(last3) < 2:
  95:             return False, "NO_TRENDLINE", None
  96:         pairs = [(last3[a], last3[b]) for a in range(len(last3)) for b in range(a + 1, len(last3))]
  97:         res = [test(j1, j2) for j1, j2 in pairs]
  98:         for ok, line in res:
  99:             if ok:
 100:                 return True, "TRENDLINE_SUPPORTIVE", line
 101:         return False, "TRENDLINE_NOT_SUPPORTIVE", res[-1][1]
 102:     raise ValueError(definition)
 103: 
 104: 
 105: class ORBCandidateStrategy(ORBStrategy):
 106:     """ORB with selectable Method 2 inner-level and trendline constructions (see the module docstring). With the default arguments it equals the frozen engine."""
 107: 
 108:     def __init__(self, name=None, params=None, proposals=None, trade=None, inner_level_def: str = "LATEST_FRACTAL_K2", trendline_def: str = "LAST_TWO_FRACTALS_K2", gap_crossing_def: str = "OPEN_BEYOND_AVERAGE"):
 109:         super().__init__(name, params, proposals, trade)
 110:         if inner_level_def not in INNER_LEVEL_DEFS or trendline_def not in TRENDLINE_DEFS or gap_crossing_def not in GAP_CROSSING_DEFS:
 111:             raise ValueError((inner_level_def, trendline_def, gap_crossing_def))
 112:         self.inner_level_def = inner_level_def
 113:         self.trendline_def = trendline_def
 114:         self.gap_crossing_def = gap_crossing_def
 115:         self._is_default = (inner_level_def, trendline_def, gap_crossing_def) == ("LATEST_FRACTAL_K2", "LAST_TWO_FRACTALS_K2", "OPEN_BEYOND_AVERAGE")
 116: 
 117:     # a copy of ORBStrategy._method2 in which ONLY the inner-level selection and the trendline test are replaced by the selectable definitions
 118:     def _method2(self, ctx: SessionContext, c: Candle, d: Direction) -> SignalRecord | None:
 119:         long = d is Direction.LONG
 120:         pre = "ORB-M2-LONG" if long else "ORB-M2-SHORT"
 121:         prev = ctx.previous
 122:         pcs = to_candles(prev_candles(prev, self.p))
 123:         n = len(pcs)
 124:         ph, pl = prev_high_low(prev, self.p)
 125:         lvl = select_inner_level(inner_levels(pcs, ph, pl, long), c, long, self.inner_level_def)
 126:         tl_idx = pivot_lows(pcs, 0, n, 2) if long else pivot_highs(pcs, 0, n, 2)
 127:         if lvl is None:
 128:             return None
 129:         broke = (c.h > lvl and c.c > lvl) if long else (c.l < lvl and c.c < lvl)
 130:         if not broke:
 131:             return None
 132:         levels = {**self._base_levels(ctx, c), "inner_level": lvl, "inner_level_def": "latest fractal(k=2) of previous session" if self.inner_level_def == "LATEST_FRACTAL_K2" else self.inner_level_def}
 133:         props = {"orb_inner_level_def": self.inner_level_def, "orb_trendline_def": self.trendline_def}
 134:         if not self._is_default:
 135:             props["phase54_candidate"] = True
 136:         fsm = SetupFSM(f"ORB M2 {d.value}")
 137:         fsm.to(State.SETUP_DETECTED, c.end, f"09:15 candle broke and closed beyond inner level {lvl}")
 138:         sat = _G + [f"{pre}-002"]
 139:         unresolved = [f"{pre}-001"]
 140:         stop, t = self._trend_gate(ctx, c, d, "Method 2", levels, sat, fsm, props)
 141:         if stop:
 142:             stop.rule_ids_unresolved = unresolved
 143:             return stop
 144:         ok, reason, line_now = trendline_supportive(pcs, tl_idx, c, long, self.trendline_def)
 145:         if line_now is not None:
 146:             levels["trendline_value_at_open"] = line_now
 147:         if not ok:
 148:             fsm.to(State.SETUP_INVALIDATED, c.end, "no trendline constructible" if reason == "NO_TRENDLINE" else "trendline direction/side not supportive")
 149:             return self._rec(ctx, c, "Method 2", d, levels, sat, [f"{pre}-001"], unresolved, SignalStatus.INVALIDATED, reason, fsm.trace, props)
 150:         if not self._quality(c, d):
 151:             fsm.to(State.SETUP_INVALIDATED, c.end, "candle quality not strong")
 152:             return self._rec(ctx, c, "Method 2", d, levels, sat, [f"{pre}-003"], unresolved, SignalStatus.INVALIDATED, "CANDLE_QUALITY", fsm.trace, props)
 153:         ema = self._near_ma_value(ctx, t)
 154:         if not math.isnan(ema) and abs(c.c - ema) <= self.p.ma_near_band_points:
 155:             beyond = (c.c - ema) if long else (ema - c.c)
 156:             if beyond < self.p.ma_close_margin_points:
 157:                 fsm.to(State.SETUP_INVALIDATED, c.end, "near the MA without a convincing close")
 158:                 return self._rec(ctx, c, "Method 2", d, levels, sat, [f"{pre}-004"], unresolved, SignalStatus.INVALIDATED, "NEAR_MA_NOT_CONVINCING", fsm.trace,
 159:                                  {**props, "ma_near_band_points": self.p.ma_near_band_points})
 160:         fsm.to(State.SIGNAL_CONFIRMED, c.end, "inner level broken, trendline supportive, candle strong")
 161:         return self._rec(ctx, c, "Method 2", d, levels, sat + [f"{pre}-003", f"{pre}-004", "ORB-TREND-001", "ORB-TREND-002", f"{pre}-001"], [], unresolved + ["ORB-MA-001"], SignalStatus.CONFIRMED, None, fsm.trace, props)
 162: 
 163:     # a copy of ORBStrategy._gap_setup in which ONLY the crossing condition differs (used when gap_crossing_def != OPEN_BEYOND_AVERAGE)
 164:     def _gap_setup(self, ctx: SessionContext, c: Candle, d: Direction) -> SignalRecord | None:
 165:         if self.gap_crossing_def == "OPEN_BEYOND_AVERAGE":
 166:             return super()._gap_setup(ctx, c, d)
 167:         long = d is Direction.LONG
 168:         pre = "ORB-GAP-LONG" if long else "ORB-GAP-SHORT"
 169:         g = gap_info(ctx, self.p)
 170:         if not g.evaluable or g.direction != ("UP" if long else "DOWN"):
 171:             return None
 172:         mode = self.p.ma_mode
 173:         ma = ma_value(ctx, 0, mode)
 174:         ma_prev = ctx.previous.ema_at_last_candle if mode == "EMA200_5M" else ma
 175:         levels = {**self._base_levels(ctx, c), "gap_points": g.points, "ma_mode": mode, "ma_value": ma, "ma_prev": ma_prev}
 176:         props = {"ma_mode": mode, "strong_candle": self.p.strong_candle, "pin_bar": self.p.pin_bar, "rejection_wick": self.p.rejection_wick, "gap_min_points": self.p.gap_min_points, "gap_max_points": self.p.gap_max_points,
 177:                  "gap_crossing_def": self.gap_crossing_def, "phase54_candidate": True}
 178:         fsm = SetupFSM(f"ORB GAP {d.value}")
 179:         sat = _G + [f"{pre}-001"]
 180:         if math.isnan(ma) or math.isnan(ma_prev):
 181:             fsm.to(State.SETUP_DETECTED, c.end, "gap in direction")
 182:             fsm.to(State.SETUP_INVALIDATED, c.end, "MA warm-up incomplete")
 183:             return self._rec(ctx, c, "Gap/200DMA", d, levels, sat, [], [f"{pre}-002"], SignalStatus.NOT_EVALUATED, f"MA_WARMUP({mode})", fsm.trace, props)
 184:         prev_close = ctx.previous.close_official
 185:         prev_wrong = prev_close < ma_prev if long else prev_close > ma_prev
 186:         open_beyond = ctx.open_price > ma if long else ctx.open_price < ma
 187:         reaches = (c.l <= ma) if long else (c.h >= ma)
 188:         crossed = prev_wrong and (open_beyond or reaches)  # the candle (not only the open) may cross the average
 189:         closed_beyond = c.c > ma if long else c.c < ma
 190:         if not crossed:
 191:             return None
 192:         fsm.to(State.SETUP_DETECTED, c.end, f"gap {g.points:+.2f} crosses MA {ma:.2f}")
 193:         sat.append(f"{pre}-002")
 194:         if not closed_beyond:
 195:             fsm.to(State.SETUP_INVALIDATED, c.end, "first candle did not close beyond the MA")
 196:             return self._rec(ctx, c, "Gap/200DMA", d, levels, sat, ["ORB-GAP-LONG-003" if long else f"{pre}-003"], ["ORB-MA-001"], SignalStatus.INVALIDATED, "CLOSE_NOT_BEYOND_MA", fsm.trace, props)
 197:         if long:
 198:             shape_ok = strong_bullish(c, self.p) or bullish_pin(c, self.p)
 199:             rejected = upper_rejection(c, self.p)
 200:         else:
 201:             shape_ok = strong_bearish(c, self.p) or bearish_pin(c, self.p)
 202:             rejected = lower_rejection(c, self.p)
 203:         qid = f"{pre}-004" if long else f"{pre}-003"
 204:         if not shape_ok or rejected:
 205:             fsm.to(State.SETUP_INVALIDATED, c.end, "candle quality / rejection wick")
 206:             return self._rec(ctx, c, "Gap/200DMA", d, levels, sat + ["ORB-GAP-LONG-003" if long else f"{pre}-003"], [qid], ["ORB-MA-001"], SignalStatus.INVALIDATED, "CANDLE_QUALITY_OR_REJECTION_WICK", fsm.trace, props)
 207:         ext_id = "ORB-GAP-LONG-005" if long else "ORB-GAP-SHORT-004"
 208:         if self.p.gap_max_points is not None and abs(g.points) > self.p.gap_max_points:
 209:             fsm.to(State.SETUP_INVALIDATED, c.end, "gap excessively extended (proposed cap)")
 210:             return self._rec(ctx, c, "Gap/200DMA", d, levels, sat, [ext_id], ["ORB-MA-001"], SignalStatus.INVALIDATED, "GAP_EXCEEDS_PROPOSED_CAP", fsm.trace, props)
 211:         fsm.to(State.SIGNAL_CONFIRMED, c.end, "gap crossed MA, close beyond, quality ok")
 212:         unresolved = ["ORB-MA-001"]
 213:         if self.p.gap_max_points is None:
 214:             unresolved.append(ext_id)
 215:         return self._rec(ctx, c, "Gap/200DMA", d, levels, sat + ["ORB-GAP-LONG-003" if long else f"{pre}-003", qid], [], unresolved, SignalStatus.CONFIRMED, None, fsm.trace, props)
```

## src/nifty_trading/strategies/orb_colour.py

```python
   1: """Phase 5.1 (opt-in research variant, NOT part of the frozen baseline): ORB with the author's colour clarification.
   2: 
   3: Author (handwritten corrections, Phase 5.1, AC27, 2025-11-27): "ORB is activated on a red candle for long side, which is wrong. ORB for long should be in green closing."
   4: The frozen ORB engine admits a bearish first candle for a long through the conditional PIN-BAR alternative (its own explanation for 20251127-1-ORB says: "the candle is bearish, i.e. against the trade direction; the
   5: pin route accepts it because the level break and close beyond it carry the direction").
   6: 
   7: ``ORBColourStrategy`` = the frozen ``ORBStrategy`` unchanged, plus ONE post-condition applied to every CONFIRMED ORB record (all three setups): a LONG needs a green first candle (close > open); by the existing
   8: mirror rule ORB-GLOBAL-002 ("same rules in both directions") a SHORT needs a red first candle (close < open). A confirmed record that fails is returned as INVALIDATED with the reason
   9: ``FIRST_CANDLE_COLOUR_AGAINST_DIRECTION``; nothing else (levels, trend filter, strength thresholds, stop, target) is touched. The frozen module ``orb.py`` is not edited: the baseline stays byte-identical and this class is
  10: used only by an explicit Phase 5.1 configuration (``research/phase51.py``).
  11: """
  12: 
  13: from __future__ import annotations
  14: 
  15: from nifty_trading.strategies.base import Direction, SignalStatus
  16: from nifty_trading.strategies.orb import ORBStrategy
  17: 
  18: REASON = "FIRST_CANDLE_COLOUR_AGAINST_DIRECTION"
  19: RULE_NOTE = "AUTHOR_CLARIFICATION_PHASE51_AC27: ORB long needs a green close; short (mirror, ORB-GLOBAL-002) a red close"
  20: 
  21: 
  22: def colour_ok(direction: str, open_: float | None, close: float | None) -> bool:
  23:     if open_ is None or close is None:
  24:         return False
  25:     return close > open_ if direction == Direction.LONG.value else close < open_
  26: 
  27: 
  28: class ORBColourStrategy(ORBStrategy):
  29:     """ORBStrategy + the colour post-condition (see the module docstring)."""
  30: 
  31:     def _scan(self, ctx, cs, gap_before):  # noqa: ANN001 - signature of the frozen engine
  32:         out = []
  33:         for r in super()._scan(ctx, cs, gap_before):
  34:             if r.signal_status == SignalStatus.CONFIRMED.value and not colour_ok(r.direction, r.signal_candle_open, r.signal_candle_close):
  35:                 r.signal_status = SignalStatus.INVALIDATED.value
  36:                 r.invalidation_reason = REASON
  37:                 r.rule_ids_failed = list(r.rule_ids_failed) + ["AUTHOR-PHASE51-ORB-COLOUR"]
  38:                 r.state_trace = list(r.state_trace) + [f"{r.signal_candle_start:%H:%M} SIGNAL_CONFIRMED->SETUP_INVALIDATED: {RULE_NOTE}"]
  39:                 r.flags = list(r.flags) + ["PHASE51_COLOUR_RULE_APPLIED"]
  40:             out.append(r)
  41:         return out
```

## src/nifty_trading/strategies/base.py

```python
   1: """Signal records, setup state machine and the BaseStrategy-compatible engine base class.
   2: 
   3: Signal detection only. A :class:`SignalRecord` is never a fill: it carries the candle on which the
   4: documented trigger completed and a *reference* price (that candle's close). Stop/target/quantity
   5: live in ``nifty_trading.core.exit_policy`` and are applied downstream.
   6: """
   7: 
   8: from __future__ import annotations
   9: 
  10: import math
  11: from abc import abstractmethod
  12: from dataclasses import asdict, dataclass, field
  13: from datetime import date, datetime
  14: from enum import Enum
  15: from typing import Any
  16: 
  17: import pandas as pd
  18: 
  19: from nifty_trading.core.execution_eligibility import classify_bar
  20: from nifty_trading.core.strategy import BaseStrategy, Signal, SignalType, StrategyContext
  21: from nifty_trading.data.sessions import SessionContext, build_session_contexts
  22: from nifty_trading.strategies.definitions import Candle, to_candles
  23: from nifty_trading.strategies.params import (
  24:     DEFAULT_PROPOSALS,
  25:     DEFAULT_TRADE,
  26:     T2_CONFLICTS,
  27:     ProposalConfig,
  28:     TradeConfig,
  29: )
  30: from nifty_trading.strategies.rule_data import IMPL_P, IMPL_R, NOT, VE
  31: from nifty_trading.strategies.rules import RULE_BY_ID, implements
  32: 
  33: INSTRUMENT = "NIFTY 50 (index, not directly tradable; points are synthetic)"
  34: 
  35: 
  36: class Direction(str, Enum):
  37:     LONG = "LONG"
  38:     SHORT = "SHORT"
  39: 
  40: 
  41: class SignalStatus(str, Enum):
  42:     CONFIRMED = "CONFIRMED"
  43:     INVALIDATED = "INVALIDATED"
  44:     INCOMPLETE_AT_EOD = "INCOMPLETE_AT_EOD"
  45:     NOT_EVALUATED = "NOT_EVALUATED"
  46: 
  47: 
  48: class VerificationStatus(str, Enum):
  49:     VERIFIED = "VERIFIED"  # every satisfied rule is VERIFIED_EXPLICIT; nothing unresolved
  50:     PROPOSAL_DEPENDENT = "PROPOSAL_DEPENDENT"  # relies on a PROPOSED_FOR_REVIEW interpretation
  51:     RESEARCH_VARIANT = "RESEARCH_VARIANT"  # relies on a rule the documents do not define (labelled variant)
  52:     NOT_READY = "NOT_READY"  # could not be evaluated / blocked
  53: 
  54: 
  55: class State(str, Enum):
  56:     WAITING_FOR_SETUP = "WAITING_FOR_SETUP"
  57:     SETUP_DETECTED = "SETUP_DETECTED"
  58:     WAITING_FOR_CONFIRMATION = "WAITING_FOR_CONFIRMATION"
  59:     SIGNAL_CONFIRMED = "SIGNAL_CONFIRMED"
  60:     SETUP_INVALIDATED = "SETUP_INVALIDATED"
  61: 
  62: 
  63: _ALLOWED = {
  64:     State.WAITING_FOR_SETUP: {State.SETUP_DETECTED},
  65:     State.SETUP_DETECTED: {State.WAITING_FOR_CONFIRMATION, State.SIGNAL_CONFIRMED, State.SETUP_INVALIDATED},
  66:     State.WAITING_FOR_CONFIRMATION: {State.SIGNAL_CONFIRMED, State.SETUP_INVALIDATED},
  67:     State.SIGNAL_CONFIRMED: set(),
  68:     State.SETUP_INVALIDATED: set(),
  69: }
  70: 
  71: 
  72: class IllegalTransition(RuntimeError):
  73:     pass
  74: 
  75: 
  76: class SetupFSM:
  77:     """One setup attempt. Chronology is enforced: transitions must not go backwards in time."""
  78: 
  79:     def __init__(self, label: str):
  80:         self.label = label
  81:         self.state = State.WAITING_FOR_SETUP
  82:         self.trace: list[str] = []
  83:         self._last_t: datetime | None = None
  84: 
  85:     def to(self, new: State, t: datetime, why: str) -> None:
  86:         if new not in _ALLOWED[self.state]:
  87:             raise IllegalTransition(f"{self.label}: {self.state.value} -> {new.value} ({why})")
  88:         if self._last_t is not None and t < self._last_t:
  89:             raise IllegalTransition(f"{self.label}: event at {t} precedes previous event at {self._last_t}")
  90:         self._last_t = t
  91:         self.trace.append(f"{t:%H:%M} {self.state.value}->{new.value}: {why}")
  92:         self.state = new
  93: 
  94:     @property
  95:     def terminal(self) -> bool:
  96:         return self.state in (State.SIGNAL_CONFIRMED, State.SETUP_INVALIDATED)
  97: 
  98: 
  99: @dataclass
 100: class SignalRecord:
 101:     strategy: str
 102:     method: str
 103:     direction: str
 104:     signal_date: date
 105:     signal_timestamp: datetime | None  # bar_end of the trigger candle = earliest actionable time
 106:     signal_candle_start: datetime | None
 107:     signal_candle_open: float | None
 108:     signal_candle_high: float | None
 109:     signal_candle_low: float | None
 110:     signal_candle_close: float | None
 111:     reference_levels: dict[str, Any]
 112:     rule_ids_satisfied: list[str]
 113:     rule_ids_failed: list[str]
 114:     signal_status: str
 115:     invalidation_reason: str | None
 116:     verification_status: str  # for a record that is NOT a CONFIRMED signal this only describes the rules satisfied before the setup ended; it carries no signal meaning (see execution_config.entry_rule_status)
 117:     rule_ids_unresolved: list[str] = field(default_factory=list)
 118:     proposals_used: dict[str, Any] = field(default_factory=dict)
 119:     state_trace: list[str] = field(default_factory=list)
 120:     flags: list[str] = field(default_factory=list)
 121:     concurrent_methods: list[str] = field(default_factory=list)
 122:     reference_price_is_fill: bool = False  # always False: a signal is not a filled trade
 123:     instrument: str = INSTRUMENT
 124:     execution_config: dict[str, Any] = field(default_factory=dict)  # which rule configuration produced this signal (Phase 2.2)
 125: 
 126:     def to_dict(self) -> dict[str, Any]:
 127:         return asdict(self)
 128: 
 129: 
 130: def verification_for(satisfied: list[str], unresolved: list[str]) -> VerificationStatus:
 131:     """Never reports VERIFIED when any satisfied rule rests on a proposal or any mandatory rule is unresolved."""
 132:     if any(RULE_BY_ID[r]["implementation_status"] == IMPL_R for r in list(satisfied) + list(unresolved)):
 133:         return VerificationStatus.RESEARCH_VARIANT
 134:     if unresolved:
 135:         return VerificationStatus.PROPOSAL_DEPENDENT
 136:     needs_proposal = any(
 137:         RULE_BY_ID[r]["classification"] != VE or RULE_BY_ID[r]["implementation_status"] in (IMPL_P, NOT)
 138:         for r in satisfied
 139:     )
 140:     return VerificationStatus.PROPOSAL_DEPENDENT if needs_proposal else VerificationStatus.VERIFIED
 141: 
 142: 
 143: class SignalEngine(BaseStrategy):
 144:     """Base class: ``evaluate_session`` -> structured signals; ``on_candle`` adapts to BaseStrategy."""
 145: 
 146:     STRATEGY = ""
 147:     METHODS: tuple[str, ...] = ()
 148:     REQUIRES_PREVIOUS_SESSION = False
 149:     TREND_METHODS: tuple[str, ...] = ()  # methods that apply the trend_mode proposal ("*" = all); others report NOT_APPLICABLE
 150: 
 151:     def __init__(self, name: str | None = None, params: dict[str, Any] | None = None,
 152:                  proposals: ProposalConfig | None = None, trade: TradeConfig | None = None):
 153:         super().__init__(name or self.STRATEGY, params)
 154:         self.p = proposals or DEFAULT_PROPOSALS
 155:         self.trade = trade or DEFAULT_TRADE
 156: 
 157:     # ---------------------------------------------------------------- public API
 158:     @implements("DATA-TIME-001")
 159:     def evaluate_session(self, ctx: SessionContext) -> list[SignalRecord]:
 160:         block = self._precheck(ctx)
 161:         if block:
 162:             return [self._blocked(ctx, block)]
 163:         cs = to_candles(ctx.candles)
 164:         if not cs:
 165:             return [self._blocked(ctx, "NO_COMPLETE_5M_CANDLES")]
 166:         gap_before = [False] + [cs[k].start != cs[k - 1].end for k in range(1, len(cs))]
 167:         out = self._scan(ctx, cs, gap_before)
 168:         cutoff = self.p.signal_window_end
 169:         if cutoff:
 170:             out = [r for r in out if r.signal_status != SignalStatus.CONFIRMED.value
 171:                    or r.signal_timestamp is None or f"{r.signal_timestamp:%H:%M}" <= cutoff]
 172:         self._mark_concurrent(out)
 173:         return out
 174: 
 175:     @abstractmethod
 176:     def _scan(self, ctx: SessionContext, cs: list[Candle], gap_before: list[bool]) -> list[SignalRecord]: ...
 177: 
 178:     # ---------------------------------------------------------------- helpers
 179:     @implements("DATA-QUAL-001")
 180:     def _precheck(self, ctx: SessionContext) -> str | None:
 181:         if not ctx.info.usable:
 182:             return f"SESSION_NOT_EVALUABLE:{ctx.info.quality.value}:{ctx.info.status.value}" + (
 183:                 f"({'; '.join(ctx.info.reasons)})" if ctx.info.reasons else "")
 184:         if self.REQUIRES_PREVIOUS_SESSION:
 185:             if ctx.previous is None:
 186:                 return "NO_PREVIOUS_SESSION_IN_DATASET"
 187:             if ctx.previous.gap_to_this_session_unverified and not self.p.allow_unverified_prev_session:
 188:                 why = "; ".join(f for f in ctx.data_flags if f.startswith("PREV")) or "previous session not verifiable"
 189:                 return f"PREV_SESSION_UNVERIFIED({why})"
 190:         return None
 191: 
 192:     def exec_config(self, method: str, status: str, execution: str, signal_ts: datetime | None = None) -> dict[str, Any]:
 193:         """The rule configuration that produced a signal. Never says VERIFIED just because some components are verified:
 194:         ``entry_rule_status`` is VERIFIED_EXPLICIT only when every satisfied rule is explicit and nothing is unresolved."""
 195:         t, st = self.trade, self.STRATEGY
 196:         uses_trend = "*" in self.TREND_METHODS or method in self.TREND_METHODS
 197:         return {
 198:             "strategy": st, "method": method, "entry_rule_status": status,
 199:             "stop_distance": t.stop_points(st), "stop_variant": t.stop_variant, "stop_status": t.stop_status(st) if t.stop_points(st) is not None else "UNRESOLVED",
 200:             "target_1": t.t1_points, "target_2": t.t2_points(st), "target_2_status": t.t2_status(st),
 201:             "target_2_conflict": T2_CONFLICTS.get(st),
 202:             "proposal_config": self.p.to_dict(),  # every PROPOSED_FOR_REVIEW setting in force: two signals under different settings are distinguishable
 203:             "trade_config": asdict(t),
 204:             "trend_mode": self.p.trend_mode if uses_trend else "NOT_APPLICABLE",
 205:             "fill_convention": "NEXT_1M_BAR_OPEN_AFTER_SIGNAL_CANDLE (PROPOSED; the reference price is not a fill)",
 206:             "execution_status": execution,
 207:         }
 208: 
 209:     def _execution_status(self, signal_ts: datetime | None) -> str:
 210:         if signal_ts is None:
 211:             return "NOT_EVALUATED"
 212:         return "RESEARCH_ONLY" if classify_bar(signal_ts).value == "CONTINUOUS" else "ENTRY_BLOCKED_" + classify_bar(signal_ts).value
 213: 
 214:     def _blocked(self, ctx: SessionContext, reason: str, method: str = "ALL") -> SignalRecord:
 215:         return SignalRecord(
 216:             strategy=self.STRATEGY, method=method, direction=self._default_direction(), signal_date=ctx.date,
 217:             signal_timestamp=None, signal_candle_start=None, signal_candle_open=None, signal_candle_high=None,
 218:             signal_candle_low=None, signal_candle_close=None, reference_levels={}, rule_ids_satisfied=[],
 219:             rule_ids_failed=[], signal_status=SignalStatus.NOT_EVALUATED.value, invalidation_reason=reason,
 220:             verification_status=VerificationStatus.NOT_READY.value, flags=list(ctx.data_flags),
 221:             execution_config=self.exec_config(method, VerificationStatus.NOT_READY.value, "NOT_EVALUATED"),
 222:         )
 223: 
 224:     def _default_direction(self) -> str:
 225:         return Direction.SHORT.value
 226: 
 227:     def _rec(self, ctx: SessionContext, c: Candle, method: str, direction: Direction, levels: dict[str, Any],
 228:              satisfied: list[str], failed: list[str] | None = None, unresolved: list[str] | None = None,
 229:              status: SignalStatus = SignalStatus.CONFIRMED, why: str | None = None,
 230:              trace: list[str] | None = None, proposals: dict[str, Any] | None = None,
 231:              flags: list[str] | None = None) -> SignalRecord:
 232:         unresolved = unresolved or []
 233:         sat = list(dict.fromkeys(satisfied))
 234:         if status is SignalStatus.CONFIRMED:
 235:             ver = verification_for(sat, unresolved)
 236:         else:
 237:             ver = VerificationStatus.NOT_READY if status is SignalStatus.NOT_EVALUATED else verification_for(sat, unresolved)
 238:         return SignalRecord(
 239:             strategy=self.STRATEGY, method=method, direction=direction.value, signal_date=ctx.date,
 240:             signal_timestamp=c.end, signal_candle_start=c.start, signal_candle_open=c.o, signal_candle_high=c.h,
 241:             signal_candle_low=c.l, signal_candle_close=c.c, reference_levels=_clean(levels),
 242:             rule_ids_satisfied=sat, rule_ids_failed=failed or [], signal_status=status.value,
 243:             invalidation_reason=why, verification_status=ver.value, rule_ids_unresolved=unresolved,
 244:             proposals_used=proposals or {}, state_trace=trace or [], flags=list(ctx.data_flags) + (flags or []),
 245:             execution_config=self.exec_config(
 246:                 method, ({"VERIFIED": "VERIFIED_EXPLICIT"}.get(ver.value, ver.value) if status is SignalStatus.CONFIRMED else "NOT_A_CONFIRMED_SIGNAL"),
 247:                 self._execution_status(c.end) if status is SignalStatus.CONFIRMED else "NOT_A_CONFIRMED_SIGNAL"),
 248:         )
 249: 
 250:     @staticmethod
 251:     def _mark_concurrent(recs: list[SignalRecord]) -> None:
 252:         confirmed = [r for r in recs if r.signal_status == SignalStatus.CONFIRMED.value]
 253:         for r in confirmed:
 254:             r.concurrent_methods = sorted(o.method for o in confirmed
 255:                                           if o is not r and o.signal_timestamp == r.signal_timestamp
 256:                                           and o.direction == r.direction)
 257: 
 258:     # ---------------------------------------------------------------- BaseStrategy adapter
 259:     def on_candle(self, context: StrategyContext) -> list[Signal]:
 260:         """Emit newly confirmed signals when the 1-minute row just received completes a 5m candle.
 261: 
 262:         ``historical_candles`` must hold 1-minute rows up to and including ``current_time`` only;
 263:         rows after ``current_time`` are discarded here as a look-ahead guard. This adapter rebuilds
 264:         contexts from history and is meant for correctness, not speed.
 265:         """
 266:         hist = context.historical_candles
 267:         now = pd.Timestamp(context.current_time)
 268:         hist = hist[hist["timestamp"] <= now]
 269:         minute_of_day = now.hour * 60 + now.minute
 270:         if (minute_of_day - (9 * 60 + 15)) % 5 != 4:
 271:             return []
 272:         ctxs, _ = build_session_contexts(hist)
 273:         today = now.date()
 274:         if today not in ctxs:
 275:             return []
 276:         bar_end = now + pd.Timedelta(minutes=1)
 277:         out: list[Signal] = []
 278:         for r in self.evaluate_session(ctxs[today]):
 279:             if r.signal_status == SignalStatus.CONFIRMED.value and r.signal_timestamp == bar_end:
 280:                 out.append(Signal(
 281:                     strategy_id=self.name, instrument="NIFTY 50", timestamp=r.signal_timestamp,
 282:                     signal_type=SignalType.SELL if r.direction == Direction.SHORT.value else SignalType.BUY,
 283:                     price=r.signal_candle_close, stop_loss=None, target=None, metadata=r.to_dict(),
 284:                 ))
 285:         return out
 286: 
 287: 
 288: def _clean(d: dict[str, Any]) -> dict[str, Any]:
 289:     return {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in d.items()}
```

## src/nifty_trading/strategies/definitions.py

```python
   1: """Mathematical definitions shared by the strategy engines.
   2: 
   3: Every function takes only data that is known at the evaluation candle (indices <= i, or <= i-1
   4: where the docstring says so). No function receives future candles by construction: callers pass
   5: ``candles`` and an index, and functions never read beyond ``upto``.
   6: 
   7: Anything depending on a threshold uses :class:`ProposalConfig` and is PROPOSED_FOR_REVIEW.
   8: """
   9: 
  10: from __future__ import annotations
  11: 
  12: import math
  13: from dataclasses import dataclass
  14: from datetime import datetime
  15: from typing import NamedTuple
  16: 
  17: import pandas as pd
  18: 
  19: from nifty_trading.data.sessions import PreviousSession, SessionContext
  20: from nifty_trading.strategies.params import DEFAULT_PROPOSALS, M3_WICK_SHARE_BAND, ProposalConfig
  21: from nifty_trading.strategies.rules import implements
  22: 
  23: EPS = 1e-9  # tolerance for threshold comparisons: prices ~24,000 on a 0.05 grid carry ~4e-12 of float error, so exact-boundary candles must not flip
  24: 
  25: 
  26: class Candle(NamedTuple):
  27:     start: datetime  # bar_start
  28:     end: datetime  # bar_end = first moment the candle may be used
  29:     o: float
  30:     h: float
  31:     l: float
  32:     c: float
  33:     ema: float  # EMA(200) of 5m closes incl. this candle; NaN while warming up
  34: 
  35: 
  36: def to_candles(df: pd.DataFrame) -> list[Candle]:
  37:     ema = df["ema200_5m"].to_numpy() if "ema200_5m" in df else [math.nan] * len(df)
  38:     return [Candle(r.bar_start, r.bar_end, float(r.open), float(r.high), float(r.low), float(r.close), float(e))
  39:             for r, e in zip(df.itertuples(index=False), ema, strict=True)]
  40: 
  41: 
  42: # ------------------------------------------------------------------ candle geometry
  43: def body(c: Candle) -> float:
  44:     return abs(c.c - c.o)
  45: 
  46: 
  47: def rng(c: Candle) -> float:
  48:     return c.h - c.l
  49: 
  50: 
  51: def upper_wick(c: Candle) -> float:
  52:     return c.h - max(c.o, c.c)
  53: 
  54: 
  55: def lower_wick(c: Candle) -> float:
  56:     return min(c.o, c.c) - c.l
  57: 
  58: 
  59: def _ratio(x: float, c: Candle) -> float:
  60:     r = rng(c)
  61:     return 0.0 if r <= 0.0 else x / r  # zero-range candle: every ratio is 0 and no shape qualifies
  62: 
  63: 
  64: def body_ratio(c: Candle) -> float:
  65:     return _ratio(body(c), c)
  66: 
  67: 
  68: def upper_ratio(c: Candle) -> float:
  69:     return _ratio(upper_wick(c), c)
  70: 
  71: 
  72: def lower_ratio(c: Candle) -> float:
  73:     return _ratio(lower_wick(c), c)
  74: 
  75: 
  76: @implements("IRF-DEF-001")
  77: def is_green(c: Candle) -> bool:
  78:     return c.c > c.o
  79: 
  80: 
  81: @implements("IRF-DEF-001")
  82: def is_red(c: Candle) -> bool:
  83:     return c.c < c.o
  84: 
  85: 
  86: @implements("ORB-M1-LONG-003", "ORB-M2-LONG-003", "ORB-CANDLE-001")
  87: def strong_bullish(c: Candle, p: ProposalConfig) -> bool:
  88:     """PROPOSED: green, body >= x of range, upper (opposite) wick <= y of range."""
  89:     t = p.strong
  90:     return (rng(c) > 0 and is_green(c) and body_ratio(c) >= t["body_ratio_min"] - EPS
  91:             and upper_ratio(c) <= t["opposite_wick_ratio_max"] + EPS)
  92: 
  93: 
  94: @implements("ORB-M1-SHORT-003", "ORB-M2-SHORT-003", "PDS-M1-001", "ORB-CANDLE-001")
  95: def strong_bearish(c: Candle, p: ProposalConfig) -> bool:
  96:     t = p.strong
  97:     return (rng(c) > 0 and is_red(c) and body_ratio(c) >= t["body_ratio_min"] - EPS
  98:             and lower_ratio(c) <= t["opposite_wick_ratio_max"] + EPS)
  99: 
 100: 
 101: def _pin(c: Candle, p: ProposalConfig, lower: bool) -> bool:
 102:     """Pin bar rejecting lower prices (``lower``=True: long lower wick) or higher prices. Two PROPOSED encodings:
 103:     ratio style (wick/body/opposite-wick shares of the range) or the owner's style (wick >= k x body AND the close inside
 104:     the favourable ``close_fraction_max`` of the range)."""
 105:     r = rng(c)
 106:     if r <= 0:
 107:         return False
 108:     t = p.pin
 109:     wick = lower_wick(c) if lower else upper_wick(c)
 110:     if "wick_to_body_min" in t:
 111:         if wick <= EPS or wick < t["wick_to_body_min"] * body(c) - EPS:
 112:             return False
 113:         dist_from_favourable_extreme = (c.h - c.c) if lower else (c.c - c.l)  # bullish: close near the high; bearish: near the low
 114:         return dist_from_favourable_extreme <= t["close_fraction_max"] * r + EPS
 115:     opp = upper_ratio(c) if lower else lower_ratio(c)
 116:     return (_ratio(wick, c) >= t["wick_ratio_min"] - EPS and body_ratio(c) <= t["body_ratio_max"] + EPS
 117:             and opp <= t["opposite_wick_ratio_max"] + EPS)
 118: 
 119: 
 120: @implements("ORB-GAP-LONG-004", "ORB-CANDLE-001", "CANDLE-DEF-001")
 121: def bullish_pin(c: Candle, p: ProposalConfig) -> bool:
 122:     """PROPOSED: long LOWER wick (rejection of lower prices) with the close in the favourable part of the range."""
 123:     return _pin(c, p, lower=True)
 124: 
 125: 
 126: @implements("PDS-M2-001", "ORB-GAP-SHORT-003", "ORB-CANDLE-001", "CANDLE-DEF-001")
 127: def bearish_pin(c: Candle, p: ProposalConfig) -> bool:
 128:     """PROPOSED higher-price-rejection pin bar. Colour is checked by the caller where the rule demands red."""
 129:     return _pin(c, p, lower=False)
 130: 
 131: 
 132: @implements("CANDLE-DEF-001")
 133: def is_small(c: Candle, p: ProposalConfig) -> bool:
 134:     """PROPOSED small candle: body <= 30% of its range (a zero-range candle is small)."""
 135:     r = rng(c)
 136:     return True if r <= 0 else body(c) <= p.small_candle_body_ratio_max * r + EPS
 137: 
 138: 
 139: def upper_rejection(c: Candle, p: ProposalConfig) -> bool:
 140:     return rng(c) > 0 and upper_ratio(c) >= p.reject["wick_ratio_min"] - EPS
 141: 
 142: 
 143: def lower_rejection(c: Candle, p: ProposalConfig) -> bool:
 144:     return rng(c) > 0 and lower_ratio(c) >= p.reject["wick_ratio_min"] - EPS
 145: 
 146: 
 147: # ------------------------------------------------------------------ swings and levels
 148: def _pivot_low(cs: list[Candle], j: int, k: int) -> bool:
 149:     return all(cs[j].l <= cs[j - m].l and cs[j].l <= cs[j + m].l for m in range(1, k + 1))
 150: 
 151: 
 152: def _pivot_high(cs: list[Candle], j: int, k: int) -> bool:
 153:     return all(cs[j].h >= cs[j - m].h and cs[j].h >= cs[j + m].h for m in range(1, k + 1))
 154: 
 155: 
 156: def pivot_lows(cs: list[Candle], lo: int, i: int, k: int) -> list[int]:
 157:     """Indices j in [lo, i-1-k] that are k-fractal lows. Confirmation needs candles up to j+k <= i-1."""
 158:     return [j for j in range(max(lo, k), i - k) if _pivot_low(cs, j, k)]
 159: 
 160: 
 161: def pivot_highs(cs: list[Candle], lo: int, i: int, k: int) -> list[int]:
 162:     return [j for j in range(max(lo, k), i - k) if _pivot_high(cs, j, k)]
 163: 
 164: 
 165: @implements("TREND-SWING-001")
 166: def confirmed_swing_highs(cs: list[Candle], upto: int, k: int = 2, lo: int = 0) -> list[int]:
 167:     """Indices j of swing highs KNOWN once candle ``upto`` (inclusive) has closed: ``high[j]`` is strictly greater than the highs of the
 168:     k candles before and the k candles after it. A swing at j is confirmed only when candle j+k has closed, so j <= upto - k."""
 169:     return [j for j in range(max(lo, k), upto - k + 1)
 170:             if all(cs[j].h > cs[j - m].h and cs[j].h > cs[j + m].h for m in range(1, k + 1))]
 171: 
 172: 
 173: @implements("TREND-SWING-001")
 174: def confirmed_swing_lows(cs: list[Candle], upto: int, k: int = 2, lo: int = 0) -> list[int]:
 175:     return [j for j in range(max(lo, k), upto - k + 1)
 176:             if all(cs[j].l < cs[j - m].l and cs[j].l < cs[j + m].l for m in range(1, k + 1))]
 177: 
 178: 
 179: @implements("IRF-M2A-001", "IRF-M3-004")
 180: def recent_support(cs: list[Candle], lo: int, i: int, p: ProposalConfig) -> tuple[int, float] | None:
 181:     """(index, level) of the recent support known BEFORE candle i, using candles lo..i-1 only."""
 182:     d = p.irf_support_def
 183:     if d in ("SWING_K1", "SWING_K2"):
 184:         k = 1 if d == "SWING_K1" else 2
 185:         js = pivot_lows(cs, lo, i, k)
 186:         return (js[-1], cs[js[-1]].l) if js else None
 187:     if d == "LAST_N3":
 188:         if i - 3 < lo:
 189:             return None
 190:         j = min(range(i - 3, i), key=lambda x: cs[x].l)
 191:         return j, cs[j].l
 192:     raise ValueError(d)
 193: 
 194: 
 195: @implements("IRF-M2B-001")
 196: def recent_resistance(cs: list[Candle], lo: int, i: int, p: ProposalConfig) -> tuple[int, float] | None:
 197:     js = pivot_highs(cs, lo, i, 1)
 198:     if not js:
 199:         return None
 200:     j = js[0] if p.irf_resistance_def == "FIRST_PUSH_TOP" else js[-1]
 201:     return j, cs[j].h
 202: 
 203: 
 204: def most_recent_colour(cs: list[Candle], upto: int, green: bool) -> int | None:
 205:     """Index of the most recent green (or red) candle at index <= upto."""
 206:     for j in range(upto, -1, -1):
 207:         if (is_green(cs[j]) if green else is_red(cs[j])):
 208:             return j
 209:     return None
 210: 
 211: 
 212: # ------------------------------------------------------------------ inside-range / sweep helpers
 213: @implements("IRF-M3-003")
 214: def wick_share_outside(c: Candle, irh: float) -> float | None:
 215:     """(High - IRH) / (High - top_of_body); None when there is no upper wick."""
 216:     uw = upper_wick(c)
 217:     if uw <= 0.0:
 218:         return None
 219:     return (c.h - irh) / uw
 220: 
 221: 
 222: def wick_share_in_band(share: float | None, p: ProposalConfig) -> bool:
 223:     if share is None:
 224:         return False
 225:     lo, hi = M3_WICK_SHARE_BAND[p.m3_wick_share_band]
 226:     return lo - 1e-12 <= share <= hi + 1e-12
 227: 
 228: 
 229: @implements("IRF-M3-001")
 230: def compression_ok(cs: list[Candle], s: int, irl: float, irh: float, p: ProposalConfig) -> bool:
 231:     """The N candles before sweep candle s lie inside the initial range (and are 'small' in variant C2)."""
 232:     n = p.m3_compression_n
 233:     if s - n < 1:  # candle 0 is the initial range itself and is not part of the compression
 234:         return False
 235:     window = cs[s - n:s]
 236:     if not all(x.l >= irl and x.h <= irh for x in window):
 237:         return False
 238:     if p.m3_compression_def == "C2":
 239:         ir_h = irh - irl
 240:         return all(rng(x) <= p.m3_compression_size_frac * ir_h for x in window)
 241:     if p.m3_compression_def == "C3":
 242:         return all(is_small(x, p) for x in window)
 243:     return True
 244: 
 245: 
 246: # ------------------------------------------------------------------ gap
 247: @dataclass(frozen=True)
 248: class GapInfo:
 249:     evaluable: bool
 250:     reason: str
 251:     points: float
 252:     direction: str  # UP | DOWN | NONE
 253: 
 254: 
 255: @implements("ORB-GAP-LONG-001", "ORB-GAP-SHORT-001", "PDR-004", "PDS-003", "RF-003", "DATA-OFFICIAL-CLOSE-001", "DATA-OPEN-001")
 256: def gap_info(ctx: SessionContext, p: ProposalConfig) -> GapInfo:
 257:     prev = ctx.previous
 258:     prev_close = prev.close_official if prev is not None else None
 259:     if prev is not None and p.prev_close_source == "LAST_PRINT_1530" and prev.close_1530_print is not None:
 260:         prev_close = prev.close_1530_print
 261:     if prev is None or prev_close is None:
 262:         return GapInfo(False, "NO_PREVIOUS_CLOSE", math.nan, "NONE")
 263:     if prev.gap_to_this_session_unverified and not p.allow_unverified_prev_session:
 264:         return GapInfo(False, "PREV_SESSION_UNVERIFIED", math.nan, "NONE")
 265:     pts = ctx.open_price - prev_close
 266:     if pts > p.gap_min_points:
 267:         d = "UP"
 268:     elif pts < -p.gap_min_points:
 269:         d = "DOWN"
 270:     else:
 271:         d = "NONE"
 272:     return GapInfo(True, "OK", pts, d)
 273: 
 274: 
 275: # ------------------------------------------------------------------ trend / moving average
 276: @dataclass(frozen=True)
 277: class TrendResult:
 278:     ok: bool | None  # None = not evaluable (warm-up); never silently True
 279:     reason: str
 280:     ma_value: float = math.nan
 281: 
 282: 
 283: @implements("ORB-TREND-001", "ORB-TREND-002", "RF-001", "RF-008", "DATA-WARM-001")
 284: def trend_check(ctx: SessionContext, i: int, direction: str, mode: str, p: ProposalConfig | None = None) -> TrendResult:
 285:     """Is the market in an established trend in ``direction`` ('LONG'/'SHORT') at candle i's close?"""
 286:     if mode == "STRUCTURE_EMA_SWING2":
 287:         return structure_trend(ctx, direction, p or DEFAULT_PROPOSALS)
 288:     if mode == "EMA_PREV_SESSION_CLOSE":
 289:         return ema_prev_session_trend(ctx, direction, p or DEFAULT_PROPOSALS)
 290:     cs = ctx.candles
 291:     close = float(cs["close"].iloc[i])
 292:     long = direction == "LONG"
 293:     if mode in ("SMA200_DAILY", "EMA200_DAILY"):
 294:         ma = ctx.daily_sma200_prev if mode == "SMA200_DAILY" else ctx.daily_ema200_prev
 295:         if math.isnan(ma):
 296:             return TrendResult(None, f"DAILY_MA_WARMUP(prior_daily_bars={ctx.daily_history_count}<200)")
 297:         ok = close > ma if long else close < ma
 298:         return TrendResult(ok, f"{mode} {'above' if long else 'below'}" if ok else f"{mode} wrong side", ma)
 299:     ema = float(cs["ema200_5m"].iloc[i])
 300:     if math.isnan(ema):
 301:         return TrendResult(None, "EMA200_5M_WARMUP(<200 completed 5m candles)")
 302:     basic = close > ema if long else close < ema
 303:     if not basic:
 304:         return TrendResult(False, "EMA5M_BASIC wrong side", ema)
 305:     if mode == "EMA5M_BASIC":
 306:         return TrendResult(True, "EMA5M_BASIC", ema)
 307:     n = 1 if mode == "EMA5M_PREV_SESSION" else 3
 308:     hist = ctx.prior_session_ema_above[:n]
 309:     if len(hist) < n or any(h is None for h in hist):
 310:         return TrendResult(None, f"PRIOR_SESSIONS_EMA_UNAVAILABLE(need {n})", ema)
 311:     on_side = all(h if long else (not h) for h in hist)
 312:     return TrendResult(on_side, mode if on_side else f"{mode}: previous session(s) were on the other side of the EMA", ema)
 313: 
 314: 
 315: @implements("TREND-EMA-001", "RF-001", "ORB-TREND-001", "DATA-WARM-001")
 316: def ema_prev_session_trend(ctx: SessionContext, direction: str, p: ProposalConfig) -> TrendResult:
 317:     """Research VARIANT A (owner-approved): the five-minute EMA(200) price location only, from PREVIOUS-session information, so the
 318:     opening gap can never establish the trend. long: last close > its EMA; short: last close < its EMA. ``ok=None`` while the EMA warms up."""
 319:     prev = ctx.previous
 320:     if prev is None:
 321:         return TrendResult(None, "NO_PREVIOUS_SESSION")
 322:     cs = to_candles(prev_candles(prev, p))
 323:     if not cs:
 324:         return TrendResult(None, "NO_PREVIOUS_CANDLES")
 325:     last = cs[-1]
 326:     if math.isnan(last.ema):
 327:         return TrendResult(None, "EMA200_5M_WARMUP(previous session)")
 328:     ok = last.c > last.ema if direction == "LONG" else last.c < last.ema
 329:     return TrendResult(ok, "EMA_PREV_SESSION_CLOSE " + ("on the trend side" if ok else "wrong side"), last.ema)
 330: 
 331: 
 332: @implements("TREND-STRUCT-001", "TREND-SWING-001", "RF-001", "ORB-TREND-001", "DATA-WARM-001")
 333: def structure_trend(ctx: SessionContext, direction: str, p: ProposalConfig) -> TrendResult:
 334:     """PROPOSED established trend, from PREVIOUS-session information only (the opening gap can never establish it):
 335: 
 336:     up:   last close > its EMA(200)  AND  SH[-1] > SH[-2]  AND  SL[-1] > SL[-2]
 337:     down: last close < its EMA(200)  AND  SH[-1] < SH[-2]  AND  SL[-1] < SL[-2]
 338: 
 339:     SH/SL are the confirmed swing highs/lows (``p.swing_k`` candles each side, strict) of the previous session's candles, so every
 340:     swing was already confirmed by the time that session ended. Returns ``ok=None`` while the EMA is warming up, ``ok=False`` when
 341:     fewer than two swing highs or lows exist (a trend cannot be called established from less).
 342:     """
 343:     prev = ctx.previous
 344:     if prev is None:
 345:         return TrendResult(None, "NO_PREVIOUS_SESSION")
 346:     cs = to_candles(prev_candles(prev, p))
 347:     if not cs:
 348:         return TrendResult(None, "NO_PREVIOUS_CANDLES")
 349:     last = cs[-1]
 350:     if math.isnan(last.ema):
 351:         return TrendResult(None, "EMA200_5M_WARMUP(previous session)")
 352:     long = direction == "LONG"
 353:     side = last.c > last.ema if long else last.c < last.ema
 354:     if not side:
 355:         return TrendResult(False, "STRUCTURE: previous close on the wrong side of EMA(200)", last.ema)
 356:     sh = confirmed_swing_highs(cs, len(cs) - 1, p.swing_k)
 357:     sl = confirmed_swing_lows(cs, len(cs) - 1, p.swing_k)
 358:     if len(sh) < 2 or len(sl) < 2:
 359:         return TrendResult(False, f"STRUCTURE: fewer than two confirmed swing highs/lows ({len(sh)}/{len(sl)})", last.ema)
 360:     h1, h2, l1, l2 = cs[sh[-2]].h, cs[sh[-1]].h, cs[sl[-2]].l, cs[sl[-1]].l
 361:     ok = (h2 > h1 and l2 > l1) if long else (h2 < h1 and l2 < l1)
 362:     why = f"STRUCTURE swing highs {h1}->{h2}, swing lows {l1}->{l2}"
 363:     return TrendResult(ok, why if ok else why + " (not " + ("higher-high/higher-low)" if long else "lower-high/lower-low)"), last.ema)
 364: 
 365: 
 366: def ma_value(ctx: SessionContext, i: int, mode: str) -> float:
 367:     if mode == "SMA200_DAILY":
 368:         return ctx.daily_sma200_prev
 369:     if mode == "EMA200_DAILY":
 370:         return ctx.daily_ema200_prev
 371:     return float(ctx.candles["ema200_5m"].iloc[i])
 372: 
 373: 
 374: # ------------------------------------------------------------------ previous-day zones (PDR / PDS)
 375: @dataclass(frozen=True)
 376: class Zone:
 377:     low: float
 378:     high: float
 379:     candle_index: int
 380:     candle_start: datetime
 381:     method: str = "A_HIGHEST_HIGH"
 382:     members: tuple[int, ...] = ()
 383:     fallback: bool = False  # legacy (PDS only): the configured method found no candidate and method A was used
 384:     diagnostic_only: bool = False  # PDR method A (absolute highest high): a diagnostic reference, never tradable
 385: 
 386: 
 387: def _pick(idxs: list[int], tie: str) -> int:
 388:     return idxs[0] if tie == "FIRST" else idxs[-1]
 389: 
 390: 
 391: @implements("DATA-CAS-001")
 392: def prev_candles(prev: PreviousSession, p: ProposalConfig) -> pd.DataFrame:
 393:     """Previous-session candles used for levels/zones: all of them, or (proposal) only those before the closing auction."""
 394:     if p.prev_day_level_window == "CONTINUOUS_ONLY" and prev.continuous_candles is not None:
 395:         return prev.continuous_candles
 396:     return prev.candles
 397: 
 398: 
 399: def prev_high_low(prev: PreviousSession, p: ProposalConfig) -> tuple[float, float]:
 400:     c = prev_candles(prev, p)
 401:     return float(c["high"].max()), float(c["low"].min())
 402: 
 403: 
 404: def _cluster(cs: list[Candle], idxs: list[int], key, tol: float, min_touches: int, top: bool) -> list[int] | None:
 405:     """Cluster swing indices whose ``key`` lies within ``tol`` of the cluster's extreme; return the members of the most extreme
 406:     cluster with at least ``min_touches`` members (``top``: highest; else lowest), or None. Greedy from the extreme downward."""
 407:     pool = sorted(idxs, key=lambda j: key(cs[j]), reverse=top)
 408:     used: set[int] = set()
 409:     for j0 in pool:
 410:         if j0 in used:
 411:             continue
 412:         ext = key(cs[j0])
 413:         members = [j for j in pool if j not in used and abs(key(cs[j]) - ext) <= tol + 1e-9]
 414:         used.update(members)
 415:         if len(members) >= min_touches:
 416:             return sorted(members)
 417:     return None
 418: 
 419: 
 420: @implements("PDR-002", "PDR-003", "PDR-ZONE-002")
 421: def pdr_zone(prev: PreviousSession, p: ProposalConfig) -> Zone | None:
 422:     """Previous-day resistance zone (PDR-D09, Phase 2.3). The owner approved two independent research candidates - B_SWING_HIGH_REVERSAL
 423:     and C_REPEATED_TOUCHES; a candidate that finds nothing returns ``None`` (NO setup - it never silently falls back to the absolute
 424:     highest high). A_HIGHEST_HIGH is a DIAGNOSTIC reference only (``Zone.diagnostic_only``). Only previous-session candles are read."""
 425:     cs = to_candles(prev_candles(prev, p))
 426:     method = p.pdr_zone_method
 427:     members: list[int] = []
 428:     if method == "B_SWING_HIGH_REVERSAL":
 429:         for j in reversed(confirmed_swing_highs(cs, len(cs) - 1, p.swing_k)):
 430:             if any(is_red(cs[m]) for m in range(j, min(len(cs), j + p.swing_k + 1))):
 431:                 members = [j]
 432:                 break
 433:     elif method == "C_REPEATED_TOUCHES":
 434:         sh = confirmed_swing_highs(cs, len(cs) - 1, p.swing_k)
 435:         members = _cluster(cs, sh, lambda c: c.h, p.zone_cluster_tolerance_points, p.zone_cluster_min_touches, True) or []
 436:     if method == "A_HIGHEST_HIGH":
 437:         top = max(c.h for c in cs)
 438:         members = [_pick([k for k, c in enumerate(cs) if c.h == top], p.zone_tie_break)]
 439:     if not members:
 440:         return None
 441:     high = max(cs[m].h for m in members)
 442:     lows = [min(cs[m].o, cs[m].c) if p.zone_lower_boundary == "ZONE_FULL" else max(cs[m].o, cs[m].c) for m in members]
 443:     j = members[-1] if method != "A_HIGHEST_HIGH" else members[0]
 444:     return Zone(low=min(lows), high=high, candle_index=j, candle_start=cs[j].start, method=method,
 445:                 members=tuple(members), diagnostic_only=method == "A_HIGHEST_HIGH")
 446: 
 447: 
 448: @implements("PDR-ZONE-002")
 449: def pdr_diagnostic_zone(prev: PreviousSession, p: ProposalConfig) -> Zone:
 450:     """The absolute highest-high zone, computed for COMPARISON on every PDR record (never used to trade)."""
 451:     z = pdr_zone(prev, replace_method(p, "A_HIGHEST_HIGH"))
 452:     assert z is not None
 453:     return z
 454: 
 455: 
 456: def replace_method(p: ProposalConfig, method: str) -> ProposalConfig:
 457:     from dataclasses import replace
 458:     return replace(p, pdr_zone_method=method)
 459: 
 460: 
 461: @implements("PDS-002", "PDS-ZONE-002")
 462: def pds_zone(prev: PreviousSession, p: ProposalConfig) -> Zone:
 463:     """Previous-day support zone (mirror of the PDR methods; NOT assumed to be an exact mirror of the PDR zone)."""
 464:     cs = to_candles(prev_candles(prev, p))
 465:     method = p.pds_zone_method
 466:     members: list[int] = []
 467:     fallback = False
 468:     if method == "B_SWING_LOW_REVERSAL":
 469:         for j in reversed(confirmed_swing_lows(cs, len(cs) - 1, p.swing_k)):
 470:             if any(is_green(cs[m]) for m in range(j, min(len(cs), j + p.swing_k + 1))):
 471:                 members = [j]
 472:                 break
 473:     elif method == "C_REPEATED_TOUCHES":
 474:         sl = confirmed_swing_lows(cs, len(cs) - 1, p.swing_k)
 475:         members = _cluster(cs, sl, lambda c: c.l, p.zone_cluster_tolerance_points, p.zone_cluster_min_touches, False) or []
 476:     if not members:
 477:         fallback = method != "A_LOWEST_LOW"
 478:         method_used = "A_LOWEST_LOW"
 479:         bot = min(c.l for c in cs)
 480:         members = [_pick([k for k, c in enumerate(cs) if c.l == bot], p.zone_tie_break)]
 481:     else:
 482:         method_used = method
 483:     low = min(cs[m].l for m in members)
 484:     tops = [max(cs[m].o, cs[m].c) if p.pds_zone_upper_boundary == "ZONE_FULL" else min(cs[m].o, cs[m].c) for m in members]
 485:     j = members[-1] if method_used != "A_LOWEST_LOW" else members[0]
 486:     return Zone(low=low, high=max(tops), candle_index=j, candle_start=cs[j].start, method=method_used,
 487:                 members=tuple(members), fallback=fallback)
 488: 
 489: 
 490: @implements("PDR-010")
 491: def previous_day_reversal_ok(prev: PreviousSession, zone: Zone, p: ProposalConfig) -> tuple[bool | None, str]:
 492:     """Research filter for 'clear high and reversal identified'. OFF => (None, 'NOT_EVALUATED')."""
 493:     if p.pdr_reversal_filter == "OFF":
 494:         return None, "REVERSAL_FILTER_OFF"
 495:     cs = to_candles(prev_candles(prev, p))
 496:     after = cs[zone.candle_index + 1:]
 497:     if not after:
 498:         return False, "NO_CANDLES_AFTER_HIGH"
 499:     depth = zone.high - min(c.l for c in after)
 500:     ph, pl = prev_high_low(prev, p)
 501:     day_range = ph - pl
 502:     return depth >= 0.25 * day_range, f"depth={depth:.2f} vs 25% of range={0.25 * day_range:.2f}"
 503: 
 504: 
 505: def green_refs(cs: list[Candle], i: int, setup_start: int = 0) -> dict[str, float | int | None]:
 506:     """Inputs for the 35/40 stop rule (IRF-SL-001, PDS-SL-001): most recent green candle at index <= i."""
 507:     gj = most_recent_colour(cs, i, True)
 508:     greens = [cs[j] for j in range(setup_start, i + 1) if is_green(cs[j])]
 509:     return {
 510:         "recent_green_high": cs[gj].h if gj is not None else None,
 511:         "recent_green_close": cs[gj].c if gj is not None else None,
 512:         "setup_green_high": max((g.h for g in greens), default=None),
 513:     }
```

## src/nifty_trading/strategies/params.py

```python
   1: """Proposal parameters for rules that the source documents state only qualitatively.
   2: 
   3: EVERYTHING here is an engineering interpretation labelled ``PROPOSED_FOR_REVIEW``. None of it is
   4: an original strategy rule, and none of it was selected by looking at historical profitability
   5: (Phase 2 forbids that). Each family lists separated candidate interpretations. Defaults follow the source
   6: wording where it gives any; numeric thresholds are mid-range placeholders, discussed in ``ambiguous_rules.md``.
   7: """
   8: 
   9: from __future__ import annotations
  10: 
  11: from dataclasses import asdict, dataclass
  12: from datetime import time
  13: from typing import Any
  14: 
  15: PROPOSAL_LABEL = "PROPOSED_FOR_REVIEW"
  16: 
  17: 
  18: class ConfigError(ValueError):
  19:     pass
  20: 
  21: 
  22: # --- candle-shape candidates: name -> thresholds ---------------------------------------------
  23: # body_ratio = |C-O| / (H-L); wick ratios are wick / (H-L); zero-range candles never qualify.
  24: STRONG_CANDLE = {
  25:     "STRICT": {"body_ratio_min": 0.70, "opposite_wick_ratio_max": 0.15},
  26:     "MODERATE": {"body_ratio_min": 0.60, "opposite_wick_ratio_max": 0.20},
  27:     "LOOSE": {"body_ratio_min": 0.50, "opposite_wick_ratio_max": 0.25},
  28: }
  29: PIN_BAR = {
  30:     "STRICT": {"wick_ratio_min": 0.70, "body_ratio_max": 0.25, "opposite_wick_ratio_max": 0.10},
  31:     "MODERATE": {"wick_ratio_min": 0.60, "body_ratio_max": 0.33, "opposite_wick_ratio_max": 0.15},
  32:     "LOOSE": {"wick_ratio_min": 0.55, "body_ratio_max": 0.40, "opposite_wick_ratio_max": 0.20},
  33:     # Phase 2.2 owner recommendation: rejection wick >= 2x the body AND the close inside the favourable 30% of the range.
  34:     "OWNER_2X_CLOSE30": {"wick_to_body_min": 2.0, "close_fraction_max": 0.30},
  35: }
  36: SMALL_CANDLE_BODY_RATIO_MAX = 0.30  # Phase 2.2 owner recommendation (PROPOSED): a "small" candle has body <= 30% of its range
  37: REJECTION_WICK = {  # wick/range at or above this counts as "strong rejection"
  38:     "STRICT": {"wick_ratio_min": 0.25},
  39:     "MODERATE": {"wick_ratio_min": 0.33},
  40:     "LOOSE": {"wick_ratio_min": 0.40},
  41: }
  42: M3_WICK_SHARE_BAND = {  # share of the upper wick that lies above IRH
  43:     "BAND_60_70": (0.60, 0.70),  # literal "approximately 60-70%"
  44:     "MIN_60": (0.60, 1.00),
  45:     "BAND_55_75": (0.55, 0.75),
  46: }
  47: # per-candidate descriptions used by the documentation generator
  48: CANDIDATE_NOTES: dict[str, dict[str, str]] = {
  49:     "strong_candle": {"STRICT": "body>=70% of range, opposite wick<=15%", "MODERATE": "body>=60%, opposite wick<=20%",
  50:                       "LOOSE": "body>=50%, opposite wick<=25%"},
  51:     "pin_bar": {"STRICT": "wick>=70%, body<=25%, opposite wick<=10%", "MODERATE": "wick>=60%, body<=33%, opp<=15%",
  52:                 "LOOSE": "wick>=55%, body<=40%, opp<=20%",
  53:                 "OWNER_2X_CLOSE30": "rejection wick >= 2x body and close within the favourable 30% of the range (owner recommendation)"},
  54:     "rejection_wick": {"STRICT": "wick>=25% of range", "MODERATE": "wick>=33%", "LOOSE": "wick>=40%"},
  55:     "trend_mode": {
  56:         "EMA5M_BASIC": "close of the first 5m candle vs EMA(200) of completed 5m closes (the 'basic filter' only)",
  57:         "EMA5M_PREV_SESSION": "BASIC + previous session's last 5m close already on the trend side of its EMA (encodes RF p.5 invalid example)",
  58:         "EMA5M_PREV_3_SESSIONS": "BASIC + each of the previous 3 sessions closed on the trend side of its EMA",
  59:         "SMA200_DAILY": "first-candle close vs SMA(200) of daily official closes up to the previous session (needs 200 prior daily bars)",
  60:         "EMA200_DAILY": "as SMA200_DAILY but exponential",
  61:         "EMA_PREV_SESSION_CLOSE": "VARIANT A (owner-approved research variant): PREVIOUS-session only - its last 5m close vs its own EMA(200); no swing structure",
  62:         "STRUCTURE_EMA_SWING2": "VARIANT B (owner-approved research variant): PREVIOUS-session only: last close vs its EMA(200) AND the last two confirmed swing highs AND the last two swing lows rising (up) / falling (down); swing = strictly beyond 2 candles each side",
  63:     },
  64:     "irf_support_def": {
  65:         "SWING_K1": "latest 3-candle fractal low confirmed before the signal candle",
  66:         "SWING_K2": "latest 5-candle fractal low (2 each side)",
  67:         "LAST_N3": "lowest low of the 3 candles immediately before the signal candle",
  68:     },
  69:     "irf_resistance_def": {
  70:         "FIRST_PUSH_TOP": "earliest 3-candle fractal high at/after the breakout candle",
  71:         "LATEST_SWING_HIGH": "latest confirmed 3-candle fractal high after the breakout candle",
  72:     },
  73:     "m2b_push_must_precede_red_candle": {"False": "the candle that closes back below resistance may itself be the one that traded above it",
  74:                                          "True": "a EARLIER candle must have traded back above the resistance"},
  75:     "m2_extension_definition": {"E1": "a later candle makes a higher high than the breakout candle",
  76:                                 "E2": "a later candle also closes above IRH"},
  77:     "m3_compression_def": {"C1": "previous N candles lie fully inside [IRL, IRH]",
  78:                            "C2": "C1 and every one of them has range <= 50% of the initial-range height",
  79:                            "C3": "C1 and every one of them is a small candle (body <= 30% of its range)"},
  80:     "m3_wick_share_band": {"BAND_60_70": "0.60 <= share <= 0.70 (literal)", "MIN_60": "share >= 0.60",
  81:                            "BAND_55_75": "0.55 <= share <= 0.75"},
  82:     "stop_distance_measure": {
  83:         "GREEN_HIGH": "distance = high of the most recent green candle - entry (short)",
  84:         "GREEN_CLOSE": "distance = close of the most recent green candle - entry (short)",
  85:         "GREEN_SETUP_HIGH": "distance = highest high among green candles since the setup began - entry",
  86:     },
  87:     "pdr_open_vs_zone": {"ABOVE_ZONE": "open > zone high (the guide's text; default)", "NOT_BELOW_ZONE": "open >= zone low (price at/above the zone, so it can act as support)",
  88:                          "ANY": "no condition on the open beyond the gap-up (55% of its signals open BELOW the zone: not recommended)"},
  89:     "pds_open_vs_zone": {"BELOW_ZONE": "open < zone low (the guide's text, p.3; default)", "NOT_ABOVE_ZONE": "open <= zone high", "ANY": "no condition beyond the gap-down"},
  90:     "prev_close_source": {"OFFICIAL_DAILY": "previous close = the vendor daily close = the published NSE closing value (verified on 9 of 9 external closes)",
  91:                           "LAST_PRINT_1530": "previous close = the last 1-minute print at 15:30 (equal to the official close only from 2026-08-03)"},
  92:     "prev_day_level_window": {"ALL_CANDLES": "previous-day high/low/zone use every complete 5m candle, as a chart shows them (default)",
  93:                               "CONTINUOUS_ONLY": "on closing-auction days (>= 2026-08-03) use only candles that ended by 15:15"},
  94:     "zone_lower_boundary": {"ZONE_FULL": "PDR zone = [body bottom, wick top] (mirrors PDS text 'body and wick')",
  95:                             "ZONE_WICK": "PDR zone = [body top, wick top] (wick only)"},
  96:     "zone_proximity_points": {"0": "actual zone intersection (strict research version)", "5": "within 5 index points (near-touch proposal)",
  97:                               "10": "within 10 index points"},
  98:     "pdr_zone_method": {"A_HIGHEST_HIGH": "DIAGNOSTIC REFERENCE ONLY (Phase 2.3): the previous session's absolute highest-high candle; signals built on it are marked DIAGNOSTIC_ONLY_NOT_TRADABLE",
  99:                         "B_SWING_HIGH_REVERSAL": "owner-approved research candidate 1 (confirmed reversal swing high): the LATEST confirmed swing high (swing_k each side) with a red candle at/after the peak; no such swing = no PDR setup",
 100:                         "C_REPEATED_TOUCHES": "owner-approved research candidate 2 (repeated resistance shelf): the highest cluster of >=2 confirmed swing highs within the tolerance; the zone spans the cluster; no cluster = no PDR setup"},
 101:     "pds_zone_method": {"A_LOWEST_LOW": "the previous session's absolute lowest-low candle",
 102:                         "B_SWING_LOW_REVERSAL": "the LATEST confirmed swing low with a green candle at/after the trough (bullish reversal)",
 103:                         "C_REPEATED_TOUCHES": "the lowest cluster of >=2 confirmed swing lows within the tolerance; zone spans the cluster"},
 104:     "pds_zone_upper_boundary": {"ZONE_FULL": "PDS zone = [wick tip, body TOP]", "ZONE_WICK": "PDS zone = [wick tip, body BOTTOM] (wick only)"},
 105:     "rf_return_inside_def": {"R1": "first later candle that CLOSES back inside [RF_L, RF_H]",
 106:                              "R2": "first later candle whose range touches RF_L (High >= RF_L)",
 107:                              "R3": "only the very next candle after the close-below, closing inside"},
 108:     "pds_small_support_def": {"SWING_K1_NEAR_ZONE": "fractal low formed after the weak red candle within the zone band",
 109:                               "LAST_N2": "lowest low of the 2 candles before the signal candle"},
 110:     "pds_m3_break_basis": {"CLOSE": "a candle CLOSES below the small support", "TOUCH": "a candle's low trades below it"},
 111:     "orb_prev_day_level_def": {"PREV_DAY_HL": "previous session high (resistance) / low (support)"},
 112: }
 113: 
 114: 
 115: @dataclass(frozen=True)
 116: class ProposalConfig:
 117:     """Selected interpretation of each ambiguous rule. All values are PROPOSED_FOR_REVIEW."""
 118: 
 119:     label: str = PROPOSAL_LABEL
 120:     strong_candle: str = "MODERATE"  # body >= 60%, opposite wick <= 20% (= the owner's Phase 2.2 recommendation)
 121:     pin_bar: str = "OWNER_2X_CLOSE30"
 122:     rejection_wick: str = "MODERATE"
 123:     trend_mode: str = "STRUCTURE_EMA_SWING2"  # Phase 2.2 owner recommendation (PROPOSED). Caveat: ORB p.7's own uptrend chart has falling recent swing highs
 124:     ma_mode: str = "EMA200_5M"  # ORB gap setup: EMA200_5M | SMA200_DAILY | EMA200_DAILY
 125:     swing_k: int = 2  # candles on each side of a swing point (PROPOSED, TREND-SWING-001)
 126:     small_candle_body_ratio_max: float = SMALL_CANDLE_BODY_RATIO_MAX
 127:     # IRF
 128:     irf_support_def: str = "SWING_K1"
 129:     irf_resistance_def: str = "FIRST_PUSH_TOP"
 130:     m1_max_candles_after_breakout: int = 1
 131:     m1_close_below_irl_counts_as_inside: bool = False
 132:     m2_extension_definition: str = "E1"
 133:     m2_red_may_be_extension_candle: bool = False
 134:     m2b_push_must_precede_red_candle: bool = False  # IRF p.9 steps 3-5: may the push above and the closing red candle be one candle?
 135:     m2a_break_may_be_red_candle: bool = False
 136:     m2_expiry_candles: int | None = None
 137:     m3_compression_def: str = "C1"
 138:     m3_compression_n: int = 2
 139:     m3_compression_size_frac: float = 0.5
 140:     m3_wick_share_band: str = "BAND_60_70"
 141:     stop_distance_measure: str = "GREEN_HIGH"
 142:     stop_boundary_inclusive_35: bool = True  # d == 35 -> 35
 143:     # gap / zones
 144:     gap_min_points: float = 0.0
 145:     gap_max_points: float | None = None
 146:     zone_lower_boundary: str = "ZONE_WICK"  # Phase 2.2: PDR charts 2 and 4 (and, within 5 points, chart 1) draw [body TOP, wick tip]; ZONE_FULL is the candidate
 147:     prev_day_level_window: str = "ALL_CANDLES"  # ALL_CANDLES | CONTINUOUS_ONLY (excludes the closing-auction candles on/after 2026-08-03)
 148:     pdr_zone_method: str = "B_SWING_HIGH_REVERSAL"  # Phase 2.3: A_HIGHEST_HIGH is a DIAGNOSTIC reference only and never yields a tradable signal
 149:     pds_zone_method: str = "A_LOWEST_LOW"
 150:     pds_zone_upper_boundary: str = "ZONE_FULL"
 151:     zone_cluster_tolerance_points: float = 5.0  # repeated-touch clustering (method C), PROPOSED
 152:     zone_cluster_min_touches: int = 2
 153:     zone_tie_break: str = "FIRST"  # which candle when several share the day's high/low
 154:     zone_proximity_points: float = 0.0  # Phase 2.2: strict zone intersection is the initial research version; 5 is the labelled near-touch variant
 155:     pdr_green_may_be_interaction_candle: bool = False
 156:     pdr_reversal_filter: str = "OFF"  # OFF | DEPTH_25PCT
 157:     pds_small_support_def: str = "SWING_K1_NEAR_ZONE"
 158:     pds_m3_break_basis: str = "CLOSE"
 159:     pds_m3_standalone: bool = False
 160:     # RF
 161:     rf_return_inside_def: str = "R1"
 162:     rf_direction: str = "LONG"
 163:     # ORB
 164:     ma_near_band_points: float = 15.0
 165:     ma_close_margin_points: float = 5.0
 166:     entry_reference_price: str = "SIGNAL_CANDLE_CLOSE"
 167:     orb_pin_bar_in_methods_1_2: bool = True  # ORB pp.9-10: the conditional pin bar applies 'across all three setups'
 168:     # PDR: the guide's TEXT says the market 'pulls back into the marked zone' (p.1) and 'come back toward the marked zone' (p.2): the open is
 169:     # above the zone. Example 3 (2025-10-07) does NOT settle it: the zone the author DREW on that chart is only ~4-5 points tall (about 25,080.5-25,084.5; the open is ~3 points above it), whereas the engine's
 170:     # zone (highest-high candle, 14:50 spike) is 38.6 points tall, so 'the open is inside the zone' was an artefact of the engine's zone.
 171:     # ABOVE_ZONE (open > zone high: the text; default) | NOT_BELOW_ZONE (open >= zone low) | ANY (WARNING: 55% of its signals have the open BELOW the zone,
 172:     # i.e. the zone is overhead resistance, not support).
 173:     pdr_open_vs_zone: str = "ABOVE_ZONE"
 174:     # PDS: the guide's text says price 'is trading below the previous support zone' after the open (p.3); no contrary example.
 175:     # BELOW_ZONE (open < zone low: the text) | NOT_ABOVE_ZONE (open <= zone high) | ANY
 176:     pds_open_vs_zone: str = "BELOW_ZONE"
 177:     prev_close_source: str = "OFFICIAL_DAILY"  # OFFICIAL_DAILY (vendor daily close = published NSE close) | LAST_PRINT_1530
 178:     max_signals_per_session: int = 1  # PROPOSED (PDR-012 / PDS-007 / RF-014)
 179:     # data hygiene
 180:     allow_unverified_prev_session: bool = False
 181:     signal_window_end: str | None = None  # "HH:MM" latest bar_end allowed; None = no cutoff (MISSING in docs)
 182: 
 183:     def __post_init__(self) -> None:
 184:         for fam, val in (("strong_candle", self.strong_candle), ("pin_bar", self.pin_bar),
 185:                          ("rejection_wick", self.rejection_wick)):
 186:             table = {"strong_candle": STRONG_CANDLE, "pin_bar": PIN_BAR, "rejection_wick": REJECTION_WICK}[fam]
 187:             if val not in table:
 188:                 raise ConfigError(f"{fam}={val!r} not in {sorted(table)}")
 189:         if self.pdr_open_vs_zone not in ("ABOVE_ZONE", "NOT_BELOW_ZONE", "ANY"):
 190:             raise ConfigError(f"pdr_open_vs_zone={self.pdr_open_vs_zone!r}")
 191:         if self.pds_open_vs_zone not in ("BELOW_ZONE", "NOT_ABOVE_ZONE", "ANY"):
 192:             raise ConfigError(f"pds_open_vs_zone={self.pds_open_vs_zone!r}")
 193:         if self.prev_close_source not in ("OFFICIAL_DAILY", "LAST_PRINT_1530"):
 194:             raise ConfigError(f"prev_close_source={self.prev_close_source!r}")
 195:         if self.prev_day_level_window not in ("ALL_CANDLES", "CONTINUOUS_ONLY"):
 196:             raise ConfigError(f"prev_day_level_window={self.prev_day_level_window!r}")
 197:         if self.m3_wick_share_band not in M3_WICK_SHARE_BAND:
 198:             raise ConfigError(f"m3_wick_share_band={self.m3_wick_share_band!r}")
 199:         if self.trend_mode not in CANDIDATE_NOTES["trend_mode"]:
 200:             raise ConfigError(f"trend_mode={self.trend_mode!r}")
 201:         if self.ma_mode not in ("EMA200_5M", "SMA200_DAILY", "EMA200_DAILY"):
 202:             raise ConfigError(f"ma_mode={self.ma_mode!r}")
 203:         for fam, val in (("pdr_zone_method", self.pdr_zone_method), ("pds_zone_method", self.pds_zone_method),
 204:                          ("pds_zone_upper_boundary", self.pds_zone_upper_boundary)):
 205:             if val not in CANDIDATE_NOTES[fam]:
 206:                 raise ConfigError(f"{fam}={val!r}")
 207:         if self.zone_proximity_points < 0 or self.zone_cluster_tolerance_points < 0 or self.zone_cluster_min_touches < 2:
 208:             raise ConfigError("zone proximity/tolerance must be >= 0 and zone_cluster_min_touches >= 2")
 209:         if self.swing_k < 1:
 210:             raise ConfigError("swing_k must be >= 1")
 211:         if self.m3_compression_def not in CANDIDATE_NOTES["m3_compression_def"]:
 212:             raise ConfigError(f"m3_compression_def={self.m3_compression_def!r}")
 213:         if self.m1_max_candles_after_breakout < 1:
 214:             raise ConfigError("m1_max_candles_after_breakout must be >= 1")
 215:         if self.rf_direction not in ("LONG",):
 216:             raise ConfigError("rf_direction: only LONG is implemented (direction is implied, RF-012)")
 217:         # Exclusivity guarantee for PDS M1 (good body) vs M2 (pin bar): a candle cannot hold
 218:         # body_ratio >= a and upper_wick_ratio >= b when a + b > 1.
 219:         a = STRONG_CANDLE[self.strong_candle]["body_ratio_min"]
 220:         pb = PIN_BAR[self.pin_bar]
 221:         if "wick_ratio_min" in pb:
 222:             b = pb["wick_ratio_min"]
 223:             if a + b <= 1.0:
 224:                 raise ConfigError(f"strong_candle/pin_bar overlap possible ({a}+{b}<=1): methods would not be exclusive")
 225:         elif a + a * pb["wick_to_body_min"] <= 1.0:  # wick >= k*body >= k*a*range must not fit beside a body of a*range
 226:             raise ConfigError("strong_candle/pin_bar overlap possible: methods would not be exclusive")
 227: 
 228:     @property
 229:     def strong(self) -> dict[str, float]:
 230:         return STRONG_CANDLE[self.strong_candle]
 231: 
 232:     @property
 233:     def pin(self) -> dict[str, float]:
 234:         return PIN_BAR[self.pin_bar]
 235: 
 236:     @property
 237:     def reject(self) -> dict[str, float]:
 238:         return REJECTION_WICK[self.rejection_wick]
 239: 
 240:     def to_dict(self) -> dict[str, Any]:
 241:         return asdict(self)
 242: 
 243: 
 244: DEFAULT_PROPOSALS = ProposalConfig()
 245: 
 246: 
 247: @dataclass(frozen=True)
 248: class SourceConstants:
 249:     """Numbers that ARE stated in the documents (VERIFIED_EXPLICIT), with their sources."""
 250: 
 251:     irf_target_points: float = 60.0  # IRF p.2
 252:     irf_stop_choices: tuple[float, float] = (35.0, 40.0)  # IRF p.2
 253:     orb_stop_points: float = 30.0  # ORB p.1
 254:     orb_target_points: float = 60.0  # ORB p.1
 255:     pdr_target_points: float = 70.0  # PDR p.1
 256:     pds_target_points: float = 70.0  # PDS p.1
 257:     pdr_pds_stop_choices: tuple[float, float] = (35.0, 40.0)
 258:     rf_stop_range: tuple[float, float] = (35.0, 40.0)  # RF p.2 (selection rule absent)
 259:     rf_target_points: float | None = None  # RF p.8: OPEN -> RF_TARGET_STATUS = UNRESOLVED
 260:     t1_points: float = 27.0  # performance report
 261:     lots_total: int = 6
 262:     lot_size: int = 65
 263:     t2_choices: tuple[float, float] = (60.0, 70.0)  # report: "60 or 70, as recorded"
 264: 
 265: 
 266: SOURCE = SourceConstants()
 267: # Phase 2.2: the RF guide still says the target is OPEN (RF p.8). The owner asked for a CONFIGURABLE research value of 60 (the report's
 268: # arithmetic and the p.9 chart box 60.80 point to it). It is a proposal: never VERIFIED_EXPLICIT, never USER_APPROVED.
 269: RF_TARGET_STATUS = "PROPOSED_FOR_REVIEW"
 270: RF_TARGET_RESEARCH_POINTS = 60.0
 271: 
 272: 
 273: # --- trade parameters: stops and targets ------------------------------------------------------------------------
 274: VERIFIED_EXPLICIT = "VERIFIED_EXPLICIT"
 275: USER_APPROVED = "USER_APPROVED"
 276: CONFLICTING = "CONFLICTING"  # the guide states the value but the performance report's recorded winners disagree
 277: STRATEGIES = ("IRF", "ORB", "PDR", "PDS", "RF")
 278: 
 279: #: User-approved provisional RESEARCH baseline (Phase 2.2). Not the historical manual trader's stop-selection rule, which the
 280: #: sources still do not define for IRF/PDR/PDS/RF (they say "35 or 40"). ORB keeps its documented 30 (ORB p.1, VERIFIED_EXPLICIT).
 281: STOP_BASELINE: dict[str, float] = {"IRF": 35.0, "ORB": 30.0, "PDR": 35.0, "PDS": 35.0, "RF": 35.0}
 282: #: Future sensitivity test (Phase 3 compares them; Phase 2.2 does NOT). ORB is deliberately unchanged.
 283: STOP_ALTERNATE: dict[str, float] = {"IRF": 40.0, "ORB": 30.0, "PDR": 40.0, "PDS": 40.0, "RF": 40.0}
 284: STOP_STATUS: dict[str, str] = {"IRF": USER_APPROVED, "ORB": VERIFIED_EXPLICIT, "PDR": USER_APPROVED, "PDS": USER_APPROVED, "RF": USER_APPROVED}
 285: #: Target 2 per strategy, with the status of the value. PDR/PDS: the guides say 70 while the performance report records winners at 60
 286: #: (PDR 1 of 6, PDS 2 of 3): the conflict is preserved in ``T2_CONFLICTS`` and never silently overwritten.
 287: T2_TABLE: dict[str, tuple[float, str]] = {
 288:     "IRF": (60.0, VERIFIED_EXPLICIT), "ORB": (60.0, VERIFIED_EXPLICIT), "PDR": (70.0, CONFLICTING),
 289:     "PDS": (70.0, CONFLICTING), "RF": (RF_TARGET_RESEARCH_POINTS, PROPOSAL_LABEL),
 290: }
 291: T2_CONFLICTS: dict[str, str] = {
 292:     "PDR": "PDR guide p.1 says 70; the performance report's arithmetic records 1 of its 6 PDR winners at 60",
 293:     "PDS": "PDS guide p.1 says 70; the performance report's arithmetic records 2 of its 3 PDS winners at 60",
 294: }
 295: STOP_VARIANTS = ("BASELINE", "ALTERNATE_40", "SOURCE_35_40_BY_DISTANCE")
 296: 
 297: 
 298: @dataclass(frozen=True)
 299: class TradeConfig:
 300:     """Stop / target configuration for the exit policy and for the ``execution_config`` carried by every signal.
 301: 
 302:     ``stop_variant``: BASELINE (35; ORB 30), ALTERNATE_40 (40; ORB 30) or SOURCE_35_40_BY_DISTANCE (the Phase 2 research
 303:     reading: 35 or 40 by the distance to the most recent opposite candle; ORB 30). Stop distances live ONLY here.
 304:     """
 305: 
 306:     stop_variant: str = "BASELINE"
 307:     t1_points: float = 27.0
 308:     rf_t2_points: float | None = RF_TARGET_RESEARCH_POINTS  # None => RF target unresolved (exits NOT_EVALUABLE)
 309:     # Phase 2.3 (USER_APPROVED): 6 lots in two equal legs of 3; the historical report used 65 units per lot (390 total, 195 per leg).
 310:     total_lots: int = 6
 311:     leg1_lots: int = 3
 312:     lot_size: int = 65  # configurable multiplier; index points are the research unit, this only scales synthetic P&L
 313:     # Phase 2.3 (USER_APPROVED): after Target 1 the remaining legs are protected by a stop 6 index points AGAINST the entry. No trailing.
 314:     post_t1_stop_mode: str = "BUFFER"  # "ENTRY_BREAKEVEN" is the SUPERSEDED performance-report rule, kept only for reconciliation
 315:     post_t1_buffer_points: float = 6.0
 316:     # Phase 3 (USER_APPROVED: positions are closed before 15:15; the price convention is a PROPOSAL): still open at this IST minute -> closed at that bar's open.
 317:     forced_exit_time: time | None = None  # None = Phase 2.3 behaviour (a position open at the end of the fillable bars is left unresolved)
 318: 
 319:     def __post_init__(self) -> None:
 320:         if self.stop_variant not in STOP_VARIANTS:
 321:             raise ConfigError(f"stop_variant={self.stop_variant!r} not in {STOP_VARIANTS}")
 322:         if self.total_lots < 2 or self.total_lots % 2 or self.leg1_lots * 2 != self.total_lots:
 323:             raise ConfigError("the position must be split into two EQUAL legs (total_lots even, leg1_lots = total_lots / 2)")
 324:         if self.lot_size < 1:
 325:             raise ConfigError("lot_size must be >= 1")
 326:         if self.post_t1_stop_mode not in ("BUFFER", "ENTRY_BREAKEVEN"):
 327:             raise ConfigError(f"post_t1_stop_mode={self.post_t1_stop_mode!r}")
 328:         if self.post_t1_buffer_points < 0:
 329:             raise ConfigError("post_t1_buffer_points must be >= 0")
 330:         if self.post_t1_buffer_points > min(STOP_BASELINE.values()):
 331:             raise ConfigError("the post-T1 stop may never be wider than the smallest initial stop (no widening)")
 332: 
 333:     def stop_points(self, strategy: str) -> float | None:
 334:         """The configured stop distance; None when the variant needs a per-trade measurement."""
 335:         if self.stop_variant == "BASELINE":
 336:             return STOP_BASELINE[strategy]
 337:         if self.stop_variant == "ALTERNATE_40":
 338:             return STOP_ALTERNATE[strategy]
 339:         return STOP_BASELINE["ORB"] if strategy == "ORB" else None
 340: 
 341:     def stop_status(self, strategy: str) -> str:
 342:         if strategy == "ORB":
 343:             return VERIFIED_EXPLICIT
 344:         return USER_APPROVED if self.stop_variant == "BASELINE" else PROPOSAL_LABEL
 345: 
 346:     def t2_points(self, strategy: str) -> float | None:
 347:         if strategy == "RF":
 348:             return self.rf_t2_points
 349:         return T2_TABLE[strategy][0]
 350: 
 351:     def t2_status(self, strategy: str) -> str:
 352:         return T2_TABLE[strategy][1] if (strategy != "RF" or self.rf_t2_points is not None) else "UNRESOLVED"
 353: 
 354: 
 355: DEFAULT_TRADE = TradeConfig()
```

## src/nifty_trading/data/sessions.py

```python
   1: """Session classification, 5-minute candle construction and causal indicators.
   2: 
   3: Timestamp convention (verified against the Phase 1 dataset, see
   4: ``reports/phase2/dataset_verification.md``): a 1-minute row labelled ``HH:MM`` covers
   5: ``[HH:MM:00, HH:MM+1:00)``. The 09:15 row is a full-size bar and the 15:30 row is a
   6: closing-print stub (74.8% zero-range). Hence a 5-minute candle labelled ``09:15``
   7: aggregates the rows 09:15..09:19, is complete only at 09:20:00 and may not be used before.
   8: 
   9: Nothing here fabricates data: a 5-minute candle with fewer than five 1-minute rows is
  10: dropped, never interpolated.
  11: 
  12: Phase 2.1 corrections (see ``docs/phase2/data_repair_report.md``):
  13: * From 2026-08-03 NSE runs a Closing Auction Session: the index is frozen from 15:15 until the official
  14:   close appears. Frozen rows inside that window on/after that date are REAL and are kept (flagged); a frozen
  15:   run anywhere else is an anomaly and marks the session CORRUPT.
  16: * The official close is the vendor DAILY close (confirmed against published closes); the 15:30 minute print is
  17:   only a fallback because before the auction regime it is the last tick, not the official close.
  18: * Pre-period 1-minute data may be supplied as WARM-UP ONLY: it seeds the EMA but is never evaluated.
  19: """
  20: 
  21: from __future__ import annotations
  22: 
  23: import glob
  24: from dataclasses import dataclass, field
  25: from datetime import date, time, timedelta
  26: from enum import Enum
  27: from pathlib import Path
  28: 
  29: import numpy as np
  30: import pandas as pd
  31: 
  32: from nifty_trading.data.market_calendar import MarketCalendar, load_market_calendar
  33: 
  34: SESSION_OPEN = time(9, 15)
  35: LAST_MINUTE_LABEL = time(15, 29)  # last full 1-minute bar of a normal session
  36: CLOSE_STUB_LABEL = time(15, 30)  # closing-print stub, excluded from candles
  37: CANDLE_MINUTES = 5
  38: EXPECTED_5M_CANDLES = 75  # 09:15 .. 15:25 start labels
  39: EMA_PERIOD_DEFAULT = 200
  40: STALE_RUN_MIN = 5  # consecutive identical flat 1-minute rows that mark a frozen index
  41: DAILY_MA_PERIOD = 200
  42: OFFICIAL_CLOSE_TOLERANCE = 0.05
  43: 
  44: 
  45: class SessionStatus(str, Enum):
  46:     USABLE = "USABLE"
  47:     USABLE_WITH_FLAGS = "USABLE_WITH_FLAGS"
  48:     EXCLUDED_NON_STANDARD_START = "EXCLUDED_NON_STANDARD_START"  # e.g. Muhurat session
  49:     EXCLUDED_NO_OPENING_CANDLE = "EXCLUDED_NO_OPENING_CANDLE"  # 09:15 candle incomplete
  50:     EXCLUDED_CORRUPT = "EXCLUDED_CORRUPT"
  51:     EXCLUDED_UNVERIFIED = "EXCLUDED_UNVERIFIED"
  52: 
  53: 
  54: class SessionQuality(str, Enum):
  55:     """Per-day data-quality status (Phase 2.1)."""
  56: 
  57:     VALID = "VALID"
  58:     VALID_SPECIAL_SESSION = "VALID_SPECIAL_SESSION"
  59:     PARTIAL = "PARTIAL"
  60:     CORRUPT = "CORRUPT"
  61:     MISSING = "MISSING"
  62:     UNVERIFIED = "UNVERIFIED"
  63: 
  64: 
  65: @dataclass(frozen=True)
  66: class SessionInfo:
  67:     date: date
  68:     status: SessionStatus
  69:     flags: tuple[str, ...]
  70:     n_1m_rows: int
  71:     n_5m_candles: int
  72:     official_close: float | None  # vendor daily close when supplied, else the 15:30 print
  73:     close_source: str  # "DAILY_VENDOR" | "STUB_1530" | "LAST_1529" | "NONE"
  74:     quality: SessionQuality = SessionQuality.VALID
  75:     reasons: tuple[str, ...] = ()  # why the quality is not VALID (empty for VALID)
  76:     cas_regime: bool = False  # closing-auction regime applies to this date
  77:     stub_close: float | None = None  # the 15:30 minute print, kept for the official-close comparison
  78: 
  79:     @property
  80:     def usable(self) -> bool:
  81:         """True when strategies may evaluate this session."""
  82:         return self.status in (SessionStatus.USABLE, SessionStatus.USABLE_WITH_FLAGS)
  83: 
  84: 
  85: def _processed_dir(processed_dir: str | Path | None) -> Path:
  86:     if processed_dir is None:
  87:         from nifty_trading.config.settings import settings
  88: 
  89:         processed_dir = settings.processed_data_dir
  90:     return Path(processed_dir)
  91: 
  92: 
  93: def load_one_minute(processed_dir: str | Path | None = None) -> pd.DataFrame:
  94:     """Read every Phase 1 Parquet partition into one chronologically sorted frame."""
  95:     pattern = str(_processed_dir(processed_dir) / "nifty50" / "year=*" / "month=*" / "candles.parquet")
  96:     files = sorted(glob.glob(pattern))
  97:     if not files:
  98:         raise FileNotFoundError(f"no parquet partitions match {pattern}")
  99:     df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
 100:     return df.sort_values("timestamp").reset_index(drop=True)
 101: 
 102: 
 103: def load_warmup_one_minute(processed_dir: str | Path | None = None) -> pd.DataFrame | None:
 104:     """Pre-period 1-minute data (WARM-UP ONLY: seeds indicators, never evaluated). None when not present."""
 105:     files = sorted(glob.glob(str(_processed_dir(processed_dir) / "nifty50_warmup" / "year=*" / "month=*" / "candles.parquet")))
 106:     if not files:
 107:         return None
 108:     return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True).sort_values("timestamp").reset_index(drop=True)
 109: 
 110: 
 111: def load_daily_official(processed_dir: str | Path | None = None) -> pd.DataFrame | None:
 112:     """Vendor daily candles (official closes) with columns date, open, high, low, close. None when not present."""
 113:     f = _processed_dir(processed_dir) / "nifty50_daily" / "candles.parquet"
 114:     if not f.exists():
 115:         return None
 116:     df = pd.read_parquet(f)
 117:     df["date"] = pd.to_datetime(df["date"]).dt.date
 118:     return df.sort_values("date").reset_index(drop=True)
 119: 
 120: 
 121: def stale_row_mask(rows: pd.DataFrame, min_run: int = STALE_RUN_MIN) -> pd.Series:
 122:     """True for rows inside a run of >= ``min_run`` consecutive 1-minute rows that all equal one frozen price.
 123: 
 124:     Whether such a run is an anomaly or the expected closing-auction freeze is decided by the caller
 125:     (``classify_session``): inside 15:15-15:29 on/after 2026-08-03 it is expected; anywhere else it is not.
 126:     """
 127:     flat = ((rows["open"] == rows["high"]) & (rows["high"] == rows["low"]) & (rows["low"] == rows["close"])).to_numpy()
 128:     price = rows["close"].to_numpy()
 129:     mins = (rows["timestamp"].dt.hour * 60 + rows["timestamp"].dt.minute).to_numpy()
 130:     out = np.zeros(len(rows), dtype=bool)
 131:     i = 0
 132:     while i < len(rows):
 133:         if not flat[i]:
 134:             i += 1
 135:             continue
 136:         j = i
 137:         while j + 1 < len(rows) and flat[j + 1] and price[j + 1] == price[i] and mins[j + 1] == mins[j] + 1:
 138:             j += 1
 139:         if j - i + 1 >= min_run:
 140:             out[i:j + 1] = True
 141:         i = j + 1
 142:     return pd.Series(out, index=rows.index)
 143: 
 144: 
 145: def _day_5m(day_df: pd.DataFrame, exclude_buckets_of: pd.Series | None = None) -> tuple[pd.DataFrame, int]:
 146:     """Aggregate one session's 1-minute rows. Returns (complete candles, dropped candle count).
 147: 
 148:     ``exclude_buckets_of``: optional boolean mask (aligned to ``day_df``) of rows whose whole 5-minute candle must be
 149:     dropped (used for anomalous frozen runs). Dropped candles are never repaired.
 150:     """
 151:     cols = ["bar_start", "bar_end", "open", "high", "low", "close", "n_minutes"]
 152:     t = day_df["timestamp"]
 153:     minute_of_day = t.dt.hour * 60 + t.dt.minute
 154:     lo = SESSION_OPEN.hour * 60 + SESSION_OPEN.minute
 155:     hi = LAST_MINUTE_LABEL.hour * 60 + LAST_MINUTE_LABEL.minute
 156:     sel = day_df[(minute_of_day >= lo) & (minute_of_day <= hi)].copy()
 157:     if sel.empty:
 158:         return pd.DataFrame(columns=cols), 0
 159:     sel["bucket"] = (minute_of_day[sel.index] - lo) // CANDLE_MINUTES
 160:     sel = sel.sort_values("timestamp")
 161:     if exclude_buckets_of is not None and exclude_buckets_of.any():
 162:         bad = set(sel.loc[exclude_buckets_of.reindex(sel.index, fill_value=False), "bucket"])
 163:         sel = sel[~sel["bucket"].isin(bad)]
 164:     if sel.empty:
 165:         return pd.DataFrame(columns=cols), 0
 166:     g = sel.groupby("bucket", sort=True)
 167:     agg = g.agg(
 168:         bar_start=("timestamp", "min"),
 169:         open=("open", "first"),
 170:         high=("high", "max"),
 171:         low=("low", "min"),
 172:         close=("close", "last"),
 173:         n_minutes=("timestamp", "nunique"),
 174:     ).reset_index(drop=True)
 175:     complete = agg[agg["n_minutes"] == CANDLE_MINUTES].copy()
 176:     dropped = len(agg) - len(complete)
 177:     complete["bar_end"] = complete["bar_start"] + pd.Timedelta(minutes=CANDLE_MINUTES)
 178:     return complete[cols].reset_index(drop=True), dropped
 179: 
 180: 
 181: def _info(d, status, quality, reasons, flags, n_rows, n_candles, official, src, cas, stub):
 182:     return SessionInfo(d, status, tuple(flags), n_rows, n_candles, official, src, quality, tuple(reasons), cas, stub)
 183: 
 184: 
 185: def classify_session(
 186:     day_df: pd.DataFrame,
 187:     calendar: MarketCalendar | None = None,
 188:     daily_close: float | None = None,
 189: ) -> tuple[SessionInfo, pd.DataFrame]:
 190:     """Classify one calendar day of 1-minute rows, assign its quality status and build its complete 5-minute candles.
 191: 
 192:     ``calendar`` defaults to an empty calendar (no special sessions, no closing-auction regime), which keeps the
 193:     behaviour of a bare call conservative. ``daily_close`` is the vendor's official daily close for the date, if known.
 194:     """
 195:     cal = calendar or MarketCalendar()
 196:     d = day_df["timestamp"].iloc[0].date()
 197:     flags: list[str] = []
 198:     reasons: list[str] = []
 199:     times = day_df["timestamp"].dt.time
 200:     n_rows = len(day_df)
 201:     cas = bool(cal.closing_auction and cal.closing_auction.applies(d))
 202: 
 203:     stub = day_df[times == CLOSE_STUB_LABEL]
 204:     stub_close = float(stub["close"].iloc[0]) if len(stub) else None
 205:     if daily_close is not None:
 206:         official, src = float(daily_close), "DAILY_VENDOR"
 207:         if stub_close is not None and abs(stub_close - official) > OFFICIAL_CLOSE_TOLERANCE:
 208:             flags.append(f"OFFICIAL_CLOSE_DIFFERS_FROM_1530_PRINT:{official - stub_close:+.2f}")
 209:     elif stub_close is not None:
 210:         official, src = stub_close, "STUB_1530"
 211:     else:
 212:         last = day_df[times == LAST_MINUTE_LABEL]
 213:         official, src = (float(last["close"].iloc[0]), "LAST_1529") if len(last) else (None, "NONE")
 214: 
 215:     # --- non-standard start (special evening sessions etc.)
 216:     if times.min() != SESSION_OPEN:
 217:         entry = cal.special_sessions.get(d)
 218:         q = SessionQuality.VALID_SPECIAL_SESSION if entry else SessionQuality.UNVERIFIED
 219:         return _info(d, SessionStatus.EXCLUDED_NON_STANDARD_START, q,
 220:                      ["NON_STANDARD_START" + (":" + entry.name if entry else ":not in calendar")],
 221:                      ["NON_STANDARD_START"], n_rows, 0, official, src, cas, stub_close), pd.DataFrame()
 222: 
 223:     # --- weekend sessions must be known special sessions
 224:     quality = SessionQuality.VALID
 225:     if d.weekday() >= 5:
 226:         entry = cal.special_sessions.get(d)
 227:         flags.append("WEEKEND_SPECIAL_SESSION")
 228:         if entry is None:
 229:             return _info(d, SessionStatus.EXCLUDED_UNVERIFIED, SessionQuality.UNVERIFIED, ["WEEKEND_SESSION_NOT_IN_CALENDAR"],
 230:                          flags, n_rows, 0, official, src, cas, stub_close), pd.DataFrame()
 231:         quality = SessionQuality.VALID_SPECIAL_SESSION
 232:         if not entry.evaluable_by_strategies:
 233:             return _info(d, SessionStatus.EXCLUDED_NON_STANDARD_START, quality, ["SPECIAL_SESSION_NOT_EVALUABLE"],
 234:                          flags, n_rows, 0, official, src, cas, stub_close), pd.DataFrame()
 235: 
 236:     # --- structural integrity
 237:     if day_df["timestamp"].duplicated().any():
 238:         return _info(d, SessionStatus.EXCLUDED_CORRUPT, SessionQuality.CORRUPT, ["DUPLICATE_TIMESTAMPS"], flags, n_rows, 0,
 239:                      official, src, cas, stub_close), pd.DataFrame()
 240:     bad_ohlc = ((day_df["high"] < day_df[["open", "close"]].max(axis=1)) | (day_df["low"] > day_df[["open", "close"]].min(axis=1))
 241:                 | day_df[["open", "high", "low", "close"]].isna().any(axis=1))
 242:     if bad_ohlc.any():
 243:         return _info(d, SessionStatus.EXCLUDED_CORRUPT, SessionQuality.CORRUPT, [f"OHLC_INCONSISTENT_ROWS:{int(bad_ohlc.sum())}"],
 244:                      flags, n_rows, 0, official, src, cas, stub_close), pd.DataFrame()
 245: 
 246:     after_close = int((times > CLOSE_STUB_LABEL).sum())
 247:     if after_close:
 248:         flags.append(f"POST_CLOSE_RECORDS_CLIPPED:{after_close}")
 249: 
 250:     # --- frozen runs: expected inside the auction window on/after the regime date, an anomaly anywhere else
 251:     in_window = day_df[(times >= SESSION_OPEN) & (times <= LAST_MINUTE_LABEL)].sort_values("timestamp")
 252:     frozen = stale_row_mask(in_window) if len(in_window) else pd.Series(dtype=bool)
 253:     anomalous = pd.Series(False, index=day_df.index)
 254:     if frozen.any():
 255:         fr = in_window[frozen]
 256:         ftimes = fr["timestamp"].dt.time
 257:         if cas and cal.closing_auction is not None:
 258:             inside = (ftimes >= cal.closing_auction.frozen_start) & (ftimes <= cal.closing_auction.frozen_end)
 259:             flags.append(f"CAS_FROZEN_WINDOW_KEPT:{int(inside.sum())}")
 260:             outside = fr[~inside.to_numpy()]
 261:             # the expected auction freeze starts at 15:15/15:16 (the index stops updating when continuous trading ends); a run that starts
 262:             # later inside the window is a feed stall that merely looks similar, so the session cannot be called VALID
 263:             late_start = fr[inside.to_numpy()]["timestamp"].dt.time.min() > time(15, 16) if inside.any() else False
 264:             if late_start:
 265:                 reasons.append("FROZEN_RUN_INSIDE_AUCTION_WINDOW_STARTS_AFTER_1516")
 266:                 return _info(d, SessionStatus.EXCLUDED_UNVERIFIED, SessionQuality.UNVERIFIED, reasons, flags, n_rows, 0, official, src, cas,
 267:                              stub_close), pd.DataFrame()
 268:         else:
 269:             outside = fr
 270:         if len(outside):
 271:             anomalous.loc[outside.index] = True
 272:             reasons.append(f"FROZEN_FEED_OUTSIDE_AUCTION_WINDOW:{len(outside)}")
 273:             quality = SessionQuality.CORRUPT
 274: 
 275:     candles, dropped = _day_5m(day_df, anomalous)
 276:     if dropped:
 277:         flags.append(f"INCOMPLETE_5M_CANDLES_DROPPED:{dropped}")
 278:         reasons.append(f"MISSING_MINUTE_BARS_IN_{dropped}_CANDLES")
 279:         if quality is SessionQuality.VALID or quality is SessionQuality.VALID_SPECIAL_SESSION:
 280:             quality = SessionQuality.PARTIAL
 281:     if stub_close is None:
 282:         flags.append("MISSING_1530_CLOSE_STUB")  # non-critical: the official close comes from the daily series
 283: 
 284:     if quality is SessionQuality.CORRUPT:
 285:         return _info(d, SessionStatus.EXCLUDED_CORRUPT, quality, reasons, flags, n_rows, len(candles), official, src, cas,
 286:                      stub_close), candles
 287:     if candles.empty or candles["bar_start"].iloc[0].time() != SESSION_OPEN:
 288:         return _info(d, SessionStatus.EXCLUDED_NO_OPENING_CANDLE, SessionQuality.PARTIAL, reasons + ["NO_COMPLETE_OPENING_CANDLE"],
 289:                      flags + ["NO_COMPLETE_OPENING_CANDLE"], n_rows, len(candles), official, src, cas, stub_close), candles
 290:     status = SessionStatus.USABLE_WITH_FLAGS if flags else SessionStatus.USABLE
 291:     return _info(d, status, quality, reasons, flags, n_rows, len(candles), official, src, cas, stub_close), candles
 292: 
 293: 
 294: def causal_ema(values: np.ndarray, period: int) -> np.ndarray:
 295:     """EMA seeded with the SMA of the first ``period`` values.
 296: 
 297:     Output is NaN for the first ``period - 1`` positions: no partially-initialised value is
 298:     ever returned. Each output depends only on values at or before its own position.
 299:     """
 300:     n = len(values)
 301:     out = np.full(n, np.nan)
 302:     if n < period:
 303:         return out
 304:     alpha = 2.0 / (period + 1.0)
 305:     out[period - 1] = float(np.mean(values[:period]))
 306:     for i in range(period, n):
 307:         out[i] = alpha * values[i] + (1.0 - alpha) * out[i - 1]
 308:     return out
 309: 
 310: 
 311: def causal_sma(values: np.ndarray, period: int) -> np.ndarray:
 312:     n = len(values)
 313:     out = np.full(n, np.nan)
 314:     if n < period:
 315:         return out
 316:     c = np.cumsum(np.insert(values, 0, 0.0))
 317:     out[period - 1:] = (c[period:] - c[:-period]) / period
 318:     return out
 319: 
 320: 
 321: @dataclass
 322: class PreviousSession:
 323:     date: date
 324:     open: float
 325:     high: float  # of ALL complete 5-minute candles (the 15:30 print is never a candle)
 326:     low: float
 327:     close_official: float | None
 328:     last_5m_close: float
 329:     candles: pd.DataFrame
 330:     ema_at_last_candle: float  # NaN when EMA warm-up was incomplete
 331:     gap_to_this_session_unverified: bool  # something between prev and today makes 'previous day' uncertain
 332:     continuous_candles: pd.DataFrame | None = None  # candles before the closing auction (== candles outside the regime)
 333:     close_source: str = "STUB_1530"
 334:     close_1530_print: float | None = None  # last 1-minute print at 15:30 (alternative previous-close definition)
 335: 
 336:     @property
 337:     def high_continuous(self) -> float:
 338:         c = self.continuous_candles if self.continuous_candles is not None else self.candles
 339:         return float(c["high"].max())
 340: 
 341:     @property
 342:     def low_continuous(self) -> float:
 343:         c = self.continuous_candles if self.continuous_candles is not None else self.candles
 344:         return float(c["low"].min())
 345: 
 346: 
 347: @dataclass
 348: class SessionContext:
 349:     """Everything a strategy may know at/after 09:20 of one session. Causal by construction."""
 350: 
 351:     date: date
 352:     info: SessionInfo
 353:     candles: pd.DataFrame  # complete 5-minute candles + ``ema200_5m`` column
 354:     previous: PreviousSession | None
 355:     open_price: float  # first 1-minute open (09:15 row)
 356:     daily_history_count: int  # number of prior OFFICIAL daily bars available (>= 200 needed for the daily MA)
 357:     daily_sma200_prev: float  # SMA of the last 200 official daily closes strictly before this session (NaN if <200)
 358:     daily_ema200_prev: float
 359:     prior_session_ema_above: tuple[bool | None, ...]  # per prior session (newest first): last 5m close > EMA?
 360:     data_flags: tuple[str, ...] = field(default_factory=tuple)
 361: 
 362:     @property
 363:     def prev_close(self) -> float | None:
 364:         return None if self.previous is None else self.previous.close_official
 365: 
 366:     def prefix(self, n_candles: int) -> SessionContext:
 367:         """The same session as it looked after ``n_candles`` candles had closed (for look-ahead tests)."""
 368:         return SessionContext(**{**self.__dict__, "candles": self.candles.iloc[:n_candles].reset_index(drop=True)})
 369: 
 370: 
 371: def build_session_contexts(
 372:     df_1m: pd.DataFrame,
 373:     ema_period: int = EMA_PERIOD_DEFAULT,
 374:     verified_holidays: set[date] | None = None,
 375:     *,
 376:     calendar: MarketCalendar | None = None,
 377:     daily_df: pd.DataFrame | None = None,
 378:     warmup_1m: pd.DataFrame | None = None,
 379: ) -> tuple[dict[date, SessionContext], dict[date, SessionInfo]]:
 380:     """Classify all sessions, build 5-minute candles and the causal indicator inputs.
 381: 
 382:     ``warmup_1m`` rows precede ``df_1m``: they seed the EMA and supply the previous session of the first evaluated day,
 383:     but no context or info is produced for them. ``daily_df`` (date, open, high, low, close) supplies official closes and
 384:     the daily moving averages (which need >= 200 earlier daily bars).
 385:     """
 386:     cal = calendar if calendar is not None else load_market_calendar()
 387:     if verified_holidays is None:
 388:         verified_holidays = set(cal.holidays)
 389:     analysis_start = df_1m["timestamp"].dt.date.min()
 390:     frames = [warmup_1m, df_1m] if warmup_1m is not None else [df_1m]
 391:     df = pd.concat(frames, ignore_index=True).sort_values("timestamp").reset_index(drop=True)
 392:     df["_d"] = df["timestamp"].dt.date
 393:     daily_close_by_date: dict[date, float] = {}
 394:     if daily_df is not None:
 395:         daily_close_by_date = dict(zip(daily_df["date"], daily_df["close"].astype(float), strict=True))
 396:     infos: dict[date, SessionInfo] = {}
 397:     candles_by_day: dict[date, pd.DataFrame] = {}
 398:     for d, day_df in df.groupby("_d", sort=True):
 399:         info, c = classify_session(day_df.drop(columns="_d"), cal, daily_close_by_date.get(d))
 400:         infos[d] = info
 401:         if info.usable:
 402:             candles_by_day[d] = c
 403: 
 404:     usable = sorted(candles_by_day)
 405:     # ---- 5-minute EMA over the concatenated, chronologically ordered, complete candles
 406:     if usable:
 407:         closes = np.concatenate([candles_by_day[d]["close"].to_numpy() for d in usable])
 408:         ema = causal_ema(closes, ema_period)
 409:         pos = 0
 410:         for d in usable:
 411:             n = len(candles_by_day[d])
 412:             candles_by_day[d]["ema200_5m"] = ema[pos:pos + n]
 413:             pos += n
 414: 
 415:     # ---- daily moving averages: official daily closes strictly BEFORE the session (never including its own close)
 416:     if daily_df is not None and len(daily_df):
 417:         dd_dates = list(daily_df["date"])
 418:         dd_close = daily_df["close"].to_numpy(dtype=float)
 419:     else:  # fall back to the closes of the evaluated sessions themselves
 420:         dd_dates = usable
 421:         dd_close = np.array([infos[d].official_close if infos[d].official_close is not None
 422:                              else candles_by_day[d]["close"].iloc[-1] for d in usable], dtype=float)
 423:     sma_d = causal_sma(dd_close, DAILY_MA_PERIOD)
 424:     ema_d = causal_ema(dd_close, DAILY_MA_PERIOD)
 425: 
 426:     import bisect
 427: 
 428:     ctxs: dict[date, SessionContext] = {}
 429:     out_infos: dict[date, SessionInfo] = {d: i for d, i in infos.items() if d >= analysis_start}
 430:     above: list[bool | None] = []  # chronological: last 5m close > EMA for each usable session
 431:     for k, d in enumerate(usable):
 432:         c = candles_by_day[d]
 433:         e_end = float(c["ema200_5m"].iloc[-1])
 434:         flags: list[str] = []
 435:         prev: PreviousSession | None = None
 436:         if k > 0:
 437:             pd_ = usable[k - 1]
 438:             pc = candles_by_day[pd_]
 439:             between = pd.date_range(pd_ + timedelta(days=1), d - timedelta(days=1)).date
 440:             missing_weekdays = [x for x in between if x.weekday() < 5 and x not in infos and x not in verified_holidays]
 441:             excluded_between = [x for x in between if x in infos and not infos[x].usable]
 442:             prev_close_day_differs = False
 443:             if daily_close_by_date:
 444:                 prior_rows = [x for x in dd_dates if x < d]
 445:                 prev_close_day_differs = bool(prior_rows) and prior_rows[-1] != pd_
 446:             close_fallback = bool(daily_close_by_date) and infos[pd_].close_source != "DAILY_VENDOR"
 447:             close_doubt: list[str] = []
 448:             if not daily_close_by_date:  # without the official daily close, post-close prints make the close ambiguous
 449:                 close_doubt = [f for f in infos[pd_].flags if f.startswith("POST_CLOSE_RECORDS")]
 450:             cont = pc
 451:             if infos[pd_].cas_regime and cal.closing_auction is not None:
 452:                 cont = pc[pc["bar_end"].dt.time <= cal.closing_auction.frozen_start].reset_index(drop=True)
 453:             prev = PreviousSession(
 454:                 date=pd_, open=float(pc["open"].iloc[0]), high=float(pc["high"].max()), low=float(pc["low"].min()),
 455:                 close_official=infos[pd_].official_close, last_5m_close=float(pc["close"].iloc[-1]), candles=pc,
 456:                 ema_at_last_candle=float(pc["ema200_5m"].iloc[-1]),
 457:                 gap_to_this_session_unverified=bool(missing_weekdays or excluded_between or prev_close_day_differs or close_doubt or close_fallback),
 458:                 continuous_candles=cont, close_source=infos[pd_].close_source, close_1530_print=infos[pd_].stub_close,
 459:             )
 460:             if missing_weekdays:
 461:                 flags.append("PREV_SESSION_GAP_UNVERIFIED:" + ",".join(map(str, missing_weekdays)))
 462:             if excluded_between:
 463:                 flags.append("PREV_SESSION_SKIPS_EXCLUDED_SESSION:" + ",".join(map(str, excluded_between)))
 464:             if prev_close_day_differs:
 465:                 flags.append(f"PREV_CLOSE_DAY_DIFFERS_FROM_PREV_SESSION({pd_})")
 466:             if close_fallback:  # the official close fell back to the 15:30 print (error up to 88 points before the auction regime)
 467:                 flags.append(f"PREV_CLOSE_FALLBACK_TO_1530_PRINT({pd_})")
 468:             if close_doubt:
 469:                 flags.append(f"PREV_CLOSE_UNRELIABLE({pd_}:{'|'.join(close_doubt)})")
 470:         else:
 471:             flags.append("NO_PREVIOUS_SESSION_IN_DATASET")
 472:         if d >= analysis_start:
 473:             idx = bisect.bisect_left(dd_dates, d) - 1 if daily_df is not None else k - 1
 474:             sma_v = float(sma_d[idx]) if idx >= 0 and not np.isnan(sma_d[idx]) else float("nan")
 475:             ema_v = float(ema_d[idx]) if idx >= 0 and not np.isnan(ema_d[idx]) else float("nan")
 476:             ctxs[d] = SessionContext(
 477:                 date=d, info=infos[d], candles=c, previous=prev, open_price=float(c["open"].iloc[0]),
 478:                 daily_history_count=max(idx + 1, 0), daily_sma200_prev=sma_v, daily_ema200_prev=ema_v,
 479:                 prior_session_ema_above=tuple(reversed(above)),
 480:                 data_flags=tuple(flags) + tuple(f"SESSION:{f}" for f in infos[d].flags),
 481:             )
 482:         above.append(None if np.isnan(e_end) else bool(c["close"].iloc[-1] > e_end))
 483:     return ctxs, out_infos
```

## src/nifty_trading/strategies/trading_day.py

```python
   1: """Shared portfolio-level trading-day controller (Phase 2.3, USER_APPROVED rules).
   2: 
   3: The five strategy engines stay exactly as they are: they emit signals. THIS module decides which signal becomes a trade, in strict
   4: chronological order, for the whole day:
   5: 
   6:   * the FIRST valid signal of any strategy opens the first trade (SEL-FIRST-001);
   7:   * while a position is active every later signal is ignored for execution and kept in a diagnostic log (SEL-ACTIVE-001);
   8:   * signals of different strategies (or opposite directions) at the same timestamp are a logged CONFLICT; no strategy is chosen unless a
   9:     TieBreakPolicy explicitly marked ``approved`` is configured (SEL-TIE-001/002) - otherwise the day is UNRESOLVED_EXECUTION;
  10:   * first trade -> Target 2: the day is finished (DAY-T2-001); first trade -> Target 1 then the post-T1 buffer stop: finished (DAY-BUF-001);
  11:   * first trade -> ORIGINAL full stop before Target 1: ONE more trade, only PDR or PDS, only from a signal confirmed after the first
  12:     position has fully closed - an earlier ignored signal is never reused (DAY-SL-001, DAY-NOREUSE-001);
  13:   * first trade closed by end of day / unresolved execution / not evaluable: no second trade (DAY-UNRES-001);
  14:   * at most 2 entries per day (DAY-MAX-001); no entry with a fill later than 13:00:00 IST (ENTRY-CUTOFF-001).
  15: 
  16: It consumes signal records and 1-minute bars of ONE session and returns the trades and the complete diagnostic log. It does not
  17: download, place orders or run a profitability backtest; the P&L it carries is synthetic index-point P&L of the exit model.
  18: """
  19: 
  20: from __future__ import annotations
  21: 
  22: from collections.abc import Sequence
  23: from dataclasses import dataclass, field, replace
  24: from datetime import date, datetime, time
  25: from enum import Enum
  26: from zoneinfo import ZoneInfo
  27: 
  28: from nifty_trading.core.execution_eligibility import ENTRY_CUTOFF, entry_within_cutoff
  29: from nifty_trading.core.exit_policy import Bar, ExitResult, TradeOutcome
  30: from nifty_trading.strategies.base import SignalRecord, SignalStatus
  31: from nifty_trading.strategies.params import DEFAULT_TRADE, TradeConfig
  32: from nifty_trading.strategies.rules import implements
  33: from nifty_trading.strategies.selection import (
  34:     NO_POSITION,
  35:     fill_from_next_bar,
  36:     is_valid,
  37:     position_end_from_result,
  38:     simulate_exit,
  39: )
  40: 
  41: IST = ZoneInfo("Asia/Kolkata")
  42: 
  43: 
  44: class DayState(str, Enum):
  45:     READY_FOR_FIRST_TRADE = "READY_FOR_FIRST_TRADE"
  46:     FIRST_TRADE_ACTIVE = "FIRST_TRADE_ACTIVE"
  47:     SECOND_TRADE_ELIGIBLE = "SECOND_TRADE_ELIGIBLE"
  48:     SECOND_TRADE_ACTIVE = "SECOND_TRADE_ACTIVE"
  49:     DAY_FINISHED = "DAY_FINISHED"
  50:     UNRESOLVED_EXECUTION = "UNRESOLVED_EXECUTION"
  51: 
  52: 
  53: @dataclass(frozen=True)
  54: class TieBreakPolicy:
  55:     """Priority between strategies that signal at the same timestamp. ``approved`` must be True to be applied: NO such policy is approved
  56:     today, so the default ``DayRules.tie_break`` is None. (Tests use a policy marked approved only to exercise the machinery.)"""
  57: 
  58:     priority: tuple[str, ...]
  59:     approved: bool = False
  60:     source: str = ""
  61: 
  62: 
  63: @dataclass(frozen=True)
  64: class DayRules:
  65:     entry_cutoff: time = ENTRY_CUTOFF
  66:     max_entries: int = 2
  67:     second_trade_strategies: tuple[str, ...] = ("PDR", "PDS")
  68:     tie_break: TieBreakPolicy | None = None
  69:     # What an UNRESOLVED same-minute collision does. MARK_DAY_UNRESOLVED (default, the Phase 2.3/3.0 convention): no trade and the day ends.
  70:     # SKIP_COLLISION_EVENT_CONTINUE_DAY: a DIAGNOSTIC counterfactual (Phase 3.1) - the colliding signals are skipped, the conflict is logged and later
  71:     # signals may still trade. Neither is an approved policy.
  72:     collision_policy: str = "MARK_DAY_UNRESOLVED"
  73: 
  74:     def __post_init__(self) -> None:
  75:         if self.collision_policy not in ("MARK_DAY_UNRESOLVED", "SKIP_COLLISION_EVENT_CONTINUE_DAY"):
  76:             raise ValueError(f"collision_policy={self.collision_policy!r}")
  77: 
  78: 
  79: @dataclass
  80: class DiagnosticEntry:
  81:     timestamp: datetime | None
  82:     strategy: str
  83:     method: str
  84:     direction: str
  85:     event: str  # IGNORED | REJECTED | CONFLICT | NOTE
  86:     reason: str
  87: 
  88: 
  89: @dataclass
  90: class TradeRecord:
  91:     trade_no: int
  92:     signal: SignalRecord
  93:     fill_timestamp: datetime
  94:     entry_price: float
  95:     result: ExitResult
  96:     classification: str  # TARGET | T1_THEN_BUFFER_STOP | INITIAL_FULL_STOP | BREAKEVEN(legacy) | INCOMPLETE_EOD | NOT_EVALUABLE
  97:     position_end: object  # datetime | None (never closed) - NO_POSITION cannot occur for an accepted trade
  98:     concurrent_methods: list[str] = field(default_factory=list)
  99: 
 100: 
 101: @dataclass
 102: class DayResult:
 103:     day: date
 104:     final_state: DayState
 105:     trades: list[TradeRecord] = field(default_factory=list)
 106:     diagnostics: list[DiagnosticEntry] = field(default_factory=list)
 107:     state_trace: list[str] = field(default_factory=list)
 108: 
 109:     @property
 110:     def conflicts(self) -> list[DiagnosticEntry]:
 111:         return [d for d in self.diagnostics if d.event == "CONFLICT"]
 112: 
 113:     def reasons(self) -> list[str]:
 114:         return [d.reason for d in self.diagnostics]
 115: 
 116: 
 117: _CLASS = {TradeOutcome.TARGET: "TARGET", TradeOutcome.T1_THEN_BUFFER_STOP: "T1_THEN_BUFFER_STOP", TradeOutcome.INITIAL_FULL_STOP: "INITIAL_FULL_STOP",
 118:           TradeOutcome.BREAKEVEN: "BREAKEVEN", TradeOutcome.FORCED_EXIT: "FORCED_EXIT", TradeOutcome.INCOMPLETE_EOD: "INCOMPLETE_EOD", TradeOutcome.NOT_EVALUABLE: "NOT_EVALUABLE"}
 119: 
 120: 
 121: @implements("SEL-FIRST-001", "SEL-ACTIVE-001", "SEL-TIE-001", "SEL-TIE-002", "SEL-TIE-003", "DAY-T2-001", "DAY-BUF-001", "DAY-SL-001", "DAY-NOREUSE-001",
 122:             "DAY-UNRES-001", "DAY-MAX-001", "ENTRY-CUTOFF-001")
 123: def run_trading_day(day: date, records: Sequence[SignalRecord], day_bars: Sequence[Bar], trade: TradeConfig = DEFAULT_TRADE,
 124:                     rules: DayRules | None = None) -> DayResult:
 125:     """Run the state machine over one session. ``records`` may mix all five strategies; only CONFIRMED ones are considered.
 126:     ``day_bars`` are the session's 1-minute bars (with their ``executable`` flags). Deterministic and causal: a decision at time t
 127:     reads only signals confirmed at or before t and bars from the fill bar onwards (the exit model walks forward from the fill)."""
 128:     rules = rules or DayRules()
 129:     res = DayResult(day, DayState.READY_FOR_FIRST_TRADE)
 130:     state = DayState.READY_FOR_FIRST_TRADE
 131:     res.state_trace.append(f"{state.value} (start of day)")
 132: 
 133:     def set_state(new: DayState, why: str, ts=None) -> DayState:
 134:         stamp = f"{ts:%H:%M} " if ts is not None else ""
 135:         res.state_trace.append(f"{stamp}{state.value} -> {new.value}: {why}")
 136:         return new
 137: 
 138:     def log(ts, r: SignalRecord, event: str, reason: str) -> None:
 139:         res.diagnostics.append(DiagnosticEntry(ts, r.strategy, r.method, r.direction, event, reason))
 140: 
 141:     usable: list[SignalRecord] = []
 142:     for r in records:
 143:         if r.signal_status != SignalStatus.CONFIRMED.value or r.signal_timestamp is None:
 144:             continue
 145:         if r.signal_date != day:  # a record of another session must never leak into this day
 146:             log(r.signal_timestamp, r, "REJECTED", f"RECORD_FOR_ANOTHER_DAY({r.signal_date})")
 147:             continue
 148:         if r.signal_timestamp.tzinfo is None:  # a naive timestamp is exchange (IST) wall-clock time
 149:             r = replace(r, signal_timestamp=r.signal_timestamp.replace(tzinfo=IST))
 150:         usable.append(r)
 151:     confirmed = sorted(usable, key=lambda r: (r.signal_timestamp, r.strategy, r.method))
 152:     groups: list[tuple[datetime, list[SignalRecord]]] = []
 153:     for r in confirmed:
 154:         if groups and groups[-1][0] == r.signal_timestamp:
 155:             groups[-1][1].append(r)
 156:         else:
 157:             groups.append((r.signal_timestamp, [r]))
 158: 
 159:     active: TradeRecord | None = None
 160: 
 161:     def settle(at: datetime | None) -> None:
 162:         """The active position has closed (or the data ended): move to the state its outcome dictates."""
 163:         nonlocal state, active
 164:         assert active is not None
 165:         cls = active.classification
 166:         first = active.trade_no == 1
 167:         if cls in ("TARGET", "T1_THEN_BUFFER_STOP", "BREAKEVEN", "FORCED_EXIT"):
 168:             new, why = DayState.DAY_FINISHED, f"first trade {cls}" if first else f"second trade {cls}"
 169:         elif cls == "INITIAL_FULL_STOP":
 170:             new, why = (DayState.SECOND_TRADE_ELIGIBLE, "first trade INITIAL_FULL_STOP: one PDR/PDS trade allowed") if first else (
 171:                 DayState.DAY_FINISHED, "second trade INITIAL_FULL_STOP")
 172:         else:  # INCOMPLETE_EOD / NOT_EVALUABLE
 173:             new, why = DayState.UNRESOLVED_EXECUTION, f"trade {active.trade_no} {cls}: exit unresolved (nothing is invented)"
 174:         state = set_state(new, why, at)
 175:         active = None
 176: 
 177:     for ts, recs in groups:
 178:         # 1) a position that has closed by now settles first
 179:         if active is not None and active.position_end is not None and ts >= active.position_end:
 180:             settle(active.position_end)
 181:         # 2) terminal states and active positions only log
 182:         if state in (DayState.DAY_FINISHED, DayState.UNRESOLVED_EXECUTION):
 183:             for r in recs:
 184:                 log(ts, r, "IGNORED", "DAY_FINISHED" if state is DayState.DAY_FINISHED else "DAY_UNRESOLVED_EXECUTION")
 185:             continue
 186:         if state in (DayState.FIRST_TRADE_ACTIVE, DayState.SECOND_TRADE_ACTIVE):
 187:             for r in recs:
 188:                 log(ts, r, "IGNORED", "POSITION_ACTIVE (signal kept for diagnostics only; never reused)")
 189:             continue
 190:         # 3) READY_FOR_FIRST_TRADE or SECOND_TRADE_ELIGIBLE: look for an executable candidate
 191:         second = state is DayState.SECOND_TRADE_ELIGIBLE
 192:         cands: list[SignalRecord] = []
 193:         for r in recs:
 194:             if second and r.strategy not in rules.second_trade_strategies:
 195:                 log(ts, r, "REJECTED", "SECOND_TRADE_RESTRICTED_TO_" + "_".join(rules.second_trade_strategies))
 196:                 continue
 197:             ok, why = is_valid(r)
 198:             if not ok:
 199:                 log(ts, r, "REJECTED", why)
 200:                 continue
 201:             if not entry_within_cutoff(ts, rules.entry_cutoff):
 202:                 log(ts, r, "REJECTED", f"ENTRY_CUTOFF_EXCEEDED(fill {ts:%H:%M} IST > {rules.entry_cutoff:%H:%M})")
 203:                 continue
 204:             if fill_from_next_bar(day_bars, ts) is None:
 205:                 log(ts, r, "REJECTED", "ENTRY_NOT_FILLABLE(no fillable bar starts at the signal candle's end)")
 206:                 continue
 207:             cands.append(r)
 208:         if not cands:
 209:             continue
 210:         chosen, concurrent = _choose(cands, rules, ts, res, log)
 211:         if chosen is None:  # unresolved collision
 212:             if rules.collision_policy == "SKIP_COLLISION_EVENT_CONTINUE_DAY":
 213:                 res.state_trace.append(f"{ts:%H}:{ts:%M} {state.value}: collision skipped, day continues (diagnostic counterfactual policy)")
 214:                 continue
 215:             state = set_state(DayState.UNRESOLVED_EXECUTION, "simultaneous signals without an approved tie-break policy", ts)
 216:             continue
 217:         for r in cands:
 218:             if r is not chosen and r.strategy == chosen.strategy and r.direction == chosen.direction:
 219:                 log(ts, r, "NOTE", f"SAME_STRATEGY_CONCURRENT_METHOD (traded as {chosen.method}; identical entry/stop/target)")
 220:         sim = simulate_exit(chosen, day_bars, trade)
 221:         assert sim is not None  # fill_from_next_bar succeeded above
 222:         fill = fill_from_next_bar(day_bars, ts)
 223:         end = position_end_from_result(sim)
 224:         if end is NO_POSITION:  # NOT_EVALUABLE exit policy: the entry happened but its exit cannot be simulated -> unresolved, never closes
 225:             end = None
 226:         no = len(res.trades) + 1
 227:         if no > rules.max_entries:  # defensive: the state machine already prevents it
 228:             log(ts, chosen, "REJECTED", "MAX_ENTRIES_PER_DAY")
 229:             continue
 230:         tr = TradeRecord(no, chosen, ts, fill[0], sim, _CLASS[sim.outcome], end, concurrent)
 231:         res.trades.append(tr)
 232:         active = tr
 233:         state = set_state(DayState.SECOND_TRADE_ACTIVE if second else DayState.FIRST_TRADE_ACTIVE,
 234:                           f"{chosen.strategy} {chosen.method} {chosen.direction} entered at {fill[0]}", ts)
 235: 
 236:     # end of the signal list: the last position resolves
 237:     if active is not None:
 238:         settle(active.position_end)
 239:     res.final_state = state
 240:     return res
 241: 
 242: 
 243: def _choose(cands: list[SignalRecord], rules: DayRules, ts, res: DayResult, log) -> tuple[SignalRecord | None, list[str]]:
 244:     """One candidate, or several of the same strategy and direction (identical trade): that trade. Otherwise a conflict."""
 245:     strategies = {r.strategy for r in cands}
 246:     directions = {r.direction for r in cands}
 247:     if len(strategies) == 1 and len(directions) == 1:
 248:         first = cands[0]
 249:         return first, [r.method for r in cands[1:]]
 250:     detail = ", ".join(f"{r.strategy}/{r.method}/{r.direction}" for r in cands)
 251:     pol = rules.tie_break
 252:     if pol is not None and pol.approved:
 253:         for name in pol.priority:
 254:             hit = [r for r in cands if r.strategy == name]
 255:             if hit:
 256:                 if len({r.direction for r in hit}) > 1:  # the winner itself signals both ways at once: still a conflict, never method-name order
 257:                     break
 258:                 for r in cands:
 259:                     if r is not hit[0]:
 260:                         log(ts, r, "IGNORED", f"LOST_APPROVED_TIE_BREAK_TO_{name}")
 261:                 res.diagnostics.append(DiagnosticEntry(ts, name, hit[0].method, hit[0].direction, "NOTE", f"TIE_BREAK_APPLIED({pol.source or 'approved policy'}): {detail}"))
 262:                 return hit[0], []
 263:     res.diagnostics.append(DiagnosticEntry(ts, "+".join(sorted(strategies)), "ALL", "+".join(sorted(directions)), "CONFLICT",
 264:                                            f"SIMULTANEOUS_SIGNAL_CONFLICT_UNRESOLVED: {detail}"))
 265:     return None, []
```

## src/nifty_trading/strategies/irf.py

```python
   1: """IRF - Initial Range Failure (short only). Source: ``IRF_Strategy_Guide Updated.pdf``.
   2: 
   3: Three source-defined entry methods are kept separate:
   4:   Method 1   breakout close above IRH, the very next candle closes back inside the range.
   5:   Method 2A  extension + red candle, then a candle closes below recent support.
   6:   Method 2B  extension + red candle, then a red candle closes back below recent resistance.
   7:   Method 3   liquidity sweep: compression inside the range, then a red candle with a long upper wick
   8:              above IRH that closes below recent support (compulsory).
   9: """
  10: 
  11: from __future__ import annotations
  12: 
  13: from dataclasses import dataclass, field
  14: from typing import Any
  15: 
  16: from nifty_trading.data.sessions import SessionContext
  17: from nifty_trading.strategies.base import (
  18:     Direction,
  19:     SetupFSM,
  20:     SignalEngine,
  21:     SignalRecord,
  22:     SignalStatus,
  23:     State,
  24: )
  25: from nifty_trading.strategies.definitions import (
  26:     Candle,
  27:     compression_ok,
  28:     is_green,
  29:     is_red,
  30:     most_recent_colour,
  31:     recent_resistance,
  32:     recent_support,
  33:     wick_share_in_band,
  34:     wick_share_outside,
  35: )
  36: from nifty_trading.strategies.rules import implements
  37: 
  38: _GLOBAL = ["IRF-GLOBAL-001", "IRF-GLOBAL-002", "IRF-GLOBAL-003"]
  39: 
  40: 
  41: @dataclass
  42: class _Attempt:
  43:     b: int  # breakout candle index
  44:     fsm: SetupFSM
  45:     e: int | None = None  # extension candle index
  46:     r: int | None = None  # first red candle at/after the extension
  47:     pending_flags: list[str] = field(default_factory=list)
  48: 
  49: 
  50: class IRFStrategy(SignalEngine):
  51:     STRATEGY = "IRF"
  52:     METHODS = ("Method 1", "Method 2A", "Method 2B", "Method 3")
  53:     REQUIRES_PREVIOUS_SESSION = False  # IRF uses only the opening range and intraday candles
  54: 
  55:     # ------------------------------------------------------------------ main scan
  56:     @implements("IRF-GLOBAL-001", "IRF-GLOBAL-002", "IRF-GLOBAL-003", "IRF-GLOBAL-004", "IRF-GLOBAL-005", "IRF-M2-004", "IRF-M2-006", "IRF-SL-001")
  57:     def _scan(self, ctx: SessionContext, cs: list[Candle], gap_before: list[bool]) -> list[SignalRecord]:
  58:         irh, irl = cs[0].h, cs[0].l
  59:         out: list[SignalRecord] = []
  60:         att: _Attempt | None = None  # Method 2 attempt keyed to one breakout close
  61:         win = self.p.m1_max_candles_after_breakout
  62:         for i in range(1, len(cs)):
  63:             c = cs[i]
  64:             if gap_before[i] and att is not None:
  65:                 att.fsm.to(State.SETUP_INVALIDATED, c.start, "DATA_GAP")
  66:                 out.append(self._setup_record(ctx, cs, att, "DATA_GAP", i))
  67:                 att = None
  68:             out.extend(self._method3(ctx, cs, i, irh, irl, gap_before))
  69:             m1 = self._method1(ctx, cs, i, irh, irl, gap_before)  # Method 1 is history-independent
  70:             if m1 is not None:
  71:                 out.append(m1[0])
  72:                 if att is not None and att.b == m1[1]:
  73:                     att = None  # IRF p.9: immediate close back inside makes it Method 1, not Method 2
  74:             if att is not None:
  75:                 # the extension / red-candle bookkeeping runs from the first candle after the breakout; only the
  76:                 # confirmation is held back while Method 1 may still fire (window; D-IRF-1)
  77:                 att, recs = self._m2_step(ctx, cs, att, i, irh, irl, may_confirm=i - att.b >= win)
  78:                 out.extend(recs)
  79:             if att is None and c.c > irh and not gap_before[i]:
  80:                 fsm = SetupFSM(f"IRF breakout@{c.end:%H:%M}")
  81:                 fsm.to(State.SETUP_DETECTED, c.end, f"close {c.c} > IRH {irh} (IRF-M1-001/M2-001)")
  82:                 att = _Attempt(b=i, fsm=fsm)
  83:         if att is not None and not att.fsm.terminal:
  84:             out.append(self._setup_record(ctx, cs, att, "SESSION_ENDED_BEFORE_CONFIRMATION", len(cs) - 1,
  85:                                           status=SignalStatus.INCOMPLETE_AT_EOD))
  86:         return out
  87: 
  88:     # ------------------------------------------------------------------ Method 1
  89:     @implements("IRF-M1-001", "IRF-M1-002", "IRF-M1-004", "IRF-M1-003", "IRF-M1-C001")
  90:     def _method1(self, ctx, cs, i: int, irh: float, irl: float, gap_before: list[bool]):
  91:         """Candle b closes above IRH and candle b+1 (== i) closes back inside the range."""
  92:         below_irl_ok = self.p.m1_close_below_irl_counts_as_inside
  93: 
  94:         def inside(x: Candle) -> bool:
  95:             return (irl <= x.c < irh) or (below_irl_ok and x.c < irl)
  96: 
  97:         if not inside(cs[i]):
  98:             return None
  99:         for k in range(1, self.p.m1_max_candles_after_breakout + 1):
 100:             b = i - k
 101:             if b < 1 or any(gap_before[b + 1:i + 1]):
 102:                 break
 103:             if cs[b].c > irh and all(not inside(cs[m]) for m in range(b + 1, i)):
 104:                 sat = _GLOBAL + ["IRF-M1-001", "IRF-M1-002", "IRF-M1-004"]
 105:                 flags: list[str] = []
 106:                 if cs[i].c < irl:
 107:                     sat.append("IRF-M1-003")
 108:                     flags.append("M1_CLOSE_BELOW_IRL_COUNTED_AS_INSIDE(proposal)")
 109:                 if k > 1:
 110:                     sat.append("IRF-M1-C001")
 111:                     flags.append(f"M1_FAILURE_ON_CANDLE_{k}_AFTER_BREAKOUT(research variant of p.14)")
 112:                 fsm = SetupFSM(f"IRF M1@{cs[i].end:%H:%M}")
 113:                 fsm.to(State.SETUP_DETECTED, cs[b].end, f"close {cs[b].c} > IRH {irh}")
 114:                 fsm.to(State.SIGNAL_CONFIRMED, cs[i].end, f"candle +{k} closes {cs[i].c} back inside [{irl},{irh})")
 115:                 return self._confirmed(ctx, cs, i, "Method 1", b, irh, irl, sat, fsm.trace, flags,
 116:                                        {"breakout_close": cs[b].c, "breakout_candle_start": cs[b].start}), b
 117:         return None
 118: 
 119:     # ------------------------------------------------------------------ Method 2 (A and B)
 120:     @implements("IRF-M2-001", "IRF-M2-002", "IRF-M2-003", "IRF-M2-005", "IRF-M2A-002", "IRF-M2B-002", "IRF-M2B-003")
 121:     def _m2_step(self, ctx, cs, att: _Attempt, i: int, irh: float, irl: float, may_confirm: bool = True):
 122:         c, b = cs[i], att.b
 123:         if may_confirm and att.fsm.state is State.SETUP_DETECTED:
 124:             att.fsm.to(State.WAITING_FOR_CONFIRMATION, c.end, "Method 1 window passed; Method 2 path (IRF-M2-004)")
 125:         if self.p.m2_expiry_candles is not None and i - b > self.p.m2_expiry_candles:
 126:             att.fsm.to(State.SETUP_INVALIDATED, c.end, "M2_EXPIRED(proposal)")
 127:             return None, [self._setup_record(ctx, cs, att, "M2_EXPIRED", i)]
 128:         # --- extension (IRF-M2-002) and red candle (IRF-M2-003), both recorded causally
 129:         if att.e is None and i > b:
 130:             ext = (c.h > cs[b].h) if self.p.m2_extension_definition == "E1" else (c.c > irh)
 131:             if ext:
 132:                 att.e = i
 133:         if att.e is not None and att.r is None:
 134:             first_ok = att.e if self.p.m2_red_may_be_extension_candle else att.e + 1
 135:             if i >= first_ok and is_red(c):
 136:                 att.r = i
 137:         if not may_confirm:
 138:             return att, []
 139:         recs: list[SignalRecord] = []
 140:         proposals = {"irf_support_def": self.p.irf_support_def, "irf_resistance_def": self.p.irf_resistance_def,
 141:                      "m2_extension_definition": self.p.m2_extension_definition}
 142:         # ---- Confirmation A: a candle closes below recent support
 143:         red_ok = att.r is not None and (att.r <= i if self.p.m2a_break_may_be_red_candle else att.r < i)
 144:         if red_ok and att.e is not None:
 145:             sup = recent_support(cs, b + 1, i, self.p)
 146:             if sup is not None and c.c < sup[1]:
 147:                 recs.append(("Method 2A", {"recent_support": sup[1], "support_candle_index": sup[0]},
 148:                              ["IRF-M2-001", "IRF-M2-002", "IRF-M2-003", "IRF-M2A-001", "IRF-M2A-002"]))
 149:         # ---- Confirmation B: red candle closes back below recent resistance after trading above it
 150:         res = recent_resistance(cs, b, i, self.p)
 151:         if res is not None and is_red(c) and c.c < res[1]:
 152:             j, rlvl = res
 153:             last_push = i if not self.p.m2b_push_must_precede_red_candle else i - 1
 154:             pushed = any(cs[m].h > rlvl for m in range(j + 1, last_push + 1))
 155:             if pushed:
 156:                 recs.append(("Method 2B", {"recent_resistance": rlvl, "resistance_candle_index": j},
 157:                              ["IRF-M2-001", "IRF-M2B-001", "IRF-M2B-002", "IRF-M2B-003"]))
 158:         if not recs:
 159:             return att, []
 160:         att.fsm.to(State.SIGNAL_CONFIRMED, c.end, "; ".join(m for m, _, _ in recs) + " trigger on close")
 161:         out = [self._confirmed(ctx, cs, i, m, b, irh, irl, _GLOBAL + sat + ["IRF-M2-005"], att.fsm.trace, [],
 162:                                {**extra, "breakout_close": cs[b].c, "extension_index": att.e, "red_candle_index": att.r},
 163:                                proposals=proposals)
 164:                for m, extra, sat in recs]
 165:         return None, out
 166: 
 167:     # ------------------------------------------------------------------ Method 3
 168:     @implements("IRF-M3-001", "IRF-M3-002", "IRF-M3-003", "IRF-M3-004", "IRF-M3-005", "IRF-M3-006")
 169:     def _method3(self, ctx, cs, i: int, irh: float, irl: float, gap_before: list[bool]) -> list[SignalRecord]:
 170:         c = cs[i]
 171:         n = self.p.m3_compression_n
 172:         if not (is_red(c) and c.h > irh):  # IRF-M3-002
 173:             return []
 174:         if any(gap_before[i - n + 1:i + 1]) if i - n >= 0 else True:
 175:             return []
 176:         if not compression_ok(cs, i, irl, irh, self.p):  # IRF-M3-001
 177:             return []
 178:         fsm = SetupFSM(f"IRF sweep@{c.end:%H:%M}")
 179:         fsm.to(State.SETUP_DETECTED, c.end, "red candle with high above IRH after compression inside range")
 180:         share = wick_share_outside(c, irh)
 181:         props = {"m3_compression_def": self.p.m3_compression_def, "m3_compression_n": n,
 182:                  "m3_wick_share_band": self.p.m3_wick_share_band, "irf_support_def": self.p.irf_support_def}
 183:         levels = {"IRH": irh, "IRL": irl, "wick_share_outside_irh": share}
 184:         sat = _GLOBAL + ["IRF-M3-001", "IRF-M3-002"]
 185:         if not wick_share_in_band(share, self.p):
 186:             fsm.to(State.SETUP_INVALIDATED, c.end, f"wick share {share} outside band (IRF-M3-003/006)")
 187:             return [self._rec(ctx, c, "Method 3", Direction.SHORT, levels, sat, ["IRF-M3-003"], [], SignalStatus.INVALIDATED,
 188:                               "WICK_SHARE_OUT_OF_BAND", fsm.trace, props)]
 189:         sat.append("IRF-M3-003")
 190:         sup = recent_support(cs, 1, i, self.p)
 191:         if sup is None:
 192:             fsm.to(State.SETUP_INVALIDATED, c.end, "no recent support identifiable")
 193:             return [self._rec(ctx, c, "Method 3", Direction.SHORT, levels, sat, ["IRF-M3-004"], [], SignalStatus.INVALIDATED,
 194:                               "NO_RECENT_SUPPORT", fsm.trace, props)]
 195:         levels["recent_support"] = sup[1]
 196:         sat.append("IRF-M3-004")
 197:         if not (c.c < sup[1]):  # IRF-M3-005 compulsory
 198:             fsm.to(State.SETUP_INVALIDATED, c.end, f"close {c.c} not below support {sup[1]}")
 199:             return [self._rec(ctx, c, "Method 3", Direction.SHORT, levels, sat, ["IRF-M3-005"], [], SignalStatus.INVALIDATED,
 200:                               "SUPPORT_NOT_BROKEN(sweep alone is never enough)", fsm.trace, props)]
 201:         fsm.to(State.SIGNAL_CONFIRMED, c.end, f"close {c.c} < support {sup[1]}")
 202:         sat.append("IRF-M3-005")
 203:         return [self._confirmed(ctx, cs, i, "Method 3", 0, irh, irl, sat, fsm.trace, [], levels, proposals=props)]
 204: 
 205:     # ------------------------------------------------------------------ record builders
 206:     def _confirmed(self, ctx, cs, i, method, setup_start, irh, irl, sat, trace, flags, extra, proposals=None):
 207:         c = cs[i]
 208:         gj = most_recent_colour(cs, i, True)
 209:         greens = [cs[j] for j in range(setup_start, i + 1) if is_green(cs[j])]
 210:         levels: dict[str, Any] = {
 211:             "IRH": irh, "IRL": irl, "entry_reference_price": c.c,
 212:             "recent_green_high": cs[gj].h if gj is not None else None,
 213:             "recent_green_close": cs[gj].c if gj is not None else None,
 214:             "setup_green_high": max((g.h for g in greens), default=None),
 215:             **extra,
 216:         }
 217:         # IRF-GLOBAL-004: trades per day / time window / re-arming are not defined in the guide, so no IRF signal
 218:         # can be called verified. IRF-GLOBAL-005: concurrent methods are reported separately, never merged.
 219:         return self._rec(ctx, c, method, Direction.SHORT, levels, sat, [], ["IRF-GLOBAL-004"], SignalStatus.CONFIRMED, None,
 220:                          trace, proposals or {}, flags)
 221: 
 222:     def _setup_record(self, ctx, cs, att: _Attempt, why: str, i: int, status=SignalStatus.INVALIDATED):
 223:         c = cs[att.b]
 224:         return self._rec(ctx, c, "Method 1/2", Direction.SHORT, {"IRH": cs[0].h, "IRL": cs[0].l},
 225:                          ["IRF-M1-001"], [], [], status, why, att.fsm.trace)
```

## src/nifty_trading/strategies/irf_phase53.py

```python
   1: """Phase 5.3 IRF: the owner-approved corrections as an opt-in, separately versioned engine (the frozen ``IRFStrategy`` and the Phase 5.2 candidate class are not modified).
   2: 
   3: Owner decisions implemented (Phase 5.3 brief):
   4: 
   5: 1. FIRST RED CANDLE'S LOW is the support of Method 2A (``support_ref="FIRST_RED_LOW"``; the actual low including the wick, never the body low or the close). The reference candle is the earliest qualifying
   6:    completed red candle of the attempt and is never replaced by a later one. Scope: Method 2A ONLY. Method 2B's reference is a RESISTANCE (the top of the first push; the red candle is the confirming candle, not
   7:    the creator of a level), Method 1 has no support level and Method 3's support is "formed by the preceding candles" (IRF guide); none of them is changed.
   8:    Provisional assumption ``first_red_search_start``: the guide orders the steps breakout -> extension -> pullback low -> red candle -> close below, so the search starts AFTER THE EXTENSION candle (the engine's
   9:    existing bookkeeping, default). The alternative ``AFTER_BREAKOUT`` (the first red candle after the breakout candle, even before the extension) is kept as a selectable variant so its effect can be reported.
  10: 
  11: 2. MINIMUM 28-POINT EMA CLEARANCE (``ema_min_clearance=28.0``, convention ``PROVISIONAL_EMA_RANGE_DISTANCE``): the nearest point of the completed signal candle's high-low range must be at least 28 points from the
  12:    latest causally available EMA(200) of completed five-minute candles (the value that includes the signal candle's own close, which exists when the candle ends = the decision time; never a later value). The 28 is inclusive
  13:    (a distance of exactly 28.0 passes). A candidate that fails is REJECTED and logged in ``self.rejections``. For Method 2 the attempt stays alive after a rejection (a later candle of the same attempt may still qualify);
  14:    Methods 1 and 3 are history-independent per candle, so their rejected candidates are simply removed. The convention is NOT confirmed as the author's meaning; the range distance does not guarantee price space towards
  15:    Target 1 (the diagnostics report where the EMA lies relative to the candle and between entry and Target 1).
  16:    ``ema_scope``: ``ALL_METHODS`` (the clarification is about IRF as a whole; the guide has no EMA text, so no method is excluded) or ``METHOD2_ONLY`` (a selectable variant).
  17: 
  18: Everything else (extension, the first-red bookkeeping, the entry on the close of the confirming candle, the 13:00 cutoff applied by the base class, stops and targets) is the frozen behaviour.
  19: """
  20: 
  21: from __future__ import annotations
  22: 
  23: import math
  24: from typing import Any
  25: 
  26: from nifty_trading.strategies.base import SignalRecord, SignalStatus, State
  27: from nifty_trading.strategies.definitions import is_red, recent_resistance
  28: from nifty_trading.strategies.irf import _GLOBAL, _Attempt
  29: from nifty_trading.strategies.irf_candidates import SUPPORT_REFS, IRFFirstRedStrategy
  30: 
  31: RED_SEARCH_STARTS = ("AFTER_EXTENSION", "AFTER_BREAKOUT")
  32: EMA_SCOPES = ("ALL_METHODS", "METHOD2_ONLY")
  33: EMA_MEASURES = ("RANGE", "CLOSE")  # RANGE = nearest point of the candle's high-low range (the Phase 5.3 convention); CLOSE = |close - EMA| (diagnostic variant)
  34: EPS = 1e-9
  35: 
  36: 
  37: def ema_geometry(h: float, l: float, c: float, ema: float) -> dict[str, Any]:
  38:     """Where the EMA lies relative to the candle and the two candidate distances. ``range_clearance`` is 0 when the EMA lies inside the candle's high-low range."""
  39:     if ema > h:
  40:         rel, rng = "EMA_ABOVE_CANDLE", ema - h
  41:     elif ema < l:
  42:         rel, rng = "EMA_BELOW_CANDLE", l - ema
  43:     else:
  44:         rel, rng = "EMA_INSIDE_CANDLE", 0.0
  45:     return {"relation": rel, "range_clearance": rng, "close_distance": abs(c - ema)}
  46: 
  47: 
  48: class IRFPhase53Strategy(IRFFirstRedStrategy):
  49:     """IRF with the Phase 5.3 owner-approved corrections (see the module docstring). With the default arguments it equals the frozen engine."""
  50: 
  51:     def __init__(self, name=None, params=None, proposals=None, trade=None, support_ref: str = "BASELINE_SWING", red_search_start: str = "AFTER_EXTENSION",
  52:                  ema_min_clearance: float | None = None, ema_scope: str = "ALL_METHODS", ema_measure: str = "RANGE"):
  53:         super().__init__(name, params, proposals, trade, support_ref=support_ref)
  54:         if support_ref not in SUPPORT_REFS:
  55:             raise ValueError(support_ref)
  56:         if red_search_start not in RED_SEARCH_STARTS or ema_scope not in EMA_SCOPES or ema_measure not in EMA_MEASURES:
  57:             raise ValueError((red_search_start, ema_scope, ema_measure))
  58:         self.red_search_start = red_search_start
  59:         self.ema_min_clearance = ema_min_clearance
  60:         self.ema_scope = ema_scope
  61:         self.ema_measure = ema_measure
  62:         self.rejections: list[dict[str, Any]] = []  # candidates rejected by the EMA clearance (read and cleared by the runner after each session)
  63: 
  64:     # ------------------------------------------------------------------ the EMA clearance gate
  65:     def _ema_gate(self, ctx, cs, i: int, method: str) -> tuple[bool, dict[str, Any]]:
  66:         """(passes, info) for the completed candle ``i`` as the confirming candle of ``method``. No EMA value (warm-up) -> the candidate is NOT rejected (unknown is not 'less than 28') and the case is flagged."""
  67:         c = cs[i]
  68:         e = ctx.candles["ema200_5m"].iloc[i]
  69:         if e is None or (isinstance(e, float) and math.isnan(e)):
  70:             return True, {"ema_available": False}
  71:         e = float(e)
  72:         g = ema_geometry(c.h, c.l, c.c, e)
  73:         dist = g["range_clearance"] if self.ema_measure == "RANGE" else g["close_distance"]
  74:         info = {"ema_available": True, "ema200": e, "measure": self.ema_measure, "distance": dist, **g, "method": method, "signal_time": f"{c.end:%H:%M}",
  75:                 "candle_ohlc": f"{c.o}/{c.h}/{c.l}/{c.c}", "min_clearance": self.ema_min_clearance}
  76:         return dist >= self.ema_min_clearance - EPS, info
  77: 
  78:     def _gated_methods(self) -> tuple[str, ...]:
  79:         return ("Method 1", "Method 2A", "Method 2B", "Method 3") if self.ema_scope == "ALL_METHODS" else ("Method 2A", "Method 2B")
  80: 
  81:     def _scan(self, ctx, cs, gap_before) -> list[SignalRecord]:
  82:         out = super()._scan(ctx, cs, gap_before)
  83:         if self.ema_min_clearance is None:
  84:             return out
  85:         kept: list[SignalRecord] = []
  86:         for r in out:
  87:             if r.signal_status == SignalStatus.CONFIRMED.value and r.method in ("Method 1", "Method 3") and r.method in self._gated_methods():
  88:                 i = next((k for k, c in enumerate(cs) if c.end == r.signal_timestamp), None)
  89:                 if i is not None:
  90:                     ok, info = self._ema_gate(ctx, cs, i, r.method)
  91:                     if not ok:
  92:                         self.rejections.append({"date": str(ctx.date), **info})
  93:                         continue
  94:                     r.flags.append(f"PHASE53_EMA_{self.ema_measure}_DISTANCE={info.get('distance', 'NA') if info.get('ema_available') else 'EMA_UNAVAILABLE'}")
  95:             kept.append(r)
  96:         return kept
  97: 
  98:     # ------------------------------------------------------------------ Method 2 (a copy of the Phase 5.2 step with TWO changes: the red-candle search start and the EMA veto)
  99:     def _m2_step(self, ctx, cs, att: _Attempt, i: int, irh: float, irl: float, may_confirm: bool = True):
 100:         c, b = cs[i], att.b
 101:         if may_confirm and att.fsm.state is State.SETUP_DETECTED:
 102:             att.fsm.to(State.WAITING_FOR_CONFIRMATION, c.end, "Method 1 window passed; Method 2 path (IRF-M2-004)")
 103:         if self.p.m2_expiry_candles is not None and i - b > self.p.m2_expiry_candles:
 104:             att.fsm.to(State.SETUP_INVALIDATED, c.end, "M2_EXPIRED(proposal)")
 105:             return None, [self._setup_record(ctx, cs, att, "M2_EXPIRED", i)]
 106:         if att.e is None and i > b:
 107:             ext = (c.h > cs[b].h) if self.p.m2_extension_definition == "E1" else (c.c > irh)
 108:             if ext:
 109:                 att.e = i
 110:         if att.r is None:
 111:             if self.red_search_start == "AFTER_BREAKOUT":  # variant: the first red candle after the breakout candle, whether or not the extension has happened yet
 112:                 if i > b and is_red(c):
 113:                     att.r = i
 114:             elif att.e is not None:  # default / frozen: the first red candle after the extension candle
 115:                 first_ok = att.e if self.p.m2_red_may_be_extension_candle else att.e + 1
 116:                 if i >= first_ok and is_red(c):
 117:                     att.r = i
 118:         if not may_confirm:
 119:             return att, []
 120:         recs: list[SignalRecord] = []
 121:         proposals = {"irf_support_def": self.p.irf_support_def, "irf_resistance_def": self.p.irf_resistance_def, "m2_extension_definition": self.p.m2_extension_definition,
 122:                      "phase53_support_ref": self.support_ref, "phase53_red_search_start": self.red_search_start, "phase53_ema_min_clearance": self.ema_min_clearance, "phase53_ema_scope": self.ema_scope,
 123:                      "phase53_ema_convention": "PROVISIONAL_EMA_RANGE_DISTANCE" if self.ema_min_clearance is not None else None}
 124:         red_ok = att.r is not None and (att.r <= i if self.p.m2a_break_may_be_red_candle else att.r < i)
 125:         if red_ok and att.e is not None:
 126:             sup = self._support_level(cs, att, b, i)
 127:             if sup is not None and c.c < sup[1]:
 128:                 recs.append(("Method 2A", {"recent_support": sup[1], "support_candle_index": sup[0], "support_ref": self.support_ref, "first_red_candle_start": f"{cs[att.r].start:%H:%M}",
 129:                                            "first_red_candle_low": cs[att.r].l},
 130:                              ["IRF-M2-001", "IRF-M2-002", "IRF-M2-003", "IRF-M2A-001", "IRF-M2A-002"]))
 131:         res = recent_resistance(cs, b, i, self.p)
 132:         if res is not None and is_red(c) and c.c < res[1]:
 133:             j, rlvl = res
 134:             last_push = i if not self.p.m2b_push_must_precede_red_candle else i - 1
 135:             pushed = any(cs[m].h > rlvl for m in range(j + 1, last_push + 1))
 136:             if pushed:
 137:                 recs.append(("Method 2B", {"recent_resistance": rlvl, "resistance_candle_index": j}, ["IRF-M2-001", "IRF-M2B-001", "IRF-M2B-002", "IRF-M2B-003"]))
 138:         if not recs:
 139:             return att, []
 140:         flags: list[str] = []
 141:         if self.ema_min_clearance is not None:
 142:             kept = []
 143:             for m, extra, sat in recs:
 144:                 if m in self._gated_methods():
 145:                     ok, info = self._ema_gate(ctx, cs, i, m)
 146:                     if not ok:
 147:                         self.rejections.append({"date": str(ctx.date), **info})  # rejected: the attempt stays alive; a later candle of the same attempt may still qualify
 148:                         continue
 149:                     flags = [f"PHASE53_EMA_{self.ema_measure}_DISTANCE={info.get('distance', 'NA') if info.get('ema_available') else 'EMA_UNAVAILABLE'}"]
 150:                 kept.append((m, extra, sat))
 151:             recs = kept
 152:             if not recs:
 153:                 return att, []
 154:         att.fsm.to(State.SIGNAL_CONFIRMED, c.end, "; ".join(m for m, _, _ in recs) + " trigger on close")
 155:         out = [self._confirmed(ctx, cs, i, m, b, irh, irl, _GLOBAL + sat + ["IRF-M2-005"], att.fsm.trace, list(flags),
 156:                                {**extra, "breakout_close": cs[b].c, "extension_index": att.e, "red_candle_index": att.r}, proposals=proposals)
 157:                for m, extra, sat in recs]
 158:         return None, out
```
