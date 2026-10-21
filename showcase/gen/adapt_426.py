"""The 4.26" adapter: everything the showcase needs from the 4.26 case project, in the contract's shapes
(sc_contract.py, ../API.md), for its four builds (standard, light strip, and the two without bottom keys: chinless since
2026-10-04, light-strip chinless since 2026-10-07).

Run it from the 4.26 project's root (enclosures/case-426) with a Python 3.11 virtual environment made from its requirements.txt, after build.py and
mechanics.py:

    <venv>/Scripts/python.exe -B ../../showcase/gen/adapt_426.py [--out DIR] [--reuse] [--check-only]

--out defaults to showcase/build/426/ (not in git), where bundle.py looks by default.

The project's params.py fixes the build at import time (SILKSCREEN_VARIANT), so this script runs itself once
per build as a child process (--child std|ls|cl|lc), each writing _work/<b>/{meshes.npz, data.json}, then combines:

  core-426.json          model file: the nodes both builds share (checked by mesh hash, and against
                         out/shared-parts.json for the printed parts)
  build-426-std.json     model file: the nodes that differ (tub, panel_*, ribbon_*)
  build-426-ls.json
  build-426-cl.json      the chinless build: its tub and lid (replacing core's lid) and the FT01C's panel_* / ribbon_*;
                         data-426-cl.json meta.absent_nodes lists the core nodes it leaves out (keys, cranks, rod, gate,
                         the bottom switches)
  build-426-lc.json      the light-strip chinless build: its tub, the chinless lid and the plain panel's panel_epd /
                         ribbon_main (the strip itself is drawn by the page, strip3d.js); absent_nodes as chinless
  extras-426.json        model file: cmp_* (the X4 and its retro case) and dummy_pcba
  data-426-<b>.json      data (sc_contract.validate_data), strict, with the node cross-check, one per build
  models-426.js          the print zip: the repo's print/4.26/ (every tub, the chinless lid, the shared parts once,
                         coupons, ROD.txt; the chinless builds' STEP files stay out: sc_contract.ZIP_NOT_SHOWN), the rod
                         jig (print/rod-jig.*) and the PCBA dummy
  adapter-426.json         a report for the bundler: node lists, shared / per-build parts, file sizes, checks

Nothing is written into the project: out/ is snapshotted (names, sizes, mtimes) before and after, and the run
fails if it changed. compare.main() writes out/<b>/compare.json, so its P.OUT is redirected for that call.
"""
import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path

GEN = Path(__file__).resolve().parent
sys.path.insert(0, str(GEN))
import numpy as np                                               # noqa: E402
import sc_contract as C                                          # noqa: E402

SIZE = '426'
REPO = GEN.parents[1]
PRINT = REPO / 'print' / '4.26'                                  # build.write_print's per-part files
ROD_JIG = [REPO / 'print' / 'rod-jig.stl', REPO / 'print' / 'rod-jig.step']   # enclosures/rod_jig.py, both sizes
DEFAULT_OUT = REPO / 'showcase' / 'build' / SIZE                 # not in git; bundle.py's default --from426
ENV = dict(C.BUILD_DIRS)                                         # build id -> SILKSCREEN_VARIANT and out/<dir>
BUILDS = C.builds_of(SIZE)                                       # std, ls, cl and lc (the chinless cases: no bottom keys)
T0 = time.time()


def log(*a):
    print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)


# ---- text: every string in the data is ASCII --------------------------------------------------------------
# Plain-text fields (tag, title, label, detail, id, name) must stay plain ASCII (the page sets them as text).
# HTML fields may carry entities. asciify() maps the common typographic characters to ASCII and anything
# else to a numeric entity, so both kinds are safe.
_PLAIN = {'\u00d7': 'x', '\u2013': '-', '\u2014': ' - ', '\u2212': '-', '\u2018': "'", '\u2019': "'",
          '\u201c': '"', '\u201d': '"', '\u00b1': '+/-', '\u00b0': ' deg', '\u2026': '...', '\u2192': '->',
          '\u2264': '<=', '\u2265': '>=', '\u00b5': 'u', '\u2033': '"', '\u2032': "'", '\u00a0': ' ',
          '\u2248': '~', '\u00b7': '-', '\u2194': '<->'}


def asciify(obj):
    if isinstance(obj, str):
        s = ''.join(_PLAIN.get(c, c) for c in obj)
        return ''.join(c if ord(c) < 0x80 else f'&#x{ord(c):x};' for c in s)
    if isinstance(obj, dict):
        return {asciify(k): asciify(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [asciify(v) for v in obj]
    return obj


def H(s):
    """An HTML string written with \\u escapes in this source: typographic characters as entities."""
    return ''.join(c if ord(c) < 0x80 else f'&#x{ord(c):x};' for c in s)


def rnd(obj, nd=4):
    import sc_lib as L
    return L.rnd(obj, nd)


def snapshot(root):
    """(relative path, size, mtime_ns) of every file under root/out: the proof that nothing wrote there."""
    out = root / 'out'
    return sorted((str(p.relative_to(out)), p.stat().st_size, p.stat().st_mtime_ns) for p in out.rglob('*') if p.is_file())


# ============================================================================================================
# child: one build, in its own process (SILKSCREEN_VARIANT set by the parent)
# ============================================================================================================
def child(b, out):
    root = Path.cwd()
    sys.path.insert(0, str(root / 'src'))
    import trimesh
    import sc_lib as L
    import hw
    import params as P
    assert P.VARIANT == ENV[b], (P.VARIANT, b)
    import keys, body, midplate, refs, panel, logo, joint, sidekeys, tub   # noqa: E401
    OB = P.OUT
    work = out / '_work' / b
    work.mkdir(parents=True, exist_ok=True)
    mech = json.loads((OB / 'mechanics.json').read_text())
    fps = hw.footprints()
    tabs = body.side_tabs()
    LS = P.LIGHT_STRIP
    KEYS = P.BOTTOM_KEYS                                 # False on the chinless builds: no keys, cranks, rod, gate
    CL = not KEYS
    LC = LS and CL                                       # the light-strip chinless: the plain panel + strip, no keys
    log(b, 'start', OB)

    # ---- meshes ------------------------------------------------------------------------------------------
    M = {}
    stl = lambda n: L.load_stl(OB / f'{n}.stl')                           # noqa: E731
    M['tub'] = stl('tub')
    M['lid'] = stl('lid_body')                           # NOT lid.stl: it has the side keys fused in
    side_refs = [t['ref'] for t in tabs]
    for r in side_refs:
        M[f'skey_{r}'] = stl(f'skey_{r}')
    M['midplate'] = stl('midplate')
    for r in P.KEY_REFS:
        M[f'key_{r}'] = stl(f'key_{r}')
    if KEYS:
        M['crank_M'] = stl('crank-M')
        M['crank_T'] = stl('crank-T')
        M['rod'] = stl('ref_rod')
        M['gate'] = stl('gate')                          # the side gate (the rod's left stop), installed pose
    # the display: FT01C (three layers, three ribbons) or the plain GDEY0426T82 (one panel, its EPD FPC)
    if LS:
        pb = refs.plain_body()
        M['panel_epd'] = L.tess(pb['glass'].union(pb['fpl']).union(pb['ps']))
        M['ribbon_main'] = refs.plain_fpc()
        dl = {'glass': L.tess(pb['glass'], 0.01, 0.1), 'fpl': L.tess(pb['fpl'], 0.01, 0.1), 'ps': L.tess(pb['ps'], 0.01, 0.1)}
        disp = [('glass', 'glass', dl['glass']), ('fpl', 'film', dl['fpl']), ('ps', 'film', dl['ps'])]
    else:
        pb = panel.body()
        M['panel_epd'] = L.tess(pb['glass'].union(pb['fpl']))
        M['panel_light'] = L.tess(pb['oca3'].union(pb['lgp']).union(pb['oca2']))
        M['panel_touch'] = L.tess(pb['touch'])
        for k, m in panel.ribbons().items():
            M[f'ribbon_{k}'] = m
        disp = [('epd', 'glass', M['panel_epd']), ('light', 'lgp', M['panel_light']), ('touch', 'film', M['panel_touch'])]
    log(b, 'printed parts + display', len(M))
    M.update(refs.battery_meshes())
    moving = P.KEY_REFS + hw.LEFT_SWITCHES + hw.RIGHT_SWITCHES + [hw.RESET]
    M.update(L.board_meshes(hw, moving, bodies=P.KEY_REFS, table=L.CATEGORY_426))
    log(b, 'board', len(M))
    sw = keys.SWITCH
    # keys.SWITCH against sc_contract's one definition of each switch (the 3.68 draws the same parts): the MJTP1117
    # is the same spec envelope; keys.SWITCH's TS365 plunger is the WORST case (the checks' band), the nominal one
    # is build.py's "crank-T on TS365, nominal" case, which is what the page draws (x3 params.TS365 alike)
    gM, gT = C.SWITCH_GEOM['M'], C.SWITCH_GEOM['T']
    assert (list(sw['MJTP']['housing'][0]) == gM['housing_yz'] and sw['MJTP']['housing'][1] == gM['housing_half_x']
            and list(sw['MJTP']['nub'][0]) == gM['nub_yz'] and sw['MJTP']['nub'][1] == gM['nub_half_x']
            and sw['MJTP']['face'] == gM['face_y']), ('keys.SWITCH MJTP vs sc_contract.SWITCH_GEOM', sw['MJTP'])
    tn = sw['TS365']['nub'][0]
    assert (list(sw['TS365']['housing'][0]) == gT['housing_yz'] and sw['TS365']['housing'][1] == gT['housing_half_x']
            and sw['TS365']['nub'][1] == gT['nub_half_x'] and sw['TS365']['face'] == gT['face_y']
            and sw['TS365']['tip'][0] == gT['face_worst_y'] and [tn[1], tn[3]] == gT['nub_z_worst']
            and tn[2] == gT['nub_yz'][2]), ('keys.SWITCH TS365 vs sc_contract.SWITCH_GEOM', sw['TS365'])
    if KEYS:
        M['sw_T_body'], M['sw_T_nub'] = L.switch_envelope(gT['housing_yz'], gT['housing_half_x'], gT['nub_yz'], gT['nub_half_x'])
    seat = P.Z_BACK + P.M2_HEAD_CB_DEPTH                                              # counterbore floor in the lid (Rev K)
    for name, (x, y) in (('screw_H3', fps['H3']['cad'][:2]), ('screw_H4', fps['H4']['cad'][:2]), ('screw_top', P.TOP_SCREW)):
        M[name] = L.tess(L.socket_head_cq(x, y, seat, length=P.SCREW_L), 0.03, 0.35)   # ISO 4762 (Ian's), since 2026-10-13
    extras = {}
    if b == 'std':
        import compare
        extras.update(compare.meshes())
        extras['dummy_pcba'] = stl('pcba-dummy')
    # instanced nodes are modelled at X = 0
    for n in C.INSTANCED:
        if n not in M:
            continue
        lo, hi = M[n].bounds
        assert abs(lo[0] + hi[0]) < 1.0, (n, lo, hi)
    arrays = {}
    for n, m in {**M, **{'X:' + k: v for k, v in extras.items()}}.items():
        arrays['v|' + n] = np.asarray(m.vertices, dtype=np.float64)
        arrays['f|' + n] = np.asarray(m.faces, dtype=np.int64)
    np.savez_compressed(work / 'meshes.npz', **arrays)
    log(b, 'meshes saved', len(M), 'extras', len(extras))

    # ---- geometry the page uses -------------------------------------------------------------------------
    kx = {r: round(keys.key_x(r), 4) for r in P.KEY_REFS}
    xs = kx['SW8'] if KEYS else 23.4975                 # chinless: where SW8 would be (the keys preset's cut)
    shell = trimesh.util.concatenate([M['tub'], M['lid']] + [M[f'skey_{r}'] for r in side_refs])
    lo, hi = shell.bounds
    envelope = [round(float(v), 2) for v in (lo[0], hi[0], lo[1], hi[1], lo[2], hi[2])]
    u = body.usb()
    uf = tub.usb_features()
    rs = hw.switch_plunger(hw.RESET)
    t_by = {t['ref']: t for t in tabs}
    t10, t1 = t_by['SW10'], t_by['SW1']

    # ---- drawings (Rev K's 22, re-cut from this build's meshes, plus the crank key section) -------------
    hm = L.HwMesh(hw)
    pcb = hm('PCB')
    D = []
    dw = lambda *a, **k: D.append(L.drawing(*a, **k))                     # noqa: E731
    at = lambda m, dx: L.moved(m, dx)                                      # noqa: E731
    if KEYS:                                            # the bottom-key section (none on the chinless build)
        swT_b, swT_n = at(M['sw_T_body'], xs), at(M['sw_T_nub'], xs)
        cM, cT = at(M['crank_M'], xs), at(M['crank_T'], xs)
        ring_x = round(xs - (P.SLOT[1] + 0.6), 4)                              # a closed rail ring between SW9 and SW8
        hook_x = round(xs + sum(P.KEY_HOOK['dx']) / 2, 4)                      # the +X hook's centre (test 2's hook keys)
        dw('key', 'x', xs, [-9.8, 4.2, -7.4, 8.8], [
            ('tub', 'case', M['tub']), ('lid', 'case2', M['lid']), ('pcb', 'pcb', pcb),
            ('sw_M', 'part', hm('SW8', 'body')), ('nub_M', 'nub', hm('SW8', 'nub')),
            ('sw_T', 'part', swT_b), ('nub_T', 'nub', swT_n), *disp,
            ('key', 'key', M['key_SW8']), ('crank_M', 'crank', cM), ('crank_T', 'crank', cT), ('rod', 'rod', M['rod'])],
            beyond=[('cheek', 'crank', cM, xs - 4.5), ('rail', 'case', M['tub'], ring_x),
                    ('hook', 'key', M['key_SW8'], hook_x)],
            notes={'ref': 'SW8', 'x': xs, 'ring_x': ring_x, 'cheek_x': round(xs - 4.5, 4), 'hook_x': hook_x,
                   'rod_yz': list(P.ROD_YZ), 'switch_M': 'board STEP (MJTP1117)', 'switch_T': 'TS365ZJ envelope, nominal plunger (sc_contract.SWITCH_GEOM)'})
    fz = t10['face'][2]
    dw('tab_plan', 'z', fz, [51.0, 67.6, 85.5, 111.0], [
        ('tub', 'case', M['tub']), ('lid', 'case2', M['lid']), ('tab', 'tab', M['skey_SW10']),
        ('sw', 'part', hm('SW10', 'body')), ('nub', 'nub', hm('SW10', 'nub'))], notes={'ref': 'SW10'})
    dw('key_side', 'x', P.X1 - 0.5, [42.4, 73.2, -8.7, 3.5], [
        ('tub', 'case', M['tub']), ('lid', 'case2', M['lid']), ('tab', 'tab', M['skey_SW1'])], notes={'ref': 'SW1'})
    dw('tab_elev', 'y', t10['face'][1], [50.5, 70.2, -7.4, 7.4], [
        ('tub', 'case', M['tub']), ('tab', 'tab', M['skey_SW10']), ('lid', 'case2', M['lid']), ('pcb', 'pcb', pcb),
        ('sw', 'part', hm('SW10', 'body')), ('nub', 'nub', hm('SW10', 'nub')), *disp, ('midplate', 'plate', M['midplate'])],
        notes={'ref': 'SW10'})
    dr = midplate.detents()[2][0]
    dyc = sum(dr['bump_y']) / 2
    dw('detent', 'y', dyc, [59.4, 62.8, 0.6, 4.6], [
        ('tub', 'case', M['tub']), ('midplate', 'plate', M['midplate']), *disp, ('pcb', 'pcb', pcb)], notes={'which': 'right, bottom'})
    dw('detent_plan', 'z', 2.5, [55.6, 63.4, 13.9, 22.1], [('tub', 'case', M['tub']), ('midplate', 'plate', M['midplate'])])
    dw('usb', 'y', u['yc'], [53.6, 69.6, -7.4, 4.2], [
        ('tub', 'case', M['tub']), ('lid', 'case2', M['lid']), ('pcb', 'pcb', pcb), ('j1', 'metal', hm('J1')),
        ('midplate', 'plate', M['midplate'])], notes={'ref': 'J1'})
    dw('usb_plan', 'z', u['zc'], [53.0, 68.2, 31.5, 51.1], [
        ('tub', 'case', M['tub']), ('lid', 'case2', M['lid']), ('j1', 'metal', hm('J1')), ('pcb', 'pcb', pcb),
        ('skey', 'tab', M['skey_SW1'])], notes={'ref': 'J1', 'skey': 'SW1'})
    dw('reset', 'y', rs['face'][1], [46.0, 67.8, -7.4, 7.4], [
        ('tub', 'case', M['tub']), ('lid', 'case2', M['lid']), ('pcb', 'pcb', pcb),
        ('sw', 'part', hm(hw.RESET, 'body')), ('nub', 'nub', hm(hw.RESET, 'nub')), *disp, ('midplate', 'plate', M['midplate'])],
        notes={'ref': hw.RESET})
    dw('stack', 'x', 14.0, [60.5, 79.5, -0.6, 7.0], [
        ('tub', 'case', M['tub']), *disp, ('midplate', 'plate', M['midplate']), ('pcb', 'pcb', pcb)])
    dw('bezel', 'y', 60.0, [-4.1, 3.9, 1.3, 6.5], [
        ('tub', 'case', M['tub']), *disp, ('midplate', 'plate', M['midplate']), ('pcb', 'pcb', pcb)])
    rib = [('ribbon', 'ribbon', M['ribbon_main'])]
    rib_beyond = [] if LS else [('touch_beyond', 'ribbon', M['ribbon_touch'], 49.0)]
    dw('ribbon', 'x', 28.0, [-3.0, 25.5, -6.0, 6.4], [
        ('tub', 'case', M['tub']), ('lid', 'case2', M['lid']), ('pcb', 'pcb', pcb), ('j2', 'part', hm('J2')),
        *disp, ('midplate', 'plate', M['midplate']), *([('key', 'key', M['key_SW8'])] if KEYS else []), *rib],
        beyond=rib_beyond,
        notes={'ribbon': 'main', 'connector': 'J2'})
    dw('battery', 'x', 18.8, [60.0, 117.0, -7.4, 7.4], [
        ('tub', 'case', M['tub']), ('lid', 'case2', M['lid']), ('cell', 'cell', M['battery_cell']),
        ('midplate', 'plate', M['midplate']), *disp, ('pcb', 'pcb', pcb), ('j7', 'part', hm('J7'))], notes={'card': 'J7'})
    dw('fence', 'z', 1.5, [-5.0, 52.0, 60.0, 116.2], [
        ('tub', 'case', M['tub']), ('pcb', 'pcb', pcb), ('cell', 'cell', M['battery_cell']),
        ('midplate', 'plate', M['midplate']), ('j5', 'part', hm('J5'))],
        beyond=[('leads', 'lead', M['battery_leads'], -2.6), ('plug', 'part', M['battery_plug'], -2.6),
                ('caps', 'plate', M['midplate'], -4.4), ('j7', 'part', hm('J7'), -1.0)])
    dw('bay_lip', 'y', 91.5, [-2.2, 41.4, -6.9, 3.4], [
        ('tub', 'case', M['tub']), ('lid', 'case2', M['lid']), ('cell', 'cell', M['battery_cell']),
        ('midplate', 'plate', M['midplate']), *disp, ('pcb', 'pcb', pcb)])
    h3, h2 = fps['H3']['cad'], fps['H2']['cad']
    dw('clamp', 'y', h3[1], [-4.2, 11.1, -7.4, 7.4], [
        ('tub', 'case', M['tub']), ('lid', 'case2', M['lid']), ('pcb', 'pcb', pcb), ('screw', 'metal', M['screw_H3'])],
        notes={'hole': 'H3'})
    py = h2[1] + P.BOARD_SNAP['slot'] / 2 + 0.25       # beside the snap post's slot (as 3.68), so its fingers are cut
    dw('pin', 'y', py, [4.0, 17.0, -7.4, 7.4], [
        ('tub', 'case', M['tub']), ('lid', 'case2', M['lid']), ('pcb', 'pcb', pcb),
        ('midplate', 'plate', M['midplate']), *disp], notes={'hole': 'H2', 'hole_y': h2[1]})
    dw('top', 'x', P.TOP_SCREW[0], [104.0, 117.0, -7.4, 7.4], [
        ('tub', 'case', M['tub']), ('lid', 'case2', M['lid']), ('pcb', 'pcb', pcb), ('screw', 'metal', M['screw_top']),
        ('j6', 'part', hm('J6')), *disp, ('midplate', 'plate', M['midplate'])])
    jl = [('tub', 'case', M['tub']), ('lid', 'case2', M['lid']), ('pcb', 'pcb', pcb)]
    dw('joint_tongue', 'y', 10.0, [-4.8, 6.4, -7.2, 1.2], jl)
    dw('joint_at_tab', 'y', 99.0, [58.8, 65.6, -7.2, 2.6], jl + [('tab', 'tab', M['skey_SW10'])], notes={'ref': 'SW10'})
    dw('joint_top', 'x', 20.0, [106.7, 116.3, -7.2, 0.9], jl + [('cell', 'cell', M['battery_cell'])])
    dw('joint_latch', 'y', P.SNAPS['right'][2], [55.6, 65.9, -7.2, 3.3],
       jl + [('tab', 'tab', M['skey_SW1']), ('midplate', 'plate', M['midplate'])], notes={'ref': 'SW1', 'wall': 'right'})
    if LS:
        # the strip as built (refs: the drawn position), with the plain panel's layers; strip_sections.py's cuts
        sf = {k: L.tess(v, 0.01, 0.1) for k, v in refs.strip_front().items()}
        st, _ = refs.strip_tail('nominal')
        sl = [('strip', 'strip', sf['strip_bar']), ('led', 'led', sf['strip_leds']), ('copper', 'metal', sf['strip_copper'])]
        dw('strip_led', 'y', 49.7, [-4.5, 4.0, 1.8, 6.3], [
            ('tub', 'case', M['tub']), ('lid', 'case2', M['lid']), ('midplate', 'plate', M['midplate']), *disp, *sl],
            notes={'led': 'D4', 'led_top': P.STRIP_LED_TOP, 'ceiling': P.STRIP_CEIL['z'], 'window_x': round(P.WIN_X0, 3),
                   'flex_top': P.STRIP_FLEX_TOP, 'plain_front': P.PLAIN_FRONT})
        dw('strip_holddown', 'y', 45.25, [-4.5, 4.0, 1.8, 6.3], [
            ('tub', 'case', M['tub']), ('midplate', 'plate', M['midplate']), *disp, *sl],
            notes={'pad_z': P.STRIP_HOLD['z'], 'flex_top': P.STRIP_FLEX_TOP})
        dw('strip_neck', 'x', 11.0, [-2.5, 12.5, -1.2, 6.3], [
            ('tub', 'case', M['tub']), ('midplate', 'plate', M['midplate']), ('pcb', 'pcb', pcb), *disp,
            ('tail', 'strip', st['strip_tail']), ('diodes', 'part', st['strip_diodes']), ('fpc', 'ribbon', M['ribbon_main'])],
            notes={'glass_edge_y': hw.PANEL_Y0})
    for d in D:
        assert d['layers'], d['name']
    log(b, 'drawings', len(D))

    # ---- kinematics: the geometry, independent rest rows, mechanics mapped ---------------------------------
    if KEYS:
        KF, KH, KO = mech['key_forces'], mech['key_hooks'], mech['key_overpress']
        bk = json.loads((OB / 'bottom-keys.json').read_text())
        SWM, SWT = sw['MJTP'], sw['TS365']
        K = {
            'refs': list(P.KEY_REFS), 'x': kx, 'draw_ref': C.DRAW_REF,
            'rod': {'yz': list(P.ROD_YZ), 'd': P.ROD_D, 'cut': P.ROD_CUT, 'gate': 'printed side gate',
                    'hole_d': P.ROD_HOLE_D, 'stops': list(P.ROD_STOPS), 'ream': P.CRANK_REAM, 'bore_d': P.CRANK_BORE_D},
            'axis': [1, 0, 0], 'theta_built': 0.0,
            'pad': {'c': list(P.CRANK_PAD['c']), 'r': P.CRANK_PAD['r']},
            'nose': {'r': P.CRANK_NOSE_R, 'c': {'M': list(P.CRANK_NOSE['M']), 'T': list(P.CRANK_NOSE['T'])}},
            'switches': {
                'M': {'part': 'MJTP1117', 'crank': 'crank-M', 'label': 'APEM MJTP1117 boards', **C.switch_geom('M'),
                      'travel': {'click': SWM['travel'][0], 'bottom': SWM['travel'][1]}, 'force_N': list(SWM['force'])},
                # nominal plunger as nub_z / nub_yz, keys.SWITCH's worst case as nub_z_worst (checked above)
                'T': {'part': 'TS365ZJ', 'crank': 'crank-T', 'label': 'SHOU HAN TS365ZJ (every JLC board)', **C.switch_geom('T'),
                      'travel': {'click': SWT['travel'][0], 'bottom': SWT['travel'][1]}, 'force_N': list(SWT['force'])}},
            'default_variant': 'T',
        }
        K['derived'] = {v: C.derive(K, v) for v in C.VARIANTS}
        rows = []
        for k, v in bk['static'].items():
            m = re.match(r'^(MJTP|TS365) crank-([MT]) delta ([+-]\d+\.\d+)$', k)
            if not m or {'MJTP': 'M', 'TS365': 'T'}[m.group(1)] != m.group(2):
                continue
            d = float(m.group(3))
            rows.append({'variant': m.group(2), 'face_dy': round(-d, 3) + 0.0, 'theta': v['theta'],
                         'key_dz': round(-v['key_lift'], 4) + 0.0,
                         'source': f'bottom-keys.json static "{k}" (delta moves the board -Y: face_dy = -delta)'})
        K['rest_rows'] = rows
        ff = KF['finger_force_N']
        # sc_contract's one table shape: {"MJTP 1.27 mu 0.3": {"y -6.20": N}} -> {"MJTP 1.27": {"mu_0.3": [N per press_ys]}}
        frows = []
        for k, row in ff.items():
            m = re.match(r'^(MJTP|TS365) (\d+\.\d+) mu (\d+(?:\.\d+)?)$', k)
            assert m, k
            for yk, val in row.items():
                frows.append((m.group(1), float(m.group(2)), float(m.group(3)), float(yk.split()[1]), val))
        ftab, fys = C.force_table(frows)
        assert all(None not in v for r in ftab.values() for v in r.values()), ftab
        K['forces'] = {'lever': {k: KF['lever'][k] for k in ('input_arm', 'output_arm', 'ratio')},
                       'ideal_key_over_switch': KF['lever']['ideal_key_over_switch'],
                       'finger_N': {'M': [ff['MJTP 1.27 mu 0.3']['y -6.20'], ff['MJTP 1.86 mu 0.3']['y -6.20']],
                                    'T': [ff['TS365 1.96 mu 0.3']['y -6.20'], ff['TS365 2.94 mu 0.3']['y -6.20']]},
                       'press_y': -6.2, 'mu': 0.3, 'table': ftab, 'press_ys': fys, 'pressable': KF['pressable'],
                       'guide_length_mm': KF['guide_length_mm'], 'rev_k_rocker_N_at_1.86': KF['rev_k_rocker_N_at_1.86'],
                       'source': 'mechanics.json key_forces'}
        # the hook keys (test 2): face down a key drops W_OUT onto its hooks, so the first press there travels W_OUT less the
        # key's rest lift, over the TS365's tip +-0.2 and the board's +-0.2. Its highest rest is the project's own
        # (mechanics key_hooks.rest); its lowest comes from the reference kinematics (the 3.68's mechanics gives both)
        up = KH['rest']['rest_high_by_switch_mm']['TS365']
        down = C.key_down(K, C.theta_at(K, 'T', C.face(K, 'T', 0.4)))
        assert abs(-C.key_down(K, C.theta_at(K, 'T', C.face(K, 'T', -0.4))) - up) < 0.01, 'rest lift: mechanics vs reference'
        pull, grav = KH['pull'], KH['gravity']
        K['hooks'] = {'W_OUT_mm': P.KEY_W_OUT, 'hook_dx': list(P.KEY_HOOK['dx']), 'hook_h_mm': P.KEY_HOOK['h'],
                      'hook_tip_y': P.KEY_HOOK['tip'], 'hook_z_rest': list(P.KEY_HOOK_Z), 'hook_lead_mm': P.KEY_HOOK_LEAD,
                      'root_mm': P.KEY_ROOT, 'slot_dx': list(P.KEY_SLOT['dx']), 'slot_back_y': P.KEY_SLOT['back'],
                      'slot_roof_z': P.KEY_SLOT_ROOF,
                      'face_down_free_travel_mm': [round(P.KEY_W_OUT - up, 3), round(P.KEY_W_OUT + down, 3)],
                      # gravity only: the face-up net force at the key through the lever (the 3.68's key_preload does the same)
                      'rest_load_on_plunger_N': round(grav['poses']['face-up']['net_at_key_N'] * KF['lever']['ratio'], 5),
                      'key_mass_g': grav['key_g'], 'wall_behind_slot_mm': KH['wall']['layers']['mm'],
                      'above_roof_mm': KH['wall']['above_roof']['mm'], 'tilt_on_hooks_deg': KH['x_tilt']['hook_error_0.1_one_deg'],
                      'pull_out': {'pull_N': pull['pull_N'], 'bearing_mm': pull['bearing_gross_mm'],
                                   'bearing_net_mm': pull['bearing_net_mm'], 'root_shear_MPa': pull['root_shear_MPa'],
                                   'root_bending_MPa': pull['root_bending_MPa']},
                      'hooks_to_crank_min_mm': KH['crank']['hook_gap_min']['mm'],
                      'source': 'mechanics.json key_hooks; params KEY_W_OUT / KEY_HOOK / KEY_SLOT / KEY_ROOT'}
        K['rod_check'] = {'press_N': KO['press_N'], 'bending_MPa': KO['rod_bending_MPa'], 'deflection_um': KO['rod_deflection_um'],
                          'bending_soft_bearings_MPa': KO['rod_bending_soft_bearings_MPa'], 'shear_MPa': KO['rod_shear_MPa'],
                          'plunger_N': KO['plunger_N'], 'pin_N': KO['pin_N'], 'per_cheek_N': KO['per_cheek_N'],
                          'cheek_seat_bearing_MPa': KO['cheek_seat_bearing_MPa'], 'crossbar': KO['crossbar'],
                          'source': 'mechanics.json key_overpress'}
        kchecks = []
        for i, (label, (ok, det)) in enumerate(bk['verdict'].items()):
            c = {'id': f'bk{i:02d}', 'label': label, 'ok': True if ok == 'accepted' else bool(ok), 'source': 'bottom-keys.json verdict'}
            if ok == 'accepted':
                c['status'] = 'accepted'
            if det is not None:
                c['detail'] = json.dumps(det)
            kchecks.append(c)
        for sec in ('key_forces', 'key_hooks', 'key_fit', 'key_overpress', 'key_sweep', 'rod_gate'):   # rod_gate: the gate's loads
            for j, (label, ok) in enumerate(mech[sec].get('checks', {}).items()):
                kchecks.append({'id': f'{sec}{j:02d}', 'label': label, 'ok': True if ok == 'accepted' else bool(ok),
                                'source': f'mechanics.json {sec}.checks', **({'status': 'accepted'} if ok == 'accepted' else {})})
        K['checks'] = kchecks
        K['instances'] = {'crank': {'M': 'crank_M', 'T': 'crank_T'}, 'switch': {'T': ['sw_T_body', 'sw_T_nub'], 'M': 'board'}}
        # an independent cross-check: mechanics.json key_forces.travel (the project's own kinematics, per board delta)
        trav = []
        for k, v in KF['travel'].items():
            m = re.match(r'^(MJTP|TS365) delta ([+-]\d+\.\d+)$', k)
            var = {'MJTP': 'M', 'TS365': 'T'}[m.group(1)]
            dd = C.derive(K, var, -float(m.group(2)))
            trav.append({'row': k, 'variant': var, 'face_dy': -float(m.group(2)),
                         'mech': [v['rest_theta'], v['click_theta'], v['bottom_theta'], v['click_key_mm'], v['bottom_key_mm']],
                         'ref': [dd['theta_rest'], dd['theta_click'], dd['theta_bottom'], dd['key_click'], dd['key_bottom']]})

    else:                                           # chinless: no bottom keys, no kinematics
        K, kchecks, trav = None, [], []

    # ---- controls ----------------------------------------------------------------------------------------
    controls = [{'id': r, 'label': f'Bottom key {i + 1} ({r})', 'kind': 'crank', 'ref': r, 'node': f'key_{r}',
                 'crank': f'crank_{r}', 'plunger': f'nub_{r}', 'pivot': [kx[r], P.ROD_YZ[0], P.ROD_YZ[1]], 'axis': [1, 0, 0]}
                for i, r in enumerate(P.KEY_REFS)]
    for t in tabs:
        root_x = round((P.X1 if t['side'] > 0 else P.X0) - t['side'] * P.TAB_T / 2, 3)
        arm = round(abs(t['face'][1] - t['flex_root']), 3)
        controls.append({'id': t['ref'], 'label': f"Side key {t['ref']} ({'right' if t['side'] > 0 else 'left'})",
                         'kind': 'flexure', 'ref': t['ref'], 'node': f"skey_{t['ref']}", 'plunger': f"nub_{t['ref']}",
                         'plunger_axis': [-t['side'], 0, 0], 'pivot': [root_x, t['flex_root'], 0.0], 'axis': [0, 0, 1],
                         'sign': int(t['side'] * math.copysign(1, t['y_free'] - t['flex_root'])), 'length': arm,
                         'gap': t['gap'], 'click_travel': round(t['gap'] + 0.25, 3), 'max_travel': round(t['gap'] + 0.45, 3)})
    rx, ry, rz = rs['face']
    controls.append({'id': hw.RESET, 'label': 'Reset (pin)', 'kind': 'pin', 'ref': hw.RESET, 'plunger': f'nub_{hw.RESET}',
                     'plunger_axis': [-rs['axis'][0], -rs['axis'][1], 0], 'pin_from': [round(P.X1 + 10.0, 3), ry, rz],
                     'pin_to': [rx, ry, rz], 'click_travel': 0.25, 'max_travel': 0.45})
    spare = P.USB_PLUG_SPARE
    seat_face = max(uf['face_x'], u['mouth_x'] + spare)                # the overmold stops on the floor (Rev K)
    tip_in = seat_face - (6.20 + spare)
    controls.append({'id': 'usb', 'label': 'USB-C plug', 'kind': 'plug', 'axis': [-1, 0, 0],
                     'from': [round(tip_in + 9.0, 3), u['yc'], u['zc']], 'to': [round(tip_in, 3), u['yc'], u['zc']],
                     'insert_mm': 9.0, 'shell_len': round(6.20 + spare, 3), 'seat_face_x': round(seat_face, 3),
                     'overmold': [11.0, 5.6]})

    # ---- presets (Rev K's 18 at this build's numbers, + strip, zstack) -----------------------------------
    J = joint.summary()
    lat_y = P.SNAPS['right'][2]
    PR = {
        'home': dict(cam=[104, -158, 142], tgt=[30, 50, -1], fit=True, tag='Assembled',
                     cap='<b>Assembled.</b> Screen side up; the four bottom keys sit in the chin below the display.'),
        'assembly': dict(cam=[175, -120, -35], tgt=[30, 52, -38], fit=True, tag='Assembly',
                         cap='<b>Assembly.</b> Parts enter the tub from behind, in this order.'),
        'keys': dict(cam=[xs + 58, -40, 26], tgt=[xs, -4.0, 0.5], sec=['x', xs, False],
                     focus=['keys', 'rod', 'tub', 'pcba', 'lid'], press='SW8', highlight=['key_*', 'crank_*'], tag='Bottom keys',
                     cap=H('<b>Bottom keys.</b> Cut through SW8. The key slides down in the chin and presses the crank\u2019s pad; '
                           'the crank turns on the rod and its nose pushes the switch plunger. Drag \u201cPress\u201d.')),
        'tabs': dict(cam=[96, 52, 42], tgt=[61, 94, -2], sec=['z', t10['face'][2], False], focus=['tub', 'pcba', 'lid'],
                     press=True, highlight=['skey_*'], tag='Side keys',
                     cap=H('<b>Side keys.</b> Cut at plunger height. Each button (highlighted) is part of the lid: its wall, '
                           'cut free, bends from its root, and from the pad on it rises into a slot in the tub. Drag \u201cPress\u201d.')),
        'keylid': dict(cam=[208, 28, 66], tgt=[58, 54, 1.5], fit=True, show=['lid'], press=True, highlight=['skey_*'],
                       tag='Side keys on the lid',
                       cap='<b>The lid on its own.</b> The five side keys (highlighted) stand on its back face, the face it '
                           'prints on, and rise past the parting line: every layer of them sits on the one before.'),
        'usb': dict(cam=[125, 12, 22], tgt=[62, round(u['yc'], 2), -2], focus=['tub', 'lid', 'pcba'], press='usb', tag='USB-C',
                    cap=H('<b>USB-C.</b> A divot for the plug\u2019s overmold, floored by the tub itself: a 0.5 mm wall round the '
                          'port, 0.62 mm in front of J1\u2019s mouth.')),
        'reset': dict(cam=[118, 6, 16], tgt=[61, round(ry, 2), round(rz, 2)], focus=['tub', 'lid', 'pcba'], press=hw.RESET,
                      tag='Reset', cap='<b>Reset.</b> The countersunk pinhole sits 11 mm below the port, straight onto SW11.'),
        'stack': dict(cam=[-34, 44, 22], tgt=[-1, 60, 3.5], sec=['y', 60.0, True], focus=['midplate', 'display', 'pcba', 'tub'],
                      tag='Screen stack',
                      cap=('<b>Screen stack.</b> Cut at y = 60 across the left bezel: the springs keep the plain panel\'s '
                           'front on the tub\'s stops, and the ceiling over the left border clears the strip\'s LEDs.' if LS else
                           '<b>Screen stack.</b> Cut at y = 60 across the left bezel: the springs keep the touch film on the lip, '
                           'and the pocket steps in above the glass.')),
        'detent': dict(cam=[63.5, 15.5, 34], tgt=[60.4, 18.6, 2.5], up=[0, 1, 0], sec=['z', 2.5, False],
                       focus=['midplate', 'tub'], show=['tub', 'midplate', 'pcba'], tag='Stack detent',
                       cap=H('<b>Stack detent.</b> Cut through the midplate: a strip of its edge, freed by a slot, carries a bump '
                             'that clicks into a pocket in the tub\u2019s wall.')),
        'ribbons': dict(cam=[28 + 62, -30, 14], tgt=[28, 9, -0.5], sec=['x', 28.0, False],
                        focus=['display', 'pcba', 'tub', 'midplate', 'lid'], tag='Ribbons',
                        cap=('<b>Display ribbon.</b> Cut through the EPD FPC: over the glass edge, down the board slot, along '
                             'the back into J2.' if LS else '<b>Display ribbons.</b> Cut through the main ribbon: over the glass '
                             'edge, down the board slot, along the back into J2.')),
        'battery': dict(cam=[20, 60, -95], tgt=[20, 97, -1], focus=['battery', 'midplate', 'pcba'], hide=['lid', 'screws'],
                        tag='Battery',
                        cap=H('<b>Battery.</b> From the back with the lid off: the cell is held in the midplate\u2019s slot by a '
                              'lip along its left edge and two snaps on its right; its lead runs past the cleats to J5, and '
                              'J7\u2019s card comes out under its bottom edge once the cell is swung out.')),
        'edges': dict(cam=[96, -52, 44], tgt=[52, 2, 1], tag='Edges',
                      cap='<b>Edges and logo.</b> 1.8 mm front and 2.0 mm back rounds, a 0.4 mm V at the parting line, and '
                          'the wordmark in the chin.'),
        'close': dict(cam=[36, -110, -58], tgt=[30, 20, -4], sec=['y', 3.0, True], focus=['screws', 'lid', 'tub', 'pcba', 'rod'],
                      highlight=['screw_*', 'gate'], tag='Fasteners',
                      cap='<b>Fasteners.</b> Cut through H3/H4: each screw clamps the board between a lid boss and a tub '
                          'boss. The printed gate in the left wall stops the rod; the lid\'s rim closes over it.'),
        'joint': dict(cam=[-42, -78, 104], tgt=[30, 56, -5], show=['lid'], tag='Tub-to-lid joint',
                      cap=H('<b>Tub-to-lid joint.</b> The tub\u2019s wall keeps an inner sliver behind every side key, and that '
                            'sliver runs on below the parting plane as a tongue into a closed groove in the lid\u2019s rim; '
                            f'{J["latch_count"]} tall latch arms stand up inside it.')),
        'latch': dict(cam=[71, 31, -3.5], tgt=[61.4, lat_y, -1.4], sec=['y', lat_y, True], show=['tub', 'lid', 'pcba', 'midplate'],
                      focus=['tub', 'lid'], tag='Latch',
                      cap=H(f'<b>Latch.</b> One of {J["latch_count"]}, over SW1\u2019s key. The arm reaches up past the key\u2019s '
                            'slot, so its barb catches in a pocket with solid wall behind it.')),
        'compare': dict(cam=[32, -265, 250], tgt=[32, 54, -2], fit=True,
                        show=['tub', 'keys', 'display', 'lid', 'screws', 'compare'] + (['strip'] if LS else []), tag='Comparison',
                        cap='<b>Side by side.</b> Xteink X4 (left; reference model by Zorian22, CC BY-NC-SA), this case, '
                            'and the X4 in its retro case (right): front faces level, bottom edges on one line.'),
        'back': dict(cam=[58, 12, -122], tgt=[30, 53.6, -6.7], up=[0, 1, 0], fit=True, tag='Back',
                     cap=H('<b>Back.</b> The site\u2019s book icon, 30 mm wide and 0.4 mm deep, centred on the lid; the grip '
                           'grooves run along the bottom edge.')),
        'dummy': dict(cam=[96, -46, -118], tgt=[30, 54, -1], fit=True, show=['dummy'], tag='PCBA dummy',
                      cap='<b>PCBA dummy.</b> Component hulls fused to a 1.6 mm board, legs trimmed flush. All ten switch sites '
                          'are open for real switches inside low walls, the module stops at the antenna notch, J1 is a '
                          'printable socket a cable plugs into, and the microSD socket is in.'),
        'strip': dict(cam=[-96, -92, 150], tgt=[26, 48, 2], fit=True, focus=['strip', 'display', 'tub'], tag='Light strip',
                      cap=('<b>Light strip.</b> The bar lies on the plain panel\'s left border under the bezel; the tail wraps '
                           'the bottom glass edge, goes through the board\'s slot and plugs into J3.' if LS else
                           '<b>Light strip.</b> The light strip needs the light-strip build: its own tub and the plain '
                           'GDEY0426T82 panel.')),
        'zstack': dict(cam=[30 + 78, 40, 14], tgt=[30, 58, -0.4], sec=['x', 30.0, False], fit=True,
                       focus=['tub', 'display', 'midplate', 'pcba', 'battery', 'lid'], tag='Front to back',
                       cap='<b>Front to back.</b> Cut at x = 30: skin, panel, midplate, the air to the board, the board, the '
                           'parts behind it, and the lid.'),
    }
    if CL:
        PR['home']['cap'] = ('<b>Assembled.</b> Screen side up. The chinless build: no bottom keys, so the case ends just '
                             'below the board, 117.4 mm tall instead of 125.0.')
        PR['keys'] = dict(cam=[xs + 58, -36, 26], tgt=[xs, 1.0, 0.5], sec=['x', xs, False], focus=['tub', 'pcba', 'lid'],
                          tag='No bottom keys',
                          cap=H('<b>No bottom keys.</b> Cut where SW8 sits on the other builds: this board has SW9, SW8, '
                                'SW3 and SW2 left off, and the chin wall stands 0.6 mm below its bottom edge. Touch '
                                'and the five side keys do the rest.'))
        PR['close'] = dict(cam=[36, -110, -58], tgt=[30, 20, -4], sec=['y', 3.0, True], focus=['screws', 'lid', 'tub', 'pcba'],
                           highlight=['screw_*'], tag='Fasteners',
                           cap='<b>Fasteners.</b> Cut through H3/H4: each screw clamps the board between a lid boss and a '
                               'tub boss; on the chinless case both lid bosses run into the chin wall.')
        PR['edges']['cap'] = ('<b>Edges and logo.</b> 1.8 mm front and 2.0 mm back rounds, a 0.4 mm V at the parting '
                              'line, and the wordmark centred on the face below the window.')
    if LC:
        PR['home']['cap'] = ('<b>Assembled.</b> Screen side up. The light-strip chinless build: the plain panel with the '
                             'light strip and no bottom keys, so the case ends just below the board, 117.4 mm tall '
                             'instead of 125.0.')
        PR['keys']['cap'] = H('<b>No bottom keys.</b> Cut where SW8 sits on the keyed builds: this board has SW9, SW8, '
                              'SW3 and SW2 left off, and the chin wall stands 0.6 mm below its bottom edge. The plain '
                              'panel has no touch: the four page keys and power do the rest.')
    presets = {k: asciify(v) for k, v in PR.items()}

    # ---- explode, assembly -------------------------------------------------------------------------------
    order = ['tub', 'display'] + (['strip'] if LS else []) + ['midplate', 'battery'] + (['keys', 'rod'] if KEYS else []) \
        + ['pcba', 'lid', 'screws']
    offs = {'tub': 0, 'display': -12, 'strip': -12, 'midplate': -24, 'battery': -34, 'keys': -44, 'rod': -52,
            'pcba': -60, 'lid': -74, 'screws': -88}
    stext = {
        'tub': 'Tub face down: the bezel lip, the key openings, the rail the cranks hang in, the slots the side keys '
               'rise into and the USB-C divot are all part of it.',
        'display': ('The plain panel, with the light strip taped on its left border, into the bezel pocket; its PS face '
                    'on the stops.' if LS else 'Display into the bezel pocket, glass against the lip.'),
        'strip': 'The strip goes in with the panel: the bar on its left border, the tail round the bottom glass edge.',
        'midplate': 'Midplate onto the back of the display; it clicks in at its four detents.',
        'battery': H('Battery in the midplate\u2019s slot: left edge under the lip, right side down past the snaps.'),
        'keys': 'The four keys from inside, cap first, hooks in their slots, until both hooks stop under the skin.',
        'rod': 'The cranks drop into their slots; the 1.75 mm filament rod slides through the rail and the cranks from '
               'the -X wall, and the printed gate drops into its slot and cams it home.',
        'pcba': H('PCBA in: the plungers pass the cranks\u2019 noses (the cranks hang clear), and it clicks onto the '
                  'midplate\u2019s three snap posts.'),
        'lid': f'Lid on, with the five side keys that are part of it: they slide up into their slots in the tub; the '
               f'tongue drops into the groove, {J["latch_count"]} latches click, posts take the board.',
        'screws': H('Three M2\u00d710 socket head caps from the back.'),
    }
    if CL:
        stext['tub'] = ('Tub face down: the bezel lip, the slots the side keys rise into and the USB-C divot are all part '
                        'of it; the chin is a plain wall just below the board.')
        stext['pcba'] = 'PCBA in (SW9, SW8, SW3 and SW2 not fitted): it clicks onto the midplate\'s three snap posts.'
    explode = {'order': order, 'offsets': {g: offs[g] for g in order}, 'steps': [asciify(stext[g]) for g in order],
               'done': '<b>Assembled.</b> Twelve printed parts, a filament rod, three screws.' if KEYS else
               '<b>Assembled.</b> Three printed parts and three screws.'}
    cam_mm = P.GATE['web'] + P.GATE['flange']                       # the bevel's cam: the rod's last move home
    A = [('coupon', 'Gate coupon, and the optional chin coupon', 'Print <code>coupon-gate</code> with a gate (plate 3 of '
          'the plate file has them): the gate slides in, cams a 20 mm piece of rod home and lifts out with a paperclip. '
          'Optional, a 15-minute fit check of the hook keys: <code>coupon-chin</code> (the chin round one key opening, '
          'with its two hook slots) and one <code>key-426</code>. The key slides up its slots from inside and stops '
          'level, 2.4 mm proud; nothing is chosen from it.', ['keys'], 'keys'),
         ('prep', 'Rod and crank bores', f'Straighten, cut ({P.ROD_CUT:.2f} &plusmn;0.2 mm), taper (tail square) and check '
          'the 1.75 mm rod; ream the eight crank bores with a 1.9 mm drill. Print two gates.', ['rod'], 'keys'),
         ('tub', 'Tub face down', 'On a soft cloth.', ['tub'], 'assembly')]
    if LS:
        A.append(('strip', 'Light strip on the panel', 'Tape the bar 0.1 mm inside the left glass edge, Kapton the slot '
                  'edges' + ('' if CL else ' and SW9&rsquo;s trimmed lead') + ', wrap the neck round the bottom glass '
                  'edge, down the slot and into J3 (the light-strip card has every step).', ['strip', 'display'], 'strip'))
    A += [('display', 'Display', 'Straight down into the pocket, glass against the lip' + (' (the plain panel&rsquo;s PS face on the '
           'three stops)' if LS else ', the three ribbons standing up through the opening') + '.', ['display'], 'stack'),
          ('midplate', 'Midplate and battery', 'Battery into the midplate&rsquo;s slot (left edge under the lip, right side '
           'down past the snaps), then the midplate onto the back of the display: it clicks in at its four detents.',
           ['midplate', 'battery'], 'detent'),
          ('keys', 'Bottom keys', 'Tub face down on the cloth, so the caps can hang out, and <b>keep it face down until the '
           'board is in</b>: turned over sooner, the keys sink (or fall in, before the rod); face down again, they come '
           'back. Each key from inside, cap first, its two hooks in the two slots of its opening (it fits one way round), '
           'and let it slide out until both hooks stop: it stands 2.4 mm proud and level. Keys go before the cranks.',
           ['keys'], 'keys'),
          ('cranks', 'Cranks', 'Drop each crank in from the open back, cheeks into their slots, pad toward the face, and let '
           'go: it comes to rest on its key, every crank at the same angle; don&rsquo;t hold it, the rod&rsquo;s tapered '
           'tip picks it up. Crank-T for TS365ZJ boards (every JLC board), crank-M for MJTP1117.', ['rod'], 'keys'),
          ('rod', 'Rod', 'Tub still face down. From the left side, lay the tapered end in the channel at the bottom of the '
           'slot beside the chin and push it straight in (hole, rings, four cranks) until its square tail is flush with the '
           'case side or just inside it. Go straight on to the gate: until it is in, only friction holds the rod.',
           ['rod'], 'keys'),
          ('gate', 'Gate', 'Drop the gate into the slot from the open back, bevel down, small hole outward, and press its '
           f'top level with the rim: its bevel pushes the rod the last {cam_mm:g} mm to its stop. If it stops proud, lift it '
           'out, push the tail a little further in and press again. Its web fills the opening in the case side, flush, '
           'with the small hole showing. From here the rod and cranks stay put however the tub is tilted, as long as its '
           'back never faces down.', ['rod'], 'close'),
          ('pcba', 'PCBA', 'Tails through the board slot into J2' + ('' if LS else '/J3/J4') + (', the strip&rsquo;s tail into J3'
           if LS else '') + '; press the board onto the three snap posts until it clicks. Let the cranks hang: the plungers '
           'pass their noses. Plug the battery into J5 and wind the spare lead round the cleats.', ['pcba'], 'battery'),
          ('lid', 'Lid', f'Each side key slides up its slot, the tongue drops into the groove, four posts take the board, '
           f'{J["latch_count"]} latches click. The lid&rsquo;s rim closes over the gate: if the case side shows an open '
           'slot instead of the gate, the gate is missing and the rod would walk out.', ['lid'], 'joint'),
          ('screws', 'Screws', 'Three M2 &times; 10 socket head caps from the back (a pan head also fits).', ['screws'], 'close'),
          ('set', 'Turn it over', 'Face up, each key settles onto its crank and the crank onto its switch (about 1.35 mm '
           'proud); a tap settles them. Face down they drop 1 mm back onto their hooks.', ['keys'], 'keys')]
    if CL:
        A = [a for a in A if a[0] not in ('coupon', 'prep', 'keys', 'cranks', 'rod', 'gate', 'set')]
        fix = {'pcba': ('Tails through the board slot into J2, the strip&rsquo;s tail into J3' if LS else
                        'Tails through the board slot into J2/J3/J4') + '; press the board (SW9, SW8, SW3 and SW2 not '
                       'fitted) onto the three snap posts until it clicks. Plug the battery into J5 and wind the spare lead '
                       'round the cleats.',
               'lid': f'The chinless lid: each side key slides up its slot, the tongue drops into the groove, the posts take '
                      f'the board, {J["latch_count"]} latches click.'}
        A = [(i, t, fix.get(i, x), g, 'battery' if i == 'pcba' else p) for i, t, x, g, p in A]
    assembly = [{'id': i, 'title': t, 'text': x, 'groups': g, 'preset': p} for i, t, x, g, p in A]

    # ---- checks ------------------------------------------------------------------------------------------
    checks = []
    inter = json.loads((OB / 'interference.json').read_text())
    snap_at = {r: fps[r]['cad'] for r in ('H1', 'H2', 'H6')}
    for i, r in enumerate(inter):
        w = r['where']
        det = f"{r['part']} x {r['with']}: {r['volume']} mm3 at x {w[0]}..{w[1]}, y {w[2]}..{w[3]}, z {w[4]}..{w[5]}"
        c = {'id': f"interference_{i:02d}", 'label': f"Interference {r['part']} x {r['with']}", 'source': 'interference.json'}
        if r.get('expected'):
            c.update(ok=True, status='expected', detail=det + ' (build.py EXPECTED: a designed contact)')
        elif (r['part'], r['with']) == ('lid', 'battery') and w[2] <= 91.0 and w[3] >= 104.0:
            c.update(ok=True, status='designed', detail=det + ': the lid\'s two battery springs (Y 91 and 104) preload the '
                     'cell model; not on build.py\'s EXPECTED list')
        elif (r['part'], r['with']) == ('midplate', 'PCB') and all(w[0] - 2 <= x <= w[1] + 2 and w[2] - 2 <= y <= w[3] + 2
                                                                    for x, y in (p[:2] for p in snap_at.values())):
            c.update(ok=True, status='designed', detail=det + ': the midplate\'s snap posts through the board at H1, H2, H6; '
                     'not on build.py\'s EXPECTED list')
        else:
            c.update(ok=False, detail=det)
        checks.append(c)
    ins = json.loads((OB / 'insertion.json').read_text())
    hits = {k: v['hits'] for k, v in ins.items() if not k.startswith('_') and v.get('hits')}
    checks.append({'id': 'insertion', 'label': 'Panel layers and midplate go in from the back past the tub'
                   + (' and keys' if KEYS else ''),
                   'ok': not hits, 'value': len([k for k in ins if not k.startswith('_')]),
                   'detail': json.dumps(hits) if hits else 'every path clear', 'source': 'insertion.json'})
    later = ins.get('_later', {})
    checks.append({'id': 'insertion_later', 'label': 'PCBA in and lid on (switches, J1, SW11, side keys): clear',
                   'ok': not any(later.values()), 'detail': json.dumps(later), 'source': 'insertion.json _later'})
    if '_across' in ins:
        rows_a = ins['_across']
        placed = {k: v for k, v in rows_a.items() if 'right wall' not in k and 'bar 0.0' not in k}
        bad = [k for k, v in placed.items() if not v['clear']]
        other = {k: (v['hits'] or 'touching') for k, v in rows_a.items() if k not in placed and not v['clear']}
        checks.append({'id': 'insertion_across', 'label': 'Light strip: the stack pushed in across the pocket, bar 0.1-0.2 '
                       'inside the glass edge', 'ok': not bad, 'value': len(placed),
                       'detail': ('failing: ' + ', '.join(bad) + '; ' if bad else '') + 'also reported (outside the placement '
                       'rule, or a glass that cannot sit there): ' + json.dumps(other), 'source': 'insertion.json _across'})
    checks += [dict(c) for c in kchecks]
    for k, rows_k in mech['side_key_sweep'].items():
        # rows: the key swung about its root to 0..115 % of the way to its stop (P.TAB_VOID); the numbers are
        # overlap volumes (mm3) with the tub, lid body, midplate, PCB and its switch's body
        vols = lambda r: max(val for kk, val in r.items() if kk not in ('nub_travel_mm', 'plunger_push_mm'))  # noqa: E731
        upto = [r for r in rows_k if r['nub_travel_mm'] <= P.TAB_VOID + 1e-6]
        past = [r for r in rows_k if r['nub_travel_mm'] > P.TAB_VOID + 1e-6]
        ov = max(vols(r) for r in upto)
        checks.append({'id': f'side_key_sweep_{k}', 'label': f'Side key {k}: swung to its stop ({P.TAB_VOID} mm at the nub), '
                       'no overlap with the tub, lid, midplate, board or switch body', 'ok': ov == 0,
                       'value': max(r['plunger_push_mm'] for r in upto),
                       'detail': f'max overlap {ov} mm3; plunger pushed {max(r["plunger_push_mm"] for r in upto)} mm'
                       + (f'; past the stop ({past[-1]["nub_travel_mm"]} mm): max overlap {max(vols(r) for r in past)} mm3 '
                          '(reported)' if past else ''), 'source': 'mechanics.json side_key_sweep'})
    sp = OB / 'slice' / 'slice-report.json'
    if sp.exists():
        srep = json.loads(sp.read_text())
        for part, v in srep.items():
            if not isinstance(v, dict):
                continue
            if part == '_key_fit':            # not a part: the keys' fit read back from the sliced tub, coupon and key
                checks.append({'id': 'slice_key_fit', 'label': 'The keys&rsquo; fit, read back from the sliced tub, '
                               'chin coupon and key (the hooks&rsquo; tip to their slots&rsquo; back and under the roof '
                               'included)', 'ok': bool(v.get('ok')), 'source': 'slice/slice-report.json _key_fit'})
                continue
            if part.startswith('_'):
                continue
            rb = v.get('readback', [])
            checks.append({'id': f'slice_{part}', 'label': f'{part}: sliced (OrcaSlicer) and read back from the G-code',
                           'ok': v.get('exit') == 0 and all(r.get('ok') for r in rb),
                           'value': v.get('grams'), 'detail': f"{v.get('layers')} layers"
                           + (f" ({v['part_layers']} the part's, on a {v.get('raft_layers')}-layer raft)" if v.get('part_layers')
                              and v.get('raft_layers') not in (None, '0') else '') + f", {v.get('time')}, {v.get('grams')} g; "
                           + ', '.join(f"{r['what']}: {'ok' if r.get('ok') else 'FAIL'}" for r in rb), 'source': 'slice/slice-report.json'})
    if LS:
        lsj = json.loads((OB / 'light-strip.json').read_text())
        for j, (k, v) in enumerate(lsj['solids'].items()):
            checks.append({'id': f'strip_solid_{j:02d}', 'label': f'Light strip: {k}', 'ok': v['overlap_mm3'] == 0,
                           'value': v['gap'], 'detail': f"gap {v['gap']} mm, overlap {v['overlap_mm3']} mm3",
                           'source': 'light-strip.json solids'})
        rows_s = lsj['sweep']['rows']
        worst = {k: min(r[k] for r in rows_s) for k in ('pads_to_copper', 'pads_to_leds', 'bar_to_wall', 'foot_to_stop')}
        ov = max(max(r['copper_overlap_mm3'], r['led_overlap_mm3'], r['bar_wall_overlap_mm3']) for r in rows_s)
        checks.append({'id': 'strip_sweep', 'label': f'Light strip: swept over its placement box ({len(rows_s)} positions)',
                       'ok': ov == 0, 'detail': 'worst gaps ' + json.dumps(worst) + f'; max overlap {ov} mm3',
                       'source': 'light-strip.json sweep'})
    if CL:                                               # chin_check: every bottom-key feature absent
        cj = json.loads((OB / 'chin.json').read_text())
        for j, (k, v) in enumerate(cj['checks'].items()):
            checks.append({'id': f'chin_{j:02d}', 'label': f'Chinless: {k}', 'ok': bool(v), 'source': 'chin.json checks'})
    for c in checks:
        if c.get('ok') is None:
            c['ok'] = None
    ids = [c['id'] for c in checks]
    assert len(ids) == len(set(ids)), 'duplicate check ids'

    # ---- the case's numbers (Rev K's meta blocks, now per card) -----------------------------------------
    lg = logo.placed()
    lgb = logo.placed(P.LOGO_BACK)
    usb = {'mouth_x': u['mouth_x'], 'x1': P.X1, 'wall_x': list(uf['wall_x']), 'yc': u['yc'], 'zc': u['zc'],
           'shell_y': list(u['y']), 'shell_z': list(u['z']), 'recess': list(uf['size']), 'r': uf['r'],
           'recess_z': list(uf['port_z']), 'recess_y': list(uf['port_y']), 'seat_x': uf['seat_x'],
           'face_x': uf['face_x'], 'floor_x': list(uf['floor_x']), 'floor_t': P.USB_FLOOR['t'],
           'hole': list(uf['hole']), 'hole_r': uf['hole_r'], 'face_to_mouth': uf['face_to_mouth'],
           'plug_short_mm': uf['plug_short_mm'], 'insert_x': P.INSERT_X1,
           'spare': P.USB_PLUG_SPARE, 'overmold_max': list(P.OVERMOLD), 'typical': [11.0, 5.6], 'seam': P.SEAM}
    tabs_meta = [{'ref': tb['ref'], 'side': tb['side'],
                  'root': [round((P.X1 if tb['side'] > 0 else P.X0) - tb['side'] * P.TAB_T / 2, 3), tb['flex_root']],
                  'y_root': tb['y_root'], 'y_block': round(tb['y_block'], 3), 'free': tb['y_free'], 'pad_y': list(tb['pad_y']),
                  'face': list(tb['face']), 'gap': tb['gap'], 'click_mm': 0.25, 'nub_to': round(tb['nub_to'], 3),
                  'inner': round(tb['inner'], 3), 'stop': round(tb['stop'], 3),
                  'nub_arm': round(abs(tb['face'][1] - tb['flex_root']), 2)} for tb in tabs]
    tab_geom = {'proud': P.TAB_PAD_PROUD, 't': P.TAB_T, 'flex_t': P.TAB_FLEX_T, 'z': list(P.TAB_Z),
                'slot_clr': P.TAB_SLOT_CLR, 'end_clr': P.TAB_END_CLR, 'root_clr': P.TAB_ROOT_CLR,
                'sliver': P.SLIVER, 'void': P.TAB_VOID, 'wall': P.SIDE_WALL, 'relief': P.TAB_RELIEF_MAX,
                'nub': [P.NUB['w'], round(P.NUB['z'][1] - P.NUB['z'][0], 2)], 'nub_z': list(P.NUB['z']),
                'nub_w': {t['ref']: t['nub_w'] for t in tabs}, 'plunger': [2.882, 1.5],
                'window': {t['ref']: [round(v, 2) for v in body.tab_window(t)['y']] for t in tabs},
                'stop': mech['springs'].get('side_key_stop'), 'bar_top': P.TAB_BAR_TOP, 'end_foot': P.TAB_END_FOOT,
                'foot': P.TAB_FOOT, 'foot_gap': list(P.TAB_FOOT_GAP), 'hinge': P.TAB_HINGE, 'pad_face': list(P.TAB_PAD_FACE),
                'block_margin': P.TAB_BLOCK_MARGIN}
    panel_meta = ({'part': 'GDEY0426T82', 'label': 'GDEY0426T82 (plain)', 'touch': False, 'front_light': False, 'ribbons': 1,
                   'x0': hw.PANEL_X0, 'x1': hw.PANEL_X1, 'y0': hw.PANEL_Y0, 'y1': hw.PANEL_Y1, 'plain': P.PLAIN,
                   'front': P.PLAIN_FRONT, 'rear': round(P.PLAIN_FRONT - P.PLAIN['t'], 3), 'layers': [['glass', P.PLAIN['glass']],
                   ['fpl', P.PLAIN['fpl']], ['ps', P.PLAIN['ps']]], 'light': 'the Silkscreen light strip on its left border'}
                  if LS else
                  {'part': 'GDEQ0426T82-FT01C', 'label': 'FT01C touch + frontlight', 'touch': True, 'front_light': True,
                   'ribbons': 3, 'x0': hw.PANEL_X0, 'x1': hw.PANEL_X1, 'y0': hw.PANEL_Y0, 'y1': hw.PANEL_Y1,
                   'layers': panel.LAYERS, 'z': {k: [round(a, 3), round(b, 3)] for k, (a, b) in panel.z_levels().items()},
                   'touch_xy': panel.TOUCH, 'lgp': panel.LGP})
    if LS:
        rib_meta = {'report': mech['ribbons'], 'slot': panel.slot(), 'bend_r': panel.BEND_R, 'count': 1,
                    'outlines': {'main': P.PLAIN['fpc_poly']}, 'connectors': {'main': {'ref': 'J2', 'x': round(fps['J2']['cad'][0], 3)}},
                    'strip_tail': {'ref': 'J3', 'x': round(fps['J3']['cad'][0], 3)}}
    else:
        rib_meta = {'report': mech['ribbons'], 'slot': panel.slot(), 'bend_r': panel.BEND_R, 'count': 3,
                    'outlines': {k: r['poly'] for k, r in panel.RIBBONS.items()},
                    'connectors': {k: {'ref': r['conn'], 'x': round(fps[r['conn']]['cad'][0], 3)} for k, r in panel.RIBBONS.items()}}
    joint_meta = {**J, 'latch': mech.get('latches'), 'seam': P.SEAM,
                  'walls': {'left': joint.LOW_X0, 'right': joint.LOW_X1, 'top': P.TOP_IN, 'bottom': P.BOT_IN},
                  'outline': [P.X0, P.X1, P.Y0, P.Y1, P.CORNER_R],
                  'tabs': [[tb['side'], *sorted((tb['y_root'], tb['y_free']))] for tb in tabs],
                  'usb_y': list(uf['port_y']), 'reset_y': ry,
                  'j6_x': [hw.bounds('J6')[0] - 0.3, hw.bounds('J6')[1] + 0.3], 'top_screw': list(P.TOP_SCREW)}
    battery_meta = {'box': P.BATT, 'springs_y': [91.0, 104.0], 'data': mech['springs']['battery_spring'], 'fence': P.FENCE,
                    'bay': midplate.battery_bay()[1], 'bay_p': P.BAY, 'j7': hw.WRL_ONLY['J7'][0],
                    'card': {'x': [13.3, 24.3], 'z': [-1.45, -0.35], 'mouth_y': 78.64, 'out_y': 84.0},
                    'cell_bbox': L.bbox(M['battery_cell'])}
    # compare: compare.main() writes P.OUT/compare.json; point that one write at _work (P.OUT is read too)

    class _Out:
        def __init__(s, real, alt):
            s.real, s.alt = real, alt

        def __truediv__(s, name):
            return s.alt / name if name == 'compare.json' else s.real / name

        def __getattr__(s, a):
            return getattr(s.real, a)
    import compare
    real_out = P.OUT
    P.OUT = _Out(real_out, work)
    try:
        cmpd = compare.main()
    finally:
        P.OUT = real_out
    for r in cmpd['rows']:
        if r['name'].startswith('Silkscreen'):
            r['note'] = ('plain GDEY0426T82 with the light strip; ' if LS else 'FT01C panel with frontlight and touch; ') + \
                ('12 printed parts (plastic: tub, lid, midplate, keys, cranks, the rod gate)' if KEYS else
                 'chinless: 3 printed parts (tub, lid, midplate), no bottom keys')
    cmpd['attribution'] = ('Xteink X4 reference model by Zorian22 (Thingiverse thing:7287950), CC BY-NC-SA, measured '
                           'with calipers; the retro case from its author&rsquo;s print files.')
    deepest = min(hw.bounds(r)[4] for r in hw.solids() if r != 'PCB')
    if LS:
        pz = [round(P.PLAIN_FRONT - P.PLAIN['t'], 3), P.PLAIN_FRONT]
        bars = [{'name': 'Front skin', 'z': [P.LIP, P.Z_FRONT]},
                {'name': 'Light strip (bar + LEDs, beside the panel)', 'z': [P.PLAIN_FRONT, round(P.STRIP_LED_TOP, 3)], 'beside': True},
                {'name': 'Stops to the lip', 'z': [P.PLAIN_FRONT, P.LIP]},
                {'name': 'Plain panel (GDEY0426T82)', 'z': pz},
                {'name': 'Spring take-up', 'z': [P.DISP_REAR, pz[0]]}]
    else:
        bars = [{'name': 'Front skin', 'z': [P.LIP, P.Z_FRONT]},
                {'name': 'Panel (FT01C)', 'z': [P.DISP_REAR, P.LIP]}]
    bars += [{'name': 'Midplate', 'z': [P.MID_REAR, P.DISP_REAR]},
             {'name': 'Air to the board', 'z': [P.PCB_FRONT, P.MID_REAR]},
             {'name': 'PCB', 'z': [P.PCB_REAR, P.PCB_FRONT]},
             {'name': 'Parts behind the board (J6 deepest)', 'z': [round(deepest, 3), P.PCB_REAR]},
             {'name': 'Clearance', 'z': [P.LID_FLOOR_IN, round(deepest, 3)]},
             {'name': 'Back (lid floor)', 'z': [P.Z_BACK, P.LID_FLOOR_IN]},
             {'name': 'Battery (in the midplate slot, through the board notch)', 'z': [P.BATT['z'][0], P.BATT['z'][1]], 'beside': True}]
    printed = [{'name': 'tub', 'count': 1, 'file': f'tub-{ENV[b]}.stl'}, {'name': 'lid (with its 5 side keys)', 'count': 1, 'file': 'lid.stl'},
               {'name': 'midplate', 'count': 1, 'file': 'midplate.stl'}, {'name': 'key', 'count': 4, 'file': 'key-426.stl'},
               {'name': 'crank (crank-T or crank-M)', 'count': 4, 'file': 'crank-T.stl'},
               {'name': 'gate (the rod\'s stop)', 'count': 1, 'file': 'gate.stl'}]
    if CL:                                               # its own tub and lid, the shared midplate; nothing else
        printed = [{'name': 'tub', 'count': 1, 'file': f'tub-{ENV[b]}.stl'},
                   {'name': 'lid (with its 5 side keys)', 'count': 1, 'file': 'lid-chinless.stl'},
                   {'name': 'midplate', 'count': 1, 'file': 'midplate.stl'}]
    vol = {n: float(M[n].volume) for n in ['tub', 'lid', 'midplate'] + [f'skey_{r}' for r in side_refs]
           + [f'key_{r}' for r in P.KEY_REFS]}
    if KEYS:
        vol['cranks'] = 4 * float(M['crank_T'].volume)
        vol['gate'] = float(M['gate'].volume)
    vol_cm3 = sum(vol.values()) / 1000
    size = [round(float(v), 1) for v in (hi - lo)]
    bodyd = [round(P.X1 - P.X0, 2), round(P.Y1 - P.Y0, 2), round(P.Z_FRONT - P.Z_BACK, 2)]
    x4 = next(r for r in cmpd['rows'] if r['name'] == 'Xteink X4')
    retro = next(r for r in cmpd['rows'] if r['name'].startswith('X4 in'))
    facts = [
        {'id': 'envelope', 'label': 'Envelope', 'value': f'{bodyd[0]:.1f} x {bodyd[1]:.1f} x {bodyd[2]:.1f}', 'unit': 'mm',
         'note': f'{size[0]:.1f} across the side buttons'},
        {'id': 'x4', 'label': 'Xteink X4, for scale', 'unit': 'mm',
         'value': (re.search(r'spec ([0-9.]+ x [0-9.]+ x [0-9.]+)', x4['note']) or
                   re.match(r'(.*)', f"{x4['w']:.1f} x {x4['h']:.1f} x {x4['t']:.1f}")).group(1),
         'note': f"in its retro case: {retro['w']:.1f} x {retro['h']:.1f} x {retro['t']:.1f}"},
        {'id': 'printed', 'label': 'Printed, PLA', 'value': '12 parts',
         'note': 'tub, lid with its 5 side keys, midplate, 4 keys, 4 cranks, the rod gate'},
        {'id': 'plastic', 'label': 'Plastic', 'value': f'{vol_cm3:.1f}', 'unit': 'cm3',
         'note': f'solid volume; {vol_cm3 * 1.24:.0f} g of PLA at 100% infill'},
        {'id': 'panel', 'label': 'Panel', 'value': panel_meta['part'],
         'note': 'plain, with the light strip on its left border' if LS else 'touch + frontlight, 3 ribbons'},
        {'id': 'hardware', 'label': 'Hardware', 'value': '3 x M2x10',
         'note': 'ISO 4762 socket heads (a pan head also fits); a printed gate stops the rod, no other screw'},
        {'id': 'rod', 'label': 'Bottom-key rod', 'value': f'{P.ROD_CUT:.2f} mm of {P.ROD_D} filament', 'note': 'not printed; cut from the spool'},
        {'id': 'files', 'label': 'Files', 'value': 'STL + STEP', 'note': 'every part, both tubs, the chin and gate coupons, a printable PCBA dummy'},
    ]
    if CL:
        facts = [f for f in facts if f['id'] != 'rod']
        for f in facts:
            if f['id'] == 'printed':
                f.update(value='3 parts', note='tub, lid with its 5 side keys, midplate')
            elif f['id'] == 'hardware':
                f['note'] = 'ISO 4762 socket heads (a pan head also fits); no rod, no gate'
            elif f['id'] == 'panel':
                f['note'] = (('plain, with the light strip on its left border' if LS else 'touch + frontlight, 3 ribbons')
                             + '; the board without its 4 bottom keys')
            elif f['id'] == 'files':
                f['note'] = (f'tub-{ENV[b]} and lid-chinless' + (' (the chinless lid)' if LS else '')
                             + ', the shared midplate, a printable PCBA dummy')
    glance = [] if CL else [
        f'One code base, two builds: <b>standard</b> for the GDEQ0426T82-FT01C (touch + frontlight) and <b>light strip</b> '
        f'for the plain GDEY0426T82 with the Silkscreen light strip. Only the tub differs; you are looking at the '
        f'<b>{"light-strip" if LS else "standard"}</b> build.',
        'Bottom keys: a straight key slides in the chin and turns a bell crank on a 1.75 mm filament rod, whose nose '
        f'pushes the switch: {KF["lever"]["ideal_key_over_switch"]:.3f} &times; the switch force at the finger before '
        'friction. <a href="#m=keys" data-goto="keys">Bottom keys</a>',
        'Crank-T for the SHOU HAN TS365ZJ on every JLC board, crank-M for the APEM MJTP1117. Print four of the one that '
        'matches your board.',
        f'The five side keys are part of the lid. A tongue runs round the tub&rsquo;s rim into a closed groove in the lid, '
        f'{J["latch_count"]} latches hold it shut, and three screws clamp the board. <a href="#m=joint" data-goto="joint">Joint</a>',
        '<b>Rev L, printed twice:</b> the rod, cranks and gate fitted. In test 2 the bottom keys tilted, sat low or fell '
        'out, so they are now hook keys: two rigid hooks each, in slots in the chin wall. Reprint the tub and the four '
        'keys (not printed yet), and keep the tub face down from the keys until the board is in. Print the gate coupon '
        'first; the chin coupon is an optional fit check.',
    ]
    if CL:
        glance = [
            '<b>Chinless</b> is the standard build without the bottom keys: the same GDEQ0426T82-FT01C touch + frontlight '
            f'panel, its own tub and lid, and the case ends just below the board: {bodyd[0]:.2f} &times; {bodyd[1]:.1f} '
            f'&times; {bodyd[2]:.1f} mm, {125.0 - bodyd[1]:.1f} mm shorter. You are looking at the <b>chinless</b> build.',
            '<b>The board needs SW9, SW8, SW3 and SW2 left off.</b> Fitted, they hang 1.92 mm past its bottom edge, into '
            'the chin wall. Touch and the five side keys are the controls.',
            'Three printed parts: <code>tub-chinless</code>, <code>lid-chinless</code> (the side keys are part of it) and '
            'the shared midplate. No keys, cranks, rod or gate; plate 4 of the plate file has all three.',
            'The wordmark is centred on the face below the window, the back icon on the shorter back, and the lid&rsquo;s '
            'H3 / H4 bosses run into the chin wall.',
            f'The five side keys, the tongue and its {J["latch_count"]} latches, the USB-C divot, the reset hole and the '
            'battery are the standard build&rsquo;s. <a href="#m=joint" data-goto="joint">Joint</a>',
        ]
    if LC:
        glance = [
            '<b>Light-strip chinless</b> is the light-strip build without the bottom keys: the plain GDEY0426T82 with '
            'the Silkscreen light strip on its left border, its own tub, the chinless lid, and the case ends just below '
            f'the board: {bodyd[0]:.2f} &times; {bodyd[1]:.1f} &times; {bodyd[2]:.1f} mm, {125.0 - bodyd[1]:.1f} mm '
            'shorter. You are looking at the <b>light-strip chinless</b> build.',
            '<b>The board needs SW9, SW8, SW3 and SW2 left off.</b> Fitted, they hang 1.92 mm past its bottom edge, into '
            'the chin wall. The plain panel has no touch, so the four page keys and power are the controls.',
            'Three printed parts: <code>tub-light-strip-chinless</code>, <code>lid-chinless</code> (the chinless '
            'build&rsquo;s lid: the lid does not depend on the panel) and the shared midplate. No keys, cranks, rod or '
            'gate; plate 5 of the plate file has all three.',
            'The light strip goes in as on the light-strip build, with no SW9 lead to trim. <a href="#m=strip" '
            'data-goto="strip">Light strip</a>',
            f'The wordmark, the back, the lid&rsquo;s H3 / H4 bosses, the five side keys and the tongue with its '
            f'{J["latch_count"]} latches are the chinless build&rsquo;s. <a href="#m=joint" data-goto="joint">Joint</a>',
        ]
    strip_block = {
        'case_cards': [{'h': '4.26&#x2033; &middot; enclosures/case-426', 'items': [
            'Front shell only; the lid, midplate, bottom keys, cranks and rod are shared with the standard build.',
            'Plain GDEY0426T82 panel instead of the FT01C: three rails hold its front at Z 4.00, on a print-layer boundary.',
            f'Ceiling over the left border raised to {P.STRIP_CEIL["z"]:.2f}, so the LED tops ({P.STRIP_LED_TOP:.2f}) clear it '
            'and the light passes under the skin to the window.',
            'Hold-down pads press the bar between the pairs, sized from the LED solder pads so they never touch them, and '
            'reaching the part of the border the e-ink film backs.',
            '0.3 mm relief in the left wall, a 0.2 mm window bevel and a ribbon gap widened to 7.7 mm for the neck.']}],
    }
    if LS:
        KEY_CAM = [[xs - 30, -14, 10], [xs, -3.6, 1.2]]
        kstep = ('<p>Cut through SW8, seen from the side: the board runs up, the face is to the right. A straight key '
                 '(slate) slides down in the chin and presses the pad of a bell crank (amber), which turns on a 1.75 mm '
                 'filament rod (blue) and pushes the switch plunger sideways. <a href="#m=keys" data-goto="keys">Bottom '
                 'keys</a> shows it moving.</p>')
        strip_block['steps'] = asciify([
            {'t': 'Fitted', 'cam': [[-96, -92, 150], [26, 48, 2]], 'f': 1, 'b': '<p>The bar lies on the panel\u2019s left border under the bezel; the tail wraps the bottom glass edge, goes through the board\u2019s slot and plugs into J3 on the back.</p>'},
            {'t': 'As it arrives', 'cam': [[-30, -40, 150], [8, 44, 3]], 'f': 0, 'b': '<p>Black coverlay, twelve LEDs in six warm/cool pairs, a bare hinge between the top two pairs, gold contacts at the tail. Diode-test one LED first, then solder and bench-test on the S / C / W pads.</p>'},
            {'t': 'Peel and lay the bar', 'cam': [[-26, -18, 46], [2, 20, 3]], 'f': 0, 'tape': True, 'b': '<p><span class="tag tape">3M 9077</span>Peel the liners on the two taped pieces. Lay the bar with its outer edge 0.1 mm <b>inside</b> the left glass edge, never overhanging: it would scrape the case wall when the stack goes in. The round top sits 1.3 mm below the top edge, the foot along the bottom border. Press between the LEDs, not on them.</p><p><span class="tag free">keep free</span>The hinge between the top two pairs lies flat and untaped on this reader.</p>'},
            {'t': 'Kapton on the path', 'cam': [[-24, -34, 18], [10, 6, 1]], 'f': 0, 'kapton': True, 'b': '<p><span class="tag kapton">Kapton</span> over both slot edges where the neck passes. This board has no SW9 (no bottom keys), so there is no lead to trim.</p>'
             if CL else '<p>First trim SW9&rsquo;s left lug lead flush: as it comes it stands 0.71 mm proud, 0.1 mm from the neck. Then <span class="tag kapton">Kapton</span> over it and over both slot edges where the neck passes.</p>'},
            {'t': 'Wrap the glass edge', 'cam': [[-26, -30, 20], [10, 6, 2]], 'f': 0.3, 'b': '<p>Wrap the neck 180\u00b0 around the bottom glass edge, inside radius 0.7\u20131.0 mm. Never crease it. The spare 0.5\u20132 mm of tail goes into this U.</p>'},
            {'t': 'Down the slot', 'cam': [[-30, -12, -26], [10, 8, 0]], 'f': 0.68, 'b': '<p>Under the glass, down the board\u2019s slot, and onto the back.</p>'},
            {'t': 'Into J3', 'cam': [[-16, -6, -40], [11, 16, -1]], 'f': 1, 'kapton': True, 'b': '<p>Contacts face away from the board. Push the tab fully home (about 2.9 mm) and close the lever. <span class="tag kapton">Kapton</span> strap over the stiffened end onto the board&rsquo;s back: J3 holds only about 3 N. Then push the whole stack into the case with the glass held against the right-hand wall.</p>'},
            {'t': 'Close the case', 'cam': [[-3.5, 31.2, 8.0], [1.2, 49.7, 4.2]], 'cutY': 49.7, 'f': 1, 'caseOn': True, 'cut': True, 'b': '<p>Cut through LED D4. The light-strip front shell raises the ceiling over the left border so the LED tops clear it, and adds stops for the plain panel and pads that hold the bar down between the pairs. The light passes under the ceiling to the window edge.</p>', 'drawing': 'strip_led'},
            *([] if CL else [{'t': 'The bottom keys', 'cam': KEY_CAM, 'cutX': xs, 'f': 1, 'caseOn': True, 'cut': True, 'b': kstep}]),
        ])
        if CL:
            strip_block['case_cards'][0]['items'][0] = ('Front shell only: its own tub. The lid (the chinless lid), the '
                                                        'midplate and the side keys are the chinless build&rsquo;s.')
            # stripDiffRows reads these rows by their part names; the keyed rows (bottom keys, cranks) are left out
            strip_block['diff'] = [
                {'part': 'Tub (front shell)', 'same': False, 'std': 'tub-chinless', 'ls': 'tub-light-strip-chinless',
                 'text': 'Its own per build: the light-strip chinless tub holds the plain GDEY0426T82 panel, the chinless '
                         'tub the FT01C'},
                {'part': 'Lid, midplate', 'same': True, 'text': 'Shared: the chinless lid (lid-chinless) and the midplate'},
                {'part': 'Panel and ribbons (not printed)', 'same': False,
                 'text': 'FT01C with 3 ribbons (chinless); plain GDEY0426T82 with its EPD FPC, and the strip in J3 '
                         '(light-strip chinless)'}]
            strip_block['diff_note'] = ('Against the chinless build (the FT01C touch panel), the light-strip chinless '
                                        'prints only its own tub, <code>tub-light-strip-chinless</code>; its lid is '
                                        '<code>lid-chinless</code>, and the midplate is the one every build shares.')
        lsj = json.loads((OB / 'light-strip.json').read_text())
        strip_block['checks'] = {'solids': lsj['solids'], 'tail': lsj['tail'].get('nominal', {}).get('path'),
                                 'plain_stack': mech.get('plain_stack')}
        strip_block['geometry'] = {'plain_front': P.PLAIN_FRONT, 'flex_top': P.STRIP_FLEX_TOP, 'led_top': P.STRIP_LED_TOP,
                                   'ceiling': P.STRIP_CEIL['z'], 'stack': P.STRIP_STACK, 'place': P.STRIP_PLACE,
                                   'dx_fit': P.STRIP_DX_FIT, 'sweep': P.STRIP_SWEEP, 'hold_z': P.STRIP_HOLD['z']}
    cards = {
        'glance': {'bullets': glance, **({'against': (
            'Against the light-strip build, the tub and the lid differ and there are no bottom keys; the midplate, the '
            'side keys, the panel and the light strip are the same, and the board leaves SW9, SW8, SW3 and SW2 off. '
            'Against the chinless build, only the tub and the panel differ.')} if LC else {})},
        'keys': {} if CL else {'proud_mm': P.KEY_CAP['proud'], 'chin_deeper_mm': 1.0, 'chin_y': P.BOT_IN, 'rail_y': list(P.RAIL_Y),
                 'rings': 5, 'seats': 4, 'coupon': 'coupon-chin',
                 'rod_len': P.ROD_CUT, 'rod_hole_d': P.ROD_HOLE_D, 'end_play': [0.3, 0.7], 'cap_y': list(P.KEY_CAP['y']),
                 'cheek': list(P.CRANK_CHEEK), 'slot': list(P.SLOT), 'travel': KF['travel'], 'key_sweep_checks': mech['key_sweep']['checks'],
                 'side_clearance': bk['side_clearance'], 'hang_theta': bk['paths']['c_board_in']['free_theta'],
                 'mech_travel_crosscheck': trav},
        'strip': strip_block,
        'sidekeys': {'count': len(tabs), 'refs': side_refs, 'draw': {'plan': 'SW10', 'side': 'SW1', 'elev': 'SW10'},
                     'tabs': tabs_meta, 'tab_mech': mech['springs']['side_keys'],
                     'tab_pad': [round(P.TAB_PAD_LEN - 2 * (P.TAB_PAD_PROUD - 0.05), 2), round(P.TAB_PAD_FACE[1] - P.TAB_PAD_FACE[0], 2)],
                     'tab_geom': tab_geom, 'summary': sidekeys.summary(), 'sweep': mech['side_key_sweep']},
        'joint': {'latch_count': J['latch_count'], 'tongue_len': J['tongue_len'], 'joint': joint_meta,
                  'latches': mech['latches'], 'board_snap': {**mech.get('board_snap', {}), 'posts': list(P.SNAP_POSTS),
                                                             'at': {r: fps[r]['cad'] for r in P.SNAP_POSTS}, 'geom': P.BOARD_SNAP}},
        'usb': {'usb': usb, 'ref': 'J1'},
        'reset': {'reset': rs, 'ref': hw.RESET},
        'screen': {'stack': mech['screen_stack'], 'panel': panel_meta, 'screw_clear': {'panel_mm': 1.29, 'ribbon_mm': 4.28},
                   'insertion': {k: v for k, v in ins.items() if k != '_across'}, 'z': {'lip': P.LIP, 'disp_rear': P.DISP_REAR,
                   'step': P.POCKET_STEP_Z}, **({'plain_stack': mech.get('plain_stack')} if LS else {})},
        'detent': {'detents': {**mech.get('mid_detents', {}), 'p': P.MID_DETENT, 'edge_clr': midplate.EDGE_CLR,
                               'wall_x': [P.POCKET_X0, P.POCKET_X1]},
                   'midplate': {'springs': midplate.SPRINGS, 'L': midplate.SPRING_L, 'W': midplate.SPRING_W, 'T': midplate.SPRING_T,
                                'nub_h': midplate.NUB_H, 'data': mech['springs']['midplate_spring']}},
        'ribbons': {'ribbons': rib_meta},
        'battery': {'battery': battery_meta},
        'zstack': {'bars': bars, 'total': [P.Z_BACK, P.Z_FRONT], 'budget': cmpd['budget']},
        'closing': {'holes': {r: fps[r]['cad'] for r in ('H1', 'H2', 'H3', 'H4', 'H5', 'H6')}, 'top_screw': list(P.TOP_SCREW),
                    'screw_seat_z': P.Z_BACK + P.M2_HEAD_CB_DEPTH, 'screws': f'M2 x {P.SCREW_L:g} ISO 4762 socket head',
                    'head': {'iso': 'ISO 4762', 'kind': 'socket head cap', 'dk': 3.8, 'k': 2.0, 'also': 'ISO 7045 pan head',
                             'below_back': {r: round(P.M2_HEAD_CB_DEPTH - 2.0, 3) for r in ('H3', 'H4', 'top')}},
                    'screw_list': [{'id': r, 'node': f'screw_{r}', 'label': 'top screw' if r == 'top' else r,
                                    'at': [round(v, 3) for v in xy], 'seat_z': round(P.Z_BACK + P.M2_HEAD_CB_DEPTH, 3),
                                    'cb_depth': P.M2_HEAD_CB_DEPTH, 'through_board': r != 'top'}
                                   for r, xy in (('H3', fps['H3']['cad'][:2]), ('H4', fps['H4']['cad'][:2]), ('top', P.TOP_SCREW))],
                    'cb_depth': {'bottom': P.M2_HEAD_CB_DEPTH, 'top': P.M2_HEAD_CB_DEPTH},
                    'screw_len': P.SCREW_L, 'pilot': P.M2_PILOT,
                    **({} if CL else {'gate': {'web': P.GATE['web'], 'flange': P.GATE['flange'], 'top_clr': P.GATE['top_clr'],
                                               'pull_d': P.GATE['pull_d'], 'stop_x': round(P.ROD_STOP_X0, 3)}}),
                    'board_snap': mech.get('board_snap')},
        'edges': {'edges': {'front_r': P.FRONT_EDGE_R, 'back_r': P.BACK_EDGE_R, 'seam_chamfer': P.SEAM_CHAMFER,
                            'key_chamfer': P.KEY_EDGE_CHAMFER, 'window_bevel': P.WINDOW_FACE_W},
                  'logo': {'polys': L.rings(lg, 2), 'bounds': [round(v, 2) for v in lg.bounds]},
                  'logo_back': {'polys': L.rings(lgb, 2), 'bounds': [round(v, 2) for v in lgb.bounds],
                                'width': P.LOGO_BACK['width'], 'depth': P.LOGO_BACK['depth'], 'at': [P.LOGO_BACK['x'], P.LOGO_BACK['y']]}},
        'compare': cmpd,
        'assembly': {'readme': 'README.md "Assembly (tub face down)" and section 6'},
        'checks': {'count': len(checks), 'failed': [c['id'] for c in checks if c['ok'] is False],
                   'measure': measure_list(b, P, hw, panel, usb, K)},
        # the zip carries the standard build's PCBA dummy only (its own on every build: the 16 MB file limit)
        'files': {'dummy': json.loads(((OB.parent / 'standard') if CL else OB).joinpath('pcba-dummy.json').read_text()),
                  'plate': 'The OrcaSlicer plate file, print/silkscreen-426-plates.3mf in the repo (not in the zip), lays '
                           'every part out: the standard and light-strip cases on plates 1 and 2, the coupons, the rod jig '
                           'and crank-M on plate 3, the chinless case (no bottom keys: tub-chinless, lid-chinless and a '
                           'midplate) on plate 4 and the light-strip chinless case (its own tub, the chinless lid) on plate '
                           '5. The 4.26 is built in 32 configurations in all (side keys: all four, the left, right or upper '
                           'pair; with or without the dev header J6), and each has its own OrcaSlicer project, made by the '
                           'case project: enclosures/case-426/README.md in the repo, "Builds".'},
    }
    meta = {
        'title': 'Silkscreen case, 4.26"', 'size_label': C.SIZE_LABELS[SIZE], 'build_label': C.BUILD_LABELS[b],
        'panel': panel_meta, 'envelope': envelope, 'size': size, 'body': bodyd,
        'walls_x': [round(P.X0, 3), round(P.X1, 3)], 'insert_x': [round(P.INSERT_X0, 3), round(P.INSERT_X1, 3)],
        'z': {'front': P.Z_FRONT, 'back': P.Z_BACK, 'seam': P.SEAM, 'lip': P.LIP, 'pcb_front': P.PCB_FRONT, 'pcb_rear': P.PCB_REAR,
              'mid_rear': P.MID_REAR, 'disp_rear': P.DISP_REAR, 'step': P.POCKET_STEP_Z, 'lid_floor_in': P.LID_FLOOR_IN},
        'active': {'cx': hw.ACTIVE_CX, 'cy': hw.ACTIVE_CY, 'w': hw.ACTIVE_W, 'h': hw.ACTIVE_H},
        'frame': 'X = KiCad x - 44.24, Y = 148.25 - KiCad y, Z = 0 at the board\'s rear face, +Z toward the screen (mm)',
        'printed': {'parts': printed, 'count': sum(p['count'] for p in printed), 'volume_cm3': round(vol_cm3, 2),
                    'volume_by_part_cm3': {k: round(v / 1000, 3) for k, v in vol.items()}},
        'side_keys': side_refs, 'bottom_keys': list(P.KEY_REFS), 'reset': hw.RESET,
        **({'board': 'SW9, SW8, SW3 and SW2 not fitted'} if CL else {}),
        'source': {'project': 'silkscreen-enclosures/enclosures/case-426', 'build': ENV[b],
                   'out': f'out/{ENV[b]}', 'generated': time.strftime('%Y-%m-%dT%H:%M:%S'), 'adapter': 'showcase/gen/adapt_426.py'},
    }
    data = {'schema': C.SCHEMA, 'size': SIZE, 'build': b, 'meta': meta, 'facts': facts, 'presets': presets,
            'explode': explode, 'controls': controls, 'keys': K, 'drawings': D, 'cards': cards, 'checks': checks,
            'assembly': assembly, 'downloads': None}
    data = rnd(asciify(data), 4)
    (work / 'data.json').write_text(json.dumps(data, separators=(',', ':'), ensure_ascii=True, allow_nan=False), encoding='ascii')
    log(b, 'data written', (work / 'data.json').stat().st_size)


def measure_list(b, P, hw, panel, usb, K):
    """cards.checks.measure: Rev K's "Measure before printing" (src/showcase_page.html; README section 11 "To measure
    before printing"), brought to today's design: the microSD socket is now checked as the real part, and the bell-crank
    keys add the TS365ZJ, the optional chin coupon (the hook keys' fit check, test 2) and the rod. HTML strings."""
    f2 = lambda v: f'{v:.2f}'.rstrip('0').rstrip('.')                               # noqa: E731
    LS, CL = b in C.STRIP_BUILDS, K is None
    T = C.switch_geom('T') if CL else K['switches']['T']
    cell_t = P.BATT['z'][1] - P.BATT['z'][0]
    gate_fit = (P.GATE_SLOT['mouth'][1] - P.GATE_SLOT['mouth'][0] - P.GATE['web_y'][1] + P.GATE['web_y'][0]) / 2  # a side
    out = [
        f'<b>The battery pack.</b> The slot&rsquo;s lip and snaps sit {f2(P.BAY["lip_z"])}&nbsp;mm off the model&rsquo;s '
        f'back (a {f2(cell_t)}&nbsp;mm pack), so a pack much thicker than 5.2&nbsp;mm won&rsquo;t go under them.',
        ('<b>The panel&rsquo;s thickness</b> (the plain GDEY0426T82: '
         f'{f2(P.PLAIN["t"])} &plusmn;{f2(P.PLAIN["t_tol"])}&nbsp;mm without its PS protective film; peel the film where '
         'the stops and the strip land)' if LS else
         f'<b>The panel&rsquo;s thickness</b> (the FT01C: {f2(hw.PANEL_T)} &plusmn;{f2(hw.PANEL_T_TOL)}&nbsp;mm in its '
         'drawing)') +
        ('.' if CL else f' and <b>the switches&rsquo; travel</b> ({f2(T["travel"]["click"])}&nbsp;mm to the click, '
                        f'{f2(T["travel"]["bottom"])} to the bottom in the model).'),
        (f'<b>The EPD FPC</b> folds on an assumed R{f2(panel.BEND_R)}' if LS else
         f'<b>The three ribbons</b> fold on an assumed R{f2(panel.BEND_R)}') +
        ': the drawing gives none, so check the real ' + ('FPC folds' if LS else 'ribbons fold') +
        ' that tightly without creasing.',
        f'<b>USB-C cables.</b> The recess takes overmolds up to {f2(P.USB_RECESS[0])} &times; {f2(P.USB_RECESS[1])}&nbsp;mm, '
        f'and a typical plug seats about {f2(usb["plug_short_mm"])}&nbsp;mm short of full depth: try your cables on the '
        'PCBA dummy.',
        f'<b>Tape on the plungers</b> must be thinner than the side keys&rsquo; gap: {f2(P.TAB_GAP_SIDE[-1])}&nbsp;mm on the '
        f'two-button side (one layer of electrical tape, 0.13&ndash;0.18, fits) but {f2(P.TAB_GAP_SIDE[+1])}&nbsp;mm on the '
        'power side, so leave those plungers bare.',
        '<b>Lid seating.</b> If a side key clicks with no free travel, or needs a long press, the lid is sitting to one '
        'side: check the tongue is fully down in its groove all round.',
        '<b>The microSD socket</b> is now checked as the real part (J7&rsquo;s MEM2075 solid, not its VRML box): it '
        'touches nothing, the lid 1.08&nbsp;mm away, so the lid&rsquo;s H2 post needs no check. Measure only if your '
        'board carries a different socket.',
        f'<b>A real TS365ZJ, before printing crank-T.</b> Its body width, plunger width and height are from its drawing. '
        f'The model puts its tip at y {f2(T["face_y"])} ({f2(T["face_worst_y"])} at worst) and its plunger at Z '
        f'{f2(T["nub_z"][0])} to {f2(T["nub_z"][1])} ({f2(T["nub_z_worst"][0])} to {f2(T["nub_z_worst"][1])} at worst): '
        'measure tip to signal-pin row, plunger height and width.',
        '<b>The chin coupon</b> (optional, about 15 minutes: <code>coupon-chin</code>, the chin round one key opening with '
        'its two hook slots, and one <code>key-426</code>). The key should slide up its slots from inside with no binding '
        f'and stop level, 2.4&nbsp;mm proud: its hooks {f2(P.KEY_W_OUT)}&nbsp;mm under the skin at rest, '
        f'{f2(P.KEY_HOOK["tip"] - P.KEY_SLOT["back"])}&nbsp;mm off the slots&rsquo; back. A firm thumb push outward from '
        'inside should leave no whitening at the hooks or behind the slots. It is a fit check only: nothing is chosen from '
        'it.',
        f'<b>The gate coupon</b>, once per printer and filament (<code>coupon-gate</code>: the left wall with the gate&rsquo;s '
        f'slot, and a gate). The gate should slide in at {f2(gate_fit)}&nbsp;mm a side, cam a 20&nbsp;mm piece of rod home and '
        'lift out with a straightened paperclip. Proof test on a kitchen scale, tape over the rim for the lid, the rod piece '
        'pressed straight down: at 2.8&nbsp;kg (27&nbsp;N) no crack, no visible set, the gate still lifts out; at 5.5&nbsp;kg '
        '(54&nbsp;N) nothing breaks. Too tight: 0.15 a side. Cracked where the web meets the flange: lips 1.05, flange 0.70.',
        f'<b>The rod.</b> {P.ROD_CUT:.2f} &plusmn;0.2&nbsp;mm of {f2(P.ROD_D)}&nbsp;mm PLA filament, straightened on the '
        'bed at about 60&nbsp;&deg;C under a flat plate. It must roll freely on a flat surface with no gap over '
        '0.1&nbsp;mm under it: a bowed rod binds the cranks. Taper the end that goes in first like a pencil to a flat '
        'about 0.8&nbsp;mm across, and cut the tail square: it bears on the gate.',
    ]
    if CL:                                     # no TS365ZJ, chin coupon, gate coupon or rod on the chinless build
        out = [x for x in out if not x.startswith(('<b>A real TS365ZJ', '<b>The chin coupon', '<b>The gate coupon',
                                                    '<b>The rod.'))]
        out.append('<b>The board&rsquo;s bottom edge.</b> The chin wall stands 0.6&nbsp;mm below it, so SW9, SW8, SW3 and '
                   'SW2 must be left off (fitted, they reach 1.92&nbsp;mm past the edge). A board whose outline runs '
                   'more than 0.4&nbsp;mm long toward the chin will not go in.')
    if LS:
        st = P.STRIP_STACK
        out.append(f'<b>The strip&rsquo;s stack</b> under the hold-downs (flex + PI stiffener + 9077 tape, '
                   f'{st["tape"] + st["pi"] + st["flex"]:.3f}&nbsp;mm nominal), with a micrometer at 2&ndash;3 points between '
                   'LED pairs, liner subtracted: it should be 0.37&ndash;0.40. Thinner than 0.37, put 0.05 Kapton on each '
                   'pad face; over 0.43, sand the pads back by the excess.')
    return out


# ============================================================================================================
# parent: run the children, split the nodes, write the files, check
# ============================================================================================================
def load_npz(p):
    import trimesh
    z = np.load(p)
    names = sorted({k.split('|', 1)[1] for k in z.files})
    out = {}
    for n in names:
        out[n] = trimesh.Trimesh(z['v|' + n], z['f|' + n], process=False)
    return out


def downloads(root, out):
    """models-426.js: one zip with the repo's print/4.26/ (the shared print files once, every tub, ROD.txt), the rod
    jig and the PCBA dummy, in the 3.68's folder layout (sc_contract: one layout in both sizes): shared/, standard/,
    light-strip/, chinless/, light-strip-chinless/, dummy/, ROD.txt and README.txt at the top."""
    import sc_lib as L
    # the chinless builds (2026-10-04, 2026-10-07): their own tubs in chinless/ and light-strip-chinless/, the chinless
    # lid in chinless/ (listed for both: builds ['cl', 'lc']), the shared midplate; the shared files they do not use
    # carry skip_builds ['cl', 'lc'] (the files card's "only this build" leaves them out)
    files = sorted(p for p in PRINT.iterdir() if p.is_file() and not (C.ZIP_NOT_SHOWN[SIZE] and p.name.startswith(C.ZIP_NOT_SHOWN[SIZE]))) + ROD_JIG
    dummy = root / 'out' / 'standard' / 'pcba-dummy.stl'
    dummy_ls = root / 'out' / 'light-strip' / 'pcba-dummy.stl'
    assert dummy.read_bytes() == dummy_ls.read_bytes(), 'the PCBA dummy differs per build'
    cut = json.loads((out / '_work' / 'std' / 'data.json').read_text())['keys']['rod']['cut']   # params is per child
    # (id, folder, label, what, match, builds)
    groups_def = [
        ('shared', 'shared/', 'Shared parts',
         'Lid (with its five side keys), midplate, the bottom keys (key-426, print 4, elephant-foot compensation 0, on a '
         '2-layer raft), both '
         'cranks (print 4 of the one for your switches: crank-T for TS365ZJ, on every JLC board; crank-M for MJTP1117; on '
         'the pad end, EFC 0, on a 2-layer raft), the rod\'s side gate (print 2, on its inner face, EFC 0), the gate coupon (print it first, '
         'once per printer and filament), the optional chin coupon (coupon-chin: the chin around one key opening with its '
         'two hook slots, printed with one key-426: a fit check of the hook keys) and the rod jig: the same in both '
         'builds',
         lambda n: n.split('.')[0] in ('lid', 'midplate', 'key-426', 'crank-M', 'crank-T', 'gate', 'rod-jig') or n.startswith('coupon-'), None),
        ('std', 'standard/', 'Standard build', 'The standard tub, for the GDEQ0426T82-FT01C touch + frontlight panel',
         lambda n: n.startswith('tub-standard.'), ['std']),
        ('ls', 'light-strip/', 'Light-strip build', 'The light-strip tub, for the plain GDEY0426T82 with the Silkscreen '
         'light strip', lambda n: n.startswith('tub-light-strip.'), ['ls']),
        ('cl', 'chinless/', 'Chinless build', 'The chinless tub and lid, for the FT01C touch + frontlight panel and a '
         'board without its four bottom keys (SW9, SW8, SW3, SW2 not fitted); with the shared midplate',
         lambda n: n.startswith(('tub-chinless.', 'lid-chinless.')), ['cl']),
        ('lc', 'light-strip-chinless/', 'Light-strip chinless build', 'The light-strip chinless tub, for the plain '
         'GDEY0426T82 with the Silkscreen light strip and a board without its four bottom keys (SW9, SW8, SW3, SW2 not '
         'fitted); with the chinless lid (lid-chinless, in chinless/) and the shared midplate',
         lambda n: n.startswith('tub-light-strip-chinless.'), ['lc']),
        ('rod', '', 'Rod notes', f'How to cut, straighten and taper the {cut:.2f} mm 1.75 mm filament rod (not '
         'printed) and fit its printed gate', lambda n: n == 'ROD.txt', None),
    ]
    readme = ('Silkscreen case, 4.26" - print files for all four builds\r\n\r\n'
              'Standard build: shared/ + standard/.  Light-strip build: shared/ + light-strip/.\r\n'
              'Chinless build (no bottom keys): chinless/ + shared/midplate only.\r\n'
              'Light-strip chinless build (no bottom keys): light-strip-chinless/ + chinless/lid-chinless\r\n'
              '+ shared/midplate only.\r\n'
              'shared/: lid, midplate, key-426 (x4), crank-T or crank-M (x4, the one for your switches: crank-T for\r\n'
              'SHOU HAN TS365ZJ, on every JLC board; crank-M for APEM MJTP1117), gate (print 2: the rod\'s stop),\r\n'
              'the gate coupon (print it first), coupon-chin (optional: with one key-426, a fit check of the hooks),\r\n'
              'rod-jig (straightens and cuts the rod).\r\n'
              'standard/: tub-standard (GDEQ0426T82-FT01C touch + frontlight panel). light-strip/: tub-light-strip\r\n'
              '(plain GDEY0426T82 with the Silkscreen light strip). chinless/: tub-chinless and lid-chinless\r\n'
              '(FT01C panel; the board WITHOUT SW9, SW8, SW3, SW2 fitted; 68.18 x 117.4 x 12.7 mm).\r\n'
              'light-strip-chinless/: tub-light-strip-chinless (the plain panel with the light strip; the board\r\n'
              'WITHOUT SW9, SW8, SW3, SW2 fitted; it takes the chinless lid).\r\n'
              'ROD.txt: the bottom keys\' rod (not printed)\r\n'
              'and its gate. dummy/pcba-dummy.stl: a printable stand-in for the board, to test-fit the case.\r\n'
              'STL files are oriented and placed as sliced; STEP files are in the CAD frame.\r\n'
              'The keys and the cranks print on a 2-layer raft (raft contact Z distance 0.2, the raft\'s initial\r\n'
              'layer expansion 1), elephant-foot compensation 0, the cranks with Arachne walls; the plate file sets it.\r\n'
              'Every part laid out on three plates for OrcaSlicer, the chinless case on a fourth and the\r\n'
              'light-strip chinless case on a fifth: print/silkscreen-426-plates.3mf in the repo. Every other\r\n'
              'configuration (side-key layouts, no dev header) has its own OrcaSlicer project: see\r\n'
              'enclosures/case-426/README.md in the repo.\r\n'
              'Rev L was printed twice: the rod, cranks and gate fitted. After test 2 the bottom keys are hook keys\r\n'
              '(two rigid hooks each, in slots in the tub\'s chin wall): reprint the tub and the four keys, and keep\r\n'
              'the tub face down from the keys until the board is in (ROD.txt). Print the gate coupon first.\r\n')
    entries = [('README.txt', readme.encode('ascii'))]
    groups = []
    used = set()
    for gid, folder, label, what, fn, builds in groups_def:
        fl = []
        for p in files:
            if fn(p.name):
                f = {'path': folder + p.name, 'bytes': p.stat().st_size}
                if builds:
                    f['builds'] = list(builds)
                    if p.name.startswith('lid-chinless.'):
                        f['builds'] = ['cl', 'lc']               # the light-strip chinless prints the chinless lid
                elif gid == 'shared' and p.name.split('.')[0] != 'midplate':
                    f['skip_builds'] = list(C.KEYLESS)           # the chinless builds use the midplate only
                fl.append(f)
                entries.append((folder + p.name, p))
                assert p.name not in used, p.name
                used.add(p.name)
        assert fl, gid
        groups.append({'id': gid, 'label': label, 'what': what, 'files': fl})
    left = [p.name for p in files if p.name not in used]
    assert not left, f'print/4.26/ files in no group: {left}'
    entries.append(('dummy/pcba-dummy.stl', dummy))
    for g in groups:
        if g['id'] == 'rod':
            for f in g['files']:
                f['skip_builds'] = list(C.KEYLESS)
    groups.append({'id': 'dummy', 'label': 'PCBA dummy', 'what': 'Component hulls fused to a 1.6 mm board: test-fit the '
                   'case without the real board', 'files': [{'path': 'dummy/pcba-dummy.stl', 'bytes': dummy.stat().st_size}]})
    zname = 'silkscreen-case-4.26.zip'
    zb = L.zip_bytes(entries)
    js = L.models_js(zb, size=SIZE, zip=zname, readme='README.txt')
    (out / C.fname('models', SIZE)).write_bytes(js.encode('ascii'))     # not write_text: Windows would add a CR
    return {'file': C.fname('models', SIZE), 'zip': zname, 'zip_bytes': len(zb), 'js_bytes': len(js.encode('ascii')),
            'readme': 'README.txt', 'groups': groups, 'raw_bytes': sum(p.stat().st_size for p in files) + dummy.stat().st_size,
            'note': 'One zip for the four builds: shared/ once, standard/ and light-strip/ each with its own tub, '
                    'chinless/ with its own tub and lid, light-strip-chinless/ with its own tub (it prints the '
                    'chinless lid).'}


BUILD_DIFF = {'cl': 'tub + lid differ, no bottom keys',       # the stage bar's tag on the chinless builds
              'lc': 'tub + lid differ, light strip, no bottom keys'}


def combine(root, out):
    import sc_lib as L
    W = out / '_work'
    ms = {b: load_npz(W / b / 'meshes.npz') for b in BUILDS}
    extras = {k[2:]: v for k, v in ms['std'].items() if k.startswith('X:')}
    for b in BUILDS:
        ms[b] = {k: v for k, v in ms[b].items() if not k.startswith('X:')}
    hs = {b: {n: L.mesh_hash(m) for n, m in ms[b].items()} for b in BUILDS}
    shared, differ, only_std, only_ls = L.split_shared(hs['std'], hs['ls'])
    core, per = [], []
    for n in shared:
        rule = C.node_rule(n)
        assert rule, n
        (per if rule[1] == 'build' else core).append(n)
    for n in differ + only_std + only_ls:
        rule = C.node_rule(n)
        if rule[1] == 'core':
            raise SystemExit(f'{n} must be a core node but differs between the builds')
        per.append(n)
    log('split: core', len(core), 'per-build', sorted(set(per)))
    # the printed parts against out/shared-parts.json (the project's own byte check)
    sp = json.loads((root / 'out' / 'shared-parts.json').read_text())
    stl_of = {'lid': 'lid_body', 'midplate': 'midplate', 'crank_M': 'crank-M', 'crank_T': 'crank-T', 'gate': 'gate',
              **{f'skey_{r}': f'skey_{r}' for r in ('SW1', 'SW4', 'SW5', 'SW7', 'SW10')},
              **{f'key_{r}': f'key_{r}' for r in C.BOTTOM_REFS}}
    for node, part in stl_of.items():
        assert sp[part]['same'] is True and node in core, (node, part)
    assert 'tub' in per and 'tub' not in sp, 'the tub must differ per build'
    rep = {'core': sorted(core), 'build': {b: sorted(n for n in per if n in ms[b]) for b in C.BUILDS},
           'extras': sorted(extras)}
    # the extra builds (chinless, light-strip chinless): what one has that core lacks or holds differently goes in its
    # own build file (tub, the chinless lid, its panel and ribbons); the core nodes it does not have are listed in its
    # data (meta.absent_nodes)
    rep['absent'] = {}
    for x in C.EXTRA_BUILDS[SIZE]:
        x_build = sorted(n for n in ms[x] if n not in core or hs[x][n] != hs['std'][n])
        x_absent = sorted(n for n in core if n not in ms[x])
        assert set(x_build) - set(per) <= {'lid'}, (x, 'core nodes that differ', sorted(set(x_build) - set(per)))
        assert not [n for n in ms[x] if C.node_rule(n) is None], (x, 'a node without a rule')
        assert 'tub' in x_build and 'lid' in x_build, (x, x_build)
        rep['build'][x] = x_build
        rep['absent'][x] = x_absent
        log(x, 'build', x_build, 'absent', x_absent)
    # the two chinless builds print one lid (lid-chinless): the same mesh in both build files
    assert hs['cl']['lid'] == hs['lc']['lid'], 'the light-strip chinless lid differs from the chinless lid'
    files = {}
    files[C.fname('core', SIZE)] = L.write_model(out / C.fname('core', SIZE), 'core', SIZE, None, {n: ms['std'][n] for n in rep['core']})
    for b in BUILDS:
        files[C.fname('build', SIZE, b)] = L.write_model(out / C.fname('build', SIZE, b), 'build', SIZE, b,
                                                          {n: ms[b][n] for n in rep['build'][b]})
    files[C.fname('extras', SIZE)] = L.write_model(out / C.fname('extras', SIZE), 'extras', SIZE, None, extras)
    log('model files', {k: v['bytes'] for k, v in files.items()})
    dl = downloads(root, out)
    files[dl['file']] = {'bytes': dl['js_bytes']}
    log('downloads', dl['zip'], dl['zip_bytes'], 'js', dl['js_bytes'])
    parts = {'shared': sorted(k for k, v in sp.items() if k != 'cross_project' and v['same']), 'per_build': ['tub']}
    datas = {}
    for b in BUILDS:
        D = json.loads((W / b / 'data.json').read_text())
        D['downloads'] = {k: dl[k] for k in ('file', 'zip', 'zip_bytes', 'js_bytes', 'readme', 'groups', 'note')}
        blk = D['cards']['strip']
        blk['diff'] = blk.get('diff') or [
            {'part': 'Tub (front shell)', 'same': False, 'std': 'tub-standard', 'ls': 'tub-light-strip',
             'text': 'Its own per build: the light-strip tub holds the plain GDEY0426T82 panel, the standard tub the FT01C'},
            {'part': 'Bottom keys', 'same': True, 'std': 'key-426', 'ls': 'key-426',
             'text': 'Shared (key-426): both faces sit at the same height'},
            {'part': 'Lid, midplate', 'same': True, 'text': 'Shared'},
            {'part': 'Cranks, rod, gate', 'same': True, 'text': 'Shared'},
            {'part': 'Panel and ribbons (not printed)', 'same': False,
             'text': 'FT01C with 3 ribbons (standard); plain GDEY0426T82 with its EPD FPC, and the strip in J3 (light strip)'}]
        blk['shared_parts'] = parts['shared']
        D['meta']['build_diff'] = BUILD_DIFF.get(b, 'tub differs')
        if b in rep['absent']:
            D['meta']['absent_nodes'] = rep['absent'][b]
        nodes = (set(rep['core']) - set(rep['absent'].get(b, []))) | set(rep['build'][b]) | set(rep['extras'])
        E = C.validate_data(D, C.fname('data', SIZE, b), nodes=nodes, strict=True)
        if E:
            raise SystemExit('\n'.join(['data does not validate:'] + E[:40]))
        L.dump(D, out / C.fname('data', SIZE, b))
        files[C.fname('data', SIZE, b)] = {'bytes': (out / C.fname('data', SIZE, b)).stat().st_size}
        datas[b] = D
    report = {'schema': C.SCHEMA, 'size': SIZE, 'generated': time.strftime('%Y-%m-%dT%H:%M:%S'),
              'nodes': rep, 'parts': parts, 'build_diff': 'tub differs',
              'build_diff_by': {x: BUILD_DIFF[x] for x in C.EXTRA_BUILDS[SIZE]},
              'display_nodes_differ': {b: sorted(n for n in rep['build'][b] if n.startswith(('panel_', 'ribbon_'))) for b in BUILDS},
              # every display node each build shows, core or per build (the 3.68 lists its core panel the same way)
              'display_nodes': {b: sorted(set(n for n in list(rep['core']) + list(rep['build'][b]) if n.startswith(('panel_', 'ribbon_'))))
                                for b in BUILDS},
              'files': {f: {'bytes': (out / f).stat().st_size, 'sha1': L.file_hash(out / f)} for f in files},
              'downloads': {k: dl[k] for k in ('zip', 'zip_bytes', 'js_bytes', 'raw_bytes')}}
    L.dump(report, out / 'adapter-426.json')
    return report, datas


def check(out):
    """Independent checks on the written files. Returns a list of (ok, text)."""
    import sc_lib as L
    R = []
    add = lambda ok, t: R.append((bool(ok), t))                                   # noqa: E731
    for f in [C.fname('core', SIZE), C.fname('extras', SIZE)] + [C.fname('build', SIZE, b) for b in BUILDS] \
            + [C.fname('data', SIZE, b) for b in BUILDS]:
        E = C.validate_file(out / f, decode=True)
        add(not E, f'{f}: validate_file ' + ('OK' if not E else '; '.join(E[:5])))
        add((out / f).stat().st_size <= C.LIMITS['file_bytes'], f'{f}: {(out / f).stat().st_size} bytes <= 16 MB')
    js = out / C.fname('models', SIZE)
    add(js.stat().st_size <= C.LIMITS['file_bytes'] and not any(c > 0x7F for c in js.read_bytes()),
        f'{js.name}: {js.stat().st_size} bytes, ASCII')
    core = json.loads((out / C.fname('core', SIZE)).read_text())
    ext = json.loads((out / C.fname('extras', SIZE)).read_text())
    total = sum((out / f).stat().st_size for f in os.listdir(out) if (out / f).is_file() and f != 'adapter-426.json')
    add(total < 36 * 1024 * 1024, f'4.26 share of the version: {total / 1e6:.1f} MB')
    for b in BUILDS:
        D = json.loads((out / C.fname('data', SIZE, b)).read_text())
        bm = json.loads((out / C.fname('build', SIZE, b)).read_text())
        nodes = (set(core['nodes']) - set(D['meta'].get('absent_nodes', []))) | set(bm['nodes']) | set(ext['nodes'])
        E = C.validate_data(D, b, nodes=nodes, strict=True)
        add(not E, f'data-426-{b}: validate_data strict with nodes: ' + ('OK' if not E else '; '.join(E[:5])))
        if b in C.KEYLESS:
            ab = set(D['meta'].get('absent_nodes', []))
            want = {f'key_{r}' for r in C.BOTTOM_REFS} | {f'nub_{r}' for r in C.BOTTOM_REFS} \
                | {f'swbody_{r}' for r in C.BOTTOM_REFS} | {'crank_M', 'crank_T', 'rod', 'gate', 'sw_T_body', 'sw_T_nub'}
            add(ab == want, f'{b}: leaves out exactly the bottom-key nodes: ' + ' '.join(sorted(ab)))
            add(D['keys'] is None and not any(c['kind'] == 'crank' for c in D['controls']) and 'key' not in
                {d['name'] for d in D['drawings']}, f'{b}: no keys block, crank controls or key drawing')
            add(abs(D['meta']['body'][1] - 117.4) < 0.01, f'{b}: body {D["meta"]["body"]} (117.4 tall)')
            add({'tub', 'lid'} <= set(bm['nodes']), f'{b}: build file ' + ' '.join(sorted(bm['nodes'])))
            need = set(C.required_drawings(SIZE, b))
            add(len(D['drawings']) >= 21 and not [d['name'] for d in D['drawings'] if not d['layers']]
                and need <= {d['name'] for d in D['drawings']},
                f'{b}: {len(D["drawings"])} drawings, none empty, all {len(need)} required present')
            if b in C.STRIP_BUILDS:
                st = D['cards']['strip']
                add(st['steps'] and not any('SW9' in s['b'] and 'no SW9' not in s['b'] for s in st['steps'])
                    and not any(s['t'] == 'The bottom keys' for s in st['steps']),
                    f'{b}: {len(st["steps"])} light-strip steps, none about SW9 or the bottom keys')
            continue
        K = D['keys']
        # kinematics: the rest rows (bottom-keys.json static) are checked by validate_keys; also the project's own
        # key_forces.travel (mechanics.json) per board delta, independently of this file's derived block
        worst = [0.0, 0.0]
        for row in D['cards']['keys']['mech_travel_crosscheck']:
            m, r = row['mech'], row['ref']
            worst[0] = max(worst[0], *(abs(a - c) for a, c in zip(m[:3], r[:3])))
            worst[1] = max(worst[1], *(abs(a - c) for a, c in zip(m[3:], r[3:])))
        add(worst[0] <= 0.011 and worst[1] <= 0.0021, f'{b}: derive() vs mechanics.json key_forces.travel (6 rows): worst '
            f'{worst[0]:.4f} deg, {worst[1]:.4f} mm (mechanics rounds to 0.01 deg / 0.001 mm)')
        n_rows = len(K['rest_rows'])
        add(n_rows == 6, f'{b}: {n_rows} independent rest rows from bottom-keys.json')
        for v in C.VARIANTS:
            d = K['derived'][v]
            add(abs(d['theta_rest']) < 1e-3, f'{b} {v}: nominal rest theta {d["theta_rest"]} (built at the nominal face)')
        nd = len(D['drawings'])
        empty = [d['name'] for d in D['drawings'] if not d['layers']]
        need = set(C.required_drawings(SIZE, b))
        add(nd >= 22 and not empty and need <= {d['name'] for d in D['drawings']},
            f'{b}: {nd} drawings, none empty, all {len(need)} required present')
        kd = next(d for d in D['drawings'] if d['name'] == 'key')
        add(set(C.KEY_DRAWING_LAYERS) <= {L_['id'] for L_ in kd['layers']} and {x['id'] for x in kd['beyond']} >= {'cheek', 'rail'},
            f'{b}: key drawing layers ' + ' '.join(L_['id'] for L_ in kd['layers']) + ' | beyond ' + ' '.join(x['id'] for x in kd['beyond']))
        add(set(D['presets']) >= set(C.required_presets(SIZE)), f'{b}: {len(D["presets"])} presets')
        mm = [m for m in D['controls'] if m['kind'] == 'flexure']
        add(len(mm) == 5, f'{b}: 5 side-key controls')
    # geometry behind the kinematics, from the shipped meshes (not from the formulas):
    Mc = L.read_model(out / C.fname('core', SIZE))
    K = json.loads((out / C.fname('data', SIZE, 'std')).read_text())['keys']
    big = (-50, 50, -50, 50)
    for v, nub in (('M', 'nub_SW8'), ('T', 'sw_T_nub')):
        g = L.cut(Mc[f'crank_{v}'], 'x', 0.0, big)
        front = g.bounds[2]
        want = K['switches'][v]['face_y']
        face = Mc[nub].bounds[0][1]
        add(abs(front - want) < 0.02 and abs(face - want) < 1e-3,
            f'crank_{v} nose front at theta 0: {front:.3f} (mesh), plunger face {face:.3f} ({nub}), face_y {want}')
    pad_top = K['pad']['c'][1] + K['pad']['r']
    kz = min(Mc[f'key_{r}'].bounds[0][2] for r in C.BOTTOM_REFS)
    add(abs(kz - pad_top) < 1e-3, f'keys rest on the pad crown: key underside z {kz:.3f}, crown top {pad_top:.3f}')
    # the instancing: crank_M moved to each key's X cuts like the build's own crank_SW* (the case project's STL)
    root = Path.cwd()
    worst = 0.0
    for r in C.BOTTOM_REFS:
        x = K['x'][r]
        own = L.load_stl(root / 'out' / 'standard' / f'crank_{r}.stl')
        for dx in (0.0, -4.5, 4.5):
            a = L.cut(L.moved(Mc['crank_M'], x), 'x', x + dx, big)
            bb = L.cut(own, 'x', x + dx, big)
            worst = max(worst, a.symmetric_difference(bb).area)
    add(worst < 1e-3, f'crank_M instanced at the 4 key X equals out/standard/crank_SW*.stl (sections at dx 0, +-4.5): '
        f'worst symmetric difference {worst:.2e} mm2')
    return R


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(DEFAULT_OUT))
    ap.add_argument('--child', choices=BUILDS)
    ap.add_argument('--reuse', action='store_true', help='keep _work from an earlier run (skip the children)')
    ap.add_argument('--check-only', action='store_true')
    a = ap.parse_args()
    out = Path(a.out)
    root = Path.cwd()
    if not (root / 'src' / 'keys.py').exists() or not (root / 'out' / 'standard').exists():
        raise SystemExit('run from the 4.26 project root (enclosures/case-426)')
    if a.child:
        child(a.child, out)
        return
    out.mkdir(parents=True, exist_ok=True)
    if not a.check_only:
        before = snapshot(root)
        for b in BUILDS:
            for ln in (root / 'out' / ENV[b] / 'build.log').read_text(errors='replace').splitlines():
                if 'Traceback' in ln or 'FAIL ' in ln:
                    raise SystemExit(f'out/{ENV[b]}/build.log reports a failure: {ln}')
        if not a.reuse:
            procs = {}
            for b in BUILDS:
                env = dict(os.environ, SILKSCREEN_VARIANT=ENV[b], PYTHONIOENCODING='utf-8')
                (out / '_work').mkdir(parents=True, exist_ok=True)
                lf = open(out / '_work' / f'child-{b}.log', 'w', encoding='utf-8')
                procs[b] = (subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), '--child', b, '--out', str(out)],
                                             cwd=root, env=env, stdout=lf, stderr=subprocess.STDOUT), lf)
            for b, (p, lf) in procs.items():
                rc = p.wait()
                lf.close()
                log(b, 'child exit', rc)
                if rc:
                    raise SystemExit((out / '_work' / f'child-{b}.log').read_text(encoding='utf-8')[-3000:])
        combine(root, out)
        after = snapshot(root)
        if before != after:
            raise SystemExit('the project\'s out/ changed during the run: ' + str(sorted(set(before) ^ set(after)))[:500])
        log('out/ unchanged (', len(before), 'files )')
    R = check(out)
    for ok, t in R:
        print(('  OK  ' if ok else '  FAIL') + ' ' + t)
    bad = [t for ok, t in R if not ok]
    print('ALL OK' if not bad else f'{len(bad)} FAILED')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
