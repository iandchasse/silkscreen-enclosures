"""Reference parts that are not printed, in their assembled positions.

display  the GDEQ0426T82-FT01C stack from panel.py (drawn 1:1 from the supplied drawing)
plain    the plain GDEY0426T82 (0.926) the light-strip variant takes, PS face at PLAIN_FRONT, and its EPD FPC
strip    the light strip from strip-geometry.json: the bar, the top-pair piece and the hinge as solids on
         the PS, its LEDs, and the tail (neck, U round the glass edge, slot, back run, stiffened end with
         the diodes) as meshes along a path whose spare length goes into the U (STRIP_TAIL)
battery  the site's 503035 model (copied from battery-connected-mm.stl into
         hardware/), moved from the site's placement into this case's battery fence, with its
         pigtail re-routed to J5 and a JST PHR-2 plug seated in J5's mouth
"""
import math
import numpy as np
import trimesh
import cadquery as cq
import hw
import params as P
import panel
from geom import box, rbox


def display(thickness=hw.PANEL_T, front=P.LIP):
    return panel.display(front, thickness)


def battery():
    """Envelope of the cell and its wrap (for clearance checks)."""
    x0, x1 = P.BATT['x']
    y0, y1 = P.BATT['y']
    z0, z1 = P.BATT['z']
    return rbox(x0, x1, y0, y1, z0, z1, 1.0)


def _bezier(p0, p1, p2, p3, n=60):
    t = np.linspace(0, 1, n)[:, None]
    return ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * t * t * p2 + t ** 3 * p3


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


def plug_box():
    """JST PHR-2 housing seated in J5's side-entry mouth (J5 opens toward -X)."""
    b = hw.bounds('J5')
    x_mouth, yc, zc = b[0], (b[2] + b[3]) / 2, -2.6
    return (x_mouth - 4.0, x_mouth + 1.0, yc - 2.9, yc + 2.9, zc - 1.5, zc + 1.5)


def battery_meshes():
    """{name: trimesh}: cell (with wrap and protection board) and the pigtail with its plug."""
    m = trimesh.load(hw.HW / 'battery-connected-mm.stl')
    bodies = [b for b in m.split(only_watertight=False) if len(b.faces) >= 12]
    # the site model's own wires are tubes of 960 faces; drop them and re-route below
    cell = trimesh.util.concatenate([b for b in bodies if len(b.faces) != 960])
    cell.apply_translation(P.BATT_MODEL_SHIFT)
    sx, sy, sz = P.BATT_MODEL_SHIFT
    x0, x1, y0, y1, z0, z1 = plug_box()
    zc = (z0 + z1) / 2
    out = {'battery_cell': cell}
    # Rev H: the leads leave between the midplate's right posts, drop behind the board's notch edge,
    # run down outboard of the lower cleat and come into the plug from the notch side. Spare lead
    # (a real pack's is longer than this) winds on the two cleats.
    wires = []
    for (ex, ey), py, dx in (((38.06, 96.5), (y0 + y1) / 2 + 0.6, 0.0), ((37.06, 95.0), (y0 + y1) / 2 - 0.6, 0.75)):
        p0 = np.array([ex + sx, ey + sy, -1.8 + sz])
        way = [p0, p0 + np.array([1.2, -0.4, -0.5]), np.array([41.0 + dx, 93.0, zc]), np.array([41.0 + dx, 86.0, zc]),
               np.array([39.3, 82.9 + 0.6 * (py > (y0 + y1) / 2), zc]), np.array([x0 - 0.8, py, zc]), np.array([x0, py, zc])]
        path = np.vstack([_bezier(a, a + (b - a) / 3, b - (b - a) / 3, b, 12)[:-1] for a, b in zip(way, way[1:])] + [way[-1]])
        # smooth the polyline's corners a little so the tube does not self-intersect
        for _ in range(3):
            path[1:-1] = (path[:-2] + 2 * path[1:-1] + path[2:]) / 4
        wires.append(tube(path, 0.35))
    out['battery_leads'] = trimesh.util.concatenate(wires)
    out['battery_plug'] = trimesh.creation.box(extents=(x1 - x0, y1 - y0, z1 - z0),
                                               transform=trimesh.transformations.translation_matrix(((x0 + x1) / 2, (y0 + y1) / 2, zc)))
    return out


# ---- light-strip variant ------------------------------------------------------------------------
import json
import shapely.geometry as sg


def _cad(pt):
    """KiCad (x, y) -> CAD (X, Y), hw.py's frame."""
    return (pt[0] - 44.24, 148.25 - pt[1])


_GEO = None


def strip_geometry():
    global _GEO
    if _GEO is None:
        _GEO = json.loads((hw.ROOT / P.STRIP_GEOMETRY).read_text())
    return _GEO


def plain_body(front=P.PLAIN_FRONT, total=P.PLAIN['t']):
    """The plain panel's layers as named solids, PS face at `front`; thickness tolerance goes to the glass."""
    L = P.PLAIN
    ps0, fpl0 = front - L['ps'], front - L['ps'] - L['fpl']
    rear = front - total

    def inset(i, z0, z1):
        l, r, t, b = i
        return box(hw.PANEL_X0 + l, hw.PANEL_X1 - r, hw.PANEL_Y0 + b, hw.PANEL_Y1 - t, z0, z1)
    return {'glass': box(hw.PANEL_X0, hw.PANEL_X1, hw.PANEL_Y0, hw.PANEL_Y1, rear, fpl0),
            'fpl': inset(L['fpl_inset'], fpl0, ps0), 'ps': inset(L['ps_inset'], ps0, front)}


def plain_display(total=P.PLAIN['t'], front=P.PLAIN_FRONT):
    parts = list(plain_body(front, total).values())
    s = parts[0]
    for p in parts[1:]:
        s = s.union(p)
    return s


def plain_fpc():
    """The plain panel's EPD FPC (mesh), on its glass, round the edge and through the slot into J2, on
    panel.py's path for the FT01C's EPD ribbon (the same GDEY0426T82 underneath)."""
    t = P.PLAIN['fpc_t']
    zg = P.PLAIN_FRONT - P.PLAIN['t']
    path = panel.Path('main', ze=zg + P.PLAIN['glass'] + t / 2, z_glass=zg)
    poly = sg.Polygon(P.PLAIN['fpc_poly'])
    L = -min(v for u, v in P.PLAIN['fpc_poly'])

    def width(s):
        line = poly.intersection(sg.LineString([(-10, -s), (80, -s)]))
        if line.is_empty:
            return None
        xs = [c[0] for g in getattr(line, 'geoms', [line]) for c in g.coords]
        return min(xs), max(xs)
    stiff = panel.RIBBONS['main']['stiff']
    return panel._strip(path, 'main', width, lambda s: sum(k for (va, vb, k) in stiff if vb <= -s <= va),
                        lambda s: (-t / 2, t / 2), (0.0, L))


def _extrude(pts, z0, z1):
    out = []
    for p in pts:                                            # drop repeated points (the export has some)
        if not out or abs(p[0] - out[-1][0]) + abs(p[1] - out[-1][1]) > 1e-4:
            out.append(tuple(p))
    pts = out[:-1] if abs(out[0][0] - out[-1][0]) + abs(out[0][1] - out[-1][1]) <= 1e-4 else out
    return cq.Workplane('XY').polyline(pts).close().extrude(z1 - z0).translate((0, 0, z0))


def strip_front():
    """{name: Workplane} of the strip's parts on the panel's front: 'strip_bar' - the top-pair piece and the
    bar + foot (tape, PI and flex, PLAIN_FRONT..STRIP_FLEX_TOP) and the bare-flex hinge between them (flex
    only, at the pieces' flex level) - 'strip_leds', the twelve LED bodies, and 'strip_copper', their 24
    solder pads (P.STRIP_COPPER) as columns from the flex top to the LEDs' top (pad, fillet and terminal)."""
    g = strip_geometry()
    S = P.STRIP_STACK
    bar = None
    for piece in g['front_pieces']:
        w = _extrude([_cad(p) for p in piece], P.PLAIN_FRONT, P.STRIP_FLEX_TOP)
        bar = w if bar is None else bar.union(w)
    h0, h1 = sorted(g['hinge_y'])
    hinge = sg.Polygon(g['outline']).intersection(sg.box(0, h0 - 0.01, 200, h1 + 0.01))
    bar = bar.union(_extrude([_cad(p) for p in hinge.exterior.coords], P.STRIP_FLEX_TOP - S['flex'], P.STRIP_FLEX_TOP))
    led = g['led']
    leds, cu = None, None
    Cu = P.STRIP_COPPER
    for d in g['leds']:
        x, y = _cad((d['x'], d['y']))
        b = box(x - led['rear_behind'], x + led['face_ahead'], y - led['len'] / 2, y + led['len'] / 2,
                P.STRIP_FLEX_TOP, P.STRIP_LED_TOP)
        leds = b if leds is None else leds.union(b)
        for s in (-1, 1):                                    # the two solder pads, as columns to the LED's top
            ya, yb = sorted((y + s * Cu['y'][0], y + s * Cu['y'][1]))
            c = box(x + Cu['x'][0], x + Cu['x'][1], ya, yb, P.STRIP_FLEX_TOP, P.STRIP_LED_TOP)
            cu = c if cu is None else cu.union(c)
    return {'strip_bar': bar, 'strip_leds': leds, 'strip_copper': cu}


class StripPath:
    """Mid-plane of the strip's tail in the (y, z) plane, from the foot's end (s = 0) to the contact tip:
    down onto the glass ledge (STRIP_DRAPE), over the glass's bottom edge and round it in a U of inside
    radius R1, back under the glass, down the slot (R2 in, R3 out onto the back), along the board's back,
    and the stiffened end up into J3's mouth. The flex's flat length from the foot to the tip is fixed, so
    the U takes whatever the rest does not use: o is how far its straight top leg runs past the edge."""

    def __init__(self, case='nominal'):
        g = strip_geometry()
        C = P.STRIP_TAIL[case]
        S = P.STRIP_STACK
        H = S['flex'] / 2
        self.case, self.C, self.H = case, C, H
        r1, r2, r3 = C['R1'] + H, C['R2'] + H, C['R3'] + H
        yd, tip = C['yd'], C['tip']
        self.ye = ye = hw.PANEL_Y0                               # the glass's bottom edge
        self.z_ledge = zl = P.PLAIN_FRONT - P.PLAIN['t'] + P.PLAIN['glass'] + H
        self.yf = yf = _cad((0, g['foot_b']))[1]                 # the foot's (stiffener's) end, 9.25
        zf = P.STRIP_FLEX_TOP - H
        self.z_leg = z_leg = zl - 2 * r1
        zb = -H                                                  # bare flex on the board's back
        tstack = S['pi'] + S['flex']
        z_st = -(S['pi'] + H)                                    # flex mid where the stiffened end lies on the board
        z_tip = P.STRIP_J3_MID - tstack / 2 + H                  # ... and at the tip, in J3's mouth
        self.extra = C.get('extra', 0.0)                         # more bare flex than drawn, taken up in the U
        self.L = g['tip_y'] - g['foot_b'] + self.extra           # flat length, foot to tip (27.615)
        self.s_stiff = g['stiff_back_y'] - g['foot_b']           # where the back stiffener starts
        Lst = g['tip_y'] - g['stiff_back_y']
        y_st = tip - math.sqrt(Lst ** 2 - (z_tip - z_st) ** 2)
        self.y_st, self.z_st, self.z_tip = y_st, z_st, z_tip

        def build(o):
            pts = [(yf, zf)]

            def line(q, n=12):
                p0 = pts[-1]
                for i in range(1, n + 1):
                    pts.append((p0[0] + (q[0] - p0[0]) * i / n, p0[1] + (q[1] - p0[1]) * i / n))

            def arc(cy, cz, r, a0, a1, n=48):
                for i in range(1, n + 1):
                    a = math.radians(a0 + (a1 - a0) * i / n)
                    pts.append((cy + r * math.cos(a), cz + r * math.sin(a)))
            line((yf - P.STRIP_DRAPE, zl))
            line((ye - o, zl))
            arc(ye - o, zl - r1, r1, 90, 270)
            line((yd - r2, z_leg))
            arc(yd - r2, z_leg - r2, r2, 90, 0, 24)
            line((yd, zb + r3), 20)
            arc(yd + r3, zb + r3, r3, 180, 270, 24)
            line((y_st - 1.0, zb), 20)
            line((y_st, z_st), 10)
            line((tip, z_tip), 60)
            line((tip + 1.0, z_tip + (z_tip - z_st) / (tip - y_st)), 4)
            return np.array(pts)

        def length_to_tip(pts):
            seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
            k = int(np.argmin(np.abs(pts[:, 0] - tip) + 100 * (pts[:, 0] < y_st)))
            return float(seg[:k].sum())
        L0 = length_to_tip(build(0.0))
        self.o = (self.L - L0) / 2                               # the U's straight top leg past the edge
        if self.o < 0:
            raise ValueError(f'strip tail {case}: {-2 * self.o:.2f} mm short')
        self.pts = build(self.o)
        seg = np.linalg.norm(np.diff(self.pts, axis=0), axis=1)
        self.s = np.concatenate([[0.0], np.cumsum(seg)])
        self.u_reach_y = ye - self.o - r1 - H                    # the U's outermost face
        self.u_bottom_z = z_leg - H

    at = panel.Path.at

    def flat(self, s):
        """Flat-pattern distance from the foot's end of the point at path length s (the extra flex sits
        in the U, after the neck's fillet)."""
        return s - self.extra if s > 3.0 else s

    def report(self):
        return {'case': self.case, **self.C, 'u_top_leg_past_edge': round(self.o, 3),
                'u_reach_past_edge': round(self.ye - self.u_reach_y, 3), 'u_outer_y': round(self.u_reach_y, 3),
                'u_bottom_face_z': round(self.u_bottom_z, 3), 'stiffened_from_y': round(self.y_st, 3),
                'tip_flex_mid_z': round(self.z_tip, 3)}


def strip_tail(case='nominal'):
    """({name: trimesh}, path): the tail (bare flex from the foot's end, with the PI stiffener on its B side
    over the last 14 mm) and the two SOT-323 diodes on its F side (away from the board on the back run)."""
    g = strip_geometry()
    path = StripPath(case)
    outline = sg.Polygon(g['outline'])
    H = path.H

    def width(s):
        y = g['foot_b'] + path.flat(s)
        line = outline.intersection(sg.LineString([(0, y), (120, y)]))
        if line.is_empty:
            return None
        xs = [c[0] for gg in getattr(line, 'geoms', [line]) for c in gg.coords]
        return min(xs) - 44.24 - hw.PANEL_X0, max(xs) - 44.24 - hw.PANEL_X0
    pi = P.STRIP_STACK['pi']
    out = {'strip_tail': panel._strip(path, 'strip', width,
                                      lambda s: pi if path.flat(s) >= path.s_stiff - 1e-6 else 0.0,
                                      lambda s: (-H, H), (0.0, path.L - 1e-3), ds=0.05)}
    D = P.STRIP_DIODE
    ds = []
    for d in g['diodes']:
        x = d['x'] - 44.24
        sc = d['y'] - g['foot_b'] + path.extra
        ds.append(panel._strip(path, 'diode', lambda s, x=x: (x - D['w'] / 2 - hw.PANEL_X0, x + D['w'] / 2 - hw.PANEL_X0),
                               lambda s: 0.0, lambda s: (H, H + D['h']), (sc - D['l'] / 2, sc + D['l'] / 2), ds=0.1))
    out['strip_diodes'] = trimesh.util.concatenate(ds)
    return out, path


if __name__ == '__main__':
    if P.LIGHT_STRIP:
        for case in P.STRIP_TAIL:
            m, sp = strip_tail(case)
            print(sp.report())
            for k, v in m.items():
                print(' ', k, len(v.faces), 'watertight', v.is_watertight, 'vol', round(v.volume, 3), np.round(v.bounds, 3).tolist())
        fm = plain_fpc()
        print('plain_fpc', fm.is_watertight, np.round(fm.bounds, 3).tolist())
        for k, v in strip_front().items():
            b = v.val().BoundingBox()
            print(k, len(v.solids().vals()), round(v.val().Volume(), 3), [round(a, 3) for a in (b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax)])
        for k, v in plain_body().items():
            b = v.val().BoundingBox()
            print(k, [round(a, 3) for a in (b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax)])
    bm = battery_meshes()
    for k, v in bm.items():
        print(k, len(v.faces), np.round(v.bounds, 2).tolist())
    # the panel this variant holds, as build.py writes it
    cq.exporters.export(plain_display() if P.LIGHT_STRIP else display(), str(P.OUT / 'ref_display.stl'), tolerance=0.02)
    cq.exporters.export(battery(), str(P.OUT / 'ref_battery.stl'), tolerance=0.02)
