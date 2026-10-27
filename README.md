# bitcoinknots-umbrel

Bitcoin Knots for Umbrel in the blake2b look, **always on the newest stable Knots release**.

- `blake2b-bitcoinknots/`: the Umbrel app folder. Same ports, IPs, Tor and I2P setup as Horizon's `btc-bitcoinknots`
  (drop-in, but do not run both at once; see the app description for moving the data folder).
- The image is the Bitcoin Node app from `Horizon-btc/umbrel-bitcoin` (backend + web UI), rebuilt with
  `overlay/ui/blake2b-theme.css`, the knot logo and icons, and **one** bitcoind: the release named in `KNOTS_TAG`.

## How it stays current

`.github/workflows/image.yml` runs every day (and on "Run workflow"). It asks `bitcoinknots/bitcoin` for its newest
stable tag (`tools/latest_knots.sh`; release candidates are skipped). If that differs from `KNOTS_TAG` it runs
`tools/bump.py` (version, release notes and image tag of the app folder), commits to `master`, tags `knots-v<version>`,
downloads the official binaries inside the Docker build and checks them against `SHA256SUMS` (published on
bitcoinknots.org and on the GitHub release, which must agree), builds amd64 + arm64 and publishes
`ghcr.io/christhealien/blake2b-bitcoinknots:<knots version>` plus `:latest`. With the `STORE_TOKEN` secret it also
copies the app folder into the store; without it the store's own sync picks the new tag up.
Umbrel only offers an app update when the app `version` changes, which is why each Knots release becomes its own app
version instead of a floating image tag.

If the build for a new Knots release fails (checksums differ, a patch no longer fits upstream), the workflow stops and
the store keeps the last good version; nothing half-built is published.

Theme-only change: `python3 tools/bump.py "$(cat KNOTS_TAG)" --rev 2 --note "..."`, commit, then
`git tag knots-v<the printed version> && git push origin master <that tag>`.

Note: GitHub switches scheduled workflows off after 60 days without repository activity. New Knots releases
(commits) keep it alive; if there is a quiet stretch, re-enable it in the Actions tab or run it once by hand.
Make the ghcr package public once, after the first build.
