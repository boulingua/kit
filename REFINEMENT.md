# Refinement record — 30 October 2026

This is a local engineering candidate on `refine/2026-10-30`. No hosted CI,
published release or production deployment of these changes has been observed.
The suite strategy and integration order live in the organisation repository,
`docs/refinement-2026-10-30.md` and `docs/release-candidate-2026-10-30.md`.

## Findings and changes

- High: gates could validate missing artifacts or the wrong repository. The CLI now distinguishes repository and build-root arguments; search, translations, path, font, token, catalogue and actual browser checks exercise their claimed inputs.
- High: audio and material generation could leave partial or stale outputs. Audio staging preserves existing and human recordings on failure; model/configuration digests and speaker identity invalidate the cache. PDF outputs publish only after both documents compile and thumbnails render; stale intermediate PDFs and missing glyphs fail.
- High: print extraction truncated vocabulary and multi-paragraph tasks, discarded differentiation, flattened exercise structure and mixed exam answers into lesson keys. Full task blocks, criteria tables, authored numbering and lesson-only answers now survive. Answer headings follow the course language. U+2B51 differentiation marks use a vector star with PDF ActualText because Source Sans 3 lacks that glyph.
- High: menu focus, project-prefix links, contrast, small text and missing landmarks affected real use. Shared templates now provide native disclosures, skip navigation, labelled checkboxes and corrected design tokens. Browser checks cover searches, downloads, mobile navigation and no-JavaScript content.
- Medium: graph libraries loaded before use and budget checks did not inspect real output. Discovery loads graph code on request; C15 checks eager and lazy assets and distinguishes explicitly configured telemetry.
- Medium: scaffolds and material synchronisation lacked safe first-use behaviour. Development-course generation creates coherent manifests, licence notices and legal pages; sync refuses locally edited or unknown files before writing anything.

## Validation and limits

Python regression suite: 40 tests passed, including failure paths, task preservation and instruction-language selection. All 18 course material trees synchronised successfully, including an idempotence/protected-edit test. Parser dry run: 180 EFL, 156 FLE and 60 DaF units, no parsing exceptions. XeLaTeX 2026 compiled and visually reviewed one slide deck and worksheet per established course. This is not a full-corpus print or pedagogical review; the 852 committed course PDFs were preserved.

The minimal generated example built with strict Hugo checks. Current source checks passed for token generation, token use, fonts, translations, contrast and material paths. All 15 development courses passed the full local gate battery. Established courses expose historical audio failures instead of hiding them. Browser checks are representative WCAG 2.1 AA automation, not complete manual accessibility certification.

The local voice audit produced 42 decodable WAV previews for 14 candidates with pinned model/config/card digests. A disposable real unit produced two Opus clips and a repeat run synthesised none. Listener approval remains pending; missing historical metadata cannot be inferred from a new voice model.

## Acceptance and next milestone

The engineering candidate can be installed and exercised using README.md and audio/README.md. Release the kit only after review of its diff, recorded dependency audit and a passing hosted equivalent of its local checks. Coordinate the organisation workflow and consumer pins as one release set. Native listener approval, curriculum-source repair, course authoring and full regenerated-material review remain separate acceptance criteria.
