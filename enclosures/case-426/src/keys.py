"""Bottom-row keys (Rev L): a straight key that slides toward -Z, and a bell crank that turns the
press into the +Y push the right-angle switches need.

  key    slides in Z between the rail's -Y face (its +Y guide) and the chin wall. Its flat pusher rests on
         the crank's crowned pad, so it sits where its switch puts it. Hook keys (test 2, 2026-09-30): no drag
         leaf, slit or bump; two rigid hooks on its chin side, one at each X end (KEY_HOOK), run in two slots
         in the chin wall (tub.key_slots, open to the rim) and stop flat under the slot's roof KEY_W_OUT above
         rest, so face down the key drops onto them level, and it cannot leave through the face: keys go in and
         come out from inside only. It prints on its -X end (+X up): the -X hook starts on the bed, the +X
         hook's -X face and the body's -X step are 45 degrees, and the bed end comes in KEY_BED_END (a 0.4 x 45
         chamfer)
  crank  two cheeks round a 1.75 mm PLA filament rod (each a closed ring over |dx| 4.05..5.25, the open C
         only in its inner 0.30, beside the TS365 housing: test 1), a crossbar with the crowned pad, a centre leg with
         a crowned nose on the plunger, and a belly that stiffens the crossbar between leg and cheeks.
         Lever 4.95 : 2.95, so the finger pushes 0.596 x the switch force before friction. crank-M suits
         the MJTP1117, crank-T (nose 0.28 shorter) the TS365ZJ on the JLC boards.
  rail   (tub.py) hangs from the skin: closed rings round the rod beside each crank, open seats under the
         switches, a slot for each cheek; webs tie it to the chin wall.

Every YZ profile is the spec's (layout.json, s4/geom4.py): shapely polygons in (y, z), extruded along X.
dx is X from the key centre (the switch plunger's X). theta turns a crank about the rod, + = pressed;
0 is crank-M's nose on the MJTP plunger's nominal face.
"""
import math
import cadquery as cq
from shapely.geometry import Polygon, Point, box as sbox
from shapely.ops import unary_union
import hw
import params as P
from geom import box, xcyl, xz_prism, yz_prism, zcyl

ROD = P.ROD_YZ
TOP = P.Z_FRONT + P.KEY_CAP['proud']          # cap top at rest


def circ(c, r):
    return Point(*c).buffer(r, 64)


def sector(c, a0, a1, r=4.0, n=40):
    pts = [c] + [(c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
                  c[1] + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]
    return Polygon(pts)


def teardrop(c, r, flat, toward):
    """A round hole with a 45-degree point toward print-up, cut flat `flat` from the centre so the point
    never prints as a sharp roof. toward 'y': +Y (a crank printed on its pad end); 'z-': -Z (the
    face-down tub)."""
    k = r * math.sqrt(2)
    s = r / math.sqrt(2)
    if toward == 'z-':
        tri = Polygon([(c[0] - s, c[1] - s), (c[0], c[1] - k), (c[0] + s, c[1] - s), c])
        clip = sbox(c[0] - 9, c[1] - flat, c[0] + 9, c[1] + 9)
    else:
        tri = Polygon([(c[0] + s, c[1] - s), (c[0] + k, c[1]), (c[0] + s, c[1] + s), c])
        clip = sbox(c[0] - 9, c[1] - 9, c[0] + flat, c[1] + 9)
    return unary_union([circ(c, r), tri]).intersection(clip)


# ---- crank profiles (theta 0) --------------------------------------------------------------------
# The crank is the same solid in both case projects (4.26 here, 3.68 in enclosures/case-368, whose
# crank.py this section follows line for line): the crossbar, crown and belly are one (y, z) outline across
# |dx| <= 5.25 (body_profile); the leg adds its 45-degree underside, tangent to the variant's nose circle, and the
# nose (|dx| <= 1.30); the cheeks carry the bore. Its re-entrant corners are rounded (CRANK_FILLET), so the torsion
# at a 20 N press is a finite, converged number (mechanics.overpress, Prandtl's stress function).
PY, PZ = ROD
BIG = 20.0


# >>> shared crank: copied from case-368/src/crank.py (the 3.68 project) so both cases
# print the same crank; keep the two in step
_CROWN = (P.CRANK_PAD['c'], P.CRANK_PAD['r'])


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
    (cy, cz), R = _CROWN
    return (P.CRANK_PAD['end'], cz - math.sqrt(R * R - (P.CRANK_PAD['end'] - cy) ** 2))


def body_profile():
    """The crossbar, crown and belly section (y, z) at theta 0, the same across |dx| <= CRANK_CHEEK[1], as one outline
    (shapely Polygon): from the bed face's lower corner 45 degrees down to the flat underside, the fillet onto the
    belly's 45-degree underside, the belly's foot, its top under the rail, the fillet up the crossbar's +Y face, the
    flat top, the fillet onto the crown, the crown over its top to the bed face (the crown's arc in 0.5-degree steps)."""
    (cy, cz), R = _CROWN
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
    nc = P.CRANK_NOSE[variant]
    return nc[0] + nc[1] - P.CRANK_NOSE_R * math.sqrt(2)


def leg_profile(variant, no_nose=False):
    """The leg's own section (|dx| <= CRANK_LEG) beyond the body: from the belly's top down to the nose, its
    45-degree underside tangent to the nose circle (so the nose's back prints at 45 degrees too) with the fillet
    where it meets the crossbar's flat underside, and the nose circle (shapely Polygon; no_nose: without the circle,
    which the solid takes as an exact cylinder)."""
    nc, R = P.CRANK_NOSE[variant], P.CRANK_NOSE_R
    k = leg_line(variant)
    zu = P.CRANK_UNDERSIDE
    by0, by1, bz = P.CRANK_BELLY_TOP
    t45 = (nc[0] - R / math.sqrt(2), nc[1] - R / math.sqrt(2))
    y0, zb = bed_corner()
    fil = _fillet((y0 + (zb - zu), zu), (k - zu, zu), t45, P.CRANK_FILLET['under'])
    g = Polygon(_dedup([(k - bz, bz), (by1, bz), nc, t45] + fil[::-1])).buffer(0)
    return g if no_nose else unary_union([g, Point(*nc).buffer(R, 256)]).buffer(0)


def cheek_trim2():
    """(y, z) half-plane beyond the second cheek trim: n . ((y, z) - ROD_AXIS) > d."""
    (n0, n1), d2 = P.CRANK_CHEEK_TRIM2
    u = (-n1, n0)                                                  # along the trim line
    p = (PY + d2 * n0, PZ + d2 * n1)
    return [(p[0] + 30 * u[0], p[1] + 30 * u[1]), (p[0] - 30 * u[0], p[1] - 30 * u[1]),
            (p[0] - 30 * u[0] + 30 * n0, p[1] - 30 * u[1] + 30 * n1), (p[0] + 30 * u[0] + 30 * n0, p[1] + 30 * u[1] + 30 * n1)]


# >>> shared crank cheek: the same text as the cheek in case-368/src/crank.py's shared cheek block, so both cases
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
# <<< shared crank


PAD_END = P.CRANK_PAD['end']
BODY = body_profile()
# the checks name the body's parts: the crown (the key's designed contact: the body within 0.001 of the crown's
# circle, so its arc is the body's own), the crossbar (to the rail's -Y face at -4.65) and the belly beyond it
def _areas(g):
    """Only the areas of a shapely result (a cut along an edge can leave lines and points beside them)."""
    return unary_union([q for q in getattr(g, 'geoms', [g]) if q.geom_type in ('Polygon', 'MultiPolygon') and q.area > 1e-9])


_CROWN_ZONE = circ(P.CRANK_PAD['c'], P.CRANK_PAD['r'] + 0.001)
CROWN = _areas(BODY.intersection(_CROWN_ZONE))
CROSSBAR = _areas(BODY.difference(_CROWN_ZONE).intersection(sbox(-9, -9, P.CRANK_BELLY_TOP[0], 9)))
BELLY = _areas(BODY.intersection(sbox(P.CRANK_BELLY_TOP[0], -9, 9, 9)))
CHEEK = cheek_yz('lip')         # the checks' cheek with X ignored (the housings'): the lip, the open C


def leg(variant):
    """The leg's section with its nose (|dx| <= CRANK_LEG), beyond the body."""
    return leg_profile(variant)


def leg_body(variant):
    """The leg without its nose circle (the checks' 'leg': the nose is the part that meets the plunger)."""
    return leg_profile(variant, no_nose=True)


def crank_bore():
    return teardrop(ROD, P.CRANK_BORE['d'] / 2, P.CRANK_BORE['flat'], toward='y')


# ---- rail profiles ------------------------------------------------------------------------------
def rail_outer(kind, lip=P.LIP):
    """Outer YZ profile of a rail segment, 0.01 up into the skin. 'ring': closed round the rod, 0.4
    chamfers on its lower corners. 'centre': the open seat's segment (the old rail's profile with its +Y
    face at RAIL_Y[1]); 'slot': over a cheek, only what is above the slot's roof."""
    a, b = P.RAIL_Y
    top = lip + 0.01
    if kind == 'ring':
        zb = P.RAIL_RING_BOTTOM
        return Polygon([(a, top), (a, zb + 0.4), (a + 0.4, zb), (b - 0.4, zb), (b, zb + 0.4), (b, top)])
    outer = Polygon([(a, top), (a, -0.575), (a + 0.4, -0.975), (-2.8, -0.975), (-2.5, -0.62), (-1.6, -0.62),
                     (b, -0.62 + (b + 1.6) * 0.82 / 1.3), (b, top)])
    if kind == 'slot':
        return outer.intersection(sbox(a - 1, P.SLOT_ROOF, b + 1, top))
    return outer


def rod_hole():
    """The hole the rod runs in, through the side wall and every rail segment: a teardrop pointing -Z
    (print-up in the face-down tub), flat 0.65 above the ring's bottom."""
    return teardrop(ROD, P.ROD_HOLE_D / 2, 1.15, toward='z-')


def seat_mouth():
    return sector(ROD, *P.RAIL_SEAT_MOUTH)


# ---- solids -------------------------------------------------------------------------------------
def extrude(poly, x0, x1):
    """A shapely (y, z) polygon, holes kept, extruded along X."""
    out = None
    for g in getattr(poly, 'geoms', [poly]):
        if g.area < 1e-6:
            continue
        s = _prism(list(g.exterior.coords)[:-1], x0, x1)
        for r in g.interiors:
            s = s.cut(_prism(list(r.coords)[:-1], x0 - 0.1, x1 + 0.1))
        out = s if out is None else out.union(s)
    return out


def _prism(pts, x0, x1):
    q = []
    for p in pts:                                  # shapely leaves near-duplicate vertices; OCC refuses them
        if not q or math.dist(p, q[-1]) > 1e-4:
            q.append(p)
    if math.dist(q[0], q[-1]) <= 1e-4:
        q.pop()
    pts = q
    return cq.Workplane('YZ').polyline(pts).close().extrude(x1 - x0).translate((x0, 0, 0))


def key_x(ref):
    return hw.switch_plunger(ref)['face'][0]


def _yz(g, x0, x1):
    return yz_prism([tuple(q) for q in g.exterior.coords[:-1]], x0, x1)


def crank(variant='M', xc=0.0, theta=0.0):
    """One crank ('M' or 'T') at key centre xc, turned theta degrees about the rod (+ = pressed)."""
    c0, c1 = P.CRANK_CHEEK
    h, lh = c1, P.CRANK_LEG
    cr = _yz(BODY, -h, h)
    for a, b in ((-c1, -c0), (c0, c1)):
        ch = cheek3d(a, b).intersect(box(a - 1, b + 1, -BIG, P.CRANK_CHEEK_TRIM_Y, -BIG, BIG))
        cr = cr.union(ch.cut(yz_prism(cheek_trim2(), a - 1, b + 1)))
    nc = P.CRANK_NOSE[variant]
    cr = cr.union(_yz(leg_profile(variant, no_nose=True), -lh, lh).union(xcyl(-lh, lh, nc[0], nc[1], 2 * P.CRANK_NOSE_R)))
    cr = cr.intersect(box(-h - 1, h + 1, PAD_END, BIG, -BIG, BIG)).clean()
    if theta:
        cr = cr.rotate((0, PY, PZ), (1, PY, PZ), theta)
    return cr.translate((xc, 0, 0)) if xc else cr


def crown_shift(theta):
    """Rise of the pad crown's centre (so of a key resting on it) when the crank turns theta."""
    t = math.radians(theta)
    vy, vz = P.CRANK_PAD['c'][0] - ROD[0], P.CRANK_PAD['c'][1] - ROD[1]
    return vy * math.sin(t) + vz * math.cos(t) - vz


def key_profiles():
    """(y, z) polygons of the key at rest: 'body' (|dx| <= KEY_BODY half), 'cheek' (over the cheeks) and 'hook' (a
    hook's section, from its tip to 0.01 into the cap's chin face). Above the pusher's stop_z1 the key's chin side is
    the cap's chin face, all the way up (the old leaf zone solid); below it the pusher's chin end is the chin-side stop."""
    cy0, cy1 = P.KEY_CAP['y']
    pu = P.KEY_PUSHER
    common = unary_union([sbox(pu['y'][0], pu['z'][0], pu['y'][1], pu['z'][1]),
                          sbox(cy0, pu['z'][1] - 0.01, P.KEY_CHEEK_ZONE['y'], TOP)])
    body = unary_union([common, sbox(pu['y'][1] - 0.01, P.KEY_BODY['z0'], cy1, TOP)])
    cheek = unary_union([common, sbox(pu['y'][1] - 0.01, pu['z'][0], P.KEY_CHEEK_ZONE['y'], TOP),
                         sbox(P.KEY_CHEEK_ZONE['y'] - 0.01, P.KEY_CHEEK_ZONE['z0'], cy1, TOP)])
    chin = sbox(cy0 - 2.0, pu['stop_z1'], cy0, TOP + 1.0)
    z0, z1 = P.KEY_HOOK_Z
    return {'body': body.difference(chin), 'cheek': cheek.difference(chin), 'hook': sbox(P.KEY_HOOK['tip'], z0, cy0 + 0.01, z1),
            'root': sbox(P.KEY_HOOK['tip'], pu['z'][0], cy0 + 0.01, z1)}


def _hooks():
    """The two hooks at |dx| KEY_HOOK dx: the -X one a block (its -X face on the bed as the key prints), the +X one
    with its -X face run back 45 degrees in plan from its inner edge at the tip to the cap's chin face (KEY_HOOK_LEAD),
    so it builds up from the cap with no overhang."""
    H, y0, e = P.KEY_HOOK, P.KEY_CAP['y'][0], 0.01
    (x0, x1), (z0, z1) = H['dx'], P.KEY_HOOK_Z
    minus = box(-x1, -x0, H['tip'], y0 + e, z0, z1)
    plus = (cq.Workplane('XY').polyline([(x0 - P.KEY_HOOK_LEAD - e, y0 + e), (x1, y0 + e), (x1, H['tip']), (x0, H['tip'])])
            .close().extrude(z1 - z0).translate((0, 0, z0)))
    return minus.union(plus)


def _yz_section(shape, x):
    """The solid's section at X x, as a shapely polygon in (y, z) (off its mesh: even-odd over the section's loops)."""
    import trimesh
    vs, ts = shape.val().tessellate(0.002, 0.05)
    m = trimesh.Trimesh([(v.x, v.y, v.z) for v in vs], ts, process=True)
    g = Polygon()
    for loop in m.section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0]).discrete:
        if len(loop) >= 3:
            g = g.symmetric_difference(Polygon(loop[:, [1, 2]]).buffer(0))
    return g


def _bed_end(k):
    """The bed end (-X) as printed on it: in each of its first two layers (0.2 each) the key's outline comes in
    KEY_BED_END (the outline taken 0.45 in, through the root, KEY_ROOT), the same as a 0.4 x 45 chamfer all round at the
    layers' mid-planes, so the first layer's elephant foot stays inside the cap's outline."""
    h = P.KEY_CAP['half']
    sec = _yz_section(k, -h + 0.45)
    for i, e in enumerate(P.KEY_BED_END):
        xa, xb = -h + P.LAYER * i, -h + P.LAYER * (i + 1)
        keep = sec.buffer(-e, join_style=2)
        kp = None
        for g in getattr(keep, 'geoms', [keep]):
            s = yz_prism(list(g.exterior.coords)[:-1], xa - 0.02, xb + 0.01)
            kp = s if kp is None else kp.union(s)
        k = k.cut(box(xa - 0.01, xb, -12, 0, -3, 10).cut(kp))
    return k


def key(xc=0.0, lift=0.0):
    """One key at key centre xc, `lift` above rest (the same solid as printed and as assembled: nothing on it flexes)."""
    pr = key_profiles()
    h, hb = P.KEY_CAP['half'], P.KEY_BODY['half']
    y0, y1 = P.KEY_CAP['y']
    k = extrude(pr['body'], -hb, hb)
    for s in (-1, 1):
        k = k.union(extrude(pr['cheek'], *sorted((s * (hb - 0.01), s * h))))
    k = k.union(_hooks())
    # the root (KEY_ROOT): at the bed end the chin side is solid out to the hooks' tip, the pusher's underside to the
    # hooks' top, so the bed end's chamfer (_bed_end) leaves no thin stub of the -X hook or of the pusher's chin end
    k = k.union(extrude(pr['root'], -h, -h + P.KEY_ROOT))
    # the body's -X step (it faces the bed in the print): 45 degrees from the cheek zone's floor down to the body's
    Bd, CZ = P.KEY_BODY, P.KEY_CHEEK_ZONE
    k = k.cut(xz_prism([(-hb - 0.01, CZ['z0']), (-hb - 0.01, Bd['z0'] - 0.01), (-hb + (CZ['z0'] - Bd['z0']) + 0.01, Bd['z0'] - 0.01)],
                       CZ['y'], y1 + 0.1))
    # the top's four edges, 0.4 x 45: the button reads the same all round, the chin edge too (the cap is closed there)
    c = P.KEY_CAP['chamfer']
    for yy, s in ((y0, 1), (y1, -1)):
        k = k.cut(yz_prism([(yy + s * c, TOP + 0.01), (yy - s * 0.01, TOP - c - 0.01), (yy - s * 0.01, TOP + 0.01)], -h - 1, h + 1))
    for s in (-1, 1):
        xe = s * h
        k = k.cut(xz_prism([(xe - s * c, TOP + 0.01), (xe + s * 0.01, TOP - c - 0.01), (xe + s * 0.01, TOP + 0.01)], y0 - 1, y1 + 1))
    k = _bed_end(k).clean()
    if xc or lift:
        k = k.translate((xc, 0, lift))
    return k


def rod(x0=None):
    """The filament rod, its tail (square) at x0 or centred in its end play; the tip (+X, the end that goes in
    first) tapered like a pencil over ROD_TIP['taper'] to a flat ROD_TIP['flat'] across."""
    a, b = P.ROD_STOPS
    x0 = (a + b - P.ROD_CUT) / 2 if x0 is None else x0
    t = P.ROD_TIP['taper']
    x1 = x0 + P.ROD_CUT
    tip = cq.Solid.makeCone(P.ROD_D / 2, P.ROD_TIP['flat'] / 2, t, cq.Vector(x1 - t, ROD[0], ROD[1]), cq.Vector(1, 0, 0))
    return xcyl(x0, x1 - t, ROD[0], ROD[1], P.ROD_D).union(cq.Workplane(obj=tip))


# >>> shared gate: the side gate (SPEC2 rev 3), the same code and numbers as case-368/src/crank.py
# (the 3.68 project) so both cases print the same gate; keep the two in step
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


# ---- the checks' geometry: the spec's YZ method, on the parts as built ------------------------------
# Across X each key is a stack of bands in which neither the crank nor the key changes its profile. In
# a band, the moving parts' exact profiles are checked against the shadow (union of sections) of every
# fixed part over the band, so a gap there is the true gap within the band; X gaps between bands (a
# cheek in its slot, a cap in its opening) are the designed side clearances, measured apart. The breaks
# are every |dx| where a part starts or ends: leg 1.30, plungers 1.44 / 1.85, key body (KEY_BODY half, 3.30),
# slot 3.60, TS365 housing 3.65, cheek 3.75, MJTP housing 4.04, the cheek's ring (CRANK_CHEEK_RING x0, 4.05), key cap
# (KEY_CAP half, 5.00), crank 5.25, opening 5.30, slot 5.40; the chin-wall slots (KEY_SLOT dx, 3.20-5.40), the hooks
# (KEY_HOOK dx, 3.95-5.00), on +X where the +X hook's 45-degree lead starts (3.08), and on -X the root's end (-4.35).
_B = (1.30, 1.44, 1.85, P.KEY_BODY['half'], 3.60, 3.65, 3.75, 4.04, P.CRANK_CHEEK_RING['x0'], P.KEY_CAP['half'], 5.25,
      5.30, 5.40, *P.KEY_SLOT['dx'], P.KEY_HOOK['dx'][0])
BANDS = tuple(sorted({*(-b for b in _B), *_B, round(P.KEY_HOOK['dx'][0] - P.KEY_HOOK_LEAD, 3),
                      round(-P.KEY_CAP['half'] + P.KEY_ROOT, 3)}))


def bands():
    return list(zip(BANDS[:-1], BANDS[1:]))


def crank_yz(a, b, variant='M'):
    """The crank's parts present across the band a..b of dx: {name: (y, z) polygon} at theta 0."""
    m = abs((a + b) / 2)
    c0, c1 = P.CRANK_CHEEK
    out = {}
    if m < c1:
        out['crossbar'] = CROSSBAR
        out['crown'] = CROWN
        out['belly'] = BELLY
        if m < P.CRANK_LEG:
            out['leg'] = leg_body(variant)
            out['nose'] = circ(P.CRANK_NOSE[variant], P.CRANK_NOSE_R)
        if m > c0:                   # the closed ring outboard of x0, the lip (the open C) inboard
            out['cheek'] = cheek_yz('ring' if m > P.CRANK_CHEEK_RING['x0'] else 'lip')
    return out


def key_yz(a, b):
    """The key's profile across the band a..b of dx at rest ({} outside the key): 'key' (with the root, KEY_ROOT, in
    its bands at the -X end), and 'hook' in a hook's bands (the +X hook's 45-degree lead as far as it reaches at the
    band's +X end: the most of it in the band)."""
    m = (a + b) / 2
    if abs(m) > P.KEY_CAP['half']:
        return {}
    pr = key_profiles()
    out = {'key': pr['body'] if abs(m) < P.KEY_BODY['half'] else pr['cheek']}
    if m < -P.KEY_CAP['half'] + P.KEY_ROOT:
        out['key'] = unary_union([out['key'], pr['root']])
    (x0, x1), lead = P.KEY_HOOK['dx'], P.KEY_HOOK_LEAD
    if x0 < abs(m) < x1:
        out['hook'] = pr['hook']
    elif x0 - lead < m < x0:
        _, z0, y1, z1 = pr['hook'].bounds
        out['hook'] = sbox(P.KEY_CAP['y'][0] - (b - (x0 - lead)), z0, y1, z1)
    return out


def turn(g, theta):
    from shapely import affinity
    return affinity.rotate(g, theta, origin=ROD) if theta else g


def lift(g, dz):
    from shapely import affinity
    return affinity.translate(g, 0, dz) if dz else g


def section(mesh, x):
    """(y, z) polygon of a closed mesh's section at X = x (holes kept), or None."""
    s = mesh.section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0])
    if s is None:
        return None
    g = None
    for loop in s.discrete:
        if len(loop) < 3:
            continue
        p = Polygon(loop[:, [1, 2]]).buffer(0)
        if p.area > 1e-6:
            g = p if g is None else g.symmetric_difference(p)
    return g


def shadow(mesh, x0, x1, step=0.1, clip=(-12.0, -8.0, 4.0, 9.0)):
    """Union of a mesh's sections across x0..x1 (just inside both ends, and every `step`), clipped to the
    chin's (y, z) window."""
    n = max(2, int(math.ceil((x1 - x0) / step)) + 1)
    xs = [x0 + 0.005 + (x1 - x0 - 0.01) * i / (n - 1) for i in range(n)]
    gs = [g for g in (section(mesh, x) for x in xs) if g is not None and not g.is_empty]
    if not gs:
        return Polygon()
    return unary_union(gs).intersection(sbox(*clip))


# the switches as the spec models them (layout.json switch_envelope_used), in (y, z), board at its nominal
# place; delta moves the board -Y (a delta of +0.2 puts the board's edge at y -0.2)
SWITCH = {
    'MJTP': dict(housing=((-0.68, -4.49, 6.0, -0.19), 4.04), nub=((-1.92, -3.459, -0.68, -1.959), 1.44), face=-1.92,
                 travel=(0.25, 0.45), force=(1.27, 1.86), variant='M'),
    'TS365': dict(housing=((-1.65, -3.6, 6.0, 0.0), 3.65), nub=((-2.2, -3.05, -1.45, -1.05), 1.85), face=-2.2,
                  tip=(-2.4, -2.0), travel=(0.25, 0.45), force=(1.96, 2.94), variant='T'),
}


def switch_yz(kind, a, b, delta=0.0, face=None):
    """The switch envelope's housing and plunger across the band a..b, the plunger's face at `face`."""
    sw = SWITCH[kind]
    m = abs((a + b) / 2)
    out = {}
    (y0, z0, y1, z1), hx = sw['housing']
    if m < hx:
        out['housing'] = sbox(y0 - delta, z0, y1 - delta, z1)
    (y0, z0, y1, z1), nx = sw['nub']
    if m < nx:
        out['plunger'] = sbox((sw['face'] if face is None else face) - delta, z0, y1 - delta, z1)
    return out


def board_yz(edge):
    return sbox(edge, 0.0, 200.0, P.PCB_FRONT)


def nose_front(variant, theta):
    c = P.CRANK_NOSE[variant]
    t = math.radians(theta)
    vy, vz = c[0] - ROD[0], c[1] - ROD[1]
    return ROD[0] + vy * math.cos(t) - vz * math.sin(t) + P.CRANK_NOSE_R


def rest_theta(variant, face):
    """Crank angle at which the nose's crown touches a plunger face at y = face."""
    lo, hi = -40.0, 40.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if nose_front(variant, mid) < face:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def gap(a, b):
    """Distance between two polygons; minus the overlap area when they overlap."""
    if a is None or b is None or a.is_empty or b.is_empty:
        return None
    if a.intersects(b):
        ov = a.intersection(b).area
        if ov > 1e-6:
            return -round(ov, 5)
    return round(a.distance(b), 4)


if __name__ == '__main__':
    for v in ('M', 'T'):
        c = crank(v)
        b = c.val().BoundingBox()
        print('crank', v, len(c.solids().vals()), round(c.val().Volume(), 1), [round(q, 2) for q in (b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax)])
    k = key()
    b = k.val().BoundingBox()
    print('key', len(k.solids().vals()), round(k.val().Volume(), 1), [round(q, 2) for q in (b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax)])
