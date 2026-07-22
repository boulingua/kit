# pagegen — the boulingua course template

**pagegen is the canonical template every boulingua language course follows.**
It is a complete, buildable Hugo course (hugo-coder theme) condensing the best of
the `efl`, `fle` and `daf` repos into one standard: the same layout, content
model, design system, gates and legal scaffold. Copy it to start a new language;
existing courses are aligned to it over time.

```bash
hugo server              # run the demo course locally
hugo new content/level-a2/units/unit01-greetings/index.md --kind unit
```

## What the standard fixes

- **Layout & config** — one templated `hugo.toml` (shared markup/pagination/ToC,
  `navTitle` brand, robots + `hideCredits`, Plausible block kept *last* to avoid
  the TOML sub-table trap, declared `[taxonomies]`); one `go.mod` pinning
  hugo-coder; no module mounts; `public/` never tracked.
- **Content model** — page bundles under `content/<course>/units/<unitNN-slug>/`,
  exams as **first-class** sibling bundles (`…-exam/`), section landings via
  shortcodes (never raw HTML), one superset front-matter schema with a
  polymorphic `curriculum` block. See [`docs/front-matter-fields.md`](docs/front-matter-fields.md).
- **Design system** — per-language flag-safe accent colour + pentagon icon,
  driven entirely by `data/accents.yaml` keyed by the site `code`; a new course
  sets `code` and never edits CSS. Regenerate the icon with `brand/make_icon.py`.
- **VG Wort** — the shared resolver + `<head>` preload + eager body pixel, so the
  author's statutory counting marks always load, immediately, for every reader.
  This is a binding standard — see [`docs/vgwort-standard.md`](docs/vgwort-standard.md).
- **Materials & audio** — generated locally from the branded `slidegen`/`sheetgen`
  LaTeX templates and Piper voices, **committed** under `static/materials` +
  `static/downloads`; CI only verifies (no TeX Live in the deploy path).
- **Gates & CI** — one `scripts/` set + one `build-deploy.yml` running the gate
  battery (VG Wort coverage/render, legal placeholders, downloads, attribution,
  …), then GitHub Pages deploy.
- **Legal** — `impressum` / `datenschutz` / `haftungsausschluss` with ⟨…⟩
  placeholders a course fills; MIT code + CC BY-SA 4.0 content.

## Instantiating a new course

1. Copy this repo to `boulingua/<code>` (e.g. `boulingua/ele` for Spanish).
2. In `hugo.toml` change the marked values: `baseURL`, `title`, `languageCode`,
   `defaultContentLanguage`, `navTitle`, `description`, `keywords`, the social
   repo URL, `params.plausible.domain`, `params.code`, and the `[[menu.main]]`
   sections.
3. Confirm `data/accents.yaml` has the language's `code` (all 17 planned
   languages are already listed); run `python brand/make_icon.py` to regenerate
   the pentagon + favicons.
4. Fill the ⟨…⟩ placeholders in the three legal pages.
5. Author units with `hugo new … --kind unit` / `--kind exam`; generate + commit
   materials and audio.
6. Draw VG Wort codes from T.O.M. and register them per
   [`docs/vgwort-standard.md`](docs/vgwort-standard.md).

## Use of LLM tools

This project uses large language model (LLM) tools to assist with drafting,
refactoring and review. All content is authored and reviewed by S. Le Boulanger;
quoted material is limited to public-domain or openly-licensed sources.

## Licence

Code: [MIT](LICENSE). Content: [CC BY-SA 4.0](LICENSE-CONTENT.md).
