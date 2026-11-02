# Refinement record — 30 October 2026

This is an engineering candidate on `refine/2026-10-30`. Hosted checkpoint
evidence and later local changes are distinguished below. No release tag or
production deployment is claimed.
The suite strategy and integration order live in the organisation repository,
`docs/refinement-2026-10-30.md` and `docs/release-candidate-2026-10-30.md`.

## Findings and changes

- High: gates could validate missing artifacts or the wrong repository. The CLI now distinguishes repository and build-root arguments; search, translations, path, font, token, catalogue and actual browser checks exercise their claimed inputs.
- High: audio and material generation could leave partial or stale outputs. Audio staging preserves existing and human recordings on failure; model/configuration digests and speaker identity invalidate the cache. PDF outputs publish only after both documents compile and thumbnails render; stale intermediate PDFs and missing glyphs fail.
- High: print extraction truncated vocabulary and multi-paragraph tasks, discarded differentiation, flattened exercise structure and mixed exam answers into lesson keys. Full task blocks, criteria tables, authored numbering and lesson-only answers now survive. Teaching points join soft-wrapped paragraphs before slide layout, so explanations are not truncated mid-sentence. Answer headings follow the course language. U+2B51 differentiation marks use a vector star with PDF ActualText because Source Sans 3 lacks that glyph.
- High: menu focus, project-prefix links, contrast, small text and missing landmarks affected real use. Shared templates now provide native disclosures, skip navigation, labelled checkboxes and corrected design tokens. Browser checks cover searches, downloads, mobile navigation and no-JavaScript content.
- Medium: graph libraries loaded before use and budget checks did not inspect real output. Discovery loads graph code on request; C15 checks eager and lazy assets and distinguishes explicitly configured telemetry.
- Medium: scaffolds and material synchronisation lacked safe first-use behaviour. Development-course generation creates coherent manifests, licence notices and legal pages; sync refuses locally edited or unknown files before writing anything.

## Validation and limits

Python regression suite: 41 tests passed, including failure paths, task preservation and instruction-language selection. All 18 course material trees synchronised successfully, including an idempotence/protected-edit test. Parser dry run: 180 EFL, 156 FLE and 60 DaF units, no parsing exceptions. XeLaTeX 2026 compiled and visually reviewed one slide deck and worksheet per established course. This is not a full-corpus print or pedagogical review; the 852 committed course PDFs were preserved.

The minimal generated example built with strict Hugo checks. Current source checks passed for token generation, token use, fonts, translations, contrast and material paths. All 15 development courses passed the full local gate battery. Established courses expose historical audio failures instead of hiding them. Browser checks are representative WCAG 2.1 AA automation, not complete manual accessibility certification.

The local voice audit produced 42 decodable WAV previews for 14 candidates with pinned model/config/card digests. A disposable real unit produced two Opus clips and a repeat run synthesised none. Listener approval remains pending; missing historical metadata cannot be inferred from a new voice model.

## Acceptance and next milestone

The engineering candidate can be installed and exercised using README.md and audio/README.md. Release the kit only after review of its diff, recorded dependency audit and a passing hosted equivalent of its local checks. Coordinate the organisation workflow and consumer pins as one release set. Native listener approval, curriculum-source repair, course authoring and full regenerated-material review remain separate acceptance criteria.


## 2026-10-31 — foundation release-blocker repairs

The re-audit exposed failures beyond the earlier candidate evidence. The path
contract's default command now uses committed snapshots of the three actual
content models, with source commits and licence retained. It passes without
sibling checkouts; a missing required fixture still fails. Live URL/material
integration is explicitly requested with `--org-root`, and is never implied by
a fixture-only pass.

Material extraction now preserves the full Input section and its multiple
stimuli, task requirements, criteria and answer tables. Slides retain the input
and lead-in text too. The existing worksheet URL now denotes the learner copy;
answers are delivered separately as `SLUG-teacher.pdf`/`.png`, linked through
`worksheet_teacher`. Both title and summary answer wrappers are recognized,
including nested wrappers. Malformed nesting fails generation. Hugo heading
anchors are not printed. All three documents must compile and render thumbnails
before the unit's outputs are replaced. An intervening source edit is rejected.

`--output-root` stages outside the course and records source/generator/PDF
hashes without changing course files. The primary CLI forwards selection and
staging options; thumbnail-only mode rejects conflicting generation flags.
After Python 3.12 dependencies, XeLaTeX and the documented fonts/templates are
available, run from this kit checkout:

```sh
python bin/kit sync ../efl
python bin/kit sync ../fle
python bin/kit sync ../daf
python bin/kit materials ../efl --keep-tex --output-root ../../review-materials/efl
python bin/kit materials ../fle --keep-tex --output-root ../../review-materials/fle
python bin/kit materials ../daf --keep-tex --output-root ../../review-materials/daf
python scripts/test_blg_paths.py --org-root .. efl fle daf
```

Use `--only PATH_SUBSTRING --limit 1` for a selected first unit. Review the
complete output receipts and PDFs before publishing the rebuilt corpus; adding
these commands does not establish that every course PDF has been rebuilt.

Speech extraction no longer drops bold-speaker/italic-utterance lines. Genuine
human recordings now require retained source/permission records and an actual
dated review bound to the delivered audio and exact transcript hashes. An
explicit private evidence root avoids publishing personal consent/source files.
`audio/README.md` documents the record and its limits: checking a record cannot
prove a permission claim true, and no fabricated review can close a release gate.

Verification at this milestone: 63 Python tests passed; live integration
reproduced 761 marked URLs and 396 presentation names. All 396 migrated teaching
units produced deck/learner/teacher TeX without exceptions. Three actual lesson
sets compiled to nine PDFs (65 pages), and the primary CLI compiled the migrated
FLE example to another three PDFs (22 pages). Extracted text confirmed missing
stimuli and production requirements now survive, answers appear only in teacher
copies, and the final logs had no missing-glyph/overfull findings. Three key
pages were visually inspected. Independent review found and then rechecked the
nested-answer case before full corpus generation. A compiled nested-answer fixture
then confirmed the secret absent in its learner PDF and present in its teacher PDF.

An isolated two-lesson audio run produced eight mono Opus clips (201.3 seconds)
and a repeat synthesized zero clips. The initial attempt lacked FFmpeg on PATH;
the existing bundled executable was exposed only in the test artifact environment
and the retry succeeded. D6 still correctly rejects these clips as an unapproved
candidate voice with no dated audition. A real-OGG negative fixture with only
`source: human` now fails for missing provenance. Course recordings and approval
records were not changed.

Detailed local evidence is retained under the suite workspace's
`remediation/foundations/`. These checks are local; final course regeneration,
source/linguistic review, genuine permissions/auditions, published dependency
pins, hosted CI and deployment remain separate release evidence.


## Analytics contract remediation — 31 October 2026

The shared head no longer silently defaults to plausible.io. It requires an explicit script source for an active domain and fails on half-configured settings. C9 (`scripts/verify_analytics.py REPO --built BUILT`) scans rendered pages for script count/source/domain and validates visible multilingual privacy notices against their small declarations. Seven adverse/positive gate tests and three scaffold tests pass; a real strict Hugo build rejected a missing source. The disabled course scaffold now emits matching configuration and notice text.

Representative strict candidate-kit builds/C9 passed for website, nsf, nvt, gfl, Scriptlibrary and the trilingual resource hub. A read-only GET of the configured self-hosted script returned HTTP 200 / application/javascript (2,586 bytes), without executing it or sending analytics events. This does not establish server retention, access control, event delivery or legal acceptance. See `docs/analytics-contract.md`; hosted CI and full integration remain separately recorded.


## Selected learner audio extraction and staged production — 31 October 2026

The audio generator now selects declared units and learner opening/Input stimuli,
excludes answer/teacher/exam/rubric content and explicitly foreign mediation
subsections, and handles the English prose/italic vocabulary conventions. A
preflight found eligible stimuli in all 396 existing units: 350 English, 510
French and 209 German segments. This is a selected listening corpus rather than
a complete spoken copy of every lesson line. Source-body digests and extraction
policy join model/configuration/speaker/backend provenance in new entries.

Nine speech/cache tests and nine authoring-safety tests pass, including missing
phoneme rejection, nested key exclusion through the shared parser, document
order, non-unit exclusion, original human-recording preservation and failed-unit
preservation. Independent review challenged and corrected same-process model
cache freshness. Optional `--persistent-model` keeps one CPU model session for
batch work; the CLI remains available and backend changes invalidate caches.
The first actual persistent-model unit produced two mono Opus clips (35.09s),
with source/transcript parity and complete FFmpeg decode checked. Full candidate
production and per-clip verification remain in progress in the external dated
workspace; native audition and source-content review remain release gates.


## Explicit release dependencies — 31 October 2026

The shared workflow caller now names the same immutable org commit in `uses` and
`org_ref`; `release-pins.json` records the actual historical kit/framework pins.
These historical pins are explicitly not the remediated release. The new org
workflow rejects absent/malformed versions, mismatched source commits and schema
bytes, and nonconforming course manifests; hubs pin dependencies without claiming
course conformance. The coordinated updater prepares exact published foundation
sets, updates consumers/checksums together and retains rollback inputs. Separate
read-only candidate CI can validate immutable pre-release commits without release
tags or deployment rights. Hosted execution and new foundation publication remain
unobserved. See the org `docs/release-pins.md`.

Four scaffold tests pass, including display-name preservation, prepared Go floor,
matching caller/module/framework/checksums and schema/digest rejection before
creating files. An explicit published release manifest avoids embedding a kit
commit hash in its own immutable source; default scaffolds stay historical.

2026-10-31 follow-up: audio vocabulary headers now select actual target terms,
including reversed bilingual and parallel target columns; rating symbols and
nested grammar paradigms are excluded. Explicit foreign ISO labels and mixed
opening labels withhold foreign-language speech and record that scope.14 content
and9 authoring-safety regressions pass. Existing staged v2 outputs/producers are
preserved; final v3 source/transcript/cache/decode verification remains a separate
candidate receipt and never constitutes native listening approval.

2026-10-31 A13 follow-up: strict support now covers the19 previously unsupported
DaF scoring formats: actual visible answer slots with per-answer rates,
horizontal point tables, additive points-first criteria, inline feedback ranges,
two decisions per item, and explicit penalty rules. Penalty keys and distractors
must partition the actual answer slots; negative totals require an explicit
zero clamp.18 regression groups pass, including independent-review false-pass
repairs. All60 actual DaF formats and168 EFL grade-scaled papers pass locally;
12 explicitly declared EFL rehearsals remain outside full-paper arithmetic.

Deliberately revised practice papers may explicitly declare
`assessment_scoring: points-only`. This mode requires unique sequential scored
task headings, an independent total, agreement with any summary table and no
remaining school-grade conversion. It never follows from missing data. The
pedagogical approval state and archived explanation of changed assessment
outcomes remain separate release requirements. FLE is being reconciled; final
inventory/check evidence follows its source freeze.


2026-10-31 final A13 follow-up: all 60 authored DaF scoring formats, 168 EFL
grade-scaled papers and all 156 FLE papers (77 retained grade-scaled, 79
explicitly declared points-only) pass the local body-based arithmetic checks.
The 12 explicitly declared EFL rehearsal pages remain outside full-paper
arithmetic. Twenty-one regression tests pass, including conflicting horizontal
maxima, overlapping/unclassified penalty distractors, localized explicit keys,
swapped task summary labels and unknown criterion task groups. Independent
review reproduced those negative cases and reran all 21 tests successfully.
FLE's 79-paper declaration inventory is bound to the final 156-unit/exam receipt
after documented exam-only whitespace/licence repairs. This verifies declared
score consistency, not native-language correctness, assessment validity or
pedagogical approval.

## Verification continuation — 2 November 2026

A fresh source copy, Python environment and `npm ci` installation passed all
nine platform CI commands locally: 148 unit tests, path fixtures, token/font/
translation/contrast checks and the strict example build. This is local evidence;
the previous hosted product runs do not establish hosted acceptance of this kit.

The final print renderer preserves Markdown-escaped punctuation, literal inline
code (including multi-backtick spans), answer gaps, authored symbols and Greek
text. Forty-two material regressions pass. Independent content checks passed all
33 first-tranche course PDFs and 120 DaF assessment PDFs, 405 pages in total,
including ordered source text, learner/key separation, live source URLs, page
bounds, compiler diagnostics and exact thumbnail pixels. Greek and functional
symbols were checked with both MuPDF and Poppler; corrected answer blanks and
Greek pages were visually inspected. These files were refreshed in the local
candidate repositories with backups. The Norwegian and Dutch draft units gained
explicit source lists for their existing inline citations, then their six PDFs
were rebuilt and their pending review hashes updated. The 60 assessment sources
remain unchanged. All 396 core unit sets (1,188 PDFs) also passed independent
final content, key, link, diagnostic, bounds and thumbnail verification; their
guarded publication has its own suite receipt.

Independent staging probes found and closed path traversal, symlink redirection,
duplicate destination and stale assessment-support reuse defects. Invalid paths
and collisions fail before generation; reused assessment workspaces must match
their recorded support files. A real two-PDF export with the new support guard
matched the previously verified document text and TeX. The material producer
binds its identity when loaded and rejects a code edit before publishing, instead
of attributing earlier execution to later source bytes. No rendering template
changed in these guards; prior verified PDF provenance is retained.

Candidate audio production now covers 396 units and 1,064 clips (350 English,
208 German, 506 French). Fresh source/transcript/provenance and full decode checks
pass, and the audition index contains a pending record for every clip. These
technical results do not replace native listening approval. The production audio
has not been replaced. Source-content, timing, mapping and educational review
gaps remain explicit in the suite handover.


## Final parser and browser review — 2 November 2026

The Hello World authoring pilot exposed a missing canonical Apply section in
print exports. Explicit step anchors now take precedence over translated or
renamed titles; legacy Produce/Apply headings remain supported. Private key,
teacher and exam anchors cannot enter learner output by a misleading heading.
Dedicated key anchors reach the teacher copy, and “Example answers” is not
misclassified as an exam. Eight regression groups and independent adverse probes
cover these boundaries. All 396 current unit sources produce byte-identical
1,188 TeX documents before/after this change: existing published PDFs and their
actual prior producer receipts remain unchanged. The revised pilot is rendered
separately and does not silently replace a published lesson.

A fresh source copy with npm installation passed all nine platform commands and
156 unit tests. Source/code checks and the strict example build pass; the
producer retains executable mode. The earlier hosted platform checkpoint
`85c338fd` passed [run 41473214190](https://github.com/boulingua/kit/actions/runs/41473214190);
that result is not a hosted claim for these subsequent edits.

Browser journeys now use declared site identity instead of checkout-folder names,
so hosted checkouts named `course` retain EFL/FLE/catalogue-specific coverage. An
actual renamed EFL checkout exercised all five pages with no findings. Full-page
light/dark scans and download hover checks wait for finite CSS transitions.
Shared badge/network ink and two consumer token rules fix observed contrast
failures. Final local runs passed all 17 noncore configured batteries (83 browser
pages); the three core batteries fail only historical-audio D6 and pass their
five-page browser journeys. The additional WCAG 2.1 A tag is included alongside
WCAG 2 A/AA and 2.1 AA; its subsequent local/hosted runs are recorded separately.

No style token or print-template change was made by these browser repairs. The
1,064 candidate audio clips remain technically verified with all review decisions
pending. Teaching-content deficits, native review, accepted mappings, classroom
timing and compatible foundation publication remain explicit release work.


## Hosted checkout identity follow-up — 2 November 2026

Hosted review checkouts are named `course`, so public counting-mark lock paths
now derive their mount prefix from Hugo's declared baseURL. Root-relative locks
remain supported; only consistently prefixed locks are normalized, using whole
path boundaries. Seven regressions preserve rejection of missing, duplicated or
wrong-page marks. Renamed copies of the current source/configuration against the
existing EFL/FLE/DaF builds pass with 370/323/68 marks respectively. Their current
locks were already root-relative; the prefixed-lock defect was reproduced in a
separate fixture. The full kit suite now passes 163 tests. No material producer,
PDF, audio or source-content bytes changed in this gate repair.

The matching org A1 validator now verifies module/site/role/origin consistency,
with explicit hub overrides and exact, retiring product compatibility copies.
Its all-consumer and renamed-checkout evidence is recorded in the suite handover.
The previous hosted kit checkpoint `8335e5f` passed
[run 41479493994](https://github.com/boulingua/kit/actions/runs/41479493994);
new hosted runs must identify this later gate revision separately.
