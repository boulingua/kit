# Boulingua kit

Shared site templates, design tokens, teaching components, material/audio
builders and release checks for the Boulingua suite. Courses import the Hugo
module and keep their own content, configuration, brand, downloads and provenance.
The archived `pagegen`, `slidegen`, `sheetgen` and `audiogen` are historical
predecessors; their maintained successors live here.

## Install and verify

Use Python 3.12, Node 22, Go 1.26.1 and Hugo extended 0.159.2.

```sh
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
npm ci
npm exec -- playwright install chromium
python -m unittest discover -s tests -v
python scripts/test_blg_paths.py
python scripts/build_example.py
```

The example exercises the current checkout through a local Hugo workspace.
It is a teaching-component fixture, not a publishable completed course.
On Linux, `playwright install --with-deps chromium` supplies browser libraries.
CI runs the Python regressions, generated-design checks and strict example build.
Browser checks run against actual course builds via C14.

## Work on a course

```sh
python bin/kit new nsf --into ../nsf
python bin/kit sync ../nsf
python bin/kit build ../nsf
python bin/kit check ../nsf --ci \
  --owner-root curriculum=../curriculum --owner-root .github=../.github
```

Scaffolding preserves existing files and creates an explicit development site;
it does not invent lessons or reviewed curriculum coverage. Deferred scripts
remain disabled under ADR-0018. `sync` refuses modified or untracked material
files before copying anything. Move intentional local authoring outside the
kit-owned `_materials/` tree before synchronizing.

A course normally imports its pinned released kit version. To review a new kit
checkout with a course, create a local Go workspace in that course:

```sh
go work init ../kit
export HUGO_MODULE_WORKSPACE="$PWD/go.work"
```

Do not commit this machine-specific workspace. Use matching platform,
framework and organisation checkouts for release verification. The 30 October
changes are not yet published as a new compatible release set.

`kit build` runs strict Hugo compilation and configured graph/search generation.
For a production-style local preview retaining the course URL prefix:

```sh
mkdir -p build/preview
ln -s "$PWD/../nsf/public" build/preview/nsf
python -m http.server 1317 --bind 127.0.0.1 --directory build/preview
```

Open `http://127.0.0.1:1317/nsf/`. A development server may instead use
`hugo server` from the course directory after building the search index.

## Materials, audio and release evidence

XeLaTeX and the documented TeX packages are needed only for PDF generation.
Piper, voice models and FFmpeg are needed only for audio generation; see
[audio/README.md](audio/README.md) for the isolated setup and review workflow.
Human recordings are retained. A preview or successful synthesis is not a
pronunciation approval. Model/configuration digests and speaker identity must
match the dated listener record before synthetic audio passes release checks.

`gates.yml` is the gate registry. Missing required tools or artifacts are
failures. Incomplete educational mappings and unresolved historical provenance
must remain visible. C14 covers representative browser journeys and automated
WCAG 2.1 AA checks; it does not replace manual accessibility or language review.
C15 measures local discovery scripts plus explicitly referenced lazy graph
modules; separately declared telemetry and later search shards are outside that
budget and are identified in its report.

See [REFINEMENT.md](REFINEMENT.md) for findings and current verification.
Code is MIT (`LICENSE`); original teaching content is CC BY-SA 4.0,
attributed to S. Le Boulanger (`LICENSE-CONTENT.md`). Third-party terms are in
`NOTICE.md`, font provenance records and `audio/NOTICE.md`.
