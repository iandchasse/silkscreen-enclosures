"""Do the two colour switches of color_options.py work as the slicer sees them? (2026-11-06; OrcaSlicer CLI, never a GUI.)

    python -B color_check.py [--size 426|368] [--printer cc2|generic] [--slug standard]

Takes the project make_plates.py wrote (case-<size>/out/configs[-cc2]/<slug>.3mf), keeps only its tub printable on plate 1 (every other item
printable="0"), and slices three copies with the OrcaSlicer CLI, switching the lines ON the way a user does in the GUI (by editing
Metadata/model_settings.config):
  neg     the project as shipped (2026-11-07: the front lines part is a Negative Volume, engraved)
  off     the front lines part: Change type -> Modifier (no setting: no lines)
  lines   the front lines part: Change type -> Modifier, then filament 2
and reads the G-code back by tool (filament): what the engraving removed, and where filament 2 lies and how much.
"""
import argparse
import json
import math
import re
import sys
import zipfile
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import LineString
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'case-426' / 'src'))
import configs_slice as CS          # noqa: E402

DIRS = {'generic': 'configs', 'cc2': 'configs-cc2'}
LAYER = 0.2
G_PER_MM = math.pi * 0.875 ** 2 * 1.24e-3      # grams of 1.75 mm PLA per mm of filament


def variant(src, dst, how):
    """dst: src with the tub and the lid alone printable and the switches of `how` ON; -> (tub id, lid id)."""
    with zipfile.ZipFile(src) as zi:
        items = [(it, zi.read(it.filename)) for it in zi.infolist()]
    ids = {}
    out = []
    for it, data in items:
        if it.filename == 'Metadata/model_settings.config':
            t = data.decode('ascii')
            for m in re.finditer(r'<object id="(\d+)">\s*<metadata key="name" value="([^"]*)"', t):
                if m.group(2) in ('tub', 'lid'):
                    ids[m.group(2)] = m.group(1)

            def obj(m):
                name = re.search(r'key="name" value="([^"]*)"', m.group(2)).group(1)
                body = m.group(0)

                def part(q):
                    pn = re.search(r'key="name" value="([^"]*)"', q.group(0)).group(1)
                    s = q.group(0)
                    f2 = '      <metadata key="extruder" value="2"/>\n      <mesh_stat'
                    if name == 'tub' and pn.startswith('front lines'):
                        assert 'subtype="negative_part"' in s, 'the front lines should ship as a Negative Volume'
                        if how in ('off', 'lines'):
                            s = s.replace('subtype="negative_part"', 'subtype="modifier_part"')
                        if how == 'lines':
                            s = s.replace('      <mesh_stat', f2)
                    return s
                return re.sub(r'    <part id="\d+" subtype="\w+">.*?</part>\n', part, body, flags=re.S)
            t = re.sub(r'  <object id="(\d+)">(.*?)</object>\n', obj, t, flags=re.S)
            data = t.encode('ascii')
        out.append([it, data])
    keep = {ids['tub']}
    for o in out:
        if o[0].filename == '3D/3dmodel.model':
            o[1] = re.sub(r'<item objectid="(\d+)"[^>]*/>',
                          lambda m: m.group(0) if m.group(1) in keep else m.group(0).replace('printable="1"', 'printable="0"'),
                          o[1].decode('ascii')).encode('ascii')
    dst.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dst, 'w') as zo:
        for it, data in out:
            zi = zipfile.ZipInfo(it.filename, it.date_time)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = it.external_attr
            zo.writestr(zi, data)
    return ids


def read(path):
    """Every extruding move of a G-code: arrays z, tool, x0, y0, x1, y1, width, e, support (bool); the footer's grams per filament and the tool changes."""
    t = Path(path).read_text(errors='ignore')
    m = re.search(r'^; extruder_offset = (-?[\d.]+)x(-?[\d.]+)', t, re.M)
    ox, oy = (float(m.group(1)), float(m.group(2))) if m else (0.0, 0.0)
    rows, tool, role, z, w, x, y, changes = [], 0, None, 0.0, 0.42, 0.0, 0.0, 0
    for line in t.splitlines():
        if line.startswith(';TYPE:'):
            role = line[6:].strip()
        elif line.startswith(';Z:'):
            z = float(line[3:])
        elif line.startswith(';WIDTH:'):
            w = float(line[7:])
        elif re.match(r'T\d+\s*$', line):
            tool = int(line[1:])
            changes += 1
        elif line.startswith(('G1 ', 'G0 ')):
            v = {q[0]: float(q[1:]) for q in line.split(';')[0].split()[1:] if q[0] in 'XYE' and len(q) > 1}
            nx, ny = v.get('X', x), v.get('Y', y)
            if line[:2] == 'G1' and v.get('E', 0.0) > 0 and (nx, ny) != (x, y) and role not in (None, 'Custom', 'Skirt', 'Prime tower', 'Wipe tower'):
                rows.append((z, tool, x + ox, y + oy, nx + ox, ny + oy, w, v['E'], role in CS.SUPPORT))
            x, y = nx, ny
    a = np.array(rows, dtype=float).reshape(-1, 9)
    g = re.search(r'^; filament used \[g\] = (.+)$', t, re.M)
    return dict(z=a[:, 0], tool=a[:, 1].astype(int), x0=a[:, 2], y0=a[:, 3], x1=a[:, 4], y1=a[:, 5], w=a[:, 6], e=a[:, 7], sup=a[:, 8] > 0,
                grams=[float(v) for v in g.group(1).split(',')] if g else [], changes=changes)


def inside(poly, d):
    mx, my = (d['x0'] + d['x1']) / 2, (d['y0'] + d['y1']) / 2
    return shapely.contains_xy(poly, mx, my)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--size', choices=('426', '368'), default='426')
    ap.add_argument('--printer', choices=tuple(DIRS), default='cc2')
    ap.add_argument('--slug', default='standard')
    o = ap.parse_args()
    root = HERE / f'case-{o.size}' / 'out' / DIRS[o.printer]
    entry = json.loads((root / 'index.json').read_text())[o.slug]
    work = HERE / f'case-{o.size}' / 'out' / 'color-check' / o.printer
    objs = {q['name']: q for q in entry['plates'][0]['objects']}
    tub = objs['tub']
    import trimesh
    import color_options as CO
    key = ('case-426' if o.size == '426' else 'case-368', 'chinless' in o.slug)
    bodies = trimesh.load(CO.LINE_FILES[key], force='mesh').split(only_watertight=False)
    lines = [shapely.geometry.Polygon(np.array(b.vertices)[:, :2] + np.array(tub['box'][:2])).convex_hull for b in bodies]
    L = unary_union(lines)
    L_in, L_out = L.buffer(-0.15), L.buffer(0.10)
    print(f'{o.size} {o.printer} {o.slug}: {len(lines)} lines, area {L.area:.1f} mm2')
    res = {}
    for how in ('off', 'neg', 'lines'):
        f = work / f'{how}.3mf'
        variant(root / entry['file'], f, how)
        r, g = CS.slice_plate(f, 1, work / how)
        if r.returncode or not g.exists():
            print(f'  {how}: OrcaSlicer failed ({r.returncode}) {r.stderr[-500:] if r.stderr else ""}')
            continue
        res[how] = read(g)
        d = res[how]
        print(f'  {how}: slices; {len(d["z"])} moves, tool changes {d["changes"]}, grams per filament {d["grams"]}')
    if 'off' not in res:
        sys.exit(1)

    def onbox(d, b):
        return (np.minimum(d['x0'], d['x1']) >= b[0] - 1e-6) & (np.maximum(d['x0'], d['x1']) <= b[3] + 1e-6) & \
               (np.minimum(d['y0'], d['y1']) >= b[1] - 1e-6) & (np.maximum(d['y0'], d['y1']) <= b[4] + 1e-6)
    ok = True

    def row(what, good, val):
        nonlocal ok
        ok &= bool(good)
        print(f'  {"ok  " if good else "FAIL"} {what}: {val}')

    def length(d, m):
        return float(np.hypot(d['x1'] - d['x0'], d['y1'] - d['y0'])[m].sum())
    for how, d in res.items():
        d['intub'] = (d['x0'] >= tub['box'][0] - 3) & (d['x1'] <= tub['box'][2] + 3) & (d['y0'] >= tub['box'][1] - 3) & (d['y1'] <= tub['box'][3] + 3) & \
                     (d['x0'] <= tub['box'][2] + 3) & (d['y0'] <= tub['box'][3] + 3) & (d['x1'] >= tub['box'][0] - 3) & (d['y1'] >= tub['box'][1] - 3)
        d['inL'] = inside(L_out, d)
        d['inLin'] = inside(L_in, d)
    off = res['off']
    low = lambda d: d['z'] <= 0.6 + 1e-6
    # (a) engraved
    if 'neg' in res:
        n = res['neg']
        a0, a1 = length(off, off['intub'] & off['inLin'] & low(off)), length(n, n['intub'] & n['inLin'] & low(n))
        up0, up1 = length(off, off['intub'] & off['inL'] & ~low(off)), length(n, n['intub'] & n['inL'] & ~low(n))
        row('(a) Negative Volume: the lines are gaps in the first 3 layers', a0 > 100 and a1 < 0.03 * a0,
            f'extrusion inside the lines (shrunk 0.15) z<=0.6: {a0:.0f} mm off -> {a1:.1f} mm; above 0.6: {up0:.0f} -> {up1:.0f} mm; filament 2 not used: {n["grams"]}')
    # (b) second colour, lines
    if 'lines' in res:
        d = res['lines']
        t1 = (d['tool'] == 1)
        outside = length(d, t1 & ~d['inL'])
        cover = float((d['w'] * np.hypot(d['x1'] - d['x0'], d['y1'] - d['y0']))[t1 & d['inL']].sum()) / (L.area * 3)
        zs = sorted(set(np.round(d['z'][t1], 2).tolist()))
        row('(b) lines in filament 2: only inside the lines, only the first 3 layers', t1.any() and outside < 1.0 and max(zs) <= 0.6 + 1e-6 and not (t1 & ~d['intub']).any(),
            f'layers {zs}; filament-2 length outside the lines (grown 0.1): {outside:.2f} mm of {length(d, t1):.0f}; the lines\' area covered {cover:.2f}; '
            f'filament 2 {d["grams"][1] if len(d["grams"]) > 1 else 0} g; tool changes {d["changes"]}; supports on filament 2: {int((t1 & d["sup"]).sum())}')
        t0in = length(d, ~t1 & d['intub'] & d['inLin'] & low(d))
        row('(b) the case colour leaves the lines to filament 2', t0in < 0.1 * length(off, off['intub'] & off['inLin'] & low(off)), f'filament-1 length left in the lines: {t0in:.0f} mm')
    print('ALL OK' if ok else 'PROBLEMS')
    json.dump({k: {'grams': v['grams'], 'changes': v['changes']} for k, v in res.items()}, open(work / 'result.json', 'w'))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
