"""Build every part of one build (params.BUILD: a configuration's slug, variants.py), export STL + STEP to
out/<build>/, and run its checks. With no build chosen, build params.PRINT_BUILDS, check what they share
(light-strip every printed part but the tub, chinless the midplate and the side keys, light-strip-chinless every
part but the tub with chinless), write the repo's print/4.26/ (write_print), and last assert that the cranks are
case-368's (cross_project_check; skipped with a warning if case-368 is not built).

Run from this project's folder (enclosures/case-426) with a Python 3.11 virtual environment made from requirements.txt (README.md, "Build"):

    python -B src/build.py            # the print builds, the shared-part check, print/4.26/
    python -B src/build.py --no-check
    python -B src/build.py --only standard-nodev,chinless     # just those, side by side; never writes print/4.26/
    $env:SILKSCREEN_VARIANT = 'standard'; python -B src/build.py      # one (PowerShell)

Each axis is read from the slug (params): what the checks see follows the flags, never the name.
light strip  (LIGHT_STRIP) the checks use the plain GDEY0426T82 and the light strip (refs.py), not the FT01C, which
             does not fit that tub; strip_check adds the clearances and contacts -> out/<build>/light-strip.json.
             Otherwise the FT01C (panel.py) and its three ribbons.
chinless     (not BOTTOM_KEYS) no bottom-key parts or checks; chin_check proves every bottom-key feature absent and
             the rest equal to its keyed twin's -> out/<build>/chin.json.
side keys    (TAB_ROOTS) only the layout's keys are built (skey_<ref>); a left-out key is the plain wall, which
             sides_check proves against the all-keys twin -> out/<build>/sides.json.
-nodev       (not DEV_HEADER) J6 not fitted: header_closed_check proves the top wall closed and the top tongue
             complete -> out/<build>/header.json.
Every build is also proven against its twins (variants.twins: the same configuration with one axis at its default),
for the parts that axis must not change (shares): the one it derives from by its last token in out/<build>/shared.json
(as before the variants), every twin in out/shares-all.json. A twin that is not built fails the check (pipeline.py
brings every twin into the run).
"""
import json, os, re, shutil, sys, time
import numpy as np
from pathlib import Path
import cadquery as cq
import hw
import params as P
import variants
import tub, lid, midplate, keys, refs, sidekeys, body, coupons
from geom import box

OUT = P.OUT
PRINT = hw.ROOT.parents[1] / 'print' / '4.26'   # committed, at the repo root: what to print (write_print)

PARTS = {                       # id: (builder, colour, material note) - the printed parts
    'tub': (tub.build, '#e8e1d0', 'PLA'),
    'lid': (lid.build, '#d9d0bc', 'PLA'),          # Rev J: with the five side keys, which are part of it
    'midplate': (midplate.build, '#6f7a70', 'PLA'),
    # the bottom keys and their cranks as assembled, at rest on an MJTP1117 (the modelled switch)
    **{f'key_{r}': ((lambda r=r: keys.key(keys.key_x(r))), c, 'PLA') for r, c in
       zip(P.KEY_REFS, ['#c8553d', '#3d3f45', '#3d3f45', '#3d3f45'])},
    **{f'crank_{r}': ((lambda r=r: keys.crank('M', keys.key_x(r))), '#8a8f98', 'PLA') for r in P.KEY_REFS},
    # the side gate (SPEC2 rev 3) seated in its slot in the -X wall: the rod's left stop
    **({'gate': (keys.gate, '#3d3f45', 'PLA')} if P.BOTTOM_KEYS else {}),
}
# What print/4.26/ gets for the bottom keys, in the CAD frame at the key's centre (X 0): one key part for all
# four (key-426: both builds have the face at 6.00; the hook key of test 2, the same solid printed and assembled),
# the crank in its two nose variants, the chin coupon (the hook keys' optional fit check) and the gate coupon
# (coupons.py). The gate is a PARTS entry (out/<variant>/gate.stl, as installed); write_print puts it in
# print/4.26/ in its print pose.
BOTTOM_KEY_PRINT_PARTS = ('key-426', 'crank-M', 'crank-T', *coupons.BOTTOM_KEY_COUPON, coupons.GATE_COUPON)
PRINT_PARTS = BOTTOM_KEY_PRINT_PARTS if P.BOTTOM_KEYS else ()


def print_parts(tub_shape):
    if not P.BOTTOM_KEYS:
        return {}
    return {'key-426': keys.key(), 'crank-M': keys.crank('M'), 'crank-T': keys.crank('T'),
            **coupons.bottom_key_coupon(tub_shape), coupons.GATE_COUPON: coupons.gate_coupon(tub_shape)}
# The side keys move, so every check (and the showcase) takes the lid apart into its fixed body and the
# five keys: lid_body.stl and skey_*.stl. They meet only on each key's root face, so the pair shows no
# overlap, and lid_body + the keys is the printed lid.
SIDE_KEYS = [f'skey_{r}' for r in P.TAB_ROOTS]
# what a build without the bottom keys must not have in its folder (stale_files): every file the bottom keys make
BOTTOM_KEY_FILES = ('key_*', 'crank_*', 'gate*', 'coupon-*', 'key-426*', 'crank-M*', 'crank-T*', 'ref_rod*', 'bottom-keys.json')


def stale_files():
    """Files in OUT that this build does not make but a reader would take for its own: side keys it no longer has
    (enclosures/make_plates.py reads every skey_*.stl as the lid's), and without the bottom keys every bottom-key file
    (plates.py, make_plates.py and the showcase would pick them up)."""
    out = [f for f in OUT.glob('skey_*.stl') if f.stem not in SIDE_KEYS]
    if not P.BOTTOM_KEYS:
        out += [f for g in BOTTOM_KEY_FILES for f in OUT.glob(g)]
    return sorted(set(out))


PRINTED_LID = []        # build_all: the printed lid (with its keys) as built; shapes['lid'] is its body (sides_check)


def build_all():
    for f in stale_files():
        f.unlink()
        print(f'removed stale {f.name}', flush=True)
    shapes = {}
    for pid, (fn, _, _) in PARTS.items():
        t0 = time.time()
        wp = fn()
        n = len(wp.solids().vals())
        shapes[pid] = wp
        cq.exporters.export(wp, str(OUT / f'{pid}.stl'), tolerance=0.02, angularTolerance=0.1)
        cq.exporters.export(wp, str(OUT / f'{pid}.step'))
        print(f'{pid:10s} solids={n} vol={wp.val().Volume():8.1f} mm3  {time.time() - t0:5.1f}s', flush=True)
    printed_lid = shapes['lid']
    PRINTED_LID[:] = [printed_lid]
    shapes['lid'] = lid.build(keys=False)
    cq.exporters.export(shapes['lid'], str(OUT / 'lid_body.stl'), tolerance=0.02, angularTolerance=0.1)
    for r in P.TAB_ROOTS:
        shapes[f'skey_{r}'] = sidekeys.build(r)
        cq.exporters.export(shapes[f'skey_{r}'], str(OUT / f'skey_{r}.stl'), tolerance=0.02, angularTolerance=0.1)
    gap = printed_lid.val().Volume() - shapes['lid'].val().Volume() - sum(shapes[k].val().Volume() for k in SIDE_KEYS)
    print(f'lid = body + keys to {gap:+.4f} mm3 ({len(printed_lid.solids().vals())} solid)', flush=True)
    if P.LIGHT_STRIP:
        sf = refs.strip_front()
        ref_parts = (('ref_display', refs.plain_display()), ('ref_battery', refs.battery()),
                     ('ref_strip', sf['strip_bar'].union(sf['strip_leds'])))
    else:
        ref_parts = (('ref_display', refs.display()), ('ref_battery', refs.battery()))
    # the bottom keys' rod (a cut length of filament): not printed, but shown with the case
    if P.BOTTOM_KEYS:
        ref_parts += (('ref_rod', keys.rod()),)
    for name, wp in ref_parts:
        cq.exporters.export(wp, str(OUT / f'{name}.stl'), tolerance=0.02)
    if P.LIGHT_STRIP:
        import trimesh
        tail = refs.strip_tail('nominal')[0]
        trimesh.util.concatenate([tail['strip_tail'], tail['strip_diodes'], refs.plain_fpc()]).export(OUT / 'ref_strip_tail.stl')
    for name, wp in print_parts(shapes['tub']).items():
        cq.exporters.export(wp, str(OUT / f'{name}.stl'), tolerance=0.02, angularTolerance=0.1)
        cq.exporters.export(wp, str(OUT / f'{name}.step'))
        print(f'{name:22s} solids={len(wp.solids().vals())} vol={wp.val().Volume():8.1f} mm3 (print part)', flush=True)
    return shapes


def interference(shapes, min_vol=1e-3):
    """Every printed part against every hardware solid, the display and the battery envelope,
    and every part against every other part, in the assembled position."""
    hwsol = hw.solids()
    if P.LIGHT_STRIP:
        # the plain panel (its PS face on the 4.00 stops; the thick one's rear, 2.974, is 0.026 past the
        # midplate as modelled at its nominal seat 3.0, which the springs take up) and the strip
        sf = refs.strip_front()
        others = {'display': refs.plain_display().val(), 'battery': refs.battery().val(),
                  'display_thick': refs.plain_display(total=P.PLAIN['t'] + P.PLAIN['t_tol']).val(),
                  'strip_bar': sf['strip_bar'].val(), 'strip_leds': sf['strip_leds'].val()}
    else:
        others = {'display': refs.display().val(), 'battery': refs.battery().val(),
                  'display_thick': refs.display(thickness=hw.PANEL_T + hw.PANEL_T_TOL).val()}
    if P.BOTTOM_KEYS:
        others.update({'rod': keys.rod().val()})
    rep = []
    for pid, wp in shapes.items():
        s = wp.val()
        sb = s.BoundingBox()
        for ref, h in list(hwsol.items()) + list(others.items()):
            hb = h.BoundingBox()
            if hb.xmin > sb.xmax or hb.xmax < sb.xmin or hb.ymin > sb.ymax or hb.ymax < sb.ymin or hb.zmin > sb.zmax or hb.zmax < sb.zmin:
                continue
            v = s.intersect(h).Volume()
            if v > min_vol:
                ib = s.intersect(h).BoundingBox()
                rep.append({'part': pid, 'with': ref, 'volume': round(v, 4), 'expected': (pid, ref) in EXPECTED,
                            'where': [round(x, 2) for x in (ib.xmin, ib.xmax, ib.ymin, ib.ymax, ib.zmin, ib.zmax)]})
    ids = list(shapes)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            v = shapes[a].val().intersect(shapes[b].val()).Volume()
            if v > min_vol:
                ib = shapes[a].val().intersect(shapes[b].val()).BoundingBox()
                rep.append({'part': a, 'with': b, 'volume': round(v, 4),
                            'where': [round(x, 2) for x in (ib.xmin, ib.xmax, ib.ymin, ib.ymax, ib.zmin, ib.zmax)]})
    return rep


def insertion_check(shapes, min_vol=1e-3):
    """The assembly path, not just the assembled position: with the tub face down (keys already
    in), the panel and then the midplate go in from the back. Each layer of the panel, at the
    drawing's largest outline, and the midplate's outline are swept from beyond the parting plane
    to where they sit; anything of the tub or the keys inside that path would stop them.
    Rev E failed this (its walls below the pocket stood 1.2 mm inside the panel's edge)."""
    import panel
    tx, ty = hw.PANEL_W_TOL / 2, hw.PANEL_H_TOL / 2
    paths = {}
    # light-strip: the plain panel's layers, and the strip taped on it, which go in with it: the bar, the top
    # piece and the LEDs (their own outlines, grown by the panel's tolerance), and the U the tail makes round
    # the glass's edge (its furthest reach) - the tail is folded before the stack goes in
    for name, layer in (refs.plain_body() if P.LIGHT_STRIP else panel.body()).items():
        b = layer.val().BoundingBox()
        paths[f'panel_{name}'] = box(b.xmin - tx, b.xmax + tx, b.ymin - ty, b.ymax + ty, P.SEAM - 1.0, b.zmax)
    if P.LIGHT_STRIP:
        g = refs.strip_geometry()
        for i, piece in enumerate(g['front_pieces']):
            pts = [refs._cad(q) for q in piece]
            paths[f'strip_piece{i}'] = refs._extrude(pts, P.SEAM - 1.0, P.STRIP_FLEX_TOP)
        sf = refs.strip_front()
        for i, led in enumerate(sf['strip_leds'].solids().vals()):
            b = led.BoundingBox()
            paths[f'strip_led{i + 1}'] = box(b.xmin - tx, b.xmax + tx, b.ymin - ty, b.ymax + ty, P.SEAM - 1.0, b.zmax)
        import shapely.geometry as sg
        neck = sg.Polygon(g['outline']).intersection(sg.LineString([(0, g['fold_y']), (120, g['fold_y'])])).bounds
        u = refs.StripPath('reach')
        paths['strip_u'] = box(neck[0] - 44.24 - tx, neck[2] - 44.24 + tx, u.u_reach_y - ty, hw.PANEL_Y0, P.SEAM - 1.0, u.z_ledge + u.H)
    b = shapes['midplate'].val().BoundingBox()
    # the plate's own outline: its four detent bumps ride into the wall by design (they flex; see
    # mechanics.mid_detents), so they are not part of the path
    x0, x1 = P.POCKET_X0 + midplate.EDGE_CLR, P.POCKET_X1 - midplate.EDGE_CLR
    paths['midplate'] = box(x0, x1, b.ymin, b.ymax, P.SEAM - 1.0, b.zmax)
    rep = {}
    for pname, path in paths.items():
        hits = {}
        for pid, wp in shapes.items():
            if pid == 'tub' or pid.startswith('key_'):
                inter = wp.val().intersect(path.val())
                v = inter.Volume()
                if v > min_vol:
                    ib = inter.BoundingBox()
                    hits[pid] = {'mm3': round(v, 4), 'where': [round(x, 2) for x in (ib.xmin, ib.xmax, ib.ymin, ib.ymax, ib.zmin, ib.zmax)]}
        pb = path.val().BoundingBox()
        rep[pname] = {'path_x': [round(pb.xmin, 3), round(pb.xmax, 3)], 'path_y': [round(pb.ymin, 3), round(pb.ymax, 3)],
                      'seated_top_z': round(pb.zmax, 3), 'hits': hits}
    if P.LIGHT_STRIP:
        rep['_across'] = insertion_across(shapes, paths, min_vol)
    return rep


def insertion_across(shapes, paths, min_vol=1e-3):
    """Light-strip: the stack pushed in across the pocket (README fitting step 5), not only centred.
    The glass (at its largest) against the left wall or the right wall (P.STRIP_INSERT_GLASS_X0), and the
    strip at both ends and the middle of its placement on it (P.STRIP_PLACE); the bar and top piece, the
    LEDs and the U move with it. The paths run from beyond the parting plane to the seat, so a gap is over
    the whole stroke. bar_gap / glass_gap: to the pocket's left wall (the tub left of X -0.9 and between the
    pocket's bottom and top walls, from its back rim to just under the hold-downs, whose 0.015 over the bar
    is the seat, not the stroke)."""
    tx, ty = hw.PANEL_W_TOL / 2, hw.PANEL_H_TOL / 2
    sf = refs.strip_front()
    tub = shapes['tub'].val()
    lwall = tub.intersect(box(-4.0, -0.9, P.POCKET_Y0 + 0.5, P.POCKET_Y1 - 0.5, P.SEAM - 2.0, P.STRIP_HOLD['z'] - 0.005).val())
    wg = hw.PANEL_W + P.PLAIN_OUTLINE_TOL
    z_glass = P.PLAIN_FRONT - P.PLAIN['ps'] - P.PLAIN['fpl']
    strip = [paths['strip_piece0'].val(), paths['strip_piece1'].val()]
    for led in sf['strip_leds'].solids().vals():
        b = led.BoundingBox()
        strip.append(box(b.xmin, b.xmax, b.ymin - ty, b.ymax + ty, P.SEAM - 1.0, b.zmax).val())
    strip = cq.Compound.makeCompound(strip)
    ub = paths['strip_u'].val().BoundingBox()
    across = {}
    PL = P.STRIP_PLACE
    for wall, gx0 in P.STRIP_INSERT_GLASS_X0.items():
        glass = box(gx0, gx0 + wg, hw.PANEL_Y0 - ty, hw.PANEL_Y1 + ty, P.SEAM - 1.0, z_glass).val()
        for inset in (PL['inset'] - PL['tol'], PL['inset'], PL['inset'] + PL['tol']):
            dx = gx0 + inset - PL['bar_x0']
            s2 = strip.moved(cq.Location(cq.Vector(dx, 0, 0)))
            u2 = box(ub.xmin + tx + dx, ub.xmax - tx + dx, ub.ymin, ub.ymax, ub.zmin, ub.zmax).val()
            hits = {}
            for part, path in (('glass', glass), ('strip', s2), ('strip_u', u2)):
                for pid, wp in shapes.items():
                    if pid == 'tub' or pid.startswith('key_'):
                        v = wp.val().intersect(path).Volume()
                        if v > min_vol:
                            hits[f'{part} x {pid}'] = round(v, 4)
            bar_gap = lwall.distance(s2)
            across[f'glass at the {wall}, bar {inset:.1f} inside its edge'] = {
                'glass_x0': round(gx0, 3), 'bar_x0': round(gx0 + inset, 3), 'strip_dx_from_drawn': round(dx, 3),
                'bar_gap': round(bar_gap, 3), 'glass_gap': round(lwall.distance(glass), 3), 'hits': hits,
                'clear': not hits and bar_gap > 1e-3}
    return across


def _sweep(m, f, n, step):
    worst = (0.0, None)
    for i in range(1, n + 1):
        v = m.moved(cq.Location(cq.Vector(0, 0, -i * step))).intersect(f).Volume()
        if v > worst[0]:
            worst = (v, round(i * step, 2))
    return worst


CROP_G = 0.5                    # later_moves: the crop boxes' margin round the mover (mm)


def later_moves(shapes, step=0.25, travel=10.0, min_vol=1e-3):
    """The parts that go in after the panel, moved along their way in (all from the back of the
    face-down tub, so along -Z from their seats):
      pcba_in  J1, SW11 and the side switches - the board's parts nearest the walls - against the
               tub, the keys and the midplate; and the board past the battery bay
      lid_on   the lid (Rev J: with its side keys) against the midplate and the board's edge parts, and
               each side key against the tub: the key's block slides up its slot and the nub up the
               sliver's window. The latch barbs ride up the tub's wall by design (they flex), so the
               lid body x tub pair is left out
    Reports the worst overlap on each path; the bottom switches are left out: their plungers pass the
    cranks' noses by design, which bottom_keys_check follows with the crank free to turn.
    Each sweep meets only the part of the fixed solid the mover can reach (2026-10-08, the variants SPEC's stage
    2d): the fixed part cropped to the mover's box grown by CROP_G, from the travel below it to its top (below);
    for the lid, which is the mover there, the lid cropped to the fixed part's box raised by the travel (above). The
    moved mover lies inside that box at every step of the way, so each intersection is the same point set as with
    the whole part, at a fraction of the time; a crop that is empty has nothing the mover can reach (skipped)."""
    g = CROP_G

    def below(m, f):
        mb = m.BoundingBox()
        return f.intersect(box(mb.xmin - g, mb.xmax + g, mb.ymin - g, mb.ymax + g, mb.zmin - travel - g, mb.zmax + g).val())

    def above(m, f):
        fb = f.BoundingBox()
        return m.intersect(box(fb.xmin - g, fb.xmax + g, fb.ymin - g, fb.ymax + g, fb.zmin - g, fb.zmax + travel + g).val())
    hwsol = hw.solids()
    movers = {r: hwsol[r] for r in ('J1', 'SW11', *hw.LEFT_SWITCHES, *hw.RIGHT_SWITCHES)}
    fixed = {k: shapes[k].val() for k in shapes if k in ('tub', 'midplate') or k.startswith(('key_', 'crank_'))}
    rep = {'pcba_in': {}, 'lid_on': {}}
    n = int(round(travel / step))
    for name, m in movers.items():
        for fname, f in fixed.items():
            mb, fb = m.BoundingBox(), f.BoundingBox()
            if mb.xmax < fb.xmin or mb.xmin > fb.xmax or mb.ymax < fb.ymin or mb.ymin > fb.ymax:
                continue
            f = below(m, f)
            if f.Volume() <= 0.0:
                continue
            worst = _sweep(m, f, n, step)
            if worst[0] > min_vol:
                rep['pcba_in'][f'{name} x {fname}'] = {'mm3': round(worst[0], 4), 'at_mm_below_seat': worst[1]}
    # Rev H: the board itself past the midplate's battery bay, whose rails and cleats stand up
    # through the board's notch within 0.3 mm of its edge (the snap posts, which pass through the
    # holes by design, are outside this crop)
    bay = shapes['midplate'].val().intersect(box(-2.0, 45.0, 79.0, 112.0, -6.0, 3.0).val())
    worst = (0.0, None)
    for i in range(1, n + 1):
        v = hwsol['PCB'].moved(cq.Location(cq.Vector(0, 0, -i * step))).intersect(bay).Volume()
        if v > worst[0]:
            worst = (v, round(i * step, 2))
    if worst[0] > min_vol:
        rep['pcba_in']['PCB x battery bay'] = {'mm3': round(worst[0], 4), 'at_mm_below_seat': worst[1]}
    # the lid: its latch arms stand 7 mm tall, up past the board's edge and the midplate's, and its side
    # keys rise past the parting line into the tub
    near = {r: hwsol[r] for r in ('PCB', 'J1', 'SW11', *hw.LEFT_SWITCHES, *hw.RIGHT_SWITCHES)}
    lid_s = shapes['lid'].val()
    for k in SIDE_KEYS:
        lid_s = lid_s.fuse(shapes[k].val())
    for fname, f in {'midplate': shapes['midplate'].val(), **near}.items():
        ml = above(lid_s, f)
        if ml.Volume() <= 0.0:
            continue
        worst = _sweep(ml, f, n, step)
        if worst[0] > min_vol:
            rep['lid_on'][f'lid x {fname}'] = {'mm3': round(worst[0], 4), 'at_mm_below_seat': worst[1]}
    tub_s = shapes['tub'].val()
    for k in SIDE_KEYS:                 # (the tub round a key is never empty: an empty crop would raise, loudly)
        m = shapes[k].val()
        worst = _sweep(m, below(m, tub_s), n, step)
        if worst[0] > min_vol:
            rep['lid_on'][f'{k} x tub'] = {'mm3': round(worst[0], 4), 'at_mm_below_seat': worst[1]}
    return rep


EXPECTED = {                    # contacts that are the design, not a clash
    ('ribbon_main', 'J2'), ('ribbon_light', 'J3'), ('ribbon_touch', 'J4'), ('battery_plug', 'J5'),
    # light-strip: the plain panel's EPD FPC in J2, the strip's tail in J3. Both: the springs' take-up on a
    # thick panel (the plate is modelled at its nominal seat, as the FT01C's display_thick always showed)
    ('ribbon_plain_fpc', 'J2'), ('strip_tail', 'J3'), ('strip_tail_reach', 'J3'), ('midplate', 'display_thick'),
    # the side gate sits on its slot's floor and bears on the lips: a touch (zero volume), listed in case the
    # tessellation-free solids ever read a trace of overlap there (gate_check measures it)
    ('tub', 'gate'),
}
# strip_check's pairs that touch by design (the tail's tip in J3; the stiffened end and the bare flex on the
# board's back and on the glass ledge; the tail's start against the foot)
EXPECTED_STRIP = {('strip_tail', 'J3'), ('strip_tail', 'PCB'), ('strip_tail', 'plain_display'),
                  ('strip_diodes', 'strip_tail')}


def mesh_interference(min_vol=1e-3):
    """Display ribbons and the battery's leads and plug (meshes) against every printed part and
    the hardware near them, with manifold booleans."""
    import trimesh
    import panel
    if P.LIGHT_STRIP:
        # the plain panel's EPD FPC and the strip's tail (nominal and furthest-reaching U) take the FT01C's
        # three ribbons' place
        items = {'ribbon_plain_fpc': refs.plain_fpc()}
        for case in P.STRIP_TAIL:
            sfx = '' if case == 'nominal' else f'_{case}'
            for k, m in refs.strip_tail(case)[0].items():
                items[k + sfx] = m
    else:
        items = {f'ribbon_{k}': m for k, m in panel.ribbons().items()}
    items.update({k: m for k, m in refs.battery_meshes().items() if k != 'battery_cell'})
    parts = {n: trimesh.load(OUT / f'{n}.stl') for n in PARTS}
    hwsol = hw.solids()
    rep = []
    for name, m in items.items():
        lo, hi = m.bounds
        others = {k: [o] for k, o in parts.items()}
        for ref, s in hwsol.items():
            b = s.BoundingBox()
            if b.xmax < lo[0] or b.xmin > hi[0] or b.ymax < lo[1] or b.ymin > hi[1] or b.zmax < lo[2] or b.zmin > hi[2]:
                continue
            # the part cropped to the item's box, one mesh per solid, so a vendor STEP whose whole tessellation
            # is not a closed volume (SW9's) is still measured, not skipped
            others[ref] = _hw_meshes(s, lo, hi)
        for other, os_ in others.items():
            v, ibs = 0.0, []
            for o in os_:
                if (o.bounds[1] < lo).any() or (o.bounds[0] > hi).any():
                    continue
                try:
                    inter = trimesh.boolean.intersection([m, o], engine='manifold')
                    if not inter.is_empty and inter.volume > 0:
                        v += inter.volume
                        ibs.append(inter.bounds)
                except Exception as e:                  # not a closed mesh: exact, the item sewn into a BREP
                    b = o.metadata.get('brep')
                    if b is None or not m.is_watertight:
                        v += float('nan')
                        continue
                    inter = _mesh_solid(m).intersect(b)
                    if inter.Volume() > 0:
                        v += inter.Volume()
                        bb = inter.BoundingBox()
                        ibs.append(np.array([[bb.xmin, bb.ymin, bb.zmin], [bb.xmax, bb.ymax, bb.zmax]]))
            if not v <= min_vol:                         # NaN (not measurable) is reported too
                ib = (np.min([q[0] for q in ibs], axis=0), np.max([q[1] for q in ibs], axis=0)) if ibs else m.bounds
                rep.append({'part': name, 'with': other, 'volume': round(float(v), 4),
                            'expected': (name, other) in EXPECTED,
                            'where': [round(float(x), 2) for x in (ib[0][0], ib[1][0], ib[0][1], ib[1][1], ib[0][2], ib[1][2])]})
    return rep


def _tess(shape, tol=0.02):
    import trimesh
    vs, ts = shape.tessellate(tol, 0.2)
    return trimesh.Trimesh([(v.x, v.y, v.z) for v in vs], ts, process=True)


def _clip(mesh, lo, hi):
    """The part of a mesh's surface inside the box (lo, hi), or None."""
    import trimesh
    m = mesh
    for ax in range(3):
        for sign, val in ((1.0, lo[ax]), (-1.0, hi[ax])):
            n, o = np.zeros(3), np.zeros(3)
            n[ax], o[ax] = sign, val
            m = trimesh.intersections.slice_mesh_plane(m, n, o, cap=False)
            if m is None or len(m.faces) == 0:
                return None
    return m


def _surface_points(mesh, size):
    import trimesh
    v, f = trimesh.remesh.subdivide_to_size(mesh.vertices, mesh.faces, max_edge=size, max_iter=30)
    return v


def mesh_gap(a, b, margin=1.5):
    """Smallest distance between two meshes' surfaces, coarse to fine: both clipped to the box round the
    other, subdivided (0.4 mm) and compared point to point (a k-d tree); then again at 0.1 where the gap is
    within 0.6 of that minimum, and at 0.025 round the closest point, so the result is within a few
    hundredths of the true gap (gaps over 1 mm stay at the coarse pass, +-0.3). None when b has nothing
    within margin of a."""
    from scipy.spatial import cKDTree
    lo, hi = a.bounds
    bc = _clip(b, lo - margin, hi + margin)
    if bc is None:
        return None
    ac = _clip(a, bc.bounds[0] - margin, bc.bounds[1] + margin)
    if ac is None:
        return None
    best = np.inf
    for size, grow in ((0.4, 0.6), (0.1, 0.15), (0.025, None)):
        pa = _surface_points(ac, size)
        d, _ = cKDTree(_surface_points(bc, size)).query(pa)
        k = int(np.argmin(d))
        best = min(best, float(d[k]))
        if grow is None or best > 1.0:                           # a gap over 1 mm needs no finer answer
            break
        if size == 0.4:
            near = pa[d <= d[k] + grow]
            nlo, nhi = near.min(axis=0) - grow, near.max(axis=0) + grow
        else:
            nlo, nhi = pa[k] - 0.4, pa[k] + 0.4
        r = d[k] + grow + 0.1
        ac2, bc2 = _clip(ac, nlo, nhi), _clip(bc, nlo - r, nhi + r)
        if ac2 is None or bc2 is None:
            break
        ac, bc = ac2, bc2
    return round(best, 3)


def _hw_meshes(s, lo, hi, grow=0.5):
    """A hardware part's BREP cropped to the box (lo, hi) grown by `grow`, as one mesh per solid. The whole
    part's tessellation is often not a closed volume (SW9's STEP: the manifold boolean refused it, and its
    overlap with the tail came back NaN); each cropped solid's is."""
    c = s.intersect(box(lo[0] - grow, hi[0] + grow, lo[1] - grow, hi[1] + grow, lo[2] - grow, hi[2] + grow).val())
    out = []
    for so in c.Solids():
        if so.Volume() > 1e-6:
            mm = _tess(so)
            mm.metadata['brep'] = so                     # for _overlap's exact fallback
            out.append(mm)
    return out


_SOLIDS = {}


def _mesh_solid(m):
    """A closed mesh as a BREP (one solid per closed shell), sewn from its triangles: exact booleans against a
    hardware part whose own tessellation is not closed (the PCB's cropped slab, SW9)."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace, BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid
    from OCP.gp import gp_Pnt
    from OCP.TopoDS import TopoDS
    from OCP.TopAbs import TopAbs_SHELL
    from OCP.TopExp import TopExp_Explorer
    key = id(m)
    if key not in _SOLIDS:
        sew = BRepBuilderAPI_Sewing(1e-5)
        for tri in m.triangles:
            poly = BRepBuilderAPI_MakePolygon(*(gp_Pnt(*map(float, q)) for q in tri), True)
            sew.Add(BRepBuilderAPI_MakeFace(poly.Wire(), True).Face())
        sew.Perform()
        ex, sols = TopExp_Explorer(sew.SewedShape(), TopAbs_SHELL), []
        while ex.More():
            sols.append(cq.Solid(BRepBuilderAPI_MakeSolid(TopoDS.Shell_s(ex.Current())).Solid()))
            ex.Next()
        _SOLIDS[key] = (m, cq.Compound.makeCompound(sols))    # keep m alive so its id stays its own
    return _SOLIDS[key][1]


def _overlap(m, others):
    """Volume of the closed mesh m inside the meshes `others`: manifold boolean, or where an obstacle's mesh is
    not a closed volume, m sewn into a BREP against the obstacle's own BREP. NaN if neither is possible."""
    import trimesh
    v = 0.0
    for o in others:
        try:
            inter = trimesh.boolean.intersection([m, o], engine='manifold')
            v += float(inter.volume) if not inter.is_empty else 0.0
        except Exception:
            b = getattr(o, 'metadata', {}).get('brep')
            if b is None:
                return float('nan')
            v += _mesh_solid(m).intersect(b).Volume()
    return v


def _gap(m, others, margin):
    gs = [g for g in (mesh_gap(m, o, margin=margin) for o in others) if g is not None]
    return min(gs) if gs else None


def sw9_trimmed():
    """SW9 with its left mounting-lug lead trimmed to SW9_LEAD_TRIM z and covered with Kapton (README's
    fitting step): the lead above z goes, and the stub and its tape are a block to z + kapton."""
    T = P.SW9_LEAD_TRIM
    s = hw.solids()['SW9']
    s = s.cut(box(T['x'][0], T['x'][1], T['y'][0], T['y'][1], T['z'], 5.0).val())
    return s.fuse(box(T['x'][0], T['x'][1], T['y'][0], T['y'][1], P.PCB_FRONT, T['z'] + T['kapton']).val())


def strip_check(shapes):
    """Light-strip variant: the clearances that matter, measured on the parts as built (BREP distance for
    the solids, each part cropped to the region in question; mesh distance for the bent tail), and the
    contacts that are the design:
      stops on the PS - 0, and no volume; hold-downs 0.015 over the bar's flex top
      LED tops under the raised ceiling, the foot under the skin and past the wall
      the strip moved over its whole placement box (STRIP_SWEEP): the pads against the LEDs' solder pads
      and bodies, the bar against the pocket's left wall and its relief
      the tail (nominal and furthest-reaching U) against everything in the chin, the slot and the back, and
      moved sideways by STRIP_SWEEP dx against SW9 (as it is, and with its lug lead trimmed) and the tub
    A chinless light-strip build has no SW9 (hw.DNP), no key_SW9 and no crank_SW9: its tail is measured against
    everything else, and sideways against the tub alone (at dx 0 too)."""
    import trimesh
    t0 = time.time()
    tub = shapes['tub'].val()
    sf = refs.strip_front()
    bar, leds, cu = sf['strip_bar'].val(), sf['strip_leds'].val(), sf['strip_copper'].val()
    pb = refs.plain_body()
    ps = pb['ps'].val()
    plain = refs.plain_display().val()
    out = {'solids': {}, 'sweep': {}, 'tail': {}, 'tail_sideways': {}}

    def solid(name, a, b, crop=None):
        if crop is not None:
            a = a.intersect(box(*crop).val())
        v = a.intersect(b).Volume()
        out['solids'][name] = {'gap': round(a.distance(b), 3), 'overlap_mm3': round(v, 4)}
        print(f'  {name:46s} {out["solids"][name]}  ({time.time() - t0:.0f}s)', flush=True)
    H = P.STRIP_HOLD
    zc = P.STRIP_CEIL['z']
    px1 = H['x'][1] + 0.3            # the pad crops reach 0.3 past the pads' inner end (STRIP_HOLD x)
    solid('tub stops x plain PS', tub, ps, (2.0, 60.0, 10.0, 110.0, 3.8, 4.2))
    solid('tub hold-downs x strip bar', tub, bar, (-1.6, px1, 9.0, 110.0, 4.2, 4.5))
    solid('tub x LEDs (ceiling, pads)', tub, leds, (-1.6, 2.0, 12.0, 110.0, 4.2, 5.6))
    solid('tub pads x LED solder pads', tub, cu, (-1.3, px1, 12.0, 110.0, 4.2, zc - 0.01))
    solid('strip bar x plain panel (tape on PS)', bar, plain)
    # the foot either side of its pad, against the tub with the pads cropped away
    fx0, fx1 = H['foot']['x']
    foot_r = bar.intersect(box(fx1 + 0.3, 14.0, 9.0, 12.8, 3.0, 5.0).val())
    solid('tub x foot right of its pad (skin, stop)', tub, foot_r, (fx1 + 0.3, 16.0, 7.5, 14.5, 3.8, 5.3))
    foot_l = bar.intersect(box(-2.0, fx0 - 0.3, 9.0, H['ys'][0][0] - 0.3, 3.0, 5.0).val())
    solid('tub x foot left end (skin, wall)', tub, foot_l, (-3.0, fx0 - 0.3, 7.5, H['ys'][0][0] - 0.3, 3.8, 5.3))
    solid('tub pads x LEDs, sideways', tub, leds, (-1.6, px1, 12.0, 110.0, 4.35, 5.25))
    solid('tub x bar, left wall and relief (below the pads)', tub, bar, (-2.5, -0.9, 8.0, 110.5, 3.6, H['z'] - 0.01))
    # over the relief the wall is the same all along the bar; the pads run into it, so it is measured between two
    # of them (WALL_BAND), where the crop can reach the wall face itself (the fix round's crop stopped 0.02 short
    # of it, at X -1.43, and read 0.013 large: 0.287 for the true 0.274)
    WALL_BAND = (H['ys'][0][1] + 0.6, H['ys'][1][0] - 0.5)
    solid('tub x bar, wall over the relief (between pads)', tub, bar, (-2.5, -0.9, *WALL_BAND, 3.6,
                                                                      P.STRIP_WALL_RELIEF['z1'] + 0.3))
    # the strip moved over its placement box: the pads (the tub below the ceiling from X -1.3, so the pocket
    # wall is not in it) against the LEDs' solder pads and bodies; the wall (below the pads) against the bar
    S = P.STRIP_SWEEP
    pads = tub.intersect(box(-1.3, px1, 12.0, 110.0, 4.2, zc - 0.01).val())
    # the wall below the pads, and up past the relief's top face (z1) between two pads (WALL_BAND, above)
    wall = tub.intersect(box(-2.5, -0.9, 8.0, 110.5, 3.6, H['z'] - 0.01).val()).fuse(
        tub.intersect(box(-2.5, -0.9, *WALL_BAND, 3.6, P.STRIP_WALL_RELIEF['z1'] + 0.3).val()))
    # the bottom stop rail (from X 14.3) against the foot's right end, which the new placement moves right
    stop = tub.intersect(box(12.0, 16.0, 8.0, 15.0, 3.9, 4.6).val())
    assert abs(bar.BoundingBox().xmin - P.STRIP_PLACE['bar_x0']) < 1e-3, 'STRIP_PLACE bar_x0 is not the drawn bar'
    rows = []
    # dx 0 is the strip as drawn (0.055 past the glass's edge); STRIP_DX_FIT is the nominal placement
    for dx in (S['dx'][0], 0.0, P.STRIP_DX_FIT, S['dx'][1]):
        for dy in (S['dy'][0], 0.0, S['dy'][1]):
            L = cq.Location(cq.Vector(dx, dy, 0))
            c2, l2, b2 = cu.moved(L), leds.moved(L), bar.moved(L)
            rows.append({'dx': dx, 'dy': dy,
                         'pads_to_copper': round(pads.distance(c2), 3), 'copper_overlap_mm3': round(pads.intersect(c2).Volume(), 4),
                         'pads_to_leds': round(pads.distance(l2), 3), 'led_overlap_mm3': round(pads.intersect(l2).Volume(), 4),
                         'bar_to_wall': round(wall.distance(b2), 3), 'bar_wall_overlap_mm3': round(wall.intersect(b2).Volume(), 4),
                         'foot_to_stop': round(stop.distance(b2), 3)})
            print(f'  sweep {rows[-1]}  ({time.time() - t0:.0f}s)', flush=True)
    g = refs.strip_geometry()
    led_face = refs._cad((g['leds'][0]['x'], 0.0))[0] + g['led']['face_ahead']
    out['sweep'] = {'rows': rows, 'dx': list(S['dx']), 'dx_fit': P.STRIP_DX_FIT,
                    **{f'worst_{k}': min(r[k] for r in rows) for k in ('pads_to_copper', 'pads_to_leds', 'bar_to_wall', 'foot_to_stop')},
                    **{f'max_{k}': max(r[k] for r in rows)
                       for k in ('copper_overlap_mm3', 'led_overlap_mm3', 'bar_wall_overlap_mm3')},
                    'led_face_x': round(led_face, 3),
                    'led_face_to_window_edge_worst': round(P.WIN_X0 - (led_face + S['dx'][1]), 3),
                    # how far the LED faces stand ahead of the pads' inner end (STRIP_HOLD x; < 0: the pads' end
                    # is past the faces, beside the LEDs): as placed, with the glass centred and the bar on its
                    # edge (the fitting rule's worst), and at the box's left end (the glass on the left wall)
                    'led_face_ahead_of_pads': {
                        'as placed': round(led_face + P.STRIP_DX_FIT - H['x'][1], 3),
                        'glass centred, bar on its edge': round(led_face + hw.PANEL_X0 - P.STRIP_PLACE['bar_x0'] - H['x'][1], 3),
                        'box left end': round(led_face + S['dx'][0] - H['x'][1], 3)}}
    # tail meshes against the parts (STL) and the hardware near them (cropped BREP, one mesh per solid)
    hwsol = hw.solids()
    parts = {n: trimesh.load(OUT / f'{n}.stl')
             for n in ('tub', 'lid', 'midplate', *(('key_SW9', 'crank_SW9') if P.BOTTOM_KEYS else ()))}
    fpc = refs.plain_fpc()
    plain_m = _tess(plain)
    margins = {'lid': 6.0, 'key_SW9': 3.0, 'crank_SW9': 3.0, 'tub': 3.0}
    for case in P.STRIP_TAIL:
        meshes, path = refs.strip_tail(case)
        rep = {'path': path.report()}
        print(f'  tail {case}: {rep["path"]}', flush=True)
        for name, m in meshes.items():
            lo, hi = m.bounds
            obst = {k: [v] for k, v in parts.items()}
            for r, s in hwsol.items():
                b = s.BoundingBox()
                if b.xmax < lo[0] - 3 or b.xmin > hi[0] + 3 or b.ymax < lo[1] - 3 or b.ymin > hi[1] + 3 \
                        or b.zmax < lo[2] - 3 or b.zmin > hi[2] + 3:
                    continue
                ms = _hw_meshes(s, lo, hi, grow=3.0)
                if ms:
                    obst[r] = ms
            obst['plain_display'] = [plain_m]
            obst['plain_fpc'] = [fpc]
            if name != 'strip_tail':
                obst['strip_tail'] = [meshes['strip_tail']]
            r2 = {}
            for oname, os_ in obst.items():
                gp = _gap(m, os_, margins.get(oname, 1.5))
                if gp is None:
                    continue
                r2[oname] = {'gap': gp, 'overlap_mm3': round(_overlap(m, os_), 4), 'expected': (name, oname) in EXPECTED_STRIP}
                print(f'    {name:12s} x {oname:14s} {r2[oname]}  ({time.time() - t0:.0f}s)', flush=True)
            rep[name] = dict(sorted(r2.items(), key=lambda kv: kv[1]['gap']))
        out['tail'][case] = rep
        # sideways: the panel and the strip both at the ends of their X play move the neck and the U with them
        m = meshes['strip_tail']
        lo, hi = m.bounds
        near = ({'SW9': _hw_meshes(hwsol['SW9'], lo, hi, grow=1.0),
                 'SW9 lead trimmed + Kapton': _hw_meshes(sw9_trimmed(), lo, hi, grow=1.0)} if P.BOTTOM_KEYS else {})
        near['tub'] = [parts['tub']]
        at0 = 'SW9 lead trimmed + Kapton' if P.BOTTOM_KEYS else 'tub'   # the one row at dx 0
        side = {}
        for dx in (0.0, P.STRIP_DX_FIT, *S['dx']):
            m2 = m.copy()
            m2.apply_translation([dx, 0.0, 0.0])
            for oname, os_ in near.items():
                if dx == 0.0 and oname != at0:
                    continue
                side[f'{oname} @ dx {dx:+.3f}'] = {'gap': _gap(m2, os_, 3.0), 'overlap_mm3': round(_overlap(m2, os_), 4)}
                print(f'    tail {case} sideways: {oname} @ dx {dx:+.3f} {side[f"{oname} @ dx {dx:+.3f}"]}', flush=True)
        # the EPD FPC moves with the glass, so against it only the strip's placement on the glass counts: the
        # neck moves toward the FPC by STRIP_DX_FIT +- tol
        for dx in (P.STRIP_DX_FIT - P.STRIP_PLACE['tol'], P.STRIP_DX_FIT + P.STRIP_PLACE['tol']):
            m2 = m.copy()
            m2.apply_translation([dx, 0.0, 0.0])
            k = f'plain_fpc (strip placed on the glass) @ dx {dx:+.3f}'
            side[k] = {'gap': _gap(m2, [fpc], 3.0), 'overlap_mm3': round(_overlap(m2, [fpc]), 4)}
            print(f'    tail {case} sideways: {k} {side[k]}', flush=True)
        out['tail_sideways'][case] = side
    return out


RING_MJ_MIN = 0.03          # the cheek's ring to the MJTP1117 housing, crank and board at their worst (SPEC A5 c)
# The free swing (2026-10-12; Ian, from printed cases: "the crank hits a friction point when rotating from its button
# side to its switch side"). In the open tub, face down with the board out (assembly), a crank turned by hand swings
# from lying on its key to its nose on the rail's +Y face, and the corner where each cheek's flat top meets its second
# trim passes under the slot's roof at about +40. The checks above stop at +16 (the board's switch stops the crank
# there) and take the CAD on the rod's axis; this one takes the parts as they print: the face-down tub on its 0.2 layer
# grid from the face, the crank on its own (it prints pad end down), each layer its mid-plane's section; each face of
# the crank grown by the worst part growth (KEY_FDM part / 2); and gravity, which face down takes the crank on the rod
# and the rod in its ring bores through their play toward the face (+Z): bore reamed to 1.90, the ring bores 1.93 free
# as sliced (ROD_HOLE_D), the rod at its smallest. The crank over its cheeks' bands against the tub's shadow there (the
# well: the slot, its roof, the skin), from the hang to the end of the swing: >= `min` all the way.
FREE_SWING = dict(grow=round(max(P.KEY_FDM['part']) / 2, 3), rod_min=1.72, ring_free=1.93, step=0.5, min=0.05)
FREE_SWING_SAG = round((P.CRANK_BORE['ream'] - FREE_SWING['rod_min']) / 2 + (FREE_SWING['ring_free'] - FREE_SWING['rod_min']) / 2, 3)


def _as_printed(g, axis, origin, step=P.LAYER):
    """A (y, z) region as the slicer prints it in layers of `step` along `axis` ('y': the crank, printed pad end down;
    'z': the face-down tub) from `origin`: each layer is its mid-plane's section, carried across the layer."""
    import math
    from shapely.geometry import LineString, box as sbox
    from shapely.ops import unary_union
    if g.is_empty:
        return g
    y0, z0, y1, z1 = g.bounds
    lo, hi = (y0, y1) if axis == 'y' else (z0, z1)
    out = []
    for k in range(math.floor((lo - origin) / step) - 1, math.ceil((hi - origin) / step) + 1):
        a, b = origin + k * step, origin + (k + 1) * step
        m = (a + b) / 2
        s = g.intersection(LineString([(m, z0 - 1), (m, z1 + 1)] if axis == 'y' else [(y0 - 1, m), (y1 + 1, m)]))
        for seg in getattr(s, 'geoms', [s]):
            if seg.is_empty or seg.length < 1e-6:
                continue
            (p, q) = seg.coords[0], seg.coords[-1]
            out.append(sbox(a, min(p[1], q[1]), b, max(p[1], q[1])) if axis == 'y' else
                       sbox(min(p[0], q[0]), a, max(p[0], q[0]), b))
    return unary_union(out).buffer(0)


def _depth_gap(a, b):
    """The gap between two (y, z) regions; when they overlap, minus the overlap's depth (the deepest point of the
    overlap from b's boundary)."""
    from shapely.geometry import Point
    if not a.intersects(b):
        return round(a.distance(b), 4)
    ov = a.intersection(b)
    pts = [p for g in getattr(ov, 'geoms', [ov]) if g.geom_type == 'Polygon' for p in g.exterior.coords]
    return -round(max((b.boundary.distance(Point(p)) for p in pts), default=0.0), 4)


def crank_free_swing(shade, B, hang):
    """The free swing (FREE_SWING, above): each crank turned from where it hangs face down (`hang`, on its key at its
    stop) to where it first meets the tub turning + (CAD, on the rod's axis: the nose on the rail's +Y face; each nose
    variant), and over its cheeks' bands (crank-M; the cheeks are the same in crank-T) against the tub there: the CAD
    on the axis (reported), as sliced (reported), and as sliced, grown and sagged (the criterion). Gaps in mm; minus an
    overlap's depth."""
    from shapely.geometry import LineString, box as sbox
    from shapely.ops import unary_union
    F, sag = FREE_SWING, FREE_SWING_SAG
    win = sbox(-10.0, -5.0, 2.0, P.Z_FRONT + 0.5)
    whole = {v: {(a, b): unary_union(list(keys.crank_yz(a, b, v).values())) for a, b in B if keys.crank_yz(a, b, v)}
             for v in ('M', 'T')}

    def touches(var, th):
        for r in P.KEY_REFS:
            for (a, b), sh in zip(B, shade[r]):
                if (a, b) in whole[var]:
                    g = keys.gap(keys.turn(whole[var][(a, b)], th), sh['tub'])
                    if g is not None and g <= 0.0:
                        return True
        return False
    end_by = {}
    for var in ('M', 'T'):
        th, step = 0.0, 1.0
        while step >= 0.05:                       # 1-degree steps to the first touch, then halve back onto it
            if th + step <= 180.0 and not touches(var, th + step):
                th += step
            else:
                step /= 2
        end_by[var] = round(th, 2)
    end = max(end_by.values())
    n = int((end - hang) / F['step'])
    thetas = sorted({round(hang + i * F['step'], 3) for i in range(n + 1)} | {hang, end})
    cases = {'cad': 'CAD, on the rod axis', 'as_sliced': 'as sliced, on the rod axis',
             'worst': f"as sliced, each face +{F['grow']}, sagged {sag} toward the face"}
    acc = {k: {'gap': 9.0} for k in cases}
    roof = {}
    for r in P.KEY_REFS:
        for (a, b), sh in zip(B, shade[r]):
            parts = keys.crank_yz(a, b, 'M')
            if 'cheek' not in parts:
                continue
            t_cad = sh['tub'].intersection(win)
            t_pr = _as_printed(t_cad, 'z', P.Z_FRONT)
            c_cad = unary_union(list(parts.values()))
            c_pr = _as_printed(c_cad, 'y', P.CRANK_PAD['end'])
            c_wc = c_pr.buffer(F['grow'], 16)
            if not roof:                          # the slot's roof over the rod's axis, drawn and as sliced
                ln = LineString([(P.ROD_YZ[0], P.ROD_YZ[1]), (P.ROD_YZ[0], P.Z_FRONT + 1)])
                roof = {k: round(min(z for g in getattr(t.intersection(ln), 'geoms', [t.intersection(ln)])
                                     for _, z in g.coords), 3) for k, t in (('cad', t_cad), ('as_sliced', t_pr))}
            for th in thetas:
                for k, c, t, dz in (('cad', c_cad, t_cad, 0.0), ('as_sliced', c_pr, t_pr, 0.0), ('worst', c_wc, t_pr, sag)):
                    g = _depth_gap(keys.lift(keys.turn(c, th), dz), t)
                    if g < acc[k]['gap']:
                        acc[k] = {'gap': g, 'at_deg': th, 'key': r, 'band': [a, b]}
    return {'what': 'crank-M over its cheeks against the tub, turned by hand in the open face-down tub (board out)',
            'range_deg': [hang, end], 'end_by_variant': end_by, 'grow': F['grow'], 'sag': sag,
            'sag_from': {'crank bore reamed': P.CRANK_BORE['ream'], 'ring bores free as sliced': F['ring_free'],
                         'rod smallest': F['rod_min']},
            'slot_roof_over_the_rod': roof, 'cases': cases, **acc, 'min': F['min'], 'ok': acc['worst']['gap'] >= F['min']}


def bottom_keys_check(shapes=None):
    """The bottom keys' own checks (the crank spec's section 8, 1-4), on the parts as built. Each key is cut into
    X bands (keys.BANDS); in each band the crank's and the key's exact YZ profiles move against the shadow of
    the built tub, lid and midplate over that band, the board, the switch envelopes (MJTP1117 as modelled,
    TS365ZJ at its worst: layout.json) and the rod. Gaps are mm, minus an overlap's area in mm2.
      static    rest for a tub-to-board offset delta of -0.2 / 0 / +0.2 (the board's edge at -delta), each
                switch with its own crank (theta from the nose on the plunger's face), the key on the crown
      sweep     theta -13..+16 with the key riding the crown; the board's edge at -0.2 and -0.4; the plungers
                follow the nose (they are pushed, so only a gap to the rest of the crank counts); and 'hang':
                on down to where the crank hangs free in the face-down tub (it rests on the tub there, so
                only overlaps and the board edges count), which is where it is while the board goes in
      free swing (2026-10-12, crank_free_swing) the board out, the tub face down: each crank turned by hand from
                where it hangs to its first tub contact (about +98 / +106), its cheeks' bands against the tub as
                sliced (both parts on their layer grids), each face grown 0.075, crank and rod sagged through
                their bores' play toward the face: >= 0.05 (FREE_SWING)
      paths     (a) the rod along X: a 1.90 cylinder clear of the tub and the cranks, the rod + 0.1 clear of
                    everything else (3D, on the built solids)
                (b) each crank along +Z into the face-down tub at theta 0 and +10, the keys at their stop (on their
                    hooks, KEY_W_OUT above rest)
                (c) the board along +Z: the plungers past the noses, with the crank where it hangs free (the
                    face-down tub swings its pad toward the face, onto its key on its hooks): the required case; held
                    at theta 0 is reported (crank-M on the worst TS365 there is an accepted finding, under 40 degrees)
                (d) each key along +Z from inside (from below the rim up to its stop), hooks included: nothing may
                    touch (the hooks run in their slots)
                and the key's fit in its opening as printed (mechanics.key_fit)
    Writes out/<variant>/bottom-keys.json; returns it."""
    import math, trimesh
    from shapely.geometry import box as sbox, Point
    from shapely.ops import unary_union, nearest_points
    if not P.BOTTOM_KEYS:
        raise SystemExit(f'{P.BUILD} has no bottom keys: nothing for bottom_keys_check (chin_check proves them absent)')
    t0 = time.time()
    if shapes is None:                          # run alone (--bottom-keys): the built parts from their STEP files
        shapes = {n: cq.importers.importStep(str(OUT / f'{n}.step'))
                  for n in ('tub', 'lid', 'midplate', 'gate', *[f'{k}_{r}' for k in ('key', 'crank') for r in P.KEY_REFS])}
    meshes = {n: trimesh.load(OUT / f'{n}.stl') for n in ('tub', 'lid', 'midplate')}
    B = keys.bands()
    xs = {r: keys.key_x(r) for r in P.KEY_REFS}
    shade = {r: [{n: keys.shadow(m, xs[r] + a, xs[r] + b) for n, m in meshes.items()} for a, b in B] for r in P.KEY_REFS}
    rod = Point(*P.ROD_YZ).buffer(P.ROD_D / 2, 64)
    SW = keys.SWITCH
    print(f'  shadows of tub, lid and midplate over {len(B)} bands x {len(xs)} keys ({time.time() - t0:.0f}s)', flush=True)

    def regions(sh):
        """The tub's shadow split where the spec names its parts: rail (y > -4.3, with the skin), chin wall
        (y < -8.1) and the rest (webs, ledge)."""
        t = sh['tub']
        return {'rail': t.intersection(sbox(-4.3, -9, 2, 9)), 'chin wall': t.intersection(sbox(-12, -9, -8.1, 9)),
                'tub': t, 'lid': sh['lid'], 'midplate': sh['midplate']}

    def worst(acc, key, g, where):
        if g is not None and (key not in acc or g < acc[key]['gap']):
            acc[key] = {'gap': g, 'at': where}

    rep = {}
    # ---- static -------------------------------------------------------------------------------------------
    static = {}
    for kind, sw in SW.items():
        var = sw['variant']
        for d in (-0.2, 0.0, 0.2):
            face = sw['face'] - d
            th = keys.rest_theta(var, face)
            lf = keys.crown_shift(th)
            acc = {}
            for r in P.KEY_REFS:
                for (a, b), sh in zip(B, shade[r]):
                    reg = regions(sh)
                    crank = {k: keys.turn(g, th) for k, g in keys.crank_yz(a, b, var).items()}
                    kk = {k: keys.lift(g, lf) for k, g in keys.key_yz(a, b).items()}
                    obst = {**reg, 'board': keys.board_yz(-d), 'rod': rod, **keys.switch_yz(kind, a, b, d, sw['face'])}
                    for cn, cg in crank.items():
                        for on, og in obst.items():
                            if on == 'rod' and cn != 'cheek':
                                continue
                            worst(acc, f'crank {cn} - {on}', keys.gap(cg, og), [r, a, b])
                    for kn, kg in kk.items():
                        for on, og in obst.items():
                            worst(acc, f'key {kn} - {on}', keys.gap(kg, og), [r, a, b])
                        rest = [g for n, g in crank.items() if n != 'crown']
                        if rest:
                            worst(acc, f'key {kn} - crank (but the crown)', keys.gap(kg, unary_union(rest)), [r, a, b])
                        if 'crown' in crank:
                            worst(acc, f'key {kn} - crown', keys.gap(kg, crank['crown']), [r, a, b])
            designed = ('key key - rail', 'key key - crown', 'crank nose - plunger', 'key key - tub')
            bad = {k: v for k, v in acc.items() if v['gap'] < -1e-4 and k not in designed}
            static[f'{kind} crank-{var} delta {d:+.1f}'] = {'theta': round(th, 2), 'key_lift': round(lf, 3), 'overlaps': bad,
                                                           'gaps': dict(sorted(acc.items(), key=lambda kv: kv[1]['gap']))}
    rep['static'] = static
    print(f'  static: ' + '; '.join(f"{k} theta {v['theta']:+.2f} lift {v['key_lift']:+.3f} overlaps {len(v['overlaps'])}"
                                    for k, v in static.items()) + f' ({time.time() - t0:.0f}s)', flush=True)

    # ---- where the crank hangs free in the face-down tub (the pad swings toward the face until the crank
    # meets the tub or its key at its stop, on its hooks), each variant; the board goes in with the cranks there
    stop = P.KEY_W_OUT
    free_by = {}
    for var in ('M', 'T'):
        free_by[var] = 0.0
        for i in range(1, 121):
            th = -i * 0.25
            hit = False
            for r in P.KEY_REFS:
                for (a, b), sh in zip(B, shade[r]):
                    cg = unary_union(list(keys.crank_yz(a, b, var).values()))
                    if cg.is_empty:
                        continue
                    cg = keys.turn(cg, th)
                    kk = keys.key_yz(a, b)
                    g1 = keys.gap(cg, sh['tub'])
                    g2 = keys.gap(cg, keys.lift(kk['key'], stop)) if kk else None
                    if (g1 is not None and g1 <= 0.0) or (g2 is not None and g2 <= 0.0):
                        hit = True
            if hit:
                break
            free_by[var] = th
    free_th = min(free_by.values())
    print(f'  hangs free at {free_by} ({time.time() - t0:.0f}s)', flush=True)

    # ---- sweep --------------------------------------------------------------------------------------------
    hang = sorted({free_th, *[float(x) for x in range(math.ceil(free_th), -13)]})
    thetas = hang + [float(x) for x in range(-13, 17)]
    sweep = {'all': {}, 'match': {}, 'hang': {}}   # match: -4..+13, the matching variant's working range;
    for var in ('M', 'T'):                         # hang: below -13, down to where it hangs free. crank-T
        for th in thetas:                          # differs only in its leg, so only the leg's bands
            lf = keys.crown_shift(th)
            for r in P.KEY_REFS:
                for (a, b), sh in zip(B, shade[r]):
                    if var == 'T' and abs((a + b) / 2) > P.CRANK_LEG:
                        continue
                    reg = regions(sh)
                    crank = {k: keys.turn(g, th) for k, g in keys.crank_yz(a, b, var).items()}
                    if not crank:
                        continue
                    kk = {k: keys.lift(g, lf) for k, g in keys.key_yz(a, b).items()}
                    obst = {**reg, 'board at -0.2': keys.board_yz(-0.2), 'board at -0.4': keys.board_yz(-0.4)}
                    for kind in SW:
                        for n, g in keys.switch_yz(kind, a, b).items():
                            if n == 'housing':
                                obst[f'{kind} housing'] = g
                    rng = sweep['hang'] if th < -13 else sweep['all']
                    for cn, cg in crank.items():
                        for on, og in obst.items():
                            if cn == 'nose' and 'housing' in on:
                                continue            # the nose meets only the plunger, which stops it
                            g = keys.gap(cg, og)
                            worst(rng, f'{cn} - {on}', g, [var, th, r, a, b])
                            if -4 <= th <= 13:
                                worst(sweep['match'], f'{cn} - {on}', g, [var, th, r, a, b])
                    rest = unary_union([g for n, g in crank.items() if n != 'crown'])
                    for kn, kg in kk.items():
                        g = keys.gap(kg, rest)
                        worst(rng, f'key {kn} - crank (but the crown)', g, [var, th, r, a, b])
                        if 'crown' in crank:
                            worst(rng, f'key {kn} - crown', keys.gap(kg, crank['crown']), [var, th, r, a, b])
    # the cheeks against the housings with X ignored, as the spec measured them (here they are in separate X
    # bands: the cheeks start at |dx| 3.75, the TS365's assumed housing ends at 3.65 and the MJTP's at 4.04)
    cheek = keys.CHEEK.difference(keys.crank_bore())
    for kind, sw in SW.items():
        hb = sbox(*sw['housing'][0])
        for th in thetas:
            g = keys.gap(keys.turn(cheek, th), hb)
            worst(sweep['hang'] if th < -13 else sweep['all'], f'cheek - {kind} housing (YZ, X ignored)', g, ['M', th])
            if -4 <= th <= 13:
                worst(sweep['match'], f'cheek - {kind} housing (YZ, X ignored)', g, ['M', th])
    # the cheek's closed ring (test 1, 2026-09-29) against the MJTP1117's housing: the envelope's housing ends at |dx|
    # 4.04, short of the ring's 4.05, so no band sees the two together; but the crank floats CRANK_CHEEK[0] - SLOT[0]
    # (0.15) in X toward it and the board can sit 0.2 nearer. So the ring's section, turned over the sweep and on down
    # to the free hang, against the housing's YZ box moved 0.2 toward the crank (-Y). Pass: >= RING_MJ_MIN
    ring = keys.cheek_yz('ring')
    hb, hb0 = (keys.switch_yz('MJTP', 0.0, 0.0, d)['housing'] for d in (0.2, 0.0))
    g, at = min((keys.gap(keys.turn(ring, th), hb), th) for th in thetas)
    rep['ring_mj'] = {'min': g, 'at_deg': at, 'theta_0': keys.gap(ring, hb), 'theta_0_board_nominal': keys.gap(ring, hb0),
                      'crank_float_toward_it': round(P.CRANK_CHEEK[0] - P.SLOT[0], 3), 'board_nearer': 0.2,
                      'thetas': [thetas[0], thetas[-1]], 'ok': g >= RING_MJ_MIN}
    # the plungers, kinematic: the face follows the nose wherever the nose is inside the plunger's Z band
    plunger = {}
    cases = [('crank-M on MJTP', 'M', 'MJTP', -1.92, (-3.459, -1.959), -0.68, 1.44),
             ('crank-T on TS365, tip -2.4, high', 'T', 'TS365', -2.4, (-3.05, -1.05), -1.45, 1.85),
             ('crank-T on TS365, nominal', 'T', 'TS365', -2.2, (-3.25, -1.75), -1.45, 1.85),
             ('crank-M on TS365, tip -2.4 (wrong variant)', 'M', 'TS365', -2.4, (-3.05, -1.05), -1.45, 1.85)]
    for name, var, kind, tip, (z0, z1), yh, hx in cases:
        acc = {}
        for th in thetas:
            if th < -13:
                continue
            nose = keys.turn(keys.circ(P.CRANK_NOSE[var], P.CRANK_NOSE_R), th).intersection(sbox(-9, z0, 9, z1))
            face = max(tip, nose.bounds[2]) if not nose.is_empty else tip
            box_ = sbox(face, z0, yh, z1)
            for a, b in B:
                if abs((a + b) / 2) > hx:
                    continue
                for cn, cg in keys.crank_yz(a, b, var).items():
                    if cn in ('nose', 'crown'):
                        continue
                    worst(acc, cn, keys.gap(keys.turn(cg, th), box_), [th, a, b])
        plunger[name] = acc
    sweep['plunger_kinematic'] = plunger
    rep['sweep'] = {k: dict(sorted(v.items(), key=lambda kv: kv[1]['gap'])) if k != 'plunger_kinematic' else v for k, v in sweep.items()}
    print(f'  sweep -13..+16 done ({time.time() - t0:.0f}s)', flush=True)
    # the free swing: the board out, a crank turned by hand from its key to its end, as printed (FREE_SWING)
    fs = rep['free_swing'] = crank_free_swing(shade, B, free_th)
    print(f"  free swing {fs['range_deg'][0]:+.2f}..{fs['range_deg'][1]:+.2f}: cheeks to the tub, CAD {fs['cad']['gap']} at "
          f"{fs['cad']['at_deg']:+.1f}, as sliced {fs['as_sliced']['gap']} at {fs['as_sliced']['at_deg']:+.1f}, grown and "
          f"sagged {fs['worst']['gap']} at {fs['worst']['at_deg']:+.1f} (>= {fs['min']}: {'PASS' if fs['ok'] else 'FAIL'}); "
          f"roof over the rod {fs['slot_roof_over_the_rod']} ({time.time() - t0:.0f}s)", flush=True)

    # ---- paths ----------------------------------------------------------------------------------------------
    paths = {}
    # (a) the rod, in 3D on the built solids
    if shapes is not None:
        tub_s = shapes['tub'].val()
        y, z = P.ROD_YZ
        from geom import xcyl
        free = xcyl(P.X0 - 0.2, P.ROD_STOPS[1] - 0.01, y, z, 1.90).val()
        near = xcyl(P.ROD_STOPS[0], P.ROD_STOPS[1] - 0.01, y, z, P.ROD_D + 0.2).val()
        rod_s = keys.rod().val()
        a = {'d1.90 x tub': round(free.intersect(tub_s).Volume(), 5),
             **{f'd1.90 x crank_{r}': round(free.intersect(shapes[f'crank_{r}'].val()).Volume(), 5) for r in P.KEY_REFS},
             'rod to tub': round(rod_s.distance(tub_s), 3),
             'rod to cranks': round(min(rod_s.distance(shapes[f'crank_{r}'].val()) for r in P.KEY_REFS), 3)}
        hwsol = hw.solids()
        for n, s in [*((k, v.val()) for k, v in shapes.items() if k != 'tub' and not k.startswith('crank_')), *hwsol.items()]:
            b = s.BoundingBox()
            if b.ymin > y + 1.2 or b.ymax < y - 1.2 or b.zmin > z + 1.2 or b.zmax < z - 1.2:
                continue
            v = near.intersect(s).Volume()
            if v > 1e-5:
                a[f'rod + 0.1 x {n}'] = round(v, 5)
        # the gate's flat is the rod's left stop: the rod + 0.1 starts on it (a touch, no volume)
        a['rod + 0.1 to the gate (its flat, X -2.34)'] = round(near.distance(shapes['gate'].val()), 4)
        paths['a_rod'] = a
    # (b) cranks along +Z (from the open back) at theta 0 and +10, keys at their stop
    b_ = {}
    for th in (0.0, 10.0):
        acc = {}
        for r in P.KEY_REFS:
            for (a, b), sh in zip(B, shade[r]):
                cg = unary_union(list(keys.crank_yz(a, b, 'M').values()))
                if cg.is_empty:
                    continue
                cg = keys.turn(cg, th)
                kk = keys.key_yz(a, b)
                kg = keys.lift(kk['key'], stop) if kk else None
                for i in range(0, 81):
                    c2 = keys.lift(cg, -i * 0.1)
                    worst(acc, 'tub', keys.gap(c2, sh['tub']), [r, a, b, round(i * 0.1, 1)])
                    worst(acc, 'rail', keys.gap(c2, regions(sh)['rail']), [r, a, b, round(i * 0.1, 1)])
                    worst(acc, 'midplate', keys.gap(c2, sh['midplate']), [r, a, b, round(i * 0.1, 1)])
                    if kg is not None:
                        worst(acc, 'keys at the stop', keys.gap(c2, kg), [r, a, b, round(i * 0.1, 1)])
        b_[f'theta {th:+.0f}'] = acc
    paths['b_crank_in'] = b_
    # (c) the board along +Z past the noses: the crank hangs from the rod as far as it swings (free_by, found
    # before the sweep), or is held at theta 0
    c_ = {'free_theta': free_th, 'free_theta_by_variant': free_by}
    for held in ('hanging free', 'held at theta 0'):
        for var in ('M', 'T'):
            th = free_by[var] if held == 'hanging free' else 0.0
            for name, tip, (z0, z1), hx in (('MJTP', -1.92, (-3.459, -1.959), 1.44), ('TS365 tip -2.4 centre -1.8', -2.4, (-2.55, -1.05), 1.85)):
                nose = keys.turn(keys.circ(P.CRANK_NOSE[var], P.CRANK_NOSE_R), th)
                body = keys.turn(unary_union([keys.leg_body(var), keys.BELLY]).difference(keys.circ(P.CRANK_NOSE[var], P.CRANK_NOSE_R)), th)
                first = None
                for i in range(0, 1201):
                    dz = -12.0 + i * 0.01
                    pb = sbox(tip, z0 + dz, 0.0, z1 + dz)
                    if pb.distance(nose) < 1e-3 or pb.intersects(body):
                        p_n, _ = nearest_points(nose, pb)
                        c = keys.turn(Point(*P.CRANK_NOSE[var]), th)
                        ny, nz = p_n.x - c.x, p_n.y - c.y
                        ang = math.degrees(math.atan2(abs(ny), abs(nz)))
                        first = {'at_dz': round(dz, 2), 'on': 'nose' if not pb.intersects(body) or pb.distance(nose) < 1e-3 else 'leg/belly',
                                 'normal_from_Z_deg': round(ang, 1), 'ok': ang >= 40.0}
                        break
                first = first or {'contact': None, 'ok': True}
                first['theta'] = th
                if held == 'held at theta 0':
                    first['required'] = False       # the cranks hang free while the board goes in (README)
                    if not first['ok']:
                        first['accepted'] = ('a crank held at 0 with the wrong variant: still above the 16.7-degree '
                                             'friction angle, so the plunger cams the crank aside')
                c_[f'{held}, crank-{var}, {name}'] = first
    paths['c_board_in'] = c_
    # (d) keys along +Z from inside, from 14 below the stop (the cap below the rim) up to the stop: nothing of the key may
    # touch the tub, the hooks included (they run up their slots from the rim; at the stop they meet the roof: a touch)
    d_ = {'key - tub': {}, 'hook - tub': {}}
    for r in P.KEY_REFS:
        for (a, b), sh in zip(B, shade[r]):
            kk = keys.key_yz(a, b)
            for i in range(0, 141):
                dz = stop - i * 0.1
                for n, g in kk.items():
                    worst(d_[f'{n} - tub'], 'gap', keys.gap(keys.lift(g, dz), sh['tub']), [r, a, b, round(dz, 2)])
    paths['d_key_in'] = d_
    rep['paths'] = paths
    # X gaps at rest, in 3D: cheeks in their slots, caps between the opening's sides
    rep['side_clearance'] = {'cheek to slot side': round(P.CRANK_CHEEK[0] - P.SLOT[0], 3), 'cheek to ring/web': round(P.SLOT[1] - P.CRANK_CHEEK[1], 3),
                             'cap to opening side': round(P.KEY_OPENING['half'] - P.KEY_CAP['half'], 3),
                             'cap to web': round(P.SLOT[1] - P.KEY_CAP['half'], 3)}
    if shapes is not None:
        rep['side_clearance']['crank_SW8 to tub, 3D'] = round(shapes['crank_SW8'].val().distance(shapes['tub'].val()), 3)
    # the key's fit in its opening as printed, best / typical / worst (the same as mechanics.json's)
    import mechanics
    rep['key_fit'] = mechanics.key_fit()
    # the key's height over the face at rest, board +-0.2, matching crank (the spec's 8.6; mechanics.key_proud)
    rep['key_proud'] = mechanics.key_proud()
    # SPEC2 rev 3 (the side gate): the cranks' pickup by the rod's tip and their drop-in (checks 2 and 3), and the
    # gate's contact, path, cam and bearing (checks 1, 5, 6 and 7)
    rep['pickup'] = crank_pickup()
    print(f'  crank pickup done ({time.time() - t0:.0f}s)', flush=True)
    rep['gate'] = gate_check(shapes)
    print(f'  gate done ({time.time() - t0:.0f}s)', flush=True)
    rep['verdict'] = bottom_keys_verdict(rep)
    (OUT / 'bottom-keys.json').write_text(json.dumps(rep, indent=1))
    print(f'  paths done ({time.time() - t0:.0f}s) -> out/{OUT.name}/bottom-keys.json', flush=True)
    return rep


def crank_pickup():
    """SPEC2 rev 3, checks 2 and 3: where a crank dropped into the face-down tub with no rod comes to rest, and how
    far its bore is from the rod's tapered tip on the way (review 2's r2 method, on out/<variant>/ as built). Each
    crank is cut into X bands (cheeks, belly, slot ends, leg); in each the crank's shadow is lowered (+Z, gravity)
    onto the tub's and its key's (lifted to the stop, on its hooks, as the keys' step leaves them) until it touches, for every
    (dy, theta) on a 0.1 mm x 2 degree grid; from each drop pose (theta 0 / +4 / +10 x dy -0.4..+0.4) the crank
    then slides downhill (its centre of mass lowest: frictionless) to rest. The bore's offset is measured from the
    rod's tip lying in the rings, sagged face down (+0.175)."""
    import math, trimesh
    from shapely import affinity
    from shapely.geometry import Point
    ax = P.ROD_YZ
    stop = P.KEY_W_OUT
    tub_m = trimesh.load(OUT / 'tub.stl')
    out = {}
    for ref in P.KEY_REFS:
        xc = keys.key_x(ref)
        cr = trimesh.load(OUT / f'crank_{ref}.stl')
        key_m = trimesh.load(OUT / f'key_{ref}.stl')
        com = cr.center_mass
        c0 = (float(com[1]), float(com[2]))
        bands = []
        for s in (-1, 1):
            bands += [(f'cheek{s:+d}', xc + s * 4.5 - 0.70, xc + s * 4.5 + 0.70), (f'belly{s:+d}', xc + s * 2.525 - 1.17, xc + s * 2.525 + 1.17),
                      (f'slotend{s:+d}', xc + s * 3.675 - 0.07, xc + s * 3.675 + 0.07)]
        bands.append(('leg', xc - 1.25, xc + 1.25))
        B = []
        for bn, a, b in bands:
            k = affinity.translate(keys.shadow(key_m, a - 0.1, b + 0.1, 0.2), 0, stop)
            t = keys.shadow(tub_m, a, b, 0.2)
            B.append((bn, keys.shadow(cr, a, b, 0.2), t.union(k) if not k.is_empty else t, k))
        memo = {}

        def rest(dy, th):
            """(dz, contact, energy) with the crank lowered from dz -1.5 onto the tub and keys; dz None if blocked."""
            if (dy, th) in memo:
                return memo[(dy, th)]
            best, who = 9.0, None
            for bn, c, obs, k in B:
                g = affinity.translate(affinity.rotate(c, th, origin=ax), dy, -1.5)
                if g.intersects(obs):
                    memo[(dy, th)] = (None, bn, None)
                    return memo[(dy, th)]
                lo, hi = 0.0, 3.0
                if not affinity.translate(g, 0, hi).intersects(obs):
                    continue
                for _ in range(16):
                    m = 0.5 * (lo + hi)
                    if affinity.translate(g, 0, m).intersects(obs):
                        hi = m
                    else:
                        lo = m
                if lo - 1.5 < best:
                    best = lo - 1.5
                    who = bn + ('/key' if not k.is_empty and affinity.translate(g, 0, hi).intersects(k) else '/tub')
            p = affinity.rotate(Point(c0), th, origin=ax)
            memo[(dy, th)] = (best, who, -(p.y + best))
            return memo[(dy, th)]

        def off(dy, dz):
            return math.hypot(dy, dz - 0.175)

        drops = {}
        for th0 in (0, 4, 10):
            for dy0 in (-0.4, -0.2, 0.0, 0.2, 0.4):
                dz0, who0, e0 = rest(dy0, th0)
                if dz0 is None:
                    drops[f'theta {th0:+d} dy {dy0:+.1f}'] = {'blocked': who0}
                    continue
                cur, worst = (dy0, th0), off(dy0, dz0)
                for _ in range(400):
                    best = cur
                    for ddy in (-0.1, 0.0, 0.1):
                        for dth in (-2, 0, 2):
                            n = (round(cur[0] + ddy, 2), cur[1] + dth)
                            if not (-1.5 <= n[0] <= 0.8 and -80 <= n[1] <= 14):
                                continue
                            r = rest(*n)
                            if r[2] is not None and r[2] < rest(*best)[2] - 1e-6:
                                best = n
                    if best == cur:
                        break
                    cur = best
                    worst = max(worst, off(cur[0], rest(*cur)[0]))
                dz, who, _ = rest(*cur)
                drops[f'theta {th0:+d} dy {dy0:+.1f}'] = {
                    'lands_dz': round(dz0, 3), 'lands_on': who0, 'landing_offset': round(off(dy0, dz0), 3),
                    'rests_theta': cur[1], 'rests_dy': cur[0], 'rests_dz': round(dz, 3), 'rests_on': who,
                    'rest_offset': round(off(cur[0], dz), 3), 'worst_on_path': round(worst, 3)}
        out[ref] = drops
    return out


def _zsec(mesh, z, clip):
    """(x, y) section of a closed mesh at Z = z (holes kept), clipped to clip = (x0, y0, x1, y1)."""
    from shapely.geometry import Polygon, box as sbox
    s = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    g = Polygon()
    for loop in (s.discrete if s is not None else []):
        if len(loop) >= 3:
            p = Polygon(loop[:, :2]).buffer(0)
            if p.area > 1e-9:
                g = g.symmetric_difference(p)
    return g.intersection(sbox(*clip))


def gate_check(shapes):
    """The side gate (SPEC2 rev 3, section 9 checks 1, 5, 6 and 7), on the built solids and their sections.
      contact  gate x tub: zero volume and touching; moved 0.01 -X it meets only the lips, 0.01 +Z only the floor
      path     (5) lowered along +Z from z -10 to its seat, centred in X (0.075 each side) and Y: >= 0.05 from the
               slot's walls all the way (the tub above z 0.85: the floor, 0.90 and lower, is where it lands), then
               on the floor only; seated, >= 0.05 from the lid, >= 0.5 from the board, display, midplate and strip
      cam      (6) the XZ section at the rod's axis: the gate lowered from z -6, the rod pushed on +X wherever the
               gate meets its end (blocked where it lands on its top); tail at X0 and X0 + 0.3, the axis nominal
               and sagged face down (+0.175): the first contact on the bevel, seated the tail at ROD_STOP_X0 and the
               flat past the axis; the tail 0.2 proud: the gate stops >= 1 proud
      bearing  (7) the plan at z -1.0 (every chamfer and the round ends as built), the gate pushed -X at Y offsets
               0, +-0.05, +-0.10: zero overlap and zero travel at rest, and the flat bearing on each lip
    Returns a dict (bottom-keys.json 'gate')."""
    import trimesh
    import numpy as np
    from shapely import affinity
    from shapely.geometry import Point, Polygon, box as sbox
    rep = {}
    tub_w, g_w = shapes['tub'], shapes['gate']
    crop = tub_w.intersect(box(-6.0, -0.5, -7.0, 2.0, -7.0, 4.0)).val()
    g = g_w.val()
    # ---- contact (check 1)
    c = {'volume': round(g.intersect(crop).Volume(), 6), 'distance': round(g.distance(crop), 4)}
    for name, v in (('moved 0.01 -X', (-0.01, 0, 0)), ('moved 0.01 +Z', (0, 0, 0.01))):
        i = g.moved(cq.Location(cq.Vector(*v))).intersect(crop)
        bb = i.BoundingBox()
        c[name] = {'volume': round(i.Volume(), 5), 'where': [round(q, 2) for q in (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)]}
    rep['contact'] = c
    # ---- path (check 5)
    walls = tub_w.intersect(box(-6.0, -0.5, -7.0, 2.0, -7.0, 0.85)).val()
    seat = -0.075                                  # centred in X, the 45-degree bevel lands 0.075 higher
    gc = g_w.translate((0.075, 0, 0))
    worst = (9.0, None)
    for dz in [*np.arange(-10.0, seat, 0.25), seat]:
        d = gc.translate((0, 0, float(dz))).val().distance(walls)
        if d < worst[0]:
            worst = (round(d, 4), round(float(dz), 3))
    gs = gc.translate((0, 0, seat)).val()
    p = {'walls_min': worst[0], 'walls_min_at_dz': worst[1],
         'seated_centred': {'volume': round(gs.intersect(crop).Volume(), 6), 'distance': round(gs.distance(crop), 4)}}
    # the lid over the gate, centred in X as the spec checks it (0.075 higher than on the lips); on the lips, where
    # the rod's push and the floor's 45-degree slope put it, it sits 0.075 lower, and at the slot's far end, flat on
    # the sliver (+0.15 X, 0.15 higher: reachable while the rod is not home), 0.075 higher (both reported)
    p['lid'] = round(gs.distance(shapes['lid'].val()), 4)
    p['lid_on_the_lips'] = round(g.distance(shapes['lid'].val()), 4)
    gf = g_w.translate((0.15, 0, -0.15)).val()
    p['on_the_sliver'] = {'lid': round(gf.distance(shapes['lid'].val()), 4), 'tub_volume': round(gf.intersect(crop).Volume(), 6)}
    near = {}
    if P.LIGHT_STRIP:
        sf = refs.strip_front()
        near.update({'display': refs.plain_display().val(), 'strip_bar': sf['strip_bar'].val(), 'strip_leds': sf['strip_leds'].val()})
    else:
        near['display'] = refs.display().val()
    near['midplate'] = shapes['midplate'].val()
    gb = g.BoundingBox()
    for ref, s in hw.solids().items():
        b = s.BoundingBox()
        if b.xmin > gb.xmax + 3 or b.xmax < gb.xmin - 3 or b.ymin > gb.ymax + 3 or b.ymax < gb.ymin - 3 or b.zmin > gb.zmax + 3 or b.zmax < gb.zmin - 3:
            continue
        near[ref] = s
    p['others'] = {k: round(g.distance(s), 3) for k, s in near.items()}
    p['others_min'] = list(min(p['others'].items(), key=lambda kv: kv[1]))
    rep['path'] = p
    # ---- cam (check 6)
    gm = trimesh.load(OUT / 'gate.stl')
    s = gm.section(plane_origin=[0, P.ROD_YZ[0], 0], plane_normal=[0, 1, 0])
    G = Polygon()
    for loop in s.discrete:
        q = Polygon(loop[:, [0, 2]]).buffer(0)
        if q.area > 1e-9:
            G = G.symmetric_difference(q)
    r = P.ROD_D / 2
    cam = {}
    for tail, sag in ((P.X0, 0.0), (P.X0, 0.175), (P.X0 + 0.3, 0.0), (P.X0 + 0.3, 0.175), (P.X0 - 0.2, 0.0), (P.X0 - 0.2, 0.175)):
        zc = P.ROD_YZ[1] + sag
        band = sbox(-99, zc - r, 99, zc + r)
        xt, first, stopped = tail, None, None
        for dz in np.arange(-6.0, 1e-9, 0.005):
            gg = affinity.translate(G, 0, float(dz))
            ov = gg.intersection(sbox(xt, zc - r, xt + P.ROD_CUT, zc + r))
            if ov.is_empty or ov.area < 1e-9:
                continue
            if first is None:
                x = ov.bounds[0] if ov.bounds[0] > xt + 0.01 else xt
                first = {'dz': round(float(dz), 3), 'x': round(x, 3), 'z': round(zc - r, 3),
                         'on': 'bevel' if P.X0 - 1e-3 <= x < P.ROD_STOP_X0 - 0.01 and ov.bounds[0] <= xt + 0.01 else 'rod top (no cam)'}
            if ov.bounds[0] > xt + 0.01:                       # on the rod's top, not its end: the gate stops
                stopped = round(float(dz) - 0.005, 3)
                break
            xt = gg.intersection(band).bounds[2]
        k = f'tail {tail - P.X0:+.1f} from the face, axis {sag:+.3f}'
        e = {'first_contact': first, 'tail_seated': round(xt, 3) if stopped is None else None, 'gate_stops_dz': stopped}
        if stopped is None:
            e['flat_past_axis'] = round(P.GATE_SLOT['floor_z'] - zc, 3)
        cam[k] = e
    rep['cam'] = cam
    # ---- bearing (check 7)
    clip = (-6.0, -7.0, -1.0, 2.0)
    T = _zsec(trimesh.load(OUT / 'tub.stl'), -1.0, clip)
    Gp = _zsec(gm, -1.0, clip)
    xl = P.X0 + P.GATE_SLOT['lip']
    br = {}
    for sh in (0.0, 0.05, -0.05, 0.10, -0.10):
        gg = affinity.translate(Gp, 0, sh)
        ov = gg.intersection(T).area
        lo, hi = 0.0, 0.6
        for _ in range(30):
            m = 0.5 * (lo + hi)
            if affinity.translate(gg, -m, 0).intersection(T).area > 1e-7:
                hi = m
            else:
                lo = m
        gg2, Tb = affinity.translate(gg, -lo, 0).buffer(1e-6), T.buffer(1e-6)
        sides = {}
        for side, (ya, yb) in (('-Y', (-4.8, -3.0)), ('+Y', (-2.0, -0.2))):
            ys = [float(y) for y in np.arange(ya, yb, 0.0025) if gg2.contains(Point(xl + 0.0005, y)) and Tb.contains(Point(xl - 0.0035, y))]
            sides[side] = [round(min(ys), 3), round(max(ys), 3), round(max(ys) - min(ys), 3)] if ys else None
        br[f'{sh:+.2f}'] = {'overlap_mm2': round(float(ov), 6), 'travel_to_contact': round(float(lo), 4), 'bearing': sides}
    rep['bearing'] = br
    return rep


def bottom_keys_verdict(rep):
    """The spec's pass criteria (section 8, 1-4) on the check's numbers: {criterion: [ok, worst]}."""
    sw = rep['sweep']

    def low(rng, skip=(), only=None):
        rows = [(n, v['gap']) for n, v in sw[rng].items() if not any(s in n for s in skip) and (only is None or any(o in n for o in only))]
        return min(rows, key=lambda r: r[1]) if rows else (None, 9.0)
    contact = ('key key - crown',)                           # the designed contact
    rail = ('leg - rail', 'leg - tub', 'belly - rail', 'belly - tub')
    board4 = ('cheek - board at -0.4',)
    v = {}
    v['static: no undesigned overlaps'] = [all(not s['overlaps'] for s in rep['static'].values()), None]
    n, g = low('all', skip=contact + rail + board4)
    v['sweep -13..+16: >= 0.10 (but the three below)'] = [g >= 0.10, [n, g]]
    n, g = low('all', only=rail)
    v['sweep -13..+16: leg and belly to the rail >= 0.06'] = [g >= 0.06, [n, g]]
    n, g = low('all', only=board4)
    v['sweep -13..+16: cheek to a board edge at -0.4 >= 0.07'] = [g >= 0.07, [n, g]]
    n, g = low('match')
    v['sweep -4..+13: >= 0.20'] = [g >= 0.20, [n, g]]
    ft = rep['paths']['c_board_in']['free_theta']
    if sw['hang']:
        n, g = low('hang', skip=contact)
        v[f"hang {ft}..-13: no overlap (it rests on the tub)"] = [g >= 0.0, [n, g]]
        n, g = low('hang', only=('board at -0.2', 'board at -0.4'))
        v['hang: cheek to a board edge at -0.4 >= 0.05'] = [g >= 0.05, [n, g]]
    else:
        # the hook keys (test 2): face down each crank rests on its key, on its hooks, inside the sweep's range, so the
        # sweep's own criteria (above) hold there
        v[f'hang: the cranks rest on their keys (on their hooks) at {ft}, inside the -13..+16 sweep'] = [ft >= -13.0, None]
    pk = min((g['gap'], k, n) for k, c in sw['plunger_kinematic'].items() for n, g in c.items())
    v['plunger, kinematic: >= 0.35'] = [pk[0] >= 0.35, list(pk)]
    if 'free_swing' in rep:
        fs = rep['free_swing']
        v[f"free swing {fs['range_deg'][0]:+.2f}..{fs['range_deg'][1]:+.2f} (board out, face down): the cheeks to the "
          f"tub as sliced, +{fs['grow']} a face, sagged {fs['sag']}, >= {fs['min']}"] = [
            fs['ok'], [fs['worst']['gap'], fs['worst']['at_deg'], fs['as_sliced']['gap'], fs['cad']['gap']]]
    if 'ring_mj' in rep:
        r = rep['ring_mj']
        v[f"ring to the MJTP housing (crank {r['crank_float_toward_it']} toward it, board {r['board_nearer']} nearer) "
          f">= {RING_MJ_MIN}"] = [r['ok'], [r['min'], r['at_deg'], r['theta_0_board_nominal']]]
    a = rep['paths'].get('a_rod', {})
    v['path a: rod path free at 1.90, nothing else within 0.1'] = [
        all(val == 0 for k, val in a.items() if k.startswith('d1.90') or k.startswith('rod + 0.1')), None]
    b = [(g['gap'], th, n) for th, c in rep['paths']['b_crank_in'].items() for n, g in c.items() if n in ('rail', 'keys at the stop', 'tub')]
    v['path b: cranks in, >= 0.3 to rail and keys'] = [min(b)[0] >= 0.3, list(min(b))]
    c = rep['paths']['c_board_in']
    v['path c: board in, cranks hanging free: contact normal >= 40 degrees'] = [
        all(r['ok'] for k, r in c.items() if k.startswith('hanging free')), None]
    v['path c: board in, cranks held at 0 (reported; accepted finding)'] = [
        'accepted' if any('accepted' in r for k, r in c.items() if k.startswith('held')) else True,
        [[k, r.get('normal_from_Z_deg')] for k, r in c.items() if k.startswith('held') and 'accepted' in r]]
    d = rep['paths']['d_key_in']
    v['path d: keys in from below the rim to the stop, the hooks in their slots: nothing touches'] = [
        all(g['gap'] >= -1e-4 for c in d.values() for g in c.values()), {k: c.get('gap', {}).get('gap') for k, c in d.items()}]
    # the key's fit as a tolerance stack (mechanics.key_fit: 2026-09-29, Ian's first print jammed)
    for k, ok in rep.get('key_fit', {}).get('checks', {}).items():
        v[f'key fit: {k}'] = [ok, None]
    # the key's height at rest (mechanics.key_proud: 2026-10-03, the cap 1.35 proud, the spec's floor)
    if 'key_proud' in rep:
        kp = rep['key_proud']
        for k, ok in kp['checks'].items():
            v[k] = [ok, [kp['proud_cad_rest'], kp['range_mm']]]
    # SPEC2 rev 3 (the side gate), section 9
    if 'gate' in rep:
        G = rep['gate']
        c = G['contact']
        v['1 parts: gate x tub a touch (zero volume); 0.01 -X meets the lips, 0.01 +Z the floor'] = [
            c['volume'] < 1e-4 and c['distance'] < 1e-3 and c['moved 0.01 -X']['where'][0] >= -3.01 and c['moved 0.01 +Z']['where'][4] >= 0.85,
            [c['volume'], c['distance'], c['moved 0.01 -X']['where'][:2], c['moved 0.01 +Z']['where'][4:]]]
        v['2 rod path: rod + 0.1 empty but the gate, touching at its flat'] = [
            a.get('rod + 0.1 to the gate (its flat, X -2.34)', 9) < 1e-3 and not any(k.startswith('rod + 0.1 x') for k in a), None]
        pk = [(d['rest_offset'], r, k) for r, dd in rep['pickup'].items() for k, d in dd.items() if 'rest_offset' in d]
        pw = [(max(d['landing_offset'], d['worst_on_path']), r, k) for r, dd in rep['pickup'].items() for k, d in dd.items() if 'rest_offset' in d]
        blocked = [(r, k) for r, dd in rep['pickup'].items() for k, d in dd.items() if 'blocked' in d]
        v['2 pickup: rest offset <= 0.30 (the 0.3 lead-ins)'] = [bool(pk) and max(pk)[0] <= 0.30, list(max(pk)) if pk else None]
        v['2 pickup: landing and path offsets <= 0.80 (the tip flat in the 2.5 mouth)'] = [bool(pw) and max(pw)[0] <= 0.80, list(max(pw)) if pw else None]
        lands = [(d['lands_dz'], r, k, d['lands_on']) for r, dd in rep['pickup'].items() for k, d in dd.items() if 'lands_dz' in d]
        v['3 drop-in: none blocked, lands at dz >= -0.05'] = [not blocked and min(lands)[0] >= -0.05, [list(min(lands)), list(max(lands))] if lands else blocked]
        p = G['path']
        v['5 gate path: >= 0.05 to the walls, then on the floor only'] = [
            p['walls_min'] >= 0.05 and p['seated_centred']['volume'] < 1e-4 and p['seated_centred']['distance'] < 1e-3, [p['walls_min'], p['seated_centred']]]
        v['5 gate to the lid >= 0.05 (centred in X)'] = [p['lid'] >= 0.05, [p['lid'], p['lid_on_the_lips'], p.get('on_the_sliver')]]
        v['5 gate to the board, display, midplate, strip >= 0.5'] = [p['others_min'][1] >= 0.5, p['others_min']]
        cm = G['cam']
        cams = {k: e for k, e in cm.items() if not k.startswith('tail -0.2')}
        v['6 cam: first contact on the bevel, seated tail at -2.34 +- 0.01, flat past the axis'] = [
            all(e['first_contact'] and e['first_contact']['on'] == 'bevel' and e['tail_seated'] is not None
                and abs(e['tail_seated'] - P.ROD_STOP_X0) <= 0.01 and e['flat_past_axis'] > 0 for e in cams.values()),
            [[k, e['tail_seated'], e.get('flat_past_axis')] for k, e in cams.items()]]
        proud = {k: e for k, e in cm.items() if k.startswith('tail -0.2')}
        v['6 cam: tail 0.2 proud, the gate stops >= 1 proud'] = [
            all(e['gate_stops_dz'] is not None and e['gate_stops_dz'] <= -1.0 for e in proud.values()), [e['gate_stops_dz'] for e in proud.values()]]
        b = G['bearing']
        ok = all(r['overlap_mm2'] < 1e-6 and r['travel_to_contact'] < 1e-3 and r['bearing']['-Y'] and r['bearing']['+Y'] for r in b.values())
        ctr = min(b['+0.00']['bearing']['-Y'][2], b['+0.00']['bearing']['+Y'][2]) if ok else 0
        ext = min(min(r['bearing']['-Y'][2], r['bearing']['+Y'][2]) for r in b.values()) if ok else 0
        v['7 bearing: zero overlap and travel; flat bearing >= 0.25 centred, >= 0.15 at +-0.10'] = [ok and ctr >= 0.25 - 0.005 and ext >= 0.15 - 0.005, [ctr, ext]]
    return {k: [bool(ok) if not isinstance(ok, str) else ok, w] for k, (ok, w) in v.items()}


def bottom_keys_summary(rep):
    """One screen of the check, against the spec's numbers."""
    L = []
    for k, v in rep['static'].items():
        L.append(f"  static {k}: theta {v['theta']:+.2f}, key {v['key_lift']:+.3f}; undesigned overlaps: {v['overlaps'] or 'none'}")
    for k in ('all', 'match', 'hang'):
        L.append(f"  sweep {dict(all='-13..+16', match='-4..+13', hang='hang..-13')[k]}: " + ', '.join(f"{n} {v['gap']}" for n, v in list(rep['sweep'][k].items())[:14]))
    for k, v in rep['sweep']['plunger_kinematic'].items():
        L.append(f"  plunger, kinematic, {k}: " + ', '.join(f"{n} {g['gap']}" for n, g in v.items()))
    if 'ring_mj' in rep:
        L.append(f"  ring to the MJTP housing: {rep['ring_mj']}")
    for k, v in rep['paths'].items():
        L.append(f'  path {k}: {v}')
    L.append(f"  side clearances: {rep['side_clearance']}")
    for n, p in rep.get('key_fit', {}).get('pairs', {}).items():
        if 'cad' in p:
            L.append(f"  key fit {n}: CAD {p['cad']:+.3f}, as printed {' / '.join(f'{q:+.3f}' for q in p['printed_b_t_w'])}")
        elif '-X' in p:
            L.append(f"  key fit {n}: " + ', '.join(f"{e} as printed {' / '.join(f'{q:+.3f}' for q in p[e]['printed_b_t_w'])}" for e in ('-X', '+X')))
        else:
            L.append(f"  key fit {n}: contact y {p['contact_y_over_-13..+16']} on the pusher {p['pusher_y']}, to its ends {p['to_its_ends']}")
    if 'key_fit' in rep:
        L.append(f"  key fit: tilt at most {rep['key_fit']['tilt_deg_at_most']} deg; accepted {rep['key_fit']['accepted']}")
    for r, dd in rep.get('pickup', {}).items():
        L.append(f'  pickup {r}: ' + '; '.join(f"{k}: " + (f"blocked by {d['blocked']}" if 'blocked' in d else
                 f"lands dz {d['lands_dz']:+.3f} on {d['lands_on']} ({d['landing_offset']:.3f}), rests theta {d['rests_theta']:+d} "
                 f"dy {d['rests_dy']:+.2f} dz {d['rests_dz']:+.3f} on {d['rests_on']} ({d['rest_offset']:.3f}; path <= {d['worst_on_path']:.3f})")
                 for k, d in dd.items()))
    for k, v in rep.get('gate', {}).items():
        L.append(f'  gate {k}: {v}')
    for k, (ok, w) in rep.get('verdict', {}).items():
        L.append(f"  {'PASS' if ok is True else ('ACCEPTED' if ok == 'accepted' else 'FAIL')}  {k}" + (f'  {w}' if w is not None else ''))
    return '\n'.join(L)


# Ian's rule: the standard and the light-strip builds share every printed part but the tub, so a light-strip
# owner prints one extra part. These are every non-tub file build_all writes (the lid with its side keys and
# taken apart, the midplate, the bottom keys and cranks as assembled, and the print parts: key-426 - both
# builds have the face at 6.00 - crank-M, crank-T and the chin and gate coupons, whose pieces of the tub are cut
# away from anything the light strip changes) and the side gate. Both have all four page keys, so all five side keys,
# whatever layout this process builds.
SHARED = ['lid', 'lid_body', *[f'skey_{r}' for r in P.TAB_ROOTS_ALL], 'midplate',
          *[f'{k}_{r}' for k in ('key', 'crank') for r in hw.BOTTOM_SWITCHES], 'gate', *BOTTOM_KEY_PRINT_PARTS]
# What each option changes: an option build shares every other part with the build without that option (its twin).
#   nodev     the tub and the lid (their top wall: the header opening closed, the top tongue and the lid's groove for it)
#   <sides>   the tub and the lid (a left-out key: the tub's slot and nub window closed, the lid's key and its cut gone,
#             the plain wall in both); the side keys it keeps are the all-keys build's
OPTION_CHANGES = {o: ('tub', 'lid', 'lid_body') for o in variants.OPTIONS}


def side_key_files(build):
    """skey_<ref> of each side key that build has, in TAB_ROOTS_ALL's order (as build_all writes them)."""
    keep = variants.SIDE_SETS[variants.parse(build).sides]
    return [f'skey_{r}' for r in P.TAB_ROOTS_ALL if r in keep]


def part_files(build):
    """Every part build_all writes for that build (an STL each; a STEP too, but for lid_body and the side keys),
    whatever build this process is: read from that build's own slug."""
    c = variants.parse(build)
    bk = ([*[f'{k}_{r}' for k in ('key', 'crank') for r in hw.BOTTOM_SWITCHES], 'gate', *BOTTOM_KEY_PRINT_PARTS]
          if c.bottom_keys else [])
    return ['tub', 'lid', 'midplate', *bk, 'lid_body', *side_key_files(build)]


def shares(build):
    """[(axis, twin, the parts the two must share)]: one per axis on which the build is not the default
    (variants.twins: the same configuration with that axis at its default), so every claim holds wherever it applies:
      panel   light strip -> the touch panel's: every part but the tub (Ian's rule; for light-strip itself that is
              SHARED, which shared_parts_check also holds). So the lid never depends on the panel
      chin    chinless -> the keyed build's: the midplate and its side keys (its tub and lid are its own)
      sides   a side-key layout -> all four keys': every part but the tub and the lid (OPTION_CHANGES): the side keys
              it keeps, the midplate and the bottom-key parts
      dev     nodev -> J6's: every part but the tub and the lid (OPTION_CHANGES)
    The bottom-key print parts include the coupons, which are crops of this build's own tub (coupons.py), not
    params-only parts: their STL bytes are compared like every other part's, on every keyed configuration."""
    c = variants.parse(build)
    files = part_files(build)
    out = []
    for axis, t in variants.twins(build):
        if axis == 'panel':
            names = [n for n in files if n != 'tub']
        elif axis == 'chin':
            names = ['midplate', *side_key_files(build)]
        else:
            names = [n for n in files if n not in OPTION_CHANGES['nodev' if axis == 'dev' else c.sides]]
        out.append((axis, t, names))
    return out


def primary_share(build):
    """(twin, parts) of the claim out/<build>/shared.json holds, as before the variants: the twin of the slug's last
    token (<x>-nodev -> <x>, <x>-<sides> -> <x>, chinless -> standard, light-strip-chinless -> chinless); None for
    standard (it has none) and for light-strip (shared_parts_check: out/shared-parts.json)."""
    c = variants.parse(build)
    axis = (('dev' if c.opts[-1] == 'nodev' else 'sides') if c.opts else
            {'chinless': 'chin', 'light-strip-chinless': 'panel'}.get(c.base))
    return next(((t, names) for a, t, names in shares(build) if a == axis), None)


def compare_parts(dir_a, dir_b, names):
    """Each part as the two folders hold it: the same STL bytes, or else (a tessellation can differ with no change
    in the solid) its two STEPs with the same faces (same_faces: every face's type, area and centre) and the same
    volume. The right-pair keyed builds' coupon-gate takes the second path: the same 768 faces, one quad of its STL
    split along the other diagonal. Never a boolean: OCC's cut of two identical shapes can come back empty (0.0, as
    if equal) or whole when it fails (variants CHECK_geometry G3, G6)."""
    rep = {}
    for name in names:
        a, b = (d / f'{name}.stl' for d in (dir_a, dir_b))
        if a.read_bytes() == b.read_bytes():
            rep[name] = {'same': True, 'by': 'STL bytes'}
            continue
        sa, sb = (d / f'{name}.step' for d in (dir_a, dir_b))
        if not (sa.exists() and sb.exists()):
            rep[name] = {'same': False, 'by': 'STL bytes (no STEP)'}
            continue
        va, vb = (cq.importers.importStep(str(f)).val() for f in (sa, sb))
        sf = same_faces(va, vb)
        rep[name] = {'same': sf['same'] and abs(va.Volume() - vb.Volume()) < 1e-4, 'by': 'STEP face signatures',
                     'faces': sf['faces'], 'volumes': [round(va.Volume(), 4), round(vb.Volume(), 4)],
                     **({} if sf['same'] else {'only_a': sf['only_a'], 'only_b': sf['only_b']})}
    return rep


def shared_parts_check():
    """Each shared part as the two print builds wrote it (compare_parts). Asserts, so a variant-gated change that
    reaches a shared part stops the build."""
    builds = ('standard', 'light-strip')
    rep = compare_parts(*(hw.ROOT / 'out' / v for v in builds), SHARED)
    (hw.ROOT / 'out' / 'shared-parts.json').write_text(json.dumps(rep, indent=1))
    bad = [k for k, r in rep.items() if not r['same']]
    print(f"\nshared parts ({', '.join(builds)}): " +('all identical' if not bad else f'DIFFER: {bad}')
          + ' -> out/shared-parts.json', flush=True)
    assert not bad, f'the variants must share every part but the tub; these differ: {bad}'
    return rep


def _twin_missing(twin, names):
    d = hw.ROOT / 'out' / twin
    return [n for n in names if not (d / f'{n}.stl').exists()]


def share_check(build=None):
    """A build other than the two print builds (whose rule shared_parts_check holds) against the twin it derives
    from (primary_share): the positive proof that an option, a side-key layout or chinless changes only its own
    parts. -> out/<build>/shared.json. Asserts; a twin that is not built fails it (pipeline.py brings every twin
    into the run). Run it after the twin's build, not beside it. Every twin of a build: twin_shares."""
    build = build or P.BUILD
    s = primary_share(build)
    if s is None:
        return None
    base, names = s
    bdir, mdir = hw.ROOT / 'out' / base, hw.ROOT / 'out' / build
    rep = {'base': base, 'parts': {}}
    missing = _twin_missing(base, names)
    if missing:
        rep['built'] = False
        rep['missing'] = missing
        print(f'FAIL: {build}: share check: out/{base}/ is not built (no {", ".join(missing)})', flush=True)
    else:
        rep['built'] = True
        rep['parts'] = compare_parts(bdir, mdir, names)
        rep['differ'] = [k for k, r in rep['parts'].items() if not r['same']]
        print(f"{build} shares with {base}: {', '.join(names)}: "
              + ('all identical' if not rep['differ'] else f"DIFFER: {rep['differ']}") + f' -> out/{build}/shared.json', flush=True)
    (mdir / 'shared.json').write_text(json.dumps(rep, indent=1))
    assert rep['built'], f'{build}: its twin out/{base}/ is not built ({missing}): build it first (pipeline.py brings it in)'
    assert not rep.get('differ'), f"{build} must share {names} with {base}; these differ: {rep['differ']}"
    return rep


def twin_shares(builds):
    """Every twin claim (shares) of each of builds against the twin's folder (compare_parts) -> out/shares-all.json:
    {build: {axis: {twin, built, parts, differ}}}, one entry per build, replaced whenever that build's share checks
    run (pipeline.py's finish steps, one after the other); the other builds' entries are left as they were. Asserts:
    a part that differs, or a twin that is not built, fails."""
    f = hw.ROOT / 'out' / 'shares-all.json'
    try:
        allrep = json.loads(f.read_text())
    except (OSError, ValueError):
        allrep = {}
    bad = []
    for b in builds:
        mdir = hw.ROOT / 'out' / b
        ent = {}
        for axis, t, names in shares(b):
            missing = _twin_missing(t, names)
            if missing:
                ent[axis] = {'twin': t, 'built': False, 'missing': missing}
                bad.append(f'{b} vs {t} ({axis}): the twin is not built ({", ".join(missing)})')
                continue
            parts = compare_parts(hw.ROOT / 'out' / t, mdir, names)
            differ = [k for k, r in parts.items() if not r['same']]
            ent[axis] = {'twin': t, 'built': True, 'parts': parts, 'differ': differ}
            if differ:
                bad.append(f'{b} vs {t} ({axis}): {", ".join(differ)} differ')
        allrep[b] = ent
        print(f'{b} twins: ' + ('; '.join(f"{a} {r['twin']} " + ('NOT BUILT' if not r['built'] else
                                                                'DIFFER ' + ','.join(r['differ']) if r['differ'] else
                                                                f"{len(r['parts'])} parts the same")
                                          for a, r in ent.items()) or 'none (the default on every axis)'), flush=True)
    rank = {s: i for i, s in enumerate(variants.ALL)}
    allrep = dict(sorted(allrep.items(), key=lambda kv: (rank.get(kv[0], len(rank)), kv[0])))
    tmp = f.with_name(f.name + '.tmp')
    tmp.write_text(json.dumps(allrep, indent=1))
    os.replace(tmp, f)
    print(f'twin shares of {len(builds)} builds -> out/shares-all.json', flush=True)
    assert not bad, 'twin shares: ' + '; '.join(bad)
    return allrep


CRANKS = ('crank-M', 'crank-T')
CROSS_PLANES = (0.0, 1.0, -1.0, 3.9, -3.9, 4.65, -4.65, 5.0, -5.0)   # dx of the YZ sections compared


def _yz_face(solid, x):
    """The solid's section at X x (a compound of planar faces)."""
    return cq.Compound.makeCompound(cq.Workplane('YZ').add([solid]).section(x).faces().vals())


def cross_project_check(tol_v=0.01, tol_b=0.002, tol_s=0.002):
    """The rule that both case projects print the same crank (keys.py's shared crank block, with its shared cheek
    block the same text as case-368/src/crank.py's): this project's crank-M and crank-T (out/standard, their STEPs)
    against case-368's, when that project is built: volume within tol_v mm3, bounds within tol_b, and YZ sections at
    CROSS_PLANES with at most tol_s mm2 of symmetric difference. The STEPs, not the STLs: the two projects tessellate
    at different tolerances. Raises AssertionError naming each part that differs; prints a warning (and records it)
    when case-368 is not built. The result goes into out/shared-parts.json under 'cross_project'."""
    mine, other = hw.ROOT / 'out' / 'standard', hw.ROOT.parent / 'case-368' / 'out' / 'standard'
    rep = {'other': str(other), 'tolerances': {'mm3': tol_v, 'bounds_mm': tol_b, 'section_mm2': tol_s}, 'parts': {}}
    if not all((other / f'{n}.step').exists() for n in CRANKS):
        rep['built'] = False
        print(f'WARNING: cross-project crank check skipped: {other} has no crank STEPs (build case-368 first)')
    else:
        rep['built'] = True
        bad = []
        for n in CRANKS:
            a = cq.importers.importStep(str(mine / f'{n}.step')).val()
            b = cq.importers.importStep(str(other / f'{n}.step')).val()
            ba, bb = a.BoundingBox(), b.BoundingBox()
            db = max(abs(p - q) for p, q in zip((ba.xmin, ba.xmax, ba.ymin, ba.ymax, ba.zmin, ba.zmax),
                                                (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)))
            secs = {}
            for x in CROSS_PLANES:
                fa, fb = _yz_face(a, x), _yz_face(b, x)
                secs[f'{x:+.2f}'] = round(fa.cut(fb).Area() + fb.cut(fa).Area(), 6)
            row = {'mm3': [round(a.Volume(), 4), round(b.Volume(), 4)], 'bounds_max_diff': round(db, 6),
                   'section_symdiff_mm2': secs}
            row['same'] = (abs(a.Volume() - b.Volume()) <= tol_v and db <= tol_b and max(secs.values()) <= tol_s)
            rep['parts'][n] = row
            if not row['same']:
                bad.append(n)
        rep['differ'] = bad
    f = hw.ROOT / 'out' / 'shared-parts.json'
    sp = json.loads(f.read_text()) if f.exists() else {}
    sp['cross_project'] = rep
    f.write_text(json.dumps(sp, indent=1))
    if rep.get('differ'):
        raise AssertionError(f"cranks differ from case-368's: {rep['differ']} (out/shared-parts.json 'cross_project')")
    return rep


def _step_text(path):
    """A STEP file's text without its export timestamp, so two exports of one shape compare equal."""
    return re.sub(rb"'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d'", b"''", path.read_bytes(), count=1)


# What print/4.26/ takes from each print build (params.PRINT_BUILDS), as (part, file name there): every shared part
# once, from the standard build, and each build's own parts. Declared, so print/4.26/ is exactly these files: a
# print build is added here and to PRINT_BUILDS together, and the default run (which builds every print build)
# makes them all.
PRINT_JOBS = {'standard': [(n, n) for n in ('lid', 'midplate', *BOTTOM_KEY_PRINT_PARTS, 'gate')] + [('tub', 'tub-standard')],
              'light-strip': [('tub', 'tub-light-strip')],
              # chinless: its own tub and lid; the midplate (and the side keys, part of the lid) are the shared ones
              'chinless': [('tub', 'tub-chinless'), ('lid', 'lid-chinless')],
              # light-strip chinless (2026-10-07): only its tub; it prints the chinless lid (share_check: the lid never
              # depends on the panel) and the shared midplate
              'light-strip-chinless': [('tub', 'tub-light-strip-chinless')]}
assert set(PRINT_JOBS) == set(P.PRINT_BUILDS), 'every print build needs its PRINT_JOBS'


def write_print(built):
    """print/4.26/ at the repo root (committed): what to print (PRINT_JOBS). Each shared part once, from the
    standard build (they are the same in both, shared_parts_check), and each print build's tub: the STL oriented
    and placed as sliced (plates.ORIENT), the STEP in the CAD frame (the bottom-key parts at their key's centre, X 0;
    the side gate's STEP is in its print pose too, on its inner face, as the STL), the chinless build's tub and
    lid (tub-chinless, lid-chinless) and the light-strip chinless build's tub (tub-light-strip-chinless; its lid is
    lid-chinless). A STEP that differs from the one there only by its timestamp is left as it is. Files there that no
    print build makes are removed; the rod is a cut length, not a part, so it gets a note (ROD.txt). Only from a run
    that built every print build (built): a partial run or a single build never writes here, so it can neither
    remove nor overwrite a print file.
    enclosures/make_plates.py lays the standard build (plate 1), the APEM cranks (2), the chinless case (its tub and
    lid, and the midplate; 3) and the test prints (4) out in print/silkscreen-426-plates.3mf, a generic OrcaSlicer
    project of the released builds; print/cc2-local/ (git-ignored) has the author's CC2 file with all four builds."""
    import plates
    missing = [b for b in P.PRINT_BUILDS if b not in built]
    if missing:
        raise SystemExit(f'write_print: this run did not build {missing}; print/4.26/ left as it is')
    PRINT.mkdir(parents=True, exist_ok=True)
    src = {v: hw.ROOT / 'out' / v for v in P.PRINT_BUILDS}
    jobs = [(part, v, name) for v in P.PRINT_BUILDS for part, name in PRINT_JOBS[v]]
    made = set()
    for part, v, name in jobs:
        plates.oriented(part, src[v]).export(PRINT / f'{name}.stl')
        step, dest = src[v] / f'{part}.step', PRINT / f'{name}.step'
        if part == 'gate':                                  # its STEP in the print pose, as its STL
            step = src[v] / 'gate-print.step'
            cq.exporters.export(keys.gate('print'), str(step))
        if not dest.exists() or _step_text(dest) != _step_text(step):
            shutil.copyfile(step, dest)
        made |= {f'{name}.stl', f'{name}.step'}
    for f in PRINT.glob('*'):
        if f.suffix in ('.stl', '.step') and f.name not in made:
            f.unlink()
    (PRINT / 'ROD.txt').write_bytes(ROD_NOTE.encode())
    print(f"print/4.26/: {', '.join(n for _, _, n in jobs)} (.stl oriented to print, .step in the CAD frame), ROD.txt", flush=True)


_PLAY = P.ROD_STOPS[1] - P.ROD_STOPS[0] - P.ROD_CUT                 # end play, nominal (0.50)
_OUT = P.X0 - (P.RAIL_END_X - P.ROD_CUT)                            # rod out of the side after the service push
ROD_NOTE = f"""Bottom keys: the crank rod (not printed) and its gate (printed, gate.stl)

Rod: 1.75 mm PLA filament, cut to {P.ROD_CUT:.2f} +- 0.2 mm. One per case.
  - Make it in the rod jig (print/rod-jig.stl, also on plate 1 of print/silkscreen-426-plates.3mf). Cut
    about 80 mm of filament and warm it until it goes limp: about 10 s in hot water (a kettle left to stand
    a minute), or lay it in the jig's groove and set the jig on the bed at 60 C for 5 minutes. Press it
    into the groove and let it cool there for half a minute. While it is still warm, cut it at both slots
    with your scraper's razor blade: it comes out straight, {P.ROD_CUT:.2f} long and square at both ends. Lift
    it out at the window in the middle.
  - Taper one end (the one that goes in first) in a pencil sharpener, stopping while the tip still has a
    flat about {P.ROD_TIP['flat']:.1f} mm across (about half the rod's width). Not a needle point. The other end
    stays square: it bears on the gate.
  - It goes in from the case's left side (-X): along the channel in the slot beside the chin, through
    the rings and the four cranks (don't hold them; the taper picks them up), until its tail is flush
    with the case side or just inside.
Gate: print two (inner face on the bed); one is a spare. Right after the rod, drop it into the slot from
  the open back, bevel down, small hole outward, and press it level with the rim: it pushes the rod the
  last {P.ROD_STOP_X0 - P.X0:.2f} mm. If it stops proud, lift it, push the tail a little further in, press again.
  End play is then {_PLAY - 0.2:.1f}-{_PLAY + 0.2:.1f} mm. No screw.
  To take it out: a straightened paperclip in its small hole, lift. Then push the rod's right end
  toward -X with a small screwdriver until it stops; {_OUT - 0.2:.1f}-{_OUT + 0.2:.1f} mm stands out of the slot.
Cranks: crank-T for TS365ZJ boards (every JLC board), crank-M for APEM MJTP1117.
  Each cheek holds the rod in a closed hole: feed the rod through; its taper finds the holes.
  Ream each crank's two bores with a {P.CRANK_REAM} mm drill; the rod must slide and turn freely.
  Print the cranks with elephant-foot compensation 0 and Arachne walls, and the keys (standing on
  their -X end) and the gate with elephant-foot compensation 0 (OrcaSlicer, per object; the plate
  file has them), no brim, no supports.
Keys (key-426, test 2): each has two hooks that run up two slots in the chin wall. Keep the tub
  face-down from the keys until the board is in, supported so the caps can hang out 2.4 mm: on a
  soft cloth, on a spacer about 3 mm thick under the screen area, or with the chin over the table's
  edge. Not flat on a bare table: that pushes the keys flush, and the board then cannot go in
  without forcing all four switches. Drop each key in from inside, hooks in the slots, and let it
  slide out until both hooks stop (2.4 proud, level); then the cranks, the rod, the gate and the
  board. Turned face-up before the board, the keys sink; face-down again puts them back.
Before the first full print: the gate coupon (fit, cam, and the 5.5 kg push). coupon-chin with one
  key-426 is an optional fit check for the hooks (about 15 minutes; nothing is chosen from it).
  See enclosures/case-426/README.md, "Bottom keys".
"""


def _vol(s, b):
    return s.intersect(box(*b).val()).Volume()


def _full(s, b, tol=1e-3):
    """s fills the box b: [volume of s in it, the box's volume, ok]."""
    v, vb = _vol(s, b), box(*b).val().Volume()
    return [round(v, 4), round(vb, 4), abs(v - vb) <= tol]


def _empty(s, b, tol=1e-4):
    """nothing of s in the box b: [volume, ok]."""
    v = _vol(s, b)
    return [round(v, 5), v <= tol]


def _mirror_x(s):
    """s mirrored about the case's centre plane X = (X0 + X1) / 2."""
    xc = (P.X0 + P.X1) / 2
    return s.mirror(cq.Vector(1, 0, 0), cq.Vector(xc, 0, 0))


def chin_check(shapes):
    """chinless (no bottom keys): every bottom-key feature positively absent. Each one is gated on P.BOTTOM_KEYS (an
    empty KEY_REFS would silently leave a long rail, the rod's hole and the gate's slot), so each gets a check that
    sees it if it came back. Generic in BOT_IN / Y0, so it holds whatever the chin's length:
      parts         no key, crank, gate, coupon or rod parts in PARTS / PRINT_PARTS or in out/<build>/
      chin wall     solid: no key openings' lead-in, hook slots or rod hole in it
      skin          solid over the chin: no key openings
      chin cavity   empty from the chin wall to the pocket's bottom wall: no rail, rings, seats, slot strips or webs
      side walls    beside the chin as they are above it
      corners       the -X lower corner is the +X one mirrored: no rod hole, gate slot (mouth, cavity, floor,
                    chamfers, lead-in) or gate notch in the tongue
      seam          the seam's V runs the chin's whole width (no rim relief over a key row)
      tongues       both side tongues start at TONGUE_RUNS and are whole to y 9 (no gate notch)
      tub           the same as its keyed twin's tub above y 11 (variants.twin(BUILD, 'chin'): the same panel, side
                    keys and dev header, with bottom keys; standard for chinless, light-strip for light-strip-chinless)
      lid           the H3 / H4 bosses run into the chin wall, the tray between them is empty, the grip grooves are at
                    GRIP_GROOVES_Y, and the printed lid is the keyed twin's away from the chin and the back icon
                    (y 8-40 and 72-Y1)
                    The twin's tub.step and lid.step must be there (pipeline.py's cross_reads bring the twin into the
                    run): when they are not, these two FAIL; they are never skipped.
      wordmark      the engraved ink centred on the face below the window (the front round's tangent Y0 + FRONT_EDGE_R
                    to the window's bevel on the face, WIN_Y0 - WINDOW_FACE_W), as cut in the tub; the back icon
                    centred on the back
      board edge    the board's bottom edge to the tub's chin (board at 0 / -0.2 / -0.4 in Y; the routed outline is
                    +-0.2 more): >= 0.15 at -0.4
      DNP proof     what SW9 / SW8 / SW3 / SW2, if fitted, would overlap (reported, not a failure: the board must not
                    have them)
    -> out/<build>/chin.json. Asserts."""
    import joint
    from tub import LOW_X0, LOW_X1
    t0 = time.time()
    T, L = shapes['tub'].val(), shapes['lid'].val()
    y1 = P.POCKET_Y0 - 1.0 - 0.085                           # 3.95: short of the pocket's bottom wall
    zt = P.Z_FRONT + 1.0
    rep, ok = {}, {}
    bad = [n for n in [*PARTS, *PRINT_PARTS] if n.startswith(('key', 'crank', 'gate', 'coupon'))]
    left = sorted(f.name for g in BOTTOM_KEY_FILES for f in OUT.glob(g))
    rep['bottom-key parts'], rep['bottom-key files in out'] = bad, left
    ok['no bottom-key parts or files'] = not bad and not left
    # the side walls beside the chin up to y 9.0; with the light strip only to just short of its pocket-wall relief
    # (STRIP_WALL_RELIEF, from y 8.7), which is the strip's own feature, not a bottom-key one
    wy1 = P.STRIP_WALL_RELIEF['y'][0] - 0.05 if P.LIGHT_STRIP else 9.0
    full = {'chin wall solid (no openings, lead-in, hook slots, rod hole)':
            (1.0, 59.0, P.Y0 + 0.05, P.BOT_IN - 0.05, P.SEAM + 0.45, P.Z_FRONT - P.FRONT_EDGE_R),
            'skin solid over the chin (no key openings)': (6.0, 54.0, P.BOT_IN + 0.05, y1, P.LIP + 0.02, P.Z_FRONT - 0.42),
            '-X side wall plain beside the chin': (P.X0 + 0.3, LOW_X0 - 0.05, 5.6, wy1, P.SEAM + 0.45, P.LIP),
            '+X side wall plain beside the chin': (LOW_X1 + 0.05, P.X1 - 0.3, 5.6, wy1, P.SEAM + 0.45, P.LIP)}
    for k, b in full.items():
        rep[k] = _full(T, b)
        ok[k] = rep[k][2]
    empty = {'chin cavity empty: no rail, rings, seats, slot strips or webs': (6.0, 54.0, P.BOT_IN + 0.05, y1, P.SEAM + 0.05, P.LIP - 0.02),
             'chin cavity empty below the screw bosses': (0.2, 59.8, P.BOT_IN + 0.05, y1, P.SEAM + 0.05, P.PCB_FRONT - 0.05),
             'chin cavity empty out to the side walls': (LOW_X0 + 0.06, LOW_X1 - 0.06, P.BOT_IN + 1.55, y1, P.SEAM + 0.05, P.PCB_FRONT - 0.05),
             "seam's V along the whole chin": (1.0, 59.0, P.Y0 - 0.01, P.Y0 + 0.15, P.SEAM, P.SEAM + 0.2)}
    for k, b in empty.items():
        rep[k] = _empty(T, b)
        ok[k] = rep[k][1]
    # the lower corners: the -X one (rod hole, gate slot, gate notch) against the +X one mirrored. The board's H3 and H4
    # are 0.005 off a mirror pair (x 3.7475 / 56.2475: 0.13 mm3 at their bosses and pilots), so the boss over H3 and
    # the mirror of H4's are left out of both (the rod's hole is below them, the gate's slot outside them)
    xc = (P.X0 + P.X1) / 2
    fps = hw.footprints()
    (h3x, h3y), (h4x, _) = fps['H3']['cad'], fps['H4']['cad']
    bx = (min(h3x, 2 * xc - h4x) - 2.5, max(h3x, 2 * xc - h4x) + 2.5)
    boss = box(*bx, h3y - 2.5, h3y + 2.5, P.PCB_FRONT - 0.1, zt).val()
    lo_l = T.intersect(box(P.X0 - 1, 6.0, P.Y0 - 1, 3.3, P.SEAM - 2.0, zt).val()).cut(boss)
    lo_r = T.intersect(box(2 * xc - 6.0, P.X1 + 1, P.Y0 - 1, 3.3, P.SEAM - 2.0, zt).val())
    m = _mirror_x(lo_r).cut(boss)
    try:
        sd = lo_l.cut(m).Volume() + m.cut(lo_l).Volume()
    except Exception:                                        # a failed boolean: the volumes still say something
        sd = float('nan')
    rep['lower corners: -X vs +X mirrored (H3 / H4 bosses left out)'] = {'mm3': [round(lo_l.Volume(), 4), round(m.Volume(), 4)], 'symdiff_mm3': round(sd, 5)}
    ok['lower corners mirror each other (no rod hole, gate slot or notch)'] = abs(lo_l.Volume() - m.Volume()) < 1e-3 and sd < 1e-3
    # the tongues from their start to y 9: the profile's area times the length, both sides (nothing cut from them)
    J = P.JOINT
    area = J['t'] * J['h'] - J['lead'] ** 2
    a0 = joint.runs()['left'][0][0], joint.runs()['right'][0][0]
    tl = T.intersect(box(LOW_X0 - 1.5, LOW_X0 + 0.3, P.Y0 - 1, 9.0, P.SEAM - 2.0, P.SEAM).val())
    tr = T.intersect(box(LOW_X1 - 0.3, LOW_X1 + 1.5, P.Y0 - 1, 9.0, P.SEAM - 2.0, P.SEAM).val())
    rep['tongues to y 9'] = {'start': list(a0), 'declared': [P.TONGUE_RUNS['left'][0][0], P.TONGUE_RUNS['right'][0][0]],
                             'mm3': [round(tl.Volume(), 4), round(tr.Volume(), 4)],
                             'expected_mm3': [round(area * (9.0 - a), 4) for a in a0],
                             'ymin': [round(tl.BoundingBox().ymin, 4), round(tr.BoundingBox().ymin, 4)]}
    ok['tongues start at TONGUE_RUNS and run whole (no gate notch)'] = (
        a0 == (P.TONGUE_RUNS['left'][0][0], P.TONGUE_RUNS['right'][0][0])
        and all(abs(v - area * (9.0 - a)) < 1e-3 for v, a in zip((tl.Volume(), tr.Volume()), a0))
        and all(abs(s.BoundingBox().ymin - a) < 1e-3 for s, a in zip((tl, tr), a0)))
    # the rest of the tub is the keyed twin's (the same panel, side keys and options, with bottom keys)
    ref = variants.twin(P.BUILD, 'chin')
    std = hw.ROOT / 'out' / ref / 'tub.step'
    key = f'tub above y 11 vs out/{ref}/tub.step'
    not_built = f'NOT BUILT: out/{ref}/ (the keyed twin must be built first; pipeline.py brings it into the run)'
    if std.exists():
        S = cq.importers.importStep(str(std)).val()
        b = box(P.X0 - 1, P.X1 + 1, 11.0, P.Y1 + 1, P.SEAM - 2.0, zt).val()
        a, c = T.intersect(b), S.intersect(b)
        try:
            d = [round(a.cut(c).Volume(), 5), round(c.cut(a).Volume(), 5)]
        except Exception:
            d = [float('nan'), float('nan')]
        rep[key] = {'mm3': [round(a.Volume(), 4), round(c.Volume(), 4)], 'differences_mm3': d}
        ok[f'tub above y 11 = the {ref} tub'] = max(d) < 1e-3 and abs(a.Volume() - c.Volume()) < 1e-3
    else:
        rep[key] = not_built
        ok[f'tub above y 11 = the {ref} tub'] = False
    # the lid: each H3 / H4 boss a block from the chin wall to short of its counterbore, the tray between them empty,
    # the grip grooves where params puts them (and solid between them)
    for r_ in ('H3', 'H4'):
        hx, _ = fps[r_]['cad']
        k = f'lid {r_} boss merged into the chin wall'
        rep[k] = _full(L, (hx - 2.9, hx + 2.9, P.BOT_IN + 0.02, 0.85, P.LID_FLOOR_IN + 0.02, -4.52))
        ok[k] = rep[k][2]
    k = 'lid tray empty between the H3 / H4 blocks'
    rep[k] = _empty(L, (8.0, 52.0, P.BOT_IN + 0.02, 3.0, P.LID_FLOOR_IN + 0.02, P.SEAM - 0.02))
    ok[k] = rep[k][1]
    gx = P.GRIP_GROOVE['x']
    for i, gy in enumerate(P.GRIP_GROOVES_Y):
        k = f'lid grip groove at y {gy}'
        rep[k] = _empty(L, (gx[0] + 0.5, gx[1] - 0.5, gy - 0.3, gy + 0.3, P.Z_BACK - 0.1, P.Z_BACK + 0.3))
        ok[k] = rep[k][1]
        if i < len(P.GRIP_GROOVES_Y) - 1:
            k = f'lid back solid between the grooves at y {gy} and {P.GRIP_GROOVES_Y[i + 1]}'
            rep[k] = _full(L, (gx[0] + 0.5, gx[1] - 0.5, gy + 0.5, P.GRIP_GROOVES_Y[i + 1] - 0.5, P.Z_BACK + 0.01, P.Z_BACK + 0.3))
            ok[k] = rep[k][2]
    rep['grip grooves to the H3 / H4 counterbores (x)'] = [round(gx[0] - (h3x + P.M2_HEAD_CB / 2), 3),
                                                          round((h4x - P.M2_HEAD_CB / 2) - gx[1], 3)]
    # the printed lid (with its side keys: out/<build>/lid.step, as exported) against the reference build's, in bands
    # clear of the chin's changes (y < 8: blocks, grooves, tray corner) and of the back icon, which follows the case's
    # centre (y 40-72). OCCT's cut can fail on coincident faces and give back the whole band; a band where it did is
    # compared by volume and its two halves' cuts instead.
    std_lid = hw.ROOT / 'out' / ref / 'lid.step'
    key = f'printed lid vs out/{ref}/lid.step, away from the chin and the back icon'
    if std_lid.exists() and (OUT / 'lid.step').exists():
        A = cq.importers.importStep(str(OUT / 'lid.step')).val()
        S = cq.importers.importStep(str(std_lid)).val()
        bands = {}

        def band(y0, y1):
            b = box(P.X0 - 1, P.X1 + 1, y0, y1, P.Z_BACK - 1.0, P.Z_FRONT + 1.0).val()
            a, c = A.intersect(b), S.intersect(b)
            va, vc = a.Volume(), c.Volume()
            try:
                d = [a.cut(c).Volume(), c.cut(a).Volume()]
            except Exception:
                d = [float('nan')] * 2
            return va, vc, d

        for y0, y1 in ((8.0, 40.0), (72.0, 95.0), (95.0, 105.0), (105.0, P.Y1 + 1.0)):
            va, vc, d = band(y0, y1)
            row = {'mm3': [round(va, 4), round(vc, 4)], 'differences_mm3': [round(x, 5) for x in d]}
            if not max(d) < 1e-3 and abs(va - vc) < 1e-3:       # a failed cut: split the band and try again
                row['split'] = {}
                for a0, a1 in ((y0, (y0 + y1) / 2 + 0.013), ((y0 + y1) / 2 + 0.013, y1)):
                    sa, sc, sd = band(a0, a1)
                    row['split'][f'{a0:.3f}-{a1:.3f}'] = {'mm3': [round(sa, 4), round(sc, 4)], 'differences_mm3': [round(x, 5) for x in sd]}
                row['same'] = all(max(v['differences_mm3']) < 1e-3 and abs(v['mm3'][0] - v['mm3'][1]) < 1e-3 for v in row['split'].values())
            else:
                row['same'] = max(d) < 1e-3 and abs(va - vc) < 1e-3
            bands[f'y {y0}-{y1:.1f}'] = row
        rep[key] = bands
        ok[f'printed lid = the {ref} lid away from the chin and the back icon'] = all(r['same'] for r in bands.values())
    else:
        rep[key] = not_built if not std_lid.exists() else f'NOT BUILT: out/{OUT.name}/lid.step'
        ok[f'printed lid = the {ref} lid away from the chin and the back icon'] = False
    # the wordmark as engraved in the tub (its 0.4 deep ink, read 0.2 under the face), on the face below the window
    f0, f1 = P.Y0 + P.FRONT_EDGE_R, P.WIN_Y0 - P.WINDOW_FACE_W
    ink = box(6.0, 54.0, f0 + 0.01, f1 - 0.01, P.Z_FRONT - 0.3, P.Z_FRONT - 0.1).val().cut(T).BoundingBox()
    m0, m1 = ink.ymin - f0, f1 - ink.ymax
    rep['wordmark (front face below the window; ink as cut)'] = {
        'face_y': [round(f0, 3), round(f1, 3)], 'face_centre_y': round((f0 + f1) / 2, 3), 'cfg_y': P.LOGO['y'],
        'ink_x': [round(ink.xmin, 3), round(ink.xmax, 3)], 'ink_y': [round(ink.ymin, 3), round(ink.ymax, 3)],
        'ink_centre_y': round((ink.ymin + ink.ymax) / 2, 3), 'margins_below_above': [round(m0, 3), round(m1, 3)]}
    ok['wordmark centred on the face below the window (margins within 0.05)'] = abs(m0 - m1) <= 0.05 and min(m0, m1) > 1.0
    # the back icon, as engraved in the lid, on the back's flat (from the back round's tangent at each end); read
    # between the grip grooves and the top screw's counterbore (y 110.7), which are the back's only other cuts
    b0, b1 = P.Y0 + P.BACK_EDGE_R, P.Y1 - P.BACK_EDGE_R
    lb = box(8.0, 52.0, max(P.GRIP_GROOVES_Y) + 1.0, 105.0, P.Z_BACK + 0.1, P.Z_BACK + 0.3).val().cut(L).BoundingBox()
    rep['back icon (back flat; ink as cut)'] = {'flat_y': [round(b0, 3), round(b1, 3)], 'flat_centre_y': round((b0 + b1) / 2, 3),
                                                'ink_x': [round(lb.xmin, 3), round(lb.xmax, 3)], 'ink_y': [round(lb.ymin, 3), round(lb.ymax, 3)],
                                                'ink_centre': [round((lb.xmin + lb.xmax) / 2, 3), round((lb.ymin + lb.ymax) / 2, 3)]}
    ok['back icon centred on the back'] = (abs((lb.ymin + lb.ymax) / 2 - (P.Y0 + P.Y1) / 2) <= 0.05
                                           and abs((lb.xmin + lb.xmax) / 2 - (P.X0 + P.X1) / 2) <= 0.05)
    rep['case outside (x, y, z)'] = [round(P.X1 - P.X0, 3), round(P.Y1 - P.Y0, 3), round(P.Z_FRONT - P.Z_BACK, 3)]
    # the board's bottom edge to the chin (the tub over the board's width, below the bosses' seats, up to 1.6 past the
    # chin wall's face so the cavity's corners are in it)
    pcb = hw.solids()['PCB'].intersect(box(-1.0, 61.0, -1.0, 3.0, -0.5, P.PCB_FRONT + 0.5).val())
    chin = T.intersect(box(-0.5, 60.5, P.Y0 - 1, P.BOT_IN + 1.6, P.SEAM - 2.0, P.PCB_FRONT - 0.01).val())
    edge = {f'{dy:+.1f}': round(pcb.moved(cq.Location(cq.Vector(0, dy, 0))).distance(chin), 3) for dy in (0.0, -0.2, -0.4)}
    rep['board edge to the chin (board moved in Y; the outline is +-0.2 more)'] = edge
    ok['board edge >= 0.15 from the chin with the board 0.4 toward it'] = edge['-0.4'] >= 0.15
    # and moved 0.2 in X as well (the plan corners: the cavity's R1.5 against the board's R1.5 / R1.75)
    edge_x = {f'{dx:+.1f}, {dy:+.1f}': round(pcb.moved(cq.Location(cq.Vector(dx, dy, 0))).distance(chin), 3)
              for dx in (-0.2, 0.2) for dy in (0.0, -0.2, -0.4)}
    rep['board edge to the chin (board moved in X and Y)'] = edge_x
    ok['board >= 0.15 from the chin moved 0.2 in X and 0.4 toward it'] = min(edge_x.values()) >= 0.15
    # what the four bottom switches would overlap if fitted (the board must not have them)
    allhw = hw._solids_all()
    rep['DNP: a fitted bottom switch would overlap (mm3)'] = {
        r: {'tub': round(allhw[r].intersect(T).Volume(), 3), 'lid': round(allhw[r].intersect(L).Volume(), 3)} for r in hw.BOTTOM_SWITCHES}
    rep['checks'] = ok
    (OUT / 'chin.json').write_text(json.dumps(rep, indent=1))
    for k, v in rep.items():
        if k != 'checks':
            print(f'  {k}: {v}', flush=True)
    for k, v in ok.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}", flush=True)
    print(f'  ({time.time() - t0:.0f}s) -> out/{OUT.name}/chin.json', flush=True)
    assert all(ok.values()), f'chin_check: {[k for k, v in ok.items() if not v]}'
    return rep


def header_closed_check(shapes):
    """nodev (J6 not fitted): the top wall closed where the header's opening was, in the tub and in the lid, and the
    top tongue completed.
      stations   the tub's and the lid's YZ sections over the top wall (y >= TOP_IN - 1.2) at three X stations across
                 the old opening, each equal in area to its mirror station on the left (the proven top-left half:
                 wall, tongue, the lid's leg and lip)
      solid      the tub's top wall over the old opening's span, and the lid's, solid
      runs       two top runs: TONGUE_RUNS' left one and its mirror
      J6         not in the hardware model; what a fitted J6 would overlap is reported (the board must not have it)
    -> out/<build>/header.json. Asserts."""
    import joint
    t0 = time.time()
    T, L = shapes['tub'].val(), shapes['lid'].val()
    j6 = hw._solids_all()['J6']
    jb = j6.BoundingBox()
    rep, ok = {}, {}
    xc = (P.X0 + P.X1) / 2
    crop = box(P.X0 - 1, P.X1 + 1, P.TOP_IN - 1.2, P.Y1 + 1, P.Z_BACK - 1, P.Z_FRONT + 1).val()
    st = {}
    for name, s in (('tub', T), ('lid', L)):
        c = s.intersect(crop)
        for x in (round((jb.xmin + jb.xmax) / 2, 3), 45.0, 57.0):
            a, b = _yz_face(c, x).Area(), _yz_face(c, 2 * xc - x).Area()
            st[f'{name} x {x} vs x {round(2 * xc - x, 3)}'] = [round(a, 4), round(b, 4)]
            ok[f'{name} section at x {x} = its mirror'] = abs(a - b) < 1e-3
    rep['sections over the top wall (mm2)'] = st
    sol = {'tub top wall over the old opening': (T, (jb.xmin - 0.25, jb.xmax + 0.25, P.TOP_IN + 0.05, P.Y1 - 0.05, P.SEAM + 0.45, 0.215)),
           'lid top wall over the old opening': (L, (jb.xmin - 0.25, jb.xmax + 0.25, P.Y1 - 1.2 + 0.05, P.Y1 - 0.2, -5.4, P.SEAM - 0.45))}
    for k, (s, b) in sol.items():
        rep[k] = _full(s, b)
        ok[k + ' solid'] = rep[k][2]
    r = joint.runs()['top']
    rep['top runs'] = r
    ok['top tongue: the left run and its mirror'] = r == [(1.3, 37.0), (43.4, 58.7)]
    ok['J6 not in the hardware model'] = 'J6' not in hw.solids()
    rep['a fitted J6 would overlap (mm3)'] = {'tub': round(j6.intersect(T).Volume(), 3), 'lid': round(j6.intersect(L).Volume(), 3)}
    rep['checks'] = ok
    (OUT / 'header.json').write_text(json.dumps(rep, indent=1))
    for k, v in rep.items():
        if k != 'checks':
            print(f'  {k}: {v}', flush=True)
    for k, v in ok.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}", flush=True)
    print(f'  ({time.time() - t0:.0f}s) -> out/{OUT.name}/header.json', flush=True)
    assert all(ok.values()), f'header_closed_check: {[k for k, v in ok.items() if not v]}'
    return rep


# ---- side-key layouts: a left-out key is the plain wall (sides_check) ------------------------------------------------
SIDE_ZCAP = P.TAB_Z[1] + P.TAB_SLOT_CLR + 0.1          # 0.9: over the keys' slots (0.8), under the latch pockets (> 0.9)
SIDE_PLAIN_Y = {-1: 32.0, +1: 29.0}                     # a plain wall section: no key, latch, port or reset hole


def side_zone(t, margin=1.0):
    """Everything one side key (body.side_tabs) changes, as a box: the lid's cut (root to the free end's slot and its
    foot chamfer), the tub's slot (with its 'away' sign, as tub.key_cuts) and nub window, the tongue's and the groove's
    break (joint.nub_windows), the pad outside and the nub inside (body.tab_span_y); from below the lid's back to over
    the slot (SIDE_ZCAP)."""
    y0, y1 = body.tab_span_y(t)
    xs = (P.POCKET_X1 - 2.0, P.X1 + 3.0) if t['side'] > 0 else (P.X0 - 3.0, P.POCKET_X0 + 2.0)
    return (xs[0], xs[1], y0 - margin, y1 + margin, P.Z_BACK - 1.0, SIDE_ZCAP)


def _faces(s):
    """Face signatures: (surface type, area, centre) of every face, sorted."""
    return sorted((f.geomType(), round(f.Area(), 4), *(round(v, 3) for v in f.Center().toTuple())) for f in s.Faces())


def same_faces(a, b, tol=2e-3):
    """Whether shapes a and b are the same, by their faces (_faces: matched exactly, the rest within tol, for a value on
    a rounding boundary): {'faces': [a, b], 'only_a': [...], 'only_b': [...]}. OCC's exact or fuzzy cut of two identical
    shapes can come back as the whole shape (variants CHECK_geometry G3, G6), so 'unchanged' is never read off a
    boolean."""
    from collections import Counter
    sa, sb = _faces(a), _faces(b)
    ca, cb = Counter(sa), Counter(sb)
    oa, ob = list((ca - cb).elements()), list((cb - ca).elements())
    for f in list(oa):
        m = next((g for g in ob if g[0] == f[0] and all(abs(x - y) <= tol for x, y in zip(f[1:], g[1:]))), None)
        if m is not None:
            oa.remove(f)
            ob.remove(m)
    return {'faces': [len(sa), len(sb)], 'only_a': oa[:8], 'only_b': ob[:8], 'same': not oa and not ob}


def _wall_band(side, y0, y1):
    """A side wall from 0.5 outside the case's face to the cavity's face (POCKET_X: the lid's lip and the latch arms
    are inside it), up to SIDE_ZCAP."""
    x = (P.X0 - 0.5, P.POCKET_X0) if side < 0 else (P.POCKET_X1, P.X1 + 0.5)
    return box(x[0], x[1], y0, y1, P.Z_BACK - 1.0, SIDE_ZCAP).val()


def plain_wall(shape, side, y0, y1, step=0.5):
    """shape's wall band (_wall_band) over y0..y1 against the plain wall: the band's section at SIDE_PLAIN_Y extruded
    over y0..y1. Two ways: the cut both ways (each must be empty), and the section's area every `step` (each must be
    the plain one's). Pass: both, or, when the cut failed (it came back as a whole operand), the sections."""
    from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
    from OCP.gp import gp_Vec
    yr = SIDE_PLAIN_Y[side]
    slab = shape.intersect(_wall_band(side, yr - 0.5, yr + 0.5))
    faces = [f for f in slab.Faces() if f.geomType() == 'PLANE' and abs(f.normalAt().y) > 0.999
             and abs(f.Center().y - (yr - 0.5)) < 1e-6]
    area = sum(f.Area() for f in faces)
    pr = None
    for f in faces:
        p = cq.Shape.cast(BRepPrimAPI_MakePrism(f.moved(cq.Location(cq.Vector(0, y0 - (yr - 0.5), 0))).wrapped,
                                                gp_Vec(0, y1 - y0, 0)).Shape())
        pr = p if pr is None else pr.fuse(p)
    seg = shape.intersect(_wall_band(side, y0, y1))
    vs, vp = seg.Volume(), pr.Volume()
    try:
        d = [seg.cut(pr).Volume(), pr.cut(seg).Volume()]
    except Exception:
        d = [float('nan')] * 2
    whole = any(not (v < 0.5 * min(vs, vp)) for v in d)        # a cut that failed (or found a whole wall missing)
    prof, y = [], y0 + step / 2
    while y < y1:
        a = seg.intersect(_wall_band(side, y - 0.01, y + 0.01)).Volume() / 0.02
        if abs(a - area) > 1e-3:
            prof.append([round(y, 2), round(a, 4)])
        y += step
    cut_ok = max(d) < 1e-3
    return {'y': [round(y0, 3), round(y1, 3)], 'plain_section_y': yr, 'plain_section_mm2': round(area, 4),
            'mm3': [round(vs, 4), round(vp, 4)], 'cut_both_ways_mm3': [round(v, 5) for v in d],
            'sections_off_plain (y, mm2)': prof,
            'ok': not prof and (cut_ok or (whole and abs(vs - vp) < 1e-3)), 'by': 'cut and sections' if cut_ok else 'sections'}


def _switch_parts(r):
    """A side switch (hw.solids) split into its plunger (the nub that stands proud of the body, 1.24 deep) and body."""
    sw = hw.solids()[r]
    sp = hw.switch_plunger(r)
    n, fx = sp['nub'], sp['face'][0]
    s = 1 if sp['axis'][0] > 0 else -1
    nb = cq.Solid.makeBox(1.26, n[3] - n[2] + 0.02, n[5] - n[4] + 0.02, cq.Vector(min(fx, fx - s * 1.24) - 0.01, n[2] - 0.01, n[4] - 0.01))
    return sw, sw.intersect(nb), sw.cut(nb), s, sp


def sides_check(shapes):
    """A side-key layout (variants: leftkeys, rightkeys, upperkeys): every key the layout leaves out is the plain wall,
    in the tub and in the lid, and nothing else changed (the boxes of the keys left out: body.side_tabs(TAB_ROOTS_ALL),
    side_zone). Its switch may stay fitted (hw keeps it), so the closed wall must keep off it.
      closed     the tub's slot solid (tub.key_cuts' box, with its 'away' sign, within the wall, over the seam's V) and
                 the sliver solid over the nub window (body.tab_window); the tongue one run across the window (joint
                 .runs), its volume the profile's area x the length; the tub's and the lid body's wall over the zone =
                 the plain wall (plain_wall: its section at SIDE_PLAIN_Y extruded; the lid's cut leaves room by the
                 groove, the seam's V and the leg's mouth that a solid box would call open, so it is compared with the
                 plain wall's, not with a box)
      unchanged  the tub and the printed lid (their STEPs) outside the zones = the all-keys twin's (variants.twin(BUILD,
                 'sides'), read through pipeline.py's cross_reads), by their faces (same_faces, never a boolean); inside
                 them the tub only gains (twin minus this 0, and the volumes add up). The printed lid inside the zones is
                 not compared with the twin's: the twin's has the keys there. The twin's tub.step and lid.step must be
                 there: when they are not, these FAIL; they are never skipped
      no key     no skey_<ref> part or file for a key left out; the printed lid = the lid body + the kept keys (by
                 volume, one solid), and = the lid body inside the zones
      switch     each left-out key's switch, fitted: its plunger >= SIDE_SHUT_GAP_MIN from the tub, and >=
                 SIDE_SHUT_WORST_MIN with the board SIDE_SHUT_SHIFT toward that wall and the face SIDE_SHUT_GROWTH
                 proud; the switch (body and plunger) >= SIDE_SHUT_LID_MIN from the lid; no overlap. And at every
                 side switch (kept or not) the lid's lip ducks: nothing of the lid body over its body's span +
                 joint.SW_CLR above SW_LIP_TOP (joint.switch_spans)
    -> out/<build>/sides.json. Asserts. Run only for a layout that leaves keys out."""
    import joint
    t0 = time.time()
    T, L = shapes['tub'].val(), shapes['lid'].val()            # the tub and the lid's body (build_all: no keys)
    tabs = {t['ref']: t for t in body.side_tabs(P.TAB_ROOTS_ALL)}
    gone = [r for r in P.TAB_ROOTS_ALL if r not in P.TAB_ROOTS]
    kept = list(P.TAB_ROOTS)
    rep, ok = {'layout': P.SIDES, 'keys': kept, 'left out': gone}, {}
    zones = {r: side_zone(tabs[r]) for r in gone}
    rep['zones'] = {r: [round(v, 3) for v in z] for r, z in zones.items()}
    Z = None
    for z in zones.values():
        Z = box(*z).val() if Z is None else Z.fuse(box(*z).val())
    J = P.JOINT
    area = J['t'] * J['h'] - J['lead'] ** 2
    runs = joint.runs()
    # closed: the tub's slot and window, the tongue, and the wall (tub and lid body) = the plain wall
    for r in gone:
        t = tabs[r]
        s, a = t['side'], t['away']
        wall = 'right' if s > 0 else 'left'
        xo, face = (P.X1, P.POCKET_X1) if s > 0 else (P.X0, P.POCKET_X0)
        row = {'side': wall}
        ys = sorted((t['y_block'] - a * P.TAB_ROOT_CLR, t['y_free'] + a * P.TAB_END_CLR))
        xs = sorted((t['stop'], xo))
        row['slot solid'] = _full(T, (xs[0], xs[1], ys[0], ys[1], P.SEAM + P.SEAM_CHAMFER + 0.05, P.TAB_Z[1] + P.TAB_SLOT_CLR))
        w = body.tab_window(t)
        xs = sorted((face, t['stop']))
        row['sliver solid over the nub window'] = _full(T, (xs[0], xs[1], w['y'][0], w['y'][1], P.SEAM + 0.02, w['top']))
        wy = (w['y'][0] - 0.1, w['y'][1] + 0.1)
        one = [list(g) for g in runs[wall] if g[0] <= wy[0] and g[1] >= wy[1]]
        tb = (face - 0.3, face + 1.5) if s > 0 else (face - 1.5, face + 0.3)
        tv = T.intersect(box(tb[0], tb[1], wy[0], wy[1], P.SEAM - 2.0, P.SEAM).val()).Volume()
        row['tongue across the window'] = {'run': one, 'mm3': round(tv, 4), 'expected_mm3': round(area * (wy[1] - wy[0]), 4)}
        ok[f'{r}: tub slot closed'] = row['slot solid'][2]
        ok[f'{r}: sliver closed over the nub window'] = row['sliver solid over the nub window'][2]
        ok[f'{r}: tongue unbroken across the nub window'] = bool(one) and abs(tv - area * (wy[1] - wy[0])) < 1e-3
        _, _, y0, y1, _, _ = side_zone(t, margin=0.5)
        for n, sh in (('tub', T), ('lid body', L)):
            row[f'{n} wall = the plain wall'] = pw = plain_wall(sh, s, y0, y1)
            ok[f'{r}: {n} wall over the key = the plain wall'] = pw['ok']
        rep[r] = row
    # unchanged: the tub and the printed lid against the all-keys twin's
    twin = variants.twin(P.BUILD, 'sides')
    tw = hw.ROOT / 'out' / twin
    for n in ('tub', 'lid'):
        k = f'{n} outside the left-out keys = the {twin} {n}'
        mine, theirs = OUT / f'{n}.step', tw / f'{n}.step'
        if not (mine.exists() and theirs.exists()):
            rep[k] = f'NOT BUILT: out/{twin}/{n}.step (the all-keys twin; pipeline.py brings it into the run)' \
                if mine.exists() else f'NOT BUILT: out/{OUT.name}/{n}.step'
            ok[k] = False
            if n == 'tub':
                ok['tub inside the zones only gains (vs the twin)'] = False
            continue
        A, B = cq.importers.importStep(str(mine)).val(), cq.importers.importStep(str(theirs)).val()
        sf = same_faces(A.cut(Z), B.cut(Z))
        rep[k] = sf
        ok[k] = sf['same']
        if n == 'tub':
            ai, bi = A.intersect(Z), B.intersect(Z)
            lost, gained = bi.cut(ai).Volume(), ai.cut(bi).Volume()
            rep['tub inside the zones vs the twin (mm3)'] = {'this': round(ai.Volume(), 4), 'twin': round(bi.Volume(), 4),
                                                            'twin minus this': round(lost, 5), 'this minus twin': round(gained, 4)}
            ok['tub inside the zones only gains (vs the twin)'] = lost < 1e-3 and abs(ai.Volume() - bi.Volume() - gained + lost) < 1e-3
    # no key, no file; the printed lid = the body + the kept keys
    for r in gone:
        ok[f'{r}: no key (no skey_{r} part or file)'] = f'skey_{r}' not in shapes and not (OUT / f'skey_{r}.stl').exists()
    lid_p = PRINTED_LID[0]                                      # as build_all built it (its STEP rounds the volume)
    Lp = lid_p.val()
    kv = sum(shapes[f'skey_{r}'].val().Volume() for r in kept)
    gap = Lp.Volume() - L.Volume() - kv
    inz = Lp.intersect(Z).Volume() - L.intersect(Z).Volume()
    rep['printed lid = lid body + kept keys (mm3)'] = {'lid': round(Lp.Volume(), 4), 'body': round(L.Volume(), 4),
                                                       'keys': round(kv, 4), 'gap': round(gap, 5),
                                                       'solids': len(lid_p.solids().vals()), 'in the zones, lid - body': round(inz, 5)}
    ok['printed lid = lid body + the kept keys, one solid'] = abs(gap) < 1e-3 and len(lid_p.solids().vals()) == 1
    ok['printed lid = lid body over the left-out keys'] = abs(inz) < 1e-3
    # the switches: a left-out key's, fitted, never pressed; the lip ducks under every one
    hws = hw.solids()
    sw_rep = {}
    for r in [*hw.LEFT_SWITCHES, *hw.RIGHT_SWITCHES]:
        if r not in hws:
            ok[f'{r} in the hardware model (every side switch stays fitted)'] = False
            continue
        sw, plunger, sbody, s, sp = _switch_parts(r)
        b = sp['body']
        y0, y1 = b[2] - joint.SW_CLR, b[3] + joint.SW_CLR
        face = P.POCKET_X1 if s > 0 else P.POCKET_X0
        lx = sorted((face - s * (J['clr'] + 0.05), face - s * (J['clr'] + J['lip'] - 0.05)))
        lip = _empty(L, (lx[0], lx[1], y0 + 0.05, y1 - 0.05, joint.SW_LIP_TOP + 0.05, P.SEAM - 0.05))
        row = {'kept': r not in gone, 'lid lip over the body span (mm3)': lip[0]}
        ok[f'{r}: the lid lip ducks under the switch'] = lip[1]
        if r in gone:
            crop = box(-8.0 if s < 0 else 52.0, 8.0 if s < 0 else 68.0, b[2] - 6.0, b[3] + 6.0, P.Z_BACK - 1.0, P.Z_FRONT + 1.0).val()
            tc, lc = T.intersect(crop), L.intersect(crop)
            nom = plunger.distance(tc)
            worst = plunger.moved(cq.Location(cq.Vector(s * P.SIDE_SHUT_SHIFT, 0, 0))).distance(tc) - P.SIDE_SHUT_GROWTH
            row.update({'plunger to tub': round(nom, 4), 'plunger to tub, worst': round(worst, 4),
                        'switch to lid': round(sw.distance(lc), 4), 'plunger to lid': round(plunger.distance(lc), 4),
                        'body to lid': round(sbody.distance(lc), 4),
                        'body to tub': round(sbody.distance(tc), 4),
                        'overlap mm3': [round(sw.intersect(tc).Volume(), 5), round(sw.intersect(lc).Volume(), 5)]})
            ok[f'{r}: plunger >= {P.SIDE_SHUT_GAP_MIN} from the closed wall'] = nom >= P.SIDE_SHUT_GAP_MIN
            ok[f'{r}: plunger >= {P.SIDE_SHUT_WORST_MIN} from it at the worst shift and print'] = worst >= P.SIDE_SHUT_WORST_MIN
            ok[f'{r}: switch >= {P.SIDE_SHUT_LID_MIN} from the lid'] = row['switch to lid'] >= P.SIDE_SHUT_LID_MIN
            ok[f'{r}: no overlap with the tub or the lid'] = max(row['overlap mm3']) < 1e-3
        sw_rep[r] = row
    rep['switches (every side switch fitted)'] = sw_rep
    rep['tongue runs'] = {w: [[round(a, 2), round(b, 2)] for a, b in g] for w, g in runs.items() if w != 'top'}
    rep['lip ducks'] = {w: [[round(a, 2), round(b, 2)] for a, b in joint.switch_spans(w)] for w in ('left', 'right')}
    rep['checks'] = ok
    (OUT / 'sides.json').write_text(json.dumps(rep, indent=1, default=str))
    for k, v in rep.items():
        if k not in ('checks', *gone):
            print(f'  {k}: {v}', flush=True)
    for r in gone:
        print(f'  {r}: ' + json.dumps(rep[r]), flush=True)
    for k, v in ok.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}", flush=True)
    print(f'  ({time.time() - t0:.0f}s) -> out/{OUT.name}/sides.json', flush=True)
    assert all(ok.values()), f'sides_check: {[k for k, v in ok.items() if not v]}'
    return rep


def build_variants(argv):
    """The print builds (params.PRINT_BUILDS), one process each, side by side, each logged to out/<build>/build.log;
    then the shared-part check and print/4.26/ (finish). With --only a,b: just those builds (any slugs), then each
    one's share check; print/4.26/ is not written. The builds run through pipeline.py, so a build whose inputs have
    not changed since a run that is in the cache is restored from it instead of rebuilt (--no-cache: rebuild)."""
    import pipeline
    only = None
    if '--only' in argv:
        i = argv.index('--only')
        only = [b for b in argv[i + 1].split(',') if b]
        argv = argv[:i] + argv[i + 2:]
    builds = only or list(P.PRINT_BUILDS)
    for b in builds:
        P.parse_build(b)
    flags = [a for a in argv if a in ('--no-cache', '--rehash', '--why')]
    rest = [a for a in argv if a not in flags]
    pipeline.main([*flags, '--builds', ','.join(builds), '--steps', 'build', '--finish', 'only' if only else 'default',
                   *(['--', *rest] if rest else [])])


def finish(builds, only):
    """What build_variants does after its builds (pipeline.py's 'finish' step, a process of its own): with only, each
    build's share checks; else the shared-part check, the share checks, print/4.26/ and the cross-project check.
    The share checks: each build against the twin it derives from (out/<build>/shared.json), then against every twin
    (out/shares-all.json)."""
    for b in builds:
        P.parse_build(b)
    hw.solids()
    if only:
        for b in builds:
            share_check(b)
        twin_shares(builds)
        print(f'--only {",".join(builds)}: print/4.26/ not written', flush=True)
        return
    shared_parts_check()
    for b in builds:                                    # each against the twin it derives from (out/<build>/shared.json)
        share_check(b)
    twin_shares(builds)
    write_print(builds)
    t0 = time.time()
    xp = cross_project_check()                          # last: it needs case-368 built with the same crank code
    if xp['built']:
        print(f"cranks, this project vs case-368 ({time.time() - t0:.0f}s): the same: "
              + '; '.join(f"{n} {r['mm3']} mm3, bounds {r['bounds_max_diff']}, sections <= {max(r['section_symdiff_mm2'].values())} mm2"
                          for n, r in xp['parts'].items()), flush=True)


# The checks a build runs after build_all, by name: every one, unless SILKSCREEN_CHECKS (pipeline.py --quick) names
# the ones to run (a quick iteration: the parts are the same, the checks' numbers can differ in their last digit,
# since a check sees what the skipped ones did to the shapes; pipeline.py marks such a build quick).
CHECKS = ('insertion', 'moves', 'lid_close', 'interference', 'bottom_keys', 'strip', 'chin', 'header', 'sides')


def _want(check):
    w = os.environ.get('SILKSCREEN_CHECKS')
    return w is None or check in w.split(',')


def _shared_from(check):
    """pipeline.py (SILKSCREEN_SHARE_ASK): the build whose report of this check this build takes, because its share
    guard (guard.py) reads the same inputs, or None: run it here. The pipeline copies that build's report into
    out/<build>/ once both have ended. Leaving bottom_keys or strip out changes no other check's output (every file of
    four build children compared, speed2). Outside the pipeline, or with no answer in 120 s, every check runs."""
    pre = os.environ.get('SILKSCREEN_SHARE_ASK')
    if not pre:
        return None
    ask, ans = Path(f'{pre}.{check}.ask'), Path(f'{pre}.{check}.answer')
    ask.write_text('ask\n')
    t0 = time.time()
    while not ans.exists():
        if time.time() - t0 > 120:
            return None
        time.sleep(0.2)
    a = ans.read_text().split()
    return a[1] if len(a) == 2 and a[0] == 'share' else None


def build_variant():
    print(f'variant: {P.BUILD} -> {OUT}', flush=True)
    shapes = build_all()
    if os.environ.get('SILKSCREEN_PHASE1'):             # pipeline.py: every part is written; the checks only add JSON
        Path(os.environ['SILKSCREEN_PHASE1']).write_text('build_all done\n')
        if os.environ.get('SILKSCREEN_CHECKS') == 'auto':   # --quick: pipeline.py names the checks once it has the parts
            f = Path(os.environ['SILKSCREEN_PHASE1'] + '.checks')
            while not f.exists():
                time.sleep(0.2)
            os.environ['SILKSCREEN_CHECKS'] = f.read_text().strip()
            print(f"quick: checks {os.environ['SILKSCREEN_CHECKS'] or 'none'}", flush=True)
    if _want('insertion') or _want('moves'):
        ins = insertion_check(shapes) if _want('insertion') else {}
        print('\ninsertion path (panel at its largest, midplate), from the back into the face-down tub:')
        for k, v in ins.items():
            if not k.startswith('_'):
                print(f"  {k:14s} x {v['path_x']} y {v['path_y']} -> {'clear' if not v['hits'] else v['hits']}")
        if '_across' in ins:
            print('the stack across the pocket (the largest glass; strip at the ends and middle of its placement):')
            for k, v in ins['_across'].items():
                print(f"  {k:44s} bar x0 {v['bar_x0']:+.3f}: bar {v['bar_gap']} / glass {v['glass_gap']} from the left wall"
                      f" -> {'clear' if v['clear'] else (v['hits'] or 'touching')}")
        t0 = time.time()
        if _want('moves'):
            lm = later_moves(shapes)
            ins['_later'] = lm
        (OUT / 'insertion.json').write_text(json.dumps(ins, indent=1))
        if _want('moves'):
            print(f"PCBA in (J1, side switches, SW11, board past the bay): {lm['pcba_in'] or 'clear'}\n"
                  f"lid on (with its side keys): {lm['lid_on'] or 'clear'}  ({time.time() - t0:.0f}s)")
    if _want('lid_close'):                              # the lid closing: the latch arms as the tongue bends them on
        import lid_close                                # the way in (2026-10-12: later_moves moves them unbent)
        t0 = time.time()
        lc = lid_close.run(*(lid_close.mesh_of(shapes[k].val()) for k in ('lid', 'tub', 'midplate')))
        (OUT / 'lid-close.json').write_text(json.dumps(lc, indent=1))
        print('\n' + lid_close.summary(lc) + f'  ({time.time() - t0:.0f}s)', flush=True)
    if '--no-check' not in sys.argv:
        t0 = time.time()
        if _want('interference'):
            rep = interference(shapes)
            rep += mesh_interference()
            (OUT / 'interference.json').write_text(json.dumps(rep, indent=1))
            print(f'\n{len(rep)} interferences ({time.time() - t0:.0f}s):')
            for r in rep:
                print(f"  {r['part']:10s} x {r['with']:14s} {r['volume']:9.4f} mm3 at {r['where']}"
                      f"{'  (expected)' if r.get('expected') else ''}")
        t0 = time.time()
        if P.BOTTOM_KEYS and _want('bottom_keys'):
            src = _shared_from('bottom_keys')
            if src:
                print(f'\nbottom keys: the same inputs as {src} (its share guard): pipeline.py copies its bottom-keys.json',
                      flush=True)
            else:
                print('\nbottom keys (crank spec section 8):', flush=True)
                bk = bottom_keys_check(shapes)
                print(bottom_keys_summary(bk), flush=True)
        src = _shared_from('strip') if P.LIGHT_STRIP and _want('strip') else None
        if src:
            print(f'\nlight strip: the same inputs as {src} (its share guard): pipeline.py copies its light-strip.json',
                  flush=True)
        elif P.LIGHT_STRIP and _want('strip'):
            t0 = time.time()
            sc = strip_check(shapes)
            (OUT / 'light-strip.json').write_text(json.dumps(sc, indent=1))
            print(f'\nlight strip ({time.time() - t0:.0f}s):')
            print('  sweep worst: ' + ', '.join(f'{k} {v}' for k, v in sc['sweep'].items() if k != 'rows'))
            for case, r in sc['tail'].items():          # nearest first
                for part in ('strip_tail', 'strip_diodes'):
                    print(f"  {case} {part}: " + ', '.join(f"{o} {v['gap']}" for o, v in list(r[part].items())[:6]))
    # the gated-off features, positively absent (also with --no-check: they are quick)
    if not P.BOTTOM_KEYS and _want('chin'):
        print('\nno bottom keys (chin_check):', flush=True)
        chin_check(shapes)
    if not P.DEV_HEADER and _want('header'):
        print('\nno dev header (header_closed_check):', flush=True)
        header_closed_check(shapes)
    if P.SIDES != 'all' and _want('sides'):
        print(f'\nside keys left out ({P.SIDES}; sides_check):', flush=True)
        sides_check(shapes)
    if '--no-share' not in sys.argv:
        share_check()


if __name__ == '__main__':
    if '--bottom-keys' in sys.argv:              # the bottom keys' checks alone, on out/<build>/ as built
        print(bottom_keys_summary(bottom_keys_check()))
    elif '--shares' in sys.argv:                 # the share check alone, on out/<build>/ as built
        share_check()
    elif '--finish' in sys.argv:                 # pipeline.py: after the builds (build_variants' second half)
        i = sys.argv.index('--finish')
        finish([b for b in sys.argv[i + 1].split(',') if b], '--only' in sys.argv)
    elif 'SILKSCREEN_VARIANT' in os.environ:
        build_variant()
    else:
        build_variants(sys.argv[1:])
