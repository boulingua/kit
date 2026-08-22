#!/usr/bin/env python3
"""Gate C2 — every locked mark renders, on exactly one page, the right page.

    verify_rendered_pixels.py REPO [BUILT]

A3 proves no URL moved. It cannot see the failure that costs money, because
that failure moves no URL: a flat-to-bundle conversion keeps every address and
changes .File.Path, so a path:-keyed registry stops matching and the pixel
disappears from a page that is still there. Measured on daf, that is 60 of 68
marks going dark while A3 passes clean and the build exits 0.

So C2 asserts PRESENCE, not stability, and it is the gate that had to exist
before P3.2 could be merged.

It also used to resolve its own lock from __file__, which meant it read the
KIT's vgwort/ directory while standing in a course — the file is not there, so
it crashed with FileNotFoundError and returned non-zero. It looked like a
failing gate and it was an absent one: it had never run against a course at
all. That is the fifth script in this kit found deriving its target from its
own location rather than from its argument.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

PIXEL_RE = re.compile(r"met\.vgwort\.de/na/([0-9a-f]{32})")


def main() -> int:
    # The battery hands a needs:built gate the BUILT directory; a person runs
    # it against the repo. Accept either rather than making the caller
    # remember, because a gate that is awkward to invoke is a gate that gets
    # invoked wrongly and then reported as broken.
    arg = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    if (arg / "vgwort").is_dir() or (arg / "hugo.toml").exists():
        repo, public = arg, (Path(sys.argv[2]).resolve()
                             if len(sys.argv) > 2 else arg / "public")
    else:
        repo, public = arg.parent, arg
    lock = repo / "vgwort" / "url-lock-provisional.csv"
    if not lock.exists():
        print(f"::error::vgwort/url-lock-provisional.csv is missing. A course "
              f"carrying registered marks must carry the lock.", file=sys.stderr)
        return 2
    rows = [r for r in csv.DictReader(
        l for l in lock.open(encoding="utf-8") if not l.startswith("#"))
        if r.get("url") and r.get("code")]
    if not rows:
        print("::error::the lock is empty or has no url/code columns. An empty "
              "lock is not a passing gate — it is the trivial pass that "
              "verify-vgwort.sh has printed against a header-only manifest for "
              "a year.", file=sys.stderr)
        return 2
    if not public.is_dir():
        print(f"::error::{public} missing — build the site first", file=sys.stderr)
        return 2

    # Index the whole build once: code -> [url, ...]. Alias stubs are skipped;
    # they are meta-refresh pages and carry no pixel by design.
    rendered: dict[str, list[str]] = {}
    for html in sorted(public.rglob("index.html")):
        txt = html.read_text(encoding="utf-8", errors="replace")
        if 'http-equiv="refresh"' in txt[:1200]:
            continue
        rel = "/" if html.parent == public else \
            "/" + html.parent.relative_to(public).as_posix() + "/"
        for c in set(PIXEL_RE.findall(txt)):
            rendered.setdefault(c, []).append(rel)

    base = ""
    first = next((r["url"] for r in rows), "")
    for cand in (repo.name,):
        if first.startswith(f"/{cand}/"):
            base = f"/{cand}"

    missing, wrong, dup = [], [], []
    for r in rows:
        want = r["url"] if r["url"].startswith("/") else "/" + r["url"]
        want = want[len(base):] if base and want.startswith(base) else want
        where = rendered.get(r["code"], [])
        if not where:
            missing.append((r["code"], want))
        elif len(where) > 1:
            dup.append((r["code"], where))
        elif where[0].rstrip("/") != want.rstrip("/"):
            wrong.append((r["code"], want, where[0]))

    for c, u in missing[:25]:
        print(f"::error::{c} is locked to {u} and renders on NO page. The page "
              f"may still exist at that address — a mark that stops rendering "
              f"costs money and moves no URL, so gate A3 cannot see it.")
    if len(missing) > 25:
        print(f"::error::… and {len(missing) - 25} more missing")
    for c, w in dup[:10]:
        print(f"::error::{c} renders on {len(w)} pages ({', '.join(w[:3])}). "
              f"VG Wort counts one work per mark.")
    for c, want, got in wrong[:10]:
        print(f"::error::{c} is locked to {want} but renders at {got}")

    bad = len(missing) + len(dup) + len(wrong)
    if bad:
        print(f"\nC2 FAIL — {bad} of {len(rows)} locked mark(s) wrong",
              file=sys.stderr)
        return 1
    print(f"C2 OK — {len(rows)} locked mark(s), each rendering on exactly one "
          f"page, and on the page it is locked to")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
