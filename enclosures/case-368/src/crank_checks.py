"""Bottom keys (crank.py, keys.py): the crank spec's checks 1, 2 and 4, run by build.py for each build; results in
out/<variant>/crank.json. mechanics.py has checks 3, 5, 6 and 7 (the key's stroke, forces, preload window, stress);
slice_check.py reads the printed features back (check 8).

  static     (1) every new part - crank, key, rod - against the tub, the lid, the midplate, each other, the board and
             the switch, in 3D, at each key, at rest for a tub-to-board offset of -0.2 / 0 / +0.2 in Y, with each switch
             family and its crank (MJTP1117 from the board's STEP on crank-M, the TS365ZJ's envelope on crank-T). The
             designed contacts are the crown on the pusher and the nose on the plunger (both tangent); nothing overlaps
             (the drag bump in the chin wall went with the hook keys, test 2, 2026-09-30). The M2.5 side screw is gone
             (SPEC2 rev 3): the gate's touch on the tub is build.contacts'
  sweep      (2) each crank turned -13..+16 degrees with its key riding the crown, in YZ: the crank's four zones (leg
             |dx| <= 1.3, belly 1.3..3.75, the cheeks' lip 3.75..4.05 with the open C and their closed ring
             4.05..5.25, 'cheek') against the shadows of everything else over the same X band (the spec's method;
             conservative, since it lets parts meet that only share Y and Z). The ring's band is beyond the TS365
             housing's and the MJTP model's (4.04), so ring_mj checks it against the MJTP housing with the crank's X
             float and the board nearer (test 1, 2026-09-29). The plunger
             follows the nose (kinematic); the crown is the only key contact. The sweep runs on down to the angle a
             crank falls to with no key under it (theta_free_no_key: in the face-down tub the pad falls toward the face
             until the crank meets the tub, about -17.5), with the key out of the way there: a crank dropped in before
             its key, or with the key out, hangs that far
  paths      (4) the rod's axial path; each crank dropped in along +Z at theta 0, +4 and +10 past the keys at their
             stop; the board lowered past the cranks (where each plunger first touches its nose, and how steeply); the
             keys pushed in from inside with their hooks in the slots (nothing meets the tub up to the stop; 0.05 past
             it only the hooks do, under the slots' roof)
  free swing (2026-10-12) the board out, the tub face down: each crank turned by hand from its key to its first tub
             contact, its cheek zones against the tub's well as sliced (both parts on their layer grids), each face
             grown, the crank and rod sagged through their bores' play toward the face: >= 0.05 (FREE_SWING)
  logo       the chin wordmark leaves >= 0.6 of plastic over the cheek slots' roofs; the back icon leaves >= 0.4 of the
             lid's floor under its engraving (logo_back_floor)
The key is the hook key (test 2, 2026-09-30): its stop above rest is KEY_W_OUT (its hooks flat under the slots' roof),
where it hangs face down in the assembly pose; mechanics.key_hooks has the hooks' own checks (the stop, the walls behind
the slots, tilt, pull-out, the hooks against the crank over -20..+60, gravity per pose).
SPEC2 rev 3 (2026-09-28: the gate replaces the M2.5 side screw; its section 9 numbers):
  pickup     (2) where a crank dropped in with no rod comes to rest, and every pose on its way there (the keys at their
             stop, gravity +Z): its bore against the sagged rod, <= 0.30 at rest (the 0.3 lead-ins alone), <= 0.80 on the
             way (the tip's flat lands in the 2.5 lead-in mouth)
  drop       (3) the crank's first contact as it drops in at 0 / +4 / +10 degrees, dy -0.4..+0.4
  gate       (5) the gate lowered into its slot, (6) its bevel camming the rod home, (7) its flat bearing on the lips
  pose_10_5  SPEC2 open item 10.5: the cheeks at the free hang with the bore 0.265 off (toward 211 and 90 degrees)
X-direction clearances (cheek to slot side 0.15, cheek to web 0.15, cap to opening side 0.30, cap to web 0.40) are set
in params and listed, not measured: the YZ checks cannot see them (mechanics.key_fit stacks the print's error on them;
slice_check.key_fit reads them back from the G-code).
"""
import math
import numpy as np
import trimesh
import cadquery as cq
import shapely
from shapely import affinity
from shapely.geometry import Polygon, Point, box as sbox
from shapely.ops import nearest_points, unary_union
import hw
import params as P
import crank
import keys
import tub as T
from geom import box, xcyl

PY, PZ = P.ROD_AXIS
SWEEP, INNER, STEP = (-13.0, 16.0), (-4.0, 13.0), 0.5
RING_X0 = P.CRANK_CHEEK_RING['x0']
ZONES = {'leg': [(0.0, P.CRANK_LEG_HALF)], 'belly': [(P.CRANK_LEG_HALF, P.CRANK_CHEEK[0])],
         'lip': [(P.CRANK_CHEEK[0], RING_X0)], 'cheek': [(RING_X0, P.CRANK_CHEEK[1])]}
ZONE_PLANE = {'leg': 0.65, 'belly': 2.5, 'lip': 3.90, 'cheek': 4.65}   # where each zone's crank section is taken
                                                              # (prismatic there). The cheek (test 1): its lip keeps
                                                              # the open C, its outer 1.20 ('cheek') is a closed ring
CRANK_FLOAT = round(P.CRANK_CHEEK[0] - P.SLOT[0], 3)          # the crank's X play in its slots, per side (0.15)
RING_MJ_MIN = 0.03                                            # the ring to the MJTP housing, crank and board worst
DY = (-P.TUB_BOARD_DY, 0.0, P.TUB_BOARD_DY)
STOP = P.KEY_W_OUT                                            # the key's stop above rest: its hooks under the roof
THETA_STOP = next(t / 10 for t in range(0, -300, -1) if crank.key_lift(t / 10) >= STOP)   # the pad on a key at its stop
MJ_HOUSING_Y = -0.68                                          # the MJTP's housing face (its nub stands in front of it)
MIN_VOL = 1e-4
EXT_RULES = {'rail': 0.0, 'board edge at -0.4': 0.04}         # below -13 (down to theta_free_no_key): the tub is what
EXT_MIN = 0.05                                                # stops the crank (its rail, 0 there); the cheek keeps
                                                              # 0.05 off a board edge at -0.4 (the second cheek trim);
                                                              # everything else >= EXT_MIN


# ---- geometry helpers --------------------------------------------------------------------------------------------
def to_mesh(shape, tol=0.004):
    vs, ts = shape.tessellate(tol, 0.05)
    return trimesh.Trimesh([(v.x, v.y, v.z) for v in vs], ts, process=True)


def section(m, x):
    s = m.section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0])
    g = Polygon()
    if s is None:
        return g
    for loop in s.discrete:
        if len(loop) >= 3:
            p = Polygon(loop[:, [1, 2]]).buffer(0)
            if p.area > 1e-7:
                g = g.symmetric_difference(p)
    return g


def shadow(m, bands, xc, step=0.1, sides=(1, -1)):
    """Union of m's YZ sections over the X bands (dx from xc, both sides of the key). The sections go onto a 0.1 um
    grid first: a prismatic part's sections nearly coincide, which makes a plain overlay crawl."""
    gs = []
    for a, b in bands:
        for s in sides:
            for dx in list(np.arange(a + 0.013, b - 0.013, step)) + [b - 0.013]:
                gs.append(shapely.set_precision(section(m, xc + s * dx), 1e-4))
    return unary_union(gs).buffer(0)


def d(a, b):
    """Gap between two YZ regions; negative: their overlap's area."""
    if a.is_empty or b.is_empty:
        return float('inf')
    if a.intersects(b):
        ov = a.intersection(b).area
        if ov > 1e-6:
            return -round(ov, 5)
    return a.distance(b)


def rot(g, th):
    return affinity.rotate(g, th, origin=(PY, PZ))


def angles(a0=SWEEP[0], a1=SWEEP[1], step=STEP):
    return [round(a0 + i * step, 3) for i in range(int(round((a1 - a0) / step)) + 1)]


def nose_front(variant, th, z0, z1):
    """Furthest +Y point of the turned nose within a plunger's Z band (the plunger face follows it)."""
    c = crank.rotp(P.CRANK_NOSE_C[variant], th)
    zb = min(max(c[1], z0), z1)
    dz = abs(zb - c[1])
    return c[0] + math.sqrt(P.CRANK_NOSE_R ** 2 - dz ** 2) if dz < P.CRANK_NOSE_R else -99.0


# ---- the parts round one key --------------------------------------------------------------------------------------
class Key:
    """Meshes and YZ shadows round one bottom key."""

    def __init__(self, ref, tub_s, lid_s, mid_s, hwsol):
        self.ref = ref
        self.xc = xc = keys.centre(ref)
        reg = box(xc - 7.5, xc + 7.5, P.Y0 - 1, 1.5, P.Z_BACK - 1, P.Z_FRONT + 2).val()
        self.tub3 = tub_s.intersect(reg)
        self.lid3 = lid_s.intersect(reg)
        self.mid3 = mid_s.intersect(reg)
        self.sw3 = hwsol[ref]
        self.pcb3 = hwsol['PCB'].intersect(reg)
        self.crank3 = {v: crank.build(v, xc).val() for v in 'MT'}
        self.key3 = keys.build(ref).val()
        m = {'tub': to_mesh(self.tub3), 'lid': to_mesh(self.lid3), 'sw': to_mesh(self.sw3),
             'key': to_mesh(self.key3), **{f'crank{v}': to_mesh(s) for v, s in self.crank3.items()}}
        self.m = m
        # the crank's zone sections at theta 0, and everything else's shadow over each zone's band
        self.C = {v: {z: section(m[f'crank{v}'], xc + ZONE_PLANE[z]) for z in ZONES} for v in 'MT'}
        self.sh = {z: {n: shadow(m[n], b, xc) for n in ('tub', 'lid', 'key', 'sw')} for z, b in ZONES.items()}
        yr = P.RAIL_Y[0] - 0.01
        for z in ZONES:
            t = self.sh[z]['tub']
            self.sh[z]['rail'] = t.intersection(sbox(yr, -20, 20, 20))
            self.sh[z]['chin'] = t.intersection(sbox(-20, -20, P.KEY_OPENING['y'][0] + 0.01, 20))
            sw = self.sh[z]['sw']
            self.sh[z]['mj_housing'] = sw.intersection(sbox(MJ_HOUSING_Y, -20, 20, 20))
            self.sh[z]['mj_nub'] = sw.intersection(sbox(-20, -20, MJ_HOUSING_Y, 20))
        self.theta_free = {v: free_hang(self, v) for v in 'MT'}


def free_hang(K, var):
    """The angle a crank with no key under it falls to in the face-down tub (pad toward the face, theta < 0): where
    one of its zones first meets the tub's shadow over that zone's band. Returns (theta, zone)."""
    def touch(th):
        return min((d(rot(K.C[var][z], th), K.sh[z]['tub']), z) for z in ZONES)
    th = 0.0
    while touch(th - 0.25)[0] > 0.0 and th > -40:
        th -= 0.25
    lo, hi = th - 0.25, th                                   # touching at lo, clear at hi
    for _ in range(20):
        m = (lo + hi) / 2
        if touch(m)[0] > 0.0:
            hi = m
        else:
            lo = m
    return round(hi, 2), touch(lo)[1]


def ts_rects(dy=0.0, worst=False):
    Tt = P.TS365
    tip = (Tt['tip_y'][0] if worst else Tt['tip_y_nom']) + dy
    z0, z1 = Tt['plunger_z_worst'] if worst else Tt['plunger_z_nom']
    housing = sbox(Tt['housing_y'] + dy, Tt['body_z'][0], 6.0, Tt['body_z'][1])
    return housing, (tip, z0, z1, Tt['housing_y'] + dy + 0.2)


def no_crown(g):
    """A crank section without its crown (the designed contact with the key's pusher)."""
    return g.difference(sbox(-7.75, -0.6 + 1e-3, -6.8, 0.7))


def no_nose(g, variant, th):
    return g.difference(rot(Point(*P.CRANK_NOSE_C[variant]).buffer(P.CRANK_NOSE_R + 0.002, 128), th))


# ---- check 1: static interference in 3D -------------------------------------------------------------------------
def _vol(a, b):
    try:
        ab, bb = a.BoundingBox(), b.BoundingBox()
    except Exception:                        # an empty clip (the midplate lies well above the chin)
        return 0.0, None
    if ab.xmin > bb.xmax or ab.xmax < bb.xmin or ab.ymin > bb.ymax or ab.ymax < bb.ymin or ab.zmin > bb.zmax or ab.zmax < bb.zmin:
        return 0.0, None
    i = a.intersect(b)
    v = i.Volume()
    if v <= MIN_VOL:
        return v, None
    ib = i.BoundingBox()
    return v, [round(x, 3) for x in (ib.xmin, ib.xmax, ib.ymin, ib.ymax, ib.zmin, ib.zmax)]


def static(K, rod_s):
    """Rows of every overlap > MIN_VOL among the new parts and their surroundings, per switch family and offset."""
    rows, rest = [], {}
    for fam, var in (('MJTP1117', 'M'), ('TS365ZJ', 'T')):
        for dy in DY:
            face = (P.PLUNGER_Y if fam == 'MJTP1117' else P.TS365['tip_y_nom']) + dy
            th = crank.rest_theta(face, var)
            lift = crank.key_lift(th)
            rest[f'{fam} {dy:+.1f}'] = {'theta': round(th, 2), 'key_lift': round(lift, 3)}
            cr = crank.rotate(cq.Workplane(obj=K.crank3[var]), th).val()
            ky = K.key3.moved(cq.Location(cq.Vector(0, 0, lift)))
            if fam == 'MJTP1117':
                sw = {'switch': K.sw3.moved(cq.Location(cq.Vector(0, dy, 0)))}
            else:
                h, pl = crank.ts365(K.xc, dy)
                sw = {'ts_housing': h.val(), 'ts_plunger': pl.val()}
            pcb = K.pcb3.moved(cq.Location(cq.Vector(0, dy, 0)))
            parts = {'crank': cr, 'key': ky, 'rod': rod_s}
            env = {'tub': K.tub3, 'lid': K.lid3, 'midplate': K.mid3, 'PCB': pcb, **sw}
            names = list(parts)
            pairs = [(a, b) for i, a in enumerate(names) for b in names[i + 1:]] + [(a, b) for a in names for b in env]
            allp = {**parts, **env}
            for a, b in pairs:
                v, where = _vol(allp[a], allp[b])
                if where:
                    rows.append({'key': K.ref, 'switch': fam, 'dy': dy, 'part': a, 'with': b, 'mm3': round(v, 4),
                                 'where': where, 'expected': None})
    return rows, rest


# ---- check 2: the crank's sweep, in YZ ---------------------------------------------------------------------------
def sweep(K):
    """Minimum gaps over -13..+16 (and -4..+13), per crank zone and neighbour; matching crank per switch family. Below
    -13, down to the crank's free-hang angle with no key (theta_free_no_key), the same pairs but the key's ('ext_min':
    no key rides the crown there)."""
    out = {}

    def track(key, g, th):
        r = out.setdefault(key, {'min': (9.0, None), 'inner_min': (9.0, None), 'ext_min': (9.0, None)})
        if th < SWEEP[0] - 1e-9:
            if g < r['ext_min'][0]:
                r['ext_min'] = (round(g, 3), th)
            return
        if g < r['min'][0]:
            r['min'] = (round(g, 3), th)
        if INNER[0] <= th <= INNER[1] and g < r['inner_min'][0]:
            r['inner_min'] = (round(g, 3), th)

    for var in 'MT':
        tf = K.theta_free[var][0]
        ext = [round(SWEEP[0] - STEP * i, 3) for i in range(1, int((SWEEP[0] - tf) / STEP) + 1)] + [tf]
        for z in ZONES:
            C0, sh = K.C[var][z], K.sh[z]
            for th in ext + angles():
                C = rot(C0, th)
                lift = crank.key_lift(th)
                keyed = th >= SWEEP[0] - 1e-9
                if var == 'M' or not keyed:  # the tub, the lid and the key are the same for both; once is enough
                    tag = '' if var == 'M' else f' [crank-{var}]'
                    track(f'{z}{tag} -> rail', d(C, sh['rail']), th)
                    track(f'{z}{tag} -> chin wall', d(C, sh['chin']), th)
                    track(f'{z}{tag} -> lid', d(C, sh['lid']), th)
                    if keyed:
                        kk = affinity.translate(sh['key'], 0, lift)
                        track(f'{z} -> key (no crown)', d(rot(no_crown(C0), th), kk), th)
                        ov = C.intersection(kk).area if C.intersects(kk) else 0.0
                        track(f'{z} crown/pusher overlap mm2 (neg)', -ov, th)
                    for e in (-0.2, -0.4):
                        track(f'{z}{tag} -> board edge at {e}', d(C, sbox(e, 0.0, 200, P.PCB_FRONT)), th)
                    track(f'{z}{tag} -> MJTP housing', d(C, sh['mj_housing']), th)
                if z in ('belly', 'lip'):    # the leg's band is the plunger's own (|dx| <= 1.85): no housing there;
                                             # the ring is beyond it in X (|dx| >= 4.05 > 3.65 + the 0.15 float)
                    ts_h, _ = ts_rects(0.0, worst=True)
                    track(f'{z} [crank-{var}] -> TS365 housing (worst face -1.65)', d(C, ts_h), th)
    # the plunger follows the nose: leg body and belly to the plunger, the nose itself excluded
    cases = [('crank-M, MJTP', 'M', P.PLUNGER_Y, (-3.459, -1.959), MJ_HOUSING_Y),
             ('crank-T, TS worst out/high', 'T', -2.4, P.TS365['plunger_z_worst'], -1.45),
             ('crank-T, TS nominal', 'T', P.TS365['tip_y_nom'], P.TS365['plunger_z_nom'], -1.45),
             ('crank-M, TS worst (wrong variant)', 'M', -2.4, P.TS365['plunger_z_worst'], -1.45)]
    for name, var, tip, (z0, z1), yh in cases:
        for z in ('leg', 'belly'):
            for th in angles():
                face = max(tip, nose_front(var, th, z0, z1))
                track(f'{z} -> plunger, kinematic: {name}', d(no_nose(rot(K.C[var][z], th), var, th), sbox(face, z0, yh, z1)), th)
    return {k: {'min': v['min'][0], 'at_deg': v['min'][1], 'inner_min': v['inner_min'][0], 'inner_at_deg': v['inner_min'][1],
                'ext_min': v['ext_min'][0] if v['ext_min'][1] is not None else None, 'ext_at_deg': v['ext_min'][1]}
            for k, v in out.items()}


def sweep_verdict(sw):
    """The spec's pass rules for the sweep: >= 0.10 everywhere (leg/belly to the rail >= 0.06, cheek to a board edge at
    -0.4 >= 0.07), >= 0.20 inside -4..+13, the plunger (kinematic) >= 0.35; the crown the only key contact. Below -13
    down to the free-hang angle (no key): the rail is the stop (>= 0), the cheek keeps >= 0.04 off a board edge at
    -0.4, everything else >= EXT_MIN."""
    bad = []
    for k, r in sw.items():
        if r.get('ext_min') is not None:
            lim_x = next((v for s, v in EXT_RULES.items() if s in k), EXT_MIN)
            if r['ext_min'] < lim_x - 1e-9:
                bad.append(k + ' (below -13)')
        if r['min'] == 9.0:              # tracked only below -13 (crank-T's own rows)
            continue
        if 'overlap' in k:
            if r['min'] < -1e-3:
                bad.append(k)
            continue
        if 'kinematic' in k:
            lim, lim_in = 0.35, 0.35
        elif k.startswith(('leg -> rail', 'belly -> rail')):
            lim, lim_in = 0.06, 0.20
        elif k.startswith('cheek -> board edge at -0.4'):
            lim, lim_in = 0.07, 0.07
        elif 'board edge at -0.4' in k:
            lim, lim_in = 0.07, 0.07
        else:
            lim, lim_in = 0.10, 0.20
        if r['min'] < lim or r['inner_min'] < lim_in:
            bad.append(k)
    return bad


# ---- the free swing (2026-10-12) ---------------------------------------------------------------------------------
# Ian, from printed cases: "the crank hits a friction point when rotating from its button side to its switch side". In
# the open tub, face down with the board out (assembly), a crank turned by hand swings from lying on its key to its
# first contact with the tub, and the corner where each cheek's flat top meets its second trim passes under the slot's
# roof at about +40. The sweep above stops at +16 (the switch stops the crank there) and takes the CAD on the rod's
# axis; this takes the parts as they print: the face-down tub on its 0.2 layer grid from the face, the crank on its own
# (it prints pad end down), each layer its mid-plane's section; each face of the crank grown by the worst part growth
# (KEY_FDM part / 2); and gravity, which face down takes the crank on the rod and the rod in its ring bores through their
# play toward the face (+Z): bore reamed to 1.90, the ring bores 1.93 free as sliced (ROD_HOLE_D), the rod at its
# smallest. The crank's cheek zones (lip, cheek) against the tub's shadow over them (the well: the slot, its roof, the
# skin), from the key's stop to the end of the swing: >= `min` all the way.
FREE_SWING = dict(grow=round(max(P.KEY_FDM['part']) / 2, 3), rod_min=P.ROD_D_RANGE[0], ring_free=1.93, step=0.5, min=0.05)
FREE_SWING_SAG = round((P.CRANK_BORE['ream'] - FREE_SWING['rod_min']) / 2 + (FREE_SWING['ring_free'] - FREE_SWING['rod_min']) / 2, 3)


def as_printed(g, axis, origin, step=P.LAYER):
    """A (y, z) region as the slicer prints it in layers of `step` along `axis` ('y': the crank, printed pad end down;
    'z': the face-down tub) from `origin`: each layer is its mid-plane's section, carried across the layer."""
    from shapely.geometry import LineString
    if g.is_empty:
        return g
    y0, z0, y1, z1 = g.bounds
    lo, hi = (y0, y1) if axis == 'y' else (z0, z1)
    out = []
    for k in range(math.floor((lo - origin) / step) - 1, math.ceil((hi - origin) / step) + 1):
        a, b = origin + k * step, origin + (k + 1) * step
        m = (a + b) / 2
        s = g.intersection(LineString([(m, z0 - 1), (m, z1 + 1)] if axis == 'y' else [(y0 - 1, m), (y1 + 1, m)]))
        for seg in getattr(s, 'geoms', [s]):
            if seg.is_empty or seg.length < 1e-6:
                continue
            p, q = seg.coords[0], seg.coords[-1]
            out.append(sbox(a, min(p[1], q[1]), b, max(p[1], q[1])) if axis == 'y' else
                       sbox(min(p[0], q[0]), a, max(p[0], q[0]), b))
    return unary_union(out).buffer(0)


def depth_gap(a, b):
    """The gap between two YZ regions; when they overlap, minus the overlap's depth (its deepest point from b's
    boundary)."""
    if not a.intersects(b):
        return round(a.distance(b), 4)
    ov = a.intersection(b)
    pts = [p for g in getattr(ov, 'geoms', [ov]) if g.geom_type == 'Polygon' for p in g.exterior.coords]
    return -round(max((b.boundary.distance(Point(p)) for p in pts), default=0.0), 4)


def free_end(K, var):
    """The end of the free swing: the angle a crank turned + from 0 first meets the tub (CAD, on the rod's axis; the
    nose on the rail's +Y face), to 0.05 degrees."""
    def touches(th):
        return any(d(rot(K.C[var][z], th), K.sh[z]['tub']) <= 0.0 for z in ZONES)
    th, step = 0.0, 1.0
    while step >= 0.05:
        if th + step <= 180.0 and not touches(th + step):
            th += step
        else:
            step /= 2
    return round(th, 2)


def free_swing(K):
    """FREE_SWING (above): crank-M's cheek zones (crank-T's are the same) from the key's stop (THETA_STOP, the crank on
    its key) to the end of either variant's swing, against the tub over each zone: the CAD on the axis (reported), as
    sliced (reported), and as sliced, grown and sagged (the criterion). Gaps in mm; minus an overlap's depth."""
    from shapely.geometry import LineString
    F, sag = FREE_SWING, FREE_SWING_SAG
    win = sbox(-10.0, -5.0, 2.0, P.Z_FRONT + 0.5)
    end_by = {v: free_end(K, v) for v in 'MT'}
    a0, a1 = THETA_STOP, max(end_by.values())
    thetas = sorted({round(a0 + i * F['step'], 3) for i in range(int((a1 - a0) / F['step']) + 1)} | {a0, a1})
    cases = {'cad': 'CAD, on the rod axis', 'as_sliced': 'as sliced, on the rod axis',
             'worst': f"as sliced, each face +{F['grow']}, sagged {sag} toward the face"}
    acc = {k: {'gap': 9.0} for k in cases}
    roof = {}
    for z in ('lip', 'cheek'):
        t_cad = K.sh[z]['tub'].intersection(win)
        t_pr = as_printed(t_cad, 'z', P.Z_FRONT)
        c_cad = K.C['M'][z]
        c_pr = as_printed(c_cad, 'y', P.CRANK_PAD_END)
        c_wc = c_pr.buffer(F['grow'], 16)
        if not roof:                              # the slot's roof over the rod's axis, drawn and as sliced
            ln = LineString([(PY, PZ), (PY, P.Z_FRONT + 1)])
            roof = {k: round(min(q for g in getattr(t.intersection(ln), 'geoms', [t.intersection(ln)])
                                 for _, q in g.coords), 3) for k, t in (('cad', t_cad), ('as_sliced', t_pr))}
        for th in thetas:
            for k, c, t, dz in (('cad', c_cad, t_cad, 0.0), ('as_sliced', c_pr, t_pr, 0.0), ('worst', c_wc, t_pr, sag)):
                g = depth_gap(affinity.translate(rot(c, th), 0.0, dz), t)
                if g < acc[k]['gap']:
                    acc[k] = {'gap': g, 'at_deg': th, 'zone': z}
    return {'range_deg': [a0, a1], 'end_by_variant': end_by, 'grow': F['grow'], 'sag': sag,
            'sag_from': {'crank bore reamed': P.CRANK_BORE['ream'], 'ring bores free as sliced': F['ring_free'],
                         'rod smallest': F['rod_min']},
            'slot_roof_over_the_rod': roof, 'cases': cases, **acc, 'min': F['min'], 'ok': acc['worst']['gap'] >= F['min']}


def ring_mj(K):
    """The ring zone against the MJTP1117's housing (SPEC A5 c). No zone's shadow sees the housing from the ring: the
    4.26's MJTP envelope ends at |dx| 4.04, this project's STEP model at about 3.6, both short of the ring's 4.05, but
    the crank floats CRANK_FLOAT in X toward it and the board can sit TUB_BOARD_DY nearer. So, as if the housing's
    widest YZ outline reached the ring: the ring's section (crank-M, the MJTP's crank) turned over the sweep and on down
    to the free hang, against the housing's shadow over its whole width (|dx| 0..RING_X0, y past MJ_HOUSING_Y), moved
    TUB_BOARD_DY toward the crank (-Y). Pass: >= RING_MJ_MIN."""
    sw = shadow(K.m['sw'], [(0.0, RING_X0)], K.xc)
    hs = affinity.translate(sw.intersection(sbox(MJ_HOUSING_Y, -20, 20, 20)), -P.TUB_BOARD_DY, 0)
    tf = K.theta_free['M'][0]
    ths = [tf] + [round(SWEEP[0] - STEP * i, 3) for i in range(1, int((SWEEP[0] - tf) / STEP) + 1)] + angles()
    g, at = min((d(rot(K.C['M']['cheek'], th), hs), th) for th in ths)
    at_rest = d(K.C['M']['cheek'], hs)
    return {'min': round(g, 3), 'at_deg': at, 'theta_0': round(at_rest, 3), 'housing_band_dx': [0.0, RING_X0],
            'housing_empty': hs.is_empty, 'ok': (not hs.is_empty) and g >= RING_MJ_MIN}


# ---- check 4: assembly paths --------------------------------------------------------------------------------------
def rod_path(tub_s, cranks, others):
    """(a) SPEC2 rev 3 check 2: a 1.90 cylinder on the rod's axis from 0.2 outside the side wall (X0 - 0.2: the rod's
    way in, along the gate slot's channel) to the +X wall (ROD_SPAN[1]): nothing of the tub or the cranks inside it; a
    1.949 one (the rod + 0.1): nothing else inside it but the gate, and the gate only up to its flat (ROD_STOP_X0)."""
    x0, x1 = P.X0 - 0.2, P.ROD_SPAN[1]
    c190 = xcyl(x0, x1, PY, PZ, 1.90).val()
    c195 = xcyl(x0, x1, PY, PZ, 1.949).val()
    rep = {'from_x': round(x0, 3), 'to_x': x1, 'tub': round(tub_s.intersect(c190).Volume(), 5)}
    rep['cranks'] = round(sum(c.intersect(c190).Volume() for c in cranks), 5)
    within = {}
    for k, v in others.items():
        i = v.intersect(c195)
        if i.Volume() > 1e-5:
            within[k] = {'mm3': round(i.Volume(), 5), 'x_max': round(i.BoundingBox().xmax, 4)}
    rep['others_within_0.1'] = within
    gate = within.get('gate')
    rep['gate_only_to_its_flat'] = gate is not None and gate['x_max'] <= P.ROD_STOP_X0 + 1e-3
    rep['ok'] = (rep['tub'] <= 1e-5 and rep['cranks'] <= 1e-5 and set(within) <= {'gate'}
                 and rep['gate_only_to_its_flat'])
    return rep


def crank_in(K):
    """(b) The crank dropped in along +Z (from the open back of the face-down tub) at theta -10 / 0 / +4 / +10, the keys
    at their stop: its least gap to the rail and to the keys over the last 6 mm."""
    out = {}
    for th in (-10, 0, 4, 10):
        for z in ZONES:
            C = rot(K.C['M'][z], th)
            kk = affinity.translate(K.sh[z]['key'], 0, STOP)
            g_rail = min(d(affinity.translate(C, 0, -t), K.sh[z]['rail']) for t in np.arange(0.0, 6.01, 0.1))
            g_key = min(d(affinity.translate(C, 0, -t), kk) for t in np.arange(0.0, 6.01, 0.1))
            out[f'{th:+d} {z}'] = {'rail': round(g_rail, 3), 'key_at_stop': round(g_key, 3)}
    return out


def board_in(K):
    """(c) The board lowered onto its bosses (+Z) past the cranks: where each plunger first meets its crank's nose
    (the contact normal's angle from Z: >= 40 means it cams the crank aside), and whether the housing or the board's
    edge meets a crank or the rail on the way. The crank's angle: in the face-down tub the crank hangs free from the
    rod, its pad toward the face, as far as it goes: onto the key's pusher with the keys at their stop (assembly
    order: theta_stop, about -11 on x3), or, with no key under it, onto the tub (theta_free_no_key, about -17.5).
    Those free-hang angles and the rest angle of each offset are the cases that must pass. Theta 0 (the design angle,
    as if a key had been pushed down first) is reported too: a wrong-variant crank held there ('TS365 worst on
    crank-M') meets the plunger's tip too steeply (about 31 degrees from Z against 40) and would push rather than cam;
    that is an accepted finding, since nothing holds a crank at 0 while the board goes in."""
    rows = []
    cases = [('MJTP on crank-M', 'M', 'MJ', P.PLUNGER_Y, (-3.459, -1.959), MJ_HOUSING_Y),
             ('TS365 nominal on crank-T', 'T', 'TS', P.TS365['tip_y_nom'], P.TS365['plunger_z_nom'], -1.45),
             ('TS365 worst (tip -2.4, high) on crank-M', 'M', 'TS', -2.4, P.TS365['plunger_z_worst'], -1.45),
             ('MJTP on crank-T', 'T', 'MJ', P.PLUNGER_Y, (-3.459, -1.959), MJ_HOUSING_Y)]
    for name, var, fam, tip, (z0, z1), yh in cases:
        for dy in DY:
            for th in sorted({0.0, THETA_STOP, K.theta_free[var][0], round(crank.rest_theta(tip + dy, var), 2)}):
                C = unary([rot(K.C[var][z], th) for z in ('leg', 'belly')])
                plunger = sbox(tip + dy, z0, yh + dy, z1)
                first = None
                for t in np.arange(8.0, -0.001, -0.02):
                    pl = affinity.translate(plunger, 0, -t)
                    if pl.distance(C) < 0.005:
                        a, b = nearest_points(C, pl)
                        c = crank.rotp(P.CRANK_NOSE_C[var], th)
                        on_nose = abs(math.hypot(a.x - c[0], a.y - c[1]) - P.CRANK_NOSE_R) < 0.02
                        ang = math.degrees(math.acos(min(1.0, abs(a.y - c[1]) / P.CRANK_NOSE_R))) if on_nose else None
                        first = {'mm_below_seat': round(float(t), 2), 'on_nose_crown': on_nose,
                                 'normal_from_z_deg': round(ang, 1) if ang is not None else None, 'at_yz': [round(a.x, 3), round(a.y, 3)]}
                        break
                # the housing and the board's edge against the crank (all three zones) and the rail, over the whole
                # way: each swept along its path as one region
                if fam == 'MJ':
                    hs = affinity.translate(unary([K.sh[z]['mj_housing'] for z in ZONES]), dy, 0)
                else:
                    hs = ts_rects(dy)[0]
                pcb = sbox(dy, 0.0, 200, P.PCB_FRONT)
                Call = unary([rot(K.C[var][z], th) for z in ZONES if fam == 'MJ' or z != 'cheek'])   # the ring:
                                             # beyond the TS365 housing in X
                rail = unary([K.sh[z]['rail'] for z in ZONES])
                g = min(d(swept_z(x, 8.0), y) for x in (hs, pcb) for y in (Call, rail))
                ok = (first is None or first['mm_below_seat'] < 0.03 or
                      (first['on_nose_crown'] and first['normal_from_z_deg'] >= 40)) and g > 0.0
                rows.append({'case': name, 'dy': dy, 'theta': th, 'required': th != 0.0, 'first_plunger_contact': first,
                             'housing_board_min_gap': round(g, 3), 'ok': ok,
                             'accepted_finding': th == 0.0 and not ok and (var, fam) in (('M', 'TS'), ('T', 'MJ'))})
    return rows


def swept_z(g, length):
    """The region g covers moving from `length` below its place (-Z) up to it: g, its lowered copy, and each edge's
    parallelogram between them."""
    v = (0.0, -length)
    parts = [g, affinity.translate(g, *v)]
    for poly in getattr(g, 'geoms', [g]):
        for ring in [poly.exterior, *poly.interiors]:
            c = list(ring.coords)
            for (a, b) in zip(c, c[1:]):
                q = Polygon([a, b, (b[0] + v[0], b[1] + v[1]), (a[0] + v[0], a[1] + v[1])])
                if q.area > 1e-9:
                    parts.append(q)
    return unary_union(parts).buffer(0)


def unary(gs):
    return unary_union([shapely.set_precision(g, 1e-4) for g in gs])


def key_in(K):
    """(d) The key pushed in along +Z from inside, before the cranks (the tub face down), its hooks in their slots, from
    below the parting plane to just short of its stop: it never overlaps the tub (in 3D: YZ shadows would let the cap
    meet the opening's sides; its guides are flush, zero area). 0.05 past the stop only its hooks meet the tub, flat
    under the slots' roof (KEY_SLOT_ROOF, inside the slots' X bands): the stop engages at KEY_W_OUT."""
    top = keys.top()
    start = P.SEAM - top - 0.5
    worst = (0.0, None)
    for lf in list(np.arange(start, STOP - 0.015, 0.1)) + [STOP - 0.01]:
        ov = K.key3.moved(cq.Location(cq.Vector(0, 0, float(lf)))).intersect(K.tub3).Volume()
        if ov > worst[0]:
            worst = (round(ov, 5), round(float(lf), 2))
    past = K.key3.moved(cq.Location(cq.Vector(0, 0, STOP + 0.05))).intersect(K.tub3)
    v = past.Volume()
    (a, b), zr = P.KEY_SLOT['dx'], P.KEY_SLOT_ROOF
    where, on_roof = None, False
    if v > 1e-6:
        bb = past.BoundingBox()
        where = [round(x, 3) for x in (bb.xmin - K.xc, bb.xmax - K.xc, bb.ymin, bb.ymax, bb.zmin, bb.zmax)]
        parts = past.Solids() if hasattr(past, 'Solids') else [past]
        on_roof = all(a - 1e-3 <= abs((q.BoundingBox().xmin + q.BoundingBox().xmax) / 2 - K.xc) <= P.SLOT[1] + 1e-3
                      and q.BoundingBox().zmin >= zr - 1e-3 and q.BoundingBox().ymin >= P.KEY_HOOK['tip'] - 1e-3
                      and q.BoundingBox().ymax <= P.KEY_Y[0] + 1e-3 for q in parts)     # within the hooks, over the roof
    return {'overlap_mm3': worst[0], 'at_lift': worst[1], 'from_lift': round(float(start), 2), 'stop': STOP,
            'past_stop_0.05': {'mm3': round(v, 5), 'where_dx_y_z': where, 'only_the_hooks_under_the_roof': on_roof},
            'ok': worst[0] <= 1e-4 and v > 1e-4 and on_roof}


def logo_over_slots():
    """The chin wordmark's engraving against the cheek slots' roofs: plastic left over each roof."""
    if not P.LOGO:
        return {'overlaps': False, 'min_plastic_mm': round(P.Z_FRONT - P.SLOT_ROOF, 3)}
    import logo
    lb = logo.solid(P.Z_FRONT - P.LOGO['depth'], P.Z_FRONT + 0.2).val().BoundingBox()
    over = False
    for xc in T.key_x():
        for a, b in ((xc - P.SLOT[1], xc - P.SLOT[0]), (xc + P.SLOT[0], xc + P.SLOT[1])):
            if lb.xmax > a and lb.xmin < b and lb.ymin < P.RAIL_Y[1] and lb.ymax > P.RAIL_Y[0]:
                over = True
    plastic = P.Z_FRONT - (P.LOGO['depth'] if over else 0.0) - P.SLOT_ROOF
    return {'logo_y': [round(lb.ymin, 2), round(lb.ymax, 2)], 'overlaps_slots': over, 'min_plastic_mm': round(plastic, 3),
            'ok': plastic >= 0.6}


def logo_back_floor(lid_s=None):
    """The back icon's engraving (params LOGO_BACK, 0.3 deep) against the lid's floor: the plastic left under it, >= 0.4.
    Over the battery pocket (with its BATT_POCKET_CLR) the floor is BATT_FLOOR_T (0.4), elsewhere LID_T (0.8); from
    params and the placed polygon. With the built lid (lid_s), also read off the solid: the icon's prism from the
    engraving's floor up is solid for 0.4 and for the plastic claimed (less 0.01), and not 0.05 past it; and the pocket's
    floor is a whole BATT_FLOOR_T under the cell."""
    if not P.LOGO_BACK:
        return {'ok': True}
    import logo
    cfg = P.LOGO_BACK
    g = logo.placed(cfg)
    c = P.BATT_POCKET_CLR
    pk = (P.BATT['x'][0] - c, P.BATT['x'][1] + c, P.BATT['y'][0] - c, P.BATT['y'][1] + c)
    pocket = sbox(pk[0], pk[2], pk[1], pk[3])
    over = g.intersects(pocket)
    floor = P.BATT_FLOOR_T if over else P.LID_T
    left = round(floor - cfg['depth'], 3)
    out = {'icon_centre': [round(cfg['x'], 2), round(cfg['y'], 2)], 'icon_xy': [round(v, 2) for v in g.bounds],
           'case_y': [round(P.Y0, 2), round(P.Y1, 2)], 'over_battery_pocket': over,
           'to_battery_pocket_mm': round(g.distance(pocket), 3), 'floor_mm': floor, 'engraving_mm': cfg['depth'],
           'plastic_left_mm': left, 'battery_pocket_floor_mm': P.BATT_FLOOR_T}
    ok = left >= 0.4
    if lid_s is not None:
        b = g.bounds
        z0 = P.Z_BACK + cfg['depth']
        near = lid_s.intersect(box(b[0] - 1, b[2] + 1, b[1] - 1, b[3] + 1, P.Z_BACK - 0.5, P.LID_FLOOR_IN + 0.5).val())
        frac = {}
        for t in (0.4, left - 0.01, left + 0.05):
            slab = logo.solid(z0 + 0.005, z0 + t, cfg).val()
            frac[f'{t:.2f}'] = round(near.intersect(slab).Volume() / slab.Volume(), 5)
        eng = logo.solid(P.Z_BACK + 0.005, z0 - 0.005, cfg).val()           # the engraving itself: cut, so empty
        ef = round(near.intersect(eng).Volume() / eng.Volume(), 5)
        pb = box(pk[0], pk[1], pk[2], pk[3], P.Z_BACK + 0.005, P.BATT_FLOOR - 0.005).val()
        pf = round(lid_s.intersect(pb).Volume() / pb.Volume(), 5)
        out['built_lid'] = {'solid_fraction_over_the_engraving': frac, 'engraving_solid_fraction': ef,
                            'battery_pocket_floor_solid_fraction': pf}
        ok = (ok and frac[f'{0.4:.2f}'] >= 0.9999 and frac[f'{left - 0.01:.2f}'] >= 0.9999
              and frac[f'{left + 0.05:.2f}'] < 0.9999 and ef <= 1e-4 and pf >= 0.9999)
    out['ok'] = ok
    return out


def x_gaps():
    """Clearances along X, set by the parameters (the YZ checks cannot see them)."""
    xs = T.key_x()
    return {'cheek_to_slot_side': round(P.CRANK_CHEEK[0] - P.SLOT[0], 3),
            'cheek_to_web': round(P.SLOT[1] - P.CRANK_CHEEK[1], 3),
            'crank_to_crank': round(min(b - a for a, b in zip(xs, xs[1:])) - 2 * P.CRANK_HALF, 3),
            'cap_to_opening_side': round(P.KEY_OPENING['half'] - P.KEY_HALF, 3),
            'cap_to_web': round(P.SLOT[1] - P.KEY_HALF, 3),
            'hook_to_hook_slot_outer_side': round(P.KEY_SLOT['dx'][1] - P.KEY_HOOK['dx'][1], 3),
            'key_body_to_cheek': round(P.CRANK_CHEEK[0] - P.KEY_BODY['half'], 3),   # > cap_to_opening_side: the
                                                                           # opening stops a key pushed sideways
            'rail_to_board_edge_at_-0.2': round(-0.2 - P.RAIL_Y[1], 3), 'rail_to_board_edge_at_-0.4': round(-0.4 - P.RAIL_Y[1], 3)}


# ---- SPEC2 rev 3: a crank dropped in with no rod (checks 2 and 3) ---------------------------------------------------
SAG = (P.ROD_HOLE_D - P.ROD_D) / 2                  # 0.175: face down, the rod lies on its holes' +Z side
PICK_TH = list(range(-30, 16, 2))                   # the grid the crank settles on (theta, dy)
PICK_DY = [round(-1.0 + 0.1 * i, 2) for i in range(19)]
DROP_TH, DROP_DY = (0, 4, 10), (-0.4, -0.2, 0.0, 0.2, 0.4)
PICK_LIMITS = {'rest': 0.30, 'path': 0.80}          # the 0.3 lead-ins alone; the tip's 0.8 flat in the 2.5 lead-in mouth


class Drop:
    """A crank (var) with no rod in the face-down tub (gravity +Z), the keys at their stop: lowered along +Z at (dy,
    theta) until it first meets the tub or a key (review 2's r2 method, per zone: the crank's section against the tub's
    and the key's shadows over the zone's band, as the sweep). Energy: -(its centre of mass's Z)."""

    def __init__(self, K, var):
        from shapely.prepared import prep
        self.obs = []
        for z in ZONES:
            t, k = K.sh[z]['tub'], affinity.translate(K.sh[z]['key'], 0, STOP)
            self.obs.append((z, K.C[var][z], prep(t), prep(k), prep(unary([t, k]))))
        c = K.m[f'crank{var}'].center_mass
        self.com = (float(c[1]), float(c[2]))
        self.cache = {}

    def land(self, dy, th):
        """(dz, 'zone/tub' or 'zone/key') at first contact, lowering from dz -1.5; (None, what) if it overlaps there."""
        key = (round(dy, 3), round(th, 3))
        if key not in self.cache:
            best, who = None, None
            for z, C0, pt, pk, pb in self.obs:
                g = affinity.translate(rot(C0, th), dy, -1.5)
                if pb.intersects(g):
                    best, who = None, z + ('/tub' if pt.intersects(g) else '/key') + ' (blocked)'
                    break
                if not pb.intersects(affinity.translate(g, 0, 3.0)):
                    continue
                lo, hi = 0.0, 3.0
                for _ in range(18):
                    m = (lo + hi) / 2
                    if pb.intersects(affinity.translate(g, 0, m)):
                        hi = m
                    else:
                        lo = m
                if best is None or lo - 1.5 < best:
                    best, who = lo - 1.5, z + ('/key' if pk.intersects(affinity.translate(g, 0, hi)) else '/tub')
            self.cache[key] = (best, who)
        return self.cache[key]

    def energy(self, dy, th):
        dz, _ = self.land(dy, th)
        return None if dz is None else -(crank.rotp(self.com, th)[1] + dz)

    @staticmethod
    def offset(dy, dz):
        """The bore's centre from the sagged rod's axis (0, +SAG)."""
        return math.hypot(dy, dz - SAG)


def pickup(K):
    """(2) SPEC2 rev 3: each crank (M and T) dropped at theta 0 / +4 / +10 and dy -0.4..+0.4 with no rod: where it lands
    (check 3), then its frictionless path on the (dy, theta) grid down to rest (steepest descent in energy), with the
    bore's offset from the sagged rod at every pose. PASS: <= 0.30 at rest and <= 0.80 on the whole way."""
    out = {}
    for var in 'MT':
        D = Drop(K, var)
        rows = []
        for th0 in DROP_TH:
            for dy0 in DROP_DY:
                dz0, who0 = D.land(dy0, th0)
                row = {'theta': th0, 'dy': dy0, 'lands_dz': None if dz0 is None else round(dz0, 3), 'on': who0}
                if dz0 is None:
                    row['ok'] = False
                    rows.append(row)
                    continue
                cur, path = (dy0, th0), [(dy0, th0)]
                for _ in range(400):
                    eb, best = D.energy(*cur), cur
                    for ddy in (-0.1, 0.0, 0.1):
                        for dth in (-2, 0, 2):
                            n = (round(cur[0] + ddy, 2), cur[1] + dth)
                            if n == cur or not (PICK_DY[0] - 1e-9 <= n[0] <= PICK_DY[-1] + 1e-9 and PICK_TH[0] <= n[1] <= PICK_TH[-1]):
                                continue
                            e = D.energy(*n)
                            if e is not None and e < eb - 1e-6:
                                eb, best = e, n
                    if best == cur:
                        break
                    cur = best
                    path.append(cur)
                offs = [D.offset(p[0], D.land(*p)[0]) for p in path]
                dz, who = D.land(*cur)
                row.update({'rests_theta': cur[1], 'rests_dy': cur[0], 'rests_dz': round(dz, 3), 'rests_on': who,
                            'land_offset': round(offs[0], 3), 'rest_offset': round(offs[-1], 3),
                            'worst_path_offset': round(max(offs), 3), 'path_poses': len(path),
                            'ok': offs[-1] <= PICK_LIMITS['rest'] and max(offs) <= PICK_LIMITS['path']})
                rows.append(row)
        out[var] = {'rows': rows, 'rest_offset_max': max((r.get('rest_offset', 9.0) for r in rows)),
                    'land_offset_max': max((r.get('land_offset', 9.0) for r in rows)),
                    'path_offset_max': max((r.get('worst_path_offset', 9.0) for r in rows)),
                    'drop_landing_dz': [min(r['lands_dz'] for r in rows if r['lands_dz'] is not None),
                                        max(r['lands_dz'] for r in rows if r['lands_dz'] is not None)],
                    'ok': all(r['ok'] for r in rows)}
    return out


def drop_verdict(pk):
    """(3) SPEC2 rev 3: FAIL if any drop pose is blocked or lands at dz < -0.05 (before its seat on the rod's line)."""
    return [f"crank-{v} theta {r['theta']:+d} dy {r['dy']:+.1f}: lands {r['lands_dz']} on {r['on']}"
            for v, p in pk.items() for r in p['rows'] if r['lands_dz'] is None or r['lands_dz'] < -0.05]


def pose_10_5(K):
    """SPEC2 open item 10.5 (pre-existing): at the free hang with no key (theta_free_no_key, about -17.5) the as-built
    +X cheek of SW2 was seen to overlap the tub by 0.012 with the bore 0.265 off toward 211 degrees. Here each cheek
    (both sides, each against the tub's shadow over its own band only) at the free hang: centred, 0.265 toward 211
    (the pin load's direction, which needs a press: a key on the crown and a plunger on the nose, so theta >= the rest
    angle, never the free hang) and 0.265 toward 90 (+Z: what gravity does to a crank on the rod in the face-down tub,
    the rod in its rings' play and the bore on the rod). Gaps (negative: overlap mm2)."""
    th = K.theta_free['M'][0]
    C = rot(K.C['M']['cheek'], th)
    out = {'theta': th}
    for sd in (1, -1):
        sh = shadow(K.m['tub'], [P.CRANK_CHEEK], K.xc, sides=(sd,))
        for nm, (ang, r) in (('centred', (0, 0.0)), ('0.265 toward 211', (211, 0.265)), ('0.265 toward 90', (90, 0.265))):
            g = affinity.translate(C, r * math.cos(math.radians(ang)), r * math.sin(math.radians(ang)))
            out[f"{'+X' if sd > 0 else '-X'} cheek, {nm}"] = round(d(g, sh), 4)
    return out


# ---- SPEC2 rev 3: the gate (checks 5, 6 and 7) --------------------------------------------------------------------------
def _slot_tub(tub_s):
    return tub_s.intersect(box(P.X0 - 1, 0.0, -7.0, 2.0, P.SEAM - 3, 4.0).val())


def gate_path(tub_s, lid_s, near):
    """(5) The gate lowered along +Z (in from the open back of the face-down tub) from its tip at z -10 to its seat,
    centred in X in its slot (0.075 each side) and in Y: its least distance to the tub without the slot's floor on the
    way and seated (>= 0.05: the lips' faces 0.075, the web to the mouth 0.10, the flange to the cavity 0.15), and where
    it first touches the tub (its seat: on the floor only). The lid >= 0.05 both seated centred (the 45-degree floor
    lifts it 0.075) and installed (its flange on the lips' faces: the rim 0.20 over the gate's top); reported too, the
    furthest it can sit from the lips (its flat on the sliver, 0.15 further +X and 0.15 higher); near (the board,
    display, midplate, strip refs) >= 0.5."""
    t = _slot_tub(tub_s)
    walls = t.cut(T.slot_floor(0.02).val())
    g0 = crank.gate().val()
    cx = (P.GATE_SLOT_X[2] - P.ROD_STOP_X0) / 2
    zb = P.GATE_SLOT['floor_z'] + P.ROD_STOP_X0 - P.X0

    def at(dz):
        return g0.moved(cq.Location(cq.Vector(cx, 0, dz)))

    dz, step, walls_min, seat = -10.0 - zb, 0.25, (9.0, None), None
    while dz <= 0.5:
        g = at(dz)
        dw = g.distance(walls)
        if dw < walls_min[0]:
            walls_min = (round(dw, 4), round(dz, 3))
        if g.distance(t) <= 1e-4:
            lo, hi = dz - step, dz                            # clear at lo, touching at hi
            for _ in range(16):
                m = (lo + hi) / 2
                if at(m).distance(t) <= 1e-4:
                    hi = m
                else:
                    lo = m
            seat = hi
            break
        dz += step
    rep = {'x_centred_by': round(cx, 3), 'from_dz': round(-10.0 - zb, 3), 'seat_dz': None if seat is None else round(seat, 4)}
    if seat is not None:
        gs = at(seat)
        dws = gs.distance(walls)
        if dws < walls_min[0]:
            walls_min = (round(dws, 4), round(seat, 3))
        rep['seated_to_walls'] = round(dws, 4)
        rep['seated_overlap_mm3'] = round(gs.intersect(t).Volume(), 6)
        rep['seated_to_lid'] = round(gs.distance(lid_s), 4)
    rep['walls_min'] = walls_min
    gi = crank.gate().val()
    rep['installed_to_lid'] = round(gi.distance(lid_s), 4)
    far = P.GATE_SLOT_X[2] - P.ROD_STOP_X0
    gf = gi.moved(cq.Location(cq.Vector(far, 0, -far)))
    rep['on_sliver'] = {'to_lid': round(gf.distance(lid_s), 4), 'overlap_tub_mm3': round(gf.intersect(t).Volume(), 6)}
    rep['installed_to'] = {k: round(gi.distance(v), 3) for k, v in near.items()}
    rep['ok'] = (seat is not None and walls_min[0] >= 0.05 and rep['seated_overlap_mm3'] <= 1e-6
                 and rep['seated_to_lid'] >= 0.05 and rep['installed_to_lid'] >= 0.05
                 and all(v >= 0.5 for v in rep['installed_to'].values()))
    return rep


def section_xz(m, y):
    """m's section at plane Y = y as a shapely region in (x, z)."""
    s = m.section(plane_origin=[0, y, 0], plane_normal=[0, 1, 0])
    g = Polygon()
    if s is None:
        return g
    for loop in s.discrete:
        if len(loop) >= 3:
            p = Polygon(loop[:, [0, 2]]).buffer(0)
            if p.area > 1e-7:
                g = g.symmetric_difference(p)
    return g


def gate_cam():
    """(6) The gate's bevel pushing the rod home, in the XZ plane of the rod's axis (y -2.5), the tub face down (the rod
    on its holes' +Z side, SAG): the gate (nominal X) lowered onto a rod whose tail is flush with the case side (X0),
    0.3 inside it and 0.2 proud. Where it first touches the rod (on the bevel, at the rod's end: it cams; on the rod's
    side: it stops), then the rod's tail as the gate goes on to its seat (the rod pushed as far as the gate reaches
    over its end's height). PASS: flush and 0.3 in both cam, the tail ends at ROD_STOP_X0 +- 0.01 with the flat over the
    rod's end past its axis; 0.2 proud stops the gate >= 1.0 short of its seat."""
    G = section_xz(to_mesh(crank.gate().val()), PY)
    r, zc = P.ROD_D / 2, PZ + SAG
    xf, zf = P.ROD_STOP_X0, P.GATE_SLOT['floor_z']
    zb = zf + xf - P.X0
    out = {}
    for nm, tail0 in (('flush', P.X0), ('0.3 in', P.X0 + 0.3), ('0.2 proud', P.X0 - 0.2)):
        rodr = sbox(tail0, zc - r, tail0 + P.ROD_CUT, zc + r)

        def touch(dz):
            g = affinity.translate(G, 0, dz)
            return g.intersects(rodr) and g.intersection(rodr).area > 1e-9

        lo, hi = -10.0 - zb, 0.0
        if not touch(hi):
            out[nm] = {'tail0': round(tail0, 3), 'first_contact': None}
            continue
        for _ in range(40):
            m = (lo + hi) / 2
            if touch(m):
                hi = m
            else:
                lo = m
        ov = affinity.translate(G, 0, hi + 2e-4).intersection(rodr)
        cxm, cz = ov.bounds[0], ov.centroid.y
        on_bevel = abs(cz - (zf + hi + (xf - ov.centroid.x))) < 0.01 and ov.centroid.x < xf
        at_end = cxm - tail0 < 0.005
        row = {'tail0': round(tail0, 3), 'first_contact_dz': round(hi, 3), 'contact_x': round(cxm, 3),
               'on_bevel': bool(on_bevel), 'on_rod_end': bool(at_end)}
        if at_end:
            tail = tail0
            for dz in list(np.arange(hi, 0.0, 0.01)) + [0.0]:
                band = affinity.translate(G, 0, dz).intersection(sbox(-20, zc - r + 1e-4, 20, zc + r - 1e-4))
                if not band.is_empty:
                    tail = max(tail, band.bounds[2])
            row.update({'cams': True, 'seated_tail_x': round(tail, 4),
                        'flat_past_axis_face_down': round(zf - zc, 3), 'flat_past_axis_face_up': round(zf - (PZ - SAG), 3)})
        else:
            row.update({'cams': False, 'stops_proud_mm': round(-hi, 3)})
        out[nm] = row
    f, i, p = out['flush'], out['0.3 in'], out['0.2 proud']
    out['ok'] = (all(x.get('cams') and x['on_bevel'] and abs(x['seated_tail_x'] - xf) <= 0.01 and x['flat_past_axis_face_down'] > 0
                     for x in (f, i)) and p.get('cams') is False and p['stops_proud_mm'] >= 1.0)
    return out


def section_xy(m, z):
    s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    g = Polygon()
    if s is None:
        return g
    for loop in s.discrete:
        if len(loop) >= 3:
            p = Polygon(loop[:, [0, 1]]).buffer(0)
            if p.area > 1e-7:
                g = g.symmetric_difference(p)
    return g


GATE_SHIFTS = (0.0, 0.05, -0.05, 0.10, -0.10)       # the web's play in the mouth: 0.10 a side


def gate_bearing(tub_s, zs=(-1.0, 0.6)):
    """(7) In plan (XY sections at zs of the built tub and gate: every chamfer and the round ends in), the gate at each
    Y offset of GATE_SHIFTS: its overlap with the tub there, its travel -X to contact, and, pushed so, the Y ranges on
    each side where its flange's outer face bears flat on a lip's face (within 0.003). PASS: no overlap and no travel
    at rest, >= 0.25 a side centred and >= 0.15 at +-0.10 (c1: 0.30 and 0.20)."""
    tm = to_mesh(_slot_tub(tub_s))
    gm = to_mesh(crank.gate().val())
    xl = P.GATE_SLOT_X[1]
    out = {}
    for z in zs:
        t, g0 = section_xy(tm, z), section_xy(gm, z)
        for sh in GATE_SHIFTS:
            g = affinity.translate(g0, 0, sh)
            ov = g.intersection(t).area if g.intersects(t) else 0.0
            lo, hi = 0.0, 0.6
            if ov <= 1e-7:
                for _ in range(30):
                    m = (lo + hi) / 2
                    gg = affinity.translate(g, -m, 0)
                    if gg.intersects(t) and gg.intersection(t).area > 1e-7:
                        hi = m
                    else:
                        lo = m
            gg = affinity.translate(g, -lo, 0)
            sides = {}
            for side, (ya, yb) in (('-Y', (-4.8, -3.0)), ('+Y', (-2.0, -0.2))):
                ys = [y for y in np.arange(ya, yb, 0.0025) if gg.contains(Point(xl + 0.0005, y))
                      and t.buffer(1e-6).contains(Point(xl - 0.0035, y))]
                sides[side] = [round(float(min(ys)), 4), round(float(max(ys)), 4)] if ys else None
            out[f'z {z:+.1f} shift {sh:+.2f}'] = {'z': z, 'shift': sh, 'overlap_mm2': round(ov, 6), 'travel': round(lo, 4),
                                                  'bearing': sides}
    for r in out.values():
        w = [b[1] - b[0] if b else 0.0 for b in r['bearing'].values()]
        need = 0.25 if r['shift'] == 0 else 0.15
        r['min_side'] = round(float(min(w)), 4)
        r['ok'] = bool(r['overlap_mm2'] <= 1e-6 and r['travel'] <= 0.002 and min(w) >= need - 1e-3)
    return out


def _near(solid, bb, margin):
    b = solid.BoundingBox()
    return not (b.xmin > bb.xmax + margin or b.xmax < bb.xmin - margin or b.ymin > bb.ymax + margin or
                b.ymax < bb.ymin - margin or b.zmin > bb.zmax + margin or b.zmax < bb.zmin - margin)


def run(shapes):
    """All of it for this build (shapes: build.py's parts). Returns the report; 'failures' lists what failed."""
    import time
    t0 = time.time()
    hwsol = hw.solids()
    tub_s, lid_s, mid_s = shapes['tub'].val(), shapes['lid'].val(), shapes['midplate'].val()
    rod_s = crank.rod().val()
    rep = {'static': [], 'rest': {}, 'sweep': {}, 'paths': {}, 'x_gaps': x_gaps(), 'logo': logo_over_slots(),
           'logo_back': logo_back_floor(lid_s)}
    Ks = [Key(r, tub_s, lid_s, mid_s, hwsol) for r in P.KEY_REFS]
    for K in Ks:
        rows, rest = static(K, rod_s)
        rep['static'] += rows
        rep['rest'][K.ref] = rest
    # the four keys' surroundings are the same inside |dx| 5.4 (tub.rail_segments): the sweeps and paths on each
    for K in Ks:
        rep['sweep'][K.ref] = sweep(K)
    rep['ring_mj'] = {K.ref: ring_mj(K) for K in Ks}
    rep['free_swing'] = {K.ref: free_swing(K) for K in Ks}
    cranks = [crank.build('M', K.xc).val() for K in Ks]
    others = {'lid': lid_s, 'midplate': mid_s, 'gate': shapes['gate'].val(), **{f'key_{K.ref}': K.key3 for K in Ks},
              **{r: hwsol[r] for r in (*P.KEY_REFS, 'PCB')}}
    rep['paths']['rod'] = rod_path(tub_s, cranks, others)
    # SPEC2 rev 3: the crank dropped in with no rod (2, 3), the gate (5, 6, 7), open item 10.5
    rep['pickup'] = {K.ref: pickup(K) for K in Ks}
    rep['pose_10_5'] = {K.ref: pose_10_5(K) for K in Ks}
    import refs
    gb = crank.gate().val().BoundingBox()
    near = {'midplate': mid_s, 'display': refs.display(thickness=hw.PANEL_T + hw.PANEL_T_TOL).val(),
            **{k: v for k, v in hwsol.items() if _near(v, gb, 3.0)},
            **({f'strip_{k}': w.val() for k, w in refs.strip().items()} if P.LIGHT_STRIP else {})}
    rep['gate'] = {'path': gate_path(tub_s, lid_s, near), 'cam': gate_cam(), 'bearing': gate_bearing(tub_s)}
    rep['paths']['crank_in'] = {K.ref: crank_in(K) for K in Ks}
    rep['paths']['board_in'] = {K.ref: board_in(K) for K in Ks}
    rep['paths']['key_in'] = {K.ref: key_in(K) for K in Ks}
    rep['theta_stop'] = THETA_STOP
    rep['theta_free_no_key'] = {K.ref: K.theta_free for K in Ks}
    rep['accepted_findings'] = [f"board in {ref}: {r['case']} dy {r['dy']:+.1f} held at theta 0 (not a free-hang angle): "
                                f"{r['first_plunger_contact']}" for ref, rows in rep['paths']['board_in'].items()
                                for r in rows if r.get('accepted_finding')]
    fails = []
    for r in rep['static']:
        if not r['expected']:
            fails.append(f"static {r['key']} {r['switch']} {r['dy']:+.1f}: {r['part']} x {r['with']} {r['mm3']} mm3")
    for ref, sw in rep['sweep'].items():
        fails += [f'sweep {ref}: {k} {sw[k]}' for k in sweep_verdict(sw)]
    fails += [f'ring to the MJTP housing {ref} (crank {CRANK_FLOAT} toward it, board {P.TUB_BOARD_DY} nearer): {r}'
              for ref, r in rep['ring_mj'].items() if not r['ok']]
    fails += [f"free swing {ref} (board out, face down; as sliced, grown, sagged; >= {r['min']}): {r['worst']}"
              for ref, r in rep['free_swing'].items() if not r['ok']]
    if not rep['paths']['rod']['ok']:
        fails.append('rod path')
    for ref, rows in rep['paths']['crank_in'].items():
        for k, v in rows.items():
            if not k.startswith('-10') and (v['rail'] < 0.3 or v['key_at_stop'] < 0.3):
                fails.append(f'crank in {ref} {k}: {v}')
    for ref, rows in rep['paths']['board_in'].items():
        fails += [f"board in {ref}: {r['case']} dy {r['dy']:+.1f} theta {r['theta']}: {r['first_plunger_contact']}, "
                  f"housing/board gap {r['housing_board_min_gap']}" for r in rows if r['required'] and not r['ok']]
    for ref, r in rep['paths']['key_in'].items():
        if not r['ok']:
            fails.append(f'key in {ref}: {r}')
    for ref, pk in rep['pickup'].items():
        fails += [f"pickup {ref} crank-{v}: rest {p['rest_offset_max']} (<= {PICK_LIMITS['rest']}), way "
                  f"{p['path_offset_max']} (<= {PICK_LIMITS['path']})" for v, p in pk.items() if not p['ok']]
        fails += [f'drop in {ref}: {x}' for x in drop_verdict(pk)]
    for k in ('path', 'cam'):
        if not rep['gate'][k]['ok']:
            fails.append(f"gate {k}: {rep['gate'][k]}")
    fails += [f'gate bearing {k}: {r}' for k, r in rep['gate']['bearing'].items() if not r['ok']]
    if not rep['logo']['ok']:
        fails.append(f"logo over the slots: {rep['logo']}")
    xg = rep['x_gaps']
    if xg['key_body_to_cheek'] < xg['cap_to_opening_side'] + 0.05:
        fails.append(f"x gaps: key body to cheek {xg['key_body_to_cheek']} not 0.05 over the key's X play "
                     f"{xg['cap_to_opening_side']}")
    if not rep['logo_back']['ok']:
        fails.append(f"back logo over the lid's floor: {rep['logo_back']}")
    rep['failures'] = fails
    rep['seconds'] = round(time.time() - t0, 1)
    return rep


def summary(rep):
    """Short printout for build.py's log."""
    lines = [f"bottom keys (crank spec checks 1, 2, 4; {rep['seconds']} s):"]
    exp = sorted({(r['part'], r['with'], r['expected']) for r in rep['static'] if r['expected']})
    un = [r for r in rep['static'] if not r['expected']]
    lines.append(f"  static (4 keys x MJTP/crank-M, TS365/crank-T x dy -0.2/0/+0.2): {len(un)} unexpected overlaps; "
                 f"expected: {', '.join(f'{a} x {b}' for a, b, _ in exp) or 'none'}")
    for r in un:
        lines.append(f"    {r}")
    rest = rep['rest'][P.KEY_REFS[0]]
    lines.append('  rest (theta deg, key lift): ' + '; '.join(f"{k} {v['theta']:+.2f} {v['key_lift']:+.3f}" for k, v in rest.items()))
    sw = rep['sweep'][P.KEY_REFS[1]]
    tf = rep['theta_free_no_key'][P.KEY_REFS[1]]
    lines.append(f"  free hang: on a key at its stop {rep['theta_stop']:+.1f}; with no key "
                 + ', '.join(f"crank-{v} {t:+.2f} (on the {z})" for v, (t, z) in tf.items()))
    lines.append(f"  sweep -13..+16 ({P.KEY_REFS[1]}; min / inside -4..+13 / below -13 to the free hang, no key):")
    for k, v in sw.items():
        mn = f"{v['min']:7.3f} at {v['at_deg']:+5.1f}   {v['inner_min']:7.3f}" if v['at_deg'] is not None else ' ' * 26
        ex = f"   {v['ext_min']:7.3f} at {v['ext_at_deg']:+6.2f}" if v.get('ext_min') is not None else ''
        lines.append(f"    {k:58s} {mn}{ex}")
    lines.append(f"  ring to the MJTP housing (crank {CRANK_FLOAT} toward it, board {P.TUB_BOARD_DY} nearer; >= {RING_MJ_MIN}): "
                 + '; '.join(f"{ref} {r['min']:.3f} at {r['at_deg']:+.1f} ({'PASS' if r['ok'] else 'FAIL'})"
                             for ref, r in rep['ring_mj'].items()))
    for ref, r in rep['free_swing'].items():
        lines.append(f"  free swing {ref} {r['range_deg'][0]:+.2f}..{r['range_deg'][1]:+.2f} (board out, face down; cheeks to the "
                     f"tub): CAD {r['cad']['gap']:.3f} at {r['cad']['at_deg']:+.1f}, as sliced {r['as_sliced']['gap']:.3f} at "
                     f"{r['as_sliced']['at_deg']:+.1f}, +{r['grow']} a face and sagged {r['sag']}: {r['worst']['gap']:.3f} at "
                     f"{r['worst']['at_deg']:+.1f} (>= {r['min']}: {'PASS' if r['ok'] else 'FAIL'}); roof over the rod "
                     f"{r['slot_roof_over_the_rod']}")
    lines.append(f"  rod path: {rep['paths']['rod']}")
    ci = rep['paths']['crank_in'][P.KEY_REFS[1]]
    lines.append('  crank in along +Z (rail / key at stop): ' + '; '.join(f"{k} {v['rail']:.2f}/{v['key_at_stop']:.2f}" for k, v in ci.items()))
    for r in rep['paths']['board_in'][P.KEY_REFS[1]]:
        lines.append(f"  board in: {r['case']:40s} dy {r['dy']:+.1f} theta {r['theta']:+.2f}: {r['first_plunger_contact']}, "
                     f"housing/board {r['housing_board_min_gap']}{'' if r['ok'] else '  FAIL'}")
    lines.append(f"  key in from inside: {rep['paths']['key_in'][P.KEY_REFS[1]]}")
    for ref, pk in rep['pickup'].items():
        lines.append(f"  pickup {ref} (no rod, keys at their stop; bore to the sagged rod): " + '; '.join(
            f"crank-{v} lands dz {p['drop_landing_dz'][0]:+.3f}..{p['drop_landing_dz'][1]:+.3f}, landing <= "
            f"{p['land_offset_max']:.3f}, way <= {p['path_offset_max']:.3f}, rest <= {p['rest_offset_max']:.3f} "
            f"({'PASS' if p['ok'] else 'FAIL'})" for v, p in pk.items()))
    r0 = rep['pickup'][P.KEY_REFS[1]]['M']['rows']
    lines.append('  drop in (crank-M, theta/dy: first contact): ' + '; '.join(
        f"{r['theta']:+d}/{r['dy']:+.1f} {r['lands_dz']:+.3f} {r['on']}" for r in r0 if r['lands_dz'] is not None))
    for ref, v in rep['pose_10_5'].items():
        lines.append(f"  open item 10.5 {ref}: {v}")
    g = rep['gate']
    lines.append(f"  gate path: {'PASS' if g['path']['ok'] else 'FAIL'} {g['path']}")
    lines.append(f"  gate cam: {'PASS' if g['cam']['ok'] else 'FAIL'} {g['cam']}")
    for k, r in g['bearing'].items():
        lines.append(f"  gate bearing {k}: {'PASS' if r['ok'] else 'FAIL'} overlap {r['overlap_mm2']} travel {r['travel']} "
                     f"bearing {r['bearing']} (min {r['min_side']})")
    lines.append(f"  x gaps: {rep['x_gaps']}")
    lines.append(f"  logo: {rep['logo']}")
    lines.append(f"  back logo: {rep['logo_back']}")
    lines.append(f"  accepted findings: {rep['accepted_findings'] or 'none'}")
    lines.append(f"  failures: {rep['failures'] or 'none'}")
    return '\n'.join(lines)
