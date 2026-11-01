"""Build the slide covers (round 2: no coupons, the case's logos engraved, rounded edges, four poses, the scallop).

    python -B build_cover.py            every cover: print/cover/4.26/cover-*.stl/.step, print/cover/3.68/cover-standard.stl/.step (the print
                                         frame: plate face down; the STEP in the case's CAD frame) with their two-colour inlay bodies
                                         (cover-*-inlay-wordmark.stl, -inlay-icon.stl, in the print frame), and cover/out/design/*.stl (the
                                         design frame the checks use: the cover on the case, with / without its ridge, and the deliberately
                                         wrong covers check.py must catch)
    python -B build_cover.py --design   only the design-frame files (fast: no STEP)

Run with the venv named in CLAUDE.local.md (cadquery, trimesh).
"""
import argparse
from pathlib import Path

import cadquery as cq
import trimesh

import model as M

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out' / 'design'
PRINT = HERE.parent.parent / 'print' / 'cover'          # NOT print/4.26 or print/3.68: both case builds delete any file there they did not make

# what each printed cover is called, and the folder it goes to
COVERS = {'keyed': ('4.26', 'cover-keyed'), 'chinless': ('4.26', 'cover-chinless'), 'x3': ('3.68', 'cover-standard')}


def stl(shape, path):
    """Export, and refuse an STL that is not a closed mesh (a printed part with holes in it)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(shape, str(path), tolerance=0.02, angularTolerance=0.1)
    m = trimesh.load(path, force='mesh')
    if not m.is_watertight:
        raise SystemExit(f'{path}: the mesh is not watertight')


def build_all(design_only=False):
    OUT.mkdir(parents=True, exist_ok=True)
    for g, (folder, name) in COVERS.items():
        s = M.spec(g)
        full = M.build(s)
        notes = list(M.NOTES)
        print(f'{g}: tp {s["tp"]}, G {s["G"]}, D_in {s["D_in"]}, scallop d {s["d_scallop"]} zone '
              f'{[(round(a, 1), round(b, 1)) for a, b in s["zones"]]}, corner extension {s["ext"]} (room {s["ext_room"]})')
        for n in notes:
            print('   note:', n)
        frame = M.build(s, ridge_on=False)
        stl(full, OUT / f'{g}.stl')
        stl(frame, OUT / f'{g}-frame.stl')
        if g == 'keyed':
            # the deliberately wrong covers (check.py must fail on each)
            stl(M.build(M.spec(g, slot_ends='bottom'), ridge_on=False), OUT / f'{g}-wrong-oneslot.stl')
            stl(M.build(M.spec(g, ext_override=16.0), ridge_on=False), OUT / f'{g}-wrong-longext.stl')
            stl(M.build(M.spec(g, ridge_shift=4.2, ridge_half=1.4)), OUT / f'{g}-wrong-ridge.stl')
            stl(M.build(M.spec(g, scallop_dmax=0.0), ridge_on=False), OUT / f'{g}-noscallop.stl')
        if not design_only:
            p = M.to_print_frame(full)
            d = PRINT / folder
            d.mkdir(parents=True, exist_ok=True)
            stl(p, d / f'{name}.stl')
            cq.exporters.export(full, str(d / f'{name}.step'))        # the STEP in the case's CAD frame (the cover on the front, at its drawn pose)
            bb = p.val().BoundingBox()
            print(f'  -> print/cover/{folder}/{name}.stl/.step  {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm, {p.val().Volume() / 1000:.2f} cm3')
            for lname in ('wordmark', 'icon'):                         # the two-colour logo switch: the bodies that fill the engravings
                ink = M.to_print_frame(M.logo_inlay(s, lname), ref=full)
                stl(ink, d / f'{name}-inlay-{lname}.stl')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--design', action='store_true', help='only the design-frame files')
    a = ap.parse_args()
    build_all(a.design)
