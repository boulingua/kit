#!/usr/bin/env python3
"""Gate C13 — the render-path JavaScript budget.

    python scripts/verify_js_budget.py public/

Promoted from daf, which is the only site that had it. Two caps, and the split
is the substance: the glue we ship eagerly is held tight, while the graph
library is dynamically imported only when the network scrolls into view and is
therefore measured against a looser total.

  render-path glue   <= 88 KB gzipped   main / filters / search / list
  total (incl. lazy) <= 280 KB gzipped  the above plus vendor.*.js

A language course is read on school hardware and on phones. A budget that is
not enforced is a budget that is exceeded, and the failure is invisible to the
person who caused it — nobody notices 40 KB, they notice the fortieth 40 KB.
"""
from __future__ import annotations

import gzip
import sys
from pathlib import Path

GLUE_MAX = 90_112     # 88 KB
TOTAL_MAX = 286_720   # 280 KB


def gz_size(p: Path) -> int:
    return len(gzip.compress(p.read_bytes(), 9))


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "public")
    net = root / "js" / "network"
    if not net.exists():
        print(f"  no {net} — this course ships no network graph, nothing to budget")
        return 0
    js = sorted(net.glob("*.js"))
    glue = sum(gz_size(p) for p in js if not p.name.startswith("vendor."))
    total = sum(gz_size(p) for p in js)
    print(f"  render-path glue: {glue:,} B gz (cap {GLUE_MAX:,})")
    print(f"  total incl. lazy: {total:,} B gz (cap {TOTAL_MAX:,})")
    bad = 0
    if glue > GLUE_MAX:
        print(f"::error::render-path glue exceeds the 88 KB gzipped budget ({glue} B)")
        bad += 1
    if total > TOTAL_MAX:
        print(f"::error::total network JS exceeds the 280 KB gzipped budget ({total} B)")
        bad += 1
    if bad:
        return 1
    print("C13 OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
