"""Phase 4: retrieve the SECONDARY 1-minute NIFTY 50 source (github.com/technovusin/nifty50-historical-data) into its own raw namespace, pinned to one commit.

Writes only under data/raw/phase4_technovusin/<commit-sha>/ : the CSV files exactly as served, README.md and LICENSE, and manifest.json (repository, commit SHA/date/message, per-file git blob SHA, SHA-256, size,
download time, licence and README hashes). Each file's git blob SHA-1 is recomputed from the downloaded bytes and compared with the repository's own tree listing (an integrity check against the repository, not
an independent check of the market data). Nothing here is merged with the 5paisa data.

Usage: python scripts/phase4_fetch_secondary.py [--years 2017 2018 2019 2022 2023 2024 2025] [--with-2026]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = "technovusin/nifty50-historical-data"
API = f"https://api.github.com/repos/{REPO}"
DEFAULT_YEARS = (2017, 2018, 2019, 2022, 2023, 2024, 2025)  # 2017: warm-up for 2018; 2022-2025: vendor-overlap audit and the vendor-sensitivity run of Window B


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "nifty-options-research/phase4 (read-only data audit)", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=120) as r:  # noqa: S310 - fixed https URLs on github.com / raw.githubusercontent.com
        return r.read()


def blob_sha1(b: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()  # noqa: S324 - git's own object id, used only to cross-check the tree listing


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--years", type=int, nargs="*", default=list(DEFAULT_YEARS))
    ap.add_argument("--with-2026", action="store_true", help="also the monthly 2026 files (overlap audit against the Phase 1 dataset)")
    ap.add_argument("--commit", default=None, help="pin to this commit SHA (default: current HEAD of the default branch)")
    a = ap.parse_args()
    meta = json.loads(get(f"{API}"))
    commit = json.loads(get(f"{API}/commits/{a.commit or meta['default_branch']}"))
    sha = commit["sha"]
    tree = json.loads(get(f"{API}/git/trees/{sha}?recursive=1"))
    assert not tree.get("truncated"), "repository tree listing truncated"
    blobs = {t["path"]: t for t in tree["tree"] if t["type"] == "blob"}
    wanted = ["README.md", "LICENSE"] + [f"1min/{y}/NIFTY50_1min_{y}.csv" for y in a.years]
    if a.with_2026:
        wanted += sorted(p for p in blobs if p.startswith("1min/2026/") and p.endswith(".csv"))
    out = ROOT / "data" / "raw" / "phase4_technovusin" / sha
    manifest = {"repository": f"https://github.com/{REPO}", "commit_sha": sha, "commit_date": commit["commit"]["committer"]["date"], "commit_message": commit["commit"]["message"][:200], "default_branch": meta["default_branch"],
                "repo_license_spdx": (meta.get("license") or {}).get("spdx_id"), "repo_description": meta.get("description"), "retrieved_utc": datetime.now(timezone.utc).isoformat(), "files": {},
                "note": "files stored exactly as served; the blob SHA-1 is git's object id and is checked against the repository tree; the underlying data vendor is not named by the repository"}
    for path in wanted:
        if path not in blobs:
            manifest["files"][path] = {"status": "NOT_IN_REPOSITORY"}
            print(f"{path}: NOT IN REPOSITORY")
            continue
        dest = out / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and blob_sha1(dest.read_bytes()) == blobs[path]["sha"]:
            body = dest.read_bytes()
        else:
            body = get(f"https://raw.githubusercontent.com/{REPO}/{sha}/{path}")
            dest.write_bytes(body)
        ok = blob_sha1(body) == blobs[path]["sha"]
        manifest["files"][path] = {"status": "OK" if ok else "BLOB_SHA_MISMATCH", "git_blob_sha": blobs[path]["sha"], "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}
        print(f"{path}: {'OK' if ok else 'BLOB SHA MISMATCH'} {len(body):,} bytes")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True))
    return 0 if all(f["status"] == "OK" for f in manifest["files"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
