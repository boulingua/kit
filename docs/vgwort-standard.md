# VG Wort Zählmarken — implementation standard

This is the **binding standard** for how every boulingua language course embeds
VG Wort METIS counting pixels ("Zählmarken"). Follow it exactly; the reference
implementation lives in this template (`pagegen`) and is copied verbatim into
each course.

## 1. Why, and the governing principle

A VG Wort Zählmarke is a 1×1 counting pixel that lets VG Wort record how often a
text ("Sprachwerk") is read, which feeds the author's **statutory remuneration**
(*gesetzlicher Vergütungsanspruch*). The counting pixel is therefore **not**
tracking or advertising — it serves the author's legal right.

**Governing principle:** the pixel must load for **every** reader, **immediately**
on page open, and **must not be restricted by any user setting** (cookie consent,
scroll position, lazy-loading, ad/tracking filters). It is emitted as a static,
JavaScript-free resource with **no consent gate**.

## 2. What may carry a Zählmarke

Register a mark on a page **only** if it is:

- an original **creative text** authored for the course (units, exams,
  appendices such as glossaries/assessment grids, about/course-overview prose), and
- **≥ 1800 characters** of rendered prose (VG Wort *Mindestumfang*).

**Never** register a mark on:

- navigation surfaces — the home page, the materials hub (`/materials/`,
  `/materiel/`, …), tag/category indexes;
- paginated continuations (`/page/2/` …);
- **templated legal pages** — Impressum, Datenschutz, Haftungsausschluss (these
  are not the author's creative Sprachwerke).

Exactly **one** Zählmarke per work, on **exactly one URL**.

## 3. Where marks come from and how they are stored

Public codes ("Öffentlicher Identifikationscode", a 32-hex token) are drawn per
work from the author's VG Wort **T.O.M.** account. They are served from
`https://vg09.met.vgwort.de/na/<code>`. Never invent codes; never expose the
**private** identification code anywhere in the site.

A page's mark is resolved, in order:

1. per-page front matter — `vgwort_pixel: "<full URL or bare code>"`; or
2. an entry in `data/vgwort.yaml`, matched by **`url:`** (the page's
   base-stripped `RelPermalink`) **or** **`path:`** (`content/<File.Path>`), with
   the token in `pixel_url`, `public_id`, or `token`.

```yaml
# data/vgwort.yaml
- url: /about/                       # or:  path: content/kurs_a1/units/unit01_x.md
  public_id: 00099581191e497bab13be8907d95a52
  pixel_url: https://vg09.met.vgwort.de/na/00099581191e497bab13be8907d95a52
  min_chars: 1800
  author: S. Le Boulanger
  registered_at: '2026-07-22'
```

## 4. The single source of truth: the resolver partial

All rendering goes through **one** partial, `layouts/_partials/vgwort/url.html`,
which returns a page's pixel URL or `""`. It performs the lookup in §3 and
returns `""` for paginated continuations, so the `<head>` preload and the body
`<img>` can never disagree, and each mark maps to one URL. Do not duplicate this
logic anywhere else.

## 5. Delivery: preload in `<head>` + eager `<img>` in `<body>`

Two mechanisms, both driven by the resolver, emitted on **every** page via
`head/extensions.html` and `body/extensions.html` (which `baseof` renders for
every template — coverage never depends on a specific single/list template):

**a) `<head>` — resource preload (fires the request during head parsing):**

```html
{{- with (partial "vgwort/url.html" .) }}
<link rel="preload" as="image" href="{{ . | safeURL }}" fetchpriority="high">
{{- end }}
```

**b) `<body>` — the canonical METIS pixel:**

```html
{{- with (partial "vgwort/url.html" .) -}}
<div style="display:inline"><img src="{{ . | safeURL }}" width="1" height="1" alt=""
  loading="eager" fetchpriority="high" decoding="async" referrerpolicy="no-referrer"
  aria-hidden="true"
  style="position:absolute!important;width:1px;height:1px;left:-9999px;top:auto;visibility:hidden" /></div>
{{- end -}}
```

The preload starts the fetch before the body renders (no scroll, no lazy). The
`<img>` **reuses** the preloaded resource, so VG Wort's server receives **exactly
one** GET per page view — no double-counting.

### Hard rules (why each matters)

- **`loading="eager"`, never `lazy`** — a lazy pixel below the fold would not
  fire until scrolled into view and would undercount reads.
- **Hide with `visibility:hidden` / off-screen, never `display:none`** —
  `display:none` (on the image or any ancestor) can suppress the fetch.
- **No JavaScript, no consent gate** — JS-injected pixels can be blocked or fail;
  a static `<img>`/`<link>` always loads. The mark is the author's statutory
  right and is emitted unconditionally.
- **Plain `met.vgwort.de` request** — do not proxy it (VG Wort must receive the
  request directly). Exclude `vgwort.de` from link-checkers (see §7) so the marks
  are not hammered and the Datenschutz link to `www.vgwort.de` does not flake CI.
- **One mark per URL** — the resolver's pagination guard enforces this.

## 6. CI gates (must all be present)

- **Coverage audit** (warning, non-blocking): walks rendered `public/**`, and for
  every editorial page ≥ 1800 chars **without** a mark emits a `::warning::`.
  Registration is asynchronous (codes come from T.O.M.), so this warns, never
  fails — it keeps unregistered long-form content visible in the build log.
- **Render verify** (blocking): every registered `pixel_url` appears in the
  rendered output, on its page, on exactly one page site-wide. Because §5 emits
  the token twice per page (preload + img), a page-level uniqueness check is used,
  not a per-page single-occurrence check.
- **Hub guard** (blocking): assert `met.vgwort.de` is **absent** from the
  materials hub page — the pixel must never fire on navigation.

## 7. Link-checkers and privacy

- Exclude the whole `vgwort.de` domain from `lychee`/link-checks:
  `'^https?://([a-z0-9-]+\.)*vgwort\.de'`.
- The pixel sets **no cookie**, sends **no personal data**, and uses
  `referrerpolicy="no-referrer"`. Disclose it in `/datenschutz/` as VG Wort METIS
  counting on the legal basis of the author's statutory remuneration right; it is
  **exempt from consent gating**.

## 8. The usage registry (record-keeping)

Maintain a registry mapping every public code to its usage: `Used`, `Projekt`
(efl/fle/daf/…), `Sprache`, `Niveau (GER)`, `Kurstitel`, `URL`, `Pixel_URL`.
This is the authoritative record of which mark is on which page and which codes
remain free. Keep it **outside** the published repos (it is private author data)
— e.g. in the local VG Wort working directory, never in `content/` or `static/`.

## 9. Adding a course / a new unit — checklist

1. Draw enough public codes from T.O.M. for the new works.
2. Add each to `data/vgwort.yaml` (by `url:` or `path:`) or the unit's
   `vgwort_pixel:` front matter.
3. Build; confirm the coverage audit shows **0** unregistered editorial pages
   (legal pages excepted) and the render verify passes.
4. Record each mark in the usage registry (§8).
5. Never reuse a code already assigned to another page.
