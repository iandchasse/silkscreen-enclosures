"""Fit-test coupons: small slices of the real parts, printed first to qualify the fits that matter most
before committing to the full enclosure.

  coupon-chin  the hook keys' fit check (build.py exports it to print/4.26/), optional (about 15 minutes; nothing is
               chosen from it, and the drag coupon's keys 1-4 went with the drag leaf, test 2, 2026-09-30): the tub
               around SW3's key opening, with half a web each side, the chin wall with its two hook slots, the ledge,
               the slots' roof and the rail face. With one key-426: face down, the key goes in from inside with its
               hooks in the two slots, slides out with no binding and stops on both hooks, 2.4 proud and level; a firm
               thumb push from inside (about 5 N) leaves no whitening at the hooks or behind the slots.
  coupon-gate  the side gate's fit, cam and strength (SPEC2 rev 3), before the first full print: the -X wall from
               X0 to X 2.0 over y -7..+2, cut from the built tub (the gate slot and its lips, the sliver, the
               rod channel and the start of the left ring), full height, printed face down like the tub, with two
               1.0 mm feet on its outer face beyond the slot. With a gate (keys.gate, printed on its inner face):
               the gate slides in at 0.10 per side, cams a 20 mm rod piece home, and lifts out with a
               straightened paperclip. Proof test: stand it on its feet on a kitchen scale, a strip of tape over
               the rim for the lid, and press the rod piece (at most 8 mm standing out) straight down with a
               flat tool: at 2.8 kg (27 N, the 1.5 m drop) no crack and no visible set, and the gate still lifts
               out; then to 5.5 kg (54 N, SF 2 on the real print): nothing breaks.
  coupon_usb   the right wall around the USB-C port and reset pinhole, tub + lid halves.
               Hold it against the PCB edge and plug in your cables.
"""
import cadquery as cq
import params as P
from geom import box
import keys

OUT = P.OUT
COUPON_KEY = 'SW3'                   # mid-row, away from the light strip's tail by SW9 (keyed builds only: the
                                     # coupons are the bottom keys' test prints, so a chinless build has none)
BOTTOM_KEY_COUPON = ('coupon-chin',)          # printed with a key-426 (the drag coupon's keys 1-4 are gone)
GATE_COUPON = 'coupon-gate'
GATE_COUPON_BOX = dict(x=(P.X0, 2.0), y=(-7.0, 2.0), feet=((-7.0, -5.5), (0.5, 2.0)), foot=1.0)


def bottom_key_coupon(tub_shape):
    """The chin strip, cut from the built tub (so it is the tub's own geometry, its two hook slots included), in the
    CAD frame at the key's centre (X 0)."""
    xc = keys.key_x(COUPON_KEY)
    s1 = P.SLOT[1]
    x0, x1 = xc - s1 - 0.6, xc + s1 + 0.6                      # half of each web beside the opening
    strip = tub_shape.intersect(box(x0, x1, P.Y0 - 1, 0.0, P.SEAM - 1, P.Z_FRONT + 1)).translate((-xc, 0, 0)).clean()
    return {'coupon-chin': strip}


def gate_coupon(tub_shape):
    """The side gate's coupon, cut from the built tub (its own geometry, the tongue and its notch included) in the
    CAD frame, with two feet GATE_COUPON_BOX['foot'] proud of the outer face (X0) beyond the slot's ends, so standing
    on them the lips and the gate's web are 1 mm off the table. The feet run from just inside the seam chamfer to
    the face, so they print from the bed."""
    B = GATE_COUPON_BOX
    (x0, x1), (y0, y1) = B['x'], B['y']
    c = tub_shape.intersect(box(x0 - 1, x1, y0, y1, P.SEAM - P.JOINT['h'] - 1, P.Z_FRONT + 1))
    for fy0, fy1 in B['feet']:
        c = c.union(box(P.X0 - B['foot'], P.X0 + 0.2, fy0, fy1, P.SEAM + P.SEAM_CHAMFER, P.Z_FRONT))
    return c.clean()


def build():
    import tub, lid
    t = tub.build()
    lo = lid.build()
    usb_box = box(49.0, P.X1 + 1, 25.0, 52.0, P.Z_BACK - 1, P.Z_FRONT + 1)
    return {**bottom_key_coupon(t), GATE_COUPON: gate_coupon(t),
            'coupon_usb_tub': t.intersect(usb_box).clean(),
            'coupon_usb_lid': lo.intersect(usb_box).clean()}


if __name__ == '__main__':
    for name, wp in build().items():
        print(name, len(wp.solids().vals()), 'solid(s)', round(wp.val().Volume() * 1.27e-3, 2), 'g')
        cq.exporters.export(wp, str(OUT / f'{name}.stl'), tolerance=0.02, angularTolerance=0.1)
        cq.exporters.export(wp, str(OUT / f'{name}.step'))
