#!/usr/bin/env python3
"""Generate branded per-unit materials from each unit's own content.

For courses with English, French or German instructional chrome, derives a slide deck
(slidegen/Beamer), a learner worksheet and a separate teacher answer copy
(sheetgen) — real content pulled from the
unit markdown, no re-authoring — compiles them with XeLaTeX in the boulingua
design language (the site's signature accent + pentagon mark + foot watermark),
renders a thumbnail, writes the PDFs under static/materials/, and rewrites the
unit's presentation:/worksheet: front matter to the open-format PDFs.

The declared site code selects the LaTeX accent
via \\blgsetlang and the /<site> URL prefix. Section names, answer-key formats
and the flat slug are detected across English, French and German units.

Usage:
  build_materials_latex.py [REPO] [--only SLUG_SUBSTR] [--limit N] [--keep-tex]
                          [--output-root EXTERNAL_STAGING_DIRECTORY]
Without --output-root, writes course artifacts and presentation/worksheet/
worksheet_teacher front matter. With it, copies the synced _materials support
tree, writes all artifacts and a digest receipt outside the course, and leaves
course files unchanged. Review staging before publishing a rebuilt corpus.
Requires xelatex and the vendored templates in
_materials/.
"""
import sys, os, re, subprocess, argparse, shutil, tempfile, hashlib, json
import yaml
from blg_paths import material_slug, site_code, SiteError, is_exam_page
from pathlib import Path

REPO = Path.cwd()
SITE = ''
MAT = REPO / '_materials'
PRES = REPO / 'static/materials/presentations'
WORK = REPO / 'static/materials/worksheets'
URL = ''
STAGED = False
OUTPUT_ROOT = REPO
TARGET_OWNERS = {}
PRODUCER_PATH = Path(__file__)
PRODUCER_SHA256 = hashlib.sha256(PRODUCER_PATH.read_bytes()).hexdigest()


def verify_producer_identity():
    if hashlib.sha256(PRODUCER_PATH.read_bytes()).hexdigest() != PRODUCER_SHA256:
        raise RuntimeError('material producer changed after loading; restart with a fresh output root')


def configure(repo, output_root=None):
    global REPO, SITE, MAT, PRES, WORK, URL, L, STAGED, OUTPUT_ROOT, TARGET_OWNERS
    verify_producer_identity()
    REPO = Path(repo).resolve()
    OUTPUT_ROOT, TARGET_OWNERS = REPO, {}
    SITE = site_code(REPO)
    config = yaml.safe_load((REPO / 'boulingua.yml').read_text()) or {}
    if config.get('code') != SITE:
        raise ValueError('boulingua.yml and Hugo must declare the same site code')
    MAT = REPO / '_materials'
    PRES = REPO / 'static/materials/presentations'
    WORK = REPO / 'static/materials/worksheets'
    URL = '/' + SITE
    chrome = config.get('chrome_language', {'efl': 'en', 'fle': 'fr', 'daf': 'de'}.get(SITE))
    if chrome not in LABELS:
        raise ValueError(f'materials require reviewed en/fr/de chrome_language; got {chrome!r} for {SITE}')
    L = LABELS[chrome]
    STAGED = output_root is not None
    if STAGED:
        output = Path(output_root).resolve()
        validate_stage_root(output, REPO)
        OUTPUT_ROOT = output
        if not MAT.is_dir():
            raise ValueError('_materials is missing; run kit sync REPO first')
        target = output / '_materials'
        shutil.copytree(MAT, target, dirs_exist_ok=True)
        MAT = target
        PRES = output / 'static/materials/presentations'
        WORK = output / 'static/materials/worksheets'


def validate_stage_root(output, repo):
    output, repo = Path(output).resolve(), Path(repo).resolve()
    if output == repo or output.is_relative_to(repo):
        raise ValueError('staged output must be outside the course checkout')
    if output.exists() and not output.is_dir():
        raise ValueError('staged output must be a directory')
    for path in output.rglob('*'):
        if path.is_symlink():
            raise ValueError(f'staged output contains a symlink: {path}')


def validate_artifact_path(path, root):
    path, root = Path(path), Path(root).resolve()
    if not path.resolve().is_relative_to(root):
        raise ValueError(f'material artifact escapes its output root: {path}')
    for ancestor in (path, *path.parents):
        if ancestor == root:
            break
        if ancestor.is_symlink():
            raise ValueError(f'material artifact uses a symlink: {ancestor}')


def reserve_material_targets(slug, source, owners):
    source = Path(source).resolve()
    for directory, stem in [('presentations', slug), ('worksheets', slug),
                            ('worksheets', slug + '-teacher')]:
        for suffix in ('.pdf', '.png'):
            target = Path('static/materials') / directory / (stem + suffix)
            if target in owners and owners[target] != source:
                raise ValueError(f'duplicate material destination: {target}')
            owners[target] = source


def preflight_material_targets(units):
    owners = {}
    for source in units:
        reserve_material_targets(unit_slug(source, source.read_text()), source, owners)
    return owners


GREEK_ACTUAL_TEXT = r"""
% Preserve Greek code points when the font reuses a glyph for Latin IPA.
\newcommand{\blggreek}[2]{\texorpdfstring{%
  \special{pdf:literal direct /Span << /ActualText <FEFF#1> >> BDC}%
  #2\special{pdf:literal direct EMC}}{#2}}
"""


def preserve_greek_characters(text):
    return re.sub(r'[\u0370-\u03ff\u1f00-\u1fff]',
                  lambda match: r'\blggreek{' + match[0].encode('utf-16-be').hex().upper() + '}{' + match[0] + '}', text)


# Original vector drawings retain authored characters absent from the text face.
# The invisible text anchor makes ActualText available to both PDF extractors.
AUTHORED_SYMBOL_MACRO = r"""
\newcommand{\blgauthoredsymbol}[2]{\leavevmode%
  \special{pdf:literal direct /Span << /ActualText <FEFF#1> >> BDC}%
  \makebox[0pt][l]{\special{pdf:literal direct 3 Tr}.\special{pdf:literal direct 0 Tr}}%
  \tikz[x=1em,y=1em,baseline=-0.15ex,line width=0.45pt]{%
    \path[use as bounding box] (0,0) rectangle (1,1);#2}%
  \special{pdf:literal direct EMC}}
"""
_STAR = r'(0.5,0.95)--(0.62,0.63)--(0.96,0.62)--(0.69,0.41)--(0.79,0.08)--(0.5,0.27)--(0.21,0.08)--(0.31,0.41)--(0.04,0.62)--(0.38,0.63)--cycle;'
AUTHORED_SYMBOLS = {
    '★': r'\fill '+_STAR,
    '⭐': r'\draw '+_STAR,
    '⬜': r'\draw (0.08,0.08) rectangle (0.92,0.92);',
    '⏤': r'\draw (0.03,0.5)--(0.97,0.5);',
    '⬤': r'\fill (0.5,0.5) circle (0.44);',
    '◐': r'\draw (0.5,0.5) circle (0.44);\fill (0.5,0.06) arc[start angle=-90,end angle=-270,radius=0.44]--cycle;',
    '⚑': r'\draw (0.2,0.05)--(0.2,0.95);\fill (0.2,0.9)--(0.88,0.9)--(0.88,0.48)--(0.2,0.48)--cycle;',
    '🙁': r'\draw (0.5,0.5) circle (0.44);\fill (0.35,0.63) circle (0.045) (0.65,0.63) circle (0.045);\draw (0.27,0.27) .. controls (0.38,0.47) and (0.62,0.47) .. (0.73,0.27);',
    '😄': r'\draw (0.5,0.5) circle (0.44);\draw (0.25,0.59) .. controls (0.31,0.74) and (0.39,0.74) .. (0.45,0.59);\draw (0.55,0.59) .. controls (0.61,0.74) and (0.69,0.74) .. (0.75,0.59);\draw (0.25,0.45)--(0.75,0.45) .. controls (0.65,0.08) and (0.35,0.08) .. (0.25,0.45);',
    '🏠': r'\draw (0.1,0.48)--(0.5,0.9)--(0.9,0.48);\draw (0.2,0.48)--(0.2,0.12)--(0.8,0.12)--(0.8,0.48);\draw (0.43,0.12) rectangle (0.61,0.42);\draw (0.28,0.48) rectangle (0.4,0.61);',
    '📅': r'\draw (0.1,0.12) rectangle (0.9,0.85);\draw (0.1,0.64)--(0.9,0.64) (0.3,0.95)--(0.3,0.76) (0.7,0.95)--(0.7,0.76);\foreach \x in {0.28,0.5,0.72}{\foreach \y in {0.3,0.47}{\fill (\x,\y) circle (0.035);}}',
    '🎂': r'\draw (0.1,0.12) rectangle (0.9,0.57);\draw (0.1,0.4)--(0.9,0.4);\foreach \x in {0.3,0.5,0.7}{\draw (\x,0.57)--(\x,0.78);\fill (\x,0.87) circle (0.035);}',
    '🎁': r'\draw (0.14,0.1) rectangle (0.86,0.64);\draw (0.08,0.64) rectangle (0.92,0.77);\draw (0.45,0.1)--(0.45,0.77) (0.55,0.1)--(0.55,0.77);\draw (0.5,0.77) .. controls (0.05,1.12) and (0.2,0.71) .. (0.5,0.77);\draw (0.5,0.77) .. controls (0.95,1.12) and (0.8,0.71) .. (0.5,0.77);',
    '🍕': r'\draw (0.12,0.83)--(0.52,0.08)--(0.91,0.83);\draw (0.12,0.83) .. controls (0.4,0.99) and (0.62,0.99) .. (0.91,0.83);\draw (0.18,0.72) .. controls (0.4,0.86) and (0.62,0.86) .. (0.85,0.72);\fill (0.4,0.63) circle (0.05) (0.64,0.6) circle (0.05) (0.52,0.39) circle (0.05);',
    '🎉': r'\draw (0.12,0.12)--(0.3,0.67)--(0.67,0.3)--cycle;\draw (0.47,0.58)--(0.66,0.91) (0.61,0.48)--(0.92,0.67);\draw (0.34,0.75)--(0.25,0.94) (0.75,0.34)--(0.94,0.25);\fill (0.85,0.87) circle (0.04) (0.53,0.97) circle (0.03);',
}


def preserve_authored_symbols(text):
    for character, drawing in AUTHORED_SYMBOLS.items():
        text = text.replace(character, r'\blgauthoredsymbol{' + character.encode('utf-16-be').hex().upper() + '}{' + drawing + '}')
    return text


def finish_document(text):
    if r'\blgauthoredsymbol{' in text:
        text = text.replace(r'\begin{document}', AUTHORED_SYMBOL_MACRO + '\n' + r'\begin{document}', 1)
    if r'\blggreek{' in text:
        return text.replace(r'\begin{document}', GREEK_ACTUAL_TEXT + '\n' + r'\begin{document}', 1)
    return text


# ---------- markdown → LaTeX ----------
SPECIAL = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$',
           '#': r'\#', '_': r'\_', '{': r'\{', '}': r'\}',
           '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
def esc(s):
    return ''.join(SPECIAL.get(c, c) for c in s)

def inline(s):
    """Convert a line of markdown to LaTeX (bold/italic/code, drop links/md)."""
    s = s.strip()
    # Backslash escapes are literal punctuation in Markdown; keep them outside
    # emphasis/link parsing, while leaving inline-code contents literal.
    code_spans = []
    def protect_code(match):
        value = match[2].replace('\n', ' ')
        if value.startswith(' ') and value.endswith(' ') and value.strip():
            value = value[1:-1]
        token = '\x09' + str(len(code_spans)) + '\x0b'
        code_spans.append((token, value))
        return token
    s = re.sub(r'(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)', protect_code, s)
    escaped = []
    def protect_escape(match):
        if match[1] is None:
            return match[0]
        token = '\x07' + str(len(escaped)) + '\x08'
        escaped.append((token, match[1]))
        return token
    punctuation = r'!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
    s = re.sub(r'`[^`]+`|\\([' + re.escape(punctuation) + '])', protect_escape, s)
    s = re.sub(r'\{\{<[^>]*>\}\}', '', s)               # shortcodes
    s = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', s)          # images
    s = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', s)      # links -> text
    # sentinel-protect emphasis, then escape, then re-insert commands
    B,Bc,I,Ic = '\x01','\x02','\x03','\x04'
    s = re.sub(r'\*\*\*(.+?)\*\*\*', B+I+r'\1'+Ic+Bc, s)        # bold-italic
    s = re.sub(r'\*\*(.+?)\*\*', B+r'\1'+Bc, s)                 # bold
    s = re.sub(r'(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)', I+r'\1'+Ic, s)   # italic
    s = re.sub(r'(?<![\w_])_(?![_\s])([^_]+?)(?<!\s)_(?![\w_])', I+r'\1'+Ic, s)
    s = s.replace('*', '')                                       # strip stray markers
    s = esc(s)
    s = (s.replace(B,r'\textbf{').replace(Bc,'}')
           .replace(I,r'\textit{').replace(Ic,'}'))
    for token, value in code_spans:
        s = s.replace(token, r'\texttt{' + esc(value) + '}')
    for token, character in escaped:
        s = s.replace(token, esc(character))
    # Authored differentiation mark, outside Source Sans 3's character map.
    # Draw the five-point star and retain U+2B51 as PDF ActualText.
    s = s.replace('⭑', r'\blgdifficultystar{}')
    # No symbol substitution. Thirteen arrows and operators used to be rewritten
    # into math mode here because the bundled 781-codepoint subset lacked them.
    # All thirteen are in the shipped payload now, and the hack was doing active
    # harm: $\to$ renders a LEFT-pointing arrow inside an Arabic run, and going
    # through math mode pulls Computer Modern Symbol into the document — every
    # committed worksheet containing an arrow embeds /XWKGGV+CMSY10, a second
    # typeface family, for one glyph. Gate D5's cmap guard replaces the table:
    # a character the face cannot render fails the build instead of being
    # silently swapped for something that looks close.
    s = re.sub(r'(?:\\_){2,}', lambda match: r'\allowbreak{}'.join([r'\_'] * (len(match[0]) // 2)), s)
    return preserve_authored_symbols(preserve_greek_characters(s))

# ---------- unit parsing ----------
def parse(md):
    m = re.match(r'^---\n(.*?)\n---\n(.*)$', md, re.S)
    fm_raw, body = (m.group(1), m.group(2)) if m else ("", md)
    fm = yaml.safe_load(fm_raw) or {}
    if not isinstance(fm, dict):
        raise ValueError('unit front matter must be a mapping')
    # split into level-2 sections (keep level-3 inside)
    parts = re.split(r'(?m)^##\s+(.+?)\s*$', body)
    secs = []  # (title, text)
    for i in range(1, len(parts), 2):
        secs.append((SectionTitle(parts[i]), parts[i+1].strip()))
    return fm, secs

class SectionTitle(str):
    """Printed heading text carrying its explicit, language-independent step."""
    def __new__(cls, text):
        value = super().__new__(cls, heading_text(text))
        match = re.search(r'\{#([\w:-]+)\}\s*$', text)
        value.anchor = match.group(1) if match else None
        return value


def heading_text(text):
    """Hugo heading anchors are identifiers, never printed lesson text."""
    return re.sub(r'\s*\{#[\w:-]+\}\s*$', '', text).strip()

def norm(t):
    return re.sub(r'^\d+\.?\s*', '', t).strip().lower()

ANSWER_TITLE = re.compile(r'l\wsung|answer\s*key|solution|corrig|barème|notenschlüssel', re.I)
WRAPPER = re.compile(r'\{\{<\s*(/?)\s*(callout|details)\b([^>]*?)>\}\}', re.S)


def callout_tree(text):
    """Parse the two instructional wrapper types, including nested wrappers.

    A single regex replacement misses answers nested inside support callouts.
    Unbalanced markup is rejected rather than allowing an ambiguous learner copy.
    """
    root = []
    stack = [(None, root)]
    cursor = 0
    for match in WRAPPER.finditer(text):
        stack[-1][1].append(text[cursor:match.start()])
        closing, tag, attrs = match.groups()
        if closing:
            if len(stack) == 1 or stack[-1][0] != tag:
                raise ValueError(f'mismatched instructional shortcode: /{tag}')
            stack.pop()
        else:
            title = re.search(r'\b(?:title|summary)\s*=\s*(["\'])(.*?)\1', attrs, re.S)
            label = title.group(2) if title else ''
            explicit_key = re.search(r'\brole\s*=\s*(?:"key"|\'key\'|key(?=\s|$))', attrs)
            node = {'title': label, 'answer': bool(explicit_key or ANSWER_TITLE.search(label)), 'children': []}
            stack[-1][1].append(node)
            stack.append((tag, node['children']))
        cursor = match.end()
    stack[-1][1].append(text[cursor:])
    if len(stack) != 1:
        raise ValueError(f'unclosed instructional shortcode: {stack[-1][0]}')
    return root


def unwrap_callouts(nodes, hide_answers=False):
    out = []
    for node in nodes:
        if isinstance(node, str):
            out.append(node)
        elif not (hide_answers and node['answer']):
            title = f"**{node['title']}**\n\n" if node['title'] else ''
            out.append('\n\n' + title + unwrap_callouts(node['children'], hide_answers).strip() + '\n\n')
    return ''.join(out)


def strip_callouts(text):
    """Hide nested answer keys but retain instructional support and hints."""
    return unwrap_callouts(callout_tree(text), hide_answers=True)

# section-name synonyms across English / French / German units
SEC = {
    "objectives": ("learning objectives", "objectives", "lernziele", "objectifs"),
    "leadin":     ("lead-in", "lead in", "einstieg", "situation de départ",
                   "situation de depart", "situation"),
    "input":      ("input", "apporter"),
    "vocab":      ("vocabulary", "wortschatz", "vocabulaire", "wörter", "worter"),
    "practise":   ("practise", "practice", "üben", "uben", "s'entraîner",
                   "s'entrainer", "entraîner", "entrainer"),
    "produce":    ("produce", "anwenden", "produire", "produktion"),
    "reflect":    ("reflect", "reflexion", "réfléchir", "reflechir"),
    "solutions":  ("solutions", "lösungen", "losungen", "corrigé", "corrige"),
}

def find_sec(secs, *names):
    for t, body in secs:
        n = norm(t)
        if any(k in n for k in names): return strip_callouts(body)
    return ""

def bullets(text):
    """List items ('- ' / '1. ' / '- [ ] '), joining soft-wrapped
    continuation lines into the item they belong to."""
    out, cur = [], None
    for ln in text.split('\n'):
        mm = re.match(r'^\s*(?:[-*]|\d+\.)\s+(?:\[[ xX]?\]\s*)?(.+)$', ln)
        if mm:
            if cur is not None: out.append(cur.strip())
            cur = mm.group(1).strip()
        elif cur is not None:
            s = ln.strip()
            if not s or s.startswith(('#', '>', '|', '{{<')):
                out.append(cur.strip()); cur = None
            else:
                cur += ' ' + s
    if cur is not None: out.append(cur.strip())
    return out

def paragraphs(text):
    """Non-list, non-heading, non-shortcode paragraphs."""
    out, buf = [], []
    for ln in text.split('\n'):
        s = ln.strip()
        if not s or s.startswith(('#','>','|','{{<')) or re.match(r'^\s*(?:[-*]|\d+\.)\s',ln):
            if buf: out.append(' '.join(buf)); buf=[]
            continue
        buf.append(s)
    if buf: out.append(' '.join(buf))
    return out

def vocab_terms(secs):
    """Vocabulary list: a short-item comma-separated italic line, or a table.
    Guards against picking up a long prose/source paragraph that merely happens
    to be italic and comma-rich (items must be genuinely word/phrase length)."""
    text = find_sec(secs, *SEC["input"]) + "\n" + find_sec(secs, *SEC["vocab"])
    for ln in text.split('\n'):
        s = ln.strip()
        mm = re.match(r'^\*([^*]+)\*\.?$', s)
        if mm and mm.group(1).count(',') >= 3:
            terms = [t.strip(' .') for t in mm.group(1).split(',') if t.strip(' .')]
            if len(terms) >= 4 and max(len(t) for t in terms) <= 28:
                return terms
    tables, rows = [], []
    for line in text.splitlines() + ['']:
        if line.strip().startswith('|'):
            rows.append(line)
        elif rows:
            tables.append(rows); rows = []
    for rows in tables:
        if len(rows) < 4: continue
        terms = []
        for row in rows[2:]:
            cells = [c.strip() for c in row.strip().strip('|').split('|')]
            if cells and cells[0] and not set(cells[0]) <= set('-: '):
                terms.append(re.sub(r'[*`]', '', cells[0]))
        if len(terms) >= 4 and max(map(len, terms)) <= 28:
            return terms
    return []

def move_lines(secs):
    """Whole teaching-point paragraphs, preserving authored soft wrapping."""
    voc = set(vocab_terms(secs))
    out = []
    for s in paragraphs(find_sec(secs, *SEC["input"])):
        plain = re.sub(r'[*`]','',s)
        if len(plain) < 20: continue
        if ('—' in s or ' - ' in s or ':' in s) and not plain.rstrip('.') in voc:
            out.append(s)
    return out

MATCHED_TITLES: list[str] = []


def answer_keys(md, secs):
    """Preserve structured lesson keys, including nested details and tables."""
    out = []
    def collect(nodes):
        for node in nodes:
            if isinstance(node, str): continue
            if node['answer']:
                MATCHED_TITLES.append(node['title'])
                body = unwrap_callouts(node['children']).strip()
                if body: out.append(body)
            else:
                collect(node['children'])
    for title, body in secs:
        if re.search(r'exam|prüfung|prufung|épreuve|epreuve|évaluation|evaluation', norm(title)):
            continue
        nodes = callout_tree(body)
        if any(key in norm(title) for key in SEC['solutions']):
            dedicated = unwrap_callouts(nodes).strip()
            if dedicated: out.append(dedicated)
        else:
            collect(nodes)
    return out

# ---------- localisation (labels follow the site's language) ----------
LABELS = {
  "en": {"teacher_key":"Teacher answer key","teacher_copy":" — Teacher copy","ui":"english",
         "obj":"Learning objectives","lead":"Lead-in","vocab":"Vocabulary",
         "key":"Key points","prac":"Practise","turn":"Your turn","refl":"Reflect",
         "read":"Reading","write":"Write","term":"Term","note":"Your note",
         "v_i":"Match each item to its meaning or use it in a sentence.",
         "r_i":"Read the text and use it for the activities below."},
  "fr": {"teacher_key":"Corrigé — enseignant","teacher_copy":" — Version enseignant","ui":"french",
         "obj":"Objectifs","lead":"Mise en situation","vocab":"Vocabulaire",
         "key":"Points clés","prac":"S'entraîner","turn":"À toi de jouer","refl":"Réfléchir",
         "read":"Lecture","write":"Produire","term":"Terme","note":"Votre note",
         "v_i":"Associez chaque terme à son sens ou employez-le dans une phrase.",
         "r_i":"Lisez le texte et utilisez-le pour les activités suivantes."},
  "de": {"teacher_key":"Lösungen — Lehrkraft","teacher_copy":" — Lehrkraftfassung","ui":"german",
         "obj":"Lernziele","lead":"Einstieg","vocab":"Wortschatz",
         "key":"Kernpunkte","prac":"Üben","turn":"Anwenden","refl":"Reflexion",
         "read":"Lesen","write":"Schreiben","term":"Wort","note":"Ihre Notiz",
         "v_i":"Ordnen Sie jedem Wort seine Bedeutung zu oder verwenden Sie es im Satz.",
         "r_i":"Lesen Sie den Text und nutzen Sie ihn für die folgenden Aufgaben."},
}
L = LABELS["en"]

# ---------- LaTeX emit ----------
def frame(title, body):
    return f"\\begin{{frame}}[allowframebreaks=0.8,t]{{{preserve_authored_symbols(preserve_greek_characters(esc(title)))}}}\n\\interlinepenalty=0\\widowpenalty=0\\clubpenalty=0\n{body}\n\\end{{frame}}\n"

def itemize(items, small=False):
    if not items: return ""
    sz = "\\small\n" if small else ""
    return sz+"\\begin{itemize}\n" + "\n".join(f"  \\item {inline(x)}" for x in items) + "\n\\end{itemize}"

def task_table(lines, rows_per_chunk=4):
    """Keep header/cell associations; short repeated-header tables can paginate."""
    rows = [[cell.strip() for cell in re.split(r'(?<!\\)\|', line.strip().strip('|'))]
            for line in lines]
    width = len(rows[0])
    if len(rows) < 2 or any(len(row) != width for row in rows):
        raise ValueError('task table has inconsistent columns')
    if not all(re.fullmatch(r':?-+:?', cell.replace(' ', '')) for cell in rows[1]):
        raise ValueError('task table is missing its header separator')
    out = []
    for start in range(2, len(rows), rows_per_chunk):
        cells = [' & '.join(r'\textbf{' + inline(cell) + '}' for cell in rows[0]) + r' \\ \midrule']
        cells += [' & '.join(inline(cell.replace(r'\|', '|')) for cell in row) + r' \\'
                  for row in rows[start:start + rows_per_chunk]]
        out.append(r'\par\medskip\noindent\begin{tabularx}{\linewidth}{@{}' +
                   ('>{\\raggedright\\arraybackslash}X' * width) + '@{}}\n' +
                   '\n'.join(cells) + '\n' + r'\bottomrule\end{tabularx}\par\medskip')
    return '\n'.join(out)


def text_blocks(text, table_rows=4):
    """Render task paragraphs, headings, quotes, tables and labelled lists."""
    # Markdown backslash line breaks are layout, not literal backslash glyphs.
    lines = text.strip().replace('\\\n', '\n\n').removesuffix('\\').splitlines()
    out, index = [], 0
    item = re.compile(r'^\s*([-*]|\d+\.)\s+(.*)$')
    def boundary(line):
        return (not line.strip() or re.match(r'^\s*(?:#{1,6}\s|\||>)', line)
                or item.match(line))
    while index < len(lines):
        line = lines[index].strip(); index += 1
        if not line: continue
        if line.startswith('|'):
            table = [line]
            while index < len(lines) and lines[index].lstrip().startswith('|'):
                table.append(lines[index]); index += 1
            out.append(task_table(table, table_rows))
        elif re.match(r'^#{1,6}\s', line):
            out.append(r'\par\medskip\textbf{' + inline(heading_text(re.sub(r'^#+\s*', '', line))) + r'}\par')
        elif line.startswith('>'):
            quoted = [re.sub(r'^>\s?', '', line)]
            while index < len(lines) and lines[index].lstrip().startswith('>'):
                quoted.append(re.sub(r'^>\s?', '', lines[index].lstrip())); index += 1
            # A quote can contain a form list or table as well as prose.
            # Parse its structure recursively, retaining soft-wrapped paragraphs.
            out.append(text_blocks('\n'.join(quoted), table_rows=table_rows))
        elif item.match(line):
            items = []
            while True:
                match = item.match(line)
                label, value = match.groups()
                while index < len(lines) and not boundary(lines[index]):
                    value += ' ' + lines[index].strip(); index += 1
                # Explicit labels preserve authored numbering, including restarts.
                prefix = r'\item[' + label + '] ' if label[0].isdigit() else r'\item '
                check = re.match(r'^\[([ xX]?)\]\s+(.*)$', value)
                if check:
                    mark, value = check.groups()
                    prefix = r'\item[{' + (label + r'\ ' if label[0].isdigit() else '') + '[' + (mark or ' ') + ']}] '
                items.append(prefix + inline(value))
                if index >= len(lines) or not item.match(lines[index]): break
                line = lines[index]; index += 1
            out.append('\\begin{itemize}\n' + '\n'.join(items) + '\n\\end{itemize}')
        else:
            paragraph = [line]
            while index < len(lines) and not boundary(lines[index]):
                paragraph.append(lines[index].strip()); index += 1
            out.append(inline(' '.join(paragraph)) + r'\par')
    return '\n'.join(out)


def is_reference_section(title):
    return getattr(title, 'anchor', None) == 'sources' or bool(re.fullmatch(
        r'sources?|quellen|further reading(?:\s*/\s*listening)?|references?|bibliograph\w*', norm(title)))


def reference_blocks(text, table_rows=4):
    """Keep source citations and their destinations readable and clickable.

    Protect URLs before ordinary Markdown rendering. Balanced link destinations
    preserve parentheses in article names; long addresses may wrap at each
    character, with no altered destination or extra typesetting dependency.
    """
    links = []
    prefix = 'BOULINGUAREFERENCEURL'
    while prefix in text:
        prefix += 'X'

    def protect(url):
        if not re.match(r'^https?://', url) or re.search(r'[\s\\{}]', url):
            raise ValueError(f'unsupported source URL: {url!r}')
        token = prefix + str(len(links)) + 'END'
        links.append((token, url))
        return token

    pattern = re.compile(r'\[([^\]\n]+)\]\((https?://)')
    parts, cursor = [], 0
    while match := pattern.search(text, cursor):
        end = match.start(2); depth = 1
        while end < len(text):
            if text[end] == '(':
                depth += 1
            elif text[end] == ')':
                depth -= 1
                if depth == 0:
                    break
            end += 1
        if depth:
            raise ValueError('unclosed source link destination')
        parts.extend([text[cursor:match.start()], match.group(1) + ' (' + protect(text[match.start(2):end]) + ')'])
        cursor = end + 1
    parts.append(text[cursor:])
    marked = ''.join(parts)
    marked = re.sub(r'<(https?://[^<>\s]+)>', lambda m: protect(m.group(1)), marked)

    def bare(match):
        url = match.group(0); tail = ''
        while url and (url[-1] in '.,;' or (url[-1] == ')' and url.count(')') > url.count('('))):
            tail = url[-1] + tail; url = url[:-1]
        return protect(url) + tail

    marked = re.sub(r'https?://[^\s<>]+', bare, marked)
    rendered = text_blocks(marked, table_rows=table_rows)
    for token, url in links:
        target = esc(url).replace(r'\textasciitilde{}', r'\string~').replace(r'\textasciicircum{}', r'\string^')
        display = r'\allowbreak{}'.join(esc(char) for char in url)
        rendered = rendered.replace(token, r'\href{' + target + '}{' + display + '}')
    return rendered


def flow_frame(title,body):
    # Leave room for the frame heading and footer around indivisible table
    # chunks. The default 95% split allowed vocabulary rows into the footer.
    return f"\\begin{{frame}}[allowframebreaks=0.8,t]{{{preserve_authored_symbols(preserve_greek_characters(esc(title)))}}}\n\\small\\interlinepenalty=0\\widowpenalty=0\\clubpenalty=0\n{body}\n\\end{{frame}}\n"


def canonical_material_sections(secs):
    """New courses must provide all five explicit steps; preserve their prose."""
    required = ['activate', 'input', 'practise', 'apply', 'reflect']
    anchors = [getattr(title, 'anchor', None) for title, _ in secs]
    for step in required:
        if anchors.count(step) != 1:
            raise ValueError(f'new-course materials require exactly one {{{{#{step}}}}} section')
    positions = [anchors.index(step) for step in required]
    if positions != sorted(positions):
        raise ValueError('new-course learner steps must occur in their declared order')
    selected = []
    for title, text in secs:
        anchor = getattr(title, 'anchor', None)
        if anchor in {'solutions', 'key', 'teacher-notes', 'exam'} or (anchor not in required and ANSWER_TITLE.search(title)):
            continue
        learner = strip_callouts(text)
        if anchor in required and not learner.strip():
            raise ValueError(f'new-course {anchor} section has no learner content')
        if learner.strip():
            selected.append((title, learner))
    return selected


def build_canonical_deck(secs, title, subtitle):
    frames = ["\\begin{frame}[plain]\\titlepage\\end{frame}"]
    for heading, text in canonical_material_sections(secs):
        frames.append(flow_frame(heading, reference_blocks(text, table_rows=2)))
    return finish_document(TEX_DECK.replace("@@TITLE@@", inline(title)).replace("@@SUBTITLE@@", inline(subtitle))
            .replace("@@LANG@@", SITE).replace("@@FRAMES@@", "\n".join(frames)))


def build_canonical_worksheet(secs, md, title, subtitle, badge, teacher):
    sections = [r'\section{' + preserve_greek_characters(esc(heading)) + '}\n' + reference_blocks(text)
                for heading, text in canonical_material_sections(secs)]
    additions = []
    if teacher:
        key_sections = [('Solutions', text) if getattr(heading, 'anchor', None) in {'solutions', 'key'} else (heading, text) for heading, text in secs]
        keys = answer_keys(md, key_sections)
        if keys:
            additions.append(r'\section{' + esc(L['teacher_key']) + '}\n' + '\n'.join(reference_blocks(k) for k in keys))
        for heading, text in secs:
            if getattr(heading, 'anchor', None) == 'teacher-notes':
                additions.append(r'\section{' + preserve_greek_characters(esc(heading)) + '}\n' + reference_blocks(strip_callouts(text)))
        title += L['teacher_copy']
    return finish_document(TEX_SHEET.replace("@@TITLE@@", inline(title)).replace("@@SUBTITLE@@", inline(subtitle))
            .replace("@@BADGE@@", esc(badge)).replace("@@LANG@@", SITE).replace("@@UI@@", L['ui'])
            .replace("@@SECTIONS@@", "\n\n".join(sections).replace(r'\section{', r'\Needspace{6\baselineskip}\section{'))
            .replace("@@ANSWERS@@", ("\\clearpage\n" + "\n\n".join(additions)) if additions else ''))


def build_deck(fm, secs, title, subtitle):
    if SITE not in {'efl', 'fle', 'daf'}:
        return build_canonical_deck(secs, title, subtitle)
    F = []
    F.append("\\begin{frame}[plain]\\titlepage\\end{frame}")
    obj = bullets(find_sec(secs, *SEC["objectives"]))
    if obj: F.append(frame(L["obj"], itemize(obj)))
    lead = find_sec(secs, *SEC["leadin"])
    if lead.strip(): F.append(flow_frame(L["lead"], reference_blocks(lead, table_rows=2)))
    terms = vocab_terms(secs)
    for start in range(0, len(terms), 12):
        group=terms[start:start+12]; half=(len(group)+1)//2
        col1=itemize(group[:half]); col2=itemize(group[half:])
        F.append(frame(L["vocab"],
            f"\\begin{{columns}}[T]\n\\column{{0.5\\linewidth}}\n{col1}\n"
            f"\\column{{0.5\\linewidth}}\n{col2}\n\\end{{columns}}"))
    inp = find_sec(secs, *SEC["input"])
    if inp.strip(): F.append(flow_frame(L["read"], reference_blocks(inp, table_rows=2)))
    practice = find_sec(secs, *SEC["practise"])
    if practice.strip(): F.append(flow_frame(L["prac"], reference_blocks(practice, table_rows=2)))
    production = find_sec(secs, *SEC["produce"])
    if production.strip(): F.append(flow_frame(L["turn"], reference_blocks(production, table_rows=2)))
    refl = bullets(find_sec(secs, *SEC["reflect"]))
    if refl: F.append(frame(L["refl"], itemize(refl, small=True)))
    for heading, text in secs:
        if is_reference_section(heading) and text.strip():
            F.append(flow_frame(heading, reference_blocks(strip_callouts(text), table_rows=2)))
    return finish_document(TEX_DECK.replace("@@TITLE@@", inline(title)).replace("@@SUBTITLE@@", inline(subtitle))
            .replace("@@LANG@@", SITE).replace("@@FRAMES@@", "\n".join(F)))

def build_worksheet(fm, secs, md, title, subtitle, badge, teacher=False):
    if SITE not in {'efl', 'fle', 'daf'}:
        return build_canonical_worksheet(secs, md, title, subtitle, badge, teacher)
    S = []
    terms = vocab_terms(secs)
    if terms:
        rows = " \\\\[0.5em]\n".join(f"{inline(t)} & " for t in terms)
        S.append(f"\\section{{{esc(L['vocab'])}}}\n{esc(L['v_i'])}\n\n"
            "\\noindent\\begin{tabularx}{\\linewidth}{@{}p{5cm}X@{}}\n\\toprule\n"
            f"\\textbf{{{esc(L['term'])}}} & \\textbf{{{esc(L['note'])}}} \\\\\n\\midrule\n"
            f"{rows} \\\\\n\\bottomrule\n\\end{{tabularx}}")
    inp = find_sec(secs, *SEC["input"])
    # Inputs include multiple texts and instructions joining them. Preserve the
    # whole section, with its labels, instead of selecting one quote or paragraph.
    if inp.strip():
        S.append(f"\\section{{{esc(L['read'])}}}\n{esc(L['r_i'])}\n\n"
                 + reference_blocks(inp) + "\n\\blglines[2]")
    practice = find_sec(secs, *SEC["practise"])
    if practice.strip():
        S.append(f"\\section{{{esc(L['prac'])}}}\n"+reference_blocks(practice)+"\n\\blglines[3]")
    production = find_sec(secs, *SEC["produce"])
    if production.strip():
        S.append(f"\\section{{{esc(L['turn'])}}}\n"+reference_blocks(production)+"\n\\blglines[6]")
    for heading, text in secs:
        if is_reference_section(heading) and text.strip():
            S.append(r'\section{' + preserve_greek_characters(esc(heading)) + '}\n' + reference_blocks(strip_callouts(text)))
    ans = answer_keys(md, secs) if teacher else []
    ansbox = ""
    if ans:
        body = '\n'.join(reference_blocks(a) for a in ans)
        # A plain section can break across pages; a long answer table must not
        # disappear below an unbreakable decorative box.
        label = L['teacher_key']
        ansbox = "\\clearpage\n\\section{" + esc(label) + "}\n" + body
    if teacher:
        title += L['teacher_copy']
    return finish_document(TEX_SHEET.replace("@@TITLE@@", inline(title)).replace("@@SUBTITLE@@", inline(subtitle))
            .replace("@@BADGE@@", esc(badge)).replace("@@LANG@@", SITE)
            .replace("@@UI@@", L['ui'])
            .replace("@@SECTIONS@@", "\n\n".join(S).replace(r'\section{', r'\Needspace{6\baselineskip}\section{'))
            .replace("@@ANSWERS@@", ansbox))

TEX_SYMBOLS = r"""
\usetikzlibrary{shapes.geometric}
\newcommand{\blgdifficultystar}{\leavevmode%
  \special{pdf:literal direct /Span << /ActualText <FEFF2B51> >> BDC}%
  \makebox[0pt][l]{\special{pdf:literal direct 3 Tr}.\special{pdf:literal direct 0 Tr}}%
  \tikz[baseline=-0.1ex]\node[star,star points=5,star point ratio=2.25,
    fill=.,draw=none,inner sep=0pt,minimum size=0.65em]{};%
  \special{pdf:literal direct EMC}}
"""
TEX_DECK = r"""\documentclass[aspectratio=169,11pt]{beamer}
\usepackage{tabularx,booktabs}
\usetheme{boulingua}
""" + TEX_SYMBOLS + r"""
\blgsetlang{@@LANG@@}
\title{@@TITLE@@}
\subtitle{@@SUBTITLE@@}
\begin{document}
@@FRAMES@@
\end{document}
"""
UNIT_WORKSHEET_HEADER = '\n\\renewcommand{\\worksheetheader}[4]{%\n  \\gdef\\blgtitle{#1}%\n  \\hypersetup{pdftitle={#1}}%\n  \\thispagestyle{empty}%\n  \\noindent\\begin{minipage}[t]{\\dimexpr\\linewidth-16mm\\relax}\n    \\vspace{0pt}\\raggedright\\blgsemibold\\LARGE\\color{blgfg}#1\\par\n  \\end{minipage}\\hfill\\begin{minipage}[t]{12mm}\n    \\vspace{0pt}\\raggedleft\\blglangmark[11mm]\n  \\end{minipage}\\par\n  \\vspace{0.35em}%\n  {\\noindent\\color{blgmuted}\\normalsize #2\\hfill{\\blgsemibold\\color{blgfg}#3}}\\par\n  \\vspace{0.35em}{\\noindent\\color{blgaccent}\\rule{\\linewidth}{1.4pt}}\\par\n  \\vspace{1.1em}}\n'
TEX_SHEET = r"""\documentclass[11pt]{article}
\usepackage{boulingua-sheet}
\usepackage{needspace}
""" + TEX_SYMBOLS + UNIT_WORKSHEET_HEADER + r"""
\blgsetlang{@@LANG@@}
\blgsetui{@@UI@@}
\emergencystretch=5em
\begin{document}
\worksheetheader{@@TITLE@@}{@@SUBTITLE@@}{@@BADGE@@}{blgcefrB}
\begin{sheetbody}
@@SECTIONS@@

@@ANSWERS@@
\end{sheetbody}
\end{document}
"""

def xelatex(texfile, passes=2):
    output = MAT / (texfile.stem + '.pdf')
    output.unlink(missing_ok=True)  # generated intermediate, never a published PDF
    result = None
    for _ in range(passes):
        result = subprocess.run(['xelatex', '-no-shell-escape', '-interaction=nonstopmode', '-halt-on-error', texfile.name],
                                cwd=MAT, capture_output=True, text=True)
        log = texfile.with_suffix('.log')
        messages = result.stdout + result.stderr + (log.read_text(errors='replace') if log.exists() else '')
        if result.returncode or 'Missing character:' in messages or re.search(r'(?m)^Overfull \\[hv]box', messages):
            diagnostic = '\n'.join(line for line in messages.splitlines()
                                   if line.startswith(('!', 'Missing character:', 'Overfull ')))
            result.stderr += '\n' + diagnostic
            return False, result
    return output.is_file() and output.stat().st_size > 0, result

def thumb(pdf, png):
    # Delegates. This used to be a second renderer at a third width — 900 px
    # here, 1280 in render_thumbs.py — so the corpus carried thumbnails at
    # three sizes depending on which script happened to produce them. One
    # renderer, one width, one place to change it.
    from render_thumbs import render_pdf
    render_pdf(Path(pdf), Path(png))

def upsert_fm(md_path, slug):
    txt = md_path.read_text()
    m = re.match(r'^---\n(.*?)\n---\n(.*)$', txt, re.S)
    if not m: return
    fm, body = m.group(1), m.group(2)
    def block(key, file_url, thumb_url):
        return f'{key}:\n  file: "{file_url}"\n  thumbnail: "{thumb_url}"'
    pres = block("presentation", f"{URL}/materials/presentations/{slug}.pdf",
                 f"{URL}/materials/presentations/{slug}.png")
    work = block("worksheet", f"{URL}/materials/worksheets/{slug}.pdf",
                 f"{URL}/materials/worksheets/{slug}.png")
    teacher = block("worksheet_teacher", f"{URL}/materials/worksheets/{slug}-teacher.pdf",
                    f"{URL}/materials/worksheets/{slug}-teacher.png")
    for key, rep in (("presentation", pres), ("worksheet", work), ("worksheet_teacher", teacher)):
        pat = re.compile(rf'(?m)^{key}:\n(?:[ \t]+.*\n?)*')
        fm2 = pat.sub(rep+"\n", fm) if re.search(pat, fm) else fm.rstrip()+"\n"+rep
        fm = fm2
    md_path.write_text(f"---\n{fm.rstrip()}\n---\n{body}")

def unit_slug(md_path, md):
    slug = material_slug(md_path)
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', slug):
        raise ValueError(f'{md_path}: material_slug must be a safe filename stem: {slug!r}')
    return slug

def unit_badge(fm, md_path):
    niv = fm.get("niveau") or fm.get("cefr") or fm.get("niveau_cefr")
    if niv: return f"Niveau {niv}"
    m = re.search(r'kurs_([abc][12])', str(md_path), re.I)   # DaF: kurs_a1 -> A1
    return m.group(1).upper() if m else ""

def process(md_path, keep_tex=False):
    verify_producer_identity()
    md_path = Path(md_path).resolve()
    if not md_path.is_relative_to(REPO):
        raise ValueError('material source must belong to the configured course')
    if STAGED:
        validate_stage_root(OUTPUT_ROOT, REPO)
    for directory in (MAT, PRES, WORK):
        validate_artifact_path(directory, OUTPUT_ROOT)
    md = md_path.read_text()
    fm, secs = parse(md)
    name = md_path.parent.name if md_path.name == 'index.md' else md_path.stem
    title, subtitle = fm.get('title', name), fm.get('subtitle', '')
    badge, slug = unit_badge(fm, md_path), unit_slug(md_path, md)
    reserve_material_targets(slug, md_path, TARGET_OWNERS)
    for kind in ('deck', 'sheet', 'teacher'):
        for suffix in ('.tex', '.pdf', '.png', '.aux', '.log', '.nav', '.snm', '.toc', '.out', '.fls', '.xdv'):
            validate_artifact_path(MAT / f'{slug}-{kind}{suffix}', OUTPUT_ROOT)
    for directory, stem in [(PRES, slug), (WORK, slug), (WORK, slug + '-teacher')]:
        for suffix in ('.pdf', '.png'):
            validate_artifact_path(directory / (stem + suffix), OUTPUT_ROOT)
    result = {'unit': name, 'deck': False, 'sheet': False, 'teacher': False}
    documents = [('deck', build_deck(fm, secs, title, subtitle), PRES, slug),
                 ('sheet', build_worksheet(fm, secs, md, title, subtitle, badge), WORK, slug),
                 ('teacher', build_worksheet(fm, secs, md, title, subtitle, badge, teacher=True), WORK, slug+'-teacher')]
    for kind, text, target, stem in documents:
        tex = MAT / f'{slug}-{kind}.tex'
        tex.write_text(text)
        good, run = xelatex(tex)
        result[kind] = good
        if not good:
            result['err_' + kind] = (run.stdout + run.stderr)[-1200:]
    # Publish the complete set only after every document and thumbnail succeeds.
    complete = all(result[kind] for kind, _, _, _ in documents)
    if complete:
        verify_producer_identity()
        if md_path.read_text() != md:
            raise RuntimeError(f'{md_path}: source changed during generation; retry the unit')
        with tempfile.TemporaryDirectory(prefix='materials-', dir=MAT) as td:
            stage = Path(td)
            prepared = []
            for kind, text, target, stem in documents:
                pdf, png = stage / f'{kind}.pdf', stage / f'{kind}.png'
                shutil.copy2(MAT / f'{slug}-{kind}.pdf', pdf)
                thumb(pdf, png)
                target.mkdir(parents=True, exist_ok=True)
                prepared.extend([(pdf, target / f'{stem}.pdf'), (png, target / f'{stem}.png')])
            for source, destination in prepared:
                source.replace(destination)
        if not STAGED: upsert_fm(md_path, slug)
        result['source_sha256'] = hashlib.sha256(md.encode()).hexdigest()
        if not STAGED: result['published_source_sha256'] = hashlib.sha256(md_path.read_bytes()).hexdigest()
        result['generator_sha256'] = PRODUCER_SHA256
        result['files'] = {str(target / f'{stem}.pdf'): hashlib.sha256((target / f'{stem}.pdf').read_bytes()).hexdigest()
                           for _, _, target, stem in documents}
    if not keep_tex and complete:
        for kind, _, _, _ in documents:
            for suffix in ['.aux', '.log', '.nav', '.snm', '.toc', '.out', '.tex', '.pdf']:
                (MAT / f'{slug}-{kind}{suffix}').unlink(missing_ok=True)
    return result

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('repo', nargs='?', type=Path, default=Path.cwd())
    ap.add_argument("--only", default=""); ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--keep-tex", action="store_true")
    ap.add_argument('--output-root', type=Path, help='stage materials outside the course without changing its front matter')
    a = ap.parse_args()
    if not shutil.which('xelatex'):
        print('::error::xelatex is required; install the documented TeX toolchain', file=sys.stderr)
        return 2
    # EFL units are leaf bundles (units/<slug>/index.md); FLE/DaF are single
    # files (units/<slug>.md). Take any markdown under a units/ folder that
    # carries a presentation: block (i.e. a real material-bearing teaching unit).
    units = sorted(p for p in a.repo.resolve().glob("content/**/*.md")
                   if "/units/" in p.as_posix() and p.name != "_index.md" and not is_exam_page(p))
    material_units = [u for u in units if 'presentation:' in u.read_text()]
    units = [u for u in material_units if a.only in str(u)]
    if a.limit < 0:
        ap.error('--limit must be nonnegative')
    if a.limit: units = units[:a.limit]
    if not units:
        print('::error::no material-bearing units match this request', file=sys.stderr)
        return 1
    try:
        preflight_material_targets(material_units)
        configure(a.repo, a.output_root)
    except (OSError, ValueError, SiteError) as exc:
        print(f'::error::{exc}', file=sys.stderr)
        return 2
    if not MAT.is_dir():
        print('::error::_materials is missing; run kit sync REPO first', file=sys.stderr)
        return 2
    okc = deckc = sheetc = teacherc = 0
    results = []
    for u in units:
        try:
            r = process(u, a.keep_tex)
        except (OSError, ValueError, RuntimeError) as exc:
            r = {'unit': str(u.relative_to(REPO)), 'deck': False, 'sheet': False, 'teacher': False,
                 'err_deck': str(exc), 'err_sheet': str(exc), 'err_teacher': str(exc)}
        r['source'] = str(u.relative_to(REPO)); results.append(r)
        okc += 1
        deckc += r["deck"]; sheetc += r["sheet"]; teacherc += r['teacher']
        flag = "OK" if r["deck"] and r["sheet"] and r['teacher'] else "PARTIAL"
        print(f"[{flag}] {r['unit']}  deck={r['deck']} sheet={r['sheet']} teacher={r['teacher']}")
        if not r["deck"] and r.get("err_deck"): print("   deck err:", r["err_deck"].replace('\n',' ')[-200:])
        if not r["sheet"] and r.get("err_sheet"): print("   sheet err:", r["err_sheet"].replace('\n',' ')[-200:])
        if not r['teacher'] and r.get('err_teacher'): print('   teacher err:', r['err_teacher'].replace('\n',' ')[-200:])
    if a.output_root:
        (a.output_root / 'materials-receipt.json').write_text(json.dumps(results, ensure_ascii=False, indent=2)+'\n')
    print(f"\n{okc} units | {deckc} decks | {sheetc} learner worksheets | {teacherc} teacher worksheets")
    return int(deckc != okc or sheetc != okc or teacherc != okc)

if __name__ == "__main__":
    raise SystemExit(main())
