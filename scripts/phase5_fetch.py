"""Phase 5: resumable, read-only retrieval of BANKNIFTY / SENSEX index candles into SEPARATE raw namespaces (never under the NIFTY directories).

  --source 5paisa     data/raw/<index>/5paisa/{1m,1d}/*.csv + manifest.json   provider responses saved unmodified, one file per request; request parameters, UTC time, rows, first / last timestamp, SHA-256 and a classified
                      status (COMPLETED | EMPTY | RATE_LIMITED | ACCESS_DENIED | FAILED). Completed requests are skipped on a re-run; EMPTY / failed ones are retried only with --retry-empty / --retry-failed.
                      The instrument mapping is read from data/metadata/phase5/<index>_instrument.json (written by scripts/phase5_discover.py from the broker's instrument master); nothing is copied from NIFTY.
  --source secondary  data/raw/<index>/secondary_kapri/<commit sha>/   the GitHub repository's CSV exactly as served, README, LICENSE and a manifest (commit, per-file git blob SHA-1 re-computed and compared with
                      the repository tree, SHA-256, licence). EXPLORATORY: the repository does not name its data vendor. Nothing is merged with the 5paisa data.

Uses the project's BrokerClient (read-only endpoints; order methods are disabled there) and never prints credentials.

Examples
  python scripts/phase5_fetch.py --index BANKNIFTY --source 5paisa --minutes --daily
  python scripts/phase5_fetch.py --index SENSEX --source 5paisa --minutes --daily
  python scripts/phase5_fetch.py --index BANKNIFTY --source secondary
  python scripts/phase5_fetch.py --index SENSEX --source secondary
"""

from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import sys
import time
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nifty_trading.research.phase5_data import DAILY_RANGE, INDEXES, MINUTE_MONTHS_5P  # noqa: E402


def months(a: tuple[int, int], b: tuple[int, int]):
    y, m = a
    while (y, m) <= b:
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def classify_error(msg: str) -> str:
    low = msg.lower()
    if "429" in low or "rate" in low or "too many" in low or "throttl" in low:
        return "RATE_LIMITED"
    if "unauthor" in low or "forbidden" in low or "denied" in low or "401" in low or "403" in low or "token" in low or "session" in low:
        return "ACCESS_DENIED"
    return "FAILED"


def save_manifest(path: Path, m: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(m, indent=1, sort_keys=True))
    tmp.replace(path)


def fetch_5paisa(ix, a) -> int:
    raw = ix.raw_5p
    manifest_path = raw / "manifest.json"
    inst_path = ix.instrument_file
    if not inst_path.exists():
        raise SystemExit(f"{inst_path} is missing: run scripts/phase5_discover.py first")
    inst = json.loads(inst_path.read_text())
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {
        "provider": "5paisa", "index": ix.key, "instrument_file": str(inst_path.relative_to(ROOT)), "instrument": {k: inst[k] for k in ("symbol", "exchange", "exchange_segment", "scrip_code")},
        "documentation": "https://xstream.5paisa.com/dev-docs/market-data-system/historical-candles", "requests": {}}
    assert manifest["instrument"]["scrip_code"] == inst["scrip_code"], "manifest was written for a different instrument"
    from nifty_trading.broker.client import BrokerClient
    broker = BrokerClient()
    jobs: list[tuple[str, date, date]] = []
    if a.daily:
        s = DAILY_RANGE[0]
        while s <= DAILY_RANGE[1]:
            e_m = s.month + 5
            e_y = s.year + (e_m - 1) // 12
            e_m = (e_m - 1) % 12 + 1
            e = min(date(e_y, e_m, calendar.monthrange(e_y, e_m)[1]), DAILY_RANGE[1])
            jobs.append(("1d", s, e))
            s = date(e.year + (e.month == 12), 1 if e.month == 12 else e.month + 1, 1)
    if a.minutes:
        for lo, hi in MINUTE_MONTHS_5P:
            jobs += [("1m", date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])) for y, m in months(lo, hi)]
    if a.probe_empty:
        jobs += [("1m", date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])) for y, m in months((2018, 1), (2019, 2))]
    counts: dict[str, int] = {}
    for tf, d0, d1 in jobs:
        key = f"{tf}_{d0}_{d1}"
        prev = manifest["requests"].get(key)
        if prev and ((prev["status"] == "COMPLETED" and (raw / prev["file"]).exists()) or (prev["status"] == "EMPTY" and not a.retry_empty) or (prev["status"] in ("FAILED", "RATE_LIMITED", "ACCESS_DENIED") and not a.retry_failed)):
            counts["SKIP_" + prev["status"]] = counts.get("SKIP_" + prev["status"], 0) + 1
            continue
        rec = {"timeframe": tf, "from": str(d0), "to": str(d1), "scrip_code": inst["scrip_code"], "exchange": inst["exchange"], "exchange_segment": inst["exchange_segment"]}
        status, err, df = "FAILED", None, None
        for k in range(3):
            rec["attempts"] = k + 1
            rec["requested_utc"] = datetime.now(timezone.utc).isoformat()
            try:
                df = broker.fetch_historical_candles(inst["exchange"], inst["exchange_segment"], inst["scrip_code"], tf, str(d0), str(d1))
                status, err = ("EMPTY" if df is None or len(df) == 0 else "COMPLETED"), None
                break
            except Exception as e:  # noqa: BLE001 - classified, never includes credentials
                err = f"{type(e).__name__}: {str(e)[:300]}"
                status = classify_error(err)
                if status == "ACCESS_DENIED":
                    break
                time.sleep(5 * (k + 1) * (3 if status == "RATE_LIMITED" else 1))
        rec["status"], rec["error"] = status, err
        if status == "COMPLETED":
            sub = raw / tf
            sub.mkdir(parents=True, exist_ok=True)
            path = sub / f"{key}.csv"
            df.to_csv(path, index=False)  # the provider's DataFrame exactly as returned
            c0 = df.columns[0]
            rec.update({"file": str(path.relative_to(raw)), "rows": int(len(df)), "columns": list(df.columns), "first_timestamp": str(df[c0].iloc[0]), "last_timestamp": str(df[c0].iloc[-1]),
                        "distinct_dates": int(df[c0].astype(str).str[:10].nunique()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        manifest["requests"][key] = rec
        save_manifest(manifest_path, manifest)
        counts[status] = counts.get(status, 0) + 1
        print(f"{ix.key} {tf} {d0}..{d1}: {status} rows={rec.get('rows', 0)} {err or ''}", flush=True)
        if status == "ACCESS_DENIED":
            print("access denied: stopping (credentials / session must be fixed by the owner)", file=sys.stderr)
            break
        time.sleep(a.pause)
    print(f"{ix.key} summary: {counts}")
    return 0 if not any(k in counts for k in ("FAILED", "RATE_LIMITED", "ACCESS_DENIED")) else 1


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "nifty-options-research/phase5 (read-only data audit)", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=300) as r:  # noqa: S310 - fixed https URLs on github.com / raw.githubusercontent.com
        return r.read()


def blob_sha1(b: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()  # noqa: S324 - git's own object id, only to cross-check the tree listing


def fetch_secondary(ix, a) -> int:
    repo = ix.secondary_repo
    api = f"https://api.github.com/repos/{repo}"
    meta = json.loads(get(api))
    commit = json.loads(get(f"{api}/commits/{a.commit or meta['default_branch']}"))
    sha = commit["sha"]
    tree = json.loads(get(f"{api}/git/trees/{sha}?recursive=1"))
    assert not tree.get("truncated"), "repository tree listing truncated"
    blobs = {t["path"]: t for t in tree["tree"] if t["type"] == "blob"}
    wanted = ["README.md", "LICENSE", ix.secondary_file]
    out = ROOT / "data" / "raw" / ix.key / "secondary_kapri" / sha
    manifest = {"repository": f"https://github.com/{repo}", "commit_sha": sha, "commit_date": commit["commit"]["committer"]["date"], "commit_message": commit["commit"]["message"][:200], "default_branch": meta["default_branch"],
                "repo_license_spdx": (meta.get("license") or {}).get("spdx_id"), "repo_description": meta.get("description"), "retrieved_utc": datetime.now(timezone.utc).isoformat(), "files": {},
                "note": "files stored exactly as served; the blob SHA-1 is git's object id and is checked against the repository tree; the underlying data vendor is not named by the repository (README: 'extracted from a reliable financial data provider')"}
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
            body = get(f"https://raw.githubusercontent.com/{repo}/{sha}/{path}")
            dest.write_bytes(body)
        ok = blob_sha1(body) == blobs[path]["sha"]
        manifest["files"][path] = {"status": "OK" if ok else "BLOB_SHA_MISMATCH", "git_blob_sha": blobs[path]["sha"], "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}
        print(f"{ix.key} {path}: {'OK' if ok else 'BLOB SHA MISMATCH'} {len(body):,} bytes", flush=True)
    save_manifest(out / "manifest.json", manifest)
    return 0 if all(f["status"] == "OK" for f in manifest["files"].values()) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 1)[1])
    ap.add_argument("--index", required=True, choices=sorted(INDEXES), help="index to retrieve")
    ap.add_argument("--source", required=True, choices=["5paisa", "secondary"])
    ap.add_argument("--minutes", action="store_true", help="5paisa: monthly 1-minute requests 2019-03..2019-12 and 2022-08..2026-08")
    ap.add_argument("--daily", action="store_true", help="5paisa: daily candles 2017-01-01..2026-08-31 in <=6-month spans")
    ap.add_argument("--probe-empty", action="store_true", help="5paisa: one 1-minute request per month 2018-01..2019-02 to document the uncovered period")
    ap.add_argument("--retry-empty", action="store_true")
    ap.add_argument("--retry-failed", action="store_true")
    ap.add_argument("--commit", default=None, help="secondary: pin to this commit SHA (default: current HEAD)")
    ap.add_argument("--pause", type=float, default=1.0, help="seconds between 5paisa requests (in addition to the client's rate limiter)")
    a = ap.parse_args()
    ix = INDEXES[a.index]
    if a.source == "5paisa":
        if not (a.minutes or a.daily or a.probe_empty):
            ap.error("--source 5paisa needs --minutes and/or --daily (and optionally --probe-empty)")
        return fetch_5paisa(ix, a)
    return fetch_secondary(ix, a)


if __name__ == "__main__":
    raise SystemExit(main())
