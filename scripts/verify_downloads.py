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

REPO = Path(__file__).resolve().parent.parent
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


def main() -> int:
    missing: list[tuple[str, str]] = []
    units = sorted(CONTENT.glob("kurs_*/units/unit*.md"))
    if not units:
        print("no unit articles found", file=sys.stderr)
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
