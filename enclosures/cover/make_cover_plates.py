"""The slide cover's OrcaSlicer plate file, made the way make_plates.py makes its plate files (its functions, imported:
Part, lay_out, build, project_settings: the generic or CC2 presets over orca-project-defaults.json, so every key OrcaSlicer
writes itself is there, filament_colour included). Nothing in make_plates.py or the case projects is edited.

    python -B make_cover_plates.py [--printer generic|cc2]
        generic (default): print/silkscreen-cover-plates.3mf   (OrcaSlicer's generic presets, a 220 x 210 bed; in git)
        cc2:               print/cc2-local/silkscreen-cover-plates.3mf   (Ian's Elegoo Centauri Carbon 2; git-ignored)

Plate 1 is the fit coupons (print them first); then one plate per cover:
    1  Test prints: the slide cover's fit coupons   cover-coupon-A/B/C (4.26) and the 3.68's cover-coupon
    2  Slide cover: 4.26 with bottom keys           cover-keyed
    3  Slide cover: 4.26 chinless                   cover-chinless
    4  Slide cover: 3.68 standard                   cover-standard
The covers are NOT in the case plate files or the per-configuration projects (2026-11-01, Ian: one separate file).

Per-object settings: wall_loops 4 on the covers and coupons (the channel wall is 1.6 mm: four lines; the stock process has 2).
Everything else is the stock process; supports are off (the design needs none: slice_read.py reads that back).
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENC = HERE.parent
sys.path.insert(0, str(ENC))
import make_plates as MP                       # noqa: E402  (the shared tool; never edited from here)

PRINT = MP.PRINT
COVER_OBJ = {'wall_loops': '4'}

_orig_object_settings = MP.object_settings


def object_settings(p, printer='cc2'):
    obj = _orig_object_settings(p, printer)
    if p.stl.stem.startswith('cover-'):
        obj.update(COVER_OBJ)
    return obj


MP.object_settings = object_settings


def parts():
    f426, f368 = PRINT / 'cover' / '4.26', PRINT / 'cover' / '3.68'
    coupons = [MP.Part('cover-coupon-A (4.26: clearance 0.30, snap 0.7)', f426 / 'cover-coupon-A.stl'),
               MP.Part('cover-coupon-B (4.26: looser, clearance 0.40)', f426 / 'cover-coupon-B.stl'),
               MP.Part('cover-coupon-C (4.26: firmer snap, 1.0)', f426 / 'cover-coupon-C.stl'),
               MP.Part('cover-coupon (3.68: clearance 0.30, snap 0.7)', f368 / 'cover-coupon.stl')]
    return dict(coupons=coupons,
                keyed=MP.Part('cover-keyed (4.26, bottom keys)', f426 / 'cover-keyed.stl'),
                chinless=MP.Part('cover-chinless (4.26)', f426 / 'cover-chinless.stl'),
                x3=MP.Part('cover-standard (3.68)', f368 / 'cover-standard.stl'))


NAMES = ('Test prints: the slide cover fit coupons (print these first)',
         'Slide cover: 4.26 with bottom keys (standard and light strip)',
         'Slide cover: 4.26 chinless (touch, no bottom keys)',
         'Slide cover: 3.68 standard')


def case(printer):
    p = parts()
    if printer == 'generic':
        plates = [(NAMES[0], p['coupons'], [], [], []), (NAMES[1], [p['keyed']], [], [], []),
                  (NAMES[2], [p['chinless']], [], [], []), (NAMES[3], [p['x3']], [], [], [])]
        out = PRINT / 'silkscreen-cover-plates.3mf'
    else:
        plates = [(NAMES[0], [p['coupons']], []), (NAMES[1], [[p['keyed']]], []), (NAMES[2], [[p['chinless']]], []),
                  (NAMES[3], [[p['x3']]], [])]
        out = MP.CC2_LOCAL / 'silkscreen-cover-plates.3mf'
    return dict(title='Silkscreen slide cover - fit coupons and covers', out=out, printer=printer, plates=plates, shared=[])


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--printer', choices=('generic', 'cc2'), default='generic')
    a = ap.parse_args()
    c = case(a.printer)
    print(c['title'], f'({a.printer})')
    MP.build(c)
