"""Reusable reportlab attribution helper for EFL worksheet PDFs.

Every PDF the project ships must carry "S. Le Boulanger" as PDF metadata
AND as a visible footer + diagonal watermark. Use `apply_attribution`
from any reportlab generator (placeholder script, real worksheet
generators) so the treatment never drifts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from reportlab.lib.colors import Color
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

AUTHOR = "S. Le Boulanger"
LICENSE = "CC-BY-SA 4.0"
SITE = "EFL"


@dataclass
class AttributionContext:
    track: str          # "gm" or "e"
    klasse: int         # 5..13
    unit_nr: int        # 1..12
    niveau: str         # "G" | "M" | "E" | "E-BF" | "E-LF"
    title: str
    subject: str = "EFL — Worksheet"


def set_metadata(canvas: Canvas, ctx: AttributionContext) -> None:
    canvas.setAuthor(AUTHOR)
    canvas.setTitle(f"{ctx.title} — Klasse {ctx.klasse} · Niveau {ctx.niveau}")
    canvas.setSubject(ctx.subject)
    canvas.setCreator(f"{AUTHOR} · {SITE}")
    canvas.setKeywords(
        f"EFL, Bildungsplan, Klasse {ctx.klasse}, "
        f"Niveau {ctx.niveau}, Track {ctx.track}, Unit {ctx.unit_nr}"
    )


def draw_header(canvas: Canvas, ctx: AttributionContext, page_size=A4) -> None:
    width, height = page_size
    canvas.saveState()
    canvas.setFont("Helvetica", 9)
    canvas.setFillGray(0.35)
    canvas.drawString(36, height - 30, f"{AUTHOR} · {SITE}")
    canvas.restoreState()


def draw_footer(canvas: Canvas, ctx: AttributionContext, page_size=A4) -> None:
    width, _ = page_size
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillGray(0.4)
    footer = (
        f"© {AUTHOR} · {LICENSE} · Klasse {ctx.klasse} · "
        f"Niveau {ctx.niveau} · Unit {ctx.unit_nr}"
    )
    canvas.drawCentredString(width / 2.0, 24, footer)
    canvas.restoreState()


def draw_watermark(canvas: Canvas, page_size=A4) -> None:
    width, height = page_size
    canvas.saveState()
    grey = Color(0.92, 0.92, 0.92)
    canvas.setFillColor(grey)
    canvas.setFont("Helvetica-Bold", 48)
    canvas.translate(width / 2.0, height / 2.0)
    canvas.rotate(55)
    canvas.drawCentredString(0, 0, AUTHOR)
    canvas.restoreState()


def apply_attribution(canvas: Canvas, ctx: AttributionContext,
                      page_size=A4, with_metadata: bool = True) -> None:
    """Apply header + footer + watermark to the current page.

    Call once per page after content is drawn but before showPage().
    If `with_metadata` is True, also sets the PDF document metadata.
    """
    if with_metadata:
        set_metadata(canvas, ctx)
    draw_watermark(canvas, page_size)
    draw_header(canvas, ctx, page_size)
    draw_footer(canvas, ctx, page_size)
