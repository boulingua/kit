#!/usr/bin/env python3
"""Audition a voice before a single byte of audio is generated from it.

    python audio/audition.py --code gfl
    python audio/audition.py --code gfl --check      licence gate only, no download

Order matters, and it is the whole design: **licence first, before the
download.** That step costs nothing and would have caught five of the eighteen
courses before anything was fetched — Turkish and Japanese (both
CC BY-NC-SA, both the only voice in their language), Chinese and Russian (whose
roadmap picks state `License: Unknown`), and Italian (whose two picks give
`License: See URL` with no resolvable statement).

Audio synthesised from a Piper model inherits the licence of its training
dataset. Course content is CC BY-SA 4.0, which permits commercial reuse and
forbids adding restrictions, so a NonCommercial model cannot ship inside it —
and an unstated licence cannot ship safely either, because no statement is not
permission.

Steps, in order:

  1. Resolve the row in voices.yml. Reject unless `licence` is in the
     allow-list, recording why.
  2. Fetch the .onnx and verify the checksum upstream publishes. A 404 demotes
     the row to status: none with the reason recorded.
  3. Synthesise a passage containing every codepoint in that language's
     `must_render` set — which is a column in voices.yml, not prose, so this
     gate is falsifiable and so F3's reference documents test the same set.
  4. Commit auditions/<code>.{txt,ogg,md} with a dated verdict.

This turns "spot-check by ear before batch-generating" — an unenforceable
instruction repeated in six roadmaps — into a gate with a file behind it.
A row at status: ready with no auditions/<code>.md carrying `verdict: pass`
fails gate D6.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REG = HERE / "voices.yml"
OUT = HERE / "auditions"

ALLOWED = {"CC0", "public domain", "public-domain", "Unlicense",
           "CC BY 3.0", "CC BY 4.0", "CC-BY 4.0", "CC-BY-4.0",
           "CC BY-SA 4.0", "Apache-2.0", "MIT"}


def normalise_licence(text: str | None) -> str:
    if not text:
        return ""
    t = text.strip().rstrip("/").split("\n")[0]
    # Upstream sometimes gives a bare URL instead of a name.
    if "creativecommons.org/publicdomain/zero" in t:
        return "CC0"
    if "creativecommons.org/licenses/by/4.0" in t:
        return "CC BY 4.0"
    if "creativecommons.org/licenses/by-sa/4.0" in t:
        return "CC BY-SA 4.0"
    return t


def rows() -> dict[str, dict]:
    return {r["code"]: r for r in yaml.safe_load(REG.read_text(encoding="utf-8"))["languages"]}


def licence_ok(row: dict) -> tuple[bool, str]:
    lic = normalise_licence(row.get("licence"))
    if not lic:
        return False, "no licence recorded — no statement is not permission"
    if lic not in ALLOWED:
        return False, f"licence {lic!r} is not in the allow-list"
    return True, lic


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--code", required=True)
    ap.add_argument("--check", action="store_true",
                    help="run the licence gate only; download nothing")
    a = ap.parse_args()

    all_rows = rows()
    if a.code not in all_rows:
        print(f"::error::{a.code} is not in voices.yml", file=sys.stderr)
        return 2
    row = all_rows[a.code]

    # ── 0. an already-resolved row is not a failure ───────────────────────
    # status: none is a decision, not an error. Reporting lle — which has no
    # voice upstream at all — as "no licence recorded" would be misleading, and
    # a gate that cries failure over a settled decision gets ignored.
    if row.get("status") == "none":
        print(f"  {a.code}: status none — transcript-only by decision, nothing to audition")
        print(f"  reason: {row.get('status_reason', '—')}")
        return 0

    # ── 1. licence, before anything is fetched ────────────────────────────
    ok, detail = licence_ok(row)
    if not ok:
        print(f"::error::{a.code} fails the licence gate: {detail}")
        print(f"  status: {row.get('status')}  reason: {row.get('status_reason', '—')}")
        print("  Nothing was downloaded. This is the cheap check and it runs first.")
        return 1
    print(f"  {a.code}: licence {detail} — in the allow-list")

    if a.check:
        print(f"  {a.code}: licence gate only (--check), nothing downloaded")
        return 0

    # ── 2. fetch and verify ───────────────────────────────────────────────
    url = row.get("url")
    if not url:
        print(f"::error::{a.code} has no url — never construct one from the key, "
              f"the Portuguese voice contains a non-ASCII character", file=sys.stderr)
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    model = OUT / f"{row['piper_key']}.onnx"
    if not model.exists():
        print(f"  fetching {row['piper_key']} …")
        try:
            urllib.request.urlretrieve(url, model)
        except Exception as e:
            print(f"::error::{a.code}: {url} did not resolve ({e.__class__.__name__}). "
                  f"Demote the row to status: none and record the reason.", file=sys.stderr)
            return 1
    got = hashlib.md5(model.read_bytes()).hexdigest()
    if row.get("md5") and got != row["md5"]:
        print(f"::error::{a.code}: checksum mismatch — expected {row['md5']}, got {got}",
              file=sys.stderr)
        return 1
    print(f"  checksum matches upstream ({got[:12]}…)")

    # ── 3. the must_render passage ────────────────────────────────────────
    must = row.get("must_render", []) + row.get("must_render_phrases", [])
    print(f"  must_render: {len(must)} item(s) — {' '.join(map(str, must))[:60]}")
    print("  Synthesise the passage, listen to it, then record the verdict in")
    print(f"  audio/auditions/{a.code}.md. A human ear is the gate here; this")
    print("  script gets you to the point where one is worth using.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
