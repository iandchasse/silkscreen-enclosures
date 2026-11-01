"""Checks of the slide covers against the REAL case STLs (tub + lid + side keys + bottom keys, as built in
enclosures/case-*/out/<build>/), for every build a cover serves, in both orientations.

    python -B check.py [--group keyed|chinless|x3|all] [--builds a,b,...] [--step 1.0] [--wrong]

What it proves (and what it does not: nothing here was printed, and the force and strain numbers are beam estimates):
  home        the cover's rigid frame (no ridge) has ZERO overlap volume with the case at home, on the front and turned over
              on the back, at the nominal pose and at the extremes of its play (plate toward / away, channel toward each
              end wall by cy - 0.05); the ridge's own overlap at home is the snap engagement and is reported;
  clearance   the least distance from the frame to the case at the nominal pose, and from the plate to every bottom-key cap
              with the plate at its nearest;
  slide       the frame swept along the whole slide path (the cover entirely off the case to home) never touches the case
              (zero overlap volume at every step); the ridge's deflection along the path, read from the real end faces
              (ray casts through the J6 opening and over both corners), its flatness along the straight stretch (a
              catch in an opening shows as a dip) and its peak;
  snap        the engagement at home (the arc's height over the ridge's tip), the deflection on the removal path, and the
              force estimates (beam model, snap.py);
  access      the USB-C opening is clear of the cover in both orientations; with the cover on the back the screen window
              is clear; the key caps' pockets clear the caps.
--wrong runs the same checks on two deliberately wrong covers (no stop-wall gaps; the ridge moved into J6's band): each
must FAIL, or the check proves nothing.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import manifold3d as m3d
import numpy as np
import trimesh

import case_info
import model as M
import raycast
import snap
import variants_list as V

HERE = Path(__file__).resolve().parent
ENC = HERE.parent
DESIGN = HERE / 'out' / 'design'
OUTJ = HERE / 'out'

EPS_VOL = 0.02          # mm3: overlap volumes below this are float32 noise
MIN_CLEAR = 0.10        # mm: the least frame-to-case distance at the nominal pose
FLAT_TOL = 0.12         # mm: the ridge's deflection may vary this much along the straight end face (the case's own
                        # print error is about +-0.1); a catch in an opening shows as a dip far larger than that
D_MAX_ALLOW = 0.95      # mm: peak deflection along the whole path (the design deflection is d_eng = 0.7)


def to_man(tm):
    return m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(tm.vertices, dtype=np.float32),
                                 tri_verts=np.asarray(tm.faces, dtype=np.uint32)))


def mat(s, shift, flip, dy=0.0, dz=0.0):
    """4x4: design frame -> case frame. The cover moves by `shift` along x (case x = u + shift on the front); turned over:
    x -> 2 xc - x, z -> 2 zm - z (a half turn about the long axis); then dy, dz in the case frame."""
    sx = -1.0 if flip else 1.0
    m = np.eye(4)
    m[0, 0] = sx
    m[2, 2] = sx
    m[0, 3] = (2 * s['xc'] - shift) if flip else shift
    m[2, 3] = (2 * s['zm'] + dz) if flip else dz
    # x' = sx * (u + shift) + (2 xc if flip) ; for flip: 2xc - u - shift  ->  m00 = -1, m03 = 2xc - shift   (as set)
    # z' = sx * z + (2 zm if flip) + dz
    m[1, 3] = dy
    return m


def apply(man, m):
    return man.transform(m[:3])


class Case:
    """A built case (out/<slug>/): its parts as manifolds, the union, and a ray caster."""

    def __init__(self, case, slug):
        self.case, self.slug = case, slug
        d = ENC / case / 'out' / slug
        names = ['tub', 'lid'] + [p.stem for p in sorted(d.glob('key_SW*.stl'))]
        self.names = names
        self.meshes = {n: trimesh.load(d / f'{n}.stl', force='mesh') for n in names}
        self.man = {n: to_man(m) for n, m in self.meshes.items()}
        u = None
        for n in names:
            u = self.man[n] if u is None else u + self.man[n]
        self.union = u
        self.caps = [n for n in names if n.startswith('key_SW')]
        self.info = case_info.info(case, slug)
        allm = trimesh.util.concatenate([self.meshes[n] for n in names])
        self.caster = raycast.Caster(allm)
        self.side_ref = {}
        for ref, b in self.info['side_keys'].items():
            self.side_ref[ref] = b

    def overlap(self, cov, m=None):
        c = cov if m is None else apply(cov, m)
        return float((c ^ self.union).volume())

    def min_gap(self, cov, m, search=3.0, part=None):
        c = apply(cov, m)
        tgt = self.union if part is None else self.man[part]
        return float(c.min_gap(tgt, search))


def usb_box(case):
    """The USB-C recess as a box on the right side, from case_info (a vtk ray over the side face)."""
    return tuple(case.info['usb'])


def box_man(x0, x1, y0, y1, z0, z1):
    return to_man(trimesh.creation.box(bounds=[[x0, y0, z0], [x1, y1, z1]]))


# ---- the ridge on the real end faces ------------------------------------------------------------------------------

def end_maps(case, s):
    """The real end faces as depth maps over the ridge's reach: depth(x, z) = how far the case's surface is inside the end
    plane (<= 0; 0 on the flat), top end (rays along -y from above Y1) and bottom end (along +y). -inf where a ray finds
    nothing within 30 mm."""
    c = case.caster
    Y0, Y1 = s['Y0'], s['Y1']
    xs = np.arange(s['X0'] - 8.0, s['X1'] + 8.0, 0.1)
    zlo, zhi = s['ridge_z']
    zm = s['zm']
    zs = np.arange(min(zlo, 2 * zm - zhi) - 1.0, max(zhi, 2 * zm - zlo) + 1.0, 0.2)
    out = {}
    for end, (ye, sign) in {'top': (Y1, -1.0), 'bottom': (Y0, 1.0)}.items():
        grid = np.full((len(xs), len(zs)), -50.0)
        for i, x in enumerate(xs):
            if x < s['X0'] or x > s['X1']:
                continue
            for j, z in enumerate(zs):
                h = c.first_hit([x, ye - sign * 4.0, z], [x, ye + sign * 30.0, z])
                if h is not None:
                    grid[i, j] = -abs(h[1] - ye)
        out[end] = (xs, zs, grid)
    return out


def ridge_samples(s):
    """Sample points of the ridge in the design frame: u, z and the protrusion p(u, z) from the wall plane (0 outside)."""
    b = s['b']
    ua = s['u_a']
    us = np.arange(ua, ua + s['r_i'] + s['f_top'] + s['r_r'] + 1e-9, 0.1)
    zlo, zhi = s['ridge_z']
    zs = np.arange(zlo, zhi + 1e-9, 0.1)
    U, Z = np.meshgrid(us, zs, indexing='ij')
    pu = np.interp(U, [ua, ua + s['r_i'], ua + s['r_i'] + s['f_top'], ua + s['r_i'] + s['f_top'] + s['r_r']],
                   [0.0, b, b, 0.0])
    pz = np.minimum(np.minimum(Z - zlo, zhi - Z), b)
    p = np.minimum(pu, np.maximum(pz, 0.0))
    return U, Z, p


def deflection_path(s, maps, shifts, flip, end, dz=0.0):
    """The prong's required deflection (mm) at each shift, for one end and one orientation (end = the cover's own end:
    'top' = the cover's top channel, which is the case's top on either side of the turn: the half turn is about Y)."""
    from scipy.interpolate import RegularGridInterpolator
    xs, zs, grid = maps[end]
    f = RegularGridInterpolator((xs, zs), grid, bounds_error=False, fill_value=-50.0)
    U, Z, p = ridge_samples(s)
    sel = p > 1e-6
    u, z, pp = U[sel], Z[sel], p[sel]
    out = []
    for sh in shifts:
        x = (2 * s['xc'] - (u + sh)) if flip else (u + sh)
        zz = ((2 * s['zm'] - z) if flip else z) + dz
        depth = f(np.c_[x, zz])
        out.append(max(0.0, float(np.max(depth + pp - s['cy']))))
    return np.array(out)


def flat_range(s, flip=False):
    """The shifts over which the whole ridge lies over the straight end face (clear of the corner arcs by 0.5)."""
    xa, xb = s['X0'] + s['CORNER_R'] + 0.5, s['X1'] - s['CORNER_R'] - 0.5
    u0 = s['u_a']
    u1 = s['u_a'] + s['r_i'] + s['f_top'] + s['r_r']
    return xa - u0, xb - u1                          # shifts: ridge from the left arc's end to the right arc's start


# ---- the checks -----------------------------------------------------------------------------------------------------

def check_build(group, case, slug, cov, frame, step=1.0, full_sweep=True, key_pockets=True, verbose=True):
    s = M.spec(group)
    cm = Case(case, slug)
    rows = []

    def row(name, ok, value):
        rows.append(dict(check=name, ok=bool(ok), value=value))
        if verbose:
            print(f'   {"ok  " if ok else "FAIL"} {name}: {value}')

    G2 = s['G'] / 2
    # 1. home (the stop wall 10 microns off the side: touching faces read as float noise), both orientations
    home = -s['cx'] + 0.01
    for flip, pose in ((False, 'front'), (True, 'back')):
        v = cm.overlap(frame, mat(s, home, flip))
        row(f'home {pose}: frame overlap', abs(v) < EPS_VOL, f'{v:.4f} mm3')
        vr = cm.overlap(cov, mat(s, home, flip))
        row(f'home {pose}: ridge overlap (the snap engagement)', True, f'{vr - v:.3f} mm3 (the preload; the prong flexes it away)')
        g = cm.min_gap(frame, mat(s, home + 0.5, flip), 3.0)
        row(f'home {pose}: least frame-to-case distance with the stop wall 0.5 off', g >= MIN_CLEAR, f'{g:.3f} mm')
        g = cm.min_gap(frame, mat(s, home, flip), 3.0)
        row(f'home {pose}: least distance at the stop (the wall 0.01 off the side)', g >= 0.005, f'{g:.3f} mm')
        worst = 0.0
        for dz in (-(s['gp'] - 0.05), s['gp'] - 0.05):
            worst = max(worst, cm.overlap(frame, mat(s, home + 0.5, flip, 0.0, dz)))
        for dy in (-(s['cy'] - 0.05), s['cy'] - 0.05):
            worst = max(worst, cm.overlap(frame, mat(s, home + 0.5, flip, dy, 0.0)))
        row(f'home {pose}: frame overlap with the cover moved a play-width in z (+-{s["gp"] - 0.05:.2f}) or y (+-{s["cy"] - 0.05:.2f})',
            worst < EPS_VOL, f'{worst:.4f} mm3 worst')
    # 2. the key slot (bottom keys): plate at its nearest, front orientation, at home and half way along the path
    if cm.caps and key_pockets:
        for sh in (home, 30.0, 55.0):
            g = min(cm.min_gap(cov, mat(s, sh, False, 0.0, -s['gp']), 3.0, part=n) for n in cm.caps)
            row(f'front: cover to the bottom-key caps, plate touching the face, s={sh:.1f} (the slot)', g >= s['key_clr'] - 0.02,
                f'{g:.3f} mm')
    # 3. the slide path
    lo, hi = -s['cx'] + 0.01, 78.0
    shifts = np.arange(lo, hi + 1e-9, step)
    for flip, pose in ((False, 'front'), (True, 'back')):
        worst, at = 0.0, None
        gmin = 9.0
        for sh in shifts:
            v = cm.overlap(frame, mat(s, sh, flip))
            if v > worst:
                worst, at = v, sh
        row(f'slide {pose}: frame overlap along the path (s {lo:.2f}..{hi:.0f}, step {step:g})', worst < EPS_VOL,
            f'{worst:.4f} mm3' + (f' at s={at:.1f}' if at is not None else ''))
    # 4. the ridge on the real end faces
    maps = end_maps(cm, s)
    sh = np.arange(-s['cx'], 78.0, 0.25)
    fa, fb = flat_range(s)
    for flip, pose in ((False, 'front'), (True, 'back')):
        for end in ('top', 'bottom'):
            dls = {}
            for dz in (-G2, 0.0, G2):
                dls[dz] = deflection_path(s, maps, sh, flip, end, dz)
            d0 = dls[0.0]
            iflat = (sh >= fa) & (sh <= fb)
            var = max(float(np.ptp(dl[iflat])) for dl in dls.values())
            dmax = max(float(dl.max()) for dl in dls.values())
            row(f'ridge {pose} {end}: deflection on the straight face (all Z play)', var <= FLAT_TOL,
                f'{d0[iflat].min():.2f}..{d0[iflat].max():.2f} mm (spread {var:.2f} at worst Z play; design {s["d_eng"]})')
            row(f'ridge {pose} {end}: peak deflection on the whole path (all Z play)', dmax <= D_MAX_ALLOW,
                f'{dmax:.2f} mm (design {s["d_eng"]})')
            home = int(np.argmin(np.abs(sh + s['cx'])))
            pre = float(d0[home])
            row(f'ridge {pose} {end}: preload at home', 0.0 <= pre <= s['d_pre'] + 0.15, f'{pre:.2f} mm (design {s["d_pre"]})')
            # the removal path: from home to where the ridge is on the flat
            iw = (sh >= -s['cx']) & (sh <= fa + 2.0)
            engage = float(d0[iw].max())
            row(f'ridge {pose} {end}: catch depth (the deflection the prong makes to leave the corner)',
                abs(engage - s['d_eng']) <= 0.15, f'{engage:.2f} mm')
            if end == 'top' and not flip:
                k_lo, _, _ = snap.stiffness(s, 3000.0, 2 * s['ridge_half'])
                k_hi, _, _ = snap.stiffness(s, 3000.0, s['z_o'] - s['prong_z_lo'])
                fr = snap.wedge(sh, d0, k_lo, 0.3, s)
                row('snap force estimate, one prong (beam model, E 3000, mu 0.3, soft bound)', True,
                    f'pull off peak {fr["pull_peak"]:.2f} N, push on peak {fr["push_peak"]:.2f} N, sliding drag '
                    f'{fr["drag"]:.2f} N, preload {fr["preload"]:.2f} N')
    # 5. access
    ub = usb_box(cm)
    if ub is None:
        row('USB-C opening located', False, 'not found')
    else:
        y0, y1, z0, z1 = ub
        probe = box_man(s['X1'] - 0.3, s['X1'] + 30, y0 - 0.5, y1 + 0.5, z0 - 0.5, z1 + 0.5)
        for flip, pose in ((False, 'front'), (True, 'back')):
            v = float((apply(frame, mat(s, -s['cx'] + 0.01, flip)) ^ probe).volume())
            row(f'USB-C access {pose}: cover inside the recess + 30 mm of plug room (y {y0:.1f}..{y1:.1f}, z {z0:.1f}..{z1:.1f})',
                v < EPS_VOL, f'{v:.4f} mm3')
    wx0, wx1, wy0, wy1 = s['window']
    screen = box_man(wx0, wx1, wy0, wy1, s['Z_FRONT'] - 0.5, s['Z_FRONT'] + 30)
    v = float((apply(cov, mat(s, -s['cx'] + 0.01, True)) ^ screen).volume())
    row('back: the screen window is clear of the cover', v < EPS_VOL, f'{v:.4f} mm3')
    return rows


def run(groups, builds=None, step=1.0, wrong=False, verbose=True):
    res = {}
    for g in groups:
        folder = DESIGN
        cov = to_man(trimesh.load(folder / f'{g}.stl', force='mesh'))
        frame = to_man(trimesh.load(folder / f'{g}-frame.stl', force='mesh'))
        for case, slug in V.builds(g, builds):
            t = time.time()
            if verbose:
                print(f'{g}: {case}/{slug}')
            res[f'{g}/{slug}'] = check_build(g, case, slug, cov, frame, step=step, verbose=verbose)
            if verbose:
                print(f'   ({time.time() - t:.0f} s)')
    return res


def wrong_covers(step=2.0):
    """The checks must FAIL on a cover that is wrong: (1) no stop-wall gaps (the wall meets the left keys' pads when the cover
    is on the back); (2) the ridge moved into J6's z band (it drops into the opening on the top end)."""
    out = {}
    g = 'keyed'
    s = M.spec(g)
    frame = to_man(trimesh.load(DESIGN / f'{g}-frame.stl', force='mesh'))
    for name, f in (('no gaps', DESIGN / f'{g}-wrong-nogaps.stl'), ('ridge in the J6 band', DESIGN / f'{g}-wrong-ridge.stl')):
        cov = to_man(trimesh.load(f, force='mesh'))
        fr = to_man(trimesh.load(f, force='mesh'))      # (for 'no gaps' the whole cover is the frame; the ridge is tested by deflection)
        print(f'wrong cover: {name}')
        if name == 'no gaps':
            rows = check_build(g, 'case-426', 'standard', cov, fr, step=step, verbose=False)
            bad = [r for r in rows if not r['ok']]
            for r in bad:
                print('   FAIL (as it must):', r['check'], '->', r['value'])
            out[name] = dict(failed=[r['check'] for r in bad], caught=bool(bad))
        else:
            sw = M.spec(g, ridge_shift=4.2, ridge_half=1.4)
            cm = Case('case-426', 'standard')
            maps = end_maps(cm, sw)
            sh = np.arange(-sw['cx'], 78.0, 0.25)
            fa, fb = flat_range(sw)
            dl = deflection_path(sw, maps, sh, False, 'top', 0.0)
            iflat = (sh >= fa) & (sh <= fb)
            var = float(np.ptp(dl[iflat]))
            ok = var <= FLAT_TOL
            print(f'   {"ok  " if ok else "FAIL"} ridge front top: deflection on the straight face: '
                  f'{dl[iflat].min():.2f}..{dl[iflat].max():.2f} mm (spread {var:.2f}); '
                  f'the ridge sits at z {sw["ridge_z"][0]:.2f}..{sw["ridge_z"][1]:.2f}')
            out[name] = dict(caught=not ok, spread=var)
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--group', default='all')
    ap.add_argument('--builds', default='all')
    ap.add_argument('--step', type=float, default=1.0)
    ap.add_argument('--wrong', action='store_true')
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()
    groups = ['keyed', 'chinless', 'x3'] if a.group == 'all' else [a.group]
    if a.wrong:
        r = wrong_covers()
        (OUTJ / 'check-wrong.json').write_text(json.dumps(r, indent=1))
        sys.exit(0 if all(v['caught'] for v in r.values()) else 1)
    res = run(groups, None if a.builds == 'all' else a.builds.split(','), a.step, verbose=not a.quiet)
    bad = [(k, r['check'], r['value']) for k, rows in res.items() for r in rows if not r['ok']]
    (OUTJ / f'check-{a.group}.json').write_text(json.dumps(res, indent=1))
    print(f'\n{sum(len(r) for r in res.values())} rows over {len(res)} builds; {len(bad)} failing')
    for b in bad[:40]:
        print('  FAIL', *b)
    sys.exit(1 if bad else 0)
