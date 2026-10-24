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

The two-colour logo switch (2026-10-24; make_plates.py: every lid carries its two logo bodies as modifier parts with no
setting, which print nothing; the prime tower is off and the project defines filament 2). logo_switch() reads both states back
from the ONE project of the keyed and the chinless 4.26 and the 3.68 (plate with the lid, the CLI, both printers):
  - the project file: two modifier_part logo parts (a name and a place, no setting), two filaments, enable_prime_tower 0,
    supports on filament 1, and the plate's wipe_tower_x / _y at least TOWER_CLEAR from every object;
  - OFF (the project as it ships) prints in filament 1 only, has no prime tower, and is the no-logo control (the same project
    with the parts removed): the same time and filament within noise, the same layers, no extrusion bucket (object, role, layer)
    OFF_E_TOL apart;
  - ON (a copy with the subtype normal_part and extruder 2 on the parts: what Change type -> Part and Change filament -> 2 write):
    both filaments are used, with no prime tower; filament 2 extrudes only in the lid's first two layers and only inside the two
    inlays' polygons (grown 0.1); the ink is covered by filament-2 lines for at least TWO_COVER of its area (all of it, layer 1
    and layer 2; each piece at least TWO_COVER_PIECE); no filament-1 line inside a glyph shrunk 0.15; every support and raft line
    stays filament 1; the job starts on the skirt and the side keys read as on the single-colour plate;
  - every project of the folder carries the same two parts at the same place in the lid's CAD frame (the other 30 are proved by
    that, not sliced).

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
NOT_PART = ('Custom', 'Skirt', 'Prime tower', 'Wipe tower')   # the start G-code's purge line, the skirt (make_plates.SKIRT)
                                    # and a prime tower the user switched on: on no object (no brim in these projects)
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


# ---- the two-colour logo switch (make_plates.py: the lid's two logo parts, modifiers with no settings): both states read back
# from the ONE project of a configuration
LOGO_REPS = {'426': ('standard', 'chinless'), '368': ('standard',)}   # sliced: the keyed and the chinless lid; the rest by position
TWO_COVER = (0.80, 0.85)            # share of ALL the ink's area the filament-2 lines cover, layer 1 and layer 2 (as a separate
                                    # object, check.md: 0.83-0.88 and 0.89-0.97)
TWO_COVER_PIECE = (0.65, 0.65)      # ... and of each piece (a glyph, the icon): the slicer leaves hairline gaps at sharp tips, and a
                                    # small piece suffers most (first in-lid slice 2026-10-23: the i's 1.5 mm dot 0.74 / 0.68, the
                                    # others 0.82-0.96; the first guess, 0.75 / 0.85 per piece, was written before any in-lid slice)
TWO_ZMAX = 0.45                     # filament 2 prints in the lid's first two layers only (z 0.2, 0.4)
TWO_GROW = 0.1                      # filament 2's line centres inside the inlays' polygons grown by this
TWO_OUTSIDE_MM = 0.2                # ... and at most this much line length outside
TWO_SHRINK = 0.15                   # no filament-1 line inside a glyph shrunk by this: at most TWO_T0_MAX of its area
TWO_T0_MAX = 0.02
TWO_AT_TOL = 0.01                   # the inlays' place in the lid's CAD frame, project to project (mm)
OFF_E_TOL = 0.3                     # OFF against the no-logo control: no (object, role, layer) bucket of extrusion differs by more
OFF_FIL_TOL = 0.1                   # mm of filament in all, and the estimated time by more than OFF_TIME_TOL s (OrcaSlicer's CLI is not
OFF_TIME_TOL = 10                   # bit-deterministic: the same file sliced twice differs by 0.001 mm jitter and +-2 s. The parts do cost
                                    # a systematic few seconds: on the 3.68 (11636 s) OFF is 6 s quicker than the control, all of it one
                                    # bucket, the lid's first-layer bottom surface (0.035 mm of filament less); 2026-10-24)
TOWER_BOX = (-4.29, -5.5, 34.29, 16.7)   # make_plates.TOWER_BOX: the tower and its brim from the set point
TOWER_CLEAR = 10.0                  # the point wipe_tower_x / _y names is at least this far from every object (plate with the lid)
LOGO_PART = re.compile(r'    <part id="(\d+)" subtype="(modifier_part|normal_part)">\n      <metadata key="name" value="(logo [^"]*)"/>\n'
                       r'((?:      <metadata key="[^"]*" value="[^"]*"/>\n)*)      <mesh_stat [^>]*/>\n    </part>\n')


def tool_lines(path, zmax=TWO_ZMAX):
    """The G-code by tool (2026-10-23): -> (lines, layers, changes). lines: [(z, tool, role, (x, y), (x2, y2), width)] for every
    extruding move up to zmax (bed coordinates: the extruder offset added back); layers: {tool: sorted z of every layer it
    extrudes in, the prime tower and the skirt left out}; changes: the number of tool-change lines (T0, T1) after the start."""
    t = path.read_text(errors='ignore')
    m = re.search(r'^; extruder_offset = (-?[\d.]+)x(-?[\d.]+)', t, re.M)
    ox, oy = (float(m.group(1)), float(m.group(2))) if m else (0.0, 0.0)
    lines, layers, changes = [], {}, 0
    tool, role, z, w, x, y = 0, None, 0.0, 0.42, 0.0, 0.0
    for line in t.splitlines():
        if line.startswith(';TYPE:'):
            role = line[6:].strip()
        elif line.startswith(';Z:'):
            z = float(line[3:])
        elif line.startswith(';WIDTH:'):
            w = float(line[7:])
        elif re.match(r'T\d+\s*$', line):
            tool = int(line[1:])
            changes += 1
        elif line.startswith(('G1 ', 'G0 ')):
            v = {q[0]: float(q[1:]) for q in line.split(';')[0].split()[1:] if q[0] in 'XYE' and len(q) > 1}
            nx, ny = v.get('X', x), v.get('Y', y)
            if line[:2] == 'G1' and v.get('E', 0.0) > 0 and (nx, ny) != (x, y) and role not in (None, 'Custom'):
                if role not in NOT_PART:
                    layers.setdefault(tool, set()).add(round(z, 3))
                if z <= zmax:
                    lines.append((round(z, 3), tool, role, (x + ox, y + oy), (nx + ox, ny + oy), w))
            x, y = nx, ny
    return lines, {k: sorted(v) for k, v in layers.items()}, changes


def buckets(path):
    """The extrusion of a plate's G-code as {(object, role, z or 'z>1'): mm of E}: the layers up to 1.0 mm one by one, the rest pooled
    (read_gcode's object markers, '; printing object NAME id:N'), and the job's header numbers {'time': s, 'filament_mm': mm}."""
    t = path.read_text(errors='ignore')
    out, obj, role, z = {}, None, None, 0.0
    for line in t.splitlines():
        if line.startswith(';TYPE:'):
            role = line[6:].strip()
        elif line.startswith(';Z:'):
            z = float(line[3:])
        elif line.startswith('; printing object '):
            obj = line[18:].split(' id:')[0]
        elif line.startswith('; stop printing object'):
            obj = None
        elif line.startswith('G1 ') and ' E' in line and ('X' in line or 'Y' in line):
            m = re.search(r' E(-?[\d.]+)', line.split(';')[0])
            if m and float(m.group(1)) > 0:
                k = (obj, role, z if z <= 1.0 else 'z>1')
                out[k] = out.get(k, 0.0) + float(m.group(1))
    m = re.search(r'estimated printing time \(normal mode\) = (?:(\d+)d )?(?:(\d+)h )?(?:(\d+)m )?(\d+)s', t)
    secs = sum(int(g or 0) * f for g, f in zip(m.groups(), (86400, 3600, 60, 1))) if m else None
    m = re.search(r'^; filament used \[mm\] = ([\d., ]+?)\s*$', t, re.M)       # one number per filament
    return out, {'time': secs, 'filament_mm': round(sum(float(v) for v in m.group(1).split(',')), 2) if m else None}


def glyph_polygons(stl, z=0.1):
    """The polygons of an inlay's print STL at height z (its bottom layer): the logo's glyphs and the icon's pieces, in the lid's
    print frame."""
    import numpy as np
    import trimesh
    sec = trimesh.load(stl, force='mesh').section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if sec is None:
        return []
    flat, _ = sec.to_planar(to_2D=np.eye(4), check=False)
    # polygons_full needs rtree (not in the venvs): each closed loop is a filled polygon, and the glyphs are their even-odd
    # XOR (a loop inside another is a hole, a loop inside that an island again)
    xor = None
    for q in flat.polygons_closed:
        q = q if q.is_valid else q.buffer(0)
        xor = q if xor is None else xor.symmetric_difference(q)
    if xor is None or xor.is_empty:
        return []
    return [g for g in getattr(xor, 'geoms', [xor]) if g.geom_type == 'Polygon' and g.area > 0.02]


def inlay_layers(stl):
    """How many 0.2 mm layers deep an inlay is (its print STL's height): 2 for the 4.26's pieces and the 3.68's wordmark, 1 for
    the 3.68's icon."""
    import trimesh
    b = trimesh.load(stl, force='mesh').bounds
    return int(round((b[1][2] - b[0][2]) / 0.2))


def lid_object(entry):
    """(plate number, the lid object's info) of an index.json entry: the plate with the logo parts ('inlays'), or None."""
    for n, pl in enumerate(entry['plates'], start=1):
        for o in pl['objects']:
            if o.get('inlays'):
                return n, o
    return None


def logo_at(slug, entry):
    """Where the lid's logo parts sit in the CAD frame, {name: [x0, y0, x1, y1]}: their boxes on the bed less the lid object's
    corner (the lid's print frame) plus the lid's own CAD corner (out/<slug>/lid.stl). The same for every project of one
    chin kind: the logo is part of the lid, wherever its side keys make its box start."""
    import trimesh
    _, lid = lid_object(entry)
    lo = trimesh.load(CONFIGS.parent / slug / 'lid.stl', force='mesh').bounds[0]
    return {q['name']: [round(q['box'][0] - lid['box'][0] + lo[0], 3), round(q['box'][1] - lid['box'][1] + lo[1], 3),
                        round(q['box'][3] - lid['box'][0] + lo[0], 3), round(q['box'][4] - lid['box'][1] + lo[1], 3)]
            for q in lid['inlays']}


def project_variant(src, dest, how):
    """A copy of a project (zip rewrite, the fixed dates kept) with the lid's logo parts changed: how 'control' removes them
    (the lid as it was before they existed: the OFF state's control), 'on' does what OrcaSlicer's GUI does for Change type -> Part
    and Change filament -> 2 (subtype normal_part, extruder 2). -> the number of logo parts found."""
    import zipfile
    with zipfile.ZipFile(src) as zi:
        items = [(it, zi.read(it.filename)) for it in zi.infolist()]
    ids, n = [], 0
    out = []
    for it, data in items:
        if it.filename == 'Metadata/model_settings.config':
            text = data.decode('ascii')
            found = LOGO_PART.findall(text)
            ids = [f[0] for f in found]
            n = len(found)
            if how == 'control':
                text = LOGO_PART.sub('', text)
            elif how == 'on':
                text = LOGO_PART.sub(lambda m: m.group(0).replace('subtype="modifier_part"', 'subtype="normal_part"')
                                     .replace('      <mesh_stat', '      <metadata key="extruder" value="2"/>\n      <mesh_stat'), text)
            else:
                raise ValueError(how)
            data = text.encode('ascii')
        out.append((it, data))
    if how == 'control':                       # the lid's components for those parts go too
        out = [(it, re.sub(r'    <component [^>]*objectid="(%s)"[^>]*/>\n' % '|'.join(ids), '', d.decode('ascii')).encode('ascii')
                if it.filename == '3D/3dmodel.model' and ids else d) for it, d in out]
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, 'w') as zo:
        for it, data in out:
            zinfo = zipfile.ZipInfo(it.filename, it.date_time)      # the project's fixed date: the same bytes every run
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            zinfo.external_attr = it.external_attr
            zo.writestr(zinfo, data)
    return n


def slice_plate(f, n, dest):
    """Slice plate n of project f into dest (cleared first), memoised by the file's bytes (cache.orca_run). -> (the run, the G-code's path)."""
    dest.mkdir(parents=True, exist_ok=True)
    for g in dest.glob('*'):
        if g.is_file():
            g.unlink()
    while cache.free_commit() < MIN_FREE:
        time.sleep(5)
    r = cache.orca_run([str(ORCA), '--slice', str(n), '--outputdir', str(dest), str(f)], dest, [f], ORCA, timeout=1800)
    return r, dest / f'plate_{n}.gcode'


def logo_switch(size, slugs=None):
    """The logo switch, both states from the ONE project (module docstring). -> (rows, info): rows [{check, ok, value}]."""
    import shapely
    import zipfile
    from shapely.geometry import box, LineString
    from shapely.ops import unary_union
    listing = json.loads((CONFIGS / 'index.json').read_text())
    rows, info = [], {}

    def verdict(what, ok, value=None):
        rows.append({'check': f'logo switch: {what}', 'ok': bool(ok), **({'value': value} if value is not None else {})})
    # 1. every project carries the two logo parts at one place in the lid's CAD frame (per chin kind: the keyed and the chinless lid)
    lacking = [s for s, e in listing.items() if lid_object(e) is None]
    verdict(f'every project ({len(listing)}) has a lid with its two logo parts', not lacking and bool(listing), lacking[:5])
    at = {s: logo_at(s, e) for s, e in listing.items() if s not in lacking}
    kinds = {}
    for s in at:
        kinds.setdefault('chinless' if 'chinless' in s else 'keyed', []).append(s)
    for kind, ss in kinds.items():
        ref = at[ss[0]]
        bad = {s: at[s] for s in ss if any(abs(a - b) > TWO_AT_TOL for k in ref for a, b in zip(at[s].get(k, [99] * 4), ref[k]))}
        verdict(f'the {len(ss)} {kind} projects carry the same two logo parts at the same place in the lid\'s CAD frame (+-{TWO_AT_TOL})',
                not bad and len(ref) == 2, {'at': ref, 'differ': list(bad)[:3]})
    info['logo_at'] = {s: at[s] for s in (kinds.get('keyed', [])[:1] + kinds.get('chinless', [])[:1])}
    # 2. the representatives, sliced (the lid's plate only): OFF as shipped, a control without the parts, ON as the GUI makes it
    for slug in LOGO_REPS[size]:
        if slugs is not None and slug not in slugs:
            continue
        if slug not in listing:
            verdict(f'{slug} is in index.json', False)
            continue
        entry = listing[slug]
        if lid_object(entry) is None:
            verdict(f'{slug}: the lid carries its two logo parts (modifier_part, no settings)', False, 'none in index.json')
            continue
        f = CONFIGS / entry['file']
        if hashlib.sha256(f.read_bytes()).hexdigest() != entry['sha256']:
            raise SystemExit(f'{f}: not the file index.json lists (rerun make_plates.py configs)')
        n, lid = lid_object(entry)
        what = f'{slug} (plate {n}, the lid)'
        # 2a. what the project file says
        with zipfile.ZipFile(f) as z:
            ms = z.read('Metadata/model_settings.config').decode('ascii')
            ps = json.loads(z.read('Metadata/project_settings.config'))
        parts = LOGO_PART.findall(ms)
        plain = all(p[1] == 'modifier_part' and re.findall(r'key="([^"]*)"', p[3]) == ['matrix'] for p in parts)
        verdict(f'{what}: the two logo parts are modifier parts with a name and a place and no setting (not even a filament)',
                len(parts) == 2 and plain, [(p[1], re.findall(r'key="([^"]*)"', p[3])) for p in parts])
        verdict(f'{what}: two filaments, prime tower off, supports on filament 1',
                len(ps['filament_colour']) == 2 and ps['enable_prime_tower'] == '0' and ps['support_filament'] == '1'
                and ps['support_interface_filament'] == '1',
                {k: ps[k] for k in ('filament_colour', 'enable_prime_tower', 'support_filament', 'support_interface_filament')})
        tx, ty = float(ps['wipe_tower_x'][n - 1]), float(ps['wipe_tower_y'][n - 1])
        tb = box(tx + TOWER_BOX[0], ty + TOWER_BOX[1], tx + TOWER_BOX[2], ty + TOWER_BOX[3])
        near = min(tb.distance(box(*[o['box'][i] - (2.5 if o['raft'] else 0.0) * (1 if i < 2 else -1) for i in range(4)]))
                   for o in entry['plates'][n - 1]['objects'])
        verdict(f'{what}: wipe_tower_x / _y ({tx:g}, {ty:g}) is {TOWER_CLEAR:g} mm or more clear of every object',
                near >= TOWER_CLEAR, round(near, 1))
        # 2b. OFF, as shipped
        t0 = time.time()
        r, g_off = slice_plate(f, n, SLICE / f'{slug}-logo-off')
        verdict(f'{what}: OFF slices (OrcaSlicer exits 0)', r.returncode == 0 and g_off.exists(), r.returncode)
        if r.returncode or not g_off.exists():
            err = r.stderr.decode(errors='replace') if isinstance(r.stderr, bytes) else str(r.stderr)
            info[slug] = {'off_stderr': err[-400:]}
            continue
        _, layers_off, _ = tool_lines(g_off, zmax=1e9)
        txt = g_off.read_text(errors='ignore')
        verdict(f'{what}: OFF prints in filament 1 only, with no prime tower and no filament-2 line',
                set(layers_off) == {0} and 'Prime tower' not in txt and 'Wipe tower' not in txt,
                {'tools': sorted(layers_off), 'prime_tower_lines': txt.count(';TYPE:Prime tower') + txt.count(';TYPE:Wipe tower')})
        # 2c. the control: the same project without the two parts
        ctl = SLICE / f'{slug}-logo-control.3mf'
        project_variant(f, ctl, 'control')
        r, g_ctl = slice_plate(ctl, n, SLICE / f'{slug}-logo-control')
        verdict(f'{what}: the no-logo control slices', r.returncode == 0 and g_ctl.exists(), r.returncode)
        if r.returncode or not g_ctl.exists():
            continue
        b_off, h_off = buckets(g_off)
        b_ctl, h_ctl = buckets(g_ctl)
        diff = {k: round(b_off.get(k, 0.0) - b_ctl.get(k, 0.0), 3) for k in set(b_off) | set(b_ctl)
                if abs(b_off.get(k, 0.0) - b_ctl.get(k, 0.0)) > OFF_E_TOL}
        dt = abs(h_off['time'] - h_ctl['time']) if h_off['time'] is not None and h_ctl['time'] is not None else 9e9
        dfil = abs(h_off['filament_mm'] - h_ctl['filament_mm']) if None not in (h_off['filament_mm'], h_ctl['filament_mm']) else 9e9
        same_layers = sorted({k[2] for k in b_off if k[2] != 'z>1'}) == sorted({k[2] for k in b_ctl if k[2] != 'z>1'})
        verdict(f'{what}: OFF is the no-logo control (time within {OFF_TIME_TOL} s, filament within {OFF_FIL_TOL} mm, the same layers, no '
                f'object/role/layer bucket of extrusion {OFF_E_TOL} mm apart)',
                dt <= OFF_TIME_TOL and dfil <= OFF_FIL_TOL and same_layers and not diff,
                {'time_s': [h_off['time'], h_ctl['time']], 'filament_mm': [h_off['filament_mm'], h_ctl['filament_mm']],
                 'same_layers': same_layers, 'buckets_apart': [[list(map(str, k)), v] for k, v in sorted(diff.items(), key=lambda kv: -abs(kv[1]))[:5]]})
        info[slug] = {'off_gcode': g_off.relative_to(CONFIGS).as_posix(), 'control_gcode': g_ctl.relative_to(CONFIGS).as_posix(),
                      'off': h_off, 'control': h_ctl}
        # 2d. ON: the GUI's two clicks, on a copy
        on = SLICE / f'{slug}-logo-on.3mf'
        project_variant(f, on, 'on')
        r, g = slice_plate(on, n, SLICE / f'{slug}-logo-on')
        verdict(f'{what}: ON (Change type -> Part, Change filament -> 2) slices', r.returncode == 0 and g.exists(), r.returncode)
        if r.returncode or not g.exists():
            continue
        lines, layers, changes = tool_lines(g)
        _, layers_all, _ = tool_lines(g, zmax=1e9)
        h_on = buckets(g)[1]
        info[slug].update({'on_gcode': g.relative_to(CONFIGS).as_posix(), 'seconds': round(time.time() - t0, 1), 'tool_changes': changes,
                           'layers_by_tool': {k: [v[0], v[-1], len(v)] for k, v in layers_all.items()}, 'on': h_on,
                           'on_cost': {'seconds': (h_on['time'] - h_off['time']) if None not in (h_on['time'], h_off['time']) else None,
                                       'filament_mm': round(h_on['filament_mm'] - h_off['filament_mm'], 1)
                                       if None not in (h_on['filament_mm'], h_off['filament_mm']) else None}})
        verdict(f'{what}: ON prints in both filaments (T0 and T1)', set(layers_all) == {0, 1} and changes >= 2,
                {'tools': sorted(layers_all), 'tool_changes': changes})
        onx = g.read_text(errors='ignore')
        verdict(f'{what}: ON has no prime tower (the tower is off; the printer purges)', ';TYPE:Prime tower' not in onx and ';TYPE:Wipe tower' not in onx)
        sup_tools = sorted({t for z, t, ro, a, b, w in tool_lines(g, zmax=1e9)[0] if ro in SUPPORT})
        verdict(f'{what}: ON keeps every support and raft line in filament 1', sup_tools == [0], sup_tools)
        t1z = layers_all.get(1, [])
        # the glyphs in the bed frame, and how many layers deep each inlay is (the 3.68's icon is one layer: its second layer is
        # the lid's own, filament 1)
        polys, per, depth = [], {}, {}
        for q in lid['inlays']:
            stem = 'inlay_wordmark' if 'wordmark' in q['name'] else 'inlay_icon'
            dx, dy = lid['box'][0], lid['box'][1]
            stl = CONFIGS.parent / slug / 'print' / f'{stem}.stl'
            gl = [shapely.affinity.translate(p, dx, dy) for p in glyph_polygons(stl)]
            per[q['name']] = gl
            depth[q['name']] = inlay_layers(stl)
            polys += gl
        deepest = max(depth.values())
        verdict(f'{what}: ON, filament 2 prints in the logo layers only ({deepest} layer{"s" * (deepest > 1)})',
                bool(t1z) and max(t1z) <= round(0.2 * deepest + 0.05, 3), t1z)
        allg = unary_union(polys)
        seg1 = [(a, b, w) for z, t, ro, a, b, w in lines if t == 1 and ro not in NOT_PART]
        cl = unary_union([LineString([a, b]) for a, b, _ in seg1]) if seg1 else shapely.Polygon()
        outside = cl.difference(allg.buffer(TWO_GROW)).length if seg1 else 0.0
        verdict(f'{what}: ON, filament 2 lays only inside the logo (line centres within {TWO_GROW} of it; <= {TWO_OUTSIDE_MM} mm outside)',
                bool(seg1) and outside <= TWO_OUTSIDE_MM, round(outside, 3))
        cover = {}
        for name, gl in per.items():
            for i, p in enumerate(sorted(gl, key=lambda q: (round(q.centroid.x, 1), round(q.centroid.y, 1)))):
                row = []
                for k, z in enumerate((0.2, 0.4)):
                    if k >= depth[name]:             # past this inlay: the lid's own layer
                        row.append(None)
                        continue
                    ss = [(a, b, w) for zz, t, ro, a, b, w in lines if t == 1 and zz == z and ro not in NOT_PART]
                    cov = unary_union([LineString([a, b]).buffer(w / 2, cap_style=2, join_style=2) for a, b, w in ss]) if ss else shapely.Polygon()
                    row.append(round(cov.intersection(p).area / p.area, 3))
                cover[f"{name.split(':')[0]} #{i + 1}"] = {'mm2': round(p.area, 2), 'layer1': row[0], 'layer2': row[1]}
        info[slug]['coverage'] = cover
        weak = {k: v for k, v in cover.items()
                if any(v[f'layer{i}'] is not None and v[f'layer{i}'] < TWO_COVER_PIECE[i - 1] for i in (1, 2))}
        whole = []
        for i in (1, 2):                             # area weighted, over the pieces that are that deep
            deep = [v for v in cover.values() if v[f'layer{i}'] is not None]
            tot = sum(v['mm2'] for v in deep)
            whole.append(round(sum(v['mm2'] * v[f'layer{i}'] for v in deep) / tot, 3) if tot else 0.0)
        info[slug]['coverage_all'] = whole
        verdict(f'{what}: ON, the ink covered by filament-2 lines (all of it >= {TWO_COVER[0]:.0%} layer 1, >= {TWO_COVER[1]:.0%} layer 2; '
                f'each of the {len(cover)} pieces >= {TWO_COVER_PIECE[0]:.0%} / {TWO_COVER_PIECE[1]:.0%})',
                bool(cover) and not weak and whole[0] >= TWO_COVER[0] and whole[1] >= TWO_COVER[1],
                {'all': whole, 'least_layer1': min(v['layer1'] for v in cover.values()),
                 'least_layer2': min(v['layer2'] for v in cover.values() if v['layer2'] is not None), 'weak': weak})
        # filament 1 inside the ink, layer by layer (a layer past an inlay's depth is the lid's own and may be filament 1)
        inside = area = 0.0
        for k, z in enumerate((0.2, 0.4)):
            shr = unary_union([q.buffer(-TWO_SHRINK) for nm, gl in per.items() if k < depth[nm] for q in gl])
            if shr.is_empty:
                continue
            t0lines = [(a, b, w) for zz, t, ro, a, b, w in lines if t == 0 and ro not in NOT_PART and zz == z]
            t0cov = unary_union([LineString([a, b]).buffer(w / 2, cap_style=2, join_style=2) for a, b, w in t0lines]) if t0lines else shapely.Polygon()
            inside += t0cov.intersection(shr).area
            area += shr.area
        share = inside / area if area else 0.0
        verdict(f'{what}: ON, no filament-1 line inside a glyph shrunk {TWO_SHRINK} (<= {TWO_T0_MAX:.0%} of its area)',
                share <= TWO_T0_MAX, round(share, 4))
        # the job and the side keys, as on the single-colour plate
        zones = lid['key_zones']
        js = job_start(g, zones)
        verdict(f'{what}: ON, the job starts on the skirt, not in a side key\'s zone', js['ok'], js)
        reads = side_key_reads(g, zones)
        verdict(f'{what}: ON, its side keys ({len(reads)}) print on what is under them', len(reads) == len(zones) and all(v['ok'] for v in reads.values()),
                {k: {'over_air_mm2_max': v['over_air_mm2_max'], 'reach_max': v['reach_max']} for k, v in reads.items()})
        bases = side_key_bases(g, zones)
        verdict(f'{what}: ON, ' + side_key_base_row(bases)[0], len(bases) == len(zones) and all(v['ok'] for v in bases.values()),
                side_key_base_row(bases)[1])
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
    tc_rows, tc_info = logo_switch(o.size, slugs)
    rep['_logo_switch'] = {'ok': all(x['ok'] for x in tc_rows), 'checks': tc_rows, **tc_info}
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
    for x in tc_rows:
        print(f"{'ok  ' if x['ok'] else 'FAIL'} {x['check']}" + ('' if x['ok'] else f": {x.get('value')}"))
    for slug, v in tc_info.items():
        if isinstance(v, dict) and 'coverage' in v:
            print(f'    {slug} logo coverage (layer 1 / layer 2): ' + '; '.join(
                f"{k} {c['layer1']:.2f}/" + ('-' if c['layer2'] is None else f"{c['layer2']:.2f}") for k, c in v['coverage'].items()))
            print(f"    {slug} logo ON costs {v['on_cost']['seconds']} s and {v['on_cost']['filament_mm']} mm of filament over OFF")
    if bad or any(not x['ok'] for x in tc_rows):
        raise SystemExit(f'configs_slice: {len(bad)} failed: {", ".join(bad)}' + (' and the logo switch read-back' if any(not x['ok'] for x in tc_rows) else ''))


if __name__ == '__main__':
    main(sys.argv[1:])
