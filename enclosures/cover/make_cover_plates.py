"""The slide cover's OrcaSlicer plate file, made the way make_plates.py makes its plate files (its functions, imported:
Part, lay_out, build, project_settings: the generic or CC2 presets over orca-project-defaults.json, so every key OrcaSlicer
writes itself is there, filament_colour included). Nothing in make_plates.py or the case projects is edited.

    python -B make_cover_plates.py [--printer generic|cc2]
        generic (default): print/silkscreen-cover-plates.3mf   (OrcaSlicer's generic presets, a 220 x 210 bed; in git)
        cc2:               print/cc2-local/silkscreen-cover-plates.3mf   (Ian's Elegoo Centauri Carbon 2; git-ignored)

One plate per cover (round 2, 2026-11-01: the coupons are gone, coupon A confirmed the fit):
    1  Slide cover: 4.26 with bottom keys           cover-keyed
    2  Slide cover: 4.26 chinless                   cover-chinless
    3  Slide cover: 3.68 standard                   cover-standard
The covers are NOT in the case plate files or the per-configuration projects (2026-11-01, Ian: one separate file). TEMPORARY: until they
go into the case plates (a later phase), these are the only plate files with covers.
Each cover carries the case's two logo inlays as modifier parts with no filament (the two-colour switch, off), named like the lid's
(make_plates.INLAY_NAMES): to switch the logo on, do what the lid's switch asks (print/README.md, "Two-colour logo"): one part at a time, Change type -> Part, Set Filament -> 2.

Per-object settings: wall_loops 4 on the covers (the channel wall is 1.6 mm: four lines; the stock process has 2).
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


def cover_part(name, folder, stem):
    """A cover Part with its two logo inlays (modifier parts, named as the lid's)."""
    return MP.Part(name, folder / f'{stem}.stl',
                   inlay_files=[(label, folder / f'{stem}-inlay-{inl.split("_")[1]}.stl') for inl, label in MP.INLAY_NAMES])


def parts():
    f426, f368 = PRINT / 'cover' / '4.26', PRINT / 'cover' / '3.68'
    return dict(keyed=cover_part('cover-keyed (4.26, bottom keys)', f426, 'cover-keyed'),
                chinless=cover_part('cover-chinless (4.26)', f426, 'cover-chinless'),
                x3=cover_part('cover-standard (3.68)', f368, 'cover-standard'))


NAMES = ('Slide cover: 4.26 with bottom keys (standard and light strip)',
         'Slide cover: 4.26 chinless (touch, no bottom keys)',
         'Slide cover: 3.68 standard')


def case(printer):
    p = parts()
    if printer == 'generic':
        plates = [(NAMES[0], [p['keyed']], [], [], []), (NAMES[1], [p['chinless']], [], [], []), (NAMES[2], [p['x3']], [], [], [])]
        out = PRINT / 'silkscreen-cover-plates.3mf'
    else:
        plates = [(NAMES[0], [[p['keyed']]], []), (NAMES[1], [[p['chinless']]], []), (NAMES[2], [[p['x3']]], [])]
        out = MP.CC2_LOCAL / 'silkscreen-cover-plates.3mf'
    return dict(title='Silkscreen slide cover - temporary plates', out=out, printer=printer, plates=plates, shared=[])


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--printer', choices=('generic', 'cc2'), default='generic')
    a = ap.parse_args()
    c = case(a.printer)
    print(c['title'], f'({a.printer})')
    MP.build(c)
