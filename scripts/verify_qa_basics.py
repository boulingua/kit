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
from urllib.parse import unquote, urlparse

PAGE_N = re.compile(r'(?:^|/)page/\d+$')

# The repo under test is an ARGUMENT, never this script's own location.
#
# These gates lived inside the repo they checked, so `Path(__file__).parent.parent`
# was that repo. Promoted into the kit it is the KIT — so the gate would have
# walked kit/static/, found nothing, and reported success about a course it
# never looked at. That is the same defect F7 removed from the generators
# (SITE = REPO.name), and it is worth restating: a shared tool must be told
# what it is operating on.
# The argument is the BUILT SITE, not the repo. Appending "public" to it —
# which these did — makes the gate unrunnable in any repo that builds
# elsewhere, and "no site found" then reads as a failure of the build
# rather than of the gate. The kit itself builds to build/site.
ARG = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
PUBLIC = ARG if (ARG / "index.html").exists() else ARG / "public"
REPO = ARG


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
            # This compared against a hard-coded "~80+", a number carried over
            # from the one repo the check was written in. A threshold borrowed
            # from another site's page count is not a check of THIS site: it
            # fails a small course for being small and passes a large one whose
            # sitemap lost half its pages. The invariant is the join — every
            # built page is listed, and nothing is listed that was not built.
            # An alias is a meta-refresh stub Hugo writes for an old URL. It
            # is correctly absent from the sitemap and must not be demanded
            # here — daf alone has 80 of them, efl 405. The same detection
            # matters elsewhere for a harder reason: an alias stub carries no
            # VG Wort pixel, which is the open question in docs/vgwort-
            # operations.md.
            built = set()
            for q in PUBLIC.rglob("index.html"):
                head = q.read_text(encoding="utf-8", errors="replace")[:1200]
                if 'http-equiv="refresh"' in head or "http-equiv='refresh'" in head:
                    continue
                built.add("" if q.parent == PUBLIC
                          else q.parent.relative_to(PUBLIC).as_posix().strip("/"))
            raw = []
            for u in urls:
                loc = u.find("sm:loc", ns)
                if loc is not None and loc.text:
                    # Non-ASCII in a URL is percent-encoded in the sitemap and
                    # is not in the directory name. daf's /tags/modul-hören/ was
                    # reported missing purely because of the ö.
                    raw.append(unquote(urlparse(loc.text).path).strip("/"))
            # A site published under a path baseURL — which every GitHub Pages
            # project site is — lists /<project>/about/ while the built tree
            # holds about/. Comparing them raw marks every page missing, which
            # is a gate that fails loudest on the sites it understands least.
            # The homepage entry carries the prefix, so take it from there.
            prefix = min(raw, key=len) if raw else ""
            listed = {r[len(prefix):].strip("/") if prefix and r.startswith(prefix)
                      else r for r in raw}
            if not urls:
                err("sitemap.xml lists no URLs at all"); failures += 1
            # /section/page/1/ is Hugo's paginated first page — byte-identical
            # to /section/ and correctly absent from the sitemap. It is the same
            # category of surface C3 forbids a VG Wort mark on, for the same
            # reason: it is a duplicate of a page that already exists.
            built = {b for b in built if not PAGE_N.search(b)}
            missing = sorted(built - listed - {""})
            if missing:
                for m in missing[:8]:
                    err(f"sitemap.xml omits a built page: /{m}/")
                if len(missing) > 8:
                    err(f"… and {len(missing) - 8} more")
                failures += 1
            print(f"  sitemap.xml: {len(urls)} URLs, {len(built)} built page(s), "
                  f"{len(missing)} omitted")

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
