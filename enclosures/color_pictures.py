"""The two pictures of the colour options (docs/images/color-front-lines.png, color-side-keys.png): vtk renders of the built 4.26
standard parts (offscreen, no GUI window), through cover/render.py. Nothing was printed: they show the CAD.

    python -B color_pictures.py

color-front-lines.png: the tub's front chin with the three lines switched to Negative Volume (the tub less the three bodies).
color-side-keys.png: the lid seen from the front, grey below the colour box's height and orange above it (what filament 2 prints).
"""
import sys
from pathlib import Path

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'cover'))
import render           # noqa: E402
import color_options as CO     # noqa: E402

IMG = HERE.parent / 'docs' / 'images'
D = HERE / 'case-426' / 'out' / 'standard'
CASE = (0.90, 0.91, 0.93)
LID = (0.80, 0.83, 0.88)
INK = (0.98, 0.58, 0.20)


def front_lines():
    tub = trimesh.load(D / 'tub.stl', force='mesh')
    ptub = trimesh.load(D / 'print' / 'tub.stl', force='mesh')
    lines = trimesh.load(CO.LINE_FILES['case-426'], force='mesh')
    # the print frame -> the CAD frame: the tub prints turned over about X, then moved to its min corner
    v = np.array(lines.vertices)
    v = np.c_[v[:, 0] + tub.bounds[0][0], tub.bounds[1][1] - v[:, 1], tub.bounds[1][2] - v[:, 2]]
    cad = trimesh.Trimesh(v, lines.faces, process=False)
    cad.invert() if cad.volume < 0 else None
    # nudge the cutters 0.01 past the face so the cut is clean
    cut = trimesh.boolean.difference([tub, cad], engine='manifold')
    assert abs(tub.bounds[1][2] - ptub.extents[2] - tub.bounds[0][2]) < 1e-3
    zf = tub.bounds[1][2]
    cx, cy = (tub.bounds[0][0] + tub.bounds[1][0]) / 2, 8.0
    d = np.array([0.0, -0.55, 0.83])
    render.render([(cut, CASE, 1.0)], IMG / 'color-front-lines.png', position=np.array([cx, cy, zf]) + d * 120, focal=(cx, cy, zf),
                  up=(0, 1, 0), size=(1600, 1000), parallel_scale=26)


def side_keys():
    lid = trimesh.load(D / 'lid.stl', force='mesh')
    top = CO.wall_top(D)
    z0 = CO.split_layer(top) + lid.bounds[0][2]
    big = [[-20, -30, z0], [90, 150, z0 + 20]]
    above = trimesh.boolean.intersection([lid, trimesh.creation.box(bounds=big)], engine='manifold')
    big = [[-20, -30, z0 - 20], [90, 150, z0]]
    below = trimesh.boolean.intersection([lid, trimesh.creation.box(bounds=big)], engine='manifold')
    cx, cy = (lid.bounds[0][0] + lid.bounds[1][0]) / 2, (lid.bounds[0][1] + lid.bounds[1][1]) / 2
    d = np.array([0.45, -0.75, 0.9])
    render.render([(below, LID, 1.0), (above, INK, 1.0)], IMG / 'color-side-keys.png', position=np.array([cx, cy, 0.0]) + d * 260,
                  focal=(cx, cy, z0), up=(0, 1, 0), size=(1600, 1000), parallel_scale=68)


if __name__ == '__main__':
    IMG.mkdir(parents=True, exist_ok=True)
    front_lines()
    side_keys()
    print('wrote', IMG / 'color-front-lines.png', IMG / 'color-side-keys.png')
