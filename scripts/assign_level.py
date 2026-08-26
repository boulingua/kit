#!/usr/bin/env python3
"""Write curriculum.level from the Klassenstufe→CEFR mapping.

    assign_level.py REPO CURRICULUM [--apply]

daf needed none of this: it carried cefr_level on all 60 pages and was migrated
directly. efl and fle carry no CEFR field at all — their axes are klassenstufe,
niveau and track, which are Bildungsplan — so a level has to come from
somewhere, and where it comes from is recorded per page.

  level_basis: derived    read back out of the page's OWN bildungsplan
                          Standardstufe. This is the author's assignment, not a
                          proposal about their curriculum.
  level_basis: proposed   from a Klassenstufe table, because nothing in the
                          repository constrains it. Queryable, so a later pass
                          can find every page still resting on a guess.

That field is the point of this script. Writing a level is easy; writing down
which ones are assertions and which are proposals is what makes the result
reviewable instead of merely present.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

FM = re.compile(r"\A(---\n)(.*?)(\n---\n)", re.S)
STUFE = re.compile(r"\b3\.(\d)\.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("repo", type=Path)
    ap.add_argument("curriculum", type=Path)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    repo = a.repo.resolve()

    table = yaml.safe_load(
        (a.curriculum / "mappings" / "klassenstufe-cefr.yaml").read_text(encoding="utf-8"))
    code = yaml.safe_load((repo / "boulingua.yml").read_text(encoding="utf-8"))["code"]
    spec = table.get(code)
    if not spec:
        print(f"  {code} is not in the mapping — nothing to do "
              f"(daf carries cefr_level per page and needs no table)")
        return 0

    by_level, by_basis, wrote, skipped = Counter(), Counter(), 0, 0
    unresolved: list[str] = []

    for md in sorted((repo / "content").rglob("*.md")):
        raw = md.read_text(encoding="utf-8")
        m = FM.match(raw)
        if not m:
            continue
        fm = yaml.safe_load(m.group(2)) or {}
        if fm.get("page_type") not in ("unit", "exam"):
            continue
        cur = fm.get("curriculum") or {}
        if cur.get("level"):
            skipped += 1
            continue
        rel = md.relative_to(repo).as_posix()

        level = basis = None
        if spec["basis"] == "bildungsplan-standardstufe":
            stufen = set()
            for b in (fm.get("bildungsplan") or []):
                stufen |= set(STUFE.findall(str(b)))
            if len(stufen) == 1:
                level = spec["standardstufe"].get(stufen.pop())
                basis = "derived"
            elif len(stufen) > 1:
                # 3.4 and 3.5 are the two Kursstufe niveaus and map to the same
                # CEFR band, so a page citing both is not ambiguous. Anything
                # else is, and is reported rather than resolved by picking one.
                mapped = {spec["standardstufe"].get(s) for s in stufen}
                if len(mapped) == 1:
                    level = mapped.pop()
                    basis = "derived"
                else:
                    unresolved.append(f"{rel}: cites Standardstufen {sorted(stufen)}, "
                                      f"which map to {sorted(mapped)} — two different "
                                      f"CEFR levels on one page")
                    continue
        # An exam inherits from the unit it examines. efl's 180 exam pages
        # carry no bildungsplan block — only units do — so they were falling
        # back to a Klassenstufe table while their own unit had a level derived
        # from the author's assignment. A unit and its exam claiming different
        # levels is not a rounding difference: the exam is what certifies the
        # unit, and gate A16 reads both.
        if level is None and fm.get("page_type") == "exam":
            stem = md.parent.name if md.name == "index.md" else md.stem
            sib = re.sub(r"[-_]exam$", "", stem)
            for cand in (md.parent.parent / sib / "index.md",
                         md.parent / f"{sib}.md",
                         md.parent.parent / f"{sib}.md"):
                if not cand.exists():
                    continue
                sm = FM.match(cand.read_text(encoding="utf-8"))
                if not sm:
                    continue
                sfm = yaml.safe_load(sm.group(2)) or {}
                stufen = set()
                for b in (sfm.get("bildungsplan") or []):
                    stufen |= set(STUFE.findall(str(b)))
                mapped = {spec.get("standardstufe", {}).get(x) for x in stufen} - {None}
                if len(mapped) == 1:
                    level, basis = mapped.pop(), "derived-from-unit"
                break

        if level is None:
            kl = fm.get("klassenstufe")
            if kl is None:
                unresolved.append(f"{rel}: no klassenstufe and no usable "
                                  f"bildungsplan code")
                continue
            level = (spec.get("klassenstufe") or {}).get(int(kl))
            basis = "proposed" if spec["basis"] == "klassenstufe" else "fallback"
            if level is None:
                unresolved.append(f"{rel}: Klassenstufe {kl} is not in the table")
                continue

        by_level[level] += 1
        by_basis[basis] += 1
        wrote += 1
        if a.apply:
            block = (f"  level: {level}\n"
                     f"  level_basis: {basis}\n")
            if cur:
                body = re.sub(r"(?m)^curriculum:\s*$", "curriculum:\n" + block.rstrip("\n"),
                              m.group(2), count=1)
            else:
                body = m.group(2) + ("\ncurriculum:\n"
                                     "  framework: boulingua-curriculum\n" + block)
            md.write_text(m.group(1) + body + m.group(3) + raw[m.end():], encoding="utf-8")

    for u in unresolved[:10]:
        print(f"::error::{u}")
    print(f"  {code}: basis {spec['basis']}")
    print(f"  levels: " + ", ".join(f"{k} {v}" for k, v in sorted(by_level.items())))
    print(f"  basis : " + ", ".join(f"{k} {v}" for k, v in by_basis.most_common()))
    if skipped:
        print(f"  {skipped} page(s) already had a level and were left alone")
    print(f"  {wrote} page(s) " + ("written" if a.apply else "would change"))
    return 1 if unresolved else 0


if __name__ == "__main__":
    raise SystemExit(main())
