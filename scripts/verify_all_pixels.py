#!/usr/bin/env python3
"""Verify every row in vgwort-manifest.csv has a corresponding entry
in data/vgwort.yaml.

Replaces the original migration-era gate that checked for inline
`<img>` tags in content/*.md. After Phase 4 of the post-migration
verification pass, pixels are no longer inline — they live in
data/vgwort.yaml and are rendered by layouts/_partials/vgwort.html.
This script enforces the manifest ↔ data-file invariant: every
public_id registered in the manifest must be present in the data
file with a matching pixel_url. The end-to-end render check is
verify_rendered_pixels.py.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "vgwort-manifest.csv"
DATA = ROOT / "data" / "vgwort.yaml"


def main() -> int:
    if not MANIFEST.is_file():
        print(f"GATE FAIL: {MANIFEST.relative_to(ROOT)} missing.",
              file=sys.stderr)
        return 1
    if not DATA.is_file():
        print(f"GATE FAIL: {DATA.relative_to(ROOT)} missing — run "
              f"_scripts/migrate_vgwort_to_data.py.", file=sys.stderr)
        return 1

    rows = list(csv.DictReader(MANIFEST.open(encoding="utf-8")))
    entries = yaml.safe_load(DATA.read_text(encoding="utf-8")) or []

    by_pid_data: dict[str, dict] = {e["public_id"]: e for e in entries}
    missing: list[tuple[str, str]] = []
    mismatched: list[tuple[str, str, str]] = []

    for r in rows:
        pid = r["public_id"]
        url = r["pixel_url"]
        e = by_pid_data.get(pid)
        if not e:
            missing.append((r["qmd_path"], pid))
            continue
        if e["pixel_url"] != url:
            mismatched.append((pid, url, e["pixel_url"]))

    print(f"manifest rows: {len(rows)} · data entries: {len(entries)}")
    fail = False
    if missing:
        print(f"\nGATE FAIL: {len(missing)} manifest row(s) absent from "
              f"data/vgwort.yaml:", file=sys.stderr)
        for qmd, pid in missing[:15]:
            print(f"  {qmd}: public_id {pid}", file=sys.stderr)
        fail = True
    if mismatched:
        print(f"\nGATE FAIL: {len(mismatched)} pixel_url mismatch(es) "
              f"between manifest and data:", file=sys.stderr)
        for pid, m_url, d_url in mismatched[:5]:
            print(f"  {pid}: manifest={m_url}", file=sys.stderr)
            print(f"            data={d_url}", file=sys.stderr)
        fail = True
    if len(entries) > len(rows):
        print(f"\nWARN: data/vgwort.yaml has {len(entries) - len(rows)} "
              f"extra entries not in the manifest. (Likely follow-up "
              f"Zählmarken added after the manifest was last regenerated.)",
              file=sys.stderr)

    if fail:
        return 1
    print(f"OK: every manifest pixel_url is in data/vgwort.yaml.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
