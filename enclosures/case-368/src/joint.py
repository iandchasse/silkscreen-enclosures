"""Tub-to-lid joint: a continuous tongue on the TUB into a closed groove in the lid, plus thirteen
snap latches.

Rev F had it the other way round - a tongue on the lid rising into a rebate cut in the tub's wall -
and that is why it could not run where it was needed. At a button tab the tub's side wall is only
the outer flexure tab, because the inner part has to be cut away for the tab to swing, so there was
no wall left to cut a rebate in. Over 79 mm of the right wall and 46 mm of the left, nothing held
the parting line at all.

Rev G's wall keeps a continuous inner sliver (params.SLIVER) behind every tab, and the tongue is
simply that sliver carried on below the parting plane. The lid's rim is rebuilt around it:

    lip            groove            leg
  |======|      |          |      |==========|      (looking along the wall, inside on the left)
  d -1.0    -0.15 |tongue| 0.95              2.7+
                  |  0..0.8   |

The leg is the old rim carried inward; the lip is new and grows into the cavity. On the side walls
the lip has to duck under the side switches, whose bodies reach z -4.493 and x 61.185, so it only
stands full height clear of them - 1.40 mm of tongue engaged over most of each wall, 0.45 mm
alongside a switch. The groove needs no cutter: it is simply the gap left between lip and leg, and
its floor is the lid's own cavity floor.

The tongue is interrupted only where a side key's nub crosses the sliver, and on the right by the
USB port.

Rev I latches. Rev G/H had eleven, and Ian found they did not hold. Eight of them hooked the sliver
where a button tab's void stood right behind it, so the barb just bowed that 0.8 mm skin out of its
way, and each caught only 0.2 mm. Now every pocket sits above the side keys' slots, where the wall
behind the sliver is solid, and is 0.6 deep; the barb catches 0.45. The arms are 7 mm tall to reach
it, which also keeps their bending strain low, and the midplate's edge is notched where their tips
pass it.
"""
import math
import params as P
import hw
import body
from geom import box, xz_prism, yz_prism, zcyl

PCB = hw.bounds('PCB')
LOW_X0 = P.WALL_X0                           # the tub's side walls' inner faces below the panel (as tub.py)
LOW_X1 = P.WALL_X1

# inner face of each wall at the parting plane, which way is out, and the wall's thickness
WALLS = {
    'left': dict(axis='y', face=LOW_X0, out=-1, t=P.SIDE_WALL),
    'right': dict(axis='y', face=LOW_X1, out=+1, t=P.SIDE_WALL),
    'top': dict(axis='x', face=P.TOP_IN, out=+1, t=P.TOP_WALL),
}
SW_LIP_TOP = -4.70                           # under the side switches' bodies (-4.493), with 0.2 to spare
SW_CLR = 0.5                                 # how far past a switch body the lip stays low


def _prism(wall, a0, a1, pts):
    """Prism on a wall: profile [(d, z), ...] with d measured outward from the inner face
    (negative = into the cavity), extruded along the wall from a0 to a1."""
    w = WALLS[wall]
    prof = [(w['face'] + w['out'] * d, z) for d, z in pts]
    return xz_prism(prof, a0, a1) if w['axis'] == 'y' else yz_prism(prof, a0, a1)


def _box(wall, a0, a1, d0, d1, z0, z1):
    return _prism(wall, a0, a1, [(d0, z0), (d1, z0), (d1, z1), (d0, z1)])


def _minus(segs, holes):
    """Subtract a list of (lo, hi) from a list of (a0, a1)."""
    for lo, hi in holes:
        nxt = []
        for a0, a1 in segs:
            if a1 <= lo or a0 >= hi:
                nxt.append((a0, a1))
                continue
            if a0 < lo:
                nxt.append((a0, lo))
            if a1 > hi:
                nxt.append((hi, a1))
        segs = nxt
    return segs


def nub_windows():
    """Y spans where a side key's nub crosses the sliver, per wall: the tongue cannot run there."""
    out = {'left': [], 'right': [], 'top': []}
    for t in body.side_tabs():
        w = body.tab_window(t)
        out['right' if t['side'] > 0 else 'left'].append((w['y'][0] - 0.1, w['y'][1] + 0.1))
    return out


def runs():
    """Tongue segments per wall: the declared free runs minus the nub windows. Short leftovers
    are dropped. Latches do NOT interrupt the tongue - their pockets are cut into the sliver's
    inner face, which is not where the tongue is."""
    win = nub_windows()
    out = {}
    for wall, spans in P.TONGUE_RUNS.items():
        segs = _minus([tuple(s) for s in spans], sorted(win.get(wall, [])))
        out[wall] = [(a, b) for a, b in segs if b - a >= P.JOINT['min_run']]
    return out


def switch_spans(wall):
    """Y spans on a side wall where the lid's inner lip has to stay below the switch bodies."""
    if wall == 'top':
        return []
    side = 1 if wall == 'right' else -1
    out = []
    for t in body.side_tabs():
        if t['side'] != side:
            continue
        b0, b1 = t['body_y']
        out.append((b0 - SW_CLR, b1 + SW_CLR))
    return sorted(out)


def tongue_profile():
    """(d, z) of the tub's tongue: the sliver carried JOINT['h'] below the parting plane, with a
    45-degree lead on both faces at its tip. It prints last, at the very top of the face-down tub,
    and both lead faces point away from the bed."""
    J = P.JOINT
    t, h, ld = J['t'], J['h'], J['lead']
    z0, z1 = P.SEAM, P.SEAM - h
    return [(0.0, z0), (t, z0), (t, z1 + ld), (t - ld, z1), (ld, z1), (0.0, z1 + ld)]


def snap_profile(chamfer=None, phase=None):
    """Latch arm profile (d, z) on the lid, d outward from the wall's inner face.
    Returns the points and the key heights. The barb's retaining face is 45 degrees (it prints as an
    overhang on the lid and its pocket as a roof in the face-down tub); its lead-in is SNAP['lead_deg'].
    chamfer=(h, v): the arm's inner top corner cut off, h along the top toward the barb and v down the inner face
    (light strip: the Y-83 arm only, params.SNAP_INNER_CHAMFER). The barb's points are the same either way.
    phase: the barb's shift from SNAP['catch'], params.LATCH_PHASE (the lid's barb as built) unless given;
    pocket_profile takes the pocket's catch line at phase 0."""
    S = P.SNAP
    g, b = S['gap'], S['barb']
    z_c = S['catch'] + (P.LATCH_PHASE if phase is None else phase)   # bottom of the flat
    z_flat = z_c + S['flat']                                     # top of the flat
    z_top = z_flat + b / math.tan(math.radians(S['lead_deg']))
    z_root = P.LATCH_ROOT_Z                                      # on its pedestal (lid_adds) since LID_DROP
    pts = [(-g, z_root), (-g, z_c - b), (-g + b, z_c), (-g + b, z_flat), (-g, z_top),
           (-g - S['t_tip'], z_top)]
    if S.get('mid'):                       # thick only below the board (params.SNAP): the inner face's kink (z, thickness)
        pts.append((-g - S['mid'][1], S['mid'][0]))
    pts.append((-g - S['t_root'], z_root))
    h = {'z_top': z_top, 'z_flat': z_flat, 'z_c': z_c, 'z_root': round(z_root + 0.1, 3), 'catch_low': z_c - b}
    if chamfer:
        ch, cv = chamfer
        (d5, z5), (d6, z6) = pts[5], pts[6]                     # inner top corner; the inner face runs down to the root
        assert 0 < ch <= S['t_tip'] - 0.2 + 1e-9 and z5 - cv > z_flat, chamfer   # a flat stays on top; clear of the barb
        zc = z5 - cv
        dc = d5 + (d6 - d5) * (z5 - zc) / (z5 - z6)             # on the (tapered) inner face
        pts = pts[:5] + [(d5 + ch, z5), (dc, zc)] + pts[6:]
        h['chamfer'] = {'h': ch, 'v': cv, 'z_low': zc, 'flat_on_top': round(S['t_tip'] - ch, 3)}
    return pts, h


def pocket_profile():
    """Pocket in the wall's inner face for a latch barb, SNAP['pocket'] deep, with a 45-degree catch
    face 0.1 mm below the return face of a barb at SNAP['catch'] with the lid at its CAD position (since 2026-10-13
    the barb is drawn params.LATCH_PHASE lower, so that the two meet at the lid's as-printed home). Rev I: it starts
    above the side keys' slots (TAB_Z[1] + TAB_SLOT_CLR), so there is solid wall behind it wherever it is."""
    S = P.SNAP
    g, b = S['gap'], S['barb']
    _, h = snap_profile(phase=0.0)                                # the pocket's catch line (the barb: LATCH_PHASE under)
    tip = S['pocket']
    z0 = h['z_c'] - b + g - 0.1                                   # catch line meets the wall face
    assert z0 > P.TAB_Z[1] + P.TAB_SLOT_CLR + 0.1, z0
    return [(-0.4, z0 - 0.4), (tip, z0 + tip), (tip, h['z_top'] + 0.15), (-0.4, h['z_top'] + 0.15)]


def latch_spans(wall):
    """(centre, width) of each latch on a wall."""
    return [(c, P.SNAP['w']) for c in P.SNAPS.get(wall, [])]


def tub_adds():
    """The tongues."""
    prof = tongue_profile()
    return [_prism(wall, a0, a1, prof) for wall, segs in runs().items() for a0, a1 in segs]


def tub_cuts():
    """Barb pockets in the sliver's inner face, and the tongue's notch over the gate slot's cavity (params GATE_SLOT;
    SPEC2 rev 3): the cavity's footprint, round ends and all, cut up through the tongue, so the tongue's outer face
    steps from X -2.34 to -2.19 over the cavity (y -4.35..-0.65) and follows the ends' arcs out to y -4.66 / -0.34.
    TONGUE_RUNS and the lid's groove are unchanged."""
    out = []
    for wall, cs in P.SNAPS.items():
        for c, w in latch_spans(wall):
            out.append(_prism(wall, c - w / 2 - 0.3, c + w / 2 + 0.3, pocket_profile()))
    S = P.GATE_SLOT
    _, xl, xc = P.GATE_SLOT_X
    (c0, c1), r = S['cavity'], S['end_r']
    z0, z1 = P.SEAM - P.JOINT['h'] - 0.5, P.SEAM + 0.01
    notch = box(xl, xc, c0, c1, z0, z1)
    for yc in (c0, c1):
        notch = notch.union(zcyl(xl + r, yc, z0, z1, 2 * r))
    out.append(notch)
    return out


def lid_adds():
    """The rim's outer leg, the inner lip, and the latch arms."""
    J, S = P.JOINT, P.SNAP
    clr, lip, mouth = J['clr'], J['lip'], J['mouth']
    z_root = P.LID_FLOOR_IN - 0.1
    adds = []
    for wall, segs in runs().items():
        w = WALLS[wall]
        d_leg = J['t'] + clr
        leg = [(d_leg + mouth, P.SEAM), (d_leg, P.SEAM - mouth), (d_leg, z_root),
               (w['t'] + 0.5, z_root), (w['t'] + 0.5, P.SEAM)]
        holes = [(c - wd / 2 - 1.0, c + wd / 2 + 1.0) for c, wd in latch_spans(wall)]
        for a0, a1 in segs:
            adds.append(_prism(wall, a0, a1, leg))
        # the lip: full height clear of the side switches, ducking under them where they reach out
        low = switch_spans(wall)
        full = _minus(_minus(segs, low), holes)
        ducked = _minus([s for s in _overlaps(segs, low)], holes)
        for a0, a1 in full:
            adds.append(_prism(wall, a0, a1, _lip_profile(P.SEAM, clr, lip, mouth, z_root)))
        for a0, a1 in ducked:
            adds.append(_prism(wall, a0, a1, _lip_profile(SW_LIP_TOP, clr, lip, mouth, z_root)))
    for wall, cs in P.SNAPS.items():
        for c, w in latch_spans(wall):
            pts, _ = snap_profile(P.SNAP_INNER_CHAMFER.get((wall, c)))
            adds.append(_prism(wall, c - w / 2, c + w / 2, pts))
            # LID_DROP: the arm stands on a pedestal as wide as it, from the (lower) floor up to its old root, run
            # out to the rim's leg across the groove's floor (the tongue's tip stays 0.98 above it), so the arm's
            # root is as stiff as before and its length, forces and strain are unchanged (mechanics.latches)
            if P.LATCH_ROOT_Z > z_root + 1e-6:
                adds.append(_box(wall, c - w / 2, c + w / 2, -S['gap'] - S['t_root'], J['t'] + clr + 0.5, z_root,
                                 P.LATCH_ROOT_Z + 0.01))
    return adds


def _lip_profile(top, clr, lip, mouth, z_root):
    m = min(mouth, max(0.0, (top - z_root) - 0.3))
    return [(-clr, z_root), (-clr, top - m), (-clr - m, top), (-clr - lip, top), (-clr - lip, z_root)]


def _overlaps(segs, holes):
    """The parts of segs that DO fall inside holes."""
    out = []
    for a0, a1 in segs:
        for lo, hi in holes:
            b0, b1 = max(a0, lo), min(a1, hi)
            if b1 - b0 > 0.05:
                out.append((b0, b1))
    return out


def lid_cuts():
    """Nothing since Rev I: the side keys stand TAB_Z[0] - SEAM clear of the rim, so it needs no
    relief under them (Rev G/H cut one for the tabs, which flexed down to d = SLIVER)."""
    return []


def midplate_notches():
    """(wall, y0, y1) spans where the midplate's edge steps back SNAP['notch'] for a latch arm's tip,
    which stands above the midplate's rear face."""
    S = P.SNAP
    return [(wall, c - S['w'] / 2 - 0.3, c + S['w'] / 2 + 0.3) for wall in ('left', 'right', 'top')
            for c in P.SNAPS.get(wall, [])]


def summary():
    """Numbers for the report and the page."""
    J, S = P.JOINT, P.SNAP
    r = runs()
    total = sum(a1 - a0 for segs in r.values() for a0, a1 in segs)
    _, h = snap_profile()
    gaps = {}
    for wall in ('left', 'right'):
        segs = sorted(r.get(wall, []))
        anchors = sorted([a for s in segs for a in s] + [c for c, _ in latch_spans(wall)])
        gaps[wall] = round(max((b - a for a, b in zip(anchors, anchors[1:])), default=0.0), 1)
    return {'scheme': 'tub tongue into a closed lid groove',
            'runs': {w: [[round(a, 2), round(b, 2)] for a, b in s] for w, s in r.items()},
            'tongue_len': round(total, 1), 'tongue_t': J['t'], 'tongue_h': J['h'], 'clr': J['clr'],
            'lip': J['lip'], 'lip_top': {'clear_of_switches': P.SEAM, 'alongside': SW_LIP_TOP},
            'engage_mm': {k: round(min(J['h'], max(0.0, top - (P.SEAM - J['h']))), 2)
                          for k, top in (('clear_of_switches', P.SEAM), ('alongside', SW_LIP_TOP))},
            'end_clr': J['end_clr'], 'snaps': {k: list(v) for k, v in P.SNAPS.items()}, 'snap': S,
            'snap_z': {k: round(v, 3) for k, v in h.items()},
            'engage': round(S['barb'] - S['gap'], 2), 'latch_count': sum(len(v) for v in P.SNAPS.values()),
            'inner_top_chamfer': {f'{w} Y{c:g}': list(v) for (w, c), v in P.SNAP_INNER_CHAMFER.items()},
            'pocket': S['pocket'], 'catch_z': S['catch'], 'barb_phase': P.LATCH_PHASE, 'longest_gap_mm': gaps}


if __name__ == '__main__':
    import json
    print(json.dumps(summary(), indent=1))
