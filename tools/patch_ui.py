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


# Cosmetic recolour: orange -> greys. Missing anchors only warn (upstream may move things), never fail the build.
UI = "apps/ui/src/"
COSMETIC = [
    (UI + "pages/home/PeersChart.tsx", [
        ("hsl(29 100% 51%)", "hsl(0 0% 94%)"), ("hsl(29 100% 30%)", "hsl(0 0% 55%)"), ("hsl(29 100% 15%)", "hsl(0 0% 30%)")]),
    (UI + "pages/home/Globe.tsx", [
        ("const PEER_DOT_COLOR = 'hsl(29,100%,60%)'", "const PEER_DOT_COLOR = '#bdbdbd'"),
        ("const ARC_COLOR = 'hsl(29,100%,60%)'", "const ARC_COLOR = '#f4f4f4'"),
        ("const TX_SPHERE_COLOR = 'hsl(29,90%,70%)'", "const TX_SPHERE_COLOR = '#e0e0e0'")]),
    (UI + "pages/home/GlobeInfo.tsx", [("Orange dots are", "Grey dots are")]),
    (UI + "pages/home/Blocks/Transactions.tsx", [
        ("vec3(0.180, 0.027, 0.004)", "vec3(0.07, 0.07, 0.07)"), ("vec3(0.745, 0.212, 0.0)", "vec3(0.42, 0.42, 0.42)"),
        ("vec3(0.933, 0.690, 0.027)", "vec3(0.85, 0.85, 0.85)"), ("vec3(0.784, 0.357, 0.114)", "vec3(0.30, 0.30, 0.30)"),
        ("vec3(0.992, 0.820, 0.0)", "vec3(0.70, 0.70, 0.70)"), ("vec3(1.0, 0.984, 0.769)", "vec3(1.0, 1.0, 1.0)")]),
    (UI + "pages/home/Blocks/liquidShader.ts", [
        ("vec3(0.180, 0.027, 0.004)", "vec3(0.07, 0.07, 0.07)"), ("vec3(0.745, 0.212, 0.0)", "vec3(0.42, 0.42, 0.42)")]),
    (UI + "pages/settings/Toggle.tsx", [
        ("data-[state=checked]:bg-[hsl(29_100%_47%)]", "data-[state=checked]:bg-[#f4f4f4]"),
        ("hsla(29_100%_51%_0.2)", "hsla(0_0%_100%_0.12)")]),
    (UI + "components/ConnectionDetails.tsx", [
        ("fgColor='#9C4C00'", "fgColor='#000000'"), ("bgColor='transparent'", "bgColor='#ffffff'"),
        ("stroke: #FF7E05 !important", "stroke: #000000 !important")]),
]
REGEX = [(UI + "pages/insights/" + n, [(r"hsla\(29,\s*100%,\s*51%,", "hsla(0,0%,94%,"), (r"hsl\(29 100% 51%\)", "hsl(0 0% 94%)"),
         (r"#FF7E05", "#f4f4f4")]) for n in ("BlockSizeChart.tsx", "BlockRewardsChart.tsx", "FeeRateChart.tsx")]


def cosmetic(up):
    edits, warns = [], []
    for rel, pairs in COSMETIC:
        try:
            s = rd(up, rel)
        except OSError:
            warns.append("%s: missing" % rel); continue
        for old, new in pairs:
            if old in s:
                s = s.replace(old, new)
            elif new not in s:
                warns.append("%s: anchor %r not found" % (rel, old))
        edits.append((rel, s))
    for rel, pairs in REGEX:
        try:
            s = rd(up, rel)
        except OSError:
            warns.append("%s: missing" % rel); continue
        for pat, new in pairs:
            s = re.sub(pat, new, s)
        edits.append((rel, s))
    return edits, warns


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
    ce, warns = cosmetic(up)
    for rel, s in ce:
        wr(up, rel, s)
    for w in warns:
        print("WARN ", w)
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
