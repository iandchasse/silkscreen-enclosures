"""Standard review renders of the current build (out/*.stl) into out/shots/.

Run from this project's folder (enclosures/case-426) with the original project's venv (README.md, "Build"):

    python -B src/review.py [name ...]
"""
import subprocess, sys
from pathlib import Path
import hw
import params as P

ROOT = hw.ROOT
OUT = P.OUT
SHOTS = OUT / 'shots'
SHOTS.mkdir(parents=True, exist_ok=True)
PY = sys.executable

C = {'tub': '#e8e1d0', 'lid': '#cfc5ae', 'midplate': '#7d8a7f', 'key_SW9': '#c8553d', 'key_SW8': '#3d3f45',
     'key_SW3': '#3d3f45', 'key_SW2': '#3d3f45', 'board': '#3a7d44', 'ref_display': '#2b2b2b', 'ref_battery': '#8fa6c9'}
KEYS = ['key_SW9', 'key_SW8', 'key_SW3', 'key_SW2'] if P.BOTTOM_KEYS else []   # chinless: no bottom keys
CASE = ['tub', 'lid', 'midplate'] + KEYS
HWREF = ['board', 'ref_display', 'ref_battery']


def path(n):
    return hw.HW / 'board.stl' if n == 'board' else OUT / f'{n}.stl'


def shot(name, view, parts, clip=(), focus=None, ortho=False, size='1400x1000', opacity=None):
    cmd = [PY, str(ROOT / 'src' / 'render.py'), '--out', str(SHOTS / f'{name}.png'), '--view', view, '--size', size, '--parts']
    for p in parts:
        op = (opacity or {}).get(p, 1.0)
        cmd.append(f'{path(p)}:{C.get(p, "#bbbbbb")}:{op}')
    for c in clip:
        cmd += ['--clip', c]
    if focus:
        cmd.append(f'--focus={focus}')
    if ortho:
        cmd.append('--ortho')
    subprocess.run(cmd, check=True, capture_output=True)
    print('shot', name)


def main(which):
    kx = hw.switch_plunger('SW8')['face'][0]
    if 'all' in which or 'ext' in which:
        shot('a-front', 'iso_front', CASE + HWREF)
        shot('a-back', 'iso_back', CASE + HWREF)
        shot('a-right', 'iso_front_r', CASE + HWREF, focus='40,64,20,110,-7,7')
        shot('a-bottom', 'iso_bottom', CASE + HWREF, focus='-3,64,-9,20,-7,7')
    if 'all' in which or 'sec' in which:
        shot('s-key', 'right', CASE + HWREF, clip=[f'x:{kx}:flip'], focus=f'{kx},{kx + 1},-9,8,-7,8',
             ortho=True, size='1600x1100')
        u = 41.3
        shot('s-usb', 'bottom', CASE + HWREF, clip=[f'y:{u}'], focus=f'50,64,{u},{u + 1},-7,7', ortho=True, size='1600x1000')
        shot('s-sw10', 'bottom', CASE + HWREF, clip=['y:93.5'], focus='52,64,93.5,94.5,-7,7', ortho=True, size='1600x1000')
        shot('s-stack', 'bottom', CASE + HWREF, clip=['y:60'], focus='-4,12,60,61,-7,7', ortho=True, size='1600x1000')
        shot('s-top', 'right', CASE + HWREF, clip=['x:40:flip'], focus='40,41,100,116,-7,7', ortho=True, size='1600x1000')
    if 'all' in which or 'parts' in which:
        shot('p-tub-inside', 'iso_back', ['tub'])
        shot('p-lid-inside', 'iso_front', ['lid'])
        shot('p-midplate', 'iso_front', ['midplate'])
        if KEYS:
            shot('p-key', 'iso_front_r', ['key_SW8'])




def exploded():
    """Translated copies of every part along Z, rendered as an exploded stack."""
    import trimesh
    tmp = SHOTS / 'tmp'
    tmp.mkdir(exist_ok=True)
    offsets = {'tub': 16, 'key_SW9': 26, 'key_SW8': 26, 'key_SW3': 26, 'key_SW2': 26, 'ref_display': 6,
               'midplate': -2, 'board': -12, 'ref_battery': -24, 'lid': -36}
    parts = []
    for n, dz in offsets.items():
        if n.startswith('key_') and n not in KEYS:
            continue
        m = trimesh.load(path(n))
        m.apply_translation([0, 0, dz])
        m.export(tmp / f'{n}.stl')
        parts.append(f'{tmp / (n + ".stl")}:{C.get(n, "#bbbbbb")}:1.0')
    cmd = [PY, str(ROOT / 'src' / 'render.py'), '--out', str(SHOTS / 'a-exploded.png'), '--view', 'iso_front',
           '--size', '1400x1400', '--parts', *parts]
    subprocess.run(cmd, check=True, capture_output=True)
    print('shot a-exploded')


if __name__ == '__main__':
    args = sys.argv[1:] or ['all']
    main(args)
    if 'all' in args or 'exploded' in args:
        exploded()
