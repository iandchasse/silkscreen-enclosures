"""An optional colour switch for the Silkscreen case plates (2026-11-06; make_plates.py puts it in every plate file and project).
As shipped the lines are ENGRAVED: the body is a Negative Volume of the tub (2026-11-07, Ian: engraved by default; Modifier for no
lines, Modifier + filament 2 for coloured lines). print/README.md, "Three front lines". Nothing under case-*/src is touched and no tub geometry changes.

Three lines on the tub's front (the idea is @juno_last's case design): three straight horizontal lines with rounded ends, 1.0 wide on a
2.5 pitch, 48 long, centred on the case's centre line, as ONE modifier volume of the tub (three shells), each 0.6 mm (3 layers) deep from the front face
(the face prints down, so they are the tub's first three layers). A chin tub (bottom keys) has them between the key openings and the window's
bottom edge; a chinless tub between the window's bottom edge and the case's bottom edge. Shipped as a Negative Volume (engraved 0.6 deep,
in the case colour); Change type -> Modifier gives no lines (a modifier with no setting changes nothing), and that modifier with filament 2
gives lines in a second colour, flush.
Bodies: print/4.26/tub-front-lines.stl (chin tubs, standard and light strip), tub-front-lines-chinless.stl (both chinless tubs) and
print/3.68/tub-front-lines.stl, made by `write` from the built tubs and checked against every tub they go on (tub_lines): inside the solid
face on all three layers and 1.2 mm or more from the openings, the window and the outline. A full case build deletes them (it sweeps
print/<size>/ of every file it did not make), so tub_lines makes a missing one again from the built tubs.

    python -B color_options.py write     the line STLs into print/4.26 and print/3.68
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
LINE_LENGTH = 48.0                       # mm: the lines' length on a chinless tub (the chin tubs' key row spans 48.0)
LINE_MARGIN = 1.2                        # mm: the lines' clearance from the key openings and from the window, on all three layers
LAYER_MIDS = (0.1, 0.3, 0.5)             # the three layers' slicing planes (the openings' first 0.09 is a skin too thin to print)
LINES_NAME = 'front lines: engraved (Change type -> Modifier = no lines; Modifier + filament 2 = colour)'
LINES_SUBTYPE = 'negative_part'         # as shipped: engraved (2026-11-07; was an inert modifier_part, 2026-11-06)
LINE_FILES = {('case-426', False): PRINT / '4.26' / 'tub-front-lines.stl', ('case-426', True): PRINT / '4.26' / 'tub-front-lines-chinless.stl',
              ('case-368', False): PRINT / '3.68' / 'tub-front-lines.stl'}     # (case, chinless)


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
    """The tub's chin band as laid on its first three layers: {'x': (x0, x1) the key row's span (a chinless tub: LINE_LENGTH about its centre
    line), 'y_win': the window's chin-side edge, 'y_key': the far limit of the band (the bottom-key openings' window-side edge, or on a chinless
    tub the outline's edge on the layers 0.1-0.5, which is already inside the front round), 'width': the tub's x extent, 'chin': bool}."""
    y_win, y_key, x0, x1, chin = -1e9, 1e9, 1e9, -1e9, True
    for z in LAYER_MIDS:
        outer, holes = _rings(tub, z)
        win = holes[0]
        keys = [h for h in holes[1:] if h.bounds[1] > win.bounds[3] and h.area < 0.2 * win.area]
        y_win = max(y_win, win.bounds[3])
        if keys:
            y_key = min(y_key, min(h.bounds[1] for h in keys))
            x0, x1 = min(x0, min(h.bounds[0] for h in keys)), max(x1, max(h.bounds[2] for h in keys))
        else:
            chin = False
            y_key = min(y_key, outer.bounds[3])
    if not chin:
        x0, x1 = tub.bounds[1][0] / 2 - LINE_LENGTH / 2, tub.bounds[1][0] / 2 + LINE_LENGTH / 2
    return {'x': (float(x0), float(x1)), 'y_win': float(y_win), 'y_key': float(y_key), 'width': float(tub.bounds[1][0]), 'chin': chin}


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


LINE_SLUGS = {('case-426', False): ('standard', 'light-strip'), ('case-426', True): ('chinless', 'light-strip-chinless'),
              ('case-368', False): ('standard', 'light-strip')}          # the builds whose tubs each line file is laid out on


def write(keys=tuple(LINE_SLUGS)):
    """The line STLs (print/4.26, print/3.68), from the built tubs. The 4.26's standard and light-strip tubs share one file: the lines are
    centred in the narrower of their two gaps."""
    for key in keys:
        case, slugs = key[0], LINE_SLUGS[key]
        chins = []
        for s in slugs:
            tub = trimesh.load(HERE / case / 'out' / s / 'print' / 'tub.stl', force='mesh')
            c = measure_chin(tub)
            assert c['chin'] != key[1], (case, s, 'chin kind')
            chins.append(c)
        lay = line_layout(chins)
        m = trimesh.util.concatenate(line_meshes(lay))
        LINE_FILES[key].parent.mkdir(exist_ok=True)
        m.export(LINE_FILES[key])
        print(f'{LINE_FILES[key].relative_to(HERE.parent)}: width {lay["width"]}, pitch {lay["pitch"]}, length {lay["length"]:.2f}, '
              f'x {lay["x"][0]:.2f}-{lay["x"][1]:.2f}, y {[round(y, 3) for y in lay["ys"]]}, gap {lay["gap"]:.2f} '
              f'(window edge to openings), margins {lay["margin_win"]:.2f} / {lay["margin_key"]:.2f}'
              + (', SHRUNK from 1.0 / 2.5' if lay['shrunk'] else ''))


_lines_cache = {}


def tub_lines(stl, base, faces):
    """The three line bodies for the tub at stl (built part enclosures/<case>/out/<slug>/print/tub.stl; base, faces: its vertices in the print
    frame, min corner 0, and its faces) -> [(volume name, mesh)] in that frame, . The STL in print/ is checked against this very tub."""
    case, slug = build_of(stl)
    key = (case, hash(np.ascontiguousarray(base).tobytes()))
    if key not in _lines_cache:
        tub = trimesh.Trimesh(base, faces, process=False)
        chin = measure_chin(tub)
        f = LINE_FILES[(case, not chin['chin'])]
        if not f.exists():       # each case's build sweeps print/<size>/ of the files it did not make itself (case-426 build.py
            write([(case, not chin['chin'])])     # write_print, case-368 build.py), so a full build removes it: made again here (2026-11-07)
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
        one = trimesh.util.concatenate(bodies)             # one modifier volume holding the three shells
        _lines_cache[key] = [(LINES_NAME, trimesh.Trimesh(one.vertices.copy(), one.faces.copy(), process=False))]
    return _lines_cache[key]


if __name__ == '__main__':
    if sys.argv[1:] == ['write']:
        write()
    else:
        sys.exit(__doc__)
