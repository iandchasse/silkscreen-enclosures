"""Print orientation, overhang audit and a one-plate fit check for a 256 x 256 mm bed
(Elegoo Centauri Carbon 2). Reads out/<variant>/*.stl, writes the oriented STLs and print-report.json to
out/<variant>/print/ (variant.py: run it once per build). enclosures/make_plates.py reads those STLs for both
builds and writes the plate files, print/silkscreen-368-plates.3mf (generic OrcaSlicer project, the standard build) and
print/cc2-local/ (the author's Elegoo CC2 file, both builds; git-ignored); the committed print/3.68/
folder is build.py's (build.write_print), oriented the same way.

The fit check (print-report.json, '_plate'): every part of one build, the PCBA dummy included, laid out on one bed,
centred. It is only a check: the plate file is make_plates.py's.

Overhang audit: every downward-facing triangle steeper than 45 degrees from vertical that
is not on the bed is summed per part. Bridges (flat spans between two supports) show up
too; the report lists the largest regions so each can be checked by eye. The bottom keys
(on their -X end since test 1, 2026-09-29) are held to KEY_OVERHANG_MAX: what shows is
their bed end's steps (KEY_BED_END) and 45-degree faces at the limit ('_checks'). The hook
keys (test 2, 2026-09-30): the key's own faces steeper than 45 degrees are listed by region
(key_steep: none may be a free overhang over 0.5 mm), and the tub round each hook slot
(tub.key_slots, 0.3 all round, up to 0.3 over its roof) has none at all (slot_audit).
"""
import json
import numpy as np
import trimesh
import hw
import params as P

OUT = hw.OUT
PRINT = OUT / 'print'
PRINT.mkdir(exist_ok=True)
BED = 256.0
GAP = 6.0

# part: rotation that puts it in print orientation (face on the bed = min Z after rotation)
ORIENT = {
    'tub': ('x', 180),          # front face down
    'lid': (None, 0),           # back face down, the side keys standing on it (Rev J)
    'midplate': ('x', 180),     # screen side down
    'key-x3std': ('y', -90), 'key-x3ls': ('y', -90),   # bottom keys: on the -X end, +X up (keys.py; test 1)
    'crank-M': ('x', 90), 'crank-T': ('x', 90),         # on the pad end, +Y up (crank.py)
    'coupon-strip': ('x', 180),                         # the hook keys' fit check: face down, as the tub
    'gate': ('y', 90),                                  # the rod's gate: inner face (X -2.34) on the bed (crank.gate)
    'coupon-gate': ('x', 180),                          # the gate's proof coupon: face down, as the tub
    'pcba-dummy': ('x', 180),   # test-fit stand-in (dummy.py): board front face down, parts up
}
KEY = 'key-x3ls' if P.LIGHT_STRIP else 'key-x3std'
# The plate carries four keys, four cranks and two gates (one a spare): crank-T, for a JLC board (TS365ZJ switches); a
# board with the MJTP1117 takes crank-M (print/ has both).
PLATE_CRANK = 'crank-T'
PARTS = ['tub', 'lid', 'midplate', KEY, 'crank-M', 'crank-T', 'gate', 'coupon-strip', 'coupon-gate', 'pcba-dummy']
SMALL = [KEY] * 4 + [PLATE_CRANK] * 4 + ['gate'] * 2
KEY_OVERHANG_MAX = 3.5                  # mm2 per key off the bed (test 1: on its -X end)


def orient(m, name):
    """Mesh m of part `name` (CAD frame) turned into its print orientation, its bounds' low corner at the origin.
    build.write_print uses it on either build's files."""
    axis, deg = ORIENT[name]
    if axis:
        vec = {'x': [1, 0, 0], 'y': [0, 1, 0], 'z': [0, 0, 1]}[axis]
        m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(deg), vec))
    m.apply_translation(-m.bounds[0])
    return m


def oriented(name, d=OUT):
    return orient(trimesh.load(d / f'{name}.stl'), name)


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


def key_steep(m, limit_deg=45.0, bed_tol=0.25, slack_deg=0.5, step=0.1):
    """The oriented key's faces that overhang past limit_deg + slack_deg (the 45-degree lead and chamfers sit on the
    limit), off the bed, and how far each reaches out past the material just under it: each such triangle's corners
    against the key's own section `step` below it (0 where they lie over it). The rule: nothing reaches out more than
    0.5 mm unless it is a bridge anchored at both ends (<= 5 mm; the key has none)."""
    from shapely.geometry import Point, Polygon
    from shapely.ops import unary_union
    n = m.face_normals
    sel = (n[:, 2] < -np.sin(np.radians(limit_deg + slack_deg))) & (m.triangles_center[:, 2] > bed_tol)
    secs, worst, area = {}, [], float(m.area_faces[sel].sum())
    for i in np.nonzero(sel)[0]:
        zb = round(float(m.triangles[i][:, 2].min()) - step, 3)
        if zb not in secs:
            s = m.section(plane_origin=[0, 0, zb], plane_normal=[0, 0, 1])
            secs[zb] = unary_union([Polygon(q).buffer(0) for q in s.discrete if len(q) >= 3]) if s is not None else Polygon()
        g = secs[zb]
        r = max(Point(v[:2]).distance(g) if not g.is_empty else 9.9 for v in m.triangles[i])
        worst.append((round(float(r), 3), [round(float(c), 2) for c in m.triangles_center[i]]))
    worst.sort(key=lambda t: -t[0])
    return {'area_mm2': round(area, 3), 'triangles': len(worst), 'reach_mm_worst': [w[0] for w in worst[:5]],
            'at_mm': [w[1] for w in worst[:5]], 'ok': all(w[0] <= 0.5 for w in worst)}


def slot_audit(m_cad, limit_deg=45.0, pad=0.3):
    """The tub round each hook slot (CAD frame; the tub prints face down, so a face that faces +Z here faces the bed):
    faces steeper than limit_deg in the print inside the slot's box grown `pad` (from below the rim to pad over the
    roof). There must be none: the slots are open at the top of the print and stand on a flat floor (the roof)."""
    import tub
    n, c, a = m_cad.face_normals, m_cad.triangles_center, m_cad.area_faces
    steep = n[:, 2] > np.cos(np.radians(limit_deg)) + 1e-6
    tot, where = 0.0, []
    for b in tub.key_slots():
        bb = b.val().BoundingBox()
        inside = ((c[:, 0] > bb.xmin - pad) & (c[:, 0] < bb.xmax + pad) & (c[:, 1] > bb.ymin - pad) &
                  (c[:, 1] < bb.ymax + pad) & (c[:, 2] > P.SEAM - 0.01) & (c[:, 2] < bb.zmax + pad))
        sel = steep & inside
        if sel.any():
            tot += float(a[sel].sum())
            where.append([round(float(bb.xmin), 2), round(float(bb.xmax), 2), round(float(a[sel].sum()), 4)])
    return {'slots': len(tub.key_slots()), 'steep_mm2': round(tot, 4), 'where': where, 'ok': tot <= 1e-4}


def layout(meshes):
    """Tub and lid side by side, the midplate and the dummy under them, the four bottom keys, four cranks and two gates
    in two columns beside them, then the whole group moved so its bounding box is centred on the bed."""
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
    # the small parts (four keys; four cranks and two gates) in two columns, longest side along Y
    y, col = 0.0, 0
    for i, name in enumerate(SMALL):
        if i == 4:
            x_col, y = max(m.bounds[1][0] for m in placed.values()) + GAP * 0.75, 0.0
        m = meshes[name].copy()
        if m.extents[0] > m.extents[1]:
            m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 0, 1]))
        meshes[f'{name}#{i}'] = m
        m = put(f'{name}#{i}', x_col, y)
        y = m.bounds[1][1] + GAP * 0.75
    lo = np.min([m.bounds[0] for m in placed.values()], axis=0)
    hi = np.max([m.bounds[1] for m in placed.values()], axis=0)
    shift = [BED / 2 - (lo[0] + hi[0]) / 2, BED / 2 - (lo[1] + hi[1]) / 2, 0]
    for m in placed.values():
        m.apply_translation(shift)
    return placed


if __name__ == '__main__':
    report = {}
    meshes = {}
    for name in PARTS:
        m = oriented(name)
        meshes[name] = m
        report[name] = {'size_mm': [round(v, 2) for v in m.extents], 'watertight': bool(m.is_watertight),
                        'volume_mm3': round(float(m.volume), 1), 'mass_g_PLA': round(float(m.volume) * 1.24e-3, 2),
                        **overhangs(m)}
        m.export(PRINT / f'{name}.stl')
    placed = layout({k: v.copy() for k, v in meshes.items()})
    bounds = np.array([m.bounds for m in placed.values()])
    lo, hi = bounds[:, 0, :].min(axis=0), bounds[:, 1, :].max(axis=0)
    report['_plate'] = {'bed_mm': BED, 'used_x': [round(float(lo[0]), 1), round(float(hi[0]), 1)], 'used_y': [round(float(lo[1]), 1), round(float(hi[1]), 1)],
                        'centre': [round(float(lo[0] + hi[0]) / 2, 1), round(float(lo[1] + hi[1]) / 2, 1)],
                        'parts': list(placed), 'fits': bool(lo[0] >= 0 and lo[1] >= 0 and hi[0] <= BED and hi[1] <= BED)}
    report['_key_steep'] = ks = key_steep(meshes[KEY])
    report['_slot_audit'] = sa = slot_audit(trimesh.load(OUT / 'tub.stl'))
    report['_checks'] = {f'{KEY} overhang {report[KEY]["overhang_mm2"]} <= {KEY_OVERHANG_MAX} mm2':
                         report[KEY]['overhang_mm2'] <= KEY_OVERHANG_MAX,
                         f"{KEY} no free overhang past 45 degrees over 0.5 mm (reaches {ks['reach_mm_worst']})": ks['ok'],
                         f"tub: nothing past 45 degrees round its {sa['slots']} hook slots ({sa['steep_mm2']} mm2)": sa['ok']}
    report['_checks'].update({f'{k} watertight': report[k]['watertight'] for k in PARTS})
    report['_checks']['plate fits'] = report['_plate']['fits']
    (PRINT / 'print-report.json').write_text(json.dumps(report, indent=1))
    # the one-plate 3MF and STL this script wrote until 2026-09-28 (make_plates.py's plate file replaces them)
    for f in [*PRINT.glob('*.stl'), *PRINT.glob('*.3mf')]:
        if f.stem not in PARTS:
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
