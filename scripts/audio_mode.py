#!/usr/bin/env python3
"""Switch a course between audio and transcript-only, reversibly.

    audio_mode.py REPO --transcript-only [--apply]
    audio_mode.py REPO --restore [--apply]

The audio block already degrades correctly: the player is guarded on a `file`
key and the transcript renders whether or not one is present. So a course whose
voice turns out to be unusable can keep every word of its recorded text and
simply stop serving the recordings.

This exists because five voices — including all three with published audio —
were found to descend from a NonCommercial base model. Removing the audio is
the conservative interim while replacements are verified; it is not the fix,
and it must not become permanent by inertia. The `file` value is preserved as
`file_withheld`, so restoring is exactly as mechanical as withholding and
nobody has to reconstruct 323 paths by hand.

The .ogg files themselves are left on disk and in git. Deleting them would make
this irreversible for the sake of a question that is still open, and the exposure
is the published PAGE referencing them, not the bytes sitting in a repository.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("repo", type=Path)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--transcript-only", action="store_true")
    g.add_argument("--restore", action="store_true")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    d = a.repo.resolve() / "data" / "audio"
    if not d.is_dir():
        print(f"  {a.repo.name} has no data/audio — nothing to do")
        return 0

    files, clips, changed, no_text = 0, 0, 0, []
    for f in sorted(d.glob("*.json")):
        segs = json.loads(f.read_text(encoding="utf-8"))
        if not isinstance(segs, list):
            continue
        files += 1
        touched = False
        for s in segs:
            clips += 1
            if a.transcript_only and "file" in s:
                if not str(s.get("transcript", "")).strip():
                    no_text.append(f"{f.stem}: {s.get('label')!r} has no transcript — "
                                   f"withholding its audio leaves the learner nothing")
                s["file_withheld"] = s.pop("file")
                touched = True
            elif a.restore and "file_withheld" in s:
                s["file"] = s.pop("file_withheld")
                touched = True
        if touched:
            changed += 1
            if a.apply:
                f.write_text(json.dumps(segs, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")

    for n in no_text[:8]:
        print(f"::warning::{n}")
    verb = "withheld" if a.transcript_only else "restored"
    print(f"  {files} manifest(s), {clips} clip(s); {changed} manifest(s) "
          + (f"{verb}" if a.apply else f"would be {verb}"))
    if no_text:
        print(f"  {len(no_text)} clip(s) have audio and NO transcript — those pages "
              f"lose content, not just a player")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
