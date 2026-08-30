#!/usr/bin/env python3
"""Re-synthesise a course's audio from its transcripts, on the declared voice.

    regen_audio.py REPO --models DIR [--apply] [--limit N]

Every clip in these courses was generated with a voice fine-tuned from
en_US-lessac-medium, whose corpus is non-commercial only. The voices are
replaced; the recordings have to follow, because a manifest pointing at a file
made by the old model is the old model still being published.

THE TRANSCRIPT IS THE SOURCE. That is what makes this recoverable at all: every
clip carries its text, verified across all 1,220 before any of them were
withheld, so the recordings can be rebuilt without anyone re-authoring a word.
It is also why withholding was an acceptable interim rather than a loss.

Output matches what the site already serves — Ogg Vorbis, one channel, so the
existing `file` paths stay valid and D6's ≤64 kbit/s single-channel contract
holds. A regeneration that changed the container would have moved 1,220 URLs
for no reason.

**The encode is chunked, and that is not a performance choice.** A single
`sf.write()` of a long clip SEGFAULTS libsndfile 1.2.2's Vorbis encoder —
reproducibly, above roughly 2.1 million frames of real speech, in a clean
process with nothing else loaded. The process dies on signal 11 with no
traceback, no stderr and exit 139, so a run over 1,220 clips stops dead at the
first long one and says nothing about why.

That is the actual origin of the stranded `dialogue3.ogg.part` in daf, which
was recorded as a truncated download. It was not a download. It is this crash,
and it reproduces on demand: daf unit01 Dialog 3, 639 characters of German, 117
seconds of audio, every time. Writing the same samples through an open
SoundFile in 262,144-frame blocks completes and reads back at full length.

A `.part` therefore cannot be cleaned up by the process that made it — it is
not running any more. Stale ones are swept at start instead, which is also what
makes an interrupted run resumable rather than merely non-destructive.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import wave
from pathlib import Path

import yaml

KIT = Path(__file__).resolve().parent.parent
# Frames per write. Anything comfortably under the ~2.1M-frame point where
# libsndfile 1.2.2 falls over; 2**18 also keeps peak memory flat.
OGG_CHUNK = 1 << 18


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("repo", type=Path)
    ap.add_argument("--models", type=Path, required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    repo = a.repo.resolve()

    cfg = yaml.safe_load((repo / "boulingua.yml").read_text(encoding="utf-8"))
    code = cfg["code"]
    reg = {r["code"]: r for r in
           yaml.safe_load((KIT / "audio" / "voices.yml").read_text(encoding="utf-8"))["languages"]}
    row = reg.get(code) or {}
    key = row.get("piper_key")
    if not key:
        print(f"  {code} declares no voice — transcript-only by design, nothing to build")
        return 0
    if row.get("provenance") != "clean":
        print(f"::error::{code}'s voice {key} is not provenance-clean "
              f"({row.get('provenance')}). Refusing to generate audio from it — "
              f"that is the situation this script exists to undo.", file=sys.stderr)
        return 1

    onnx = a.models / f"{key}.onnx"
    if not onnx.exists():
        print(f"::error::{onnx} not found. Fetch the model first.", file=sys.stderr)
        return 2

    import soundfile as sf
    from piper import PiperVoice
    voice = PiperVoice.load(str(onnx))

    # Sweep .part files left by a previous run that was killed or crashed. A
    # dead process cannot tidy up after itself, and a stale .part next to a
    # good .ogg reads as a half-finished write that never happened.
    swept = 0
    audio_root = repo / "static"
    if audio_root.is_dir():
        for stale in audio_root.rglob("*.ogg.part"):
            if a.apply:
                stale.unlink()
            swept += 1
    if swept:
        print(f"  swept {swept} stale .part file(s) from an interrupted run"
              + ("" if a.apply else " (dry run — not removed)"))

    made = skipped = empty = 0
    for mf in sorted((repo / "data" / "audio").glob("*.json")):
        segs = json.loads(mf.read_text(encoding="utf-8"))
        if not isinstance(segs, list):
            continue
        touched = False
        for s in segs:
            rel = s.get("file") or s.get("file_withheld")
            text = str(s.get("transcript") or "").strip()
            if not rel or not text:
                skipped += 1
                continue
            # The path in the manifest is a URL carrying the site prefix; the
            # file lives under static/ without it.
            parts = [p for p in str(rel).lstrip("/").split("/")]
            if parts and parts[0] == code:
                parts = parts[1:]
            out = repo / "static" / Path(*parts)
            if a.apply:
                out.parent.mkdir(parents=True, exist_ok=True)
                buf = io.BytesIO()
                with wave.open(buf, "wb") as w:
                    voice.synthesize_wav(text, w)
                buf.seek(0)
                data, rate = sf.read(buf)
                if getattr(data, "ndim", 1) > 1:
                    data = data.mean(axis=1)      # one channel, per D6
                if not rate or len(data) == 0:
                    print(f"::error::{out.name}: synthesis produced no samples "
                          f"from {len(text)} characters — not written")
                    empty += 1
                    continue
                # ATOMIC. A run over 1,220 clips at roughly a minute each WILL be
                # interrupted, and an interrupted sf.write leaves a truncated Ogg
                # that is a perfectly valid file of zero duration — silent audio
                # that no gate distinguishes from working audio. Found exactly
                # that way: killing this script mid-write produced one.
                tmp = out.with_suffix(".ogg.part")
                # Chunked, because one big sf.write() segfaults the Vorbis
                # encoder on long clips. See the module docstring.
                with sf.SoundFile(str(tmp), "w", samplerate=int(rate), channels=1,
                                  format="OGG", subtype="VORBIS") as fh:
                    for i in range(0, len(data), OGG_CHUNK):
                        fh.write(data[i:i + OGG_CHUNK])
                if sf.info(str(tmp)).duration <= 0:
                    tmp.unlink(missing_ok=True)
                    print(f"::error::{out.name}: wrote a zero-duration file — discarded")
                    empty += 1
                    continue
                tmp.replace(out)
                if "file_withheld" in s:
                    s["file"] = s.pop("file_withheld")
                    touched = True
            made += 1
            if a.limit and made >= a.limit:
                break
        if touched and a.apply:
            mf.write_text(json.dumps(segs, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
        if a.limit and made >= a.limit:
            break

    print(f"  {code} on {key}: {made} clip(s) "
          + ("regenerated and restored" if a.apply else "would be regenerated")
          + (f", {skipped} skipped (no transcript or no path)" if skipped else "")
          + (f", {empty} produced NO AUDIO and were discarded" if empty else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
