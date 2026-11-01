# Slide-on cover (round 2, 2026-11-01)

> [!IMPORTANT]
> AI-assisted, not the official Silkscreen enclosure: see the notice at the top of the
> [main README](../../README.md) and https://silkscreenreader.com/ai.

> [!WARNING]
> **Only one piece of this has been printed:** the first round's fit coupon A (the channel, the lip and the prong with its ridge), which
> Ian found fine. **No whole cover has been printed**, and nothing here is tested or proven. The cover is checked in CAD against the
> real case STLs and sliced with the OrcaSlicer CLI; the forces are beam estimates. The plate files in `print/` are **temporary** (one
> cover per plate) until the covers go into the case plate files.

A TI-84 style reversible cover, one printed part. It goes over the screen to carry the reader, and over the back while you read.
It slides on **sideways, along the case's width** (X), gripping the case's top and bottom end walls. It does not touch the
case's long sides, and **the case itself does not change**, so it fits every case already printed.

**Round 2 (Ian, 2026-11-01).** The cover carries the Silkscreen icon and wordmark engraved on its outer face; every edge you can touch is
rounded (no sharp edges, a short list of justified exceptions below); it goes on **any of four ways**; and its long sides curve inward over
the side keys. What did not change is the working geometry Ian printed as coupon A: the channel, the lip, the prong's thickness profile,
length and root, the ridge's height and ramps (the snap figures are compared below).

## Which cover fits which build

| Cover (`print/cover/`) | Fits | Plate | Size (mm) | Print time, generic / CC2 | PLA |
|---|---|---|---|---|---|
| `4.26/cover-keyed` | the 16 4.26 builds with bottom keys: `standard` and `light-strip`, each with all four side keys, the left pair, the right pair or the upper pair, with or without J6 | 1 | 72.1 x 128.8 x 17.4 | 1 h 03 / 31 min | 18.1 g (17.9 g CC2) |
| `4.26/cover-chinless` | the 16 chinless builds: `chinless` and `light-strip-chinless`, every layout | 2 | 72.1 x 121.2 x 16.4 | 59 min / 29 min | 16.6 g (16.5 g CC2) |
| `3.68/cover-standard` | the 3.68 standard build | 3 | 72.1 x 111.8 x 17.8 | 1 h 00 / 30 min | 17.1 g (16.9 g CC2) |

The 4.26 light-strip builds share the standard's envelope, so one cover serves both. The 3.68 light strip is unreleased and has no cover.
Times and grams are the OrcaSlicer 2.4 CLI's for the plate file's presets (generic: Generic PLA, 0.20 mm Standard; CC2: Elegoo CC2 presets).

`print/silkscreen-cover-plates.3mf` (generic OrcaSlicer presets, 220 x 210 bed) holds one plate per cover; Ian's CC2 twin is
`print/cc2-local/silkscreen-cover-plates.3mf` (git-ignored). **Temporary:** the covers are not in the case plate files or the
per-configuration projects yet. Every object has wall_loops 4 (the channel wall is four 0.4 lines); nothing else differs from the stock
process, and no supports (below). The coupons are gone (coupon A confirmed the fit; the channel section is unchanged).

**Two-colour logo.** Each cover carries its two logo bodies as modifier parts with no filament, named like the lid's ("logo wordmark: ...",
"logo icon: ..."): the switch is OFF and the cover slices as one colour with the engraving empty. To switch it on, do what the lid's switch asks
(`print/README.md`, "Two-colour logo": one logo part at a time, Change type -> Part, then Set Filament -> 2); the logo is the cover's first two
layers (the outer face is on the bed), so you need a printer that changes filament by itself. `inlay_check.py` does that to a copy of the plate
file and reads the G-code back.

## Using it

The cover is **symmetric about its own mid-length and mid-plane**, so there are four legal poses (`check.py` checks all four, on every
build). In each the plate's outer face (the one with the logo) faces away from the case.

| Pose | How | Stop side |
|---|---|---|
| front | on the screen | right: the power-key side (SW1, SW4, SW10 and the USB-C) |
| back | turned over about the long axis (like a page) | left (SW5, SW7) |
| front, turned | on the screen, turned 180 degrees in the plane: top and bottom swapped, it goes on from the other side | left |
| back, turned | on the back, turned 180 degrees in the plane | right |

Put the cover's open end on the case edge on the **side opposite the stop**, so its two channels slip over the case's top and bottom end
faces, and push toward the stop until the stop pieces (the two corner pieces, with nothing between them) meet the case's side. The ridges on the
prongs rub along the end faces (a light drag); at the end they drop into the case's rounded corners with a gentle click, and the cover is held.
Taking it off: pull it away from the stop with a firm pull (about 3 N at the cover, estimated). It cannot be lifted straight off: the lips hook
the case's end edges.

**The logo reads upside down in the two turned poses** (it is engraved once, on one end of the plate). In every pose it faces away from the
case. With the cover on the **back** (the un-turned back pose) it sits exactly over the case's own back logo and reads the same way.

**Keys.** The page keys and the power key can be pressed in every pose: the cover has no wall along the long sides except the two corner
pieces and their short extensions (4.7 mm on the 4.26, 4.2 on the 3.68), cut back so that no key pad of any layout in any pose touches
them, and both long sides **curve inward** over the side keys and the power key (the scallop below). The bottom keys are covered with the
cover on the front, in both front poses (the plate's slot over them never touches a cap: 0.25 clear with the plate on the face); on the back
they are free. J6 (the developer header) is covered by the end wall either way: take the cover off to use it (see "What it does not do").

![The cover at home on the front](../../docs/images/cover-front.png)
![The cover at home on the back](../../docs/images/cover-back.png)
![The four poses](../../docs/images/cover-poses.png)
![A turned pose, part way on](../../docs/images/cover-turned.png)

## How it works

Drawn on the case, in its own axes (`model.py`; Z up toward the screen, cover on the front at home):

- **Plate** over the face, inner face 0.35 off it. 2.8 mm thick (keyed), 1.8 (chinless), 3.0 (3.68): whole layers, and the thickest the
  key slots need (the slot roof is at least 1.2 thick, six layers, so the bed chamfer and the logo's engraving fit). The outer face prints on
  the bed. Over the screen, and over a mirrored area at the other end (the cover turns end for end), the plate is relieved; the relief and a
  **key slot at each end** are one cavity of one depth, running out through the leading edge (the plate passes over the caps on its way, and
  either end of the plate may land over the bottom keys).
- **Two end channels**, one at each end: a wall 0.30 off the end face, 1.6 thick, and a **lip** that hooks the opposite face's end
  edge, as in coupon A (47-degree face following the back round at 0.45 normal clearance; the tip is now a half round of 0.6).
- **Stop side**: the channels turn the corner on the case's R5 plan arc (inner radius 5.2) and run on 4.7 mm along the long side at
  full height; **no wall between them** (the round-1 stop wall had gaps for each layout's keys, and it could not serve the turned poses).
  The extension is as long as stays clear of every pad's y range **and its mirror about mid-length**, after a 3 mm finger margin and the ease.
- **Scallop.** Both long sides of the plate curve inward between the corner pieces: a quintic ease (tangent- and curvature-continuous,
  6 mm in and 6 mm out) over the union of every pad's y range and its mirror, plus the 3 mm margin. One curve where the zones are close
  (the 3.68's). Inset: **2.4 mm** inside the case's side face on the 4.26, **3.0 mm** on the 3.68, limited by the screen: with the cover on
  the front the plate still reaches 2.0 mm or more past the screen opening on each side (measured from the tub STL).
- **Retention: a prong in each channel at the open end**, a free cantilever 0.8 mm thick (two lines, thickening to the full wall over 4 mm
  at its root), standing on the bed: no overhang. Round 2 moves the thinning to its **inner** side, so the outside of the cover is one
  smooth surface; the ridge is raised to match. The **ridge** (ramps of 18 and 45 degrees) rides the flat end face with the prong deflected
  0.7 mm while sliding; at home the case's R5 corner arc falls away under it and the prong springs back to within 0.15 of free. Pulling the
  cover off, the ridge climbs the arc again.
- **Why a tall ridge.** J6's opening is in the top end wall at x 42.75 to 59.1, z -5.5 to +0.25. A ridge centred on the case's
  mid-plane keeps at least 2.4 mm of its contact on intact wall above J6 in all four poses, so the prong never drops into it.

![The snap corner at home, and the prong's deflection along the slide](../../docs/images/cover-snap-corner.png)

### Edges and rounds

45-degree **chamfer 0.6** round the whole outer-face perimeter (it is also the printed bed's elephant-foot relief); every other exposed edge a
**fillet of 0.5** or more (wall top, lip, corner pieces, plate edges, the notches beside the prongs; some slot-mouth fillets are 0.2 to 0.3,
below); the open-end plan corners **R3** (R1.5 where the key slot leaves through the leading edge, R1 at the notch's end); the prong's free
end is a full round in plan and at its top.

![The open end and the prong, 27bbdaf next to round 2](../../docs/images/cover-open-end.png)
![The scallop with a side key and a fingertip on the back](../../docs/images/cover-scallop.png)
![The logo face as printed, with the two-colour bodies](../../docs/images/cover-logo.png)

`edges.py` is the sharp-edge check: every convex mesh edge of the STL that turns more than 50 degrees, grouped by place, and whether a hand
can reach it (the two face normals traced out from the edge against the cover and the case at home). On **27bbdaf's cover** (coupon A's
geometry, kept as `ref/old-27bbdaf-keyed.stl`) it finds 291 convex edge segments turning more than 50 degrees, **275 of them touchable**, 1437 mm of edge (226 segments on the wall, lip and corner pieces, 28 on the prong and ridge, 15 on the plate's edges, 22 elsewhere). The round-2 results are in "Sharp-edge result".

## The numbers

| | design | notes |
|---|---|---|
| channel wall to the end face | 0.30 per side | as coupon A (Ian printed it: "feels fine") |
| stop pieces to the long side | 0.30 drawn; closed (touching) at home | the prongs preload the cover into them |
| plate to the face, lip flat to the back face | 0.35 each (G = 0.70 total; 0.695 on the 3.68) | whole layers |
| prong | 0.8 thick, 11.0 from its root to the ridge's centre | beam model: 4.3 N/mm (soft bound) to 7.8 N/mm, E 3000 MPa |
| ridge | stands 0.7 inside the end face on the flat | 0.15 left at home; strain at the root 0.9 % |
| forces, one prong (beam estimates) | sliding drag 0.9 N; push on, peak 1.4 N; pull off, peak 1.4 N (0.9 to 4.0 over E 2500-3500, both stiffness bounds, mu 0.2-0.4) | two prongs: about 3 N to take it off |

**Snap, round 1 (27bbdaf, coupon A's geometry) against round 2**, through the same ray casts on the real standard 4.26 end faces
(`check.py --snap`): the prong's thickness profile along its length is equal to within 0.11 mm (0.80 free span blending to 1.60 at the root; the only differences are the full-round tip and the root blend); deflection 0.70 flat and 0.70 peak in both; preload 0.15 against 0.14 mm; one prong, nominal (E 3000 MPa, soft bound, mu 0.3): pull-off peak 1.38 N against 1.41 N (-1.9 %), push-on peak 1.38 against 1.40 N (-0.8 %), sliding drag 0.90 N both, strain 0.89 % both; over E 2500 to 3500 MPa, both stiffness bounds and mu 0.2 to 0.4 the pull-off peak is 0.92 to 3.92 N against 0.94 to 3.97 N. All within 2 %, inside the 10 % asked. The ridge's rounding took 0.03 mm off the home preload, so the ridge sits 0.05 mm further along the cover
(`ridge_trim`).

## What was checked, and how

`check.py` (run: `python -B check.py`) works on the **real STLs** of every build the covers serve: tub, lid with its side keys and
the bottom-key caps from `case-426/out/<build>/` and `case-368/out/standard/`, 33 builds, in **all four poses**, with manifold3d (overlap
volumes, least distances) and vtk ray casts of the end faces and of the cover's own ridge. **2346 rows over the 33 builds, 0 failing.** (The full run had two failing rows on the 3.68: the ridge's undeflected tip, which stands 0.7 inside the end wall, came 0.15 from a key cap's stem inside the case; the cap-clearance row now measures the rigid frame, the prong deflects away from the wall, and the 3.68 re-run passes. The full run was on the prong foot chamfered 0.3; the foot is now 0.1 (see Print), so one build per group was re-run on the final STLs: 216 rows, 0 failing.)
- **Home, every pose**: the frame has no overlap with the case, least distance 0.30 with the stop 0.5 off, none with the cover moved a
  play-width in Z or Y. The ridge's overlap at home (0.64 mm3) is the snap, not a collision.
- **Slide, every pose**: the frame swept along the whole path, cover entirely off the case to home, 1 mm steps: zero overlap.
- **Ridge on the real end faces**, read through the cover's own ridge mesh: deflection 0.70 flat along the straight face (spread 0.00 at
  the extremes of the Z play), peak 0.70, preload 0.15, at both ends in all four poses: nothing catches in J6.
- **Access**: the USB-C recess plus 30 mm of plug room is clear in every pose; the screen window is clear with the cover on the back; the
  plate clears the bottom-key caps by 0.25 in both front poses at home and along the path; the plate stays 2.0 mm or more past the screen
  opening (4.26: 2.01 to 3.2 mm at the left and 2.08 to 2.78 at the right over the 32 builds; 3.68: 2.8 and 4.3).
- **Fingertip**: an r 7 mm sphere touching each pad face's centre, swept in from the side along the face's normal, is clear of the cover in
  every pose, every pad, every build: least clearance 4.82 mm on the 4.26, 6.18 on the 3.68. For comparison, the same approach to a cover without the scallop (`out/design/keyed-noscallop.stl`) clears by 2.71 mm: the scallop gains 2.1 mm.
- **Logo**: with the cover on the back, its engraving lies over the case's own logo (area overlap with the lid STL's section, 1.000 for the icon and for the wordmark, centroid offset 0.00 mm, in
  every build) and the plate behind the engraving is solid for at least 0.8 (0.8 to 1.0 on the 3.68) mm below its floor everywhere (a slab test: the engraving never
  breaks into the relief or a key slot; the need is 0.6).
- **It can fail**: the wrong covers must fail, and do. A key slot at one end only fails in the front-turned pose (the plate meets the caps: 122 mm3 at home on the standard build). A 16 mm corner extension meets a pad (all 16 keyed builds, the two poses with the stop on the right, 8.75 mm3 each: 32 failures). The ridge moved into J6's band fails (deflection 0.00 to 0.70 along the straight face, spread 0.70 against the 0.12 limit). 27bbdaf's cover fails the sharp-edge scan (275 touchable segments). `check.py --wrong`.
- **Print**: `printcheck.py` reads every layer of the STLs: nothing hangs more than 0.45 mm past the layer below. `slice_read.py` slices
  the plate file with the OrcaSlicer CLI (never a GUI), generic and CC2, and reads the G-code back: **no support extrusion on any plate**; the lip, the prong and the ridge lie where the mesh puts them to 0.02 mm on every layer they stand in, including the prong's first layer on the CC2 (a 0.3 chamfer on the prong's foot left a first-layer line 0.4 wide, which the CC2's classic walls and EFC 0.1 dropped; the foot chamfer is 0.1 so the line is laid); the only bridges are one layer (z 0.6, or 0.4 and 0.6 on the 3.68) over the engraving's 0.2 to 0.4 deep voids, where a line hangs at most 0.77 mm past the layer below (the lid's own logos do the same). Generic presets: 1 h 03 / 59 min / 1 h 00 and 18.1 / 16.6 / 17.1 g; CC2: 31 / 29 / 30 min and 17.9 / 16.5 / 16.9 g (keyed, chinless, 3.68). `inlay_check.py` switches the logo on in a copy of the plate file: filament 2 is laid only inside the two logo boxes on layers 0.2 and 0.4 (0.10 g on the keyed plate) and filament 1 uses 18.09 g against 18.10 g with the switch off.

### Sharp-edge result

`python -B edges.py keyed|chinless|x3` (convex mesh edges turning more than 50 degrees, grouped; "touchable" = a face normal escapes), on the STLs as built:

| Cover | Logo engraving rims | Prong block's end step | Key-slot roof edge | Other |
|---|---|---|---|---|
| 4.26 keyed | 1020 segments, 589 mm | 10 segments, 5.3 mm (up to 90 degrees) | 2 x 4.1 mm at 90 degrees; 2 x 0.5 mm of faceted slot-mouth corner (up to 67 degrees) | none |
| 4.26 chinless | 1020 segments, 589 mm | 6 segments, 2.3 mm | none (no bottom keys) | 15.0 mm at 51 degrees on the plate's inner-face fillet, **not touchable** (faces the case); 270 sub-0.06 mm facets at the scallop's seams, a mesher fan (the B-rep fillet is tangent there), not counted |
| 3.68 | 1000 segments, 542 mm | 6 segments, 2.3 mm | 2 x 4.4 mm at 90 degrees | none |

Everything else has no convex edge over 50 degrees: the outer-face perimeter chamfer, the wall tops, lips, corner pieces and their extensions, the prong (free end,
top and flanks), the ridge, the plate's edges, the notches, the relief and the slot mouths (the latter at 0.2 to 0.3 where 0.5 would not take). What is left, and why:
- **Logo engraving rims**: the case's own treatment of the same logos (0.4 deep, strokes down to 0.36 wide: they cannot take a fillet).
- **Prong block's end step** (u = 10.2 at each prong): the prong's foot is chamfered 0.1 where the plate's outer face has 0.6; the prong block ends there, leaving a
  step 0.5 high and 1 to 2 mm long. A 0.3 chamfer on the 0.8 mm prong left a first layer 0.4 wide that the CC2 does not lay (see Print), so the foot stays at 0.1.
- **Key-slot roof edge** (keyed and 3.68): where each slot's roof leaves through the plate's leading face, a 90-degree edge 4.1 mm (4.4 on the 3.68) long, reachable only from the slot's
  mouth. OpenCascade could not fillet it (`build_cover.py` notes: "slot exit: 18 edges left sharp") and a 0.5 mm prism bevel cut across it left mesher artefacts, so it is open.
  This is the one place Ian's "no sharp edges" is not met on a touchable face beyond the logo; it is on the open end's two slots, under the leading edge.
- **Mesher fans**: tiny facets the STL writer puts at some fillet seams; zero-width slivers, no geometry.

27bbdaf's cover, the same scan: 275 touchable segments.

## What it does not do

- **J6.** A window in the end wall for J6 is not cut: take the cover off to use the developer header. The USB-C is clear in every pose.
- **Z clamp.** None. The plate and the lip leave 0.70 mm of Z play and the channel walls 0.60 of Y play; the prongs take up the Y and X
  play at home, not Z.
- **Not proven:** the as-printed fit of a whole cover, the forces, the long-term strain in PLA, warping of the big plate, and the two-colour
  switch on a real printer (the CLI read-back is the only test).

## Rebuild

From `enclosures/cover`, with the 4.26 Python of `CLAUDE.local.md` (cadquery, trimesh, manifold3d, vtk; it also reads the 3.68's params):
```
python -B build_cover.py        # print/cover/4.26 and 3.68 (.stl, .step, inlay bodies) and out/design/ (what check.py reads)
python -B check.py              # 33 builds, four poses (about 30 minutes); --group keyed|chinless|x3, --builds a,b; --wrong; --snap
python -B edges.py [keyed|chinless|x3|old]   # the sharp-edge scan
python -B printcheck.py         # the layer audit of the STLs
python -B make_cover_plates.py  # print/silkscreen-cover-plates.3mf; --printer cc2 for print/cc2-local/
python -B slice_read.py         # slice it with the OrcaSlicer CLI and read the G-code back; --printer cc2
python -B inlay_check.py        # the two-colour switch switched on, sliced, read back
python -B pictures.py           # docs/images/cover-*.png
```
`case_info.py` reads each case's envelope, pads, window and logos from `params.py` / `logo.py` (imported in a subprocess with
`SILKSCREEN_VARIANT` set) and from the built STLs; run the case builds first, and delete `out/case_info.json` after a case change. Nothing
under `case-426/src` or `case-368/src` is edited. The cover files are in `print/cover/`, not `print/4.26` or `print/3.68`: both case builds
delete any file in their size folder that they did not make.

Files: `model.py` (the geometry and every number), `case_info.py`, `logo_dump.py`, `build_cover.py`, `check.py`, `edges.py`, `snap.py` (force and
strain estimates), `printcheck.py`, `make_cover_plates.py`, `slice_read.py`, `inlay_check.py`, `pictures.py`, `render.py`, `raycast.py`,
`variants_list.py`.
