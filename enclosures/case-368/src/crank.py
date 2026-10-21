"""Bottom keys' bell cranks (2026-09-26; params 'bottom keys'), their rod and its gate (the rod's left stop, SPEC2 rev
3), the TS365ZJ's envelope, and the crank's kinematics.

Each crank turns on the rod (a cut length of 1.75 mm PLA filament) under the skin in front of the board's edge. Its
parts, as YZ profiles extruded along X (dx from the key's centre), at theta 0:
  cheeks    |dx| 3.75..5.25, round the rod; each runs in a slot in the tub's rail with rail on both sides. A closed
            ring |dx| 4.05..5.25; the open C only in the inner 0.30, beside the TS365 housing (test 1, 2026-09-29).
            The ring's bore is round, its wall 0.75 or more (0.80 over the bore; 2026-09-30, 0.57 before)
  crossbar  |dx| <= 5.25, from the cheeks to the pad; the pad's crown (R 0.6) carries the key's flat pusher
  leg/nose  |dx| <= 1.30, down past the rail to the crowned nose (R 1.0) that pushes the plunger toward +Y
  belly     1.30 <= |dx| <= 5.25: the leg's body without the nose, under the crossbar. It takes the crossbar from
            62 to 24.5 MPa as a beam along X at a 20 N over-press (mechanics.crank_stress)
crank-M and crank-T differ only in the nose: 0.28 shorter on crank-T, for the TS365ZJ's plunger tip (-2.2 against the
MJTP1117's -1.92), so that either key rests at the same height with its own switch. The leg's 45-degree underside is
drawn tangent to each variant's own nose circle.

The crossbar-and-belly section (body_profile) is one outline, the same across |dx| <= 5.25: the crown and the flat top,
the crossbar's +Y face and the belly's top under the rail, the belly's 45-degree underside, a flat underside at
CRANK_UNDERSIDE and a 45-degree line up to the bed face. Its re-entrant corners are rounded (CRANK_FILLET), so the
torsion at a 20 N press is a finite, converged number (mechanics.crank_stress; 2026-09-27: the underside went from
-1.8 to -2.2 for it).

Printed on the pad end (y -7.70, the face the whole crank is clipped to), +Y up: every face that looks -Y is 45 degrees
or steeper, but for the tops of the bores: the ring's bore is round and closes at y -1.50 (a layer boundary) as a short
bridge held on both sides; the lip's is a teardrop pointing +Y, cut flat at -1.35.
"""
import math
import cadquery as cq
from shapely.geometry import Polygon, Point, box as sbox
from shapely.ops import unary_union
import params as P
from geom import box, xcyl, xz_prism, yz_prism

PY, PZ = P.ROD_AXIS
BIG = 20.0


def _sector(c, a0, a1, r, n=24):
    """(y, z) polygon of a circular sector about c from a0 to a1 degrees (0 = +Y, 90 = +Z)."""
    return [c] + [(c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
                   c[1] + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def teardrop(x0, x1, c, d, flat, toward):
    """A hole of diameter d along X through x0..x1, with a 45-degree point toward `toward` ('+y' or '-z': print-up
    for the crank on its pad end / the tub face down), cut flat `flat` from the centre."""
    r = d / 2
    k = r / math.sqrt(2)
    if toward == '+y':
        tri = [(c[0] + k, c[1] - k), (c[0] + r * math.sqrt(2), c[1]), (c[0] + k, c[1] + k), c]
        keep = box(x0 - 1, x1 + 1, -BIG, c[0] + flat, -BIG, BIG)
    else:
        tri = [(c[0] - k, c[1] - k), (c[0], c[1] - r * math.sqrt(2)), (c[0] + k, c[1] - k), c]
        keep = box(x0 - 1, x1 + 1, -BIG, BIG, c[1] - flat, BIG)
    return xcyl(x0, x1, c[0], c[1], d).union(yz_prism(tri, x0, x1).intersect(keep))


def _arc(c, r, a0, a1, n):
    """Points on the circle (c, r) from angle a0 to a1 (degrees, 0 = +Y, 90 = +Z), ends included."""
    return [(c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             c[1] + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def _fillet(p0, p1, p2, r):
    """The arc (from its tangent point on p1-p0 to the one on p1-p2) that rounds the corner p1 to radius r, in steps
    of at most 1 degree."""
    a = (p0[0] - p1[0], p0[1] - p1[1]); la = math.hypot(*a); a = (a[0] / la, a[1] / la)
    b = (p2[0] - p1[0], p2[1] - p1[1]); lb = math.hypot(*b); b = (b[0] / lb, b[1] / lb)
    half = math.acos(max(-1.0, min(1.0, a[0] * b[0] + a[1] * b[1]))) / 2
    d = r / math.tan(half)
    s = (a[0] + b[0], a[1] + b[1]); ls = math.hypot(*s); s = (s[0] / ls, s[1] / ls)
    c = (p1[0] + s[0] * r / math.sin(half), p1[1] + s[1] * r / math.sin(half))
    t1, t2 = (p1[0] + a[0] * d, p1[1] + a[1] * d), (p1[0] + b[0] * d, p1[1] + b[1] * d)
    a1 = math.degrees(math.atan2(t1[1] - c[1], t1[0] - c[0]))
    a2 = math.degrees(math.atan2(t2[1] - c[1], t2[0] - c[0]))
    if a2 - a1 > 180:
        a2 -= 360
    elif a1 - a2 > 180:
        a2 += 360
    return [t1] + _arc(c, r, a1, a2, max(2, int(math.ceil(abs(a2 - a1)))))[1:-1] + [t2]


def bed_corner():
    """The bed face's lower edge: the crown's circle at the pad end."""
    (cy, cz), R = P.CRANK_CROWN
    return (P.CRANK_PAD_END, cz - math.sqrt(R * R - (P.CRANK_PAD_END - cy) ** 2))


def body_profile():
    """The crossbar, crown and belly section (y, z) at theta 0, the same across |dx| <= CRANK_HALF, as one outline
    (shapely Polygon): from the bed face's lower corner 45 degrees down to the flat underside, the fillet onto the
    belly's 45-degree underside, the belly's foot, its top under the rail, the fillet up the crossbar's +Y face, the
    flat top, the fillet onto the crown, the crown over its top to the bed face (the crown's arc in 0.5-degree steps)."""
    (cy, cz), R = P.CRANK_CROWN
    zu, zt = P.CRANK_UNDERSIDE, P.CRANK_TOP
    by0, by1, bz = P.CRANK_BELLY_TOP
    f1, f2 = P.CRANK_BELLY_FOOT
    F = P.CRANK_FILLET
    y0, zb = bed_corner()
    y45 = y0 + (zb - zu)                                           # the 45-degree line from the bed corner reaches zu
    yb = f2[0] - (zu - f2[1])                                      # the belly's 45-degree underside reaches zu
    # the crown's fillet: a circle r on the flat top, touching the crown's circle
    r = F['crown']
    fc = (cy + math.sqrt((R + r) ** 2 - (zt + r - cz) ** 2), zt + r)
    af = math.degrees(math.atan2(cz - fc[1], cy - fc[0]))          # its tangent point on the crown, from fc
    ac = math.degrees(math.atan2(fc[1] - cz, fc[0] - cy))          # the same point, from the crown's centre
    atop = math.degrees(math.atan2(math.sqrt(R * R - (y0 - cy) ** 2), y0 - cy))   # the crown at the bed face
    pts = [(y0, zb), (y45, zu)]
    pts += _fillet((y45, zu), (yb, zu), f2, F['under'])
    pts += [f2, f1]
    pts += [(by1, bz)]
    pts += _fillet((by1, bz), (by0, bz), (by0, zt), F['top'])
    pts += [(by0, zt)]
    pts += _arc(fc, r, -90.0, af, max(2, int(math.ceil(abs(af + 90.0)))))
    n = max(2, int(round((atop - ac) / 0.5)))
    pts += _arc((cy, cz), R, ac, atop, n)[1:]
    pts += [(y0, cz + math.sqrt(R * R - (y0 - cy) ** 2))]
    return Polygon(_dedup(pts)).buffer(0)


def _dedup(pts, tol=1e-7):
    out = []
    for p in pts:
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > tol:
            out.append((float(p[0]), float(p[1])))
    if math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) <= tol:
        out.pop()
    return out


def leg_line(variant):
    """k of the leg's 45-degree underside y + z = k, tangent to the variant's nose circle."""
    nc = P.CRANK_NOSE_C[variant]
    return nc[0] + nc[1] - P.CRANK_NOSE_R * math.sqrt(2)


def leg_profile(variant, no_nose=False):
    """The leg's own section (|dx| <= CRANK_LEG_HALF) beyond the body: from the belly's top down to the nose, its
    45-degree underside tangent to the nose circle (so the nose's back prints at 45 degrees too) with the fillet
    where it meets the crossbar's flat underside, and the nose circle (shapely Polygon; no_nose: without the circle,
    which the solid takes as an exact cylinder)."""
    nc, R = P.CRANK_NOSE_C[variant], P.CRANK_NOSE_R
    k = leg_line(variant)
    zu = P.CRANK_UNDERSIDE
    by0, by1, bz = P.CRANK_BELLY_TOP
    t45 = (nc[0] - R / math.sqrt(2), nc[1] - R / math.sqrt(2))
    y0, zb = bed_corner()
    fil = _fillet((y0 + (zb - zu), zu), (k - zu, zu), t45, P.CRANK_FILLET['under'])
    g = Polygon(_dedup([(k - bz, bz), (by1, bz), nc, t45] + fil[::-1])).buffer(0)
    return g if no_nose else unary_union([g, Point(*nc).buffer(R, 256)]).buffer(0)


def _prism(g, x0, x1):
    return yz_prism([tuple(p) for p in g.exterior.coords[:-1]], x0, x1)


def cheek_trim2():
    """(y, z) half-plane beyond the second cheek trim: n . ((y, z) - ROD_AXIS) > d."""
    (n0, n1), d2 = P.CRANK_CHEEK_TRIM2
    u = (-n1, n0)                                                  # along the trim line
    p = (PY + d2 * n0, PZ + d2 * n1)
    return [(p[0] + 30 * u[0], p[1] + 30 * u[1]), (p[0] - 30 * u[0], p[1] - 30 * u[1]),
            (p[0] - 30 * u[0] + 30 * n0, p[1] - 30 * u[1] + 30 * n1), (p[0] + 30 * u[0] + 30 * n0, p[1] + 30 * u[1] + 30 * n1)]


# >>> shared crank cheek: the same text as the cheek in case-426/src/keys.py's shared crank block, so both cases
# print the same crank (build.py compares the two projects' crank STLs); keep the two in step
# The cheeks (test 1, 2026-09-29: the open C's jaw cracked off at the bore and cranks came off the rod). Each cheek is a
# closed ring round the rod over |dx| CRANK_CHEEK_RING['x0']..CRANK_CHEEK[1] (the 'ring', with a fill under it), and
# keeps the open C only in its inner 'lip', |dx| CRANK_CHEEK[0]..x0, beside the TS365 housing (whose corner is 1.04 from
# the rod's axis). One (y, z) outline for both zones, the top an arc R top_r about the rod under the 45-degree roof:
# cheek_yz is its 2D section (the checks'), cheek3d the solid, from the same data. The ring (Ian, 2026-09-30: thicker
# where it holds the rod) has a round bore (its top at y -1.50, a layer boundary, prints as a short bridge closed on
# both sides; the 1.9 ream takes out any sag) and its fill carried forward under the rod to ring_mj's frontier; the lip
# keeps the teardrop. This text reads only P.CRANK_CHEEK, P.CRANK_CHEEK_TRIM_Y, P.CRANK_CHEEK_TRIM2, P.CRANK_BORE,
# P.CRANK_CHEEK_RING, PY, PZ and cheek_trim2.
_CK_POLY = [(-6.2, -1.5), (-6.2, -0.625), (-3.075, 2.5), (-0.6, 2.5), (-0.6, 0.55), (-2.3, 0.0), (-2.3, -1.3)]
_CK_PAD = (-6.2, -4.0, -1.5, -0.6)        # y0, y1, z0, z1: the block from the cheek down to the pad end
_CK_C = (-80.0, 0.0, 3.0)                 # the lip's open C: a sector about the rod (a0, a1 degrees, R) and, below the
_CK_C_BOX = (-2.33, 0.0, -3.0, -0.95)     # rod on the housing's side, a box y0, y1, z0, z1 (z1 from the rod's axis)


def _ck_sector(a0, a1, r, n=24):
    """(y, z) points of a sector about the rod's axis from a0 to a1 degrees (0 = +Y, 90 = +Z)."""
    return [(PY, PZ)] + [(PY + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
                          PZ + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def _ck_teardrop():
    """The lip's bore point, 45 degrees toward +Y (print-up: the crank prints on its pad end), as (y, z) points. The
    lip's bore is its CRANK_BORE['d'] circle and this, cut flat CRANK_BORE['flat'] from the axis (its top overhangs the
    open C); the ring's is the circle alone."""
    r = P.CRANK_BORE['d'] / 2
    k = r / math.sqrt(2)
    return [(PY + k, PZ - k), (PY + r * math.sqrt(2), PZ), (PY + k, PZ + k), (PY, PZ)]


def _ck_lead_in(xf, sign):
    """CRANK_BORE['lead'] x 45 lead-in cone on the bore at face X xf, the part's material on the `sign` side of it: it
    catches the rod's tapered end as it is fed through."""
    B = P.CRANK_BORE
    return cq.Workplane(obj=cq.Solid.makeCone(B['d'] / 2 + B['lead'] + 0.05, B['d'] / 2 - 0.01, B['lead'] + 0.06,
                                              cq.Vector(xf - sign * 0.05, PY, PZ), cq.Vector(sign, 0, 0)))


def _ck_roof():
    """(y, z) region above the 45-degree roof z = y + roof_c: the cheek prints with no overhang, 0.8 of wall over the
    bore."""
    c = P.CRANK_CHEEK_RING['roof_c']
    return [(-20.0, 20.0), (-20.0, -20.0 + c), (20.0 - c, 20.0)]


def cheek_yz(zone):
    """The cheek's (y, z) section at theta 0 (shapely), the bore a hole, both trims applied: zone 'ring' (closed round
    the rod, the fill under it, a round bore) or 'lip' (the open C and the teardrop)."""
    R, B = P.CRANK_CHEEK_RING, P.CRANK_BORE
    disc = lambda r: Point(PY, PZ).buffer(r, 64)
    body = [Polygon(_CK_POLY), disc(1.75), disc(R['top_r']).intersection(sbox(PY - 9, PZ, PY + 9, PZ + 9))]
    if zone == 'ring':
        body.append(Polygon(R['fill']))
    c = unary_union(body).difference(Polygon(_ck_roof()))
    bore = disc(B['d'] / 2)
    if zone == 'lip':
        y0, y1, z0, z1 = _CK_C_BOX
        c = c.difference(unary_union([Polygon(_ck_sector(*_CK_C)), sbox(y0, z0, y1, PZ + z1)]))
        bore = unary_union([bore, Polygon(_ck_teardrop())]).intersection(sbox(PY - 9, PZ - 9, PY + B['flat'], PZ + 9))
    y0, y1, z0, z1 = _CK_PAD
    c = unary_union([c.difference(bore), sbox(y0, z0, y1, z1)])
    c = c.intersection(sbox(-20.0, -20.0, P.CRANK_CHEEK_TRIM_Y, 20.0))       # clear of a board edge at -0.4
    return c.difference(Polygon(cheek_trim2())).buffer(0)


def _ck_zone(x0, x1, zone):
    """One zone of a cheek's solid over x0..x1, before the lead-ins and the trims."""
    R, B = P.CRANK_CHEEK_RING, P.CRANK_BORE
    c = yz_prism(_CK_POLY, x0, x1).union(xcyl(x0, x1, PY, PZ, 3.5))
    c = c.union(xcyl(x0, x1, PY, PZ, 2 * R['top_r']).intersect(box(x0 - 1, x1 + 1, -20.0, 20.0, PZ, 20.0)))
    if zone == 'ring':
        c = c.union(yz_prism(list(R['fill']), x0, x1))
    c = c.cut(yz_prism(_ck_roof(), x0 - 1, x1 + 1))
    bore = xcyl(x0 - 1, x1 + 1, PY, PZ, B['d'])
    if zone == 'lip':
        y0, y1, z0, z1 = _CK_C_BOX
        c = c.cut(yz_prism(_ck_sector(*_CK_C), x0 - 1, x1 + 1)).cut(box(x0 - 1, x1 + 1, y0, y1, z0, PZ + z1))
        bore = bore.union(yz_prism(_ck_teardrop(), x0 - 1, x1 + 1).intersect(
            box(x0 - 2, x1 + 2, -20.0, PY + B['flat'], -20.0, 20.0)))
    c = c.cut(bore)
    y0, y1, z0, z1 = _CK_PAD
    return c.union(box(x0, x1, y0, y1, z0, z1))


def cheek3d(x0, x1):
    """One cheek's solid over x0..x1 (both on one side of the key's centre): the lip next to the key's centre, the ring
    outboard of it; the bore's lead-in on both outer faces, and on the ring's inner face where the lip leaves it bare
    (its C and its teardrop's point: on the +X cheek the rod's tip meets that face after the lip). The trims are the
    caller's (build)."""
    s = 1 if x0 > 0 else -1
    xr = s * P.CRANK_CHEEK_RING['x0']
    if s > 0:
        lip, ring = _ck_zone(x0, xr, 'lip'), _ck_zone(xr, x1, 'ring')
    else:
        ring, lip = _ck_zone(x0, xr, 'ring'), _ck_zone(xr, x1, 'lip')
    c = lip.union(ring)
    for xf, sg in ((x0, 1), (x1, -1)):
        c = c.cut(_ck_lead_in(xf, sg))
    y0, y1, z0, z1 = _CK_C_BOX
    tip = yz_prism(_ck_teardrop(), xr - 1, xr + 1).intersect(
        box(xr - 1, xr + 1, -20.0, PY + P.CRANK_BORE['flat'], -20.0, 20.0))
    csec = yz_prism(_ck_sector(*_CK_C), xr - 1, xr + 1).union(box(xr - 1, xr + 1, y0, y1, z0, PZ + z1)).union(tip)
    return c.cut(_ck_lead_in(xr, s).intersect(csec))
# <<< shared crank cheek


def build(variant='M', xc=0.0, theta=0.0):
    """One crank ('M' or 'T'), its key centre at X xc, turned theta degrees (pressed +)."""
    h, (c0, c1), lh = P.CRANK_HALF, P.CRANK_CHEEK, P.CRANK_LEG_HALF
    cr = _prism(body_profile(), -h, h)
    for a, b in ((-c1, -c0), (c0, c1)):
        ch = cheek3d(a, b).intersect(box(a - 1, b + 1, -BIG, P.CRANK_CHEEK_TRIM_Y, -BIG, BIG))
        cr = cr.union(ch.cut(yz_prism(cheek_trim2(), a - 1, b + 1)))
    nc = P.CRANK_NOSE_C[variant]
    cr = cr.union(_prism(leg_profile(variant, no_nose=True), -lh, lh).union(xcyl(-lh, lh, nc[0], nc[1], 2 * P.CRANK_NOSE_R)))
    cr = cr.intersect(box(-h - 1, h + 1, P.CRANK_PAD_END, BIG, -BIG, BIG)).clean()
    if theta:
        cr = rotate(cr, theta)
    return cr.translate((xc, 0, 0)) if xc else cr


def rotate(wp, theta):
    """Turn about the rod's axis; + is pressed (the pad moves -Z, the nose +Y)."""
    return wp.rotate((0, PY, PZ), (1, PY, PZ), theta)


def rod(d=P.ROD_D, tail=None):
    """The rod (ROD_CUT long), its square tail at X tail (default: centred in its end play), its tip at +X tapered to a
    flat (ROD_TIP): the end that goes in first."""
    x0 = (P.ROD_SPAN[0] + P.ROD_SPAN[1]) / 2 - P.ROD_CUT / 2 if tail is None else tail
    T = P.ROD_TIP
    x1 = x0 + P.ROD_CUT - T['taper']
    tip = cq.Solid.makeCone(d / 2, T['flat'] / 2, T['taper'], cq.Vector(x1, PY, PZ), cq.Vector(1, 0, 0))
    return xcyl(x0, x1, PY, PZ, d).union(cq.Workplane(obj=tip))


# >>> shared gate: the side gate (SPEC2 rev 3), the same code and numbers as case-426/src/keys.py
# (the 4.26 project) so both cases print the same gate; keep the two in step
def gate_plan():
    """The gate's T in plan, (X, y) as a shapely polygon: the web in the mouth, flush with the outer face X0, and the
    flange behind the lips, its bed-side (inner) vertical edges chamfered for elephant foot and its outer ones, which
    bear on the lips, only broken."""
    G = P.GATE
    x0 = round(P.X0, 6)          # to 6 dp: the 4.26's X0 is -4.089999999999998, which splits a face differently
    xl, xf = x0 + G['web'], x0 + G['web'] + G['flange']
    (y0, y1), c, b = G['flange_y'], G['bed_chamfer'], G['bearing_break']
    flange = Polygon([(xl, y0 + b), (xl + b, y0), (xf - c, y0), (xf, y0 + c), (xf, y1 - c), (xf - c, y1), (xl + b, y1), (xl, y1 - b)])
    web = Polygon([(x0, G['web_y'][0]), (xl, G['web_y'][0]), (xl, G['web_y'][1]), (x0, G['web_y'][1])])
    return unary_union([flange, web]).buffer(0)


def gate_side():
    """The gate's side view, (X, z): top GATE['top_clr'] under the rim with the web's outer top edge chamfered (on the
    tub's seam chamfer), the inner face flat at ROD_STOP_X0 from the top down to the slot's floor_z, then the
    45-degree bevel to the outer face (its tip, at the outer face, stays sharp: a chamfer there would land a flush
    tail on its blunt part)."""
    G = P.GATE
    x0, xf = round(P.X0, 6), round(P.ROD_STOP_X0, 6)
    top, tc, zf = P.SEAM + G['top_clr'], G['top_chamfer'], P.GATE_SLOT['floor_z']
    return [(x0, top + tc), (x0 + tc, top), (xf, top), (xf, zf), (x0, zf + (xf - x0))]


def gate(pose='installed'):
    """The side gate. 'installed': in the case, seated on the slot's floor, its flange on the lips (the CAD frame);
    'print': its inner face (the rod's stop) on the bed, the flange the first layers, the bevel a 45-degree
    overhang and the pull hole vertical, moved to X, Y, Z >= 0."""
    G = P.GATE
    pl = gate_plan()
    ys = (pl.bounds[1] - 1, pl.bounds[3] + 1)
    side = gate_side()
    z0, z1 = min(z for _, z in side) - 1, max(z for _, z in side) + 1
    plan = cq.Workplane('XY').polyline(list(pl.exterior.coords)[:-1]).close().extrude(z1 - z0).translate((0, 0, z0))
    g = plan.intersect(xz_prism(side, *ys))
    yc = sum(G['web_y']) / 2
    g = g.cut(xcyl(round(P.X0, 6) - 0.1, round(P.X0, 6) + G['pull_depth'], yc, G['pull_z'], G['pull_d'])).clean()
    if pose == 'print':
        g = g.rotate((0, 0, 0), (0, 1, 0), 90)                   # +X (the inner face) to -Z: onto the bed
        bb = g.val().BoundingBox()
        g = g.translate((-bb.xmin, -bb.ymin, -bb.zmin))
    return g
# <<< shared gate


def ts365(xc, dy=0.0, worst=False):
    """TS365ZJ envelope at a bottom key (housing and plunger), dy further +Y than nominal; worst: the plunger tip out
    to -2.4 and high (the drawing's extremes). Returns (housing, plunger)."""
    T = P.TS365
    tip = (T['tip_y'][0] if worst else T['tip_y_nom']) + dy
    z0, z1 = T['plunger_z_worst'] if worst else T['plunger_z_nom']
    hx, px = T['housing_half_x'], T['plunger_half_x']
    housing = box(xc - hx, xc + hx, T['housing_y'] + dy, 6.0, T['body_z'][0], T['body_z'][1])
    plunger = box(xc - px, xc + px, tip, T['housing_y'] + dy + 0.2, z0, z1)
    return housing, plunger


# ---- kinematics (YZ) -------------------------------------------------------------------------------------------
def rotp(pt, theta):
    t = math.radians(theta)
    vy, vz = pt[0] - PY, pt[1] - PZ
    return (PY + vy * math.cos(t) - vz * math.sin(t), PZ + vy * math.sin(t) + vz * math.cos(t))


def key_lift(theta):
    """How far the key's pusher rises (+Z) from its theta-0 height when the crank turns theta: it rides the crown."""
    c = P.CRANK_CROWN[0]
    return rotp(c, theta)[1] - c[1]


def rest_theta(face_y, variant):
    """The angle at which the nose's front touches a plunger face at Y face_y (the key resting on the crown)."""
    nc = P.CRANK_NOSE_C[variant]
    f = lambda th: rotp(nc, th)[0] + P.CRANK_NOSE_R - face_y
    lo, hi = -40.0, 40.0
    for _ in range(60):
        m = (lo + hi) / 2
        if f(lo) * f(m) <= 0:
            hi = m
        else:
            lo = m
    return (lo + hi) / 2


def nose_contact_z(theta, variant):
    """Z of the nose's front point (where it meets a flat plunger face) at theta."""
    return rotp(P.CRANK_NOSE_C[variant], theta)[1]


def theta_for_key_travel(travel, theta_rest):
    """The crank angle at which the key has moved `travel` down (-Z) from its rest at theta_rest."""
    lo, hi = theta_rest, theta_rest + 60.0
    for _ in range(60):
        m = (lo + hi) / 2
        if key_lift(theta_rest) - key_lift(m) < travel:
            lo = m
        else:
            hi = m
    return (lo + hi) / 2
