"""Reference parts that are not printed, in their assembled positions (x3).

display  the 3.68-inch panel stack from panel.py
strip    the light strip (this variant), from strip-geometry.json: bar, fold, neck and tail
battery  a 503035 LiPo (500 mAh, 5 x 30 x 37 mm, PH2.0 lead) in the lid's bay, behind the board: pouch, its
         protection board at the lead end, the lead routed to J5, and a JST PHR-2 plug seated in J5
"""
import math
import numpy as np
import trimesh
import cadquery as cq
import hw
import params as P
import panel
from geom import box, rbox

WIRE_D = 1.0                     # 26-28 AWG PVC lead, outside diameter
WIRE_PITCH = 1.15                # the pair runs side by side
PCM_LEN = 3.0                    # the protection board, folded at the lead end, inside the pack's 32 mm
LEAD_EXIT_X = None               # where the pair leaves the pack's top edge: None = the middle, as Rev K's pack
LEAD_BEND_R = 1.2                # centre-line bend radius, 1.2 x the wire's diameter
PACK_T = 5.18                    # Rev K's pack (the bay allows P.BATT_T_MAX)


def display(thickness=hw.PANEL_T, front=P.LIP):
    return panel.display(front, thickness)


def battery(thickness=P.BATT_T_MAX):
    """The pack's envelope for clearance checks: the max thickness, lying on the lid's floor."""
    x0, x1 = P.BATT['x']
    y0, y1 = P.BATT['y']
    z0 = P.BATT_FLOOR
    return rbox(x0, x1, y0, y1, z0, z0 + thickness, 0.6)


def plug_box():
    """JST PHR-2 housing seated in J5's side-entry mouth (J5 opens toward -X), as Rev K."""
    b = hw.bounds('J5')
    x_mouth, yc, zc = b[0], (b[2] + b[3]) / 2, -2.6
    return (x_mouth - 4.0, x_mouth + 1.0, yc - 2.9, yc + 2.9, zc - 1.5, zc + 1.5)


def _rounded(way, radius, step=0.05, radii=None):
    """A polyline with every corner replaced by a circular arc of `radius` (smaller where a leg is short: a leg
    between two corners gives each at most 45% of itself, the first and last legs up to 95%).
    Returns the sampled points and the exact length (straights plus arcs); the radii used go into `radii`."""
    way = [np.asarray(w, float) for w in way]
    pts, length = [way[0]], 0.0
    cur = way[0]
    last = len(way) - 3
    for i, (a, b, c) in enumerate(zip(way, way[1:], way[2:])):
        u, v = b - a, c - b
        la, lb = np.linalg.norm(u), np.linalg.norm(v)
        u, v = u / la, v / lb
        th = math.acos(float(np.clip(np.dot(u, v), -1, 1)))
        if th < 1e-6:
            continue
        trim = min(radius * math.tan(th / 2), la * (0.95 if i == 0 else 0.45), lb * (0.95 if i == last else 0.45))
        r = trim / math.tan(th / 2)
        if radii is not None:
            radii.append(r)
        t0, t1 = b - u * trim, b + v * trim
        seg = np.linalg.norm(t0 - cur)
        n = max(2, int(seg / step))
        pts += list(np.linspace(cur, t0, n)[1:])
        length += seg
        # arc from t0 to t1 about the centre on the inside of the corner
        bis = (v - u) / np.linalg.norm(v - u)
        centre = b + bis * (r / math.cos(th / 2))
        r0, r1 = t0 - centre, t1 - centre
        n = max(3, int(r * th / step))
        for s in np.linspace(0, 1, n)[1:]:
            w = (math.sin((1 - s) * th) * r0 + math.sin(s * th) * r1) / math.sin(th)
            pts.append(centre + w)
        length += r * th
        cur = t1
    seg = np.linalg.norm(way[-1] - cur)
    pts += list(np.linspace(cur, way[-1], max(2, int(seg / step)))[1:])
    length += seg
    return np.array(pts), length


LEAD_T = (40.0, 92.5)             # the tape point: the lead's centre on the midplate's back, at the top of the tape line


def lead_waypoints(exit_x=LEAD_EXIT_X, t=LEAD_T):
    """The pair's centre line. It leaves the middle of the pack's top edge, U-turns up over that edge and runs to the
    tape point T on the midplate's back above J5 (a free span: no hook, nothing on the lid presses it), then fixed along
    the midplate and past the board's round corner down to the plug's height, and turns into the plug's rear face."""
    x0, x1, y0, y1, z0, z1 = plug_box()
    yp = (y0 + y1) / 2
    bx0, bx1 = P.BATT['x']
    by1 = P.BATT['y'][1]
    ex = (bx0 + bx1) / 2 if exit_x is None else exit_x
    zc = P.BATT_FLOOR + PACK_T / 2                   # the pack's mid-thickness
    zf = P.BATT_FRONT + 0.1 + WIRE_D / 2               # just over the pack's face (at its thickest)
    yt = by1 + P.BATT_POCKET_CLR + 0.2 + WIRE_D / 2    # the U-turn, over the pocket's top (0.1 less than before 2026-10-19: the
                                                       # pair's outer wire stands a pitch beyond it and met the top fence)
    zt = P.MID_REAR - WIRE_D / 2 - 0.05                # lying on the midplate's back
    return [(ex, by1, zc), (ex, yt, zc), (ex, yt, zf), (t[0], t[1], zt), (38.9, 86.5, zt), (38.9, 82.2, -2.6),
            (x0 - 0.6, yp, -2.6), (x0, yp, -2.6)]


def lead_path(exit_x=LEAD_EXIT_X):
    return _rounded(lead_waypoints(exit_x), LEAD_BEND_R)


def lead_report():
    pts, L = lead_path()
    radii = []
    _rounded(lead_waypoints(), LEAD_BEND_R, radii=radii)
    xs = (P.BATT['x'][0] + 2.0, (P.BATT['x'][0] + P.BATT['x'][1]) / 2, P.BATT['x'][1] - 2.0)
    lengths = {f'exit_x_{x:g}': round(lead_path(x)[1], 1) for x in xs}
    return {'wire_d': WIRE_D, 'bend_r': LEAD_BEND_R, 'min_bend_r': round(min(radii), 2),
            'reference_exit_x': LEAD_EXIT_X or 'middle',
            'routed_length_mm': round(L, 1), 'length_by_exit_position_mm': lengths,
            'note': "from the cell's end to the plug: a free span to one tape point on the midplate above J5, then fixed "
                    "along the midplate and past the board's round corner into the plug; any spare coiled beside the tape point"}


def _pair(pts):
    """Two wires side by side along the pair's centre line (flat on the pack's face), splaying at the end to J5's
    pins, 2 mm apart in Y."""
    pts = np.asarray(pts)
    tang = np.gradient(pts, axis=0)
    tang /= np.linalg.norm(tang, axis=1)[:, None]
    out = []
    for k in (-1, 1):
        w = []
        for i, (p, t) in enumerate(zip(pts, tang)):
            side = np.cross(t, [0.0, 0.0, 1.0])
            side = side / np.linalg.norm(side) if np.linalg.norm(side) > 1e-6 else np.array([1.0, 0.0, 0.0])
            f = min(1.0, max(0.0, (i - (len(pts) - 45)) / 40))       # splay over the last 2 mm
            w.append(p + k * side * ((WIRE_PITCH / 2) * (1 - f) + 1.0 * f))
        out.append(np.array(w))
    return out


def tube(points, r, sides=12):
    """Closed tube mesh along a polyline."""
    pts = np.asarray(points, float)
    tang = np.gradient(pts, axis=0)
    tang /= np.linalg.norm(tang, axis=1)[:, None]
    ref = np.array([0.0, 0.0, 1.0])
    rings = []
    for p, t in zip(pts, tang):
        a = ref if abs(np.dot(ref, t)) < 0.9 else np.array([1.0, 0.0, 0.0])
        n = np.cross(t, a); n /= np.linalg.norm(n)
        b = np.cross(t, n)
        rings.append([p + r * (math.cos(k * 2 * math.pi / sides) * n + math.sin(k * 2 * math.pi / sides) * b)
                      for k in range(sides)])
    V = [v for ring in rings for v in ring] + [pts[0], pts[-1]]
    F = []
    m = len(rings)
    for i in range(m - 1):
        for k in range(sides):
            a, b = i * sides + k, i * sides + (k + 1) % sides
            c, d = a + sides, b + sides
            F += [(a, c, d), (a, d, b)]
    s0, s1 = len(V) - 2, len(V) - 1
    for k in range(sides):
        F.append((s0, (k + 1) % sides, k))
        F.append((s1, (m - 1) * sides + k, (m - 1) * sides + (k + 1) % sides))
    mesh = trimesh.Trimesh(np.array(V), np.array(F), process=True)
    mesh.fix_normals()
    return mesh


def battery_meshes(thickness=PACK_T):
    """{name: trimesh}: the pouch, its folded protection board, the two wires and the plug."""
    x0, x1 = P.BATT['x']
    y0, y1 = P.BATT['y']
    z0 = P.BATT_FLOOR
    pouch = rbox(x0, x1, y0, y1 - PCM_LEN, z0, z0 + thickness, 1.0)
    pouch = pouch.edges('not |Z').fillet(0.8)
    pcm = rbox(x0 + 0.3, x1 - 0.3, y1 - PCM_LEN, y1, z0 + 0.1, z0 + thickness - 0.1, 0.5)   # the taped end

    def mesh(w):
        v, f = w.val().tessellate(0.02, 0.15)
        return trimesh.Trimesh([p.toTuple() for p in v], f, process=True)

    pts, _ = lead_path()
    wires = _pair(pts)
    bx = plug_box()
    plug = trimesh.creation.box(extents=(bx[1] - bx[0], bx[3] - bx[2], bx[5] - bx[4]),
                                transform=trimesh.transformations.translation_matrix(
                                    ((bx[0] + bx[1]) / 2, (bx[2] + bx[3]) / 2, (bx[4] + bx[5]) / 2)))
    return {'battery_cell': mesh(pouch), 'battery_pcm': mesh(pcm), 'lead_red': tube(wires[0], WIRE_D / 2),
            'lead_black': tube(wires[1], WIRE_D / 2), 'battery_plug': plug}


# ---- the light strip (this variant): its assembled shape, for the clearance checks ------------------------------
# From hardware/reference/light-strip/strip-geometry.json (KiCad frame: X = x - 44.24, Y = 148.25 - y). Layers are
# modelled solid: the stiffened pieces as tape + PI + flex, the bends as the bare flex (0.11) swept along a centre
# line of straights and arcs. Where it matters (fold, seat, J3) the numbers are exact to the drawing.
STRIP_KI = (44.24, 148.25)
STRIP_HINGE = (90.35, 93.975)           # bare hinge between the bar and the top pair's piece (flat)
STRIP_FOOT_END = 9.25                   # the bar+foot piece's stiffener ends here; the neck is bare flex
STRIP_TIP_Y = 23.25                     # contact tip seated in J3 (KiCad 125.0)
STRIP_TAIL_Z = (-0.77, -0.435)          # the stiffened tail in J3's mouth (Z -0.805..-0.37): flex -0.77..-0.66 with
                                        # its F side (fingers, diodes) facing -Z, PI above it toward the board
STRIP_NECK_X = (8.247, 13.76)
DIODE = (2.1, 2.1, 1.1)                 # SOT-323 envelope, either way round
GLASS_EDGE_Y = hw.PANEL_Y0              # 7.05, the 3.68's bottom glass edge
CHIN_LOOP_REACH = 1.65                  # the chin loop's outer face past the glass edge (strip_tail_path)


def strip_data():
    import json
    d = json.loads((hw.ROOT / P.STRIP_JSON).read_text())
    cad = lambda p: (p[0] - STRIP_KI[0], STRIP_KI[1] - p[1])
    return {'outline': [cad(p) for p in d['outline']],
            'pieces': [[cad(p) for p in pc] for pc in d['front_pieces']],
            'leds': [(r['ref'], *cad((r['x'], r['y']))) for r in d['leds']],
            'diodes': [(r['ref'], *cad((r['x'], r['y']))) for r in d['diodes']],
            'hinge': tuple(sorted(STRIP_KI[1] - y for y in d['hinge_y'])),
            'tip_flat': STRIP_KI[1] - d['tip_y'], 'stiff_flat': STRIP_KI[1] - d['stiff_back_y'],
            'foot_end': STRIP_KI[1] - d['foot_b'], 'led': d['led']}


def _turtle(start, heading_deg, segs, step=0.02):
    """Centre line in the (y, z) plane: ('line', length) or ('arc', radius, signed degrees, + = anticlockwise
    seen with +Y right and +Z up). Returns the sampled points and the heading at the end (degrees)."""
    p = np.array(start, float)
    h = math.radians(heading_deg)
    pts = [p.copy()]
    for s in segs:
        if s[0] == 'line':
            d = np.array([math.cos(h), math.sin(h)])
            n = max(1, int(abs(s[1]) / step))
            for i in range(1, n + 1):
                pts.append(p + d * s[1] * i / n)
            p = p + d * s[1]
        else:
            r, a = s[1], math.radians(s[2])
            sg = 1 if a > 0 else -1
            c = p + r * np.array([math.cos(h + sg * math.pi / 2), math.sin(h + sg * math.pi / 2)])
            a0 = h - sg * math.pi / 2
            n = max(2, int(abs(a) * r / step))
            for i in range(1, n + 1):
                t = a0 + a * i / n
                pts.append(c + r * np.array([math.cos(t), math.sin(t)]))
            p = pts[-1].copy()
            h += a
    return np.array(pts), math.degrees(h)


def _path_len(pts):
    return float(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum())


def _band(pts, x0, x1, t=None):
    """The bare flex (thickness t) along a (y, z) centre line, swept across X from x0 to x1."""
    import shapely.geometry as sg
    t = P.STRIP_FLEX if t is None else t
    poly = sg.LineString([tuple(p) for p in pts]).buffer(t / 2, cap_style=2, join_style=1, resolution=8)
    poly = poly.simplify(0.002)
    ring = _clean(list(poly.exterior.coords))
    return cq.Workplane('YZ').polyline(ring).close().extrude(x1 - x0).translate((x0, 0, 0))


def _clean(pts, tol=1e-4):
    out = []
    for p in pts:
        if not out or math.dist(p, out[-1]) > tol:
            out.append(tuple(p))
    while len(out) > 2 and math.dist(out[0], out[-1]) <= tol:
        out.pop()
    return out


def _plan(poly, z0, z1):
    return cq.Workplane('XY').polyline(_clean(poly)).close().extrude(z1 - z0).translate((0, 0, z0))


def strip_fold(rin=P.FOLD_RIN):
    """The fold-back at the bare hinge: the bar's flex (centre line at the bar's flex level) runs on for f, loops
    down through 180 degrees on radius R (inside radius rin), carries on round for theta and turns back on a
    reverse arc of the same radius, so it arrives under the bar at the folded piece's flex level, tape to tape.
    The hinge's 3.625 fixes f: the loop takes the whole hinge at rin 0.63; a tighter fold leaves a straight."""
    z_up = P.STRIP_Z0 + P.STRIP_STACK - P.STRIP_FLEX / 2                   # 3.80
    z_lo = P.STRIP_Z0 - P.STRIP_STACK + P.STRIP_FLEX / 2                   # 3.14
    R = rin + P.STRIP_FLEX / 2
    rise = 2 * R - (z_up - z_lo)
    th = math.degrees(math.acos(1 - rise / (2 * R)))
    L = STRIP_HINGE[1] - STRIP_HINGE[0]
    f = L - (math.pi * R + 2 * R * math.radians(th))
    assert f > -1e-6, (rin, f)
    pts, h = _turtle((STRIP_HINGE[0], z_up), 0.0, [('line', max(f, 0.0)), ('arc', R, -180.0), ('arc', R, -th), ('arc', R, th)])
    return {'pts': pts, 'f': f, 'R': R, 'theta': th, 'y_end': float(pts[-1][0]), 'z_end': float(pts[-1][1]),
            'loop_y_max': float(pts[:, 0].max()) + P.STRIP_FLEX / 2, 'loop_z_min': float(pts[:, 1].min()) - P.STRIP_FLEX / 2,
            'length': _path_len(pts)}


def strip_tail_path(chin_loop=False):
    """The neck and the bare tail: off the foot's end, down over the PS film's end onto the glass ledge, 90 degrees
    over the glass's bottom edge (inside R0.65, as the panel's FPC) and down through the slot; on the back a hairpin
    takes up the slack and a 90-degree bend brings it to the stiffened tail's height at Y 9.25. The bare length is
    the drawing's 13.615 (foot end to tail stiffener), so the hairpin's depth is solved for.
    chin_loop=True: part of the slack goes into a loop in the chin that reaches CHIN_LOOP_REACH past the glass
    edge before the drop (the most the chin's gap allows beside SW9's pin)."""
    d = strip_data()
    L = d['foot_end'] - d['stiff_flat']                                        # 13.615
    h = P.STRIP_FLEX / 2
    z_up = P.STRIP_Z0 + P.STRIP_STACK - h                                      # 3.80
    z_glass = P.LIP - hw.PANEL_T + panel.GLASS_T + h                           # 3.155
    z_ps = P.LIP + h
    z_st = STRIP_TAIL_Z[0] + h                                                 # -0.715
    lead = [(d['foot_end'], z_up), (8.80, z_ps), (8.35, z_glass), (GLASS_EDGE_Y, z_glass)]

    def build(zb):
        if chin_loop:
            ra, rb = 0.6, 0.5
            y_out = GLASS_EDGE_Y - CHIN_LOOP_REACH + h
            segs = [('line', GLASS_EDGE_Y - (y_out + ra)), ('arc', ra, 90.0), ('line', 0.1),
                    ('arc', rb, 90.0), ('arc', rb, -90.0)]
        else:
            segs = [('arc', 0.65 + h, 90.0)]
        a, _ = _turtle(lead[-1], 180.0, segs)
        z_top = a[-1][1]
        ru, r2 = 0.7, 0.7
        segs2 = [('line', z_top - (zb + ru)), ('arc', ru, 180.0), ('line', (z_st - r2) - (zb + ru)), ('arc', r2, -90.0)]
        b, _ = _turtle(a[-1], 270.0, segs2)
        c = np.array([b[-1], [STRIP_FOOT_END, z_st]])
        return np.vstack([np.array(lead), a[1:], b[1:], c[1:]])

    lo, hi = -6.0, z_st - 1.5
    for _ in range(50):
        m = (lo + hi) / 2
        if _path_len(build(m)) > L:
            lo = m
        else:
            hi = m
    pts = build(lo)
    return {'pts': pts, 'length': _path_len(pts), 'flat_length': L, 'hairpin_bottom': float(pts[:, 1].min()) - h,
            'chin_reach': GLASS_EDGE_Y - (float(pts[:, 0].min()) - h),
            'drop_y': float(pts[np.argmin(np.abs(pts[:, 1] - 0.8)), 0])}


def strip(rin=P.FOLD_RIN, chin_loop=False, dx=0.0, dz=0.0, front_dx=0.0):
    """{name: Workplane} for the strip as fitted (dx, dz shift it, for the insertion check). front_dx shifts only the
    stiff front (STRIP_FRONT) and the neck, which hangs off the foot: the strip-at-the-wall case (P.STRIP_WALL_DX), with
    the tail still in J3."""
    d = strip_data()
    z0, st, lh = P.STRIP_Z0, P.STRIP_STACK, P.STRIP_LED_H
    bx0, bx1 = P.STRIP_BAR_X
    lx0, lx1 = P.STRIP_LED_X
    half = d['led']['len'] / 2
    fold = strip_fold(rin)
    ye = fold['y_end']
    top_piece = [(x, ye - (y - STRIP_HINGE[1])) for x, y in d['pieces'][0]]
    out = {'strip_bar': _plan(d['pieces'][1], z0, z0 + st)}
    leds = None
    for ref, x, y in d['leds']:
        if y > STRIP_HINGE[1]:
            continue
        b = box(lx0, lx1, y - half, y + half, z0 + st, z0 + st + lh)
        leds = b if leds is None else leds.union(b)
    out['strip_leds'] = leds
    out['strip_hinge'] = _band(fold['pts'], bx0, bx1)
    out['strip_folded'] = _plan(top_piece, z0 - st, z0)
    fl = None
    for ref, x, y in d['leds']:
        if y < STRIP_HINGE[1]:
            continue
        yf = ye - (y - STRIP_HINGE[1])
        b = box(lx0, lx1, yf - half, yf + half, z0 - st - lh, z0 - st)
        fl = b if fl is None else fl.union(b)
    out['strip_folded_leds'] = fl
    tp = strip_tail_path(chin_loop)
    out['strip_neck'] = _band(tp['pts'], *STRIP_NECK_X)
    # the stiffened tail: the flat outline between the tip and the stiffener's start, turned onto the board's back
    import shapely.geometry as sg
    poly = sg.Polygon(d['outline']).intersection(sg.box(-5, d['tip_flat'] - 0.01, 20, d['stiff_flat']))
    poly = max(getattr(poly, 'geoms', [poly]), key=lambda g: g.area)
    seat = lambda y: STRIP_FOOT_END + (d['stiff_flat'] - y)
    ring = [(x, seat(y)) for x, y in list(poly.exterior.coords)[:-1]]
    out['strip_tail'] = _plan(ring, *STRIP_TAIL_Z)
    dd = None
    for ref, x, y in d['diodes']:
        ys = seat(y)
        b = box(x - DIODE[0] / 2, x + DIODE[0] / 2, ys - DIODE[1] / 2, ys + DIODE[1] / 2, STRIP_TAIL_Z[0] - DIODE[2], STRIP_TAIL_Z[0])
        dd = b if dd is None else dd.union(b)
    out['strip_diodes'] = dd
    if front_dx:
        out = {k: (v.translate((front_dx, 0, 0)) if k in STRIP_FRONT or k == 'strip_neck' else v) for k, v in out.items()}
    if dx or dz:
        out = {k: v.translate((dx, 0, dz)) for k, v in out.items()}
    return out


STRIP_FRONT = ('strip_bar', 'strip_leds', 'strip_hinge', 'strip_folded', 'strip_folded_leds')


def strip_front(rin=P.FOLD_RIN, dx=0.0, dz=0.0):
    """The stiff part that goes into the channel as one: bar and foot, its LEDs, the hinge loop and the folded
    pair (the neck and the tail are flexible and follow)."""
    s = strip(rin, dx=dx, dz=dz)
    u = s[STRIP_FRONT[0]]
    for k in STRIP_FRONT[1:]:
        u = u.union(s[k])
    return u


def strip_report(rin=P.FOLD_RIN):
    d = strip_data()
    f = strip_fold(rin)
    ye = f['y_end']
    fold_leds = {ref: [round(ye - (y - STRIP_HINGE[1]) - 2.0, 3), round(ye - (y - STRIP_HINGE[1]) + 2.0, 3)]
                 for ref, x, y in d['leds'] if y > STRIP_HINGE[1]}
    piece = [ye - (y - STRIP_HINGE[1]) for x, y in d['pieces'][0]]
    rows = {}
    for chin in (False, True):
        t = strip_tail_path(chin)
        rows['chin_loop' if chin else 'back_loop'] = {'bare_length': round(t['length'], 3), 'flat_length': round(t['flat_length'], 3),
                                                      'hairpin_bottom_z': round(t['hairpin_bottom'], 3),
                                                      'reach_past_glass_edge': round(t['chin_reach'], 3),
                                                      'drop_y': round(t['drop_y'], 3)}
    return {'fold_inside_radius': rin, 'fold_R_centre': round(f['R'], 4), 'fold_straight_f': round(f['f'], 3),
            'fold_theta_deg': round(f['theta'], 2), 'folded_piece_y': [round(min(piece), 3), round(max(piece), 3)],
            'loop_y_max': round(f['loop_y_max'], 3), 'loop_z_min': round(f['loop_z_min'], 3), 'hinge_len': round(f['length'], 3),
            'folded_leds_y': fold_leds, 'tail': rows}


if __name__ == '__main__':
    import json
    print(json.dumps(lead_report(), indent=1))
    bm = battery_meshes()
    for k, v in bm.items():
        print(k, len(v.faces), np.round(v.bounds, 2).tolist())
    cq.exporters.export(display(), str(hw.OUT / 'ref_display.stl'), tolerance=0.02)
    cq.exporters.export(battery(), str(hw.OUT / 'ref_battery.stl'), tolerance=0.02)
