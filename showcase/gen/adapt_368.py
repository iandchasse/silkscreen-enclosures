"""The 3.68" case (enclosures/case-368) for the Silkscreen showcase: meshes, section drawings, bottom-key
kinematics, card data and downloads for both builds, in the bundle's own file formats (../API.md, sc_contract.py).

Run from the 3.68 project's root (enclosures/case-368) with a Python 3.11 virtual environment made from its requirements.txt, after build.py and mechanics.py; nothing in the
project is written:

    <venv>/Scripts/python.exe -B ../../showcase/gen/adapt_368.py [--out DIR]

--out defaults to showcase/build/368/ (not in git), where bundle.py looks by default.

It starts one worker per build (SILKSCREEN_VARIANT=standard / light-strip: the project's modules read it when they
are imported, so one process cannot hold both builds), then merges what they wrote. Into <dir>:

  core-368.json         model file: nodes identical in both builds (split by mesh hash, checked against the
                        project's out/shared-parts.json)
  build-368-std.json    model file: the standard tub and its keys (key-x3std)
  build-368-ls.json     model file: the light-strip tub and its keys (key-x3ls)
  extras-368.json       model file: cmp_* (the X4 and its retro case, placed beside the standard build) and dummy_pcba
  data-368-std.json     data file (sc_contract.validate_data)
  data-368-ls.json
  models-368.js         the print zip for both builds: the repo's print/3.68/ (shared parts once), the rod jig
                        (print/rod-jig.*) and the PCBA dummy
  adapter-368.json      what was built and checked (node hashes per build, the split, sizes, timings)
  work/                 the workers' intermediate files (<b>.glb, <b>-data.json, <b>-log.txt)

    --only std|ls       run one worker only (no merge); --merge: merge existing work/ only; --jobs 1: workers in turn
"""
import argparse
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

GEN = Path(__file__).resolve().parent
REPO = GEN.parents[1]
PROJ = REPO / 'enclosures' / 'case-368'
PRINT = REPO / 'print' / '3.68'                     # build.write_print's per-part files
DEFAULT_OUT = REPO / 'showcase' / 'build' / '368'   # not in git; bundle.py's default --from368
sys.path.insert(0, str(GEN))

import sc_contract as C  # noqa: E402

SIZE = '368'
VAR_OF = {'std': 'standard', 'ls': 'light-strip'}
KEYS_NAME = {'std': 'key-x3std', 'ls': 'key-x3ls'}
# the display chip's and the manifest's panel label per build (the 4.26: 'FT01C touch + frontlight' / 'GDEY0426T82 (plain)')
PANEL_LABEL = {'std': '3.68&#x2033; EPD (bare)', 'ls': '3.68&#x2033; EPD + light strip'}
T0 = time.time()


def log(*a):
    print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)


def r3(v):
    return round(float(v), 3) + 0.0


def r4(v):
    return round(float(v), 4) + 0.0


def strip_over_std(P):
    """How much higher the light-strip tub's face stands than the standard tub's (0.8 since 2026-10, when the standard
    face went up STD_FACE_RAISE for its screen bevel; x3: 1.2). Both builds' params hold both faces."""
    return round(P.Z_FRONT_STRIP - (P.Z_FRONT_BASE + P.STD_FACE_RAISE), 3) + 0.0


def cap1(s):
    return s[:1].upper() + s[1:]


# ======================================================================================================================
# worker: one build, in its own process (the project's modules read SILKSCREEN_VARIANT on import)
# ======================================================================================================================
class Build:
    """Everything one build needs, loaded once: the project's modules, its out/ folder, meshes, reports."""

    def __init__(self, b):
        self.b = b
        os.environ['SILKSCREEN_VARIANT'] = VAR_OF[b]
        sys.path.insert(0, str(PROJ / 'src'))
        import variant
        assert variant.NAME == VAR_OF[b], (variant.NAME, b)
        import hw
        import params as P
        import sc_lib as L
        self.hw, self.P, self.L = hw, P, L
        self.out = PROJ / 'out' / VAR_OF[b]
        assert hw.OUT.resolve() == self.out.resolve(), hw.OUT
        self.json = {n: json.loads((self.out / f'{n}.json').read_text()) for n in
                     ('mechanics', 'crank', 'summary', 'interference', 'insertion', 'pcba-dummy')}
        self.hwm = L.HwMesh(hw)

    def stl(self, name):
        return self.L.load_stl(self.out / f'{name}.stl')


# The four screws (params.SCREWS, since 2026-10-13; until then H3, H4 and top): node names and seats. The bottom pair
# sit in the chin's corners (M2_CB_DEPTH 'corner'); the top-left screw takes the top one's counterbore.
SCREW_NODES = {'bottom-left': 'screw_bottom_left', 'bottom-right': 'screw_bottom_right', 'top': 'screw_top',
               'top-left': 'screw_top_left'}


def screw_node(key):
    return SCREW_NODES[key]


def screw_depth(P, key):
    return P.M2_CB_DEPTH['corner' if key.startswith('bottom') else 'top']


def screw_seat(P, key):
    return r3(P.Z_BACK + screw_depth(P, key))


def screw_list(P):
    return [{'id': k, 'node': screw_node(k), 'label': f'{k} screw', 'at': [r3(x), r3(y)], 'seat_z': screw_seat(P, k),
             'cb_depth': screw_depth(P, k), 'through_board': False} for k, (x, y) in P.SCREWS.items()]


def worker_meshes(B):
    """{node: trimesh} for this build (extras only for std). Printed parts are the build's own STLs, so parts shared
    by the builds are byte-identical and split into core by hash."""
    hw, P, L = B.hw, B.P, B.L
    import crank
    import panel
    import refs
    M = {}
    M['tub'] = B.stl('tub')
    M['lid'] = B.stl('lid_body')                      # never lid.stl: it has the side keys fused in
    for r in P.TAB_ROOTS:
        M[f'skey_{r}'] = B.stl(f'skey_{r}')
    M['midplate'] = B.stl('midplate')
    for r in P.KEY_REFS:
        M[f'key_{r}'] = B.stl(f'key_{r}')
    M['crank_M'] = B.stl('crank-M')                   # at X = 0, theta 0: the viewer places one per key
    M['crank_T'] = B.stl('crank-T')
    M['rod'] = B.stl('ref_rod')
    M['gate'] = B.stl('gate')                         # the side gate in the -X wall, the rod's left stop (crank.gate)
    # the TS365ZJ envelope (crank.ts365) at X = 0: shown with crank-T instead of the board's MJTP1117 bodies
    th, tp = crank.ts365(0.0)
    M['sw_T_body'], M['sw_T_nub'] = L.tess(th, 0.02, 0.3), L.tess(tp, 0.02, 0.3)
    t = time.time()
    moving = list(P.KEY_REFS) + hw.LEFT_SWITCHES + hw.RIGHT_SWITCHES + [hw.RESET]
    M.update(L.board_meshes(hw, moving, bodies=P.KEY_REFS, table=L.CATEGORY_368))
    log(f'board meshes {time.time() - t:.0f}s')
    pb = panel.body()                                 # glass, epl, ps: the bare 3.68" EPD, one node
    M['panel_epd'] = L.concat([L.tess(pb[k], 0.02, 0.2) for k in ('glass', 'epl', 'ps')])
    for k, m in panel.ribbons().items():
        M[f'ribbon_{k}'] = m
    bm = refs.battery_meshes()
    M['battery_cell'] = bm['battery_cell']
    M['battery_pcm'] = bm['battery_pcm']
    M['battery_leads'] = L.concat([bm['lead_red'], bm['lead_black']])
    M['battery_plug'] = bm['battery_plug']
    for key, (x, y) in P.SCREWS.items():              # four M2 x 8 socket head caps, seated in their counterbores
        M[screw_node(key)] = L.tess(L.socket_head_cq(x, y, screw_seat(P, key), length=P.SCREW_L), 0.03, 0.35)
    if B.b == 'std':
        import compare
        t = time.time()
        M.update(compare.meshes())                    # beside the standard build, front faces level with its face
        log(f'compare meshes {time.time() - t:.0f}s')
        M['dummy_pcba'] = B.stl('pcba-dummy')
    return M


# ---- section drawings ------------------------------------------------------------------------------------------------
# Rev K's drawings (the 4.26 project's src/showcase.py, deleted 2026-09-28; in git history), re-aimed at this case: the same names, this
# case's refs and windows. Z windows cover both builds (the light-strip face is the higher, 5.27), so a build switch keeps
# the framing. Refs differ from the 4.26: notes.ref says which part each drawing cuts.
ZW = (-7.6, 5.8)                                      # back (-7.235) to past the light-strip face (5.27)


def worker_drawings(B, M):
    hw, P, L = B.hw, B.P, B.L
    import body
    import crank
    import midplate
    import panel
    import tub as tubm
    hwm = B.hwm
    pcb = hwm('PCB')
    pb = panel.body()
    epd = L.concat([L.tess(pb['glass'], 0.01, 0.1), L.tess(pb['epl'], 0.01, 0.1)])
    film = L.tess(pb['ps'], 0.01, 0.1)
    disp = [('epd', 'glass', epd), ('film', 'film', film)]
    fps = hw.footprints()
    tabs = {t['ref']: t for t in body.side_tabs()}
    kx = hw.switch_plunger(C.DRAW_REF)['face'][0]
    tub, lid, mid = M['tub'], M['lid'], M['midplate']
    strip = {}
    if B.b == 'ls':
        for n in ('bar', 'leds', 'diodes', 'hinge', 'folded', 'folded_leds', 'neck', 'tail'):
            strip[n] = B.stl(f'ref_strip_{n}')
    D = []

    def add(name, axis, at, window, layers, beyond=None, notes=None):
        d = L.drawing(name, axis, at, window, layers, beyond, notes)
        D.append(d)
        return d

    # the bottom key through SW8: key, crank-M and crank-T at theta 0 (one shows per variant), the rod, the board's
    # MJTP1117 (sw_M / nub_M) and the TS365ZJ's envelope (sw_T / nub_T); beyond: a cheek, the +X hook, a rail ring
    th, tp = crank.ts365(kx)
    ring = next(((a + b) / 2 for k, a, b in tubm.rail_segments() if k == 'ring' and b < kx and b > kx - 8.0), kx - 6.0)
    rail = [-4.6, 0.2, -1.8, 4.2]
    d = add('key', 'x', kx, [-9.8, 4.2, -7.6, 8.8], [
        ('tub', 'case', tub), ('lid', 'case2', lid), ('pcb', 'pcb', pcb), ('key', 'key', M[f'key_{C.DRAW_REF}']),
        ('crank_M', 'crank', L.moved(M['crank_M'], kx)), ('crank_T', 'crank', L.moved(M['crank_T'], kx)),
        ('rod', 'rod', M['rod']), ('sw_M', 'part', hwm(C.DRAW_REF, 'body')), ('nub_M', 'nub', hwm(C.DRAW_REF, 'nub')),
        ('sw_T', 'part', L.tess(th, 0.01, 0.1)), ('nub_T', 'nub', L.tess(tp, 0.01, 0.1))],
        beyond=[('cheek', 'crank', L.moved(M['crank_M'], kx), kx - 4.5),
                ('hook', 'key', M[f'key_{C.DRAW_REF}'], kx + sum(P.KEY_HOOK['dx']) / 2)],
        notes={'ref': C.DRAW_REF, 'x': r4(kx), 'cheek_x': r4(kx - 4.5), 'hook_x': r4(kx + sum(P.KEY_HOOK['dx']) / 2),
               'ring_x': r4(ring), 'face_z': r3(P.Z_FRONT), 'chin_wall_y': r3(P.BOT_IN), 'slot_back_y': r3(P.KEY_SLOT['back']),
               'rail_y': [r3(v) for v in P.RAIL_Y], 'theta': 0.0, 'what': 'section through SW8, crank at theta 0'})
    rr = L.rings(L.cut(tub, 'x', ring, rail))          # the rail's ring beside the crank, dashed on the page
    if rr:
        d['beyond'].append({'id': 'rail', 'role': 'case', 'at': r3(ring), 'polys': rr})
    # side keys: SW7 (power, the left wall: this case's new key) in plan and elevation; SW1 from the side
    t7 = tabs['SW7']
    add('tab_plan', 'z', t7['face'][2], [-6.4, 8.4, 68.5, 90.0], [
        ('tub', 'case', tub), ('lid', 'case2', lid), ('tab', 'tab', M['skey_SW7']),
        ('sw', 'part', hwm('SW7', 'body')), ('nub', 'nub', hwm('SW7', 'nub'))],
        notes={'ref': 'SW7', 'side': t7['side'], 'root_y': t7['flex_root'], 'what': 'plan at the plunger height'})
    t1 = tabs['SW1']
    add('key_side', 'x', P.X1 - 0.5, [44.0, 72.2, -8.4, 3.6], [
        ('tub', 'case', tub), ('lid', 'case2', lid), ('tab', 'tab', M['skey_SW1'])],
        notes={'ref': 'SW1', 'root_y': t1['flex_root'], 'what': 'the key from the side, through the middle of its wall'})
    add('tab_elev', 'y', t7['face'][1], [-7.0, 12.7, ZW[0], ZW[1]], [
        ('tub', 'case', tub), ('tab', 'tab', M['skey_SW7']), ('lid', 'case2', lid), ('pcb', 'pcb', pcb),
        ('sw', 'part', hwm('SW7', 'body')), ('nub', 'nub', hwm('SW7', 'nub')), *disp, ('midplate', 'plate', mid)],
        notes={'ref': 'SW7', 'what': 'elevation through the plunger'})
    # a midplate detent (the right-hand bottom one), across its bump and in plan at the plate's mid-thickness
    dr = midplate.detents()[2][0]
    dyc = sum(dr['bump_y']) / 2
    zmid = (P.MID_REAR + P.DISP_REAR) / 2
    add('detent', 'y', dyc, [59.4, 62.8, 0.4, 4.6], [
        ('tub', 'case', tub), ('midplate', 'plate', mid), *disp, ('pcb', 'pcb', pcb)],
        notes={'wall': dr['wall'], 'bump_y': dr['bump_y'], 'strip_y': dr['strip_y']})
    add('detent_plan', 'z', zmid, [55.6, 63.4, dr['strip_y'][0] - 1.0, dr['bump_y'][1] + 1.3], [
        ('tub', 'case', tub), ('midplate', 'plate', mid)], notes={'z': r3(zmid)})
    # USB-C, in elevation and in plan
    u = body.usb()
    add('usb', 'y', u['yc'], [53.6, 69.6, ZW[0], 4.4], [
        ('tub', 'case', tub), ('lid', 'case2', lid), ('pcb', 'pcb', pcb), ('j1', 'metal', hwm('J1')),
        ('midplate', 'plate', mid)], notes={'ref': 'J1'})
    add('usb_plan', 'z', u['zc'], [53.0, 68.2, u['yc'] - 9.8, u['yc'] + 9.8], [
        ('tub', 'case', tub), ('lid', 'case2', lid), ('j1', 'metal', hwm('J1')), ('pcb', 'pcb', pcb),
        ('skey', 'tab', M['skey_SW1'])], notes={'ref': 'J1'})
    # reset pinhole
    rs = hw.switch_plunger(hw.RESET)
    add('reset', 'y', rs['face'][1], [46.0, 67.8, ZW[0], ZW[1]], [
        ('tub', 'case', tub), ('lid', 'case2', lid), ('pcb', 'pcb', pcb),
        ('sw', 'part', hwm(hw.RESET, 'body')), ('nub', 'nub', hwm(hw.RESET, 'nub')), *disp, ('midplate', 'plate', mid)],
        notes={'ref': hw.RESET})
    # the screen stack through a midplate spring, and the left bezel edge
    lstrip = [('strip', 'strip', strip['bar']), ('led', 'led', strip['leds'])] if strip else []
    sx, sy, _ = midplate.SPRINGS[0]                   # (8.5, 11.5): across the bottom border, where the lip is
    add('stack', 'x', sx, [sy - 9.5, sy + 9.5, -0.6, ZW[1]], [
        ('tub', 'case', tub), *disp, ('midplate', 'plate', mid), ('pcb', 'pcb', pcb)],
        notes={'spring': [sx, sy], 'what': 'across the bottom border, through a midplate spring'})
    add('bezel', 'y', 60.0, [-4.1, 3.9, 1.0, ZW[1]], [
        ('tub', 'case', tub), *disp, ('midplate', 'plate', mid), ('pcb', 'pcb', pcb), *lstrip],
        notes={'what': 'the left border at y 60'})
    # the display FPC: over the glass edge, down the board's slot, along the back into J2
    add('ribbon', 'x', 28.0, [-3.0, 25.5, ZW[0], ZW[1]], [
        ('tub', 'case', tub), ('lid', 'case2', lid), ('pcb', 'pcb', pcb), ('j2', 'part', hwm('J2')), *disp,
        ('midplate', 'plate', mid), ('key', 'key', M['key_SW8']), ('ribbon', 'ribbon', M['ribbon_main'])],
        notes={'ref': 'J2'})
    # the battery in the lid: down the cell's middle (through J7, the microSD socket it sits over), and in plan at
    # the cell's mid-thickness (the lip, the end stop, the lead to J5)
    bx = sum(P.BATT['x']) / 2
    add('bay', 'x', bx, [50.0, 99.4, ZW[0], 4.4], [
        ('tub', 'case', tub), ('lid', 'case2', lid), ('cell', 'cell', M['battery_cell']), ('pcm', 'part', M['battery_pcm']),
        ('leads', 'lead', M['battery_leads']), ('midplate', 'plate', mid), *disp, ('pcb', 'pcb', pcb), ('j7', 'part', hwm('J7'))],
        notes={'ref': 'J7', 'x': r3(bx), 'what': 'down the middle of the cell'})
    zc = sum(P.BATT['z']) / 2
    add('bay_plan', 'z', zc, [2.0, 47.0, 50.0, 99.4], [
        ('lid', 'case2', lid), ('cell', 'cell', M['battery_cell']), ('pcm', 'part', M['battery_pcm']),
        ('leads', 'lead', M['battery_leads']), ('plug', 'part', M['battery_plug']), ('j5', 'part', hwm('J5'))],
        beyond=[('leads_beyond', 'lead', M['battery_leads'], -1.2), ('j5_beyond', 'part', hwm('J5'), -1.2)],
        notes={'z': r3(zc), 'what': 'plan at the cell mid-thickness'})
    # fasteners: the bottom-left corner screw (the drawing keeps the name 'clamp'; until 2026-10-13 it cut the H3
    # screw, which clamped the board), the board's snap post at H6, the top screw. The two screw drawings start below
    # the back face (ZW does not: it predates LID_DROP), so the heads in their counterbores show whole.
    zb = r3(P.Z_BACK - 0.5)
    cx, cy = P.SCREWS['bottom-left']
    add('clamp', 'x', cx, [r3(P.Y0 - 0.6), 3.4, zb, ZW[1]], [
        ('tub', 'case', tub), ('lid', 'case2', lid), ('pcb', 'pcb', pcb), ('rod', 'rod', M['rod']),
        ('screw', 'metal', M[screw_node('bottom-left')])],
        notes={'ref': 'bottom-left', 'u': r3(cy), 'mirror': 'bottom-right', 'rod_axis': [r3(v) for v in P.ROD_AXIS],
               'what': "the bottom-left corner screw, through a lid post into the tub's corner block, below the rod"})
    h6 = fps['H6']['cad']
    py = h6[1] + P.BOARD_SNAP['slot'] / 2 + 0.25       # beside the snap post's slot, so its fingers are cut
    add('pin', 'y', py, [h6[0] - 6.5, h6[0] + 6.5, ZW[0], ZW[1]], [
        ('tub', 'case', tub), ('lid', 'case2', lid), ('pcb', 'pcb', pcb), ('midplate', 'plate', mid), *disp],
        notes={'ref': 'H6', 'hole_y': h6[1], 'what': 'the board snapped onto a midplate post, the lid post behind it'})
    add('top', 'x', P.TOP_SCREW[0], [84.0, 99.4, zb, ZW[1]], [
        ('tub', 'case', tub), ('lid', 'case2', lid), ('pcb', 'pcb', pcb), ('screw', 'metal', M['screw_top']),
        *disp, ('midplate', 'plate', mid)], notes={'ref': 'top screw'})
    # the tub-to-lid joint: the tongue on the left wall, the tongue behind SW4's key, the top wall over the cell,
    # a latch over SW1's key
    jl = [('tub', 'case', tub), ('lid', 'case2', lid), ('pcb', 'pcb', pcb)]
    add('joint_tongue', 'y', 10.0, [-4.8, 6.4, ZW[0], 1.2], jl)
    add('joint_at_tab', 'y', 83.0, [58.8, 65.8, ZW[0], 2.6], jl + [('tab', 'tab', M['skey_SW4'])], notes={'ref': 'SW4'})
    add('joint_top', 'x', 20.0, [89.0, 99.4, ZW[0], 1.0], jl + [('cell', 'cell', M['battery_cell'])])
    sy = P.SNAPS['right'][2]
    add('joint_latch', 'y', sy, [55.6, 65.9, ZW[0], 3.3], jl + [('tab', 'tab', M['skey_SW1']), ('midplate', 'plate', mid)],
        notes={'ref': 'SW1', 'latch_y': sy})
    if strip:
        # the light strip: through LED D4 (the light-strip page's cut), through the folded top pair, and the neck
        sl = [('tub', 'case', tub), ('strip', 'strip', strip['bar']), ('led', 'led', strip['leds']),
              ('diodes', 'part', strip['diodes']), *disp, ('midplate', 'plate', mid), ('pcb', 'pcb', pcb)]
        add('strip_led', 'y', 49.7, [-4.6, 6.0, 0.8, ZW[1]], sl, notes={'ref': 'D4', 'what': 'through LED D4'})
        add('strip_fold', 'y', 79.5, [-4.6, 6.0, 0.8, ZW[1]], sl + [
            ('hinge', 'strip', strip['hinge']), ('folded', 'strip', strip['folded']), ('folded_led', 'led', strip['folded_leds'])],
            notes={'what': 'through the folded top pair'})
        nx = sum(P.STRIP_GAP['x']) / 2
        add('strip_neck', 'x', nx, [-9.8, 10.0, -6.0, ZW[1]], [
            ('tub', 'case', tub), ('lid', 'case2', lid), ('pcb', 'pcb', pcb), *disp, ('midplate', 'plate', mid),
            ('key', 'key', M['key_SW9']), ('neck', 'strip', strip['neck']), ('tail', 'strip', strip['tail'])],
            notes={'x': r3(nx), 'what': 'the neck over the glass edge and down the slot'})
    return D


# ---- the bottom keys: geometry for the page's exact kinematics, independent rest rows, mechanics -----------------
def keys_block(B):
    """sc_contract's keys block from crank.py's own numbers (P.ROD_AXIS, CRANK_CROWN, CRANK_NOSE_C; note crank.py's
    rest_theta(face_y, variant) takes its arguments the other way round from the 4.26's keys.rest_theta(variant, face)).
    The rest rows are crank.json's (build.py's checker), NOT recomputed here: the validator compares them with the
    reference kinematics, so they are an independent check."""
    hw, P = B.hw, B.P
    import crank
    mech, cj = B.json['mechanics'], B.json['crank']
    kf, pre, cs = mech['key_forces'], mech['key_preload'], mech['crank_stress']
    x = {r: r4(hw.switch_plunger(r)['face'][0]) for r in C.BOTTOM_REFS}
    sp = hw.switch_plunger(C.DRAW_REF)
    body = sp['body']
    T = P.TS365
    K = {
        'refs': list(C.BOTTOM_REFS), 'x': x, 'draw_ref': C.DRAW_REF,
        'rod': {'yz': [r4(v) for v in P.ROD_AXIS], 'd': P.ROD_D, 'd_range': list(P.ROD_D_RANGE), 'cut': P.ROD_CUT,
                'cut_tol': P.ROD_CUT_TOL, 'span': [r3(v) for v in P.ROD_SPAN], 'hole_d': P.ROD_HOLE_D,
                'end_play': [r3(P.ROD_SPAN[1] - P.ROD_SPAN[0] - P.ROD_CUT - P.ROD_CUT_TOL),
                             r3(P.ROD_SPAN[1] - P.ROD_SPAN[0] - P.ROD_CUT + P.ROD_CUT_TOL)],
                'gate': 'printed side gate',
                'material': '1.75 mm PLA filament'},
        'axis': [1, 0, 0], 'theta_built': 0.0,
        'pad': {'c': [r4(v) for v in P.CRANK_CROWN[0]], 'r': P.CRANK_CROWN[1]},
        'nose': {'r': P.CRANK_NOSE_R, 'c': {v: [r4(c) for c in P.CRANK_NOSE_C[v]] for v in C.VARIANTS}},
        'switches': {
            # MJTP1117: sc_contract's one definition (the 4.26 spec envelope). The board STEP's own numbers are
            # checked against it below; its plunger probe is only 0.3 deep, so it cannot give the housing's front.
            'M': {'part': 'MJTP1117', 'crank': 'crank-M', 'label': 'APEM MJTP1117 boards', 'maker': 'APEM',
                  'stem': 'black', **C.switch_geom('M'),
                  'travel': {'click': 0.25, 'bottom': 0.45}, 'force_N': list(P.SWITCH_FORCE['MJTP1117'])},
            'T': {'part': 'TS365ZJ', 'crank': 'crank-T', 'label': 'SHOU HAN TS365ZJ (every JLC board)',
                  'maker': 'SHOU HAN', 'stem': 'white', 'face_y': T['tip_y_nom'], 'face_worst_y': T['tip_y'][0],
                  'nub_z': list(T['plunger_z_nom']), 'nub_z_worst': list(T['plunger_z_worst']),
                  'housing_yz': [T['housing_y'], T['body_z'][0], 6.0, T['body_z'][1]], 'housing_half_x': T['housing_half_x'],
                  'nub_yz': [T['tip_y_nom'], T['plunger_z_nom'][0], r3(T['housing_y'] + 0.2), T['plunger_z_nom'][1]],
                  'nub_half_x': T['plunger_half_x'],
                  'travel': {'click': 0.25, 'bottom': 0.45}, 'force_N': list(P.SWITCH_FORCE['TS365ZJ'])}},
        'default_variant': C.DEFAULTS['variant'],
    }
    # this project's own switch numbers against sc_contract's one definition of each (the same board as the 4.26)
    step_m = {'face_y': P.PLUNGER_Y, 'nub_z': [r3(sp['nub'][4]), r3(sp['nub'][5])],
              'housing_half_x': r3((body[1] - body[0]) / 2), 'nub_half_x': r3((sp['nub'][1] - sp['nub'][0]) / 2)}
    g = C.SWITCH_GEOM['M']
    assert abs(sp['nub'][2] - g['face_y']) < 0.01 and abs(body[4] - g['housing_yz'][1]) < 0.01, (sp, body)
    for k, v in step_m.items():
        vv, gg = (v if isinstance(v, list) else [v]), (g[k] if isinstance(g[k], list) else [g[k]])
        assert all(abs(a - b) < C.SWITCH_GEOM_TOL + 1e-9 for a, b in zip(vv, gg)), ('MJTP STEP vs SWITCH_GEOM', k, v, g[k])
    bad = C.switch_geom_diff(K['switches']['T'], 'T')
    assert not bad, ('params.TS365 vs sc_contract.SWITCH_GEOM', bad)
    K['derived'] = {v: C.derive(K, v) for v in C.VARIANTS}
    # board tolerance: crank.json rest['SW8']['<part> <+d>'] = {theta, key_lift}; +d moves the plunger face +Y,
    # key_lift is +Z (up), so key_dz (mm down) = -key_lift
    rows = []
    for k, r in cj['rest'][C.DRAW_REF].items():
        part, dy = k.split()
        v = {'MJTP1117': 'M', 'TS365ZJ': 'T'}[part]
        rows.append({'variant': v, 'face_dy': float(dy) + 0.0, 'theta': r['theta'] + 0.0, 'key_dz': r4(-r['key_lift']),
                     'source': f'crank.json rest {C.DRAW_REF} {k}'})
    K['rest_rows'] = sorted(rows, key=lambda r: (r['variant'], r['face_dy']))
    # the same rows through the whole press (mechanics.key_travel): proud = the key's top over this build's face
    tol = []
    for k, r in kf['travel'].items():
        part, dy = k.split()
        tol.append({'variant': {'MJTP1117': 'M', 'TS365ZJ': 'T'}[part], 'face_dy': float(dy) + 0.0, **r})
    K['tolerance'] = sorted(tol, key=lambda r: (r['variant'], r['face_dy']))
    # the same check the rows get from the validator, done here too (crank.py's own functions, both argument orders)
    for r in K['rest_rows']:
        face = K['switches'][r['variant']]['face_y'] + r['face_dy']
        th = crank.rest_theta(face, r['variant'])                  # (face_y, variant): x3's order
        assert abs(th - r['theta']) < 0.006 and abs(-crank.key_lift(th) - r['key_dz']) < 0.0006, (r, th)
    i62 = kf['press_y'].index(-6.2)
    ff = kf['mu_0.3']['finger_force_N']
    arm_in = abs(P.ROD_AXIS[0] - P.CRANK_CROWN[0][0])
    arm_out = abs(P.ROD_AXIS[1] - P.CRANK_NOSE_C['M'][1])
    K['forces'] = {'lever': {'input_arm': r3(arm_in), 'output_arm': r3(arm_out), 'ratio': kf['lever_ratio'],
                             'no_friction_ratio': kf['no_friction_ratio']},
                   'finger_N': {'M': [ff['MJTP 1.27'][i62], ff['MJTP 1.86'][i62]], 'T': [ff['TS365 1.96'][i62], ff['TS365 2.94'][i62]]},
                   'press_y': -6.2, 'mu': 0.3, 'press_ys': sorted(kf['press_y']),
                   # sc_contract.force_table's shape: {"MJTP 1.27": {"mu_0.3": [N per press_ys]}}
                   'table': C.force_table([(k.split()[0], float(k.split()[1]), mu, y, kf[f'mu_{mu:g}']['finger_force_N'][k][i])
                                           for k in ff for mu in (0.3, 0.45) for i, y in enumerate(kf['press_y'])])[0],
                   'guide_length_mm': kf['guide_length_mm'], 'top_edge_factor': kf['mu_0.3']['top_edge_factor'],
                   'rocker_for_comparison': kf.get('rocker_for_comparison'),
                   'source': 'mechanics.json key_forces (mu 0.3, press at y -6.2)'}
    # the hook keys (test 2): mechanics.json key_hooks (and key_preload's rest load, gravity only), params' hook numbers
    kh = mech['key_hooks']
    hp, po = kh['params'], kh['pull_out']
    K['hooks'] = {'W_OUT_mm': hp['W_OUT'], 'hook_dx': list(hp['hook_dx']), 'hook_h_mm': P.KEY_HOOK['h'],
                  'hook_tip_y': hp['hook_tip'], 'hook_z_rest': list(hp['hook_z_at_rest']), 'hook_lead_mm': hp['hook_lead'],
                  'root_mm': P.KEY_ROOT, 'slot_dx': list(hp['slot_dx']), 'slot_back_y': hp['slot_back'],
                  'slot_roof_z': hp['slot_roof'], 'face_down_free_travel_mm': list(kh['window']['face_down_free_travel_mm']),
                  'rest_load_on_plunger_N': pre['rest_load_on_plunger_N'], 'key_mass_g': pre['key_mass_g'],
                  'wall_behind_slot_mm': kh['walls']['least_wall_behind_the_slot']['wall']['mm'],
                  'above_roof_mm': kh['walls']['least_above_the_roof_at_the_back']['mm'],
                  'tilt_on_hooks_deg': kh['tilt']['on_the_hooks_deg'],
                  'pull_out': {'pull_N': po['at_N'], 'bearing_mm': po['bearing_gross_mm'], 'bearing_net_mm': po['flat_bearing_net_mm'],
                               'root_shear_MPa': po['root_shear_MPa'], 'root_bending_MPa': po['root_bending_in_layer_MPa']},
                  'hooks_to_crank_min_mm': min(r['min_gap'] for r in kh['crank']['rows'].values()),
                  'key_proud_at_rest_mm': pre['key_proud_at_rest_mm'],
                  'key_proud_with_ts365_tip_tolerance_mm': pre['key_proud_with_ts365_tip_tolerance_mm'],
                  'key_proud_at_click_min_mm': pre['key_proud_at_click_min_mm'],
                  'key_proud_at_bottom_min_mm': pre['key_proud_at_bottom_min_mm'],
                  'wrong_variant_key_shift_mm': pre['wrong_variant_key_shift_mm'],
                  'source': 'mechanics.json key_hooks (and key_preload: the rest load, gravity only); params KEY_HOOK / KEY_ROOT'}
    K['rod_check'] = {'press_N': cs['press_N'], 'bending_MPa': cs['rod']['bending_MPa'],
                      'deflection_um': cs['rod']['deflection_um'], 'shear_MPa': cs['rod']['shear_MPa'],
                      'plunger_N': cs['plunger_N'], 'pin_N': cs['pin_N'], 'crossbar_torsion_plus_shear_MPa':
                      r3(cs['crossbar']['torsion_MPa'] + cs['crossbar']['shear_MPa']),
                      'switch_rating_note': cs.get('switch_rating_note'),
                      'source': 'mechanics.json crank_stress'}
    K['checks'] = keys_checks(B)
    K['instances'] = {'crank': {'M': 'crank_M', 'T': 'crank_T'}, 'switch': {'T': ['sw_T_body', 'sw_T_nub'], 'M': 'board'}}
    K['stop_above_rest_mm'] = r3(max(mech['key_sweep']['lifts_mm']))     # the hooks meet the slots' roof (W_OUT)
    assert abs(K['stop_above_rest_mm'] - P.KEY_W_OUT) < 1e-6, ('key_sweep stop vs KEY_W_OUT', K['stop_above_rest_mm'])
    K['key'] = {'name': KEYS_NAME[B.b], 'top_over_face': P.KEY_TOP_OVER_FACE, 'tall': r3(B.json['summary']['keys_top_z'] - (P.KEY_PUSHER['z0'])),
                'half': P.KEY_HALF, 'chin_moved_mm': 1.0, 'hook_dx': list(P.KEY_HOOK['dx'])}
    return K


def keys_checks(B):
    """crank.json (build.py's crank_checks) and mechanics' key checks, as {id, label, ok, value, detail, source}."""
    mech, cj = B.json['mechanics'], B.json['crank']
    out = [{'id': 'crank_failures', 'label': 'Crank, key, rod and switch: no failures in the static, sweep and path checks',
            'ok': not cj['failures'], 'value': len(cj['failures']), 'detail': '; '.join(cj['failures'])[:400],
            'source': 'crank.json failures'}]
    acc = cj['accepted_findings']
    out.append({'id': 'crank_accepted', 'label': 'Accepted finding: a wrong-variant crank held at 0&deg; while the board goes in',
                'ok': True, 'value': len(acc),
                'detail': 'A crank-M with a worst-case TS365ZJ, held at theta 0 (not a free-hang angle): the fix is not '
                          'to hold the cranks up.' if acc else '', 'source': 'crank.json accepted_findings',
                'status': 'accepted'})
    # clearances only (not the crown/pusher overlap rows, whose 0 is the pass; 9.0 = not tracked in -13..+16)
    sw = [(p['min'], ref, pair) for ref, pairs in cj['sweep'].items() for pair, p in pairs.items()
          if isinstance(p, dict) and p.get('min') is not None and 'overlap' not in pair and p['min'] < 9.0]
    if sw:
        m = min(sw)
        out.append({'id': 'crank_sweep', 'label': 'Every crank swept from -13&deg; to +16&deg; with its key on the crown: '
                    'nothing it passes is touched', 'ok': m[0] > 0 and not any('sweep' in f for f in cj['failures']),
                    'value': m[0], 'detail': f'closest: {m[2]} at {m[1]}, {m[0]} mm (the spec asks 0.06 there)',
                    'source': 'crank.json sweep'})
    pa = cj['paths']
    out.append({'id': 'rod_path', 'label': 'The rod slides in along its axis through the side wall, rings and cranks',
                'ok': bool(pa['rod'].get('ok')), 'source': 'crank.json paths.rod'})
    ki = pa['key_in']
    out.append({'id': 'key_in', 'label': 'Each key goes in from inside, its hooks up their slots, and only the hooks meet the '
                'tub, under the roof, at the stop',
                'ok': all(r.get('ok', True) for r in ki.values()), 'source': 'crank.json paths.key_in'})
    xg = cj['x_gaps']
    out.append({'id': 'x_gaps', 'label': 'Side gaps: cheeks to their slots and webs, caps to their openings',
                'ok': min(xg.values()) > 0, 'value': min(xg.values()), 'detail': ', '.join(f'{k} {v}' for k, v in xg.items()),
                'source': 'crank.json x_gaps'})
    out.append({'id': 'logo', 'label': 'The chin wordmark stays clear of the cranks&rsquo; slots',
                'ok': bool(cj['logo'].get('ok')), 'value': cj['logo'].get('min_plastic_mm'), 'source': 'crank.json logo'})
    for blk, name in (('key_forces', 'forces'), ('key_preload', 'rest load'), ('key_hooks', 'hooks'), ('key_fit', 'key fit'),
                      ('crank_stress', 'stress'), ('key_sweep', 'key sweep')):
        ch = mech[blk].get('checks', {})
        out.append({'id': f'mech_{blk}', 'label': f'Mechanics, {name}: ' + ', '.join(k.replace('_', ' ') for k in ch),
                    'ok': all(ch.values()), 'value': f'{sum(ch.values())} of {len(ch)}', 'source': f'mechanics.json {blk}.checks'})
    # the side gate: its way in, the cam and the flat bearing (crank.json gate), then its loads (mechanics.json gate)
    g = cj['gate']
    out.append({'id': 'gate_fit', 'label': 'The gate drops into its slot clear of the walls, the lid and the board, its '
                'bevel cams the rod home, and its flange bears flat on both lips',
                'ok': bool(g['path'].get('ok')) and bool(g['cam'].get('ok')) and all(r.get('ok') for r in g['bearing'].values()),
                'value': g['cam']['flush']['seated_tail_x'],
                'detail': f"to the walls {g['path']['seated_to_walls']} mm, to the lid {g['path']['installed_to_lid']} "
                          f"({g['path']['on_sliver']['to_lid']} on the sliver); seated tail at x {g['cam']['flush']['seated_tail_x']}; "
                          f"a tail 0.2 proud stops the gate {g['cam']['0.2 proud']['stops_proud_mm']} mm proud; flat bearing "
                          f"at least {min(r['min_side'] for r in g['bearing'].values())} mm a side",
                'source': 'crank.json gate'})
    gc, gl = mech['gate']['checks'], mech['gate']['loads']
    stiff = gl['stiff-stop sensitivity']
    out.append({'id': 'mech_gate', 'label': 'Mechanics, gate: ' + ', '.join(k.replace('_', ' ') for k in gc),
                'ok': all(v is True or v in ('PASS', 'ACCEPTED', 'reported') for v in gc.values()),
                'value': f"{sum(v is True or v == 'PASS' for v in gc.values())} of {len(gc)}",
                'detail': '; '.join(f'{k}: {v}' for k, v in gc.items()) + f" (the stiff stop: lip SF "
                          f"{stiff['centred']['lip_SF_25']} centred, {stiff['min_SF']['lip_SF_25']} at the full shift, "
                          f"on 25 MPa)", 'source': 'mechanics.json gate.checks'})
    return out


def controls_block(B):
    hw, P = B.hw, B.P
    import body
    rows = []
    for r in C.BOTTOM_REFS:
        rows.append({'id': r, 'label': cap1(hw.SWITCH_ROLES[r]), 'kind': 'crank', 'ref': r, 'node': f'key_{r}',
                     'crank': f'crank_{r}', 'plunger': f'nub_{r}',
                     'pivot': [r4(hw.switch_plunger(r)['face'][0]), *[r4(v) for v in P.ROD_AXIS]], 'axis': [1, 0, 0]})
    sk = B.json['mechanics']['springs']['side_keys']
    for t in body.side_tabs():
        s = sk[t['ref']]
        xo = P.X1 if t['side'] > 0 else P.X0
        rows.append({'id': t['ref'], 'label': cap1(hw.SWITCH_ROLES[t['ref']]), 'kind': 'flexure', 'ref': t['ref'],
                     'node': f"skey_{t['ref']}", 'plunger': f"nub_{t['ref']}", 'plunger_axis': [-t['side'], 0, 0],
                     'pivot': [r4(xo - t['side'] * P.TAB_T / 2), t['flex_root'], 0.0], 'axis': [0, 0, 1],
                     'sign': int(t['side'] * math.copysign(1, t['y_free'] - t['flex_root'])),
                     'length': r3(abs(t['face'][1] - t['flex_root'])), 'gap': s['gap_mm'],
                     'click_travel': s['pad_travel_to_click_mm'], 'max_travel': s['stop_travel_mm'],
                     'force_click_N': s['finger_force_N']['pad_centre'], 'k_N_per_mm': s['k_N_per_mm']})
    rx, ry, rz = hw.switch_plunger(hw.RESET)['face']
    rows.append({'id': hw.RESET, 'label': 'Reset (pin)', 'kind': 'pin', 'ref': hw.RESET, 'plunger': f'nub_{hw.RESET}',
                 'plunger_axis': [-1, 0, 0], 'pin_from': [r3(P.X1 + 10.0), r4(ry), r4(rz)], 'pin_to': [r4(rx), r4(ry), r4(rz)],
                 'click_travel': 0.25, 'max_travel': 0.45, 'hole_d': 1.2})
    # the plug as the 4.26 adapter has it (the same J1 and divot): from / to are the tip of the plug's shell, 9 mm out
    # and seated; the overmold stops on the tub's floor
    u = body.usb()
    import tub as tubm
    uf = tubm.usb_features()
    spare = P.USB_PLUG_SPARE
    seat_face = max(uf['face_x'], u['mouth_x'] + spare)
    tip_in = seat_face - (6.20 + spare)
    rows.append({'id': 'usb', 'label': 'USB-C plug', 'kind': 'plug', 'axis': [-1, 0, 0],
                 'from': [r3(tip_in + 9.0), r3(u['yc']), r3(u['zc'])], 'to': [r3(tip_in), r3(u['yc']), r3(u['zc'])],
                 'insert_mm': 9.0, 'shell_len': r3(6.20 + spare), 'seat_face_x': r3(seat_face), 'overmold': [11.0, 5.6]})
    return rows


# ---- presets: the full camera table for this case (Rev K's 18 + strip, zstack, boardprep) -----------------------
def presets_block(B):
    hw, P = B.hw, B.P
    kx = hw.switch_plunger(C.DRAW_REF)['face'][0]
    yc = (P.Y0 + P.Y1) / 2
    sw4 = hw.switch_plunger('SW4')['face']
    u = __import__('body').usb()
    rs = hw.switch_plunger(hw.RESET)['face']
    lat = P.SNAPS['right'][2]
    bx = sum(P.BATT['x']) / 2
    by = sum(P.BATT['y']) / 2
    zf = P.Z_FRONT
    ls = B.b == 'ls'
    v = lambda *a: [r3(x) for x in a]
    pr = {
        'home': {'cam': v(95, -138, 125), 'tgt': v(30, yc, -1), 'fit': True, 'tag': 'Assembled',
                 'cap': '<b>Assembled.</b> Screen side up; the four bottom keys sit in the chin below the display.'},
        'assembly': {'cam': v(158, -106, -35), 'tgt': v(30, yc, -38), 'fit': True, 'tag': 'Assembly',
                     'cap': '<b>Assembly.</b> Parts enter the face-down tub from behind, in this order.'},
        'keys': {'cam': v(kx + 58, -34, 26), 'tgt': v(kx, -1.5, 0.5), 'sec': ['x', r4(kx), False],
                 'focus': ['keys', 'rod', 'tub', 'pcba', 'lid'], 'press': C.DRAW_REF, 'highlight': ['key_*', 'crank_*'],
                 'tag': 'Bottom keys',
                 'cap': '<b>Bottom keys.</b> Cut through SW8. The key slides straight down onto the crank&rsquo;s crowned pad; '
                        'the crank turns on the filament rod and its nose pushes the switch plunger along the board.'},
        'tabs': {'cam': v(96, sw4[1] - 42, 42), 'tgt': v(61, sw4[1], -2), 'sec': ['z', r4(sw4[2]), False],
                 'focus': ['tub', 'pcba', 'lid'], 'press': True, 'highlight': ['skey_*'], 'tag': 'Side keys',
                 'cap': '<b>Side keys.</b> Cut at plunger height. Each key (highlighted) is part of the lid: its wall, cut '
                        'free, bends from its root and rises into a slot in the tub. Drag &ldquo;Press buttons&rdquo;.'},
        'keylid': {'cam': v(208, 19, 66), 'tgt': v(58, yc, 1.5), 'fit': True, 'show': ['lid'], 'press': True,
                   'highlight': ['skey_*'], 'tag': 'Side keys on the lid',
                   'cap': '<b>The lid on its own.</b> The three side keys (highlighted) stand on its back face, the face it '
                          'prints on, and rise past the parting line.'},
        'usb': {'cam': v(125, u['yc'] - 29, 22), 'tgt': v(62, u['yc'], -2), 'focus': ['tub', 'lid', 'pcba'], 'press': 'usb',
                'tag': 'USB-C',
                'cap': '<b>USB-C.</b> A divot for the plug&rsquo;s overmold, floored by the tub itself: a 0.5 mm wall round the '
                       'port, 0.62 mm in front of J1&rsquo;s mouth.'},
        'reset': {'cam': v(118, rs[1] - 24, 16), 'tgt': v(61, rs[1], rs[2]), 'focus': ['tub', 'lid', 'pcba'],
                  'press': hw.RESET, 'tag': 'Reset',
                  'cap': f'<b>Reset.</b> The countersunk 1.2 mm pinhole sits {u["yc"] - rs[1]:.0f} mm below the port, straight onto SW11.'},
        'stack': {'cam': v(-34, 44, 22), 'tgt': v(-1, 60, 2.8), 'sec': ['y', 60.0, True],
                  'focus': ['midplate', 'display', 'pcba', 'tub'] + (['strip'] if ls else []), 'tag': 'Screen stack',
                  'cap': '<b>Screen stack.</b> Cut at y = 60 across the left border: the midplate&rsquo;s springs keep the '
                         'panel&rsquo;s front on the lip.' + (' Here the light strip&rsquo;s bar lies beside the panel.' if ls else '')},
        'detent': {'cam': v(63.5, 16.9, 34), 'tgt': v(60.4, 20.0, 2.2), 'up': [0, 1, 0], 'sec': ['z', 2.2, False],
                   'focus': ['midplate', 'tub'], 'show': ['tub', 'midplate', 'pcba'], 'tag': 'Stack detent',
                   'cap': '<b>Stack detent.</b> Cut through the midplate: a strip of its edge, freed by a slot, carries a '
                          'bump that clicks into a pocket in the tub&rsquo;s wall.'},
        'ribbons': {'cam': v(90, -30, 14), 'tgt': v(28, 9, -0.5), 'sec': ['x', 28.0, False],
                    'focus': ['display', 'pcba', 'tub', 'midplate', 'lid'], 'tag': 'Display FPC',
                    'cap': '<b>Display FPC.</b> Cut through the panel&rsquo;s one ribbon: over the glass edge, straight down '
                           'the board&rsquo;s slot and along the back into J2.'},
        'battery': {'cam': v(bx, by - 60, -95), 'tgt': v(bx, by, -3), 'focus': ['battery', 'pcba'], 'hide': ['lid', 'screws'],
                    'tag': 'Battery',
                    'cap': '<b>Battery.</b> From the back with the lid off: the 500 mAh cell lies over the one patch of '
                           'board where nothing stands taller than 1.6 mm, its lead a short run to J5. It rides in the lid.'},
        'boardprep': {'cam': v(30, 18, -110), 'tgt': v(30, 55, -1), 'up': [0, 1, 0], 'show': ['pcba'], 'tag': 'Board prep',
                      'cap': f'<b>Board prep.</b> The board is cut above J5 (y {hw.PCB_CUT_Y:g} here, KiCad y 62.00), power '
                             'moves to SW7, and SW5 is left off.'},
        'edges': {'cam': v(96, -52, 44), 'tgt': v(52, 2, 1), 'tag': 'Edges',
                  'cap': f'<b>Edges and logo.</b> {P.FRONT_EDGE_R:g} mm front and {P.BACK_EDGE_R:g} mm back rounds, a '
                         f'{P.SEAM_CHAMFER:g} mm V at the parting line (the lid&rsquo;s half only, on the chin under the '
                         'keys), and the wordmark in the chin.'},
        'close': {'cam': v(36, -110, -58), 'tgt': v(30, 20, -4), 'sec': ['y', r3(P.SCREWS['bottom-left'][1]), True],
                  'focus': ['screws', 'lid', 'tub', 'pcba', 'rod'], 'highlight': ['screw_*', 'gate'], 'tag': 'Fasteners',
                  'cap': '<b>Fasteners.</b> Cut through the bottom pair of screws: each M2 runs through a post in the lid '
                         'into a solid block in the chin&rsquo;s corner, below the rod. Two more hold the top corners. '
                         'The printed gate in the left wall stops the rod; the lid&rsquo;s rim closes over it.'},
        'joint': {'cam': v(-42, -78, 104), 'tgt': v(30, yc, -5), 'show': ['lid'], 'tag': 'Tub-to-lid joint',
                  'cap': '<b>Tub-to-lid joint.</b> The tub&rsquo;s wall runs on below the parting plane as a tongue into a '
                         'closed groove in the lid&rsquo;s rim; twelve latch arms stand up inside it.'},
        'latch': {'cam': v(71, lat - 23.5, -3.5), 'tgt': v(61.4, lat, -1.4), 'sec': ['y', r3(lat), True],
                  'show': ['tub', 'lid', 'pcba', 'midplate'], 'focus': ['tub', 'lid'], 'tag': 'Latch',
                  'cap': '<b>Latch.</b> One of twelve, over SW1&rsquo;s key. The arm reaches up past the key&rsquo;s slot, so '
                         'its barb catches in a pocket with solid wall behind it.'},
        'compare': {'cam': v(32, -265, 250), 'tgt': v(32, yc, -2), 'fit': True,
                    'show': ['tub', 'keys', 'display', 'lid', 'screws', 'compare'], 'tag': 'Comparison',
                    'cap': '<b>Side by side.</b> Xteink X4 (left), this case, and the X4 in its retro case (right): front '
                           'faces level with the standard build&rsquo;s, bottom edges on one line.'},
        'back': {'cam': v(58, 12, -122), 'tgt': v(30, yc, r3(P.Z_BACK)), 'up': [0, 1, 0], 'fit': True, 'tag': 'Back',
                 'cap': f'<b>Back.</b> The site&rsquo;s book icon, {P.LOGO_BACK["width"]:g} mm wide and '
                        f'{P.LOGO_BACK["depth"]:g} mm deep, on the lid; the grip grooves run along the bottom edge.'},
        'dummy': {'cam': v(96, -46, -118), 'tgt': v(30, 43, -1), 'fit': True, 'show': ['dummy'], 'tag': 'PCBA dummy',
                  'cap': '<b>PCBA dummy.</b> The trimmed board&rsquo;s parts as hulls on a 1.6 mm board, to try the case '
                         'without a real board: the switch sites are open for real switches.'},
        'strip': {'cam': v(-92, -84, 140), 'tgt': v(26, 50, 2), 'tag': 'Light strip',
                  'cap': f'<b>Light strip.</b> Twelve LEDs on a flex bar beside the panel, under a front {strip_over_std(P):g} mm higher '
                         'than the standard build&rsquo;s.'},
        'zstack': {'cam': v(bx + 80, 58, 8), 'tgt': v(bx, 62, -1.5), 'sec': ['x', r3(bx), False],
                   'focus': ['tub', 'display', 'midplate', 'pcba', 'battery', 'lid'], 'tag': 'Front to back',
                   'cap': f'<b>Front to back.</b> Cut through the cell: skin, panel, midplate, board, the cell in the '
                          f'lid, the floor. {P.Z_FRONT - P.Z_BACK:.1f} mm in all.'},
    }
    return pr


# ---- explode, assembly -------------------------------------------------------------------------------------------
def explode_block(B):
    P = B.P
    ls = B.b == 'ls'
    order = ['tub'] + (['strip'] if ls else []) + ['display', 'keys', 'rod', 'midplate', 'pcba', 'battery', 'lid', 'screws']
    off = {'tub': 0.0, 'strip': -6.0, 'display': -12.0, 'keys': -20.0, 'rod': -26.0, 'midplate': -33.0, 'pcba': -44.0,
           'battery': -56.0, 'lid': -64.0, 'screws': -80.0}
    text = {
        'tub': 'Tub face down: the bezel lip, the key openings and the rail under the chin, the slots the side keys '
               'rise into and the USB-C divot are all part of it.' +
               (f' The light-strip tub&rsquo;s face stands {strip_over_std(P):g} mm higher, with a channel for the bar.' if ls else ''),
        'strip': 'The light strip goes in before the panel: the bar drops in beside the seat, LEDs toward the skin, and '
                 'slides left against six small ribs; the folded top pair drops into the fold zone.',
        'display': 'The panel into its pocket, glass to the lip, its FPC standing up at the bottom edge.',
        'keys': 'Four keys in from inside, cap first, hooks in their slots, until both hooks of each stop under the roof.',
        'rod': f'The cranks drop in behind the keys, then the {P.ROD_CUT:g} mm filament rod slides in from the left, '
               'along the channel in the gate&rsquo;s slot, through the rail and every crank; the printed gate drops '
               'into the slot and closes it.',
        'midplate': 'Midplate onto the back of the panel; it clicks in at its four detents.',
        'pcba': 'The trimmed board: FPC through the slot into J2, then press it onto the H2 and H6 snap posts. Each '
                'bottom switch&rsquo;s plunger slides past its crank&rsquo;s nose.',
        'battery': 'The cell rides in the lid: bottom edge under the lip, pushed right (and down only until it stops under the lip) and taped. Stand '
                   'the lid up by the top edge and plug the lead into J5.',
        'lid': 'Fold the lid down like a book: the three side keys slide up their slots, the tongue drops into its '
               'groove and twelve latches click.',
        'screws': f'Four M2 &times; {P.SCREW_L:g} socket head caps from the back.',
    }
    return {'order': order, 'offsets': {g: off[g] for g in order}, 'steps': [text[g] for g in order],
            'done': '<b>Assembled.</b> ' + ('Case, light strip and all.' if ls else 'The case, closed.')}


def assembly_block(B):
    hw, P = B.hw, B.P
    ls = B.b == 'ls'
    kn = KEYS_NAME[B.b]
    st = [
        {'id': 'coupon', 'title': 'Gate coupon, and the optional chin coupon', 'groups': ['keys'], 'preset': 'keys',
         'text': f'Print <code>coupon-gate-{kn.split("-", 1)[1]}</code> with a gate (the test-prints plate, 3, of the plate file has them): '
                 'the gate slides in, cams a 20 mm piece of rod home and lifts out with a paperclip. Optional, a '
                 f'15-minute fit check of the hook keys: <code>coupon-strip-{kn.split("-", 1)[1]}</code> (the chin round one '
                 f'key opening, with its two hook slots) and one <code>{kn}</code>. The key slides up its slots from inside '
                 'and stops level, 2.5 mm proud; nothing is chosen from it.'},
        {'id': 'prep', 'title': 'Before you start', 'groups': ['pcba'], 'preset': 'boardprep',
         'text': f'Cut the board at the upper extension (y {hw.PCB_CUT_Y:g} in the CAD frame, KiCad y 62.00). Do the power '
                 'rework: fit R72 (10 k&Omega;) and R74 (0 &Omega;), remove R36 and R73. Leave SW5 off. Trim J5&rsquo;s '
                 f'through-hole leads and the switches&rsquo; pins to 0.65 mm proud. Measure the cell: at most '
                 f'{P.BATT_T_MAX:g} mm thick and 31.7 &times; 37.9 mm.'},
        {'id': 'rodprep', 'title': 'Rod and cranks', 'groups': ['rod'],
         'text': f'Cut {P.ROD_CUT:g} &plusmn; {P.ROD_CUT_TOL:g} mm of 1.75 mm PLA filament, straighten it on the warm bed, '
                 'taper one end like a pencil to a flat about 0.8 mm across and cut the other square. Print two gates '
                 '(one is a spare). Ream the eight crank bores with a 1.9 mm drill. Pick the crank for the board&rsquo;s '
                 'switches: crank-T for JLC boards (TS365ZJ, white stem), crank-M for MJTP1117 boards (black stem).'},
        {'id': 'tub', 'title': 'Tub face down', 'groups': ['tub'], 'preset': 'assembly',
         'text': 'Tub face down on a soft cloth, or on a spacer about 3 mm thick under the screen area, so the key caps can '
                 'hang out of their openings.'},
    ]
    if ls:
        st.append({'id': 'strip', 'title': 'Light strip', 'groups': ['strip'], 'preset': 'strip',
                   'text': 'Fold the top pair back (tape to tape), then drop the bar in beside the seat, LEDs toward the '
                           'skin, and slide it left against the six ribs. It goes in before the panel.'})
    st += [
        {'id': 'display', 'title': 'Panel', 'groups': ['display'], 'preset': 'stack',
         'text': 'Panel in, glass to the lip, the FPC standing up at the bottom edge.'},
        {'id': 'keys', 'title': 'Keys', 'groups': ['keys'], 'preset': 'keys',
         'text': '<b>Keep the tub face down from here until the board is in</b>: turned over sooner, the keys sink (or '
                 f'fall in, before the rod); face down again, they come back. Each key ({kn}) in from inside, cap first, '
                 'its two hooks in the two slots of its opening (it fits one way round), and let it slide out until both '
                 'hooks stop: it stands 2.5 mm proud and level. Keys go before the cranks: at rest height they block the '
                 'cranks&rsquo; way in.'},
        {'id': 'cranks', 'title': 'Cranks', 'groups': ['rod'], 'preset': 'keys',
         'text': 'Drop each crank in from the open back, cheeks in their slots, pad toward the face, and let go: it '
                 'comes to rest on its key, every crank at the same angle. Don&rsquo;t hold it; the rod&rsquo;s tapered '
                 'tip picks it up.'},
        {'id': 'rod', 'title': 'Rod', 'groups': ['rod'], 'preset': 'keys',
         'text': 'Tub still face down. From the left side, lay the tapered end in the channel at the bottom of the slot '
                 'beside the chin and push it straight in (hole, rings, four cranks) until its square tail is flush with '
                 'the case side or just inside it. Go straight on to the gate: until it is in, only friction holds the rod.'},
        {'id': 'gate', 'title': 'Gate', 'groups': ['rod'], 'preset': 'close',
         'text': 'Drop the gate into the slot from the open back, bevel down, small hole outward, and press its top '
                 f"level with the rim: its bevel pushes the rod the last {P.GATE['web'] + P.GATE['flange']:g} mm to its "
                 'stop. If it stops proud, lift it out, push the tail a little further in and press again. Its web fills '
                 'the opening in the case side, flush, with the small hole showing. From here the rod and cranks stay put '
                 'however the tub is tilted, as long as its back never faces down.'},
        {'id': 'midplate', 'title': 'Midplate', 'groups': ['midplate'], 'preset': 'detent',
         'text': 'Onto the back of the panel; it clicks in at its four detents.'},
        {'id': 'pcba', 'title': 'Board', 'groups': ['pcba'], 'preset': 'ribbons',
         'text': 'Feed the FPC through the board&rsquo;s slot and plug it into J2. Press the board onto the H2 and H6 snap '
                 'posts until it clicks; the plungers slide past the cranks&rsquo; noses.'},
        {'id': 'battery', 'title': 'Battery, in the lid', 'groups': ['battery', 'lid'], 'preset': 'battery',
         'text': 'Tuck the cell&rsquo;s bottom edge under the lid&rsquo;s lip, push it right, and down only until it stops under the lip, and tape it down. '
                 'Stand the lid up beside the case&rsquo;s top edge and plug the lead into J5.'},
        {'id': 'close', 'title': 'Close', 'groups': ['lid', 'screws'], 'preset': 'close',
         'text': f'Fold the lid down like a book; the side keys slide up their slots, the tongue drops into its groove '
                 f'and the latches click. Four M2 &times; {P.SCREW_L:g} socket head caps from the back (a pan head also fits). The lid&rsquo;s rim '
                 'closes over the gate: if the case side shows an open slot instead of the gate, the gate is missing and '
                 'the rod would walk out.'},
        {'id': 'setkeys', 'title': 'Turn it over', 'groups': ['keys'], 'preset': 'keys',
         'text': 'Face up, each key settles onto its crank and the crank onto its switch, about 1.5 mm proud; a tap '
                 'settles them. Face down they drop 1 mm back onto their hooks.'},
    ]
    return st


# ---- card blocks (Rev K's meta blocks under the card that shows them, plus x3's own) -----------------------------
def depth_map(B, res=1.0):
    """The board's rear: the deepest part over each 1 mm cell, and which cells are on the board (showcase_x3.py)."""
    import cadquery as cq
    import numpy as np
    import shapely.geometry as sg
    sol = B.hw.solids()
    xs = np.arange(-1.5, 61.5, res)
    ys = np.arange(-2.0, 94.0, res)
    d = np.zeros((len(ys), len(xs)))
    for ref, s in sol.items():
        if ref == 'PCB':
            continue
        b = s.BoundingBox()
        if b.zmin >= -0.05:
            continue
        ix = (xs + res / 2 > b.xmin) & (xs + res / 2 < b.xmax)
        iy = (ys + res / 2 > b.ymin) & (ys + res / 2 < b.ymax)
        d[np.ix_(iy, ix)] = np.maximum(d[np.ix_(iy, ix)], -b.zmin)
    f = cq.Workplane(obj=sol['PCB']).faces('<Z').val()
    pts = [f.outerWire().positionAt(t / 400) for t in range(401)]
    outline = sg.Polygon([(p.x, p.y) for p in pts]).buffer(0)
    holes = [sg.Polygon([(p.x, p.y) for p in [w.positionAt(t / 60) for t in range(61)]]).buffer(0) for w in f.innerWires()
             if w.BoundingBox().xlen > 3]
    board = outline.difference(sg.MultiPolygon(holes).buffer(0)) if holes else outline
    on = [[bool(board.contains(sg.Point(x + res / 2, y + res / 2))) for x in xs] for y in ys]
    return {'x0': float(xs[0]), 'y0': float(ys[0]), 'res': res, 'nx': len(xs), 'ny': len(ys),
            'depth': [[round(float(v), 2) for v in row] for row in d], 'on': on,
            'outline': [[round(x, 2), round(y, 2)] for x, y in list(outline.exterior.coords)[::2]]}


def compare_block(B, printed_mm3):
    """compare.py's main() for this build, from this build's out/ (compare.main itself reads a pre-split out/tub.stl
    and writes out/compare.json, so it is not called): the rows, the thickness budget, the outlines. The X4 model is
    Zorian22's (CC BY-NC-SA), the retro case's print files are from its author's download."""
    import numpy as np
    import shapely.geometry as sg
    from shapely.affinity import translate
    import body
    import compare as cp
    P, hw = B.P, B.hw
    rp = cp.retro_parts()
    frame = rp['retro_frame']
    x4 = cp.x4_in_retro(frame)
    sec = cp.section_polys([frame], -0.4)
    holes = sorted([sg.Polygon(r) for p in sec for r in p.interiors], key=lambda h: -h.area)
    win = holes[0].bounds
    win_c = ((win[0] + win[2]) / 2, (win[1] + win[3]) / 2)
    retro = list(rp.values())
    r_lo, r_hi = np.min([m.bounds[0] for m in retro], 0), np.max([m.bounds[1] for m in retro], 0)
    r_vol, r_foot = cp.envelope(retro, r_lo[2], r_hi[2])
    import trimesh
    buttons = [trimesh.load(f) for f in cp.RETRO.glob('*.stl') if not any(k in f.name for k in ('stl_2', 'stl_6', 'stl_7'))]
    r_plastic = sum(m.volume for m in retro) + sum(b.volume for b in buttons)
    x4_front = x4.bounds[1][2]
    zs = np.round(x4.vertices[:, 2], 2)
    x4_body_front = float(np.percentile(zs, 99.0))
    x_vol = float(trimesh.load(cp.X4_STL).volume)
    _, x_foot = cp.envelope([x4], x4.bounds[0][2], x4.bounds[1][2], dz=0.2)
    tub, lid = B.stl('tub'), B.stl('lid')
    o_vol = body.outer_body().val().Volume()
    o_foot = sg.box(P.X0, P.Y0, P.X1, P.Y1).area - (4 - np.pi) * P.CORNER_R ** 2
    a_w, a_h, a_cx, a_cy = hw.ACTIVE_W, hw.ACTIVE_H, hw.ACTIVE_CX, hw.ACTIVE_CY
    o_sec = cp.section_polys([tub], P.Z_FRONT - 0.4)
    o_win = sorted([sg.Polygon(r) for p in o_sec for r in p.interiors], key=lambda h: -h.area)[0].bounds

    def row(name, w, h, t, vol, foot, plastic, act, bez, note):
        return {'name': name, 'w': round(w, 1), 'h': round(h, 1), 't': round(t, 1),
                'envelope_cm3': round(vol / 1000, 1), 'footprint_cm2': round(foot / 100, 1),
                'plastic_cm3': None if plastic is None else round(plastic / 1000, 1),
                'plastic_g': None if plastic is None else round(plastic * cp.PETG, 1),
                'active_mm': [round(act[0], 1), round(act[1], 1)],
                'screen_ratio_pct': round(100 * act[0] * act[1] / foot, 1),
                'bezels': None if bez is None else {k: round(v, 1) for k, v in bez.items()}, 'note': note}

    rb = r_hi - r_lo
    ls = B.b == 'ls'
    rows = [
        row('Silkscreen 3.68&#x2033; (this case' + (', light strip)' if ls else ')'), P.X1 - P.X0, P.Y1 - P.Y0,
            P.Z_FRONT - P.Z_BACK, o_vol, o_foot, printed_mm3, (a_w, a_h),
            {'left': o_win[0] - P.X0, 'right': P.X1 - o_win[2], 'top': P.Y1 - o_win[3], 'bottom': o_win[1] - P.Y0},
            '3.68&#x2033; bare e-paper, 500 mAh inside' + (', light strip' if ls else '') + '; 12 printed parts'),
        row('Xteink X4', x4.extents[0], x4.extents[1], x4_body_front - x4.bounds[0][2], x_vol, x_foot.area, None,
            cp.X4_ACTIVE, None, 'reference model (Zorian22), calipers; spec 69 &times; 114 &times; 5.9'),
        row('X4 in the retro case', rb[0], rb[1], rb[2], r_vol, r_foot.area, r_plastic, cp.X4_ACTIVE,
            {'left': win[0] - r_lo[0], 'right': r_hi[0] - win[2], 'top': r_hi[1] - win[3], 'bottom': win[1] - r_lo[1]},
            'bezels measured to the case window'),
    ]
    o_front = cp.silhouette([tub, lid], (0, 1))
    o_side = cp.silhouette([tub, lid], (1, 2))
    views = {
        'ours': {'front': cp.rings(translate(o_front, -a_cx, -a_cy)), 'side': cp.rings(translate(o_side, -a_cy, -P.Z_FRONT)),
                 'screen': [r3(-a_w / 2), r3(-a_h / 2), r3(a_w / 2), r3(a_h / 2)],
                 'window': [round(v, 2) for v in (o_win[0] - a_cx, o_win[1] - a_cy, o_win[2] - a_cx, o_win[3] - a_cy)]},
        'x4': {'front': cp.rings(translate(cp.silhouette([x4], (0, 1)), -win_c[0], -win_c[1])),
               'side': cp.rings(translate(cp.silhouette([x4], (1, 2)), -win_c[1], -x4_body_front)),
               'screen': [r3(-cp.X4_ACTIVE[0] / 2), r3(-cp.X4_ACTIVE[1] / 2), r3(cp.X4_ACTIVE[0] / 2), r3(cp.X4_ACTIVE[1] / 2)]},
        'retro': {'front': cp.rings(translate(cp.silhouette(retro, (0, 1)), -win_c[0], -win_c[1])),
                  'side': cp.rings(translate(cp.silhouette(retro, (1, 2)), -win_c[1], 0)),
                  'window': [round(v, 2) for v in (win[0] - win_c[0], win[1] - win_c[1], win[2] - win_c[0], win[3] - win_c[1])]},
    }
    budget = [[b['name'], r3(b['z'][1] - b['z'][0])] for b in stack_bars(P)]      # ours, front to back (the stack chart)
    return {'rows': rows, 'views': views, 'budget': budget,
            'retro_window_mm': [round(win[2] - win[0], 1), round(win[3] - win[1], 1)],
            'our_window_mm': [round(o_win[2] - o_win[0], 1), round(o_win[3] - o_win[1], 1)],
            'x4_seat': {'depth_mm': round(-x4_front, 2)}, 'retro_plate_z': round(float(r_lo[2]), 2),
            'x4_active_from': '800 &times; 480 at 220 ppi (Xteink spec)',
            'placed_beside': 'standard',
            'attribution': 'Xteink X4 reference model by Zorian22 (Thingiverse thing:7287950), CC BY-NC-SA; '
                           'the retro case from its author&rsquo;s print files.'}


def stack_bars(P):
    """x3's Z stack, front to back (showcase_x3.py), with this build's face."""
    return [
        {'name': 'Front skin', 'z': [P.LIP, P.Z_FRONT]},
        {'name': 'Panel', 'z': [P.DISP_REAR, P.DISP_FRONT]},
        {'name': 'Midplate', 'z': [P.MID_REAR, P.DISP_REAR]},
        {'name': 'Spring gap', 'z': [P.PCB_FRONT, P.MID_REAR]},
        {'name': 'PCB', 'z': [P.PCB_REAR, P.PCB_FRONT]},
        {'name': 'Parts under the cell', 'z': [-P.BATT_DEEPEST, P.PCB_REAR]},
        {'name': 'Clearance', 'z': [P.BATT_FRONT, -P.BATT_DEEPEST]},
        {'name': f'Battery ({P.BATT_T_MAX:g} allowance)', 'z': [P.BATT_FLOOR, P.BATT_FRONT]},
        {'name': 'Back', 'z': [P.Z_BACK, P.BATT_FLOOR]},
    ]


def strip_block(B):
    """The light-strip card's 3.68 content: its install steps (the light-strip page's STEPS['368'], unchanged: they
    are in this CAD frame), the case bullets and the build-diff rows for this size."""
    KX = 23.4975
    P = B.P
    up, ls_depth = strip_over_std(P), P.Z_FRONT_STRIP - P.Z_BACK
    key_step = ('<p>Cut through SW8, seen from the side: the board runs up, the face is to the right. A straight key '
                '(slate) slides down in the chin and presses the pad of a bell crank (amber), which turns on a 1.75 mm '
                'filament rod (blue) and pushes the switch plunger sideways.</p>')
    steps = [
        {'t': 'Fitted', 'cam': [[-92, -84, 140], [26, 50, 2]], 'f': 1, 'b': '<p>The bar lies beside the 3.68\u2033 panel on a shelf at the panel\u2019s front plane. The top pair is folded back under the bar, where its light is hidden. The tail folds over the glass edge straight into the slot.</p>'},
        {'t': 'As it arrives', 'cam': [[-30, -40, 150], [8, 44, 3]], 'f': 0, 'b': '<p>The same strip as the 4.26\u2033. Diode-test, solder and bench-test it the same way.</p>'},
        {'t': 'Fold the top pair back', 'cam': [[-20, 72, 16], [0, 86, 3]], 'f': 0.25, 'tape': True, 'b': '<p>Score the bar&rsquo;s liner 16 mm below the hinge and where the bar meets the foot. Peel the top piece&rsquo;s liner and the bar&rsquo;s above the score, then fold the top pair 180&deg; backward, <span class="tag tape">3M 9077</span> tape to tape. The hinge forms an open loop; never crease it. The folded LEDs face the back.</p>'},
        {'t': 'Into the tub, then the panel', 'cam': [[-26, -18, 44], [2, 22, 3]], 'f': 0.3, 'tape': True, 'b': '<p>The strip goes into the tub before the panel. With the tub face down, drop the bar in 0.5 mm right of its place, LEDs toward the skin, and slide it left under the seat against the six small ribs. The folded pair drops into the fold zone.</p><p><span class="tag tape">3M 9077</span>Leave the rest of the bar&rsquo;s liner on; peel only the foot&rsquo;s, then fit the panel against its two corner stops.</p>'},
        {'t': 'Kapton on the path', 'cam': [[-24, -34, 18], [10, 6, 1]], 'f': 0.3, 'kapton': True, 'b': '<p><span class="tag kapton">Kapton</span> on both slot edges where the neck passes, and on SW9&rsquo;s pin just below the slot.</p>'},
        {'t': 'Over the edge and down', 'cam': [[-26, -30, 20], [10, 6, 2]], 'f': 0.8, 'b': '<p>Fold the neck over the glass edge straight into the slot. This reader leaves 4&ndash;5.6 mm of spare tail: a small loop can sit in the chin, and the rest stands as a loop on the board&rsquo;s back before the stiffened end.</p>'},
        {'t': 'Into J3', 'cam': [[-16, -6, -40], [11, 16, -1]], 'f': 1, 'kapton': True, 'b': '<p>Contacts away from the board, fully home, lever closed. <span class="tag kapton">Kapton</span> strap over the stiffened end only; leave the loop of spare tail free.</p>'},
        {'t': 'Close the case', 'cam': [[-3.5, 31.2, 7.4], [1.2, 49.7, 3.6]], 'cutY': 49.7, 'f': 1, 'caseOn': True, 'cut': True, 'drawing': 'strip_led', 'b': f'<p>Cut through LED D4. The light-strip front shell stands {up:g} mm higher than the standard build&rsquo;s (its skin is {P.Z_FRONT_STRIP - P.LIP:.1f} mm) so its skin clears the LED tops, with a channel for the bar beside the panel and the light path under the skin to the window.</p>'},
        {'t': 'The fold, in the case', 'cam': [[-3.5, 61.0, 6.6], [0.8, 79.5, 2.8]], 'cutY': 79.5, 'f': 1, 'caseOn': True, 'cut': True, 'drawing': 'strip_fold', 'b': '<p>Cut through the folded pair. It lies under the bar, LEDs facing the back, where the front shell&#x2019;s frame is cut away and the midplate is notched through.</p>'},
        {'t': 'The bottom keys', 'cam': [[KX - 30, -14, 10], [KX, -3.6, 1.2]], 'cutX': KX, 'f': 1, 'caseOn': True, 'cut': True, 'b': key_step},
    ]
    case_cards = [{'h': '3.68\u2033 &middot; enclosures/case-368', 'items': [
        f'Front shell {up:g} mm higher than the standard build&rsquo;s, still one flat face; the case is {ls_depth:.1f} mm deep.',
        'Channel for the bar beside the panel, with the light path to the window; six small ribs set the bar sideways and the foot stops the panel corner.',
        'Midplate notched through under the folded pair and under the corner stops; one detent moved clear of the fold. Both 3.68\u2033 builds now share this midplate.',
        'Left border held by ribbed pads, within about 0.03 mm of the other borders; two full-depth corner stops locate the glass.',
        f'Its own four bottom keys (key-x3ls), {up:g} mm taller than the standard ones to match the raised face; the cranks and rod are shared.',
        'A 0.5 mm chamfer on the one lid latch arm under the folded pair; a neck gap in the chin.']}]
    diff = [
        {'part': 'Tub (front shell)', 'same': False, 'std': 'tub-standard', 'ls': 'tub-light-strip',
         'text': f'Its own per build: the light-strip face is {up:g} mm higher, with the channel for the bar; the '
                 'standard tub&rsquo;s screen window has the wider bevel, with round corners'},
        {'part': 'Bottom keys', 'same': False, 'std': 'key-x3std', 'ls': 'key-x3ls',
         'text': f'Their own per build: key-x3ls is {up:g} mm taller than key-x3std, to match the face'},
        {'part': 'Lid, midplate', 'same': True, 'text': 'Shared'},
        {'part': 'Cranks, rod, gate', 'same': True, 'text': 'Shared'},
        {'part': 'Panel and FPC (not printed)', 'same': True,
         'text': 'The same bare 3.68&#x2033; panel in both; the light strip adds its bar beside it and its tail in J3'}]
    sp = json.loads((PROJ / 'out' / 'shared-parts.json').read_text())
    out = {'case_cards': case_cards, 'diff': diff,
           'shared_parts': sorted(k for k, v in sp['parts'].items() if v.get('same_files') or v.get('same_solid')),
           'cut_led_y': 49.7, 'cut_fold_y': 79.5, 'key_cut_x': KX}
    if B.b == 'ls':
        out['steps'] = steps
        inter, ins = B.json['interference'], B.json['insertion']
        out['checks'] = {'interference': inter.get('strip', []), 'insertion': ins.get('_strip', {}),
                         'foot_stop': B.json['mechanics']['springs'].get('foot_stop'),
                         'seat_entry': B.json['mechanics'].get('seat_entry'),
                         'channel_skin': B.json['mechanics'].get('channel_skin')}
        out['geometry'] = {'front': P.Z_FRONT, 'front_raise': P.FRONT_RAISE, 'flex_top': round(P.STRIP_Z0 + P.STRIP_STACK, 3),
                           'led_top': P.STRIP_LED_TOP, 'led_clr': P.STRIP_LED_CLR, 'ceiling': P.CHANNEL_TOP,
                           'stack': {'tape': P.STRIP_TAPE, 'pi': P.STRIP_PI, 'flex': P.STRIP_FLEX, 'led_h': P.STRIP_LED_H},
                           'stack_tol': P.STRIP_STACK_TOL, 'bar_x': list(P.STRIP_BAR_X), 'seat_x1': P.SEAT_X1,
                           'seat_y': list(P.SEAT_Y), 'channel_x1': P.CHANNEL_X1, 'channel_y': list(P.CHANNEL_Y),
                           'fold_zone': list(P.FOLD_ZONE), 'fold_rin': P.FOLD_RIN, 'ribs_y': list(P.STRIP_RIBS['y']),
                           'pads_y': list(P.PAD_Y), 'locator_x': P.LOCATOR_X, 'gap': P.STRIP_GAP}
    return out


def cards_block(B, M, K):
    """One block per card. Where the card is the same for both sizes, the block has the 4.26 adapter's shape (Rev K's
    meta blocks under their Rev K names, API.md section 7), so a card reads the same paths on both; this case's own
    content (the battery in the lid, the board prep) is added beside it."""
    hw, P = B.hw, B.P
    import body
    import joint
    import lid as lidm
    import logo
    import midplate
    import panel
    import refs
    import sidekeys
    import tub as tubm
    mech, cj = B.json['mechanics'], B.json['crank']
    ls = B.b == 'ls'
    fps = hw.footprints()
    tabs = body.side_tabs()
    u = body.usb()
    uf = tubm.usb_features()
    G = {}
    G['glance'] = {'bullets': [
        '3.68&#x2033; 528 &times; 792 e-paper on Ian&rsquo;s board, trimmed above J5 (power moves to SW7).',
        f'{P.X1 - P.X0:.1f} &times; {P.Y1 - P.Y0:.1f} &times; {P.Z_FRONT - P.Z_BACK:.1f} mm; '
        f'{B.json["summary"]["with_keys_mm"]:.1f} over the bottom keys.',
        '500 mAh 503035 cell in the lid, over the one patch of the board where nothing stands taller than 1.6 mm.',
        f'Four bottom keys: a straight key over a bell crank on a {P.ROD_D:g} mm filament rod (lever 1.678).',
        'Three side keys cut from the lid&rsquo;s own wall; twelve printed parts, no supports.',
    ] + ([f'Light strip: twelve LEDs beside the panel under a front {strip_over_std(P):g} mm higher than the standard '
          'build&rsquo;s; its own tub and keys.'] if ls else
         ['The light-strip build swaps the tub and the four keys; everything else is shared.'])}
    # ---- keys: the 4.26 block's names, then this case's extras
    travel = {}
    for r in K['tolerance']:
        nm = {'M': 'MJTP', 'T': 'TS365'}[r['variant']]
        travel[f"{nm} delta {-r['face_dy'] + 0.0:+.1f}"] = {                   # 4.26's naming: delta moves the board -Y
            'rest_theta': r['theta_rest'], 'click_theta': r['theta_click'], 'click_key_mm': r['key_travel_click'],
            'bottom_theta': r['theta_bottom'], 'bottom_key_mm': r['key_travel_bottom'],
            'proud_rest_mm': r['key_proud_at_rest'], 'proud_click_mm': r['key_proud_at_click'],
            'proud_bottom_mm': r['key_proud_at_bottom']}
    xg = cj['x_gaps']
    hang = min(v[0] for per in cj['theta_free_no_key'].values() for v in per.values())
    G['keys'] = {
        'proud_mm': P.KEY_TOP_OVER_FACE, 'chin_deeper_mm': 1.0, 'chin_y': P.BOT_IN, 'rail_y': list(P.RAIL_Y),
        'rings': sum(1 for s in tubm.rail_segments() if s[0] == 'ring'), 'seats': sum(1 for s in tubm.rail_segments() if s[0] == 'seat'),
        'coupon': f'coupon-strip-{KEYS_NAME[B.b].split("-", 1)[1]}', 'rod_len': P.ROD_CUT,
        'rod_hole_d': P.ROD_HOLE_D, 'end_play': K['rod']['end_play'], 'cap_y': list(P.KEY_Y), 'cheek': list(P.CRANK_CHEEK),
        'slot': list(P.SLOT), 'travel': travel, 'key_sweep_checks': mech['key_sweep']['checks'],
        'side_clearance': {k.replace('_', ' '): v for k, v in xg.items()}, 'hang_theta': hang,
        'mech_travel_crosscheck': 'derived (sc_contract) vs mechanics.json key_forces.travel: checked in the merge',
        # this case's extras
        'key_name': KEYS_NAME[B.b], 'key_names': dict(KEYS_NAME), 'key_tall_mm': K['key']['tall'],
        'proud_range_mm': K['hooks']['key_proud_at_rest_mm'], 'stop_above_rest_mm': K['stop_above_rest_mm'],
        'wrong_variant_shift_mm': K['hooks']['wrong_variant_key_shift_mm'], 'lever': K['forces']['lever'],
        'rod_tol': P.ROD_CUT_TOL, 'rod_d_range': list(P.ROD_D_RANGE), 'crank_nose_diff_mm': r3(P.CRANK_NOSE_C['M'][0] - P.CRANK_NOSE_C['T'][0]),
        'keys_differ_per_build': True}
    G['strip'] = strip_block(B)
    # ---- side keys
    sk = mech['springs']['side_keys']
    G['sidekeys'] = {
        'count': len(tabs), 'refs': [t['ref'] for t in tabs], 'draw': {'plan': 'SW7', 'side': 'SW1', 'elev': 'SW7'},
        'tabs': [{'ref': t['ref'], 'side': t['side'], 'root': [r3((P.X1 if t['side'] > 0 else P.X0) - t['side'] * P.TAB_T / 2), t['flex_root']],
                  'y_root': t['y_root'], 'y_block': r3(t['y_block']), 'free': t['y_free'], 'pad_y': list(t['pad_y']),
                  'face': [r4(v) for v in t['face']], 'gap': t['gap'], 'click_mm': 0.25, 'nub_to': r3(t['nub_to']),
                  'inner': r3(t['inner']), 'stop': r3(t['stop']), 'nub_arm': round(abs(t['face'][1] - t['flex_root']), 2),
                  'role': hw.SWITCH_ROLES[t['ref']], 'pad_len': P.TAB_PAD_LENS.get(t['ref'], P.TAB_PAD_LEN), 'nub_w': t['nub_w']}
                 for t in tabs],
        'tab_mech': sk,
        'tab_pad': [round(P.TAB_PAD_LEN - 2 * (P.TAB_PAD_PROUD - 0.05), 2), round(P.TAB_PAD_FACE[1] - P.TAB_PAD_FACE[0], 2)],
        'tab_geom': {'proud': P.TAB_PAD_PROUD, 't': P.TAB_T, 'flex_t': P.TAB_FLEX_T, 'z': [r3(v) for v in P.TAB_Z],
                     'slot_clr': P.TAB_SLOT_CLR, 'end_clr': P.TAB_END_CLR, 'root_clr': P.TAB_ROOT_CLR, 'sliver': P.SLIVER,
                     'void': P.TAB_VOID, 'wall': r3(P.SIDE_WALL), 'relief': P.TAB_RELIEF_MAX,
                     'nub': [P.NUB['w'], round(P.NUB['z'][1] - P.NUB['z'][0], 2)], 'nub_z': list(P.NUB['z']),
                     'nub_w': {t['ref']: t['nub_w'] for t in tabs},
                     'window': {t['ref']: [round(v, 2) for v in body.tab_window(t)['y']] for t in tabs},
                     'stop': mech['springs'].get('side_key_stop'), 'bar_top': r3(P.TAB_BAR_TOP), 'end_foot': P.TAB_END_FOOT,
                     'foot': P.TAB_FOOT, 'foot_gap': list(P.TAB_FOOT_GAP), 'hinge': P.TAB_HINGE,
                     'pad_face': list(P.TAB_PAD_FACE), 'block_margin': P.TAB_BLOCK_MARGIN,
                     'plunger': [r3(hw.switch_plunger('SW1')['nub'][3] - hw.switch_plunger('SW1')['nub'][2]),
                                 r3(hw.switch_plunger('SW1')['nub'][5] - hw.switch_plunger('SW1')['nub'][4])]},
        'summary': sidekeys.summary(), 'sweep': mech.get('side_key_sweep'),
        'roles': {t['ref']: hw.SWITCH_ROLES[t['ref']] for t in tabs}, 'power_key': 'SW7'}
    # ---- joint
    J = joint.summary()
    G['joint'] = {'latch_count': J['latch_count'], 'tongue_len': J['tongue_len'],
                  'joint': {**J, 'latch': mech.get('latches'), 'seam': P.SEAM,
                            'walls': {'left': P.WALL_X0, 'right': P.WALL_X1, 'top': P.TOP_IN, 'bottom': P.BOT_IN},
                            'outline': [P.X0, P.X1, P.Y0, P.Y1, P.CORNER_R],
                            'tabs': [[t['side'], *sorted((t['y_root'], t['y_free']))] for t in tabs],
                            'usb_y': [r3(v) for v in uf['port_y']], 'reset_y': hw.switch_plunger(hw.RESET)['face'][1],
                            'top_screw': list(P.TOP_SCREW),
                            'screws': [[k, r3(x), r3(y)] for k, (x, y) in P.SCREWS.items()]},
                  'latches': mech.get('latches'),
                  'board_snap': {**mech.get('board_snap', {}), 'at': {r: fps[r]['cad'] for r in P.SNAP_POSTS},
                                 'geom': P.BOARD_SNAP}}
    G['usb'] = {'usb': {'mouth_x': r4(u['mouth_x']), 'x1': P.X1, 'wall_x': list(uf['wall_x']), 'yc': r3(u['yc']), 'zc': r3(u['zc']),
                        'shell_y': [r3(v) for v in u['y']], 'shell_z': [r3(v) for v in u['z']], 'recess': list(uf['size']),
                        'r': uf['r'], 'recess_z': [r3(v) for v in uf['port_z']], 'recess_y': [r3(v) for v in uf['port_y']],
                        'seat_x': r4(uf['seat_x']), 'face_x': r3(uf['face_x']), 'floor_x': [r3(v) for v in uf['floor_x']],
                        'floor_t': P.USB_FLOOR['t'], 'hole': [r3(v) for v in uf['hole']], 'hole_r': uf['hole_r'],
                        'face_to_mouth': r3(uf['face_to_mouth']), 'plug_short_mm': r3(uf['plug_short_mm']),
                        'insert_x': P.INSERT_X1, 'spare': P.USB_PLUG_SPARE, 'overmold_max': list(P.OVERMOLD),
                        'typical': [11.0, 5.6], 'seam': P.SEAM}, 'ref': 'J1'}
    rs = hw.switch_plunger(hw.RESET)
    G['reset'] = {'reset': dict(rs), 'ref': hw.RESET, 'hole_d': 1.2, 'sink_d': 2.2, 'below_usb_mm': r3(u['yc'] - rs['face'][1])}
    # ---- screen stack
    zl = panel.z_levels()
    G['screen'] = {'stack': mech['screen_stack'],
                   'panel': {'part': '3.68&#x2033; 528 &times; 792 e-paper', 'label': PANEL_LABEL['ls' if ls else 'std'], 'touch': False,
                             'front_light': False, 'ribbons': 1, 'x0': r3(hw.PANEL_X0), 'x1': r3(hw.PANEL_X1),
                             'y0': r3(hw.PANEL_Y0), 'y1': r3(hw.PANEL_Y1), 'w': hw.PANEL_W, 'h': hw.PANEL_H,
                             't': hw.PANEL_T, 't_tol': hw.PANEL_T_TOL, 'front': r3(P.LIP), 'rear': r3(P.DISP_REAR),
                             'layers': [[k, t] for k, t in panel.LAYERS], 'z': {k: [r3(a), r3(b)] for k, (a, b) in zl.items()},
                             'active': [hw.ACTIVE_W, hw.ACTIVE_H]},
                   'insertion': {k: v for k, v in B.json['insertion'].items() if not k.startswith('_')},
                   'z': {'front': r3(P.Z_FRONT), 'lip': r3(P.LIP), 'disp_rear': r3(P.DISP_REAR), 'mid_rear': P.MID_REAR,
                         'pcb_front': P.PCB_FRONT, 'skin': r3(P.Z_FRONT - P.LIP)},
                   # the window (tub.window, params WINDOW_*): face_mm is the bevel as seen, its width on the face
                   # (standard: 35 degrees, 0.9 deep, 1.29 on the face, R0.4 / R1.69 corners; light strip: x3's 45-degree
                   # 1.2 on a 0.6 land, square corners); depth_mm how far down the face it runs, land_mm the straight part
                   # under it to the lip
                   'window': {'face_mm': P.WINDOW_BEVEL_W, 'deg': P.WINDOW_BEVEL_ANGLE, 'depth_mm': P.WINDOW_CHAMFER,
                              'land_mm': P.WINDOW_LAND, 'corner_r_mm': [P.WINDOW_CORNER_R, r3(P.WINDOW_CORNER_R + P.WINDOW_BEVEL_W)],
                              'margin_mm': P.WINDOW_MARGIN}}
    if ls:
        G['screen']['strip_stack'] = {'tape': P.STRIP_TAPE, 'pi': P.STRIP_PI, 'flex': P.STRIP_FLEX, 'led_h': P.STRIP_LED_H,
                                      'led_top': r3(P.STRIP_LED_TOP), 'led_clr': P.STRIP_LED_CLR, 'ceiling': P.CHANNEL_TOP,
                                      'front_raise': P.FRONT_RAISE, 'over_std': strip_over_std(P)}
    # ---- detents, ribbons
    G['detent'] = {'detents': {**mech['mid_detents'], 'p': P.MID_DETENT, 'edge_clr': midplate.EDGE_CLR,
                               'wall_x': [P.WALL_X0, P.WALL_X1]},
                   'midplate': {'springs': [list(s) for s in midplate.SPRINGS], 'L': midplate.SPRING_L, 'W': midplate.SPRING_W,
                                'T': midplate.SPRING_T, 'nub_h': midplate.NUB_H, 'data': mech['springs']['midplate_spring']}}
    rb = {'report': mech['ribbons'], 'slot': [r3(v) for v in panel.slot()], 'bend_r': panel.BEND_R, 'count': 1,
          'outlines': {k: [list(p) for p in r['poly']] for k, r in panel.RIBBONS.items()},
          'connectors': {k: {'ref': r['conn'], 'x': r3(fps[r['conn']]['cad'][0])} for k, r in panel.RIBBONS.items()},
          'fpc_len': panel.FPC_L, 'fpc_len_tol': panel.FPC_L_TOL, 'insert': panel.INSERT}
    if ls:
        rb['strip_tail'] = {'ref': 'J3', 'x': r3(fps['J3']['cad'][0])}
    G['ribbons'] = {'ribbons': rb}
    # ---- the battery: in the lid (x3), with the board-rear depth map
    bay = lidm.bay()[2]
    G['battery'] = {'battery': {
        'in_lid': True, 'capacity_mAh': 500, 'ref': P.BATT_REF,
        'box': {'x': list(P.BATT['x']), 'y': list(P.BATT['y']), 'z': [r3(v) for v in P.BATT['z']]},
        'allowance_mm': P.BATT_T_MAX, 'clearance_mm': P.BATT_CLR_BOARD, 'deepest_under_mm': P.BATT_DEEPEST,
        'swell_mm': r3(P.BATT_T_MAX + P.BATT_CLR_BOARD - P.BATT_REF['size'][2]), 'floor_t': P.BATT_FLOOR_T,
        'pocket_mm': [r3(bay['pocket'][1] - bay['pocket'][0]), r3(bay['pocket'][3] - bay['pocket'][2])],
        'bay': bay, 'retention': mech['springs']['battery_retention'], 'lead': refs.lead_report(),
        'plug': [r3(v) for v in refs.plug_box()],
        'lead_xy': [[round(float(x), 2), round(float(y), 2)] for x, y, z in refs.lead_path()[0][::6]],
        'deep_parts': {r: r3(-hw.bounds(r)[4]) for r in ('J5', 'SW7', 'L1', 'J1', 'U4', 'U3', 'J7')},
        'antenna': [0.51, 7.5, 36.75, 54.75], 'antenna_gap_mm': 1.25, 'module': [r3(v) for v in hw.bounds('U4')[:4]],
        'j5': [r3(v) for v in hw.bounds('J5')[:4]], 'j7': [r3(v) for v in hw.bounds('J7')],
        'envelope_mm': P.BATT_ENV_T,
        'air_under_j7_mm': json.loads((B.out / 'slice' / 'slice-report.json').read_text())['_as_printed']['bay']
                           ['bay_air']['zones']['under J7'],
        'cell_bbox': [r3(v) for v in M['battery_cell'].bounds.ravel()]},
        'depth_map': depth_map(B)}
    # ---- board prep (3.68 only)
    feet = json.loads((hw.HW / 'footprints.json').read_text())['footprints']
    G['boardprep'] = {'trim_y': hw.PCB_CUT_Y, 'trim_kicad_y': 62.0, 'fit': list(hw.FITTED),
                      'remove': [r for r in hw.REMOVED if r != 'SW5'], 'leave_off': ['SW5'],
                      'fit_values': {'R72': '10 k&Omega;', 'R74': '0 &Omega;'}, 'power_key': 'SW7',
                      'gone_with_cut': sorted(f['ref'] for f in feet if f['cad'][1] >= hw.PCB_CUT_Y),
                      'lead_trim_mm': 0.65, 'lead_tip_z': P.LEAD_TIP, 'support_post': list(P.SUPPORT_POSTS[0]),
                      'snap_posts': list(P.SNAP_POSTS)}
    # ---- front to back
    bars = [{'name': b['name'], 'z': [r3(v) for v in b['z']]} for b in stack_bars(P)]
    if ls:
        bars.insert(1, {'name': 'Light strip (bar and LEDs, beside the panel)', 'z': [r3(P.STRIP_Z0), r3(P.STRIP_LED_TOP)],
                        'beside': True})
    G['zstack'] = {'bars': bars, 'total': [r3(P.Z_BACK), r3(P.Z_FRONT)],
                   'budget': [[b['name'], r3(b['z'][1] - b['z'][0])] for b in bars if not b.get('beside')],
                   'thickness': r3(P.Z_FRONT - P.Z_BACK), 'with_keys': B.json['summary']['with_keys_mm'], 'seam': P.SEAM,
                   'without_battery': r3(P.Z_FRONT - P.Z_BACK - P.BATT_T_MAX)}
    # ---- closing up
    sl = screw_list(P)
    G['closing'] = {'holes': {r: fps[r]['cad'] for r in sorted(fps) if r.startswith('H')}, 'top_screw': list(P.TOP_SCREW),
                    'screw_seat_z': screw_seat(P, 'bottom-left'),
                    'screws': f'M2 x {P.SCREW_L:g} ISO 4762 socket head',
                    'head': {'iso': 'ISO 4762', 'kind': 'socket head cap', 'dk': 3.8, 'k': 2.0, 'also': 'ISO 7045 pan head',
                             'below_back': {s['id']: r3(s['cb_depth'] - 2.0) for s in sl}},
                    'screw_list': sl, 'pinned': ['H3', 'H4'], 'pin_d': P.H34_PIN['d'],
                    'gate': {'web': P.GATE['web'], 'flange': P.GATE['flange'], 'top_clr': P.GATE['top_clr'],
                             'pull_d': P.GATE['pull_d'], 'stop_x': r3(P.ROD_STOP_X0)},
                    'board_snap': mech['board_snap'],
                    'seat_z': {s['id']: s['seat_z'] for s in sl},
                    'cb_depth': {'bottom': P.M2_CB_DEPTH['corner'], 'top': P.M2_CB_DEPTH['top']},
                    'screw_len': P.SCREW_L, 'pilot': P.M2_PILOT,
                    'support_post': list(P.SUPPORT_POSTS[0])}
    # ---- edges and logo
    lg = logo.placed()
    lb = logo.placed(P.LOGO_BACK)
    G['edges'] = {'edges': {'front_r': P.FRONT_EDGE_R, 'back_r': P.BACK_EDGE_R, 'seam_chamfer': P.SEAM_CHAMFER,
                            # the window's bevel as seen: its width on the face (the 4.26 adapter's too), its angle
                            # and its corners at the screen and on the face
                            'key_chamfer': P.KEY_EDGE_CHAMFER, 'window_bevel': P.WINDOW_BEVEL_W, 'window_land': P.WINDOW_LAND,
                            'window_bevel_deg': P.WINDOW_BEVEL_ANGLE,
                            'window_corner_r': [P.WINDOW_CORNER_R, r3(P.WINDOW_CORNER_R + P.WINDOW_BEVEL_W)]},
                  'logo': {'polys': B.L.rings(lg, 2), 'bounds': [round(v, 2) for v in lg.bounds],
                           'width': P.LOGO['width'], 'depth': P.LOGO['depth']},
                  'logo_back': {'polys': B.L.rings(lb, 2), 'bounds': [round(v, 2) for v in lb.bounds],
                                'width': P.LOGO_BACK['width'], 'depth': P.LOGO_BACK['depth'],
                                'at': [r3(P.LOGO_BACK['x']), P.LOGO_BACK['y']]},
                  'grip_grooves': {'y': list(P.GRIP_GROOVES_Y), **P.GRIP_GROOVE}}
    G['assembly'] = {'readme': 'README.md "Assembly (tub face down)" and "Bottom keys: Assembly"'}
    G['checks'] = {}                                        # count / failed: filled in by worker_data
    G['files'] = {'dummy': B.json['pcba-dummy'],
                  'plate': 'The OrcaSlicer plate file (generic presets, a 220 x 210 mm bed; the standard build on three plates: the case '
                           'and the rod jig on plate 1, the coupons on plate 3) is print/silkscreen-368-plates.3mf in the '
                           'repo; it is not in the zip.',
                  'print': 'PLA, 0.2 mm layers, three or more perimeters, no supports and no brim (a brim would tie the '
                           'side keys to the lid). Elephant-foot compensation 0 for the keys, the cranks and the gate; '
                           'the keys and the cranks on a 2-layer raft (contact Z distance 0.2).'}
    return G


# ---- checks: generated from the project's own reports -----------------------------------------------------------------
def checks_block(B, K):
    out = B.out
    inter, ins = B.json['interference'], B.json['insertion']
    mech = B.json['mechanics']
    C_ = []
    parts = inter['parts']
    pp = [r for r in parts if 'expected' in r]                     # printed part against printed part
    bad = [r for r in pp if not r['expected']]
    C_.append({'id': 'interference_parts', 'label': 'No printed part overlaps another, apart from the designed ones '
               '(the gate only touches its slot&rsquo;s floor and lips; the hook keys touch nothing at rest)',
               'ok': not bad, 'value': len(bad),
               'detail': '; '.join(f"{r['part']} / {r['with']} {r['volume']} mm3" for r in (bad or [r for r in pp if r['expected']]))[:600],
               'source': 'interference.json parts', **({} if bad else {'status': 'expected'})})
    hwc = [r for r in parts if 'expected' not in r]
    known = {('midplate', 'PCB'): 'the midplate&rsquo;s spring nubs on the board (their preload)',
             ('midplate', 'display_thick'): 'a +0.1 mm panel pressing the midplate back (the springs take it)'}
    unk = [r for r in hwc if (r['part'], r['with']) not in known]
    C_.append({'id': 'interference_hardware', 'label': 'Printed parts against the board, panel and cell: only the '
               'designed contacts', 'ok': not unk, 'value': len(hwc),
               'detail': '; '.join(f"{r['part']} / {r['with']} {r['volume']} mm3" + (f" ({known[(r['part'], r['with'])]})"
                                   if (r['part'], r['with']) in known else '') for r in hwc)[:700],
               'source': 'interference.json parts', **({'status': 'designed'} if hwc and not unk else {})})
    C_.append({'id': 'display_vs_board', 'label': 'The panel clears the board&rsquo;s trimmed leads',
               'ok': not inter.get('display_vs_board'), 'source': 'interference.json display_vs_board'})
    if 'strip' in inter:
        sb = [r for r in inter['strip'] if not r['expected']]
        C_.append({'id': 'strip_interference', 'label': 'The light strip (nominal, tight fold, against the wall) touches '
                   'only where it is meant to (the neck on the glass ledge, the tail in J3)', 'ok': not sb,
                   'value': len(sb), 'source': 'interference.json strip'})
    hits = {k: v['hits'] for k, v in ins.items() if not k.startswith('_')}
    C_.append({'id': 'insertion', 'label': 'The panel (at its largest) and the midplate go into the face-down tub '
               'from behind without touching it', 'ok': not any(hits.values()), 'source': 'insertion.json'})
    lm = ins.get('_later', {})
    C_.append({'id': 'later_moves', 'label': 'The board goes in and the lid goes on (with its side keys) along their '
               'paths without a clash', 'ok': not any(lm.values()), 'source': 'insertion.json _later'})
    if '_strip' in ins:
        s = ins['_strip']
        badm = [k for k, v in s.items() if isinstance(v, str) and v != 'clear']
        C_.append({'id': 'strip_insertion', 'label': 'The strip drops in, slides under the seat and settles in every '
                   'modelled case (bent, on its LEDs, against the wall)', 'ok': not badm,
                   'value': sum(1 for v in s.values() if v == 'clear'), 'source': 'insertion.json _strip'})
    K_ok = all(c['ok'] is not False for c in K['checks'])
    C_.append({'id': 'bottom_keys', 'label': 'Bottom keys: cranks, keys, rod and both switch families checked at rest, '
               'through the whole press and along their way in', 'ok': K_ok,
               'value': f"{sum(c['ok'] is True for c in K['checks'])} of {len(K['checks'])}",
               'detail': 'rest rows: ' + ', '.join(f"{r['variant']} {r['face_dy']:+.1f}: {r['theta']:.2f}&deg;" for r in K['rest_rows']),
               'source': 'crank.json, mechanics.json'})
    ks = mech['side_key_sweep']
    sk = mech['springs']['side_keys']
    sok, val = True, {}
    for r, rows in ks.items():
        stop = sk[r]['stop_travel_mm']
        upto = [x for x in rows if x['nub_travel_mm'] <= stop + 1e-9]
        past = [x for x in rows if x['nub_travel_mm'] > stop + 1e-9]
        clear = all(all(v == 0 for k, v in x.items() if k not in ('nub_travel_mm', 'plunger_push_mm')) for x in upto)
        push = max(x['plunger_push_mm'] for x in upto)
        stopped = all(x.get('tub', 0) > 0 or x.get('lid', 0) > 0 for x in past)     # past the stop it would be in the wall
        sok &= clear and push <= 0.45 + 1e-9 and stopped
        val[r] = push
    C_.append({'id': 'side_keys', 'label': 'Side keys swept to their stop: nothing is touched on the way, the plunger '
               'reaches no more than its 0.45 mm travel, and past the stop the key would be in the wall',
               'ok': sok, 'value': val, 'source': 'mechanics.json side_key_sweep'})
    for blk, lab in (('latches', 'Latches'), ('board_snap', 'Board snaps'), ('mid_detents', 'Midplate detents')):
        v = mech.get(blk, {})
        st = v.get('root_strain_pct', v.get('strain_pct'))
        C_.append({'id': blk, 'label': f'{lab}: strain at the root under 1.5 %', 'ok': None if st is None else st < 1.5,
                   'value': st, 'source': f'mechanics.json {blk}'})
    pr = json.loads((out / 'print' / 'print-report.json').read_text())
    parts_ = {k: v for k, v in pr.items() if not k.startswith('_')}
    C_.append({'id': 'print_watertight', 'label': 'Every print file is a closed solid', 'ok': all(v['watertight'] for v in parts_.values()),
               'value': len(parts_), 'source': 'print/print-report.json'})
    if '_plate' in pr:
        C_.append({'id': 'print_plate', 'label': f"Everything fits one {pr['_plate']['bed_mm']:g} mm bed",
                   'ok': bool(pr['_plate']['fits']), 'source': 'print/print-report.json _plate'})
    sp = out / 'slice' / 'slice-report.json'
    if sp.exists():
        sr = json.loads(sp.read_text())
        sl = {k: v for k, v in sr.items() if not k.startswith('_')}
        feats = sr.get('_features', [])
        isl = sr.get('_islands', {})
        # a feature slice_check only reports (ok None: not one of its judged boxes) is not a failure
        more = [*sr.get('_bores', []), *sr.get('_first_layer', {}).values(), *sr.get('_bridges', {}).values()] \
            + ([sr['_gate']] if '_gate' in sr else [])
        C_.append({'id': 'slicing', 'label': 'The keys slice cleanly (OrcaSlicer) with no supports: their hooks and root '
                   'print in every layer, nothing starts in mid-air and no layer reaches more than 0.5 mm past the one '
                   'below; the gate prints flange first with its pull hole open, and no bridge crosses its slot',
                   'ok': all(v.get('exit') == 0 for v in sl.values())
                   and all(f.get('ok') is not False for f in feats) and all(v.get('ok') for v in isl.values())
                   and all(v.get('ok') for v in more),
                   'value': ', '.join(sorted(sl)), 'source': 'slice/slice-report.json'})
    dm = B.json['pcba-dummy'].get('checks')
    if isinstance(dm, dict):
        C_.append({'id': 'dummy', 'label': 'The printable PCBA dummy is one closed solid with every switch site open',
                   'ok': all(v for v in dm.values() if isinstance(v, bool)) if dm else None, 'source': 'pcba-dummy.json checks'})
    return C_


def measure_block(B, cards, K):
    """cards.checks.measure: what to measure (or print and try) before printing, Rev K's "Measure before printing"
    brought to this case (README: Battery, Assembly, To verify on the first print, Bottom keys' Open items, Fitting the
    strip). HTML strings; the numbers are this build's data."""
    P, hw = B.P, B.hw
    import panel
    ba, us = cards['battery']['battery'], cards['usb']['usb']
    T = K['switches']['T']
    f2 = lambda v: f'{v:.2f}'.rstrip('0').rstrip('.')                               # noqa: E731
    gate_fit = (P.GATE_SLOT['mouth'][1] - P.GATE_SLOT['mouth'][0] - P.GATE['web_y'][1] + P.GATE['web_y'][0]) / 2  # a side
    out = [
        '<b>The battery pack.</b> A 503035, at most 5.3&nbsp;mm thick with up to two layers of tape on each face. Push it '
        'to the right, and down only until it stops under the lip, and tape it down; check where its lead leaves and its polarity at J5.',
        f'<b>The pack against the microSD socket.</b> At {f2(ba["envelope_mm"])}&nbsp;mm (the cell with two layers of tape '
        f'on each face) the pack clears J7, the deepest part over it ({f2(ba["deepest_under_mm"])}&nbsp;mm), by '
        f'{f2(ba["air_under_j7_mm"])}&nbsp;mm as printed. A charged or aged pack swells: check it still leaves a gap '
        'after a full charge.',
        f'<b>The panel&rsquo;s thickness</b> ({f2(hw.PANEL_T)} &plusmn;{f2(hw.PANEL_T_TOL)}&nbsp;mm in its drawing; the '
        f'midplate&rsquo;s springs take up the range) and <b>the switches&rsquo; travel</b> ({f2(T["travel"]["click"])}'
        f'&nbsp;mm to the click, {f2(T["travel"]["bottom"])} to the bottom in the model).',
        f'<b>The FPC.</b> Its folds over the glass edge assume R{f2(panel.BEND_R)}; the drawing gives none, so check it '
        'folds that tightly without creasing. Check its contact side against J2, too: the drawing does not say.',
        f'<b>USB-C cables.</b> The recess takes overmolds up to {f2(P.USB_RECESS[0])} &times; {f2(P.USB_RECESS[1])}&nbsp;mm, '
        f'and a typical plug seats about {f2(us["plug_short_mm"])}&nbsp;mm short of full depth: try your cables on the '
        'PCBA dummy.',
        f'<b>Tape on the plungers</b> must be thinner than the side keys&rsquo; gap: {f2(P.TAB_GAP_SIDE[+1])}&nbsp;mm on the '
        f'right-hand keys (seen from the front), {f2(P.TAB_GAP_SIDE[-1])}&nbsp;mm on the left.',
        '<b>Lid seating.</b> If a side key clicks with no free travel, or needs a long press, the lid is sitting to one '
        'side: check the tongue is fully down in its groove all round.',
        f'<b>A real TS365ZJ, before printing crank-T.</b> Its body width, plunger width and height are from its drawing. '
        f'The model puts its tip at y {f2(T["face_y"])} ({f2(T["face_worst_y"])} at worst) and its plunger at Z '
        f'{f2(T["nub_z"][0])} to {f2(T["nub_z"][1])} ({f2(T["nub_z_worst"][0])} to {f2(T["nub_z_worst"][1])} at worst): '
        'measure tip to signal-pin row, plunger height and width.',
        f'<b>The chin coupon</b> (optional, about 15 minutes: <code>coupon-strip-{KEYS_NAME[B.b].split("-", 1)[1]}</code>, '
        f'the chin round one key opening with its two hook slots, and one <code>{KEYS_NAME[B.b]}</code>). The key should '
        'slide up its slots from inside with no binding and stop level, 2.5&nbsp;mm proud: its hooks '
        f'{f2(P.KEY_W_OUT)}&nbsp;mm under the roof at rest, {f2(P.KEY_HOOK["tip"] - P.KEY_SLOT["back"])}&nbsp;mm off the '
        'slots&rsquo; back. A firm thumb push outward from inside should leave no whitening at the hooks or behind the '
        'slots, and from outside the chin&rsquo;s rounded edge should show no see-through behind a slot. It is a fit check '
        'only: nothing is chosen from it.',
        f'<b>The gate coupon</b>, once per printer and filament (<code>coupon-gate-{KEYS_NAME[B.b].split("-", 1)[1]}</code> and a gate: '
        f'the left wall with the gate&rsquo;s slot, and a gate). The gate should slide in at {f2(gate_fit)}&nbsp;mm a side, '
        'cam a 20&nbsp;mm piece of rod home and lift out with a straightened paperclip. Proof test on a kitchen scale, tape '
        'over the rim for the lid, the rod piece pressed straight down: at 2.8&nbsp;kg (27&nbsp;N) no crack, no visible set, '
        'the gate still lifts out; at 5.5&nbsp;kg (54&nbsp;N) nothing breaks. Too tight: 0.15 a side. Cracked where the web '
        'meets the flange: lips 1.05, flange 0.70.',
        f'<b>The rod.</b> {P.ROD_CUT:g} &plusmn;{f2(P.ROD_CUT_TOL)}&nbsp;mm of {f2(P.ROD_D)}&nbsp;mm PLA filament (real '
        f'filament is {f2(P.ROD_D_RANGE[0])}&ndash;{f2(P.ROD_D_RANGE[1])}), straightened under a flat plate on a warm bed. '
        'It must roll straight on a flat surface: a bowed rod binds the cranks. Taper the end that goes in first like a '
        f'pencil to a flat about {f2(P.ROD_TIP["flat"])}&nbsp;mm across, and cut the tail square: it bears on the gate.',
    ]
    if B.b == 'ls':
        out.append(f'<b>The strip&rsquo;s stack</b> (tape + PI stiffener + flex, {P.STRIP_STACK:.3f}&nbsp;mm nominal; its '
                   f'drawing gives no tolerance and the case is checked to {P.STRIP_STACK_TOL:.3f} over) and its LEDs&rsquo; '
                   f'height ({f2(P.STRIP_LED_H)} nominal, checked to 0.9).')
    return out

def meta_block(B, M):
    hw, P = B.hw, B.P
    import trimesh
    shell = trimesh.util.concatenate([M['tub'], M['lid']] + [m for k, m in M.items() if k.startswith('skey_')])
    lo, hi = shell.bounds
    pr = json.loads((B.out / 'print' / 'print-report.json').read_text())
    kn = KEYS_NAME[B.b]
    printed = [{'name': 'tub', 'count': 1, 'file': f'tub-{VAR_OF[B.b]}.stl'},
               {'name': 'lid', 'count': 1, 'file': 'lid.stl', 'note': 'with the three side keys'},
               {'name': 'midplate', 'count': 1, 'file': 'midplate.stl'},
               {'name': 'key', 'count': 4, 'file': f'{kn}.stl'},
               {'name': 'crank', 'count': 4, 'file': 'crank-T.stl', 'alt': 'crank-M.stl'},
               {'name': 'gate', 'count': 1, 'file': 'gate.stl', 'note': 'the rod&rsquo;s stop; print two, one is a spare'}]
    mass = pr['tub']['mass_g_PLA'] + pr['lid']['mass_g_PLA'] + pr['midplate']['mass_g_PLA'] + 4 * pr[kn]['mass_g_PLA'] \
        + 4 * pr['crank-T']['mass_g_PLA'] + pr['gate']['mass_g_PLA'] if kn in pr else None
    try:
        rev = subprocess.run(['git', '-C', str(PROJ), 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
    except Exception:                                                          # noqa: BLE001
        rev = ''
    return {
        'title': 'Silkscreen 3.68&#x2033; case', 'size_label': '3.68"',
        'panel': {'part': '3.68&#x2033; 528 &times; 792 e-paper', 'label': PANEL_LABEL[B.b], 'touch': False,
                  'front_light': False, 'ribbons': 1, 'w': hw.PANEL_W, 'h': hw.PANEL_H, 't': hw.PANEL_T,
                  'active': [hw.ACTIVE_W, hw.ACTIVE_H], 'pixels': [528, 792],
                  **({'light': 'the Silkscreen light strip on its left border'} if B.b == 'ls' else {})},
        'envelope': [r3(v) for v in (lo[0], hi[0], lo[1], hi[1], lo[2], hi[2])],
        'size': [round(float(v), 1) for v in (hi - lo)],
        'body': [r3(P.X1 - P.X0), r3(P.Y1 - P.Y0), r3(P.Z_FRONT - P.Z_BACK)],
        'with_keys': B.json['summary']['with_keys_mm'],
        'walls_x': [P.X0, P.X1], 'insert_x': [P.INSERT_X0, P.INSERT_X1],
        'z': {'front': r3(P.Z_FRONT), 'back': r3(P.Z_BACK), 'seam': P.SEAM, 'lip': r3(P.LIP), 'pcb_front': P.PCB_FRONT,
              'pcb_rear': P.PCB_REAR, 'mid_rear': P.MID_REAR, 'disp_rear': r3(P.DISP_REAR), 'disp_front': r3(P.DISP_FRONT),
              'batt_front': r3(P.BATT_FRONT), 'batt_floor': r3(P.BATT_FLOOR), 'lid_floor_in': r3(P.LID_FLOOR_IN),
              'keys_top': B.json['summary']['keys_top_z']},
        'active': {'cx': r4(hw.ACTIVE_CX), 'cy': r4(hw.ACTIVE_CY), 'w': hw.ACTIVE_W, 'h': hw.ACTIVE_H},
        'frame': 'X = KiCad x - 44.24, Y = 148.25 - KiCad y, Z = 0 at the board&rsquo;s rear face, +Z toward the screen',
        'printed': {'parts': printed, 'count': sum(p['count'] for p in printed), 'mass_g': None if mass is None else round(mass, 1),
                    'rod': f'{P.ROD_CUT:g} mm of 1.75 mm PLA filament (not printed)'},
        'side_keys': list(P.TAB_ROOTS), 'bottom_keys': list(C.BOTTOM_REFS), 'reset': hw.RESET,
        'roles': dict(hw.SWITCH_ROLES),
        'source': {'project': 'silkscreen-enclosures/enclosures/case-368', 'commit': rev, 'variant': VAR_OF[B.b],
                   'out': f'out/{VAR_OF[B.b]}', 'generated': time.strftime('%Y-%m-%dT%H:%M:%S'),
                   'adapter': 'showcase/gen/adapt_368.py'},
    }


def facts_block(B, meta, cmp):
    """The masthead's facts, with the 4.26 adapter's ids and plain-text values (value and note may be set as text)."""
    P = B.P
    b = meta['body']
    ls = B.b == 'ls'
    retro = next((r for r in cmp['rows'] if r['name'] == 'X4 in the retro case'), None)
    vol = meta['printed']['volume_cm3']
    return [
        {'id': 'envelope', 'label': 'Envelope', 'value': f'{b[0]:.1f} x {b[1]:.1f} x {b[2]:.1f}', 'unit': 'mm',
         'note': f"{meta['size'][0]:.1f} across the side buttons, {meta['with_keys']:.1f} over the bottom keys"},
        {'id': 'x4', 'label': 'Xteink X4, for scale', 'unit': 'mm', 'value': '69 x 114 x 5.9',
         'note': f"in its retro case: {retro['w']:.1f} x {retro['h']:.1f} x {retro['t']:.1f}" if retro else ''},
        {'id': 'printed', 'label': 'Printed, PLA', 'value': f"{meta['printed']['count']} parts",
         'note': 'tub, lid with its 3 side keys, midplate, 4 keys, 4 cranks, the rod&rsquo;s gate'},
        {'id': 'plastic', 'label': 'Plastic', 'value': f'{vol:.1f}', 'unit': 'cm3',
         'note': f"solid volume; {vol * 1.24:.0f} g of PLA at 100% infill"},
        {'id': 'panel', 'label': 'Panel', 'value': '3.68" 528 x 792 e-paper',
         'note': 'bare panel, one FPC' + (', the light strip on its left border' if ls else '')},
        {'id': 'battery', 'label': 'Battery', 'value': '500 mAh', 'note': f'503035 cell in the lid, {P.BATT_T_MAX:g} mm allowance'},
        {'id': 'hardware', 'label': 'Hardware', 'value': f'{len(P.SCREWS)} x M2x{P.SCREW_L:g}',
         'note': 'ISO 4762 socket heads (a pan head also fits), the lid&rsquo;s only; a printed gate holds the rod'},
        {'id': 'rod', 'label': 'Bottom-key rod', 'value': f'{P.ROD_CUT:g} mm of {P.ROD_D} filament', 'note': 'not printed; cut from the spool'},
        {'id': 'files', 'label': 'Files', 'value': 'STL + STEP',
         'note': 'every part, both tubs, both key sets, the chin and gate coupons, a printable PCBA dummy'},
    ]



def asciify(obj):
    """Every string to ASCII: non-ASCII characters become numeric HTML entities (all text here is shown as HTML)."""
    if isinstance(obj, dict):
        return {k: asciify(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [asciify(v) for v in obj]
    if isinstance(obj, str):
        return ''.join(c if ord(c) < 0x80 else f'&#x{ord(c):x};' for c in obj)
    return obj


def worker_data(B, M, D):
    K = keys_block(B)
    meta = meta_block(B, M)
    printed_mm3 = sum(M[n].volume for n in ('tub', 'lid', 'midplate', *[f'skey_{r}' for r in B.P.TAB_ROOTS])) \
        + 4 * M['key_SW8'].volume + 4 * M['crank_T'].volume + M['gate'].volume
    cards = cards_block(B, M, K)
    t = time.time()
    cards['compare'] = compare_block(B, printed_mm3)
    log(f'compare {time.time() - t:.0f}s')
    meta['printed']['volume_cm3'] = round(printed_mm3 / 1000, 2)
    meta['build_diff'] = 'tub + 4 keys differ'
    meta['build_label'] = C.BUILD_LABELS[B.b]
    checks = checks_block(B, K)
    cards['checks'] = {'count': len(checks) + len(K['checks']),
                       'failed': [c['id'] for c in checks + K['checks'] if c['ok'] is False],
                       'measure': measure_block(B, cards, K)}
    data = {
        'schema': C.SCHEMA, 'size': SIZE, 'build': B.b, 'meta': meta, 'facts': facts_block(B, meta, cards['compare']),
        'presets': presets_block(B), 'explode': explode_block(B), 'controls': controls_block(B), 'keys': K,
        'drawings': D, 'cards': {c['id']: cards.get(c['id'], {}) for c in C.CARDS if C.card_applies(c, SIZE, B.b)},
        'checks': checks, 'assembly': assembly_block(B),
        'downloads': None,                                        # filled in by the merge (both builds' files)
    }
    return B.L.rnd(asciify(data), 4)


def render_drawings(D, path):
    """A contact sheet of every drawing (matplotlib), for looking at them."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path as MPath
    col = {'case': '#c9c2b0', 'case2': '#a9a391', 'plate': '#6f8a7a', 'pcb': '#2e7d4f', 'part': '#555', 'nub': '#bbb',
           'glass': '#223', 'lgp': '#9cc', 'film': '#557', 'key': '#333', 'crank': '#d08a2a', 'rod': '#3a6fd0',
           'tab': '#b9a98a', 'metal': '#999', 'ribbon': '#c98a2b', 'cell': '#aab', 'lead': '#b33', 'strip': '#111',
           'led': '#fc3', 'tape': '#c24', 'kapton': '#d99a24', 'ref': '#777'}
    n = len(D)
    cols = 5
    rows = (n + cols - 1) // cols
    fig, axs = plt.subplots(rows, cols, figsize=(cols * 5, rows * 4.2))
    for ax, d in zip(axs.ravel(), D):
        for kind in ('layers', 'beyond'):
            for Ly in d[kind]:
                for poly in Ly['polys']:
                    verts, codes = [], []
                    for ring in poly:
                        verts += ring
                        codes += [MPath.MOVETO] + [MPath.LINETO] * (len(ring) - 1)
                    pp = MPath(verts, codes)
                    if kind == 'layers':
                        ax.add_patch(PathPatch(pp, fc=col.get(Ly['role'], 'm'), ec='k', lw=0.3, alpha=0.85))
                    else:
                        ax.add_patch(PathPatch(pp, fc='none', ec='r', lw=0.6, ls='--'))
        u0, u1, v0, v1 = d['window']
        ax.set_xlim(u0, u1)
        ax.set_ylim(v0, v1)
        ax.set_aspect('equal')
        ax.set_title(f"{d['name']} {d['axis']}={d['at']} {d['notes'].get('ref', '')}", fontsize=9)
        ax.tick_params(labelsize=6)
    for ax in axs.ravel()[n:]:
        ax.axis('off')
    fig.tight_layout()
    fig.savefig(path, dpi=70)
    plt.close(fig)


def main_worker(b, out):
    B = Build(b)
    work = out / 'work'
    work.mkdir(parents=True, exist_ok=True)
    M = worker_meshes(B)
    for n in M:
        assert C.NODE_RE.match(n) and C.node_rule(n) and C.group_of(n), f'node {n!r} breaks the contract'
    glb = B.L.pack_glb(M)
    (work / f'{b}.glb').write_bytes(glb)
    log(f'{b}: {len(M)} nodes, {sum(len(m.faces) for m in M.values())} tris, glb {len(glb) / 1e6:.2f} MB')
    t = time.time()
    D = worker_drawings(B, M)
    log(f'{b}: {len(D)} drawings {time.time() - t:.0f}s')
    for d in D:
        E = C.Errors()
        C.validate_drawing(d, d['name'], E)
        if E:
            log('  DRAWING ERRORS', E)
        log(f"  {d['name']:13s} {B.L.drawing_summary(d)}")
    render_drawings(D, work / f'{b}-drawings.png')
    data = worker_data(B, M, D)
    B.L.dump(data, work / f'{b}-data.json')
    log(f'{b}: data {(work / f"{b}-data.json").stat().st_size / 1e3:.0f} kB')


# ======================================================================================================================
# merge: split the nodes, write the model files, the zip and the downloads block, validate, report
# ======================================================================================================================
def run_workers(out, builds, jobs):
    py = sys.executable
    procs = []
    for b in builds:
        env = {**os.environ, 'SILKSCREEN_VARIANT': VAR_OF[b], 'PYTHONIOENCODING': 'utf-8'}
        lf = open(out / 'work' / f'{b}-log.txt', 'w', encoding='utf-8')
        p = subprocess.Popen([py, '-B', str(Path(__file__).resolve()), '--out', str(out), '--worker', b],
                             cwd=str(PROJ), env=env, stdout=lf, stderr=subprocess.STDOUT)
        procs.append((b, p, lf))
        if jobs == 1:
            p.wait()
    bad = []
    for b, p, lf in procs:
        p.wait()
        lf.close()
        log(f'worker {b}: exit {p.returncode}')
        if p.returncode:
            bad.append(b)
            print((out / 'work' / f'{b}-log.txt').read_text(encoding='utf-8')[-3000:])
    if bad:
        raise SystemExit(f'worker(s) failed: {bad}')


def _pair(*names):
    return [f'{n}.{e}' for n in names for e in ('stl', 'step')]


COUPONS = ['coupon-strip', 'coupon-gate']      # the chin strip (the hook keys' optional fit check) and the gate's
PRINT_GROUPS = [   # (group id, label, what, [file in print/3.68/, or a key of models_zip's extra])
    ('shared', 'Shared parts', 'Lid (with the three side keys), midplate, both cranks, the rod&rsquo;s gate and the rod '
     'jig: the same in both builds',
     _pair('lid', 'midplate', 'crank-T', 'crank-M', 'gate', 'rod-jig')),
    ('std', 'Standard build', 'The standard tub, its four keys (key-x3std), its chin coupon (optional: coupon-strip, '
     'a fit check of the hook keys with one key) and its gate coupon',
     _pair('tub-standard', 'key-x3std', *(f'{c}-x3std' for c in COUPONS))),
    ('ls', 'Light-strip build', 'The light-strip tub, its four keys (key-x3ls, taller, for its higher face), its chin coupon '
     '(optional: coupon-strip, a fit check of the hook keys with one key) and its gate coupon',
     _pair('tub-light-strip', 'key-x3ls', *(f'{c}-x3ls' for c in COUPONS))),
    ('rod', 'Rod notes', 'How to cut, straighten and fit the 1.75 mm filament rod and its printed gate', ['ROD.txt']),
    ('dummy', 'PCBA dummy', 'A printable stand-in for the trimmed board, to try the case without one', ['pcba-dummy.stl']),
]
GROUP_DIR = {'shared': 'shared/', 'std': 'standard/', 'ls': 'light-strip/', 'rod': '', 'dummy': 'dummy/'}
GROUP_BUILDS = {'std': ['std'], 'ls': ['ls']}


def readme_txt(groups, zname):
    lines = [f'{zname}: the Silkscreen 3.68" case (enclosures/case-368), both builds.', '',
             'Print in PLA, 0.2 mm layers, three or more perimeters, no supports and no brim. Elephant-foot compensation',
             '0 for the keys, the cranks and the gates. Four keys, four cranks and a gate (print',
             'two: one is a spare) per case. The keys and the cranks print on a 2-layer raft (raft contact Z',
             "distance 0.2, the raft's initial layer expansion 1); the plate file sets it.", '',
             'Standard build: shared/ + standard/.  Light-strip build: shared/ + light-strip/.',
             'Also needed: the rod (ROD.txt) and four M2 x 8 socket head cap screws (ISO 4762; a pan head,',
             'ISO 7045, also fits).',
             'The standard build laid out on three plates for OrcaSlicer: print/silkscreen-368-plates.3mf in the repo.', '']
    for g in groups:
        lines.append(f"{g['label']}: {g['what']}")
        for f in g['files']:
            lines.append(f"  {f['path']}  ({f['bytes']} bytes)")
        lines.append('')
    return '\n'.join(lines)


def models_zip(P):
    """One zip for both builds (shared parts once): the repo's print/3.68/ (with its ROD.txt) + the rod jig + the
    PCBA dummy + README.txt."""
    import sc_lib as L
    pdir = PRINT
    extra = {'pcba-dummy.stl': PROJ / 'out' / 'standard' / 'print' / 'pcba-dummy.stl',
             'rod-jig.stl': REPO / 'print' / 'rod-jig.stl', 'rod-jig.step': REPO / 'print' / 'rod-jig.step'}
    entries, groups = [], []
    listed = set()
    for gid, label, what, files in PRINT_GROUPS:
        fl = []
        for f in files:
            src = extra.get(f, pdir / f)
            data = src if isinstance(src, bytes) else Path(src).read_bytes()
            arc = GROUP_DIR[gid] + f
            entries.append((arc, data))
            listed.add(f)
            row = {'path': arc, 'bytes': len(data)}
            if gid in GROUP_BUILDS:
                row['builds'] = GROUP_BUILDS[gid]
            fl.append(row)
        groups.append({'id': gid, 'label': label, 'what': what, 'files': fl})
    missing = sorted(p.name for p in pdir.iterdir() if p.is_file() and p.name not in listed)
    assert not missing, f'print/3.68/ files not in the zip groups: {missing}'
    zname = 'silkscreen-case-3.68.zip'
    readme = readme_txt(groups, zname)
    entries.insert(0, ('README.txt', readme.encode('ascii')))
    zb = L.zip_bytes(entries)
    js = L.models_js(zb, size=SIZE, zip=zname)
    return zname, zb, js, groups


def main_merge(out):
    os.environ['SILKSCREEN_VARIANT'] = 'standard'
    sys.path.insert(0, str(PROJ / 'src'))
    import params as P
    import sc_lib as L
    work = out / 'work'
    rep = {'schema': C.SCHEMA, 'size': SIZE, 'generated': time.strftime('%Y-%m-%dT%H:%M:%S'), 'errors': [],
           'warnings': [], 'checks': {}}
    E = rep['errors']
    M = {b: L.read_model({'data': __import__('base64').b64encode((work / f'{b}.glb').read_bytes()).decode('ascii')})
         for b in ('std', 'ls')}
    H = {b: {n: L.mesh_hash(m) for n, m in M[b].items()} for b in M}
    shared, differ, only_std, only_ls = L.split_shared(H['std'], H['ls'])
    # a CadQuery tessellation (the battery's filleted pouch) can come out in another vertex order, with other
    # diagonals, in another process: for a node the contract puts in core, the same vertex set (to 1e-4 mm), the same
    # number of faces and the same area and volume (to 1e-6) is the same surface
    import numpy as np

    def vset(m):
        v = np.round(np.asarray(m.vertices), 4) + 0.0
        return v[np.lexsort(v.T[::-1])]
    same_within = []
    for n in list(differ):
        a, b = M['std'][n], M['ls'][n]
        if C.node_rule(n)[1] == 'core' and len(a.faces) == len(b.faces) and len(a.vertices) == len(b.vertices) \
                and np.array_equal(vset(a), vset(b)) and abs(a.area - b.area) <= 1e-6 * a.area \
                and abs(a.volume - b.volume) <= 1e-6 * abs(a.volume):
            differ.remove(n)
            shared.append(n)
            same_within.append(n)
            H['ls'][n] = H['std'][n]
    shared.sort()
    rep['split'] = {'shared': shared, 'differ': differ, 'only_std': only_std, 'only_ls': only_ls,
                    'same_within_1e-5': same_within}
    for n in shared:
        if C.node_rule(n)[1] == 'build':
            E.append(f'{n} is the same in both builds but NODE_RULES puts it in a build file')
    for n in differ:
        if C.node_rule(n)[1] == 'core':
            E.append(f'{n} differs between the builds but NODE_RULES says core (tessellation not deterministic?)')
    for n in only_std:
        if C.node_rule(n)[1] != 'extras':
            E.append(f'{n} only in the standard build')
    for n in only_ls:
        if not n.startswith('strip_'):
            E.append(f'{n} only in the light-strip build')
    # the split against the project's own shared-parts check (build.py: STEP booleans and byte-equal STLs)
    sp = json.loads((PROJ / 'out' / 'shared-parts.json').read_text())
    node_of = {'lid_body': 'lid', 'crank-M': 'crank_M', 'crank-T': 'crank_T', 'midplate': 'midplate',
               **{f'skey_{r}': f'skey_{r}' for r in P.TAB_ROOTS}}
    agree = {}
    for part, row in sp['parts'].items():
        if part in node_of:
            same = bool(row.get('same_files') or row.get('same_solid'))
            agree[part] = (node_of[part], same, node_of[part] in shared)
            if same != (node_of[part] in shared):
                E.append(f'shared-parts.json says {part} same={same}, the node split says {node_of[part] in shared}')
    for part, row in sp['tub_specific'].items():
        agree[part] = (part, not row['differ'], part in shared)
        if row['differ'] != (part in differ):
            E.append(f'shared-parts.json says {part} differs={row["differ"]}, the split says {part in differ}')
    if sp.get('differ'):
        E.append(f'shared-parts.json lists differing shared parts: {sp["differ"]}')
    rep['checks']['split_vs_shared_parts'] = {k: {'node': v[0], 'shared_parts_same': v[1], 'split_shared': v[2]} for k, v in agree.items()}
    # the instanced crank placed at each key = that key's crank STL (the one-mesh-per-variant claim), both builds
    import numpy as np
    worst = 0.0
    for b in ('std', 'ls'):
        for r in C.BOTTOM_REFS:
            cs = L.load_stl(PROJ / 'out' / VAR_OF[b] / f'crank_{r}.stl')
            x = json.loads((work / f'{b}-data.json').read_text())['keys']['x'][r]
            cm = L.moved(M[b]['crank_M'], x)
            d = float(np.abs(cs.bounds - cm.bounds).max())
            dv = abs(cs.volume - cm.volume) / cs.volume
            win = [-20, 20, -20, 20]
            for dx in (-4.5, -3.0, -1.0, 0.0, 1.0, 3.0, 4.5):        # cheeks, crossbar, leg / nose
                ga, gb = L.cut(cs, 'x', x + dx, win), L.cut(cm, 'x', x + dx, win)
                worst = max(worst, ga.symmetric_difference(gb).area / max(ga.area, 1e-9))
            if d > 1e-3 or dv > 1e-4 or worst > 1e-3:
                E.append(f'{b} crank_{r}.stl is not crank-M at x {x} (bounds {d:.4f}, volume {dv:.2e}, section {worst:.2e})')
    rep['checks']['crank_instances'] = {'what': 'crank-M.stl moved to keys.x[ref] against crank_<ref>.stl, 4 keys x 2 builds: '
                                                'bounds, volume and 7 sections across the crank',
                                        'worst_section_symdiff_rel': worst}
    # the kinematics' geometry against the shipped meshes: at theta 0 each nose front is on its plunger face, and each
    # key's pusher is on the pad crown's top
    Kd = json.loads((work / 'std-data.json').read_text())['keys']
    geo = {}
    for v, crank_n, nub_n, x0 in (('M', 'crank_M', 'nub_SW8', Kd['x']['SW8']), ('T', 'crank_T', 'sw_T_nub', 0.0)):
        cv = np.asarray(M['std'][crank_n].vertices)
        leg = cv[(np.abs(cv[:, 0]) <= 1.3) & (cv[:, 2] < -1.5)]
        nose = float(leg[:, 1].max())
        face = float(np.asarray(M['std'][nub_n].vertices)[:, 1].min())
        geo[v] = {'nose_front': round(nose, 4), 'plunger_face': round(face, 4), 'face_y': Kd['switches'][v]['face_y'],
                  'nose_front_ref': round(C.nose_front(Kd, v, 0.0), 4)}
        if max(abs(nose - face), abs(nose - Kd['switches'][v]['face_y']), abs(nose - C.nose_front(Kd, v, 0.0))) > 0.01:
            E.append(f'variant {v}: nose front {nose:.4f}, plunger face {face:.4f}, face_y {Kd["switches"][v]["face_y"]}')
    for b in ('std', 'ls'):
        kz = float(M[b]['key_SW8'].bounds[0][2])
        crown = Kd['pad']['c'][1] + Kd['pad']['r']
        geo[f'key_underside_{b}'] = {'key_min_z': round(kz, 4), 'crown_top': round(crown, 4)}
        if abs(kz - crown) > 0.01:
            E.append(f'{b} key_SW8 underside {kz:.4f} is not on the crown top {crown:.4f}')
    rep['checks']['kinematic_geometry'] = geo
    # model files
    files = {}
    t = time.time()
    files[C.fname('core', SIZE)] = L.write_model(out / C.fname('core', SIZE), 'core', SIZE, None, {n: M['std'][n] for n in shared})
    for b in ('std', 'ls'):
        per = differ + (only_ls if b == 'ls' else [])
        files[C.fname('build', SIZE, b)] = L.write_model(out / C.fname('build', SIZE, b), 'build', SIZE, b, {n: M[b][n] for n in per})
    files[C.fname('extras', SIZE)] = L.write_model(out / C.fname('extras', SIZE), 'extras', SIZE, None, {n: M['std'][n] for n in only_std})
    log(f'model files {time.time() - t:.0f}s', {k: v['bytes'] for k, v in files.items()})
    # the zip
    zname, zb, js, groups = models_zip(P)
    (out / C.fname('models', SIZE)).write_text(js, encoding='ascii')
    files[C.fname('models', SIZE)] = {'bytes': (out / C.fname('models', SIZE)).stat().st_size, 'zip_bytes': len(zb)}
    rep['zip'] = {'name': zname, 'zip_bytes': len(zb), 'js_bytes': files[C.fname('models', SIZE)]['bytes'],
                  'entries': [f['path'] for g in groups for f in g['files']]}
    # data files
    nodes_core, extras = set(shared), set(only_std)
    for b in ('std', 'ls'):
        D = json.loads((work / f'{b}-data.json').read_text())
        D['downloads'] = {'file': C.fname('models', SIZE), 'zip': zname, 'zip_bytes': len(zb),
                          'js_bytes': files[C.fname('models', SIZE)]['bytes'], 'readme': 'README.txt', 'groups': groups,
                          'raw_bytes': sum(f['bytes'] for g in groups for f in g['files']),
                          'note': 'One zip for both builds: shared/ once, standard/ and light-strip/ each with its own '
                                  'tub, keys, chin coupon and gate coupon.'}
        nodes = nodes_core | set(differ) | (set(only_ls) if b == 'ls' else set()) | extras
        Ed = C.validate_data(D, C.fname('data', SIZE, b), nodes=nodes)
        E.extend(Ed)
        # independent: the derived click / bottom against mechanics.key_travel (computed by the project from crank.py)
        # every tolerance row (M/T x face_dy -0.2 / 0 / +0.2) through the reference kinematics
        Kd = D['keys']
        worst = [0.0, 0.0]
        for r in Kd['tolerance']:
            d = C.derive(Kd, r['variant'], r['face_dy'])
            for a, bb, tol, i in (('theta_rest', 'theta_rest', 0.011, 0), ('theta_click', 'theta_click', 0.011, 0),
                                  ('theta_bottom', 'theta_bottom', 0.011, 0), ('key_click', 'key_travel_click', 0.0011, 1),
                                  ('key_bottom', 'key_travel_bottom', 0.0011, 1)):
                worst[i] = max(worst[i], abs(d[a] - r[bb]))
                if abs(d[a] - r[bb]) > tol:
                    E.append(f"{b} {r['variant']} {r['face_dy']:+.1f}: sc_contract {a} {d[a]} != mechanics.json travel {bb} {r[bb]}")
        rows = []
        for r in Kd['rest_rows']:
            th = C.theta_at(Kd, r['variant'], C.face(Kd, r['variant'], r['face_dy']))
            rows.append({**r, 'reference_theta': round(th, 4) + 0.0, 'reference_key_dz': round(C.key_down(Kd, th), 4) + 0.0,
                         'd_theta': round(abs(th - r['theta']), 4), 'd_key_dz': round(abs(C.key_down(Kd, th) - r['key_dz']), 4)})
        rep['checks'][f'kinematics_{b}'] = {'rest_rows_vs_reference': rows, 'derived': Kd['derived'],
                                            'mechanics_travel_worst': {'deg': round(worst[0], 4), 'mm': round(worst[1], 4)}}
        C.fname('data', SIZE, b)
        L.dump(D, out / C.fname('data', SIZE, b))
        files[C.fname('data', SIZE, b)] = {'bytes': (out / C.fname('data', SIZE, b)).stat().st_size}
        rep['checks'][f'data_{b}'] = {'errors': len(Ed), 'drawings': [d['name'] for d in D['drawings']],
                                      'presets': sorted(D['presets']), 'cards': sorted(D['cards']),
                                      'checks_false': [c['id'] for c in D['checks'] if c['ok'] is False],
                                      'keys_checks_false': [c['id'] for c in D['keys']['checks'] if c['ok'] is False]}
    # every written file: the contract's file validation (ASCII bytes, GLB decode, names)
    for f in files:
        Ef = C.validate_file(out / f)
        E.extend(Ef)
        files[f]['valid'] = not Ef
        if files[f]['bytes'] > C.LIMITS['file_bytes']:
            E.append(f'{f}: {files[f]["bytes"]} bytes > 16 MB')
    rep['files'] = files
    rep['total_bytes'] = sum(v['bytes'] for v in files.values())
    # the 4.26 adapter's report shape (API.md section 7), then this adapter's detail
    rep['nodes'] = {'core': sorted(shared), 'build': {b: sorted(differ + (only_ls if b == 'ls' else [])) for b in ('std', 'ls')},
                    'extras': sorted(only_std)}
    rep['parts'] = {'shared': sorted(k for k, v in sp['parts'].items() if v.get('same_files') or v.get('same_solid')),
                    'per_build': sorted(sp['tub_specific'])}
    rep['build_diff'] = 'tub + 4 keys differ'
    rep['display_nodes_differ'] = {}
    # every display node each build shows (core or per build), as the 4.26 lists them: the bare panel and its FPC,
    # the same mesh in both builds, so in core here
    rep['display_nodes'] = {b: sorted(n for n in shared + differ + (only_ls if b == 'ls' else [])
                                      if n.startswith(('panel_', 'ribbon_'))) for b in ('std', 'ls')}
    assert all(rep['display_nodes'][b] for b in ('std', 'ls')), rep['display_nodes']
    import hashlib
    for f, info in files.items():
        info['sha1'] = hashlib.sha1((out / f).read_bytes()).hexdigest()
    rep['downloads'] = {'zip': zname, 'zip_bytes': len(zb), 'js_bytes': files[C.fname('models', SIZE)]['bytes'],
                        'raw_bytes': sum(f['bytes'] for g in groups for f in g['files'])}
    rep['node_info'] = {n: {'tris': len(M['std'][n].faces), 'hash': H['std'][n], 'file': 'core' if n in shared else 'extras'}
                        for n in shared + only_std}
    for b in ('std', 'ls'):
        for n in differ + (only_ls if b == 'ls' else []):
            rep['node_info'][f'{n}@{b}'] = {'tris': len(M[b][n].faces), 'hash': H[b][n], 'file': f'build-{b}'}
    rep['seconds'] = round(time.time() - T0, 1)
    L.dump(rep, out / f'adapter-{SIZE}.json')
    log('files', {k: v['bytes'] for k, v in files.items()}, 'total', rep['total_bytes'])
    log(f'{len(E)} errors')
    for e in E[:60]:
        print('  ', e)
    return not E


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(DEFAULT_OUT))
    ap.add_argument('--worker', choices=('std', 'ls'))
    ap.add_argument('--only', choices=('std', 'ls'))
    ap.add_argument('--merge', action='store_true')
    ap.add_argument('--jobs', type=int, default=2)
    a = ap.parse_args()
    out = Path(a.out)
    if a.worker:
        main_worker(a.worker, out)
        sys.exit(0)
    (out / 'work').mkdir(parents=True, exist_ok=True)
    if not a.merge:
        run_workers(out, [a.only] if a.only else ['std', 'ls'], a.jobs)
    if a.only:
        sys.exit(0)
    sys.exit(0 if main_merge(out) else 1)
