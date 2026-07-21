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

| Language | Voice (Piper) | Used by |
|----------|---------------|---------|
| French   | `fr_FR-siwis-medium`     | fle |
| German   | `de_DE-thorsten-medium`  | daf |
| English  | `en_GB-alba-medium`      | efl |

More languages/voices are added here as new sister sites come online. A second
voice per language enables alternating speakers in dialogues.

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
- `get_voices.sh` — downloads the openly-licensed Piper voices
- `templates/audio-block.*.html` — the per-language Hugo partial each site uses
- `AUDIO_STRUCTURE.md` — the detailed design/structure
- `requirements.txt`

## Licence

Code MIT (see `LICENSE`). Generated audio inherits each course's content licence
(CC BY / CC BY-SA); the Piper voices are used under their own openly-licensed terms.

## Use of LLM tools

Portions of this project were prepared with assistance from large language model tooling for narrowly defined, non-authorial tasks: copyediting, prose smoothing, Markdown/LaTeX formatting, scaffolding of boilerplate files (CI configs, build scripts), code refactoring. The tools used were Chat AI, the LLM service of KISSKI (GWDG), and a self-hosted Mistral Small (24B, Apache-2.0) run locally via Ollama and the ollamar R package — local inference only, with no data sent to third parties for the self-hosted model.
