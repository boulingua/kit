#!/usr/bin/env python3
"""Generate branded per-unit materials from each unit's own content.

Multi-site (efl/fle/daf): for every teaching unit it derives a slide deck
(slidegen/Beamer) and a worksheet (sheetgen) — real content pulled from the
unit markdown, no re-authoring — compiles them with XeLaTeX in the boulingua
design language (the site's signature accent + pentagon mark + foot watermark),
renders a thumbnail, writes the PDFs under static/materials/, and rewrites the
unit's presentation:/worksheet: front matter to the open-format PDFs.

The site (== repo directory name, e.g. efl/fle/daf) selects the LaTeX accent
via \\blgsetlang and the /<site> URL prefix. Section names, answer-key formats
and the flat slug are detected across English, French and German units.

Usage:
  build_materials_latex.py [--only SLUG_SUBSTR] [--limit N] [--keep-tex]
Local, LLM-free, deterministic. Requires xelatex + the vendored templates in
_materials/.
"""
import sys, os, re, subprocess, glob, argparse, shutil
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SITE = REPO.name                 # efl | fle | daf -> \blgsetlang{SITE}, /SITE URLs
MAT = REPO / "_materials"
PRES = REPO / "static/materials/presentations"
WORK = REPO / "static/materials/worksheets"
URL = "/" + SITE

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
    # arrows/symbols the bundled text font lacks -> math equivalents
    for u,t in (('→',r'$\to$'),('←',r'$\gets$'),('↔',r'$\leftrightarrow$'),
                ('⇒',r'$\Rightarrow$'),('⇐',r'$\Leftarrow$'),('×',r'$\times$'),
                ('≥',r'$\geq$'),('≤',r'$\leq$'),('≈',r'$\approx$'),('≠',r'$\neq$'),
                ('±',r'$\pm$'),('÷',r'$\div$'),('∞',r'$\infty$')):
        s = s.replace(u, t)
    return s

# ---------- unit parsing ----------
def parse(md):
    m = re.match(r'^---\n(.*?)\n---\n(.*)$', md, re.S)
    fm_raw, body = (m.group(1), m.group(2)) if m else ("", md)
    fm = {}
    for line in fm_raw.split('\n'):
        mm = re.match(r'^(\w[\w_]*):\s*"?(.*?)"?\s*$', line)
        if mm and mm.group(2): fm[mm.group(1)] = mm.group(2)
    # split into level-2 sections (keep level-3 inside)
    parts = re.split(r'(?m)^##\s+(.+?)\s*$', body)
    secs = []  # (title, text)
    for i in range(1, len(parts), 2):
        secs.append((parts[i].strip(), parts[i+1].strip()))
    return fm, secs

def norm(t):
    return re.sub(r'^\d+\.?\s*', '', t).strip().lower()

def strip_callouts(t):
    """Remove {{< callout >}}…{{< /callout >}} and {{< details >}}…{{< /details >}}
    blocks (answer keys, grading scales, hints) so section extraction doesn't
    pull answers into exercises."""
    t = re.sub(r'\{\{<\s*callout.*?\{\{<\s*/callout\s*>\}\}', '', t, flags=re.S)
    t = re.sub(r'\{\{<\s*details.*?\{\{<\s*/details\s*>\}\}', '', t, flags=re.S)
    return t

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
                return terms[:12]
    rows = [l for l in text.split('\n') if l.strip().startswith('|')]
    if len(rows) >= 4:
        terms=[]
        for r in rows[2:]:
            cells=[c.strip() for c in r.strip().strip('|').split('|')]
            if cells and cells[0] and not set(cells[0])<=set('-: '):
                terms.append(re.sub(r'[*`]','',cells[0]))
        terms=[t for t in terms if t]
        if len(terms) >= 4 and max(len(t) for t in terms) <= 28:
            return terms[:12]
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

def answer_keys(md, secs):
    """Answer keys, wherever the site keeps them: callout/details blocks titled
    Answer key / Lösungen / Solutions / Corrigé (EFL, DaF), or a dedicated
    ## Solutions / ## Lösungen / ## Corrigé section (FLE)."""
    out = []
    pat = (r'\{\{<\s*(?:callout|details)[^>]*title="(?:Answer key|L\wsungen?|'
           r'Solutions?|Corrig\w)"[^>]*>\}\}(.*?)\{\{<\s*/(?:callout|details)\s*>\}\}')
    for m in re.finditer(pat, md, re.S):
        for ln in m.group(1).strip().split('\n'):
            s = ln.strip()
            if s and not s.startswith('|'): out.append(s)
    for ln in find_sec(secs, *SEC["solutions"]).split('\n'):
        s = ln.strip()
        if s and not s.startswith('|'): out.append(s)
    return out

# ---------- localisation (labels follow the site's language) ----------
LANG = {"efl": "en", "fle": "fr", "daf": "de"}.get(SITE, "en")
L = {
  "en": {"obj":"Learning objectives","lead":"Lead-in","vocab":"Vocabulary",
         "key":"Key points","prac":"Practise","turn":"Your turn","refl":"Reflect",
         "read":"Reading","write":"Write","term":"Term","note":"Your note",
         "v_i":"Match each item to its meaning or use it in a sentence.",
         "r_i":"Read the text, then answer in full sentences."},
  "fr": {"obj":"Objectifs","lead":"Mise en situation","vocab":"Vocabulaire",
         "key":"Points clés","prac":"S'entraîner","turn":"À toi de jouer","refl":"Réfléchir",
         "read":"Lecture","write":"Produire","term":"Terme","note":"Votre note",
         "v_i":"Associez chaque terme à son sens ou employez-le dans une phrase.",
         "r_i":"Lisez le texte, puis répondez par des phrases complètes."},
  "de": {"obj":"Lernziele","lead":"Einstieg","vocab":"Wortschatz",
         "key":"Kernpunkte","prac":"Üben","turn":"Anwenden","refl":"Reflexion",
         "read":"Lesen","write":"Schreiben","term":"Wort","note":"Ihre Notiz",
         "v_i":"Ordnen Sie jedem Wort seine Bedeutung zu oder verwenden Sie es im Satz.",
         "r_i":"Lesen Sie den Text und antworten Sie in ganzen Sätzen."},
}[LANG]

# ---------- LaTeX emit ----------
def frame(title, body):
    return f"\\begin{{frame}}{{{esc(title)}}}\n{body}\n\\end{{frame}}\n"

def itemize(items, small=False):
    if not items: return ""
    sz = "\\small\n" if small else ""
    return sz+"\\begin{itemize}\n" + "\n".join(f"  \\item {inline(x)}" for x in items) + "\n\\end{itemize}"

def build_deck(fm, secs, title, subtitle):
    F = []
    F.append("\\begin{frame}[plain]\\titlepage\\end{frame}")
    obj = bullets(find_sec(secs, *SEC["objectives"]))
    if obj: F.append(frame(L["obj"], itemize(obj)))
    lead = paragraphs(find_sec(secs, *SEC["leadin"]))
    if lead:
        F.append(frame(L["lead"], f"\\large {inline(lead[0])}"))
    terms = vocab_terms(secs)
    if terms:
        half = (len(terms)+1)//2
        col1 = itemize(terms[:half]); col2 = itemize(terms[half:])
        F.append(frame(L["vocab"],
            f"\\begin{{columns}}[T]\n\\column{{0.5\\linewidth}}\n{col1}\n"
            f"\\column{{0.5\\linewidth}}\n{col2}\n\\end{{columns}}"))
    moves = move_lines(secs)
    if moves:
        F.append(frame(L["key"], itemize(moves, small=True)))
    prac = bullets(find_sec(secs, *SEC["practise"]))[:5]
    if prac: F.append(frame(L["prac"], itemize(prac, small=True)))
    prod = paragraphs(find_sec(secs, *SEC["produce"]))
    if prod:
        F.append(frame(L["turn"], f"\\large {inline(prod[0])}"))
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
            "\\begin{tabularx}{\\linewidth}{@{}p{5cm}X@{}}\n\\toprule\n"
            f"\\textbf{{{esc(L['term'])}}} & \\textbf{{{esc(L['note'])}}} \\\\\n\\midrule\n"
            f"{rows} \\\\\n\\bottomrule\n\\end{{tabularx}}")
    src = ""
    inp = find_sec(secs, *SEC["input"])
    for p in paragraphs(inp):
        if len(p) > 160: src = p; break
    if src:
        S.append(f"\\section{{{esc(L['read'])}}}\n{esc(L['r_i'])}\n\n"
                 f"\\begingroup\\itshape {inline(src)}\\endgroup\n\\blglines[2]")
    prac = bullets(find_sec(secs, *SEC["practise"]))
    if prac:
        items = "\n".join(f"  \\item {inline(x)}" for x in prac)
        S.append(f"\\section{{{esc(L['prac'])}}}\n\\begin{{enumerate}}\n"+items+"\n\\end{enumerate}\n\\blglines[3]")
    prod = paragraphs(find_sec(secs, *SEC["produce"]))
    if prod:
        S.append(f"\\section{{{esc(L['write'])}}}\n"+inline(prod[0])+"\n\\blglines[6]")
    ans = answer_keys(md, secs)
    ansbox = ""
    if ans:
        body = " \\\\\n".join(inline(a) for a in ans[:8])
        ansbox = "\\begin{blganswers}\n"+body+"\n\\end{blganswers}"
    return (TEX_SHEET.replace("@@TITLE@@", inline(title)).replace("@@SUBTITLE@@", inline(subtitle))
            .replace("@@BADGE@@", esc(badge)).replace("@@LANG@@", SITE)
            .replace("@@SECTIONS@@", "\n\n".join(S)).replace("@@ANSWERS@@", ansbox))

TEX_DECK = r"""\documentclass[aspectratio=169,11pt]{beamer}
\usetheme{boulingua}
\blgsetlang{@@LANG@@}
\title{@@TITLE@@}
\subtitle{@@SUBTITLE@@}
\begin{document}
@@FRAMES@@
\end{document}
"""
TEX_SHEET = r"""\documentclass[11pt]{article}
\usepackage{boulingua-sheet}
\blgsetlang{@@LANG@@}
\begin{document}
\worksheetheader{@@TITLE@@}{@@SUBTITLE@@}{@@BADGE@@}{blgcefrB}
\begin{sheetbody}
@@SECTIONS@@

@@ANSWERS@@
\end{sheetbody}
\end{document}
"""

def xelatex(texfile, passes=2):
    for _ in range(passes):
        r = subprocess.run(["xelatex","-interaction=nonstopmode","-halt-on-error",texfile.name],
                           cwd=MAT, capture_output=True, text=True)
    return (MAT / (texfile.stem + ".pdf")).is_file(), r

def thumb(pdf, png):
    import fitz
    d = fitz.open(pdf); pg = d[0]
    z = 900 / pg.rect.width
    pg.get_pixmap(matrix=fitz.Matrix(z, z)).save(png)

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
    """Reuse the site's established flat slug: take it from the existing
    presentation:/worksheet: URL if present (keeps every download link stable
    across the .odp/.pptx -> .pdf migration); otherwise derive it."""
    m = re.search(r'/materials/(?:presentations|worksheets)/([^/"\s.]+)\.(?:pdf|odp|pptx)', md)
    if m: return m.group(1)
    if md_path.name == "index.md":            # EFL leaf bundle
        return md_path.parent.name
    return md_path.stem                        # FLE/DaF single-file unit

def unit_badge(fm, md_path):
    niv = fm.get("niveau") or fm.get("cefr") or fm.get("niveau_cefr")
    if niv: return f"Niveau {niv}"
    m = re.search(r'kurs_([abc][12])', str(md_path), re.I)   # DaF: kurs_a1 -> A1
    return m.group(1).upper() if m else ""

def process(md_path, keep_tex=False):
    md = md_path.read_text()
    fm, secs = parse(md)
    name = md_path.parent.name if md_path.name == "index.md" else md_path.stem
    title = fm.get("title", name)
    subtitle = fm.get("subtitle", "")
    badge = unit_badge(fm, md_path)
    slug = unit_slug(md_path, md)
    ok = {"unit": name, "deck": False, "sheet": False}
    PRES.mkdir(parents=True, exist_ok=True); WORK.mkdir(parents=True, exist_ok=True)
    # deck
    dtex = MAT / f"{slug}-deck.tex"; dtex.write_text(build_deck(fm, secs, title, subtitle))
    good, r = xelatex(dtex)
    if good:
        shutil.move(str(MAT / f"{slug}-deck.pdf"), str(PRES / f"{slug}.pdf"))
        thumb(PRES / f"{slug}.pdf", PRES / f"{slug}.png"); ok["deck"] = True
    else:
        ok["err_deck"] = r.stdout[-400:]
    # worksheet
    wtex = MAT / f"{slug}-sheet.tex"; wtex.write_text(build_worksheet(fm, secs, md, title, subtitle, badge))
    good, r = xelatex(wtex)
    if good:
        shutil.move(str(MAT / f"{slug}-sheet.pdf"), str(WORK / f"{slug}.pdf"))
        thumb(WORK / f"{slug}.pdf", WORK / f"{slug}.png"); ok["sheet"] = True
    else:
        ok["err_sheet"] = r.stdout[-400:]
    if ok["deck"] and ok["sheet"]:
        upsert_fm(md_path, slug)
    if not keep_tex:
        for f in MAT.glob(f"{slug}-*"):
            if f.suffix in (".aux",".log",".nav",".snm",".toc",".out",".tex"): f.unlink()
    return ok

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=""); ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--keep-tex", action="store_true")
    a = ap.parse_args()
    # EFL units are leaf bundles (units/<slug>/index.md); FLE/DaF are single
    # files (units/<slug>.md). Take any markdown under a units/ folder that
    # carries a presentation: block (i.e. a real material-bearing teaching unit).
    units = sorted(p for p in REPO.glob("content/**/*.md")
                   if "/units/" in p.as_posix() and p.name != "_index.md")
    units = [u for u in units if a.only in str(u)]
    units = [u for u in units if 'presentation:' in u.read_text()]
    if a.limit: units = units[:a.limit]
    okc = deckc = sheetc = 0
    for u in units:
        r = process(u, a.keep_tex); okc += 1
        deckc += r["deck"]; sheetc += r["sheet"]
        flag = "OK" if r["deck"] and r["sheet"] else "PARTIAL"
        print(f"[{flag}] {r['unit']}  deck={r['deck']} sheet={r['sheet']}")
        if not r["deck"] and r.get("err_deck"): print("   deck err:", r["err_deck"].replace('\n',' ')[-200:])
        if not r["sheet"] and r.get("err_sheet"): print("   sheet err:", r["err_sheet"].replace('\n',' ')[-200:])
    print(f"\n{okc} units | {deckc} decks | {sheetc} worksheets")

if __name__ == "__main__":
    main()
