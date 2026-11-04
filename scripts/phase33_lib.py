"""Phase 3.3 analysis library: raw-data reconstruction of the PDR setup, independent of the strategy engine.

Reads only the raw one-minute / daily parquet files and the Phase 3.2 CSV exports (as inputs to compare against). It imports NOTHING from ``nifty_trading``: candles,
zones, the PDR state machine and the candle geometry are re-implemented from the written rules (PDR guide pp.1-3 and the owner-approved research configuration), so every
agreement with the engine is evidence and every disagreement is reported. Read-only: nothing here changes a rule, a ledger or a data file.
"""

from __future__ import annotations

import csv
import glob
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
P32 = ROOT / "reports" / "phase3" / "phase32"
P31 = ROOT / "reports" / "phase3" / "phase31"
EPS = 1e-9
SESSION_START_MIN = 9 * 60 + 15
CAS_START = date(2026, 8, 3)  # NSE closing-auction regime: continuous trading ends 15:15 (data/metadata/nse_calendar_2025_2026.json)
CAS_FIRST_AUCTION_MIN = 15 * 60 + 15


def rows(path: Path) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------------------------------------- raw data
def _read(pattern: str) -> pd.DataFrame:
    return pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(str(ROOT / pattern), recursive=True))]).sort_values("timestamp").reset_index(drop=True)


@dataclass
class Candle:
    start: datetime
    open: float
    high: float
    low: float
    close: float

    @property
    def end(self) -> datetime:
        return self.start + timedelta(minutes=5)

    @property
    def green(self) -> bool:
        return self.close > self.open

    @property
    def red(self) -> bool:
        return self.close < self.open


class World:
    """All raw inputs: 1-minute bars per day, standard-session 5-minute candles per day, official closes."""

    def __init__(self) -> None:
        raw = pd.concat([_read("data/processed/nifty50_warmup/**/*.parquet"), _read("data/processed/nifty50/**/*.parquet")]).drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)
        raw["day"] = raw.timestamp.dt.date
        raw["mod"] = raw.timestamp.dt.hour * 60 + raw.timestamp.dt.minute
        self.minutes = {d: g.reset_index(drop=True) for d, g in raw.groupby("day")}
        g = raw.groupby("day").agg(first=("mod", "min"), n=("mod", "count"))
        self.standard = sorted(g[(g["first"] == SESSION_START_MIN) & (g["n"] >= 300)].index)  # excludes special sessions such as the Diwali Muhurat hour
        daily = pd.read_parquet(ROOT / "data/processed/nifty50_daily/candles.parquet")
        self.official_close = {pd.Timestamp(str(r["date"])[:10]).date(): float(r["close"]) for r in daily.to_dict("records")}
        self.candles: dict[date, list[Candle]] = {}
        for d in self.standard:
            m = self.minutes[d]
            m = m[(m["mod"] >= SESSION_START_MIN) & (m["mod"] <= 929)].copy()
            m["bucket"] = (m["mod"] - SESSION_START_MIN) // 5
            out = []
            for _, b in m.groupby("bucket", sort=True):
                if len(b) == 5:
                    out.append(Candle(b.timestamp.iloc[0].to_pydatetime(), float(b.open.iloc[0]), float(b.high.max()), float(b.low.min()), float(b.close.iloc[-1])))
            self.candles[d] = out
        self.index = {d: i for i, d in enumerate(self.standard)}

    def prev(self, d: date) -> date | None:
        i = self.index.get(d)
        return self.standard[i - 1] if i else None

    def first_open(self, d: date) -> float:
        return float(self.minutes[d].open.iloc[0])

    def minute_bar(self, ts: datetime) -> pd.Series | None:
        m = self.minutes[ts.date()]
        hit = m[m.timestamp == pd.Timestamp(ts)]
        return None if hit.empty else hit.iloc[0]


# ---------------------------------------------------------------------------------------------------- zones
def swing_highs(cs: list[Candle], k: int) -> list[int]:
    return [j for j in range(k, len(cs) - k) if all(cs[j].high > cs[j - m].high and cs[j].high > cs[j + m].high for m in range(1, k + 1))]


@dataclass
class Zone:
    name: str
    lo: float
    hi: float
    members: tuple[int, ...]
    cs: list[Candle]

    @property
    def source(self) -> Candle:
        return self.cs[self.members[-1]]


def _body_top(c: Candle) -> float:
    return max(c.open, c.close)


def zone_engine_b(cs: list[Candle], k: int) -> Zone | None:
    """B_SWING_HIGH_REVERSAL: the latest confirmed swing high (k candles each side, strict) with a red candle among the peak and the next k candles; [body top, wick high]."""
    for j in reversed(swing_highs(cs, k)):
        if any(cs[m].red for m in range(j, min(len(cs), j + k + 1))):
            return Zone("B_SWING_HIGH_REVERSAL", _body_top(cs[j]), cs[j].high, (j,), cs)
    return None


def zone_a_day_high(cs: list[Candle]) -> Zone:
    """The candle carrying the previous session's absolute high (first occurrence); [body top, wick high]."""
    top = max(c.high for c in cs)
    j = next(i for i, c in enumerate(cs) if c.high == top)
    return Zone("A_PREVIOUS_DAY_HIGH_CANDLE", _body_top(cs[j]), cs[j].high, (j,), cs)


def zone_c_shelf(cs: list[Candle], k: int, tol: float, min_touches: int) -> Zone | None:
    """C_REPEATED_TOUCHES: cluster confirmed swing highs whose highs lie within ``tol`` of the cluster extreme (greedy from the highest); the most extreme cluster with >= min_touches."""
    idxs = swing_highs(cs, k)
    pool = sorted(idxs, key=lambda j: cs[j].high, reverse=True)
    used: set[int] = set()
    for j0 in pool:
        if j0 in used:
            continue
        ext = cs[j0].high
        members = [j for j in pool if j not in used and abs(cs[j].high - ext) <= tol + 1e-9]
        used.update(members)
        if len(members) >= min_touches:
            ms = tuple(sorted(members))
            return Zone("C_REPEATED_TOUCHES", min(_body_top(cs[m]) for m in ms), max(cs[m].high for m in ms), ms, cs)
    return None


def run_state_machine(today: list[Candle], z: Zone, prox: float = 0.0) -> list[dict]:
    """PDR sequence with the engine's re-arming and the per-session cap lifted: a candle whose range intersects the zone (+/- proximity) opens a test; the first LATER green candle
    confirms; the machine then re-arms from the next candle. Returns every confirmation (index of the interaction candle j and of the confirmation candle i)."""
    out, j = [], None
    for i, c in enumerate(today):
        if j is None:
            if c.low <= z.hi + prox and c.high >= z.lo - prox:
                j = i
            continue
        if c.green and i > j:
            out.append({"j": j, "i": i})
            j = None
    return out


# ---------------------------------------------------------------------------------------------------- geometry
def geometry(c: Candle) -> dict:
    rng = c.high - c.low
    body = abs(c.close - c.open)
    uw, lw = c.high - max(c.open, c.close), min(c.open, c.close) - c.low
    z = rng <= 0
    return {"range": rng, "body": body, "body_pct": None if z else 100 * body / rng, "upper_wick": uw, "upper_wick_pct": None if z else 100 * uw / rng, "lower_wick": lw,
            "lower_wick_pct": None if z else 100 * lw / rng, "direction": "BULLISH" if c.close > c.open else ("BEARISH" if c.close < c.open else "DOJI")}


def hm(ts: datetime) -> str:
    return f"{ts:%H:%M}"


def config() -> dict:
    return json.loads((P32 / "configuration_snapshot.json").read_text())["proposal_config"]
