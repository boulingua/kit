#!/usr/bin/env python3
"""Gate A8 — inline positioning is expressed logically.

    python scripts/verify_logical_css.py

`padding-left` is a statement about the screen. `padding-inline-start` is a
statement about the text. On a left-to-right page they are the same thing,
which is exactly why the wrong one survives review: nothing looks broken until
a right-to-left island appears, and by then the property has been copied into
forty rules.

So this gate runs now, years before the first Arabic course, and that is
deliberate. Retro-fitting logical properties under wave-5 time pressure is how
a physical property survives into production.

ALLOWED, and each for a reason:

  flex-direction: row | row-reverse    Direction-neutral. `row` already follows
                                       the writing mode; `row-reverse` reverses
                                       relative to it, not to the screen.
  text-align: center | justify         No inline direction.
  background-position, transform,      Geometric, not textual. A drop shadow
  box-shadow offsets                   does not mirror with the text.

FORBIDDEN: padding/margin/border/inset -left|-right, and bare `left:`/`right:`
in a positioned rule. Use the -inline-start / -inline-end forms.

An exception that is genuinely geometric carries `/* a8-allow: <why> */` in the
three lines above it, so the reason lands in the diff rather than in someone's
memory.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT / "scripts"))
from verify_tokens import decomment  # noqa: E402  — same comment handling

PHYSICAL = re.compile(
    r"(?<![\w-])(?:(?:padding|margin|border|inset|scroll-margin|scroll-padding)"
    r"-(?:left|right)(?:-[a-z]+)?|left|right)\s*:")
ALLOW = re.compile(r"a8-allow:")
WINDOW = 3


def main() -> int:
    bad = 0
    files = sorted((KIT / "assets" / "css").glob("*.css"))
    for path in files:
        # tokens.css is generated and declares custom properties, not layout.
        if path.name == "tokens.css":
            continue
        raw = path.read_text(encoding="utf-8")
        lines, code = raw.split("\n"), decomment(raw, "css")
        for i, line in enumerate(code):
            if not PHYSICAL.search(line):
                continue
            if any(ALLOW.search(lines[j]) for j in range(max(0, i - WINDOW), i)):
                continue
            print(f"::error file={path.relative_to(KIT)},line={i + 1}::physical inline "
                  f"property — use the -inline-start/-inline-end form: {lines[i].strip()[:80]}")
            bad += 1

    if bad:
        print(f"\nA8 FAIL — {bad} physical inline propert{'y' if bad == 1 else 'ies'}. "
              f"These look correct until the first right-to-left island, which is "
              f"why they are caught now.", file=sys.stderr)
        return 1
    n = sum(len(re.findall(r"-inline(?:-start|-end)?(?:-[a-z]+)?\s*:", p.read_text(encoding="utf-8")))
            for p in files)
    print(f"A8 OK — {len(files)} stylesheet(s), {n} logical inline properties, no physical ones")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
