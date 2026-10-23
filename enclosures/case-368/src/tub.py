"""Front tub: screen bezel, display pocket, chin with the four keys, and the side walls down to the
parting plane. Printed face down; every internal surface that faces the screen (+Z) is either on the bed
or a <=45 degree slope in that orientation.

x3: the 3.68-inch panel is narrower than the board, so its pocket sits inside Rev K's side walls, which are
set by the board and its switches. Between the two, a frame 0.6 thick stands in front of the midplate
(FRAME_REAR), clear of it at any panel thickness. Below the pocket (toward the back) the walls stand at
Rev K's width, so the midplate and the board drop in past them (Rev F; params.INSERT_X0/X1).

The tub differs between the two builds (params.LIGHT_STRIP), and so do the bottom keys, which stand a fixed height
over their tub's face. Standard: x3's tub, with its left upper detent pocket at the shared midplate's 58.0
(detent_pockets). Light strip: the strip's bar lies beside the panel's left edge in a channel under the skin
(strip_features), so the front face is FRONT_RAISE higher all over (still one plane: it prints on the bed).

Bottom keys (2026-09-26, crank.py and keys.py): the rod's rail with its rings and open seats, the webs from it to the
chin wall, the keys' openings, the gate's slot and the rod's channel in the -X wall (gate_slot, SPEC2 rev 3; the M2.5
screw's countersink is gone), the chin wall's lead-in and, since test 2 (2026-09-30, the hook keys), two slots per key
in the chin wall's inner face that the keys' hooks run in (key_slots). They replace the rocker's seat rib, its spring's
ledge and, on the light strip, the caps' wells. The chin is 1.0 deeper (params BOT_IN). Over the key row the chin's rim
has no seam chamfer (rim_chamfer), so the wall behind the slots prints up to the rim."""
import math
import cadquery as cq
import hw
import params as P
from geom import box, rbox, zcyl, xcyl, xz_prism, yz_prism, stadium_x, rrect_x
import crank
from body import outer_body, inner_limit, side_tabs, usb

PCB = hw.bounds('PCB')
LOW_X0 = P.WALL_X0                           # side walls' inner faces below the panel
LOW_X1 = P.WALL_X1
CHIN_WEB = dict(y0=1.5, z0=2.6)              # the chin's skin is solid down to z0 above the board's front,
                                             # from y0 to the panel pocket (0.29 over the bottom switches' lead
                                             # tips, which reach 2.31); the key mechanism stays at y < 0


def _ring(x0, x1, y0, y1, r, o, z):
    """Closed wire at height z: the window x0..x1, y0..y1 with corners r, grown by o all round (corners r + o)."""
    R = r + o
    X0, X1, Y0, Y1 = x0 - o, x1 + o, y0 - o, y1 + o
    V = lambda x, y: cq.Vector(x, y, z)
    arc = lambda cx, cy, a0: cq.Edge.makeCircle(R, V(cx, cy), cq.Vector(0, 0, 1), a0, a0 + 90)
    return cq.Wire.assembleEdges([
        cq.Edge.makeLine(V(X0 + R, Y0), V(X1 - R, Y0)), arc(X1 - R, Y0 + R, 270),
        cq.Edge.makeLine(V(X1, Y0 + R), V(X1, Y1 - R)), arc(X1 - R, Y1 - R, 0),
        cq.Edge.makeLine(V(X1 - R, Y1), V(X0 + R, Y1)), arc(X0 + R, Y1 - R, 90),
        cq.Edge.makeLine(V(X0, Y1 - R), V(X0, Y0 + R)), arc(X0 + R, Y0 + R, 180)])


def window():
    """The screen window (params WINDOW_*). Standard: straight up from 0.2 under the lip (the active area +
    WINDOW_MARGIN, corners WINDOW_CORNER_R) to WINDOW_CHAMFER under the face, then out at WINDOW_BEVEL_ANGLE to 0.05
    past it (WINDOW_BEVEL_W wider each side on the face, corners R + W): one ruled loft through three rings, so the
    corners are cones. Light strip: x3's straight land and 45-degree bevel, sharp corners."""
    if not P.LIGHT_STRIP:
        x0 = hw.ACTIVE_CX - hw.ACTIVE_W / 2 - P.WINDOW_MARGIN
        x1 = hw.ACTIVE_CX + hw.ACTIVE_W / 2 + P.WINDOW_MARGIN
        y0 = hw.ACTIVE_CY - hw.ACTIVE_H / 2 - P.WINDOW_MARGIN
        y1 = hw.ACTIVE_CY + hw.ACTIVE_H / 2 + P.WINDOW_MARGIN
        zb, ztop = P.Z_FRONT - P.WINDOW_CHAMFER, P.Z_FRONT + 0.05
        k = 1 / math.tan(math.radians(P.WINDOW_BEVEL_ANGLE))
        wires = [_ring(x0, x1, y0, y1, P.WINDOW_CORNER_R, max(0.0, z - zb) * k, z) for z in (P.LIP - 0.2, zb, ztop)]
        return cq.Workplane(obj=cq.Solid.makeLoft(wires, True))
    x0 = hw.ACTIVE_CX - hw.ACTIVE_W / 2 - P.WINDOW_MARGIN
    y0 = hw.ACTIVE_CY - hw.ACTIVE_H / 2 - P.WINDOW_MARGIN
    w, h = hw.ACTIVE_W + 2 * P.WINDOW_MARGIN, hw.ACTIVE_H + 2 * P.WINDOW_MARGIN
    straight = box(x0, x0 + w, y0, y0 + h, P.LIP - 0.2, P.Z_FRONT - P.WINDOW_CHAMFER + 0.01)
    c = P.WINDOW_CHAMFER + 0.02
    bevel = (cq.Workplane('XY', origin=(hw.ACTIVE_CX, hw.ACTIVE_CY, P.Z_FRONT - P.WINDOW_CHAMFER))
             .rect(w, h).workplane(offset=c).rect(w + 2 * c, h + 2 * c).loft())
    return straight.union(bevel)


def cavity():
    lim = inner_limit(P.SEAM - 1.5, P.LIP)
    # below the panel: the walls' width, up to the frame's rear face
    lower = rbox(LOW_X0, LOW_X1, P.BOT_IN, P.TOP_IN, P.SEAM - 1.5, P.FRAME_REAR, 1.5)
    # the panel's pocket, from below the midplate's front up to the lip, with corner reliefs for the glass
    pocket = box(P.POCKET_X0, P.POCKET_X1, P.POCKET_Y0, P.POCKET_Y1, P.MID_REAR - 0.05, P.LIP)
    for cx in (P.POCKET_X0, P.POCKET_X1):
        for cy in (P.POCKET_Y0, P.POCKET_Y1):
            pocket = pocket.union(zcyl(cx, cy, P.MID_REAR - 0.05, P.LIP, 1.0))
    # the chin: open to the lip over the keys (their caps, necks and ridges move there); above them the
    # skin is thick down to CHIN_WEB['z0']
    chin = box(LOW_X0, LOW_X1, P.BOT_IN, CHIN_WEB['y0'], P.MID_REAR - 0.05, P.LIP)
    chin = chin.union(box(LOW_X0, LOW_X1, CHIN_WEB['y0'] - 0.01, P.POCKET_Y0 + 0.01, P.MID_REAR - 0.05, CHIN_WEB['z0']))
    v = lower.union(pocket).union(chin)
    for g in ribbon_gaps():
        v = v.union(g)
    return v.intersect(lim)


def ribbon_gaps():
    """The FPC leaves the glass's bottom edge on the glass's front face and folds straight down past the
    edge (panel.Path). The pocket's bottom wall and the chin's web are open over its width, full height,
    so nothing pinches it; the rest of the wall still holds the glass."""
    import panel
    c = P.FPC_GAP_CLR
    at_fold = [u for r in panel.RIBBONS.values() for u, v in r['poly'] if v >= -3.0]
    x0 = hw.PANEL_X0 + min(at_fold) - c
    x1 = hw.PANEL_X0 + max(at_fold) + c
    y0 = hw.PANEL_Y0 - panel.BEND_R - 0.12 - 0.35
    return [box(x0, x1, y0, P.POCKET_Y0 + 0.1, P.MID_REAR - 0.05, P.LIP)]


def key_x():
    """The bottom keys' centres (their switches' plungers), left to right."""
    return [hw.switch_plunger(r)['face'][0] for r in P.KEY_REFS]


def rail_segments():
    """X spans of the rail's segments: ('ring', x0, x1) beside the cranks (the ends and the webs' rings), ('seat', ..)
    under each switch (the open seats), ('slot', ..) where a crank cheek runs (no rail: the slot is open up to the skin,
    SLOT_ROOF = LIP)."""
    xs = key_x()
    s0, s1 = P.SLOT
    out, x = [], P.WALL_X0 - 0.05                              # the left ring runs on into the side wall
    for xc in xs:
        out += [('ring', x, xc - s1), ('slot', xc - s1, xc - s0), ('seat', xc - s0, xc + s0), ('slot', xc + s0, xc + s1)]
        x = xc + s1
    out.append(('ring', x, P.RAIL_X1))
    return out


def rail():
    """The rod's rail under the skin in front of the board's edge (params 'bottom keys'): closed teardrop rings beside
    the cranks, open seats under the switches (their mouth faces the TS365's housing, 0.065 from the bore; the pin's
    load at 211 degrees goes into the solid wall), and nothing over each cheek slot: the slot runs up to the skin
    (SLOT_ROOF = LIP; 2026-10-12, it had 0.32 of rail over it, which a cheek's top corner scraped turning by hand). The
    -Y face is the keys' +Y guide."""
    (ya, yb), (py, pz), lip = P.RAIL_Y, P.ROD_AXIS, P.LIP + 0.01
    c, rb = P.RAIL_CHAMFER, P.RING_BOTTOM
    ring = [(yb, lip), (yb, rb + c), (yb - c, rb), (ya + c, rb), (ya, rb + c), (ya, lip)]
    seat = [(ya, lip), (ya, -0.575), (-3.825, -0.975), (-2.8, -0.975), (-2.5, -0.62), (-1.6, -0.62),
            (yb, -0.62 + (yb + 1.6) * 0.82 / 1.3), (yb, lip)]
    mouth = crank._sector((py, pz), 262, 370, 4.0)
    out = []
    for kind, x0, x1 in rail_segments():
        if kind == 'ring':
            r = yz_prism(ring, x0, x1).cut(crank.teardrop(x0 - 1, x1 + 1, (py, pz), P.ROD_HOLE_D, P.ROD_TEARDROP_FLAT, '-z'))
        elif kind == 'seat':
            r = (yz_prism(seat, x0, x1).cut(xcyl(x0 - 1, x1 + 1, py, pz, P.ROD_HOLE_D))
                 .cut(yz_prism(mouth, x0 - 1, x1 + 1)))
        else:                    # a cheek's slot: open to the skin (SLOT_ROOF is LIP, so no rail strip over it)
            assert P.SLOT_ROOF >= P.LIP - 1e-9, 'tub.rail: SLOT_ROOF under the skin needs its rail strip back'
            continue
        out.append(r)
    return out


def webs():
    """Rail to chin wall, from the skin down to WEB['z0'], between the cranks: each web stands where the rail has a
    ring (0.15 from the cheeks either side; the spec's 1.4-wide webs came within 0.05 of the cheeks' sweep), and at the
    two ends out to WEB['x_ends']."""
    xs = key_x()
    s1 = P.SLOT[1]
    spans = [(P.WEB['x_ends'][0], xs[0] - s1)] + [(a + s1, b - s1) for a, b in zip(xs, xs[1:])] + [(xs[-1] + s1, P.WEB['x_ends'][1])]
    return [box(a, b, P.BOT_IN - 0.01, P.RAIL_Y[0] + 0.01, P.WEB['z0'], P.LIP + 0.01) for a, b in spans]


def floor_z(x):
    """The gate slot's floor at X x: the gate's bevel plane out to the case side, flat at GATE_SLOT['floor_z'] past its
    flat."""
    return P.GATE_SLOT['floor_z'] + max(0.0, P.ROD_STOP_X0 - x)


def slot_floor(margin=0.02):
    """The gate slot's floor as a region for the checks (build.contacts, crank_checks): from margin over its surface
    (floor_z) down (+Z) into the wall, over the slot's X and past its Y."""
    xf, zf = P.ROD_STOP_X0, P.GATE_SLOT['floor_z']
    x0 = P.X0 - 1
    return xz_prism([(x0, floor_z(x0) - margin), (xf, zf - margin), (P.WALL_X0, zf - margin), (P.WALL_X0, 6.0), (x0, 6.0)],
                    -7.0, 2.0)


def _chamfer_section(x, s):
    """(y, z) quad that takes GATE_SLOT['channel_chamfer'] off the edge where the rod's channel breaks the slot's floor at X x
    (s = +1: the +Y edge, -1: the -Y edge): from the floor's edge E out c along the floor (A) and c (chord) down the
    channel's wall (B), and 0.05 into the slot's air over E and A. None where the channel stays under the floor."""
    (py, pz), R, c = P.ROD_AXIS, P.ROD_HOLE_D / 2, P.GATE_SLOT['channel_chamfer']
    a = floor_z(x) - pz
    if a >= R:
        return None
    w = math.sqrt(R * R - a * a)
    th = math.atan2(a, w) + 2 * math.asin(c / (2 * R))
    th = min(th, math.pi / 2)
    pts = [(w, a - 0.05), (w + c, a - 0.05), (w + c, a), (R * math.cos(th), R * math.sin(th))]
    return [(py + s * u, pz + v) for u, v in pts]


def gate_slot():
    """The gate's slot in the -X wall (params GATE_SLOT, GATE; SPEC2 rev 3), open to the rim, with the rod's channel:
      mouth    through the case side, the web's (0.10 a side), from the rim to the floor
      cavity   behind the lips, the flange's (0.15 a side and behind), its ends R0.40 semicircles (the lips' root
               relief: no fillets), from the rim to the floor
      floor    the gate's own bevel plane (2.65 at the face, 1.55 at the lips' inner face), flat at 0.90 over the last
               0.15; the gate seats on it
      channel  the rod's 2.10 teardrop from X0 on through the floor and the sliver (X -2.19..WALL_X0) into the left
               ring; where it breaks the floor (X > -3.09) both its edges are chamfered, and the sliver's -X face has
               a 45-degree lead-in. The floor's ramp and the chamfers lift a drooping rod tip back in
    The countersink and the M2.5 screw are gone. Everything is open to the rim, the floor is a top surface in the
    face-down print and the hole a teardrop, so nothing bridges. The tongue's notch over the cavity is joint.tub_cuts'."""
    S = P.GATE_SLOT
    py, pz = P.ROD_AXIS
    xo, xl, xc = P.GATE_SLOT_X
    xf, zf = P.ROD_STOP_X0, S['floor_z']
    r = S['end_r']
    (m0, m1), (c0, c1) = S['mouth'], S['cavity']
    z0 = P.SEAM - 0.1
    mouth = xz_prism([(xo - 1, z0), (xl + 0.01, z0), (xl + 0.01, floor_z(xl + 0.01)), (xo - 1, floor_z(xo - 1))], m0, m1)
    plan = box(xl, xc, c0, c1, z0, 3.0)
    for yc in (c0, c1):
        plan = plan.union(zcyl(xl + r, yc, z0, 3.0, 2 * r))
    under = xz_prism([(xl - 0.01, z0), (xc + 0.01, z0), (xc + 0.01, zf), (xf, zf), (xl - 0.01, floor_z(xl - 0.01))],
                     c0 - r - 0.1, c1 + r + 0.1)
    cuts = [mouth, plan.intersect(under)]
    cuts.append(crank.teardrop(xo - 1, P.WALL_X0 + 0.1, (py, pz), P.ROD_HOLE_D, P.ROD_TEARDROP_FLAT, '-z'))
    # the channel's edges in the floor: a ruled loft over the bevel (the floor's height changes along X), a prism over
    # the flat
    x_break = xf - (pz + P.ROD_HOLE_D / 2 - zf)                   # -3.09: where the channel's bottom meets the floor
    xs = [x_break + 0.005 + (xf - x_break - 0.005) * i / 8 for i in range(9)]
    for s in (1, -1):
        for xa, xb in zip(xs, xs[1:]):
            qa, qb = _chamfer_section(xa, s), _chamfer_section(xb, s)
            cuts.append(cq.Workplane('YZ').workplane(offset=xa).polyline(qa).close()
                        .workplane(offset=xb - xa).polyline(qb).close().loft(ruled=True))
        cuts.append(yz_prism(_chamfer_section(xf, s), xf - 0.001, xc))
    ld, R = S['sliver_lead'], P.ROD_HOLE_D / 2                       # from the sliver's face, not before it: the floor
    cuts.append(cq.Workplane(obj=cq.Solid.makeCone(R + ld + 0.001, R - 0.01, ld + 0.011, cq.Vector(xc - 0.001, py, pz),
                                                   cq.Vector(1, 0, 0))))   # in front of it stays whole
    return cuts


def key_openings():
    """Each key's opening through the skin, straight, with KEY_EDGE_CHAMFER at the face. Its +Y edge is flush with
    the rail's face (the key's guide runs on up through the skin) and its chin edge overhangs the chin wall 0.25: the
    ledge (on the light strip, where the slots' roof is the skin's underside, the hooks bear under it)."""
    O = P.KEY_OPENING
    k = P.KEY_EDGE_CHAMFER
    out = []
    for xc in key_x():
        x0, x1 = xc - O['half'], xc + O['half']
        y0, y1 = O['y']
        out.append(rbox(x0, x1, y0, y1, P.LIP - 0.01, P.Z_FRONT + 1, O['r']))
        s0 = cq.Sketch().rect(x1 - x0, y1 - y0).vertices().fillet(O['r'])
        e = k + 0.2                                                  # 45 degrees to 0.2 past the face
        s1 = cq.Sketch().rect(x1 - x0 + 2 * e, y1 - y0 + 2 * e).vertices().fillet(O['r'] + e)
        out.append(cq.Workplane('XY', origin=((x0 + x1) / 2, (y0 + y1) / 2, P.Z_FRONT - k))
                   .placeSketch(s0, s1.moved(cq.Location(cq.Vector(0, 0, e)))).loft())
    return out


def chin_lead_in():
    """45-degree lead-in on the chin wall's lower inner edge over each key: the keys go in from inside (the hook slots
    cut through it)."""
    a, b = P.BOT_IN, P.SEAM
    c = P.CHIN_LEAD_IN
    tri = [(a + 0.01, b + c + 0.01), (a - c - 0.01, b - 0.01), (a + 0.01, b - 0.01)]
    return [yz_prism(tri, xc - P.KEY_OPENING['half'], xc + P.KEY_OPENING['half']) for xc in key_x()]


def key_slots():
    """The hook keys' slots (params KEY_SLOT; test 2, 2026-09-30): two per key in the chin wall's inner face, |dx|
    KEY_SLOT dx (the outer side flush with the web's face), from the chin wall's face back to KEY_SLOT back, and from
    below the rim up to a flat roof at KEY_SLOT_ROOF (the skin's underside on the light strip; inside the chin wall,
    on the tub's layer grid, on x3 standard). In the face-down print each is a slot open at its top (the rim), on a
    flat floor (the roof): no overhang, no bridge. The lid's rim covers their ends."""
    (a, b), yb = P.KEY_SLOT['dx'], P.KEY_SLOT['back']
    z0 = P.SEAM - P.JOINT['h'] - 1.0
    return [box(x0, x1, yb, P.BOT_IN + 0.01, z0, P.KEY_SLOT_ROOF)
            for xc in key_x() for x0, x1 in ((xc - b, xc - a), (xc + a, xc + b))]


def rim_relief():
    """X span on the chin where the tub has no seam chamfer (params KEY_SLOT relief): the key row, from `relief`
    before the first slot to `relief` past the last."""
    xs, b, r = key_x(), P.KEY_SLOT['dx'][1], P.KEY_SLOT['relief']
    return xs[0] - b - r, xs[-1] + b + r


def rim_chamfer():
    """The tub's half of the seam's V (body.seam_chamfer), left off the chin over the key row (rim_relief; hverify1 F1,
    2026-09-30): there the chamfer thinned the wall behind the hook slots below what Orca prints in the rim's last
    layers. Over the key row the tub's rim meets the lid's chamfer square; the step at each end is vertical."""
    from body import seam_chamfer
    x0, x1 = rim_relief()
    return seam_chamfer(upper=True).cut(box(x0, x1, P.Y0 - 3.0, P.Y0 + 1.0, P.SEAM - 1.0, P.SEAM + 1.0))


def coupon(tub_wp):
    """The hook keys' optional fit check (test 2, 2026-09-30; RECOMMENDATION section 5, 15 minutes): SW9's opening
    between the two webs beside it, with the chin wall and its two slots, the ledge and a stub of the rail's face, cut
    from the built tub; printed face down like it, with one key. It checks the fit; nothing is chosen from it."""
    xs = key_x()
    s1 = P.SLOT[1]
    x0, x1 = P.WEB['x_ends'][0], xs[1] - s1
    return tub_wp.intersect(box(x0, x1, P.Y0 - 1, P.RAIL_Y[0] + 0.625, P.SEAM - 1, P.Z_FRONT + 1)).clean()


def gate_coupon(tub_wp):
    """The gate's proof coupon (SPEC2 rev 3, check 10): the -X wall at the gate's slot, X X0..+2.0 and y -7..+2, its
    whole height, cut from the built tub: the slot and its lips, the floor, the sliver, the rod's channel and the start
    of the left ring. Printed face down like the tub. Two 1.0 feet on its outer face (y < -5.5 and y > 0.5, filling the
    corner's round and the front edge's) stand it on a kitchen scale with the lips and the gate's web 1 mm off the
    table, for the proof test (README, Bottom keys)."""
    piece = tub_wp.intersect(box(P.X0 - 1, 2.0, -7.0, 2.0, P.SEAM - P.JOINT['h'] - 1, P.Z_FRONT + 1))
    for y0, y1 in ((-7.0, -5.5), (0.5, 2.0)):
        piece = piece.union(box(P.X0 - 1.0, P.WALL_X0 - 0.3, y0, y1, P.SEAM, P.Z_FRONT))
    return piece.clean()


def screw_bosses():
    """The screws' bosses and pilots (params, fasteners): the corner blocks of the bottom pair (corner_blocks), the top
    boss, which merges into the right wall above the board's cut edge, and the top-left one (top_left_boss). Every
    pilot runs from the parting plane to PILOT_CAP under x3's face. And the H3/H4 bosses, with no pilot since the bottom pair
    moved to the corners (2026-10-13). Their faces stand P.H34_FLOAT (0.4, two layers from the bed) clear of the board
    (P.H34_FACE, 2026-10-20): the board is held by the lid's posts and the springs, not clamped line to line between
    the lid and these bosses (which levered the lid open along its long sides)."""
    fps = hw.footprints()
    add, cut = [], []
    pilot = lambda x, y: zcyl(x, y, P.SEAM - 0.1, P.Z_FRONT_BASE - P.PILOT_CAP, P.M2_PILOT)    # x3's depth
    for ref in ('H3', 'H4'):
        hx, hy = fps[ref]['cad']
        flat = box(hx - P.BOSS_D, hx + P.BOSS_D, hy - P.BOSS_D, P.POCKET_Y0, P.H34_FACE - 1, P.LIP + 1)
        add.append(zcyl(hx, hy, P.H34_FACE, P.LIP + 0.01, P.BOSS_D).intersect(flat))
    add += corner_blocks()
    cut += [pilot(x, y) for x, y in P.CORNER_SCREWS]
    tx, ty = P.TOP_SCREW
    boss = zcyl(tx, ty, P.SEAM, P.LIP + 0.01, P.TOP_BOSS_D)
    boss = boss.union(box(tx, LOW_X1 + 0.01, ty - P.TOP_BOSS_D / 2, ty + P.TOP_BOSS_D / 2, P.SEAM, P.LIP + 0.01))
    add.append(boss)
    cut.append(pilot(tx, ty))
    add.append(top_left_boss())
    cut.append(pilot(*P.TOP_LEFT_SCREW))
    return add, cut


def top_left_boss():
    """The top-left screw's boss (2026-10-13): the top boss's TOP_BOSS_D round, merged into the left and top walls
    (the corner between them filled), flat where it meets the panel's pocket at its largest, from the parting plane to
    the skin. It stands on the frame in the face-down print: no overhang. It fills the pocket's corner relief at this
    corner (cavity: a 1.0 round at each corner): with the relief the pilot kept 0.20 of wall toward the glass's corner,
    without it 0.70; the largest glass's corner stays 0.15 / 0.15 off the two walls. The midplate is notched round it
    (midplate.top_left_notch)."""
    x, y = P.TOP_LEFT_SCREW
    r = P.TOP_BOSS_D / 2
    z0, z1 = P.SEAM, P.LIP + 0.01
    boss = zcyl(x, y, z0, z1, P.TOP_BOSS_D)
    boss = boss.union(box(LOW_X0 - 0.01, x + r, y, P.TOP_IN + 0.01, z0, z1))
    boss = boss.union(box(LOW_X0 - 0.01, x, y - r, P.TOP_IN + 0.01, z0, z1))
    return boss.cut(box(P.POCKET_X0, P.POCKET_X1, P.POCKET_Y0, P.POCKET_Y1, z0 - 1, z1 + 1))


def corner_blocks():
    """The bottom pair's bosses (2026-10-13): each of the chin's two bottom corners filled, from the side wall to the end
    web (WEB x_ends: the block meets the web's face, so the hook keys' coupon, cut from X 4.8, is unchanged) and from the
    chin wall to CORNER_BLOCK_Y1 under the rod, from the parting plane to the skin. Clear of the cranks' cheeks (from
    X 6.25 / to 53.75: they turn about X), the keys, the rail's bores and the gate's slot; the rod's bare right end
    (X 56.3..61.41) keeps its 0.375 under it for the push-out. It prints face down on the skin: no overhang."""
    xa, xb = P.WEB['x_ends']
    return [box(x0, x1, P.BOT_IN - 0.01, P.CORNER_BLOCK_Y1, P.SEAM, P.LIP + 0.01)
            for x0, x1 in ((P.WALL_X0 - 0.01, xa), (xb, P.WALL_X1 + 0.01))]


def usb_features():
    """The port (Rev I-K, unchanged): the recess - the divot - for the plug's overmold, USB_RECESS (typical
    cables) with a 45-degree lead-in at the case face, and its floor, which is the tub itself:
    USB_FLOOR['t'] thick, its inside on the insertion corridor (INSERT_X1). The port's hole is J1's opening
    plus USB_FLOOR['hole'] a side; below it the floor is open to the parting line (a notch), so the hole
    prints with no bridge, and a block on the lid rises into the notch and closes the hole's lower edge.

    tub_cuts  the recess, from the floor's face outward, and the hole with its notch
    tub_adds  the floor's inner 0.1 mm, where it stands proud of the wall's inside (LOW_X1 -> INSERT_X1)
    lid_cuts  the recess
    lid_adds  the block that closes the hole's lower edge

    2026-10-22: the hole's and the recess's board-side edges stand P.USB_HOLE_TOP / USB_RECESS_TOP, a layer or so
    further out than J1's opening plus 0.1, and the lid's block is P.USB_BLOCK_DROP lower (board Rev 1.02's J1 sits 0.14
    nearer the board; asprinted.usb_fit reads the printed edges against both boards' sockets)."""
    u = usb()
    F = P.USB_FLOOR
    w, h = P.USB_RECESS
    x_in = P.INSERT_X1
    x_face = x_in + F['t']                                   # the floor's outer face
    # Rev 1.0 / Rev 1.02 (params.USB_HOLE_TOP): the recess and the hole keep their far edges and their widths; their
    # board-side edges (the larger z) stand on layer lines, drawn for the frozen Rev 1.0 board copy
    assert all(abs(u[k] - v) < 0.005 for k, v in P.J1_REV10.items()), \
        f"J1 moved (zc {u['zc']:.3f}): redo P.J1_REV10, USB_HOLE_TOP, USB_RECESS_TOP, USB_BLOCK_DROP"
    zr0 = u['zc'] - h / 2                                    # the recess's far edge (-4.955)
    hr = P.USB_RECESS_TOP - zr0                              # its height now (the board-side edge moved out a layer)
    zr = zr0 + hr / 2                                        # its centre
    recess = rrect_x(x_face, P.X1 + 1, u['yc'], zr, w, hr, P.USB_RECESS_R)
    ld, over = P.USB_RECESS_LEAD, 0.5                        # 45-degree lead-in at the case face
    s0 = cq.Sketch().rect(w, hr).vertices().fillet(P.USB_RECESS_R)
    s1 = cq.Sketch().rect(w + 2 * (ld + over), hr + 2 * (ld + over)).vertices().fillet(P.USB_RECESS_R + ld + over)
    recess = recess.union(cq.Workplane('YZ', origin=(P.X1 - ld, u['yc'], zr))
                          .placeSketch(s0, s1.moved(cq.Location(cq.Vector(0, 0, ld + over)))).loft())
    iw = (u['inner_y'][1] - u['inner_y'][0]) + 2 * F['hole']
    ih0 = (u['inner_z'][1] - u['inner_z'][0]) + 2 * F['hole']      # J1's opening plus the clearance: 2.76
    ir = u['inner_r'] + F['hole']
    z_far = u['zc'] - ih0 / 2                                # the hole's far edge, the lid block's top (-3.335) ...
    z_blk = z_far - P.USB_BLOCK_DROP                         # ... less the 3.68's layer
    ih = P.USB_HOLE_TOP - z_blk                              # the hole's height now: board-side edge to the block's top
    zh = z_blk + ih / 2
    hole = rrect_x(x_in - 0.3, x_face + 0.02, u['yc'], zh, iw, ih, ir)
    notch = box(x_in - 0.3, x_face + 0.02, u['yc'] - iw / 2, u['yc'] + iw / 2, P.SEAM - 0.1, u['zc'])
    m = 0.6
    floor_add = box(x_in, LOW_X1 + 0.01, u['yc'] - w / 2 - m, u['yc'] + w / 2 + m, P.SEAM, u['zc'] + h / 2 + m)
    floor_add = floor_add.cut(hole).cut(notch)
    nc = F['notch_clr']
    block = box(u['mouth_x'] + F['lid_gap'], x_face, u['yc'] - iw / 2 + nc, u['yc'] + iw / 2 - nc,
                P.SEAM - 0.3, z_blk)
    return {'tub_cuts': [recess, hole, notch], 'tub_adds': [floor_add], 'lid_cuts': [recess], 'lid_adds': [block],
            'size': (w, round(hr, 3)), 'r': P.USB_RECESS_R,
            'port_y': (u['yc'] - w / 2, u['yc'] + w / 2), 'port_z': (zr0, P.USB_RECESS_TOP),
            'wall_x': (LOW_X1, P.X1), 'floor_x': (x_in, x_face), 'face_x': x_face,
            'seat_x': u['mouth_x'] + P.USB_PLUG_SPARE, 'hole': (round(iw, 3), round(ih, 3)), 'hole_r': round(ir, 3),
            'hole_z': (round(z_blk, 3), P.USB_HOLE_TOP),
            'block_y': (u['yc'] - w / 2 - 1.0, u['yc'] + w / 2 + 1.0),
            'face_to_mouth': round(x_face - u['mouth_x'], 3),
            'plug_short_mm': round(max(0.0, (x_face - u['mouth_x']) - P.USB_PLUG_SPARE), 3)}


def reset_hole():
    rx, ry, rz = hw.switch_plunger(hw.RESET)['face']
    hole = xcyl(LOW_X1 - 0.5, P.X1 + 1, ry, rz, 1.2)
    sink = cq.Workplane(obj=cq.Solid.makeCone(0.6, 1.1, 0.5, cq.Vector(P.X1 - 0.5, ry, rz), cq.Vector(1, 0, 0)))
    return hole.union(sink).union(xcyl(P.X1 - 0.01, P.X1 + 1, ry, rz, 2.2))


def detent_pockets():
    """Rev K: a pocket in each side wall's inner face for each of the midplate's detent bumps
    (midplate.detents), MID_DETENT['depth'] past the wall face. Its roof - the face toward the back,
    which the bump catches - is 45 degrees, because in the face-down tub it prints as a roof; it runs
    toward the front so a -0.1 panel's plate still sits free in it once the lid is on. The left upper one
    follows the shared midplate's strip to 58.0 in both builds (params.MID_DETENT)."""
    import midplate
    D = P.MID_DETENT
    d, z0, z1 = D['depth'], D['z0'], D['z1']
    out = []
    for r in midplate.detents()[2]:
        s = 1 if r['wall'] == 'right' else -1
        xw = LOW_X1 if s > 0 else LOW_X0
        prof = [(xw - s * 0.01, z0), (xw + s * d, z0 + d), (xw + s * d, z1), (xw - s * 0.01, z1)]
        out.append(xz_prism(prof, r['bump_y'][0] - D['clr'], r['bump_y'][1] + D['clr']))
    return out


def key_cuts(t):
    """The slot one side key (sidekeys.py, part of the lid since Rev J) rises into.

    slot     the outer layer and the void, from the parting line up to TAB_SLOT_CLR over the key's
             top, from TAB_ROOT_CLR before its block to TAB_END_CLR past its free end
    window   through the sliver where the nub crosses it
    Both are open to the parting line, so the tub prints round them face down with no overhang anywhere,
    and the key slides in along them as the lid goes on."""
    s, a = t['side'], t['away']
    xo = P.X1 if s > 0 else P.X0
    ys = sorted((t['y_block'] - a * P.TAB_ROOT_CLR, t['y_free'] + a * P.TAB_END_CLR))
    xs = sorted((t['stop'], xo + s * 1.0))
    top = P.TAB_Z[1] + P.TAB_SLOT_CLR
    assert top < P.FRAME_REAR - 1.0, top
    cuts = [box(xs[0], xs[1], ys[0], ys[1], P.SEAM - 0.1, top)]
    from body import tab_window
    w = tab_window(t)
    cuts.append(box(w['x'][0], w['x'][1], w['y'][0], w['y'][1], P.SEAM - P.JOINT['h'] - 0.6, w['top']))
    return cuts


def strip_features(ribs=True):
    """Light strip: the bar's channel, its seat, the fold zone, the foot's pocket, the neck's gap in the chin, the
    panel's corner stops, the hold-down pads and their ribs, and the bar's stop ribs (params 'light strip'). Returns
    (cuts, adds); the adds go on after the cuts, the window's bevel is cut after both. ribs=False leaves the stop ribs
    out (the strip-at-the-wall check case).

    channel  under the skin from the side wall to the window's edge, from the foot to the fold zone's end, up to
             CHANNEL_TOP: the bar's LEDs clear it by STRIP_LED_CLR and their light reaches the window under it
    seat     the frame beside the bar is cut back to SEAT_X1 over SEAT_Y, so the strip can drop in beside it and
             slide under it (face-down tub, before the panel); the bar's tape side rests on what is left, at the
             lip's plane. Below SEAT_Y (under the foot's pocket and on to SEAT_Y[0]) the frame goes
             entirely, so the bar's leading edge meets no seat edge before it has bent up off the pocket's roof
    fold     over FOLD_ZONE the frame goes entirely: the folded pair and its loop hang below the bar there
    foot     a pocket in the lip over the foot and the neck up to the window's edge, its roof FOOT_POCKET['top']
             (0.015 over the foot: the foot is the panel's stop there)
    gap      the neck's gap in the chin's web (STRIP_GAP), open into the panel's pocket
    stops    at the panel's two left corners (the only places clear of the strip) a block from the side wall stands
             out to LOCATOR_X, so the glass stays clear of the folded LEDs; it reaches down past the frame to
             LOCATOR_Z0, so it faces the glass's whole edge on every panel (the midplate is notched under it)
    pads     hold-downs over the PS film's left border between the pairs (the lip is gone there); pads 1-4 each
             carry a rib (PAD_RIBS) under the channel's ceiling back to the side wall, clear over the bar's flex. The
             pad ribs are not stop ribs: ribs=False keeps them
    ribs     STRIP_RIBS on the channel's side wall, which stop the bar (and, on the fold zone, the folded piece) at
             STRIP_BAR_X"""
    x_w = LOW_X0 - 0.01
    cuts = [box(x_w, P.CHANNEL_X1, P.CHANNEL_Y[0], P.CHANNEL_Y[1], P.LIP, P.CHANNEL_TOP),
            box(P.SEAT_X1, P.POCKET_X0 + 0.01, P.SEAT_Y[0], P.SEAT_Y[1] + 0.01, P.FRAME_REAR - 0.01, P.LIP + 0.01),
            box(x_w, P.POCKET_X0 + 0.01, P.LOCATOR_Y[1], P.SEAT_Y[0] + 0.01, P.FRAME_REAR - 0.01, P.LIP + 0.01),
            box(x_w, P.POCKET_X0 + 0.01, P.FOLD_ZONE[0], P.FOLD_ZONE[1], P.FRAME_REAR - 0.01, P.LIP + 0.01),
            box(x_w, P.FOOT_POCKET['x1'], P.POCKET_Y0, P.FOOT_POCKET['y1'], P.LIP, P.FOOT_POCKET['top'])]
    g = P.STRIP_GAP
    cuts.append(box(g['x'][0], g['x'][1], g['y'][0], P.POCKET_Y0 + 0.1, g['z'][0], g['z'][1]))
    adds = []
    for y0, y1 in (P.LOCATOR_Y, P.LOCATOR_Y_TOP):              # from the wall, down past the frame to LOCATOR_Z0
        adds.append(box(x_w - 0.04, P.LOCATOR_X, y0, y1, P.LOCATOR_Z0, P.LOCATOR_Z))
    for yc in P.PAD_Y:
        adds.append(box(P.PAD_X[0], P.PAD_X[1], yc - P.PAD_LEN / 2, yc + P.PAD_LEN / 2, P.LIP, P.CHANNEL_TOP + 0.01))
    PR = P.PAD_RIBS                                             # wall to pad, under the ceiling, over the bar's flex
    for yc in PR['y']:
        adds.append(box(x_w - 0.04, P.PAD_X[0] + 0.01, yc - PR['len'] / 2, yc + PR['len'] / 2, PR['z0'], P.CHANNEL_TOP + 0.01))
    if ribs:
        R = P.STRIP_RIBS
        for yc in R['y']:
            z0 = P.LIP if yc < P.FOLD_ZONE[0] else R['z_fold']
            adds.append(box(R['x0'] - 0.05, R['x1'], yc - R['len'] / 2, yc + R['len'] / 2, z0, P.CHANNEL_TOP + 0.01))
    return cuts, adds


def build(ribs=True):
    body = outer_body()
    tub = body.intersect(box(P.X0 - 1, P.X1 + 1, P.Y0 - 1, P.Y1 + 1, P.SEAM, P.Z_FRONT + 1))
    tub = tub.cut(cavity())
    if P.LIGHT_STRIP:
        s_cut, s_add = strip_features(ribs)
        for c in s_cut:
            tub = tub.cut(c)
        for a in s_add:
            tub = tub.union(a)
    add, cut = screw_bosses()
    u = usb_features()
    for a in [*rail(), *webs(), *add, *u['tub_adds']]:
        tub = tub.union(a)
    for t in side_tabs():
        cut += key_cuts(t)
    import joint
    for a in joint.tub_adds():                               # the tongues, below the parting plane
        tub = tub.union(a)
    cut += [window(), *key_openings(), *gate_slot(), *chin_lead_in(), *key_slots(), *u['tub_cuts'], reset_hole(), *joint.tub_cuts(), *detent_pockets()]
    cut.append(rim_chamfer())
    for c in cut:
        tub = tub.cut(c)
    if P.LOGO:
        import logo
        tub = tub.cut(logo.solid(P.Z_FRONT - P.LOGO['depth'], P.Z_FRONT + 0.2))
    return tub.intersect(body).clean()                       # nothing may stand outside the envelope


if __name__ == '__main__':
    import time
    t0 = time.time()
    tub = build()
    print('tub solids:', len(tub.solids().vals()), 'volume', round(tub.val().Volume(), 1), f'{time.time() - t0:.1f}s')
    cq.exporters.export(tub, str(hw.OUT / 'tub.stl'), tolerance=0.03, angularTolerance=0.15)
