#!/usr/bin/env python3
"""Add page_type and curriculum.level. The mechanical half of the migration.

    migrate_frontmatter.py REPO            report
    migrate_frontmatter.py REPO --apply    write

TWO FIELDS, AND ONLY TWO. `page_type` is derivable from where a page sits;
`curriculum.level` is a rename of `cefr_level`. Everything else in the
curriculum block needs a person:

  implements   cannot be generated. The whole value of the field is that a
               human asserted the mapping — a script that guessed would put a
               conformance claim in a manifest nobody made.
  can_do       needs an id per statement, and there is no mapping anywhere in
               the organisation. On daf it is worse than a lookup: only 67 of
               179 entries even begin "Ich kann". The other 112 open with
               "Ich kenne", "Ich verstehe", "Ich schreibe" — they are learning
               aims, not can-do descriptors, so populating can_do is a rewrite
               and not a copy.

So this script does the part that is safe to automate and stops. The line
between the two halves is the point of the file.

`cefr_level` is left in place, not deleted. Removing it in the same pass would
mean the old key and the new one never coexist, and a course mid-migration
could not be read by either the old tooling or the new. It is removed by the
gate ramp once A2 is blocking, which is a separate, checkable step.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

FM = re.compile(r"\A(---\n)(.*?)(\n---\n)", re.S)

# Path -> page_type, first match wins. Deliberately ordered: a unit under
# /units/ is a unit even if it is called _index.md, and a legal page is legal
# even though it sits at the top level with the reference pages.
RULES = [
    # Exam BEFORE unit: fle keeps its exams as sibling pages inside units/,
    # named <unit>_exam, so a rule that only looks for /units/ calls all 156 of
    # them units and disagrees with the page_type they already carry. daf has
    # no exam pages at all — its exams are a `## Prüfung` section inside each
    # unit — so this rule is inert there rather than wrong.
    # Both separators. fle names its exams unit12_x_exam, efl names them
    # unit12-x-exam, and a rule that knows only one calls the other course's
    # 180 exams units — which is not a wrong label on a page nobody reads, it
    # is the wrong gate ramp and the wrong EQS contract applied to 180 pages.
    (lambda r: "/units/" in r
     and re.search(r"[-_]exam(/index)?\.md$|[-_]exam/$", r) is not None, "exam"),
    (lambda r: "/units/" in r and not r.endswith("_index.md"), "unit"),
    # Match the page's own slug, not just a flat filename. efl keeps its legal
    # pages as leaf bundles — impressum/index.md — so a filename test sees
    # "index.md" and files three statutory notices under `reference`, which is
    # the page_type gate A18 uses to decide what a marked non-unit page must
    # carry. daf and fle keep them flat, so the filename test worked there and
    # the gap only appears on the third repo.
    (lambda r: (Path(r).stem if Path(r).stem != "index" else Path(r).parent.name)
     in ("impressum", "datenschutz", "haftungsausschluss", "privacy",
         "imprint", "disclaimer", "mentions-legales"), "legal"),
    (lambda r: Path(r).name == "_index.md", "section"),
    (lambda r: r.startswith(("anhaenge/", "appendices/", "annexes/")), "appendix"),
    (lambda r: True, "reference"),
]


def page_type(rel: str) -> str:
    for test, kind in RULES:
        if test(rel):
            return kind
    return "reference"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("repo", type=Path)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    repo = a.repo.resolve()
    content = repo / "content"

    kinds, levels, wrote, already = Counter(), Counter(), 0, 0
    conflicts: list[str] = []

    for md in sorted(content.rglob("*.md")):
        raw = md.read_text(encoding="utf-8")
        m = FM.match(raw)
        if not m:
            continue
        fm = yaml.safe_load(m.group(2)) or {}
        rel = md.relative_to(content).as_posix()
        want = page_type(rel)
        kinds[want] += 1

        have = fm.get("page_type")
        if have and have != want:
            # An existing value is the author's; a path rule is a guess. Report
            # the disagreement rather than overwriting a deliberate choice.
            conflicts.append(f"{rel}: page_type is {have!r}, the path says {want!r}")
            continue

        body = m.group(2)
        changed = False
        if not have:
            body = f"page_type: {want}\n" + body
            changed = True
        else:
            already += 1

        lvl = fm.get("cefr_level")
        cur = fm.get("curriculum") or {}
        if lvl and not cur.get("level"):
            levels[str(lvl)] += 1
            if cur:
                body = re.sub(r"(?m)^curriculum:\s*$",
                              f"curriculum:\n  level: {lvl}", body, count=1)
            else:
                body += (f"\ncurriculum:\n  framework: boulingua-curriculum\n"
                         f"  level: {lvl}\n"
                         f"  # implements: chosen by hand — see"
                         f" `conformance_audit.py suggest --page`\n")
            changed = True

        if changed:
            wrote += 1
            if a.apply:
                md.write_text(m.group(1) + body + m.group(3) + raw[m.end():],
                              encoding="utf-8")

    for c in conflicts:
        print(f"::error::{c}")
    print(f"  page_type by path: " + ", ".join(f"{k} {v}" for k, v in kinds.most_common()))
    if already:
        print(f"  {already} page(s) already carried page_type and were left alone")
    if levels:
        print(f"  curriculum.level from cefr_level: "
              + ", ".join(f"{k} {v}" for k, v in sorted(levels.items())))
    print(f"  {wrote} file(s) " + ("written" if a.apply else "would change"))
    print("  implements and can_do are NOT written — they need a person, and a "
          "generated conformance claim is a claim nobody made")
    return 1 if conflicts else 0


if __name__ == "__main__":
    raise SystemExit(main())
