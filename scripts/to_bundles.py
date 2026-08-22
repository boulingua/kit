#!/usr/bin/env python3
"""Flat page -> leaf bundle, with the URL proof built into the operation.

    to_bundles.py REPO --plan      show what would move
    to_bundles.py REPO --apply     move it, and prove nothing moved with it

`content/a/b.md` and `content/a/b/index.md` render at the same URL, so this
conversion is URL-neutral. That sentence is true and it is not sufficient. It
is true of Hugo in general; it is not automatically true of a particular repo,
where a `slug:`, a `url:`, a permalink pattern, an existing directory of the
same name or two files normalising to one bundle can each break it. Every one
of those is a silent break — the build succeeds and a page simply lives
somewhere else.

For a repo carrying registered VG Wort marks that is not a bug, it is lost
income that nobody notices for a quarter. So this does not argue that the
conversion is neutral. It MEASURES it:

    build  ->  snapshot every RelPermalink  ->  move  ->  rebuild  ->  diff

and if the two URL sets differ by so much as one entry it puts every file back
and exits non-zero. The proof is the operation. An implementer cannot skip it
because there is no code path that does the move without it.

`_index.md` is never converted. A branch bundle is already a directory form and
`content/a/_index.md` is not the same page as `content/a/index.md`.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HUGO = os.path.expanduser("~/.local/bin/hugo")


def hugo_urls(repo: Path) -> set[str]:
    """Every RelPermalink the repo renders, from a throwaway build."""
    out = Path(tempfile.mkdtemp(prefix="blgurl-"))
    r = subprocess.run(
        [HUGO if Path(HUGO).exists() else "hugo",
         "--destination", str(out), "--baseURL", "/", "--gc"],
        cwd=repo, capture_output=True, text=True)
    if r.returncode:
        shutil.rmtree(out, ignore_errors=True)
        raise SystemExit(f"hugo failed:\n{r.stdout}\n{r.stderr}")
    urls = set()
    for p in out.rglob("index.html"):
        head = p.read_text(encoding="utf-8", errors="replace")[:1200]
        # Alias stubs are meta-refresh pages Hugo writes for old URLs. They are
        # real URLs and must be compared too — an alias that stops rendering is
        # a reader's dead link, even though it carries no pixel.
        rel = "/" if p.parent == out else "/" + p.parent.relative_to(out).as_posix() + "/"
        urls.add(rel + ("  [alias]" if 'http-equiv="refresh"' in head else ""))
    shutil.rmtree(out, ignore_errors=True)
    return urls


def plan(repo: Path) -> list[tuple[Path, Path]]:
    moves = []
    for md in sorted((repo / "content").rglob("*.md")):
        if md.name in ("index.md", "_index.md"):
            continue
        dest_dir = md.parent / md.stem
        moves.append((md, dest_dir / "index.md"))
    return moves


def collisions(moves: list[tuple[Path, Path]]) -> list[str]:
    bad = []
    seen: dict[Path, Path] = {}
    for src, dst in moves:
        if dst.parent.exists():
            bad.append(f"{src}: {dst.parent} already exists — a page and a "
                       f"section share a name, and the move would merge them")
        if dst in seen:
            bad.append(f"{src} and {seen[dst]} both become {dst}")
        seen[dst] = src
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("repo", type=Path)
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--only", default=None,
                    help="restrict to paths containing this substring, e.g. /units/")
    a = ap.parse_args()
    repo = a.repo.resolve()

    moves = plan(repo)
    if a.only:
        moves = [m for m in moves if a.only in m[0].as_posix()]

    bad = collisions(moves)
    for b in bad:
        print(f"::error::{b}")
    if bad:
        print(f"\nto_bundles FAIL — {len(bad)} collision(s), nothing moved", file=sys.stderr)
        return 1

    if not a.apply:
        for src, dst in moves:
            print(f"  {src.relative_to(repo)}  ->  {dst.relative_to(repo)}")
        print(f"\n{len(moves)} file(s) would move; run with --apply to move and prove")
        return 0

    print(f"  before: building {repo.name} to snapshot its URL set")
    before = hugo_urls(repo)
    print(f"  before: {len(before)} URL(s)")

    done: list[tuple[Path, Path]] = []
    try:
        for src, dst in moves:
            dst.parent.mkdir(parents=True, exist_ok=False)
            # git mv where possible so history follows the file; the fallback
            # matters for a repo not yet under git, and for a dry run in /tmp.
            r = subprocess.run(["git", "mv", str(src), str(dst)],
                               cwd=repo, capture_output=True, text=True)
            if r.returncode:
                src.rename(dst)
            done.append((src, dst))
        print(f"  moved {len(done)} file(s)")

        after = hugo_urls(repo)
        gone, new = sorted(before - after), sorted(after - before)
        if gone or new:
            for g in gone[:20]:
                print(f"::error::URL DISAPPEARED: {g}")
            for n in new[:20]:
                print(f"::error::URL APPEARED: {n}")
            raise RuntimeError(f"{len(gone)} lost, {len(new)} gained")
    except Exception as e:
        print(f"\n::error::{e}\n  reverting {len(done)} move(s)", file=sys.stderr)
        for src, dst in reversed(done):
            r = subprocess.run(["git", "mv", str(dst), str(src)],
                               cwd=repo, capture_output=True, text=True)
            if r.returncode:
                dst.rename(src)
            try:
                dst.parent.rmdir()
            except OSError:
                pass
        print("  reverted. Nothing moved.", file=sys.stderr)
        return 1

    print(f"  after:  {len(after)} URL(s)")
    print(f"\nto_bundles OK — {len(done)} file(s) converted, "
          f"URL set identical ({len(before)} URLs, 0 changed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
