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

## `curriculum:` — one framework, zero or more anchors

```yaml
curriculum:
  framework: boulingua-curriculum       # const — not a choice
  level: B1
  implements:                           # REQUIRED on unit and exam, 3-6 entries
    - B1.INT.conversation.02
    - B1.REC.reading-for-information-and-argument.01
  can_do:                               # optional, bound to an id
    - { id: B1.INT.conversation.02, text: "Ich kann ..." }
  bildungsplan:                         # efl and fle only
    plan: bw-2016-englisch
    niveau: E
    klassenstufe: 9
    track: e
    codes: ["3.2.3.2", "3.2.3.3"]
    topic_codes: ["3.2.1"]              # Orientierungswissen; no CEFR counterpart
```

**Why this replaced `framework: cefr | bildungsplan-bw`.** That enum modelled
the two as alternatives. They are orthogonal: the Bildungsplan is a *state
syllabus*, the boulingua curriculum is a *descriptor catalogue*. efl and fle
need both at once — and the schema made them choose, so they chose the one
their Ministry asks about. That is exactly why both carry a `bildungsplan:`
block and, between them, zero CEFR ids.

One framework, then, and any number of secondary anchors (ADR-0012).

### `implements` is required, and it is the whole point

Before it, a course could declare any conformance level and nothing could
contradict the claim. It cannot be generated: the value of the field is that a
human asserted the mapping, and a script that guessed would manufacture a claim
nobody made. `conformance_audit.py suggest --level L --domain D` ranks
candidates from the page's own `skills_focus` and Bildungsplan codes, so the
author confirms rather than searches.

**At least one id must come from a domain other than the page's primary skill
domain.** A unit implementing only `REC.*` descriptors is a reading exercise
wearing a unit's clothes.

### The requirement ramps, and the ramp is declared

Zero pages carry an id today, and for efl and fle there is no field to rename —
roughly 672 pages need 3-6 ids each, which is about 14 author-weeks. Requiring
it on the day the schema lands would red two live sites for months. So
`milestone:` in `boulingua.yml` sets the level: **M0** warns, **M1** requires it
on pages a PR touches, **M2** requires it repo-wide, **M3** adds coverage.

A declared state rather than a per-PR judgement, because "we will turn it on
when we are ready" is how a gate never gets turned on. Changing `milestone` is
a diff somebody signs.

An id that is *present* must be correct at every milestone. Only the
*requirement* ramps.

### `skills_focus`

Eight values, English: `reading` `listening` `speaking_interaction`
`speaking_production` `writing` `mediation` `language_awareness`
`intercultural`.

`speaking` is not among them, deliberately. Whether a unit's speaking is
interaction or production is read from its `implements` — an `INT.*` id implies
interaction, `PROD.*` production — so that split lands *after* the unit's ids,
never before. It is the one place where descriptor ids drive a migration
instead of following it.

### Bildungsplan codes must not be mirrored into `tags:`

efl does this today: 816 of its 1,356 tag occurrences are numeric syllabus
codes, producing taxonomy terms like `/tags/3-2-3-7/`. A syllabus reference is
not a topic a learner browses by.
