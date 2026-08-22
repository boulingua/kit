#!/usr/bin/env python3
"""
verify_downloads.py — walk every unit article in content/ and
verify that the .pptx, .pdf, .png and exam-PDF files its frontmatter
points at all exist on disk under static/.

Run from repo root:  python scripts/verify_downloads.py
Exit 1 if any file is missing.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

# The repo under test is an ARGUMENT, never this script's own location.
# Inside a course that was the same thing; in the kit it is the kit, and the
# gate reports success about a repo it never opened.
REPO = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else Path.cwd()
CONTENT = REPO / "content"
STATIC = REPO / "static"
FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)


SITE_PREFIX = "daf/"  # GitHub Pages project-pages path prefix; baked
                      # into frontmatter URLs to satisfy Hugo's relURL.


def static_path(url: str) -> Path:
    """Map a /<prefix>/foo URL to its static/foo path on disk.

    Frontmatter stores '/daf/materials/foo.png' so Hugo's relURL
    passes it through verbatim and the live HTML carries the right
    GitHub-Pages-prefixed path. The actual file lives at
    static/materials/foo.png — strip the leading /daf/ here.
    """
    rel = url.lstrip("/")
    if rel.startswith(SITE_PREFIX):
        rel = rel[len(SITE_PREFIX):]
    return STATIC / rel


def _has_units(repo: Path) -> bool:
    """Does this course have any unit content at all?

    The distinction these gates must draw is between "artefacts are missing for
    content that exists" — a real failure — and "there is no content yet",
    which is what every course looks like on its first commit. Failing a fresh
    scaffold teaches the author to ignore the battery before they have written
    a single unit, and a battery ignored from day one is never switched back on.
    """
    c = repo / "content"
    return c.exists() and any(
        p.suffix == ".md" and p.name not in ("_index.md",) and "/units/" in p.as_posix()
        for p in c.rglob("*.md"))


def main() -> int:
    if not _has_units(REPO):
        print('verify-downloads: no unit content yet — nothing to resolve.')
        return 0
    missing: list[tuple[str, str]] = []
    # Both bundle forms, and no course-specific section name. The glob here was
    # `kurs_*/units/unit*.md` — daf's own directory naming, and flat-only, so it
    # matched 60 files before the leaf-bundle conversion and zero after. This
    # script was promoted into the kit without being generalised, which is the
    # cost of promoting a working script rather than a general one.
    #
    # _has_units() twenty lines above already had the right rule. Two ways of
    # asking the same question in one file is how they drift apart.
    units = sorted(p for p in CONTENT.rglob("*.md")
                   if "/units/" in p.as_posix() and p.name != "_index.md")
    if not units:
        print("::error::no unit article found under any content/**/units/ path, "
              "but _has_units() said this course has units. The two disagree — "
              "that is a bug here, not an empty course.", file=sys.stderr)
        return 1

    for md in units:
        m = FM_RE.match(md.read_text(encoding="utf-8"))
        if not m:
            continue
        fm = yaml.safe_load(m.group(1)) or {}
        rel = md.relative_to(REPO).as_posix()

        slug = fm.get("unit_slug")
        nr = fm.get("unit_nr")
        level = (fm.get("cefr_level") or "").lower()
        if slug and nr is not None and level:
            base = f"unit{int(nr):02d}_{slug}"
            exam = STATIC / "downloads" / level / f"{base}_exam.pdf"
            if not exam.exists():
                missing.append((rel, str(exam.relative_to(REPO))))

        for key in ("presentation", "worksheet"):
            block = fm.get(key) or {}
            for sub in ("file", "thumbnail"):
                v = block.get(sub)
                if not v:
                    continue
                p = static_path(v)
                if not p.exists():
                    missing.append((rel, str(p.relative_to(REPO))))

    if missing:
        print(f"::error::{len(missing)} download path(s) missing on disk:")
        for src, target in missing[:50]:
            print(f"  {src} -> {target}")
        return 1
    print(f"verify-downloads: {len(units)} units · all download paths present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
