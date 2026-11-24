"""IRF V3 configuration, scenario labels and the rule-authority registry.

Authority vocabulary (derived ONLY from what the two PDFs print):
  STATED          printed as a rule in the rulebook with no 'TO CONFIRM' tag.
  TO_CONFIRM      printed in the rulebook explicitly tagged '(TO CONFIRM)'.
  SOURCE_SILENT   the rulebook is silent / ambiguous - an implementation convention had to be chosen (labelled, never author-approved).
  EXAMPLE_ONLY    value appears only in a chart label (approximate, screenshot-read).
Note: both PDFs say rules are marked CONFIRMED vs TO CONFIRM and that open items are collected in 'Open Items to Confirm'; neither PDF (8 pages each) contains a per-rule CONFIRMED tag or that section.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time

PDF1 = "IRF_Inverse_Retest_Failure_Rulebook.pdf"
PDF2 = "IRF_Method2_First_Red_Candle_Rulebook.pdf"

WINDOWS = {
    "A": (date(2025, 9, 1), date(2026, 8, 31)),
    "B": (date(2022, 9, 1), date(2025, 8, 31)),
}
TICK = 1e-9


@dataclass(frozen=True)
class IrfV3Config:
    """One reference scenario. Only the stop distance, the forced-exit clock and the tie policy differ between scenarios; the SIGNAL logic has no tunable parameter."""
    scenario_id: str = "SL40_T60"
    stop_points: float = 40.0              # source: 'about 35 to 40' - 35 and 40 are separately labelled scenarios (selection algorithm not defined)
    target_points: float = 60.0            # STATED (60 points below entry)
    entry_cutoff: time = time(13, 0)       # STATED 'no entry after 1 pm'; implemented as: entry (fill) bar start <= 13:00:00 inclusive (repo ENTRY-CUTOFF-001 reading)
    entry_convention: str = "NEXT_1M_OPEN"  # first causally available price after the failure candle closes; SIGNAL_CLOSE = source illustration (TO CONFIRM) used as a reference only
    tie_policy: str = "STOP_FIRST_5M"      # source: SL and target both touched inside one 5-minute candle -> SL first (TO CONFIRM). MINUTE_ORDER = chronological 1-minute alternative
    forced_exit: time = time(15, 14)       # SOURCE_SILENT ('end of the session, exit time to be confirmed'): open of the 15:14 bar (< 15:15), the repo forced-exit convention
    m2_invalidate_close_below_a: bool = False   # M2 variant (NOT in the source): a close below Level A before Level B is marked kills the setup. Default off: the PDF states no invalidation
    allow_red_breakout_candle_as_first_red: bool = False   # M2 reading: the rally-breakout candle itself may be the 'first red candle'? default NO ('first red candle AFTER the rally breakout')


PRIMARY = IrfV3Config()
SCENARIOS = {
    "SL40_T60": IrfV3Config("SL40_T60", 40.0),
    "SL35_T60": IrfV3Config("SL35_T60", 35.0),
}
# One-at-a-time sensitivity of the unresolved execution conventions (never headline results).
SENSITIVITY = {
    "SL40_ENTRY_SIGNAL_CLOSE": IrfV3Config("SL40_ENTRY_SIGNAL_CLOSE", 40.0, entry_convention="SIGNAL_CLOSE"),
    "SL40_TIE_MINUTE_ORDER": IrfV3Config("SL40_TIE_MINUTE_ORDER", 40.0, tie_policy="MINUTE_ORDER"),
    "SL40_FORCED_EXIT_1300": IrfV3Config("SL40_FORCED_EXIT_1300", 40.0, forced_exit=time(13, 0)),
    "SL35_FORCED_EXIT_1300": IrfV3Config("SL35_FORCED_EXIT_1300", 35.0, forced_exit=time(13, 0)),
    "SL40_CUTOFF_EXCLUSIVE": IrfV3Config("SL40_CUTOFF_EXCLUSIVE", 40.0, entry_cutoff=time(12, 59)),   # 'no entry after 1 pm' read as: a fill at 13:00:00 is NOT allowed
    "SL40_M2_INVALIDATE_BELOW_A": IrfV3Config("SL40_M2_INVALIDATE_BELOW_A", 40.0, m2_invalidate_close_below_a=True),
}

# (rule_id, method, rule, pdf, page, authority, implemented_as)
RULES: list[tuple] = [
    ("M1-R01", "M1", "Instrument Nifty 50 index, 5-minute chart", PDF1, 1, "STATED", "NIFTY 50 index, 5-minute candles built from 1-minute rows"),
    ("M1-R02", "M1", "Marked level = HIGH of the 09:15-09:20 candle including the upper wick; marked once after the candle closes and never moves", PDF1, "1,3", "STATED", "level = first-candle high; available from 09:20:00"),
    ("M1-R03", "M1", "Breakout = ANY later candle (green or red) CLOSES strictly above the marked level; a wick above that closes at/below is not a breakout", PDF1, "1,3,5", "STATED", "close > level (strict), candle colour ignored"),
    ("M1-R04", "M1", "Do not enter during the breakout", PDF1, "3", "STATED", "breakout never produces a signal"),
    ("M1-R05", "M1", "Failure = first LATER candle that CLOSES strictly below the marked level after a breakout candle has closed; may be immediate or many candles later", PDF1, "3,5", "STATED", "close < level (strict) after >=1 breakout close"),
    ("M1-R06", "M1", "Order matters: a close below the level with no earlier close above it is not a signal", PDF1, "4,5", "STATED", "state machine AWAIT_BREAKOUT -> AWAIT_FAILURE"),
    ("M1-R07", "M1", "SHORT entry once the failure candle has closed (no other confirmation candle)", PDF1, "3,5", "STATED", "signal_time = failure candle end"),
    ("M1-R08", "M1", "No trend restriction, no EMA(200), no previous-day S/R, no gap filter, no candle-body rule", PDF1, "1,2,8", "STATED", "no such filter exists in method1.py"),
    ("M1-R09", "M1", "First-candle colour is not restricted (example candle is green)", PDF1, "3", "TO_CONFIRM", "colour ignored"),
    ("M1-R10", "M1", "A candle closing exactly on the level is neither above nor below: ignored", PDF1, "5", "TO_CONFIRM", "equality is ignored (strict > and <)"),
    ("M1-R11", "M1", "Entry price E = close of the failure candle", PDF1, "5", "TO_CONFIRM", "primary: OPEN of the first 1-minute bar at/after confirmation (first causally available price); SIGNAL_CLOSE = reference sensitivity"),
    ("M1-R12", "M1", "Stop-loss = E + 35 to 40 points; the selection between 35 and 40 is not defined", PDF1, "1,5,6", "STATED", "two labelled scenarios SL35_T60 and SL40_T60; no choice is made"),
    ("M1-R13", "M1", "Target = E - 60 points; stop and target are measured from the entry price, not from the level", PDF1, "1,5", "STATED", "target 60 points"),
    ("M1-R14", "M1", "One trade per day; after the stop or target the strategy is finished for the day", PDF1, "1,5,8", "TO_CONFIRM", "first signal only; later cycles are counted as diagnostics (later_cycles), never traded"),
    ("M1-R15", "M1", "If stop and target are both touched inside one 5-minute candle the stop is counted first", PDF1, "5", "TO_CONFIRM", "tie_policy STOP_FIRST_5M (primary); MINUTE_ORDER sensitivity"),
    ("M1-R16", "M1", "No entry after 1 pm", PDF1, "1", "STATED", "fill bar start <= 13:00:00 (inclusive); later signals stay in the ledger flagged AFTER_CUTOFF"),
    ("M1-R17", "M1", "If neither stop nor target is hit the position is closed at the end of the session; exit time to be confirmed", PDF1, "5", "TO_CONFIRM", "forced exit at the open of the 15:14 bar (repo convention); 13:00 forced exit as sensitivity"),
    ("M1-R18", "M1", "The header row 'Latest entry time and exit time' prints only 'No entry after 1 Pm' (no exit time)", PDF1, 1, "SOURCE_SILENT", "exit clock treated as unresolved (see M1-R17)"),
    ("M1-R19", "M1", "Stop distances observed in examples 35.25-40.75 pts and targets 59.25-60.65 pts (chart labels, approximate)", PDF1, 6, "EXAMPLE_ONLY", "not implemented; fixed 35/40 and 60 scenarios"),
    ("M2-R01", "M2", "Instrument Nifty 50 index, 5-minute chart", PDF2, 1, "STATED", "NIFTY 50 index, 5-minute candles"),
    ("M2-R02", "M2", "Level A = HIGH of the 09:15-09:20 candle incl. upper wick", PDF2, "1,3", "STATED", "initial range high"),
    ("M2-R03", "M2", "Rally breakout = a later candle (green or red) CLOSES strictly above Level A; a wick above that closes at/below is not a breakout", PDF2, "3,5", "STATED", "close > A"),
    ("M2-R04", "M2", "Do not enter on the rally breakout; let the rally continue", PDF2, "3", "STATED", "no signal"),
    ("M2-R05", "M2", "Level B = TOP OF THE BODY of the FIRST RED candle in the rally = its open; the upper wick is ignored; only the first red candle sets Level B, later red candles are ignored", PDF2, "1,3,5", "STATED", "first candle with close < open after the rally-breakout candle; B = its open"),
    ("M2-R06", "M2", "A red candle forming BEFORE any candle has closed above Level A is ignored (not part of the rally); the examples show this", PDF2, "4,5", "TO_CONFIRM", "red candles before the rally breakout are ignored and counted"),
    ("M2-R07", "M2", "'First red candle AFTER the rally breakout forms': whether the breakout candle itself, if red, may be the first red candle is not stated", PDF2, "5", "SOURCE_SILENT", "primary: the breakout candle is excluded; variant M2_ALT_BREAKOUT_RED reported as sensitivity"),
    ("M2-R08", "M2", "Second breakout = a later candle CLOSES strictly above Level B; do not enter", PDF2, "3,5", "STATED", "close > B on a candle after the red candle"),
    ("M2-R09", "M2", "Failure = a later candle CLOSES strictly below Level B after the second breakout; immediate or many candles later", PDF2, "3,5", "STATED", "close < B after >=1 close > B"),
    ("M2-R10", "M2", "Order matters: a close below Level B with no earlier close above B is not a signal", PDF2, "4,5", "STATED", "state machine order"),
    ("M2-R11", "M2", "SHORT entry once the failure candle has closed", PDF2, "3,5", "STATED", "signal_time = failure candle end"),
    ("M2-R12", "M2", "No trend restriction, no EMA(200), no previous-day S/R, no gap filter", PDF2, "1,2,8", "STATED", "no such filter exists in method2.py"),
    ("M2-R13", "M2", "A candle closing exactly on a level is neither above nor below: ignored", PDF2, "5", "TO_CONFIRM", "strict > and <"),
    ("M2-R14", "M2", "Stop = entry + 35 to 40 points; target = entry - 60 points", PDF2, "1,5,6,7", "STATED", "same two labelled stop scenarios; 60-point target"),
    ("M2-R15", "M2", "1 trade per day", PDF2, "1,8", "TO_CONFIRM", "first signal only"),
    ("M2-R16", "M2", "Latest entry time and exit time: '1 pm' (single value for both)", PDF2, "2", "SOURCE_SILENT", "read as entry cutoff 13:00 (as in Method 1); a 13:00 forced exit is a sensitivity"),
    ("M2-R17", "M2", "Entry price, tie rule and end-of-session exit are NOT mentioned in the Method 2 text", PDF2, "all", "SOURCE_SILENT", "Method 2 uses the same labelled execution scenarios as Method 1 (an assumption, flagged)"),
    ("M2-R18", "M2", "Nothing says what happens if price closes back below Level A (or below B) before the second breakout: setup neither expires nor invalidates", PDF2, "all", "SOURCE_SILENT", "no invalidation implemented; the setup stays armed. Independent review: in window A the first red candle itself closes below Level A in about a third of rally sessions, so the headline M2 numbers depend on this reading; variant SL40_M2_INVALIDATE_BELOW_A (close below A before B is marked kills the setup) is reported as a sensitivity"),
    ("M2-R20", "M2", "'Red' is not defined numerically; a doji (close == open) is neither red nor green", PDF2, "3,5", "SOURCE_SILENT", "red = close < open strictly; a doji is not red and cannot set Level B"),
    ("M2-R21", "M2", "Example 4 (3 Nov 2026): the screenshot's entry equals the close of the candle AFTER the first candle that closes below Level B in secondary-vendor data (failure margin 0.70 pt); whether a minimum margin or a different candle is meant is not stated", PDF2, 7, "SOURCE_SILENT", "none: strict close below B on the first such candle; reported as a non-reproduction"),
    ("M2-R19", "M2", "No colour / body-strength requirement for any candle other than 'red' for the Level-B candle", PDF2, "3,5", "STATED", "none implemented"),
    ("X-R01", "BOTH", "Both methods use the same first-candle high as their first level (Method 1 marked level == Method 2 Level A)", f"{PDF1}+{PDF2}", "3 / 3", "STATED", "each module computes it independently; no shared reference level is imposed beyond this identical definition"),
    ("X-R02", "BOTH", "Which method has priority when both fire is not defined", f"{PDF1}+{PDF2}", "-", "SOURCE_SILENT", "earliest causally executable signal; same-instant tie -> METHOD_1 deterministic research policy (identical entry/stop/target, so P&L is unaffected)"),
]
