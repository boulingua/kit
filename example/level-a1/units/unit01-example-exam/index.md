---
# Exam is a SIBLING bundle of its unit: <unit-slug>-exam/index.md.
# It INHERITS the unit's identity (unit_nr, slug, curriculum) so it shares the
# unit's taxonomy and is discoverable, and adds exam-only fields.
title: "Unit 1 — Exam (example)"
page_type: exam
author: S. Le Boulanger
date: 2026-01-01
unit_nr: 1                      # same unit_nr as its unit → the exam↔unit link
description: "Model exam for Unit 1 — demonstrates the exam bundle schema."
tags: ["example", "exam"]
materials_status: draft

curriculum:
  framework: cefr
  cefr_level: A1
  pruefungs_module: [lesen, schreiben]

# exam-only fields:
duration_min: 45
total_points: 100
notenschluessel: "60 % to pass"
exam:
  file: /downloads/a1/unit01-example-exam.pdf
---

## Reading (40 points)

Exam tasks go here. Exams are first-class HTML pages (like EFL), with the PDF as
a download artifact under `static/downloads/<level>/`. FLE's exams — currently
stranded as `.qmd` — should be migrated into this shape.

## Writing (30 points)

...

## Listening (30 points)

Exam tasks go here. Three parts, 40 + 30 + 30 = 100, matching
`total_points` — A13 checks that sum, so an example that did not
add up would be demonstrating the failure rather than the shape.
