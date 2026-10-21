"""The share guard of one build (pipeline.py's guard step, 2026-10-08): signatures of what the shared checks read,
so that a configuration takes a check's result from another one only when both would have read the same inputs.

    $env:SILKSCREEN_VARIANT = '<slug>'; python -B src/guard.py      -> out/.share/<slug>.json

It reads the build's parts as build_all wrote them (out/<slug>/: STL, STEP), the hardware (hw.solids, from hardware/,
which is in every step's key) and the source of the shared checks (deps.py; build.py and keys.py for their crops).
For each shared item:
  strip         (strip_check, light-strip builds) the triangles of tub/lid/midplate (+ key_SW9, crank_SW9 when keyed)
                within the margins mesh_gap clips them to round the tail meshes (both cases, every sideways shift), and
                whether each of those whole meshes is a closed volume (_overlap's manifold boolean needs every mesh to
                be one, else its result is NaN); the tub's BREP over the pocket front (STRIP_SLAB, which holds every
                crop strip_check makes of the tub: strip_crops reads them from its source at each run); the hardware
                within 3 mm of the tail
  bottom_keys   (bottom_keys_check, keyed builds) the triangles of tub/lid/midplate in the key bands' window (the
                shadows' sections: keys.shadow's own clip) and the tub's at gate_check's section (its own clip and Z,
                read from its source); the gate, keys and cranks whole (STL); the tub's and the lid's BREP over the chin
                (the rod line, the gate region, the cranks); the hardware there
  mech_sks      (mechanics' side_key_sweep, per side key) the tub's and the lid's BREP over the key's zone
                (build.side_zone, grown to the key's swept box if that reaches past it), the midplate (STL), the
                hardware there, and the key's root (TAB_ROOTS[key])
  mech_kk       (mechanics' key_hooks and key_sweep, keyed builds) the tub's triangles round the key slots
and for each one the params values its code can read (deps.params_read over the shared functions; OUT and BUILD are
labels: OUT names the folder whose files are compared here by content). So it compares what each check reads within
the regions it reads, not every byte of every part.
hw.DNP is not among the params values: params.py sets it from BOTTOM_KEYS and DEV_HEADER, and deps resolves the name to
hw.py's own `DNP = frozenset()`. The hardware lists cover it: each item lists the fitted hardware near its region
(hw_near runs this build's hw.solids()), and the checks use hardware only near those regions. Counting DEV_HEADER as a
params read would end every share across the dev axis.
The lid's BREP here is the printed lid's (lid.step: the body and its side keys as one), while the checks take the body
(lid.build(keys=False)) and the skey_* parts apart: within these regions the printed lid holds both.
Triangles are compared rotation-canonical (each one from its smallest vertex, orientation kept; rows sorted): the same
set of facets, whatever their order in the file. The order is left out on purpose (it follows the whole part's
tessellation, also away from the region); pipeline --unshared --verify is what shows that choice holds (each build's
own reports against the shared ones). BREP regions by face signatures (build._faces) of the part cropped to the
region: geometry, not tessellation.
A share is taken (pipeline.py) only between builds whose digests for that item are equal. pipeline --unshared runs
every check in every build (the audit: with --verify, each rerun is compared with what the shares made).
"""
import ast, hashlib, inspect, json, sys, textwrap, time, types
import numpy as np
from pathlib import Path
import cadquery as cq
import trimesh
import hw
import params as P
import body, build as B, deps, keys, refs, sidekeys
from geom import box

LABELS = {'OUT', 'BUILD'}           # path and message labels: what they name is compared by content here
FUNCS = {'strip': ['build.strip_check'], 'bottom_keys': ['build.bottom_keys_check'],
         'mech_sks': ['mechanics.side_key_sweep'], 'mech_kk': ['mechanics.key_hooks', 'mechanics.key_sweep']}
STRIP_SLAB = (-3.0, 60.0, 7.5, 110.5, 3.6, 5.6)        # the union of strip_check's crops of the tub (pocket front)


def h(*parts):
    m = hashlib.sha256()
    for p in parts:
        m.update(p if isinstance(p, bytes) else json.dumps(p, sort_keys=True, default=str).encode())
        m.update(b'\0')
    return m.hexdigest()[:20]


def canon(v, _seen=None):
    """A params value as a string that changes when (and only when) the value does: a function by its source, the
    values of the globals it names and its closure and defaults (as cache.canon was in 889ba26)."""
    seen = set() if _seen is None else _seen
    if v is None or isinstance(v, (bool, str, bytes)):
        return repr(v)
    if isinstance(v, int):
        return f'int:{v!r}'
    if isinstance(v, float):
        return f'float:{v.hex()}'
    if isinstance(v, (list, tuple)):
        return f'{type(v).__name__}[' + ','.join(canon(x, seen) for x in v) + ']'
    if isinstance(v, (set, frozenset)):
        return f'{type(v).__name__}[' + ','.join(sorted(canon(x, seen) for x in v)) + ']'
    if isinstance(v, dict):
        return '{' + ','.join(canon(k, seen) + ':' + canon(x, seen) for k, x in v.items()) + '}'
    if isinstance(v, Path):
        return 'path:' + v.as_posix()
    if isinstance(v, types.ModuleType):
        return 'module:' + v.__name__
    if isinstance(v, (types.BuiltinFunctionType, types.BuiltinMethodType)):
        return f'builtin:{getattr(v, "__module__", None)}.{v.__qualname__}'
    if isinstance(v, types.FunctionType):
        if id(v) in seen:
            return 'fn-again:' + v.__qualname__
        seen.add(id(v))
        names = set()

        def walk(code):
            names.update(code.co_names)
            for c in code.co_consts:
                if isinstance(c, types.CodeType):
                    walk(c)
        walk(v.__code__)
        g = v.__globals__
        return 'fn:' + h(inspect.getsource(v), {n: canon(g[n], seen) for n in sorted(names) if n in g},
                         [canon(c.cell_contents, seen) for c in (v.__closure__ or ())],
                         canon(v.__defaults__, seen), canon(v.__kwdefaults__, seen))
    if isinstance(v, np.ndarray):
        return f'ndarray:{v.dtype.str}:{v.shape}:' + h(np.ascontiguousarray(v).tobytes())
    if isinstance(v, np.generic):
        return canon(v.item(), seen)
    if hasattr(v, '_asdict'):
        return canon(dict(v._asdict()), seen)
    raise TypeError(f'guard.canon: {type(v)}')


def params_part(item, drop=()):
    names, _ = deps.params_read(FUNCS[item])
    if '*' in names:                                    # params passed on whole: never shared
        return {'*': P.BUILD}
    return {n: canon(getattr(P, n)) if hasattr(P, n) else '<absent>' for n in names if n not in LABELS and n not in drop}


# ---------------------------------------------------------------- meshes
_TRIS = {}


def tris(name):
    if name not in _TRIS:
        b = (P.OUT / f'{name}.stl').read_bytes()
        if b[:5] == b'solid' and b'facet' in b[:300]:
            raise SystemExit(f'guard: {name}.stl is an ASCII STL')
        n = int.from_bytes(b[80:84], 'little')
        a = np.frombuffer(b, dtype=np.dtype([('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')]), count=n, offset=84)
        _TRIS[name] = a['v']
    return _TRIS[name]


def crop_tris(name, bx):
    """The facets of out/<build>/<name>.stl whose box meets bx = (x0, x1, y0, y1, z0, z1), rotation-canonical."""
    v = tris(name)
    lo, hi = v.min(axis=1), v.max(axis=1)
    bl, bh = np.array(bx[0::2]), np.array(bx[1::2])
    sel = v[np.all(hi >= bl, axis=1) & np.all(lo <= bh, axis=1)]
    if len(sel):
        first = np.array([np.lexsort((t[:, 2], t[:, 1], t[:, 0]))[0] for t in sel])
        sel = np.stack([np.roll(t, -k, axis=0) for t, k in zip(sel, first)])
    rows = np.ascontiguousarray(sel.reshape(len(sel), 9))
    if len(rows):
        rows = rows[np.lexsort(rows.T[::-1])]
    return {'n': int(len(rows)), 'sha': h(rows.tobytes())}


def file_sha(name):
    return h((P.OUT / name).read_bytes())


# ---------------------------------------------------------------- BREP regions
_STEP = {}


def solid(name):
    if name not in _STEP:
        _STEP[name] = cq.importers.importStep(str(P.OUT / f'{name}.step')).val()
    return _STEP[name]


def crop_faces(name, bx):
    c = solid(name).intersect(box(*bx).val())
    return h(B._faces(c))


def hw_near(bx, grow=0.0):
    out = []
    for r, s in hw.solids().items():
        b = s.BoundingBox()
        if not (b.xmax < bx[0] - grow or b.xmin > bx[1] + grow or b.ymax < bx[2] - grow or b.ymin > bx[3] + grow
                or b.zmax < bx[4] - grow or b.zmin > bx[5] + grow):
            out.append(r)
    return sorted(out)


def grow(bx, d, dx=(0.0, 0.0)):
    return (bx[0] - d + dx[0], bx[1] + d + dx[1], bx[2] - d, bx[3] + d, bx[4] - d, bx[5] + d)


def union(a, b):
    return (min(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), max(a[3], b[3]), min(a[4], b[4]), max(a[5], b[5]))


def bbox(s):
    b = s.BoundingBox()
    return (b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax)


# ---------------------------------------------------------------- the regions against the checks' own crops
# The regions are numbers here; the crops they must hold are in the checks' own code, read from it at each run (the
# guard's key holds build.py and keys.py, so an edit there reruns this): a params or code change that moves a crop
# out of its region stops the guard, instead of leaving part of what a check reads uncompared.
def _fn_tree(fn):
    return ast.parse(textwrap.dedent(inspect.getsource(fn))).body[0]


def _line(fn, node):
    return f'{fn.__module__}.py line {fn.__code__.co_firstlineno + node.lineno - 1}'


def _eval(node, ns, fn):
    e = ast.fix_missing_locations(ast.copy_location(ast.Expression(body=node), node))
    try:
        return eval(compile(e, '<guard>', 'eval'), {'__builtins__': {}}, dict(ns))
    except Exception as ex:
        raise SystemExit(f"guard: cannot compute the crop at {_line(fn, node)} from params ({ex!r}): check the "
                         f"guard's regions against it by hand, and teach strip_crops to read it")


def strip_crops():
    """[(x0, x1, y0, y1, z0, z1)] of every crop strip_check makes of the tub's BREP (solid(name, tub, b, crop) and
    tub.intersect(box(..).val())), from its source: its assignments that need nothing but params (H, zc, px1, the
    foot's x, WALL_BAND) evaluated in order, then each crop. Any other use of the tub stops the guard."""
    fn = B.strip_check
    t = _fn_tree(fn)
    stores = {}
    for n in ast.walk(t):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            stores[n.id] = stores.get(n.id, 0) + 1
    ns = {'P': P}
    for st in t.body:
        if not isinstance(st, ast.Assign) or len(st.targets) != 1 or any(isinstance(x, ast.Call) for x in ast.walk(st.value)):
            continue
        tg = st.targets[0]
        names = [x.id for x in ast.walk(tg) if isinstance(x, ast.Name)]
        if any(stores.get(n, 0) > 1 for n in names):
            continue                                    # assigned again somewhere: not one value
        try:
            v = eval(compile(ast.fix_missing_locations(ast.Expression(body=st.value)), '<guard>', 'eval'),
                     {'__builtins__': {}}, dict(ns))
        except NameError:
            continue                                    # reads a local made from the shapes (tub, bar, ...)
        if isinstance(tg, ast.Name):
            ns[tg.id] = v
        elif isinstance(tg, ast.Tuple) and all(isinstance(x, ast.Name) for x in tg.elts):
            for x, y in zip(tg.elts, v, strict=True):
                ns[x.id] = y
    crops, uses = [], []
    for n in ast.walk(t):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'solid':
            if len(n.args) > 1 and isinstance(n.args[1], ast.Name) and n.args[1].id == 'tub':
                uses.append(n.args[1])
                crop = n.args[3] if len(n.args) > 3 else next((k.value for k in n.keywords if k.arg == 'crop'), None)
                if crop is None:
                    raise SystemExit(f'guard: strip_check measures the whole tub at {_line(fn, n)}: STRIP_SLAB no '
                                     f'longer holds what it reads')
                crops.append(_eval(crop, ns, fn))
        elif (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'intersect'
              and isinstance(n.func.value, ast.Name) and n.func.value.id == 'tub'):
            uses.append(n.func.value)
            a = n.args[0] if n.args else None
            if not (isinstance(a, ast.Call) and isinstance(a.func, ast.Attribute) and a.func.attr == 'val'
                    and isinstance(a.func.value, ast.Call) and isinstance(a.func.value.func, ast.Name)
                    and a.func.value.func.id == 'box'):
                raise SystemExit(f'guard: strip_check intersects the tub with something not a box at {_line(fn, n)}')
            crops.append(_eval(ast.copy_location(ast.Tuple(elts=a.func.value.args, ctx=ast.Load()), a), ns, fn))
    other = [n for n in ast.walk(t) if isinstance(n, ast.Name) and n.id == 'tub' and isinstance(n.ctx, ast.Load)
             and not any(n is u for u in uses)]
    if other or not crops:
        raise SystemExit(f'guard: strip_check uses the tub uncropped at {_line(fn, other[0])}' if other else
                         'guard: no crop of the tub found in strip_check')
    return crops


def shadow_clip():
    """keys.shadow's (y0, z0, y1, z1) clip: its default, which every caller in build.py, mechanics.py and keys.py
    keeps (checked)."""
    clip = inspect.signature(keys.shadow).parameters['clip'].default
    for mod in ('build', 'mechanics', 'keys'):
        t = ast.parse((Path(keys.__file__).parent / f'{mod}.py').read_text(encoding='utf-8'))
        for n in ast.walk(t):
            f = getattr(n, 'func', None)
            if isinstance(n, ast.Call) and ((isinstance(f, ast.Attribute) and f.attr == 'shadow')
                                            or (isinstance(f, ast.Name) and f.id == 'shadow')):
                if len(n.args) > 4 or any(k.arg in ('clip', None) for k in n.keywords):
                    raise SystemExit(f'guard: {mod}.py line {n.lineno} calls keys.shadow with its own clip: the '
                                     f'bottom_keys and mech_kk windows must hold it')
    return clip


def gate_section():
    """gate_check's section of the tub, ((x0, y0, x1, y1), z): its clip and Z, from its source."""
    fn = B.gate_check
    t = _fn_tree(fn)
    clips = [st.value for st in ast.walk(t) if isinstance(st, ast.Assign) and len(st.targets) == 1
             and isinstance(st.targets[0], ast.Name) and st.targets[0].id == 'clip']
    zs = {ast.literal_eval(n.args[1]) for n in ast.walk(t) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
          and n.func.id == '_zsec' and len(n.args) == 3 and isinstance(n.args[2], ast.Name) and n.args[2].id == 'clip'}
    if len(clips) != 1 or len(zs) != 1:
        raise SystemExit(f'guard: gate_check has {len(clips)} clip assignments and sections at {sorted(zs)}: read '
                         f'its section again')
    return ast.literal_eval(clips[0]), zs.pop()


def inside(a, b):
    """Box a = (x0, x1, y0, y1, z0, z1) within box b."""
    return all(a[i] >= b[i] for i in (0, 2, 4)) and all(a[i] <= b[i] for i in (1, 3, 5))


# ---------------------------------------------------------------- the items
def strip_item():
    tb = None
    for case in P.STRIP_TAIL:
        for m in refs.strip_tail(case)[0].values():
            lo, hi = m.bounds
            b = (lo[0], hi[0], lo[1], hi[1], lo[2], hi[2])
            tb = b if tb is None else union(tb, b)
    S = P.STRIP_SWEEP
    shifts = (min(S['dx'][0], 0.0, P.STRIP_DX_FIT - P.STRIP_PLACE['tol']) - 0.05,
              max(S['dx'][1], P.STRIP_DX_FIT + P.STRIP_PLACE['tol']) + 0.05)
    meshes = {'tub': 3.0, 'lid': 6.0, 'midplate': 1.5, **({'key_SW9': 3.0, 'crank_SW9': 3.0} if P.BOTTOM_KEYS else {})}
    out = [c for c in strip_crops() if not inside(c, STRIP_SLAB)]
    if out:
        raise SystemExit(f'guard: strip_check crops the tub to {out}, outside STRIP_SLAB {STRIP_SLAB}: grow it')
    parts = {'tail_box': [round(x, 6) for x in tb],
             'meshes': {n: crop_tris(n, grow(tb, m + 0.05, shifts)) for n, m in meshes.items()},
             # _overlap reads each whole mesh: trimesh's manifold boolean refuses one that is not a closed volume
             # (loaded as strip_check loads it: trimesh.load with its defaults)
             'volume': {n: bool(trimesh.load(P.OUT / f'{n}.stl').is_volume) for n in meshes},
             'tub_slab': crop_faces('tub', STRIP_SLAB),
             'hw': hw_near(grow(tb, 0.0, shifts), grow=3.0),
             'params': params_part('strip')}
    return parts


def bottom_keys_item():
    xs = [keys.key_x(r) for r in P.KEY_REFS]
    bb = keys.bands()
    # keys.shadow: sections at X across every band of every key, clipped to its clip (y -12..4, z -8..9); gate_check:
    # the tub's section at Z -1 clipped to (x -6..-1, y -7..2). Both read from their code (shadow_clip, gate_section).
    # A facet that meets the box is one that can reach the clip
    sc = shadow_clip()
    win = (min(xs) + bb[0][0], max(xs) + bb[-1][1], sc[0], sc[2], sc[1], sc[3])
    gc, gz = gate_section()
    gate_sec = (gc[0], gc[2], gc[1], gc[3], gz - 1e-6, gz + 1e-6)
    chin = (P.X0 - 1.0, P.X1 + 1.0, P.Y0 - 1.0, 6.0, P.Z_BACK - 1.0, P.Z_FRONT + 1.0)
    whole = ['gate.stl', 'midplate.stl'] + [f'{k}_{r}.stl' for k in ('key', 'crank') for r in P.KEY_REFS]
    return {'window': [round(x, 6) for x in win],
            'meshes': {n: crop_tris(n, win) for n in ('tub', 'lid', 'midplate')},
            'tub_gate_section': crop_tris('tub', gate_sec),
            'whole': {n: file_sha(n) for n in whole},
            'tub_chin': crop_faces('tub', chin), 'lid_chin': crop_faces('lid', chin),
            'hw': hw_near(chin),
            'params': params_part('bottom_keys')}


def sks_items():
    """{ref: parts} for each side key of this build."""
    pp = params_part('mech_sks', drop={'TAB_ROOTS'})
    mid = file_sha('midplate.stl')
    out = {}
    for t in body.side_tabs():
        s, a = t['side'], t['away']
        zone = B.side_zone(t)
        # the key as side_key_sweep swings it: its box at rest and at the far end of the swing
        xo = P.X1 if s > 0 else P.X0
        yf = sorted((t['flex_root'] + a * 0.3, t['flex_root'] + a * 40))
        k0 = sidekeys.build(t['ref']).intersect(
            cq.Workplane('XY').box(80, yf[1] - yf[0], 30).translate((30, (yf[0] + yf[1]) / 2, 0))).val()
        ax = xo - s * P.TAB_T / 2
        L = abs(t['face'][1] - t['flex_root'])
        kb = bbox(k0)
        for f in (1.15, -1.15):
            psi = np.degrees(s * f * P.TAB_VOID / (a * L))
            kb = union(kb, bbox(cq.Workplane(obj=k0).rotate((ax, t['flex_root'], 0), (ax, t['flex_root'], 1), psi).val()))
        kb = grow(kb, 0.2)
        inside = all(kb[i] >= zone[i] for i in (0, 2, 4)) and all(kb[i] <= zone[i] for i in (1, 3, 5))
        reg = zone if inside else union(zone, kb)
        out[t['ref']] = {'region': [round(x, 6) for x in reg], 'zone_holds_swing': inside,
                         'root': canon(P.TAB_ROOTS[t['ref']]),
                         'tub': crop_faces('tub', reg), 'lid': crop_faces('lid', reg), 'midplate': mid,
                         'hw': hw_near(reg), 'params': pp}
    return out


def kk_item():
    xs = [keys.key_x(r) for r in P.KEY_REFS]
    win = (min(xs) - 12.0, max(xs) + 12.0, P.Y0 - 3.6, 8.0, P.Z_BACK - 2.3, 10.0)
    # key_sweep's shadows (keys.shadow's clip in y, z; the bands, pushed across by the key's side play, in x) and
    # key_hooks' line (y from -12) inside the window
    sc = shadow_clip()
    reach = max(abs(x) for ab in keys.bands() for x in ab) + P.KEY_OPENING['half'] - P.KEY_CAP['half']
    need = (min(xs) - reach, max(xs) + reach, min(sc[0], -12.0), sc[2], sc[1], sc[3])
    if not inside(need, win):
        raise SystemExit(f'guard: mech_kk reads {need}, outside its window {win}: grow it')
    return {'window': [round(x, 6) for x in win], 'tub': crop_tris('tub', win), 'params': params_part('mech_kk')}


def main():
    t0 = time.time()
    rep = {'slug': P.BUILD}
    items = {}
    if P.LIGHT_STRIP:
        items['strip'] = strip_item()
    if P.BOTTOM_KEYS:
        items['bottom_keys'] = bottom_keys_item()
        items['mech_kk'] = kk_item()
    sks = sks_items()
    for k, v in items.items():
        rep[k] = {'digest': h(v), 'parts': v}
    rep['mech_sks'] = {'digest': {r: h(v) for r, v in sks.items()}, 'parts': sks}
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else P.OUT.parent / '.share' / f'{P.BUILD}.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=1, sort_keys=True))
    print(f"guard {P.BUILD}: " + ', '.join(f'{k} {v["digest"]}' for k, v in rep.items() if k not in ('slug', 'mech_sks'))
          + f"; side keys {rep['mech_sks']['digest']} ({time.time() - t0:.0f}s)", flush=True)


if __name__ == '__main__':
    main()
