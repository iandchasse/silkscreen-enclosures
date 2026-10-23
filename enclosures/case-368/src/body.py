"""Outer body shared by the front tub and the back lid, plus the side-feature layout."""
import cadquery as cq
import hw
import params as P
from geom import box, rbox


def outer_body():
    """Full closed envelope: rounded plan corners, rounded front and back edges."""
    b = rbox(P.X0, P.X1, P.Y0, P.Y1, P.Z_BACK, P.Z_FRONT, P.CORNER_R)
    b = b.faces('>Z').edges().fillet(P.FRONT_EDGE_R)
    b = b.faces('<Z').edges().fillet(P.BACK_EDGE_R)
    return b


def inner_limit(z0, z1, wall=1.0):
    """No cavity may come closer than `wall` to the outer surface in plan."""
    return rbox(P.X0 + wall, P.X1 - wall, P.Y0 + wall, P.Y1 - wall, z0, z1, P.CORNER_R - wall)


def _outline_sketch(inset):
    return cq.Sketch().rect(P.X1 - P.X0 - 2 * inset, P.Y1 - P.Y0 - 2 * inset).vertices().fillet(P.CORNER_R - inset)


def seam_chamfer(upper):
    """Cutter for a 45-degree chamfer on the outer edge at the parting plane, on the tub
    (upper=True) or the lid side. Together they form a small V that makes the parting line
    deliberate and hides a tenth of misalignment. None when params.SEAM_CHAMFER is 0 (since 2026-10-23 both halves
    are square at the parting line)."""
    c = P.SEAM_CHAMFER
    if c <= 0:
        return None
    e = 0.02                                   # the frustum overruns the slab so no sliver is left
    cx, cy = (P.X0 + P.X1) / 2, (P.Y0 + P.Y1) / 2
    if upper:
        ring = rbox(P.X0 - 2, P.X1 + 2, P.Y0 - 2, P.Y1 + 2, P.SEAM - 0.01, P.SEAM + c, P.CORNER_R + 2)
        z0, lo, hi = P.SEAM - e, _outline_sketch(c + e), _outline_sketch(-e)
    else:
        ring = rbox(P.X0 - 2, P.X1 + 2, P.Y0 - 2, P.Y1 + 2, P.SEAM - c, P.SEAM + 0.01, P.CORNER_R + 2)
        z0, lo, hi = P.SEAM - c - e, _outline_sketch(-e), _outline_sketch(c + e)
    keep = cq.Workplane('XY', origin=(cx, cy, z0)).placeSketch(lo, hi.moved(cq.Location(cq.Vector(0, 0, c + 2 * e)))).loft()
    return ring.cut(keep)


# ---- side keys: one flexure key per switch, grown out of the lid's side wall ---------------------
def side_tabs():
    """Layout of the side keys (sidekeys.py builds them, lid.py makes them part of the lid). Returns
    dicts with side (+1 right / -1 left), the switch plunger face, the key's inner face X at the nub,
    its Y span (root end, free end) and the pad span.

    Each pad is TAB_PAD_LEN long and centred on its plunger, so a thumb anywhere on it lands on the
    switch; the key runs TAB_FREE_BEYOND past the pad's far end. It flexes from TAB_ROOTS, where its
    bar joins the lid's wall, to y_block, where it rises past the parting line to carry the pad.

    The key's bar replaces the outer TAB_T of the SIDE_WALL. Its nub stops TAB_GAP_SIDE[side] from the plunger.
    Behind the void stands the inner sliver (in the tub) and the lid's own wall (below the parting
    line), whose outer face ('stop') the bar bottoms on after TAB_VOID - the gap plus the switch's own
    maximum travel - so the case, not the switch, takes an over-press."""
    out = []
    for ref, y_root in P.TAB_ROOTS.items():
        sp = hw.switch_plunger(ref)
        fx, fy, fz = sp['face']
        side = 1 if sp['axis'][0] > 0 else -1
        inner = P.X1 - P.TAB_T if side > 0 else P.X0 + P.TAB_T
        stop = P.WALL_X1 + P.SLIVER if side > 0 else P.WALL_X0 - P.SLIVER
        nub_to = fx + side * P.TAB_GAP_SIDE[side]
        half = P.TAB_PAD_LENS.get(ref, P.TAB_PAD_LEN) / 2
        away = 1 if y_root < fy else -1                  # direction from the root toward the free end
        y_free = fy + away * (half + P.TAB_FREE_BEYOND)
        nw = P.NUB_W.get(ref, P.NUB['w'])
        y_block = fy - away * (half + P.TAB_BLOCK_MARGIN)  # where the key rises past the parting line
        out.append({'ref': ref, 'side': side, 'away': away, 'face': (fx, fy, fz), 'inner': inner, 'stop': stop,
                    'y_root': y_root, 'y_free': y_free, 'pad_y': (fy - half, fy + half),
                    'nub_to': nub_to, 'nub_w': nw, 'nub_y': (fy - nw / 2, fy + nw / 2),
                    'gap': round(abs(nub_to - fx), 4), 'travel_to_stop': round(abs(inner - stop), 4),
                    'flex_root': y_root, 'y_block': y_block, 'body_y': (sp['body'][2], sp['body'][3])})
    return out


def tab_window(t):
    """The window one nub needs through the inner sliver, open to the parting line. Since Rev I the
    nub's top is flat (it is the last layer of the key's print), so the window only has to clear it.
    The window runs down through the tongue as well, which is why joint.runs() subtracts these spans
    from the tongue."""
    s, W = t['side'], P.NUB_WINDOW
    top = P.NUB['z'][1] + W['top_clr']
    y0, y1 = t['nub_y']
    x = (P.WALL_X1 - 0.4, t["stop"] + 0.4) if s > 0 else (t["stop"] - 0.4, P.WALL_X0 + 0.4)
    return {'y': (y0 - W['clr'], y1 + W['clr']), 'top': top, 'x': (min(x), max(x))}


def usb():
    """Receptacle shell envelope measured by slicing the STEP model 0.2 mm behind its mouth
    (the model's overall bounds include the through-hole legs, which stand up through the PCB)."""
    s = hw.solids()['J1']
    b = s.BoundingBox()
    cut = s.intersect(cq.Solid.makeBox(0.1, 40, 40, cq.Vector(b.xmax - 0.3, b.ymin - 5, b.zmin - 5)))
    sl = cut.BoundingBox()
    # the shell's inner opening (J1's socket), from the section face's hole
    face = max(cq.Workplane(obj=cut).faces('>X').vals(), key=lambda f: f.Area())
    ib = face.innerWires()[0].BoundingBox()
    # corner radii: the shell is a rounded rectangle (r 1.3 outside, 1.0 inside), not a stadium
    radius = lambda w: max(e.radius() for e in w.Edges() if e.geomType() == 'CIRCLE')
    return {'y': (sl.ymin, sl.ymax), 'z': (sl.zmin, sl.zmax), 'mouth_x': b.xmax,
            'yc': (sl.ymin + sl.ymax) / 2, 'zc': (sl.zmin + sl.zmax) / 2,
            'inner_y': (ib.ymin, ib.ymax), 'inner_z': (ib.zmin, ib.zmax),
            'r': radius(face.outerWire()), 'inner_r': radius(face.innerWires()[0])}
