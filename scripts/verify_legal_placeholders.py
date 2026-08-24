"""Gates A5 and C7 — no placeholder ships, in source or in the rendered page.

    verify_legal_placeholders.py REPO --source     A5
    verify_legal_placeholders.py BUILT_SITE        C7

Two modes because they catch different mistakes. C7 reads the three rendered
legal pages and is the last line: whatever reaches a reader has no ⟨…⟩ in it.
A5 reads the source tree and is the useful one, because it names the file to
edit instead of a URL to trace back.

The org shipped this check for a year in the Quarto era and then again in Hugo,
and both times it was suppressed with `|| true` in CI — not out of carelessness
but because the shared template legitimately contains ⟨…⟩ and there was nowhere
to say so. A gate with no way to express a legitimate exception gets switched
off, every time. So the exceptions are declared in placeholder-exceptions.yml,
each with a reason, a `filled_by`, and an `expect` list that is itself checked:
a template that has been filled makes its own exception stale, and a stale
exception fails. That is the difference between an exception and a suppression.
""" 
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# The argument is the BUILT SITE, not the repo. Appending "public" to it —
# which these did — makes the gate unrunnable in any repo that builds
# elsewhere, and "no site found" then reads as a failure of the build
# rather than of the gate. The kit itself builds to build/site.
ARG = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT
PUBLIC = ARG if (ARG / "index.html").exists() else ARG / "public"

# Slugs, not URLs, discovered at any depth. The hardcoded
# ("/impressum/", "/datenschutz/", "/haftungsausschluss/") assumed a German
# monolingual site rooted at /. ressources is de/en/fr with its notices at
# /de/impressum/, /en/disclaimer/, /fr/mentions-legales/ — so the gate found
# none of them, reported three pages missing, and examined nothing. A gate
# that cannot find the pages it checks is not stricter than one that can.
ALIAS_RE = re.compile(r"""http-equiv\s*=\s*["']?refresh""", re.I)

LEGAL_SLUGS = ("impressum", "imprint", "mentions-legales",
               "datenschutz", "privacy", "confidentialite",
               "haftungsausschluss", "disclaimer", "avertissement")
EXCEPTIONS = ROOT / "placeholder-exceptions.yml"


def exceptions() -> dict[str, list[str]]:
    """path -> expected placeholder fragments, from the declared list."""
    if not EXCEPTIONS.exists():
        return {}
    import yaml
    doc = yaml.safe_load(EXCEPTIONS.read_text(encoding="utf-8")) or {}
    return {t["path"]: t.get("expect", []) for t in doc.get("templates", [])}


def scan_source(repo: Path) -> int:
    """A5 — the source tree, where the fix actually is."""
    allowed = exceptions()
    bad, stale, checked = [], [], 0
    roots = [d for d in (repo / "content", repo / "example", repo / "layouts",
                         repo / "i18n") if d.is_dir()] or [repo]
    for f in sorted(x for r in roots for x in r.rglob("*")
                    if x.suffix in {".md", ".html", ".yaml", ".yml", ".toml"}):
        rel = f.relative_to(repo).as_posix()
        try:
            body = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        checked += 1
        if rel in allowed:
            # The exception is only valid while it is still needed.
            present = [e for e in allowed[rel] if e in body]
            if not present:
                stale.append(rel)
            continue
        for needle in PLACEHOLDERS:
            if needle in body:
                bad.append(f"{rel}: placeholder {needle!r}")
    for x in bad:
        print(f"::error::{x}")
    for x in stale:
        print(f"::error::{x}: listed in placeholder-exceptions.yml but contains "
              f"none of its `expect` fragments — it has been filled, so remove "
              f"the exception. A list that outlives its reason is a suppression")
    if bad or stale:
        print(f"\nA5 FAIL — {len(bad) + len(stale)} problem(s)", file=sys.stderr)
        return 1
    print(f"A5 OK — {checked} source file(s), {len(allowed)} declared template "
          f"exception(s), all still needed")
    return 0

# Forbidden placeholder strings — any survival of these in a rendered
# legal page indicates the page was shipped before its template was
# filled in.
PLACEHOLDERS = (
    "{{CONTACT_EMAIL_HELLER}}",
    "{{CONTACT_EMAIL_LEBOULANGER}}",
    "{{SITE_DOMAIN}}",
    "{{NAME}}",
    "{{ADDRESS}}",
    "[NAME]",
    "[ADDRESS]",
    "Lorem ipsum",
    "<TODO:",
    "<FIXME:",
    "[STUB]",
    "[TBD]",
    "⟨",  # angle-bracket template placeholders, e.g. ⟨NAME⟩ — must be filled
)
# Markers that should never appear inside a legal page (case-sensitive
# to avoid false positives on the literal word "TODO list" etc., but
# we still match TODO / FIXME as standalone tokens).
MARKERS_RE = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b")


def main() -> int:
    if "--source" in sys.argv:
        return scan_source(ARG)
    if not PUBLIC.is_dir():
        print(f"GATE FAIL: {PUBLIC} missing — "
              f"run `hugo --minify` first.", file=sys.stderr)
        return 2

    # The kit's own example site renders the three legal TEMPLATES, so C7 must
    # honour the same declared exception A5 does — but only for the kit's own
    # build. The scope test is that PUBLIC sits inside the kit; a course's
    # rendered legal pages come from the course's own content and can never
    # reach this branch, however its build directory is named. An exception
    # that could follow the template into a course would be the bug, not the
    # feature.
    # Waive the DECLARED FRAGMENTS, never the page. The first version of this
    # skipped any page with an exception, which left C7 examining nothing at all
    # in the kit and printing OK — the same vacuous pass this gate was rewritten
    # to remove, reintroduced by its own exception mechanism. TODO markers,
    # Lorem ipsum and any placeholder nobody declared still fail on these pages.
    in_kit = PUBLIC.is_relative_to(ROOT)
    waived = {Path(k).stem: set(v) for k, v in exceptions().items()} if in_kit else {}

    violations: list[tuple[str, str]] = []
    waived_n: dict[str, int] = {}
    pages: list[tuple[str, Path]] = []
    for f in sorted(PUBLIC.rglob("index.html")):
        if f.parent.name not in LEGAL_SLUGS:
            continue
        head = f.read_text(encoding="utf-8", errors="replace")[:2000]
        if ALIAS_RE.search(head):
            continue        # a meta-refresh stub for an old URL, not a page
        rel = "/" + f.parent.relative_to(PUBLIC).as_posix() + "/"
        pages.append((rel, f))
    if not pages:
        print(f"::error::no legal page found anywhere under {PUBLIC}. Every site "
              f"in this organisation publishes a statutory notice; finding none "
              f"is a failure of the site, or of this slug list — either way it "
              f"is not a pass.", file=sys.stderr)
        return 1

    for url, page in pages:
        body = page.read_text(encoding="utf-8")
        allow = waived.get(url.strip("/"), set())
        for needle in PLACEHOLDERS:
            if needle not in body:
                continue
            # A declared fragment is waived only where the whole surviving
            # placeholder is one of the declared ones. "⟨" matches anything in
            # angle brackets, so waiving the bare needle would waive an
            # undeclared placeholder that happens to sit on the same page.
            found = set(re.findall(r"⟨[^⟩]{0,80}⟩", body)) if needle == "⟨" else set()
            if needle == "⟨":
                undeclared = [f for f in found
                              if not any(f.startswith(a.rstrip("⟩")) for a in allow)]
                for f in undeclared:
                    violations.append((url, f"undeclared placeholder: {f}"))
                if allow and not undeclared:
                    waived_n[url] = len(found)
                continue
            if needle in allow:
                waived_n[url] = waived_n.get(url, 0) + 1
                continue
            violations.append((url, f"placeholder present: {needle}"))
        for m in MARKERS_RE.finditer(body):
            violations.append((url, f"marker present: {m.group(0)}"))

    if violations:
        print(f"GATE FAIL: {len(violations)} legal-page placeholder/marker "
              f"violation(s):", file=sys.stderr)
        for url, why in violations:
            print(f"  {url}: {why}", file=sys.stderr)
        return 1

    extra = ""
    if waived_n:
        extra = ("; " + ", ".join(f"{u} {n} declared template fragment(s) waived"
                                  for u, n in sorted(waived_n.items()))
                 + " — the exception does not travel to a course")
    print(f"C7 OK — {len(pages)} legal page(s) found and checked, no undeclared placeholders, "
          f"no TODO/FIXME markers{extra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
