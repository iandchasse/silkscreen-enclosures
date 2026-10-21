"""Small CadQuery helpers. All sizes in mm, CAD frame."""
import math
import cadquery as cq


def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane('XY').box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def rbox(x0, x1, y0, y1, z0, z1, r):
    """Box with its vertical (Z) edges rounded."""
    b = box(x0, x1, y0, y1, z0, z1)
    return b.edges('|Z').fillet(r) if r > 0 else b


def zcyl(x, y, z0, z1, d):
    return cq.Workplane('XY').circle(d / 2).extrude(z1 - z0).translate((x, y, z0))


def xcyl(x0, x1, y, z, d):
    return cq.Workplane('YZ').circle(d / 2).extrude(x1 - x0).translate((x0, y, z))


def yz_prism(points, x0, x1):
    """Extrude a closed (y, z) polyline along +X from x0 to x1."""
    return cq.Workplane('YZ').polyline(points).close().extrude(x1 - x0).translate((x0, 0, 0))


def xz_prism(points, y0, y1):
    """Extrude a closed (x, z) polyline along +Y from y0 to y1."""
    # CadQuery's XZ workplane normal is -Y, so extrude negative and shift.
    return cq.Workplane('XZ').polyline(points).close().extrude(-(y1 - y0)).translate((0, y0, 0))


def stadium_x(x0, x1, yc, zc, w, h):
    """Rounded-end slot (USB-C shape) running along X, width w (Y) and height h (Z)."""
    r = min(w, h) / 2
    s = cq.Sketch().rect(w, h).vertices().fillet(r - 1e-3)
    return cq.Workplane('YZ').placeSketch(s).extrude(x1 - x0).translate((x0, yc, zc))


def rrect_x(x0, x1, yc, zc, w, h, r):
    s = cq.Sketch().rect(w, h).vertices().fillet(r)
    return cq.Workplane('YZ').placeSketch(s).extrude(x1 - x0).translate((x0, yc, zc))


def union_all(items):
    items = [i for i in items if i is not None]
    out = items[0]
    for it in items[1:]:
        out = out.union(it)
    return out


def cut_all(base, items):
    for it in items:
        if it is not None:
            base = base.cut(it)
    return base


def solid_count(wp):
    return len(wp.solids().vals())
