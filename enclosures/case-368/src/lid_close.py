"""Does the lid close? Two checks the rigid sweep (build.later_moves) cannot make, PASS / FAIL (2026-10-12).

Ian printed the standard 3.68 from main's print/ (2026-10-11) and its lid would not shut: it rocked on a high spot in
the middle and stopped about 1 mm short at whichever end he pressed, worse with the battery in. His board is a Rev 1.0
cut for the x3, with R72/R74 fitted, R36/R73/SW5 off, J5's leads and the switch pins trimmed, and the two charging
bodge wires laid against its back. build.later_moves moves the lid as a rigid body, its latch arms unbent, and it
has no bodge wires, so it passed. These two checks failed on that lid (9c5a639):

  latch_arms  Over the last ~8 mm each latch barb rides the tub's tongue and sliver, which bends its arm inward by
              the barb's engagement (SNAP barb - gap, 0.45) until the barb drops into its pocket just before home.
              Bent, the arm's top stands that much further in, toward the midplate's edge and the board's. In the
              plane through each latch's centre the arm (its section of the built lid, above its root) is bent as a
              cantilever from its root, loaded at the barb, by the least amount that clears the tub's section, at
              every step of the lid's last ARM_TRAVEL mm, and held against the midplate's and the board's sections.
              PASS: every arm clears the midplate all the way home, with the plate nominal and pushed its EDGE_CLR
              toward the arm's wall, and the board as placed; with the board pushed toward the wall (BOARD_PLAY) an
              arm may meet it only beside its flat top (on the 45-degree inner top chamfer, a cam that pushes the
              board back), never with the flat top, which would stop the lid.
              9c5a639 (latch notch 0.7, square tops): 11 of the 12 arms land on the midplate 0.68 before home.
              Home is the lid's as-printed home (2026-10-13), params.LID_HOME_DZ past its CAD position (s < 0):
              the barbs are drawn to drop into their pockets there (params.LATCH_PHASE).
  rework      The charging fix for a Rev 1.0 board cut for the x3 (README, "Board notes"; board-trim.md): 3V3 from
              R40 pad 2 to R81 pad 2, or across the cut's two 3V3 stubs, and GND from C6 pad 2 to C21 pad 2, laid on
              the back of the board. Each is a WIRE_D wire on its straight route, lying on the deepest part under it
              (a square section: the envelope), against the lid at home and the pack at BATT_T_MAX on its floor.
              PASS: clear of both.
              9c5a639 (0.1 of air over the pack): the GND wire on C6 stands 0.70 into the pack.

build.py runs both on every build (out/<build>/insertion.json, '_lid_close'). Standalone, on a built out folder:
    python -B src/lid_close.py [out/<build>]      # reads lid_body.stl, tub.stl, midplate.stl; the board from hw
"""
import json
import math
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

ARM_TRAVEL = 8.5                # the barbs meet the tongue's tip ~8.0 before home
STEP_FAR, STEP_NEAR, NEAR = 0.1, 0.01, 3.0
MAX_BEND = 1.2
MIN_MM2 = 2e-4                  # overlap in a section that counts as contact
MID_PLAY = 0.2                  # midplate.EDGE_CLR: the plate's edge to the tub's wall
BOARD_PLAY = (0.15, 0.35)       # the board toward a wall: its play on the H2/H6 snap posts (2.2 holes, 1.9 posts), and
                                # that plus the midplate's
WIRE_D = 1.0                    # hookup wire with its insulation; 30 AWG wire-wrap is about 0.5
CUT_STUBS_X = (43.286, 56.36)   # the two cut 3V3 tracks at the board's edge (board-trim.md, "Copper crossing")


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
    """The latch_arms check (module docstring). Meshes in the CAD frame (trimesh)."""
    _, h = joint.snap_profile()
    z_root, z_load = h['z_root'], h['z_c']            # the arm's free length starts at its root; the barb's load
    S = P.SNAP
    rows, ok = {}, True
    # down to the lid's as-printed home, params.LID_HOME_DZ past its CAD position (2026-10-13: the barbs are drawn to
    # meet their pockets there, params.LATCH_PHASE)
    travel = sorted(set([round(v, 3) for v in np.arange(ARM_TRAVEL, NEAR, -STEP_FAR)]
                        + [round(v, 3) for v in np.arange(NEAR, -P.LID_HOME_DZ - 1e-9, -STEP_NEAR)]
                        + [round(-P.LID_HOME_DZ, 3)]), reverse=True)
    for wall, cs in P.SNAPS.items():
        for c in cs:
            L, T, M, B = (_section(m, wall, c) for m in (lid_m, tub_m, mid_m, pcb_m))
            arm = L.intersection(sbox(-(S['barb'] + 0.45), z_root + 0.02, S['gap'] + S['t_root'] + 0.4, h['z_top'] + 1.0))
            rings = [np.asarray(Polygon(p.exterior.coords).segmentize(0.05).exterior.coords)
                     for p in getattr(arm, 'geoms', [arm]) if p.area > 1e-4]
            ztop = max(r[:, 1].max() for r in rings)
            u_flat_in = max(r[np.abs(r[:, 1] - ztop) < 1e-3, 0].max() for r in rings if (np.abs(r[:, 1] - ztop) < 1e-3).any())
            tub_w = T.intersection(sbox(-3.0, z_root - 1.0, S['pocket'], h['z_top'] + 1.5))   # its wall, tongue, pocket
            cases = {'midplate': affinity.translate(M, xoff=0.0),
                     f'midplate {MID_PLAY} toward the wall': affinity.translate(M, xoff=-MID_PLAY),
                     'board': B}
            info = {f'board {b} toward the wall': affinity.translate(B, xoff=-b) for b in BOARD_PLAY}
            first = {k: None for k in (*cases, *info)}
            bend_max, s_pocket = 0.0, None
            for s in travel:
                if _moved(rings, 0.0, s, z_root, z_load).intersection(tub_w).area < 1e-5:
                    d = 0.0
                else:
                    lo, hi = 0.0, MAX_BEND
                    if _moved(rings, hi, s, z_root, z_load).intersection(tub_w).area >= 1e-5:
                        first.setdefault('tub', None)
                        first['tub'] = first['tub'] or {'s_mm_before_home': s, 'note': f'the arm cannot bend past the tub ({hi})'}
                        d = hi
                    else:
                        for _ in range(12):
                            m = (lo + hi) / 2
                            if _moved(rings, m, s, z_root, z_load).intersection(tub_w).area < 1e-5:
                                hi = m
                            else:
                                lo = m
                        d = hi
                if d > bend_max:
                    bend_max = d
                if bend_max > 0.2 and d < 0.05 and s_pocket is None:
                    s_pocket = s
                A = None
                for k, G in (*cases.items(), *info.items()):
                    if first[k] is not None or G.is_empty:
                        continue
                    if A is None:
                        A = _moved(rings, d, s, z_root, z_load)
                    ov = A.intersection(G)
                    if ov.area > MIN_MM2:
                        row = {'s_mm_before_home': s, 'bend_mm': round(d, 3), 'overlap_mm2': round(ov.area, 4)}
                        if k.startswith('board'):
                            f = _bend_fn(d, z_root, z_load)
                            u_in = float(u_flat_in + f(np.array([ztop]))[0])      # the flat top's inner end, bent
                            u_edge = G.bounds[0]                                   # the board's edge nearest the wall
                            row['flat_top'] = bool(u_edge < u_in - 1e-3)
                            row['board_edge_past_flat_mm'] = round(u_in - u_edge, 3)
                        first[k] = row
            fails = [k for k in cases if first[k] is not None] + (['tub'] if first.get('tub') else [])
            fails += [k for k in info if first[k] is not None and first[k]['flat_top']]
            ok &= not fails
            rows[f"{wall} {'X' if wall == 'top' else 'Y'}{c:g}"] = {'ok': not fails, 'fails': fails, 'bend_max_mm': round(bend_max, 3),
                                      'barb_in_pocket_at_mm': s_pocket, 'arm_top_z': round(ztop, 3),
                                      'contacts': {k: v for k, v in first.items() if v is not None}}
    return {'ok': bool(ok), 'latches': rows,
            'n_blocked': sum(not r['ok'] for r in rows.values()),
            'note': 'first contact on the way in (mm before home) for each case; flat_top: the board meets the arm\'s '
                    'flat top (a stop), else its inner top chamfer (a cam)'}


def pad_xy(ref, name):
    """A pad's centre in the CAD frame (as midplate.tht_pads)."""
    f = hw.footprints()[ref]
    fx, fy = f['cad']
    rot = math.radians(f['rot'])
    lx, ly = next(p for p in f['pads'] if p['name'] == name)['local']
    return (round(fx + lx * math.cos(rot) + ly * math.sin(rot), 3),
            round(fy - (-lx * math.sin(rot) + ly * math.cos(rot)), 3))


def routes():
    y = hw.PCB_CUT_Y - WIRE_D / 2
    return {'GND C6.2-C21.2': (pad_xy('C6', '2'), pad_xy('C21', '2')),
            '3V3 R40.2-R81.2': (pad_xy('R40', '2'), pad_xy('R81', '2')),
            '3V3 across the cut stubs': ((CUT_STUBS_X[0], y), (CUT_STUBS_X[1], y))}


def wire(a, b, step=0.25):
    """The wire from a to b as a list of (x0, x1, y0, y1, z_low, z_high) boxes: each a step of the route, WIRE_D
    wide, lying on the deepest board part under it (or on the board), WIRE_D deep."""
    import cadquery as cq
    parts = {r: s for r, s in hw.solids().items() if r != 'PCB'}
    bbs = {r: s.BoundingBox() for r, s in parts.items()}
    a, b = np.array(a, float), np.array(b, float)
    n = max(1, int(math.ceil(np.linalg.norm(b - a) / step)))
    out, r = [], WIRE_D / 2
    for i in range(n + 1):
        p = a + (b - a) * i / n
        x0, x1, y0, y1 = p[0] - r, p[0] + r, p[1] - r, p[1] + r
        z = 0.0
        for ref, bb in bbs.items():
            if bb.xmax < x0 or bb.xmin > x1 or bb.ymax < y0 or bb.ymin > y1 or bb.zmin >= z:
                continue
            cut = parts[ref].intersect(cq.Solid.makeBox(2 * r, 2 * r, 20, cq.Vector(x0, y0, -20)))
            if cut.Volume() > 1e-6:
                z = min(z, cut.BoundingBox().zmin)
        out.append((x0, x1, y0, y1, z - WIRE_D, z))
    return out


def rework(lid_shape, lid_m):
    """The rework check (module docstring). lid_shape / lid_m: the lid as fitted, as a cq.Shape and a mesh."""
    import cadquery as cq
    bx = P.BATT['x'], P.BATT['y']
    face = P.BATT_FRONT
    rows, ok = {}, True
    for name, (a, b) in routes().items():
        boxes = wire(a, b)
        under = [w for w in boxes if w[1] > bx[0][0] and w[0] < bx[0][1] and w[3] > bx[1][0] and w[2] < bx[1][1]]
        pack = round(min(w[4] for w in under) - face, 3) if under else None
        solid = cq.Compound.makeCompound([cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0))
                                          for x0, x1, y0, y1, z0, z1 in boxes])
        lid_mm3 = solid.intersect(lid_shape).Volume()
        # what of the lid stands under the wire, straight down (the lid comes on along +Z)
        org = [(x, y, z0) for x0, x1, y0, y1, z0, _ in boxes for x in np.linspace(x0, x1, 3) for y in np.linspace(y0, y1, 3)]
        tops = _top_under(lid_m, org)
        gaps = [o[2] - t for o, t in zip(org, tops) if t is not None]
        gap = round(float(min(gaps)), 3) if gaps else None
        deepest = min(w[4] for w in boxes)
        good = (pack is None or pack >= 0.0) and lid_mm3 <= 1e-4 and (gap is None or gap >= 0.0)
        ok &= good
        rows[name] = {'ok': good, 'from': list(a), 'to': list(b), 'wire_d': WIRE_D,
                      'wire_deepest_z': round(deepest, 3),
                      'pack_face_z': round(face, 3), 'clear_of_pack_mm': pack,
                      'into_lid_mm3': round(lid_mm3, 4), 'clear_of_lid_mm': gap}
    return {'ok': bool(ok), 'routes': rows,
            'note': f'pack at BATT_T_MAX {P.BATT_T_MAX} on its floor; clear_of_pack: the wire to the face of the pack, and '
                    'clear_of_lid: to the lid straight under it (negative: into it)'}


def _top_under(mesh, pts):
    """The highest surface of mesh straight under each point (x, y, z) of pts, at or below z (None: nothing)."""
    tri = mesh.triangles
    lo, hi = tri[:, :, :2].min(1), tri[:, :, :2].max(1)
    out = []
    for x, y, z in pts:
        t = tri[(lo[:, 0] <= x) & (hi[:, 0] >= x) & (lo[:, 1] <= y) & (hi[:, 1] >= y)]
        a, b, c = t[:, 0], t[:, 1], t[:, 2]
        v0, v1, v2 = b[:, :2] - a[:, :2], c[:, :2] - a[:, :2], np.array([x, y]) - a[:, :2]
        den = v0[:, 0] * v1[:, 1] - v1[:, 0] * v0[:, 1]
        ok = np.abs(den) > 1e-12
        den = np.where(ok, den, 1.0)
        l1 = (v2[:, 0] * v1[:, 1] - v1[:, 0] * v2[:, 1]) / den
        l2 = (v0[:, 0] * v2[:, 1] - v2[:, 0] * v0[:, 1]) / den
        zs = a[:, 2] + l1 * (b[:, 2] - a[:, 2]) + l2 * (c[:, 2] - a[:, 2])
        zs = zs[ok & (l1 >= -1e-9) & (l2 >= -1e-9) & (l1 + l2 <= 1 + 1e-9) & (zs <= z + 1e-6)]
        out.append(float(zs.max()) if len(zs) else None)
    return out


def mesh_of(shape, tol=0.01):
    v, t = shape.tessellate(tol, 0.1)
    return trimesh.Trimesh([(p.x, p.y, p.z) for p in v], t, process=True)


def run(lid_m, tub_m, mid_m, lid_shape):
    """Both checks. lid_m: the lid body without its side keys (they are away from every latch and every wire), as a
    mesh; lid_shape: the same as a cq.Shape."""
    pcb_m = mesh_of(hw.solids()['PCB'])
    return {'latch_arms': latch_arms(lid_m, tub_m, mid_m, pcb_m), 'rework': rework(lid_shape, lid_m)}


def summary(r):
    la, rw = r['latch_arms'], r['rework']
    lines = [f"lid closes, latch arms bent on the way in: {'PASS' if la['ok'] else 'FAIL'} "
             f"({la['n_blocked']} of {len(la['latches'])} blocked)"]
    for k, v in la['latches'].items():
        c = v['contacts']
        lines.append(f"  {k:10s} bend {v['bend_max_mm']:.3f}, pocket at {v['barb_in_pocket_at_mm']}: "
                     + ('clear' if not c else '; '.join(f"{n} at {x['s_mm_before_home']}"
                                                           + (f" ({'flat top' if x['flat_top'] else 'chamfer'})" if 'flat_top' in x else '')
                                                           for n, x in c.items()))
                     + ('' if v['ok'] else '  FAIL'))
    lines.append(f"lid closes over the charging bodge wires ({WIRE_D} mm, on the parts under them): {'PASS' if rw['ok'] else 'FAIL'}")
    for k, v in rw['routes'].items():
        lines.append(f"  {k:26s} deepest {v['wire_deepest_z']}, to the pack {v['clear_of_pack_mm']}, "
                     f"to the lid {v['clear_of_lid_mm']}{'' if v['ok'] else '  FAIL'}")
    return '\n'.join(lines)


if __name__ == '__main__':
    import cadquery as cq
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else hw.OUT
    lid_m, tub_m, mid_m = (trimesh.load(str(out / f'{n}.stl')) for n in ('lid_body', 'tub', 'midplate'))
    lid_shape = cq.importers.importStep(str(out / 'lid.step')).val()       # the printed lid: the body and its keys
    res = run(lid_m, tub_m, mid_m, lid_shape)
    (out / 'lid-close.json').write_text(json.dumps(res, indent=1))
    print(summary(res))
    sys.exit(0 if res['latch_arms']['ok'] and res['rework']['ok'] else 1)
