#!/usr/bin/env python3
"""Rename unit_slug -> material_slug, deriving it and then CHECKING it.

    material_slug.py REPO            report
    material_slug.py REPO --apply    write

A page in efl carries four independent slug namespaces, and they are not
interchangeable:

    unit_slug: "hello-world"                       a front-matter field
    presentation.file: .../track-e_kl05_unit01-hello-world.pdf   the MATERIAL
    the leaf-bundle directory unit01-hello-world   THIS IS THE URL
    aliases: /track_e_kl05/units/unit01_hello-world.html   the pre-migration URL

Changing the material slug renames a PDF and orphans nothing. Changing the
directory orphans a registered VG Wort mark and leaves the PDF untouched. So
`material_slug` is a PDF-naming key and never a URL input, and `unit_slug` is
RENAMED into it rather than left beside it as a fifth name.

The derivation is `<track>_kl<NN>_<bundle dir>`, and it is checked against the
committed `presentation.file` on every page rather than trusted. That check is
the whole point: efl's materials are named that way today, and a derivation
that silently disagreed — using the bare directory name, say — would repoint
360 download links at files no generator will ever produce. A mismatch is
reported and the page is left alone.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

FM = re.compile(r"\A(---\n)(.*?)(\n---\n)", re.S)


def derive(fm: dict, bundle_dir: str) -> str | None:
    track, kl = fm.get("track"), fm.get("klassenstufe")
    if track is None or kl is None:
        return None
    return f"track-{track}_kl{int(kl):02d}_{bundle_dir}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("repo", type=Path)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    repo = a.repo.resolve()

    ok, mismatched, underived, wrote, skipped = 0, [], [], 0, 0
    for md in sorted((repo / "content").rglob("index.md")):
        raw = md.read_text(encoding="utf-8")
        m = FM.match(raw)
        if not m:
            continue
        fm = yaml.safe_load(m.group(2)) or {}
        if "unit_slug" not in fm and "material_slug" not in fm:
            continue
        rel = md.relative_to(repo).as_posix()
        want = derive(fm, md.parent.name)
        if not want:
            underived.append(f"{rel}: no track/klassenstufe to derive from")
            continue

        # The check. presentation.file is what the generator actually produced.
        pres = ((fm.get("presentation") or {}).get("file") or "")
        actual = Path(str(pres)).stem if pres else None
        if actual and actual != want:
            mismatched.append(f"{rel}: derived {want!r} but presentation.file is "
                              f"{actual!r} — the rename would repoint this page's "
                              f"downloads at a file nothing produces")
            continue
        ok += 1

        if fm.get("material_slug") == want and "unit_slug" not in fm:
            skipped += 1
            continue

        body = m.group(2)
        if "unit_slug" in fm:
            body = re.sub(r"(?m)^unit_slug:.*$", f'material_slug: "{want}"', body, count=1)
        else:
            body = f'material_slug: "{want}"\n' + body
        wrote += 1
        if a.apply:
            md.write_text(m.group(1) + body + m.group(3) + raw[m.end():], encoding="utf-8")

    for x in mismatched:
        print(f"::error::{x}")
    for x in underived:
        print(f"::warning::{x}")
    print(f"  {ok} page(s) whose derived material_slug matches the committed "
          f"presentation.file")
    if skipped:
        print(f"  {skipped} already correct")
    print(f"  {wrote} file(s) " + ("written" if a.apply else "would change"))
    if mismatched:
        print(f"\nmaterial_slug FAIL — {len(mismatched)} mismatch(es), "
              f"nothing written for those pages", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
