#!/bin/sh
# Print the newest STABLE Bitcoin Knots release tag (vNN.N.knotsYYYYMMDD) that can actually be downloaded.
# Release candidates are skipped. A new git tag can appear days before the Knots team uploads its binaries,
# so tags are tried newest first and the first one whose SHA256SUMS can be fetched wins; the others are
# reported on stderr and will be picked up by a later run.
#   KNOTS_TAGS="v1 v2"  overrides the tag list (newest first); KNOTS_SITES_TMPL overrides the download addresses
#   (use @VER@, @MAJOR@ and @TAG@) -- both are for testing.
set -eu
UA="Mozilla/5.0 (X11; Linux x86_64) blake2b-knots-build"
TMPL="${KNOTS_SITES_TMPL:-https://bitcoinknots.org/files/@MAJOR@.x/@VER@ https://github.com/bitcoinknots/bitcoin/releases/download/@TAG@}"
tags="${KNOTS_TAGS:-$(git ls-remote --tags --refs https://github.com/bitcoinknots/bitcoin 'refs/tags/v*.knots*' \
  | sed 's|.*refs/tags/||' \
  | grep -E '^v[0-9]+\.[0-9]+(\.[0-9]+)?\.knots[0-9]{8}$' \
  | sort -rV)}"
for tag in $tags; do
  ver="${tag#v}"; major="${ver%%.*}"
  for t in $TMPL; do
    base="$(printf '%s' "$t" | sed -e "s/@VER@/$ver/g" -e "s/@MAJOR@/$major/g" -e "s/@TAG@/$tag/g")"
    code="$(curl -sSL -A "$UA" -m 30 -o /dev/null -w '%{http_code}' "$base/SHA256SUMS" 2>/dev/null || true)"
    if [ "$code" = 200 ]; then echo "$tag"; exit 0; fi
    echo "  $tag: $base/SHA256SUMS -> HTTP ${code:-none}" >&2
  done
  echo "  $tag has no downloadable release yet, trying the one before" >&2
done
echo "no Bitcoin Knots release with downloadable binaries found" >&2
exit 1
