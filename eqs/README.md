# Teaching structure

`step-map.yml` mirrors the canonical `curriculum/standards/step-map.yml` in the
coordinated framework release. Change the canonical file first and copy it here
in the same release increment. A12 checks that these declarations agree.

Units declare the five ordered `steps` and explicit heading anchors. The heading
render hook emits their exact `anchor_aliases` from front matter; the downloads
anchor belongs to the shared download section and is emitted once. Localized
visible headings are retained. `details` accepts `title` and `summary`, and answer
keys carry `data-role="key"` for learner/teacher output separation.

Run `python scripts/verify_eqs_structure.py COURSE --report evidence.json` with
`BLG_CURRICULUM` pointing to the framework checkout. Use `--include-drafts` and
`--built PATH` with a Hugo `--buildDrafts` review build to inspect unpublished
content. The report measures actual source and rendered assessment content;
missing review decisions and content budgets remain findings.
