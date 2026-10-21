"""Silkscreen logos (copied from the website's logo assets into hardware/logo/) as printable
outlines: the wordmark for the chin engraving, the book icon for the back.

A small SVG path reader (M L H V C S Q T Z, absolute and relative; translate/scale/matrix/rotate
transforms; circles and rects) flattens the curves; each path is filled even-odd. For the
wordmark the shapes are unioned. For the icon (cfg['painter']) they are composited in document
order like a renderer does: black adds, white cuts away, so the white page faces and the black
page lines drawn over them come out as drawn. Features narrower than cfg['min_feature'] are
removed with a morphological opening, because a gap that narrow cannot print in the first
layers of a face-down part.
"""
import re
import math
import numpy as np
import shapely.geometry as sg
import shapely.ops as so
import shapely.affinity as sa
import cadquery as cq
import hw
import params as P

NUM = re.compile(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?')


def _tf(s):
    """SVG transform attribute -> 3x3 matrix."""
    m = np.eye(3)
    for name, args in re.findall(r'(\w+)\s*\(([^)]*)\)', s or ''):
        a = [float(x) for x in NUM.findall(args)]
        if name == 'translate':
            t = np.array([[1, 0, a[0]], [0, 1, a[1] if len(a) > 1 else 0], [0, 0, 1]])
        elif name == 'scale':
            t = np.diag([a[0], a[1] if len(a) > 1 else a[0], 1])
        elif name == 'matrix':
            t = np.array([[a[0], a[2], a[4]], [a[1], a[3], a[5]], [0, 0, 1]])
        elif name == 'rotate':
            c, s = math.cos(math.radians(a[0])), math.sin(math.radians(a[0]))
            t = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
            if len(a) == 3:                                  # rotate(angle, cx, cy)
                t = np.array([[1, 0, a[1]], [0, 1, a[2]], [0, 0, 1]]) @ t @ np.array([[1, 0, -a[1]], [0, 1, -a[2]], [0, 0, 1]])
        else:
            continue
        m = m @ t
    return m


def _flatten(d, seg=14):
    """Path data -> list of closed point lists (SVG units)."""
    toks = re.findall(r'[MmLlHhVvCcSsQqTtZzAa]|' + NUM.pattern, d)
    subs, cur, start = [], [], (0.0, 0.0)
    x = y = 0.0
    cmd, i, last_c = None, 0, None

    def take(n):
        nonlocal i
        vals = [float(v) for v in toks[i:i + n]]
        i += n
        return vals

    def bez(p0, p1, p2, p3):
        for k in range(1, seg + 1):
            t = k / seg
            mt = 1 - t
            cur.append((mt ** 3 * p0[0] + 3 * mt * mt * t * p1[0] + 3 * mt * t * t * p2[0] + t ** 3 * p3[0],
                        mt ** 3 * p0[1] + 3 * mt * mt * t * p1[1] + 3 * mt * t * t * p2[1] + t ** 3 * p3[1]))

    while i < len(toks):
        if re.match(r'[A-Za-z]', toks[i]):
            cmd = toks[i]
            i += 1
            if cmd in 'Zz':
                if cur:
                    subs.append(cur)
                cur, (x, y), last_c = [], start, None
                continue
        rel = cmd.islower()
        c = cmd.upper()
        if c == 'M':
            px, py = take(2)
            x, y = (x + px, y + py) if rel else (px, py)
            if cur:
                subs.append(cur)
            cur, start = [(x, y)], (x, y)
            cmd = 'l' if rel else 'L'
            last_c = None
        elif c == 'L':
            px, py = take(2)
            x, y = (x + px, y + py) if rel else (px, py)
            cur.append((x, y)); last_c = None
        elif c == 'H':
            (px,) = take(1)
            x = x + px if rel else px
            cur.append((x, y)); last_c = None
        elif c == 'V':
            (py,) = take(1)
            y = y + py if rel else py
            cur.append((x, y)); last_c = None
        elif c in 'CS':
            if c == 'C':
                a = take(6)
                p1 = (x + a[0], y + a[1]) if rel else (a[0], a[1])
                p2 = (x + a[2], y + a[3]) if rel else (a[2], a[3])
                p3 = (x + a[4], y + a[5]) if rel else (a[4], a[5])
            else:
                a = take(4)
                p1 = (2 * x - last_c[0], 2 * y - last_c[1]) if last_c else (x, y)
                p2 = (x + a[0], y + a[1]) if rel else (a[0], a[1])
                p3 = (x + a[2], y + a[3]) if rel else (a[2], a[3])
            bez((x, y), p1, p2, p3)
            last_c, (x, y) = p2, p3
        elif c in 'QT':
            if c == 'Q':
                a = take(4)
                q = (x + a[0], y + a[1]) if rel else (a[0], a[1])
                p3 = (x + a[2], y + a[3]) if rel else (a[2], a[3])
            else:
                a = take(2)
                q = (2 * x - last_c[0], 2 * y - last_c[1]) if last_c else (x, y)
                p3 = (x + a[0], y + a[1]) if rel else (a[0], a[1])
            bez((x, y), (x + 2 / 3 * (q[0] - x), y + 2 / 3 * (q[1] - y)),
                (p3[0] + 2 / 3 * (q[0] - p3[0]), p3[1] + 2 / 3 * (q[1] - p3[1])), p3)
            last_c, (x, y) = q, p3
        elif c == 'A':
            a = take(7)                          # arcs: straight chord is enough for this logo
            x, y = (x + a[5], y + a[6]) if rel else (a[5], a[6])
            cur.append((x, y)); last_c = None
        else:
            raise ValueError('unsupported path command ' + cmd)
    if cur:
        subs.append(cur)
    return [s for s in subs if len(s) >= 3]


WHITE = ('#fff', '#ffffff', 'white')


def outline(path=None, painter=False):
    """Logo as a shapely geometry in SVG units (y down), plus the viewBox. With painter=True the
    shapes are composited in document order (black adds, white cuts away) instead of unioned."""
    src = (hw.ROOT / (path or P.LOGO['svg'])).read_text(encoding='utf-8')
    vb = [float(v) for v in NUM.findall(re.search(r'viewBox="([^"]+)"', src).group(1))]
    shapes, ink = [], None
    stack = [(np.eye(3), '#000')]                            # transform and inherited fill
    for m in re.finditer(r'<(/?)(g|path|circle|rect)\b([^>]*?)(/?)>', src):
        closing, tag, attrs, selfclose = m.groups()
        fa = re.search(r'\bfill="([^"]+)"', attrs)
        if tag == 'g':
            if closing:
                stack.pop()
            elif not selfclose:
                t = re.search(r'transform="([^"]+)"', attrs)
                stack.append((stack[-1][0] @ _tf(t.group(1) if t else ''), fa.group(1) if fa else stack[-1][1]))
            continue
        tm = stack[-1][0] @ _tf((re.search(r'transform="([^"]+)"', attrs) or [None, ''])[1])
        fill = (fa.group(1) if fa else stack[-1][1]).lower()
        if tag == 'circle':
            cx, cy, r = (float(re.search(fr'\b{k}="([^"]+)"', attrs).group(1)) for k in ('cx', 'cy', 'r'))
            rings = [[(cx + r * math.cos(a), cy + r * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 64, endpoint=False)]]
        elif tag == 'rect':
            x, y, w, h = (float(re.search(fr'\b{k}="([^"]+)"', attrs).group(1)) for k in ('x', 'y', 'width', 'height'))
            rings = [[(x, y), (x + w, y), (x + w, y + h), (x, y + h)]]
        else:
            rings = _flatten(re.search(r'\bd="([^"]+)"', attrs).group(1))
        geom = None
        for ring in rings:
            pts = np.array(ring)
            pts = (tm @ np.column_stack([pts, np.ones(len(pts))]).T).T[:, :2]
            p = sg.Polygon(pts).buffer(0)
            if p.is_empty:
                continue
            geom = p if geom is None else geom.symmetric_difference(p)
        if geom is None or geom.is_empty:
            continue
        if not painter:
            shapes.append(geom)
        elif fill in WHITE:
            ink = ink.difference(geom) if ink is not None else None
        elif fill != 'none':
            ink = geom if ink is None else ink.union(geom)
    return (ink if painter else so.unary_union(shapes)), vb


def placed(cfg=None):
    """Logo in CAD XY (mm), sized and centred per params.LOGO, thin features removed.
    With cfg['part'] == 'wordmark' only the lettering is used (the icon sits right of x=2990)."""
    cfg = cfg or P.LOGO
    g, vb = outline(cfg['svg'], painter=cfg.get('painter', False))
    if cfg.get('part') == 'wordmark':
        g = so.unary_union([p for p in getattr(g, 'geoms', [g]) if p.bounds[2] < 2990])
    elif cfg.get('part') == 'icon':
        g = so.unary_union([p for p in getattr(g, 'geoms', [g]) if p.bounds[0] >= 2990])
    s = cfg['width'] / (g.bounds[2] - g.bounds[0])
    # SVG y runs down; a logo on the back is seen from -Z, so it is mirrored in X to read right
    g = sa.scale(g, xfact=-s if cfg.get('mirror') else s, yfact=-s, origin=(0, 0))
    minx, miny, maxx, maxy = g.bounds
    g = sa.translate(g, cfg['x'] - (minx + maxx) / 2, cfg['y'] - (miny + maxy) / 2)
    r = cfg['min_feature'] / 2
    if cfg.get('bold'):                  # line art: thicken it so its main strokes clear the filter
        g = g.buffer(cfg['bold'], join_style=1)
    g = g.buffer(-r, join_style=2).buffer(r, join_style=2).buffer(0)
    if cfg.get('bold'):                  # and close any white gap left too thin to print
        g = g.buffer(r, join_style=1).buffer(-r, join_style=1).buffer(0)
    return g.simplify(0.01)


def solid(z0, z1, cfg=None):
    """Prism of the placed logo between z0 and z1 (a cutter for the engraving)."""
    g = placed(cfg)
    faces = []
    for p in getattr(g, 'geoms', [g]):
        if p.area < 0.02:
            continue
        outer = cq.Wire.makePolygon([cq.Vector(x, y, z0) for x, y in p.exterior.coords[:-1]], close=True)
        inner = [cq.Wire.makePolygon([cq.Vector(x, y, z0) for x, y in r.coords[:-1]], close=True) for r in p.interiors]
        faces.append(cq.Face.makeFromWires(outer, inner))
    prisms = [cq.Solid.extrudeLinear(f, cq.Vector(0, 0, z1 - z0)) for f in faces]
    return cq.Workplane(obj=cq.Compound.makeCompound(prisms))


if __name__ == '__main__':
    g = placed()
    print('logo polygons', len(getattr(g, 'geoms', [g])), 'bounds', [round(v, 2) for v in g.bounds], 'area', round(g.area, 1))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(12, 3))
    for p in getattr(g, 'geoms', [g]):
        ax.fill(*p.exterior.xy, color='k')
        for r in p.interiors:
            ax.fill(*r.xy, color='w')
    ax.set_aspect('equal')
    fig.savefig(hw.ROOT / 'out' / 'logo-check.png', dpi=120)
