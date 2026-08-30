#!/usr/bin/env python3
"""
vgwort_audit.py — flag long-form content (>=1800 chars body, post
shortcode/HTML strip) that has no VG Wort Zählmarke registered.

Looks for a token in:
  1. per-page frontmatter (`vgwort_pixel:` or `vgwort:`)
  2. a registry entry whose `url` matches the page's URL

That second line said `path` until now, and **no registry in this
organisation has ever had a path field**. daf, efl and fle key all 821
entries by `url:`, so the lookup returned an empty dict on every course
and every registered page counted as unregistered. It never showed,
because the walk was rooted at the kit and there were no pages to count.
Two independent faults, each of which alone would have been visible, and
together produced a clean zero.

The URL comes from blg_paths.url_key — the same resolver A3 and C2 use.
Deriving it here from the directory name would be a fourth slug
namespace, and the reason that module exists is that the org already
lost marks to exactly that shortcut.

Emits ::warning:: on every miss so the CI run shows them. Does NOT
fail the build — registration is async (you can't generate a
Zählmarke from CI) — and `severity: warn` in gates.yml is what
arranges that. Exit non-zero when something is flagged, so the battery
renders the gate as `warn`; "exit 0 always" predates the register and
made the severity field inert, printing `ok` beside the findings.

    python scripts/vgwort_audit.py REPO

**REPO is an argument and has to be.** This script derived it from
`__file__`, so it walked `kit/content` — a directory that does not
exist — while standing in a course. `rglob` over nothing yields
nothing, so it printed `0 unregistered long-form page(s); 0 pages
skipped` and returned 0, identically, for daf with 60 units and efl
with 360. That is not a gate reporting a wrong number. It is a gate
that has never run, reporting the number a clean repo would produce,
which is the one output nobody investigates.

C4 next door had the same `__file__` root and at least crashed loudly
about it. Exit 0 always is what made this one invisible for a year, and
it is why the count of *pages examined* is now printed on every run: a
gate with nothing to look at must not be able to look green.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blg_paths import is_mark_forbidden, url_key  # noqa: E402

KIT = Path(__file__).resolve().parent.parent
MIN_CHARS = 1800

FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)
SHORTCODE_RE = re.compile(r"\{\{[<%].*?[>%]\}\}", re.S)
HTML_TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def registry_path(repo: Path) -> Path:
    """The registry the course declares, falling back to the org default.

    daf's boulingua.yml says `registry: vgwort/marks.yaml` and its marks are in
    `data/vgwort.yaml`. Nothing read the field, so nothing noticed. Read it —
    and fall back rather than fail, because a declaration that points at
    nothing must not stop the audit that would have found the real file."""
    declared = None
    cfg = repo / "boulingua.yml"
    if cfg.exists():
        doc = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
        declared = (doc.get("vgwort") or {}).get("registry")
    if declared and (repo / declared).exists():
        return repo / declared
    return repo / "data" / "vgwort.yaml"


def load_registry(data: Path) -> dict[str, dict]:
    """Keyed by url. `path` is still accepted so a course that adopts the
    field is not silently unmatched, but nothing in the org uses it today."""
    if not data.exists():
        return {}
    raw = yaml.safe_load(data.read_text(encoding="utf-8"))
    if not raw or not isinstance(raw, list):
        return {}
    out: dict[str, dict] = {}
    for e in raw:
        for field in ("url", "path"):
            if e.get(field):
                out[str(e[field])] = e
    return out


def body_chars(md_text: str) -> int:
    body = FM_RE.sub("", md_text, count=1)
    body = SHORTCODE_RE.sub(" ", body)
    body = HTML_TAG_RE.sub(" ", body)
    body = WS_RE.sub(" ", body)
    return len(body.strip())


def main() -> int:
    repo = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    content = repo / "content"
    if repo == KIT or not content.is_dir():
        # Not "nothing to flag" — nothing to look at. The two used to print the
        # same line.
        print(f"C1 n/a — {repo} has no content/ directory to audit.")
        return 0

    data = registry_path(repo)
    registry = load_registry(data)
    flagged = 0
    skipped = 0
    examined = 0
    for md in sorted(content.rglob("*.md")):
        rel = md.relative_to(repo).as_posix()
        # Don't audit hub/list pages.
        if md.name == "_index.md":
            skipped += 1
            continue
        if rel.startswith("content/materials/"):
            skipped += 1
            continue
        text = md.read_text(encoding="utf-8")
        m = FM_RE.match(text)
        fm = yaml.safe_load(m.group(1)) if m else {}
        url = url_key(md, content, fm or {})
        # C3 fails a mark found on one of these. Asking for one here would be
        # this gate instructing the author to break that one.
        if is_mark_forbidden(url):
            skipped += 1
            continue
        examined += 1
        if (fm or {}).get("vgwort_pixel") or (fm or {}).get("vgwort"):
            continue
        if url in registry or rel in registry:
            continue
        chars = body_chars(text)
        if chars >= MIN_CHARS:
            print(f"::warning file={rel}::{chars} chars >= {MIN_CHARS} but no VG Wort Zählmarke registered")
            flagged += 1

    print(f"\nvgwort_audit: {examined} page(s) examined, {len(registry)} "
          f"registry entr(ies) from {data.relative_to(repo)}, "
          f"{flagged} unregistered long-form page(s), "
          f"{skipped} skipped (lists/hub).")
    return 1 if flagged else 0


if __name__ == "__main__":
    sys.exit(main())
