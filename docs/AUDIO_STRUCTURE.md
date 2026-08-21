# Boulingua audio (TTS) — comprehensive structure & flow

## Goal
Every unit's spoken content — vocabulary, dialogues, reading texts, key phrases —
is available as **native-voice audio**, generated locally from openly-licensed
voices, in the **open OGG/Opus** format, always paired with its written text
(shown on the page; long texts also downloadable as a transcript PDF).

## Voices (Piper TTS — MIT; voices openly licensed, native speakers)
- **FR (FLE):** fr_FR-siwis-medium (native FR, female) [+ fr_FR-upmc for a 2nd voice]
- **DE (DaF):** de_DE-thorsten-medium (native DE, male) [+ de_DE-kerstin for a 2nd voice]
- **EN (EFL):** en_GB-alba-medium (native GB, female) [+ en_GB-northern_english_male]
Different voices per language give variety; dialogues can alternate speaker voices.

## File layout (committed — CI cannot run Piper)
```
<repo>/static/materials/audio/<unit-slug>/
    vocab.ogg          # the target-language column of every vocab table, read with pauses
    dialogue1.ogg …    # each dialogue (speaker lines), voices may alternate
    texte1.ogg …       # each reading text / Hörtext / Text
    phrases.ogg        # key phrases block (if present)
<repo>/data/audio/<unit-slug>.json   # manifest: [{file,label,transcript}]
```
Format: **OGG/Opus** 48 kbit/s mono (open, tiny, universal `<audio>` support).

## Generation flow (build_audio.py — local, LLM-free)
1. Walk every "ready" unit .md.
2. Parse markdown → segments:
   - **vocab**: first column of each `| … | … |` table (the target-language term)
   - **dialogues**: blockquotes containing `**Name :**` speaker markers → spoken lines
   - **textes**: blockquotes without speaker markers, ≥ ~120 chars (reading texts)
3. Synthesize each segment (Piper, unit's language voice) → WAV → ffmpeg → OGG.
4. Write `<unit>.json` manifest (file, human label, transcript text).
Idempotent; skips unchanged segments (hash of text).

## Page integration (no per-unit editing)
A Hugo partial `audio-block.html`, called from the unit layout, reads
`data/audio/<slug>.json` and renders an **« Écouter » / « Anhören » / « Listen »**
section: one `<audio controls>` per segment with its transcript shown beneath
(or a `<details>`/collapsible for long texts). Degrades gracefully when no audio
exists yet. Fully keyboard-accessible; transcripts satisfy a11y (audio + text).

## Downloadable transcript (long texts)
For units whose combined spoken text exceeds a threshold, the worksheet PDF gains
a **« Transcriptions audio »** appendix so learners have the full spoken text offline.

## Coverage plan
Generate for all completed units first (DaF 60, FLE done), then each new content
wave includes audio generation as a pipeline step (author → materials → **audio** →
gates → push).
