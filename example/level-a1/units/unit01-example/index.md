---
# ─── CORE (every page_type) ───────────────────────────────────────────────
title: "Unit 1 — Example unit"
page_type: unit                 # unit | exam | section | appendix
author: S. Le Boulanger
date: 2026-01-01
unit_nr: 1                      # links a unit to its sibling exam (same unit_nr)
# URL + canonical slug come from the bundle DIR name (unitNN-slug); do NOT set a
# front-matter `slug:` — Hugo would use it for the URL and collide with the exam.
description: "The canonical unit bundle demonstrating the standard schema."
tags: ["example"]
materials_status: draft         # draft | ready

# ─── UNIT/EXAM fields ─────────────────────────────────────────────────────
skills_focus:                   # CEFR-skill enum (standard across all courses):
  - listening                   #   listening | reading | speaking_interaction |
  - speaking_production         #   speaking_production | writing | mediation |
topic: introductions            #   language_awareness | intercultural
presentation:
  file: /materials/presentations/unit01-example.pdf
  thumbnail: /materials/presentations/unit01-example.png
worksheet:
  file: /materials/worksheets/unit01-example.pdf
  thumbnail: /materials/worksheets/unit01-example.png
# vgwort_pixel: "https://vg09.met.vgwort.de/na/<code>"   # optional; usually in data/vgwort.yaml

# ─── POLYMORPHIC CURRICULUM BLOCK ─────────────────────────────────────────
# Choose ONE framework; fill only its fields. This replaces the old
# niveau/klassenstufe/track (Bildungsplan) vs cefr_level (CEFR) fork.
curriculum:
  framework: cefr               # cefr | bildungsplan-bw
  # cefr:
  cefr_level: A1
  cefr_can_do:
    - "I can introduce myself and ask simple personal questions."
  pruefungs_module: [sprechen]
  # bildungsplan-bw (use instead of the cefr:* fields above):
  # niveau: E
  # klassenstufe: 5
  # track: e
  # codes: ["3.1.1.1"]
---

## 1. Objectives

State what learners will be able to do by the end of the unit (mirror
`cefr_can_do`). This is the standard five-move unit body.

## 2. Input

Present the model text / dialogue / vocabulary. Keep quoted material original or
public-domain/CC-licensed (see the copyright policy in `LEGAL.md`).

## 3. Practise

Guided tasks that rehearse the target language.

## 4. Produce

The main output task. This is what differentiation (support/extension) scaffolds.

## 5. Reflect

Learners self-assess against the can-do statements.

## Target-language runs

An inline run — {{< tl >}}Guten Morgen{{< /tl >}} — carries its own `lang`,
so a screen reader switches voice and the spellchecker stops underlining it.

{{< tl block >}}
Ein ganzer Absatz in der Zielsprache steht als eigener Block.
{{< /tl >}}

An explicit override for a citation: {{< tl lang="grc" >}}μῆνιν ἄειδε{{< /tl >}}.
