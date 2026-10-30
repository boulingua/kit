#!/usr/bin/env python3
"""Verify built local links and assets, including project-site URL prefixes."""
from pathlib import Path
from urllib.parse import urljoin, urlsplit, unquote
import argparse
import tomllib
from html_tree import parse

PUBLIC_SITES = {'website','efl','fle','daf','nsf','nvt','afl','cfl','ele','gfl','ils','jfl','lle','pfa','pfl','ple','rki','tfl','ufl','ressources','scriptlibrary','curriculum','kit','scriptbridge'}


def audit(repo):
    cfg=tomllib.loads((repo/'hugo.toml').read_text())
    base=cfg.get('baseURL')
    if not base:return ['hugo.toml must declare baseURL'],0
    urlbase=urlsplit(base);prefix=urlbase.path.rstrip('/')+'/'
    root=repo/'public';pages=sorted(root.rglob('*.html'));errors=[];checked=0;anchors={}
    if not pages:return ['no built HTML pages found'],0
    for page in pages:
        tree=parse(page.read_text(errors='replace'))
        anchors[page]={e.attrs['id'] for e in tree.walk() if e.attrs.get('id')}
    for page in pages:
        pageurl=urljoin(base,page.relative_to(root).as_posix())
        for element in parse(page.read_text(errors='replace')).walk():
            attribute='href' if element.tag in {'a','link'} else 'src' if element.tag in {'img','script','audio','video','source','iframe'} else None
            if not attribute:continue
            raw=element.attrs.get(attribute,'')
            if not raw:continue
            url=urlsplit(urljoin(pageurl,raw))
            if url.scheme not in {'http','https'} or url.netloc!=urlbase.netloc:continue
            if not url.path.startswith(prefix):
                # Explicit links to another suite site are external to this build.
                if url.path.strip('/').split('/')[0] in PUBLIC_SITES:continue
                errors.append(f'{page.relative_to(root)}: site prefix missing from {raw!r}')
                continue
            relative=unquote(url.path[len(prefix):]);target=(root/relative).resolve()
            if not target.is_relative_to(root.resolve()):
                errors.append(f'{page.relative_to(root)}: path escapes built site: {raw!r}');continue
            if target.is_dir():target=target/'index.html'
            checked+=1
            if not target.is_file():errors.append(f'{page.relative_to(root)}: missing {raw!r}')
            elif url.fragment and target.suffix=='.html' and unquote(url.fragment) not in anchors.get(target,set()):
                errors.append(f'{page.relative_to(root)}: missing anchor {raw!r}')
    return errors,checked


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('repo',type=Path);a=ap.parse_args()
    errors,checked=audit(a.repo.resolve())
    for error in errors[:40]:print('::error::'+error)
    print(f'Local links: {checked} checked; {len(errors)} findings')
    return int(bool(errors))


if __name__=='__main__':raise SystemExit(main())
