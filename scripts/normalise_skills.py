#!/usr/bin/env python3
"""Normalise `skills_focus` onto the eight-value English enum.

    normalise_skills.py REPO            report what would change
    normalise_skills.py REPO --apply    write it

Three vocabularies exist today and the differences are not merely linguistic:

    efl  7 values, English   speaking 71  <- cannot be split mechanically
    daf  6 values, German    sprechen 37  <- same
    fle 11 values, mixed     sprechen_monolog 53 / sprechen_dialog 39

fle is the best placed of the three, which is the opposite of how its eleven
values look. It already distinguishes monologue from dialogue, so its speaking
split resolves today. efl and daf collapsed both into one word and cannot.

**`speaking` is therefore left alone by this script.** Whether a unit's
speaking is interaction or production is decided from its `implements` — an
`INT.*` id implies interaction, `PROD.*` production — so that half of the
migration lands AFTER the unit's implements tranche. It is the one place in the
programme where descriptor ids drive a migration rather than follow it, and
guessing here would put a wrong claim in a conformance manifest.

Anything this script cannot resolve, it names and leaves.

TAGS MOVE WITH IT. daf mirrors skills_focus into `tags:` as `skill-<value>` —
verified: every one of its 299 tag occurrences across 22 terms is mechanically
derivable from four front-matter fields, with zero extras and zero omissions on
every page. Rewriting skills_focus alone would desynchronise 60 pages and leave
six live taxonomy URLs (/tags/skill-lesen/ and friends) pointing at a
vocabulary no page carries any more. Those URLs carry no VG Wort mark, so this
costs a reader's dead link rather than income — but a migration that half-moves
a taxonomy is how a taxonomy ends up with both spellings forever.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

ENUM = {"reading", "listening", "speaking_interaction", "speaking_production",
        "writing", "mediation", "language_awareness", "intercultural"}

# Resolvable one-to-one. Every entry is a translation or a spelling variant of
# something already in the enum — no judgement is being made here.
MAP = {
    # efl — English already
    "reading": "reading", "listening": "listening", "writing": "writing",
    "mediation": "mediation", "language_awareness": "language_awareness",
    "intercultural": "intercultural",
    # daf — German
    "lesen": "reading", "hoeren": "listening", "hören": "listening",
    "schreiben": "writing", "sprachmittlung": "mediation",
    "sprachreflexion": "language_awareness",
    # fle — French/German, including the variants
    "leseverstehen": "reading",
    "hoerverstehen": "listening",
    "hör_hörsehverstehen": "listening",   # 18 pages; also non-ASCII in a key
                                          # that reaches URLs, which is its own
                                          # reason to remove it
    "wortschatz": "language_awareness",
    "interkulturelle_kompetenz": "intercultural",
    # fle DOES distinguish these, so they resolve where efl's and daf's do not
    "sprechen_monolog": "speaking_production",
    "sprechen_dialog": "speaking_interaction",
}

# Deliberately unresolved, each for a different reason.
DEFER = {
    "speaking": "collapses interaction and production; decided per unit from "
                "`implements` after that unit's tranche",
    "sprechen": "same — daf collapses both into one word",
}
NOT_A_SKILL = {
    "text_medien": "a Bildungsplan competence area, not a skill (ADR-0017). "
                   "Moves to bildungsplan.topic_codes, not into this enum.",
    "textmedienkompetenz": "as text_medien — a competence area",
}

FM = re.compile(r"\A(---\n)(.*?)(\n---\n)", re.S)


def replace_block(body: str, key: str, values: list) -> str:
    """Replace a YAML block-sequence key, list items and all.

    The first version used re.sub with `^key:.*?(?=^\\S|\\Z)` under (?ms).
    A block-sequence item starts with `- ` at column zero, which IS \\S — so
    the lookahead fired on the first item, the match consumed only the `key:`
    line, and the new block was prepended while every old item stayed. Applied
    to daf that produced `skills_focus: [reading, sprechen, lesen]` and a
    duplicated tag on 59 files: not a crash, not a diff anyone would skim
    twice, and a page carrying both vocabularies at once.

    Parsing the boundary properly instead: a key's block runs until the next
    line that is neither indented nor a `- ` item.
    """
    lines = body.splitlines()
    out, i, done = [], 0, False
    while i < len(lines):
        if not done and re.match(rf"^{re.escape(key)}\s*:", lines[i]):
            i += 1
            while i < len(lines) and (lines[i].startswith(("- ", "  ", "\t"))
                                      or not lines[i].strip()):
                if lines[i].strip() and not lines[i].startswith(("- ", "  ", "\t")):
                    break
                if not lines[i].strip():
                    break
                i += 1
            out.append(f"{key}:")
            out += [f"- {v}" for v in values]
            done = True
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("repo", type=Path)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    changed = Counter()
    retagged = Counter()
    deferred = Counter()
    notskill = Counter()
    orphaned: list[str] = []
    files = 0

    for md in sorted((a.repo / "content").rglob("*.md")):
        raw = md.read_text(encoding="utf-8", errors="replace")
        m = FM.match(raw)
        if not m:
            continue
        try:
            fm = yaml.safe_load(m.group(2)) or {}
        except Exception:
            continue
        sf = fm.get("skills_focus")
        if not sf:
            continue
        vals = sf if isinstance(sf, list) else [sf]
        out, touched = [], False
        for v in vals:
            v = str(v)
            if v in ENUM and v not in DEFER:
                out.append(v)
            elif v in DEFER:
                out.append(v)
                deferred[v] += 1
            elif v in NOT_A_SKILL:
                # Dropped, but only after checking the fact survives elsewhere.
                # These are Bildungsplan competence areas that ADR-0017 moves to
                # bildungsplan.topic_codes; on fle all 21 pages carrying
                # text_medien already list the matching 3.x.4 code in their
                # bildungsplan block, so the value is a duplicate and removing
                # it loses nothing. Where it is NOT duplicated the page is
                # named and the value is LEFT, because a migration that quietly
                # deletes the only copy of a fact is not a migration.
                bp = " ".join(str(x) for x in (fm.get("bildungsplan") or []))
                if re.search(r"3\.\d\.4|textuelle|m.diatique|Medien", bp, re.I):
                    notskill[v] += 1
                    touched = True
                else:
                    out.append(v)
                    orphaned.append(f"{md}: {v!r} is not a skill, but this page's "
                                    f"bildungsplan block does not carry the "
                                    f"equivalent code — left in place rather than "
                                    f"dropped")
            elif v in MAP:
                out.append(MAP[v])
                changed[f"{v} -> {MAP[v]}"] += 1
                touched = True
            else:
                print(f"::error::{md}: unknown skills_focus value {v!r}")
                out.append(v)
        # The mirrored tags, in lockstep. A `skill-<old>` tag whose value this
        # script just renamed becomes `skill-<new>`; a tag mirroring a value
        # left deliberately unsplit is left alone too, so the two fields never
        # disagree at any point in the migration.
        tags = fm.get("tags")
        newtags = None
        if isinstance(tags, list):
            nt, tagged = [], False
            for t in tags:
                t = str(t)
                if t.startswith("skill-"):
                    v = t[len("skill-"):]
                    if v in MAP and v not in DEFER:
                        # Hyphens in the tag, underscores in the enum. The enum
                        # value is a key; the tag is a URL segment, and
                        # /tags/skill-language_awareness/ mixes both
                        # conventions in one path.
                        slug = MAP[v].replace("_", "-")
                        nt.append(f"skill-{slug}")
                        retagged[f"skill-{v} -> skill-{slug}"] += 1
                        tagged = True
                        continue
                nt.append(t)
            if tagged:
                newtags = sorted(set(nt))
                touched = True

        if touched and a.apply:
            body = m.group(2)
            for key, val in (("skills_focus", sorted(set(out))),
                             ("tags", newtags)):
                if val is None:
                    continue
                body = replace_block(body, key, val)
            md.write_text(m.group(1) + body + m.group(3) + raw[m.end():], encoding="utf-8")
        files += 1 if touched else 0

    print(f"  {files} file(s) would change" + (" (applied)" if a.apply else ""))
    if retagged:
        print("  mirrored tags, moved in lockstep:")
        for k, n in retagged.most_common():
            print(f"    {n:4d}  {k}")
    for k, n in changed.most_common():
        print(f"    {n:4d}  {k}")
    if notskill:
        print("  dropped from skills_focus — not skills:")
        for k, n in notskill.most_common():
            print(f"    {n:4d}  {k}: {NOT_A_SKILL[k]}")
    for o in orphaned:
        print(f"::warning::{o}")
    if deferred:
        print("  LEFT ALONE, deliberately:")
        for k, n in deferred.most_common():
            print(f"    {n:4d}  {k}: {DEFER[k]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
