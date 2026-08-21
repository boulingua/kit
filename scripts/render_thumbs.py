#!/usr/bin/env python3
"""render_thumbs.py — the one thumbnail renderer.

PDF → PNG at TARGET_WIDTH via PyMuPDF. No external binaries, no format
conversion: decks are XeLaTeX PDFs now, so the LibreOffice PPTX path was
converting a format nothing in the org produces, and it is gone along with the
libreoffice-impress install it required in CI.

There were two renderers before this, at two widths, and a third width in the
corpus from an earlier run — so a thumbnail's size depended on which script
happened to make it. build_materials_latex.thumb() now delegates here.

Idempotent; safe to re-run.

Run from repo root:  python scripts/render_thumbs.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Need PyMuPDF: pip install pymupdf", file=sys.stderr)
    sys.exit(2)

REPO = Path(__file__).resolve().parent.parent
PRES = REPO / "static" / "materials" / "presentations"
WORK = REPO / "static" / "materials" / "worksheets"
EXAMS = REPO / "static" / "downloads"

# Render PDF page 1 at this width (px). 96 dpi × 8.27 in ≈ 794; we go
# wider for retina rendering of the card thumbnail.
TARGET_WIDTH = 1000
# 1000 px, not 1280. A material card renders at up to 320 CSS px, so a 2x
# display needs 640 device px and 1000 clears that with margin. 1280 buys
# nothing measurable: PNG size tracks area, and the 1280 px exam thumbnails
# average 179 KB against 105 KB for the same documents at 900 px — 1.7x the
# bytes for no perceptible gain. Existing thumbnails are NOT re-rendered; each
# ages out the next time its PDF changes (ADR-0010).



def render_pdf(pdf_path: Path, out_path: Path) -> None:
    doc = fitz.open(pdf_path)
    try:
        page = doc[0]
        zoom = TARGET_WIDTH / page.rect.width
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        pix.save(out_path.as_posix())
    finally:
        doc.close()



def main() -> int:

    # PRES was globbed for *.pptx/*.odp only, never *.pdf — so since the
    # LaTeX migration deck thumbnails were produced solely as a side-effect
    # of build_materials_latex.py. This is the missing loop.
    for pdf in sorted(PRES.glob("*.pdf")):
        render_pdf(pdf, pdf.with_suffix(".png"))
        n += 1

    for pdf in sorted(WORK.glob("*.pdf")):
        png = pdf.with_suffix(".png")
        try:
            render_pdf(pdf, png)
            print(f"  pdf  -> {png.relative_to(REPO)}")
            n_pdf += 1
        except Exception as e:
            print(f"  FAIL {pdf.relative_to(REPO)}: {e}", file=sys.stderr)
            return 1

    for pdf in sorted(EXAMS.rglob("*.pdf")):
        png = pdf.with_suffix(".png")
        try:
            render_pdf(pdf, png)
            print(f"  exam -> {png.relative_to(REPO)}")
            n_pdf += 1
        except Exception as e:
            print(f"  FAIL {pdf.relative_to(REPO)}: {e}", file=sys.stderr)
            return 1
if __name__ == "__main__":
    sys.exit(main())
