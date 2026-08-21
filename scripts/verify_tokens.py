#!/usr/bin/env python3
"""Gate A7 — one source for the design system, proved on every push.

Two halves, and both matter:

1. **No generated file was edited by hand.** Delegates to
   `design/build_tokens.py --check`, which regenerates every artefact and diffs.

2. **The raw material is not available outside the one place it belongs.** Zero
   `#rrggbb`, `rgb()`, `rgba()` or `hsl()` in `assets/css/*.css` other than the
   generated `tokens.css`; zero `\\definecolor` in `latex/*.sty` other than the
   generated `boulingua-tokens.sty`.

The second half is the one that actually prevents recurrence. A check that only
compares generated output would pass a hand-written colour sitting in a
component rule, and that is precisely the shape of the original defect: the
palette had two sources — CSS custom properties and 86 `\\definecolor` literals
across two .sty files — kept in agreement by hand and not in agreement. Persian
reached the CSS side and never reached either .sty, so `pfa` had a web accent
and no print accent for as long as it existed.

A literal that genuinely must stay is marked in the three lines above it with

    /* a7-allow: <why> */

which forces a reason into the diff. There is exactly one today: the flat
`rgba()` fallback under the `color-mix()` callout wash, because a browser that
does not understand `color-mix()` must get a neutral tint rather than an
unstyled block.

    python scripts/verify_tokens.py        exit 1 on any violation
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
COLOUR = re.compile(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(")
ALLOW = re.compile(r"a7-allow:")
ALLOW_WINDOW = 3          # lines above the literal that may carry the marker


def allowed(lines: list[str], i: int) -> bool:
    return any(ALLOW.search(lines[j]) for j in range(max(0, i - ALLOW_WINDOW), i))


def decomment(text: str, style: str) -> list[str]:
    """Blank out comment bodies while preserving line numbering, so a rule
    written in prose ("no rgba() here") is not mistaken for a colour. Line
    count is kept exactly, because the caller reports line numbers.

    Run after the a7-allow markers have been read: those live in comments and
    would be erased by this."""
    if style == "css":
        out, depth = [], 0
        for line in text.split("\n"):
            buf, i = [], 0
            while i < len(line):
                if depth == 0 and line.startswith("/*", i):
                    depth, i = 1, i + 2
                elif depth and line.startswith("*/", i):
                    depth, i = 0, i + 2
                else:
                    buf.append(" " if depth else line[i]); i += 1
            out.append("".join(buf))
        return out
    return [re.sub(r"(?<!\\)%.*$", "", line) for line in text.split("\n")]


def scan(paths: list[Path], pattern: re.Pattern, what: str, generated: str) -> int:
    bad = 0
    for path in sorted(paths):
        if path.name == generated:
            continue
        raw = path.read_text(encoding="utf-8")
        lines = raw.split("\n")
        code = decomment(raw, "css" if path.suffix == ".css" else "tex")
        for i, line in enumerate(code):
            if not pattern.search(line):
                continue
            if allowed(lines, i):
                continue
            rel = path.relative_to(KIT)
            print(f"::error file={rel},line={i + 1}::{what} outside {generated}: "
                  f"{lines[i].strip()[:90]}")
            bad += 1
    return bad


def main() -> int:
    print("A7 — checking generated artefacts match design/tokens.yaml")
    r = subprocess.run([sys.executable, str(KIT / "design" / "build_tokens.py"), "--check"])
    bad = 1 if r.returncode else 0

    print("A7 — checking no colour is written outside the generated files")
    bad += scan(sorted((KIT / "assets" / "css").glob("*.css")),
                COLOUR, "colour literal", "tokens.css")
    bad += scan(sorted((KIT / "latex").glob("*.sty")),
                re.compile(r"\\definecolor"), "\\definecolor", "boulingua-tokens.sty")

    if bad:
        print("\nA7 FAIL — the design system has more than one source again. Put the "
              "value in design/tokens.yaml and regenerate, or mark a genuine "
              "exception with an a7-allow comment and say why.", file=sys.stderr)
        return 1
    print("A7 OK — one source for every colour, and nothing edited by hand")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
