#!/usr/bin/env python3
"""Gates A18 and C6 — what a marked page owes, when it is not a unit.

    verify_page_contract.py REPO [BUILT]

EQS-1 governs units. It says nothing about the other 89 marked pages in this
organisation — glossaries, appendices, about pages, acknowledgements — and
those carry registered VG Wort marks exactly as units do. Until now nothing
examined them at all: they are revenue-bearing and unpoliced, which is the
combination that produces a registration nobody can defend.

Four things, and each is a different way for a mark to be indefensible:

  C6, the length floor. VG Wort's Mindestumfang for a Text is 1,800 characters.
  A shorter page carrying a mark is a registration that would not survive being
  looked at. Measured on the RENDERED page after stripping markup, because
  front-matter and shortcode syntax are not text a reader reads.

  A sources section. A page presenting factual or cultural claims without one
  asks a reader to take it on trust, and for an appendix — a glossary, a table
  of common errors — that is the whole content.

  An author. `<meta name="author">` is what ties the page to the person the
  mark is registered to.

  A page_type that permits a mark at all. section and legal pages must not
  carry one, which C3 also enforces from the rendered side; this catches it in
  the source, where it is cheaper to fix.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import yaml

FM = re.compile(r"\A---\n(.*?)\n---\n", re.S)
MIN_CHARS = 1800
# A page that says it will be written later, carrying a mark registered as
# though it already were. Found on 22 fle pages of ~215 bytes each: "Cette
# annexe sera remplie après l'écriture des 156 unités". This is a different
# failure from being short — a stub can grow, a placeholder is a statement that
# the work does not exist yet, and the mark asserts otherwise.
PLACEHOLDER = re.compile(r"à venir|to be filled|sera rempli|wird sp.ter|"
                         r"noch nicht|coming soon|Phase \d+ \(", re.I)
SOURCES = ("sources", "quellen", "sources et références", "sources et references",
           "further reading", "weiterführendes", "références", "literatur",
           "quellen und weiterführendes", "bibliographie")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from blg_paths import MARK_ELIGIBLE_PAGE_TYPES as ALLOWED  # noqa: E402


def body_chars(md: str) -> int:
    """Characters a reader actually reads."""
    t = re.sub(r"\{\{<.*?>\}\}", " ", md, flags=re.S)      # shortcodes
    t = re.sub(r"<[^>]+>", " ", t)                          # raw html
    t = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", t)        # links/images
    t = re.sub(r"[#*_`>|~-]", " ", t)                       # markup furniture
    return len(re.sub(r"\s+", " ", t).strip())


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    # --all prints every finding instead of the first 20. Disposing of these is
    # per-page author work against a list, and a list that stops at 20 with
    # "… and 76 more" cannot be worked through — you fix twenty, re-run, and
    # meet twenty different ones.
    show_all = "--all" in sys.argv[1:]
    repo = Path(args[0]).resolve() if args else Path.cwd()
    lock = repo / "vgwort" / "url-lock-provisional.csv"
    if not lock.exists():
        print("A18/C6 n/a — this repo registers no marks")
        return 0
    locked = {("/" + r["url"].strip("/") + "/")
              for r in csv.DictReader(l for l in lock.open(encoding="utf-8")
                                      if not l.startswith("#")) if r.get("url")}
    cfg = repo / "boulingua.yml"
    code = (yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}).get("code") \
        if cfg.exists() else None
    if code:
        locked = {u[len(code) + 1:] if u.startswith(f"/{code}/") else u for u in locked}

    bad, checked, units = [], 0, 0
    unsourced: list[str] = []
    for md in sorted((repo / "content").rglob("*.md")):
        raw = md.read_text(encoding="utf-8")
        m = FM.match(raw)
        if not m:
            continue
        fm = yaml.safe_load(m.group(1)) or {}
        rel = md.relative_to(repo / "content").as_posix()
        url = "/" + re.sub(r"/?_?index\.md$|\.md$", "", rel).strip("/") + "/"
        if url not in locked:
            continue
        ptype = fm.get("page_type")
        if ptype in ("unit", "exam"):
            units += 1
            continue
        checked += 1
        body = raw[m.end():]

        if ptype not in ALLOWED:
            bad.append(f"{rel}: carries a mark with page_type {ptype!r}. A section "
                       f"or legal page is not the author's Sprachwerk and must not "
                       f"be registered.")
        if PLACEHOLDER.search(body):
            bad.append(f"{rel}: carries a mark and says the content is still to "
                       f"come. A registration asserts a work exists; this page "
                       f"says it does not yet. Withdraw the mark or write the "
                       f"page — the mark cannot wait for the page.")
        n = body_chars(body)
        if n < MIN_CHARS:
            bad.append(f"{rel}: {n} characters, under VG Wort's {MIN_CHARS} "
                       f"Mindestumfang, while holding a mark. That registration "
                       f"would not survive being looked at.")
        heads = [h.strip().lower().rstrip(".")
                 for h in re.findall(r"(?m)^#{2,3}\s+(.+?)\s*$", body)]
        if not any(any(s in h for s in SOURCES) for h in heads):
            # WARNING, not a failure. Whether a page owes sources depends on
            # whether it makes claims about the world, and a gate cannot tell a
            # glossary of the course's own terminology — original authored
            # content — from an appendix summarising external facts. Failing 48
            # pages on that distinction would teach people to stop reading the
            # output. The length floor, the author and the page type are the
            # parts that are checkable without judgement, and those DO fail.
            unsourced.append(f"{rel}: no sources section. If this page makes "
                             f"claims about the world rather than presenting the "
                             f"course's own material, it owes one.")
        if not fm.get("author"):
            bad.append(f"{rel}: no author in front matter — the mark is registered "
                       f"to a person and nothing on the page names them")

    for u in unsourced[:6]:
        print(f"::warning::{u}")
    if len(unsourced) > 6:
        print(f"::warning::… and {len(unsourced) - 6} more without a sources section")
    import os
    for b in (bad if show_all else bad[:20]):
        print(f"::error::{b}")
    if len(bad) > 20:
        print(f"::error::… and {len(bad) - 20} more — re-run with --all for "
              f"the full list")
    print(f"  {units} marked unit/exam page(s) (EQS-1's territory), "
          f"{checked} marked non-unit page(s) checked here")
    if bad:
        print(f"\nA18/C6 FAIL — {len(bad)} problem(s)", file=sys.stderr)
        return 1
    print(f"A18/C6 OK — {checked} marked non-unit page(s): all over "
          f"{MIN_CHARS} characters, authored, and of a type that may carry a mark"
          + (f"; {len(unsourced)} carry no sources section, which is a judgement "
             f"call and is reported rather than failed" if unsourced else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
