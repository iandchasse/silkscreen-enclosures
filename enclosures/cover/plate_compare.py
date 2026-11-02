"""Did putting the slide covers on the case plates change anything else? (2026-11-01; OrcaSlicer CLI, never a GUI.)

    python -B plate_compare.py configs [--printer generic|cc2] [--size 426|368] [--builds a,b,...]
    python -B plate_compare.py public [--size 426|368]

The baseline is what the plates were before the covers: `out/baseline/<configs|configs-cc2>/` (the per-configuration projects as make_plates.py at HEAD
wrote them, with their slices) and `out/baseline/public/` (the public plate files). The new slices are configs_slice.py's (out/configs*/slice/) and, for
the public files, sliced here. For every plate that existed before, the extrusion of every object that existed before is read back as
configs_slice.buckets does, {(object, role, layer): mm of E} (the layers up to 1.0 mm one by one, the rest pooled), and no bucket may differ by more than
TOL = 0.3 mm (OrcaSlicer's CLI is not bit-deterministic: the same file sliced twice differs by 0.001 mm of jitter). The cover's own objects are left out of
the comparison; each plate's time and grams, before and after, are listed (a plate that gained the cover gains its time and grams; the others must not change).
"""
import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENC = HERE.parent
sys.path.insert(0, str(ENC / 'case-426' / 'src'))
sys.path.insert(0, str(ENC))
import configs_slice as CS          # noqa: E402

TOL = 0.3
DIRS = {'generic': 'configs', 'cc2': 'configs-cc2'}


def grams(path):
    m = re.search(r'total filament used \[g\] = ([\d.]+)', Path(path).read_text(errors='ignore'))
    return float(m.group(1)) if m else None


def is_cover(name):
    return name is not None and name.startswith('slide cover')


NOT_OBJECT = ('Skirt', 'Custom', 'Prime tower', 'Wipe tower')       # the skirt loops round everything on the plate (it grows with a new object), the start G-code's purge line


def buckets_xy(path, objects):
    """{(object, role, z or 'z>1'): mm of E} for a G-code with no '; printing object' markers (the Elegoo CC2's): each extruding move belongs to the object whose box
    (index.json, on the bed, plus the extruder offset in the footer) is nearest its end, as configs_slice.read_gcode attributes it (a move farther than REACH from every
    box is '(stray)'). Roles that are no object's (skirt, purge line) are left out."""
    t = Path(path).read_text(errors='ignore')
    m = re.search(r'^; extruder_offset = (-?[\d.]+)x(-?[\d.]+)', t, re.M)
    ox, oy = (float(m.group(1)), float(m.group(2))) if m else (0.0, 0.0)
    out, role, z, x, y = {}, None, 0.0, 0.0, 0.0
    for line in t.splitlines():
        if line.startswith(';TYPE:'):
            role = line[6:].strip()
        elif line.startswith(';Z:'):
            z = float(line[3:])
        elif line.startswith(('G1 ', 'G2 ', 'G3 ', 'G0 ')):
            v = {q[0]: float(q[1:]) for q in line.split(';')[0].split()[1:] if q[0] in 'XYE' and len(q) > 1}
            nx, ny, e = v.get('X', x), v.get('Y', y), v.get('E', 0.0)
            if line[:2] in ('G1', 'G2', 'G3') and e > 0 and (nx, ny) != (x, y) and role is not None and role not in NOT_OBJECT:
                bx, by = nx + ox, ny + oy
                d = [max(o['box'][0] - bx, bx - o['box'][2], o['box'][1] - by, by - o['box'][3], 0.0) for o in objects]
                i = min(range(len(objects)), key=d.__getitem__)
                name = objects[i]['name'] if d[i] <= CS.REACH else '(stray)'
                k = (name, role, z if z <= 1.0 else 'z>1')
                out[k] = out.get(k, 0.0) + e
            x, y = nx, ny
    return out


def compare(g_old, g_new, objs_old=None, objs_new=None):
    """-> (the buckets of existing objects that differ by more than TOL, the number compared, the largest difference, (time old, new), (g old, g new)).
    With objs_old / objs_new (index.json's objects of the plate) and a G-code without object markers, the objects are told apart by position (buckets_xy)."""
    b0, h0 = CS.buckets(g_old)
    b1, h1 = CS.buckets(g_new)
    if objs_old is not None and not any(k[0] for k in b0):
        b0, b1 = buckets_xy(g_old, objs_old), buckets_xy(g_new, objs_new)
    b0 = {k: v for k, v in b0.items() if not is_cover(k[0]) and k[1] not in NOT_OBJECT}
    b1 = {k: v for k, v in b1.items() if not is_cover(k[0]) and k[1] not in NOT_OBJECT}
    keys = set(b0) | set(b1)
    diff = {k: round(b1.get(k, 0.0) - b0.get(k, 0.0), 3) for k in keys if abs(b1.get(k, 0.0) - b0.get(k, 0.0)) > TOL}
    worst = max((abs(b1.get(k, 0.0) - b0.get(k, 0.0)) for k in keys), default=0.0)
    return diff, len(keys), worst, (h0['time'], h1['time']), (grams(g_old), grams(g_new))


def hms(s):
    return f'{s // 3600}h{(s % 3600) // 60:02d}m{s % 60:02d}s' if s is not None else '?'


def configs(printer, size, builds):
    base = ENC / f'case-{size}' / 'out' / 'baseline' / DIRS[printer]
    new = ENC / f'case-{size}' / 'out' / DIRS[printer]
    old_idx = json.loads((base / 'index.json').read_text())
    new_idx = json.loads((new / 'index.json').read_text())
    slugs = builds or list(new_idx)
    rows, bad, n_plates = {}, [], 0
    for s in slugs:
        n_old, n_new = len(old_idx[s]['plates']), len(new_idx[s]['plates'])
        rows[s] = []
        for n in range(1, n_old + 1):
            g0, g1 = base / 'slice' / s / f'plate_{n}.gcode', new / 'slice' / s / f'plate_{n}.gcode'
            if not (g0.exists() and g1.exists()):
                bad.append((s, n, 'missing G-code', str(g0.exists()), str(g1.exists())))
                continue
            diff, nb, worst, (t0, t1), (w0, w1) = compare(g0, g1, old_idx[s]['plates'][n - 1]['objects'], new_idx[s]['plates'][n - 1]['objects'])
            covers = [o['name'] for o in new_idx[s]['plates'][n - 1]['objects'] if is_cover(o['name'])]
            rows[s].append(dict(plate=n, buckets=nb, worst=round(worst, 3), apart=len(diff), t=(t0, t1), g=(w0, w1), cover=bool(covers)))
            n_plates += 1
            if diff:
                bad.append((s, n, 'buckets apart', sorted(diff.items(), key=lambda kv: -abs(kv[1]))[:3]))
        for n in range(n_old + 1, n_new + 1):         # a plate the covers added: only the cover prints on it (or the cover and its neighbours)
            g1 = new / 'slice' / s / f'plate_{n}.gcode'
            rows[s].append(dict(plate=n, new=True, t=(None, CS.buckets(g1)[1]['time']) if g1.exists() else None, g=(None, grams(g1)) if g1.exists() else None))
    return rows, bad, n_plates


def public(size):
    import make_plates as MP
    rows, bad, n_plates = {}, [], 0
    for name in (f'silkscreen-{size}-plates.3mf',):
        old = ENC / 'case-426' / 'out' / 'baseline' / 'public' / name
        new = MP.PRINT / name
        count = lambda f: len(re.findall(r'<plate>', zipfile.ZipFile(f).read('Metadata/model_settings.config').decode('ascii')))
        n_old, n_new = count(old), count(new)
        rows[name] = []
        dest0, dest1 = ENC / f'case-{size}' / 'out' / 'baseline' / 'public-slice', ENC / f'case-{size}' / 'out' / 'public-slice'
        for n in range(1, max(n_old, n_new) + 1):
            g1 = None
            if n <= n_new:
                r, g1 = CS.slice_plate(new, n, dest1 / f'plate{n}')
                if r.returncode:
                    bad.append((name, n, 'new plate does not slice', r.returncode))
                    continue
            if n <= n_old:
                r, g0 = CS.slice_plate(old, n, dest0 / f'plate{n}')
                if r.returncode:
                    bad.append((name, n, 'baseline plate does not slice', r.returncode))
                    continue
                diff, nb, worst, (t0, t1), (w0, w1) = compare(g0, g1)
                rows[name].append(dict(plate=n, buckets=nb, worst=round(worst, 3), apart=len(diff), t=(t0, t1), g=(w0, w1)))
                n_plates += 1
                if diff:
                    bad.append((name, n, 'buckets apart', sorted(diff.items(), key=lambda kv: -abs(kv[1]))[:3]))
            else:
                rows[name].append(dict(plate=n, new=True, t=(None, CS.buckets(g1)[1]['time']), g=(None, grams(g1))))
    return rows, bad, n_plates


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('what', choices=('configs', 'public'))
    ap.add_argument('--printer', choices=tuple(DIRS), default='generic')
    ap.add_argument('--size', choices=('426', '368'), default='426')
    ap.add_argument('--builds', default=None)
    a = ap.parse_args()
    if a.what == 'configs':
        rows, bad, n = configs(a.printer, a.size, [s for s in a.builds.split(',') if s] if a.builds else None)
    else:
        rows, bad, n = public(a.size)
    print(f'{a.what} {a.printer} {a.size}: {n} existing plates compared (tolerance {TOL} mm of E per object/role/layer bucket), {len(bad)} problems')
    for k, v in rows.items():
        for r in v:
            if r.get('new'):
                print(f'  {k} plate {r["plate"]} (new): {hms(r["t"][1]) if r["t"] else "?"}, {r["g"][1] if r["g"] else "?"} g')
            else:
                dt = (r['t'][1] - r['t'][0]) if None not in r['t'] else None
                dg = round(r['g'][1] - r['g'][0], 2) if None not in r['g'] else None
                print(f'  {k} plate {r["plate"]}: {r["buckets"]} buckets, worst {r["worst"]} mm, {r["apart"]} apart; time {hms(r["t"][0])} -> {hms(r["t"][1])} ({dt:+d} s), '
                      f'{r["g"][0]} -> {r["g"][1]} g ({dg:+.2f})' + ('  [carries the cover]' if r.get('cover') else ''))
    for b in bad:
        print('  PROBLEM', *b)
    out = ENC / 'case-426' / 'out' / f'plate-compare-{a.what}-{a.printer}-{a.size}.json'
    out.write_text(json.dumps({'rows': rows, 'problems': bad}, indent=1, default=str))
    sys.exit(1 if bad else 0)
