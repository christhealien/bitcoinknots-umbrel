#!/usr/bin/env python3
"""Point the app at a Knots release:  bump.py KNOTS_TAG [--rev N] [--note "text"]
Writes KNOTS_TAG, and the version, release notes and image tag of blake2b-bitcoinknots/.
Prints VERSION=..., IMAGE_TAG=... and TAG=... (the git tag that releases it).
--rev N is for a new build of the same Knots release (a theme or packaging change): it adds .N to the version."""
import argparse, os, re, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(HERE, "blake2b-bitcoinknots")


def names(tag, rev):
    m = re.fullmatch(r"v(\d+)\.(\d+)(?:\.(\d+))?\.knots(\d{8})", tag)
    if not m:
        sys.exit("bad Knots tag %r" % tag)
    major, minor, patch, date = m.group(1), m.group(2), m.group(3) or "0", m.group(4)
    version = "%s.%s.%s-knots.%s" % (major, minor, patch, date) + (".%d" % rev if rev else "")
    image = tag[1:] + ("-%d" % rev if rev else "")
    return version, image


def sub(path, pattern, repl):
    s = open(path, encoding="utf-8").read()
    n, c = re.subn(pattern, repl, s, count=1, flags=re.M)
    if c != 1:
        sys.exit("%s: could not find %r" % (path, pattern))
    open(path, "w", encoding="utf-8").write(n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tag")
    ap.add_argument("--rev", type=int, default=0)
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    version, image = names(a.tag, a.rev)
    open(os.path.join(HERE, "KNOTS_TAG"), "w").write(a.tag + "\n")
    y = os.path.join(APP, "umbrel-app.yml")
    sub(y, r'^version: ".*"$', 'version: "%s"' % version)
    note = a.note or "Bitcoin Knots %s." % a.tag
    sub(y, r"^releaseNotes: >-\n(?:  .*\n?)+", "releaseNotes: >-\n  %s\n" % note)
    sub(os.path.join(APP, "docker-compose.yml"), r"(image: ghcr\.io/[^/\s]+/blake2b-bitcoinknots:)\S+", r"\g<1>" + image)
    print("VERSION=%s\nIMAGE_TAG=%s\nTAG=knots-v%s" % (version, image, version))


if __name__ == "__main__":
    main()
