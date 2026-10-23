"""The battery bay as printed (2026-10-19): read-backs of the lid's G-code against what is over it, closed.

Ian's cell is a 503035 whose datasheet allows 5.3 mm thick; with two layers of tape on each face it is 6.02 mm (BATT_ENV_T).
Judged on the lid as sliced (the layers slice_check.device_layers builds: the CAD frame, each layer's mid-plane and its
lines at their widths), put at the lid's as-printed home, not on the CAD:

  bay_air         the cell's air: over the pocket, from the pocket floor as printed to the lowest of the board's parts, the
                  midplate, the tub and the lid's own overhangs (the lip), less the cell's envelope. >= AIR_MIN.
  lip_underside   the lip's underside over the pocket floor, along the cell's bottom edge: the cell must slide under it.
  lead_reach      the battery lead is a limp string (10 % slack), plugged into J5 with the lid stood up at 90 degrees. From
                  every cell exit it reaches the tape point T on the midplate's back; every lid feature inside that reach
                  must leave two leads (LEAD_2) under whatever is over it, the coil well three, the fixed run (the plug up
                  to T) two. A lead pinched between the lid and the midplate or the board is how the cell's wires fail.
  cut_zone        where Ian cut the board (Y 86.25), a sliver of board or the 3V3 bodge wire at the cut would sit on any
                  post past it: nothing of the lid may stand above CUT_TOP_MAX within CUT_ZONE.
  backstop_gap    the backstops' (and the fence's) gap under the midplate as printed, on a nominal panel and on the thickest.
  midplane_ties   CAD only. A top at a layer's mid-plane prints one layer high or low between slices: a height in the bay
                  must sit on a whole layer from the bed.
  ribs            the lid's internal ribs (lid.RIBS) printed to RIB_TOP, and clear of everything over them, all over the lid
                  (the switch housings and the bodge wires are part of the ceiling here).

Everything is on a 0.1 mm grid; a layer spans zc +- 0.1; the lid is put at home (dz) and the board at BOARD_DZ. The ceiling
(what is over the lid) is cached next to the slice (the three STLs it reads are its key).
"""
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from shapely import contains_xy
from shapely.geometry import Point, box as sbox
from shapely.ops import unary_union
import hw
import params as P

LAYER = 0.2
RES = 0.1
BOX_FULL = (-5.0, 65.0, -10.0, 99.5)          # the whole lid, for the ribs and the maps
BOX_Y0 = 40.0                                 # the bay checks read Y >= 40 of the same grid
BOARD_DZ = 0.07                               # the board's rear rests on the lid's posts, which print to -0.035; lid +0.105
ENV = getattr(P, 'BATT_ENV_T', 6.02)          # 503035: 5.3 + 4 x 0.18 (params.BATT_ENV_T)
LEAD_2 = 2.6                                  # two 1.3 mm leads side by side
LEAD_3 = 3.9                                  # three
AIR_MIN = 0.40                                # air over the cell's envelope (a layer of tape and a little)
LIP_MIN = 6.17                                # the lip's underside over the floor: ENV + 0.15
CUT_TOP_MAX = -1.5                            # anything on the lid past the cut stays this low (the board's front face is -1.6)
CUT_ZONE = (40.17, 60.0, hw.PCB_CUT_Y, hw.PCB_CUT_Y + 3.0)
GAP_MIN = (0.30, 0.20)                        # backstops to the midplate: nominal panel, thickest panel
HINGE = (98.6, -3.75)                         # the lid stood up at 90 degrees to plug in: the top rim's (Y, Z)
T_LINE = [(40.0, 92.5), (39.6, 90.0), (39.5, 88.0)]    # where the lead's tape point may be: along the midplate's back above J5
T_Z = P.MID_REAR - 0.65                       # a lead's centre lying on the midplate's back
EXITS = (17.0, 22.5, 28.0, 33.0, 36.0)        # where the lead leaves the cell's top end (X)
E_Z = round(P.BATT_FLOOR + 2.65, 3)           # the cell's mid-thickness
SLACK = 1.1
COIL = (38.5, 47.0, 86.5, 93.0)               # the well beside the tape point
FIXED_RUN = [(40.36, 81.75), (38.9, 82.2), (38.9, 86.5)]    # J5's plug, round the board's corner, up the midplate (then T)
PLUG_BOX = (40.3, 45.4, 78.8, 84.7)           # the plug's own box: not part of the fixed run's band
RUN_BAND = 1.0
Y_TOP_REACH = P.TOP_IN - 0.2                  # the lead cannot go past the top rib's outer face
CELL = (P.BATT['x'][0], P.BATT['x'][1], P.BATT['y'][0], P.BATT['y'][1])
AIR_ZONE = (6.98, 38.08, 56.6, 93.3)
ZONES = {'under J7': (12.32, 28.76, 64.15, 79.15), 'under U9': (33.99, 36.79, 76.32, 79.22),
         'gallery': (6.98, 38.08, 80.8, 93.3)}
LIP_SPANS = ((7.3, 13.8), (22.8, 37.6))
# 'printed' counts cells of the rib's core (the box less RIB_SHRINK) under a line of the top layer, the lines taken flat-ended
# as device_layers lays them: the sliced top layer has 0.1-0.3 gaps where its fill lines end, so a rib that prints to the top
# reads 0.91-0.93 here (0.96-0.98 by the layer's own area); a rib that stops short reads 0. 0.85 leaves room for a re-slice.
RIB_PRINTED_MIN, RIB_TOP_TOL, RIB_FREE_MIN, RIB_SHRINK = 0.85, 0.05, 0.50, 0.25
TIE_TOL = 0.012
SW_HOUSING_Z = -4.493                         # the side and bottom switches' bodies (hw / joint: SW_LIP_TOP)
CEIL_VER = 2


def grid(box, res=RES):
    x0, x1, y0, y1 = box
    nx, ny = int(round((x1 - x0) / res)), int(round((y1 - y0) / res))
    return x0 + (np.arange(nx) + 0.5) * res, y0 + (np.arange(ny) + 0.5) * res


def zmap(mesh, box, res=RES, zlim=(-1e9, 1e9)):
    """The lowest z of a mesh's surface over each cell centre of the grid (NaN where none), counting z within zlim."""
    xs, ys = grid(box, res)
    x0, y0 = box[0], box[2]
    out = np.full((len(ys), len(xs)), np.nan)
    tris = mesh.triangles
    lo, hi = tris[:, :, :2].min(1), tris[:, :, :2].max(1)
    keep = (hi[:, 0] >= box[0]) & (lo[:, 0] <= box[1]) & (hi[:, 1] >= box[2]) & (lo[:, 1] <= box[3])
    keep &= (tris[:, :, 2].max(1) >= zlim[0]) & (tris[:, :, 2].min(1) <= zlim[1])
    for tri, l, h in zip(tris[keep], lo[keep], hi[keep]):
        i0 = max(int(math.ceil((l[0] - x0) / res - 0.5 - 1e-9)), 0)
        i1 = min(int(math.floor((h[0] - x0) / res - 0.5 + 1e-9)), len(xs) - 1)
        j0 = max(int(math.ceil((l[1] - y0) / res - 0.5 - 1e-9)), 0)
        j1 = min(int(math.floor((h[1] - y0) / res - 0.5 + 1e-9)), len(ys) - 1)
        if i1 < i0 or j1 < j0:
            continue
        a, b, c = tri
        v0, v1 = b[:2] - a[:2], c[:2] - a[:2]
        den = v0[0] * v1[1] - v1[0] * v0[1]
        if abs(den) < 1e-12:
            continue
        gx, gy = np.meshgrid(xs[i0:i1 + 1], ys[j0:j1 + 1])
        px, py = gx - a[0], gy - a[1]
        l1 = (px * v1[1] - v1[0] * py) / den
        l2 = (v0[0] * py - px * v0[1]) / den
        ok = (l1 >= -1e-9) & (l2 >= -1e-9) & (l1 + l2 <= 1 + 1e-9)
        z = a[2] + l1 * (b[2] - a[2]) + l2 * (c[2] - a[2])
        ok &= (z >= zlim[0]) & (z <= zlim[1])
        blk = out[j0:j1 + 1, i0:i1 + 1]
        upd = ok & (np.isnan(blk) | (z < blk))
        blk[upd] = z[upd]
    return out


def _stl_key():
    h = hashlib.sha1(f'v{CEIL_VER}'.encode())
    for n in ('pcba-dummy.stl', 'midplate.stl', 'tub.stl', 'pcba-dummy.json'):
        s = (hw.OUT / n).stat()
        h.update(f'{n}:{s.st_size}:{s.st_mtime_ns}'.encode())
    return h.hexdigest()


def ceilings():
    """What is over the lid, closed (the lowest tub-side surface per cell over BOX_FULL), as two arrays: 'base' (the
    board's parts as printed +BOARD_DZ, J5's plug, the midplate, the tub) for the bay's checks, and 'full' (base, and the
    open switch sites' housings and the charging bodge wires) for the ribs."""
    cache = hw.OUT / 'slice' / 'bay-ceiling.npz'
    key = _stl_key()
    try:
        d = np.load(cache, allow_pickle=False)
        if str(d['key']) == key:
            return d['base'], d['full']
    except Exception:
        pass
    import trimesh
    import refs
    xs, ys = grid(BOX_FULL)
    X, Y = np.meshgrid(xs, ys)
    load = lambda n: trimesh.load(str(hw.OUT / n), force='mesh')
    board = zmap(load('pcba-dummy.stl'), BOX_FULL) + BOARD_DZ
    mid = zmap(load('midplate.stl'), BOX_FULL)
    tub = zmap(load('tub.stl'), BOX_FULL, zlim=(-20, 20))
    pb = refs.plug_box()
    plug = np.full(board.shape, np.nan)
    plug[(X >= pb[0]) & (X <= pb[1]) & (Y >= pb[2]) & (Y <= pb[3])] = pb[4] + BOARD_DZ
    base = np.stack([np.where(np.isnan(v), np.inf, v) for v in (board, plug, mid, tub)]).min(0)
    base[np.isinf(base)] = np.nan
    full = np.where(np.isnan(base), np.inf, base)
    sites = json.loads((hw.OUT / 'pcba-dummy.json').read_text()).get('open_sites', {})
    for ref, s in sites.items():
        if ref.startswith('SW') and 'housing' in s:
            x0, x1, y0, y1 = s['housing']
            m = (X >= x0) & (X <= x1) & (Y >= y0) & (Y <= y1)
            full[m] = np.minimum(full[m], SW_HOUSING_Z + BOARD_DZ)
    import lid_close
    for a, b in lid_close.routes().values():
        for x0, x1, y0, y1, zl, _ in lid_close.wire(a, b):
            m = (X >= x0) & (X <= x1) & (Y >= y0) & (Y <= y1)
            full[m] = np.minimum(full[m], zl + BOARD_DZ)
    full[np.isinf(full)] = np.nan
    try:
        np.savez_compressed(cache, key=np.array(key), base=base, full=full)
    except Exception:
        pass
    return base, full


def lid_columns(lid_layers, dz):
    """The lid as printed, per cell over BOX_FULL: floor_top (the top of the material standing on the bed), under (the
    underside of the first material over a gap above it: an overhang), top (the highest material), all CAD, closed.
    lid_layers: [(zc, polygon)] in the CAD frame (slice_check.device_layers)."""
    xs, ys = grid(BOX_FULL)
    XX, YY = np.meshgrid(xs, ys)
    layers = sorted(lid_layers, key=lambda t: t[0])
    tops = np.array([zc + LAYER / 2 for zc, _ in layers])
    occ = np.stack([contains_xy(g, XX, YY) for _, g in layers])
    nl, ny, nx = occ.shape
    ft = np.where(occ[0], tops[0], np.nan)
    under = np.full((ny, nx), np.nan)
    run = occ[0].copy()                              # still in the first solid run up from the bed
    gap = np.zeros((ny, nx), bool)
    for k in range(1, nl):
        o = occ[k]
        cont = run & o
        ft = np.where(cont, tops[k], ft)
        gap |= run & ~o
        run = cont
        under = np.where(gap & o & np.isnan(under), tops[k] - LAYER, under)
    idx = nl - 1 - np.argmax(occ[::-1], axis=0)
    top = np.where(occ.any(0), tops[idx], np.nan)
    return {'xs': xs, 'ys': ys, 'floor_top': ft + dz, 'under': under + dz, 'top': top + dz}


def _zone(X, Y, x0, x1, y0, y1):
    return (X > x0) & (X < x1) & (Y > y0) & (Y < y1)


def _argmin(a, mask):
    v = np.where(mask, a, np.nan)
    j, i = np.unravel_index(np.nanargmin(v), v.shape)
    return float(v[j, i]), j, i


def _open_pos(y, z):
    """A point of the lid at (y, z), after the lid has been stood up 90 degrees about the top rim."""
    dy, dz = y - HINGE[0], z - HINGE[1]
    return HINGE[0] - dz, HINGE[1] + dy


def _clusters(free, mask, thr, xs, ys):
    from scipy import ndimage as nd
    lab, n = nd.label(free < thr)
    out = []
    for h in np.unique(lab[mask & (free < thr)]):
        if h == 0:
            continue
        cm = lab == h
        sel = cm & mask
        v, j, i = _argmin(free, sel)
        out.append({'free': round(v, 3), 'at': [round(float(xs[i]), 1), round(float(ys[j]), 1)]})
    return sorted(out, key=lambda r: r['free'])


def _backstop_clip():
    import lid
    shapes = [Point(x, y).buffer(d / 2) for x, y, d in lid.BACKSTOPS]
    y0, y1 = lid.TOP_RIB['y']
    shapes += [sbox(a, y0, b, y1) for a, b in lid.TOP_RIB['x']]
    return unary_union(shapes).buffer(0.3)


def run(L, dz):
    """All the bay's read-backs. L: {'lid': layers, 'midplate': layers, ...} (slice_check.as_printed); dz: the lid's home.
    Returns {name: {value, at, ok}} and 'ok'."""
    import asprinted as A
    import lid
    m = lid_columns(L['lid'], dz)
    xs, ys = m['xs'], m['ys']
    base_full, full_full = ceilings()
    j0 = int(round((BOX_Y0 - BOX_FULL[2]) / RES))
    xb, yb = xs, ys[j0:]
    X, Y = np.meshgrid(xb, yb)
    ft, under, top = (m[k][j0:] for k in ('floor_top', 'under', 'top'))
    ceil = base_full[j0:]
    out = {}

    # the cell's air
    room = np.fmin(ceil, under) - ft
    msk = _zone(X, Y, *AIR_ZONE) & np.isfinite(room)
    v, j, i = _argmin(room, msk)
    zones = {}
    for nm, zb in ZONES.items():
        zm = _zone(X, Y, *zb) & np.isfinite(room)
        zv, zj, zi = _argmin(room, zm)
        zones[nm] = round(zv - ENV, 3)
    out['bay_air'] = {'value': round(v - ENV, 3), 'at': [round(float(xb[i]), 1), round(float(yb[j]), 1)],
                      'need': f'>= {AIR_MIN} over a {ENV} cell', 'zones': zones, 'ok': bool(v - ENV >= AIR_MIN - 1e-9)}

    # the lip's underside
    lipm = np.zeros(X.shape, bool)
    for a, b in LIP_SPANS:
        lipm |= _zone(X, Y, a, b, 56.0, 56.1)
    lipm &= np.isfinite(under) & np.isfinite(ft)
    v, j, i = _argmin(under - ft, lipm)
    out['lip_underside'] = {'value': round(v, 3), 'at': [round(float(xb[i]), 1), round(float(yb[j]), 1)],
                            'need': f'>= {LIP_MIN}', 'ok': bool(v >= LIP_MIN - 1e-9)}

    # the lead
    cell = _zone(X, Y, *CELL)
    lidsurf = np.where(cell, ft + ENV, top)
    free = ceil - lidsurf
    ey = P.BATT['y'][1]
    bad, worst = {}, None
    for T in T_LINE:
        t3 = np.array([T[0], T[1], T_Z])
        dT = np.hypot(X - T[0], Y - T[1])
        for ex in EXITS:
            oy, oz = _open_pos(ey, E_Z)
            Lopen = SLACK * math.dist((ex, oy, oz), t3)
            dE = np.hypot(X - ex, Y - ey)
            reach = (np.sqrt((dE + dT) ** 2 + (T_Z - E_Z) ** 2) <= Lopen) & (Y <= Y_TOP_REACH)
            cl = _clusters(free, reach, LEAD_2, xb, yb)
            if cl:
                bad[f'T {T} exit {ex:g}'] = cl[:3]
                worst = cl[0] if worst is None or cl[0]['free'] < worst['free'] else worst
        coil = _zone(X, Y, *COIL)
        cl = _clusters(free, coil, LEAD_3, xb, yb)
        if cl and 'coil' not in bad:
            bad['coil'] = cl[:3]
            worst = cl[0] if worst is None or cl[0]['free'] < worst['free'] else worst
        band = np.zeros(X.shape, bool)
        pts = FIXED_RUN + [T]
        for (a, b), (c, d) in zip(pts, pts[1:]):
            for t in np.linspace(0, 1, int(math.dist((a, b), (c, d)) / RES) + 2):
                band |= np.hypot(X - (a + t * (c - a)), Y - (b + t * (d - b))) <= RUN_BAND
        cl = _clusters(free, band & ~_zone(X, Y, *PLUG_BOX), LEAD_2, xb, yb)
        if cl:
            bad.setdefault(f'fixed run to T {T}', cl[:3])
            worst = cl[0] if worst is None or cl[0]['free'] < worst['free'] else worst
    out['lead_reach'] = {'value': worst['free'] if worst else None, 'at': worst['at'] if worst else None,
                         'need': f'free >= {LEAD_2} (coil {LEAD_3}) everywhere a lead can lie', 'hard_points': bad,
                         'ok': not bad}

    # the cut zone
    cz = _zone(X, Y, *CUT_ZONE) & np.isfinite(top)
    tv = np.where(cz, top, np.nan)
    j, i = np.unravel_index(np.nanargmax(tv), tv.shape)
    out['cut_zone'] = {'value': round(float(tv[j, i]), 3), 'at': [round(float(xb[i]), 1), round(float(yb[j]), 1)],
                       'need': f'<= {CUT_TOP_MAX}', 'ok': bool(tv[j, i] <= CUT_TOP_MAX + 1e-9)}

    # the backstops' gap under the midplate
    F = _backstop_clip()
    g0 = A.z_gap(L['lid'], L['midplate'], dz, 0.0, clip=F)
    g1 = A.z_gap(L['lid'], L['midplate'], dz, -hw.PANEL_T_TOL, clip=F)
    gv = [g0['gap'] if g0 else None, g1['gap'] if g1 else None]
    out['backstop_gap'] = {'value': gv, 'at': g0['where'] if g0 else None,
                           'need': f'>= {GAP_MIN[0]} nominal, >= {GAP_MIN[1]} on the thickest panel',
                           'ok': bool(all(v is not None and v >= n - 1e-9 for v, n in zip(gv, GAP_MIN)))}

    # the heights on whole layers (CAD only)
    out['midplane_ties'] = midplane_ties()

    # the ribs
    out['ribs'] = ribs(m, full_full, dz)

    out['ok'] = all(v['ok'] for v in out.values())
    return out


def midplane_ties():
    """The bed height (top - Z_BACK) of every solid in the bay, the backstops, the ribs, and the logo's and the grooves'
    depths: none within TIE_TOL of a layer's mid-plane (0.1 + 0.2 k), where the slicer's choice flips between versions."""
    import lid
    rows = []
    for nm, solids in (('bay', lid.bay()[0]), ('backstops', lid.backstops()), ('ribs', lid.ribs())):
        for k, s in enumerate(solids):
            rows.append((f'{nm}[{k}]', s.val().BoundingBox().zmax - P.Z_BACK))
    if P.LOGO_BACK:
        rows.append(('logo depth', P.LOGO_BACK['depth']))
    if P.LOGO_BACK_WORDMARK:
        rows.append(('back wordmark depth', P.LOGO_BACK_WORDMARK['depth']))
    rows.append(('grip groove depth', P.GRIP_GROOVE['depth']))
    near = []
    for nm, h in rows:
        k = round((h - LAYER / 2) / LAYER)
        if abs(h - (LAYER / 2 + k * LAYER)) < TIE_TOL:
            near.append({'what': nm, 'bed_height': round(h, 3)})
    return {'value': near or None, 'at': None, 'need': f'none within {TIE_TOL} of a layer mid-plane', 'checked': len(rows),
            'ok': not near}


def ribs(m, ceil_full, dz):
    """The lid's internal ribs (lid.RIBS), as printed: each box shrunk RIB_SHRINK must reach RIB_TOP (share of its cells
    >= RIB_PRINTED_MIN, median top within RIB_TOP_TOL), with RIB_FREE_MIN left under the ceiling over the whole box."""
    import lid
    xs, ys = m['xs'], m['ys']
    X, Y = np.meshgrid(xs, ys)
    top = m['top']
    rows, ok = {}, True
    for nm, (x0, x1, y0, y1) in lid.RIBS.items():
        core = _zone(X, Y, x0 + RIB_SHRINK, x1 - RIB_SHRINK, y0 + RIB_SHRINK, y1 - RIB_SHRINK) & np.isfinite(top)
        whole = _zone(X, Y, x0, x1, y0, y1)
        if not core.any():
            rows[nm] = {'printed': 0.0, 'top': None, 'free': None, 'ok': False}
            ok = False
            continue
        tops = top[core]
        want_top = lid.RIB_TOP + dz
        printed = float(np.mean(tops >= want_top - 0.05))
        med = float(np.median(tops))
        fr = np.where(whole & np.isfinite(top) & np.isfinite(ceil_full), ceil_full - top, np.nan)
        if np.isnan(fr).all():
            fmin, at = None, None
        else:
            fmin, j, i = _argmin(fr, np.isfinite(fr))
            at = [round(float(xs[i]), 1), round(float(ys[j]), 1)]
        good = (printed >= RIB_PRINTED_MIN and abs(med - want_top) <= RIB_TOP_TOL and fmin is not None
                and fmin >= RIB_FREE_MIN - 1e-9)
        rows[nm] = {'printed': round(printed, 3), 'top': round(med, 3), 'free': None if fmin is None else round(fmin, 3),
                    'at': at, 'ok': bool(good)}
        ok &= good
    return {'value': rows, 'at': None, 'need': f'printed >= {RIB_PRINTED_MIN} to RIB_TOP +-{RIB_TOP_TOL}, free >= {RIB_FREE_MIN}',
            'ok': bool(ok)}



def show(r):
    """Print the bay's read-backs, one line each (slice_check's report style)."""
    for nm, v in r.items():
        if nm == 'ok':
            continue
        if nm == 'ribs':
            body = '; '.join(f"{k} printed {x['printed']} top {x['top']} free {x['free']}" for k, x in v['value'].items())
        elif nm == 'lead_reach':
            body = 'no hard point in any lead reach' if v['ok'] else \
                f"hard points {len(v['hard_points'])} (worst free {v['value']} at {v['at']}): " + \
                '; '.join(f"{k}: {c[0]['free']} at {c[0]['at']}" for k, c in list(v['hard_points'].items())[:6])
        elif nm == 'midplane_ties':
            body = f"{v['checked']} heights, " + ('none on a mid-plane' if v['ok'] else f"on a mid-plane: {v['value']}")
        else:
            body = f"{v['value']} at {v['at']}" + (f" (zones {v['zones']})" if 'zones' in v else '')
        print(f"    bay {nm:14s} {body}   need {v['need']}  {'PASS' if v['ok'] else 'FAIL'}")
    print(f"  as printed, the battery bay: {'PASS' if r['ok'] else 'FAIL'}")
