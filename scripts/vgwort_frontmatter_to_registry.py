#!/usr/bin/env python3
"""Move VG Wort marks out of page front matter and into the registry.

    vgwort_frontmatter_to_registry.py REPO [--built DIR] --plan
    vgwort_frontmatter_to_registry.py REPO [--built DIR] --apply

A mark in front matter works — the kit's resolver reads `vgwort_pixel:` before
it reads the registry, deliberately, as a back-compat path. What it is not is a
registry. You cannot ask 349 pages a question; there is no single place that
says which marks this course holds, so nothing can audit them, C1 has to walk
the whole content tree to count them, and a mark is orphaned by any edit that
touches the file it lives in.

**THE MAPPING IS MEASURED.** Every URL here is read from the BUILT site by
finding which page actually renders that pixel today. Deriving the URL from the
content path instead would be a fourth slug convention and this organisation has
already lost marks to exactly that shortcut: fle carries 312 front-matter `slug:`
overrides, none of them recoverable from a filename.

The refusal conditions are the point of the script. It will not apply while:

  - a front-matter code renders on no page — it is registered and earning
    nothing today, and converting it would file that failure as a fact;
  - a code renders on more than one page — VG Wort treats one mark as one work,
    and the duplicate has to be resolved before the key is frozen;
  - the URL set or the code set would change across the move. That is checked
    by comparison, not by argument, and it is the whole safety property: the
    same codes on the same URLs, in a different file.

The author on an entry comes from the page's front matter, and failing that
from the site's `params.author` — the same order Hugo uses to fill
`<meta name="author">` and therefore the same answer gate C8 has been checking
against all along. 156 of fle's marked unit pages declare no author of their own
and render S. Le Boulanger from the site config; refusing them would be this
script disagreeing with the page it is reading.

`registered_at` is written as the sentinel `unknown-pre-programme`, per ADR-0015
and ADR-0019. fle's 349 dates exist in no repository — they are in T.O.M. and
nowhere else — and inventing one from the lock's `first_seen` would record the
day this org first looked at the mark as the day VG Wort issued it. C1 stays
warn for fle until the export backfills them, which ADR-0020 already says.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blg_paths import url_key  # noqa: E402

PIXEL_RE = re.compile(r"met\.vgwort\.de/na/([0-9a-f]{32})")
BARE_RE = re.compile(r"\b([0-9a-f]{32})\b")
ALIAS_RE = re.compile(r"""http-equiv\s*=\s*["']?refresh""", re.I)
FM_RE = re.compile(r"\A---\n(.*?\n)---\n", re.S)
FM_MARK_RE = re.compile(r"(?m)^(?:vgwort_pixel|vgwort):[^\n]*\n")
SENTINEL = "unknown-pre-programme"


def built_index(built: Path) -> dict[str, list[str]]:
    """code -> [url, ...], read from the rendered HTML. Aliases are skipped:
    a meta-refresh stub carries no pixel and counting it as a second page for
    the same code would make every mark look like a duplicate."""
    idx: dict[str, list[str]] = defaultdict(list)
    for f in sorted(built.rglob("index.html")):
        html = f.read_text(encoding="utf-8", errors="replace")
        if ALIAS_RE.search(html[:2000]):
            continue
        url = ("/" + f.parent.relative_to(built).as_posix() + "/"
               if f.parent != built else "/")
        for code in sorted(set(PIXEL_RE.findall(html))):
            idx[code].append(url)
    return idx


def site_author(repo: Path) -> str | None:
    """`params.author` from hugo.toml, which is what Hugo renders into
    <meta name="author"> for a page that declares none."""
    f = repo / "hugo.toml"
    if not f.exists():
        return None
    m = re.search(r'(?m)^\s*author\s*=\s*"([^"]+)"', f.read_text(encoding="utf-8"))
    return m.group(1) if m else None


def code_of(value: str) -> str | None:
    m = PIXEL_RE.search(str(value)) or BARE_RE.search(str(value))
    return m.group(1) if m else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--built", default=None)
    ap.add_argument("--registry", default="data/vgwort.yaml")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--plan", action="store_true")
    g.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    repo = Path(a.repo).resolve()
    built = Path(a.built).resolve() if a.built else repo / "public"
    content = repo / "content"
    reg_path = repo / a.registry
    if not built.is_dir():
        print(f"::error::{built} does not exist. The mapping is read from the "
              f"built site and cannot be derived — build first.", file=sys.stderr)
        return 2

    fallback_author = site_author(repo)
    idx = built_index(built)
    rendered_before = {c: sorted(u) for c, u in idx.items()}

    existing = yaml.safe_load(reg_path.read_text(encoding="utf-8")) if reg_path.exists() else []
    existing = existing or []
    known_urls = {str(e["url"]) for e in existing if e.get("url")}

    moves, problems = [], []
    for md in sorted(content.rglob("*.md")):
        text = md.read_text(encoding="utf-8")
        m = FM_RE.match(text)
        if not m:
            continue
        fm = yaml.safe_load(m.group(1)) or {}
        raw = fm.get("vgwort_pixel") or fm.get("vgwort")
        if not raw:
            continue
        rel = md.relative_to(content).as_posix()
        code = code_of(raw)
        if not code:
            problems.append(f"{rel}: front matter carries {raw!r}, which holds no "
                            f"32-hex code. Nothing can be moved from it.")
            continue
        urls = idx.get(code, [])
        if len(urls) == 0:
            problems.append(f"{rel}: code {code} renders on no page. It is "
                            f"registered and earning nothing today; converting it "
                            f"would record that as a fact.")
            continue
        if len(urls) > 1:
            problems.append(f"{rel}: code {code} renders on {len(urls)} pages "
                            f"({', '.join(urls)}). VG Wort treats one mark as one "
                            f"work — resolve the duplicate before re-keying.")
            continue
        url = urls[0]
        derived = url_key(md, content, fm)
        if derived != url:
            # Reported, never corrected. The built site is the authority; a
            # divergence means url_key and Hugo disagree about this page, which
            # is worth knowing and is not this script's to decide.
            problems.append(f"{rel}: renders at {url} but url_key says {derived}. "
                            f"The resolver and the build disagree; fix that before "
                            f"freezing a key on either.")
            continue
        if url in known_urls:
            problems.append(f"{rel}: {url} already has a registry entry, and this "
                            f"page also carries the mark in front matter.")
            continue
        moves.append({
            "md": md, "rel": rel, "url": url, "code": code,
            "author": fm.get("author") or fallback_author,
            "inherited": not fm.get("author"),
        })

    print(f"{len(moves)} mark(s) to move, {len(existing)} already in "
          f"{reg_path.relative_to(repo)}, {len(problems)} problem(s)")
    for p in problems:
        print(f"::error::{p}")
    if problems:
        print("\nNothing moved. Every one of these is a mark that would be "
              "silently mis-filed.", file=sys.stderr)
        return 1
    if not moves:
        print("  nothing in front matter — the registry is already the registry")
        return 0

    no_author = [m["rel"] for m in moves if not m["author"]]
    if no_author:
        print(f"::error::{len(no_author)} page(s) carry a mark and neither the "
              f"page nor hugo.toml names an author. A registry entry names the "
              f"person the mark is registered to; it cannot be left blank.",
              file=sys.stderr)
        for r in no_author[:10]:
            print(f"    {r}", file=sys.stderr)
        return 1
    inherited = sum(1 for m in moves if m["inherited"])
    if inherited:
        print(f"  {inherited} entr(ies) take the author from hugo.toml "
              f"({fallback_author!r}) — the same value those pages already "
              f"render into <meta name=\"author\">")

    new = [{
        "url": m["url"],
        "public_id": m["code"],
        "pixel_url": f"https://vg09.met.vgwort.de/na/{m['code']}",
        "min_chars": 1800,
        "author": m["author"],
        "registered_at": SENTINEL,
    } for m in moves]

    if a.plan:
        for m in moves[:10]:
            print(f"  {m['rel']}  ->  {m['url']}  {m['code']}")
        if len(moves) > 10:
            print(f"  … and {len(moves) - 10} more")
        print(f"\nplan only. --apply writes {len(new)} entries and removes the "
              f"front-matter line from {len(moves)} page(s).")
        return 0

    merged = sorted(existing + new, key=lambda e: str(e["url"]))
    header = ""
    if reg_path.exists():
        head = reg_path.read_text(encoding="utf-8").split("\n")
        header = "\n".join(l for l in head[:40] if l.startswith("#"))
        if header:
            header += "\n"
    reg_path.parent.mkdir(parents=True, exist_ok=True)
    reg_path.write_text(header + yaml.safe_dump(merged, sort_keys=False,
                                                allow_unicode=True, width=1000),
                        encoding="utf-8")
    for m in moves:
        text = m["md"].read_text(encoding="utf-8")
        fmm = FM_RE.match(text)
        stripped = FM_MARK_RE.sub("", fmm.group(1))
        m["md"].write_text(text[:fmm.start(1)] + stripped + text[fmm.end(1):],
                           encoding="utf-8")

    print(f"\napplied: {len(new)} entries written, {len(moves)} front-matter "
          f"line(s) removed. {len(merged)} marks now in "
          f"{reg_path.relative_to(repo)}.")
    print("REBUILD AND COMPARE. The move is only proved by the rendered pixel "
          "set being identical, and this script has not rebuilt anything.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
