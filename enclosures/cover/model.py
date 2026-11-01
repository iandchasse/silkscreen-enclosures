"""The slide-on cover: one printed part per case envelope, gripping the case's top and bottom END walls.

DESIGN FRAME (the cover sitting on the FRONT of the case, at home): X, Y, Z are the case's own (CAD) axes, so the cover
is drawn on the case it fits. Z is up toward the screen. The cover is a plate over the front face with, at each end of
the case, a CHANNEL: a wall facing the end face and a lip that hooks the opposite face's end edge (its round). It slides
along X. At its +X end it has a closed STOP side (the corner pieces and a low wall along the long side); at its -X end it
is open, and each channel wall carries a PRONG (a cantilever, cut free of the plate by a kerf, 0.8 thick) with a tall bump
(the ridge) that rides the flat end face and drops into the case's R5 plan corner when the cover is home: the snap.

Turn the cover over about the long axis (x -> 2 xc - x, z -> zm - (z - zm)) and the same part sits on the BACK of the case
with its stop on the left. The case's plan is symmetric about xc, and the ridge's z band and the gaps are symmetric
about the case's mid-plane, so the one part works both ways (check.py proves it on the real STLs).

PRINT FRAME: the plate's outer face on the bed (rotate 180 degrees about Y); the channels rise from it, the lip is the last
thing printed and its case side is a 47-degree overhang; nothing needs a support (check.py audits every layer).

Every number that sets a fit is in SPEC below with the reason next to it. Nothing here edits the case: the envelope, the
rounds, the key caps and the side keys are read from the case projects (case_info.py).
"""
import math
from copy import deepcopy

import cadquery as cq

import case_info

LAYER = 0.2

# ---- the numbers ------------------------------------------------------------------------------------------------
SPEC = dict(
    # clearances (design values; check.py prints the as-printed budget). FDM: parts come out 0.05-0.15 large (the case's
    # own KEY_FDM), so a 0.30 channel clearance per side is 0.15-0.25 as printed on a typical case.
    cy=0.30,          # channel wall to the end face, per side (the coupons try 0.20 and 0.30)
    cx=0.30,          # stop wall to the long side in the drawn pose: the same as cy, so the corner and side sections are the
                      # end wall's (the snap preloads the cover into the stop, so at home this gap is closed)
    G=0.70,           # total Z play: plate gap + lip gap. The nominal cover sits centred: plate gap = lip gap = G/2. Set so
                      # that plate + channel is a whole number of 0.2 layers (whole_layers) so the lip's flat prints true
    gn=0.45,          # normal clearance of the lip's 47-degree face to the BACK round (R2.0) at the end walls; the FRONT round
                      # (R1.8) lies 0.08 nearer (0.37). At the stop side, home (the wall touching) takes 0.22 off both: 0.23 / 0.15
    tw=1.6,           # channel wall: four 0.4 lines
    ts=1.6,           # stop wall
    tl=1.2,           # lip, at its tip (six layers); it is thicker toward the wall (the 47-degree face)
    lip_deg=47.0,     # the lip's case side, from horizontal: steeper than 45 so it prints as a plain slope (the repo's rule:
                      # an exact 45 lands on the overhang audit's threshold)
    reach=1.10,       # lip tip past the end face: the 47-degree face runs to v_f = 1.14 from the wall, so the tip leaves a flat of
                      # 0.26 (a layer can hang 0.3 over air): nothing overhangs more. The front's key caps start 1.87 in from
                      # the bottom end and the lip meets them when the cover is on the back (tip < 1.57). It hooks the ROUND
    hw=3.4,           # stop wall height from the plate's inner face (17 layers) at most: on the front its bottom stays above the
                      # USB-C recess by usb_clr (the 3.68's is lower in the case, so its wall is shorter, derive())
    usb_clr=1.0,
    gap_margin=1.2,   # stop wall gaps: past each side key's box, along Y
    gap_join=3.0,     # two gaps closer than this are one (no free-standing stub of wall)
    ext=2.7,          # the corner piece carries on along the long side this far (full height) before the low wall
    # the snap prong
    t_pr=0.8,         # prong thickness: two lines, in plane along the layers (bends about a vertical edge: never across layers)
    taper=4.0,        # the prong's outer face thickens to tw at its root over this length
    kerf=1.0,         # plate edge to the prong's inner face, along the prong: so the prong flexes free of the plate
    d_eng=0.7,        # engagement: the tip of the ridge stands this far inside the end face plane at home, i.e. the prong
                      # deflects d_eng riding the flat end face. b = cy + d_eng is the ridge's height off the wall
    d_pre=0.15,       # preload at home: how far the prong is still deflected when the stop wall touches
    r_i=3.0,          # insertion ramp (shallow: arctan(b / r_i) = 18 degrees)
    f_top=1.6,        # flat top of the ridge
    r_r=1.0,          # removal ramp (45 degrees)
    ridge_half=3.7,   # the ridge's base spans +-3.7 about the case's mid-plane (7.4 tall, 5.4 at its tip: 45-degree ends)
    ridge_shift=0.0,  # moves the ridge's band along the wall (0 = centred: the same z in both orientations). Only the check's
                      # deliberately wrong cover uses it
    h_pr_top=0.55,    # the prong stands this far above the ridge's top
    L_pr=11.0,        # prong root to the ridge's centre (sets u_root)
    corner_clr=0.20,  # the corner pieces' inner radius = CORNER_R + this
    chamfer=0.4,      # plate's outer (bed) edge
    # plate
    key_clr=0.25,     # pocket ceiling over a key cap, with the plate at its nearest (touching the face)
    pocket_xy=0.6,    # pocket past the cap in x and y
    relief_xy=1.2,    # screen relief past the window's box
    web=1.2,          # plate thickness over the relief and the pockets' roof: >= this (six layers)
    pocket_roof=0.8,  # thinnest plate over a key pocket (four layers)
)


def whole_layers(tp, T, G0):
    """G >= G0 such that tp + T + G is a whole number of layers (the lip's flat then falls on a layer boundary)."""
    k = math.ceil((tp + T + G0) / LAYER - 1e-9)
    return round(k * LAYER - tp - T, 4)


def spec(group, **over):
    """The cover's full set of numbers for a group ('keyed', 'chinless', 'x3') and any override."""
    g = deepcopy(GROUPS[group])
    c = case_info.info(g['case'], g['slug'])
    s = dict(SPEC)
    s.update(g.get('over', {}))
    s.update(over)
    s['group'] = group
    for k in ('X0', 'X1', 'Y0', 'Y1', 'Z_FRONT', 'Z_BACK', 'CORNER_R', 'FRONT_EDGE_R', 'BACK_EDGE_R'):
        s[k] = c[k]
    s['T'] = round(c['Z_FRONT'] - c['Z_BACK'], 4)
    s['caps'] = c['caps']
    s['window'] = c['window']
    s['usb'] = c['usb']
    # the side keys of every build of the group: the union of their Y boxes (any layout, either side)
    keys = {}
    for slug in g['key_builds']:
        for ref, b in case_info.info(g['case'], slug)['side_keys'].items():
            keys.setdefault(ref, b)
    s['side_keys'] = keys
    # plate thickness: pockets over the key caps need the most (cap proud + clearance + the plate's nearest approach)
    if s['caps']:
        proud = max(k[4] for k in s['caps']) - s['Z_FRONT']
        s['pocket_depth'] = round(proud + s['key_clr'], 3)       # over the cap with the plate touching the face
        s['tp'] = s.get('tp') or round(math.ceil((s['pocket_depth'] + s['pocket_roof']) / LAYER - 1e-9) * LAYER, 3)
    else:
        s['pocket_depth'] = 0.0
        s['tp'] = s.get('tp') or 1.8
    if 'G' not in over:
        s['G'] = whole_layers(s['tp'], s['T'], SPEC['G'] - 0.01)
    derive(s)
    return s


GROUPS = {
    'keyed': dict(case='case-426', slug='standard', key_builds=['standard'],
                  label='4.26 with bottom keys (standard and light strip, every side-key layout, J6 or not)'),
    'chinless': dict(case='case-426', slug='chinless', key_builds=['chinless'],
                     label='4.26 chinless (chinless and light-strip chinless, every layout)'),
    'x3': dict(case='case-368', slug='standard', key_builds=['standard'], label='3.68 standard'),
}


def derive(s):
    """Positions that follow from the numbers (design frame, front pose, nominal Z)."""
    gp = gl = s['G'] / 2
    s['gp'], s['gl'] = gp, gl
    s['D_in'] = round(s['T'] + s['G'], 4)
    s['z_i'] = s['Z_FRONT'] + gp                      # plate inner face
    s['z_o'] = s['z_i'] + s['tp']                     # plate outer face (the bed)
    s['z_lf'] = s['Z_BACK'] - gl                      # lip, case side (flat)
    s['z_lb'] = s['z_lf'] - s['tl']                   # lip, outer face
    s['zm'] = (s['Z_FRONT'] + s['Z_BACK']) / 2
    s['xc'] = (s['X0'] + s['X1']) / 2
    s['ym'] = (s['Y0'] + s['Y1']) / 2
    s['yw_t'] = s['Y1'] + s['cy']                      # channel wall inner faces
    s['yw_b'] = s['Y0'] - s['cy']
    s['xs'] = s['X1'] + s['cx']                        # stop wall inner face
    s['R_ci'] = s['CORNER_R'] + s['corner_clr']
    s['cxc'] = s['xs'] - s['R_ci']                     # corner piece centres (right side)
    s['cyc_t'] = s['yw_t'] - s['R_ci']
    s['cyc_b'] = s['yw_b'] + s['R_ci']
    # the lip's case-side face, in (v, z): v = inward distance from the wall's inner face
    m = math.tan(math.radians(s['lip_deg']))
    s['m'] = m
    Rb, gn, cy = s['BACK_EDGE_R'], s['gn'], s['cy']
    zc = s['Z_BACK'] + Rb
    z0 = zc + m * (cy + Rb) - (Rb + gn) * math.sqrt(1 + m * m)          # the line's z at the wall (v = 0)
    s['z_cf0'] = z0
    s['v_f'] = (z0 - s['z_lf']) / m                                      # where it meets the flat
    s['v_tip'] = cy + s['reach']
    # the stop wall: no taller than keeps its bottom usb_clr above the USB-C recess's top (front orientation)
    s['hw_eff'] = min(s['hw'], math.floor((s['z_i'] - s['usb'][3] - s['usb_clr']) / LAYER + 1e-9) * LAYER)
    # the ridge
    b = cy + s['d_eng']
    s['b'] = b
    s['h_mid'] = s['D_in'] / 2
    hr = s['h_mid'] + s['ridge_shift']
    s['ridge_z'] = (s['z_i'] - (hr + s['ridge_half']), s['z_i'] - (hr - s['ridge_half']))   # z lo, hi
    s['prong_z_lo'] = s['ridge_z'][0] - s['h_pr_top']
    s['prong_z_lo'] = round(s['z_o'] - round((s['z_o'] - s['prong_z_lo']) / LAYER) * LAYER, 4)
    # home: the stop wall touches the long side (cover shift s_home = -cx); the ridge's flat top ends where the end
    # round plan arc stands d_eng - d_pre above the tip, i.e. y_arc = Y1 - d_pre
    R = s['CORNER_R']
    xa = s['X0'] + R                                                     # the arc's tangent point on the end face
    run = math.sqrt(R * R - (R - s['d_eng'] + s['d_pre']) ** 2)         # the arc stands d_eng - d_pre over the tip there
    x_t = xa - run                                                       # case x of the flat top's trailing end at home
    s['u_t'] = x_t + s['cx']                                             # in the cover's own u (shift -cx at home)
    s['u_a'] = s['u_t'] - s['r_i'] - s['f_top']                          # ridge starts
    s['u_tip'] = s['u_a'] - 0.5
    s['u_root'] = s['u_t'] - s['f_top'] / 2 + s['L_pr']
    s['u_cs'] = s['cxc']                                                 # straight walls end where the corner piece starts
    return s


# ---- solids -----------------------------------------------------------------------------------------------------

def _box(x0, x1, y0, y1, z0, z1):
    return (cq.Workplane('XY').box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0)))


def section_vz(s):
    """The wall + lip cross-section in (v, z): v inward from the wall's inner face (0), negative into the wall."""
    top = s['z_i'] + 0.2
    pts = [(0.0, top), (0.0, s['z_cf0'])]
    if s['v_f'] < s['v_tip']:
        pts += [(s['v_f'], s['z_lf']), (s['v_tip'], s['z_lf']), (s['v_tip'], s['z_lb'])]
    else:                                                                # the tip is on the slope: no flat
        zt = s['z_cf0'] - s['m'] * s['v_tip']
        pts += [(s['v_tip'], zt), (s['v_tip'], zt - s['tl'])]
    pts += [(-s['tw'], s['z_lb']), (-s['tw'], top)]
    return pts


def straight_wall(s, u0, u1):
    """The top channel's wall + lip as an extrusion along X from u0 to u1 (the profile at y = yw_t - v)."""
    pts = [(s['yw_t'] - v, z) for v, z in section_vz(s)]
    return cq.Workplane('YZ', origin=(u0, 0, 0)).polyline(pts).close().extrude(u1 - u0)


def corner_piece(s):
    """The top-right corner: the section revolved 90 degrees about the vertical axis through (cxc, cyc_t), then carried on
    along the long side for ext (full height), so the stop side holds the case's R5 arc and the hard stop is the cover's
    own: wall and lip follow the arc at corner_clr."""
    pts = [(s['cyc_t'] + s['R_ci'] - v, z) for v, z in section_vz(s)]
    w = cq.Workplane('YZ', origin=(s['cxc'], 0, 0)).polyline(pts).close()
    rev = w.revolve(90, (s['cyc_t'], 1, 0), (s['cyc_t'], 0, 0))      # +90 about -Z: from +Y round to +X
    # along the side: section in (x, z) at x = xs - v, extruded toward -Y from y = cyc_t
    ptx = [(s['xs'] - v, z) for v, z in section_vz(s)]
    side = (cq.Workplane('XZ', origin=(0, s['cyc_t'], 0)).polyline(ptx).close().extrude(s['ext']))
    return rev.union(side)


def prong(s):
    """The top prong with its ridge: a thin wall from the bed (z_o) down to prong_z_lo, from the tip to the root, the outer
    face thickening to tw at the root; the ridge on its inner face."""
    yw, tw, tp = s['yw_t'], s['tw'], s['t_pr']
    pts = [(s['u_tip'], yw), (s['u_root'], yw), (s['u_root'], yw + tw), (s['u_root'] - s['taper'], yw + tp),
           (s['u_tip'], yw + tp)]
    z_hi, z_lo = s['z_o'], s['prong_z_lo']
    w = cq.Workplane('XY', origin=(0, 0, z_lo)).polyline(pts).close().extrude(z_hi - z_lo)
    # the ridge: the (u, y) trapezoid extruded over z, cut to the (y, z) trapezoid (45-degree ends) extruded along u
    b = s['b']
    ua = s['u_a']
    tr = [(ua, yw + 0.3), (ua, yw), (ua + s['r_i'], yw - b), (ua + s['r_i'] + s['f_top'], yw - b),
          (ua + s['r_i'] + s['f_top'] + s['r_r'], yw), (ua + s['r_i'] + s['f_top'] + s['r_r'], yw + 0.3)]
    zlo, zhi = s['ridge_z']
    prism = cq.Workplane('XY', origin=(0, 0, zlo - 0.0)).polyline(tr).close().extrude(zhi - zlo)
    ends = [(yw + 0.3, zlo), (yw, zlo), (yw - b, zlo + b), (yw - b, zhi - b), (yw, zhi), (yw + 0.3, zhi)]
    trap = (cq.Workplane('YZ', origin=(ua - 1, 0, 0)).polyline(ends).close().extrude(s['r_i'] + s['f_top'] + s['r_r'] + 2))
    return w.union(prism.intersect(trap))


def plate_outline(s):
    """The plate's plan outline as a closed wire's points + arcs: x from u_tip to the stop wall's outer face; the right
    corners follow the corner pieces' outer radius."""
    Ro = s['R_ci'] + s['tw']
    x0 = s['u_tip']
    xr = s['xs'] + s['ts']
    yt = s['yw_t'] + s['tw']
    yb = s['yw_b'] - s['tw']
    c45 = math.sqrt(0.5)
    cxc, cyt, cyb = s['cxc'], s['cyc_t'], s['cyc_b']
    w = (cq.Workplane('XY', origin=(0, 0, s['z_i']))
         .moveTo(x0, yb).lineTo(cxc, yb)
         .threePointArc((cxc + Ro * c45, cyb - Ro * c45), (xr, cyb))
         .lineTo(xr, cyt)
         .threePointArc((cxc + Ro * c45, cyt + Ro * c45), (cxc, yt))
         .lineTo(x0, yt).close())
    return w.extrude(s['tp'])


def gaps(s):
    """Y intervals where the low stop wall is cut away: every side key of the group (either side) plus gap_margin."""
    iv = sorted((b[2] - s['gap_margin'], b[3] + s['gap_margin']) for b in s['side_keys'].values())
    out = []
    for a, b in iv:
        if out and a - out[-1][1] < s['gap_join']:                       # a stub of wall too short to stand: one gap
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [tuple(v) for v in out]


def stop_wall(s, with_gaps=True):
    """The low wall along the long side between the corner pieces' extensions, cut at the gaps."""
    y_lo = s['cyc_b'] + s['ext']                                 # the bottom extension's end
    y_hi = s['cyc_t'] - s['ext']
    z0, z1 = s['z_i'] - s['hw_eff'], s['z_i'] + 0.2
    segs = [(y_lo, y_hi)]
    if with_gaps:
        for a, b in gaps(s):
            nxt = []
            for p, q in segs:
                if b <= p or a >= q:
                    nxt.append((p, q))
                    continue
                if a > p:
                    nxt.append((p, a))
                if b < q:
                    nxt.append((b, q))
            segs = nxt
    solid = None
    for p, q in segs:
        if q - p < 0.5:
            continue
        bx = _box(s['xs'], s['xs'] + s['ts'], p, q, z0, z1)
        solid = bx if solid is None else solid.union(bx)
    return solid


def half_top(s):
    """Everything that belongs to the top end and is mirrored for the bottom: straight wall and corner piece (the prong
    is added after the kerfs are cut)."""
    return straight_wall(s, s['u_root'], s['u_cs']).union(corner_piece(s))


def mirror_y(wp, s):
    return wp.mirror('XZ', (0, s['ym'], 0))


def pockets(s):
    """The cuts into the plate's inner face: ONE slot along the slide direction over the bottom-key row (the plate passes over
    the caps on its way, so a pocket at home alone would hit them: the slot runs from the leading end to just past the last
    cap at home), and the screen relief."""
    cuts = []
    z0 = s['z_i'] - 0.1
    if s['caps']:
        top = max(k[4] for k in s['caps'])
        x1 = max(k[1] for k in s['caps']) + s['pocket_xy'] + s['cx']
        y0 = min(k[2] for k in s['caps']) - s['pocket_xy']
        y1 = max(k[3] for k in s['caps']) + s['pocket_xy']
        cuts.append(_box(s['u_tip'] - 1, x1, y0, y1, z0, top + s['key_clr'] + s['gp']))
    wx0, wx1, wy0, wy1 = s['window']
    depth = s['tp'] - s['web']
    if depth > 0.05:
        r = s['relief_xy']
        cuts.append(_box(wx0 - r, wx1 + r, wy0 - r, wy1 + r, z0, s['z_i'] + depth))
    return cuts


def kerfs(s):
    """The plate cut away beside each prong, so the prong stands free (from the bed) and flexes."""
    cuts = []
    x1 = s['u_root']
    cuts.append(_box(s['u_tip'] - 1, x1, s['yw_t'] - s['kerf'], s['yw_t'] + s['tw'] + 1, s['z_i'] - 0.1, s['z_o'] + 0.1))
    cuts.append(_box(s['u_tip'] - 1, x1, s['yw_b'] - s['tw'] - 1, s['yw_b'] + s['kerf'], s['z_i'] - 0.1, s['z_o'] + 0.1))
    return cuts


def build(s, with_gaps=True, ridge=True, relief=True):
    """The whole cover in the design frame. with_gaps=False (the wrong cover the checks must catch); ridge=False the rigid
    frame (the slide-path check moves it and adds the ridge's own test); relief=False no pockets / relief."""
    plate = plate_outline(s)
    try:
        plate = plate.faces('>Z').edges().chamfer(s['chamfer'])
    except Exception:
        pass
    top = half_top(s)
    bot = mirror_y(top, s)
    body = plate.union(top).union(bot)
    sw = stop_wall(s, with_gaps)
    if sw is not None:
        body = body.union(sw)
    for k in kerfs(s):
        body = body.cut(k)
    # the prongs stand in the kerfs: put them back (the kerf box only clears the plate)
    p = prong(s)
    body = body.union(p).union(mirror_y(p, s))
    if relief:
        for c in pockets(s):
            body = body.cut(c)
    if not ridge:
        body = body.cut(_ridge_zone(s)).cut(mirror_y(_ridge_zone(s), s))
    return body


def _ridge_zone(s):
    """A box over the ridge's volume on the inner side of the top prong's wall plane (to remove the ridge, leave the wall)."""
    yw = s['yw_t']
    return _box(s['u_tip'] - 1, s['u_root'] - 3, yw - s['b'] - 0.1, yw - 1e-3, s['prong_z_lo'] - 1, s['z_i'] - 1e-3)


def to_print_frame(shape, s):
    """Plate face down: rotate 180 degrees about Y (x -> -x, z -> -z), then the min corner to the origin."""
    r = shape.rotate((0, 0, 0), (0, 1, 0), 180)
    bb = r.val().BoundingBox()
    return r.translate((-bb.xmin, -bb.ymin, -bb.zmin))
