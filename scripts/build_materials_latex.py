#!/usr/bin/env python3
"""Generate branded per-unit materials from each unit's own content.

Multi-site (efl/fle/daf): for every teaching unit it derives a slide deck
(slidegen/Beamer) and a worksheet (sheetgen) — real content pulled from the
unit markdown, no re-authoring — compiles them with XeLaTeX in the boulingua
design language (the site's signature accent + pentagon mark + foot watermark),
renders a thumbnail, writes the PDFs under static/materials/, and rewrites the
unit's presentation:/worksheet: front matter to the open-format PDFs.

The declared site code selects the LaTeX accent
via \\blgsetlang and the /<site> URL prefix. Section names, answer-key formats
and the flat slug are detected across English, French and German units.

Usage:
  build_materials_latex.py [REPO] [--only SLUG_SUBSTR] [--limit N] [--keep-tex]
Requires xelatex and the vendored templates in
_materials/.
"""
import sys, os, re, subprocess, argparse, shutil, tempfile
import yaml
from blg_paths import material_slug, site_code, SiteError
from pathlib import Path

REPO = Path.cwd()
SITE = ''
MAT = REPO / '_materials'
PRES = REPO / 'static/materials/presentations'
WORK = REPO / 'static/materials/worksheets'
URL = ''


def configure(repo):
    global REPO, SITE, MAT, PRES, WORK, URL, L
    REPO = Path(repo).resolve()
    SITE = site_code(REPO)
    config = yaml.safe_load((REPO / 'boulingua.yml').read_text()) or {}
    if config.get('code') != SITE:
        raise ValueError('boulingua.yml and Hugo must declare the same site code')
    MAT = REPO / '_materials'
    PRES = REPO / 'static/materials/presentations'
    WORK = REPO / 'static/materials/worksheets'
    URL = '/' + SITE
    if SITE not in {'efl', 'fle', 'daf'}:
        raise ValueError(f'materials labels are not reviewed for {SITE}')
    L = LABELS[{'efl': 'en', 'fle': 'fr', 'daf': 'de'}[SITE]]


# ---------- markdown → LaTeX ----------
SPECIAL = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$',
           '#': r'\#', '_': r'\_', '{': r'\{', '}': r'\}',
           '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
def esc(s):
    return ''.join(SPECIAL.get(c, c) for c in s)

def inline(s):
    """Convert a line of markdown to LaTeX (bold/italic/code, drop links/md)."""
    s = s.strip()
    s = re.sub(r'\{\{<[^>]*>\}\}', '', s)               # shortcodes
    s = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', s)          # images
    s = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', s)      # links -> text
    # sentinel-protect emphasis, then escape, then re-insert commands
    B,Bc,I,Ic,C,Cc = '\x01','\x02','\x03','\x04','\x05','\x06'
    s = re.sub(r'`([^`]+)`', C+r'\1'+Cc, s)                      # code first
    s = re.sub(r'\*\*\*(.+?)\*\*\*', B+I+r'\1'+Ic+Bc, s)        # bold-italic
    s = re.sub(r'\*\*(.+?)\*\*', B+r'\1'+Bc, s)                 # bold
    s = re.sub(r'(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)', I+r'\1'+Ic, s)   # italic
    s = re.sub(r'(?<![A-Za-z0-9])_([^_]+)_(?![A-Za-z0-9])', I+r'\1'+Ic, s)
    s = s.replace('*', '')                                       # strip stray markers
    s = esc(s)
    s = (s.replace(B,r'\textbf{').replace(Bc,'}')
           .replace(I,r'\textit{').replace(Ic,'}')
           .replace(C,r'\texttt{').replace(Cc,'}'))
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
    return s

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
        secs.append((parts[i].strip(), parts[i+1].strip()))
    return fm, secs

def norm(t):
    return re.sub(r'^\d+\.?\s*', '', t).strip().lower()

def strip_callouts(t):
    """Hide answer keys but retain instructional hints and differentiation."""
    def content(match):
        attrs, body = match.group(2), match.group(3)
        title = re.search(r'title=["\']([^"\']+)', attrs)
        title = title.group(1) if title else ''
        if re.search(r'l\wsung|answer\s*key|solution|corrig|barème|notenschlüssel', title, re.I):
            return ''
        return '\n\n' + (f'**{title}**\n\n' if title else '') + body.strip() + '\n\n'
    return re.sub(r'\{\{<\s*(callout|details)([^>]*)>\}\}(.*?)\{\{<\s*/\1\s*>\}\}',
                  content, t, flags=re.S)

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
    """Individual short teaching-point lines from Input (e.g. 'Voice — ...'),
    excluding headings, the long source paragraph and the vocab list."""
    voc = set(vocab_terms(secs))
    out = []
    for ln in find_sec(secs, *SEC["input"]).split('\n'):
        s = ln.strip()
        if not s or s.startswith(('#','>','|','{{<')): continue
        if re.match(r'^\s*(?:[-*]|\d+\.)\s', ln): continue
        plain = re.sub(r'[*`]','',s)
        if not (20 <= len(plain) <= 200): continue          # not the long source
        if ('—' in s or ' - ' in s or ':' in s) and not plain.rstrip('.') in voc:
            out.append(s)
    return out[:4]

MATCHED_TITLES: list[str] = []


def answer_keys(md, secs):
    """Answer keys, wherever the site keeps them: callout/details blocks titled
    Answer key / Lösungen / Solutions / Corrigé (EFL, DaF), or a dedicated
    ## Solutions / ## Lösungen / ## Corrigé section (FLE)."""
    out = []
    # The title is matched as a SUBSTRING, not as the whole string. The exact
    # match this replaces recognised "Lösungen" and nothing else, so every
    # variant an author reached for — "Lösungen Prüfung", "Musterlösung",
    # "Lösungen (für Lehrkräfte)", "Lösungen & Punkte-Rubrik" — was silently
    # dropped from the worksheet. Measured on daf: 61 of 87 answer-key blocks
    # matched, and FOUR of the sixty shipped worksheet PDFs contain no answer
    # key at all as a result. Nothing failed; the sheet simply came out without
    # its solutions, and it has been shipping that way.
    #
    # Widening it risks a false positive on a block that merely discusses
    # solutions. That trade is not close: an answer key wrongly included is
    # visible on the page the moment anyone looks at the sheet, and an answer
    # key wrongly dropped is invisible until a teacher needs it in a lesson.
    pat = (r'\{\{<\s*(?:callout|details)[^>]*title="([^"]*)"[^>]*>\}\}'
           r'(.*?)\{\{<\s*/(?:callout|details)\s*>\}\}')
    KEYWORD = re.compile(r'(l\wsung|answer\s*key|solution|corrig)', re.I)
    teaching = "\n\n".join(body for title, body in secs
                           if not re.search(r'exam|prüfung|prufung|épreuve|epreuve', norm(title)))
    for m in re.finditer(pat, teaching, re.S):
        if not KEYWORD.search(m.group(1)):
            continue
        MATCHED_TITLES.append(m.group(1))
        for ln in m.group(2).strip().split('\n'):
            s = ln.strip()
            if s and not s.startswith('|'): out.append(s)
    for ln in find_sec(secs, *SEC["solutions"]).split('\n'):
        s = ln.strip()
        if s and not s.startswith('|'): out.append(s)
    return out

# ---------- localisation (labels follow the site's language) ----------
LABELS = {
  "en": {"obj":"Learning objectives","lead":"Lead-in","vocab":"Vocabulary",
         "key":"Key points","prac":"Practise","turn":"Your turn","refl":"Reflect",
         "read":"Reading","write":"Write","term":"Term","note":"Your note",
         "v_i":"Match each item to its meaning or use it in a sentence.",
         "r_i":"Read the text and use it for the activities below."},
  "fr": {"obj":"Objectifs","lead":"Mise en situation","vocab":"Vocabulaire",
         "key":"Points clés","prac":"S'entraîner","turn":"À toi de jouer","refl":"Réfléchir",
         "read":"Lecture","write":"Produire","term":"Terme","note":"Votre note",
         "v_i":"Associez chaque terme à son sens ou employez-le dans une phrase.",
         "r_i":"Lisez le texte et utilisez-le pour les activités suivantes."},
  "de": {"obj":"Lernziele","lead":"Einstieg","vocab":"Wortschatz",
         "key":"Kernpunkte","prac":"Üben","turn":"Anwenden","refl":"Reflexion",
         "read":"Lesen","write":"Schreiben","term":"Wort","note":"Ihre Notiz",
         "v_i":"Ordnen Sie jedem Wort seine Bedeutung zu oder verwenden Sie es im Satz.",
         "r_i":"Lesen Sie den Text und nutzen Sie ihn für die folgenden Aufgaben."},
}
L = LABELS["en"]

# ---------- LaTeX emit ----------
def frame(title, body):
    return f"\\begin{{frame}}{{{esc(title)}}}\n{body}\n\\end{{frame}}\n"

def itemize(items, small=False):
    if not items: return ""
    sz = "\\small\n" if small else ""
    return sz+"\\begin{itemize}\n" + "\n".join(f"  \\item {inline(x)}" for x in items) + "\n\\end{itemize}"

def task_table(lines):
    """Keep header/cell associations; short repeated-header tables can paginate."""
    rows = [[cell.strip() for cell in re.split(r'(?<!\\)\|', line.strip().strip('|'))]
            for line in lines]
    width = len(rows[0])
    if len(rows) < 2 or any(len(row) != width for row in rows):
        raise ValueError('task table has inconsistent columns')
    if not all(re.fullmatch(r':?-+:?', cell.replace(' ', '')) for cell in rows[1]):
        raise ValueError('task table is missing its header separator')
    out = []
    for start in range(2, len(rows), 4):
        cells = [' & '.join(r'\textbf{' + inline(cell) + '}' for cell in rows[0]) + r' \\ \midrule']
        cells += [' & '.join(inline(cell.replace(r'\|', '|')) for cell in row) + r' \\'
                  for row in rows[start:start + 4]]
        out.append(r'\par\medskip\noindent\begin{tabularx}{\linewidth}{@{}' +
                   ('>{\\raggedright\\arraybackslash}X' * width) + '@{}}\n' +
                   '\n'.join(cells) + '\n' + r'\bottomrule\end{tabularx}\par\medskip')
    return '\n'.join(out)


def text_blocks(text):
    """Render task paragraphs, headings, quotes, tables and labelled lists."""
    lines = text.strip().splitlines()
    out, index = [], 0
    item = re.compile(r'^\s*([-*]|\d+\.)\s+(?:\[[ xX]?\]\s*)?(.*)$')
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
            out.append(task_table(table))
        elif re.match(r'^#{1,6}\s', line):
            out.append(r'\par\medskip\textbf{' + inline(re.sub(r'^#+\s*', '', line)) + r'}\par')
        elif line.startswith('>'):
            out.append(inline(re.sub(r'^>\s?', '', line)) + r'\par')
        elif item.match(line):
            items = []
            while True:
                match = item.match(line)
                label, value = match.groups()
                while index < len(lines) and not boundary(lines[index]):
                    value += ' ' + lines[index].strip(); index += 1
                # Explicit labels preserve authored numbering, including restarts.
                prefix = r'\item[' + label + '] ' if label[0].isdigit() else r'\item '
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


def flow_frame(title,body):
    return f"\\begin{{frame}}[allowframebreaks]{{{esc(title)}}}\n\\small\n{body}\n\\end{{frame}}\n"


def build_deck(fm, secs, title, subtitle):
    F = []
    F.append("\\begin{frame}[plain]\\titlepage\\end{frame}")
    obj = bullets(find_sec(secs, *SEC["objectives"]))
    if obj: F.append(frame(L["obj"], itemize(obj)))
    lead = paragraphs(find_sec(secs, *SEC["leadin"]))
    if lead:
        F.append(frame(L["lead"], f"\\large {inline(lead[0])}"))
    terms = vocab_terms(secs)
    for start in range(0, len(terms), 12):
        group=terms[start:start+12]; half=(len(group)+1)//2
        col1=itemize(group[:half]); col2=itemize(group[half:])
        F.append(frame(L["vocab"],
            f"\\begin{{columns}}[T]\n\\column{{0.5\\linewidth}}\n{col1}\n"
            f"\\column{{0.5\\linewidth}}\n{col2}\n\\end{{columns}}"))
    moves = move_lines(secs)
    if moves:
        F.append(frame(L["key"], itemize(moves, small=True)))
    practice = find_sec(secs, *SEC["practise"])
    if practice.strip(): F.append(flow_frame(L["prac"], text_blocks(practice)))
    production = find_sec(secs, *SEC["produce"])
    if production.strip(): F.append(flow_frame(L["turn"], text_blocks(production)))
    refl = bullets(find_sec(secs, *SEC["reflect"]))
    if refl: F.append(frame(L["refl"], itemize(refl, small=True)))
    return (TEX_DECK.replace("@@TITLE@@", inline(title)).replace("@@SUBTITLE@@", inline(subtitle))
            .replace("@@LANG@@", SITE).replace("@@FRAMES@@", "\n".join(F)))

def build_worksheet(fm, secs, md, title, subtitle, badge):
    S = []
    terms = vocab_terms(secs)
    if terms:
        rows = " \\\\[0.5em]\n".join(f"{inline(t)} & " for t in terms)
        S.append(f"\\section{{{esc(L['vocab'])}}}\n{esc(L['v_i'])}\n\n"
            "\\noindent\\begin{tabularx}{\\linewidth}{@{}p{5cm}X@{}}\n\\toprule\n"
            f"\\textbf{{{esc(L['term'])}}} & \\textbf{{{esc(L['note'])}}} \\\\\n\\midrule\n"
            f"{rows} \\\\\n\\bottomrule\n\\end{{tabularx}}")
    src = ""
    inp = find_sec(secs, *SEC["input"])
    # A dialogue/source is a blockquote. Vocabulary and explanatory prose are
    # not reading stimuli, even when they happen to exceed 160 characters.
    quoted = re.findall(r'(?m)(?:^>[^\n]*(?:\n|$))+', inp)
    if quoted:
        src = '\n'.join(re.sub(r'^>\s?', '', line) for line in quoted[0].strip().splitlines())
    if src:
        reading = r'\par '.join(inline(line) for line in src.splitlines())
        S.append(f"\\section{{{esc(L['read'])}}}\n{esc(L['r_i'])}\n\n"
                 f"\\begingroup\\itshape {reading}\\endgroup\n\\blglines[2]")
    practice = find_sec(secs, *SEC["practise"])
    if practice.strip():
        S.append(f"\\section{{{esc(L['prac'])}}}\n"+text_blocks(practice)+"\n\\blglines[3]")
    production = find_sec(secs, *SEC["produce"])
    if production.strip():
        S.append(f"\\section{{{esc(L['turn'])}}}\n"+text_blocks(production)+"\n\\blglines[6]")
    ans = answer_keys(md, secs)
    ansbox = ""
    if ans:
        body = " \\\\\n".join(inline(a) for a in ans)
        ansbox = "\\begin{blganswers}\n"+body+"\n\\end{blganswers}"
    return (TEX_SHEET.replace("@@TITLE@@", inline(title)).replace("@@SUBTITLE@@", inline(subtitle))
            .replace("@@BADGE@@", esc(badge)).replace("@@LANG@@", SITE)
            .replace("@@UI@@", {'efl': 'english', 'fle': 'french', 'daf': 'german'}[SITE])
            .replace("@@SECTIONS@@", "\n\n".join(S).replace(r'\section{', r'\Needspace{6\baselineskip}\section{'))
            .replace("@@ANSWERS@@", ansbox))

TEX_SYMBOLS = r"""
\usetikzlibrary{shapes.geometric}
\newcommand{\blgdifficultystar}{%
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
TEX_SHEET = r"""\documentclass[11pt]{article}
\usepackage{boulingua-sheet}
\usepackage{needspace}
""" + TEX_SYMBOLS + r"""
\blgsetlang{@@LANG@@}
\blgsetui{@@UI@@}
\emergencystretch=2em
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
        if result.returncode or 'Missing character:' in messages:
            diagnostic = '\n'.join(line for line in messages.splitlines()
                                   if line.startswith(('!', 'Missing character:')))
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
    for key, rep in (("presentation", pres), ("worksheet", work)):
        pat = re.compile(rf'(?m)^{key}:\n(?:[ \t]+.*\n?)*')
        fm2 = pat.sub(rep+"\n", fm) if re.search(pat, fm) else fm.rstrip()+"\n"+rep
        fm = fm2
    md_path.write_text(f"---\n{fm.rstrip()}\n---\n{body}")

def unit_slug(md_path, md):
    return material_slug(md_path)

def unit_badge(fm, md_path):
    niv = fm.get("niveau") or fm.get("cefr") or fm.get("niveau_cefr")
    if niv: return f"Niveau {niv}"
    m = re.search(r'kurs_([abc][12])', str(md_path), re.I)   # DaF: kurs_a1 -> A1
    return m.group(1).upper() if m else ""

def process(md_path, keep_tex=False):
    md = md_path.read_text()
    fm, secs = parse(md)
    name = md_path.parent.name if md_path.name == 'index.md' else md_path.stem
    title, subtitle = fm.get('title', name), fm.get('subtitle', '')
    badge, slug = unit_badge(fm, md_path), unit_slug(md_path, md)
    result = {'unit': name, 'deck': False, 'sheet': False}
    documents = [('deck', build_deck(fm, secs, title, subtitle), PRES),
                 ('sheet', build_worksheet(fm, secs, md, title, subtitle, badge), WORK)]
    for kind, text, target in documents:
        tex = MAT / f'{slug}-{kind}.tex'
        tex.write_text(text)
        good, run = xelatex(tex)
        result[kind] = good
        if not good:
            result['err_' + kind] = (run.stdout + run.stderr)[-1200:]
    # Publish neither document until both compile and both thumbnails render.
    if result['deck'] and result['sheet']:
        with tempfile.TemporaryDirectory(prefix='materials-', dir=MAT) as td:
            stage = Path(td)
            prepared = []
            for kind, text, target in documents:
                pdf, png = stage / f'{kind}.pdf', stage / f'{kind}.png'
                shutil.copy2(MAT / f'{slug}-{kind}.pdf', pdf)
                thumb(pdf, png)
                target.mkdir(parents=True, exist_ok=True)
                prepared.extend([(pdf, target / f'{slug}.pdf'), (png, target / f'{slug}.png')])
            for source, destination in prepared:
                source.replace(destination)
        upsert_fm(md_path, slug)
    if not keep_tex and result['deck'] and result['sheet']:
        for kind, _, _ in documents:
            for suffix in ['.aux', '.log', '.nav', '.snm', '.toc', '.out', '.tex', '.pdf']:
                (MAT / f'{slug}-{kind}{suffix}').unlink(missing_ok=True)
    return result

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('repo', nargs='?', type=Path, default=Path.cwd())
    ap.add_argument("--only", default=""); ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--keep-tex", action="store_true")
    a = ap.parse_args()
    try:
        configure(a.repo)
    except (OSError, ValueError, SiteError) as exc:
        print(f'::error::{exc}', file=sys.stderr)
        return 2
    if not shutil.which('xelatex'):
        print('::error::xelatex is required; install the documented TeX toolchain', file=sys.stderr)
        return 2
    if not MAT.is_dir():
        print('::error::_materials is missing; run kit sync REPO first', file=sys.stderr)
        return 2
    # EFL units are leaf bundles (units/<slug>/index.md); FLE/DaF are single
    # files (units/<slug>.md). Take any markdown under a units/ folder that
    # carries a presentation: block (i.e. a real material-bearing teaching unit).
    units = sorted(p for p in REPO.glob("content/**/*.md")
                   if "/units/" in p.as_posix() and p.name != "_index.md")
    units = [u for u in units if a.only in str(u)]
    units = [u for u in units if 'presentation:' in u.read_text()]
    if a.limit < 0:
        ap.error('--limit must be nonnegative')
    if a.limit: units = units[:a.limit]
    if not units:
        print('::error::no material-bearing units match this request', file=sys.stderr)
        return 1
    okc = deckc = sheetc = 0
    for u in units:
        try:
            r = process(u, a.keep_tex)
        except (OSError, ValueError, RuntimeError) as exc:
            r = {'unit': str(u.relative_to(REPO)), 'deck': False, 'sheet': False,
                 'err_deck': str(exc), 'err_sheet': str(exc)}
        okc += 1
        deckc += r["deck"]; sheetc += r["sheet"]
        flag = "OK" if r["deck"] and r["sheet"] else "PARTIAL"
        print(f"[{flag}] {r['unit']}  deck={r['deck']} sheet={r['sheet']}")
        if not r["deck"] and r.get("err_deck"): print("   deck err:", r["err_deck"].replace('\n',' ')[-200:])
        if not r["sheet"] and r.get("err_sheet"): print("   sheet err:", r["err_sheet"].replace('\n',' ')[-200:])
    print(f"\n{okc} units | {deckc} decks | {sheetc} worksheets")
    return int(deckc != okc or sheetc != okc)

if __name__ == "__main__":
    raise SystemExit(main())
