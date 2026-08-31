#!/usr/bin/env python3
"""A20/G1 — nothing published may disappear without somebody saying so.

    verify_url_set.py scan BUILT --out FILE
    verify_url_set.py --diff BASE NOW [--allow-removed PATH ...]

**The failure this exists for, measured rather than imagined.** Deleting
`daf/layouts/materials/list.html` removes five fingerprinted JavaScript bundles
from the published tree — `js/network/{filters,list,main,search,vendor}.<sha>.js`
— and the organisation reports:

    hugo --minify --gc --panicOnWarning     exit 0, 145 of 145 pages, no WARN
    kit urldiff daf                         A3 OK — 68 locked marks still on their URLs
    kit check daf                           26 gate(s) run, 0 warning(s), 0 blocked

Every one of those is telling the truth about the question it asks. A3 defends
789 of the org's 2,076 published files and asks whether a *mark* moved; the
battery asks whether the *pages* are correct. Neither asks whether the site
still contains what it contained yesterday, and eleven of the fourteen
harmonisation steps delete a template.

So this compares the published FILE SET, not the HTML and not the marks:

    removed   a file that was published and is not          -> FAIL
    moved     the same bytes at a different path            -> FAIL
    added     a new file                                    -> pass, and counted

Additions pass because a migration that ships a stylesheet is normal and a
migration that silently drops a script bundle is not. The asymmetry is the
whole design.

**Fingerprints are normalised, or every build would be a rename.** Hugo emits
`custom.min.<sha256>.css`, and the hash changes whenever the content does. A
fingerprint change at the same logical path is reported as CHANGED and passes;
what fails is the logical path going away. The hash is content-derived, so two
builds of one tree give an identical set — that determinism is what makes this
a gate rather than a diff.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

#: `name.min.<32-or-40-or-64 hex>.ext` — Hugo's fingerprint, and integrity
#: hashes that reach filenames. Collapsed so a content change is not a rename.
FINGERPRINT = re.compile(r"\.([0-9a-f]{32}|[0-9a-f]{40}|[0-9a-f]{64})(?=\.[^.]+$)")


def logical(rel: str) -> str:
    return FINGERPRINT.sub("", rel)


def scan(built: Path) -> dict[str, tuple[str, int]]:
    """logical path -> (real path, size). Symlinks are resolved as files; the
    published tree has none today and a future one would still be content."""
    out: dict[str, tuple[str, int]] = {}
    for p in sorted(built.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(built).as_posix()
        out[logical(rel)] = (rel, p.stat().st_size)
    return out


def write(manifest: dict[str, tuple[str, int]], path: Path) -> None:
    path.write_text(
        "".join(f"{k}\t{v[0]}\t{v[1]}\n" for k, v in sorted(manifest.items())),
        encoding="utf-8")


def read(path: Path) -> dict[str, tuple[str, int]]:
    out: dict[str, tuple[str, int]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        out[parts[0]] = (parts[1], int(parts[2])) if len(parts) > 2 else (parts[0], -1)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("built", nargs="?")
    ap.add_argument("--out")
    ap.add_argument("--diff", nargs=2, metavar=("BASE", "NOW"))
    ap.add_argument("--allow-removed", action="append", default=[],
                    help="a logical path this change deliberately retires. Every "
                         "one has to be named; a wildcard is not accepted, because "
                         "the point is that somebody looked at it.")
    a = ap.parse_args()

    if a.diff:
        base, now = read(Path(a.diff[0])), read(Path(a.diff[1]))
        allowed = set(a.allow_removed)
        gone = sorted(set(base) - set(now))
        new = sorted(set(now) - set(base))
        # A file whose bytes are unchanged but whose logical path moved. Matched
        # on size, which is coarse and is meant to be: it exists to give a
        # rename a better message than "one removed, one added".
        by_size: dict[int, list[str]] = {}
        for k in new:
            by_size.setdefault(now[k][1], []).append(k)
        moved, removed = [], []
        for k in gone:
            cand = [c for c in by_size.get(base[k][1], [])
                    if Path(c).name == Path(k).name]
            (moved.append((k, cand[0])) if cand else removed.append(k))
        undeclared = [k for k in removed if k not in allowed]
        declared = [k for k in removed if k in allowed]
        changed = sum(1 for k in set(base) & set(now)
                      if base[k][1] != now[k][1] or base[k][0] != now[k][0])

        for k, to in moved:
            print(f"::error::MOVED  {k}  ->  {to}")
        for k in undeclared:
            print(f"::error::REMOVED  {k}")
        for k in declared:
            print(f"::notice::retired (declared)  {k}")
        if moved or undeclared:
            print(f"\nURL SET FAIL — {len(undeclared)} removed, {len(moved)} moved. "
                  f"A published file that disappears without being named is the "
                  f"failure no other gate in this battery can see.", file=sys.stderr)
            return 1
        print(f"URL SET OK — {len(now)} files, 0 removed, {len(moved)} moved, "
              f"{len(new)} added, {changed} changed"
              + (f", {len(declared)} retired (declared)" if declared else ""))
        return 0

    if not a.built:
        print("::error::give a built site to scan, or --diff BASE NOW", file=sys.stderr)
        return 2
    built = Path(a.built).resolve()
    if not built.is_dir():
        print(f"::error::{built} does not exist — build first", file=sys.stderr)
        return 2
    m = scan(built)
    if not m:
        print(f"::error::{built} holds no files. An empty set would compare "
              f"equal to another empty set, which is the vacuous pass this "
              f"whole battery exists to remove.", file=sys.stderr)
        return 2
    if a.out:
        write(m, Path(a.out))
    print(f"url set — {len(m)} published file(s) under {built}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
