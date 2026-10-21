"""Mechanism checks: the bottom keys' forces, hooks, travel, sweep and over-press stresses (Rev L's bell
crank; the crank spec's sections 6-8; the hook keys of test 2, 2026-09-30), the side keys' sweep against the real hardware and case, plus the
spring/force estimates for every compliant feature. Writes out/<variant>/mechanics.json (the
light-strip variant adds plain_stack). Run after build.py: the bottom keys' sweep reads its tub.stl.

Material model: Ian prints PLA (Elegoo PLA on a Centauri Carbon 2). Printed PLA is taken as
E = 3000 MPa and kept under ~1.5 % strain in anything that flexes; Rev D-H used PETG's 2000, which
put every spring and snap force about a third low. Rev H's numbers are recomputed with the same
model where the page compares against them.
Switches: APEM MJTP1117 (1.27-1.86 N, the modelled one) and SHOU HAN TS365ZJ (1.96-2.94 N) on the bottom
row; the side keys' numbers use the MJTP's 1.57-1.86 N and 0.25 (+0.20/-0.10) mm travel.
"""
import json, math
import cadquery as cq
import hw
import params as P
import keys, tub, lid, midplate

E = 3000.0                        # printed PLA
F_SW = 1.86                       # worst-case operating force
F_SW_MIN = 1.57
TRAVEL_MAX = 0.45
CLICK = 0.25                      # nominal travel to the click
MU = 0.3                          # PLA on PLA / FR4 solder mask / the switch's plunger, dry
# Rev H's side tabs, recomputed for PLA: their stiffness at the plunger (from Rev H's own model, which
# used PETG's E = 2000) scaled to E, over Rev H's 0.39 gap plus the click.
REV_H_TAB_K_PETG = {'SW1': 1.29, 'SW4': 1.53, 'SW10': 1.66, 'SW5': 0.83, 'SW7': 0.83}
# Rev I's separate side keys, press at the pad centre in PLA (its own out/mechanics.json)
REV_I_SIDE_N = {'SW1': 2.53, 'SW4': 2.58, 'SW10': 2.41, 'SW5': 2.14, 'SW7': 2.14}


# ---- bottom keys (Rev L: bell crank + sliding key; the crank spec, sections 4, 6 and 8) ------------------
# Lever: the key pushes the pad's crown 4.95 from the rod, the nose pushes the plunger 2.95 from it (below).
L_IN = P.ROD_YZ[0] - P.CRANK_PAD['c'][0]                     # 4.95
A_OUT = P.ROD_YZ[1] - P.CRANK_NOSE['M'][1]                   # 2.95
DZ_PAD = P.ROD_YZ[1] - (P.CRANK_PAD['c'][1] + P.CRANK_PAD['r'])   # the pad's friction arm, to the crown's top (0.80)
DY_NOSE = P.PLUNGER_Y - P.ROD_YZ[0]                          # the nose's friction arm, at the plunger face (0.58)
R_PIN = P.ROD_D / 2
MU_KEY = (0.3, 0.45)                                         # PLA on PLA: dry, and worn/dusty
# the finger at the cap's chin edge, centre and top edge. The chin-edge point stays at -7.45, the 3.68's too: the
# showcase compares the two sizes' force tables at the same points. Since 2026-09-29 the 4.26 cap's chin face is at
# -7.53 (the 3.68's -7.55), so the point is 0.08 in from it.
PRESS_Y = (-7.45, -6.20, -4.60)
GUIDE_Y = (P.KEY_PUSHER['y'][0], P.KEY_CAP['y'][1])          # the key's two guide contacts: the pusher's chin end
                                                             # (the chin-side stop), the +Y face
# The spec's guide length: the key's +Y face runs on the rail face and the opening's edge from the board's
# rear face to the case face, so Lg is the face's Z (6.00 here; 4.07 / 5.27 on the x3)
LG = P.Z_FRONT
# The drag leaf, its bump and the drag coupon went with test 2 (2026-09-30): the hook keys have no drag (key_hooks).
SWITCHES = {'MJTP 1.27': ('MJTP', 1.27), 'MJTP 1.86': ('MJTP', 1.86), 'TS365 1.96': ('TS365', 1.96), 'TS365 2.94': ('TS365', 2.94)}
OVERPRESS = 20.0                                             # N on one key
SKHL_LIMIT = 29.4                                            # the only published static limit near these switches (N)


def pad_force(Fs, mu, mu_pin):
    """Force on the pad for a switch force Fs, with friction at the pad (arm DZ_PAD), at the nose (DY_NOSE)
    and on the rod: P (L_IN - mu DZ_PAD) = Fs A_OUT + mu Fs DY_NOSE + mu_pin R_PIN sqrt(P^2 + Fs^2)."""
    p = Fs * A_OUT / L_IN
    for _ in range(50):
        p = (Fs * A_OUT + mu * Fs * DY_NOSE + mu_pin * R_PIN * math.hypot(p, Fs)) / (L_IN - mu * DZ_PAD)
    return p


def guide_factor(e, mu, lg=LG):
    """Tilt factor of the key in its guide for a press e from the pad (+: toward the top edge). The key's
    two guide contacts (the pusher's chin end and the +Y face) each take friction; 2 mu e / Lg >= 1 would jam it."""
    yp = P.CRANK_PAD['c'][0]
    s = mu * (GUIDE_Y[0] + GUIDE_Y[1] - 2 * yp)
    den = lg + s if e >= 0 else lg - s
    k = 1 - 2 * mu * abs(e) / den
    return float('inf') if k <= 0 else 1 / k


def key_travel(kind, delta=0.0):
    """Key travel to the click and to the switch's bottom, the matching crank on the switch's own face."""
    sw = keys.SWITCH[kind]
    var = sw['variant']
    face = sw['face'] - delta
    th0 = keys.rest_theta(var, face)
    out = {'rest_theta': round(th0, 2)}
    for name, s in (('click', sw['travel'][0]), ('bottom', sw['travel'][1])):
        th = keys.rest_theta(var, face + s)
        out[f'{name}_theta'] = round(th, 2)
        out[f'{name}_key_mm'] = round(keys.crown_shift(th0) - keys.crown_shift(th), 3)
    return out


KEY_PROUD_SPEC = (1.0, 2.0)          # BELL-CRANK-SPEC.md section 8 item 6: key proud at board delta +-0.2, matching crank
KEY_PROUD_DELTA = 0.2
KEY_PROUD_CHECK = 'key proud 1.0-2.0 at rest, board delta +-0.2, matching crank (the spec, section 8.6)'


def key_proud():
    """The key's height over the face at rest (the spec's section 8 item 6; added 2026-10-03, when the cap went 1.50 ->
    1.35 proud: no check held it before, and 1.30 builds passed). The cap's top as the key is built (keys.key(), the CAD
    rest, theta 0) over Z_FRONT, plus the crown's rise at each switch's rest with its matching crank, for a board offset
    delta of -0.2 / 0 / +0.2 (the plunger's face at face - delta, as build.bottom_keys_check's static), through the
    model's own lever (keys.rest_theta, keys.crown_shift). It must lie in KEY_PROUD_SPEC at every delta: the lowest key
    (the board 0.2 away from it) is about 0.33 down, so a cap under about 1.34 proud fails. Reported, not checked: the
    range as printed (the key grows KEY_FDM part 0.05-0.15 in Z; it prints on its -X end) and the wrong crank's shift."""
    top = keys.key().val().BoundingBox().zmax
    cad = round(top - P.Z_FRONT, 3)
    rows, wrong = {}, {}
    for kind, sw in keys.SWITCH.items():
        for d in (-KEY_PROUD_DELTA, 0.0, KEY_PROUD_DELTA):
            lift = keys.crown_shift(keys.rest_theta(sw['variant'], sw['face'] - d))
            rows[f"{kind} crank-{sw['variant']} delta {d:+.1f}"] = round(cad + lift, 3)
        other = 'T' if sw['variant'] == 'M' else 'M'
        wrong[f'{kind} with crank-{other}'] = round(keys.crown_shift(keys.rest_theta(other, sw['face'])), 3)
    lo, hi = min(rows.values()), max(rows.values())
    part = P.KEY_FDM['part']
    return {'cap_top_z': round(top, 3), 'proud_cad_rest': cad, 'spec': list(KEY_PROUD_SPEC), 'proud_at_rest_mm': rows,
            'range_mm': [lo, hi], 'as_printed_range_mm': [round(lo + part[0], 3), round(hi + part[2], 3)],
            'wrong_crank_shift_mm': wrong,
            'checks': {KEY_PROUD_CHECK: KEY_PROUD_SPEC[0] <= lo and hi <= KEY_PROUD_SPEC[1]}}


def key_forces():
    """Finger force to click a bottom key (the spec's section 6): at the cap's chin edge, centre and top edge,
    for both switch families at both ends of their force range, dry and worn (the hook keys have no drag to add)."""
    rows = {}
    for mu in MU_KEY:
        for name, (kind, Fs) in SWITCHES.items():
            p = pad_force(Fs, mu, mu)
            rows[f'{name} mu {mu}'] = {f'y {y:+.2f}': round(p * guide_factor(y - P.CRANK_PAD['c'][0], mu), 2) for y in PRESS_Y}
    e_top = PRESS_Y[2] - P.CRANK_PAD['c'][0]
    e_max = max(abs(PRESS_Y[0] - P.CRANK_PAD['c'][0]), abs(GUIDE_Y[1] - P.CRANK_PAD['c'][0]))
    zone = {}
    for mu in MU_KEY:
        emax = max(e / 100 for e in range(0, 400) if guide_factor(e / 100, mu) <= 1.5)
        zone[f'mu {mu}'] = {'factor_le_1.5_up_to_y': round(P.CRANK_PAD['c'][0] + emax, 2),
                            'top_edge_factor': round(guide_factor(e_top, mu), 3),
                            '2mu_e_over_Lg_max': round(2 * mu * e_max / LG, 3)}
    travel = {f'{kind} delta {d:+.1f}': key_travel(kind, d) for kind in keys.SWITCH for d in (-0.2, 0.0, 0.2)}
    centre = {n: rows[f'{n} mu 0.3'][f'y {PRESS_Y[1]:+.2f}'] for n in SWITCHES}
    clicks = [v['click_key_mm'] for v in travel.values()]
    checks = {'centre MJTP 1.27 <= 1.3 N (mu 0.3)': centre['MJTP 1.27'] <= 1.3,
              'centre MJTP 1.86 <= 1.7 N (mu 0.3)': centre['MJTP 1.86'] <= 1.7,
              'top-edge factor <= 1.6 (mu 0.3)': zone['mu 0.3']['top_edge_factor'] <= 1.6,
              '2 mu e / Lg < 0.8 everywhere': max(z['2mu_e_over_Lg_max'] for z in zone.values()) < 0.8,
              'travel to the click 0.35-0.50': 0.35 <= min(clicks) and max(clicks) <= 0.50}
    return {'lever': {'input_arm': round(L_IN, 3), 'output_arm': round(A_OUT, 3), 'ratio': round(L_IN / A_OUT, 3),
                      'ideal_key_over_switch': round(A_OUT / L_IN, 3)},
            'guide_length_mm': LG, 'finger_force_N': rows, 'pressable': zone, 'travel': travel,
            # Rev K's rocker (its mechanics.json), 1.86 N switch, mu 0.3, at the cap's chin edge / centre / top
            'rev_k_rocker_N_at_1.86': {'chin edge': 1.64, 'centre': 2.28, 'top edge': 3.18},
            'checks': checks}


# ---- the hook keys (test 2, 2026-09-30: keystab RECOMMENDATION section 6.4, the diagnosis's missing checks) -----------
LEVER = L_IN / A_OUT                                          # 1.678: a plunger's scatter in Y, at the key
RHO = 1.24e-3                                                 # printed PLA, g/mm3
G_N = 9.81e-3                                                 # N per g
FDM_R = dict(wall=0.21, layer=0.10)                           # as-printed corner radii: the outer wall / 2 in a layer,
                                                              # the layer / 2 across layers
HOOK_PULL = 5.0                                               # N outward on one key: a firm thumb push from inside
HOOK_LIMIT = dict(bend=25.0, shear=8.0, bearing=20.0)         # MPa at HOOK_PULL (the hooks' section lies in the key's
                                                              # layers: it prints on its -X end)
PRESS_LOW = -3.4                                              # the key's sweep goes this far below rest: past the switch's
                                                              # bottom, as far as a key sinks face up before the board
HOOK_CRANK_MIN = 0.30                                         # the hooks' least gap to the crank, -20..+60 degrees


def printed_roof():
    """Where the slot's roof prints: the face-down tub's layers run down from Z_FRONT; the first layer whose mid-plane
    is below KEY_SLOT_ROOF is open, so the roof is that layer's top (5.00 for the 4.98 skin underside)."""
    k = math.floor((P.Z_FRONT - P.KEY_SLOT_ROOF) / P.LAYER + 0.5 + 1e-9) + 1
    return round(P.Z_FRONT - P.LAYER * (k - 1), 4)


def rest_high():
    """The switch-set rest's worst high above nominal at the key: ({switch: through the lever}, worst + KEY_CHAIN_PRINT).
    The plunger furthest -Y (the TS365's tip -2.4; the MJTP as modelled) with the board 0.2 toward the key."""
    hi = {}
    for kind, sw in keys.SWITCH.items():
        tip = sw.get('tip', (sw['face'], sw['face']))[0]
        hi[kind] = round(keys.crown_shift(keys.rest_theta(sw['variant'], tip - 0.2)), 3)
    return hi, round(max(hi.values()) + P.KEY_CHAIN_PRINT, 3)


def _xz(mesh, y):
    """(x, z) section of a closed mesh at Y = y (holes kept)."""
    from shapely.geometry import Polygon
    s = mesh.section(plane_origin=[0, y, 0], plane_normal=[0, 1, 0])
    g = Polygon()
    for loop in (s.discrete if s is not None else []):
        if len(loop) >= 3:
            g = g.symmetric_difference(Polygon(loop[:, [0, 2]]).buffer(0))
    return g


def key_hooks():
    """The hook keys' checks (test 2, 2026-09-30: RECOMMENDATION section 6.4; the diagnosis's section 6 item 10), on the
    tub as built (out/<variant>/tub.stl) and the key as drawn (key_sweep has the stop and the key's travel):
      rest     the switch-set rest's worst high at the key (the plunger furthest -Y: TS365 tip -2.4 and the board 0.2
               toward the key, through the lever) plus KEY_CHAIN_PRINT, against KEY_W_OUT and against W_OUT as printed
               (the roof on its layer, printed_roof; the key's height grown by KEY_FDM part): the stop never presses a
               plunger
      wall     the chin wall behind each slot at every layer mid-plane the face-down tub prints up to the roof (and the
               least over the CAD, reported), the material over the roof at the slot's back, and nothing left in a slot
      pull     the hooks under the roof: flat bearing net of the as-printed corner radii (the hook's tip, FDM_R wall; the
               roof's edge, FDM_R layer), the key locked in +Y by the rail (key_sweep's guide); at HOOK_PULL the hooks'
               root shear and bending and the bearing on that flat
      x_tilt   free: the key's XZ sections at three y planes (through the cap, and through the hooks) against the tub's,
               rotated about Y with any X shift and any height from rest to just under the stop, bisected; on the hooks:
               the same at the stop (both hooks on the roof), the tilt a hook's +-0.1 print error gives, a pull at the
               cap's end inside the hooks' span, and face up the crown's length under the cap
      crank    the crank turned -20..+60 degrees (both noses), the key lowered onto it in the checks' bands: where it
               rests and on what (never a hook), the hooks' least gap to the crank, and the key against the tub there
      gravity  per pose (face-up, face-down, on edge chin down, chin up): the net force closing the chain at the key, and
               what holds the key and the crank"""
    import trimesh
    from shapely import affinity
    from shapely.geometry import LineString, Polygon
    from shapely.ops import unary_union
    S, H, W = P.KEY_SLOT, P.KEY_HOOK, P.KEY_W_OUT
    out = {}
    # ---- rest vs the stop -----------------------------------------------------------------------------------------
    hi, need = rest_high()
    roof_p = printed_roof()
    w_pr = [round(W + (roof_p - P.KEY_SLOT_ROOF) - p, 3) for p in P.KEY_FDM['part']]
    rss = math.sqrt(2 * (LEVER * 0.2) ** 2 + P.KEY_CHAIN_PRINT ** 2)
    out['rest'] = {'rest_high_by_switch_mm': hi, 'rest_high_worst_mm': round(need, 3), 'rest_high_rss_mm': round(rss, 3),
                   'w_out': W, 'roof_cad': P.KEY_SLOT_ROOF, 'roof_printed': roof_p, 'w_out_printed_b_t_w': w_pr,
                   'margin_printed_worst': round(w_pr[2] - need, 3), 'spec_need': round(need + 0.15, 3)}
    # ---- the wall behind each slot --------------------------------------------------------------------------------
    tub_m = trimesh.load(P.OUT / 'tub.stl')
    planes = [round(P.Z_FRONT - P.LAYER * (k - 0.5), 4) for k in range(1, 400)]
    planes = [z for z in planes if P.SEAM < z < P.KEY_SLOT_ROOF]
    rim = P.SEAM                     # no seam chamfer over the key row (KEY_SLOT relief): the wall runs to the rim
    wall = {'layers': (9.0, None), 'cad': (9.0, None), 'above_roof': (9.0, None), 'left_in_slot': (0.0, None)}
    dxs = [round(S['dx'][0] + 0.05 + 0.1 * i, 3) for i in range(int(round((S['dx'][1] - S['dx'][0]) / 0.1)))]
    for ref in P.KEY_REFS:
        xc = keys.key_x(ref)
        for sd in (-1, 1):
            for dx in dxs:
                g = keys.section(tub_m, xc + sd * dx)
                at = [ref, sd * dx]
                for z in planes:
                    w = LineString([(-12.0, z), (S['back'] - 1e-3, z)]).intersection(g).length
                    if w < wall['layers'][0]:
                        wall['layers'] = (round(w, 3), at + [z])
                    x = LineString([(S['back'] + 0.01, z), (P.BOT_IN - 0.01, z)]).intersection(g).length
                    if x > wall['left_in_slot'][0]:
                        wall['left_in_slot'] = (round(x, 3), at + [z])
                for i in range(int((P.KEY_SLOT_ROOF - rim) / 0.02)):
                    z = rim + 0.01 + 0.02 * i
                    w = LineString([(-12.0, z), (S['back'] - 1e-3, z)]).intersection(g).length
                    if w < wall['cad'][0]:
                        wall['cad'] = (round(w, 3), at + [round(z, 2)])
                a = LineString([(S['back'] + 0.01, P.KEY_SLOT_ROOF + 1e-3), (S['back'] + 0.01, 9.0)]).intersection(g).length
                if a < wall['above_roof'][0]:
                    wall['above_roof'] = (round(a, 3), at)
    out['wall'] = {k: {'mm': v[0], 'at': v[1]} for k, v in wall.items()}
    out['wall']['layer_planes'] = [planes[0], planes[-1], len(planes)]
    # ---- pull-out -------------------------------------------------------------------------------------------------
    edge = P.KEY_OPENING['y'][0] if P.KEY_SLOT_ROOF >= P.LIP - 1e-6 else P.BOT_IN     # where the flat under the roof ends
    gross = edge - H['tip']
    net = gross - FDM_R['wall'] - FDM_R['layer']
    wx, hh = H['dx'][1] - H['dx'][0], H['h']
    Fh = HOOK_PULL / 2
    arm = P.KEY_CAP['y'][0] - (edge + H['tip']) / 2
    pull = {'bearing_gross_mm': round(gross, 3), 'corner_radii_mm': [FDM_R['wall'], FDM_R['layer']], 'bearing_net_mm': round(net, 3),
            'bearing_as_printed_worst_mm': round(gross + (P.KEY_FDM['part'][0] + P.KEY_FDM['hole'][0]) / 2 - FDM_R['wall'] - FDM_R['layer'], 3),
            'locked_in_plus_y': 'the key\'s +Y face on the rail (key_sweep: on the guide >= 2.5 at every lift, the stop too)',
            'pull_N': HOOK_PULL, 'per_hook_N': Fh, 'root_shear_MPa': round(Fh / (wx * hh), 2),
            'root_bending_MPa': round(6 * Fh * arm / (wx * hh ** 2), 2), 'bearing_MPa': round(Fh / (wx * net), 2), 'arm_mm': round(arm, 3)}
    out['pull'] = pull
    # ---- X-tilt ---------------------------------------------------------------------------------------------------
    vs, ts = keys.key().val().tessellate(0.005, 0.05)
    km = trimesh.Trimesh([(v.x, v.y, v.z) for v in vs], ts, process=True)
    ys = (-8.0, -7.0, -5.5)                                   # through the hooks under the ledge, and through the cap
    kx = [_xz(km, y) for y in ys]
    txs = [round(-0.5 + 0.02 * i, 3) for i in range(51)]
    piv = (0.0, 3.5)

    def feasible(tz_list, ang, T):
        for tz in tz_list:
            for tx in txs:
                if not any(affinity.translate(affinity.rotate(k, ang, origin=piv), tx, tz).intersection(t).area > 1e-5
                           for k, t in zip(kx, T) if not k.is_empty):
                    return (tx, round(tz, 3))
        return None

    def maxang(tz_list, sign, T, hi_=20.0):
        if feasible(tz_list, 0.0, T) is None:
            return None
        lo, hi2 = 0.0, hi_
        for _ in range(10):
            mid = (lo + hi2) / 2
            if feasible(tz_list, sign * mid, T):
                lo = mid
            else:
                hi2 = mid
        return round(lo, 2)
    xt = {}
    for ref in P.KEY_REFS:
        xc = keys.key_x(ref)
        T = [affinity.translate(_xz(tub_m, y), -xc, 0).intersection(Polygon([(-8, -2), (8, -2), (8, 9), (-8, 9)])) for y in ys]
        free = [round(-0.3 + 0.1 * i, 3) for i in range(int(round((W - 0.02 + 0.3) / 0.1)) + 1)]
        xt[ref] = {'free_deg': [maxang(free, 1, T), maxang(free, -1, T)],
                   'at_the_stop_deg': [maxang([W], 1, T, 3.0), maxang([W], -1, T, 3.0)]}
    fr = max(max(v['free_deg']) for v in xt.values() if None not in v['free_deg'])
    st = max(max(v['at_the_stop_deg']) for v in xt.values() if None not in v['at_the_stop_deg'])
    span = 2 * sum(H['dx']) / 2
    out['x_tilt'] = {'by_key': xt, 'free_max_deg': fr, 'free_end_to_end_mm': round(2 * P.KEY_CAP['half'] * math.sin(math.radians(fr)), 2),
                     'at_the_stop_max_deg': st, 'hook_centres_apart_mm': round(span, 3),
                     'hook_error_0.1_one_deg': round(math.degrees(math.atan(0.1 / span)), 2),
                     'hook_error_0.1_both_deg': round(math.degrees(math.atan(0.2 / span)), 2),
                     'pull_at_the_cap_end_inside_the_hooks': H['dx'][1] >= P.KEY_CAP['half'] - 1e-9,
                     'crown_half_length_vs_cap': [P.CRANK_CHEEK[1], P.KEY_CAP['half']]}
    # ---- the hooks against the crank, -20..+60 degrees --------------------------------------------------------------
    B = keys.bands()
    shade = {r: [keys.shadow(tub_m, keys.key_x(r) + a, keys.key_x(r) + b) for a, b in B] for r in P.KEY_REFS}
    rows, worst_h, worst_t, rests_on = [], (9.0, None), (9.0, None), set()
    for var in ('M', 'T'):
        for th in range(-20, 61, 2):
            parts = []
            for i, (a, b) in enumerate(B):
                cr = keys.crank_yz(a, b, var)
                kk = keys.key_yz(a, b)
                if not cr or not kk:
                    continue
                parts.append((i, unary_union([keys.turn(g, th) for g in cr.values()]), kk))

            def hit(lf):
                return any(keys.lift(g, lf).intersection(c).area > 1e-6 for _, c, kk in parts for g in kk.values())
            if hit(W):
                lf, on = W, 'the crank stopped by the key at its stop'
            elif not hit(-8.0):
                lf, on = None, 'no support'
            else:
                lo, hi2 = -8.0, W
                for _ in range(22):
                    mid = (lo + hi2) / 2
                    if hit(mid):
                        lo = mid
                    else:
                        hi2 = mid
                lf, on = hi2, None
            if lf is None:
                rows.append({'crank': var, 'theta': th, 'key_lift': None, 'on': on})
                continue
            gk, gh = 9.0, 9.0
            for i, c, kk in parts:
                gk = min(gk, keys.lift(kk['key'], lf).distance(c))
                if 'hook' in kk:
                    gh = min(gh, keys.lift(kk['hook'], lf).distance(c))
            on = on or ('pusher/key' if gk <= gh else 'HOOK')
            rests_on.add(on)
            if gh < worst_h[0]:
                worst_h = (round(gh, 3), [var, th, round(lf, 3)])
            for r in P.KEY_REFS:
                for i, c, kk in parts:
                    for g in kk.values():
                        t = keys.gap(keys.lift(g, lf), shade[r][i])
                        if t is not None and t < worst_t[0]:
                            worst_t = (t, [var, th, r, B[i]])
            if th % 10 == 0:
                rows.append({'crank': var, 'theta': th, 'key_lift': round(lf, 3), 'on': on, 'hook_gap': round(gh, 3)})
    out['crank'] = {'thetas': [-20, 60], 'rows': rows, 'rests_on': sorted(rests_on), 'hook_gap_min': {'mm': worst_h[0], 'at': worst_h[1]},
                    'key_vs_tub_min': {'gap': worst_t[0], 'at': worst_t[1]}}
    # ---- gravity per pose -----------------------------------------------------------------------------------------
    kv, cv = keys.key().val(), keys.crank('T').val()
    mk, mc = kv.Volume() * RHO, cv.Volume() * RHO
    c = cv.Center()
    dy, dz = c.y - P.ROD_YZ[0], c.z - P.ROD_YZ[1]
    wk, wc = mk * G_N, mc * G_N
    grav = {}
    for pose, (gy, gz) in (('face-up', (0, -1)), ('face-down', (0, 1)), ('on edge, chin down', (-1, 0)), ('on edge, chin up', (1, 0))):
        tq = dy * gz * wc - dz * gy * wc + (L_IN * wk if gz < 0 else 0.0)
        grav[pose] = {'net_at_key_N': round(tq / L_IN, 5)}
    grav['face-up']['holds'] = 'the chain closes: key on its crank, crank on its switch (the rest is the switch\'s, no free travel)'
    grav['face-down']['holds'] = f'the key drops {W} onto both hooks under the roof; the crank swings pad-up onto the key'
    ratio = MU_KEY[0] * wk / max(1e-9, -grav['on edge, chin down']['net_at_key_N'])
    grav['on edge, chin down']['holds'] = (f'the crank pulls the chain open; the key\'s weight on its chin side gives mu {MU_KEY[0]} x '
                                           f'{wk:.5f} N of friction, {ratio:.1f} x that pull')
    grav['on edge, chin down']['friction_over_pull'] = round(ratio, 2)
    grav['on edge, chin up']['holds'] = 'the chain closes (the crank\'s weight), the key on the rail'
    out['gravity'] = {'key_g': round(mk, 3), 'crank_g': round(mc, 3), 'crank_cg_from_rod': [round(dy, 3), round(dz, 3)], 'poses': grav}
    out['checks'] = {
        f'W_OUT {W} >= the rest\'s worst high + the stop\'s print 0.10 + 0.05 ({need + 0.15:.3f})': W >= need + 0.15 - 1e-9,
        'W_OUT as printed at worst (roof on its layer, key grown) >= the rest\'s worst high: the stop never presses a plunger': w_pr[2] >= need - 1e-9,
        f"wall behind the slot >= {S['wall']} at every printed layer, the rim's included (no seam chamfer over the key row)": wall['layers'][0] >= S['wall'] - 1e-3,
        f"material over the roof at the slot's back >= {S['above']}": wall['above_roof'][0] >= S['above'] - 1e-3,
        'nothing left in a slot': wall['left_in_slot'][0] <= 1e-3,
        'pull-out: flat bearing net of the corner radii > 0 (the key locked in +Y by the rail)': net > 0,
        f"hooks at {HOOK_PULL} N: root bending <= {HOOK_LIMIT['bend']}, shear <= {HOOK_LIMIT['shear']}, bearing <= {HOOK_LIMIT['bearing']} MPa":
            pull['root_bending_MPa'] <= HOOK_LIMIT['bend'] and pull['root_shear_MPa'] <= HOOK_LIMIT['shear'] and pull['bearing_MPa'] <= HOOK_LIMIT['bearing'],
        'X-tilt on the hooks: level at the stop (<= 0.2 deg), <= 1.5 deg at +-0.1 per hook, a pull at the cap end inside them':
            st <= 0.2 and out['x_tilt']['hook_error_0.1_both_deg'] <= 1.5 and out['x_tilt']['pull_at_the_cap_end_inside_the_hooks'],
        'face up the crown runs under the whole cap': P.CRANK_CHEEK[1] >= P.KEY_CAP['half'],
        'crank -20..+60: the key rests on its pusher, never on a hook': 'HOOK' not in rests_on,
        f'crank -20..+60: hooks >= {HOOK_CRANK_MIN} off the crank': worst_h[0] >= HOOK_CRANK_MIN,
        'crank -20..+60: the key never overlaps the tub': worst_t[0] >= -1e-4,
        'gravity: face up the chain closes on the switch, face down the crank follows the key': grav['face-up']['net_at_key_N'] > 0 > grav['face-down']['net_at_key_N'],
        'gravity: on edge (chin down) the key\'s friction holds the crank\'s pull (>= 1)': ratio >= 1.0}
    return out


def printed_layers(a, b, layer=P.LAYER):
    """The part of a span a..b of print height (from the bed) that prints: the layers whose mid-plane lies inside it
    (a plane on its end face prints nothing). Returns (from, to)."""
    k0 = math.ceil((a + layer / 2) / layer - 1e-6)
    k1 = math.ceil((b + layer / 2) / layer - 1e-6) - 1
    return round((k0 - 1) * layer, 4), round(k1 * layer, 4)


def key_fit():
    """The key's fit in its opening as a tolerance stack (2026-09-29: Ian's first print jammed, the chin side had
    0.15 and a print takes 0.15-0.35 of it). Each pair from the params, in CAD and as printed best / typical / worst
    (KEY_FDM: holes 0.10-0.20 small, parts 0.05-0.15 large). Y pairs one-sided, the +Y face on the rail
    (c - hole - part); the hooks (test 2): L the tip to the slot's back, M the slot's sides with the key across by its
    play, N the hook's top to the roof at rest (the roof on its layer, the key grown), H the flat under the roof net
    of the corner radii (what holds it: the rail locks the key in +Y, key_hooks). The key prints on its -X
    end (test 1, 2026-09-29): X is its layer axis, so its X sizes are layer-quantized, not grown (the 10.00 key is 50
    layers, 10.00 long since 2026-10-03; the 9.90 one was 49, 9.80: layers print where their mid-plane is inside it),
    and an X pair is two-sided with the key centred (c_q - hole/2); its bed end has no flare past the outline
    (KEY_BED_END), so the cap-down rows (A*, D*: the layer-1 X ends; C*: the cap top's first layer through the skin)
    are gone. E: the key pushed +X by its play (A as printed) moves its body's farther X face toward that side's
    cheek, which grows part/2. A body face that falls on a layer's mid-plane (the 50-layer key's +-3.30) prints
    either way in the slicer (float noise; Orca prints it out to the layer's far boundary, +-3.40, as sliced), so
    the face is taken out to that boundary: the worse case."""
    hole, part = P.KEY_FDM['hole'], P.KEY_FDM['part']
    O, C, Pu, Hk, S = P.KEY_OPENING, P.KEY_CAP, P.KEY_PUSHER, P.KEY_HOOK, P.KEY_SLOT
    # on its -X end: the key's X extent as printed (from the bed at -half), and its body's +X face, key centred
    hh = C['half']
    lay = printed_layers(0.0, 2 * hh)
    xq = (-hh + lay[0], -hh + lay[1])                                  # -5.00 .. 5.00
    # the body's faces from the bed, each out to the boundary of a layer whose mid-plane it touches (the worse case);
    # bx is the farther one from the key's printed centre
    b0, b1 = hh - P.KEY_BODY['half'], hh + P.KEY_BODY['half']
    f0 = P.LAYER * (math.ceil(b0 / P.LAYER + 0.5 - 1e-6) - 1)
    f1 = P.LAYER * math.floor(b1 / P.LAYER + 0.5 + 1e-6)
    xm = (lay[0] + lay[1]) / 2
    bx = round(max(f1 - xm, xm - f0), 4)                               # 3.40 (3.30 on the 49-layer key)

    def xq2(c):
        return [round(c - h / 2, 3) for h in hole]

    def y1(c):
        return [round(c - h - p, 3) for h, p in zip(hole, part)]

    A, D = O['half'] - C['half'], P.SLOT[1] - C['half']
    Aq, Dq = O['half'] - (xq[1] - xq[0]) / 2, P.SLOT[1] - (xq[1] - xq[0]) / 2
    E = P.CRANK_CHEEK[0] - P.KEY_BODY['half']
    Cy, Fy = C['y'][0] - O['y'][0], Pu['y'][0] - P.BOT_IN
    Ly = Hk['tip'] - S['back']                                         # the hook's tip to the slot's back
    # M: across by the key's play A (its end face on the opening's side), the hook's outer face to the slot's outer side
    # and the +X hook's lead (where it crosses the chin wall's face) to the slot's inner side; the opening and the slots
    # are one print, so hole/2 cancels; the lead's X is set by the key's layers: the first layer whose mid-plane reaches
    # the wall's face prints from its bottom
    lead_x = Hk['dx'][0] - P.KEY_HOOK_LEAD + (C['y'][0] - P.BOT_IN)
    kq = math.ceil((lead_x + C['half']) / P.LAYER + 0.5 - 1e-9)
    lead_xq = -C['half'] + P.LAYER * (kq - 1)
    Mo, Mi, Miq = S['dx'][1] - Hk['dx'][1] - A, lead_x - S['dx'][0] - A, lead_xq - S['dx'][0] - A
    roof_p = printed_roof()
    edge = O['y'][0] if P.KEY_SLOT_ROOF >= P.LIP - 1e-6 else P.BOT_IN
    Hg = edge - Hk['tip']
    pair = lambda cad, printed, **kw: {'cad': round(cad, 3), 'printed_b_t_w': printed, **kw}
    pairs = {
        'A cap to opening side, X per side (skin)': pair(A, xq2(Aq), layer_quantized=round(Aq, 3)),
        'D key to web, X per side (pocket)': pair(D, xq2(Dq), layer_quantized=round(Dq, 3)),
        'C cap chin face to opening chin edge (skin)': pair(Cy, y1(Cy)),
        "F the pusher's chin end to the chin wall (pocket; the chin-side stop)": pair(Fy, y1(Fy)),
        'L hook tip to the slot back (pocket; the chin-side stop with F)': pair(Ly, y1(Ly)),
        'M hook to its slot sides, X, the key across by its play (outer / inner)': pair(min(Mo, Mi), [round(min(Mo, Miq), 3)] * 3,
                                                                                       outer=round(Mo, 3), inner=round(Mi, 3),
                                                                                       inner_as_printed=round(Miq, 3)),
        'N hook top to the roof at rest (KEY_W_OUT)': pair(P.KEY_W_OUT, [round(P.KEY_W_OUT + roof_p - P.KEY_SLOT_ROOF - p, 3) for p in part],
                                                          roof_printed=roof_p),
        'H hook under the roof (retention), gross': pair(Hg, [round(Hg + (p + h) / 2, 3) for h, p in zip(hole, part)],
                                                         net_of_corner_radii=round(Hg - FDM_R['wall'] - FDM_R['layer'], 3)),
        # E: the key's body to its crank's cheek, crank centred (it floats CRANK_CHEEK[0] - SLOT[0] each way in its
        # slots): the body's +X face on its layer boundary (bx), the cheek grown part/2; held against the key's X play
        # in its opening (A as printed), so a key pushed sideways stops on the opening before its body reaches the cheek
        'E key body to crank cheek, X per side (beyond the X play A)': pair(E, [round(P.CRANK_CHEEK[0] - p / 2 - bx, 3) for p in part],
                                                                          crank_float=round(P.CRANK_CHEEK[0] - P.SLOT[0], 3),
                                                                          body_x_face_as_printed=round(bx, 3)),
    }
    # K: the crown's contact on the pusher's flat, where the crown's circle is highest (a flat on a circle), turned
    # with the crank over -13..+16 degrees and at each matching rest
    (cy, cz), (ry, rz) = P.CRANK_PAD['c'], P.ROD_YZ

    def contact(th):
        t = math.radians(th)
        return ry + (cy - ry) * math.cos(t) - (cz - rz) * math.sin(t)

    ths = [-13.0 + 0.5 * i for i in range(59)]
    rests = [keys.rest_theta(sw['variant'], sw['face'] - d) for sw in keys.SWITCH.values() for d in (-0.2, 0.0, 0.2)]
    margin = lambda y: min(y - Pu['y'][0], Pu['y'][1] - y)
    k = min(margin(contact(t)) for t in ths)
    pairs["K crown contact on the pusher's flat"] = {
        'pusher_y': list(Pu['y']), 'contact_y_over_-13..+16': [round(contact(-13.0), 3), round(contact(16.0), 3)],
        'to_its_ends': {'-13': round(margin(contact(-13.0)), 3), 'rest': [round(min(margin(contact(t)) for t in rests), 3),
                        round(max(margin(contact(t)) for t in rests), 3)], '+16': round(margin(contact(16.0)), 3)}}
    tilt = math.degrees(math.atan(y1(Fy)[0] / (P.Z_FRONT - Pu['stop_z1'])))
    wy = [pairs[q]['printed_b_t_w'][2] for q in pairs if q.startswith(('C ', 'F ', 'L '))]
    wx = [pairs[q]['printed_b_t_w'][2] for q in pairs if q.startswith(('A ', 'D '))]
    m = min(pairs[q]['printed_b_t_w'][2] for q in pairs if q.startswith('M '))
    ea = [e - a for e, a in zip([E] + pairs[next(q for q in pairs if q.startswith('E '))]['printed_b_t_w'],
                                [A] + pairs[next(q for q in pairs if q.startswith('A '))]['printed_b_t_w'])]
    pairs[next(q for q in pairs if q.startswith('E '))]['beyond_A_cad_b_t_w'] = [round(v, 3) for v in ea]
    checks = {'rigid Y pairs (C, F, L) >= +0.05 as printed at worst': min(wy) >= 0.05 - 1e-9,
              'key body clears its crank cheek by more than its X play (E - A >= +0.05, CAD and as printed)': min(ea) >= 0.05 - 1e-9,
              'X pairs (A, D) >= +0.15 as printed at worst': min(wx) >= 0.15,
              'hooks clear their slot sides with the key across (M >= +0.05 as printed)': m >= 0.05 - 1e-9,
              'hook top under the roof at rest as printed at worst (N > 0)': pairs['N hook top to the roof at rest (KEY_W_OUT)']['printed_b_t_w'][2] > 0,
              'hook under the roof net of the corner radii (H) > 0': pairs['H hook under the roof (retention), gross']['net_of_corner_radii'] > 0,
              "crown contact on the pusher's flat, >= 0.10 from each end over -13..+16 deg": k >= 0.10}
    return {'model': {'KEY_FDM': P.KEY_FDM, 'order': 'best / typical / worst',
                      'printed_on': '-X end', 'key_x_as_printed': [round(q, 3) for q in xq],
                      'layers': round((lay[1] - lay[0]) / P.LAYER)},
            'pairs': pairs, 'tilt_deg_at_most': round(tilt, 1), 'accepted': {},
            'checks': checks}


def rod_fe(F_pin, kfac=1.0, cheek_w=None, gap=None):
    """The rod as a beam on elastic bearings (the rail beside each cheek, Winkler, 0.8 E per mm), loaded by one
    crank's two cheeks, each spreading half the pin load over its width (design/rodfe.py). Returns the peak
    bending stress (MPa, at the thinnest real filament, 1.72) and the deflection (mm)."""
    import numpy as np
    d = 1.72
    I = math.pi * d ** 4 / 64
    Z = math.pi * d ** 3 / 32
    cw = cheek_w or (P.CRANK_CHEEK[1] - P.CRANK_CHEEK[0])
    g = gap or (P.CRANK_CHEEK[0] - P.SLOT[0])
    n = 2401
    x = np.linspace(-12.0, 12.0, n)
    h = x[1] - x[0]
    c_in = P.CRANK_CHEEK[0]
    ch = [(-c_in - cw, -c_in), (c_in, c_in + cw)]
    k = np.full(n, kfac * E * 0.8)
    q = np.zeros(n)
    for a, b in ch:
        k[(x > a - g) & (x < b + g)] = 0.0
        m = (x >= a) & (x <= b)
        q[m] = (F_pin / 2) / (b - a)
    K = np.zeros((2 * n, 2 * n))
    Fv = np.zeros(2 * n)
    ke = E * I / h ** 3 * np.array([[12, 6 * h, -12, 6 * h], [6 * h, 4 * h * h, -6 * h, 2 * h * h],
                                    [-12, -6 * h, 12, -6 * h], [6 * h, 2 * h * h, -6 * h, 4 * h * h]])
    for e in range(n - 1):
        idx = [2 * e, 2 * e + 1, 2 * e + 2, 2 * e + 3]
        K[np.ix_(idx, idx)] += ke
    for i in range(n):
        K[2 * i, 2 * i] += k[i] * h
        Fv[2 * i] += q[i] * h
    w = np.linalg.solve(K, Fv)[0::2]
    M = E * I * np.gradient(np.gradient(w, h), h)
    return float(abs(M).max() / Z), float(w.max())


def torsion(poly, h=0.01):
    """Saint-Venant torsion of a solid (y, z) section by Prandtl's stress function: laplacian(phi) = -2 inside,
    phi = 0 on the boundary, on an h grid (5-point finite differences). Returns J = 2 int(phi) and the peak
    |grad phi|, so the peak shear is T / J * that. Concave corners must be rounded (the crank's are) or the
    peak grows without bound as h shrinks."""
    import numpy as np
    from shapely import contains_xy
    from scipy.sparse import coo_matrix
    from scipy.sparse.linalg import spsolve
    y0, z0, y1, z1 = poly.bounds
    ys = np.arange(y0 - 2 * h, y1 + 2 * h, h)
    zs = np.arange(z0 - 2 * h, z1 + 2 * h, h)
    Y, Z = np.meshgrid(ys, zs, indexing='ij')
    ins = contains_xy(poly, Y, Z)
    idx = -np.ones(ins.shape, int)
    n = int(ins.sum())
    idx[ins] = np.arange(n)
    I, J_ = np.nonzero(ins)
    k = idx[I, J_]
    rows, cols, vals = [k], [k], [np.full(n, 4.0)]
    for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        kk = idx[I + di, J_ + dj]
        m = kk >= 0
        rows.append(k[m])
        cols.append(kk[m])
        vals.append(-np.ones(int(m.sum())))
    A = coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr()
    phi = np.zeros(ins.shape)
    phi[ins] = spsolve(A, np.full(n, 2 * h * h))
    gy, gz = np.gradient(phi, h)
    g = np.hypot(gy, gz)
    g[~ins] = 0.0
    i = np.unravel_index(int(np.argmax(g)), g.shape)
    return float(2 * phi.sum() * h * h), float(g.max()), (round(float(ys[i[0]]), 2), round(float(zs[i[1]]), 2))


def _section(poly):
    """Area, second moments about the centroid (Iy for bending in Z, Iz for bending in Y), extreme fibres
    and centroid of a (y, z) polygon, on a 0.01 grid (stress4.py)."""
    import numpy as np
    from shapely import contains_xy
    c = poly.centroid
    ys = np.arange(poly.bounds[0], poly.bounds[2], 0.01)
    zs = np.arange(poly.bounds[1], poly.bounds[3], 0.01)
    YY, ZZ = np.meshgrid(ys, zs)
    m = contains_xy(poly, YY, ZZ)
    Iy = float(((ZZ[m] - c.y) ** 2).sum() * 1e-4)
    Iz = float(((YY[m] - c.x) ** 2).sum() * 1e-4)
    cz = max(abs(poly.bounds[1] - c.y), abs(poly.bounds[3] - c.y))
    cy = max(abs(poly.bounds[0] - c.x), abs(poly.bounds[2] - c.x))
    return poly.area, Iy, Iz, cz, cy, c


def overpress():
    """Stress at a 20 N press on one key (the spec's check 7). The switch takes the over-press - no stop in the
    tub or the crank works across the rest scatter - so every part in the load path is checked at it."""
    from shapely.ops import unary_union
    F = OVERPRESS
    Fs = F * L_IN / A_OUT
    pin = math.hypot(F, Fs)
    cheek = pin / 2
    d = 1.72
    cw = P.CRANK_CHEEK[1] - P.CRANK_CHEEK[0]
    rod1, defl = rod_fe(pin)
    rod3, _ = rod_fe(pin, kfac=1 / 3)
    shear = 4 / 3 * (cheek / 2) / (math.pi * d ** 2 / 4)     # each cheek's load splits to the rail on its two sides
    bearing = cheek / (d * cw)
    Fs_click = 2.94
    p_click = pad_force(Fs_click, 0.0, 0.0)
    bearing_click = math.hypot(p_click, Fs_click) / 2 / (d * cw)
    # the crossbar with the belly, a beam along X pinned at the cheeks' centres, loaded by the key over its
    # width and the plunger at the leg (stress4.py)
    A, Iy, Iz, cz, cy, c = _section(keys.BODY)
    half = (P.CRANK_CHEEK[0] + P.CRANK_CHEEK[1]) / 2
    x = half - P.CRANK_LEG
    q = F / (2 * P.CRANK_CHEEK[1] - 0.3)
    My = Fs / 2 * x
    Mz = q * half * x - q * x * x / 2
    s_y, s_z = My * cy / Iz, Mz * cz / Iy
    # torsion: the crossbar between the leg and a cheek carries the twist of what lies outboard of its
    # section at dx - that cheek's pin reaction (half the pin load, at the rod) and the key's load outboard of
    # dx (spread over the cap's width, at the crown) - about the section's centroid; Prandtl's solution
    # (torsion()) gives the peak shear, and the shear of the transverse load (1.5 V / A) is added to it
    poly = keys.BODY
    Jt, gmax, at = torsion(poly)
    pin_c = (Fs / 2, F / 2)                     # on the crank, per cheek, in (y, z)
    rows = {}
    for s in (1.35, 1.5, 2.2, 3.0, 3.7):
        Fk = F * (P.KEY_CAP['half'] - s) / (2 * P.KEY_CAP['half'])
        T = (P.ROD_YZ[0] - c.x) * pin_c[1] - (P.ROD_YZ[1] - c.y) * pin_c[0] - (P.CRANK_PAD['c'][0] - c.x) * Fk
        V = math.hypot(pin_c[0], pin_c[1] - Fk)
        rows[s] = (abs(T) / Jt * gmax, 1.5 * V / A, T)
    s_w = max(rows, key=lambda q: rows[q][0] + rows[q][1])
    tau_t, tau_v, T = rows[s_w]
    # the crossbar's root at y -6.2 (the pad arm, across the crank's width; across the layers as printed
    # pad-down: its depth there from the profile) and the leg's root at z -1.3 (with the belly, the whole
    # width, 1.73 deep)
    w = 2 * P.CRANK_CHEEK[1]
    from shapely.geometry import LineString
    cut = keys.CROSSBAR.intersection(LineString([(-6.2, -9), (-6.2, 9)]))
    depth = cut.bounds[3] - cut.bounds[1]
    root = 6 * (F * (-6.2 - P.CRANK_PAD['c'][0])) / (w * depth ** 2)
    leg_root = 6 * (Fs * (-1.3 - P.CRANK_NOSE['M'][1])) / (w * 1.73 ** 2)
    out = {'press_N': F, 'plunger_N': round(Fs, 1), 'pin_N': round(pin, 1), 'per_cheek_N': round(cheek, 1),
           'rod_bending_MPa': round(rod1, 1), 'rod_bending_soft_bearings_MPa': round(rod3, 1), 'rod_deflection_um': round(defl * 1000, 1),
           'rod_shear_MPa': round(shear, 1), 'cheek_seat_bearing_MPa': round(bearing, 1),
           'bearing_at_a_2.94N_click_MPa': round(bearing_click, 2),
           'crossbar': {'A': round(A, 2), 'Iy': round(Iy, 2), 'Iz': round(Iz, 2), 'bending_inlayer_MPa': round(s_y + s_z, 1),
                        'sigma_Y_MPa': round(s_y, 1), 'sigma_Z_MPa': round(s_z, 1), 'torsion_MPa': round(tau_t, 2),
                        'shear_MPa': round(tau_v, 2), 'torsion_plus_shear_MPa': round(tau_t + tau_v, 2),
                        'torsion': {'method': 'Prandtl stress function, finite differences, h 0.01', 'J_mm4': round(Jt, 3),
                                    'peak_at_yz': at, 'governing_dx': s_w, 'T_Nmm': round(T, 2),
                                    'by_dx': {f'{q:.2f}': [round(r[0], 2), round(r[1], 2)] for q, r in rows.items()}}},
           'crossbar_root_depth_mm': round(depth, 2), 'crossbar_root_across_layers_MPa': round(root, 1), 'leg_root_MPa': round(leg_root, 1),
           'switch': {'plunger_N': round(Fs, 1), 'skhl_limit_N': SKHL_LIMIT, 'press_at_that_limit_N': round(SKHL_LIMIT * A_OUT / L_IN, 1),
                      'note': 'neither switch publishes a static limit; the plunger takes the over-press (accepted risk)'}}
    out['checks'] = {'rod bending <= 20 MPa (1x and 1/3x bearings)': max(rod1, rod3) <= 20.0,
                     'rod shear <= 8 MPa': shear <= 8.0, 'cheek/seat bearing <= 10 MPa': bearing <= 10.0,
                     'crossbar <= 25 MPa in-layer': s_y + s_z <= 25.0,
                     'crossbar torsion + shear <= 8 MPa': tau_t + tau_v <= 8.0,
                     'crossbar and leg roots <= 12 MPa': max(root, leg_root) <= 12.0}
    out['cheek'] = ck = cheek_stress()
    out['checks'].update(ck['checks'])
    return out


# The cheek (test 1, 2026-09-29: the open C's jaw cracked off at the bore and cranks came off the rod). Its stress across
# the layers is the test-1 study's 2D plane-stress FE of the cheek's section (a closed ring over |dx| 4.05..5.25, the
# rod's load a cos pressure over +-60 degrees about 31 degrees, fixed at the belly), recorded here, not recomputed, as
# EDGE_PRESS is: per N of pin load on one cheek, and at the 20 N over-press (19.5 N per cheek). The open C as built was
# 8.0 MPa per N (156 peak / 131 layer average at 20 N). The same rows as case-368's mechanics.cheek_stress.
# 2026-09-30 (Ian: thicker where it holds the rod; the ring study's v2d): the ring's bore round, the cheek's +Y face at
# -0.70 (on the layer grid) and the fill carried forward under the rod: 1.32 -> 1.26 per N, 25.8 / 19.7 -> 24.5 / 18.8
# at 20 N (the worst layer is still the +Z band where the key-limited 45-degree roof pinches it).
CHEEK_FE_PER_N = 1.26                                      # MPa per N per cheek, peak across the layers
CHEEK_FE_20N = {'peak': 24.5, 'layer_avg': 18.8}           # MPa at the 20 N over-press
CHEEK_LAYER_Y = (-3.0, -1.4)                               # the layer planes through the rod's bore (the crank prints
                                                           # on its pad end, +Y up, 0.2 layers)


def cheek_stress():
    """The cheek's rows (test 1): the ring closed round the rod at |dx| 4.65, with its wall round the bore (the least,
    and over the round bore's top at PY + d/2, a layer boundary, up to the CRANK_CHEEK_TRIM_Y face); the stress
    across the layers at the largest click (<= 12, BELL-CRANK-SPEC's across-layer rule for crank roots) and at the 20 N
    over-press (layer average <= 25: the band cannot grow, since the key's cheek zone and the 45-degree roof leave 0.142
    at theta 16, so the 12 at 20 N is not met; accepted because clicks are 2.6x under 12, and a band cracked by a jab
    still leaves the rod captive: the ring is closed and its fill side holds); and the least layer area per cheek
    through the rod, a geometry guard (at the slicer's layer mid-planes, pad end on the bed), on crank-M as built."""
    import trimesh
    from shapely.geometry import LinearRing, LineString, Point, Polygon, box as sbox
    from shapely.ops import nearest_points
    vs, ts = keys.crank('M').val().tessellate(0.002, 0.05)
    m = trimesh.Trimesh([(v.x, v.y, v.z) for v in vs], ts, process=True)
    py, pz = P.ROD_YZ
    xr = (P.CRANK_CHEEK_RING['x0'] + P.CRANK_CHEEK[1]) / 2           # 4.65
    ring = {}
    top_y = py + P.CRANK_BORE['d'] / 2                              # the ring's round bore's top (-1.50)
    for sd in (1, -1):
        S = keys.section(m, sd * xr)
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
    fmax = max(max(v.values()) for v in kf['finger_force_N'].values())
    pin_per_N = math.hypot(1.0, L_IN / A_OUT)
    click = CHEEK_FE_PER_N * pin_per_N * fmax / 2
    # the layer areas: each cheek's band (lip and ring) at the layer mid-planes y through the bore
    ys = [round(P.CRANK_PAD['end'] + 0.1 + 0.2 * i, 3) for i in range(60)]
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
        'cheek ring closed round the rod, wall over the bore >= 0.80, least >= 0.70': all(
            r['closed'] and r['wall_over_the_bore_mm'] >= 0.80 - 1e-3 and r['least_wall_mm'] >= 0.70 for r in ring.values()),
        'cheek across the layers at the largest click <= 12 MPa': click <= 12,
        'cheek at the 20 N over-press, layer average <= 25 MPa (accepted over 12)': CHEEK_FE_20N['layer_avg'] <= 25,
        'cheek least layer area through the rod >= 3.4 mm2': la[0] >= 3.4}
    return out


# ---- the rod's left stop: the side gate (SPEC2 rev 3, sections 6, 7 and check 8) --------------------------------
# Axial loads on the gate, rod end -> gate flat -> flange -> tub lips (the lid only caps the gate in Z). The 1.5 m
# drop is the loads report's 27 N (the rod's own axial stiffness caps the hit near 28 N: 5.4 m/s, 0.19 g,
# 140 N/mm); 33 N is the stiff-stop sensitivity. Sideways presses: 1.7 N at a click, 9 N at a 20 N over-press,
# 17.6 N extreme.
GATE_LOADS = {'sideways click': 1.7, 'sideways 20 N over-press': 9.0, 'extreme': 17.6, '1.5 m drop': 27.0,
              'stiff-stop sensitivity': 33.0}
GATE_STRIP = 3.53                 # one-way strip height (C3's p4b: patch 1.78 wide)
S_ACROSS, S_IN = 25.0, 50.0       # printed PLA across the layers / in them
ROD_STACK = dict(cut=0.2, gate=0.1, wall=0.1, square=0.05)   # end-play stack (+-): cut, gate and slot, +X wall, tail
# The edge press (pre-existing, unchanged by the gate): SPEC2 rev 3 section 7, from the coupled rod-crank-key FE of
# rodstop2/edge.md (the rod over its whole length on the rings and seats as built, the crank a beam, the key rigid
# on compression-only springs); recorded here, not re-run
EDGE_PRESS = {'20 N at the cap edge, bearings 1x (MPa)': [18.9, 19.6], '20 N at the cap edge, bearings 0.3x (MPa)': [24.4, 26.9],
              '20 N centred (MPa)': [14.1, 14.4], 'TS365 2.94 N click at the cap edge (MPa)': [2.0, 2.1],
              'source': 'SPEC2 rev 3 section 7; rodstop2/edge.md (edgefe.py, run2.txt): the rod over its whole length'}


def gate_bearing(shift):
    """The gate's flat bearing on each lip with the gate `shift` off centre in Y (its web locates it to +-0.10), from
    the plan: the flange's outer face (outside the web, less the bearing break) against the lip faces (from the
    mouth's edge to the cavity's straight end, where the round end starts). [(y0, y1), ...] for the -Y and +Y lips."""
    G, S = P.GATE, P.GATE_SLOT
    b = G['bearing_break']
    (f0, f1), (w0, w1) = G['flange_y'], G['web_y']
    (m0, m1), (c0, c1) = S['mouth'], S['cavity']
    return [(max(f0 + b + shift, c0), min(w0 + shift, m0)), (max(w1 + shift, m1), min(f1 - b + shift, c1))]


def gate_loads():
    """The gate and the tub's lips at each axial load and each Y offset the gate can take (0, +-0.05, +-0.10): C3's
    p4b one-way strip (c1_gate, variant N). Per side, the load from statics about the rod's axis. The lip, a
    cantilever along Y from its root (the cavity's round end) to the bearing's centroid, its depth growing round
    the end: the larger of 1.1 x the peak of (L + d) / t(d)^2 along the arc and 1.3 x L / t0^2, judged on 25 MPa
    (it also bends in Z, across its layers). The flange's wing, from the web's edge to the bearing's centroid, no Kt,
    judged on 50 (the gate prints on its X face, so its bending lies in its layers); its shear, across the layers,
    on 25. The lip faces' bearing pressure and the rod end on the flat (the rod face down, sagged +0.175, 1.72)."""
    G, S = P.GATE, P.GATE_SLOT
    yrod = P.ROD_YZ[0]
    t0, r, fl = S['lip'], S['end_r'], G['flange']
    (c0, c1), (w0, w1) = S['cavity'], G['web_y']
    rows, worst = {}, {}
    for sh in (0.0, 0.05, -0.05, 0.10, -0.10):
        (a0, a1), (b0, b1) = gate_bearing(sh)
        ca, cb = (a0 + a1) / 2, (b0 + b1) / 2
        la, lb = yrod - ca, cb - yrod
        fa, fb = lb / (la + lb), la / (la + lb)
        sides = []
        for side, f, cen, w, root, web in (('-Y', fa, ca, a1 - a0, c0, w0 + sh), ('+Y', fb, cb, b1 - b0, c1, w1 + sh)):
            L = abs(cen - root)
            peak = max((L + d) / (t0 + r - math.sqrt(max(r * r - d * d, 0.0))) ** 2 for d in [r * i / 400 for i in range(401)])
            k_lip = max(1.1 * peak, 1.3 * L / t0 ** 2)
            arm = abs(web - cen)
            sides.append({'side': side, 'share': f, 'bearing': w, 'lever': L, 'arm': arm, 'k_lip': k_lip})
        rows[f'{sh:+.2f}'] = sides
    out = {'offsets': {k: [{'side': s['side'], 'share_pct': round(100 * s['share'], 1), 'bearing_mm': round(s['bearing'], 3),
                            'lip_lever': round(s['lever'], 3), 'flange_arm': round(s['arm'], 3)} for s in v] for k, v in rows.items()},
           'loads': {}}
    for name, F in GATE_LOADS.items():
        per = {}
        for k, sides in rows.items():
            lip = max(6 * s['share'] * F / GATE_STRIP * s['k_lip'] for s in sides)
            flange = max(6 * s['share'] * F / GATE_STRIP * s['arm'] / fl ** 2 for s in sides)
            shear = max(1.5 * s['share'] * F / (fl * GATE_STRIP) for s in sides)
            bear = max(s['share'] * F / (s['bearing'] * GATE_STRIP) for s in sides)
            per[k] = (lip, flange, shear, bear)
        c, w = per['+0.00'], [max(v[i] for v in per.values()) for i in range(4)]
        out['loads'][name] = {'N': F, 'lip_MPa': [round(c[0], 1), round(w[0], 1)], 'lip_SF_on_25': [round(S_ACROSS / c[0], 2), round(S_ACROSS / w[0], 3)],
                              'flange_MPa': [round(c[1], 1), round(w[1], 1)], 'flange_SF_on_50': [round(S_IN / c[1], 2), round(S_IN / w[1], 2)],
                              'flange_shear_MPa': [round(c[2], 1), round(w[2], 1)], 'shear_SF_on_25': [round(S_ACROSS / c[2], 2), round(S_ACROSS / w[2], 2)],
                              'lip_bearing_MPa': [round(c[3], 1), round(w[3], 1)], 'note': '[centred, worst offset]'}
    # the rod's end on the flat: the flat covers the end face from its top down to floor_z
    d = 1.72
    for name, sag in (('face down (+0.175)', 0.175), ('nominal', 0.0)):
        e = S['floor_z'] - (P.ROD_YZ[1] + sag)                        # the flat's edge past the axis
        R = d / 2
        seg = R * R * math.acos(e / R) - e * math.sqrt(R * R - e * e)  # the uncovered segment beyond the edge
        area = math.pi * R * R - seg
        out.setdefault('rod_end_on_flat', {})[name] = {'flat_past_axis': round(e, 3), 'covered_pct': round(100 * area / (math.pi * R * R), 1),
                                                        'MPa_at_27N': round(27.0 / area, 1)}
    L27, L33 = out['loads']['1.5 m drop'], out['loads']['stiff-stop sensitivity']
    ax = [out['loads'][k] for k in ('sideways 20 N over-press', 'extreme')]
    out['checks'] = {
        '27 N drop, every offset: lip SF >= 2.0 on 25': L27['lip_SF_on_25'][1] >= 2.0,
        '27 N drop, every offset: gate flange SF >= 2.0 on 50 in-plane': L27['flange_SF_on_50'][1] >= 2.0,
        '27 N drop, every offset: flange interlayer shear SF >= 2.0 on 25': L27['shear_SF_on_25'][1] >= 2.0,
        # reported, and accepted at a lip SF of 1.7 (SPEC2 rev 3: 1.70, its hand model's value at two decimals)
        '33 N stiff stop: lip SF >= 1.7 on 25 (reported)': 'accepted' if round(L33['lip_SF_on_25'][1], 2) >= 1.7 else False,
        'axial 9 N and 17.6 N: lip and gate SF >= 3': all(min(a['lip_SF_on_25'][1], a['flange_SF_on_50'][1]) >= 3.0 for a in ax)}
    return out


def end_play():
    """The rod's end play between the gate's flat and the +X wall: from the cut's tolerance alone, and with the
    whole stack (ROD_STACK: cut, gate and slot, wall, a tail not quite square)."""
    nom = P.ROD_STOPS[1] - P.ROD_STOPS[0] - P.ROD_CUT
    st = sum(ROD_STACK.values())
    out = {'stops': [round(P.ROD_STOPS[0], 3), round(P.ROD_STOPS[1], 3)], 'cut': P.ROD_CUT, 'nominal': round(nom, 3),
           'from_the_cut': [round(nom - ROD_STACK['cut'], 3), round(nom + ROD_STACK['cut'], 3)],
           'with_the_stack': [round(nom - st, 3), round(nom + st, 3)], 'stack': ROD_STACK}
    out['checks'] = {'end play 0.30-0.70 from the cut, 0.05-0.95 with the stack (never jams)':
                     abs(out['from_the_cut'][0] - 0.30) < 1e-6 and abs(out['from_the_cut'][1] - 0.70) < 1e-6 and out['with_the_stack'][0] > 0.0}
    return out


def rod_span_fe(F_pin, kfac=1.0, tail=None, h=0.02):
    """The rod over its whole length (tail at `tail`, the gate's flat by default, to its tip), a beam on elastic
    bearings (Winkler, 0.8 E per mm, as rod_fe) wherever the tub holds it: the sliver's hole (from the gate cavity
    to the pocket's wall) and the rail up to RAIL_END_X, but not across each cheek's slot. One crank at a time
    loaded as rod_fe (half the pin load over each cheek). Returns {key: (peak MPa, dx of the peak from the key)}."""
    import numpy as np
    from scipy.sparse import lil_matrix
    from scipy.sparse.linalg import spsolve
    d = 1.72
    I = math.pi * d ** 4 / 64
    Zs = math.pi * d ** 3 / 32
    x0 = P.ROD_STOP_X0 if tail is None else tail
    x = np.arange(x0, x0 + P.ROD_CUT + h / 2, h)
    n = len(x)
    kb = np.zeros(n)
    sl = P.X0 + P.GATE_SLOT['lip'] + 2 * P.GATE_SLOT['end_r']
    kb[(x >= sl) & (x <= P.RAIL_END_X)] = kfac * E * 0.8
    xs = {r: keys.key_x(r) for r in P.KEY_REFS}
    for xc in xs.values():
        kb[(np.abs(x - xc) > P.SLOT[0]) & (np.abs(x - xc) < P.SLOT[1])] = 0.0
    ke = E * I / h ** 3 * np.array([[12, 6 * h, -12, 6 * h], [6 * h, 4 * h * h, -6 * h, 2 * h * h],
                                    [-12, -6 * h, 12, -6 * h], [6 * h, 2 * h * h, -6 * h, 4 * h * h]])
    K = lil_matrix((2 * n, 2 * n))
    for e in range(n - 1):
        for i in range(4):
            for j in range(4):
                K[2 * e + i, 2 * e + j] += ke[i, j]
    for i in range(n):
        K[2 * i, 2 * i] += kb[i] * h
    K = K.tocsr()
    out = {}
    for r, xc in xs.items():
        Fv = np.zeros(2 * n)
        for a, b in ((xc - P.CRANK_CHEEK[1], xc - P.CRANK_CHEEK[0]), (xc + P.CRANK_CHEEK[0], xc + P.CRANK_CHEEK[1])):
            m = (x >= a) & (x <= b)
            Fv[0::2][m] += (F_pin / 2) / m.sum()
        w = spsolve(K, Fv)[0::2]
        M = E * I * np.gradient(np.gradient(w, h), h)
        i = int(np.argmax(np.abs(M)))
        out[r] = (float(abs(M[i]) / Zs), round(float(x[i] - xc), 2))
    return out


def rod_gate():
    """SPEC2 rev 3, check 8: end play, the gate at every axial load and offset, the rod over its new span at a 20 N
    press centred (<= 14.6 MPa; tail at the gate and at the far end of its play), the edge press recorded."""
    F = OVERPRESS
    pin = math.hypot(F, F * L_IN / A_OUT)
    span = {}
    for name, tail in (('tail on the gate', P.ROD_STOP_X0), ('tail at the far end of its play', P.ROD_STOPS[1] - P.ROD_CUT)):
        for kf, kn in ((1.0, '1x'), (1 / 3, '1/3x')):
            span[f'{name}, bearings {kn}'] = {r: [round(v[0], 2), v[1]] for r, v in rod_span_fe(pin, kf, tail).items()}
    worst1 = max(v[0] for k, rr in span.items() if k.endswith('1x') for v in rr.values())
    out = {'end_play': end_play(), 'gate': gate_loads(),
           'rod_span_20N': {'pin_N': round(pin, 1), 'rod_mm': [round(P.ROD_STOP_X0, 2), round(P.ROD_STOP_X0 + P.ROD_CUT, 2)], 'by_key': span,
                            'worst_1x_MPa': round(worst1, 2)},
           'edge_press': EDGE_PRESS}
    out['checks'] = {**out['end_play']['checks'], **out['gate']['checks'],
                     'rod over its new span, 20 N centred, bearings 1x: <= 14.6 MPa': worst1 <= 14.6,
                     'edge press recorded (18.9-19.6 MPa at 1x; 24.4-26.9 at 0.3x, pre-existing)': True}
    return out


def key_sweep():
    """The key alone from its stop (the hooks' tops on the slot's roof, KEY_W_OUT above rest) down to PRESS_LOW (the
    spec's check 3, and test 2's), on the tub as built (out/<variant>/tub.stl), in the checks' bands (keys.BANDS): no
    overlap with the tub, the hooks included; the +Y face on its guide over at least 2.5 of Lg; nothing of the key on the
    crank but the crown while the crank follows it (to 16 degrees; the crown's contact on the pusher is key_fit's); and
    the stop: lifted 0.05 past W_OUT both hooks are under the roof (they overlap it), at W_OUT - 0.02 nothing touches.
    Side push (2026-10-03, the 50-layer key's audit: the sweep above keeps the key centred in X): the same lifts with
    the key pushed across by its side play to each side, its ends 0.01 off the opening's sides: no overlap with the
    tub, the hooks included (each band against the tub's shadow over the band moved by the push)."""
    import trimesh
    from shapely.geometry import LineString
    from shapely.ops import unary_union
    tub_m = trimesh.load(P.OUT / 'tub.stl')
    stop = P.KEY_W_OUT
    low16 = keys.crown_shift(16.0)
    th_of = {}
    rows = []
    worst = {'key - tub': (9.0, None), 'hook - tub': (9.0, None), 'key - crank (but the crown)': (9.0, None)}
    guide_min = (99.0, None)                     # the whole bands (dx >= x7), every lift
    Bd, czz = P.KEY_BODY, P.KEY_CHEEK_ZONE['z0']
    x7 = round(-Bd['half'] + (czz - Bd['z0']), 3)   # -1.00: the body's -X step is cut 45 degrees from dx -3.30 to here
    cut = {'le0': (99.0, None), 'stop': (99.0, None)}
    engage = {'over (+0.05)': 9.0, 'under (-0.02)': 0.0, 'bands': 0}
    for ref in P.KEY_REFS:
        xc = keys.key_x(ref)
        sh = [(a, b, keys.shadow(tub_m, xc + a, xc + b)) for a, b in keys.bands()]
        for a, b, t in sh:
            kk = keys.key_yz(a, b)
            if 'hook' in kk and abs((a + b) / 2) > P.KEY_HOOK['dx'][0]:
                ov = keys.lift(kk['hook'], stop + 0.05).intersection(t)
                engage['over (+0.05)'] = min(engage['over (+0.05)'], round(ov.bounds[2] - ov.bounds[0], 3) if ov.area > 1e-7 else 0.0)
                engage['under (-0.02)'] = max(engage['under (-0.02)'], round(keys.lift(kk['hook'], stop - 0.02).intersection(t).area, 5))
                engage['bands'] += 1
        n = int(round((stop - PRESS_LOW) / 0.05))
        for i in range(n + 1):
            lf = round(stop - i * 0.05, 4)
            if lf not in th_of:
                th_of[lf] = 0.0 if lf >= 0 else _theta_for_lift(lf)
            th = th_of[lf]
            for a, b, t in sh:
                kk = keys.key_yz(a, b)
                if not kk:
                    continue
                kg = keys.lift(kk['key'], lf)
                g = keys.gap(kg, t)
                if g is not None and g < worst['key - tub'][0]:
                    worst['key - tub'] = (g, [ref, round(lf, 2), a, b])
                if 'hook' in kk:
                    g = keys.gap(keys.lift(kk['hook'], lf), t)
                    if g is not None and g < worst['hook - tub'][0]:
                        worst['hook - tub'] = (g, [ref, round(lf, 2), a, b])
                cr = keys.crank_yz(a, b)
                if cr and lf >= low16 - 1e-9:
                    rest = keys.turn(unary_union([v for k_, v in cr.items() if k_ != 'crown']), th)
                    g = min(q for q in (keys.gap(keys.lift(v, lf), rest) for v in kk.values()) if q is not None)
                    if g < worst['key - crank (but the crown)'][0]:
                        worst['key - crank (but the crown)'] = (g, [ref, round(lf, 2), round(th, 2), a, b])
                if abs((a + b) / 2) < Bd['half']:
                    # the +Y face from its bottom (the body's z0; in the cut step's bands its highest point, at the
                    # band's -X end) to the cap's chamfer, on the tub's shadow over the band
                    z1 = keys.TOP - P.KEY_CAP['chamfer'] + lf
                    tb = t.buffer(0.01)
                    for part_, z0 in (('whole', Bd['z0']) if b > x7 else (None, None),
                                      ('cut', max(Bd['z0'], czz - (a + Bd['half']))) if a < x7 else (None, None)):
                        if part_ is None:
                            continue
                        face = LineString([(P.RAIL_Y[0] - 0.005, z0 + lf), (P.RAIL_Y[0] - 0.005, z1)])
                        on = round(face.intersection(tb).length, 3)
                        where = [ref, round(lf, 2), a, b]
                        if part_ == 'whole' and on < guide_min[0]:
                            guide_min = (on, where)
                        if part_ == 'cut' and lf <= 1e-9 and on < cut['le0'][0]:
                            cut['le0'] = (on, where)
                        if part_ == 'cut' and i == 0 and on < cut['stop'][0]:
                            cut['stop'] = (on, where)
            if ref == P.KEY_REFS[0] and i % 10 == 0:
                rows.append({'lift': round(lf, 2), 'theta': round(th, 2)})
    # the side push: the key's ends 0.01 off the opening's sides
    push = round(P.KEY_OPENING['half'] - P.KEY_CAP['half'] - 0.01, 3)
    side = {'+X': (9.0, None), '-X': (9.0, None)}
    n = int(round((stop - PRESS_LOW) / 0.05))
    for ref in P.KEY_REFS:
        xc = keys.key_x(ref)
        for sd, d in (('+X', push), ('-X', -push)):
            sh = [(a, b, kk, keys.shadow(tub_m, xc + d + a, xc + d + b)) for a, b in keys.bands() for kk in [keys.key_yz(a, b)] if kk]
            for i in range(n + 1):
                lf = round(stop - i * 0.05, 4)
                for a, b, kk, t in sh:
                    for v in kk.values():
                        g = keys.gap(keys.lift(v, lf), t)
                        if g is not None and g < side[sd][0]:
                            side[sd] = (g, [ref, round(lf, 2), a, b])
    out = {'from_lift': round(stop, 3), 'to_lift': PRESS_LOW, 'crank_follows_to_lift': round(low16, 3), 'rows': rows,
           **{k: {'gap': v[0], 'at': v[1]} for k, v in worst.items()},
           'guide_on_face_min_mm': {'length': guide_min[0], 'at': guide_min[1]},
           'guide_on_face_cut_step_bands_mm': {'dx': [-Bd['half'], x7], 'lifts_le_0_min': {'length': cut['le0'][0], 'at': cut['le0'][1]},
                                               'at_the_stop': {'length': cut['stop'][0], 'at': cut['stop'][1]},
                                               'note': 'the body -X step, cut 45 degrees for the print on end (test 1): '
                                                       'held to 2.5 at rest and pressed; at the stop reported'},
           'hooks_at_the_stop': engage,
           'side_push': {'push_mm': push, **{k: {'gap': v[0], 'at': v[1]} for k, v in side.items()}}}
    out['checks'] = {f'no key/tub overlap from the stop to {PRESS_LOW}, hooks included': min(worst['key - tub'][0], worst['hook - tub'][0]) >= -1e-4,
                     'nothing of the key on the crank but the crown (to 16 degrees)': worst['key - crank (but the crown)'][0] >= -1e-4,
                     '+Y face on the guide >= 2.5 (whole bands, every lift)': guide_min[0] >= 2.5,
                     '+Y face on the guide >= 2.5 (the cut step bands, at rest and pressed)': cut['le0'][0] >= 2.5,
                     f'the stop engages at W_OUT {stop}: every hook band under the roof at +0.05, clear at -0.02':
                         engage['bands'] > 0 and engage['over (+0.05)'] > 0 and engage['under (-0.02)'] <= 1e-6,
                     f'pushed across by its side play (+-{push}), no key/tub overlap from the stop to {PRESS_LOW}, hooks included':
                         min(side['+X'][0], side['-X'][0]) >= -1e-4}
    return out


def _theta_for_lift(lf):
    lo, hi = 0.0, 40.0
    for _ in range(50):
        m = (lo + hi) / 2
        if keys.crown_shift(m) > lf:
            lo = m
        else:
            hi = m
    return (lo + hi) / 2


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
    out['midplate_spring'] = {f'{d:+.1f}mm_panel': bridge(midplate.SPRING_L, midplate.SPRING_W, midplate.SPRING_T,
                                                          max(0.0, mp_nominal + d))
                              for d in (-0.2, 0.0, 0.2)}
    out['midplate_spring']['count'] = len(midplate.SPRINGS)
    out['midplate_spring']['travel_limit_mm'] = P.MID_T - midplate.SPRING_T
    bx0, bx1 = P.BATT['x']
    L = (bx1 - 4.0) - (bx0 + 4.0)
    out['battery_spring'] = {f'{d:+.1f}mm_pack': bridge(L, 4.0, 0.6, max(0.0, 0.5 + d)) for d in (-0.3, 0.0, 0.3)}
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
            'rev_h_pla_N': round(F_SW + REV_H_TAB_K_PETG[t['ref']] * E / 2000.0 * (0.39 + CLICK), 2),
            'rev_i_N': REV_I_SIDE_N[t['ref']],
            'stress_at_stop_MPa': round(kk * stop * max(arm * cz for arm, cz in secs), 1),
            'strain_at_stop_pct': round(100 * kk * stop * max(arm * cz for arm, cz in secs) / E, 2)}
    return rows, {'void_mm': P.TAB_VOID, 'relief_mm': P.TAB_RELIEF_MAX,
                  'note': 'the bar bottoms on the sliver above the nub window when the switch reaches its maximum travel'}


# ---- side keys' reach (test 1, 2026-09-29: the three +X keys did not click, the two -X keys did) ----------------
# The lid carries the keys, and it holds the board in X only by the H5 pin (lid.py: d1.9 in the board's 2.2 hole)
# and by J1's mouth on its USB block (USB_FLOOR['lid_gap'] in front of it, so it bears only when the board moves
# +X), both on the board's +X half. A press pushes the board away from the key: a -X key drives J1 onto the block
# almost at once, a +X key lets the board back off until the pin bears. The board is screwed to the tub (M2 in its
# 2.2 holes) and J1's mouth stands INSERT_X1 - mouth in front of the tub's port floor; the tub floats in the lid's
# groove by JOINT['clr'] a face.
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
                    # the most the plunger goes in before the key bottoms (the switch's rated maximum is TRAVEL_MAX)
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
    for dt in (-0.2, 0.0, 0.2):
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
            'lip_bearing_on_touch_film_mm': {'left': round(wx0 - tx0, 2), 'right': round(tx1 - wx1, 2),
                                             'bottom': round(wy0 - ty0, 2), 'top': round(ty1 - wy1, 2)},
            # the light-strip builds keep Rev K's window (params WINDOW_CHAMFER, WINDOW_BEVEL), the others the 35-degree one
            **({'window_land_mm': round(P.SKIN - P.WINDOW_CHAMFER, 2), 'window_bevel_mm': P.WINDOW_CHAMFER} if P.LIGHT_STRIP else
               {'window_land_mm': round(P.SKIN - P.WINDOW_BEVEL_DEPTH, 2), 'window_bevel_mm': P.WINDOW_BEVEL_W,
                'window_bevel_deg': P.WINDOW_BEVEL_ANGLE,
                'window_corner_r_mm': [P.WINDOW_CORNER_R, round(P.WINDOW_CORNER_R + P.WINDOW_BEVEL_W, 3)]}),
            'visible_border_beyond_active_mm': P.WINDOW_MARGIN}


def plain_stack():
    """Light-strip variant: the plain GDEY0426T82 (PLAIN['t'] +- t_tol) held with its PS face on the tub's
    stops at PLAIN_FRONT (a layer boundary, as it prints) and the strip's bar 0.015 under the hold-downs.
    The springs push the plate and the panel onto the stops: their deflection, force and the travel left,
    for the thin, nominal and thick panel."""
    L = P.PLAIN
    rows = {}
    n = len(midplate.SPRINGS)
    limit = P.MID_T - midplate.SPRING_T
    for dt in (-L['t_tol'], 0.0, L['t_tol']):
        rear = P.PLAIN_FRONT - (L['t'] + dt)                 # the panel's rear = the plate's front face
        nub_tip = rear - P.MID_T - midplate.NUB_H
        defl = P.PCB_FRONT - nub_tip
        b = bridge(midplate.SPRING_L, midplate.SPRING_W, midplate.SPRING_T, max(0.0, defl))
        rows[f'{dt:+.1f}mm_panel'] = {'panel_rear_z': round(rear, 3), 'spring_deflection_mm': round(defl, 3),
                                      'travel_left_mm': round(limit - defl, 3), 'force_N_each': b['force_N'],
                                      'force_N_total': round(b['force_N'] * n, 2), 'stress_MPa': b['stress_MPa']}
    return {'stop_face_z': P.PLAIN_FRONT, 'springs': n, 'travel_limit_mm': limit, 'rows': rows,
            'fct01c_nominal_deflection_mm': round(midplate.NUB_H - (P.MID_REAR - P.PCB_FRONT), 3),
            'holddown_z': P.STRIP_HOLD['z'], 'bar_flex_top_z': round(P.STRIP_FLEX_TOP, 3),
            'holddown_gap_mm': round(P.STRIP_HOLD['z'] - P.STRIP_FLEX_TOP, 3)}


def latches():
    """Tub-to-lid latch arm (joint.py): a cantilever standing on the lid floor, tapering
    linearly from t_root to t_tip, deflected by the barb's engagement as the lid goes on.
    Tip deflection under a tip load F: d = F * integral((L - s)^2 / (E I(s)) ds)."""
    import joint
    S = P.SNAP
    _, h = joint.snap_profile()
    L = h['z_c'] - h['z_root']                    # the barb's load acts at its retaining face
    y = S['barb'] - S['gap']                      # the arm bends by the barb's engagement
    n = 400
    comp = 0.0
    for i in range(n):
        s = (i + 0.5) * L / n
        t = S['t_root'] + (S['t_tip'] - S['t_root']) * s / L
        comp += (L - s) ** 2 / (E * S['w'] * t ** 3 / 12) * (L / n)
    F = y / comp                                  # transverse force at full deflection
    strain = 6 * F * L / (S['w'] * S['t_root'] ** 2) / E
    lead = math.radians(S['lead_deg'])
    push = F * (math.tan(lead) + MU) / (1 - MU * math.tan(lead))
    pull = F * (1 + MU) / (1 - MU)                # 45-degree retaining face
    n = sum(len(v) for v in P.SNAPS.values())
    # the arms' inner top chamfer (params.SNAP_INNER_CHAMFER, every arm since 2026-10-12) is above the barb's catch,
    # where the barb's load puts no moment into the arm, and leaves the barb's points as they are: the figures above
    # hold for it
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
            'pocket_z': [round(h['catch_low'] - 0.1, 2), round(h['z_top'] + 0.15, 2)], 'inner_top_chamfer': cham,
            'rev_h': {'catch_mm': 0.2, 'backed': '3 of 11', 'note': '8 of 11 pulled on an unbacked 0.8 mm sliver'},
            'note': 'bends across layer lines (arm prints standing up), so strain is kept low; every pocket '
                    'is backed by solid wall above the side keys\' slots'}


def board_snap():
    """The midplate's snap posts through the board's H1/H2 holes: what the fingers have to do to
    get in, and what they hold afterwards."""
    B = P.BOARD_SNAP
    hole = 2.2                                              # board's drilled hole
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
    ssweep = side_key_sweep(tub_s, lid_s, mid_s)
    import panel
    import joint
    sp = springs()
    # the bottom keys' entries only with the bottom keys (chinless has none), in the same order as ever
    kk = ({'key_forces': key_forces(), 'key_hooks': key_hooks(), 'key_fit': key_fit(), 'key_proud': key_proud(),
           'key_overpress': overpress(), 'key_sweep': key_sweep()} if P.BOTTOM_KEYS else {})
    rep = {**kk,
           'springs': sp, 'side_key_reach': side_key_reach(sp['side_keys']), 'screen_stack': screen_stack(),
           **({'plain_stack': plain_stack()} if P.LIGHT_STRIP else {}),
           'joint': joint.summary(), 'latches': latches(), 'board_snap': board_snap(), 'mid_detents': mid_detents(),
           'ribbons': {f'{dt:+.1f}mm_panel': panel.report(total=hw.PANEL_T + dt) for dt in (-0.2, 0.0, 0.2)},
           'side_key_sweep': ssweep, **({'rod_gate': rod_gate()} if P.BOTTOM_KEYS else {})}
    (P.OUT / 'mechanics.json').write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: v for k, v in rep.items() if k != 'side_key_sweep'}, indent=1))
    for ref, rows in ssweep.items():
        print(ref)
        for r in rows:
            print('   ', r)
    print("side keys' reach (test 1: nub travel left for the switch under a press):")
    for k, ok in rep['side_key_reach']['checks'].items():
        print(f"  {'PASS' if ok else 'FAIL'}  {k}")
    if P.BOTTOM_KEYS:
        print('key height at rest (the crank spec, 8.6):')
        for k, ok in rep['key_proud']['checks'].items():
            print(f"  {'PASS' if ok else 'FAIL'}  {k}  {rep['key_proud']['range_mm']}")
        print('rod and gate (SPEC2 rev 3, check 8):')
        for k, ok in rep['rod_gate']['checks'].items():
            print(f"  {'PASS' if ok is True else ('ACCEPTED' if ok == 'accepted' else 'FAIL')}  {k}")
