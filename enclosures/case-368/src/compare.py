"""Size comparison against the Xteink X4 and the X4 "retro case".

Sources (hardware/compare/, copied from Ian's downloads):
  x4/files/X4_-_Xteink_X4_model.stl   Xteink X4 reference model by Zorian22, Thingiverse
                                      thing:7287950, CC BY-NC-SA. Measured with calipers.
  retrocase/*.stl                     the retro case's print files (front frame, two back-plate
                                      halves, buttons), laid out flat for printing.

The retro case is reassembled here: the frame is printed face down, so it is flipped; the two
back-plate halves are placed against its bottom and top edges and pushed onto the frame until
they touch (manifold collision), which puts their outer face 9.8 mm behind the front face.

Frames used below. Device frame: front face at z = 0 facing +Z, screen centre at the origin.
The X4 model has no screen marking, so its screen centre is taken as the retro case's window
centre with the X4 seated in the case, and its active area comes from Xteink's spec
(800 x 480 at 220 ppi). Ours comes from the FT01C drawing.

Writes out/compare.json. meshes() gives the placed models for the 3D view.
"""
import json
import numpy as np
import trimesh
import manifold3d as mf
import shapely.geometry as sg
import shapely.ops as so
import hw
import params as P

SRC = hw.ROOT / 'hardware' / 'compare'
RETRO = SRC / 'retrocase'
X4_STL = SRC / 'x4' / 'files' / 'X4_-_Xteink_X4_model.stl'
PETG = 1.27e-3                 # g/mm3
X4_ACTIVE = (480 / 220 * 25.4, 800 / 220 * 25.4)       # (w, h) portrait, 55.4 x 92.4
X4_SPEC = (69.0, 114.0, 5.9)


def _man(m):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))


def _retro(name):
    return trimesh.load(next(RETRO.glob(f'*{name}.stl')))


def retro_parts():
    """Assembled retro case in its own frame: front face at z = 0, outline centred on XY."""
    frame = _retro('stl_7')
    frame.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [0, 1, 0]))
    frame.apply_translation(-np.r_[frame.bounds.mean(0)[:2], frame.bounds[1][2]])
    fb = frame.bounds
    lower, upper = _retro('stl_2'), _retro('stl_6')              # the plate halves
    lower.apply_translation([fb[0][0] - lower.bounds[0][0], fb[0][1] - lower.bounds[0][1], 0])
    upper.apply_translation([fb[0][0] - upper.bounds[0][0], fb[1][1] - upper.bounds[1][1], 0])
    F = _man(frame)
    for plate in (lower, upper):
        # Seat each half as far forward as it goes without overlapping the frame. The halves
        # carry snap bumps that collide on the way in, so this scans instead of bisecting.
        mp = _man(plate)
        base = -plate.bounds[1][2]
        free = [z for z in np.arange(-14.0, 0.001, 0.05) if (F ^ mp.translate([0, 0, base + z])).volume() < 0.5]
        plate.apply_translation([0, 0, base + max(free)])
    return {'retro_frame': frame, 'retro_back_lower': lower, 'retro_back_upper': upper}


def x4_in_retro(frame):
    """Seat the X4 in the retro frame: centred in X, the Y shift and depth with no overlap."""
    x4 = trimesh.load(X4_STL)
    x4.apply_translation([0, 0, -x4.bounds[1][2]])       # the model's own origin is its body centre
    F, X = _man(frame), _man(x4)
    best = None
    for dy in np.arange(-1.0, 1.01, 0.25):
        for dz in np.arange(-1.0, -3.01, -0.1):
            if (F ^ X.translate([0, dy, dz])).volume() < 0.05:
                if best is None or dz > best[1] + 1e-9:
                    best = (dy, dz)
                break
    x4.apply_translation([0, best[0], best[1]])
    return x4


def filled(polys):
    """Union of section polygons with their holes filled (the outer envelope)."""
    g = so.unary_union([sg.Polygon(p.exterior) for p in polys if p.area > 1e-6])
    return g


def section_polys(meshes, z):
    out = []
    for m in meshes:
        s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if s is None:
            continue
        loops = [sg.Polygon(l[:, :2]).buffer(0) for l in s.discrete if len(l) >= 3]
        g = None
        for p in loops:
            g = p if g is None else g.symmetric_difference(p)
        if g is not None and not g.is_empty:
            out += list(getattr(g, 'geoms', [g]))
    return [p for p in out if p.geom_type == 'Polygon']


def envelope(meshes, z0, z1, dz=0.1):
    """Volume inside the outer surface and the largest footprint. Each slice is the convex hull
    of the section (every outline here is a rounded rectangle; button holes would otherwise
    break the wall rings open)."""
    vol, foot = 0.0, None
    for z in np.arange(z0 + dz / 2, z1, dz):
        polys = section_polys(meshes, z)
        if not polys:
            continue
        g = so.unary_union(polys).convex_hull
        vol += g.area * dz
        if foot is None or g.area > foot.area:
            foot = g
    return vol, foot


def silhouette(meshes, axes):
    """Projection outline of meshes onto two axes (e.g. (0, 1) = front view)."""
    tris = []
    for m in meshes:
        t = m.triangles[:, :, list(axes)]
        a = 0.5 * np.abs(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]))
        tris += [sg.Polygon(x) for x in t[a > 1e-7]]
    return so.unary_union(tris).buffer(0.01).buffer(-0.01).simplify(0.03)


def rings(g, nd=2):
    out = []
    for p in getattr(g, 'geoms', [g]):
        if p.geom_type != 'Polygon' or p.area < 0.5:
            continue
        out.append([[[round(x, nd), round(y, nd)] for x, y in p.exterior.coords]] +
                   [[[round(x, nd), round(y, nd)] for x, y in r.coords] for r in p.interiors])
    return out


def ours():
    """Our shell (tub + lid, as built) and the numbers that describe it."""
    tub = trimesh.load(hw.ROOT / 'out' / 'tub.stl')
    lid = trimesh.load(hw.ROOT / 'out' / 'lid.stl')
    return tub, lid


def main():
    import body, cadquery as cq
    rp = retro_parts()
    frame = rp['retro_frame']
    x4 = x4_in_retro(frame)
    # retro window: largest hole in the frame just behind its front face
    sec = section_polys([frame], -0.4)
    holes = sorted([sg.Polygon(r) for p in sec for r in p.interiors], key=lambda h: -h.area)
    win = holes[0].bounds
    win_c = ((win[0] + win[2]) / 2, (win[1] + win[3]) / 2)
    retro_meshes = list(rp.values())
    r_lo, r_hi = np.min([m.bounds[0] for m in retro_meshes], 0), np.max([m.bounds[1] for m in retro_meshes], 0)
    r_vol, r_foot = envelope(retro_meshes, r_lo[2], r_hi[2])
    buttons = [trimesh.load(f) for f in RETRO.glob('*.stl') if not any(k in f.name for k in ('stl_2', 'stl_6', 'stl_7'))]
    r_plastic = sum(m.volume for m in retro_meshes) + sum(b.volume for b in buttons)

    # X4 alone (its own centre), with its screen where the retro window is
    x4_front = x4.bounds[1][2]
    zs = np.round(x4.vertices[:, 2], 2)
    x4_body_front = float(np.percentile(zs, 99.0))                 # flat front, below the button bars
    x_vol = float(trimesh.load(X4_STL).volume)
    _, x_foot = envelope([x4], x4.bounds[0][2], x4.bounds[1][2], dz=0.2)

    # ours
    tub, lid = ours()
    ob = body.outer_body().val()
    o_vol = ob.Volume()
    o_foot = sg.box(P.X0, P.Y0, P.X1, P.Y1).area - (4 - np.pi) * P.CORNER_R ** 2
    shapes = ['tub', 'lid', 'midplate'] + [f'key_{r}' for r in P.KEY_REFS]      # the lid carries the side keys
    o_plastic = sum(trimesh.load(hw.ROOT / 'out' / f'{n}.stl').volume for n in shapes)
    a_w, a_h, a_cx, a_cy = hw.ACTIVE_W, hw.ACTIVE_H, hw.ACTIVE_CX, hw.ACTIVE_CY
    # visible window, measured the same way as the retro case's: 0.4 mm behind the front face
    o_sec = section_polys([tub], P.Z_FRONT - 0.4)
    o_win = sorted([sg.Polygon(r) for p in o_sec for r in p.interiors], key=lambda h: -h.area)[0].bounds

    def row(name, w, h, t, vol, foot, plastic, act, bez, note):
        return {'name': name, 'w': round(w, 1), 'h': round(h, 1), 't': round(t, 1),
                'envelope_cm3': round(vol / 1000, 1), 'footprint_cm2': round(foot / 100, 1),
                'plastic_cm3': None if plastic is None else round(plastic / 1000, 1),
                'plastic_g': None if plastic is None else round(plastic * PETG, 1),
                'active_mm': [round(act[0], 1), round(act[1], 1)],
                'screen_ratio_pct': round(100 * act[0] * act[1] / foot, 1),
                'bezels': None if bez is None else {k: round(v, 1) for k, v in bez.items()}, 'note': note}

    rb = r_hi - r_lo
    rows = [
        row('Silkscreen (this case)', P.X1 - P.X0, P.Y1 - P.Y0, P.Z_FRONT - P.Z_BACK, o_vol, o_foot, o_plastic,
            (a_w, a_h), {'left': o_win[0] - P.X0, 'right': P.X1 - o_win[2], 'top': P.Y1 - o_win[3], 'bottom': o_win[1] - P.Y0},
            'FT01C panel with frontlight and touch; 8 printed parts'),
        row('Xteink X4', x4.extents[0], x4.extents[1], x4_body_front - x4.bounds[0][2], x_vol, x_foot.area, None,
            X4_ACTIVE, None, 'reference model, calipers; spec 69 x 114 x 5.9'),
        row('X4 in the retro case', rb[0], rb[1], rb[2], r_vol, r_foot.area, r_plastic, X4_ACTIVE,
            {'left': win[0] - r_lo[0], 'right': r_hi[0] - win[2], 'top': r_hi[1] - win[3], 'bottom': win[1] - r_lo[1]},
            'bezels measured to the case window'),
    ]

    # thickness budget for ours, front to back
    import refs
    deepest = min(hw.bounds(r)[4] for r in hw.solids() if r != 'PCB')
    budget = [('front skin', P.Z_FRONT - P.LIP), ('panel', hw.PANEL_T), ('midplate', P.MID_T), ('air to board', P.MID_REAR - P.PCB_FRONT),
              ('PCB', P.PCB_FRONT), ('rear parts (expansion header, J6)', -deepest), ('clearance', deepest - P.LID_FLOOR_IN), ('back', P.LID_T)]

    # silhouettes in the device frame: screen centre at (0, 0), front face at z = 0
    o_front = silhouette([tub, lid], (0, 1))
    o_side = silhouette([tub, lid], (1, 2))
    x4_front_s = silhouette([x4], (0, 1))
    x4_side_s = silhouette([x4], (1, 2))
    r_front = silhouette(retro_meshes, (0, 1))
    r_side = silhouette(retro_meshes, (1, 2))
    from shapely.affinity import translate
    views = {
        'ours': {'front': rings(translate(o_front, -a_cx, -a_cy)), 'side': rings(translate(o_side, -a_cy, -P.Z_FRONT)),
                 'screen': [-a_w / 2, -a_h / 2, a_w / 2, a_h / 2],
                 'window': [round(v, 2) for v in (o_win[0] - a_cx, o_win[1] - a_cy, o_win[2] - a_cx, o_win[3] - a_cy)]},
        'x4': {'front': rings(translate(x4_front_s, -win_c[0], -win_c[1])),
               'side': rings(translate(x4_side_s, -win_c[1], -x4_body_front)),       # front face level with the others
               'screen': [-X4_ACTIVE[0] / 2, -X4_ACTIVE[1] / 2, X4_ACTIVE[0] / 2, X4_ACTIVE[1] / 2]},
        'retro': {'front': rings(translate(r_front, -win_c[0], -win_c[1])), 'side': rings(translate(r_side, -win_c[1], 0)),
                  'window': [round(v, 2) for v in (win[0] - win_c[0], win[1] - win_c[1], win[2] - win_c[0], win[3] - win_c[1])]},
    }
    out = {'rows': rows, 'budget': [[k, round(v, 2)] for k, v in budget], 'views': views,
           'retro_window_mm': [round(win[2] - win[0], 1), round(win[3] - win[1], 1)],
           'our_window_mm': [round(o_win[2] - o_win[0], 1), round(o_win[3] - o_win[1], 1)],
           'x4_seat': {'depth_mm': round(-x4_front, 2)}, 'retro_plate_z': round(float(r_lo[2]), 2),
           'x4_active_from': '800 x 480 at 220 ppi (Xteink spec)'}
    (hw.ROOT / 'out' / 'compare.json').write_text(json.dumps(out, separators=(',', ':')))
    return out


def meshes():
    """Comparison models placed beside ours in the CAD frame, front faces level with ours:
    the X4 on the left and the retro case on the right, bottom edges on a common line."""
    rp = retro_parts()
    x4 = trimesh.load(X4_STL)
    zs = np.round(x4.vertices[:, 2], 2)
    front = float(np.percentile(zs, 99.0))
    gap = 18.0
    x4.apply_translation([P.X0 - gap - x4.bounds[1][0], P.Y0 - x4.bounds[0][1], P.Z_FRONT - front])
    lo = np.min([m.bounds[0] for m in rp.values()], 0)
    for m in rp.values():
        m.apply_translation([P.X1 + gap - lo[0], P.Y0 - lo[1], P.Z_FRONT])
    return {'cmp_x4': x4, **{'cmp_' + k: v for k, v in rp.items()}}


if __name__ == '__main__':
    import time
    t0 = time.time()
    o = main()
    for r in o['rows']:
        print(r)
    print('budget', o['budget'], 'sum', round(sum(v for _, v in o['budget']), 2))
    print('retro window', o['retro_window_mm'], 'x4 seat', o['x4_seat'], f'{time.time() - t0:.0f}s')
