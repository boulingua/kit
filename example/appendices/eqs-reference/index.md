---
title: "EQS shortcode reference"
page_type: appendix
description: "Every teaching shortcode the educational standard is written against, rendered once."
material_slug: "appendix_eqs-reference"
unit_slug: "eqs-reference"
---

Every shortcode EQS-1 is written against, exercised once. This page exists so
`--panicOnWarning` is a real test of them: a shortcode that is never rendered is
a shortcode nobody knows is broken.

## Vocabulary

{{< vocab >}}
der Bahnhof | station | Wir treffen uns am Bahnhof.
die Fahrkarte | ticket | Ich kaufe eine Fahrkarte am Automaten.
umsteigen | to change trains | In Hannover müssen wir umsteigen.
die Verspätung | delay | Der Zug hat zwanzig Minuten Verspätung.
{{< /vocab >}}

Each column carries its own `lang`, so a screen reader switches voice between
the term and its gloss instead of reading French words with German phonology.

## Differentiation

{{< niveau G >}}
Ordne die Wörter den Bildern zu.
{{< /niveau >}}

{{< niveau E >}}
Schreibe eine Reiseauskunft für einen Mitschüler, der zum ersten Mal allein fährt.
{{< /niveau >}}

The letter is text, not a coloured chip: colour alone is not an affordance, and
these sheets are photocopied.

## Cloze

Ich fahre mit dem {{< gap len="10" >}} nach Berlin und muss in Hannover
{{< gap len="9" hint="Verb" >}}.

Each blank carries an `aria-label`. An empty span with a border is read as a
sentence with a word missing, and the learner never learns a task was there.

## Spaced retrieval

{{< recycles unit="example-unit" label="Unit 1 — the example unit" >}}

Resolved through the editorial `unit_slug`, never a hand-written URL.

## Extension

{{< extension title="Weiterdenken" >}}
Vergleiche die Fahrpläne zweier Städte und begründe, welche Verbindung du wählst.
{{< /extension >}}

## Target-language runs

An inline run — {{< tl >}}Guten Morgen{{< /tl >}} — and a block:

{{< tl block >}}
Der Zug nach Berlin fährt von Gleis 7 ab.
{{< /tl >}}
