#!/usr/bin/env python3
"""Gate A10 — the palette meets the rules the design page publishes.

    verify_contrast.py [KIT]

Four rules are stated publicly on the design page. Two of them are checkable
here, and both were false when this gate was written: ten of eighteen accents
fell below 4.5:1 on white and eight pairs sat closer than 15° of OKLCH hue.
S5 re-derived the palette; this is what stops it drifting back.

MEASURED FROM tokens.yaml, NOT FROM THE ROUND-TRIPPED HEX — and that
distinction earned itself. The re-derivation solved to 17° of separation,
wrote the result as 8-bit hex, and measured 11.3° when read back: darkening a
saturated colour at constant chroma walks it out of the sRGB gamut, and
clamping the channels does not preserve the hue it clamped from. So the solver
gained gamut mapping and this gate reads what the file actually holds, because
that is what every stylesheet, LaTeX style and brand mark is generated from.

Rules 1 and 4 are not checkable here. Flag-safety is a judgement about a
national flag that nothing in this repository records, and hub blue is checked
as a hue distance rather than as an exact value.
"""
from __future__ import annotations

import itertools
import math
import sys
from pathlib import Path

import yaml

KIT = Path(__file__).resolve().parent.parent
MIN_SEP = 15.0
MIN_CONTRAST = 4.5
HUB = "#1A73E8"


def _lin(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def oklch(hx):
    r, g, b = (_lin(int(hx[i:i + 2], 16)) for i in (1, 3, 5))
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    A = 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s
    B = 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s
    return math.degrees(math.atan2(B, A)) % 360


def contrast(hx, other="#FFFFFF"):
    def lum(h):
        r, g, b = (_lin(int(h[i:i + 2], 16)) for i in (1, 3, 5))
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    a, b = lum(hx), lum(other)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def sep(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else KIT
    f = root / "design" / "tokens.yaml"
    if not f.exists():
        print(f"A10 n/a — {root.name} holds no tokens.yaml")
        return 0
    t = yaml.safe_load(f.read_text(encoding="utf-8"))
    acc = [a for a in t["accents"] if a["code"] != "template"]

    bad = []
    for a in acc:
        c = contrast(a["accent"])
        if c < MIN_CONTRAST:
            bad.append(f"{a['code']}: accent {a['accent']} is {c:.2f}:1 on white, "
                       f"below {MIN_CONTRAST}:1. It is used for links and rules, "
                       f"not decoration.")
    # The dark-theme pair has to work on the dark surface, not on white.
    surf = (t.get("colour", {}).get("surface", {}) or {}).get("dark")
    if surf:
        for a in acc:
            c = contrast(a["dark"], surf)
            if c < MIN_CONTRAST:
                bad.append(f"{a['code']}: dark accent {a['dark']} is {c:.2f}:1 on "
                           f"the dark surface {surf}")

    hues = {a["code"]: oklch(a["accent"]) for a in acc}
    for x, y in itertools.combinations(sorted(hues), 2):
        d = sep(hues[x], hues[y])
        if d < MIN_SEP:
            bad.append(f"{x} and {y} are {d:.1f}° apart in OKLCH hue, under "
                       f"{MIN_SEP}° — two courses that can be mistaken for each "
                       f"other")
    hub = oklch(HUB)
    for c, h in sorted(hues.items()):
        if sep(h, hub) < MIN_SEP:
            bad.append(f"{c} is {sep(h, hub):.1f}° from hub blue {HUB}, which is "
                       f"reserved for the umbrella site")

    for b in bad:
        print(f"::error::{b}")
    if bad:
        print(f"\nA10 FAIL — {len(bad)} problem(s)", file=sys.stderr)
        return 1
    worst_c = min(contrast(a["accent"]) for a in acc)
    worst_s = min(sep(hues[x], hues[y])
                  for x, y in itertools.combinations(sorted(hues), 2))
    print(f"A10 OK — {len(acc)} accents; worst contrast {worst_c:.2f}:1, "
          f"closest pair {worst_s:.1f}°, all clear of hub blue")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
