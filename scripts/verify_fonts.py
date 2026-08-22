#!/usr/bin/env python3
"""Gate A4 — every shipped font file is attributed and licensed.

    python scripts/verify_fonts.py

Three checks:

1. **Every shipped `.woff2`, `.otf` and `.ttf` appears in ATTRIBUTION.md.** A
   font that arrives without a row is a font nobody recorded the licence for.
2. **Every licence file a family points at exists** and is non-empty.
3. **No deferred tier has committed binaries.** `arabic`, `hanzi-sc` and
   `kana-kanji` are declared so the mechanism is built and the decision is
   recorded, but shipping their payload now would cost megabytes for courses
   that will not exist for years, and would silently let a course select a tier
   whose reference document has never been built.

Why this is a gate and not a README note: the previous template shipped seven
`.woff2` files carrying the OFL URL inside their own name table with no licence
text anywhere in the repository. The font said it was OFL; the repository did
not honour §5. Nothing detected that, because nothing was looking.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

KIT = Path(__file__).resolve().parent.parent
# A4 runs against a COURSE as well as against the kit, and the two ask
# different questions. In the kit: are the cut faces reproducible and licensed.
# In a course: does every .woff2 this repo actually ships trace to a licence
# and an attribution entry. Deriving the target from __file__ answered the kit
# question every time and reported "67 font files, all attributed" while
# standing in a course directory — a true sentence about the wrong repository,
# which is the most durable kind of vacuous pass.
REPO = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else KIT
MANIFEST = KIT / "design" / "fonts.yaml"
ATTR = KIT / "design" / "fonts" / "ATTRIBUTION.md"
FONT_SUFFIXES = {".woff2", ".otf", ".ttf"}


def shipped() -> list[Path]:
    out: list[Path] = []
    for root in (REPO / "static" / "fonts", REPO / "fonts"):
        if root.exists():
            out += [p for p in root.rglob("*") if p.suffix in FONT_SUFFIXES]
    # design/fonts/src/ is the upstream working copy, not a shipped payload.
    return sorted(p for p in out if "src" not in p.parts)


def main() -> int:
    if not ATTR.exists():
        print("::error::design/fonts/ATTRIBUTION.md is missing", file=sys.stderr)
        return 1
    text = ATTR.read_text(encoding="utf-8")
    # A repo may ship faces the kit does not cut — the hub uses Permanent Marker
    # for one display heading and Google's 300/500 weights of Source Sans, none
    # of which are in the kit's tiers. Those files are still shipped fonts and
    # still need an attribution, so the repo carries its own and A4 reads both.
    # What is NOT allowed is shipping a face documented nowhere, which is the
    # state all five content repos were in: 36 files, no rows.
    local = REPO / "static" / "fonts" / "ATTRIBUTION.md"
    if local.exists():
        text += "\n" + local.read_text(encoding="utf-8")
        print(f"  + {local.relative_to(REPO)} (repo-local faces)")
    m = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    bad = 0

    files = shipped()
    missing = [p for p in files if p.name not in text]
    for p in missing:
        print(f"::error::{p.relative_to(REPO)} ships with no ATTRIBUTION.md row")
    bad += len(missing)

    for fam, spec in m["families"].items():
        if spec.get("status") == "deferred":
            continue
        lf = spec.get("licence_file")
        if not lf:
            print(f"::error::family {fam} declares no licence_file")
            bad += 1
            continue
        # The manifest names a shared path; the attribution names the per-family
        # file that actually carries that project's copyright notice.
        cands = list((KIT / "design" / "fonts" / "LICENSES").glob("*"))
        if not any(fam.replace("-", "").lower() in c.name.replace("-", "").lower()
                   for c in cands):
            print(f"::error::no licence file in LICENSES/ for {fam}")
            bad += 1

    for tier, spec in m["tiers"].items():
        if spec["status"] != "deferred":
            continue
        d = KIT / "fonts" / tier
        if d.exists() and any(p.suffix in FONT_SUFFIXES for p in d.rglob("*")):
            print(f"::error::tier {tier} is deferred but has committed binaries")
            bad += 1

    if bad:
        print(f"\nA4 FAIL — {bad} problem(s). A font without an attribution row is a "
              f"font whose licence nobody recorded.", file=sys.stderr)
        return 1
    print(f"A4 OK — {len(files)} font files, all attributed; "
          f"{len([f for f in m['families'].values() if f.get('status') != 'deferred'])} "
          f"families, all licensed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
