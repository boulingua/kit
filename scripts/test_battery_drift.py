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
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
TEMPLATE = KIT / "templates" / "deploy.yml"

# Anything that looks like a check being run in the workflow rather than in the
# battery. `uses:` a reusable workflow is fine; running a verifier is not.
SMELLS = [
    (re.compile(r"python .*verify_", re.I), "runs a verifier directly"),
    (re.compile(r"pa11y|pagefind|lychee", re.I), "runs a gate tool directly"),
    (re.compile(r"continue-on-error", re.I), "suppresses a failure"),
    (re.compile(r"\|\|\s*true"), "swallows a non-zero exit"),
]


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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
