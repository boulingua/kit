#!/usr/bin/env python3
"""Gates C3 and C5 — a registered mark must actually load, on a page that may carry one.

    verify_pixel_delivery.py BUILT_SITE

A2 and C2 prove a mark is present in the HTML. Present is not the same as
loaded, and VG Wort counts a request, not a tag. Every failure below produces a
page that looks correct in a diff, renders correctly in a browser, and earns
nothing:

  loading="lazy" on the pixel. The single most expensive attribute in this
  codebase. A 1×1 image positioned off-screen is exactly what a lazy loader
  declines to fetch, so the mark is on the page and never requested.

  A display:none ancestor. Browsers skip fetching images inside a
  display:none subtree. visibility:hidden and off-screen positioning still
  load, which is why the pixel partial uses those.

  Script injection. A mark that appears only after JavaScript runs is a mark
  that does not exist for a reader with JS off, and it is not what was
  registered.

  More than one eager pixel, or a preload that names a different code than the
  body img. Two requests for one work is not two payments; a mismatch means one
  of them is wrong and nothing says which.

C3 is the other half: a mark on a page that must never carry one. Navigation
surfaces, paginated continuations and the three templated legal notices are not
the author's Sprachwerke, and a mark there is a registration that cannot be
defended if it is ever questioned.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PIXEL = re.compile(r"met\.vgwort\.de/na/([0-9a-f]{32})")
IMG = re.compile(r"<img\b[^>]*met\.vgwort\.de[^>]*>", re.I)
PRELOAD = re.compile(r"<link\b[^>]*rel=[\"']?preload[\"']?[^>]*met\.vgwort\.de[^>]*>", re.I)
ALIAS = re.compile(r"""http-equiv\s*=\s*["']?refresh""", re.I)
LAZY = re.compile(r"loading\s*=\s*[\"']?lazy", re.I)
DISPLAY_NONE = re.compile(r"display\s*:\s*none", re.I)

FORBIDDEN = ("impressum", "datenschutz", "haftungsausschluss", "disclaimer",
             "privacy", "imprint", "mentions-legales", "tags", "categories",
             "materials", "materiel", "materialien")


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path("public")
    if not root.is_dir():
        print(f"::error::{root} does not exist — build first", file=sys.stderr)
        return 2

    bad, marked, checked = [], 0, 0
    for f in sorted(root.rglob("index.html")):
        html = f.read_text(encoding="utf-8", errors="replace")
        if ALIAS.search(html[:2000]):
            continue
        checked += 1
        codes = set(PIXEL.findall(html))
        if not codes:
            continue
        marked += 1
        rel = "/" + f.parent.relative_to(root).as_posix() + "/" if f.parent != root else "/"

        # ── C3: pages that must never carry a mark ────────────────────────
        segs = [s for s in rel.strip("/").split("/") if s]
        if any(s in FORBIDDEN for s in segs):
            bad.append(f"{rel}: carries a mark, and this is a navigation or legal "
                       f"surface. Those are not the author's Sprachwerke — a "
                       f"registration here cannot be defended if it is questioned.")
        if re.search(r"/page/\d+/$", rel):
            bad.append(f"{rel}: a paginated continuation carries a mark. It is a "
                       f"duplicate of a page that already has one.")
        if rel == "/":
            bad.append("/: the home page carries a mark — it is navigation")

        # ── C5: delivery shape ────────────────────────────────────────────
        imgs = IMG.findall(html)
        if not imgs:
            bad.append(f"{rel}: the code appears but no <img> requests it. VG Wort "
                       f"counts a request, not a tag.")
        for tag in imgs:
            if LAZY.search(tag):
                bad.append(f"{rel}: loading=\"lazy\" on the counting pixel. A 1x1 "
                           f"image positioned off-screen is exactly what a lazy "
                           f"loader declines to fetch — the mark is on the page and "
                           f"is never requested.")
        if len(imgs) > 1:
            bad.append(f"{rel}: {len(imgs)} pixel <img> tags. Two requests for one "
                       f"work is not two payments.")
        if len(codes) > 1:
            bad.append(f"{rel}: {len(codes)} distinct codes on one page")

        # A display:none ANCESTOR stops the fetch; the pixel's own
        # visibility:hidden does not, which is why the partial uses it.
        for m in IMG.finditer(html):
            before = html[max(0, m.start() - 400):m.start()]
            if DISPLAY_NONE.search(before) and "visibility" not in before[-120:]:
                bad.append(f"{rel}: the pixel sits inside a display:none subtree, "
                           f"which browsers do not fetch. visibility:hidden and "
                           f"off-screen positioning still load.")
                break

        pre = PRELOAD.findall(html)
        if len(pre) > 1:
            bad.append(f"{rel}: {len(pre)} preloads for the pixel")
        for p in pre:
            pc = set(PIXEL.findall(p))
            if pc and pc != codes:
                bad.append(f"{rel}: the head preload names {pc} and the body img "
                           f"names {codes} — one of them is wrong and nothing here "
                           f"says which")

        if re.search(r"met\.vgwort\.de[^\"']*[\"']\s*\)?\s*;", html) and not imgs:
            bad.append(f"{rel}: the pixel looks script-injected. A mark that needs "
                       f"JavaScript does not exist for a reader with it off.")

    for b in bad[:20]:
        print(f"::error::{b}")
    if len(bad) > 20:
        print(f"::error::… and {len(bad) - 20} more")
    print(f"  {checked} page(s) examined, {marked} carrying a mark")
    if bad:
        print(f"\nC3/C5 FAIL — {len(bad)} problem(s)", file=sys.stderr)
        return 1
    if marked == 0:
        print("C3/C5 OK — this site carries no marks; nothing to deliver wrongly")
        return 0
    print(f"C3/C5 OK — {marked} marked page(s): one eager pixel each, no lazy "
          f"loading, no display:none ancestor, none on a navigation or legal surface")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
