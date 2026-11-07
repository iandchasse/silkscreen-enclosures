"""Two optional colour switches for the Silkscreen case plates (2026-11-06; make_plates.py puts them in every plate file and project).
Both are OFF as shipped: a body in the file that prints nothing until the user switches it on (the same idea as the two-colour logo,
print/README.md). Nothing under case-*/src is touched and no tub or lid geometry changes.

1. Three lines on the tub's front chin (the idea is @juno_last's case design). A chin tub (the 4.26 with bottom keys, standard and light
   strip, and the 3.68 standard) carries three straight horizontal lines with rounded ends between the bottom-key openings and the
   screen window's bottom edge, centred on the case's centre line, as three modifier volumes of the tub, each 0.6 mm (3 layers)
   deep from the front face (the face prints down, so the lines are the tub's first three layers). Switched ON by changing a body's type
   to Negative Volume (the lines are engraved, in the case colour) or by giving it filament 2 (a second colour, flush).
   The bodies are STLs in the tub's print frame: print/4.26/tub-front-lines.stl (the standard and the light-strip tub share them) and
   print/3.68/tub-front-lines.stl, made by `python -B color_options.py write` from the built tubs and checked against every tub they
   go on (load_lines): inside the solid face on all three layers and 1.2 mm or more from the key openings and the window.
2. The side keys in a second colour. Every lid carries one modifier box over its footprint from the layer boundary above the middle tab
   between the side keys to the top. Filament 2 on the box colours everything of the lid above that height: the keys' pads, their pegs
   and the lid's inner pegs and clips (hidden when assembled). The box is made from each lid's own footprint at run time (side_key_box).
   `python -B color_options.py report` lists what the box holds.

    python -B color_options.py write     the line STLs into print/4.26 and print/3.68
    python -B color_options.py report    the numbers and the classification of what lies above the split (needs the built lids)
"""
import glob
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import trimesh
from shapely.geometry import LineString, Point, Polygon
from shapely.geometry.polygon import orient

HERE = Path(__file__).resolve().parent
PRINT = HERE.parent / 'print'
LAYER = 0.2                              # mm: the projects' layer height (make_plates / configs_slice.LAYER)
LINE_DEPTH = 0.6                         # mm from the front face: three layers
LINE_SIZES = ((1.0, 2.5), (1.0, 2.2), (0.9, 2.0), (0.8, 1.8), (0.8, 1.6))   # (width, pitch) tried in order; the first that fits
LINE_MARGIN = 1.2                        # mm: the lines' clearance from the key openings and from the window, on all three layers
LAYER_MIDS = (0.1, 0.3, 0.5)             # the three layers' slicing planes (the openings' first 0.09 is a skin too thin to print)
LINES_NAME = 'front lines {i}/3: off (Negative Volume = engrave, filament 2 = colour)'
BOX_NAME = 'side keys colour: off (filament 2 = second colour above z {z:g})'
# the lid's middle tab (its wall between the side keys) tops out at SEAM - Z_BACK in the lid's print frame, per case; report() reads the
# params and proves it on the STL, side_key_box() asserts the lids of a run against it
WALL_TOP = {'case-426': 2.95, 'case-368': 4.685}
LINE_FILES = {'case-426': PRINT / '4.26' / 'tub-front-lines.stl', 'case-368': PRINT / '3.68' / 'tub-front-lines.stl'}


def build_of(stl):
    """(case folder name, build slug) of a built part: enclosures/<case>/out/<slug>/print/<part>.stl."""
    p = Path(stl).resolve()
    return p.parents[3].name, p.parents[1].name


# ---------------------------------------------------------------- 1. the lines

def _rings(m, z):
    """(outer, holes) of the tub's section at height z: shapely polygons in the print frame (a loop inside the outline is a hole)."""
    s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    rings = [Polygon(r[:, :2]).buffer(0) for r in s.discrete if len(r) > 3]
    rings = sorted((r for r in rings if r.area > 0.05), key=lambda r: -r.area)
    return rings[0], rings[1:]


def measure_chin(tub):
    """The tub's chin as laid on its first three layers (tub: a trimesh in its print frame, front face on the bed), or None without
    one: {'x': (x0, x1) the bottom-key openings' span, 'y_win': the window's chin-side edge, 'y_key': the openings' window-side edge,
    'width': the tub's x extent} with the extremes over the layers 0.1, 0.3 and 0.5."""
    y_win, y_key, x0, x1 = -1e9, 1e9, 1e9, -1e9
    for z in LAYER_MIDS:
        outer, holes = _rings(tub, z)
        if not holes:
            return None
        win = holes[0]
        keys = [h for h in holes[1:] if h.bounds[1] > win.bounds[3] and h.area < 0.2 * win.area]
        if not keys:
            return None
        y_win = max(y_win, win.bounds[3])
        y_key = min(y_key, min(h.bounds[1] for h in keys))
        x0, x1 = min(x0, min(h.bounds[0] for h in keys)), max(x1, max(h.bounds[2] for h in keys))
    return {'x': (float(x0), float(x1)), 'y_win': float(y_win), 'y_key': float(y_key), 'width': float(tub.bounds[1][0])}


def _prism(poly, z0, z1):
    """A watertight prism of a convex shapely polygon between z0 and z1."""
    pts = np.array(orient(poly, 1.0).exterior.coords)[:-1]
    n = len(pts)
    v = np.vstack([np.c_[pts, np.full(n, z0)], np.c_[pts, np.full(n, z1)]])
    f = [[0, i + 1, i] for i in range(1, n - 1)] + [[n, n + i, n + i + 1] for i in range(1, n - 1)]
    for i in range(n):
        j = (i + 1) % n
        f += [[i, j, n + j], [i, n + j, n + i]]
    m = trimesh.Trimesh(v, np.array(f), process=False)
    if m.volume < 0:
        m.invert()
    assert m.is_watertight and m.volume > 0
    return m


def line_layout(chins):
    """The lines for one or more tubs that share them: -> {'width', 'pitch', 'length', 'x', 'ys', 'gap', 'margin_win', 'margin_key'}.
    The lines are centred in the narrowest gap between the openings and the window over all the tubs, as long as the openings' span,
    as wide and as far apart as LINE_SIZES allow with LINE_MARGIN to both sides (the first size that fits)."""
    y_win = max(c['y_win'] for c in chins)
    y_key = min(c['y_key'] for c in chins)
    x0, x1 = min(c['x'][0] for c in chins), max(c['x'][1] for c in chins)
    assert all(abs((c['x'][0] + c['x'][1]) / 2 - c['width'] / 2) < 0.05 for c in chins), 'the key row is not on the case centre line'
    gap = y_key - y_win
    for w, p in LINE_SIZES:
        if 2 * p + w <= gap - 2 * LINE_MARGIN:
            yc = (y_win + y_key) / 2
            ys = [yc - p, yc, yc + p]
            return {'width': w, 'pitch': p, 'length': x1 - x0, 'x': (x0, x1), 'ys': ys, 'gap': gap,
                    'margin_win': ys[0] - w / 2 - y_win, 'margin_key': y_key - (ys[2] + w / 2), 'shrunk': (w, p) != LINE_SIZES[0]}
    raise SystemExit(f'three lines do not fit the gap of {gap:.2f} mm even at {LINE_SIZES[-1]}')


def line_meshes(lay):
    """The three line bodies of a layout (one watertight mesh each, in the print frame, from the front face to LINE_DEPTH)."""
    x0, x1 = lay['x']
    w = lay['width']
    out = []
    for y in lay['ys']:
        poly = LineString([(x0 + w / 2, y), (x1 - w / 2, y)]).buffer(w / 2, quad_segs=8)
        out.append(_prism(poly, 0.0, LINE_DEPTH))
    return out


def write():
    """The two line STLs (print/4.26, print/3.68), from the built tubs. The 4.26's standard and light-strip tubs share one file: the lines are
    centred in the narrower of their two gaps."""
    for case, slugs in (('case-426', ('standard', 'light-strip')), ('case-368', ('standard',))):
        chins = []
        for s in slugs:
            tub = trimesh.load(HERE / case / 'out' / s / 'print' / 'tub.stl', force='mesh')
            c = measure_chin(tub)
            assert c, (case, s, 'no chin')
            chins.append(c)
        lay = line_layout(chins)
        m = trimesh.util.concatenate(line_meshes(lay))
        LINE_FILES[case].parent.mkdir(exist_ok=True)
        m.export(LINE_FILES[case])
        print(f'{LINE_FILES[case].relative_to(HERE.parent)}: width {lay["width"]}, pitch {lay["pitch"]}, length {lay["length"]:.2f}, '
              f'x {lay["x"][0]:.2f}-{lay["x"][1]:.2f}, y {[round(y, 3) for y in lay["ys"]]}, gap {lay["gap"]:.2f} '
              f'(window edge to openings), margins {lay["margin_win"]:.2f} / {lay["margin_key"]:.2f}'
              + (', SHRUNK from 1.0 / 2.5' if lay['shrunk'] else ''))


_lines_cache = {}


def tub_lines(stl, base, faces):
    """The three line bodies for the tub at stl (built part enclosures/<case>/out/<slug>/print/tub.stl; base, faces: its vertices in the print
    frame, min corner 0, and its faces) -> [(volume name, mesh)] in that frame, or [] for a build without lines (a chinless tub; the 3.68's
    light-strip tub, which is not released). The STL in print/ is checked against this very tub."""
    case, slug = build_of(stl)
    if 'chinless' in slug or (case == 'case-368' and slug != 'standard'):
        return []
    key = (case, hash(np.ascontiguousarray(base).tobytes()))
    if key not in _lines_cache:
        tub = trimesh.Trimesh(base, faces, process=False)
        chin = measure_chin(tub)
        if chin is None:
            raise SystemExit(f'{stl}: a build with bottom keys but no key openings found on the tub\'s first layers')
        f = LINE_FILES[case]
        bodies = sorted(trimesh.load(f, force='mesh').split(only_watertight=False), key=lambda b: b.bounds[0][1])
        if len(bodies) != 3:
            raise SystemExit(f'{f}: {len(bodies)} bodies, want 3 (python -B color_options.py write)')
        sec = [_rings(tub, z) for z in LAYER_MIDS]
        for i, b in enumerate(bodies, start=1):
            lo, hi = b.bounds
            ok = abs(lo[2]) < 1e-3 and abs(hi[2] - LINE_DEPTH) < 1e-3 and abs((lo[0] + hi[0]) / 2 - chin['width'] / 2) < 0.05
            ok = ok and chin['y_win'] + LINE_MARGIN - 1e-3 <= lo[1] and hi[1] <= chin['y_key'] - LINE_MARGIN + 1e-3
            ok = ok and chin['x'][0] - 1e-3 <= lo[0] and hi[0] <= chin['x'][1] + 1e-3
            foot = Polygon(np.array([v[:2] for v in b.vertices])).convex_hull
            for outer, holes in sec:
                ok = ok and outer.contains(foot) and all(not h.intersects(foot) for h in holes)
            if not ok:
                raise SystemExit(f'{f}: line {i} does not fit {stl} (python -B color_options.py write)')
        _lines_cache[key] = [(LINES_NAME.format(i=i), trimesh.Trimesh(b.vertices.copy(), b.faces.copy(), process=False))
                             for i, b in enumerate(bodies, start=1)]
    return _lines_cache[key]


# ---------------------------------------------------------------- 2. the side keys' colour

def wall_top(build_dir):
    """The top of the lid's middle tab in its print frame, read off the built lid: the highest point of lid_body.stl (the lid without its side
    keys) within 1.5 mm of its outline, less the lid's own lowest z."""
    body = trimesh.load(Path(build_dir) / 'lid_body.stl', force='mesh')
    zb = trimesh.load(Path(build_dir) / 'lid.stl', force='mesh').bounds[0][2]
    v, (lo, hi) = body.vertices, body.bounds
    band = (v[:, 0] < lo[0] + 1.5) | (v[:, 0] > hi[0] - 1.5) | (v[:, 1] < lo[1] + 1.5) | (v[:, 1] > hi[1] - 1.5)
    return float(v[band][:, 2].max() - zb)


def split_layer(top):
    """The box's bottom: the bottom of the first layer whose slicing plane (its mid-height) lies over the tab's top, as the slicer lays the tab (a
    feature prints to the layer whose mid-plane is under its CAD top): 2.95 -> 3.0, 4.685 -> 4.6."""
    return round(LAYER * math.floor((top + LAYER / 2) / LAYER + 1e-9), 6)


def side_key_box(build_dir, base):
    """The lid's colour box: [(volume name, mesh)] over the lid's footprint (base: the lid's vertices in its print frame, min corner 0), from the
    split layer to 0.2 above the lid's top. build_dir: the lid's build folder (out/<slug>)."""
    case = Path(build_dir).resolve().parent.parent.name
    top = wall_top(build_dir)
    if abs(top - WALL_TOP[case]) > 0.01:
        raise SystemExit(f'{build_dir}: the lid\'s middle tab tops out at {top:.3f}, not {WALL_TOP[case]} (python -B color_options.py report)')
    z0 = split_layer(top)
    hi = np.asarray(base).max(axis=0)
    m = trimesh.creation.box(bounds=[[0.0, 0.0, z0], [hi[0], hi[1], hi[2] + LAYER]])
    return [(BOX_NAME.format(z=z0), trimesh.Trimesh(m.vertices.copy(), m.faces.copy(), process=False))]


# ---------------------------------------------------------------- the report

_READER = r'''
import os, sys, json
case, slug = sys.argv[1], sys.argv[2]
os.environ['SILKSCREEN_VARIANT'] = slug
sys.path.insert(0, sys.argv[3] + '/' + case + '/src')
os.chdir(sys.argv[3] + '/' + case)
import params as P
print(json.dumps({n: getattr(P, n) for n in ('SEAM', 'Z_BACK', 'X0', 'X1', 'Y0', 'Y1')}))
'''


def _params(case, slug):
    r = subprocess.run([sys.executable, '-X', 'utf8', '-B', '-c', _READER, case, slug, str(HERE)], capture_output=True, text=True, timeout=300)
    if r.returncode:
        raise SystemExit(r.stderr[-1500:])
    return json.loads(r.stdout.strip().splitlines()[-1])


def report():
    """z_split per size from the params and from the STL, and what the lid holds above it (the polygons of the lid's section just over it, each
    classed by where it is and how big)."""
    from functools import reduce
    for case, slug in (('case-426', 'standard'), ('case-426', 'chinless'), ('case-426', 'light-strip'), ('case-368', 'standard')):
        d = HERE / case / 'out' / slug
        p = _params(case, slug)
        lid = trimesh.load(d / 'lid.stl', force='mesh')
        zb = lid.bounds[0][2]
        top = wall_top(d)
        z0 = split_layer(top)
        print(f'{case}/{slug}: SEAM {p["SEAM"]} - Z_BACK {p["Z_BACK"]} = {p["SEAM"] - p["Z_BACK"]:.3f}; wall top on the lid STL {top:.3f}; '
              f'box from z {z0:g} (lid {lid.extents[2]:.3f} high)')
        assert abs(p['SEAM'] - p['Z_BACK'] - top) < 0.01 and abs(top - WALL_TOP[case]) < 0.01
        s = lid.section(plane_origin=[0, 0, zb + z0 + 0.1], plane_normal=[0, 0, 1])
        rings = sorted((Polygon(r[:, :2]).buffer(0) for r in s.discrete if len(r) > 3), key=lambda q: -q.area)
        g = reduce(lambda a, b: a.symmetric_difference(b), rings)
        pieces = list(g.geoms) if hasattr(g, 'geoms') else [g]
        v = np.asarray(lid.vertices)
        cls = {}
        for q in pieces:
            c = q.centroid
            k = q.bounds[0] < p['X0'] - 0.3 or q.bounds[2] > p['X1'] + 0.3      # a side key's pad stands out of the case face by 1.2
            w, h = q.bounds[2] - q.bounds[0], q.bounds[3] - q.bounds[1]
            kind = 'side key' if k else 'clip' if min(w, h) < 1.0 and q.area < 5 else 'peg' if q.area < 25 else 'bar or rib'
            top_z = max([z for x, y, z in v if z > zb + z0 and q.buffer(0.05).contains(Point(x, y))] or [np.nan]) - zb
            inset = min(q.bounds[0] - p['X0'], q.bounds[1] - p['Y0'], p['X1'] - q.bounds[2], p['Y1'] - q.bounds[3]) if not k else 0.0
            cls.setdefault(kind, []).append((round(top_z, 2), round(inset, 1)))
        for kind, rows in cls.items():
            print(f'    {kind}: {len(rows)}, top z {min(r[0] for r in rows)}-{max(r[0] for r in rows)}'
                  + ('' if kind == 'side key' else f', least distance to the case side wall / ends {min(r[1] for r in rows)} mm'))


if __name__ == '__main__':
    if sys.argv[1:] == ['write']:
        write()
    elif sys.argv[1:] == ['report']:
        report()
    else:
        sys.exit(__doc__)
