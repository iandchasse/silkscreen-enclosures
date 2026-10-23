"""Front tub: screen bezel, display pocket, chin with the four keys, and the side walls
down to the parting plane. Printed face down; every internal surface that faces the
screen (+Z) is either on the bed or a <=45 degree slope in that orientation.

The panel, then the midplate, go in from the back, so from the parting plane up to the pocket
the side walls stand at the pocket's width (Rev F; see params.INSERT_X0/X1)."""
import cadquery as cq
import hw
import params as P
from geom import box, rbox, zcyl, xcyl, xz_prism, yz_prism, stadium_x, rrect_x
from body import outer_body, inner_limit, side_tabs, usb

PCB = hw.bounds('PCB')                       # x -0.0025..59.9975, y 0..111.25
LOW_X0 = P.POCKET_X0                         # side walls' inner faces below the pocket: straight down
LOW_X1 = P.POCKET_X1                         # from the pocket, so the panel drops in past them


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
    """The screen window (params WINDOW_*). Straight up from 0.2 under the lip (the window at the lip: the active area
    + WINDOW_MARGIN, corners WINDOW_CORNER_R) to the bevel's foot WINDOW_BEVEL_DEPTH under the face, then out at
    WINDOW_BEVEL_ANGLE from the face to 0.05 past it (WINDOW_BEVEL_W wider each side on the face, corners R + W): one
    ruled loft through three sections, so the corners are cones, tangent to the sides, and print like them.
    Light-strip: Rev K's window, unchanged (_window_per_edge, P.WINDOW_BEVEL)."""
    import math
    x0 = hw.ACTIVE_CX - hw.ACTIVE_W / 2 - P.WINDOW_MARGIN
    y0 = hw.ACTIVE_CY - hw.ACTIVE_H / 2 - P.WINDOW_MARGIN
    w, h = hw.ACTIVE_W + 2 * P.WINDOW_MARGIN, hw.ACTIVE_H + 2 * P.WINDOW_MARGIN
    if P.LIGHT_STRIP:                                        # its left edge has its own bevel (WINDOW_BEVEL)
        return _window_per_edge(x0, x0 + w, y0, y0 + h, P.WINDOW_BEVEL)
    assert P.WINDOW_CORNER_R > 0
    zb, ztop = P.Z_FRONT - P.WINDOW_BEVEL_DEPTH, P.Z_FRONT + 0.05
    k = 1 / math.tan(math.radians(P.WINDOW_BEVEL_ANGLE))
    wires = [_ring(x0, x0 + w, y0, y0 + h, P.WINDOW_CORNER_R, max(0.0, z - zb) * k, z) for z in (P.LIP - 0.2, zb, ztop)]
    return cq.Workplane(obj=cq.Solid.makeLoft(wires, True))


def _window_per_edge(x0, x1, y0, y1, B):
    """Light-strip builds (Rev K's window, kept for them for now): its own 45-degree bevel on each edge
    (P.WINDOW_BEVEL), as the intersection of four half-spaces, one per edge, each straight up to Z_FRONT - bevel and
    then out at 45 degrees. With every bevel at WINDOW_CHAMFER it is Rev K's standard window (straight box + lofted
    bevel)."""
    zlo, ztop, far = P.LIP - 0.2, P.Z_FRONT + 0.02, 5.0

    def half(edge, c):
        zs = P.Z_FRONT - c
        o = ztop - zs                                        # the bevel's outward reach at ztop
        if edge in ('left', 'right'):
            e, s = (x0, -1) if edge == 'left' else (x1, 1)
            prof = [(e, zlo), (e, zs), (e + s * o, ztop), (e - s * (x1 - x0 + far), ztop), (e - s * (x1 - x0 + far), zlo)]
            return xz_prism(prof, y0 - far, y1 + far)
        e, s = (y0, -1) if edge == 'bottom' else (y1, 1)
        prof = [(e, zlo), (e, zs), (e + s * o, ztop), (e - s * (y1 - y0 + far), ztop), (e - s * (y1 - y0 + far), zlo)]
        return yz_prism(prof, x0 - far, x1 + far)
    out = None
    for edge, c in B.items():
        hs = half(edge, c)
        out = hs if out is None else out.intersect(hs)
    return out


def cavity():
    lim = inner_limit(P.SEAM - 1.5, P.LIP)
    lower = rbox(LOW_X0, LOW_X1, P.BOT_IN, P.TOP_IN, P.SEAM - 1.5, P.MID_REAR, 1.5)
    # Pocket: full size up to the EPD glass; above it the walls step in over the light guide and
    # touch film (inset ~0.45 mm on the drawing), which thickens the wall under the front edge round.
    import panel
    pocket = box(P.POCKET_X0, P.POCKET_X1, P.POCKET_Y0, P.POCKET_Y1, P.MID_REAR - 0.05, P.POCKET_STEP_Z)
    sx0 = hw.PANEL_X0 + panel.TOUCH[0] - P.POCKET_STEP_CLR
    sx1 = hw.PANEL_X0 + panel.TOUCH[1] + P.POCKET_STEP_CLR
    pocket = pocket.union(box(sx0, sx1, P.POCKET_Y0, P.POCKET_Y1, P.POCKET_STEP_Z - 0.01, P.LIP))
    for cx in (P.POCKET_X0, P.POCKET_X1):
        for cy in (P.POCKET_Y0, P.POCKET_Y1):
            pocket = pocket.union(zcyl(cx, cy, P.MID_REAR - 0.05, P.POCKET_STEP_Z, 1.0))   # glass-corner relief
    chin = box(P.POCKET_X0, P.POCKET_X1, P.BOT_IN, P.POCKET_Y0 - 1.0, P.MID_REAR - 0.05, P.LIP)
    # the screen's bottom-edge wall only needs to hold the glass (rear at 3.0 +-0.2): keep it
    # above the bottom switches' through-hole lead tips at Y 4.3 (Z 2.31)
    chin = chin.union(box(P.POCKET_X0, P.POCKET_X1, P.BOT_IN, P.POCKET_Y0 + 0.01, P.MID_REAR - 0.05, P.DISP_REAR - 0.4))
    v = lower.union(pocket).union(chin)
    for g in ribbon_gaps():
        v = v.union(g)
    return v.intersect(lim)


def ribbon_gaps():
    """The display ribbons leave the glass's bottom edge at three heights (touch at the front
    surface, frontlight 0.44 below it, EPD on the glass) and fold down past the edge. The
    pocket's bottom wall is open from the frontlight tail to the touch neck, full height, so
    no ribbon is pinched; the corners of the wall still hold the glass. The span also covers
    the back view's wider outline of the main ribbon. Light-strip variant: it starts at
    STRIP_GAP_X0, 0.55 left of the strip's neck, which takes the frontlight tail's place."""
    import panel
    c = P.FPC_GAP_CLR
    at_fold = [u for r in panel.RIBBONS.values() for u, v in r['poly'] if v >= -3.0]
    x0 = hw.PANEL_X0 + min(min(at_fold), 15.3) - c
    if P.LIGHT_STRIP:
        x0 = min(x0, P.STRIP_GAP_X0)                         # its neck is wider than the FT01C's tail
    x1 = hw.PANEL_X0 + max(at_fold) + c
    y0 = hw.PANEL_Y0 - panel.BEND_R - 0.12 - 0.35
    return [box(x0, x1, min(y0, P.POCKET_Y0 - 1.0), P.POCKET_Y0 + 0.1, P.MID_REAR - 0.05, P.LIP)]


def key_rail():
    """What the bottom keys and their cranks need from the tub (Rev L; keys.py has the profiles).

    rail   hangs from the skin between the keys and the board, from the -X wall to RAIL_END_X. Beside each
           crank a closed ring round the rod (the two ends and the three webs between the keys); under each
           switch an open seat, whose mouth clears the TS365's housing; over each cheek only a strip above
           the slot's roof. Its -Y face is the keys' +Y guide.
    webs   tie the rail to the chin wall between the keys, down to WEB_Z0. They stop 0.15 short of the
           cheeks, as the rail's rings do (the spec's 0.1 wider webs came within 0.05 of the cheeks' roofs).
    The rail is a set of walls grown from the skin as the tub prints face down; the slot roofs are floors
    and the bores teardrops pointing print-up, so nothing in it is a bridge."""
    import keys
    from shapely.ops import unary_union
    xs = [keys.key_x(r) for r in P.KEY_REFS]
    s0, s1 = P.SLOT
    ring = keys.rail_outer('ring').difference(keys.rod_hole())
    seat = keys.rail_outer('centre').difference(unary_union([keys.circ(P.ROD_YZ, P.ROD_HOLE_D / 2), keys.seat_mouth()]))
    slot = keys.rail_outer('slot')
    rings = [LOW_X0 - 0.01, *[v for x in xs for v in (x - s1, x + s1)], P.RAIL_END_X]
    out = [keys.extrude(ring, a, b) for a, b in zip(rings[0::2], rings[1::2])]
    for x in xs:
        out.append(keys.extrude(seat, x - s0, x + s0))
        out += [keys.extrude(slot, x - s1, x - s0), keys.extrude(slot, x + s0, x + s1)]
    webs = [P.WEB_OUTER[0], *[v for x in xs for v in (x - s1, x + s1)], P.WEB_OUTER[1]]
    for a, b in zip(webs[0::2], webs[1::2]):
        out.append(box(a, b, P.BOT_IN - 0.01, P.RAIL_Y[0] + 0.01, P.WEB_Z0, P.LIP + 0.01))
    return out


def rod_hole():
    """The rod's way in through the -X side wall: its teardrop, from the outer face through the side gate's slot
    (the rod channel in the slot's floor) and the sliver to the pocket, and the slot itself (gate_slot)."""
    import keys
    return [keys.extrude(keys.rod_hole(), P.X0 - 1, LOW_X0 + 0.02), *gate_slot()]


def _channel_chamfer(zf):
    """(y, z) section of the chamfers on the rod channel's two edges where it breaks a floor at z = zf: legs
    GATE_SLOT['channel_chamfer'] along the floor and along the channel's wall (down from the edge), both sides, closed
    through the channel (already cut) and 0.02 into the slot above the floor. The floor meets the wall at 107-180
    degrees here, so a flank at 45 degrees to the floor would never meet the wall: equal legs are the chamfer."""
    import math
    c, R = P.GATE_SLOT['channel_chamfer'], P.ROD_HOLE_D / 2
    yc, zc = P.ROD_YZ
    b = zf - zc
    h = math.sqrt(max(R * R - b * b, 0.0))                      # the edge, from the channel's centre line
    a = min(math.atan2(b, h) + c / R, math.pi / 2)              # c down the wall from the edge
    yw, zw = R * math.cos(a), zc + R * math.sin(a)
    return [(yc - h - c, zf - 0.02), (yc + h + c, zf - 0.02), (yc + h + c, zf), (yc + yw, zw), (yc - yw, zw), (yc - h - c, zf)]


def gate_slot():
    """The side gate's slot in the -X wall (SPEC2 rev 3, params.GATE_SLOT; the gate is keys.gate), open to the rim so
    the gate drops in from the open back:
      mouth    X0 .. the lips' faces, over `mouth` in Y: the gate's web, flush with the outer face
      cavity   behind the lips to the sliver, straight over `cavity` with full round ends (the lips' root relief; the
               tongue is notched to the same plan in joint.tub_cuts)
      floor    the gate's bevel plane, z = floor_z + (ROD_STOP_X0 - X), from 2.65 at the face to floor_z under the
               gate's flat, then flat to the sliver: the gate sits on it. The rod's teardrop (rod_hole) runs through
               it; where it breaks the floor (X > -3.09) its edges are chamfered (_channel_chamfer)
      lead-in  sliver_lead x 45 degrees on the sliver's -X face round the teardrop, for the rod's tip
    The slot and cavity are open to the rim and the floor and chamfers face print-up in the face-down tub, so
    nothing here is a bridge."""
    import math, joint
    S = P.GATE_SLOT
    x0, (yc, zc) = P.X0, P.ROD_YZ
    xl = x0 + S['lip']
    xc = xl + 2 * S['end_r']                                    # the sliver's -X face
    xf, zf = P.ROD_STOP_X0, S['floor_z']
    top, zb = P.SEAM - 0.01, zf + (xf - x0) + 2.0
    floor = xz_prism([(x0 - 1, top), (xc + 1, top), (xc + 1, zf), (xf, zf), (x0 - 1, zf + (xf - x0) + 1)], S['cavity'][0] - 1, S['cavity'][1] + 1)
    mouth = box(x0 - 1, xl + 0.01, S['mouth'][0], S['mouth'][1], top, zb).intersect(floor)
    cavity = joint.gate_cavity(top, zb).intersect(floor)
    # the chamfers: lofted through sections where the floor slopes (from where it meets the channel's bottom,
    # X xf - (zc + R - zf) = -3.09, to the flat), then straight along the flat to the sliver
    R = P.ROD_HOLE_D / 2
    xa = xf - (zc + R - zf) + 0.02
    n = 16
    wires = []
    for i in range(n + 1):
        x = xa + (xf - xa) * i / n
        pts = _channel_chamfer(zf + (xf - x))
        wires.append(cq.Wire.makePolygon([cq.Vector(x, y, z) for y, z in pts], close=True))
    slope = cq.Workplane(obj=cq.Solid.makeLoft(wires, ruled=True))
    flat = yz_prism(_channel_chamfer(zf), xf - 0.001, xc + 0.01)
    L = S['sliver_lead']
    lead = cq.Workplane(obj=cq.Solid.makeCone(R + L + 0.01, R - 0.01, L + 0.02, cq.Vector(xc - 0.01, yc, zc), cq.Vector(1, 0, 0)))
    return [mouth, cavity, slope, flat, lead]


def key_openings():
    """Key openings through the skin, each with a 45-degree chamfer on its front edge. The +Y edge is flush
    with the rail's face, so the key's +Y face runs on one straight guide from the rail to the face. The
    cap sits 0.30 inside the sides (KEY_SIDE_GAP) and 0.42 inside the chin edge (KEY_CHIN_GAP['skin']); the
    +Y corners are square and the chin corners R0.2. The chin edge stands 0.25 over the chin wall: the
    ledge (over key_slots it is the slot's roof the hooks stop under)."""
    out = []
    k = P.KEY_EDGE_CHAMFER
    O = P.KEY_OPENING
    y0, y1 = O['y']
    for ref in P.KEY_REFS:
        sx = hw.switch_plunger(ref)['face'][0]
        w, h = 2 * O['half'], y1 - y0
        s0 = cq.Sketch().rect(w, h).vertices('<Y').fillet(O['r'])
        s1 = cq.Sketch().rect(w + 2 * k + 0.4, h + 2 * k + 0.4).vertices('<Y').fillet(O['r'] + k + 0.2)
        out.append(cq.Workplane('XY', origin=(sx, (y0 + y1) / 2, P.LIP - 0.3)).placeSketch(s0).extrude(P.Z_FRONT + 1 - P.LIP + 0.3))
        out.append(cq.Workplane('XY', origin=(sx, (y0 + y1) / 2, P.Z_FRONT - k))
                   .placeSketch(s0, s1.moved(cq.Location(cq.Vector(0, 0, k + 0.2)))).loft())
        # a 45-degree lead-in on the chin wall's lower inside edge, for the key's chin side on its way in from the back
        L = P.CHIN_LEAD_IN
        out.append(yz_prism([(P.BOT_IN + 0.01, P.SEAM - 0.01), (P.BOT_IN - L - 0.01, P.SEAM - 0.01), (P.BOT_IN + 0.01, P.SEAM + L + 0.02)],
                            sx - O['half'], sx + O['half']))
    return out


def key_slots():
    """The hook keys' slots (test 2, 2026-09-30; params.KEY_SLOT): two per key in the chin wall's inner face, at |dx|
    KEY_SLOT dx (the outer side flush with the web's face), KEY_SLOT back deep, from below the rim up to KEY_SLOT_ROOF
    (the skin's underside): the key's hooks run up them from inside and stop flat under the roof. Open to the rim, they
    print as plain open-topped slots in the face-down tub (no bridge, no overhang); the lid's rim covers their ends,
    and over the key row the tub has no seam chamfer (rim_chamfer), so the wall behind them prints up to the rim.
    Each runs 0.01 into the cavity so it opens cleanly on the wall's face."""
    S = P.KEY_SLOT
    out = []
    for ref in P.KEY_REFS:
        x = hw.switch_plunger(ref)['face'][0]
        for s in (-1, 1):
            out.append(box(*sorted((x + s * S['dx'][0], x + s * S['dx'][1])), S['back'], P.BOT_IN + 0.01, P.SEAM - 1.0, P.KEY_SLOT_ROOF))
    return out


def rim_relief():
    """X span on the chin where the tub has no seam chamfer (params KEY_SLOT relief): the key row, from `relief`
    before the first slot to `relief` past the last."""
    import keys
    xs = sorted(keys.key_x(r) for r in P.KEY_REFS)
    b, r = P.KEY_SLOT['dx'][1], P.KEY_SLOT['relief']
    return xs[0] - b - r, xs[-1] + b + r


def rim_chamfer():
    """The tub's half of the seam's V (body.seam_chamfer), left off the chin over the key row (rim_relief; hverify2,
    2026-09-30, as the 3.68's): there the chamfer left the rim layer nothing behind the hook slots, a one-layer slit
    into them in the V over every key. Over the key row the tub's rim meets the lid's chamfer square; the step at each
    end is vertical."""
    from body import seam_chamfer
    v = seam_chamfer(upper=True)
    if v is None:                                            # no V at all since 2026-10-23
        return None
    x0, x1 = rim_relief()
    return v.cut(box(x0, x1, P.Y0 - 3.0, P.Y0 + 1.0, P.SEAM - 1.0, P.SEAM + 1.0))


def screw_bosses():
    """PCB clamp bosses at H3/H4 (lid screws pass through the PCB into these) and the top boss."""
    fps = hw.footprints()
    add, cut = [], []
    for ref in ('H3', 'H4'):
        hx, hy = fps[ref]['cad']
        # flat on the screen side: the round boss reached 0.17 into the pocket, in the panel's way
        flat = box(hx - P.BOSS_D, hx + P.BOSS_D, hy - P.BOSS_D, P.POCKET_Y0, P.PCB_FRONT - 1, P.LIP + 1)
        add.append(zcyl(hx, hy, P.PCB_FRONT, P.LIP + 0.01, P.BOSS_D).intersect(flat))
        cut.append(zcyl(hx, hy, P.PCB_FRONT - 0.1, P.Z_FRONT - 0.55, P.M2_PILOT))
    tx, ty = P.TOP_SCREW
    add.append(zcyl(tx, ty, P.SEAM, P.LIP + 0.01, P.TOP_BOSS_D))
    cut.append(zcyl(tx, ty, P.SEAM - 0.1, P.Z_FRONT - 0.55, P.M2_PILOT))
    # the top screw's relief (2026-10-23): an M2_CLEAR bore from the rim to TOP_SCREW_CLEAR_TO, so the screw thread-forms only the
    # last 3.8 of the pilot (3.6 as printed), as H3 / H4 do; it had 9.0 and stripped heads. 1.6 is a layer line of the face-down tub
    cut.append(zcyl(tx, ty, P.SEAM - 0.1, P.TOP_SCREW_CLEAR_TO, P.M2_CLEAR))
    return add, cut


def usb_features():
    """The port (Rev I): the recess - the divot - for the plug's overmold, USB_RECESS (typical
    cables) with a 45-degree lead-in at the case face, and its floor, which is the tub itself:
    USB_FLOOR['t'] thick, its inside on the panel's insertion corridor (INSERT_X1). The port's hole is
    J1's opening plus USB_FLOOR['hole'] a side; below it the floor is open to the parting line (a
    notch), so the hole prints with no bridge, and a block on the lid rises into the notch and closes
    the hole's lower edge. The recess crosses the parting line, so the lid cuts its lower part too.

    tub_cuts  the recess, from the floor's face outward, and the hole with its notch
    tub_adds  the floor's inner 0.1 mm, where it stands proud of the wall's inside (LOW_X1 -> INSERT_X1)
    lid_cuts  the recess
    lid_adds  the block that closes the hole's lower edge

    2026-10-22: the hole's and the recess's board-side edges stand P.USB_HOLE_TOP / USB_RECESS_TOP, a layer or so
    further out than J1's opening plus 0.1 (board Rev 1.02's J1 sits 0.14 nearer the board; asprinted.usb_fit reads
    the printed edges against both boards' sockets)."""
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
    # the floor's inner 0.1 mm: over the recess and a margin round it
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


def header_opening():
    """Mating opening for the J6 expansion header (plastic body Z -5.165..-0.085; its pins,
    not the body, stand through the PCB)."""
    b = hw.bounds('J6')
    return box(b[0] - 0.3, b[1] + 0.3, P.TOP_IN - 0.5, P.Y1 + 1, P.SEAM - 0.2, -0.085 + 0.3)


def detent_pockets():
    """Rev K: a pocket in each side wall's inner face for each of the midplate's detent bumps
    (midplate.detents), MID_DETENT['depth'] past the wall face. Its roof - the face toward the back,
    which the bump catches - is 45 degrees, because in the face-down tub it prints as a roof; it runs
    long toward the front so a -0.2 panel's plate still sits free in it once the lid is on."""
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
    """The slot one side key (sidekeys.py, part of the lid since Rev J) rises into. Rev G/H cut the
    key out of this wall, so its top edge had to be printed over an air gap.

    slot     the outer layer and the void, from the parting line up to TAB_SLOT_CLR over the key's
             top, from TAB_ROOT_CLR before its block to TAB_END_CLR past its free end (the bar that
             flexes is below the parting line, under the tub's whole wall)
    window   through the sliver where the nub crosses it
    Both are open to the parting line, so the tub prints round them face down with no overhang
    anywhere, and the key slides in along them as the lid goes on. (Rev I's socket for the clip is
    gone: the wall behind the root is solid again.)"""
    s, a = t['side'], t['away']
    xo = P.X1 if s > 0 else P.X0
    ys = sorted((t['y_block'] - a * P.TAB_ROOT_CLR, t['y_free'] + a * P.TAB_END_CLR))
    xs = sorted((t['stop'], xo + s * 1.0))
    top = P.TAB_Z[1] + P.TAB_SLOT_CLR
    assert top < P.POCKET_STEP_Z - 1.0, top
    cuts = [box(xs[0], xs[1], ys[0], ys[1], P.SEAM - 0.1, top)]
    from body import tab_window
    w = tab_window(t)
    cuts.append(box(w['x'][0], w['x'][1], w['y'][0], w['y'][1], P.SEAM - P.JOINT['h'] - 0.6, w['top']))
    return cuts


def strip_cuts():
    """Light-strip variant: the raised ceiling over the left border (skin underside up to STRIP_CEIL z
    from the pocket's wall to the window, so the LEDs' light passes under the skin into the window),
    and the pocket's step wall taken out along the bar and the foot (the bar overhangs the glass's edge
    and stands above the step); and the relief in the pocket's left wall (STRIP_WALL_RELIEF) so the bar
    is never the panel's left stop, with a 45-degree roof (it prints as a roof, face down)."""
    import panel
    C = P.STRIP_CEIL
    sx0 = hw.PANEL_X0 + panel.TOUCH[0] - P.POCKET_STEP_CLR       # the step wall's face, as cavity()
    R = P.STRIP_WALL_RELIEF
    xw, d = P.POCKET_X0, R['depth']
    k = R['rise'] / d                                            # the roof's dz per dx
    relief = xz_prism([(xw + 0.01, R['z0'] - 0.01 * k), (xw - d, R['z0'] + R['rise']), (xw - d, R['z1']), (xw + 0.01, R['z1'])],
                      R['y'][0], R['y'][1])
    return [box(C['x'][0], C['x'][1] + 0.01, C['y'][0], C['y'][1], P.POCKET_STEP_Z - 0.01, C['z']),
            box(C['x'][0], sx0 + 0.01, C['step_y'][0], C['step_y'][1], P.POCKET_STEP_Z - 0.01, P.LIP),
            relief]


def strip_adds():
    """Light-strip variant, added after every cut:
    stops      rails from the lip onto the plain panel's PS at PLAIN_FRONT (the layer boundary 4.00),
               right, top and bottom (PANEL_STOPS), so the thinner panel sits 0.074 in front of where
               the FT01C's rear sat and the springs keep most of their travel
    hold-downs pads from the raised ceiling to 0.015 over the bar's flex top, between the LED pairs and
               off their solder pads, and one from the skin onto the foot (STRIP_HOLD), so the panel's
               left edge stays down too"""
    out = []
    for s in P.PANEL_STOPS.values():
        out.append(box(s['x'][0], s['x'][1], s['y'][0], s['y'][1], P.PLAIN_FRONT, P.LIP + 0.01))
    H = P.STRIP_HOLD
    for y0, y1 in H['ys']:
        out.append(box(H['x'][0] - 0.01, H['x'][1], y0, y1, H['z'], P.STRIP_CEIL['z'] + 0.01))
    f = H['foot']
    out.append(box(f['x'][0], f['x'][1], f['y'][0], f['y'][1], H['z'], P.LIP + 0.01))
    return out


def build():
    body = outer_body()
    tub = body.intersect(box(P.X0 - 1, P.X1 + 1, P.Y0 - 1, P.Y1 + 1, P.SEAM, P.Z_FRONT + 1))
    tub = tub.cut(cavity())
    add, cut = screw_bosses()
    u = usb_features()
    # every bottom-key feature (rail, openings, hook slots, the rod's hole and the gate's slot, the rim relief) is
    # gated on P.BOTTOM_KEYS, the dev header's opening on P.DEV_HEADER; each sits where it always did in its list
    keyed = P.BOTTOM_KEYS
    for a in [*(key_rail() if keyed else []), *add, *u['tub_adds']]:
        tub = tub.union(a)
    for t in side_tabs():
        cut += key_cuts(t)
    import joint
    for a in joint.tub_adds():                               # the tongues, below the parting plane
        tub = tub.union(a)
    cut += [window(), *(key_openings() if keyed else []), *(key_slots() if keyed else []), *(rod_hole() if keyed else []),
            *u['tub_cuts'], reset_hole(), *([header_opening()] if P.DEV_HEADER else []), *joint.tub_cuts(), *detent_pockets()]
    if P.LIGHT_STRIP:
        cut += strip_cuts()
    if keyed:                                                # the seam's V (None: square since 2026-10-23)
        v = rim_chamfer()
    else:                                                    # no key row: the seam's full V all round
        from body import seam_chamfer
        v = seam_chamfer(upper=True)
    if v is not None:
        cut.append(v)
    for c in cut:
        tub = tub.cut(c)
    if P.LIGHT_STRIP:
        for a in strip_adds():                               # after the cuts: the pads hang from the raised ceiling
            tub = tub.union(a)
    if P.LOGO:
        import logo
        tub = tub.cut(logo.solid(P.Z_FRONT - P.LOGO['depth'], P.Z_FRONT + 0.2))
    return tub.intersect(body).clean()                       # nothing may stand outside the envelope


if __name__ == '__main__':
    import time
    t0 = time.time()
    tub = build()
    print('tub solids:', len(tub.solids().vals()), 'volume', round(tub.val().Volume(), 1), f'{time.time() - t0:.1f}s')
    cq.exporters.export(tub, str(P.OUT / 'tub.stl'), tolerance=0.03, angularTolerance=0.15)
