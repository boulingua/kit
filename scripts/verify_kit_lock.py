#!/usr/bin/env python3
"""Gate A5 — the vendored surface has not drifted.

    python scripts/verify_kit_lock.py REPO

`_materials/` is the ONLY vendored surface in this organisation: the LaTeX
styles, the fonts and the brand icons, copied into each course because XeLaTeX
cannot read a Hugo module. Everything else arrives by import or CI checkout and
therefore cannot fork.

Which means this directory is the entire drift surface, and it is hashed. A
one-byte edit to a vendored .sty fails here rather than being discovered months
later when two courses render differently — which is exactly what happened
before, when nine of sixteen shared scripts had forked byte-for-byte and
nothing was looking.

A course with no `_materials/` passes: it has not synced yet.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path


def main() -> int:
    repo = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    mat = repo / "_materials"
    lock = mat / "kit.lock"
    if not mat.exists():
        print("  no _materials/ — not synced yet")
        return 0
    if not lock.exists():
        print("::error::_materials/ exists with no kit.lock. Run `kit sync` — an "
              "unhashed vendored surface is the drift this file prevents.")
        return 1
    want = {}
    for line in lock.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        digest, _, rel = line.partition("  ")
        want[rel] = digest
    bad = 0
    for rel, digest in sorted(want.items()):
        p = mat / rel
        if not p.exists():
            print(f"::error::_materials/{rel} is in kit.lock but missing on disk")
            bad += 1
            continue
        got = hashlib.sha256(p.read_bytes()).hexdigest()
        if got != digest:
            print(f"::error::_materials/{rel} was edited in place. The vendored "
                  f"surface is a copy of the kit, not a place to change things — "
                  f"change it in the kit and re-sync.")
            bad += 1
    on_disk = {p.relative_to(mat).as_posix() for p in mat.rglob("*")
               if p.is_file() and p.name != "kit.lock"}
    for extra in sorted(on_disk - set(want)):
        print(f"::error::_materials/{extra} is not in kit.lock — it did not come "
              f"from `kit sync`")
        bad += 1
    if bad:
        print(f"\nA5 FAIL — {bad} divergence(s) in the vendored surface", file=sys.stderr)
        return 1
    print(f"A5 OK — {len(want)} vendored files match kit.lock")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
