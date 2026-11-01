"""Build the slide covers and the fit coupons.

    python -B build_cover.py            every cover and coupon: print/cover/4.26/cover-*.stl/.step, print/cover/3.68/cover-*.stl/.step
                                         (the print frame: plate face down), and cover/out/design/*.stl (the design frame the
                                         checks use: the cover on the case, with / without its ridge, and the deliberately
                                         wrong covers check.py must catch)
    python -B build_cover.py --design   only the design-frame files (fast: no STEP)

Run with the venv named in CLAUDE.local.md (cadquery, trimesh).
"""
import argparse
import sys
from pathlib import Path

import cadquery as cq

import model as M

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out' / 'design'
PRINT = HERE.parent.parent / 'print' / 'cover'          # NOT print/4.26 or print/3.68: both case builds delete any file there they did not make (build.write_print)

# what each printed cover is called, and the folder it goes to
COVERS = {'keyed': ('4.26', 'cover-keyed'), 'chinless': ('4.26', 'cover-chinless'), 'x3': ('3.68', 'cover-standard')}
# the fit coupons: the top end's channel with its prong, 30 mm of it, in three variants (2026-11-01). cy is the channel
# clearance per side, d_eng how far the snap's ridge stands inside the end face (the prong deflects that much on the flat)
COUPONS = {'A': dict(cy=0.30, d_eng=0.7, note='the cover as designed'),
           'B': dict(cy=0.40, d_eng=0.7, note='a looser slide (0.10 more each side)'),
           'C': dict(cy=0.30, d_eng=1.0, note='a firmer snap (the ridge 0.3 deeper)')}
COUPON_LEN = 30.0
COUPON_W = 16.0                    # the plate strip's width from the end face inward


def stl(shape, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(shape, str(path), tolerance=0.02, angularTolerance=0.1)


def coupon_body(group, key):
    """The top end of the cover: plate strip, wall, lip, prong with its ridge, 30 mm of it from the prong's tip. Built from a
    cover without pockets or relief (coupon_spec) and cut to a box."""
    s = M.spec(group, **{k: v for k, v in COUPONS[key].items() if k != 'note'}, tp=1.8)
    body = M.build(s, relief=False)
    x0 = s['u_tip']
    box = M._box(x0 - 0.5, x0 + COUPON_LEN, s['Y1'] - COUPON_W, s['yw_t'] + s['tw'] + 1.0, s['z_lb'] - 1, s['z_o'] + 1)
    return s, body.intersect(box)


def label(s, text, shape):
    """Engrave the variant's letter in the outer face (the bed face), readable from outside: 0.4 deep."""
    try:
        x = s['u_tip'] + COUPON_LEN - 6.0
        y = s['Y1'] - COUPON_W / 2 + 1.0
        t = (cq.Workplane('XY', origin=(x, y, s['z_o'] - 0.4)).text(text, 7.0, 0.5, kind='bold', halign='center',
                                                                       valign='center'))
        return shape.cut(t)
    except Exception as e:                                           # a missing font must not stop the build
        print('  label skipped:', e)
        return shape


def build_all(design_only=False):
    OUT.mkdir(parents=True, exist_ok=True)
    for g, (folder, name) in COVERS.items():
        s = M.spec(g)
        print(f'{g}: tp {s["tp"]}, G {s["G"]}, D_in {s["D_in"]}, gaps {[tuple(round(v, 1) for v in x) for x in M.gaps(s)]}')
        full = M.build(s)
        frame = M.build(s, ridge=False)
        stl(full, OUT / f'{g}.stl')
        stl(frame, OUT / f'{g}-frame.stl')
        if g == 'keyed':
            # the deliberately wrong covers (check.py must fail on each): no stop-wall gaps; the ridge moved into the J6 band
            stl(M.build(M.spec(g), with_gaps=False, ridge=False), OUT / f'{g}-wrong-nogaps.stl')
            wr = M.spec(g, ridge_shift=4.2, ridge_half=1.4)
            stl(M.build(wr), OUT / f'{g}-wrong-ridge.stl')
        if not design_only:
            p = M.to_print_frame(full, s)
            d = PRINT / folder
            d.mkdir(parents=True, exist_ok=True)
            stl(p, d / f'{name}.stl')
            cq.exporters.export(p, str(d / f'{name}.step'))
            bb = p.val().BoundingBox()
            print(f'  -> print/cover/{folder}/{name}.stl/.step  {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm, '
                  f'{p.val().Volume() / 1000:.2f} cm3')
    for g, (folder, base) in (('keyed', ('4.26', 'cover-coupon')), ('x3', ('3.68', 'cover-coupon'))):
        keys = COUPONS if g == 'keyed' else {'A': COUPONS['A']}
        for k in keys:
            s, c = coupon_body(g, k)
            stl(c, OUT / f'coupon-{g}-{k}.stl')
            c = label(s, k, c)
            if not design_only:
                p = M.to_print_frame(c, s)
                name = f'{base}-{k}' if g == 'keyed' else base
                d = PRINT / folder
                stl(p, d / f'{name}.stl')
                cq.exporters.export(p, str(d / f'{name}.step'))
                bb = p.val().BoundingBox()
                print(f'  coupon {g} {k}: {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm, {p.val().Volume() / 1000:.2f} cm3'
                      f' -> print/cover/{folder}/{name}.stl')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--design', action='store_true', help='only the design-frame files')
    a = ap.parse_args()
    build_all(a.design)
