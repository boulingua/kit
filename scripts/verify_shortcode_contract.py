#!/usr/bin/env python3
"""Gate A19 — the shortcode set is closed, and nothing bypasses it.

    verify_shortcode_contract.py REPO

Three failures, and they are three different kinds of invisible.

  RAW MARKUP owning a shortcode's class. `<div class="card">` in Markdown is
  invisible to everything that is not a browser: the LaTeX emitter never sees
  it, nothing can style it later, and no query can find which pages use it.

  AN UNDECLARED SHORTCODE. A course inventing one is a fork with no file — it
  works until the kit ships a shortcode of the same name and silently wins.

  A DECLARED SHORTCODE WITH NO EMITTER. This is the one that costs teaching
  content: a block with no LaTeX emitter renders on the page and vanishes from
  the printed worksheet, and nothing about the build says so. The declaration
  therefore requires either an emitter symbol that exists in the .sty files, or
  a written reason it is deferred — the reason being what stops "not yet" from
  becoming "never" without anyone deciding it.

Verified live when this was written: efl carries 180 `<div class="notes">`,
fle 198 raw divs across 25 files, daf ~95 across 17. None is in the declared
set — `notes` is a real block with no shortcode at all — so they are reported
as unowned rather than as violations of an owner that does not exist.
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

import yaml

KIT = Path(__file__).resolve().parent.parent
RAW_TAG = re.compile(r'<(div|span|section|aside)\b[^>]*class="([^"]+)"')
USED = re.compile(r"\{\{<\s*/?\s*([a-z][a-z0-9_-]*)")


def main() -> int:
    repo = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    decl = yaml.safe_load((KIT / "shortcodes.yml").read_text(encoding="utf-8"))["shortcodes"]
    # A repo may ship a shortcode the kit does not — website's {{< worldmap >}}
    # renders a map no course has. Closed means "declared somewhere", not
    # "declared in the kit": a course inventing one silently is the failure,
    # and a course declaring one in its own file has done exactly what the
    # contract asks. Its entries carry the same four requirements.
    local = repo / "shortcodes.yml"
    if local.exists():
        extra = (yaml.safe_load(local.read_text(encoding="utf-8")) or {}).get("shortcodes") or []
        for e in extra:
            e["_local"] = True
        decl = decl + extra
    names = {d["name"] for d in decl}
    owned = {c: d for d in decl for c in (d.get("owns") or [])}

    bad, unowned, furniture = [], Counter(), Counter()

    # 1. the declaration against the .sty files — checked once, not per repo
    sty = "\n".join(p.read_text(encoding="utf-8", errors="replace")
                    for p in (KIT / "latex").glob("*.sty"))
    for d in decl:
        sym = d.get("latex")
        if sym:
            hay = sty
            if d.get("_local"):
                hay += "\n".join(p.read_text(encoding="utf-8", errors="replace")
                                  for p in (repo / "latex").glob("*.sty")) if (repo / "latex").is_dir() else ""
            if not re.search(rf"\\(newcommand|newenvironment|newtcolorbox)\{{?\\?{re.escape(sym)}\b", hay):
                bad.append(f"shortcodes.yml: {d['name']} declares LaTeX emitter "
                           f"{sym!r}, which no .sty defines. A block with no "
                           f"emitter renders on the page and vanishes from the "
                           f"printed worksheet.")
        elif not str(d.get("latex_deferred", "")).strip():
            bad.append(f"shortcodes.yml: {d['name']} has no LaTeX emitter and no "
                       f"latex_deferred reason. 'Not yet' without a reason is how "
                       f"it becomes 'never' without anyone deciding.")

    # 2. and 3. the repo's content
    for md in sorted((repo / "content").rglob("*.md")):
        text = md.read_text(encoding="utf-8", errors="replace")
        rel = md.relative_to(repo).as_posix()
        for _, classes in RAW_TAG.findall(text):
            for c in classes.split():
                d = owned.get(c)
                if d is None:
                    unowned[c] += 1
                elif d.get("kind") == "furniture":
                    furniture[c] += 1
                else:
                    bad.append(f"{rel}: raw markup carrying class {c!r}, which "
                               f"{{{{< {d['name']} >}}}} owns. Raw HTML is invisible "
                               f"to the LaTeX emitter, so this block renders on the "
                               f"page and is absent from the printed worksheet.")
        for name in set(USED.findall(text)):
            if name not in names:
                bad.append(f"{rel}: uses {{{{< {name} >}}}}, which is not in the "
                           f"declared set")

    for b in bad[:20]:
        print(f"::error::{b}")
    if len(bad) > 20:
        print(f"::error::… and {len(bad) - 20} more")
    if unowned:
        top = ", ".join(f"{c} ×{n}" for c, n in unowned.most_common(6))
        print(f"::warning::{sum(unowned.values())} raw block(s) carry a class no "
              f"shortcode owns ({top}). These are not violations — there is no "
              f"owner to violate — but each is a block only a browser can read.")
    if furniture:
        top = ", ".join(f"{c} x{n}" for c, n in furniture.most_common(5))
        print(f"::notice::{sum(furniture.values())} raw furniture block(s) ({top}). "
              f"Not converted, deliberately: a heading inside a raw div reaches "
              f".TableOfContents and the same heading inside a shortcode does not "
              f"— built and checked — so converting these would drop unit headings "
              f"out of the landing-page outlines to satisfy a rule that protects "
              f"the printed worksheet, which furniture never reaches.")
    if bad:
        print(f"\nA19 FAIL — {len(bad)} problem(s)", file=sys.stderr)
        return 1
    n_local = sum(1 for d in decl if d.get("_local"))
    print(f"A19 OK — {len(names)} declared shortcode(s)"
          + (f" ({n_local} declared by this repo)" if n_local else "")
          + f", every emitter present or deferred with a reason, no raw markup "
            f"on an owned class")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
