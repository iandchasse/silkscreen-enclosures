"""Print orientation, overhang audit and a one-plate fit check for a 256 x 256 mm bed
(Elegoo Centauri Carbon 2). Reads out/<build>/*.stl, writes the oriented STLs and print-report.json to
out/<build>/print/. enclosures/make_plates.py reads those STLs for every print build and writes the plate files:
print/silkscreen-426-plates.3mf (generic OrcaSlicer project, the released builds), print/cc2-local/ (the author's Elegoo
CC2 files, every build; git-ignored) and, with `configs`, each configuration's own project in out/configs/;
build.write_print writes print/4.26/ the same way.

The fit check (print-report.json, '_plate'): every part of one build, the PCBA dummy included, laid out on
one bed, centred. It is only a check: the plate file is make_plates.py's.

Overhang audit: every downward-facing triangle steeper than 45 degrees from vertical that
is not on the bed is summed per part. Bridges (flat spans between two supports) show up
too; the report lists the largest regions so each can be checked by eye. The bottom keys
(on their -X end since test 1, 2026-09-29) are held to KEY_OVERHANG_MAX: what shows is
their bed end's steps (KEY_BED_END) and 45-degree faces at the limit ('_checks').
"""
import json
import numpy as np
import trimesh
import hw
import params as P

OUT = P.OUT
PRINT = OUT / 'print'
PRINT.mkdir(exist_ok=True)
BED = 256.0
GAP = 6.0

# part: rotation that puts it in print orientation (face on the bed = min Z after rotation)
ORIENT = {
    'tub': ('x', 180),          # front face down
    'lid': (None, 0),           # back face down, the five side keys standing on it (Rev J)
    'midplate': ('x', 180),     # screen side down
    'key-426': ('y', -90),      # on its -X end, +X up (test 1): the -X hook on the bed, the +X hook's 45-degree lead
    'crank-M': ('x', 90),       # on the pad end (y -7.70), +Y up: every -Y face is 45 degrees or steeper
    'crank-T': ('x', 90),
    'coupon-chin': ('x', 180),  # face down, as the tub (the hook keys' fit check, with a key-426)
    'gate': ('y', 90),          # the side gate on its inner face (the rod's stop): the flange is the first layers,
                                # the bevel a 45-degree overhang, the pull hole vertical
    'coupon-gate': ('x', 180),  # face down, as the tub
    'pcba-dummy': ('x', 180),   # test-fit stand-in (dummy.py): board front face down, parts up
}
BOTTOM_KEY_PARTS = ('key-426', 'crank-M', 'crank-T', 'coupon-chin', 'gate', 'coupon-gate')
if not P.BOTTOM_KEYS:           # chinless: no bottom-key parts to orient (and none left in print/: the pruning below)
    ORIENT = {k: v for k, v in ORIENT.items() if k not in BOTTOM_KEY_PARTS}
# the plate's small parts and how many of each: four keys, and four cranks of each nose (only one set is
# fitted - crank-T on a TS365ZJ board, crank-M on an MJTP1117 one - but they are 0.1 g each, and printing
# both leaves the choice to the board in hand), and two side gates (one is a spare: it is small enough to lose)
SMALL = [('key-426', 4), ('crank-M', 4), ('crank-T', 4), ('gate', 2)] if P.BOTTOM_KEYS else []
PLATE = ['tub', 'lid', 'midplate', 'pcba-dummy', *[n for n, _ in SMALL]]
KEY_OVERHANG_MAX = 3.5                  # mm2 per key off the bed (test 1: on its -X end)
KEYS = ['key-426'] if P.BOTTOM_KEYS else []   # the drag coupon's keys 1-4 went with the drag leaf (test 2, 2026-09-30)


def oriented(name, out=OUT):
    src = out / f'{name}.stl'
    m = trimesh.load(src)
    axis, deg = ORIENT[name]
    if axis:
        vec = {'x': [1, 0, 0], 'y': [0, 1, 0], 'z': [0, 0, 1]}[axis]
        m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(deg), vec))
    m.apply_translation(-m.bounds[0])
    return m


def overhangs(m, limit_deg=45.0, bed_tol=0.25):
    n = m.face_normals
    z = m.triangles_center[:, 2]
    down = n[:, 2] < -np.cos(np.radians(limit_deg))
    off_bed = z > bed_tol
    sel = down & off_bed
    area = m.area_faces[sel]
    centers = m.triangles_center[sel]
    # cluster overhang faces into regions on a 2 mm grid for a readable report
    regions = {}
    for c, a in zip(centers, area):
        key = tuple((c // 2).astype(int))
        regions[key] = regions.get(key, 0) + a
    top = sorted(regions.items(), key=lambda kv: -kv[1])[:8]
    return {'overhang_mm2': round(float(area.sum()), 2),
            'largest_regions': [{'at_mm': [float(k[0] * 2 + 1), float(k[1] * 2 + 1), float(k[2] * 2 + 1)],
                                 'mm2': round(float(v), 2)} for k, v in top]}


def layout(meshes):
    """Tub and lid side by side, the midplate and the dummy under them, the bottom keys and cranks in
    columns beside them, then the whole group moved so its bounding box is centred on the bed."""
    placed = {}

    def put(name, x0, y0):
        m = meshes[name]
        m.apply_translation([x0 - m.bounds[0][0], y0 - m.bounds[0][1], 0])
        placed[name] = m
        return m

    ext = {k: meshes[k].extents for k in meshes}
    row0 = max(ext['midplate'][1], ext['pcba-dummy'][1])       # lower row: midplate, dummy
    put('midplate', 0.0, 0.0)
    put('pcba-dummy', placed['midplate'].bounds[1][0] + GAP, 0.0)
    put('tub', 0.0, row0 + GAP)
    put('lid', placed['tub'].bounds[1][0] + GAP, row0 + GAP)
    x_col = max(m.bounds[1][0] for m in placed.values()) + GAP
    # the small parts, a column of each, longest side along Y
    for name, count in SMALL:
        y, w = 0.0, 0.0
        for i in range(count):
            m = meshes[name].copy()
            if m.extents[0] > m.extents[1]:
                m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 0, 1]))
            meshes[f'{name}#{i + 1}'] = m
            m = put(f'{name}#{i + 1}', x_col, y)
            y = m.bounds[1][1] + GAP * 0.75
            w = max(w, m.extents[0])
        x_col += w + GAP
    lo = np.min([m.bounds[0] for m in placed.values()], axis=0)
    hi = np.max([m.bounds[1] for m in placed.values()], axis=0)
    shift = [BED / 2 - (lo[0] + hi[0]) / 2, BED / 2 - (lo[1] + hi[1]) / 2, 0]
    for m in placed.values():
        m.apply_translation(shift)
    return placed


if __name__ == '__main__':
    report = {}
    meshes = {}
    for name in ORIENT:
        m = oriented(name)
        meshes[name] = m
        report[name] = {'size_mm': [round(v, 2) for v in m.extents], 'watertight': bool(m.is_watertight),
                        'volume_mm3': round(float(m.volume), 1), 'mass_g_PLA': round(float(m.volume) * 1.24e-3, 2),
                        **overhangs(m)}
        m.export(PRINT / f'{name}.stl')
    placed = layout({k: meshes[k].copy() for k in PLATE})
    bounds = np.array([m.bounds for m in placed.values()])
    lo, hi = bounds[:, 0, :].min(axis=0), bounds[:, 1, :].max(axis=0)
    report['_plate'] = {'bed_mm': BED, 'used_x': [round(float(lo[0]), 1), round(float(hi[0]), 1)], 'used_y': [round(float(lo[1]), 1), round(float(hi[1]), 1)],
                        'centre': [round(float(lo[0] + hi[0]) / 2, 1), round(float(lo[1] + hi[1]) / 2, 1)],
                        'parts': list(placed), 'fits': bool(lo[0] >= 0 and lo[1] >= 0 and hi[0] <= BED and hi[1] <= BED)}
    report['_checks'] = {f'{k} overhang {report[k]["overhang_mm2"]} <= {KEY_OVERHANG_MAX} mm2':
                         report[k]['overhang_mm2'] <= KEY_OVERHANG_MAX for k in KEYS}
    report['_checks'].update({f'{k} watertight': report[k]['watertight'] for k in ORIENT})
    report['_checks']['plate fits'] = report['_plate']['fits']
    (PRINT / 'print-report.json').write_text(json.dumps(report, indent=1))
    # parts this build no longer makes (Rev K's rocker keys, key_SW*) would otherwise linger here, and so
    # would the one-plate 3MF and STL this script wrote until 2026-09-28 (make_plates.py's plate file replaces it)
    for f in [*PRINT.glob('*.stl'), *PRINT.glob('*.3mf')]:
        if f.stem not in ORIENT:
            f.unlink()
            print('removed stale', f.name)
    for k, v in report.items():
        if k == '_checks':
            for c, ok in v.items():
                print(f"{'PASS' if ok else 'FAIL'}  {c}")
        elif k.startswith('_'):
            print(k, v)
        else:
            print(f"{k:10s} {v['size_mm']}  {v['mass_g_PLA']:5.2f} g  watertight={v['watertight']}  overhang>45: {v['overhang_mm2']} mm2")
            for r in v['largest_regions'][:4]:
                print('            ', r)
