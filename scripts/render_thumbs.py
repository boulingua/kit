#!/usr/bin/env python3
"""Render changed PDF covers at 1000 px; preserve recorded legacy thumbnails.

Usage: python scripts/render_thumbs.py REPO [--force]
The lock records source and thumbnail hashes. Existing thumbnails without a
lock are adopted as legacy; subsequent PDF changes regenerate their cover.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import tempfile
import sys
import pymupdf as fitz

TARGET_WIDTH = 1000


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_pdf(pdf_path: Path, out_path: Path) -> None:
    with fitz.open(pdf_path) as doc:
        if not doc.page_count:
            raise ValueError('PDF has no pages')
        page = doc[0]
        zoom = TARGET_WIDTH / page.rect.width
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(suffix='.png', dir=out_path.parent)
        os.close(fd)
        temporary = Path(name)
        try:
            pix.save(str(temporary))
            temporary.replace(out_path)
        finally:
            temporary.unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('repo', nargs='?', type=Path, default=Path.cwd())
    ap.add_argument('--force', action='store_true', help='regenerate even unchanged or legacy covers')
    args = ap.parse_args()
    repo = args.repo.resolve()
    if not (repo / 'content').is_dir():
        ap.error(f'{repo} is not a content repository')
    lock = repo / 'thumbnails.lock.json'
    try:
        old = json.loads(lock.read_text()) if lock.exists() else {}
        records, changed, failed = {}, 0, []
        pdfs = sorted({p for directory in ['static/materials/presentations', 'static/materials/worksheets', 'static/downloads'] for p in (repo / directory).rglob('*.pdf')})
        for pdf in pdfs:
            key = pdf.relative_to(repo).as_posix()
            png = pdf.with_suffix('.png')
            previous = old.get(key, {})
            source_hash = digest(pdf)
            stale = previous and (previous.get('pdf_sha256') != source_hash or not png.exists() or previous.get('png_sha256') != digest(png))
            regenerate = args.force or not png.exists() or stale
            try:
                if regenerate:
                    render_pdf(pdf, png)
                    changed += 1
                pix = fitz.Pixmap(str(png))
                standard = '1000px' if regenerate else previous.get('standard', 'legacy')
                records[key] = {'pdf_sha256': source_hash, 'png_sha256': digest(png), 'width': pix.width, 'standard': standard}
            except Exception as exc:
                failed.append(f'{key}: {exc}')
        if failed:
            for finding in failed:
                print(f'::error::{finding}', file=sys.stderr)
            return 1
        temporary = lock.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(records, indent=2, sort_keys=True) + '\n')
        temporary.replace(lock)
    except (ValueError, OSError, TypeError) as exc:
        print(f'::error::{exc}', file=sys.stderr)
        return 1
    print(f'Thumbnails: {len(pdfs)} PDFs inspected, {changed} covers rendered')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
