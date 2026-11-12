"""Shared helpers for the Phase 6.0 scripts (paths, window cache outside the repo, CSV writer)."""

from __future__ import annotations

import csv
import pickle
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "reports" / "phase6" / "phase60_orb_from_scratch"
CACHE = Path("/private/tmp/claude-501/-Users-syedaskari-algo-nifty-options/dc8ac295-6b01-4d30-b811-e11236c4316e/scratchpad/phase60_cache")

WINDOW_KEYS = (("A", "5P"), ("B", "5P"), ("A", "TV"), ("B", "TV"))


def get_window(w: str, vendor: str = "5P"):
    from nifty_trading.research.orb_v2 import data_access as DA
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"window_{w}_{vendor}.pkl"
    if p.exists():
        inp = pickle.loads(p.read_bytes())
    else:
        inp = DA.load_window(w, vendor)
        p.write_bytes(pickle.dumps(inp, protocol=4))
    DA.index_positions(inp)
    return inp


def write_csv(path: Path, rows: list[dict], cols: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text(",".join(cols) + "\n" if cols else "")
        return
    cols = cols or list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else (f"{r[k]:.6f}".rstrip("0").rstrip(".") if isinstance(r.get(k), float) else r.get(k))) for k in cols})
