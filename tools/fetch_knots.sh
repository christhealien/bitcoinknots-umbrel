#!/bin/sh
# Download the official Bitcoin Knots binaries for one release and check them.
#   fetch_knots.sh TAG ARCH OUTDIR      e.g.  fetch_knots.sh v29.4.3.knots20260508 x86_64-linux-gnu /out
# Sources: bitcoinknots.org/files and the GitHub release. When both publish SHA256SUMS they must agree.
# It says what it asked for and what came back, so a failed build explains itself.
set -eu
tag="$1"; arch="$2"; out="$3"
ver="${tag#v}"; major="${ver%%.*}"
file="bitcoin-${ver}-${arch}.tar.gz"
UA="Mozilla/5.0 (X11; Linux x86_64) blake2b-knots-build"
SITES="${KNOTS_SITES:-https://bitcoinknots.org/files/${major}.x/${ver} https://github.com/bitcoinknots/bitcoin/releases/download/${tag}}"
work="$(mktemp -d)"; cd "$work"

get() {   # url dest: success only on HTTP 200
  code="$(curl -sSL -A "$UA" --retry 3 -o "$2" -w '%{http_code}' "$1" 2>err.txt || true)"
  echo "  GET $1 -> HTTP ${code:-none} $(tr '\n' ' ' < err.txt)"
  [ "$code" = 200 ]
}

echo "Knots $tag: looking for $file"
got=""; i=0
for base in $SITES; do
  i=$((i + 1))
  if get "$base/SHA256SUMS" "sums.$i"; then got="$got $i"; fi
done
if [ -z "$got" ]; then
  echo "ERROR: no SHA256SUMS found for $tag at any source." >&2
  for base in $SITES; do
    echo "--- what $base/ offers:" >&2
    curl -sSL -A "$UA" -m 30 "$base/" 2>&1 | grep -oE 'href="[^"]+"' | head -40 >&2 || true
  done
  exit 1
fi
first="$(echo $got | cut -d' ' -f1)"
for n in $got; do
  cmp -s "sums.$first" "sums.$n" || { echo "ERROR: SHA256SUMS differ between sources" >&2; exit 1; }
done
grep -E "[ *]${file}\$" "sums.$first" > want.sum || {
  echo "ERROR: $file is not listed in SHA256SUMS. It lists:" >&2; head -30 "sums.$first" >&2; exit 1; }
ok=""; i=0
for base in $SITES; do
  i=$((i + 1))
  if get "$base/$file" "$file" && sha256sum -c want.sum; then ok=1; break; fi
done
[ -n "$ok" ] || { echo "ERROR: could not download a verified $file" >&2; exit 1; }
tar xzf "$file"
mkdir -p "$out"
cp "bitcoin-${ver}/bin/bitcoind" "bitcoin-${ver}/bin/bitcoin-cli" "$out/"
"$out/bitcoind" -version | head -1
