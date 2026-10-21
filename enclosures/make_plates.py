"""One OrcaSlicer project 3MF per case size, with every printed part laid out on named plates, written to the
repo's print/ folder:

    print/silkscreen-426-plates.3mf    the 4.26 case (enclosures/case-426)
    print/silkscreen-368-plates.3mf    the 3.68 case (enclosures/case-368)

Plate 1 "Standard case": the standard tub, lid, midplate, 4 bottom keys, 4 crank-T, 2 gates (one spare).
Plate 2 "Light-strip case": the same with the light-strip tub (and, on the 3.68, its own keys).
Plate 3 "Test prints and extras": the rod jig, the chin coupon(s) with a bottom key to try in each (optional fit
checks for the hook keys: coupon-chin with a key-426 on the 4.26, coupon-strip with key-x3std / key-x3ls on the 3.68),
the gate coupon(s) and a gate to test them with (print these first), the PCBA test-fit dummy, and 4 crank-M (APEM
MJTP1117 boards only).
Plate 4 "Chinless case (touch, no bottom keys)" (the 4.26 only, 2026-10-04): the chinless build's tub and lid (no
bottom keys: a touch panel, and a board without SW9/SW8/SW3/SW2 fitted) and the shared midplate; no keys, cranks or
gate. It comes last so that plates 1-3 keep their objects, numbering and places (only the support enforcers' ids,
which follow every object's, move up).
Plate 5 "Light-strip chinless case (no touch, no bottom keys)" (the 4.26 only, 2026-10-07): the light-strip chinless
build's tub (the plain panel with the light strip, no bottom keys), the chinless lid (the lid never depends on the
panel; build.py's share check asserts it) and the shared midplate. Last again, so plates 1-4 keep their objects and
their places on the plate; the enforcers' ids move up 6, and with five plates OrcaSlicer's plate grid is three wide,
so plates 3 and 4 sit at other origins on its canvas (plate_origins).

Settings: the stock Elegoo Centauri Carbon 2 0.4 nozzle / 0.20mm Standard @Elegoo CC2 0.4 nozzle / Elegoo PLA
@ECC2 presets, resolved inside the Elegoo vendor folder as OrcaSlicer's GUI resolves them, with no brim and a one-loop
skirt (SKIRT, 2026-10-13), are the project settings; the plate type is Textured PEI (60 C for this PLA). Every key,
crank and gate carries elephant-foot compensation 0; the cranks also carry Arachne walls (per-object settings; the
same parts as slice_check.py's small_part(), and the process its crank read-back slices). Every bottom key and
crank also prints on a 2-layer raft (RAFT, 2026-10-06, Ian: so that they don't unstick from the plate; raft_layers 2,
raft_contact_distance 0.2, raft_first_layer_expansion 1, per object; slice_check slices them the same way and reads
them from their own bed face), and check_plate keeps each raft off its neighbours. Supports are off for every object but
the lid, and on the lid they go only under its side keys' hinge notches (LID_SUPPORT, side_key_enforcers): manual
supports with a support_enforcer part round each notch's roof, the part of the key that prints over air.

Reads the print-oriented STLs that each project's src/plates.py writes to out/standard/print/ and
out/light-strip/print/ (and on the 4.26 out/chinless/print/ and out/light-strip-chinless/print/; run it for every
print build first), the lid and its
side keys in the CAD frame from out/<build>/ (build.py's lid.stl and skey_*.stl), and print/rod-jig.stl (rod_jig.py).
No imports from the case projects (the configs pass reads the 4.26's src/variants.py, the slugs: standard library
only, no side effects). Run from this folder (enclosures/) with a Python 3.11 virtual environment made from
requirements.txt:

    python -B make_plates.py
    python -B make_plates.py configs [--builds a,b,...]
                                                                     [--printer generic|cc2]
    python -B make_plates.py configs --size 368 [--printer ...]

The output depends only on the STLs and the installed profiles: the zip entries carry a fixed date.

Per-configuration projects (`configs`, 2026-10-07): one OrcaSlicer project per 4.26 configuration (the 32 slugs of
case-426/src/variants.py; --builds names some, default all), with what that configuration prints and nothing else,
written to case-426/out/configs/<slug>.3mf (out/ is not in git; print/ keeps only the print builds' files). Plate 1
"Case: <the configuration in words>": its tub, its lid with one support enforcer per side key it has (5, or 3 for a
side-key layout) and the midplate; with bottom keys also 4 key-426, 4 crank-T, 2 gates (one spare) and the rod jig.
Plate 2, bottom keys only: "Only for APEM MJTP1117 boards: crank-M" x 4. No test prints (the coupons and the PCBA
dummy stay in the plate file). The per-object settings are the plate file's (EFC 0, Arachne on the cranks, the raft
under every key and crank, LID_SUPPORT on the lid). Each file is written through one path, the one a web page could
also take: library/ holds each distinct part's model file once, raw-deflated (<role>-<hash of its text>.dfl; its
object ids are a fixed block per role, ROLE_IDS, so a part file never depends on what is written with it or before
it, and the 3MF's bytes never depend on which configurations a run writes), recipes/<slug>.json the plates and, per
object, its part, name, place and settings, and assemble() zips a recipe's few generated XML files with the library's
part files as they are stored (every copy of a part points at its one file: 1.24 MB with bottom keys, 0.86 MB
chinless). index.json lists each file (bytes, sha256, its plates and every object's box on the bed, for the read-back;
since 2026-10-12 also each lid's side-key zones, 'key_zones', where configs_slice reads what each layer stands on).
A run updates the configurations it names and keeps the others' last files. case-426/src/configs_slice.py then slices
each with the OrcaSlicer CLI; case-426/src/pipeline.py runs both after the builds, plates and share checks pass.
--printer (2026-10-11): generic, the default and what the website serves, gives the projects OrcaSlicer's generic
presets (PRINTERS: Generic Marlin Printer 0.4, 0.20mm Standard, Generic PLA) and lays each plate out for a 220 x 210
bed (layout_compact: the midplate turned on the plate by its item's transform, 'rot' in the recipe), with what the
parts need on the objects (GENERIC_OBJ, GENERIC_LID, GENERIC_RAFT besides the plate file's); cc2 writes the Elegoo
CC2 projects as before (the plate file's presets and layout) into case-426/out/configs-cc2/. The library's part
files are the same for both.
--size 368 (2026-10-11, Ian: "do the same for the 3.68 parts. There is only one config for that"): the 3.68's one
released configuration, its standard build (CONFIGS_368; the light-strip 3.68 is unreleased and left out), through
the same path into case-368/out/configs/standard.3mf (cc2: out/configs-cc2/) with its own index.json, README.md,
library/ and recipes/: plate 1 its tub, lid (3 side keys, 3 enforcers), midplate, 4 key-x3std, 4 crank-T, 2 gates
and the rod jig, plate 2 the APEM boards' 4 crank-M (config_case_368). case-426/src/configs_slice.py --size 368 reads
it back.
"""
import hashlib
import json
import math
import struct
import sys
import zipfile
import zlib
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

import numpy as np
import shapely
import trimesh

HERE = Path(__file__).resolve().parent
PRINT = HERE.parent / 'print'            # the repo's print/: the plate files and the rod jig
PROFILES = Path(r'C:\Program Files\OrcaSlicer\resources\profiles')
VENDOR = 'Elegoo'
PRESETS = {'machine': 'Elegoo Centauri Carbon 2 0.4 nozzle',
           'process': '0.20mm Standard @Elegoo CC2 0.4 nozzle',
           'filament': 'Elegoo PLA @ECC2'}
NO_BRIM = {'brim_type': 'no_brim', 'brim_width': '0'}
# 2026-10-13 (Ian): a one-loop skirt on the first layer, 3 mm out, in every project this script writes (both plate
# files and every per-configuration project, generic and cc2), so that the job's first line is the skirt and not a
# side key: in the 3.68 lid job Ian printed, SW7's hinge support was the first line after the purge line, and a 4.26
# lid printed alone starts on SW5's. The skirt is a line you peel off; it touches no part (configs_slice reads back
# that each plate starts on it and that no side key's zone comes first). Its three keys are always listed in
# different_settings_to_system, also where the stock preset has the value already (the generic process's
# skirt_height 1): a slicer whose own preset of that name differs (ElegooSlicer opening the CC2 plate files) keeps the
# listed keys and takes the rest from its preset.
SKIRT = {'skirt_loops': '1', 'skirt_height': '1', 'skirt_distance': '3'}
SKIRT_REACH = 3.5                        # mm: the skirt's outer edge past the first layer's outline (3 + a 0.5 line)
# The per-configuration projects' printers (make_plates.py configs --printer, 2026-10-11). Ian: "orca slicer generic
# files as the default, at least for what I serve on the website". generic: the presets every OrcaSlicer install
# ships, whatever printer its user has: the Custom vendor's "Generic Marlin Printer" (MyMarlin 0.4 nozzle, plain
# Marlin start G-code, a 250 x 250 bed), its 0.20mm Standard process (0.2 layers, 0.2 first layer) and the Orca
# filament library's Generic PLA (compatible with every printer). The user picks their own printer on opening it (and
# keeps a 0.4 nozzle and 0.2 mm layers); what the design needs rides on the objects (object_settings), which a
# printer or process change keeps. cc2: Ian's own Elegoo Centauri Carbon 2 presets (the plate files' PRESETS).
PRINTERS = {
    'generic': {'presets': {'machine': ('Custom', 'MyMarlin 0.4 nozzle'),
                            'process': ('Custom', '0.20mm Standard @MyMarlin'),
                            'filament': ('OrcaFilamentLibrary', 'Generic PLA @System')},
                'bed': 250.0, 'exclude': None, 'area': (220.0, 210.0), 'dir': 'configs'},
    'cc2': {'presets': {k: (VENDOR, n) for k, n in PRESETS.items()},
            'bed': 256.0, 'exclude': (246.0, 0.0, 256.0, 20.0), 'area': None, 'dir': 'configs-cc2'},
}
# generic: every plate's parts (and their rafts) at least AREA_MARGIN inside the 220 x 210 corner of the bed at its
# origin, which every common bed holds (Ender-3 class 220 x 220, Prusa MK4 250 x 210, Bambu and the CC2 256): a
# printer change in Orca keeps the objects where they are on the plate
AREA_MARGIN = 5.0
# what a generic project's objects also carry, so that they keep it when the user's printer brings its own process:
# no brim (the plate files' project-level NO_BRIM) on every object, and on the lid the CC2 process's 1 mm support grid
# (the generic process has 2.5) under its side keys, the grid LID_SUPPORT's other values were tuned with; and under
# the keys and cranks the CC2 process's tree(auto) support type, which only picks how Orca builds the raft (supports
# stay off): with normal(auto), the generic process's and many others', Orca 2.4 leaves out the object's
# raft_first_layer_expansion 1 (the raft's first layer 4.25 past the part's box instead of 2.25, so the rafts of
# neighbouring keys and cranks run together; configs_slice, 2026-10-11)
GENERIC_OBJ = dict(NO_BRIM)
GENERIC_LID = {'support_base_pattern_spacing': '1'}
GENERIC_RAFT = {'support_type': 'tree(auto)'}
BED_TYPE = 'Textured PEI Plate'          # the CC2's plate; Elegoo PLA @ECC2 heats it to 60 C (Cool Plate: 35 C)
EFC0 = {'elefant_foot_compensation': '0'}
CRANK_OBJ = {'elefant_foot_compensation': '0', 'wall_generator': 'arachne'}   # test 1 (2026-09-29): with classic
                                         # walls Orca drops the inner loop in the cranks' 1.5 cheeks, leaving voids
# 2026-10-06, Ian: "maybe add 2-layer rafts to the buttons/cranks. That's what I've been doing so that they don't
# unstick from the build plate". Every bottom key and every crank (raft_part: the keys on their -X end, the cranks on
# their pad end, the coupons' keys included) prints on a 2-layer raft; nothing else does. The names are Orca's own, as
# its saved 3MFs write them (an Orca --export-3mf round trip of the plate file keeps all three on every one of these
# objects). Orca lays the 2 layers as one base layer (z 0.2, 0.5 lines, raft_first_layer_density 90 %) and one
# interface layer (0.3 thick, top at 0.5: 0.42 lines 0.5 apart, support_interface_spacing); the part's first layer is
# then 0.7-0.9, and every layer of the part is the 0.2 slab it was on the bed (only the first is laid with the layers'
# own 0.42-0.47 lines instead of the bed's 0.5): slice_check reads them from the part's own bed face. Those layers fall
# between the rest of the plate's (0.9, 1.1, ... against 0.8, 1.0, ...), so Orca prints them as layers of their own: a
# plate's G-code has about twice the layers (4.26 plate 1: 56 -> 107) and takes 1.5-2 min longer.
# raft_expansion stays the stock 1.5 (the interface 1.5 wider all round than the part's bed face).
RAFT = {
    'raft_layers': '2',
    'raft_contact_distance': '0.2',      # Orca's default 0.1; 0.2 is the crank spec's "2-layer raft (0.2 gap)" (up to
                                         # 0.1 of residue on the pad end tolerated) and one layer of air, as under the
                                         # lid's supports (support_top_z_distance, the profile's 0.2): it lifts off
    'raft_first_layer_expansion': '1',   # stock 2: the raft's first layer 3.46 past the part's bed face (line centres),
}                                        # which runs two keys' rafts 0.3 into each other at the plates' 6 mm (GAP);
                                         # at 1 it is 2.46 past it, and the rafts stay 1.0-1.6 apart as sliced
RAFT_REACH = 2.5                         # mm: the raft's first layer past the part's XY box at most (as sliced, its
                                         # lines' edges: the cranks 2.5, the keys 2.2; the bed face is inside the box)
RAFT_GAP_MIN = 0.9                       # mm between a raft's first layer and the next part's (or raft's) (check_plate)
# The lid's side keys (2026-09-30, Ian: the part of each key that prints in air after the air gap needs a support,
# thin enough to snap off, and nothing under the logo, its text or anything else). That part is the roof of each key's
# hinge notch: for TAB_HINGE (3.0) from the root the key's round and foot are cut away up to TAB_FOOT (1.05) above the
# bed, so the bar over it is a 3 mm bridge from the lid's wall to the rest of the key. The lid object alone gets
# supports, in manual mode, so Orca supports only inside the support_enforcer parts that side_key_enforcers() puts
# round each notch; every other object, and the rest of the lid, keeps supports off.
LID_SUPPORT = {
    'enable_support': '1',
    'support_type': 'normal(manual)',    # supports only where an enforcer is; a plain grid (no tree: 1 mm tall)
    'support_on_build_plate_only': '1',  # standing on the bed only, never on the lid
    'support_top_z_distance': '0.2',     # one layer of air between the support and the key (the stock value)
    'support_interface_top_layers': '0',  # no dense roof (stock 2): the key's first layer lies on the plain grid
    'support_object_xy_distance': '0.4',  # off the lid's wall and the key's foot beside the notch (stock 0.35)
    'raft_first_layer_expansion': '0',   # stock 2: the support's first layer 2 mm wider all round, into the slot
}                                        # behind the key, where a line would tie the key to the lid
OVER_AIR_NZ = -0.85                      # a key's face that prints over air: facing down within 32 degrees of flat
OVER_AIR_Z = 0.5                         # mm above the bed (below it is the back round's tangent, on the bed)
SIDE_KEY_VOLUME_TOL = 1.0                # mm3: lid.stl - lid_body.stl - the side keys (side_key_enforcers)
ENFORCER_XY = 0.25                       # an enforcer's margin round the face in plan
ENFORCER_Z = (-0.1, 0.15)                # and its span round the face's height: only the first layer over the air
                                         # (the roof is 1.05 over the bed, so that is the layer 1.0-1.2, which Orca
                                         # slices at 1.1); the back round's and the lid's 45-degree faces in the
                                         # layers below it are left unsupported, as everywhere else
KEY_ZONE_XY = (0.3, 1.0)                 # a side key's zone (side_key_zones): its box this much wider in x and in y
KEY_BASE_BED = 0.05                      # side_key_bases: a key's bed vertices lie this close to the bed (z of the lid's min)
KEY_BASE_TRIM = 0.1                      # ... its base box stops this far in from the hinge's end and from the free end
KEY_BASE_IN = 0.1                        # ... and runs this far past the key's inner bed edge toward the lid's centre
KEY_BASE_OUT = 2.15                      # ... and this far from that edge toward the case face (the 2.0 the base can fill
                                         # from the face to the edge, and 0.15 over)
# what this OrcaSlicer (2.4.0-dev) writes into its own project files. Tried and dropped (2026-09-28): stamping it
# as ElegooSlicer 1.5.1.6 makes Orca 2.4 merge the plates, and ElegooSlicer's CLI crashes on the file either way
# (after loading every object and plate; its GUI is untested). An older Orca stamp only trips its version check.
APP = 'BambuStudio-02.06.00.51'
APP_VERSION = '02.06.00.51'
CLIENT_VERSION = APP_VERSION             # slice_info's X-BBL-Client-Version

BED = 256.0
GAP = 6.0                                # between parts (>= 5)
PLATE_GAP = 1 / 5                        # Orca: plates sit one bed plus a fifth apart (LOGICAL_PART_PLATE_GAP)
EXCLUDE = (246.0, 0.0, 256.0, 20.0)      # the CC2 profile's bed_exclude_area
FIXED_DATE = (1980, 1, 1, 0, 0, 0)

CRANK_T = 'crank-T {} - TS365ZJ, JLC boards'
CRANK_M = 'crank-M {} - APEM MJTP1117 only'


def small_part(stem):
    """slice_check.py's rule: these print with elephant-foot compensation 0."""
    return stem.startswith(('crank-', 'key-')) or stem == 'gate'


def raft_part(stem):
    """slice_check.py's rule: these print on a raft (RAFT), the bottom keys and the cranks."""
    return stem.startswith(('crank-', 'key-'))


# ---------------------------------------------------------------- settings

def _index(root):
    idx = {}
    for kind in ('machine', 'process', 'filament'):
        for f in sorted(root.rglob(f'{kind}/**/*.json')):
            try:
                d = json.loads(f.read_text(encoding='utf-8'))
            except Exception:
                continue
            if 'name' in d:
                idx.setdefault((kind, d['name']), f)
    return idx


def _flatten(kind, name, idx):
    d = json.loads(idx[(kind, name)].read_text(encoding='utf-8'))
    parent = d.get('inherits')
    base = _flatten(kind, parent, idx) if parent and (kind, parent) in idx else {}
    base.update({k: v for k, v in d.items() if k != 'inherits'})
    return base


def stock_presets(presets=None):
    """The three stock presets ({kind: (vendor folder, name)}, default the CC2's PRESETS), inheritance resolved inside
    each one's vendor folder (as the GUI does)."""
    presets = presets or {k: (VENDOR, n) for k, n in PRESETS.items()}
    idx = {v: _index(PROFILES / v) for v in sorted({v for v, _ in presets.values()})}
    return {kind: _flatten(kind, name, idx[v]) for kind, (v, name) in presets.items()}


META_KEYS = {'name', 'from', 'type', 'setting_id', 'instantiation', 'inherits', 'filament_id', 'version',
             'compatible_printers', 'compatible_printers_condition', 'compatible_prints',
             'compatible_prints_condition', 'renamed_from', 'description'}


def project_settings(printer='cc2'):
    """Metadata/project_settings.config: the flattened stock presets (PRINTERS[printer]), no brim, the one-loop
    skirt, and the preset names."""
    presets = PRINTERS[printer]['presets']
    names = {k: n for k, (_, n) in presets.items()}
    pre = stock_presets(presets)
    area = [tuple(float(c) for c in xy.split('x')) for xy in pre['machine']['printable_area']]
    bed = PRINTERS[printer]['bed']
    if area != [(0, 0), (bed, 0), (bed, bed), (0, bed)]:
        sys.exit(f'{names["machine"]}: printable_area {pre["machine"]["printable_area"]}, PRINTERS says {bed} square')
    cfg = {}
    for kind in ('machine', 'filament', 'process'):
        cfg.update({k: v for k, v in pre[kind].items() if k not in META_KEYS})
    changed = sorted({k for k, v in NO_BRIM.items() if pre['process'].get(k) != v} | set(SKIRT))
    cfg.update(NO_BRIM)
    cfg.update(SKIRT)
    cfg.update({
        'name': 'project_settings',
        'from': 'project',
        'version': APP_VERSION,
        'printer_settings_id': names['machine'],
        'print_settings_id': names['process'],
        'filament_settings_id': [names['filament']],
        'filament_ids': [pre['filament'].get('filament_id', '')],
        'print_compatible_printers': pre['process'].get('compatible_printers', []),
        'inherits_group': ['', '', ''],
        # [process, filament, printer]: the keys that differ from the stock preset
        'different_settings_to_system': [';'.join(changed), '', ''],
        'curr_bed_type': BED_TYPE,
    })
    text = json.dumps(cfg, indent='\t', sort_keys=True, ensure_ascii=True)
    return text.replace('\n', '\r\n') + '\r\n', changed


# ---------------------------------------------------------------- parts and plates

class Part:
    def __init__(self, name, stl, efc0=None, side_keys=None, spin=False):
        self.name, self.stl = name, Path(stl)
        self.efc0 = small_part(self.stl.stem) if efc0 is None else efc0
        self.raft = raft_part(self.stl.stem)
        self.mesh = None                 # oriented, min corner at 0, in plate coordinates once laid out
        self.base = None                 # the oriented vertices, min corner at 0, before the layout moves them
        self.turned = False
        self.spin = spin                 # turned 90 degrees about Z on the plate only (the 3MF item's transform, SPIN;
                                         # its library file and base stay as they are): the generic layout's midplate
        self.side_keys = side_keys       # the lid: its build's folder, for side_key_enforcers()
        self.enforcers = []              # [(name, mesh)] in the oriented part's frame (min corner 0)
        self.key_zones = []              # [(ref, [x0, y0, x1, y1, top])], the same frame (side_key_zones)
        self.key_bases = {}              # {ref: [x0, y0, x1, y1]}, the same frame (side_key_bases)


def side_key_enforcers(build_dir):
    """One support_enforcer box per side key of the lid in build_dir (out/<build>/), round the faces of the key that
    print over air (OVER_AIR_NZ, OVER_AIR_Z; on every key that is the hinge notch's roof), ENFORCER_XY wider in plan
    and spanning ENFORCER_Z round its height (Orca supports an enforcer's overhangs down to the bed). Read off the
    keys themselves (build.py's skey_*.stl, CAD frame), so a change elsewhere in the lid cannot move them. The lid
    prints as it is drawn (plates.py's ORIENT: no turn), so its print STL is the CAD lid moved to its min corner;
    that is checked here."""
    cad = trimesh.load(build_dir / 'lid.stl', force='mesh')
    printed = trimesh.load(build_dir / 'print' / 'lid.stl', force='mesh')
    lo = cad.bounds[0]
    a = np.sort(np.asarray(cad.vertices) - lo, axis=0)
    b = np.sort(np.asarray(printed.vertices), axis=0)
    if a.shape != b.shape or not np.allclose(a, b, atol=2e-3):
        sys.exit(f"{build_dir}: print/lid.stl is not lid.stl moved to its min corner (did the lid's pose change?)")
    ext = printed.extents
    # the side keys there are exactly the lid's: lid.stl (with its keys) = lid_body.stl + every skey_*.stl, by volume
    # (each key is 130-180 mm3; the meshes agree to 0.01). A key file left from a build that no longer has that key,
    # or one missing, would otherwise put an enforcer where the lid has no key, or leave a key without one.
    skeys = sorted(build_dir.glob('skey_*.stl'), key=lambda f: f.stem)
    body = trimesh.load(build_dir / 'lid_body.stl', force='mesh')
    rest = cad.volume - body.volume - sum(trimesh.load(f, force='mesh').volume for f in skeys)
    if abs(rest) > SIDE_KEY_VOLUME_TOL:
        sys.exit(f'{build_dir}: lid.stl is not lid_body.stl + {", ".join(f.stem for f in skeys)} ({rest:+.2f} mm3): '
                 'a stale or a missing side key; run src/build.py for that build')
    out = []
    for f in skeys:
        m = trimesh.load(f, force='mesh')
        sel = (m.face_normals[:, 2] < OVER_AIR_NZ) & (m.triangles_center[:, 2] - lo[2] > OVER_AIR_Z)
        if not sel.any():
            continue
        v = m.triangles[sel].reshape(-1, 3) - lo
        (x0, y0, _), (x1, y1, z1) = v.min(axis=0), v.max(axis=0)
        # a key's over-air faces are in its bar, at the case's side (never under the back's logo, grip grooves or
        # screws), and in the bottom few layers
        if not (x1 < 3.5 or x0 > ext[0] - 3.5) or z1 > 3.0 or y1 - y0 > 6.0:
            sys.exit(f'{f.name}: faces over air at x {x0:.2f}-{x1:.2f} y {y0:.2f}-{y1:.2f} z <= {z1:.2f}: '
                     'not a hinge notch')
        e, (d0, d1) = ENFORCER_XY, ENFORCER_Z
        box = trimesh.creation.box(bounds=[[x0 - e, y0 - e, v[:, 2].min() + d0], [x1 + e, y1 + e, z1 + d1]])
        out.append((f'support enforcer {f.stem[5:]} hinge', box))
    if not out:
        sys.exit(f'{build_dir}: no side key (skey_*.stl) with a face over air; run src/build.py')
    return out


def side_key_zones(build_dir):
    """Each side key's zone, [(ref, [x0, y0, x1, y1, top])] in the oriented lid's frame (min corner 0): the key's box
    (build.py's skey_*.stl: bar, block, pad and nub) KEY_ZONE_XY wider, so that its slot, the lid's edge beside it and
    the wall at its ends are in it, from the bed to the key's top. configs_slice reads the lid's G-code back in it
    (side_key_read: what each layer stands on). Called after side_key_enforcers, which checks that the key files are
    the lid's."""
    lo = trimesh.load(build_dir / 'lid.stl', force='mesh').bounds[0]
    ex, ey = KEY_ZONE_XY
    out = []
    for f in sorted(build_dir.glob('skey_*.stl'), key=lambda f: f.stem):
        (x0, y0, _), (x1, y1, z1) = trimesh.load(f, force='mesh').bounds - lo
        out.append((f.stem[5:], [x0 - ex, y0 - ey, x1 + ex, y1 + ey, z1]))
    return out


def side_key_bases(build_dir):
    """Each side key's base box, {ref: [x0, y0, x1, y1]} in the oriented lid's frame (min corner 0), where configs_slice's
    side_key_base reads what the key's first two layers stand on (2026-10-19: Ian's keys print scraggly in their free
    half; as sliced each stood on one 0.52 bead). From the key's own mesh (build.py's skey_*.stl): its vertices on the
    bed spread along the key (the hinge's end to the free end, trimmed KEY_BASE_TRIM at each end); across it the box
    runs from KEY_BASE_IN past the bed vertex nearest the lid's centre (the key's inner bed edge: 2.0 in from the case
    face on both sizes) toward the centre, to KEY_BASE_OUT past it toward the case face. Today's keys have a line of
    bed vertices there and print on one bead; a key with TAB_BASE has them over the filled width (square: from the
    face; teardrop: from 1.17 in) to that edge."""
    lid = trimesh.load(build_dir / 'lid.stl', force='mesh')
    lo = lid.bounds[0]
    ctr = (lid.bounds[1] - lo) / 2
    out = {}
    for f in sorted(build_dir.glob('skey_*.stl'), key=lambda f: f.stem):
        v = np.asarray(trimesh.load(f, force='mesh').vertices) - lo
        v = v[v[:, 2] < KEY_BASE_BED]
        if len(v) < 3:
            sys.exit(f'{f.name}: no vertices on the bed (z < {KEY_BASE_BED}): not a key standing on the back')
        ext = v[:, :2].max(axis=0) - v[:, :2].min(axis=0)
        along = int(np.argmax(ext))                     # 0: x, 1: y
        cross = 1 - along
        edge = v[np.argmin(np.abs(v[:, cross] - ctr[cross])), cross]
        sgn = 1.0 if ctr[cross] >= edge else -1.0        # +1: the centre lies in +cross from the edge
        c0, c1 = sorted((edge + sgn * KEY_BASE_IN, edge - sgn * KEY_BASE_OUT))
        a0, a1 = v[:, along].min() + KEY_BASE_TRIM, v[:, along].max() - KEY_BASE_TRIM
        box = [0.0] * 4
        box[along], box[along + 2] = a0, a1
        box[cross], box[cross + 2] = c0, c1
        out[f.stem[5:]] = box
    return out


def load(part, turn):
    """The oriented STL (plates.py wrote it with its min corner at 0); small parts turned 90 degrees about Z
    so the longest side runs along Y, as plates.py lays them out. The turn is exact: (x, y) -> (-y, x)."""
    m = trimesh.load(part.stl, force='mesh')
    v = np.array(m.vertices, dtype=float)
    if turn and m.extents[0] > m.extents[1]:
        v = np.column_stack([-v[:, 1], v[:, 0], v[:, 2]])
        part.turned = True
    v -= v.min(axis=0)
    part.base = v.copy()
    if part.spin:                        # (x, y) -> (-y, x), as the item transform SPIN turns it
        v = np.column_stack([-v[:, 1], v[:, 0], v[:, 2]])
        v -= v.min(axis=0)
    part.mesh = trimesh.Trimesh(v, np.array(m.faces), process=False)
    return part


def layout(rows, cols):
    """plates.py's layout: the large parts side by side in rows (the first row nearest the front), the small
    parts in columns to their right, each column one part type; then the group centred on the bed."""
    placed = []

    def put(p, x0, y0):
        p.mesh.apply_translation([x0 - p.mesh.bounds[0][0], y0 - p.mesh.bounds[0][1], 0])
        placed.append(p)

    y = 0.0
    for row in rows:
        x, h = 0.0, 0.0
        for p in row:
            load(p, turn=False)
            put(p, x, y)
            x = p.mesh.bounds[1][0] + GAP
            h = max(h, p.mesh.extents[1])
        y += h + GAP
    x = max(p.mesh.bounds[1][0] for p in placed) + GAP if placed else 0.0
    for col in cols:
        y, w = 0.0, 0.0
        for p in col:
            load(p, turn=True)
            put(p, x, y)
            y = p.mesh.bounds[1][1] + GAP
            w = max(w, p.mesh.extents[0])
        x += w + GAP
    lo = np.min([p.mesh.bounds[0] for p in placed], axis=0)
    hi = np.max([p.mesh.bounds[1] for p in placed], axis=0)
    shift = [round(BED / 2 - (lo[0] + hi[0]) / 2, 3), round(BED / 2 - (lo[1] + hi[1]) / 2, 3), 0]
    for p in placed:
        p.mesh.apply_translation(shift)
    return placed


def layout_compact(front, back, cols, side, area):
    """The generic projects' layout, for a 220 x 210 bed (area): the front row the turned midplate (spin) and the small
    parts' columns beside it, each column one part type; behind it the tub and the lid side by side, and the rod jig
    (side) to their right; then the group centred on area, whose corner is the bed's origin."""
    placed = []

    def put(p, x0, y0):
        p.mesh.apply_translation([x0 - p.mesh.bounds[0][0], y0 - p.mesh.bounds[0][1], 0])
        placed.append(p)

    x = 0.0
    for p in front:
        load(p, turn=False)
        put(p, x, 0.0)
        x = p.mesh.bounds[1][0] + GAP
    for col in cols:
        y, w = 0.0, 0.0
        for p in col:
            load(p, turn=True)
            put(p, x, y)
            y = p.mesh.bounds[1][1] + GAP
            w = max(w, p.mesh.extents[0])
        x += w + GAP
    yb = max(p.mesh.bounds[1][1] for p in placed) + GAP if placed else 0.0
    x = 0.0
    for p in back:
        load(p, turn=False)
        put(p, x, yb)
        x = p.mesh.bounds[1][0] + GAP
    for p in side:
        load(p, turn=True)
        put(p, x, yb)
        x = p.mesh.bounds[1][0] + GAP
    lo = np.min([p.mesh.bounds[0] for p in placed], axis=0)
    hi = np.max([p.mesh.bounds[1] for p in placed], axis=0)
    shift = [round(area[0] / 2 - (lo[0] + hi[0]) / 2, 3), round(area[1] / 2 - (lo[1] + hi[1]) / 2, 3), 0]
    for p in placed:
        p.mesh.apply_translation(shift)
    return placed


def check_plate(parts, bed=BED, exclude=EXCLUDE, area=None):
    """Inside the bed, clear of the excluded corner and of the purge line (y > 0.5), >= 5 mm apart (XY boxes); a part
    on a raft (RAFT) also keeps its raft's first layer (RAFT_REACH past its box) RAFT_GAP_MIN off the next part's (or
    its raft's) and on the bed. With an area (the generic projects' 220 x 210), every part and raft stays AREA_MARGIN
    inside it. The skirt round the plate (SKIRT_REACH) stays on the bed and out of the excluded corner."""
    errs = []
    for p in parts:
        (x0, y0, z0), (x1, y1, z1) = p.mesh.bounds
        if x0 < 0 or y0 < 0.5 or x1 > bed or y1 > bed:
            errs.append(f'{p.name}: outside the bed {x0:.2f} {y0:.2f} {x1:.2f} {y1:.2f}')
        r = RAFT_REACH if p.raft else 0.0
        if p.raft and (x0 - r < 0 or y0 - r < 0.5 or x1 + r > bed or y1 + r > bed):
            errs.append(f'{p.name}: its raft runs off the bed')
        if area and (x0 - r < AREA_MARGIN or y0 - r < AREA_MARGIN or x1 + r > area[0] - AREA_MARGIN
                     or y1 + r > area[1] - AREA_MARGIN):
            errs.append(f'{p.name}: not {AREA_MARGIN} mm inside {area[0]:g} x {area[1]:g} '
                        f'({x0 - r:.2f} {y0 - r:.2f} {x1 + r:.2f} {y1 + r:.2f})')
        if abs(z0) > 1e-9:
            errs.append(f'{p.name}: not on the bed (z {z0})')
        ex = exclude
        if ex and x1 > ex[0] and x0 < ex[2] and y1 > ex[1] and y0 < ex[3]:
            errs.append(f'{p.name}: in the excluded corner')
    # the skirt (SKIRT): Orca lays it round the convex hull of the plate's first layer (the rafts' first layers
    # included), so SKIRT_REACH round that hull must be on the bed, clear of the purge line and the excluded corner
    if parts:
        foot = [shapely.MultiPoint(p.mesh.vertices[p.mesh.vertices[:, 2] < 0.25][:, :2]).convex_hull
                .buffer(RAFT_REACH if p.raft else 0.0) for p in parts]
        skirt = shapely.union_all(foot).convex_hull.buffer(SKIRT_REACH)
        sx0, sy0, sx1, sy1 = skirt.bounds
        w, h = area or (bed, bed)
        if sx0 < 0 or sy0 < 0.5 or sx1 > w or sy1 > h:
            errs.append(f'the skirt runs off the bed (or the {w:g} x {h:g} area) or onto the purge line '
                        f'({sx0:.2f} {sy0:.2f} {sx1:.2f} {sy1:.2f})')
        if exclude and skirt.intersects(shapely.box(*exclude)):
            errs.append('the skirt runs into the excluded corner')
    gap_min = math.inf
    for i, a in enumerate(parts):
        for b in parts[i + 1:]:
            (ax0, ay0, _), (ax1, ay1, _) = a.mesh.bounds
            (bx0, by0, _), (bx1, by1, _) = b.mesh.bounds
            gap = max(bx0 - ax1, ax0 - bx1, by0 - ay1, ay0 - by1)
            gap_min = min(gap_min, gap)
            if gap < 5.0:
                errs.append(f'{a.name} / {b.name}: {gap:.2f} mm apart')
            rr = RAFT_REACH * (a.raft + b.raft)
            if rr and gap - rr < RAFT_GAP_MIN - 1e-9:
                errs.append(f'{a.name} / {b.name}: rafts {gap - rr:.2f} mm apart')
    return errs, gap_min


def plate_origins(n, bed=BED):
    """Orca's PartPlateList::compute_origin: cols = round(sqrt(n)) (+1 if sqrt(n) is above it), plate i at
    (col, -row) * bed * (1 + 1/5)."""
    v = math.sqrt(n)
    r = math.floor(v + 0.5)
    cols = r + 1 if v > r else r
    stride = bed * (1 + PLATE_GAP)
    return [((i % cols) * stride, -(i // cols) * stride) for i in range(n)]


# ---------------------------------------------------------------- the two cases

ROD_JIG = PRINT / 'rod-jig.stl'         # rod_jig.py: the same rod, so the same jig, in both cases

def case_426():
    proj = HERE / 'case-426'
    std, ls = proj / 'out' / 'standard' / 'print', proj / 'out' / 'light-strip' / 'print'
    chin = proj / 'out' / 'chinless' / 'print'
    lsc = proj / 'out' / 'light-strip-chinless' / 'print'

    def case_plate(src, tub):
        rows = [[Part('midplate', src / 'midplate.stl')],
                [Part(tub, src / 'tub.stl'), Part('lid', src / 'lid.stl', side_keys=src.parent)]]
        cols = [[Part(f'key-426 {i}', src / 'key-426.stl') for i in range(1, 5)],
                [Part(CRANK_T.format(i), src / 'crank-T.stl') for i in range(1, 5)],
                [Part('gate 1', src / 'gate.stl'), Part('gate 2 (spare)', src / 'gate.stl')]]
        return rows, cols

    extras = ([[Part('rod jig (straighten and cut the rod)', ROD_JIG)], [Part('pcba-dummy (test fit)', std / 'pcba-dummy.stl')]],
              [[Part('coupon-chin', std / 'coupon-chin.stl'), Part('key-426 (for the chin coupon)', std / 'key-426.stl')],
               [Part('coupon-gate', std / 'coupon-gate.stl'), Part('gate (for the gate coupon)', std / 'gate.stl')],
               [Part(CRANK_M.format(i), std / 'crank-M.stl') for i in range(1, 5)]])
    # parts taken from the standard build's folder that the light-strip build shares (the chin coupon is the hook
    # keys' optional fit check, tried with a key-426)
    shared = ['coupon-chin', 'coupon-gate', 'pcba-dummy', 'crank-M', 'gate', 'key-426']
    # the chinless case (touch, no bottom keys): its own tub and lid (side keys and their enforcers as on plates 1-2),
    # the shared midplate; nothing for the bottom keys
    chinless = ([[Part('midplate', chin / 'midplate.stl')],
                 [Part('tub (chinless)', chin / 'tub.stl'), Part('lid (chinless)', chin / 'lid.stl', side_keys=chin.parent)]],
                [])
    # the light-strip chinless case (plain panel + light strip, no bottom keys): its own tub, the chinless lid (the
    # same file as plate 4's, asserted below with the midplate), its side keys' enforcers as on plates 1, 2 and 4
    ls_chinless = ([[Part('midplate', lsc / 'midplate.stl')],
                    [Part('tub (light-strip chinless)', lsc / 'tub.stl'),
                     Part('lid (chinless)', lsc / 'lid.stl', side_keys=lsc.parent)]],
                   [])
    return dict(title='Silkscreen 4.26 case - all printed parts',
                out=PRINT / 'silkscreen-426-plates.3mf',
                sources=[std, ls, chin, lsc], shared=[(std / f'{s}.stl', ls / f'{s}.stl') for s in shared]
                + [(std / 'midplate.stl', chin / 'midplate.stl'), (std / 'midplate.stl', lsc / 'midplate.stl'),
                   (chin / 'lid.stl', lsc / 'lid.stl')],
                plates=[('Standard case', *case_plate(std, 'tub (standard)')),
                        ('Light-strip case', *case_plate(ls, 'tub (light strip)')),
                        ('Test prints and extras', *extras),
                        ('Chinless case (touch, no bottom keys)', *chinless),
                        ('Light-strip chinless case (no touch, no bottom keys)', *ls_chinless)])


def case_368():
    proj = HERE / 'case-368'
    std, ls = proj / 'out' / 'standard' / 'print', proj / 'out' / 'light-strip' / 'print'

    def case_plate(src, tub, key):
        rows = [[Part('midplate', src / 'midplate.stl')],
                [Part(tub, src / 'tub.stl'), Part('lid', src / 'lid.stl', side_keys=src.parent)]]
        cols = [[Part(f'{key} {i}', src / f'{key}.stl') for i in range(1, 5)],
                [Part(CRANK_T.format(i), src / 'crank-T.stl') for i in range(1, 5)],
                [Part('gate 1', src / 'gate.stl'), Part('gate 2 (spare)', src / 'gate.stl')]]
        return rows, cols

    def coupon(src, build, key):
        # the hook keys' optional fit check (test 2): the chin strip with its two slots, and one key to try in it
        return [Part(f'coupon-strip ({build})', src / 'coupon-strip.stl'),
                Part(f'{key} (for the coupon strip)', src / f'{key}.stl')]

    extras = ([[Part('rod jig (straighten and cut the rod)', ROD_JIG)], [Part('pcba-dummy (test fit)', std / 'pcba-dummy.stl')]],
              [coupon(std, 'standard', 'key-x3std'), coupon(ls, 'light strip', 'key-x3ls'),
               [Part('coupon-gate (standard)', std / 'coupon-gate.stl'),
                Part('coupon-gate (light strip)', ls / 'coupon-gate.stl'),
                Part('gate (for the gate coupons)', std / 'gate.stl')],
               [Part(CRANK_M.format(i), std / 'crank-M.stl') for i in range(1, 5)]])
    shared = ['pcba-dummy', 'crank-M', 'gate']
    return dict(title='Silkscreen 3.68 case - all printed parts',
                out=PRINT / 'silkscreen-368-plates.3mf',
                sources=[std, ls], shared=[(std / f'{s}.stl', ls / f'{s}.stl') for s in shared],
                plates=[('Standard case', *case_plate(std, 'tub (standard)', 'key-x3std')),
                        ('Light-strip case', *case_plate(ls, 'tub (light strip)', 'key-x3ls')),
                        ('Test prints and extras', *extras)])


# ---------------------------------------------------------------- 3MF writer (the layout OrcaSlicer writes)

NS = ('xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
      'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
      'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p"')
MODEL_REL = 'http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel'


def _f(x):
    s = '%.9g' % x
    return '0' if s == '-0' else s


def _model_xml(objs):
    """A model file of mesh objects [(id, p:UUID, mesh)]. Every volume is type "model", as OrcaSlicer's own save
    writes them: what makes one an enforcer is its subtype in model_settings.config (an Orca --export-3mf round trip,
    2026-09-30)."""
    out = ['<?xml version="1.0" encoding="UTF-8"?>\n',
           f'<model unit="millimeter" xml:lang="en-US" {NS}>\n',
           ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n',
           ' <resources>\n']
    for oid, uuid, m in objs:
        out += [f'  <object id="{oid}" p:UUID="{uuid}" type="model">\n',
                '   <mesh>\n    <vertices>\n']
        out += [f'     <vertex x="{_f(x)}" y="{_f(y)}" z="{_f(z)}"/>\n' for x, y, z in m.vertices]
        out.append('    </vertices>\n    <triangles>\n')
        out += [f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>\n' for a, b, c in m.faces]
        out.append('    </triangles>\n   </mesh>\n  </object>\n')
    out.append(' </resources>\n <build/>\n</model>\n')
    return ''.join(out)


def _mesh_xml(k, local, extra=()):
    """3D/Objects/object_<k>.model: the mesh, centred on its bounding box (as Orca stores a volume); then the
    object's other volumes (extra: [(id, j, mesh)], the lid's support enforcers), each its own object."""
    return _model_xml([(oid, f'{k:04x}{j:04x}-81cb-4c03-9d28-80fed5dfa1dc', m)
                       for oid, j, m in [(2 * k - 1, 0, local), *extra]])


def object_settings(p, printer='cc2'):
    """The part's per-object settings (model_settings.config): EFC 0 on the small parts (and Arachne walls on the
    cranks), the raft under the keys and cranks, the lid's manual supports; in a generic project also no brim on every
    object, the lid's support grid and the rafts' support type (GENERIC_OBJ, GENERIC_LID, GENERIC_RAFT)."""
    obj = {}
    if p.efc0:
        obj.update(CRANK_OBJ if p.stl.stem.startswith('crank-') else EFC0)
    if p.raft:
        obj.update(RAFT)
    if p.enforcers:
        obj.update(LID_SUPPORT)
    if printer == 'generic':
        obj.update(GENERIC_OBJ)
        if p.enforcers:
            obj.update(GENERIC_LID)
        if p.raft:
            obj.update(GENERIC_RAFT)
    return obj


def write_3mf(path, title, plates, settings_text):
    """plates: [(name, [Part, ...] laid out in plate coordinates)]. Returns the objects written."""
    origins = plate_origins(len(plates))
    files = {}
    objects = []                                   # (k, part, plate index, world offset, centre)
    extra = {}                                     # k: [(id, j, name, offset from the object's origin)]
    eid = 2 * sum(len(parts) for _, parts in plates)   # the enforcers' ids follow every object's two
    k = 0
    for pi, (pname, parts) in enumerate(plates):
        ox, oy = origins[pi]
        for p in parts:
            k += 1
            lo, hi = p.mesh.bounds
            c = (lo + hi) / 2
            local = trimesh.Trimesh(p.mesh.vertices - c, p.mesh.faces, process=False)
            vols = []
            assert not (p.enforcers and p.turned)
            for j, (ename, em) in enumerate(p.enforcers, start=1):
                eid += 1
                emid = (em.bounds[0] + em.bounds[1]) / 2
                ec = emid + p.mesh.bounds[0]               # the oriented part's frame (min corner 0) -> the plate
                vols.append((eid, j, trimesh.Trimesh(em.vertices - emid, em.faces, process=False)))
                extra.setdefault(k, []).append((eid, j, ename, (ec[0] - c[0], ec[1] - c[1], ec[2])))
            files[f'3D/Objects/object_{k}.model'] = _mesh_xml(k, local, vols)
            objects.append((k, p, pi, (ox + c[0], oy + c[1], 0.0), (0.0, 0.0, c[2])))

    model = ['<?xml version="1.0" encoding="UTF-8"?>\n', f'<model unit="millimeter" xml:lang="en-US" {NS}>\n',
             f' <metadata name="Application">{APP}</metadata>\n',
             ' <metadata name="OrcaSlicer">2.4.0-dev</metadata>\n',
             ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n']
    for key in ('Copyright', 'CreationDate', 'Description', 'Designer', 'DesignerCover', 'DesignerUserId',
                'License', 'ModificationDate', 'Origin'):
        model.append(f' <metadata name="{key}"></metadata>\n')
    model.append(f' <metadata name="Title">{escape(title)}</metadata>\n <resources>\n')
    for k, p, pi, off, vol in objects:
        model += [f'  <object id="{2 * k}" p:UUID="{k:08x}-61cb-4c03-9d28-80fed5dfa1dc" type="model">\n',
                  '   <components>\n',
                  f'    <component p:path="/3D/Objects/object_{k}.model" objectid="{2 * k - 1}" '
                  f'p:UUID="{k:04x}0000-b206-40ff-9872-83e8017abed1" '
                  f'transform="1 0 0 0 1 0 0 0 1 {_f(vol[0])} {_f(vol[1])} {_f(vol[2])}"/>\n']
        model += [f'    <component p:path="/3D/Objects/object_{k}.model" objectid="{e}" '
                  f'p:UUID="{k:04x}{j:04x}-b206-40ff-9872-83e8017abed1" '
                  f'transform="1 0 0 0 1 0 0 0 1 {_f(t[0])} {_f(t[1])} {_f(t[2])}"/>\n'
                  for e, j, _, t in extra.get(k, [])]
        model.append('   </components>\n  </object>\n')
    model.append(' </resources>\n <build p:UUID="2c7c17d8-22b5-4d84-8835-1976022ea369">\n')
    for k, p, pi, off, vol in objects:
        model.append(f'  <item objectid="{2 * k}" p:UUID="{2 * k:08x}-b1ec-4553-aec9-835e5b724bb4" '
                     f'transform="1 0 0 0 1 0 0 0 1 {_f(off[0])} {_f(off[1])} {_f(off[2])}" printable="1"/>\n')
    model.append(' </build>\n</model>\n')
    files['3D/3dmodel.model'] = ''.join(model)

    rels = ['<?xml version="1.0" encoding="UTF-8"?>\n',
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n']
    rels += [f' <Relationship Target="/3D/Objects/object_{k}.model" Id="rel-{k}" Type="{MODEL_REL}"/>\n'
             for k, *_ in objects]
    rels.append('</Relationships>\n')
    files['3D/_rels/3dmodel.model.rels'] = ''.join(rels)

    cfg = ['<?xml version="1.0" encoding="UTF-8"?>\n<config>\n']
    for k, p, pi, off, vol in objects:
        cfg += [f'  <object id="{2 * k}">\n',
                f'    <metadata key="name" value={quoteattr(p.name)}/>\n',
                '    <metadata key="extruder" value="1"/>\n']
        cfg += [f'    <metadata key="{key}" value="{v}"/>\n' for key, v in object_settings(p).items()]
        vols = [(2 * k - 1, 'normal_part', p.name, vol)]
        vols += [(e, 'support_enforcer', n, t) for e, _, n, t in extra.get(k, [])]
        for vid, sub, vname, t in vols:
            cfg += [f'    <part id="{vid}" subtype="{sub}">\n',
                    f'      <metadata key="name" value={quoteattr(vname)}/>\n',
                    f'      <metadata key="matrix" value="1 0 0 {_f(t[0])} 0 1 0 {_f(t[1])} 0 0 1 {_f(t[2])} 0 0 0 1"/>\n',
                    '      <mesh_stat edges_fixed="0" degenerate_facets="0" facets_removed="0" facets_reversed="0" backwards_edges="0"/>\n',
                    '    </part>\n']
        cfg.append('  </object>\n')
    for pi, (pname, parts) in enumerate(plates):
        cfg += ['  <plate>\n', f'    <metadata key="plater_id" value="{pi + 1}"/>\n',
                f'    <metadata key="plater_name" value={quoteattr(pname)}/>\n',
                '    <metadata key="locked" value="false"/>\n',
                '    <metadata key="filament_map_mode" value="Auto For Flush"/>\n',
                '    <metadata key="gcode_file" value=""/>\n']
        for k, p, qi, off, vol in objects:
            if qi == pi:
                cfg += ['    <model_instance>\n', f'      <metadata key="object_id" value="{2 * k}"/>\n',
                        '      <metadata key="instance_id" value="0"/>\n',
                        f'      <metadata key="identify_id" value="{100 + k}"/>\n', '    </model_instance>\n']
        cfg.append('  </plate>\n')
    cfg.append('  <assemble>\n  </assemble>\n</config>\n')
    files['Metadata/model_settings.config'] = ''.join(cfg)
    files['Metadata/project_settings.config'] = settings_text
    files['Metadata/slice_info.config'] = (
        '<?xml version="1.0" encoding="UTF-8"?>\n<config>\n  <header>\n'
        '    <header_item key="X-BBL-Client-Type" value="slicer"/>\n'
        f'    <header_item key="X-BBL-Client-Version" value="{CLIENT_VERSION}"/>\n'
        '    <header_item key="OrcaSlicer-Version" value="2.4.0-dev"/>\n  </header>\n</config>\n')
    files['Metadata/filament_sequence.json'] = json.dumps(
        {f'plate_{i + 1}': {'nozzle_sequence': [], 'optimal_assignment': [], 'sequence': []} for i in range(len(plates))},
        separators=(',', ':'))
    files['[Content_Types].xml'] = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
        ' <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
        ' <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>\n'
        ' <Default Extension="png" ContentType="image/png"/>\n'
        ' <Default Extension="gcode" ContentType="text/x.gcode"/>\n</Types>\n')
    files['_rels/.rels'] = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        f' <Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="{MODEL_REL}"/>\n</Relationships>\n')

    order = ['[Content_Types].xml', '_rels/.rels', '3D/3dmodel.model', '3D/_rels/3dmodel.model.rels',
             *[f'3D/Objects/object_{k}.model' for k, *_ in objects],
             'Metadata/project_settings.config', 'Metadata/model_settings.config', 'Metadata/slice_info.config',
             'Metadata/filament_sequence.json']
    assert sorted(order) == sorted(files)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.3mf.tmp')
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name in order:
            zi = zipfile.ZipInfo(name, FIXED_DATE)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, files[name].encode('ascii'))
    tmp.replace(path)
    return objects


def missing_parts(case):
    def parts(groups):
        for g in groups:
            if isinstance(g, Part):
                yield g
            else:
                yield from parts(g)
    return [str(p.stl) for _, *groups in case['plates'] for p in parts(groups) if not p.stl.exists()]


def lay_out(case):
    """Each plate of case['plates'] laid out, the lid's support enforcers placed (inside the lid's own box) and the
    plate checked (check_plate). -> [(plate name, [Part])]; exits on any layout error. A case with a 'printer' (the
    per-configuration projects) is laid out and checked for it: a generic plate is (name, front, back, cols, side),
    laid out by layout_compact."""
    pr = PRINTERS[case.get('printer', 'cc2')]
    plates, errs = [], []
    for pname, *groups in case['plates']:
        parts = layout_compact(*groups, pr['area']) if pr['area'] else layout(*groups)
        for p in parts:
            if p.side_keys:
                p.enforcers = side_key_enforcers(p.side_keys)
                p.key_zones = side_key_zones(p.side_keys)
                p.key_bases = side_key_bases(p.side_keys)
                for n, m in p.enforcers:         # inside the part's own box, so the layout's gaps still hold
                    if (m.bounds[0][:2] < 0).any() or (m.bounds[1][:2] > p.mesh.extents[:2]).any():
                        errs.append(f'{p.name}: {n} is outside the part')
        for p in parts:
            if p.spin and (p.enforcers or p.turned):
                errs.append(f'{p.name}: spun and turned, or spun with enforcers')
        e, gap = check_plate(parts, pr['bed'], pr['exclude'], pr['area'])
        errs += [f'{pname}: {x}' for x in e]
        plates.append((pname, parts))
        lo = np.min([p.mesh.bounds[0] for p in parts], axis=0)
        hi = np.max([p.mesh.bounds[1] for p in parts], axis=0)
        sup = [f', supports on the {p.name} only, {len(p.enforcers)} enforcers (its side keys)'
               for p in parts if p.enforcers]
        print(f'  {pname}: {len(parts)} objects, x {lo[0]:.1f}-{hi[0]:.1f}, y {lo[1]:.1f}-{hi[1]:.1f}, '
              f'closest {gap:.1f} mm, {sum(p.efc0 for p in parts)} with EFC 0, {sum(p.raft for p in parts)} on a raft'
              + ''.join(sup))
    if errs:
        sys.exit('layout errors:\n  ' + '\n  '.join(errs))
    return plates


def build(case, settings_text):
    for a, b in case['shared']:
        if a.read_bytes() != b.read_bytes():
            sys.exit(f'{a.name}: {a.parent.parent.name} and {b.parent.parent.name} differ; this script assumes one shared part')
    missing = missing_parts(case)
    if missing:
        sys.exit('missing (run src/plates.py for every print build): ' + ', '.join(missing))
    plates = lay_out(case)
    write_3mf(case['out'], case['title'], plates, settings_text)
    print(f'  -> {case["out"].relative_to(HERE.parent)} ({case["out"].stat().st_size} bytes)')


# ---------------------------------------------------------------- per-configuration projects (the 4.26's 32)

CONFIGS = HERE / 'case-426' / 'out' / 'configs'      # the generic projects (the website's); cc2: out/configs-cc2
# Every part's role owns a block of 16 object ids in every per-configuration project (the lid's support enforcers take
# the ids after its own). A configuration holds at most one distinct part per role, so the ids are unique in every
# package (Orca's CLI crashes on a repeated one), and a part's file is the same whatever is written with it or before.
ROLE_IDS = {'midplate': 1001, 'tub': 1017, 'lid': 1033, 'key-426': 1049, 'crank-T': 1065, 'gate': 1081,
            'rod-jig': 1097, 'crank-M': 1113, 'key-x3std': 1129}    # key-x3std: the 3.68's bottom key (--size 368)
CONFIG_WORDS = {'panel': {'standard': 'touch panel', 'light-strip': 'light strip'},
                'chin': {True: 'bottom keys', False: 'chinless'},
                'sides': {'all': 'all four side keys', 'leftkeys': 'left pair of side keys',
                          'rightkeys': 'right pair of side keys', 'upperkeys': 'upper pair of side keys'},
                'dev': {True: 'J6', False: 'no J6'}}
APEM_PLATE = 'Only for APEM MJTP1117 boards: crank-M'


def load_variants():
    """case-426/src/variants.py (the slugs; standard library only, no side effects), read from its file."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('variants', HERE / 'case-426' / 'src' / 'variants.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def config_case(V, slug, printer='generic'):
    """One configuration's plates: plate 1 the case (its tub, its lid, the midplate, and with bottom keys the keys,
    cranks, gates and the rod jig), plate 2 (bottom keys only) the APEM boards' cranks. cc2: laid out as the plate
    file's (256 bed); generic: layout_compact's (220 x 210, the midplate turned on the plate)."""
    c, a = V.parse(slug), V.axes(slug)
    build_dir = HERE / 'case-426' / 'out' / slug
    src = build_dir / 'print'
    words = ', '.join(CONFIG_WORDS[x][a[x]] for x in V.AXES)
    rows = [[Part('midplate', src / 'midplate.stl')],
            [Part('tub', src / 'tub.stl'), Part('lid', src / 'lid.stl', side_keys=build_dir)]]
    cols = []
    if c.bottom_keys:
        cols = [[Part(f'key-426 {i}', src / 'key-426.stl') for i in range(1, 5)],
                [Part(CRANK_T.format(i), src / 'crank-T.stl') for i in range(1, 5)],
                [Part('gate 1', src / 'gate.stl'), Part('gate 2 (spare)', src / 'gate.stl'),
                 Part('rod jig (straighten and cut the rod)', ROD_JIG)]]
    plates = [(f'Case: {words}', rows, cols)]
    if c.bottom_keys:
        plates.append((APEM_PLATE, [], [[Part(CRANK_M.format(i), src / 'crank-M.stl') for i in range(1, 5)]]))
    if printer == 'generic':
        rows[0][0].spin = True
        side = [cols[2].pop()] if cols else []          # the rod jig, beside the lid
        plates = [(plates[0][0], rows[0], rows[1], cols, side)] + [(n, [], [], cl, []) for n, _, cl in plates[1:]]
    return dict(title=f'Silkscreen 4.26 case {slug} ({words})', plates=plates, side_keys=V.SIDE_SETS[c.sides],
                cad=[build_dir / 'lid.stl', build_dir / 'lid_body.stl'], printer=printer)


# The 3.68's per-configuration projects (--size 368): its one released configuration, the standard build (the bare x3
# panel, the bottom keys, x3's three side keys); the light-strip 3.68 is not released, so it has no project
CONFIGS_368 = ('standard',)
SIDE_KEYS_368 = ('SW1', 'SW4', 'SW7')        # the 3.68 lid's side keys (build.py's skey_*.stl), one enforcer each


def config_case_368(slug, printer='generic'):
    """The 3.68 standard case's plates, as config_case lays out a 4.26 configuration with bottom keys: plate 1 its tub,
    lid and midplate, 4 key-x3std, 4 crank-T, 2 gates (one spare) and the rod jig; plate 2 the APEM boards' crank-M."""
    assert slug in CONFIGS_368, slug
    build_dir = HERE / 'case-368' / 'out' / slug
    src = build_dir / 'print'
    words = 'standard: bare x3 panel, bottom keys, three side keys'
    rows = [[Part('midplate', src / 'midplate.stl')],
            [Part('tub', src / 'tub.stl'), Part('lid', src / 'lid.stl', side_keys=build_dir)]]
    cols = [[Part(f'key-x3std {i}', src / 'key-x3std.stl') for i in range(1, 5)],
            [Part(CRANK_T.format(i), src / 'crank-T.stl') for i in range(1, 5)],
            [Part('gate 1', src / 'gate.stl'), Part('gate 2 (spare)', src / 'gate.stl'),
             Part('rod jig (straighten and cut the rod)', ROD_JIG)]]
    plates = [(f'Case: {words}', rows, cols),
              (APEM_PLATE, [], [[Part(CRANK_M.format(i), src / 'crank-M.stl') for i in range(1, 5)]])]
    if printer == 'generic':
        rows[0][0].spin = True
        side = [cols[2].pop()]                          # the rod jig, beside the lid
        plates = [(plates[0][0], rows[0], rows[1], cols, side), (plates[1][0], [], [], plates[1][2], [])]
    return dict(title=f'Silkscreen 3.68 case {slug} ({words})', plates=plates, side_keys=SIDE_KEYS_368,
                cad=[build_dir / 'lid.stl', build_dir / 'lid_body.stl'], printer=printer)


def part_model(p):
    """A distinct part's model file, as every per-configuration project holds it (3D/Objects/<name>.model): the
    oriented part centred on its box as object ROLE_IDS[role], then its support enforcers (the lid's) as the next ids,
    each centred on its own box, as write_3mf places them. -> (name, text, meta): the name is the role and the hash of
    the text, so a name always holds the same bytes; meta is what the assembler needs (each volume's id, subtype, name
    and offset from the part's centre, z from the bed)."""
    role = p.stl.stem
    oid = ROLE_IDS[role]
    assert len(p.enforcers) < 16, p.name
    lo, hi = p.base.min(axis=0), p.base.max(axis=0)
    c0, size = (lo + hi) / 2, hi - lo
    vols = [(oid, 'normal_part', role, trimesh.Trimesh(p.base - c0, p.mesh.faces, process=False), (0.0, 0.0, c0[2]))]
    for j, (ename, em) in enumerate(p.enforcers, start=1):
        emid = (em.bounds[0] + em.bounds[1]) / 2
        vols.append((oid + j, 'support_enforcer', ename, trimesh.Trimesh(em.vertices - emid, em.faces, process=False),
                     (emid[0] - c0[0], emid[1] - c0[1], emid[2])))
    text = _model_xml([(i, f'{i:08x}-81cb-4c03-9d28-80fed5dfa1dc', m) for i, _, _, m, _ in vols])
    name = f'{role}-{hashlib.sha256(text.encode("ascii")).hexdigest()[:12]}'
    meta = {'role': role, 'size_mm': [round(float(s), 4) for s in size], 'turned': p.turned,
            'volumes': [{'id': i, 'subtype': sub, 'name': n, 'offset': [float(t) for t in off]}
                        for i, sub, n, _, off in vols]}
    return name, text, meta


def deflate_raw(b):
    c = zlib.compressobj(9, zlib.DEFLATED, -15)
    return c.compress(b) + c.flush()


def _write(path, data):
    """path gets data whole or not at all."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_bytes(data)
    tmp.replace(path)


SPIN = '0 1 0 -1 0 0 0 0 1'                # a recipe object's 'rot': 90, its item turned (x, y) -> (-y, x)


def assemble(rec, index):
    """A per-configuration project from its recipe and the library's index -> (the zip's entry names in order, the
    generated files' text). The same files write_3mf writes, except that every copy of a part points at the part's one
    library file (3D/Objects/<part>.model) and the project settings are the recipe's library file."""
    objects = []                                        # (k, recipe object, plate index, its part's meta)
    for pi, pl in enumerate(rec['plates']):
        for o in pl['objects']:
            objects.append((len(objects) + 1, o, pi, index['parts'][o['part']]))
    used = list(dict.fromkeys(o['part'] for _, o, _, _ in objects))
    files = {}
    model = ['<?xml version="1.0" encoding="UTF-8"?>\n', f'<model unit="millimeter" xml:lang="en-US" {NS}>\n',
             f' <metadata name="Application">{APP}</metadata>\n', ' <metadata name="OrcaSlicer">2.4.0-dev</metadata>\n',
             ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n']
    for key in ('Copyright', 'CreationDate', 'Description', 'Designer', 'DesignerCover', 'DesignerUserId', 'License',
                'ModificationDate', 'Origin'):
        model.append(f' <metadata name="{key}"></metadata>\n')
    model.append(f' <metadata name="Title">{escape(rec["title"])}</metadata>\n <resources>\n')
    for k, o, pi, part in objects:
        model += [f'  <object id="{2 * k}" p:UUID="{k:08x}-61cb-4c03-9d28-80fed5dfa1dc" type="model">\n',
                  '   <components>\n']
        for v in part['volumes']:
            t = v['offset']
            model.append(f'    <component p:path="/3D/Objects/{o["part"]}.model" objectid="{v["id"]}" '
                         f'p:UUID="{k:04x}{v["id"] - 1:04x}-b206-40ff-9872-83e8017abed1" '
                         f'transform="1 0 0 0 1 0 0 0 1 {_f(t[0])} {_f(t[1])} {_f(t[2])}"/>\n')
        model.append('   </components>\n  </object>\n')
    model.append(' </resources>\n <build p:UUID="2c7c17d8-22b5-4d84-8835-1976022ea369">\n')
    for k, o, pi, part in objects:                      # the recipe's x, y are the plate's origin + the place on it
        rot = {0: '1 0 0 0 1 0 0 0 1', 90: SPIN}[o.get('rot', 0)]     # about the part's centre (its library frame's 0)
        model.append(f'  <item objectid="{2 * k}" p:UUID="{2 * k:08x}-b1ec-4553-aec9-835e5b724bb4" '
                     f'transform="{rot} {_f(o["x"])} {_f(o["y"])} 0" printable="1"/>\n')
    model.append(' </build>\n</model>\n')
    files['3D/3dmodel.model'] = ''.join(model)
    rels = ['<?xml version="1.0" encoding="UTF-8"?>\n',
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n']
    rels += [f' <Relationship Target="/3D/Objects/{n}.model" Id="rel-{i + 1}" Type="{MODEL_REL}"/>\n'
             for i, n in enumerate(used)]
    rels.append('</Relationships>\n')
    files['3D/_rels/3dmodel.model.rels'] = ''.join(rels)
    cfg = ['<?xml version="1.0" encoding="UTF-8"?>\n<config>\n']
    for k, o, pi, part in objects:
        cfg += [f'  <object id="{2 * k}">\n', f'    <metadata key="name" value={quoteattr(o["name"])}/>\n',
                '    <metadata key="extruder" value="1"/>\n']
        cfg += [f'    <metadata key="{key}" value="{val}"/>\n' for key, val in o['settings'].items()]
        for v in part['volumes']:
            name = o['name'] if v['subtype'] == 'normal_part' else v['name']
            t = v['offset']
            cfg += [f'    <part id="{v["id"]}" subtype="{v["subtype"]}">\n',
                    f'      <metadata key="name" value={quoteattr(name)}/>\n',
                    f'      <metadata key="matrix" value="1 0 0 {_f(t[0])} 0 1 0 {_f(t[1])} 0 0 1 {_f(t[2])} 0 0 0 1"/>\n',
                    '      <mesh_stat edges_fixed="0" degenerate_facets="0" facets_removed="0" facets_reversed="0" backwards_edges="0"/>\n',
                    '    </part>\n']
        cfg.append('  </object>\n')
    for pi, pl in enumerate(rec['plates']):
        cfg += ['  <plate>\n', f'    <metadata key="plater_id" value="{pi + 1}"/>\n',
                f'    <metadata key="plater_name" value={quoteattr(pl["name"])}/>\n',
                '    <metadata key="locked" value="false"/>\n',
                '    <metadata key="filament_map_mode" value="Auto For Flush"/>\n',
                '    <metadata key="gcode_file" value=""/>\n']
        for k, o, qi, part in objects:
            if qi == pi:
                cfg += ['    <model_instance>\n', f'      <metadata key="object_id" value="{2 * k}"/>\n',
                        '      <metadata key="instance_id" value="0"/>\n',
                        f'      <metadata key="identify_id" value="{100 + k}"/>\n', '    </model_instance>\n']
        cfg.append('  </plate>\n')
    cfg.append('  <assemble>\n  </assemble>\n</config>\n')
    files['Metadata/model_settings.config'] = ''.join(cfg)
    files['Metadata/slice_info.config'] = (
        '<?xml version="1.0" encoding="UTF-8"?>\n<config>\n  <header>\n'
        '    <header_item key="X-BBL-Client-Type" value="slicer"/>\n'
        f'    <header_item key="X-BBL-Client-Version" value="{CLIENT_VERSION}"/>\n'
        '    <header_item key="OrcaSlicer-Version" value="2.4.0-dev"/>\n  </header>\n</config>\n')
    files['Metadata/filament_sequence.json'] = json.dumps(
        {f'plate_{i + 1}': {'nozzle_sequence': [], 'optimal_assignment': [], 'sequence': []}
         for i in range(len(rec['plates']))}, separators=(',', ':'))
    files['[Content_Types].xml'] = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
        ' <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
        ' <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>\n'
        ' <Default Extension="png" ContentType="image/png"/>\n'
        ' <Default Extension="gcode" ContentType="text/x.gcode"/>\n</Types>\n')
    files['_rels/.rels'] = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        f' <Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="{MODEL_REL}"/>\n</Relationships>\n')
    order = ['[Content_Types].xml', '_rels/.rels', '3D/3dmodel.model', '3D/_rels/3dmodel.model.rels',
             *[f'3D/Objects/{n}.model' for n in used], 'Metadata/project_settings.config',
             'Metadata/model_settings.config', 'Metadata/slice_info.config', 'Metadata/filament_sequence.json']
    return order, files


def zip_bytes(order, files, rec, index, lib, store=False):
    """The project's zip, written by hand (no zip64, no data descriptors, the fixed date): the generated files
    deflated (store: kept as they are, as a web page that only copies bytes would), the library's files copied as
    they are stored (raw deflate, their CRC and sizes from the index)."""
    out, central = bytearray(), bytearray()
    dos_time, dos_date = 0, (FIXED_DATE[0] - 1980) << 9 | FIXED_DATE[1] << 5 | FIXED_DATE[2]
    for name in order:
        nb = name.encode('ascii')
        if name in files:
            raw = files[name].encode('ascii')
            data, method = (raw, 0) if store else (deflate_raw(raw), 8)
            crc, size = zlib.crc32(raw), len(raw)
        else:
            blob = rec['settings'] if name == 'Metadata/project_settings.config' else name[11:-6]   # 3D/Objects/<>.model
            e = index['settings' if blob == rec['settings'] else 'parts'][blob]
            data = (lib / f'{blob}.dfl').read_bytes()
            if len(data) != e['csize']:
                sys.exit(f'{lib / blob}.dfl: {len(data)} bytes, the index says {e["csize"]}')
            crc, size, method = e['crc32'], e['size'], 8
        off = len(out)
        out += struct.pack('<IHHHHHIIIHH', 0x04034b50, 20, 0, method, dos_time, dos_date, crc, len(data), size, len(nb), 0)
        out += nb + data
        central += struct.pack('<IHHHHHHIIIHHHHHII', 0x02014b50, 0x0314, 20, 0, method, dos_time, dos_date, crc,
                               len(data), size, len(nb), 0, 0, 0, 0, 0o644 << 16, off)
        central += nb
    cd = len(out)
    out += central
    out += struct.pack('<IHHHHIIH', 0x06054b50, 0, 0, len(order), len(order), len(central), cd, 0)
    return bytes(out)


def _read_json(path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def code_hash(size='426'):
    """The code a configuration's files were made with, as 12 hex digits: the case's (size's) modules that make its parts
    (build.py's and plates.py's imports, followed through src/ as pipeline.py's step keys follow them; so an edit of
    the runner or a check-only script does not count) and this file, line endings normalised (the same on any
    checkout of one commit). index.json records it per entry ('code'), so after a code change a partial run's entries
    can be told from the older ones."""
    import ast
    src = HERE / f'case-{size}' / 'src'
    seen, todo = set(), ['build', 'plates']
    while todo:
        m = todo.pop()
        if m in seen or m in ('pipeline', '_step') or not (src / f'{m}.py').exists():   # the runner (pipeline.NOT_CODE)
            continue
        seen.add(m)
        for n in ast.walk(ast.parse((src / f'{m}.py').read_text(encoding='utf-8'))):
            if isinstance(n, ast.Import):
                todo += [a.name.split('.')[0] for a in n.names]
            elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
                todo.append(n.module.split('.')[0])
    h = hashlib.sha256()
    for f in [*(src / f'{m}.py' for m in sorted(seen)), Path(__file__).resolve()]:
        h.update(f.name.encode() + b'\0' + f.read_bytes().replace(b'\r\n', b'\n') + b'\0')
    return h.hexdigest()[:12]


SIDE_CHOICE = {'all': 'All four', 'leftkeys': 'Left pair', 'rightkeys': 'Right pair', 'upperkeys': 'Upper pair'}


def configs_readme(V, listing, printer='generic', size='426'):
    """out/configs/README.md (cc2: out/configs-cc2/): which file each website-builder choice gets, and the builder
    note (print/SITE-BUILDER-NOTE.md: the side keys as one four-way choice; Ian changes the site later). The 3.68
    (size 368): its one file."""
    if size == '368':
        e = listing.get('standard')
        f = f"`{e['file']}` ({e['bytes'] / 1e6:.2f} MB)" if e else '`standard.3mf` (not made yet)'
        if printer == 'generic':
            head = ("Made by `make_plates.py configs --size 368`; not in git. The OrcaSlicer project of the 3.68 case's\n"
                    "one released configuration, the standard build (bare x3 panel, bottom keys, three side keys):\n"
                    f"{f}. Every part it needs, plated, with its supports and rafts set; the file the website serves\n"
                    "for the 3.68. It carries OrcaSlicer's generic presets (Generic Marlin Printer 0.4 nozzle, 0.20mm\n"
                    "Standard, Generic PLA), and every plate fits a 220 x 210 mm bed. Open it in OrcaSlicer, pick your\n"
                    "own printer, and keep a 0.4 mm nozzle and 0.2 mm layers: the rafts, the lid's side-key supports\n"
                    "and the other per-part settings ride on the parts and stay. Other slicers are not supported.\n"
                    "The light-strip 3.68 is not released and has no project. `index.json` lists the file; `library/`\n"
                    "and `recipes/` hold the parts it is assembled from. Ian's Elegoo Centauri Carbon 2 version:\n"
                    "`make_plates.py configs --size 368 --printer cc2` (out/configs-cc2/).\n")
        else:
            head = ("Made by `make_plates.py configs --size 368 --printer cc2`; not in git. The Elegoo Centauri Carbon 2\n"
                    f"version of out/configs/standard.3mf: {f}. The website serves out/configs/, the generic one.\n")
        return "# The 3.68 print file" + (" (Elegoo CC2)" if printer == 'cc2' else '') + "\n\n" + head
    rows = []
    for s in V.ALL:
        c = V.parse(s)
        e = listing.get(s)
        rows.append(f"| {'FT01C (touch)' if c.panel == 'standard' else 'plain + light strip'} | "
                    f"{'on' if c.bottom_keys else 'off (chinless)'} | {SIDE_CHOICE[c.sides]} | "
                    f"{'on' if c.dev else 'off'} | "
                    + (f"`{e['file']}` ({e['bytes'] / 1e6:.2f} MB) |" if e else f"`{s}.3mf` (not made yet) |"))
    if printer == 'generic':
        head = ("Made by `make_plates.py configs` (the pipeline's configs step); not in git. One OrcaSlicer project per\n"
                "configuration: every part it needs, plated, with its supports and rafts set. These are the files the\n"
                "website serves. They carry OrcaSlicer's generic presets (Generic Marlin Printer 0.4 nozzle, 0.20mm\n"
                "Standard, Generic PLA), and every plate fits a 220 x 210 mm bed (Ender-3 class, Prusa MK4, Bambu and\n"
                "larger). Open one in OrcaSlicer, pick your own printer, and keep a 0.4 mm nozzle and 0.2 mm layers:\n"
                "the rafts, the lid's side-key supports and the other per-part settings ride on the parts and stay.\n"
                "Other slicers are not supported. `index.json` lists them; `library/` and `recipes/` hold the shared\n"
                "parts they are assembled from. Ian's own Elegoo Centauri Carbon 2 versions: `make_plates.py configs\n"
                "--printer cc2` (out/configs-cc2/).\n\n")
    else:
        head = ("Made by `make_plates.py configs --printer cc2`; not in git. The Elegoo Centauri Carbon 2 versions of\n"
                "out/configs/ (Ian's printer: its presets and a 256 mm plate). The website serves out/configs/, the\n"
                "generic ones. `index.json` lists them; `library/` and `recipes/` hold the shared parts.\n\n")
    return ("# The 4.26 per-configuration print files" + (" (Elegoo CC2)" if printer == 'cc2' else '') + "\n\n"
            + head +
            "NOTE for the website builder (see print/SITE-BUILDER-NOTE.md in the repo): its four free side-key\n"
            "toggles (16 combinations) should become one four-way choice: all four, left pair, right pair, upper\n"
            "pair. Power is on every case. Left and right are as the reader is held, screen toward you.\n\n"
            "| Panel | Bottom row | Side keys | Dev header | File |\n|---|---|---|---|---|\n"
            + '\n'.join(rows) + '\n')


def configs(V, slugs, settings_text, printer='generic', size='426'):
    """make_plates.py configs: each named configuration's project (out/configs/<slug>.3mf; cc2: out/configs-cc2/), its
    recipe, the library files it needs, and its entry in that folder's index.json (with the code that made it,
    code_hash); the configurations not named keep their last files, and a listing that then mixes code versions is
    reported. size: the case, 426 (V: its variants module) or 368 (CONFIGS_368, config_case_368; V unused)."""
    pr = PRINTERS[printer]
    CONFIGS = HERE / f'case-{size}' / 'out' / pr['dir']
    every = V.ALL if size == '426' else CONFIGS_368
    lib, recipes = CONFIGS / 'library', CONFIGS / 'recipes'
    index = _read_json(lib / 'index.json', {'parts': {}, 'settings': {}})
    listing = _read_json(CONFIGS / 'index.json', {})
    code = code_hash(size)

    def put(name, text):
        """A library file (raw-deflated), written once: its name holds its text's hash."""
        b = text.encode('ascii')
        f = lib / f'{name}.dfl'
        if not f.exists():
            _write(f, deflate_raw(b))
        return {'size': len(b), 'csize': f.stat().st_size, 'crc32': zlib.crc32(b)}

    sname = f'settings-{hashlib.sha256(settings_text.encode("ascii")).hexdigest()[:12]}'
    index['settings'][sname] = put(sname, settings_text)
    made = {}                       # the STL's bytes, its turn and its enforcers -> its library name (once a run)
    for slug in slugs:
        case = config_case(V, slug, printer) if size == '426' else config_case_368(slug, printer)
        missing = missing_parts(case) + [str(f) for f in case['cad'] if not f.exists()]
        if missing:
            sys.exit(f'{slug}: missing (run its build and plates.py first): ' + ', '.join(missing))
        print(case['title'])
        plates = lay_out(case)
        lids = [p for _, parts in plates for p in parts if p.side_keys]
        keys = case['side_keys']
        if len(lids) != 1 or len(lids[0].enforcers) != len(keys):
            sys.exit(f'{slug}: {[len(p.enforcers) for p in lids]} support enforcers on its lid, but its layout has '
                     f'{len(keys)} side keys ({", ".join(keys)})')
        origins = plate_origins(len(plates), pr['bed'])
        rec = {'title': case['title'], 'settings': sname, 'plates': []}
        layout_info = []
        for pi, (pname, parts) in enumerate(plates):
            ox, oy = origins[pi]
            objs, info = [], []
            for p in parts:
                h = hashlib.sha256(p.stl.read_bytes())
                h.update(b'T' if p.turned else b'-')
                for n, m in p.enforcers:
                    h.update(n.encode() + np.ascontiguousarray(m.vertices, dtype='<f8').tobytes())
                if h.digest() not in made:
                    name, text, meta = part_model(p)
                    index['parts'][name] = {**meta, **put(name, text)}
                    made[h.digest()] = name
                lo, hi = p.mesh.bounds
                c = (lo + hi) / 2
                objs.append({'part': made[h.digest()], 'name': p.name, 'x': float(ox + c[0]), 'y': float(oy + c[1]),
                             **({'rot': 90} if p.spin else {}), 'settings': object_settings(p, printer)})
                # what configs_slice reads the G-code back by: the object's box on the bed, its enforcers' boxes, and
                # (the lid) its side keys' zones
                info.append({'name': p.name, 'role': p.stl.stem, 'raft': p.raft,
                             'box': [round(float(v), 3) for v in (lo[0], lo[1], hi[0], hi[1])],
                             'enforcers': [{'name': n, 'box': [round(float(v), 3)
                                                               for v in (*(m.bounds[0] + lo), *(m.bounds[1] + lo))]}
                                           for n, m in p.enforcers],
                             **({'key_zones': [{'name': n, 'top': round(float(b[4]), 3),
                                                'box': [round(float(v), 3) for v in
                                                        (b[0] + lo[0], b[1] + lo[1], b[2] + lo[0], b[3] + lo[1])],
                                                'base': [round(float(v), 3) for v in
                                                         (q[0] + lo[0], q[1] + lo[1], q[2] + lo[0], q[3] + lo[1])]}
                                               for (n, b), q in ((z, p.key_bases[z[0]]) for z in p.key_zones)]}
                                if p.key_zones else {})})
            rec['plates'].append({'name': pname, 'objects': objs})
            layout_info.append({'name': pname, 'objects': info})
        _write(recipes / f'{slug}.json', json.dumps(rec, indent=1).encode())
        data = zip_bytes(*assemble(rec, index), rec, index, lib)
        _write(CONFIGS / f'{slug}.3mf', data)
        parts = sorted({o['part'] for pl in rec['plates'] for o in pl['objects']})
        listing[slug] = {'title': case['title'], 'file': f'{slug}.3mf', 'bytes': len(data),
                         'sha256': hashlib.sha256(data).hexdigest(), 'side_keys': list(keys),
                         'objects': sum(len(pl['objects']) for pl in rec['plates']), 'parts': parts,
                         'code': code, 'plates': layout_info}
        print(f'  -> {CONFIGS.name}/{slug}.3mf ({len(data)} bytes, {len(parts)} part files)')
    # the listing in variants.ALL's order (an entry whose files are gone is dropped); the library keeps the files the
    # listed configurations' recipes use
    listing = {s: listing[s] for s in every
               if s in listing and (recipes / f'{s}.json').exists() and (CONFIGS / f'{s}.3mf').exists()}
    used = set()
    for s in listing:
        rec = json.loads((recipes / f'{s}.json').read_text())
        used |= {rec['settings'], *(o['part'] for pl in rec['plates'] for o in pl['objects'])}
    for kind in ('parts', 'settings'):
        index[kind] = {n: e for n, e in sorted(index[kind].items()) if n in used}
    for f in [*lib.glob('*.dfl'), *CONFIGS.glob('*.3mf'), *recipes.glob('*.json')]:
        if f.stem not in used and f.stem not in listing:
            f.unlink()
    _write(lib / 'index.json', json.dumps(index, indent=1, sort_keys=True).encode())
    _write(CONFIGS / 'index.json', json.dumps(listing, indent=1).encode())
    _write(CONFIGS / 'README.md', configs_readme(V, listing, printer, size).encode())
    roles = {}
    for n in index['parts']:
        roles[n.rsplit('-', 1)[0]] = roles.get(n.rsplit('-', 1)[0], 0) + 1
    print(f'{len(listing)} configurations in {CONFIGS} '
          f'({sum(e["bytes"] for e in listing.values()) / 1e6:.1f} MB); the library: {len(index["parts"])} distinct '
          f'parts ({", ".join(f"{k} {v}" for k, v in sorted(roles.items()))})')
    old = [s for s, e in listing.items() if e.get('code') != code]
    if old:
        print(f'NOTE: {len(old)} of the {len(listing)} configurations in index.json were made by other code than this '
              f'run\'s ({code}): {", ".join(old)}. Run make_plates.py configs --size {size} --printer {printer} for all of them '
              '(after their builds) before publishing the files.')


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('what', nargs='?', choices=('plates', 'configs'), default='plates',
                    help='plates: the two plate files in print/ (the default); configs: the per-configuration projects')
    ap.add_argument('--builds', default='all', help='configs: the slugs, comma-separated, or all (the default)')
    ap.add_argument('--size', choices=('426', '368'), default='426',
                    help='configs: the case, 426 (the default: its 32 configurations, case-426/out/configs/) or 368 '
                         '(its one released configuration, standard: case-368/out/configs/)')
    ap.add_argument('--printer', choices=tuple(PRINTERS), default='generic',
                    help="configs: generic (the default: OrcaSlicer's generic presets, a 220 x 210 bed; out/configs/, "
                         "what the website serves) or cc2 (Ian's Elegoo Centauri Carbon 2; out/configs-cc2/)")
    o = ap.parse_args()
    text, changed = project_settings(o.printer if o.what == 'configs' else 'cc2')
    print('project settings: stock presets', ', '.join(n for _, n in PRINTERS[o.printer if o.what == 'configs'
                                                                            else 'cc2']['presets'].values()),
          '; different_settings_to_system:', changed or 'nothing', '; plate:', BED_TYPE)
    if o.what == 'configs' and o.size == '368':
        slugs = list(CONFIGS_368) if o.builds == 'all' else [s for s in o.builds.split(',') if s]
        if not slugs or any(s not in CONFIGS_368 for s in slugs):
            sys.exit(f'--builds: the 3.68 has {", ".join(CONFIGS_368)} only (the light-strip 3.68 is not released)')
        configs(None, slugs, text, o.printer, '368')
    elif o.what == 'configs':
        V = load_variants()
        slugs = list(V.ALL) if o.builds == 'all' else [s for s in o.builds.split(',') if s]
        for s in slugs:
            try:
                V.parse(s)
            except ValueError as ex:
                sys.exit(f'--builds: {ex}')
        configs(V, slugs, text, o.printer)
    else:
        for make in (case_426, case_368):
            c = make()
            print(c['title'])
            build(c, text)
