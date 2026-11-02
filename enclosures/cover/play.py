"""The cover's effective play at home, on the real STLs (2026-11-01, Ian: the fit is not quite there, the vertical room a tiny bit more strict).

    python -B play.py [--axis y|z] [--groups keyed,chinless,x3] [--cy 0.2,0.15] [--layered] [--where]

At home (the stop 0.01 off the side) the rigid frame (the cover without its ridge) is moved along one axis of the case's frame until it first touches the case,
both ways. The prongs are springs, so what the cover can do rigidly is what these numbers are; the sum of the two ways is the travel (the rattle).

  --axis y (default): along the case's long axis (top to bottom, Ian's "vertical"): the channel walls against the end faces, the corner pieces against the corner
      arcs, the lips against the rounds. Measured for the whole frame and for each end alone (the stop end = the half with the corner pieces, the open end
      = the half with the tabs), in all four poses. --cy builds covers with another channel clearance (per side) to measure them too. --where names the
      place of the first touch (the centre of the overlap, case frame).
  --axis z: front to back: the plate against the face and the lip against the back round (the 'plate_gap' / 'lip_gap'). --layered replaces the lip and
      the walls below the plate by what a 0.2 mm slicer lays (each layer the mesh's section at its mid-plane, extruded 0.2), the as-printed figure.
"""
import argparse
import os
import tempfile
from pathlib import Path

import numpy as np
import shapely
import trimesh

import check as C
import model as M

HERE = Path(__file__).resolve().parent
DESIGN = HERE / 'out' / 'design'
CASES = {'keyed': ('case-426', 'standard'), 'chinless': ('case-426', 'chinless'), 'x3': ('case-368', 'standard')}
EPS = 0.02              # mm3 of overlap that counts as a touch (float32 noise is below it)


def layered(mesh, s):
    """The cover as a 0.2 slicer lays it, below the plate: a manifold. The plate (z >= z_i) keeps its true shape (its faces are flat, on the layers)."""
    ext = np.array(mesh.bounds)
    zo, zi = s['z_o'], s['z_i']
    k = int(np.ceil((zo - ext[0][2]) / 0.2))
    parts = []
    for i in range(int(round(s['tp'] / 0.2)), k + 1):            # layers below the plate: [zo - 0.2 (i + 1), zo - 0.2 i]
        zm = zo - 0.2 * i - 0.1
        sec = mesh.section(plane_origin=[0, 0, zm], plane_normal=[0, 0, 1])
        if sec is None:
            continue
        g = shapely.Polygon()
        for p in sec.discrete:
            g = g.symmetric_difference(shapely.Polygon(p[:, :2]).buffer(0))
        if g.is_empty:
            continue
        parts.append(C.prism(g, zo - 0.2 * (i + 1), zo - 0.2 * i))
    low = parts[0]
    for q in parts[1:]:
        low = low + q
    top = C.to_man(mesh) ^ C.box_man(ext[0][0] - 1, ext[1][0] + 1, ext[0][1] - 1, ext[1][1] + 1, zi, zo + 1)
    return low + top


def first_touch(cm, man, s, axis, sign, pose=(False, False), hi=1.0, steps=16, home=None):
    """The distance (mm) the cover can move along `axis` ('y' or 'z', sign +1 / -1) before it touches the case at home (bisection on the overlap volume);
    None if it is still clear at `hi`."""
    home = -s['cx'] + 0.01 if home is None else home
    flip, turn = pose

    def ov(d):
        m = C.mat(s, home, flip, turn, dy=sign * d if axis == 'y' else 0.0, dz=sign * d if axis == 'z' else 0.0)
        return cm.overlap(man, m)

    if ov(hi) < EPS:
        return None
    lo = 0.0
    top = hi
    for _ in range(steps):
        mid = (lo + top) / 2
        if ov(mid) < EPS:
            lo = mid
        else:
            top = mid
    return lo


def where(cm, man, s, axis, sign, d, pose):
    """Where the overlap is, just past the first touch (case frame): its centre and the extents."""
    flip, turn = pose
    home = -s['cx'] + 0.01
    m = C.mat(s, home, flip, turn, dy=sign * (d + 0.02) if axis == 'y' else 0.0, dz=sign * (d + 0.02) if axis == 'z' else 0.0)
    inter = C.apply(man, m) ^ cm.union
    mesh = inter.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3]
    if not len(v):
        return None
    return v.mean(axis=0), v.min(axis=0), v.max(axis=0)


def build_frame(s):
    import cadquery as cq
    fd, path = tempfile.mkstemp(suffix='.stl')
    os.close(fd)
    cq.exporters.export(M.build(s, ridge_on=False), path, tolerance=0.02, angularTolerance=0.1)
    mesh = trimesh.load(path, force='mesh')
    os.unlink(path)
    return mesh


def frame_mesh(group, s, over):
    return trimesh.load(DESIGN / f'{group}-frame.stl', force='mesh') if not over else build_frame(s)


def travel_z(group, G=None, use_layers=False, **over):
    over = dict(over)
    if G is not None:
        over['G'] = G
    s = M.spec(group, **over)
    case, slug = CASES[group]
    cm = C.Case(case, slug)
    mesh = frame_mesh(group, s, over)
    man = layered(mesh, s) if use_layers else C.to_man(mesh)
    toward = first_touch(cm, man, s, 'z', -1.0)       # the cover toward the case: the plate on the face
    away = first_touch(cm, man, s, 'z', +1.0)         # the cover away from the case: the lip on the back
    return dict(group=group, G=s['G'], plate_gap=toward, lip_gap=away, travel=(toward or 0) + (away or 0), nominal_gp=s['gp'], nominal_gl=s['gl'])


def travel_y(group, show_where=False, **over):
    """{pose: {part: (gap +Y, gap -Y)}} for the whole frame, its open-end half and its stop-end half."""
    s = M.spec(group, **over)
    case, slug = CASES[group]
    cm = C.Case(case, slug)
    mesh = frame_mesh(group, s, over)
    man = C.to_man(mesh)
    umid = s['xc'] + s['cx'] - 0.01                       # the cover's middle in its own u at home (case x = u - cx + 0.01)
    ext = np.array(mesh.bounds)
    parts = {'whole': man,
             'open end': man ^ C.box_man(ext[0][0] - 1, umid, ext[0][1] - 1, ext[1][1] + 1, ext[0][2] - 1, ext[1][2] + 1),
             'stop end': man ^ C.box_man(umid, ext[1][0] + 1, ext[0][1] - 1, ext[1][1] + 1, ext[0][2] - 1, ext[1][2] + 1)}
    out = {}
    for pose, pv in C.POSES.items():
        out[pose] = {}
        for name, pm in parts.items():
            up = first_touch(cm, pm, s, 'y', +1.0, pv)
            dn = first_touch(cm, pm, s, 'y', -1.0, pv)
            w = None
            if show_where and name != 'whole':
                w = (where(cm, pm, s, 'y', +1.0, up, pv) if up is not None else None, where(cm, pm, s, 'y', -1.0, dn, pv) if dn is not None else None)
            out[pose][name] = (up, dn, w)
    return s, out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--axis', default='y')
    ap.add_argument('--groups', default='keyed,chinless,x3')
    ap.add_argument('--G', default=None, help='z: comma list of total plays to build and measure (default: the design as built)')
    ap.add_argument('--var', default=None, help='y: variants to build and measure, separated by /, each as name=value,name=value (e.g. cy=0.2,corner_clr=0.14/cy=0.25); default: the design as built')
    ap.add_argument('--layered', action='store_true')
    ap.add_argument('--gn', type=float, default=None)
    ap.add_argument('--where', action='store_true')
    ap.add_argument('--poses', default=None)
    a = ap.parse_args()
    for g in a.groups.split(','):
        if a.axis == 'z':
            for G in ([None] if a.G is None else [float(x) for x in a.G.split(',')]):
                r = travel_z(g, G, a.layered, **({'gn': a.gn} if a.gn is not None else {}))
                print(f"{g:9s} G {r['G']:.3f}{' layered' if a.layered else ''}: toward the case (plate on the face) {r['plate_gap']:.3f} mm "
                      f"(drawn {r['nominal_gp']:.3f}), away (lip on the back) {r['lip_gap']:.3f} mm (drawn {r['nominal_gl']:.3f}); travel {r['travel']:.3f} mm", flush=True)
        else:
            for var in ([None] if a.var is None else a.var.split('/')):
                ov = {} if var is None else {k: float(v) for k, v in (kv.split('=') for kv in var.split(','))}
                s, res = travel_y(g, a.where, **ov)
                print(f"{g:9s} cy {s['cy']:.3f} corner_clr {s['corner_clr']:.3f} (drawn): first touch along Y (+Y / -Y, travel = sum), mm", flush=True)
                for pose, d in res.items():
                    cells = []
                    for name, (up, dn, w) in d.items():
                        f = lambda v: 'clear' if v is None else f'{v:.3f}'
                        tot = '' if up is None or dn is None else f' = {up + dn:.3f}'
                        cells.append(f'{name}: {f(up)} / {f(dn)}{tot}')
                    print(f'   {pose:13s} ' + ';  '.join(cells), flush=True)
                    if a.where:
                        for name, (up, dn, w) in d.items():
                            if w is not None:
                                for lab, wv in zip(('+Y', '-Y'), w):
                                    if wv is not None:
                                        c, lo, hi = wv
                                        print(f'      {name} {lab} touches at x {c[0]:.1f} y {c[1]:.2f} z {c[2]:.2f} (extent x {lo[0]:.1f}..{hi[0]:.1f}, z {lo[2]:.1f}..{hi[2]:.1f})', flush=True)
