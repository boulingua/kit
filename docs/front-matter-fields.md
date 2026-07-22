# Front-matter standard

Every course page declares a `page_type` and follows the superset schema below.
Fill only the fields relevant to the type. See the worked examples in
`content/level-a1/`.

## Content model

```
content/
  <course>/                     # one flat key: level-a1, e-kl05, gm-kl06 …
    _index.md                   # page_type: section  (shortcode landing)
    units/
      <unitNN-slug>/index.md    # page_type: unit     (leaf bundle; DIR = URL)
      <unitNN-slug>-exam/index.md  # page_type: exam  (sibling bundle)
  appendices/
    <slug>/index.md             # page_type: appendix
  impressum.md · datenschutz.md · haftungsausschluss.md · about/index.md
```

The bundle **directory name** is the canonical slug and the URL — do **not** set
a front-matter `slug:` (Hugo would use it for the URL and collide the exam with
its unit). A unit and its exam are linked by a shared `unit_nr`.

## Fields

| Field | Types | Notes |
|---|---|---|
| `page_type` | all | `unit` \| `exam` \| `section` \| `appendix` (discriminator) |
| `title` | all | |
| `author` | all | `S. Le Boulanger` |
| `date` | all | `YYYY-MM-DD` |
| `description` | all | used for `<meta>` + list leads |
| `unit_nr` | unit, exam | links a unit to its sibling exam |
| `tags` | all | derive from structured fields where possible |
| `materials_status` | unit, exam | `draft` \| `ready` |
| `skills_focus` | unit, exam | CEFR-skill enum (below) |
| `topic` | unit, exam | discovery/topic key |
| `presentation` / `worksheet` | unit | `{ file, thumbnail }` |
| `exam` | exam | `{ file }` — PDF under `static/downloads/<level>/` |
| `duration_min` / `total_points` / `notenschluessel` | exam | exam-only |
| `curriculum` | unit, exam | polymorphic block (below) |
| `vgwort_pixel` | any | optional; usually registered in `data/vgwort.yaml` |

### `skills_focus` enum (standard across all courses)

`listening` · `reading` · `speaking_interaction` · `speaking_production` ·
`writing` · `mediation` · `language_awareness` · `intercultural`

### Polymorphic `curriculum` block

Choose one `framework`; fill only its fields.

```yaml
curriculum:
  framework: cefr            # CEFR-organised courses (e.g. DaF)
  cefr_level: B1
  cefr_can_do: ["…"]
  pruefungs_module: [lesen]
# — or —
  framework: bildungsplan-bw # school-year courses (e.g. EFL/FLE)
  niveau: E                  # E | M | G
  klassenstufe: 6
  track: e
  codes: ["3.1.3.2"]
```

This replaces the old `niveau`/`klassenstufe`/`track` vs `cefr_level` fork with
one schema, so EFL/FLE keep Bildungsplan codes and DaF keeps CEFR can-do
statements without three divergent schemas.
