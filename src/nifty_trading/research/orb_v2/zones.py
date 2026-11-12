"""Level / zone break tests. A level is a Level(floor, ceiling); a single price has floor == ceiling. BUY breaks resistance (close beyond the CEILING), SELL breaks support
(close beyond the FLOOR): a genuine zone is never collapsed to one price. The closing-boundary convention (strict vs inclusive) is TO_CONFIRM and kept explicit."""

from __future__ import annotations

from nifty_trading.research.orb_v2.config import OrbV2Config
from nifty_trading.research.orb_v2.models import Level


def broken(level: Level, direction: str, o: float, c: float, cfg: OrbV2Config) -> bool:
    strict = cfg.boundary == "STRICT"
    if direction == "BUY":
        if level.side != "RESISTANCE":
            return False
        edge = level.ceiling
        beyond = c > edge if strict else c >= edge
        old_side_ok = True if cfg.break_mode == "CLOSE_BEYOND" else o <= edge
        return beyond and old_side_ok
    if level.side != "SUPPORT":
        return False
    edge = level.floor
    beyond = c < edge if strict else c <= edge
    old_side_ok = True if cfg.break_mode == "CLOSE_BEYOND" else o >= edge
    return beyond and old_side_ok


def describe(level: Level) -> str:
    rng = f"{level.floor:.2f}" if not level.is_zone else f"{level.floor:.2f}-{level.ceiling:.2f}"
    return f"{level.kind} {level.side} [{level.method}] {rng} ({level.evidence})"
