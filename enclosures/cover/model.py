"""The slide-on cover: one printed part per case envelope, gripping the case's top and bottom END walls.  Round 2 (2026-11-01).

DESIGN FRAME (the cover sitting on the FRONT of the case, at home): X, Y, Z are the case's own (CAD) axes, so the cover is drawn on the
case it fits. Z is up toward the screen. The cover is a plate over the front face with, at each end of the case, a CHANNEL: a wall facing
the end face and a lip that hooks the opposite face's end edge. It slides along X. At its +X end it has a closed STOP side (a
corner piece at each end, no wall between them); its -X end is open and each channel wall carries a PRONG (a cantilever, standing free of
the plate, 0.8 thick) with a tall ridge that rides the flat end face and drops into the case's R5 plan corner when the cover is home:
the snap.

The cover is SYMMETRIC about its own mid-length (y = (Y0 + Y1) / 2) and about the case's mid-plane in z, so it sits on the front or the
back, turned either way round in the plane, the same four ways (check.py: front, back, front turned, back turned). What is not symmetric
is the logo engraved in its outer face: it reads right in the front pose and sits exactly over the case's own back logo in the back
pose; in the two turned poses it reads upside down.

Round 2 changes (Ian, 2026-11-01): the case's back logos engraved in the outer face (and the two-colour inlay parts); every exposed edge
rounded (bed-face perimeter 45-degree chamfer, other edges filleted, the prong's free end fully rounded, the open-end plan corners R3);
the prong's thinning is on its INNER side (the outer face is one smooth surface); both ends of the plate have the key slot; no long stop
wall (the corner pieces and their extensions only); both long sides curve inward over the side keys (the scallop).

Phase 2 (2026-11-01): the plate is SOLID over the screen (no relief; chinless 2.4 thick), the key slots' cutters are flared 45 degrees at the mouth, two
engraved border lines follow the plate's outline (2.5 and 4.5 in), the tab's side outline is a rounded tongue inside phase 1's footprint (the ridge's
lead-in is trimmed to it: only the flat top keeps the full J6 band), and the slit between the tab and the plate is one uniform slit with a round end
(the tab's bed foot grows into the plate's chamfer over its taper: no step).

PRINT FRAME: the plate's outer face on the bed (rotate 180 degrees about Y); nothing needs a support (printcheck.py audits every layer).
Every number that sets a fit is in SPEC below with the reason next to it. Nothing here edits the case: the envelope, the rounds, the key
caps, the side keys, the window and the logos are read from the case projects (case_info.py).
"""
import math
from copy import deepcopy

import cadquery as cq
import shapely.affinity as sa
from shapely import wkt

import case_info

LAYER = 0.2

# ---- the numbers ------------------------------------------------------------------------------------------------
SPEC = dict(
    # ---- fit: unchanged from coupon A, which Ian printed and found fine (2026-11-01)
    cy=0.30,          # channel wall to the end face, per side (FDM: as printed 0.20 / 0.10 / 0.00 best / typical / worst)
    cx=0.30,          # stop piece to the long side in the drawn pose; closed at home (the snap preloads the cover into it)
    G=0.70,           # total Z play: plate gap + lip gap (whole layers: whole_layers)
    gn=0.45,          # normal clearance of the lip's 47-degree face to the back round (0.37 to the front's)
    tw=1.6,           # channel wall: four 0.4 lines
    ts=1.6,           # stop piece wall
    tl=1.2,           # lip thickness at its tip (the tip is a half round of lip_r)
    lip_deg=47.0,     # the lip's case side, from horizontal
    # ---- the snap prong (the working geometry is A's: thickness profile, root, length, ridge height and ramps)
    t_pr=0.8,         # prong thickness: two lines, in plane along the layers
    taper=4.0,        # the prong's INNER face thickens to the full wall at its root over this length (the outer face is flush)
    d_eng=0.7,        # the ridge's tip stands this far inside the end face plane at home
    d_pre=0.15,       # preload at home
    r_i=3.0,          # insertion ramp (18 degrees)
    f_top=1.6,        # flat top of the ridge
    r_r=1.0,          # removal ramp (45 degrees)
    ridge_half=3.7,   # the ridge's z span at the wall plane: +-3.7 about the case's mid-plane (5.4 at its tip: 45-degree ends)
    ridge_shift=0.0,  # moves the ridge's band along the wall (only the check's deliberately wrong cover uses it)
    ridge_trim=0.05,  # the ridge sits this much further along u: its 0.3 and 0.5 roundings cut the corner of the 45-degree ramp, which took 0.03 mm off the home preload
    h_pr_top=0.55,    # the prong stands this far past the ridge base's top
    L_pr=11.0,        # prong root to the ridge's flat-top centre
    corner_clr=0.20,  # the corner pieces' inner radius = CORNER_R + this
    # ---- round 2: edges
    bed_chamfer=0.6,  # 45 degrees round the whole bed-face (outer face) perimeter of the plate
    prong_chamfer=0.1,  # the same round the prong's foot, much smaller: it is only 0.8 thick, and the CC2 (EFC 0.1, classic walls) lays no first-layer line narrower than about 0.45 (0.3 left 0.4)
    fillet=0.5,       # every other exposed edge
    lip_r=0.6,        # the lip's tip is a half round: the 47-degree face runs into it
    wall_r=0.9,       # the wall's outer-bottom corner (the lip's outer face meets the wall)
    inner_r=0.8,      # the wall / lip's concave corner
    prong_top_r=0.30,  # every edge of the tab's side outline (the 0.8 plate keeps a 0.2 flat: a 0.38 round left the bed foot 0.55 wide at the first layer's mid-plane, too thin for the CC2)
    ridge_r=0.45,     # the ridge's edges (ramp-to-flat bends are 18 and 45 degrees: this moves the surface < 0.02)
    tongue_r=3.0,     # plan radius of the open-end corners of the plate
    tongue_r_slot=1.5,  # ... where the key slot leaves through the leading edge (3.0 would put the slot's wall through the corner round)
    kink_r=8.0,       # the tab's inner face turns 11 degrees at the ends of its taper: rounded (the plate edge is one slit away, so R +- slit)
    slit_flat=1.2,    # the plate edge runs flat this far before the slit's round end
    slit=0.8,         # the slit between the plate and each tab: one uniform width, following the tab's inner face, ending in a round end at the root
    tongue_hT=1.5,    # the tab's side outline (print height h above the bed, x = u - u_a): the bottom edge rises 45 degrees from x = tongue_xA ...
    tongue_xA=2.0,    # ... to the tip vertex (x = xA - hT, h = hT), the top edge runs from the tip vertex up to the vertex at x = tongue_xC, h = the full height
    tongue_xC=-1.0,
    tongue_RA=1.2,    # radii: where the bottom edge leaves the bed (small: a bigger blend is a near-flat overhang in the first layers), at the tip, and where the top edge leaves the full height
    tongue_RT=4.0,
    tongue_RC=5.0,
    tongue_out=0.5,   # the plate's leading edge stands this far past the case's side face (outside the scallop)
    # ---- round 2: sides
    scallop_M=3.0,    # finger margin past the pad zone, along Y (a target: the corner arc starts 4.7 past the last pad)
    scallop_Lt=6.0,   # length of each ease in and out (quintic: tangent- and curvature-continuous)
    scallop_join=20.0,  # zones closer than this are one curve
    scallop_dmax=3.0,  # target inset (the limit is the screen: scallop_overlap)
    scallop_overlap=2.0,  # the plate stays this far past the screen opening's edge on each side (front pose)
    ext_override=None,  # only the check's deliberately wrong cover sets it
    # ---- plate
    key_clr=0.25,     # slot ceiling over a key cap, with the plate at its nearest (touching the face)
    pocket_xy=0.6,    # slot past the cap in x (the far end)
    pocket_y=0.35,    # slot past the cap in y: the slot then leaves through the leading edge's straight part, clear of the corner round
    roof_flare=0.5,   # the key slot's cutter flares 45 degrees up toward the leading face over this length: the roof leaves the face in a bevel, not a 90-degree edge
    pocket_roof=1.2,  # thinnest plate over a key slot (six layers): the bed chamfer (0.6) and the slot-mouth fillet (0.5) both end there
    slot_ends='both',  # 'both' (round 2) or 'bottom' (the deliberately wrong one-ended cover)
    logo=True,        # engrave the case's back logos in the outer face
    border=True,      # two engraved lines round the plate's outline, like a book cover's tooled border (grip; not part of the two-colour switch)
    border_insets=(2.5, 4.5),   # their centre lines, from the plate's edge
    border_w=0.8,     # the case's grip groove width (params.GRIP_GROOVE)
    border_depth=0.4,  # two whole layers (the case's groove is 0.35 / 0.2: a whole layer for the printer)
    border_r=2.0,     # the centre lines' smallest radius (corners and the scallop's curves are rounded to this)
    border_clr=2.0,   # the lines stay this far from the logos (they move, the logos do not)
    tp_plain=2.4,     # the plate's thickness with no bottom keys (chinless): SOLID over the screen, no relief (phase 2, 2026-11-01)
)


def whole_layers(tp, T, G0):
    """G >= G0 such that tp + T + G is a whole number of layers."""
    k = math.ceil((tp + T + G0) / LAYER - 1e-9)
    return round(k * LAYER - tp - T, 4)


GROUPS = {
    'keyed': dict(case='case-426', slug='standard', key_builds=['standard'],
                  label='4.26 with bottom keys (standard and light strip, every side-key layout, J6 or not)'),
    'chinless': dict(case='case-426', slug='chinless', key_builds=['chinless'],
                     label='4.26 chinless (chinless and light-strip chinless, every layout)'),
    'x3': dict(case='case-368', slug='standard', key_builds=['standard'], label='3.68 standard'),
}


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
    s['window_face'] = c['window_face']
    s['usb'] = c['usb']
    s['logos'] = c['logos']
    s['case_slug'] = g['slug']
    pads = {}                                  # the pads of every build of the group (any layout, either side): the union
    for slug in g['key_builds']:
        for ref, b in case_info.info(g['case'], slug)['pads'].items():
            pads.setdefault(ref, b)
    s['pads'] = pads
    if s['caps']:
        proud = max(k[4] for k in s['caps']) - s['Z_FRONT']
        s['pocket_depth'] = round(proud + s['key_clr'], 3)
        s['tp'] = s.get('tp') or round(math.ceil((s['pocket_depth'] + s['pocket_roof']) / LAYER - 1e-9) * LAYER, 3)
    else:
        s['pocket_depth'] = 0.0
        s['tp'] = s.get('tp') or s['tp_plain']
    if 'G' not in over:
        s['G'] = whole_layers(s['tp'], s['T'], SPEC['G'] - 0.01)
    derive(s)
    return s


def merge_zones(iv, join):
    out = []
    for a, b in sorted(iv):
        if out and a - out[-1][1] < join:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [tuple(v) for v in out]


def derive(s):
    """Positions that follow from the numbers (design frame, front pose, nominal Z)."""
    gp = gl = s['G'] / 2
    s['gp'], s['gl'] = gp, gl
    s['D_in'] = round(s['T'] + s['G'], 4)
    s['z_i'] = s['Z_FRONT'] + gp                      # plate inner face
    s['z_o'] = s['z_i'] + s['tp']                     # plate outer face (the bed)
    s['z_lf'] = s['Z_BACK'] - gl                      # the lip's flat level (before round 2; kept for the checks' notes)
    s['z_lb'] = s['z_lf'] - s['tl']                   # lip, outer face
    s['zm'] = (s['Z_FRONT'] + s['Z_BACK']) / 2
    s['xc'] = (s['X0'] + s['X1']) / 2
    s['ym'] = (s['Y0'] + s['Y1']) / 2
    s['yw_t'] = s['Y1'] + s['cy']                      # channel wall inner faces
    s['yw_b'] = s['Y0'] - s['cy']
    s['yt_t'] = s['yw_t'] + s['tw']                    # channel wall outer faces (the plate's edge)
    s['yt_b'] = s['yw_b'] - s['tw']
    s['xs'] = s['X1'] + s['cx']                        # stop piece inner face
    s['xr'] = s['xs'] + s['ts']                        # ... and outer
    s['R_ci'] = s['CORNER_R'] + s['corner_clr']
    s['cxc'] = s['xs'] - s['R_ci']                     # corner piece centres (right side)
    s['cyc_t'] = s['yw_t'] - s['R_ci']
    s['cyc_b'] = s['yw_b'] + s['R_ci']
    # the lip's case-side face, in (v, z): v = inward distance from the wall's inner face
    m = math.tan(math.radians(s['lip_deg']))
    s['m'] = m
    Rb, gn, cy = s['BACK_EDGE_R'], s['gn'], s['cy']
    zc = s['Z_BACK'] + Rb
    s['z_cf0'] = zc + m * (cy + Rb) - (Rb + gn) * math.sqrt(1 + m * m)   # the line's z at the wall (v = 0)
    s['v_b'] = (s['z_cf0'] - s['z_lb']) / m                              # the line meets the lip's outer face here; the tip round replaces it
    r, a = s['lip_r'], math.radians(s['lip_deg'])
    vc = s['v_b'] - r / math.sin(a / 2) * math.cos(a / 2)                # the tip round's centre: on the wedge's bisector
    s['lip_centre'] = (vc, s['z_lb'] + r)
    s['v_tip'] = vc + r                                                  # the farthest the lip reaches in from the wall's inner face
    # the ridge
    s['b'] = cy + s['d_eng']
    s['h_mid'] = s['D_in'] / 2
    hr = s['h_mid'] + s['ridge_shift']
    s['ridge_z'] = (s['z_i'] - (hr + s['ridge_half']), s['z_i'] - (hr - s['ridge_half']))   # z lo, hi at the wall plane
    zlo_base = s['ridge_z'][0] - (s['t_pr'] + 0.3)                       # the 45-degree ends run on to the prong's inner face
    pz = zlo_base - s['h_pr_top']
    s['prong_z_lo'] = round(s['z_o'] - round((s['z_o'] - pz) / LAYER) * LAYER, 4)
    # home: the stop piece touches the long side (cover shift -cx); the ridge's flat top ends where the end round's plan arc stands
    # d_eng - d_pre over the tip
    R = s['CORNER_R']
    xa = s['X0'] + R
    run = math.sqrt(R * R - (R - s['d_eng'] + s['d_pre']) ** 2)
    s['u_t'] = xa - run + s['cx'] + s['ridge_trim']
    s['u_a'] = s['u_t'] - s['r_i'] - s['f_top']
    s['u_root'] = s['u_t'] - s['f_top'] / 2 + s['L_pr']
    s['u_tip'] = min(u for u, _ in outline_points(*tongue_outline(s)))     # the tab's free end (its tongue reaches past the ridge)
    s['u_cs'] = s['cxc']
    # ---- the sides: scallop zones (every pad's y range and its mirror about the mid-length, plus the finger margin)
    iv = []
    for side, y0, y1, z0, z1, xf in s['pads'].values():
        for a0, a1 in ((y0, y1), (2 * s['ym'] - y1, 2 * s['ym'] - y0)):
            iv.append([a0 - s['scallop_M'], a1 + s['scallop_M']])
    s['zones'] = merge_zones(iv, s['scallop_join'])
    s['zone_lo'] = min(z[0] for z in s['zones'])
    s['zone_hi'] = max(z[1] for z in s['zones'])
    wf = s['window_face']                                                # the screen opening's face edges, from the tub STL
    room = min(wf[0] - s['scallop_overlap'] - s['X0'], s['X1'] - wf[1] - s['scallop_overlap'])
    s['d_scallop'] = min(s['scallop_dmax'], math.floor(room * 10 + 1e-9) / 10)
    s['u_L'] = s['X0'] + s['d_scallop'] + s['cx']                        # the scalloped edges, cover u (home: x = u - cx)
    s['u_R'] = s['X1'] - s['d_scallop'] + s['cx']
    s['u_l'] = s['X0'] - s['tongue_out'] + s['cx']                       # the plate's leading edge outside the scallop
    ext = s['cyc_t'] - (s['zone_hi'] + s['scallop_Lt'])
    s['ext_room'] = round(ext, 3)
    s['ext'] = round(max(s['ext_override'] if s['ext_override'] is not None else ext, 0.0), 3)
    return s


# ---- 2D helpers --------------------------------------------------------------------------------------------------

def _unit(a, b):
    d = math.hypot(b[0] - a[0], b[1] - a[1])
    return ((b[0] - a[0]) / d, (b[1] - a[1]) / d)


def round_path(pts, radii):
    """A closed polygon with exact arcs: pts [(x, y)], radii [r] (0 = sharp). -> start point and a list of ('line', p) / ('arc', mid, end)
    segments (trace with moveTo(start), then lineTo / threePointArc, close())."""
    n = len(pts)
    ent, ext_, mid = [None] * n, [None] * n, [None] * n
    for i in range(n):
        p, a, b = pts[i], pts[i - 1], pts[(i + 1) % n]
        r = radii[i]
        if r <= 0:
            ent[i] = ext_[i] = p
            continue
        d1, d2 = _unit(a, p), _unit(p, b)
        cr = d1[0] * d2[1] - d1[1] * d2[0]
        phi = math.acos(max(-1.0, min(1.0, d1[0] * d2[0] + d1[1] * d2[1])))      # the turning angle
        if phi < 1e-6:
            ent[i] = ext_[i] = p
            continue
        t = r * math.tan(phi / 2)
        A = (p[0] - d1[0] * t, p[1] - d1[1] * t)
        B = (p[0] + d2[0] * t, p[1] + d2[1] * t)
        sg = 1.0 if cr > 0 else -1.0
        C = (A[0] - d1[1] * sg * r, A[1] + d1[0] * sg * r)
        pc = math.hypot(p[0] - C[0], p[1] - C[1])
        ent[i], ext_[i], mid[i] = A, B, (C[0] + (p[0] - C[0]) / pc * r, C[1] + (p[1] - C[1]) / pc * r)
    segs = []
    for i in range(1, n):
        segs.append(('line', ent[i]))
        if mid[i] is not None:
            segs.append(('arc', mid[i], ext_[i]))
    segs.append(('line', ent[0]))
    if mid[0] is not None:
        segs.append(('arc', mid[0], ext_[0]))
    return ext_[0], segs


def outline_points(pts, radii, n=24):
    """The round_path outline sampled to points (for extents and containment checks; the CAD uses the exact arcs)."""
    st, segs = round_path(pts, radii)
    out, cur = [st], st
    for sg in segs:
        if sg[0] == 'line':
            out.append(sg[1])
            cur = sg[1]
            continue
        mid, end = sg[1], sg[2]
        ax, ay = cur
        bx, by = mid
        cx, cy = end
        d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
        uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
        r = math.hypot(ax - ux, ay - uy)
        a0, a1, a2 = math.atan2(ay - uy, ax - ux), math.atan2(by - uy, bx - ux), math.atan2(cy - uy, cx - ux)
        d1, d2 = (a1 - a0) % (2 * math.pi), (a2 - a0) % (2 * math.pi)
        tot = d2 if d1 < d2 else -((a0 - a2) % (2 * math.pi))
        out += [(ux + r * math.cos(a0 + tot * k / n), uy + r * math.sin(a0 + tot * k / n)) for k in range(1, n + 1)]
        cur = end
    return out


def tongue_outline(s):
    """The tab's SIDE outline in (u, z) as round_path input: root (inside the wall) bottom -> the point where the bottom edge leaves the bed ->
    the tip vertex -> the top vertex -> root top. Print height h = z_o - z; the bottom edge (toward the bed) rises 45 degrees toward the tip,
    so it prints without support; the top edge drops from the full height toward the tip in a large arc; the tip is a round. The ridge's whole
    z band stays inside for u >= u_a (tongue_contains_ridge)."""
    H = s['z_o'] - s['prong_z_lo']
    ua, ue = s['u_a'], s['u_root'] + 2.0
    hT, xA, xC = s['tongue_hT'], s['tongue_xA'], s['tongue_xC']
    pts_h = [(ue, 0.0), (ua + xA, 0.0), (ua + xA - hT, hT), (ua + xC, H), (ue, H)]
    return [(u, s['z_o'] - h) for u, h in pts_h], [0.0, s['tongue_RA'], s['tongue_RT'], s['tongue_RC'], 0.0]


def tongue_contains_ridge(s):
    """The ridge's z band at the tab's inner face (45-degree ends) lies inside the side outline from the flat top's start (u_a + r_i) to the root: only the flat top needs the full band; the lead-in shrinks toward the tip."""
    import shapely
    poly = shapely.Polygon(outline_points(*tongue_outline(s)))
    q = s['yt_t'] - s['t_pr'] + 0.3 - s['yw_t']
    zlo, zhi = s['ridge_z']
    return poly.contains(shapely.box(s['u_a'] + s['r_i'], zlo - q - 0.2, s['u_root'], zhi + q + 0.2))


def tongue_prism(s, y_hi, y_lo):
    """The tab's side outline extruded across y (from y_hi down to y_lo): cuts the tab, and the ridge's lead-in, to the tongue."""
    st, segs = round_path(*tongue_outline(s))
    return trace(cq.Workplane('XZ', origin=(0, y_hi, 0)), st, segs).extrude(y_hi - y_lo)


def trace(wp, start, segs):
    wp = wp.moveTo(*start)
    for sg in segs:
        wp = wp.lineTo(*sg[1]) if sg[0] == 'line' else wp.threePointArc(sg[1], sg[2])
    return wp.close()


def corner(prev, p, nxt, r):
    """The exact arc rounding the polygon corner p (between prev and nxt) with radius r -> (tangent point on the prev side, arc midpoint, tangent
    point on the next side)."""
    d1, d2 = _unit(prev, p), _unit(p, nxt)
    cr = d1[0] * d2[1] - d1[1] * d2[0]
    phi = math.acos(max(-1.0, min(1.0, d1[0] * d2[0] + d1[1] * d2[1])))
    tl = r * math.tan(phi / 2)
    A = (p[0] - d1[0] * tl, p[1] - d1[1] * tl)
    B = (p[0] + d2[0] * tl, p[1] + d2[1] * tl)
    sg = 1.0 if cr > 0 else -1.0
    C = (A[0] - d1[1] * sg * r, A[1] + d1[0] * sg * r)
    pc = math.hypot(p[0] - C[0], p[1] - C[1])
    return A, (C[0] + (p[0] - C[0]) / pc * r, C[1] + (p[1] - C[1]) / pc * r), B


def smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * t * (t * (6 * t - 15) + 10)           # quintic ease: zero slope and curvature at both ends


def _box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane('XY').box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


NOTES = []
SECOND_PASS = 0.0


def try_edges(wp, selector, op, r, label):
    """wp.<selector>.<op>(r) with a fallback to smaller r and, failing that, the shape unchanged (recorded in NOTES)."""
    for k, rr in enumerate((r, r * 0.8, r * 0.6, r * 0.4)):
        try:
            out = getattr(selector(wp), op)(rr)
            if out.val().isValid():
                if k:
                    NOTES.append(f'{label}: {op} {rr:.2f} instead of {r:.2f}')
                return out
        except Exception:
            continue
    NOTES.append(f'{label}: {op} {r} failed, left sharp')
    return wp


def watertight(wp):
    """Does the shape tessellate to a closed mesh at the build's STL tolerances (0.02, 0.1)? A fillet set can be a valid solid and still
    come out of the mesher with holes; such a stage is dropped."""
    import tempfile
    import os
    import trimesh
    fd, path = tempfile.mkstemp(suffix='.stl')
    os.close(fd)
    try:
        cq.exporters.export(wp, path, tolerance=0.02, angularTolerance=0.1)
        return bool(trimesh.load(path, force='mesh').is_watertight)
    finally:
        os.unlink(path)


def guarded(before, after, label):
    """`after` if it still meshes closed, else `before` (recorded)."""
    if after is before or watertight(after):
        return after
    NOTES.append(f'{label}: dropped (the mesh had holes)')
    return before


def fillet_good(wp, selector, r, label, op='fillet'):
    """Fillet the edges of `selector(wp)` that take a fillet one at a time (tangent seams and edges that cannot take it are left out), all
    at once, at r, else 0.8 r, 0.6 r (the edges that failed are counted in NOTES)."""
    es = selector(wp).vals()
    for k, rr in enumerate((r, r * 0.8, r * 0.6)):
        good = []
        for e in es:
            try:
                if getattr(wp.newObject([e]), op)(rr).val().isValid():
                    good.append(e)
            except Exception:
                pass
        if not good:
            continue
        try:
            out = getattr(wp.newObject(good), op)(rr)
            if out.val().isValid():
                NOTES.append(f'{label}: {len(good)} of {len(es)} edges {op}ed {rr:.2f}' + ('' if rr == r else f' (not {r:.2f})'))
                return out
        except Exception:
            continue
    NOTES.append(f'{label}: {len(es)} edges left sharp')
    return wp


# ---- the wall and lip, the corner pieces --------------------------------------------------------------------------

def section_vz(s):
    """The wall + lip cross-section as a rounded polygon in (v, z): v inward from the wall's inner face (0), negative into the wall. The
    lip's case side is the 47-degree line from (0, z_cf0) to the wedge's tip, which the half round of radius lip_r replaces; its outer
    face is flat at z_lb."""
    top = s['z_o'] - s['bed_chamfer'] - 0.1                # the wall stops under the bed chamfer: the plate carries the chamfer
    pts = [(0.0, top), (0.0, s['z_cf0']), (s['v_b'], s['z_lb']), (-s['tw'], s['z_lb']), (-s['tw'], top)]
    radii = [0.0, s['inner_r'], s['lip_r'], s['wall_r'], 0.0]
    return pts, radii


def _section_wp(plane_wp, s, mapper):
    pts, radii = section_vz(s)
    st, segs = round_path([mapper(v, z) for v, z in pts], radii)
    return trace(plane_wp, st, segs)


def straight_wall(s, u0, u1):
    """The top channel's wall + lip as an extrusion along X from u0 to u1, the cap at u0 (it faces the open end) rounded."""
    w = _section_wp(cq.Workplane('YZ', origin=(u0, 0, 0)), s, lambda v, z: (s['yw_t'] - v, z)).extrude(u1 - u0)
    return try_edges(w, lambda q: q.faces('<X').edges(), 'fillet', s['fillet'], 'wall start cap')


def corner_piece(s):
    """The top-right corner: the section revolved 90 degrees about the vertical axis through (cxc, cyc_t), then carried on along the long
    side for `ext` at full height (the stop's contact patch), its end rounded."""
    w = _section_wp(cq.Workplane('YZ', origin=(s['cxc'], 0, 0)), s, lambda v, z: (s['cyc_t'] + s['R_ci'] - v, z))
    rev = w.revolve(90, (s['cyc_t'], 1, 0), (s['cyc_t'], 0, 0))      # +90 about -Z: from +Y round to +X
    if s['ext'] < 0.3:
        return rev
    side = _section_wp(cq.Workplane('XZ', origin=(0, s['cyc_t'], 0)), s, lambda v, z: (s['xs'] - v, z)).extrude(s['ext'])
    side = try_edges(side, lambda q: q.faces('<Y').edges(), 'fillet', s['fillet'], 'extension end')
    return rev.union(side)


# ---- the prong and its ridge -------------------------------------------------------------------------------------

def prong(s, with_ridge=True):
    """The top tab. Outer face flush with the wall's outer face (y = yt_t); the thinning is on the INNER side: the inner face is t_pr in from the
    outer face and ramps back to the full wall over `taper` at the root. Its SIDE outline is a tongue (tongue_outline: the bottom edge rises 45
    degrees from the bed, the top edge drops in a large arc, a round tip), cut from the plan prism; every edge of that outline is rounded (the
    fillet's tangent chain takes the bed foot along with it), and over the taper the foot's round grows into the plate's 0.6 chamfer (chamfer_ramp:
    one smooth transition, no step); the ridge stands on the inner face."""
    yt, yw, tp = s['yt_t'], s['yw_t'], s['t_pr']
    u0, u1 = s['u_tip'] - 1.0, s['u_root']
    z_hi, z_lo = s['z_o'], s['prong_z_lo']
    pts = [(u0, yt), (u1 + 2.0, yt), (u1 + 2.0, yw), (u1, yw), (u1 - s['taper'], yw + tp), (u0, yw + tp)]
    pst, psegs = round_path(pts, [0, 0, 0, s['kink_r'], s['kink_r'], 0])
    plan = trace(cq.Workplane('XY', origin=(0, 0, z_lo)), pst, psegs).extrude(z_hi - z_lo)
    w = plan.intersect(tongue_prism(s, yt + 0.5, yw - 0.5))
    prof = lambda q: q.newObject([e for e in q.edges().vals() if e.Center().z < z_hi - 0.2 and e.Center().x < u1 + 0.6])
    w = guarded(w, try_edges(w, prof, 'fillet', s['prong_top_r'], 'tab outline'), 'tab outline')
    w = w.cut(chamfer_ramp(s))
    return w.union(ridge(s)) if with_ridge else w


def chamfer_ramp(s):
    """The bed chamfer of the tab's outer edge grows from the foot's prong_chamfer to the plate's bed_chamfer over the taper (a plane: a 45-degree
    chamfer of linearly growing size is one), and stays there over the overlap with the plate: no step where the tab meets the plate."""
    yt, zo, e = s['yt_t'], s['z_o'], 0.3
    u0, u1 = s['u_root'] - s['taper'], s['u_root']
    c0, c1 = s['prong_chamfer'], s['bed_chamfer']
    tri = lambda c: [(yt - c - e, zo + e), (yt + e, zo - c - e), (yt + e, zo + e)]
    ramp = (cq.Workplane('YZ', origin=(u0, 0, 0)).polyline(tri(c0)).close().workplane(offset=u1 - u0).polyline(tri(c1)).close().loft(ruled=True))
    flat = cq.Workplane('YZ', origin=(u1, 0, 0)).polyline(tri(c1)).close().extrude(2.3)
    return ramp.union(flat)


def ridge(s):
    """The ridge on the top prong's inner face: the (u, y) profile (ramps 18 / 45 degrees, flat top, base block out to the prong) cut by
    the (y, z) trapezoid (45-degree z ends), edges rounded."""
    yw, b = s['yw_t'], s['b']
    ypi = s['yt_t'] - s['t_pr']                                       # the prong's inner face
    ua, ri, f, rr = s['u_a'], s['r_i'], s['f_top'], s['r_r']
    pts = [(ua, ypi + 0.3), (ua, yw), (ua + ri, yw - b), (ua + ri + f, yw - b), (ua + ri + f + rr, yw), (ua + ri + f + rr, ypi + 0.3)]
    st, segs = round_path(pts, [0.0, s['fillet'], 0.3, 0.3, s['fillet'], 0.0])
    zlo, zhi = s['ridge_z']
    prism = trace(cq.Workplane('XY', origin=(0, 0, zlo - 2.0)), st, segs).extrude(zhi - zlo + 4.0)
    q = ypi + 0.3 - yw                                                # the (y, z) trapezoid: 45 degrees from the tip level out to the prong
    ends = [(ypi + 0.3, zlo - q), (ypi + 0.3, zhi + q), (yw - b, zhi - b), (yw - b, zlo + b)]
    trap = cq.Workplane('YZ', origin=(ua - 1, 0, 0)).polyline(ends).close().extrude(ri + f + rr + 2)
    rd = prism.intersect(trap).intersect(tongue_prism(s, ypi + 0.4, yw - b - 0.5))      # the lead-in shrinks in height with the tab's outline
    sel = lambda w: w.edges(cq.selectors.BoxSelector((ua - 1, yw - b - 0.5, zlo - 3), (ua + ri + f + rr + 1, ypi + 0.1, zhi + 3)))
    return try_edges(rd, sel, 'fillet', s['ridge_r'], 'ridge')


# ---- the plate ---------------------------------------------------------------------------------------------------

def _arc_mid(c, r, a0, a1):
    am = (a0 + a1) / 2
    return (c[0] + r * math.cos(am), c[1] + r * math.sin(am))


def plate_outline_wp(s, z0):
    """The plate's plan outline, counter-clockwise, exact arcs and quintic Bezier curves; on a workplane at z0."""
    xr, yt, yb = s['xr'], s['yt_t'], s['yt_b']
    Ro = s['R_ci'] + s['tw']
    cxc, cyt, cyb = s['cxc'], s['cyc_t'], s['cyc_b']
    ur, ul, uL, uR = s['u_root'], s['u_l'], s['u_L'], s['u_R']
    ype_t, ype_b = s['yw_t'], s['yw_b']                  # the plate's edge beside each tab: the wall's inner plane
    Rt, sw, tap, kr = s['tongue_r_slot'] if s['caps'] else s['tongue_r'], s['slit'], s['taper'], s['kink_r']
    uc = ur + s['slit_flat']                              # the slit's round end: its centre line
    lo, hi, Lt, ext = s['zone_lo'], s['zone_hi'], s['scallop_Lt'], s['ext']
    ya_b, ya_t = s['cyc_b'] + ext, s['cyc_t'] - ext     # where the plate's edge leaves the stop pieces' wall face
    fits = lo - Lt >= ya_b - 0.01 and ya_t >= hi + Lt - 0.01
    assert fits or s['ext_override'] is not None, (lo, hi, Lt, ya_b, ya_t, ext)

    def ease(y0, x0, y1, x1):
        """The quintic smoothstep between two parallel edges as an exact degree-5 Bezier: x = x0 + dx S(t), y linear in t."""
        return [(x0 + (x1 - x0) * k, y0 + (y1 - y0) * i / 5) for i, k in enumerate((0, 0, 0, 1, 1, 1))]

    w = cq.Workplane('XY', origin=(0, 0, z0)).moveTo(uc, yb).lineTo(cxc, yb)
    w = w.threePointArc(_arc_mid((cxc, cyb), Ro, -math.pi / 2, 0.0), (xr, cyb))
    if fits:
        w = w.lineTo(xr, lo - Lt)                                               # the stop piece's wall face, then ease in
        w = w.bezier(ease(lo - Lt, xr, lo, uR))
        w = w.lineTo(uR, hi)
        w = w.bezier(ease(hi, uR, hi + Lt, xr))
    w = w.lineTo(xr, cyt)
    w = w.threePointArc(_arc_mid((cxc, cyt), Ro, 0.0, math.pi / 2), (cxc, yt))
    w = w.lineTo(uc, yt)
    # the notch beside the top prong: down the notch end, round into the plate's edge, along it to the tongue's corner
    w = w.lineTo(uc, ype_t)                                                    # down the end face (hidden: it lies inside the tab's block)
    w = w.threePointArc((uc + sw / 2, ype_t - sw / 2), (uc, ype_t - sw))      # the slit's round end (tangent to the tab's face and to the plate edge)
    a1, m1, b1 = corner((uc, ype_t - sw), (ur, ype_t - sw), (ur - tap, ype_t), kr + sw)       # the plate edge follows the tab's inner face, one slit away
    w = w.lineTo(*a1).threePointArc(m1, b1)
    a2, m2, b2 = corner((ur, ype_t - sw), (ur - tap, ype_t), (ul + Rt, ype_t), kr - sw)
    w = w.lineTo(*a2).threePointArc(m2, b2)
    w = w.lineTo(ul + Rt, ype_t)
    w = w.threePointArc(_arc_mid((ul + Rt, ype_t - Rt), Rt, math.pi / 2, math.pi), (ul, ype_t - Rt))
    if fits:
        w = w.lineTo(ul, hi + Lt)                                               # the leading edge, top to bottom, scalloped
        w = w.bezier(ease(hi + Lt, ul, hi, uL))
        w = w.lineTo(uL, lo)
        w = w.bezier(ease(lo, uL, lo - Lt, ul))
    w = w.lineTo(ul, ype_b + Rt)
    w = w.threePointArc(_arc_mid((ul + Rt, ype_b + Rt), Rt, math.pi, 3 * math.pi / 2), (ul + Rt, ype_b))
    a2, m2, b2 = corner((ul + Rt, ype_b), (ur - tap, ype_b), (ur, ype_b + sw), kr - sw)
    w = w.lineTo(*a2).threePointArc(m2, b2)
    a1, m1, b1 = corner((ur - tap, ype_b), (ur, ype_b + sw), (uc, ype_b + sw), kr + sw)
    w = w.lineTo(*a1).threePointArc(m1, b1)
    w = w.lineTo(uc, ype_b + sw)
    w = w.threePointArc((uc + sw / 2, ype_b + sw / 2), (uc, ype_b))
    return w.close()


def plate(s, relief=True):
    """The plate: outline extruded, bed-face chamfer, the key slots cut (relief=False: nothing cut), then every edge of the inner face (its
    perimeter and the slots' openings) filleted. SOLID over the screen: there is no relief (phase 2, 2026-11-01)."""
    p = plate_outline_wp(s, s['z_i']).extrude(s['tp'])
    p = try_edges(p, lambda q: q.faces('>Z').edges(), 'chamfer', s['bed_chamfer'], 'plate bed chamfer')
    if relief:
        for c in cutters(s):
            p = p.cut(c)
    # the inner face's edges: the plate's perimeter (0.5), then the slots' mouths (what the neighbouring cuts allow)
    ym2 = 2 * s['ym']
    cav = []
    if relief and s['caps']:
        y0 = min(k[2] for k in s['caps']) - s['pocket_y']
        y1 = max(k[3] for k in s['caps']) + s['pocket_y']
        xs1 = max(k[1] for k in s['caps']) + s['pocket_xy'] + s['cx']
        cav = [(s['u_l'] - 2, xs1 + 0.5, y0 - 0.5, y1 + 0.5), (s['u_l'] - 2, xs1 + 0.5, ym2 - y1 - 0.5, ym2 - y0 + 0.5)]

    def in_cav(c):
        return any(a <= c.x <= b and c0 <= c.y <= d for a, b, c0, d in cav)
    perim = lambda q: q.newObject([e for e in q.faces('<Z').edges().vals() if not in_cav(e.Center())])
    mouth = lambda q: q.newObject([e for e in q.faces('<Z').edges().vals() if in_cav(e.Center())])
    p = guarded(p, try_edges(p, perim, 'fillet', s['fillet'], 'plate perimeter, inner face'), 'plate perimeter, inner face')
    if cav:
        p = guarded(p, try_edges(p, mouth, 'fillet', s['fillet'], 'slot mouths'), 'slot mouths')
    if relief and s['caps']:                                 # last, where each slot leaves through the leading edge: its vertical edges
        y0 = min(k[2] for k in s['caps']) - s['pocket_y']
        y1 = max(k[3] for k in s['caps']) + s['pocket_y']
        for a, b in ([(y0, y1), (ym2 - y1, ym2 - y0)] if s['slot_ends'] == 'both' else [(y0, y1)]):
            box = lambda q, a=a, b=b: q.edges(cq.selectors.BoxSelector((s['u_l'] - 0.5, a - 0.5, s['z_i'] + 0.3), (s['u_l'] + 2.0, b + 0.5, s['z_o'] + 0.1), boundingbox=False))
            q = guarded(p, fillet_good(p, box, s['fillet'], 'slot exit'), 'slot exit')
            if q is p:                                       # a 45-degree chamfer meshes where the fillet's patches do not
                q = guarded(p, fillet_good(p, box, 0.4, 'slot exit chamfer', 'chamfer'), 'slot exit chamfer')
            p = q
    return p


def slot_cutter(s, ya, yb, xa, x1, z0, zc):
    """One key slot's cutter: the plan rectangle ya..yb from the leading face to x1 (rounded 1.0 at x1), z0..zc, with its roof FLARED 45
    degrees up over the last roof_flare mm before the leading face (a wedge on the same y span, unioned into one solid): the roof leaves the
    face in a bevel, not a 90-degree edge (a fillet after the cut would not take)."""
    ul, c, e = s['u_l'], s['roof_flare'], 0.3
    st, segs = round_path([(ul + c, ya), (x1, ya), (x1, yb), (ul + c, yb)], [0, 1.0, 1.0, 0])
    body = trace(cq.Workplane('XY', origin=(0, 0, z0)), st, segs).extrude(zc - z0)
    if c <= 0:
        return body
    wedge = [(ul + c, z0), (ul + c, zc), (ul - e, zc + c + e), (xa, zc + c + e), (xa, z0)]
    return body.union(cq.Workplane('XZ', origin=(0, yb, 0)).polyline(wedge).close().extrude(yb - ya))


def cutters(s):
    """The cut into the plate's inner face: with the bottom keys, a key slot at EACH end of the plate that runs out through the leading edge
    (the plate passes over the caps on its way, and the cover turns end for end); without them nothing. The plate is SOLID over the screen
    (phase 2: the relief is gone)."""
    if not s['caps']:
        return []
    z0 = s['z_i'] - 0.1
    ym2 = 2 * s['ym']
    top = max(k[4] for k in s['caps'])
    zc = top + s['key_clr'] + s['gp']
    x1 = max(k[1] for k in s['caps']) + s['pocket_xy'] + s['cx']
    y0 = min(k[2] for k in s['caps']) - s['pocket_y']
    y1 = max(k[3] for k in s['caps']) + s['pocket_y']
    xa = s['u_l'] - 1.0
    out = [slot_cutter(s, y0, y1, xa, x1, z0, zc)]
    if s['slot_ends'] == 'both':                         # (the deliberately wrong one-ended cover has the bottom slot only)
        out.append(slot_cutter(s, ym2 - y1, ym2 - y0, xa, x1, z0, zc))
    return out


def logo_polys(s):
    """The case's back logos in the cover's design frame: the cover on the back at home must sit exactly over the case's own logo, so the
    cover's polygon is the case's mirrored about the centre line (x -> 2 xc - x) and moved by the stop gap (home: x = u - cx).
    {'icon': (polygon, depth), 'wordmark': (polygon, depth)}"""
    out = {}
    for name in ('icon', 'wordmark'):
        d = s['logos'][name]
        g = sa.scale(wkt.loads(d['wkt']), xfact=-1.0, yfact=1.0, origin=(s['xc'], 0))
        out[name] = (sa.translate(g, xoff=s['cx'], yoff=0.0), d['depth'])
    return out


def plate_polygon(s):
    """The plate's plan outline as a shapely polygon (design frame): the exact outline wire sampled every 0.1 mm."""
    import shapely
    wire = plate_outline_wp(s, 0.0).val()
    n = int(wire.Length() / 0.1)
    return shapely.Polygon([wire.positionAt(k / n).toTuple()[:2] for k in range(n)]).buffer(0)


def border_polys(s):
    """The two border grooves as shapely geometry (design frame): each is the plate's outline moved in by border_insets, its corners rounded to
    border_r (opening and closing), made border_w wide; whatever lies within border_clr of a logo is cut away (the lines give way, the logos
    do not). {inset: geometry}"""
    import shapely
    from shapely.ops import unary_union
    plate = plate_polygon(s)
    logos = unary_union([g for g, _ in logo_polys(s).values()]).buffer(s['border_clr'])
    out = {}
    r = s['border_r']
    for d in s['border_insets']:
        line = plate.buffer(-d).buffer(-r).buffer(r).buffer(r).buffer(-r)          # in by d, then convex and concave corners rounded to r
        ring = line.buffer(s['border_w'] / 2).difference(line.buffer(-s['border_w'] / 2))
        ring = ring.difference(logos).buffer(-0.12).buffer(0.12).simplify(0.008)    # clear of the logos; the cut ends rounded; 8 microns of chord
        out[d] = ring
    return out


def border_cutter(s):
    zo, depth = s['z_o'], s['border_depth']
    from shapely.ops import unary_union
    return _prisms(unary_union(list(border_polys(s).values())), zo - depth, zo + 0.2)


def _prisms(g, z0, z1):
    faces = []
    for p in getattr(g, 'geoms', [g]):
        if p.area < 0.02:
            continue
        outer = cq.Wire.makePolygon([cq.Vector(x, y, z0) for x, y in p.exterior.coords[:-1]], close=True)
        inner = [cq.Wire.makePolygon([cq.Vector(x, y, z0) for x, y in r.coords[:-1]], close=True) for r in p.interiors]
        faces.append(cq.Face.makeFromWires(outer, inner))
    return cq.Workplane(obj=cq.Compound.makeCompound([cq.Solid.extrudeLinear(f, cq.Vector(0, 0, z1 - z0)) for f in faces]))


def logo_cutter(s, name):
    g, depth = logo_polys(s)[name]
    return _prisms(g, s['z_o'] - depth, s['z_o'] + 0.2)


def logo_inlay(s, name):
    """The body that exactly fills one engraving (the two-colour switch): from the outer face down by the engraving's depth."""
    g, depth = logo_polys(s)[name]
    return _prisms(g, s['z_o'] - depth, s['z_o'])


# ---- the whole cover ---------------------------------------------------------------------------------------------

def mirror_y(wp, s):
    return wp.mirror('XZ', (0, s['ym'], 0))


def build(s, ridge_on=True, relief=True):
    """The whole cover in the design frame. ridge_on=False: the rigid frame (check.py moves it and tests the ridge by its own deflection);
    relief=False: no slots or logos (the plain plate)."""
    NOTES.clear()
    body = plate(s, relief)
    top = straight_wall(s, s['u_root'], s['u_cs']).union(corner_piece(s))
    body = body.union(top).union(mirror_y(top, s))
    pr = prong(s, ridge_on)
    body = body.union(pr).union(mirror_y(pr, s))
    if relief and s['logo']:
        for name in ('icon', 'wordmark'):
            body = body.cut(logo_cutter(s, name))
    if relief and s['border']:
        body = body.cut(border_cutter(s))
    return body


def to_print_frame(shape, ref=None):
    """Plate face down: rotate 180 degrees about Y (x -> -x, z -> -z), then the min corner of `ref` (default the shape) to the origin."""
    r = shape.rotate((0, 0, 0), (0, 1, 0), 180)
    bb = (ref.rotate((0, 0, 0), (0, 1, 0), 180) if ref is not None else r).val().BoundingBox()
    return r.translate((-bb.xmin, -bb.ymin, -bb.zmin))
