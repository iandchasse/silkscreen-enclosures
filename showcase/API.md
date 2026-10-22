# Silkscreen showcase: data contract and page API

One case-centric page for both case sizes (4.26" and 3.68") and both builds (standard and light strip). It keeps
the Rev K showcase's layout: a sticky 3D stage with part chips, explode, section, press, Play assembly, and a tour
of mechanism cards with live section drawings. The light strip is one card, placed right after the bottom-keys card.

The source of truth for everything in sections 1-3 is `gen/sc_contract.py` (schema, tables and validator). This
file explains it. If the two disagree, the code wins; fix this file.

**Rebuilding the page (since the 2026-09-28 restructure).** The case projects are `enclosures/case-426` and
`enclosures/case-368`, and their print files are in the repo's `print/4.26/` and `print/3.68/`. After a case build, run
each adapter from its project folder with that project's Python (`$py426` and `$py368` below: a Python 3.11 virtual
environment made from that project's `requirements.txt`), then the bundler from the repo root:

```powershell
cd enclosures\case-426; & $py426 -B ..\..\showcase\gen\adapt_426.py
cd ..\case-368;        & $py368 -B ..\..\showcase\gen\adapt_368.py
cd ..\..;              python -B showcase\gen\bundle.py --strict-page      # add --mirror DIR for a copy to publish
```

The adapters write to `showcase/build/426/` and `showcase/build/368/` (not in git), where the bundler reads by
default. Sections 6-17 below are the development log, dated as written: the paths there are the ones of the day, and
the `scratchpad/...` test tools they name were working files that were not kept.

```
showcase/
  API.md                 this file
  gen/
    sc_contract.py       schema, node rules, groups, cards, presets and drawings lists, crank kinematics
                         (reference), validators, a hand-made sample
    sc_lib.py            meshing, board meshes, screws, sections/drawings, GLB model files, zip, split helpers
    adapt_426.py         4.26 adapter (run in the 4.26 venv, from that project's root)
    adapt_368.py         3.68 adapter (x3 venv)
    bundle.py            merges the adapters' outputs into docs/showcase/ (and, with --mirror, a copy to publish)
  page/
    shell.html           masthead, stage bar, stage markup, CSS, page core (SC bus, state, loader, Drawing, bindings)
    viewer.js            three.js stage (ES module)
    strip3d.js           the light strip's fold, tape and light (ES module, drives the same scene)
    strip.json           the light strip's geometry for strip3d.js and the strip card (hand-kept; the bundler copies it)
    cards/<id>.html      one tour card's markup (an <article>)
    cards/<id>.js        that card's script (SC.card({...}))
docs/showcase/           the bundle: index.html + the data files below (replaces the old light-strip page)
```

Run the self-test with `python -B gen/sc_contract.py --selftest`. Validate a finished bundle with
`python -B gen/sc_contract.py --bundle docs/showcase`. Either venv works: the contract uses only the standard
library, and `sc_lib` needs trimesh, shapely and numpy (plus CadQuery for `tess` and the board functions).

## 1. Frame, sizes, builds, variants

- **CAD frame (mm)**, shared by both projects:
  - X = KiCad x - 44.24
  - Y = 148.25 - KiCad y
  - Z = 0 at the board's rear face, +Z toward the screen
  - The light-strip page's `dev(x, y)` is this frame too, so its cameras port unchanged.
- **`size`**: `'426'` or `'368'`. Labels `4.26"` and `3.68"`.
- **`build`**: `'std'` or `'ls'`. On disk these are the case projects' `out/standard` and `out/light-strip`. The 4.26
  also has `'cl'` (chinless, section 18) and `'lc'` (light-strip chinless, section 19): `sc_contract.builds_of(S)`.
- **`variant`**: `'T'` or `'M'`. It is the bottom keys' crank and switch pair:
  - `T`: crank-T with the SHOU HAN TS365ZJ, which is on every JLC board. **This is the default.**
  - `M`: crank-M with the APEM MJTP1117. Label it "APEM MJTP1117 boards".
- **Defaults**: `{size: '426', build: 'std', variant: 'T'}`.
- **Bottom keys**: `SW9, SW8, SW3, SW2`, left to right, in both sizes. The section drawing cuts through `SW8`.
- **Side keys**: 5 on the 4.26 (`SW1 SW4 SW5 SW7 SW10`), 3 on the 3.68 (`SW1 SW4 SW7`). Reset is `SW11` on both.

## 2. Files

Every file is ASCII: HTML entities in markup, `\uXXXX` in JS strings and JSON. The limits are 16 MB per file and
64 MB per version. Models ship as JSON because the host serves no `.glb`.

| file | contents | loaded |
|---|---|---|
| `manifest.json` | what exists (below) | first |
| `core-S.json` | model file: the nodes shared by both builds of size S | first paint (S) |
| `build-S-B.json` | model file: the nodes that differ per build | first paint, and on a build switch |
| `extras-S.json` | model file: `cmp_*`, `dummy_pcba` | when their chip or preset is first used |
| `data-S-B.json` | everything else for one size and build (section 3) | first paint, and on any switch |
| `models-S.js` | `window.SC_MODELS = {size, zip, zip_bytes, b64}`: the print zip | first download click |
| `strip.json`, `optics_heatmaps.png` | the light-strip card's assets, unchanged | `strip.json` (36 KB) on the first `ls` mount (`strip3d.js` builds the live strip for the strip chip); the PNG when the strip card renders |

**Model file**: `{format: 'glb-base64', schema: 'sc/1', kind: 'core'|'build'|'extras', size, build (build files only, else null), nodes: {name: {tris, hash, bbox: [x0,y0,z0,x1,y1,z1]}}, data: <base64 binary glTF>}`
- The glTF has one node and one mesh per name, in the CAD frame, with no normals: the viewer computes creased normals, as Rev K did.
- Write it with `sc_lib.write_model` (it validates and decodes before writing). Read it back with `sc_lib.read_model`.

**Manifest**:
- `schema`, `generated`, `title`.
- `defaults`: see section 1.
- `sizes.S = {label, build_diff}`. `build_diff` is the stage bar's tag, for example "tub differs" on 4.26 and "tub + 4 keys differ" on 3.68.
- `builds.B = {label}`.
- `groups` = `sc_contract.GROUPS`. `cards` = `sc_contract.CARDS`.
- `files.<name> = {bytes, kind, sha1, ...}`.
- `load.S = {core, build: {std, ls}, extras, data: {std, ls}, models}`.
- `nodes.S = {core: [...], build: {std: [...], ls: [...]}, extras: [...]}`. Both builds have the same per-build nodes, apart from `strip_*`.
- `parts.S = {shared: [...], per_build: [...]}`: printed part names, from the project's `out/shared-parts.json`.
- `assets = {strip, optics}`.

## 3. Nodes and groups

Node names are `^[a-z][a-z0-9]*(_[A-Za-z0-9]+)*$`; refs keep their case (`key_SW8`). The rules come from
`sc_contract.NODE_RULES`:

| node | file | notes |
|---|---|---|
| `tub` | build | differs per build in both sizes |
| `lid` | core | from `lid_body.stl`. Never use `lid.stl`: it has the side keys fused in, so they would show twice. |
| `skey_<ref>` | core | a side key. It is part of the lid and bends about its flex root. |
| `midplate` | core | |
| `key_<ref>` | core on 4.26, build on 3.68 | a bottom key; slides -Z. The 3.68 builds use key-x3std and key-x3ls. |
| `crank_M`, `crank_T` | core | `crank-M.stl` / `crank-T.stl`, **modelled once, centred on X = 0, at theta 0**. The viewer places each one 4 times at `keys.x[ref]` and names the instances `crank_<ref>`. |
| `rod`, `gate` | core | `ref_rod.stl`; `gate.stl`: the printed side gate, the rod's left stop, in its installed pose (the same part in both sizes; it replaced the M2.5 x 4 rod screw, SPEC2 rev 3) |
| `panel_epd`, `panel_light`, `panel_touch` | any | The 4.26 light-strip build has `panel_epd` only (plain GDEY0426T82). |
| `ribbon_*` | any | display ribbons and FPCs (x3's `fpc_*` renamed) |
| `pcba_<category>` | core | the board merged per category (`sc_lib.category`) |
| `nub_<ref>` | core | a switch plunger, split out, for the bottom, side and reset switches (x3's `plunger_*` renamed) |
| `swbody_<ref>` | core | a bottom key's MJTP1117 body, kept out of `pcba_switch` so that variant T can hide it |
| `sw_T_body`, `sw_T_nub` | core | a TS365ZJ envelope at X = 0 (`sc_lib.switch_envelope`), placed 4 times for variant T |
| `battery_cell`, `battery_leads`, `battery_plug` | core | |
| `screw_H3`, `screw_H4`, `screw_top` (4.26); `screw_bottom_left`, `screw_bottom_right`, `screw_top`, `screw_top_left` (3.68) | core | M2 socket head caps (ISO 4762) in their counterbores; the 4.26's are Rev K's `screw_1..3` renamed (section 20) |
| `strip_*` | build (ls) | light-strip reference parts that `strip3d.js` does not generate |
| `cmp_*` | extras | the Xteink X4 and its retro case. The **X4 reference model** is by Zorian22 (Thingiverse thing:7287950, CC BY-NC-SA); the retro case comes from its author's print files (`compare.py` headers). Keep the attribution. |
| `dummy_pcba` | extras | the printable PCBA dummy |

**Groups (chips)**: a node belongs to the first group it matches (`sc_contract.GROUPS`, `group_of(name)`).
- Groups and their matches:
  - `tub`: tub
  - `keys`: `key_*`
  - `rod`: rod, `gate`, `crank_*`
  - `display`: `panel_*`, `ribbon_*`, and the page's `screen` plane
  - `midplate`: midplate
  - `pcba`: `pcba_*`, `nub_*`, `swbody_*`, `sw_T_*`
  - `battery`: `battery_*`
  - `lid`: lid, `skey_*`
  - `screws`: `screw_*`
  - `strip`: `strip_*`, plus the live strip group; light-strip builds only
  - `dummy`: `dummy_pcba`; starts off; lazy
  - `compare`: `cmp_*`; starts off; lazy
- The panel chip's label comes from `meta.panel.label`.
- The `lid` group also has a Case (hide shell) toggle, which the light-strip page had.

**Variant swap**: the viewer does this for `SC.viewer.variant(v)`.
- `T`: shows `crank_T` instances and `sw_T_*` instances, and hides `crank_M` instances and `swbody_*`. `nub_<ref>` of the bottom keys is replaced by the `sw_T_nub` instances.
- `M`: the reverse.

## 4. data-S-B.json

The validator is `sc_contract.validate_data(D, nodes=..., strict=True, needs=[...])`. The top-level keys are:

`schema, size, build, meta, facts, presets, explode, controls, keys, drawings, cards, checks, assembly, downloads`

### meta
- `title`, `size_label`.
- `panel {part, label, touch, front_light, ribbons}`.
- `envelope [x0,x1,y0,y1,z0,z1]`: the section slider's range.
- `size [3]` across the side pads, and `body [3]`.
- `z {front, back, seam, lip, pcb_front, ...}`, `active {cx, cy, w, h}`: the page texture plane.
- `frame` (text).
- `printed {parts: [{name, count, file}], count}`: the masthead's part count. The printed parts are now tub, lid, midplate, 4 keys, 4 cranks and the rod's gate; the rod is not printed.
- `side_keys [refs]`, `bottom_keys [refs]`, `reset`.
- `source {project, generated, ...}`.
- Rev K's other meta blocks (`usb`, `tabs`, `joint`, `battery`, `detents`, ...) belong in the matching `cards.<id>` block, not in meta.

### facts
`[{id, label, value, unit?}]` fills the masthead `dl`. `value` is display text or a number.

### presets
Presets are the full camera table per size, never offsets shared between sizes (on the 3.68 the battery is in the lid).
- **Required**: Rev K's 18 presets (`home assembly keys tabs keylid usb reset stack detent ribbons battery edges close joint latch compare back dummy`), plus `strip` and `zstack`, plus `boardprep` on 3.68.
- **Fields**:
  - `cam [x,y,z]`, `tgt [x,y,z]`, and optionally `up [x,y,z]`.
  - `fit`: widen for a narrow aspect. Rev K did this for home, assembly, compare, dummy, back and keylid.
  - `sec [axis, pos, flip]`.
  - `focus [groups]` (dim the others), `show [groups]` (only these), `hide [groups]`.
  - `press`: a control id, or `true` for all; it enables the press slider.
  - `highlight [node patterns]`: shown in orange, 0xc7782a.
  - `explode` (0-1), `variant`.
  - `tag` (text) and `cap` (HTML).
- **Every card's preset must exist** (`sc_contract.CARDS[].preset`). So must every `data-show` / `data-preset` name in the card fragments; the step 6 check covers this.

### explode
`{order: [groups], offsets: {group: dz}, steps: [html, one per order entry], done: html}`.
- Parts enter the tub from behind (-Z).
- `rod` follows `keys` in the order: the cranks drop in and the rod slides in from the -X wall.

### controls
Each control is one moving thing on the stage. `SC.viewer.press(id, t)` moves it. The fields by kind:

- **`crank`** (x4): `{id: ref, label, kind, ref, node: 'key_<ref>', crank: 'crank_<ref>', plunger: 'nub_<ref>', pivot: [x, rodY, rodZ], axis: [1,0,0]}`. Its motion comes from `keys`, below.
- **`flexure`** (side keys): `{id, label, kind, ref, node: 'skey_<ref>', plunger, plunger_axis, pivot: [x,y,0], axis: [0,0,1], sign, length, gap, click_travel, max_travel}`.
  - `rotation.z = sign * d / length` for pad travel d.
  - The plunger moves `max(0, d - gap)` along `plunger_axis`. Rev K's formula is `side * sign(free - root)`.
- **`pin`** (reset): `{id, label, kind, ref, plunger, plunger_axis, pin_from, pin_to, click_travel, max_travel}`. A pin (drawn by the viewer) runs from `pin_from` to `pin_to` and on by the travel.
- **`plug`** (USB-C): `{id, label, kind, axis, from, to, insert_mm}`. A plug (drawn by the viewer) moves from `from` to `to`.

### keys: the bottom keys, exact kinematics
The page computes the kinematics from the geometry, as `showcase-keys/frag_script.html` did. It does not use a table. The same functions drive the 2D drawing and the 3D stage.

```
refs, x {ref: xc}, draw_ref, rod {yz, d, cut, gate}, axis [1,0,0], theta_built 0,
pad {c [y,z], r}, nose {r, c {M [y,z], T [y,z]}},
switches {M|T: {part, crank, label, face_y, face_worst_y (T), nub_z [z0,z1] (NOMINAL plunger),
                nub_z_worst [z0,z1] (T), nub_yz [y0,z0,y1,z1], nub_half_x, housing_yz [y0,z0,y1,z1], housing_half_x,
                travel {click, bottom}, force_N [lo,hi]}},     (geometry = sc_contract.SWITCH_GEOM, both sizes)
default_variant 'T',
derived {M|T: {theta_rest, theta_click, theta_bottom, key_rest, key_click, key_bottom}},   (nominal face)
rest_rows [{variant, face_dy, theta, key_dz, source}],    (board tolerance: face_dy -0.2 / 0 / +0.2 for M and T)
forces {lever {input_arm, output_arm, ratio}, finger_N {M [lo,hi], T [lo,hi]}, press_y, mu, source,
        press_ys [y, ...] ascending, table {"<MJTP|TS365> <N.NN>": {"mu_<mu>": [N per press_ys]}}},   (one shape)
hooks {W_OUT_mm, hook_dx [a,b], hook_h_mm, hook_tip_y, hook_z_rest [z0,z1], slot_dx [a,b], slot_back_y, slot_roof_z,
       face_down_free_travel_mm [lo,hi], rest_load_on_plunger_N, key_mass_g, source},   (test 2: the hook keys)
rod_check {press_N, bending_MPa, deflection_um, source},
checks [{id, label, ok, value?, detail?}],
instances {crank {M: 'crank_M', T: 'crank_T'}, switch {T: ['sw_T_body','sw_T_nub'], M: 'board'}}
```

The functions are the reference (`sc_contract`); the page's `SC.crank` must return the same values:

```
rot(p, th)            = rod + R(th)(p - rod)            right-handed about +X; +theta = pressed
crownZ(th)            = rot(pad.c, th).z                 the key rides the pad crown's top
keyDown(th, th0)      = crownZ(th0) - crownZ(th)         mm down (-Z) since th0 (default theta_built)
noseFront(v, th)      = rot(nose.c[v], th).y + nose.r
face(v, dy)           = switches[v].face_y + dy          dy = plunger face moved +Y (board tolerance)
plungerIn(v, th, dy)  = max(0, noseFront(v, th) - face(v, dy))
thetaAt(v, y)         = bisection on [-40, 40], 60 steps, noseFront(v, th) = y
rest / click / bottom = thetaAt(v, face), thetaAt(v, face + travel.click), thetaAt(v, face + travel.bottom)
```

**3D**:
- `crank_<ref>.rotation.x = rad(th - theta_built)`, with its pivot at `(x, rod.y, rod.z)`.
- `key_<ref>.position.z = -keyDown(th, theta_built)`.
- The plunger node's `position.y = plungerIn(v, th, 0)`.
- The 3D board is nominal (dy = 0). The tolerance rows are readouts and a selector in the keys card, not stage motion.

**Readouts**: crank angle `th`, key down `keyDown(th, rest)`, plunger in, and switch state:
- `open` below click
- `clicked` from click
- `bottom` within 0.05 deg of bottom

**Press slider**: t in 0-1 maps to `th = rest + t * (bottom - rest)`. The x4 exaggeration multiplies `(th - rest)`.

Nominal values (these checks passed: see "Checked" below):
- M: rest 0, click 4.83 deg (key 0.412 mm), bottom 8.68 deg (0.731 mm).
- T: rest 0, click 4.81 deg (0.410 mm), bottom 8.62 deg (0.726 mm).
- T at the worst tip (face_dy -0.2): rest -3.92 deg.

**Adapters, sign conventions**:
- 4.26 `bottom-keys.json` `static["<SW> crank-<v> delta d"]`: `face_dy = -d`, because delta moves the board -Y. `key_dz = -key_lift`.
- x3 `crank.json` `rest[ref]["<part> +d"]`: `face_dy = +d`. `key_dz = -key_lift`.
- The validator recomputes each row and fails when theta is off by more than 0.015 deg or key_dz by more than 0.0015 mm. This is the independent check, so do **not** fill the rows from the reference functions.
- **Mechanics mapping**:
  - `forces`: 4.26 `mechanics.key_forces` (`lever`, and `finger_force_N["MJTP 1.27 mu 0.3"]["y -6.20"]`...); x3 `key_forces["mu_0.3"].finger_force_N["MJTP 1.27"][i]`, with i the index of press_y -6.2. Both adapters map their table through `sc_contract.force_table(rows)` to the one `table` / `press_ys` shape; the validator checks the shape and that `finger_N` is the table at `press_y`, `mu`.
  - `switches`: both adapters build the geometry from `sc_contract.switch_geom(v)` and assert their project against it: 4.26 `keys.SWITCH` (its TS365 `nub` is the worst case, so it goes to `nub_z_worst`; the nominal plunger is build.py's "crank-T on TS365, nominal" case), x3 `params.TS365` and the board STEP's MJTP1117 (face, plunger Z band, body Z0 and half-width; its 0.3 mm plunger probe cannot give the housing's front, which is why the x3 adapter used to emit `housing_yz` y0 -1.62). `sc_contract.cross_check_keys` compares the two sizes in `validate_bundle` and in the bundler.
  - `hooks` (test 2, 2026-09-30; was `drag`, the leaf's coupon band): the hook and slot numbers from each `params.py`
    (`KEY_W_OUT`, `KEY_HOOK`, `KEY_HOOK_Z`, `KEY_SLOT`, `KEY_SLOT_ROOF`, `KEY_ROOT`) and `mechanics.json key_hooks`:
    4.26 `rest` / `wall` / `x_tilt` / `pull` / `crank` / `gravity` (its `face_down_free_travel_mm` is `W_OUT` less
    `rest.rest_high_by_switch_mm.TS365`, and `W_OUT` plus the reference kinematics' lowest rest, TS365 tip and board
    +0.4; its rest load is the face-up net force at the key times the lever), x3 `params` / `window` / `walls` /
    `tilt` / `pull_out` / `crank` and `key_preload` (the rest load, gravity only). The validator checks that the hooks'
    top plus `W_OUT` is the slot's roof, the hooks' height, the hooks inside their slots in X, the tip short of the
    slot's back and 0 <= lo <= hi.
  - `rod_check`: 4.26 `key_overpress` (`press_N`, `rod_bending_MPa`, `rod_deflection_um`); x3 `crank_stress` (`press_N`, `rod.bending_MPa`, `rod.deflection_um`).
  - `checks`: 4.26 `bottom-keys.json.verdict` (label -> [ok, detail]) and `mechanics.json` `key_*` and `rod_gate` checks (an `accepted` value becomes `status: 'accepted'`); x3 `crank.json` (`failures`, `accepted_findings`, sweep and path minima, `gate`) and `mechanics.json` blocks (`gate` included), normalised to `{id, label, ok, value, detail}`.

### drawings
`[{name, axis, at, window [u0,u1,v0,v1], layers [{id, role, polys}], beyond [{id, role, at, polys}], notes}]`.
Make them with `sc_lib.drawing()`, which cuts the same meshes the model files carry.
- **Plane frames**:
  - axis x: u = Y, v = Z
  - axis y: u = X, v = Z
  - axis z: u = X, v = Y
- **Polys**: `[polygon]`, where a polygon is `[exterior ring, hole rings...]` and a ring is `[[u,v], ...]`. Every point lies inside the window.
- **Roles**: `case case2 plate pcb part nub glass lgp film key crank rod tab metal ribbon cell lead strip led tape kapton ref`.
  - `case`, `case2` and `plate` are hatched.
  - The other roles are CSS classes. `crank`, `rod`, `strip`, `led`, `tape`, `kapton` and `ref` are new since Rev K and need CSS in the shell.
- **Required names**:
  - Both sizes: `key tab_plan key_side tab_elev detent detent_plan usb usb_plan reset stack bezel ribbon clamp pin top joint_tongue joint_at_tab joint_top joint_latch`.
  - 4.26 adds `battery fence bay_lip`; 3.68 adds `bay`.
  - Light-strip builds add `strip_led` (through D4). `strip_neck` and `strip_fold` (3.68) are optional.
- **Names are stable across sizes; the refs are not.** For example, `tab_plan` is SW10 on 4.26 and SW7 on 3.68. Put the refs in `notes` (`notes.ref`) and let the card label from there.
- **The `key` drawing** has layers `tub lid key crank_M crank_T rod sw_M nub_M sw_T nub_T`.
  - Cranks are at theta 0. Switches are nominal envelopes at `keys.x[draw_ref]`.
  - Optional layers: `pcb` and panel layers.
  - Beyond: `cheek` (the crank at x - 4.5) and the rail ring.
  - The keys card shows the layers for the current variant.
  - Window `[-9.8, 4.2, -7.4, 8.8]` works for both sizes.

### cards
`cards.<id>` holds one block per card that applies to this size and build (it may be `{}`). It carries that card's numbers and structures. Known shapes (validated):
- `glance.bullets [html]`
- `zstack.bars [{name, z [z0,z1]}]`: both sizes (the 4.26 adapter needs its own stack too)
- `battery.depth_map {x0, y0, res, nx, ny, depth[ny][nx], on[ny][nx], outline}`: 3.68, from x3 `depth_map()`
- `boardprep {trim_y 86.25, trim_kicad_y 62.00, fit [R72 R74], remove [R36 R73], leave_off [SW5]}`: 3.68
- `compare.attribution`: must name Zorian22
- `checks {count, failed, measure [html]}`: `measure` is Rev K's "Measure before printing", per size and build (battery, panel thickness and switch travel, ribbon / FPC bend radius, USB-C overmold and short seat, plunger tape vs the side keys' gap, lid seating, the microSD socket, a real TS365ZJ before crank-T, the chin coupon (the hook keys' optional fit check; was the drag / tuning coupon), the gate coupon, the rod with its taper and square tail; `ls` adds the strip's stack). Required; the checks card shows it under "Measure before printing".
- `strip.steps [{t, cam [[cam],[tgt]], f, tape?, kapton?, cutX?, cutY?, caseOn?, cut?, b (html)}]`: required on `ls`. Also `strip.case_cards` (the per-size bullets) and `strip.diff` (the build-diff rows).

Content the critique lists as dropped must be kept: the X4 compare stack chart (in `compare` or `zstack`), the keylid and back presets, the masthead part count and mass, and the strip card's case bullets.

### checks, assembly, downloads
- **`checks`**: `[{id, label, ok (true/false/null = not run), value?, detail?, source?}]`. They are generated from interference, insertion, mechanics sweeps, the bottom-keys / crank verdicts and slicing. No prose.
- **`assembly`**: `[{id, title, text (html), groups [...], preset?}]`, per size and build.
  - The bottom-keys steps, in the READMEs' order: `keys` (in from inside, hooks up their slots, until both hooks stop under the roof; the tub face down until the board is in), `cranks` (dropped in, let go), `rod` (in from the -X wall, tail flush) and `gate` (dropped into its slot; its bevel cams the rod home). The lid step says the rim closes over the gate.
  - 3.68 adds board prep and the battery in the lid, which folds like a book.
  - `ls` inserts the strip steps.
- **`downloads`**: `{file: 'models-S.js', zip, zip_bytes, js_bytes, readme, groups [{id, label, what, files [{path, bytes, builds?}]}]}`.
  - One zip per size holds the shared parts once, both tubs, both 3.68 key sets, the coupons, `ROD.txt` (the rod notes) and the PCBA dummy.
  - One layout in both sizes (`sc_contract.ZIP_DIRS`, checked in strict validation and by the bundler): `shared/`, `standard/`, `light-strip/`, `dummy/`, with `README.txt` and `ROD.txt` at the top; groups `shared, std, ls, rod, dummy` in that order; `builds` is `['std']` / `['ls']` on the build folders' files and absent elsewhere.
  - Print files kept out of the zip, by name prefix per size (`sc_contract.ZIP_NOT_SHOWN`): at first those of builds the showcase did not show yet; since section 18 the chinless tub's and lid's STEP files, and since section 19 also the light-strip chinless tub's, which would take `models-426.js` past the 16,000,000-byte file limit. The adapter leaves them out, and the bundler's "every print file is in the zip" check skips them with a note (and fails if one is in the zip).
  - Download names (`sc_contract.download_names`, `files.js zipName`): everything `<zip>`, a build `<base>-<dir>.zip`, a group `<base>-<dir or id>-only.zip`. All 16 names across both sizes differ.
  - The zip name must match `silkscreen-*.zip` (for example `silkscreen-case-4.26.zip`). No hard-coded `silkscreen-rev-k-` names anywhere.
  - Measured sizes: 4.26 about 8.3 MB zip, 11.1 MB as `models-426.js`; 3.68 about 5.2 MB zip, 7.0 MB as js.

## 5. Page API

Everything goes through one global, `window.SC`. The shell's core script (in `page/shell.html`) defines it before
any card script runs. `viewer.js` and `strip3d.js` are ES modules that attach to it. The code is the reference:
`page/shell.html` (core) and `page/viewer.js` (stage). This section was brought up to date in step 3.

### Load order (how index.html runs)
1. `SC_BOOT` (the manifest, inlined by the bundler), then the core script: `SC` exists, nothing is loaded yet.
2. The card scripts: each `SC.card({...})` registers synchronously.
3. `SC._boot()` (a one-line script the shell places right after `<!--SC:CARD_SCRIPTS-->`): reads the hash and the
   stored default, starts fetching `data-S-B` + `core-S` + `build-S-B`, then renders every card and binds.
4. The importmap and the module scripts (`viewer.js`, `strip3d.js`). They wait for three.js from jsdelivr, so the
   cards usually render before the stage exists. The viewer mounts whatever `SC.data` holds when it arrives; the
   shell never waits for it. If WebGL fails, `SC.viewer` stays null and the drawings still work.

Globals for tests: `SC.ready` (true after the first data bind) and `SC.viewer.stats().parts > 0` (stage mounted).
`SC.timing` = `{ready, viewer, cards_ms}`: ms since navigation start for the first bind and the first stage mount, and
the duration of the last full card render (step 5). Model files (`core`, `build`, `extras`) are fetched with
`priority: 'low'`, data files and assets with `'high'`, so the cards' numbers are not queued behind 5 MB of meshes.

### Bus and state
- **`SC.on(ev, fn)`** returns an `off()` function. **`SC.emit(ev, arg)`** calls the listeners synchronously; a
  throwing listener is logged and does not stop the others.
- **`SC.state`** = `{size, build, variant, card}`, a copy. Change it with `SC.set` / `SC.open`.
- **`SC.set({size?, build?, variant?}, {toast?, undo?})`** returns a Promise. Calls are queued (one runs at a time;
  a newer call wins over a stale fetch). A size or build change:
  1. fetches `data-S-B` (and starts `core-S` / `build-S-B` in parallel);
  2. sets `SC.data`, writes the hash and the stored default, redraws the stage bar and the masthead;
  3. hides / shows cards, re-runs every visible card's `render(D, ctx)`, re-binds `[data-k]`, re-enters the open card;
  4. mounts the stage meshes (`SC.viewer.mount`), keeping camera, section, press, explode, visibility and focus;
  5. emits `state` with `{size, build, variant, prev}` (`prev` null on the first load).
  - A **variant-only** change skips the card re-render: it re-binds (`data-variant`), calls each card's
    `onVariant(v, D, ctx)`, and swaps the crank / switch instances on the stage.
  - `toast` (HTML) shows `SC.toast(toast, {undo})` once the data is in.
- **URL hash**: written as `#s=368&b=ls&m=keys` (plus `&v=M` when not the default) with `history.replaceState`.
  It also reads bare tokens separated by `-` `_` `.` `~`, such as `#368-ls-keys` or `#keys`: **an artifact link only
  passes a bare token** through to the page, so share links in that form. The stored default is localStorage
  `sc.state` = `{size, build, variant}`; every access is in try/catch. Precedence: hash, then stored, then
  `manifest.defaults`.
- **`SC.data`**: the current data-S-B object (the `D` handed to cards). **`SC.manifest`**: the manifest.
- **`SC.load(file)`**: fetch + parse (JSON for `.json`), cached per file, cache-busted with `?v=` + the first 10
  hex of `manifest.files[file].sha1`. It streams, so the stage message and the stage bar show a progress bar and
  "Loading N MB... P%". **`SC.files(S, B)`** returns `{core, build, data, extras, models}` file names.
- **`SC.toast(html, {undo: fn, ms = 7000})`**: a note fixed at the bottom of the window, with an Undo button when
  `undo` is given.
- **Helpers**: `SC.fmt(x, d)` (d decimals, or up to 3 significant decimals when d is null; -0 prints as 0),
  `SC.get(obj, 'a.b.0.c')`, `SC.esc(text)`, `SC.text(html)` (decodes the entities some data strings carry),
  `SC.svg(tag, attrs, parent)`, `SC.dPath(polys)` (the drawing path, v flipped), `SC.drawing(name)` (the current
  data's drawing object).

| event | payload | from |
|---|---|---|
| `ready` | - | shell: first data bound (`SC.ready` true) |
| `loading` | `{what, bytes, loaded, done}` | shell: a fetch started, progressed or finished |
| `state` | `{size, build, variant, prev}` | shell (or the viewer, if it mounted late), after a switch has fully rendered |
| `viewer` | `SC.viewer` | viewer: the first mount finished (also `SC.viewer.ready`, a Promise) |
| `card` | `{id, prev}` | shell: the open card changed (`id` null when closed) |
| `focus` | preset name | a `[data-show]` button: the viewer runs the preset |
| `pressed` | `{id, kind, t, theta?, key_down?, plunger_in?, travel?, state, src}` | viewer, after any `press` |
| `step` | index, -1 (assembled) or `order.length` (play finished) | viewer: assembly step |
| `play` | - | `[data-play]` button |
| `exag` | bool | the x4 toggle |
| `released` | `{src, was}` | viewer: every control back to rest (`release()`, the Press selector, a preset that changes it, Reset view); `src` is `stage`, `preset`, `view` or the caller's; `was` = how many were pressed. Cards with their own press slider (sidekeys, reset, usb) follow it |

### The stage (SC.viewer)
Chips come from `manifest.groups`; the `strip` chip shows on `ls` only; `dummy` and `compare` start off and load
`extras-S.json` the first time their chip (or a preset showing them) turns on. The panel chip reads
`meta.panel.label` plus "ribbons" or "FPC". The controls panel has: chips, Assembly (explode), Section (axis, flip,
position over `meta.envelope`, 1 mm margin), Press (a control selector: "All keys" or any `controls[]` entry, and
a 0-1 slider), Play assembly, Reset view, the x4 toggle, the bottom-key switch selector (T / M, it calls `SC.set`),
and Render (shadows, ambient occlusion, edge lines, free spin, Hide case = tub + lid + screws). Views (front, back,
left, right, top, bottom, iso) and Expand sit on the viewport. `#stage-extra` is an empty, hidden slot for card
controls on the stage (the strip card's Fold slider): `SC.viewer.extraSlot()`.

**Scene names.** Every mesh is a *part* named after its node, except:
- `crank_M` / `crank_T` are placed 4 times: `crank_M_SW8`, `crank_T_SW8`, ... on a pivot at `(keys.x[ref], rod.y,
  rod.z)`. `node('crank_SW8')` returns the current variant's instance.
- `sw_T_body` / `sw_T_nub` are placed 4 times: `sw_T_body_SW8`, `sw_T_nub_SW8`, ... (X offset `keys.x[ref]`).
- Variant T shows `crank_T_*`, `sw_T_*` and hides `crank_M_*`, `swbody_*` and the bottom keys' `nub_<ref>`; M is the
  reverse. (Parts carry `variant`; the swap is `visible`.)
- `skey_<ref>` sits on a pivot at its flexure control's `pivot`.
- The viewer adds `screen` (the page texture on `meta.active` at `meta.z.lip + 0.02`, display group), and the tools
  `tool_pin` and `tool_plug` (+ `tool_plug_body`) outside every chip group.

**API** (`SC.viewer`):
- `ready` (Promise of the API), `mount(state, D, {variantOnly})` (the shell calls it), `stats()` =
  `{parts, unmatched, frames, extras, size, build, variant}`, `state` = `{size, build, variant, preset, explode,
  section}`.
- Visibility: `groups()`, `visible(id, on?)`, `setVisible(ids | null)` (null = everyday set), `show(ids)`,
  `hide(ids)`, `ensureExtras()`.
- Camera: `preset(name, {animate = true})`, `frame(name, animate)`, `view(name)`,
  `tween(cam, tgt, up, {fit, animate})` (`fit` backs off on a narrow stage as a preset's `fit` does; `animate: false`
  jumps); `camera`, `controls` (`controls.target`), `scene`, `THREE`, `renderer`.
- `section(axis | 'off', pos, flip)`, `clip()` (the plane or null).
- `explode(e)`, `explodeStep(k, f = 0.98)` (the stage at fraction f of step k's arrival; returns e), `play()`,
  `stop()`, `reset()` (also closes the open card).
- `press(id | 'all' | 'kind:<kind>' | [ids], t, {theta, src})`: `'kind:flexure'` moves every side key and nothing
  else; a kind or an array does not move the stage's Press selector and emits `pressed` with `ids`. `release(src)`
  (emits `released`), `pressState(id)` (the stored t, 0 at rest), `exaggerate(on)`, `variant(v)` (instance swap
  only; cards change the variant with `SC.set({variant})`).
- `highlight(patterns, color = 0xc7782a)` (globs over part names), `clearHighlight()`, `look({focus, highlight,
  color}?)` (set the focus / highlight look without a preset: camera, chips and section stay; returns the current
  look), `clearLook()`.
- `node(name)` (the moving Object3D), `part(name)` (`{obj, holder, mesh, cap, lines, group, base, mat, rest, ...}`),
  `nodes()`.
- `caption(html, tag)`, `invalidate()` (redraw on dirty only), `setting(k, v?)` for `shadows ao edges free shell`.
- `group(id)`: a persistent `THREE.Group` inside chip group `id` that survives mounts (the live strip uses
  `group('strip')`). Materials under it get the section plane from `applyClip` unless `userData.noClip`.
- `extraSlot()`: the `#stage-extra` element.

**Mount.** Size / build switches dispose the parts and their materials and rebuild them from the cached parsed
geometry (one parse per file). They keep the camera where it is, the section (its absolute position, clamped to the
new envelope), every control's press, the explode value, chip visibility (groups not in the build are turned off),
the focus / highlight look, and the caption of the current preset.

**Presets** (`preset(name)`): Rev K's `focus()`, driven by `D.presets[name]`: stop play, `explode` (default 0),
`show` / `hide` / everyday set, dim groups not in `focus`, colour `highlight` parts, section from `sec` (or off),
`variant` via `SC.set`, the press selector to `press` (`true` = All keys; a preset without `press` sets it back to
All keys and releases), the camera (`fit` widens for a narrow aspect as Rev K did), and `tag` / `cap`.
A missing preset is a console warning (the page checks treat warnings as errors).

**Press** (`press(id, t, {theta, src})`), t in 0-1, returns the payload it emits as `pressed`:
- `'all'` moves every `crank` and `flexure` control (the buttons), not the pin or the plug.
- `crank`: `th = rest + t (bottom - rest)` from `SC.crank.raw(variant, 0)`, or `theta` if given (then `t` in the
  result is the normalised angle). The x4 exaggeration multiplies `(th - rest)` for the motion only; the returned
  `theta / key_down / plunger_in / state` are real. Both variants' crank instances turn, the key moves
  `-keyDown(thv, theta_built)` in Z, and the visible plunger (`nub_<ref>` for M, `sw_T_nub_<ref>` for T) moves +Y by
  `plungerIn(v, thv, 0)`. Verified in step 3 to 1e-9 against `SC.crank` at rest, click and bottom.
- `flexure`: pad travel `d = t max_travel`; the key turns `sign d / length` rad about `axis`; the plunger moves
  `max(0, d - gap)` along `plunger_axis`; `state` is `clicked` from `click_travel`.
- `pin`: t 0-0.6 brings the pin from `pin_from` to `pin_to`, t 0.6-1 pushes on by `max_travel`, and the plunger
  with it. The pin shows while t > 0 or while it is the selected control.
- `plug`: the plug's shell tip moves from `from` to `to`; `travel` is `t insert_mm`; shown like the pin.
- The stage slider follows presses from cards (`src` other than `'stage'` sets the selector and the slider).

### SC.crank
`rot(p, th), crownZ(th), keyDown(th, th0), noseFront(v, th), face(v, dy), plungerIn(v, th, dy), thetaAt(v, y)`,
`raw(v, dy)` (rest / click / bottom unrounded), `derive(v, dy)` (rounded to 4 decimals like `sc_contract.derive`;
checked equal to `keys.derived` in all 4 data files) and `state(v, th)` (`open`, `clicked`, `bottom` within 0.05
deg). Each takes an optional last argument `K` (default `SC.data.keys`).

### SC.Drawing(name, host, opts)
Rev K's engine, as section 4 describes (`name` may also be a drawing object). Additions: pattern ids are unique per
drawing (one drawing can appear twice), `opts.hide [ids]`, `self.layer(id)` (a layer or beyond path),
`self.show(id, on)`, `self.bbox(id)` (a layer's or beyond's `[u0, v0, u1, v1]` from the data, step 5) and
`self.destroy()` (drops the ResizeObserver and the SVG). `SC.A(d).label(u, v, text, dx, dy, {fit: true})` keeps
the text inside the drawing window (flips side, else slides; step 5; the cards' own `fitA` helpers still work). `SC.A(self)` is the annotation
helper set. Roles `crank rod strip led tape kapton ref` have CSS (`--d-crank`, `--d-rod`, `--warm`, `--gold`,
`--tape`, `--kapton`, `--d-ref`), and beyond roles `crank`, `case`, `case2` too. Hosts with class `dwg-host` get
the drawing frame and, at 720 px or less, the sideways scroll with a 540 px minimum.

### [data-k] binding (`SC.bind(root)`)
- Order: `data-only` sets `hidden` (every token must be the size or one of the build's tokens: its own id and those of
  the builds whose panel or chin it has, `manifest.builds.B.tokens` = `sc_contract.BUILD_TOKENS`; `SC.buildIs(tok, B?)`),
  `data-not` hides on any such token, then `data-variant`, then every
  `[data-k]` that is not inside a hidden element or an away card is filled.
- Values: numbers through `SC.fmt` with `data-d`, `+` with `data-sign`; arrays joined with `data-join` (default
  ", "); `data-len` prints a length; booleans print yes / no; strings go in as HTML (data strings carry entities).
  `data-u` adds a thin space and the unit.
- A missing, empty or object value prints `?`, gets `k-missing` and a console warning.

### Cards
A card is `cards/<id>.html` (one `<article class="mech" data-card="<id>" data-preset="<preset>">`) and
`cards/<id>.js` (`SC.card({...})`), as before. What the shell does with them:
- **Heading**: put the heading in `<div class="mech-head">` (an `h2`, optional `.refs`, `.thesis`). An away card
  (below) hides everything else.
- **Card CSS**: shared classes live in the shell (Rev K's: `mech-head refs ref thesis body note dwg-pair dwg-host
  scrub state nums show3d steps checks check-item forces cmp tbl-wrap logo-wrap bars bar stack stack-key dl-list
  dl-row dl-status map-wrap jmap leg btn btns chip seg`). Card-only CSS may go in a `<style>` inside the article,
  scoped with `[data-card="<id>"]`.
- **Visibility**: `hidden` when `sizes` / `builds` exclude the state. A card with `enter_build` that applies to its
  build stays visible on the other builds as **away**: class `sc-away`, not rendered or bound, with an inserted
  `.sc-enter` line "This card shows the light strip build. [Switch to it]". Its `home_builds` (CARDS; default
  `[enter_build]`) are the builds it works on in place (the strip card: `ls` and `lc`).
- **Opening** (`SC.open(id, {scroll})`, returns a Promise): a click anywhere in the card (not on a link), a
  `[data-show]` / `[data-enter]` button in it, a `[data-goto]` link, or `#m=<id>` on load. Scrolling never opens a
  card. Opening marks it `.on`, writes `m=` to the hash, calls the previous card's `onLeave` and this card's
  `onEnter`, and emits `card`. Opening an away card first runs `SC.set({build: enter_build})` with the toast
  "Switched to the light strip build." and an Undo back to the previous build. `SC.close()` closes.
- **Scopes**: `render(D, ctx)` gets a render scope, dropped before the next render (its `ctx.Drawing`s are
  destroyed, its `ctx.on` listeners removed). `onEnter(D, ctx)` gets an enter scope, dropped on leave. So drawings
  made in `render` stay on the page while the card is not open. `ctx` = `{size, build, variant, el, data, manifest,
  q(sel), qa(sel), Drawing(name, host | id, opts), on(ev, fn), listen(el | sel, ev, fn, opts), cleanup(fn)}`; a
  host id is looked up inside the card first. `listen` adds a DOM listener and `cleanup` any undo function
  (observers, rAF loops, timers); both run when the scope is dropped (step 5).
- A switch that leaves the open card not applying, or away (the strip card after Undo to standard), closes it.
- A `[data-play]` button opens its card, then plays (step 5).
- `onVariant(v, D, ctx)` receives the render scope's ctx. Errors in any hook go to `SC.cardError(id, e)`, which
  logs and adds a `.card-err` line to the card; the other cards still run.
- `SC.card` merges the definition over `manifest.cards[id]` (the manifest wins for title, order, preset, sizes,
  builds, enter_build). `SC.cards()` lists registrations; `SC.cardApplies(id, S?, B?)`.
- **Placeholders**: until a card's fragments exist, a non-strict bundle inserts
  `<article class="mech sc-placeholder" data-card="<id>" data-preset="<preset>">` with the title and a Show in 3D
  button. They behave like cards without `SC.card`. `--strict-page` turns a missing card into an error again.

### Downloads (`SC.dl`, for the files card)
`SC.dl.zip(S?)` loads `models-S.js` once (a script tag; it clears `window.SC_MODELS` after decoding) and resolves
to the zip bytes. `SC.dl.subset(bytes, Set of paths)` returns a Blob holding only those entries (Rev K's copy of the
local records). `SC.dl.api()` resolves to `window.claude.use('downloads')` when the host offers it (a page published there must
declare the `downloads` capability), and otherwise to `SC.dl.plain()`, a plain browser download of the zip (a blob link),
which needs the page served over http like its data files. Zip and file names come from `data.downloads` and the
manifest; sizes from `manifest.files[f].bytes`.

### Page rules
- **three.js**: 0.169 from jsdelivr via the importmap in the shell; `RoundedBoxGeometry` for the plug.
- **Skeleton**: the host wraps the page in `<!doctype html><head>` with the charset and viewport meta, so the shell
  has none of its own. `step3_serve.py` (below) serves the bundle wrapped the same way for tests.
- **Width**: works at 390 px with 16 px gutters (body padding) and no horizontal page scroll; the bench stacks at
  1180 px or less, and the stage is sticky only above that. At 900 px tall the sticky stage fits the window.
- **Theme**: tokens on `:root`, in `@media (prefers-color-scheme: dark) :root:not([data-theme="light"])` and in
  `:root[data-theme="dark"]` (with `color-scheme: dark`), explicit body background. The viewer repaints its
  gradient on a theme change.
- **Motion**: reduced motion jumps the camera and plays the assembly in one step.
- **Coarse pointers**: GTAO off, 2048 shadows.
- **Source text**: ASCII only. Note for agents: the Write and Edit tools turn a typed backslash-u escape into the
  character itself, so re-escape after writing (`scratchpad/showcase-build/step3_asciify.py <files>`); the bundler
  refuses non-ASCII.
- **Tour order**: `sc_contract.CARDS` (table in the previous revision of this section, unchanged): glance 10, keys
  20, strip 25 (enter_build ls), sidekeys 30, joint 40, usb 50, reset 55, screen 60, detent 65, ribbons 70,
  battery 80, boardprep 85 (3.68), zstack 90, closing 100, edges 110, compare 115, assembly 120, checks 130, files
  140.

## 6. Checked in step 1 (2026-09-27)
- **Self-test**: `sc_contract.py --selftest` passes in both venvs.
  - The sample manifest and all 4 sample data files validate.
  - 14 broken data copies and one broken manifest are each caught for the intended reason:
    - Data: a flipped rest-row sign, `key_dz` given as a lift, stale derived values, a missing preset, an unknown group, non-ASCII text, a drawing outside its window, a key drawing without `crank_T`, an unknown control node, a 3.68 with 2 side keys, depth-map rows, the hooks' W_OUT missing, a slot roof off the hooks' top + W_OUT, the T finger force, and a dropped Zorian22 attribution.
    - Manifest: a 17 MB file and a dangling load reference.
- **Key drawing**: cut from the real `out/standard` STLs of both sizes at SW8 (x 23.4975).
  - The tub and `crank_SW8` sections are non-empty: tub 2 polygons (75 / 73 points), crank 68 points.
  - `crank-M.stl` moved to x 23.4975 cuts exactly as `crank_SW8.stl` (symmetric difference 0), so the one-mesh-per-variant instancing is exact.
  - The full 10-layer key drawing, with the cheek beyond, validates.
- **Model files**: a round trip (write, validate with the GLB decoded, read back) keeps the names, bounds and face counts. One 4.26 tub is about 0.77 MB as a model file, and the 3.68 tub 0.71 MB.
- **Kinematics**: the independent rest rows agree with the reference kinematics in both sizes: 4.26 from `bottom-keys.json` static, 3.68 from `crank.json` rest for SW8. Examples: M +0.2 gives 3.87 deg and 0.331 mm down; T -0.2 gives -3.92 deg and 0.342 mm up.

## 7. The 4.26 adapter (step 2a, 2026-09-27)

**Run** from `enclosures/case-426` with the 4.26 project's venv:
`python -B ../../showcase/gen/adapt_426.py [--out DIR] [--reuse] [--check-only]`.
- The default `--out` is `showcase/build/426/` (it was a scratchpad folder until 2026-09-28). A run takes about 75 s.
- `params.py` fixes the build at import time. So the script runs itself once per build as a child process
  (`SILKSCREEN_VARIANT`), both in parallel, and then combines their results.
- It writes nothing into the project. `out/` is snapshotted (names, sizes, mtimes) before and after, and the run fails
  if it changed.
- `compare.main()` writes `out/<b>/compare.json`, so that one write is redirected into `_work/`.

**Outputs.** The bundler copies only the contract names. `_work/` is scratch: child logs, `meshes.npz` and renders.

| file | bytes | |
|---|---|---|
| `core-426.json` | 4.91 MB | 45 nodes |
| `build-426-std.json` / `build-426-ls.json` | 0.93 / 0.84 MB | tub + display nodes |
| `extras-426.json` | 3.75 MB | `cmp_x4`, `cmp_retro_frame`, `cmp_retro_back_lower`, `cmp_retro_back_upper`, `dummy_pcba` |
| `data-426-std.json` / `data-426-ls.json` | 155 / 167 KB | 22 / 25 drawings |
| `models-426.js` | 11.07 MB | zip `silkscreen-case-4.26.zip`, 8.30 MB |
| `adapter-426.json` | 2 KB | for the bundler: `nodes {core, build {std, ls}, extras}`, `parts {shared, per_build}`, `build_diff`, `display_nodes_differ`, `files {bytes, sha1}` |

**For the bundler (step 4):**
- **The 4.26 builds do not have the same per-build nodes.**
  - std: `panel_epd panel_light panel_touch ribbon_main ribbon_light ribbon_touch ribbon_touch_ic tub`.
  - ls: `panel_epd ribbon_main tub`. The plain panel has no touch or light layer, and one FPC.
  - `sc_contract.validate_manifest` requires equal per-build sets apart from `strip_*`. That rule must also let the
    display group (`panel_*`, `ribbon_*`) differ.
- **The core/build split** is by mesh hash across the two builds. It was also checked against `out/shared-parts.json`:
  - lid, the side keys, midplate, the keys and crank-M/T are shared;
  - the tub differs.
- There are **no `strip_*` nodes** on 4.26. `strip3d.js` builds the bar, the LEDs and the diodes live. The as-built CAD
  strip appears only in the drawings `strip_led`, `strip_holddown` and `strip_neck`.
- `ribbon_touch_ic` (the touch IC on its ribbon; Rev K's name) is a std node.

**Data details (4.26)**
- **Display layer ids in drawings.**
  - std: `epd` (glass), `light` (lgp), `touch` (film).
  - ls: `glass` (glass), `fpl` (film), `ps` (film).
- **The key drawing's beyond outlines** are `cheek` (the crank at x - 4.5), `rail` (a closed ring at x - 6.0) and `hook`
  (the key's +X hook at x + 4.45, its centre; test 2, was `bump`, the drag bump at x + 4.65). Its `notes` give the x values.
- **Facts** have a `note`: the small line under the value.
- **Checks** have a `status`, and a status always comes with a `detail`:
  - `expected`: on build.py's EXPECTED list.
  - `designed`: two contacts that build.py's EXPECTED list does not have. Both are reported with ok true. Ian may
    want them added to `EXPECTED`.
    - The lid's two battery springs (Y 91 and 104) on the cell model: 12.0 mm3.
    - The midplate's snap posts through the board at H1, H2 and H6: 6.25 mm3.
  - `accepted`: the bottom-keys verdict's accepted finding.
- **Controls.**
  - `plug.from` and `plug.to` are the tip of the plug's shell, 9 mm out and seated. The overmold stops on the tub's
    floor. The plug also carries `shell_len`, `seat_face_x` and `overmold`.
  - `pin.pin_from` is 10 mm outside the case face.
  - `flexure.sign` is Rev K's `side * sign(free - root)`.
- **Presets.**
  - `press` is `'SW8'` (keys), `true` (tabs, keylid), `'usb'` or `'SW11'`.
  - `fit` is set where Rev K had it, and on strip and zstack.
  - `highlight` is on keys, tabs, keylid and close.
- **Explode and assembly.**
  - The explode order is `tub display [strip] midplate battery keys rod pcba lid screws`.
  - The assembly list follows the project README: coupon (gate, and the optional chin coupon), rod prep, tub, [strip],
    display, midplate + battery, keys (the tub face down until the board is in), cranks, rod, gate, PCBA, lid (its rim
    over the gate), screws, then turn it over.
  - The README puts the keys **before** the cranks: at rest height the keys block the cranks' path.
- **`keys` extras.**
  - `switches.<v>` adds `housing_half_x`, `nub_yz` and `nub_half_x` (the `sw_T_*` boxes).
  - `rod` adds `hole_d`, `stops`, `ream` and `bore_d`.
  - `forces` adds `table` (every switch x mu x press point), `pressable`, `guide_length_mm` and
    `rev_k_rocker_N_at_1.86`.
  - `hooks` adds `hook_lead_mm`, `root_mm`, `wall_behind_slot_mm`, `above_roof_mm`, `tilt_on_hooks_deg`, `pull_out`
    and `hooks_to_crank_min_mm`.
  - `rod_check` adds shear, bearing and `crossbar`.
- **`cards.<id>`.** Rev K's meta blocks moved here under their Rev K names. Ported card code reads `D.cards.usb.usb`
  where it read `M.usb`.

  | card | blocks |
  |---|---|
  | `sidekeys` | `{count, refs, draw {plan, side, elev}, tabs, tab_mech, tab_pad, tab_geom, summary, sweep}` |
  | `joint` | `{latch_count, tongue_len, joint, latches, board_snap}` |
  | `usb` | `{usb, ref}` |
  | `reset` | `{reset, ref}` |
  | `screen` | `{stack, panel, screw_clear, insertion, z}`, plus `plain_stack` on ls |
  | `detent` | `{detents, midplate}` |
  | `ribbons` | `{ribbons {count, outlines, connectors, ...}}` |
  | `battery` | `{battery}` |
  | `zstack` | `{bars [{name, z, beside?}], total, budget}` |
  | `closing` | `{holes, top_screw, screw_seat_z, screws, head, screw_list, cb_depth, screw_len, pilot, gate {web, flange, top_clr, pull_d, stop_x}, board_snap}` (section 20) |
  | `edges` | `{edges, logo, logo_back}` |
  | `compare` | `compare.py`'s output `{rows, budget, views, ...}` plus `attribution`. `budget` is the X4 stack chart. |
  | `keys` | `{proud_mm, chin_deeper_mm, rings, seats, coupon, rod_len, end_play, travel, side_clearance, hang_theta, mech_travel_crosscheck, ...}` |
  | `strip` | `{case_cards [{h, items}], diff [{part, same, text, std?, ls?}], shared_parts}`, plus `steps`, `checks` and `geometry` on ls |
  | `files` | `{dummy, plate}` |
- **Strip steps (ls)** are the light-strip page's `STEPS['426']`.
  - "Close the case" carries `drawing: 'strip_led'`.
  - The bottom-keys step uses `cutX` = SW8.
- **Links in data HTML** are `<a href="#m=<card>" data-goto="<card>">`. The shell should turn a `data-goto` click into
  opening that card.
- **Downloads.**
  - One zip holds `print/` (both tubs, the shared parts once, the coupons, `ROD.txt`), plus `pcba-dummy.stl` (the same
    bytes in both builds) and `README.txt`. Since 2026-09-28: the repo's `print/4.26/`, plus the rod jig in `shared/`.
  - The tub files carry `builds`.
  - The per-build one-plate 3MF is not in the zip. The README in the zip says so. (Since 2026-09-28 there is no
    per-build 3MF: the README points at the plate file, `print/silkscreen-426-plates.3mf`, which is not in the zip.)

**Checks run (2026-09-27, all passed)**
- Every file passes `validate_file`, with the GLBs decoded.
- Both builds pass `validate_data` in strict mode, with the node cross-check.
- Every file is under 16 MB. The 4.26 share of the version is 21.8 MB.
- **Kinematics.**
  - The 6 rest rows from `bottom-keys.json` static agree with the reference, within the validator's tolerances.
  - `derive()` agrees with `mechanics.json key_forces.travel` in all 6 rows (M/T x delta -0.2 / 0 / +0.2). The worst
    difference is 0.0038 deg and 0.0005 mm; mechanics rounds to 0.01 deg.
  - The nominal values:

    | variant | click | key at click | bottom | key at bottom |
    |---|---|---|---|---|
    | M | 4.832 deg | 0.412 mm | 8.680 deg | 0.731 mm |
    | T | 4.813 deg | 0.410 mm | 8.619 deg | 0.726 mm |
- **Geometry, measured on the shipped meshes.**
  - At theta 0 the crank-M nose front is at -1.920, and so is the `nub_SW8` face.
  - At theta 0 the crank-T nose front is at -2.200, and so is the `sw_T_nub` face.
  - The key's underside is at -0.200, which is the pad crown's top.
  - `crank_M` moved to each key's X cuts like `out/standard/crank_SW*.stl`. The worst symmetric difference is 7e-15 mm2.
- **Drawings.** std has 22 and ls 25, none empty, with every required name. The key drawing has all 10 required layers
  plus `pcb`. It and 8 others were rendered to images and checked by eye.
- **`out/`** was unchanged across the run (201 files).

## 8. The 3.68 adapter (step 2b, 2026-09-27)

**Run** from `enclosures/case-368` with the x3 project's venv:
`python -B ../../showcase/gen/adapt_368.py [--out DIR] [--merge] [--only std|ls] [--jobs 1]`.
- `--out` defaults to `showcase/build/368/` (since 2026-09-28; it was required, and before that a scratchpad folder). A run takes about 75 s: two workers in parallel
  (about 67 s: board tessellation 18 s, drawings 8 s, the compare 22 s), then the merge (8 s). `--merge` redoes only
  the merge from `DIR/work/`.
- Like the 4.26 adapter, it runs itself once per build (`SILKSCREEN_VARIANT`; x3's `params`/`hw` read it on import).
- It writes nothing into the project. Checked: a size + mtime listing of the whole project (655 files) was the same
  before and after a full run. `compare.main()` is **not** called: it reads a pre-split `out/tub.stl` and writes
  `out/compare.json`. The adapter recomputes the comparison itself with compare.py's functions (`compare_block`).

**Outputs.** The same file set and report shape as the 4.26 adapter. `work/` is scratch: `<b>.glb`, `<b>-data.json`,
`<b>-log.txt`, `<b>-drawings.png` (a contact sheet of every drawing).

| file | bytes | |
|---|---|---|
| `core-368.json` | 4.77 MB | 39 nodes |
| `build-368-std.json` / `build-368-ls.json` | 0.82 / 0.83 MB | `tub`, `key_SW9 key_SW8 key_SW3 key_SW2` (key-x3std / key-x3ls) |
| `extras-368.json` | 3.66 MB | `cmp_x4`, `cmp_retro_frame`, `cmp_retro_back_lower`, `cmp_retro_back_upper`, `dummy_pcba` |
| `data-368-std.json` / `data-368-ls.json` | 183 / 200 KB | 21 / 24 drawings |
| `models-368.js` | 6.97 MB | zip `silkscreen-case-3.68.zip`, 5.23 MB |
| `adapter-368.json` | 13 KB | `nodes`, `parts`, `build_diff`, `display_nodes_differ` (`{}`), `files {bytes, sha1}`, `downloads`, plus `split`, `checks`, `node_info` |

The 3.68 share of the version is 17.4 MB. With the 4.26's 21.8 MB, that is 39.2 MB before `strip.json`, the optics
PNG and the page.

**For the bundler (step 4)**
- **The two 3.68 builds have the same per-build nodes** (`tub` + the four keys), so `validate_manifest`'s rule holds
  here. `manifest.sizes['368'].build_diff` is `tub + 4 keys differ`; `parts` comes from `adapter-368.json`.
- **The split** is by mesh hash, checked against `out/shared-parts.json`: lid (`lid_body`), the side keys, midplate
  and crank-M/T are shared; the tub and `key_SW*` differ.
  - One exception is handled: `battery_cell` (a filleted CadQuery solid) tessellates with other diagonals in each
    process. For a node that `NODE_RULES` puts in core, the merge accepts the same vertex set (to 1e-4), the same face
    count, and the same area and volume (to 1e-6) as the same mesh (`adapter-368.json` `split['same_within_1e-5']`).
    The 4.26 adapter may meet the same thing on a rerun.
- **No `strip_*` nodes**, as on 4.26. The as-built CAD strip (`ref_strip_*.stl`) appears only in the drawings.
- **`battery_pcm`** is a 3.68-only node (the pack's folded protection board). It is in the `battery` group; the viewer
  colours it by group or by a `battery_*` default.
- **The `cmp_*` meshes** stand beside the standard build: their front faces are level with its face (Z 4.47 since the
  screen bevel of 2026-10-10; 4.07 before). On the light-strip build (face 5.27) they sit 0.8 mm behind it (1.2
  before). `cards.compare.placed_beside` is `'standard'`.

**Data details (3.68), where they differ from the 4.26**
- **Refs in the drawings** (`notes.ref`):
  - `tab_plan` and `tab_elev` cut SW7, the power key on the **left** wall (4.26: SW10 on the right). `key_side` cuts
    SW1. `joint_at_tab` cuts at Y 83.0 behind SW4, where the tongue runs.
  - `pin` is the board on the H6 snap post. It is cut 0.55 mm off the hole centre, so the post's fingers show and not
    its slot.
  - `stack` runs across the bottom border through the midplate spring at (8.5, 11.5), where the lip is.
  - `ribbon` cuts the one FPC at X 28.
- **Drawing names.** The required ones, plus `bay_plan` (the cell in plan at its mid-thickness: lip, hooks, end stop,
  lead to J5) and, on ls, `strip_fold` (through the folded top pair, Y 79.5) and `strip_neck` (X 11.15).
  - `bay` cuts down the cell's middle at X 22.53, through J7.
  - `strip_led` is through D4 at Y 49.7.
- **Display layer ids in drawings:** `epd` (glass + EPL, role `glass`) and `film` (the PS, role `film`), in both builds.
- **Strip layer ids:** `strip` (bar), `led`, `diodes`, `hinge`, `folded`, `folded_led`, `neck` and `tail`.
- **The key drawing's beyond outlines:** `cheek` (x - 4.5), `hook` (x + 4.45, the +X hook; was `bump`) and `rail`. `rail` is the tub cut at the
  ring segment left of the key (X 17.4975), clipped to the rail's box `[-4.6, 0.2, -1.8, 4.2]` so that only the ring
  shows, not a second outline of the skin. The `sw_M`/`nub_M` layers are the board STEP's MJTP1117.
- **`keys`:**
  - The same crank geometry and nominal numbers as the 4.26. The rest rows are `crank.json` `rest.SW8` (`"MJTP1117 +0.2"`:
    `face_dy` +0.2, `key_dz` = -`key_lift`).
  - It adds `tolerance`: the 6 rows of `mechanics.json key_forces.travel`, with `variant` and `face_dy`, and the key's
    proud at rest, click and bottom over this build's face.
  - It adds `key {name, tall, top_over_face, ...}` and `stop_above_rest_mm` (0.97).
  - `switches.<v>` carries `housing_half_x`, `nub_yz` and `nub_half_x` as on 4.26. M is the board STEP's MJTP1117;
    T is `crank.ts365`. T also has `nub_z_worst`.
  - `forces.table` is keyed `"MJTP 1.27"` etc. with `mu_0.3` and `mu_0.45` rows at `press_ys`.
- **`cards.keys.travel`** uses the 4.26 naming (`"MJTP delta +0.2"`, delta = -`face_dy`). So it reads the same on both
  sizes.
- **Presets:** 21. These are the 20 of the 4.26 plus `boardprep`.
  - `battery` hides the lid and screws: the cell is shown behind the board, where it sits over the shallow patch.
  - `zstack` cuts X through the cell.
  - `keys` presses `SW8`, `usb` presses `usb`, `reset` presses `SW11`, and `tabs` and `keylid` press `true`.
- **Explode order** (the x3 README's): `tub [strip] display keys rod midplate pcba battery lid screws`. The strip goes
  in before the panel on this size. The battery is just in front of the lid, which carries it.
- **Assembly:** `coupon` (the gate coupon, and the optional chin coupon), `prep` (board cut, power rework, lead trim,
  cell check), `rodprep`, `tub`, `[strip]`, `display`, `keys` (the tub face down until the board is in), `cranks`,
  `rod`, `gate` (README steps 3-6), `midplate`, `pcba`, `battery` (in the lid; plug J5 with the lid stood up), `close`
  (fold the lid like a book; its rim over the gate), `setkeys` (turn it over).
- **Cards.** The 4.26 block shapes, so a card reads the same paths on both sizes: `usb.usb`, `reset.reset`,
  `ribbons.ribbons`, `detent.detents` / `detent.midplate`, `edges.edges` / `logo` / `logo_back`, `joint.joint` /
  `latches` / `board_snap`, `sidekeys.draw` / `tabs` / `tab_mech` / `tab_pad` / `tab_geom`,
  `screen.stack` / `panel` / `insertion` / `z`, `zstack.bars` / `total [z0, z1]` / `budget`, `compare` (+ `budget`),
  `closing`, `files.dummy` / `plate`, `checks.count` / `failed`, and `strip.case_cards` / `diff` / `shared_parts`,
  plus `steps` / `checks` / `geometry` on ls. What is only in this size:

  | block | 3.68 content |
  |---|---|
  | `battery` | `battery {in_lid, capacity_mAh, ref, box, allowance_mm, clearance_mm, swell_mm, pocket_mm, bay, hooks, lead, plug, lead_xy, deep_parts, antenna, antenna_gap_mm, module, j5, j7, cell_bbox}` and `depth_map` (x3's board-rear map, 1 mm cells, 63 x 96) |
  | `boardprep` | `{trim_y 86.25, trim_kicad_y 62.0, fit [R72 R74], fit_values, remove [R36 R73], leave_off [SW5], power_key SW7, gone_with_cut [...], lead_trim_mm, support_post, snap_posts}` |
  | `zstack` | x3's 9 bars. On ls a `beside: true` row for the strip (LIP to the LED tops). `thickness`, `with_keys`, `without_battery`. |
  | `screen` | `strip_stack` on ls: the tape, PI, flex and LED heights, the ceiling, `front_raise` (x3's 1.2) and `over_std` (the light-strip face over the standard's: 0.8). `window` (below) |
  | `edges` | `edges.window_bevel_deg` and `edges.window_corner_r` (below) |
  | `closing` | `seat_z` per screw, `pinned` and `pin_d` (H3/H4's pins, section 20) |
  | `keys` | `key_name`, `key_names`, `key_tall_mm`, `proud_range_mm`, `wrong_variant_shift_mm`, `lever`, `keys_differ_per_build` |
  | `strip` | `cut_led_y`, `cut_fold_y`, `key_cut_x`. `steps` are the light-strip page's `STEPS['368']` (10), with `drawing: 'strip_led'` / `'strip_fold'` on the two cut steps. |

- **The screen bevel (2026-10-10, the standard build's 35-degree window on a face 0.4 higher).**
  - `cards.screen.window {face_mm, deg, depth_mm, land_mm, corner_r_mm [at the lip, on the face], margin_mm}`
    replaces `cards.screen.window_land`, `window_bevel` and `window_margin`. `face_mm` is the bevel as seen, its width
    on the face; `depth_mm` how far down from the face it runs; `land_mm` the straight part under it to the lip. std:
    1.285 at 35 degrees, 0.9 deep, a 0.1 land, corners [0.4, 1.685]; ls (x3's window): 1.2 at 45, 1.2 deep, a 0.6 land,
    [0.0, 1.2] (square corners). `margin_mm` 0.5 on both. The screen card binds `cards.screen.window.*`, and its
    corners text is `data-only="std"`.
  - `cards.screen.stack` (mechanics.json `screen_stack`) adds `window_bevel_face_mm`, `window_bevel_deg` and
    `window_corner_r_mm` on std; its `window_land_mm` / `window_bevel_mm` are 0.1 / 0.9 there (0.3 / 0.3 before).
  - `cards.screen.strip_stack.over_std` (ls): the light-strip face over the standard's, 0.8 (`strip_over_std`:
    `Z_FRONT_STRIP - (Z_FRONT_BASE + STD_FACE_RAISE)`). The screen card's ls text binds it in place of `front_raise`.
  - `cards.edges.edges.window_bevel` is the bevel's width on the face (`WINDOW_BEVEL_W`: 1.285 std, 1.2 ls), as in
    the 4.26 data; it was the depth (`WINDOW_CHAMFER`: 0.3 / 1.2). New: `window_bevel_deg` (35 / 45 degrees) and
    `window_corner_r` [at the screen, on the face] ([0.4, 1.685] / [0.0, 1.2]). `window_land` stays (0.1 / 0.6). The
    edges card adds a "Screen window" row only where `window_bevel_deg` is given (3.68), and names round corners
    only where `window_corner_r[0]` is not 0.
  - Texts: the `strip` preset's caption, the `tub` explode text, `strip.steps`' "Close the case", `strip.case_cards`,
    `strip.diff` and the light-strip item of `glance.bullets` give the light-strip face (and `key-x3ls`) as
    `over_std` higher than the standard build's, not a fixed 1.2; the tub's `strip.diff` row adds the standard
    window's wider bevel with round corners. The ls print group gives no number ("key-x3ls, taller, for its higher
    face").
- **Facts:** the 4.26 ids (`envelope x4 printed plastic panel hardware rod files`) plus `battery`, with plain-text
  values and a `note`.
- **Controls:** labels are the switch roles ("Page down (DWN1)", "Power (UP2)"). `pin_from` is 10 mm outside the face,
  and the plug is computed as on 4.26 (the same J1 and divot).
- **Checks** (top level):
  - The ids are `interference_parts interference_hardware display_vs_board [strip_interference] insertion later_moves
    [strip_insertion] bottom_keys side_keys latches board_snap mid_detents print_watertight print_plate slicing dummy`.
  - `status` is `expected` (the gate on its floor and lips; until test 2 also the keys' drag bumps), `designed` (the midplate's spring nubs on the
    board, and a +0.1 panel against the midplate), or `accepted` (in `keys.checks`: a wrong-variant crank held at 0
    degrees while the board goes in; crank.json lists it 8 times).
  - `keys.checks`: `crank_failures crank_accepted crank_sweep rod_path key_in x_gaps logo mech_key_forces
    mech_key_preload mech_key_hooks mech_key_fit mech_crank_stress mech_key_sweep gate_fit mech_gate` (`gate_fit`: crank.json `gate` path, cam
    and bearing; `mech_gate`: mechanics.json `gate.checks`, the 33 N stiff stop ACCEPTED in its detail).
- **Downloads:**
  - The zip paths have folders: `shared/` (lid, midplate, crank-T, crank-M, gate; STL + STEP), `standard/` and
    `light-strip/` (tub, keys, the chin and gate coupons; these files carry `builds`), `ROD.txt` and
    `dummy/pcba-dummy.stl`, and `README.txt` at the root. Since 2026-09-28 the coupons are STL + STEP per build
    (`coupon-strip-`, `coupon-gate-` with `x3std` / `x3ls`; the drag coupon's `coupon-key-<n>-` went with test 2), the parts are `<name>.stl` (was
    `<name>-print.stl`), and `shared/` also holds the rod jig.
  - `ROD.txt` is x3's own `print/ROD.txt` (now `print/3.68/ROD.txt`: the rod and its gate); the adapter no longer
    writes one. The merge fails if a `print/3.68/` file is in no group.
  - The per-build one-plate 3MF is not in the zip, and the README says so. (Since 2026-09-28 the README points at
    the plate file, `print/silkscreen-368-plates.3mf`, which is not in the zip.)

**Checks run (2026-09-27, all passed; `adapter-368.json` `checks`)**
- Every output passes `validate_file`, with the GLBs decoded. Every byte is ASCII, and so is `adapt_368.py`.
- Both builds pass `validate_data` in strict mode, with the node cross-check (core + build + extras).
- **Kinematics:**
  - The 6 `crank.json` rest rows agree with the reference: the worst is 0.0036 deg and 0.0005 mm. The worker also
    asserts them with x3's own `crank.rest_theta(face_y, variant)` and `crank.key_lift`.
  - `derive()` at face_dy -0.2 / 0 / +0.2 for M and T agrees with `mechanics.json key_forces.travel` (rest, click and
    bottom angles, and the key travels): the worst is 0.0038 deg and 0.0005 mm.
  - The nominal values are the same as on 4.26: M click 4.832 deg / 0.412 mm, bottom 8.680 deg / 0.731 mm; T click
    4.813 deg / 0.410 mm, bottom 8.619 deg / 0.726 mm.
- **Geometry, measured on the shipped meshes:**
  - The crank-M nose front at theta 0 is at -1.9201, and the `nub_SW8` face is at -1.920.
  - The crank-T nose front is at -2.200, and so is the `sw_T_nub` face.
  - The `key_SW8` underside is at -0.200 in both builds, the pad crown's top.
  - `crank_M` moved to each key's X matches `crank_SW*.stl` in both builds: bounds, volume, and 7 sections across the
    crank, with a worst relative symmetric difference of 2e-10.
- **Checks in the data:** none false in either build (`checks` and `keys.checks`).
- **Drawings:** std has 21 and ls 24, none empty. The contact sheets (`work/std-drawings.png`, `work/ls-drawings.png`)
  and the key drawing per variant were checked by eye: the nose touches the plunger face, the key sits on the crown,
  the rail ring is dashed round the rod, and the strip bar and LEDs sit under the raised skin.

## 9. The bundler (step 2c, 2026-09-27)

**Run** from the repo root with either venv (it needs only the standard library and `sc_contract`):
`python -B showcase/gen/bundle.py [--from426 DIR] [--from368 DIR] [--out DIR] [--mirror DIR] [--page auto|skip|require] [--strict-page] [--no-decode] [--check-only]`.
- The defaults are the adapters' default outputs (`showcase/build/426` and `/368`), `--out docs/showcase` and no
  mirror (`--mirror DIR` writes a copy to publish). Until 2026-09-28 they were scratchpad folders. A run takes
  about 3 s.
- It does not run the adapters. Rerun them first when a case project's `out/` or its `print/4.26/` / `print/3.68/`
  changes; the freshness check warns when an adapter output is older than any file there.
- `--check-only` re-checks `--out` as it is (the manifest stands in for the adapter reports) and writes nothing.
- The output is deterministic: `manifest.generated` is the newest adapter time, and unchanged files are not rewritten.
  A second run with the same inputs writes nothing.
- Exit code 0 means no errors. Warnings do not fail the run.

**Outputs.** The adapter files are copied unchanged, so their sha1 values match `adapter-S.json`. Then the bundler
adds `strip.json` (its source is the git-tracked `showcase/page/strip.json`, in `docs/showcase/` until 2026-09-28;
nothing in `tools/` generates it) and
`optics_heatmaps.png` (from `docs/images/`, which is `tools/optics_sim.py`'s output). It writes `manifest.json` last,
and `index.html` once the page exists. The mirror holds exactly the published set, and extra files there are removed.

| file | bytes | loaded |
|---|---|---|
| `manifest.json` | 7,798 | first (also inlined in `index.html` as `SC_BOOT`) |
| `core-426.json` / `core-368.json` | 4,913,791 / 4,765,699 | first paint |
| `build-426-std.json` / `-ls` | 926,872 / 837,931 | first paint, build switch |
| `build-368-std.json` / `-ls` | 816,629 / 825,748 | first paint, build switch |
| `data-426-std.json` / `-ls` | 154,858 / 167,210 | first paint, any switch |
| `data-368-std.json` / `-ls` | 183,472 / 200,467 | first paint, any switch |
| `extras-426.json` / `extras-368.json` | 3,745,166 / 3,660,388 | compare or dummy chip |
| `models-426.js` / `models-368.js` | 11,072,734 / 6,968,984 | first download click |
| `strip.json`, `optics_heatmaps.png` | 36,230 / 222,273 | strip card |
| **total** (before `index.html`) | **39,506,250** | limit 64 MB; the largest file is 11.07 MB (limit 16 MB) |

- First paint (manifest + core + build + data): 4.26 std 6.00 MB, ls 5.93 MB; 3.68 std 5.77 MB, ls 5.80 MB.
- A build switch fetches about 1.0 MB; a size switch about 5.8 MB, once.

**Manifest additions** (on top of section 2; `validate_manifest` allows extra keys):
- `sizes.S` adds `side_keys` (count), `project`, `adapter_generated`, `zip`, `zip_bytes`, `display_nodes {std, ls}` and
  `panel {std, ls}` (the panel chip labels).
- `builds.B.dir` is the case projects' folder name (`standard`, `light-strip`).
- `variants {T, M}` holds display labels.
- `files.<f>` adds `size` (and `build` on build and data files). Assets have `kind: 'asset'`.
- `first_paint_bytes.S.B` is the sum above, without the manifest.
- **Use `manifest.files[f].bytes` for download sizes, not `data.downloads.js_bytes`.** The 4.26 adapter's `js_bytes`
  is one byte short (11,072,733 against the file's 11,072,734; the trailing newline). The bundler warns about it.
  Cache-bust data fetches with `?v=` + `files[f].sha1.slice(0, 10)`.

**Split checks.** The core / per-build split is checked three ways:
1. **Model files.** Core, build and extras are disjoint. A node in both build files must differ by hash, apart from
   display nodes.
2. **Each project's `out/shared-parts.json`.** The two schemas are parsed. 4.26 is `{part: {same, by}}` and does not
   list the tub. 3.68 is `{parts: {part: {same_files, same_solid}}, tub_specific: {part: {differ}}}`.
   - Mapping: `lid_body` -> `lid`, `crank-M` / `crank_SW*` -> `crank_M`, and `crank-T` -> `crank_T`.
   - `lid` (the fused copy), `key-426` / `key-x3*` and the coupons are not stage nodes.
3. **STL bytes.** `out/standard/<part>.stl` is compared with `out/light-strip/<part>.stl` for every printed-part node
   (14 on 4.26, 12 on 3.68).

The adapter reports' `nodes` and `parts` must agree with these, and every adapter file's sha1 must match its report.
The result: 4.26 per-build = tub (plus the display nodes); 3.68 per-build = tub + `key_SW9 key_SW8 key_SW3 key_SW2`.

**Download checks.** For each size:
- `models-S.js` parses, and the zip tests clean. Its name and bytes match `data.downloads`.
- Every `downloads.groups` file is in the zip with the same bytes.
- It holds both tubs, both 3.68 key sets, a coupon, `ROD.txt`, the PCBA dummy and a README.
- Every file of the size's print folder (`print/4.26/`, `print/3.68/`) is in it with the same CRC.
- No content appears twice. A file that the print folder itself ships under two names with the same bytes would be
  a note, not an error; there is none (the drag coupon's keys, which could have matched a key, went with test 2).

**Contract fix (done in step 5).** `sc_contract.validate_manifest` now lets the builds differ in `panel_*`,
`ribbon_*` and `strip_*` nodes only, so `python -B gen/sc_contract.py --bundle docs/showcase` passes and the waiver
below no longer fires. The 4.26 builds differ in display nodes:
- std: `panel_epd panel_light panel_touch ribbon_main ribbon_light ribbon_touch ribbon_touch_ic`
- ls: `panel_epd ribbon_main`

`bundle.waive()` drops exactly that error when the difference is only `panel_*` / `ribbon_*` / `strip_*`; a test shows
it still reports a non-display mismatch. Until the rule is relaxed, `python -B gen/sc_contract.py --bundle docs/showcase`
prints only that one error and exits 1. `bundle.py --check-only` is the check to use.

### The page hook: how index.html is assembled
When `page/shell.html` exists (`--page auto`), the bundler builds `index.html` from the shell, `viewer.js`,
`strip3d.js` and `cards/<id>.html` + `cards/<id>.js`. Each marker must appear in `shell.html` exactly once, as a
comment:

| marker | replaced by |
|---|---|
| `<!--SC:BOOT-->` | `<script>window.SC_BOOT={generated, manifest}</script>`. The page uses `SC_BOOT.manifest` and does not fetch `manifest.json` (it still ships, for tools). |
| `<!--SC:CARDS-->` | the card `<article>`s in `sc_contract.CARDS` order, each after a `<!-- card <id> -->` comment |
| `<!--SC:VIEWER-->` | `<script type="module">` + `viewer.js` + `</script>` |
| `<!--SC:STRIP3D-->` | `<script type="module">` + `strip3d.js` + `</script>` |
| `<!--SC:CARD_SCRIPTS-->` | one classic `<script data-card-js="<id>">` per card: `(function(){try{ <card js> }catch(e){console.error('[card <id>]',e); if(window.SC&&SC.cardError)SC.cardError('<id>',e);}})();` |

- **Order.** Place `CARD_SCRIPTS` after the classic script that defines `window.SC`, so each card's `SC.card({...})`
  registers synchronously. The module scripts run after the parse, so they attach to `SC` that is already defined.
- **`SC.cardError(id, err)`** is optional. When the shell defines it, a card whose script throws is reported, and the
  other cards still load. This was checked in node.
- **Cards without fragments** get a placeholder `<article class="mech sc-placeholder">` (title + Show in 3D) and a
  warning, so the tour's order and visibility can be tested before the cards land (step 3). A missing
  `page/strip3d.js` leaves the STRIP3D marker empty with a warning. `--strict-page` makes both errors; the final
  build should use it.
- Preconnect links to the font origins (`https://fonts.googleapis.com`, no trailing slash) are allowed (step 3 fix).
- **Static checks.** Any one of these failing means `index.html` is not written:
  - `shell.html`: every marker once; scripts from `cdn.jsdelivr.net/npm/` or `cdnjs.cloudflare.com` only, and links
    from Google Fonts or those CDNs only. A missing `three@0.169` importmap entry is a warning.
  - `viewer.js`, `strip3d.js` and each card's JS contain no `</script` (write `<\/script`) and are ASCII.
  - Each fragment:
    - is exactly one `<article class="mech" data-card="<id>">` with `data-preset` equal to `CARDS[id].preset` (none
      for `checks`), and no `<script>`;
    - comes with both of its files (`.html` and `.js`).
  - Ids are unique across the whole page. An id without the card prefix (`<id>-...` or `dw-<id>...`) is a warning.
  - The top-level `id`, `title`, `order`, `preset`, `sizes` and `builds` literals in `SC.card({...})` equal `CARDS`
    (a small scanner that skips strings and comments reads them).
  - Every `needs` path resolves, non-empty, in each data file the card applies to.
  - Every `[data-k]` path resolves, and every `[data-show]` names a preset. This is checked in each data file where
    both the card and the element's `data-only` tokens (its own and its ancestors') apply. Unknown tokens are a
    warning.
  - Every `[data-goto]` names a card.
  - The strip card (`enter_build: 'ls'`) is checked against both sizes' `ls` data.
- **Pruning.** When `index.html` is written, files in `--out` that are not in the bundle are deleted. That is today's
  `case426.json` and `case368.json`, which only the old light-strip page used. Until then the bundler lists them and
  leaves the old `index.html` alone.

**Checks run (2026-09-27, all passed; 0 errors, 3 warnings: the `js_bytes` pair and the waiver)**
- Both sizes: all 14 adapter files validate with the GLBs decoded, and all 4 data files pass strict validation with
  the node cross-check.
- The split agrees three ways: model files, `shared-parts.json` and STL bytes.
- Both zips pass every download check above, and both adapters are fresh (13:19 / 13:42 against `out/` 12:32).
- `validate_bundle` passes on `docs/showcase`, with the one waiver. The mirror is byte-identical (17 files).
- A rerun is idempotent (0 written). `--check-only` passes.
- **Mutation tests**, run in memory or in a temporary directory:
  - 15 split, zip and waiver faults are all caught: a shared part shipped per build (caught 3 ways), the tub or a
    3.68 key in core, a node in core and build, a key missing from one build, a stale report, parts disagreeing, a
    missing `ROD.txt`, a missing key set, a shared part twice, wrong group bytes and a wrong zip name. The waiver
    also still reports a non-display mismatch.
  - 17 page faults are all caught, and a good page assembles with `SC_BOOT` equal to the manifest.

## 10. The page shell and the viewer (step 3, 2026-09-27)

**Files.** `page/shell.html` (CSS, markup, page core) and `page/viewer.js` (the stage), assembled by `bundle.py`
into `docs/showcase/index.html` (133 KB) and mirrored to `scratchpad/showcase-new/`. The bundle now **replaces the
old light-strip page** in `docs/showcase/` and prunes `case426.json` / `case368.json` there (both still in git HEAD,
and the published copy is still in `scratchpad/showcase/`). The strip card step ports from `git show
HEAD:docs/showcase/index.html`.

**Test tools** (in `scratchpad/showcase-build/`):
- `step3_serve.py <dir> <port>`: serves the bundle like the artifact host (index.html inside the doctype / viewport
  skeleton) plus `/__t.js` = `step3_t.js`. Stop it afterwards.
- `step3_t.js`: `window.T` helpers: `combo(S, B)`, `info()`, `kin()`, `chips()`, `stagePress()`, `explodeCheck()`,
  `sectionCheck(x)`, `swapKeeps(S, B)`, `variantSwap()`, `enterStrip()`, `extras()`, `presets()`.
- `step3_plan.py <tag> <light|dark>` writes the cdp plan; `step3_runall.sh` runs 1400x900 and 390x844, light and
  dark, with `showcase-keys/cdpplan2.mjs`; `step3_sheet.py` makes contact sheets of the shots (`shots3/`).
- Headless screenshots only paint what is inside the window: scroll the element into view before a shot.

**Checks run (all 4 runs: 1400x900 and 390x844, light and dark; 0 page errors or warnings in each)**
- All four size / build combinations mount: 69 parts (4.26 std), 64 (4.26 ls), 60 (3.68 std and ls), no
  unmatched nodes, 8 crank instances, 5 / 3 side keys. The tub mesh changes on every size and build switch; the
  3.68 keys change with the build and the 4.26 keys do not; `panel_light` only on 4.26 std; the strip chip only on
  ls; the panel chip, the build-diff tag, the masthead facts and the hash follow the state.
- Kinematics on the stage for SW8 at rest / click / bottom, T and M: crank angle, key Z and the visible plunger's Y
  equal `SC.crank` (1e-6 deg, 1e-9 mm); `SC.crank.derive` equals `keys.derived`. T: 4.8133 / 8.619 deg, key 0.4104 /
  0.726 mm, plunger 0.25 / 0.45 mm.
- Chips toggle a group; the stage Press slider on All keys moves every crank and side key; explode 0.6 moves the
  screws (-88 mm on 4.26, -80 on 3.68); section X at SW8 clips every material.
- A size switch with the section on and SW8 pressed keeps the section, the pressed angle and the camera.
- The variant swap shows exactly the right crank / switch instances; opening the strip card on the standard build
  switches to ls with the toast, and Undo goes back (the card is then away again).
- The compare chip loads `extras-S` lazily; every preset of the data runs without an error (20 on 4.26, 21 on 3.68).
- No horizontal scroll at 390 or 1400; 0 `.k-missing`; body background from the tokens in both themes; at 900 px
  tall the sticky stage is 881 px. A bare-token hash (`#368-ls`) opens that size and build.
- `bundle.py`: 0 errors (warnings: the known `js_bytes` pair, the display-node waiver, strip3d.js missing,
  placeholders); `--check-only` 0 errors; every source file ASCII.

**For the next steps**
- Card steps: write `cards/<id>.html` + `.js` per section 5. The placeholders disappear as fragments land; build the
  final page with `--strict-page`.
- The strip card (step 11): `strip3d.js` attaches to `SC.viewer` (`group('strip')`, `scene`, `THREE`, `camera`,
  `controls`, `tween`, `section`, `clip()`, `extraSlot()` for the Fold slider). There are no `strip_*` nodes in any
  model file, so the strip chip controls only the live group. `presets.strip` exists in all 4 data files.
- The keys card (step 7) drives the stage with `SC.viewer.press('SW8', 0, {theta, src: 'keys'})` and listens to
  `pressed` (ignore its own `src`); the variant selector is `SC.set({variant})`.
- The files card (step 10) uses `SC.dl` and needs the `downloads` capability at publish.
- Not done here: meshopt compression, and the old Rev K / x3 pages (they stay as history).


## 11. The bottom-keys card (step 4-keys, 2026-09-27)

**Files.** `page/cards/keys.html` + `keys.js` (`SC.card({id: 'keys', ...})`, all sizes and builds). Only the page / card
API above is used; `viewer.js` and `shell.html` are unchanged.

**What it does.**
- The `key` drawing through `keys.draw_ref`, drawn from a card-side copy with a wider window (labels beside the parts).
  Moving groups: `crank` (`crank_M`, `crank_T`) and `crankb` (beyond `cheek`) rotate `rotate(-(th - theta_built), y_rod,
  -z_rod)` (the SVG frame is u = Y, y = -Z, so +theta is a negative SVG angle); `key` + beyond `hook` translate
  `keyDown(th, theta_built)`; `board` (`pcb`, `sw_*`) translate `dy`; `nub` translate `dy + plungerIn(v, th, dy)`.
  The other variant's `crank_ / sw_ / nub_` layers are hidden.
- Pose = press fraction `t` and board offset `dy` in {-0.2, 0, +0.2} (the "Board position" selector: plunger face moved
  +Y). `th = rest + t (bottom - rest)` from `SC.crank.raw(v, dy)`. State: bottom within 0.05 deg, clicked from click.
  Readouts: crank, key down from rest, plunger in, switch, key proud (`cards.keys.proud_mm - keyDown(th, theta_built)`).
- Play / scrub with rest / click / bottom marks; autoplays while on screen until the reader takes over; reduced motion
  turns Play into Press / Release steps (rest, click, bottom).
- While the card is open every pose goes to the stage: `SC.viewer.press(draw_ref, t, {theta, src: 'keys'})` when
  `dy` is 0, `press(draw_ref, t, {src: 'keys'})` otherwise (the 3D board stays nominal). It re-pushes after the
  `keys` preset runs (Show in 3D) and after each `state` event (a variant swap re-mounts the stage with the old
  angle). A `pressed` event from anyone else for `draw_ref` or `all` (a crank) moves the drawing.
- The switch selector calls `SC.set({variant})`: the stage swaps crank-M/T and the switch bodies; the card redraws.
- Info boxes computed from `keys` (and `cards.keys`): forces (the mechanics table normalised over both size shapes),
  travel, proud (range over +-0.2, lowest at bottom, wrong crank), rod (`rod_check`), the hooks (`hooks`; was the drag leaf); a board
  tolerance table whose last column checks each `rest_rows` entry against the computed rest (0.015 deg / 0.0015 mm);
  `keys.checks` as a collapsible list.

**For tests and other cards:** `SC.cards().keys.now()` returns the pose `{t, dy, variant, theta, key_down,
key_from_built, plunger_in, state, proud, range, open, playing}`; `SC.cards().keys.pose(t, dy?)` sets it (stops play).

**Checked** (headless, 1400x900 and 390x844, light and dark; all four size / build combinations, T and M; 0 page
errors or warnings): the drawing's crank transform moves the nose and pad centres exactly to `SC.crank.rot` (1e-4),
the key's underside stays on the crown and the nose on the plunger face (2e-6) at rest, click and bottom, also at
dy +-0.2; the stage's crank angle, key Z and visible plunger Y equal the card's pose (also with x4); stage slider ->
drawing; wrong-crank proud 1.979 / 1.042 mm equals 4.26 `drag.key_proud_mm` (until test 2) and 3.68 `wrong_variant_key_shift_mm`;
all tolerance rows agree with the solver rows; `#368-ls-M-keys` opens the card on M; no horizontal scroll.

## 12. Mechanism cards A (step 4-mech-a, 2026-09-27)

**Files.** `page/cards/<id>.html` + `.js` for `sidekeys usb reset screen detent ribbons` (written as `mech-a-<id>.*`, renamed in step 5). **`bundle.py` reads
only `cards/<id>.*`**, so these must be renamed to `cards/<id>.*` when the page is integrated (or the bundler taught
to accept `cards/*-<id>.*`). Until then the real bundle shows placeholders for these six. The content already uses
`data-card="<id>"` and `SC.card({id: '<id>'})`; test bundles were made by a wrapper that renames into a scratch page copy.

**What each card does.**
- `sidekeys` (all 4): drawings `key_side`, `tab_plan`, `tab_elev` (refs from `cards.sidekeys.draw`; left-wall keys are
  mirrored), a key selector (`#sidekeys-sel`) and a press slider that calls `SC.viewer.press(<ref>, t, {src:
  'sidekeys'})` on the chosen flexure control and moves the drawn key (rotation `sign * d / length` about the root,
  nub `max(0, d - gap)`); it follows `pressed` for any flexure (switching the selection) and for `all`, redraws on
  `exag`, and resets on `focus`. Table and numbers from `tab_mech` / `tab_geom` / `summary`; roles from `roles` (3.68)
  or side + height + the narrow-nub power key (4.26: SW10). The sweep sentence counts only rows up to `stop_travel`.
- `usb` (all 4): drawings `usb`, `usb_plan` with the plug drawn over them; slider t = the `plug` control's t (0 = 9 mm
  out, 1 = seated), drives and follows the stage.
- `reset` (all 4): drawing `reset`; the slider uses the viewer's `pin` mapping (0-0.6 approach, 0.6-1 push by
  `max_travel`), drives and follows the stage, resets on `focus`.
- `screen` (per build): `[data-only]` text for `426 std` (FT01C), `426 ls` (plain GDEY0426T82, `plain_stack`) and
  `368` (+ `ls`: raised front, `strip_stack`, the `left_border` note). Labels are placed from the drawings' layers.
- `detent` (all 4): drawings `detent_plan`, `detent`; the screw row only where `cards.screen.screw_clear` exists (4.26).
- `ribbons` (per build): 3 ribbons on 4.26 std; one FPC on 4.26 ls (outline numbers only: its `report` is the FT01C's)
  and on 3.68 (report `main` row). Tail offset = outline tail centre + `cards.screen.panel.x0` - connector x.

**Checks run.** Headless (cdpplan2) at 1400 and 390 wide, light and dark, all 4 size/build combinations x 6 cards:
0 page errors or warnings, 0 `.k-missing`, 0 `.card-err`, no `?`, no horizontal scroll; the stage's flexure angle
equals `sign * t * max_travel / length` for the pressed key; plug and pin show and follow; screenshots checked by eye.
Also bundled together with the `keys` and `strip` cards: 0 errors.

**API gaps (worked around inside the cards; suggested for the shell / viewer).**
- `SC.A(d).label` should keep text inside the drawing window: each card carries a `fitA(a, d)` wrapper.
- No event when the viewer releases presses (`release()`, presets, the stage selector): card sliders reset on `focus`.
  Suggest emitting `pressed` with `src: 'release'`, or `SC.viewer.pressState(id)`.
- `SC.viewer.press(id)` always moves the stage's selector to `id`, so a card cannot press several flexures at once
  without the cranks. Suggest `press([ids])` or a `flexure` group id.
- Suggest `self.bbox(layerId)` on `SC.Drawing`: `screen` and `ribbons` compute layer boxes to place labels per size.

**Data notes (4.26 light strip).** `cards.ribbons.ribbons.report` and `cards.screen.stack` are the FT01C's numbers
unchanged (the project's own `out/light-strip/mechanics.json` has the same); the plain panel's are `outlines.main` and
`cards.screen.plain_stack`. The 4.26 `bezel` drawing has no strip layer on ls. 4.26 lacks `cards.reset.hole_d`,
`sink_d` and `below_usb_mm` (3.68 has them).

## 13. The light-strip card and strip3d.js (step 4-strip, 2026-09-27)

**Files.** `page/strip3d.js` (ES module), `page/cards/strip.html`, `page/cards/strip.js`. Tests are in
`scratchpad/showcase-build/strip/` (`strip_t.js` = `window.ST`, `plan.py`, `runall.sh`, `sheet.py`).

### strip3d.js: `SC.strip3d`
- The old light-strip page's fold model, ported unchanged: the per-size fold paths (4.26: the "legs" solve; 3.68:
  the "bump" solve plus the hinge that folds the top pair back), `progFor(f)`, `place()` and the banded
  triangulation. The solve lands the contacts at Y 23.25 (in J3) in both sizes.
- It builds once from `strip.json` into `SC.viewer.group('strip')`: the flex, 3 PI stiffeners, the 3M 9077 tape
  (the 2 front pieces), 12 LEDs (body, lens, light cone), D13/D14, 3 test pads, 6 contacts and 4 Kapton pieces.
  Object names are `strip3d-*`. The light on the page is a plane `strip3d-light` in `group('display')`, at
  `meta.z.lip + 0.06`. So there is one WebGL context, and the strip explodes with the `strip` group.
- **Z from data.** `zFront = cards.strip.geometry.flex_top - (stack.tape + stack.pi + stack.flex)`. That is 4.00 on
  4.26 (the plain panel's stop face; the old page used 3.926) and 3.47 on 3.68.
- **When it builds.** It follows `state`. On an `ls` build it loads `strip.json` (once, 36 KB) and places the strip
  for the size. So the strip chip shows the live strip on every ls build, not only while the card is open (this
  changes the section 2 table's "when the strip card opens"). On `std` it only turns the light off; the viewer hides
  the strip chip's root there.
- **API.**
  - `ready` (Promise), `sync()`, `built()`.
  - `fold(f?, {animate})` returns the target (0 = flat as it arrives, 1 = fitted). It eases by time (tau 0.22 s),
    so a slow frame rate does not slow it. `foldNow()` is the current value.
  - `tape(on?)`, `kapton(on?)`, `light('off' | 'warm' | 'cool'?)`.
  - `ledY(ref = 'D4')` is an LED's case-frame Y (the default Y cut).
  - `reset({animate})`: fold 1, tape, Kapton and light off.
  - `probe()` (for tests: tip, D4, folded LEDs, bbox), `stats()`, `group`.
- **Events.** `strip3d` (the API, once, when the module has attached), `stripfold` `{fold, target}` while the fold
  moves, `stripset` (stats) after any setting.
- Its materials clip with the stage's section plane (the viewer re-applies the plane to live groups).

### The card (`strip`, order 25, `enter_build: 'ls'`)
- **Opening it on the standard build.** The shell switches to ls and shows the toast "Switched to the light strip
  build." with Undo. The away card shows its heading and "Switch to it".
- **Stage panel.** `onEnter` puts a panel in `SC.viewer.extraSlot()`: previous / step label / next, the Fold
  slider, and Case / Cut / Tape / Light chips (Light cycles warm, cool, off). `onLeave` removes it (the slot hides
  when empty), resets the strip, restores the everyday chips and turns off a cut it made.
- **Steps** come from `cards.strip.steps` (`{t, cam: [[cam], [tgt]], f, tape?, kapton?, caseOn?, cut?, cutX?,
  cutY?, drawing?, b}`). A step sets:
  - the camera, with Y up, as the old page had it. A view along Y (the cuts across the bar) takes Z up instead. A
    close-up (under 100 mm) backs off by up to x1.8 on a narrow stage; the far views fit a tall stage as they are.
  - the chips: Case off shows only strip, display and pcba.
  - the cut: section X at `cutX`, or Y at `cutY` (else LED D4), keeping the far side (flip).
  - the fold, the tape, Kapton (`kapton || tape`, as the old page did), and the caption and tag.
  - Before each step, `preset('home', {animate: false})` clears another card's focus or highlight, and the camera
    is put back (see wish 1).
- **Content.**
  - The section drawings: `strip_led`, `strip_holddown` (4.26), `strip_fold` (3.68) and `strip_neck`, with the LED
    top to ceiling dimension.
  - The flat pattern, the tape table, the optics PNG, BOM, electrical and flex (these are static, from the old page).
  - This size's case bullets (`cards.strip.case_cards`).
  - **Standard vs light strip**, computed from `manifest.parts[S].per_build` / `shared` and
    `sizes[S].display_nodes`, with the text from `cards.strip.diff`. It warns in the console if the data's `same`
    disagrees with the manifest.
  - The `strip*` rows of the top-level `checks`, and tables from `cards.strip.checks` (`plain_stack`, `foot_stop`,
    `seat_entry`, `channel_skin`, `tail`).
- `needs`: `cards.strip.steps case_cards diff geometry checks`. Bound values: `cards.strip.geometry.led_top`,
  `ceiling`, `flex_top`.

### Checked (headless; 1400x900 and 390x844, light and dark; both sizes, ls, entered from std)
- 0 page errors or warnings, no horizontal scroll, 0 `.k-missing`, 0 card errors.
- **Away and switching.** On std the card is away and the strip chip is hidden. "Switch to it" gives ls, the card
  open, the toast and Undo. Undo returns to std with the card away and the panel removed.
- **Steps.** Every step on both sizes (9 on 4.26, 10 on 3.68) lands on its own fold, cut, chips, tape and
  highlighted row. A size switch with the card open keeps the step index and rebuilds the strip for the new size.
- **3D against the CAD sections.**
  - LED D4's body in the scene matches the `strip_led` drawing's `led` layer to 0.003 mm in X and 0.000 in Z, on
    both sizes.
  - On 3.68 the folded D7 at the `strip_fold` cut is at Z 2.287 to 3.087; the drawing's `folded_led` is 2.285 to
    3.085.
  - Fitted, the contacts are at Y 22.15, Z -0.37 (4.26) and -0.31 (3.68): in J3.
- **Light.** Warm lights D1 to D6 on 4.26, and D2 to D6 on 3.68 (D1 is folded under); cool is the same pattern.
  Off hides the page plane.
- **Contact sheets checked by eye:** every step, light warm, fold 50%, every card section, and the stage panel.
- **Harness note.** Headless Chrome can stop producing frames after clipped screenshots far down a 390-wide page.
  When that happens, requestAnimationFrame and the viewer's own loop stall, and a smooth scroll never ends. The plan
  scrolls to the top and shoots the stage first. `until` expressions must return a boolean (`!!(...)`): returning
  `SC.strip3d` makes CDP's returnByValue fail, and the wait runs to its maximum.

### API wishes (not implemented here; the card works around each one)
1. `SC.viewer.look({focus, highlight})` or `clearLook()`, to drop another card's focus without running a preset.
   Now: `preset('home')`, then the camera is restored.
2. `userData.noAO` honoured by the GTAO pass. Now the light cones zero their `matrixWorld` while an override
   material renders.
3. **Viewer bug.** A chip that was turned off only because its group was unavailable stays off once the group is
   available again (the strip chip after std, then ls). strip3d turns the strip chip back on when it enters ls from
   another build; the viewer's `mount` should do this.
4. A `fit` option on `SC.viewer.tween(cam, tgt, up)` (the presets' narrow-aspect widening). The card has its own.

## 14. Mechanism cards B (step 4-mech-b, 2026-09-27)

**Files.** `page/cards/<id>.html` + `.js` for `glance joint battery boardprep zstack closing edges compare` (written as `mech-b-<id>.*`, renamed in step 5).
Like mech-a, **`bundle.py` reads only `cards/<id>.*`**: rename `mech-b-<id>.*` to `<id>.*` at integration (or teach
the bundler `cards/*-<id>.*`). The content already uses `data-card="<id>"` and `SC.card({id: '<id>'})`. Test bundles
were made with `scratchpad/showcase-build/mech-b/bundle_test.py [--with-others]` (renames into a scratch page copy).
Only the page / card API is used; `viewer.js` and `shell.html` are unchanged.

**What each card does.**
- `glance` (all 4): `cards.glance.bullets` as a numbered list, a one-line summary from `facts` (envelope, panel,
  battery), the build-diff tag from `manifest.sizes[S].build_diff`, and Show assembled (`home`), Show the back
  (`back`) and Play the assembly (`data-play`).
- `joint` (all 4): the parting-line plan built from `cards.joint.joint` (runs, latches per wall including the 3.68's
  `snaps.top`, tabs, USB, reset, J6 if present, top screw; key refs per wall from `cards.sidekeys.tabs`), the four
  drawings `joint_tongue joint_at_tab joint_top joint_latch` (refs from `notes.ref`), nums from `cards.joint.latches`,
  wall text from `cards.sidekeys.tab_geom`. Buttons `joint`, `latch`.
- `battery`: 4.26 = Rev K's slot (`bay_lip`, `fence`, `battery` drawings, nums from `cards.battery.battery`
  `bay/bay_p/fence/data`). 3.68 = the board-rear depth map (SVG, run-length rects per band, seen from behind, bands
  and legend labelled from `battery.deep_parts`; colours are `color-mix` of `--copper` into `--paper`, so both
  themes work), the `bay` and `bay_plan` drawings, lead text from `battery.lead`, and the layouts table (static,
  from the x3 README "The battery"; the chosen row's depth and height come from `meta.body`).
- `boardprep` (3.68): a plan of the trimmed board from `cards.battery.depth_map.outline`, the cut line at
  `boardprep.trim_y`, the open hatched band for the cut-off extension with `gone_with_cut`, snap posts from
  `cards.closing.holes`, the post in SW5's site (`support_post`), J5, the side switches; steps and nums from
  `cards.boardprep`.
- `zstack` (all 4): `cards.zstack.bars` to scale (pixel-true SVG, redrawn by a ResizeObserver), `beside` bars in a
  narrow column, labels spread and wrapped. The other size's stack (same build) is fetched with
  `SC.load(SC.files(other, B).data)` when the card is first opened, or by the "Put the X beside it" button; once
  the reader uses the button, opening the card no longer adds it. Nums: total, in front of / behind z 0,
  `with_keys`, `without_battery`.
- `closing` (all 4): drawings `clamp`, `pin`, `top` (hole ref from `notes.hole` on 4.26, `notes.ref` on 3.68),
  board-snap text and nums from `cards.closing.board_snap`, and the rod's gate from `keys.rod` +
  `cards.closing.gate` + `cards.keys.end_play`. "Show the rod gate" runs `preset('close')`, turns the section
  off, highlights `gate` + `rod` and tweens the camera onto the `gate` part's bounding box from the -X side
  (checked: the camera lands at about (-44, -36, 27) on every size and build).
- `edges` (all 4): wordmark and mirrored back icon from `cards.edges.logo(_back)`; edge numbers; depth, window land
  and `grip_grooves` only where the data has them (3.68).
- `compare` (all 4): table, front and side outlines, the front-to-back stack bar (`cards.compare.budget`: this is
  the X4 compare stack chart the critique says to keep), sentences computed from `rows`, and a sources note
  naming Zorian22 and CC BY-NC-SA. On `368 ls` a line says the X4 models stand level with the standard build's face.

**Drawing helpers the cards carry (API wishes).** Each drawing card has `fitA` (as mech-a), `P(dr, layer, u, v)`
(the nearest point inside a layer, so a label's dot sits on the right part in both sizes), `labAt(...)` (a label
whose text goes to a model-space point), and `widen(dr, dv0, dv1)` (a copy of a drawing with a taller window, for
the very wide sections `bay_lip`, `battery` and `bay`, so labels get rows above and below). Suggest `SC.A` gain
`labelAt`, and `SC.Drawing` a `pointIn(layer, u, v)` / `bbox(layer)` and an `opts.pad` for extra window room.

**Checked** (headless cdpplan2; 1400x4200 and 390x4200, light and dark; all four size / build combinations, every
card opened; also bundled with keys, strip, mech-a and end-*): 0 page errors or warnings, 0 `.k-missing`, 0
`.card-err`, no `?` / NaN / undefined, no annotation text outside a drawing's viewBox, no card wider than itself, no
horizontal page scroll; the rod-gate camera, the zstack toggle and every preset these cards use (`joint latch
battery zstack close edges back compare home`, + `boardprep` on 3.68) run without a warning. Screenshots of every
card were looked at in both widths and themes.

**Data notes for the adapters.**
- **Attribution (4.26).** `cards.compare.attribution` and the `compare` preset's caption say the *retro case* model
  is Zorian22's. Both projects' `compare.py` headers and Rev K's page say the **Xteink X4 reference model** is
  Zorian22's (Thingiverse thing:7287950, CC BY-NC-SA) and the retro case came from its author's print files. The
  3.68 data has it right. The card writes the correct sources note itself; section 3 of this file (`cmp_*` row)
  and `sc_contract.NODE_RULES` / the sample repeat the wrong wording.
- **4.26 `pin` drawing** (H2, y 77.75) cuts the snap post exactly through its slot, so no post shows in the hole
  (the 3.68 adapter cuts 0.55 mm off centre for this reason). Suggest the same offset on 4.26.
- 4.26 has no `cards.edges.logo.width/depth` (the card uses the bounds) and no `grip_grooves`, though its `back`
  caption mentions grip grooves; `cards.closing` has no `pilot` / `cb_depth` on 4.26.
## 15. Assembly, checks and model files (step 4-end, 2026-09-27)

**Files.** `page/cards/assembly.*`, `checks.*`, `files.*` (`.html` + `.js`; ASCII; written as `end-<id>.*`, renamed in step 5). As with mech-a, **`bundle.py`
reads only `cards/<id>.*`**, so integration must rename `end-<id>.*` to `<id>.*` (or teach the bundler the prefix). The
content already uses `data-card="<id>"` / `SC.card({id: '<id>'})` with the `CARDS` literals (checks: `preset: null`, no
`data-preset`). Tests bundle through `scratchpad/showcase-build/end/bundle_test.py --with-others` (renames into a scratch
page copy; skips `mech-b-*` unless `--with-b`, since those were half-written during this step).

### assembly (order 120, all four)
- The step list is `D.assembly` as the adapters wrote it (project READMEs). **Both projects put the keys before the
  cranks** (at rest height the keys block the cranks' path), then cranks, rod from the -X wall, the printed gate
  (a step each since the gate replaced the rod screw).
- **Play sync.** `walk(D)` maps each explode index k (`explode.order[k]`) to a run of assembly items that name that
  group, searching forward from the previous run, so the list marks what the stage is doing (`li.now`, earlier items
  `li.done`). Items before the first run are "before you start" (coupon, rod prep, 3.68 board prep), items after the
  last one "closed up" (turn it over); `step === order.length` (Play finished) marks those. Listens to `step` in the
  render scope, so the stage's own Play button and explode slider drive it too.
- **Tap a step**: `focus('assembly')`, then `SC.viewer.explode(1 - (k - 0.02) / (n - 1))` (the step's last group just
  landed; `kOf[i]` skips a group the next item shares), highlights the step's groups, and captions the stage with the
  item's own title and text. Items without a 3D step run their `preset` (3.68 prep -> `boardprep`).
- Also: what you need (facts `printed plastic panel battery rod hardware`, the strip card link on ls), the print list
  from `meta.printed.parts` with the crank row following the variant (`onVariant`), and the screw count in the thesis
  parsed from `facts.hardware`.
- Test hooks: `SC.cards().assembly.walk(D)` = `{runs, first, last, kOf, n}`, `.now()` = the marked items.

### checks (order 130, all four)
- One list: `D.checks`, then `D.keys.checks` ids not already there (4.26 has them in both; 3.68 only in keys). The count
  equals `cards.checks.count` in all four files (the card warns in the console otherwise).
- Grouped by source into Bottom keys, Light strip, Interference, Assembly paths, Side keys, Snaps and detents, Printing,
  PCBA dummy (none fell into Other). A `<details>` per group (open when something fails), each row: pass mark, label,
  value, status badge (`expected` / `designed` / `accepted`, with a legend for the ones used), detail and source. JSON
  strings in `detail` (the 4.26 verdict rows) are parsed and spelled out. No prose beyond one note that these are model
  checks and the gate coupon proves the gate on the printer (the chin coupon is an optional fit check; until test 2 the
  note said the drag coupon was tuned there).
- Counts: 4.26 std 75, ls 87; 3.68 std 27, ls 29; all pass (2026-09-28, with the gate's rows).

### files (order 140, all four)
- Zip from `SC.dl.zip(S)`; "Download everything" saves it whole; "Only the <build> build" and each group's Download save
  `SC.dl.subset` of the group paths (+ `README.txt`). Names derive from `downloads.zip`: `silkscreen-case-4.26.zip`,
  `-standard.zip` / `-light-strip.zip` (build and 3.68's build groups use `builds.B.dir`), `-<group id>.zip`.
- Sizes: the zip from `manifest.sizes.S.zip_bytes`, the one-off load from `manifest.files['models-S.js'].bytes` (not
  `downloads.js_bytes`), file sizes from the groups. Rows tag "this build" / "other build" (3.68) or name the build per file
  (4.26 tubs). Text from `cards.files` (`plate`, `print` on 3.68, `dummy`: counts, size, mass at 1.24 g/cm3, open switch
  sites, the dummy's contacts, USB mock).
- With no host downloads capability the buttons save through the browser (`SC.dl.plain()`); they stay off only when
  even that is missing: "Downloads are not available in this view." A host that offers the capability (a published
  copy) should be given the `downloads` capability.
- Test hooks: `SC.cards().files.pack(which)` -> `{name, blob, paths}` without saving; `.paths(D, which, B)`; `.info()`.

### Checked (headless, cdpplan2; 1400x900 light, 1400x3000 light and dark, 390x4200 light, 390x4200 dark without the
downloads mock; all four size / build combinations each)
- 0 page errors or warnings, no horizontal scroll, 0 `.k-missing`, 0 `.card-err`, no `undefined` / `NaN` /
  `[object Object]` in the three cards.
- Explode sweep: every step marks at least one item, every marked item names the arriving group, marks never go back.
- Real Play in every combination: step events 1..n in order, finished, the end marks the trailing items.
- Every item tapped (12 / 13 / 10 / 11): stage explode = the item's step (to the slider's 0.001), or its preset; the
  list marks it; the caption shows it.
- Checks: rows = `cards.checks.count`.
- Downloads with a mocked `window.claude.use('downloads')`: every button in every combination (10 zips on 4.26, 7 on
  3.68): the saved zip parses (central directory, every local header and name), its entries are exactly the expected
  paths, `README.txt` inflates to its size, the whole zip is `zip_bytes`, names match `silkscreen-*.zip`, and no
  `silkscreen-rev-k-` anywhere in the page. Without the mock the buttons use the plain browser download.
- Screenshots of all three cards in every run and the stage after a tap, looked at.

### API wishes (worked around in the cards)
1. The viewer never emits `step 0`: at explode 1 the loop already reports group 1 (its `lo` is 0), so the tub step is
   never marked by Play. Play's end also emits `-1` just before `order.length`.
2. A `[data-play]` click does not open its card (the shell returns before the card-open branch); the card opens itself.
3. A render scope drops `ctx.on` listeners but not DOM listeners: a card that binds static fragment elements in
   `render` gets one more listener per size / build switch. The cards use `onclick` on static elements; a
   `ctx.listen(el, ev, fn)` dropped with the scope would help (the mech-a / keys wish for `ctx.cleanup` is the same).
4. `SC.viewer.explode(e)` stores the value through the slider (step 0.001); an `explodeTo(step)` would avoid every card
   re-deriving the viewer's `lo/hi` mapping.


## 16. Integration and polish (step 5, 2026-09-27)

**Build it.** From the repo root with either venv: `python -B showcase/gen/bundle.py --strict-page` (0 errors, 0
warnings). It writes `docs/showcase/` (index.html 0.45 MB + 17 data files, 39.96 MB in all, the largest
`models-426.js` at 11.07 MB) and mirrors it byte-identical to `scratchpad/showcase-new/` for publishing. Then
`python -B showcase/gen/sc_contract.py --bundle docs/showcase` prints OK and `bundle.py --check-only` 0 / 0.
**Publish with the `downloads` capability** (the files card saves zips through it); the main session does that.

**Cards.** All 19 fragments are in: `mech-a-*`, `mech-b-*` and `end-*` were renamed to `cards/<id>.*`. The tour order
is `sc_contract.CARDS`: glance, keys, strip, sidekeys, joint, usb, reset, screen, detent, ribbons, battery, boardprep
(3.68), zstack, closing, edges, compare, assembly, checks, files. On a standard build the strip card is "away"
(heading + "Switch to it"); opening it switches to the light-strip build with the toast and Undo.

**Data and contract fixes.**
- 4.26 `cards.compare.attribution` and the `compare` preset caption now credit Zorian22 for the **X4 reference model**
  (thing:7287950, CC BY-NC-SA) and the retro case to its author's print files, as `compare.py` says; the same wording
  is in `sc_contract` (NODE_RULES, validator message, sample), section 3 and the page footer.
- 4.26 `pin` drawing is cut 0.55 mm off the H2 post's slot (as 3.68), so the snap fingers show; `notes.hole_y` added.
- 4.26 `models-426.js` is written with `write_bytes` (Windows `write_text` added a CR, so `js_bytes` was one short).
- `validate_manifest` allows the builds to differ in `panel_*` / `ribbon_*` / `strip_*` only; the bundler's waiver no
  longer fires. Self-test passes in both venvs.
- The 4.26 adapter was rerun (full, then `--reuse`): ALL OK, the project's `out/` unchanged (201 files).

**API added in this step** (details in section 5): `ctx.listen`, `ctx.cleanup`; `SC.Drawing(...).bbox(id)`;
`SC.A(d).label(..., {fit: true})`; `SC.timing`; data-play opens its card; a switch closes an open card that is now
away. Viewer: `press('kind:<kind>' | [ids])`, `release(src)` + the `released` event, `pressState(id)`,
`explodeStep(k, f)`, `look()` / `clearLook()`, `tween(cam, tgt, up, {fit, animate})`; step 0 is now emitted (the
first group alone, fully apart) and Play's end emits `order.length` without a `-1` before it; a chip turned off only
because a build lacked its group comes back on when the group is available again (strip3d's own workaround removed);
a pressed crank is stored as its stroke fraction, so a variant swap re-derives the angle for the new pair.
- Card steps' wishes **not** done: `userData.noAO` in the GTAO pass (strip3d's cone trick stays), `SC.A.labelAt` /
  `Drawing.pointIn` / `opts.pad` (the mech-b cards keep `P`, `labAt`, `widen`), `bundle.py --page DIR`. Cards keep
  their own `fitA` helpers; new code should use `{fit: true}`.

**Cross-card fixes.** Undo back to standard left `m=strip` in the hash with the card away: the card now closes. The
strip card restarts at step 1 after it is left (a size switch while open keeps the step). The 3.68 strip neck label
ran off its drawing (now `{fit: true}`). The zstack card's two totals overlapped when the other size is beside it. The
side keys, reset and USB sliders follow `released`. Masthead facts are typeset (68.2 &times; 125.0, cm&sup3;) and stay
in two columns on a phone (the one-column masthead pushed the stage 1100 px down).

**Load timing** (headless, local server, 1400 x 900): first data bound and every card rendered at 1.6-2.4 s
(`SC.timing.ready`; 3.3 s with two headless runs side by side), the stage mounted at 3.6-5.0 s (`viewer`, waits for three.js from jsdelivr and the 5.8-6.0 MB of
first-paint models); a full render of all cards takes 65-180 ms (`cards_ms`), 480 ms once on a size + build switch
under load. Model files are fetched at low priority so the data file (0.15-0.2 MB) is not queued behind them.

**Checked** (`scratchpad/showcase-build/s5/`: `t5.js` = `window.T5` on top of `keys_t.js` (KT) and `strip/strip_t.js`
(ST); `plan5.py <tag> <theme> <func|cards> [reduce] [stageshots] [combos=..] [only=..] [segh=] [segs=]`;
`runall.sh`; `summ.py` summarises a run; `blank.py` lists flat screenshots; `cat.py` / `strips.py` make sheets).
Server: `keys_serve.py showcase-new 8957` (stopped afterwards). Runs, each over 426 std, 426 ls, 368 std, 368 ls:
- `dA` 1400 x 900 light and `dF` 1400 x 900 dark, functional with stage shots; `mB` 390 x 844 dark with reduced motion,
  functional with stage shots; `cC` 1400 x 3000 dark, `cD` and `cE` 390 x 844 light: card shots.
- Every card entered once (opened, its first Show in 3D run): 0 `.k-missing`, 0 `.card-err`, no `?` / NaN /
  undefined, no card wider than itself, no annotation outside its drawing (after the neck fix), every drawing
  labelled, every button / input named, every chip and segmented toggle carries `aria-pressed`, no duplicate ids.
- The keys card at rest / click / bottom, T in every combination and M on both standard builds: angle, key travel,
  plunger and state exact (T 0 / 4.8133 / 8.619 deg, key 0.4104 / 0.726 mm; M 4.8323 / 8.6798 deg, 0.412 / 0.731 mm),
  the drawing's nose on the plunger face and key on the crown to 1e-4, and the stage equal to the card.
- The strip card: every step on both sizes (9 on 4.26, 10 on 3.68) lands on its fold, cut, chips and tape; LED D4 in
  3D equals the `strip_led` drawing to 0.003 mm; entering from standard gives ls + toast + Undo, Undo gives standard
  with the card closed and away.
- Play: step events 0, 1, ... in order, then `order.length`, no `-1`; with reduced motion one jump (0, then the end).
- The new viewer API (explodeStep 0 and 3, look / clearLook, `kind:flexure` presses the 5 side keys, `released`).
- No horizontal scroll at 390 or 1400; 0 page errors or console warnings in every run.

**Harness notes.** Headless Chrome paints only the window, so tall cards are shot in segments (`T5.seg`, an overlay
`#seg`). On a phone a Show in 3D smooth-scrolls to the stage, so shots taken right after it miss the card (the card
runs no longer click Show). A bash heredoc turned a typed `\b` into a backspace once: after patching with Python
from bash, scan for control characters.

## 17. Review fixes (fix1, 2026-09-27)

The five confirmed problems from the showcase review, and the key drawing on a phone:
1. **Measure before printing** is back: `cards.checks.measure` (section 4, cards), written by `adapt_426.measure_list`
   (Rev K's block, with the microSD socket now answered by the real MEM2075 part, plus the TS365ZJ, the drag and gate
   coupons and the rod; since test 2 the chin coupon replaces the drag coupon) and `adapt_368.measure_block` (the 503035 at most 5.2 x 31.7 x 37.9 mm, the pack against J7, the 0.87 panel,
   the FPC's R0.65 and contact side, the tuning and gate coupons per build, the rod; since test 2 the chin and gate coupons). `ls` adds the strip's stack. The checks card
   renders it under its own heading below the check groups.
2. **One switch geometry**: `sc_contract.SWITCH_GEOM` (section 4, keys). The 4.26 now draws the nominal TS365 plunger
   (Z -3.25..-1.75; the worst case is `nub_z_worst`), in the data, in `sw_T_nub` and in the `key` drawing's `nub_T`.
   The 3.68's MJTP1117 `housing_yz` is the spec envelope `[-0.68, -4.49, 6.0, -0.19]`, not the STEP probe's end.
3. **One force-table shape** (`sc_contract.force_table`, validated; `keys.js forceRows` reads only it) and **one zip
   layout** (`shared/`, `standard/`, `light-strip/`, `dummy/`) in both sizes.
4. **Unique download names**: groups end in `-only.zip`.
5. **3.68 display nodes and panel labels**: `manifest.sizes.S.display_nodes` now lists every display node a build
   shows, core or per build (3.68: `panel_epd`, `ribbon_main` in both), checked against each adapter's
   `display_nodes`; the 3.68 panel label is `3.68" EPD (bare)` / `3.68" EPD + light strip`.

The key drawing opens at scroll 0 on a phone: the left labels read in full and the rest is a sideways scroll.

## 18. The 4.26 chinless build (`cl`, 2026-10-04)

The 4.26 has a third build, `cl` (Chinless, "touch, no bottom keys"): the standard build's FT01C panel, its own tub
and lid, no bottom keys, cranks, rod or gate, and a board with SW9, SW8, SW3 and SW2 not fitted; 68.18 x 117.4 x 12.7.
- **Contract.** `BUILDS` stays `('std', 'ls')` (every size has both); `EXTRA_BUILDS = {'426': ('cl',)}`,
  `builds_of(S)`, `ALL_BUILDS`, `KEYLESS = ('cl',)`. A keyless data file has `keys: null`, `meta.bottom_keys: []`,
  no crank controls and no `key` drawing (`DRAWINGS_NOT`), and `meta.absent_nodes`: the core nodes it leaves out
  (the 18 bottom-key nodes: `key_*`, `crank_M/T`, `rod`, `gate`, `sw_T_*`, `swbody_*`, the bottom `nub_*`). An extra
  build's file may carry a core node to replace it (`build-426-cl.json`: `tub`, `lid`, and the FT01C's `panel_*` /
  `ribbon_*`). The `keys` and `rod` chips are `builds: ['std', 'ls']`. Manifest: `sizes.S.builds`,
  `sizes.S.build_diff_by {cl}`, `builds.cl.note`, `nodes.426.absent.cl`, `load.426.{build,data}.cl`.
- **Cards.** `away_builds {B: B2}` + `away_note` (CARDS): on B the card shows its heading and "Not in this build",
  and its button switches to B2 (the keys card on `cl` -> `std`, with a toast and Undo). Markup takes `data-not="cl"`
  (hidden when any token is the size or the build; the bundler skips those bindings there). The closing, assembly,
  checks, edges, joint, glance and files cards handle `cl`; the strip card is away as on `std`.
- **Downloads.** The zip gains `chinless/` (`tub-chinless.stl`, `lid-chinless.stl`, files `builds: ['cl']`); group
  order `sc_contract.download_groups(S)`. Shared files the chinless build does not use carry `skip_builds: ['cl']`,
  so its "only this build" download is `chinless/` + `shared/midplate.*` + the dummy + README. The zip has the
  standard build's PCBA dummy only (out/chinless/pcba-dummy.stl is left out: the 16 MB file limit).
- **Viewer.** `addNodes(core, skip)` skips `meta.absent_nodes` and every node the build file carries; `D.keys` null
  is tolerated. **Shell.** The build buttons come from `sizes.S.builds`; a size without the current build falls back
  to `std`; the bottom-key switch selector hides on a keyless build.
- **Sizes (2026-10-04).** `build-426-cl.json` 1.25 MB, `data-426-cl.json` 0.13 MB: first paint 4.26 cl 6.85 MB (std
  6.81), switch to cl 1.39 MB. With the chinless tub's and lid's STEP files in the zip, `models-426.js` was 16.64 MB
  (16,640,346 bytes): it passed the bundler's check of then, 16 MiB (16,777,216), but it is over the 16,000,000 bytes
  the bundler checks since 2026-10-08 (`sc_contract.LIMITS`, the host's 16 MB per file read as decimal). Those two
  STEP files were left out of the zip on 2026-10-04 itself (`sc_contract.ZIP_NOT_SHOWN`; they stay in `print/4.26/`),
  which made `models-426.js` 14.9 MB; a bigger 4.26 print file needs the zip split or more STEP files left out
  (section 19 also leaves out the light-strip chinless tub's STEP).

## 19. The 4.26 light-strip chinless build (`lc`, 2026-10-07)

The 4.26 has a fourth build, `lc` (Light-strip chinless, "no touch, no bottom keys"): the light-strip build's plain
GDEY0426T82 with the Silkscreen light strip, its own tub, the chinless lid (`lid-chinless`, the same file as `cl`'s),
no bottom keys, and a board with SW9, SW8, SW3 and SW2 not fitted; 68.18 x 117.4 x 12.7. It is print build 4 of the
case project (plate 5 of the author's CC2 plate file). The case project builds 32 configurations in all; the side-key layouts and
the no-dev-header cases are not showcase builds (the files card names them and where they are described).
- **Contract.** `EXTRA_BUILDS = {'426': ('cl', 'lc')}`, `KEYLESS = ('cl', 'lc')`, `STRIP_BUILDS = ('ls', 'lc')`,
  `BUILD_DIRS.lc = 'light-strip-chinless'`, `ZIP_DIRS.lc = 'light-strip-chinless/'`, `DRAWINGS_BUILD.lc =
  ('strip_led',)`, `DRAWINGS_NOT.lc = ('key',)`. `BUILD_TOKENS` (also `manifest.builds.B.tokens`): `std` std; `ls`
  ls; `cl` cl, std (it shows the FT01C's `426 std` texts, which the chinless build did not show before); `lc` lc, ls,
  cl. So existing markup works unchanged: `data-only="ls"` texts show on `lc`, `data-only="cl"` / `data-not="cl"` act
  on it. `sc_contract.tokens_match` is the rule; the bundler checks bindings with it.
- **Cards.** The keys card is away on `lc` (to `ls`). The strip card has `home_builds: ['ls', 'lc']`: on `lc` it works
  in place, with `lc`'s steps (no "trim SW9's lead", no bottom-keys step), without the SW9 row of the Kapton table,
  the keyed rows of the build table, and `cards.strip.diff_note` (against the chinless build). `strip3d.js` is
  active on any build with the `ls` token and hides the Kapton over SW9 on a keyless build. Glance takes
  `cards.glance.against` when the data gives it. The files card tags a build's group "this build" when every file is
  this build's and "other build" when none is.
- **Downloads.** The zip gains `light-strip-chinless/tub-light-strip-chinless.stl` (`builds: ['lc']`); the chinless
  lid in `chinless/` lists `builds: ['cl', 'lc']` (a build group's files list that build first and may list others
  that print them). Shared files neither chinless build uses carry `skip_builds: ['cl', 'lc']`.
  `tub-light-strip-chinless.step` stays out (`ZIP_NOT_SHOWN`): with it `models-426.js` would be about 16.3 MB.
- **Sizes (2026-10-07).** `models-426.js` 15,328,502 bytes (published limit 16,000,000, `sc_contract.LIMITS`
  `file_bytes`), `build-426-lc.json` 1.17 MB, `data-426-lc.json` 0.15 MB; the bundle 48.84 MB (limit 64,000,000,
  `version_bytes`); first paint 4.26 lc 6.78 MB, switch to lc 1.31 MB.

## 20. Four screws on the 3.68, socket heads on both (2026-10-13)

The 3.68 took a fourth screw and moved its bottom pair (the case project's params `SCREWS`, `CORNER_SCREWS`,
`TOP_LEFT_SCREW`, `M2_CB_DEPTH {'corner', 'top'}`): the bottom pair sit in the chin's corners below the rod, through
posts in the lid into solid corner blocks in the tub; the top-left corner has a screw built as the top one; H3 and H4
keep the lid's posts, now with a pin into the board's hole (`H34_PIN`) and no screw. Ian's screws are socket head caps
(ISO 4762, dk 3.8, k 2.0); a pan head (ISO 7045) also fits both cases. The 4.26's counterbores went from 1.8 to 2.0
deep (`M2_HEAD_CB_DEPTH`), so a socket head's top is flush with its back.
- **Meshes.** `sc_lib.socket_head_cq` (a hex socket in the head's back face) replaces `pan_head_cq` in both adapters,
  `length=SCREW_L` (8 on the 3.68, 10 on the 4.26). The 3.68's nodes are `screw_bottom_left`, `screw_bottom_right`,
  `screw_top` and `screw_top_left` (`adapt_368.SCREW_NODES`); the 4.26's are unchanged. The `screws` group still
  matches `screw_*`.
- **`cards.closing`** (both sizes): `screws` is `'M2 x L ISO 4762 socket head'`; `head {iso, kind, dk, k, also,
  below_back {id: mm}}` (how far a socket head's top sits below the back, as modelled: 0.0 on the 4.26, 1.6 at the
  3.68's corners and 0.6 at its top two); `screw_list [{id, node, label, at, seat_z, cb_depth, through_board}]`;
  `cb_depth {bottom, top}`; `screw_len`, `pilot`. The 3.68 adds `pinned` and `pin_d`; its `seat_z` is keyed by
  screw id.
- **The `clamp` drawing** keeps its name (`DRAWINGS_COMMON`). On the 4.26 it still cuts the H3 screw along y. On the
  3.68 it cuts the bottom-left corner screw along x (u = Y): the chin wall, the corner block, the lid post, the screw
  and the rod above it; `notes {ref: 'bottom-left', u, mirror, rod_axis}`. The 3.68's `clamp` and `top` drawings start
  0.5 below the back face (`ZW` still starts at -7.6, from before `LID_DROP` put the back at -8.235), so the heads show
  whole.
- **The `close` preset** on the 3.68 cuts at the corner screws' y (-5.25) instead of 3.0.
- **`cards.joint.joint.screws`** (3.68): `[[id, x, y]]`; the joint card's plan draws every screw and labels the
  top-left one.
- **Cards.** The closing card counts the screws from `screw_list` (title, thesis, the screws paragraph, the numbers),
  names the head from `screws` and `head`, and annotates the 3.68's clamp drawing as a corner screw (`notes.u`). Its
  H3/H4 clamp texts are `data-only="426"`, with `data-only="368"` texts for the corner screws and the top-left one.
  The detent card's "the two bottom screws go through the board" sentence is `data-only="426"`. The assembly card
  reads the count from the `hardware` fact (`4 x M2x8` on the 3.68).
