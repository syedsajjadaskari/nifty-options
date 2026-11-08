"""Phase 5.4: ORB-only, separately selectable VARIANTS for the signal-only audit of the ORB source rules (NO controller, NO fills, NO P&L).

Every variant is DISABLED BY DEFAULT: the frozen Phase 3.6 default, the Phase 5.2 and the Phase 5.3 configurations never use one. A variant replaces ONLY the ORB engine (IRF, PDR, PDS and RF are not touched) and changes ONE
unresolved construction or threshold family so that its historical signal impact can be measured. None of them is source-defined or approved; ``authority`` says what is known.

  orb-frozen                         the frozen ORB engine (reference)
  orb-var-inner-highest-fractal      Method 2 inner level = the highest (long) / lowest (short) inner swing of the previous session
  orb-var-inner-nearest-from-open    Method 2 inner level = the first inner swing the price must cross from the opening price
  orb-var-inner-highest-broken       Method 2 inner level = the most distant inner swing the first candle broke and closed beyond
  orb-var-trendline-any-pair         Method 2 trendline through ANY two of the last three fractal lows (highs)
  orb-var-trendline-none             DIAGNOSTIC: the unresolved Method 2 trendline condition is not applied
  orb-var-strength-strict / -loose   strong-candle profile STRICT / LOOSE (numeric approximation of 'strong'; the rulebook gives no numbers)
  orb-var-trend-structure            trend = previous close on the trend side of its EMA AND two higher swing highs and lows (owner variant B)
  orb-var-trend-ema-basic            trend = the first candle's close against the EMA(200) at 09:20 ('price above the 200 EMA', the rulebook's literal basic confirmation; DIAGNOSTIC: the frozen design uses
                                     previous-session information so that the opening gap cannot establish the trend)
  orb-var-gap-candle-crossing        Gap / 200 DMA setup: the first CANDLE (not only the open) may cross the average (the p.8 / p.9 schematics and the p.12 real chart draw it so)
  orb-var-colour                     the Phase 5.1 colour rule (long needs a green first candle, short a red one)
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from nifty_trading.strategies.orb import ORBStrategy
from nifty_trading.strategies.orb_candidates import ORBCandidateStrategy
from nifty_trading.strategies.orb_colour import ORBColourStrategy

FROZEN_KEY = "orb-frozen"


@dataclass(frozen=True)
class OrbVariant:
    key: str
    title: str
    authority: str
    inner_level_def: str = "LATEST_FRACTAL_K2"
    trendline_def: str = "LAST_TWO_FRACTALS_K2"
    gap_crossing_def: str = "OPEN_BEYOND_AVERAGE"
    strong_candle: str | None = None
    trend_mode: str | None = None
    colour: bool = False
    note: str = ""


VARIANTS: dict[str, OrbVariant] = {v.key: v for v in (
    OrbVariant(FROZEN_KEY, "Frozen ORB engine", "ACTIVE_REFERENCE"),
    OrbVariant("orb-var-inner-highest-fractal", "Method 2 inner level = highest inner swing", "RESEARCH_PROPOSAL_NOT_APPROVED", inner_level_def="HIGHEST_FRACTAL_K2"),
    OrbVariant("orb-var-inner-nearest-from-open", "Method 2 inner level = first inner swing from the open", "RESEARCH_PROPOSAL_NOT_APPROVED", inner_level_def="NEAREST_FRACTAL_FROM_OPEN_K2"),
    OrbVariant("orb-var-inner-highest-broken", "Method 2 inner level = most distant inner swing broken (chosen after seeing the 09:20 close: non-discriminating)", "DIAGNOSTIC_ONLY", inner_level_def="HIGHEST_BROKEN_FRACTAL_K2"),
    OrbVariant("orb-var-trendline-any-pair", "Method 2 trendline = any two of the last three fractals", "RESEARCH_PROPOSAL_NOT_APPROVED", trendline_def="ANY_RISING_PAIR_OF_LAST_THREE_K2"),
    OrbVariant("orb-var-trendline-none", "Method 2 without the trendline condition (diagnostic)", "DIAGNOSTIC_ONLY", trendline_def="NONE"),
    OrbVariant("orb-var-strength-strict", "Strong-candle profile STRICT", "DIAGNOSTIC_ONLY", strong_candle="STRICT"),
    OrbVariant("orb-var-strength-loose", "Strong-candle profile LOOSE", "RESEARCH_PROPOSAL_NOT_APPROVED", strong_candle="LOOSE"),
    OrbVariant("orb-var-trend-structure", "Trend = EMA side + two higher swing highs and lows (owner variant B)", "OWNER_VARIANT_NOT_ACTIVE", trend_mode="STRUCTURE_EMA_SWING2"),
    OrbVariant("orb-var-trend-ema-basic", "Trend = first-candle close against EMA(200) (literal basic confirmation)", "DIAGNOSTIC_ONLY", trend_mode="EMA5M_BASIC"),
    OrbVariant("orb-var-gap-candle-crossing", "Gap / 200 DMA: the candle (not only the open) may cross the average", "RESEARCH_PROPOSAL_NOT_APPROVED", gap_crossing_def="CANDLE_CROSSES_AVERAGE"),
    OrbVariant("orb-var-colour", "ORB colour rule (Phase 5.1)", "CANDIDATE_NOT_APPROVED", colour=True),
)}


def make_orb_engine(key: str, p, t):
    """The ORB engine of a variant. The frozen key returns the frozen ``ORBStrategy``; only the listed construction / profile differs otherwise."""
    v = VARIANTS[key]
    pv = p
    if v.strong_candle is not None:
        pv = replace(pv, strong_candle=v.strong_candle)
    if v.trend_mode is not None:
        pv = replace(pv, trend_mode=v.trend_mode)
    if key == FROZEN_KEY:
        return ORBStrategy(proposals=pv, trade=t)
    if v.colour:
        return ORBColourStrategy(proposals=pv, trade=t)
    return ORBCandidateStrategy(proposals=pv, trade=t, inner_level_def=v.inner_level_def, trendline_def=v.trendline_def, gap_crossing_def=v.gap_crossing_def)


def orb_signals_for(ctxs: dict, sc, key: str) -> dict:
    """All ORB signal records (every status) per session for variant ``key``: {date: [SignalRecord]}. Signals only."""
    eng = make_orb_engine(key, sc.proposals, sc.trade)
    return {d: eng.evaluate_session(ctxs[d]) for d in sorted(ctxs)}
