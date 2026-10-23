"""Back lid: a shallow tray below the parting plane.

  - two M2 screws pass through the lid, the PCB's H3/H4 holes and into the tub bosses,
    clamping the PCB; a third screw at the top centre closes the top edge
  - four posts support the PCB rear at H1/H2/H5/H6: H5's carries the locating pin, the other three
    are bored round the midplate's pins
  - battery bay: two bridge springs press the pack lightly forward into the midplate's slot; they
    stop short of the cell's right edge, where spare lead wound on the midplate's cleats runs
  - carries the lower part of the USB-C recess, the block that closes the port hole's lower edge,
    and the reset-pin guide
  - its rim is the closed groove the tub's tongue runs in, and thirteen latch arms reach up past the
    side keys' slots to hook pockets in the tub's wall (joint.py)
  - the five side keys (Rev J, sidekeys.py): each is the lid's side wall cut free on three sides and
    carried up past the parting line into its slot in the tub, so it prints standing on the back face
  - the site's book icon engraved 0.4 mm into the centre of the back (params.LOGO_BACK) and the wordmark above the grip
    grooves (params.LOGO_BACK_WORDMARK; it was in the chin until 2026-10-23)
Printed back face down.
"""
import cadquery as cq
import hw
import params as P
from geom import box, rbox, zcyl, rrect_x
from body import outer_body, side_tabs, usb
import sidekeys
from tub import usb_features, LOW_X0, LOW_X1

RIM = 1.2
TOP_CB_WALL_D = 6.2           # the top screw's boss round its counterbore (below)


def counterbore(x, y):
    """A screw head's counterbore from the back face, with the two-layer stepped bridge over its ceiling
    (params.M2_CB_BRIDGE_LAYERS): a slot M2_CLEAR wide across it, then an M2_CLEAR square; the round
    clearance hole is cut separately. The slot runs along X: the counterbore is round, so each layer's
    bridges are no longer one way than the other."""
    z = P.Z_BACK + P.M2_HEAD_CB_DEPTH
    c, r = P.M2_CLEAR, P.M2_HEAD_CB / 2
    slot = box(x - r, x + r, y - c / 2, y + c / 2, z, z + P.LAYER).intersect(zcyl(x, y, z, z + P.LAYER, P.M2_HEAD_CB))
    square = box(x - c / 2, x + c / 2, y - c / 2, y + c / 2, z, z + P.M2_CB_BRIDGE_LAYERS * P.LAYER)
    return [zcyl(x, y, P.Z_BACK - 1, z, P.M2_HEAD_CB), slot, square]


def build(keys=True):
    """The lid as printed; keys=False leaves the five side keys out (the checks and the showcase
    handle them as separate bodies, because they move)."""
    body = outer_body()
    lid = body.intersect(box(P.X0 - 1, P.X1 + 1, P.Y0 - 1, P.Y1 + 1, P.Z_BACK - 1, P.SEAM))
    lid = lid.cut(rbox(P.X0 + RIM, P.X1 - RIM, P.Y0 + RIM, P.Y1 - RIM, P.LID_FLOOR_IN, P.SEAM + 1, P.CORNER_R - RIM))
    fps = hw.footprints()
    adds, cuts = [], []

    # PCB clamp screws at H3/H4 and the top screw. The counterbores (params.M2_HEAD_CB_DEPTH) end at z_cb, and the
    # stepped bridge over each is two layers on from there (bridge_top). Each H3 / H4 boss is Ø6.0 up to bridge_top, so
    # both bridge layers land on it (-4.5 until 2026-10-13, when the counterbores went one layer deeper for socket heads;
    # above it the Ø4.2 post would leave 0.4 round the square layer's corners)
    z_cb = P.Z_BACK + P.M2_HEAD_CB_DEPTH
    bridge_top = z_cb + P.M2_CB_BRIDGE_LAYERS * P.LAYER
    for ref in ('H3', 'H4'):
        hx, hy = fps[ref]['cad']
        adds.append(zcyl(hx, hy, P.LID_FLOOR_IN - 0.1, bridge_top, 6.0))
        adds.append(zcyl(hx, hy, -4.6, P.PCB_REAR, 4.2))
        if not P.BOTTOM_KEYS:
            # chinless: the short chin's wall is 0.6 from the Ø6 boss, a slot narrower than two lines; the boss runs
            # into the wall instead, its own width and top (the clearance hole and the counterbore cut through it)
            adds.append(box(hx - 3.0, hx + 3.0, P.BOT_IN - 0.01, hy, P.LID_FLOOR_IN - 0.1, bridge_top))
        cuts += [zcyl(hx, hy, P.Z_BACK - 1, P.PCB_REAR + 1, P.M2_CLEAR), *counterbore(hx, hy)]
    tx, ty = P.TOP_SCREW
    adds.append(zcyl(tx, ty, P.LID_FLOOR_IN - 0.1, P.SEAM, 5.0))
    # round the counterbore this Ø5.0 boss leaves a 0.4 wall, too thin for the slicer (classic walls drop it), so its
    # ceiling had nothing under it but the top wall. The boss is Ø6.2 up to the stepped bridge's top, except: no
    # further toward J6 (x 42.88) than it already reached (x 42.7); no nearer the end of the joint's inner lip
    # (x 37.0, y 112.4-113.25) than 0.6; and not into the groove past the lip (y > 113.25), where the tub's tongue
    # ends. It also keeps 0.3 off the midplate's top battery cleat, whose cap hangs down to BAY['cleat_top'] just
    # above the ceiling (under the cleat it stops 0.3 below the cleat: at the ceiling until 2026-10-13, a layer under it
    # since the counterbores are 2.0 deep; there the counterbore's wall is the Ø5.0 boss's 0.4 for that layer). The wall
    # the bridge's first layer lands on is then 0.95-1.0 thick. On +X, by J6 and the header opening, the wall stays
    # 0.3-0.4 and still does not print: the square layer's wall there spans ~2 mm from this wall to the top wall.
    # nodev (no J6, no opening): there that 0.4 wall printed a 0.15 mm2 scrap in mid-air at the stepped bridge's first
    # layer (z 2.0 as printed, x 42.5, y 113.1). So the Ø6.2 wall runs full round toward J6's place (1.0 thick there)
    # and on into the end of the lip's second top run (x 43.4), leaving no slot narrower than two lines (variants C6,
    # 2026-10-07; slice_check.top_no_support reads it).
    wall = zcyl(tx, ty, P.LID_FLOOR_IN - 0.1, bridge_top, TOP_CB_WALL_D).intersect(
        box(37.6, tx + 2.5 if P.DEV_HEADER else tx + TOP_CB_WALL_D, ty - 4, 113.25, P.LID_FLOOR_IN - 1, P.SEAM))
    if not P.DEV_HEADER:
        wall = wall.union(box(tx, P.TONGUE_RUNS['top'][1][0] + 0.05, 112.4, 113.25, P.LID_FLOOR_IN - 0.1, bridge_top))
    cx0 = P.BATT['x'][1] + P.FENCE['clr']
    cy1 = P.BAY['cleats'][1] + P.FENCE['len'] / 2 + P.BAY['cap']
    under_cleat = min(z_cb, P.BAY['cleat_top'] - 0.3)
    adds.append(wall.cut(box(cx0 - 0.3, cx0 + P.BAY['cleat_t'] + 0.3, ty - 5, cy1 + 0.3, under_cleat, P.SEAM)))
    cuts += [zcyl(tx, ty, P.Z_BACK - 1, P.SEAM + 1, P.M2_CLEAR), *counterbore(tx, ty)]

    # PCB support posts. H1, H2 and (Rev H) H6 take the midplate's snap posts through the board, so
    # they carry no locating pin, only a clearance bore for the barb; H5 keeps its pin, which is
    # what still registers the board's top end in X and Y.
    for ref in ('H1', 'H2', 'H5', 'H6'):
        hx, hy = fps[ref]['cad']
        adds.append(zcyl(hx, hy, P.LID_FLOOR_IN - 0.1, P.PCB_REAR, P.BOARD_POST_D[ref]))
        if ref in P.SNAP_POSTS:
            bd, bz = P.BOARD_SNAP_BORE
            cuts.append(zcyl(hx, hy, bz, P.PCB_REAR + 0.01, bd))
        else:
            adds.append(zcyl(hx, hy, P.PCB_REAR - 0.01, P.PCB_REAR + 0.8, 1.9))
            adds.append(cq.Workplane(obj=cq.Solid.makeCone(0.95, 0.6, 0.4, cq.Vector(hx, hy, P.PCB_REAR + 0.79))))

    # USB: solid block under the receptacle, a mm wider than the recess each side; the recess's lower
    # part is cut into it (the tub has the rest), and a block rises from it into the tub floor's notch
    # to close the port hole's lower edge
    u = usb()
    uf = usb_features()
    py0, py1 = uf['block_y']
    adds.append(box(58.5, P.X1 - 0.5, py0, py1, P.LID_FLOOR_IN - 0.1, P.SEAM))
    adds += uf['lid_adds']
    cuts += uf['lid_cuts']

    # reset pin guide: a trough under the pin path, stopping at the joint groove's inner face
    rx, ry, rz = hw.switch_plunger(hw.RESET)['face']
    trough = box(rx + 0.6, LOW_X1 - P.JOINT['clr'], ry - 1.4, ry + 1.4, P.LID_FLOOR_IN - 0.1, rz + 0.5)
    trough = trough.cut(box(rx, LOW_X1 + 1, ry - 0.6, ry + 0.6, rz - 0.6, rz + 1))
    adds.append(trough)

    # battery bay
    bx0, bx1 = P.BATT['x']
    by0, by1 = P.BATT['y']
    bz0 = P.BATT['z'][0]
    # the midplate's slot locates the pack; the lid only presses it forward
    spring_top = bz0 - 0.35
    for sy in (91.0, 104.0):
        sx0, sx1 = bx0 + 4.0, bx1 - 4.0
        for px in (sx0, sx1):
            adds.append(box(px - 1.5, px + 1.5, sy - 2.5, sy + 2.5, P.LID_FLOOR_IN - 0.1, spring_top))
        adds.append(box(sx0, sx1, sy - 2.0, sy + 2.0, spring_top - 0.6, spring_top))
        cx = (sx0 + sx1) / 2
        adds.append(box(cx - 1.5, cx + 1.5, sy - 2.0, sy + 2.0, spring_top - 0.01, bz0 + 0.5))

    # joint: the rim's outer leg, the inner lip that closes the groove, and the latch arms
    import joint
    adds += joint.lid_adds()

    for a in adds:
        lid = lid.union(a)
    for c in cuts:
        lid = lid.cut(c)

    # header opening (lower half); none when J6 is not fitted (nodev): the top wall stays closed
    if P.DEV_HEADER:
        b6 = hw.bounds('J6')
        lid = lid.cut(box(b6[0] - 0.3, b6[1] + 0.3, P.TOP_IN - 0.5, P.Y1 + 1, b6[4] - 0.25, P.SEAM + 1))
    for c in joint.lid_cuts():
        lid = lid.cut(c)
    g = P.GRIP_GROOVE
    for gy in P.GRIP_GROOVES_Y:
        lid = lid.cut(rbox(g['x'][0], g['x'][1], gy - g['width'] / 2, gy + g['width'] / 2,
                           P.Z_BACK - 0.5, P.Z_BACK + g['depth'], g['width'] / 2 - 0.01))
    from body import seam_chamfer
    v = seam_chamfer(upper=False)
    if v is not None:                                # square since 2026-10-23
        lid = lid.cut(v)
    if P.LOGO_BACK:                                  # the site's book icon, centred on the back
        import logo
        lid = lid.cut(logo.solid(P.Z_BACK - 0.2, P.Z_BACK + P.LOGO_BACK['depth'], P.LOGO_BACK))
    if P.LOGO_BACK_WORDMARK:                         # the wordmark above the grip grooves (2026-10-23: it was in the chin)
        import logo
        lid = lid.cut(logo.solid(P.Z_BACK - 0.2, P.Z_BACK + P.LOGO_BACK_WORDMARK['depth'], P.LOGO_BACK_WORDMARK))
    lid = lid.intersect(body)
    # the side keys: out comes each one's footprint, its void and its free-end slot; in goes the key,
    # which stands on the back face and is fused to the wall at its root
    for t in side_tabs():
        lid = lid.cut(sidekeys.lid_cut(t))
    if keys:
        for t in side_tabs():
            lid = lid.union(sidekeys.build(t['ref']))
    return lid.clean()


if __name__ == '__main__':
    import time
    t0 = time.time()
    lid = build()
    print('lid solids', len(lid.solids().vals()), 'vol', round(lid.val().Volume(), 1), f'{time.time() - t0:.1f}s')
    cq.exporters.export(lid, str(P.OUT / 'lid.stl'), tolerance=0.03, angularTolerance=0.15)
