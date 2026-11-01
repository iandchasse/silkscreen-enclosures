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

**Round 2 (Ian, 2026-11-01), two phases.** Phase 1: the cover carries the Silkscreen icon and wordmark engraved on its outer face; every edge
you can touch is rounded; it goes on **any of four ways**; and its long sides curve inward over the side keys. Phase 2: the plate is **solid over
the screen** (no relief), the key slots' roof edges are flared away, **two engraved border lines** run round the outer face (grip, and a
book-cover look), the snap tab's end is **rounded down in side view** and the slit between the tab and the plate is **one uniform slit** that
ends in a round end. What did not change is the working geometry Ian printed as coupon A: the channel, the lip, the tab's thickness
profile, length and root, the ridge's height and ramps (the snap figures are compared below). The cover stays inside phase 1's footprint
(72.0 mm wide, the same length: the tab does not stand further out).

## Which cover fits which build

| Cover (`print/cover/`) | Fits | Plate | Size (mm) | Print time, generic / CC2 | PLA |
|---|---|---|---|---|---|
| `4.26/cover-keyed` | the 16 4.26 builds with bottom keys: `standard` and `light-strip`, each with all four side keys, the left pair, the right pair or the upper pair, with or without J6 | 1 | 72.0 x 128.8 x 17.4 | 1 h 17 / 40 min | 22.7 g (23.8 g CC2) |
| `4.26/cover-chinless` | the 16 chinless builds: `chinless` and `light-strip-chinless`, every layout | 2 | 72.0 x 121.2 x 17.0 | 1 h 10 / 38 min | 20.8 g (22.0 g CC2) |
| `3.68/cover-standard` | the 3.68 standard build | 3 | 72.0 x 111.8 x 17.8 | 1 h 11 / 38 min | 20.6 g (21.5 g CC2) |

The 4.26 light-strip builds share the standard's envelope, so one cover serves both. The 3.68 light strip is unreleased and has no cover.
Times and grams are the OrcaSlicer 2.4 CLI's for the plate file's presets (generic: Generic PLA, 0.20 mm Standard; CC2: Elegoo CC2 presets). The solid plate and the
border lines cost against phase 1 (generic / CC2): keyed +13.6 min and +4.6 g / +9.2 min and +5.9 g, chinless +11.4 min and +4.3 g / +8.5 min and +5.5 g, 3.68
+11.1 min and +3.5 g / +8.2 min and +4.6 g.

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

- **Plate** over the face, inner face 0.35 off it. **Solid over the screen** (phase 2: no relief). 2.8 mm thick (keyed), 2.4 (chinless: up from 1.8, the
  outer face moves out 0.6), 3.0 (3.68): whole layers, and (keyed, 3.68) the thickest the key slots need (the slot roof is at least 1.2 thick, six
  layers, so the bed chamfer, the logo's engraving and the border lines fit). The outer face prints on the bed. With the relief gone the plate
  is **8 to 13 times stiffer** over the glass and its rest gap to the display glass is **1.37 mm** (1.35 on the 3.68): the glass lies 1.02 below the front face and the plate
  is 0.35 off it. A press has to bend the plate that far before it touches the glass: my estimate (Navier's series for a plate simply supported on
  the screen opening, 59.2 x 96.0 mm (55.1 x 81.0 on the 3.68), uniform thickness, E 3000 MPa, Poisson 0.35, central point load, bending only, the tub's skin as the support
  and the glass itself ignored) is **155 N keyed, 98 N chinless, 225 N on the 3.68** (stiffness 113, 71 and 167 N/mm); phase 1's 1.2 mm over the window gave 8.9 N/mm and 27 / 18 / 37 N by the same method.
  Each end of the plate has a **key slot** that runs out through the leading edge (the plate passes over the caps on its way, and either end of
  the plate may land over the bottom keys); its roof leaves the face in a **45-degree flare of 0.5 mm** (the slot's cutter is flared, not filleted
  afterwards: the roof edge is no longer a 90-degree edge).
- **Two end channels**, one at each end: a wall 0.30 off the end face, 1.6 thick, and a **lip** that hooks the opposite face's end
  edge, as in coupon A (47-degree face following the back round at 0.45 normal clearance; the tip is now a half round of 0.6).
- **Stop side**: the channels turn the corner on the case's R5 plan arc (inner radius 5.2) and run on 4.7 mm along the long side at
  full height; **no wall between them** (the round-1 stop wall had gaps for each layout's keys, and it could not serve the turned poses).
  The extension is as long as stays clear of every pad's y range **and its mirror about mid-length**, after a 3 mm finger margin and the ease.
- **Scallop.** Both long sides of the plate curve inward between the corner pieces: a quintic ease (tangent- and curvature-continuous,
  6 mm in and 6 mm out) over the union of every pad's y range and its mirror, plus the 3 mm margin. One curve where the zones are close
  (the 3.68's). Inset: **2.4 mm** inside the case's side face on the 4.26, **3.0 mm** on the 3.68, limited by the screen: with the cover on
  the front the plate still reaches 2.0 mm or more past the screen opening on each side (measured from the tub STL).
- **Retention: a tab in each channel at the open end**, a free cantilever 0.8 mm thick (two lines, thickening to the full wall over 4 mm
  at its root), standing on the bed: no overhang. The thinning is on its **inner** side, so the outside of the cover is one smooth surface; the ridge
  is raised to match. The **ridge** (ramps of 18 and 45 degrees) rides the flat end face with the tab deflected 0.7 mm while sliding; at home the
  case's R5 corner arc falls away under it and the tab springs back to within 0.15 of free. Pulling the cover off, the ridge climbs the arc again.
- **The tab's end (phase 2).** In side view the tab no longer ends in a tall square end: its outline is a **tongue**: the top edge curves down in an R5
  arc from the full height, the end is an R4 round, and the bottom edge leaves the bed at 45 degrees (it prints without support), all within the ridge's lead-in length (the tip
  is 0.4 mm past the ridge's start, as before: the cover stays inside phase 1's footprint). The ridge's **lead-in is trimmed to the same outline**, so it shrinks in height toward the tip;
  only the flat top keeps the full height that bridges J6 (the contact during the slide is the ridge apex). The push-on still meets the case's corner as a ramp: the angle at
  first touch along the swept path is **18.5 degrees** in all four poses, both ends, at every Z play (27bbdaf: 18.5; the limit is 25).
- **The slit (phase 2).** Between the tab and the plate there is one **uniform slit**, 0.8 wide, that follows the tab's inner face as it thickens toward the root (the plate edge is one
  slit away, the bends rounded to R8) and ends at the root in a **round end** (a semicircle, tangent to both walls). The plate's edge along the slit has the 0.6 chamfer on the outer face and the
  0.5 fillet on the inner face; the tab's bed foot is rounded and **grows into the plate's chamfer over the taper** (one plane, no step), so the slit is the only break.
- **Border lines (phase 2).** Two engraved lines, 0.8 wide (the case's grip groove width) and 0.4 deep (two whole layers), follow the plate's outline 2.5 and 4.5 mm in from its edge (the corners
  and the scallop's curves rounded to R2, round the slit's end), like a book cover's tooled border. They stay 2 mm from the logos (they are 5.5 mm away) and more than 2 mm from the edge,
  so they never cross the slit or the tab, and the plate behind them is solid 0.8 mm (the key slots' roofs included). They are not part of the two-colour switch.
- **Why a tall ridge.** J6's opening is in the top end wall at x 42.75 to 59.1, z -5.5 to +0.25. A ridge centred on the case's
  mid-plane keeps at least 2.4 mm of its contact on intact wall above J6 in all four poses, so the prong never drops into it.

![The snap corner at home, and the prong's deflection along the slide](../../docs/images/cover-snap-corner.png)

### Edges and rounds

45-degree **chamfer 0.6** round the whole outer-face perimeter (it is also the printed bed's elephant-foot relief), along the slit too; every other exposed edge a
**fillet of 0.5** or more (wall top, lip, corner pieces, plate edges; some slot-mouth fillets are 0.2 to 0.3); the open-end plan corners **R3** (R1.5 where the key slot leaves through the leading edge);
the tab's whole side outline a **0.3 round** (the 0.8 plate keeps a 0.2 flat; 0.38 left the first layer's foot 0.55 wide, which the CC2 would not lay).

![The open end corner, phase 1 next to phase 2: the outer face, the side, the case side](../../docs/images/cover-open-end.png)
![The whole outer face: border lines, logo and wordmark](../../docs/images/cover-face.png)
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
| tab (prong) | 0.8 thick, 11.0 from its root to the ridge's centre | beam model: 4.3 N/mm (soft bound) to 7.8 N/mm, E 3000 MPa |
| ridge | stands 0.7 inside the end face on the flat | 0.15 left at home; strain at the root 0.9 %; first touch on the way on at 18.5 degrees (limit 25), all four poses |
| plate over the screen | solid: 2.8 keyed, 2.4 chinless, 3.0 on the 3.68 | rest gap to the glass 1.37 mm (1.35); estimated press to touch it 155 / 98 / 225 N (stiffness 113 / 71 / 167 N/mm; Navier, simply supported on the opening, E 3000, Poisson 0.35, central point load) |
| border lines | 0.8 wide, 0.4 deep, 2.5 and 4.5 mm in from the plate's edge | 5.5 mm from the logos; plate behind them 0.8 mm solid or more |
| footprint | 72.0 x 128.8 / 121.2 / 111.8 mm | phase 1: 72.11 x the same; the tab's tip is 0.4 mm past the ridge's start |
| forces, one prong (beam estimates) | sliding drag 0.9 N; push on, peak 1.4 N; pull off, peak 1.4 N (0.9 to 4.0 over E 2500-3500, both stiffness bounds, mu 0.2-0.4) | two prongs: about 3 N to take it off |

**Snap, 27bbdaf (coupon A's geometry) against phase 2**, through the same ray casts on the real standard 4.26 end faces
(`check.py --snap`): the tab's thickness profile along its length is equal to within 0.03 mm (0.80 free span blending to 1.60 at the root; the tongue's end, which is
past the ridge, is left out); deflection 0.70 flat and 0.70 peak in both; preload 0.15 against 0.14 mm; one tab, nominal (E 3000 MPa, soft bound, mu 0.3): pull-off peak
1.38 N against 1.41 N (-1.9 %), push-on peak 1.38 against 1.40 N (-0.8 %), sliding drag 0.90 N both, strain 0.89 % both; over E 2500 to 3500 MPa, both stiffness bounds and mu 0.2 to 0.4
the pull-off peak is 0.92 to 3.92 N against 0.94 to 3.97 N. All within 2 %, inside the 10 % asked. The ridge's rounding took 0.03 mm off the home preload, so the ridge sits
0.05 mm further along the cover (`ridge_trim`). The angle at which the ridge **first touches** the case on the way on (`check.py --angle`: the required deflection against the shift along the swept
path, its steepest slope over the first 0.4 mm after the touch; worst of both ends and the three Z plays) is **18.5 degrees in all four poses**, for 27bbdaf's cover and for all three phase-2 covers: still a ramp, not a blunt face.

## What was checked, and how

`check.py` (run: `python -B check.py`) works on the **real STLs** of every build the covers serve: tub, lid with its side keys and
the bottom-key caps from `case-426/out/<build>/` and `case-368/out/standard/`, 33 builds, in **all four poses**, with manifold3d (overlap
volumes, least distances) and vtk ray casts of the end faces and of the cover's own ridge. **Run of record (phase 2's final STLs): 2511 rows over the 33 builds, 0 failing.**
- **Home, every pose**: the frame has no overlap with the case, least distance 0.30 with the stop 0.5 off, none with the cover moved a
  play-width in Z or Y. The ridge's overlap at home (0.64 mm3) is the snap, not a collision.
- **Slide, every pose**: the frame swept along the whole path, cover entirely off the case to home, 1 mm steps: zero overlap.
- **Ridge on the real end faces**, read through the cover's own ridge mesh: deflection 0.70 flat along the straight face (spread 0.00 at
  the extremes of the Z play), peak 0.70, preload 0.15, at both ends in all four poses: nothing catches in J6.
- **Access**: the USB-C recess plus 30 mm of plug room is clear in every pose; the screen window is clear with the cover on the back; the
  plate clears the bottom-key caps by 0.25 in both front poses at home and along the path; the plate stays 2.0 mm or more past the screen
  opening (4.26: 2.1 to 3.2 mm at the left and 2.08 to 2.78 at the right over the 32 builds; 3.68: 2.8 and 4.3).
- **The screen** (the plate is solid over it): the cover rests 1.02 from the glass with the plate on the face and 1.37 at rest (1.35 on the 3.68; the light-strip builds' glass lies deeper), in both front poses, every build.
- **Fingertip**: an r 7 mm sphere touching each pad face's centre, swept in from the side along the face's normal, is clear of the cover in
  every pose, every pad, every build: least clearance 4.82 mm on the 4.26, 6.18 on the 3.68. For comparison, the same approach to a cover without the scallop (`out/design/keyed-noscallop.stl`) clears by 2.71 mm: the scallop gains 2.1 mm.
- **Logo**: with the cover on the back, its engraving lies over the case's own logo (area overlap with the lid STL's section, 1.000 for the icon and for the wordmark, centroid offset 0.00 mm, in
  every build) and the plate behind the engraving is solid for at least 0.8 (0.8 to 1.0 on the 3.68) mm below its floor everywhere (a slab test: the engraving never
  breaks into a key slot; the need is 0.6). **Border lines**: on the plate, 2.09 mm or more in from its edge (so never across the slit or the tab), 5.49 mm or more from the logos, and the plate solid
  behind them for 0.8 mm (0.8 on the keyed cover and the 3.68, the key-slot roofs included; 2.0 on the chinless). **Footprint**: x 72.01 / 71.99 / 72.03 mm against phase 1's 72.11, y the same 128.8 / 121.2 / 111.8.
  **Tab**: the ridge's flat-top band lies inside the tongue outline in every build.
- **It can fail**: the wrong covers must fail, and do. A key slot at one end only fails in the front-turned pose (the plate meets the caps: 124 mm3 at home on the standard build). A 16 mm corner extension meets a pad (all 16 keyed builds, the two poses with the stop on the right, 8.75 mm3 each: 32 failures). The ridge moved into J6's band fails (deflection 0.00 to 0.70 along the straight face, spread 0.70 against the 0.12 limit). 27bbdaf's cover fails the sharp-edge scan (275 touchable segments). `check.py --wrong`.
- **Print**: `printcheck.py` reads every layer of the STLs: nothing hangs more than 0.31 mm past the layer below (the tab's bottom blend to the bed is R1.2: a bigger blend is a near-flat overhang
  in the first layers, 0.9 mm). `slice_read.py` slices the plate file with the OrcaSlicer CLI (never a GUI), generic and CC2, and reads the G-code back: **no support extrusion on any plate**; the lip, the tab and the ridge
  lie where the mesh puts them to 0.04 mm on every layer they stand in (probes: the lip, the tab's free span, the tongue, the taper and the ridge), including the tab's first layer on the CC2 (the foot's rounded
  to 0.3 where a 0.38 round left a first-layer line 0.55 wide that the CC2's classic walls and EFC 0.1 would drop); on the generic preset's Arachne walls two layers of the 1.2 mm taper leave a 0.28 mm gap
  between two lines (the CC2's classic walls fill it); the only bridges are one layer (z 0.6, or 0.4 and 0.6 on the 3.68) over the engravings' 0.2 to 0.4 deep voids (the logos and the border lines), where a line
  hangs at most 0.77 mm past the layer below (the lid's own logos do the same). Generic presets: 1 h 17 / 1 h 10 / 1 h 11 and 22.7 / 20.8 / 20.6 g; CC2: 40 / 38 / 38 min and 23.8 / 22.0 / 21.5 g (keyed, chinless, 3.68).
  `inlay_check.py` switches the logo on in a copy of the plate file: filament 2 is laid only inside the two logo boxes on layers 0.2 and 0.4 (0.10 g on the keyed plate) and filament 1 uses 22.42 g against 22.68 g with the switch off
  (the border lines are not part of the switch).

### Sharp-edge result

`python -B edges.py keyed|chinless|x3` (convex mesh edges turning more than 50 degrees, grouped; "touchable" = a face normal escapes), on the STLs as built:

| Cover | Engraving rims (logo and border lines) | Anything else |
|---|---|---|
| 4.26 keyed | 1766 segments, 2063 mm | 46 facets under 0.06 mm (1.6 mm of edge in all) at the slit's round end, a mesher fan, not geometry |
| 4.26 chinless | 1764 segments, 2002 mm | 16 such facets (0.9 mm) and 3 segments of 0.4 mm in all at 50 to 51 degrees |
| 3.68 | 1773 segments, 1885 mm | 46 such facets (1.6 mm) |

**No touchable sharp edge is left on any cover but the engraving rims.** In phase 1 the key slots' roof edges (2 x 4.1 mm on the keyed, 2 x 4.4 on the 3.68, 90 degrees), the 0.5 mm step where the tab's
foot met the plate's chamfer (5.3 mm of edge on the keyed cover) and the chinless cover's mesher fans were left; phase 2 removed them: the slot cutter is flared at the mouth, the tab's foot grows into the
plate's chamfer over the taper, and the plate has no relief to leave fans at its seams. What is left, and why:
- **Engraving rims** (the case's two logos, 0.4 and 0.2 deep with strokes down to 0.36 wide, and the border lines, 0.8 wide, 0.4 deep): the case's own treatment of its logos and grip grooves; a stroke that narrow cannot take a fillet.
- **Mesher facets**: tiny facets the STL writer puts at the slit's round end; zero-width slivers, no geometry.

27bbdaf's cover, the same scan: 275 touchable segments (1437 mm).

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
python -B check.py              # 33 builds, four poses (about 40 minutes); --group keyed|chinless|x3, --builds a,b; --wrong; --snap; --angle; --plate
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
