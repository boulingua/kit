#!/usr/bin/env python3
"""Re-key a VG Wort registry from `path:` to `url:`, by measurement.

    vgwort_rekey.py REPO --plan       show the mapping and what does not map
    vgwort_rekey.py REPO --apply      rewrite data/vgwort.yaml

A `path:` key names the exact source file — `path: content/anhaenge/x.md` — and
the resolver builds its match from `.File.Path`. So the moment a file moves,
including the URL-NEUTRAL move from `x.md` to `x/index.md`, the key stops
matching and the pixel silently stops rendering. The page still exists, at the
same URL, earning nothing. That is why the re-key and the move are one commit:
either alone is a quarter of lost income that no build failure announces.

THE MAPPING IS MEASURED, NOT DERIVED. It would be easy to compute the URL from
the path — strip `content/`, drop `.md`, add slashes — and that is precisely the
reasoning that produces a lock defending URLs nobody checked. Instead this reads
the BUILT site and asks, for each registered code, which page actually renders
that pixel today. The answer comes from the HTML, so a mark whose page was
renamed, deleted, or never carried the pixel at all shows up as unmapped rather
than as a confident wrong guess.

Three outcomes per mark, and the last two are findings:

    exactly one page   -> that URL is the key
    no page            -> dead today. It is registered and earns nothing, and
                          converting it would encode that failure as a fact
    several pages      -> one mark on several URLs, which VG Wort treats as one
                          work; the duplicate must be resolved before re-keying
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

import yaml

# Anchored on the pixel URL, not on "a 32-hex string somewhere on a page that
# also mentions vgwort". The loose form matched asset integrity hashes and
# fingerprinted CSS names on the same pages, reporting 77 codes where the site
# renders 68 — and a collision would have mapped a mark to the wrong URL, which
# is worse than a wrong count.
PIXEL_RE = re.compile(r"met\.vgwort\.de/na/([0-9a-f]{32})")
CODE_RE = re.compile(r"([0-9a-f]{32})")   # for reading the registry's own fields


def built_index(built: Path) -> dict[str, list[str]]:
    """code -> [URL, ...] measured from the rendered HTML."""
    idx: dict[str, list[str]] = defaultdict(list)
    for f in sorted(built.rglob("index.html")):
        html = f.read_text(encoding="utf-8", errors="replace")
        if "met.vgwort.de" not in html:
            continue
        rel = "/" if f.parent == built else "/" + f.parent.relative_to(built).as_posix() + "/"
        for m in set(PIXEL_RE.findall(html)):
            idx[m].append(rel)
    return idx


NON_ASCII = re.compile(r"[^\x00-\x7F]")


def strip_base(url: str, base: str) -> str:
    if base and url.startswith(base):
        url = url[len(base):]
    return "/" + url.strip("/") + "/" if url.strip("/") else "/"


def encode_like_hugo(url: str) -> str:
    """Percent-encode the way .RelPermalink does.

    This is measured from the built directory NAME, which is the decoded form:
    Hugo writes `public/tags/modul-hören/` on disk but .RelPermalink is
    `/tags/modul-h%C3%B6ren/`. The resolver compares `eq .url $rel` against the
    encoded form, so a key taken literally off the filesystem silently never
    matches — the page builds, Hugo warns about nothing, and the pixel is
    absent. daf transliterates its slugs (begruessung, not begrüßung) so no
    mark hits this today, but German course content is exactly where an umlaut
    slug appears next, and `hören` already reaches a URL in this repo's tags.
    """
    return "/".join(quote(seg, safe="") for seg in url.split("/"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("repo", type=Path)
    ap.add_argument("--built", default="public")
    ap.add_argument("--base", default="", help="path baseURL prefix to strip, e.g. /daf")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    repo = a.repo.resolve()
    built = (repo / a.built).resolve()
    reg = repo / "data" / "vgwort.yaml"
    if not built.is_dir():
        print(f"::error::{built} does not exist — build the site first, because "
              f"the mapping is read from the rendered HTML", file=sys.stderr)
        return 2

    entries = yaml.safe_load(reg.read_text(encoding="utf-8")) or []
    idx = built_index(built)
    base = a.base.rstrip("/")

    mapped, dead, dupe, already = [], [], [], []
    for e in entries:
        code = str(e.get("public_id") or "")
        m = CODE_RE.search(code) or CODE_RE.search(str(e.get("pixel_url") or ""))
        code = m.group(1) if m else None
        if e.get("url"):
            already.append(e)
            continue
        urls = idx.get(code or "", [])
        if len(urls) == 1:
            key = strip_base(urls[0], base)
            if NON_ASCII.search(key):
                enc = encode_like_hugo(key)
                print(f"::notice::{key} contains non-ASCII; keyed as {enc} to "
                      f"match .RelPermalink, which is percent-encoded")
                key = enc
            mapped.append((e, key))
        elif not urls:
            dead.append(e)
        else:
            dupe.append((e, urls))

    print(f"  {len(entries)} registered mark(s); {len(idx)} distinct code(s) "
          f"rendered across the built site")
    print(f"  {len(mapped)} mapped to exactly one URL")
    if already:
        print(f"  {len(already)} already url:-keyed, left alone")
    for e in dead:
        print(f"::error::{e.get('path') or e.get('public_id')}: registered but "
              f"renders on NO page — this mark earns nothing today and re-keying "
              f"it would record that as its address")
    for e, urls in dupe:
        print(f"::error::{e.get('path') or e.get('public_id')}: renders on "
              f"{len(urls)} pages ({', '.join(urls[:3])}) — VG Wort counts one "
              f"work per mark; resolve the duplicate before re-keying")

    if a.plan:
        for e, u in mapped[:8]:
            print(f"    {e.get('path')}\n      -> url: {u}")
        if len(mapped) > 8:
            print(f"    … and {len(mapped) - 8} more")

    if dead or dupe:
        print(f"\nrekey FAIL — {len(dead)} dead, {len(dupe)} duplicated; "
              f"nothing written", file=sys.stderr)
        return 1

    if not a.apply:
        print("\nrekey OK (plan) — every mark maps to exactly one rendered URL")
        return 0

    # Rewrite in place, preserving the header comment block and field order.
    head = []
    for line in reg.read_text(encoding="utf-8").splitlines(True):
        if line.startswith("- ") or (line.strip() and not line.startswith("#")):
            break
        head.append(line)
    lookup = {id(e): u for e, u in mapped}
    out = []
    for e in entries:
        u = lookup.get(id(e))
        row = {}
        if u:
            row["url"] = u
        elif e.get("url"):
            row["url"] = e["url"]
        for k, v in e.items():
            if k in ("path", "url"):
                continue
            row[k] = v
        out.append(row)
    body = yaml.dump(out, allow_unicode=True, sort_keys=False, default_flow_style=False)
    reg.write_text("".join(head) + body, encoding="utf-8")
    print(f"\nrekey OK — {len(mapped)} mark(s) re-keyed from path: to url:.")
    print("  Land this BEFORE the file move, as its own commit. A url: key "
          "resolves identically on a flat file and on a bundle, so this commit "
          "is a no-op to the rendered site and the next one is provably safe — "
          "which is two verifiable steps instead of one unverifiable atomic one. "
          "The same-commit rule is for URL-CHANGING work; this changes no URL.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
