# Voice provenance and attribution

The registry in `voices.yml` records candidate models and their upstream dataset
licence statements at a pinned model-repository revision. Candidates are not
approved teaching voices. Existing clips require their own model provenance;
changing the registry does not retrospectively identify old recordings.

As a project distribution policy, only models whose recorded terms meet the
registry's allowlist may enter the audition pipeline. We preserve the upstream
model card, source URL and file hashes with each preview, including for models
whose cards say CC0 or public domain. This is an evidence and attribution policy,
not a claim that every model's training-data licence automatically determines
the copyright status or licence of every synthesized output.

The current attribution-bearing candidates are:

| Courses | Models | Dataset identified by upstream | Recorded licence |
|---|---|---|---|
| French, German, Dutch | `fr_FR-mls-medium`, `de_DE-mls-medium`, `nl_NL-mls-medium` | [Multilingual LibriSpeech](https://openslr.org/94/) | CC BY 4.0 |
| Italian | `it_IT-serena-medium` | [Serena synthetic Italian dataset](https://huggingface.co/datasets/committa/serena-synthetic-it-27h) | CC BY 4.0 |

The generated preview directory contains a copy of each selected model card.
Retain it and the receipt when distributing recordings. The content transcript
and the synthesis/model provenance are separate records.

Historical attribution for `en_GB-alba-medium` (CSTR Edinburgh, CC BY 4.0) and
`fr_FR-siwis-medium` (SIWIS, CC BY 4.0) must be retained where recordings actually
use those models. Neither is the current selected candidate. Unidentified
historical clips must be resolved or replaced before a provenance-complete release.

Arabic, Japanese, Latin and Turkish currently have no selected model. See each
registry row for the dated decision and candidate limitations. Human recordings
with documented permission remain an alternative; a neighbouring language's
voice is not an acceptable substitute for pronunciation instruction.
