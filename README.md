# audiogen

Audio-generation workflow for the [boulingua](https://github.com/boulingua)
multilingual teaching platform. It turns each course unit's spoken content —
vocabulary, dialogues, reading texts — into **native-voice audio**, generated
locally from **openly-licensed** voices and delivered in the open **OGG/Opus**
format, always paired with its written transcript on the unit page.

## Why local, openly-licensed TTS

- **Openly licensed:** [Piper TTS](https://github.com/rhasspy/piper) (MIT) with
  voices from [rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices)
  — native speakers, redistributable.
- **Local inference only:** no per-request cloud calls, no learner data sent
  anywhere; audio is generated once, ahead of time, and committed to each site.
- **Open format:** OGG/Opus (48 kbit/s mono) via `ffmpeg` — tiny and universally
  supported by the HTML5 `<audio>` element.

## Voices

`voices.yml` is the single source of truth: one row per boulingua language
code, carrying the exact upstream Piper key, its quality tier, its speaker
count, its licence verbatim from the model card, and the other voices
available for that language. Voice IDs are written nowhere else — not in this
table, not in a ROADMAP, not in `get_voices.sh`, which reads the registry
rather than carrying a list of its own. A second voice per language, where the
registry records one, enables alternating speakers in dialogues.

**The licence rule.** Course content ships under CC BY-SA 4.0, and audio
synthesised from a Piper model inherits the licence of that model's training
dataset. A NonCommercial voice therefore cannot go into a unit at all, and a
voice whose dataset licence is unstated cannot be shipped safely either — no
statement is not permission. Each row records the judgement as `licence_ok:`,
and `get_voices.sh` downloads only rows that are both `status: ready` and
`licence_ok: true`, checking the licence before it fetches a single byte. Of
the eighteen languages, fourteen have an openly-licensed voice; Arabic,
Japanese, Turkish and Latin do not, and those courses ship transcript-only
until one appears.

## Flow

```
unit .md ──parse──▶ segments (vocab · dialogues · texts)
         ──Piper──▶ WAV ──ffmpeg──▶ OGG/Opus
         ──────────▶ static/materials/audio/<unit>/<segment>.ogg
         ──────────▶ data/audio/<unit>.json   (file · label · transcript)
```
The unit layout renders a **« Écouter » / „Hören" / "Listen"** section from the
manifest: one accessible `<audio>` player per segment with its transcript shown
beneath (audio **and** text, for accessibility).

## Usage

```bash
pip install -r requirements.txt        # piper-tts
sudo apt-get install -y ffmpeg          # OGG/Opus encoder
./get_voices.sh                         # download the openly-licensed voices

# generate audio for a target site (only enriched units — those with an .odp deck)
python build_audio.py /path/to/daf voices/de_DE-thorsten-medium.onnx de 'content/kurs_*/units/*.md'
python build_audio.py /path/to/fle voices/fr_FR-siwis-medium.onnx  fr 'content/track_*/units/*.md'
```

Idempotent: a segment is re-synthesized only when its text (or voice) changes.
CI does not run TTS — the generated `.ogg` files and manifests are committed
with each content change; this repo is the canonical source of the tooling.

## Files

- `build_audio.py` — extraction + synthesis + manifest generator (the workflow)
- `voices.yml` — the voice registry: one row per language code, with the
  upstream key, licence and status (the single source of truth for voice IDs)
- `get_voices.sh` — downloads the openly-licensed Piper voices named in `voices.yml`
- `templates/audio-block.*.html` — the per-language Hugo partial each site uses
- `AUDIO_STRUCTURE.md` — the detailed design/structure
- `requirements.txt`

## Licence

Code MIT (see `LICENSE`). Generated audio inherits each course's content licence
(CC BY / CC BY-SA); the Piper voices are used under their own openly-licensed terms.

## Use of LLM tools

Portions of this project were prepared with assistance from large language model tooling for narrowly defined, non-authorial tasks: copyediting, prose smoothing, Markdown/LaTeX formatting, scaffolding of boilerplate files (CI configs, build scripts), code refactoring. The tools used were Chat AI, the LLM service of KISSKI (GWDG), and a self-hosted Mistral Small (24B, Apache-2.0) run locally via Ollama and the ollamar R package — local inference only, with no data sent to third parties for the self-hosted model.
