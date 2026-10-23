"""The checks for the six changes of 2026-10-23 (Ian, after a community member's edit of the 4.26 standard case; the
same file is in both cases, case-426/src and case-368/src: keep the two byte-identical).

  seam square   no V at the parting line, in the tub (z SEAM + 0.1), the lid (SEAM - 0.1) and the side keys' bars
                (TAB_BAR_TOP - 0.1): a point 0.05 inside the plan outline that is air while the point 0.6 further in is solid
                is a V. Total length of V, mm: 0 when square.
  pads          every kept side key's pad face stands DECIDED['pad_proud'] (1.2) past the case face
  pins          each midplate snap post is a plain pin: solid on its axis (no slot), nothing in the annulus where the barb
                was, its tip at DECIDED['pin_tip'] (-1.00, whole layers from the bed)
  back wordmark engraved in the lid's back above the grip grooves (the ink box is reported), with the floor left under it
  chin plain    the wordmark's old place on the tub's face is solid
  inlays        inlay_wordmark.step and inlay_icon.step fill their recesses exactly: none of the lid, nothing outside the
                body, no recess volume left over; the depth is whole layers
  top screw     (4.26 only) a 2.4 clearance from the rim to PCB_FRONT (1.6) round the top screw: empty on the axis, a wall
                round it, the pilot below 1.6 as before

The limits are the decisions' own numbers (DECIDED), not params values, so the check fails on the old design and passes
on the new one without reading the parameters it checks. run(folder) reads one build's folder of STEP files; the build
calls it on its own out/<build>/ and the report goes to community.json.
"""
import json
import math
from pathlib import Path
import cadquery as cq
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.TopAbs import TopAbs_IN
from OCP.gp import gp_Pnt
import hw
import params as P
import body
import logo
from geom import box, zcyl

DECIDED = dict(          # Ian, 2026-10-23
    seam_v=0.0,          # no V on either half
    pad_proud=1.2,       # side key pads
    pin_d=1.90,          # plain pins in the board's holes
    pin_tip=-1.00,       # the pin's tip, under the board's rear face (whole layers from the midplate's bed)
    wordmark_dy=6.55,    # the back wordmark's centre above the top groove (ink 1.4 to 8.5 on the keyed 4.26 and the 3.68)
    ink_floor=0.4,       # at least this much of the back left under an engraving
    top_clear_to=1.6,    # the top screw's clearance bore reaches the board's front face level
    top_clear_d=2.4,
)
STEP = 0.5               # the seam probe's spacing along the outline (mm)


class Inside:
    """Point-in-solid for a shape (one classifier per solid)."""

    def __init__(self, shape):
        self.c = [BRepClass3d_SolidClassifier(s.wrapped) for s in shape.Solids()]

    def __call__(self, x, y, z):
        p = gp_Pnt(x, y, z)
        for c in self.c:
            c.Perform(p, 1e-6)
            if c.State() == TopAbs_IN:
                return True
        return False


def outline(step=STEP):
    """Points and inward normals round the plan outline (the rounded rectangle of body.outer_body)."""
    X0, X1, Y0, Y1, R = P.X0, P.X1, P.Y0, P.Y1, P.CORNER_R
    out = []

    def line(a, b, n):
        k = max(1, int(math.dist(a, b) / step))
        out.extend(((a[0] + (b[0] - a[0]) * i / k, a[1] + (b[1] - a[1]) * i / k), n) for i in range(k))

    def arc(c, a0, a1):
        k = max(1, int(R * abs(a1 - a0) / step))
        out.extend(((c[0] + R * math.cos(a0 + (a1 - a0) * i / k), c[1] + R * math.sin(a0 + (a1 - a0) * i / k)),
                    (-math.cos(a0 + (a1 - a0) * i / k), -math.sin(a0 + (a1 - a0) * i / k))) for i in range(k))
    line((X0 + R, Y0), (X1 - R, Y0), (0, 1))
    arc((X1 - R, Y0 + R), -math.pi / 2, 0)
    line((X1, Y0 + R), (X1, Y1 - R), (-1, 0))
    arc((X1 - R, Y1 - R), 0, math.pi / 2)
    line((X1 - R, Y1), (X0 + R, Y1), (0, -1))
    arc((X0 + R, Y1 - R), math.pi / 2, math.pi)
    line((X0, Y1 - R), (X0, Y0 + R), (1, 0))
    arc((X0 + R, Y0 + R), math.pi, 1.5 * math.pi)
    return out


def v_length(solid, z, pts):
    """Length (mm) of the outline where the solid has a V at height z: air 0.05 inside the outline, solid 0.6 further in
    (air at both is an opening: a slot, the port, the header)."""
    inside = Inside(solid)
    n = 0
    for (x, y), (nx, ny) in pts:
        if not inside(x + 0.05 * nx, y + 0.05 * ny, z) and inside(x + 0.65 * nx, y + 0.65 * ny, z):
            n += 1
    return round(n * STEP, 2)


def _vol(s, b):
    return s.intersect(box(*b).val()).Volume()


def _frac(s, prism):
    """The part of the prism (a logo cutter) that is solid in s."""
    pv = prism.val()
    return s.intersect(pv).Volume() / pv.Volume()


def run(folder):
    """The checks on one build's folder (tub.step, lid.step, midplate.step, inlay_*.step). -> (report, ok)."""
    f = Path(folder)
    T = cq.importers.importStep(str(f / 'tub.step')).val()
    L = cq.importers.importStep(str(f / 'lid.step')).val()
    M = cq.importers.importStep(str(f / 'midplate.step')).val()
    rep, ok = {}, {}
    D = DECIDED

    # ---- seam square ------------------------------------------------------------------------------------------------
    pts = outline()
    rep['seam V (mm of outline)'] = r = {'tub z SEAM+0.1': v_length(T, P.SEAM + 0.1, pts),
                                         'lid z SEAM-0.1': v_length(L, P.SEAM - 0.1, pts),
                                         'key bars z TAB_BAR_TOP-0.1': v_length(L, P.TAB_BAR_TOP - 0.1, pts)}
    ok['seam square: no V in the tub, the lid or the key bars'] = all(v <= D['seam_v'] for v in r.values())

    # ---- pads -------------------------------------------------------------------------------------------------------
    zf = (P.TAB_PAD_FACE[0] + P.TAB_PAD_FACE[1]) / 2
    pads = {}
    for t in body.side_tabs():
        yc = sum(t['pad_y']) / 2
        bb = L.intersect(box(P.X0 - 3, P.X1 + 3, yc - 1.0, yc + 1.0, zf - 0.1, zf + 0.1).val()).BoundingBox()
        pads[t['ref']] = round(bb.xmax - P.X1 if t['side'] > 0 else P.X0 - bb.xmin, 3)
    rep['pad face proud of the case face'] = pads
    ok[f"pads stand {D['pad_proud']} proud"] = bool(pads) and all(abs(v - D['pad_proud']) <= 0.01 for v in pads.values())

    # ---- pins -------------------------------------------------------------------------------------------------------
    fps = hw.footprints()
    pins = {}
    for ref in P.SNAP_POSTS:
        cx, cy = fps[ref]['cad']
        a = (0.5, 0.5, D['pin_tip'] + 0.35, -0.2)
        axis = _vol(M, (cx - 0.25, cx + 0.25, cy - 0.25, cy + 0.25, a[2], a[3]))
        axis_box = 0.5 * 0.5 * (a[3] - a[2])
        ann = zcyl(cx, cy, -0.6, -0.15, 2.6).cut(zcyl(cx, cy, -0.7, -0.05, 1.96))
        barb = M.intersect(ann.val()).Volume()
        tip = M.intersect(box(cx - 1.5, cx + 1.5, cy - 1.5, cy + 1.5, -3.0, -0.3).val()).BoundingBox().zmin
        pins[ref] = {'axis_solid': round(axis / axis_box, 4), 'barb_mm3': round(barb, 4), 'tip_z': round(tip, 3)}
    rep['pins'] = pins
    ok[f"pins: plain d{D['pin_d']} (solid on the axis, no barb), tip {D['pin_tip']}"] = all(
        v['axis_solid'] >= 0.9999 and v['barb_mm3'] <= 1e-4 and abs(v['tip_z'] - D['pin_tip']) <= 0.01 for v in pins.values())

    # ---- the wordmark on the back, the plain chin --------------------------------------------------------------------
    cfg = P.LOGO_BACK_WORDMARK
    zb = P.Z_BACK
    g = logo.placed(cfg)
    rep['back wordmark'] = {'ink_x': [round(g.bounds[0], 3), round(g.bounds[2], 3)], 'ink_y': [round(g.bounds[1], 3), round(g.bounds[3], 3)],
                            'y': round(cfg['y'], 3), 'depth': cfg['depth']}
    eng = _frac(L, logo.solid(zb + 0.05, zb + 0.35, cfg))
    floor = _frac(L, logo.solid(zb + cfg['depth'] + 0.05, zb + cfg['depth'] + D['ink_floor'], cfg))
    rep['back wordmark'].update({'solid_in_the_engraving': round(eng, 5), 'solid_in_the_floor': round(floor, 5)})
    ok['back wordmark engraved (open in its depth, the floor under it solid)'] = (
        eng <= 1e-4 and floor >= 0.9999 and abs(cfg['y'] - (max(P.GRIP_GROOVES_Y) + D['wordmark_dy'])) < 1e-6 and cfg.get('mirror'))
    chin = _frac(T, logo.solid(P.Z_FRONT - 0.3, P.Z_FRONT - 0.1, P.LOGO_CHIN))
    rep['chin wordmark place solid in the tub'] = round(chin, 5)
    ok['chin plain (the old wordmark place is solid)'] = chin >= 0.9999 and P.LOGO is None

    # ---- the two-colour inlays ----------------------------------------------------------------------------------------
    rb = body.outer_body().val()
    inl = {}
    for name, c in (('inlay_wordmark', P.LOGO_BACK_WORDMARK), ('inlay_icon', P.LOGO_BACK)):
        p = f / f'{name}.step'
        if not p.exists():
            inl[name] = 'MISSING'
            continue
        S = cq.importers.importStep(str(p)).val()
        gb = logo.placed(c).bounds
        win = box(gb[0] - 0.3, gb[2] + 0.3, gb[1] - 0.3, gb[3] + 0.3, zb - 0.01, zb + c['depth']).val().intersect(rb)
        left = win.cut(L.intersect(win)).cut(S)
        inl[name] = {'vol_mm3': round(S.Volume(), 3), 'in_lid_mm3': round(S.intersect(L).Volume(), 5),
                     'outside_body_mm3': round(S.cut(rb).Volume(), 5), 'recess_left_mm3': round(left.Volume(), 5),
                     'depth_layers': round(c['depth'] / P.LAYER, 4)}
    rep['inlays'] = inl
    ok['inlays fill their recesses exactly (0 in the lid, 0 outside, 0 left, whole layers)'] = all(
        isinstance(v, dict) and v['in_lid_mm3'] < 1e-3 and v['outside_body_mm3'] < 1e-3 and v['recess_left_mm3'] < 1e-3
        and abs(v['depth_layers'] - round(v['depth_layers'])) < 1e-6 for v in inl.values()) and len(inl) == 2

    # ---- the top screw's relief (4.26) ---------------------------------------------------------------------------------
    if hasattr(P, 'TOP_SCREW_CLEAR_TO'):
        tx, ty = P.TOP_SCREW
        z0, z1 = P.SEAM + 0.05, D['top_clear_to'] - 0.05
        bore = T.intersect(zcyl(tx, ty, z0, z1, D['top_clear_d'] - 0.1).val()).Volume()      # inside the bore (r 1.15)
        wall = {}
        for nm, (dx, dy) in {'-X': (-1.45, 0), '+X': (1.45, 0), '-Y': (0, -1.45), '+Y': (0, 1.45)}.items():
            b = (tx + dx - 0.15, tx + dx + 0.15, ty + dy - 0.15, ty + dy + 0.15, z0, z1)
            v, vb = _vol(T, b), 0.3 * 0.3 * (z1 - z0)
            wall[nm] = round(v / vb, 3)
        pil = {}
        zp0, zp1 = D['top_clear_to'] + 0.1, D['top_clear_to'] + 3.0
        pil['pilot bore empty r 0.8'] = round(T.intersect(zcyl(tx, ty, zp0, zp1, 1.6).val()).Volume(), 5)
        pil['pilot wall solid (fraction at r 1.25, four sides)'] = {}
        for nm, (dx, dy) in {'-X': (-1.25, 0), '+X': (1.25, 0), '-Y': (0, -1.25), '+Y': (0, 1.25)}.items():
            b = (tx + dx - 0.1, tx + dx + 0.1, ty + dy - 0.1, ty + dy + 0.1, zp0, zp1)
            pil['pilot wall solid (fraction at r 1.25, four sides)'][nm] = round(_vol(T, b) / (0.04 * (zp1 - zp0)), 3)
        rep['top screw'] = {'clearance_bore_mm3_in_d2.3': round(bore, 5), 'wall_at_r1.45 (fraction solid)': wall, **pil}
        ok['top screw relief: bore empty to 1.6, a wall round it, the pilot below as before'] = (
            bore <= 1e-3 and sum(v >= 0.999 for v in wall.values()) >= 2
            and pil['pilot bore empty r 0.8'] <= 1e-3
            and sum(v >= 0.999 for v in pil['pilot wall solid (fraction at r 1.25, four sides)'].values()) >= 3)
    rep['checks'] = ok
    return rep, ok


def check(folder, out_json=None, verbose=True):
    """run() and print it; writes out_json when given. Asserts all passed (build) or just returns (baseline)."""
    rep, ok = run(folder)
    if out_json:
        Path(out_json).write_text(json.dumps(rep, indent=1))
    if verbose:
        for k, v in rep.items():
            if k != 'checks':
                print(f'  {k}: {v}', flush=True)
        for k, v in ok.items():
            print(f"  {'PASS' if v else 'FAIL'}  {k}", flush=True)
    return rep, ok


# ---- the slice read-backs (slice_check calls these with a part's layers from slice_check.device_layers) -----------------
PIN_LAID_MIN = 1.80      # the pin as laid, across X and across Y (drawn 1.90)
LOGO_OPEN_MAX = 0.02     # an engraving as laid: this much of the ink's area may be covered by lines in the first two layers
LOGO_PLAIN_MIN = 0.95    # a plain face as laid: at least this much of the old ink's area is covered


def pins_laid(layers, z0=None, z1=None):
    """The midplate's snap posts as laid (R2): in every layer from the board's rear face to its front face (z0..z1; the
    midplate itself starts at MID_REAR), the section round each post's axis is ONE piece, at least PIN_LAID_MIN across
    X and across Y. The slotted barb post laid two fingers, 1.4-1.5 across X. layers: [(zc, polygon in x, y)]."""
    from shapely.geometry import Point
    z0 = 0.05 if z0 is None else z0
    z1 = P.PCB_FRONT - 0.05 if z1 is None else z1
    fps = hw.footprints()
    rows, ok = {}, True
    for ref in P.SNAP_POSTS:
        cx, cy = fps[ref]['cad']
        ax = Point(cx, cy)
        win = ax.buffer(1.6)
        per = []
        for z, g in layers:
            if not z0 < z < z1:
                continue
            piece = g.intersection(win)
            comps = [c for c in getattr(piece, 'geoms', [piece]) if not c.is_empty and c.distance(ax) < 1.0]
            ext = [(round(c.bounds[2] - c.bounds[0], 3), round(c.bounds[3] - c.bounds[1], 3)) for c in comps]
            per.append({'z': round(z, 3), 'pieces': len(comps), 'across_x_y': ext})
        good = bool(per) and all(r['pieces'] == 1 and min(r['across_x_y'][0]) >= PIN_LAID_MIN for r in per)
        ok &= good
        xs = [e[0] for r in per for e in r['across_x_y']]
        ys = [e[1] for r in per for e in r['across_x_y']]
        rows[ref] = {'layers': len(per), 'pieces_max': max((r['pieces'] for r in per), default=0),
                     'across_x': [min(xs, default=0), max(xs, default=0)], 'across_y': [min(ys, default=0), max(ys, default=0)], 'ok': good}
    return {'what': f'midplate pins as laid: one piece, >= {PIN_LAID_MIN} across X and Y, in the board hole', 'pins': rows, 'ok': ok}


def logo_laid(layers, cfg, what, engraved, bed_high=False):
    """A logo as laid (R3), in the part's first two layers (the bed side: the lid's back, the tub's face): the share of the
    ink's area (the placed logo shrunk 0.1) that the laid lines cover. engraved: <= LOGO_OPEN_MAX (the ink is open);
    otherwise >= LOGO_PLAIN_MIN (the face is plain). layers: [(zc, polygon in x, y)]; bed_high: the print's bed is at the
    highest z (the tub prints face down), else at the lowest (the lid prints back down)."""
    ink = logo.placed(cfg).buffer(-0.1)
    first = sorted(layers, key=lambda r: -r[0] if bed_high else r[0])[:2]
    cov = [round(g.intersection(ink).area / ink.area, 4) for _, g in first]
    ok = all(c <= LOGO_OPEN_MAX for c in cov) if engraved else all(c >= LOGO_PLAIN_MIN for c in cov)
    return {'what': f'{what} as laid, layers 1-2: {"open" if engraved else "plain"} (covered share of the ink {cov})',
            'layer_z': [round(z, 3) for z, _ in first], 'ink_mm2': round(ink.area, 2), 'covered': cov, 'ok': ok}


if __name__ == '__main__':
    import sys
    d = sys.argv[1] if len(sys.argv) > 1 else str(P.OUT)
    rep, ok = check(d, out_json=sys.argv[2] if len(sys.argv) > 2 else None)
    sys.exit(0 if all(ok.values()) else 1)
