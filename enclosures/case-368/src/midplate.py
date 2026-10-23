"""Midplate: a flat 0.8 mm printed plate between the screen and the PCB (Rev D-K, x3).

  - backs the whole glass so touches never load it through a point
  - carries bridge springs whose nubs rest on the PCB's front face and hold the screen against the bezel
    lip, taking up the panel's +-0.1 mm thickness tolerance (no foam, no tape)
  - carries the snap posts the board clips onto (H2, H6), so the PCBA "slots in and stays"
  - clicks into the tub (Rev K): detent strips at its edges snap into pockets in the tub's walls, so the
    display, the midplate and the PCBA can go in as one stack and stay there
It is cut away round every through-hole lead that stands proud of the PCB's front. Above the board's
edge (the trimmed top) nothing is behind it but the lid, whose ribs back it there (lid.backstops).
x3: the battery no longer rides on it - it is in the lid, behind the board.
Printed screen side down; the springs are short bridges, so no supports are needed.
For the light strip: a notch in its left edge under the strip's folded pair (fold_relief), and the left upper
detent strip moved down to 58.0 (params.MID_DETENT) out of the relief. Notches under the light-strip tub's two left
corner stops (stop_notches), which reach down past the plate's front face.
The plate is shared by both builds (Ian: only the tub differs), so the standard build has these too: there the
notches only leave the glass's left edge unbacked out to X 1.3 over their Y spans, and the standard tub's left upper
detent pocket moves to 58.0 with the strip.
Its top-left corner is notched round the top-left screw's boss (2026-10-13, top_left_notch), as its top-right one is
round the top screw's.
"""
import math
import cadquery as cq
import hw
import params as P
from geom import box, rbox, zcyl, xz_prism, yz_prism
from body import usb

EDGE_CLR = 0.2
Y_BOTTOM = 7.3                   # 0.5 above the chin's web (tub.CHIN_WEB, which stops at the pocket, 6.80) and
                                 # 0.85 above the FPC's drop through the slot (6.35..6.45)
SPRING_L, SPRING_W, SPRING_T = 12.0, 3.0, 0.4
SPRING_SLOT = 0.5
NUB_D, NUB_H = 2.2, 0.4          # nub reaches 0.2 past the PCB's front at the nominal stack, so the strip deflects
                                 # 0.1 .. 0.3 over the panel's +-0.1, inside its 0.4 window (MID_T - SPRING_T)
LEAD_CLR = 0.5
# Spring centres: over the board, clear of every through-hole pad, spread over the panel so the glass is
# pressed evenly; the two by the side keys (SW1 / SW4 / SW7 at Y 61.5 and 75.5) also press the board onto the
# lid's posts right where a side key pushes on it.
SPRINGS = [(8.5, 11.5, 'x'), (50.5, 11.5, 'x'), (13.0, 42.0, 'y'), (46.5, 52.0, 'y'), (11.5, 66.0, 'y'),
           (50.0, 66.5, 'y'), (31.5, 77.0, 'x')]


def tht_pads():
    """Every drilled pad on the board: (x, y, radius) in the CAD frame."""
    out = []
    for f in hw.footprints().values():
        if f['dnp']:
            continue
        fx, fy = f['cad']
        rot = math.radians(f['rot'])
        for p in f['pads']:
            if not p['drill'] or f['ref'].startswith('H'):
                continue
            try:
                if float(p['drill'][0]) < 0.6:      # thermal vias inside pads: nothing stands proud
                    continue
            except ValueError:
                pass
            lx, ly = p['local']
            kx = lx * math.cos(rot) + ly * math.sin(rot)
            ky = -lx * math.sin(rot) + ly * math.cos(rot)
            x, y = fx + kx, fy - ky
            r = max(p['size'] or [1.0]) / 2
            out.append((x, y, r))
    return out


def edges():
    return P.WALL_X0 + EDGE_CLR, P.WALL_X1 - EDGE_CLR, Y_BOTTOM, P.TOP_IN - EDGE_CLR    # the top edge is no longer backed by the rib (a fence now): the tub's frame covers it


CORNER_R = 1.8                   # the tub's cavity has R1.5 plan corners; the plate's stay clear of them


def outline(z0=P.MID_REAR, z1=P.DISP_REAR):
    """The plate's plan outline, extruded z0..z1 (the insertion check sweeps it from the back)."""
    x0, x1, y0, y1 = edges()
    plate = rbox(x0, x1, y0, y1, z0, z1, CORNER_R)
    u = usb()
    # the wall above the USB port is kept solid further in (tub.usb_features' floor); step the edge in there
    ow = P.OVERMOLD[0] + 2 * P.OVERMOLD_CLR
    plate = plate.cut(box(60.35, x1 + 1, u['yc'] - ow / 2 - 1.0, u['yc'] + ow / 2 + 1.0, z0 - 1, z1 + 1))
    # the top screw's boss, which stands in the tub's top-right corner
    tx, ty = P.TOP_SCREW
    r = P.TOP_BOSS_D / 2 + 0.3
    plate = plate.cut(box(tx - r, x1 + 1, ty - r, y1 + 1, z0 - 1, z1 + 1))
    plate = plate.cut(top_left_notch(z0 - 1, z1 + 1))        # and the top-left screw's (2026-10-13)
    for n in stop_notches(z0 - 1, z1 + 1):                   # light strip: part of the outline (the insertion path)
        plate = plate.cut(n)
    return plate


def top_left_notch(z0, z1, clr=0.3):
    """The plate's top-left corner, clr clear of the top-left screw's boss (tub.top_left_boss: its round merged into the
    left and top walls, flat on the panel's pocket at its largest), z0..z1: round the boss's round, back to X 2.1 at
    most, and clr into the largest panel's pocket where the boss is flat on it. Most of it lies beside the glass or
    under the light strip's corner stop notch (stop_notches, X <= 1.3 to Y 93.74), which both builds have; over the
    largest panel's top border it takes 0.15 of backing at most, over a nominal one's 0.05."""
    x, y = P.TOP_LEFT_SCREW
    r = P.TOP_BOSS_D / 2
    x0, _, _, y1 = edges()
    n = zcyl(x, y, z0, z1, P.TOP_BOSS_D + 2 * clr)
    n = n.union(box(x0 - 1, x + r + clr, y - clr, y1 + 1, z0, z1)).union(box(x0 - 1, x + clr, y - r - clr, y1 + 1, z0, z1))
    return n.cut(box(P.POCKET_X0 + clr, P.POCKET_X1, P.POCKET_Y0, P.POCKET_Y1 - clr, z0 - 1, z1 + 1))


def stop_notches(z0, z1):
    """Light strip: the tub's two left corner stops reach down to LOCATOR_Z0, past the plate's front face (2.5..2.7
    over the panel's +-0.1), so the plate is notched right through under them, from its left edge to
    MID_STOP_NOTCH['x1'] and MID_STOP_NOTCH['clr'] past each stop's ends in Y. The bottom one ends where the first
    left latch notch starts (9.45); the top one carries the fold relief on to 93.74. No spring, detent or post is near."""
    x0, _, y0, _ = edges()
    N = P.MID_STOP_NOTCH
    return [box(x0 - 1, N['x1'], y0 - 1, P.LOCATOR_Y[1] + N['clr'], z0, z1),
            box(x0 - 1, N['x1'], P.LOCATOR_Y_TOP[0] - 0.01, P.LOCATOR_Y_TOP[1] + N['clr'], z0, z1)]


def spring(cx, cy, axis):
    """Window through the plate with a bridge strip across it and a nub on the PCB side."""
    L, W = SPRING_L, SPRING_W
    wx, wy = (L, W + 2 * SPRING_SLOT) if axis == 'x' else (W + 2 * SPRING_SLOT, L)
    window = box(cx - wx / 2, cx + wx / 2, cy - wy / 2, cy + wy / 2, P.MID_REAR - 1, P.DISP_REAR + 1)
    sx, sy = (L + 1.0, W) if axis == 'x' else (W, L + 1.0)      # ends overlap the plate 0.5 mm
    strip = box(cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, P.MID_REAR, P.MID_REAR + SPRING_T)
    nub = zcyl(cx, cy, P.MID_REAR - NUB_H, P.MID_REAR + 0.01, NUB_D)
    return window, strip.union(nub)


def snap_posts():
    """The midplate's posts through the board's holes (params.SNAP_POSTS, style params.BOARD_SNAP['style']).

    'pole' (since 2026-10-23): a plain pin, d BOARD_SNAP['d'], from the tip (BOARD_SNAP['tip'], under the board's rear
    face) up through the plate, its tip edge rounded. It locates the board in X and Y; nothing holds it in Z until the
    lid is on, and with the lid on the lid's posts set Z as before.

    'barb' (Rev G-K): a two-finger snap with a barb that catches the rear face, so the PCBA clips onto the midplate
    before the lid goes on. It captures rather than clamps: the retaining face sits BOARD_SNAP['catch'] just under the
    board's rear face, so with the lid on the board still rests on the lid's posts and the barbs go slack. The midplate
    prints screen side down, so the retaining face is the overhang: 45 degrees, which is why the board comes off again
    with a firm pull.
    """
    B = P.BOARD_SNAP
    pole = B.get('style', 'barb') == 'pole'
    if not pole:
        rise = (B['crest'] - B['d']) / 2
        z_crest = B['catch'] - rise / math.tan(math.radians(B['face_deg']))       # widest point of the barb
        z_lead = z_crest - rise / math.tan(math.radians(B['lead_deg']))           # bottom of the lead-in cone
        assert z_lead > B['tip'] + 0.02, (z_lead, B['tip'])
    fps = hw.footprints()
    out = []
    for ref in P.SNAP_POSTS:
        cx, cy = fps[ref]['cad']
        p = zcyl(cx, cy, B['tip'], P.DISP_REAR, B['d'])
        if pole:                                             # fillet the tip's edge (-Z end)
            p = p.faces('<Z').edges().fillet(B['tip_r'])
        else:
            p = p.union(cq.Workplane('XY', origin=(cx, cy, z_lead))
                        .circle(B['d'] / 2).workplane(offset=z_crest - z_lead).circle(B['crest'] / 2).loft())
            p = p.union(cq.Workplane('XY', origin=(cx, cy, z_crest))
                        .circle(B['crest'] / 2).workplane(offset=B['catch'] - z_crest).circle(B['d'] / 2).loft())
            r = B['crest'] / 2 + 0.1
            p = p.cut(box(cx - r, cx + r, cy - B['slot'] / 2, cy + B['slot'] / 2, B['tip'] - 0.1, P.DISP_REAR + 0.01))
        out.append(p)
    return out


def detents():
    """Rev K: the plate's click-in strips (params.MID_DETENT). Each is the plate's edge, cut free by a slot
    behind it and across its tip, so it bends in the plate's plane; near its tip a bump stands `bump` past
    the edge, with a 45-degree lead on its front (bed-side) edge. Returns (cuts, adds, rows)."""
    D = P.MID_DETENT
    x0, x1, _, _ = edges()
    z0, z1 = P.MID_REAR - 1, P.DISP_REAR + 1
    cuts, adds, rows = [], [], []
    for wall, roots in D['spans'].items():
        s = 1 if wall == 'right' else -1
        xe = x1 if s > 0 else x0
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


def latch_notches():
    """The plate's edge steps back SNAP['notch'] where each latch arm's tip, which stands above the plate's
    rear face, passes it (side walls and, x3, the top wall)."""
    import joint
    n = P.SNAP['notch']
    x0, x1, _, y1 = edges()
    out = []
    for wall, a0, a1 in joint.midplate_notches():
        if wall == 'top':
            out.append(box(a0, a1, y1 - n, y1 + 1, P.MID_REAR - 1, P.DISP_REAR + 1))
            continue
        xs = (x1 - n, x1 + 1) if wall == 'right' else (x0 - 1, x0 + n)
        out.append(box(xs[0], xs[1], a0, a1, P.MID_REAR - 1, P.DISP_REAR + 1))
    return out


def fold_relief():
    """Light strip: the folded top pair hangs below the bar with its LEDs facing the plate (down to Z 2.285) and its
    loop down to 2.375; the plate is notched right through under them, from its left edge to MID_RELIEF['x1'] (the
    glass's edge is at 1.1..1.227), over the fold zone. No spring or post is there, and the latch notch at
    80.45..85.55 already goes through. Where a lead hole's clearance (tht_pads + LEAD_CLR) comes within
    MID_RELIEF['web_min'] of the notch's edge (SW7's two front leads), the notch runs on into the hole over the hole's
    height, to its centre, so no web narrower than one printed line is left between them."""
    x0, _, _, _ = edges()
    R = P.MID_RELIEF
    y0, y1 = P.FOLD_ZONE
    out = box(x0 - 1, R['x1'], y0, y1, R['floor'], P.DISP_REAR + 1)
    for x, y, r in tht_pads():
        rc = r + LEAD_CLR
        if x - rc < R['x1'] + R['web_min'] and y + rc > y0 and y - rc < y1:
            out = out.union(box(R['x1'] - 0.1, x, max(y0, y - rc), min(y1, y + rc), R['floor'], P.DISP_REAR + 1))
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
    adds += snap_posts()
    for s in adds:
        plate = plate.union(s)
    x0, x1, y0, y1 = edges()
    for x, y, r in tht_pads():
        if x0 - 2 < x < x1 + 2 and y0 - 2 < y < y1:
            plate = plate.cut(zcyl(x, y, P.MID_REAR - 1, P.DISP_REAR + 1, 2 * (r + LEAD_CLR)))
    plate = plate.cut(fold_relief())
    return plate.clean()


def spring_pad_conflicts():
    """Springs whose window or nub a through-hole pad's clearance would cut into (should be none)."""
    bad = []
    for cx, cy, ax in SPRINGS:
        L, W = SPRING_L, SPRING_W + 2 * SPRING_SLOT
        hx, hy = (L / 2, W / 2) if ax == 'x' else (W / 2, L / 2)
        for x, y, r in tht_pads():
            rr = r + LEAD_CLR
            if abs(x - cx) < hx + rr and abs(y - cy) < hy + rr:
                bad.append(((cx, cy), (round(x, 2), round(y, 2))))
    return bad


if __name__ == '__main__':
    print('spring/pad conflicts:', spring_pad_conflicts())
    m = build()
    print('midplate solids', len(m.solids().vals()), 'vol', round(m.val().Volume(), 1))
    cq.exporters.export(m, str(hw.OUT / 'midplate.stl'), tolerance=0.03, angularTolerance=0.15)
