"""VG Wort Mindestumfang coverage warning.

Walks every content page that LIKELY qualifies for VG Wort
registration (long-form editorial pages: unit pages, exam wrappers,
course indexes, schedules, appendices, top-level prose pages — but
NOT the home page, materials hub, or other navigation surfaces) and
warns when prose >= 1800 characters has no entry in data/vgwort.yaml.

Per the brief this is a build WARNING, not a hard fail — Zählmarken
are registered async via the VG Wort T.O.M. portal, and surfacing
unregistered long-form content lets the author trigger that flow.

Run after `hugo --minify`. Reads `public/**/*.html` so the prose
count is post-render (no shortcode/markup noise).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
DATA = ROOT / "data" / "vgwort.yaml"

THRESHOLD = 1800

# Pages that are navigation, not editorial — skip even if long.
SKIP_PREFIXES = (
    "/",                # homepage exact
    "/materials/",
    "/track-e/", "/track-gm/",  # track parents (no _index page anyway)
)
SKIP_EXACT = {
    "/",
    "/materials/",
    "/materials/presentations/",
    "/materials/worksheets/",
    "/impressum/",
    "/datenschutz/",
    "/haftungsausschluss/",
}

PROSE_RE = re.compile(r"<article\b[^>]*>(.*?)</article>", re.DOTALL | re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>", re.DOTALL)


PAGINATOR_RE = re.compile(r"/page/\d+/$")


def page_url_from_path(p: Path) -> str:
    rel = p.relative_to(PUBLIC).as_posix()
    if rel.endswith("/index.html"):
        return "/" + rel.removesuffix("index.html")
    return "/" + rel


def is_paginator(url: str) -> bool:
    return bool(PAGINATOR_RE.search(url))


def article_chars(html: str) -> int:
    m = PROSE_RE.search(html)
    body = m.group(1) if m else html
    text = TAG_RE.sub(" ", body)
    text = re.sub(r"\s+", " ", text).strip()
    return len(text)


def main() -> int:
    if not DATA.is_file():
        print(f"data/vgwort.yaml missing — VG Wort partial will render "
              f"nothing. Re-run _scripts/migrate_vgwort_to_data.py.",
              file=sys.stderr)
        return 1

    entries = yaml.safe_load(DATA.read_text(encoding="utf-8")) or []
    registered = {e["url"] for e in entries}

    over_threshold_unregistered: list[tuple[str, int]] = []
    long_pages = 0
    for html_file in PUBLIC.rglob("*.html"):
        # Skip alias-redirects (1-line meta refresh files).
        head = html_file.read_text(encoding="utf-8", errors="ignore")[:600]
        if 'http-equiv="refresh"' in head or "http-equiv=refresh" in head:
            continue
        url = page_url_from_path(html_file)
        if url in SKIP_EXACT or is_paginator(url):
            continue
        full = html_file.read_text(encoding="utf-8", errors="ignore")
        n = article_chars(full)
        if n < THRESHOLD:
            continue
        long_pages += 1
        if url not in registered:
            over_threshold_unregistered.append((url, n))

    print(f"Pages over {THRESHOLD}-char Mindestumfang: {long_pages}")
    print(f"  registered: {long_pages - len(over_threshold_unregistered)}")
    print(f"  unregistered: {len(over_threshold_unregistered)}")
    if over_threshold_unregistered:
        print("\nWARN: long-form pages without VG Wort Zählmarken:")
        for url, n in sorted(over_threshold_unregistered)[:30]:
            print(f"  {url} ({n} chars)")
        if len(over_threshold_unregistered) > 30:
            print(f"  …and {len(over_threshold_unregistered) - 30} more")
        print("\nRegister via VG Wort T.O.M. and re-run "
              "_scripts/migrate_vgwort_to_data.py once the public_id is "
              "added to vgwort-manifest.csv.")
    return 0  # warning, not a hard fail


if __name__ == "__main__":
    raise SystemExit(main())
