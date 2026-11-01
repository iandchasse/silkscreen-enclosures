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
    prong_top_r=0.38,  # the prong's free end: 0.8 thick, so a full round
    ridge_r=0.45,     # the ridge's edges (ramp-to-flat bends are 18 and 45 degrees: this moves the surface < 0.02)
    tongue_r=3.0,     # plan radius of the open-end corners of the plate
    tongue_r_slot=1.5,  # ... where the key slot leaves through the leading edge (3.0 would put the slot's wall through the corner round)
    kerf_r=1.0,       # plan radius at the end of the notch beside each prong
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
    relief_xy=1.2,    # screen relief past the window's box (and its mirror: the cover turns end for end)
    web=1.2,          # plate thickness over the relief: >= this (six layers)
    pocket_roof=1.2,  # thinnest plate over a key slot (six layers): the bed chamfer (0.6) and the slot-mouth fillet (0.5) both end there
    slot_ends='both',  # 'both' (round 2) or 'bottom' (the deliberately wrong one-ended cover)
    logo=True,        # engrave the case's back logos in the outer face
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
        s['tp'] = s.get('tp') or 1.8
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
    s['u_tip'] = s['u_a'] - 0.5
    s['u_root'] = s['u_t'] - s['f_top'] / 2 + s['L_pr']
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


def trace(wp, start, segs):
    wp = wp.moveTo(*start)
    for sg in segs:
        wp = wp.lineTo(*sg[1]) if sg[0] == 'line' else wp.threePointArc(sg[1], sg[2])
    return wp.close()


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
    """The top prong. Outer face flush with the wall's outer face (y = yt_t); the thinning is on the INNER side: the inner face is t_pr in
    from the outer face and ramps back to the full wall over `taper` at the root. A plan semicircle for the tip; the top face is rounded
    and the bed foot chamfered; the ridge stands on the inner face (its base block carries the working geometry out to the tip level)."""
    yt, yw, tp = s['yt_t'], s['yw_t'], s['t_pr']
    r = tp / 2
    u0, u1 = s['u_tip'], s['u_root']
    z_hi, z_lo = s['z_o'], s['prong_z_lo']
    w = (cq.Workplane('XY', origin=(0, 0, z_lo)).moveTo(u0 + r, yt).threePointArc((u0, yt - r), (u0 + r, yt - tp))
         .lineTo(u1 - s['taper'], yt - tp).lineTo(u1, yw).lineTo(u1 + 1.0, yw).lineTo(u1 + 1.0, yt).close().extrude(z_hi - z_lo))
    w = try_edges(w, lambda q: q.faces('<Z').edges(), 'fillet', s['prong_top_r'], 'prong top')
    foot = lambda q: q.faces('>Z').edges(cq.selectors.BoxSelector((u0 - 1, yw - 1, z_hi - 0.05), (u1 - 0.2, yt + 1, z_hi + 0.05)))
    w = try_edges(w, foot, 'chamfer', s['prong_chamfer'], 'prong foot')
    return w.union(ridge(s)) if with_ridge else w


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
    rd = prism.intersect(trap)
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
    ype_t, ype_b = s['yw_t'], s['yw_b']                  # the plate's edge beside each prong: the wall's inner plane
    Rt, Rk = s['tongue_r_slot'] if s['caps'] else s['tongue_r'], s['kerf_r']
    lo, hi, Lt, ext = s['zone_lo'], s['zone_hi'], s['scallop_Lt'], s['ext']
    ya_b, ya_t = s['cyc_b'] + ext, s['cyc_t'] - ext     # where the plate's edge leaves the stop pieces' wall face
    fits = lo - Lt >= ya_b - 0.01 and ya_t >= hi + Lt - 0.01
    assert fits or s['ext_override'] is not None, (lo, hi, Lt, ya_b, ya_t, ext)

    def ease(y0, x0, y1, x1):
        """The quintic smoothstep between two parallel edges as an exact degree-5 Bezier: x = x0 + dx S(t), y linear in t."""
        return [(x0 + (x1 - x0) * k, y0 + (y1 - y0) * i / 5) for i, k in enumerate((0, 0, 0, 1, 1, 1))]

    w = cq.Workplane('XY', origin=(0, 0, z0)).moveTo(ur, yb).lineTo(cxc, yb)
    w = w.threePointArc(_arc_mid((cxc, cyb), Ro, -math.pi / 2, 0.0), (xr, cyb))
    if fits:
        w = w.lineTo(xr, lo - Lt)                                               # the stop piece's wall face, then ease in
        w = w.bezier(ease(lo - Lt, xr, lo, uR))
        w = w.lineTo(uR, hi)
        w = w.bezier(ease(hi, uR, hi + Lt, xr))
    w = w.lineTo(xr, cyt)
    w = w.threePointArc(_arc_mid((cxc, cyt), Ro, 0.0, math.pi / 2), (cxc, yt))
    w = w.lineTo(ur, yt)
    # the notch beside the top prong: down the notch end, round into the plate's edge, along it to the tongue's corner
    w = w.lineTo(ur, ype_t + Rk)
    w = w.threePointArc(_arc_mid((ur - Rk, ype_t + Rk), Rk, 0.0, -math.pi / 2), (ur - Rk, ype_t))
    w = w.lineTo(ul + Rt, ype_t)
    w = w.threePointArc(_arc_mid((ul + Rt, ype_t - Rt), Rt, math.pi / 2, math.pi), (ul, ype_t - Rt))
    if fits:
        w = w.lineTo(ul, hi + Lt)                                               # the leading edge, top to bottom, scalloped
        w = w.bezier(ease(hi + Lt, ul, hi, uL))
        w = w.lineTo(uL, lo)
        w = w.bezier(ease(lo, uL, lo - Lt, ul))
    w = w.lineTo(ul, ype_b + Rt)
    w = w.threePointArc(_arc_mid((ul + Rt, ype_b + Rt), Rt, math.pi, 3 * math.pi / 2), (ul + Rt, ype_b))
    w = w.lineTo(ur - Rk, ype_b)
    w = w.threePointArc(_arc_mid((ur - Rk, ype_b - Rk), Rk, math.pi / 2, 0.0), (ur, ype_b - Rk))
    return w.close()


def plate(s, relief=True):
    """The plate: outline extruded, bed-face chamfer, the screen relief and the key slots cut, then every edge of the inner face (its
    perimeter and the slots' and the relief's openings) filleted."""
    p = plate_outline_wp(s, s['z_i']).extrude(s['tp'])
    p = try_edges(p, lambda q: q.faces('>Z').edges(), 'chamfer', s['bed_chamfer'], 'plate bed chamfer')
    if relief:
        for c in cutters(s):
            p = p.cut(c)
    # the inner face's edges: the plate's perimeter (0.5), then the relief's and the slots' mouths (what the neighbouring cuts allow)
    ym2 = 2 * s['ym']
    wx0, wx1, wy0, wy1 = s['window']
    rr = s['relief_xy'] + 0.5
    cav = [(wx0 - rr, wx1 + rr, min(wy0, ym2 - wy1) - rr, max(wy1, ym2 - wy0) + rr)] if relief else []

    def in_cav(c):
        return any(a <= c.x <= b and c0 <= c.y <= d for a, b, c0, d in cav)
    if relief and s['caps']:
        y0 = min(k[2] for k in s['caps']) - s['pocket_y']
        y1 = max(k[3] for k in s['caps']) + s['pocket_y']
        xs1 = max(k[1] for k in s['caps']) + s['pocket_xy'] + s['cx']
        cav += [(s['u_tip'] - 2, xs1 + 0.5, y0 - 0.5, y1 + 0.5), (s['u_tip'] - 2, xs1 + 0.5, ym2 - y1 - 0.5, ym2 - y0 + 0.5)]
    perim = lambda q: q.newObject([e for e in q.faces('<Z').edges().vals() if not in_cav(e.Center())])
    mouth = lambda q: q.newObject([e for e in q.faces('<Z').edges().vals() if in_cav(e.Center())])
    p = guarded(p, try_edges(p, perim, 'fillet', s['fillet'], 'plate perimeter, inner face'), 'plate perimeter, inner face')
    if cav:
        p = guarded(p, try_edges(p, mouth, 'fillet', s['fillet'], 'relief and slot mouths'), 'relief and slot mouths')
    if relief and s['caps']:                                 # last, where each slot leaves through the leading edge: the vertical and the roof edges
        ym2 = 2 * s['ym']
        y0 = min(k[2] for k in s['caps']) - s['pocket_y']
        y1 = max(k[3] for k in s['caps']) + s['pocket_y']
        for a, b in ([(y0, y1), (ym2 - y1, ym2 - y0)] if s['slot_ends'] == 'both' else [(y0, y1)]):
            box = lambda q, a=a, b=b: q.edges(cq.selectors.BoxSelector((s['u_l'] - 0.5, a - 0.5, s['z_i'] + 0.3), (s['u_l'] + 2.0, b + 0.5, s['z_o'] + 0.1), boundingbox=False))
            q = guarded(p, fillet_good(p, box, s['fillet'], 'slot exit'), 'slot exit')
            if q is p:                                       # a 45-degree chamfer meshes where the fillet's patches do not
                q = guarded(p, fillet_good(p, box, 0.4, 'slot exit chamfer', 'chamfer'), 'slot exit chamfer')
            p = q
            if SECOND_PASS:
                p = fillet_good(p, box, SECOND_PASS, 'slot exit, the rest')
    return p


def _rbox(x0, x1, y0, y1, z0, z1, r):
    """A box with its vertical edges rounded to r (a plan-rounded cutter)."""
    b = _box(x0, x1, y0, y1, z0, z1)
    try:
        return b.edges('|Z').fillet(min(r, (x1 - x0) / 2 - 0.01, (y1 - y0) / 2 - 0.01))
    except Exception:
        return b


def cutters(s):
    """The cut into the plate's inner face: ONE cavity, as deep as the slot needs. With the bottom keys it is the screen relief (the window
    and its mirror about the mid-length: the cover turns end for end) joined to a key slot at EACH end of the plate that runs out through
    the leading edge (the plate passes over the caps on its way, and the cover turns end for end); without them just the relief. The
    outline is one rounded polygon (exact arcs), so there are no cusps where the slot meets the relief."""
    z0 = s['z_i'] - 0.1
    ym2 = 2 * s['ym']
    wx0, wx1, wy0, wy1 = s['window']
    r = s['relief_xy']
    if not s['caps']:
        depth = s['tp'] - s['web']
        if depth <= 0.05:
            return []
        return [_rbox(wx0 - r, wx1 + r, min(wy0, ym2 - wy1) - r, max(wy1, ym2 - wy0) + r, z0, s['z_i'] + depth, 3.0)]
    top = max(k[4] for k in s['caps'])
    zc = top + s['key_clr'] + s['gp']
    x1 = max(k[1] for k in s['caps']) + s['pocket_xy'] + s['cx']
    y0 = min(k[2] for k in s['caps']) - s['pocket_y']
    y1 = max(k[3] for k in s['caps']) + s['pocket_y']
    xa = s['u_tip'] - 1.0
    rx0, rx1 = wx0 - r, wx1 + r
    ya, yb = ym2 - y0, ym2 - y1                          # the top slot's outer and inner walls
    if s['slot_ends'] == 'both':
        pts = [(xa, y0), (x1, y0), (x1, y1), (rx1, y1), (rx1, yb), (x1, yb), (x1, ya), (xa, ya), (xa, yb), (rx0, yb), (rx0, y1), (xa, y1)]
        rc = max(0.3, min(3.0, rx1 - x1 - 1.4))        # the relief's corners: R3 where the slot's concave round leaves room
        rad = [0, 1.0, 1.0, rc, rc, 1.0, 1.0, 0, 0, 1.0, 1.0, 0]
    else:                                                # the deliberately wrong one-ended cover: the relief up to its own top edge
        ytop = max(wy1, ym2 - wy0) + r
        pts = [(xa, y0), (x1, y0), (x1, y1), (rx1, y1), (rx1, ytop), (rx0, ytop), (rx0, y1), (xa, y1)]
        rad = [0, 1.0, 1.0, 3.0, 3.0, 3.0, 1.0, 0]
    st, segs = round_path(pts, rad)
    return [trace(cq.Workplane('XY', origin=(0, 0, z0)), st, segs).extrude(zc - z0)]


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
    relief=False: no slots, screen relief or logos (the plain plate)."""
    NOTES.clear()
    body = plate(s, relief)
    top = straight_wall(s, s['u_root'], s['u_cs']).union(corner_piece(s))
    body = body.union(top).union(mirror_y(top, s))
    pr = prong(s, ridge_on)
    body = body.union(pr).union(mirror_y(pr, s))
    if relief and s['logo']:
        for name in ('icon', 'wordmark'):
            body = body.cut(logo_cutter(s, name))
    return body


def to_print_frame(shape, ref=None):
    """Plate face down: rotate 180 degrees about Y (x -> -x, z -> -z), then the min corner of `ref` (default the shape) to the origin."""
    r = shape.rotate((0, 0, 0), (0, 1, 0), 180)
    bb = (ref.rotate((0, 0, 0), (0, 1, 0), 180) if ref is not None else r).val().BoundingBox()
    return r.translate((-bb.xmin, -bb.ymin, -bb.zmin))
