"""The slide cover's pictures for docs/images/: renders of the real meshes (vtk, offscreen: no GUI window).

    python -B pictures.py          cover-front.png, cover-back.png, cover-stop-side.png, cover-snap-corner.png, cover-coupon.png

The case is the built 4.26 standard (out/standard/: tub, lid with its side keys, bottom keys); the cover is the design-frame
STL of build_cover.py placed on the front or the back at home (check.mat). Nothing printed: these show the CAD.
"""
import sys
from pathlib import Path

import manifold3d as m3d
import numpy as np
import trimesh

import check as C
import model as M
import render

HERE = Path(__file__).resolve().parent
ENC = HERE.parent
IMG = ENC.parent / 'docs' / 'images'

CASE = (0.86, 0.87, 0.89)
LID = (0.80, 0.82, 0.86)
KEYS = (0.25, 0.45, 0.80)
CAPS = (0.30, 0.32, 0.36)
COVER = (0.95, 0.55, 0.25)


def posed(tm, s, shift, flip):
    m = C.mat(s, shift, flip)
    v = (m[:3, :3] @ np.asarray(tm.vertices).T).T + m[:3, 3]
    return trimesh.Trimesh(v, tm.faces, process=False)


def case_parts(slug='standard'):
    d = ENC / 'case-426' / 'out' / slug
    out = [(trimesh.load(d / 'tub.stl', force='mesh'), CASE, 1.0), (trimesh.load(d / 'lid.stl', force='mesh'), LID, 1.0)]
    for k in sorted(d.glob('key_SW*.stl')):
        out.append((trimesh.load(k, force='mesh'), CAPS, 1.0))
    for k in sorted(d.glob('skey_*.stl')):
        out.append((trimesh.load(k, force='mesh'), KEYS, 1.0))
    return out


def cut(tm, normal, offset, keep='below'):
    """The part of a mesh on one side of a plane (manifold3d), for section views."""
    man = C.to_man(tm)
    n = np.array(normal, dtype=float)
    r = man.trim_by_plane(tuple(-n if keep == 'below' else n), -offset if keep == 'below' else offset)
    me = r.to_mesh()
    return trimesh.Trimesh(np.asarray(me.vert_properties)[:, :3], np.asarray(me.tri_verts), process=False)


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    s = M.spec('keyed')
    cov = trimesh.load(HERE / 'out' / 'design' / 'keyed.stl', force='mesh')
    home = -s['cx'] + 0.0
    parts = case_parts()
    # front: the cover on the front, a little drawn off to the right so the open end shows; view from the screen side
    c = np.array([30.0, 50.0, 0.0])
    f = posed(cov, s, home, False)
    render.render(parts + [(f, COVER, 1.0)], IMG / 'cover-front.png', position=(c[0] - 150, c[1] - 150, 170), focal=c,
                  up=(0, 0, 1), size=(1500, 1000))
    b = posed(cov, s, home, True)
    render.render(parts + [(b, COVER, 1.0)], IMG / 'cover-back.png', position=(c[0] + 150, c[1] - 150, -170), focal=c,
                  up=(0, 0, 1), size=(1500, 1000))
    # the stop side, with its key gaps: cover on the back, the stop wall on the left; look at the left side from outside
    f2 = (np.array([-4.0, 68.0, -3.5]))
    render.render(parts + [(b, COVER, 1.0)], IMG / 'cover-stop-side.png', position=(f2[0] - 95, f2[1] - 30, f2[2] - 30),
                  focal=f2, up=(0, 0, 1), size=(1500, 1000))
    # the snap corner at home: the top-left corner on the front, the cover cut at z = 0.2 (above removed) seen from above
    top = {'cover': cut(f, (0, 0, 1), 0.2, 'below')}
    case_cut = [(cut(m, (0, 0, 1), 0.2, 'below'), col, op) for m, col, op in parts[:2]]
    corner = np.array([-1.0, 111.0, 0.0])
    render.render(case_cut + [(top['cover'], COVER, 1.0)], IMG / 'cover-snap-corner.png',
                  position=(corner[0] - 18, corner[1] - 30, 62), focal=corner, up=(0, 1, 0), size=(1500, 1000), view_angle=22)
    # the coupons: A, B, C side by side from the inside, and A from outside
    from build_cover import coupon_body, label, stl
    ms = []
    for i, k in enumerate('ABC'):
        sc, cb = coupon_body('keyed', k)
        cb = label(sc, k, cb)
        tmp = HERE / 'out' / 'design' / f'coupon-view-{k}.stl'
        stl(cb, tmp)
        m = trimesh.load(tmp, force='mesh')
        m.apply_translation((i * 40.0, 0, 0))
        ms.append((m, COVER, 1.0))
    ctr = np.array([40.0, 108.0, 0.0])
    render.render(ms, IMG / 'cover-coupon.png', position=(ctr[0] - 20, ctr[1] - 95, -75), focal=ctr, up=(0, 0, 1),
                  size=(1500, 900), view_angle=30)
    print('pictures in', IMG)


if __name__ == '__main__':
    main()
