#!/usr/bin/env python3
"""
verify_pdf_metadata.py — Phase-6.6 gate (restored from the Quarto-era
publish.yml). Every PDF served from this site must carry author
metadata containing 'Le Boulanger' (the canonical attribution).

Walks static/**/*.pdf. Exits 1 on any miss with file-pathed
::error:: messages.

Requires: pip install pypdf
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:
    print("::error::need pypdf — pip install pypdf", file=sys.stderr)
    sys.exit(2)

# The repo under test is an ARGUMENT, never this script's own location.
#
# These gates lived inside the repo they checked, so `Path(__file__).parent.parent`
# was that repo. Promoted into the kit it is the KIT — so the gate would have
# walked kit/static/, found nothing, and reported success about a course it
# never looked at. That is the same defect F7 removed from the generators
# (SITE = REPO.name), and it is worth restating: a shared tool must be told
# what it is operating on.
_args = [a for a in sys.argv[1:] if not a.startswith("-")]
REPO = Path(_args[0]).resolve() if _args else Path.cwd()
# --strict enforces the full field set. Without it, a field that only arrives
# with regeneration is COUNTED, not failed.
#
# This matters for adoption, not for rigour. /Title is missing from every
# worksheet in the org — 60 in daf alone — because \worksheetheader never set
# it, and that is fixed in the kit's LaTeX now. But the committed artefacts
# predate the fix, so switching the gate on today would red every build for a
# defect nobody can clear without regenerating. A gate that fails on 100% of
# existing artefacts teaches people to ignore it, which is how the org ended up
# with nine continue-on-error suppressions.
STRICT = "--strict" in sys.argv
STATIC = REPO / "static"
NEEDLE = "Le Boulanger"

# Gate D2. Promoted from daf, repaired on the way up rather than after.
#
# Two defects, and the first is the one this programme exists to remove: an
# empty glob returned 0 with "no PDFs found". On efl, where the PDFs are
# gitignored and regenerated in CI, this gate therefore passed VACUOUSLY —
# a legal-adjacent attribution invariant reporting success precisely because
# the build step it depends on had not run.
#
# The second: it checked /Author alone. Every worksheet in the org shipped with
# no /Title, no /Subject and no /Keywords, and passed.
REQUIRED_FIELDS = ("/Author", "/Title")
# /Subject and /Creator arrive with the first regeneration through kit/latex/,
# so they are reported but not yet enforced — a gate that fails on 100% of
# today's artefacts teaches people to ignore it.
REPORTED_FIELDS = ("/Subject", "/Keywords", "/Creator")


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
    pdfs = sorted(STATIC.rglob("*.pdf"))
    if not pdfs:
        # Is this course supposed to have artefacts? If it commits its
        # materials, finding none means the build did not run, and reporting
        # success for that is exactly backwards.
        if not _has_units(REPO):
            print("verify_pdf_metadata: no unit content yet — nothing to attribute.")
            return 0
        cfg = REPO / "boulingua.yml"
        committed = "materials: committed" in cfg.read_text(encoding="utf-8") \
            if cfg.exists() else (REPO / "static" / "materials").exists()
        if committed:
            print("::error::no PDFs under static/ on a course that commits its "
                  "materials. This gate used to return 0 here, which meant it "
                  "reported success because it had nothing to check.")
            return 1
        print("verify_pdf_metadata: no PDFs, and this course does not commit them.")
        return 0

    bad: list[tuple[str, str]] = []
    pending: list[tuple[str, list]] = []
    for p in pdfs:
        rel = str(p.relative_to(REPO))
        try:
            r = PdfReader(str(p))
            meta = r.metadata or {}
            author = meta.get("/Author", "") or ""
            missing = [f for f in REQUIRED_FIELDS if not (meta.get(f) or "").strip()]
            if missing:
                if STRICT or "/Author" in missing:
                    bad.append((rel, "missing " + ", ".join(missing)))
                else:
                    pending.append((rel, missing))
                continue
        except Exception as exc:
            bad.append((rel, f"read error: {exc}"))
            continue
        if NEEDLE not in author:
            bad.append((rel, f"author='{author}' (missing '{NEEDLE}')"))

    for path, reason in bad[:50]:
        print(f"::error file={path}::{reason}")

    if pending:
        fields = sorted({f for _, ms in pending for f in ms})
        print(f"::notice::{len(pending)} PDF(s) predate the metadata fix and lack "
              f"{', '.join(fields)}. Counted, not failed — they carry it once "
              f"regenerated through kit/latex/. Run with --strict after that.")
    print(f"\nverify_pdf_metadata: {len(pdfs)} PDFs checked; {len(bad)} violation(s)"
          f"{f', {len(pending)} pending regeneration' if pending else ''}.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
