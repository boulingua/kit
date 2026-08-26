#!/usr/bin/env python3
"""S5 — re-derive the accent palette so it meets the rules the site publishes.

    rederive_accents.py [--apply]

The design page states four rules and, measured, the palette broke two of them:
ten of eighteen accents fall below 4.5:1 on white, and eight pairs sit closer
than the 15° of OKLCH hue separation gate A10 enforces. The page says so out
loud now, which is honest and is not a fix.

WHAT THIS PRESERVES, AND WHY THAT IS THE HARD PART. Rule 1 is flag-safety: the
hue must not appear in that language's national flag. That is a judgement the
author made per language and nothing in this repository records the reasoning,
so a solver free to move hues wherever it likes would silently undo eighteen
decisions it cannot see. Every hue therefore moves as little as the constraints
allow, and the report names each one that moved by more than 8° so the
flag-safety call can be re-checked on exactly those.

Lightness does the contrast work. Darkening an OKLCH colour at constant hue and
chroma raises contrast against white without touching the hue at all, so the
ten failing accents can be fixed without entering anyone's flag.
"""
from __future__ import annotations

import argparse
import colorsys
import itertools
import math
from pathlib import Path

import yaml

HUB = "#1A73E8"
MIN_SEP = 15.0
MIN_CONTRAST = 4.5

# Solve with headroom, because the answer is written as 8-bit hex and read back
# through it. The first run converged on exactly 15.05 degrees of separation and
# 4.50:1 of contrast, and after the round-trip to #RRGGBB the same palette
# measured four pairs under 15 and sat on the contrast boundary. The programme
# names this trap — gate A10 must measure "the OKLCH hue axis of tokens.yaml,
# not of the round-tripped hex" — and the honest fix is to leave enough margin
# that both readings agree rather than to pick whichever one passes.
SOLVE_SEP = 17.0
SOLVE_CONTRAST = 4.62


# ── colour conversions ──────────────────────────────────────────────────────
def _lin(c: float) -> float:
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _unlin(c: float) -> float:
    c = 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055
    return max(0, min(255, round(c * 255)))


def hex_to_oklch(hx: str) -> tuple[float, float, float]:
    r, g, b = (_lin(int(hx[i:i + 2], 16)) for i in (1, 3, 5))
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    L = 0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s
    A = 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s
    B = 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s
    return L, math.hypot(A, B), math.degrees(math.atan2(B, A)) % 360


def _srgb(L: float, C: float, H: float) -> tuple[float, float, float]:
    a, b = C * math.cos(math.radians(H)), C * math.sin(math.radians(H))
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return (+4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
            -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
            -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)


def in_gamut(L: float, C: float, H: float) -> bool:
    return all(-0.001 <= x <= 1.001 for x in _srgb(L, C, H))


def fit_gamut(L: float, C: float, H: float) -> float:
    """Largest chroma at this L and H that sRGB can actually hold.

    THIS IS THE BUG THE FIRST TWO ATTEMPTS HAD. Darkening at constant chroma
    walks a saturated colour straight out of the sRGB gamut, and converting it
    to hex CLAMPS each channel to 0..255 — which does not preserve the hue it
    was clamped from. The palette came back measuring 11.3 degrees where it had
    been solved to 17, and raising the solve margin made it WORSE, because a
    wider target pushed more colours further outside the gamut.

    Reducing chroma keeps the hue exactly and costs only saturation, which is
    the right trade for a colour whose job is to be distinguishable.
    """
    if in_gamut(L, C, H):
        return C
    lo, hi = 0.0, C
    for _ in range(40):
        mid = (lo + hi) / 2
        if in_gamut(L, mid, H):
            lo = mid
        else:
            hi = mid
    return lo


def oklch_to_hex(L: float, C: float, H: float) -> str:
    C = fit_gamut(L, C, H)
    return "#" + "".join(f"{_unlin(x):02X}" for x in _srgb(L, C, H))


def luminance(hx: str) -> float:
    r, g, b = (_lin(int(hx[i:i + 2], 16)) for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_on_white(hx: str) -> float:
    return 1.05 / (luminance(hx) + 0.05)


def sep(a: float, b: float) -> float:
    d = abs(a - b) % 360
    return min(d, 360 - d)


# ── the two solvers ─────────────────────────────────────────────────────────
def space_hues(hues: dict[str, float], forbidden: float) -> dict[str, float]:
    """Push hues apart to MIN_SEP, moving each as little as possible.

    Circular, so it is solved by relaxation rather than by sorting and
    redistributing: redistribution would move every hue to an even spacing and
    throw away eighteen flag-safety decisions to fix eight pairs.
    """
    h = dict(hues)
    for _ in range(4000):
        worst = None
        for x, y in itertools.combinations(sorted(h), 2):
            d = sep(h[x], h[y])
            if d < SOLVE_SEP and (worst is None or d < worst[2]):
                worst = (x, y, d)
        # Keep clear of hub blue too — it is reserved for the umbrella site.
        for c in sorted(h):
            d = sep(h[c], forbidden)
            if d < SOLVE_SEP and (worst is None or d < worst[2]):
                worst = (c, None, d)
        if worst is None:
            return h
        x, y, d = worst
        push = (SOLVE_SEP - d) / 2 + 0.05
        if y is None:
            away = 1 if ((h[x] - forbidden) % 360) < 180 else -1
            h[x] = (h[x] + away * push * 2) % 360
        else:
            fwd = ((h[y] - h[x]) % 360) < 180
            h[x] = (h[x] - push) % 360 if fwd else (h[x] + push) % 360
            h[y] = (h[y] + push) % 360 if fwd else (h[y] - push) % 360
    return h


def darken_to_contrast(L: float, C: float, H: float) -> tuple[float, str]:
    """Lowest darkening that clears 4.5:1, hue and chroma untouched."""
    lo, hi = 0.0, L
    for _ in range(60):
        mid = (lo + hi) / 2
        if contrast_on_white(oklch_to_hex(mid, C, H)) >= SOLVE_CONTRAST:
            lo = mid
        else:
            hi = mid
    # lo is the darkest passing; walk back up to the LIGHTEST that still passes
    best = lo
    for step in range(1, 400):
        cand = lo + step * 0.0008
        if cand > L:
            break
        if contrast_on_white(oklch_to_hex(cand, C, H)) >= SOLVE_CONTRAST:
            best = cand
    return best, oklch_to_hex(best, C, H)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    root = Path(__file__).resolve().parent
    t = yaml.safe_load((root / "tokens.yaml").read_text(encoding="utf-8"))
    acc = [x for x in t["accents"] if x["code"] != "template"]

    cur = {x["code"]: hex_to_oklch(x["accent"]) for x in acc}
    new_h = space_hues({c: v[2] for c, v in cur.items()}, hex_to_oklch(HUB)[2])

    moved, darkened, out = [], [], {}
    for code, (L, C, H) in cur.items():
        h2 = new_h[code]
        L2, hexv = L, oklch_to_hex(L, C, h2)
        if contrast_on_white(hexv) < SOLVE_CONTRAST:
            L2, hexv = darken_to_contrast(L, C, h2)
            darkened.append((code, contrast_on_white(oklch_to_hex(L, C, h2)),
                             contrast_on_white(hexv)))
        d = sep(H, h2)
        if d > 8:
            moved.append((code, H, h2, d))
        out[code] = (hexv, L2, C, h2)

    print(f"  hue moves > 8 deg — RE-CHECK FLAG-SAFETY on these {len(moved)}:")
    for c, h0, h1, d in sorted(moved, key=lambda z: -z[3]):
        print(f"      {c}  {h0:6.1f} -> {h1:6.1f}   ({d:.1f} deg)")
    print(f"  darkened for contrast: {len(darkened)}")
    for c, before, after in sorted(darkened, key=lambda z: z[1]):
        print(f"      {c}  {before:.2f}:1 -> {after:.2f}:1")

    # VERIFY THE RESULT, NOT THE INTENT. The first version checked the hues it
    # had solved for rather than the hues of the hex it was about to write, and
    # reported "0 pairs under 15" while shipping a palette that measured 11.3.
    # An 8-bit hex does not hold an arbitrary OKLCH hue, so the only number that
    # matters is the one read back out of the file everything else reads.
    hs = {c: hex_to_oklch(v[0])[2] for c, v in out.items()}
    bad = [(x, y, sep(hs[x], hs[y])) for x, y in itertools.combinations(sorted(hs), 2)
           if sep(hs[x], hs[y]) < MIN_SEP]
    fail = [(c, contrast_on_white(v[0])) for c, v in out.items()
            if contrast_on_white(v[0]) < MIN_CONTRAST]
    for x, y, d in bad:
        print(f"::error::{x}/{y} still {d:.1f} deg apart after the hex round-trip")
    print(f"\n  after: {len(bad)} pair(s) under {MIN_SEP} deg, "
          f"{len(fail)} accent(s) under {MIN_CONTRAST}:1")

    if not a.apply:
        return 0 if not (bad or fail) else 1
    if bad or fail:
        print("::error::constraints not met — nothing written")
        return 1

    txt = (root / "tokens.yaml").read_text(encoding="utf-8")
    for code, (hexv, L2, C, H2) in out.items():
        old = next(x for x in acc if x["code"] == code)
        # hover is the accent one step darker; dark/dark_hover are the dark-theme
        # pair, kept at their existing lightness relationship to the new hue.
        hov = oklch_to_hex(max(0.0, L2 - 0.06), C, H2)
        dl, dc, _ = hex_to_oklch(old["dark"])
        dkv = oklch_to_hex(dl, dc, H2)
        dhl, dhc, _ = hex_to_oklch(old["dark_hover"])
        dhv = oklch_to_hex(dhl, dhc, H2)
        for field, val in (("accent", hexv), ("hover", hov),
                           ("dark", dkv), ("dark_hover", dhv)):
            txt = txt.replace(f'{field}: "{old[field]}"', f'{field}: "{val}"', 1)
    (root / "tokens.yaml").write_text(txt, encoding="utf-8")
    print(f"  tokens.yaml updated — regenerate artefacts with `kit design`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
