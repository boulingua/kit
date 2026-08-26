# Voice audition — <code>

Copy to `<code>.md`, listen, fill in, commit. Gate 3 reads the verdict, the
listener and the date, and refuses `status: ready` without all three.

**Why a human has to do this.** Whether a synthetic voice is good enough to put
in front of a child learning to pronounce a language is not a property of the
model file. A voice can be technically correct and still teach a wrong vowel
length, flatten a pitch accent, or read a set phrase in a register no speaker
would use to a stranger. None of that shows up in a licence or a checksum.

---

voice: <piper_key>
model_url: <the resolve/ URL the model was fetched from>
listener: <name — the person who actually listened>
date: <YYYY-MM-DD>
verdict: <pass | fail | hold>

## What was listened to

At least one sample from each: a two-turn dialogue, a vocabulary list, and a
continuous text of 60+ words. A voice that handles isolated words well and
falls apart across a sentence is common, and a vocabulary-only audition misses
it entirely.

## Findings

**Segmental accuracy.** Vowels and consonants correct for the taught variety?
Name the variety — a Bokmål course auditioned on a Nynorsk-leaning voice is a
fail even if the audio is clean.

**Prosody.** Sentence stress, question intonation, and for tonal or
pitch-accent languages whether the distinction is audible at all.

**Register.** Set phrases at the politeness level the unit teaches. A greeting
read too casually teaches the wrong thing more effectively than silence.

**Artefacts.** Clicks, truncation, mispronounced loanwords and proper nouns.

## Verdict reasoning

One paragraph. A `hold` is a legitimate outcome and more useful than a
reluctant `pass`: it says the voice is close and names what would settle it.
