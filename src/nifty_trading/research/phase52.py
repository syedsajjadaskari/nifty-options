"""Phase 5.2: separately selectable strategy configurations for the author's latest clarifications.

The frozen Phase 3.6 default (``phase3.combined_scenario("BODY_BASED_PHASE36")`` + ``phase3.make_engines``) is never replaced. A Phase 5.2 configuration is chosen by key:

  phase36-frozen                       the frozen reference (nothing changes)
  phase52-approved                     what is USER_APPROVED or explicit: the first-eligible-confirmation-candle principle for PDR and PDS. The audit found the frozen PDR and PDS engines ALREADY activate on the first
                                       eligible candle, so the approved set leaves every signal as it is, records co-confirmed PDS methods and adds the required diagnostics; the equality with the frozen engines is asserted by a regression test
  phase52-cand-orb-colour              opt-in candidate (Phase 5.1): ORB long needs a green first candle, short a red one
  phase52-cand-irf-first-red-low       opt-in candidate: IRF Method 2A support = LOW of the first red candle
  phase52-cand-irf-first-red-body-low  opt-in candidate: IRF Method 2A support = BODY LOW of the first red candle

Candidates are labelled NOT_APPROVED: the author's wording leaves the level definition (and the ORB short mirror) open. They exist only for the signal-only comparison.
"""

from __future__ import annotations

from dataclasses import dataclass

from nifty_trading.research import phase3 as P
from nifty_trading.strategies.irf import IRFStrategy
from nifty_trading.strategies.irf_candidates import IRFFirstRedStrategy
from nifty_trading.strategies.orb import ORBStrategy
from nifty_trading.strategies.orb_colour import ORBColourStrategy
from nifty_trading.strategies.pds import PDSStrategy
from nifty_trading.strategies.pds_first_eligible import PDSCoConfirmStrategy

FROZEN_KEY = "phase36-frozen"


@dataclass(frozen=True)
class Phase52Config:
    key: str
    title: str
    authority: str  # ACTIVE_REFERENCE | USER_APPROVED_VERIFIED | CANDIDATE_NOT_APPROVED
    orb_colour: bool = False
    irf_support_ref: str | None = None
    pds_co_confirm: bool = False
    note: str = ""


CONFIGS: dict[str, Phase52Config] = {c.key: c for c in (
    Phase52Config(FROZEN_KEY, "Frozen Phase 3.6 reference", "ACTIVE_REFERENCE", note="unchanged; the default of every earlier phase"),
    Phase52Config("phase52-approved", "Phase 5.2 approved set (first eligible confirmation candle for PDR and PDS)", "USER_APPROVED_VERIFIED", pds_co_confirm=True,
                  note="PDR / PDS engines already act on the first eligible candle (verified by audit); engines act as before; PDS additionally records co-confirmed methods; diagnostics added"),
    Phase52Config("phase52-cand-orb-colour", "Candidate: ORB colour filter", "CANDIDATE_NOT_APPROVED", orb_colour=True,
                  note="author wrote 'for long' only; the short mirror is a source interpretation (ORB-GLOBAL-002)"),
    Phase52Config("phase52-cand-irf-first-red-low", "Candidate: IRF 2A support = low of the first red candle", "CANDIDATE_NOT_APPROVED", irf_support_ref="FIRST_RED_LOW",
                  note="level definition not established by the author or the guide"),
    Phase52Config("phase52-cand-irf-first-red-body-low", "Candidate: IRF 2A support = body low of the first red candle", "CANDIDATE_NOT_APPROVED", irf_support_ref="FIRST_RED_BODY_LOW",
                  note="level definition not established by the author or the guide"),
)}


def make_engines52(key: str, p, t, pdr_engine: str = "BODY_BASED_PHASE36", pdr_revision=None):
    """The five engines in their fixed order for a configuration. Starts from the frozen factory (``phase3.make_engines``) and replaces only the slot a candidate changes."""
    cfg = CONFIGS[key]
    engines = P.make_engines(p, t, pdr_engine, pdr_revision)
    out = []
    for e in engines:
        if cfg.orb_colour and type(e) is ORBStrategy:
            e = ORBColourStrategy(proposals=p, trade=t)
        elif cfg.pds_co_confirm and type(e) is PDSStrategy:
            e = PDSCoConfirmStrategy(proposals=p, trade=t)
        elif cfg.irf_support_ref and type(e) is IRFStrategy:
            e = IRFFirstRedStrategy(proposals=p, trade=t, support_ref=cfg.irf_support_ref)
        out.append(e)
    return out


def signals_for(ctxs: dict, sc, key: str) -> dict:
    """All signal records (every status) per session for configuration ``key``: {date: [SignalRecord]}. Signals only: no controller, no fills, no P&L."""
    engines = make_engines52(key, sc.proposals, sc.trade, sc.pdr_engine, sc.pdr_revision)
    return {d: [r for e in engines for r in e.evaluate_session(ctxs[d])] for d in sorted(ctxs)}
