"""Midplate: a flat 1 mm printed plate between the screen and the PCB.

  - backs the whole glass so touches and the battery never load it through a point
  - clicks into the tub (Rev K): four detent strips at its edges snap into pockets in the tub's
    walls, so the display, the midplate and the PCBA can go in as one stack and stay there
  - separates the battery from the glass
  - carries bridge springs whose nubs rest on the PCB front face and hold the screen
    against the bezel lip, taking up the panel's +-0.2 mm thickness tolerance
    (no foam, no tape)
It is cut away around every through-hole lead that stands proud of the PCB front.
Printed screen side down; the springs are short bridges, so no supports are needed.
"""
import math
import cadquery as cq
import hw
import params as P
from geom import box, rbox, zcyl, xz_prism, yz_prism
from body import usb

EDGE_CLR = 0.2
Y_BOTTOM = 7.6                   # stays above the PCB's FPC slot (5.65..7.15) so the tails pass freely
SPRING_L, SPRING_W, SPRING_T = 14.0, 3.0, 0.4
SPRING_SLOT = 0.5
NUB_D, NUB_H = 2.2, 0.75         # nub reaches 0.35 past the PCB front face at the nominal stack, which
                                 # centres the 0..0.6 take-up window over the panel's +-0.2 thickness
LEAD_CLR = 0.5

# Spring centres. They press the board back onto the lid's posts, so Rev G adds one on each side
# near the side buttons (y 61.5 and 93.5 are the two that had no support near them) - the plunger
# sitting where the nub expects it is what makes a side button land squarely.
SPRINGS = [(8.0, 11.5, 'x'), (52.0, 11.5, 'x'), (52.5, 70.0, 'y'), (53.0, 102.0, 'x'), (14.0, 70.0, 'y'),
           (12.0, 61.5, 'y'), (52.5, 88.0, 'y')]


def tht_pads():
    """Every drilled pad on the board: (x, y, radius) in the CAD frame."""
    out = []
    for f in hw.footprints().values():
        if f['dnp']:
            continue
        fx, fy = f['cad']
        rot = math.radians(f['rot'])
        back = f['layer'] == 'B.Cu'
        for p in f['pads']:
            if not p['drill'] or f['ref'].startswith('H'):
                continue
            try:
                if float(p['drill'][0]) < 0.6:      # thermal vias inside pads: nothing stands proud
                    continue
            except ValueError:
                pass
            lx, ly = p['local']
            # KiCad local coords: y down; footprint rotation is CCW in KiCad's y-down frame.
            kx = lx * math.cos(rot) + ly * math.sin(rot)
            ky = -lx * math.sin(rot) + ly * math.cos(rot)
            if back:
                pass  # pad positions are already in board coordinates after rotation
            x, y = fx + kx, fy - ky
            r = max(p['size'] or [1.0]) / 2
            out.append((x, y, r))
    return out


def outline():
    x0 = P.POCKET_X0 + EDGE_CLR
    x1 = P.POCKET_X1 - EDGE_CLR
    y1 = P.POCKET_Y1 - EDGE_CLR
    plate = rbox(x0, x1, Y_BOTTOM, y1, P.MID_REAR, P.DISP_REAR, 0.8)
    u = usb()
    # the wall above the USB port is kept solid higher up (tub.usb_features' block); step the plate edge in there
    ow = P.OVERMOLD[0] + 2 * P.OVERMOLD_CLR
    plate = plate.cut(box(60.35, x1 + 1, u['yc'] - ow / 2 - 1.0, u['yc'] + ow / 2 + 1.0, P.MID_REAR - 1, P.DISP_REAR + 1))
    return plate


def spring(cx, cy, axis):
    """Window through the plate with a bridge strip across it and a nub on the PCB side."""
    L, W = SPRING_L, SPRING_W
    wx, wy = (L, W + 2 * SPRING_SLOT) if axis == 'x' else (W + 2 * SPRING_SLOT, L)
    window = box(cx - wx / 2, cx + wx / 2, cy - wy / 2, cy + wy / 2, P.MID_REAR - 1, P.DISP_REAR + 1)
    sx, sy = (L + 1.0, W) if axis == 'x' else (W, L + 1.0)      # ends overlap the plate 0.5 mm
    strip = box(cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, P.MID_REAR, P.MID_REAR + SPRING_T)
    nub = zcyl(cx, cy, P.MID_REAR - NUB_H, P.MID_REAR + 0.01, NUB_D)
    return window, strip.union(nub)


def battery_bay():
    """Battery slot on the plate's back face (the tub's top wall closes the top once it is in).

    left rail   continuous, from the bottom stop to the plate's top edge, with a LIP that turns in
                over the cell's back edge (Rev I)
    right rail  posts, so the lead can leave between them (between the two snaps). The two
                plain ones are SNAPS (Rev I): each ends in a 45-degree barb over the cell's back edge
                and is thin enough to flex out of its way
    stop        across the bottom, only BAY['stop_h'] tall: the microSD card's path runs behind it
    cleats      two right posts carried past the cell's back and capped along Y, for spare lead

    Every lip's and barb's underside is 45 degrees, so the plate still prints screen side down with
    no supports, and the left rail flares at the top end, so the cell can also slide in from the
    plate's top edge. Returns (solids, info)."""
    f, B = P.FENCE, P.BAY
    bx0, bx1 = P.BATT['x']
    by0, by1 = P.BATT['y']
    zb = P.BATT['z'][0]                                          # the cell's back face
    base = P.MID_REAR + 0.01
    y_top = P.POCKET_Y1 - EDGE_CLR                               # the plate's top edge
    y_stop = (by0 - f['clr'] - 0.6, by0 - f['clr'])              # 0.6 thick: keeps 0.39 to the board's notch edge
    lx = (bx0 - f['clr'] - f['t'], bx0 - f['clr'])
    rx = (bx1 + f['clr'], bx1 + f['clr'] + f['t'])
    # A lip's 45-degree underside leaves the rail's face at z_a, which puts it lip_z clear of the
    # cell's back right at the cell's edge (f['clr'] in from the rail).
    z_a = zb - B['lip_z'] + f['clr']
    ov_l = f['clr'] + B['lip_over']
    z_rail = z_a - ov_l - B['lip_t']                             # left rail's end, below the lip's tip
    ov_s = f['clr'] + B['snap_over']
    z_snap = z_a - 2 * ov_s                                      # snap post's end, below its lead-in

    def flare_cut(p, e, inward, y1, z0):
        """Plan chamfer on the rail's inner face (and its lip) at the plate's top edge."""
        fl, reach = B['flare'], ov_l + 0.3
        tri = (cq.Workplane('XY').polyline([(e + inward * reach, y1 - fl), (e + inward * reach, y1 + 0.01),
                                            (e - inward * min(fl, f['t'] - 0.3), y1 + 0.01), (e, y1 - fl)]).close()
               .extrude(base - z0 + 2).translate((0, 0, z0 - 1)))
        return p.cut(tri)

    def post(x0, x1, y0, y1, z_top, inward):
        """A rail along Y whose inner face is at x1 (inward=+1) or x0 (inward=-1), with a 45-degree
        lead-in on its inner end edge."""
        p = box(x0, x1, y0, y1, z_top, base)
        e = x1 if inward > 0 else x0
        li = f['lead_in']
        return p.cut(xz_prism([(e, z_top - 0.01), (e - inward * (li + 0.01), z_top - 0.01), (e + inward * 0.01, z_top + li)],
                              y0 - 1, y1 + 1))

    # left rail with its lip
    e = lx[1]
    left = box(lx[0], lx[1], y_stop[0], y_top, z_rail, base)
    left = left.union(xz_prism([(e - 0.01, z_a), (e + ov_l, z_a - ov_l), (e + ov_l, z_rail), (e - 0.01, z_rail)],
                               y_stop[1], y_top))
    out = [flare_cut(left, e, +1, y_top, z_rail)]
    # right posts: the snaps, and the two that carry the cleats (plain, at Rev H's height)
    e = rx[0]
    c_lo, c_hi = B['cleats']
    posts = [(c_lo - f['len'] / 2, c_lo + f['len'] / 2), *B['snaps'], (c_hi - f['len'] / 2, y_top)]
    for y0c, y1c in posts:                               # the lead leaves between the two snaps
        if (y0c, y1c) in B['snaps']:
            p = box(rx[0], rx[1], y0c, y1c, z_snap, base)
            p = p.union(xz_prism([(e + 0.01, z_a), (e - ov_s, z_a - ov_s), (e + 0.01, z_a - 2 * ov_s)], y0c, y1c))
            out.append(p)
        else:
            out.append(post(*rx, y0c, y1c, f['z1'], -1))
    # bottom stop: low, from the left rail to 0.3 short of the board notch's bottom-right corner arc
    # (R4.43, centre 35.75/85.0), which reaches in to x 37.92 at the stop's lower edge
    x_stop1 = 37.62
    stop = box(lx[0], x_stop1, y_stop[0], y_stop[1], P.MID_REAR - B['stop_h'], base)
    li = f['lead_in']
    stop = stop.cut(yz_prism([(y_stop[1], P.MID_REAR - B['stop_h'] - 0.01), (y_stop[1] - li - 0.01, P.MID_REAR - B['stop_h'] - 0.01),
                              (y_stop[1] + 0.01, P.MID_REAR - B['stop_h'] + li)], lx[0] - 1, x_stop1 + 1))
    out.append(stop)
    # cleats: the first and last right posts, thickened outward and carried past the cell's back
    cleats = []
    for cy in B['cleats']:
        c0, c1 = cy - f['len'] / 2, cy + f['len'] / 2
        x0, x1 = rx[0], rx[0] + B['cleat_t']
        pst = box(x0, x1, c0, c1, B['cleat_top'], base)
        # cap: the top B['cap_h'] reaches B['cap'] further along Y each way, with a 45-degree
        # underside (it faces the bed: the plate prints screen side down)
        cz0, cz1 = B['cleat_top'], B['cleat_top'] + B['cap_h']
        cap = yz_prism([(c0 - B['cap'], cz0), (c1 + B['cap'], cz0), (c1 + B['cap'], cz1), (c1, cz1 + B['cap']),
                        (c0, cz1 + B['cap']), (c0 - B['cap'], cz1)], x0, x1)
        cleats.append(pst.union(cap))
    out += cleats
    info = {'left_rail': [round(v, 2) for v in (*lx, y_stop[0], y_top)], 'right_posts': [round(v, 2) for v in rx],
            'stop_y': [round(v, 2) for v in y_stop], 'stop_x': [round(lx[0], 2), round(x_stop1, 2)], 'stop_z': [P.MID_REAR - B['stop_h'], P.MID_REAR],
            'rail_z': [round(z_rail, 3), P.MID_REAR], 'cleats_y': list(B['cleats']),
            'cleat_x': [round(rx[0], 2), round(rx[0] + B['cleat_t'], 2)], 'cleat_z': [B['cleat_top'], P.MID_REAR],
            'lip': {'x': [round(lx[1], 3), round(lx[1] + ov_l, 3)], 'z_face': round(z_a, 3), 'z_tip': round(z_a - ov_l, 3),
                    'over_cell': B['lip_over'], 'clear_of_back': B['lip_z']},
            'snaps': {'y': [list(s) for s in B['snaps']], 'x': [round(rx[0] - ov_s, 3), round(rx[0], 3)],
                      'z': [round(z_snap, 3), round(z_a, 3)], 'tip_z': round(z_a - ov_s, 3), 'over_cell': B['snap_over']},
            'cell_back_z': zb, 'plate_top_y': round(y_top, 3)}
    return out, info


def fence_posts():
    """Kept for callers of the Rev G name: the Rev H battery bay's solids."""
    return battery_bay()[0]


def snap_posts():
    """A post through each of the board's H1/H2 holes with a two-finger barb that catches the
    rear face, so the PCBA clips onto the midplate before the lid goes on.

    It captures rather than clamps: the barb's retaining face sits BOARD_SNAP['catch'] just under
    the board's rear face, so with the lid on the board still rests on the lid's posts and the
    barbs go slack. Nothing here fights the panel's thickness tolerance.

    The midplate prints screen side down, so these posts stand up off the bed and the barb's
    retaining face is the overhang: it is 45 degrees, which is why the board comes off again with
    a firm pull instead of never.
    """
    B = P.BOARD_SNAP
    rise = (B['crest'] - B['d']) / 2
    z_crest = B['catch'] - rise / math.tan(math.radians(B['face_deg']))       # widest point of the barb
    z_lead = z_crest - rise / math.tan(math.radians(B['lead_deg']))           # bottom of the lead-in cone
    assert z_lead > B['tip'] + 0.02, (z_lead, B['tip'])
    fps = hw.footprints()
    out = []
    for ref in P.SNAP_POSTS:
        cx, cy = fps[ref]['cad']
        p = zcyl(cx, cy, B['tip'], P.DISP_REAR, B['d'])      # through the plate: the finger roots at
                                                             # its front face, so it is 3.95 mm long
        p = p.union(cq.Workplane('XY', origin=(cx, cy, z_lead))               # lead-in cone
                    .circle(B['d'] / 2).workplane(offset=z_crest - z_lead).circle(B['crest'] / 2).loft())
        p = p.union(cq.Workplane('XY', origin=(cx, cy, z_crest))              # 45-degree retaining face
                    .circle(B['crest'] / 2).workplane(offset=B['catch'] - z_crest).circle(B['d'] / 2).loft())
        # one slot through post and plate, so the two halves can squeeze together on the way in
        r = B['crest'] / 2 + 0.1
        p = p.cut(box(cx - r, cx + r, cy - B['slot'] / 2, cy + B['slot'] / 2, B['tip'] - 0.1, P.DISP_REAR + 0.01))
        out.append(p)
    return out


def detents():
    """Rev K: the plate's four click-in strips (params.MID_DETENT). Each is the plate's edge, cut free
    by a slot behind it and across its tip, so it bends in the plate's plane; near its tip a bump stands
    `bump` past the edge, with a 45-degree lead on its front (bed-side) edge. Returns (cuts, adds, rows)."""
    D = P.MID_DETENT
    x0, x1 = P.POCKET_X0 + EDGE_CLR, P.POCKET_X1 - EDGE_CLR
    z0, z1 = P.MID_REAR - 1, P.DISP_REAR + 1
    cuts, adds, rows = [], [], []
    for wall, roots in D['spans'].items():
        s = 1 if wall == 'right' else -1
        xe = x1 if s > 0 else x0                                   # the plate's edge
        for ya in roots:
            yb = ya + D['len']
            xs = sorted((xe - s * D['w'], xe - s * (D['w'] + D['slot'])))
            cuts.append(box(xs[0], xs[1], ya, yb + D['tip_slot'], z0, z1))          # behind the strip
            xt = sorted((xe - s * (D['w'] + D['slot']), xe + s * 1.0))
            cuts.append(box(xt[0], xt[1], yb, yb + D['tip_slot'], z0, z1))          # across its tip
            b, L, ld = D['bump'], D['bump_len'], D['lead']
            yc = yb - L / 2 - 0.3
            plan = [(xe - s * 0.05, yc - L / 2), (xe + s * b, yc - L / 2 + b), (xe + s * b, yc + L / 2 - b), (xe - s * 0.05, yc + L / 2)]
            bump = cq.Workplane('XY').polyline(plan).close().extrude(P.MID_T).translate((0, 0, P.MID_REAR))
            lead = xz_prism([(xe + s * (b - ld), P.DISP_REAR + 0.01), (xe + s * (b + 0.01), P.DISP_REAR + 0.01),
                             (xe + s * (b + 0.01), P.DISP_REAR - ld - 0.01)], yc - L, yc + L)
            adds.append(bump.cut(lead))
            rows.append({'wall': wall, 'strip_y': [round(ya, 2), round(yb, 2)], 'bump_y': [round(yc - L / 2, 2), round(yc + L / 2, 2)],
                         'bump_x': round(xe + s * b, 3), 'edge_x': round(xe, 3), 'arm': round(yc - ya, 2)})
    return cuts, adds, rows


def spring_windows():
    """(x0, x1, y0, y1) of each spring's window through the plate (spring())."""
    out = []
    for cx, cy, axis in SPRINGS:
        wx, wy = (SPRING_L, SPRING_W + 2 * SPRING_SLOT) if axis == 'x' else (SPRING_W + 2 * SPRING_SLOT, SPRING_L)
        out.append((cx - wx / 2, cx + wx / 2, cy - wy / 2, cy + wy / 2))
    return out


# The plate left between a latch notch and an opening behind it. OrcaSlicer's classic walls (the stock CC2 process)
# drop a strip narrower than one line (0.42): read back, a 0.36 or 0.41 web printed in none of the plate's three lower
# layers. Where a notch would leave less, it runs on into the opening instead (2026-10-12).
MIN_WEB = 0.5
# A notch that ends less than MIN_WEB short of a detent strip's root on its wall (both Y-12 notches, 0.35 short of the
# Y-14.9 strips; left Y 83 and right Y 82.3, 0.45 short of theirs) is held at the strip's width (MID_DETENT w, 0.7,
# flush with the strip's inner edge, as every notch was before) over its last DETENT_HOLD. At the full 0.85 it left a
# 0.15 x 0.35 neck at the Y-14.9 strips' roots, and OrcaSlicer printed both strips as loops of their own, 0.155 from
# the plate's, in every layer (2026-10-12). Held, their lines touch the plate's (0.006) in layers 2-5 as on main
# (slice_check.latch_readback). The arm ends 0.3 short of its notch's end, so the step stands EDGE_CLR (the plate's
# play) past it and the arm meets only the 0.85 (lid_close's case with the plate shifted along the wall).
DETENT_HOLD = 0.1


def detent_holds(wall, y0, y1):
    """[(h0, h1, strip root y)]: the end of the notch (wall, y0, y1) held at MID_DETENT w (DETENT_HOLD above)."""
    return [(y1 - DETENT_HOLD, y1, ya) for ya in P.MID_DETENT['spans'].get(wall, []) if 0.0 <= ya - y1 < MIN_WEB]


def latch_notches():
    """The plate's edge steps back SNAP['notch'] where each latch arm's tip, which stands above the
    plate's rear face since Rev I, passes it. 0.85 since 2026-10-12 (was 0.7): the arms, bent inward by the tub's
    tongue on the way in, landed on the plate (params.SNAP, lid_close.py). Where a spring's window stands less than
    MIN_WEB behind a notch (the Y-102 spring's, 0.36 behind the right Y-100.3 notch), the notch runs on into the
    window over their common span. build() cuts the notches again after the adds, so no spring strip stands in one.
    Where a notch ends near a detent strip, its last DETENT_HOLD is held at the strip's width (detent_holds)."""
    import joint
    n = P.SNAP['notch']
    nh = min(n, P.MID_DETENT['w'])
    x0, x1 = P.POCKET_X0 + EDGE_CLR, P.POCKET_X1 - EDGE_CLR
    z0, z1 = P.MID_REAR - 1, P.DISP_REAR + 1
    out = []
    for wall, y0, y1 in joint.midplate_notches():
        xs = (x1 - n, x1 + 1) if wall == 'right' else (x0 - 1, x0 + n)
        yb = y1
        for h0, h1, _ in detent_holds(wall, y0, y1):
            yb = h0
            xh = (x1 - nh, x1 + 1) if wall == 'right' else (x0 - 1, x0 + nh)
            out.append(box(xh[0], xh[1], h0, h1, z0, z1))
        out.append(box(xs[0], xs[1], y0, yb, z0, z1))
        for wx0, wx1, wy0, wy1 in spring_windows():
            a, b = max(y0, wy0), min(y1, wy1)
            web = (x1 - n) - wx1 if wall == 'right' else wx0 - (x0 + n)
            if b > a and 0.0 <= web < MIN_WEB:
                xr = (wx1 - 0.1, x1 + 1) if wall == 'right' else (x0 - 1, wx0 + 0.1)
                out.append(box(xr[0], xr[1], a, b, z0, z1))
    return out


def build():
    plate = outline()
    dc, da, _ = detents()
    for c in latch_notches() + dc:
        plate = plate.cut(c)
    adds = list(da)
    for cx, cy, ax in SPRINGS:
        w, s = spring(cx, cy, ax)
        plate = plate.cut(w)
        adds.append(s)
    adds += battery_bay()[0]
    adds += snap_posts()
    for s in adds:
        plate = plate.union(s)
    for c in latch_notches():                   # again: the Y-102 spring's strip ran on into its notch (2026-10-12)
        plate = plate.cut(c)
    for x, y, r in tht_pads():
        if P.POCKET_X0 < x < P.POCKET_X1 and Y_BOTTOM - 2 < y < P.POCKET_Y1:
            plate = plate.cut(zcyl(x, y, P.MID_REAR - 1, P.DISP_REAR + 1, 2 * (r + LEAD_CLR)))
    return plate.clean()


if __name__ == '__main__':
    m = build()
    print('midplate solids', len(m.solids().vals()), 'vol', round(m.val().Volume(), 1))
    cq.exporters.export(m, str(P.OUT / 'midplate.stl'), tolerance=0.03, angularTolerance=0.15)
