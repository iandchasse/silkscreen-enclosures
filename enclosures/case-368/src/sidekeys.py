"""Side keys (Rev J): each side button is a flexure key that is part of the LID: the lid's side wall,
cut free on three sides, and from the pad on, carried up past the parting line into a slot in the tub.

Rev G/H cut the key out of the tub's wall, which meant its top edge was printed over an air gap: on
every print it strung. Rev I made it a separate part, and the clip that held it was too small to hold.
The lid prints back face down, so a key standing on the back face has its bottom edge on the bed and
its top edge as the last layer: every surface grows straight up, and it is anchored in the lid's wall.

  bar      the outer TAB_T of the lid's wall, flush with the case face, from the back face (TAB_Z[0])
           to TAB_BAR_TOP, just under the tub's rim, and from its root in the lid's wall to its free
           end. It is the flexure: TAB_FLEX_T thick from the root to the block, full thickness from
           there to the nub (that stretch is the hard stop) and relieved toward the free end, which
           deflects further than the nub. Since Rev K its bottom edge was the lid's own BACK_EDGE_R
           round with a 45-degree foot along its inside; since 2026-10-19 (TAB_BASE) the round's
           corner under the key is filled, and since 2026-10-20 (TAB_BASE 'teardrop') the round's last 0.59 under
           the key, from the hinge's end to the free end, is a 45 to the bed, so it stands on 0.83 of bed beside
           the foot's edge; for TAB_HINGE from the root all of it is notched away, and that is where it bends
  block    the same section carried on up to TAB_Z[1] from y_block (just before the pad) to the free
           end, into the tub's slot: 7.3 tall, so it barely bends, and it carries the pad and the nub
  pad      TAB_PAD_PROUD proud with a flat face; a 45-degree face below it, back to the key (it prints
           as an overhang now), and the Rev G-I upper face above it
  nub      from the bar's inner face through the sliver's window to TAB_GAP_SIDE off the plunger, with a
           45-degree gusset under it for the same reason

Behind the key is a TAB_VOID-wide slot through the lid's back face (the key's travel), and at its free
end a TAB_END_CLR slot through the lid's wall; above the parting line the tub's slot surrounds it as
it did Rev I's keys. The switch's plunger returns the key; nothing else needs a spring. The keys go on
with the lid, last: they slide up their slots and the nubs up the sliver's windows.
"""
import cadquery as cq
import hw
import params as P
import body
from geom import box, xz_prism, yz_prism



def inner_x(t, y):
    """X of the key's inner face at Y: full at the root, tapering to TAB_FLEX_T, which runs to the
    block; full again from there to the plunger, then relieved to the free end."""
    s, a = t['side'], t['away']
    xo = P.X1 if s > 0 else P.X0
    full, flex = xo - s * P.TAB_T, xo - s * P.TAB_FLEX_T
    fy = t['face'][1]
    u = (y - t['y_root']) * a                            # distance from the root toward the free end
    r0, r1 = P.TAB_ROOT_FULL, P.TAB_ROOT_FULL + P.TAB_ROOT_TAPER
    n0 = (t['y_block'] - t['y_root']) * a
    nf = (fy - t['y_root']) * a
    ne = (t['y_free'] - t['y_root']) * a
    taper = 0.3
    if u <= r0:
        return full
    if u <= r1:
        return full + (flex - full) * (u - r0) / (r1 - r0)
    if u <= n0 - taper:
        return flex
    if u <= n0:
        return flex + (full - flex) * (u - (n0 - taper)) / taper
    if u <= nf:
        return full
    return full + s * P.TAB_RELIEF_MAX * min(1.0, (u - nf) / max(ne - nf, 1e-6))


def _plan(t, y0, z0, z1):
    """The key's plan from y0 to its free end, extruded from z0 to z1."""
    s, a = t['side'], t['away']
    xo = P.X1 if s > 0 else P.X0
    yr, yb = t['y_root'], t['y_block']
    ys = [yr, yr + a * P.TAB_ROOT_FULL, yr + a * (P.TAB_ROOT_FULL + P.TAB_ROOT_TAPER), yb - a * 0.3, yb,
          t['face'][1], t['y_free']]
    ys = sorted({y for y in ys if (y - y0) * a > 1e-6} | {y0}, key=lambda y: (y - yr) * a)
    inner = [(inner_x(t, y), y) for y in ys]
    outer = [(xo, y) for y in reversed(ys)]
    return cq.Workplane('XY').polyline(inner + outer).close().extrude(z1 - z0).translate((0, 0, z0))


def foot_x(t):
    """X of the foot's inner edge on the bed, and of the lid's cut there (TAB_FOOT_GAP behind it at the
    root and the nub, opening toward the free end): (foot, cut(y))."""
    s, a = t['side'], t['away']
    xo = P.X1 if s > 0 else P.X0
    xb = xo - s * (P.TAB_FLEX_T + P.TAB_FOOT)
    g0, g1 = P.TAB_FOOT_GAP
    nf = (t['face'][1] - t['y_root']) * a
    ne = (t['y_free'] - t['y_root']) * a

    def cut(y):
        u = (y - t['y_root']) * a
        g = g0 if u <= nf else g0 + (g1 - g0) * min(1.0, (u - nf) / max(ne - nf, 1e-6))
        return xb - s * g
    return xb, cut


def bar(t):
    """The bar - the lid's wall below the parting line - from the root to the free end, with the
    parting line's V on its outer top edge where the tub's wall stands over it. Rev K: its bottom edge
    was the lid's back round, with the foot along its inside at the bed what it printed on (one 0.52 bead); since
    2026-10-19 TAB_BASE fills the round's corner under it, from the hinge's end to the free end."""
    import body as B
    s, a = t['side'], t['away']
    xo = P.X1 if s > 0 else P.X0
    b = _plan(t, t['y_root'], P.TAB_Z[0], P.TAB_BAR_TOP)
    c = 0.25
    v = xz_prism([(xo - s * c, P.TAB_BAR_TOP + 0.01), (xo + s * 0.5, P.TAB_BAR_TOP + 0.01), (xo + s * 0.5, P.TAB_BAR_TOP - c - 0.5),
                  (xo, P.TAB_BAR_TOP - c)], *sorted((t['y_root'] - a * 1, t['y_block'])))
    b = b.cut(v)
    xb, _ = foot_x(t)
    xi = xo - s * 0.35
    h = abs(xi - xb)
    # the foot from the hinge's end to the free end: since 2026-10-12 it stands TAB_FOOT (1.26) up the bar's inner
    # face, over the notch's roof (TAB_NOTCH), and in the hinge it would stiffen the bend
    ys = sorted((t['y_root'] + a * P.TAB_HINGE, t['y_free']))
    ft = xz_prism([(xb, P.Z_BACK), (xi, P.Z_BACK), (xi, P.Z_BACK + h)], *ys)
    b = b.union(ft).intersect(B.outer_body())
    if P.TAB_BASE:
        # 2026-10-19: the back round's corner under the key, filled from the hinge's end to the free end (params.TAB_BASE),
        # so the key's first layers stand on more bed than one 0.52 bead: 'square' 1.70, 'chamfer' 1.00, 'teardrop' 0.83
        # (as sliced with the CC2 presets; Ian chose 'teardrop' 2026-10-20). The profile's long side is the foot's
        # 45-degree face, so nothing new overhangs; lid_cut already clears the lid u 0..TAB_FOOT_BED + TAB_FOOT_GAP
        u = abs(xo - xb)                                   # the foot's inner edge on the bed: 2.0 on both cases
        R, k, c = P.BACK_EDGE_R, 1 - 2 ** -0.5, P.TAB_BASE_C
        prof = {'square': [(0.0, 0.0), (u, 0.0), (0.0, R)],
                'chamfer': [(c, 0.0), (u, 0.0), (0.0, R), (0.0, c)],
                'teardrop': [(2 * k * R, 0.0), (u, 0.0), (k * R, k * R)]}[P.TAB_BASE]
        yb = sorted((t['y_root'] + a * P.TAB_HINGE, t['y_free']))
        b = b.union(xz_prism([(xo - s * du, P.Z_BACK + dz) for du, dz in prof], *yb))
    # the hinge: no round and no foot for TAB_HINGE from the root, so the key bends there
    xn = sorted((xb - s * 1.0, xo + s * 1.0))
    yn = sorted((t['y_root'] - a * 0.01, t['y_root'] + a * P.TAB_HINGE))
    return b.cut(box(xn[0], xn[1], yn[0], yn[1], P.Z_BACK - 1.0, P.Z_BACK + P.TAB_NOTCH))


def block(t):
    """The block: the key carried up past the parting line from y_block to the free end."""
    return _plan(t, t['y_block'], P.TAB_BAR_TOP - 0.01, P.TAB_Z[1])


def pad(t):
    """Pad: flat face, 45-degree lower face (an overhang in the lid's print, so it has to be), the
    Rev G-I upper face, rounded ends in plan."""
    s = t['side']
    xo = P.X1 if s > 0 else P.X0
    pr = P.TAB_PAD_PROUD
    zf0, zf1 = P.TAB_PAD_FACE
    pz1 = P.TAB_Z[1] - 0.1
    py0, py1 = t['pad_y']
    root = xo - s * 0.3                                  # the pad overlaps the bar
    prof = [(root, zf0 - pr - 0.3), (xo + s * pr, zf0), (xo + s * pr, zf1), (root, pz1)]
    p = xz_prism(prof, py0 - 1, py1 + 1)
    z_lo = zf0 - pr - 0.3
    plan = (cq.Workplane('XY').placeSketch(
        cq.Sketch().rect(pr + 0.3, py1 - py0).vertices('>X' if s > 0 else '<X').fillet(pr - 0.05))
        .extrude(pz1 - z_lo + 2).translate(((root + xo + s * pr) / 2, (py0 + py1) / 2, z_lo - 1)))
    return p.intersect(plan)


def nub(t):
    """From the bar's inner face to TAB_GAP_SIDE off the plunger. Flat tip over NUB['z'], a lead at its top
    edge, and a 45-degree gusset under it back to the bar - the lid prints it from the bottom up, so the
    underside cannot be flat. The gusset is also the lead-in that walks the nub past the plunger as the
    lid goes on. A NUB_BOND key's base follows the relieved face: it reaches 0.05 into it at the nub's
    free-end end, so the gusset runs that much lower."""
    s, n = t['side'], P.NUB
    nz0, nz1 = n['z']
    L = n['lead']
    tip, base = t['nub_to'], t['inner'] + s * 0.05
    if t['ref'] in P.NUB_BOND:          # fused to the relieved face over its whole width (params.NUB_BOND)
        y_far = t['nub_y'][1] if t['away'] > 0 else t['nub_y'][0]
        base = inner_x(t, y_far) + s * 0.05
    drop = abs(base - tip)
    prof = [(tip, nz0), (tip, nz1 - L), (tip + s * L, nz1), (base, nz1), (base, nz0 - drop)]
    return xz_prism(prof, t['nub_y'][0], t['nub_y'][1])


def build(ref):
    """One side key in its assembled position: the part of the lid that flexes."""
    t = next(tb for tb in body.side_tabs() if tb['ref'] == ref)
    return bar(t).union(block(t)).union(pad(t)).union(nub(t)).clean()


def lid_cut(t):
    """What comes out of the lid for one key before the key goes back in: the key's own footprint and
    the void behind it (from the sliver's outer face out), from the root to TAB_END_CLR past the free
    end, from below the back face to above the parting line; and at the bed, the room behind the key's
    foot, which rises at 45 degrees from TAB_FOOT_GAP behind it until it meets that void. The lid wall's
    edge beyond the end slot is chamfered TAB_END_FOOT at the bed, so the first layer's squash cannot
    close the slot."""
    s, a = t['side'], t['away']
    xo = P.X1 if s > 0 else P.X0
    xs = sorted((t['stop'], xo + s * 1.0))
    ye = t['y_free'] + a * P.TAB_END_CLR
    ys = sorted((t['y_root'], ye))
    cut = box(xs[0], xs[1], ys[0], ys[1], P.Z_BACK - 1.0, P.SEAM + 1.0)
    # behind the foot: a ruled solid between the cut line on the bed and the same line H higher, H out
    _, xc = foot_x(t)
    H = 1.8
    yk = [t['y_root'], t['face'][1], t['y_free'], ye]
    far = xo + s * 1.0
    z0 = P.Z_BACK - 0.01
    lo = [(xc(y) - s * 0.01, y) for y in yk] + [(far, y) for y in reversed(yk)]
    hi = [(xc(y) + s * (H + 0.01) - s * 0.01, y) for y in yk] + [(far, y) for y in reversed(yk)]
    back = (cq.Workplane('XY').workplane(offset=z0).polyline(lo).close()
            .workplane(offset=H + 0.01).polyline(hi).close().loft(ruled=True))
    cut = cut.union(back)
    f = P.TAB_END_FOOT
    xf = sorted((xc(ye) - s * 0.3, far))
    foot = yz_prism([(ye - a * 0.01, z0), (ye + a * f, z0), (ye - a * 0.01, P.Z_BACK + f + 0.01)], xf[0], xf[1])
    return cut.union(foot)


def summary():
    rows = {}
    for t in body.side_tabs():
        rows[t['ref']] = {'root': t['y_root'], 'block': round(t['y_block'], 2), 'free': round(t['y_free'], 2), 'gap': t['gap'], 'void': t['travel_to_stop'],
                          'flex_len': round(abs(t['y_block'] - t['y_root']), 2),
                          'length': round(abs(t['y_free'] - t['y_root']), 2)}
    return {'keys': rows, 'flex_t': P.TAB_FLEX_T, 't': P.TAB_T, 'z': list(P.TAB_Z), 'height': round(P.TAB_Z[1] - P.TAB_Z[0], 2),
            'slot_clr': P.TAB_SLOT_CLR, 'end_clr': P.TAB_END_CLR, 'root_clr': P.TAB_ROOT_CLR, 'end_foot': P.TAB_END_FOOT,
            'pad_face': list(P.TAB_PAD_FACE), 'nub_z': list(P.NUB['z']), 'bar_top': P.TAB_BAR_TOP,
            'foot': P.TAB_FOOT, 'foot_gap': list(P.TAB_FOOT_GAP), 'hinge': P.TAB_HINGE,
            'notch': P.TAB_NOTCH}


if __name__ == '__main__':
    import json
    for t in body.side_tabs():
        k = build(t['ref'])
        print(t['ref'], len(k.solids().vals()), round(k.val().Volume(), 2))
        cq.exporters.export(k, str(hw.ROOT / 'out' / f"skey_{t['ref']}.stl"), tolerance=0.01, angularTolerance=0.1)
    print(json.dumps(summary(), indent=1))
