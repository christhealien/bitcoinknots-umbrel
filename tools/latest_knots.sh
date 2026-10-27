#!/bin/sh
# Print the newest STABLE Bitcoin Knots release tag (vNN.N.knotsYYYYMMDD; release candidates are skipped).
set -eu
git ls-remote --tags --refs https://github.com/bitcoinknots/bitcoin 'refs/tags/v*.knots*' \
  | sed 's|.*refs/tags/||' \
  | grep -E '^v[0-9]+\.[0-9]+(\.[0-9]+)?\.knots[0-9]{8}$' \
  | sort -V | tail -n1
