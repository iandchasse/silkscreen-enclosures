"""Mechanism checks: the bottom keys' stroke, forces, preload window and stress (the crank spec's checks 3, 5, 6 and 7;
build.py runs checks 1, 2 and 4 through crank_checks.py), the hook keys' own checks (key_hooks, test 2, 2026-09-30),
the side keys' sweep, plus the spring/force estimates for
every compliant feature. Writes out/<variant>/mechanics.json (variant.py): the strip's checks (channel_skin,
seat_entry, springs' foot_stop) in the light-strip build only.

Material model: Ian prints PLA (Elegoo PLA on a Centauri Carbon 2). Printed PLA is taken as
E = 3000 MPa and kept under ~1.5 % strain in anything that flexes; Rev D-H used PETG's 2000, which
put every spring and snap force about a third low. Rev H's numbers are recomputed with the same
model where the page compares against them.
Switches: APEM MJTP1117, 1.27-1.86 N operating force, 0.25 (+0.20/-0.10) mm travel (the side keys are figured at
1.86); the bottom keys also for the SHOU HAN TS365ZJ, 1.96-2.94 N (params SWITCH_FORCE).
"""
import json, math, sys
import numpy as np
import cadquery as cq
import hw
import params as P
import keys, tub, lid, midplate, crank

E = 3000.0                        # printed PLA
F_SW = 1.86                       # worst-case operating force
CLICK = 0.25                      # nominal travel to the click
MU = 0.3                          # PLA on PLA / FR4 solder mask / the switch's plunger, dry
# Rev H's side tabs, recomputed for PLA: their stiffness at the plunger (from Rev H's own model, which
# used PETG's E = 2000) scaled to E, over Rev H's 0.39 gap plus the click.
REV_H_TAB_K_PETG = {'SW1': 1.29, 'SW4': 1.53, 'SW10': 1.66, 'SW5': 0.83, 'SW7': 0.83}
# Rev I's separate side keys, press at the pad centre in PLA (its own out/mechanics.json)
REV_I_SIDE_N = {'SW1': 2.53, 'SW4': 2.58, 'SW10': 2.41, 'SW5': 2.14, 'SW7': 2.14}


# ---- bottom keys: bell crank + straight key (crank.py, keys.py; the crank spec's checks 3, 5, 6 and 7) ---------------
# Force model (spec section 6). The key's pusher presses the crank's crown LIN from the rod; the nose pushes the plunger
# A_OUT from it. Friction mu at the crown (acting DZ_PAD above the rod) and at the nose (DY_NOSE beside it), and in the
# pin on the rod's radius RPIN:  P (LIN - mu DZ_PAD) = Fs A_OUT + mu Fs DY_NOSE + mu_pin RPIN sqrt(P^2 + Fs^2).
# The key then tilts between its chin-side stop (the pusher's chin end, y YA) and its +Y face (YB), which multiplies the
# force by g(e) for a press e off the crown (a guide length Lg: the key's +Y face on the rail and the opening's edge, up
# to the face). No drag since the hook keys (test 2, 2026-09-30): the leaf and its bump are gone.
LIN = P.ROD_AXIS[0] - P.CRANK_CROWN[0][0]                  # 4.95
A_OUT = P.ROD_AXIS[1] - P.CRANK_NOSE_C['M'][1]             # 2.95
RPIN = P.ROD_D / 2
DZ_PAD = P.ROD_AXIS[1] - (P.CRANK_CROWN[0][1] + P.CRANK_CROWN[1])   # 0.80
DY_NOSE = P.PLUNGER_Y - P.ROD_AXIS[0]                      # 0.58
YP = P.CRANK_CROWN[0][0]
YA, YB = P.KEY_PUSHER['y'][0], P.KEY_Y[1]
PRESS_Y = (round(P.KEY_Y[0] + 0.10, 2), -6.20, -4.60)      # the cap's chin edge (-7.45), its centre and its top edge
SWITCHES = {'MJTP 1.27': 1.27, 'MJTP 1.86': 1.86, 'TS365 1.96': 1.96, 'TS365 2.94': 2.94}
PLUNGER_TRAVEL = {'click': 0.25, 'bottom': 0.45}           # MJTP1117 (the TS365ZJ taken as alike)
OVERPRESS = 20.0                                           # N, a hard thumb on one key


def pad_force(Fs, mu, mu_pin):
    """Force on the crank's pad that holds switch force Fs."""
    p = Fs * A_OUT / LIN
    for _ in range(50):
        p = (Fs * A_OUT + mu * Fs * DY_NOSE + mu_pin * RPIN * math.hypot(p, Fs)) / (LIN - mu * DZ_PAD)
    return p


def guide(e, Lg, mu):
    """The key's tilt factor for a press e off the crown (y; + toward the rail)."""
    s = mu * (YA + YB - 2 * YP)
    k = 1 - 2 * mu * abs(e) / (Lg + s if e >= 0 else Lg - s)
    return float('inf') if k <= 0 else 1 / k


def key_travel():
    """Key travel to the click and to the switch's bottom, and the crank's angles, at tub-to-board offsets -0.2 / 0 /
    +0.2 with the matching crank (crank-M on the MJTP's face, crank-T on the TS365's nominal tip)."""
    out = {}
    for fam, var, face in (('MJTP1117', 'M', P.PLUNGER_Y), ('TS365ZJ', 'T', P.TS365['tip_y_nom'])):
        for dy in (-P.TUB_BOARD_DY, 0.0, P.TUB_BOARD_DY):
            th = crank.rest_theta(face + dy, var)
            row = {'theta_rest': round(th, 2), 'key_proud_at_rest': round(P.KEY_TOP_OVER_FACE + crank.key_lift(th), 3)}
            for k, t in PLUNGER_TRAVEL.items():
                th1 = crank.rest_theta(face + dy + t, var)
                tr = crank.key_lift(th) - crank.key_lift(th1)
                row[f'theta_{k}'] = round(th1, 2)
                row[f'key_travel_{k}'] = round(tr, 3)
                row[f'key_proud_at_{k}'] = round(row['key_proud_at_rest'] - tr, 3)
            out[f'{fam} {dy:+.1f}'] = row
    return out


def key_forces():
    """Finger force at the click (check 5), both switch families' ranges, mu 0.3 and 0.45, at the cap's chin edge,
    centre and top edge (no drag: the hook keys, test 2); the tilt factor over the cap, and the travel."""
    Lg = P.Z_FRONT
    out = {'lever_ratio': round(LIN / A_OUT, 3), 'no_friction_ratio': round(A_OUT / LIN, 3), 'guide_length_mm': Lg,
           'press_y': PRESS_Y}
    for mu in (0.3, 0.45):
        rows = {}
        for sn, Fs in SWITCHES.items():
            p = pad_force(Fs, mu, mu)
            rows[sn] = [round(p * guide(y - YP, Lg, mu), 3) for y in PRESS_Y]
        emax = max(e / 100 for e in range(0, 400) if guide(e / 100, Lg, mu) <= 1.5)
        out[f'mu_{mu}'] = {'finger_force_N': rows,
                           'top_edge_factor': round(guide(PRESS_Y[2] - YP, Lg, mu), 3),
                           'factor_le_1.5_up_to_y': round(YP + emax, 2),
                           'max_2mu_e_over_Lg': round(2 * mu * max(abs(PRESS_Y[0] - YP), abs(YB - YP)) / Lg, 3)}
    out['travel'] = key_travel()
    m = out['mu_0.3']
    tr = [r['key_travel_click'] for r in out['travel'].values()]
    out['checks'] = {'centre_MJTP_1.27_le_1.3': m['finger_force_N']['MJTP 1.27'][1] <= 1.3,
                     'centre_MJTP_1.86_le_1.7': m['finger_force_N']['MJTP 1.86'][1] <= 1.7,
                     'top_edge_factor_le_1.6': m['top_edge_factor'] <= 1.6,
                     '2mu_e_over_Lg_lt_0.8': max(out[f'mu_{mu}']['max_2mu_e_over_Lg'] for mu in (0.3, 0.45)) < 0.8,
                     'travel_to_click_0.35_0.50': 0.35 <= min(tr) and max(tr) <= 0.50}
    out['rocker_for_comparison'] = 'the rocker (to 2026-09-26) needed 2.21 / 2.55 / 3.11 N at its centre for a 1.57 N switch'
    return out


def printed_layers(a, b, layer=P.LAYER, ties=False):
    """The part of a span a..b of print height (from the bed) that prints: the layers whose mid-plane lies inside it
    (a plane on its end face prints nothing). An end exactly on a mid-plane is a tie, which Orca settles by float
    noise (2026-10-03: the 9.90 key's top at 9.90 did not print; the 50-layer key's body faces at +-3.30 print to
    +-3.40). By default the tie at a counts and the one at b does not; ties=True counts both (the larger part: the
    worse case for a clearance). Returns (from, to)."""
    k0 = math.ceil((a + layer / 2) / layer - 1e-6)
    k1 = (math.floor((b + layer / 2) / layer + 1e-6) if ties else math.ceil((b + layer / 2) / layer - 1e-6) - 1)
    return round((k0 - 1) * layer, 4), round(k1 * layer, 4)


def key_fit():
    """The key's fit in the tub as printed (2026-09-29: Ian's first print of the Rev L keys needed force to go in and
    would not press freely). Each key-to-tub pair's clearance in CAD and as printed at the best / typical / worst of
    params KEY_FDM (holes 0.10-0.20 small, parts 0.05-0.15 large). The key's +Y face rides the rail with no play (it
    is the key's guide face), so a Y pair takes both errors on its chin side (c - hole - part). The hook keys (test 2,
    2026-09-30) add the hooks' pairs (H, S, L); the drag bump's (G, J, I and its ledge H) are gone. The key prints on
    its -X end (test 1, 2026-09-29): X is its layer
    axis, so its X sizes are layer-quantized, not grown (the 10.00 key is 50 layers, 10.00 long since 2026-10-03; the
    9.90 one printed 49, 9.80: layers print where their mid-plane is inside it), and an X pair is two-sided with the key
    centred (c_q - hole/2); its bed end has no flare
    past the outline (KEY_BED_END), so the old layer-1 rows (A*, D*: the cap-down X ends; C*: the cap top's first layer
    through the skin) are gone. Pairs from params, not typed-in numbers:
      A  cap to the opening's side, X per side (skin)     D  key to a web, X per side (pocket)
      C  cap's chin face to the opening's chin edge        F  the pusher's chin end (the stop) to the chin wall
      H  a hook's tip to its slot's back (pocket)          S  a hook to its slot's outer side, X per side (as D)
      L  the +X hook's 45-degree lead to its slot's inner side, the key at its chin stop and pushed -X by its play
         (A): the lead may cam it back, it must not meet the wall (CAD; as printed less hole / 2 + part / 2)
      E  the key's body to its crank's cheek, X, less the key's X play (A): a key pushed sideways meets the opening
         first. The body's +X face as printed: on the 50-layer key the +-3.30 faces lie on layer mid-planes, and
         Orca prints them at +-3.40 (2026-10-03 G-code), so the tie counts (printed_layers ties, the worse case);
         the cheek grows part/2; the crank centred (E* with the crank off-centre by its slot play: reported). Its
         -X side is cut 45 degrees under the cap: no stop there
      K  the crank's crown on the pusher's flat over the sweep (-13..+16 degrees)
    Also the most the key can rock on its chin side (reported)."""
    Fd = P.KEY_FDM
    hole, part = Fd['hole'], Fd['part']
    O, Pu, Hk, Sl = P.KEY_OPENING, P.KEY_PUSHER, P.KEY_HOOK, P.KEY_SLOT
    h, cy0 = P.KEY_HALF, P.KEY_Y[0]
    lead_x = Hk['dx'][0] - (P.BOT_IN - Sl['back'])             # the lead where it crosses the wall's face, tip on the back
    c = {'A': O['half'] - h, 'D': P.SLOT[1] - h, 'C': cy0 - O['y'][0], 'F': Pu['y'][0] - P.BOT_IN,
         'H': Hk['tip'] - Sl['back'], 'S': Sl['dx'][1] - Hk['dx'][1], 'L': lead_x - P.KEY_SIDE_GAP - Sl['dx'][0],
         'E': P.CRANK_CHEEK[0] - P.KEY_BODY['half'], 'slot': P.CRANK_CHEEK[0] - P.SLOT[0]}
    r3 = lambda v: [round(x, 3) for x in v]
    xpair = lambda cc: r3(cc - a / 2 - b / 2 for a, b in zip(hole, part))
    ypair = lambda cc: r3(cc - a - b for a, b in zip(hole, part))
    # on its -X end: the key's X extent as printed (from the bed at -h), and its body's +X face
    lay = printed_layers(0.0, 2 * h)
    xq = (-h + lay[0], -h + lay[1])                            # -5.00 .. 5.00 (50 layers)
    cq_ = (-h + printed_layers(h - P.KEY_BODY['half'], h + P.KEY_BODY['half'], ties=True)[1]) - (xq[0] + xq[1]) / 2
                                                               # body +X, centred: 3.40 as Orca prints it
    aq, dq = O['half'] - (xq[1] - xq[0]) / 2, P.SLOT[1] - (xq[1] - xq[0]) / 2
    sq = Sl['dx'][1] - (xq[1] - xq[0]) / 2                     # the hooks run to the key's X ends
    xq_pair = lambda cc: r3(cc - a / 2 for a in hole)
    rows = {'A cap to opening side, X per side (skin)': (c['A'], xq_pair(aq)),
            'D key to web, X per side (pocket)': (c['D'], xq_pair(dq)),
            'C cap chin face to opening chin edge (skin)': (c['C'], ypair(c['C'])),
            'F pusher chin end (the stop) to chin wall (pocket)': (c['F'], ypair(c['F'])),
            'H hook tip to slot back (pocket)': (c['H'], ypair(c['H'])),
            'S hook to slot outer side, X per side (pocket)': (c['S'], xq_pair(sq)),
            'L hook lead to slot inner side, key at its chin stop and -X by A': (c['L'], xpair(c['L']))}
    # E: the key pushed +X by its play (A, as printed) moves its body's +X face (as printed) toward the +X
    # cheek, which grows part/2
    e = r3(P.CRANK_CHEEK[0] - b / 2 - (cq_ + a) for b, a in zip(part, rows['A cap to opening side, X per side (skin)'][1]))
    rows['E key body to crank cheek, X per side, less the key X play (A)'] = (c['E'] - c['A'], e)
    estar = ('E* as E, the crank off-centre toward the key by its slot play',
             (c['E'] - c['A'] - c['slot'], r3(x - max(0.0, sp) for x, sp in zip(e, xpair(c['slot'])))))
    # K: the crown's top point (its contact with the flat pusher), turned with the crank
    ths = [t / 2 for t in range(-26, 33)]
    ys = [crank.rotp(P.CRANK_CROWN[0], t)[0] for t in ths]
    rest = crank.rest_theta(P.PLUNGER_Y, 'M')
    k = {'contact_y': [round(min(ys), 3), round(crank.rotp(P.CRANK_CROWN[0], rest)[0], 3), round(max(ys), 3)],
         'pusher_y': list(Pu['y']), 'to_chin_end': round(min(ys) - Pu['y'][0], 3),
         'to_body_end': round(Pu['y'][1] - max(ys), 3)}
    # the key's rock on its chin side: the stop's gap as printed at best, over the guide (the face down to the stop band)
    arm = P.Z_FRONT - (Pu['z0'] + Pu['stop_z1']) / 2
    gap = ypair(c['F'])[0]
    tilt = {'gap_mm': gap, 'arm_mm': round(arm, 3), 'deg': round(math.degrees(math.atan(gap / arm)), 1)}
    out = {'model': {'hole': list(hole), 'part': list(part),
                     'key_x_as_printed': [round(q, 3) for q in xq], 'layers': round((lay[1] - lay[0]) / P.LAYER),
                     'body_x_face_centred': round(cq_, 3), 'columns': 'CAD, as printed best / typical / worst'},
           'pairs': {n: {'cad': round(v[0], 3), 'printed': v[1]} for n, v in rows.items()},
           'accepted': {estar[0]: {'cad': round(estar[1][0], 3), 'printed': estar[1][1],
                                   'note': f'CAD sizes only: a key pushed fully sideways comes {estar[1][0]:+.2f} to a '
                                           f'crank that sits fully toward it (below 0 it nudges it over); the crank floats '
                                           f'in its slot, so it is a push, not a stop'}},
           'crown_on_pusher': k, 'tilt_max': tilt}
    p = out['pairs']
    w = lambda n: p[n]['printed'][2]
    out['checks'] = {'rigid_Y_pairs_C_F_H_ge_0.05_worst': min(w('C cap chin face to opening chin edge (skin)'),
                                                              w('F pusher chin end (the stop) to chin wall (pocket)'),
                                                              w('H hook tip to slot back (pocket)')) >= 0.05 - 1e-9,
                     'X_pairs_A_D_S_ge_0.15_worst': min(w('A cap to opening side, X per side (skin)'),
                                                        w('D key to web, X per side (pocket)'),
                                                        w('S hook to slot outer side, X per side (pocket)')) >= 0.15,
                     'opening_stops_the_key_before_its_hooks_S_gt_A': c['S'] > c['A'],
                     'hook_lead_clear_of_the_slot_L_ge_0_worst': w('L hook lead to slot inner side, key at its chin stop and -X by A') >= 0.0,
                     'opening_stops_the_key_before_its_crank_E_ge_0.05': min(
                         [p['E key body to crank cheek, X per side, less the key X play (A)']['cad']]
                         + p['E key body to crank cheek, X per side, less the key X play (A)']['printed']) >= 0.05 - 1e-9,
                     'crown_on_the_pushers_flat_ge_0.10_from_each_end': min(k['to_chin_end'], k['to_body_end']) >= 0.10}
    return out


def preload_window():
    """Check 6: what the key puts on the plunger at rest (it must stay well under the switch's operating force), the
    key's height at rest over the face, and what a crank of the wrong variant does. The hook keys (test 2) have no drag
    and no preload: face-up the key and its crank rest on the plunger under their own weight (mechanics.key_hooks has
    the gravity in every pose)."""
    vol = keys.build().val().Volume()
    weight = vol * 1.24e-6 * 9.81                          # PLA 1.24 g/cm3
    g = crank_gravity()
    fs = float(weight * LIN + g['crank_torque_face_up_Nmm']) / A_OUT     # the key's weight and the crank's CG, face up
    out = {'key_mass_g': round(vol * 1.24e-3, 3), 'key_weight_N': round(weight, 4),
           'rest_load_on_plunger_N': round(fs, 4), 'note': 'gravity only (face up): no drag, no preload'}
    out['checks'] = {'rest_load_le_0.25': fs <= 0.25,
                     'rest_load_lt_0.3_min_op_MJTP': fs < 0.3 * P.SWITCH_FORCE['MJTP1117'][0],
                     'rest_load_lt_0.3_min_op_TS365': fs < 0.3 * P.SWITCH_FORCE['TS365ZJ'][0]}
    tr = key_travel()
    proud = [r['key_proud_at_rest'] for r in tr.values()]
    out['key_proud_at_rest_mm'] = [min(proud), max(proud)]
    # on its -X end the key's height (device Z) is an XY size: it comes out part/2 .. part (0.05..0.15) taller, all of
    # it at the cap's top (its pusher rests on the crown)
    grow = (P.KEY_FDM['part'][0], P.KEY_FDM['part'][2])
    out['key_proud_at_rest_as_printed_mm'] = [round(min(proud) + grow[0], 3), round(max(proud) + grow[1], 3)]
    out['checks']['key_proud_1.0_2.0'] = 1.0 <= min(proud) + grow[0] and max(proud) + grow[1] <= 2.0 + 1e-9
    # the TS365's tip tolerance (+-0.2) on top of the tub-to-board play
    lifts = [crank.key_lift(crank.rest_theta(P.TS365['tip_y_nom'] + a + b, 'T')) for a in (-0.2, 0.2) for b in (-0.2, 0.2)]
    out['key_proud_with_ts365_tip_tolerance_mm'] = [round(P.KEY_TOP_OVER_FACE + min(lifts), 3), round(P.KEY_TOP_OVER_FACE + max(lifts), 3)]
    out['key_proud_at_click_min_mm'] = min(r['key_proud_at_click'] for r in tr.values())
    out['key_proud_at_bottom_min_mm'] = min(r['key_proud_at_bottom'] for r in tr.values())
    wrong = {'crank-M with a TS365': crank.key_lift(crank.rest_theta(P.TS365['tip_y_nom'], 'M')),
             'crank-T with an MJTP': crank.key_lift(crank.rest_theta(P.PLUNGER_Y, 'T'))}
    out['wrong_variant_key_shift_mm'] = {k: round(v, 3) for k, v in wrong.items()}
    return out


def rod_bending(F_pin, kfac=1.0, n=1201):
    """The rod (d 1.72, the thinnest filament) as a beam on elastic bearings - the rail on both sides of each cheek,
    none in the slots - loaded by one crank's two cheeks (Hermite elements, a Winkler bed of 0.8 E per mm of rail).
    Returns (max bending stress MPa, max deflection mm, peak bearing pressure on the rail MPa)."""
    import numpy as np
    from scipy.sparse import lil_matrix
    from scipy.sparse.linalg import spsolve
    d = P.ROD_D_RANGE[0]
    I = math.pi * d ** 4 / 64
    Zs = math.pi * d ** 3 / 32
    x = np.linspace(-12.0, 12.0, n)
    h = x[1] - x[0]
    c0, c1 = P.CRANK_CHEEK
    s0, s1 = P.SLOT
    k = np.full(n, kfac * E * 0.8)
    q = np.zeros(n)
    for sg in (-1, 1):
        a, b = sorted((sg * s0, sg * s1))
        k[(x > a) & (x < b)] = 0.0
        a, b = sorted((sg * c0, sg * c1))
        m = (x >= a) & (x <= b)
        q[m] = (F_pin / 2) / (b - a)
    N = 2 * n
    K = lil_matrix((N, N))
    Fv = np.zeros(N)
    ke = E * I / h ** 3 * np.array([[12, 6 * h, -12, 6 * h], [6 * h, 4 * h * h, -6 * h, 2 * h * h],
                                    [-12, -6 * h, 12, -6 * h], [6 * h, 2 * h * h, -6 * h, 4 * h * h]])
    for e in range(n - 1):
        idx = [2 * e, 2 * e + 1, 2 * e + 2, 2 * e + 3]
        for i in range(4):
            for j in range(4):
                K[idx[i], idx[j]] += ke[i, j]
    for i in range(n):
        K[2 * i, 2 * i] += k[i] * h
        Fv[2 * i] += q[i] * h
    u = spsolve(K.tocsr(), Fv)
    w = u[0::2]
    M = E * I * np.gradient(np.gradient(w, h), h)
    return float(abs(M).max() / Zs), float(abs(w).max()), float((k * np.clip(w, 0, None)).max() / d)


def prandtl(S, h):
    """Saint-Venant torsion of a YZ section (shapely) from Prandtl's stress function: lap(phi) = -2 inside, phi = 0 on
    the boundary (unit twist, G = 1), on an h grid with Shortley-Weller stencils at the boundary (each node's distance
    to it along the grid lines exact). Returns J = 2 int(phi) dA, the peak |grad phi| (the shear stress per unit
    torque is |grad phi| / J; the peak is on the boundary: there the slope is read at the boundary point from a
    parabola through the boundary and the two nodes inside) and where it is. Checked against a 3.05 x 1.2 rectangle
    (J and peak to 4 digits of the series solution) and a circle."""
    import numpy as np
    from shapely import contains_xy, intersection, points, linestrings, distance
    from scipy.sparse import coo_matrix
    from scipy.sparse.linalg import spsolve
    x0, y0, x1, y1 = S.bounds
    ys = np.arange(x0 - 3.3719 * h, x1 + 4 * h, h)             # grid offset so no node lands on a boundary line
    zs = np.arange(y0 - 3.6143 * h, y1 + 4 * h, h)
    YY, ZZ = np.meshgrid(ys, zs, indexing='ij')
    inside = contains_xy(S, YY, ZZ)
    idx = -np.ones(inside.shape, int)
    I, Jn = np.nonzero(inside)
    n = len(I)
    idx[I, Jn] = np.arange(n)
    B = S.boundary
    dist = {}
    for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        out = ~inside[I + di, Jn + dj]
        a = np.full(n, h)
        ii, jj = I[out], Jn[out]
        p0 = np.stack([ys[ii], zs[jj]], 1)
        p1 = np.stack([ys[ii + di], zs[jj + dj]], 1)
        dd = distance(points(p0), intersection(linestrings(np.stack([p0, p1], 1)), B))
        a[out] = np.clip(np.where(np.isfinite(dd), dd, h), 1e-3 * h, h)
        dist[(di, dj)] = a
    rows, cols, vals = [], [], []
    diag = np.zeros(n)
    for dp, dm in (((1, 0), (-1, 0)), ((0, 1), (0, -1))):
        hp, hm = dist[dp], dist[dm]
        cp, cm = 2 / (hp * (hp + hm)), 2 / (hm * (hp + hm))
        diag -= cp + cm
        for d, c in ((dp, cp), (dm, cm)):
            nb = idx[I + d[0], Jn + d[1]]
            ok = nb >= 0
            rows.append(np.arange(n)[ok]); cols.append(nb[ok]); vals.append(c[ok])
    rows.append(np.arange(n)); cols.append(np.arange(n)); vals.append(diag)
    A = coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr()
    phi = spsolve(A, np.full(n, -2.0))
    J = float(2 * phi.sum() * h * h)

    def val(di, dj):
        nb = idx[I + di, Jn + dj]
        return np.where(nb >= 0, phi[np.maximum(nb, 0)], 0.0), nb >= 0

    def slope(dp, dm):
        hp, hm = dist[dp], dist[dm]
        (up, okp), (um, okm) = val(*dp), val(*dm)
        res = (up - um) / (hp + hm)
        for d, a_, ok in ((dp, hp, okp), (dm, hm, okm)):
            sgn = 1 if d[0] + d[1] > 0 else -1
            (u1, ok1), (u2, ok2) = val(-d[0], -d[1]), val(-2 * d[0], -2 * d[1])
            near = a_ < 0.5 * h                                  # too near the boundary: use the next two nodes in
            s0, v0 = np.where(near, -h, 0.0), np.where(near, u1, phi)
            s1, v1 = np.where(near, -2 * h, -h), np.where(near, u2, u1)
            dv = v0 * (a_ - s1) / ((s0 - a_) * (s0 - s1)) + v1 * (a_ - s0) / ((s1 - a_) * (s1 - s0))
            res = np.where((~ok) & ok1 & (ok2 | ~near), sgn * dv, res)
        return res

    g = np.hypot(slope((1, 0), (-1, 0)), slope((0, 1), (0, -1)))
    k = int(np.argmax(g))
    return J, float(g.max()), (round(float(ys[I[k]]), 3), round(float(zs[Jn[k]]), 3))


def crank_stress():
    """Check 7: a 20 N over-press on one key. The rod in bending (on elastic bearings, 1x and 1/3x as stiff), shear and
    bearing; the crank's crossbar with its belly as a beam along X pinned at the cheeks (its section read off the built
    crank), in layer; the crossbar's root and the leg's root across the layers; the cheeks (cheek_stress). (The drag
    leaf's stress went with the leaf: the hook keys, test 2; the hooks' own stress is key_hooks'.)"""
    import crank_checks
    import numpy as np
    from shapely.geometry import box as sbox
    F = OVERPRESS
    Fs = F * LIN / A_OUT
    pin = math.hypot(F, Fs)
    d = P.ROD_D_RANGE[0]
    A_rod = math.pi * d ** 2 / 4
    out = {'press_N': F, 'plunger_N': round(Fs, 1), 'pin_N': round(pin, 1), 'per_cheek_N': round(pin / 2, 1)}
    s1, w1, pb = rod_bending(pin)
    s3, _, _ = rod_bending(pin, kfac=1 / 3)
    cw = P.CRANK_CHEEK[1] - P.CRANK_CHEEK[0]
    out['rod'] = {'bending_MPa': round(s1, 1), 'bending_soft_bearings_MPa': round(s3, 1), 'deflection_um': round(w1 * 1000, 1),
                  'shear_MPa': round(4 / 3 * (pin / 4) / A_rod, 1), 'cheek_bearing_MPa': round((pin / 2) / (d * cw), 1),
                  'seat_bearing_MPa': round(pb, 1)}
    # the crossbar's section (crossbar, crown and belly) off the built crank, at the belly's middle; it must be
    # crank.body_profile(), which the torsion is solved on
    m = crank_checks.to_mesh(crank.build('M').val())
    S = crank_checks.section(m, crank_checks.ZONE_PLANE['belly']).intersection(sbox(-9, -9, -2.9, 0.5))
    prof = crank.body_profile()
    sd = S.symmetric_difference(prof).area
    c = S.centroid
    ys = np.arange(S.bounds[0], S.bounds[2], 0.01)
    zs = np.arange(S.bounds[1], S.bounds[3], 0.01)
    YY, ZZ = np.meshgrid(ys, zs)
    from shapely import contains_xy
    msk = contains_xy(S, YY, ZZ)
    Iy = float(((ZZ[msk] - c.y) ** 2).sum() * 1e-4)
    Iz = float(((YY[msk] - c.x) ** 2).sum() * 1e-4)
    cz = max(abs(S.bounds[1] - c.y), abs(S.bounds[3] - c.y))
    cy = max(abs(S.bounds[0] - c.x), abs(S.bounds[2] - c.x))
    span = 2 * P.CRANK_HALF - 0.3
    x = (P.CRANK_CHEEK[0] + P.CRANK_CHEEK[1]) / 2 - P.CRANK_LEG_HALF    # cheek to the leg's side
    q = F / span
    My, Mz = Fs / 2 * x, q * 4.5 * x - q * x * x / 2
    sy, sz = My * cy / Iz, Mz * cz / Iy
    # torsion and shear on the layer planes, at each cut dx s through the belly zone (1.3..3.75): the free body
    # outboard of the cut carries half the rod's reaction (Fs/2 along +Y, F/2 along +Z) at the rod and the key's load
    # over s..KEY_HALF at the crown's top; its moment about the section's centroid is the torque. The stress is
    # Prandtl's (the section's own peak |grad phi| / J, every re-entrant corner rounded: CRANK_FILLET, so it converges),
    # plus 1.5 V / A of direct shear added on top (as the spec's check does, though the two peaks are not at one point)
    rows = {}
    for h in (0.01, 0.005):
        J, gmax, at = prandtl(prof, h)
        rows[h] = (J, gmax, at)
    J, gmax, at = rows[0.005]
    worst = None
    for s in [P.CRANK_LEG_HALF + i * (P.CRANK_CHEEK[0] - P.CRANK_LEG_HALF) / 10 for i in range(11)]:
        F1 = F * (P.KEY_HALF - s) / (2 * P.KEY_HALF)
        ry, rz = P.ROD_AXIS[0] - c.x, P.ROD_AXIS[1] - c.y
        ky, kz = YP - c.x, (P.CRANK_CROWN[0][1] + P.CRANK_CROWN[1]) - c.y
        Ts = ry * (F / 2) - rz * (Fs / 2) + ky * (-F1)
        V = math.hypot(Fs / 2, F / 2 - F1)
        tt, tv = abs(Ts) * gmax / J, 1.5 * V / prof.area
        if worst is None or tt + tv > worst[0]:
            worst = (tt + tv, s, Ts, tt, tv)
    out['crossbar'] = {'section_mm2': round(S.area, 3), 'section_vs_body_profile_symdiff_mm2': round(sd, 5),
                       'Iy': round(Iy, 2), 'Iz': round(Iz, 2), 'bending_in_layer_MPa': round(sy + sz, 1),
                       'J_mm4': round(J, 3), 'peak_grad_phi': round(gmax, 3), 'peak_at_yz': at,
                       'grid_h_0.01_J_peak': [round(rows[0.01][0], 3), round(rows[0.01][1], 3)],
                       'worst_cut_dx': round(worst[1], 3), 'torque_Nmm': round(worst[2], 2),
                       'torsion_MPa': round(worst[3], 2), 'shear_MPa': round(worst[4], 2)}
    # the crossbar's root at y -6.2 (the pad's load 1.25 off it) and the leg's root at z -1.3 (the plunger's 1.05 below
    # it), each across the crank's full width
    W = 2 * P.CRANK_HALF
    h_root = 1.2
    out['crossbar_root_across_layers_MPa'] = round(F * (-6.2 - YP) / (W * h_root ** 2 / 6), 1)
    lb = 4.65 - 2.92
    out['leg_root_MPa'] = {'leg_alone': round(Fs * (-1.3 - P.CRANK_NOSE_C['M'][1]) / (2 * P.CRANK_LEG_HALF * lb ** 2 / 6), 1),
                           'leg_and_belly': round(Fs * (-1.3 - P.CRANK_NOSE_C['M'][1]) / (W * lb ** 2 / 6), 1)}
    out['switch_rating_note'] = (f'neither switch publishes a static limit; the SKHL\'s 29.4 N is reached at a '
                                 f'{29.4 * A_OUT / LIN:.1f} N press')
    out['checks'] = {'rod_bending_le_20': max(s1, s3) <= 20, 'rod_shear_le_8': out['rod']['shear_MPa'] <= 8,
                     'bearing_le_10': max(out['rod']['cheek_bearing_MPa'], out['rod']['seat_bearing_MPa']) <= 10,
                     'crossbar_le_25_in_layer': out['crossbar']['bending_in_layer_MPa'] <= 25,
                     'crossbar_torsion_plus_shear_le_8': out['crossbar']['torsion_MPa'] + out['crossbar']['shear_MPa'] <= 8
                                                         and sd < 1e-3,
                     'roots_across_layers_le_12': max(out['crossbar_root_across_layers_MPa'], out['leg_root_MPa']['leg_and_belly']) <= 12}
    out['cheek'] = ck = cheek_stress(m)
    out['checks'].update(ck['checks'])
    return out


# The cheek (test 1, 2026-09-29: the open C's jaw cracked off at the bore and cranks came off the rod). Its stress across
# the layers is the test-1 study's 2D plane-stress FE of the cheek's section (a closed ring over |dx| 4.05..5.25, the
# rod's load a cos pressure over +-60 degrees about 31 degrees, fixed at the belly), recorded here, not recomputed, as
# EDGE_PRESS is: per N of pin load on one cheek, and at the 20 N over-press (19.5 N per cheek). The open C as built was
# 8.0 MPa per N (156 peak / 131 layer average at 20 N). The ring as it is since 2026-09-30 (the ring study's v2d: a round
# bore, the +Y face at -0.70, the fill forward under the rod) is the same FE on that section; the teardrop ring before
# it was 1.32 MPa per N (25.8 peak / 19.7 layer average at 20 N).
CHEEK_FE_PER_N = 1.26                                      # MPa per N per cheek, peak across the layers
CHEEK_FE_20N = {'peak': 24.5, 'layer_avg': 18.8}           # MPa at the 20 N over-press
CHEEK_LAYER_Y = (-3.0, -1.4)                               # the layer planes through the rod's bore (the crank prints
                                                           # on its pad end, +Y up, 0.2 layers)


def cheek_stress(m):
    """The cheek's rows (test 1): the ring closed round the rod at |dx| 4.65, with its wall round the bore (the least,
    and over the bore: from its top, ROD_AXIS + d/2, to the +Y face, CRANK_CHEEK_TRIM_Y: 4 layers); the stress
    across the layers at the largest click (<= 12, BELL-CRANK-SPEC's across-layer rule for crank roots) and at the 20 N
    over-press (layer average <= 25: the band cannot grow, since the key's cheek zone and the 45-degree roof leave 0.142
    at theta 16, so the 12 at 20 N is not met; accepted because clicks are 2.5x under 12, and a band cracked by a jab
    still leaves the rod captive: the ring is closed and its fill side holds); and the least layer area per cheek
    through the rod, a geometry guard (at the slicer's layer mid-planes, pad end on the bed). m: crank-M's mesh."""
    import crank_checks
    import numpy as np
    from shapely.geometry import LinearRing, LineString, Point, Polygon, box as sbox
    from shapely.ops import nearest_points
    py, pz = P.ROD_AXIS
    xr = (P.CRANK_CHEEK_RING['x0'] + P.CRANK_CHEEK[1]) / 2           # 4.65
    ring = {}
    top_y = py + P.CRANK_BORE['d'] / 2                             # the round bore's top, -1.50 (a layer boundary)
    for sd in (1, -1):
        S = crank_checks.section(m, sd * xr)
        polys = [g for g in getattr(S, 'geoms', [S]) if g.geom_type == 'Polygon']
        body = max(polys, key=lambda g: g.area)
        holes = [h for h in body.interiors if Polygon(h).contains(Point(py, pz))]
        if not holes:
            ring[f'{sd:+d}'] = {'closed': False}
            continue
        h = LinearRing(holes[0].coords)
        p, q = nearest_points(h, body.exterior)
        over = body.intersection(LineString([(top_y, pz), (P.CRANK_CHEEK_TRIM_Y, pz)])).length
        ring[f'{sd:+d}'] = {'closed': True, 'least_wall_mm': round(p.distance(q), 3),
                            'least_wall_from_yz': [round(p.x, 3), round(p.y, 3)], 'wall_over_the_bore_mm': round(over, 3)}
    kf = key_forces()
    fmax = max(max(v) for mu in (0.3, 0.45) for v in kf[f'mu_{mu}']['finger_force_N'].values())
    pin_per_N = math.hypot(1.0, LIN / A_OUT)
    click = CHEEK_FE_PER_N * pin_per_N * fmax / 2
    # the layer areas: each cheek's band (lip and ring) at the layer mid-planes y through the bore
    ys = [round(P.CRANK_PAD_END + 0.1 + 0.2 * k, 3) for k in range(60)]
    ys = [y for y in ys if CHEEK_LAYER_Y[0] - 1e-6 <= y <= CHEEK_LAYER_Y[1] + 1e-6]
    areas = []
    c0, c1 = P.CRANK_CHEEK
    for y in ys:
        s = m.section(plane_origin=(0, y, 0), plane_normal=(0, 1, 0))
        g = Polygon()
        for loop in (s.discrete if s is not None else []):
            if len(loop) >= 3:
                g = g.symmetric_difference(Polygon(loop[:, [0, 2]]).buffer(0))
        for sd in (1, -1):
            areas.append((round(g.intersection(sbox(min(sd * c0, sd * c1), -9, max(sd * c0, sd * c1), 9)).area, 3), y, sd))
    la = min(areas)
    out = {'ring_at_dx_4.65': ring,
           'click': {'largest_finger_force_N': round(fmax, 3), 'pin_per_N_of_press': round(pin_per_N, 3),
                     'per_cheek_N': round(pin_per_N * fmax / 2, 3), 'fe_MPa_per_N_per_cheek': CHEEK_FE_PER_N,
                     'across_layers_MPa': round(click, 2), 'as_built_open_C_MPa': round(8.0 * pin_per_N * fmax / 2, 1)},
           'overpress_20N_fe_MPa': CHEEK_FE_20N,
           'overpress_note': (f"20 N: the layer average {CHEEK_FE_20N['layer_avg']} is over the 12 across-layer rule for "
                              f"crank roots; the band cannot grow (the key's cheek zone and the 45-degree roof leave 0.142 "
                              f"at theta 16). Accepted: the largest click is {12 / click:.1f}x under 12, and a band cracked "
                              f"by a jab leaves the rod captive (closed ring, the fill side holds)"),
           'least_layer_area_mm2': {'area': la[0], 'y': la[1], 'cheek': f'{la[2]:+d}', 'layer_mid_planes_y': ys}}
    out['checks'] = {
        'cheek_ring_closed_wall_over_the_bore_ge_0.80_least_ge_0.70': all(
            r['closed'] and r['wall_over_the_bore_mm'] >= 0.80 - 1e-3 and r['least_wall_mm'] >= 0.70 for r in ring.values()),
        'cheek_across_layers_at_the_largest_click_le_12': click <= 12,
        'cheek_20N_overpress_layer_average_le_25': CHEEK_FE_20N['layer_avg'] <= 25,
        'cheek_least_layer_area_through_the_rod_ge_3.4': la[0] >= 3.4}
    return out


# ---- the rod's gate (SPEC2 rev 3, check 8) ------------------------------------------------------------------------------
# The axial load: rod end -> the gate's flat -> its flange -> the tub's two lips (all tub but the gate, which the tub
# holds; the lid only caps the gate in Z). SPEC2 section 7's model (C3's p4b one-way strip, c1_gate): a strip GATE_STRIP
# tall; the per-side load from statics about the rod's axis (y -2.50) on the flat bearing that crank_checks.gate_bearing
# reads off the built tub and gate; the lip a cantilever from its root (the cavity's straight end) to the bearing's
# centroid, the larger of 1.1 x the peak of (L + d) / t(d)^2 along the R0.40 round end and 1.3 x L / t0^2, judged on 25
# MPa (the across-layer reading: the lip also bends in Z); the flange from the web's edge to the bearing's centroid, no
# Kt, on 50 in-plane (the gate prints on its X face, so its bending lies in its layers); the flange wing's interlayer
# shear 1.5 V / A on 25.
GATE_STRIP = 3.53
GATE_LOADS = {'sideways click': 1.7, 'sideways 20 N over-press': 9.0, 'extreme': 17.6, '1.5 m drop': 27.0,
              'stiff-stop sensitivity': 33.0}
GATE_LIMITS = {'1.5 m drop': 2.0, 'stiff-stop sensitivity': 1.7, 'sideways 20 N over-press': 3.0, 'extreme': 3.0}
# The edge press (edge.md, 2026-09-27: the coupled rod-crank-key FE over the rod's whole length, run outside the repo;
# the rod, rail and crank are the same numbers in both sizes, so it holds for all four builds). Pre-existing, unchanged by
# the gate: recorded here, not recomputed.
EDGE_PRESS = {'20 N at the cap edge, 1x bearings': (18.9, 19.6), '20 N at the cap edge, 0.3x bearings': (24.4, 26.9),
              '20 N centred': (14.1, 14.4), 'click (TS365 2.94) at the cap edge': (2.0, 2.1),
              'note': 'MPa in the rod, per key SW9..SW2; the worst is SW2 pressed on its +X edge. The 0.3x column is over '
                      'the 15-20 limit (SPEC2 10.9, open).'}


def rod_end_play():
    """The rod's end play between the gate's flat and the +X wall: from the cut's tolerance alone, and with the stack
    (the cut +-0.2, the gate +-0.1, the wall +-0.1, the tail's squareness 0.05)."""
    span = P.ROD_SPAN[1] - P.ROD_SPAN[0]
    nom = span - P.ROD_CUT
    stack = P.ROD_CUT_TOL + 0.1 + 0.1 + 0.05
    cut = [round(nom - P.ROD_CUT_TOL, 3), round(nom + P.ROD_CUT_TOL, 3)]
    st = [round(nom - stack, 3), round(nom + stack, 3)]
    return {'span': [P.ROD_SPAN[0], P.ROD_SPAN[1]], 'cut': P.ROD_CUT, 'nominal': round(nom, 3), 'from_the_cut': cut,
            'with_the_stack': st, 'ok': cut == [0.3, 0.7] and st[0] >= 0.05 - 1e-9 and st[1] <= 0.95 + 1e-9}


def _lip_sigma(L, frac, F):
    """SPEC2 section 7's lip: the per-side load frac x F on the strip, lever L from the lip's root to the bearing."""
    S = P.GATE_SLOT
    t0, r = S['lip'], S['end_r']
    best = 0.0
    for i in range(81):
        dd = r * i / 80
        t = t0 + r - math.sqrt(max(r * r - dd * dd, 0.0))
        best = max(best, (L + dd) / t ** 2)
    return 6 * frac * F / GATE_STRIP * max(1.1 * best, 1.3 * L / t0 ** 2)


def gate_loads(bearing):
    """SPEC2 check 8: every load of GATE_LOADS at every Y offset of the gate (bearing: crank_checks.gate_bearing's rows
    at one z), the lip (SF on 25), the flange (on 50 in-plane) and the flange's interlayer shear (on 25). Limits
    (GATE_LIMITS): the 27 N drop >= 2.0 on all three; 33 N ACCEPTED at a lip SF >= 1.7; 9 and 17.6 N >= 3."""
    S, G = P.GATE_SLOT, P.GATE
    yrod = P.ROD_AXIS[0]
    roots = S['cavity']
    tf = G['flange']
    rows = {}
    for name, F in GATE_LOADS.items():
        worst = None
        per_shift = {}
        for r in bearing.values():
            (a0, a1), (b0, b1) = r['bearing']['-Y'], r['bearing']['+Y']
            c1, c2 = (a0 + a1) / 2, (b0 + b1) / 2
            l1, l2 = yrod - c1, c2 - yrod
            f1, f2 = l2 / (l1 + l2), l1 / (l1 + l2)
            web = (G['web_y'][0] + r['shift'], G['web_y'][1] + r['shift'])
            lips, fls, shs = [], [], []
            for c, f, root, we in ((c1, f1, roots[0], web[0]), (c2, f2, roots[1], web[1])):
                lips.append(_lip_sigma(abs(c - root), f, F))
                fls.append(6 * f * F / GATE_STRIP * abs(we - c) / tf ** 2)
                shs.append(1.5 * f * F / (tf * GATE_STRIP))
            row = {'lip_MPa': round(max(lips), 2), 'flange_MPa': round(max(fls), 2), 'shear_MPa': round(max(shs), 2),
                   'lip_SF_25': round(25 / max(lips), 2), 'flange_SF_50': round(50 / max(fls), 2),
                   'shear_SF_25': round(25 / max(shs), 2), 'load_split': [round(f1, 3), round(f2, 3)]}
            per_shift[f"{r['shift']:+.2f}"] = row
            if worst is None or row['lip_SF_25'] < worst['lip_SF_25']:
                worst = row
        mins = {k: min(v[k] for v in per_shift.values()) for k in ('lip_SF_25', 'flange_SF_50', 'shear_SF_25')}
        lim = GATE_LIMITS.get(name)
        if name == 'stiff-stop sensitivity':
            verdict = 'ACCEPTED' if mins['lip_SF_25'] >= lim - 1e-9 else 'FAIL'
        elif lim is not None:
            verdict = 'PASS' if min(mins.values()) >= lim - 1e-9 else 'FAIL'
        else:
            verdict = 'reported'
        rows[name] = {'N': F, 'centred': per_shift['+0.00'], 'min_SF': mins, 'limit': lim, 'verdict': verdict,
                      'per_shift': per_shift}
    return rows


def rod_span_bending(F_pin, xc, kfac=1.0, h=0.02):
    """The rod over its whole length (d 1.72, its tail at the gate's flat, ROD_CUT long) on elastic bearings where the
    tub holds it - the sliver's bore past its lead-in, the rings and the open seats (tub.rail_segments), none in the
    cheek slots or past the right ring - loaded by one crank's two cheeks at key centre xc (Hermite elements, a Winkler
    bed of 0.8 E per mm, as rod_bending). Returns (max bending stress MPa, max deflection mm)."""
    import numpy as np
    from scipy.sparse import lil_matrix
    from scipy.sparse.linalg import spsolve
    d = P.ROD_D_RANGE[0]
    I = math.pi * d ** 4 / 64
    Zs = math.pi * d ** 3 / 32
    x0 = P.ROD_STOP_X0
    n = int(round(P.ROD_CUT / h)) + 1
    x = np.linspace(x0, x0 + P.ROD_CUT, n)
    h = x[1] - x[0]
    k = np.zeros(n)
    sup = [(P.GATE_SLOT_X[2] + P.GATE_SLOT['sliver_lead'], P.WALL_X0)] + [(a, b) for kind, a, b in tub.rail_segments() if kind != 'slot']
    for a, b in sup:
        k[(x >= a) & (x <= b)] = kfac * E * 0.8
    q = np.zeros(n)
    c0, c1 = P.CRANK_CHEEK
    for sg in (-1, 1):
        a, b = sorted((xc + sg * c0, xc + sg * c1))
        m = (x >= a) & (x <= b)
        q[m] = (F_pin / 2) / (b - a)
    N = 2 * n
    K = lil_matrix((N, N))
    Fv = np.zeros(N)
    ke = E * I / h ** 3 * np.array([[12, 6 * h, -12, 6 * h], [6 * h, 4 * h * h, -6 * h, 2 * h * h],
                                    [-12, -6 * h, 12, -6 * h], [6 * h, 2 * h * h, -6 * h, 4 * h * h]])
    for e in range(n - 1):
        idx = [2 * e, 2 * e + 1, 2 * e + 2, 2 * e + 3]
        for i in range(4):
            for j in range(4):
                K[idx[i], idx[j]] += ke[i, j]
    for i in range(n):
        K[2 * i, 2 * i] += k[i] * h
        Fv[2 * i] += q[i] * h
    u = spsolve(K.tocsr(), Fv)
    w = u[0::2]
    M = E * I * np.gradient(np.gradient(w, h), h)
    return float(abs(M).max() / Zs), float(abs(w).max())


def gate_mechanics(tub_s):
    """SPEC2 rev 3 check 8: end play, the gate's loads at every Y offset (the bearing read off the built parts at z -1.0),
    the rod's end on the flat at the 27 N drop, the drop's cap from the rod's axial stiffness, the rod over its new span
    at a centred 20 N press on each key (<= 14.6 MPa at 1x bearings), and the edge press (recorded, EDGE_PRESS)."""
    import crank_checks
    ep = rod_end_play()
    br = {k: v for k, v in crank_checks.gate_bearing(tub_s, zs=(-1.0,)).items()}
    loads = gate_loads(br)
    # the rod's end on the flat: the disc (d 1.72) below the flat's end (its axis SAG past it, face down)
    r = P.ROD_D_RANGE[0] / 2
    hgt = P.GATE_SLOT['floor_z'] - (P.ROD_AXIS[1] + crank_checks.SAG)
    seg = r * r * math.acos(hgt / r) - hgt * math.sqrt(r * r - hgt * hgt)
    area = math.pi * r * r - seg
    # the drop: a 1.5 m fall, the rod (its own mass) stopped by its axial stiffness E A / L
    v = math.sqrt(2 * 9.81 * 1.5)
    A = math.pi * r * r
    mass = 1.24e-3 * A * P.ROD_CUT * 1e-3                    # kg
    kax = E * A / P.ROD_CUT * 1e3                            # N/m
    hit = v * math.sqrt(kax * mass)
    Fs = OVERPRESS * LIN / A_OUT
    pin = math.hypot(OVERPRESS, Fs)
    span = {}
    for ref in P.KEY_REFS:
        s1, w1 = rod_span_bending(pin, keys.centre(ref))
        s3, _ = rod_span_bending(pin, keys.centre(ref), kfac=1 / 3)
        span[ref] = {'bending_MPa': round(s1, 2), 'bending_soft_bearings_MPa': round(s3, 2), 'deflection_um': round(w1 * 1000, 1)}
    worst = max(v_['bending_MPa'] for v_ in span.values())
    return {'end_play': ep, 'loads': loads,
            'rod_end_on_flat': {'area_mm2': round(area, 3), 'MPa_at_27N': round(27.0 / area, 1), 'covered_past_axis': round(hgt, 3)},
            'drop_cap': {'v_m_s': round(v, 2), 'rod_g': round(mass * 1e3, 3), 'axial_N_mm': round(kax / 1e3, 1),
                         'hit_N': round(hit, 1)},
            'rod_new_span': {'press_N': OVERPRESS, 'pin_N': round(pin, 1), 'span': [P.ROD_STOP_X0, round(P.ROD_STOP_X0 + P.ROD_CUT, 2)],
                             'per_key': span, 'worst_MPa': worst, 'ok': worst <= 14.6},
            'edge_press': EDGE_PRESS,
            'checks': {'end_play': ep['ok'], **{k: v_['verdict'] for k, v_ in loads.items()},
                       'rod_new_span_le_14.6': worst <= 14.6}}


def key_sweep(tub_s, lid_s, mid_s):
    """Check 3: each key from its stop (its hooks under the slots' roof, KEY_W_OUT) down to its lowest in use (the crank
    at +16 degrees) and on down to -3.4 (a key sunk before the board, its crank near +55: KEY_SINK), in 3D: the key,
    hooks and all, against the tub, the lid, the midplate, the board and its switch (all nil). Its +Y face on its guide
    (the rail's face and the opening's edge) over at least 2.5. The crown's contact on the pusher is key_fit's; the
    hooks' own checks are key_hooks'."""
    import crank_checks
    hwsol = hw.solids()
    low = crank.key_lift(16.0)
    stop = crank_checks.STOP
    lifts = [round(stop - (stop - low) * i / 10, 3) for i in range(11)]
    sunk = [x for x in KEY_SINK if x < low]
    out = {'lifts_mm': lifts, 'sunk_lifts_mm': sunk}
    from geom import box
    for ref in P.KEY_REFS:
        kn = keys.build(ref).val()
        xc = keys.centre(ref)
        reg = box(xc - 7, xc + 7, P.Y0 - 1, 1.5, P.Z_BACK - 1, P.Z_FRONT + 3).val()
        env = {'tub': tub_s.intersect(reg), 'lid': lid_s.intersect(reg), 'midplate': mid_s.intersect(reg),
               'PCB': hwsol['PCB'].intersect(reg), 'switch': hwsol[ref]}
        rows = []
        for lf in lifts + sunk:
            k = kn.moved(cq.Location(cq.Vector(0, 0, lf)))
            row = {'lift': lf}
            for name, o in env.items():
                row[name] = round(k.intersect(o).Volume(), 4) if o.Volume() > 0 else 0.0
            rows.append(row)
        out[ref] = rows
    # the +Y face's engagement with its guide (body zone; the seat's face from -0.575, the opening's edge to the face),
    # per X band: the face's bottom is the body's (KEY_BODY z0), but over dx -3.30..-1.00 the body's -X step is cut 45
    # degrees (test 1: it would face the bed as the key prints on its -X end), so there it is max(z0, 2.70 - (dx +
    # 3.30)). The check is read on the bands the cut leaves whole (the face the key rides on, 4.3 wide, as before);
    # the cut bands are reported: their face starts at 2.70 at dx -3.30, as over the cheeks (the cheek zone) always
    guide_lo = -0.575
    Bd, czz = P.KEY_BODY, P.KEY_CHEEK_ZONE['z0']
    x7 = round(-Bd['half'] + (czz - Bd['z0']), 3)                                  # -1.00: where the cut ends

    def engage(lf, dx):
        zb = max(Bd['z0'], czz - (dx + Bd['half']))
        return round(min(P.Z_FRONT, keys.top() + lf - P.KEY_CAP_CHAMFER) - max(guide_lo, zb + lf), 3)
    dxs = [round(-Bd['half'] + 0.05 * i, 3) for i in range(int(round(2 * Bd['half'] / 0.05)) + 1)]
    eng = {lf: min(engage(lf, dx) for dx in dxs if dx >= x7) for lf in lifts + [0.0]}
    cut = {lf: min(engage(lf, dx) for dx in dxs if dx < x7) for lf in lifts + [0.0]}
    out['guide_engagement_mm'] = eng
    out['guide_engagement_cut_bands_mm'] = {'dx': [-Bd['half'], x7], 'min_by_lift': cut,
                                            'at_rest': cut[0.0], 'at_the_stop': cut[lifts[0]],
                                            'lifts_le_0_min': min(v for lf, v in cut.items() if lf <= 0),
                                            'note': 'reported, no limit: the key rides on the whole bands'}
    bad = [f"{ref} lift {r['lift']}: {k} {r[k]}" for ref in P.KEY_REFS for r in out[ref]
           for k in ('tub', 'lid', 'midplate', 'PCB', 'switch') if r[k] > 1e-3]
    out['checks'] = {'no_interference': not bad, 'guide_engagement_ge_2.5': min(eng.values()) >= 2.5}
    out['failures'] = bad
    return out


KEY_SINK = (-1.6, -2.6, -3.4)            # a key sunk before the board, face up (its crank toward +60): key_sweep, key_hooks
HOOK_R = {'hook_tip': 0.21, 'roof_edge': 0.10}   # FDM corner radii (the diagnosis' model): the hook's tip in its key's
                                          # layer plane (the outer wall's half line), the roof's edge across the tub's layers
HOOK_PULL = 5.0                           # N: a firm thumb pushing a key outward from inside (RECOMMENDATION 5, test 2)


def crank_gravity():
    """The crank's mass and its centre of mass from the rod (crank-T; crank-M alike), and its gravity torque about the
    rod face up (+: pressed, toward the plunger)."""
    import crank_checks
    m = crank_checks.to_mesh(crank.build('T').val())
    mass = float(m.volume) * 1.24e-3
    cg = m.center_mass
    r = (float(cg[1]) - P.ROD_AXIS[0], float(cg[2]) - P.ROD_AXIS[1])
    w = mass * 9.81e-3
    return {'mass_g': round(mass, 4), 'weight_N': round(w, 6), 'cg_from_rod_yz': [round(r[0], 3), round(r[1], 3)],
            'crank_torque_face_up_Nmm': -r[0] * w}


def key_hooks(tub_s):
    """The hook keys' checks (test 2, 2026-09-30; keystab RECOMMENDATION 6.4 and the diagnosis' missing checks):
      stop       each key 0.02 short of KEY_W_OUT and at rest, pressed to -0.8 / -1.6 / -2.6 / -3.4, centred, pushed
                 0.01 short of its X play either way (0.29: KEY_SIDE_GAP 0.30), 0.02 short of the chin side's
                 (0.38: KEY_CHIN_GAP 0.40), and both at once as far as the cap's R0.3 chin corners let it into the
                 opening's R0.5 ones, less 0.015 (0.17 in X at 0.38; 0.22 at the 0.35 gap: those corners are the
                 stop there), in 3D against the built tub: no overlap; 0.05 past KEY_W_OUT only the hooks meet it,
                 under the slots' roof
      window     KEY_W_OUT against the switch's rest scatter at the key (the crank's kinematics: board +-0.2, TS365 tip
                 +-0.2, MJTP +-0.2) + KEY_CHAIN_PRINT + KEY_STOP_MARGIN: the stop never presses a plunger
      walls      read off the built tub's YZ sections over every slot's X band (every 0.1): the chin wall left behind
                 the slot >= KEY_SLOT wall in every layer from the rim to the roof (the rim's own layer and the seam
                 chamfer's height reported apart: the tub has no chamfer there, KEY_SLOT relief; hverify1 F1), and
                 >= KEY_SLOT above over the roof at the slot's back
      tilt       rotation about Y: on the hooks (face down, both flat under one roof) from a 0.1 print error between
                 them, <= 1.0 deg; free (nothing under the key) between the opening's sides and the slots' / webs'
                 (reported); the crown under the whole cap (face up)
      pull_out   the hook's top on the roof net of FDM corner radii (HOOK_R): flat bearing >= 0 and the +Y motion that
                 unhooking needs (the gross overlap) against the key's +Y room (0: its +Y face rides the rail); the
                 hook's root at HOOK_PULL (shear <= 8, bending in its layer plane <= 25 MPa), its bearing reported
      crank      the hooks against the crank (both variants) over its free swing, -20 (its belly on the rail) to +60
                 degrees, in YZ shadows (the hooks over their X bands; the crank over those grown by the key's X play
                 and its own float): the key riding the crown and at its stop, >= 0.10. With a key in, the crank cannot
                 turn past theta_stop (-11.4: its crown on the pusher of a key at its stop), so -20..theta_stop is
                 reported, not judged (it needs the crown inside the pusher). The root (KEY_ROOT) past the pusher's
                 chin end the same way: the crown rides its plane (>= 0), the rest of the crank >= 0.10
      gravity    the key and its crank in each pose (face up / down, upright chin down / up, on either side): the net
                 force at the key (+ closes the chain onto the plunger) and what holds the key"""
    import crank_checks as CC
    import numpy as np
    from shapely import affinity
    from shapely.geometry import LineString, box as sbox
    from geom import box
    Hk, Sl, W = P.KEY_HOOK, P.KEY_SLOT, P.KEY_W_OUT
    zr, (hz0, hz1) = P.KEY_SLOT_ROOF, P.KEY_HOOK_Z
    out = {'params': {'W_OUT': W, 'slot_dx': list(Sl['dx']), 'slot_back': Sl['back'], 'slot_roof': zr,
                      'hook_dx': list(Hk['dx']), 'hook_tip': Hk['tip'], 'hook_z_at_rest': [hz0, hz1],
                      'hook_lead': P.KEY_HOOK_LEAD}}
    checks = {}
    # ---- stop and overlaps (3D) ----
    sx, sy = round(P.KEY_SIDE_GAP - 0.01, 3), round(P.KEY_CHIN_GAP - 0.02, 3)
    # the chin corners (key R0.3 inside the opening's R0.5): the key's corner centre may come within ro - rk of the
    # opening's; at the chin push sy that allows sd in X (0.237 at the 0.35 gap, 0.187 at 0.30), less 0.015
    ro, rk = P.KEY_OPENING['r'], P.KEY_CORNER_R[1]
    ey = P.KEY_CHIN_GAP + rk - ro - sy
    sd = math.floor(100 * (P.KEY_SIDE_GAP - (ro - rk) + math.sqrt((ro - rk) ** 2 - ey ** 2) - 0.015) + 1e-6) / 100
    shifts = [(0.0, 0.0), (-sx, 0.0), (sx, 0.0), (0.0, -sy), (-sd, -sy), (sd, -sy)]
    lifts = [0.0, -0.8, -1.6, -2.6, -3.4, round(W - 0.02, 3)]
    fits = {}
    for ref in P.KEY_REFS:
        xc = keys.centre(ref)
        t3 = tub_s.intersect(box(xc - 7.5, xc + 7.5, P.Y0 - 1, 1.5, P.SEAM - 3, P.Z_FRONT + 3).val())
        k3 = keys.build(ref).val()
        worst = (0.0, None)
        for dx, dy in shifts:
            for lf in lifts:
                v = k3.moved(cq.Location(cq.Vector(dx, dy, lf))).intersect(t3).Volume()
                if v > worst[0]:
                    worst = (round(v, 5), [dx, dy, lf])
        past = k3.moved(cq.Location(cq.Vector(0, 0, W + 0.05))).intersect(t3)
        pv = past.Volume()
        where, on_roof = None, False
        if pv > 1e-6:
            pb = past.BoundingBox()
            where = [round(x, 3) for x in (pb.xmin - xc, pb.xmax - xc, pb.ymin, pb.ymax, pb.zmin, pb.zmax)]
            on_roof = all(Sl['dx'][0] - 1e-3 <= abs((q.BoundingBox().xmin + q.BoundingBox().xmax) / 2 - xc) <= Sl['dx'][1] + 1e-3
                          and q.BoundingBox().zmin >= zr - 1e-3 and q.BoundingBox().ymin >= Hk['tip'] - 1e-3
                          and q.BoundingBox().ymax <= P.KEY_Y[0] + 1e-3 for q in past.Solids())   # within the hooks
        fits[ref] = {'overlap_mm3_worst': worst[0], 'at_dx_dy_lift': worst[1], 'past_stop_0.05_mm3': round(pv, 5),
                     'past_stop_where_dx_y_z': where, 'past_stop_only_hooks_under_the_roof': on_roof}
    out['stop'] = {'shifts_dx_dy': shifts, 'lifts': lifts, 'keys': fits}
    checks[f'no key-tub overlap at rest, pressed to -3.4 and 0.02 short of the stop (centred, +-{sx} X, {sy} chin, both)'] = \
        all(r['overlap_mm3_worst'] <= 1e-4 for r in fits.values())
    checks[f'the stop engages at W_OUT {W}: 0.05 past it only the hooks meet the tub, under the roof'] = \
        all(r['past_stop_0.05_mm3'] > 1e-4 and r['past_stop_only_hooks_under_the_roof'] for r in fits.values())
    # ---- the stop window ----
    rest = {}
    for tip in (-0.2, 0.0, 0.2):
        for dy in (-P.TUB_BOARD_DY, 0.0, P.TUB_BOARD_DY):
            rest[f'TS365 tip {tip:+.1f} board {dy:+.1f}'] = crank.key_lift(crank.rest_theta(P.TS365['tip_y_nom'] + tip + dy, 'T'))
    for dy in (-P.TUB_BOARD_DY, 0.0, P.TUB_BOARD_DY):
        rest[f'MJTP board {dy:+.1f}'] = crank.key_lift(crank.rest_theta(P.PLUNGER_Y + dy, 'M'))
    wr = max(rest.values())
    need = wr + P.KEY_CHAIN_PRINT + P.KEY_STOP_MARGIN
    out['window'] = {'rest_lift_mm': {k: round(v, 3) for k, v in rest.items()}, 'worst_rest_lift': round(wr, 3),
                     'chain_print': P.KEY_CHAIN_PRINT, 'stop_margin': P.KEY_STOP_MARGIN, 'needs': round(need, 3),
                     'W_OUT': W, 'face_down_free_travel_mm': [round(W - wr, 3), round(W - min(rest.values()), 3)]}
    checks[f'W_OUT {W} >= worst rest {wr:.3f} + chain {P.KEY_CHAIN_PRINT} + stop {P.KEY_STOP_MARGIN} = {need:.3f}'] = W >= need - 1e-9
    # ---- walls behind the slots, off the built tub ----
    m = CC.to_mesh(tub_s.intersect(box(P.X0 - 1, P.X1 + 1, P.Y0 - 1, P.BOT_IN + 1.0, P.SEAM - 1, P.Z_FRONT + 1).val()))
    a, b = Sl['dx']
    zs = [round(z, 3) for z in np.arange(P.SEAM + 0.05, zr - 0.02 + 1e-9, 0.05)]
    wall = {'wall': (9.0, None), 'rim': (9.0, None), 'rim layer': (9.0, None)}
    above = (9.0, None)
    for xc in tub.key_x():
        for sd in (-1, 1):
            for dx in list(np.arange(a + 0.013, b - 0.013, 0.1)) + [b - 0.013]:
                x = xc + sd * dx
                g = CC.section(m, x).intersection(sbox(P.Y0 - 0.5, P.SEAM - 0.5, P.BOT_IN + 0.5, P.Z_FRONT + 0.5))
                for z in zs:
                    w_ = g.intersection(LineString([(P.Y0 - 0.5, z), (Sl['back'] - 0.001, z)])).length
                    zone = ('rim layer' if z < P.SEAM + P.LAYER else 'rim' if z < P.SEAM + P.SEAM_CHAMFER else 'wall')
                    if w_ < wall[zone][0]:
                        wall[zone] = (round(w_, 3), [round(sd * dx, 3), z])
                ab = g.intersection(LineString([(Sl['back'] + 0.01, zr + 0.001), (Sl['back'] + 0.01, P.Z_FRONT + 0.5)])).length
                if ab < above[0]:
                    above = (round(ab, 3), round(sd * dx, 3))
    R, yc = P.FRONT_EDGE_R, P.Y0 + P.FRONT_EDGE_R                 # the chin's front round (params.chin_outer_y)
    z_back = P.Z_FRONT if Sl['back'] >= yc else P.Z_FRONT - R + math.sqrt(max(0.0, R ** 2 - (Sl['back'] - yc) ** 2))
    model = {'wall_at_the_top_open_layer': round(Sl['back'] - P.chin_outer_y(zr - P.LAYER / 2), 3),
             'above_roof_at_back': round(z_back - zr, 3)}
    out['walls'] = {'least_wall_behind_the_slot': {k: {'mm': v[0], 'at_dx_z': v[1]} for k, v in wall.items()},
                    'least_above_the_roof_at_the_back': {'mm': above[0], 'at_dx': above[1]}, 'params_model': model,
                    'limits': {'wall': Sl['wall'], 'rim (the rim layer and the seam chamfer height)': Sl['wall'],
                               'above': Sl['above']}, 'relief_x': [round(v, 3) for v in tub.rim_relief()]}
    checks[f"wall behind every slot {wall['wall'][0]} >= {Sl['wall']} (above the seam chamfer's height)"] = wall['wall'][0] >= Sl['wall'] - 2e-3
    least_rim = min(wall['rim'][0], wall['rim layer'][0])
    checks[f"wall behind every slot at the rim {least_rim} >= {Sl['wall']} (the rim layer and the chamfer's height: no chamfer "
           f"over the key row)"] = least_rim >= Sl['wall'] - 2e-3
    checks[f"material over every roof at the slot's back {above[0]} >= {Sl['above']}"] = above[0] >= Sl['above'] - 2e-3
    # ---- X-tilt ----
    span = 2 * (Hk['dx'][0] + Hk['dx'][1]) / 2
    on = math.degrees(math.atan(0.1 / span))
    top_z = P.Z_FRONT - P.KEY_EDGE_CHAMFER
    low = min(P.WEB['z0'], hz0)
    free = math.degrees(math.atan((P.KEY_SIDE_GAP + (P.SLOT[1] - P.KEY_HALF)) / (top_z - low)))
    out['tilt'] = {'on_the_hooks_deg': round(on, 2), 'hook_centres_apart': round(span, 3),
                   'on_the_hooks_end_to_end_at_the_cap_mm': round(2 * P.KEY_HALF * math.tan(math.radians(on)), 3),
                   'free_deg': round(free, 1), 'free_note': 'nothing under the key (reported): face down both hooks '
                   'level it, face up the crown (the full width) does',
                   'crown_length': 2 * P.CRANK_HALF, 'cap_width': 2 * P.KEY_HALF}
    checks[f'X-tilt on the hooks {on:.2f} deg <= 1.0 (0.1 between them, {span:.2f} apart)'] = on <= 1.0
    checks['the crown runs under the whole cap (face up, a corner press needs no guide)'] = 2 * P.CRANK_HALF >= 2 * P.KEY_HALF
    # ---- pull-out ----
    edge = P.BOT_IN if zr < P.LIP - 1e-6 else P.KEY_OPENING['y'][0]      # the roof's edge: the wall's face / the ledge
    gross = round(edge - Hk['tip'], 3)
    flat = round(gross - HOOK_R['hook_tip'] - HOOK_R['roof_edge'], 3)
    ang = 0.0 if flat >= 0 else math.degrees(math.asin(min(1.0, -flat / (HOOK_R['hook_tip'] + HOOK_R['roof_edge']))))
    hx = Hk['dx'][1] - Hk['dx'][0]
    root = hx * Hk['h']
    arm = P.KEY_Y[0] - (Hk['tip'] + edge) / 2
    shear = HOOK_PULL / (2 * root)
    bend = (HOOK_PULL / 2) * arm / (hx * Hk['h'] ** 2 / 6)
    bearing = (HOOK_PULL / 2) / (gross * (hx - P.KEY_BED_END[0]))
    out['pull_out'] = {'roof_edge_y': edge, 'bearing_gross_mm': gross, 'corner_radii': HOOK_R,
                       'flat_bearing_net_mm': flat, 'contact_normal_from_z_deg': round(ang, 1),
                       'unhook_needs_plus_y_mm': gross, 'key_plus_y_room_mm': 0.0,
                       'at_N': HOOK_PULL, 'root_shear_MPa': round(shear, 2), 'root_bending_in_layer_MPa': round(bend, 1),
                       'bearing_MPa': round(bearing, 1)}
    checks[f'pull-out: flat bearing net of the FDM radii {flat} >= 0 (the pull stays along Z)'] = flat >= 0
    checks[f'pull-out: unhooking needs {gross} of +Y, the rail leaves 0'] = gross > 0
    checks[f'hook roots at {HOOK_PULL} N: shear {shear:.1f} <= 8, bending {bend:.1f} <= 25 MPa (in layer)'] = shear <= 8 and bend <= 25
    # ---- the hooks against the crank, -20..+60 ----
    hm = CC.to_mesh(keys.hooks().val())
    bands = [(Hk['dx'][0], Hk['dx'][1])]
    H = CC.shadow(hm, bands, 0.0)
    Hl = CC.shadow(hm, [(round(Hk['dx'][0] - P.KEY_HOOK_LEAD, 3), Hk['dx'][0])], 0.0, sides=(1,))
    H = H.union(Hl).buffer(0)
    play = P.KEY_SIDE_GAP + CC.CRANK_FLOAT
    crank_band = [(round(Hk['dx'][0] - P.KEY_HOOK_LEAD - play, 3), P.CRANK_HALF)]
    th_stop = CC.THETA_STOP
    cr = {}
    for v in 'MT':
        C0 = CC.shadow(CC.to_mesh(crank.build(v).val()), crank_band, 0.0)
        best, below = (9.0, None), (9.0, None)
        for th in range(-20, 61):
            C = CC.rot(C0, th)
            ride = crank.key_lift(th)
            for lf in sorted({min(ride, W), W}):
                g_ = CC.d(affinity.translate(H, 0, lf), C)
                if th < th_stop:
                    if g_ < below[0]:
                        below = (round(g_, 3), [th, round(lf, 3)])
                elif g_ < best[0]:
                    best = (round(g_, 3), [th, round(lf, 3)])
        cr[f'crank-{v}'] = {'min_gap': best[0], 'at_theta_lift': best[1],
                            'below_theta_stop_unreachable': {'min_gap': below[0], 'at_theta_lift': below[1]}}
    out['crank'] = {'theta': [-20, 60], 'judged_from': th_stop, 'crank_band_dx': crank_band, 'rows': cr,
                    'note': 'the key riding the crown and at its stop; below theta_stop the crown would sit inside the '
                            'pusher of a key at its stop: reported'}
    worst_c = min(r['min_gap'] for r in cr.values())
    checks[f'hooks vs crank over {th_stop}..+60 deg (-20..{th_stop}: no crank gets there with a key in) >= 0.10 ({worst_c})'] = worst_c >= 0.10
    # the root (KEY_ROOT) past the pusher's chin end, the same way. Its underside is the pusher's plane, which rides the
    # crown: the crown's circle falls away from it (tangent), so only the crown comes near (reported, >= 0); the rest of
    # the crank is judged >= 0.10. (Inside the pusher's chin end the root is the pusher: crank_checks' sweep.)
    Pu = P.KEY_PUSHER
    root_yz = sbox(Hk['tip'], Pu['z0'], Pu['y'][0], hz1)
    root_band = [(round(P.KEY_HALF - P.KEY_ROOT - play, 3), P.CRANK_HALF)]
    (ccy, ccz), ccr = P.CRANK_CROWN
    from shapely.geometry import Point
    rr = {}
    for v in 'MT':
        C0 = CC.shadow(CC.to_mesh(crank.build(v).val()), root_band, 0.0)
        best, best_nc = (9.0, None), (9.0, None)
        for th in range(-20, 61):
            if th < th_stop:
                continue
            C = CC.rot(C0, th)
            crown = CC.rot(Point(ccy, ccz).buffer(ccr + 0.001, 64), th)
            for lf in sorted({min(crank.key_lift(th), W), W}):
                R = affinity.translate(root_yz, 0, lf)
                g_, gn = CC.d(R, C), CC.d(R, C.difference(crown))
                if g_ < best[0]:
                    best = (round(g_, 3), [th, round(lf, 3)])
                if gn < best_nc[0]:
                    best_nc = (round(gn, 3), [th, round(lf, 3)])
        rr[f'crank-{v}'] = {'min_gap': best[0], 'at_theta_lift': best[1], 'min_gap_but_the_crown': best_nc[0],
                            'at_theta_lift_but_the_crown': best_nc[1]}
    out['crank']['root'] = {'yz': [round(v, 3) for v in root_yz.bounds], 'band_dx': root_band, 'rows': rr}
    worst_r = min(r['min_gap_but_the_crown'] for r in rr.values())
    worst_rc = min(r['min_gap'] for r in rr.values())
    checks[f'the root past the pusher vs crank over {th_stop}..+60 deg: the crown {worst_rc} >= 0 (it rides the '
           f'root\'s plane), the rest {worst_r} >= 0.10'] = worst_rc >= 0 and worst_r >= 0.10
    # ---- gravity per pose ----
    kv = keys.build().val().Volume()
    wk = kv * 1.24e-6 * 9.81
    cgv = crank_gravity()
    wc = cgv['weight_N']
    ry, rz = cgv['cg_from_rod_yz']
    poses = {'face up': (0, 0, -1), 'face down': (0, 0, 1), 'upright, chin down': (0, -1, 0),
             'upside down, chin up': (0, 1, 0), 'on its -X side': (-1, 0, 0), 'on its +X side': (1, 0, 0)}
    grav = {}
    for n, (gx, gy, gz) in poses.items():
        tc = ry * gz * wc - rz * gy * wc                     # the crank's torque about the rod (+: toward the plunger)
        tk = LIN * (-gz) * wk if gz < 0 else 0.0             # the key's weight on the crown (face up only)
        net = (tc + tk) / LIN
        row = {'net_at_key_N': round(net, 5)}
        if gz > 0:
            row['held_by'] = f'its hooks: the key drops {W} (W_OUT) onto them, its crank follows it (theta {th_stop})'
            row['ok'] = True
        elif gy < 0:
            f3, f45 = 0.3 * wk, 0.45 * wk
            row.update({'key_friction_N_mu_0.3_0.45': [round(f3, 5), round(f45, 5)],
                        'hold_ratio': [round(f3 / max(1e-9, -net), 2), round(f45 / max(1e-9, -net), 2)] if net < 0 else None,
                        'held_by': 'the chain closed' if net >= 0 else "the key's friction on its chin side"})
            row['ok'] = net >= 0 or f3 >= -net
        elif gx:
            row.update({'held_by': 'neutral: gravity along the rod; the key and crank stay where they are', 'ok': True})
        else:
            row.update({'held_by': 'the chain closed onto the plunger', 'ok': net > 0})
        grav[n] = row
    out['gravity'] = {'key_mass_g': round(kv * 1.24e-3, 4), 'key_weight_N': round(wk, 5), 'crank': cgv, 'poses': grav}
    checks['gravity: every pose holds the key (face up closed, face down on its hooks, upright friction >= the crank at mu 0.3)'] = \
        all(r['ok'] for r in grav.values())
    out['checks'] = {k: bool(v) for k, v in checks.items()}
    return out


def side_key_sweep(tub_s, lid_s, mid_s):
    """Each side key - everything past its root in the lid's wall - swung in about that root until
    the nub has gone 0 .. 115 % of the way to the stop, against the tub, the lid's body, the midplate,
    the PCB and its own switch's body. The plunger (its whole 1.24 mm stand-off from the collar) is
    what the nub is meant to push, so it is left out; 'plunger_push_mm' is how far in it has gone. A
    rigid swing about the root stands in for the bar's bending: close to it at the nub, a little
    short of it at the free end, which is why the tub's first contact is reported as a travel. The
    first 0.3 mm past the root is left out: it is fused to the lid's wall, and a rigid swing about the
    root would turn its inner half into that wall."""
    import body, sidekeys
    hwsol = hw.solids()
    out = {}
    for t in body.side_tabs():
        s, a = t['side'], t['away']
        xo = P.X1 if s > 0 else P.X0
        yf = sorted((t['flex_root'] + a * 0.3, t['flex_root'] + a * 40))   # the first 0.3 is fused to the wall
        k0 = sidekeys.build(t['ref']).intersect(
            cq.Workplane('XY').box(80, yf[1] - yf[0], 30).translate((30, (yf[0] + yf[1]) / 2, 0))).val()
        ax = xo - s * P.TAB_T / 2
        L = abs(t['face'][1] - t['flex_root'])
        sw = hwsol[t['ref']]
        n = hw.switch_plunger(t['ref'])['nub']
        fx = t['face'][0]
        x0p = fx - s * 1.24                                  # the plunger stands 1.24 proud of its collar
        nb = cq.Solid.makeBox(1.24 + 0.02, n[3] - n[2] + 0.02, n[5] - n[4] + 0.02,
                              cq.Vector(min(fx, x0p) - 0.01, n[2] - 0.01, n[4] - 0.01))
        body_, plunger = sw.cut(nb), sw.intersect(nb)
        rows = []
        for f in (0.0, 0.25, 0.5, 0.75, 0.9, 1.0, 1.15):
            d = f * P.TAB_VOID
            psi = math.degrees(s * d / (a * L))
            k = cq.Workplane(obj=k0).rotate((ax, t['flex_root'], 0), (ax, t['flex_root'], 1), psi).val()
            row = {'nub_travel_mm': round(d, 3)}
            for name, other in (('tub', tub_s), ('lid', lid_s), ('midplate', mid_s), ('pcb', hwsol['PCB']), ('switch_body', body_)):
                row[name] = round(k.intersect(other).Volume(), 4)
            pi = k.intersect(plunger)
            row['plunger_push_mm'] = round(max(0.0, d - t['gap']), 3) if pi.Volume() > 1e-6 else 0.0
            rows.append(row)
        out[t['ref']] = rows
    return out


def foot_stop(mp_nominal):
    """Light strip: the spring at (8.5, 11.5) presses the panel's bottom-left border up under the foot's pocket,
    where there is no lip (params FOOT_POCKET). The foot, bonded to the PS film, is the stop: the corner rises until
    the foot meets the roof, or is pressed back by a foot thicker than the roof allows. So the spring deflects by its
    nominal, plus the panel's tolerance, less that gap. Strip stack: nominal and +-STRIP_STACK_TOL."""
    cx, cy, _ = midplate.SPRINGS[0]
    rows = {}
    for dt in (-hw.PANEL_T_TOL, 0.0, hw.PANEL_T_TOL):
        for st, lab in ((-P.STRIP_STACK_TOL, 'thin'), (0.0, 'nominal'), (P.STRIP_STACK_TOL, 'thick')):
            gap = P.FOOT_POCKET['top'] - (P.LIP + P.STRIP_STACK + st)
            d = mp_nominal + dt - gap
            rows[f'{dt:+.1f}mm_panel, {lab} stack'] = {'roof_gap_mm': round(gap, 3), 'deflection_mm': round(d, 3),
                                                        **bridge(midplate.SPRING_L, midplate.SPRING_W, midplate.SPRING_T, max(0.0, d))}
    d_all = [r['deflection_mm'] for r in rows.values()]
    old_gap = 4.07 - (P.LIP + P.STRIP_STACK)
    return {'spring_xy': [cx, cy], 'roof_z': P.FOOT_POCKET['top'], 'foot_top_z': round(P.LIP + P.STRIP_STACK, 3),
            'stack_tol_mm': P.STRIP_STACK_TOL, 'rows': rows,
            'deflection_range_mm': [min(d_all), max(d_all)], 'travel_limit_mm': round(P.MID_T - midplate.SPRING_T, 3),
            'within_travel': bool(max(d_all) <= P.MID_T - midplate.SPRING_T and min(d_all) > 0),
            'with_roof_at_4.07': {'roof_gap_mm': round(old_gap, 3), 'deflection_nominal_mm': round(mp_nominal - old_gap, 3),
                                  'note': 'the next layer line up: the corner could rise past the spring\'s own preload'}}


def strip_bend(y, st=0.0, led_h=None):
    """Light strip, in the face-down tub while the bar slides in under the seat: the bar's tape-side Z at Y (in the
    bar's own X range), for a strip stack st over nominal and an LED led_h tall. The bar is held flat on the foot's
    pocket roof up to the roof's end (the channel's start, CHANNEL_Y[0]) and flat on the skin from D6's body on
    (LEDs down); between the two it bends as a uniform beam held flat at both ends and moved sideways:
    z = z_roof + h (3t^2 - 2t^3). That is the lowest of the plausible shapes near the roof (a straight, pivoting bar
    rises faster), so it is the one that meets the seat first."""
    import refs
    led_h = P.STRIP_LED_H if led_h is None else led_h
    d = refs.strip_data()
    y_led = min(yy for _, _, yy in d['leds']) - d['led']['len'] / 2            # D6's body, 16.6
    y_roof = P.CHANNEL_Y[0]
    z_roof = P.FOOT_POCKET['top'] - (P.STRIP_STACK + st)
    z_led = P.CHANNEL_TOP - led_h - (P.STRIP_STACK + st)
    t = min(1.0, max(0.0, (y - y_roof) / (y_led - y_roof)))
    return {'z': z_roof + (z_led - z_roof) * (3 * t * t - 2 * t ** 3), 'z_line': z_roof + (z_led - z_roof) * t,
            'z_roof': z_roof, 'z_led': z_led, 'y_roof': y_roof, 'y_led': y_led}


def seat_entry():
    """Light strip: where the seat starts (SEAT_Y[0]), the bar's tape side must stay above the seat's level (LIP) while
    it slides in, or the bar's leading edge meets the seat's edge. strip_bend at SEAT_Y[0] for the stack at -tol / 0 /
    +tol (STRIP_STACK_TOL) and an LED of STRIP_LED_H and STRIP_LED_H_MAX; also at the old starts (12.85, 14.0) and the
    first Y (0.05 grid) where every case clears. Also where D6 lies on the seat."""
    y0 = P.SEAT_Y[0]
    cases = [(st, lh) for st in (-P.STRIP_STACK_TOL, 0.0, P.STRIP_STACK_TOL) for lh in (P.STRIP_LED_H, P.STRIP_LED_H_MAX)]
    lab = lambda st, lh: f"{'thin' if st < 0 else 'thick' if st > 0 else 'nominal'} stack, {lh} LED"
    clr = lambda y, st, lh: strip_bend(y, st, lh)['z'] - P.LIP
    rows = {}
    for st, lh in cases:
        b = strip_bend(y0, st, lh)
        rows[lab(st, lh)] = {'clear_at_seat_start_mm': round(b['z'] - P.LIP, 4),
                             'straight_bar_mm': round(b['z_line'] - P.LIP, 4),
                             'at_roof_mm': round(b['z_roof'] - P.LIP, 4), 'at_D6_mm': round(b['z_led'] - P.LIP, 4),
                             'from_12.85_mm': round(clr(12.85, st, lh), 4), 'from_14.0_mm': round(clr(14.0, st, lh), 4)}
    y = P.CHANNEL_Y[0]
    while min(clr(y, st, lh) for st, lh in cases) <= 0 and y < 20:
        y = round(y + 0.05, 2)
    b = strip_bend(y0)
    worst = min(r['clear_at_seat_start_mm'] for r in rows.values())
    return {'seat_start_y': y0, 'seat_top_z': P.LIP, 'roof_end_y': b['y_roof'], 'D6_body_y': round(b['y_led'], 3),
            'D6_copper_y': P.STRIP_D6_COPPER_Y, 'D6_copper_on_seat_mm': round(P.STRIP_D6_COPPER_Y - y0, 3),
            'rows': rows, 'worst_mm': worst, 'all_clear': bool(worst > 0), 'first_all_clear_y': y}


def channel_skin():
    """Light strip: the 0.4 skin over the bar's channel under a fingertip (skin_plate: a Kirchhoff plate clamped at the
    side wall and the channel's ends, held at the hold-down pads, with the pad ribs). SKIN_PRESS['F'] over a disc of SKIN_PRESS['r'], all
    of it on the skin, centred over each bar LED (X 0.26) and further out, between the LEDs' faces and the pads
    (X 1.4, the worst place); PLA at E and at 2/3 of it; and a smaller 4 mm disc. Reports the skin's largest
    deflection over any LED against the LEDs' clearance to it (STRIP_LED_CLR). Also each pad's stiffness against the
    panel (skin_plate.pad_stiffness), with and without its rib."""
    import refs, skin_plate
    leds = [(r, y) for r, x, y in refs.strip_data()['leds'] if y < refs.STRIP_HINGE[0]]
    F, r = P.SKIN_PRESS['F'], P.SKIN_PRESS['r']
    xc = sum(P.STRIP_LED_X) / 2
    cases = {}

    def run(label, x, y, rr, e):
        xs, ys, W, R = skin_plate.solve(dict(F=F, x=x, y=y, r=rr), E=e)
        o = skin_plate.over_leds(xs, ys, W, leds)
        worst = max(o, key=o.get)
        cases[label] = {'over_led_mm': round(o[worst], 3), 'led': worst, 'skin_max_mm': round(float(W.max()), 3),
                        'pad_N': {k: round(v, 2) for k, v in R.items() if abs(v) > 0.005}}
    worst_y = None
    for x, lab in ((xc, 'over the LEDs'), (1.4, 'between the LED faces and the pads')):
        best = None
        for ref, y in leds:
            xs, ys, W, R = skin_plate.solve(dict(F=F, x=x, y=y, r=r), E=E)
            v = skin_plate.over_leds(xs, ys, W, leds)[ref]
            if best is None or v > best[0]:
                best = (v, ref, y)
        run(f'{F:g} N, r {r:g}, E {E:g}, {lab}: worst LED {best[1]}', x, best[2], r, E)
        worst_y = best[2]
    run(f'{F:g} N, r {r:g}, E {2 * E / 3:g}, X 1.4', 1.4, worst_y, r, 2 * E / 3)
    run(f'{F:g} N, r 2, E {E:g}, X 1.4', 1.4, worst_y, 2.0, E)
    run(f'{F:g} N, r 2, E {2 * E / 3:g}, X 1.4', 1.4, worst_y, 2.0, 2 * E / 3)
    # how stiffly each of pads 1-4 holds the panel's border (retention review): with its rib (PAD_RIBS), and without
    pad_k = {f'E {e:g}{lab}': {f'{y:g}': round(k, 2) for y, k in skin_plate.pad_stiffness(e, ribs=rb).items()}
             for e, rb, lab in ((E, True, ''), (2 * E / 3, True, ''), (E, False, ', no pad ribs'))}
    return {'led_clearance_mm': P.STRIP_LED_CLR, 'cases': cases,
            'margin_mm_nominal_case': round(P.STRIP_LED_CLR - max(v['over_led_mm'] for k, v in cases.items() if f'E {E:g}' in k and 'r 2' not in k), 3),
            'pad_k_N_per_mm': pad_k,
            'model': 'skin_plate.py: ACM plate elements 0.15 x 0.25; clamped at the side wall (X -1.42) and the channel ends; '
                     'w = 0 at the pads; 0.4 thick to X 1.63, tapering to 0 at 2.03 under the window bevel; 1.0 over the pad '
                     'ribs; all of F on the skin. pad_k: skin_plate.pad_stiffness (1 N over the contact of one pad on the panel, '
                     'the pad block solid, no pad supports)'}


def bridge(L, w, t, defl):
    """Fixed-fixed beam, centre load."""
    I = w * t ** 3 / 12
    k = 192 * E * I / L ** 3
    f = k * defl
    stress = (f * L / 8) * (t / 2) / I
    return {'k_N_per_mm': round(k, 3), 'force_N': round(f, 3), 'stress_MPa': round(stress, 1)}


def springs():
    out = {}
    mp_nominal = midplate.NUB_H - (P.MID_REAR - P.PCB_FRONT)        # 0.3 compression at nominal
    tol = hw.PANEL_T_TOL
    out['midplate_spring'] = {f'{d:+.1f}mm_panel': {**bridge(midplate.SPRING_L, midplate.SPRING_W, midplate.SPRING_T,
                                                             max(0.0, mp_nominal + d)), 'deflection_mm': round(mp_nominal + d, 3),
                                                    'strain_pct': round(100 * 12 * max(0.0, mp_nominal + d) * midplate.SPRING_T
                                                                        / midplate.SPRING_L ** 2, 2)}
                              for d in (-tol, 0.0, tol)}
    out['midplate_spring']['count'] = len(midplate.SPRINGS)
    out['midplate_spring']['travel_limit_mm'] = round(P.MID_T - midplate.SPRING_T, 3)
    if P.LIGHT_STRIP:
        out['foot_stop'] = foot_stop(mp_nominal)
    # x3: the battery sits in the lid, under a lip, pushed into the bottom-right corner and taped (lid.bay)
    b = lid.bay()[2]
    out['battery_retention'] = {'lip_over_mm': P.BATT_LIP['over'],
                                'lip_underside_over_floor_mm': round(b['lip']['z_edge'] - P.BATT_FLOOR, 3),
                                'envelope_mm': P.BATT_ENV_T, 'end_stop': b['end_stop'],
                                'note': 'the cell tucks under the bottom lip, pushed into the bottom-right corner, and is '
                                        'held with tape; nothing on the lid presses it'}
    out['side_keys'], out['side_key_stop'] = side_keys()
    return out


def _second_moment(poly, axis_x=True):
    """Second moment of area of a shapely polygon about its own centroidal axis parallel to Z (the
    section's v), i.e. for bending that moves the section in u (X)."""
    import shapely.geometry as sg

    def ring_terms(coords):
        a = ix = sx = 0.0
        for (x0, y0), (x1, y1) in zip(coords[:-1], coords[1:]):
            c = x0 * y1 - x1 * y0
            a += c
            sx += (x0 + x1) * c
            ix += (x0 * x0 + x0 * x1 + x1 * x1) * c
        return a / 2, sx / 6, ix / 12
    A = SX = IX = 0.0
    for g in getattr(poly, 'geoms', [poly]):
        g = sg.polygon.orient(g, 1.0)
        for i, ring in enumerate([g.exterior] + list(g.interiors)):
            a, sx, ix = ring_terms(list(ring.coords))
            A, SX, IX = A + a, SX + sx, IX + ix
    xc = SX / A
    return IX - A * xc * xc, A, xc


def side_keys():
    """Each side key as the cantilever it is, from its own sections: sliced across Y every 0.25 mm
    from the flexure's root to the plunger, second moment of each section about its centroid (bar,
    block, pad and all), and the unit-load deflection integrated along it. A press anywhere on the pad
    is then a lever about the root. The stress at the stop is the largest M.c/I along the way (Rev J:
    the bar is 2.95 tall to the block and 7.3 tall past it)."""
    import body, sidekeys, trimesh
    import shapely.geometry as sg
    rows = {}
    for t in body.side_tabs():
        k = sidekeys.build(t['ref'])
        verts, tris = k.val().tessellate(0.01, 0.1)
        mesh = trimesh.Trimesh([(v.x, v.y, v.z) for v in verts], tris, process=True)
        fy, a = t['face'][1], t['away']
        y0 = t['flex_root']
        L = abs(fy - y0)
        n = max(8, int(L / 0.25))
        d_nub = d_rot = 0.0
        Is, secs = [], []
        for i in range(n):
            sy = (i + 0.5) * L / n
            y = y0 + a * sy
            sec = mesh.section(plane_origin=[0, y, 0], plane_normal=[0, 1, 0])
            polys = [sg.Polygon(loop[:, [0, 2]]).buffer(0) for loop in sec.discrete] if sec is not None else []
            geom = polys[0]
            for q in polys[1:]:
                geom = geom.symmetric_difference(q)
            I, _, xc = _second_moment(geom)
            bx0, _, bx1, _ = geom.bounds
            Is.append(I)
            secs.append((L - sy, max(bx1 - xc, xc - bx0) / I))
            d_nub += (L - sy) ** 2 / (E * I) * (L / n)
            d_rot += (L - sy) / (E * I) * (L / n)
        kk = 1.0 / d_nub                                     # N/mm at the plunger
        a_end = abs(t['y_free'] - fy)
        ratio = 1.0 + (d_rot / d_nub) * a_end                # free-end deflection / nub deflection
        gap = t['gap']
        at_click = F_SW + kk * (gap + CLICK)
        near, far = sorted(t['pad_y'], key=lambda y: abs(y - y0))
        stop = min(P.TAB_VOID, (P.TAB_VOID + P.TAB_RELIEF_MAX) / ratio)
        I_root = Is[0]
        th = P.TAB_FLEX_T
        rows[t['ref']] = {
            'length_root_to_plunger_mm': round(L, 1), 'flex_t_mm': th, 'I_root_mm4': round(I_root, 3),
            'k_N_per_mm': round(kk, 2), 'gap_mm': round(gap, 3), 'pad_travel_to_click_mm': round(gap + CLICK, 3),
            'pad_proud_at_click_mm': round(P.TAB_PAD_PROUD - gap - CLICK, 2),
            'nub_mm': [t['nub_w'], round(P.NUB['z'][1] - P.NUB['z'][0], 2)],
            'contact_mm2': round(min(2.882, t['nub_w']) * min(1.5, P.NUB['z'][1] - P.NUB['z'][0]), 2),
            'free_end_ratio': round(ratio, 2), 'stop_travel_mm': round(stop, 3),
            'overtravel_past_click_mm': round(stop - gap - CLICK, 3),
            'finger_force_N': {'pad_centre': round(at_click, 2),
                               'pad_end_near_root': round(at_click * L / abs(near - y0), 2),
                               'pad_end_far': round(at_click * L / abs(far - y0), 2)},
            'rev_h_pla_N': round(F_SW + REV_H_TAB_K_PETG.get(t['ref'], 0.83) * E / 2000.0 * (0.39 + CLICK), 2),
            'rev_i_N': REV_I_SIDE_N.get(t['ref']),
            'stress_at_stop_MPa': round(kk * stop * max(arm * cz for arm, cz in secs), 1),
            'strain_at_stop_pct': round(100 * kk * stop * max(arm * cz for arm, cz in secs) / E, 2)}
    return rows, {'void_mm': P.TAB_VOID, 'relief_mm': P.TAB_RELIEF_MAX,
                  'note': 'the bar bottoms on the sliver above the nub window when the switch reaches its maximum travel'}


# ---- side keys' reach (test 1, 2026-09-29: the 4.26's three +X keys did not click, its two -X keys did) -------------
# The lid carries the keys, and it holds the board in X only by the H5 pin (lid.py: d1.9 in the board's 2.2 hole)
# and by J1's mouth on its USB block (USB_FLOOR['lid_gap'] in front of it, so it bears only when the board moves
# +X), both on the board's +X half. A press pushes the board away from the key: a -X key drives J1 onto the block
# almost at once, a +X key lets the board back off until the pin bears. The board is screwed to the tub (M2 in its
# 2.2 holes) and J1's mouth stands INSERT_X1 - mouth in front of the tub's port floor; the tub floats in the lid's
# groove by JOINT['clr'] a face. The same model as the 4.26's (case-426 mechanics.side_key_reach).
REACH_PIN = (2.2 - 1.9) / 2               # the H5 pin's slack in the board's hole, CAD (0.15)
REACH_SCREW = (2.2 - 2.0) / 2             # the board on the tub's M2 screws (+-0.10)
REACH_LEFT = (0.39, 0.34)                 # travel left for the switch under a press: typical print, worst print
REACH_REST = 0.09                         # the rest gap with the board toward the key: never pre-pressed


def side_key_reach(rows=None):
    """How much nub travel each side key has left for its switch once it has met the plunger under a press
    (the test-1 study's budget, side/s9_budget2.py). The lid is the frame; b is the board's X offset on it, u the
    tub's, s the key's side.
      loaded gap  TAB_GAP_SIDE less the nub's growth, plus the board's slack away from the key: to the pin (its
                  slack less the pin's growth) or the screws for a +X key; to the USB block (lid_gap less the
                  block's growth), the pin, the screws or J1 on the tub's port floor for a -X key
      stop        the least of: the key's inner face on the tub's sliver ('upper': TAB_VOID less both parts'
                  growth and the tub's shift toward the key), the key's foot on the lid's own 45-degree cut ('bed':
                  TAB_FOOT_GAP[0] less the lid slot's shrink) and the free end on the sliver ('free':
                  (TAB_VOID + TAB_RELIEF_MAX) less the growth, over the free-end ratio)
      left        stop - loaded gap: what the switch gets, against the MJTP1117's 0.25 (+0.20/-0.10) to its click
      rest gap    the gap with the board as far toward the key as it goes: must stay open
    Growth is KEY_FDM's: faces grow part/2 on the lid and on the tub, the lid's slots shrink by hole (one print).
    'typical' is the middle print with the tub centred, 'worst' the least over every print with the tub centred
    (the limits), 'tub_anywhere' adds the tub anywhere in its groove (reported only: the screws tie the board to
    it, so it mostly cancels)."""
    import body, itertools
    rows = rows or side_keys()[0]
    port = P.INSERT_X1 - body.usb()['mouth_x']                      # J1's mouth to the tub's port floor (0.115)
    grow = [round(g / 2, 4) for g in P.KEY_FDM['part']]
    prints = list(zip(grow, P.KEY_FDM['hole']))                     # the lid's faces and slots, one print
    c = P.JOINT['clr']
    shifts = (-c, -c / 2, 0.0, c / 2, c)

    def state(s, G, ratio, p, hl, t, u):
        pin, blk = REACH_PIN - p, P.USB_FLOOR['lid_gap'] - p
        plus = min(blk, pin, u + REACH_SCREW, u + port - t)           # the board's furthest +X on the lid
        minus = max(-pin, u - REACH_SCREW)                            # and -X
        away, toward = (minus, plus) if s > 0 else (plus, minus)
        load = G - p - s * away
        stops = {'upper': P.TAB_VOID - p - t - s * u, 'bed': P.TAB_FOOT_GAP[0] - hl,
                 'free': (P.TAB_VOID + P.TAB_RELIEF_MAX - p - t - s * u) / ratio}
        by = min(stops, key=stops.get)
        return {'loaded_gap': round(load, 3), 'stop': round(stops[by], 3), 'stop_by': by,
                'left': round(stops[by] - load, 3), 'rest_gap': round(G - p - s * toward, 3)}

    out, checks = {}, {}
    for t in body.side_tabs():
        ref, s = t['ref'], t['side']
        G, ratio = t['gap'], rows[ref]['free_end_ratio']
        typ = state(s, G, ratio, grow[1], P.KEY_FDM['hole'][1], grow[1], 0.0)
        u0 = [state(s, G, ratio, p, hl, tt, 0.0) for (p, hl), tt in itertools.product(prints, grow)]
        wc = [state(s, G, ratio, p, hl, tt, u) for (p, hl), tt, u in itertools.product(prints, grow, shifts)]
        worst = min(u0, key=lambda r: r['left'])
        anywhere = min(wc, key=lambda r: r['left'])
        rest = min(r['rest_gap'] for r in wc)
        out[ref] = {'side': s, 'gap_mm': G, 'typical': typ,
                    'worst': {'left': worst['left'], 'stop_by': worst['stop_by']},
                    'tub_anywhere': {'left': anywhere['left'], 'stop_by': anywhere['stop_by']},
                    'rest_gap_min': rest,
                    # the gap before a press, board toward the key .. away from it, over every print and tub shift
                    'gap_range': [rest, max(r['loaded_gap'] for r in wc)],
                    # the most the plunger goes in before the key bottoms
                    'most_left': max(r['left'] for r in u0)}
        checks[f'{ref} ({"+X" if s > 0 else "-X"}, gap {G:.2f}): left to the click {typ["left"]:.3f} typical >= '
               f'{REACH_LEFT[0]}, {worst["left"]:.3f} worst >= {REACH_LEFT[1]}'] = \
            typ['left'] >= REACH_LEFT[0] and worst['left'] >= REACH_LEFT[1]
        checks[f'{ref}: rest gap, board toward the key, {rest:.3f} >= {REACH_REST}'] = rest >= REACH_REST
    return {'model': {'pin_slack': round(REACH_PIN, 3), 'usb_block': P.USB_FLOOR['lid_gap'], 'screws': round(REACH_SCREW, 3),
                      'port_floor': round(port, 3), 'tub_in_groove': c, 'growth_face': grow,
                      'lid_slot_shrink': list(P.KEY_FDM['hole']), 'gap': {str(k): v for k, v in P.TAB_GAP_SIDE.items()}},
            'keys': out, 'checks': checks}


def mid_detents():
    """Rev K: the midplate's four click-in strips (midplate.detents), each an in-plane cantilever of the
    plate from its root to the bump. The bump rides `bump` - EDGE_CLR into the wall on the way in and
    catches that much in the pocket; the pocket's roof is 45 degrees."""
    D = P.MID_DETENT
    rows = midplate.detents()[2]
    a = rows[0]['arm']
    w, t = D['w'], P.MID_T
    I = t * w ** 3 / 12
    k = 3 * E * I / a ** 3
    ride = D['bump'] - midplate.EDGE_CLR
    M = k * ride * a
    strain = M * (w / 2) / I / E
    hold = k * ride * (1 + MU) / (1 - MU)
    return {'count': len(rows), 'arm_mm': a, 'strip_mm': [w, t], 'k_N_per_mm': round(k, 2), 'ride_mm': round(ride, 3),
            'strain_pct': round(100 * strain, 2), 'drag_N_each': round(k * ride * MU, 2),
            'hold_N_each': round(hold, 2), 'hold_N_total': round(hold * len(rows), 1),
            'pocket_z': [D['z0'], D['z1']], 'catch_z': round(D['z0'] + ride, 3),
            'plate_rear_z': [round(P.MID_REAR - hw.PANEL_T_TOL, 2), round(P.MID_REAR + hw.PANEL_T_TOL, 2)],
            'rows': rows}


def screen_stack():
    """The panel is pushed against the bezel lip by the midplate springs; the spring nubs must
    stay in contact with the PCB across the panel's thickness tolerance, and the lip must bear
    on the touch film all round the window."""
    import panel
    rows = {}
    for dt in (-hw.PANEL_T_TOL, 0.0, hw.PANEL_T_TOL):
        nub_tip = P.LIP - (hw.PANEL_T + dt) - P.MID_T - midplate.NUB_H
        rows[f'{dt:+.1f}mm_panel'] = {'spring_deflection_mm': round(P.PCB_FRONT - nub_tip, 2),
                                      'gap_glass_to_lip_mm': 0.0 if P.PCB_FRONT - nub_tip > 0 else round(nub_tip - P.PCB_FRONT, 2)}
    wx0 = hw.ACTIVE_CX - hw.ACTIVE_W / 2 - P.WINDOW_MARGIN
    wx1 = hw.ACTIVE_CX + hw.ACTIVE_W / 2 + P.WINDOW_MARGIN
    wy0 = hw.ACTIVE_CY - hw.ACTIVE_H / 2 - P.WINDOW_MARGIN
    wy1 = hw.ACTIVE_CY + hw.ACTIVE_H / 2 + P.WINDOW_MARGIN
    tu0, tu1, tv0, tv1 = panel.TOUCH
    tx0, tx1, ty0, ty1 = hw.PANEL_X0 + tu0, hw.PANEL_X0 + tu1, hw.PANEL_Y0 + tv0, hw.PANEL_Y0 + tv1
    return {'tolerance': rows,
            'lip_bearing_on_ps_film_mm': {'left': round(wx0 - tx0, 2), 'right': round(tx1 - wx1, 2),
                                             'bottom': round(wy0 - ty0, 2), 'top': round(ty1 - wy1, 2)},
            'window_land_mm': round(P.Z_FRONT - P.LIP - P.WINDOW_CHAMFER, 2), 'window_bevel_mm': P.WINDOW_CHAMFER,
            **({'window_bevel_face_mm': P.WINDOW_BEVEL_W, 'window_bevel_deg': P.WINDOW_BEVEL_ANGLE,
                'window_corner_r_mm': [P.WINDOW_CORNER_R, round(P.WINDOW_CORNER_R + P.WINDOW_BEVEL_W, 3)]}
               if not P.LIGHT_STRIP else {}),
            **({'left_border': 'light strip: no lip; hold-down pads at Y %s over X %.2f..%.3f' % (list(P.PAD_Y), *P.PAD_X)}
               if P.LIGHT_STRIP else {}),
            'visible_border_beyond_active_mm': P.WINDOW_MARGIN}


def latches():
    """Tub-to-lid latch arm (joint.py): a cantilever standing on the lid floor, its section read off its profile
    (joint.snap_profile: its inner face, root to top, with the 'mid' point of the thick-below-the-board arm),
    deflected by the barb's engagement as the lid goes on.
    Tip deflection under a tip load F: d = F * integral((L - s)^2 / (E I(s)) ds)."""
    import joint
    S = P.SNAP
    _, h = joint.snap_profile()                   # the lid's barb, drawn params.LATCH_PHASE under its pocket's catch
    _, h0 = joint.snap_profile(phase=0.0)         # the pocket's
    L = h['z_c'] - h['z_root']                    # the barb's load acts at its retaining face
    pts0, _ = joint.snap_profile()
    inner = sorted((z, -d - S['gap']) for d, z in pts0[5:])      # the arm's thickness along its inner face
    inner_z, inner_t = [a for a, _ in inner], [b for _, b in inner]
    y = S['barb'] - S['gap']                      # the arm bends by the barb's engagement
    n = 400
    comp = 0.0
    for i in range(n):
        s = (i + 0.5) * L / n
        t = float(np.interp(h['z_root'] + s, inner_z, inner_t))   # replaces the linear t_root -> t_tip over L
        comp += (L - s) ** 2 / (E * S['w'] * t ** 3 / 12) * (L / n)
    F = y / comp                                  # transverse force at full deflection
    strain = 6 * F * L / (S['w'] * float(np.interp(h['z_root'], inner_z, inner_t)) ** 2) / E
    lead = math.radians(S['lead_deg'])
    push = F * (math.tan(lead) + MU) / (1 - MU * math.tan(lead))
    pull = F * (1 + MU) / (1 - MU)                # 45-degree retaining face
    n = sum(len(v) for v in P.SNAPS.values())
    # light strip: the Y-83 arm's inner top chamfer (params.SNAP_INNER_CHAMFER) is above the barb's catch, where the
    # barb's load puts no moment into the arm, and leaves the barb's points as they are: the figures above hold for it
    cham = {}
    for (w, c), v in P.SNAP_INNER_CHAMFER.items():
        pc, hc = joint.snap_profile(v)
        p0, _ = joint.snap_profile()
        assert pc[:5] == p0[:5] and pc[-1] == p0[-1] and all(hc[k] == h[k] for k in h), (w, c)
        cham[f'{w} Y{c:g}'] = {'along_top_mm': v[0], 'down_inner_face_mm': v[1], 'z_low': round(hc['chamfer']['z_low'], 3),
                              'above_catch_mm': round(hc['chamfer']['z_low'] - h['z_c'], 3),
                              'flat_left_on_top_mm': hc['chamfer']['flat_on_top'], 'barb_unchanged': True}
    return {'arm_mm': round(L, 2), 'deflection_mm': round(y, 2), 'catch_mm': round(y, 2), 'transverse_N': round(F, 2),
            'root_strain_pct': round(100 * strain, 2), 'root_stress_MPa': round(strain * E, 1),
            'push_on_N_each': round(push, 2), 'pull_off_N_each': round(pull, 2), 'count': n,
            'push_on_N_all': round(push * n, 1), 'pull_off_N_all': round(pull * n, 1),
            'pocket_z': [round(h0['catch_low'] - 0.1, 2), round(h0['z_top'] + 0.15, 2)], 'inner_top_chamfer': cham,
            'barb_phase_mm': P.LATCH_PHASE,
            'checks': {'pull-off >= 7.5 N an arm': bool(pull >= 7.5), 'root strain <= 1.0 %': bool(strain <= 0.010)},
            'rev_h': {'catch_mm': 0.2, 'backed': '3 of 11', 'note': '8 of 11 pulled on an unbacked 0.8 mm sliver'},
            'note': 'bends across layer lines (arm prints standing up), so strain is kept low; every pocket '
                    'is backed by solid wall above the side keys\' slots'}


def board_snap():
    """The midplate's posts (plain pins since 2026-10-23; before, snap posts) through the board's H2/H6 holes: what the fingers have to do to
    get in, and what they hold afterwards."""
    B = P.BOARD_SNAP
    hole = 2.2                                              # board's drilled hole
    if B.get('style', 'barb') == 'pole':                    # plain pins since 2026-10-23: they locate, nothing snaps
        return {'style': 'pole', 'posts': list(P.SNAP_POSTS), 'post_d': B['d'], 'hole_d': hole,
                'xy_clearance_mm': round((hole - B['d']) / 2, 3), 'tip_past_board_rear_mm': round(-B['tip'], 3), 'catch_mm': 0.0,
                'board_z_play_mm': None,
                'note': 'locates the board on the midplate in X and Y; nothing holds it in Z until the lid is on, and with the '
                        'lid on its posts set Z (as before)'}
    delta = (B['crest'] - hole) / 2                          # radial squeeze to pass
    L = P.DISP_REAR - B['tip']                               # finger roots at the plate's front face
    t = B['d'] / 2                                           # half-round finger, bending radially
    strain = 3 * t * delta / (2 * L ** 2)
    I = (math.pi * (B['d'] / 2) ** 4 / 8) / 2                # one of two half-round fingers, roughly
    F = 3 * E * I * delta / L ** 3
    lead, face = math.radians(B['lead_deg']), math.radians(B['face_deg'])
    return {'posts': list(P.SNAP_POSTS), 'post_d': B['d'], 'hole_d': hole,
            'xy_clearance_mm': round((hole - B['d']) / 2, 3),
            'squeeze_mm': round(delta, 3), 'finger_mm': round(L, 2),
            'root_strain_pct': round(100 * strain, 2),
            'push_on_N_each': round(2 * F * (math.tan(lead) + MU) / (1 - MU * math.tan(lead)), 2),
            'pull_off_N_each': round(2 * F * (math.tan(face) + MU) / (1 - MU * math.tan(face)), 2),
            'catch_mm': round(delta, 3), 'board_z_play_mm': abs(B['catch']),
            'note': 'captures the board on the midplate before the lid goes on; with the lid on the '
                    'board sits on the lid posts and the barbs go slack, so nothing fights the '
                    'panel thickness take-up'}


if __name__ == '__main__':
    tub_s = tub.build().val()
    lid_s = lid.build(keys=False).val()               # the side keys are swept as bodies of their own
    mid_s = midplate.build().val()
    sweep = key_sweep(tub_s, lid_s, mid_s)
    ssweep = side_key_sweep(tub_s, lid_s, mid_s)
    import panel
    import joint
    sp = springs()
    rep = {'variant': P.VARIANT, 'key_forces': key_forces(), 'key_fit': key_fit(), 'key_preload': preload_window(),
           'crank_stress': crank_stress(),
           'gate': gate_mechanics(tub_s),
           **({'channel_skin': channel_skin(), 'seat_entry': seat_entry()} if P.LIGHT_STRIP else {}),
           'springs': sp, 'side_key_reach': side_key_reach(sp['side_keys']), 'screen_stack': screen_stack(),
           'joint': joint.summary(), 'latches': latches(), 'board_snap': board_snap(), 'mid_detents': mid_detents(),
           'ribbons': {f'{dt:+.1f}mm_panel': panel.report(total=hw.PANEL_T + dt)
                       for dt in (-hw.PANEL_T_TOL, 0.0, hw.PANEL_T_TOL)},
           'key_sweep': sweep, 'side_key_sweep': ssweep, 'key_hooks': key_hooks(tub_s)}
    (hw.OUT / 'mechanics.json').write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: v for k, v in rep.items() if k not in ('key_sweep', 'side_key_sweep')}, indent=1))
    print('key_sweep', json.dumps({k: sweep[k] for k in ('guide_engagement_mm', 'checks', 'failures')}))
    print('key_hooks:')
    for k, ok in rep['key_hooks']['checks'].items():
        print(f"  {'PASS' if ok else 'FAIL'}  {k}")
    for ref, rows in {**{r: sweep[r] for r in P.KEY_REFS}, **ssweep}.items():
        print(ref)
        for r in rows:
            print('   ', r)
    print("side keys' reach (test 1: nub travel left for the switch under a press):")
    for k, ok in rep['side_key_reach']['checks'].items():
        print(f"  {'PASS' if ok else 'FAIL'}  {k}")
    print("latch arms (hold and strain, 2026-10-19):")
    for k, ok in rep['latches']['checks'].items():
        print(f"  {'PASS' if ok else 'FAIL'}  {k}")
    if not all(rep['latches']['checks'].values()):
        sys.exit(1)
