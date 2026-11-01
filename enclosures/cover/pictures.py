"""The slide cover's pictures for docs/images/: renders of the real meshes (vtk, offscreen: no GUI window) and two section drawings.

    python -B pictures.py          cover-front.png, cover-back.png, cover-stop-side.png, cover-snap-corner.png, cover-coupon.png

The case is the built 4.26 standard (out/standard/: tub, lid with its side keys, bottom keys); the cover is the design-frame
STL of build_cover.py placed on the front or the back (check.mat). Nothing was printed: these show the CAD.
"""
from pathlib import Path

import matplotlib
import numpy as np
import shapely
import trimesh

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

import check as C   # noqa: E402
import model as M   # noqa: E402
import render       # noqa: E402

HERE = Path(__file__).resolve().parent
ENC = HERE.parent
IMG = ENC.parent / 'docs' / 'images'

CASE = (0.90, 0.91, 0.93)
LID = (0.80, 0.83, 0.88)
KEYS = (0.22, 0.45, 0.85)
CAPS = (0.28, 0.30, 0.34)
COVER = (0.98, 0.58, 0.20)


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


def sec_polys(m, z):
    s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    return [] if s is None else s.discrete


def snap_figure(s, cov, path):
    """The top-left corner at home, seen from the screen side, cut at z = zm (through the ridge): case (blue), cover (orange), and
    the deflection the prong makes along the slide (from the real end faces)."""
    import check
    case = trimesh.util.concatenate([trimesh.load(ENC / 'case-426' / 'out' / 'standard' / f'{n}.stl', force='mesh')
                                     for n in ('tub', 'lid')])
    home = -s['cx']
    z = s['zm'] + 0.1
    cv = posed(cov, s, home, False)
    fig, axs = plt.subplots(1, 2, figsize=(15, 6.4), gridspec_kw={'width_ratios': [1.25, 1]})
    ax = axs[0]
    for pl in sec_polys(cv, z):
        ax.fill(pl[:, 0], pl[:, 1], color=(0.98, 0.58, 0.20), alpha=0.85, lw=0.8, ec=(0.5, 0.25, 0.0))
    for pl in sec_polys(case, z):
        ax.fill(pl[:, 0], pl[:, 1], color=(0.55, 0.65, 0.90), alpha=0.55, lw=0.8, ec=(0.1, 0.2, 0.5))
    ax.set_xlim(-8, 22)
    ax.set_ylim(105, 118.5)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    ax.set_title('Top-left corner, cover on the front at home, cut through the ridge (z %.1f)\n'
                 'blue: case (R5 corner arc); orange: the cover\'s wall, the prong (0.8) and its ridge' % z, fontsize=10)
    ax.set_xlabel('case x (mm)')
    ax.set_ylabel('case y (mm)')
    ax.annotate('ridge flat top\nrests on the R5 arc at home', xy=(-1.2, 114.85), xytext=(-7.5, 108.5), fontsize=9,
                arrowprops=dict(arrowstyle='->'))
    ax.annotate('prong root (wall 1.6)', xy=(s['u_root'] - s['cx'], 116.8), xytext=(11, 108.2), fontsize=9,
                arrowprops=dict(arrowstyle='->'))
    ax.annotate('end face', xy=(14, 115.6), xytext=(15, 111), fontsize=9, arrowprops=dict(arrowstyle='->'))
    cm = check.Case('case-426', 'standard')
    maps = check.end_maps(cm, s)
    sh = np.arange(-s['cx'], 78.0, 0.25)
    d0 = check.deflection_path(s, maps, sh, False, 'top', 0.0)
    ax = axs[1]
    ax.plot(sh, d0, lw=2, color=(0.85, 0.35, 0.0))
    ax.axhline(s['d_eng'], color='gray', ls=':')
    ax.set_xlabel('cover shift s along x (mm); home at the left, off the case at the right')
    ax.set_ylabel('prong deflection needed (mm)')
    ax.set_title('Deflection of the top prong along the slide\n(ray casts on the real 4.26 end face, J6 opening included)', fontsize=10)
    ax.set_ylim(-0.05, 0.95)
    ax.grid(True, alpha=0.3)
    ax.annotate('home: preload %.2f' % d0[0], xy=(0, d0[0]), xytext=(8, 0.15), fontsize=9, arrowprops=dict(arrowstyle='->'))
    ax.annotate('flat end face, J6 opening\n(no dip: the ridge stays on the wall above it)', xy=(36, 0.7), xytext=(24, 0.45), fontsize=9,
                arrowprops=dict(arrowstyle='->'))
    ax.annotate('over the right corner arc\n(the ramp the cover goes on by)', xy=(66, 0.35), xytext=(44, 0.1), fontsize=9,
                arrowprops=dict(arrowstyle='->'))
    plt.tight_layout()
    plt.savefig(path, dpi=100)
    plt.close(fig)


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    s = M.spec('keyed')
    cov = trimesh.load(HERE / 'out' / 'design' / 'keyed.stl', force='mesh')
    home = -s['cx']
    parts = case_parts()
    c = np.array([30.0, 52.0, 0.0])
    # the cover going on from the right (front): 38 mm short of home, so the case and the open end show
    f = posed(cov, s, home + 38.0, False)
    render.render(parts + [(f, COVER, 1.0)], IMG / 'cover-front.png', position=(c[0] + 120, c[1] - 175, 150), focal=c,
                  up=(0, 0, 1), size=(1500, 1000))
    b = posed(cov, s, home + 38.0, True)
    render.render(parts + [(b, COVER, 1.0)], IMG / 'cover-back.png', position=(c[0] - 175, c[1] - 255, -205), focal=c,
                  up=(0, 0, 1), size=(1500, 1000))
    # the stop side and its gaps: cover home on the back, the stop wall on the left; look at the left side from outside
    bh = posed(cov, s, home, True)
    f2 = np.array([-4.0, 68.0, -3.0])
    render.render(parts + [(bh, COVER, 1.0)], IMG / 'cover-stop-side.png', position=(f2[0] - 100, f2[1] - 40, f2[2] - 55),
                  focal=f2, up=(0, 0, 1), size=(1500, 1000), view_angle=32)
    snap_figure(s, cov, IMG / 'cover-snap-corner.png')
    # the coupons as printed (plate down): A, B, C side by side, from above at an angle
    ms = []
    for i, k in enumerate('ABC'):
        m = trimesh.load(ENC.parent / 'print' / 'cover' / '4.26' / f'cover-coupon-{k}.stl', force='mesh')
        m.apply_translation((i * 38.0, 0, 0))
        ms.append((m, COVER, 1.0))
    ctr = np.array([53.0, 9.0, 6.0])
    render.render(ms, IMG / 'cover-coupon.png', position=(ctr[0] + 22, ctr[1] - 120, 95), focal=ctr, up=(0, 0, 1),
                  size=(1500, 760), view_angle=28)
    print('pictures in', IMG)


if __name__ == '__main__':
    main()
