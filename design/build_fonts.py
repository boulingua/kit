#!/usr/bin/env python3
"""Subset the upstream faces into the web and print payloads.

    python design/build_fonts.py                build both payloads
    python design/build_fonts.py --check        verify without writing
    python design/build_fonts.py --tier greek   one tier only

Reads design/fonts.yaml. Writes:

    static/fonts/<family>-<weight><style>.<tier>.woff2   web payload
    static/css/fonts.css                                  generated @font-face
    fonts/<tier>/*.otf|ttf                                print payload

Requires fontTools with brotli (`pip install 'fonttools[woff]'`). This is a
local authoring dependency like TeX Live, never a deploy-path one: the output
is committed and CI only verifies it.

WHAT THIS REPLACES. Seven .woff2 files fetched from a Google Fonts helper with
the `latin,latin-ext` ranges: 781 codepoints, no Greek, no Cyrillic, a mangled
name table declaring every weight `Source Sans 3 ExtraLight`, and no licence
text anywhere in the repo despite the OFL requiring it. Six planned courses
needed glyphs those files do not contain.

THE TWO RULES THAT MAKE THIS SAFE

1. Ranges come from fonts.yaml as codepoints. Google's `cyrillic` range stops
   at U+045F and Ukrainian ґ is U+0490, so a name-based subset drops a letter
   that is present in the face. Names are simply not available here.

2. No-drop on OpenType features. The retention set is computed per face as
   (the face's own features) ∩ (floor ∪ everything it has), and the produced
   subset is re-opened and compared. A dropped joining feature does not degrade
   Arabic, it breaks it, so this fails the build naming the tag rather than
   warning.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

KIT = Path(__file__).resolve().parent.parent
SRC = KIT / "design" / "fonts" / "src"
MANIFEST = KIT / "design" / "fonts.yaml"
WEB_FONTS = KIT / "static" / "fonts"
WEB_CSS = KIT / "static" / "css" / "fonts.css"
PRINT = KIT / "fonts"


def load() -> dict:
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))


def find_src(filename: str) -> Path | None:
    hits = sorted(SRC.rglob(filename))
    # Prefer an unhinted/full build where a release ships several.
    for h in hits:
        if "full" in h.parts or "OTF" in h.parts:
            return h
    return hits[0] if hits else None


def face_features(path: Path) -> set[str]:
    from fontTools.ttLib import TTFont
    f = TTFont(path, lazy=True)
    tags: set[str] = set()
    for tbl in ("GSUB", "GPOS"):
        if tbl in f:
            tags |= {r.FeatureTag for r in f[tbl].table.FeatureList.FeatureRecord}
    return tags


def retention(m: dict, present: set[str], tier: str) -> set[str]:
    floor = set(m["features"]["required_floor"]["gsub"]) | set(m["features"]["required_floor"]["gpos"])
    if tier == "arabic":
        floor |= set(m["features"]["required_floor_arabic"]["gsub"])
    # Keep everything the face actually has that is in the floor, plus the
    # typographic set we rely on. Never demand a tag the face lacks: `isol` is
    # the unsubstituted default form and `curs` is GPOS, and IBM Plex Sans
    # Arabic has neither — a fixed list would reject the chosen face.
    useful = {"aalt", "salt", "ss01", "ss02", "ss03", "ss04", "ss05", "ss06",
              "onum", "lnum", "pnum", "tnum", "frac", "sups", "subs", "zero",
              "dlig", "dnom", "numr", "ordn", "case", "cv01", "cv02"}
    return (floor | useful) & present


def subset(src: Path, out: Path, ranges: list[str], keep: set[str],
           flavour: str | None) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    feats = "*" if keep == {"*"} else ",".join(sorted(keep))
    cmd = [sys.executable, "-m", "fontTools.subset", str(src),
           f"--output-file={out}",
           "--unicodes=" + ",".join(r.replace("U+", "") for r in ranges),
           f"--layout-features={feats}",
           "--no-hinting", "--desubroutinize",
           "--name-IDs=*", "--name-legacy", "--notdef-outline",
           "--drop-tables+=DSIG"]
    if flavour:
        cmd += [f"--flavor={flavour}", "--with-zopfli"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"subset failed for {src.name}: {r.stderr.strip()[:400]}")


def verify_no_drop(src: Path, out: Path, ranges: list[str], tmp: Path,
                   floor: set[str]) -> list[str]:
    """Name any feature OUR configuration dropped.

    The naive check — compare the subset's features against the source face's —
    is wrong, and wrong in a way that would have made this gate useless. When a
    face is cut to one script, features whose input glyphs fall outside that
    range are legitimately removed: `frac` needs digits and a slash, so it
    cannot survive a Greek-only subset and its absence means nothing.

    So the baseline is not the source face. It is the same subset taken with
    every feature retained. Anything present there and missing from ours was
    dropped by our choice, which is the only kind of loss worth failing on.
    That is also what keeps the rule from going stale when a face is upgraded:
    it never names a tag."""
    ref = tmp / ("ref-" + out.name.replace(".woff2", ".ttf"))
    subset(src, ref, ranges, {"*"}, None)
    survivable = face_features(ref)
    # Only the FLOOR is protected. Excluding smcp, ss07+ and the cv* character
    # variants is curation — a deliberate decision that costs bytes we do not
    # spend — and a rule that cannot tell curation from breakage fails on the
    # wrong thing and gets switched off. What must never be lost is the set
    # that changes whether text is *correct*: composition, localisation,
    # contextual alternates, ligatures, kerning, mark attachment, and for
    # Arabic the joining forms.
    return sorted((survivable & floor) - face_features(out))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="verify, do not write")
    ap.add_argument("--tier", default=None, help="build one tier only")
    a = ap.parse_args()

    m = load()
    shipped = {name: t for name, t in m["tiers"].items()
               if t["status"] == "shipped" and (a.tier is None or name == a.tier)}
    if not shipped:
        print(f"no shipped tier matches {a.tier!r}", file=sys.stderr)
        return 2

    # A family without a measured ratio may not ship. 100% is exactly the value
    # that produces the "second design" the ratio exists to prevent, so an
    # unmeasured family is a build failure, never a default.
    for fam, spec in m["families"].items():
        if spec.get("status") == "deferred":
            continue
        if spec.get("x_height_ratio") is None:
            print(f"::error::family {fam} ships but has no measured x_height_ratio",
                  file=sys.stderr)
            return 1

    faces_out: list[dict] = []
    problems = 0
    tmp = Path(tempfile.mkdtemp(prefix="blgfonts-"))
    try:
        for tier, tspec in shipped.items():
            ranges = tspec["ranges"]
            for fam, spec in m["families"].items():
                if spec.get("status") == "deferred" or tier not in spec.get("tiers", []):
                    continue
                for face in spec["faces"]:
                    src = find_src(face["file"])
                    if not src:
                        print(f"::error::{face['file']} not in design/fonts/src/", file=sys.stderr)
                        problems += 1
                        continue
                    present = face_features(src)
                    keep = retention(m, present, tier)
                    floor = set(m["features"]["required_floor"]["gsub"]) | \
                            set(m["features"]["required_floor"]["gpos"])
                    if tier == "arabic":
                        floor |= set(m["features"]["required_floor_arabic"]["gsub"])
                    stem = f"{fam}-{face['weight']}{'i' if face['style'] == 'italic' else ''}"
                    woff = (tmp if a.check else WEB_FONTS) / f"{stem}.{tier}.woff2"
                    subset(src, woff, ranges, keep, "woff2")
                    dropped = verify_no_drop(src, woff, ranges, tmp, floor)
                    if dropped:
                        print(f"::error::{woff.name} dropped OpenType features: "
                              f"{', '.join(dropped)}", file=sys.stderr)
                        problems += 1
                    faces_out.append(dict(family=fam, spec=spec, face=face,
                                          tier=tier, file=woff.name,
                                          size=woff.stat().st_size))
                    if not a.check:
                        # Print takes the FULL face, not a subset: XeLaTeX has no
                        # unicode-range, and a deck that needs one Greek word in an
                        # otherwise Latin course must still find the glyph.
                        dst = PRINT / tier / src.name
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, dst)
        if not a.check:
            WEB_CSS.parent.mkdir(parents=True, exist_ok=True)
            WEB_CSS.write_text(emit_css(m, faces_out), encoding="utf-8")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    total = sum(f["size"] for f in faces_out)
    print(f"  {len(faces_out)} web faces, {total // 1024} KB total")
    for tier in sorted({f['tier'] for f in faces_out}):
        n = [f for f in faces_out if f["tier"] == tier]
        print(f"    {tier:11s} {len(n):2d} faces  {sum(x['size'] for x in n) // 1024:4d} KB")
    if problems:
        print(f"\nFAIL — {problems} problem(s)", file=sys.stderr)
        return 1
    print("  no-drop rule satisfied on every face")
    return 0


def emit_css(m: dict, faces: list[dict]) -> str:
    w = m["web"]
    out = [
        "/* GENERATED by design/build_fonts.py from design/fonts.yaml. Do not edit. */",
        "/* Six hand-copied variants of this file existed across the org, three of",
        "   them with different content and none carrying a single unicode-range. */",
        "",
        f"html {{ font-synthesis: {w['font_synthesis']}; }}",
        "/* Global, so a missing italic is visible rather than faked. A synthesised",
        "   oblique of Cyrillic is not ugly, it is the wrong letterforms. */",
        "",
    ]
    for f in sorted(faces, key=lambda x: (x["family"], x["face"]["weight"],
                                          x["face"]["style"], x["tier"])):
        spec, face = f["spec"], f["face"]
        out += [
            "@font-face {",
            f"  font-family: '{f['family']}';",
            f"  src: url('../fonts/{f['file']}') format('woff2');",
            f"  font-weight: {face['weight']};",
            f"  font-style: {face['style']};",
            f"  font-display: {w['font_display']};",
        ]
        if spec["size_adjust"] != 100.0:
            out.append(f"  size-adjust: {spec['size_adjust']}%;"
                       f"  /* x-height {spec['x_height_ratio']}x Source Sans 3 */")
        rngs = spec.get("fallback_ranges") or m["tiers"][f["tier"]]["ranges"]
        out.append("  unicode-range: " + ", ".join(rngs) + ";")
        out += ["}", ""]
    return "\n".join(out)


if __name__ == "__main__":
    raise SystemExit(main())
