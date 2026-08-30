#!/usr/bin/env python3
"""The path, slug and site-code contract. Imported by every generator and gate.

There are FOUR slug namespaces in this organisation and they are not
interchangeable. One `slug()` helper would be wrong in a way that costs money,
so this module exposes four named accessors and never one.

Taken from a single real `efl` unit:

    bundle directory   unit06-interview-and-portrait          <- THE URL
    material_slug      track-e_kl09_unit06-interview-and-portrait
    unit_slug          interview-and-portrait
    aliases            /track_e_kl09/units/unit06_...html     <- historical

In `efl` the material slug has no relationship to the URL: renaming it renames
a PDF and orphans nothing, while renaming the bundle directory orphans a
registered VG Wort mark and leaves the material slug untouched. `fle` splits
differently again — its file stem is the material slug and a front-matter
`slug:` is the URL — and `daf` is the only repo where the names coincide, which
is exactly why code written against `daf` breaks on the other two.

    url_key(page)        RelPermalink       VG Wort, url-lock, gates A3 and C2
    material_slug(page)  front matter       PDF filenames, thumbnails
    unit_slug(page)      front matter       editorial cross-references
    audio_slug(page)     = material_slug    data/audio/<slug>.json

**Gate A3 keys on url_key and never on material_slug** (C8). A gate watching
the wrong name is worse than no gate, because it reports green while a mark is
being orphaned.

Nothing here derives the site code from a directory name. `SITE = REPO.name`
meant a clone into ~/work/efl-main/ baked `/efl-main/` into 360 front-matter
URLs, and running a generator inside the template emitted `\\blgsetlang{pagegen}`
— an undefined colour, and a LaTeX error only if you were lucky.
"""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

import yaml

FM_RE = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.S)
CODE_RE = re.compile(r'^\s*code\s*=\s*"([^"]+)"', re.M)
BASEURL_RE = re.compile(r'^\s*baseURL\s*=\s*"([^"]+)"', re.M)
# The material slug is recoverable from an already-written material URL. This
# regex is what preserved both slug conventions through the .odp -> .pdf
# migration, so it stays; what does not stay is guessing from a directory name.
MATERIAL_URL_RE = re.compile(r'/materials?/(?:presentations|worksheets|fiches)/([^/"\']+?)\.(?:pdf|png|odp|pptx)')

EXAM_RE = re.compile(r"[-_]exam$")

# ── The surfaces that must never carry a mark ───────────────────────────────
# One definition, imported by C3 (which fails a mark found on one), by C1 and
# by C4 (which must not ask for a mark to be registered on one). Those gates
# have to agree: a coverage gate that reports /datenschutz/ as unregistered is
# instructing the author to do the thing C3 blocks, and whichever of the two
# they believe, the other one is lying to them.
#
# Slugs and not URLs, at any depth, in the four chrome languages the org
# ships — ressources alone puts its notices at /de/impressum/,
# /en/disclaimer/ and /fr/mentions-legales/.
MARK_FORBIDDEN_SLUGS = (
    "impressum", "imprint", "mentions-legales",
    "datenschutz", "privacy", "confidentialite",
    "haftungsausschluss", "disclaimer", "avertissement",
    "tags", "categories",
    "materials", "materiel", "materialien",
)


# ── The page types that may carry a mark ────────────────────────────────────
# A18/C6 fails a mark held by anything else; C4 must not ask for one there.
# Shared for the same reason as the list above: the two gates are a pair, and a
# pair that disagrees leaves the author holding two instructions and no way to
# satisfy both.
MARK_ELIGIBLE_PAGE_TYPES = frozenset({"unit", "exam", "reference", "appendix"})


def is_mark_forbidden(url: str) -> bool:
    """True if `url` names a navigation or statutory surface. Takes a URL and
    splits it, so a slug matches at any depth and never as a substring —
    `/anhaenge/glossar-privacy-hinweise/` is a Sprachwerk, not a privacy page."""
    return any(s in MARK_FORBIDDEN_SLUGS
               for s in (x for x in url.strip("/").split("/") if x))


# ── C7: one exam predicate, applied to a slug and never to a path ───────────
def is_exam(slug: str) -> bool:
    """True if `slug` names an exam page.

    Takes a SLUG. The `$` anchor is deliberate and it is also the trap:
    is_exam("content/.../unit01_ma-rentree_exam.md") is False, because the
    string ends in ".md". Callers must strip the extension — which is why
    is_exam_page() below exists and why nothing should use this directly.
    """
    return bool(EXAM_RE.search(slug))


def is_exam_page(md_path: Path | str) -> bool:
    """True if the file at `md_path` is an exam page. Handles both content
    models: a leaf bundle is named by its directory, a flat file by its stem."""
    p = Path(md_path)
    return is_exam(p.parent.name if p.name == "index.md" else p.stem)


# ── C1-C3: the site code is declared, asserted, never derived ───────────────
class SiteError(RuntimeError):
    pass


def site_code(repo: Path, override: str | None = None) -> str:
    """Read `code` from hugo.toml. No default, ever.

    make_icon.py defaulted to "efl" when the key was absent, which is the same
    failure class: a wrong value that looks like a working build ships another
    course's identity.
    """
    if override:
        return override
    for name in ("hugo.toml", "hugo.defaults.toml", "config.toml"):
        cfg = repo / name
        if cfg.exists():
            m = CODE_RE.search(cfg.read_text(encoding="utf-8"))
            if m:
                return m.group(1)
            raise SiteError(f"{cfg} has no [params] code key — declare it or pass --site")
    raise SiteError(f"no hugo config in {repo}")


def assert_site(repo: Path, code: str, accents: Path | None = None) -> None:
    """C2 and C3. Both catch a wrong code before XeLaTeX or Hugo sees it."""
    cfg = next((repo / n for n in ("hugo.toml", "hugo.defaults.toml") if (repo / n).exists()), None)
    if cfg:
        m = BASEURL_RE.search(cfg.read_text(encoding="utf-8"))
        if m:
            path = urlparse(m.group(1)).path.strip("/")
            # CHANGEME is the template's own placeholder and is not a course.
            if path and path != code and path != "CHANGEME":
                raise SiteError(
                    f"C2: baseURL path {path!r} does not match code {code!r} — "
                    f"one of them is wrong, and a mismatch bakes the wrong prefix "
                    f"into every material URL")
    reg = accents or (repo / "data" / "accents.yaml")
    if reg.exists():
        codes = {a["code"] for a in yaml.safe_load(reg.read_text(encoding="utf-8"))}
        if code not in codes:
            raise SiteError(
                f"C3: code {code!r} is not in {reg.name} — this catches a clone "
                f"directory name or the template's own name before it reaches "
                f"\\blgsetlang and becomes an undefined colour")


# ── front matter ────────────────────────────────────────────────────────────
def front_matter(md_path: Path) -> tuple[dict, str]:
    m = FM_RE.match(Path(md_path).read_text(encoding="utf-8"))
    if not m:
        return {}, ""
    return (yaml.safe_load(m.group(1)) or {}), m.group(2)


# ── C4: the four accessors ──────────────────────────────────────────────────
def url_key(md_path: Path, content_root: Path, fm: dict | None = None) -> str:
    """The URL, as Hugo computes it. THE key for every VG Wort operation.

    Leaf bundles are named by their directory, flat files by their stem, and a
    front-matter `slug:` overrides either — which is what makes fle's
    conversion to leaf bundles URL-neutral, and what makes deleting one of its
    312 slug: lines look like tidying while orphaning a mark.
    """
    p, root = Path(md_path), Path(content_root)
    fm = fm if fm is not None else front_matter(p)[0]
    rel = p.relative_to(root)
    parts = list(rel.parts)
    # BOTH bundle forms map to the containing directory, not to a child of it.
    # index.md is a leaf bundle (a page); _index.md is a branch bundle (a
    # section landing). Treating _index.md as a regular page yields
    # /track-e/kl05/_index/ — a URL that does not exist — and it is 32 of the
    # 821 marked pages across the org, every one of them a section landing.
    if parts[-1] in ("index.md", "_index.md"):
        parts = parts[:-1]
    else:
        parts = parts[:-1] + [Path(parts[-1]).stem]
    if fm.get("slug"):
        parts[-1] = str(fm["slug"])
    return "/" + "/".join(parts) + "/"


def material_slug(md_path: Path, fm: dict | None = None, body: str | None = None) -> str:
    """The PDF/thumbnail filename stem. Required and immutable.

    Read the field. Failing that, recover it from an already-written material
    URL — correct, and how both conventions survived the .odp migration. Failing
    THAT, raise: never fall back to a directory name.

    That fallback is not hypothetical harm. `md_path.parent.name` yields
    `unit06-interview-and-portrait`, but efl's material slug is
    `track-e_kl09_unit06-interview-and-portrait`. Since efl's PDFs are
    git-ignored and regenerated, a front-matter pass firing that fallback would
    silently repoint 360 download links at files the generator will never
    produce under those names.
    """
    p = Path(md_path)
    if fm is None or body is None:
        fm, body = front_matter(p)
    if fm.get("material_slug"):
        return str(fm["material_slug"])
    raw = p.read_text(encoding="utf-8")
    m = MATERIAL_URL_RE.search(raw)
    if m:
        return m.group(1)
    raise SiteError(
        f"{p}: no material_slug and no material URL to recover it from. "
        f"Add `material_slug:` to the front matter — do not let a caller guess, "
        f"because the only available guess is the directory name and in efl "
        f"that is a different string.")


def unit_slug(md_path: Path, fm: dict | None = None) -> str:
    """The editorial name, for cross-references. Not a filename, not a URL."""
    p = Path(md_path)
    fm = fm if fm is not None else front_matter(p)[0]
    if fm.get("unit_slug"):
        return str(fm["unit_slug"])
    if fm.get("slug"):
        return str(fm["slug"])
    return p.parent.name if p.name == "index.md" else p.stem


def audio_slug(md_path: Path, fm: dict | None = None, body: str | None = None) -> str:
    """Where a unit's clips and manifest live. Defaults to the material slug.

    build_audio.py carried a second, subtly different derivation of its own.
    Two derivations of one name is how they drift."""
    return material_slug(md_path, fm, body)
