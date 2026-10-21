"""Slice every per-configuration project (out/configs/<slug>.3mf, ../make_plates.py configs: OrcaSlicer's generic
presets, what the website serves; --printer cc2: out/configs-cc2/, the Elegoo CC2 ones) as a user's OrcaSlicer
opens it, and read the G-code back (2026-10-07; generic 2026-10-11). The CLI loads the project with its own settings and slices every
plate (--slice 0; memoised by the file's bytes, cache.orca_run), and for each configuration:
  - Orca exits 0 and writes one G-code per plate; its grams, layers and time are recorded;
  - every extrusion lies on an object of that plate (within its box on the bed + REACH: a raft's first layer reaches
    2.5 past the part), and every object prints;
  - supports (Orca's support roles) only where the project asks for them: under every bottom key and crank (its
    raft, no higher than RAFT_TOP) and under the lid's side keys, inside the lid's support enforcers, one per side key
    the configuration has (5, or 3 for a side-key layout: variants.SIDE_SETS, as index.json lists them; the 3.68's 3)
    and each of them used; nowhere else;
  - every bottom key prints its height in LAYER layers over its raft (2026-10-11: 50, as slice_check's key fit has
    it on both cases), read from the library's part size;
  - the lid's side keys print on what is under them (2026-10-12, after the 3.68 lid's keys "really messed up" on
    Ian's printer: as sliced with the CC2 presets no key had a first layer, so each started 0.2 over the bed and was
    tied to nothing): in each side key's zone (index.json's 'key_zones', make_plates.side_key_zones: the key, its slot
    and the lid round it), every layer of the lid, its lines thickened to their widths, must stand on the lid's layer
    below or on support lines just under it (each piece at least KEY_STAND of it), and reach no further than KEY_REACH
    past that (Ian's no-support rule, slice_check.OVERHANG_REACH_MAX) but for KEY_OVER_AIR_MM2 a layer (line ends
    at the nub gusset's corners). So a face over air passes only with support under it or at 45 degrees or steeper;
    and each piece of the support there stands on the support under it (it is on the bed only);
  - every plate's job starts on the skirt (2026-10-13, make_plates.SKIRT; job_start): its first line after the start
    G-code is the skirt's, not a line in a side key's zone. In the 3.68 lid job Ian printed, SW7's hinge support was
    the first line, straight off the purge line. And once a run, the lid printed alone (the first configuration's
    project with every other object made unprintable, plate 1; lid_alone): the reprint-the-lid job, which starts the
    same way, and its side keys read as on the full plate.
--size 368 (2026-10-11): the 3.68's one project (enclosures/case-368/out/configs/, make_plates.py configs --size 368).
Writes slice-report.json in that folder (an entry for a configuration not sliced in this run stays while its 3MF is the
one it was made from) and exits 1 when any configuration fails.

    python -B src/configs_slice.py [--builds a,b,...] [--printer generic|cc2] [--size 426|368]
                                     (default: every configuration in out/configs/index.json, the generic projects)
"""
import concurrent.futures, hashlib, json, re, sys, time
from pathlib import Path
import cache

ORCA = Path(r'C:\Program Files\OrcaSlicer\orca-slicer.exe')     # slice_check.ORCA
DIRS = {'generic': 'configs', 'cc2': 'configs-cc2'}    # make_plates.PRINTERS' folders
CONFIGS = cache.ROOT / 'out' / DIRS['generic']         # main() points these at --printer's (and --size's) folder
SLICE = CONFIGS / 'slice'
SUPPORT = ('Support', 'Support interface', 'Support transition')   # Orca's roles in rafts and supports
NOT_PART = ('Custom', 'Skirt')      # the start G-code's purge line and the skirt (make_plates.SKIRT): on no object
                                    # (no brim in these projects)
REACH = 3.0                         # mm: an object's extrusion past its box (a raft's first layer: 2.5)
ENFORCER_REACH = 2.0                # mm: the lid's support past its enforcer's box: Orca draws its grid up to 0.7
                                    # (x) and 1.35 (y) past it (line centres, 2026-10-07); the next key is 18 away
RAFT_TOP = 0.55                     # mm: a raft's two layers are at z 0.2 and 0.5 (make_plates.RAFT)
LAYER = 0.2                         # mm: the projects' layer height (a key of 10.00 is 50 layers)
MIN_FREE = 8e9                      # bytes of commit charge free before an OrcaSlicer starts (pipeline --mem-floor's
                                    # default; this wait is its own, whatever --mem-floor a run is given)
KEY_REACH = 0.5                     # mm: a layer's lines past the layer below or its support (a 45-degree face: 0.2)
KEY_OVER_AIR_MM2 = 0.25             # mm2 a layer past KEY_REACH in a key's zone: line ends at the nub gusset's corners
                                    # (the 3.68's 0.15, the 4.26 plate file's 0.14); a key's lost first layer: 7-9
KEY_STAND = 0.2                     # a piece of a layer floats when less than this share of it lies on what is under it
KEY_SUP_BELOW = 0.65                # mm: support lines this far under a layer's top hold it (0.2 of air and a layer;
                                    # the generic projects lay the support in 0.3 layers of its own)
KEY_BED_W = 0.68                    # mm: a side key's first layer is at least this wide (two beads side by side: the
                                    # teardrop's 0.83, the square's 1.70; one 0.45-0.5 bead, or its double pass, reads
                                    # 0.48-0.52), over KEY_BED_SHARE of its length. 2026-10-20: 0.75 -> 0.68, midway
                                    # between the round (<= 0.523) and the teardrop (>= 0.818)
KEY_BED_SHARE = 0.95                # of the key's length from the hinge's end to the free end, sampled every 0.25
KEY_BED_L2 = 0.60                   # share of the second layer (in the base box) that lies on the first (2026-10-19: Ian's
                                    # keys print scraggly in their free half; as sliced each stood on one 0.52 bead and
                                    # its second layer was 42 % on it. With TAB_BASE 'teardrop' (2026-10-20): 0.83 wide,
                                    # 76 %; 'square': 1.70, 94 %)


def read_gcode(path, objects):
    """Per object (by box on the bed): extrusion (mm of E) of the part and of the support roles, the support's top z
    and, for the lid, the support per enforcer; plus what lies on no object. The G-code's X, Y are the bed's less the
    extruder offset (the CC2 profile's 0x1.5: Orca moves every coordinate 1.5 down in Y; the generic printer's 0x0),
    read from its footer."""
    t = path.read_text(errors='ignore')
    m = re.search(r'^; extruder_offset = (-?[\d.]+)x(-?[\d.]+)', t, re.M)
    ox, oy = (float(m.group(1)), float(m.group(2))) if m else (0.0, 0.0)
    head = {'extruder_offset': [ox, oy]}
    for key, pat in {'grams': r'total filament used \[g\] = ([\d.]+)', 'layers': r'total layers count = (\d+)',
                     'time': r'estimated printing time \(normal mode\) = (.+)'}.items():
        m = re.search(pat, t)
        head[key] = m.group(1).strip() if m else None
    per = [{'part_E': 0.0, 'support_E': 0.0, 'support_z_max': None, 'enforcer_E': [0.0] * len(o['enforcers']),
            'enforcer_reach': [0.0] * len(o['enforcers'])} for o in objects]
    zs = [set() for _ in objects]                       # the z of every layer the part itself extrudes in
    stray = {'moves': 0, 'E': 0.0, 'where': []}
    off_enf = {'moves': 0, 'E': 0.0}
    role, z, x, y, rel = None, 0.0, 0.0, 0.0, True
    for line in t.splitlines():
        if line.startswith(';TYPE:'):
            role = line[6:].strip()
        elif line.startswith(';Z:'):
            z = float(line[3:])
        elif line.startswith('M83'):
            rel = True
        elif line.startswith('M82'):
            rel = False
        elif line.startswith(('G1 ', 'G0 ', 'G2 ', 'G3 ')):
            v = {q[0]: float(q[1:]) for q in line.split(';')[0].split()[1:] if q[0] in 'XYE' and len(q) > 1}
            nx, ny = v.get('X', x), v.get('Y', y)
            e = v.get('E', 0.0)
            if not rel:
                raise SystemExit(f'{path}: absolute E (M82): not read here')
            if (line[:2] in ('G1', 'G2', 'G3') and e > 0 and (nx, ny) != (x, y) and role is not None
                    and role not in NOT_PART):
                # the object whose box is nearest the move's end on the bed (>= 5 mm apart: make_plates.GAP)
                bx, by = nx + ox, ny + oy
                d = [max(o['box'][0] - bx, bx - o['box'][2], o['box'][1] - by, by - o['box'][3], 0.0) for o in objects]
                i = min(range(len(objects)), key=d.__getitem__)
                if d[i] > REACH:
                    stray['moves'] += 1
                    stray['E'] += e
                    if len(stray['where']) < 5:
                        stray['where'].append([round(bx, 2), round(by, 2), round(z, 2), role])
                elif role in SUPPORT:
                    p = per[i]
                    p['support_E'] += e
                    p['support_z_max'] = z if p['support_z_max'] is None else max(p['support_z_max'], z)
                    if objects[i]['enforcers']:
                        # the enforcer nearest the move, and how far past its box the move ends
                        de = [max(b[0] - bx, bx - b[3], b[1] - by, by - b[4], 0.0)
                              for b in (q['box'] for q in objects[i]['enforcers'])]
                        j = min(range(len(de)), key=de.__getitem__)
                        if de[j] <= ENFORCER_REACH:
                            p['enforcer_E'][j] += e
                            p['enforcer_reach'][j] = max(p['enforcer_reach'][j], de[j])
                        else:
                            off_enf['moves'] += 1
                            off_enf['E'] += e
                else:
                    per[i]['part_E'] += e
                    zs[i].add(round(z, 3))
            x, y = nx, ny
    for p, s in zip(per, zs):
        p['part_layers'] = len(s)
        p['part_z'] = [min(s), max(s)] if s else None
    return head, per, stray, off_enf


def side_key_lines(path, zones, pad=1.0):
    """[{z: {'part': [(a, b, w)], 'sup': [(a, b, w)]}}], one per zone (index.json's 'key_zones' boxes, bed x0 y0 x1
    y1): every extrusion of the G-code that comes within pad of the zone, up to its 'top', with its ;WIDTH, in bed
    coordinates (the extruder offset added back, as read_gcode does)."""
    t = path.read_text(errors='ignore')
    m = re.search(r'^; extruder_offset = (-?[\d.]+)x(-?[\d.]+)', t, re.M)
    ox, oy = (float(m.group(1)), float(m.group(2))) if m else (0.0, 0.0)
    boxes = [(q['box'][0] - pad, q['box'][1] - pad, q['box'][2] + pad, q['box'][3] + pad, q['top'] + 0.5)
             for q in zones]
    out = [{} for _ in zones]
    role, z, w, x, y = None, 0.0, 0.42, 0.0, 0.0
    for line in t.splitlines():
        if line.startswith(';TYPE:'):
            role = line[6:].strip()
        elif line.startswith(';Z:'):
            z = float(line[3:])
        elif line.startswith(';WIDTH:'):
            w = float(line[7:])
        elif line.startswith(('G1 ', 'G0 ')):
            v = {q[0]: float(q[1:]) for q in line.split(';')[0].split()[1:] if q[0] in 'XYE' and len(q) > 1}
            nx, ny = v.get('X', x), v.get('Y', y)
            if (line[:2] == 'G1' and v.get('E', 0.0) > 0 and (nx, ny) != (x, y) and role is not None
                    and role not in NOT_PART):
                a, b = (x + ox, y + oy), (nx + ox, ny + oy)
                for i, (x0, y0, x1, y1, top) in enumerate(boxes):
                    if (z <= top and max(a[0], b[0]) >= x0 and min(a[0], b[0]) <= x1 and max(a[1], b[1]) >= y0
                            and min(a[1], b[1]) <= y1):
                        d = out[i].setdefault(round(z, 3), {'part': [], 'sup': []})
                        d['sup' if role in SUPPORT else 'part'].append((a, b, w))
            x, y = nx, ny
    return out


def side_key_read(layers, zone):
    """One side key's zone, layer by layer (side_key_lines): each layer of the lid's lines, thickened to their widths
    (round ends) and cut to the zone, against what is under it: the lid's own layer below (support may lie in layers of
    its own) and the support lines up to KEY_SUP_BELOW under it. -> the pieces that float (less than KEY_STAND of
    them on it), and per layer the area further than KEY_REACH from it and the furthest point. The support in the
    zone is read the same way: each piece of it stands on the support layer below (it is on the bed only), or is its
    first."""
    import numpy as np
    import shapely
    from shapely.geometry import box
    x0, y0, x1, y1 = zone['box']
    clip, near = box(x0, y0, x1, y1), box(x0 - 1, y0 - 1, x1 + 1, y1 + 1)

    def solid(lines):
        lines = [(a, b, w) for a, b, w in lines if a != b]
        if not lines:
            return shapely.Polygon()
        segs = shapely.linestrings(np.array([(a, b) for a, b, _ in lines]))
        g = shapely.buffer(segs, np.array([w / 2 for *_, w in lines]), quad_segs=4)
        return shapely.union_all(g).intersection(near)
    zs = sorted(layers)
    part = {z: solid(layers[z]['part']) for z in zs if layers[z]['part']}
    sup = {z: solid(layers[z]['sup']) for z in zs if layers[z]['sup']}
    floating, over, reach, own = [], [], (0.0, None), []
    for z in zs:
        if z not in part:
            continue
        g = part[z].intersection(clip)
        if own and not g.is_empty:
            under = shapely.union_all([part[own[-1]], *(s for q, s in sup.items() if 0 < z - q < KEY_SUP_BELOW)])
            for q in getattr(g, 'geoms', [g]):
                if q.area < 0.005:
                    continue
                if q.intersection(under).area < KEY_STAND * q.area:
                    floating.append({'z': z, 'mm2': round(q.area, 3),
                                     'at': [round(c, 2) for c in q.centroid.coords[0]]})
                pts = np.array(q.exterior.segmentize(0.05).coords)
                d = shapely.distance(shapely.points(pts), under) if not under.is_empty else np.full(len(pts), 99.0)
                j = int(np.argmax(d))
                if d[j] > reach[0]:
                    reach = (float(d[j]), {'z': z, 'at': [round(float(c), 2) for c in pts[j]]})
            a = g.difference(under.buffer(KEY_REACH, quad_segs=4)).area if not under.is_empty else g.area
            if a > 0.01:
                over.append({'z': z, 'mm2': round(a, 3)})
        own.append(z)
    # the support: on the bed or on the support under it (a piece that starts in mid-air, or on the lid, prints a
    # loose strand by the key; 2026-10-12: with the 3.68's hinge notch 1.26 tall, Orca laid one beside each root)
    sup_floating, below = [], None
    for z in sorted(sup):
        g = sup[z].intersection(clip)
        for q in getattr(g, 'geoms', [g]):
            if q.area < 0.005:
                continue
            if (below is None and z > zs[0] + 1e-6) or (below is not None
                                                          and q.intersection(sup[below]).area < KEY_STAND * q.area):
                sup_floating.append({'z': z, 'mm2': round(q.area, 3),
                                     'at': [round(c, 2) for c in q.centroid.coords[0]]})
        below = z
    worst = max((o['mm2'] for o in over), default=0.0)
    return {'layers': len(own), 'floating': floating, 'over_air': over, 'over_air_mm2_max': worst,
            'reach_max': round(reach[0], 3), 'reach_at': reach[1], 'support_layers': len(sup),
            'support_floating': sup_floating,
            'ok': bool(own) and not floating and worst <= KEY_OVER_AIR_MM2 and not sup_floating}


def side_key_reads(path, zones):
    """{key: side_key_read} for a plate's G-code and its lid's side-key zones, memoised (cache.memo: 3 s a lid) by the
    G-code's bytes, the zones and this read-back's code and limits."""
    import inspect
    parts = [cache.sha(path.read_bytes()), zones, [KEY_REACH, KEY_OVER_AIR_MM2, KEY_STAND, KEY_SUP_BELOW],
             inspect.getsource(side_key_lines), inspect.getsource(side_key_read)]
    return cache.memo('side-keys', parts, lambda: {q['name']: side_key_read(lines, q)
                                                   for q, lines in zip(zones, side_key_lines(path, zones))})


def side_key_base(layers, base):
    """What a side key stands on at the bed (2026-10-19). layers is side_key_lines' output for the key's zone, base the
    zone's 'base' box (make_plates.side_key_bases, bed x0 y0 x1 y1: from the hinge's end to the free end, from 0.15 past
    the case face to 0.1 past the key's inner bed edge). -> the first layer's width over the key's length (its lines
    thickened to their widths, cut to the box, sampled every 0.25 along the key: median, and the share at least
    KEY_BED_W) and the share of the second layer in the box that lies on the first; ok when the share is at least
    KEY_BED_SHARE and the second layer stands at least KEY_BED_L2 on the first. Support lines do not count."""
    import numpy as np
    import shapely
    from shapely.geometry import box
    if not base:
        return {'ok': False, 'why': 'no base box', 'width_median': 0.0, 'width_ok_share': 0.0, 'layer2_on_1': 0.0}
    x0, y0, x1, y1 = base
    clip = box(x0, y0, x1, y1)
    along_y = (y1 - y0) >= (x1 - x0)

    def solid(lines):
        lines = [(a, b, w) for a, b, w in lines if a != b]
        if not lines:
            return shapely.Polygon()
        segs = shapely.linestrings(np.array([(a, b) for a, b, _ in lines]))
        return shapely.union_all(shapely.buffer(segs, np.array([w / 2 for *_, w in lines]), quad_segs=4)).intersection(clip)
    zs = sorted(z for z in layers if layers[z]['part'])
    if len(zs) < 2:
        return {'ok': False, 'why': 'no layers', 'width_median': 0.0, 'width_ok_share': 0.0, 'layer2_on_1': 0.0}
    g1, g2 = solid(layers[zs[0]]['part']), solid(layers[zs[1]]['part'])
    n = int((y1 - y0 if along_y else x1 - x0) / 0.25)
    ws = []
    for i in range(n):
        c = (y0 if along_y else x0) + (i + 0.5) * 0.25
        cut = box(x0, c - 0.005, x1, c + 0.005) if along_y else box(c - 0.005, y0, c + 0.005, y1)
        ws.append(g1.intersection(cut).area / 0.01)
    ws = np.array(ws)
    share = float((ws >= KEY_BED_W).mean()) if n else 0.0
    on = g2.intersection(g1).area / g2.area if g2.area > 0 else 0.0
    return {'z': [zs[0], zs[1]], 'width_median': round(float(np.median(ws)), 3) if n else 0.0,
            'width_ok_share': round(share, 3), 'layer2_on_1': round(on, 3),
            'ok': bool(n and share >= KEY_BED_SHARE and on >= KEY_BED_L2)}


def side_key_bases(path, zones):
    """{key: side_key_base} for a plate's G-code and its lid's side-key zones (a zone without a 'base' box fails),
    memoised like side_key_reads by the G-code's bytes, the zones and this read-back's code and limits."""
    import inspect
    parts = [cache.sha(path.read_bytes()), zones, [KEY_BED_W, KEY_BED_SHARE, KEY_BED_L2],
             inspect.getsource(side_key_lines), inspect.getsource(side_key_base)]
    return cache.memo('side-key-bases', parts, lambda: {q['name']: side_key_base(lines, q.get('base'))
                                                        for q, lines in zip(zones, side_key_lines(path, zones))})


def side_key_base_row(reads):
    """The verdict text and value for a side_key_bases read (check() and lid_alone())."""
    return (f"the lid's side keys ({len(reads)}) stand on a base >= {KEY_BED_W} mm wide over >= {KEY_BED_SHARE:.0%} of "
            f"their length, their second layer >= {KEY_BED_L2:.0%} on it",
            {k: {'width_median': v['width_median'], 'width_ok_share': v['width_ok_share'],
                 'layer2_on_1': v['layer2_on_1'], **({'why': v['why']} if 'why' in v else {})}
             for k, v in reads.items()})


def job_start(path, zones):
    """Where the job starts (2026-10-13): its first extruded line after the start G-code (role, where on the bed, z),
    and the first line of the part or its support that comes within the zones (a lid's 'key_zones', bed boxes; [] on a
    plate without the lid; the skirt may pass through a zone's margin, 3 mm off the lid's first layer), with the mm of
    line laid before it. ok: the first line is the skirt's, so no side key's line or support comes first."""
    import math
    t = path.read_text(errors='ignore')
    m = re.search(r'^; extruder_offset = (-?[\d.]+)x(-?[\d.]+)', t, re.M)
    ox, oy = (float(m.group(1)), float(m.group(2))) if m else (0.0, 0.0)
    role, z, x, y = None, 0.0, 0.0, 0.0
    first, laid = None, 0.0
    for line in t.splitlines():
        if line.startswith(';TYPE:'):
            role = line[6:].strip()
        elif line.startswith(';Z:'):
            z = float(line[3:])
        elif line.startswith(('G1 ', 'G0 ')):
            v = {q[0]: float(q[1:]) for q in line.split(';')[0].split()[1:] if q[0] in 'XYE' and len(q) > 1}
            nx, ny = v.get('X', x), v.get('Y', y)
            if line[:2] == 'G1' and v.get('E', 0.0) > 0 and (nx, ny) != (x, y) and role not in (None, 'Custom'):
                a, b = (x + ox, y + oy), (nx + ox, ny + oy)
                if first is None:
                    first = {'role': role, 'at': [round(a[0], 2), round(a[1], 2)], 'z': round(z, 3)}
                hit = next((q['name'] for q in zones
                            if max(a[0], b[0]) >= q['box'][0] and min(a[0], b[0]) <= q['box'][2]
                            and max(a[1], b[1]) >= q['box'][1] and min(a[1], b[1]) <= q['box'][3]), None)
                if hit and role != 'Skirt':
                    return {'first': first, 'first_in_key_zone': {'key': hit, 'role': role, 'z': round(z, 3)},
                            'laid_before_mm': round(laid, 1),
                            'ok': first['role'] == 'Skirt' and laid > 0}
                laid += math.dist(a, b)
            x, y = nx, ny
    return {'first': first, 'first_in_key_zone': None, 'laid_before_mm': round(laid, 1),
            'ok': first is not None and first['role'] == 'Skirt'}


def check(slug, entry, dest, r):
    """The verdicts for one configuration's slice."""
    rows, plates = [], []
    # each object's part and its size (the recipe lists the objects in index.json's order)
    rec = json.loads((CONFIGS / 'recipes' / f'{slug}.json').read_text())
    lib = json.loads((CONFIGS / 'library' / 'index.json').read_text())['parts']
    size = [[lib[o['part']]['size_mm'] for o in pl['objects']] for pl in rec['plates']]

    def verdict(what, ok, value=None):
        rows.append({'check': what, 'ok': bool(ok), **({'value': value} if value is not None else {})})

    verdict('OrcaSlicer exits 0', r.returncode == 0, r.returncode)
    lids = [o for pl in entry['plates'] for o in pl['objects'] if o['enforcers']]
    keys = entry['side_keys']
    have = sorted(q['name'].split()[2] for o in lids for q in o['enforcers'])    # 'support enforcer SW1 hinge'
    verdict(f'the lid has one support enforcer per side key it has ({len(keys)}: {", ".join(keys)}), no other',
            len(lids) == 1 and have == sorted(keys), have)
    for n, pl in enumerate(entry['plates'], start=1):
        g = dest / f'plate_{n}.gcode'
        p = {'name': pl['name'], 'gcode': (g.relative_to(CONFIGS).as_posix() if g.is_relative_to(CONFIGS) else str(g))
             if g.exists() else None}
        plates.append(p)
        verdict(f'plate {n} sliced ({pl["name"]})', g.exists())
        if not g.exists():
            continue
        head, per, stray, off_enf = read_gcode(g, pl['objects'])
        p.update(head)
        p['objects'] = {}
        for o, q in zip(pl['objects'], per):
            p['objects'][o['name']] = {k: (round(v, 3) if isinstance(v, float) else [round(w, 3) for w in v]
                                           if isinstance(v, list) else v) for k, v in q.items()}
        verdict(f'plate {n}: every extrusion lies on an object (within {REACH} mm of its box)', stray['moves'] == 0,
                {k: (round(v, 3) if isinstance(v, float) else v) for k, v in stray.items()})
        verdict(f'plate {n}: every object prints', all(q['part_E'] > 0 for q in per),
                [o['name'] for o, q in zip(pl['objects'], per) if q['part_E'] <= 0])
        js = p['job_start'] = job_start(g, [q for o in pl['objects'] for q in o.get('key_zones', [])])
        verdict(f'plate {n}: the job starts on the skirt, not in a side key\'s zone', js['ok'], js)
        bk = [(o, q, round(sz[2] / LAYER)) for o, q, sz in zip(pl['objects'], per, size[n - 1])
              if o['role'].startswith('key-')]
        if bk:
            verdict(f'plate {n}: every bottom key ({len(bk)}) prints its height in {LAYER} layers over its raft',
                    all(q['part_layers'] == k for _, q, k in bk),
                    {o['name']: [q['part_layers'], k, q['part_z']] for o, q, k in bk})
        rafts = [(o, q) for o, q in zip(pl['objects'], per) if o['raft']]
        if rafts:
            verdict(f'plate {n}: a raft under every key and crank ({len(rafts)}), no higher than {RAFT_TOP}',
                    all(q['support_E'] > 0 and q['support_z_max'] <= RAFT_TOP for _, q in rafts),
                    {o['name']: [round(q['support_E'], 3), q['support_z_max']] for o, q in rafts})
        for o, q in zip(pl['objects'], per):
            if o['enforcers']:
                verdict(f'plate {n}: the {o["name"]}\'s supports all inside its {len(o["enforcers"])} enforcers',
                        off_enf['moves'] == 0, {k: round(v, 3) for k, v in off_enf.items()})
                verdict(f'plate {n}: every enforcer of the {o["name"]} has its support',
                        all(e > 0.5 for e in q['enforcer_E']), [round(e, 3) for e in q['enforcer_E']])
            if o.get('key_zones'):
                reads = side_key_reads(g, o['key_zones'])
                p['objects'][o['name']]['side_keys'] = reads
                verdict(f'plate {n}: the {o["name"]}\'s side keys ({len(reads)}) print on what is under them: nothing '
                        f'floats (nor their support), nothing over {KEY_OVER_AIR_MM2} mm2 a layer reaches over '
                        f'{KEY_REACH} past the layer below or its support',
                        len(reads) == len(o['enforcers']) and all(v['ok'] for v in reads.values()),
                        {k: {'floating': v['floating'][:3], 'support_floating': v['support_floating'][:3],
                             'over_air_mm2_max': v['over_air_mm2_max'], 'reach_max': v['reach_max'],
                             'reach_at': v['reach_at']} for k, v in reads.items()})
                bases = side_key_bases(g, o['key_zones'])
                p['objects'][o['name']]['side_key_bases'] = bases
                what, value = side_key_base_row(bases)
                verdict(f'plate {n}: {what}', len(bases) == len(o['enforcers']) and all(v['ok'] for v in bases.values()),
                        value)
        none = [o['name'] for o, q in zip(pl['objects'], per)
                if not o['raft'] and not o['enforcers'] and q['support_E'] > 0]
        verdict(f'plate {n}: no support under anything else', not none, none)
    return {'sha256': entry['sha256'], 'plates': plates, 'checks': rows, 'ok': all(x['ok'] for x in rows)}


def slice_one(slug, entry):
    f = CONFIGS / entry['file']
    if hashlib.sha256(f.read_bytes()).hexdigest() != entry['sha256']:
        raise SystemExit(f'{f}: not the file index.json lists (rerun make_plates.py configs)')
    dest = SLICE / slug
    dest.mkdir(parents=True, exist_ok=True)
    for g in dest.glob('*'):
        if g.is_file():
            g.unlink()
    while cache.free_commit() < MIN_FREE:
        time.sleep(5)
    t0 = time.time()
    cmd = [str(ORCA), '--slice', '0', '--outputdir', str(dest), str(f)]
    r = cache.orca_run(cmd, dest, [f], ORCA, timeout=1200)     # cache.Lock waits out Windows' brief EACCES itself
    rep = check(slug, entry, dest, r)
    rep['seconds'] = round(time.time() - t0, 1)
    if r.returncode:
        err = r.stderr.decode(errors='replace') if isinstance(r.stderr, bytes) else str(r.stderr)
        rep['stderr'] = err[-2000:]
    return rep


def lid_alone(slug, entry):
    """The lid printed alone (print/README's 'reprint the lid'; 2026-10-13): slug's project with every build item but
    the lid's made unprintable (printable="0"), plate 1 sliced into SLICE/lid-alone/. Only the lid may print, its job
    must start on the skirt and not in a side key's zone (job_start), and its side keys must print on what is under
    them (side_key_reads), as on the full plate. -> (verdict rows, what was read)."""
    import zipfile
    objs = [o for pl in entry['plates'] for o in pl['objects']]
    k = next(i for i, o in enumerate(objs, start=1) if o.get('key_zones'))    # the lid: assemble()'s object 2k
    lid = objs[k - 1]
    f, dest = SLICE / 'lid-alone.3mf', SLICE / 'lid-alone'
    dest.mkdir(parents=True, exist_ok=True)
    for g in dest.glob('*'):
        if g.is_file():
            g.unlink()

    def item(m):
        return m.group(0) if m.group(1) == str(2 * k) else m.group(0).replace('printable="1"', 'printable="0"')
    with zipfile.ZipFile(CONFIGS / entry['file']) as zi, zipfile.ZipFile(f, 'w') as zo:
        for it in zi.infolist():
            d = zi.read(it.filename)
            if it.filename == '3D/3dmodel.model':
                d = re.sub(r'<item objectid="(\d+)"[^>]*/>', item, d.decode()).encode()
            zinfo = zipfile.ZipInfo(it.filename, it.date_time)       # the project's fixed date: the same bytes
            zinfo.compress_type = zipfile.ZIP_DEFLATED                # every run (cache.orca_run's key)
            zo.writestr(zinfo, d)
    while cache.free_commit() < MIN_FREE:
        time.sleep(5)
    r = cache.orca_run([str(ORCA), '--slice', '1', '--outputdir', str(dest), str(f)], dest, [f], ORCA, timeout=1200)
    g = dest / 'plate_1.gcode'
    what = f'the lid alone ({slug}\'s project, plate 1, every other object unprintable)'
    if r.returncode or not g.exists():
        return [{'check': f'{what}: OrcaSlicer exits 0 and slices it', 'ok': False, 'value': r.returncode}], None
    head, per, stray, _ = read_gcode(g, [lid])
    js = job_start(g, lid['key_zones'])
    reads = side_key_reads(g, lid['key_zones'])
    bases = side_key_bases(g, lid['key_zones'])
    info = {'gcode': g.relative_to(CONFIGS).as_posix(), **head, 'job_start': js,
            'side_keys': {n: {'ok': v['ok'], 'over_air_mm2_max': v['over_air_mm2_max'], 'reach_max': v['reach_max']}
                          for n, v in reads.items()},
            'side_key_bases': {n: {k: v[k] for k in ('ok', 'width_median', 'width_ok_share', 'layer2_on_1')}
                               for n, v in bases.items()}}
    rows = [{'check': f'{what}: only the lid prints, and the job starts on the skirt, not in a side key\'s zone',
             'ok': stray['moves'] == 0 and per[0]['part_E'] > 0 and js['ok'],
             'value': {'stray_moves': stray['moves'], 'job_start': js}},
            {'check': f'{what}: its side keys ({len(reads)}) print on what is under them, as on the full plate',
             'ok': len(reads) == len(lid['key_zones']) and all(v['ok'] for v in reads.values()),
             'value': info['side_keys']},
            {'check': f'{what}: ' + side_key_base_row(bases)[0],
             'ok': len(bases) == len(lid['key_zones']) and all(v['ok'] for v in bases.values()),
             'value': side_key_base_row(bases)[1]}]
    return rows, info


def main(argv):
    global CONFIGS, SLICE
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--builds', default=None,
                    help='slugs, comma-separated (default: every one in the folder\'s index.json)')
    ap.add_argument('--printer', choices=tuple(DIRS), default='generic',
                    help='generic: out/configs/ (the default, the website\'s files); cc2: out/configs-cc2/')
    ap.add_argument('--size', choices=('426', '368'), default='426',
                    help='426: this case (the default); 368: enclosures/case-368/out/ (make_plates.py configs --size 368)')
    o = ap.parse_args(argv)
    CONFIGS = cache.ROOT.parent / f'case-{o.size}' / 'out' / DIRS[o.printer]
    SLICE = CONFIGS / 'slice'
    if not (CONFIGS / 'index.json').exists():
        raise SystemExit(f'{CONFIGS / "index.json"}: none (run make_plates.py configs --size {o.size} --printer {o.printer})')
    listing = json.loads((CONFIGS / 'index.json').read_text())
    slugs = list(listing) if o.builds is None else [s for s in o.builds.split(',') if s]
    if not slugs:
        raise SystemExit('configs_slice: no configuration to slice (--builds names none, or index.json lists none)')
    lost = [s for s in slugs if s not in listing]
    if lost:
        raise SystemExit(f'not in {CONFIGS / "index.json"} (run make_plates.py configs): {", ".join(lost)}')
    longest = max((SLICE / s / f'plate_{len(listing[s]["plates"])}.gcode' for s in slugs), key=lambda p: len(str(p)))
    if len(str(longest)) >= cache.ORCA_PATH_MAX:
        raise SystemExit(f'{longest}: {len(str(longest))} characters; OrcaSlicer fails at {cache.ORCA_PATH_MAX} or '
                         'more: run from a checkout with a shorter path')
    rf = CONFIGS / 'slice-report.json'
    try:
        old = json.loads(rf.read_text())
    except (OSError, ValueError):
        old = {}
    t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(2) as ex:      # cache.orca_run runs 2 OrcaSlicers at most
        done = dict(zip(slugs, ex.map(lambda s: slice_one(s, listing[s]), slugs)))
    # once a run: the first configuration's lid printed alone (the reprint-the-lid job), its verdicts in that entry
    rows, info = lid_alone(slugs[0], listing[slugs[0]])
    d = done[slugs[0]]
    d['checks'] += rows
    d['lid_alone'] = info
    d['ok'] = all(x['ok'] for x in d['checks'])
    rep = {s: done.get(s, old.get(s)) for s in listing
           if s in done or (s in old and old[s].get('sha256') == listing[s]['sha256'])}
    cache.atomic_write(rf, json.dumps(rep, indent=1).encode())
    bad = [s for s in slugs if not done[s]['ok']]
    for s in slugs:
        d = done[s]
        print(f"{s}: {'ok' if d['ok'] else 'FAILED'} in {d['seconds']} s; "
              + '; '.join(f"{p['name']}: {p.get('grams')} g, {p.get('layers')} layers, {p.get('time')}"
                          for p in d['plates']))
        for x in d['checks']:
            if not x['ok']:
                print(f"    FAIL {x['check']}: {x.get('value')}")
        for p in d['plates']:
            js = p.get('job_start')
            if js and js['first_in_key_zone']:                     # the plate with the lid
                print(f"    {p['name'][:40]}: starts on {js['first'] and js['first']['role']}, first side-key line "
                      f"({js['first_in_key_zone']['key']}, {js['first_in_key_zone']['role']}) after "
                      f"{js['laid_before_mm']} mm")
        la = d.get('lid_alone')
        if la:
            js = la['job_start']
            print(f"    the lid alone: {la.get('grams')} g, {la.get('time')}; starts on {js['first'] and js['first']['role']}"
                  + (f", first side-key line ({js['first_in_key_zone']['key']}, {js['first_in_key_zone']['role']}) "
                     f"after {js['laid_before_mm']} mm" if js['first_in_key_zone'] else ''))
    print(f'{len(slugs)} configurations sliced in {time.time() - t0:.0f} s -> {rf.relative_to(cache.REPO)}')
    if bad:
        raise SystemExit(f'configs_slice: {len(bad)} failed: {", ".join(bad)}')


if __name__ == '__main__':
    main(sys.argv[1:])
