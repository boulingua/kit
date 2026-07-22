#!/usr/bin/env python3
"""
render_thumbs.py — regenerate PNG thumbnails directly from the
.pptx and .pdf files under static/materials/. Idempotent; safe to
re-run after any swap.

PDF → PNG: PyMuPDF (cross-platform, no external binaries).
PPTX → PNG: LibreOffice headless (`soffice --headless --convert-to pdf`)
            piped through PyMuPDF. If LibreOffice isn't installed we
            log a warning and leave the existing PNG in place — useful
            for local Windows dev where soffice may not be on PATH;
            CI runs on Ubuntu which ships it.

Run from repo root:  python scripts/render_thumbs.py
"""
from __future__ import annotations

import shutil
import subprocess
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
TARGET_WIDTH = 1280


def find_libreoffice() -> str | None:
    for cand in ("soffice", "libreoffice"):
        if shutil.which(cand):
            return cand
    if sys.platform.startswith("win"):
        for p in (
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ):
            if Path(p).exists():
                return p
    return None


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


def render_pptx(pptx_path: Path, out_path: Path, soffice: str, tmp: Path) -> None:
    subprocess.run(
        [
            soffice,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(tmp),
            str(pptx_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    pdf = tmp / (pptx_path.stem + ".pdf")
    if not pdf.exists():
        raise RuntimeError(f"LibreOffice produced no PDF for {pptx_path.name}")
    try:
        render_pdf(pdf, out_path)
    finally:
        pdf.unlink(missing_ok=True)


def main() -> int:
    soffice = find_libreoffice()
    if not soffice:
        print(
            "  warn: LibreOffice not found; PPTX thumbnails will not be regenerated.\n"
            "        Install LibreOffice or run this in CI for full coverage.",
            file=sys.stderr,
        )

    n_pdf = 0
    n_pptx = 0
    n_skip = 0

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

    if soffice:
        with tempfile.TemporaryDirectory(prefix="render-thumbs-") as td:
            tmp = Path(td)
            # Presentation decks may be .pptx or .odp — both route through
            # LibreOffice (soffice --convert-to pdf → PNG) identically.
            for pptx in sorted(PRES.glob("*.pptx")) + sorted(PRES.glob("*.odp")):
                png = pptx.with_suffix(".png")
                try:
                    render_pptx(pptx, png, soffice, tmp)
                    print(f"  deck -> {png.relative_to(REPO)}")
                    n_pptx += 1
                except Exception as e:
                    print(f"  FAIL {pptx.relative_to(REPO)}: {e}", file=sys.stderr)
                    return 1
    else:
        n_skip = sum(1 for _ in PRES.glob("*.pptx")) + sum(1 for _ in PRES.glob("*.odp"))

    print(
        f"\nrendered: {n_pdf} pdf · {n_pptx} pptx"
        + (f" · {n_skip} pptx skipped (no soffice)" if n_skip else "")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
