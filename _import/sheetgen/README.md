# sheetgen

LaTeX **worksheet template** in the [boulingua](https://github.com/boulingua)
design language, for printable exercise sheets that match the sister sites and
the [slidegen](https://github.com/boulingua/slidegen) slide decks.

> **Status — draft.** The style and an example worksheet are in place; a
> content-to-worksheet generator will follow.

---

## Requirements

- **XeLaTeX** or **LuaLaTeX** (the style uses `fontspec`; pdfLaTeX will not work).
- No system fonts needed — Source Sans 3, JetBrains Mono and Permanent Marker are
  bundled in `fonts/`.
- **Compile twice.** The foot watermark is placed with TikZ `remember picture`,
  which needs two passes to settle. `make` does this for you.

## Quick start

```bash
make            # build worksheet-template.pdf (two XeLaTeX passes)
make clean      # remove LaTeX aux files
```

or by hand:

```bash
xelatex worksheet-template.tex
xelatex worksheet-template.tex
```

## Using the style in your own sheet

```latex
\documentclass[11pt]{article}
\usepackage{boulingua-sheet}
\blgsetlang{efl}          % pick the language accent + icon (see table below)

\begin{document}
% \worksheetheader{Title}{Subtitle line}{Badge label}{badge colour}
\worksheetheader{Unit 2 — Growing Up}%
  {English · Track G+M · Klasse 7 · Skill: Reading \& Writing}%
  {Niveau M}{blgcefrB}

\section{Vocabulary}
Match each word to its definition.
\blglines[4]

\begin{blganswers}
\textbf{1.} ...
\end{blganswers}
\end{document}
```

### Helpers

| Command / env | Purpose |
|---|---|
| `\worksheetheader{title}{subtitle}{badge}{badgecolour}` | Header block: title, language icon (top-right), subtitle, level badge, accent rule. The **title** is also picked up by the foot watermark. |
| `\blgbadge[colour]{label}` | A rounded pill badge (defaults to the accent). |
| `\blglines[n]` | *n* ruled writing lines for hand-written answers (default 3). |
| `blganswers` (env) | A shaded "Solutions" answer-key box. |
| `\blgsetlang{code}` | Set the language accent **and** icon in one call. Omit to stay boulingua blue. |
| `\blglangmark[height]` | Draw the current language's icon (used in the header; available anywhere). |

Badge colours: the shared CEFR ramp `blgcefrA` / `blgcefrB` / `blgcefrC`, or the
language accent `blgaccent`.

## Design language

- **Fonts:** Source Sans 3 (headings/body) + JetBrains Mono (code), bundled.
- **CEFR ramp** (shared across all sites, independent of language):
  A `#4CAF50`, B `#1A73E8`, C `#8E24AA`.
- **Watermark:** boulingua logo + `© S. Le Boulanger · <title>`, centred at the
  foot of every page (`<title>` comes from `\worksheetheader`).
- **Per-language accent + icon** — see below.

## Per-language accent colours & icons

Every language project has **its own signature accent**, shown as a **pentagon** in that colour. The accents are **flag-safe** — each hue is deliberately chosen *not* to
appear in that language's own flag — mutually distinct (≥20° apart on the hue
wheel), kept clear of the boulingua hub blue, and contrast-checked for light and
dark backgrounds. Select one with `\blgsetlang{code}`:

<!-- palette:begin -->
| Code | Language | Light accent | Dark accent |
|------|----------|--------------|-------------|
| `daf` | German | `#1D87A7` | `#7ECEE7` |
| `efl` | English | `#248D19` | `#89E77E` |
| `fle` | French | `#4B8D19` | `#ACE77E` |
| `afl` | Arabic | `#4A23C7` | `#977EE7` |
| `cfl` | Chinese | `#2334C7` | `#7E89E7` |
| `ele` | Spanish | `#198D81` | `#7EE7DC` |
| `gfl` | Greek | `#C74A23` | `#E7977E` |
| `ils` | Italian | `#8023C7` | `#B97EE7` |
| `jfl` | Japanese | `#867B18` | `#E7DC7E` |
| `lle` | Latin | `#C72334` | `#E77E89` |
| `nsf` | Norwegian | `#6D8618` | `#CEE77E` |
| `nvt` | Dutch | `#198D34` | `#7EE797` |
| `pfl` | Polish | `#AD701F` | `#E7B97E` |
| `ple` | Portuguese | `#B723C7` | `#DC7EE7` |
| `rki` | Russian | `#198D5B` | `#7EE7B9` |
| `tfl` | Turkish | `#C7236A` | `#E77EAC` |
| `ufl` | Ukrainian | `#C723A1` | `#E77ECE` |
<!-- palette:end -->

The worksheets use the **light** accent (they print on white). The dark values
are the matching web dark-theme accents, kept here so the whole boulingua colour
system lives in one place. The icons in `brand/icons/<code>.pdf` are the same
marks used in each language's README and on the hub website.

## Files

```
boulingua-sheet.sty        the style (palette, fonts, header, helpers, \blgsetlang)
worksheet-template.tex     worked example worksheet
brand/icons/<code>.pdf     17 per-language icons (accent-filled)
fonts/                     bundled TTFs
assets/boulingua-logo.png  watermark logo (black-on-transparent)
Makefile
```

## Licence

Code MIT (see `LICENSE`). The boulingua logo and name are used under the project's own terms.

## Use of LLM tools

Portions of this project were prepared with assistance from large language model tooling for narrowly defined, non-authorial tasks: copyediting, prose smoothing, Markdown/LaTeX formatting, scaffolding of boilerplate files (CI configs, build scripts), code refactoring. The tools used were Chat AI, the LLM service of KISSKI (GWDG), and a self-hosted Mistral Small (24B, Apache-2.0) run locally via Ollama and the ollamar R package — local inference only, with no data sent to third parties for the self-hosted model.
