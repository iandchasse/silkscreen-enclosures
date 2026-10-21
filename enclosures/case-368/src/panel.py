"""The 3.68-inch 528 x 792 bare EPD (x3), from the supplied drawing
(hardware/reference/panel-3p68.png), in its assembled position: front surface against the bezel
lip, its one 24-pin FPC folded over the glass's bottom edge, straight down through the PCB slot and along
the back of the board into J2.

Drawing frame: u across from the panel's left edge, v up from its bottom edge (front view).
CAD frame: X = PANEL_X0 + u, Y = PANEL_Y0 + v.

From the drawing:
  outline 56.24 x 86.54 +-0.2, 0.87 +-0.1 thick: PS film 0.20, EPL 0.17, TFT glass 0.50, front to back
  PS film 54.94 x 84.11 (0.65 in from the top and sides), EPL 53.14 x 82.01 (1.55 in),
  active area 51.84 x 77.76 (2.20 in); so at the bottom, where the FPC leaves, 1.78 / 2.98 / 6.58
  FPC 22.36 +-0.3 long from the glass edge, 0.10 +-0.03 thick; its 12.50 wide terminal starts 21.87 from
  the left edge, so it is centred; FPC + stiffener 0.30 +-0.05 at the terminal
Read off the drawing's picture (not dimensioned): the neck is ~15.9 wide for its first ~6 mm, then the
tail's 12.5; the stiffened end is ~5 mm. No bend radius is given: the fold is modelled at R0.65, as Rev K.
The drawing does not say which face the contacts are on relative to J2's; check that before ordering.
"""
import math
import numpy as np
import cadquery as cq
import shapely.geometry as sg
import trimesh
import hw
import params as P
from geom import box

# ---- stack (side view), front to back: 0.87 +-0.1 ----------------------------------------------
LAYERS = [('ps', 0.20), ('epl', 0.17), ('glass', 0.50)]
GLASS_T = 0.50                  # TFT glass; the FPC is bonded on its front face below the EPL
# outlines (u0, u1, v0, v1) from the front-view dimensions
EPD = (0.0, 56.24, 0.0, 86.54)
PS = (0.65, 56.24 - 0.65, 86.54 - 0.65 - 84.11, 86.54 - 0.65)        # 54.94 x 84.11
EPL = (1.55, 56.24 - 1.55, 86.54 - 1.55 - 82.01, 86.54 - 1.55)       # 53.14 x 82.01
ACTIVE = (2.20, 2.20 + 51.84, 86.54 - 2.20 - 77.76, 86.54 - 2.20)    # 51.84 x 77.76
TOUCH = PS                      # Rev K callers that ask for the front sheet's outline


def z_levels(front=P.LIP, total=hw.PANEL_T):
    """{layer: (z0, z1)} with the front surface at `front`. The drawing does not split the tolerance by
    layer; it goes to the EPL, which keeps the TFT glass (and the FPC bonded to it) its drawn 0.50."""
    out, z = {}, front
    for name, t in LAYERS:
        if name == 'epl':
            t += total - hw.PANEL_T
        out[name] = (z - t, z)
        z -= t
    return out


def rect(o, z0, z1):
    u0, u1, v0, v1 = o
    return box(hw.PANEL_X0 + u0, hw.PANEL_X0 + u1, hw.PANEL_Y0 + v0, hw.PANEL_Y0 + v1, z0, z1)


def body(front=P.LIP, total=hw.PANEL_T):
    """The panel stack as named solids."""
    z = z_levels(front, total)
    return {'glass': rect(EPD, *z['glass']), 'epl': rect(EPL, *z['epl']), 'ps': rect(PS, *z['ps'])}


def display(front=P.LIP, total=hw.PANEL_T):
    parts = list(body(front, total).values())
    s = parts[0]
    for p in parts[1:]:
        s = s.union(p)
    return s


# ---- the FPC (front view outline, v <= 0 is beyond the glass edge) -------------------------------
FPC_L = 22.36
FPC_L_TOL = 0.30
RIBBONS = {
    'main': dict(conn='J2', t=0.10, on_glass=True,
                 poly=[(19.2, 0.0), (35.1, 0.0), (35.1, -6.0), (34.37, -6.6), (34.37, -FPC_L),
                       (21.87, -FPC_L), (21.87, -6.6), (19.2, -6.0)],
                 stiff=[(-(FPC_L - 5.0), -FPC_L, 0.20)]),       # 0.30 total over its last 5 mm
}
BEND_R = 0.65                   # centre-line radius of both folds (inner ~0.6 mm)
INSERT = 2.6                    # the FPC's end sits this far inside J2's mouth (Rev K)
Z_REAR = -0.45                  # the FPC's height along the back of the board (J2's entry)


def slot():
    """The PCB's FPC slot (x0, x1, y0, y1), measured from the board solid."""
    return (7.021, 54.06, 5.75, 7.05)


def exit_z(name, front=P.LIP, total=hw.PANEL_T):
    return z_levels(front, total)['glass'][1] + RIBBONS[name]['t'] / 2


def flat_length(name):
    return -min(v for u, v in RIBBONS[name]['poly'])


def width_at(name, v):
    """u-interval of the flat FPC at height v."""
    poly = sg.Polygon(RIBBONS[name]['poly'])
    line = poly.intersection(sg.LineString([(-10, v), (80, v)]))
    if line.is_empty:
        return None
    xs = [c[0] for g in getattr(line, 'geoms', [line]) for c in g.coords]
    return min(xs), max(xs)


class Path:
    """Centre line of the FPC in the (y, z) plane, sampled with arc length.

    x3 route: it leaves the glass's bottom edge heading -Y, folds 90 degrees over the edge (R0.65), so it is
    already on the slot's centre line (the panel is placed for that), drops straight through the slot, and
    folds 90 degrees again to run up the back of the board into J2. Rev K's panel needed an S under the glass
    to reach the slot; this one does not, which leaves ~1 mm more slack."""

    def __init__(self, name='main', front=P.LIP, total=hw.PANEL_T, length=None):
        self.name = name
        R = BEND_R
        ye = hw.PANEL_Y0
        ze = exit_z(name, front, total)
        yv = ye - R                                          # the drop's line (the slot's centre)
        mouth = hw.bounds(RIBBONS[name]['conn'])[2]
        self.mouth, self.tip_target = mouth, mouth + INSERT
        pts = []

        def arc(cy, cz, a0, a1, n=40):
            for i in range(n + 1):
                a = math.radians(a0 + (a1 - a0) * i / n)
                pts.append((cy + R * math.cos(a), cz + R * math.sin(a)))

        def line(p, q, n=20):
            for i in range(1, n + 1):
                pts.append((p[0] + (q[0] - p[0]) * i / n, p[1] + (q[1] - p[1]) * i / n))

        arc(ye, ze - R, 90, 180)                             # over the glass edge, heading down (-Z)
        line(pts[-1], (yv, Z_REAR + R))                      # straight through the slot
        arc(yv + R, Z_REAR + R, 180, 270)                    # along the back of the board (+Y)
        self.pre = np.array(pts)
        self.drop_y = yv
        self.rear_y0 = yv + R
        L0 = self._length(self.pre)
        self.fold_length = L0
        straight = self.tip_target - self.rear_y0
        L = flat_length(name) if length is None else length
        self.slack = L - L0 - straight
        # take the slack up as a gentle bow away from the board between the slot and the stiffened end
        stiff = abs(RIBBONS[name]['stiff'][0][1] - RIBBONS[name]['stiff'][0][0])
        ya, yb = self.rear_y0 + 1.0, self.tip_target - stiff - 0.3
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
        tail = width_at(self.name, -flat_length(self.name) + 1e-5)
        b = hw.bounds(RIBBONS[self.name]['conn'])
        return {'flat_length_mm': round(flat_length(self.name), 2), 'fold_length_mm': round(self.fold_length, 2),
                'connector': RIBBONS[self.name]['conn'], 'mouth_y': round(self.mouth, 2),
                'drop_y': round(self.drop_y, 3), 'slack_mm': round(self.slack, 2), 'bow_height_mm': round(h, 2),
                'exit_z': round(self.pre[0][1], 2),
                'terminal_offset_to_J2_mm': round(hw.PANEL_X0 + sum(tail) / 2 - (b[0] + b[1]) / 2, 3)}


def _strip(path, name, u_range_fn, back_extra_fn, front_off, s_range, ds=0.08):
    """Watertight mesh of the FPC (or a part on it) following `path` between s_range."""
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
    """{name: trimesh} for the FPC in its installed shape."""
    out = {}
    for name, r in RIBBONS.items():
        path = Path(name, front, total)
        L = flat_length(name)

        def back_extra(s, r=r):
            v = -s
            return sum(t for (va, vb, t) in r['stiff'] if vb <= v <= va)

        out[name] = _strip(path, name, lambda s, name=name: width_at(name, -s),
                           back_extra, lambda s, r=r: (-r['t'] / 2, r['t'] / 2), (0.0, L))
    return out


def report(front=P.LIP, total=hw.PANEL_T):
    out = {name: Path(name, front, total).report() for name in RIBBONS}
    for name in RIBBONS:
        out[name]['slack_short_tail_mm'] = round(Path(name, front, total, flat_length(name) - FPC_L_TOL).slack, 2)
        out[name]['slack_long_tail_mm'] = round(Path(name, front, total, flat_length(name) + FPC_L_TOL).slack, 2)
    return out


if __name__ == '__main__':
    import json
    print(json.dumps(report(), indent=1))
    for dt in (-hw.PANEL_T_TOL, hw.PANEL_T_TOL):
        print('panel', dt, {k: v['slack_mm'] for k, v in report(total=hw.PANEL_T + dt).items()})
    rb = ribbons()
    for k, m in rb.items():
        print(k, len(m.faces), 'watertight', m.is_watertight, np.round(m.bounds, 2).tolist())
