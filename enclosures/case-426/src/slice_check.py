"""Slice every part with the installed OrcaSlicer and the stock Elegoo Centauri Carbon 2
profiles (0.4 nozzle, 0.20 mm Standard, Elegoo PLA), then report time/filament and plot
toolpaths of selected layers so thin features can be checked by eye, and read the G-code back over the
bottom keys' thin features: each must be laid down (or left open) in every layer it spans.

The bottom keys and the cranks print with supports off (test 1, 2026-09-29: Ian's rule), so for each of them the
G-code is also read for what would need one (no_support): no piece of a layer may start in mid-air (every piece
stands on the layer below, or on the bed), and no layer may reach out past the one below by more than
OVERHANG_REACH_MAX unless Orca lays it as a bridge (its Bridge role) no longer than BRIDGE_MAX; Orca's own 'Overhang
wall' and 'Bridge' roles are listed with their lengths. The tub and coupon-chin are read the same way over the chin
(chin_window: the chin wall, the hook keys' slots and the ledge, test 2), and every tub but the light-strip ones over
the screen window's 35-degree bevel (window_bevel: it prints face down, so the bevel is an overhang; the light-strip
tubs keep Rev K's 45-degree window); over the whole tub the rule is not held (Orca
lays bridges up to 40 mm in it and it reaches 0.53-0.87 past a layer by the gate slot and at a top corner, all older than
the slots, and it has printed). A side-key layout's tub and lid are read the same way over each closed wall, against a
plain stretch of the same wall (side_wall_no_support).

The bottom keys and the cranks print on a 2-layer raft (2026-10-06, Ian; make_plates.RAFT, set per object in the plate
file), so they are sliced on one here (RAFT, in process-key.json and process-crank.json). Every read-back takes the
part from its own bed face: the raft's layers (below the part's first, Orca's support roles only) are left out, and z
counts from the bottom of the part's first layer (raft_info), so the key reads as 50 layers from z 0, as on the bed.

The screws as printed (2026-10-13, as_printed; asprinted.py, the 3.68's module): the lid and the tub as sliced, the lid
at its as-printed home, each M2 x 10 (H3, H4, the top screw) on its seat: a socket head cap's (ISO 4762) and a pan
head's (ISO 7045) top flush with the back or below it, >= 3.0 mm in the pilot (also with the lid 0.3 open), the tip
short of the pilot's end and >= 0.8 from the front face. A FAIL there makes this script exit 1 (the read-backs above
are printed and read).

Orca's CLI does not resolve profile inheritance for files passed on the command line, so the
presets are flattened here first. Nothing is sent to a printer; G-code stays in out/slice/.
"""
import json, math, re, sys
from pathlib import Path
import hw
import params as P
import keys

ORCA = Path(r'C:\Program Files\OrcaSlicer\orca-slicer.exe')
PROFILES = Path(r'C:\Program Files\OrcaSlicer\resources\profiles')
OUT = P.OUT / 'slice'
OUT.mkdir(parents=True, exist_ok=True)
PRESETS = {'machine': 'Elegoo Centauri Carbon 2 0.4 nozzle',
           'process': '0.20mm Standard @Elegoo CC2 0.4 nozzle',
           'filament': 'Elegoo PLA @ECC2'}                   # Ian prints PLA
# Ian prints with no brim (the stock process has an auto brim 5 wide), so every read-back slice does too.
# The bottom keys and cranks print with elephant-foot compensation 0 (an OrcaSlicer per-object setting: the
# README's print steps): with the stock 0.1 the crank's 1.10 bed face printed 0.96 wide and the key's 0.5
# leaf dropped out of layer 1. 'small' is the process those parts are sliced with here.
NO_BRIM = {'brim_type': 'no_brim', 'brim_width': '0'}
SMALL_PROCESS = {'elefant_foot_compensation': '0'}
# 2026-10-06 (Ian: "maybe add 2-layer rafts to the buttons/cranks ... so that they don't unstick from the build
# plate"): the bottom keys and the cranks print on a 2-layer raft, which make_plates' plate file sets per object
# (make_plates.RAFT, the same three settings), so they are sliced on it here too, and every read-back drops the raft's
# layers and reads the part from its own bed face (raft_info)
RAFT = {'raft_layers': '2', 'raft_contact_distance': '0.2', 'raft_first_layer_expansion': '1'}
KEY_PROCESS = {**SMALL_PROCESS, **RAFT}
# the cranks also with Arachne walls (test 1, 2026-09-29): with classic walls Orca drops the inner loop in the 1.5
# cheeks and leaves voids at the ring's root; make_plates' plate file sets the same per object
CRANK_PROCESS = {**SMALL_PROCESS, 'wall_generator': 'arachne', **RAFT}


def small_part(name):
    return name.startswith(('crank-', 'key-')) or name == 'gate'


def raft_part(name):
    """make_plates.raft_part: the parts that print on a raft (RAFT)."""
    return name.startswith(('crank-', 'key-'))


RAFT_TYPES = ('Support', 'Support interface', 'Support transition')   # Orca's roles in a raft's layers
_RAFTS = {}


def raft_info(gcode):
    """The raft under the part in this G-code (RAFT): (shift, the raft's layers' z). The raft's layers are the ones below
    the part's first that hold only Orca's support roles (by role). The part's bed face is its first layer's top less
    that layer's own ;HEIGHT (the one its lines are laid with: the layer header's is the step from the raft's top, 0.4
    over the 0.2 gap), and the parsers here take every z from there and leave out the raft's layers (by Z), so a part on
    a raft reads as it would on the bed: its first layer at 0.2, its layers 0.2 apart. No raft: (0.0, [])."""
    g = Path(gcode)
    key = (str(g), g.stat().st_mtime_ns)
    if key not in _RAFTS:
        z, t, h, x, y, raft, first = 0.0, None, P.LAYER, 0.0, 0.0, set(), None
        for line in g.read_text(errors='ignore').splitlines():
            if line.startswith(';Z:'):
                z = float(line[3:])
            elif line.startswith(';TYPE:'):
                t = line[6:].strip()
            elif line.startswith(';HEIGHT:'):
                h = float(line[8:])
            elif line.startswith(('G1', 'G0')):
                v = dict((q[0], float(q[1:])) for q in line.split(';')[0].split()[1:] if q[0] in 'XYE' and len(q) > 1)
                nx, ny = v.get('X', x), v.get('Y', y)
                if line.startswith('G1') and v.get('E', 0) > 0 and (nx, ny) != (x, y) and t not in (None, 'Custom', 'Skirt', 'Brim'):
                    if t not in RAFT_TYPES:
                        first = (z, h)
                        break
                    raft.add(round(z, 3))
                x, y = nx, ny
        raft = sorted(r for r in raft if first and r < first[0] - 1e-6)
        _RAFTS[key] = (round(first[0] - first[1], 3), raft) if raft else (0.0, [])
    return _RAFTS[key]


def index():
    """{(kind, name): profile file} of every Orca profile: _index's, memoised (cache.py) by the stat of every file and
    folder under PROFILES and of the executable, so any change to the install is a miss."""
    import cache
    rel = cache.memo('orca-index', [cache.orca_signature(ORCA, PROFILES)],
                     lambda: {k: str(f.relative_to(PROFILES)) for k, f in _index().items()})
    return {k: PROFILES / f for k, f in rel.items()}


def _index():
    idx = {}
    for kind in ('machine', 'process', 'filament'):
        for f in PROFILES.rglob(f'{kind}/**/*.json'):
            try:
                d = json.loads(f.read_text(encoding='utf-8'))
            except Exception:
                continue
            if 'name' in d:
                idx.setdefault((kind, d['name']), f)
    return idx


def flatten(kind, name, idx):
    d = json.loads(idx[(kind, name)].read_text(encoding='utf-8'))
    parent = d.get('inherits')
    base = flatten(kind, parent, idx) if parent and (kind, parent) in idx else {}
    base.update({k: v for k, v in d.items() if k != 'inherits'})
    return base


def presets():
    idx = index()
    paths = {}
    for kind, name in PRESETS.items():
        d = flatten(kind, name, idx)
        # keep the stock names: the process and filament name the printers they are compatible
        # with, and Orca's CLI refuses a renamed machine ("found error, exit", nothing else)
        d['name'] = name
        d.pop('instantiation', None)
        if kind == 'machine' and 'G92 E0' not in (d.get('layer_gcode') or ''):
            d['layer_gcode'] = ((d.get('layer_gcode') or '') + '\nG92 E0').strip()   # relative-E check
        if kind == 'process':
            d.update(NO_BRIM)
            q = OUT / 'process-small.json'
            q.write_text(json.dumps({**d, **SMALL_PROCESS}, indent=1))
            paths['process-small'] = q
            q = OUT / 'process-crank.json'
            q.write_text(json.dumps({**d, **CRANK_PROCESS}, indent=1))
            paths['process-crank'] = q
            q = OUT / 'process-key.json'
            q.write_text(json.dumps({**d, **KEY_PROCESS}, indent=1))
            paths['process-key'] = q
        p = OUT / f'{kind}.json'
        p.write_text(json.dumps(d, indent=1))
        paths[kind] = p
    return paths


def slice_part(stl, pre):
    dest = OUT / stl.stem
    dest.mkdir(exist_ok=True)
    for old in dest.glob('*.gcode'):
        old.unlink()
    process = (pre['process-crank'] if stl.stem.startswith('crank-') else pre['process-key'] if raft_part(stl.stem) else
               pre['process-small'] if small_part(stl.stem) else pre['process'])
    cmd = [str(ORCA), '--orient', '0', '--arrange', '0', '--slice', '0', '--load-settings', f"{pre['machine']};{process}",
           '--load-filaments', str(pre['filament']), '--outputdir', str(dest), str(stl)]
    import cache                                        # memoised by the input files' bytes (cache.orca_run)
    if len(str(dest / 'plate_1.gcode')) >= cache.ORCA_PATH_MAX:   # Orca would fail to write it (exit -100)
        raise SystemExit(f"{dest / 'plate_1.gcode'}: {len(str(dest / 'plate_1.gcode'))} characters; OrcaSlicer fails at "
                         f'{cache.ORCA_PATH_MAX} or more: run from a checkout with a shorter path')
    r = cache.orca_run(cmd, dest, [stl, pre['machine'], process, pre['filament']], ORCA)
    g = next(dest.glob('*.gcode'), None)
    info = {'exit': r.returncode, 'gcode': str(g.relative_to(hw.ROOT)) if g else None,
            'process': {'elephant_foot_compensation': 0.0 if small_part(stl.stem) else 0.1, 'brim': 0,
                        'raft_layers': int(RAFT['raft_layers']) if raft_part(stl.stem) else 0}}
    if g:
        head = g.read_text(errors='ignore')
        for key, pat in {'time': r'estimated printing time \(normal mode\) = (.+)', 'grams': r'total filament used \[g\] = ([\d.]+)',
                         'layers': r'total layers count = (\d+)', 'filament_type': r'; filament_type = (\S+)',
                         'wall_generator': r'; wall_generator = (\S+)', 'raft_layers': r'; raft_layers = (\d+)',
                         'raft_contact_distance': r'; raft_contact_distance = (\S+)'}.items():
            m = re.search(pat, head)
            info[key] = m.group(1).strip() if m else None
        # 'layers' is the G-code's own count, the raft's included; the part's are the rest
        shift, raft = raft_info(g)
        info['raft'] = {'layers_z': raft, 'part_bed_face_z': shift}
        info['part_layers'] = int(info['layers']) - len(raft) if info.get('layers') else None
    return info


def plot_layers(gcode, zs, out_png, title):
    """Plot extrusion moves at the requested heights (nearest layer)."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    layers, cur, z, x, y, e_abs = {}, [], 0.0, 0.0, 0.0, True
    shift = raft_info(gcode)[0]                 # z from the part's bed face, the raft left out
    for line in Path(gcode).read_text(errors='ignore').splitlines():
        if line.startswith(';Z:') or line.startswith('; Z_HEIGHT:'):
            z = float(line.split(':')[1])
        if not line.startswith(('G1', 'G0')):
            if line.startswith('M83'):
                e_abs = False
            continue
        vals = dict((t[0], float(t[1:])) for t in line.split(';')[0].split()[1:] if t[0] in 'XYZE' and len(t) > 1)
        nx, ny = vals.get('X', x), vals.get('Y', y)
        if 'Z' in vals:
            z = vals['Z']
        if vals.get('E', 0) > 0 and line.startswith('G1') and (z - shift > 1e-6 or not shift):
            layers.setdefault(round(z - shift, 2), []).append(((x, y), (nx, ny)))
        x, y = nx, ny
    fig, axes = plt.subplots(1, len(zs), figsize=(6 * len(zs), 6))
    axes = axes if len(zs) > 1 else [axes]
    keys = sorted(layers)
    for ax, zt in zip(axes, zs):
        zl = min(keys, key=lambda k: abs(k - zt))
        for (a, b) in layers[zl]:
            ax.plot([a[0], b[0]], [a[1], b[1]], color='#c8553d', lw=0.6)
        ax.set_title(f'{title}  z={zl}')
        ax.set_aspect('equal')
        ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(out_png, dpi=110)
    plt.close(fig)


# ---- read-back: what the slicer actually lays down in the bottom keys' thin features (the crank spec's check 8)
# Each check is a box (or a bore) in the CAD frame, taken into the G-code's frame through the part's print
# orientation (plates.ORIENT) and Orca's placement (read off the outer walls). A box must have extrusion in
# every layer through it ('present') or none ('absent'); a line's material is its centreline +- half its width.
HALF_W = 0.21                                   # 0.42 walls


def parse(gcode):
    """{layer top z: [(x0, y0, x1, y1, type)]} for every extruding move. A part on a raft (RAFT): z from its bed face,
    the raft's layers left out (raft_info)."""
    layers, z, x, y, t = {}, 0.0, 0.0, 0.0, None
    shift = raft_info(gcode)[0]
    for line in Path(gcode).read_text(errors='ignore').splitlines():
        if line.startswith(';Z:'):
            z = round(float(line[3:]) - shift, 3)
        elif line.startswith(';TYPE:'):
            t = line[6:]
        elif line.startswith(('G1', 'G0')):
            v = dict((q[0], float(q[1:])) for q in line.split(';')[0].split()[1:] if q[0] in 'XYZE' and len(q) > 1)
            nx, ny = v.get('X', x), v.get('Y', y)
            if line.startswith('G1') and v.get('E', 0) > 0 and (nx, ny) != (x, y) and (z > 1e-6 or not shift):
                layers.setdefault(z, []).append((x, y, nx, ny, t))
            x, y = nx, ny
    return layers


class Frame:
    """CAD -> G-code: the print rotation, the shift that puts the oriented part at the origin, and Orca's
    offset on the bed (its outer walls above the first layer sit HALF_W inside the part's outline)."""

    def __init__(self, name, layers):
        import numpy as np, trimesh, plates
        self.R = np.eye(3)
        axis, deg = plates.ORIENT[name]
        if axis:
            vec = {'x': [1, 0, 0], 'y': [0, 1, 0], 'z': [0, 0, 1]}[axis]
            self.R = trimesh.transformations.rotation_matrix(np.radians(deg), vec)[:3, :3]
        m = trimesh.load(P.OUT / f'{name}.stl')
        v = m.vertices @ self.R.T
        self.lo = v.min(axis=0)
        walls = [s for z in sorted(layers)[1:] for s in layers[z] if s[4] in ('Outer wall', 'Overhang wall')]
        # the oriented part starts at 0 in X and Y at some layer above the first, where its outer wall runs
        # HALF_W inside the outline
        self.off = (min(min(s[0], s[2]) for s in walls) - HALF_W, min(min(s[1], s[3]) for s in walls) - HALF_W)

    def pt(self, p):
        import numpy as np
        q = self.R @ np.asarray(p, float) - self.lo
        return q[0] + self.off[0], q[1] + self.off[1], q[2]

    def box(self, b):
        import itertools
        c = [self.pt(p) for p in itertools.product(b[0:2], b[2:4], b[4:6])]
        return [min(q[i] for q in c) for i in range(3)], [max(q[i] for q in c) for i in range(3)]


def _layers_through(layers, z0, z1, h=0.2):
    return [z for z in sorted(layers) if z0 <= z - h / 2 <= z1]


def box_check(layers, fr, what, b, expect, join=2):
    """expect 'present' (in every layer through the box), 'absent' (in none) or 'somewhere' (in at least one:
    a feature whose tip falls between two layers' slice planes prints in whichever layer reaches it). join 1: the
    box grown by HALF_W with round corners, which is exactly where a line's material (+- HALF_W) reaches it; the
    default square corners reach 0.09 further at each corner, too far for a box set 0.06 inside a round end."""
    from shapely.geometry import LineString, box as sbox
    lo, hi = fr.box(b)
    zs = _layers_through(layers, lo[2], hi[2])
    rect = sbox(lo[0], lo[1], hi[0], hi[1]).buffer(HALF_W, join_style=join)
    hits = []
    for z in zs:
        hit = any(rect.intersects(LineString([(s[0], s[1]), (s[2], s[3])])) for s in layers[z])
        hits.append(hit)
    ok = bool(zs) and {'present': all, 'absent': lambda h: not any(h), 'somewhere': any}[expect](hits)
    return {'what': what, 'expect': expect, 'layers': len(zs), 'with_extrusion': int(sum(hits)), 'ok': bool(ok)}


def bore_check(layers, fr, what, axis_yz, x0, x1, d_min, n=5):
    """Free diameter of a hole along the CAD X axis: the largest circle round its axis clear of every layer's
    material (lines +- HALF_W, layers 0.2 thick), at n stations along it."""
    import numpy as np
    worst = 99.0
    for xs in np.linspace(x0 + 0.2, x1 - 0.2, n):
        c = fr.pt((xs, axis_yz[0], axis_yz[1]))
        for z in _layers_through(layers, c[2] - 2.0, c[2] + 2.0):
            # a layer's lines stand its full 0.2 (z - 0.2 .. z), so the chord that closes the hole is at the
            # layer's edge nearer the axis (|dz from mid-layer| - 0.1), not at mid-layer: a horizontal hole
            # prints in steps and each step's inner corner is what the rod meets
            dz = max(0.0, (z - 0.2) - c[2], c[2] - z)
            for x_0, y_0, x_1, y_1, _ in layers[z]:
                if max(x_0, x_1) < c[0] - 0.3 or min(x_0, x_1) > c[0] + 0.3:
                    continue
                if x_1 != x_0:                      # the part of the line within 0.3 of the station
                    ta = (c[0] - 0.3 - x_0) / (x_1 - x_0)
                    tb = (c[0] + 0.3 - x_0) / (x_1 - x_0)
                    ta, tb = max(0.0, min(ta, tb)), min(1.0, max(ta, tb))
                    ya, yb = y_0 + ta * (y_1 - y_0), y_0 + tb * (y_1 - y_0)
                else:
                    ya, yb = y_0, y_1
                ylo, yhi = min(ya, yb) - HALF_W, max(ya, yb) + HALF_W
                dy = max(0.0, ylo - c[1], c[1] - yhi)
                worst = min(worst, math.hypot(dy, dz))
    return {'what': what, 'free_d': round(float(2 * worst), 3), 'min_d': d_min, 'ok': bool(2 * worst >= d_min)}


def _part(s):
    """A move that is the part's own: not the brim, the skirt or the start G-code's purge line (Custom, at Z 0)."""
    return s[4] not in ('Brim', 'Skirt', 'Custom')


def first_part_layer(layers):
    return min(q for q in layers if any(_part(s) for s in layers[q]))


def first_layer(layers, fr, what, ax, w_min):
    """The part's own first layer across `ax` (0 X, 1 Y of the G-code), as laid: its outermost lines carried out by half
    their own ;WIDTH (parse_width's layers). The brim and skirt are not the part. Until 2026-10-06 this was the lines'
    centres apart plus 0.5 (the bed's first-layer line), which read the crank's pad end 1.092: Arachne lays it as one
    0.63 loop (1.227 as laid). On the raft (RAFT) the first layer is the part's first over it, at the layers' own widths
    (the crank's: two loops, 0.42-0.47, 1.226 as laid)."""
    z = first_part_layer(layers)
    segs = [s for s in layers[z] if _part(s)]
    w = max(max(s[ax], s[ax + 2]) + s[5] / 2 for s in segs) - min(min(s[ax], s[ax + 2]) - s[5] / 2 for s in segs)
    return {'what': what, 'layer_z': z, 'width': round(float(w), 3), 'min': w_min, 'ok': bool(w >= w_min)}


def no_bridge(layers, fr, what, b):
    """No bridge in the box: none of Orca's bridge moves ('Bridge', 'Internal Bridge') crosses its plan, any layer."""
    from shapely.geometry import LineString, box as sbox
    lo, hi = fr.box(b)
    rect = sbox(lo[0], lo[1], hi[0], hi[1])
    n = sum(1 for z in sorted(layers) if lo[2] - 0.2 <= z <= hi[2] + 0.2 for q in layers[z]
            if q[4] and 'Bridge' in q[4] and rect.intersects(LineString([(q[0], q[1]), (q[2], q[3])])))
    return {'what': what, 'bridge_moves': n, 'ok': n == 0}


def vbore_check(layers, fr, what, c, x0, x1, d_min):
    """Free diameter of a hole along the CAD X axis that prints vertical (the gate on its inner face): in every layer
    through x0..x1, the largest circle round the axis clear of every line (+- HALF_W)."""
    worst = 99.0
    a, b = fr.pt((x0, c[0], c[1])), fr.pt((x1, c[0], c[1]))
    z0, z1 = sorted((a[2], b[2]))
    for z in _layers_through(layers, z0 + 0.05, z1 - 0.05):
        for q in layers[z]:
            if not _part(q):
                continue
            x_0, y_0, x_1, y_1 = q[:4]
            dx, dy = x_1 - x_0, y_1 - y_0
            L2 = dx * dx + dy * dy
            u = 0.0 if L2 == 0 else max(0.0, min(1.0, ((a[0] - x_0) * dx + (a[1] - y_0) * dy) / L2))
            worst = min(worst, math.hypot(x_0 + u * dx - a[0], y_0 + u * dy - a[1]) - HALF_W)
    return {'what': what, 'free_d': round(float(2 * worst), 3), 'min_d': d_min, 'ok': bool(2 * worst >= d_min)}


def bevel_steps(layers, fr, what):
    """The gate's bevel as printed (on its inner face the bevel is its +print-X side): the part's reach that way may
    grow at most a layer's height per layer (45 degrees), +0.02 for the slicer's rounding."""
    zs = [z for z in sorted(layers) if any(_part(q) for q in layers[z])][1:]   # from layer 2: layer 1's lines are wider
    far = [max(max(q[0], q[2]) for q in layers[z] if _part(q)) for z in zs]
    steps = [(far[i] - far[i - 1], zs[i] - zs[i - 1]) for i in range(1, len(zs))]
    worst = max((d - h for d, h in steps), default=0.0)
    ang = max((math.degrees(math.atan2(d, h)) for d, h in steps if d > 0), default=0.0)
    return {'what': what, 'worst_step_minus_layer': round(worst, 3), 'steepest_deg': round(ang, 1), 'ok': worst <= 0.02}


def gate_slot_readback(layers, fr):
    """SPEC2 rev 3, check 9: the side gate's slot in the tub (and its coupon): the mouth, cavity and round ends open
    from the rim to the floor; the floor under the flange and the lips present; the sliver's hole; no bridges."""
    y, z = P.ROD_YZ
    S = P.GATE_SLOT
    out = [box_check(layers, fr, 'gate_mouth_open!', (-4.0, -3.1, -3.7, -1.3, -3.7, 0.5), 'absent'),
           box_check(layers, fr, 'gate_cavity_open!', (-2.9, -2.3, -4.2, -0.8, -3.7, 0.8), 'absent'),
           # the round ends' boxes: their outer corners are 0.06 inside the R0.40 arcs, so they are read with round corners
           box_check(layers, fr, 'gate_end_open! (-Y)', (-2.75, -2.45, -4.65, -4.40, -3.7, 0.8), 'absent', join=1),
           box_check(layers, fr, 'gate_end_open! (+Y)', (-2.75, -2.45, -0.60, -0.35, -3.7, 0.8), 'absent', join=1)]
    # the floor under the flange, 0.05-0.35 into the wall below its surface: the floor slopes 45 degrees, so in steps
    # 0.1 wide along X (each box from 0.05 below the step's highest floor to 0.35 below its lowest)
    xf, zf = P.ROD_STOP_X0, S['floor_z']
    for xa in (-2.9, -2.8, -2.7, -2.6):
        top, bot = zf + (xf - xa), zf + (xf - xa - 0.1)
        out.append(box_check(layers, fr, f'gate_floor X {xa:.1f}', (xa, xa + 0.1, -4.2, -3.9, top + 0.05, bot + 0.35), 'present'))
    for y0, y1 in ((-4.30, -3.95), (-1.05, -0.70)):
        out.append(box_check(layers, fr, f'lip y {y0:.2f}..{y1:.2f}', (-4.0, -3.1, y0, y1, P.SEAM + 0.05, zf + (xf + 3.1) - 0.05), 'present'))
    xc = P.X0 + S['lip'] + 2 * S['end_r']
    out.append(bore_check(layers, fr, 'sliver hole', (y, z), xc, P.POCKET_X0, 1.90, n=3))
    out.append(no_bridge(layers, fr, 'no bridges in the slot', (P.X0 - 0.1, xc + 0.8, -4.8, -0.2, P.SEAM - 1.5, 2.7)))
    return out


def cover_check(layers, fr, what, b, along=0, step=0.05):
    """The chin wall behind a hook slot across the slot's whole width, in every layer through the box: the share of
    the box's CAD X span (along=0) where some line's material (+- HALF_W) lies inside the box at that X. A slit
    anywhere across it would let one see into the slot (hverify2, 2026-09-30: the 4.26's rim layer did, in the seam's
    V, before KEY_SLOT relief)."""
    from shapely.geometry import LineString, box as sbox
    from shapely.ops import unary_union
    lo, hi = fr.box(b)
    rect = sbox(lo[0], lo[1], hi[0], hi[1])
    zs = _layers_through(layers, lo[2], hi[2])
    ax = 0 if abs(fr.pt((b[1], b[2], b[4]))[0] - fr.pt((b[0], b[2], b[4]))[0]) > 1e-6 else 1   # CAD X's G-code axis
    a0, a1 = lo[ax], hi[ax]
    n = max(1, int((a1 - a0) / step) + 1)
    worst = (1.0, None) if zs else (0.0, None)          # no layer through the box is a failure, not a pass
    for z in zs:
        mat = unary_union([LineString([(s[0], s[1]), (s[2], s[3])]).buffer(HALF_W) for s in layers[z]
                           if rect.buffer(HALF_W).intersects(LineString([(s[0], s[1]), (s[2], s[3])]))] or [rect.buffer(-9)])
        mat = mat.intersection(rect)
        hit = 0
        for i in range(n):
            c = a0 + (a1 - a0) * i / max(1, n - 1)
            cut = LineString([(c, lo[1]), (c, hi[1])]) if ax == 0 else LineString([(lo[0], c), (hi[0], c)])
            hit += cut.intersects(mat)
        if hit / n < worst[0]:
            worst = (hit / n, round(z, 2))
    return {'what': what, 'expect': 'across the width', 'layers': len(zs), 'cover_min': round(worst[0], 3),
            'at_layer': worst[1], 'ok': bool(zs) and worst[0] >= 1.0 - 1e-9}


def slot_readback(layers, fr, xc, ref):
    """The hook keys' two slots at key centre xc (test 2; params.KEY_SLOT): open from the rim up to the roof, the chin
    wall behind each present from the rim (no seam chamfer over the key row, KEY_SLOT relief) up to where the front
    round starts and, in the rim's layers, across the slot's whole width; the roof (the skin over the slot) present,
    and no bridge in them."""
    S = P.KEY_SLOT
    zr, rim = P.KEY_SLOT_ROOF, P.SEAM - 0.05                  # 0.05 past the seam: the box takes in the rim layer
    out = []
    for sd in (-1, 1):
        xa, xb = sorted((xc + sd * (S['dx'][0] + 0.25), xc + sd * (S['dx'][1] - 0.25)))
        out.append(box_check(layers, fr, f'{ref} slot {sd:+d} open, rim to roof!', (xa, xb, S['back'] + 0.20, P.BOT_IN - 0.20, P.SEAM + 0.1, zr - 0.1), 'absent'))
        out.append(box_check(layers, fr, f'{ref} slot {sd:+d} wall behind it', (xa, xb, S['back'] - 0.40, S['back'] - 0.05, rim,
                                                                            P.Z_FRONT - P.FRONT_EDGE_R), 'present'))
        wa, wb = sorted((xc + sd * S['dx'][0], xc + sd * S['dx'][1]))
        out.append(cover_check(layers, fr, f'{ref} slot {sd:+d} wall behind it across the slot, rim layers',
                               (wa, wb, S['back'] - 0.40, S['back'] - 0.02, rim, rim + 1.0)))
        out.append(box_check(layers, fr, f'{ref} slot {sd:+d} roof', (xa, xb, S['back'] + 0.1, P.BOT_IN - 0.1, zr + 0.05, zr + 0.35), 'present'))
        out.append(no_bridge(layers, fr, f'{ref} slot {sd:+d} no bridge', (xa, xb, S['back'], P.BOT_IN, P.SEAM, zr)))
    return out


def readback(name, gcode):
    """The spec's read-back boxes for the tub, the key, the cranks, the side gate and its coupon, and coupon-chin."""
    layers = parse(gcode)
    fr = Frame(name, layers)
    out = []
    if name == 'tub' and P.BOTTOM_KEYS:
        y, z = P.ROD_YZ
        for ref in P.KEY_REFS:
            xc = keys.key_x(ref)
            s0, s1 = P.SLOT
            # the spec's lip boxes (z 0.7-0.85 and -0.4..-0.3) each catch one slice plane just short of the lip's
            # tip; the lip prints in the next layer, so the box reaches one layer further on its side
            out.append(box_check(layers, fr, f'{ref} open seat, lip A', (xc - 1, xc + 1, -1.6, -1.5, 0.7, 0.85 + P.LAYER), 'somewhere'))
            out.append(box_check(layers, fr, f'{ref} open seat, lip B', (xc - 1, xc + 1, -2.7, -2.6, -0.4 - P.LAYER, -0.3), 'somewhere'))
            out.append(box_check(layers, fr, f'{ref} rail over the slot roofs', (xc + s0 + 0.3, xc + s1 - 0.3, -4.0, -0.7, P.SLOT_ROOF + 0.05, P.LIP - 0.05), 'present'))
            out.append(box_check(layers, fr, f'{ref} ledge (skin over the chin wall)', (xc - 4, xc + 4, P.BOT_IN + 0.05, P.KEY_OPENING['y'][0] - 0.05, P.LIP + 0.05, P.Z_FRONT - P.KEY_EDGE_CHAMFER - 0.05), 'present'))
            out.append(box_check(layers, fr, f'{ref} chin-wall lead-in', (xc - 4, xc + 4, P.BOT_IN - 0.25, P.BOT_IN - 0.05, P.SEAM, P.SEAM + 0.15), 'absent'))
            out += slot_readback(layers, fr, xc, ref)
        xs = [keys.key_x(r) for r in P.KEY_REFS]
        rings = [P.POCKET_X0 - 0.01] + [v for x in xs for v in (x - P.SLOT[1], x + P.SLOT[1])] + [P.RAIL_END_X]
        for i, (a, b) in enumerate(zip(rings[0::2], rings[1::2])):
            a1 = max(a, 0.2)
            out.append(box_check(layers, fr, f'ring {i} under its bore', (a1, b - 0.1, y - 0.2, y + 0.2, P.RAIL_RING_BOTTOM + 0.05, z - 1.15 - 0.05), 'present'))
            out.append(box_check(layers, fr, f'ring {i} +Y side', (a1, b - 0.1, y + 1.05, P.RAIL_Y[1] - 0.05, z - 0.2, z + 0.2), 'present'))
            out.append(box_check(layers, fr, f'ring {i} -Y side', (a1, b - 0.1, P.RAIL_Y[0] + 0.05, y - 1.05, z - 0.2, z + 0.2), 'present'))
            out.append(bore_check(layers, fr, f'ring {i} bore', (y, z), a1, b, 1.90))
        ws = [P.WEB_OUTER[0], *[v for x in xs for v in (x - P.SLOT[1], x + P.SLOT[1])], P.WEB_OUTER[1]]
        for i, (a, b) in enumerate(zip(ws[0::2], ws[1::2])):
            out.append(box_check(layers, fr, f'web {i}', (a + 0.2, b - 0.2, -8.1, -4.3, P.WEB_Z0 + 0.1, P.LIP - 0.05), 'present'))
        out += gate_slot_readback(layers, fr)
    elif name == 'tub':
        # no bottom keys (chinless): a plain chin. The chin wall in every layer through it, the skin over the chin, and
        # nothing between the chin wall and the pocket's bottom wall below the skin (no rail, rings, webs, slots)
        y1 = P.POCKET_Y0 - 1.0 - 0.3
        out.append(box_check(layers, fr, 'chin wall', (1.0, 59.0, P.Y0 + 0.1, P.BOT_IN - 0.1, P.SEAM + 0.5, P.Z_FRONT - P.FRONT_EDGE_R - 0.1), 'present'))
        out.append(box_check(layers, fr, 'skin over the chin', (6.3, 53.7, P.BOT_IN + 0.3, y1, P.LIP + 0.1, P.Z_FRONT - 0.5), 'present'))
        out.append(box_check(layers, fr, 'chin cavity empty (no rail, rings, webs, slots)', (6.3, 53.7, P.BOT_IN + 0.3, y1, P.SEAM + 0.1, P.LIP - 0.1), 'absent'))
        if P.ROD_YZ[0] - 0.3 > P.BOT_IN + 0.3:          # where the rod's hole would be, if the chin still reaches it
            out.append(box_check(layers, fr, 'no rod hole in the -X wall', (P.X0 + 0.3, P.POCKET_X0 - 0.3, P.ROD_YZ[0] - 0.3, P.ROD_YZ[0] + 0.3,
                                                                            P.ROD_YZ[1] - 0.3, P.ROD_YZ[1] + 0.3), 'present'))
    elif name == 'lid' and not P.BOTTOM_KEYS:
        # chinless: the H3 / H4 bosses run into the chin wall (each block in every layer from the floor to its top), the
        # tray between them open, the grip grooves open in the back face
        fps = hw.footprints()
        for ref in ('H3', 'H4'):
            hx, hy = fps[ref]['cad']
            out.append(box_check(layers, fr, f'{ref} boss merged into the chin wall', (hx - 2.7, hx + 2.7, P.BOT_IN + 0.1, 0.7, P.LID_FLOOR_IN + 0.1, -4.6), 'present'))
        out.append(box_check(layers, fr, 'tray open between the H3 / H4 blocks', (8.3, 51.7, P.BOT_IN + 0.3, 3.0, P.LID_FLOOR_IN + 0.25, P.SEAM - 0.1), 'absent'))
        g = P.GRIP_GROOVE
        for gy in P.GRIP_GROOVES_Y:
            out.append(box_check(layers, fr, f'grip groove at y {gy}', (g['x'][0] + 0.6, g['x'][1] - 0.6, gy - 0.1, gy + 0.1, P.Z_BACK + 0.05, P.Z_BACK + 0.3), 'absent'))
    elif name == 'coupon-chin':
        out += slot_readback(layers, fr, 0.0, 'coupon')
    elif name == 'coupon-gate':
        out += gate_slot_readback(layers, fr)
        y, z = P.ROD_YZ
        out.append(bore_check(layers, fr, 'left ring bore (to X 2.0)', (y, z), P.POCKET_X0, 2.0, 1.90, n=3))
    elif name == 'gate':
        # on its inner face: the flange is the first layer (nothing past the flat's end, z 0.90, where the bevel
        # starts); the bevel at most 45 degrees; the pull hole open; every wall round it 0.45 or more (0.60)
        G = P.GATE
        xf, zf = P.ROD_STOP_X0, P.GATE_SLOT['floor_z']
        yc = sum(G['web_y']) / 2
        out.append(box_check(layers, fr, 'flange in layer 1', (xf - 0.15, xf - 0.05, -3.5, -1.5, -3.0, 0.5), 'present'))
        out.append(box_check(layers, fr, 'nothing past the flat in layer 1', (xf - 0.15, xf - 0.05, -3.5, -1.5, zf + 0.3, zf + 1.0), 'absent'))
        out.append(bevel_steps(layers, fr, 'bevel <= 45 degrees'))
        out.append(vbore_check(layers, fr, 'pull hole', (yc, G['pull_z']), P.X0, P.X0 + G['pull_depth'], 1.15))
        w0, w1 = G['web_y']
        r = G['pull_d'] / 2
        for what, b in (('pull hole -Y wall', (w0 + 0.1, yc - r - 0.1)), ('pull hole +Y wall', (yc + r + 0.1, w1 - 0.1))):
            out.append(box_check(layers, fr, what, (P.X0 + 0.2, P.X0 + G['pull_depth'] - 0.1, b[0], b[1], G['pull_z'] - 0.3, G['pull_z'] + 0.3), 'present'))
        out.append(box_check(layers, fr, 'pull hole wall above', (P.X0 + 0.4, P.X0 + G['pull_depth'] - 0.1, yc - 0.3, yc + 0.3,
                                                                    P.SEAM + G['top_clr'] + 0.1, G['pull_z'] - r - 0.1), 'present'))
        wall = min((w1 - w0 - G['pull_d']) / 2, G['pull_z'] - r - (P.SEAM + G['top_clr']) - G['top_chamfer'])
        out.append({'what': 'thinnest wall round the pull hole (geometry, >= 0.45)', 'wall': round(wall, 3), 'ok': wall >= 0.45})
    elif name == 'key-426':
        # on its -X end (test 1), the hook key (test 2): both hooks laid in every layer through them (the -X one past the
        # bed end's two layers); the old leaf zone solid; the chin side cut back to the cap's face above the pusher's
        # stop; the pusher's chin end, the chin-side stop, below it
        H, pu, y0 = P.KEY_HOOK, P.KEY_PUSHER, P.KEY_CAP['y'][0]
        z0, z1 = P.KEY_HOOK_Z
        for sd in (-1, 1):
            xa, xb = sorted((sd * (H['dx'][0] + 0.1), sd * (H['dx'][1] - (0.1 if sd > 0 else 0.4))))
            out.append(box_check(layers, fr, f'hook {sd:+d}', (xa, xb, H['tip'] + 0.05, y0 - 0.05, z0 + 0.05, z1 - 0.05), 'present'))
        out.append(box_check(layers, fr, 'the old leaf zone, solid', (-4.4, 4.4, y0 + 0.08, P.KEY_PUSHER['y'][1] - 0.1, 1.0, P.Z_FRONT - 0.5), 'present'))
        out.append(box_check(layers, fr, 'chin side cut back above the stop!', (-4.4, 4.4, pu['y'][0] + 0.02, y0 - 0.12, pu['stop_z1'] + 0.25, z0 - 0.25), 'absent'))
        out.append(box_check(layers, fr, 'pusher chin end', (-4.4, 4.5, pu['y'][0] + 0.02, pu['y'][0] + 0.15, pu['z'][0] + 0.05, pu['stop_z1'] - 0.05), 'present'))
    elif name.startswith('crank-'):
        y, z = P.ROD_YZ
        var = name[-1]
        for s in (-1, 1):
            xc = s * (P.CRANK_CHEEK[0] + P.CRANK_CHEEK[1]) / 2
            x0, x1 = xc - 0.5, xc + 0.5
            out.append(box_check(layers, fr, f'cheek {s:+d} wall over the bore', (x0, x1, y - 0.2, y + 0.2, z + 1.0 + 0.05, z + 1.0 + 0.68), 'present'))
            out.append(box_check(layers, fr, f'cheek {s:+d} wall under the bore', (x0, x1, y - 0.2, y + 0.2, z - 1.0 - 0.68, z - 1.0 - 0.05), 'present'))
            out.append(box_check(layers, fr, f'cheek {s:+d} wall -Y of the bore', (x0, x1, y - 1.0 - 0.68, y - 1.0 - 0.05, z - 0.2, z + 0.2), 'present'))
            out.append(bore_check(layers, fr, f'cheek {s:+d} bore (before reaming)', (y, z), *sorted((s * P.CRANK_CHEEK[0], s * P.CRANK_CHEEK[1])), 1.80, n=3))
        cy, cz = P.CRANK_PAD['c']
        out.append(box_check(layers, fr, 'pad crown', (-5.0, 5.0, cy - 0.15, cy + 0.15, cz + 0.3, cz + 0.5), 'present'))
        ny, nz = P.CRANK_NOSE[var]
        out.append(box_check(layers, fr, 'nose', (-1.1, 1.1, ny + 0.5, ny + 0.8, nz - 0.15, nz + 0.15), 'present'))
        out.append(box_check(layers, fr, 'belly', (1.5, 3.4, -4.4, -3.2, -2.0, -1.5), 'present'))
        out.append(box_check(layers, fr, 'belly (-X)', (-3.4, -1.5, -4.4, -3.2, -2.0, -1.5), 'present'))
        out.append(first_layer(parse_width(gcode), fr, 'first layer across (device Z), as laid', 1, 1.0))
        # the cheek's closed ring (test 1): the ring's wall under the bore, inside the old C's sector, present; the
        # fill under the ring present; the lip's C (|dx| 3.75..4.05) still open. Boxes in dx from the crank's centre
        for s in (-1, 1):
            xs = sorted((s * 4.2, s * 5.1))
            out.append(box_check(layers, fr, f'ring closed where the C was {s:+d}', (*xs, -2.2, -1.7, -1.0, -0.3), 'present'))
            out.append(box_check(layers, fr, f'fill {s:+d}', (*xs, -2.8, -2.0, -2.1, -1.4), 'present'))
            out.append(box_check(layers, fr, f'lip C still open {s:+d}!', (*sorted((s * 3.8, s * 4.0)), -2.2, -1.7, -1.0, -0.3), 'absent'))
    if name in ('lid', 'midplate'):
        out += latch_readback(name, layers, fr)
    return out


def latch_readback(name, layers, fr):
    """2026-10-12, the lid closing (params.SNAP notch and SNAP_INNER_CHAMFER, lid_close.py), read back from the G-code:
      lid       each latch arm's inner top corner, chamfered 0.4 x 0.4: nothing over its inner part (d -0.72..-0.66 from
                the wall's inner face, where the square top's inner wall line lay) in the arm's top two layers (mid-planes
                Z 2.2 and 2.4); the arm itself there (d -0.28..-0.12) in the lower of them. Its top layer is 0.35 wide at
                Z 2.4 (lead-in to chamfer) and may drop out: the arm then ends 0.2 lower, well above the barb (whose flat
                ends at Z 1.7)
      midplate  each latch notch open to its 0.85 (nothing from 0.80 in to the edge, over the arm's width, in any layer;
                main's 0.7 notch left its edge's wall line there), and the right Y-100.3 notch run on into the Y-102
                spring's window (nothing between them in any layer: a 0.36 web would have printed only under the strip);
                and each detent strip beside a notch's end (midplate.detent_holds) still joined to the plate: in every
                layer above the first, the strip's lines (+- HALF_W) within DETENT_JOIN of the plate's (main and the held
                notches: 0.006, adjacent walls; the unheld 0.85 left 0.155 at the Y-14.9 strips). The first layer is
                not judged (0.11 on main, 0.24 held: Orca's first-layer outline)"""
    import joint, midplate
    out = []
    S = P.SNAP
    if name == 'lid':
        _, h = joint.snap_profile()
        zt = h['z_top']
        for wall, cs in P.SNAPS.items():
            w = joint.WALLS[wall]
            for c in cs:
                if (wall, c) not in P.SNAP_INNER_CHAMFER:
                    continue
                xs = sorted((w['face'] + w['out'] * -0.72, w['face'] + w['out'] * -0.66))
                xf = sorted((w['face'] + w['out'] * -0.28, w['face'] + w['out'] * -0.12))
                tag = f"{wall} Y{c:g}"
                out.append(box_check(layers, fr, f'latch arm {tag}: inner top corner chamfered (top two layers)!',
                                     (*xs, c - 1.5, c + 1.5, zt - 0.30, zt - 0.05), 'absent'))
                out.append(box_check(layers, fr, f'latch arm {tag}: the arm, the layer below its top',
                                     (*xf, c - 1.5, c + 1.5, zt - 0.30, zt - 0.20), 'present'))
    elif name == 'midplate':
        x0, x1 = P.POCKET_X0 + midplate.EDGE_CLR, P.POCKET_X1 - midplate.EDGE_CLR
        n = S['notch']
        z = (P.MID_REAR + 0.05, P.DISP_REAR - 0.05)
        notches = joint.midplate_notches()
        for wall, y0, y1 in notches:
            c = (y0 + y1) / 2
            xs = (x1 - n + 0.05, x1 - 0.05) if wall == 'right' else (x0 + 0.05, x0 + n - 0.05)
            out.append(box_check(layers, fr, f'midplate notch {wall} Y{c:g} open to {n}', (*xs, c - 2.25, c + 2.25, *z), 'absent'))
        for wall, y0, y1 in notches:
            for wx0, wx1, wy0, wy1 in midplate.spring_windows():
                a, b = max(y0, wy0), min(y1, wy1)
                web = (x1 - n) - wx1 if wall == 'right' else wx0 - (x0 + n)
                if b > a and 0.0 <= web < midplate.MIN_WEB:
                    xs = (wx1 + 0.05, x1 - 0.05) if wall == 'right' else (x0 + 0.05, wx0 - 0.05)
                    out.append(box_check(layers, fr, f'midplate notch {wall} Y{(y0 + y1) / 2:g} run on into the spring '
                                                     f'window (no {web:.2f} web)', (*xs, a + 0.3, b - 0.25, *z), 'absent'))
        for wall, y0, y1 in notches:
            for _, _, ya in midplate.detent_holds(wall, y0, y1):
                out.append(detent_join(layers, fr, wall, y1, ya))
    return out


DETENT_JOIN = 0.02


def detent_join(layers, fr, wall, y_end, ya):
    """Is the detent strip rooted at ya joined to the plate beside the notch that ends at y_end (latch_readback)? In the
    window from the plate's edge 2.0 in, Y y_end - 1.55 .. ya + 2.6, the lines (+- HALF_W) that reach a point on the
    strip (0.35 in, 1.9 past its root) and those that reach a point on the plate (1.6 in, 0.95 short of the notch's
    end), per layer."""
    from shapely.geometry import LineString, Point, box as sbox
    from shapely.ops import unary_union
    import midplate
    x0, x1 = P.POCKET_X0 + midplate.EDGE_CLR, P.POCKET_X1 - midplate.EDGE_CLR
    s = 1 if wall == 'right' else -1
    xe = x1 if s > 0 else x0
    xw = sorted((xe + s * 0.1, xe - s * 2.0))
    lo, hi = fr.box((*xw, y_end - 1.55, ya + 2.6, P.MID_REAR, P.DISP_REAR))
    win = sbox(lo[0], lo[1], hi[0], hi[1])
    a = fr.pt((xe - s * 0.35, ya + 1.9, (P.MID_REAR + P.DISP_REAR) / 2))
    c = fr.pt((xe - s * 1.6, y_end - 0.95, (P.MID_REAR + P.DISP_REAR) / 2))
    gaps = []
    for zl in _layers_through(layers, lo[2], hi[2]):
        segs = [g for g in (LineString([(q[0], q[1]), (q[2], q[3])]) for q in layers[zl]) if win.intersects(g)]
        mat = unary_union([g.buffer(HALF_W) for g in segs]).intersection(win) if segs else None
        comps = [] if mat is None or mat.is_empty else list(getattr(mat, 'geoms', [mat]))
        ca = [q for q in comps if q.distance(Point(a[:2])) < 0.15]
        cc = [q for q in comps if q.distance(Point(c[:2])) < 0.15]
        if ca and cc:
            gaps.append((zl, min(p.distance(q) for p in ca for q in cc)))
        elif ca or cc:
            gaps.append((zl, None))
    judged = [(zl, g) for zl, g in gaps if zl > min(layers)]
    ok = len(judged) >= 3 and all(g is not None and g <= DETENT_JOIN for _, g in judged)
    return {'what': f'midplate detent strip {wall} Y{ya:g} joined to the plate beside the notch ending Y{y_end:.2f} '
                    f'(layers 2+, gap <= {DETENT_JOIN})', 'expect': 'joined', 'layers': len(judged),
            'gaps': [None if g is None else round(g, 3) for _, g in gaps], 'ok': bool(ok)}


def latch_no_support(name, gcode):
    """The lid's latch arms (2026-10-12: chamfered tops): no_support over each arm, from the floor to above its top,
    from past its inner face to the barb's reach. Nothing may float, and the reach (the barb's 45-degree catch face,
    0.2 a layer) stays within OVERHANG_REACH_MAX or is a bridge."""
    import joint
    _, h = joint.snap_profile()
    rows, ok = {}, True
    for wall, cs in P.SNAPS.items():
        w = joint.WALLS[wall]
        xs = sorted((w['face'] + w['out'] * -0.9, w['face'] + w['out'] * 0.6))
        for c in cs:
            ns = no_support(name, gcode, (*xs, c - P.SNAP['w'] / 2 - 0.2, c + P.SNAP['w'] / 2 + 0.2,
                                          P.LID_FLOOR_IN + 0.3, h['z_top'] + 0.3))
            rows[f'{wall} Y{c:g}'] = {'floating': len(ns['floating']), 'reach_max_mm': ns['reach_max_mm'], 'ok': ns['ok']}
            ok = ok and ns['ok']
    return {'what': 'no support needed over the latch arms (chamfered tops): nothing floating, reach <= '
                    f'{OVERHANG_REACH_MAX} or a bridge', 'arms': rows, 'ok': ok}


# ---- test 1 (2026-09-29): the parts printed with supports off, the cranks' cheeks and the key on its end ------------
OVERHANG_REACH_MAX = 0.5                 # mm a layer may reach past the one below where it is not a bridge
BRIDGE_MAX = 5.0                         # mm: Orca's Bridge lines, anchored at both ends
FLOAT_MIN_ON = 0.2                       # a piece of a layer stands on the one below if this much of it is over it
NO_SUPPORT_PARTS = ('key-', 'crank-')
NO_SUPPORT_CHIN = ('tub', 'coupon-chin')            # over chin_window


def top_window(name, x=(44.0, 60.0)):
    """nodev (J6 not fitted): the top wall where the header's opening was, right of the top screw's boss, rim to face,
    in the tub and in the lid (each as it prints): read for what would need a support (top_no_support)."""
    return (x[0], x[1], P.TOP_IN - 3.0, P.Y1 + 0.5, P.Z_BACK - 0.5, P.Z_FRONT + 0.5)


def top_screw_window():
    """The lid round the top screw's counterbore (its boss, the stepped bridge, the lip ends either side), back face
    to rim (device box)."""
    tx, ty = P.TOP_SCREW
    return (tx - 4.0, tx + 4.0, ty - 4.0, P.Y1 + 0.5, P.Z_BACK - 0.5, P.SEAM + 0.5)


def top_no_support(name, gcode):
    """nodev: no_support over top_window, against the same read over its mirror on the left (x 0-16), the printed design
    the closed right half copies. Over either window the strict rule flags the same things: the front / back edge
    round's second layer (0.51-0.53) and lines cut by the window's own X edges (reach up to 1.2, at x = the edges), so
    the pass is: nothing floating, and the right reaches no further than the left (+0.02).
    The lid is also read round the top screw's counterbore (top_screw_window), where J6's cut used to clear the thin
    side of its boss: nothing may float there either. Its reach is not compared (the stepped bridge's layers are
    Orca's Bridge lines). Until variants C6 (2026-10-07) every nodev lid printed a 0.15 mm2 scrap of that wall in
    mid-air there (z 2.0, x 42.5, y 113.1), outside top_window, so this read did not see it."""
    xc = (P.X0 + P.X1) / 2
    right = no_support(name, gcode, top_window(name))
    left = no_support(name, gcode, top_window(name, (2 * xc - 60.0, 2 * xc - 44.0)))
    ok = not right['floating'] and right['reach_max_mm'] <= left['reach_max_mm'] + 0.02
    rep = {'what': 'no support needed over the closed top wall (nodev): nothing floating, reach <= its left mirror',
           'floating': len(right['floating']), 'reach_max_mm': right['reach_max_mm'], 'reach_at': right['reach_at'],
           'left_mirror_reach_max_mm': left['reach_max_mm'], 'left_mirror_reach_at': left['reach_at'],
           'roles': right['roles'], 'ok': ok}
    if name == 'lid':
        cb = no_support(name, gcode, top_screw_window())
        rep['what'] += "; nothing floating round the top screw's counterbore"
        rep['counterbore_floating'] = cb['floating']
        rep['ok'] = ok and not cb['floating']
    return rep


SIDE_PLAIN_WINDOW_Y = {-1: (29.0, 36.0), +1: (27.2, 31.2)}   # a plain stretch of each side wall: no key, latch, port or
                                                             # reset hole


def side_wall_windows():
    """A side-key layout (SIDES != 'all'): over each key it leaves out, the closed wall from 0.5 outside the case's
    face to 1.5 into the cavity (the lid's leg, groove and lip; the tub's tongue), over the key's whole span (its lid
    cut and foot chamfer, the tub's slot and the nub window: body.tab_span_y, as build.side_zone, +0.5), every z, in
    the tub and in the lid (each as it prints): {ref: device box}."""
    import body
    out = {}
    for t in body.side_tabs(P.TAB_ROOTS_ALL):
        if t['ref'] in P.TAB_ROOTS:
            continue
        y0, y1 = body.tab_span_y(t)
        x = (P.X0 - 0.5, P.POCKET_X0 + 1.5) if t['side'] < 0 else (P.POCKET_X1 - 1.5, P.X1 + 0.5)
        out[t['ref']] = (*x, y0 - 0.5, y1 + 0.5, P.Z_BACK - 0.5, P.Z_FRONT + 0.5)
    return out


def side_wall_no_support(name, gcode):
    """A side-key layout: no_support over each left-out key's closed wall (side_wall_windows), against the same read
    over a plain stretch of the same wall (SIDE_PLAIN_WINDOW_Y), which is the printed design the closed wall copies.
    Either way the strict rule flags only the front / back edge round's second layer (0.50-0.52), so the pass is:
    nothing floating over a closed wall, and it reaching no further than the plain wall (+0.02). Orca's bridge and
    overhang lines near a window (within 1 mm, e.g. the foot room under a kept neighbour's free end) are listed."""
    rows, ok = {}, True
    for ref, win in side_wall_windows().items():
        s = -1 if win[0] < P.X0 else 1
        ns = no_support(name, gcode, win)
        ref_ns = no_support(name, gcode, (win[0], win[1], *SIDE_PLAIN_WINDOW_Y[s], win[4], win[5]))
        good = not ns['floating'] and ns['reach_max_mm'] <= ref_ns['reach_max_mm'] + 0.02
        rows[ref] = {'floating': len(ns['floating']), 'reach_max_mm': ns['reach_max_mm'], 'reach_at': ns['reach_at'],
                     'plain_wall_reach_max_mm': ref_ns['reach_max_mm'], 'roles': ns['roles'], 'ok': good}
        ok = ok and good
    return {'what': 'no support needed over the closed side walls (keys left out): nothing floating, reach <= the plain '
                    'wall', 'keys': rows, 'ok': ok}


def device_layers(name, gcode, ends='flat'):
    """A sliced part back in the CAD frame: [(c, polygon)], one per layer, c its mid-plane along the CAD axis the
    print's Z runs along (X for the key on its -X end, Y for the cranks on their pad end, Z for the case parts), the
    polygon in the other two CAD axes in order ((y, z), (x, z) or (x, y)): each of the part's extruding lines buffered
    by half its width (;WIDTH), merged. ends 'flat' stops a line at its end points (the widths across walls and slots);
    'round' carries it half a width past, as deposited."""
    import numpy as np
    from shapely.geometry import LineString
    from shapely.ops import unary_union
    layers = parse_width(gcode)
    fr = Frame(name, layers)
    R = np.asarray(fr.R)
    ax = int(np.argmax(np.abs(R[2, :])))
    assert abs(abs(R[2, ax]) - 1) < 1e-9, name          # the print's Z is one of the part's own axes
    keep = [i for i in range(3) if i != ax]
    out = []
    for z in sorted(layers):
        segs = [s for s in layers[z] if _part(s)]
        if not segs:
            continue
        g0 = np.array([[s[0] - fr.off[0] + fr.lo[0], s[1] - fr.off[1] + fr.lo[1], z - P.LAYER / 2 + fr.lo[2]] for s in segs]) @ R
        g1 = np.array([[s[2] - fr.off[0] + fr.lo[0], s[3] - fr.off[1] + fr.lo[1], z - P.LAYER / 2 + fr.lo[2]] for s in segs]) @ R
        gs = [LineString([g0[i, keep], g1[i, keep]]).buffer(s[5] / 2, cap_style=1 if ends == 'round' else 2,
                                                            join_style=1 if ends == 'round' else 2)
              for i, s in enumerate(segs) if abs(g0[i, keep[0]] - g1[i, keep[0]]) + abs(g0[i, keep[1]] - g1[i, keep[1]]) > 1e-6]
        out.append((round(float(g0[0, ax]), 3), unary_union(gs)))
    return out


def _runs(g, p0, p1):
    """Material along the line p0 -> p1 (along the first or the second axis): merged (start, end) runs in the
    coordinate that varies."""
    from shapely.geometry import LineString
    i = 0 if abs(p1[0] - p0[0]) > abs(p1[1] - p0[1]) else 1
    hit = LineString([p0, p1]).intersection(g)
    rs = []
    for q in getattr(hit, 'geoms', [hit]):
        if q.geom_type in ('LineString', 'LinearRing') and q.length > 1e-6:
            c = [v[i] for v in q.coords]
            rs.append((min(c), max(c)))
    out = []
    for a, b in sorted(rs):
        if out and a <= out[-1][1] + 1e-6:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def _gap_at(rs, t, open_=9.0):
    """The free width round t between material runs: 0 if t is in material, open_ if nothing bounds it on a side."""
    if any(a <= t <= b for a, b in rs):
        return 0.0
    lo = [b for a, b in rs if b <= t]
    hi = [a for a, b in rs if a >= t]
    return (min(hi) - max(lo)) if lo and hi else open_


# the tub's and coupon-chin's no-support window (device frame): the chin across the four keys, from the outer face to the
# opening's chin edge (the chin wall, the hook keys' slots and the ledge), from below the rim to 0.5 over the slots' roof:
# the layers the slots change. The face's first layers there (the R1.8 front round starting under the key openings' 0.3
# chamfer: little of layer 1 is in the window, so layer 2 reads as floating in it) predate the slots and print
def chin_no_support(name, gcode):
    """chinless: no_support over the whole plain chin between the plan corners (wall to wall, rim to face, up to the
    pocket's bottom wall), against the same read over the two lower plan corners, which are the printed design. Every
    tub's front edge round where it meets a plan corner steps 0.51 in its second layer (just over OVERHANG_REACH_MAX,
    in every printed tub), so the pass is: nothing floating anywhere, and the chin reaching no further than the
    corners (+0.02). Bridges over the wordmark's engraving are Orca's Bridge lines, as on every tub."""
    r = P.CORNER_R
    chin = no_support(name, gcode, (P.X0 + r, P.X1 - r, P.Y0 - 0.5, P.POCKET_Y0 - 1.0, P.SEAM - 0.5, P.Z_FRONT + 0.5))
    corners = [no_support(name, gcode, (x0, x1, P.Y0 - 0.5, P.Y0 + r, P.SEAM - 0.5, P.Z_FRONT + 0.5))
               for x0, x1 in ((P.X0 - 0.5, P.X0 + r + 0.5), (P.X1 - r - 0.5, P.X1 + 0.5))]
    ref = max(c['reach_max_mm'] for c in corners)
    ok = not chin['floating'] and not any(c['floating'] for c in corners) and chin['reach_max_mm'] <= ref + 0.02
    return {'what': 'no support needed over the plain chin (chinless): nothing floating, reach <= the plan corners',
            'floating': len(chin['floating']) + sum(len(c['floating']) for c in corners), 'reach_max_mm': chin['reach_max_mm'],
            'reach_at': chin['reach_at'], 'corners_reach_max_mm': ref, 'roles': chin['roles'], 'ok': ok}


def lid_chin_no_support(name, gcode):
    """chinless: no_support over the lid's short chin between the plan corners (the H3 / H4 blocks run into the chin
    wall, their counterbores' stepped bridges, the grip grooves; back face to rim, from the outer face to y 9), against
    the same read over the lid's two lower plan corners and over the top screw's counterbore, which carry the printed
    design's back-edge round and stepped bridge. Pass: nothing floating over the chin, and the chin reaching no
    further than those (+0.02). The references' own floating pieces are reported, not judged here: they are the rest
    of the lid's (the counterbore's is judged by top_no_support on a nodev lid, which had a 0.15 mm2 one there, at
    x 42.5, until variants C6)."""
    r = P.CORNER_R
    chin = no_support(name, gcode, (P.X0 + r, P.X1 - r, P.Y0 - 0.5, 9.0, P.Z_BACK - 0.5, P.SEAM + 0.5))
    refs = [no_support(name, gcode, (x0, x1, P.Y0 - 0.5, P.Y0 + r, P.Z_BACK - 0.5, P.SEAM + 0.5))
            for x0, x1 in ((P.X0 - 0.5, P.X0 + r + 0.5), (P.X1 - r - 0.5, P.X1 + 0.5))]
    refs.append(no_support(name, gcode, top_screw_window()))
    ref = max(c['reach_max_mm'] for c in refs)
    ok = not chin['floating'] and chin['reach_max_mm'] <= ref + 0.02
    return {'what': "no support needed over the lid's short chin (chinless): nothing floating, reach <= the lower plan "
                    "corners and the top screw's counterbore",
            'floating': len(chin['floating']), 'reach_max_mm': chin['reach_max_mm'], 'reach_at': chin['reach_at'],
            'reference_reach_max_mm': [c['reach_max_mm'] for c in refs],
            'reference_floating': [f for c in refs for f in c['floating']], 'roles': chin['roles'], 'ok': ok}


def window_bevel_windows():
    """The screen window's bevel band (tub.window, the builds without the light strip) through the skin: the middle of
    the right, top and bottom edges and the top-right corner (the left edge mirrors the right). Device boxes, clear of
    the wordmark and the top screw. They start just above the lip (LIP + 0.05; no_support reads one layer more on each
    side, so the lip's layer is in), so the light-strip tub's panel stop rails, which hang from the lip under the
    window's edges, would stay out of them."""
    m, W, z = 1.0, P.WINDOW_BEVEL_W, (P.LIP + 0.05, P.Z_FRONT + 0.5)
    return {'right': (P.WIN_X1 - m, P.WIN_X1 + W + m, 40.0, 80.0, *z),
            'top': (15.0, 35.0, P.WIN_Y1 - m, P.WIN_Y1 + W + m, *z),
            'bottom': (20.0, 40.0, P.WIN_Y0 - W - m, P.WIN_Y0 + m, *z),
            'top-right corner': (P.WIN_X1 - 3.0, P.WIN_X1 + W + m, P.WIN_Y1 - 3.0, P.WIN_Y1 + W + m, *z)}


def window_bevel(name, gcode):
    """The screen window's bevel as the tub prints it, face down (no_support over window_bevel_windows): nothing floats
    and no layer reaches past the one below by more than OVERHANG_REACH_MAX. Each layer steps 0.2 / tan(the bevel's
    angle): 0.29 at 35 degrees (0.39 on the second layer, with Orca's 0.1 elephant-foot pull-back), 0.35 at 30; at 25
    the step is wider than the outer wall and Orca hangs it as an overhang wall (reach 0.52: FAIL)."""
    out = {n: no_support(name, gcode, w) for n, w in window_bevel_windows().items()}
    return {'what': 'screen window bevel prints without support (right, top, bottom edges, top-right corner)',
            'reach_max_mm': {n: r['reach_max_mm'] for n, r in out.items()},
            'floating': sum(len(r['floating']) for r in out.values()),
            'roles': {n: r['roles'] for n, r in out.items() if r['roles']},
            'ok': all(r['ok'] for r in out.values())}


def chin_window(name):
    if name == 'coupon-chin':
        x0, x1 = -P.SLOT[1] - 0.6, P.SLOT[1] + 0.6
    else:
        xs = [keys.key_x(r) for r in P.KEY_REFS]
        x0, x1 = min(xs) - P.SLOT[1] - 0.6, max(xs) + P.SLOT[1] + 0.6
    return (x0, x1, P.Y0 - 0.5, P.KEY_OPENING['y'][0] + 0.05, P.SEAM - 0.5, P.KEY_SLOT_ROOF + 0.5)


def no_support(name, gcode, window=None):
    """What a part printed with supports off would need one for, read off its G-code in the print frame (test 1, Ian's
    rule). Each layer's material: its lines at their widths, round ends, merged.
      floating   pieces of a layer with less than FLOAT_MIN_ON of their area over the layer below: nothing may start in
                 mid-air (the first layer is on the bed)
      reach      how far a layer's material reaches past the layer below's (the largest distance from it of any point
                 of the layer): a 45-degree face steps 0.2, a flat overhang reaches as far as it hangs. Where it is over
                 OVERHANG_REACH_MAX the layer must lay it as Orca's Bridge, each line <= BRIDGE_MAX and both its ends
                 on the layer below (a bridge)
      roles      Orca's 'Overhang wall', 'Bridge' and 'Internal Bridge' lines: count, total and longest length, and
                 where (print frame)
    Pass: no floating piece, and every reach over OVERHANG_REACH_MAX a bridge. Places ('at') are in the CAD frame.
    window: a device box (x0, x1, y0, y1, z0, z1): only the part of each layer inside it, and only its layers."""
    import numpy as np
    from shapely.geometry import LineString, Point, box as sbox
    from shapely.ops import unary_union
    layers = parse_width(gcode)
    fr = Frame(name, layers)
    clip = None
    if window is not None:
        lo, hi = fr.box(window)
        clip = sbox(lo[0], lo[1], hi[0], hi[1])
        near = clip.buffer(1.0)
        layers = {z: v for z, v in layers.items() if lo[2] - P.LAYER <= z <= hi[2] + P.LAYER}

    def cad(p, z):
        q = np.asarray(fr.R).T @ np.array([p[0] - fr.off[0] + fr.lo[0], p[1] - fr.off[1] + fr.lo[1], z - P.LAYER / 2 + fr.lo[2]])
        return [round(float(v), 2) for v in q]
    zs = [z for z in sorted(layers) if any(_part(s) for s in layers[z])]
    prev, floating, reach, roles, bad = None, [], (0.0, None), {}, []
    for z in zs:
        segs = [s for s in layers[z] if _part(s) and (s[0], s[1]) != (s[2], s[3])]
        if clip is not None:
            segs = [s for s in segs if near.intersects(LineString([(s[0], s[1]), (s[2], s[3])]))]
        g = unary_union([LineString([(s[0], s[1]), (s[2], s[3])]).buffer(s[5] / 2, cap_style=1) for s in segs])
        if clip is not None:
            g = g.intersection(clip)
        for s in segs:
            if s[4] in ('Overhang wall', 'Bridge', 'Internal Bridge'):
                L = math.hypot(s[2] - s[0], s[3] - s[1])
                r = roles.setdefault(s[4], {'lines': 0, 'mm': 0.0, 'longest': 0.0, 'layers': set()})
                r['lines'] += 1
                r['mm'] += L
                r['longest'] = max(r['longest'], L)
                r['layers'].add(z)
        if prev is not None:
            for q in [q for q in getattr(g, 'geoms', [g]) if q.area > 0.005]:
                if q.intersection(prev).area < FLOAT_MIN_ON * q.area:
                    floating.append({'z': z, 'mm2': round(q.area, 3), 'at': cad(q.centroid.coords[0], z)})
            un = g.difference(prev)
            for q in [q for q in getattr(un, 'geoms', [un]) if q.geom_type == 'Polygon' and q.area > 1e-4]:
                far = max((prev.distance(Point(p)), p) for p in q.exterior.coords)
                if far[0] > reach[0]:
                    reach = (far[0], {'z': z, 'at': cad(far[1], z)})
                if far[0] > OVERHANG_REACH_MAX:
                    # a bridge: Orca's Bridge lines over it, each <= BRIDGE_MAX with both ends on the layer below
                    br = [s for s in segs if 'Bridge' in (s[4] or '') and LineString([(s[0], s[1]), (s[2], s[3])]).intersects(q)]
                    ok = bool(br) and all(math.hypot(s[2] - s[0], s[3] - s[1]) <= BRIDGE_MAX and
                                          prev.distance(Point(s[0], s[1])) < 0.25 and prev.distance(Point(s[2], s[3])) < 0.25
                                          for s in br)
                    if not ok:
                        bad.append({'z': z, 'reach': round(far[0], 3), 'at': cad(far[1], z),
                                    'bridge_lines': len(br)})
        prev = g
    roles = {n: {'lines': r['lines'], 'mm': round(r['mm'], 2), 'longest_mm': round(r['longest'], 2), 'layers': len(r['layers']),
                 'z': [min(r['layers']), max(r['layers'])]} for n, r in roles.items()}
    return {'layers': len(zs), 'window': window, 'floating': floating, 'reach_max_mm': round(reach[0], 3), 'reach_at': reach[1],
            'reach_over_limit_not_a_bridge': bad[:6], 'roles': roles,
            'ok': not floating and not bad}


KEY_BED_AREA_MIN = 7.5                  # mm2: the key's first layer on the bed (on its -X end, 10.0 tall); on the raft
                                         # (RAFT, 2026-10-06) the part's first layer over it
CHEEK_SLICED_MIN = 0.90                  # the sliced cheek over its designed section, every layer through the bore
CHEEK_LAYERS_Y = (-3.0, -1.4)            # device y of those layers' mid-planes (the crank prints +Y up)
HOOK_COVER_MIN = 0.75                    # a hook's section covered by lines, every layer through it
HOOK_SLICED_TOL = 0.05                   # a hook's tip and top as sliced, off the CAD


def key_first_layer(name, gcode):
    """The key stands on its -X end (test 1): its first layer's area as deposited (its lines at their widths, round
    ends) >= KEY_BED_AREA_MIN, and all of it inside the key's outline there (its section 0.45 in, through the -X hook):
    KEY_BED_END's 0.30 keeps the squashed first layer in. On the raft (RAFT, 2026-10-06) it is the key's first layer
    over the raft (raft_info), laid at the layers' own widths, not the bed's 0.5."""
    import trimesh
    from shapely.geometry import Point
    c1, g1 = min(device_layers(name, gcode, ends='round'), key=lambda q: q[0])
    sec = keys.section(trimesh.load(P.OUT / f'{name}.stl'), -P.KEY_CAP['half'] + 0.45)
    outside = g1.difference(sec)
    far = max([Point(q).distance(sec) for g in getattr(outside, 'geoms', [outside]) if not g.is_empty and g.geom_type == 'Polygon'
               for q in g.exterior.coords] or [0.0])
    on = 'the raft' if raft_info(gcode)[1] else 'the bed'
    return {'what': f'first layer on {on}: >= {KEY_BED_AREA_MIN} mm2, inside the outline', 'layer_dx': c1,
            'area_mm2': round(g1.area, 2), 'outside_outline_mm2': round(outside.area, 4), 'outside_outline_max_mm': round(far, 3),
            'ok': g1.area >= KEY_BED_AREA_MIN and outside.area <= 0.005}


def crank_sections(name, gcode):
    """The crank's cheeks as sliced against their designed section, every layer whose mid-plane is in CHEEK_LAYERS_Y
    (the bore's layers): in the cheek's band (|dx| 3.55..5.45) the area of the layer's lines (at their widths, round
    ends) inside the model's section there, over the section's area. >= CHEEK_SLICED_MIN in every layer and both
    cheeks. It also shows the Arachne walls are in: classic walls drop the inner loop in the 1.5 cheek (the crank
    study: 83 % stock, 91.6 % Arachne)."""
    import trimesh
    from shapely.geometry import Polygon, box as sbox
    m = trimesh.load(P.OUT / f'{name}.stl')
    rows = []
    for c, g in device_layers(name, gcode, ends='round'):
        if not CHEEK_LAYERS_Y[0] - 1e-6 <= c <= CHEEK_LAYERS_Y[1] + 1e-6:
            continue
        s = m.section(plane_origin=[0, c, 0], plane_normal=[0, 1, 0])
        sec = Polygon()
        for loop in (s.discrete if s is not None else []):
            if len(loop) >= 3:
                sec = sec.symmetric_difference(Polygon(loop[:, [0, 2]]).buffer(0))
        for sd in (1, -1):
            des = sec.intersection(sbox(min(sd * 3.55, sd * 5.45), -9, max(sd * 3.55, sd * 5.45), 9))
            if des.area > 0:
                rows.append({'y': c, 'cheek': f'{sd:+d}', 'designed_mm2': round(des.area, 3),
                             'fraction': round(des.intersection(g).area / des.area, 3)})
    w = min(rows, key=lambda r: r['fraction']) if rows else None
    return {'what': f'cheek as sliced >= {CHEEK_SLICED_MIN} of its section, every layer y {CHEEK_LAYERS_Y}', 'layers': len(rows),
            'worst': w, 'ok': bool(rows) and w['fraction'] >= CHEEK_SLICED_MIN}


def _seams(name, gcode):
    """Where each outer-wall loop starts (Orca's seam), CAD frame: (the layer's mid-plane along the print's Z axis, and
    the other two axes)."""
    import numpy as np
    layers = parse_width(gcode)
    fr = Frame(name, layers)
    R = np.asarray(fr.R)
    ax = int(np.argmax(np.abs(R[2, :])))
    keep = [i for i in range(3) if i != ax]
    out = []
    for z in sorted(layers):
        end = None
        for s in layers[z]:
            if s[4] == 'Outer wall' and (end is None or math.hypot(s[0] - end[0], s[1] - end[1]) > 1e-3):
                q = np.array([s[0] - fr.off[0] + fr.lo[0], s[1] - fr.off[1] + fr.lo[1], z - P.LAYER / 2 + fr.lo[2]]) @ R
                out.append((round(float(q[ax]), 2), round(float(q[keep[0]]), 3), round(float(q[keep[1]]), 3)))
            end = (s[2], s[3]) if s[4] == 'Outer wall' else None
    return out


def key_on_end(name, gcode):
    """The key printed on its -X end (test 1), the hook key (test 2): in every layer through a hook (the -X one past the
    bed end's two layers), the hook's section (y tip..the cap's chin face, z its bottom..top) covered by lines as
    deposited (round ends) >= HOOK_COVER_MIN, and its tip and top as sliced (the most chin-ward material at the hook's
    mid-height, the highest along its mid-depth) within HOOK_SLICED_TOL of the CAD; the seams (outer-wall starts) off the
    button face (the cap's top and its chamfers) and off the chin face where it shows (over the face)."""
    from shapely.geometry import box as sbox
    H, y0 = P.KEY_HOOK, P.KEY_CAP['y'][0]
    z0, z1 = P.KEY_HOOK_Z
    zm, ym = (z0 + z1) / 2, (H['tip'] + y0) / 2
    hook = sbox(H['tip'], z0, y0, z1)
    top, ch = keys.TOP, P.KEY_CAP['chamfer']
    rows = []
    for c, g in device_layers(name, gcode, ends='round'):
        if not (H['dx'][0] + 0.1 <= abs(c) <= H['dx'][1] - 0.1) or c < -P.KEY_CAP['half'] + 2 * P.LAYER:
            continue
        rt = _runs(g, (H['tip'] - 1.0, zm), (y0 + 0.5, zm))
        rz = [r for r in _runs(g, (ym, z0 - 1.0), (ym, z1 + 1.0)) if r[0] <= zm <= r[1]]
        rows.append({'dx': c, 'cover': round(hook.intersection(g).area / hook.area, 3),
                     'tip': round(rt[0][0], 3) if rt else None, 'top': round(rz[0][1], 3) if rz else None})
    seams = _seams(name, gcode)
    bad = [q for q in seams if q[2] > top - ch - 0.1 or (q[1] < y0 + 0.15 and q[2] > P.Z_FRONT)]
    ok_rows = [r for r in rows if r['tip'] is not None and r['top'] is not None]
    worst = {'cover': min(r['cover'] for r in rows), 'tip_off': round(max(abs(r['tip'] - H['tip']) for r in ok_rows), 3),
             'top_off': round(max(abs(r['top'] - z1) for r in ok_rows), 3)} if rows and len(ok_rows) == len(rows) else {}
    return {'what': 'key on its end: hooks as sliced (cover, tip, top), seams', 'layers_in_the_hooks': len(rows),
            'by_side': {sd: len([r for r in rows if (r['dx'] > 0) == (sd > 0)]) for sd in (-1, 1)}, 'worst': worst,
            'seams': sorted({(round(q[1], 1), round(q[2], 1)) for q in seams}), 'seams_on_show': bad[:6],
            'ok': bool(worst) and worst['cover'] >= HOOK_COVER_MIN and worst['tip_off'] <= HOOK_SLICED_TOL
                  and worst['top_off'] <= HOOK_SLICED_TOL and not bad}


# ---- the keys' fit as sliced (2026-09-29, Ian's first print: the keys jammed) ---------------------------------------
# Every clearance between a key and its opening, read back from the two parts' G-code: each layer's lines buffered by
# half their ;WIDTH (round ends and joins, as a nozzle lays them: flat ends cut a line's corner back to its
# centreline, so a first-layer end read 0.25 short) and merged, taken back to the device frame. Only differences within
# one part are used (the tub's free widths, the key's widths and depths), so wherever Orca put either part cancels out.
# Less KEY_FDM's worst, each must meet mechanics.key_fit's limits as printed, with no allowance (the hook keys: the hook's
# tip to its slot's back as the pusher's chin end, and W_OUT as sliced less the key's growth over the rest's worst high,
# mechanics.rest_high). The Y clearances are
# read across the whole cap (FIT_DX): Orca simplifies the opening's R0.2 corners and its skin chin edge reads slanted
# (-7.938 at the cap's -X end to -7.950 at +X; the Rev L tub, both builds), so the narrowest point is near the -X end;
# the key is taken as its deepest (+Y face to chin face, over its width) against the opening's narrowest.
FIT_MIN = {'x': 0.15, 'y': 0.05}
FIT_DX = tuple(round(-4.9 + 0.1 * i, 1) for i in range(99))   # the stations across a key for its Y clearances
HOOK_DX = round(sum(P.KEY_HOOK['dx']) / 2, 3)   # the hooks' middles, +-4.45


_WIDTHS = {}


def parse_width(gcode):
    """As parse, with each line's width: {layer top z: [(x0, y0, x1, y1, type, width)]} (Orca writes ;WIDTH before a
    feature's lines). A part on a raft: as parse. Memoised by the file and its time (no_support reads one G-code once
    per window: the lid's thirteen latch arms, 2026-10-12); no caller changes what it returns."""
    g = Path(gcode)
    key = (str(g), g.stat().st_mtime_ns)
    if key not in _WIDTHS:
        _WIDTHS.clear()
        _WIDTHS[key] = _parse_width(g)
    return _WIDTHS[key]


def _parse_width(gcode):
    layers, z, x, y, t, w = {}, 0.0, 0.0, 0.0, None, 2 * HALF_W
    shift = raft_info(gcode)[0]
    for line in Path(gcode).read_text(errors='ignore').splitlines():
        if line.startswith(';Z:'):
            z = round(float(line[3:]) - shift, 3)
        elif line.startswith(';TYPE:'):
            t = line[6:]
        elif line.startswith(';WIDTH:'):
            w = float(line[7:])
        elif line.startswith(('G1', 'G0')):
            v = dict((q[0], float(q[1:])) for q in line.split(';')[0].split()[1:] if q[0] in 'XYZE' and len(q) > 1)
            nx, ny = v.get('X', x), v.get('Y', y)
            if line.startswith('G1') and v.get('E', 0) > 0 and (nx, ny) != (x, y) and (z > 1e-6 or not shift):
                layers.setdefault(z, []).append((x, y, nx, ny, t, w))
            x, y = nx, ny
    return layers


class Sliced:
    """A part's G-code as material in the device frame, for the parts that print turned about X (the key cap down, the
    tub and the coupon strip face down): the G-code's X and Y map to the device's X and Y, its Z to the device's Z."""

    def __init__(self, name, gcode):
        import numpy as np
        self.layers = parse_width(gcode)
        self.fr = Frame(name, self.layers)
        RT = self.fr.R.T
        assert abs(RT[0][2]) < 1e-9 and abs(RT[1][2]) < 1e-9, f'{name}: its print pose turns Z into X or Y'
        self.RT = RT
        self.q0 = np.array([self.fr.lo[0] - self.fr.off[0], self.fr.lo[1] - self.fr.off[1], self.fr.lo[2]])

    def xy(self, gx, gy):
        q = (gx + self.q0[0], gy + self.q0[1])
        return (self.RT[0][0] * q[0] + self.RT[0][1] * q[1], self.RT[1][0] * q[0] + self.RT[1][1] * q[1])

    def zs(self, z0, z1):
        """The layers whose mid-plane is at device z0..z1: [(device z, layer key)]."""
        out = []
        for z in sorted(self.layers):
            zd = self.RT[2][2] * (z - P.LAYER / 2 + self.q0[2])
            if z0 <= zd <= z1:
                out.append((round(float(zd), 3), z))
        return out

    def area(self, key, win):
        """The layer's material within the device window win = (x0, y0, x1, y1)."""
        from shapely.geometry import LineString
        from shapely.ops import unary_union
        gs = []
        for s in self.layers[key]:
            if not _part(s):
                continue
            a, b = self.xy(s[0], s[1]), self.xy(s[2], s[3])
            if max(a[0], b[0]) < win[0] or min(a[0], b[0]) > win[2] or max(a[1], b[1]) < win[1] or min(a[1], b[1]) > win[3]:
                continue
            gs.append(LineString([a, b]).buffer(s[5] / 2, cap_style=1, join_style=1))
        return unary_union(gs)


def _free(g, p, axis, span=9.0):
    """The free interval (lo, hi) round the point p along X (axis 0) or Y (1) in the material g; None if p is in it."""
    from shapely.geometry import LineString
    a, b = list(p), list(p)
    a[axis] -= span
    b[axis] += span
    lo, hi = p[axis] - span, p[axis] + span
    hit = LineString([a, b]).intersection(g)
    for s in getattr(hit, 'geoms', [hit]):
        if s.is_empty or s.length < 1e-6:
            continue
        c = [q[axis] for q in s.coords]
        if max(c) <= p[axis]:
            lo = max(lo, max(c))
        elif min(c) >= p[axis]:
            hi = min(hi, min(c))
        else:
            return None
    return lo, hi


def _extent(g, p0, p1, axis):
    """The material's (min, max) along the line p0 -> p1, in X (axis 0) or Y (1); None if it misses."""
    from shapely.geometry import LineString
    hit = LineString([p0, p1]).intersection(g)
    c = [q[axis] for s in getattr(hit, 'geoms', [hit]) if not s.is_empty and s.length > 1e-6 for q in s.coords]
    return (min(c), max(c)) if c else None


def opening_sliced(S, xc):
    """The tub's (or the coupon strip's) opening at key centre xc as sliced, device frame, each the least over its
    layers: the free X and Y in the skin, the free X web to web and Y chin wall to rail in the pocket, the ledge (the
    skin's chin edge over the chin wall's face, at the centre), and the hook keys' slots at +-HOOK_DX: the back (the
    most +Y, over the layers the hooks run in), the skin's chin edge over them (the least), and the roof (where the slot
    closes: the top of its highest open layer)."""
    ym = sum(P.KEY_OPENING['y']) / 2
    yp = -6.1                                   # across the pocket, between the chin wall and the rail
    ys = (P.KEY_SLOT['back'] + P.BOT_IN) / 2     # inside a slot
    win = (xc - 7.5, P.BOT_IN - 1.5, xc + 7.5, P.RAIL_Y[0] + 1.5)
    r = {'skin_x': 99.0, 'skin_y': {dx: 99.0 for dx in FIT_DX}, 'pocket_x': 99.0, 'pocket_y': {dx: 99.0 for dx in FIT_DX},
         'rail_face': 99.0, 'chin_face': -99.0, 'skin_chin_edge': 99.0, 'slot_back': -99.0, 'skin_chin_edge_at_hooks': 99.0}
    skin = S.zs(P.LIP + 0.05, P.Z_FRONT - P.KEY_EDGE_CHAMFER - 0.05)
    pocket = S.zs(P.WEB_Z0 + 0.1, P.LIP - 0.1)
    for _, k in skin:
        g = S.area(k, win)
        f = _free(g, (xc, ym), 0)
        r['skin_x'] = min(r['skin_x'], f[1] - f[0])
        for dx in FIT_DX:
            f = _free(g, (xc + dx, ym), 1)
            r['skin_y'][dx] = min(r['skin_y'][dx], f[1] - f[0])
        r['skin_chin_edge'] = min(r['skin_chin_edge'], _free(g, (xc, ym), 1)[0])
        for sd in (-1, 1):
            r['skin_chin_edge_at_hooks'] = min(r['skin_chin_edge_at_hooks'], _free(g, (xc + sd * HOOK_DX, ym), 1)[0])
    for _, k in pocket:
        g = S.area(k, win)
        f = _free(g, (xc, yp), 0)
        r['pocket_x'] = min(r['pocket_x'], f[1] - f[0])
        for dx in FIT_DX:
            f = _free(g, (xc + dx, yp), 1)
            r['pocket_y'][dx] = min(r['pocket_y'][dx], f[1] - f[0])
            r['rail_face'] = min(r['rail_face'], f[1])
        r['chin_face'] = max(r['chin_face'], _free(g, (xc, yp), 1)[0])
        for sd in (-1, 1):
            f = _free(g, (xc + sd * HOOK_DX, ys), 1)
            r['slot_back'] = max(r['slot_back'], f[0] if f else 99.0)
    r['ledge'] = r['skin_chin_edge'] - r['chin_face']
    # the roof: from the rim up, the top of the last layer before the slot closes at either hook's middle
    r['roof'] = None
    for z, k in sorted(S.zs(P.SEAM + 0.1, P.Z_FRONT)):
        if not all(_free(S.area(k, win), (xc + sd * HOOK_DX, ys), 1) for sd in (-1, 1)):
            break
        r['roof'] = round(z + P.LAYER / 2, 3)
    for n in ('skin_y', 'pocket_y'):             # across the cap: the narrowest (where), and the widest
        d = min(r[n], key=r[n].get)
        r[n] = {'min': round(r[n][d], 4), 'at_dx': d, 'max': round(max(r[n].values()), 4)}
    r['layers'] = {'skin': [skin[0][0], skin[-1][0], len(skin)], 'pocket': [pocket[0][0], pocket[-1][0], len(pocket)]}
    return r


def _x_bounds(g, y0, y1):
    """The material's X extent (min, max) in the band y0..y1 (device frame); None if there is none."""
    from shapely.geometry import box as sbox
    h = g.intersection(sbox(-8.0, y0, 8.0, y1))
    return None if h.is_empty else [round(h.bounds[0], 4), round(h.bounds[2], 4)]


INSET = 0.25                             # key_sliced: its levels off each band's ends (a line's half width and more)


def key_sliced(name, gcode):
    """The key as sliced on its -X end (test 1), from its centre, device frame: its X is its layers' span (a whole
    number of layers); in the body's layers (|dx| <= 3.2), at levels over the hooks and under the top chamfer,
    its chin face and +Y face (the most chin-ward and the most +Y: the key's deepest), and its lowest point (the
    pusher's underside, on the crown at rest); the pusher's chin end at the stop levels; in the hooks' layers (past the
    bed end's two) the hooks' tip at their mid-height and their top along their mid-depth. The levels keep INSET off each
    band's ends: a wall line runs along z here, and it rounds off near a corner."""
    H, Pu = P.KEY_HOOK, P.KEY_PUSHER
    z0, z1 = P.KEY_HOOK_Z
    cap = (P.KEY_HOOK_Z[1] + INSET, keys.TOP - P.KEY_CAP['chamfer'] - INSET)     # over the hooks (and the +X one's lead)
    stop = (Pu['z'][0] + INSET, Pu['stop_z1'] - INSET)
    lv = lambda lo, hi: [lo + (hi - lo) * i / 6 for i in range(7)]
    r = {'plus_y': [], 'chin': [], 'pusher': [], 'bottom': [], 'tip': [], 'top': []}
    dl = device_layers(name, gcode, ends='round')
    zm, ym = (z0 + z1) / 2, (H['tip'] + P.KEY_CAP['y'][0]) / 2
    for c, g in dl:
        if abs(c) <= 3.2:
            for z in lv(*cap):
                rs = _runs(g, (-9.5, z), (-3.0, z))
                if rs:
                    r['plus_y'].append(rs[-1][1])
                    r['chin'].append(rs[0][0])
            for z in lv(*stop):
                rs = _runs(g, (-9.5, z), (-3.0, z))
                if rs:
                    r['pusher'].append(rs[0][0])
            rs = _runs(g, ((Pu['y'][0] + Pu['y'][1]) / 2, -2.0), ((Pu['y'][0] + Pu['y'][1]) / 2, 2.0))
            if rs:
                r['bottom'].append(rs[0][0])
        if H['dx'][0] + 0.1 <= abs(c) <= H['dx'][1] - 0.1 and c >= -P.KEY_CAP['half'] + 2 * P.LAYER:
            rs = _runs(g, (H['tip'] - 1.0, zm), (-3.0, zm))
            if rs:
                r['tip'].append(rs[0][0])
            rs = [q for q in _runs(g, (ym, z0 - 1.0), (ym, z1 + 1.0)) if q[0] <= zm <= q[1]]
            if rs:
                r['top'].append(rs[0][1])
    cs = [c for c, _ in dl]
    return {'cap_x': [round(min(cs) - P.LAYER / 2, 3), round(max(cs) + P.LAYER / 2, 3)], 'plus_y': round(max(r['plus_y']), 4),
            'chin_face': round(min(r['chin']), 4), 'pusher_chin_end': round(min(r['pusher']), 4), 'bottom': round(min(r['bottom']), 4),
            'hook_tip': round(min(r['tip']), 4), 'hook_top': round(max(r['top']), 4),
            'layers': len(cs), 'samples': {q: len(v) for q, v in r.items()}}


def fit_pair(o, k):
    """The clearances of the key k in the opening o as sliced, each against the CAD's and, less KEY_FDM's worst for its
    kind of pair (X two-sided with the key centred, Y one-sided from the +Y face), against FIT_MIN as printed. The key
    prints on its -X end (test 1): its X is its layers' span (50 layers, 10.00 since 2026-10-03) and does not grow, so an
    X pair's CAD is the layer-quantized one (0.30 skin, 0.40 webs) and as printed it loses hole/2 only. The hooks
    (test 2): the tip to the slot's back as the pusher's chin end; the flat under the roof (the skin's chin edge over the
    hooks less the hook's tip, the key on the rail); W_OUT (the roof less the hooks' top, the key's underside on the
    crown at rest), as printed less the key's growth, over the rest's worst high (mechanics.rest_high)."""
    import mechanics
    hole, part = P.KEY_FDM['hole'][2], P.KEY_FDM['part'][2]
    cap_x = k['cap_x'][1] - k['cap_x'][0]
    lay = mechanics.printed_layers(0.0, 2 * P.KEY_CAP['half'])
    xq = (lay[1] - lay[0]) / 2
    y_skin = o['skin_y']['min'] - (k['plus_y'] - k['chin_face'])            # the opening's narrowest, the key's deepest
    y_pocket = o['pocket_y']['min'] - (k['plus_y'] - k['pusher_chin_end'])
    tip = o['rail_face'] - (k['plus_y'] - k['hook_tip'])                    # the hooks' tip, the key on the rail
    rows = {'X skin per side': ((o['skin_x'] - cap_x) / 2, P.KEY_OPENING['half'] - xq, hole / 2, FIT_MIN['x']),
            'X webs per side': ((o['pocket_x'] - cap_x) / 2, P.SLOT[1] - xq, hole / 2, FIT_MIN['x']),
            'Y skin, chin side': (y_skin, P.KEY_CAP['y'][0] - P.KEY_OPENING['y'][0], hole + part, FIT_MIN['y']),
            'Y pocket, chin side': (y_pocket, P.KEY_PUSHER['y'][0] - P.BOT_IN, hole + part, FIT_MIN['y']),
            'Y hook tip to the slot back': (tip - o['slot_back'], P.KEY_HOOK['tip'] - P.KEY_SLOT['back'], hole + part, FIT_MIN['y'])}
    out = {}
    for n, (v, cad, fdm, lim) in rows.items():
        out[n] = {'sliced': round(v, 3), 'cad': round(cad, 3), 'printed_worst': round(v - fdm, 3),
                  'ok': abs(v - cad) <= 0.03 and round(v - fdm, 3) >= lim}
    out['Y skin, chin side']['opening_narrowest_at_dx'] = o['skin_y']['at_dx']
    out['Y pocket, chin side']['opening_narrowest_at_dx'] = o['pocket_y']['at_dx']
    b = o['skin_chin_edge_at_hooks'] - tip
    cad_b = P.KEY_OPENING['y'][0] - P.KEY_HOOK['tip']
    out['hook under the roof'] = {'sliced': round(b, 3), 'cad': round(cad_b, 3),
                                  'net_of_corner_radii': round(b - mechanics.FDM_R['wall'] - mechanics.FDM_R['layer'], 3),
                                  'ok': b >= cad_b - 0.03 and b - mechanics.FDM_R['wall'] - mechanics.FDM_R['layer'] > 0}
    w = o['roof'] - (P.KEY_PUSHER['z'][0] + k['hook_top'] - k['bottom']) if o['roof'] is not None else -9.0
    need = mechanics.rest_high()[1]
    out['W_OUT as sliced'] = {'sliced': round(w, 3), 'cad': P.KEY_W_OUT, 'printed': round(w - part, 3), 'min': need,
                              'ok': abs(w - P.KEY_W_OUT) <= 0.08 and w - part >= need}
    out['ledge'] = {'sliced': round(o['ledge'], 3), 'cad': round(P.KEY_OPENING['y'][0] - P.BOT_IN, 3), 'ok': o['ledge'] >= 0.23}
    return out


def _gcode(report, name):
    """A part's G-code: this run's, or else the last one sliced into out/<variant>/slice/<name>/."""
    info = report.get(name)
    if info and info.get('gcode'):
        return hw.ROOT / info['gcode']
    return next((OUT / name).glob('*.gcode'), None)


def key_fit(report):
    """The keys' fit as sliced, both pairs this build prints: the tub with key-426 at each of its four openings, and
    coupon-chin (the hook keys' fit check) with key-426 (and the strip against the tub's own opening, which it
    reproduces)."""
    import coupons
    need = ['tub', 'key-426', 'coupon-chin']
    missing = [n for n in need if _gcode(report, n) is None]
    if missing:
        return {'missing': missing, 'ok': False}
    S = {n: Sliced(n, _gcode(report, n)) for n in ('tub', 'coupon-chin')}
    k = key_sliced('key-426', _gcode(report, 'key-426'))
    ops = {r: opening_sliced(S['tub'], keys.key_x(r)) for r in P.KEY_REFS}
    strip = opening_sliced(S['coupon-chin'], 0.0)
    out = {'tub': {r: fit_pair(ops[r], k) for r in P.KEY_REFS}, 'coupon': {'key-426': fit_pair(strip, k)}}
    t = ops[coupons.COUPON_KEY]
    same = {'skin_x': (strip['skin_x'], t['skin_x']), 'pocket_x': (strip['pocket_x'], t['pocket_x']),
            'ledge': (strip['ledge'], t['ledge']), 'slot_back': (strip['slot_back'], t['slot_back']), 'roof': (strip['roof'], t['roof']),
            **{f'{n} {m}': (strip[n][m], t[n][m]) for n in ('skin_y', 'pocket_y') for m in ('min', 'max')}}
    out['coupon reproduces the opening'] = {n: {'strip': round(a, 3), 'tub': round(b, 3), 'ok': abs(a - b) <= 0.03}
                                            for n, (a, b) in same.items()}
    out['measured'] = {'openings': ops, 'strip': strip, 'key': k}
    out['ok'] = (all(c['ok'] for grp in ('tub', 'coupon') for pair in out[grp].values() for c in pair.values())
                 and all(c['ok'] for c in out['coupon reproduces the opening'].values()))
    return out


def key_fit_table(kf):
    """The key-fit read-back, one table per build."""
    if 'missing' in kf:
        return f"key fit: not read, no G-code for {kf['missing']}  <-- CHECK"
    L = [f'key fit as sliced ({P.VARIANT}): sliced (CAD) -> as printed at worst (KEY_FDM)']
    pairs = [(f'tub {r} + key-426', v) for r, v in kf['tub'].items()] + [(f'coupon-chin + {n}', v) for n, v in kf['coupon'].items()]
    for name, rows in pairs:
        cells = []
        for n, c in rows.items():
            s = f"{n} {c['sliced']:+.3f}"
            if 'printed_worst' in c:
                s += f" ({c['cad']:+.3f}) -> {c['printed_worst']:+.3f}"
            elif 'printed' in c:
                s += f" ({c['cad']:+.3f}) -> {c['printed']:+.3f} (>= {c['min']:.3f})"
            elif 'net_of_corner_radii' in c:
                s += f" ({c['cad']:+.3f}), net of the corner radii {c['net_of_corner_radii']:+.3f}"
            else:
                s += f" (CAD {c['cad']:+.3f}, >= 0.23)"
            cells.append(s + ('' if c['ok'] else '  <-- CHECK'))
        L.append(f'  {name}:\n    ' + '\n    '.join(cells))
    bad = [n for n, c in kf['coupon reproduces the opening'].items() if not c['ok']]
    L.append("  coupon-chin reproduces the tub's opening and slots (+-0.03): " + ('yes' if not bad else f'NO {bad}  <-- CHECK'))
    L.append(f"key fit: {'PASS' if kf['ok'] else 'FAIL'}")
    return '\n'.join(L)


def community_readback(name, gcode):
    """The read-backs of the 2026-10-23 changes (community.py): the midplate's pins as laid (R2), the lid's back wordmark
    open and the tub's chin plain as laid (R3). Rows marked 'community' stop the run (exit 1) like the screws do."""
    import community
    if name == 'midplate':
        rows = [community.pins_laid(device_layers(name, gcode, ends='round'))]
    elif name == 'lid':
        rows = [community.logo_laid(device_layers(name, gcode), P.LOGO_BACK_WORDMARK, 'lid back wordmark', engraved=True)]
    elif name == 'tub':
        rows = [community.logo_laid(device_layers(name, gcode), P.LOGO_CHIN, "tub chin (the old wordmark's place)", engraved=False,
                                    bed_high=True)]
    else:
        return []
    return [{**r, 'community': True} for r in rows]


def as_printed(report):
    """The screws as printed (2026-10-13, asprinted.py, the same module as the 3.68's): the lid's home on the tub, then
    each screw (H3, H4, the top screw) read from this build's lid and tub as sliced, put together where they meet: in
    the lid, the seat of a socket head cap (ISO 4762, Ian's: dk 3.8, k 2.0) and of a pan head (ISO 7045: dk 4.0, k
    1.6), neither head proud of the back; in the tub, the pilot. The M2 x SCREW_L on its seat with the lid at home:
    >= 3.0 in the pilot (also with the lid 0.3 open), its tip short of the pilot's end and >= 0.8 from the front face.
    A FAIL makes this script exit 1. Needs the lid and the tub sliced; None otherwise."""
    import asprinted as A
    if not all((report.get(k) or {}).get('gcode') for k in ('lid', 'tub')):
        return None
    L = {k: device_layers(k, hw.ROOT / report[k]['gcode']) for k in ('lid', 'tub')}
    fps = hw.footprints()
    rims = [(P.POCKET_X0 - 2.0, y) for y in (20.0, 33.0, 47.0)] + [(P.POCKET_X1 + 2.0, y) for y in (18.0, 30.0)]
    posts = [(fps[r]['cad'][0] + 1.5, fps[r]['cad'][1]) for r in ('H3', 'H4')]    # beside the posts' pins
    h = A.home(L['lid'], L['tub'], rims, posts, hw.PCB_T)
    screws = {'H3': tuple(fps['H3']['cad'][:2]), 'H4': tuple(fps['H4']['cad'][:2]), 'top': P.TOP_SCREW}
    sc = [A.screw(n, x, y, L['lid'], L['tub'], h['dz'], P.SCREW_L, P.Z_BACK) for n, (x, y) in screws.items()]
    usb = usb_fit(report, h['dz'], posts)
    # the top screw's relief (2026-10-23, R1): the M2_CLEAR bore from the rim to TOP_SCREW_CLEAR_TO (1.6), so the pilot as
    # laid starts there, not at the rim (the screw then thread-forms 3.6, not 9.0)
    top = next(s for s in sc if s['screw'] == 'top')
    to = 1.6                                                  # Ian's number, not params: the check must not follow a change of it
    relief = {'what': f'top screw: the pilot starts at the end of the clearance bore ({to}), not at the rim',
              'pilot': top.get('pilot'), 'ok': bool(top.get('pilot') and top['pilot'][0] >= to - 0.05)}
    return {'ok': bool(h['dz'] is not None and all(s['ok'] for s in sc) and usb['ok'] and relief['ok']), 'home': h, 'screws': sc,
            'usb': usb, 'top_relief': relief}


def usb_fit(report, dz, posts):
    """The USB port as printed (asprinted.usb_fit, 2026-10-22): a nominal plug centred in the Rev 1.0 socket and in the
    Rev 1.02 socket (0.14 nearer the board), each seated J1_SEAT_DZ nearer the board than KiCad draws it, on the board's
    posts, against the lid (at home) and the tub as laid. FAIL under USB_FIT_MIN on any flat. The hole
    is read from the lid's and the tub's layers with round line ends, as deposited."""
    import asprinted as A
    u = P.J1_REV10
    R = {k: device_layers(k, hw.ROOT / report[k]['gcode'], ends='round') for k in ('lid', 'tub')}
    bz = A.post_top(R['lid'], posts, dz)
    if dz is None or bz is None:
        return {'ok': False, 'rows': [], 'fails': ['no lid home or no board post'], 'min': P.USB_FIT_MIN}
    s = P.J1_SEAT_DZ
    sockets = {'Rev 1.0 (USB4085)': u['zc'] + s, 'Rev 1.02 (USB4105, 0.14 nearer)': u['zc'] + P.J1_REV102_DZ + s}
    return A.usb_fit(R['lid'], R['tub'], dz, bz, u['yc'], u['mouth_x'], P.INSERT_X1 + P.USB_FLOOR['t'], sockets,
                     plug=P.USB_PLUG, fit_min=P.USB_FIT_MIN)


if __name__ == '__main__':
    pre = presets()
    import coupons
    parts = sys.argv[1:] or (['key-426', 'crank-M', 'crank-T', 'gate', 'midplate', 'lid', 'tub', 'coupon-gate', *coupons.BOTTOM_KEY_COUPON]
                             if P.BOTTOM_KEYS else ['midplate', 'lid', 'tub'])
    report = {}
    for name in parts:
        stl = P.OUT / 'print' / f'{name}.stl'
        info = slice_part(stl, pre)
        report[name] = info
        print(name, info, flush=True)
        if info['gcode'] and (name in ('tub', 'key-426', 'gate', 'coupon-gate', 'coupon-chin', 'lid', 'midplate')
                              or name.startswith('crank-')):
            g = hw.ROOT / info['gcode']
            rb = readback(name, g)
            if name == 'tub' and not P.LIGHT_STRIP:
                rb.append(window_bevel(name, g))
            if name == 'tub' and not P.BOTTOM_KEYS:
                rb.append(chin_no_support(name, g))
            elif name == 'lid' and not P.BOTTOM_KEYS:
                rb.append(lid_chin_no_support(name, g))
            elif name.startswith(NO_SUPPORT_PARTS) or name in NO_SUPPORT_CHIN:
                w = chin_window(name) if name in NO_SUPPORT_CHIN else None
                ns = no_support(name, g, w)
                info['no_support'] = ns
                rb.append({'what': 'no support needed (floating pieces, reach past the layer below)' + (' over the chin' if w else ''),
                           'floating': len(ns['floating']), 'reach_max_mm': ns['reach_max_mm'], 'roles': ns['roles'], 'ok': ns['ok']})
            if name.startswith('key-'):
                rb.append(key_first_layer(name, g))
                rb.append(key_on_end(name, g))
            if name.startswith('crank-'):
                rb.append(crank_sections(name, g))
                rb.append({'what': 'crank sliced with Arachne walls', 'wall_generator': info.get('wall_generator'),
                           'ok': info.get('wall_generator') == 'arachne'})
            if not P.DEV_HEADER and name in ('tub', 'lid'):
                rb.append(top_no_support(name, g))
            if P.SIDES != 'all' and name in ('tub', 'lid'):
                rb.append(side_wall_no_support(name, g))
            if name == 'lid':
                rb.append(latch_no_support(name, g))
            rb += community_readback(name, g)
            info['readback'] = rb
            bad = [r for r in rb if not r['ok']]
            print(f"  read-back: {len(rb) - len(bad)}/{len(rb)} ok" + ''.join(f'\n    FAIL {r}' for r in bad), flush=True)
            for r in rb:
                if any(k in r for k in ('free_d', 'width', 'free_gap', 'islands', 'steepest_deg', 'wall', 'bridge_moves', 'ends',
                                        'floating', 'area_mm2', 'worst', 'wall_generator', 'keys')):
                    print(f'    {r}', flush=True)
    # the keys' fit as sliced: needs the tub, key-426 and coupon-chin (this run's G-code, or the last sliced), so it
    # runs whenever this run sliced any of them
    if P.BOTTOM_KEYS and any(n in report for n in ('tub', 'key-426', *coupons.BOTTOM_KEY_COUPON)):
        kf = key_fit(report)
        report['_key_fit'] = kf
        print(key_fit_table(kf), flush=True)
    ap = report['_as_printed'] = as_printed(report)      # the screws as printed (lid at home, socket and pan heads)
    if ap is not None:
        import asprinted
        asprinted.show(ap)
    (OUT / 'slice-report.json').write_text(json.dumps(report, indent=1, default=str))
    if 'key-426' in report and report['key-426']['gcode']:
        plot_layers(hw.ROOT / report['key-426']['gcode'], [0.2, 3.0, 6.0], OUT / 'toolpath-key.png', 'key')
    if 'crank-M' in report and report['crank-M']['gcode']:
        plot_layers(hw.ROOT / report['crank-M']['gcode'], [0.2, 4.0, 6.0], OUT / 'toolpath-crank.png', 'crank')
    if 'tub' in report and report['tub']['gcode']:
        plot_layers(hw.ROOT / report['tub']['gcode'], [0.2, 4.0, 7.0], OUT / 'toolpath-tub.png', 'tub')
    comm_bad = [r['what'] for v in report.values() if isinstance(v, dict) for r in v.get('readback', []) if r.get('community') and not r['ok']]
    for w in comm_bad:
        print(f'FAIL (community) {w}', flush=True)
    sys.exit(0 if (ap is None or ap['ok']) and not comm_bad else 1)     # the as-printed screws stop the run (the read-backs above are read)
