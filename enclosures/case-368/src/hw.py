"""Hardware reference for x3: Ian's 2026-09-21 Silkscreen board, trimmed, with the 3.68-inch panel.

x3 changes to the board (hardware/reference/board-trim.md has the copper audit):
  - the narrow upper extension is cut off at Y = PCB_CUT_Y (KiCad Y 62.00), just above J5; J6, H1,
    SW10 and the protection parts beside them go with it
  - power moves to SW7 (UP2): R72 and R74 fitted, R36, R73 and R62 removed; SW5 (DWN2) is left off
  - the 3.68-inch 528 x 792 panel replaces the GDEQ0426T82 (hardware/reference/panel-3p68.png)

CAD frame: mm, X = KiCad X - 44.24, Y = 148.25 - KiCad Y, Z = 0 at the PCB rear face,
+Z toward the screen, +Y toward the top edge. Components sit on the rear (-Z) side.

The board STEP takes ~8 s to read, so its solids are cached per reference designator.
Run this file directly to (re)build the cache and print the mechanical summary.
"""
import json
from functools import lru_cache
from pathlib import Path

import cadquery as cq
import variant

ROOT = Path(__file__).resolve().parents[1]
HW = ROOT / 'hardware'
CACHE = HW / 'cache'
OUT = ROOT / 'out' / variant.NAME        # out/standard or out/light-strip (x3 itself wrote out/x3)
OUT.mkdir(parents=True, exist_ok=True)

PCB_T = 1.6                    # fabricated thickness. The frozen STEP draws the substrate 1.51, so solids()
PCB_FRONT = PCB_T              # rebuilds it at 1.6 from its rear face
PCB_CUT_Y = 86.25              # x3: the board is trimmed here (KiCad Y 62.00), 1.55 above J5's body and clear
                               # of the ground via at (53.11, 85.55); the cut crosses only the narrow extension
FITTED = ('R72', 'R74')        # x3 power rework: fitted (the export has no solid for them, see solids())
REMOVED = ('R36', 'R73', 'SW5')  # removed, or left off (the CAD keeps R62's body: conservative)
REWORK_REMOVE = ('R36', 'R73', 'R62')  # the power rework's removals as written up; R62 is SW10's old series resistor

# ---- display: 3.68-inch 528 x 792 bare EPD, from the supplied drawing ------------------------
# Outline 56.24 x 86.54 (+-0.2 each), 0.87 +-0.1 thick; active area 51.84 x 77.76, 2.20 in from the top
# and the sides, so 6.58 up from the bottom edge, where the FPC leaves. The FPC's terminal is centred on
# the panel (21.87 + 12.50 / 2 = 28.12, half of 56.24), so the panel is centred in X on J2 and its tail
# runs straight into the connector. That puts the screen 0.75 left of the board's centre line.
# In Y the panel's bottom edge sits one fold radius past the FPC slot's centre line (panel.py): the tail
# folds once over the glass edge, drops straight through the slot and turns along the back.
PANEL_W, PANEL_H, PANEL_T = 56.24, 86.54, 0.87
PANEL_W_TOL, PANEL_H_TOL, PANEL_T_TOL = 0.20, 0.20, 0.10     # the drawing's +- values (an edge moves half the W/H one)
PANEL_CX = 29.247462                                          # J2's centre
PANEL_Y0 = 7.05                                               # the slot's centre line 6.40 + fold radius 0.65
PANEL_CY = PANEL_Y0 + PANEL_H / 2
PANEL_X0, PANEL_X1 = PANEL_CX - PANEL_W / 2, PANEL_CX + PANEL_W / 2      # 1.127 .. 57.367
PANEL_Y1 = PANEL_Y0 + PANEL_H                                           # 93.59
ACTIVE_W, ACTIVE_H = 51.84, 77.76
ACTIVE_CX = PANEL_CX
ACTIVE_CY = PANEL_Y1 - 2.20 - ACTIVE_H / 2                              # 2.20 below the panel's top edge


def footprints():
    """Footprints left on the trimmed board, with the x3 population."""
    out = {}
    for f in json.loads((HW / 'footprints.json').read_text())['footprints']:
        if f['cad'][1] >= PCB_CUT_Y:
            continue
        f = dict(f)
        if f['ref'] in REMOVED:
            f['dnp'] = True
        if f['ref'] in FITTED:
            f['dnp'] = False
        out[f['ref']] = f
    return out


def outline():
    return json.loads((HW / 'outline.json').read_text())


def _read_step():
    """Return {ref: [cq.Solid, ...]} for every component plus 'PCB' for the board body."""
    from OCP.STEPCAFControl import STEPCAFControl_Reader
    from OCP.TDocStd import TDocStd_Document
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.XCAFDoc import XCAFDoc_DocumentTool
    from OCP.TDF import TDF_LabelSequence, TDF_Label
    from OCP.TDataStd import TDataStd_Name
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_SOLID

    doc = TDocStd_Document(TCollection_ExtendedString('XmlOcaf'))
    rd = STEPCAFControl_Reader()
    rd.SetNameMode(True)
    rd.ReadFile(str(HW / 'board.step'))
    rd.Transfer(doc)
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())

    def name_of(label):
        n = TDataStd_Name()
        return n.Get().ToExtString() if label.FindAttribute(TDataStd_Name.GetID_s(), n) else ''

    out = {}

    def walk(label, loc, owner):
        nm = name_of(label)
        if st.IsReference_s(label):
            ref = TDF_Label()
            st.GetReferredShape_s(label, ref)
            # KiCad names component instances by reference designator; the board body gets an
            # auto-generated '=>[0:1:1:n]' instance name, so fall back to its product name.
            inst = nm if nm and not nm.startswith('=>') else name_of(ref)
            walk(ref, loc.Multiplied(st.GetLocation_s(label)), owner or inst)
            return
        if st.IsAssembly_s(label):
            kids = TDF_LabelSequence()
            st.GetComponents_s(label, kids)
            for i in range(1, kids.Length() + 1):
                walk(kids.Value(i), loc, owner)
            return
        shp = st.GetShape_s(label).Moved(loc)
        exp = TopExp_Explorer(shp, TopAbs_SOLID)
        while exp.More():
            key = 'PCB' if (not owner or owner.endswith('_PCB')) else ''.join(c for c in owner if c.isalnum() or c in '-_')
            out.setdefault(key, []).append(cq.Solid(exp.Current()))
            exp.Next()

    free = TDF_LabelSequence()
    st.GetFreeShapes(free)
    for i in range(1, free.Length() + 1):
        walk(free.Value(i), TopLoc_Location(), None)
    return out


# Parts whose footprint carries only a VRML model: KiCad's STEP export leaves them out, so they
# would be invisible to every clearance check. J7, the push-push microSD socket, is one: its
# TF-SMD_TF-PUSH.wrl, read in the footprint's frame (x 2.54u + 1.6, y -(2.54v - 5.3)) and flipped
# to the back, spans the box below. The card leaves its mouth (y 78.64) heading +y.
# x3: J7 is now the real MEM2075, read from the 2026-09-16 board export that still carried its STEP model
# (local copy in hardware/reference/j7/; J7's footprint has not moved since). Its shield stands only 1.535
# behind the board, 0.5 less than the VRML box Revs H-K used, which is what lets the battery pass over it.
# The second box is its pin row.
WRL_ONLY = {'J7': [(12.32, 28.76, 64.15, 79.15, -1.535, 0.0), (12.94, 28.14, 63.30, 64.40, -0.36, 0.0)]}
# The export models the TI SOT-23 parts under the battery 1.635 deep; TI's DBV package drawings (DBV0005A,
# DBV0006A) give 1.45 max from the seating plane, so their solids are cut back to that. J7 (1.535) then sets
# the battery's face.
DATASHEET_DEPTH = {'U1': 1.45, 'U3': 1.45, 'U9': 1.45}


@lru_cache(maxsize=1)
def solids():
    """{ref: cq.Shape (compound)} from cache; builds the cache from board.step when missing."""
    CACHE.mkdir(exist_ok=True)
    index = CACHE / 'index.json'
    if not index.exists() or index.stat().st_mtime < (HW / 'board.step').stat().st_mtime:
        comps = _read_step()
        for ref, sols in comps.items():
            cq.Compound.makeCompound(sols).exportBrep(str(CACHE / f'{ref}.brep'))
        index.write_text(json.dumps(sorted(comps)))
    full = {ref: cq.Shape.importBrep(str(CACHE / f'{ref}.brep')) for ref in json.loads(index.read_text())}
    for ref, boxes in WRL_ONLY.items():
        if ref not in full:
            full[ref] = cq.Compound.makeCompound([cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0))
                                                  for x0, x1, y0, y1, z0, z1 in boxes])
    # x3: trim the board. The cache stays the untrimmed export; only this in-memory copy is cut.
    out = {}
    keep = cq.Solid.makeBox(100, PCB_CUT_Y + 20, 40, cq.Vector(-20, -20, -20))
    for ref, shape in full.items():
        if ref in REMOVED:
            continue
        b = shape.BoundingBox()
        if ref == 'PCB':
            # rebuild the substrate at the fabricated 1.6 from its rear face, then cut it
            face = max(cq.Workplane(obj=shape).faces('<Z').vals(), key=lambda f: f.Area())
            shape = cq.Solid.extrudeLinear(face, cq.Vector(0, 0, PCB_T)).intersect(keep)
        elif b.ymin >= PCB_CUT_Y:
            continue
        elif b.ymax > PCB_CUT_Y:
            raise ValueError(f'the board cut crosses {ref}')
        if ref in DATASHEET_DEPTH:
            shape = shape.intersect(cq.Solid.makeBox(200, 200, 60, cq.Vector(-50, -50, -DATASHEET_DEPTH[ref])))
        out[ref] = shape
    # R72 (10k) and R74 (0R) are fitted for the power rework, but the export has no solid for a DNP part:
    # a 0603 envelope stands in
    fps = footprints()
    for ref in FITTED:
        if ref not in out:
            x, y = fps[ref]['cad']
            out[ref] = cq.Solid.makeBox(1.7, 1.0, 0.55, cq.Vector(x - 0.85, y - 0.5, -0.55 - 0.085))
    return out


def bounds(ref):
    b = solids()[ref].BoundingBox()
    return (b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax)


def all_hardware():
    return cq.Compound.makeCompound(list(solids().values()))


# ---- mechanically important features, measured from the frozen STEP -------------------
def switch_plunger(ref):
    """Plunger contact face: returns (x, y, z) of the face centre and the outward axis sign.

    The MJTP1117 plunger is the thin nub that stands proud of the switch body.
    """
    s = solids()[ref]
    b = s.BoundingBox()
    fp = footprints()[ref]
    rot = round(fp['rot']) % 360
    # outward direction of the plunger (in CAD frame) from footprint rotation on the rear side
    axis = {180: (0, -1), 0: (0, 1), 90: (-1, 0), 270: (1, 0)}[rot]
    if axis == (0, -1):
        face = b.ymin
    elif axis == (0, 1):
        face = b.ymax
    elif axis == (-1, 0):
        face = b.xmin
    else:
        face = b.xmax
    # find the nub by slicing a thin layer just inside the face
    probe_d = 0.3
    if axis[1]:
        y0 = face if axis[1] < 0 else face - probe_d
        cut = cq.Solid.makeBox(40, probe_d, 20, cq.Vector(b.xmin - 10, y0, b.zmin - 5))
    else:
        x0 = face if axis[0] < 0 else face - probe_d
        cut = cq.Solid.makeBox(probe_d, 40, 20, cq.Vector(x0, b.ymin - 10, b.zmin - 5))
    nub = s.intersect(cut).BoundingBox()
    cx, cy, cz = (nub.xmin + nub.xmax) / 2, (nub.ymin + nub.ymax) / 2, (nub.zmin + nub.zmax) / 2
    if axis[1]:
        cy = face
    else:
        cx = face
    return {'ref': ref, 'face': (round(cx, 4), round(cy, 4), round(cz, 4)), 'axis': axis,
            'nub': [round(v, 3) for v in (nub.xmin, nub.xmax, nub.ymin, nub.ymax, nub.zmin, nub.zmax)],
            'body': [round(v, 3) for v in (b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax)]}


BOTTOM_SWITCHES = ['SW9', 'SW8', 'SW3', 'SW2']        # left to right under the screen
LEFT_SWITCHES = ['SW7']                               # UP2: power since the x3 rework (SW5/DWN2 left off)
RIGHT_SWITCHES = ['SW1', 'SW4']                       # DWN1, UP1: the page keys
RESET = 'SW11'
SWITCH_ROLES = {'SW9': 'bottom 1', 'SW8': 'bottom 2', 'SW3': 'bottom 3', 'SW2': 'bottom 4',
                'SW7': 'power (UP2)', 'SW4': 'page up (UP1)', 'SW1': 'page down (DWN1)', 'SW11': 'reset'}


def summary():
    s = solids()
    fps = footprints()
    rep = {'pcb': [round(v, 4) for v in bounds('PCB')]}
    rep['switches'] = {r: switch_plunger(r) for r in BOTTOM_SWITCHES + LEFT_SWITCHES + RIGHT_SWITCHES + [RESET]}
    rep['components'] = {r: [round(v, 3) for v in bounds(r)] for r in s if r != 'PCB'}
    holes = {}
    for r, f in fps.items():
        if r.startswith('H'):
            holes[r] = {'cad': f['cad'], 'drill': f['pads'][0]['drill'] if f['pads'] else None,
                        'pad': f['pads'][0]['size'] if f['pads'] else None}
    rep['holes'] = holes
    b = all_hardware().BoundingBox()
    rep['envelope'] = [round(v, 3) for v in (b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax)]
    return rep


if __name__ == '__main__':
    import time
    t = time.time()
    s = solids()
    print(f'{len(s)} solid groups in {time.time() - t:.1f}s')
    rep = summary()
    (OUT / 'mechanical.json').write_text(json.dumps(rep, indent=1))
    print('PCB body', rep['pcb'])
    print('envelope', rep['envelope'])
    for r, v in rep['switches'].items():
        print(f"{r:5s} face {v['face']} axis {v['axis']} nub {v['nub']}")
    print('holes', json.dumps(rep['holes']))
    tall = sorted(rep['components'].items(), key=lambda kv: kv[1][4])[:12]
    print('deepest rear components:')
    for r, b in tall:
        print(f'  {r:6s} x[{b[0]:7.2f},{b[1]:7.2f}] y[{b[2]:7.2f},{b[3]:7.2f}] z[{b[4]:6.2f},{b[5]:6.2f}]')
    front = sorted(rep['components'].items(), key=lambda kv: -kv[1][5])[:12]
    print('front-most (leads through PCB):')
    for r, b in front:
        print(f'  {r:6s} x[{b[0]:7.2f},{b[1]:7.2f}] y[{b[2]:7.2f},{b[3]:7.2f}] z[{b[4]:6.2f},{b[5]:6.2f}]')
    # render mesh
    cq.exporters.export(cq.Workplane(obj=all_hardware()), str(OUT / 'board-trimmed.stl'), tolerance=0.03, angularTolerance=0.2)
    print('wrote board-trimmed.stl')
