#!/usr/bin/env python3
"""Gates A12 and A14 — the teaching shortcodes render, and render accessibly.

    python scripts/verify_eqs.py BUILT_SITE

Six shortcodes carry the educational standard, and each is four artefacts: the
HTML, the LaTeX emitter, an accessibility contract, and this. The contract is
the part that is cheap to write and expensive to retrofit, so it is checked in
the built output rather than trusted from the template.

What is checked, and why each one is the failure that actually happens:

  vocab      Per-column `lang`. A vocabulary table is the one place on a page
             where two languages sit in adjacent cells; without it a screen
             reader reads the target terms in the chrome language's phonology,
             which is unusable for exactly the learner who most needs audio.
             Plus <th scope="col">, so a cell read out of order still says
             which column it is in.

  niveau     The letter must be TEXT. A coloured chip alone fails anyone who
             cannot see it — and colour is the only thing distinguishing G from
             M from E at a glance.

  gap        An aria-label. This is the one where the naive version is actively
             hostile: an empty bordered span is read as a sentence with a word
             missing, so the learner never learns a task was there.

  recycles   Must resolve. An unresolved reference renders visibly rather than
             as a broken link, and this fails on it — a dead link that looks
             like a link is worse than one that announces itself.

  extension  <details>, so it is keyboard-reachable with no script, and its
             summary is a real heading in the document outline.

  tl         A lang attribute on every run (gate C12, checked here too).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Attribute matches, not substring matches. `'lang=' in tag` is True for
# data-lang=, aria-labelledby= satisfies a naive 'aria-label' test, and both
# would let a malformed fixture through — which is exactly what happened when
# this gate was first tested against one.
LANG_ATTR = re.compile(r'(?:^|\s)lang\s*=')
ARIA_LABEL_ATTR = re.compile(r'(?:^|\s)aria-label\s*=')

RECYCLES_RE = re.compile(r'<aside class="recycles".*?</aside>', re.S)
VOCAB_RE = re.compile(r'<table class="vocab">.*?</table>', re.S)
GAP_RE = re.compile(r'<span class="gap"[^>]*>')
NIVEAU_RE = re.compile(r'<div class="niveau[^"]*"[^>]*>.*?</div>', re.S)
TL_RE = re.compile(r'<(?:span|div) class="tl"[^>]*>')


def check(html: str, rel: str) -> list[str]:
    bad: list[str] = []

    for t in VOCAB_RE.findall(html):
        langs = set(re.findall(r'(?:^|\s)lang="([a-zA-Z-]+)"', t))
        if len(langs) < 2:
            bad.append(f"{rel}: vocab table carries {len(langs)} distinct lang "
                       f"attribute(s); the term and gloss columns must differ, or a "
                       f"screen reader reads the target language in the wrong voice")
        if not re.search(r'<th[^>]*scope="col"', t):
            bad.append(f"{rel}: vocab table has no <th scope=\"col\">")

    for n in NIVEAU_RE.findall(html):
        if not ARIA_LABEL_ATTR.search(n):
            bad.append(f"{rel}: niveau block has no aria-label naming the level in full")
        if 'visually-hidden' not in n and 'aria-label' not in n:
            bad.append(f"{rel}: niveau letter is presented without a text equivalent")

    for g in GAP_RE.findall(html):
        if not ARIA_LABEL_ATTR.search(g):
            bad.append(f"{rel}: a gap has no aria-label — it will be read as a "
                       f"sentence with a word missing and the task will be invisible")

    for a in RECYCLES_RE.findall(html):
        if 'recycles-unresolved' in a:
            unit = re.search(r'data-unit="([^"]*)"', a)
            bad.append(f"{rel}: recycles references unit_slug "
                       f"{unit.group(1) if unit else '?'!r}, which no page carries")

    for d in re.findall(r'<details class="extension">.*?</summary>', html, re.S):
        if '<summary>' not in d:
            bad.append(f"{rel}: extension is not a <details>/<summary>")

    for t in TL_RE.findall(html):
        if not LANG_ATTR.search(t):
            bad.append(f"{rel}: a tl run carries no lang attribute")

    return bad


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "public")
    if not root.exists():
        print(f"::error::{root} does not exist — build the site first", file=sys.stderr)
        return 1
    bad, seen = [], 0
    for f in sorted(root.rglob("index.html")):
        html = f.read_text(encoding="utf-8", errors="replace")
        if not any(k in html for k in ('class="vocab"', 'class="niveau',
                                       'class="gap"', 'class="recycles"',
                                       'class="extension"', 'class="tl"')):
            continue
        seen += 1
        bad += check(html, str(f.relative_to(root)))
    for b in bad:
        print(f"::error::{b}")
    if bad:
        print(f"\nA12/A14 FAIL — {len(bad)} violation(s) across {seen} page(s)",
              file=sys.stderr)
        return 1
    print(f"A12/A14 OK — {seen} page(s) using teaching shortcodes, all contracts met")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
