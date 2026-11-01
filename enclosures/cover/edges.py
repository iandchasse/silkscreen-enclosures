"""Sharp-edge check: every convex mesh edge of a cover STL that turns more than ANGLE degrees, grouped by place, and whether a hand can
touch it.

    python -B edges.py [group] [stl]       default: the keyed cover as built (out/design/keyed.stl); `old` reads 27bbdaf's print STL

A convex edge turns more than 50 degrees where two faces meet at more than 50 degrees on the outside (a 90-degree box edge turns 90; a
fillet tessellated at the build's 0.1 rad angular tolerance turns 5.7 degrees per facet). trimesh gives the adjacency, the angle and the
convexity of every shared edge.

TOUCHABLE: the edge's two face normals are traced out from it (0.15 mm off, 100 mm long, vtk ray casts against the cover and the case at
home): if either escapes, a hand or a pocket can reach that edge. An edge both of whose faces look into the case (the ridge's tip, the
plate's inner face, the lip's case side, a prong's inner face) is listed as case-facing and justified, not counted as touchable. The
logo's engraving rims (the case's own back logos, 0.4 and 0.2 deep, strokes down to 0.36 wide) are a third class: they are the case's
own treatment of the same logos, and a stroke that thin cannot take a fillet.
"""
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import shapely
import trimesh
from scipy.spatial import cKDTree

import model as M
import raycast

HERE = Path(__file__).resolve().parent
ENC = HERE.parent
ANGLE = 50.0
SLIVER_H = 0.01          # mm: a triangle thinner than this is a tessellation sliver
FAN_LEN = 0.06           # mm: a cluster of flagged edges averaging under this is the mesher's fan of tiny facets at a fillet seam, not a feature
KNIFE = 120.0            # degrees: a convex turn beyond this next to a sliver is the mesher's fold
FLAG_STATS = {}


def flagged(mesh, angle=ANGLE):
    """-> dict of arrays for the convex edges turning more than `angle`: mid (n, 3), turn (deg), normals (n, 2, 3), length."""
    adj = mesh.face_adjacency
    ang = np.degrees(mesh.face_adjacency_angles)
    conv = mesh.face_adjacency_convex
    # zero-width slivers: triangles the mesher leaves at a fillet's seam (height under 10 microns, areas down to 1e-8 mm2; their folds read as
    # turns of 150 to 180 degrees). They are tessellation, not geometry (the B-rep's fillet there is tangent), so they are counted apart.
    tri = mesh.triangles
    longest = np.max(np.stack([np.linalg.norm(tri[:, i] - tri[:, (i + 1) % 3], axis=1) for i in range(3)]), axis=0)
    height = 2.0 * mesh.area_faces / np.maximum(longest, 1e-12)
    sliver = np.minimum(height[adj[:, 0]], height[adj[:, 1]]) < SLIVER_H
    fold = sliver & (ang > KNIFE)           # a sliver whose fold reads as a knife edge: its normal is noise, the edge is not geometry
    FLAG_STATS['slivers'] = int((conv & (ang > angle) & fold).sum())
    sel = conv & (ang > angle) & ~fold
    e = mesh.face_adjacency_edges[sel]
    v = mesh.vertices
    a, b = v[e[:, 0]], v[e[:, 1]]
    return dict(mid=(a + b) / 2, turn=ang[sel], normals=np.stack([mesh.face_normals[adj[sel][:, 0]], mesh.face_normals[adj[sel][:, 1]]], axis=1),
                length=np.linalg.norm(a - b, axis=1))


def classify(f, caster):
    """Per edge: True where a normal escapes (touchable)."""
    out = np.zeros(len(f['mid']), dtype=bool)
    for i, (m, ns) in enumerate(zip(f['mid'], f['normals'])):
        for n in ns:
            p0 = m + 0.15 * n
            if caster.first_hit(p0, p0 + 100.0 * n) is None:
                out[i] = True
                break
    return out


def clusters(mid, eps=1.6):
    n = len(mid)
    if not n:
        return np.zeros(0, dtype=int)
    tree = cKDTree(mid)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b in tree.query_pairs(eps):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    roots = np.array([find(i) for i in range(n)])
    _, lab = np.unique(roots, return_inverse=True)
    return lab


def place(c, s, logo_zone):
    """A name for where a cluster of edges is (design frame)."""
    (x0, y0, z0), (x1, y1, z1) = c.min(axis=0), c.max(axis=0)
    zc = (z0 + z1) / 2
    xc, yc = (x0 + x1) / 2, (y0 + y1) / 2
    if logo_zone is not None and z1 > s['z_o'] - 0.6 and z0 > s['z_o'] - 0.6 and shapely.contains_xy(logo_zone, c[:, 0], c[:, 1]).mean() > 0.6:
        return 'logo engraving rim'
    if z0 > s['z_o'] - s['bed_chamfer'] - 0.3 and z1 > s['z_o'] - 0.05:
        return 'bed-face perimeter'
    if abs(zc - s['z_i']) < 0.8 or (z0 > s['z_i'] - 0.8 and z1 < s['z_i'] + s['tp'] - 0.5):
        return 'plate edge or cutout'
    near_end = min(abs(yc - s['yw_t']), abs(yc - s['yw_b'])) < 3.5
    if x1 < s['u_root'] + 0.5 and near_end and zc < s['z_i'] - 0.5:
        return 'prong, ridge'
    if zc < s['z_i'] - 0.5:
        return 'wall, lip, corner piece'
    return 'other'


def report(mesh, s, case_mesh=None, verbose=True, label=''):
    f = flagged(mesh)
    n = len(f['mid'])
    comb = mesh if case_mesh is None else trimesh.util.concatenate([mesh, case_mesh])
    caster = raycast.Caster(comb)
    touch = classify(f, caster) if n else np.zeros(0, dtype=bool)
    lg = None
    try:
        from model import logo_polys
        lg = shapely.unary_union([p.buffer(0.3) for p, _ in logo_polys(s).values()])
    except Exception:
        pass
    lab = clusters(f['mid'])
    rows = []
    for k in range(lab.max() + 1 if n else 0):
        idx = lab == k
        c = f['mid'][idx]
        name = place(c, s, lg)
        if f['length'][idx].mean() < FAN_LEN and name != 'logo engraving rim':
            name = 'mesher fan at a fillet seam (facets under 0.06 mm)'
        rows.append(dict(place=name, n=int(idx.sum()), touchable=int(touch[idx].sum()), max_turn=float(f['turn'][idx].max()),
                         length=float(f['length'][idx].sum()), box=[round(float(v), 1) for v in (*c.min(axis=0), *c.max(axis=0))]))
    agg = {}
    for r in rows:
        a = agg.setdefault(r['place'], dict(groups=0, edges=0, touchable=0, length=0.0, max_turn=0.0))
        a['groups'] += 1
        a['edges'] += r['n']
        a['touchable'] += r['touchable']
        a['length'] += r['length']
        a['max_turn'] = max(a['max_turn'], r['max_turn'])
    if verbose:
        print(f'{label} {n} convex edge segments turn more than {ANGLE:.0f} degrees, {int(touch.sum())} of them touchable'
              f' (plus {FLAG_STATS.get("slivers", 0)} knife folds of zero-width mesher slivers, not counted)')
        for k, a in sorted(agg.items()):
            print(f'   {k:26s} {a["edges"]:6d} segments in {a["groups"]:3d} groups, {a["touchable"]:6d} touchable, {a["length"]:8.1f} mm of edge, up to {a["max_turn"]:.0f} degrees')
    return dict(total=n, touchable=int(touch.sum()), places=agg, groups=rows)


def case_mesh_for(s):
    """The case at home in the design frame (the cover's u = case x + cx)."""
    d = ENC / s_case_dir(s)
    ms = [trimesh.load(d / f'{n}.stl', force='mesh') for n in ('tub', 'lid')]
    m = trimesh.util.concatenate(ms)
    m.apply_translation((s['cx'], 0, 0))
    return m


def s_case_dir(s):
    return Path(('case-426' if s['group'] != 'x3' else 'case-368') + '/out/' + s['case_slug'])


def old_cover_mesh():
    """27bbdaf's keyed cover in its design frame (ref/old-27bbdaf-keyed.stl: the design STL that build made, kept before round 2's rebuild;
    `git show 27bbdaf:enclosures/cover/model.py` and build_cover.py rebuild it)."""
    return trimesh.load(HERE / 'ref' / 'old-27bbdaf-keyed.stl', force='mesh')


if __name__ == '__main__':
    grp = sys.argv[1] if len(sys.argv) > 1 else 'keyed'
    if grp == 'old':
        s = M.spec('keyed')
        report(old_cover_mesh(), s, case_mesh_for(s), label='27bbdaf cover (design frame)')
    else:
        s = M.spec(grp)
        path = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / 'out' / 'design' / f'{grp}.stl'
        m = trimesh.load(path, force='mesh')
        report(m, s, case_mesh_for(s), label=f'{grp} ({path.name})')
