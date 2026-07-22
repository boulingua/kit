#!/usr/bin/env python3
"""Generate this course's brand pentagon + favicons from data/accents.yaml.

The pentagon is the boulingua per-language icon: a solid pentagon in the
course's signature accent colour (flag-safe, one per language). Run from the
repo root:

    python brand/make_icon.py            # reads `code` from hugo.toml
    python brand/make_icon.py efl        # or pass a site code explicitly

Writes: brand/icon.svg, brand/icon.png, static/favicon-32.png, favicon-16.png,
apple-touch-icon.png. Wire the favicons in layouts/_partials/head/custom-icons.html.
"""
from __future__ import annotations
import math, re, sys, pathlib
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


def site_code() -> str:
    if len(sys.argv) > 1:
        return sys.argv[1]
    txt = (ROOT / "hugo.toml").read_text(encoding="utf-8")
    m = re.search(r'^\s*code\s*=\s*"([^"]+)"', txt, re.M)
    return m.group(1) if m else "efl"


def accent_for(code: str) -> str:
    accents = yaml.safe_load((ROOT / "data" / "accents.yaml").read_text(encoding="utf-8"))
    for a in accents:
        if a.get("code") == code:
            return a["accent"]
    raise SystemExit(f"code '{code}' not in data/accents.yaml")


def pentagon_points(cx, cy, r):
    # point-up regular pentagon
    return [(cx + r * math.sin(2 * math.pi * i / 5),
             cy - r * math.cos(2 * math.pi * i / 5)) for i in range(5)]


def main() -> int:
    code = site_code()
    colour = accent_for(code)
    pts = pentagon_points(50, 52, 42)
    path = " ".join(f"{'M' if i == 0 else 'L'}{x:.2f},{y:.2f}" for i, (x, y) in enumerate(pts)) + " Z"
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
           f'<path d="{path}" fill="{colour}"/></svg>')
    (ROOT / "brand" / "icon.svg").write_text(svg, encoding="utf-8")
    print(f"code={code} accent={colour} → brand/icon.svg")

    # Raster outputs are optional (need matplotlib); skip gracefully if absent.
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Polygon
        for name, px in [("brand/icon.png", 512), ("static/favicon-32.png", 32),
                         ("static/favicon-16.png", 16), ("static/apple-touch-icon.png", 180)]:
            fig = plt.figure(figsize=(1, 1), dpi=px)
            ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off"); ax.set_xlim(0, 100); ax.set_ylim(100, 0)
            ax.add_patch(Polygon(pts, closed=True, facecolor=colour, edgecolor="none"))
            out = ROOT / name; out.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(out, transparent=True, dpi=px); plt.close(fig)
            print(f"  → {name}")
    except ImportError:
        print("  (matplotlib not installed — SVG only; run `pip install matplotlib` for PNG/favicons)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
