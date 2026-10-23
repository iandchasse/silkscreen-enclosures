"""Back lid: a shallow tray below the parting plane (Rev K), carrying the battery (x3).

  - four M2 x 8 screws (three until 2026-10-13) pass through posts in the lid into the tub: two in the chin's bottom
    corners, below the rod (until 2026-10-13 through the board's H3/H4 holes into bosses in front of it), one in the
    top-right corner and one in the top-left (params, fasteners). Their heads' counterbores open at the bed; each ceiling steps from a slot to a square
    (stepped_bridge), so it prints with no support (2026-09-30)
  - posts support the PCB's rear at H3, H4, H5, H6 and in SW5's empty site: H3/H4's and H5's carry a locating pin
    into the board's hole, H6's is bored for the midplate's snap barb (H2's post gave way to the battery; its snap
    post still clips the board)
  - the battery bay (x3): the cell lies on the lid's floor behind the board, over the middle of the board
    where nothing stands deeper than 1.635. Its bottom edge tucks under a lip and it is held with tape (the two
    hooks went 2026-10-19: nothing on the lid presses the cell). Its lead leaves the top end, turns in the gallery
    above it and is taped to the midplate's bare back above J5 (the tape point, with a coil well beside it)
  - backstops: above the board's trimmed edge nothing is behind the midplate but the lid, so posts rise
    from the floor to hold it there (clear of it as printed with the lid home: BACKSTOP_TOP), none within 3.45 of
    the board's cut; a low fence (FENCE_TOP) runs along the top wall, 2.6 under the plate so two leads pass over it
  - ribs (2026-10-19): six low straight ribs on the floor stiffen the back from inside (RIBS)
  - the lower part of the USB-C recess, the block that closes the port hole's lower edge, the reset guide
  - its rim is the closed groove the tub's tongue runs in, and latch arms reach up past the side keys'
    slots to hook pockets in the tub's wall (joint.py); two more on the top wall (x3)
  - the three side keys (Rev J/K, sidekeys.py): each is the lid's side wall cut free on three sides
  - the site's book icon engraved in the back (params.LOGO_BACK), the wordmark above the grip grooves
    (params.LOGO_BACK_WORDMARK; it was in the chin until 2026-10-23), and the grip grooves
Printed back face down.
"""
import math
import cadquery as cq
import hw
import params as P
from geom import box, rbox, zcyl, xz_prism, yz_prism
from body import outer_body, side_tabs, usb
import sidekeys
from tub import usb_features, LOW_X0, LOW_X1

RIM = 1.2
BAY_WALL_TOP = P.BATT_FRONT - 0.6            # the bay's side walls hold the cell's edge up to 0.6 short of its face:
                                             # bed 5.0, a whole layer (-0.5 was bed 5.1, a mid-plane)
# The backstops and the top rib stop under the midplate's rear, as printed with the lid at its home (2026-10-13): on
# the lid's layer grid, the line at least BACKSTOP_CLR under the plate's rear with the lid LID_HOME_DZ forward: 1.565,
# 0.13 clear of a nominal panel's plate and 0.03 of the thickest's. They were drawn 0.1 behind it (1.70), which printed
# to the line over it (1.765), so with the lid home they stood 0.07 into a nominal panel's plate (0.17 into the
# thickest's): the only place in the closed case where two printed parts met, along the top edge, holding the top-left
# corner open by that much. slice_check reads the gap back (asprinted.overlap).
# 2026-10-19 (the bay study): BACKSTOP_CLR 0.3 (was 0.1), so the posts stand 0.33 clear of a nominal panel's plate and
# 0.23 of the thickest's, the lead can lie over or by them. The two right posts moved to X 49.5 / 54.5, Y 91.2: none
# stands within 3.45 of the board's cut (Y 86.25; they were 1.15 and 1.45 past it, as tall as the board's front face,
# where a sliver of board or the 3V3 bodge wire would sit on them), and none in the lead's well (X 38.5-47, Y 86.5-93).
BACKSTOP_CLR = 0.3
BACKSTOP_TOP = round(P.Z_BACK + P.LAYER * math.floor((P.MID_REAR - P.LID_HOME_DZ - BACKSTOP_CLR - P.Z_BACK) / P.LAYER
                                                     + 1e-9), 3)       # 1.565
BACKSTOPS = [(3.4, 86.0, 3.0), (3.4, 92.2, 3.0), (49.5, 91.2, 3.0), (54.5, 91.2, 3.0)]   # (x, y, d)
TOP_RIB = dict(y=(P.TOP_IN - 1.0, P.TOP_IN - 0.2), x=[(10.9, 44.1), (50.0, 56.9)])   # along the top wall, above
                                                                                     # the lead's gallery
# The top rib is a fence now: its top FENCE_CLR under the midplate as printed, so two 1.3 leads fit over it, and it
# keeps the lead's U-turn out of the tongue's groove.
FENCE_CLR = 2.6
FENCE_TOP = round(P.Z_BACK + P.LAYER * math.floor((P.MID_REAR - P.LID_HOME_DZ - FENCE_CLR - P.Z_BACK) / P.LAYER
                                                  + 1e-9), 3)       # -1.035
# 2026-10-19 (Ian: stiffen the back from inside, nothing visible; bow.md option c, re-fitted to the bay lid): straight
# ribs on the floor, 1.2 wide, from the floor to RIB_TOP (bed 3.0: whole layers), each >= 0.6 from every post,
# screw post, bay wall, latch pedestal and rim, out of the cell's pocket and of the lead's zone (X 37-48 above Y 76.5:
# the fixed run, the plug, T and the coil well), and >= 0.5 under whatever is over it as printed (a switch housing's
# body over T30b / L55.5: 0.907). (x0, x1, y0, y1)
RIB_TOP = round(P.Z_BACK + 3.0, 3)          # -5.435
RIBS = {'T30a': (0.8, 21.4, 29.4, 30.6), 'T30b': (28.5, 55.8, 29.4, 30.6),   # across at Y 30, either side of H6's post
        'T52': (0.9, 59.3, 51.4, 52.6),                                         # across, 2.6 under the pocket's wall
        'L3': (2.4, 3.6, 7.1, 52.0), 'L41': (40.4, 41.6, -7.0, 75.3), 'L55.5': (54.9, 56.1, 7.1, 52.0)}   # along


def ribs():
    return [box(x0, x1, y0, y1, P.LID_FLOOR_IN - 0.1, RIB_TOP) for x0, x1, y0, y1 in RIBS.values()]


def bay():
    """The battery bay's solids: walls, the end stop, the bottom lip (no hooks since 2026-10-19). Returns (adds,
    cuts, info)."""
    c = P.BATT_POCKET_CLR
    bx0, bx1 = P.BATT['x']
    by0, by1 = P.BATT['y']
    zf, zc = P.BATT_FRONT, P.BATT_FLOOR              # the cell's front face (at its max thickness), its floor
    px0, px1, py0, py1 = bx0 - c, bx1 + c, by0 - c, by1 + c
    t = P.BATT_WALL_T
    root = zc - 0.1
    adds, cuts = [], []
    # left wall, low where SW7's body stands over it; right wall up to where the lead comes down; bottom wall.
    # The top end stays open, so the lead can leave the cell anywhere along it and turn toward J5.
    lo = P.BATT_WALL_LOW
    y_side = by1 - 1.0
    for a, b in ((py0 - t, lo['y'][0]), (lo['y'][1], y_side)):
        adds.append(box(px0 - t, px0, a, b, root, BAY_WALL_TOP))
    adds.append(box(px0 - t, px0, lo['y'][0], lo['y'][1], root, lo['top']))
    adds.append(box(px1, px1 + t, py0 - t, P.BATT_RIGHT_WALL_TO, root, BAY_WALL_TOP))
    tb = P.BATT_WALL_BOTTOM_T                         # thinner: it stands 0.45 clear of the ESP32 module's edge
    adds.append(box(px0 - t, px1 + t, py0 - tb, py0, root, BAY_WALL_TOP))
    # the top end's low wall: an end stop under the lead, so the cell cannot slide out from under the lip
    es = P.BATT_END_STOP
    adds.append(box(px0 - t, px1, by1 + es['clr'], by1 + es['clr'] + es['t'], root, zc + es['h']))
    # bottom lip: the strip of board over the cell's bottom edge is bare but for a row of 0603 resistors
    # (BATT_LIP['skip']), which it steps round. Its underside is 45 degrees (an overhang in the lid's print) and
    # passes BATT_LIP['clr_z'] over the cell's face right at the cell's edge, reaching `over` past it.
    L = P.BATT_LIP
    z_edge = zf + L['clr_z']
    z_w = z_edge - (by0 - py0)                         # the underside meets the wall's face lower, at 45 degrees
    y_tip, z_tip = by0 + L['over'], z_edge + L['over']
    prof = [(py0 - tb, root), (py0, root), (py0, z_w), (y_tip, z_tip), (y_tip, z_tip + L['t']), (py0 - tb, z_tip + L['t'])]
    x_hi = min(px1 - 0.3, hw.bounds('U11')[0] - 0.3)   # its right end stops short of the charger (U11)
    for a, b in ((px0 + 0.3, L['skip'][0]), (L['skip'][1], x_hi)):
        adds.append(yz_prism(prof, a, b))
    info = {'pocket': [round(v, 3) for v in (px0, px1, py0, py1)], 'z': [round(zc, 3), round(zf, 3)],
            'floor_under_cell': P.BATT_FLOOR_T,
            'lip': {'y': [round(py0, 3), round(y_tip, 3)], 'z_edge': round(z_edge, 3), 'z_top': round(z_tip + L['t'], 3),
                    'skip_x': list(L['skip'])},
            'end_stop': {'y': round(by1 + es['clr'], 3), 'top': round(zc + es['h'], 3),
                         'lip_engagement_min': round(L['over'] - es['clr'], 3)},
            'wall_top': round(BAY_WALL_TOP, 3), 'wall_low': lo}
    return adds, cuts, info


def backstops():
    """Posts from the floor to just behind the midplate, and the fence along the top wall, where the board has been
    cut away."""
    out = [zcyl(x, y, P.LID_FLOOR_IN - 0.1, BACKSTOP_TOP, d) for x, y, d in BACKSTOPS]
    y0, y1 = TOP_RIB['y']
    out += [box(a, b, y0, y1, P.LID_FLOOR_IN - 0.1, FENCE_TOP) for a, b in TOP_RIB['x']]
    return out


def stepped_bridge(x, y, z_seat, along):
    """The cuts that let a screw head's counterbore print with no support. The lid prints back face down, so the
    counterbore opens at the bed and its ceiling (the head's seat) is over air with the clearance hole in it: bridge
    lines laid across it would end in mid-air at the hole. Instead the first layer over the seat leaves open only a
    slot as wide as the clearance hole, running `along` ('x' or 'y') right across the counterbore, so that layer
    bridges wall to wall beside the slot; the next leaves open only the clearance hole's square, so it bridges across
    the slot's two ends, from the first layer's material on either side; the round hole goes on from there. The
    seat must be on the layer grid from the back face (the bed)."""
    k = (z_seat - P.Z_BACK) / P.LAYER
    assert abs(k - round(k)) < 1e-6, f'seat {z_seat} is off the layer grid ({k:.3f} layers)'
    c, d, L = P.M2_CLEAR, P.M2_HEAD_CB, P.LAYER
    a, b = (d / 2 + 0.1, c / 2) if along == 'x' else (c / 2, d / 2 + 0.1)
    slot = box(x - a, x + a, y - b, y + b, z_seat - 0.01, z_seat + L).intersect(zcyl(x, y, z_seat - 0.1, z_seat + L + 0.1, d))
    square = box(x - c / 2, x + c / 2, y - c / 2, y + c / 2, z_seat + L - 0.01, z_seat + 2 * L)
    return [slot, square]


def screw_cuts(x, y, z_seat, along):
    """A screw's way through the lid: the clearance hole, the head's counterbore from the back up to its seat, and the
    stepped bridge over it."""
    return [zcyl(x, y, P.Z_BACK - 1, P.SEAM + 1, P.M2_CLEAR),
            zcyl(x, y, P.Z_BACK - 1, z_seat, P.M2_HEAD_CB)] + stepped_bridge(x, y, z_seat, along)


def board_pin(x, y, pin=None):
    """A pin on a board post into the board's hole (H5's, and H3/H4's since 2026-10-13): a stub and a cone on its tip."""
    p = pin or P.H34_PIN
    r0, r1, h = p['cone']
    return [zcyl(x, y, P.PCB_REAR - 0.01, P.PCB_REAR + p['h'], p['d']),
            cq.Workplane(obj=cq.Solid.makeCone(r0, r1, h, cq.Vector(x, y, P.PCB_REAR + p['h'] - 0.01)))]


def build(keys=True):
    """The lid as printed; keys=False leaves the side keys out (the checks and the showcase handle them as
    separate bodies, because they move)."""
    body = outer_body()
    lid = body.intersect(box(P.X0 - 1, P.X1 + 1, P.Y0 - 1, P.Y1 + 1, P.Z_BACK - 1, P.SEAM))
    lid = lid.cut(rbox(P.X0 + RIM, P.X1 - RIM, P.Y0 + RIM, P.Y1 - RIM, P.LID_FLOOR_IN, P.SEAM + 1, P.CORNER_R - RIM))
    # the cell's pocket is sunk into the floor, leaving BATT_FLOOR_T (two layers) under the cell
    c = P.BATT_POCKET_CLR
    lid = lid.cut(box(P.BATT['x'][0] - c, P.BATT['x'][1] + c, P.BATT['y'][0] - c, P.BATT['y'][1] + c,
                      P.BATT_FLOOR, P.LID_FLOOR_IN + 0.01))
    fps = hw.footprints()
    adds, cuts = [], []

    # the board's posts at H3/H4 (until 2026-10-13 the bottom pair's screws went through them and the board): a wide
    # base, a post under the board above it (as when they carried the counterbores: the base's top at Z_BACK + 4.3,
    # the post's foot at + 4.2) and on it H5's pin into the board's hole, the board's X/Y stop at its bottom edge
    for ref in ('H3', 'H4'):
        hx, hy = fps[ref]['cad']
        adds.append(zcyl(hx, hy, P.LID_FLOOR_IN - 0.1, P.Z_BACK + 4.3, 6.0))
        adds.append(zcyl(hx, hy, P.Z_BACK + 4.2, P.PCB_REAR, 4.2))
        adds += board_pin(hx, hy)
    # the bottom pair, in the chin's corners (params.CORNER_SCREWS): a post from the floor to the parting plane,
    # D-shaped into the bottom wall, under the tub's corner block
    for sx, sy in P.CORNER_SCREWS:
        cb_top = P.Z_BACK + P.M2_CB_DEPTH['corner']
        r = P.CORNER_POST_D / 2
        adds.append(zcyl(sx, sy, P.LID_FLOOR_IN - 0.1, P.SEAM, P.CORNER_POST_D)
                    .union(box(sx - r, sx + r, P.BOT_IN - 0.01, sy, P.LID_FLOOR_IN - 0.1, P.SEAM)))
        cuts += screw_cuts(sx, sy, cb_top, P.M2_CB_SLOT['corner'])
    tx, ty = P.TOP_SCREW
    cb_top = P.Z_BACK + P.M2_CB_DEPTH['top']
    adds.append(zcyl(tx, ty, P.LID_FLOOR_IN - 0.1, P.SEAM, 5.0))
    adds.append(box(tx, LOW_X1 + 0.5, ty - 2.5, ty + 2.5, P.LID_FLOOR_IN - 0.1, P.SEAM))
    # the boss's wall round the counterbore is 0.4 on its -X side, too thin for the slicer to print: up through the
    # bridge layers that side is a 6.0 round, as H3/H4's base, so the counterbore's ceiling has a wall to stand on
    adds.append(zcyl(tx, ty, P.LID_FLOOR_IN - 0.1, cb_top + 2 * P.LAYER, 6.0)
                .intersect(box(tx - 4, tx, ty - 4, ty + 4, P.LID_FLOOR_IN - 1, cb_top + 1)))
    cuts += screw_cuts(tx, ty, cb_top, P.M2_CB_SLOT['top'])
    # the top-left screw (params.TOP_LEFT_SCREW, 2026-10-13), built as the top one: a 5.0 post to the parting plane in
    # the corner (the body trims it), the 6.0 round all round it up through the bridge layers (its 0.4 wall round the
    # counterbore is too thin to print on every side), its seat. The tongues' ends stand clear of both (TONGUE_RUNS)
    lx, ly = P.TOP_LEFT_SCREW
    adds.append(zcyl(lx, ly, P.LID_FLOOR_IN - 0.1, P.SEAM, 5.0))
    adds.append(zcyl(lx, ly, P.LID_FLOOR_IN - 0.1, cb_top + 2 * P.LAYER, 6.0))
    cuts += screw_cuts(lx, ly, cb_top, P.M2_CB_SLOT['top'])

    # PCB support posts. H2 and H6 take the midplate's snap posts through the board, so they carry only a
    # clearance bore for the barb; H5 keeps its pin, which registers the board's top end in X and Y.
    for ref in P.BOARD_POST_D:
        hx, hy = fps[ref]['cad']
        adds.append(zcyl(hx, hy, P.LID_FLOOR_IN - 0.1, P.PCB_REAR, P.BOARD_POST_D[ref]))
        if ref in P.SNAP_POSTS:
            bd, bz = P.BOARD_SNAP_BORE
            cuts.append(zcyl(hx, hy, bz, P.PCB_REAR + 0.01, bd))
        else:
            adds += board_pin(hx, hy)

    # USB: solid block under the receptacle, a mm wider than the recess each side; the recess's lower part is
    # cut into it (the tub has the rest), and a block rises from it into the tub floor's notch to close the
    # port hole's lower edge
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

    # the board's top-left, where H2's post was, is carried by a post in SW5's empty site
    for x, y, d in P.SUPPORT_POSTS:
        adds.append(zcyl(x, y, P.LID_FLOOR_IN - 0.1, P.PCB_REAR, d))
    # the battery bay and the backstops
    ba, bc, _ = bay()
    adds += ba
    adds += backstops()
    adds += ribs()

    # joint: the rim's outer leg, the inner lip that closes the groove, and the latch arms
    import joint
    adds += joint.lid_adds()

    for a in adds:
        lid = lid.union(a)
    for c in cuts + bc:
        lid = lid.cut(c)
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
    if P.LOGO_BACK:
        import logo
        lid = lid.cut(logo.solid(P.Z_BACK - 0.2, P.Z_BACK + P.LOGO_BACK['depth'], P.LOGO_BACK))
    if P.LOGO_BACK_WORDMARK:                         # the wordmark above the grip grooves (2026-10-23: it was in the chin)
        import logo
        lid = lid.cut(logo.solid(P.Z_BACK - 0.2, P.Z_BACK + P.LOGO_BACK_WORDMARK['depth'], P.LOGO_BACK_WORDMARK))
    lid = lid.intersect(body)
    # the side keys: out comes each one's footprint, its void and its free-end slot; in goes the key, which
    # stands on the back face and is fused to the wall at its root
    for t in side_tabs():
        lid = lid.cut(sidekeys.lid_cut(t))
    if keys:
        for t in side_tabs():
            lid = lid.union(sidekeys.build(t['ref']))
    return lid.clean()


if __name__ == '__main__':
    import time
    t0 = time.time()
    print('bay', bay()[2])
    lid = build()
    print('lid solids', len(lid.solids().vals()), 'vol', round(lid.val().Volume(), 1), f'{time.time() - t0:.1f}s')
    cq.exporters.export(lid, str(hw.OUT / 'lid.stl'), tolerance=0.03, angularTolerance=0.15)
