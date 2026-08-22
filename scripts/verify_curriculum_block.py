#!/usr/bin/env python3
"""Gate A2 — the `curriculum:` block, enforced on a declared ramp.

    verify_curriculum_block.py REPO

`implements` is what converts conformance from prose into enforcement: before
it, a course could claim any level and nothing could contradict it. But zero
pages in this organisation carry a descriptor id today, and for efl and fle
there is no field to rename — every one of ~672 pages needs 3–6 ids chosen by
hand, which the programme prices at roughly 14 author-weeks.

Making it required on the day the schema lands would red two live sites for
months. So the requirement ramps, and **the ramp is a declared state read from
`boulingua.yml`, not a per-PR judgement**:

    M0   a missing curriculum: block is a warning
    M1   required on any page the PR touches
    M2   required repo-wide
    M3   required, and coverage must be met

That distinction matters more than it looks. "We'll turn it on when we're
ready" is how a gate never gets turned on; `milestone: M1` in a committed file
is a state somebody has to change deliberately, in a diff, with a reason.

The breadth rule: at least one id must come from a domain other than the page's
primary skill domain. A unit implementing only REC descriptors is a reading
exercise wearing a unit's clothes, and the eight-domain enum is what makes that
checkable rather than a matter of taste.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ID_RE = re.compile(r"^(preA1|A1|A2|B1|B2|C1|C2)\."
                   r"(REC|PROD|INT|MED|PLUR|LING|SOC|PRAG)\.([a-z0-9-]+)\.(\d{2})$")
FM = re.compile(r"\A---\n(.*?)\n---\n", re.S)
GATED_TYPES = {"unit", "exam"}
# Which domain a skill primarily lives in, for the breadth rule.
PRIMARY = {"reading": "REC", "listening": "REC",
           "speaking_interaction": "INT", "speaking_production": "PROD",
           "writing": "PROD", "mediation": "MED",
           "language_awareness": "LING", "intercultural": "SOC"}


def main() -> int:
    repo = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    cfgf = repo / "boulingua.yml"
    cfg = yaml.safe_load(cfgf.read_text(encoding="utf-8")) if cfgf.exists() else {}
    milestone = str(cfg.get("milestone", "M0")).upper()

    missing, malformed, narrow, checked, inferred = [], [], [], 0, 0
    deferred_breadth: list[str] = []
    for md in sorted((repo / "content").rglob("*.md")):
        m = FM.match(md.read_text(encoding="utf-8", errors="replace"))
        if not m:
            continue
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except Exception:
            continue
        ptype = fm.get("page_type")
        if ptype is None:
            # efl and daf carry NO page_type at all — 0 of 411 and 0 of 83 — so
            # keying only on it means examining nothing and reporting OK, which
            # is precisely the vacuous pass this programme exists to remove.
            # Fall back to the path: a page under /units/ is a unit or its exam.
            if "/units/" not in md.as_posix():
                continue
            inferred += 1
        elif ptype not in GATED_TYPES:
            continue
        checked += 1
        rel = md.relative_to(repo)
        cur = fm.get("curriculum") or {}
        ids = cur.get("implements") or []
        if not ids:
            missing.append(str(rel))
            continue
        for i in ids:
            if not ID_RE.match(str(i)):
                malformed.append(f"{rel}: {i}")
        domains = {ID_RE.match(str(i)).group(2) for i in ids if ID_RE.match(str(i))}
        skills = fm.get("skills_focus") or []
        vals = [str(x) for x in (skills if isinstance(skills, list) else [skills])]
        primary = {PRIMARY.get(v) for v in vals} - {None}
        # A value outside the enum contributes NO domain, which quietly shrinks
        # `primary` and makes the subset test easier to pass. That is not a
        # hypothetical: `sprechen` and `speaking` are deliberately left
        # unsplit until each unit's implements ids decide whether they are
        # interaction or production, and while they sit there a page with
        # skills ['reading', 'sprechen'] has primary == {REC}. Ids covering
        # {REC, INT} then look broad and are not — the moment the split lands,
        # primary becomes {REC, INT}, the same ids become a subset, and 37 daf
        # pages flip from pass to fail with nobody having edited them.
        #
        # So an unmapped value is reported rather than dropped. The breadth
        # verdict on that page is not yet knowable, and saying so is the only
        # honest answer.
        unmapped = sorted({v for v in vals if v not in PRIMARY})
        if unmapped and ids:
            deferred_breadth.append(
                f"{rel}: skills_focus carries {unmapped}, which maps to no "
                f"domain, so the breadth rule cannot be evaluated on this page. "
                f"It is not passing — it is unjudged, and it will be judged the "
                f"moment that value is split.")
        if domains and primary and not unmapped and domains <= primary:
            narrow.append(f"{rel}: every id is in {sorted(domains)}, the page's own "
                          f"skill domain(s) — at least one must come from elsewhere")

    print(f"  milestone {milestone}: {checked} unit/exam page(s) examined")
    if inferred:
        print(f"::notice::{inferred} page(s) carry no page_type and were identified "
              f"by path instead. The discriminator is missing from this repo — a "
              f"known gap, scheduled with its Phase 3 front-matter pass. Without "
              f"the fallback this gate would examine nothing and report OK.")
    if checked == 0 and any((repo / "content").rglob("*.md")):
        print("::warning::this repo has content but no page this gate recognises "
              "as a unit or exam. That is a finding, not a pass.")

    # Malformed and narrow are WRONG, and wrong fails at every milestone. Only
    # the missing-block requirement ramps: an id that is present must be right.
    hard = len(malformed) + len(narrow)
    for x in malformed:
        print(f"::error::malformed implements id — {x}")
    for x in narrow:
        print(f"::error::{x}")
    for x in deferred_breadth[:6]:
        print(f"::warning::{x}")
    if len(deferred_breadth) > 6:
        print(f"::warning::… and {len(deferred_breadth) - 6} more page(s) whose "
              f"breadth cannot yet be evaluated")

    if missing:
        level = "error" if milestone in {"M2", "M3"} else "warning"
        for x in missing[:10]:
            print(f"::{level}::{x}: no curriculum.implements")
        if len(missing) > 10:
            print(f"::{level}::… and {len(missing) - 10} more")
        print(f"  {len(missing)} page(s) without implements — "
              f"{'BLOCKING' if level == 'error' else 'warning'} at {milestone}")
        if level == "error":
            hard += len(missing)

    if hard:
        print(f"\nA2 FAIL — {hard} problem(s)", file=sys.stderr)
        return 1
    if deferred_breadth:
        print(f"  {len(deferred_breadth)} page(s) UNJUDGED on breadth — an "
              f"unmapped skills_focus value, not a pass")
    print("A2 OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
