#!/usr/bin/env python3
"""Build the material discovery data from current course sources and real URLs.

Runs after Hugo; writes only the built tree. Every node corresponds to a unit
or one of its declared downloads. IDs use the stable, unique material key.
"""
from pathlib import Path
from collections import Counter
from itertools import combinations
from urllib.parse import urlsplit
import argparse
import json
import tomllib
import yaml
from blg_paths import front_matter, material_slug, url_key


def build(repo):
    config=tomllib.loads((repo/'hugo.toml').read_text())
    prefix=urlsplit(config['baseURL']).path.rstrip('/')
    content=repo/'content';nodes=[];articles=[];edges=[];ids=set()
    def local(url):
        if not url:return None
        if url.startswith(('https://','http://')):return url
        return url if url.startswith(prefix+'/') else prefix+'/'+url.lstrip('/')
    for page in sorted(content.rglob('*.md')):
        fm,body=front_matter(page)
        if fm.get('page_type')!='unit':continue
        slug=material_slug(page);article='article-'+slug
        if article in ids:raise ValueError(f'{page}: duplicate material key {slug}')
        ids.add(article)
        course='/'.join(page.relative_to(content).parts[:-2] if page.name=='index.md' else page.relative_to(content).parts[:-1]).split('/units')[0]
        tags=fm.get('tags') or []
        if not isinstance(tags,list):raise ValueError(f'{page}: tags must be a list')
        tags=sorted({str(t) for t in tags if not str(t).startswith('3.')})
        common={'title':fm['title'],'course':course,'topic':fm.get('topic',''),'tags':tags,'niveau':fm.get('niveau',''),'level':(fm.get('curriculum') or {}).get('level',''),'klassenstufe':fm.get('klassenstufe'),'track':fm.get('track',''),'unit_nr':fm.get('unit_nr'),'materials_status':fm.get('materials_status','committed')}
        parent={**common,'id':article,'type':'article','url':local(url_key(page,content)),'related':[]}
        nodes.append(parent);articles.append(parent)
        for kind,short in [('presentation','pres'),('worksheet','ws')]:
            material=fm.get(kind)
            if not material:continue
            if not isinstance(material,dict) or not material.get('file'):raise ValueError(f'{page}: {kind} has no file')
            nid=short+'-'+slug;parent['related'].append(nid)
            nodes.append({**common,'id':nid,'type':kind,'url':local(material['file']),'thumbnail':local(material.get('thumbnail')),'parent_article':article})
            edges.append({'id':nid+'--'+article,'source':nid,'target':article,'kind':'same-article','weight':3})
    if not articles:raise ValueError('network is enabled but no teaching units were found')
    for a,b in combinations(articles,2):
        common=set(a['tags'])&set(b['tags'])
        if len(common)>=2:edges.append({'id':a['id']+'--'+b['id'],'source':a['id'],'target':b['id'],'kind':'shared-tags','weight':min(len(common),5)})
    topics_path=repo/'data/topics.yml'
    topics=yaml.safe_load(topics_path.read_text()) if topics_path.exists() else []
    labels={x['id']:x for x in topics if isinstance(x,dict) and x.get('id')}
    facets={}
    for facet in ['type','topic','course','tags']:
        counts=Counter(v for n in nodes for v in (n.get(facet,[]) if facet=='tags' else [n.get(facet,'')]) if v)
        facets[{'type':'types','topic':'topics','course':'courses','tags':'tags'}[facet]]=[{**labels.get(key,{}),'id':key,'label':labels.get(key,{}).get('label',key),'count':value} for key,value in sorted(counts.items())]
    document={'schema_version':1,'nodes':nodes,'edges':edges,'facets':facets,'stats':{'articles':len(articles),'nodes':len(nodes),'edges':len(edges)}}
    # Validate every generated local destination, including teaching-page URLs.
    for node in nodes:
        for field in ['url','thumbnail']:
            url=node.get(field)
            if not url or urlsplit(url).netloc:continue
            path=repo/'public'/url[len(prefix)+1:]
            if path.is_dir():path=path/'index.html'
            if not path.is_file():raise ValueError(f'{node["id"]}: {field} points to missing {url}')
    return document


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('repo',type=Path);a=ap.parse_args();repo=a.repo.resolve()
    try:document=build(repo)
    except (OSError,ValueError,KeyError) as exc:print(f'::error::{exc}');return 1
    text=json.dumps(document,ensure_ascii=False,separators=(',',':'))+'\n'
    # Both existing graph addresses stay supported.
    for relative in ['network/graph.json','materials/graph.json']:
        p=repo/'public'/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
    print(f'Material network: {document["stats"]}')
    return 0


if __name__=='__main__':raise SystemExit(main())
