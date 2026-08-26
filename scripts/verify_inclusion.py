#!/usr/bin/env python3
"""Gate A15 — sourcing, and the cast data that does not exist yet.

    verify_inclusion.py REPO

EQS §5.5 asks for four things: no undeclared speaker, no gender share above
60%, no cast fact contradicted between units, and no culture window without a
source. Two of the four are checkable against what these repos hold. Two are
not, and saying which is which is most of what this gate is for.

CHECKABLE NOW

  A unit that presents cultural or factual claims carries a sources section.
  Each course names it in its own language — "Sources", "Quellen", "Sources et
  références", and efl still calls it "Further reading / listening" — so the
  aliases are listed rather than one spelling imposed, because failing 360
  units over a heading word would say nothing about their sourcing.

  Speaker names in a unit's transcripts are used consistently. A dialogue that
  introduces Lena and then answers as Lena. is a typo the reader trips over and
  nothing else catches.

NOT CHECKABLE, AND NOT FAKEABLE

  Gender share needs a declared cast with declared genders. No repo in this
  organisation has one: the audio manifests carry file, label and transcript,
  and nothing else. Inferring gender from a first name would be unreliable in
  German and French and inappropriate in any language, so this reports the
  absence instead of manufacturing a number. The fix is a cast declaration, and
  that is authoring work.

  Cast fact contradiction needs the same declaration — you cannot notice that
  Lena is fourteen in one unit and sixteen in another without somewhere that
  says how old Lena is.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

FM = re.compile(r"\A---\n(.*?)\n---\n", re.S)
SPEAKER = re.compile(r"^([A-ZÄÖÜÉÈÀ][\wäöüßéèàâçîô-]{1,20}):", re.M)
SOURCES = ("sources", "quellen", "sources et références", "sources et references",
           "further reading", "further reading / listening", "weiterführendes",
           "quellen und weiterführendes", "références")


def main() -> int:
    repo = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    bad, units, sourced = [], 0, 0

    for md in sorted((repo / "content").rglob("*.md")):
        raw = md.read_text(encoding="utf-8")
        m = FM.match(raw)
        if not m:
            continue
        fm = yaml.safe_load(m.group(1)) or {}
        if fm.get("page_type") != "unit":
            continue
        units += 1
        rel = md.relative_to(repo).as_posix()
        heads = [h.strip().lower().rstrip(".")
                 for h in re.findall(r"(?m)^#{2,3}\s+(.+?)\s*$", raw[m.end():])]
        if any(any(s in h for s in SOURCES) for h in heads):
            sourced += 1
        else:
            bad.append(f"{rel}: no sources section. A unit presenting cultural or "
                       f"factual content without one asks a learner to take it on "
                       f"trust.")

    # Speaker consistency, from the transcripts where the names actually live.
    cast: dict[str, Counter] = defaultdict(Counter)
    manifests = sorted((repo / "data" / "audio").glob("*.json"))
    for f in manifests:
        try:
            segs = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(segs, list):
            continue
        for s in segs:
            for name in SPEAKER.findall(str(s.get("transcript", ""))):
                cast[f.stem][name] += 1
    for unit, names in sorted(cast.items()):
        low = defaultdict(list)
        for n in names:
            low[n.lower()].append(n)
        for k, v in low.items():
            if len(set(v)) > 1:
                bad.append(f"data/audio/{unit}.json: the same speaker is written "
                           f"{sorted(set(v))} in one unit")

    for b in bad[:15]:
        print(f"::error::{b}")
    if len(bad) > 15:
        print(f"::error::… and {len(bad) - 15} more")

    speakers = sum(len(v) for v in cast.values())
    print(f"  {units} unit(s); {sourced} carry a sources section")
    print(f"  {len(manifests)} audio manifest(s), {speakers} named speaker "
          f"appearance(s) across them")
    print(f"::notice::gender share and cast-fact consistency are NOT checked. "
          f"They need a declared cast with declared attributes and no repo here "
          f"has one — the audio manifests carry file, label and transcript only. "
          f"Inferring gender from a first name would be unreliable and is not "
          f"something this gate will manufacture. EQS 5.5 is half-enforced until "
          f"a cast declaration exists.")
    if bad:
        print(f"\nA15 FAIL — {len(bad)} problem(s)", file=sys.stderr)
        return 1
    print("A15 OK — every unit carries a sources section, speaker names consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
