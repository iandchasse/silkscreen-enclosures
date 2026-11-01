"""Does the print frame need supports? A layer-by-layer overhang audit of the cover and coupon STLs in print/ (plate face down),
from the mesh alone; the G-code read-back (slice_read.py) is the proof, this is the cheap pre-check.

For every layer (sliced at its mid-plane, 0.2 mm layers) the part of the layer that lies farther than REACH from the layer
below counts as unsupported area; REACH is 0.30 mm (a layer's line is 0.42 wide: it can hang out about 0.3 over air without
drooping; the 47-degree lip face steps out only 0.19 a layer).

    python -B printcheck.py            all the cover and coupon STLs
"""
import sys
from pathlib import Path

import numpy as np
import shapely
import trimesh

HERE = Path(__file__).resolve().parent
PRINT = HERE.parent.parent / 'print' / 'cover'
LAYER = 0.2
REACH = 0.30
HANG = 0.45                         # mm: the most a layer may hang past the one below it


def layer_shapes(m, layer=LAYER):
    top = m.bounds[1][2]
    n = int(round(top / layer))
    out = []
    for k in range(n):
        z = (k + 0.5) * layer
        s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        g = shapely.Polygon()
        if s is not None:
            for p in s.discrete:
                if len(p) >= 4:
                    g = g.symmetric_difference(shapely.Polygon(p[:, :2]).buffer(0))
        out.append(g)
    return out


def audit(path):
    """Per layer: how far the layer hangs past the layer below at its worst (mm, over air), and the area of what is farther
    than REACH. A layer passes when nothing hangs more than HANG (0.45 mm: a flat of 0.26 plus a 47-degree step of 0.19; the
    engraved label's strokes are allowed 0.75 in its first three layers: they bridge 1.5 mm at most)."""
    m = trimesh.load(path, force='mesh')
    layers = layer_shapes(m)
    worst = (0.0, None)
    bad = []
    for k in range(1, len(layers)):
        a, b = layers[k], layers[k - 1]
        if a.is_empty:
            continue
        un = a.difference(b.buffer(REACH)) if not b.is_empty else a
        if un.is_empty or un.area < 1e-6:
            continue
        pts = []
        for g in (un.geoms if hasattr(un, 'geoms') else [un]):
            if g.area > 1e-4:
                pts += list(g.exterior.coords)
        hang = max((shapely.Point(p).distance(b) for p in pts), default=0.0) if not b.is_empty else 99.0
        limit = 0.75 if k <= 3 else HANG
        if hang > worst[0]:
            worst = (hang, k)
        if hang > limit:
            bad.append((k, round(hang, 2), round(un.area, 2)))
    first = layers[0].area if layers else 0.0
    return dict(file=path.name, layers=len(layers), height=float(m.bounds[1][2]), first_layer_mm2=round(first, 1),
                worst_hang_mm=round(worst[0], 2), worst_layer=worst[1], layers_over=bad[:8], n_over=len(bad), ok=not bad)


if __name__ == '__main__':
    files = [*sorted((PRINT / '4.26').glob('cover-*.stl')), *sorted((PRINT / '3.68').glob('cover-*.stl'))]
    bad = 0
    for f in files:
        r = audit(f)
        print(f"{r['file']:24s} {r['layers']:3d} layers, first layer {r['first_layer_mm2']:7.1f} mm2, worst overhang "
              f"{r['worst_hang_mm']:.2f} mm (layer {r['worst_layer']})  {'ok' if r['ok'] else 'OVER: ' + str(r['layers_over'])}")
        bad += not r['ok']
    sys.exit(1 if bad else 0)
