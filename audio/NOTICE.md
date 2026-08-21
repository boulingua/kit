# Voice attribution

Piper voice models used to synthesise the audio in these courses, and the
attribution their licences require.

Audio synthesised from a model inherits the licence of that model's training
dataset. A CC BY or CC BY-SA voice therefore places an attribution obligation
on every clip generated from it — an obligation none of these were carrying,
because nothing recorded which voices needed one.

CC0 and public-domain voices impose no obligation and are not listed. The full
registry, including the voices rejected on licence grounds and why, is
`audio/voices.yml`.

| Course | Model | Licence | Source |
|---|---|---|---|
| `efl` | `en_GB-alba-medium` | https://creativecommons.org/licenses/by/4.0/ | [rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alba/medium) |
| `fle` | `fr_FR-siwis-medium` | CC-BY 4.0 | [rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium) |
| `ils` | `it_IT-serena-medium` | CC-BY-4.0 | [rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices/resolve/main/it/it_IT/serena/medium) |

## Not used, and why

Four courses ship transcript-only. This is a licence outcome, not a quality
one, and in three of the four the language has exactly one voice in the entire
catalogue:

- **afl** — ar_JO-kareem MODEL_CARD says 'License: See URL' and the URL carries no licence statement. The ROADMAP called it 'MIT-compatible OFL data' — wrong twice: no statement is not permission, and OFL is a font licence with no application to a speech dataset. Gated pending a written determination.
- **jfl** — ja_JA-hi_fi_captain-medium is the only Japanese voice and is CC BY-NC-SA 4.0. Note the catalogue tag is ja_JA, not the ja_JP written in the ROADMAP. Transcript-only.
- **lle** — No Latin voice exists upstream — 0 of 174. Approximating with an Italian or Spanish voice is rejected: never a neighbouring language's voice.
- **tfl** — tr_TR-dfki-medium is the only Turkish voice in the catalogue and is CC BY-NC-SA 4.0. A NonCommercial model cannot ship inside CC BY-SA 4.0 content. Transcript-only; the blocker is licence, not quality.
