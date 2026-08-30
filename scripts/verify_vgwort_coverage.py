#!/usr/bin/env python3
"""C4 — Mindestumfang coverage. Pages that have earned a mark and have none.

    python scripts/verify_vgwort_coverage.py REPO_OR_BUILT_SITE

Walks the built site for editorial pages whose rendered prose clears the
1,800-character VG Wort Mindestumfang and carry no entry in the course's
registry. It is the only gate in the battery pointed at **revenue not yet
claimed**; every other VG Wort gate defends marks that already exist.

Per the brief this is a WARNING, not a hard fail: Zählmarken are issued
asynchronously through the T.O.M. portal, so a page can be complete and correct
for weeks before its mark exists. A blocking coverage gate would punish the
author for VG Wort's queue.

"Warning" is `severity: warn` in gates.yml, and the battery renders it from the
EXIT CODE — non-zero on a warn gate prints `warn`, on a blocking gate `FAIL`.
This script returned 0 unconditionally, which is not the same thing: it made
the severity field inert and printed `ok` next to its own findings. website
carries three unregistered pages, one of them 10,487 characters, and the
summary line said ok.

**It had never run.** Until now the first three lines read

    ROOT   = Path(__file__).resolve().parents[1]   # the kit, always
    PUBLIC = ROOT / "public"
    DATA   = ROOT / "data" / "vgwort.yaml"

and the script read no argv at all, while `bin/kit check` passes the repo as
argv[1] like it does to every sibling. So C4 opened `kit/data/vgwort.yaml`,
did not find it, printed "data/vgwort.yaml missing" and returned 1 — on every
repo, including the three where that file exists and holds 821 entries between
them. Severity `warn` meant the wrong answer never blocked anything, and the
message had been on screen long enough to read as furniture.

Three further things were wrong once the root was fixed, and each is worth
naming because each would have produced a plausible number:

  - the skip list carried `/track-e/` and `/track-gm/`, which are efl's section
    paths, hardcoded into a script that runs on all five courses;
  - the registry location was assumed rather than read from `boulingua.yml`,
    where daf declares `vgwort/marks.yaml` and keeps its marks in
    `data/vgwort.yaml`;
  - a missing registry returned 1 instead of reporting the coverage, which is
    backwards — a course with long pages and no registry is the *strongest*
    finding this gate can make, not a reason to decline to make it.

The forbidden-surface list is imported, not restated, and so is the set of
page types that may carry a mark at all. A coverage gate that asks for a mark on
/datenschutz/ is instructing the author to do the thing C3 fails them for; one
that asks for a mark on a `page_type: section` landing page is contradicting
A18/C6, which fails exactly that. On the first run of this rewrite it did the
second, on daf's five level indexes — 4,691 to 6,480 rendered characters each,
which is why they look like Sprachwerke and are not. `page_type` does not reach
the rendered HTML, so eligibility is read from the source front matter and
keyed by url_key, the same resolver A3, C1 and C2 use.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blg_paths import (  # noqa: E402
    MARK_ELIGIBLE_PAGE_TYPES, front_matter, is_mark_forbidden, url_key)

KIT = Path(__file__).resolve().parent.parent
THRESHOLD = 1800

PROSE_RE = re.compile(r"<article\b[^>]*>(.*?)</article>", re.DOTALL | re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>", re.DOTALL)
PAGINATOR_RE = re.compile(r"/page/\d+/$")
ALIAS_RE = re.compile(r"""http-equiv\s*=\s*["']?refresh""", re.I)


def locate(arg: Path) -> tuple[Path, Path]:
    """(repo, built site). Accept either, as C2 does — a gate that is awkward
    to invoke gets invoked wrongly and then reported as broken.

    A repo is recognised by `boulingua.yml`, which every course has and the kit
    does not; `hugo.toml` is checked second because a scaffold has one before
    it is configured. Sniffing on `hugo.toml` ALONE sends the kit down the
    built-site branch — it ships `hugo.defaults.toml` — and the gate then walks
    `kit/layouts/` and reports two partials as unregistered Sprachwerke. It
    did, on the first run of this rewrite."""
    if (arg / "boulingua.yml").exists() or (arg / "hugo.toml").exists():
        return arg, arg / "public"
    return arg.parent, arg


def config(repo: Path) -> dict:
    f = repo / "boulingua.yml"
    if not f.exists():
        return {}
    return (yaml.safe_load(f.read_text(encoding="utf-8")) or {}).get("vgwort") or {}


def registry_urls(repo: Path, cfg: dict) -> tuple[set[str], Path | None]:
    """Every URL the course has a mark for. Declared location first, then the
    org default — a declaration pointing at nothing must not hide the real
    file, which is exactly daf's situation."""
    candidates = []
    if cfg.get("registry"):
        candidates.append(repo / str(cfg["registry"]))
    candidates.append(repo / "data" / "vgwort.yaml")
    for c in candidates:
        if c.exists():
            entries = yaml.safe_load(c.read_text(encoding="utf-8")) or []
            return {str(e["url"]) for e in entries if e.get("url")}, c
    return set(), None


def ineligible_urls(repo: Path) -> set[str]:
    """URLs whose page_type may not carry a mark — sections, legal notices, and
    anything else outside the allow-list A18/C6 enforces.

    Read from source because `page_type` is front matter and never rendered. A
    page with no page_type at all is left eligible: this gate warns, and a
    missing declaration is A2's finding to make, not a reason for C4 to fall
    silent about a page that may well be earning nothing."""
    content = repo / "content"
    if not content.is_dir():
        return set()
    out = set()
    for md in content.rglob("*.md"):
        try:
            fm, _ = front_matter(md)
        except Exception:
            continue
        ptype = (fm or {}).get("page_type")
        if ptype is not None and ptype not in MARK_ELIGIBLE_PAGE_TYPES:
            out.add(url_key(md, content, fm or {}))
    return out


def page_url(p: Path, public: Path) -> str:
    rel = p.relative_to(public).as_posix()
    if rel.endswith("index.html"):
        return "/" + rel.removesuffix("index.html")
    return "/" + rel


def article_chars(html: str) -> int:
    m = PROSE_RE.search(html)
    body = m.group(1) if m else html
    return len(re.sub(r"\s+", " ", TAG_RE.sub(" ", body)).strip())


def main() -> int:
    arg = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    # The kit is answered before anything is sniffed. It is a platform
    # repository: it has no registry, no Mindestumfang and nothing to claim.
    if arg == KIT or KIT in arg.parents:
        print("C4 n/a — the kit publishes no Sprachwerke and registers no marks.")
        return 0
    repo, public = locate(arg)
    if not public.is_dir():
        # Not a pass. C4 reads rendered prose, so an unbuilt site is a gate
        # that cannot run, and the battery counts those as failures in CI.
        print(f"::error::{public} does not exist — C4 reads rendered prose and "
              f"must run after `hugo`. Reporting zero uncovered pages from an "
              f"unbuilt site is the vacuous pass this battery exists to remove.",
              file=sys.stderr)
        return 2

    cfg = config(repo)
    registered, source = registry_urls(repo, cfg)
    # Per-course navigation surfaces, on top of the org-wide statutory list.
    extra = tuple(str(x) for x in (cfg.get("hub_exclusions") or ()))
    ineligible = ineligible_urls(repo)

    uncovered: list[tuple[str, int]] = []
    long_pages = examined = 0
    for f in sorted(public.rglob("*.html")):
        head = f.read_text(encoding="utf-8", errors="ignore")[:2000]
        if ALIAS_RE.search(head):
            continue
        url = page_url(f, public)
        if url == "/" or PAGINATOR_RE.search(url) or is_mark_forbidden(url):
            continue
        if url in extra or any(e != "/" and url.startswith(e) for e in extra):
            continue
        if url in ineligible:
            continue
        examined += 1
        n = article_chars(f.read_text(encoding="utf-8", errors="ignore"))
        if n < THRESHOLD:
            continue
        long_pages += 1
        if url not in registered:
            uncovered.append((url, n))

    where = source.relative_to(repo) if source else "no registry file"
    print(f"C4 — {examined} mark-eligible page(s) examined, {long_pages} over "
          f"the {THRESHOLD}-character Mindestumfang, {len(registered)} mark(s) "
          f"in {where}, {len(ineligible)} page(s) ineligible by page_type")
    if not examined:
        print(f"::error::C4 examined no pages under {public}. Every page was a "
              f"navigation surface or an alias, which is not a state any course "
              f"in this org is in.", file=sys.stderr)
        return 2
    if not long_pages:
        # Distinct from "all covered". A scaffold with no long-form page yet has
        # nothing to claim; saying "every page carries a mark" of zero pages is
        # the vacuous phrasing of a true statement.
        print("  no page clears the Mindestumfang yet — nothing to claim")
        return 0
    if not uncovered:
        print("  covered: all {} page(s) over the floor carry a mark".format(long_pages))
        return 0

    print(f"  UNCOVERED: {len(uncovered)} — long-form pages earning nothing")
    for url, n in sorted(uncovered)[:30]:
        print(f"::warning::{url} — {n} characters, over the Mindestumfang, no mark")
    if len(uncovered) > 30:
        print(f"  …and {len(uncovered) - 30} more")
    print("\nRegister each through the VG Wort T.O.M. portal and add the code to "
          "the registry. Until then these pages are written and earning nothing.")
    # Non-zero so the battery prints `warn`. gates.yml holds the severity; a
    # script that decides its own by returning 0 has overruled the register.
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
