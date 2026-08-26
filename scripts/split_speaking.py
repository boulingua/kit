#!/usr/bin/env python3
"""Split `speaking` / `sprechen` from the page's own implements ids.

    split_speaking.py REPO [--apply]

The one migration in this programme where descriptor ids drive a rename rather
than follow it. efl and daf collapse interaction and production into one word;
fle already distinguishes them and needs nothing here. Guessing was never an
option, because the answer is a claim about what the unit actually asks a
learner to do — so the field waited until `implements` existed to be read.

The rule, from the programme: an INT.* id implies interaction, a PROD.* id
implies production. A page carrying both is genuinely both and gets both
values; a page carrying neither cannot be decided and is reported, not guessed.

The mirrored skill-* tags move in lockstep, as they did in the first pass.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

FM = re.compile(r"\A(---\n)(.*?)(\n---\n)", re.S)
COLLAPSED = {"speaking", "sprechen"}


def replace_block(body: str, key: str, values: list) -> str:
    lines, out, i, done = body.splitlines(), [], 0, False
    while i < len(lines):
        if not done and re.match(rf"^{re.escape(key)}\s*:", lines[i]):
            i += 1
            while i < len(lines) and lines[i].startswith("- "):
                i += 1
            out.append(f"{key}:")
            out += [f"- {v}" for v in values]
            done = True
            continue
        out.append(lines[i]); i += 1
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("repo", type=Path)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    repo = a.repo.resolve()

    outcome, undecidable, wrote = Counter(), [], 0
    unasserted: list[str] = []
    for md in sorted((repo / "content").rglob("*.md")):
        raw = md.read_text(encoding="utf-8")
        m = FM.match(raw)
        if not m:
            continue
        fm = yaml.safe_load(m.group(2)) or {}
        skills = [str(x) for x in (fm.get("skills_focus") or [])]
        if not (set(skills) & COLLAPSED):
            continue
        rel = md.relative_to(repo).as_posix()
        cur = fm.get("curriculum") or {}
        # PROPOSED ids cannot decide this, and the first run of this script
        # proved why: every one of efl's 71 and daf's 37 pages came out as
        # "interaction AND production", unanimously. That is not a finding, it
        # is an echo — the proposer treats `speaking` as spanning INT and PROD
        # and seeds one id of each, so reading them back returns the assumption
        # that generated them.
        #
        # The split is a claim about what a unit actually asks a learner to do.
        # It waits for ids somebody asserted after reading the unit.
        if cur.get("implements_basis") == "proposed":
            unasserted.append(rel)
            continue
        ids = [str(i) for i in (cur.get("implements") or [])]
        doms = {i.split(".")[1] for i in ids if i.count(".") >= 2}

        repl = []
        if "INT" in doms:
            repl.append("speaking_interaction")
        if "PROD" in doms:
            repl.append("speaking_production")
        if not repl:
            undecidable.append(f"{rel}: collapsed speaking value with no INT.* or "
                               f"PROD.* id to decide it from — left as it is")
            continue

        new = sorted({s for s in skills if s not in COLLAPSED} | set(repl))
        outcome["+".join(x.replace("speaking_", "") for x in repl)] += 1
        tags = fm.get("tags")
        newtags = None
        if isinstance(tags, list):
            keep = [str(t) for t in tags
                    if str(t) not in {f"skill-{c}" for c in COLLAPSED}
                    and str(t) not in COLLAPSED]
            added = [r.replace("_", "-") if not any(str(t).startswith("skill-") for t in tags)
                     else f"skill-{r.replace('_', '-')}" for r in repl]
            newtags = sorted(set(keep) | set(added))
        wrote += 1
        if a.apply:
            body = replace_block(m.group(2), "skills_focus", new)
            if newtags is not None:
                body = replace_block(body, "tags", newtags)
            md.write_text(m.group(1) + body + m.group(3) + raw[m.end():], encoding="utf-8")

    if unasserted:
        print(f"  {len(unasserted)} page(s) hold PROPOSED implements and were not "
              f"split. Reading a machine proposal back to decide the field it was "
              f"generated from returns the assumption, not an answer — confirm a "
              f"tranche to implements_basis: asserted, then re-run.")
    for u in undecidable[:8]:
        print(f"::warning::{u}")
    print(f"  {wrote} page(s) " + ("split" if a.apply else "would split"))
    for k, v in outcome.most_common():
        print(f"      {v:4d}  -> {k}")
    if undecidable:
        print(f"  {len(undecidable)} page(s) undecidable and left alone")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
