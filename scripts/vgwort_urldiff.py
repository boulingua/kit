#!/usr/bin/env python3
"""Compare a built site against the committed VG Wort URL lock.

This is gate A3 in neutrality mode. It answers one question: did this change
move, or remove, a URL that carries a Zaehlmarke? A mark is keyed to its URL, so
a moved URL is a forfeited mark, and a forfeited mark is lost statutory income.

It does NOT check whether the locked URLs are the ones registered in T.O.M. —
the lock cannot know that, and says so in its own header. See ADR-0020.

Exit codes
    0  no locked URL moved or disappeared. New marked URLs are reported and
       allowed: adding a work is not orphaning one.
    1  at least one locked URL moved or vanished, and the change was not
       declared. This blocks the merge.

Declaring an intentional move: pass --allow-move OLD=NEW (repeatable), which is
the file-level equivalent of the same-commit re-key rule. The mark must be
re-registered against NEW in the same commit; this flag only records that the
move was deliberate.

Usage
    vgwort_urldiff.py <repo> <built-site-dir> [--base /prefix]
                      [--allow-move /old/=/new/ ...]
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vgwort_lock import PIXEL_RE, url_for  # noqa: E402


def read_lock(repo: Path) -> dict[str, str]:
    f = repo / "vgwort" / "url-lock-provisional.csv"
    if not f.exists():
        print(f"no lock at {f} — run vgwort_lock.py first", file=sys.stderr)
        raise SystemExit(2)
    rows = csv.DictReader(l for l in f.open(encoding="utf-8") if not l.startswith("#"))
    return {r["code"]: r["url"] for r in rows}


def scan(built: Path, base: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for page in sorted(built.rglob("index.html")):
        codes = set(PIXEL_RE.findall(page.read_text(encoding="utf-8", errors="replace")))
        if len(codes) == 1:
            out[codes.pop()] = url_for(page, built, base)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Gate A3 — VG Wort URL neutrality check.")
    ap.add_argument("repo", type=Path)
    ap.add_argument("built", type=Path)
    ap.add_argument("--base", default="")
    ap.add_argument("--allow-move", action="append", default=[], metavar="OLD=NEW")
    a = ap.parse_args()

    allowed = dict(p.split("=", 1) for p in a.allow_move)
    locked = read_lock(a.repo.resolve())
    now = scan(a.built.resolve(), a.base)

    moved, gone, added = [], [], []
    for code, old in locked.items():
        new = now.get(code)
        if new is None:
            gone.append((code, old))
        elif new != old and allowed.get(old) != new:
            moved.append((code, old, new))
    for code, url in now.items():
        if code not in locked:
            added.append((code, url))

    for code, old, new in moved:
        print(f"::error::mark {code} MOVED {old} -> {new}")
    for code, old in gone:
        print(f"::error::mark {code} VANISHED from {old} — the page no longer renders it")
    for code, url in added:
        print(f"::notice::new mark {code} at {url}")

    if moved or gone:
        print(f"\nA3 FAIL — {len(moved)} moved, {len(gone)} vanished. Each of these is a "
              f"registered work whose URL no longer matches. Re-key in the same commit "
              f"(see ADR-0015) or declare with --allow-move.", file=sys.stderr)
        return 1
    print(f"A3 OK — {len(locked)} locked marks all still on their URLs"
          + (f"; {len(added)} new" if added else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
