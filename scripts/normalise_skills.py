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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("repo", type=Path)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    changed = Counter()
    deferred = Counter()
    notskill = Counter()
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
                notskill[v] += 1          # dropped from skills_focus
                touched = True
            elif v in MAP:
                out.append(MAP[v])
                changed[f"{v} -> {MAP[v]}"] += 1
                touched = True
            else:
                print(f"::error::{md}: unknown skills_focus value {v!r}")
                out.append(v)
        if touched and a.apply:
            new = yaml.dump({"skills_focus": sorted(set(out))},
                            allow_unicode=True, sort_keys=False).rstrip("\n")
            body = re.sub(r"(?ms)^skills_focus:.*?(?=^\S|\Z)", new + "\n", m.group(2))
            md.write_text(m.group(1) + body + m.group(3) + raw[m.end():], encoding="utf-8")
        files += 1 if touched else 0

    print(f"  {files} file(s) would change" + (" (applied)" if a.apply else ""))
    for k, n in changed.most_common():
        print(f"    {n:4d}  {k}")
    if notskill:
        print("  dropped from skills_focus — not skills:")
        for k, n in notskill.most_common():
            print(f"    {n:4d}  {k}: {NOT_A_SKILL[k]}")
    if deferred:
        print("  LEFT ALONE, deliberately:")
        for k, n in deferred.most_common():
            print(f"    {n:4d}  {k}: {DEFER[k]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
