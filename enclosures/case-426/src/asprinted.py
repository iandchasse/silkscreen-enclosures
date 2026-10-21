"""As-printed read-backs of the closed case (2026-10-13, the x3 round): the tub, the lid and the midplate as sliced
(slice_check's slices, the CC2 presets), each layer's lines at their widths turned back into the CAD frame, and put
together where they really meet, which is not where the CAD puts them. slice_check runs them on every build; FAIL on
any makes slice_check exit 1.

  home      where the lid comes to rest pressed onto the tub. The slicer keeps a layer only if its mid-plane is inside
            the part, so the lid's rim and the tub's rim each print a little short of the parting plane, and so do the
            lid's board posts and the tub's bosses: the lid sits forward of CAD by the smaller of the two gaps (the
            3.68: 0.105 both ways, params.LID_HOME_DZ; the 4.26: -0.100, 0.1 behind it). Read at the rims and at the
            H3/H4 posts and bosses with a PCB_T board.
  board     (3.68, 2026-10-20) the room between the board and the tub's H3/H4 bosses with the lid at home: the bosses'
            faces less the lid's posts' tops (both as printed, the lid forward by `dz`) less the board. FAIL if the
            room with a board BOARD_PLUS (0.16, +10 %) thicker is under BOARD_ROOM_MIN (0.20): the board is then
            clamped between the lid and the tub 8.25 above the bottom screws, with no screw through it, and any
            extra thickness levers the lid open along its long sides. (main a55c3b1: 0.000 room, FAIL.)
  screws    every screw in params.SCREWS: in the lid, each head's seat (HEADS: the first layer over the counterbore
            that the head cannot pass, for a socket head cap and for a pan head) and the clearance hole; in the tub,
            the pilot's mouth (where the screw first meets plastic), its end (the solid cap in front of it), its laid
            diameter, and the front face. The parts list's screw (SCREW_L, under the head) on its seat with the lid at
            home: FAIL if a head stands proud of the lid's back as laid (its first layer's bed face), if it has less
            than SCREW_MIN_IN in the hole (at home and with SCREW_STANDOFF of the lid left open; from the shallower
            seat), if its tip is past the hole's end (it would drill the cap) or nearer the face than SCREW_FACE_MIN
            (from the deeper seat), or if the pilot is laid wider than SCREW_PILOT_MAX. (2026-10-13: the 3.68's bottom
            pair at H3/H4 had 2.0 mm in the hole, which no check read; they never bit. The same day Ian's screws
            turned out to be socket heads, which stood 0.2 proud of the 4.26's 1.8 deep counterbores.)
  overlap   the lid at home against the tub, and against the midplate on a nominal panel and on the thickest
            (PANEL_T_TOL: the plate sits that much nearer the lid). Two layers that share more than Z_SHARED of Z may
            not share more than OVERLAP_MM2 of plan: FAIL on any. Also the least Z gap from the lid up to the midplate
            (the backstops and the top rib, which printed 0.065 proud of their CAD top and met the plate first).
  latches   each latch's barb (lid) and pocket (tub) in the plane through its centre and LATCH_OFFSETS either side,
            as printed: the lift from home before a barb step meets a pocket step, its dead band; FAIL above
            LATCH_PLAY_MAX, or if a barb overlaps its pocket's wall at home (it could not drop in).

The checks take each part as a list of layers [(zc, polygon)] in the CAD frame (slice_check.device_layers), so they
can be fed any slice (the 4.26's too: the screws and the latches need only its frames and its params' numbers). The
4.26 has the same module (case-426/src/asprinted.py, kept identical to this one): its slice_check reads the home and
the screws on every build."""
import math
import numpy as np
from shapely.geometry import Point, LineString

# the M2 heads the case takes, (head diameter, head height), both at their maximum: the first layer a head cannot
# pass is its seat, and its top (seat - height) may not stand proud of the back
HEADS = {'socket': (3.8, 2.0),       # ISO 4762 (DIN 912) socket head cap: dk 3.8, k 2.0 (Ian's screws)
         'pan': (4.0, 1.6)}          # ISO 7045 pan head: dk 4.0, k 1.6
SCREW_MIN_IN = 3.0         # mm of screw in the hole (1.5 d, thread-forming into PLA; the 4.26's H3/H4 have 3.6)
SCREW_STANDOFF = 0.3       # and still that much with the lid left this far open
SCREW_FACE_MIN = 0.8       # tip to the front face (four layers)
SCREW_PILOT_MAX = 1.75     # the pilot as laid (1.7 drawn; a wider one bites less)
PILOT_R = (0.5, 1.2)       # a layer is pilot if the axis is free by this much (0: solid cap; past it: air)
LAYER = 0.2
BOARD_PLUS = 0.16          # a board this much thicker than nominal (PCB_T +-10 %)
BOARD_ROOM_MIN = 0.20      # the least board-to-boss room at H3/H4 with that board
Z_SHARED = 0.02            # layers that share less Z than this touch, they do not overlap
OVERLAP_MM2 = 0.005
LATCH_PLAY_MAX = 0.05
LATCH_OFFSETS = (-1.0, 0.0, 1.0)      # along the wall from each latch's centre (the barb is 4.5 wide)


def _free_r(poly, x, y):
    """How far the point is from the layer's material (0 inside it)."""
    if poly.is_empty:
        return math.inf
    return poly.distance(Point(x, y))


def _covering(layers, x, y, r=0.0):
    """The layers with material within r of (x, y): [(zc, poly)]."""
    return [(z, g) for z, g in layers if _free_r(g, x, y) <= r]


def home(lid, tub, rim_points, posts=(), pcb_t=1.6):
    """The lid's as-printed home (its shift toward +Z from the CAD position) and how it was read. rim_points: (x, y)
    on the rims, where the lid's top layer meets the tub's last; posts: (x, y) on the lid's board posts and the tub's
    bosses that hold a pcb_t board between them."""
    rims = []
    for x, y in rim_points:
        lz = [z for z, _ in _covering(lid, x, y)]
        tz = [z for z, _ in _covering(tub, x, y)]
        if lz and tz:
            rims.append(round((min(tz) - LAYER / 2) - (max(lz) + LAYER / 2), 3))
    chain = []
    for x, y in posts:
        lz = [z for z, _ in _covering(lid, x, y) if z < 0.5]
        tz = [z for z, _ in _covering(tub, x, y) if z > 0.5]
        if lz and tz:
            chain.append(round((min(tz) - LAYER / 2 - pcb_t) - (max(lz) + LAYER / 2), 3))
    cands = [float(np.median(v)) for v in (rims, chain) if v]
    dz = round(min(cands), 3) if cands else None
    return {'dz': dz, 'rims': rims, 'posts_board': chain,
            'note': 'the lid stops where the first of these closes: rim on rim, or post / board / boss'}


def board_room(lid, tub, dz, posts, pcb_t=1.6, plus=BOARD_PLUS):
    """The room between the board and the tub's H3/H4 bosses at the lid's home (module docstring, `board`). posts: (x,
    y) on each lid post and tub boss with a board between them. The board's back rests on the lid post's top (shifted
    forward by dz at home), its front is pcb_t further, and the boss's face is the lowest tub layer's bottom."""
    rows = []
    for x, y in posts:
        lz = [z for z, _ in _covering(lid, x, y) if z < 0.5]
        tz = [z for z, _ in _covering(tub, x, y) if z > 0.5]
        if not (lz and tz) or dz is None:
            rows.append({'xy': [x, y], 'ok': False, 'fails': ['no post or boss here']})
            continue
        post_top = round(max(lz) + LAYER / 2 + dz, 3)
        face = round(min(tz) - LAYER / 2, 3)
        room = round(face - post_top - pcb_t, 3) + 0.0
        thick = round(room - plus, 3) + 0.0
        rows.append({'xy': [x, y], 'post_top_home': post_top, 'boss_face': face, 'room': room,
                     'room_thick_board': thick, 'ok': thick >= BOARD_ROOM_MIN - 1e-9,
                     'fails': [] if thick >= BOARD_ROOM_MIN - 1e-9 else
                     [f'{room:.3f} of room, {thick:.3f} with a board {plus} thicker (need >= {BOARD_ROOM_MIN})']})
    return {'posts': rows, 'ok': bool(rows) and all(r['ok'] for r in rows), 'plus': plus, 'min': BOARD_ROOM_MIN}


def screw(name, x, y, lid, tub, dz, screw_l, z_back):
    """One screw read back (module docstring)."""
    near = lambda layers: [(z, g) for z, g in layers if _free_r(g, x, y) < 4.0]
    L = sorted(near(lid))
    T = sorted(near(tub), reverse=True)                     # from the face (the tub's bed) toward the lid
    row = {'screw': name, 'xy': [x, y], 'L': screw_l}
    # the lid: the counterbore from the bed, then each head's seat
    fr = [(z, _free_r(g, x, y)) for z, g in L]
    if not fr:
        return {**row, 'ok': False, 'fails': ['no lid at the screw'], 'seat': None}
    back = round(fr[0][0] - LAYER / 2, 3)                  # the back as laid: the first layer's bed face
    heads = {}
    for h, (hd, hh) in HEADS.items():
        kh = next((i for i, (_, r) in enumerate(fr) if r < hd / 2), None)
        sh = round(fr[kh][0] - LAYER / 2, 3) if kh is not None else None
        heads[h] = {'d': hd, 'height': hh, 'counterbore_layers': kh, 'seat': sh,
                    'top_below_back': round(sh - hh - back, 3) if sh is not None else None}
    ks = [v['counterbore_layers'] for v in heads.values()]
    if None in ks or min(ks) == 0:
        return {**row, 'ok': False, 'fails': ['no counterbore in the lid' if None not in ks else 'nothing holds a head'],
                'seat': None, 'heads': heads}
    k = min(ks)                                             # the larger head's seat
    seat = round(fr[k][0] - LAYER / 2, 3)
    seat_deep = max(v['seat'] for v in heads.values())     # the smaller head's (the same layer over a stepped bridge)
    m = k + 2                                               # over the stepped bridge: the clearance hole, up the post
    while m < len(fr) and fr[m][1] < 1.6:
        m += 1
    hole = [r for _, r in fr[k + 2:m]] or [math.inf]
    row.update(seat=seat, seat_deepest=seat_deep, back=back, counterbore_depth=round(seat - back, 3),
               counterbore_layers=k, counterbore_d=round(2 * min(r for _, r in fr[:k]), 3), heads=heads,
               hole_d=round(2 * min(hole), 3), lid_top=round(fr[m - 1][0] + LAYER / 2, 3), z_back=z_back)
    # the tub: face, cap, pilot, mouth
    tr = [(z, _free_r(g, x, y)) for z, g in T]
    face = round(tr[0][0] + LAYER / 2, 3)
    i = 0
    while i < len(tr) and tr[i][1] < PILOT_R[0]:            # the cap (solid, or a top-surface layer part over it)
        i += 1
    cap_end = i
    j = i
    while j < len(tr) and PILOT_R[0] <= tr[j][1] <= PILOT_R[1]:
        j += 1
    if cap_end == len(tr) or j == i:
        return {**row, 'ok': False, 'fails': ['no pilot in the tub'], 'face': face}
    pilot_end = round(tr[i][0] + LAYER / 2, 3)
    mouth = round(tr[j - 1][0] - LAYER / 2, 3)
    laid = round(2 * max(r for _, r in tr[i:j]), 3)
    row.update(face=face, cap=round(face - pilot_end, 3), pilot=[mouth, pilot_end], pilot_laid_d=laid,
               pilot_least_d=round(2 * min(r for _, r in tr[i:j]), 3))
    tip = round(seat_deep + dz + screw_l, 3)                # the tip from the deeper seat, the engagement from the
    tip_shallow = round(seat + dz + screw_l, 3)             # shallower
    in_hole = round(max(0.0, min(tip_shallow, pilot_end) - mouth), 3)
    in_open = round(max(0.0, min(tip_shallow - SCREW_STANDOFF, pilot_end) - mouth), 3)
    fails = [f"{h} head ({v['d']:.1f} x {v['height']:.1f}) {-v['top_below_back']:.2f} proud of the back"
             for h, v in heads.items() if v['top_below_back'] < -1e-6]
    if in_hole < SCREW_MIN_IN - 1e-6:
        fails.append(f'{in_hole} in the hole < {SCREW_MIN_IN}')
    if in_open < SCREW_MIN_IN - 1e-6:
        fails.append(f'{in_open} in the hole with the lid {SCREW_STANDOFF} open < {SCREW_MIN_IN}')
    if tip > pilot_end + 1e-6:
        fails.append(f'tip {tip} past the hole\'s end {pilot_end}')
    if face - tip < SCREW_FACE_MIN - 1e-6:
        fails.append(f'tip {round(face - tip, 3)} from the face < {SCREW_FACE_MIN}')
    if laid > SCREW_PILOT_MAX + 1e-6:
        fails.append(f'pilot laid {laid} > {SCREW_PILOT_MAX}')
    row.update(tip=tip, in_hole=in_hole, in_hole_lid_open=in_open, tip_short_of_end=round(pilot_end - tip, 3),
               tip_to_face=round(face - tip, 3), ok=not fails, fails=fails)
    return row


def _pairs(A, B, dzA=0.0, dzB=0.0, clip=None):
    hits = []
    for za, ga in A:
        a0, a1 = za + dzA - LAYER / 2, za + dzA + LAYER / 2
        for zb, gb in B:
            b0, b1 = zb + dzB - LAYER / 2, zb + dzB + LAYER / 2
            if min(a1, b1) - max(a0, b0) <= Z_SHARED:
                continue
            if not ga.bounds or not gb.bounds or ga.bounds[2] < gb.bounds[0] or gb.bounds[2] < ga.bounds[0] \
                    or ga.bounds[3] < gb.bounds[1] or gb.bounds[3] < ga.bounds[1]:
                continue
            i = ga.intersection(gb)
            if i.area > OVERLAP_MM2:
                hits.append({'z': [round(max(a0, b0), 3), round(min(a1, b1), 3)], 'mm2': round(i.area, 3),
                             'where': [round(v, 2) for v in i.bounds]})
    return hits


def z_gap(lower, upper, dz_lower=0.0, dz_upper=0.0, clip=None):
    """The least Z gap from the lower part's layers up to the upper part's, over the places they share in plan
    (negative: they overlap by that much). clip: a shapely region; only the lower part within it counts (the
    backstops, which the bay read-backs judge on their own)."""
    best = None
    for zu, gu in upper:
        u0 = zu + dz_upper - LAYER / 2
        for zl, gl in lower:
            l1 = zl + dz_lower + LAYER / 2
            if zl + dz_lower >= zu + dz_upper or (best is not None and u0 - l1 >= best[0]):
                continue
            i = (gl.intersection(clip) if clip is not None else gl).intersection(gu)
            if i.area > OVERLAP_MM2:
                g = round(u0 - l1, 3)
                if best is None or g < best[0]:
                    best = (g, [round(v, 2) for v in i.bounds])
    return {'gap': best[0], 'where': best[1]} if best else None


def overlap(lid, tub, mid, dz, panel_tol):
    """The lid at home against the tub and the midplate (nominal and thickest panel); the tub against the midplate."""
    out = {'lid x tub': _pairs(lid, tub, dzA=dz)}
    for nm, dm in (('nominal panel', 0.0), (f'panel +{panel_tol}', -panel_tol)):
        out[f'lid x midplate, {nm}'] = _pairs(lid, mid, dzA=dz, dzB=dm)
    gaps = {nm: z_gap(lid, mid, dz, dm) for nm, dm in (('nominal panel', 0.0), (f'panel +{panel_tol}', -panel_tol))}
    info = {'tub x midplate, nominal panel': _pairs(tub, mid)}
    return {'dz': dz, 'hits': out, 'ok': not any(out.values()), 'lid_to_midplate_gap': gaps, 'info': info}


def _wall_runs(poly, p0, p1):
    """Material along p0 -> p1 as (t0, t1) runs, t the distance from p0."""
    if poly.is_empty:
        return []
    hit = LineString([p0, p1]).intersection(poly)
    L = math.dist(p0, p1)
    out = []
    for q in getattr(hit, 'geoms', [hit]):
        if q.geom_type == 'LineString' and q.length > 1e-6:
            ts = [math.dist(p0, c) for c in q.coords]
            out.append((min(ts), max(ts)))
    return sorted(out)


def latch(lid, tub, dz, wall, c, face, out_sign, axis, barb_z, pocket_z):
    """One latch (module docstring). wall frame: d outward from the wall's inner face (face, out_sign), along `axis`
    ('y': a side wall, 'x': the top wall); barb_z / pocket_z: the CAD Z windows of the barb and the pocket."""
    res = []
    for s in LATCH_OFFSETS:
        def pts(d):
            v = face + out_sign * d
            return (v, c + s) if axis == 'y' else (c + s, v)
        d0, d1 = -1.5, 1.3
        p0, p1 = pts(d0), pts(d1)
        barb, pocket = [], []
        for z, g in lid:
            if barb_z[0] <= z <= barb_z[1]:
                rs = [(d0 + a, d0 + b) for a, b in _wall_runs(g, p0, p1)]
                rs = [r for r in rs if r[0] < 0.75]
                if rs:
                    barb.append((round(z + dz - LAYER / 2, 3), round(z + dz + LAYER / 2, 3), round(max(b for _, b in rs), 3)))
        for z, g in tub:
            if pocket_z[0] <= z <= pocket_z[1]:
                rs = [(d0 + a, d0 + b) for a, b in _wall_runs(g, p0, p1)]
                rs = [r for r in rs if r[1] > -0.6]
                if rs:
                    pocket.append((round(z - LAYER / 2, 3), round(z + LAYER / 2, 3), round(max(-0.6, min(a for a, _ in rs)), 3)))
        lifts, clash = [], []
        for a, b, dl in barb:
            for ta, tb, dt in pocket:
                if dl <= dt + 1e-6:
                    continue
                if a >= tb - 1e-6:
                    lifts.append(round(a - tb, 3))
                elif min(b, tb) - max(a, ta) > 1e-6:
                    clash.append([a, b, dl, ta, tb, dt])
        res.append({'offset': s, 'dead_band': min(lifts) if lifts else None, 'clash_at_home': clash[:3],
                    'barb': barb, 'pocket': pocket})
    worst = [r['dead_band'] for r in res if r['dead_band'] is not None]
    db = max(worst) if len(worst) == len(res) else None
    clash = [r['clash_at_home'] for r in res if r['clash_at_home']]
    fails = []
    if db is None or db > LATCH_PLAY_MAX + 1e-6:
        fails.append(f'dead band {db} > {LATCH_PLAY_MAX}')
    if clash:
        fails.append('the barb overlaps its pocket\'s wall at home (it cannot drop in)')
    return {'latch': f"{wall} {'X' if axis == 'x' else 'Y'}{c:g}", 'dead_band': db, 'ok': not fails, 'fails': fails,
            'sections': res}


def show(r):
    """Print the read-backs (slice_check's report style); r may hold only some of them (the 4.26 reads the home and
    the screws)."""
    h = r['home']
    print(f"  as printed: lid home {h['dz']:+.3f} from CAD (rims {h['rims']}, posts / board / bosses {h['posts_board']})")
    for s in r['screws']:
        if 'tip' not in s:
            print(f"    screw {s['screw']:12s} FAIL {s['fails']}")
            continue
        hd = ', '.join(f"{n} {v['d']:.1f} x {v['height']:.1f} {v['top_below_back']:+.2f}" for n, v in s['heads'].items())
        print(f"    screw {s['screw']:12s} M2x{s['L']:g}: seat {s['seat']:+.3f} ({s['counterbore_layers']} layers, "
              f"{s['counterbore_depth']:.2f} deep), head tops below the back: {hd}; "
              f"hole {s['hole_d']:.2f} | pilot {s['pilot'][0]:+.2f}..{s['pilot'][1]:+.2f} laid {s['pilot_laid_d']:.2f}, "
              f"face {s['face']:+.2f} | tip {s['tip']:+.3f}: {s['in_hole']:.2f} in the hole ({s['in_hole_lid_open']:.2f} "
              f"{SCREW_STANDOFF} open), {s['tip_short_of_end']:+.2f} short of its end, {s['tip_to_face']:.2f} to the face"
              f"  {'PASS' if s['ok'] else 'FAIL ' + '; '.join(s['fails'])}")
    if 'board' in r:
        b = r['board']
        for p in b['posts']:
            if 'room' not in p:
                print(f"    board at H3/H4 {p['xy']}: FAIL {p['fails']}")
                continue
            print(f"    board at H3/H4 ({p['xy'][0]:.1f}, {p['xy'][1]:.1f}): lid post top at home {p['post_top_home']:+.3f}, "
                  f"boss face {p['boss_face']:+.3f}: room {p['room']:.3f}, {p['room_thick_board']:.3f} with a board {b['plus']} thicker"
                  f"  {'PASS' if p['ok'] else 'FAIL ' + '; '.join(p['fails'])}")
        print(f"  as printed, board-to-boss room at H3/H4 >= {b['min']} with a +{b['plus']} board: {'PASS' if b['ok'] else 'FAIL'}")
    if 'overlap' in r:
        o = r['overlap']
        for k, v in o['hits'].items():
            print(f"    {k:34s} {'clear' if not v else f'{len(v)} overlaps, e.g. ' + str(v[:3])}")
        for k, v in o['lid_to_midplate_gap'].items():
            print(f"    lid up to the midplate, {k:15s} least gap {v['gap'] if v else None} at {v['where'] if v else '-'}")
        for k, v in o['info'].items():
            print(f"    ({k}: {'clear' if not v else f'{len(v)} overlaps, e.g. ' + str(v[:2])})")
        print(f"  as printed, lid at home vs tub and midplate: {'PASS' if o['ok'] else 'FAIL'}")
    if 'latches' in r:
        bad = [l for l in r['latches'] if not l['ok']]
        print(f"    latch dead bands from home: " + ', '.join(f"{l['latch']} {l['dead_band']}" for l in r['latches']))
        print(f"  as printed, latch dead band <= {LATCH_PLAY_MAX}: {'PASS' if not bad else 'FAIL'}"
              + ('' if not bad else '  ' + '; '.join(f"{l['latch']}: {', '.join(l['fails'])}" for l in bad)))
    print(f"  as printed, screws (an M2x{r['screws'][0]['L']:g} socket head cap or pan head): "
          f"{'PASS' if all(s['ok'] for s in r['screws']) else 'FAIL'}")
