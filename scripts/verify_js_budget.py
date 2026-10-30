#!/usr/bin/env python3
"""Measure scripts actually referenced by each built discovery page.

The initial page scripts must fit 88 KiB gzip; the page plus explicitly
referenced lazy graph modules must fit 280 KiB. Missing pages/assets and
external graph dependencies fail. This is a graph-page budget, not a claim
about later Pagefind query shards, separately configured telemetry or all network traffic.
"""
from __future__ import annotations
import gzip
import json
from pathlib import Path
import sys
import tomllib
from urllib.parse import unquote, urljoin, urlsplit
from html_tree import parse

GLUE_MAX = 90_112
TOTAL_MAX = 286_720
MARKERS = {'network-graph', 'network-mount', 'overview-root'}

def gz_size(p):
    return len(gzip.compress(p.read_bytes(), 9, mtime=0))

def audit(root: Path, base: str, telemetry=()):
    root = root.resolve(); errors = []; rows = []
    parsed = urlsplit(base); prefix = parsed.path.rstrip('/') + '/'
    if not root.is_dir(): return ['built site is missing'], rows
    def resolve(url, page):
        target = urlsplit(urljoin(base + page.relative_to(root).as_posix(), url))
        if target.netloc != parsed.netloc or target.scheme != parsed.scheme:
            raise ValueError(f'external script: {url}')
        path = unquote(target.path)
        if not path.startswith(prefix): raise ValueError(f'site prefix missing: {url}')
        file = (root/path[len(prefix):]).resolve()
        if not file.is_relative_to(root) or not file.is_file(): raise ValueError(f'missing script: {url}')
        return file
    for page in sorted(root.rglob('*.html')):
        html = page.read_text(encoding='utf-8')
        if not any(marker in html for marker in MARKERS): continue
        elements = list(parse(html).walk())
        if not any(e.attrs.get('id') in MARKERS for e in elements): continue
        eager, lazy = set(), set()
        excluded_telemetry = set()
        inline = 0
        for element in elements:
            if element.tag == 'script':
                if element.attrs.get('src') in telemetry and element.attrs.get('data-domain'):
                    excluded_telemetry.add(element.attrs['src'])
                elif element.attrs.get('src'): eager.add(element.attrs['src'])
                elif element.attrs.get('type', '') not in {'application/ld+json', 'application/json'}:
                    inline += len(gzip.compress(element.text.encode(), 9, mtime=0))
            for key, value in element.attrs.items():
                if key == 'data-vendors':
                    try:
                        urls = json.loads(value)
                        if not isinstance(urls, list) or any(not isinstance(u, str) for u in urls): raise ValueError('expected URL list')
                        lazy.update(urls)
                    except (ValueError, TypeError) as exc: errors.append(f'{page.relative_to(root)}: invalid data-vendors ({exc})')
                elif key.startswith('data-') and value and urlsplit(value).path.endswith('.js'):
                    lazy.add(value)
        try:
            initial = {resolve(u, page) for u in eager}
            deferred = {resolve(u, page) for u in lazy}
        except ValueError as exc:
            errors.append(f'{page.relative_to(root)}: {exc}'); continue
        if not initial:
            errors.append(f'{page.relative_to(root)}: discovery page has no script entry point'); continue
        glue = inline + sum(gz_size(p) for p in initial)
        total = inline + sum(gz_size(p) for p in initial | deferred)
        rows.append({'page':str(page.relative_to(root)), 'initial_gzip':glue, 'total_gzip':total,
                     'eager_assets':len(initial), 'lazy_assets':len(deferred-initial), 'telemetry_outside_graph_budget':sorted(excluded_telemetry)})
        if glue > GLUE_MAX: errors.append(f'{page.relative_to(root)}: initial scripts {glue} > {GLUE_MAX} bytes gzip')
        if total > TOTAL_MAX: errors.append(f'{page.relative_to(root)}: all graph scripts {total} > {TOTAL_MAX} bytes gzip')
    if not rows and not errors: errors.append('no built discovery page found for the enabled network gate')
    return errors, rows

def main():
    repo=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve()
    config=repo/'hugo.toml'
    if not config.is_file():
        print('::error::Give the course repository with hugo.toml and public/');return 1
    cfg=tomllib.loads(config.read_text())
    base=cfg.get('baseURL')
    if not base:
        print('::error::hugo.toml has no baseURL');return 1
    plausible=cfg.get('params',{}).get('plausible',{})
    telemetry={plausible.get('src')} if plausible.get('domain') else set()
    errors, rows=audit(repo/'public',base,telemetry)
    for row in rows: print(json.dumps(row))
    for error in errors: print('::error::'+error)
    print(f'JavaScript budget: {len(rows)} pages; {len(errors)} findings')
    return int(bool(errors))

if __name__=='__main__':raise SystemExit(main())
