"""The showcase bundler: packs the two adapters' outputs into docs/showcase/ and, with --mirror, copies that folder
elsewhere for publishing. Standard library only (plus sc_contract next to it), so any Python 3.10+ runs it.

    python -B showcase/gen/bundle.py                     bundle, check (and assemble index.html if page/ has a
                                                         shell.html)
    python -B showcase/gen/bundle.py --check-only        re-check an existing bundle folder, write nothing
    options: --from426 DIR --from368 DIR (adapter outputs, default showcase/build/426 and /368), --out DIR (default
             docs/showcase), --mirror DIR (default none), --page auto|skip|require, --no-decode, --strict-page

What it writes (API.md sections 2 and 9):
    manifest.json, core-S.json, build-S-B.json, extras-S.json, data-S-B.json, models-S.js (copied from the adapter
    folders, unchanged), strip.json + optics_heatmaps.png (the light-strip card's assets), and index.html once the
    page exists (page/shell.html + viewer.js + strip3d.js + cards/<id>.html/.js, see assemble_page).

What it checks (every check is an error unless marked as a warning):
    - every adapter file passes sc_contract.validate_file (GLBs decoded); every build's data passes validate_data
      (strict, with the node cross-check against core + build + extras, less the build's meta.absent_nodes). The
      4.26 has two more builds (sc_contract.EXTRA_BUILDS: 'cl', chinless, since 2026-10-04; 'lc', light-strip
      chinless, since 2026-10-07; neither has bottom keys)
    - the core / per-build split three ways: the model files (core and build disjoint; a node in both builds' build
      files must differ by hash, except display nodes), the project's out/shared-parts.json (its two schemas), and
      the out/standard vs out/light-strip STL bytes of every printed-part node; plus the adapters' own reports
    - the download zip: models-S.js parses, the zip tests clean, its name matches data.downloads, every
      downloads.groups file is in it with the same bytes, it holds both tubs (and both 3.68 key sets), a coupon,
      ROD.txt, the PCBA dummy and a README, no file twice, and every file of the size's print/4.26/ or print/3.68/
      (same CRC) but the ones left out for size (sc_contract.ZIP_NOT_SHOWN: STEP files that would take the model
      file past the 16 MB per-file limit), which must not be in it
    - adapter outputs newer than the project's out/ and the size's print folder (warning when stale)
    - every file <= 16 MB, the published set <= 64 MB, every text file ASCII, every manifest file exists with its
      bytes, sc_contract.validate_manifest and validate_bundle (one narrow waiver, see waive()), mirror identical
    - the page (when assembled): markers, one <article> per card fragment with the right data-card / data-preset,
      no inline script in fragments, SC.card ids and top-level title/order/preset/sizes/builds against CARDS,
      every data-show / data-k / needs path / data-goto resolves in every size / build the element applies to
      (data-only / data-not honoured, with each build's sc_contract.BUILD_TOKENS), unique ids, no '</script' inside inlined code, ASCII, allowed CDN hosts
"""
import argparse
import datetime as dt
import base64
import hashlib
import io
import json
import os
import re
import shutil
import sys
import zipfile
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sc_contract as C                                                   # noqa: E402

REPO = HERE.parents[1]                                                    # the repo root
# the adapters' default --out (showcase/build/<size>/, not in git)
DEFAULT_FROM = {'426': REPO / 'showcase' / 'build' / '426', '368': REPO / 'showcase' / 'build' / '368'}
DEFAULT_OUT = REPO / 'docs' / 'showcase'
DEFAULT_MIRROR = ''                                                       # none; pass --mirror DIR to publish a copy
PAGE = REPO / 'showcase' / 'page'
PROJECTS = {'426': REPO / 'enclosures' / 'case-426',                     # out/ (the builds)
            '368': REPO / 'enclosures' / 'case-368'}
PRINTS = {'426': REPO / 'print' / '4.26',                                 # build.write_print's per-part files
          '368': REPO / 'print' / '3.68'}
# the light-strip card's assets: strip.json is kept in git next to the page (no generator in tools/), the
# heatmap is tools/optics_sim.py's output in docs/images; the bundle copies both into --out
ASSETS = {'strip.json': PAGE / 'strip.json',
          'optics_heatmaps.png': REPO / 'docs' / 'images' / 'optics_heatmaps.png'}
TITLE = 'Silkscreen case'
TEXT_EXT = ('.json', '.js', '.html', '.css', '.txt', '.md', '.svg')
DISPLAY_PREFIX = ('panel_', 'ribbon_')
# printed-part node -> its STL in out/<build>/ (lid: lid_body.stl, never lid.stl, which has the side keys fused in)
def part_stl(node):
    if node == 'lid':
        return 'lid_body.stl'
    if node in ('crank_M', 'crank_T'):
        return node.replace('_', '-') + '.stl'
    if node in ('tub', 'midplate', 'gate') or node.startswith(('skey_', 'key_')):
        return node + '.stl'
    return None


# shared-parts.json names -> node names (crank_SW* are crank-M at each key: the instanced crank_M node)
def part_node(part):
    if part == 'lid_body':
        return 'lid'
    if part in ('crank-M', 'crank-T'):
        return part.replace('-', '_')
    if re.match(r'^crank_SW\d+$', part):
        return 'crank_M'
    if part in ('tub', 'midplate', 'gate') or part.startswith(('skey_', 'key_')):
        return part
    return None                                    # lid (fused copy), key-426 / key-x3*, coupons: not stage nodes


class Log:
    def __init__(self):
        self.errors, self.warnings, self.notes = [], [], []

    def err(self, msg):
        self.errors.append(msg)
        print('  ERROR', msg)

    def warn(self, msg):
        self.warnings.append(msg)
        print('  warn ', msg)

    def note(self, msg):
        self.notes.append(msg)
        print('  -', msg)

    def check(self, ok, msg):
        if not ok:
            self.err(msg)
        return ok


def sha1(b):
    return hashlib.sha1(b).hexdigest()


def dump(obj):
    return json.dumps(obj, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def mb(n):
    return f'{n / 1e6:6.2f} MB'


def is_ascii(b):
    return not any(c > 0x7F for c in b)


def iso(t):
    return dt.datetime.fromtimestamp(t).isoformat(timespec='seconds')


# ---- adapter outputs ---------------------------------------------------------------------------------------
def adapter_files(S):
    return [C.fname('core', S), C.fname('extras', S), C.fname('models', S)] + \
           [C.fname('build', S, B) for B in C.builds_of(S)] + [C.fname('data', S, B) for B in C.builds_of(S)]


def load_size(S, src, L, decode, need_report=True):
    """Read and validate one size's adapter folder. Returns {'raw': {name: bytes}, 'core', 'extras', 'build',
    'data', 'report'}."""
    print(f'\n[{S}] adapter outputs in {src}')
    out = {'raw': {}, 'build': {}, 'data': {}}
    for f in adapter_files(S):
        p = src / f
        if not L.check(p.exists(), f'{S}: {p} missing'):
            continue
        out['raw'][f] = p.read_bytes()
        E = C.validate_file(p, decode=decode)
        L.check(not E, f'{f}: ' + '; '.join(E[:6]))
    rp = src / f'adapter-{S}.json'
    out['report'] = json.loads(rp.read_text()) if rp.exists() else None
    if need_report:
        L.check(out['report'] is not None, f'{rp} missing')
    if len(out['raw']) != len(adapter_files(S)):
        return out
    js = lambda f: json.loads(out['raw'][f])                                           # noqa: E731
    out['core'], out['extras'] = js(C.fname('core', S)), js(C.fname('extras', S))
    for B in C.builds_of(S):
        out['build'][B] = js(C.fname('build', S, B))
        out['data'][B] = js(C.fname('data', S, B))
    for B in C.builds_of(S):
        D = out['data'][B]
        L.check(D['size'] == S and D['build'] == B, f'data-{S}-{B}: says size {D["size"]} build {D["build"]}')
        absent = set(D['meta'].get('absent_nodes', []))
        L.check(absent <= set(out['core']['nodes']), f'data-{S}-{B}: absent_nodes not in core: {sorted(absent - set(out["core"]["nodes"]))}')
        nodes = (set(out['core']['nodes']) - absent) | set(out['build'][B]['nodes']) | set(out['extras']['nodes'])
        E = C.validate_data(D, C.fname('data', S, B), nodes=nodes, strict=True)
        L.check(not E, f'data-{S}-{B} (strict, node cross-check): ' + '; '.join(E[:6]))
    for M, k in ((out['core'], 'core'), (out['extras'], 'extras'), *((out['build'][B], 'build') for B in C.builds_of(S))):
        L.check(M['kind'] == k and M['size'] == S, f'{S}: a {k} file says kind {M["kind"]} size {M["size"]}')
    print(f'  {len(out["raw"])} files read and validated (GLB decoded: {decode})')
    return out


# ---- the core / per-build split ----------------------------------------------------------------------------
def shared_parts(path):
    """Either project's out/shared-parts.json -> (shared names, differing names). 4.26: {part: {same, by}}, the tub
    not listed. 3.68: {rule, parts: {part: {same_files, same_solid?}}, differ: [...], tub_specific: {part: {differ}}}."""
    J = json.loads(Path(path).read_text())
    shared, differ = set(), set()
    if 'parts' in J:
        # the project's rule (build.shared_check): a part is shared on identical files OR on equal solids. Since
        # 2026-10-13 OCC's lid-minus-lid difference fails on the 3.68 (same_solid false, the whole volume left), while
        # both builds' lid files are byte-identical
        for n, v in J['parts'].items():
            (shared if v.get('same_files') or v.get('same_solid') else differ).add(n)
        differ |= set(J.get('differ', []))
        differ |= {n for n, v in J.get('tub_specific', {}).items() if v.get('differ')}
    else:
        for n, v in J.items():
            (shared if v.get('same') else differ).add(n)
    return shared, differ


def check_split(S, A, L):
    """The core / build split, three ways. Returns (parts {shared, per_build}, display {B: [...]}, notes)."""
    print(f'\n[{S}] core / per-build split')
    core, extras = set(A['core']['nodes']), set(A['extras']['nodes'])
    bn = {B: A['build'][B]['nodes'] for B in C.builds_of(S)}
    for B in C.BUILDS:
        L.check(not (core & set(bn[B])), f'{S}: nodes in core and build-{B}: {sorted(core & set(bn[B]))}')
        L.check(not (extras & set(bn[B])), f'{S}: nodes in extras and build-{B}: {sorted(extras & set(bn[B]))}')
    for B in C.EXTRA_BUILDS[S]:
        # an extra build (the 4.26 chinless) may replace a core node with its own mesh (its lid): then it must differ
        over = sorted(core & set(bn[B]))
        L.check(all(bn[B][n]['hash'] != A['core']['nodes'][n]['hash'] for n in over),
                f'{S}: build-{B} repeats a core node with the same mesh: {over}')
        L.check(not (extras & set(bn[B])), f'{S}: nodes in extras and build-{B}: {sorted(extras & set(bn[B]))}')
        ab = set(A['data'][B]['meta'].get('absent_nodes', []))
        L.check(not (ab & set(bn[B])), f'{S}: build-{B} both ships and leaves out {sorted(ab & set(bn[B]))}')
        print(f'  {B}: build file {len(bn[B])} nodes (replacing core {over}), leaves out {len(ab)} core nodes')
    L.check(not (core & extras), f'{S}: nodes in core and extras: {sorted(core & extras)}')
    std, ls = set(bn['std']), set(bn['ls'])
    odd = {n for n in std ^ ls if not n.startswith(DISPLAY_PREFIX) and not n.startswith('strip_')}
    L.check(not odd, f'{S}: per-build node sets differ outside display / strip_*: {sorted(odd)}')
    # every display node each build shows, core or per build (the 3.68's bare panel and FPC are core)
    display = {B: sorted(n for n in core | set(bn[B]) if n.startswith(DISPLAY_PREFIX)) for B in C.builds_of(S)}
    rd = (A['report'] or {}).get('display_nodes')
    if rd is not None:
        L.check(all(sorted(rd.get(B, [])) == display[B] for B in C.builds_of(S)),
                f'{S}: adapter-{S}.json display_nodes {rd} != the model files {display}')
    L.check(all(display[B] for B in C.builds_of(S)), f'{S}: a build without display nodes: {display}')
    if std != ls:
        L.note(f'{S}: per-build display nodes differ: std {display["std"]}, ls {display["ls"]}')
    for n in sorted(std & ls):
        same = bn['std'][n]['hash'] == bn['ls'][n]['hash']
        if same and n.startswith(DISPLAY_PREFIX):
            L.note(f'{S}: {n} is the same mesh in both builds but ships per build (the display set differs)')
        else:
            L.check(not same, f'{S}: {n} has the same hash in both build files: it belongs in core')
    # the adapter's own report
    rep = A['report'] or {}
    rn = rep.get('nodes', {})
    L.check(set(rn.get('core', [])) == core and set(rn.get('extras', [])) == extras
            and all(set(rn.get('build', {}).get(B, [])) == set(bn[B]) for B in C.builds_of(S)),
            f'{S}: adapter-{S}.json nodes differ from the model files')
    # shared-parts.json
    sp_path = PROJECTS[S] / 'out' / 'shared-parts.json'
    shared, differ = shared_parts(sp_path)
    for p in sorted(shared | differ):
        n = part_node(p)
        if n is None:
            continue
        if p in shared:
            L.check(n in core, f'{S}: shared-parts.json says {p} is shared, but node {n} is not in core-{S}')
        else:
            L.check(n in std and n in ls, f'{S}: shared-parts.json says {p} differs, but node {n} is not per build')
    # the STL bytes themselves (read only)
    printed = sorted(n for n in core | std | ls if part_stl(n))
    seen = 0
    for n in printed:
        a = PROJECTS[S] / 'out' / 'standard' / part_stl(n)
        b = PROJECTS[S] / 'out' / 'light-strip' / part_stl(n)
        if not L.check(a.exists() and b.exists(), f'{S}: {part_stl(n)} missing in out/standard or out/light-strip'):
            continue
        same = a.read_bytes() == b.read_bytes()
        seen += 1
        L.check(same == (n in core), f'{S}: {n}: STL bytes {"same" if same else "differ"} across builds but the '
                                     f'node is in {"core" if n in core else "build"}')
        if n == 'tub' and 'tub' not in shared | differ:
            L.note(f'{S}: tub is not listed in shared-parts.json; the STL bytes differ, so it is per build')
    per_build = sorted({p for p in differ if part_node(p)} | ({'tub'} if 'tub' in std else set()))
    parts = {'shared': sorted(shared), 'per_build': per_build}
    rp = rep.get('parts')
    L.check(rp is not None and sorted(rp['shared']) == parts['shared'] and sorted(rp['per_build']) == parts['per_build'],
            f'{S}: adapter parts {rp} != shared-parts.json {parts}')
    print(f'  core {len(core)}, build std {len(std)} / ls {len(ls)}, extras {len(extras)}; '
          f'{seen} printed-part nodes checked against the STL bytes and shared-parts.json')
    return parts, display


# ---- downloads ---------------------------------------------------------------------------------------------
def check_models(S, A, L):
    print(f'\n[{S}] download zip')
    f = C.fname('models', S)
    raw = A['raw'][f]
    txt = raw.decode('ascii')
    pre = 'window.SC_MODELS='
    if not L.check(txt.startswith(pre) and txt.rstrip().endswith(';'), f'{f}: not "window.SC_MODELS={{...}};"'):
        return {}
    O = json.loads(txt[len(pre):].rstrip().rstrip(';'))
    zb = base64.b64decode(O['b64'])
    L.check(len(zb) == O.get('zip_bytes'), f'{f}: zip_bytes {O.get("zip_bytes")} != decoded {len(zb)}')
    Z = zipfile.ZipFile(io.BytesIO(zb))
    L.check(Z.testzip() is None, f'{f}: zip CRC test failed')
    info = {i.filename: i for i in Z.infolist() if not i.is_dir()}
    names = list(info)
    for B in C.builds_of(S):
        dl = A['data'][B]['downloads']
        L.check(dl['zip'] == O.get('zip'), f'data-{S}-{B}: downloads.zip {dl["zip"]} != {O.get("zip")}')
        L.check(dl['zip_bytes'] == len(zb), f'data-{S}-{B}: downloads.zip_bytes {dl["zip_bytes"]} != {len(zb)}')
        if dl['js_bytes'] != len(raw):
            L.warn(f'data-{S}-{B}: downloads.js_bytes {dl["js_bytes"]} != {f} {len(raw)} bytes '
                   f'(the page should show manifest.files["{f}"].bytes)')
        for g in dl['groups']:
            for x in g['files']:
                i = info.get(x['path'])
                L.check(i is not None and i.file_size == x['bytes'],
                        f'data-{S}-{B}: downloads {g["id"]} {x["path"]} ({x["bytes"]} B) not in the zip with those bytes')
    # one folder layout in both sizes (sc_contract.ZIP_DIRS), and every zip entry in a group
    for n in names:
        L.check(n in C.ZIP_TOP or any(n.startswith(d) and '/' not in n[len(d):] for d in C.ZIP_DIRS.values()),
                f'{f}: {n} is outside the layout ({", ".join(C.ZIP_DIRS.values())}, README.txt, ROD.txt)')
    grouped = {x['path'] for g in A['data']['std']['downloads']['groups'] for x in g['files']}
    L.check(set(names) - grouped <= {A['data']['std']['downloads']['readme']},
            f'{f}: zip entries in no download group: {sorted(set(names) - grouped)}')
    if any(A['data'][B]['downloads'] != A['data']['std']['downloads'] for B in C.builds_of(S)):
        L.warn(f'{S}: downloads blocks differ between the builds\' data (one zip per size)')
    low = [n.lower() for n in names]
    want = {'standard tub': lambda n: 'tub-standard' in n, 'light-strip tub': lambda n: 'tub-light-strip.' in n,
            'coupon': lambda n: 'coupon' in n, 'ROD.txt': lambda n: n.endswith('rod.txt'),
            'PCBA dummy': lambda n: 'pcba-dummy' in n, 'README': lambda n: n.endswith('readme.txt')}
    if 'cl' in C.builds_of(S):
        want.update({'chinless tub': lambda n: 'tub-chinless' in n, 'chinless lid': lambda n: 'lid-chinless' in n})
    if 'lc' in C.builds_of(S):
        want.update({'light-strip chinless tub': lambda n: 'tub-light-strip-chinless.' in n})
    if S == '368':
        want.update({'standard key set': lambda n: 'key-x3std' in n, 'light-strip key set': lambda n: 'key-x3ls' in n})
    for w, fn in want.items():
        L.check(any(fn(n) for n in low), f'{f}: no {w} in the zip')
    # no file twice. A pair that print/<size>/ itself holds under two names with the same bytes would be the project's
    # choice, not a part duplicated per build: a note (none since test 2: the drag coupon's keys are gone).
    pr = PRINTS[S]
    base = lambda n: n.rsplit('/', 1)[-1]                                                # noqa: E731
    seen = {}
    for n, i in info.items():
        k = (i.CRC, i.file_size)
        if k in seen:
            a, b = pr / base(seen[k]), pr / base(n)
            if a.name != b.name and a.exists() and b.exists() and a.read_bytes() == b.read_bytes():
                L.note(f'{f}: {n} has the same bytes as {seen[k]}; print/{pr.name}/ ships both names, so the zip does too')
            else:
                L.err(f'{f}: {n} duplicates {seen[k]} (shared parts go in once)')
        seen[k] = n
    # every file of the size's print folder is in the zip, same content
    by_base = {}
    for n, i in info.items():
        by_base.setdefault(base(n), []).append(i)
    missing, not_shown = [], []
    for p in sorted(pr.iterdir()):
        if not p.is_file():
            continue
        if C.ZIP_NOT_SHOWN.get(S) and p.name.startswith(C.ZIP_NOT_SHOWN[S]):
            not_shown.append(p.name)                 # left out for size (sc_contract.ZIP_NOT_SHOWN)
            if any(base(n) == p.name for n in info):
                L.err(f'{f}: {p.name} is in the zip, but sc_contract.ZIP_NOT_SHOWN leaves it out')
            continue
        crc = zipfile.crc32(p.read_bytes()) & 0xFFFFFFFF
        if not any(i.CRC == crc and i.file_size == p.stat().st_size for i in by_base.get(p.name, [])):
            missing.append(p.name)
    L.check(not missing, f'{f}: print/{pr.name}/ files not in the zip (or changed since): {missing}')
    if not_shown:
        L.note(f'{f}: left out of the zip, they would take it past the per-file limit (sc_contract.ZIP_NOT_SHOWN): '
               f'{not_shown}')
    total = sum(i.file_size for i in info.values())
    print(f'  {O.get("zip")}: {len(names)} files, {mb(total)} raw, zip {mb(len(zb))}, js {mb(len(raw))}; '
          f'print/{pr.name}/ fully covered: {not missing}')
    return {'zip': O.get('zip'), 'zip_bytes': len(zb), 'entries': len(names), 'raw_bytes': total}


def check_fresh(S, A, L):
    """Adapter outputs must be newer than the project's out/ and the size's print folder."""
    gens = [A['data'][B]['meta']['source'].get('generated') for B in C.builds_of(S)]
    gen = min(g for g in gens if g)
    newest, what = 0.0, None
    roots = [PROJECTS[S] / 'out' / C.BUILD_DIRS[B] for B in C.builds_of(S)] + [PRINTS[S]]
    for r in roots:
        for p in r.rglob('*'):
            if p.is_file() and 'showcase' not in p.parts and p.stat().st_mtime > newest:
                newest, what = p.stat().st_mtime, p
    sp = PROJECTS[S] / 'out' / 'shared-parts.json'
    if sp.stat().st_mtime > newest:
        newest, what = sp.stat().st_mtime, sp
    if iso(newest) > gen:
        L.warn(f'{S}: the adapter output ({gen}) is older than {what} ({iso(newest)}): rerun the adapter')
    else:
        print(f'  [{S}] fresh: adapter {gen} >= newest project output {iso(newest)}')
    return gen


# ---- the page hook -----------------------------------------------------------------------------------------
MARKERS = ('BOOT', 'CARDS', 'CARD_SCRIPTS', 'VIEWER', 'STRIP3D')
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}
ONLY_TOKENS = set(C.SIZES) | set(C.ALL_BUILDS)
CDN_OK = ('https://cdn.jsdelivr.net/npm/', 'https://cdnjs.cloudflare.com/')
FONT_OK = ('https://fonts.googleapis.com/', 'https://fonts.gstatic.com/')


def marker(n):
    return f'<!--SC:{n}-->'


class Bindings(HTMLParser):
    """Collects [data-k], [data-show], [data-goto], ids and <article>s with the data-only tokens in force."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.items, self.ids, self.articles, self.scripts = [], [], [], [], 0

    def only(self):
        t = set()
        for _, tok, _n in self.stack:
            t |= tok
        return t

    def nots(self):
        t = set()
        for _, _o, n in self.stack:
            t |= n
        return t

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        tok = set((a.get('data-only') or '').split())
        nt = set((a.get('data-not') or '').split())          # hidden when any token is the size or the build
        here = self.only() | tok
        for k in ('data-k', 'data-show', 'data-goto'):
            if a.get(k):
                self.items.append((k, a[k], frozenset(here), frozenset(self.nots() | nt)))
        if a.get('id'):
            self.ids.append(a['id'])
        if tag == 'article':
            self.articles.append(a)
        if tag == 'script':
            self.scripts += 1
        if tag not in VOID and not tag.endswith('/'):
            self.stack.append((tag, tok, nt))

    def handle_startendtag(self, tag, attrs):
        a = dict(attrs)
        tok = set((a.get('data-only') or '').split())
        nt = set((a.get('data-not') or '').split())
        for k in ('data-k', 'data-show', 'data-goto'):
            if a.get(k):
                self.items.append((k, a[k], frozenset(self.only() | tok), frozenset(self.nots() | nt)))
        if a.get('id'):
            self.ids.append(a['id'])

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                return


def scan_card_call(js):
    """The top-level keys of the object literal in SC.card({...}) whose values are simple literals, and the string
    list of needs: [...]. A small scanner that skips strings, template literals and comments."""
    m = re.search(r'SC\.card\s*\(\s*\{', js)
    if not m:
        return None
    i, n, depth, out = m.end(), len(js), 0, {}
    while i < n:
        c = js[i]
        if c in '\'"`':
            q, i = c, i + 1
            while i < n and js[i] != q:
                i += 2 if js[i] == '\\' else 1
            i += 1
            continue
        if js.startswith('//', i):
            i = js.find('\n', i) if js.find('\n', i) >= 0 else n
            continue
        if js.startswith('/*', i):
            i = js.find('*/', i) + 2 if js.find('*/', i) >= 0 else n
            continue
        if c in '{[(':
            depth += 1
        elif c in '}])':
            if depth == 0:
                break
            depth -= 1
        elif depth == 0:
            k = re.match(r'([A-Za-z_]\w*)\s*:\s*', js[i:])
            if k and (i == 0 or not re.match(r'[\w.]', js[i - 1])):
                key, j = k.group(1), i + k.end()
                v = re.match(r"'([^'\\]*)'|\"([^\"\\]*)\"|(-?\d+(?:\.\d+)?)|(null|true|false)\b", js[j:])
                if v:
                    out[key] = v.group(1) if v.group(1) is not None else v.group(2) if v.group(2) is not None else \
                        float(v.group(3)) if v.group(3) else {'null': None, 'true': True, 'false': False}[v.group(4)]
                elif js[j] == '[' and key in ('needs', 'sizes', 'builds'):
                    e = js.find(']', j)
                    out[key] = re.findall(r"'([^'\\]*)'|\"([^\"\\]*)\"", js[j:e])
                    out[key] = [a or b for a, b in out[key]]
                i = j
                continue
        i += 1
    return out


def placeholder(card):
    """The <article> for a card whose fragments do not exist yet (non-strict builds only): its title from CARDS and
    a Show in 3D button for its preset. The shell treats it like any card without SC.card (no render)."""
    esc = lambda s: s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace("'", '&#x2019;')
    pre = card.get('preset')
    btn = (f'\n  <div class="btns"><button class="btn show3d" type="button" data-show="{pre}">Show in 3D</button></div>'
           if pre else '')
    return (f'<article class="mech sc-placeholder" data-card="{card["id"]}"' + (f' data-preset="{pre}"' if pre else '') +
            f'>\n  <div class="mech-head">\n    <h2>{esc(card["title"])}</h2>\n'
            f'    <p class="thesis">This card is still being written.</p>\n  </div>{btn}\n</article>')


def only_matches(tokens, nots, S, B):
    """data-only / data-not as the shell applies them (each build answers to its sc_contract.BUILD_TOKENS)."""
    return C.tokens_match(tokens, nots, S, B)


def assemble_page(mf, datas, L, strict=False):
    """page/shell.html + viewer.js + strip3d.js + cards/<id>.html/.js -> index.html text, or None on errors.

    The shell holds each marker exactly once (as an HTML comment on its own):
      <!--SC:BOOT-->          <script>window.SC_BOOT={generated, manifest}</script>: the manifest inlined (saves a
                              fetch; cache-bust data fetches with manifest.files[f].sha1)
      <!--SC:CARDS-->         the card fragments' <article>s, in sc_contract.CARDS order
      <!--SC:VIEWER-->        <script type="module"> viewer.js </script>
      <!--SC:STRIP3D-->       <script type="module"> strip3d.js </script>
      <!--SC:CARD_SCRIPTS-->  one classic <script data-card-js="<id>"> per card: the card's js in an IIFE with a
                              try / catch that logs and calls SC.cardError(id, e) when the shell defines it
    Put CARD_SCRIPTS after the page core (the script that defines window.SC)."""
    n0 = len(L.errors)
    shell_p = PAGE / 'shell.html'
    shell = shell_p.read_text(encoding='ascii', errors='strict') if is_ascii(shell_p.read_bytes()) else None
    if not L.check(shell is not None, 'page/shell.html is not ASCII'):
        return None
    for mk in MARKERS:
        L.check(shell.count(marker(mk)) == 1, f'shell.html: marker {marker(mk)} must appear exactly once '
                                              f'(found {shell.count(marker(mk))})')
    if 'three@0.169' not in shell:
        L.warn('shell.html: no importmap entry for three@0.169')
    for url in re.findall(r'<script[^>]+src="([^"]+)"', shell):
        L.check(url.startswith(CDN_OK) or not url.startswith('http'), f'shell.html: script from {url} (cdnjs / jsdelivr only)')
    for url in re.findall(r'<link[^>]+href="(https?://[^"]+)"', shell):
        L.check((url.rstrip('/') + '/').startswith(FONT_OK + CDN_OK), f'shell.html: stylesheet / link from {url}')
    mods = {}
    for mname in ('viewer.js', 'strip3d.js'):
        p = PAGE / mname
        if mname == 'strip3d.js' and not p.exists() and not strict:
            L.warn('page/strip3d.js missing: the STRIP3D marker is left empty (the strip card step adds it)')
            continue
        if not L.check(p.exists(), f'page/{mname} missing'):
            continue
        b = p.read_bytes()
        L.check(is_ascii(b), f'page/{mname}: non-ASCII bytes (use \\u escapes)')
        t = b.decode('ascii', 'replace')
        L.check(not re.search(r'</script', t, re.I), f"page/{mname}: contains '</script' (write '<\\/script')")
        mods[mname] = t
    combos = [(S, B) for S in C.SIZES for B in C.builds_of(S)]
    arts, scripts, missing, ids = [], [], [], []
    sb = Bindings()
    sb.feed(shell)
    ids += sb.ids
    for it in sb.items:                                   # the shell's own bindings apply everywhere they show
        check_binding('shell', it, combos, datas, L)
    for card in C.CARDS:
        cid = card['id']
        hp, jp = PAGE / 'cards' / f'{cid}.html', PAGE / 'cards' / f'{cid}.js'
        if not hp.exists() and not jp.exists():
            missing.append(cid)
            if not strict:                                # a placeholder keeps the tour's order and visibility testable
                h = placeholder(card)
                P = Bindings()
                P.feed(h)
                for it in P.items:
                    check_binding(f'card {cid} (placeholder)', it, [x for x in combos if C.card_applies(card, *x)]
                                  or [(S, b) for S in C.SIZES for b in C.card_home(card) if b in C.builds_of(S)], datas, L)
                arts.append(f'<!-- card {cid} (placeholder) -->\n{h}\n')
            continue
        if not L.check(hp.exists() and jp.exists(), f'card {cid}: needs both cards/{cid}.html and cards/{cid}.js'):
            continue
        hb, jb = hp.read_bytes(), jp.read_bytes()
        L.check(is_ascii(hb) and is_ascii(jb), f'card {cid}: non-ASCII bytes')
        h, j = hb.decode('ascii', 'replace').strip(), jb.decode('ascii', 'replace')
        P = Bindings()
        P.feed(h)
        L.check(len(P.articles) == 1 and h.startswith('<article') and h.endswith('</article>'),
                f'card {cid}: the fragment must be exactly one <article>')
        if P.articles:
            a = P.articles[0]
            L.check(a.get('data-card') == cid and 'mech' in (a.get('class') or '').split(),
                    f'card {cid}: <article class="mech" data-card="{cid}"> expected, got {a}')
            L.check((a.get('data-preset') or None) == card['preset'],
                    f'card {cid}: data-preset {a.get("data-preset")!r} != CARDS preset {card["preset"]!r}')
        L.check(P.scripts == 0, f'card {cid}: inline <script> in the fragment (put it in cards/{cid}.js)')
        bad_ids = [i for i in P.ids if not (i.startswith(cid + '-') or i.startswith('dw-' + cid))]
        if bad_ids:
            L.warn(f'card {cid}: ids not prefixed with the card id: {bad_ids[:6]}')
        ids += P.ids
        cc = [x for x in combos if C.card_applies(card, *x) and not C.card_away(card, x[1])]   # away: heading only
        if card.get('enter_build'):                       # it shows (in place) on its home builds only
            cc = [(S, b) for S in C.SIZES for b in C.card_home(card) if b in C.builds_of(S)]
        for it in P.items:
            check_binding(f'card {cid}', it, cc, datas, L)
        call = scan_card_call(j)
        if L.check(call is not None, f'card {cid}: no SC.card({{...}}) call in cards/{cid}.js'):
            L.check(call.get('id') == cid, f'card {cid}: SC.card id {call.get("id")!r}')
            for k in ('title', 'order', 'preset', 'sizes', 'builds'):
                if k in call:
                    want = card.get(k)
                    got = call[k]
                    if k == 'order':
                        got = int(got)
                    L.check(got == want or (k in ('sizes', 'builds') and not got and not want),
                            f'card {cid}: SC.card {k} {got!r} != CARDS {want!r} (one source for the tour)')
            for path in call.get('needs', []):
                for S, B in cc:
                    try:
                        v = C._get(datas[S][B], path)
                        L.check(v is not None and v != '', f'card {cid}: needs {path!r} empty in data-{S}-{B}')
                    except KeyError:
                        L.err(f'card {cid}: needs {path!r} does not resolve in data-{S}-{B}')
        L.check(not re.search(r'</script', j, re.I), f"card {cid}: js contains '</script'")
        arts.append(f'<!-- card {cid} -->\n{h}\n')
        scripts.append(f'<script data-card-js="{cid}">(function(){{try{{\n{j.rstrip()}\n}}catch(e){{'
                       f"console.error('[card {cid}]',e);if(window.SC&&SC.cardError)SC.cardError('{cid}',e);}}}})();"
                       f'</script>\n')
    dup = sorted({i for i in ids if ids.count(i) > 1})
    L.check(not dup, f'page: duplicate ids {dup[:8]}')
    if missing:
        (L.err if strict else L.warn)(f'page: cards without fragments ({"an error with --strict-page" if strict else "placeholders"}): {missing}')
    if len(L.errors) > n0:
        return None
    boot = {'generated': mf['generated'], 'manifest': mf}
    html = shell
    rep = {'BOOT': '<script>window.SC_BOOT=' + dump(boot).replace('</', '<\\/') + ';</script>',
           'CARDS': ''.join(arts),
           'VIEWER': '<script type="module">\n' + mods.get('viewer.js', '') + '\n</script>',
           'STRIP3D': '<script type="module">\n' + mods.get('strip3d.js', '') + '\n</script>',
           'CARD_SCRIPTS': ''.join(scripts)}
    for k, v in rep.items():
        html = html.replace(marker(k), v)
    L.check(is_ascii(html.encode('ascii', 'replace')) and all(ord(c) < 0x80 for c in html), 'index.html: non-ASCII')
    print(f'  page: {len(arts)} cards, {len(missing)} missing, index.html {mb(len(html))}')
    return html


def check_binding(where, it, combos, datas, L):
    kind, val, tokens, nots = it
    unknown = [t for t in tokens | nots if t not in ONLY_TOKENS]
    if unknown:
        L.warn(f'{where}: data-only / data-not tokens {unknown} (known: {sorted(ONLY_TOKENS)})')
    for S, B in combos:
        if not only_matches(tokens, nots, S, B):
            continue
        D = datas[S][B]
        if kind == 'data-show':
            L.check(val in D['presets'], f'{where}: data-show {val!r} is not a preset in data-{S}-{B}')
        elif kind == 'data-goto':
            L.check(val in C.CARD_IDS, f'{where}: data-goto {val!r} is not a card')
            return
        else:
            try:
                v = C._get(D, val)
                L.check(v is not None and v != '', f'{where}: data-k {val!r} empty in data-{S}-{B}')
            except KeyError:
                L.err(f'{where}: data-k {val!r} does not resolve in data-{S}-{B}')


# ---- writing -----------------------------------------------------------------------------------------------
def put(folder, name, data):
    """Write bytes unless the file already holds them (keeps mtimes). Returns True if written."""
    p = folder / name
    if p.exists() and p.read_bytes() == data:
        return False
    tmp = folder / (name + '.tmp')
    tmp.write_bytes(data)
    os.replace(tmp, p)
    return True


def waive(E, mf):
    """validate_manifest requires both builds to carry the same per-build nodes (bar strip_*). The 4.26 builds
    differ in their display nodes (std: FT01C with touch + light layers and 3 ribbons; ls: plain GDEY0426T82, one
    FPC), which API.md section 7 asks the contract to allow. Until sc_contract does, drop exactly that error when
    the difference is only panel_* / ribbon_* / strip_* nodes."""
    keep, waived = [], []
    for e in E:
        m = re.match(r'^manifest\.nodes\.(\d+): both builds must have the same per-build nodes', e)
        if m:
            N = mf['nodes'][m.group(1)]['build']
            diff = set(N['std']) ^ set(N['ls'])
            if all(n.startswith(DISPLAY_PREFIX + ('strip_',)) for n in diff):
                waived.append(e)
                continue
        keep.append(e)
    return keep, waived


def build_manifest(A, parts, display, zips, gens, files):
    load, nodes = {}, {}
    for S in C.SIZES:
        load[S] = {'core': C.fname('core', S), 'extras': C.fname('extras', S), 'models': C.fname('models', S),
                   'build': {B: C.fname('build', S, B) for B in C.builds_of(S)},
                   'data': {B: C.fname('data', S, B) for B in C.builds_of(S)}}
        nodes[S] = {'core': sorted(A[S]['core']['nodes']), 'extras': sorted(A[S]['extras']['nodes']),
                    'build': {B: sorted(A[S]['build'][B]['nodes']) for B in C.builds_of(S)}}
        ab = {B: A[S]['data'][B]['meta']['absent_nodes'] for B in C.builds_of(S) if A[S]['data'][B]['meta'].get('absent_nodes')}
        if ab:
            nodes[S]['absent'] = ab
    sizes = {}
    for S in C.SIZES:
        D = A[S]['data']['std']
        sizes[S] = {'label': C.SIZE_LABELS[S], 'build_diff': A[S]['report']['build_diff'], 'builds': list(C.builds_of(S)),
                    **({'build_diff_by': A[S]['report']['build_diff_by']} if A[S]['report'].get('build_diff_by') else {}),
                    'side_keys': len(D['meta']['side_keys']), 'project': D['meta']['source'].get('project'),
                    'adapter_generated': gens[S], 'zip': zips[S].get('zip'), 'zip_bytes': zips[S].get('zip_bytes'),
                    'display_nodes': display[S],
                    'panel': {B: A[S]['data'][B]['meta']['panel']['label'] for B in C.builds_of(S)}}
    first = {S: {B: sum(files[f]['bytes'] for f in (load[S]['core'], load[S]['build'][B], load[S]['data'][B]))
                 for B in C.builds_of(S)} for S in C.SIZES}
    allb = [B for B in C.ALL_BUILDS if any(B in C.builds_of(S) for S in C.SIZES)]
    return {'schema': C.SCHEMA, 'generated': max(gens.values()), 'title': TITLE, 'defaults': dict(C.DEFAULTS),
            'sizes': sizes, 'builds': {B: {'label': C.BUILD_LABELS[B], 'dir': C.BUILD_DIRS[B],
                                           **({'note': C.BUILD_NOTES[B]} if B in C.BUILD_NOTES else {}),
                                           'tokens': list(C.BUILD_TOKENS[B])} for B in allb},
            'variants': {'T': 'crank-T + SHOU HAN TS365ZJ (every JLC board)', 'M': 'crank-M + APEM MJTP1117 boards'},
            'groups': C.GROUPS, 'cards': C.CARDS, 'files': files, 'load': load, 'nodes': nodes, 'parts': parts,
            'assets': {'strip': 'strip.json', 'optics': 'optics_heatmaps.png'}, 'first_paint_bytes': first}


def file_entry(name, data, kind=None, **kw):
    k = kind or C.kind_of(name)
    e = {'bytes': len(data), 'kind': k, 'sha1': sha1(data)}
    e.update({a: b for a, b in kw.items() if b is not None})
    return e


# ---- main --------------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--from426', default=str(DEFAULT_FROM['426']))
    ap.add_argument('--from368', default=str(DEFAULT_FROM['368']))
    ap.add_argument('--out', default=str(DEFAULT_OUT))
    ap.add_argument('--mirror', default=str(DEFAULT_MIRROR))
    ap.add_argument('--page', choices=('auto', 'skip', 'require'), default='auto')
    ap.add_argument('--strict-page', action='store_true', help='a card without fragments is an error')
    ap.add_argument('--no-decode', action='store_true', help='skip decoding the GLBs in validation')
    ap.add_argument('--check-only', action='store_true', help='check --out as it is; write nothing')
    a = ap.parse_args()
    L = Log()
    out = Path(a.out)
    decode = not a.no_decode
    src = {'426': Path(a.from426), '368': Path(a.from368)}
    if a.check_only:
        src = {S: out for S in C.SIZES}
    t0 = dt.datetime.now()
    print(f'bundle.py {t0.isoformat(timespec="seconds")}  out={out}  mirror={a.mirror or "-"}')

    A, parts, display, zips, gens = {}, {}, {}, {}, {}
    mraw = (out / 'manifest.json').read_bytes() if a.check_only else None
    for S in C.SIZES:
        A[S] = load_size(S, src[S], L, decode, need_report=not a.check_only)
        if a.check_only:                        # the manifest stands in for the adapter report
            m0 = json.loads(mraw)
            A[S]['report'] = {'nodes': m0['nodes'][S], 'parts': m0['parts'][S],
                              'build_diff': m0['sizes'][S]['build_diff'], 'build_diff_by': m0['sizes'][S].get('build_diff_by'),
                              'files': {f: e for f, e in m0['files'].items() if e.get('size') == S}}
    if L.errors:
        return finish(L, 'adapter outputs failed validation')
    for S in C.SIZES:
        parts[S], display[S] = check_split(S, A[S], L)
        zips[S] = check_models(S, A[S], L)
        gens[S] = check_fresh(S, A[S], L)
    print('\n[both sizes]')
    for B in C.BUILDS:
        Ek = C.cross_check_keys(A['426']['data'][B]['keys'], A['368']['data'][B]['keys'])
        L.check(not Ek, f'{B}: the sizes disagree on the switches: ' + '; '.join(Ek))
    dn = {S: C.download_names(A[S]['data']['std']['downloads'], S) for S in C.SIZES}
    alln = [n for S in C.SIZES for n in dn[S].values()]
    L.check(len(set(alln)) == len(alln), f'download file names repeat: {dn}')
    print(f'  switch geometry and force tables agree; {len(alln)} download names, all different')

    files = {}
    blobs = {}
    for S in C.SIZES:
        for f, b in A[S]['raw'].items():
            k = C.kind_of(f)
            m = C.FILE_RE[k].match(f)
            blobs[f] = b
            files[f] = file_entry(f, b, size=S, build=m.group(2) if k in ('build', 'data') else None)
    print('\n[assets]')
    for name, p in ASSETS.items():
        p = out / name if a.check_only else p
        if not L.check(p.exists(), f'asset {p} missing'):
            continue
        b = p.read_bytes()
        if name.endswith('.json'):
            L.check(is_ascii(b), f'{name}: non-ASCII')
            J = json.loads(b)
            L.check(all(k in J for k in ('outline', 'leds', 'panel', 'fingers')), f'{name}: not the strip geometry')
        else:
            L.check(b[:8] == b'\x89PNG\r\n\x1a\n', f'{name}: not a PNG')
        blobs[name] = b
        files[name] = file_entry(name, b, kind='asset')
        print(f'  {name}: {len(b)} B from {p}')

    if a.check_only:
        mf = json.loads(mraw)
        L.check({f: {k: v for k, v in e.items() if k in ('bytes', 'sha1')} for f, e in files.items()} ==
                {f: {k: v for k, v in e.items() if k in ('bytes', 'sha1')} for f, e in mf['files'].items()},
                'manifest.files does not match the folder')
    else:
        for S in C.SIZES:
            for f in adapter_files(S):
                L.check(A[S]['report']['files'].get(f, {}).get('sha1') == files[f]['sha1'],
                        f'{S}: {f} sha1 differs from adapter-{S}.json (an adapter rerun in progress?)')
        mf = build_manifest(A, parts, display, zips, gens, files)
    mtext = mraw if a.check_only else dump(mf).encode('ascii')
    E = C.validate_manifest(mf)
    E, waived = waive(E, mf)
    L.check(not E, 'manifest: ' + '; '.join(E))
    for w in waived:
        L.warn('waived (contract fix pending, see waive()): ' + w)
    if L.errors:
        return finish(L, 'not written')

    # ---- the page hook
    html = None
    datas = {S: A[S]['data'] for S in C.SIZES}
    if a.page != 'skip' and (PAGE / 'shell.html').exists():
        print('\n[page]')
        html = assemble_page(mf, datas, L, strict=a.strict_page)
        if html is None:
            return finish(L, 'page assembly failed; nothing written')
    elif a.page == 'require':
        L.err(f'--page require: {PAGE / "shell.html"} does not exist')
        return finish(L, 'no page')
    else:
        print(f'\n[page] {PAGE / "shell.html"} not there yet: data only (index.html left as it is)')

    # ---- limits over the published set
    pub = dict(blobs)
    pub['manifest.json'] = mtext
    if html is not None:
        pub['index.html'] = html.encode('ascii')
    for n, b in pub.items():
        L.check(len(b) <= C.LIMITS['file_bytes'], f'{n}: {len(b)} bytes > 16 MB')
        if n.endswith(TEXT_EXT):
            L.check(is_ascii(b), f'{n}: non-ASCII bytes')
    total = sum(len(b) for b in pub.values())
    L.check(total <= C.LIMITS['version_bytes'], f'published set {total} bytes > 64 MB')
    if L.errors:
        return finish(L, 'limits; nothing written')

    # ---- write (manifest last, so it only ever names files that exist)
    if not a.check_only:
        out.mkdir(parents=True, exist_ok=True)
        wrote = [n for n, b in pub.items() if n != 'manifest.json' and put(out, n, b)]
        if put(out, 'manifest.json', mtext):
            wrote.append('manifest.json')
        print(f'\n[write] {out}: {len(wrote)} files written, {len(pub) - len(wrote)} unchanged')
    stale = sorted(p.name for p in out.iterdir() if p.is_file() and p.name not in pub
                   and not (p.name == 'index.html' and html is None))
    if stale and html is not None and not a.check_only:
        for n in stale:
            (out / n).unlink()
        L.note(f'pruned stale files from {out} (the old page is replaced): {stale}')
    elif stale:
        L.note(f'{out} still holds files outside the bundle (pruned once index.html is assembled): {stale}')
    if html is None and (out / 'index.html').exists():
        L.note(f'{out / "index.html"} is still the previous page; the shell step replaces it')

    # ---- whole-bundle validation (reads back what is on disk)
    print('\n[validate_bundle]')
    E, waived = waive(C.validate_bundle(out, decode=decode), mf)
    L.check(not E, 'validate_bundle: ' + '; '.join(E[:8]))
    for n, b in pub.items():
        p = out / n
        L.check(p.exists() and sha1(p.read_bytes()) == sha1(b), f'{out}: {n} on disk differs from the bundle')
    print(f'  {"OK" if not E else "FAILED"} ({len(waived)} waived)')

    # ---- mirror
    if a.mirror and not a.check_only:
        mir = Path(a.mirror)
        mir.mkdir(parents=True, exist_ok=True)
        n_w = sum(put(mir, n, b) for n, b in pub.items())
        extra = sorted(p.name for p in mir.iterdir() if p.is_file() and p.name not in pub)
        for n in extra:
            (mir / n).unlink()
        same = all(sha1((mir / n).read_bytes()) == sha1(b) for n, b in pub.items())
        L.check(same, f'mirror {mir} differs from the bundle')
        L.check(sorted(p.name for p in mir.iterdir() if p.is_file()) == sorted(pub), f'mirror {mir}: file set differs')
        print(f'\n[mirror] {mir}: {n_w} written, {len(extra)} removed {extra if extra else ""}; identical: {same}')

    # ---- report
    print('\n[sizes]')
    for n in sorted(pub, key=lambda x: (x != 'index.html', x != 'manifest.json', x)):
        k = files.get(n, {}).get('kind', 'page' if n == 'index.html' else 'manifest')
        print(f'  {n:24s} {len(pub[n]):>10d}  {mb(len(pub[n]))}  {k}')
    print(f'  {"total":24s} {total:>10d}  {mb(total)}  (limit 64 MB; largest file '
          f'{max(len(b) for b in pub.values()) / 1e6:.2f} MB, limit 16 MB)')
    for S in C.SIZES:
        fp = mf['first_paint_bytes'][S]
        extra = len(mtext) + (len(pub['index.html']) if 'index.html' in pub else 0)
        print(f'  first paint {S}: ' + ', '.join(f'{B} {mb(fp[B] + extra)}' for B in C.builds_of(S)) +
              f' (manifest{" + index.html" if html else ""} + core + build + data); build switch ' +
              ', '.join(f'{B} {mb(files[C.fname("build", S, B)]["bytes"] + files[C.fname("data", S, B)]["bytes"])}'
                        for B in C.builds_of(S) if B != 'std'))
    return finish(L, 'bundle written' if not a.check_only else 'checked')


def finish(L, what):
    print(f'\n{what}: {len(L.errors)} errors, {len(L.warnings)} warnings')
    for e in L.errors:
        print('  ERROR', e)
    for w in L.warnings:
        print('  warn ', w)
    return 1 if L.errors else 0


if __name__ == '__main__':
    sys.exit(main())
