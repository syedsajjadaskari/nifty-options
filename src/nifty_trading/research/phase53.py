"""Phase 5.3: the owner-approved author corrections as separately selectable configurations (signal level; no controller, no fills, no P&L).

The frozen Phase 3.6 default (``phase3.combined_scenario("BODY_BASED_PHASE36")`` + ``phase3.make_engines``) and the Phase 5.2 configurations are never replaced. Keys:

  phase36-frozen                     the frozen reference (unchanged)
  phase52-approved                   Phase 5.2 approved set (identical signals; reference)
  phase53-irf-first-red-low          IRF Method 2A support = LOW of the first red candle (owner approved; red search after the extension)
  phase53-irf-ema28                  IRF minimum 28-point EMA(200) clearance of the signal candle's range (owner approved 28; measure PROVISIONAL_EMA_RANGE_DISTANCE), all IRF methods
  phase53-pdr-first-eligible         PDR earliest eligible confirmation (PROVISIONAL_PDR_MINIMAL_CONFIRMATION)
  phase53-pds-first-eligible         PDS earliest eligible confirmation (PROVISIONAL_PDS_MINIMAL_QUALITY)
  phase53-author-corrected           the four rules above together (ORB and RF frozen)
  phase53-var-irf-first-red-after-breakout   assumption variant: the first red candle is searched from the breakout candle
  phase53-var-irf-ema28-method2-only         scope variant: the EMA clearance applies to Methods 2A / 2B only
  phase53-var-irf-ema27                      comparison variant (the handwritten pages' 27)
  phase53-var-irf-ema28-close                comparison variant: |close - EMA| >= 28 instead of the range distance
  phase53-var-orb-colour             the Phase 5.1 ORB colour rule, opt-in and NOT part of the combined configuration
"""

from __future__ import annotations

from dataclasses import dataclass

from nifty_trading.research import phase3 as P
from nifty_trading.strategies.first_eligible_phase53 import (
    PDRFirstEligibleStrategy,
    PDSFirstEligibleStrategy,
)
from nifty_trading.strategies.irf import IRFStrategy
from nifty_trading.strategies.irf_phase53 import IRFPhase53Strategy
from nifty_trading.strategies.orb import ORBStrategy
from nifty_trading.strategies.orb_colour import ORBColourStrategy
from nifty_trading.strategies.pdr_body import PDRBodyStrategy
from nifty_trading.strategies.pds import PDSStrategy

FROZEN_KEY = "phase36-frozen"
COMBINED_KEY = "phase53-author-corrected"


@dataclass(frozen=True)
class Phase53Config:
    key: str
    title: str
    authority: str
    irf: tuple[tuple[str, object], ...] | None = None  # IRFPhase53Strategy keyword arguments (None = the frozen IRF engine)
    pdr_first: bool = False
    pds_first: bool = False
    orb_colour: bool = False
    note: str = ""


_FRL = (("support_ref", "FIRST_RED_LOW"),)
_E28 = (("ema_min_clearance", 28.0), ("ema_scope", "ALL_METHODS"), ("ema_measure", "RANGE"))

CONFIGS: dict[str, Phase53Config] = {c.key: c for c in (
    Phase53Config(FROZEN_KEY, "Frozen Phase 3.6 reference", "ACTIVE_REFERENCE", note="unchanged"),
    Phase53Config("phase52-approved", "Phase 5.2 approved set (reference; signals identical to the frozen set)", "USER_APPROVED_VERIFIED", note="PDS co-confirmed methods recorded (annotation only)"),
    Phase53Config("phase53-irf-first-red-low", "IRF Method 2A support = low of the first red candle", "OWNER_APPROVED_LEVEL; SCOPE_AND_SEARCH_START_PROVISIONAL", irf=_FRL,
                  note="Method 2A only; the first red candle is searched after the extension candle (provisional)"),
    Phase53Config("phase53-irf-ema28", "IRF minimum 28-point EMA(200) clearance (range distance)", "OWNER_APPROVED_28; MEASURE_PROVISIONAL_EMA_RANGE_DISTANCE", irf=_E28, note="inclusive 28; all IRF methods (provisional scope)"),
    Phase53Config("phase53-pdr-first-eligible", "PDR earliest eligible confirmation", "OWNER_APPROVED_INTENT; CONVENTION_PROVISIONAL", pdr_first=True,
                  note="green candle (guide s.4.3) or lower-price rejection, close strictly above the ceiling, after the retest candle"),
    Phase53Config("phase53-pds-first-eligible", "PDS earliest eligible confirmation", "OWNER_APPROVED_INTENT; CONVENTION_PROVISIONAL", pds_first=True,
                  note="structural dominance tests (an implicit threshold); weak first red candle still goes to Method 3 (source rule)"),
    Phase53Config(COMBINED_KEY, "Phase 5.3 author-corrected (IRF first-red-low + EMA 28, PDR/PDS first eligible)", "COMPOSITE: OWNER_APPROVED RULES WITH PROVISIONAL CONVENTIONS", irf=_FRL + _E28, pdr_first=True, pds_first=True,
                  note="ORB and RF frozen; the day's-low restriction is pending and NOT applied"),
    Phase53Config("phase53-var-irf-first-red-after-breakout", "Variant: first red candle searched after the breakout candle", "ASSUMPTION_VARIANT", irf=_FRL + (("red_search_start", "AFTER_BREAKOUT"),)),
    Phase53Config("phase53-var-irf-ema28-method2-only", "Variant: EMA clearance applies to Methods 2A / 2B only", "SCOPE_VARIANT", irf=(("ema_min_clearance", 28.0), ("ema_scope", "METHOD2_ONLY"), ("ema_measure", "RANGE"))),
    Phase53Config("phase53-var-irf-ema27", "Variant (comparison only): 27-point clearance", "DIAGNOSTIC_VARIANT", irf=(("ema_min_clearance", 27.0), ("ema_scope", "ALL_METHODS"), ("ema_measure", "RANGE"))),
    Phase53Config("phase53-var-irf-ema28-close", "Variant (comparison only): |close - EMA| >= 28", "DIAGNOSTIC_VARIANT", irf=(("ema_min_clearance", 28.0), ("ema_scope", "ALL_METHODS"), ("ema_measure", "CLOSE"))),
    Phase53Config("phase53-var-orb-colour", "Variant: ORB colour rule (Phase 5.1)", "CANDIDATE_NOT_APPROVED", orb_colour=True),
)}
COMPARISON_ORDER = list(CONFIGS)


def make_engines53(key: str, p, t, pdr_engine: str = "BODY_BASED_PHASE36", pdr_revision=None):
    """The five engines in their fixed order for a configuration: the frozen factory with only the slots a configuration changes replaced (RF is never replaced)."""
    cfg = CONFIGS[key]
    out = []
    for e in P.make_engines(p, t, pdr_engine, pdr_revision):
        if cfg.irf is not None and type(e) is IRFStrategy:
            e = IRFPhase53Strategy(proposals=p, trade=t, **dict(cfg.irf))
        elif cfg.pdr_first and type(e) is PDRBodyStrategy:
            e = PDRFirstEligibleStrategy(proposals=p, trade=t, revision=e.rev)
        elif cfg.pds_first and type(e) is PDSStrategy:
            e = PDSFirstEligibleStrategy(proposals=p, trade=t)
        elif cfg.orb_colour and type(e) is ORBStrategy:
            e = ORBColourStrategy(proposals=p, trade=t)
        out.append(e)
    if key == "phase52-approved":
        from nifty_trading.research.phase52 import make_engines52
        return make_engines52(key, p, t, pdr_engine, pdr_revision)
    return out


def signals_for(ctxs: dict, sc, key: str, collect_rejections: list | None = None) -> dict:
    """All signal records (every status) per session for configuration ``key``: {date: [SignalRecord]}. Signals only. EMA-rejected candidates are appended to ``collect_rejections`` when given."""
    engines = make_engines53(key, sc.proposals, sc.trade, sc.pdr_engine, sc.pdr_revision)
    res = {}
    for d in sorted(ctxs):
        res[d] = [r for e in engines for r in e.evaluate_session(ctxs[d])]
        for e in engines:
            if hasattr(e, "rejections") and e.rejections:
                if collect_rejections is not None:
                    collect_rejections.extend({"config": key, **x} for x in e.rejections)
                e.rejections.clear()
    return res
