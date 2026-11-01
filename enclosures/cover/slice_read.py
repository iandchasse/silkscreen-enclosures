"""Slice the cover plate file with the OrcaSlicer CLI (never a GUI) and read the G-code back.

    python -B slice_read.py [--printer generic|cc2] [--plates 1,2,3,4] [--no-slice]

For every plate: (1) the roles in the G-code and the extrusion of each (supports must be 0); (2) layer by layer, each part's
section (the mesh at the layer's mid-plane, in the plate's frame) against what the slicer laid (its lines thickened to their
;WIDTH): the area of the section with no line near it (missing) and the area of lines far from the section (extra); (3) the
overhang as laid: the area of each layer's lines that is farther than REACH from the layer below's lines (a bridge or a layer
hanging in air), worst layer and where; (4) the prong and its ridge and the lip, by their own boxes: lines per layer, the
width of the prong's wall, how far each layer of the lip steps past the one below; (5) time and grams from the footer.
The numbers are what the slicer lays for the generic / CC2 presets of the plate file; nothing was printed.
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import shapely
import trimesh
from shapely.geometry import LineString, box

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_cover_plates as MC          # noqa: E402
import model as M                      # noqa: E402

MP = MC.MP
ORCA = Path(r'C:\Program Files\OrcaSlicer\orca-slicer.exe')
OUT = HERE / 'out' / 'slice'
REACH = 0.30            # mm: a layer's line this far (centre line + half width) beyond the layer below counts as in the air
MIN_FREE = 8e9          # bytes of commit charge that must stay free (CLAUDE.local.md: >= 8 GB)


def free_commit():
    r = subprocess.run(['powershell', '-NoProfile', '-Command',
                        '(Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory * 1024'], capture_output=True, text=True)
    return float(r.stdout.strip())


def slice_plate(f, n, dest):
    dest.mkdir(parents=True, exist_ok=True)
    for g in dest.glob('*'):
        if g.is_file():
            g.unlink()
    while free_commit() < MIN_FREE:
        time.sleep(5)
    t = time.time()
    r = subprocess.run([str(ORCA), '--slice', str(n), '--outputdir', str(dest), str(f)], capture_output=True, timeout=1800,
                       cwd=dest)
    return r, dest / f'plate_{n}.gcode', time.time() - t


def parse(path):
    """-> (head, layers {z: [(role, (x0, y0), (x1, y1), width)]}) in bed coordinates (the extruder offset added back)."""
    t = Path(path).read_text(errors='ignore')
    m = re.search(r'^; extruder_offset = (-?[\d.]+)x(-?[\d.]+)', t, re.M)
    ox, oy = (float(m.group(1)), float(m.group(2))) if m else (0.0, 0.0)
    head = {}
    for key, pat in {'grams': r'total filament used \[g\] = ([\d.]+)', 'layers': r'total layers count = (\d+)',
                     'time': r'estimated printing time \(normal mode\) = (.+)'}.items():
        mm = re.search(pat, t)
        head[key] = mm.group(1).strip() if mm else None
    layers, role, z, w, x, y = {}, None, 0.0, 0.42, 0.0, 0.0
    rel = True
    for line in t.splitlines():
        if line.startswith(';TYPE:'):
            role = line[6:].strip()
        elif line.startswith(';Z:'):
            z = round(float(line[3:]), 3)
        elif line.startswith(';WIDTH:'):
            w = float(line[7:])
        elif line.startswith('M82'):
            rel = False
        elif line.startswith(('G1 ', 'G0 ', 'G2 ', 'G3 ')):
            v = {q[0]: float(q[1:]) for q in line.split(';')[0].split()[1:] if q[0] in 'XYE' and len(q) > 1}
            nx, ny = v.get('X', x), v.get('Y', y)
            if line[:2] == 'G1' and v.get('E', 0.0) > 0 and (nx, ny) != (x, y) and role is not None:
                layers.setdefault(z, []).append((role, (x + ox, y + oy), (nx + ox, ny + oy), w, v['E']))
            x, y = nx, ny
    if not rel:
        raise SystemExit(f'{path}: absolute E')
    return head, layers


def footprint(segs):
    geoms = [LineString([a, b]).buffer(w / 2, cap_style='round') for _, a, b, w, _ in segs if a != b]
    return shapely.union_all(geoms) if geoms else shapely.Polygon()


def section_at(mesh, z):
    s = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    g = shapely.Polygon()
    if s is not None:
        for p in s.discrete:
            if len(p) >= 4:
                g = g.symmetric_difference(shapely.Polygon(p[:, :2]).buffer(0))
    return g


def to_print(s, pts_design, design_bounds):
    """Design frame -> print frame (half turn about Y, min corner at the origin), for boxes."""
    (xmin, ymin, zmin), (xmax, ymax, zmax) = design_bounds
    return [(xmax - x, y - ymin, zmax - z) for x, y, z in pts_design]


def seg_points(segs, step=0.2):
    """Sample points along extrusion segments: -> (x, y) arrays."""
    xs, ys = [], []
    for _, a, b, w, _ in segs:
        n = max(1, int(np.hypot(b[0] - a[0], b[1] - a[1]) / step))
        t = (np.arange(n) + 0.5) / n
        xs.append(a[0] + (b[0] - a[0]) * t)
        ys.append(a[1] + (b[1] - a[1]) * t)
    if not xs:
        return np.zeros(0), np.zeros(0)
    return np.concatenate(xs), np.concatenate(ys)


def read_plate(plate_parts, layers, head, label, specials):
    """plate_parts: [Part] laid out (meshes in plate coordinates). layers from parse(). Predicates and point samples only (the
    overlay operations choke on the unions of thousands of round-capped lines)."""
    roles = {}
    for z, segs in layers.items():
        for r, *_, e in segs:
            roles[r] = roles.get(r, 0.0) + e
    rep = dict(label=label, roles={k: round(v, 1) for k, v in sorted(roles.items())}, head=head)
    rep['support_E'] = round(sum(v for k, v in roles.items() if 'upport' in k), 3)
    zs = sorted(layers)
    rep['layers'] = len(zs)
    out = []
    step = 0.2
    for p in plate_parts:
        mesh = p.mesh
        lo, hi = mesh.bounds
        pad = 3.5
        worst_miss = (0.0, None, 0.0)
        worst_extra = (0.0, None)
        worst_air = (0.0, None, 0.0)
        n_air = 0
        bridges = []
        prev = None
        n_layers = 0
        for z in zs:
            if z > hi[2] + 0.01 or z <= 0.0:
                continue
            segs = [sg for sg in layers[z] if (lo[0] - pad <= min(sg[1][0], sg[2][0]) and max(sg[1][0], sg[2][0]) <= hi[0] + pad
                                                  and lo[1] - pad <= min(sg[1][1], sg[2][1]) and max(sg[1][1], sg[2][1]) <= hi[1] + pad
                                                  and 'upport' not in sg[0] and sg[0] not in ('Skirt', 'Custom'))]
            sec = shapely.make_valid(section_at(mesh, z - 0.1)).buffer(0)       # the layer's mid-plane (layer top z, 0.2 thick)
            if sec.is_empty:
                continue
            n_layers += 1
            fp = shapely.make_valid(footprint(segs)).buffer(0)
            # missing: grid points of the section with no line within 0.12
            x0, y0, x1, y1 = sec.bounds
            gx, gy = np.meshgrid(np.arange(x0, x1, step), np.arange(y0, y1, step))
            gx, gy = gx.ravel(), gy.ravel()
            ins = shapely.contains_xy(sec, gx, gy) & ~shapely.contains_xy(sec.buffer(-0.9), gx, gy)     # the shell zone (4 lines deep)
            gx, gy = gx[ins], gy[ins]
            cov = shapely.contains_xy(fp.buffer(0.12), gx, gy)
            miss = float((~cov).sum()) * step * step
            # extra: line samples more than 0.35 outside the section
            sx, sy = seg_points(segs, step)
            wsegs = [sg for sg in segs if sg[0] in ('Outer wall', 'Inner wall', 'Overhang wall', 'Bridge')]
            wx, wy = seg_points(wsegs, step)
            br = [sg for sg in segs if sg[0] == 'Bridge']
            if br:
                bx, by = seg_points(br, step)
                bridges.append((z, round(len(bx) * step, 1), [round(float(bx.min()), 1), round(float(by.min()), 1), round(float(bx.max()), 1), round(float(by.max()), 1)]))
            ex = float((~shapely.contains_xy(sec.buffer(0.35), sx, sy)).sum()) * step
            if miss > worst_miss[0]:
                worst_miss = (miss, z, float(sec.area))
            if ex > worst_extra[0]:
                worst_extra = (ex, z)
            if prev is not None and len(wx):
                near = shapely.contains_xy(prev.buffer(REACH), wx, wy)
                outx, outy = wx[~near], wy[~near]
                length = len(outx) * step
                hang = float(shapely.distance(shapely.points(outx, outy), prev).max()) if len(outx) else 0.0
                if hang > worst_air[0]:
                    worst_air = (hang, z, length)
                if length > 1.0:
                    n_air += 1
            prev = fp
        out.append(dict(part=p.name, layers=n_layers, worst_missing_mm2=round(worst_miss[0], 2), at_z=worst_miss[1],
                        of_section=round(worst_miss[2], 1), worst_extra_mm=round(worst_extra[0], 2), extra_at_z=worst_extra[1],
                        worst_hang_mm=round(worst_air[0], 2), hang_at_z=worst_air[1], hang_length_mm=round(worst_air[2], 1),
                        n_layers_with_line_in_air=n_air, bridge_layers=bridges[:12], n_bridge_layers=len(bridges)))
    rep['parts'] = out
    return rep


def intervals(mask, ys):
    out, start = [], None
    for i, m in enumerate(mask):
        if m and start is None:
            start = ys[i]
        if not m and start is not None:
            out.append((round(float(start), 2), round(float(ys[i - 1]), 2)))
            start = None
    if start is not None:
        out.append((round(float(start), 2), round(float(ys[-1]), 2)))
    return out


def probe(part, layers, design_bounds, x_d, y0_d, y1_d, z_d_range, label):
    """The section of the mesh against the laid lines along one line of y at one x (design coordinates: the cover on the front
    at home), on every layer whose design z is in z_d_range = (lo, hi). -> [(layer top z, design z, [mesh intervals], [laid
    intervals])] with y in the design frame. Print frame: x = xmax - x_d, y = y_d - ymin, z = zmax - z_d, then the part's
    place on the plate (its min corner)."""
    (xmin, ymin, zmin), (xmax, ymax, zmax) = design_bounds
    ox, oy = part.mesh.bounds[0][0], part.mesh.bounds[0][1]
    xp = xmax - x_d + ox
    ys_d = np.arange(y0_d, y1_d, 0.02)
    yp = ys_d - ymin + oy
    rows = []
    for z in sorted(layers):
        zd = zmax - (z - 0.1)
        if not (z_d_range[0] <= zd <= z_d_range[1]):
            continue
        segs = [sg for sg in layers[z] if sg[0] not in ('Skirt', 'Custom') and 'upport' not in sg[0]]
        fp = shapely.make_valid(footprint(segs)).buffer(0)
        sec = shapely.make_valid(section_at(part.mesh, z - 0.1)).buffer(0)
        mesh_iv = intervals(shapely.contains_xy(sec, np.full(len(yp), xp), yp), ys_d)
        laid_iv = intervals(shapely.contains_xy(fp, np.full(len(yp), xp), yp), ys_d)
        rows.append((z, round(zd, 2), mesh_iv, laid_iv))
    return rows


def cover_probes(part, layers, group):
    """The lip, the prong and the ridge as laid, against the mesh, on every layer they stand in (probe()). The probes are lines
    of y at one x each: the lip in the middle of the straight run (u = 30), the prong where it is 0.8 thick (u = 2), the ridge
    at the middle of its flat top. max_dev: the largest difference between an end of a mesh interval and the matching end of
    the laid one."""
    s = M.spec(group)
    d = trimesh.load(HERE / 'out' / 'design' / f'{group}.stl')
    bd = d.bounds
    yw, tw = s['yw_t'], s['tw']
    y_hi = yw + tw + 0.5
    ux = s['u_a'] + s['r_i'] + s['f_top'] / 2
    specs = {'lip (u=30)': (30.0, s['Y1'] - 1.0, y_hi, (s['z_lb'], s['z_cf0'] + 0.2), 'the 47-degree face and its flat, tip 1.1 past the end face'),
             'prong (u=2)': (2.0, yw - 0.3, y_hi, (s['prong_z_lo'], s['z_o']), '0.8 mm wall from the bed up'),
             'ridge (flat top)': (ux, yw - s['b'] - 0.3, y_hi, (s['ridge_z'][0] - 0.2, s['ridge_z'][1] + 0.2),
                                  'the ridge standing 1.0 off the prong, 45-degree ends')}
    out = {}
    for k, (x, y0, y1, zr, note) in specs.items():
        rows = probe(part, layers, bd, x, y0, y1, zr, k)
        dev = 0.0
        for _, _, mi, li in rows:
            if len(mi) != len(li):
                dev = max(dev, 9.99)
                continue
            for (a, b), (c, e) in zip(mi, li):
                dev = max(dev, abs(a - c), abs(b - e))
        out[k] = dict(layers=len(rows), max_dev=dev, note=note, sample=[(r[0], r[1], r[2], r[3]) for r in rows[:: max(1, len(rows) // 6)]])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--printer', choices=('generic', 'cc2'), default='generic')
    ap.add_argument('--plates', default='1,2,3,4')
    ap.add_argument('--no-slice', action='store_true')
    a = ap.parse_args()
    c = MC.case(a.printer)
    f = c['out']
    plates = MP.lay_out(c)
    report = {}
    for n in [int(q) for q in a.plates.split(',')]:
        name, parts = plates[n - 1]
        dest = OUT / a.printer / f'plate{n}'
        gcode = dest / f'plate_{n}.gcode'
        if not a.no_slice or not gcode.exists():
            r, gcode, secs = slice_plate(f, n, dest)
            print(f'plate {n}: sliced in {secs:.0f} s (exit {r.returncode})')
            if r.returncode or not gcode.exists():
                print(r.stderr.decode(errors='replace')[-1500:])
                report[n] = dict(error=r.returncode)
                continue
        head, layers = parse(gcode)
        rep = read_plate(parts, layers, head, name, None)
        report[n] = rep
        if n >= 2:
            rep['probes'] = cover_probes(parts[0], layers, {2: 'keyed', 3: 'chinless', 4: 'x3'}[n])
            for k, v in rep['probes'].items():
                print(f'   {k}: {v["layers"]} layers probed, mesh vs laid ends differ by at most {v["max_dev"]:.2f} mm; {v["note"]}')
        print(f'plate {n} "{name}": {rep["layers"]} layers, {head["time"]}, {head["grams"]} g, support extrusion '
              f'{rep["support_E"]} mm, roles {rep["roles"]}')
        for p in rep['parts']:
            print(f'   {p["part"]}: {p["layers"]} layers; section with no line within 0.12: worst {p["worst_missing_mm2"]} mm2 '
                  f'(z {p["at_z"]}, of {p["of_section"]}); line more than 0.35 outside it: worst {p["worst_extra_mm"]} mm (z {p["extra_at_z"]}); '
                  f'a line hangs past the layer below by at most {p["worst_hang_mm"]} mm (z {p["hang_at_z"]}, {p["hang_length_mm"]} mm of it); '
                  f'{p["n_layers_with_line_in_air"]} layers with > 1 mm of wall line over air; Bridge-role lines on {p["n_bridge_layers"]} layers '
                  f'{[(b[0], b[1]) for b in p["bridge_layers"][:6]]}')
    (OUT / f'read-{a.printer}.json').write_text(json.dumps(report, indent=1, default=str))


if __name__ == '__main__':
    main()
