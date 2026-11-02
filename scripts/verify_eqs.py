#!/usr/bin/env python3
"""Check rendered teaching shortcode accessibility, including minified HTML.

Pedagogical step ordering, task quality and progression need content review.
"""
from pathlib import Path
import sys
from html_tree import Element, parse

CONTRACTS = {'vocab', 'niveau', 'gap', 'recycles', 'extension', 'tl', 'callout'}


def check(html: str, rel: str) -> list[str]:
    bad = []
    for node in parse(html).walk():
        classes, attrs = node.classes, node.attrs
        if attrs.get('data-role') == 'key':
            containers = [n for n in node.walk() if n.tag == 'details']
            if not containers or any('open' in n.attrs for n in containers):
                bad.append(f'{rel}: answer key must use details closed by default')
        if 'vocab' in classes:
            cells = [n for n in node.walk() if n.tag in ('th', 'td')]
            headers = [n for n in cells if n.tag == 'th']
            if node.tag != 'table' or not headers:
                bad.append(f'{rel}: vocab must be a table with column headers')
            if any(n.attrs.get('scope') != 'col' for n in headers):
                bad.append(f'{rel}: every vocab header needs scope="col"')
            # DaF can use German for both target and explanation.
            if any(not (n.attrs.get('lang') or '').strip() for n in cells):
                bad.append(f'{rel}: every vocabulary cell needs a language')
        if 'niveau' in classes:
            if not (attrs.get('aria-label') or '').strip():
                bad.append(f'{rel}: niveau has no accessible level name')
            badges = [n for n in node.walk() if 'niveau-badge' in n.classes]
            if not badges or not any(n.text.strip() in ('G', 'M', 'E') for n in badges):
                bad.append(f'{rel}: niveau must show its G, M or E letter as text')
        if 'gap' in classes and not (attrs.get('aria-label') or '').strip():
            bad.append(f'{rel}: a gap has no accessible label')
        if 'recycles' in classes:
            if any('recycles-unresolved' in n.classes for n in node.walk()):
                bad.append(f'{rel}: recycles references an unresolved unit')
        if 'extension' in classes:
            summaries = [n for n in node.children if isinstance(n, Element) and n.tag == 'summary']
            if node.tag != 'details' or not summaries or not summaries[0].text.strip():
                bad.append(f'{rel}: extension needs details with a nonempty summary')
        if 'tl' in classes:
            language = (attrs.get('lang') or '').strip()
            if not language:
                bad.append(f'{rel}: target-language passage has no lang attribute')
            if language.split('-')[0] in {'ar', 'fa', 'he', 'ur'} and attrs.get('dir') != 'rtl':
                bad.append(f'{rel}: right-to-left passage needs dir="rtl"')
    return bad


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else 'public')
    if (root / 'content').is_dir():
        root = root / 'public'
    pages = sorted(root.rglob('*.html')) if root.is_dir() else []
    if not pages:
        print(f'::error::{root}: no built HTML pages; build the site first')
        return 1
    bad, seen = [], 0
    for path in pages:
        html = path.read_text(encoding='utf-8')
        if any(n.classes & CONTRACTS for n in parse(html).walk()):
            seen += 1
            bad.extend(check(html, str(path.relative_to(root))))
    for finding in bad:
        print(f'::error::{finding}')
    if not seen:
        print(f'A12/A14/C12 n/a — scanned {len(pages)} HTML pages; no teaching components present')
    else:
        print(f'A12/A14/C12 {"FAIL" if bad else "OK"} — {seen} component pages, {len(bad)} violations')
    return int(bool(bad))


if __name__ == '__main__':
    raise SystemExit(main())
