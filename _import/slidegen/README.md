# slidegen

Beamer (LaTeX) **slide template** in the [boulingua](https://github.com/boulingua)
design language, for course presentations that match the sister sites and the
[sheetgen](https://github.com/boulingua/sheetgen) worksheets.

> **Status — draft.** The theme and an example deck are in place; a
> content-to-slides generator will follow.

---

## Requirements

- **XeLaTeX** or **LuaLaTeX** (the theme uses `fontspec`; pdfLaTeX will not work).
- No system fonts needed — Source Sans 3, JetBrains Mono and Permanent Marker are
  bundled in `fonts/`.
- **Compile twice.** The foot watermark is placed with TikZ `remember picture`,
  which needs two passes to settle. `make` does this for you.

## Quick start

```bash
make            # build slides-template.pdf (two XeLaTeX passes)
make clean      # remove LaTeX aux files
```

or by hand:

```bash
xelatex slides-template.tex
xelatex slides-template.tex
```

## Using the theme in your own deck

```latex
\documentclass[aspectratio=169,11pt]{beamer}
\usetheme{boulingua}
\blgsetlang{efl}          % pick the language accent + icon (see table below)

\title{Unit 2 — Growing Up}
\subtitle{English · Track G+M · Klasse 7 · Niveau M}
% \author and \date are NOT shown on the title slide — the foot watermark
% already carries "© S. Le Boulanger · <title>" on every slide.

\begin{document}
\begin{frame}[plain]\titlepage\end{frame}

\begin{frame}{Learning objectives}
  \begin{itemize}
    \item ...
  \end{itemize}
\end{frame}
\end{document}
```

### What the theme gives you

| Element | Behaviour |
|---|---|
| **Title slide** | Language icon → title → accent rule → subtitle. No author/date (see watermark). |
| **Frame titles** | Semibold, with a thin accent rule underneath. |
| **`block`** | Rounded, accent-coloured title bar (use for *Rule*, *Note*, *Tip* …). |
| **Itemize bullets** | Small accent squares. |
| **Foot watermark** | The boulingua **B** (black-on-transparent) + `© S. Le Boulanger · <title>`, centred on **every** slide. `<title>` is pulled from `\title`. |
| **Slide number** | Muted, lower-right. |

### Commands

- `\blgsetlang{code}` — set the language accent **and** the language icon in one call
  (e.g. `\blgsetlang{daf}`). Call it once in the preamble. Omit it to stay boulingua blue.
- `\blglangmark[height]` — draw the current language's icon (used on the title slide;
  available anywhere, e.g. `\blglangmark[8mm]`). No-op until `\blgsetlang` is called.

## Design language

- **Fonts:** Source Sans 3 (headings/body) + JetBrains Mono (code), bundled.
- **CEFR ramp** (shared across all sites, independent of language):
  A `#4CAF50`, B `#1A73E8`, C `#8E24AA`.
- **Watermark:** boulingua logo + author, centred at the foot of every slide.
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

The slides use the **light** accent (they print on white). The dark values are
the matching web dark-theme accents, kept here so the whole boulingua colour
system lives in one place. The icons in `brand/icons/<code>.pdf` are the same
marks used in each language's README and on the hub website.

## Files

```
beamerthemeboulingua.sty   the theme (palette, fonts, templates, \blgsetlang)
slides-template.tex        worked example deck
brand/icons/<code>.pdf     17 per-language icons (accent-filled)
fonts/                     bundled TTFs
assets/boulingua-logo.png  watermark logo (black-on-transparent)
Makefile
```

## Licence

Code MIT (see `LICENSE`). The boulingua logo and name are used under the project's own terms.

## Use of LLM tools

Portions of this project were prepared with assistance from large language model tooling for narrowly defined, non-authorial tasks: copyediting, prose smoothing, Markdown/LaTeX formatting, scaffolding of boilerplate files (CI configs, build scripts), code refactoring. The tools used were Chat AI, the LLM service of KISSKI (GWDG), and a self-hosted Mistral Small (24B, Apache-2.0) run locally via Ollama and the ollamar R package — local inference only, with no data sent to third parties for the self-hosted model.
