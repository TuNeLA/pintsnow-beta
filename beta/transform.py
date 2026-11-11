#!/usr/bin/env python3
"""PintsNow BETA build: copy the app (docs/ of TuNeLA/Beer-map, branch big-update) and mark it as a beta.
usage: transform.py <docs dir> <out dir> <commit sha> [--mode beta|staging] [--testenv <dir>]
--mode beta (default) = https://tunela.github.io/pintsnow-beta/
- same Supabase backend and Mapbox token (config.js unchanged)
- <meta robots noindex,nofollow>, title "BETA · …", no web app manifest (no install prompt, no "Install app" card)
- a small fixed "BETA" badge (with the short commit) on top of the map; pointer-events none
- never contains the test toolbar (any testenv/testbar file is removed); its sw.js leaves /test/ alone
--mode staging = https://tunela.github.io/pintsnow-beta/test/ (the owner's hand-test build)
- every live Supabase address + key is replaced by the STAGING project (build FAILS if a live ref is left)
- testenv.js first in <head> (own storage, fake clock / position, test-kit login), testbar.js + .css (the test panel)
- a "TESTLÄGE · staging" badge; installable as "PN Test" (own manifest name), noindex
Idempotent; tolerant to text changes in index.html (regex anchors only on tag names)."""
import re, shutil, sys, os, html, hashlib

LIVE_REF, STAGING_REF = "wcdskpcevbhouvbytkhv", "vdtmzsxajpvzwwbhnfmr"
STAGING_URL = "https://%s.supabase.co" % STAGING_REF
# public anon key of the STAGING project (role anon; same kind of key as docs/config.js). Not a secret.
STAGING_ANON = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZkdG16c3hhanB2end3YmhuZm1yIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTQwOTIxNzQsImV4cCI6MjEwOTY2ODE3NH0.bk45yZXL0OrHWSrZrAhFJpbtBXgzD_CDVbnoZrKCS-w"
TEST_FILES = ("testenv.js", "js/testbar.js", "testbar.css", "test.js")

args = sys.argv[1:]
mode, testenv = "beta", None
if "--mode" in args:
    i = args.index("--mode"); mode = args[i + 1]; del args[i:i + 2]
if "--testenv" in args:
    i = args.index("--testenv"); testenv = args[i + 1]; del args[i:i + 2]
if mode not in ("beta", "staging"):
    sys.exit("transform: --mode must be beta or staging")
src, out, sha = args[0], args[1], (args[2] if len(args) > 2 else "")[:7]
STAGING = mode == "staging"
if STAGING and not testenv:
    testenv = os.path.join(os.path.dirname(os.path.abspath(src.rstrip("/"))), "testenv")
if os.path.exists(out): shutil.rmtree(out)
shutil.copytree(src, out)
TEXT = (".js", ".html", ".json", ".css", ".webmanifest", ".txt", ".md")

def rd(p): return open(p, encoding="utf-8").read()
def wr(p, s): open(p, "w", encoding="utf-8").write(s)

if STAGING:
    # 1. the live key + address → staging (every text file; the app has the address in config.js, index.html, flytta.html)
    cp = os.path.join(out, "config.js"); c = rd(cp)
    live_key = re.search(r'SUPABASE_ANON_KEY:\s*"([^"]+)"', c)
    live_key = live_key.group(1) if live_key else None
    c = re.sub(r'(SUPABASE_URL:\s*)"[^"]*"', r'\1"%s"' % STAGING_URL, c)
    c = re.sub(r'(SUPABASE_ANON_KEY:\s*)"[^"]*"', r'\1"%s"' % STAGING_ANON, c)
    c = re.sub(r'(BETA_URL:\s*)"[^"]*"', r'\1""', c)          # no "Betaversion" switch inside the test build
    wr(cp, c)
    for dp, dn, fn in os.walk(out):
        for f in fn:
            if not f.endswith(TEXT): continue
            p = os.path.join(dp, f)
            try: t = rd(p)
            except UnicodeDecodeError: continue
            t2 = t.replace(live_key, STAGING_ANON) if live_key else t
            t2 = t2.replace(LIVE_REF, STAGING_REF)
            if t2 != t: wr(p, t2)
    # 2. the test files
    if not os.path.isdir(testenv): sys.exit("transform: --mode staging needs the testenv dir (%s)" % testenv)
    shutil.copy(os.path.join(testenv, "testenv.js"), os.path.join(out, "testenv.js"))
    shutil.copy(os.path.join(testenv, "testbar.js"), os.path.join(out, "js", "testbar.js"))
    shutil.copy(os.path.join(testenv, "testbar.css"), os.path.join(out, "testbar.css"))
else:
    for f in TEST_FILES:   # the normal beta never ships the test panel
        try: os.remove(os.path.join(out, f))
        except FileNotFoundError: pass

p = os.path.join(out, "index.html"); s = rd(p)
if STAGING:
    if 'src="./js/testbar.js' not in s:
        s, n = re.subn(r'(<script\b[^>]*\bsrc="\./app\.js)', '<script defer src="./js/testbar.js"></script>\n\\1', s, count=1)
        if not n: sys.exit("transform: app.js <script> not found")
    if 'href="./testbar.css' not in s:
        s = re.sub(r"(</head>)", '<link rel="stylesheet" href="./testbar.css">\n\\1', s, count=1)
# pnds: stamp like stamp-version.yml (every local js/css ?v=<sha256[:10]>, sw.js VERSION = hash of the app files)
def _h(fp): return hashlib.sha256(open(fp, "rb").read()).hexdigest()[:10]
def _stamp(m):
    f = m.group(2); fp = os.path.join(out, f)
    return m.group(1) + f + ("?v=" + _h(fp) if os.path.isfile(fp) else (m.group(3) or "")) + '"'
s = re.sub(r'((?:src|href)="\./)([^"?]+\.(?:js|css))(\?v=[^"]*)?"', _stamp, s)
_sw = os.path.join(out, "sw.js")
if os.path.exists(_sw) and not STAGING:
    # the normal beta's worker (scope /pintsnow-beta/) must not answer for the test build under /pintsnow-beta/test/
    _t = rd(_sw)
    if "pintsnow-beta /test/" not in _t:
        _t, n = re.subn(r'(\n(\s*)var scopePath = new URL\(self\.registration\.scope\)\.pathname;\n)',
                        r'\1\2if (url.pathname.indexOf(scopePath + "test/") === 0) return;   // pintsnow-beta /test/ = the staging test build (own worker)\n',
                        _t, count=1)
        if not n: print("transform: WARNING sw.js anchor not found; the beta worker may answer for /test/ on a first visit")
        wr(_sw, _t)
_all = hashlib.sha256()
for dp, dn, fn in sorted(os.walk(out)):
    dn.sort()
    for f in sorted(fn):
        rel = os.path.relpath(os.path.join(dp, f), out)
        if rel in ("sw.js", "index.html", "bars.json", "places.json") or rel.startswith(("places/", "buildings/", "buildings3d/")): continue
        _all.update(rel.encode() + b"\0" + open(os.path.join(dp, f), "rb").read())
if os.path.exists(_sw):
    _t = rd(_sw)
    _t = re.sub(r'^var VERSION = "[^"]*";', 'var VERSION = "olnu-%s%s";' % ("t" if STAGING else "b", _all.hexdigest()[:9]), _t, count=1, flags=re.M)
    wr(_sw, _t)
if STAGING:
    title, badge_txt, badge_bg, badge_fg, setup = "TEST", "TESTLÄGE · staging", "#e0457b", "#fff", "test.js"
else:
    title, badge_txt, badge_bg, badge_fg, setup = "BETA", "BETA", "#f5a623", "#241300", "beta.js"
    s = re.sub(r'\s*<link[^>]+rel="manifest"[^>]*>', "", s)                       # not installable
s = re.sub(r"<title>(?!%s)" % title, "<title>%s · " % title, s, count=1)
head = ('<meta name="robots" content="noindex,nofollow">\n'
  + ('<script src="./testenv.js"></script>\n' if STAGING else '')
  + '<script src="./%s"></script>\n' % setup
  + '<style id="beta-css">#olnu-beta{position:fixed;z-index:2147483000;top:calc(env(safe-area-inset-top,0px) + 3px);left:50%;transform:translateX(-50%);'
  'font:700 10px/14px system-ui,sans-serif;letter-spacing:.08em;padding:1px 7px;border-radius:7px;background:' + badge_bg + ';color:' + badge_fg + ';'
  'pointer-events:none;opacity:.92;box-shadow:0 1px 4px rgba(0,0,0,.5);white-space:nowrap}</style>\n')
if 'name="robots"' not in s:   # after <meta charset> (must stay in the first bytes) and the CSP meta when they exist
    m = list(re.finditer(r'<meta[^>]+(charset=|http-equiv="Content-Security-Policy")[^>]*>\s*', s[:4000], re.I))
    at = m[-1].end() if m else re.search(r"<head[^>]*>\s*", s).end()
    s = s[:at] + head + s[at:]
badge = '<div id="olnu-beta" aria-hidden="true">' + badge_txt + (" " + html.escape(sha) if sha else "") + "</div>"
if 'id="olnu-beta"' not in s: s = re.sub(r"(<body[^>]*>)", r"\1\n" + badge, s, count=1)
base = "https://tunela.github.io/pintsnow-beta/" + ("test/" if STAGING else "")
s = s.replace("https://tunela.github.io/Beer-map/docs/", base)   # link preview shows the build's own image
s = re.sub(r'(og-image\.png)(\?v=[^"]*)?"', r'\1?v=pn1"', s)   # new URL = chat apps fetch the new PintsNow image, not a cached old one
wr(p, s)
if STAGING:
    mp = os.path.join(out, "manifest.webmanifest")
    if os.path.exists(mp):
        mt = rd(mp)
        mt = re.sub(r'("name":\s*)"[^"]*"', r'\1"PintsNow TEST"', mt, count=1)
        mt = re.sub(r'("short_name":\s*)"[^"]*"', r'\1"PN Test"', mt, count=1)
        wr(mp, mt)
    open(os.path.join(out, "test.js"), "w").write('window.PN_BETA=%r;window.PN_TEST={ref:%r,sha:%r};\n' % (sha, STAGING_REF, sha))
    # safety: no live address or live key may be left anywhere in the test build
    bad = []
    for dp, dn, fn in os.walk(out):
        for f in fn:
            fp = os.path.join(dp, f)
            try: b = open(fp, "rb").read()
            except Exception: continue
            if LIVE_REF.encode() in b or (live_key and live_key.encode() in b): bad.append(os.path.relpath(fp, out))
    if bad: sys.exit("transform: live Supabase ref/key still in: " + ", ".join(bad[:20]))
else:
    for f in ("manifest.webmanifest",):   # nothing links it any more; remove so no store / browser picks it up
        try: os.remove(os.path.join(out, f))
        except FileNotFoundError: pass
    # the app's CSP allows only 'self' scripts: the beta setup is a file. It skips the first-visit "install the app" card.
    open(os.path.join(out, "beta.js"), "w").write('window.PN_BETA=%r;try{localStorage.setItem("olnu.inst1",String(Date.now()));localStorage.setItem("olnu.beta",%r)}catch(e){}\n' % (sha, sha))
    for dp, dn, fn in os.walk(out):   # safety: the normal beta never contains the test panel
        for f in fn:
            if f in ("testenv.js", "testbar.js", "testbar.css"): sys.exit("transform: test file in the normal beta: " + f)
open(os.path.join(out, ".nojekyll"), "w").close()
print(("staging test" if STAGING else "beta") + " build ok", sha)
