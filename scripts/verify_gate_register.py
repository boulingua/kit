#!/usr/bin/env python3
"""The register checks itself.

    python scripts/verify_gate_register.py [ORG_ROOT]

`gates.yml` is the single definition of every check in this organisation, and a
register is only worth having while it agrees with the disk. The failure it
exists to prevent is not a typo — it is the register slowly becoming a wish
list, where an ID reads `status: live` because it was live when somebody wrote
the line.

So this asserts the joins, in both directions:

  register -> disk   a live or partial gate's scripts exist
  disk -> register   every verify_*.py in the kit is claimed by some gate

The second direction is the one that catches real drift. An unclaimed script is
either a gate nobody registered or a gate that was replaced and left behind,
and both were found in this repo the first time this ran: verify_kit_lock.py
called itself A5, which is legal placeholders, and verify_js_budget.py called
itself C13, which is lychee. Two scripts, two wrong IDs, both self-declared in
their own docstrings and therefore invisible to anything but a cross-check.

The bookkeeping rules are the same idea applied to the fields:

  warn without `ramp`      a suppression wearing a gate's clothes
  partial without `gap`    a hole in the battery nobody can see
  planned without `booked` a gate that will never be written
  live but not in the      a check that runs somewhere unnamed, which is
  battery and no `runs`    how a gate stops running without anyone noticing

None of these are style rules. Each is one of the four ways this organisation
has already lost a gate.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

KIT = Path(__file__).resolve().parent.parent
ID_RE = re.compile(r"^(A[1-9]\d?|B[1-4]|C1[0-5]|C[1-9]|D[1-6]|E1)$")
STATUS = {"live", "partial", "planned", "withdrawn"}
SEVERITY = {"blocking", "warn"}
NEEDS = {"source", "built", "materials", "audio", "none"}
OWNERS = {"kit", ".github", "curriculum"}

# Scripts in kit/scripts that are not gates and are not expected to be claimed.
NOT_A_GATE = {
    "blg_paths.py", "build_graph.py", "build_materials_latex.py",
    "normalise_skills.py", "pdf_attribution.py", "vgwort_lock.py",
    "verify_gate_register.py",
}


def resolve(spec: str, owner: str, org: Path) -> Path:
    if spec.startswith("kit:"):
        return KIT / spec[4:]
    root = KIT if owner == "kit" else org / owner
    return root / spec


def main() -> int:
    org = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else KIT.parent
    reg = yaml.safe_load((KIT / "gates.yml").read_text(encoding="utf-8"))
    gates = reg["gates"]
    bad: list[str] = []
    claimed: set[str] = set()
    seen: set[str] = set()

    for g in gates:
        gid = g.get("id", "?")
        where = f"gates.yml[{gid}]"
        if not ID_RE.match(str(gid)):
            bad.append(f"{where}: not a valid gate id")
        if gid in seen:
            bad.append(f"{where}: duplicate id — ids are permanent and never reused")
        seen.add(gid)

        for field, allowed in (("status", STATUS), ("severity", SEVERITY),
                               ("needs", NEEDS), ("owner", OWNERS)):
            if g.get(field) not in allowed:
                bad.append(f"{where}: {field}={g.get(field)!r} outside {sorted(allowed)}")

        st, sev = g.get("status"), g.get("severity")

        if sev == "warn" and not str(g.get("ramp", "")).strip():
            bad.append(f"{where}: severity warn with no `ramp`. A gate that warns "
                       f"with no stated route to blocking is a permanent "
                       f"suppression — say what turns it on, or make it blocking")
        if st == "partial" and not str(g.get("gap", "")).strip():
            bad.append(f"{where}: status partial with no `gap`. Name what the ID "
                       f"promises that the script does not do, or the battery has "
                       f"a hole that reads as coverage")
        if st == "planned":
            if not str(g.get("booked", "")).strip():
                bad.append(f"{where}: status planned with no `booked` phase")
            if g.get("scripts"):
                bad.append(f"{where}: status planned but names scripts")
            if g.get("battery"):
                bad.append(f"{where}: status planned but battery: true — "
                           f"`kit check` would invoke a script that does not exist")

        for spec in g.get("scripts") or []:
            p = resolve(spec, g["owner"], org)
            if st in {"live", "partial"} and not p.exists():
                bad.append(f"{where}: {spec} does not exist ({p})")
            if p.is_relative_to(KIT):
                claimed.add(p.name)

        if st in {"live", "partial"} and not g.get("battery") \
                and not str(g.get("runs", "")).strip():
            bad.append(f"{where}: runs neither in the battery nor anywhere named. "
                       f"Set battery: true or say where it runs in `runs`")

    for p in sorted((KIT / "scripts").glob("verify_*.py")):
        if p.name in NOT_A_GATE or p.name in claimed:
            continue
        bad.append(f"scripts/{p.name}: no gate in the register claims this script. "
                   f"Either it is an unregistered gate or it was superseded and "
                   f"left behind — both have happened here")

    for b in bad:
        print(f"::error::{b}")
    if bad:
        print(f"\ngate register FAIL — {len(bad)} problem(s)", file=sys.stderr)
        return 1
    n = len(gates)
    live = sum(1 for g in gates if g["status"] == "live")
    part = sum(1 for g in gates if g["status"] == "partial")
    plan = sum(1 for g in gates if g["status"] == "planned")
    print(f"gate register OK — {n} ids: {live} live, {part} partial, {plan} planned")
    print(f"  {plan} planned gates each name the phase that delivers them")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
