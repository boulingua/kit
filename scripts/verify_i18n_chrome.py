#!/usr/bin/env python3
"""Gate A9 — no chrome string is hard-coded, and every key exists in every file.

    verify_i18n_chrome.py [KIT_OR_REPO]

Two failures, and the second is the one that bites.

  A literal in a layout. "Foliensatz" written into a template is invisible to
  every other language: a Greek course inherits the German word and nobody
  finds out until a learner reads it.

  A key used and not translated. `i18n "listen"` with no `listen` in de.yaml
  falls through to the inline `| default "Listen"`, so a German page silently
  prints an English word. That fallback is a safety net against a blank
  interface, not a licence to leave a key untranslated, and it is exactly why
  this failure is invisible without a gate: nothing is empty, nothing errors,
  the page just quietly speaks the wrong language.

This was blocked until kit/i18n/de.yaml existed at all. It did not — the whole
organisation had no German chrome vocabulary, while chrome_language: de is the
default for fifteen scaffolded courses.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

KIT = Path(__file__).resolve().parent.parent
I18N_CALL = re.compile(r'i18n\s+"([a-z_0-9]+)"')

# Chrome words that have appeared hard-coded in this org's layouts. Each was
# found in a real template, not imagined: they are the words a template author
# reaches for when there is no i18n file to reach for instead.
LITERALS = ("Foliensatz", "Arbeitsblatt", "Herunterladen", "Hören",
            "Text anzeigen", "Vorschau", "Downloads", "Hauptmenü",
            "Farbschema", "Ihr Browser", "Solutions", "Lösungen",
            "Wortschatz", "Prüfung", "Foliensätze", "Arbeitsblätter")


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else KIT
    layouts = root / "layouts"
    i18n_dir = root / "i18n"
    if not layouts.is_dir():
        print(f"A9 n/a — {root.name} ships no layouts/")
        return 0

    used: set[str] = set()
    literals: list[str] = []
    for f in sorted(layouts.rglob("*.html")):
        text = f.read_text(encoding="utf-8", errors="replace")
        used |= set(I18N_CALL.findall(text))
        for ln_no, ln in enumerate(text.splitlines(), 1):
            if ln.lstrip().startswith(("{{/*", "{{- /*", "#", "*")) or "i18n" in ln:
                continue
            for lit in LITERALS:
                if lit in ln:
                    literals.append(f"{f.relative_to(root)}:{ln_no}: chrome literal "
                                    f"{lit!r} — every other language inherits this "
                                    f"word. Move it to i18n/ and call it by key.")

    files = sorted(i18n_dir.glob("*.yaml")) if i18n_dir.is_dir() else []
    if not files:
        print(f"::error::{root.name} has layouts calling i18n but no i18n/*.yaml. "
              f"Every key falls through to its inline default, which is English.",
              file=sys.stderr)
        return 1

    missing: list[str] = []
    for f in files:
        have = set(yaml.safe_load(f.read_text(encoding="utf-8")) or {})
        for k in sorted(used - have):
            missing.append(f"i18n/{f.name}: key {k!r} is used in layouts/ and not "
                           f"translated here — the page prints the English default")

    for x in literals:
        print(f"::error::{x}")
    for x in missing:
        print(f"::error::{x}")
    bad = len(literals) + len(missing)
    if bad:
        print(f"\nA9 FAIL — {bad} problem(s)", file=sys.stderr)
        return 1
    print(f"A9 OK — {len(used)} key(s) used across {len(files)} language file(s), "
          f"all translated, no chrome literal in a layout")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
