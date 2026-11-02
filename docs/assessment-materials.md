# Assessment review PDFs

`build_assessments_latex.py` exports the actual standalone exam source as a
learner copy and a separate teacher copy. It retains the prompts, source texts,
scoring rules and source links. Answer-bearing `details`/`callout` blocks marked
`role="key"` appear only in the teacher copy. Mark every answer explicitly;
a successful export cannot determine whether an unmarked paragraph reveals one.
Public `Barème`/`Notenschlüssel` blocks remain visible. An unmarked block whose
title identifies it as a solution is rejected until its role is made explicit.

## Prerequisites and first use

Use Python 3.12 with the kit's `requirements.txt`, and XeLaTeX from TeX Live 2026
(or a corresponding full MacTeX installation). The shared styles need `beamer`,
`fontspec`, `xcolor`, `geometry`, `titlesec`, `enumitem`, `tools` (including
`tabularx`/`array`), `booktabs`, `tcolorbox`, `graphics`, `eso-pic`, `pgf`,
`fancyhdr`, `changepage`, `hyperref`, `etoolbox` and `needspace`. Course fonts and
brand assets are supplied by `kit sync`; no system-font substitution is needed.

From the kit checkout, with the Python environment active:

```sh
python bin/kit sync ../daf
python scripts/build_assessments_latex.py ../daf \
  --output-root ../assessment-review \
  --only kurs_b1/units/unit04_gesundheitssystem-dach_exam
```

Omit `--only` to process every standalone exam. The output directory must be
outside the course checkout. A negative `--limit`, unsafe destination, duplicate
learner/teacher path, unsupported shortcode, missing glyph or overflowing box
fails the build. Use a fresh staging directory to retain each review attempt.
Symlinks anywhere inside an existing staging tree are rejected before writing.
Markdown images and embedded HTML media also fail: this exporter cannot yet
carry a visual/listening asset into the paper and must not silently drop one.

The output contains learner/teacher PDFs, 1000-pixel first-page thumbnails,
LaTeX sources/logs and `assessments-receipt.json`. The receipt records source,
generator, renderer, LaTeX and PDF hashes, with distinct intermediate paths for
each output directory. Producer hashes are captured when code loads, and a
mid-run code change fails instead of relabelling earlier outputs. Each destination
workspace also records its typesetting support files. Reusing a workspace after
source styles/fonts change, after a staged support file changes, or without that
receipt fails with a request to use a fresh output root; stale support is never
silently reused. DaF keeps its established
`downloads/<level>/unitNN_<slug>_exam.pdf` learner URL; teacher copies add
`-teacher`. Other courses require an explicit safe `material_slug`.

These are review copies unless the source has an actual
`assessment_review: approved` record. Source fidelity and arithmetic checks
cannot approve language, pedagogy, rights or suitability for a formal examination.

## Verification and publication

Read both versions, compare all tasks/stimuli/criteria against the source, test
source links, and check that learner copies contain no keys. Confirm source
hashes are unchanged since generation and preserve previous files before
publishing. The builder itself changes no course source or published asset.

After a verified publication, exam front matter can expose distinct downloads:

```yaml
assessment:
  file: /daf/downloads/b1/unit04_gesundheitssystem-dach_exam.pdf
  thumbnail: /daf/downloads/b1/unit04_gesundheitssystem-dach_exam.png
assessment_teacher:
  file: /daf/downloads/b1/unit04_gesundheitssystem-dach_exam-teacher.pdf
  thumbnail: /daf/downloads/b1/unit04_gesundheitssystem-dach_exam-teacher.png
```

Run `python scripts/verify_downloads.py ../daf` and rebuild the course. The
browser journey checks that learner and teacher links are distinct and resolve.
`python scripts/verify_assessment.py ../daf` checks recognized scoring rules;
it does not replace a source/key review or timed classroom trial.
