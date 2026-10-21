"""Bottom-row keys (2026-09-26): straight keys over bell cranks (crank.py; params 'bottom keys').

The finger presses the key straight toward -Z. It slides between the rail's face (its +Y face rides it) and the chin
wall, and pushes the crank's crowned pad with its flat pusher; the crank turns the press into the +Y push the
right-angle switch needs. Nothing preloads the chain: the key rests on its crank and the crank on the switch, so the
key's rest height is the switch's (no free travel face-up), and two rigid hooks only bound it outward (test 2,
2026-09-30: the hook keys, keystab RECOMMENDATION / concept C4-A; the drag leaf, its slit and bump are gone).

Parts (YZ profiles, dx from the key's centre, at rest):
  cap      |dx| <= 5.00 (10.00: 50 layers on its -X end; 4.95 to 2026-10-03), y -7.55..-4.225, from KEY_CAP_Z0
           to KEY_TOP_OVER_FACE over the build's face: the keys are tub-specific (x3 standard 5.77 tall, light strip
           6.97). Solid across its full depth; 0.4 x 45 on all four top edges; its vertical corners R1.0 (+Y; R0.5
           to 2026-10-03: as sliced its end layers came 0.20 off the opening's R0.5 arcs; the bed end's starts with
           its 45-degree tangent) and R0.3 (chin side)
  pusher   the back plate under the cap's chin half, y -7.80..-6.55, down to -0.20: flat, on the crank's crown. No
           foot (2026-09-29): the pusher's chin end below KEY_PUSHER stop_z1 (0.55), 0.40 off the chin wall, is the
           chin-side stop; above it the key's chin side is the cap's chin face (-7.55) all the way up
  body     under the cap between the crank's cheeks, |dx| <= 3.30: 0.45 off their inner faces, over the key's 0.30 of
           X play (the opening stops a key pushed sideways first); over the cheeks (the cheek zone) the cap is cut up
           to 2.70. Its -X step is cut 45 degrees (it would face the bed in the print)
  hooks    two, |dx| 3.95..5.00 (KEY_HOOK, centres 8.95 apart), KEY_HOOK h (0.80) tall at KEY_HOOK_Z (KEY_W_OUT
           under the slot's roof at rest), from the chin face out to KEY_HOOK tip, 0.40 off the back of the tub's slot
           (params KEY_SLOT: two per key in the chin wall's inner face, open to the rim). Face down the key drops
           KEY_W_OUT onto them, both flat under the roof. The +X hook's -X face has a 45-degree lead in plan
           (KEY_HOOK_LEAD): it faces the bed as the key prints. Each runs 0.35 into the key, so it squares the chin
           face's R0.3 corner over its own height
  root     over the first KEY_ROOT (0.60) from the -X end the chin side is solid out to the hooks' tip, from the
           pusher's underside up to the hooks' top (in the -X slot), so the bed end's chamfer leaves no thin stub of
           the -X hook for layer 2 to hang from
Fit (2026-09-29, Ian's first print jammed the Rev L keys): 0.40 on the chin side (the cap's chin face to the opening's
chin edge, the pusher's chin end to the chin wall, each hook's tip to its slot's back), 0.30 per side to the opening,
0.40 to the webs and to the slots' outer sides (0.35 / 0.45 to 2026-10-03: the 50-layer key), all from the key
(mechanics.key_fit, slice_check.key_fit).

Printed on its -X end (plates.ORIENT: +X up; test 1, 2026-09-29), no supports: the -X hook starts on the bed (on the
root) and the +X hook builds up its 45-degree lead, so nothing overhangs past 45 degrees. The bed end's outline comes
in KEY_BED_END (0.30 in layer 1, 0.10 in layer 2: a 0.4 x 45 chamfer all round), so its elephant foot stays inside the
cap's outline.
The button face is a side wall in this pose (fine layer lines, not the bed's texture).
"""
import cadquery as cq
from shapely.geometry import Polygon
import hw
import params as P
from geom import box, xz_prism, yz_prism

NAME = 'key-x3ls' if P.LIGHT_STRIP else 'key-x3std'


def centre(ref):
    return hw.switch_plunger(ref)['face'][0]


def top(face=None):
    return (P.Z_FRONT if face is None else face) + P.KEY_TOP_OVER_FACE


def _plan(x0, x1, y0, y1, z0, z1, r_top=0.0, r_bottom=0.0, bed_tangent=False):
    """Prism over a plan rectangle with its +Y (r_top) or -Y (r_bottom) vertical corners rounded. bed_tangent: the
    -X end's +Y arc starts with its 45-degree tangent instead (from the end face to the arc's 45-degree point): the key
    prints on its -X end, where an arc starting square off the bed end would be a flat overhang (2026-10-03, R1.0)."""
    s = cq.Sketch().rect(x1 - x0, y1 - y0)
    if r_top:
        s = s.vertices('>Y').fillet(r_top)
    if r_bottom:
        s = s.reset().vertices('<Y').fillet(r_bottom)
    w = (cq.Workplane('XY').placeSketch(s).extrude(z1 - z0)
         .translate(((x0 + x1) / 2, (y0 + y1) / 2, z0)))
    if r_top and bed_tangent:
        k = r_top * (1 - 2 ** -0.5)
        w = w.union(cq.Workplane('XY').polyline([(x0 + k, y1 - k), (x0, y1 - 2 * k), (x0, y1 - r_top)]).close()
                    .extrude(z1 - z0).translate((0, 0, z0)))
    return w


def hooks():
    """The two hooks in the key's own frame (dx from its centre, at rest): the -X hook a block, the +X hook with its
    45-degree lead on its -X face (in plan, from the chin face at dx 3.95 - KEY_HOOK_LEAD out to the tip at 3.95). Each
    runs 0.35 into the key (it squares the chin face's R0.3 corner over its height)."""
    Hk, (z0, z1) = P.KEY_HOOK, P.KEY_HOOK_Z
    (x0, x1), tip, y0 = Hk['dx'], Hk['tip'], P.KEY_Y[0]
    yin = round(y0 + 0.35, 3)
    lead = P.KEY_HOOK_LEAD
    minus = box(-x1, -x0, tip, yin, z0, z1)
    plus = (cq.Workplane('XY').polyline([(x0 - lead, yin), (x0 - lead, y0), (x0, tip), (x1, tip), (x1, yin)]).close()
            .extrude(z1 - z0).translate((0, 0, z0)))
    return minus.union(plus)


def root():
    """The root in the key's own frame: over the first KEY_ROOT from the -X end, the chin side solid from the hooks' tip
    to 0.01 into the key, from the pusher's underside up to the hooks' top (its top face is the -X hook's)."""
    h, y0 = P.KEY_HALF, P.KEY_Y[0]
    return box(-h, -h + P.KEY_ROOT, P.KEY_HOOK['tip'], round(y0 + 0.01, 3), P.KEY_PUSHER['z0'], P.KEY_HOOK_Z[1])


def _yz_section(shape, x):
    """The solid's section at X x, as a shapely polygon in (y, z) (off its mesh: even-odd over the section's loops)."""
    import trimesh
    vs, ts = shape.val().tessellate(0.002, 0.05)
    m = trimesh.Trimesh([(v.x, v.y, v.z) for v in vs], ts, process=True)
    g = Polygon()
    for loop in m.section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0]).discrete:
        if len(loop) >= 3:
            g = g.symmetric_difference(Polygon(loop[:, [1, 2]]).buffer(0))
    return g


def _bed_end(key):
    """The bed end (-X) as printed on it: in each of its first two layers (0.2 each) the key's outline comes in
    KEY_BED_END (the outline taken 0.45 in, inside the root block), the same as a 0.4 x 45 chamfer all round at the
    layers' mid-planes."""
    h = P.KEY_HALF
    sec = _yz_section(key, -h + 0.45)
    for i, e in enumerate(P.KEY_BED_END):
        xa, xb = -h + 0.2 * i, -h + 0.2 * (i + 1)
        keep = sec.buffer(-e, join_style=2)
        kp = None
        for g in getattr(keep, 'geoms', [keep]):
            s = yz_prism(list(g.exterior.coords)[:-1], xa - 0.02, xb + 0.01)
            kp = s if kp is None else kp.union(s)
        key = key.cut(box(xa - 0.01, xb, -12, 0, -3, 10).cut(kp))
    return key


def build(ref=None, lift=0.0, xc=None, face=None, with_hooks=True):
    """One key at rest (lift: +Z from rest), at the switch `ref` (or X xc; 0 without either); face: the tub face the key
    is set from (this build's); with_hooks=False leaves the hooks off (the checks take them apart)."""
    h, (y0, y1), z0 = P.KEY_HALF, P.KEY_Y, P.KEY_CAP_Z0
    zt = top(face)
    r_top, r_chin = P.KEY_CORNER_R
    ch = P.KEY_CAP_CHAMFER
    yc = round(y0 + 0.5, 3)                          # the cap's chin strip (its R0.3 corners) and the rest
    # the cap: the chin strip and the rest, its +Y and X top edges chamfered (the chin edge below, with the others)
    rest = _plan(-h, h, yc, y1, z0, zt, r_top=r_top, bed_tangent=True)
    rest = rest.faces('>Z').edges('not <Y').chamfer(ch)
    key = _plan(-h, h, y0, yc + 0.01, z0, zt, r_bottom=r_chin).union(rest)
    Pu, Bd, CZ = P.KEY_PUSHER, P.KEY_BODY, P.KEY_CHEEK_ZONE
    key = key.union(box(-h, h, Pu['y'][0], Pu['y'][1], Pu['z0'], z0 + 0.01))
    key = key.union(box(-Bd['half'], Bd['half'], Pu['y'][1] - 0.01, y1, Bd['z0'], z0 + 0.01))
    for a, b in ((-h, -Bd['half']), (Bd['half'], h)):
        key = key.union(box(a, b, Pu['y'][1] - 0.01, CZ['y'], Pu['z0'], z0 + 0.01))      # the pusher, on over the cheek
        key = key.cut(box(a - (1 if a < 0 else 0), b + (1 if b > 0 else 0), CZ['y'], y1 + 1, -1, CZ['z0']))
    # above the pusher's stop (stop_z1) the chin side is the cap's chin face, its corners R0.3 as the cap's; below it
    # the pusher's chin end (0.40 off the chin wall) is the chin-side stop
    st = Pu['stop_z1']
    key = key.cut(box(-h - 1, h + 1, y0 - 1, y0, st, zt + 1))
    key = key.cut(box(-h - 1, h + 1, y0 - 0.01, yc, st, z0 + 0.005).cut(_plan(-h, h, y0, y1, st - 0.1, z0 + 0.1, r_bottom=r_chin)))
    if with_hooks:
        key = key.union(hooks()).union(root())
    # the body's -X step (it faces the bed in the print), 45 degrees from the cheek zone's floor down to the body's
    hb, zb0, czz = Bd['half'], Bd['z0'], CZ['z0']
    key = key.cut(xz_prism([(-hb - 0.01, czz), (-hb - 0.01, zb0 - 0.01), (-hb + (czz - zb0) + 0.01, zb0 - 0.01)], CZ['y'], y1 + 0.1))
    # the top's four edges, 0.4 x 45 (the button reads the same all round)
    for yy, s in ((y0, 1), (y1, -1)):
        key = key.cut(yz_prism([(yy + s * ch, zt + 0.01), (yy - s * 0.01, zt - ch - 0.01), (yy - s * 0.01, zt + 0.01)], -h - 1, h + 1))
    for s in (-1, 1):
        xe = s * h
        key = key.cut(xz_prism([(xe - s * ch, zt + 0.01), (xe + s * 0.01, zt - ch - 0.01), (xe + s * 0.01, zt + 0.01)], y0 - 1, y1 + 1))
    key = _bed_end(key)
    key = key.clean()
    x = centre(ref) if ref else (xc or 0.0)
    return key.translate((x, 0, lift)) if (x or lift) else key


if __name__ == '__main__':
    for ref in P.KEY_REFS:
        k = build(ref)
        print(ref, len(k.solids().vals()), round(k.val().Volume(), 1))
