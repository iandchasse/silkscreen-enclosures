"""Hardware reference for the Silkscreen board: Ian's 2026-09-21 revision (H6 added, H5 moved
0.5/-0.2 mm; outline, switches and connectors identical to the Rev D-G board, commit 18d026a).

CAD frame: mm, X = KiCad X - 44.24, Y = 148.25 - KiCad Y, Z = 0 at the PCB rear face,
+Z toward the screen, +Y toward the top edge. Components sit on the rear (-Z) side.

The board STEP takes ~8 s to read, so its solids are cached per reference designator.
Run this file directly to (re)build the cache and print the mechanical summary.
"""
import json
from functools import lru_cache
from pathlib import Path

import cadquery as cq

ROOT = Path(__file__).resolve().parents[1]
HW = ROOT / 'hardware'
CACHE = HW / 'cache'

PCB_T = 1.6                    # fabricated thickness; the STEP board body is drawn 1.6 as well (checked below)
PCB_FRONT = PCB_T

# ---- display: GDEQ0426T82-FT01C drawing, centred on the board as in Ian's assembly --------
PANEL_W, PANEL_H, PANEL_T = 62.37, 105.33, 1.98
PANEL_W_TOL, PANEL_H_TOL, PANEL_T_TOL = 0.15, 0.20, 0.20
PANEL_CX, PANEL_CY = 30.0, 57.95
PANEL_X0, PANEL_X1 = PANEL_CX - PANEL_W / 2, PANEL_CX + PANEL_W / 2      # -1.185 .. 61.185
PANEL_Y0, PANEL_Y1 = PANEL_CY - PANEL_H / 2, PANEL_CY + PANEL_H / 2      # 5.285 .. 110.615
ACTIVE_W, ACTIVE_H = 55.68, 92.8
ACTIVE_CX, ACTIVE_CY = 30.0, 61.5                                       # 3.55 above panel centre


def footprints():
    return {f['ref']: f for f in json.loads((HW / 'footprints.json').read_text())['footprints']}


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
WRL_ONLY = {'J7': [(12.34, 28.49, 63.44, 78.64, -2.05, 0.0)]}


# Parts the build's board does NOT have fitted (params sets it from the build: the bottom switches for chinless, J6
# for nodev). They leave solids(), so no check sees them, and bounds() / switch_plunger() on one raise KeyError: no
# code of such a build may use their geometry. footprints() is never filtered (the midplate's lead holes follow the
# footprints, so the shared midplate stays the same).
DNP = frozenset()


def solids():
    """{ref: cq.Shape (compound)} of the fitted parts (all but DNP); the same dict every call."""
    s = _solids_all()
    return s if not DNP else _fitted(DNP)


@lru_cache(maxsize=4)
def _fitted(dnp):
    return {r: v for r, v in _solids_all().items() if r not in dnp}


@lru_cache(maxsize=1)
def _solids_all():
    """{ref: cq.Shape (compound)} of every part on the board, fitted or not, from cache; builds the cache from
    board.step when missing."""
    CACHE.mkdir(exist_ok=True)
    index = CACHE / 'index.json'
    if not index.exists() or index.stat().st_mtime < (HW / 'board.step').stat().st_mtime:
        comps = _read_step()
        for ref, sols in comps.items():
            cq.Compound.makeCompound(sols).exportBrep(str(CACHE / f'{ref}.brep'))
        index.write_text(json.dumps(sorted(comps)))
    out = {ref: cq.Shape.importBrep(str(CACHE / f'{ref}.brep')) for ref in json.loads(index.read_text())}
    for ref, boxes in WRL_ONLY.items():
        if ref not in out:
            out[ref] = cq.Compound.makeCompound([cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0))
                                                 for x0, x1, y0, y1, z0, z1 in boxes])
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
LEFT_SWITCHES = ['SW5', 'SW7']                        # lower, upper on the left edge
RIGHT_SWITCHES = ['SW1', 'SW4', 'SW10']               # lower, upper, power on the right edge
RESET = 'SW11'


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
    (HW / 'mechanical.json').write_text(json.dumps(rep, indent=1))
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
    cq.exporters.export(cq.Workplane(obj=all_hardware()), str(HW / 'board.stl'), tolerance=0.03, angularTolerance=0.2)
    print('wrote board.stl')
