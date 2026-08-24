#!/usr/bin/env python3
"""Remove syllabus codes from `tags:`, once they are proved to survive elsewhere.

    detag_syllabus_codes.py REPO            report
    detag_syllabus_codes.py REPO --apply    write

A tag is something a learner browses by. `3.2.3.7` is a Bildungsplan reference,
and mirroring it into `tags:` produces a taxonomy term at /tags/3-2-3-7/ that
no reader will ever click and no teacher will ever search. On efl that is 816 of
1,356 tag occurrences across 47 distinct codes — the tag cloud is mostly
syllabus numbering.

The removal is conditional on the code existing in the page's `bildungsplan:`
block, checked per code and per page. Where it does not, the tag is LEFT and
the page is named: `tags:` would then be the only copy of that alignment, and
deleting it would lose a fact rather than de-duplicate one.

Syllabus codes carry no VG Wort mark — verified against the URL lock before
running — so the taxonomy URLs this removes cost a reader's link at most, and
those links point at pages built entirely out of syllabus numbering.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

FM = re.compile(r"\A(---\n)(.*?)(\n---\n)", re.S)
CODE = re.compile(r"^[\d.]+$")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("repo", type=Path)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    repo = a.repo.resolve()

    removed, kept, wrote = 0, [], 0
    for md in sorted((repo / "content").rglob("*.md")):
        raw = md.read_text(encoding="utf-8")
        m = FM.match(raw)
        if not m:
            continue
        fm = yaml.safe_load(m.group(2)) or {}
        tags = fm.get("tags")
        if not isinstance(tags, list):
            continue
        bp = " ".join(str(x) for x in (fm.get("bildungsplan") or []))
        rel = md.relative_to(repo).as_posix()

        out, changed = [], False
        for t in tags:
            t = str(t)
            if CODE.match(t):
                if t in bp:
                    removed += 1
                    changed = True
                    continue
                kept.append(f"{rel}: {t!r} is a syllabus code but appears in no "
                            f"bildungsplan entry on this page — tags: is its only "
                            f"copy, so it stays")
            out.append(t)

        if changed:
            wrote += 1
            if a.apply:
                block = yaml.dump({"tags": out}, allow_unicode=True,
                                  sort_keys=False).rstrip("\n")
                body = re.sub(r"(?ms)^tags:.*?(?=^\S|\Z)", block + "\n", m.group(2))
                md.write_text(m.group(1) + body + m.group(3) + raw[m.end():],
                              encoding="utf-8")

    for k in kept[:10]:
        print(f"::warning::{k}")
    print(f"  {removed} syllabus code tag(s) removed, each verified present in "
          f"the same page's bildungsplan block")
    if kept:
        print(f"  {len(kept)} left in place — tags: is their only copy")
    print(f"  {wrote} file(s) " + ("written" if a.apply else "would change"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
