"""Exit-rule specification (Phase 2: specified and unit-tested, NOT run as a performance backtest).

Source of the model: ``NIFTY_System_Trading_Strategy_Performance.docx`` (6 lots = 390 qty at 65/lot;
Leg 1 = 3 lots exits at Target 1 = 27 points; Leg 2 = 3 lots exits at Target 2; once Target 1 is
booked the stop on Leg 2 moves to the entry price). All P&L is in NIFTY spot-index POINTS (and
points x quantity): the index is not directly tradable, so every figure here is SYNTHETIC.

Stops come from ``params.TradeConfig`` (single place): the user-approved research baseline is 35 points (ORB keeps its
documented 30) and 40 is a sensitivity variant. A value the documents leave open and nobody supplied stays ``None`` and is
listed in ``unresolved``: evaluation then returns ``NOT_EVALUABLE`` instead of guessing. Source CONFLICTS (PDR/PDS target 70 vs
report winners at 60) do not block evaluation but are carried in ``conflicts``.

Execution eligibility: a ``Bar`` with ``executable=False`` (closing-auction reference bars, post-close rows) can never fill a
stop or target. A position still open when such a bar is reached is reported ``INCOMPLETE_EOD`` with an explicit
``UNRESOLVED_AT_CLOSING_AUCTION`` flag instead of inventing an exit price.

Intrabar order is unknowable from 1-minute OHLC. Every same-bar ambiguity is recorded and resolved
ADVERSELY (stop/breakeven before target; no favourable fills): that is a PROPOSED conservative
convention, not a source rule.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import time
from enum import Enum
from zoneinfo import ZoneInfo

from nifty_trading.strategies.params import DEFAULT_TRADE, SOURCE, T2_CONFLICTS, TradeConfig
from nifty_trading.strategies.rules import implements

IST = ZoneInfo("Asia/Kolkata")
FORCED_EXIT_LIMIT = time(15, 15)  # FORCED-EXIT-001: the forced exit must fill strictly before this clock time


class TradeOutcome(str, Enum):
    TARGET = "Target"  # both legs booked (T1 then T2)
    BREAKEVEN = "BE"  # SUPERSEDED legacy mode only (post_t1_stop_mode="ENTRY_BREAKEVEN"): T1 booked, Leg 2 stopped at exactly the entry
    T1_THEN_BUFFER_STOP = "T1_BUFFER"  # Phase 2.3 (USER_APPROVED): T1 booked, Leg 2 stopped at the entry -/+ 6 points
    STOP_LOSS = "SL"  # both legs stopped, full quantity before Target 1
    INITIAL_FULL_STOP = "SL"  # alias: the Phase 2.3 name for STOP_LOSS (the only outcome that permits a second PDR/PDS trade)
    FORCED_EXIT = "ForcedExit"  # Phase 3: still open at the forced-exit time, closed at the open of that minute (FORCED-EXIT-001/002)
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
    breakeven_after_t1: bool = True  # kept for compatibility: "a protective stop exists on Leg 2 after Target 1" (must stay True)
    post_t1_stop_mode: str = "BUFFER"  # "BUFFER": Leg 2 stop = entry -/+ post_t1_buffer_points (USER_APPROVED, Phase 2.3) | "ENTRY_BREAKEVEN": superseded report rule
    post_t1_buffer_points: float = 6.0  # LONG: entry - 6; SHORT: entry + 6. No trailing and no further adjustment.
    eod_policy: EodPolicy = EodPolicy.LEAVE_OPEN
    forced_exit_time: time | None = None  # Phase 3: a position still open at this clock time (IST) is closed at the OPEN of that minute's bar
    t2_note: str = ""
    unresolved: tuple[str, ...] = field(default_factory=tuple)
    conflicts: tuple[str, ...] = field(default_factory=tuple)  # recorded source conflicts; they do NOT block evaluation
    stop_status: str = "UNRESOLVED"  # VERIFIED_EXPLICIT | USER_APPROVED | PROPOSED_FOR_REVIEW | UNRESOLVED
    t2_status: str = "UNRESOLVED"
    stop_variant: str = "BASELINE"
    execution_status: str = "RESEARCH_ONLY"  # nothing is approved for live or verified execution

    def __post_init__(self) -> None:
        if self.leg1_lots + self.leg2_lots != self.total_lots:
            raise ValueError("leg lots must sum to total lots")
        if self.leg1_lots != self.leg2_lots:
            raise ValueError("the position is split into two EQUAL legs (owner decision SIZE-LOT-001)")
        if self.t2_points is not None and self.t2_points <= self.t1_points:
            raise ValueError("Target 2 must be beyond Target 1")
        if not self.breakeven_after_t1:
            raise ValueError("breakeven_after_t1=False is not specified by any source document and is not implemented")
        if self.post_t1_stop_mode not in ("BUFFER", "ENTRY_BREAKEVEN"):
            raise ValueError(f"post_t1_stop_mode={self.post_t1_stop_mode!r}")
        if self.post_t1_buffer_points < 0:
            raise ValueError("post_t1_buffer_points must be >= 0")
        if self.stop_points is not None and self.post_t1_buffer_points > self.stop_points:
            raise ValueError("the post-T1 stop may never be wider than the initial stop (no widening)")

    def post_t1_stop(self, direction: str, entry: float) -> float:
        """Leg-2 stop once Target 1 is booked: entry - 6 (LONG) / entry + 6 (SHORT); the superseded mode returns the entry itself."""
        buf = self.post_t1_buffer_points if self.post_t1_stop_mode == "BUFFER" else 0.0
        return entry - buf if direction == "LONG" else entry + buf

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
    lo, hi = SOURCE.pdr_pds_stop_choices
    small = d <= lo if inclusive_35 else d < lo
    return lo if small else hi


@implements("IRF-TGT-001", "ORB-GLOBAL-003", "PDR-008", "PDS-TGT-001", "PDR-009", "RF-009", "RF-011", "EXE-T2-001", "EXE-STOP-001", "SIZE-LOT-001")
def policy_for(strategy: str, reference_price: float | None = None, entry: float | None = None,
               inclusive_35: bool = True, trade: TradeConfig = DEFAULT_TRADE) -> ExitPolicyConfig:
    """Exit policy per strategy: stops/targets from ``trade`` (one place), statuses attached, conflicts recorded.

    ``reference_price``/``entry``/``inclusive_35`` are used only by the research variant
    ``stop_variant='SOURCE_35_40_BY_DISTANCE'`` (35 or 40 by the distance to the most recent opposite candle).
    """
    s = strategy.upper()
    if s not in ("ORB", "IRF", "PDR", "PDS", "RF"):
        raise ValueError(f"unknown strategy {strategy!r}")
    stop = trade.stop_points(s)
    unresolved: list[str] = []
    if stop is None:  # SOURCE_35_40_BY_DISTANCE: needs the per-trade measurement
        if entry is not None:
            stop = select_stop_distance(entry, reference_price, inclusive_35)
        if stop is None:
            unresolved.append(f"stop_points({s}: 35/40 by distance needs the opposite-candle reference)")
    t2 = trade.t2_points(s)
    if t2 is None:
        unresolved.append("t2_points: RF_TARGET_STATUS=UNRESOLVED (RF p.8 'OPEN') and no research value configured")
    notes = {"ORB": "ORB p.1: target 60", "IRF": "IRF p.2: target 60 for all methods",
             "PDR": "PDR p.1: target 70", "PDS": "PDS p.1: target 70",
             "RF": "RF p.8: target OPEN; the configured value is a PROPOSED research value, not a source rule"}
    return ExitPolicyConfig(total_lots=trade.total_lots, lot_size=trade.lot_size, leg1_lots=trade.leg1_lots,
                            leg2_lots=trade.total_lots - trade.leg1_lots, post_t1_stop_mode=trade.post_t1_stop_mode,
                            post_t1_buffer_points=trade.post_t1_buffer_points, forced_exit_time=trade.forced_exit_time,
                            t1_points=trade.t1_points, t2_points=t2, stop_points=stop, unresolved=tuple(unresolved),
                            conflicts=(T2_CONFLICTS[s],) if s in T2_CONFLICTS else (), t2_note=notes[s],
                            stop_status=trade.stop_status(s) if stop is not None else "UNRESOLVED",
                            t2_status=trade.t2_status(s), stop_variant=trade.stop_variant)


@dataclass(frozen=True)
class Bar:
    """One 1-minute OHLC bar (label = bar start)."""
    ts: object
    o: float
    h: float
    l: float
    c: float
    executable: bool = True  # False: closing-auction reference / post-close / non-trading bar - may never fill an order
    ineligible: str = "CLOSING_AUCTION_REFERENCE"  # why it is not fillable (a BarEligibility value); only read when executable is False


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
    non_executable_bars_skipped: int = 0
    unresolved_at_closing_auction: bool = False  # True: position still open when the first CLOSING-AUCTION reference bar was reached
    closing_auction_truncated: bool = False  # True: closing-auction bars were skipped (also set when a research EOD flatten replaced the exit)
    post_t1_stop_level: float | None = None  # the Leg-2 stop that applied after Target 1 (None until T1 booked)
    adverse_slippage_points: float = 0.0  # fill worse than the stop level (gap through the stop); 0 when filled at the level
    forced_exit_reference_close: float | None = None  # sensitivity only: the close of the forced-exit minute (NOT used for the fill)


@implements("EXE-T1-001", "EXE-POS-001")
def levels(direction: str, entry: float, cfg: ExitPolicyConfig) -> dict[str, float | None]:
    sgn = 1.0 if direction == "LONG" else -1.0
    return {
        "t1": entry + sgn * cfg.t1_points,
        "t2": None if cfg.t2_points is None else entry + sgn * cfg.t2_points,
        "stop": None if cfg.stop_points is None else entry - sgn * cfg.stop_points,
        "post_t1_stop": cfg.post_t1_stop(direction, entry),
    }


@implements("POST-T1-STOP-006", "FORCED-EXIT-001", "FORCED-EXIT-002", "EXE-OUT-001", "EXE-PNL-001", "EXE-MISSING-001", "IRF-SL-002")
def evaluate_exit(direction: str, entry: float, bars: Sequence[Bar], cfg: ExitPolicyConfig, entry_at_first_bar_open: bool = False) -> ExitResult:
    """Walk 1-minute bars (the first bar is the one that STARTS at the signal candle's close) and resolve exits.

    Conventions (PROPOSED_CONSERVATIVE, see module docstring):
      * stops are checked before targets inside one bar when both are touched;
      * a stop gapped through fills at the worse of (level, bar open) and the adverse slippage is recorded; a target fills at its level;
      * Phase 2.3 (USER_APPROVED): after Target 1 the Leg-2 stop is entry - 6 (LONG) / entry + 6 (SHORT), fixed: no trailing, no further move;
        the superseded report rule (stop exactly at the entry) is only available as ``post_t1_stop_mode="ENTRY_BREAKEVEN"``;
      * Target 1 then Target 2 inside one bar is allowed (a continuous path must cross T1 first), unless the same
        bar also touches the post-T1 stop, which is resolved adversely (Leg 2 stops out; outcome T1_THEN_BUFFER_STOP);
      * ``entry_at_first_bar_open=True`` (the causal fill of ``selection.simulate_exit``): the entry IS the first bar's open, so in the
        superseded exact-entry mode that bar cannot "touch" the entry merely by opening there (strictly beyond is required).
    """
    if direction not in ("LONG", "SHORT"):
        raise ValueError(direction)
    lv = levels(direction, entry, cfg)
    long = direction == "LONG"
    if cfg.missing:
        return ExitResult(TradeOutcome.NOT_EVALUABLE, direction, entry, lv["stop"], lv["t1"], lv["t2"], None, None, None, None,
                          0.0, 0.0, [], cfg.missing, [])
    t1, t2, sl, stop2 = lv["t1"], lv["t2"], lv["stop"], lv["post_t1_stop"]
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
    skipped = 0
    auction_skipped = 0
    first_skipped_ts = None
    first_auction_ts = None
    executable_bars = [b for b in bars if b.executable]
    forced_bar = None
    forced_at = cfg.forced_exit_time
    for bar_no, b in enumerate(bars):
        if forced_at is not None and _clock(b.ts) >= forced_at:  # the position is closed at this minute's open; later bars are never walked
            forced_bar = b
            break
        if not b.executable:  # reference / non-fillable bar: nothing may fill here, whatever its range touches
            skipped += 1
            if b.ineligible == "CLOSING_AUCTION_REFERENCE":
                auction_skipped += 1
                first_auction_ts = b.ts if first_auction_ts is None else first_auction_ts
            first_skipped_ts = b.ts if first_skipped_ts is None else first_skipped_ts
            touched = [name for name, lvl, adverse in (("stop", sl, True), ("Target 1", t1, False), ("Target 2", t2, False)) if
                       (hit_adverse(b, lvl) if adverse else hit_high(b, lvl))]
            if touched:
                amb.append(f"{b.ts}: {'/'.join(touched)} touched in a NON-EXECUTABLE bar (closing-auction reference): no fill is simulated")
            continue
        if not t1_done:
            stop_hit = hit_adverse(b, sl)
            t1_hit = hit_high(b, t1)
            if stop_hit and t1_hit:
                amb.append(f"{b.ts}: stop {sl} and Target 1 {t1} both touched in one 1-minute bar; resolved as STOP (adverse)")
            if stop_hit:
                px = stop_fill(b, sl)
                slip = (sl - px) if long else (px - sl)
                ev.append(f"{b.ts}: INITIAL_FULL_STOP, both legs out at {px}" + (f" (adverse slippage {slip:.2f} points)" if slip > 0 else ""))
                p = pts(px)
                return ExitResult(TradeOutcome.INITIAL_FULL_STOP, direction, entry, sl, t1, t2, px, px, b.ts, b.ts, p, p * qt, amb, (), ev,
                                  adverse_slippage_points=slip)
            if not t1_hit:
                continue
            t1_done, leg1_px, leg1_ts = True, t1, b.ts
            ev.append(f"{b.ts}: Target 1 {t1} booked on Leg 1 ({q1} qty); Leg 2 stop -> {stop2} (entry {entry}, {cfg.post_t1_stop_mode})")
            # same bar: does it also touch the post-T1 stop (order unknown)?
            legacy_entry_bar = entry_at_first_bar_open and bar_no == 0 and stop2 == entry
            stop2_touched = (b.l < stop2 if long else b.h > stop2) if legacy_entry_bar else hit_adverse(b, stop2)
            if stop2_touched:
                amb.append(f"{b.ts}: Target 1 and the post-T1 stop {stop2} both touched in one bar; resolved as the STOP (adverse)")
                # the stop only exists once Target 1 is booked, so the bar's OPEN (which came before T1) cannot be a gap through it: fill at its level
                return _be(direction, entry, sl, t1, t2, leg1_px, leg1_ts, b, cfg, amb, ev, qt, q1, q2, stop2, stop2)
            if hit_high(b, t2):
                ev.append(f"{b.ts}: Target 2 {t2} booked on Leg 2 ({q2} qty)")
                return _tgt(direction, entry, sl, t1, t2, leg1_px, leg1_ts, b, cfg, amb, ev, qt, q1, q2)
            continue
        # ---- Leg 2 only; the stop is the fixed post-T1 level (POST-T1-STOP-006): never trailed, never moved again
        be_hit = hit_adverse(b, stop2)
        t2_hit = hit_high(b, t2)
        if be_hit and t2_hit:
            amb.append(f"{b.ts}: Leg 2 stop {stop2} and Target 2 {t2} both touched in one bar; resolved as STOP (adverse)")
        if be_hit:
            return _be(direction, entry, sl, t1, t2, leg1_px, leg1_ts, b, cfg, amb, ev, qt, q1, q2, stop_fill(b, stop2), stop2)
        if t2_hit:
            ev.append(f"{b.ts}: Target 2 {t2} booked on Leg 2 ({q2} qty)")
            return _tgt(direction, entry, sl, t1, t2, leg1_px, leg1_ts, b, cfg, amb, ev, qt, q1, q2)

    # ---- forced exit (Phase 3): a position still open when the forced-exit minute arrives is closed at that bar's OPEN
    if forced_bar is not None and forced_bar.executable and _clock(forced_bar.ts) < FORCED_EXIT_LIMIT:  # never fill at/after 15:15 (a missing 15:14 bar leaves the position unresolved)
        px = forced_bar.o
        p_w = (pts(leg1_px) * q1 + pts(px) * q2) if t1_done else pts(px) * qt
        first = leg1_px if t1_done else px
        ev.append(f"{forced_bar.ts}: FORCED_EXIT, {'Leg 2 (' + str(q2) + ' qty)' if t1_done else 'all ' + str(qt) + ' qty'} closed at the bar open {px}")
        return ExitResult(TradeOutcome.FORCED_EXIT, direction, entry, sl, t1, t2, first, px, leg1_ts if t1_done else forced_bar.ts, forced_bar.ts,
                          p_w / qt, p_w, amb, (), ev, post_t1_stop_level=stop2 if t1_done else None, forced_exit_reference_close=forced_bar.c)

    # ---- bars exhausted with the position still open: the source defines no end-of-day rule
    last = executable_bars[-1] if executable_bars else None
    flags: tuple[str, ...] = ()
    if auction_skipped:
        flags = (f"UNRESOLVED_AT_CLOSING_AUCTION: position still open when the closing-auction reference bar {first_auction_ts} was reached; "
                 "no exit is invented (explicit Phase 3 treatment required)",)
        ev.append(f"{first_auction_ts}: {auction_skipped} closing-auction reference bar(s) skipped; position unresolved")
    elif skipped:
        ev.append(f"{first_skipped_ts}: {skipped} non-fillable post-close bar(s) skipped; position open at the end of the fillable bars")
    if cfg.eod_policy is EodPolicy.EXIT_AT_LAST_CLOSE and last is not None:
        px = last.c
        if t1_done:
            p_w = (pts(leg1_px) * q1 + pts(px) * q2)
            ev.append(f"{last.ts}: research EOD flatten of Leg 2 at {px}")
            return ExitResult(TradeOutcome.INCOMPLETE_EOD, direction, entry, sl, t1, t2, leg1_px, px, leg1_ts, last.ts, p_w / qt, p_w, amb,
                              ("eod_policy: EXIT_AT_LAST_CLOSE is a research option, not a source rule",), ev, skipped, False, bool(auction_skipped))
        p_w = pts(px) * qt
        ev.append(f"{last.ts}: research EOD flatten of the full position at {px}")
        return ExitResult(TradeOutcome.INCOMPLETE_EOD, direction, entry, sl, t1, t2, px, px, last.ts, last.ts, p_w / qt, p_w, amb,
                          ("eod_policy: EXIT_AT_LAST_CLOSE is a research option, not a source rule",), ev, skipped, False, bool(auction_skipped))
    realised = pts(leg1_px) * q1 if t1_done else 0.0
    return ExitResult(TradeOutcome.INCOMPLETE_EOD, direction, entry, sl, t1, t2, leg1_px, None, leg1_ts, None, realised / qt, realised, amb,
                      flags + ("end-of-day exit rule absent from the source documents",), ev, skipped, bool(auction_skipped), bool(auction_skipped))


def _clock(ts) -> time:
    """Exchange (IST) wall-clock time of a bar label (naive labels are taken as IST already)."""
    if getattr(ts, "tzinfo", None) is not None:
        ts = ts.astimezone(IST)
    return ts.time()


def _be(direction, entry, sl, t1, t2, leg1_px, leg1_ts, b, cfg, amb, ev, qt, q1, q2, px, stop2):
    """Leg 2 stopped at the post-T1 stop; ``px`` is the fill (worse of the level and the bar open: no favourable fill).
    Outcome ``T1_THEN_BUFFER_STOP`` (Phase 2.3) or, only in the superseded exact-entry mode, ``BREAKEVEN``."""
    long = direction == "LONG"
    slip = (stop2 - px) if long else (px - stop2)
    mode = TradeOutcome.T1_THEN_BUFFER_STOP if cfg.post_t1_stop_mode == "BUFFER" else TradeOutcome.BREAKEVEN
    ev.append(f"{b.ts}: post-T1 stop {stop2}, Leg 2 ({q2} qty) out at {px}" + (f" (adverse slippage {slip:.2f} points)" if slip > 0 else ""))
    leg1 = (leg1_px - entry) if long else (entry - leg1_px)
    leg2 = (px - entry) if long else (entry - px)
    total = leg1 * q1 + leg2 * q2
    return ExitResult(mode, direction, entry, sl, t1, t2, leg1_px, px, leg1_ts, b.ts, total / qt, total, amb, (), ev,
                      post_t1_stop_level=stop2, adverse_slippage_points=slip)


def _tgt(direction, entry, sl, t1, t2, leg1_px, leg1_ts, b, cfg, amb, ev, qt, q1, q2):
    long = direction == "LONG"
    leg1 = (leg1_px - entry) if long else (entry - leg1_px)
    leg2 = (t2 - entry) if long else (entry - t2)
    total = leg1 * q1 + leg2 * q2
    return ExitResult(TradeOutcome.TARGET, direction, entry, sl, t1, t2, leg1_px, t2, leg1_ts, b.ts, total / qt, total, amb, (), ev,
                      post_t1_stop_level=cfg.post_t1_stop(direction, entry))
