#!/usr/bin/env python3
"""Validate source and rendered EQS structure; report content budgets honestly."""
from __future__ import annotations
import argparse
import collections
import html
import json
import os
from pathlib import Path
import re
import sys
import yaml
from blg_paths import front_matter, url_key
from build_materials_latex import strip_callouts
from html_tree import Element, parse

KIT = Path(__file__).resolve().parents[1]
KEYS = ['activate', 'input', 'practise', 'apply', 'reflect']
HEADING = re.compile(r'(?m)^##[ \t]+([^\n]+)')
ANCHOR = re.compile(r'\s*\{#([^}]+)\}\s*$')
EXCLUDED = re.compile(r'(?i)^(?:exam|prüfung|évaluation|teacher|notes pour|hinweise für lehr|downloads|sources|quellen|weiterführ|further reading|bildungsplan|curriculum framework)')

def sections(body):
    matches = list(HEADING.finditer(body))
    for i, m in enumerate(matches):
        title = m[1].strip(); key = ANCHOR.search(title)
        yield (key[1] if key else '', ANCHOR.sub('', title), body[m.end():matches[i+1].start() if i+1 < len(matches) else len(body)])

def plain_text(source):
    source = strip_callouts(source)
    source = re.sub(r'(?ms)^\s*(```|~~~).*?^\s*\1[^\n]*$', '', source)
    source = re.sub(r'\{\{[<%].*?[>%]\}\}', '', source, flags=re.S)
    source = re.sub(r'<[^>]+>', '', source)
    source = re.sub(r'!?\[([^\]]*)\]\([^)]*\)', r'\1', source)
    source = re.sub(r'\{#[^}]+\}', '', source)
    source = re.sub(r'(?m)^\s*\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)+\|?\s*$', '', source)
    source = re.sub(r'(?m)^\s*(?:#{1,6}\s+|>\s*|[-+*]\s+|\d+[.)]\s+)', '', source)
    source = re.sub(r'[*_`|\\]', '', source)
    return ' '.join(html.unescape(source).split())

def learner_body(body):
    parts = []
    # Include preamble; it contains authored learning objectives in some units.
    first = HEADING.search(body)
    if first: parts.append(body[:first.start()])
    for key, title, text in sections(body):
        if key in {'exam', 'teacher-notes', 'teacher_notes', 'sources', 'downloads', 'alignment'} or EXCLUDED.search(title):
            continue
        parts.append(title + '\n' + text)
        if key == 'reflect': break
    return '\n'.join(parts)

def word_count(body):
    return len(re.findall(r"[^\W_]+(?:[’'-][^\W_]+)*", plain_text(learner_body(body)), re.UNICODE))

def band(fm, spec):
    school = fm.get('klassenstufe')
    level = str((fm.get('curriculum') or {}).get('level') or fm.get('cefr_level') or '')
    for name, conf in spec['bands'].items():
        if school is not None and int(school) in conf['klassenstufen']: return str(name)
    for name, conf in spec['bands'].items():
        if level in conf['levels']: return str(name)
    return None

def exam_path(repo, value):
    if not isinstance(value, str) or not value or value.startswith('/'):
        return None
    base = (repo / 'content').resolve()
    stem = base / value
    for p in (stem / 'index.md', stem.with_suffix('.md')):
        if p.resolve().is_relative_to(base) and p.is_file(): return p
    return None

def rendered_text(node):
    if isinstance(node, str): return node
    if node.attrs.get('data-role') == 'key' or node.attrs.get('aria-hidden') == 'true' or node.tag in {'nav','footer','script','style'} or node.classes & {'downloads-section', 'heading-link'}:
        return ''
    parts = []; excluded = False
    for child in node.children:
        if isinstance(child, Element) and child.tag == 'h2':
            excluded = child.attrs.get('id') in {'teacher-notes','teacher_notes','sources','downloads','alignment'} or bool(EXCLUDED.search(child.text.strip()))
        if not excluded: parts.append(rendered_text(child))
    return ' '.join(parts)

def audit(repo, spec, include_drafts=False, built=None):
    repo = repo.resolve()
    built = built or repo / 'public'
    rows = []; owners = collections.defaultdict(list)
    for p in sorted((repo / 'content').rglob('*.md')):
        fm, body = front_matter(p)
        if fm.get('page_type') != 'unit' or (fm.get('draft') and not include_drafts): continue
        rel = str(p.relative_to(repo)); findings = []
        if fm.get('steps') != KEYS: findings.append('steps must declare exactly the five ordered canonical keys')
        parsed = list(sections(body)); keys = [key for key, _, _ in parsed if key in KEYS]
        if keys != KEYS: findings.append('the five keyed H2 headings must appear exactly once and in order')
        for key, title, text in parsed:
            if key in KEYS and not plain_text(text): findings.append(f'{key}: empty teaching step')
            if re.fullmatch(r'(?i)solutions?|answer keys?|lösungen', title.strip()) and plain_text(text): findings.append('bare answer section must use collapsible details')
        ex = fm.get('exam') or {}
        if not isinstance(ex, dict): ex = {}; findings.append('exam must be a metadata pointer')
        missing = [k for k in spec['assessment']['pointer_fields'] if ex.get(k) in (None, '', [])]
        if missing: findings.append('exam pointer missing reviewed values: '+', '.join(missing))
        ep = exam_path(repo, ex.get('page'))
        if ep is None: findings.append('exam.page does not resolve inside content')
        else:
            owners[str(ep.relative_to(repo))].append(rel)
            efm, _ = front_matter(ep)
            if efm.get('page_type') != 'exam': findings.append('exam.page must identify an exam page')
            if p.parent.parent != ep.parent.parent: findings.append('exam must be a sibling leaf bundle')
        for key, title, text in parsed:
            if key == 'exam':
                if len(plain_text(text)) > 650 or not re.search(r'\]\(|\{\{[<%]\s*ref',text):
                    findings.append('in-unit exam must be a short metadata/link pointer')
        b = band(fm,spec); words = word_count(body)
        if b is None: findings.append('no EQS word band can be determined')
        else:
            limits = spec['bands'][b]['unit_words']
            if not limits['minimum'] <= words <= limits['maximum']:
                findings.append(f'band {b}: {words} learner words outside {limits["minimum"]}–{limits["maximum"]}')
        rendered = built / url_key(p,repo/'content',fm).strip('/') / 'index.html'
        exam_chars = None
        if not rendered.is_file(): findings.append('rendered unit missing; build this source revision first')
        else:
            root = parse(rendered.read_text()); ids = collections.Counter(n.attrs['id'] for n in root.walk() if n.attrs.get('id'))
            for key in KEYS:
                nodes=[n for n in root.walk() if n.tag=='h2' and n.attrs.get('id')==key]
                if len(nodes)!=1: findings.append(f'rendered {key}: expected exactly one keyed H2')
            for group in (fm.get('anchor_aliases') or {}).values():
                for alias in group:
                    if ids[alias] != 1: findings.append(f'legacy fragment #{alias}: expected exactly one target')
        if ep is not None and b:
            efm,_=front_matter(ep); rendered_exam = built / url_key(ep,repo/'content',efm).strip('/') / 'index.html'
            if not rendered_exam.is_file(): findings.append('rendered sibling exam missing')
            else:
                tree=parse(rendered_exam.read_text()); articles=[n for n in tree.walk() if n.tag=='article']
                if len(articles)!=1: findings.append('exam must render exactly one article')
                else:
                    exam_chars=len(' '.join(rendered_text(articles[0]).split()))
                    minimum=spec['bands'][b]['exam_characters']['minimum']
                    if exam_chars<minimum: findings.append(f'exam: {exam_chars} learner characters below {minimum}')
        rows.append({'path':rel,'band':b,'learner_words':words,'exam_characters':exam_chars,'findings':findings})
    for ep, unit_paths in owners.items():
        if len(unit_paths)>1:
            for row in rows:
                if row['path'] in unit_paths: row['findings'].append(f'sibling exam shared by {len(unit_paths)} units: {ep}')
    return rows

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('repo',type=Path);parser.add_argument('--report',type=Path);parser.add_argument('--include-drafts',action='store_true');parser.add_argument('--built',type=Path)
    a=parser.parse_args(); framework=Path(os.environ.get('BLG_CURRICULUM',KIT.parent/'curriculum'))
    specpath=framework/'standards/eqs.yml'
    if not specpath.is_file(): print(f'::error::Missing canonical EQS contract: {specpath}');return 1
    canonical_map=framework/'standards/step-map.yml'; kit_map=KIT/'eqs/step-map.yml'
    if not canonical_map.is_file() or not kit_map.is_file() or yaml.safe_load(canonical_map.read_text()) != yaml.safe_load(kit_map.read_text()):
        print('::error::kit and curriculum teaching labels differ; synchronize the coordinated release');return 1
    spec=yaml.safe_load(specpath.read_text())
    if spec['steps'] != KEYS:
        print('::error::unsupported canonical step contract; upgrade the checker with the framework');return 1
    rows=audit(a.repo.resolve(),spec,a.include_drafts,a.built)
    if a.report:a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    findings=[f"{r['path']}: {f}" for r in rows for f in r['findings']]
    for f in findings[:40]:print('::error::'+f)
    print(f'EQS: {len(rows)} units; {sum(bool(r["findings"]) for r in rows)} with outstanding criteria; {len(findings)} findings')
    if len(findings)>40:print(f'{len(findings)-40} additional findings; use --report for the complete ledger')
    return int(bool(findings))
if __name__=='__main__':raise SystemExit(main())
