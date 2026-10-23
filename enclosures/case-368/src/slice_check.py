"""Slice every part with the installed OrcaSlicer and the stock Elegoo Centauri Carbon 2
profiles (0.4 nozzle, 0.20 mm Standard, Elegoo PLA), then report time/filament and plot
toolpaths of selected layers so thin features can be checked by eye.

Orca's CLI does not resolve profile inheritance for files passed on the command line, so the
presets are flattened here first. Nothing is sent to a printer; G-code stays in out/<variant>/slice/ (variant.py:
run it once per build, after plates.py; the tub's read-back boxes are the light strip's).

The bottom keys' boxes expect extrusion in every layer through them ('present') or in none ('absent'); the older
boxes are read by eye, as before (a trailing '!' on their names now marks the ones that should stay empty). The bottom keys' parts
(2026-09-26; the crank spec's check 8) add boxes on the tub (webs, the rail's rings and open seats, the plastic over the
cheek slots' roofs, the ledge, the chin wall's lead-in; since test 2 the hook slots: empty to the roof, the wall behind
(from the rim, across the slot's whole width) and the roof over them printed, in the tub and the coupon's strip), on
the key (its hooks and the +X hook's lead, the pusher's chin-side stop) and on both cranks (the walls round the bore,
crown, nose, belly), and the rod's holes are read back as free diameters from
the perimeters (bores(): the tub's sliver bore and ring bores >= 1.90, the cranks' bores >= 1.80 before reaming).
The key's fit (2026-09-29, key_fit()): every clearance round a key read back from the sliced tub, the coupon's strip and
the key (the tub's openings, webs, chin wall and hook slots; the key's cap, pusher and hooks), as differences within one part's
G-code, so where the slicer put the part cancels; less params KEY_FDM's worst, each must still leave the fit that
mechanics.key_fit asks for.
Ian's settings for the read-back: no brim, and (2026-09-27) elephant-foot compensation 0 for the bottom keys, the
cranks and the gate (an OrcaSlicer per-object setting; here their own process file): the cranks stand
on a 1.10 face, and the keys stand on their -X end. Test 1 (2026-09-29): the cranks also get Arachne walls (their own
process file, as make_plates.py's per-object setting): classic walls left voids in the 1.5 cheeks. The cranks'
read-back adds the closed ring, its fill and the lip's open C (boxes), every piece of every layer standing on the layer
below (islands) and the sliced cheek against its designed section (crank_sections: >= 90 % in every layer through the
bore). The key prints on its -X end: its read-back (key_on_end) is each hook's section in every layer through it and
the seams off the button face and the visible chin face; first_layers adds its bed end's area and that it stays inside
the key's outline; key_fit reads the key's X from its layers. The hook keys (test 2, 2026-09-30), no supports: no
support, bridge or overhang line anywhere in the key, and none in the tub round its hook slots (no_support()). The key
pushed sideways all along its travel, both parts as sliced (2026-10-03, the 50-layer key: key_side_sweep()).
SPEC2 rev 3 (2026-09-28, the rod's gate; check 9): the gate's slot in the tub and in its proof coupon (coupon-gate):
the mouth, the cavity and its round ends stay empty, the floor and the lips print, the sliver's bore reads back >= 1.90
and nothing in the slot is a bridge (bridges()); the gate: its first layer is the flange, nothing overhangs past 45
degrees, the pull hole reads back >= 1.15 and its walls print (gate_checks()).
The bottom keys and the cranks print on a 2-layer raft (2026-10-06, Ian; make_plates.RAFT, set per object in the plate
file), so they are sliced on one here (RAFT, in process-key.json and process-crank.json). Every read-back takes the
part from its own bed face: the raft's layers (below the part's first, Orca's support roles only) are left out, and z
counts from the bottom of the part's first layer (raft_info), so the key reads as 50 layers from z 0, as on the bed;
no_support() does not count the raft's Support lines, which are not the key's.
The standard tub's screen window (2026-10: 35 degrees from the raised face, R0.4 corners at the lip), face down, is an
overhang: window_bevel() reads each skin layer's window edge back (4 edges, 4 corners) against the CAD at the layer's
mid-plane, so the lip's layer prints on the lip line, and holds the no-support rule over it (nothing floating, reach
<= 0.5, no support, bridge or overhang line). The light-strip tub keeps x3's 45-degree window and is not read.
The closed case as printed (2026-10-13, as_printed(); asprinted.py): the tub, the lid and the midplate put together
where they really meet, the lid at its as-printed home: every screw's thread in its pilot, tip and face; no printed
part overlapping another; every latch's dead band. A FAIL there makes this script exit 1 (the other read-backs only
mark '<-- CHECK').
"""
import json, math, re, subprocess, sys
from pathlib import Path
import hw

ORCA = Path(r'C:\Program Files\OrcaSlicer\orca-slicer.exe')
PROFILES = Path(r'C:\Program Files\OrcaSlicer\resources\profiles')
OUT = hw.OUT / 'slice'
OUT.mkdir(parents=True, exist_ok=True)
PRESETS = {'machine': 'Elegoo Centauri Carbon 2 0.4 nozzle',
           'process': '0.20mm Standard @Elegoo CC2 0.4 nozzle',
           'filament': 'Elegoo PLA @ECC2'}                   # Ian prints PLA


def index():
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
            # no brim: the profile's auto brim wraps the side keys' feet on the lid's first layer, and a line of
            # it in the 0.7 mm slot behind a key would tie the key to the lid
            d['brim_type'] = 'no_brim'
            d['brim_width'] = '0'
        p = OUT / f'{kind}.json'
        p.write_text(json.dumps(d, indent=1))
        paths[kind] = p
        if kind == 'process':            # the small bottom-key parts: elephant-foot compensation 0 (EFC0_PARTS)
            e = dict(d, elefant_foot_compensation='0')
            p = OUT / 'process-efc0.json'
            p.write_text(json.dumps(e, indent=1))
            paths['process_efc0'] = p
            c = dict(e, **CRANK_PROCESS, **RAFT)   # the cranks: EFC 0, Arachne walls (make_plates.CRANK_OBJ), a raft
            p = OUT / 'process-crank.json'
            p.write_text(json.dumps(c, indent=1))
            paths['process_crank'] = p
            k = dict(e, **RAFT)                    # the keys: EFC 0 and a raft (make_plates.RAFT)
            p = OUT / 'process-key.json'
            p.write_text(json.dumps(k, indent=1))
            paths['process_key'] = p
    return paths


EFC0_PARTS = ('key-', 'crank-', 'gate')   # printed with elephant-foot compensation 0 (Ian's per-object
                                                         # setting)
CRANK_PROCESS = {'wall_generator': 'arachne'}            # and the cranks with Arachne walls too (test 1, 2026-09-29)
# 2026-10-06 (Ian: "maybe add 2-layer rafts to the buttons/cranks ... so that they don't unstick from the build
# plate"): the bottom keys and the cranks print on a 2-layer raft, set per object in the plate file (make_plates.RAFT,
# the same three settings), so they are sliced on it here, and every read-back drops the raft's layers and reads the
# part from its own bed face (raft_info)
RAFT = {'raft_layers': '2', 'raft_contact_distance': '0.2', 'raft_first_layer_expansion': '1'}
RAFT_PARTS = ('key-', 'crank-')                          # make_plates.raft_part
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
        z, t, h, x, y, raft, first = 0.0, None, 0.2, 0.0, 0.0, set(), None
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


def slice_part(stl, pre):
    dest = OUT / stl.stem
    dest.mkdir(exist_ok=True)
    for old in dest.glob('*.gcode'):
        old.unlink()
    proc = (pre['process_crank'] if stl.stem.startswith('crank-') else
            pre['process_key'] if stl.stem.startswith(RAFT_PARTS) else
            pre['process_efc0'] if stl.stem.startswith(EFC0_PARTS) else pre['process'])
    cmd = [str(ORCA), '--orient', '0', '--arrange', '0', '--slice', '0', '--load-settings', f"{pre['machine']};{proc}",
           '--load-filaments', str(pre['filament']), '--outputdir', str(dest), str(stl)]
    r = subprocess.run(cmd, capture_output=True, timeout=600, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    g = next(dest.glob('*.gcode'), None)
    info = {'exit': r.returncode, 'gcode': str(g.relative_to(hw.ROOT)) if g else None,
            'stderr_tail': r.stderr.decode(errors='ignore')[-300:] if r.returncode else ''}
    if g:
        head = g.read_text(errors='ignore')
        for key, pat in {'time': r'estimated printing time \(normal mode\) = (.+)', 'grams': r'total filament used \[g\] = ([\d.]+)',
                         'layers': r'total layers count = (\d+)', 'filament_type': r'; filament_type = (\S+)',
                         'elefant_foot_compensation': r'; elefant_foot_compensation = (\S+)', 'brim_type': r'; brim_type = (\S+)',
                         'wall_generator': r'; wall_generator = (\S+)', 'raft_layers': r'; raft_layers = (\d+)',
                         'raft_contact_distance': r'; raft_contact_distance = (\S+)'}.items():
            m = re.search(pat, head)
            info[key] = m.group(1).strip() if m else None
        # 'layers' is the G-code's own count, the raft's included; the part's are the rest
        shift, raft = raft_info(g)
        info['raft'] = {'layers_z': raft, 'part_bed_face_z': shift}
        info['part_layers'] = int(info['layers']) - len(raft) if info.get('layers') else None
        info['brim_or_skirt_lines'] = sum(1 for ln in head.splitlines() if ln.startswith(';TYPE:') and ln[6:].strip() in ('Brim', 'Skirt'))
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


def extrusions(gcode):
    """{z: [((x0, y0), (x1, y1)), ...]} for every extruding move of the part itself. The start G-code's purge
    line (';TYPE:Custom') and any skirt or brim are left out: they would throw the alignment below off (the purge
    by the width of the bed; Orca's auto brim, which the lid gets, by half its uneven width). A part on a raft (RAFT):
    z from its bed face, the raft's layers left out (raft_info)."""
    layers, z, x, y, kind = {}, 0.0, 0.0, 0.0, ''
    shift = raft_info(gcode)[0]
    for line in Path(gcode).read_text(errors='ignore').splitlines():
        if line.startswith(';Z:') or line.startswith('; Z_HEIGHT:'):
            z = float(line.split(':')[1])
        if line.startswith(';TYPE:'):
            kind = line[6:].strip()
        if not line.startswith(('G1', 'G0')):
            continue
        if kind in ('Custom', '', 'Skirt', 'Brim'):
            x, y = (dict((t[0], float(t[1:])) for t in line.split(';')[0].split()[1:] if t[0] in 'XY' and len(t) > 1).get(k, v)
                    for k, v in (('X', x), ('Y', y)))
            continue
        vals = dict((t[0], float(t[1:])) for t in line.split(';')[0].split()[1:] if t[0] in 'XYZE' and len(t) > 1)
        nx, ny = vals.get('X', x), vals.get('Y', y)
        if 'Z' in vals:
            z = vals['Z']
        if vals.get('E', 0) > 0 and line.startswith('G1') and (z - shift > 1e-6 or not shift):
            layers.setdefault(round(z - shift, 2), []).append(((x, y), (nx, ny)))
        x, y = nx, ny
    return layers


def x_cover(segs, box, axis, half=0.2, step=0.05):
    """Share of the box's span along `axis` (0: X, 1: Y) that the layer's lines inside the box cover, each line
    counted half a line width either side of its centre: a wall behind a hook slot must cover the slot's whole width
    (a slit anywhere across it would let one see into the slot)."""
    x0, x1, y0, y1 = box
    lo, hi = box[2 * axis], box[2 * axis + 1]
    n = max(1, int((hi - lo) / step) + 1)
    hit = [False] * n
    for (ax, ay), (bx, by) in segs:
        k = max(2, int(math.hypot(bx - ax, by - ay) / 0.05))
        for i in range(k):
            t = (i + 0.5) / k
            mx, my = ax + (bx - ax) * t, ay + (by - ay) * t
            if x0 <= mx <= x1 and y0 <= my <= y1:
                c = (mx, my)[axis]
                for j in range(max(0, int((c - half - lo) / step)), min(n, int((c + half - lo) / step) + 2)):
                    if abs(lo + j * step - c) <= half:
                        hit[j] = True
    return sum(hit) / n


def length_in(segs, box):
    """Extruded length inside an XY box (segments clipped to it)."""
    x0, x1, y0, y1 = box
    tot = 0.0
    for (ax, ay), (bx, by) in segs:
        n = max(2, int(math.hypot(bx - ax, by - ay) / 0.05))
        for i in range(n):
            t0, t1 = i / n, (i + 1) / n
            mx, my = ax + (bx - ax) * (t0 + t1) / 2, ay + (by - ay) * (t0 + t1) / 2
            if x0 <= mx <= x1 and y0 <= my <= y1:
                tot += math.hypot(bx - ax, by - ay) / n
    return tot


def features():
    """Feature boxes to read back, in the CAD frame: (part, name, (x0, x1, y0, y1, z0, z1))."""
    import params as P, lid, keys, midplate
    out = []
    # the latch arms' inner top chamfer (params.SNAP_INNER_CHAMFER; the light strip's Y-83 arm first, every arm since
    # 2026-10-12) in their top two layers. Nothing should print over the inner part (X -0.95..-0.62, clear of the
    # flat's lines). The flat left on top (X -1.40..-1.00) prints in the lower of the two only: the top layer's section
    # is 0.235 wide and drops out, so the arm ends 0.2 lower than x3's (1/2 is the expected result; the lead-in meets
    # the wall's face at Z 2.34, below it). The Y-68.5 arm (until 2026-10-12 the square-topped control: 2/2) now reads
    # as the Y-83 one. With every arm chamfered no arm reaches the lid's top layer any more, so the slicer makes none:
    # the window holds one layer (chamfer 0/1, flat 1/1)
    import joint
    _, h = joint.snap_profile()
    zt = h['z_top']
    for nm, yc, xs in (('latch_arm_Y83_chamfer!', 83.0, (-0.95, -0.62)), ('latch_arm_Y83_flat', 83.0, (-1.40, -1.00)),
                       ('latch_arm_Y68_chamfer!', 68.5, (-0.95, -0.62)), ('latch_arm_Y68_flat', 68.5, (-1.40, -1.00))):
        out.append(('lid', nm, (xs[0], xs[1], yc - 1.5, yc + 1.5, zt - 0.145, zt - 0.015)))
    out += bottom_key_features()
    out += gate_features()
    out += latch_arm_root_features()
    for cx, cy, ax in midplate.SPRINGS[:3]:
        L = midplate.SPRING_L
        hx, hy = (L / 2 - 1.0, 1.0) if ax == 'x' else (1.0, L / 2 - 1.0)
        out.append(('midplate', f'spring_{cx:g}_{cy:g}', (cx - hx, cx + hx, cy - hy, cy + hy, P.MID_REAR, P.MID_REAR + midplate.SPRING_T)))
    # light strip (its tub only; x3 read back no tub boxes): the channel's 0.4 skin, the seat the bar rests on (a 0.71
    # overhang in the face-down tub) and a hold-down pad
    if P.LIGHT_STRIP:
        out.append(('tub', 'strip_channel_skin', (-1.0, 1.8, 20.0, 70.0, P.CHANNEL_TOP + 0.02, P.Z_FRONT - 0.02)))
        out.append(('tub', 'strip_seat', (P.WALL_X0 + 0.05, P.SEAT_X1 - 0.05, 20.0, 70.0, P.FRAME_REAR + 0.02, P.LIP - 0.02)))
        # where the seat starts (SEAT_Y[0]): it prints from there on, and below it (under the foot's pocket and on to
        # SEAT_Y[0]) the frame is gone from the wall, so nothing prints there
        out.append(('tub', 'strip_seat_start', (P.WALL_X0 + 0.05, P.SEAT_X1 - 0.05, P.SEAT_Y[0] + 0.25, P.SEAT_Y[0] + 1.25,
                                                P.FRAME_REAR + 0.02, P.LIP - 0.02)))
        out.append(('tub', 'strip_seat_cut_below!', (P.WALL_X0 + 0.05, P.SEAT_X1 - 0.05, P.LOCATOR_Y[1] + 0.3, P.SEAT_Y[0] - 0.25,
                                                    P.FRAME_REAR + 0.02, P.LIP - 0.02)))
        yc = P.PAD_Y[1]
        out.append(('tub', 'strip_pad', (P.PAD_X[0] + 0.05, P.PAD_X[1] - 0.25, yc - 0.4, yc + 0.4, P.LIP + 0.02, P.LIP + 0.45)))
        # a stop rib: the wall's outer perimeter jogs out to it (line centre 0.21 inside the rib's face, X -1.45); the
        # control box is the same box on the plain wall beside it, where the perimeter runs at X -1.63 (above the rib since
        # the pad ribs: 2.5 below it is now under pad 2's rib)
        R = P.STRIP_RIBS
        for nm, y in (('strip_rib', R['y'][2]), ('strip_rib_control!', R['y'][2] + 2.5)):
            out.append(('tub', nm, (R['x1'] - 0.26, R['x1'] - 0.06, y - 0.6, y + 0.6, P.LIP + 0.02, P.CHANNEL_TOP - 0.02)))
        y = R['y'][-1]                              # a fold-zone rib, down to z_fold past the folded piece
        out.append(('tub', 'strip_rib_fold', (R['x1'] - 0.26, R['x1'] - 0.06, y - 0.6, y + 0.6, R['z_fold'] + 0.02, P.CHANNEL_TOP - 0.02)))
        # the foot's pocket: its roof layer prints, the pocket under it stays empty right up to the window's edge (the old
        # 0.28 strip of lip is gone on purpose)
        fp = P.FOOT_POCKET
        out.append(('tub', 'foot_pocket_roof', (3.0, 7.0, 10.0, 12.5, fp['top'] + 0.02, fp['top'] + 0.18)))
        out.append(('tub', 'foot_pocket_void!', (3.0, 14.0, 10.0, fp['y1'] - 0.05, P.LIP + 0.02, fp['top'] - 0.02)))
    # the midplate beside SW7's front lead holes, where the notch now runs into them: nothing should print there (the
    # plate is shared, so in both builds)
    out.append(('midplate', 'notch_into_sw7_holes!', (P.MID_RELIEF['x1'] + 0.02, 2.2, 76.9, 79.1, P.MID_REAR + 0.02, P.DISP_REAR - 0.02)))
    # retention fixes (2026-09-26): a pad rib prints on all its layers under the ceiling and nothing prints below it
    # (the bar's flex passes there); the corner stops' new rear part below the frame prints (the light-strip tub); the
    # midplate's notches under the stops stay empty (the shared plate: both builds)
    if P.LIGHT_STRIP:
        PR = P.PAD_RIBS
        yc = PR['y'][1]
        out.append(('tub', 'pad_rib', (-0.8, 1.2, yc - 0.6, yc + 0.6, PR['z0'] + 0.02, P.CHANNEL_TOP - 0.02)))
        out.append(('tub', 'pad_rib_underside_void!', (-0.8, 1.2, yc - 0.6, yc + 0.6, P.LIP + 0.02, PR['z0'] - 0.02)))
        for nm, (y0, y1) in (('corner_stop_rear_bottom', P.LOCATOR_Y), ('corner_stop_rear_top', P.LOCATOR_Y_TOP)):
            out.append(('tub', nm, (-1.2, 1.0, y0 + 0.15, y1 - 0.15, P.LOCATOR_Z0 + 0.02, P.FRAME_REAR - 0.02)))
    for nm, (y0, y1) in (('stop_notch_bottom', (7.5, 9.3)), ('stop_notch_top', (92.8, 93.6))):
        out.append(('midplate', nm + '!', (-1.0, P.MID_STOP_NOTCH['x1'] - 0.1, y0, y1, P.MID_REAR + 0.02, P.DISP_REAR - 0.02)))
    return out


def latch_arm_root_features():
    """One judged box per latch arm (2026-10-19, the thicker arms: 1.3 at the root, params.SNAP): the arm's inner
    perimeter must print through the root's last 1.7 mm. u runs inward from the wall's inner face; the box takes u
    0.96..1.21, the strip that today's arm (1.0 at the root) does not reach, and every layer through it must carry
    extrusion (as the bottom keys' boxes: judged)."""
    import params as P, joint
    out = []
    for wall, cs in P.SNAPS.items():
        w = joint.WALLS[wall]
        for c in cs:
            u0, u1 = (w['face'] - w['out'] * 0.96, w['face'] - w['out'] * 1.21)
            lo, hi = min(u0, u1), max(u0, u1)
            bx = (lo, hi, c - 1.5, c + 1.5, -6.3, -4.6) if w['axis'] == 'y' else (c - 1.5, c + 1.5, lo, hi, -6.3, -4.6)
            out.append(('lid', f'latch_arm_root_{wall}{c:g}', bx))
    return out


def bottom_key_features():
    """The bottom keys' boxes (crank spec check 8). Tub boxes in the CAD frame; the key and the cranks in their own
    frame (dx from the key's centre). A name ending in '!' expects no extrusion ('absent')."""
    import params as P, keys, tub
    out = []
    lip, (ya, yb), (py, pz) = P.LIP, P.RAIL_Y, P.ROD_AXIS
    xs = tub.key_x()
    for i, (kind, x0, x1) in enumerate(tub.rail_segments()):
        a, b = max(x0, P.WALL_X0) + 0.2, x1 - 0.2
        if kind == 'ring':               # the full ring round each closed bore: below its flat, beside it, above it
            rr = P.ROD_HOLE_D / 2 + 0.08
            out += [('tub', f'ring{i}_below', (a, b, py - 0.3, py + 0.3, P.RING_BOTTOM + 0.1, pz - P.ROD_TEARDROP_FLAT - 0.05)),
                    ('tub', f'ring{i}_plus_y', (a, b, py + rr, yb - 0.05, pz - 0.3, pz + 0.3)),
                    ('tub', f'ring{i}_minus_y', (a, b, ya + 0.05, py - rr, pz - 0.3, pz + 0.3)),
                    ('tub', f'ring{i}_above', (a, b, py - 0.3, py + 0.3, pz + rr, lip - 0.05))]
        elif kind == 'seat':             # the open seat's two lips, each just clear of its sharp tip (the spec's
            # boxes, y -1.6..-1.5 and -2.7..-2.6, lie on the tips' 10 / 262 degree mouth edges and in the bore)
            out += [('tub', f'seat{i}_lip_A', (a, b, -1.3, -1.0, 0.95, 1.15)),
                    ('tub', f'seat{i}_lip_B', (a, b, -2.95, -2.75, -0.85, -0.5))]
        else:                            # over the cheek's slot: its roof (the skin, SLOT_ROOF = LIP since 2026-10-12)
            # prints, the slot under it stays open up to it
            out += [('tub', f'slot{i}_roof', (a, b, ya + 0.1, yb - 0.1, P.SLOT_ROOF + 0.02, P.SLOT_ROOF + 0.6)),
                    ('tub', f'slot{i}_open!', (a, b, ya + 0.1, yb - 0.1, 0.0, P.SLOT_ROOF - 0.1))]
    for j, (a, b) in enumerate(web_spans(xs)):
        out.append(('tub', f'web{j}', (a + 0.2, b - 0.2, P.BOT_IN + 0.1, ya - 0.075, P.WEB['z0'] + 0.1, lip - 0.02)))
    O = P.KEY_OPENING
    for xc in xs[:1] + xs[-1:]:
        out.append(('tub', f'ledge_{xc:.0f}', (xc - 5.0, xc + 5.0, P.BOT_IN + 0.02, O['y'][0] - 0.02, lip + 0.02, P.Z_FRONT - 0.35)))
        out.append(('tub', f'lead_in_{xc:.0f}!', (xc - 5.0, xc + 5.0, P.BOT_IN - 0.25, P.BOT_IN - 0.05, P.SEAM + 0.02, P.SEAM + 0.15)))
    # the hook slots (test 2): each empty from the rim to its roof, the chin wall behind it printed from the rim (its
    # last layer included: no seam chamfer over the key row, KEY_SLOT relief; hverify1 F1) to the roof (0.45 thick on
    # x3std: one line) across the slot's whole width (verify: x cover), and the wall over the roof printed. The
    # coupon's strip (cut from the tub) has SW9's two slots
    (sa, sb), yb, zr = P.KEY_SLOT['dx'], P.KEY_SLOT['back'], P.KEY_SLOT_ROOF
    for part, xcs in (('tub', xs), ('coupon-strip', xs[:1])):
        for xc in xcs:
            for sd, (a, b) in (('m', (xc - sb, xc - sa)), ('p', (xc + sa, xc + sb))):
                nm = f'{xc:.0f}{sd}'
                out += [(part, f'hook_slot_{nm}!', (a + 0.1, b - 0.1, yb + 0.05, P.BOT_IN - 0.05, P.SEAM + 0.02, zr - 0.05)),
                        (part, f'hook_slot_wall_{nm}', (a + 0.1, b - 0.1, P.Y0 + 0.05, yb - 0.05, P.SEAM + 0.02, zr - 0.05)),
                        (part, f'hook_slot_roof_{nm}', (a + 0.1, b - 0.1, yb + 0.05, P.BOT_IN - 0.05, zr + 0.05, zr + 0.45))]
    z0, Pu, Hk = P.KEY_CAP_Z0, P.KEY_PUSHER, P.KEY_HOOK
    (hz0, hz1), (hx0, hx1), tip, y0 = P.KEY_HOOK_Z, Hk['dx'], Hk['tip'], P.KEY_Y[0]
    ylead = round(tip + (hx0 - 3.6) + 0.05, 3)               # the lead's reach at dx 3.6 (it grows 45 degrees to the tip)
    k = keys.NAME
    # on its -X end: each hook's YZ section prints in every layer through it (the -X hook from past the bed end's 0.4;
    # the +X hook to its last whole layer, 4.80), the +X hook's lead builds up at dx 3.6..3.8, nothing chin-side of the
    # cap's face over the hooks; the pusher's chin end below stop_z1 (the chin-side stop, 0.40 off the chin wall) prints,
    # and over it, clear of the hooks and the lead, nothing does. X from -4.4: the bed end's first two layers come in
    # KEY_BED_END
    # the root (KEY_ROOT): under the -X hook the chin side is solid out to the hooks' tip, in its third layer (past the
    # bed end's two)
    out += [(k, 'root', (-P.KEY_HALF + 0.45, -P.KEY_HALF + P.KEY_ROOT - 0.05, tip + 0.05, y0 - 0.05, Pu['z0'] + 0.05, hz0 - 0.05)),
            (k, 'hook_minus_x', (-hx1 + 0.55, -hx0 - 0.1, tip + 0.05, y0 - 0.05, hz0 + 0.05, hz1 - 0.05)),
            (k, 'hook_plus_x', (hx0 + 0.1, hx1 - 0.2, tip + 0.05, y0 - 0.05, hz0 + 0.05, hz1 - 0.05)),
            (k, 'hook_lead', (3.6, 3.8, ylead, y0 - 0.07, hz0 + 0.05, hz1 - 0.05)),
            (k, 'over_the_hooks!', (hx0 + 0.1, hx1 - 0.2, tip + 0.05, y0 - 0.1, hz1 + 0.1, hz1 + 0.6)),
            # (0.30 deep: the outer wall's line runs half a line, 0.21, inside the pusher's chin face)
            (k, 'pusher_stop', (-3.4, 2.8, Pu['y'][0] + 0.05, Pu['y'][0] + 0.35, Pu['z0'] + 0.02, Pu['stop_z1'] - 0.05)),
            (k, 'over_stop_step!', (-3.4, 2.8, Pu['y'][0] + 0.05, y0 - 0.05, Pu['stop_z1'] + 0.25, z0 - 0.1))]
    for c, nc in (('crank-M', P.CRANK_NOSE_C['M']), ('crank-T', P.CRANK_NOSE_C['T'])):
        for sg in (-1, 1):
            a, b = sorted((sg * 4.1, sg * 4.9))
            out += [(c, f'bore_wall_minus_y_{sg:+d}', (a, b, py - 1.62, py - 1.05, pz - 0.25, pz + 0.25)),
                    (c, f'bore_wall_above_{sg:+d}', (a, b, py - 0.3, py + 0.3, pz + 1.05, pz + 1.7)),
                    (c, f'bore_wall_below_{sg:+d}', (a, b, py - 0.6, py - 0.1, pz - 1.6, pz - 1.05))]
            # test 1: the cheek closed round the rod where the lip's C is open, and its fill down to the belly. z -1.0
            # .. -0.3 (the spec's -0.5..0.0 is the bore's lower wall, whose line runs just under -0.5 in two of the
            # three layers there): the ring's wall under the bore, all inside the C's sector
            a2, b2 = sorted((sg * 4.2, sg * 5.1))
            a3, b3 = sorted((sg * 3.8, sg * 4.0))
            out += [(c, f'ring_closed_where_the_C_was_{sg:+d}', (a2, b2, -2.2, -1.7, -1.0, -0.3)),
                    (c, f'fill_{sg:+d}', (a2, b2, -2.8, -2.0, -2.1, -1.4)),
                    (c, f'lip_C_still_open_{sg:+d}!', (a3, b3, -2.2, -1.7, -1.0, -0.3))]
        out += [(c, 'crown', (-5.0, 5.0, -7.6, -7.3, -0.7, -0.35)),
                (c, 'nose', (-1.1, 1.1, nc[0] + 0.4, nc[0] + 0.85, nc[1] - 0.25, nc[1] + 0.25)),
                (c, 'belly', (2.0, 3.4, -3.9, -3.2, -1.9, -1.4)),
                (c, 'crossbar_underside', (-4.0, 4.0, -6.4, -5.0, P.CRANK_UNDERSIDE + 0.05, P.CRANK_UNDERSIDE + 0.3))]
    return out


def gate_features():
    """SPEC2 rev 3 check 9: the gate's slot in the tub and in its proof coupon (cut from the tub in the CAD frame, so the
    same boxes), and the gate (boxes in its installed pose; plates.ORIENT turns them with it). A name ending in '!'
    expects no extrusion."""
    import params as P, tub
    out = []
    for part in ('tub', 'coupon-gate'):
        out += [(part, 'gate_mouth_open!', (-4.0, -3.1, -3.7, -1.3, -3.7, 0.5)),
                (part, 'gate_cavity_open!', (-2.9, -2.3, -4.2, -0.8, -3.7, 0.8)),
                (part, 'gate_end_open_minus_y!', (-2.75, -2.45, -4.65, -4.40, -3.7, 0.8)),
                (part, 'gate_end_open_plus_y!', (-2.75, -2.45, -0.60, -0.35, -3.7, 0.8)),
                (part, 'lip_minus_y', (-4.0, -3.1, -4.30, -3.95, P.SEAM + 0.02, tub.floor_z(-3.1) - 0.05)),
                (part, 'lip_plus_y', (-4.0, -3.1, -1.05, -0.70, P.SEAM + 0.02, tub.floor_z(-3.1) - 0.05))]
        # the floor: 0.05 to 0.35 under its surface at the box's -X end (the floor slopes 45 degrees down toward +X, so
        # the whole box is floor), under the flange's wing and on into the round end (y to -4.6, not the spec's -4.2:
        # the walls there run along Y, and a 0.3-wide box holds only 0.3 of each line against the 0.5 a layer needs)
        f = tub.floor_z(-2.9)
        out.append((part, 'gate_floor', (-2.9, -2.5, -4.6, -3.9, f + 0.05, f + 0.35)))
    x0, G = P.X0, P.GATE
    out += [('gate', 'pull_wall_minus_y', (x0 + 0.1, x0 + 0.9, -3.70, -3.20, -2.5, -1.5)),
            ('gate', 'pull_wall_plus_y', (x0 + 0.1, x0 + 0.9, -1.80, -1.30, -2.5, -1.5)),
            ('gate', 'pull_wall_above', (x0 + 0.1, x0 + 0.9, -2.8, -2.2, P.SEAM + G['top_clr'] + 0.35,
                                         G['pull_z'] - G['pull_d'] / 2 - 0.1)),
            ('gate', 'pull_hole!', (x0 + 0.1, x0 + 0.9, -2.8, -2.2, G['pull_z'] - 0.3, G['pull_z'] + 0.3)),
            ('gate', 'flange_wing_minus_y', (-2.95, -2.62, -4.10, -3.80, -3.0, 0.5)),     # its wings, clear of the
            ('gate', 'flange_wing_plus_y', (-2.95, -2.62, -1.20, -0.90, -3.0, 0.5))]      # 0.40 bed chamfers
    return out


def web_spans(xs):
    import params as P
    s1 = P.SLOT[1]
    return [(P.WEB['x_ends'][0], xs[0] - s1)] + [(a + s1, b - s1) for a, b in zip(xs, xs[1:])] + [(xs[-1] + s1, P.WEB['x_ends'][1])]


_OFFSETS = {}                            # _offset's result per part and G-code (verify() asks once per feature box)


def _offset(part, mm, gcode):
    """Where the slicer put the part on the bed: the extrusion's centre against the oriented mesh's (mm, moved to the
    origin), layer by layer, each layer's lines against the mesh's own section at that layer's mid-plane (where Orca
    slices it). Each layer is read twice, by its lines' centres and by its lines carried half their own width out (as
    deposited: wide_extrusions), and the offset is the median of both readings over every layer but the first and the
    last. A layer that does not match is outvoted: the first (elephant-foot compensated), one that drops a thin feature
    on one side (the key's bed end), one whose two faces print as lines of different widths (the coupon strip's -Y face
    in most of its layers: its centres alone read 0.011 off in Y) and one with a line that reaches past the outline
    (the gate's flange layers: its widths alone read 0.0075 off). 2026-10-03: until then the case parts were matched on
    their first layer alone and the small parts on all their layers' line centres against the mesh's bounds; the tub's
    and the lid's first layers come in 0.35 on three sides but 0.25 on the fourth, which put the tub 0.050 off in Y and
    the lid 0.049 off in X. Every part here now reads Orca's real shift, (0, -1.50), within 0.001. Says so if a part's
    layers disagree (over 0.02)."""
    import numpy as np
    gcode = Path(gcode)
    key = (part, str(gcode), gcode.stat().st_mtime_ns)
    if key in _OFFSETS:
        return _OFFSETS[key]
    layers = wide_extrusions(gcode)
    zs = sorted(layers)
    per = []
    for z in (zs[1:-1] if len(zs) > 4 else zs):
        sec = mm.section(plane_origin=[0, 0, z - 0.1], plane_normal=[0, 0, 1])
        if not layers[z] or sec is None:
            continue
        mc = (sec.bounds[0][:2] + sec.bounds[1][:2]) / 2
        for k in (0.0, 0.5):                     # the lines' centres; carried half their width out
            x0 = min(min(a[0], b[0]) - k * w for a, b, w in layers[z])
            x1 = max(max(a[0], b[0]) + k * w for a, b, w in layers[z])
            y0 = min(min(a[1], b[1]) - k * w for a, b, w in layers[z])
            y1 = max(max(a[1], b[1]) + k * w for a, b, w in layers[z])
            per.append(((x0 + x1) / 2 - mc[0], (y0 + y1) / 2 - mc[1]))
    per = np.array(per)
    off = np.median(per, axis=0)
    agree = np.abs(per - off).max(axis=1) <= 0.02
    if agree.mean() < 0.5:
        print(f'  _offset {part}: its layers disagree on where the slicer put it ({int(agree.sum())} of {len(per)} '
              f'readings within 0.02 of the median {off.round(3)})   <-- CHECK', flush=True)
    _OFFSETS[key] = off
    return off


def _to_print(part, info):
    """CAD -> print-frame mapping for a part as sliced: returns (M, shift, off, layers) so that a CAD point q maps to
    (M @ q)[:3] + shift, then + off in XY (the slicer's placement on the bed: _offset)."""
    import numpy as np, trimesh, plates
    layers = extrusions(hw.ROOT / info['gcode'])
    m = trimesh.load(hw.OUT / f'{part}.stl')
    axis, deg = plates.ORIENT[part]
    M = np.eye(4)
    if axis:
        vec = {'x': [1, 0, 0], 'y': [0, 1, 0], 'z': [0, 0, 1]}[axis]
        M = trimesh.transformations.rotation_matrix(np.radians(deg), vec)
    m.apply_transform(M)
    shift = -m.bounds[0]
    mm = m.copy()
    mm.apply_translation(shift)
    off = _offset(part, mm, hw.ROOT / info['gcode'])
    first = layers[min(layers)]
    gx = [p[0] for s in first for p in s]
    gy = [p[1] for s in first for p in s]
    return M, shift, off, layers, (round(max(gx) - min(gx), 2), round(max(gy) - min(gy), 2))


def bores(report, line_w=0.42):
    """The rod's holes read back from the G-code: each bore runs along X, so every layer through it shows two lines
    along X either side of the axis; the gap between them less a line's width is the free chord at that layer's height,
    and each chord gives the free diameter of the circle through it, taken at the layer's edge nearer the axis (|dz| -
    0.1): a layer is solid over its whole 0.2, so that edge is where it pinches the round rod (read at mid-layer, the
    stair-stepped 1.95 bores came back as 1.95 while a 1.75 rod was all that fitted). The least over the layers within
    1.2 of the axis is the printed free diameter: the tub's sliver bore and ring bores (>= 1.90), each crank's cheek
    bores (>= 1.80 before reaming to 1.9)."""
    import numpy as np, params as P, tub
    (py, pz) = P.ROD_AXIS
    jobs = []
    xs0 = P.GATE_SLOT_X[2] + P.GATE_SLOT['sliver_lead'] + 0.05     # the sliver's bore past its lead-in
    if report.get('coupon-gate', {}).get('gcode'):
        jobs.append(('coupon-gate', 'sliver_hole', (xs0, P.WALL_X0), 1.90))
    if report.get('tub', {}).get('gcode'):
        jobs.append(('tub', 'sliver_hole', (xs0, P.WALL_X0), 1.90))
        for i, (kind, x0, x1) in enumerate(tub.rail_segments()):
            if kind == 'ring':
                jobs.append(('tub', f'ring{i}_bore', (max(x0, P.WALL_X0) + 0.3, x1 - 0.3), 1.90))
    for c in ('crank-M', 'crank-T'):
        if report.get(c, {}).get('gcode'):
            for sg in (-1, 1):
                a, b = sorted((sg * 4.15, sg * 4.85))
                jobs.append((c, f'cheek_bore_{sg:+d}', (a, b), 1.80))
    maps, rows = {}, []
    for part, name, (xa, xb), need in jobs:
        if part not in maps:
            maps[part] = _to_print(part, report[part])
        M, shift, off, layers, _ = maps[part]
        pt = lambda x, y, z: (M @ np.array([x, y, z, 1.0]))[:3] + shift + np.array([off[0], off[1], 0.0])
        ax0, ax1 = pt(xa, py, pz), pt(xb, py, pz)
        lo_x, hi_x = sorted((ax0[0], ax1[0]))
        ay, az = ax0[1], ax0[2]
        best = None
        for z, segs in layers.items():
            zc = z - 0.1                                       # the layer's middle
            if abs(zc - az) > 1.2:
                continue
            dz = max(0.0, abs(zc - az) - 0.1)                  # its edge nearer the axis
            ys = []
            for (x0, y0), (x1, y1) in segs:
                if abs(y1 - y0) < 0.05 and min(x0, x1) < hi_x - 0.1 and max(x0, x1) > lo_x + 0.1:
                    ys.append((y0 + y1) / 2)
            below = [y for y in ys if y < ay]
            above = [y for y in ys if y > ay]
            if not below or not above:
                continue
            chord = min(above) - max(below) - line_w
            dfree = 2 * math.sqrt((chord / 2) ** 2 + dz ** 2)
            if best is None or dfree < best[0]:
                best = (dfree, round(z, 2), round(chord, 3))
        rows.append({'part': part, 'bore': name, 'free_d_mm': round(best[0], 3) if best else None,
                     'at_layer_z': best[1] if best else None, 'chord_mm': best[2] if best else None,
                     'need_mm': need, 'ok': bool(best and best[0] >= need)})
    return rows


def verify(report):
    """Map each feature box into its sliced part's G-code and measure the extrusion inside it, layer by
    layer. The slicer keeps the part where plates.py put it except for a shift on the bed, found by
    matching its layers' extents to the oriented mesh's sections (_offset)."""
    import numpy as np, trimesh, plates
    rows = []
    new = {(pt, nm) for pt, nm, _ in bottom_key_features() + gate_features() + latch_arm_root_features()}
    for part, name, bx in features():
        info = report.get(part)
        if not info or not info.get('gcode'):
            continue
        layers = extrusions(hw.ROOT / info['gcode'])
        m = trimesh.load(hw.OUT / f'{part}.stl')
        axis, deg = plates.ORIENT[part]
        M = np.eye(4)
        if axis:
            vec = {'x': [1, 0, 0], 'y': [0, 1, 0], 'z': [0, 0, 1]}[axis]
            M = trimesh.transformations.rotation_matrix(np.radians(deg), vec)
        m.apply_transform(M)
        shift = -m.bounds[0]
        corners = np.array([[x, y, z, 1.0] for x in bx[:2] for y in bx[2:4] for z in bx[4:]]).T
        pc = (M @ corners)[:3].T + shift
        lo, hi = pc.min(axis=0), pc.max(axis=0)
        first = layers[min(layers)]
        gx = [p[0] for s in first for p in s]
        gy = [p[1] for s in first for p in s]
        mm = m.copy()
        mm.apply_translation(shift)
        off = _offset(part, mm, hw.ROOT / info['gcode'])
        box = (lo[0] + off[0], hi[0] + off[0], lo[1] + off[1], hi[1] + off[1])
        judged = (part, name) in new
        if judged:                       # the layers (0.2, top at z) that really cross the box
            per = {z: round(length_in(segs, box), 1) for z, segs in layers.items() if z > lo[2] + 0.02 and z - 0.2 < hi[2] - 0.02}
        else:                            # the older boxes' window, as before
            per = {z: round(length_in(segs, box), 1) for z, segs in layers.items() if lo[2] - 0.01 <= z <= hi[2] + 0.21}
        filled = sum(1 for v in per.values() if v > 0.5)
        absent = name.endswith('!')
        ok = (filled == 0 if absent else filled == len(per)) if judged else None
        row = {'part': part, 'feature': name.rstrip('!'), 'expect': 'absent' if absent else 'present',
               'z_print': [round(lo[2], 2), round(hi[2], 2)], 'layers': len(per), 'layers_with_extrusion': filled,
               'ok': ok, 'mm_per_layer': per,
               'first_layer_extent_mm': [round(max(gx) - min(gx), 2), round(max(gy) - min(gy), 2)]}
        if name.startswith('hook_slot_wall'):          # across the slot's whole width, in every layer (CAD X, as printed)
            axis = 0 if abs(M[0][0]) > 0.5 else 1
            cov = {z: round(x_cover(layers[z], box, axis), 3) for z in per}
            row['x_cover_min'] = min(cov.values()) if cov else 0.0
            row['x_cover_per_layer'] = cov
            row['ok'] = ok and row['x_cover_min'] >= 1.0 - 1e-9
        rows.append(row)
    return rows


def show(report):
    for f in report['_features']:
        print(f"  {f['part']:12s} {f['feature']:24s} {f['expect']:7s} {f['layers_with_extrusion']}/{f['layers']} layers extruded"
              f"{', across the slot >= ' + str(f['x_cover_min']) if 'x_cover_min' in f else ''}"
              f"{'   <-- CHECK' if f['ok'] is False else ''}")
    for b in report['_bores']:
        print(f"  {b['part']:12s} {b['bore']:24s} free d {b['free_d_mm']} (need {b['need_mm']}){'' if b['ok'] else '   <-- CHECK'}")
    for p, r in report.get('_first_layer', {}).items():
        if 'width_mm' in r:
            print(f"  {p}: first layer {r['width_mm']} mm wide as laid (need >= 1.0){'' if r['ok'] else '   <-- CHECK'}")
        else:
            print(f"  {p}: first layer (its -X end) {r['area_mm2']} mm2 (need >= {KEY_BED_AREA_MIN}), outside the key's outline "
                  f"{r['outside_outline_mm2']} mm2{'' if r['ok'] else '   <-- CHECK'}")
    for p, r in report.get('_bridges', {}).items():
        print(f"  {p}: bridge extrusion in the gate's slot {r['bridge_mm']} mm (need 0; internal bridges, over infill, "
              f"{r.get('internal_bridge_mm', 0.0)} mm){'' if r['ok'] else '   <-- CHECK'}")
    g = report.get('_gate')
    if g:
        print(f"  gate: first layer {g['first_layer']} ({'the flange' if g['first_layer_is_flange'] else 'NOT the flange'}); "
              f"steepest overhang {g['steepest_overhang_deg']} deg (<= 45); pull hole free d {g['pull_hole_free_d']} (>= 1.15); "
              f"thinnest wall {g['thinnest_wall_mm']} (>= 0.45){'' if g['ok'] else '   <-- CHECK'}")
    for p, r in report.get('_islands', {}).items():
        print(f"  {p}: {r['layers']} layers, up to {r['most_pieces_in_a_layer']} pieces in a layer, "
              f"{len(r['floating'])} not on the layer below (need 0), reach past the layer below {r.get('reach_max_mm')} "
              f"(<= {OVERHANG_REACH_MAX}){'' if r['ok'] else '   <-- CHECK ' + str(r['floating'][:3]) + ' ' + str(r.get('reach_at'))}")
    for p, r in report.get('_crank_sections', {}).items():
        print(f"  {p} ({r['wall_generator']} walls): sliced cheek over its design, worst {r['worst']} (need >= "
              f"{CHEEK_SLICED_MIN}){'' if r['ok'] else '   <-- CHECK'}")
    for p, r in report.get('_key_on_end', {}).items():
        print(f"  {p} on its end: {r['layers_in_the_hooks']} hook layers, worst cover {r['worst_hook_cover']} (>= "
              f"{HOOK_COVER_MIN}); seams on show {r['seams_on_show']}{'' if r['ok'] else '   <-- CHECK'}")
    for p, r in report.get('_no_support', {}).items():
        what = r.get('lines_mm', r.get('lines_mm_round_the_slots'))
        print(f"  {p}: support / bridge / overhang lines {what or 'none'}"
              f"{' round its ' + str(r['slots']) + ' hook slots' if 'slots' in r else ''}{'' if r['ok'] else '   <-- CHECK'}")


OVERHANG_REACH_MAX = 0.5                 # mm a layer may reach past the one below (Ian's no-support rule; the 4.26's)


def islands(report):
    """The keys (on their -X end) and the cranks (on their pad end), every layer: each piece of material (the layer's
    lines thickened to their widths, round ends, merged) must stand on the layer below (at least a fifth of it over it),
    so nothing starts in mid-air (test 1, 2026-09-29; the crank study's s11 reading), and no layer may reach past the
    one below by more than OVERHANG_REACH_MAX (the largest distance of any point of its material from the layer below's:
    a 45-degree face steps 0.2, a flat overhang reaches as far as it hangs; Orca lays a short one as plain wall, with no
    overhang line). Several pieces in a layer are by design: in a few layers Orca splits off the pusher's 0.28 strip over
    the cheek zones; the crank's two cheeks and its nose are separate pieces above the crossbar. Reported: the most
    pieces in a layer; judged: floating pieces (none) and the reach."""
    import numpy as np
    import shapely
    from shapely.geometry import LineString
    from shapely.ops import unary_union
    out = {}
    for p, info in report.items():
        if p.startswith('_') or not p.startswith(('key-', 'crank-')) or not info.get('gcode'):
            continue
        layers = wide_extrusions(hw.ROOT / info['gcode'])
        prev, most, floating, reach = None, 0, [], (0.0, None)
        for z in sorted(layers):
            g = unary_union([LineString([a, b]).buffer(w / 2, cap_style=1) for a, b, w in layers[z] if a != b])
            pieces = [q for q in getattr(g, 'geoms', [g]) if q.area > 0.005]
            most = max(most, len(pieces))
            if prev is not None:
                floating += [{'z': z, 'mm2': round(q.area, 3), 'at': [round(c, 2) for c in q.centroid.coords[0]]}
                             for q in pieces if q.intersection(prev).area < 0.2 * q.area]
                for q in pieces:
                    pts = np.array(q.exterior.segmentize(0.02).coords)
                    d = shapely.distance(shapely.points(pts), prev)
                    j = int(np.argmax(d))
                    if d[j] > reach[0]:
                        reach = (float(d[j]), {'z': z, 'at': [round(float(c), 2) for c in pts[j]]})
            prev = g
        out[p] = {'layers': len(layers), 'most_pieces_in_a_layer': most, 'floating': floating,
                  'reach_max_mm': round(reach[0], 3), 'reach_at': reach[1],
                  'ok': not floating and reach[0] <= OVERHANG_REACH_MAX}
    return out


KEY_BED_AREA_MIN = 7.5                   # mm2: the key's first layer on the bed (on its -X end, 10.0 tall); on the raft
                                         # (RAFT, 2026-10-06) the key's first layer over it


def first_layers(report):
    """The cranks stand on their pad end (1.10 x 10.5 modelled): the first layer's width as laid, its outermost lines
    carried out by half their own ;WIDTH (the elephant-foot compensation takes 0.1 off each side). Until 2026-10-06 this
    was the lines' centres apart plus 0.5 (the bed's first-layer line), which read 1.09: Arachne lays the pad end as one
    0.63 loop (1.23 as laid). On the raft (RAFT) the first layer is the crank's first over it, at the layers' own widths
    (two loops, 0.42-0.47: 1.23 as laid). The keys stand on
    their -X end (test 1): the first layer's area as deposited (its lines at their widths, round ends) >= KEY_BED_AREA_MIN,
    and all of it inside the key's outline there (its section 0.45 in, inside the root block): KEY_BED_END's 0.30 keeps
    the squashed first layer in."""
    import trimesh, params as P
    from shapely.geometry import Point
    out = {}
    for p, info in report.items():
        if not p.startswith('_') and p.startswith('key-') and info.get('gcode'):
            c1, g1 = min(device_layers(p, info, ends='round'), key=lambda q: q[0])
            m = trimesh.load(hw.OUT / f'{p}.stl')
            sec = _section(m, 0, -P.KEY_HALF + 0.45)
            outside = g1.difference(sec)
            far = max([Point(q).distance(sec) for g in getattr(outside, 'geoms', [outside]) if not g.is_empty
                       for q in g.exterior.coords] or [0.0])
            out[p] = {'layer_dx': c1, 'area_mm2': round(g1.area, 2), 'outside_outline_mm2': round(outside.area, 4),
                      'outside_outline_max_mm': round(far, 3), 'ok': g1.area >= KEY_BED_AREA_MIN and outside.area <= 0.005}
    for p, info in report.items():
        if not p.startswith('_') and p.startswith('crank') and info.get('gcode'):
            layers = wide_extrusions(hw.ROOT / info['gcode'])
            first = layers[min(layers)]
            gx = [q[0] for s in first for q in s[:2]]
            gy = [q[1] for s in first for q in s[:2]]
            ext = sorted((max(gx) - min(gx), max(gy) - min(gy)))
            span = lambda i: (max(max(s[0][i], s[1][i]) + s[2] / 2 for s in first)
                              - min(min(s[0][i], s[1][i]) - s[2] / 2 for s in first))
            wl = sorted((span(0), span(1)))
            out[p] = {'line_centres_mm': [round(e, 2) for e in ext], 'width_mm': round(wl[0], 2),
                      'length_mm': round(wl[1], 2), 'ok': wl[0] >= 1.0}
    return out


def typed_extrusions(gcode):
    """{z: [(type, ((x0, y0), (x1, y1))), ...]}: extrusions() with each move's ';TYPE:' (Bridge, Internal Bridge, ...).
    A part on a raft: as extrusions() (the raft's Support lines are not the part's)."""
    layers, z, x, y, kind = {}, 0.0, 0.0, 0.0, ''
    shift = raft_info(gcode)[0]
    for line in Path(gcode).read_text(errors='ignore').splitlines():
        if line.startswith(';Z:') or line.startswith('; Z_HEIGHT:'):
            z = float(line.split(':')[1])
        if line.startswith(';TYPE:'):
            kind = line[6:].strip()
        if not line.startswith(('G1', 'G0')):
            continue
        vals = dict((t[0], float(t[1:])) for t in line.split(';')[0].split()[1:] if t[0] in 'XYZE' and len(t) > 1)
        nx, ny = vals.get('X', x), vals.get('Y', y)
        if 'Z' in vals:
            z = vals['Z']
        if vals.get('E', 0) > 0 and line.startswith('G1') and kind not in ('Custom', '', 'Skirt', 'Brim') and (z - shift > 1e-6 or not shift):
            layers.setdefault(round(z - shift, 2), []).append((kind, ((x, y), (nx, ny))))
        x, y = nx, ny
    return layers


def bridges(report):
    """SPEC2 check 9: no bridge in the gate's slot. The extruded length of Orca's bridge lines over air (';TYPE:'
    'Bridge') inside the slot's region (the -X wall from the case side to the sliver's inner face, y -4.9..-0.1, from
    the rim to the floor's deepest point), for the tub and the gate's coupon. 'Internal Bridge' lines are solid infill
    laid over sparse infill inside the part, with plastic under them: reported, not counted. (2026-10-13: the left
    corner block, a screw's boss, joins the wall beside the slot, so the solid wall face-ward of the slot's floor is
    wide enough for sparse infill, and Orca lays one layer of internal bridge in it, at Z 2.77: 19 mm in the box.)"""
    import numpy as np, params as P
    out = {}
    for part in ('tub', 'coupon-gate'):
        info = report.get(part)
        if not info or not info.get('gcode'):
            continue
        M, shift, off, _, _ = _to_print(part, info)
        bx = (P.X0 - 0.1, P.WALL_X0 + 0.05, -4.9, -0.1, P.SEAM, P.GATE_SLOT['floor_z'] + P.ROD_STOP_X0 - P.X0 + 0.1)
        corners = np.array([[x, y, z, 1.0] for x in bx[:2] for y in bx[2:4] for z in bx[4:]]).T
        pc = (M @ corners)[:3].T + shift
        lo, hi = pc.min(axis=0), pc.max(axis=0)
        pb = (lo[0] + off[0], hi[0] + off[0], lo[1] + off[1], hi[1] + off[1])
        tl = typed_extrusions(hw.ROOT / info['gcode'])
        zs = [z for z in tl if lo[2] - 0.01 <= z <= hi[2] + 0.21]
        mm = sum(length_in([sg for k, sg in tl[z] if 'Bridge' in k and k != 'Internal Bridge'], pb) for z in zs)
        mi = sum(length_in([sg for k, sg in tl[z] if k == 'Internal Bridge'], pb) for z in zs)
        out[part] = {'bridge_mm': round(mm, 2), 'internal_bridge_mm': round(mi, 2), 'ok': mm <= 0.5}
    return out


def gate_checks(report, line_w=0.42):
    """SPEC2 check 9 on the gate: its first layer is the flange's face (its extent inside the flange's 3.40 x 4.45: the
    web's outer face would be 6.2 long); the steepest down-facing surface off the bed (the oriented mesh: the bevel at 45); the
    pull hole read back from the G-code (each layer through it: twice the least distance from its axis to an extrusion
    line's centre, less a line) >= 1.15; the thinnest wall, from the model (the hole's walls in Y and above it, the
    flange) >= 0.45. None if the gate was not sliced."""
    import numpy as np, trimesh, plates, params as P
    info = report.get('gate')
    if not info or not info.get('gcode'):
        return None
    M, shift, off, layers, first_ext = _to_print('gate', info)
    G = P.GATE
    top, yc = P.SEAM + G['top_clr'], sum(G['web_y']) / 2
    fl = (G['flange_y'][1] - G['flange_y'][0], P.GATE_SLOT['floor_z'] - top)         # the flange's face: 3.40 x 4.45
    ext = sorted(first_ext)
    is_flange = ext[1] <= max(fl) + 0.1 and ext[0] <= min(fl) + 0.1 and ext[0] >= 1.5   # the web's face: 6.2 long
    m = plates.oriented('gate')
    nz = m.face_normals[:, 2]
    off_bed = m.triangles_center[:, 2] > 0.05
    down = (nz < -1e-6) & off_bed
    steep = float(np.degrees(np.arcsin(np.clip(-nz[down], 0, 1))).max()) if down.any() else 0.0
    q = lambda x, y, z: (M @ np.array([x, y, z, 1.0]))[:3] + shift + np.array([off[0], off[1], 0.0])
    c0, c1 = q(P.X0 + 0.05, yc, G['pull_z']), q(P.X0 + G['pull_depth'] - 0.05, yc, G['pull_z'])
    zlo, zhi = sorted((c0[2], c1[2]))
    free = []
    for z, segs in layers.items():
        if not (zlo + 0.1 < z - 0.1 < zhi - 0.1):
            continue
        dmin = 9.0
        for (ax, ay), (bx, by) in segs:
            vx, vy = bx - ax, by - ay
            L2 = vx * vx + vy * vy
            t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((c0[0] - ax) * vx + (c0[1] - ay) * vy) / L2))
            dmin = min(dmin, math.hypot(ax + t * vx - c0[0], ay + t * vy - c0[1]))
        free.append((round(2 * dmin - line_w, 3), z))
    hole = min(free) if free else (None, None)
    walls = {'pull hole to the web side (Y)': round((G['web_y'][1] - G['web_y'][0] - G['pull_d']) / 2, 3),
             'pull hole to the top (at the chamfer)': round(G['pull_z'] - G['pull_d'] / 2 - top - G['top_chamfer'], 3),
             'flange': G['flange']}
    thin = min(walls.values())
    return {'first_layer': list(first_ext), 'first_layer_is_flange': bool(is_flange), 'steepest_overhang_deg': round(steep, 2),
            'pull_hole_free_d': hole[0], 'pull_hole_layers': len(free), 'pull_hole_at_z': hole[1], 'walls_mm': walls,
            'thinnest_wall_mm': thin,
            'ok': bool(is_flange and steep <= 45.05 and hole[0] is not None and hole[0] >= 1.15 and thin >= 0.45)}


# ---- the key's fit, read back (2026-09-29) -------------------------------------------------------------------------
def wide_extrusions(gcode):
    """{z: [((x0, y0), (x1, y1), width), ...]}: extrusions() with each line's width (Orca writes ';WIDTH:' before each
    feature). A part on a raft: as extrusions()."""
    layers, z, x, y, kind, w = {}, 0.0, 0.0, 0.0, '', 0.42
    shift = raft_info(gcode)[0]
    for line in Path(gcode).read_text(errors='ignore').splitlines():
        if line.startswith(';Z:') or line.startswith('; Z_HEIGHT:'):
            z = float(line.split(':')[1])
        elif line.startswith(';TYPE:'):
            kind = line[6:].strip()
        elif line.startswith(';WIDTH:'):
            w = float(line.split(':')[1])
        if not line.startswith(('G1', 'G0')):
            continue
        vals = dict((t[0], float(t[1:])) for t in line.split(';')[0].split()[1:] if t[0] in 'XYZE' and len(t) > 1)
        nx, ny = vals.get('X', x), vals.get('Y', y)
        if 'Z' in vals:
            z = vals['Z']
        if vals.get('E', 0) > 0 and line.startswith('G1') and kind not in ('Custom', '', 'Skirt', 'Brim') and (z - shift > 1e-6 or not shift):
            layers.setdefault(round(z - shift, 2), []).append(((x, y), (nx, ny), w))
        x, y = nx, ny
    return layers


def device_layers(part, info, xy=None, ends='flat'):
    """A sliced part back in the CAD frame: [(c, polygon)], one per layer, c its mid-plane in the part's own axis that
    the print's Z runs along (Z for the case parts, X for the key on its -X end, Y for the cranks on their pad end); the
    polygon, in the other two axes in order ((x, y), (y, z) or (x, z)), is every extruding line buffered by half its
    width, merged. Only lines that reach into xy (a0, a1, b0, b1 in those two axes). ends 'flat' stops each line at its
    end point (the widths across walls and holes); 'round' carries it half a width past, as deposited, for a part's
    outer extent at a corner (with flat ends a convex corner reads the end of the line along the edge, the other wall's
    half width short)."""
    import numpy as np
    from shapely.geometry import LineString
    from shapely.ops import unary_union
    M, shift, off, _, _ = _to_print(part, info)
    R = M[:3, :3]
    ax = int(np.argmax(np.abs(R[2, :])))
    assert abs(abs(R[2, ax]) - 1) < 1e-9, part          # the print's Z is one of the part's own axes
    keep = [i for i in range(3) if i != ax]
    t = np.array([shift[0] + off[0], shift[1] + off[1], shift[2]])
    out = []
    for z, segs in sorted(wide_extrusions(hw.ROOT / info['gcode']).items()):
        zc = float(R[2, ax] * (z - 0.1 - t[2]))
        a = ((np.array([[s[0][0], s[0][1], z] for s in segs]) - t) @ R)[:, keep]
        b = ((np.array([[s[1][0], s[1][1], z] for s in segs]) - t) @ R)[:, keep]
        gs = []
        for i, sg in enumerate(segs):
            if xy and (max(a[i, 0], b[i, 0]) < xy[0] or min(a[i, 0], b[i, 0]) > xy[1] or
                       max(a[i, 1], b[i, 1]) < xy[2] or min(a[i, 1], b[i, 1]) > xy[3]):
                continue
            if abs(a[i, 0] - b[i, 0]) + abs(a[i, 1] - b[i, 1]) > 1e-6:
                gs.append(LineString([a[i], b[i]]).buffer(sg[2] / 2, cap_style=1 if ends == 'round' else 2,
                                                          join_style=1 if ends == 'round' else 2))
        if gs:
            out.append((round(zc, 3), unary_union(gs)))
    return out


def _section(m, axis, c):
    """The model's (a trimesh mesh in the CAD frame) section at axis = c, as a shapely polygon in the other two axes
    (even-odd over its loops)."""
    from shapely.geometry import Polygon
    n = [0, 0, 0]
    n[axis] = 1
    o = [0, 0, 0]
    o[axis] = c
    keep = [i for i in range(3) if i != axis]
    sec = m.section(plane_origin=o, plane_normal=n)
    g = Polygon()
    for loop in (sec.discrete if sec is not None else []):
        if len(loop) >= 3:
            g = g.symmetric_difference(Polygon(loop[:, keep]).buffer(0))
    return g


def runs(g, p0, p1):
    """Material along the line p0 -> p1 (along X or along Y): merged (start, end) runs in the coordinate that varies."""
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


def free(rs, t):
    """The free interval (lo, hi) round t between material runs; None if t is in material or open on a side."""
    lo = [b for a, b in rs if b <= t]
    hi = [a for a, b in rs if a >= t]
    if not lo or not hi or any(a < t < b for a, b in rs):
        return None
    return max(lo), min(hi)


def _mean(v):
    return round(sum(v) / len(v), 3) if v else None


def tub_fit(part, info, xcs):
    """The opening, webs and chin wall round each key centre in xcs, from the sliced tub (or the coupon's strip), CAD
    frame. Skin layers (LIP + 0.05 .. Z_FRONT - KEY_EDGE_CHAMFER - 0.05): the free X across the opening at its mid-y and
    the free Y (chin edge to +Y edge) at dx 0 / +-3. Pocket layers (WEB z0 + 0.1 .. LIP - 0.1): the free X between the
    webs at y -6.1 and the free Y (chin wall to rail face) at dx 0 / +-3. The hook slots (test 2), in their layers
    (above the seam chamfer, under the roof): each slot's back at dx +-4.45, and across the key at the slots' mid-y the
    two slots' outer sides apart. Widths only: the part's placement cancels. Min, mean over the layers."""
    import params as P
    O, Sl = P.KEY_OPENING, P.KEY_SLOT
    ym = sum(O['y']) / 2
    skin = (P.LIP + 0.05, P.Z_FRONT - P.KEY_EDGE_CHAMFER - 0.05)
    pocket = (P.WEB['z0'] + 0.1, P.LIP - 0.1)
    sz = (P.SEAM + P.SEAM_CHAMFER + 0.1, P.KEY_SLOT_ROOF - 0.1)
    hx = sum(P.KEY_HOOK['dx']) / 2
    ys = (Sl['back'] + P.BOT_IN) / 2
    out = {}
    layers = [(z, g) for z, g in device_layers(part, info, (min(xcs) - 7.5, max(xcs) + 7.5, P.Y0 - 0.5, P.RAIL_Y[0] + 1.5))
              if min(pocket[0], sz[0]) <= z <= skin[1]]
    for xc in xcs:
        r = {k: [] for k in ('skin_x', 'skin_y', 'chin_edge', 'web_x', 'pocket_y', 'chin_wall', 'rail', 'slot_back', 'slots_out')}
        for z, g in layers:
            if skin[0] <= z <= skin[1]:
                f = free(runs(g, (xc - 8, ym), (xc + 8, ym)), xc)
                if f:
                    r['skin_x'].append(f[1] - f[0])
                for dx in (0.0, -3.0, 3.0):
                    f = free(runs(g, (xc + dx, P.BOT_IN - 1.5), (xc + dx, P.RAIL_Y[0] + 1.5)), ym)
                    if f:
                        r['skin_y'].append(f[1] - f[0])
                        r['chin_edge'].append(f[0])
            if pocket[0] <= z <= pocket[1]:
                f = free(runs(g, (xc - 8, -6.1), (xc + 8, -6.1)), xc)
                if f:
                    r['web_x'].append(f[1] - f[0])
                for dx in (0.0, -3.0, 3.0):
                    f = free(runs(g, (xc + dx, P.BOT_IN - 1.5), (xc + dx, P.RAIL_Y[0] + 1.5)), -6.1)
                    if f:
                        r['pocket_y'].append(f[1] - f[0])
                        r['chin_wall'].append(f[0])
                        if dx == 0.0:
                            r['rail'].append(f[1])
            if sz[0] <= z <= sz[1]:               # the slots' backs (the cheek's slot opens the rail at +-4.45)
                for sd in (-1, 1):
                    lo = [b for a, b in runs(g, (xc + sd * hx, P.Y0 - 0.5), (xc + sd * hx, P.RAIL_Y[0] + 1.5)) if b <= P.BOT_IN - 0.1]
                    if lo:
                        r['slot_back'].append(max(lo))
                fl, fr = free(runs(g, (xc - 8, ys), (xc + 8, ys)), xc - hx), free(runs(g, (xc - 8, ys), (xc + 8, ys)), xc + hx)
                if fl and fr:
                    r['slots_out'].append(fr[1] - fl[0])
        ok = all(r[k] for k in r)
        out[round(xc, 3)] = {
            'skin_free_x': [round(min(r['skin_x']), 3), _mean(r['skin_x'])] if ok else None,
            'skin_free_y': [round(min(r['skin_y']), 3), _mean(r['skin_y'])] if ok else None,
            'webs_free_x': [round(min(r['web_x']), 3), _mean(r['web_x'])] if ok else None,
            'pocket_free_y': [round(min(r['pocket_y']), 3), _mean(r['pocket_y'])] if ok else None,
            'pocket_free_y_at_hooks': round(_mean(r['rail']) - _mean(r['slot_back']), 3) if ok else None,
            'slots_outer_sides_apart': [round(min(r['slots_out']), 3), _mean(r['slots_out'])] if ok else None,
            'ledge': round(min(r['chin_edge']) - max(r['chin_wall']), 3) if ok else None,
            'layers': {k: len(v) for k, v in r.items()}}
    return out


INSET = 0.25                             # key_dims: its levels off each band's ends (a line's half width and more)
RES = 0.001                              # the G-code's resolution (3 decimals): an as-sliced reading is good to it


def key_dims(part, info):
    """The key's own widths and depths from its G-code (its frame: dx from its centre). It prints on its -X end (test 1),
    so each layer is a YZ section at its mid-plane dx: the key's X is its layers' span (a whole number of layers). In the
    body's layers (|dx| <= 3.2): the cap's depth along y at its closed levels (over the slit's roof, under the top
    chamfer), its chin face and +Y face; the pusher's chin end at the stop levels; in the hooks' layers (dx 4.05 .. 4.80
    and -4.50 .. -4.05): their tips at the hooks' levels. Each band's levels keep INSET off its ends: a wall line runs along z here, and
    with flat ends it stops half a line short of a corner (the next wall's half width), which would read the face short
    there. Max, mean over the layers and levels (for the chin-side stop and the tip: the least y, mean)."""
    import params as P, keys
    Pu, (hx0, hx1) = P.KEY_PUSHER, P.KEY_HOOK['dx']
    top = keys.top()
    cap = (P.Z_FRONT - 0.5 + INSET, top - P.KEY_CAP_CHAMFER - INSET)
    stop = (Pu['z0'] + INSET, Pu['stop_z1'] - INSET)
    bz = (P.KEY_HOOK_Z[0] + INSET, P.KEY_HOOK_Z[1] - INSET)
    levels = lambda lo, hi: [lo + (hi - lo) * i / 6 for i in range(7)]
    r = {k: [] for k in ('depth', 'plus_y', 'chin', 'pusher', 'tip')}
    layers = device_layers(part, info)
    for c, g in layers:
        if abs(c) <= 3.2:
            for z in levels(*cap):
                rs = runs(g, (-9.5, z), (-3.0, z))
                if rs:
                    r['depth'].append(rs[-1][1] - rs[0][0])
                    r['plus_y'].append(rs[-1][1])
                    r['chin'].append(rs[0][0])
            for z in levels(*stop):
                rs = runs(g, (-9.5, z), (-3.0, z))
                if rs:
                    r['pusher'].append(rs[0][0])
        if hx0 + 0.1 <= abs(c) <= hx1 - 0.2 and c > -hx1 + 0.5:
            for z in levels(*bz):
                rs = runs(g, (-9.5, z), (-3.0, z))
                if rs:
                    r['tip'].append(rs[0][0])
    cs = [c for c, _ in layers]
    x = round(max(cs) - min(cs) + P.LAYER, 3)
    return {'cap_x': [x, x], 'layers_x': [round(min(cs) - P.LAYER / 2, 3), round(max(cs) + P.LAYER / 2, 3)],
            'depth': [round(max(r['depth']), 3), _mean(r['depth'])],
            'plus_y': _mean(r['plus_y']), 'chin_face': _mean(r['chin']),
            'stop_depth': [round(max(r['plus_y']) - min(r['pusher']), 3), round(_mean(r['plus_y']) - _mean(r['pusher']), 3)],
            'pusher_chin_end': [round(min(r['pusher']), 3), _mean(r['pusher'])],
            'hook_tip': [round(min(r['tip']), 3), _mean(r['tip'])],
            'samples': {k: len(v) for k, v in r.items()}}


def key_fit(report):
    """The key's clearances as sliced, and as printed at worst (2026-09-29). Pairs: the tub and this build's key at each
    of the four openings; the coupon's strip and each of its keys at its opening. Each clearance is a difference within
    one part's G-code (the tub's free widths, the key's widths and depths), so where the slicer put a part cancels:
      X skin per side    (free X skin - cap X) / 2                   0.30, +-0.03
      X webs per side    (free X webs - cap X) / 2                   0.40, +-0.03
      Y skin, chin side  free Y skin - (cap +Y face - chin face)     0.40, +-0.03
      Y pocket, chin     free Y pocket - (+Y face - pusher chin end) 0.40, +-0.03
      Y hooks            free Y at the hooks (rail - slot back) - (+Y face - hook tip)   0.40, +-0.03
      X slots per side   (the slots' outer sides apart - cap X) / 2  0.40, +-0.03
      ledge              skin's chin edge - the chin wall's face     >= 0.23
    The key prints on its -X end (test 1): its X is its layers' span (50 layers, 10.00 since 2026-10-03: X per side
    0.30 skin, 0.40 webs and slots expected; the 9.90 key printed 49 layers, 9.80) and does not grow, so as printed
    at worst (params KEY_FDM): X - hole / 2 >= 0.15; Y - (hole + part) >= 0.05 (both to the G-code's RES). Worst
    reading of each (the least free width, the largest key). The coupon's strip (the hook keys' fit check, test 2)
    must read as the tub's opening (+-0.03). Its bed end: first_layers."""
    import params as P, tub, keys, mechanics
    Fd = P.KEY_FDM
    xw = Fd['hole'][2] / 2
    yw = Fd['hole'][2] + Fd['part'][2]
    lay = mechanics.printed_layers(0.0, 2 * P.KEY_HALF)
    xq = (lay[1] - lay[0]) / 2
    exp = {'x_skin': P.KEY_OPENING['half'] - xq, 'x_webs': P.SLOT[1] - xq,
           'y_skin': P.KEY_Y[0] - P.KEY_OPENING['y'][0], 'y_pocket': P.KEY_PUSHER['y'][0] - P.BOT_IN,
           'y_hooks': P.KEY_HOOK['tip'] - P.KEY_SLOT['back'], 'x_slots': P.KEY_SLOT['dx'][1] - xq}
    xs = tub.key_x()
    holes = {}
    if report.get('tub', {}).get('gcode'):
        holes['tub'] = tub_fit('tub', report['tub'], xs)
    if report.get('coupon-strip', {}).get('gcode'):
        holes['coupon-strip'] = tub_fit('coupon-strip', report['coupon-strip'], xs[:1])
    pairs = [('tub', x, keys.NAME) for x in xs] + [('coupon-strip', xs[0], keys.NAME)]
    kd, rows = {}, []
    for hp, xc, kp in pairs:
        if hp not in holes or not report.get(kp, {}).get('gcode'):
            continue
        if kp not in kd:
            kd[kp] = key_dims(kp, report[kp])
        h, k = holes[hp][round(xc, 3)], kd[kp]
        if h['skin_free_x'] is None:
            rows.append({'hole': hp, 'xc': round(xc, 3), 'key': kp, 'ok': False, 'note': f"no read-back: {h['layers']}"})
            continue
        v = {'x_skin': (h['skin_free_x'][0] - k['cap_x'][0]) / 2, 'x_webs': (h['webs_free_x'][0] - k['cap_x'][0]) / 2,
             'y_skin': h['skin_free_y'][0] - k['depth'][0], 'y_pocket': h['pocket_free_y'][0] - k['stop_depth'][0],
             'y_hooks': h['pocket_free_y_at_hooks'] - (k['plus_y'] - k['hook_tip'][0]),
             'x_slots': (h['slots_outer_sides_apart'][0] - k['cap_x'][0]) / 2, 'ledge': h['ledge']}
        v = {n: round(x, 3) for n, x in v.items()}
        printed = {n: round(v[n] - (xw if n.startswith('x') else yw), 3) for n in exp}
        fails = [n for n in exp if abs(v[n] - exp[n]) > 0.03 + 1e-9]
        if v['ledge'] < 0.23 - 1e-9:
            fails.append('ledge')
        # (to RES: the chin side is 0.05 at worst in CAD, and the sliced tub's skin opening reads 0.001 under its 3.725)
        fails += [f'{n} as printed' for n in ('x_skin', 'x_webs', 'x_slots') if printed[n] < 0.15 - RES - 1e-9]
        fails += [f'{n} as printed' for n in ('y_skin', 'y_pocket', 'y_hooks') if printed[n] < 0.05 - RES - 1e-9]
        rows.append({'hole': hp, 'xc': round(xc, 3), 'key': kp, 'as_sliced': v,
                     'as_printed_worst': printed, 'fails': fails, 'ok': not fails})
    same = None
    if 'tub' in holes and 'coupon-strip' in holes:
        a, b = holes['tub'][round(xs[0], 3)], holes['coupon-strip'][round(xs[0], 3)]
        d = {n: round(b[n][0] - a[n][0], 3) for n in ('skin_free_x', 'skin_free_y', 'webs_free_x', 'pocket_free_y',
                                                    'slots_outer_sides_apart') if a[n] and b[n]}
        for n in ('ledge', 'pocket_free_y_at_hooks'):
            if a[n] is not None and b[n] is not None:
                d[n] = round(b[n] - a[n], 3)
        same = {'coupon_strip_minus_tub': d, 'ok': len(d) == 7 and all(abs(x) <= 0.03 + 1e-9 for x in d.values())}
    return {'expected': {n: round(x, 3) for n, x in exp.items()}, 'fdm_worst': {'x': round(xw, 3), 'y': round(yw, 3)},
            'holes': holes, 'keys': kd, 'pairs': rows, 'coupon_reproduces_the_opening': same,
            'ok': bool(rows) and all(r['ok'] for r in rows) and (same is None or same['ok'])}


# ---- test 1 (2026-09-29): the cranks' cheeks and the key on its end, read back -------------------------------------
CHEEK_SLICED_MIN = 0.90                  # the sliced cheek over its designed section, every layer through the bore
CHEEK_LAYERS_Y = (-3.0, -1.4)            # device y of those layers' mid-planes (the crank prints +Y up)


def crank_sections(report):
    """Each crank's cheeks as sliced against their designed section, every layer whose mid-plane is in CHEEK_LAYERS_Y
    (the bore's layers): in the cheek's band (|dx| 3.55..5.45) the area of the layer's lines (at their widths, round
    ends) inside the model's section there, over the section's area. >= CHEEK_SLICED_MIN in every layer and both
    cheeks. It also shows the per-object Arachne walls are in: classic walls drop the inner loop in the 1.5 cheek (the
    crank study: 83 % stock, 91.6 % Arachne)."""
    import trimesh
    from shapely.geometry import box as sbox
    out = {}
    for p in ('crank-M', 'crank-T'):
        info = report.get(p)
        if not info or not info.get('gcode'):
            continue
        m = trimesh.load(hw.OUT / f'{p}.stl')
        rows = []
        for c, g in device_layers(p, info, ends='round'):
            if not CHEEK_LAYERS_Y[0] - 1e-6 <= c <= CHEEK_LAYERS_Y[1] + 1e-6:
                continue
            sec = _section(m, 1, c)
            for sd in (1, -1):
                band = sbox(min(sd * 3.55, sd * 5.45), -9, max(sd * 3.55, sd * 5.45), 9)
                des = sec.intersection(band)
                if des.area > 0:
                    rows.append({'y': c, 'cheek': f'{sd:+d}', 'designed_mm2': round(des.area, 3),
                                 'fraction': round(des.intersection(g).area / des.area, 3)})
        w = min(rows, key=lambda r: r['fraction']) if rows else None
        out[p] = {'wall_generator': info.get('wall_generator'), 'layers': len(rows), 'worst': w,
                  'ok': bool(rows) and w['fraction'] >= CHEEK_SLICED_MIN}
    return out


HOOK_COVER_MIN = 0.75                    # each hook's section covered by lines, every layer through it


def _seams(part, info):
    """Where each outer-wall loop starts (Orca's seam), CAD frame (the two axes device_layers keeps, and the layer's
    mid-plane)."""
    import numpy as np
    M, shift, off, _, _ = _to_print(part, info)
    R = M[:3, :3]
    ax = int(np.argmax(np.abs(R[2, :])))
    keep = [i for i in range(3) if i != ax]
    t = np.array([shift[0] + off[0], shift[1] + off[1], shift[2]])
    out, prev = [], None
    for z, segs in sorted(typed_extrusions(hw.ROOT / info['gcode']).items()):
        prev = None
        for kind, (a, b) in segs:
            if kind == 'Outer wall' and prev != 'Outer wall':
                q = (np.array([a[0], a[1], z - 0.1]) - t) @ R
                out.append((round(float(q[ax]), 2), round(float(q[keep[0]]), 3), round(float(q[keep[1]]), 3)))
            prev = kind
    return out


def gap_at(rs, t, open_=9.0):
    """The free width round t between material runs: 0 if t is in material, open_ if nothing bounds it on a side (in a
    few layers over the cheek zones Orca leaves out the key's 0.28 strip beside the slit, so the slit opens there)."""
    if any(a <= t <= b for a, b in rs):
        return 0.0
    lo = [b for a, b in rs if b <= t]
    hi = [a for a, b in rs if a >= t]
    return (min(hi) - max(lo)) if lo and hi else open_


def key_on_end(report):
    """The key printed on its -X end (test 1), per key: in every layer through a hook (the -X hook from past the bed
    end's 0.4, the +X hook to its last whole layer), the hook's section (y tip..the cap's chin face, z its height at
    rest) covered by lines >= HOOK_COVER_MIN; the seams (outer-wall starts) off the button face (the cap's top and its
    chamfers) and off the chin face where it shows (over the build's face)."""
    import params as P, keys
    from shapely.geometry import box as sbox
    Hk, (hz0, hz1), y0 = P.KEY_HOOK, P.KEY_HOOK_Z, P.KEY_Y[0]
    (hx0, hx1), tip = Hk['dx'], Hk['tip']
    top, ch = keys.top(), P.KEY_CAP_CHAMFER
    hook = sbox(tip, hz0, y0, hz1)
    out = {}
    for p, info in report.items():
        if p.startswith('_') or not p.startswith('key-') or not info.get('gcode'):
            continue
        rows = []
        for c, g in device_layers(p, info):
            if not (-hx1 + 0.4 <= c <= -hx0 or hx0 <= c <= hx1 - 0.1):
                continue
            rows.append({'dx': c, 'hook_cover': round(hook.intersection(g).area / hook.area, 3)})
        seams = _seams(p, info)
        bad = [q for q in seams if q[2] > top - ch - 0.1 or (q[1] < y0 + 0.15 and q[2] > P.Z_FRONT)]
        worst = min(r['hook_cover'] for r in rows) if rows else 0.0
        out[p] = {'layers_in_the_hooks': len(rows), 'worst_hook_cover': worst,
                  'seams': sorted({(round(q[1], 1), round(q[2], 1)) for q in seams}), 'seams_on_show': bad[:6],
                  'ok': bool(rows) and worst >= HOOK_COVER_MIN and not bad}
    return out


SUPPORT_TYPES = ('Support', 'Bridge', 'Overhang')           # Orca's ';TYPE:' names (Support, Support interface,
                                                            # Bridge, Internal Bridge, Overhang wall)


def no_support(report):
    """The hook keys print with no supports (test 2, Ian: no support, no bridge, no overhang past 45 degrees): the
    G-code's support, bridge and overhang lines, by type, over the whole key (none) and in the tub (and the coupon's
    strip) round each hook slot (its box grown 0.3, from the rim to 0.5 over its roof: none). Orca prints a support
    only where the part asks for one, so none in the G-code is the slicer's own check that nothing starts in mid-air
    or overhangs past its limit there (islands() reads the keys layer by layer as well)."""
    import numpy as np, params as P, tub
    out = {}
    for p, info in report.items():
        if p.startswith('_') or not p.startswith('key-') or not info.get('gcode'):
            continue
        tl = typed_extrusions(hw.ROOT / info['gcode'])
        found = {}
        for z, segs in tl.items():
            for kind, (a, b) in segs:
                # a de-retract (E with no move) is no line: on a raft the key's first layer starts with one that still
                # carries the raft's last role (Support interface)
                if any(t in kind for t in SUPPORT_TYPES) and a != b:
                    found[kind] = round(found.get(kind, 0.0) + math.hypot(b[0] - a[0], b[1] - a[1]), 2)
        out[p] = {'lines_mm': found, 'support_material': bool(re.search(r'; enable_support = 1', Path(hw.ROOT / info['gcode']).read_text(errors='ignore'))),
                  'ok': not found}
    for part in ('tub', 'coupon-strip'):
        info = report.get(part)
        if not info or not info.get('gcode'):
            continue
        M, shift, off, _, _ = _to_print(part, info)
        tl = typed_extrusions(hw.ROOT / info['gcode'])
        found, n = {}, 0
        slots = tub.key_slots() if part == 'tub' else tub.key_slots()[:2]
        for sl in slots:
            bb = sl.val().BoundingBox()
            bx = (bb.xmin - 0.3, bb.xmax + 0.3, bb.ymin - 0.3, bb.ymax + 0.3, P.SEAM, P.KEY_SLOT_ROOF + 0.5)
            corners = np.array([[x, y, z, 1.0] for x in bx[:2] for y in bx[2:4] for z in bx[4:]]).T
            pc = (M @ corners)[:3].T + shift
            lo, hi = pc.min(axis=0), pc.max(axis=0)
            pb = (lo[0] + off[0], hi[0] + off[0], lo[1] + off[1], hi[1] + off[1])
            n += 1
            for z, segs in tl.items():
                if not (lo[2] - 0.01 <= z <= hi[2] + 0.21):
                    continue
                for kind in {k for k, _ in segs if any(t in k for t in SUPPORT_TYPES)}:
                    mm = length_in([sg for k, sg in segs if k == kind], pb)
                    if mm > 0.05:
                        found[kind] = round(found.get(kind, 0.0) + mm, 2)
        out[part] = {'slots': n, 'lines_mm_round_the_slots': found, 'ok': not found}
    return out


# ---- the screen window's bevel, as sliced (2026-10, the standard build: 35 degrees on the raised face) -------------
WINDOW_EDGE_TOL = 0.03                   # mm: a layer's window edge against the CAD's at the layer's mid-plane (as
                                         # sliced: the sides within 0.001, the corners 0.006-0.013 inside their arcs,
                                         # Orca's 0.012 resolution)
WINDOW_EFC_MAX = 0.15                    # mm: the face's layer may stand this much further out (the profile's
                                         # elephant-foot compensation, 0.1, pulls the first layer back)
WINDOW_BAND = (1.0, 10.0)                # mm: each band runs from 1.0 inside the window's edge to 1.0 past the bevel,
                                         # 10.0 either side of the edge's middle (corners: the quadrant past the arc's
                                         # centre, out to R + W + 1.0)


def window_bevel(report):
    """The standard tub's screen window (tub.window, params WINDOW_*: WINDOW_BEVEL_ANGLE from the face down
    WINDOW_CHAMFER, to the last skin layer's mid-plane; corners WINDOW_CORNER_R at the lip, R + W on the face) as it
    prints, face down, read back from the G-code through the skin, each layer from the face to the lip's, over a band
    across the middle of each edge and round each corner (WINDOW_BAND). Each layer's material (its lines at their
    widths, round ends, merged), taken back to the CAD frame:
      edge     where the material starts, from the window at the lip (the active area + WINDOW_MARGIN), outward
               positive: on an edge the least distance across it, at a corner the least distance from the arc's centre
               less WINDOW_CORNER_R. Each must be the CAD's at the layer's mid-plane within WINDOW_EDGE_TOL (the face's
               layer up to WINDOW_EFC_MAX further out), so the lip's layer prints on the lip line and the screen seen is
               the active area + 0.5, as x3's
      reach    how far the layer reaches past the one below (face down the bevel is an overhang: 0.2 / tan(angle) a
               layer, 0.29 at 35 degrees, 0.39 on the second with the face's elephant-foot pull-back): no piece may
               float, and none over OVERHANG_REACH_MAX (at 25 degrees Orca lays the step as an overhang wall, 0.52)
      roles    Orca's Overhang wall, Bridge and Support lines in the bands: none.
    The light-strip tub keeps x3's 45-degree window with sharp corners: not read (None)."""
    import numpy as np, params as P, shapely
    from shapely.geometry import LineString, Point, box as sbox
    from shapely.affinity import affine_transform
    from shapely.ops import unary_union
    info = report.get('tub')
    if P.LIGHT_STRIP or not info or not info.get('gcode'):
        return None
    M, shift, off, _, _ = _to_print('tub', info)
    if abs(M[:2, 2]).max() > 1e-9 or abs(M[2, :2]).max() > 1e-9:
        raise AssertionError('window_bevel: the tub no longer prints with its face flat on the bed')
    A = M[:2, :2]                        # print XY -> CAD XY: q = A^T (p - shift - off)
    t = -(A.T @ (shift[:2] + off))
    to_cad = [A[0, 0], A[1, 0], A[0, 1], A[1, 1], t[0], t[1]]
    x0 = hw.ACTIVE_CX - hw.ACTIVE_W / 2 - P.WINDOW_MARGIN
    x1 = hw.ACTIVE_CX + hw.ACTIVE_W / 2 + P.WINDOW_MARGIN
    y0 = hw.ACTIVE_CY - hw.ACTIVE_H / 2 - P.WINDOW_MARGIN
    y1 = hw.ACTIVE_CY + hw.ACTIVE_H / 2 + P.WINDOW_MARGIN
    W, R, (m, h) = P.WINDOW_BEVEL_W, P.WINDOW_CORNER_R, WINDOW_BAND
    xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
    zb, k = P.Z_FRONT - P.WINDOW_CHAMFER, 1 / math.tan(math.radians(P.WINDOW_BEVEL_ANGLE))
    bands = {'left': (sbox(x0 - W - m, ym - h, x0 + m, ym + h), lambda g: x0 - g.bounds[2]),
             'right': (sbox(x1 - m, ym - h, x1 + W + m, ym + h), lambda g: g.bounds[0] - x1),
             'bottom': (sbox(xm - h, y0 - W - m, xm + h, y0 + m), lambda g: y0 - g.bounds[3]),
             'top': (sbox(xm - h, y1 - m, xm + h, y1 + W + m), lambda g: g.bounds[1] - y1)}
    for name, sx, sy in (('bottom-left', -1, -1), ('bottom-right', 1, -1), ('top-left', -1, 1), ('top-right', 1, 1)):
        c = (x1 - R if sx > 0 else x0 + R, y0 + R if sy < 0 else y1 - R)
        e = R + W + m
        bands[name] = (sbox(min(c[0], c[0] + sx * e), min(c[1], c[1] + sy * e), max(c[0], c[0] + sx * e),
                            max(c[1], c[1] + sy * e)), lambda g, c=c: Point(c).distance(g) - R)
    wl = wide_extrusions(hw.ROOT / info['gcode'])
    tl = typed_extrusions(hw.ROOT / info['gcode'])
    z_cad = lambda zl: (zl - P.LAYER / 2 - shift[2]) / M[2, 2]          # a layer's mid-plane, CAD z
    zs = [z for z in sorted(wl) if P.LIP < z_cad(z) < P.Z_FRONT]
    near = unary_union([bx for bx, _ in bands.values()]).buffer(0.5)

    def material(z):                     # the layer's lines near the bands, at their widths, in the CAD frame
        segs = [(a, b, w) for a, b, w in wl[z] if a != b]
        ab = np.array([(*a, *b) for a, b, _ in segs]).reshape(-1, 4)
        ca = ab[:, :2] @ A + t           # q = A^T p + t, row-wise
        cb = ab[:, 2:] @ A + t
        lo, hi = np.minimum(ca, cb), np.maximum(ca, cb)
        nb = near.bounds
        keep = (hi[:, 0] >= nb[0]) & (lo[:, 0] <= nb[2]) & (hi[:, 1] >= nb[1]) & (lo[:, 1] <= nb[3])
        lines = [LineString([ca[j], cb[j]]) for j in np.flatnonzero(keep)]
        return unary_union([ln.buffer(segs[j][2] / 2, cap_style=1) for ln, j in zip(lines, np.flatnonzero(keep))
                            if ln.intersects(near)])

    rows, prev, reach, floating, roles, fails = [], {}, {}, [], {}, []
    for i, z in enumerate(zs):
        zc = z_cad(z)
        exp = max(0.0, zc - zb) * k
        mat = material(z)
        row = {'z': z, 'z_cad': round(zc, 3), 'expect_mm': round(exp, 3), 'edge_mm': {}, 'reach_mm': {}}
        for name, (bx, edge) in bands.items():
            g = mat.intersection(bx)
            if g.is_empty:
                fails.append(f'{name} z {z}: no material')
                continue
            e = edge(g)
            row['edge_mm'][name] = round(e, 3)
            lo, hi = exp - WINDOW_EDGE_TOL, exp + WINDOW_EDGE_TOL + (WINDOW_EFC_MAX if i == 0 else 0.0)
            if not lo <= e <= hi:
                fails.append(f'{name} z {z}: edge {e:.3f} (CAD {exp:.3f})')
            if name in prev:
                p = prev[name]
                for q in getattr(g, 'geoms', [g]):
                    if q.area > 0.005 and q.intersection(p).area < 0.2 * q.area:
                        floating.append({'band': name, 'z': z, 'mm2': round(q.area, 3)})
                un = g.difference(p)
                pts = [pt for q in getattr(un, 'geoms', [un]) if q.geom_type == 'Polygon' and q.area > 1e-4
                       for pt in q.exterior.coords]
                far = float(shapely.distance(shapely.points(np.array(pts)), p).max()) if pts else 0.0
                row['reach_mm'][name] = round(far, 3)
                reach[name] = max(reach.get(name, 0.0), far)
            prev[name] = g
        for kind, (a, b) in tl.get(z, []):
            if a != b and any(s in kind for s in ('Overhang', 'Bridge', 'Support')):
                ln = affine_transform(LineString([a, b]), to_cad)
                for name, (bx, _) in bands.items():
                    L = ln.intersection(bx).length
                    if L > 0.01:
                        roles[kind] = round(roles.get(kind, 0.0) + L, 2)
        rows.append(row)
    rmax = max(reach.values()) if reach else 0.0
    if len(zs) != round((P.Z_FRONT - P.LIP) / P.LAYER):
        fails.append(f'{len(zs)} skin layers (CAD {(P.Z_FRONT - P.LIP) / P.LAYER:.0f})')
    if rmax > OVERHANG_REACH_MAX:
        fails.append(f'reach {rmax:.3f} > {OVERHANG_REACH_MAX}')
    if floating:
        fails.append(f'{len(floating)} floating pieces')
    if roles:
        fails.append(f'support / bridge / overhang lines {roles}')
    return {'what': 'screen window bevel as sliced: every layer on the CAD, nothing floating, reach <= '
                    f'{OVERHANG_REACH_MAX}, no support / bridge / overhang line (4 edges, 4 corners)',
            'window_at_lip': [round(v, 4) for v in (x0, x1, y0, y1)],
            'bevel': {'angle_deg': P.WINDOW_BEVEL_ANGLE, 'depth_mm': P.WINDOW_CHAMFER, 'face_mm': W,
                      'corner_r_mm': [R, round(R + W, 3)]},
            'layers': rows, 'reach_max_mm': {n: round(v, 3) for n, v in reach.items()}, 'floating': floating,
            'roles_mm': roles, 'fails': fails, 'ok': not fails}


def show_window_bevel(wb):
    print(f"  tub screen window ({wb['bevel']['angle_deg']:.0f} deg, {wb['bevel']['depth_mm']} deep, "
          f"{wb['bevel']['face_mm']} on the face, corners R{wb['bevel']['corner_r_mm'][0]} / R{wb['bevel']['corner_r_mm'][1]}),"
          " each layer's edge from the lip line (CAD at its mid-plane), face first:")
    for r in wb['layers']:
        e = r['edge_mm']
        sides = ' / '.join(f"{e[n]:.3f}" for n in ('left', 'right', 'bottom', 'top') if n in e)
        corners = [e[n] for n in e if '-' in n]
        print(f"    z {r['z']:.1f}: CAD {r['expect_mm']:.3f}; sides {sides}; corners {min(corners):.3f}..{max(corners):.3f}"
              + (f"; reach {max(r['reach_mm'].values()):.3f}" if r['reach_mm'] else ''))
    print(f"  window bevel: reach max {max(wb['reach_max_mm'].values()) if wb['reach_max_mm'] else 0} (<= {OVERHANG_REACH_MAX}), "
          f"floating {len(wb['floating'])}, support / bridge / overhang lines {wb['roles_mm'] or 'none'}: "
          f"{'PASS' if wb['ok'] else 'FAIL   <-- CHECK ' + '; '.join(wb['fails'][:6])}")


# ---- the key pushed sideways along its travel, as sliced (2026-10-03, the 50-layer key) ----------------------------
SIDE_SWEEP_GRID = (0.01, 0.02, 0.01)     # raster x (tub), y (both), z (the key's sections): mm
SIDE_SWEEP_STEP = 0.05                   # lift step from the stop (KEY_W_OUT) down to the lowest mechanics.KEY_SINK


def key_side_sweep(report):
    """The key pushed sideways all along its travel, both parts as sliced (mechanics.key_sweep is CAD at the key's
    centred X; mechanics.key_hooks pushes it in CAD at six lifts). The key's layers (its YZ sections, lines carried half
    a width past their ends: as deposited) and the tub's (XY, the same) are rasterised (SIDE_SWEEP_GRID). At every lift
    from its stop (KEY_W_OUT) to -3.4 (SIDE_SWEEP_STEP) and in every tub layer it spans, the key centred on its opening
    must not overlap the tub, and its free X travel each way, to the first tub line in its rows, is its side play
    there (the skin while the cap is in it; the webs, slots and chin wall deeper). Nothing centres the key in X, so,
    as key_fit's X pairs (two-sided, the key centred), its play per side at each lift is half the two ways' sum; the
    least over every lift and opening, less KEY_FDM's worst hole / 2 (the key's X is its layers and does not grow),
    must keep 0.15. The cap's +Y corners are judged on their own, each side (the rows of the opening's R0.5 arcs, y >=
    KEY_OPENING y1 - r): >= 0.15 as well, less the same. There the key's last layer at each end (its section at the
    layer's mid-plane, carried 0.10 past it) comes nearer the opening's arc than the CAD corner does: with the cap's
    R0.5 corners 0.20 as sliced (2026-10-03, the tub registered right), with R1.0 (KEY_CORNER_R) 0.46. Each side's own
    least anywhere is reported. Read to the raster's 0.01."""
    import numpy as np, params as P, keys, tub, mechanics
    from shapely import contains_xy
    from shapely.geometry import box as sbox
    kp = keys.NAME
    if not (report.get('tub', {}).get('gcode') and report.get(kp, {}).get('gcode')):
        return {'ok': None, 'note': 'needs the tub and the key sliced'}
    GX, GY, GZ = SIDE_SWEEP_GRID
    W, low = P.KEY_W_OUT, min(mechanics.KEY_SINK)
    dl = device_layers(kp, report[kp], ends='round')
    cs = np.array([c for c, _ in dl])
    yb = (min(g.bounds[0] for _, g in dl) - 0.1, max(g.bounds[2] for _, g in dl) + 0.1)
    zb = (min(g.bounds[1] for _, g in dl) - 0.1, max(g.bounds[3] for _, g in dl) + 0.1)
    YS = np.round(np.arange(yb[0], yb[1], GY), 3)
    ZK = np.round(np.arange(zb[0], zb[1], GZ), 3)
    YY, ZZ = np.meshgrid(YS, ZK, indexing='ij')
    KR = np.stack([contains_xy(g, YY, ZZ) for _, g in dl])                 # [key layer, y, z]
    xs = tub.key_x()
    half = (cs.max() - cs.min()) / 2 + P.LAYER / 2 + 1.5                    # the key's half length and 1.5 round it
    yc = P.KEY_OPENING['y'][1] - P.KEY_OPENING['r']                        # the +Y corners' rows: the opening's R0.5 arcs
    tl = [(z, g) for z, g in device_layers('tub', report['tub'], (min(xs) - half, max(xs) + half, yb[0], yb[1]),
                                           ends='round') if zb[0] + low - 0.2 <= z <= zb[1] + W + 0.2]
    lifts = [round(W - SIDE_SWEEP_STEP * i, 3) for i in range(int(round((W - low) / SIDE_SWEEP_STEP)) + 1)]
    out = {'key': kp, 'key_layers': len(dl), 'key_x': [round(float(cs.min() - P.LAYER / 2), 3),
                                                        round(float(cs.max() + P.LAYER / 2), 3)],
           'lifts': [lifts[0], lifts[-1], SIDE_SWEEP_STEP], 'openings': {}}
    for xc in xs:
        XS = np.round(np.arange(xc - half, xc + half, GX), 3)
        XX, YT = np.meshgrid(XS, YS)
        win = sbox(XS[0] - 0.5, yb[0], XS[-1] + 0.5, yb[1])
        n = len(XS)
        idx = np.arange(n)
        T = []
        for z, g in tl:
            occ = contains_xy(g.intersection(win), XX, YT)                     # [y, x]
            if not occ.any():
                continue
            nxt = np.minimum.accumulate(np.where(occ, idx, n + 10000)[:, ::-1], axis=1)[:, ::-1]
            prv = np.maximum.accumulate(np.where(occ, idx, -10000), axis=1)
            T.append((z, occ, nxt, prv))
        # the key's layer over each x cell, centred (a cell on a layer boundary takes the layer on its +X side)
        li = np.full(n, -1)
        for i, c in enumerate(cs):
            li[(XS >= xc + c - P.LAYER / 2 - 1e-9) & (XS < xc + c + P.LAYER / 2 - 1e-9)] = i
        inside = li >= 0
        rows, worst, overlaps = [], {'+X': (9.0, None), '-X': (9.0, None)}, []
        for lf in lifts:
            dp, dm, cp, cm = 9.0, 9.0, 9.0, 9.0
            for z, occ, nxt, prv in T:
                iz = int(round((z - lf - ZK[0]) / GZ))
                if iz < 0 or iz >= len(ZK):
                    continue
                ko = KR[:, :, iz]                                              # [key layer, y]
                if not ko.any():
                    continue
                kx = np.zeros((len(YS), n), bool)
                kx[:, inside] = ko[li[inside], :].T
                if (kx & occ).any():
                    overlaps.append({'lift': lf, 'z': z, 'cells': int((kx & occ).sum())})
                    continue
                right = kx & ~np.concatenate([kx[:, 1:], np.zeros((len(YS), 1), bool)], axis=1)
                left = kx & ~np.concatenate([np.zeros((len(YS), 1), bool), kx[:, :-1]], axis=1)
                ry, rx = np.nonzero(right)
                if len(ry):
                    d = (nxt[ry, np.minimum(rx + 1, n - 1)] - rx) * GX
                    j = int(np.argmin(d))
                    if (YS[ry] >= yc).any():
                        cp = min(cp, float(d[YS[ry] >= yc].min()))
                    if d[j] < dp:
                        dp = float(d[j])
                        if dp < worst['+X'][0]:
                            worst['+X'] = (round(dp, 3), {'lift': lf, 'z': z, 'y': float(YS[ry[j]])})
                ly, lx = np.nonzero(left)
                if len(ly):
                    d = (lx - prv[ly, np.maximum(lx - 1, 0)]) * GX
                    j = int(np.argmin(d))
                    if (YS[ly] >= yc).any():
                        cm = min(cm, float(d[YS[ly] >= yc].min()))
                    if d[j] < dm:
                        dm = float(d[j])
                        if dm < worst['-X'][0]:
                            worst['-X'] = (round(dm, 3), {'lift': lf, 'z': z, 'y': float(YS[ly[j]])})
            rows.append((lf, round(dp, 3), round(dm, 3), round(cp, 3), round(cm, 3)))
        deep = [r for r in rows if r[0] <= lifts[0] - 2.0]
        cen = min(rows, key=lambda r: r[1] + r[2])
        out['openings'][round(xc, 3)] = {
            'free_x_least': {k: v[0] for k, v in worst.items()}, 'where': {k: v[1] for k, v in worst.items()},
            'centred_per_side_least': round((cen[1] + cen[2]) / 2, 3), 'centred_at_lift': cen[0],
            'free_x_at_the_stop': list(rows[0][1:3]),
            'free_x_least_from_2_under_the_stop': [min(r[1] for r in deep), min(r[2] for r in deep)] if deep else None,
            'plus_y_corners': {'+X': min(r[3] for r in rows), '-X': min(r[4] for r in rows)},
            'overlaps': overlaps[:6], 'n_overlaps': len(overlaps)}
    hw_ = P.KEY_FDM['hole'][2] / 2
    op = out['openings'].values()
    least = min(min(o['free_x_least'].values()) for o in op)
    cen = min(o['centred_per_side_least'] for o in op)
    cor = min(min(o['plus_y_corners'].values()) for o in op)
    out.update({'least_free_x_one_side': round(least, 3), 'least_one_side_as_printed_worst': round(least - hw_, 3),
                'centred_per_side': round(cen, 3), 'centred_per_side_as_printed_worst': round(cen - hw_, 3),
                'plus_y_corners_one_side': round(cor, 3), 'plus_y_corners_one_side_as_printed_worst': round(cor - hw_, 3),
                'plus_y_corner_rows_from_y': round(float(yc), 3)})
    out['ok'] = (all(o['n_overlaps'] == 0 for o in op) and cen - hw_ >= 0.15 - 1e-9
                 and cor - hw_ >= 0.15 - 1e-9)
    return out


def show_key_side_sweep(ks):
    if not ks or ks.get('ok') is None:
        return
    print(f"  key side sweep as sliced ({ks['key']}, {ks['key_layers']} layers, X {ks['key_x'][0]}..{ks['key_x'][1]}; "
          f"lifts {ks['lifts'][0]} to {ks['lifts'][1]} by {ks['lifts'][2]}): free X each way (+X / -X)")
    for xc, o in ks['openings'].items():
        print(f"    opening {xc:6.1f}: least {o['free_x_least']['+X']:.2f} / {o['free_x_least']['-X']:.2f}, at the stop "
              f"{o['free_x_at_the_stop'][0]:.2f} / {o['free_x_at_the_stop'][1]:.2f}, from 2 under the stop "
              f"{o['free_x_least_from_2_under_the_stop']}, centred {o['centred_per_side_least']:.3f} a side, +Y corners "
              f"{o['plus_y_corners']['+X']:.2f} / {o['plus_y_corners']['-X']:.2f}, "
              f"overlaps {o['n_overlaps']}")
    print(f"  key side sweep: centred {ks['centred_per_side']} a side, as printed at worst "
          f"{ks['centred_per_side_as_printed_worst']} (>= 0.15); the +Y corners (y >= {ks['plus_y_corner_rows_from_y']}) "
          f"one side {ks['plus_y_corners_one_side']}, at worst {ks['plus_y_corners_one_side_as_printed_worst']} (>= 0.15); "
          f"one side least anywhere {ks['least_free_x_one_side']} ({ks['least_one_side_as_printed_worst']} at worst, "
          f"reported): {'PASS' if ks['ok'] else 'FAIL'}")


def as_printed(report):
    """The closed case as printed (asprinted.py, 2026-10-13): the lid's home on the tub, every screw (params.SCREWS),
    the lid at home against the tub and the midplate, every latch's dead band. Needs the tub, the lid and the midplate
    sliced; None otherwise."""
    import params as P, joint, asprinted as A
    if not all(report.get(k, {}).get('gcode') for k in ('tub', 'lid', 'midplate')):
        return None
    L = {k: device_layers(k, report[k]) for k in ('lid', 'tub', 'midplate')}
    fps = hw.footprints()
    rims = ([(P.WALL_X0 - 2.0, y) for y in (20.0, 33.0, 47.0)] + [(P.WALL_X1 + 2.0, y) for y in (10.0, 20.0)]
            + [(x, P.TOP_IN + 1.5) for x in (20.0, 30.0)])     # on the rims' flats, clear of latches, keys and slots
    posts = [(fps[r]['cad'][0] + 1.5, fps[r]['cad'][1]) for r in ('H3', 'H4')]    # beside the posts' pins
    h = A.home(L['lid'], L['tub'], rims, posts, hw.PCB_T)
    board = A.board_room(L['lid'], L['tub'], h['dz'], posts, hw.PCB_T)      # 2026-10-20: the board floats at H3/H4
    screws = [A.screw(n, x, y, L['lid'], L['tub'], h['dz'], P.SCREW_L, P.Z_BACK) for n, (x, y) in P.SCREWS.items()]
    ov = A.overlap(L['lid'], L['tub'], L['midplate'], h['dz'], hw.PANEL_T_TOL)
    _, sh = joint.snap_profile()
    pk = joint.pocket_profile()
    barb_z = (sh['catch_low'] - 0.3, sh['z_top'])
    pocket_z = (pk[0][1] - 0.2, min(pk[2][1] + 0.2, P.FRAME_REAR - 0.1))
    latches = [A.latch(L['lid'], L['tub'], h['dz'], wall, c, joint.WALLS[wall]['face'], joint.WALLS[wall]['out'],
                       joint.WALLS[wall]['axis'], barb_z, pocket_z) for wall, cs in P.SNAPS.items() for c in cs]
    import bayread
    bay = bayread.run(L, h['dz'])
    usb = usb_fit(report, h['dz'], posts)
    ok = bool(h['dz'] is not None and all(s['ok'] for s in screws) and ov['ok'] and all(l['ok'] for l in latches)
              and bay['ok'] and board['ok'] and usb['ok'])
    return {'ok': ok, 'home': h, 'screws': screws, 'board': board, 'overlap': ov, 'latches': latches, 'bay': bay,
            'usb': usb, 'expected_home_dz': P.LID_HOME_DZ}


def usb_fit(report, dz, posts):
    """The USB port as printed (asprinted.usb_fit, 2026-10-22): a nominal plug centred in the Rev 1.0 socket and in the
    Rev 1.02 socket (0.14 nearer the board), each seated J1_SEAT_DZ nearer the board than KiCad draws it, on the board's
    posts, against the lid (at home) and the tub as laid. FAIL under USB_FIT_MIN on any flat. The hole
    is read from the lid's and the tub's layers with round line ends, as deposited."""
    import asprinted as A
    import params as P
    u = P.J1_REV10
    R = {k: device_layers(k, report[k], ends='round') for k in ('lid', 'tub')}
    bz = A.post_top(R['lid'], posts, dz)
    if dz is None or bz is None:
        return {'ok': False, 'rows': [], 'fails': ['no lid home or no board post'], 'min': P.USB_FIT_MIN}
    s = P.J1_SEAT_DZ
    sockets = {'Rev 1.0 (USB4085)': u['zc'] + s, 'Rev 1.02 (USB4105, 0.14 nearer)': u['zc'] + P.J1_REV102_DZ + s}
    return A.usb_fit(R['lid'], R['tub'], dz, bz, u['yc'], u['mouth_x'], P.INSERT_X1 + P.USB_FLOOR['t'], sockets,
                     plug=P.USB_PLUG, fit_min=P.USB_FIT_MIN)


def show_key_fit(kf):
    if not kf or not kf.get('pairs'):
        return
    e = kf['expected']
    print(f"  key fit as sliced (expected X skin {e['x_skin']}, X webs {e['x_webs']}, X slots {e['x_slots']}, Y skin "
          f"{e['y_skin']}, Y pocket {e['y_pocket']}, Y hooks {e['y_hooks']}; as printed at worst: less "
          f"{kf['fdm_worst']['x']} in X, {kf['fdm_worst']['y']} in Y):")
    print(f"    {'hole':17s} {'key':13s} {'X skin':>7s} {'X webs':>7s} {'X slot':>7s} {'Y skin':>7s} {'Y pckt':>7s} "
          f"{'Y hook':>7s} {'ledge':>6s}   as printed worst: X skin / webs / slots, Y skin / pocket / hooks")
    for r in kf['pairs']:
        if 'as_sliced' not in r:
            print(f"    {r['hole']:17s} {r['key']:13s} {r['note']}   <-- CHECK")
            continue
        v, p = r['as_sliced'], r['as_printed_worst']
        print(f"    {r['hole'] + ' ' + format(r['xc'], '.1f'):17s} {r['key']:13s} {v['x_skin']:7.3f} {v['x_webs']:7.3f} "
              f"{v['x_slots']:7.3f} {v['y_skin']:7.3f} {v['y_pocket']:7.3f} {v['y_hooks']:7.3f} {v['ledge']:6.3f}   "
              f"{p['x_skin']:.3f} / {p['x_webs']:.3f} / {p['x_slots']:.3f}, {p['y_skin']:.3f} / {p['y_pocket']:.3f} / "
              f"{p['y_hooks']:.3f}{'' if r['ok'] else '   <-- CHECK ' + ', '.join(r['fails'])}")
    s = kf.get('coupon_reproduces_the_opening')
    if s:
        print(f"    coupon strip - tub (SW9's opening): {s['coupon_strip_minus_tub']}{'' if s['ok'] else '   <-- CHECK'}")
    print(f"  key fit: {'PASS' if kf['ok'] else 'FAIL'}")


if __name__ == '__main__':
    import math
    if '--verify-only' in sys.argv:
        report = json.loads((OUT / 'slice-report.json').read_text())
        report['_features'] = verify(report)
        report['_bores'] = bores(report)
        report['_first_layer'] = first_layers(report)
        report['_islands'] = islands(report)
        report['_bridges'] = bridges(report)
        report['_gate'] = gate_checks(report)
        report['_key_fit'] = key_fit(report)
        report['_crank_sections'] = crank_sections(report)
        report['_key_on_end'] = key_on_end(report)
        report['_no_support'] = no_support(report)
        report['_key_side_sweep'] = key_side_sweep(report)
        wb = window_bevel(report)
        if wb is not None:
            report['_window_bevel'] = wb
        ap = report['_as_printed'] = as_printed(report)
        show(report)
        show_key_fit(report['_key_fit'])
        show_key_side_sweep(report['_key_side_sweep'])
        if wb is not None:
            show_window_bevel(wb)
        if ap is not None:
            import asprinted, bayread
            asprinted.show(ap)
            bayread.show(ap['bay'])
        (OUT / 'slice-report.json').write_text(json.dumps(report, indent=1))
        sys.exit(0 if ap is None or ap['ok'] else 1)
    pre = presets()
    import keys, params as P
    parts = sys.argv[1:] or ['tub', 'lid', 'midplate', keys.NAME, 'crank-M', 'crank-T', 'gate', 'coupon-strip',
                             'coupon-gate', 'pcba-dummy']
    report = {}
    for name in parts:
        stl = hw.OUT / 'print' / f'{name}.stl'
        info = slice_part(stl, pre)
        report[name] = info
        print(name, {k: v for k, v in info.items() if k != 'stderr_tail'}, flush=True)
    report['_features'] = verify(report)
    report['_bores'] = bores(report)
    report['_first_layer'] = first_layers(report)
    report['_islands'] = islands(report)
    report['_bridges'] = bridges(report)
    report['_gate'] = gate_checks(report)
    report['_key_fit'] = key_fit(report)
    report['_crank_sections'] = crank_sections(report)
    report['_key_on_end'] = key_on_end(report)
    report['_no_support'] = no_support(report)
    report['_key_side_sweep'] = key_side_sweep(report)
    wb = window_bevel(report)                # the standard tub only (None for the light strip)
    if wb is not None:
        report['_window_bevel'] = wb
    ap = report['_as_printed'] = as_printed(report)      # the closed case: screws, lid at home, latches
    show(report)
    show_key_fit(report['_key_fit'])
    show_key_side_sweep(report['_key_side_sweep'])
    if wb is not None:
        show_window_bevel(wb)
    if ap is not None:
        import asprinted, bayread
        asprinted.show(ap)
        bayread.show(ap['bay'])
    (OUT / 'slice-report.json').write_text(json.dumps(report, indent=1))
    if keys.NAME in report and report[keys.NAME]['gcode']:
        plot_layers(hw.ROOT / report[keys.NAME]['gcode'], [0.2, 2.0, 4.0], OUT / 'toolpath-key.png', 'key')
    for c in ('crank-M',):
        if c in report and report[c]['gcode']:
            plot_layers(hw.ROOT / report[c]['gcode'], [0.2, 3.0, 5.0], OUT / 'toolpath-crank.png', c)
    if 'lid' in report and report['lid']['gcode']:
        plot_layers(hw.ROOT / report['lid']['gcode'], [0.2, 2.0, 4.0], OUT / 'toolpath-lid.png', 'lid')
    sys.exit(0 if ap is None or ap['ok'] else 1)     # the as-printed read-backs stop the chain (the boxes above are read)
