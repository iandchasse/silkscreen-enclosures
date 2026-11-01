"""Does the two-colour logo switch work the way make_plates.py's lid switch does? (OrcaSlicer CLI, never a GUI.)

    python -B inlay_check.py [--plate 1]

The cover plate files carry the two logo inlays as modifier parts with no filament: they print nothing (the switch is OFF). This copies
print/silkscreen-cover-plates.3mf to out/slice/inlay-on.3mf with the two inlay volumes switched ON the way a user does it in OrcaSlicer (Change
type -> Part, Change filament -> 2: here by editing Metadata/model_settings.config), slices the plate and reads the G-code back: filament 2
must be extruded only inside the logo's footprint, on the first layers, and the body's own filament must not change (the engraving is empty
when OFF). The OFF slice is out/slice/generic/plate<N>/ (slice_read.py).
"""
import argparse
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_cover_plates as MC          # noqa: E402
import slice_read as SR                 # noqa: E402

OUT = HERE / 'out' / 'slice'


def switch_on(src, dst):
    """dst: src with every 'logo ...' modifier_part switched to a normal part printed with filament 2."""
    n = 0
    with zipfile.ZipFile(src) as zi, zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as zo:
        for info in zi.infolist():
            data = zi.read(info.filename)
            if info.filename == 'Metadata/model_settings.config':
                t = data.decode('utf-8')

                def fix(m):
                    nonlocal n
                    block = m.group(0)
                    if 'name" value="logo ' not in block:
                        return block
                    n += 1
                    block = block.replace('subtype="modifier_part"', 'subtype="normal_part"')
                    return block.replace('<metadata key="name"', '<metadata key="extruder" value="2"/>\n      <metadata key="name"', 1)
                t = re.sub(r'<part id="\d+" subtype="modifier_part">.*?</part>', fix, t, flags=re.S)
                data = t.encode('utf-8')
            zo.writestr(info, data)
    return n


def by_tool(gcode):
    """-> (grams per filament from the footer, {tool: [(x, y, z)] of its extrusion moves}), absolute coordinates as printed."""
    t = Path(gcode).read_text(errors='ignore')
    m = re.search(r'^; filament used \[g\] = (.+)$', t, re.M)
    grams = [float(v) for v in m.group(1).split(',')] if m else []
    tool, z, x, y = 0, 0.0, 0.0, 0.0
    pts = {0: [], 1: []}
    for line in t.splitlines():
        if re.match(r'T[01]\b', line):
            tool = int(line[1])
        elif line.startswith(';Z:'):
            z = float(line[3:])
        elif line.startswith(('G1 ', 'G0 ')):
            v = {q[0]: float(q[1:]) for q in line.split(';')[0].split()[1:] if q[0] in 'XYE' and len(q) > 1}
            nx, ny = v.get('X', x), v.get('Y', y)
            if line.startswith('G1') and v.get('E', 0.0) > 0 and (nx, ny) != (x, y):
                pts[tool].append((nx, ny, z))
            x, y = nx, ny
    return grams, pts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plate', type=int, default=1)
    a = ap.parse_args()
    c = MC.case('generic')
    src = c['out']
    OUT.mkdir(parents=True, exist_ok=True)
    dst = OUT / 'inlay-on.3mf'
    n = switch_on(src, dst)
    print(f'{n} logo volumes switched to normal parts with filament 2 in {dst.name}')
    plates = MC.MP.lay_out(c)
    name, parts = plates[a.plate - 1]
    p = parts[0]
    d = OUT / 'generic' / f'inlay-on-plate{a.plate}'
    r, gcode, secs = SR.slice_plate(dst, a.plate, d)
    print(f'plate {a.plate} ON: sliced in {secs:.0f} s (exit {r.returncode})')
    if r.returncode or not gcode.exists():
        print(r.stderr.decode(errors='replace')[-1500:])
        sys.exit(1)
    grams, pts = by_tool(gcode)
    off = SR.parse(OUT / 'generic' / f'plate{a.plate}' / f'plate_{a.plate}.gcode')[0]
    print(f'ON grams per filament {grams}; OFF (the plate as shipped) total {off["grams"]} g')
    t1 = np.array(pts[1])
    if not len(t1):
        print('FAIL: filament 2 extrudes nothing')
        sys.exit(1)
    # the logo's footprint on the plate: the inlay STLs are in the part's print frame, the part's min corner at p.mesh.bounds[0]
    lo = p.mesh.bounds[0]
    boxes = []
    for nm, m in p.inlays:
        b = np.array(m.bounds)
        boxes.append((nm, b[0][:2] + lo[:2], b[1][:2] + lo[:2], float(b[1][2])))
    inside = np.zeros(len(t1), dtype=bool)
    for nm, a0, a1, h in boxes:
        inside |= (t1[:, 0] >= a0[0] - 0.3) & (t1[:, 0] <= a1[0] + 0.3) & (t1[:, 1] >= a0[1] - 0.3) & (t1[:, 1] <= a1[1] + 0.3)
    print(f'filament 2: {len(t1)} extrusion moves, {int(inside.sum())} inside the two logo boxes, layers z {t1[:, 2].min():.2f}..{t1[:, 2].max():.2f} '
          f'(the inlays are {max(b[3] for b in boxes):.2f} deep); filament 1 moves {len(pts[0])}')
    for nm, a0, a1, h in boxes:
        print(f'   {nm.split(":")[0]}: box x {a0[0]:.1f}..{a1[0]:.1f}, y {a0[1]:.1f}..{a1[1]:.1f}, {h:.2f} deep')
    ok = int(inside.sum()) == len(t1) and t1[:, 2].max() <= max(b[3] for b in boxes) + 0.25
    print('ON switch:', 'OK (filament 2 only in the logo, only in its own layers)' if ok else 'CHECK: filament 2 outside the logo boxes')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
