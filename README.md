# kit — the boulingua platform

**A course repo contains content, marks, materials, brand and configuration.
It contains no code.** Everything else lives here, once, and is imported.

This repo replaces `pagegen`, `slidegen`, `sheetgen` and `audiogen`. Their
histories are preserved here by subtree merge; the originals are archived.

## Why it is not a template

`pagegen` was copied to start a course. That model had already failed, and it
failed quietly: of sixteen script basenames shared between repos, nine had
forked byte-for-byte; all ten shared layout partials had diverged, with
`head/extensions.html` at six distinct hashes across six repos; and one counting
pixel was emitted by a partial living under three different names, backed by a
manifest file with four incompatible schemas. Nothing detected any of it,
because copying leaves no link to detect.

A course now *imports* the shared surface. Drift stops being something to police
and becomes something that cannot happen: the files are not in the course repo.

## How a course consumes it

| Layer | Mechanism | Why this one |
|---|---|---|
| `layouts/ assets/ static/ i18n/ archetypes/ data/` | Hugo Module | Hugo consumes modules natively. The files stop existing in the course repo, so most of the drift surface is removed by construction. |
| `scripts/` and the gate battery | CI checkout + local `bin/kit` | A workflow needs scripts on disk before Hugo runs. A module in the Hugo cache is not such a path. |
| `latex/`, `fonts/`, `brand/` | vendored `_materials/`, digest-locked | XeLaTeX cannot read a Hugo module. This is the only vendored surface, and it is hash-gated. |

## Layout

```
hugo.defaults.toml   the per-course config; copy it, change the marked values
templates/deploy.yml the twelve-line workflow every course runs
example/             the kit's own content tree — builds on every push with
                     --panicOnWarning, which is the platform's first gate
layouts/ assets/ static/ i18n/ archetypes/ data/   the Hugo module surface
latex/               the two .sty files, both templates, one Makefile
fonts/ brand/        assets the LaTeX side needs, assembled flat into _materials/
audio/               build_audio.py, get_voices.sh, voices.yml, templates
scripts/             generators and gate scripts
docs/                the binding standards
```

`latex/Makefile` assembles `fonts/`, `brand/` and the `.sty` files into a flat
tree and compiles there, because that is the arrangement a course receives. It
tests what ships rather than something more convenient.

## Arriving later

These are named in the platform plan and land with their own work items, so the
tree above is what exists rather than what is intended: `design/` with the token
and font generators (F2, F3), the per-script font sets under `fonts/` (F3), the
RTL and CJK LaTeX templates (F4, deferred), `bin/kit` (F10), and the seven
teaching shortcodes (F12).

## Licence

Code MIT (`LICENSE`). Content CC BY-SA 4.0 (`LICENSE-CONTENT.md`).
