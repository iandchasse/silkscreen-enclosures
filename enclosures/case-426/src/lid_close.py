"""Does the lid close? The latch arms as they bend on the way in, PASS / FAIL (2026-10-12; case-368/src/lid_close.py's
latch_arms, here with the plate and the board read across each arm's width).

The 4.26's lid closed only under the screws' force. build.later_moves moves the lid as a rigid body, its latch arms
unbent, so it passed. Over the last ~7 mm each barb rides the tub's tongue and sliver, which bends its arm inward by
the barb's engagement (SNAP barb - gap, 0.45; 0.54 at the arm's top) until the barb drops into its pocket 0.1 before
home. Bent, the arm's top stands that much further in, toward the midplate's edge and the board's. In the plane through
each latch's centre the arm (its section of the built lid, above its root) is bent as a cantilever from its root,
loaded at the barb, by the least amount that clears the tub's section, at every step of the lid's last ARM_TRAVEL mm,
and held against the midplate's and the board's sections, each taken at Y_OFFS across the arm's width and merged (the
arm is a prism along the wall, so it meets a part if its section meets any of them).

PASS: every arm clears the midplate all the way home, with the plate nominal, pushed its EDGE_CLR toward the arm's
wall, and pushed toward the wall and shifted its EDGE_CLR along it either way (the plate also read at ALONG, past the
arm's ends: the notches held at 0.7 over their last 0.1 beside a detent strip, midplate.DETENT_HOLD), and the board as
placed; with the board pushed toward the wall (BOARD_PLAY) an arm may meet it only beside its
flat top (on the inner top chamfer, a 45-degree cam that pushes the board back), never with the flat top, which would
stop the lid. Reported, not judged: the plate with the panel PANEL_TOL thicker or thinner (the springs hold the glass
against the lip, so the plate sits that much further back or forward), and the least clearance to the plate on the
way in.
Main before the fix (9088325: notch 0.7, square tops): all 13 arms land on the plate 0.48 before home (nominal and
pushed), and with the board 0.35 toward a wall ten arms' flat tops land on it 2.48 before home.

build.py runs it on every build (CHECKS 'lid_close' -> out/<build>/lid-close.json). Standalone, on a built out folder:
    $env:SILKSCREEN_VARIANT = '<slug>'; python -B src/lid_close.py [out/<slug>]   # lid_body.stl, tub.stl, midplate.stl
"""
import json
import sys
from pathlib import Path
import numpy as np
import trimesh
from shapely.geometry import Polygon, box as sbox
from shapely.ops import unary_union
from shapely import affinity
import hw
import params as P
import joint

ARM_TRAVEL = 8.5                # the barbs meet the tongue's tip ~7.2 before home
STEP_FAR, STEP_NEAR, NEAR = 0.1, 0.01, 3.0
MAX_BEND = 1.2
MIN_MM2 = 2e-4                  # overlap in a section that counts as contact
MID_PLAY = 0.2                  # midplate.EDGE_CLR: the plate's edge to the tub's wall
BOARD_PLAY = (0.15, 0.35)       # the board toward a wall: its play on the H1/H2 snap posts (2.2 holes, 1.9 posts), and
                                # that plus the midplate's
PANEL_TOL = 0.2                 # the panel's thickness, +- (the drawing): the plate sits that much back or forward
Y_OFFS = (-2.2, -1.1, 0.0, 1.1, 2.2)   # plate and board sections across the arm's 4.5 width
ALONG = P.SNAP['w'] / 2 + MID_PLAY - 0.01   # +-: the plate's section under the arm's ends, the plate shifted along the wall


def _section(mesh, wall, c):
    """mesh's section in the plane through a latch's centre, as a region in (u, z): u inward from the wall's inner
    face (joint.WALLS), so an arm bends toward +u."""
    w = joint.WALLS[wall]
    if w['axis'] == 'y':
        s, cols = mesh.section(plane_origin=[0, c, 0], plane_normal=[0, 1, 0]), [0, 2]
    else:
        s, cols = mesh.section(plane_origin=[c, 0, 0], plane_normal=[1, 0, 0]), [1, 2]
    g = Polygon()
    if s is not None:
        for loop in s.discrete:
            if len(loop) >= 3:
                p = Polygon(loop[:, cols]).buffer(0)
                if p.area > 1e-7:
                    g = g.symmetric_difference(p)
    o, f = w['out'], w['face']
    return affinity.affine_transform(g, [-o, 0, 0, 1, o * f, 0]).buffer(0)


def _across(mesh, wall, c):
    """mesh's sections at Y_OFFS across the arm's width, merged."""
    return unary_union([_section(mesh, wall, c + yo) for yo in Y_OFFS]).buffer(0)


def _bend_fn(d, z_root, z_load):
    """u offset at height z of an arm bent by d at z_load: a cantilever from z_root under an end load at z_load,
    straight (its end slope) above it."""
    a = z_load - z_root

    def f(z):
        x = np.clip(z - z_root, 0.0, None)
        inner = d * x * x * (3 * a - x) / (2 * a ** 3)
        return np.where(x <= a, inner, d * (1.0 + 1.5 * (x - a) / a))
    return f


def _moved(rings, d, s, z_root, z_load):
    f = _bend_fn(d, z_root, z_load)
    return unary_union([Polygon(np.column_stack([r[:, 0] + f(r[:, 1]), r[:, 1] - s])) for r in rings]).buffer(0)


def latch_arms(lid_m, tub_m, mid_m, pcb_m):
    """The check (module docstring). Meshes in the CAD frame (trimesh)."""
    _, h = joint.snap_profile()
    z_root, z_load = h['z_root'], h['z_c']            # the arm's free length starts at its root; the barb's load
    S = P.SNAP
    rows, ok = {}, True
    travel = sorted(set([round(v, 3) for v in np.arange(ARM_TRAVEL, NEAR, -STEP_FAR)]
                        + [round(v, 3) for v in np.arange(NEAR, -1e-9, -STEP_NEAR)]), reverse=True)
    for wall, cs in P.SNAPS.items():
        for c in cs:
            L, T = _section(lid_m, wall, c), _section(tub_m, wall, c)
            M, B = _across(mid_m, wall, c), _across(pcb_m, wall, c)
            arm = L.intersection(sbox(-(S['barb'] + 0.45), z_root + 0.02, S['gap'] + S['t_root'] + 0.4, h['z_top'] + 1.0))
            rings = [np.asarray(Polygon(p.exterior.coords).segmentize(0.05).exterior.coords)
                     for p in getattr(arm, 'geoms', [arm]) if p.area > 1e-4]
            ztop = max(r[:, 1].max() for r in rings)
            top = np.vstack([r[np.abs(r[:, 1] - ztop) < 1e-3] for r in rings])
            u_flat = (float(top[:, 0].min()), float(top[:, 0].max()))
            tub_w = T.intersection(sbox(-3.0, z_root - 1.0, S['pocket'], h['z_top'] + 1.5))   # its wall, tongue, pocket
            Ma = unary_union([M] + [_section(mid_m, wall, c + e) for e in (-ALONG, ALONG)]).buffer(0)
            cases = {'midplate': M, f'midplate {MID_PLAY} toward the wall': affinity.translate(M, xoff=-MID_PLAY),
                     f'midplate {MID_PLAY} toward the wall and along it': affinity.translate(Ma, xoff=-MID_PLAY),
                     'board': B}
            info = {**{f'board {b} toward the wall': affinity.translate(B, xoff=-b) for b in BOARD_PLAY},
                    **{f'midplate{sh}, panel {dt:+.1f}': affinity.translate(M, xoff=-sh_v, yoff=-dt)
                       for dt in (PANEL_TOL, -PANEL_TOL) for sh, sh_v in (('', 0.0), (f' {MID_PLAY} toward the wall', MID_PLAY))}}
            plates = [k for k in (*cases, *info) if k.startswith('midplate')]
            first = {k: None for k in (*cases, *info)}
            clear = {k: None for k in plates}
            bend_max, s_pocket, tub_stop = 0.0, None, None
            for s in travel:
                if _moved(rings, 0.0, s, z_root, z_load).intersection(tub_w).area < 1e-5:
                    d = 0.0
                else:
                    lo, hi = 0.0, MAX_BEND
                    if _moved(rings, hi, s, z_root, z_load).intersection(tub_w).area >= 1e-5:
                        tub_stop = tub_stop or {'s_mm_before_home': s, 'note': f'the arm cannot bend past the tub ({hi})'}
                        d = hi
                    else:
                        for _ in range(12):
                            m = (lo + hi) / 2
                            if _moved(rings, m, s, z_root, z_load).intersection(tub_w).area < 1e-5:
                                hi = m
                            else:
                                lo = m
                        d = hi
                bend_max = max(bend_max, d)
                if bend_max > 0.2 and d < 0.05 and s_pocket is None:
                    s_pocket = s
                A = _moved(rings, d, s, z_root, z_load)
                for k, G in (*cases.items(), *info.items()):
                    if G.is_empty:
                        continue
                    if k in clear and first[k] is None:
                        g = A.distance(G)
                        clear[k] = g if clear[k] is None else min(clear[k], g)
                    if first[k] is not None:
                        continue
                    ov = A.intersection(G)
                    if ov.area > MIN_MM2:
                        row = {'s_mm_before_home': s, 'bend_mm': round(d, 3), 'overlap_mm2': round(ov.area, 4)}
                        if k.startswith('board'):
                            f = _bend_fn(d, z_root, z_load)
                            u_in = float(u_flat[1] + f(np.array([ztop]))[0])      # the flat top's inner end, bent
                            u_edge = G.bounds[0]                                   # the board's edge nearest the wall
                            row['flat_top'] = bool(u_edge < u_in - 1e-3)
                            row['board_edge_past_flat_mm'] = round(u_in - u_edge, 3)
                        first[k] = row
            fails = [k for k in cases if first[k] is not None] + (['tub'] if tub_stop else [])
            fails += [k for k in info if k.startswith('board') and first[k] is not None and first[k]['flat_top']]
            ok &= not fails
            rows[f"{wall} {'X' if wall == 'top' else 'Y'}{c:g}"] = {
                'ok': not fails, 'fails': fails, 'bend_max_mm': round(bend_max, 3), 'barb_in_pocket_at_mm': s_pocket,
                'arm_top_z': round(ztop, 3), 'flat_top_u': [round(u_flat[0], 3), round(u_flat[1], 3)],
                'contacts': {k: v for k, v in first.items() if v is not None},
                'least_clearance_to_plate_mm': {k: (round(v, 3) if first[k] is None else None) for k, v in clear.items()},
                **({'tub': tub_stop} if tub_stop else {})}
    return {'ok': bool(ok), 'latches': rows, 'n_blocked': sum(not r['ok'] for r in rows.values()),
            'note': "first contact on the way in (mm before home) for each case; flat_top: the board meets the arm's "
                    'flat top (a stop), else its inner top chamfer (a cam). least_clearance_to_plate_mm: over the whole '
                    'way in, None where it touches. Judged: the plate nominal and pushed toward the wall, the board centred, '
                    'and the board pushed toward the wall on the flat top only; the panel cases are reported'}


def mesh_of(shape, tol=0.01):
    v, t = shape.tessellate(tol, 0.1)
    return trimesh.Trimesh([(p.x, p.y, p.z) for p in v], t, process=True)


def run(lid_m, tub_m, mid_m):
    """lid_m: the lid body without its side keys (they are away from every latch), as a mesh."""
    return {'latch_arms': latch_arms(lid_m, tub_m, mid_m, mesh_of(hw.solids()['PCB']))}


def summary(r):
    la = r['latch_arms']
    lines = [f"lid closes, latch arms bent on the way in: {'PASS' if la['ok'] else 'FAIL'} "
             f"({la['n_blocked']} of {len(la['latches'])} blocked)"]
    for k, v in la['latches'].items():
        c = v['contacts']
        cl = v['least_clearance_to_plate_mm']
        judged = {n: x for n, x in c.items() if 'panel' not in n}
        lines.append(f"  {k:9s} bend {v['bend_max_mm']:.3f}, pocket at {v['barb_in_pocket_at_mm']}: "
                     + ('clear' if not judged else '; '.join(f"{n} at {x['s_mm_before_home']}"
                                                              + (f" ({'flat top' if x['flat_top'] else 'chamfer'})" if 'flat_top' in x else '')
                                                              for n, x in judged.items()))
                     + f"; plate clearance {cl['midplate']} / {cl[f'midplate {MID_PLAY} toward the wall']} pushed"
                     + ('' if v['ok'] else '  FAIL'))
    return '\n'.join(lines)


if __name__ == '__main__':
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else P.OUT
    lid_m, tub_m, mid_m = (trimesh.load(str(out / f'{n}.stl')) for n in ('lid_body', 'tub', 'midplate'))
    res = run(lid_m, tub_m, mid_m)
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(json.dumps(res, indent=1))
    print(summary(res))
    sys.exit(0 if res['latch_arms']['ok'] else 1)
