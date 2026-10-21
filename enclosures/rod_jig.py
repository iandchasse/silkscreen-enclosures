"""Rod jig for the bottom keys' rod (1.75 mm PLA filament, cut to 63.25 in both case sizes).

A warm piece of filament lies in the straight groove and cools there, straight; then the printer scraper's
razor blade goes down the two slots and cuts it to length with both ends square. The slots are one blade
thickness further apart than the rod, so the piece between the two cuts is ROD_CUT. A window at mid-length
lets the blade's corner get under the rod to lift it out.

    print: groove up, flat on the bed, no supports, no brim (9 minutes, 3.9 g on the CC2 profile)
    use:   cut about 80 mm of filament; warm it until it goes limp (about 10 s in water just off the boil, or
           5 min in the jig on the bed at 60 C); press it into the groove and let it cool (half a minute);
           cut at both slots while it is still warm; lift it out; taper one end in a pencil sharpener.

Writes the repo's print/rod-jig.stl (print pose) and print/rod-jig.step; make_plates.py puts the STL on plate 3 of
both plate files, so rerun it after this. Run from this folder (enclosures/) with a Python 3.11 virtual environment made from
either case's requirements.txt:

    python -B rod_jig.py
"""
from pathlib import Path

import cadquery as cq

ROD_CUT = 63.25            # both projects' params.ROD_CUT: change the three together
BLADE_T = 0.25             # a printer scraper's razor blade
PITCH = ROD_CUT + BLADE_T  # slot centre to slot centre: the piece between the blades is ROD_CUT
SLOT_W = 0.50              # guides the blade square; the cut lands within +-0.125 of the slot centre
SLOT_LEAD = 0.30           # 45-degree lead-in at the top of each slot wall
L, W, H = 86.0, 12.0, 5.0  # the bar
GROOVE_W = 1.95            # prints about 1.85-1.9: a slip fit for 1.72-1.78 filament
GROOVE_D = 2.20            # the rod sits wholly below the top
GROOVE_LEAD = 0.40         # 45 degrees on the groove's top edges, to press the rod in
SLOT_BELOW = 0.80          # the slots run this far under the groove floor, so the blade goes right through
WINDOW = dict(len=6.0, w=4.5, below=1.0)   # the lift window at mid-length
CORNER_R = 1.0

OUT = Path(__file__).resolve().parents[1] / 'print'      # the repo's print/


def jig():
    floor = H - GROOVE_D
    body = cq.Workplane('XY').box(L, W, H, centered=(False, True, False)).edges('|Z').fillet(CORNER_R)
    # the groove, open at both ends, with its lead-in
    groove = cq.Workplane('YZ').polyline([(-GROOVE_W / 2, floor), (GROOVE_W / 2, floor),
                                          (GROOVE_W / 2, H - GROOVE_LEAD), (GROOVE_W / 2 + GROOVE_LEAD, H + 0.01),
                                          (-GROOVE_W / 2 - GROOVE_LEAD, H + 0.01), (-GROOVE_W / 2, H - GROOVE_LEAD)]
                                         ).close().extrude(L + 2).translate((-1, 0, 0))
    body = body.cut(groove)
    # two blade slots across the whole width, each with a lead-in
    x1 = (L - PITCH) / 2
    for xc in (x1, x1 + PITCH):
        slot = cq.Workplane('XZ').polyline([(xc - SLOT_W / 2, floor - SLOT_BELOW), (xc + SLOT_W / 2, floor - SLOT_BELOW),
                                            (xc + SLOT_W / 2, H - SLOT_LEAD), (xc + SLOT_W / 2 + SLOT_LEAD, H + 0.01),
                                            (xc - SLOT_W / 2 - SLOT_LEAD, H + 0.01), (xc - SLOT_W / 2, H - SLOT_LEAD)]
                                           ).close().extrude(W / 2 + 1, both=True)
        body = body.cut(slot)
    # the lift window: wider and deeper than the groove over a short length at the middle
    win = cq.Workplane('XY').box(WINDOW['len'], WINDOW['w'], GROOVE_D + WINDOW['below'] + 0.01,
                                 centered=(True, True, False)).translate((L / 2, 0, floor - WINDOW['below']))
    return body.cut(win)


if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    j = jig().translate((0, W / 2, 0))     # min corner at the origin, as plates.py writes the case parts
    cq.exporters.export(j, str(OUT / 'rod-jig.stl'), tolerance=0.01, angularTolerance=0.1)
    cq.exporters.export(j, str(OUT / 'rod-jig.step'))
    x1 = (L - PITCH) / 2
    print(f'rod-jig: {L} x {W} x {H} mm, volume {j.val().Volume():.0f} mm3 (about {j.val().Volume() * 1.24e-3:.1f} g PLA); '
          f'slots at x {x1:.3f} and {x1 + PITCH:.3f} (pitch {PITCH}), groove {GROOVE_W} x {GROOVE_D} -> {OUT}')
