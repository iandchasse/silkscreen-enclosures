"""Reusable pieces for the showcase adapters and the bundler, moved out of the Rev K showcase.py and showcase_x3.py
(the case projects' old src/ page generators, deleted 2026-09-28; in git history) and generalised: nothing here imports a
case project's modules; the adapters pass theirs in (hw, params, ...).

  text / JSON      dump, rnd, html_ascii, assert_ascii
  meshes           tess (CadQuery -> trimesh), load_stl, moved, centred_x, box_mesh, yz_prism, concat, bbox,
                   mesh_hash, file_hash
  board            category, split_switch, board_meshes (pcba_<category>, nub_<ref>, swbody_<ref>), HwMesh (fine
                   meshes of single board parts for sections), switch_envelope (a TS365ZJ-like body + plunger)
  screws           socket_head_cq (ISO 4762, both cases since 2026-10-13), pan_head_cq (ISO 7045, Rev K),
                   pan_head_mesh (plain cylinders, x3)
  sections         PLANES, cut, rings, drawing, window_of, drawing_summary
  model files      pack_glb, model_file, write_model, read_model
  downloads        zip_bytes, models_js
  bundling         split_shared

CadQuery is imported lazily (tess, split_switch, socket_head_cq, pan_head_cq), so the bundler can import this without it.
Contract: sc_contract.py and ../API.md.
"""
import base64
import hashlib
import io
import json
import math
import zipfile
from pathlib import Path

import numpy as np
import trimesh
import shapely.geometry as sg

import sc_contract as C


# ---- text / JSON -------------------------------------------------------------------------------------------
def rnd(obj, nd=4):
    """Round floats (numpy too) all through obj; -0.0 becomes 0.0; tuples become lists."""
    if isinstance(obj, dict):
        return {str(k): rnd(v, nd) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [rnd(v, nd) for v in obj]
    if isinstance(obj, np.ndarray):
        return rnd(obj.tolist(), nd)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        return round(float(obj), nd) + 0.0
    return obj


def dump(obj, path=None):
    """Compact, ASCII-only JSON (non-ASCII as \\u escapes), no NaN. Writes it when path is given."""
    s = json.dumps(obj, separators=(',', ':'), ensure_ascii=True, allow_nan=False)
    if path is not None:
        Path(path).write_text(s, encoding='ascii')
    return s


def html_ascii(s):
    """Non-ASCII characters in page text -> numeric HTML entities."""
    return ''.join(c if ord(c) < 0x80 else f'&#x{ord(c):x};' for c in s)


def assert_ascii(data, name='text'):
    b = data.encode('utf-8') if isinstance(data, str) else data
    bad = [i for i, c in enumerate(b) if c > 0x7F]
    if bad:
        i = bad[0]
        raise ValueError(f'{name}: {len(bad)} non-ASCII bytes, first at {i}: {b[max(0, i - 30):i + 10]!r}')


# ---- meshes ------------------------------------------------------------------------------------------------
def tess(shape, tol=0.02, ang=0.15):
    """CadQuery shape or Workplane -> trimesh (Rev K: 0.02 / 0.15 for printed parts, coarser for the board)."""
    import cadquery as cq
    if isinstance(shape, cq.Workplane):
        vals = shape.vals()
        shape = vals[0] if len(vals) == 1 else cq.Compound.makeCompound(vals)
    verts, tris = shape.tessellate(tol, ang)
    v = np.array([(p.x, p.y, p.z) for p in verts], dtype=np.float64)
    return trimesh.Trimesh(v, np.array(tris, dtype=np.int64), process=True)


def load_stl(path):
    m = trimesh.load(str(path), force='mesh')
    if not isinstance(m, trimesh.Trimesh) or len(m.faces) == 0:
        raise ValueError(f'{path}: no mesh')
    return m


def moved(mesh, dx=0.0, dy=0.0, dz=0.0):
    m = mesh.copy()
    m.apply_translation((dx, dy, dz))
    return m


def centred_x(mesh, xc):
    """A copy moved so X = xc lands on X = 0 (for the instanced nodes: crank_M/T, sw_T_*)."""
    return moved(mesh, -xc)


def box_mesh(x0, x1, y0, y1, z0, z1):
    m = trimesh.creation.box(extents=(x1 - x0, y1 - y0, z1 - z0))
    m.apply_translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    return m


def yz_prism(poly, x0, x1):
    """A shapely polygon in (y, z) extruded along X from x0 to x1."""
    m = trimesh.creation.extrude_polygon(poly, x1 - x0)          # in (x', y', z') = (y, z, along)
    T = np.array([[0, 0, 1, x0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float)
    m.apply_transform(T)
    return m


def concat(meshes):
    ms = [m for m in meshes if m is not None and len(m.faces)]
    return trimesh.util.concatenate(ms) if ms else None


def bbox(mesh, nd=3):
    lo, hi = mesh.bounds
    return [round(float(v), nd) + 0.0 for v in (*lo, *hi)]


def mesh_hash(mesh, nd=4):
    """Geometry hash (vertices to 1e-4 mm, faces): equal for byte-identical STLs and for identical tessellations."""
    h = hashlib.sha1()
    h.update(np.round(np.asarray(mesh.vertices, dtype=np.float64), nd).astype(np.float32).tobytes())
    h.update(np.asarray(mesh.faces, dtype=np.int32).tobytes())
    return h.hexdigest()[:16]


def file_hash(path):
    return hashlib.sha1(Path(path).read_bytes()).hexdigest()


# ---- board -------------------------------------------------------------------------------------------------
CATEGORY_426 = {'connector': ('J2', 'J3', 'J4', 'J5'), 'header': ('J6',), 'ic_prefix': ('U', 'Q', 'D', 'CR', 'F')}
CATEGORY_368 = {'connector': ('J2', 'J3', 'J4', 'J5', 'J7'), 'header': (), 'ic_prefix': ('U', 'Q', 'D', 'CR', 'F', 'L')}
BOARD_TOLS = {'pcb': (0.02, 0.3), 'passive': (0.1, 0.6), 'ic': (0.06, 0.5), 'connector': (0.05, 0.4),
              'module': (0.05, 0.4), 'usb': (0.03, 0.3), 'header': (0.05, 0.4), 'switch': (0.06, 0.5)}


def category(ref, table=CATEGORY_426):
    """A board part's chip group: pcb, switch, usb, module, connector, header, ic or passive."""
    if ref == 'PCB':
        return 'pcb'
    if ref.startswith('SW'):
        return 'switch'
    if ref == 'J1':
        return 'usb'
    if ref == 'U4':
        return 'module'
    if ref in table['connector']:
        return 'connector'
    if ref in table['header']:
        return 'header'
    if ref.startswith(table['ic_prefix']):
        return 'ic'
    return 'passive'


def split_switch(hw, ref):
    """(body, plunger) CadQuery solids of a board switch: the plunger box is hw.switch_plunger(ref)['nub']."""
    import cadquery as cq
    s = hw.solids()[ref]
    n = hw.switch_plunger(ref)['nub']
    nb = cq.Solid.makeBox(n[1] - n[0] + 0.02, n[3] - n[2] + 0.02, n[5] - n[4] + 0.02,
                          cq.Vector(n[0] - 0.01, n[2] - 0.01, n[4] - 0.01))
    return s.cut(nb), s.intersect(nb)


def board_meshes(hw, moving, bodies=(), table=CATEGORY_426, tols=None, nub_tol=(0.04, 0.5)):
    """The PCBA as pcba_<category> (merged), nub_<ref> for every ref in moving (split from its switch), and
    swbody_<ref> for refs in bodies (their switch bodies kept out of pcba_switch, so a variant can hide them).
    hw: the size's hw module (solids(), switch_plunger())."""
    tols = {**BOARD_TOLS, **(tols or {})}
    groups, out = {}, {}
    for ref, s in hw.solids().items():
        cat = category(ref, table)
        if ref in moving:
            b, n = split_switch(hw, ref)
            out[f'nub_{ref}'] = tess(n, *nub_tol)
            if ref in bodies:
                out[f'swbody_{ref}'] = tess(b, *tols['switch'])
            else:
                groups.setdefault('switch', []).append(tess(b, *tols['switch']))
            continue
        if ref in bodies:
            out[f'swbody_{ref}'] = tess(s, *tols['switch'])
            continue
        groups.setdefault(cat, []).append(tess(s, *tols[cat]))
    for k, v in groups.items():
        out[f'pcba_{k}'] = trimesh.util.concatenate(v)
    return out


class HwMesh:
    """Fine meshes of single board parts for section drawings (Rev K's hwmesh): hm('PCB'), hm('SW8', 'body'),
    hm('SW8', 'nub'). Cached."""

    def __init__(self, hw, tol=0.01, ang=0.1):
        self.hw, self.tol, self.ang, self.cache = hw, tol, ang, {}

    def __call__(self, ref, part='all'):
        key = (ref, part)
        if key not in self.cache:
            if part == 'all':
                self.cache[key] = tess(self.hw.solids()[ref], self.tol, self.ang)
            else:
                b, n = split_switch(self.hw, ref)
                self.cache[key] = tess(b if part == 'body' else n, self.tol, self.ang)
        return self.cache[key]


def switch_envelope(housing_yz, housing_half_x, nub_yz, nub_half_x):
    """A switch as two boxes at X = 0: (body, plunger). housing_yz / nub_yz: (y0, z0, y1, z1), e.g. 4.26
    keys.SWITCH['TS365']['housing'] = ((-1.65, -3.6, 6.0, 0.0), 3.65) and ['nub'] = ((-2.2, -3.05, -1.45, -1.05), 1.85).
    The plunger's -Y face is the switch's face (nominal; the page moves it +Y by plunger_in)."""
    y0, z0, y1, z1 = housing_yz
    body = box_mesh(-housing_half_x, housing_half_x, y0, y1, z0, z1)
    y0, z0, y1, z1 = nub_yz
    nub = box_mesh(-nub_half_x, nub_half_x, y0, y1, z0, z1)
    return body, nub


# ---- screws ------------------------------------------------------------------------------------------------
def socket_head_cq(x, y, z_seat, dk=3.8, k=2.0, d=2.0, length=10.0, s=1.5, t=1.0, chamfer=0.2):
    """ISO 4762 / DIN 912 socket head cap screw (M2 by default: dk 3.8, k 2.0, a 1.5 hex socket 1.0 deep) as
    CadQuery: head below its seat at z_seat (its top face, the one with the socket, toward -Z), shank up (+Z)."""
    import cadquery as cq
    head = cq.Workplane('XY').circle(dk / 2).extrude(k).translate((x, y, z_seat - k))
    head = head.faces('<Z').edges().chamfer(chamfer)
    sock = cq.Workplane('XY').polygon(6, s / math.cos(math.pi / 6)).extrude(t).translate((x, y, z_seat - k))
    head = head.cut(sock)
    shank = cq.Workplane('XY').circle(d / 2).extrude(length).translate((x, y, z_seat))
    shank = shank.faces('>Z').chamfer(0.25)
    return head.union(shank)


def pan_head_cq(x, y, z_seat, dk=4.0, k=1.6, d=2.0, length=10.0, fillet=0.55):
    """ISO 7045 pan head (M2 x 10 by default) as CadQuery: head below its seat at z_seat, shank up (+Z), a
    cross recess. Rev K's screw()."""
    import cadquery as cq
    head = cq.Workplane('XY').circle(dk / 2).extrude(k).translate((x, y, z_seat - k))
    head = head.faces('<Z').edges().fillet(fillet)
    for a in (0, 90):
        slot = cq.Workplane('XY').box(dk * 0.6, 0.5, 1.0).rotate((0, 0, 0), (0, 0, 1), a).translate((x, y, z_seat - k + 0.45))
        head = head.cut(slot)
    shank = cq.Workplane('XY').circle(d / 2).extrude(length).translate((x, y, z_seat))
    shank = shank.faces('>Z').chamfer(0.25)
    return head.union(shank)


def pan_head_mesh(x, y, z_seat, dk=3.8, k=1.3, d=2.0, length=10.0):
    """The same as plain cylinders (x3's screw()): fast, no CadQuery."""
    head = trimesh.creation.cylinder(radius=dk / 2, height=k, sections=28)
    head.apply_translation((x, y, z_seat - k / 2))
    shank = trimesh.creation.cylinder(radius=d / 2, height=length, sections=18)
    shank.apply_translation((x, y, z_seat + length / 2))
    return trimesh.util.concatenate([head, shank])


# ---- sections ----------------------------------------------------------------------------------------------
# world (x, y, z) -> the plane's (u, v, w): x -> (y, z), y -> (x, z), z -> (x, y); see sc_contract.DRAW_UV
PLANES = {
    'x': np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0], [0, 0, 0, 1]], float),
    'y': np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]], float),
    'z': np.eye(4),
}


def cut(mesh, axis, value, window):
    """Section of a mesh by an axis plane, as shapely geometry in the plane's (u, v) frame, clipped to
    window (u0, u1, v0, v1). Nested loops become holes (even-odd)."""
    i = 'xyz'.index(axis)
    origin = [0.0, 0.0, 0.0]
    origin[i] = value
    normal = [0.0, 0.0, 0.0]
    normal[i] = 1.0
    sec = mesh.section(plane_origin=origin, plane_normal=normal)
    if sec is None:
        return sg.GeometryCollection()
    T = PLANES[axis]
    polys = []
    for loop in sec.discrete:
        uv = trimesh.transform_points(loop, T)[:, :2]
        if len(uv) >= 3:
            p = sg.Polygon(uv).buffer(0)
            if not p.is_empty:
                polys.append(p)
    if not polys:
        return sg.GeometryCollection()
    geom = polys[0]
    for p in polys[1:]:
        geom = geom.symmetric_difference(p)
    u0, u1, v0, v1 = window
    return geom.intersection(sg.box(u0, v0, u1, v1))


def rings(geom, nd=3, simplify=0.004, min_area=1e-4):
    """shapely (multi)polygon -> [polygon], polygon = [exterior ring, hole rings...], ring = [[u, v], ...]."""
    out = []
    gs = getattr(geom, 'geoms', [geom])
    for g in gs:
        if g.is_empty:
            continue
        if g.geom_type in ('MultiPolygon', 'GeometryCollection'):
            out += rings(g, nd, simplify, min_area)
            continue
        if g.geom_type != 'Polygon' or g.area < min_area:
            continue
        g = g.simplify(simplify) if simplify else g
        rs = [list(g.exterior.coords)] + [list(r.coords) for r in g.interiors]
        out.append([[[round(u, nd) + 0.0, round(v, nd) + 0.0] for u, v in r] for r in rs])
    return out


def drawing(name, axis, value, window, layers, beyond=None, notes=None):
    """A section drawing (sc_contract.validate_drawing). layers: [(id, role, mesh)]; beyond: [(id, role, mesh,
    value)] cut at another plane and drawn as outlines seen beyond the section. Empty cuts are dropped; a mesh
    of None is skipped. window: [u0, u1, v0, v1] in the plane's frame (x: y/z, y: x/z, z: x/y)."""
    d = {'name': name, 'axis': axis, 'at': round(float(value), 3) + 0.0, 'window': [float(w) for w in window],
         'layers': [], 'beyond': [], 'notes': notes or {}}
    for lid, role, m in layers:
        if m is None:
            continue
        r = rings(cut(m, axis, value, window))
        if r:
            d['layers'].append({'id': lid, 'role': role, 'polys': r})
    for lid, role, m, v in beyond or []:
        if m is None:
            continue
        r = rings(cut(m, axis, v, window))
        if r:
            d['beyond'].append({'id': lid, 'role': role, 'at': round(float(v), 3) + 0.0, 'polys': r})
    return d


def window_of(meshes, axis, value, pad=1.0):
    """A window around everything the plane cuts in meshes (a start for a size's own windows)."""
    big = (-1e4, 1e4, -1e4, 1e4)
    b = None
    for m in meshes:
        g = cut(m, axis, value, big)
        if g.is_empty:
            continue
        x0, y0, x1, y1 = g.bounds
        b = [x0, x1, y0, y1] if b is None else [min(b[0], x0), max(b[1], x1), min(b[2], y0), max(b[3], y1)]
    if b is None:
        return None
    return [round(b[0] - pad, 2), round(b[1] + pad, 2), round(b[2] - pad, 2), round(b[3] + pad, 2)]


def drawing_summary(d):
    """{'layer id': (polygons, rings, points)} for logs and checks."""
    out = {}
    for kind in ('layers', 'beyond'):
        for L in d[kind]:
            out[('~' if kind == 'beyond' else '') + L['id']] = (len(L['polys']), sum(len(p) for p in L['polys']),
                                                               sum(len(r) for p in L['polys'] for r in p))
    return out


# ---- model files -------------------------------------------------------------------------------------------
def pack_glb(meshes):
    """{node name: trimesh} -> binary glTF, one node + one mesh per name, no normals (the page creases them)."""
    scene = trimesh.Scene()
    for name, m in meshes.items():
        if not C.NODE_RE.match(name):
            raise ValueError(f'bad node name {name!r}')
        scene.add_geometry(m, node_name=name, geom_name=name)
    return trimesh.exchange.gltf.export_glb(scene, include_normals=False)


def model_file(kind, size, build, meshes):
    """A core / build / extras file (sc_contract.validate_model): nodes {name: {tris, hash, bbox}} + base64 GLB."""
    glb = pack_glb(meshes)
    nodes = {n: {'tris': int(len(m.faces)), 'hash': mesh_hash(m), 'bbox': bbox(m)} for n, m in meshes.items()}
    return {'format': 'glb-base64', 'schema': C.SCHEMA, 'kind': kind, 'size': size,
            'build': build if kind == 'build' else None, 'nodes': nodes,
            'data': base64.b64encode(glb).decode('ascii')}


def write_model(path, kind, size, build, meshes):
    obj = model_file(kind, size, build, meshes)
    E = C.validate_model(obj, Path(path).name, decode=True)
    if E:
        raise ValueError('\n'.join(E))
    dump(obj, path)
    return {'bytes': Path(path).stat().st_size, 'nodes': len(meshes), 'glb_bytes': len(base64.b64decode(obj['data']))}


def read_model(src):
    """A model file (path or parsed object) -> {node name: trimesh} in the CAD frame."""
    obj = json.loads(Path(src).read_text()) if not isinstance(src, dict) else src
    scene = trimesh.load(io.BytesIO(base64.b64decode(obj['data'])), file_type='glb', force='scene')
    out = {}
    for node in scene.graph.nodes_geometry:
        T, gname = scene.graph[node]
        m = scene.geometry[gname].copy()
        m.apply_transform(T)
        out[node] = m
    return out


# ---- downloads ---------------------------------------------------------------------------------------------
def zip_bytes(entries, level=9):
    """[(name in the zip, source)] -> zip bytes (deflate). source: a path (str / Path) or the content (bytes)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED, compresslevel=level) as z:
        for arc, src in entries:
            if isinstance(src, (bytes, bytearray)):
                z.writestr(arc, bytes(src))
            else:
                z.write(str(src), arc)
    return buf.getvalue()


def models_js(zbytes, **meta):
    """models-S.js: window.SC_MODELS = {...meta, zip_bytes, b64}. The page loads it on the first download click."""
    obj = {**meta, 'zip_bytes': len(zbytes), 'b64': base64.b64encode(zbytes).decode('ascii')}
    return 'window.SC_MODELS=' + dump(obj) + ';\n'


# ---- bundling ----------------------------------------------------------------------------------------------
def split_shared(a, b):
    """Two builds' {node: hash} -> (shared, differ, only_a, only_b) name lists, sorted."""
    both = set(a) & set(b)
    shared = sorted(n for n in both if a[n] == b[n])
    differ = sorted(n for n in both if a[n] != b[n])
    return shared, differ, sorted(set(a) - set(b)), sorted(set(b) - set(a))
