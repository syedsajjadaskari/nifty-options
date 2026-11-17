"""Phase 6.2: the combined five-strategy configurations (engine factories). The controller, exit policy, stops, targets, sizing and cutoff are the frozen ones (nothing is edited); only the ENGINE FACTORY is swapped at run time.

  A  Phase 3.6 frozen                                    (phase55 key 'A')
  B  Phase 5.3 author-corrected (legacy ORB)             (phase55 key 'B')
  C  IRF-V2 + ORB-V2 + PDR/PDS first-eligible + RF       NEW: 'phase62-irfv2-orbv2-combined'
  D1 IRF-V2 + frozen (legacy) ORB + PDR/PDS first-eligible + RF   diagnostic attribution (IRF effect)
  D2 frozen IRF + ORB-V2 + PDR/PDS first-eligible + RF            diagnostic attribution (ORB effect)
Configurations are never mixed; D is attribution only, never a selection device.
"""

from __future__ import annotations

import contextlib

from nifty_trading.research import phase3 as P
from nifty_trading.research import phase31 as P31
from nifty_trading.research import phase53 as F53
from nifty_trading.research import phase55 as X
from nifty_trading.strategies.irf import IRFStrategy
from nifty_trading.strategies.irf_phase53 import IRFPhase53Strategy
from nifty_trading.strategies.irf_v2 import IRFV2SupportBreakStrategy
from nifty_trading.strategies.orb import ORBStrategy
from nifty_trading.strategies.orb_v2_adapter import ORBV2Strategy

KEYS = ("A", "B", "C", "D1", "D2")
C_ID = "phase62-irfv2-orbv2-combined"
TITLES = {"A": "A - Phase 3.6 frozen", "B": "B - Phase 5.3 author-corrected (legacy ORB)", "C": "C - IRF V2 + ORB V2 + PDR/PDS (Phase 5.3 first-eligible) + RF",
          "D1": "D1 - IRF V2 + legacy ORB (attribution of the IRF change)", "D2": "D2 - frozen IRF + ORB V2 (attribution of the ORB change)"}


def engines_for(key: str, p, t, pdr_engine: str = "BODY_BASED_PHASE36", pdr_revision=None, orb_v2: ORBV2Strategy | None = None) -> list:
    if key in ("A", "B"):
        return X.engines_for(key, p, t, pdr_engine, pdr_revision)
    base = F53.make_engines53(F53.COMBINED_KEY, p, t, pdr_engine, pdr_revision)        # IRF phase53, ORB legacy, PDR/PDS first-eligible, RF (the same slots as configuration B)
    out = []
    for e in base:
        if key in ("C", "D1") and type(e) is IRFPhase53Strategy:
            e = IRFV2SupportBreakStrategy(proposals=p, trade=t)
        elif key == "D2" and type(e) is IRFPhase53Strategy:
            e = IRFStrategy(proposals=p, trade=t)                                       # the previous (frozen Phase 3.6) IRF
        elif key in ("C", "D2") and type(e) is ORBStrategy:
            assert orb_v2 is not None, "ORB V2 decisions are required for C and D2"
            e = orb_v2
        out.append(e)
    return out


@contextlib.contextmanager
def patched_engines(key: str, orb_v2: ORBV2Strategy | None = None):
    saved = (P31.make_engines, P.make_engines)

    def factory(p, t, pdr_engine="LEGACY", pdr_revision=None):
        return engines_for(key, p, t, pdr_engine, pdr_revision, orb_v2)
    P31.make_engines = factory
    try:
        yield
    finally:
        P31.make_engines, P.make_engines = saved


def run_timelines_cfg(key: str, sc, ctxs: dict, bars: dict, orb_v2: ORBV2Strategy | None = None):
    with patched_engines(key, orb_v2):
        return P31.run_timelines(sc, ctxs, bars)
