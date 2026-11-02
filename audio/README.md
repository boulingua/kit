# Voice previews and course recordings

Previews can be generated on this machine with Piper. Human recordings are also
supported by course manifests using `source: human`; synthesis preserves them.
The selected model registry contains 14 candidates and four courses with no
selected model. No candidate becomes approved merely because it produces audio.

## Generate an audition

Use Python 3.12. From the kit checkout:

```sh
python3.12 -m venv .audio-venv
. .audio-venv/bin/activate
python -m pip install -r audio/requirements.txt
python bin/kit audio audition --code fle --models "$HOME/.cache/boulingua/voices" --output build/voice-previews
python audio/preview_index.py build/voice-previews
```

For Mandarin, additionally install `audio/requirements-zh.txt`. Its phonemizer
also downloads its own resources into the model cache on first use. Initial
model downloads need an internet connection; the listening page works offline.
Models and WAV previews are local artifacts, excluded from source commits.

Open `build/voice-previews/index.html`. Each course has a dialogue, vocabulary
list, continuous reading, original transcripts, an upstream model card, a
machine-readable receipt and a listening sheet. The registry pins one upstream
revision and publishes expected checksums for model/config/card files. Receipts
record SHA-256 hashes, speaker ID, Piper version and measured audio properties.

Use `--speaker NUMBER` to audition a different speaker of a multi-speaker model.
Use a separate output directory for comparisons. A pre-existing listening sheet
is never overwritten; confirm its identity fields match the new receipt.

The Ukrainian character model requires lowercase speech input and ASCII
apostrophes. The receipt records normalized speech input separately; learner
transcripts retain the original spelling. Missing phonemes, empty audio and
excessive clipping fail generation instead of being treated as successful output.

## Review and release

A competent listener reviews the texts and all three samples. Record the actual
listener, date, verdict, model/config hashes, speaker and findings in
`audio/auditions/CODE.md`, retaining the matching receipt and reviewed samples.
The release gate matches recording identity to that review. A held or failed
review remains a release finding. Change registry status to `ready` only after
review; do not fabricate an approval to make a gate pass.

Human recordings need an accurate transcript and documented provenance and
permission. Keep the source recording; encode a mono OGG derivative at no more
than 64 kb/s for course delivery. The course manifest identifies it as human,
not as a synthesis-model output.

Each human manifest segment must also name `human_provenance`, a JSON filename
relative to the course's `data/audio-provenance/`. The record contains:

```json
{
  "performer": "<actual name or documented performer identifier>",
  "recorded_on": "<YYYY-MM-DD>",
  "source_recording": {"path": "<retained source path>", "sha256": "<source SHA-256>"},
  "permission": {
    "path": "<retained permission or licence record>",
    "sha256": "<record SHA-256>",
    "scope": "<actual permitted use, including the intended distribution>"
  },
  "review": {
    "reviewer": "<actual reviewer>",
    "date": "<YYYY-MM-DD>",
    "verdict": "<pass, hold or fail>",
    "notes": "<observed transcript, pronunciation and recording-quality findings>",
    "recording_sha256": "<delivered OGG SHA-256>",
    "transcript_sha256": "<SHA-256 of the exact UTF-8 manifest transcript>"
  }
}
```

This is a schema example, not permission or approval. Fill it only from genuine
records. D6 rejects missing evidence, placeholders, future dates, held reviews
and any changed source, permission, delivery clip or transcript digest. It cannot
determine the truth of an asserted permission; release review must check that
the real record covers the actual use. A reviewed TTS clip must not be relabelled
human to bypass the voice audition.

Source/permission paths resolve relative to the course by default. Keep personal
consent records and source recordings outside a public Git repository where
appropriate; point `--evidence-root /private/course-evidence` or
`BOULINGUA_AUDIO_EVIDENCE_ROOT` at the retained evidence directory when running
D6/`kit check`. Files must remain inside that directory. The gate verifies them
in place and does not copy them into the website. CI needs authorized read access
to that evidence; a missing private record is a blocked check, not a waiver.

For speech extraction, italics and bold are spoken text. Only a whole
parenthesized aside, optionally italicized, is treated as a stage direction
(for example `*(The door opens.)*`). Directions stay in the displayed transcript;
bold speaker labels followed by italic utterances retain their spoken turns.

## Generate course clips

Install FFmpeg with the `libopus` encoder in addition to the Python environment:

```sh
python bin/kit audio build ../fle \
  --voice "$HOME/.cache/boulingua/voices/fle/fr_FR-mls-medium.onnx" \
  --lang fr --speaker 0 --units-glob 'content/**/index.md' --only UNIT_DIRECTORY
```

Review one complete unit before using `--all`. The tool stages audio and
manifests before publishing a successful unit, preserves human recordings,
records model/config identity and updates the source page's manifest key.
`--only` takes the exact unit-directory name. A release still requires the
recording/provenance gate and a passed audition for the actual selected voice.

Existing historical recordings have incomplete provenance. Do not assign the
current candidate's identity to them without evidence; regenerate or document
their true source. See [NOTICE.md](NOTICE.md) for attribution policy.


## Extraction scope and batch preparation

Only pages declared `page_type: unit` are eligible, even when a broad glob also
matches legal or exam bundles. Speech comes from the opening learner story and
Input sections: blockquote dialogues/readings, explicitly named vocabulary
tables, English italic vocabulary lists/reading passages, and plain opening
stories. Recognized answer wrappers, teacher notes, exam tasks, grammar tables,
assessment criteria and explicitly foreign-language mediation headings are
excluded. This is a selected listening corpus, not a spoken copy of every lesson
line. Short excerpts, unrecognized formats and foreign mediation source texts
need deliberate authoring/review before a recording is added.

Every synthesized entry records its source path, exact source-body digest,
extraction policy, model/configuration digests, speaker and synthesis backend.
Normalization changes only the separate `tts` field; the transcript retains the
selected written stimulus. Review both, especially stage directions and names.

For a large staged build, the direct generator supports `--persistent-model`:

```sh
python audio/build_audio.py /path/to/copied-course /path/to/voice.onnx en \
  'content/**/index.md' --all --speaker 0 --persistent-model
```

This optional mode uses the installed Piper Python API, retaining one model
session per selected voice with one CPU inference thread. It rejects unmapped
phonemes and synthesis failures before publishing a unit. The CLI backend
remains the default; backend changes invalidate synthesis caches. A successful
batch, waveform decode or source-text comparison does not establish native
pronunciation quality, factual accuracy or listening approval. Keep staged
candidates separate until those reviews pass.

The learner-input-v3 policy selects target-language vocabulary columns from
supported headers, including parallel target columns. Ratings, grammatical
person labels and foreign-source translation columns are withheld. Explicit
foreign-language names and uppercase ISO labels such as `(original, DE)` also
withhold a section; mixed-language openings must carry that explicit source
label. Each generated manifest records `withheld_foreign_sections`. This is a
selected target-language audio corpus, not a voiced copy of every source line.
