"""Printable stand-in for the PCBA, for test-fitting the case without risking the real board.

  - every component keeps its outer shape as a convex hull, per STEP solid, and each switch's
    plunger is hulled on its own so it stays a distinct nub where the keys and tabs meet it
  - through-hole leads are cut off at the board's rear face. A slicer would drop 0.3-0.6 mm legs
    anyway, which leaves bodies floating; without them the front face is flat for the bed
  - each body hangs from the board on a skirt that fills its standoff gap (inside the board
    outline only), so the whole thing is one solid
  - vias and lead holes are filled; the five mounting holes and the display-ribbon slot stay
  - the board is the fabricated 1.6 mm (the STEP draws it 1.51)
  - every switch site is left empty for a real switch (Rev F; Rev E opened three), so each key,
    tab and the reset pin can be tried with the real click before any board is made. Each site
    keeps its four through-holes, drilled HOLE_COMP larger all round because printed holes
    shrink, and (Rev H, back again) a low cradle on the three sides away from its plunger, now
    clipped clear of the display-ribbon slot that the bottom row's back rims used to cover
  - J1 is modelled rather than left out (Rev G, Ian's ask): a receptacle shell a real plug can enter.
    Rev H made every wall of it printable (USB_MOCK); Rev I drops the bezel, so it is that printable
    shell right to the mouth, behind the tub's own port floor
  - J7, the microSD socket, is in (Rev H): it has only a VRML model, so hw.WRL_ONLY supplies it
  - the ESP32-S3 module stops at the board edge: its antenna end hangs over the board's notch,
    where it would only print as a strand in mid-air (CLIP)

Writes out/pcba-dummy.stl (assembly frame) and out/pcba-dummy.json (what was kept, and how it
sits in the case). Print it front face down: plates.py writes the oriented copy to out/<build>/print/.
"""
import json
import numpy as np
import trimesh
import manifold3d as mf
import shapely.geometry as sg
import cadquery as cq
import hw
import params as P

MIN_VOL = 0.3            # mm3: hulls smaller than this (0402 parts, lead stubs) are left out
SINK = 0.05              # hulls and skirts reach this far into the board, so every union is an overlap
SWITCHES = P.KEY_REFS + hw.LEFT_SWITCHES + hw.RIGHT_SWITCHES + [hw.RESET]
# Empty sites for real switches: all of them (the four bottom keys, the five side tabs, reset).
OPEN = list(SWITCHES)
# Parts cut back to the board outline: U4's antenna end overhangs the notch in the left edge.
CLIP = {'U4'}
HOLE_COMP = 0.1          # radius added to the open sites' 1.0 / 1.3 mm holes
# Rev H: the low walls round each open switch site are back (Ian took them off in Rev G only because
# the bottom row's back rims covered the display-ribbon slot). Each rim is now clipped clear of
# every hole the board keeps, the ribbon slot included, by `hole_clr`; the bottom four keep their
# two side rims and lose the back one, which sat 0.2 mm from the slot's edge.
CRADLE = dict(w=0.8, clr=0.2, depth=1.2, hole_clr=0.3)
# J1 stand-in (Rev H/I). A real USB-C receptacle is 0.3 mm steel round an 8.34 x 2.56 opening, and a
# 0.4 nozzle cannot print a 0.3 mm wall: Rev G's 0.20 mm sides were simply dropped by the slicer.
# So the bore takes a plug (8.25 x 2.40) with room, and the side walls are `side` thick - two lines -
# which makes the shell 0.56 mm wider than the real one; nothing else reaches that far. Top and bottom
# stay the real part's height: in print they are layers, not lines, so any thickness prints. Rev H kept
# the last 1.3 mm at the real outline for the bezel's sleeve; with the bezel gone (Rev I) the widened
# shell runs right to the mouth, and the tub's port floor, 0.115 in front of it, hides it.
USB_MOCK = dict(bore=(8.40, 2.62), bore_r=1.0, side=0.55, depth=6.6)


def _mesh(shape, tol=0.03, ang=0.3):
    verts, tris = shape.tessellate(tol, ang)
    return trimesh.Trimesh(np.array([(p.x, p.y, p.z) for p in verts]), np.array(tris), process=True)


def _manifold(m):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32),
                               tri_verts=np.asarray(m.faces, np.uint32)))


def _union(meshes):
    """Union of meshes; any that is not a valid solid is reported rather than poisoning the rest."""
    good, bad = [], 0
    for m in meshes:
        man = _manifold(m)
        if man.status() == mf.Error.NoError and man.volume() > 1e-6:
            good.append(man)
        else:
            bad += 1
    return mf.Manifold.batch_boolean(good, mf.OpType.Add), bad


def _trimesh(man):
    o = man.to_mesh()
    return trimesh.Trimesh(np.asarray(o.vert_properties)[:, :3], np.asarray(o.tri_verts), process=False)


def board():
    """Board solid at 1.6 mm with the mechanical holes, the open sites' lead holes (enlarged),
    and the board outline as a column for clipping skirts."""
    f = cq.Workplane(obj=hw.solids()['PCB']).faces('<Z').val()
    sites = {r: hw.bounds(r) for r in OPEN}
    keep, opened, big = [], {r: [] for r in OPEN}, []
    for w in f.innerWires():
        b = w.BoundingBox()
        cx, cy = (b.xmin + b.xmax) / 2, (b.ymin + b.ymax) / 2
        if min(b.xlen, b.ylen) >= 2.0 or max(b.xlen, b.ylen) >= 5.0:
            keep.append(w)
            big.append(sg.box(b.xmin, b.ymin, b.xmax, b.ymax))    # mounting holes, the ribbon slot, ...
            continue
        for r, s in sites.items():
            if s[0] <= cx <= s[1] and s[2] <= cy <= s[3]:
                d = b.xlen + 2 * HOLE_COMP                   # every lead hole here is round
                keep.append(cq.Wire.makeCircle(d / 2, cq.Vector(cx, cy, b.zmin), cq.Vector(0, 0, 1)))
                opened[r].append([round(cx, 2), round(cy, 2), round(b.xlen, 2), round(d, 2)])
    face = cq.Face.makeFromWires(f.outerWire(), keep)
    solid = cq.Solid.extrudeLinear(face, cq.Vector(0, 0, hw.PCB_T))
    column = cq.Solid.extrudeLinear(cq.Face.makeFromWires(f.outerWire()), cq.Vector(0, 0, 8.0)).translate(cq.Vector(0, 0, -8.0 + SINK + 0.01))
    return solid, column, len(keep), len(f.innerWires()), opened, big


def housing(ref):
    """Footprint of an open site's switch housing, just below its 0.3 mm standoff (clear of the
    plunger and the leads). Reported so the page can show what has to fit in each empty site."""
    s = hw.solids()[ref]
    b = s.BoundingBox()
    h = s.intersect(cq.Solid.makeBox(b.xlen + 20, b.ylen + 20, 0.02, cq.Vector(b.xmin - 10, b.ymin - 10, -1.0))).BoundingBox()
    return [round(v, 2) for v in (h.xmin, h.xmax, h.ymin, h.ymax)]


def cradle(ref, holes):
    """Rims on the three sides of an open site's switch housing away from its plunger: the back
    one takes the press, the two side ones keep the switch square (as Rev F). Each is clipped
    CRADLE['hole_clr'] clear of the board's kept holes - on the bottom row that removes the back
    rim, which would sit over the display-ribbon slot. Returns shapely polygons."""
    hx0, hx1, hy0, hy1 = housing(ref)
    c, w = CRADLE['clr'], CRADLE['w']
    X0, X1, Y0, Y1 = hx0 - c, hx1 + c, hy0 - c, hy1 + c
    ax, ay = hw.switch_plunger(ref)['axis']
    if ax == 0:                                              # plunger along Y
        back = (X0 - w, X1 + w, Y1, Y1 + w) if ay < 0 else (X0 - w, X1 + w, Y0 - w, Y0)
        rims = [back, (X0 - w, X0, Y0, Y1 + w if ay < 0 else Y1), (X1, X1 + w, Y0 if ay < 0 else Y0 - w, Y1)]
    else:                                                    # plunger along X
        back = (X1, X1 + w, Y0 - w, Y1 + w) if ax < 0 else (X0 - w, X0, Y0 - w, Y1 + w)
        rims = [back, (X0, X1, Y0 - w, Y0), (X0, X1, Y1, Y1 + w)]
    keep_out = sg.MultiPolygon(holes).buffer(CRADLE['hole_clr']) if holes else sg.Polygon()
    out = []
    for x0, x1, y0, y1 in rims:
        r = sg.box(x0, y0, x1, y1).difference(keep_out)
        out += [g for g in getattr(r, 'geoms', [r]) if g.geom_type == 'Polygon' and g.area > 0.1]
    return out


def _prism(poly, z0, z1):
    """Watertight prism over a convex polygon (shapely), built explicitly: qhull can return an
    open mesh for very flat prisms."""
    poly = sg.polygon.orient(poly.simplify(0.005), 1.0)
    p = np.asarray(poly.exterior.coords)[:-1]
    n = len(p)
    v = np.vstack([np.c_[p, np.full(n, z0)], np.c_[p, np.full(n, z1)]])
    f = [[0, i + 1, i] for i in range(1, n - 1)] + [[n, n + i, n + i + 1] for i in range(1, n - 1)]
    for i in range(n):
        j = (i + 1) % n
        f += [[i, j, n + j], [i, n + j, n + i]]
    return trimesh.Trimesh(v, np.array(f), process=True)


def _clip_hull(points, edges):
    """Convex hull of a solid clipped to z <= 0: its vertices below the board's rear face plus
    every edge's crossing of that plane."""
    below = points[points[:, 2] <= SINK]
    a, b = points[edges[:, 0]], points[edges[:, 1]]
    cross = (a[:, 2] <= SINK) != (b[:, 2] <= SINK)
    a, b = a[cross], b[cross]
    t = (SINK - a[:, 2]) / (b[:, 2] - a[:, 2])
    pts = np.vstack([below, a + (b - a) * t[:, None]]) if len(a) else below
    if len(pts) < 4 or np.ptp(pts, axis=0).min() < 0.05:
        return None
    try:
        return trimesh.convex.convex_hull(pts)
    except Exception:
        return None


MERGE = {'J6'}            # one hull for the whole part: the header's plastic is drawn per pin


def usb_mock():
    """A printable stand-in for the J1 receptacle, so a real cable can be tried through the case's
    port (USB_MOCK has the reasoning). The mouth stays where the design references it (body.usb():
    x 61.195); the shell is widened so its side walls are two lines thick.

    Returns the mesh, its standoff skirt, and the numbers for the report: the plug clearance, the
    walls, and how deep the bore is against the spec's 6.20 mm mated insertion.
    """
    import body
    from geom import rrect_x
    M = USB_MOCK
    u = body.usb()
    b = hw.bounds('J1')
    w, h = u['y'][1] - u['y'][0], u['z'][1] - u['z'][0]
    bw, bh = M['bore']
    wb = bw + 2 * M['side']                                  # the widened shell
    x_mouth = u['mouth_x']
    shell = rrect_x(b[0], x_mouth, u['yc'], u['zc'], wb, h, min(h / 2 - 0.01, M['bore_r'] + M['side']))
    bore = rrect_x(x_mouth - M['depth'], x_mouth + 0.01, u['yc'], u['zc'], bw, bh, M['bore_r'])
    solid = shell.cut(bore)
    plug = (8.25, 2.40)                                      # USB-C plug shell, nominal
    info = {'shell': [round(w, 2), round(h, 2)], 'shell_r': round(u['r'], 2), 'mouth_x': round(x_mouth, 3),
            'body_mm': round(x_mouth - b[0], 2), 'body_w': round(wb, 2),
            'side_wall_mm': M['side'], 'top_bottom_mm': round((h - bh) / 2, 3), 'real_wall_mm': 0.3,
            'bore': [bw, bh], 'bore_depth_mm': M['depth'],
            'plug_clearance_mm': [round((bw - plug[0]) / 2, 3), round((bh - plug[1]) / 2, 3)],
            'spec_insertion_mm': 6.20}
    # the shell's top is 0.375 below the board's rear face (its legs bridge that on the real part):
    # a skirt fills the standoff over the board, and is clipped to the board outline with the others
    skirt = _prism(sg.box(b[0], u['yc'] - wb / 2, hw.bounds('PCB')[1] - 0.05, u['yc'] + wb / 2).buffer(-0.03),
                   u['z'][1] - 0.02, SINK)
    return _mesh(solid.val(), 0.01, 0.15), skirt, info


def pieces(ref):
    """(solid, is_plunger) for one component."""
    s = hw.solids()[ref]
    if ref in MERGE:
        return [(s, False)]
    if ref == 'J1':
        # A hull of the receptacle shell wraps its side legs and squares off the shell's rounded
        # top corners, which the tub's USB tunnel follows at 0.2 mm. Use the measured shell
        # outline (the tunnel's own reference) as a filled stadium instead.
        import body
        u = body.usb()
        w, h = u['y'][1] - u['y'][0], u['z'][1] - u['z'][0]
        out = []
        for x in s.Solids():
            bb = x.BoundingBox()
            if bb.xmax > hw.bounds('PCB')[1] + 0.1:
                sk = cq.Sketch().rect(w, h).vertices().fillet(min(w, h) / 2 - 1e-3)
                st = cq.Workplane('YZ').placeSketch(sk).extrude(u['mouth_x'] - bb.xmin).translate((bb.xmin, u['yc'], u['zc']))
                out.append((st.val(), False))
            else:
                out.append((x, False))
        return out
    if ref in SWITCHES:
        n = hw.switch_plunger(ref)['nub']
        nb = cq.Solid.makeBox(n[1] - n[0] + 0.02, n[3] - n[2] + 0.02, n[5] - n[4] + 0.02,
                              cq.Vector(n[0] - 0.01, n[2] - 0.01, n[4] - 0.01))
        return [(x, False) for x in s.cut(nb).Solids()] + [(x, True) for x in s.intersect(nb).Solids()]
    return [(x, False) for x in s.Solids()]


def build():
    solid, column, n_keep, n_holes, opened, big_holes = board()
    parts, skirts = [_mesh(solid, 0.02, 0.2)], []
    kept, dropped, sites = {}, {}, {}
    for ref in OPEN:
        rims = cradle(ref, big_holes)
        sites[ref] = {'holes': opened[ref], 'housing': housing(ref), 'axis': hw.switch_plunger(ref)['axis'],
                      'rims': len(rims)}
        # cradles go in with the skirts, so they are clipped to the board outline with them. A rim
        # clipped round a hole need not be convex, so it is extruded rather than fanned (_prism)
        for r in rims:
            m = trimesh.creation.extrude_polygon(r, CRADLE['depth'] + SINK)
            m.apply_translation((0, 0, -CRADLE['depth']))
            skirts.append(m)
    mock = None
    if USB_MOCK:
        shell, skirt, mock = usb_mock()
        parts.append(shell)
        skirts.append(skirt)
    clipped = {}
    for ref in sorted(hw.solids()):
        if ref == 'PCB' or ref in OPEN or (USB_MOCK and ref == 'J1'):
            continue
        for sol, plunger in pieces(ref):
            if ref in CLIP:                               # keep only what lies over the board
                before = sol.Volume()
                sol = sol.intersect(column)
                clipped[ref] = round(clipped.get(ref, 0.0) + before - sol.Volume(), 2)
                if sol.Volume() < 1e-6:
                    continue
            m = _mesh(sol)
            h = _clip_hull(np.asarray(m.vertices), np.asarray(m.edges_unique))
            if h is None:
                continue
            if h.volume < MIN_VOL and not plunger:
                dropped[ref] = dropped.get(ref, 0) + 1
                continue
            hm = _manifold(h)
            if hm.status() != mf.Error.NoError or hm.volume() <= 1e-6:   # qhull left it open: use a prism
                h = _prism(sg.MultiPoint(h.vertices[:, :2]).convex_hull, h.bounds[0][2], h.bounds[1][2])
            parts.append(h)
            kept[ref] = kept.get(ref, 0) + 1
            top = h.bounds[1][2]
            if top < SINK - 0.07:                         # standoff gap: skirt up to the board
                # 0.03 inside the hull's own sides: coincident side faces leave slivers in the union
                fp = sg.MultiPoint(h.vertices[:, :2]).convex_hull.buffer(-0.03)
                if fp.geom_type == 'Polygon' and fp.area > 0.01:
                    skirts.append(_prism(fp, top - 0.02, SINK))
    body, bad = _union(parts)
    if skirts:
        sk, bad2 = _union(skirts)
        bad += bad2
        sk = sk ^ _manifold(_mesh(column, 0.02, 0.2))       # skirts stay inside the board outline
        body = body + sk
    mesh = _trimesh(body)
    # The union can leave a zero-volume sliver of two triangles on a seam. Once an STL reader
    # merges vertices, it turns into a pair of non-manifold edges, so drop anything without volume.
    mesh.merge_vertices()
    pieces_ = mesh.split(only_watertight=False)
    if len(pieces_) > 1:
        mesh = trimesh.util.concatenate([p for p in pieces_ if abs(p.volume) > 1e-3 or len(p.faces) > 50])
    info = {'components_kept': len(kept), 'hulls': sum(kept.values()), 'skirts': len(skirts), 'invalid_skipped': bad,
            'open_sites': sites, 'hole_comp': HOLE_COMP, 'cradle': CRADLE, 'usb_mock': mock, 'clipped_mm3': clipped,
            'small_parts_left_out': sorted(dropped), 'holes_kept': n_keep, 'holes_filled': n_holes - n_keep,
            'bodies': len(mesh.split(only_watertight=False)), 'watertight': bool(mesh.is_watertight),
            'volume_mm3': round(float(mesh.volume), 1), 'triangles': len(mesh.faces),
            'size_mm': [round(float(v), 2) for v in mesh.extents], 'board_t': hw.PCB_T}
    return mesh, info


def checks(mesh):
    """Overlap of the dummy with every printed part in the assembled position, and of each real
    switch, dropped into its open site, with the dummy (its leads through the holes). The lid is the
    printed one, with its side keys (Rev J), whose nubs stand 0.25 off the dummy's switch sites."""
    D = _manifold(mesh)
    out = {'case': {}, 'real_switch_in_site': {}}
    for n in ['tub', 'lid', 'midplate'] + [f'{p}_{r}' for p in ('key', 'crank') for r in P.KEY_REFS]:
        inter = D ^ _manifold(trimesh.load(hw.OUT / f'{n}.stl'))
        v = inter.volume()
        if v > 1e-3:
            lo, hi = np.asarray(inter.bounding_box()).reshape(2, 3) if hasattr(inter, 'bounding_box') else (None, None)
            out['case'][n] = {'mm3': round(v, 3), 'where': [round(float(x), 2) for x in np.r_[lo, hi]]}
        else:
            out['case'][n] = 0.0
    for r in OPEN:
        sw = _mesh(hw.solids()[r], 0.01, 0.1)
        out['real_switch_in_site'][r] = round((D ^ _manifold(sw)).volume(), 4)
    return out


if __name__ == '__main__':
    import time
    t0 = time.time()
    mesh, info = build()
    info['checks'] = checks(mesh)
    mesh.export(hw.OUT / 'pcba-dummy.stl')
    (hw.OUT / 'pcba-dummy.json').write_text(json.dumps(info, indent=1))
    print(json.dumps({k: v for k, v in info.items() if k != 'small_parts_left_out'}), f'{time.time() - t0:.0f}s')
    print('left out (all < %.1f mm3):' % MIN_VOL, len(info['small_parts_left_out']), 'refs')
