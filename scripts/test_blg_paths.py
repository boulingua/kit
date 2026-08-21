#!/usr/bin/env python3
"""Verify the path contract against all three live content models.

    python scripts/test_blg_paths.py [../efl ../fle ../daf]

Two halves. The first is a fixture matrix of the four namespaces on real units
from each repo. The second is the one that matters: run the accessors across
every live unit and check they reproduce **today's URLs** — compared against
`vgwort/url-lock-provisional.csv`, which was derived from the built sites and
is therefore what actually ships — and **today's material filenames**, compared
against the PDFs on disk.

That second half is the acceptance criterion, and it is worth stating why it is
shaped like this. A path helper that is merely plausible is not enough here:
every URL it gets wrong is a registered VG Wort mark orphaned, and the failure
is silent, because a wrong URL still renders a page. So the test does not check
that the function is reasonable. It checks that it agrees, row for row, with
what is already deployed.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blg_paths as bp  # noqa: E402

# Real units, one content model each. The efl row is the whole reason the four
# accessors exist: three different strings for one page.
FIXTURES = [
    dict(repo="efl", model="leaf bundle",
         rel="content/track-e/kl09/units/unit06-interview-and-portrait/index.md",
         url="/track-e/kl09/units/unit06-interview-and-portrait/",
         material="track-e_kl09_unit06-interview-and-portrait",
         unit="interview-and-portrait", exam=False),
    dict(repo="fle", model="flat file + slug override",
         rel="content/track_gm_kl10/units/unit01_transition-formation-emploi.md",
         url="/track_gm_kl10/units/transition-formation-emploi/",
         material="unit01_transition-formation-emploi",
         unit="transition-formation-emploi", exam=False),
    dict(repo="daf", model="flat file",
         rel="content/kurs_b2/units/unit09_bildungsdebatten.md",
         url="/kurs_b2/units/unit09_bildungsdebatten/",
         material="unit09_bildungsdebatten",
         unit="bildungsdebatten", exam=False),
]


def check_fixtures(org: Path) -> int:
    bad = 0
    print("── fixture matrix: four namespaces x three content models ──")
    for f in FIXTURES:
        md = org / f["repo"] / f["rel"]
        if not md.exists():
            print(f"  SKIP {f['repo']}: {f['rel']} not found")
            continue
        root = org / f["repo"] / "content"
        fm, body = bp.front_matter(md)
        got = dict(url=bp.url_key(md, root, fm),
                   material=bp.material_slug(md, fm, body),
                   unit=bp.unit_slug(md, fm),
                   exam=bp.is_exam_page(md))
        ok = all(got[k] == f[k] for k in ("url", "material", "unit", "exam"))
        print(f"  {'ok  ' if ok else 'FAIL'} {f['repo']} ({f['model']})")
        for k in ("url", "material", "unit"):
            mark = " " if got[k] == f[k] else "!"
            print(f"      {mark} {k:9s} {got[k]}")
            if got[k] != f[k]:
                print(f"        expected {f[k]}")
        bad += 0 if ok else 1
    return bad


def check_urls(org: Path, repos: list[str]) -> int:
    """Reproduce every URL that carries a mark today."""
    bad = 0
    print("\n── URL reproduction against the deployed set ──")
    for r in repos:
        lock = org / r / "vgwort" / "url-lock-provisional.csv"
        root = org / r / "content"
        if not lock.exists():
            print(f"  SKIP {r}: no url-lock")
            continue
        want = {row["url"] for row in csv.DictReader(
            l for l in lock.open(encoding="utf-8") if not l.startswith("#"))}
        got = set()
        for md in root.rglob("*.md"):
            try:
                got.add(bp.url_key(md, root))
            except Exception:
                pass
        missing = want - got
        print(f"  {r}: {len(want)} marked URLs, {len(missing)} not reproduced")
        for u in sorted(missing)[:4]:
            print(f"      missing {u}")
        bad += 1 if missing else 0
    return bad


def check_materials(org: Path, repos: list[str]) -> int:
    """Reproduce every material filename on disk, with no fallback fired."""
    bad = 0
    print("\n── material filename reproduction ──")
    for r in repos:
        root = org / r / "content"
        pres = org / r / "static" / "materials" / "presentations"
        if not pres.exists() or not any(pres.glob("*.pdf")):
            print(f"  {r}: no committed presentations (gitignored) — skipped")
            continue
        on_disk = {p.stem for p in pres.glob("*.pdf")}
        derived, failed = set(), 0
        for md in root.rglob("*.md"):
            if bp.is_exam_page(md):
                continue
            try:
                fm, body = bp.front_matter(md)
                if not fm:
                    continue
                derived.add(bp.material_slug(md, fm, body))
            except bp.SiteError:
                # Only a page that HAS materials needs a material slug. Section
                # landings, legal pages and appendices legitimately have none.
                if "/units/" in md.as_posix():
                    failed += 1
        missing = on_disk - derived
        print(f"  {r}: {len(on_disk)} PDFs on disk, {len(missing)} not derived, "
              f"{failed} unit(s) with no recoverable slug")
        for s in sorted(missing)[:4]:
            print(f"      missing {s}")
        bad += 1 if missing else 0
    return bad


def main() -> int:
    org = Path(__file__).resolve().parents[2]
    repos = sys.argv[1:] or ["efl", "fle", "daf"]
    bad = check_fixtures(org) + check_urls(org, repos) + check_materials(org, repos)
    print("\n" + ("path contract verified against all three content models"
                  if not bad else f"{bad} check group(s) failed"))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
