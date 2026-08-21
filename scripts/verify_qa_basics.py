#!/usr/bin/env python3
"""
verify_qa_basics.py — Phase-7 sanity gate. Confirms the rendered
site has the standard infrastructure files and that they look
sane:

  /sitemap.xml          present, contains every published page
  /index.xml            (Hugo RSS for site root) present, parses,
                        contains items
  /robots.txt           present, doesn't accidentally Disallow: /
  /404.html             present and styled (non-empty body)

Exits 1 on any structural failure with file-pathed ::error::
messages.
"""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# The repo under test is an ARGUMENT, never this script's own location.
#
# These gates lived inside the repo they checked, so `Path(__file__).parent.parent`
# was that repo. Promoted into the kit it is the KIT — so the gate would have
# walked kit/static/, found nothing, and reported success about a course it
# never looked at. That is the same defect F7 removed from the generators
# (SITE = REPO.name), and it is worth restating: a shared tool must be told
# what it is operating on.
REPO = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
PUBLIC = REPO / "public"


def err(msg: str) -> None:
    print(f"::error::{msg}", file=sys.stderr)


def main() -> int:
    failures = 0

    sitemap = PUBLIC / "sitemap.xml"
    if not sitemap.exists():
        err("public/sitemap.xml missing"); failures += 1
    else:
        try:
            root = ET.fromstring(sitemap.read_text(encoding="utf-8"))
        except ET.ParseError as e:
            err(f"sitemap.xml parse error: {e}"); failures += 1
        else:
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            urls = root.findall("sm:url", ns)
            if len(urls) < 50:
                err(f"sitemap.xml has only {len(urls)} URLs (expected ~80+)"); failures += 1
            else:
                print(f"  sitemap.xml: {len(urls)} URLs")

    rss = PUBLIC / "index.xml"
    if not rss.exists():
        err("public/index.xml (RSS) missing"); failures += 1
    else:
        try:
            root = ET.fromstring(rss.read_text(encoding="utf-8"))
        except ET.ParseError as e:
            err(f"index.xml parse error: {e}"); failures += 1
        else:
            items = root.findall(".//item")
            if not items:
                err("index.xml has zero <item>"); failures += 1
            else:
                print(f"  index.xml: {len(items)} items")

    robots = PUBLIC / "robots.txt"
    if not robots.exists():
        err("public/robots.txt missing"); failures += 1
    else:
        body = robots.read_text(encoding="utf-8")
        if re.search(r"^Disallow:\s*/\s*$", body, re.M):
            err("robots.txt has 'Disallow: /' — entire site blocked from crawl"); failures += 1
        else:
            print(f"  robots.txt: {len(body)} bytes, no full-site Disallow")

    notfound = PUBLIC / "404.html"
    if not notfound.exists():
        err("public/404.html missing"); failures += 1
    else:
        body = notfound.read_text(encoding="utf-8")
        if len(body) < 500:
            err(f"404.html is {len(body)} bytes — likely unstyled"); failures += 1
        else:
            print(f"  404.html: {len(body)} bytes")

    print(f"\nverify_qa_basics: {failures} failure(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
