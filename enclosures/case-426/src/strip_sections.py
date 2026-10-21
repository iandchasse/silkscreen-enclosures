"""Light-strip builds: cross-sections through the built parts with the plain panel and the strip drawn in,
to out/<build>/light-strip-sections/. Run after build.py (it reads out/<build>/*.stl), from this project's
folder (enclosures/case-426) with the original project's venv (README.md, "Build"):

    python -B src/strip_sections.py                                     (light-strip, the default build)
    $env:SILKSCREEN_VARIANT = 'light-strip-chinless'; python -B src/strip_sections.py
A chinless light-strip build has no SW9 and no key_SW9 (no bottom keys): its sections leave them out.
"""
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MPath
import hw
import params as P
import refs

OUT = P.OUT / 'light-strip-sections'
STYLE = {   # name: (face, edge, alpha)
    'tub': ('#e8e1d0', '#6b6250', 1.0), 'lid': ('#d9d0bc', '#6b6250', 1.0), 'midplate': ('#8a958b', '#3f4a40', 1.0),
    'key_SW9': ('#c8553d', '#7a2e20', 1.0), 'PCB': ('#3f8f4f', '#1f4f28', 1.0), 'hw': ('#9a9a9a', '#444444', 1.0),
    'glass': ('#bcd9ee', '#4a7ea8', 1.0), 'fpl': ('#7fb0d8', '#355f86', 1.0), 'ps': ('#dcecf7', '#4a7ea8', 1.0),
    'strip_bar': ('#f28e2b', '#8a4a0c', 1.0), 'strip_leds': ('#ffd92f', '#8a6d00', 1.0), 'strip_copper': ('#b87333', '#5a3210', 1.0),
    'strip_tail': ('#f28e2b', '#8a4a0c', 1.0), 'strip_diodes': ('#4d4d4d', '#111111', 1.0),
    'strip_tail_reach': ('none', '#b5179e', 1.0), 'plain_fpc': ('#b08d57', '#5e4520', 1.0),
}


def tess(shape, tol=0.01):
    vs, ts = shape.tessellate(tol, 0.1)
    return trimesh.Trimesh([(v.x, v.y, v.z) for v in vs], ts, process=True)


def load():
    m = {n: trimesh.load(P.OUT / f'{n}.stl') for n in ('tub', 'lid', 'midplate', *(('key_SW9',) if P.BOTTOM_KEYS else ()))}
    for k, v in refs.plain_body().items():
        m[k] = tess(v.val())
    for k, v in refs.strip_front().items():
        m[k] = tess(v.val())
    t, _ = refs.strip_tail('nominal')
    m.update(t)
    m['strip_tail_reach'] = refs.strip_tail('reach')[0]['strip_tail']
    m['plain_fpc'] = refs.plain_fpc()
    hs = hw.solids()
    for r in ('PCB', 'SW9', 'J3', 'R50', 'H3'):
        if r in hs:                                 # SW9 is not in a chinless build's model (hw.DNP)
            m[r] = tess(hs[r], 0.02)
    return m


def plane(kind, c):
    """4x4 world -> plane frame: 'xz' at Y = c (2D = (X, Z)), 'yz' at X = c (2D = (Y, Z))."""
    if kind == 'xz':
        return np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, c], [0, 0, 0, 1]], float), (0, c, 0), (0, 1, 0)
    return np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, -c], [0, 0, 0, 1]], float), (c, 0, 0), (1, 0, 0)


def draw(ax, meshes, kind, c, window):
    M, origin, normal = plane(kind, c)
    x0, x1, z0, z1 = window
    order = ['lid', 'PCB', 'SW9', 'J3', 'R50', 'H3', 'midplate', 'glass', 'fpl', 'ps', 'plain_fpc', 'tub', 'key_SW9',
             'strip_bar', 'strip_copper', 'strip_leds', 'strip_tail', 'strip_diodes', 'strip_tail_reach']
    for name in order:
        if name not in meshes:
            continue
        sec = meshes[name].section(plane_origin=origin, plane_normal=normal)
        if sec is None:
            continue
        p2, _ = sec.to_planar(to_2D=M, check=False)
        fc, ec, a = STYLE.get(name, STYLE['hw'])
        geom = None                                               # even-odd fill of the closed loops
        for poly in p2.polygons_closed:
            if poly is None or not poly.is_valid or poly.area < 1e-6:
                continue
            geom = poly if geom is None else geom.symmetric_difference(poly)
        if geom is not None and not geom.is_empty:
            for poly in getattr(geom, 'geoms', [geom]):
                if poly.geom_type != 'Polygon':
                    continue
                b = poly.bounds
                if b[2] < x0 or b[0] > x1 or b[3] < z0 or b[1] > z1:
                    continue
                verts, codes = [], []
                for ring in [poly.exterior, *poly.interiors]:
                    c = np.asarray(ring.coords)
                    verts += c.tolist()
                    codes += [MPath.MOVETO] + [MPath.LINETO] * (len(c) - 2) + [MPath.CLOSEPOLY]
                ax.add_patch(PathPatch(MPath(verts, codes), fc=fc, ec=ec, lw=0.6, alpha=a,
                                       ls='--' if name == 'strip_tail_reach' else '-',
                                       zorder=3 if name.startswith('strip') else 2))
        else:                                                     # open section lines (thin meshes)
            for e in p2.discrete:
                ax.plot(e[:, 0], e[:, 1], color=ec, lw=0.6, ls='--' if name == 'strip_tail_reach' else '-', zorder=3)
    ax.set_xlim(x0, x1)
    ax.set_ylim(z0, z1)
    ax.set_aspect('equal')
    ax.grid(True, lw=0.3, alpha=0.4)
    ax.set_xlabel('X (mm)' if kind == 'xz' else 'Y (mm)')
    ax.set_ylabel('Z (mm)')


def annotate(ax, pts):
    for x, z, text in pts:
        ax.annotate(text, (x, z), xytext=(4, 4), textcoords='offset points', fontsize=6.5, color='#222222',
                    arrowprops=None, zorder=5)
        ax.plot([x], [z], marker='+', color='#222222', ms=4, zorder=5)


def fig(meshes, name, title, kind, c, window, notes=(), size=(9, 4.2)):
    f, ax = plt.subplots(figsize=size, dpi=200)
    draw(ax, meshes, kind, c, window)
    annotate(ax, notes)
    ax.set_title(title, fontsize=8)
    f.tight_layout()
    f.savefig(OUT / name)
    plt.close(f)
    print('wrote', OUT / name)


def main():
    if not P.LIGHT_STRIP:
        raise SystemExit(f'strip_sections.py draws the light-strip variant; SILKSCREEN_VARIANT is {P.VARIANT}')
    OUT.mkdir(parents=True, exist_ok=True)
    m = load()
    tail = refs.StripPath('nominal')
    reach = refs.StripPath('reach')
    fig(m, '1_led_D4_xz.png', f'XZ at Y 49.7 (LED D4): LED top {P.STRIP_LED_TOP:.3f} under the raised ceiling '
        f'{P.STRIP_CEIL["z"]:.2f}; skin {P.Z_FRONT - P.STRIP_CEIL["z"]:.2f}; light passes to the window edge X {P.WIN_X0:.2f}',
        'xz', 49.7, (-4.5, 4.0, 1.8, 6.3),
        [(0.96, P.STRIP_LED_TOP, f'LED face X 0.96, top {P.STRIP_LED_TOP:.3f}'),
         (P.WIN_X0, P.STRIP_CEIL['z'], f'ceiling {P.STRIP_CEIL["z"]:.2f} to window {P.WIN_X0:.2f} (bevel {P.WINDOW_BEVEL["left"]})'),
         (-1.71, 4.3, 'wall relief to X -1.71'), (-0.385, P.PLAIN_FRONT, 'PS edge -0.385')])
    fig(m, '2_holddown_xz.png', f'XZ at Y 45.25 (hold-down pad between D11 and D4): pad {P.STRIP_HOLD["z"]:.2f}, '
        f'{P.STRIP_HOLD["z"] - P.STRIP_FLEX_TOP:.3f} over the bar' + "'" + f's flex top {P.STRIP_FLEX_TOP:.3f}',
        'xz', 45.25, (-4.5, 4.0, 1.8, 6.3),
        [(P.STRIP_HOLD['x'][1], P.STRIP_HOLD['z'], f'pad X {P.STRIP_HOLD["x"][0]:.2f}..{P.STRIP_HOLD["x"][1]:.2f}'),
         (hw.PANEL_X0 + P.PLAIN['fpl_inset'][0], P.PLAIN_FRONT - P.PLAIN['ps'], f'FPL edge {hw.PANEL_X0 + P.PLAIN["fpl_inset"][0]:.3f}')])
    fig(m, '3_right_stop_xz.png', f'XZ at Y 60 (right border): stop X {P.WIN_X1}..59.3 on the PS at {P.PLAIN_FRONT:.3f}',
        'xz', 60.0, (55.5, 64.5, 1.8, 6.3), [(59.3, P.PLAIN_FRONT, f'stop on PS {P.PLAIN_FRONT:.2f}'), (59.185, P.PLAIN_FRONT - P.PLAIN['ps'], 'FPL edge')])
    fig(m, '4_foot_xz.png', 'XZ at Y 11.0 (foot): foot under the skin, its pad, the bottom stop from X 14.3',
        'xz', 11.0, (-4.5, 17.0, 1.8, 6.3), [(13.76, P.STRIP_FLEX_TOP, 'foot/neck edge 13.76'), (14.3, P.PLAIN_FRONT, 'bottom stop X 14.3')],
        size=(11, 3.6))
    fig(m, '5_neck_U_yz.png', f'YZ at X 11.0 (neck): drape to the ledge, U round the glass edge (nominal solid, reach dashed: '
        f'outer face Y {tail.u_reach_y:.2f} / {reach.u_reach_y:.2f}), slot, back run',
        'yz', 11.0, (-2.5, 12.5, -1.2, 6.3),
        [(tail.u_reach_y, tail.z_ledge - tail.C['R1'], 'U nominal'), (reach.u_reach_y, reach.z_ledge - reach.C['R1'] - 0.3, 'U reach'),
         (hw.PANEL_Y0, 3.5, 'glass edge 5.285'), (P.STRIP_HOLD['foot']['y'][0], P.STRIP_FLEX_TOP, 'foot pad')], size=(10, 5))
    fig(m, '6_tail_back_yz.png', 'YZ at X 11.0: the whole tail, slot to J3, against the lid and the board',
        'yz', 11.0, (-8.5, 26.0, -7.0, 6.5), [(23.25, -0.35, 'tip in J3'), (11.65, -1.6, 'diode')], size=(11, 4.6))
    fig(m, '7_chin_xz.png', 'XZ at Y 4.3 (chin, through the U): neck X 8.247..13.76 vs the gap edge 7.7'
        + (' and SW9\'s lug lead' if P.BOTTOM_KEYS else ' (no SW9: chinless)'),
        'xz', 4.3, (5.0, 16.0, 1.3, 6.3), [*([(8.147, 2.31, 'SW9 lug lead')] if P.BOTTOM_KEYS else []), (7.7, 4.5, 'gap edge 7.7')],
        size=(9, 4.2))
    fig(m, '8_back_diodes_xz.png', 'XZ at Y 11.65 (diodes on the tail\'s F side, facing the lid)',
        'xz', 11.65, (4.0, 18.0, -7.0, 2.2), [(12.1, -1.5, 'D13/D14 1.1 tall'), (10.0, -5.5, 'lid floor -5.5')], size=(9, 4.6))
    ys = ', '.join(f'{a}-{b}' for a, b in P.STRIP_HOLD['ys'])
    fig(m, '9_pads_lower_yz.png', f'YZ at X -0.04 (the LEDs line), Y 12-50: hold-downs ({P.STRIP_HOLD["z"]:.2f}) between the pairs, '
        'off the LED solder pads (copper, brown)', 'yz', -0.04, (12.0, 50.0, 3.4, 6.2),
        [(15.35, P.STRIP_HOLD['z'], 'pad to 15.35'), (15.95, P.STRIP_FLEX_TOP, 'D6 copper 15.95'), (28.5, P.STRIP_HOLD['z'], '28.5'),
         (30.9, P.STRIP_HOLD['z'], '30.9')], size=(12, 3.2))
    fig(m, '10_pads_top_yz.png', f'YZ at X -0.04, Y 86-111: the top piece, its pads under D1 and over the round end; pads {ys}',
        'yz', -0.04, (86.0, 111.0, 3.4, 6.2),
        [(94.0, P.STRIP_HOLD['z'], '94.0'), (95.15, P.STRIP_FLEX_TOP, 'D1 copper'), (107.7, P.STRIP_HOLD['z'], '107.7'),
         (93.975, P.STRIP_FLEX_TOP - 0.3, 'hinge end 93.975')], size=(12, 3.2))
    R = P.STRIP_WALL_RELIEF
    fig(m, '11_wall_relief_xz.png', f'XZ at Y 30 (left wall): relief {R["depth"]} deep, roof from Z {R["z0"]} rising {R["rise"]}, to Z {R["z1"]}; '
        'the bar 0.47 from it at nominal', 'xz', 30.0, (-3.6, 1.8, 2.8, 6.2),
        [(-1.71, R['z1'], 'relief X -1.71'), (P.POCKET_X0, R['z0'], f'roof starts {R["z0"]}'), (-1.24, P.STRIP_FLEX_TOP, 'bar edge -1.24')],
        size=(8, 4.6))


if __name__ == '__main__':
    main()
