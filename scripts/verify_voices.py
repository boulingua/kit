#!/usr/bin/env python3
"""Gate 3 / D6-audition — a voice is not usable until somebody has listened.

    verify_voices.py [KIT]

Every course publishes under CC BY-SA 4.0, so a voice model on a NonCommercial
or ShareAlike-incompatible licence cannot generate its audio: the organisation
would be distributing derivative audio it has no right to. That is why the
allowlist exists and why `status: ready` is a claim rather than a default.

What this enforces:

  status: ready requires an audition file. A verdict nobody recorded is a
  verdict nobody reached — and "ready" is the field that lets the audio
  pipeline run against 60 units.

  An audition file requires a verdict line, and a `pass` verdict requires a
  named listener and a date. Whether a synthetic voice is good enough to put in
  front of a child learning to pronounce a language is not a property of the
  model file; somebody has to listen to it.

  Every declared licence is on the allowlist, MATCHED AFTER NORMALISING. The
  registry spells one licence three ways — "CC-BY 4.0", "CC-BY-4.0" and a bare
  creativecommons.org URL — and an exact-string allowlist flagged seven codes
  of which four are perfectly fine. A gate that fails a course over a hyphen
  teaches people to ignore it.

  A voice with no licence must also have no status: ready. Those two fields
  disagreeing is the state where audio gets generated from an unknown model.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

KIT = Path(__file__).resolve().parent.parent
VERDICT = re.compile(r"(?mi)^\s*(?:\*\*)?verdict(?:\*\*)?\s*[:=]\s*(pass|fail|hold)\b")
LISTENER = re.compile(r"(?mi)^\s*(?:\*\*)?(?:listener|checked by|auditioned by)(?:\*\*)?\s*[:=]\s*(\S.*)$")
DATED = re.compile(r"(?m)^\s*(?:\*\*)?date(?:\*\*)?\s*[:=]\s*(\d{4}-\d{2}-\d{2})")


def norm(lic: str | None) -> str | None:
    """One spelling per licence, so the allowlist matches meaning not text."""
    if not lic:
        return None
    s = str(lic).strip().lower()
    s = re.sub(r"^https?://(?:www\.)?creativecommons\.org/(?:licenses|publicdomain)/", "", s)
    s = s.replace("zero/1.0", "cc0").replace("/", " ").replace("-", " ")
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\b(\d)\.0\b", r"\1.0", s)
    for canon, pats in {
        "CC0": (r"^cc0", r"^publicdomain", r"^public domain"),
        "CC BY 4.0": (r"^cc by 4\.0$", r"^by 4\.0$"),
        "CC BY 3.0": (r"^cc by 3\.0$", r"^by 3\.0$"),
        "CC BY-SA 4.0": (r"^cc by sa 4\.0$", r"^by sa 4\.0$"),
        "Apache-2.0": (r"^apache",),
        "MIT": (r"^mit$",),
        "Unlicense": (r"^unlicense$",),
    }.items():
        if any(re.match(p, s) for p in pats):
            return canon
    return str(lic).strip()


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else KIT
    f = root / "audio" / "voices.yml"
    if not f.exists():
        print(f"Gate 3 n/a — {root.name} holds no audio/voices.yml")
        return 0
    d = yaml.safe_load(f.read_text(encoding="utf-8"))
    allow = {norm(x) for x in d.get("licence_allowlist", [])}
    rows = d.get("languages") or []

    bad, notes = [], []
    ready = candidate = none = 0
    for r in rows:
        code = r.get("code", "?")
        status = str(r.get("status") or "none")
        raw_lic = r.get("licence")
        lic = norm(raw_lic)
        if raw_lic and lic != str(raw_lic).strip():
            notes.append(f"{code}: licence {raw_lic!r} normalised to {lic!r}")

        if status == "ready":
            ready += 1
        elif status == "candidate":
            candidate += 1
        else:
            none += 1

        if raw_lic and lic not in allow:
            bad.append(f"{code}: licence {raw_lic!r} (reads as {lic!r}) is not on the "
                       f"allowlist. Every course publishes under CC BY-SA 4.0; audio "
                       f"from a model this licence does not permit is audio the "
                       f"organisation has no right to distribute.")
        if status == "ready" and not raw_lic:
            bad.append(f"{code}: status ready with no licence at all — this is the "
                       f"state where audio gets generated from an unknown model")

        # PROVENANCE, which is a different question from the dataset licence
        # and the one the registry was not asking. Every voice this
        # organisation has shipped audio with advertises an allowlist-clean
        # dataset — CC0, CC BY 4.0 — while its Training line reads "Finetuned
        # from U.S. English lessac voice". That base is trained on the Blizzard
        # 2013 corpus, which is non-commercial only and non-sublicensable, and
        # upstream's own ku_TR-berfin_renas-medium declares the identical
        # derivation CC BY-NC 4.0 for exactly that reason.
        #
        # A sweep of the upstream catalogue found 76 of 175 voices in this
        # position. Reading only the dataset line passes all 76.
        if r.get("provenance") == "blocked":
            bad.append(f"{code}: {r.get('piper_key')} is provenance-blocked — "
                       f"{r.get('base_model')} descends from a non-commercial "
                       f"corpus, and this course publishes under CC BY-SA 4.0, "
                       f"which grants downstream commercial use. See "
                       f"docs/voice-provenance.md.")
        elif raw_lic and not r.get("base_model") and status in ("ready", "candidate"):
            notes.append(f"{code}: no base_model recorded. The dataset licence is "
                         f"not the whole question — check the model card's Training "
                         f"line before this reaches ready.")

        aud = root / "audio" / "auditions" / f"{code}.md"
        if status == "ready":
            if not aud.exists():
                bad.append(f"{code}: status ready with no audio/auditions/{code}.md. "
                           f"Whether a synthetic voice is good enough to put in front "
                           f"of a child is not a property of the model file — somebody "
                           f"has to listen.")
                continue
            text = aud.read_text(encoding="utf-8")
            v = VERDICT.search(text)
            if not v:
                bad.append(f"audio/auditions/{code}.md: no verdict line")
            elif v.group(1).lower() != "pass":
                bad.append(f"{code}: status ready but the audition verdict is "
                           f"{v.group(1)!r}")
            elif not LISTENER.search(text):
                bad.append(f"audio/auditions/{code}.md: verdict pass with no named "
                           f"listener")
            elif not DATED.search(text):
                bad.append(f"audio/auditions/{code}.md: verdict pass with no date")
        elif aud.exists():
            text = aud.read_text(encoding="utf-8")
            v = VERDICT.search(text)
            if v and v.group(1).lower() == "pass":
                bad.append(f"{code}: an audition passed but status is {status!r} — "
                           f"the verdict and the registry disagree")

    for n in notes[:8]:
        print(f"::notice::{n}")
    for b in bad[:15]:
        print(f"::error::{b}")
    print(f"  {len(rows)} language(s): {ready} ready, {candidate} candidate, "
          f"{none} without a voice")
    if bad:
        print(f"\nGate 3 FAIL — {len(bad)} problem(s)", file=sys.stderr)
        return 1
    print("Gate 3 OK — every licence on the allowlist, every ready voice "
          "auditioned by a named listener")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
