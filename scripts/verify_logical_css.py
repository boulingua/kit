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


def rel_to(path: Path, repo: Path) -> str:
    """A path the reader can act on. This was relative_to(KIT) unconditionally,
    which raises ValueError the moment the file belongs to a course — so the
    first real finding this gate ever produced crashed it."""
    for base in (repo, KIT):
        try:
            return f"{base.name}/{path.resolve().relative_to(base)}"
        except ValueError:
            continue
    return str(path)


def stylesheets(root: Path) -> list[Path]:
    """Every stylesheet a repo actually ships. The kit's own live under
    assets/css; a course may put them in either assets/ or static/."""
    out: list[Path] = []
    for sub in (("assets", "css"), ("static", "css")):
        d = root.joinpath(*sub)
        if d.is_dir():
            out += sorted(d.glob("*.css")) + sorted(d.rglob("*.scss"))
    return out


def main() -> int:
    # THE ARGUMENT, like every sibling script. This read
    #     # and never touched sys.argv, so it printed the identical verdict —
    # "A8 OK — 2 stylesheet(s), 22 logical inline properties, no physical ones"
    # — for daf, efl, fle, nsf, website AND for a path that does not exist.
    # It had never opened a course stylesheet, and the four it never opened
    # hold 23 physical inline properties between them, including seven
    # border-left-color rules in fle/assets/css/network.css: precisely the
    # "copied into forty rules" case the docstring says it exists to stop
    # before the first RTL course.
    bad = 0
    repo = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else KIT
    if not repo.is_dir():
        # Without this the kit fallback below makes a typo'd path scan the
        # kit's two stylesheets and print OK — the same vacuous pass in a new
        # place. A gate must not answer a question about a repo that is absent.
        print(f"::error::{repo} is not a directory. A8 cannot report on a repo "
              f"it cannot open.", file=sys.stderr)
        return 2
    files = stylesheets(repo)
    if repo != KIT:
        files += stylesheets(KIT)
    generated = {(KIT / "assets" / "css" / "tokens.css").resolve()}
    if not files:
        print(f"A8 n/a — {repo.name} ships no stylesheet of its own "
              f"and the kit's were not reachable")
        return 0
    checked = 0
    for path in files:
        # tokens.css is GENERATED and declares custom properties, not layout.
        # Keyed on the resolved path, not the basename: a course file of the
        # same name is a hand-written stylesheet and must be examined.
        if path.resolve() in generated:
            continue
        checked += 1
        raw = path.read_text(encoding="utf-8")
        lines, code = raw.split("\n"), decomment(raw, "css")
        for i, line in enumerate(code):
            if not PHYSICAL.search(line):
                continue
            if any(ALLOW.search(lines[j]) for j in range(max(0, i - WINDOW), i)):
                continue
            print(f"::error file={rel_to(path, repo)},line={i + 1}::physical inline "
                  f"property — use the -inline-start/-inline-end form: {lines[i].strip()[:80]}")
            bad += 1

    if bad:
        print(f"\nA8 FAIL — {bad} physical inline propert{'y' if bad == 1 else 'ies'}. "
              f"These look correct until the first right-to-left island, which is "
              f"why they are caught now.", file=sys.stderr)
        return 1
    # `checked`, not len(files): the generated tokens.css is skipped by the
    # loop above and counting it inflated the verdict by one on every run.
    n = sum(len(re.findall(r"-inline(?:-start|-end)?(?:-[a-z]+)?\s*:",
                           q.read_text(encoding="utf-8")))
            for q in files if q.resolve() not in generated)
    print(f"A8 OK — {checked} stylesheet(s) examined in {repo.name}, "
          f"{n} logical inline properties, no physical ones")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
