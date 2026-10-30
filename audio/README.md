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
