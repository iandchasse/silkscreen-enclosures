# Bottom keys: bell crank + sliding key — implementation spec (2026-09-26, stage 4: review fixes)

Scope: SW9, SW8, SW3 and SW2 in both cases: the 4.26" Rev K (standard and light-strip builds) and the 3.68" x3 (standard and light-strip builds). This replaces today's rocker, spring toe, rib, V-seat and toe ledge.

Frame: X runs along the board; the key centres are 11.4975, 23.4975, 36.4975 and 48.4975. "dx" is X measured from the key centre. Y runs up the board, with 0 at the board's bottom edge. Z points toward the screen: 0 is the PCB rear and 1.6 the PCB front. Units are mm and degrees. θ is the crank angle; positive means pressed, and 0 means the crank-M nose is touching the nominal MJTP face.

**Status (2026-09-28):** built into both case projects (Rev L: `case-426/src/keys.py`, `case-368/src/keys.py` and `crank.py`, every number in each `params.py`) and checked; not printed. The rod's left stop is now the printed side gate of [SIDE-GATE-SPEC.md](SIDE-GATE-SPEC.md) ("SPEC2 rev 3"), not the M2.5 screw below; the lines marked "Superseded" say where. Where this spec and the code differ, the code and the case READMEs are the later check.

**Test 1 (2026-09-29, the printed 4.26 case; edited in place 2026-09-30):** the cranks' open C cracked off at the bore and some cranks came off the rod, and the key's slit showed on the button face. Two changes, the same in both case projects:
- **Crank cheeks** (§0, §3, §8 items 7 and 8): each cheek is a closed ring round the rod over |dx| 4.05–5.25 with a round bore (0.80 of wall over the rod, 0.75 at the least); the open C is left only in the inner 0.30, beside the TS365 housing. The +Y trim is -0.70, on the print's layer grid. The cranks print with Arachne walls.
- **Key** (§4, §8 items 7 and 8, §10): it prints on its -X end, and its slit stops under a closed roof 0.70 (x3std 0.50) below the face, so the button face has no slit.

**Test 2 (2026-09-30, the 4.26 case printed again; edited in place):** the keys tilted, sat low, stuck or fell out, and the cranks were out of place until the lid went on. The drag leaf held a key wherever it was left, tilted or not; some bumps touched the chin wall and some did not; the only hook was the bump's small top at the key's +X end. Ian chose the design study's recommendation (keystab `RECOMMENDATION.md`, concept "C4-A"): the **hook keys**, the same in both case projects.
- **Key** (§0, §4): the leaf, its slit, the roof slot and the bump are gone. Two rigid hooks stand on the chin side, one at each end, and a root fills the chin side at the bed end. Nothing on the key flexes or rubs.
- **Tub** (§5): two slots per key in the chin wall's inner face, open to the rim, up to a flat roof. Face down, each key drops `KEY_W_OUT` = 1.00 onto both hooks, level; face up it rests on its crank as before.
- **Assembly** (§7): no tuning coupon; the tub stays face down from the keys until the board is in. **Checks** (§8), shared parts (§9) and risks (§10) follow. The cranks, rod, gate, lid, midplate and board are unchanged.

**The 3.68 standard build's screen bevel (2026-10-10; edited in place):** x3std's face went from Z 4.07 to 4.47 (`case-368/src/params.py` `STD_FACE_RAISE`), so its skin over the panel is 1.0 (was 0.6). Computed from the face, `key-x3std` is 0.4 taller (6.17), its hooks and the slots' roof are 0.4 higher (roof 2.67, still the highest z that keeps 0.45 of wall behind the slot; hooks 0.87–1.67 at rest), and its guide is 0.4 longer, so it tilts less. §1, §4's per-build table, §5's hook slots and §9 give the new numbers. The §4 drawing, the x3 std forces, stresses and tilt figures (§3, §4 Guides and Pressable zone, §6, §8 item 7) and the plastic over the cheek slots (§2, §8) are still x3's at face 4.07; the 3.68 README's "Screen bevel" gives the new ones. x3ls and the 4.26 are unchanged.

**The crank well (2026-10-12; edited in place).** Ian, from his printed and assembled cases (both sizes): "The crank hits a friction point when rotating from its button side to its switch side." In the open, face-down tub (assembly, before the board is in) a crank turned by hand swings from lying on its key (-11.25 / -11.4) to its nose on the rail's +Y face (about +98 for crank-M, +106 for crank-T). At about +40 the corner where the cheek's flat z 2.5 top meets its second trim (y -1.00, z 2.50) passes under the cheek slot's roof. That corner is 2.42 from the rod's axis, outside the R 2.20 arc that §3 measures the roof gap to, and 2.48 as sliced (its layer, y -1.1 to -0.9, carries z 2.5 on to y -0.9).
- Drawn, it cleared the 3.15 roof by 0.13. As printed the roof lands on the face-down tub's layer grid: 3.20 on the 4.26, 3.07 on the 3.68.
- Face down, gravity takes the crank on the rod and the rod in its rings toward the roof, through their play (bore reamed 1.90, ring bores 1.93 free as sliced, rod 1.72 at its smallest: 0.195), and each face of the crank prints up to 0.075 large.
- So it scraped: -0.15 (4.26) and -0.28 (3.68) at worst. §8's sweep stopped at +16, where the board's switch stops the crank, and took the CAD on the rod's axis. In use the crank never reaches the corner's pass.

The fix is in the tub alone: the slot roof (`SLOT_ROOF`) goes to 3.60 on the 4.26 and to the skin's underside, 3.47, on the 3.68.
- 4.26: 3.60 is a layer boundary, so it prints at 3.60; 1.38 of rail is left over each slot.
- 3.68: the 0.32 of rail over each slot is gone. 3.47 is on both builds' layer grids.
- §8 item 2a, the new free-swing check, now reads 0.25 (4.26) and 0.12 (3.68) at worst. As sliced, on the axis, it reads 0.52 / 0.39; drawn, 0.58 / 0.45.
- The cranks, keys, rod and gate are unchanged: reprint the tub. §2, §3 (Cheeks, Clearances), §5, §7 step 5 and §8 give the new numbers.

The Rev L key-fit clearances of 2026-09-29 (cap y -7.53 on the 4.26 and -7.55 on the 3.68 to -4.225, half-width 4.95, chin side 0.40, no foot; half-width 5.00 since 2026-10-03, and on the 3.68 the cap's +Y corners R1.0, was R0.5) are in the code and the case READMEs only; §4's outline and gaps are still the stage-4 ones.

Sources: the working files this spec cites (`layout.json`, `stage3.md`, `stage4.md`, the stage-4 scripts in `s4/` and the stage 1–3 scripts in `design/`) were not kept; their numbers are in each project's `params.py` and its "keys (bottom row)" block. There is no `forces.md`: the forces are in §6 of this spec.

## 0. Decisions in one screen

- **Mechanism.** The finger presses a straight key toward -Z. The key pushes the crank's crowned pad at y -7.45. The crank turns on a 1.75 mm PLA filament rod at (y -2.50, z +0.60). Its crowned nose pushes the plunger toward +Y at z -2.35. The lever ratio is 1.678 (input arm 4.95, output arm 2.95), so the key force is 0.596 × the switch force before friction.
- **Rod capture (stage 4).** The rod is fed in along its axis through a Ø1.95 hole in the tub's -X side wall. Nothing snaps.
  - The 5 rail segments beside the cranks (the two ends and the three webs) are closed rings.
  - The 4 centre segments keep an open seat. It has to be open: the TS365 housing comes within 0.065 of the bore. It takes the pin load at 211°, into its solid wall.
  - Axial stops: a printed side gate in a slot in the -X wall (SPEC2 rev 3; it replaced an M2.5 x 4 flat-head screw), and the +X side wall's inner face.
- **Rod support.** Every crank cheek runs in a 1.8 mm slot, with rail on both sides and 0.15 gaps. The rod works in shear and bearing. At a 20 N over-press on one key it sees 14.6 MPa of bending (18.9 MPa with 3× softer bearings).
- **Crank (stage 4).**
  - A **belly** fills in under the crossbar across |dx| 1.3–5.25. At 20 N the crossbar, loaded as a beam along X, drops from 62 MPa to 24.5 MPa, in-layer.
  - The whole crank is **clipped at y -7.70**. That widens the bed face and raises the chin gap at -13° from 0.11 to 0.20.
  - The cheeks are trimmed to y ≤ -0.70, to clear the board edge (-0.75 at stage 4; the pad-end print puts that face on the 0.2 layer grid at -0.70 either way).
  - **Cheeks (test 1, 2026-09-29/30).** Each cheek is a closed ring round the rod over |dx| 4.05–5.25, with a round bore. The open C is left only in the inner 0.30, beside the TS365 housing. The crank can no longer leave the rod.
- **No take-up and no preload (test 2).** The key rests on its crank and the crank on its switch, so the key's rest height is the switch's: face up there is no free travel before the click. Nothing on the key flexes or rubs.
  - Until test 2 a friction drag leaf on each key (0.017–0.092 N once its bump was set from a tuning coupon) held the key where it was left. It held tilted keys too, and the bumps touched the wall on some keys and not on others.
  - Why not a spring: a Z-acting spring would have to cover about 2–2.9 mm of travel while staying under about 0.2 N at the plunger. That needs a PLA leaf at least 16 mm long (17–24 by the test-2 study), and there is no room.
- **Key retention (test 2): two rigid hooks.** Each key has a hook at each end of its chin side; they run in two slots in the chin wall, open to the rim. Face down the key drops `KEY_W_OUT` = 1.00 outward onto both hooks, flat under the slots' roof, level and 2.5 proud (the 4.26 since 2026-10-03: 2.37, its cap 0.15 lower: §4, Height proud). It cannot come out through the face: its +Y face rides the rail, so a hook can only move toward the chin, deeper under the roof. Keys go in and come out from the inside only. (Stage 4 to test 2: the bump's square top under a 0.25 skin ledge.)
- **No hard over-press stop.** Any tub-fixed or crank-fixed stop lies inside the rest scatter (±0.34, or ±0.68 with the TS365 tip tolerance). The switch takes the over-press: a 20 N press puts 33.6 N on the plunger.
- **Bezel.** The chin grows by Ian's +1.0 mm. The chin wall moves -1.0 in Y (inside -8.2, outside -9.2) on both the tub and the lid, and stays 1.0 thick.

## 1. Builds

| build | face Z | skin underside ("lip") | lid floor inside | key part |
|---|---|---|---|---|
| 426std | 6.00 | 4.98 | -5.5 | key-426 (shared) |
| 426ls | 6.00 | 4.98 | -5.5 | key-426 (shared) |
| x3std | 4.47 (4.07 until 2026-10-10) | 3.47 (1.0 skin; 0.6 until 2026-10-10) | -7.435 (-6.435 until 2026-10-12) | key-x3std |
| x3ls | 5.27 | 3.47 (1.8 skin) | -7.435 (-6.435 until 2026-10-12) | key-x3ls |

## 2. Rod and rod support

> **Superseded 2026-09-28 by SPEC2 rev 3:** the rod's left stop is a printed side gate in a slot in the -X wall (no M2.5 screw, no countersink); rod 63.25 +- 0.2 with a pencil-taper tip to a 0.8 flat and a square tail; removal with a paperclip in the gate's pull hole. The lines below are edited to match; each project's README "Bottom keys" has the details.

**Rod**
- One length of 1.75 mm PLA filament (real diameter 1.72–1.78), cut to **63.25 +- 0.2** (61.0 with the old screw).
- **Straighten it:** take it from the outer turns of the spool. Lay it on the printer bed at about 60 °C under a flat plate for 5 minutes and let it cool under the plate.
- Accept it only if it rolls freely on a flat surface with no gap over 0.1 under it.
- Taper the insertion end like a pencil over 1.0-1.5 with a craft knife and sand the very tip flat, about 0.8 across (not a chamfer, not a needle point). Cut the other end square: it bears on the gate.
- It spans X -2.34 to 61.41, with end play 0.3–0.7 (0.05-0.95 with the gate, slot and squareness stack).
  - Left stop: the side gate's flat inner face at X -2.34.
  - Right stop: the +X side wall's inner face at X 61.41.

**Side-wall hole (tub, -X wall, all four builds)**
- Ø1.95 on the rod axis (y -2.50, z 0.60) through the wall, X -4.09 to -1.41.
- No countersink and no screw. Instead a **gate slot**, open to the rim (SPEC2 rev 3, section 3): a mouth X -4.09..-2.99 (y -3.85..-1.15) between two 1.10 lips, a flange cavity X -2.99..-2.19 behind them with R0.40 round ends, and a 45-degree floor; the rod's teardrop runs through the floor.
- A printed **gate** (a T, SPEC2 rev 3, section 4) drops into the slot from the open back. Its bevel cams the rod's square tail the last 1.75 home, and its flat inner face at X -2.34 closes the rod's end play. The lid's rim closes over it.
- The wall is flat there (y -3.5 to +1). The slot's round ends reach y -4.75 and -0.25; the corner curve starts at y -5.
- Nothing else lies on the rod path: over X -1.3 to 3.6 and X 56.4 to 61.3, the nearest part in every build is 1.87 from the rod (+0.1).

**Rail (hangs from the skin; +Y face at y -0.45, -Y face at -4.225)**

| segment X | seat | profile (`layout.json`) |
|---|---|---|
| end L **-1.41**–6.1 (runs on to the side wall) | closed ring | `profile_ring_lip_*` |
| 7.9–15.1, 19.9–27.1, 32.9–40.1, 44.9–52.1 (centre, under each switch) | open seat | `profile_centre_lip_*` |
| webs 16.9–18.1, 28.9–31.1, 41.9–43.1 | closed ring | `profile_ring_lip_*` |
| end R 53.9–56.3 (through; the rod runs on to the +X wall) | closed ring | `profile_ring_lip_*` |

- **Ring seat.**
  - Bore Ø1.95 on (-2.50, 0.60), drawn as a teardrop pointing device -Z (print-up), flat-topped at z -0.55.
  - Ring block y -4.225 to -0.45, from the skin down to z -1.20, with 0.4 × 45° chamfers on its lower corners.
  - Walls: 0.65 under the flat, 1.07 to the +Y face, 0.75 to the -Y face.
- **Open seat.** Today's profile with the +Y face moved to -0.45. The mouth (262–370°) is now only clearance: 0.77 to the TS365 housing and 0.36 to its plunger. The load ray (211°) has 1.02 of wall.
- **Cheek slots** at |dx| 3.60–5.40 per key, open toward -Z. Since 2026-10-12 (the crank well, above) the roof is at z 3.60 on the 4.26, with 1.38 of rail plus the 1.02 skin over each slot. On the 3.68 it is the skin's underside, z 3.47, with no rail over the slot. Before that it was z 3.15 in all four builds (on x3, 0.32 of rail plus the skin).
- The rail's -Y bottom edge keeps its 0.4 × 45° chamfer. Over the plunger it rises to -0.62.
- Rail to board: 0.25 with the board edge at -0.2 (δ 0.2). With a further 0.2 of PCB outline tolerance (edge at -0.4) it is 0.05.

**Webs**
- X 4.8–6.2, 16.8–18.2, 28.8–31.2, 41.8–43.2 and 53.8–55.2.
- They span y -8.2 to -4.225, from the skin down to z 1.0.
- They tie the rail to the chin wall and guide the keys in X.

**Stress at a 20 N over-press on one key**
- Loads: 33.6 N into the plunger, 39.1 N on the pin, 19.5 N per cheek.
- Rod (the supports are unchanged in position):
  - bending: 14.6 MPa FE (`design/rodfe.py`), 18.9 MPa with 1/3 bearing stiffness; the reviewer's hand check gives 10.3;
  - shear: 5.7 MPa;
  - deflection: 8 µm.
- Cheek and seat bearing: 7.6 MPa. A normal click with the 2.94 N switch: 1.2 MPa.

## 3. Crank (identical in all four builds; 4 per case)

**Geometry (θ 0; YZ profiles in `layout.json` → `crank.profiles_yz_theta0`)**
- **Cheeks**
  - Two cheeks at |dx| 3.75–5.25, 1.5 thick, around the rod.
  - They stay behind the rail face above z -0.6 and have a 45° front roof, z = y + 5.575.
  - Their top is an arc R 2.20 about the rod (test 1), so it stands at z 2.80 over the axis (was 2.50). That was 0.35 under the 3.15 slot roof; since 2026-10-12 it is 0.80 (4.26) or 0.67 (3.68).
  - On the +Y side the flat z 2.5 top runs on outside the arc, from y -1.39 to the second trim, and ends in a corner 2.42 from the axis (2.48 as sliced). Turning the crank + by hand with the board out (the free swing) takes that corner under the slot roof at about +40 (the crank well, above).
  - **Trimmed to y ≤ -0.70** (test 1; -0.75 at stage 4). The crank prints pad end down in 0.2 layers from y -7.70, so a face normal to Y lands on that grid: -0.75 printed at -0.70 anyway, and the model is now what prints.
  - **Two zones (test 1)** on one (y, z) outline:
    - **Lip, |dx| 3.75–4.05** (0.30 wide): the stage-4 open C and teardrop (see Bore). A closed ring cannot exist here: the TS365 housing's corner is 1.04 from the rod axis.
    - **Ring, |dx| 4.05–5.25** (1.20 wide; 4.05 = the housing's 3.65 + the crank's X float 0.15 + 0.25): closed round the rod, with a fill under it, the polygon (-3.40, 0), (-1.50, 0), (-1.30, -0.70), (-1.70, -2.20), (-3.40, -2.20). The fill ties the ring's -Z side into the belly and runs forward under the rod to the MJTP housing's frontier (0.03 clear over the swing).
- **Crossbar and pad**
  - Span |dx| ≤ 5.25, **y -7.70** to -4.65, z -1.5 up to -0.6. From y -7.0 on the bottom drops to -1.8.
  - The lower-front corner is chamfered along the line from (-7.2, -1.6) to (-8.5, -0.3).
- **Pad crown**: R 0.6, centre (-7.45, -0.80), top -0.20, full width, **clipped at y -7.70** like the rest of the crank.
- **Centre leg**: |dx| ≤ 1.30 under the rail, ending in a crowned nose (R 1.0) that contacts the plunger at z -2.35.
- **Belly (stage 4)**
  - The leg's body profile without the nose, extruded across 1.30 ≤ |dx| ≤ 5.25 on both sides.
  - Its outline runs (-4.9, -0.6), (-4.65, -0.6), (-4.65, -1.3), (-2.92, -1.3), (-2.92, -3.05), (-3.22, -3.35), (-4.9, -1.5). That puts a 0.3 chamfer on the +Y lower corner.
  - It merges with the cheeks and the leg, and keeps the leg's 45° underside.
- **Bore**
  - Ø2.0, reamed to 1.9, with a 0.3 × 45° lead-in on both outer faces of each cheek. Since test 1 the same lead-in is also cut on the ring's inner face where the lip leaves it bare: on the +X cheek the rod's tip meets that face after the lip.
  - **Ring (test 1, 2026-09-30): round.** Its top, y -1.50, is a layer boundary, and it closes as a short arch held on both sides. The wall is 0.80 over the rod (y -1.50 to the -0.70 face: four layers) and 0.75 at the least (the R1.75 disc beside the axis, and the 45° roof). With the stage-4 teardrop it was 0.57. As sliced (Arachne) the least wall is about 0.58, from 0.41.
  - **Lip:** the stage-4 flat-topped teardrop pointing +Y (flat 1.15 from the axis) and the open C, -80° to 0° (clearance for the switch housing).
  - The rod goes in axially through the closed holes, and its taper finds them. The lip's C plays no part in holding it.

**Two nose variants**

| variant | nose front y | crown centre | use with |
|---|---|---|---|
| crank-M | -1.92 | (-2.92, -2.35) | APEM MJTP1117 (DigiKey build) |
| crank-T | -2.20 | (-3.20, -2.35) | SHOU HAN TS365ZJ (every JLC board) |

A wrong variant shifts the key's rest height by about ±0.48.

**Printing**
- Stand it on the pad end (the y -7.70 face) with +Y up. The first layer is 1.10 × 10.5; the part is 7.00 tall (6.95 with the stage-4 trim) with its CG about 3.2 up, centred over the strip.
- No supports and no brim. Every -Y-facing face is at 45° or steeper, except the ring's round-bore crown (an arch closed from both sides; no sliced layer reaches more than 0.48 past the one below) and the lip's 0.53 teardrop flat (a 0.26 ledge).
- Elephant-foot compensation 0 and Arachne walls, per object (test 1; the plate files carry both). With classic walls Orca drops the inner loop in the 1.5 cheeks (under the 1.74 two loops need) and leaves 0.25–0.70 mm² of void per layer at the ring's root. With Arachne the sliced cheek covers at least 0.90 of its section in every layer through the bore.
- If a crank tips in the test print, print on a 2-layer raft (0.2 gap). Up to 0.1 of residue on the pad end is tolerated: the -13° chin gap drops from 0.196 to 0.086.

**Rotation (matching variant)**

| state | θ | key travel |
|---|---|---|
| rest | -3.9 to +3.9 (tub–board δ ±0.2) | – |
| click | 4.8 | 0.41 |
| switch bottom | 8.7 | 0.73 |
| worst case | 12.5 | – |

All clearance sweeps cover -13° to +16° (key travel -1.15 to +1.31).

**Clearances (minimum over the sweep; the matching range -4° to +13° in brackets)**

| from | to | gap |
|---|---|---|
| cheek | TS365 housing | 0.162 |
| cheek (lip) | MJTP housing | 0.391 (0.665); stage 4: 0.413 |
| ring (test 1) | MJTP housing moved 0.2 nearer, the crank at its 0.15 X float toward it (≥ 0.03) | 0.052 (the 4.26's envelope) / 0.089 (the 3.68's) |
| cheek | board edge at -0.2 | 0.334 (0.439); stage 4: 0.266 |
| cheek | board edge at -0.4 | 0.134 (0.239), 0.10 with the crank hanging free; stage 4: 0.071 (-0.014 untrimmed) |
| cheek | slot roof | 0.241 with the 3.15 roof (stage 4; 0.311 at +16° as built). Since 2026-10-12 the roof is 0.45 (4.26) or 0.32 (3.68) higher: 0.761 / 0.631 at +16° (0.800 / 0.670 inside -4..+13). Over the free swing (§8 item 2a), at the cheek's corner about +40°: 0.580 / 0.450 drawn, 0.250 / 0.120 as sliced, grown and sagged |
| leg and belly | centre rail | 0.067 at -13° (0.236) |
| crossbar | rail | 0.375 |
| belly | TS365 housing | 0.248 (0.438) |
| belly | MJTP housing | 1.218 |
| belly | plunger, kinematic: the nose pushes the plunger; the TS365 plunger may be 3.7 wide, so \|dx\| ≤ 1.85 | ≥ 0.448, same as the leg body |
| crank | chin wall | 0.196 at -13° (0.377) |
| crank | lid | ≥ 2.08 |

**Strength at a 20 N press**
- Crossbar with belly, as a beam along X pinned at the cheeks: section A 6.05, Iy 2.45, Iz 12.7.
  - Bending: 10.7 + 13.8 = **24.5 MPa**, in-layer. The pad-down print puts X in the layers, and PLA manages about 50 MPa in-layer.
  - Torsion about 2 MPa and shear 4.2 MPa, both on the layer planes.
  - Without the belly the same beam gives 62 MPa.
- Crossbar root at y -6.2, across the layers: 9.9 MPa.
- **Cheeks (test 1; `mechanics.cheek_stress`)**, across the layers, from a 2D FE of the cheek's section (recorded as `CHEEK_FE_PER_N` and `CHEEK_FE_20N`, not re-run):
  - 1.26 MPa per N of pin load on one cheek. The stage-4 open C gave 8.0, and the first closed ring (teardrop bore) 1.32.
  - At the largest click: 4.6 MPa on the 4.26 (3.74 N on the cap), 5.7 on the x3std (4.60 N) and 4.9 on the x3ls (3.96 N), all ≤ 12. The open C gave 29–36 at the same clicks.
  - At a 20 N press (19.5 N per cheek): 18.8 MPa layer average, 24.5 peak, in the +Z band where the 45° roof pinches it. That is over the 12 of §8 item 7; the exception is stated there.
  - Least layer area per cheek through the rod (y -3.0 to -1.4): 3.87 mm². It was 3.51 with the teardrop, and 1.3 (open) with the C.

## 4. Key (a)

```
 section at the key centre, rest, x3 std (face 4.07; other builds only taller)
      y: -8.2 -7.95 -7.8 -7.3 -6.8 -6.55        -4.225  -2.5
 5.57         |LL| |KKKKKKKKKKKKKKKKKKKKKK|            cap top = face + 1.5
 4.07  skin===]|LL| |KKKKKKKKKKKKKKKKKKKKKK|[== skin (solid)
 3.47  ledge 0.25^|LL|s|KKKKKKKKKKKKKKKKKKKKKK|RRRRRRRR  rail (+Y face -0.45)
 2.50  bump top _|LL|l|KKKK  body |dx|<=3.45 |RR  o   <- rod (-2.5, 0.6)
 1.90  flat  |<[LL|i|KKKK                     |RR
 1.60  bump  |   |t|KKKK  (cheek zone: underside 2.70 for y > -6.25)
       -8.32 tip  \KKKK
 0.55  foot KKKKKKKKKK  back plate / pusher     rail face -4.225 = +Y guide
-0.20  KKKKKKKKKKKKKK  <- flat pusher on the crown (-7.45, top -0.20)
```

The drawing is the stage-4 key. Since test 2 the leaf (L), slit (s), roof slot and bump are gone: above the pusher's stop (z 0.55) the key's chin side is the cap's chin face, solid, with the two hooks on it (Hooks, below).

**Guides**
- The +Y face rides a continuous face at y -4.225: the rail face, with the skin opening's +Y edge made flush with it. Nothing presses it there since test 2 (the leaf did); the rail is what keeps the hooks from unhooking.
- In X, the cap (|dx| 5.10) runs between the webs and the opening sides (5.30).
- The foot sits 0.15 off the chin wall. That limits tilt play to 0.15/Lg (about 2° on x3 std).

**Shape (device Z at rest; the same outline in every build)**

| zone | extent | bottom |
|---|---|---|
| cap | \|dx\| ≤ 5.10, **y -7.80** to -4.225 (3.575 deep), above z 1.60 | top at face + 1.50; 0.4×45° chamfer on all four top edges (test 1: the chin edge was square while the slit came up through the face) |
| back plate / pusher | \|dx\| ≤ 5.10, y -7.90 to -6.55, below z 1.60 | flat at -0.20 |
| foot | y -8.05 to -7.90, z -0.20 to 0.55 | – |
| body | \|dx\| ≤ 3.45, y -6.55 to -4.225 | +0.40 |
| cheek zone | \|dx\| 3.45–5.10 | -0.20 for y ≤ -6.25; **+2.70** for y > -6.25 |

- The crown contact moves from y -7.63 to -6.88 over -13° to +16°. It stays on the pusher band (-7.90 to -6.55) and inside the crank's -7.70 clip.
- Minimum gaps to the crank over -13° to +16°, with the belly: 0.236 in the centre and middle zones, 0.142 in the cheek zone (`s4/key4b.py`).

**Hooks** (test 2, 2026-09-30; `KEY_HOOK`, `KEY_SLOT`, `KEY_W_OUT`, `KEY_ROOT` in each `params.py`)
- **Chin side.** Above the pusher's stop (z 0.55) the key's chin side is the cap's chin face (y -7.53 on the 4.26, -7.55 on the 3.68), solid all the way up: the old leaf zone is filled. Below it the pusher's chin end, 0.40 off the chin wall, is the chin-side stop.
- **Two hooks**, one at each end: |dx| 3.95–5.00 (centres 8.95 apart; 4.95 and 8.9 until 2026-10-03), 0.80 tall (two outer wall lines as the key prints), from the chin face out to the tip, **0.40 off the slot's back** (as the pusher is off the chin wall: all the key's print error in Y lands on the chin side, and 0.40 keeps a rigid pair ≥ +0.05 at the worst of `KEY_FDM`).
  - The +X hook's -X face is a 45° lead in plan (from the chin face at dx 3.95 − lead out to the tip at 3.95), so it builds up with no overhang as the key prints on its -X end.
  - **Root** (`KEY_ROOT` 0.60): over the first 0.60 from the -X end (the bed) the chin side is solid out to the hooks' tip, from the pusher's underside up to the hooks' top. Without it the bed end's chamfer left a thin stub of the -X hook in layer 1, which the slicer drops, and layer 2 hung the hook about 1 mm off nothing.
- **Slots** in the tub (§5): two per key, open to the rim, up to a flat roof. `KEY_W_OUT` = 1.00 is the hook top to the roof at rest: it must clear the switch's rest scatter at the key (0.70 worst: board ±0.2 and TS365 tip ±0.2 through the lever) plus the chain's print (0.14) and the stop's (0.15): 0.99.
- **The hold.** Face up (or held tilted back to read) gravity lays the key on its crank and the crank on its switch: the key sits where its switch puts it, with no free travel before the click. Face down it drops 1.00 onto both hooks, level (0.64° at most for 0.1 of difference between them). The first press in that pose travels about 0.5–1.5 before the click.

**Per build (test 2)**

| | key-426 (both 4.26 builds) | key-x3std | key-x3ls |
|---|---|---|---|
| key height (pusher to top) | 7.70 | 6.17 (5.77 until 2026-10-10) | 6.97 |
| slots \|dx\| | 3.20–5.40 | 2.65–5.40 | 2.65–5.40 |
| slot back (y) | -8.80 | -8.95 | -8.85 |
| slot roof (z) | 4.98 (skin underside) | 2.67 (inside the chin wall; 2.27 until 2026-10-10) | 3.47 (skin underside) |
| hook tip (y) | -8.40 | -8.55 | -8.45 |
| hooks at rest (z) | 3.18–3.98 | 0.87–1.67 (0.47–1.27 until 2026-10-10) | 1.67–2.47 |
| +X hook's lead | 0.87 | 1.00 | 0.90 |
| stop above rest (`KEY_W_OUT`) | 1.00 | 1.00 | 1.00 |
| guide length Lg | 6.0 | 4.47 (4.07 until 2026-10-10) | 5.27 |

- The slots' outer side is flush with the webs' face (5.40): the opening's 5.30 would leave a 0.10 fin. On the 3.68 the inner side is 2.65, clear of the +X hook's lead with the key at its chin stop and pushed sideways; on the 4.26 (3.20) the lead meets the slot's inner edge first when the key sits fully -X and 0.25 toward the chin, a 45° sliding contact.
- x3std: its 0.6 skin and the chin's R1.8 round leave too little wall behind a slot under the skin, so its roof is the highest z that keeps 0.45 of wall on the tub's layers (2.27, where the round starts; the study's 2.40 would print at 2.47 with 0.44), and the hooks bear 0.35 on the roof, not on the skin. Since 2026-10-10 the face, its round and so the roof are 0.4 higher (2.67, with 0.449 of wall behind the slot), under a 1.0 skin.
- Hook roots at a 5 N pull-out: shear 3.1 MPa, bending 15–19 MPa in the layer (≤ 8 / 25).
- Until test 2 the key had a drag leaf (the chin-face strip, 0.5 thick, with a slit beside it and a bump at its free end) that pressed 0.017–0.092 N of drag onto the chin wall once its bump was set from a tuning coupon (`KEY_DRAG_BUMP`, four coupon keys). Its numbers are in the case projects' history (git), not here.

**Height proud**
- 1.50 nominal. 1.16–1.84 across tub–board δ ±0.2 with the matching crank. 0.82–2.18 if the TS365 tip tolerance (±0.2) is added.
- At the click the key is at least 0.72 proud; at the switch bottom, at least 0.38.
- **The 4.26 since 2026-10-03: 1.35 nominal** (Ian: the caps stood "a small fraction of a mm too high"; `case-426/src/params.py` `KEY_CAP` proud, 1.50 before). Only the cap's top moved: the hooks hang from the slots' roof, so `KEY_W_OUT`, the stop and the travel are unchanged, and face down the cap stands 2.37 proud (2.52 before). 1.02–1.69 across δ ±0.2 with the matching crank (`mechanics.key_proud`), 0.67–2.03 with the TS365 tip tolerance. At the click the median key stands about 0.90 proud; at the low end of δ the key is at least 0.62 proud at the click and 0.31 at the switch bottom (its rest less `mechanics.json`'s travel). **1.35 is the floor:** at that end of δ ±0.2 the lever takes 0.33 off, so a cap under about 1.34 breaks §8 item 6's 1.0. To undo, set it back to 1.50. The 3.68 keeps 1.50 (lowering it needs its own check).

**Pressable zone (`s4/forces4.py`)**
- At μ 0.3 the tilt factor stays ≤ 1.5 over the whole cap on 4.26 and x3 ls, and up to y -4.76 on x3 std. At its top edge the factor is 1.54.
- No jamming anywhere, even at μ 0.45: 2μe/Lg ≤ 0.71.

**Retention**
- The skin opening's chin edge is at **y -7.95**, over the chin wall (-8.20). The cap's chin face keeps 0.42 (4.26) or 0.40 (3.68) of clearance to it.
- Since test 2 the hooks are the outward stop: 1.00 above rest both hooks meet the slots' flat roof (the skin's underside, or on x3std a roof inside the chin wall). It is a positive stop, not a ramp, and the key's +Y face on the rail stops it unhooking.
- Keys go in from inside, hooks in their slots (they fit only one way round: turned round, the hooks would hit the rail). They come out inward, after the crank is removed, down the slots and out at the rim. There is no inward stop of the key's own: before the board is in, the crank is all that stops a key sinking (§7, keep the tub face down).
- Until test 2: the bump's square top under the 0.25 ledge, 2.48 (4.26) or 0.97 (x3) above rest.

**Printing** (test 1, 2026-09-29): on its -X end, +X up; no supports, no brim; elephant-foot compensation 0 (per object).
- The bed end has a 0.4 × 45° chamfer all round (the outline 0.30 in on layer 1 and 0.10 on layer 2), so its elephant foot stays inside the cap. The root (test 2) keeps that chamfer from leaving a thin stub of the -X hook.
- The -X hook starts on the root at the bed; the +X hook's -X face is its 45° lead in plan; the body's -X step (from (dx -3.30, z 2.70) to (dx -1.00, z 0.40), for y -6.25 to the +Y face) is cut at 45°. Nothing starts in mid-air, and no layer reaches more than 0.30 past the one below (the cap's top chamfer), read back from the G-code.
- The hooks are 0.80 tall: two outer wall lines, solid (0.85–1.7 would leave a void between them).
- **No slit on the button face** (test 1, and since test 2 no slit at all). In this pose the face is a side wall (fine 0.2 layer lines, not the PEI texture), and the seams sit inside, off the button face and the chin face.
- The key stands 10.00 tall, exactly 50 layers, on a first layer of about 8–16 mm² (key-x3std to key-426; 9 for key-x3std until its R1.0 corners, 2026-10-03), like the cranks' 7.00 on 11.5. (Until 2026-10-03 it was 9.9: Orca dropped the 50th layer and printed 9.8, 0.40 of side play a side; now 0.30.)
- Until test 1 the key printed cap-down (flat top on the bed): the leaf and slit started on the bed, and the slit showed on the cap top, 0.5 in from the chin edge.

## 5. Tub changes (b), all four builds

**Remove**
- The rocker rib / V-seat walls (`tub.key_seats` rib).
- The toe ledge (y -7.15 to -6.4, z -3.69 to -2.21, full X).
- The old rocker ribs and pillars at X_c -2 to +1.5.
- The sloped-cap key openings, and the x3ls key wells (the new caps stand proud).

**Chin**
- Tub and lid chin walls move -1.0 in Y: y -9.2 to -8.2, still 1.0 thick. The built wall is -8.2 to -7.2.
- Add a 0.5 × 45° lead-in on the tub chin wall's lower inner edge (about z -3.6), across each key opening's X span.

**Key openings**
- |dx| ≤ 5.30, **y -7.95** to -4.225, straight through the skin, R0.5 corners, 0.3 × 45° chamfer at the face.
- The +Y edge is flush with the rail face. The chin edge overhangs the chin wall by 0.25 (the retention ledge until test 2).

**Hook slots (test 2)**
- Two per key in the chin wall's inner face, |dx| 3.20–5.40 (4.26) or 2.65–5.40 (3.68), back at y -8.80 (4.26), -8.95 (x3std), -8.85 (x3ls): 8 per tub.
- Open to the rim, up to a flat roof: the skin's underside (z 4.98 on the 4.26, 3.47 on x3ls) or, on x3std, z 2.67 inside the chin wall (2.27 until 2026-10-10).
- Chin wall left behind each slot ≥ 0.45 in every printed layer up to the rim (both sizes: the tub has no seam chamfer on the chin over the key row, from 0.50 before the first slot to 0.50 past the last, `KEY_SLOT` relief; with it the rim layer printed nothing behind the slots, a one-layer slit into them in the seam's V), and ≥ 0.50 of material over the roof at the back (`mechanics.key_hooks`).
- In the face-down print a slot is a plain vertical slot and its roof is the top of the layers below it: no bridge, no overhang.

**Add**
- Solid skin from the opening's +Y edge (-4.225) to the old opening edge.
- The rail (§2): 5 ring segments (the left one runs on to the side wall), 4 open-seat centre segments, 8 cheek slots.
- The side-wall hole and the gate slot (§2; no countersink).
- The 5 webs (§2).

**Tub print (face-down)**
- Rail, webs and ledge are walls grown from the skin.
- The slot roofs are print-top surfaces (floors), not bridges, on the layer grid: z 3.60 on the 4.26, and on the 3.68 the skin's underside, 3.47 (since 2026-10-12; 3.15 before, which printed at 3.20 / 3.07).
- The ring bores and the side-wall hole are teardrops pointing print-up. The open seats print with their mouth facing print-up, leaving a 0.6-chord arc on lip B as the only real overhang.

**x3 std**
- The chin web (underside z 2.85, y ≥ 1.5) is untouched: every new part stays at y < 0.
- Assert that the chin wordmark engraving leaves at least 0.6 of plastic over the slot roofs.

**Lid**: only the -1 mm chin shift. The midplate is unchanged.

## 6. Forces and travel (replaces `mechanics.key_forces`; `s4/forces4.py`)

Model:

  P·(4.95 − μ·0.80) = Fs·2.95 + μ·Fs·0.58 + μ_pin·0.875·√(P² + Fs²)

The finger force is F = P·g(e) + D, where:
- g is the guide-tilt factor: g = 1/(1 − 2μ|e|/(Lg ± μ·(y_A + y_B − 2·y_pad))), with e = y_press + 7.45.
- The guide contacts are y_A -8.05 (foot) and y_B -4.225 (+Y face).
- D is the tuned maximum drag. Since test 2 there is no drag: D = 0, and the case READMEs' "Forces" give the numbers (the 4.26 at the centre, μ 0.3: 1.04 / 1.53 / 1.61 / 2.42 N for the four switch forces below).

Key force without the fingertip model, μ 0.3, cap at y -7.7 / -6.2 / -4.6 (range 4.26 to x3 std):

| switch | centre (-6.2) | chin edge / top edge |
|---|---|---|
| MJTP 1.27 N | 1.11–1.14 | 1.02 / 1.30–1.48 |
| MJTP 1.86 N | 1.59–1.65 | 1.46–1.47 / 1.88–2.14 |
| TS365 1.96 N | 1.67–1.74 | 1.54–1.55 / 1.98–2.26 |
| TS365 2.94 N | 2.48–2.59 | 2.28–2.30 / 2.94–3.36 |

- At μ 0.45 the centre values rise by about 18%. The x3 std top edge then reaches ×1.95; that is the zone to avoid pressing.
- Without friction the ratio is 0.596 × Fs.
- Today's design at 1.57 N needs 2.21 / 2.55 / 3.11 N with the finger model (centre). The new one needs about 1.35 N at the same switch force before the finger model, which check-cc puts at ×1.07–1.24 for caps at least 1.2 proud.
- Travel at the key: 0.41 to the click (0.40–0.44 across tolerance), 0.73 to the switch bottom.
- There is no dead travel and no rest preload with the case face up. Face down (since test 2) the keys hang on their hooks, and the first press travels about 0.5–1.5 before the click.

## 7. Assembly (c), tub face-down

> **Superseded 2026-09-28 by SPEC2 rev 3:** the rod's left stop is a printed side gate in a slot in the -X wall (no M2.5 screw, no countersink); rod 63.25 +- 0.2 with a pencil-taper tip to a 0.8 flat and a square tail; removal with a paperclip in the gate's pull hole. Steps 1, 5 and 6 and disassembly step 2 are edited to match; the cranks are no longer held while the rod goes in.

0. **Optional fit check (test 2).** Print the tub's chin strip (one key opening with its two hook slots, a web, the chin wall and a rail-face stub: `coupon-chin` on the 4.26, `coupon-strip` on the 3.68) and one key of the build. The key slides up its slots from inside and stops level, 2.5 proud (the 4.26: 2.4). Nothing is chosen from it. (Until test 2 this step was mandatory: four coupon keys with `KEY_DRAG_BUMP` 0.07–0.22 set the drag.)
1. **Prep.**
   - Straighten, cut (63.25), taper and check the rod (§2); its tail cut square. Print two gates.
   - Ream the 8 crank bores with a 1.9 mm drill; the rod must slide and turn freely.
   - Print crank-T for JLC boards (TS365ZJ) and crank-M for MJTP1117 boards.
2. **Support the tub.** Lay it face-down on a soft cloth (or on a spacer about 3 mm thick under the screen area, or with the chin over the table edge), so the caps can hang out 2.5 (the 4.26: 2.4). **Keep it face down from step 3 until the board is in (step 7).** Turned face up before that, the keys sink (up to 2.1 below the face once the rod is in; the 4.26: 2.2) or, before the rod, fall in; turned face down again, they come back.
3. **Keys.**
   - Put each key in from inside, cap first, with its hooks in the two slots of its opening (it fits only one way round).
   - Let it slide out until both hooks stop under the roof: it stands 2.5 proud and level (the 4.26: 2.4).
   - This order is required: at rest height the keys block the crank's path.
4. **Cranks.**
   - Drop each crank in from the open back (along +Z) with its cheeks into their slots, pad toward the face, nose toward the board side.
   - Each comes to rest on its key's pusher, the key on its hooks: every crank at the same angle, about -11° (-11.25 on the 4.26, -11.4 on the 3.68), and the board later goes in without touching a plunger.
5. **Rod.**
   - From the -X side, lay the tapered end in the channel at the bottom of the gate slot and push it straight in, through the side-wall hole and the left ring.
   - Don't hold the cranks: each lies on its key and the tapered tip picks it up. Feed on through cheek, centre seat, cheek and web ring until the square tail is flush with the case side or just inside it.
   - Check that each crank turns freely, by hand from its key to its stop. Since 2026-10-12 nothing catches on the way; before, each cheek's top corner scraped the slot roof at about 40° (the crank well, above).
6. **Gate.** Drop it into the slot from the open back, bevel down, small hole outward, and press its top level with the rim: its bevel pushes the rod the last 1.75 to its stop. If it stops proud, lift it out, push the tail a little further in and press again. The lid's rim closes over it (step 8).
7. **Board.**
   - Lower it onto its bosses. Each plunger slides past its nose. A TS365 on crank-M cams the crown back; the key above is free.
   - Fit the screws.
8. **Close.** Fit the lid and its screws.
9. **Turn it over.** Face up, each key settles onto its crank and the crank onto its switch (about 1.5 proud; the 4.26 about 1.35); a tap settles them. Face down they drop 1.00 back onto their hooks.

**Disassembly** (superseded 2026-09-28 by SPEC2 rev 3: step 2 now lifts the printed gate out with a paperclip; no side screw)
1. Take off the lid and remove the board screws. Lift the board: the plungers slide off the noses.
2. Hook a straightened paperclip into the small hole in the gate's outside face and lift the gate out toward the back. With a small screwdriver, push the rod's right end (exposed at X 56.3-61.4) toward -X until it stops at the last ring; 2.7-3.1 mm then stands out of the slot: pull it out with fingers or flat-nose pliers.
3. Lift the cranks out along -Z.
4. Push each key in from the face. It drops out on the inside.
5. A rod can be re-used if it still rolls straight.

## 8. Checks to add (d), with pass criteria

**1. Static interference** (all four builds, θ at rest for δ -0.2 / 0 / +0.2, both switch envelopes, matching variant)
- No overlaps among tub, lid, midplate, strip/ribbon parts, board, switch, rod, gate, crank and key.
- Designed contacts are the only exceptions: crown/pusher, nose/plunger, rod/seats, rod/gate flat, gate/slot floor and lip faces, rod/+X wall and key/guide (until test 2 also bump/chin wall; the hooks touch nothing at rest).
- Minimum gaps must match §3 and §4 to within 0.02.

**2. Crank sweep** from -13° to +16° with the key riding the crown (key Z = crown centre + 0.6), belly included.
- ≥ 0.10 everywhere, except the leg and belly to the rail (≥ 0.06 at -13°) and the cheek to a board edge at -0.4 (≥ 0.07).
- ≥ 0.20 inside -4° to +13° (measured minimum 0.236, leg and belly to the rail).
- Plunger check done kinematically, with the plunger face following the nose: ≥ 0.35 (belly 0.448; the unchanged leg body 0.37).
- The crown is the only key contact.

**2a. Free swing (2026-10-12; `case-426` `build.crank_free_swing`, `case-368` `crank_checks.free_swing`).** The board is out and the tub face down, as in assembly. Each crank is turned from lying on its key to its first tub contact going + (CAD, on the axis: the nose on the rail's +Y face, about +98 / +106).
- What is swept: the crank across its cheeks' X bands, against the tub's shadow there (the slot, its roof, the skin).
- Both parts as sliced: the face-down tub in 0.2 layers from the face, the crank in 0.2 layers from its pad end, each layer its mid-plane's section.
- The crank grown 0.075 a face (`KEY_FDM` part / 2), then moved toward the face (+Z) by the bores' play. That is (1.90 − 1.72)/2 on the crank plus (1.93 − 1.72)/2 for the rod in its ring bores: 0.195.
- Pass: ≥ 0.05 all the way. The old 3.15 roof fails it: -0.150 on the 4.26, -0.280 on the 3.68, at about +40. The deeper slots pass: 0.250 / 0.120. The drawn and as-sliced gaps on the axis are reported too.

**3. Key sweep to over-travel.** The key moves from the stop (+1.00, `KEY_W_OUT`, since test 2; +0.97 x3 / +2.48 4.26 before) to -1.31 (+16°), and on down to -3.4 (a key sunk before the board is in).
- The key's +Y face stays on the guide over at least 2.5 of Lg.
- The hooks stay in their slots and meet the roof only at the stop; no key-tub overlap anywhere down to -3.4 (until test 2: the bump on the chin wall below the ledge for all rest positions within ±0.84).
- The foot never meets the crank.

**4. Assembly paths**
- (a) Rod axial path from X -4.09 to 61.41: side hole, 5 rings, 4 open seats and 8 cheek bores all ≥ Ø1.90 on the axis. Nothing else within 0.1 of the rod.
- (b) Each crank along +Z at θ 0 and +10, with keys at the stop: ≥ 0.3 to rail and keys.
- (c) Board along +Z: the plunger touches only the nose crown's flank, at a contact normal at least 40° from ±Z. Check the TS365 worst case (tip -2.4, centre -1.8) on crank-M, and the MJTP on crank-T.
- (d) Key along +Z from inside, hooks in their slots: nothing touches until the hooks reach the roof at the stop (until test 2: only the bump touched, through the chin-wall lead-in).

**5. Force model** (§6) across μ 0.3 and 0.45 and both switches' ranges:
- At μ 0.3, centre force ≤ 1.3 N for MJTP 1.27 and ≤ 1.7 N for MJTP 1.86.
- Top-edge factor ≤ 1.6 at μ 0.3.
- 2μe/Lg < 0.8 everywhere on the cap.
- Travel to the click 0.35–0.50.

**6. Preload window**
- Rest load on the plunger: since test 2 gravity only (the key and crank, a few mN). It must be less than 0.3 × the minimum operating force (0.38 N MJTP, 0.59 N TS365). (Until test 2: ≤ 1.68·D_max + pin friction ≤ 0.25 N, and D_min ≥ 4 × the key's weight.)
- Key proud 1.0–2.0 at δ ±0.2 with the matching crank. On the 4.26 `mechanics.key_proud` checks it (since 2026-10-03, in `build.py`'s PASS / FAIL list): 1.02–1.69 at its 1.35 cap, the floor (§4, Height proud).
- Report the wrong-variant shift.

**6a. Hooks and slots (test 2, `mechanics.key_hooks`; the design study's missing checks)**
- The stop engages at `KEY_W_OUT`: 0.05 past it only the hooks meet the tub, under the roof; no key-tub overlap at rest, pressed to -3.4 or 0.02 short of the stop, centred and at the key's X and chin play.
- `KEY_W_OUT` ≥ the worst rest lift (0.70) + the chain's print (0.14) + the stop's (0.15).
- Chin wall behind every slot ≥ 0.45 in every layer up to the rim, across the slot's whole width as sliced; ≥ 0.50 over the roof at the slot's back.
- X-tilt on the hooks ≤ 1.0° for 0.1 between them; the crown runs under the whole cap.
- Pull-out: a flat bearing under the roof net of the FDM corner radii; unhooking needs +Y, which the rail leaves 0; hook roots at 5 N ≤ 8 MPa shear, ≤ 25 MPa bending in the layer.
- Hooks (and the root) against the crank over -20° to +60°, the key riding the crown and at its stop: ≥ 0.10.
- Gravity in each pose (face up, face down, on either edge): the net force at the key and what holds it.

**7. Stress at a 20 N over-press**
- Rod bending ≤ 20 MPa (rodfe.py, elastic bearings; stiffness 1× and 1/3×).
- Rod shear ≤ 8 MPa; cheek and seat bearing ≤ 10 MPa.
- Crossbar with belly, as a beam along X pinned at the cheeks: ≤ 25 MPa in-layer. Torsion plus shear on the layer planes ≤ 8 MPa.
- Crossbar root (y -6.2) and leg root, across the layers: ≤ 12 MPa.
- Crank cheeks (test 1, `mechanics.cheek_stress`; the numbers are in §3):
  - the ring closed round the rod at |dx| 4.65, with a wall over the bore ≥ 0.80 and ≥ 0.70 at the least (0.80 / 0.75);
  - across the layers at the largest click: ≤ 12 MPa (4.6 / 5.7 / 4.9);
  - the least layer area through the rod in the ring zone (y planes -3.0 to -1.4): ≥ 3.4 mm² (3.87). A geometry guard, not a stress figure;
  - at 20 N: layer average ≤ 25 (18.8; peak 24.5), a stated exception to the 12 above. The band under the 45° roof cannot grow: the key's cheek zone and the roof leave 0.142 at θ 16°. It is accepted because the largest click is 2.1× (x3std) to 2.6× (4.26) under 12, and a band cracked by a jab still leaves the rod captive: the ring is closed and its fill side holds.
- Hook roots at a 5 N pull-out (§8 item 6a; until test 2: leaf static stress ≤ 8 MPa at interference 0.30, across the layers).
- Report the plunger load (33.6 N) against the switch's rating.

**8. Slice read-back** (slice_check.py: extrusion must be present, or absent where stated, in every layer through each box)
- Tub:
  - each web (X band, y -8.1 to -4.3, z from the skin down to 1.1);
  - the rail in every segment, with the full ring around each ring bore;
  - the open seat's lip A (y -1.6 to -1.5, z 0.7–0.85) and lip B (y -2.7 to -2.6, z -0.4 to -0.3);
  - over the slot roofs: on the 4.26 the rail (z 3.65–4.93, since 2026-10-12); on the 3.68 the skin, and the slot open up to it (z 3.47; until 2026-10-12, the 0.32 of rail over a 3.15 roof);
  - the 0.25 ledge;
  - the chin-wall lead-in;
  - the side-wall hole and every ring bore free to at least Ø1.90 (read back from the G-code perimeters).
  - since test 2, each hook slot empty from the rim to its roof, the chin wall behind it and the material over its roof present, in the tub and in the chin coupon (3.68: the wall from the rim up, across the slot's whole width in every layer); no support, bridge or overhang line round the slots.
- Key (on its -X end since test 1; the hook key since test 2):
  - each hook present in every layer through it, covering ≥ 0.75 of its section; the +X hook's lead and the root present; nothing chin-side of the cap's face over the hooks;
  - the pusher's chin end present, and the chin side cut back above it;
  - the first layer ≥ 7.5 mm² and inside the model's outline;
  - no seam on the button face or on the chin face above the device face;
  - no supports: nothing starts in mid-air, no layer reaches more than 0.5 past the one below, and no support, bridge or overhang line anywhere in the key;
  - the fit as sliced: the hook tip to the slot's back, the hook under the roof, and `KEY_W_OUT` as sliced over the worst rest lift.
  - (Until test 2: the leaf, the slit, the roof slot, the gap under the leaf and the bump, and the drag with the leaf as sliced.)
- Crank:
  - bore wall of at least 0.68 around each cheek bore;
  - crown, nose and belly;
  - first layer at least 1.0 wide;
  - test 1: the ring closed where the C was, the fill present, the lip's C still open; the sliced cheek ≥ 0.90 of the designed section in every layer through the bore (y -3.0 to -1.4), which also shows the Arachne walls are in.
- Crank bores: the printed free diameter must be ≥ 1.80 before reaming.

**9. Shared-part assertions** (§9).

## 9. Shared-part rule (e)

- **3.68.** The keys become tub-specific:
  - the standard build ships key-x3std (height 6.17; 5.77 until 2026-10-10);
  - the light-strip build ships its tub plus key-x3ls (height 6.97).
  Every other non-tub part (crank-M, crank-T, lid, midplate and the rest) must stay byte-identical between the two builds. The build asserts this, with the keys whitelisted.
- **4.26.** key-426 is shared by both builds (same face, 6.00). All non-tub parts stay identical.
- **Crank.** crank-M and crank-T are identical in all four builds; export them once per package.
- **Rod and gate.** The rod is a cut instruction (63.25 of straightened 1.75 filament), not a part. The gate is a printed part, identical in all four builds (print 2: one spare). No screw (SPEC2 rev 3).
- **Coupon.** Export the chin strip with its two hook slots per tub (the 4.26's `coupon-chin` is shared; the 3.68's `coupon-strip` is per build), printed with one key of the build: an optional fit check (test 2). The four bump-offset coupon keys went with the drag leaf.

## 10. Open items and risks

- **TS365ZJ.** The body width (assumed ±3.65), plunger width (up to 3.7) and plunger height are from paper. Measure a real part (tip to signal-pin row, plunger height and width) before cutting crank-T.
- **Switch rating under over-press.** Neither switch has a published static limit. At 20 N the plunger sees 33.6 N; the SKHL's 29.4 N limit is reached at a 17.5 N press. This is an accepted, reported risk: no tub-fixed stop works across δ ±0.2 plus the TS365 tip ±0.2.
- **Hook keys (test 2, not yet printed).** The drag leaf is gone (it depended on the coupon; in test 2 it held keys tilted, low or stuck). What the hooks leave open:
  - **Face down** (on a table, or reading lying on your back) every key drops 1.0 onto its hooks, and the first press travels 0.5–1.5 (1.8 at worst) before the click: the same on all four, but not "no free travel". `KEY_W_OUT` sets it; it can shrink only if the real switch scatter is smaller than the datasheet's.
  - **The rest follows the switch:** key to key ±0.37 with the TS365's ±0.2 tip tolerance (±0.17 if the part holds ±0.05), and the row ±0.34 with the board's position. A low key stays low, but sits still and clicks in the same place.
  - **Upright** (chin down, face vertical) only the key's friction on the chin wall holds the chain closed, 1.2–2.3× the crank's opening pull: small in absolute terms, so vibration can walk a key up to its hooks.
  - **No inward stop before the board:** keep the tub face down from the keys until the board is in (§7).
  - **x3std:** the hooks bear 0.35 on a roof inside the chin wall.
  - **3.68 seam:** the tub's half of the seam's V is left off the chin over the key row (x 5.6–54.4), so the V is half as deep there. With it, the wall behind each slot thinned to 0.17–0.37 in the rim's last one or two layers, which Orca does not print: eight slits into the slots, above the lid's rim (found by slicing, 2026-09-30).
- **Side gate** (SPEC2 rev 3; was a side-wall screw). The gate's flush 2.5 x 6.2 web and its 1.3 pull hole show on the -X side face at y -2.5, about 6.7 up from the case's chin edge.
- **Crank knock-off.** A 1.10 × 10.5 first layer, 7.00 tall. Fall back to a raft if the test print loses one (§3). None tipped in test 1.
- **Rod straightness.** Straighten it and apply the roll test (§2). A bowed rod binds in the rings rather than falling out, but it also binds the cranks.
- **The slit on the cap: fixed in test 1.** Cap-down, the slit showed on the cap top (stage3.md step 1 had rejected the alternatives). The key now prints on its -X end, and the slit stops under a closed roof 0.70 (x3std 0.50) below the face, so the button face has no slit. The costs: the face is a side wall (fine layer lines, not the PEI texture), and the key stands 10.0 tall (9.9 until 2026-10-03) on about 8–16 mm². (The leaf, which bent across its layers, went in test 2, and with it the slit.)
- **Crank cheeks: fixed in test 1.** The open C's jaw cracked off at the bore and some cranks came off the rod. The cheeks are now closed rings (§3). The 20 N layer average, 18.8 MPa, stays over the 12 MPa rule for crank roots: an accepted, reported exception (§8 item 7).

## 11. Review responses (review.md, 2026-09-26)

Kept as the record of stage 4. The drag leaf, its bump, the ledge stop and the tuning coupon (C3, C4, P7, P8) were replaced by the hook keys in test 2 (§4).

**Confirmed problems**
- **C1 (seats can't snap): agreed. Fixed with the reviewer's alternative, the axial rod. The keeper bar was rejected.**
  - A keeper along X must cross all four switch zones. There the TS365 worst housing leaves only a 0.78 inscribed width inside the mouth, and the cheek sweep needs the 296–347° sector.
  - The section common to both zones is 0.31 mm² with a 0.27 inscribed width (`s4/c1.py`), below the 0.45 print limit. A variable keeper would need pockets in every centre segment.
  - The axial rod gives full capture with no snap and no keeper. It costs one hole and one M2.5 screw (since SPEC2 rev 3: a slot and a printed gate, no screw).
  - The tub's end gaps allowed it: the left block runs on to the side wall, and the right gap (5.1) is kept for push-out.
- **C2 (crossbar over-stressed): agreed, belly adopted.** I get 24.5 MPa in-layer with the belly (the reviewer got 10.4 + 13.5), after the -7.70 clip, down from 62.
  - Torsion: my estimate is about 2 MPa. The reviewer's 15 MPa used the stage-3 section and the key-load arm. Either way it is under the 8 MPa limit with the belly.
  - The static plunger-box overlap in the reviewer's approach vanishes kinematically: ≥ 0.448, the same as today's leg body.
- **C3 (bump number): agreed.** The tip is at y -8.32 (4.095 from the +Y face). `KEY_DRAG_BUMP` is now defined as the interference, 0.12.
- **C4 (drag window): agreed.** The tip flat is now 0.60 (3 layers), and the coupon step is mandatory (§7 step 0). The per-build table uses the tuned window, and the untuned extremes are reported.
- **C5 (contradictions): agreed, all fixed.**
  - Check 5 is restated for MJTP 1.27 (≤ 1.3 N) and MJTP 1.86 (≤ 1.7 N).
  - The chin wall's outside is -9.2 (+1.0 of bezel).
  - The slot roofs are floors.
  - `forces4.py` replaces `forces3.py`, with guides at -8.05 / -4.225, the cap at -7.80 to -4.225, and the tuned drag.
  - `forces.md` is declared absent, and `layout.json` is regenerated.

**Plausible risks**
- **P6 (rod straightness): adopted** (§2).
- **P7 (slit fuses): adopted, with a change.** Only the body-side edge gets the 0.3 chamfer, plus EFC 0.1. The leaf keeps its 0.5, and I did not use a 0.6 slit because it would thin the S-zone wall to 0.45. The leaf's top edge also loses the cap chamfer, which would have left a sub-0.45 sliver.
- **P8 (keys pop or walk): adopted, with a change.** Square bump top, 0.25 ledge and chin-wall lead-in. The opening's chin edge moved to -7.95 as proposed, but that would have left 0.05 of clearance to the cap. So the cap and leaf chin face moved +0.10 to -7.80, keeping 0.15, and the bump grew to 0.52. The stop sits 0.97 / 2.48 above rest.
- **P9 (crank knocked off): partly adopted.** Not the sled at the pad face: its cut residue lands on the pad end's lower corner, which sets the -13° chin gap (0.111 → 0.013 with 0.1 of residue; `s4/chin13.py`). Instead the crank is clipped at -7.70: the bed strip widens to 1.10 and the chin gap grows to 0.196. A raft is the fallback.
- **P10 (board binding): adopted.** The rail's +Y face is at -0.45. The cheeks also had to be trimmed to -0.75: at a board edge of -0.4 they overlapped by 0.014, and now clear by 0.071 (the trim is -0.70 since test 1; the current sweep gives 0.134).
- **P11 (over-press into the switch): agreed.** It stays a reported risk (§10).

**Sound items**
- Agreed on the lever (1.678), the load direction (210.8°), rod stress, the drag take-up argument, board insertion, the other clearances and tub printability.
- The stage-4 changes leave these unchanged. The rod supports keep the same X positions, and the new ring walls are ≥ 0.65.
