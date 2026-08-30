#!/usr/bin/env python3
"""Where each gate owner is checked out. One answer, given rather than derived.

`gates.yml` names three owners — `kit`, `.github` and `curriculum` — and a
gate's scripts live in its owner's repository. Something has to turn an owner
name into a directory, and until 2026-08-30 that something was `KIT.parent`.

That works locally, where the checkout root holds every repo as a sibling, and
it cannot work in CI, where the reusable workflow puts the kit *inside* the
course at `.kit` and curriculum at `.curriculum`, and did not check `.github`
out at all. `KIT.parent` became the course root, so the register looked for
`<course>/.github/scripts/kit_drift.py` — the course's own workflow directory —
and for `<course>/curriculum/...` while the checkout sat at `.curriculum`.
Neither existed, the register exited 1, and it does so *before* the battery is
built. Between 2026-08-22 and 2026-08-30 no gate examined any site in this
organisation and nothing deployed.

The defect was not the wrong default. It is that a derived path always yields
*a* path, so a missing answer arrives disguised as a missing file — and in a log
those two read very differently. One says "somebody deleted kit_drift.py", which
is false and sends you into `.github`; the other says "nobody told me where
`.github` is", which is true and takes a line of YAML to fix.

So, three rules:

  - a caller that knows the layout states it       ``--owner-root NAME=PATH``
  - a sibling is used only when it *is* that owner — see below
  - an owner nobody located is a hard error that names the owner

The second rule cannot be "the directory exists", and this is the part worth
reading twice. **Every course repository contains a `.github/` directory** — its
own `workflows/deploy.yml`. So in CI the sibling probe finds `<course>/.github`,
finds it present, accepts it, and then reports `kit_drift.py does not exist`:
the original misleading message, now produced by the code that was meant to
remove it. A name is not an identity.

A checkout is therefore accepted as an owner only when it holds the scripts
`gates.yml` says that owner provides. That is not a heuristic marker file — it
is the exact property the caller is about to depend on, so a probe that passes
cannot be followed by a join that fails.

`kit` is never mapped. It is the tree this file lives in, and that is the one
root that cannot be got wrong.
"""
from __future__ import annotations

from pathlib import Path

KIT = Path(__file__).resolve().parent.parent

#: Owners that are repositories in their own right. `kit` is resolved from this
#: file's location and is deliberately absent from the mappable set.
MAPPABLE = {".github", "curriculum"}


class CheckoutError(ValueError):
    """A malformed --owner-root. Raised at parse time, never swallowed."""


def parse_owner_root(arg: str) -> tuple[str, Path]:
    """Parse one ``NAME=PATH``. The path is resolved but not required to exist —
    existence is checked in `resolve_owners`, so a wrong mapping and an absent
    mapping produce different messages."""
    name, sep, path = arg.partition("=")
    name, path = name.strip(), path.strip()
    if not sep or not name or not path:
        raise CheckoutError(
            f"--owner-root expects NAME=PATH, got {arg!r}. "
            f"Example: --owner-root .github=.github-org")
    if name == "kit":
        raise CheckoutError(
            "--owner-root kit=... is refused. The kit is located from the "
            "running script, so a mapping could only ever disagree with it.")
    if name not in MAPPABLE:
        raise CheckoutError(
            f"--owner-root {name}=... names no owner in gates.yml. "
            f"Mappable owners: {', '.join(sorted(MAPPABLE))}")
    return name, Path(path).resolve()


def owners_needing_a_root(gates: list[dict]) -> dict[str, list[str]]:
    """``{owner: [script, ...]}`` for every owner a register check or a battery
    run will have to locate — those naming at least one script that is not
    `kit:`-prefixed — with the scripts themselves, which are what identifies the
    checkout.

    E1 owns nothing on disk and must not force a `.github` checkout on a course
    that has no other reason for one."""
    needed: dict[str, list[str]] = {}
    for g in gates:
        owner = g.get("owner")
        if owner == "kit" or not owner:
            continue
        for spec in g.get("scripts") or []:
            if not str(spec).startswith("kit:"):
                needed.setdefault(owner, [])
                if spec not in needed[owner]:
                    needed[owner].append(str(spec))
    return needed


def is_checkout_of(root: Path, scripts: list[str]) -> bool:
    """True if `root` holds every script `gates.yml` attributes to that owner.

    The test is deliberately the strongest one available rather than a marker
    file: the caller's very next act is to join these paths, so anything weaker
    would let a probe pass and the join fail.
    """
    return root.is_dir() and all((root / s).exists() for s in scripts)


def resolve_owners(needed: dict[str, list[str]],
                   overrides: dict[str, Path] | None = None,
                   org: Path | str | None = None) -> tuple[dict[str, Path], list[str]]:
    """Map every needed owner to a directory.

    Returns ``(roots, problems)``. `problems` is a list of complete sentences
    ready to print; an owner that appears there is absent from `roots`, so a
    caller must check for membership rather than assume the map is total.

    An explicit mapping is taken at its word beyond existing as a directory: if
    it is wrong the per-gate check reports precisely which script is missing,
    which is the right message for a mapping somebody typed. Only the *probe*
    has to prove identity, because nobody typed it.
    """
    overrides = dict(overrides or {})
    org = Path(org).resolve() if org is not None else KIT.parent
    roots: dict[str, Path] = {"kit": KIT}
    problems: list[str] = []

    for owner, scripts in sorted(needed.items()):
        if owner == "kit":
            continue
        if owner in overrides:
            root = overrides[owner]
            if root.is_dir():
                roots[owner] = root
            else:
                problems.append(
                    f"--owner-root {owner}={root} is not a directory. The "
                    f"mapping is wrong, not missing: check the `path:` the "
                    f"workflow gave actions/checkout for {owner}.")
            continue

        sibling = org / owner
        if is_checkout_of(sibling, scripts):
            roots[owner] = sibling
            continue

        why = (f"{sibling} exists but holds none of "
               f"{', '.join(scripts)} — that is not the {owner} repository"
               if sibling.is_dir() else
               f"{sibling} does not exist")
        problems.append(
            f"owner {owner!r} has no checkout: probed a sibling of the kit and "
            f"{why}, and no --owner-root {owner}=… was given. In CI the owners "
            f"are not siblings of the kit — check the repository out and pass "
            f"its path. Note that every course repo has a `.github/` directory "
            f"of its own, so a name match here proves nothing; guessing from "
            f"one is what stopped the whole battery for eight days.")
    return roots, problems


def describe(roots: dict[str, Path]) -> str:
    """One line per owner, for the log. A run that cannot be read afterwards
    cannot be debugged afterwards, and this map is the thing you want first."""
    return "\n".join(f"  {owner:12s} {path}"
                     for owner, path in sorted(roots.items()))
