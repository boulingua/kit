"""Phase 6.1 — fail the build if rendered legal pages still contain
unfilled placeholders or TODO/FIXME markers.

Re-implements the Quarto-era `scripts/check-legal-placeholders.sh`,
retargeted at Hugo's `public/`. Loud + specific failures.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"

LEGAL_URLS = ("/impressum/", "/datenschutz/", "/haftungsausschluss/")

# Forbidden placeholder strings — any survival of these in a rendered
# legal page indicates the page was shipped before its template was
# filled in.
PLACEHOLDERS = (
    "{{CONTACT_EMAIL_HELLER}}",
    "{{CONTACT_EMAIL_LEBOULANGER}}",
    "{{SITE_DOMAIN}}",
    "{{NAME}}",
    "{{ADDRESS}}",
    "[NAME]",
    "[ADDRESS]",
    "Lorem ipsum",
    "<TODO:",
    "<FIXME:",
    "[STUB]",
    "[TBD]",
    "⟨",  # angle-bracket template placeholders, e.g. ⟨NAME⟩ — must be filled
)
# Markers that should never appear inside a legal page (case-sensitive
# to avoid false positives on the literal word "TODO list" etc., but
# we still match TODO / FIXME as standalone tokens).
MARKERS_RE = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b")


def main() -> int:
    if not PUBLIC.is_dir():
        print(f"GATE FAIL: {PUBLIC.relative_to(ROOT)} missing — "
              f"run `hugo --minify` first.", file=sys.stderr)
        return 2

    violations: list[tuple[str, str]] = []
    for url in LEGAL_URLS:
        page = PUBLIC / url.strip("/") / "index.html"
        if not page.is_file():
            violations.append((url, "page missing — has it been moved?"))
            continue
        body = page.read_text(encoding="utf-8")
        for needle in PLACEHOLDERS:
            if needle in body:
                violations.append((url, f"placeholder present: {needle}"))
        for m in MARKERS_RE.finditer(body):
            violations.append((url, f"marker present: {m.group(0)}"))

    if violations:
        print(f"GATE FAIL: {len(violations)} legal-page placeholder/marker "
              f"violation(s):", file=sys.stderr)
        for url, why in violations:
            print(f"  {url}: {why}", file=sys.stderr)
        return 1

    print(f"Legal pages clean — {len(LEGAL_URLS)} pages checked, "
          f"no placeholders, no TODO/FIXME markers.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
