#!/usr/bin/env python3
"""Prove the no-drop rule fails when a load-bearing feature is stripped.

    python design/test_no_drop.py

This exists because a gate nobody has seen fail is not a gate. Three separate
checks in this organisation turned out to be incapable of failing — a
conformance script that audited its own repo and exited 0 whatever the course
contained, a VG Wort verifier that short-circuited on an empty manifest with
"passing trivially", and a PDF attribution check that grepped /Author while
every worksheet shipped with no /Title. Each was cited as evidence that
something was fine.

The rule under test protects the OpenType features that decide whether text is
*correct* rather than merely pretty: composition, localisation, contextual
alternates, ligatures, kerning and mark attachment, plus the Arabic joining
forms. Dropping `init`/`medi`/`fina` does not make Arabic look worse; it makes
it stop joining, which is the difference between typography and a bug.

Arabic ships at wave 5 (ADR-0018), so the proof runs against a shipped face:
subset Source Sans 3 to Cyrillic while deliberately withholding `kern` and
`mark`, and assert the rule names exactly those two.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_fonts import face_features, find_src, load, subset, verify_no_drop  # noqa: E402


def main() -> int:
    m = load()
    src = find_src("SourceSans3-Regular.otf")
    if not src:
        print("SourceSans3-Regular.otf missing from design/fonts/src/", file=sys.stderr)
        return 2

    ranges = m["tiers"]["cyrillic"]["ranges"]
    floor = set(m["features"]["required_floor"]["gsub"]) | \
            set(m["features"]["required_floor"]["gpos"])
    tmp = Path(tempfile.mkdtemp(prefix="blgtest-"))
    failures = 0

    # 1. Honest build: keep everything the floor asks for that the face has.
    good = tmp / "good.woff2"
    subset(src, good, ranges, floor & face_features(src), "woff2")
    dropped = verify_no_drop(src, good, ranges, tmp, floor)
    if dropped:
        print(f"  FAIL  an honest build reported drops: {dropped}")
        failures += 1
    else:
        print("  ok    honest build reports no drops")

    # 2. Sabotaged build: withhold floor features that are genuinely survivable
    # HERE. Not every floor feature applies to every script — Source Sans 3 has
    # no mark-attachment lookups reachable from a Cyrillic-only subset, so
    # `mark` cannot be dropped from one and the rule is right to stay silent
    # about it. Compute the survivable floor rather than naming tags, so this
    # test does not go stale when a face is upgraded.
    ref = tmp / "ref-probe.ttf"
    subset(src, ref, ranges, {"*"}, None)
    survivable_floor = floor & face_features(ref)
    stripped = set(sorted(survivable_floor)[:2])
    assert len(stripped) == 2, f"need two survivable floor features, got {survivable_floor}"
    print(f"  ..    survivable floor here: {sorted(survivable_floor)}; stripping {sorted(stripped)}")
    bad = tmp / "bad.woff2"
    subset(src, bad, ranges, survivable_floor - stripped, "woff2")
    dropped = verify_no_drop(src, bad, ranges, tmp, floor)
    if set(dropped) != stripped:
        print(f"  FAIL  expected the rule to name {sorted(stripped)}, it named {dropped}")
        failures += 1
    else:
        print(f"  ok    rule names exactly the stripped features: {dropped}")

    # 3. Curation must NOT be reported: excluding smcp is a decision, not a loss.
    # A rule that cannot tell the two apart fails on the wrong thing and is
    # switched off, which is worse than not having it.
    if "smcp" in face_features(src):
        cur = tmp / "curated.woff2"
        subset(src, cur, ranges, floor & face_features(src), "woff2")
        if "smcp" in verify_no_drop(src, cur, ranges, tmp, floor):
            print("  FAIL  curation reported as a drop")
            failures += 1
        else:
            print("  ok    curated-out features are not reported as drops")

    print("no-drop rule verified" if not failures else f"{failures} check(s) failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
