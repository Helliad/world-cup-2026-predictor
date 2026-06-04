"""Pull + validate the latest data snapshot (§8.3, §8.4).

Downloads the upstream martj42 results.csv, validates it against the ingest
contract, records checksum + row count + max date into a snapshot manifest, and
**fails loudly** if validation fails or the row count shrinks suspiciously. Never
overwrites the committed snapshot unless validation passes.

Usage:
  python -m scripts.refresh_data            # download, validate, write snapshot + manifest
  python -m scripts.refresh_data --check     # validate the committed snapshot only (no download)
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from config import load_config, resolve_path
from scripts.validate_data import load_aliases, validate_results

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "snapshot_manifest.json"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_prev_manifest() -> dict | None:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return None


def write_manifest(df: pd.DataFrame, raw: bytes, source_url: str) -> dict:
    played = df["home_score"].notna() & df["away_score"].notna()
    manifest = {
        "source_url": source_url,
        "downloaded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "rows": int(len(df)),
        "played_rows": int(played.sum()),
        "max_date": str(df["date"].max()),
        "sha256": sha256_bytes(raw),
        "schema_columns": list(df.columns),
        "license": "CC BY-NC-SA 4.0 (martj42/international_results) — see data/README.md",
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def fetch(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "wc2026-refresh/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (trusted https URL)
        return resp.read()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Refresh + validate the results.csv snapshot.")
    ap.add_argument(
        "--check", action="store_true", help="Validate committed snapshot only; do not download."
    )
    args = ap.parse_args(argv)

    cfg = load_config()
    snapshot_path = resolve_path(cfg["data"]["snapshot_path"])
    source_url = cfg["data"]["source_url"]
    prev = read_prev_manifest()
    prev_rows = prev.get("rows") if prev else None

    if args.check:
        raw = snapshot_path.read_bytes()
        print(f"Validating committed snapshot {snapshot_path.relative_to(ROOT)} ...")
    else:
        print(f"Downloading {source_url} ...")
        raw = fetch(source_url)

    df = pd.read_csv(io.BytesIO(raw), encoding="utf-8")

    # Schema-version guard: column set must match what the pipeline expects.
    rep = validate_results(df, aliases=load_aliases(), prev_row_count=prev_rows)
    print(rep.render())
    if not rep.ok:
        print("\nREFRESH ABORTED: validation errors. Snapshot NOT updated.", file=sys.stderr)
        return 1

    if not args.check:
        snapshot_path.write_bytes(raw)
        manifest = write_manifest(df, raw, source_url)
        print(f"\nSnapshot updated: {snapshot_path.relative_to(ROOT)}")
        print(
            f"Manifest: rows={manifest['rows']} max_date={manifest['max_date']} sha256={manifest['sha256'][:12]}..."
        )
    else:
        # Even in --check mode, (re)write the manifest so checksum/stats stay current.
        manifest = write_manifest(df, raw, source_url)
        print(f"\nManifest refreshed for committed snapshot: rows={manifest['rows']}")

    print("\nREFRESH OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
