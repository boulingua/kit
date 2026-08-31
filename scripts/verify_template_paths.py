#!/usr/bin/env python3
"""A21 — a course may not select a template by the name of a frozen URL.

    verify_template_paths.py REPO

Hugo picks a template by SECTION NAME. A section name is the first segment of a
public URL, and in this organisation a public URL is frozen permanently by
ADR-0003 because 789 registered VG Wort Zaehlmarken are keyed to them. Put those
two facts together and you get the defect this gate names:

    daf/layouts/materials/materials-list.html      92 lines
    fle/layouts/materiel/materials-list.html       the same 92 lines

Two files, one template, kept apart by nothing but the fact that *materials* and
*materiel* are different words. Eleven of the twenty course-local layouts in this
org exist for that reason and no other — not because the courses need different
templates, but because the courses have different URLs and Hugo routes on them.

The fix is to select by a front-matter `layout:` key at a section-neutral path
in the kit, which costs no URL and deletes the fork. This gate is the assertion
that the fix stays fixed: **no course template's first path segment may be a
top-level content section.**

It needs no configuration to say something true. Where `boulingua.yml` declares
a `templates:` block it also checks the declaration against the disk, in both
directions, so a promoted template cannot be left behind in a course and a
declared one cannot go missing.

It also refuses `url_shape` and its synonyms outright. That key was named as the
destination for daf's faceted-browser fork, and designing it was rejected: it
would encode the frozen section vocabulary of three courses into a config schema
that fifteen more would then have to fit, which is ADR-0003's rejected
alternative written in YAML. Selecting on `layout:` needs no such declaration,
so the absence of the key is part of the contract rather than an omission.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

#: Hugo's own reserved directories. A template here is routed by kind or called
#: by name, never by section, so it cannot be coupled to a URL.
NEUTRAL = {"_partials", "_shortcodes", "_markup", "_default", "partials",
           "shortcodes", "_internal"}

#: Keys that would reintroduce a declared section vocabulary.
FORBIDDEN_KEYS = {"url_shape", "section_pattern", "url_pattern", "section_map"}


def content_sections(repo: Path) -> set[str]:
    c = repo / "content"
    if not c.is_dir():
        return set()
    return {p.name for p in c.iterdir() if p.is_dir()}


def walk_keys(node, path=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield str(k), path
            yield from walk_keys(v, f"{path}.{k}" if path else str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk_keys(v, f"{path}[{i}]")


def main() -> int:
    repo = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    cfg_f = repo / "boulingua.yml"
    if not cfg_f.exists():
        print(f"A21 n/a — {repo.name} has no boulingua.yml and is not a course")
        return 0
    cfg = yaml.safe_load(cfg_f.read_text(encoding="utf-8")) or {}

    layouts = repo / "layouts"
    local = sorted(p.relative_to(layouts).as_posix()
                   for p in layouts.rglob("*") if p.is_file()) if layouts.is_dir() else []
    sections = content_sections(repo)

    bad, notes = [], []

    # (a) the forbidden key, anywhere in the config
    for key, where in walk_keys(cfg):
        if key in FORBIDDEN_KEYS:
            bad.append(f"boulingua.yml declares {key!r} at {where or '(root)'}. That "
                       f"key encodes a frozen section vocabulary into config, which "
                       f"is ADR-0003's rejected alternative in YAML. Select the "
                       f"template with a front-matter `layout:` key instead — it "
                       f"needs no vocabulary and costs no URL.")

    # (b) THE RULE: a template routed by a section name is coupled to a URL
    coupled = []
    for rel in local:
        first = rel.split("/")[0]
        if first in NEUTRAL or "/" not in rel:
            continue
        if first in sections:
            coupled.append((rel, first))
    for rel, first in coupled:
        bad.append(f"layouts/{rel} is selected by the section name {first!r}, which "
                   f"is the first segment of a frozen URL. Rename the section and "
                   f"789 marks move; keep it and this template can never be shared "
                   f"with a course that spells it differently. Move it to the kit "
                   f"under a section-neutral path and select it with `layout:`.")

    # (c) declaration vs disk, both directions — only where declared
    decl = cfg.get("templates") or {}
    if decl:
        if str(decl.get("selection", "")).strip() == "section":
            bad.append("boulingua.yml sets templates.selection: section, which is "
                       "the coupling this gate exists to remove.")
        declared = [str(x) for x in (decl.get("local") or [])]
        for d in declared:
            if d not in local:
                bad.append(f"templates.local names {d}, which is not in layouts/. "
                           f"A declaration that outlives its file is a standing "
                           f"permission for a fork nobody has.")
        for rel in local:
            if rel not in declared:
                bad.append(f"layouts/{rel} is not declared in templates.local. "
                           f"Every course-local template is a deliberate exception "
                           f"and has to be written down as one.")
    elif local:
        notes.append(f"{len(local)} local template(s) and no templates: block in "
                     f"boulingua.yml. The declaration becomes required at kit "
                     f"v1.23.0; until then this is a count, not a failure.")

    for b in bad:
        print(f"::error::{b}")
    for n in notes:
        print(f"::notice::{n}")
    if bad:
        print(f"\nA21 FAIL — {len(bad)} problem(s); {len(coupled)} of "
              f"{len(local)} local template(s) routed by a frozen section name",
              file=sys.stderr)
        return 1
    print(f"A21 OK — {len(local)} local template(s), {len(coupled)} routed by a "
          f"section name, {len(sections)} content section(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
