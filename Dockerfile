# Bitcoin Knots node app for Umbrel, themed like the other blake2b apps.
#
# Built from the Horizon-btc/umbrel-bitcoin app (backend + web UI) with this repo's overlay applied (tools/patch_ui.py),
# and the NEWEST Bitcoin Knots release (KNOTS_TAG) as the only bitcoind. The workflow works out KNOTS_TAG by itself,
# so nothing here is pinned to one release.
#
# docker buildx build -f Dockerfile --build-arg KNOTS_TAG=v29.4.knots20260508 <patched umbrel-bitcoin checkout>

###########################################
# bitcoind + bitcoin-cli, from the official release, checksum-verified
###########################################
FROM debian:bookworm-slim AS knots
ARG KNOTS_TAG
ARG TARGETARCH
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*
RUN set -eu; \
    test -n "$KNOTS_TAG" || { echo "KNOTS_TAG is required" >&2; exit 1; }; \
    ver="${KNOTS_TAG#v}"; major="${ver%%.*}"; \
    case "$TARGETARCH" in amd64) arch=x86_64-linux-gnu;; arm64) arch=aarch64-linux-gnu;; *) echo "unsupported arch $TARGETARCH" >&2; exit 1;; esac; \
    file="bitcoin-${ver}-${arch}.tar.gz"; \
    mkdir /dl && cd /dl; \
    site="https://bitcoinknots.org/files/${major}.x/${ver}"; \
    gh="https://github.com/bitcoinknots/bitcoin/releases/download/${KNOTS_TAG}"; \
    got=""; \
    for base in "$site" "$gh"; do \
      if curl -fsSL --retry 3 -o "SHA256SUMS.$(echo $base | cut -d/ -f3)" "$base/SHA256SUMS"; then got="$got $base"; fi; \
    done; \
    test -n "$got" || { echo "no SHA256SUMS found for $KNOTS_TAG" >&2; exit 1; }; \
    # when both hosts publish the list they must agree, so one compromised host cannot slip a binary through
    n=0; for s in SHA256SUMS.*; do n=$((n+1)); done; \
    if [ "$n" -gt 1 ]; then cmp SHA256SUMS.* || { echo "SHA256SUMS differ between hosts" >&2; exit 1; }; fi; \
    sums="$(ls SHA256SUMS.* | head -1)"; \
    grep -E "[ *]${file}\$" "$sums" > want.sum || { echo "$file is not in SHA256SUMS" >&2; exit 1; }; \
    ok=""; \
    for base in $got; do \
      if curl -fsSL --retry 3 -o "$file" "$base/$file" && sha256sum -c want.sum; then ok=1; break; fi; \
    done; \
    test -n "$ok" || { echo "could not download a verified $file" >&2; exit 1; }; \
    tar xzf "$file"; \
    mkdir -p /out; \
    cp "bitcoin-${ver}/bin/bitcoind" "bitcoin-${ver}/bin/bitcoin-cli" /out/; \
    /out/bitcoind -version | head -1

##########################################################
# Dependencies layer: install every workspace's deps
##########################################################
FROM node:20-slim AS deps
WORKDIR /repo
COPY package*.json ./
COPY apps/backend/package*.json apps/backend/
COPY apps/ui/package*.json apps/ui/
RUN npm ci --workspaces --include-workspace-root --install-strategy=hoisted
ENV PATH="/repo/node_modules/.bin:$PATH"

#################################################
# app-builder: compile backend and bundle the UI
#################################################
FROM deps AS app-builder
WORKDIR /repo
COPY . .
RUN tsc -b libs/shared-types libs/settings apps/backend \
 && npm run --workspace apps/ui build

########################################
# runtime: final production image
########################################
FROM node:20-slim AS runtime
ARG KNOTS_TAG
WORKDIR /app
COPY package*.json ./
COPY apps/backend/package*.json apps/backend/
RUN npm ci --omit=dev --install-strategy=hoisted --ignore-scripts

COPY --from=app-builder /repo/apps/backend/dist ./dist
COPY --from=app-builder /repo/apps/ui/dist ./dist/public
COPY --from=app-builder /repo/libs/settings/dist ./libs/settings/dist
COPY --from=app-builder /repo/libs/shared-types/dist ./libs/shared-types/dist

# the one bitcoind, under the version name the app expects (/opt/bitcoind/<tag>/bitcoind)
COPY --from=knots /out/bitcoind /out/bitcoin-cli /tmp/knots/
RUN mkdir -p "/opt/bitcoind/${KNOTS_TAG}" \
 && mv /tmp/knots/bitcoind /tmp/knots/bitcoin-cli "/opt/bitcoind/${KNOTS_TAG}/" \
 && rm -rf /tmp/knots \
 && chown 1000:1000 /opt/bitcoind \
 && ln -sfn "/opt/bitcoind/${KNOTS_TAG}" /opt/bitcoind/current \
 && ln -sfn /opt/bitcoind/current/bitcoind    /usr/local/bin/bitcoind \
 && ln -sfn /opt/bitcoind/current/bitcoin-cli /usr/local/bin/bitcoin-cli

# the datadir link lets `bitcoin-cli` inside the container find the RPC cookie
RUN ln -sfn /data/bitcoin /root/.bitcoin \
 && mkdir -p /home/node \
 && ln -sfn /data/bitcoin /home/node/.bitcoin \
 && chown -h 1000:1000 /home/node/.bitcoin

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

ENV NODE_ENV=production
ENV BITCOIN_DIR=/data/bitcoin
ENV APP_STATE_DIR=/data/app
LABEL org.opencontainers.image.description="Bitcoin Knots ${KNOTS_TAG} node app (blake2b theme)"
EXPOSE 3000 8332 8333
VOLUME /data
CMD ["node", "dist/server.js"]
