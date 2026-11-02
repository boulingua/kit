#!/usr/bin/env python3
"""Stage source-faithful learner/teacher assessment PDFs without changing a course.

Uses the shared worksheet typography and Markdown renderer. Review and publishing
are separate: an export preserves source content; it does not approve an exam.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

import yaml
import build_materials_latex as materials
from blg_paths import is_exam_page

CODE_PATHS = {'generator_sha256': Path(__file__), 'renderer_sha256': Path(materials.__file__)}
CODE_HASHES = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in CODE_PATHS.items()}


def verify_producer_identity():
    for name, path in CODE_PATHS.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != CODE_HASHES[name]:
            raise RuntimeError(f'producer changed after loading: {path}')


def validate_output_root(output, repo):
    """An external stage must not redirect any descendant into live files."""
    output, repo = output.resolve(), repo.resolve()
    if output == repo or output.is_relative_to(repo):
        raise ValueError('staged output must be outside the course checkout')
    if output.exists() and not output.is_dir():
        raise ValueError('staged output must be a directory')
    for path in output.rglob('*'):
        if path.is_symlink():
            raise ValueError(f'staged output contains a symlink: {path}')

CHECKBOX = r"""
\newcommand{\blgchecksquare}{%
  \leavevmode%
  \special{pdf:literal direct /Span << /ActualText <FEFF25A2> >> BDC}%
  \makebox[0pt][l]{\special{pdf:literal direct 3 Tr}.\special{pdf:literal direct 0 Tr}}%
  \tikz[baseline=-0.1ex]\draw[rounded corners=0.7pt,line width=0.4pt] (0,0) rectangle (0.7em,0.7em);%
  \special{pdf:literal direct EMC}}
"""

TOPIC_ICON = r"""
\newcommand{\blgtopicicon}[2]{%
  \leavevmode%
  \special{pdf:literal direct /Span << /ActualText <FEFF#1> >> BDC}%
  \makebox[0pt][l]{\special{pdf:literal direct 3 Tr}.\special{pdf:literal direct 0 Tr}}%
  \tikz[x=1em,y=1em,baseline=-0.15ex,line width=0.4pt]{%
    \path[use as bounding box] (0,0) rectangle (1,1);#2}%
  \special{pdf:literal direct EMC}}
"""
TOPIC_ICONS = {
    '🎸': r'\draw[rotate around={-35:(0.5,0.5)}] (0.4,0.25) ellipse (0.22 and 0.27);\draw[rotate around={-35:(0.5,0.5)}] (0.35,0.44) rectangle (0.45,0.91);\draw (0.34,0.31) circle (0.055);',
    '⚽': r'\draw (0.5,0.5) circle (0.43);\draw (0.5,0.73)--(0.72,0.57)--(0.63,0.31)--(0.37,0.31)--(0.28,0.57)--cycle;\draw (0.5,0.73)--(0.5,0.93) (0.72,0.57)--(0.91,0.63) (0.63,0.31)--(0.76,0.16) (0.37,0.31)--(0.24,0.16) (0.28,0.57)--(0.09,0.63);',
    '📚': r'\draw (0.1,0.12) rectangle (0.85,0.34);\draw (0.2,0.37) rectangle (0.95,0.59);\draw (0.08,0.62) rectangle (0.83,0.84);\draw (0.23,0.12)--(0.23,0.34) (0.33,0.37)--(0.33,0.59) (0.21,0.62)--(0.21,0.84);',
    '📷': r'\draw[rounded corners=0.7pt] (0.08,0.18) rectangle (0.93,0.77);\draw (0.3,0.77)--(0.37,0.92)--(0.63,0.92)--(0.7,0.77);\draw (0.5,0.48) circle (0.2);\fill (0.81,0.65) circle (0.035);',
}


def read_source(source: Path):
    text = source.read_text(encoding='utf-8')
    match = re.match(r'^---\n(.*?)\n---\n(.*)$', text, re.S)
    if not match:
        raise ValueError(f'{source}: YAML front matter is required')
    fm = yaml.safe_load(match[1])
    if not isinstance(fm, dict) or fm.get('page_type') != 'exam':
        raise ValueError(f'{source}: page_type must be exam')
    unknown = set(re.findall(r'\{\{<\s*/?\s*([\w-]+)', match[2])) - {'callout', 'details', 'tl'}
    if unknown:
        raise ValueError(f'{source}: unsupported assessment shortcodes: {sorted(unknown)}')
    if re.search(r'!\[|<\s*(?:img|picture|svg|video|audio)\b', match[2], re.I):
        raise ValueError(f'{source}: image and media stimuli require an asset-aware exporter')
    assessment_tree(match[2])
    return fm, match[2], hashlib.sha256(text.encode()).hexdigest()


def assessment_tree(body):
    """Hide explicit keys, preserve public scoring, reject ambiguous old keys."""
    nodes = materials.callout_tree(body)
    attributes = iter(match[3] for match in materials.WRAPPER.finditer(body) if not match[1])
    def classify(children):
        for node in children:
            if isinstance(node, str):
                continue
            attrs = next(attributes)
            explicit = re.search(r'\brole\s*=\s*(?:"key"|\'key\'|key(?=\s|$))', attrs)
            rubric = (re.match(r'(?i)^(?:barème|notenschlüssel)\b', node['title'].strip())
                      and not re.search(r'(?i)l\wsung|answer\s*key|solution|corrig', node['title']))
            if node['answer'] and not explicit and not rubric:
                raise ValueError('answer-bearing assessment block needs explicit role="key": ' + node['title'])
            node['answer'] = bool(explicit)
            classify(node['children'])
    classify(nodes)
    return nodes


def destination(fm, source, repo):
    """Keep the established DaF download URL, otherwise use an explicit slug."""
    if materials.SITE == 'daf':
        level, slug, number = fm.get('cefr_level', '').lower(), fm.get('unit_slug'), fm.get('unit_nr')
        if level not in {'a1', 'a2', 'b1', 'b2', 'c1', 'c2'} or not slug or not isinstance(number, int):
            raise ValueError(f'{source}: incomplete established assessment path metadata')
        stem = f'unit{number:02d}_{slug}_exam'
        result = Path('static/downloads') / level / f'{stem}.pdf'
    else:
        slug = fm.get('material_slug')
        if not isinstance(slug, str) or not re.fullmatch(r'[a-z0-9_-]+', slug):
            raise ValueError(f'{source}: an explicit safe material_slug is required')
        result = Path('static/materials/assessments') / f'{slug}.pdf'
    if '..' in result.parts or result.is_absolute() or not re.fullmatch(r'[a-z0-9_./-]+', str(result)):
        raise ValueError(f'{source}: unsafe assessment destination')
    return result


def assessment_layout(rendered):
    """Keep source paths breakable and give statements space beside checkboxes."""
    def code(match):
        value = re.sub(r'(\\_|/|-)', lambda part: part[0] + r'\allowbreak{}', match[1])
        return r'\texttt{' + value + '}'
    rendered = re.sub(r'\\texttt\{([^{}]*)\}', code, rendered)
    # Justification cannot stretch a path fragment. A ragged paragraph lets
    # TeX actually use these break opportunities without overflowing the page.
    rendered = '\n'.join(r'\begingroup\raggedright ' + line + r'\endgroup'
                         if r'\texttt{' in line and line.endswith(r'\par')
                         else line for line in rendered.splitlines())

    def choice_table(match):
        rows = [row.strip() for row in match[2].split(r'\\') if row.strip()]
        cells = [[cell.strip().removeprefix(r'\midrule').strip() for cell in row.split(' & ')] for row in rows]
        width = len(cells[0])
        if width < 4 or any(len(row) != width for row in cells):
            return match[0]
        plain = [[re.sub(r'\\text(?:bf|it)\{([^{}]*)\}', r'\1', cell) for cell in row] for row in cells]
        lengths = [max(len(row[i]) for row in plain) for i in range(width)]
        # A statement with small number/answer columns needs asymmetric space.
        # Ordinary rubrics and all-text tables retain the shared layout.
        wide = [i for i, length in enumerate(lengths) if length > 8]
        if len(wide) != 1 or any('\\' in row[i] for row in plain for i in range(width) if i not in wide):
            return match[0]
        columns = []
        for i in range(width):
            # Natural-width answer columns use actual font metrics, including
            # bold headers; the statement takes the remaining line width.
            size = 'X' if i in wide else 'l'
            columns.append(r'>{\raggedright\arraybackslash}' + size)
        return (r'\begin{tabularx}{\linewidth}{@{}' + ''.join(columns) + '@{}}\n' +
                match[2] + r'\bottomrule\end{tabularx}')
    return re.sub(r'\\begin\{tabularx\}\{\\linewidth\}\{(@\{\}.*?@\{\})\}\n(.*?)\\bottomrule\\end\{tabularx\}',
                  choice_table, rendered, flags=re.S)


def document(fm, body, teacher=False):
    config = yaml.safe_load((materials.REPO / 'boulingua.yml').read_text()) or {}
    language = config.get('chrome_language') or {'daf':'de', 'fle':'fr', 'efl':'en'}.get(materials.SITE)
    labels = {
        'de': ('german', ' — Lehrkraftfassung', 'Prüfungsübung · Reviewfassung'),
        'en': ('english', ' — Teacher copy', 'Assessment practice · Review copy'),
        'fr': ('french', ' — Version enseignant', 'Évaluation pratique · Version à relire'),
    }
    if language not in labels:
        raise ValueError(f'unsupported instructional language: {language}')
    ui, suffix, review = labels[language]
    nodes = assessment_tree(body)
    visible = materials.unwrap_callouts(nodes, hide_answers=not teacher)
    title = str(fm['title'])
    identity = title + (suffix if teacher else '')
    subtitle = review if fm.get('assessment_review') != 'approved' else ''
    if teacher:
        subtitle = suffix.strip(' —') + (' · ' + subtitle if subtitle else '')
    # Assessment copies must carry offline attribution and usable source links.
    rendered = assessment_layout(materials.reference_blocks(visible)).replace('▢', r'\blgchecksquare{}')
    pictograms = False
    for character, drawing in TOPIC_ICONS.items():
        if character in rendered:
            pictograms = True
            rendered = rendered.replace(character, r'\blgtopicicon{' + character.encode('utf-16-be').hex().upper() + '}{' + drawing + '}')
    # The role belongs on the subtitle line; retain it in metadata and every
    # footer without making an already long assessment heading overflow.
    template = materials.TEX_SHEET.replace(r'\begin{document}', CHECKBOX + '\n' + r'\begin{document}')
    if pictograms:
        template = template.replace(r'\begin{document}', TOPIC_ICON + '\n' + r'\begin{document}', 1)
    template = template.replace(r'\begin{sheetbody}',
        r'\gdef\blgtitle{' + materials.inline(identity) + '}\n' +
        r'\hypersetup{pdftitle={' + materials.inline(identity) + '}}\n' + r'\begin{sheetbody}')
    return materials.finish_document(template.replace('@@TITLE@@', materials.inline(title))
            .replace('@@SUBTITLE@@', materials.inline(subtitle))
            .replace('@@BADGE@@', materials.esc(str(fm.get('cefr_level', ''))))
            .replace('@@LANG@@', materials.SITE).replace('@@UI@@', ui)
            .replace('@@SECTIONS@@', rendered).replace('@@ANSWERS@@', ''))


def reserve_targets(relative, targets):
    for target in (relative, relative.with_stem(relative.stem + '-teacher')):
        if target in targets:
            raise ValueError(f'duplicate assessment destination: {target}')
        targets.add(target)


def support_inventory(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.rglob('*')) if path.is_file()}


def prepare_workspace(workspace):
    """A reused destination must retain the exact original typesetting inputs."""
    support = materials.REPO / '_materials'
    expected = support_inventory(support)
    manifest = workspace / '.assessment-support.json'
    if workspace.exists():
        try:
            recorded = json.loads(manifest.read_text())
        except (OSError, ValueError) as exc:
            raise ValueError('assessment workspace has no valid support receipt; use a fresh output root') from exc
        if recorded != expected:
            raise ValueError('assessment support changed; use a fresh output root')
        for relative, digest in expected.items():
            path = workspace / relative
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError('assessment workspace support changed; use a fresh output root')
    else:
        shutil.copytree(support, workspace)
        manifest.write_text(json.dumps(expected, indent=2, sort_keys=True) + '\n')
    return expected


def process(source, output):
    output = output.resolve()
    validate_output_root(output, materials.REPO)
    base_materials = materials.MAT.resolve()
    if not base_materials.is_relative_to(output.resolve()):
        raise ValueError('assessment materials must be configured inside the external stage')
    fm, body, source_hash = read_source(source)
    relative = destination(fm, source, materials.REPO)
    # Mirror the destination directory, so equal names in separate levels keep
    # separate TeX/log evidence as well as separate PDF destinations.
    workspace = base_materials / relative.parent.relative_to('static')
    support = prepare_workspace(workspace)
    validate_output_root(output, materials.REPO)
    record = {'source': str(source.relative_to(materials.REPO)), 'source_sha256': source_hash,
              'status': 'staged-review-copy', 'support_sha256': support, 'outputs': {}}
    for teacher in (False, True):
        role = 'teacher' if teacher else 'learner'
        target = output / relative
        if teacher:
            target = target.with_stem(target.stem + '-teacher')
        tex = workspace / (target.stem + '.tex')
        tex.write_text(document(fm, body, teacher), encoding='utf-8')
        try:
            materials.MAT = workspace
            okay, result = materials.xelatex(tex)
        finally:
            materials.MAT = base_materials
        if not okay:
            raise RuntimeError(f'{source}: {role} compilation failed\n{(result.stdout + result.stderr)[-2000:]}')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tex.with_suffix('.pdf'), target)
        materials.thumb(target, target.with_suffix('.png'))
        record['outputs'][role] = {'file': str(target.relative_to(output)),
            'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
            'tex_sha256': hashlib.sha256(tex.read_bytes()).hexdigest(),
            'tex_file': str(tex.relative_to(output)),
            'log_file': str(tex.with_suffix('.log').relative_to(output))}
    if hashlib.sha256(source.read_bytes()).hexdigest() != source_hash:
        raise RuntimeError(f'{source}: source changed during generation')
    if support_inventory(materials.REPO / '_materials') != support:
        raise RuntimeError('assessment support changed during generation; use a fresh output root')
    prepare_workspace(workspace)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--only', default='')
    parser.add_argument('--limit', type=int, default=0)
    args = parser.parse_args()
    if args.limit < 0:
        parser.error('--limit must be nonnegative')
    output = args.output_root.resolve()
    validate_output_root(output, args.repo)
    verify_producer_identity()
    materials.configure(args.repo, output)
    sources = sorted(p for p in materials.REPO.glob('content/**/*.md')
                     if is_exam_page(p) and args.only in str(p))
    if args.limit:
        sources = sources[:args.limit]
    if not sources:
        parser.error('no assessment source matched')
    records, errors, targets = [], [], set()
    # Reject collisions before producing any PDFs.
    for source in sources:
        fm, _, _ = read_source(source)
        target = destination(fm, source, materials.REPO)
        reserve_targets(target, targets)
    for source in sources:
        try:
            verify_producer_identity()
            record = process(source, output)
            verify_producer_identity()
            records.append(record)
            print(f'[OK] {source.relative_to(materials.REPO)}', flush=True)
        except (ValueError, OSError, RuntimeError) as exc:
            errors.append({'source': str(source.relative_to(materials.REPO)), 'error': str(exc)})
            print(f'[FAILED] {exc}', file=sys.stderr, flush=True)
        receipt = {**CODE_HASHES,
                   'assessments': records, 'errors': errors}
        (output / 'assessments-receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n')
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
