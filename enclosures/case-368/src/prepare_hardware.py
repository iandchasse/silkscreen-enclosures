"""Derive enclosure reference data from the Silkscreen PCB.

Reads hardware/board-2026-09-21/silkscreen_pcb.kicad_pcb, a copy of Ian's working
the silkscreen-pcb repo's silkscreen_pcb.kicad_pcb taken 2026-09-21 (the revision that adds H6 and
moves H5), with its CERN-OHL-S LICENSE and NOTICE. The Rev D-G board (hardware/frozen/ until 2026-09-28, now in
git history) has the same outline, so the CAD frame below still holds. The ${KIPRJMOD} 3D-model paths resolve to
a silkscreen-pcb checkout, ORIGINAL_PROJECT (set the SILKSCREEN_PCB_DIR environment variable to its folder).

Writes, all under hardware/:

  silkscreen_pcb-portable.kicad_pcb  ${KIPRJMOD} model paths made absolute (read-only use of originals)
  board.step                         KiCad STEP export, CAD frame below
  footprints.json                    every footprint: ref, value, position, rotation, side, DNP, pads
  outline.json                       Edge.Cuts primitives in the CAD frame

CAD frame (same as the earlier handoff, so old and new data compare directly):
  X = KiCad X - 44.24,  Y = 148.25 - KiCad Y,  Z = 0 at PCB rear face, +Z toward the screen.
"""
import json, os, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HW = ROOT / 'hardware'
BOARD_PCB = HW / 'board-2026-09-21' / 'silkscreen_pcb.kicad_pcb'   # the board this case is built around
ORIGINAL_PROJECT = Path(os.environ.get('SILKSCREEN_PCB_DIR') or (ROOT.parents[2] / 'silkscreen-pcb'))  # a silkscreen-pcb checkout
KICAD_CLI = Path(r'C:\Program Files\KiCad\9.0\bin\kicad-cli.exe')
OX, OY = 44.24, 148.25


def cad(x, y):
    return [round(x - OX, 6), round(OY - y, 6)]


# ---- minimal s-expression parser --------------------------------------------------------
TOKEN = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+')


def parse(text):
    stack, cur = [], []
    for m in TOKEN.finditer(text):
        t = m.group(0)
        if t == '(':
            stack.append(cur)
            cur = []
        elif t == ')':
            done = cur
            cur = stack.pop()
            cur.append(done)
        else:
            cur.append(t[1:-1] if t.startswith('"') else t)
    return cur[0]


def find(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def first(node, key, default=None):
    f = find(node, key)
    return f[0] if f else default


def main():
    text = BOARD_PCB.read_text(encoding='utf-8')
    portable = text.replace('${KIPRJMOD}', ORIGINAL_PROJECT.as_posix())
    port_path = HW / 'silkscreen_pcb-portable.kicad_pcb'
    port_path.write_text(portable, encoding='utf-8')

    tree = parse(text)
    thickness = float(first(first(tree, 'general'), 'thickness')[1])

    fps = []
    for fp in find(tree, 'footprint'):
        at = first(fp, 'at')
        x, y = float(at[1]), float(at[2])
        rot = float(at[3]) if len(at) > 3 else 0.0
        props = {p[1]: p[2] for p in find(fp, 'property') if len(p) > 2}
        attr = first(fp, 'attr', [])
        pads = []
        for pad in find(fp, 'pad'):
            pat = first(pad, 'at')
            size = first(pad, 'size')
            drill = first(pad, 'drill')
            pads.append({'name': pad[1], 'type': pad[2], 'shape': pad[3],
                         'local': [float(pat[1]), float(pat[2])], 'rot': float(pat[3]) if len(pat) > 3 else 0.0,
                         'size': [float(size[1]), float(size[2])] if size else None,
                         'drill': [v for v in drill[1:] if not isinstance(v, list)] if drill else None})
        fps.append({'ref': props.get('Reference', '?'), 'value': props.get('Value', ''), 'footprint': fp[1],
                    'layer': first(fp, 'layer')[1], 'kicad': [x, y], 'cad': cad(x, y), 'rot': rot,
                    'attr': attr[1:] if attr else [], 'dnp': 'dnp' in (attr[1:] if attr else []),
                    'models': [m[1] for m in find(fp, 'model')], 'pads': pads})
    (HW / 'footprints.json').write_text(json.dumps({'boardThickness': thickness, 'footprints': fps}, indent=1))

    edges = []
    for kind in ('gr_line', 'gr_arc', 'gr_circle', 'gr_rect'):
        for g in find(tree, kind):
            if first(g, 'layer')[1] != 'Edge.Cuts':
                continue
            pts = {k: cad(float(first(g, k)[1]), float(first(g, k)[2])) for k in ('start', 'mid', 'end', 'center')
                   if first(g, k)}
            edges.append({'kind': kind, **pts})
    (HW / 'outline.json').write_text(json.dumps(edges, indent=1))
    print(f'{len(fps)} footprints, {len(edges)} Edge.Cuts primitives, board thickness {thickness}')

    if '--no-step' not in sys.argv:
        out = HW / 'board.step'
        cmd = [str(KICAD_CLI), 'pcb', 'export', 'step', '--force', '--subst-models', '--no-dnp',
               '--user-origin', f'{OX}x{OY}mm', '-o', str(out), str(port_path)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        (HW / 'step-export.log').write_text(r.stdout + r.stderr)
        print('STEP export', 'OK' if r.returncode == 0 else f'FAILED ({r.returncode})', out.stat().st_size if out.exists() else '')


if __name__ == '__main__':
    main()
