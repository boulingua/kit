#!/usr/bin/env bash
# Download the openly-licensed native Piper voices used by boulingua.
# Voices: rhasspy/piper-voices (MIT). Stored in ./voices/.
set -euo pipefail
BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main"
mkdir -p voices && cd voices
# name|path (add more voices for variety / more languages here)
voices=(
  "fr_FR-siwis-medium|fr/fr_FR/siwis/medium"
  "de_DE-thorsten-medium|de/de_DE/thorsten/medium"
  "en_GB-alba-medium|en/en_GB/alba/medium"
)
for v in "${voices[@]}"; do
  name="${v%%|*}"; path="${v##*|}"
  for ext in onnx onnx.json; do
    [ -f "$name.$ext" ] || curl -fsSL "$BASE/$path/$name.$ext" -o "$name.$ext"
  done
  echo "voice ready: $name"
done
