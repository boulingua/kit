#!/usr/bin/env python3
"""Gate B3 — the search index was actually built and is not empty.

    python scripts/verify_pagefind.py public/

Promoted from daf. A missing index does not break the build and does not look
broken: the page renders, the search box appears, and it returns nothing. So
this checks the index exists AND carries entries, because "the directory is
there" is the failure this is meant to catch.

Opt-in is handled by the battery. Once invoked, a missing index is a failure.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "public")
    pf = root / "pagefind"
    if not pf.exists():
        print("::error::search is enabled but pagefind/ is missing; build the index")
        return 1
    entries = list(pf.glob("pagefind-entry.json")) or list(pf.glob("*.pf_meta"))
    frags = list((pf / "fragment").glob("*")) if (pf / "fragment").exists() else []
    if not entries:
        print("::error::pagefind/ exists but carries no entry file — the index "
              "did not build. Search will render and return nothing.")
        return 1
    n = 0
    for e in entries:
        if e.suffix == ".json":
            try:
                n = len(json.loads(e.read_text(encoding="utf-8")).get("languages", {}))
            except (ValueError, OSError) as exc:
                print(f"::error::{e}: invalid index metadata: {exc}")
                return 1
            if not n:
                print(f"::error::{e}: index declares no languages")
                return 1
    print(f"  pagefind index present: {len(entries)} entry file(s), "
          f"{len(frags)} fragment(s)")
    if not frags:
        print("::error::the index has no fragments — it built empty, which "
              "renders a working search box over nothing")
        return 1
    print("B3 OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
