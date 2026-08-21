#!/usr/bin/env bash
# Download the openly-licensed native Piper voices used by boulingua.
# Voices: rhasspy/piper-voices (MIT). Stored in ./voices/.
#
# The voice IDs are not in this script. They are in voices.yml next to it,
# which is the single source of truth; nothing here constructs a URL from a
# key. Only rows that are both `status: ready` and `licence_ok: true` are
# fetched — the licence is checked before anything is downloaded, because a
# NonCommercial voice cannot ship inside boulingua's CC BY-SA 4.0 content.
# Everything else is reported and skipped.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
registry="$here/voices.yml"
[ -f "$registry" ] || { echo "get_voices: missing $registry" >&2; exit 1; }

# code|status|licence_ok|voice|model_url, one line per language row.
rows="$(awk '
  function emit() { if (code != "") printf "%s|%s|%s|%s|%s\n", code, status, ok, voice, url }
  function val(s) { sub(/^[^:]*:[[:space:]]*/, "", s); gsub(/"/, "", s); return s }
  /^languages:/            { inlangs = 1; next }
  inlangs && /^  - code: / { emit(); code = $3; status = ""; ok = ""; voice = ""; url = "" }
  inlangs && /^    status: /     { status = val($0) }
  inlangs && /^    licence_ok: / { ok     = val($0) }
  inlangs && /^    voice: /      { voice  = val($0) }
  inlangs && /^    model_url: /  { url    = val($0) }
  END { emit() }
' "$registry")"

mkdir -p "$here/voices" && cd "$here/voices"
fetched=0
while IFS='|' read -r code status ok voice url; do
  [ -n "$code" ] || continue
  if [ "$status" != "ready" ]; then
    echo "skip $code: status $status"
    continue
  fi
  if [ "$ok" != "true" ]; then
    echo "skip $code: licence not usable for CC BY-SA 4.0 content"
    continue
  fi
  # The URL comes from the registry verbatim (it is percent-encoded); only the
  # local filename is built from the key, which is what build_audio.py expects.
  for ext in onnx onnx.json; do
    case "$ext" in onnx) u="$url" ;; *) u="$url.json" ;; esac
    [ -f "$voice.$ext" ] || curl -fsSL "$u" -o "$voice.$ext"
  done
  echo "voice ready: $voice"
  fetched=$((fetched + 1))
done <<EOF
$rows
EOF
echo "get_voices: $fetched voice(s) in $here/voices"
