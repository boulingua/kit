#!/usr/bin/env python3
"""
verify_author_meta.py — Phase-6.7 gate. Every rendered HTML page
that represents a content entry (i.e. has /index.html under a
section path, but is not a tag/list page) must contain the
canonical author string in <meta name="author">.

Hugo's Coder theme emits this from .Site.Params.author, so the
real-world failure mode is a content section configured to bypass
the default head partial. We catch that here.

Exits 1 on any miss with file-pathed ::error:: messages.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# The repo under test is an ARGUMENT, never this script's own location.
#
# These gates lived inside the repo they checked, so `Path(__file__).parent.parent`
# was that repo. Promoted into the kit it is the KIT — so the gate would have
# walked kit/static/, found nothing, and reported success about a course it
# never looked at. That is the same defect F7 removed from the generators
# (SITE = REPO.name), and it is worth restating: a shared tool must be told
# what it is operating on.
# The argument is the BUILT SITE, not the repo. Appending "public" to it —
# which these did — makes the gate unrunnable in any repo that builds
# elsewhere, and "no site found" then reads as a failure of the build
# rather than of the gate. The kit itself builds to build/site.
ARG = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
PUBLIC = ARG if (ARG / "index.html").exists() else ARG / "public"
REPO = ARG
NEEDLE = "S. Le Boulanger"

META_RE = re.compile(
    r'<meta\s+[^>]*name=["\']?author["\']?[^>]*content=["\']([^"\']*)["\']',
    re.I,
)
META_RE_REVERSE = re.compile(
    r'<meta\s+[^>]*content=["\']([^"\']*)["\'][^>]*name=["\']?author["\']?',
    re.I,
)
REDIRECT_RE = re.compile(r'<meta\s+http-equiv=["\']?refresh["\']?', re.I)
PAGINATOR_RE = re.compile(r"/page/\d+/index\.html$")

# Pages we deliberately exclude (lists / hub / tag indices).
EXCLUDE_PREFIXES = (
    "tags/",
    "categories/",
    "materials/",  # navigation, not editorial
)


def main() -> int:
    if not PUBLIC.is_dir():
        print("::error::public/ not found — run hugo first", file=sys.stderr)
        return 2

    bad: list[str] = []
    n = 0
    for html in PUBLIC.rglob("index.html"):
        rel = html.relative_to(PUBLIC).as_posix()
        # Skip Hugo paginator redirect pages (page/1/, page/2/, ...).
        if PAGINATOR_RE.search(rel):
            continue
        if rel == "index.html":
            kind = "home"
        else:
            section = rel[:-len("/index.html")]
            if any(section.startswith(p) for p in EXCLUDE_PREFIXES):
                continue
            kind = "content"

        text = html.read_text(encoding="utf-8", errors="replace")
        # Skip alias / meta-refresh redirect pages — they have no body.
        if REDIRECT_RE.search(text):
            continue
        n += 1
        m = META_RE.search(text) or META_RE_REVERSE.search(text)
        author = m.group(1) if m else ""
        if NEEDLE not in author:
            bad.append(f"{rel} ({kind}) — meta author='{author}'")

    for line in bad[:50]:
        print(f"::error::{line}")

    print(f"\nverify_author_meta: {n} pages checked; {len(bad)} violation(s).")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
