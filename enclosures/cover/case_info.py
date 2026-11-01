"""What the slide cover needs to know about a case, read from the case projects themselves (never typed in twice).

The numbers come from two places: the case's params.py (its envelope, rounds and corner radius), imported at run time
in a subprocess with SILKSCREEN_VARIANT set to the configuration (params.py reads that variable when it is imported,
and the 4.26's and the 3.68's modules share names, so each gets a process of its own), and the built STLs in
out/<slug>/ (the bottom-key caps and the side keys, as built). Nothing under case-426/src or case-368/src is touched.

    info('case-426', 'standard') -> dict   (cached in cover/out/case_info.json; delete it to re-read)
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
ENC = HERE.parent
OUT = HERE / 'out'
CACHE = OUT / 'case_info.json'

PARAMS = ('X0', 'X1', 'Y0', 'Y1', 'Z_FRONT', 'Z_BACK', 'CORNER_R', 'FRONT_EDGE_R', 'BACK_EDGE_R', 'TAB_PAD_PROUD')
_READER = r'''
import os, sys, json
case, slug, names = sys.argv[1], sys.argv[2], sys.argv[3].split(',')
os.environ['SILKSCREEN_VARIANT'] = slug
root = sys.argv[4]
sys.path.insert(0, root + '/' + case + '/src')
os.chdir(root + '/' + case)
import params as P
print(json.dumps({n: getattr(P, n) for n in names}))
'''


def read_params(case, slug):
    r = subprocess.run([sys.executable, '-X', 'utf8', '-B', '-c', _READER, case, slug, ','.join(PARAMS), str(ENC)],
                       capture_output=True, text=True, timeout=300)
    if r.returncode:
        raise SystemExit(f'{case} {slug}: params import failed:\n{r.stderr[-1500:]}')
    d = json.loads(r.stdout.strip().splitlines()[-1])
    return {k: round(float(v), 6) for k, v in d.items()}


def mesh(case, slug, name):
    return trimesh.load(ENC / case / 'out' / slug / f'{name}.stl', force='mesh')


def caps(case, slug, zf):
    """The bottom keys' caps as built: [(x0, x1, y0, y1, ztop)] of the part of each key_SW*.stl that stands over the
    face (a section 0.5 over it); [] with no bottom keys."""
    out = []
    for f in sorted((ENC / case / 'out' / slug).glob('key_SW*.stl')):
        m = trimesh.load(f, force='mesh')
        s = m.section(plane_origin=[0, 0, zf + 0.5], plane_normal=[0, 0, 1])
        if s is None:
            continue
        v = np.vstack(s.discrete)
        out.append([float(v[:, 0].min()), float(v[:, 0].max()), float(v[:, 1].min()), float(v[:, 1].max()),
                    float(m.bounds[1][2])])
    return sorted(out)


def side_keys(case, slug):
    """{ref: (x0, x1, y0, y1)} of every side key of the build (skey_*.stl: bar, block, pad and nub)."""
    out = {}
    for f in sorted((ENC / case / 'out' / slug).glob('skey_*.stl')):
        b = trimesh.load(f, force='mesh').bounds
        out[f.stem[5:]] = (float(b[0][0]), float(b[1][0]), float(b[0][1]), float(b[1][1]))
    return out


def window(case, slug, zf):
    """The screen window's box on the face, [x0, x1, y0, y1]: where the tub's front face is sunk more than 0.3 below the face
    (a vtk ray from above on a 0.25 grid; the bottom-key openings, at y < 5, are left out)."""
    sys.path.insert(0, str(HERE))
    import raycast
    m = mesh(case, slug, 'tub')
    c = raycast.Caster(m)
    b = m.bounds
    xs = np.arange(b[0][0] + 2.4, b[1][0] - 2.4, 0.25)      # inside the front round (R1.8) all round
    ys = np.arange(5.0, b[1][1] - 2.4, 0.25)
    hit = []
    for y in ys:
        for x in xs:
            h = c.first_hit([x, y, zf + 5], [x, y, zf - 8])
            if h is not None and h[2] < zf - 0.3:
                hit.append((x, y))
    h = np.array(hit)
    return [float(h[:, 0].min()), float(h[:, 0].max()), float(h[:, 1].min()), float(h[:, 1].max())]


def usb(case, slug, p):
    """The USB-C recess on the +X side as [y0, y1, z0, z1]: where the side face is sunk more than 1.5 (a vtk ray along -x on a
    0.25 grid; the recess floor is 2.8 in, a side key's nub window less)."""
    sys.path.insert(0, str(HERE))
    import raycast
    ms = [mesh(case, slug, n) for n in ('tub', 'lid')]
    c = raycast.Caster(trimesh.util.concatenate(ms))
    hit = []
    for y in np.arange(15, 49, 0.25):                         # below the first right side key (y 49.5)
        for z in np.arange(p['Z_BACK'] + 2.2, p['Z_FRONT'] - 1.8, 0.25):
            h = c.first_hit([p['X1'] + 4, y, z], [p['X1'] - 6, y, z])
            if h is not None and h[0] < p['X1'] - 1.5:
                hit.append((y, z))
    h = np.array(hit)
    return [float(h[:, 0].min()), float(h[:, 0].max()), float(h[:, 1].min()), float(h[:, 1].max())]


def info(case, slug, refresh=False):
    OUT.mkdir(exist_ok=True)
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    key = f'{case}/{slug}'
    if key in cache and not refresh and all(k in cache[key] for k in ('caps', 'side_keys', 'window', 'usb')):
        return cache[key]
    p = read_params(case, slug)
    d = dict(case=case, slug=slug, **p)
    d['caps'] = caps(case, slug, p['Z_FRONT'])
    d['side_keys'] = side_keys(case, slug)
    d['window'] = window(case, slug, p['Z_FRONT'])
    d['usb'] = usb(case, slug, p)
    cache[key] = d
    CACHE.write_text(json.dumps(cache, indent=1, sort_keys=True))
    return d


if __name__ == '__main__':
    for c, s in (('case-426', 'standard'), ('case-426', 'chinless'), ('case-368', 'standard')):
        print(json.dumps(info(c, s, refresh=True), indent=1))
