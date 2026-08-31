#!/usr/bin/env python3
"""Assert no gate is reachable from one entry point and not the other.

    python scripts/test_battery_drift.py

`kit check` claims that passing locally means passing in CI. That claim is only
true while CI runs exactly the battery and adds nothing of its own — so this
test reads the course workflow template and fails if it contains gate logic.

The claim matters more than it sounds. Every one of the nine
`continue-on-error` suppressions this organisation accumulated began with
somebody unable to reproduce a CI failure locally. A gate that can only be run
by pushing is a gate that eventually gets switched off, and the switch is
always described as temporary.

The second half of the file tests the *other* direction of the same claim: that
the battery starts at all in the shape CI actually builds. From 2026-08-22 the
register defaulted the org root to the kit's parent, which is the checkout root
locally and the course root in CI, so it looked for `.github/scripts/` inside
the course and found the course's own workflow directory. Every gate in the org
stopped running for eight days and every local run stayed green, because
locally the guess was right. So the CI shape is built here — kit at `.kit`,
curriculum at `.curriculum`, no siblings — and asserted three ways: unmapped
fails, correctly mapped passes, wrongly mapped fails. A register that has been
wrong in CI while passing locally is exactly the thing that needs a test
standing in the CI shape rather than in this one.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
TEMPLATE = KIT / "templates" / "deploy.yml"
REGISTER = KIT / "scripts" / "verify_gate_register.py"

# Anything that looks like a check being run in the workflow rather than in the
# battery. `uses:` a reusable workflow is fine; running a verifier is not.
SMELLS = [
    (re.compile(r"python .*verify_", re.I), "runs a verifier directly"),
    (re.compile(r"pa11y|pagefind|lychee", re.I), "runs a gate tool directly"),
    (re.compile(r"continue-on-error", re.I), "suppresses a failure"),
    (re.compile(r"\|\|\s*true"), "swallows a non-zero exit"),
]


# ── the CI shape ────────────────────────────────────────────────────────────
def ci_shape(tmp: Path) -> tuple[Path, Path, Path]:
    """A course checkout as the reusable workflow lays it out.

    `.kit` is a real directory holding this working tree's `gates.yml` and
    `scripts/`, copied fresh on every run. It must not be a symlink: the
    register locates itself with `Path(__file__).resolve()`, which follows
    links, so a symlinked kit would put `KIT.parent` back at the developer's
    checkout root — where `.github` and `curriculum` really are siblings — and
    the unmapped case would pass. That is the bug wearing the test's clothes.

    The course also gets a `.github/workflows/deploy.yml` of its own, because
    every real course has one and it is the decoy the probe has to see through.
    """
    course = tmp / "course"
    (course / "content").mkdir(parents=True)
    (course / ".kit" / "scripts").mkdir(parents=True)
    shutil.copy2(KIT / "gates.yml", course / ".kit" / "gates.yml")
    for f in (KIT / "scripts").iterdir():
        if f.is_file():
            shutil.copy2(f, course / ".kit" / "scripts" / f.name)

    decoy = course / ".github" / "workflows" / "deploy.yml"
    decoy.parent.mkdir(parents=True)
    decoy.write_text("# the course's own caller, not the org repository\n",
                     encoding="utf-8")

    # Stand-ins for the two non-kit owners, at the paths CI checks them out to.
    # Only the script paths gates.yml names have to exist; what is in them is
    # not this test's business.
    for owner, script in ((".curriculum", "scripts/conformance_audit.py"),
                          (".github-org", "scripts/kit_drift.py")):
        f = course / owner / script
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("# stand-in\n", encoding="utf-8")

    # The org repo's workflows, because the register now verifies that a gate's
    # `runs:` claim naming a workflow is true of that workflow — B2 and E1 both
    # name course-build.yml. In real CI this file is checked out with the rest
    # of `.github`; a fixture that omits it is not the CI shape, and the first
    # version of this one said the battery could not start when in fact only
    # the stand-in was thin.
    wf = course / ".github-org" / ".github" / "workflows" / "course-build.yml"
    wf.parent.mkdir(parents=True, exist_ok=True)
    wf.write_text((KIT.parent / ".github" / ".github" / "workflows" /
                   "course-build.yml").read_text(encoding="utf-8")
                  if (KIT.parent / ".github" / ".github" / "workflows" /
                      "course-build.yml").exists()
                  else "# stand-in caller\n", encoding="utf-8")
    return course, course / ".github-org", course / ".curriculum"


def register_in(course: Path, *mappings: str) -> tuple[int, str]:
    r = subprocess.run([sys.executable, str(course / ".kit" / "scripts" /
                                            "verify_gate_register.py"), *mappings],
                       capture_output=True, text=True, cwd=course)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def test_register_in_ci_shape() -> int:
    """Three cases. The middle one is the fix; the outer two are why it stays."""
    bad = 0
    with tempfile.TemporaryDirectory() as td:
        course, org_github, curric = ci_shape(Path(td))

        rc, out = register_in(course)
        if rc == 0:
            print("::error::the register passed in the CI shape with no "
                  "--owner-root. It located `.github` and `curriculum` by "
                  "guessing, which is the defect, not the fix.")
            bad += 1
        elif "kit_drift.py does not exist" in out:
            print("::error::the register saw the course's own `.github/` and "
                  "accepted it, then blamed a missing script. A name match is "
                  "not an identity — this is the 2026-08-22 failure exactly.")
            bad += 1
        elif "has no checkout" not in out:
            print(f"::error::the register failed unmapped, but not because an "
                  f"owner was unlocated. A missing checkout must not be "
                  f"reported as a missing script: {out.strip()[:200]}")
            bad += 1

        rc, out = register_in(course,
                              "--owner-root", f".github={org_github}",
                              "--owner-root", f"curriculum={curric}")
        if rc != 0:
            print(f"::error::the register failed in the CI shape with correct "
                  f"mappings — CI cannot run the battery: {out.strip()[:400]}")
            bad += 1

        rc, _ = register_in(course,
                            "--owner-root", f".github={curric}",
                            "--owner-root", f"curriculum={curric}")
        if rc == 0:
            print("::error::the register passed with `.github` mapped at the "
                  "curriculum checkout. A mapping that is accepted without "
                  "being checked is the guess again, wearing a flag.")
            bad += 1

    print(f"  register: 3 CI-shape cases, {3 - bad} as specified")
    return bad


def test_caller_passes_owner_roots() -> int:
    """`kit check` in the caller must carry the mappings, or the register will
    guess again the moment somebody re-reads this file and thinks the flag is
    optional."""
    wf = KIT.parent / ".github" / ".github" / "workflows" / "course-build.yml"
    if not wf.exists():
        print(f"  reusable workflow not checked out at {wf} — skipped")
        return 0
    text = wf.read_text(encoding="utf-8")
    bad = 0
    for owner in (".github", "curriculum"):
        if f"--owner-root {owner}=" not in text:
            print(f"::error::course-build.yml runs `kit check` without "
                  f"--owner-root {owner}=…. In CI that owner is not a sibling "
                  f"of the kit and the battery will not start.")
            bad += 1
    if bad == 0:
        print("  reusable workflow passes both owner roots")
    return bad


def main() -> int:
    if not TEMPLATE.exists():
        print(f"::error::{TEMPLATE} is missing", file=sys.stderr)
        return 1
    text = TEMPLATE.read_text(encoding="utf-8")
    bad = 0
    for i, line in enumerate(text.split("\n"), 1):
        if line.lstrip().startswith("#"):
            continue
        for pat, why in SMELLS:
            if pat.search(line):
                print(f"::error file=templates/deploy.yml,line={i}::{why} — gates "
                      f"belong in `kit check`, not in the workflow. Adding one here "
                      f"breaks the local/CI equivalence the battery depends on: "
                      f"{line.strip()[:60]}")
                bad += 1
    body = [l for l in text.split("\n")
            if l.strip() and not l.lstrip().startswith("#")]
    print(f"  caller is {len(body)} non-comment lines")
    if bad:
        print(f"\ndrift FAIL — {bad} gate(s) live in the workflow", file=sys.stderr)
        return 1
    print("drift OK — the workflow calls the battery and adds nothing")

    shape = test_register_in_ci_shape() + test_caller_passes_owner_roots()
    if shape:
        print(f"\nCI-shape FAIL — {shape} problem(s). The battery would not "
              f"start in CI.", file=sys.stderr)
        return 1
    print("CI shape OK — the battery starts where CI puts the checkouts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
