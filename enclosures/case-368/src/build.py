"""Build every part of both builds, export STL + STEP to out/standard/ and out/light-strip/, run each build's
interference and assembly-path checks (with the bottom keys' crank checks, crank_checks.py), assert that every part but
the tub and the bottom keys is the same in both, write the repo's print/3.68/ (write_print), and last assert that the
cranks are case-426's (cross_project_check; skipped with a warning if case-426 is not built).

Run from this project's folder (enclosures/case-368) with a Python 3.11 virtual environment made from requirements.txt (README.md, "Rebuilding"):

    python -B src/build.py            # both builds + checks, the shared-part assert, print/3.68/
    python -B src/build.py --no-check
    $env:SILKSCREEN_VARIANT = 'standard'; python -B src/build.py    # one build only (variant.py)

Standard is x3's case (its checks as x3 ran them); light-strip adds the strip's checks (strip_insertion,
strip_interference). With SILKSCREEN_VARIANT set, only that build runs, with no assert and no print/3.68/.
"""
import json, os, re, shutil, subprocess, sys, time
from pathlib import Path
import cadquery as cq
import hw
import params as P
import variant
import tub, lid, midplate, keys, refs, sidekeys, body, crank
from geom import box

OUT = hw.OUT

PARTS = {                       # id: (builder, colour, material note) - the printed parts
    'tub': (tub.build, '#e8e1d0', 'PLA'),
    'lid': (lid.build, '#d9d0bc', 'PLA'),          # Rev J: with the side keys, which are part of it
    'midplate': (midplate.build, '#6f7a70', 'PLA'),
    **{f'key_{r}': ((lambda r=r: keys.build(r)), c, 'PLA') for r, c in
       zip(P.KEY_REFS, ['#c8553d', '#3d3f45', '#3d3f45', '#3d3f45'])},
    # the bottom keys' cranks as fitted: crank-M, the board STEP's switches being the MJTP1117 (crank_checks.py puts
    # crank-T with the TS365ZJ's envelope)
    **{f'crank_{r}': ((lambda r=r: crank.build('M', keys.centre(r))), '#8a8f96', 'PLA') for r in P.KEY_REFS},
    'gate': (crank.gate, '#5a7fa8', 'PLA'),         # the rod's left stop (SPEC2 rev 3), installed in the -X wall's slot
}
# Printed once per build at the origin of their own frame (dx from the key's centre): the key (tub-specific) and the
# two cranks. The hook keys' optional fit check (coupon-strip, tub.coupon: SW9's opening with its two slots; test 2,
# 2026-09-30: the drag coupon's four keys went with the drag) and the gate's proof coupon (coupon-gate,
# tub.gate_coupon) are cut from the built tub in the CAD frame.
CRANKS = ['crank-M', 'crank-T']
# The side keys move, so every check (and the showcase) takes the lid apart into its fixed body and the
# keys: lid_body.stl and skey_*.stl. They meet only on each key's root face, so the pair shows no
# overlap, and lid_body + the keys is the printed lid.
SIDE_KEYS = [f'skey_{r}' for r in P.TAB_ROOTS]
# Ian's rule: a light-strip owner prints one extra part, so every printed part but the tub is the same in both builds
# (shared_check asserts it), and the lid's split bodies as well. The crank keys (2026-09-26) stand a fixed height over
# their own tub's face, so the bottom keys are tub-specific too: a light-strip owner prints the tub and four keys.
TUB_SPECIFIC = ['tub', *(f'key_{r}' for r in P.KEY_REFS)]
SHARED = [p for p in PARTS if p not in TUB_SPECIFIC] + CRANKS
PRINT_DIR = hw.ROOT.parents[1] / 'print' / '3.68'    # committed, at the repo root (write_print)


def build_all():
    shapes = {}
    for pid, (fn, _, _) in PARTS.items():
        t0 = time.time()
        wp = fn()
        n = len(wp.solids().vals())
        shapes[pid] = wp
        cq.exporters.export(wp, str(OUT / f'{pid}.stl'), tolerance=0.02, angularTolerance=0.1)
        cq.exporters.export(wp, str(OUT / f'{pid}.step'))
        print(f'{pid:10s} solids={n} vol={wp.val().Volume():8.1f} mm3  {time.time() - t0:5.1f}s', flush=True)
        if n != 1:
            print(f'  WARNING: {pid} is {n} separate solids', flush=True)
    printed_lid = shapes['lid']
    shapes['lid'] = lid.build(keys=False)
    cq.exporters.export(shapes['lid'], str(OUT / 'lid_body.stl'), tolerance=0.02, angularTolerance=0.1)
    for r in P.TAB_ROOTS:
        shapes[f'skey_{r}'] = sidekeys.build(r)
        cq.exporters.export(shapes[f'skey_{r}'], str(OUT / f'skey_{r}.stl'), tolerance=0.02, angularTolerance=0.1)
    gap = printed_lid.val().Volume() - shapes['lid'].val().Volume() - sum(shapes[k].val().Volume() for k in SIDE_KEYS)
    print(f'lid = body + keys to {gap:+.4f} mm3 ({len(printed_lid.solids().vals())} solid)', flush=True)
    for name, wp in (('ref_display', refs.display()), ('ref_battery', refs.battery())):
        cq.exporters.export(wp, str(OUT / f'{name}.stl'), tolerance=0.02)
    if P.LIGHT_STRIP:
        for name, wp in refs.strip().items():               # light strip, as fitted (relaxed fold, loop on the back)
            cq.exporters.export(wp, str(OUT / f'ref_{name}.stl'), tolerance=0.01)
    # the parts to print once (their own frame); the rod as a reference (no screw since SPEC2 rev 3: the gate, a PART)
    single = {keys.NAME: keys.build(), **{c: crank.build(c[-1]) for c in CRANKS},
              'coupon-strip': tub.coupon(shapes['tub']), 'coupon-gate': tub.gate_coupon(shapes['tub'])}
    for name, wp in single.items():
        cq.exporters.export(wp, str(OUT / f'{name}.stl'), tolerance=0.01, angularTolerance=0.1)
        cq.exporters.export(wp, str(OUT / f'{name}.step'))
        n = len(wp.solids().vals())
        print(f'{name:16s} solids={n} vol={wp.val().Volume():8.2f} mm3', flush=True)
        if n != 1:
            print(f'  WARNING: {name} is {n} separate solids', flush=True)
    cq.exporters.export(crank.rod(), str(OUT / 'ref_rod.stl'), tolerance=0.01)
    (OUT / 'ref_screw.stl').unlink(missing_ok=True)          # the M2.5 side screw's, gone with it
    return shapes


def interference(shapes, min_vol=1e-3):
    """Every printed part against every hardware solid, the display and the battery envelope,
    and every part against every other part, in the assembled position."""
    hwsol = hw.solids()
    others = {'display': refs.display().val(), 'battery': refs.battery().val(),
              'display_thick': refs.display(thickness=hw.PANEL_T + hw.PANEL_T_TOL).val(),
              'display_thin': refs.display(thickness=hw.PANEL_T - hw.PANEL_T_TOL).val()}
    rep = []
    shapes = {k: v for k, v in shapes.items() if k != 'tub_noribs'}
    shapes = {**shapes, 'rod': crank.rod()}
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
                rep.append({'part': pid, 'with': ref, 'volume': round(v, 4),
                            'where': [round(x, 2) for x in (ib.xmin, ib.xmax, ib.ymin, ib.ymax, ib.zmin, ib.zmax)]})
    ids = list(shapes)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            v = shapes[a].val().intersect(shapes[b].val()).Volume()
            if v > min_vol:
                ib = shapes[a].val().intersect(shapes[b].val()).BoundingBox()
                rep.append({'part': a, 'with': b, 'volume': round(v, 4), 'expected': _designed(a, b, ib, v),
                            'where': [round(x, 2) for x in (ib.xmin, ib.xmax, ib.ymin, ib.ymax, ib.zmin, ib.zmax)]})
    return rep


def _designed(a, b, ib, v=0.0):
    """Designed overlaps between the parts as fitted. One (2026-10-13): the lid's latch barbs in their pockets. The
    barbs are drawn params.LATCH_PHASE (one layer) under the pockets' catch, so that they meet at the lid's as-printed
    home, params.LID_HOME_DZ forward of its CAD position; at the CAD position, which the lid never reaches, each barb's
    45-degree face stands 0.1 into its pocket's: about 0.25 mm3 a latch, all of it between the barb's lowest point and
    its flat. slice_check reads the latches back as printed (asprinted.latch: they meet, they do not overlap).
    (The keys' drag bump in the chin wall went with the hook keys, test 2, 2026-09-30; the side screw's thread in its
    hole with the screw, SPEC2 rev 3.)"""
    if {a, b} == {'lid', 'tub'} and P.LATCH_PHASE < 0:
        import joint
        _, h = joint.snap_profile()
        n = sum(len(c) for c in P.SNAPS.values())
        return (ib.zmin >= h['catch_low'] - 0.01 and ib.zmax <= h['z_c'] - P.LATCH_PHASE / 2 + 0.01
                and v <= 0.3 * n)
    return False


EXPECTED_CONTACTS = [('tub', 'gate')]     # designed touches of zero volume: the gate seated on its floor and its
                                          # flange's outer face on the lips' faces (SPEC2 rev 3, check 1)


def contacts(shapes, min_vol=1e-3, tol=1e-3):
    """The designed zero-volume touches (EXPECTED_CONTACTS): each pair's overlap (<= min_vol, so interference() lists
    none) and distance (0: they touch). For the gate, where it touches: its section outlines (plan at z -3.0 / -1.0 /
    0.6, XZ at nine y across it) sampled every 0.005 against the tub's sections; every point within tol of the tub must
    lie on the slot's floor plane (tub.floor_z) or on the lips' faces (X GATE_SLOT_X[1]). Its clearances to the rest of
    the slot (0.10 to the mouth, 0.15 to the cavity) are crank_checks.gate_path's."""
    import crank_checks as CC
    from shapely.geometry import Point
    out = []
    xl = P.GATE_SLOT_X[1]
    for a, b in EXPECTED_CONTACTS:
        sa, sb = shapes[a].val(), shapes[b].val()
        loc = sa.intersect(box(P.X0 - 1, 0.0, -7.0, 2.0, P.SEAM - 3, 4.0).val())
        v = loc.intersect(sb).Volume()
        row = {'pair': [a, b], 'mm3': round(v, 6), 'distance': round(loc.distance(sb), 4)}
        tm, gm = CC.to_mesh(loc), CC.to_mesh(sb)
        where = {'floor': 0, 'lips': 0, 'other': 0}
        others = []
        secs = [('xy', z, CC.section_xy) for z in (-3.0, -1.0, 0.6)] + [('xz', y, CC.section_xz) for y in
                (-4.15, -3.95, -3.7, -3.3, -2.5, -1.7, -1.3, -1.05, -0.85)]
        for kind, c, fn in secs:
            t, g = fn(tm, c), fn(gm, c)
            for poly in getattr(g, 'geoms', [g]):
                ring = poly.exterior
                for i in range(int(ring.length / 0.005) + 1):
                    q = ring.interpolate(i * 0.005)
                    if t.distance(q) > tol:
                        continue
                    if abs(q.x - xl) <= tol:
                        where['lips'] += 1
                    elif kind == 'xz' and q.x <= P.ROD_STOP_X0 + tol and abs(q.y - tub.floor_z(q.x)) <= 2 * tol:
                        where['floor'] += 1
                    else:
                        where['other'] += 1
                        others.append([kind, c, round(q.x, 3), round(q.y, 3)])
        row['touch_points'] = where
        row['touches_elsewhere'] = others[:10]
        row['ok'] = v <= min_vol and row['distance'] <= tol and where['floor'] > 0 and where['lips'] > 0 and not others
        out.append(row)
    return out


def insertion_check(shapes, min_vol=1e-3):
    """The assembly path, not just the assembled position: with the tub face down (keys already
    in), the panel and then the midplate go in from the back. Each layer of the panel, at the
    drawing's largest outline, and the midplate's outline are swept from beyond the parting plane
    to where they sit; anything of the tub or the keys inside that path would stop them.
    Rev E failed this (its walls below the pocket stood 1.2 mm inside the panel's edge).
    x3: the panel's pocket is narrower than the walls, so its path ends at the lip and the midplate's
    at the frame's rear face."""
    import panel
    tx, ty = hw.PANEL_W_TOL / 2, hw.PANEL_H_TOL / 2
    # light strip: the left corner stops (P.LOCATOR_X) push a max-width panel right of centre
    sx = max(0.0, P.LOCATOR_X - (hw.PANEL_X0 - tx)) if P.LIGHT_STRIP else 0.0
    paths = {}
    for name, layer in panel.body().items():
        b = layer.val().BoundingBox()
        paths[f'panel_{name}'] = box(b.xmin - tx + sx, b.xmax + tx + sx, b.ymin - ty, b.ymax + ty, P.SEAM - 1.0, b.zmax)
    b = shapes['midplate'].val().BoundingBox()
    # the plate's own outline: its four detent bumps ride into the wall by design (they flex; see
    # mechanics.mid_detents), so they are not part of the path
    paths['midplate'] = midplate.outline(P.SEAM - 1.0, b.zmax)
    rep = {}
    for pname, path in paths.items():
        hits = {}
        for pid, wp in shapes.items():
            if pid == 'tub' or pid.startswith(('key_', 'crank_')):
                inter = wp.val().intersect(path.val())
                v = inter.Volume()
                if v > min_vol:
                    ib = inter.BoundingBox()
                    hits[pid] = {'mm3': round(v, 4), 'where': [round(x, 2) for x in (ib.xmin, ib.xmax, ib.ymin, ib.ymax, ib.zmin, ib.zmax)]}
        pb = path.val().BoundingBox()
        rep[pname] = {'path_x': [round(pb.xmin, 3), round(pb.xmax, 3)], 'path_y': [round(pb.ymin, 3), round(pb.ymax, 3)],
                      'seated_top_z': round(pb.zmax, 3), 'hits': hits}
    return rep


def _sweep(m, f, n, step):
    worst = (0.0, None)
    for i in range(1, n + 1):
        v = m.moved(cq.Location(cq.Vector(0, 0, -i * step))).intersect(f).Volume()
        if v > worst[0]:
            worst = (v, round(i * step, 2))
    return worst


def later_moves(shapes, step=0.25, travel=10.0, min_vol=1e-3):
    """The parts that go in after the panel, moved along their way in (all from the back of the
    face-down tub, so along -Z from their seats):
      pcba_in  J1, SW11 and the side switches - the board's parts nearest the walls - against the
               tub, the keys and the midplate
      lid_on   the lid (Rev J: with its side keys) against the midplate and the board's edge parts, and
               each side key against the tub: the key's block slides up its slot and the nub up the
               sliver's window. The latch barbs ride up the tub's wall by design (they flex), so the
               lid body x tub pair is left out; the arms as they flex are lid_close.latch_arms' (2026-10-12: the
               rigid sweep missed them landing on the midplate)
    Reports the worst overlap on each path; the bottom switches are left out: crank_checks.board_in follows them
    past the cranks' noses."""
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
            worst = _sweep(m, f, n, step)
            if worst[0] > min_vol:
                rep['pcba_in'][f'{name} x {fname}'] = {'mm3': round(worst[0], 4), 'at_mm_below_seat': worst[1]}
    # the lid: its latch arms stand 7 mm tall, up past the board's edge and the midplate's, and its side
    # keys rise past the parting line into the tub
    # x3: the battery rides in the lid, so it goes on with it, past everything on the board's rear
    near = {r: hwsol[r] for r in ('PCB', 'J1', 'J5', 'J7', 'U3', 'U9', 'U4', 'U11', 'SW11', 'H2', *hw.LEFT_SWITCHES,
                                  *hw.RIGHT_SWITCHES) if r in hwsol}
    lid_s = shapes['lid'].val().fuse(refs.battery().val())
    for k in SIDE_KEYS:
        lid_s = lid_s.fuse(shapes[k].val())
    for fname, f in {'midplate': shapes['midplate'].val(), **near}.items():
        worst = _sweep(lid_s, f, n, step)
        if worst[0] > min_vol:
            rep['lid_on'][f'lid x {fname}'] = {'mm3': round(worst[0], 4), 'at_mm_below_seat': worst[1]}
    tub_s = shapes['tub'].val()
    for k in SIDE_KEYS:
        worst = _sweep(shapes[k].val(), tub_s, n, step)
        if worst[0] > min_vol:
            rep['lid_on'][f'{k} x tub'] = {'mm3': round(worst[0], 4), 'at_mm_below_seat': worst[1]}
    return rep


EXPECTED = {                    # contacts that are the design, not a clash
    ('ribbon_main', 'J2'), ('battery_plug', 'J5'), ('lead_red', 'battery_plug'), ('lead_black', 'battery_plug'),
    ('lead_red', 'battery_pcm'), ('lead_black', 'battery_pcm'),
    ('strip_tail', 'J3'),       # light strip: its contact end sits in J3's mouth, on J3's contacts
    ('strip_neck', 'display_thin'), ('strip_neck', 'display_thin_left'),
                                      # the neck lies on the glass ledge; a -0.1 panel's ledge is 0.1 higher
}                                     # (panel.z_levels) and the flex rides up with it
EXPECTED |= {(b, a) for a, b in EXPECTED}


def mesh_interference(min_vol=1e-3):
    """Display ribbons and the battery's leads and plug (meshes) against every printed part and
    the hardware near them, with manifold booleans."""
    import trimesh
    import panel
    items = {f'ribbon_{k}': m for k, m in panel.ribbons().items()}
    bm = refs.battery_meshes()
    items.update({k: m for k, m in bm.items() if k != 'battery_cell'})
    parts = {n: trimesh.load(OUT / f'{n}.stl') for n in PARTS}
    hwsol = hw.solids()
    rep = []
    for name, m in items.items():
        lo, hi = m.bounds
        others = dict(parts)
        others.update({k: v for k, v in bm.items() if k != name and not (name.startswith('lead') and k.startswith('lead'))})
        for ref, s in hwsol.items():
            b = s.BoundingBox()
            if b.xmax < lo[0] or b.xmin > hi[0] or b.ymax < lo[1] or b.ymin > hi[1] or b.zmax < lo[2] or b.zmin > hi[2]:
                continue
            vs, ts = s.tessellate(0.02, 0.2)
            others[ref] = trimesh.Trimesh([(v.x, v.y, v.z) for v in vs], ts, process=True)
        for other, o in others.items():
            if (o.bounds[1] < lo).any() or (o.bounds[0] > hi).any():
                continue
            try:
                inter = trimesh.boolean.intersection([m, o], engine='manifold')
                v = inter.volume if not inter.is_empty else 0.0
            except Exception as e:                      # non-manifold vendor mesh: fall back to a vertex test
                v = float(o.contains(m.vertices).sum()) * 1e-3 if o.is_watertight else 0.0
            if v > min_vol:
                ib = inter.bounds if v and not inter.is_empty else m.bounds
                rep.append({'part': name, 'with': other, 'volume': round(float(v), 4),
                            'expected': (name, other) in EXPECTED,
                            'where': [round(float(x), 2) for x in (ib[0][0], ib[1][0], ib[0][1], ib[1][1], ib[0][2], ib[1][2])]})
    return rep


STRIP_VARIANTS = {             # light strip: the two ends of the range the fit allows, and the bar against the wall
    'strip': dict(rin=P.FOLD_RIN, chin_loop=False),          # fold on the whole hinge; all the slack on the back
    'strip_tight': dict(rin=0.45, chin_loop=True),           # a tighter fold (its loop higher, the pair nearer the
                                                             # hinge) and a slack loop in the chin as well
    'strip_wall': dict(rin=P.FOLD_RIN, chin_loop=False, front_dx=P.STRIP_WALL_DX),   # the stiff front and the neck
}                                                            # against the side wall, as if the stop ribs had not printed
NO_RIBS = {'strip_wall'}                                     # checked against the tub without its ribs


def strip_interference(shapes, min_vol=1e-3):
    """Light strip: every piece of it (refs.strip) against every printed part, every board part, the panel at
    its three thicknesses and the battery, in every STRIP_VARIANTS case. Rows carry 'expected' as
    mesh_interference's. The at-the-wall case sees the tub without its stop ribs (shapes['tub_noribs'])."""
    hwsol = hw.solids()
    others = {**{k: v.val() for k, v in shapes.items() if k != 'tub_noribs'}, **hwsol,
              'display': refs.display().val(), 'battery': refs.battery().val(),
              'display_thick': refs.display(thickness=hw.PANEL_T + hw.PANEL_T_TOL).val(),
              'display_thin': refs.display(thickness=hw.PANEL_T - hw.PANEL_T_TOL).val(),
              # a -0.1 panel pushed against the left corner stops: its glass top is highest, its edge nearest the fold
              'display_thin_left': refs.display(thickness=hw.PANEL_T - hw.PANEL_T_TOL).translate((P.LOCATOR_X - hw.PANEL_X0, 0, 0)).val()}
    rep = []
    for var, kw in STRIP_VARIANTS.items():
        oth = dict(others, tub=shapes['tub_noribs'].val()) if var in NO_RIBS else others
        for name, wp in refs.strip(**kw).items():
            s = wp.val()
            sb = s.BoundingBox()
            for ref, h in oth.items():
                hb = h.BoundingBox()
                if hb.xmin > sb.xmax or hb.xmax < sb.xmin or hb.ymin > sb.ymax or hb.ymax < sb.ymin or hb.zmin > sb.zmax or hb.zmax < sb.zmin:
                    continue
                inter = s.intersect(h)
                v = inter.Volume()
                if v > min_vol:
                    ib = inter.BoundingBox()
                    rep.append({'variant': var, 'part': name, 'with': ref, 'volume': round(v, 4), 'expected': (name, ref) in EXPECTED,
                                'where': [round(x, 2) for x in (ib.xmin, ib.xmax, ib.ymin, ib.ymax, ib.zmin, ib.zmax)]})
    return rep


def bent_slide(tub_shape, st, led_h, step=0.1, min_vol=1e-5, n_bend=24, y_max=30.0, end=0.0):
    """Light strip: the slide under the seat with the bar bent as it really lies (mechanics.strip_bend), for a strip
    stack st over nominal and an LED led_h tall. The rigid sweep (strip_insertion) holds the whole front at the
    foot's 0.015 lift, which a thick stack takes below the seat's level. Here the stiff front is cut into Y slices:
    below the roof's end at the foot's height, over the bend in n_bend slices each at the bend's lowest point over it
    (so it is never higher than the real bar, and meets the seat's edge no later), from D6's body on at the LEDs'
    height. Swept -X from the drop-in place to its place against the ribs, against the tub below Y y_max (the seat's
    start and the first rib). The overlaps it looks for are thin slabs (0.01 deep over a 0.3 slice is 0.002 mm3), so
    its threshold is 1e-5 mm3, not the 1e-3 of the other sweeps. Returns 'clear' or the worst overlap.
    With y_max past the channel's end it is the whole slide on the LEDs (the flex at CHANNEL_TOP - led_h, under the pad
    ribs, PAD_RIBS); end < 0 carries the slide on toward the wall (the at-the-wall case, with the rib-less tub)."""
    from mechanics import strip_bend
    b = strip_bend(0.0, st, led_h)
    ys = [0.0, b['y_roof']] + [b['y_roof'] + (b['y_led'] - b['y_roof']) * i / n_bend for i in range(1, n_bend + 1)] + [y_max]
    f = refs.strip_front(P.FOLD_RIN).val()
    fx = tub_shape.intersect(box(-5, 16, 0, y_max, -1, P.Z_FRONT + 1).val())
    pieces = []
    for ya, yb in zip(ys[:-1], ys[1:]):
        pc = f.intersect(box(-5, 16, ya, yb, -5, 10).val())
        if pc.Volume() > 1e-6:
            pieces.append((pc, strip_bend(ya, st, led_h)['z'] - P.STRIP_Z0))
    dx = P.SEAT_X1 - P.STRIP_BAR_X[0]
    worst = (0.0, None)
    n = int(round((dx - end) / step))
    for x in [dx - i * step for i in range(n + 1)] + [end]:
        for pc, dz in pieces:
            v = pc.moved(cq.Location(cq.Vector(x, 0, dz))).intersect(fx).Volume()
            if v > worst[0]:
                worst = (v, (round(x, 3), round(dz, 4)))
    return 'clear' if worst[0] <= min_vol else {'mm3': round(worst[0], 4), 'at_dx_dz': worst[1]}


def strip_insertion(shapes, step=0.1, min_vol=1e-3):
    """Light strip: the way in, in the face-down tub before the panel. The stiff front (bar and foot, LEDs, the loop and
    the folded pair) drops in from the back SEAT_X1 - STRIP_BAR_X[0] to the right of its place, with its LEDs on the
    skin (lifted off its seat until the LEDs meet the skin or the foot its pocket's roof), slides -X under the seat
    to its place against the stop ribs, and settles onto the seat.
    Swept against the tub and the keys; reports the worst overlap on each leg, for both folds. Then:
      strip:ribs_stop   the relaxed fold slid on past its place toward the wall: where the ribs first stop it
      *:slide_bent      the slide with the bar bent off the foot's roof onto the skin (bent_slide): nominal, and a
                        +STRIP_STACK_TOL stack with an 0.8 and a STRIP_LED_H_MAX LED
      *:slide_on_leds   the same over the bar's whole length (under the pad ribs), nominal and thick with a tall LED,
                        and on to the wall in the rib-less tub
      strip_wall:*      the same legs with the slide carried on to STRIP_WALL_DX, against the tub without its ribs"""
    dx = P.SEAT_X1 - P.STRIP_BAR_X[0]
    # lifted off the seat until the foot meets its pocket's roof (0.015); elsewhere the LEDs would reach the skin at 0.215
    lift = min(P.STRIP_LED_CLR, round(P.FOOT_POCKET['top'] - (P.STRIP_Z0 + P.STRIP_STACK), 4))
    region = box(-5, 16, 5, 95, -1, P.Z_FRONT + 1).val()
    keysf = {k: shapes[k].val().intersect(region) for k in shapes if k.startswith('key_')}
    fixed = {'tub': shapes['tub'].val().intersect(region), **keysf}
    fixed_nr = {'tub': shapes['tub_noribs'].val().intersect(region), **keysf}

    def legs(end):
        n = int(round((dx - end) / step))
        return {'drop_in': [(dx, -8.0 + i * 0.25) for i in range(int((8.0 + lift) / 0.25) + 1)] + [(dx, lift)],
                'slide': [(dx - i * step, lift) for i in range(n + 1)] + [(end, lift)],
                'settle': [(end, lift), (end, lift / 2), (end, 0.0)]}

    def sweep(f, poses, fx_set):
        worst = (0.0, None, None)
        for x, z in poses:
            m = f.moved(cq.Location(cq.Vector(x, 0, z)))
            for k, fx in fx_set.items():
                v = m.intersect(fx).Volume()
                if v > worst[0]:
                    worst = (v, k, (round(x, 3), round(z, 3)))
        return 'clear' if worst[0] <= min_vol else {'mm3': round(worst[0], 4), 'with': worst[1], 'at_dx_dz': worst[2]}

    rep = {'shift_x': round(dx, 3), 'lift_z': lift, 'wall_dx': P.STRIP_WALL_DX}
    for var, rin, end, fx_set in (('strip', P.FOLD_RIN, 0.0, fixed), ('strip_tight', 0.45, 0.0, fixed),
                                  ('strip_wall', P.FOLD_RIN, P.STRIP_WALL_DX, fixed_nr)):
        f = refs.strip_front(rin).val()
        for leg, poses in legs(end).items():
            rep[f'{var}:{leg}'] = sweep(f, poses, fx_set)
    # the ribs: from its place on toward the wall in 0.01 steps, the first position where the bar meets them
    f = refs.strip_front(P.FOLD_RIN).val()
    first = None
    for i in range(1, int(round(-P.STRIP_WALL_DX / 0.01)) + 1):
        v = f.moved(cq.Location(cq.Vector(-0.01 * i, 0, 0.0))).intersect(fixed['tub']).Volume()
        if v > min_vol:
            first = {'dx': round(-0.01 * i, 3), 'mm3': round(v, 4)}
            break
    rep['strip:ribs_stop'] = first or 'not stopped'
    # the bar bent (bent_slide), with the strip stack at +STRIP_STACK_TOL, where the rigid sweep's lift would be -0.03
    rep['strip_thick:slide_bent'] = bent_slide(shapes['tub'].val(), P.STRIP_STACK_TOL, P.STRIP_LED_H)
    rep['strip_thick_tall_led:slide_bent'] = bent_slide(shapes['tub'].val(), P.STRIP_STACK_TOL, P.STRIP_LED_H_MAX)
    rep['strip:slide_bent'] = bent_slide(shapes['tub'].val(), 0.0, P.STRIP_LED_H)
    # the whole slide on the LEDs, under the pad ribs (PAD_RIBS): the flex lies at CHANNEL_TOP - LED height, 0.2 under
    # the ribs with an 0.8 LED (the tightest), 0.3 with a 0.9 one; also on to the wall in the rib-less tub
    ym = P.CHANNEL_Y[1] + 3.0
    rep['strip:slide_on_leds'] = bent_slide(shapes['tub'].val(), 0.0, P.STRIP_LED_H, y_max=ym)
    rep['strip_thick_tall_led:slide_on_leds'] = bent_slide(shapes['tub'].val(), P.STRIP_STACK_TOL, P.STRIP_LED_H_MAX, y_max=ym)
    rep['strip_wall:slide_on_leds'] = bent_slide(shapes['tub_noribs'].val(), 0.0, P.STRIP_LED_H, y_max=ym, end=P.STRIP_WALL_DX)
    return rep


def display_vs_board(min_vol=1e-4):
    """Rev K's open item: the display against the board's own parts, with every through-hole lead tip trimmed
    to LEAD_TIP (the assembly note), at the panel's thickest (its rear is closest to the board)."""
    disp = refs.display(thickness=hw.PANEL_T + hw.PANEL_T_TOL).val()
    clip = box(-10, 70, -10, 100, -10, P.LEAD_TIP).val()
    rep = []
    for ref, h in hw.solids().items():
        hb = h.BoundingBox()
        if hb.zmax < P.DISP_REAR - 0.3:
            continue
        v = disp.intersect(h.intersect(clip)).Volume()
        if v > min_vol:
            rep.append({'with': ref, 'volume': round(v, 4)})
    return rep


def summary(shapes):
    b = {k: shapes[k].val().BoundingBox() for k in shapes}
    return {'shell_mm': [round(P.X1 - P.X0, 2), round(P.Y1 - P.Y0, 2), round(P.Z_FRONT - P.Z_BACK, 3)],
            'z_front': P.Z_FRONT, 'z_back': P.Z_BACK, 'seam': P.SEAM,
            'with_keys_mm': round(max(v.zmax for v in b.values()) - min(v.zmin for v in b.values()), 3),
            'panel_xy': [round(hw.PANEL_X0, 3), round(hw.PANEL_X1, 3), round(hw.PANEL_Y0, 3), round(hw.PANEL_Y1, 3)],
            'battery': {'xy': [*P.BATT['x'], *P.BATT['y']], 'z': [round(v, 3) for v in P.BATT['z']], 'ref': P.BATT_REF},
            'volumes_mm3': {k: round(v.val().Volume(), 1) for k, v in shapes.items()}}


def main():
    """One build (SILKSCREEN_VARIANT): its parts, then its checks. The light strip's checks run in its build only."""
    print(f'build: {P.VARIANT} -> {OUT}', flush=True)
    shapes = build_all()
    sm = summary(shapes)
    sm['variant'] = P.VARIANT
    sm['keys_top_z'] = round(max(shapes[f'key_{r}'].val().BoundingBox().zmax for r in P.KEY_REFS), 4)   # the caps
    # stand KEY_TOP_OVER_FACE over this build's face at rest
    if P.LIGHT_STRIP:
        shapes['tub_noribs'] = tub.build(ribs=False)        # the strip-at-the-wall case's tub (no stop ribs)
    (OUT / 'summary.json').write_text(json.dumps(sm, indent=1))
    print('summary', json.dumps({k: sm[k] for k in ('shell_mm', 'with_keys_mm', 'keys_top_z')}))
    ins = insertion_check(shapes)
    print('\ninsertion path (panel at its largest, midplate), from the back into the face-down tub:')
    for k, v in ins.items():
        print(f"  {k:14s} x {v['path_x']} y {v['path_y']} -> {'clear' if not v['hits'] else v['hits']}")
    t0 = time.time()
    import lid_close                                        # the lid closing: the latch arms bent, the bodge wires
    lc = lid_close.run(*(lid_close.mesh_of(shapes[k].val()) for k in ('lid', 'tub', 'midplate')), shapes['lid'].val())
    ins['_lid_close'] = lc
    print(lid_close.summary(lc) + f'  ({time.time() - t0:.0f}s)', flush=True)
    t0 = time.time()
    lm = later_moves(shapes)
    ins['_later'] = lm
    if P.LIGHT_STRIP:
        t0 = time.time()
        si = strip_insertion(shapes)
        ins['_strip'] = si
        print(f'light strip in (sideways under the seat, before the panel): {si}  ({time.time() - t0:.0f}s)')
    (OUT / 'insertion.json').write_text(json.dumps(ins, indent=1))
    print(f"PCBA in (J1, side switches, SW11, board past the bay): {lm['pcba_in'] or 'clear'}\n"
          f"lid on (with its side keys): {lm['lid_on'] or 'clear'}  ({time.time() - t0:.0f}s)")
    if '--no-check' not in sys.argv:
        t0 = time.time()
        rep = interference(shapes)
        rep += mesh_interference()
        dvb = display_vs_board()
        con = contacts(shapes)
        res = {'parts': rep, 'contacts': con, 'display_vs_board': dvb}
        if P.LIGHT_STRIP:
            res['strip'] = srep = strip_interference(shapes)
        (OUT / 'interference.json').write_text(json.dumps(res, indent=1))
        print('display vs board (leads trimmed to LEAD_TIP):', dvb or 'clear')
        print(f'\n{len(rep)} interferences ({time.time() - t0:.0f}s):')
        for r in rep:
            print(f"  {r['part']:10s} x {r['with']:14s} {r['volume']:9.4f} mm3 at {r['where']}"
                  f"{'  (expected)' if r.get('expected') else ''}")
        for r in con:
            print(f"expected contact {' x '.join(r['pair'])}: {'PASS' if r['ok'] else 'FAIL'} {r}")
        if P.LIGHT_STRIP:
            print(f"\nlight strip ({', '.join(STRIP_VARIANTS)}): {len(srep)} contacts, "
                  f"{sum(not r['expected'] for r in srep)} unexpected:")
            for r in srep:
                print(f"  {r['variant']:12s} {r['part']:18s} x {r['with']:14s} {r['volume']:9.4f} mm3 at {r['where']}"
                      f"{'  (expected)' if r['expected'] else ''}")
        import crank_checks
        cr = crank_checks.run(shapes)
        (OUT / 'crank.json').write_text(json.dumps(cr, indent=1))
        print('\n' + crank_checks.summary(cr))


def _step_text(path):
    """A STEP file's text without its export timestamp, so two exports of one shape compare equal."""
    return re.sub(rb"'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d'", b"''", path.read_bytes(), count=1)


def shared_check(dirs, tol=1e-6):
    """Ian's rule, asserted: every part but the tub and the bottom keys is the same in the two builds (dirs: variant ->
    its out folder). Each SHARED part (the cranks among them), from both builds' STEPs: equal volumes and an empty
    boolean difference both ways; also whether the STEPs (bar the timestamp) and the STLs are the same byte for byte.
    The lid's split bodies (lid_body, the side keys) have STLs only: byte for byte. A part passes on the solids or on
    identical files; raises AssertionError naming every part that fails. The tub-specific parts (TUB_SPECIFIC) are
    listed with whether they differ, which they should."""
    a, b = dirs['standard'], dirs['light-strip']
    rows, bad = {}, []
    for name in SHARED:
        sa = cq.importers.importStep(str(a / f'{name}.step')).val()
        sb = cq.importers.importStep(str(b / f'{name}.step')).val()
        va, vb = sa.Volume(), sb.Volume()
        d_ab, d_ba = sa.cut(sb).Volume(), sb.cut(sa).Volume()
        solids = abs(va - vb) <= tol and d_ab <= tol and d_ba <= tol
        files = (_step_text(a / f'{name}.step') == _step_text(b / f'{name}.step')
                 and (a / f'{name}.stl').read_bytes() == (b / f'{name}.stl').read_bytes())
        rows[name] = {'mm3': [round(va, 4), round(vb, 4)], 'standard_minus_light_strip_mm3': round(d_ab, 6),
                      'light_strip_minus_standard_mm3': round(d_ba, 6), 'same_solid': solids, 'same_files': files}
        if not (solids or files):
            bad.append(name)
    for name in ['lid_body', *SIDE_KEYS]:
        files = (a / f'{name}.stl').read_bytes() == (b / f'{name}.stl').read_bytes()
        rows[name] = {'same_files': files}
        if not files:
            bad.append(name)
    specific = {}
    for name in TUB_SPECIFIC:
        va = cq.importers.importStep(str(a / f'{name}.step')).val().Volume()
        vb = cq.importers.importStep(str(b / f'{name}.step')).val().Volume()
        specific[name] = {'mm3': [round(va, 4), round(vb, 4)], 'differ': abs(va - vb) > tol}
    rep = {'rule': 'every printed part but the tub and the bottom keys is shared', 'parts': rows, 'differ': bad,
           'tub_specific': specific}
    (hw.ROOT / 'out' / 'shared-parts.json').write_text(json.dumps(rep, indent=1))
    if bad:
        raise AssertionError(f'shared parts differ between the builds: {bad} (out/shared-parts.json)')
    return rep


CROSS_PLANES = (0.0, 1.0, -1.0, 3.9, -3.9, 4.65, -4.65, 5.0, -5.0)   # dx of the YZ sections compared


def _yz_face(solid, x):
    """The solid's section at X x (a compound of planar faces)."""
    return cq.Compound.makeCompound(cq.Workplane('YZ').add([solid]).section(x).faces().vals())


def cross_project_check(tol_v=0.01, tol_b=0.002, tol_s=0.002):
    """The rule that both case projects print the same crank (crank.py's shared cheek block is the same text as
    case-426/src/keys.py's; the rest of the crank follows it line for line): this project's crank-M and crank-T (out/
    standard, their STEPs) against case-426's, when that project is built: volume within tol_v mm3, bounds within
    tol_b, and YZ sections at CROSS_PLANES with at most tol_s mm2 of symmetric difference. Raises AssertionError naming
    each part that differs; prints a warning (and records it) when case-426 is not built. The result goes into
    out/shared-parts.json under 'cross_project'."""
    mine, other = hw.ROOT / 'out' / 'standard', hw.ROOT.parent / 'case-426' / 'out' / 'standard'
    rep = {'other': str(other), 'tolerances': {'mm3': tol_v, 'bounds_mm': tol_b, 'section_mm2': tol_s}, 'parts': {}}
    if not all((other / f'{n}.step').exists() for n in CRANKS):
        rep['built'] = False
        print(f'WARNING: cross-project crank check skipped: {other} has no crank STEPs (build case-426 first)')
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
        raise AssertionError(f"cranks differ from case-426's: {rep['differ']} (out/shared-parts.json 'cross_project')")
    return rep


KEY_FILES = {'standard': 'key-x3std', 'light-strip': 'key-x3ls'}
COUPONS = ['coupon-strip', 'coupon-gate']      # per build: print/3.68/<coupon>-x3std, <coupon>-x3ls


def write_print(dirs):
    """print/3.68/ at the repo root, the committed files to print from, each as a print-oriented STL (plates.ORIENT,
    '<name>.stl') and a STEP in the CAD frame ('<name>.step'):
      tub-standard, tub-light-strip       one per build
      key-x3std, key-x3ls                 the bottom key, one per build (print four)
      lid, midplate, crank-M, crank-T     shared (from the light-strip build; shared_check has shown them the same).
                                          Four cranks: crank-T for JLC boards (TS365ZJ), crank-M for MJTP1117 boards
      gate                                the rod's left stop (SPEC2 rev 3), shared: gate.stl and gate.step both in its
                                          print pose, on its inner face (crank.gate('print'), as the 4.26 case's
                                          print/4.26/gate.step); out/<build>/gate.* are installed in the -X wall
      coupon-strip-x3std, coupon-gate-x3std (and the same -x3ls)
                                          per build: the hook keys' optional fit check (tub.coupon: SW9's opening and
                                          its two slots, printed with one key; test 2 removed the drag coupon's keys)
                                          and the gate's proof coupon (tub.gate_coupon), printed with a gate
      ROD.txt                             the rod and the gate: cut, taper, fit, service (rod_note)
    enclosures/make_plates.py lays the same parts out on three plates in print/silkscreen-368-plates.3mf. The rod is
    not a part: a 63.25 cut of 1.75 PLA filament (ROD.txt). A STEP that differs from the one there only by its
    timestamp is left as it is. Files there that this build no longer makes are removed."""
    import trimesh, plates
    PRINT_DIR.mkdir(parents=True, exist_ok=True)
    items = ([(f'tub-{v}', dirs[v], 'tub') for v in variant.VARIANTS] + [(KEY_FILES[v], dirs[v], KEY_FILES[v]) for v in variant.VARIANTS]
             + [(p, dirs['light-strip'], p) for p in SHARED if not p.startswith('crank_')]
             + [(f"{c}-{KEY_FILES[v].split('-')[1]}", dirs[v], c) for v in variant.VARIANTS for c in COUPONS])
    made = {'ROD.txt'}
    for name, d, part in items:
        plates.orient(trimesh.load(d / f'{part}.stl'), part).export(PRINT_DIR / f'{name}.stl')
        dest = PRINT_DIR / f'{name}.step'
        src = d / f'{part}.step'
        if part == 'gate':                                   # its STEP in the print pose, as its STL
            src = d / 'gate-print.step'
            cq.exporters.export(crank.gate('print'), str(src))
        if not dest.exists() or _step_text(dest) != _step_text(src):
            shutil.copyfile(src, dest)
        made |= {f'{name}.stl', f'{name}.step'}
    for f in PRINT_DIR.iterdir():
        if f.is_file() and f.name not in made:
            f.unlink()
    (PRINT_DIR / 'ROD.txt').write_bytes(rod_note().encode())
    return sorted(p.name for p in PRINT_DIR.iterdir())


def rod_note():
    """print/3.68/ROD.txt (SPEC2 rev 3, section 8), its numbers from params: the rod's cut and end play, and how far it
    stands out of the slot once pushed back to the last ring for service."""
    span = P.ROD_SPAN[1] - P.ROD_SPAN[0]
    play = (span - P.ROD_CUT - P.ROD_CUT_TOL, span - P.ROD_CUT + P.ROD_CUT_TOL)
    out = (P.X0 - (P.RAIL_X1 - P.ROD_CUT + P.ROD_CUT_TOL), P.X0 - (P.RAIL_X1 - P.ROD_CUT - P.ROD_CUT_TOL))
    T, G = P.ROD_TIP, P.GATE
    return f"""Bottom keys: the crank rod (not printed) and its gate (printed, gate.stl)

Rod: 1.75 mm PLA filament, cut to {P.ROD_CUT:.2f} +- {P.ROD_CUT_TOL:.1f} mm. One per case.
  - Make it in the rod jig (print/rod-jig.stl, also on plate 3 of print/silkscreen-368-plates.3mf). Cut
    about 80 mm of filament and warm it until it goes limp: about 10 s in hot water (a kettle left to stand
    a minute), or lay it in the jig's groove and set the jig on the bed at 60 C for 5 minutes. Press it
    into the groove and let it cool there for half a minute. While it is still warm, cut it at both slots
    with your scraper's razor blade: it comes out straight, {P.ROD_CUT:.2f} long and square at both ends. Lift
    it out at the window in the middle.
  - Taper one end (the one that goes in first) in a pencil sharpener, stopping while the tip still has a
    flat about {T['flat']:.1f} mm across (about half the rod's width). Not a needle point. The other end
    stays square: it bears on the gate.
  - It goes in from the case's left side (-X): along the channel in the slot beside the chin, through
    the rings and the four cranks (don't hold them; the taper picks them up), until its tail is flush
    with the case side or just inside.
Gate: print two (inner face on the bed); one is a spare. Right after the rod, drop it into the slot from
  the open back, bevel down, small hole outward, and press it level with the rim: it pushes the rod the
  last {G['web'] + G['flange']:.2f} mm. If it stops proud, lift it, push the tail a little further in, press again.
  End play is then {play[0]:.1f}-{play[1]:.1f} mm. No screw.
  To take it out: a straightened paperclip in its small hole, lift. Then push the rod's right end
  toward -X with a small screwdriver until it stops; {out[0]:.1f}-{out[1]:.1f} mm stands out of the slot.
Cranks: crank-T for TS365ZJ boards (every JLC board), crank-M for APEM MJTP1117.
  Each cheek holds the rod in a closed hole: feed the rod through; its taper finds the holes.
  Ream each crank's two bores with a 1.9 mm drill; the rod must slide and turn freely.
  Print the cranks with elephant-foot compensation 0 and Arachne walls, and the keys (standing on
  their -X end) and the gate with elephant-foot compensation 0 (OrcaSlicer, per object; the plate
  file has them), no brim, no supports.
Keys (the hook keys, since test 2): each has two small hooks on its chin side that run in two slots
  in the chin wall. Keep the tub face-down, on a cloth, from the keys until the board is in:
  1. keys: from inside, hooks in their slots, slide each out until it stops (2.5 mm proud, level);
     it only fits one way round;
  2. cranks: drop each into its slot; it lies on its key;
  3. rod, then the gate (above); from here nothing can fall out;
  4. board, then the lid and screws; turn it over and the keys settle onto their switches.
  Turned face-up before the board, the keys sink (or fall in, before the rod); face-down again puts
  them back.
Before the first full print: the gate coupon (fit, cam, and the 5.5 kg push). The chin coupon
  (coupon-strip, with one key) is an optional 15-minute fit check of the hooks in their slots; nothing
  is tuned from it. See enclosures/case-368/README.md, "Bottom keys".
"""


def build_variants(args):
    """Both builds, each in its own process (params reads the variant once, at import), each logged to
    out/<variant>/build.log; then shared_check and write_print."""
    dirs = {v: hw.ROOT / 'out' / v for v in variant.VARIANTS}
    for v, d in dirs.items():
        d.mkdir(parents=True, exist_ok=True)
        with open(d / 'build.log', 'w', encoding='utf-8') as log:
            p = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), *args], cwd=hw.ROOT,
                                 env=dict(os.environ, SILKSCREEN_VARIANT=v, PYTHONUNBUFFERED='1'), stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
            for line in p.stdout:
                sys.stdout.write(line)
                sys.stdout.flush()
                log.write(line)
                log.flush()
            rc = p.wait()
            log.write(f'exit {rc}\n')
        if rc:
            raise SystemExit(f'{v} build failed (exit {rc}): {d / "build.log"}')
    t0 = time.time()
    rep = shared_check(dirs)
    print(f"\nshared parts, standard vs light-strip ({time.time() - t0:.0f}s): all {len(rep['parts'])} the same")
    for k, r in rep['parts'].items():
        print(f'  {k:18s} {r}')
    print('tub-specific: ' + ', '.join(f"{k} {'differ' if r['differ'] else 'SAME'} {r['mm3']}" for k, r in rep['tub_specific'].items()))
    files = write_print(dirs)
    print(f'print/3.68/: {len(files)} files: {", ".join(files)}')
    t0 = time.time()
    xp = cross_project_check()                          # last: it needs case-426 built with the same crank code
    if xp['built']:
        print(f"cranks, this project vs case-426 ({time.time() - t0:.0f}s): the same: "
              + '; '.join(f"{n} {r['mm3']} mm3, bounds {r['bounds_max_diff']}, sections <= {max(r['section_symdiff_mm2'].values())} mm2"
                          for n, r in xp['parts'].items()))


if __name__ == '__main__':
    if 'SILKSCREEN_VARIANT' in os.environ:
        main()
    else:
        build_variants(sys.argv[1:])
