"""Exit-rule specification (Phase 2: specified and unit-tested, NOT run as a performance backtest).

Source of the model: ``NIFTY_System_Trading_Strategy_Performance.docx`` (6 lots = 390 qty at 65/lot;
Leg 1 = 3 lots exits at Target 1 = 27 points; Leg 2 = 3 lots exits at Target 2; once Target 1 is
booked the stop on Leg 2 moves to the entry price). All P&L is in NIFTY spot-index POINTS (and
points x quantity): the index is not directly tradable, so every figure here is SYNTHETIC.

Values the documents leave open stay ``None`` and are listed in ``unresolved``; evaluation of a
policy with unresolved parameters returns ``NOT_EVALUABLE`` instead of guessing.

Intrabar order is unknowable from 1-minute OHLC. Every same-bar ambiguity is recorded and resolved
ADVERSELY (stop/breakeven before target; no favourable fills): that is a PROPOSED conservative
convention, not a source rule.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum

from nifty_trading.strategies.params import SOURCE
from nifty_trading.strategies.rules import implements


class TradeOutcome(str, Enum):
    TARGET = "Target"  # both legs booked (T1 then T2)
    BREAKEVEN = "BE"  # T1 booked, Leg 2 stopped at entry
    STOP_LOSS = "SL"  # both legs stopped, full quantity
    INCOMPLETE_EOD = "Incomplete"  # session ended with the position still open (no EOD rule in the source)
    NOT_EVALUABLE = "NotEvaluable"  # policy has unresolved parameters


class EodPolicy(str, Enum):
    LEAVE_OPEN = "LEAVE_OPEN"  # default: the report defines no end-of-day outcome
    EXIT_AT_LAST_CLOSE = "EXIT_AT_LAST_CLOSE"  # research option: flatten at the last bar's close


class StopRule(str, Enum):
    FIXED = "FIXED"  # ORB: 30
    OPPOSITE_CANDLE_35_40 = "OPPOSITE_CANDLE_35_40"  # IRF, PDS
    UNRESOLVED = "UNRESOLVED"  # PDR (35/40 'depending on the situation'), RF (35-40 'logical')


@dataclass(frozen=True)
class ExitPolicyConfig:
    total_lots: int = SOURCE.lots_total
    lot_size: int = SOURCE.lot_size
    leg1_lots: int = 3
    leg2_lots: int = 3
    t1_points: float = SOURCE.t1_points
    t2_points: float | None = None
    stop_points: float | None = None
    breakeven_after_t1: bool = True
    eod_policy: EodPolicy = EodPolicy.LEAVE_OPEN
    t2_note: str = ""
    unresolved: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.leg1_lots + self.leg2_lots != self.total_lots:
            raise ValueError("leg lots must sum to total lots")
        if self.t2_points is not None and self.t2_points <= self.t1_points:
            raise ValueError("Target 2 must be beyond Target 1")
        if not self.breakeven_after_t1:
            raise ValueError("breakeven_after_t1=False is not specified by any source document and is not implemented")

    @property
    def total_qty(self) -> int:
        return self.total_lots * self.lot_size

    @property
    def leg1_qty(self) -> int:
        return self.leg1_lots * self.lot_size

    @property
    def leg2_qty(self) -> int:
        return self.leg2_lots * self.lot_size

    @property
    def missing(self) -> tuple[str, ...]:
        m = list(self.unresolved)
        if self.t2_points is None and "t2_points" not in m:
            m.append("t2_points")
        if self.stop_points is None and "stop_points" not in m:
            m.append("stop_points")
        return tuple(m)


@implements("IRF-SL-001", "PDS-SL-001")
def select_stop_distance(entry: float, reference_price: float | None, inclusive_35: bool = True) -> float | None:
    """35 or 40 by the distance between entry and the most recent opposite candle's reference price.

    PROPOSED measurement: |reference - entry| <= 35 -> 35 else 40 (IRF p.14 card; p.10 'within 35').
    The absolute value is itself an interpretation: a green candle on the profit side of the entry (below a short
    entry) counts by its distance too. The source does not say; see ambiguous_rules.md AMB-IRF-12.
    Returns None when no reference exists (unresolved, never guessed).
    """
    if reference_price is None or math.isnan(reference_price):
        return None
    d = abs(reference_price - entry)
    small = d <= 35.0 if inclusive_35 else d < 35.0
    return 35.0 if small else 40.0


@implements("IRF-TGT-001", "ORB-GLOBAL-003", "PDR-008", "PDS-TGT-001", "PDR-009", "RF-009", "RF-011", "EXE-T2-001")
def policy_for(strategy: str, reference_price: float | None = None, entry: float | None = None,
               inclusive_35: bool = True) -> ExitPolicyConfig:
    """Exit policy per strategy exactly as far as the documents determine it. Anything else is flagged."""
    s = strategy.upper()
    if s == "ORB":
        return ExitPolicyConfig(t2_points=SOURCE.orb_target_points, stop_points=SOURCE.orb_stop_points,
                                t2_note="ORB p.1: target 60")
    if s == "IRF":
        stop = select_stop_distance(entry, reference_price, inclusive_35) if entry is not None else None
        return ExitPolicyConfig(t2_points=SOURCE.irf_target_points, stop_points=stop,
                                unresolved=() if stop is not None else ("stop_points(IRF-SL-001 needs the green-candle reference)",),
                                t2_note="IRF p.2: target 60 for all methods")
    if s == "PDS":
        stop = select_stop_distance(entry, reference_price, inclusive_35) if entry is not None else None
        return ExitPolicyConfig(t2_points=SOURCE.pds_target_points, stop_points=stop,
                                unresolved=("t2_points: PDS guide says 70, report records 60 or 70 (CONFLICT)",)
                                + (() if stop is not None else ("stop_points(PDS-SL-001 needs the green-candle reference)",)),
                                t2_note="PDS p.1: target 70 (report arithmetic shows 60 on 2 of 3 PDS winners)")
    if s == "PDR":
        return ExitPolicyConfig(t2_points=SOURCE.pdr_target_points, stop_points=None,
                                unresolved=("t2_points: PDR guide says 70, report records 60 or 70 (CONFLICT)",
                                            "stop_points: 35 vs 40 'depending on the situation' has no selection rule (PDR-009)"),
                                t2_note="PDR p.1: target 70 (report arithmetic shows 60 on 1 of 6 PDR winners)")
    if s == "RF":
        return ExitPolicyConfig(t2_points=None, stop_points=None,
                                unresolved=("t2_points: RF_TARGET_STATUS=UNRESOLVED (RF p.8 'OPEN')",
                                            "stop_points: 35-40 'logical for the setup' has no selection rule (RF-009)"),
                                t2_note="RF p.8: target OPEN")
    raise ValueError(f"unknown strategy {strategy!r}")


@dataclass(frozen=True)
class Bar:
    """One 1-minute OHLC bar (label = bar start)."""
    ts: object
    o: float
    h: float
    l: float
    c: float


@dataclass
class ExitResult:
    outcome: TradeOutcome
    direction: str
    entry: float
    stop_level: float | None
    t1_level: float
    t2_level: float | None
    leg1_exit: float | None
    leg2_exit: float | None
    leg1_ts: object | None
    leg2_ts: object | None
    pnl_points_weighted: float  # per full position, weighted by leg quantity / total
    pnl_rupees: float  # SYNTHETIC: points x quantity, before costs
    ambiguities: list[str]
    unresolved: tuple[str, ...]
    events: list[str]


@implements("EXE-T1-001", "EXE-POS-001")
def levels(direction: str, entry: float, cfg: ExitPolicyConfig) -> dict[str, float | None]:
    sgn = 1.0 if direction == "LONG" else -1.0
    return {
        "t1": entry + sgn * cfg.t1_points,
        "t2": None if cfg.t2_points is None else entry + sgn * cfg.t2_points,
        "stop": None if cfg.stop_points is None else entry - sgn * cfg.stop_points,
    }


@implements("EXE-BE-001", "EXE-OUT-001", "EXE-PNL-001", "EXE-MISSING-001", "IRF-SL-002")
def evaluate_exit(direction: str, entry: float, bars: Sequence[Bar], cfg: ExitPolicyConfig) -> ExitResult:
    """Walk 1-minute bars (the first bar is the one that STARTS at the signal candle's close) and resolve exits.

    Conventions (PROPOSED_CONSERVATIVE, see module docstring):
      * stop and breakeven are checked before targets inside one bar when both are touched;
      * a stop OR breakeven stop gapped through fills at the worse of (level, bar open); a target fills at its level, never better;
      * Target 1 then Target 2 inside one bar is allowed (a continuous path must cross T1 first), unless the same
        bar also touches the breakeven stop, which is resolved adversely (Leg 2 exits at entry).
    """
    if direction not in ("LONG", "SHORT"):
        raise ValueError(direction)
    lv = levels(direction, entry, cfg)
    long = direction == "LONG"
    if cfg.missing:
        return ExitResult(TradeOutcome.NOT_EVALUABLE, direction, entry, lv["stop"], lv["t1"], lv["t2"], None, None, None, None,
                          0.0, 0.0, [], cfg.missing, [])
    t1, t2, sl = lv["t1"], lv["t2"], lv["stop"]
    amb: list[str] = []
    ev: list[str] = []
    q1, q2, qt = cfg.leg1_qty, cfg.leg2_qty, cfg.total_qty

    def hit_high(b: Bar, lvl: float) -> bool:  # price reached lvl in the profitable direction
        return b.h >= lvl if long else b.l <= lvl

    def hit_adverse(b: Bar, lvl: float) -> bool:  # price reached lvl in the losing direction
        return b.l <= lvl if long else b.h >= lvl

    def stop_fill(b: Bar, lvl: float) -> float:
        return min(lvl, b.o) if long else max(lvl, b.o)

    def pts(exit_px: float) -> float:
        return (exit_px - entry) if long else (entry - exit_px)

    t1_done = False
    leg1_px = leg1_ts = None
    for b in bars:
        if not t1_done:
            stop_hit = hit_adverse(b, sl)
            t1_hit = hit_high(b, t1)
            if stop_hit and t1_hit:
                amb.append(f"{b.ts}: stop {sl} and Target 1 {t1} both touched in one 1-minute bar; resolved as STOP (adverse)")
            if stop_hit:
                px = stop_fill(b, sl)
                ev.append(f"{b.ts}: stop-loss, both legs out at {px}")
                p = pts(px)
                return ExitResult(TradeOutcome.STOP_LOSS, direction, entry, sl, t1, t2, px, px, b.ts, b.ts, p, p * qt, amb, (), ev)
            if not t1_hit:
                continue
            t1_done, leg1_px, leg1_ts = True, t1, b.ts
            ev.append(f"{b.ts}: Target 1 {t1} booked on Leg 1 ({q1} qty); Leg 2 stop -> entry {entry}")
            # same bar: does it also touch the breakeven stop (order unknown)?
            if cfg.breakeven_after_t1 and hit_adverse(b, entry):
                amb.append(f"{b.ts}: Target 1 and breakeven stop {entry} both touched in one bar; resolved as BREAKEVEN (adverse)")
                return _be(direction, entry, sl, t1, t2, leg1_px, leg1_ts, b, cfg, amb, ev, qt, q1, q2, stop_fill(b, entry))
            if hit_high(b, t2):
                ev.append(f"{b.ts}: Target 2 {t2} booked on Leg 2 ({q2} qty)")
                return _tgt(direction, entry, sl, t1, t2, leg1_px, leg1_ts, b, cfg, amb, ev, qt, q1, q2)
            continue
        # ---- Leg 2 only; stop is the entry price (breakeven) or the original stop if breakeven is disabled
        stop2 = entry  # EXE-BE-001: after Target 1 the Leg 2 stop is the entry price
        be_hit = hit_adverse(b, stop2)
        t2_hit = hit_high(b, t2)
        if be_hit and t2_hit:
            amb.append(f"{b.ts}: Leg 2 stop {stop2} and Target 2 {t2} both touched in one bar; resolved as STOP (adverse)")
        if be_hit:
            return _be(direction, entry, sl, t1, t2, leg1_px, leg1_ts, b, cfg, amb, ev, qt, q1, q2, stop_fill(b, stop2))
        if t2_hit:
            ev.append(f"{b.ts}: Target 2 {t2} booked on Leg 2 ({q2} qty)")
            return _tgt(direction, entry, sl, t1, t2, leg1_px, leg1_ts, b, cfg, amb, ev, qt, q1, q2)

    # ---- bars exhausted with the position still open: the source defines no end-of-day rule
    last = bars[-1] if bars else None
    if cfg.eod_policy is EodPolicy.EXIT_AT_LAST_CLOSE and last is not None:
        px = last.c
        if t1_done:
            p_w = (pts(leg1_px) * q1 + pts(px) * q2)
            ev.append(f"{last.ts}: research EOD flatten of Leg 2 at {px}")
            return ExitResult(TradeOutcome.INCOMPLETE_EOD, direction, entry, sl, t1, t2, leg1_px, px, leg1_ts, last.ts, p_w / qt, p_w, amb,
                              ("eod_policy: EXIT_AT_LAST_CLOSE is a research option, not a source rule",), ev)
        p_w = pts(px) * qt
        ev.append(f"{last.ts}: research EOD flatten of the full position at {px}")
        return ExitResult(TradeOutcome.INCOMPLETE_EOD, direction, entry, sl, t1, t2, px, px, last.ts, last.ts, p_w / qt, p_w, amb,
                          ("eod_policy: EXIT_AT_LAST_CLOSE is a research option, not a source rule",), ev)
    realised = pts(leg1_px) * q1 if t1_done else 0.0
    return ExitResult(TradeOutcome.INCOMPLETE_EOD, direction, entry, sl, t1, t2, leg1_px, None, leg1_ts, None, realised / qt, realised, amb,
                      ("end-of-day exit rule absent from the source documents",), ev)


def _be(direction, entry, sl, t1, t2, leg1_px, leg1_ts, b, cfg, amb, ev, qt, q1, q2, px):
    """Leg 2 stopped at the breakeven level; ``px`` is the fill (worse of level and bar open: no favourable fill)."""
    long = direction == "LONG"
    ev.append(f"{b.ts}: breakeven stop, Leg 2 ({q2} qty) out at {px}")
    leg1 = (leg1_px - entry) if long else (entry - leg1_px)
    leg2 = (px - entry) if long else (entry - px)
    total = leg1 * q1 + leg2 * q2
    return ExitResult(TradeOutcome.BREAKEVEN, direction, entry, sl, t1, t2, leg1_px, px, leg1_ts, b.ts, total / qt, total, amb, (), ev)


def _tgt(direction, entry, sl, t1, t2, leg1_px, leg1_ts, b, cfg, amb, ev, qt, q1, q2):
    long = direction == "LONG"
    leg1 = (leg1_px - entry) if long else (entry - leg1_px)
    leg2 = (t2 - entry) if long else (entry - t2)
    total = leg1 * q1 + leg2 * q2
    return ExitResult(TradeOutcome.TARGET, direction, entry, sl, t1, t2, leg1_px, t2, leg1_ts, b.ts, total / qt, total, amb, (), ev)
