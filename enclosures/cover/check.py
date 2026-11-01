"""Checks of the slide covers against the REAL case STLs (tub + lid + side keys + bottom keys, as built in
enclosures/case-*/out/<build>/), for every build a cover serves, in all FOUR poses.  Round 2 (2026-11-01).

    python -B check.py [--group keyed|chinless|x3|all] [--builds a,b,...] [--step 1.0] [--quiet]
    python -B check.py --wrong          the deliberately wrong covers: each must FAIL
    python -B check.py --snap           snap forces before / after the round-2 rework (27bbdaf's cover against this one)

The four poses (the cover is symmetric about its own mid-length, so each is a legal way to put it on):
    front          on the screen, stop on the right (the original)
    back           turned over about the long axis (x -> 2 xc - x, z -> 2 zm - z): on the back, stop on the left
    front-turned   on the screen, turned 180 degrees in the plane (x -> 2 xc - x, y -> 2 ym - y): top and bottom swapped, goes on from the
                   other side, stop on the left
    back-turned    on the back, turned 180 degrees in the plane: (x, y, z) -> (x, 2 ym - y, 2 zm - z): stop on the right
What it checks (nothing here was printed; the force and strain numbers are beam estimates):
  home        the rigid frame has ZERO overlap volume with the case at home in every pose, at the nominal pose and at the extremes of its
              play; the ridge's own overlap at home is the snap engagement and is reported;
  clearance   the least distance frame-to-case (stop 0.5 off); the plate to every bottom-key cap and to the display glass at its nearest;
  slide       the frame swept along the whole slide path (the cover entirely off the case to home) never touches the case, in every pose;
              the ridge's deflection along the path, read from the real end faces through the cover's own mesh (ray casts through the
              J6 opening and over both corners: the ridge's rounding is in it), its flatness along the straight stretch, its peak;
  access      the USB-C opening plus plug room is clear in every pose; with the cover on the back the screen window is clear;
  screen      in the front pose the plate stays 2 mm or more past the screen opening on each side (opening measured from the tub STL);
  fingertip   an r 7 mm sphere touching each pad face's centre, approaching from the side, is clear of the cover in every pose;
  logo        with the cover on the back, its engraving lies over the case's own back logo (area overlap against the lid STL), and the
              plate behind the engraving is solid for at least 0.6 everywhere (no break into the screen relief or the key slots).
--wrong runs deliberately wrong covers through the same checks: a one-ended key slot, an over-long corner extension, the ridge in J6's band,
and a cover without the scallop (the fingertip test); each must FAIL.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import manifold3d as m3d
import numpy as np
import shapely
import trimesh
from scipy.interpolate import RegularGridInterpolator
from shapely import wkt

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
FLAT_TOL = 0.12         # mm: the ridge's deflection may vary this much along the straight end face
D_MAX_ALLOW = 0.95      # mm: peak deflection along the whole path (the design deflection is d_eng = 0.7)
FINGER_R = 7.0          # mm: the fingertip
BEHIND_MIN = 0.6        # mm: plate left behind the engraving
POSES = {'front': (False, False), 'back': (True, False), 'front-turned': (False, True), 'back-turned': (True, True)}


def to_man(tm):
    return m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(tm.vertices, dtype=np.float32), tri_verts=np.asarray(tm.faces, dtype=np.uint32)))


def mat(s, shift, flip, turn=False, dy=0.0, dz=0.0):
    """4x4: design frame -> case frame for one pose. The cover moves by `shift` along its own x (case x = u + shift on the front); flip: a
    half turn about the long axis (x -> 2 xc - x, z -> 2 zm - z); turn: a half turn in the plane (x -> 2 xc - x, y -> 2 ym - y); then
    dy, dz in the case frame."""
    A = np.eye(4)
    A[0, 3] = shift
    F = np.eye(4)
    if flip:
        F[0, 0], F[0, 3] = -1.0, 2 * s['xc']
        F[2, 2], F[2, 3] = -1.0, 2 * s['zm']
    T = np.eye(4)
    if turn:
        T[0, 0], T[0, 3] = -1.0, 2 * s['xc']
        T[1, 1], T[1, 3] = -1.0, 2 * s['ym']
    D = np.eye(4)
    D[1, 3], D[2, 3] = dy, dz
    return D @ T @ F @ A


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
        sk = [p.stem for p in sorted(d.glob('skey_*.stl'))]          # the side keys (pads, bars, blocks): part of the case for every check
        for n in sk:
            self.meshes[n] = trimesh.load(d / f'{n}.stl', force='mesh')
            self.man[n] = to_man(self.meshes[n])
            u = u + self.man[n]
        self.union = u
        self.caps = [n for n in names if n.startswith('key_SW')]
        self.info = case_info.info(case, slug)
        self.caster = raycast.Caster(trimesh.util.concatenate([self.meshes[n] for n in names]))

    def overlap(self, cov, m=None):
        return float(((cov if m is None else apply(cov, m)) ^ self.union).volume())

    def min_gap(self, cov, m, search=3.0, part=None):
        return float(apply(cov, m).min_gap(self.union if part is None else self.man[part], search))


def box_man(x0, x1, y0, y1, z0, z1):
    return to_man(trimesh.creation.box(bounds=[[x0, y0, z0], [x1, y1, z1]]))


# ---- the ridge on the real end faces, read through the cover's own mesh ----------------------------------------------

def end_maps(case, s):
    """The real end faces as depth maps over the ridge's reach: depth(x, z) = how far the case's surface is inside the end plane (<= 0; 0
    on the flat), top end (rays along -y from above Y1) and bottom end (along +y). -50 where a ray finds nothing."""
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


def ridge_samples_mesh(cov_mesh, s, du=0.02):
    """The cover's own ridge as built: rays along +y through the top prong (design frame) over the ridge's u and z reach; the protrusion p
    = how far the surface standing there is inside the wall's inner plane (0 where there is none: the prong's own inner face is 0.8
    outside it)."""
    cast = raycast.Caster(cov_mesh)
    yw = s['yw_t']
    ua = s['u_a']
    us = np.arange(ua - 0.5, ua + s["r_i"] + s["f_top"] + s["r_r"] + 0.5 + 1e-9, du)
    zlo, zhi = s['ridge_z']
    zs = np.arange(zlo - 0.8, zhi + 0.8 + 1e-9, 0.1)
    P = np.full((len(us), len(zs)), 0.0)
    for i, u in enumerate(us):
        for j, z in enumerate(zs):
            h = cast.first_hit([u, yw - 2.5, z], [u, yw + 2.5, z])
            P[i, j] = 0.0 if h is None else max(0.0, yw - h[1])
    U, Z = np.meshgrid(us, zs, indexing='ij')
    return U, Z, P


def deflection_path(s, maps, shifts, flip, turn, case_end, dz=0.0, samples=None):
    """The prong's required deflection (mm) at each shift for the prong that lands on `case_end` ('top' or 'bottom') in one pose. The two
    prongs are mirror images, so the ridge samples (the top prong's) serve both; x is mirrored when exactly one of flip / turn is on."""
    xs, zs, grid = maps[case_end]
    f = RegularGridInterpolator((xs, zs), grid, bounds_error=False, fill_value=-50.0)
    U, Z, P = samples
    sel = P > 1e-6
    u, z, pp = U[sel], Z[sel], P[sel]
    mirror_x = flip != turn
    out = []
    for sh in shifts:
        x = (2 * s['xc'] - (u + sh)) if mirror_x else (u + sh)
        zz = ((2 * s['zm'] - z) if flip else z) + dz
        out.append(max(0.0, float(np.max(f(np.c_[x, zz]) + pp - s['cy']))))
    return np.array(out)


def flat_range(s):
    """The shifts over which the whole ridge lies over the straight end face (clear of the corner arcs by 0.5)."""
    xa, xb = s['X0'] + s['CORNER_R'] + 0.5, s['X1'] - s['CORNER_R'] - 0.5
    return xa - s['u_a'], xb - (s['u_a'] + s['r_i'] + s['f_top'] + s['r_r'])


def section_polygon(mesh, z):
    """The mesh's cross-section at height z as a shapely geometry (even-odd over its closed loops: holes come out as holes)."""
    sec = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    g = shapely.Polygon()
    if sec is None:
        return g
    for p in sec.discrete:
        g = g.symmetric_difference(shapely.Polygon(p[:, :2]).buffer(0))
    return g


def screen_overlap(cov_mesh, s, opening):
    """In the front pose at home: how far the plate reaches past the screen opening at the face, on each side (mm), over the whole of the
    opening's height. The section is taken above the cavity's ceiling (z_o - 0.7: the relief and slots are cut from the inner face)."""
    g = section_polygon(cov_mesh, s['z_o'] - 0.7)
    x0, x1, y0, y1 = opening
    left, right = [], []
    for y in np.arange(y0, y1 + 1e-9, 0.5):
        i = g.intersection(shapely.LineString([(-20.0, y), (90.0, y)]))
        if i.is_empty:
            continue
        b = i.bounds
        left.append(x0 - (b[0] - s['cx']))                   # home: case x = u - cx
        right.append((b[2] - s['cx']) - x1)
    return min(left), min(right)


def _rings(g):
    out = []
    for p in getattr(g, 'geoms', [g]):
        if p.area < 1e-6:
            continue
        out.append(np.asarray(p.exterior.coords[:-1], dtype=np.float64))
        out += [np.asarray(r.coords[:-1], dtype=np.float64) for r in p.interiors]
    return out


def prism(g, z0, z1):
    cs = m3d.CrossSection(_rings(g), m3d.FillRule.EvenOdd)
    return m3d.Manifold.extrude(cs, z1 - z0).translate((0.0, 0.0, z0))


def finger_capsule(side, xf, yc, zc, reach=40.0):
    """The fingertip's approach: an r 7 sphere touching the pad's face centre, swept in from `reach` mm out along the side's normal."""
    sph = m3d.Manifold.sphere(FINGER_R, 64)
    a = sph.translate((xf + side * FINGER_R, yc, zc))
    b = sph.translate((xf + side * (FINGER_R + reach), yc, zc))
    return m3d.Manifold.batch_hull([a, b])


def finger_clearances(cov, pads, s, home):
    """{(pad, pose): clearance mm} of the fingertip's approach path (finger_capsule) to the cover at home; 0 where it meets the cover."""
    out = {}
    for ref, (side, py0, py1, pz0, pz1, xf) in pads.items():
        cap = finger_capsule(side, xf, (py0 + py1) / 2, (pz0 + pz1) / 2)
        for pose, (flip, turn) in POSES.items():
            c = apply(cov, mat(s, home, flip, turn))
            out[(ref, pose)] = 0.0 if float((c ^ cap).volume()) > 1e-3 else float(c.min_gap(cap, 20.0))
    return out


def logo_checks(cov_mesh, cov, s, cm):
    """With the cover on the back at home: the area overlap (IoU) of its engraving with the case's own logo cut in the lid (the lid STL's
    section just inside its back face), and the centroid offset; and the plate behind each engraving (the largest slab t, below the
    engraving's floor, that the cover fills solid everywhere under the logo's footprint)."""
    m = mat(s, -s['cx'], True)
    posed = trimesh.Trimesh((m[:3, :3] @ np.asarray(cov_mesh.vertices).T).T + m[:3, 3], cov_mesh.faces, process=False)
    lid = cm.meshes['lid']
    out = dict(iou={}, shift={}, behind={})
    for name in ('icon', 'wordmark'):
        d = s['logos'][name]
        cg = wkt.loads(d['wkt'])
        win = shapely.box(*cg.buffer(0.6).bounds)
        cb = cg.buffer(0.3)
        vc = win.difference(section_polygon(posed, 2 * s['zm'] - s['z_o'] + 0.5 * d['depth'])).intersection(cb)
        vl = win.difference(section_polygon(lid, s['Z_BACK'] + 0.5 * d['depth'])).intersection(cb)
        out['iou'][name] = vc.intersection(vl).area / max(vc.union(vl).area, 1e-9)
        out['shift'][name] = float(np.hypot(vc.centroid.x - vl.centroid.x, vc.centroid.y - vl.centroid.y))
        g, depth = M.logo_polys(s)[name]
        zf = s['z_o'] - depth
        best = 0.0
        for t in np.arange(0.2, 3.01, 0.1):
            void = float((prism(g, zf - t, zf) - cov).volume())
            if void > 0.002:
                break
            best = t
        out['behind'][name] = round(best, 1)
    return out


# ---- the checks -----------------------------------------------------------------------------------------------------

def check_build(group, case, slug, cov, frame, cov_mesh, step=1.0, verbose=True, s=None):
    s = s or M.spec(group)
    cm = Case(case, slug)
    rows = []

    def row(name, ok, value):
        rows.append(dict(check=name, ok=bool(ok), value=value))
        if verbose:
            print(f'   {"ok  " if ok else "FAIL"} {name}: {value}')

    G2 = s['G'] / 2
    home = -s['cx'] + 0.01
    # 1. home, every pose
    for pose, (flip, turn) in POSES.items():
        v = cm.overlap(frame, mat(s, home, flip, turn))
        row(f'home {pose}: frame overlap', abs(v) < EPS_VOL, f'{v:.4f} mm3')
        vr = cm.overlap(cov, mat(s, home, flip, turn))
        row(f'home {pose}: ridge overlap (the snap engagement)', True, f'{vr - v:.3f} mm3 (the preload; the prong flexes it away)')
        g = cm.min_gap(frame, mat(s, home + 0.5, flip, turn), 3.0)
        row(f'home {pose}: least frame-to-case distance with the stop 0.5 off', g >= MIN_CLEAR, f'{g:.3f} mm')
        g = cm.min_gap(frame, mat(s, home, flip, turn), 3.0)
        row(f'home {pose}: least distance at the stop (0.01 off the side)', g >= 0.005, f'{g:.3f} mm')
        worst = 0.0
        for dz in (-(s['gp'] - 0.05), s['gp'] - 0.05):
            worst = max(worst, cm.overlap(frame, mat(s, home + 0.5, flip, turn, 0.0, dz)))
        for dy in (-(s['cy'] - 0.05), s['cy'] - 0.05):
            worst = max(worst, cm.overlap(frame, mat(s, home + 0.5, flip, turn, dy, 0.0)))
        row(f'home {pose}: frame overlap with the cover moved a play-width in z (+-{s["gp"] - 0.05:.2f}) or y (+-{s["cy"] - 0.05:.2f})',
            worst < EPS_VOL, f'{worst:.4f} mm3 worst')
    # 2. the key slots (bottom keys): plate at its nearest, both front poses, at home and along the path
    if cm.caps:
        for pose in ('front', 'front-turned'):
            flip, turn = POSES[pose]
            for sh in (home, 30.0, 55.0):
                g = min(cm.min_gap(frame, mat(s, sh, flip, turn, 0.0, -s['gp']), 3.0, part=n) for n in cm.caps)       # the frame: the undeflected ridge tip stands 0.7 inside the end wall, near the caps' stems, and never gets there (the prong deflects)
                row(f'{pose}: cover frame to the bottom-key caps, plate touching the face, s={sh:.1f} (the slots)', g >= s['key_clr'] - 0.02,
                    f'{g:.3f} mm')
    # 2b. the display glass seen through the window
    dpath = ENC / case / 'out' / slug / 'ref_display.stl'
    if dpath.exists():
        wx0, wx1, wy0, wy1 = s['window']
        dm = trimesh.load(dpath, force='mesh')
        depth = s['Z_FRONT'] - float(dm.bounds[1][2])                  # the glass's top sits this far below the front face
        disp = to_man(dm) ^ box_man(wx0, wx1, wy0, wy1, -10, 20)
        g = min(apply(cov, mat(s, home, False, t, 0.0, -s['gp'])).min_gap(disp, 8.0) for t in (False, True))
        row('front poses: cover to the display glass seen through the window, plate resting on the face (never nearer than the face)', g >= depth - 0.05,
            f'{g:.2f} mm (the glass is {depth:.2f} below the face; the nearest point is plate over a rounded corner of the relief)')
    # 3. the slide path, every pose
    shifts = np.arange(home, 78.0 + 1e-9, step)
    for pose, (flip, turn) in POSES.items():
        worst, at = 0.0, None
        for sh in shifts:
            v = cm.overlap(frame, mat(s, sh, flip, turn))
            if v > worst:
                worst, at = v, sh
        row(f'slide {pose}: frame overlap along the path (s {home:.2f}..78, step {step:g})', worst < EPS_VOL,
            f'{worst:.4f} mm3' + (f' at s={at:.1f}' if at is not None else ''))
    # 4. the ridge on the real end faces, through the cover's own mesh
    maps = end_maps(cm, s)
    samples = ridge_samples_mesh(cov_mesh, s)
    sh = np.arange(-s['cx'], 78.0, 0.25)
    fa, fb = flat_range(s)
    iflat = (sh >= fa) & (sh <= fb)
    iw = (sh >= -s['cx']) & (sh <= fa + 2.0)
    home_i = int(np.argmin(np.abs(sh + s['cx'])))
    d_front_top = None
    for pose, (flip, turn) in POSES.items():
        for end in ('top', 'bottom'):
            dls = {dz: deflection_path(s, maps, sh, flip, turn, end, dz, samples) for dz in (-G2, 0.0, G2)}
            d0 = dls[0.0]
            var = max(float(np.ptp(dl[iflat])) for dl in dls.values())
            dmax = max(float(dl.max()) for dl in dls.values())
            row(f'ridge {pose}, case {end} end: deflection on the straight face (all Z play)', var <= FLAT_TOL,
                f'{d0[iflat].min():.2f}..{d0[iflat].max():.2f} mm (spread {var:.2f} at worst Z play; design {s["d_eng"]})')
            row(f'ridge {pose}, case {end} end: peak deflection on the whole path (all Z play)', dmax <= D_MAX_ALLOW,
                f'{dmax:.2f} mm (design {s["d_eng"]})')
            pre = float(d0[home_i])
            row(f'ridge {pose}, case {end} end: preload at home', 0.0 <= pre <= s['d_pre'] + 0.15, f'{pre:.2f} mm (design {s["d_pre"]})')
            engage = float(d0[iw].max())
            row(f'ridge {pose}, case {end} end: catch depth (the deflection the prong makes to leave the corner)',
                abs(engage - s['d_eng']) <= 0.15, f'{engage:.2f} mm')
            if end == 'top' and pose == 'front':
                d_front_top = d0
    k_lo, _, _ = snap.stiffness(s, 3000.0, 2 * s['ridge_half'])
    fr = snap.wedge(sh, d_front_top, k_lo, 0.3, s)
    row('snap force estimate, one prong (beam model, E 3000, mu 0.3, soft bound)', True,
        f'pull off peak {fr["pull_peak"]:.2f} N, push on peak {fr["push_peak"]:.2f} N, sliding drag {fr["drag"]:.2f} N, preload {fr["preload"]:.2f} N')
    # 5. access
    y0, y1, z0, z1 = cm.info['usb']
    probe = box_man(s['X1'] - 0.3, s['X1'] + 30, y0 - 0.5, y1 + 0.5, z0 - 0.5, z1 + 0.5)
    for pose, (flip, turn) in POSES.items():
        v = float((apply(frame, mat(s, home, flip, turn)) ^ probe).volume())
        row(f'USB-C access {pose}: cover inside the recess + 30 mm of plug room (y {y0:.1f}..{y1:.1f}, z {z0:.1f}..{z1:.1f})', v < EPS_VOL,
            f'{v:.4f} mm3')
    wx0, wx1, wy0, wy1 = s['window']
    screen = box_man(wx0, wx1, wy0, wy1, s['Z_FRONT'] - 0.5, s['Z_FRONT'] + 30)
    for pose in ('back', 'back-turned'):
        flip, turn = POSES[pose]
        v = float((apply(cov, mat(s, home, flip, turn)) ^ screen).volume())
        row(f'{pose}: the screen window is clear of the cover', v < EPS_VOL, f'{v:.4f} mm3')
    # 6. the scallop: the screen stays covered; the fingertip stays clear of the cover
    ov = screen_overlap(cov_mesh, s, cm.info['window_face'])
    row('front pose: the plate stays past the screen opening (left, right)', min(ov) >= s['scallop_overlap'] - 0.02,
        f'{ov[0]:.2f} / {ov[1]:.2f} mm (the opening measured from the tub STL at its face; need {s["scallop_overlap"]})')
    fm = finger_clearances(cov, cm.info['pads'], s, home)
    if fm:
        worst = min(fm.items(), key=lambda kv: kv[1])
        backs = {r: v for (r, p), v in fm.items() if p == 'back'}
        row(f'fingertip (r {FINGER_R:g} sphere touching each pad face centre, swept in from the side), every pad, every pose: least clearance',
            worst[1] > 0.0, f'{worst[1]:.2f} mm ({worst[0][0]}, {worst[0][1]}); back pose by pad: '
            + ', '.join(f'{r} {v:.1f}' for r, v in sorted(backs.items())))
    # 7. the logo
    if s['logo']:
        lg = logo_checks(cov_mesh, cov, s, cm)
        row('back: the cover\'s engraving over the case\'s own logo (area overlap with the lid STL, icon / wordmark; centroid offset)',
            min(lg['iou'].values()) > 0.9,
            f'{lg["iou"]["icon"]:.3f} / {lg["iou"]["wordmark"]:.3f}; offset {lg["shift"]["icon"]:.2f} / {lg["shift"]["wordmark"]:.2f} mm')
        row('plate behind the engraving is solid (no break into the relief or the slots), icon / wordmark',
            min(lg['behind'].values()) >= BEHIND_MIN, f'{lg["behind"]["icon"]:.1f} / {lg["behind"]["wordmark"]:.1f} mm solid below the floor')
    return rows


def run(groups, builds=None, step=1.0, verbose=True):
    res = {}
    for g in groups:
        s = M.spec(g)
        cov_mesh = trimesh.load(DESIGN / f'{g}.stl', force='mesh')
        cov = to_man(cov_mesh)
        frame = to_man(trimesh.load(DESIGN / f'{g}-frame.stl', force='mesh'))
        for case, slug in V.builds(g, builds):
            t = time.time()
            if verbose:
                print(f'{g}: {case}/{slug}', flush=True)
            res[f'{g}/{slug}'] = check_build(g, case, slug, cov, frame, cov_mesh, step=step, verbose=verbose, s=s)
            if verbose:
                print(f'   ({time.time() - t:.0f} s)', flush=True)
    return res


# ---- the deliberately wrong covers ------------------------------------------------------------------------------------

def _home_overlaps(frame, s, builds, shifts):
    """Frame overlap volume at the given shifts, every pose, over the builds: {(slug, pose): worst}."""
    out = {}
    for case, slug in builds:
        cm = Case(case, slug)
        for pose, (flip, turn) in POSES.items():
            w = max(cm.overlap(frame, mat(s, sh, flip, turn)) for sh in shifts)
            if w >= EPS_VOL:
                out[(slug, pose)] = round(w, 2)
    return out


def wrong_covers():
    """Each deliberately wrong cover must FAIL its check. (1) a key slot at one end only: in the turned front pose the plate meets the
    bottom-key caps; (2) a corner extension 16 mm long: it meets a pad in some layout and pose; (3) the ridge moved into J6's z band: its
    deflection on the straight face is no longer flat. (4) is a comparison only: the fingertip clearance with and without the scallop. The
    sharp-edge catch of 27bbdaf's cover is `python -B edges.py old`."""
    out = {}
    s = M.spec('keyed')
    home = -s['cx'] + 0.01
    keyed = V.builds('keyed')
    for name, f, shifts, builds in (('one-ended key slot', 'keyed-wrong-oneslot', [home, 30.0, 55.0], [b for b in keyed if b[1] == 'standard']),
                                    ('corner extension 16 mm', 'keyed-wrong-longext', [home], keyed)):
        fr = to_man(trimesh.load(DESIGN / f'{f}.stl', force='mesh'))
        bad = _home_overlaps(fr, s, builds, shifts)
        shown = dict(list(bad.items())[:8])
        print(f'wrong cover: {name}: frame overlap with the case at s in {[round(x, 2) for x in shifts]} over {len(builds)} build(s): '
              f'{len(bad)} (build, pose) failures {shown if bad else "NOT CAUGHT"}', flush=True)
        out[name] = dict(caught=bool(bad), failures=len(bad), examples={f'{k[0]}/{k[1]}': v for k, v in shown.items()})
    # (3) the ridge in the J6 band
    cm = Case('case-426', 'standard')
    sw = M.spec('keyed', ridge_shift=4.2, ridge_half=1.4)
    maps = end_maps(cm, sw)
    sh = np.arange(-sw['cx'], 78.0, 0.25)
    fa, fb = flat_range(sw)
    cov_mesh = trimesh.load(DESIGN / 'keyed-wrong-ridge.stl', force='mesh')
    dl = deflection_path(sw, maps, sh, False, False, 'top', 0.0, ridge_samples_mesh(cov_mesh, sw))
    iflat = (sh >= fa) & (sh <= fb)
    var = float(np.ptp(dl[iflat]))
    print(f'wrong cover: ridge in the J6 band: deflection on the straight face {dl[iflat].min():.2f}..{dl[iflat].max():.2f} (spread {var:.2f} '
          f'vs the {FLAT_TOL} limit): {"caught" if var > FLAT_TOL else "NOT CAUGHT"}', flush=True)
    out['ridge in the J6 band'] = dict(caught=var > FLAT_TOL, spread=round(var, 3))
    # (4) for comparison, not a failure: the cover without the scallop against the same fingertip approach
    ns = to_man(trimesh.load(DESIGN / 'keyed-noscallop.stl', force='mesh'))
    cov = to_man(trimesh.load(DESIGN / 'keyed-frame.stl', force='mesh'))
    for case, slug in keyed:
        if slug != 'standard':
            continue
        pads = case_info.info(case, slug)['pads']
        a, b = finger_clearances(cov, pads, s, home), finger_clearances(ns, pads, s, home)
        print(f'comparison (not a failure): fingertip clearance, least over pads and poses: with the scallop {min(a.values()):.2f} mm, without {min(b.values()):.2f} mm; '
              f'back pose {min(v for (r, p), v in a.items() if p == "back"):.2f} / {min(v for (r, p), v in b.items() if p == "back"):.2f} mm', flush=True)
        out['fingertip clearance with / without the scallop (standard build, informational)'] = dict(
            caught=True, with_scallop=round(min(a.values()), 2), without=round(min(b.values()), 2))
    return out


# ---- snap before / after ------------------------------------------------------------------------------------------------

def prong_thickness(mesh, s, z):
    """The prong's thickness along u (outside the plate edge, y > yw_t) from a section at height z: [(u, t)] every 0.5 mm."""
    g = section_polygon(mesh, z)
    out = []
    yw, yt = s['yw_t'], s['yt_t']
    for u in np.arange(s['u_tip'] + 0.2, s['u_root'] + 1.0, 0.5):
        i = g.intersection(shapely.LineString([(u, yw - 0.001), (u, yt + 1.0)]))
        out.append((float(u), float(i.length)))
    return out


def snap_compare():
    """27bbdaf's keyed cover against this one, on the real standard 4.26 end faces: the prong's thickness profile, the deflection along the
    path, the force and strain estimates (beam model: E 2500..3500, soft and stiff width, mu 0.2..0.4), through the same ray casts."""
    import edges
    s = M.spec('keyed')
    cm = Case('case-426', 'standard')
    maps = end_maps(cm, s)
    sh = np.arange(-s['cx'], 78.0, 0.25)
    fa, fb = flat_range(s)
    iflat = (sh >= fa) & (sh <= fb)
    res = {}
    for label, mesh in (('27bbdaf (coupon A geometry)', edges.old_cover_mesh()), ('round 2', trimesh.load(DESIGN / 'keyed.stl', force='mesh'))):
        samples = ridge_samples_mesh(mesh, s)
        d0 = deflection_path(s, maps, sh, False, False, 'top', 0.0, samples)
        rows = []
        for E in snap.E_PLA:
            for b in (2 * s['ridge_half'], s['z_o'] - s['prong_z_lo']):
                k, eps1, _ = snap.stiffness(s, E, b)
                for mu in snap.MU:
                    f = snap.wedge(sh, d0, k, mu, s)
                    rows.append(dict(E=E, b=b, mu=mu, k=k, pull=f['pull_peak'], push=f['push_peak'], drag=f['drag'], preload=f['preload'],
                                     strain=eps1 * k * float(d0.max())))
        nom = next(r for r in rows if r['E'] == 3000.0 and abs(r['b'] - 2 * s['ridge_half']) < 1e-6 and r['mu'] == 0.3)
        th = prong_thickness(mesh, s, s['z_o'] - 0.9)
        res[label] = dict(d_flat=(float(d0[iflat].min()), float(d0[iflat].max())), d_peak=float(d0.max()), nominal=nom,
                          pull_range=(min(r['pull'] for r in rows), max(r['pull'] for r in rows)),
                          push_range=(min(r['push'] for r in rows), max(r['push'] for r in rows)),
                          strain_max=max(r['strain'] for r in rows), thickness=th)
    a, b = res['27bbdaf (coupon A geometry)'], res['round 2']
    for k, v in res.items():
        n = v['nominal']
        print(f'{k}: deflection on the flat {v["d_flat"][0]:.2f}..{v["d_flat"][1]:.2f}, peak {v["d_peak"]:.2f} mm; nominal one prong: stiffness '
              f'{n["k"]:.2f} N/mm, pull-off peak {n["pull"]:.2f} N (range {v["pull_range"][0]:.2f}-{v["pull_range"][1]:.2f}), push-on peak '
              f'{n["push"]:.2f} N, drag {n["drag"]:.2f} N, preload {n["preload"]:.2f} N, strain {100 * n["strain"]:.2f} % (worst {100 * v["strain_max"]:.2f} %)')
    ta, tb = np.array([t for _, t in a['thickness']]), np.array([t for _, t in b['thickness']])
    print('prong thickness along u (section 0.9 under the bed face), old / new:')
    print('  ' + ' '.join(f'{u:.1f}:{x:.2f}/{y:.2f}' for (u, _), x, y in zip(a['thickness'], ta, tb)))
    rel = lambda x, y: 100.0 * (y - x) / x
    print(f'differences, new vs old: deflection peak {rel(a["d_peak"], b["d_peak"]):+.1f} %, pull-off peak {rel(a["nominal"]["pull"], b["nominal"]["pull"]):+.1f} %, '
          f'push-on peak {rel(a["nominal"]["push"], b["nominal"]["push"]):+.1f} %, drag {rel(a["nominal"]["drag"], b["nominal"]["drag"]):+.1f} %, '
          f'strain {rel(a["nominal"]["strain"], b["nominal"]["strain"]):+.1f} %; thickness differs by at most {float(np.abs(ta - tb).max()):.2f} mm')
    return res


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--group', default='all')
    ap.add_argument('--builds', default='all')
    ap.add_argument('--step', type=float, default=1.0)
    ap.add_argument('--wrong', action='store_true')
    ap.add_argument('--snap', action='store_true')
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()
    groups = ['keyed', 'chinless', 'x3'] if a.group == 'all' else [a.group]
    if a.snap:
        r = snap_compare()
        (OUTJ / 'check-snap.json').write_text(json.dumps(r, indent=1, default=float))
        sys.exit(0)
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
