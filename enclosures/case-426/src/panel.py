"""GDEQ0426T82-FT01C touch + frontlight panel, 1:1 from the supplied drawing
(hardware/reference/GDEQ0426T82-FT01C.pdf; its vector geometry is read by
hardware/reference/extract/), in its assembled position: front surface against the bezel lip,
ribbons folded past the glass's bottom edge, down through the PCB slot and along the back of
the board into J2 (EPD), J3 (frontlight) and J4 (touch).

Drawing frame: u across from the EPD's left edge, v up from its bottom edge (front view).
CAD frame: X = PANEL_X0 + u, Y = PANEL_Y0 + v.
"""
import math
import numpy as np
import cadquery as cq
import shapely.geometry as sg
import trimesh
import hw
import params as P
from geom import box

# ---- stack (side view), front to back; the drawing gives 1.98 +-0.2 in total -------------
# EPD is listed as 0.93; 0.92 keeps the stack at its stated 1.98.
LAYERS = [('touch', 0.30), ('oca2', 0.18), ('lgp', 0.40), ('oca3', 0.18), ('epd', 0.92)]
GLASS_T = 0.64                  # TFT glass inside the EPD; the EPD ribbon is bonded on its front
# outlines (u0, u1, v0, v1) from the front-view dimensions
EPD = (0.0, 62.37, 0.0, 105.33)
LGP = (62.37 - 0.47 - 61.40, 62.37 - 0.47, 105.33 - 0.15 - 103.60, 105.33 - 0.15)
TOUCH = (62.37 - 0.42 - 61.50, 62.37 - 0.42, 105.33 - 0.43 - 99.70, 105.33 - 0.43)
FPL = (0.25, 62.12, 1.20, 104.51)                     # front plane on the glass (side view)
ACTIVE = (3.345, 3.345 + 55.68, 9.815, 9.815 + 92.8)


def z_levels(front=P.LIP, total=hw.PANEL_T):
    """{layer: (z0, z1)} with the front surface at `front`; thickness tolerance goes to the EPD."""
    out, z = {}, front
    for name, t in LAYERS:
        if name == 'epd':
            t += total - hw.PANEL_T
        out[name] = (z - t, z)
        z -= t
    out['glass'] = (z, z + GLASS_T)
    out['fpl'] = (z + GLASS_T, out['epd'][1])
    return out


def rect(o, z0, z1):
    u0, u1, v0, v1 = o
    return box(hw.PANEL_X0 + u0, hw.PANEL_X0 + u1, hw.PANEL_Y0 + v0, hw.PANEL_Y0 + v1, z0, z1)


def body(front=P.LIP, total=hw.PANEL_T):
    """The panel stack as named solids."""
    z = z_levels(front, total)
    return {'glass': rect(EPD, *z['glass']), 'fpl': rect(FPL, *z['fpl']),
            'oca3': rect(LGP, *z['oca3']), 'lgp': rect(LGP, *z['lgp']),
            'oca2': rect(TOUCH, *z['oca2']), 'touch': rect(TOUCH, *z['touch'])}


def display(front=P.LIP, total=hw.PANEL_T):
    parts = list(body(front, total).values())
    s = parts[0]
    for p in parts[1:]:
        s = s.union(p)
    return s


# ---- ribbons (front view outlines, v <= 0 is beyond the glass edge) -----------------------
RIBBONS = {
    'light': dict(conn='J3', t=0.10, depth_below_front=0.44,
                  poly=[(9.97, 0.0), (13.48, 0.0), (13.48, -24.01), (13.24, -24.33), (10.29, -24.33), (9.97, -24.01)],
                  stiff=[(-21.0, -24.33, 0.20)]),
    'main': dict(conn='J2', t=0.12, on_glass=True,
                 poly=[(17.87, 0.0), (41.32, 0.0), (41.32, -14.68), (37.34, -16.45), (37.34, -24.01),
                       (24.81, -24.01), (24.81, -16.45), (17.87, -13.56)],
                 stiff=[(-18.0, -24.01, 0.18)], bend_area=(-0.40, -3.03)),
    'touch': dict(conn='J4', t=0.10, depth_below_front=0.05,
                  poly=[(46.35, 0.0), (52.33, 0.0), (52.33, -8.86), (54.33, -10.05), (54.33, -20.02), (51.14, -20.02),
                        (51.14, -24.01), (50.82, -24.33), (47.95, -24.33), (47.63, -24.01), (47.63, -20.02),
                        (44.36, -20.02), (44.36, -10.05), (46.35, -8.86)],
                  stiff=[(-10.05, -20.02, 0.15), (-21.0, -24.33, 0.20)],
                  ic=dict(u=(47.31, 52.25), v=(-17.55, -12.53), h=0.55)),
}
BEND_R = 0.65                   # centre-line radius of every fold (inner ~0.6 mm)
INSERT = 2.6                    # ribbon end sits this far inside the connector mouth
Z_REAR = -0.45                  # ribbon height along the back of the board (connector entry)


def slot():
    """The PCB's ribbon slot (x0, x1, y0, y1), measured from the board solid."""
    return (7.021, 54.06, 5.75, 7.05)


def exit_z(name, front=P.LIP, total=hw.PANEL_T):
    r = RIBBONS[name]
    if r.get('on_glass'):
        return z_levels(front, total)['glass'][1] + r['t'] / 2
    return front - r['depth_below_front']


def flat_length(name):
    return -min(v for u, v in RIBBONS[name]['poly'])


def width_at(name, v):
    """u-interval of the flat ribbon at height v."""
    poly = sg.Polygon(RIBBONS[name]['poly'])
    line = poly.intersection(sg.LineString([(-10, v), (80, v)]))
    if line.is_empty:
        return None
    xs = [c[0] for g in getattr(line, 'geoms', [line]) for c in g.coords]
    return min(xs), max(xs)


class Path:
    """Centre line of one ribbon in the (y, z) plane, sampled with arc length."""

    def __init__(self, name, front=P.LIP, total=hw.PANEL_T, ze=None, z_glass=None):
        # ze, z_glass (light-strip variant): the exit height and the glass's rear for a panel that is not
        # the FT01C stack (refs.plain_fpc: the plain GDEY0426T82's EPD FPC on its 0.5 glass)
        self.name = name
        R = BEND_R
        ye = hw.PANEL_Y0
        ze = exit_z(name, front, total) if ze is None else ze
        zg = z_levels(front, total)['glass'][0] if z_glass is None else z_glass
        z_s = min(zg + 0.05, ze - R)                         # where the S-bend starts
        s0, s1, y0, y1 = slot()[0], slot()[1], slot()[2], slot()[3]
        yv = (y0 + y1) / 2                                   # straight down the slot's centre
        mouth = hw.bounds(RIBBONS[name]['conn'])[2]
        self.mouth, self.tip_target = mouth, mouth + INSERT
        pts = []

        def arc(cy, cz, a0, a1, n=40):
            for i in range(n + 1):
                a = math.radians(a0 + (a1 - a0) * i / n)
                pts.append((cy + R * math.cos(a), cz + R * math.sin(a)))

        def line(p, q, n=10):
            for i in range(1, n + 1):
                pts.append((p[0] + (q[0] - p[0]) * i / n, p[1] + (q[1] - p[1]) * i / n))

        arc(ye, ze - R, 90, 180)                             # over the glass edge, heading down
        line(pts[-1], (ye - R, z_s))
        arc(ye, z_s, 180, 270)                               # under the glass edge, heading in
        line(pts[-1], (yv - R, z_s - R))
        arc(yv - R, z_s - 2 * R, 90, 0)                      # down into the slot
        line(pts[-1], (yv, Z_REAR + R), 20)
        arc(yv + R, Z_REAR + R, 180, 270)                    # along the back of the board
        self.pre = np.array(pts)
        self.rear_y0 = yv + R
        L0 = self._length(self.pre)
        self.fold_length = L0
        straight = self.tip_target - self.rear_y0
        self.slack = flat_length(name) - L0 - straight
        # take the slack up as a gentle bow away from the board between the slot and the connector
        ya, yb = self.rear_y0 + 1.0, mouth - 1.0
        self.bow = (ya, yb, self._solve_bow(ya, yb, max(self.slack, 0.0)))
        self.pts = np.vstack([self.pre, self._rear(n=240)])
        seg = np.linalg.norm(np.diff(self.pts, axis=0), axis=1)
        self.s = np.concatenate([[0.0], np.cumsum(seg)])

    @staticmethod
    def _length(p):
        return float(np.sum(np.linalg.norm(np.diff(p, axis=0), axis=1)))

    def _bow_z(self, y, ya, yb, h):
        if y <= ya or y >= yb:
            return Z_REAR
        return Z_REAR - h * (1 - math.cos(2 * math.pi * (y - ya) / (yb - ya))) / 2

    def _solve_bow(self, ya, yb, extra):
        if extra <= 0:
            return 0.0
        lo, hi = 0.0, 8.0
        ys = np.linspace(ya, yb, 400)
        for _ in range(50):
            h = (lo + hi) / 2
            zs = [self._bow_z(y, ya, yb, h) for y in ys]
            if self._length(np.column_stack([ys, zs])) - (yb - ya) < extra:
                lo = h
            else:
                hi = h
        return (lo + hi) / 2

    def _rear(self, n):
        ya, yb, h = self.bow
        ys = np.linspace(self.rear_y0, self.tip_target + 1.0, n)[1:]
        return np.array([(y, self._bow_z(y, ya, yb, h)) for y in ys])

    def at(self, s):
        """(y, z), unit tangent and front-face normal at arc length s."""
        i = int(np.clip(np.searchsorted(self.s, s) - 1, 0, len(self.s) - 2))
        f = (s - self.s[i]) / max(1e-9, self.s[i + 1] - self.s[i])
        p = self.pts[i] + f * (self.pts[i + 1] - self.pts[i])
        t = self.pts[i + 1] - self.pts[i]
        t = t / np.linalg.norm(t)
        n = np.array([t[1], -t[0]])                          # front face: +Z at the exit, -Z along the back
        return p, t, n

    def report(self):
        ya, yb, h = self.bow
        return {'flat_length_mm': round(flat_length(self.name), 2), 'fold_length_mm': round(self.fold_length, 2),
                'connector': RIBBONS[self.name]['conn'], 'mouth_y': round(self.mouth, 2),
                'slack_mm': round(self.slack, 2), 'bow_height_mm': round(h, 2), 'exit_z': round(self.pre[0][1], 2)}


def _strip(path, name, u_range_fn, back_extra_fn, front_off, s_range, ds=0.08):
    """Watertight mesh of a ribbon (or a part on it) following `path` between s_range."""
    ss = np.arange(s_range[0], s_range[1], ds).tolist() + [s_range[1] - 1e-6]
    rows = []
    for s in ss:
        w = u_range_fn(s)
        if w is None:
            continue
        p, t, n = path.at(s)
        lo, hi = front_off(s)
        lo -= back_extra_fn(s)
        a = [(hw.PANEL_X0 + w[0], *(p + n * lo)), (hw.PANEL_X0 + w[1], *(p + n * lo)),
             (hw.PANEL_X0 + w[1], *(p + n * hi)), (hw.PANEL_X0 + w[0], *(p + n * hi))]
        rows.append(a)
    V, F = [], []
    for r in rows:
        V.extend(r)
    m = len(rows)
    for i in range(m - 1):
        a, b = 4 * i, 4 * (i + 1)
        for k in range(4):
            k2 = (k + 1) % 4
            F.append((a + k, b + k, b + k2))
            F.append((a + k, b + k2, a + k2))
    F.append((0, 2, 1)); F.append((0, 3, 2))
    e = 4 * (m - 1)
    F.append((e, e + 1, e + 2)); F.append((e, e + 2, e + 3))
    mesh = trimesh.Trimesh(np.array(V), np.array(F), process=True)
    mesh.fix_normals()
    return mesh


def ribbons(front=P.LIP, total=hw.PANEL_T):
    """{name: trimesh} for the three ribbons in their installed shape, plus the touch IC."""
    out = {}
    for name, r in RIBBONS.items():
        path = Path(name, front, total)
        L = flat_length(name)

        def back_extra(s, r=r):
            v = -s
            return sum(t for (va, vb, t) in r['stiff'] if vb <= v <= va)

        out[name] = _strip(path, name, lambda s, name=name: width_at(name, -s),
                           back_extra, lambda s, r=r: (-r['t'] / 2, r['t'] / 2), (0.0, L))
        if 'ic' in r:
            ic = r['ic']
            out[name + '_ic'] = _strip(path, name, lambda s, ic=ic: ic['u'],
                                       lambda s: 0.0, lambda s, r=r, ic=ic: (r['t'] / 2, r['t'] / 2 + ic['h']),
                                       (-ic['v'][1], -ic['v'][0]))
    return out


def report(front=P.LIP, total=hw.PANEL_T):
    return {name: Path(name, front, total).report() for name in RIBBONS}


if __name__ == '__main__':
    import json
    print(json.dumps(report(), indent=1))
    for dt in (-0.2, 0.2):
        print('panel', dt, {k: v['slack_mm'] for k, v in report(total=hw.PANEL_T + dt).items()})
    rb = ribbons()
    for k, m in rb.items():
        print(k, len(m.faces), 'watertight', m.is_watertight, np.round(m.bounds, 2).tolist())
