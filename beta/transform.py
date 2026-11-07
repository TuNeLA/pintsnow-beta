#!/usr/bin/env python3
"""PintsNow BETA build: copy the app (docs/ of TuNeLA/Beer-map, branch big-update) and mark it as a beta.
usage: transform.py <docs dir> <out dir> <commit sha>
- same Supabase backend and Mapbox token (config.js unchanged)
- <meta robots noindex,nofollow>, title "BETA · …", no web app manifest (no install prompt, no "Install app" card)
- a small fixed "BETA" badge (with the short commit) on top of the map; pointer-events none
Idempotent; tolerant to text changes in index.html (regex anchors only on tag names)."""
import re, shutil, sys, os, html
src, out, sha = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else "")[:7]
if os.path.exists(out): shutil.rmtree(out)
shutil.copytree(src, out)
p = os.path.join(out, "index.html"); s = open(p, encoding="utf-8").read()
# pnds: stamp like stamp-version.yml (every local js/css ?v=<sha256[:10]>, sw.js VERSION = hash of the app files)
import hashlib
def _h(fp): return hashlib.sha256(open(fp, "rb").read()).hexdigest()[:10]
def _stamp(m):
    f = m.group(2); fp = os.path.join(out, f)
    return m.group(1) + f + ("?v=" + _h(fp) if os.path.isfile(fp) else (m.group(3) or "")) + '"'
s = re.sub(r'((?:src|href)="\./)([^"?]+\.(?:js|css))(\?v=[^"]*)?"', _stamp, s)
_all = hashlib.sha256()
for dp, dn, fn in sorted(os.walk(out)):
    dn.sort()
    for f in sorted(fn):
        rel = os.path.relpath(os.path.join(dp, f), out)
        if rel in ("sw.js", "index.html", "bars.json", "places.json") or rel.startswith(("places/", "buildings/", "buildings3d/")): continue
        _all.update(rel.encode() + b"\0" + open(os.path.join(dp, f), "rb").read())
_sw = os.path.join(out, "sw.js")
if os.path.exists(_sw):
    _t = open(_sw, encoding="utf-8").read()
    _t = re.sub(r'^var VERSION = "[^"]*";', 'var VERSION = "olnu-b%s";' % _all.hexdigest()[:9], _t, count=1, flags=re.M)
    open(_sw, "w", encoding="utf-8").write(_t)
s = re.sub(r'\s*<link[^>]+rel="manifest"[^>]*>', "", s)                       # not installable
s = re.sub(r"<title>(?!BETA)", "<title>BETA · ", s, count=1)
head = ('<meta name="robots" content="noindex,nofollow">\n'
  '<script src="./beta.js"></script>\n'
  '<style id="beta-css">#olnu-beta{position:fixed;z-index:2147483000;top:calc(env(safe-area-inset-top,0px) + 3px);left:50%;transform:translateX(-50%);'
  'font:700 10px/14px system-ui,sans-serif;letter-spacing:.08em;padding:1px 7px;border-radius:7px;background:#f5a623;color:#241300;'
  'pointer-events:none;opacity:.92;box-shadow:0 1px 4px rgba(0,0,0,.5)}</style>\n')
if 'name="robots"' not in s:   # after <meta charset> (must stay in the first bytes) and the CSP meta when they exist
    m = list(re.finditer(r'<meta[^>]+(charset=|http-equiv="Content-Security-Policy")[^>]*>\s*', s[:4000], re.I))
    at = m[-1].end() if m else re.search(r"<head[^>]*>\s*", s).end()
    s = s[:at] + head + s[at:]
badge = '<div id="olnu-beta" aria-hidden="true">BETA' + (" " + html.escape(sha) if sha else "") + "</div>"
if 'id="olnu-beta"' not in s: s = re.sub(r"(<body[^>]*>)", r"\1\n" + badge, s, count=1)
s = s.replace("https://tunela.github.io/Beer-map/docs/", "https://tunela.github.io/pintsnow-beta/")   # link preview shows the beta's own new image
s = re.sub(r'(og-image\.png)(\?v=[^"]*)?"', r'\1?v=pn1"', s)   # new URL = chat apps fetch the new PintsNow image, not a cached old one
open(p, "w", encoding="utf-8").write(s)
for f in ("manifest.webmanifest",):   # nothing links it any more; remove so no store / browser picks it up
    try: os.remove(os.path.join(out, f))
    except FileNotFoundError: pass
# the app's CSP allows only 'self' scripts: the beta setup is a file. It skips the first-visit "install the app" card.
open(os.path.join(out, "beta.js"), "w").write('try{localStorage.setItem("olnu.inst1",String(Date.now()));localStorage.setItem("olnu.beta",%r)}catch(e){}\n' % sha)
open(os.path.join(out, ".nojekyll"), "w").close()
print("beta build ok", sha)
