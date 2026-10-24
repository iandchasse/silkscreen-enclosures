"""The Silkscreen showcase's data contract: file layout, node names, groups, cards, the bottom-key kinematics
and a validator for every file the bundle ships.

One page shows both case sizes (S in SIZES) and both builds (B in BUILDS), and the 4.26's extra builds
(EXTRA_BUILDS: chinless, light-strip chinless). The generator writes, per bundle:

  manifest.json        what exists: sizes, builds, groups, cards, every file with its bytes and sha1, which node
                       lives in which model file, the shared / per-build printed parts, defaults
  core-S.json          model file: nodes identical in both builds of size S
  build-S-B.json       model file: nodes that differ per build (the tub; the 3.68's keys; strip reference parts)
  extras-S.json        model file: nodes loaded on demand (cmp_* for "Next to the X4", dummy_pcba)
  data-S-B.json        everything else the page shows for one size and build (see validate_data)
  models-S.js          the print-file zip for size S (both builds, shared parts once), loaded on click
  strip.json, optics_heatmaps.png     the light-strip card's assets, as the light-strip page had them

A model file is JSON: {"format": "glb-base64", "schema", "kind", "size", "build", "nodes": {name: info}, "data"},
data being a binary glTF (no normals: the page computes creased normals) whose mesh / node names are the node
names below, in the CAD frame (mm; X = KiCad x - 44.24, Y = 148.25 - KiCad y, Z = 0 at the board's rear face,
+Z toward the screen). Both case projects share this frame.

Pure Python (json, math, re, base64): importable from either project's venv and from the bundler. The crank
kinematics here are the reference the page's JavaScript must reproduce exactly (API.md, "SC.crank").

    python -B sc_contract.py --selftest            validate the built-in sample and some broken copies of it
    python -B sc_contract.py <file.json> ...       validate files (kind from the file name)
    python -B sc_contract.py --bundle <dir>        validate a whole bundle folder
"""
import base64
import copy
import json
import math
import re
import sys
from pathlib import Path

SCHEMA = 'sc/1'
SIZES = ('426', '368')
BUILDS = ('std', 'ls')                                      # the full builds: every size has both
# builds only some sizes have (2026-10-04: the 4.26 chinless case, no bottom keys; 2026-10-07: the 4.26 light-strip
# chinless case, the light strip's panel with no bottom keys). builds_of(S) is what a size shows.
EXTRA_BUILDS = {'426': ('cl', 'lc'), '368': ()}
ALL_BUILDS = ('std', 'ls', 'cl', 'lc')
KEYLESS = ('cl', 'lc')                                      # builds without the bottom keys (no keys, cranks, rod, gate)
STRIP_BUILDS = ('ls', 'lc')                                 # builds with the plain panel and the light strip
BUILD_DIRS = {'std': 'standard', 'ls': 'light-strip', 'cl': 'chinless',
              'lc': 'light-strip-chinless'}                 # out/<dir> and SILKSCREEN_VARIANT
# the page's data-only / data-not tokens a build answers to: its own id, and the id of each build whose panel or chin
# it has (the chinless build shows the standard build's FT01C texts; the light-strip chinless shows the light strip's
# panel texts and the chinless build's chin texts). A size answers to its own id only.
BUILD_TOKENS = {'std': ('std',), 'ls': ('ls',), 'cl': ('cl', 'std'), 'lc': ('lc', 'ls', 'cl')}
VARIANTS = ('T', 'M')                                       # crank-T + TS365ZJ (every JLC board), crank-M + MJTP1117
DEFAULTS = {'size': '426', 'build': 'std', 'variant': 'T'}
SIZE_LABELS = {'426': '4.26"', '368': '3.68"'}
BUILD_LABELS = {'std': 'Standard', 'ls': 'Light strip', 'cl': 'Chinless', 'lc': 'Light-strip chinless'}
BUILD_NOTES = {'ls': 'in development, not released', 'cl': 'touch, no bottom keys',
               'lc': 'in development, not released; no touch, no bottom keys'}   # the stage bar's small print


def builds_of(size):
    """The builds a size shows, in stage-bar order."""
    return BUILDS + EXTRA_BUILDS.get(size, ())


def tokens_match(only, nots, size, build):
    """An element with data-only tokens `only` and data-not tokens `nots` shows on (size, build): every only-token is
    the size or one of the build's BUILD_TOKENS, and no not-token is (shell.html's tokensOk does the same)."""
    have = {size, *BUILD_TOKENS[build]}
    return all(t in have for t in only) and not (set(nots) & have)
BOTTOM_REFS = ('SW9', 'SW8', 'SW3', 'SW2')                  # left to right; the same in both sizes
DRAW_REF = 'SW8'                                            # the bottom key the section drawing cuts through
SIDE_KEY_COUNT = {'426': 5, '368': 3}
# the host's published limits, 16 MB per file and 64 MB per publish, read as decimal megabytes (the safe reading:
# 16 MiB would pass a file of 16,000,001 to 16,777,216 bytes)
LIMITS = {'file_bytes': 16_000_000, 'version_bytes': 64_000_000}


def fname(kind, size=None, build=None):
    """The bundle's file name for a kind of file."""
    return {'manifest': 'manifest.json', 'core': f'core-{size}.json', 'build': f'build-{size}-{build}.json',
            'extras': f'extras-{size}.json', 'data': f'data-{size}-{build}.json', 'models': f'models-{size}.js',
            'strip': 'strip.json', 'optics': 'optics_heatmaps.png'}[kind]


FILE_RE = {
    'manifest': re.compile(r'^manifest\.json$'),
    'core': re.compile(r'^core-(426|368)\.json$'),
    'build': re.compile(r'^build-(426|368)-(std|ls|cl|lc)\.json$'),
    'extras': re.compile(r'^extras-(426|368)\.json$'),
    'data': re.compile(r'^data-(426|368)-(std|ls|cl|lc)\.json$'),
    'models': re.compile(r'^models-(426|368)\.js$'),
}


def kind_of(name):
    for k, r in FILE_RE.items():
        if r.match(name):
            return k
    return None


# ---- nodes -------------------------------------------------------------------------------------------------
# Every mesh in a model file is one node. Names: lower-case word, then _-separated parts (refs keep their case).
NODE_RE = re.compile(r'^[a-z][a-z0-9]*(_[A-Za-z0-9]+)*$')
# (pattern, where it may live, what it is). '*' matches the rest of the name.
NODE_RULES = [
    ('tub', 'build', 'the front shell; differs per build'),
    ('lid', 'core', 'lid_body.stl: the lid WITHOUT its side keys (lid.stl has them fused in and would show them twice)'),
    ('skey_*', 'core', 'a side key (part of the lid), bends about its flex root; skey_<ref>'),
    ('midplate', 'core', 'the midplate'),
    ('key_*', 'any', 'a bottom key, slides -Z; key_<ref> (core on 4.26, build on 3.68: key-x3std / key-x3ls)'),
    ('crank_M', 'core', 'crank-M.stl: ONE crank at X = 0, theta 0; the viewer places it at keys.x[ref] 4 times'),
    ('crank_T', 'core', 'crank-T.stl: the same for crank-T'),
    ('rod', 'core', 'the 1.75 mm filament rod (ref_rod.stl)'),
    ('gate', 'core', "the side gate: the printed T in the -X wall that stops the rod's tail (gate.stl, installed pose)"),
    ('panel_*', 'any', 'display layers: panel_epd, panel_light, panel_touch (the 4.26 light-strip build: panel_epd only)'),
    ('ribbon_*', 'any', 'display ribbons / FPC: ribbon_main, ribbon_touch, ribbon_light, ...'),
    ('pcba_*', 'core', 'the board, merged per category: pcba_pcb, pcba_switch, pcba_passive, pcba_ic, ...'),
    ('nub_*', 'core', 'a switch plunger, split from its switch: nub_<ref> for bottom, side and reset switches'),
    ('swbody_*', 'core', 'a bottom switch body (MJTP1117 from the board STEP), split out of pcba_switch: swbody_<ref>'),
    ('sw_T_body', 'core', 'a TS365ZJ body at X = 0 (placed at keys.x[ref] 4 times when variant T is shown)'),
    ('sw_T_nub', 'core', 'its plunger at X = 0, nominal face -2.2'),
    ('battery_*', 'core', 'battery_cell, battery_leads, battery_plug'),
    ('screw_*', 'core', 'M2 socket head caps: screw_H3, screw_H4, screw_top (4.26); screw_bottom_left, '
                        'screw_bottom_right, screw_top, screw_top_left (3.68)'),
    ('strip_*', 'build', 'light-strip reference parts not generated live by strip3d.js (light-strip builds only)'),
    ('cmp_*', 'extras', 'the Xteink X4 and its retro case beside ours (X4 reference model: Zorian22, CC BY-NC-SA)'),
    ('dummy_pcba', 'extras', 'the printable PCBA dummy'),
]
INSTANCED = ('crank_M', 'crank_T', 'sw_T_body', 'sw_T_nub')    # modelled at X = 0, placed per bottom key


def node_rule(name):
    for pat, where, what in NODE_RULES:
        if pat.endswith('*') and name.startswith(pat[:-1]) or name == pat:
            return pat, where, what
    return None


# Chips: a node belongs to the first group whose match it fits. 'off' groups start hidden; 'builds' limits a
# group to those builds; 'lazy' groups live in extras-S and load when first shown.
GROUPS = [
    {'id': 'tub', 'label': 'Tub', 'match': ['tub']},
    {'id': 'keys', 'label': 'Keys', 'match': ['key_*'], 'builds': ['std', 'ls']},
    {'id': 'rod', 'label': 'Rod + cranks', 'match': ['rod', 'gate', 'crank_*'], 'builds': ['std', 'ls']},
    {'id': 'display', 'label': 'Panel + ribbons', 'match': ['panel_*', 'ribbon_*', 'screen']},
    {'id': 'midplate', 'label': 'Midplate', 'match': ['midplate']},
    {'id': 'pcba', 'label': 'PCBA', 'match': ['pcba_*', 'nub_*', 'swbody_*', 'sw_T_*']},
    {'id': 'battery', 'label': 'Battery', 'match': ['battery_*']},
    {'id': 'lid', 'label': 'Lid + side keys', 'match': ['lid', 'skey_*']},
    {'id': 'screws', 'label': 'Screws', 'match': ['screw_*']},
    {'id': 'strip', 'label': 'Light strip', 'match': ['strip_*'], 'builds': list(STRIP_BUILDS)},
    {'id': 'dummy', 'label': 'PCBA dummy', 'match': ['dummy_pcba'], 'off': True, 'lazy': True},
    {'id': 'compare', 'label': 'X4 + retro case', 'match': ['cmp_*'], 'off': True, 'lazy': True},
]
GROUP_IDS = [g['id'] for g in GROUPS]


def group_of(name):
    for g in GROUPS:
        for m in g['match']:
            if m.endswith('*') and name.startswith(m[:-1]) or name == m:
                return g['id']
    return None


# ---- cards -------------------------------------------------------------------------------------------------
# The tour, in order. sizes / builds: where the card shows (None = everywhere). preset: the stage preset its
# "Show in 3D" opens. enter_build: opening the card switches to that build (with a toast and an undo), unless the
# build is one of home_builds (default: enter_build alone), where the card works in place.
# away_builds {B: B2}: on build B the card shows only its heading and away_note, and its button switches to B2.
CARDS = [
    {'id': 'glance', 'order': 10, 'title': 'At a glance', 'preset': 'home'},
    {'id': 'keys', 'order': 20, 'title': 'Bottom keys: a straight key over a bell crank', 'preset': 'keys',
     'away_builds': {'cl': 'std', 'lc': 'ls'}, 'away_note': 'The chinless builds have no bottom keys.'},
    {'id': 'strip', 'order': 25, 'title': 'Light strip', 'preset': 'strip', 'enter_build': 'ls',
     'home_builds': list(STRIP_BUILDS)},
    {'id': 'sidekeys', 'order': 30, 'title': 'Side keys', 'preset': 'tabs'},
    {'id': 'joint', 'order': 40, 'title': 'Tub to lid joint', 'preset': 'joint'},
    {'id': 'usb', 'order': 50, 'title': 'USB-C', 'preset': 'usb'},
    {'id': 'reset', 'order': 55, 'title': 'Reset', 'preset': 'reset'},
    {'id': 'screen', 'order': 60, 'title': 'Screen stack', 'preset': 'stack'},
    {'id': 'detent', 'order': 65, 'title': 'Stack detents', 'preset': 'detent'},
    {'id': 'ribbons', 'order': 70, 'title': 'Display ribbons', 'preset': 'ribbons'},
    {'id': 'battery', 'order': 80, 'title': 'Battery', 'preset': 'battery'},
    {'id': 'boardprep', 'order': 85, 'title': 'Board prep', 'preset': 'boardprep', 'sizes': ['368']},
    {'id': 'zstack', 'order': 90, 'title': 'Front to back', 'preset': 'zstack'},
    {'id': 'closing', 'order': 100, 'title': 'Closing up', 'preset': 'close'},
    {'id': 'edges', 'order': 110, 'title': 'Edges and logo', 'preset': 'edges'},
    {'id': 'compare', 'order': 115, 'title': 'Next to the X4', 'preset': 'compare'},
    {'id': 'assembly', 'order': 120, 'title': 'Assembly order', 'preset': 'assembly'},
    {'id': 'checks', 'order': 130, 'title': "What's been checked", 'preset': None},
    {'id': 'files', 'order': 140, 'title': 'Model files', 'preset': 'dummy'},
]
CARD_IDS = [c['id'] for c in CARDS]


def card_applies(card, size, build):
    return (not card.get('sizes') or size in card['sizes']) and (not card.get('builds') or build in card['builds'])


def card_home(card):
    """The builds an enter_build card works on in place."""
    return list(card.get('home_builds') or ([card['enter_build']] if card.get('enter_build') else []))


def card_away(card, build):
    """True when the card shows only its heading on this build (enter_build elsewhere, or away_builds)."""
    return bool(card.get('enter_build') and build not in card_home(card) or build in (card.get('away_builds') or {}))


# ---- presets -----------------------------------------------------------------------------------------------
# The full camera table per size (Rev K had these 18), plus the new cards' presets.
PRESETS_REVK = ('home', 'assembly', 'keys', 'tabs', 'keylid', 'usb', 'reset', 'stack', 'detent', 'ribbons',
                'battery', 'edges', 'close', 'joint', 'latch', 'compare', 'back', 'dummy')
PRESETS_NEW = ('strip', 'zstack')
PRESETS_SIZE = {'426': (), '368': ('boardprep',)}


def required_presets(size):
    return PRESETS_REVK + PRESETS_NEW + PRESETS_SIZE[size]


PRESET_KEYS = {'cam', 'tgt', 'up', 'fit', 'sec', 'focus', 'show', 'hide', 'press', 'highlight', 'explode', 'tag',
               'cap', 'variant'}

# ---- drawings ----------------------------------------------------------------------------------------------
# A drawing is a section of the built meshes by an axis plane, in that plane's (u, v) frame:
#   axis x: u = Y, v = Z      axis y: u = X, v = Z      axis z: u = X, v = Y
DRAW_UV = {'x': ('y', 'z'), 'y': ('x', 'z'), 'z': ('x', 'y')}
ROLES = ('case', 'case2', 'plate', 'pcb', 'part', 'nub', 'glass', 'lgp', 'film', 'key', 'crank', 'rod', 'tab',
         'metal', 'ribbon', 'cell', 'lead', 'strip', 'led', 'tape', 'kapton', 'ref')
DRAWINGS_COMMON = ('key', 'tab_plan', 'key_side', 'tab_elev', 'detent', 'detent_plan', 'usb', 'usb_plan', 'reset',
                   'stack', 'bezel', 'ribbon', 'clamp', 'pin', 'top', 'joint_tongue', 'joint_at_tab', 'joint_top',
                   'joint_latch')
DRAWINGS_SIZE = {'426': ('battery', 'fence', 'bay_lip'), '368': ('bay',)}
DRAWINGS_BUILD = {'std': (), 'ls': ('strip_led',), 'cl': (), 'lc': ('strip_led',)}
DRAWINGS_NOT = {'cl': ('key',), 'lc': ('key',)}             # keyless builds have no bottom-key section
# the bottom-key section: layer ids the keys card moves (crank_* rotate about the rod, key slides -Z,
# nub_* slide +Y); crank_M/sw_M/nub_M show for variant M, crank_T/sw_T/nub_T for variant T
KEY_DRAWING_LAYERS = ('tub', 'lid', 'key', 'crank_M', 'crank_T', 'rod', 'sw_M', 'nub_M', 'sw_T', 'nub_T')


def required_drawings(size, build):
    return tuple(n for n in DRAWINGS_COMMON + DRAWINGS_SIZE[size] + DRAWINGS_BUILD[build]
                 if n not in DRAWINGS_NOT.get(build, ()))


# ---- the bottom-key switches (the same board in both sizes, so the same numbers) ------------------------------
# (y, z) at the nominal board, CAD frame. MJTP1117: the spec's envelope (4.26 keys.SWITCH = layout.json
# switch_envelope_used); the x3 board STEP gives the same face, plunger Z band, body Z0 and half-width, but its
# plunger probe is only 0.3 mm deep, so its own "housing front" (y -1.62) is the probe's end, not the body's.
# TS365ZJ: its drawing, nominal plunger (both projects' TS365 nominal case) and, as nub_z_worst, the worst-case
# plunger band with no tolerance given (x3 params.TS365 plunger_z_worst, 4.26 keys.SWITCH nub).
SWITCH_GEOM = {
    'M': {'face_y': -1.92, 'nub_z': [-3.459, -1.959], 'nub_yz': [-1.92, -3.459, -0.68, -1.959], 'nub_half_x': 1.44,
          'housing_yz': [-0.68, -4.49, 6.0, -0.19], 'housing_half_x': 4.04},
    'T': {'face_y': -2.2, 'face_worst_y': -2.4, 'nub_z': [-3.25, -1.75], 'nub_z_worst': [-3.05, -1.05],
          'nub_yz': [-2.2, -3.25, -1.45, -1.75], 'nub_half_x': 1.85, 'housing_yz': [-1.65, -3.6, 6.0, 0.0],
          'housing_half_x': 3.65},
}
SWITCH_GEOM_TOL = 0.01                                     # mm: the x3 STEP's MJTP numbers round to 3 places


def switch_geom(v):
    """A copy of SWITCH_GEOM[v] (the adapters build keys.switches from it and check their project against it)."""
    return copy.deepcopy(SWITCH_GEOM[v])


def switch_geom_diff(got, v, tol=SWITCH_GEOM_TOL):
    """The fields of a keys.switches[v] entry that differ from SWITCH_GEOM[v] by more than tol: [(field, got, want)]."""
    out = []
    for k, want in SWITCH_GEOM[v].items():
        g = got.get(k) if isinstance(got, dict) else None
        a, b = (g if isinstance(g, list) else [g]), (want if isinstance(want, list) else [want])
        if len(a) != len(b) or not all(_num(x) and abs(x - y) <= tol + 1e-9 for x, y in zip(a, b)):
            out.append((k, g, want))
    return out


# ---- the bottom keys' force table: one shape in both sizes ----------------------------------------------------
# keys.forces.table = {"<MJTP|TS365> <switch N, 2 places>": {"mu_<mu>": [finger N at each keys.forces.press_ys]}},
# press_ys ascending (from the chin to the key's top edge). The 4.26 mechanics.json writes
# {"MJTP 1.27 mu 0.3": {"y -6.20": N}}, the x3 one {"MJTP 1.27": [...]} under key_forces["mu_0.3"]: the adapters
# map theirs with force_table().
FORCE_KEY_RE = re.compile(r'^(MJTP|TS365) (\d+\.\d\d)$')
FORCE_MU_RE = re.compile(r'^mu_(\d+(\.\d+)?)$')


def force_table(rows):
    """rows: iterable of (family 'MJTP'|'TS365', switch_N, mu, press_y, finger_N) -> (table, press_ys)."""
    ys = sorted({round(float(r[3]), 2) + 0.0 for r in rows})
    T = {}
    for fam, n, mu, y, val in rows:
        e = T.setdefault(f'{fam} {float(n):.2f}', {}).setdefault(f'mu_{float(mu):g}', [None] * len(ys))
        e[ys.index(round(float(y), 2) + 0.0)] = val
    return T, ys


def _force_table_ok(F, where, E):
    T, ys = F.get('table'), F.get('press_ys')
    if not (isinstance(ys, list) and len(ys) >= 2 and all(_num(y) for y in ys) and ys == sorted(ys)):
        E.at(where + '.press_ys', 'press_ys: [y, ...] ascending (the points along the key the table gives)')
        return
    if not isinstance(T, dict) or not T:
        E.at(where + '.table', '{"MJTP 1.27": {"mu_0.3": [N per press_ys]}, ...}')
        return
    fams = set()
    for k, row in T.items():
        m = FORCE_KEY_RE.match(k)
        if not m or not isinstance(row, dict) or not row:
            E.at(f'{where}.table.{k}', 'key "<MJTP|TS365> <N.NN>" with {"mu_<mu>": [N, ...]}')
            continue
        fams.add(m.group(1))
        for mk, vals in row.items():
            if not FORCE_MU_RE.match(mk) or not (isinstance(vals, list) and len(vals) == len(ys) and all(_num(x) for x in vals)):
                E.at(f'{where}.table.{k}.{mk}', f'mu_<mu>: {len(ys)} numbers, one per press_ys')
    if fams != {'MJTP', 'TS365'}:
        E.at(where + '.table', 'rows for both MJTP and TS365')
    # finger_N is the table at press_y, mu
    if _num(F.get('press_y')) and F['press_y'] in ys and _num(F.get('mu')):
        i, mk = ys.index(F['press_y']), f'mu_{F["mu"]:g}'
        for v, fam in (('M', 'MJTP'), ('T', 'TS365')):
            got = sorted(r[mk][i] for k, r in T.items() if k.startswith(fam + ' ') and isinstance(r, dict) and mk in r
                         and isinstance(r[mk], list) and len(r[mk]) == len(ys))
            fn = F.get('finger_N', {}).get(v)
            if _vec(fn, 2) and got and (abs(got[0] - fn[0]) > 0.006 or abs(got[-1] - fn[1]) > 0.006):
                E.at(where + '.finger_N', f'{v} {fn} is not the table at press_y {F["press_y"]}, {mk}: {got}')
    else:
        E.at(where, 'press_y must be one of press_ys, and mu a number')


def cross_check_keys(K426, K368, E=None):
    """The two sizes put the same switches on the same board: the switch geometry, travel and forces must agree."""
    E = E if E is not None else Errors()
    for v in VARIANTS:
        a, b = K426['switches'][v], K368['switches'][v]
        for k in ('part', 'crank', *SWITCH_GEOM[v].keys(), 'travel', 'force_N'):
            x, y = a.get(k), b.get(k)
            same = (all(abs(p - q) <= SWITCH_GEOM_TOL + 1e-9 for p, q in zip(x, y)) and len(x) == len(y)
                    if isinstance(x, list) and isinstance(y, list) else x == y)
            if not same:
                E.at(f'keys.switches.{v}.{k}', f'4.26 {x} != 3.68 {y} (same switch, same board)')
    fa, fb = K426['forces'], K368['forces']
    if set(fa.get('table', {})) != set(fb.get('table', {})) or fa.get('press_ys') != fb.get('press_ys'):
        E.at('keys.forces', "the two sizes' force tables must have the same rows and press_ys")
    return E

# ---- the print-file zip: one folder layout in both sizes, and one download name per distinct download ---------
ZIP_DIRS = {'shared': 'shared/', 'std': 'standard/', 'ls': 'light-strip/', 'cl': 'chinless/',
            'lc': 'light-strip-chinless/', 'dummy': 'dummy/'}
ZIP_TOP = ('README.txt', 'ROD.txt')                       # the only files outside the folders
DOWNLOAD_GROUPS = ('shared', 'std', 'ls', 'rod', 'dummy')


def download_groups(size):
    """The group ids of a size's zip, in order: shared, one per build of the size, rod, dummy."""
    return ('shared',) + builds_of(size) + ('rod', 'dummy')


# print files left out of the zip, by size: name prefixes the adapter leaves out and the bundler's "every print file
# is in the zip" check skips. At first those of builds the showcase did not show yet; now STEP files only, for size.
# 2026-10-04: the 4.26 chinless case (plate 4 of the plate file) was left out until the showcase took it as a third
# build ('cl', the same day). Its two STEP files stay out of the zip (they are in print/4.26/ in the repo): with them
# models-426.js was 16.64 MB, at the published page's 16 MB per file. 2026-10-07: the 4.26 light-strip chinless case
# (plate 5) is the fourth build ('lc'): its tub's STL is in the zip, its STEP stays out like the chinless ones (with
# it models-426.js would be about 16.3 MB).
# 2026-10-23: the logo inlays (the optional two-colour logo, print/*/lid-inlay-*, lid-chinless-inlay-*) are not listed: whether the
# site offers the two-colour files is Ian's later call.
ZIP_NOT_SHOWN = {'426': ('tub-chinless.step', 'lid-chinless.step', 'tub-light-strip-chinless.step', 'lid-inlay-', 'lid-chinless-inlay-'),
                 '368': ('lid-inlay-',)}
# a shared file may carry skip_builds [B]: a build that does not use it (the chinless cases have their own lid and no
# keys, cranks, gate or rod), so the files card's "only this build" download leaves it out. A file in a build's group
# lists that build first and may list others that print it too (lid-chinless: ['cl', 'lc']).


def download_names(dl, size=None):
    """The file name of every download the files card offers for one size (page/cards/files.js zipName does the
    same): {'all': base.zip, 'build:<B>': base-<dir>.zip, 'group:<id>': base-<dir or id>-only.zip}."""
    base = re.sub(r'\.zip$', '', dl['zip'], flags=re.I)
    out = {'all': base + '.zip'}
    for b in (builds_of(size) if size else BUILDS):
        out['build:' + b] = f'{base}-{BUILD_DIRS[b]}.zip'
    for g in dl.get('groups', []):
        out['group:' + g['id']] = f'{base}-{BUILD_DIRS.get(g["id"], g["id"])}-only.zip'
    return out


def _downloads_layout(dl, where, E, size=None):
    ids = [g.get('id') for g in dl.get('groups', [])]
    want_ids = download_groups(size) if size else DOWNLOAD_GROUPS
    if tuple(ids) != want_ids:
        E.at(where + '.groups', f'group ids must be {list(want_ids)} (one layout in both sizes), not {ids}')
    for g in dl.get('groups', []):
        for f in g.get('files', []):
            p, bl = f.get('path', ''), f.get('builds')
            d = ZIP_DIRS.get(g.get('id'))
            if d is None:
                ok = p in ZIP_TOP
            else:
                ok = p.startswith(d) and '/' not in p[len(d):]
            if not ok:
                E.at(f'{where}.groups.{g.get("id")}', f'{p}: must be ' + (f'{d}<file>' if d else ' or '.join(ZIP_TOP)))
            gid = g.get('id')
            ok = (bl is None if gid not in ALL_BUILDS else isinstance(bl, list) and bl[:1] == [gid]
                  and len(set(bl)) == len(bl) and set(bl) <= set(ALL_BUILDS))
            if not ok:
                E.at(f'{where}.groups.{gid}', f'{p}: builds {bl}, want ' +
                     ('none' if gid not in ALL_BUILDS else f'[{gid!r}, ...]'))
            sk = f.get('skip_builds')
            if sk is not None and (bl is not None or not set(sk) <= set(ALL_BUILDS)):
                E.at(f'{where}.groups.{g.get("id")}', f'{p}: skip_builds {sk} only on files without builds')
    names = download_names(dl, size)
    if len(set(names.values())) != len(names):
        E.at(where, f'two downloads share a file name: {names}')

# ---- controls ----------------------------------------------------------------------------------------------
CONTROL_KINDS = ('crank', 'flexure', 'pin', 'plug')
CONTROL_KEYS = {
    'crank': ('id', 'label', 'kind', 'ref', 'node', 'crank', 'plunger', 'pivot', 'axis'),
    'flexure': ('id', 'label', 'kind', 'ref', 'node', 'plunger', 'plunger_axis', 'pivot', 'axis', 'sign', 'length',
                'gap', 'click_travel', 'max_travel'),
    'pin': ('id', 'label', 'kind', 'ref', 'plunger', 'plunger_axis', 'pin_from', 'pin_to', 'click_travel',
            'max_travel'),
    'plug': ('id', 'label', 'kind', 'axis', 'from', 'to', 'insert_mm'),
}


# ---- bottom-key kinematics (the reference the page reproduces) --------------------------------------------
# data.keys holds the crank's geometry; everything moves by one angle theta (degrees) about the rod, right-handed
# about +X: +theta = pressed (the pad goes down, the nose goes +Y into the plunger). Meshes are built at
# theta_built (0: crank-M's nose on a nominal MJTP1117 face, crank-T's on a nominal TS365ZJ face).
#   rot(p, th)          = rod + R(th) (p - rod)                      (p, rod in (y, z))
#   crown_z(th)         = rot(pad.c, th).z                           the key rides the pad crown's top
#   key_down(th, th0)   = crown_z(th0) - crown_z(th)                 mm the key has gone -Z since th0
#   nose_front(v, th)   = rot(nose.c[v], th).y + nose.r              the nose crown's +Y extreme
#   face(v, dy)         = switches[v].face_y + dy                    dy: the board / plunger face moved +Y
#   plunger_in(v, th, dy) = max(0, nose_front(v, th) - face(v, dy))
#   theta_at(v, y)      = the th in [-40, 40] with nose_front(v, th) = y (60 bisection steps)
#   rest(v, dy)  = theta_at(v, face(v, dy));  click(v, dy) = theta_at(v, face + travel.click);  bottom: + travel.bottom
# 3D: crank_<ref>.rotation.x = rad(th - theta_built) about (x, rod.y, rod.z); key_<ref>.position.z =
# -key_down(th, theta_built); the plunger node .position.y = plunger_in(v, th, 0).
def _rot(p, th, rod):
    t = math.radians(th)
    vy, vz = p[0] - rod[0], p[1] - rod[1]
    return (rod[0] + vy * math.cos(t) - vz * math.sin(t), rod[1] + vy * math.sin(t) + vz * math.cos(t))


def crown_z(K, th):
    return _rot(K['pad']['c'], th, K['rod']['yz'])[1]


def key_down(K, th, th0=None):
    return crown_z(K, K['theta_built'] if th0 is None else th0) - crown_z(K, th)


def nose_front(K, v, th):
    return _rot(K['nose']['c'][v], th, K['rod']['yz'])[0] + K['nose']['r']


def face(K, v, dy=0.0):
    return K['switches'][v]['face_y'] + dy


def plunger_in(K, v, th, dy=0.0):
    return max(0.0, nose_front(K, v, th) - face(K, v, dy))


def theta_at(K, v, y):
    lo, hi = -40.0, 40.0
    for _ in range(60):
        m = (lo + hi) / 2
        if nose_front(K, v, m) < y:
            lo = m
        else:
            hi = m
    return (lo + hi) / 2


def derive(K, v, dy=0.0):
    """Rest, click and bottom for variant v with the plunger face moved dy (+Y)."""
    f = face(K, v, dy)
    tr = K['switches'][v]['travel']
    th_r, th_c, th_b = theta_at(K, v, f), theta_at(K, v, f + tr['click']), theta_at(K, v, f + tr['bottom'])
    r = lambda x: round(x, 4) + 0.0                             # + 0.0: no '-0.0'
    return {'theta_rest': r(th_r), 'theta_click': r(th_c), 'theta_bottom': r(th_b),
            'key_rest': r(key_down(K, th_r)),                     # below the built key (tolerance readout)
            'key_click': r(key_down(K, th_c, th_r)), 'key_bottom': r(key_down(K, th_b, th_r))}


# ---- validation --------------------------------------------------------------------------------------------
class Errors(list):
    def at(self, where, msg):
        self.append(f'{where}: {msg}')


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _vec(x, n=3):
    return isinstance(x, list) and len(x) == n and all(_num(v) for v in x)


def _str(x):
    return isinstance(x, str) and x != ''


def _ascii(obj, where, E):
    s = json.dumps(obj, ensure_ascii=False, allow_nan=True)
    bad = [c for c in set(s) if ord(c) > 0x7F]
    if bad:
        E.at(where, f'non-ASCII characters {"".join(sorted(bad))[:20]!r}: use HTML entities or JSON \\u escapes')
    if re.search(r'\b(NaN|Infinity)\b', s):
        E.at(where, 'NaN / Infinity is not JSON')


def _need(d, keys, where, E):
    if not isinstance(d, dict):
        E.at(where, 'must be an object')
        return False
    miss = [k for k in keys if k not in d]
    if miss:
        E.at(where, f'missing {miss}')
    return not miss


def _groups_ok(lst, where, E):
    if lst is None:
        return
    if not isinstance(lst, list) or any(g not in GROUP_IDS for g in lst):
        E.at(where, f'unknown group in {lst} (groups: {GROUP_IDS})')


def _get(obj, path):
    cur = obj
    for p in path.split('.'):
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        elif isinstance(cur, list) and p.isdigit() and int(p) < len(cur):
            cur = cur[int(p)]
        else:
            raise KeyError(path)
    return cur


def validate_model(M, name='model', decode=False):
    """A core / build / extras file. decode: also parse the GLB's JSON chunk and match its mesh names."""
    E = Errors()
    if not _need(M, ('format', 'schema', 'kind', 'size', 'build', 'nodes', 'data'), name, E):
        return E
    if M['format'] != 'glb-base64':
        E.at(name, "format must be 'glb-base64'")
    if M['schema'] != SCHEMA:
        E.at(name, f'schema {M["schema"]!r} != {SCHEMA!r}')
    if M['kind'] not in ('core', 'build', 'extras'):
        E.at(name, f'kind {M["kind"]!r}')
    if M['size'] not in SIZES:
        E.at(name, f'size {M["size"]!r}')
    if (M['kind'] == 'build') != (M['build'] in ALL_BUILDS) or (M['kind'] != 'build' and M['build'] is not None):
        E.at(name, 'build must be set on build files only')
    for n, info in M['nodes'].items():
        w = f'{name}.nodes.{n}'
        if not NODE_RE.match(n):
            E.at(w, 'bad node name')
        r = node_rule(n)
        if r is None:
            E.at(w, 'matches no NODE_RULES entry')
        elif r[1] != 'any' and r[1] != M['kind'] and not (
                # an extra build's file may replace a core node (the chinless lid: same name, its own mesh)
                M['kind'] == 'build' and r[1] == 'core' and M['build'] not in BUILDS):
            E.at(w, f'belongs in a {r[1]} file, not {M["kind"]}')
        if group_of(n) is None:
            E.at(w, 'matches no group')
        _need(info, ('tris', 'hash', 'bbox'), w, E)
        if 'bbox' in info and not _vec(info['bbox'], 6):
            E.at(w, 'bbox must be [x0, y0, z0, x1, y1, z1]')
        if n in INSTANCED and 'bbox' in info and _vec(info['bbox'], 6) and abs(info['bbox'][0] + info['bbox'][3]) > 1.0:
            E.at(w, 'instanced nodes are modelled centred on X = 0')
    if not isinstance(M['data'], str) or not M['data']:
        E.at(name, 'data must be base64 text')
    elif decode:
        try:
            names = glb_mesh_names(base64.b64decode(M['data']))
            if set(names) != set(M['nodes']):
                E.at(name, f'GLB meshes {sorted(set(names) ^ set(M["nodes"]))[:8]} differ from the nodes list')
        except Exception as e:                                      # noqa: BLE001
            E.at(name, f'GLB does not parse: {e}')
    return E


def glb_mesh_names(glb):
    """Node names in a binary glTF (JSON chunk only; no mesh decoding)."""
    import struct
    magic, ver, length = struct.unpack_from('<4sII', glb, 0)
    if magic != b'glTF' or ver != 2:
        raise ValueError('not glTF 2 binary')
    clen, ctype = struct.unpack_from('<I4s', glb, 12)
    if ctype != b'JSON':
        raise ValueError('first chunk is not JSON')
    g = json.loads(glb[20:20 + clen])
    return [n.get('name') for n in g.get('nodes', []) if 'mesh' in n]


def validate_keys(K, where='keys', E=None, nodes=None):
    E = E if E is not None else Errors()
    if not _need(K, ('refs', 'x', 'draw_ref', 'rod', 'axis', 'theta_built', 'pad', 'nose', 'switches', 'default_variant',
                     'derived', 'rest_rows', 'forces', 'hooks', 'rod_check', 'checks', 'instances'), where, E):
        return E
    if list(K['refs']) != list(BOTTOM_REFS):
        E.at(where, f'refs must be {list(BOTTOM_REFS)} (left to right)')
    if set(K['x']) != set(K['refs']) or not all(_num(v) for v in K['x'].values()):
        E.at(where + '.x', 'one X per ref')
    if K['draw_ref'] not in K['refs']:
        E.at(where, 'draw_ref not in refs')
    if not _need(K['rod'], ('yz', 'd', 'cut', 'gate'), where + '.rod', E) or not _vec(K['rod']['yz'], 2):
        E.at(where + '.rod', 'yz must be [y, z]')
    if K['axis'] != [1, 0, 0]:
        E.at(where, 'axis must be [1, 0, 0]')
    if not (_need(K['pad'], ('c', 'r'), where + '.pad', E) and _vec(K['pad']['c'], 2)):
        E.at(where + '.pad', 'c must be [y, z]')
    if not (_need(K['nose'], ('c', 'r'), where + '.nose', E) and all(_vec(K['nose']['c'].get(v), 2) for v in VARIANTS)):
        E.at(where + '.nose', 'c must give [y, z] for each variant ' + str(VARIANTS))
    if K['default_variant'] not in VARIANTS:
        E.at(where, 'default_variant')
    if E:
        return E
    for v in VARIANTS:
        s = K['switches'].get(v)
        w = f'{where}.switches.{v}'
        if not _need(s, ('part', 'crank', 'face_y', 'nub_z', 'housing_yz', 'travel', 'force_N', 'label'), w, E):
            continue
        if not (_num(s['face_y']) and _vec(s['nub_z'], 2) and _vec(s['housing_yz'], 4) and _vec(s['force_N'], 2)):
            E.at(w, 'face_y number, nub_z [z0, z1], housing_yz [y0, z0, y1, z1], force_N [lo, hi]')
        if not (isinstance(s['travel'], dict) and _num(s['travel'].get('click')) and _num(s['travel'].get('bottom'))
                and 0 < s['travel']['click'] < s['travel']['bottom']):
            E.at(w, 'travel {click, bottom} with 0 < click < bottom')
        # one definition of each switch in both sizes (SWITCH_GEOM): nominal plunger as nub_z / nub_yz, the TS365's
        # worst case only as nub_z_worst / face_worst_y
        for k, got, want in switch_geom_diff(s, v):
            E.at(f'{w}.{k}', f'{got} != sc_contract.SWITCH_GEOM {want}')
        ny = s.get('nub_yz')
        if _vec(ny, 4) and _vec(s['nub_z'], 2) and (abs(ny[0] - s['face_y']) > 1e-6 or [ny[1], ny[3]] != list(s['nub_z'])):
            E.at(w, 'nub_yz must be [face_y, nub_z[0], y1, nub_z[1]] (the nominal plunger)')
    if E:
        return E
    # derived must be what the reference computes (the page recomputes it in JS)
    for v in VARIANTS:
        d, ref = K['derived'].get(v), derive(K, v)
        if not isinstance(d, dict):
            E.at(f'{where}.derived.{v}', 'missing')
            continue
        for k, val in ref.items():
            if not _num(d.get(k)) or abs(d[k] - val) > 2e-3:
                E.at(f'{where}.derived.{v}.{k}', f'{d.get(k)} != reference {val}')
        if not (ref['theta_rest'] < ref['theta_click'] < ref['theta_bottom']):
            E.at(f'{where}.derived.{v}', 'rest < click < bottom fails')
        # monotonic between rest and bottom: the key goes down, the plunger in
        th = [ref['theta_rest'] + (ref['theta_bottom'] - ref['theta_rest']) * i / 40 for i in range(41)]
        kd = [key_down(K, t) for t in th]
        pi = [plunger_in(K, v, t) for t in th]
        if any(b <= a for a, b in zip(kd, kd[1:])) or any(b < a - 1e-12 for a, b in zip(pi, pi[1:])):
            E.at(f'{where}.derived.{v}', 'key_down / plunger_in not monotonic from rest to bottom')
    # board-tolerance rest rows: INDEPENDENT numbers (bottom-keys.json static / crank.json rest), checked against
    # the reference; they are also the page's tolerance readout
    rows = K['rest_rows']
    if not isinstance(rows, list) or not rows:
        E.at(where + '.rest_rows', 'need rows')
    else:
        seen = set()
        for i, r in enumerate(rows):
            w = f'{where}.rest_rows[{i}]'
            if not _need(r, ('variant', 'face_dy', 'theta', 'key_dz', 'source'), w, E):
                continue
            if r['variant'] not in VARIANTS:
                E.at(w, 'variant')
                continue
            seen.add((r['variant'], round(r['face_dy'], 3)))
            th = theta_at(K, r['variant'], face(K, r['variant'], r['face_dy']))
            if abs(th - r['theta']) > 0.015 + 1e-9:
                E.at(w, f'theta {r["theta"]} but the geometry gives {th:.4f} (sign or face convention?)')
            kd = key_down(K, th)
            if abs(kd - r['key_dz']) > 0.0015 + 1e-9:
                E.at(w, f'key_dz {r["key_dz"]} but the geometry gives {kd:.4f} (key_dz = mm DOWN from theta_built)')
        for v in VARIANTS:
            for dy in (-0.2, 0.0, 0.2):
                if (v, dy) not in seen:
                    E.at(where + '.rest_rows', f'missing row {v} face_dy {dy:+.1f}')
    # one shape for both projects' mechanics (4.26 mechanics.key_forces / key_hooks / key_overpress; x3
    # key_forces['mu_0.3'] / key_hooks + key_preload / crank_stress)
    F = K['forces']
    if _need(F, ('lever', 'finger_N', 'press_y', 'mu', 'source'), where + '.forces', E):
        _need(F['lever'], ('input_arm', 'output_arm', 'ratio'), where + '.forces.lever', E)
        if not all(_vec(F['finger_N'].get(v), 2) for v in VARIANTS):
            E.at(where + '.forces.finger_N', 'M and T: [N at the low switch force, N at the high], at press_y, mu')
        else:
            _force_table_ok(F, where + '.forces', E)
    # the hook keys (test 2, 2026-09-30): two rigid hooks per key in two slots of the chin wall; the key rests on its
    # crank face up and drops W_OUT onto its hooks face down (the drag leaf and its coupon band are gone)
    Hk = K['hooks']
    if _need(Hk, ('W_OUT_mm', 'hook_dx', 'hook_h_mm', 'hook_tip_y', 'hook_z_rest', 'slot_dx', 'slot_back_y', 'slot_roof_z',
                  'face_down_free_travel_mm', 'rest_load_on_plunger_N', 'key_mass_g', 'source'), where + '.hooks', E):
        w = where + '.hooks'
        if not all(_vec(Hk[k], 2) for k in ('hook_dx', 'hook_z_rest', 'slot_dx', 'face_down_free_travel_mm')):
            E.at(w, 'hook_dx, hook_z_rest, slot_dx and face_down_free_travel_mm are [lo, hi]')
        elif abs(Hk['hook_z_rest'][1] + Hk['W_OUT_mm'] - Hk['slot_roof_z']) > 2e-3:
            E.at(w, f"the hooks' top + W_OUT ({Hk['hook_z_rest'][1]} + {Hk['W_OUT_mm']}) is not the slot roof {Hk['slot_roof_z']}")
        elif abs(Hk['hook_z_rest'][1] - Hk['hook_z_rest'][0] - Hk['hook_h_mm']) > 2e-3:
            E.at(w, 'hook_z_rest must span hook_h_mm')
        elif not (Hk['slot_dx'][0] < Hk['hook_dx'][0] < Hk['hook_dx'][1] <= Hk['slot_dx'][1]):
            E.at(w, 'the hooks must lie inside their slots in X')
        elif not Hk['slot_back_y'] < Hk['hook_tip_y']:
            E.at(w, "a hook's tip must stop short of its slot's back")
        elif not 0 <= Hk['face_down_free_travel_mm'][0] <= Hk['face_down_free_travel_mm'][1]:
            E.at(w, 'face_down_free_travel_mm [lo, hi] with 0 <= lo <= hi (W_OUT must clear the rest scatter)')
    _need(K['rod_check'], ('press_N', 'bending_MPa', 'deflection_um', 'source'), where + '.rod_check', E)
    if not isinstance(K['instances'], dict) or set(K['instances'].get('crank', {})) != set(VARIANTS):
        E.at(where + '.instances', "crank: {'M': 'crank_M', 'T': 'crank_T'}")
    if nodes is not None:
        need = {f'key_{r}' for r in BOTTOM_REFS} | {f'nub_{r}' for r in BOTTOM_REFS} | {f'swbody_{r}' for r in BOTTOM_REFS} \
            | {'crank_M', 'crank_T', 'sw_T_body', 'sw_T_nub', 'rod', 'gate'}
        miss = sorted(need - set(nodes))
        if miss:
            E.at(where, f'nodes missing from the model files: {miss}')
    _checks(K['checks'], where + '.checks', E)
    return E


def _checks(lst, where, E):
    if not isinstance(lst, list):
        E.at(where, 'must be a list')
        return
    for i, c in enumerate(lst):
        w = f'{where}[{i}]'
        if _need(c, ('id', 'label', 'ok'), w, E) and c['ok'] not in (True, False, None):
            E.at(w, 'ok must be true, false or null (not run)')


def validate_drawing(d, where, E):
    if not _need(d, ('name', 'axis', 'at', 'window', 'layers', 'beyond', 'notes'), where, E):
        return
    if d['axis'] not in DRAW_UV or not _num(d['at']):
        E.at(where, 'axis x|y|z and a numeric at')
    if not _vec(d['window'], 4) or not (d['window'][0] < d['window'][1] and d['window'][2] < d['window'][3]):
        E.at(where, 'window [u0, u1, v0, v1] with u0 < u1, v0 < v1')
        return
    u0, u1, v0, v1 = d['window']
    if not d['layers']:
        E.at(where, 'no layers: nothing was cut (wrong plane or window?)')
    ids = set()
    for kind in ('layers', 'beyond'):
        for j, L in enumerate(d[kind]):
            w = f'{where}.{kind}[{j}]'
            if not _need(L, ('id', 'role', 'polys') + (('at',) if kind == 'beyond' else ()), w, E):
                continue
            if kind == 'layers':
                if L['id'] in ids:
                    E.at(w, f'duplicate layer id {L["id"]!r}')
                ids.add(L['id'])
            if L['role'] not in ROLES:
                E.at(w, f'role {L["role"]!r} not in ROLES')
            if not L['polys']:
                E.at(w, 'empty polys (drop the layer instead)')
            for poly in L['polys']:
                for ring in poly:
                    if len(ring) < 3 or any(not _vec(p, 2) for p in ring):
                        E.at(w, 'a ring needs 3+ [u, v] points')
                        break
                    if any(p[0] < u0 - 0.01 or p[0] > u1 + 0.01 or p[1] < v0 - 0.01 or p[1] > v1 + 0.01 for p in ring):
                        E.at(w, 'points outside the window')
                        break
    if d['name'] == 'key':
        miss = [i for i in KEY_DRAWING_LAYERS if i not in ids]
        if miss:
            E.at(where, f'the key drawing needs layers {miss}')


def validate_data(D, name='data', nodes=None, strict=True, needs=()):
    """data-S-B.json. nodes: the node names of core-S + build-S-B (+ extras-S) to cross-check references.
    strict: require the full preset and drawing lists. needs: extra dotted paths that must resolve (cards'
    [data-k] bindings)."""
    E = Errors()
    top = ('schema', 'size', 'build', 'meta', 'facts', 'presets', 'explode', 'controls', 'keys', 'drawings', 'cards',
           'checks', 'assembly', 'downloads')
    if not _need(D, top, name, E):
        return E
    _ascii(D, name, E)
    if D['schema'] != SCHEMA:
        E.at(name, f'schema {D["schema"]!r}')
    S, B = D['size'], D['build']
    if S not in SIZES or B not in builds_of(S):
        E.at(name, f'size {S!r} / build {B!r}')
        return E
    keyless = B in KEYLESS
    # meta
    m = D['meta']
    if _need(m, ('title', 'size_label', 'panel', 'envelope', 'size', 'body', 'z', 'active', 'frame', 'printed',
                 'side_keys', 'bottom_keys', 'reset', 'source'), name + '.meta', E):
        if not _vec(m['envelope'], 6) or not _vec(m['size'], 3) or not _vec(m['body'], 3):
            E.at(name + '.meta', 'envelope [x0, x1, y0, y1, z0, z1], size [3], body [3]')
        _need(m['panel'], ('part', 'label', 'touch', 'front_light', 'ribbons'), name + '.meta.panel', E)
        _need(m['active'], ('cx', 'cy', 'w', 'h'), name + '.meta.active', E)
        if _need(m['printed'], ('parts', 'count'), name + '.meta.printed', E):
            for p in m['printed']['parts']:
                _need(p, ('name', 'count', 'file'), name + '.meta.printed.parts[]', E)
        if len(m['side_keys']) != SIDE_KEY_COUNT[S]:
            E.at(name + '.meta.side_keys', f'{S} has {SIDE_KEY_COUNT[S]} side keys')
        if list(m['bottom_keys']) != ([] if keyless else list(BOTTOM_REFS)):
            E.at(name + '.meta.bottom_keys', '[]' if keyless else str(BOTTOM_REFS))
        ab = m.get('absent_nodes', [])
        if not isinstance(ab, list):
            E.at(name + '.meta.absent_nodes', 'a list of the core nodes this build leaves out')
    # facts
    if not isinstance(D['facts'], list) or not D['facts']:
        E.at(name + '.facts', 'a non-empty list')
    else:
        for i, f in enumerate(D['facts']):
            _need(f, ('id', 'label', 'value'), f'{name}.facts[{i}]', E)
    # presets
    P = D['presets']
    if not isinstance(P, dict):
        E.at(name + '.presets', 'object')
        P = {}
    if strict:
        miss = [p for p in required_presets(S) if p not in P]
        if miss:
            E.at(name + '.presets', f'missing {miss}')
    for pn, p in P.items():
        w = f'{name}.presets.{pn}'
        if not _need(p, ('cam', 'tgt', 'tag', 'cap'), w, E):
            continue
        extra = set(p) - PRESET_KEYS
        if extra:
            E.at(w, f'unknown keys {sorted(extra)}')
        if not _vec(p['cam']) or not _vec(p['tgt']) or ('up' in p and not _vec(p['up'])):
            E.at(w, 'cam / tgt / up are [x, y, z]')
        if 'sec' in p and not (isinstance(p['sec'], list) and len(p['sec']) == 3 and p['sec'][0] in 'xyz'
                               and _num(p['sec'][1]) and isinstance(p['sec'][2], bool)):
            E.at(w, 'sec is [axis, position, flip]')
        for k in ('focus', 'show', 'hide'):
            _groups_ok(p.get(k), f'{w}.{k}', E)
        if 'variant' in p and p['variant'] not in VARIANTS:
            E.at(w, 'variant')
    for c in CARDS:
        if strict and card_applies(c, S, B) and c['preset'] and c['preset'] not in P:
            E.at(name + '.presets', f'card {c["id"]} needs preset {c["preset"]!r}')
    # explode
    X = D['explode']
    if _need(X, ('order', 'offsets', 'steps', 'done'), name + '.explode', E):
        _groups_ok(X['order'], name + '.explode.order', E)
        if set(X['offsets']) != set(X['order']):
            E.at(name + '.explode', 'offsets must cover exactly the order')
        if len(X['steps']) != len(X['order']):
            E.at(name + '.explode', 'one step text per group in order')
    # controls
    ids = set()
    for i, c in enumerate(D['controls'] if isinstance(D['controls'], list) else []):
        w = f'{name}.controls[{i}]'
        k = c.get('kind') if isinstance(c, dict) else None
        if k not in CONTROL_KINDS:
            E.at(w, f'kind {k!r}')
            continue
        _need(c, CONTROL_KEYS[k], w, E)
        if c.get('id') in ids:
            E.at(w, 'duplicate id')
        ids.add(c.get('id'))
        for vk in ('pivot', 'axis', 'plunger_axis', 'pin_from', 'pin_to', 'from', 'to'):
            if vk in c and not _vec(c[vk]):
                E.at(w, f'{vk} is [x, y, z]')
        if nodes is not None:
            for nk in ('node', 'plunger'):
                if c.get(nk) and c[nk] not in nodes:
                    E.at(w, f'{nk} {c[nk]!r} is not a node')
    kinds = [c.get('kind') for c in D['controls'] if isinstance(c, dict)]
    ncrank = 0 if keyless else 4
    if kinds.count('crank') != ncrank or kinds.count('flexure') != SIDE_KEY_COUNT[S] or 'pin' not in kinds or 'plug' not in kinds:
        E.at(name + '.controls', f'{ncrank} crank, {SIDE_KEY_COUNT[S]} flexure, 1 pin (reset), 1 plug (USB) controls')
    # keys (null on a keyless build)
    if keyless:
        if D['keys'] is not None:
            E.at(name + '.keys', 'null on a build without bottom keys')
    else:
        validate_keys(D['keys'], name + '.keys', E, nodes)
    # drawings
    names = set()
    for i, d in enumerate(D['drawings'] if isinstance(D['drawings'], list) else []):
        validate_drawing(d, f'{name}.drawings[{i}:{d.get("name") if isinstance(d, dict) else "?"}]', E)
        if isinstance(d, dict):
            if d.get('name') in names:
                E.at(name + '.drawings', f'duplicate {d.get("name")!r}')
            names.add(d.get('name'))
    if strict:
        miss = [n for n in required_drawings(S, B) if n not in names]
        if miss:
            E.at(name + '.drawings', f'missing {miss}')
    # cards: one block per card that applies (may be {}), nothing for unknown cards
    C = D['cards']
    if not isinstance(C, dict):
        E.at(name + '.cards', 'object')
    else:
        for k in C:
            if k not in CARD_IDS:
                E.at(name + '.cards', f'unknown card {k!r}')
        if strict:
            for c in CARDS:
                if card_applies(c, S, B) and c['id'] not in C:
                    E.at(name + '.cards', f'missing block for card {c["id"]!r}')
        _card_blocks(C, S, B, name + '.cards', E)
    _checks(D['checks'], name + '.checks', E)
    for i, a in enumerate(D['assembly'] if isinstance(D['assembly'], list) else []):
        w = f'{name}.assembly[{i}]'
        if _need(a, ('id', 'title', 'text', 'groups'), w, E):
            _groups_ok(a['groups'], w + '.groups', E)
            if a.get('preset') and a['preset'] not in P:
                E.at(w, f'preset {a["preset"]!r} unknown')
    if not D['assembly']:
        E.at(name + '.assembly', 'no steps')
    dl = D['downloads']
    if _need(dl, ('file', 'zip', 'zip_bytes', 'js_bytes', 'groups', 'readme'), name + '.downloads', E):
        if dl['file'] != fname('models', S):
            E.at(name + '.downloads.file', f'must be {fname("models", S)}')
        if not re.match(r'^silkscreen-[a-z0-9.-]+\.zip$', dl['zip']):
            E.at(name + '.downloads.zip', 'silkscreen-<...>.zip, lower case')
        if strict:
            _downloads_layout(dl, name + '.downloads', E, S)
        for g in dl['groups']:
            if _need(g, ('id', 'label', 'what', 'files'), name + '.downloads.groups[]', E):
                for f in g['files']:
                    if not _need(f, ('path', 'bytes'), f'{name}.downloads.groups.{g["id"]}.files[]', E) \
                            or not isinstance(f['bytes'], int):
                        E.at(f'{name}.downloads.groups.{g["id"]}', 'files need path and integer bytes')
    for p in needs:
        try:
            v = _get(D, p)
            if v is None or v == '':
                E.at(name, f'bound number {p!r} is empty')
        except KeyError:
            E.at(name, f'bound number {p!r} does not resolve')
    return E


def _card_blocks(C, S, B, where, E):
    """Shapes of the structured card blocks (plain numbers are free-form; cards list what they bind)."""
    g = C.get('glance')
    if isinstance(g, dict) and not isinstance(g.get('bullets'), list):
        E.at(where + '.glance', 'bullets: [html]')
    z = C.get('zstack')
    if isinstance(z, dict):
        for i, b in enumerate(z.get('bars', [])):
            if not (_need(b, ('name', 'z'), f'{where}.zstack.bars[{i}]', E) and _vec(b['z'], 2)):
                E.at(f'{where}.zstack.bars[{i}]', 'z is [z0, z1]')
        if 'bars' not in z:
            E.at(where + '.zstack', 'bars: [{name, z: [z0, z1]}]')
    bat = C.get('battery')
    dm = bat.get('depth_map') if isinstance(bat, dict) else None
    if S == '368' and isinstance(bat, dict) and dm is None:
        E.at(where + '.battery', 'the 3.68 battery card needs depth_map')
    if dm is not None and _need(dm, ('x0', 'y0', 'res', 'nx', 'ny', 'depth', 'on', 'outline'), where + '.battery.depth_map', E):
        if len(dm['depth']) != dm['ny'] or any(len(r) != dm['nx'] for r in dm['depth']) or len(dm['on']) != dm['ny']:
            E.at(where + '.battery.depth_map', 'depth / on must be ny rows of nx')
    if S == '368' and isinstance(C.get('boardprep'), dict):
        _need(C['boardprep'], ('trim_y', 'trim_kicad_y', 'fit', 'remove', 'leave_off'), where + '.boardprep', E)
    ck = C.get('checks')
    if isinstance(ck, dict):
        ms = ck.get('measure')
        if not (isinstance(ms, list) and ms and all(isinstance(x, str) and x.strip() for x in ms)):
            E.at(where + '.checks.measure', '"Measure before printing": a list of HTML strings (Rev K block)')
    cmp_ = C.get('compare')
    if isinstance(cmp_, dict) and 'attribution' in cmp_ and 'Zorian22' not in cmp_['attribution']:
        E.at(where + '.compare', 'the X4 reference model is by Zorian22 (CC BY-NC-SA): keep the attribution')
    st = C.get('strip')
    if isinstance(st, dict) and B in STRIP_BUILDS:
        for i, s in enumerate(st.get('steps', [])):
            w = f'{where}.strip.steps[{i}]'
            if _need(s, ('t', 'cam', 'f', 'b'), w, E) and not (isinstance(s['cam'], list) and len(s['cam']) == 2
                                                                and _vec(s['cam'][0]) and _vec(s['cam'][1])):
                E.at(w, 'cam is [[camera xyz], [target xyz]]')
        if not st.get('steps'):
            E.at(where + '.strip', 'the light-strip build needs steps')


def validate_manifest(Mf, name='manifest'):
    E = Errors()
    if not _need(Mf, ('schema', 'generated', 'title', 'defaults', 'sizes', 'builds', 'groups', 'cards', 'files', 'load',
                      'nodes', 'parts', 'assets'), name, E):
        return E
    _ascii(Mf, name, E)
    if Mf['schema'] != SCHEMA:
        E.at(name, 'schema')
    d = Mf['defaults']
    if d.get('size') not in SIZES or d.get('build') not in BUILDS or d.get('variant') not in VARIANTS:
        E.at(name + '.defaults', 'size / build / variant')
    if set(Mf['sizes']) != set(SIZES) or not set(BUILDS) <= set(Mf['builds']) <= set(ALL_BUILDS):
        E.at(name, 'sizes and builds must list all of ' + str((SIZES, BUILDS)))
    for s, info in Mf['sizes'].items():
        _need(info, ('label', 'build_diff'), f'{name}.sizes.{s}', E)
        if 'builds' in info and (tuple(info['builds']) != builds_of(s) or not set(info['builds']) <= set(Mf['builds'])):
            E.at(f'{name}.sizes.{s}.builds', f'must be {list(builds_of(s))}')
    if [g['id'] for g in Mf['groups']] != GROUP_IDS:
        E.at(name + '.groups', 'must be sc_contract.GROUPS')
    if [c['id'] for c in Mf['cards']] != CARD_IDS:
        E.at(name + '.cards', 'must be sc_contract.CARDS')
    total = 0
    for f, info in Mf['files'].items():
        w = f'{name}.files.{f}'
        if _need(info, ('bytes', 'kind', 'sha1'), w, E):
            total += info['bytes']
            if info['bytes'] > LIMITS['file_bytes']:
                E.at(w, f'{info["bytes"]} bytes > 16 MB')
            k = kind_of(f)
            if k and k != info['kind']:
                E.at(w, f'kind {info["kind"]!r} but the name says {k!r}')
    if total > LIMITS['version_bytes']:
        E.at(name + '.files', f'{total} bytes > 64 MB per version')
    for s in SIZES:
        L = Mf['load'].get(s)
        w = f'{name}.load.{s}'
        if not _need(L, ('core', 'build', 'extras', 'data', 'models'), w, E):
            continue
        refs = [L['core'], L['extras'], L['models'], *L['build'].values(), *L['data'].values()]
        for r in refs:
            if r not in Mf['files']:
                E.at(w, f'{r!r} not in files')
        N = Mf['nodes'].get(s, {})
        if not _need(N, ('core', 'build', 'extras'), f'{name}.nodes.{s}', E):
            continue
        both = set(N['build'].get('std', [])) & set(N['build'].get('ls', []))
        # the builds may differ in display nodes (4.26: FT01C + 3 ribbons vs the plain panel + one FPC) and strip_*
        odd = set(N['build'].get('std', [])) ^ set(N['build'].get('ls', []))
        odd = {n for n in odd if not n.startswith(('panel_', 'ribbon_', 'strip_'))}
        if odd:
            E.at(f'{name}.nodes.{s}', f'both builds must have the same per-build nodes (bar panel_* ribbon_* strip_*): {sorted(odd)}')
        if both & set(N['core']):
            E.at(f'{name}.nodes.{s}', f'nodes in core and build: {sorted(both & set(N["core"]))}')
        P = Mf['parts'].get(s)
        _need(P, ('shared', 'per_build'), f'{name}.parts.{s}', E)
    return E


def validate_file(path, decode=True):
    path = Path(path)
    k = kind_of(path.name)
    raw = path.read_bytes()
    E = Errors()
    if any(b > 0x7F for b in raw):
        E.at(path.name, 'non-ASCII bytes')
    if k is None or k == 'models':
        return E
    obj = json.loads(raw)
    if k == 'manifest':
        return E + validate_manifest(obj, path.name)
    if k == 'data':
        return E + validate_data(obj, path.name)
    return E + validate_model(obj, path.name, decode=decode)


def b_all(mf, s):
    """True when the manifest loads every build of size s (older bundles carry the two full builds only)."""
    return all(b in mf['load'][s]['data'] for b in builds_of(s))


def validate_bundle(folder, decode=True):
    """Every file in a bundle folder, plus the cross-references between them."""
    folder = Path(folder)
    E = Errors()
    mf = json.loads((folder / 'manifest.json').read_text())
    E += validate_manifest(mf)
    for f, info in mf['files'].items():
        p = folder / f
        if not p.exists():
            E.at('bundle', f'{f} listed but missing')
            continue
        if p.stat().st_size != info['bytes']:
            E.at('bundle', f'{f}: {p.stat().st_size} bytes, manifest says {info["bytes"]}')
        if f.endswith(('.json', '.js', '.html', '.css')) and any(b > 0x7F for b in p.read_bytes()):
            E.at('bundle', f'{f}: non-ASCII bytes')
    for s in SIZES:
        L, N = mf['load'][s], mf['nodes'][s]
        core = json.loads((folder / L['core']).read_text())
        extras = json.loads((folder / L['extras']).read_text())
        E += validate_model(core, L['core'], decode)
        E += validate_model(extras, L['extras'], decode)
        for b in (builds_of(s) if b_all(mf, s) else BUILDS):
            bm = json.loads((folder / L['build'][b]).read_text())
            E += validate_model(bm, L['build'][b], decode)
            nodes = set(core['nodes']) | set(bm['nodes']) | set(extras['nodes'])
            D = json.loads((folder / L['data'][b]).read_text())
            E += validate_data(D, L['data'][b], nodes=nodes)
            if set(bm['nodes']) != set(N['build'][b]):
                E.at('bundle', f'{L["build"][b]} nodes differ from manifest.nodes')
        if set(core['nodes']) != set(N['core']) or set(extras['nodes']) != set(N['extras']):
            E.at('bundle', f'{s}: core / extras nodes differ from manifest.nodes')
    # across the sizes: the same switches on the same board, and no two different downloads with one file name
    D = {s: {b: json.loads((folder / mf['load'][s]['data'][b]).read_text()) for b in BUILDS} for s in SIZES}
    for b in BUILDS:
        cross_check_keys(D['426'][b]['keys'], D['368'][b]['keys'], E)
    names = [n for s in SIZES for n in download_names(D[s]['std']['downloads'], s).values()]
    if len(set(names)) != len(names):
        E.at('bundle', f'download file names repeat across the sizes: {sorted(names)}')
    return E


# ---- a hand-made sample (the self-test; also a stand-in for page work before the adapters run) -------------
def sample(size='426', build='std'):
    """A small but complete data-S-B object. The keys geometry is the real one (both sizes share it); rest rows
    are the independent values from 4.26 bottom-keys.json / x3 crank.json."""
    sq = lambda u, v, s=0.5: [[[u, v], [u + s, v], [u + s, v + s], [u, v + s], [u, v]]]
    def dwg(n, axis='x', at=0.0, ids=('tub',)):
        return {'name': n, 'axis': axis, 'at': at, 'window': [-10.0, 10.0, -8.0, 9.0],
                'layers': [{'id': i, 'role': 'case' if i in ('tub',) else 'part', 'polys': [sq(-9.0 + k, -7.0)]}
                           for k, i in enumerate(ids)], 'beyond': [], 'notes': {}}
    side = {'426': ['SW1', 'SW4', 'SW5', 'SW7', 'SW10'], '368': ['SW1', 'SW4', 'SW7']}[size]
    K = {
        'refs': list(BOTTOM_REFS), 'x': {'SW9': 11.4975, 'SW8': 23.4975, 'SW3': 36.4975, 'SW2': 48.4975},
        'draw_ref': DRAW_REF, 'rod': {'yz': [-2.5, 0.6], 'd': 1.75, 'cut': 63.25, 'gate': 'printed side gate'},
        'axis': [1, 0, 0], 'theta_built': 0.0, 'pad': {'c': [-7.45, -0.80], 'r': 0.6},
        'nose': {'r': 1.0, 'c': {'M': [-2.92, -2.35], 'T': [-3.20, -2.35]}},
        'switches': {
            'M': {'part': 'MJTP1117', 'crank': 'crank-M', 'label': 'APEM MJTP1117 boards', **switch_geom('M'),
                  'travel': {'click': 0.25, 'bottom': 0.45}, 'force_N': [1.27, 1.86]},
            'T': {'part': 'TS365ZJ', 'crank': 'crank-T', 'label': 'SHOU HAN TS365ZJ (every JLC board)', **switch_geom('T'),
                  'travel': {'click': 0.25, 'bottom': 0.45}, 'force_N': [1.96, 2.94]}},
        'default_variant': 'T',
        'rest_rows': [{'variant': v, 'face_dy': dy, 'theta': th, 'key_dz': kd, 'source': src}
                      for v, dy, th, kd, src in (
                          ('M', -0.2, -3.91, -0.340, 'crank.json rest MJTP1117 -0.2'),
                          ('M', 0.0, 0.0, 0.0, 'crank.json rest MJTP1117 +0.0'),
                          ('M', 0.2, 3.87, 0.331, 'bottom-keys.json static MJTP crank-M delta -0.2'),
                          ('T', -0.2, -3.92, -0.342, 'crank.json rest TS365ZJ -0.2'),
                          ('T', 0.0, 0.0, 0.0, 'crank.json rest TS365ZJ +0.0'),
                          ('T', 0.2, 3.86, 0.330, 'crank.json rest TS365ZJ +0.2'))],
        'forces': {'lever': {'input_arm': 4.95, 'output_arm': 2.95, 'ratio': 1.678}, 'press_y': -6.2, 'mu': 0.3,
                   'finger_N': {'M': [1.148, 1.659], 'T': [1.745, 2.594]}, 'press_ys': [-7.7, -6.2, -4.6],
                   'table': {'MJTP 1.27': {'mu_0.3': [1.023, 1.148, 1.483]}, 'MJTP 1.86': {'mu_0.3': [1.475, 1.659, 2.15]},
                             'TS365 1.96': {'mu_0.3': [1.552, 1.745, 2.263]}, 'TS365 2.94': {'mu_0.3': [2.304, 2.594, 3.371]}},
                   'source': 'mechanics.json key_forces'},
        'hooks': {'W_OUT_mm': 1.0, 'hook_dx': [3.95, 4.95], 'hook_h_mm': 0.8, 'hook_tip_y': -8.55, 'hook_z_rest': [0.47, 1.27],
                  'slot_dx': [2.65, 5.4], 'slot_back_y': -8.95, 'slot_roof_z': 2.27,
                  'face_down_free_travel_mm': [0.304, 1.648], 'rest_load_on_plunger_N': 0.0041, 'key_mass_g': 0.194,
                  'source': 'mechanics.json key_hooks'},
        'rod_check': {'press_N': 20.0, 'bending_MPa': 14.2, 'deflection_um': 7.6, 'source': 'mechanics.json crank_stress'},
        'checks': [{'id': 'static', 'label': 'static: no undesigned overlaps', 'ok': True}],
        'instances': {'crank': {'M': 'crank_M', 'T': 'crank_T'}, 'switch': {'T': ['sw_T_body', 'sw_T_nub'], 'M': 'board'}},
    }
    K['derived'] = {v: derive(K, v) for v in VARIANTS}
    kx = K['x']
    controls = [{'id': r, 'label': r, 'kind': 'crank', 'ref': r, 'node': f'key_{r}', 'crank': f'crank_{r}',
                 'plunger': f'nub_{r}', 'pivot': [kx[r], -2.5, 0.6], 'axis': [1, 0, 0]} for r in BOTTOM_REFS]
    controls += [{'id': r, 'label': r, 'kind': 'flexure', 'ref': r, 'node': f'skey_{r}', 'plunger': f'nub_{r}',
                  'plunger_axis': [-1, 0, 0], 'pivot': [62.0, 50.0, 0.0], 'axis': [0, 0, 1], 'sign': 1, 'length': 8.0,
                  'gap': 0.25, 'click_travel': 0.5, 'max_travel': 0.7} for r in side]
    controls += [{'id': 'SW11', 'label': 'Reset (pin)', 'kind': 'pin', 'ref': 'SW11', 'plunger': 'nub_SW11',
                  'plunger_axis': [-1, 0, 0], 'pin_from': [70.0, 30.2, -2.7], 'pin_to': [61.0, 30.2, -2.7],
                  'click_travel': 0.25, 'max_travel': 0.45},
                 {'id': 'usb', 'label': 'USB-C plug', 'kind': 'plug', 'axis': [-1, 0, 0], 'from': [80.0, 41.0, -2.0],
                  'to': [64.6, 41.0, -2.0], 'insert_mm': 6.6}]
    pre = {p: {'cam': [100.0, -150.0, 140.0], 'tgt': [30.0, 50.0, -1.0], 'tag': p, 'cap': '<b>' + p + '.</b>'}
           for p in required_presets(size)}
    pre['keys'].update({'sec': ['x', kx['SW8'], False], 'focus': ['keys', 'rod', 'tub', 'pcba', 'lid'], 'press': 'SW8',
                        'highlight': ['key_*', 'crank_*']})
    draws = [dwg(n) for n in required_drawings(size, build) if n != 'key']
    draws.append(dwg('key', 'x', kx['SW8'], KEY_DRAWING_LAYERS))
    order = ['tub', 'display', 'keys', 'rod', 'midplate', 'battery', 'pcba', 'lid', 'screws']
    cards = {c['id']: {} for c in CARDS if card_applies(c, size, build)}
    cards['glance']['bullets'] = ['One page, two sizes.']
    cards['checks']['measure'] = ['<b>The battery pack.</b> Measure it.']
    cards['joint'].update({'latch_count': 13, 'tongue_len': 1.2})
    cards['zstack']['bars'] = [{'name': 'PCB', 'z': [0.0, 1.6]}]
    cards['compare']['attribution'] = 'Xteink X4 reference model by Zorian22, CC BY-NC-SA'
    cards['strip']['steps'] = [{'t': 'Fitted', 'cam': [[-96, -92, 150], [26, 48, 2]], 'f': 1, 'b': '<p>Fitted.</p>'}]
    if size == '368':
        cards['battery']['depth_map'] = {'x0': -1.5, 'y0': -2.0, 'res': 1.0, 'nx': 2, 'ny': 2,
                                         'depth': [[0.0, 1.2], [0.4, 0.0]], 'on': [[True, True], [True, False]],
                                         'outline': [[0, 0], [1, 0], [1, 1]]}
        cards['boardprep'].update({'trim_y': 86.25, 'trim_kicad_y': 62.0, 'fit': ['R72', 'R74'],
                                   'remove': ['R36', 'R73', 'R62'], 'leave_off': ['SW5']})
    return {
        'schema': SCHEMA, 'size': size, 'build': build,
        'meta': {'title': 'Silkscreen case', 'size_label': SIZE_LABELS[size],
                 'panel': {'part': 'GDEY0426T82', 'label': 'FT01C', 'touch': True, 'front_light': True, 'ribbons': 3},
                 'envelope': [-4.09, 64.09, -9.4, 115.6, -6.7, 6.0], 'size': [68.2, 125.0, 12.7], 'body': [68.2, 125.0, 12.7],
                 'z': {'front': 6.0, 'back': -6.7, 'seam': -1.2}, 'active': {'cx': 30.0, 'cy': 55.0, 'w': 53.0, 'h': 90.0},
                 'frame': 'X = KiCad x - 44.24, Y = 148.25 - KiCad y, Z = 0 at the board rear',
                 'printed': {'parts': [{'name': 'tub', 'count': 1, 'file': 'tub-standard.stl'}], 'count': 12},
                 'side_keys': side, 'bottom_keys': list(BOTTOM_REFS), 'reset': 'SW11',
                 'source': {'project': 'sample', 'generated': '2026-09-27'}},
        'facts': [{'id': 'envelope', 'label': 'Envelope', 'value': '68.2 x 125.0 x 12.7', 'unit': 'mm'}],
        'presets': pre,
        'explode': {'order': order, 'offsets': {g: -10.0 * i for i, g in enumerate(order)},
                    'steps': [f'Step {g}.' for g in order], 'done': '<b>Assembled.</b>'},
        'controls': controls, 'keys': K, 'drawings': draws, 'cards': cards,
        'checks': [{'id': 'interference', 'label': 'No part overlaps another', 'ok': True, 'source': 'interference.json'}],
        'assembly': [{'id': 'tub', 'title': 'Tub face down', 'text': 'Tub face down.', 'groups': ['tub'], 'preset': 'assembly'}],
        'downloads': {'file': fname('models', size), 'zip': f'silkscreen-case-{size}.zip', 'zip_bytes': 1, 'js_bytes': 2,
                      'readme': 'README.txt', 'groups': [
                          {'id': 'shared', 'label': 'Shared parts', 'what': 'both builds', 'files': [{'path': 'shared/lid.stl', 'bytes': 1}]},
                          {'id': 'std', 'label': 'Standard build', 'what': 'its tub',
                           'files': [{'path': 'standard/tub-standard.stl', 'bytes': 1, 'builds': ['std']}]},
                          {'id': 'ls', 'label': 'Light-strip build', 'what': 'its tub',
                           'files': [{'path': 'light-strip/tub-light-strip.stl', 'bytes': 1, 'builds': ['ls']}]},
                          # the size's extra builds (the 4.26's chinless cases): one group each, in builds_of order
                          *({'id': b, 'label': BUILD_LABELS[b] + ' build', 'what': 'its tub',
                             'files': [{'path': f'{ZIP_DIRS[b]}tub-{BUILD_DIRS[b]}.stl', 'bytes': 1, 'builds': [b]}]}
                            for b in EXTRA_BUILDS.get(size, ())),
                          {'id': 'rod', 'label': 'Rod notes', 'what': 'the rod', 'files': [{'path': 'ROD.txt', 'bytes': 1}]},
                          {'id': 'dummy', 'label': 'PCBA dummy', 'what': 'a stand-in board',
                           'files': [{'path': 'dummy/pcba-dummy.stl', 'bytes': 1}]}]},
    }


def sample_nodes(size='426', build='std'):
    side = sample(size, build)['meta']['side_keys']
    return ({'tub', 'lid', 'midplate', 'rod', 'gate', 'crank_M', 'crank_T', 'sw_T_body', 'sw_T_nub', 'pcba_pcb',
             'pcba_switch', 'nub_SW11', 'panel_epd', 'battery_cell', 'screw_H3', 'screw_H4', 'screw_top', 'ribbon_main'}
            | {f'{p}_{r}' for p in ('key', 'nub', 'swbody') for r in BOTTOM_REFS}
            | {f'skey_{r}' for r in side} | {f'nub_{r}' for r in side})


def sample_manifest():
    files, load, nodes, parts = {}, {}, {}, {}
    for S in SIZES:
        core = sorted(n for n in sample_nodes(S) if n != 'tub' and not (S == '368' and n.startswith('key_')))
        per = ['tub'] + ([f'key_{r}' for r in BOTTOM_REFS] if S == '368' else [])
        nodes[S] = {'core': core, 'build': {'std': per, 'ls': per + ['strip_diodes']}, 'extras': ['cmp_x4', 'dummy_pcba']}
        load[S] = {'core': fname('core', S), 'extras': fname('extras', S), 'models': fname('models', S),
                   'build': {B: fname('build', S, B) for B in BUILDS}, 'data': {B: fname('data', S, B) for B in BUILDS}}
        for f in [load[S]['core'], load[S]['extras'], load[S]['models'], *load[S]['build'].values(), *load[S]['data'].values()]:
            files[f] = {'bytes': 1000, 'kind': kind_of(f), 'sha1': '0' * 40, 'size': S}
        parts[S] = {'shared': ['lid', 'midplate', 'crank-M', 'crank-T'], 'per_build': ['tub'] + (['key'] if S == '368' else [])}
    files['strip.json'] = {'bytes': 36000, 'kind': 'asset', 'sha1': '0' * 40}
    return {'schema': SCHEMA, 'generated': '2026-09-27T00:00:00', 'title': 'Silkscreen case', 'defaults': dict(DEFAULTS),
            'sizes': {S: {'label': SIZE_LABELS[S], 'build_diff': 'tub differs' if S == '426' else 'tub + 4 keys differ'}
                      for S in SIZES},
            'builds': {B: {'label': BUILD_LABELS[B]} for B in BUILDS}, 'groups': GROUPS, 'cards': CARDS,
            'files': files, 'load': load, 'nodes': nodes, 'parts': parts,
            'assets': {'strip': 'strip.json', 'optics': 'optics_heatmaps.png'}}


def selftest():
    ok = True
    E = validate_manifest(sample_manifest())
    print('sample manifest:', 'OK' if not E else E)
    ok &= not E
    bad = sample_manifest()
    bad['files']['core-426.json']['bytes'] = 17 * 1024 * 1024
    bad['load']['368']['core'] = 'core-368x.json'
    E = validate_manifest(bad)
    hit = any('16 MB' in e for e in E) and any('core-368x.json' in e for e in E)
    print('  broken manifest (17 MB file, dangling load ref):', 'caught' if hit else f'NOT CAUGHT {E}')
    ok &= hit
    for s in SIZES:
        for b in BUILDS:
            E = validate_data(sample(s, b), f'sample-{s}-{b}', nodes=sample_nodes(s, b),
                              needs=('cards.joint.latch_count', 'keys.derived.T.theta_click'))
            print(f'sample {s} {b}:', 'OK' if not E else E)
            ok &= not E
    # broken copies must fail, each for the reason given
    def broken(desc, fn, expect):
        nonlocal ok
        D = copy.deepcopy(sample('368', 'ls'))
        fn(D)
        E = validate_data(D, 'broken', nodes=sample_nodes('368', 'ls'))
        hit = any(expect in e for e in E)
        print(f'  broken ({desc}):', 'caught' if hit else f'NOT CAUGHT {E[:3]}')
        ok &= hit
    broken('rest row sign flipped', lambda D: D['keys']['rest_rows'][2].update(theta=-3.87), 'rest_rows[2]')
    broken('key_dz as lift (up)', lambda D: D['keys']['rest_rows'][2].update(key_dz=-0.331), 'key_dz')
    broken('derived stale', lambda D: D['keys']['derived']['T'].update(theta_click=5.0), 'derived.T.theta_click')
    broken('preset missing', lambda D: D['presets'].pop('boardprep'), "'boardprep'")
    broken('unknown group', lambda D: D['presets']['keys'].update(focus=['keys', 'crank']), 'unknown group')
    broken('non-ASCII text', lambda D: D['facts'][0].update(value='68 ' + chr(0xD7) + ' 125'), 'non-ASCII')
    broken('drawing points outside', lambda D: D['drawings'][0]['layers'][0]['polys'][0][0].append([99, 0]), 'outside the window')
    broken('key drawing lacks crank_T', lambda D: [d['layers'].pop(4) for d in D['drawings'] if d['name'] == 'key'], 'crank_T')
    broken('control node unknown', lambda D: D['controls'][0].update(node='key_SW99'), "'key_SW99'")
    broken('two side keys on 3.68', lambda D: D['meta']['side_keys'].pop(), 'side keys')
    broken('depth map rows', lambda D: D['cards']['battery']['depth_map']['depth'].pop(), 'ny rows')
    broken('hooks W_OUT missing', lambda D: D['keys']['hooks'].pop('W_OUT_mm'), 'hooks')
    broken('hooks roof off W_OUT', lambda D: D['keys']['hooks'].update(slot_roof_z=2.47), 'slot roof')
    broken('finger force for T missing', lambda D: D['keys']['forces']['finger_N'].pop('T'), 'finger_N')
    broken('attribution dropped', lambda D: D['cards']['compare'].update(attribution='X4 compare'), 'Zorian22')
    broken('TS365 worst plunger drawn as nominal', lambda D: D['keys']['switches']['T'].update(nub_z=[-3.05, -1.05]),
           'switches.T.nub_z')
    broken('MJTP housing from the STEP probe', lambda D: D['keys']['switches']['M'].update(housing_yz=[-1.62, -4.493, 6.0, 0.0]),
           'switches.M.housing_yz')
    broken('force table in the 4.26 mechanics shape', lambda D: D['keys']['forces'].update(
        table={'MJTP 1.27 mu 0.3': {'y -6.20': 1.12}}), 'forces.table')
    broken('measure list dropped', lambda D: D['cards']['checks'].pop('measure'), 'checks.measure')
    broken('flat zip', lambda D: D['downloads']['groups'][1]['files'][0].update(path='tub-standard.stl'), 'standard/<file>')
    broken('group named like a build zip', lambda D: D['downloads'].update(zip='silkscreen-case-3.68.zip') or
           D['downloads']['groups'][0].update(id='standard'), 'group ids')
    K4, K3 = copy.deepcopy(sample('426')['keys']), copy.deepcopy(sample('368')['keys'])
    K4['switches']['M']['housing_yz'] = [-1.62, -4.493, 6.0, 0.0]
    E = cross_check_keys(K4, K3)
    hit = any('switches.M.housing_yz' in e for e in E)
    print('  cross-size switch mismatch:', 'caught' if hit else f'NOT CAUGHT {E}')
    ok &= hit
    ok &= not cross_check_keys(sample('426')['keys'], sample('368')['keys'])
    return ok


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a or a[0] == '--selftest':
        sys.exit(0 if selftest() else 1)
    if a[0] == '--bundle':
        E = validate_bundle(a[1])
    else:
        E = Errors()
        for p in a:
            E += validate_file(p)
    print('\n'.join(E) if E else 'OK')
    sys.exit(1 if E else 0)
