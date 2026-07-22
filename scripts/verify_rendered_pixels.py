#!/usr/bin/env python3
"""Verify every VG Wort pixel URL from vgwort-manifest.csv appears in the
rendered Hugo output under public/. This is the deploy-gate verification.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    rows = list(csv.DictReader((ROOT / "vgwort-manifest.csv").open(encoding="utf-8")))
    public = ROOT / "public"
    if not public.is_dir():
        print("public/ missing — run `hugo --minify` first", file=sys.stderr)
        return 2

    # Index every URL once across the entire build output.
    found: dict[str, int] = {}
    for html in public.rglob("*.html"):
        try:
            txt = html.read_text(encoding="utf-8")
        except Exception:
            continue
        # Aliases redirect-pages contain just a meta refresh, no pixel; skip.
        if '<meta http-equiv="refresh"' in txt[:500]:
            continue
        for r in rows:
            if r["pixel_url"] in txt:
                found[r["pixel_url"]] = found.get(r["pixel_url"], 0) + 1

    total = len(rows)
    missing = [r for r in rows if r["pixel_url"] not in found]
    if missing:
        print("MISSING pixels in rendered output:")
        for r in missing[:20]:
            print(f"  {r['qmd_path']}: {r['pixel_url']}")
        print(f"\n{len(missing)} of {total} pixels missing from public/.")
        return 1
    print(f"All {total} pixels found in public/. (Total occurrences: "
          f"{sum(found.values())} across {len([h for h in public.rglob('*.html')])} pages.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
