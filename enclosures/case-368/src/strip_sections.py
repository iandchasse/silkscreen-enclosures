"""Light strip: cross-sections through the built parts with the strip drawn in, and the clearances round it.

Run from this project's folder (enclosures/case-368) with the original project's venv (README.md, "Rebuilding"):

    python -B src/strip_sections.py     # after src/build.py (reads out/light-strip/*.step)

The light-strip build only (variant.py). Writes out/light-strip-sections/*.png and clearances.json. Sections are cut from the exported meshes (the tub, the
midplate, the lid, the keys) and from the reference solids (board parts, panel, strip), so they show what the checks
see. Clearances are exact (OpenCascade's shape-to-shape distance on the CAD solids)."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly
import cadquery as cq
import hw
import params as P
import refs, tub, midplate, lid, keys, crank
from geom import box

OUT = hw.ROOT / 'out' / 'light-strip-sections'
COL = {'tub': '#d8cfb8', 'midplate': '#8a968b', 'lid': '#bdb39c', 'key': '#c8553d', 'PCB': '#2f6b3a',
       'display': '#9fb6cc', 'part': '#555555', 'strip_bar': '#e0a020', 'strip_folded': '#e0a020',
       'strip_leds': '#fff3a0', 'strip_folded_leds': '#fff3a0', 'strip_hinge': '#b86b00', 'strip_neck': '#b86b00',
       'strip_tail': '#e0a020', 'strip_diodes': '#333333'}


def _section(shape, axis, at, n=240):
    """Polygons (shapely, with holes) of a CAD solid cut by the plane axis = at, in (horizontal, Z) coordinates:
    OpenCascade's planar common of the solid and the plane, each face's wires sampled along their length."""
    import shapely.geometry as sg
    if axis == 'y':
        plane = cq.Face.makePlane(400, 400, cq.Vector(0, at, 0), cq.Vector(0, 1, 0))
        uv = lambda v: (v.x, v.z)
    else:
        plane = cq.Face.makePlane(400, 400, cq.Vector(at, 0, 0), cq.Vector(1, 0, 0))
        uv = lambda v: (v.y, v.z)
    try:
        res = shape.intersect(plane)
    except Exception:
        return []
    out = []
    from shapely.ops import unary_union
    for f in res.Faces():
        vs, tris = f.tessellate(0.005, 0.1)
        pts = [uv(v) for v in vs]
        poly = unary_union([sg.Polygon([pts[a], pts[b], pts[c]]).buffer(1e-6) for a, b, c in tris])
        out += [g for g in getattr(poly, 'geoms', [poly]) if g.geom_type == 'Polygon' and g.area > 1e-6]
    return out


def _scene(variant, tub_solid=None):
    items = {}
    for name in ('tub', 'midplate', 'lid'):
        items[name] = cq.importers.importStep(str(hw.OUT / f'{name}.step')).val()
    if tub_solid is not None:
        items['tub'] = tub_solid
    for r in P.KEY_REFS:
        for p in ('key', 'crank'):
            items[f'{p}_{r}'] = cq.importers.importStep(str(hw.OUT / f'{p}_{r}.step')).val()
    sol = hw.solids()
    for r in ('PCB', 'J3', 'SW9', 'R50', 'R60', 'Q5', 'SW7', 'U13'):
        items[r] = sol[r]
    items['display'] = refs.display().val()
    for k, v in refs.strip(**variant).items():
        items[k] = v.val()
    return items


def _colour(name):
    if name in COL:
        return COL[name]
    if name.startswith('key_'):
        return COL['key']
    return COL['part']


def draw(items, axis, at, xlim, zlim, title, fname, notes=()):
    fig, ax = plt.subplots(figsize=(11, 11 * (zlim[1] - zlim[0]) / (xlim[1] - xlim[0]) + 1.6), dpi=150)
    drawn = set()
    order = ['lid', 'PCB', 'midplate', 'display', 'tub'] + [k for k in items if k not in ('lid', 'PCB', 'midplate', 'display', 'tub')]
    for name in order:
        if name not in items:
            continue
        for poly in _section(items[name], axis, at):
            c = _colour(name)
            lab = None
            if name.startswith('strip'):
                lab = name
            elif name.startswith('key_'):
                lab = 'bottom key'
            elif name.startswith('crank_'):
                lab = 'crank'
            else:
                lab = name
            ax.add_patch(MPoly(np.array(poly.exterior.coords), closed=True, fc=c, ec='k', lw=0.4,
                               label=lab if lab not in drawn else None, zorder=3 if name.startswith('strip') else 2))
            drawn.add(lab)
            for r in poly.interiors:
                ax.add_patch(MPoly(np.array(r.coords), closed=True, fc='white', ec='k', lw=0.3, zorder=2))
    ax.set_xlim(*xlim)
    ax.set_ylim(*zlim)
    ax.set_aspect('equal')
    ax.set_xlabel(('X' if axis == 'y' else 'Y') + ' (mm, CAD frame)')
    ax.set_ylabel('Z (mm; 0 = PCB rear, + toward the viewer)')
    ax.set_title(title, fontsize=10)
    ax.grid(True, lw=0.3, alpha=0.5)
    for (x, z, t) in notes:
        ax.annotate(t, (x, z), fontsize=7, zorder=5, bbox=dict(fc='white', ec='none', alpha=0.8, pad=0.5))
    ax.legend(loc='lower right', fontsize=7, framealpha=0.9)
    fig.tight_layout()
    fig.savefig(OUT / fname)
    plt.close(fig)


VARIANTS = {'strip': dict(rin=P.FOLD_RIN, chin_loop=False), 'strip_tight': dict(rin=0.45, chin_loop=True),
            'strip_wall': dict(rin=P.FOLD_RIN, chin_loop=False, front_dx=P.STRIP_WALL_DX)}     # build.STRIP_VARIANTS


def latch_arm(lid_solid):
    """The lid's left latch arm at Y 83.0 (Y 80.75..85.25, its top at Z 2.485), the one under the folded pair."""
    return lid_solid.intersect(box(-3.0, 1.0, 78.0, 88.0, 0.0, 3.0).val())


def clearances(tub_noribs=None):
    """Smallest distance between each strip piece and what is near it, in every case (0 = touching or overlapping).
    The at-the-wall case is measured against the tub without its stop ribs."""
    sol = hw.solids()
    lid_s = lid.build(keys=False).val()
    parts = {'tub': tub.build().val(), 'midplate': midplate.build().val(), 'lid': lid_s, 'latch_arm_Y83': latch_arm(lid_s),
             'key_SW9': keys.build('SW9').val(), 'crank_SW9': crank.build('M', keys.centre('SW9')).val(),
             'display': refs.display().val(),
             'display_max_left': refs.display().translate((P.LOCATOR_X - hw.PANEL_X0, 0, 0)).val()}
    parts.update({r: sol[r] for r in ('PCB', 'J3', 'SW9', 'R50', 'R60', 'Q5', 'U13', 'SW7')})
    noribs = tub_noribs if tub_noribs is not None else tub.build(ribs=False).val()
    pairs = {'strip_leds': ['tub'], 'strip_bar': ['tub', 'display'], 'strip_hinge': ['tub', 'midplate'],
             'strip_folded': ['tub', 'midplate', 'display', 'display_max_left'],
             'strip_folded_leds': ['latch_arm_Y83', 'midplate', 'display', 'display_max_left', 'SW7', 'PCB'],
             'strip_neck': ['tub', 'midplate', 'SW9', 'key_SW9', 'crank_SW9', 'PCB', 'lid', 'R60'],
             'strip_tail': ['lid', 'R50', 'R60', 'Q5', 'U13', 'PCB', 'J3'], 'strip_diodes': ['lid', 'R60', 'PCB', 'J3']}
    out = {}
    for var, kw in VARIANTS.items():
        s = refs.strip(**kw)
        pp = dict(parts, tub=noribs) if var == 'strip_wall' else parts
        out[var] = {k: {o: round(s[k].val().distance(pp[o]), 3) for o in os} for k, os in pairs.items()}
    # the folded LEDs against the Y-83 latch arm for every fold radius the zone takes, at the ribs and at the wall
    arm = parts['latch_arm_Y83']
    rows = {}
    for rin in (P.FOLD_RIN, 0.45, 0.35):
        for dxl, fdx in (('at the ribs', 0.0), ('at the wall', P.STRIP_WALL_DX)):
            fl = refs.strip(rin=rin, front_dx=fdx)['strip_folded_leds'].val()
            ov = fl.intersect(arm).Volume()
            rows[f'R{rin:g} {dxl}'] = {'distance_mm': round(fl.distance(arm), 4), 'overlap_mm3': round(ov, 5) if ov > 1e-7 else 0.0}
    out['folded_leds_to_latch_arm_Y83'] = rows
    out['retention'] = retention(parts['tub'], parts['midplate'])
    return out


def retention(tub_s, mid_s):
    """The retention fixes (2026-09-26). Pad ribs: the bar's flex and LEDs, lifted onto the skin as they slide in (flex
    at CHANNEL_TOP - LED height), against the ribs (the tub inside the ribs' boxes, clear of the stop ribs), and the Y
    margins from each rib to the LED bodies and their solder pads either side. Corner stops: how much of the glass's
    edge they face for each panel thickness, and their clearance to the midplate's notches."""
    PR = P.PAD_RIBS
    d = refs.strip_data()
    ribs = None
    for yc in PR['y']:
        b = box(P.STRIP_RIBS['x1'] + 0.01, P.PAD_X[0] - 0.01, yc - PR['len'] / 2, yc + PR['len'] / 2, PR['z0'] - 0.5, P.CHANNEL_TOP)
        ribs = b if ribs is None else ribs.union(b)
    rib_s = tub_s.intersect(ribs.val())
    out = {'pad_ribs': {'z0': PR['z0'], 'len': PR['len'], 'y': list(PR['y'])}}
    for lab, lh in (('0.8 LED', P.STRIP_LED_H), ('0.9 LED', P.STRIP_LED_H_MAX)):
        lift = P.CHANNEL_TOP - lh - (P.STRIP_Z0 + P.STRIP_STACK)
        s = refs.strip(dz=lift)
        out['pad_ribs'][f'on the LEDs, {lab}: flex to ribs'] = round(s['strip_bar'].val().distance(rib_s), 3)
        s = refs.strip(dz=P.STRIP_LED_CLR)
        out['pad_ribs'][f'on the LEDs, {lab}: LED bodies to ribs'] = round(s['strip_leds'].val().distance(rib_s), 3)
    ys = [y for _, _, y in d['leds'] if y < refs.STRIP_HINGE[0]]
    half, pad_end = d['led']['len'] / 2, 2.65
    m_body = min(min(abs(y - yc) for y in ys) - half - PR['len'] / 2 for yc in PR['y'])
    m_pads = min(min(abs(y - yc) for y in ys) - pad_end - PR['len'] / 2 for yc in PR['y'])
    out['pad_ribs']['y_margin_to_led_bodies'] = round(m_body, 3)
    out['pad_ribs']['y_margin_to_led_solder_pads'] = round(m_pads, 3)
    st = {}
    for th in (hw.PANEL_T - hw.PANEL_T_TOL, hw.PANEL_T, hw.PANEL_T + hw.PANEL_T_TOL):
        g0 = P.LIP - th                                              # the glass is the panel's rear 0.5
        g1 = g0 + 0.5
        cov = max(0.0, min(g1, P.LOCATOR_Z) - max(g0, P.LOCATOR_Z0))
        st[f'{th:.2f} panel'] = {'glass_edge_z': [round(g0, 3), round(g1, 3)], 'faced_mm': round(cov, 3),
                                 'contact_mm2': round(cov * ((P.LOCATOR_Y[1] - P.LOCATOR_Y[0]) + (P.LOCATOR_Y_TOP[1] - P.LOCATOR_Y_TOP[0])), 3)}
    near = box(-2.0, 1.6, 6.0, 10.0, 1.0, 3.5).val(), box(-2.0, 1.6, 91.5, 95.0, 1.0, 3.5).val()
    out['corner_stops'] = {'z': [P.LOCATOR_Z0, P.LOCATOR_Z], 'x': P.LOCATOR_X, 'y': [list(P.LOCATOR_Y), list(P.LOCATOR_Y_TOP)],
                           'glass_edge': st,
                           'to_midplate_notch_mm': [round(tub_s.intersect(n).distance(mid_s.intersect(n)), 3) for n in near]}
    return out


if __name__ == '__main__':
    if not P.LIGHT_STRIP:
        raise SystemExit('strip_sections.py is for the light-strip build (SILKSCREEN_VARIANT=light-strip)')
    OUT.mkdir(parents=True, exist_ok=True)
    rep = refs.strip_report()
    relaxed = dict(rin=P.FOLD_RIN, chin_loop=False)
    tight = dict(rin=0.45, chin_loop=True)
    items = _scene(relaxed)
    top = P.STRIP_LED_TOP
    draw(items, 'y', 49.70, (-4.6, 6.0), (-0.6, 5.8),
         f'Across the bar through LED D4 (Y 49.70): bar on the seat at Z {P.LIP}, LED top {top:.3f}, '
         f'skin underside {P.CHANNEL_TOP} ({P.CHANNEL_TOP - top:.3f} clear), face {P.Z_FRONT}',
         'bar-led-D4-Y49.70.png',
         notes=[(-4.4, P.Z_FRONT + 0.15, f'raised face {P.Z_FRONT} (x3 {P.Z_FRONT_BASE})'),
                (1.2, 4.2, 'light path under the skin\nto the window (edge 2.827)')])
    R = P.STRIP_RIBS
    draw(items, 'y', R['y'][2], (-4.6, 6.0), (-0.6, 5.8),
         f'Across the bar at a stop rib (Y {R["y"][2]}): rib X {R["x0"]}..{R["x1"]} on the channel wall, the bar\'s edge on it',
         f'rib-Y{R["y"][2]}.png')
    draw(items, 'x', 10.0, (5.0, 15.0), (2.8, 5.4),
         f'Foot pocket (X 10.0): roof at {P.FOOT_POCKET["top"]}, {P.FOOT_POCKET["top"] - P.STRIP_Z0 - P.STRIP_STACK:.3f} over the foot; '
         f'the pocket opens into the window at Y {P.FOOT_POCKET["y1"]}', 'foot-pocket-X10.0.png')
    PR = P.PAD_RIBS
    draw(items, 'y', P.PAD_Y[1], (-4.6, 6.0), (-0.6, 5.8),
         f'Across the bar between pairs, through a hold-down pad (Y {P.PAD_Y[1]}): pad X {P.PAD_X[0]}..{P.PAD_X[1]:.3f} on the PS film, '
         f'its rib back to the wall under the ceiling (Z {PR["z0"]}..{P.CHANNEL_TOP})',
         f'pad-Y{P.PAD_Y[1]}.png')
    draw(items, 'x', 0.26, (36.0, 54.0), (2.4, 5.6),
         f'Along the bar (X 0.26) past the rib of pad 2 (Y {PR["y"][1] - PR["len"] / 2:g}..{PR["y"][1] + PR["len"] / 2:g}, Z {PR["z0"]}..{P.CHANNEL_TOP}) '
         'between D11 and D4; the bar on its seat', 'pad-rib-along-X0.26.png')
    s_up = _scene(relaxed)
    for k, v in refs.strip(dz=P.CHANNEL_TOP - P.STRIP_LED_H - (P.STRIP_Z0 + P.STRIP_STACK)).items():
        s_up[k] = v.val()
    draw(s_up, 'x', 0.26, (36.0, 54.0), (2.4, 5.6),
         f'As it slides in, face down, on its LEDs (X 0.26): flex at {P.CHANNEL_TOP - P.STRIP_LED_H:.2f}, '
         f'{PR["z0"] - (P.CHANNEL_TOP - P.STRIP_LED_H):.2f} under the rib', 'pad-rib-slide-X0.26.png')
    draw(items, 'y', 8.1, (-4.6, 6.0), (-0.6, 5.8),
         f'Across the bottom-left corner stop (Y 8.1): block from the wall to X {P.LOCATOR_X}, Z {P.LOCATOR_Z0}..{P.LOCATOR_Z}, '
         'facing the whole glass edge; the midplate notched under it', 'corner-stop-Y8.1.png')
    draw(items, 'x', 10.0, (-1.0, 16.0), (-4.2, 5.8),
         'Foot and neck (X 10.0): foot on the PS, neck over the PS end and the glass ledge, 90 deg over the glass edge '
         f'(Y 7.05), down the slot, hairpin on the back (bottom Z {rep["tail"]["back_loop"]["hairpin_bottom_z"]}), stiffened tail to J3',
         'foot-neck-X10.0.png')
    draw(items, 'y', 79.5, (-4.6, 6.0), (-0.6, 5.8),
         "Fold-back, across (Y 79.5): bar LED D2 on top, the folded pair's D7 below it facing -Z, midplate notched "
         "through under it", "fold-across-Y79.5.png")
    draw(items, 'x', 0.26, (70.0, 95.0), (1.4, 5.8),
         f'Fold-back, along the bar (X 0.26), relaxed fold (inside R{P.FOLD_RIN}): folded piece Y {rep["folded_piece_y"]}, '
         f'loop to Y {rep["loop_y_max"]}, Z {rep["loop_z_min"]}', 'fold-along-X0.26.png')
    items_t = _scene(tight)
    r45 = refs.strip_report(0.45)
    draw(items_t, 'x', 0.26, (70.0, 95.0), (1.4, 5.8),
         f'Fold-back, along the bar (X 0.26), tight fold (inside R0.45): folded piece Y {r45["folded_piece_y"]}, '
         f'loop to Y {r45["loop_y_max"]}', 'fold-along-X0.26-tight.png')
    draw(items_t, 'x', 8.4, (-1.0, 16.0), (-4.2, 5.8),
         'Neck beside SW9\'s pin (X 8.4) with the slack loop in the chin (1.65 past the glass edge) and a shorter hairpin',
         'neck-chin-loop-X8.4.png')
    t_nr = tub.build(ribs=False).val()
    items_w = _scene(VARIANTS['strip_wall'], tub_solid=t_nr)
    draw(items_w, 'y', 84.5, (-4.6, 6.0), (-0.6, 5.8),
         f'Strip at the wall (front shifted {P.STRIP_WALL_DX}, tub without its ribs), across at Y 84.5: folded D1 over the '
         'Y-83 latch arm', 'wall-case-Y84.5.png')
    draw(items, 'y', 84.5, (-4.6, 6.0), (-0.6, 5.8),
         'At the ribs (as modelled), across at Y 84.5: folded D1 beside the Y-83 latch arm', 'fold-arm-Y84.5.png')
    c = clearances(t_nr)
    (OUT / 'clearances.json').write_text(json.dumps({'report': rep, 'tight_fold': r45, 'clearances': c}, indent=1))
    print(json.dumps(c, indent=1))
