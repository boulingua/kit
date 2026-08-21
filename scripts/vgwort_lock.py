#!/usr/bin/env python3
"""Generate vgwort/url-lock-provisional.csv from a built site.

The lock records which URLs currently carry a VG Wort Zaehlmarke, so a gate can
tell whether a change is about to orphan one. It is derived from the *built*
site rather than from front matter or data/vgwort.yaml, because what ships is
what earns: the three live repos store their marks three different ways, and the
rendered page is the one place all three agree.

PROVISIONAL, and the filename says so. There is no `registered_url` column,
because that column can only be filled from a T.O.M. export and a lock that
guessed at it would teach the URL gate to defend a fact nobody checked. See
ADR-0020. When the export lands (programme SS15), this file is replaced by
vgwort/url-lock.csv with the column populated, and the gate moves from
neutrality mode to correctness mode.

Columns
    url          RelPermalink with the baseURL path stripped, always with a
                 trailing slash. This is the key the gate compares on.
    code         the 32-hex public identification code. Never a private code.
    first_seen   the date this URL/code pair entered the lock.
    content_sha  sha256 of the page's rendered main content, whitespace
                 normalised. It exists to flag that a marked page's text
                 changed enough to re-check the 1800-character floor. Editing a
                 shared template perturbs it for every page at once; that is a
                 known limitation of deriving it from the build and is why it
                 is advisory here and not a gate input.

Usage
    vgwort_lock.py <repo> <built-site-dir> [--base /prefix] [--date YYYY-MM-DD]

Relocates to bin/kit at F10; this is the standalone form so P0.8 can run before
the kit exists.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from pathlib import Path

PIXEL_RE = re.compile(r"https://vg\d+\.met\.vgwort\.de/na/([0-9a-f]{32})")
# The rendered article body. hugo-coder wraps page content in <main>; fall back
# to the whole document rather than silently recording an empty hash.
MAIN_RE = re.compile(r"<main\b[^>]*>(.*?)</main>", re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def content_sha(html: str) -> str:
    m = MAIN_RE.search(html)
    body = m.group(1) if m else html
    text = WS_RE.sub(" ", TAG_RE.sub(" ", body)).strip()
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def url_for(page: Path, root: Path, base: str) -> str:
    rel = page.relative_to(root).as_posix()
    rel = rel[: -len("index.html")] if rel.endswith("index.html") else rel
    url = "/" + rel.strip("/")
    if url != "/":
        url += "/"
    if base and url.startswith(base.rstrip("/") + "/"):
        url = url[len(base.rstrip("/")):]
    return url or "/"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Generate vgwort/url-lock-provisional.csv from a built site.")
    ap.add_argument("repo", type=Path, help="the course repo root")
    ap.add_argument("built", type=Path, help="the built site directory")
    ap.add_argument("--base", default="",
                    help="baseURL path prefix to strip, e.g. /efl/")
    ap.add_argument("--date", default="2026-08-21", help="first_seen date")
    a = ap.parse_args()
    repo, built = a.repo.resolve(), a.built.resolve()

    rows, seen_codes = [], {}
    for page in sorted(built.rglob("index.html")):
        html = page.read_text(encoding="utf-8", errors="replace")
        codes = set(PIXEL_RE.findall(html))
        if not codes:
            continue
        if len(codes) > 1:
            print(f"FAIL {page}: {len(codes)} distinct codes on one page", file=sys.stderr)
            return 1
        code = codes.pop()
        url = url_for(page, built, a.base)
        if code in seen_codes:
            print(f"FAIL duplicate code {code}: {seen_codes[code]} and {url}", file=sys.stderr)
            return 1
        seen_codes[code] = url
        rows.append({"url": url, "code": code, "first_seen": a.date,
                     "content_sha": content_sha(html)})

    rows.sort(key=lambda r: r["url"])
    out = repo / "vgwort" / "url-lock-provisional.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        fh.write("# VG Wort URL lock - PROVISIONAL. Derived from the built site, not from a\n")
        fh.write("# T.O.M. export: it records where a mark RENDERS, never where it EARNS.\n")
        fh.write("# No registered_url column by design - see ADR-0020. Gate A3 reads this in\n")
        fh.write("# neutrality mode (does a change move a locked URL). Replaced by\n")
        fh.write("# url-lock.csv at programme SS15, after which A3 checks correctness.\n")
        w = csv.DictWriter(fh, fieldnames=["url", "code", "first_seen", "content_sha"])
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} rows -> {out.relative_to(repo)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
