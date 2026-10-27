#!/usr/bin/env python3
"""Apply this repo's changes to a checkout of Horizon-btc/umbrel-bitcoin.

  patch_ui.py UPSTREAM_DIR KNOTS_TAG [--check]

1. makes KNOTS_TAG the newest (index 0) version the app knows, so "Always use the latest version" runs it and the
   settings that depend on the version keep working (they compare positions in that list)
2. shows only that one version in the version dropdown (it is the only bitcoind in the image) and, when a saved
   setting names a version that is not in the image, starts the newest one instead of failing
3. adds the blake2b theme, logo and icons
Every edit is anchored on an exact piece of upstream. A missing anchor stops the build, so an upstream
refactor can never ship a half-patched app.
"""
import os, re, shutil, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
META = "libs/settings/settings.meta.ts"
MANAGER = "apps/backend/src/modules/bitcoind/manager.ts"
MAIN = "apps/ui/src/main.tsx"
INDEX = "apps/ui/index.html"


def rd(up, rel):
    with open(os.path.join(up, rel), encoding="utf-8") as f:
        return f.read()


def wr(up, rel, s):
    with open(os.path.join(up, rel), "w", encoding="utf-8") as f:
        f.write(s)


def plan(up, tag):
    """returns (edits, problems); edits is a list of (file, new text)"""
    edits, bad = [], []

    s = rd(up, META)
    m = re.search(r"export const AVAILABLE_BITCOIN_KNOTS_VERSIONS = \[", s)
    if not m:
        bad.append("%s: AVAILABLE_BITCOIN_KNOTS_VERSIONS list not found" % META)
    else:
        if ("'%s'" % tag) not in s[m.end():m.end() + 4000]:
            s = s[:m.end()] + "'%s', " % tag + s[m.end():]
        old = "...AVAILABLE_BITCOIN_KNOTS_VERSIONS.map((version) => ({value: version, label: version})),"
        if ".slice(0, 1).map((version)" in s:
            pass
        elif s.count(old) != 1:
            bad.append("%s: version dropdown line not found exactly once" % META)
        else:
            s = s.replace(old, "...AVAILABLE_BITCOIN_KNOTS_VERSIONS.slice(0, 1).map((version) => ({value: version, label: version})),")
        edits.append((META, s))

    s = rd(up, MANAGER)
    old = "const version = getVersionFromSettings()"
    if "const wanted = getVersionFromSettings()" in s:
        pass
    elif s.count(old) != 1:
        bad.append("%s: expected exactly one %r" % (MANAGER, old))
    else:
        s = s.replace(old, "const wanted = getVersionFromSettings()\n\t\t// blake2b: the image holds one bitcoind, the newest. A saved older choice falls back to it.\n\t\tconst version = isVersionInstalled(wanted) ? wanted : DEFAULT_BITCOIN_KNOTS_VERSION")
        edits.append((MANAGER, s))

    s = rd(up, MAIN)
    if "blake2b-theme.css" not in s:
        old = "import './index.css'"
        if s.count(old) != 1:
            bad.append("%s: expected exactly one %r" % (MAIN, old))
        else:
            edits.append((MAIN, s.replace(old, old + "\nimport './blake2b-theme.css'")))

    s = rd(up, INDEX)
    if "<title>Bitcoin Knots</title>" in s:
        pass
    elif "<title>Bitcoin Node</title>" not in s:
        bad.append("%s: title not found" % INDEX)
    else:
        edits.append((INDEX, s.replace("<title>Bitcoin Node</title>", "<title>Bitcoin Knots</title>")))
    return edits, bad


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        print(__doc__); return 2
    up, tag = args
    if not re.fullmatch(r"v\d+\.\d+(\.\d+)?\.knots\d{8}", tag):
        print("FAIL  %r does not look like a stable Knots release tag (vNN.N.knotsYYYYMMDD)" % tag); return 2
    edits, bad = plan(up, tag)
    for b in bad:
        print("FAIL ", b)
    if bad:
        return 2
    if "--check" in sys.argv:
        print("OK  patch fits this upstream"); return 0
    for rel, s in edits:
        wr(up, rel, s)
    ui = os.path.join(HERE, "overlay/ui")
    shutil.copy(os.path.join(ui, "blake2b-theme.css"), os.path.join(up, "apps/ui/src/blake2b-theme.css"))
    shutil.copy(os.path.join(ui, "logo.svg"), os.path.join(up, "apps/ui/src/assets/logo.svg"))
    fav = os.path.join(up, "apps/ui/public/favicons")
    os.makedirs(fav, exist_ok=True)
    for n in os.listdir(os.path.join(ui, "favicons")):
        shutil.copy(os.path.join(ui, "favicons", n), os.path.join(fav, n))
    # the manifest names the app and uses the same icons
    mf = os.path.join(fav, "manifest.webmanifest")
    if os.path.exists(mf):
        t = open(mf, encoding="utf-8").read().replace("Bitcoin Node", "Bitcoin Knots")
        open(mf, "w", encoding="utf-8").write(t)
    print("OK  patched for %s" % tag)
    return 0


if __name__ == "__main__":
    sys.exit(main())
