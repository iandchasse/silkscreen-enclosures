"""The slide cover's pictures for docs/images/: renders of the real meshes (vtk, offscreen: no GUI window) and one section drawing.

    python -B pictures.py          cover-front.png, cover-back.png, cover-poses.png, cover-turned.png, cover-scallop.png,
                                   cover-open-end.png (old next to new), cover-logo.png, cover-snap-corner.png

The case is the built 4.26 standard (out/standard/: tub, lid with its side keys, bottom keys); the cover is the design-frame STL of
build_cover.py placed in one of its four poses (check.mat). cover-open-end.png sets 27bbdaf's cover (coupon A's geometry, ref/old-27bbdaf-
keyed.stl) beside this one. Nothing was printed: these show the CAD.
"""
from pathlib import Path

import matplotlib
import numpy as np
import trimesh
from PIL import Image, ImageDraw

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

import check as C   # noqa: E402
import model as M   # noqa: E402
import render       # noqa: E402

HERE = Path(__file__).resolve().parent
ENC = HERE.parent
IMG = ENC.parent / 'docs' / 'images'
TMP = HERE / 'out' / 'pics'

CASE = (0.90, 0.91, 0.93)
LID = (0.80, 0.83, 0.88)
KEYS = (0.22, 0.45, 0.85)
CAPS = (0.28, 0.30, 0.34)
COVER = (0.98, 0.58, 0.20)
OLD = (0.62, 0.64, 0.68)
INK = (0.10, 0.12, 0.35)


def posed(tm, s, shift, flip, turn=False):
    m = C.mat(s, shift, flip, turn)
    v = (m[:3, :3] @ np.asarray(tm.vertices).T).T + m[:3, 3]
    return trimesh.Trimesh(v, tm.faces, process=False)


def case_parts(slug='standard'):
    d = ENC / 'case-426' / 'out' / slug
    out = [(trimesh.load(d / 'tub.stl', force='mesh'), CASE, 1.0), (trimesh.load(d / 'lid.stl', force='mesh'), LID, 1.0)]
    for k in sorted(d.glob('key_SW*.stl')):
        out.append((trimesh.load(k, force='mesh'), CAPS, 1.0))
    return out


def sec_polys(m, z):
    s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    return [] if s is None else s.discrete


def label(path, text):
    im = Image.open(path).convert('RGB')
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, im.width, 34], fill=(255, 255, 255))
    d.text((10, 10), text, fill=(20, 20, 20))
    im.save(path)


def montage(paths, out, cols):
    ims = [Image.open(p).convert('RGB') for p in paths]
    w, h = ims[0].size
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new('RGB', (w * cols, h * rows), (255, 255, 255))
    for i, im in enumerate(ims):
        sheet.paste(im, ((i % cols) * w, (i // cols) * h))
    sheet.save(out)


def snap_figure(s, cov, path):
    """The top-left corner at home, seen from the screen side, cut at z = zm (through the ridge): case (blue), cover (orange), and
    the deflection the prong makes along the slide (from the real end faces)."""
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
    cm = C.Case('case-426', 'standard')
    maps = C.end_maps(cm, s)
    sh = np.arange(-s['cx'], 78.0, 0.25)
    d0 = C.deflection_path(s, maps, sh, False, False, 'top', 0.0, C.ridge_samples_mesh(cov, s))
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


PHASE1 = 'f45db64'          # the commit with phase 1's covers (print/cover/4.26/cover-keyed.stl): the 'old' of the A4-A6 pictures


def phase1_keyed():
    import io
    import subprocess
    raw = subprocess.run(['git', 'show', f'{PHASE1}:print/cover/4.26/cover-keyed.stl'], capture_output=True, cwd=ENC.parent, check=True).stdout
    return trimesh.load(io.BytesIO(raw), file_type='stl', force='mesh')


def corner_compare(path):
    """Phase 1's open-end corner (the top prong, y = 128, x = 66 to 72 in the print frame) next to the new one, three views each: the outer face
    (from below the bed), the side (along y), the case side (from above)."""
    old = phase1_keyed()
    new = trimesh.load(ENC.parent / 'print' / 'cover' / '4.26' / 'cover-keyed.stl', force='mesh')
    c = np.array([60.0, 122.0, 6.0])
    views = {'the outer face': ((c[0], c[1] - 14, -110), (c[0], c[1], c[2]), (0, 1, 0)),
             'the side': ((c[0] + 4, c[1] + 110, c[2] + 6), (c[0] + 4, c[1], c[2] + 4), (0, 0, 1)),
             'the case side': ((c[0], c[1] - 14, 120), (c[0], c[1], c[2]), (0, 1, 0))}
    cells = []
    for k, (vn, (pos, foc, up)) in enumerate(views.items()):
        for j, (nm, mesh, col) in enumerate((('phase 1', old, OLD), ('phase 2', new, COVER))):
            f = TMP / f'corner-{k}-{j}.png'
            render.render([(mesh, col, 1.0)], f, position=pos, focal=foc, up=up, size=(800, 760), view_angle=22)
            label(f, f'{nm}: {vn}')
            cells.append(f)
    montage([cells[i] for i in (0, 1, 2, 3, 4, 5)], path, 2)


def outer_face(path):
    """The whole outer face as it prints (seen from below the bed), the two border lines, the logo and the wordmark."""
    new = trimesh.load(ENC.parent / 'print' / 'cover' / '4.26' / 'cover-keyed.stl', force='mesh')
    c = np.array(new.bounds).mean(axis=0)
    render.render([(new, COVER, 1.0)], path, position=(c[0] + 6, c[1] - 40, -330), focal=c, up=(0, 1, 0), size=(1100, 1300), view_angle=26)


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    s = M.spec('keyed')
    cov = trimesh.load(HERE / 'out' / 'design' / 'keyed.stl', force='mesh')
    old = trimesh.load(HERE / 'ref' / 'old-27bbdaf-keyed.stl', force='mesh')
    home = -s['cx']
    parts = case_parts()
    side = [(trimesh.load(f, force='mesh'), KEYS, 1.0) for f in sorted((ENC / 'case-426' / 'out' / 'standard').glob('skey_*.stl'))]
    c = np.array([30.0, 52.0, 0.0])
    # front and back at home: straight down on the screen, and straight up at the back (the case turned over about its long axis)
    f = posed(cov, s, home, False)
    render.render(parts + side + [(f, COVER, 1.0)], IMG / 'cover-front.png', position=(c[0], c[1] - 60, 330), focal=c, up=(0, 1, 0),
                  size=(1100, 1300), view_angle=26)
    b = posed(cov, s, home, True)
    render.render(parts + side + [(b, COVER, 1.0)], IMG / 'cover-back.png', position=(c[0], c[1] - 60, -330), focal=c, up=(0, 1, 0),
                  size=(1100, 1300), view_angle=26)
    # the four poses at home, one sheet
    names = {'front': 'FRONT, stop on the right', 'back': 'BACK, stop on the left', 'front-turned': 'FRONT turned 180 degrees in the plane (logo upside down)',
             'back-turned': 'BACK turned 180 degrees in the plane (logo upside down)'}
    paths = []
    for pose, (flip, turn) in C.POSES.items():
        p = TMP / f'pose-{pose}.png'
        m = posed(cov, s, home, flip, turn)
        z = -330 if flip else 330
        render.render(parts + side + [(m, COVER, 1.0)], p, position=(c[0], c[1] - 40, z), focal=c, up=(0, 1, 0), size=(700, 860), view_angle=26)
        label(p, names[pose])
        paths.append(p)
    montage(paths, IMG / 'cover-poses.png', 4)
    # a turned pose, part way on: the front, turned, coming from the left
    t = posed(cov, s, home + 40.0, False, True)
    render.render(parts + side + [(t, COVER, 1.0)], IMG / 'cover-turned.png', position=(c[0] - 60, c[1] - 175, 150), focal=c + np.array([-8, 0, 0]),
                  up=(0, 0, 1), size=(1500, 1000))
    # the scallop with a key on the back: the cover on the back at home, the right side (the three pads SW1, SW4, SW10) and a fingertip
    sc = posed(cov, s, home, True)
    tip = trimesh.creation.icosphere(subdivisions=4, radius=C.FINGER_R)
    pads = C.case_info.info('case-426', 'standard')['pads']
    sd, y0, y1, z0, z1, xf = pads['SW4']
    tip.apply_translation((xf + sd * C.FINGER_R, (y0 + y1) / 2, (z0 + z1) / 2))
    fc = np.array([64.0, 80.0, -3.0])
    render.render(parts + side + [(sc, COVER, 1.0), (tip, (0.35, 0.8, 0.45), 0.55)], IMG / 'cover-scallop.png',
                  position=(fc[0] + 95, fc[1] - 20, fc[2] - 75), focal=fc, up=(0, 0, 1), size=(1500, 1000), view_angle=34)
    # the open end corner, phase 1 next to phase 2, from the outer face, the side and the case side (the print frame: the outer face on the bed)
    corner_compare(IMG / 'cover-open-end.png')
    outer_face(IMG / 'cover-face.png')
    # the logo face, as printed: the outer face on the bed, seen from below the bed, with the two inlay bodies (the two-colour switch on)
    pf = trimesh.load(ENC.parent / 'print' / 'cover' / '4.26' / 'cover-keyed.stl', force='mesh')
    inl = [(trimesh.load(ENC.parent / 'print' / 'cover' / '4.26' / f'cover-keyed-inlay-{n}.stl', force='mesh'), INK, 1.0) for n in ('wordmark', 'icon')]
    pc = np.array(pf.bounds).mean(axis=0)
    render.render([(pf, COVER, 1.0)] + inl, IMG / 'cover-logo.png', position=(pc[0], pc[1] - 25, -300), focal=pc, up=(0, 1, 0),
                  size=(1100, 1300), view_angle=26)
    snap_figure(s, cov, IMG / 'cover-snap-corner.png')
    print('pictures in', IMG)


if __name__ == '__main__':
    main()
