#!/usr/bin/env bash
# verify-vgwort.sh — fail the build if any article registered in
# vgwort-manifest.csv is missing its VG Wort Zählpixel in the rendered
# Hugo output under public/.
#
# When the manifest is empty (header only), the script passes trivially.
# This is intentional — the DaF site has no per-article VG Wort tokens
# at the time of migration; the gate becomes meaningful the moment the
# author begins registering counting marks in T.O.M.

set -euo pipefail

MANIFEST="${1:-vgwort-manifest.csv}"
PUBLIC="${2:-public}"

if [ ! -f "$MANIFEST" ]; then
  echo "verify-vgwort: $MANIFEST not found — nothing to verify."
  exit 0
fi

# Skip header line; count remaining rows.
rows=$(tail -n +2 "$MANIFEST" | grep -cv '^[[:space:]]*$' || true)

if [ "$rows" -eq 0 ]; then
  echo "verify-vgwort: manifest is empty — passing trivially."
  exit 0
fi

if [ ! -d "$PUBLIC" ]; then
  echo "::error::verify-vgwort: $PUBLIC does not exist but manifest has $rows entries."
  exit 1
fi

failed=0
while IFS=, read -r qmd_path article_slug pixel_url _rest; do
  [ -z "$qmd_path" ] && continue
  # Strip surrounding quotes if any.
  pixel_url="${pixel_url%\"}"
  pixel_url="${pixel_url#\"}"

  # Map qmd_path -> rendered html path. .qmd articles become directories
  # with index.html under Hugo's pretty-URL convention.
  rel="${qmd_path%.qmd}"
  rel="${rel%.md}"
  candidate1="$PUBLIC/$rel/index.html"
  candidate2="$PUBLIC/$rel.html"

  page=""
  if [ -f "$candidate1" ]; then
    page="$candidate1"
  elif [ -f "$candidate2" ]; then
    page="$candidate2"
  fi

  if [ -z "$page" ]; then
    echo "FAIL  $qmd_path  (no rendered page found at $candidate1 or $candidate2)"
    failed=$((failed + 1))
    continue
  fi

  # A registered page carries the token twice: once as the <head>
  # rel=preload hint and once as the body <img>. Both resolve to a single
  # network request (the img reuses the preloaded resource), so the invariant
  # is "present on its page, and on exactly one page site-wide".
  hits=$(grep -c "$pixel_url" "$page" || true)
  pages=$(grep -rl --include="*.html" -- "$pixel_url" "$PUBLIC" 2>/dev/null | wc -l)
  if [ "$hits" -lt 1 ]; then
    echo "FAIL  $qmd_path  (pixel absent) in $page"
    failed=$((failed + 1))
  elif [ "$pages" -ne 1 ]; then
    echo "FAIL  $qmd_path  (pixel appears on $pages pages, want 1): $pixel_url"
    failed=$((failed + 1))
  else
    echo "ok    $qmd_path"
  fi
done < <(tail -n +2 "$MANIFEST")

if [ "$failed" -gt 0 ]; then
  echo "::error::verify-vgwort: $failed article(s) missing or duplicated pixels."
  exit 1
fi

echo "verify-vgwort: all $rows article(s) carry their pixel exactly once."
