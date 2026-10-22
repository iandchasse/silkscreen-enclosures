# SPEC2 rev 3: side gate (replaces the M2.5 side screw)

<!-- Kept in the repo 2026-09-28 from the working copy. Paths in the text are as they were then: the per-part
print files are now print/4.26/ and print/3.68/, the case projects enclosures/case-426 and enclosures/case-368. -->

**Status (2026-09-28):** built into both case projects (Rev L) and checked; not printed. This is the spec the code
cites as "SPEC2 rev 3". It replaces the M2.5 side screw of [BELL-CRANK-SPEC.md](BELL-CRANK-SPEC.md) with a printed
side gate; where the two differ, this one holds. Each case's README ("Bottom keys") says how to print and fit it;
`print/<size>/ROD.txt` is the short version.

This revision answers review 2. Rev 3's own runs were (the working files, the review and the earlier revisions were not kept):
- `c1_gate`: gate and slot in plan, bearing and stresses at every Y position the gate can take.
- `c1_ends`: the round cavity ends checked against the built tubs.
- `c1_lid`: the lid checked over the slot footprint.
- `r2_nocradle` (outputs `r2n_*`): review 2's crank-rest model run with today's cranks and no cradles.

The "Review responses" section at the end gives the reasons for each change.

**Rev 3.1 (2026-09-28, after verify1):** the gate's top is 0.20 under the rim (was 0.10) and its top chamfer 0.20 (was 0.30). At 0.10 the lid came within 0.025 of a gate seated centred in X (the 45 deg floor lifts it 0.075) and met one sitting on its flat (+0.15 X), and as printed the floor's stairs lift the gate 0.05-0.13, so the lid could land on it. Now: 0.200 on the lips, 0.125 centred, 0.050 on the sliver. The chamfer still ends at z -3.35 (level with the seam chamfer), so the wall over the pull hole is 0.90, and 0.70 at the face. Mechanics are unchanged.

## Why this concept

Scores are 0-5, weighted R2/R3/R4 x3, R6 x2, and R1/R5/simplicity x1 (maximum 70).

| | R1 | R2 | R3 | R4 | R5 | R6 | simple | total |
|---|---|---|---|---|---|---|---|---|
| C1 lid block + tooth + leaf | 5 | 2 | 2 | 3 | 4 | 3 | 3 | 39 |
| C2 drop-in module | 5 | 2 | 3 | 2 | 4 | 2 | 1 | 35 |
| **C3 side gate (rev 3)** | 5 | 4 | 4 | 4 | 4 | 4 | 4 | **57** |

- **C1:** the pin push stays. Its axial stop is held by the lid, so a sideways over-press (9 N, 17.6 N extreme) loads a lid part. The 3.68 leaf runs at 1.6-2.0 % strain.
- **C2:** opens all 9 bearings. Ring stress rises 16-17 %, and the webs have to be extended even to get there. With the lid on, the rod floats 0.3 toward the plungers. Before the lid, only gravity holds it (15 deg of margin), and it needs a carrier tool.
- **C3:** every press load stays in the tub. The rings are unchanged, and the axial load goes rod -> gate -> tub lips. There is no pin, no hand-holding and no tool, and gravity keeps the gate seated up to a 90 deg tilt.

**Changes in rev 3:**
1. **Gate and lips (C1).**
   - Dimensions: lips 1.10, flange 0.65, web 2.50 with 0.10 per side in the mouth.
   - Round cavity ends (R0.40 semicircles) replace the R0.30 lip-root fillets. The flange's outer edges get only a 0.05 break.
   - Flat bearing is 0.30 per side, or 0.20 at the worst Y position the gate can take.
   - Lip SF at 27 N is 2.32 centred and 2.08 at the worst position (on 25 MPa). The gate flange is 3.68 and 2.97 (on 50 MPa, in-plane).
2. **Pull hole (C2):** d1.30 x 1.0 deep at z -2.00, with walls 0.60 / 1.00. The tool is a straightened paperclip.
3. **Cradles and crank cheek cut removed (C3).**
   - With or without them the cranks settle on their keys, at the same place: 0.252 off the rod's line on the 4.26 either way, and 0.200 without them (0.218 with) on the 3.68.
   - The cranks are now unchanged from today.
4. **Rod tip:** a pencil taper ending in a flat about 0.8 across. It is neither a chamfer nor a needle point.
5. **Checks and README:** section 9 is renumbered. Checks 2, 3, 5, 8, 9 and 10 are rewritten and check 7 is new (C1, C3, C4). README steps 5-7 are rewritten (C3, P2, P3).

**Kept from SPEC2:**
- The rod channel is cut through the slot floor, so the tip is carried across the slot from below.
- The gate's flat ends at z 0.90, putting the bevel tip at 2.65.
- The tongue notch.
- No geometry change for the edge press.

---

## 1. What changes

The numbers are the same in all 4 builds unless a line says otherwise.
- **Tub:**
  - Adds: the gate slot (mouth, round-ended flange cavity, bevelled floor), the rod channel through the slot floor, the sliver lead-in and the tongue notch.
  - Removes: the countersink.
  - Unchanged: the rail, rings, open seats, cheek slots and webs.
- **Gate:** a new printed part, one per case, identical in all 4 builds.
- **Rod:** 63.25 long. The tip is tapered to a small flat and the tail is cut square.
- **Unchanged:** crank-M, crank-T, keys, lid and midplate.
- **Screws:** only the lid's (3 x M2x10 on the 4.26, 3 x M2x8 on the 3.68; 4 x M2x8 since 2026-10-13, two of them in the chin's corners: `case-368/README.md`, "Four screws"). Socket head caps (ISO 4762), Ian's; a pan head (ISO 7045) also fits (the 4.26's counterbores 2.0 deep since 2026-10-13: `case-426/README.md`, "Socket head screws").
- **Shared-part rule:** kept.
  - On the 4.26 only the tub differs between builds; on the 3.68 the tub and keys do.
  - The gate depends only on `X0` (-4.09 in both sizes), the rim and the rod axis.

## 2. Sketches

Both sketches are drawn with the case face down, which is how it sits during assembly.

**A. XZ at y -2.50 (gate and rod). +Z (toward the screen) points down the page, which is the direction of gravity during assembly.**
```
 z -3.75 ==rim==+------------+====  lid's outer lip (top -3.75 over X -3.7..-2.8)
 z -3.55        | GATE top   |      0.20 under the rim; 0.20x45 on the web's outer top edge
 z -2.00        |(o) pull    |      d1.30 x 1.0 deep, in the web's outer face
                | web  |flng |  s |
 z -0.28        | 1.10 |0.65 |  l |<== square rod tail at X -2.34 (home) ====> rings, cranks
 z  0.60        |      |     |  i |    rod axis
 z  0.90        |______|flat_|  v |    flat inner face ends, bevel starts
                 \    bevel  | e |
 z  1.55 . . . . .\. . . . . |_r_|   floor at the lip face (X -2.99); channel bottom is 1.65
                   \  45 deg |   |   the d2.10 teardrop runs through the whole wall and the floor
 z  2.65    tip ->  \________|   |   floor = bevel plane; the gate sits on it
        X -4.09  -2.99    -2.34 -2.19 -1.41
```
**B. XY plan at z 0.6, seen from the back (+y up the page):**
```
  y -0.25            (  R0.40  )            round cavity end, about (X -2.59, y -0.65)
  y -0.65 ///////////+---------+----+
  y -0.80  lip 1.10  |FLANGE   |    |       flange X -2.99..-2.34, y -4.20..-0.80
  y -1.15 +----------+ <-bears |  s |       mouth X -4.09..-2.99, y -3.85..-1.15
  y -1.25 |  WEB     |  here   |  l |       web   X -4.09..-2.99, y -3.75..-1.25 (0.10 per side)
  y -2.50 |  2.50    |=========|==i=|==o== rod ==>
  y -3.75 |          |         |  v |
  y -3.85 +----------+ <-bears |  e |
  y -4.20  lip 1.10  |         |  r |       cavity X -2.99..-2.19, straight y -4.35..-0.65
  y -4.35 ///////////+---------+----+
  y -4.75            (  R0.40  )            round cavity end, about (X -2.59, y -4.35)
        X -4.09     -2.99    -2.34 -2.19 -1.41
```

## 3. Tub (tub.py and joint.py, both projects)

- **Delete:** `ROD_COUNTERSINK_D` (4.26), `SIDE_SCREW` (both), and the countersink cone in `rod_hole()`.
- **New param `GATE_SLOT`, the gate slot:** `lip=1.10`, `mouth=(-3.85, -1.15)`, `cavity=(-4.35, -0.65)`, `end_r=0.40`. It is derived from `X0`, and on the 3.68 also from `WALL_X0`.

| feature | X | y | z |
|---|---|---|---|
| mouth | -4.09..-2.99 | -3.85..-1.15 | rim (-3.75) to floor |
| flange cavity | -2.99..-2.19 | straight over -4.35..-0.65, with R0.40 semicircular ends centred (X -2.59, y -4.35) and (X -2.59, y -0.65), reaching -4.75 and -0.25 | rim to floor |
| floor | 0.90 + (-2.34 - X) for X <= -2.34; 0.90 over -2.34..-2.19 | whole slot | 2.65 at the face, 1.55 at X -2.99 |

- **Lips:** the wall beside the mouth, X -4.09..-2.99 (1.10 thick), 0.50 from lip tip to cavity end.
  - Each lip's +X face runs straight into its cavity's round end, which acts as the root relief. There are **no fillets** in the cavity corners, so nothing is left for the flange's corners to hit.
  - c1_ends: the tub is solid today over both round-end volumes in all 4 builds (void 0.0000 mm2), with at least 3.0 of wall beyond each arc.
- **Rod channel:** the existing `ROD_HOLE_D` 2.10 teardrop (flat 1.15, pointing -Z), from `X0` to the inner face at -1.41, cut through the floor.
  - It breaks the floor only at X > -3.09. There, put 0.30 x 45 deg chamfers on both edges.
  - At the face the floor is 1.0 below the channel, and its 45 deg ramp lifts a drooping tip back in.
- **Sliver** (X -2.19..-1.41, 0.78 thick): keep the teardrop and add a 0.50 x 45 deg lead-in on its -X face. The left ring from -1.41 is unchanged.
- **Tongue notch** (in `joint.tub_cuts`): the cavity footprint, round ends included, is cut up through the tongue.
  - The tongue's outer face moves from X -2.34 to -2.19 over y -4.35..-0.65 and follows the arcs out to y -4.66 and -0.34.
  - `TONGUE_RUNS` and the lid's groove are unchanged.
  - c1_ends: the tongue is X -2.34..-1.41 over the whole range in all 4 builds.
  - c1_lid: the lid has no material below the rim over the slot footprint (0.0000 mm2 in all 4 builds).
- **Nothing else in the rail changes.** There are no cradles.

## 4. Gate (new; `gate()` in keys.py for the 4.26 and crank.py for the 3.68; param `GATE`)

- **Shape:** a T extruded in Z.
  - Web: X -4.09..-2.99, y -3.75..-1.25 (2.50).
  - Flange: X -2.99..-2.34, y -4.20..-0.80 (3.40).
  - Top: z -3.55 (0.20 under the rim), with a 0.20 x 45 deg chamfer on the web's outer top edge (to z -3.35, level
    with the tub's seam chamfer).
- **Inner face:** flat at X -2.34, from the top down to z 0.90.
- **Bottom:** a 45 deg bevel plane from (X -2.34, z 0.90) to (X -4.09, z 2.65). The tip stays sharp; see section 10.4.
- **Edges:**
  - 0.40 x 45 deg on the flange's bed-side (X -2.34) vertical edges, for elephant foot.
  - Only a 0.05 break on the flange's outer (X -2.99) vertical edges, because that face bears on the lips.
- **Pull hole:** d1.30, 1.0 deep into the web's outer face, centred at (y -2.50, z -2.00).
  - Walls are 0.60 each side in Y and 0.90 above.
  - At the outer face the wall above is 0.70, after the top chamfer.
- **Fit:**
  - The web has 0.10 per side in the mouth (Y). It locates the gate.
  - The flange has 0.15 per side to the cavity's straight part and 0.15 behind it (X).
  - Whatever Y position the gate takes (+-0.10), the flange ends stay in the straight part, off the round ends.
- **Bearing on the lips (c1_gate):**
  - The flange's outer face and the lip faces are coplanar at X -2.99: zero overlap and zero travel at rest.
  - Centred, it bears flat at y -4.15..-3.85 and -1.15..-0.85, which is 0.30 per side.
  - At the +-0.10 extreme the bearing is 0.40 on one side and 0.20 on the other.
- **Seat:**
  - The web's full 2.50 sits on the mouth floor over X -4.09..-3.09.
  - Under the flange, the floor beside the channel adds up to 1.2 in total over X -2.45..-2.99.
  - Within 0.1 of the flat the bed-side chamfers put the flange over the channel, so it bears nothing there.
  - The lid lip is 0.20 over the top on the lips, 0.125 seated centred in X and 0.05 with the flat on the sliver.
- **Rod-end coverage (unchanged):** the flat covers the rod end past its axis by 0.125 face down and 0.375 face up.
- **Print:**
  - Inner face on the bed, so the first layer is the flange and there are no ledges.
  - The bevel is a 45 deg overhang and the pull hole is vertical.
  - The thinnest wall is 0.60. The part is about 25 mm^3. Print two.
- **Outputs:** `print/gate.stl` and `.step`, and `out/<build>/gate.stl` in the installed pose.

## 5. Cranks and keys: unchanged

- No cheek cut and no new parameter. Crank-M and crank-T stay exactly as built today.
- Where a crank comes to rest once dropped in with no rod (r2n, today's cranks and tub, keys at their stop +2.48 / +0.97, gravity +Z):
  - **4.26:** it lands on its belly at dz +0.11..+0.41 (+0.33..+0.41 at dy 0).
    - Frictionless, it rests at theta -28 with its pad on the key.
    - The bore is 0.252 from the sagged rod (+0.175).
  - **3.68:** it lands the same way and rests at theta -8, with the bore 0.200 from the sagged rod.
  - **With friction:** a crank that stops where it lands is at most 0.445 off (dy -0.4).
- The rod's tapered tip picks each crank up (section 6, check 2). Nobody holds or aligns a crank.

## 6. Rod

- **Cut length:** `ROD_CUT` 61.0 -> **63.25 +- 0.2** in both sizes.
- **Stops:**
  - 4.26: `ROD_STOPS` = (`ROD_STOP_X0`, `POCKET_X1`).
  - 3.68: `ROD_SPAN` = (`ROD_STOP_X0`, `WALL_X1`).
  - `ROD_STOP_X0` = `X0` + web + flange = -2.34.
- **End play:** 0.50 nominal.
  - From the cut tolerance alone it is 0.30-0.70.
  - With the gate, slot and squareness stack it is 0.05-0.95.
- **Tip, the end that goes in first:** a pencil taper 1.0-1.5 long ending in a flat 0.7-0.9 across.
  - Pickup: the flat lands inside a crank's 2.5 lead-in mouth for offsets up to 0.80, and the worst landing is 0.445.
  - +X wall: the flat carries the right-hand stop hits at 42-70 MPa at 27 N. A 0.3 point would indent.
- **Tail:** cut square. It bears on the gate.
- **Positions:**
  - Pushed flush, the tail is at -4.09 and the tip at 59.16.
  - At home the tail is at -2.34 and the tip at 60.91.
  - The taper stays clear of the ring round the Right key (SW2) (to 56.3) in both.

## 7. Loads (R2)

- **Radial:** the 211 deg load still goes into the unchanged rings and seats, 14.1-14.4 MPa centred at 20 N. The rod's span and supports are unchanged.
- **Axial:** rod end -> gate flat -> flange -> tub lips. It is all tub material except the gate, which the tub holds. The lid only caps the gate's top in Z, and the flat contact gives it no Z load.
- **Model (c1_gate):** C3's p4b one-way strip. Each piece:
  - Strip height 3.53.
  - Per-side load from statics about the rod axis: 50/50 centred, 48/52 at the +-0.10 shift.
  - Lip: lever from the root to the bearing centroid. The value is the larger of two:
    - 1.1 x the peak of (L + d) / t(d)^2 along the round end;
    - 1.3 x L / t0^2.
  - Flange: arm from the web edge to the bearing centroid, no Kt (p4b's convention; see section 10.3).
  - The lip is judged on 25 MPa, the across-layer reading, because the lip also bends in Z. The gate's bending stresses lie in its layers (it prints on its X face), so it is judged on 50 MPa in-plane.

| case | N | lip, centred / worst shift | lip SF on 25 | gate flange, centred / worst | gate SF on 50 |
|---|---|---|---|---|---|
| sideways click | 1.7 | 0.7 / 0.8 MPa | 37 / 33 | 0.9 / 1.1 MPa | 58 / 47 |
| sideways 20 N over-press | 9 | 3.6 / 4.0 | 6.9 / 6.3 | 4.5 / 5.6 | 11 / 8.9 |
| extreme | 17.6 | 7.0 / 7.8 | 3.6 / 3.2 | 8.9 / 11.0 | 5.6 / 4.6 |
| **1.5 m drop** | **27** | 10.8 / 12.0 | **2.32 / 2.08** | 13.6 / 16.8 | **3.68 / 2.97** |
| stiff-stop sensitivity | 33 | 13.2 / 14.7 | 1.90 / 1.70 | 16.6 / 20.5 | 3.0 / 2.4 |

- **Other stresses at 27 N:**
  - Interlayer shear in the flange wing: 8.8 / 9.1 MPa (SF 2.8 / 2.7 on 25).
  - Bearing pressure on the lip faces: 12.7 / 19.8 MPa.
  - Rod end on the flat: 16.9 MPa.
- **Drop cap:** the rod's axial stiffness limits the hit to about 28 N (5.4 m/s, 0.19 g, 140 N/mm).
- **What hits:** the slots hold the cranks in X, so only the rod hits the gate.
- **Edge press (pre-existing, unchanged by this spec):**
  - 20 N at the cap edge: 18.9-19.6 MPa at 1x bearing stiffness and 24.4-26.9 MPa at 0.3x.
  - Centred: 14.1-14.4 MPa.
  - Click at the edge: 2.0-2.1 MPa.

## 8. README (both) and print/ROD.txt

**4.26 "Assembly": replace steps 5-7.** The other steps stay.

> 5. **Cranks:** drop each in from the open back, cheeks into their slots, at 0 to +10 deg (pad toward the face, nose toward the board side), and let go. It tips pad-first onto its key and lies there (about -28 deg on this case). Don't hold or straighten them: the rod's tapered tip picks each one up.
> 6. **Rod:** tub still face down. From the left side, lay the tapered end in the channel at the bottom of the slot beside the chin. Push it straight in (hole, rings, four cranks) until its square tail is flush with the case side or just inside it; a fingertip leaves it about 0.3 mm in. You can watch it cross the slot from above. Go straight on to step 7: until the gate is in, only friction holds the rod.
> 7. **Gate:** drop it into the slot from the open back, bevel down, small hole outward, and press its top level with the rim. Its bevel pushes the rod the last 1.75 mm to its stop. If it stops proud, lift it out, push the tail a little further in and press again. Check that the gate's web fills the opening in the case side, flush, with its small hole showing. From here the rod and cranks stay put however you tilt or lift the tub, as long as its back never faces down.

In step 9, add: "The lid's rim closes over the gate. If the case side shows an open slot instead of the gate, the gate is missing: the rod would walk out."

**"Taking it apart": replace the screw text with this.**

> Lid off, board screws out, lift the board. Hook a straightened paperclip into the small hole in the gate's outside face and lift the gate out toward the back. Push the rod's right end (bare at X 56.3-61.4) toward -X with a small screwdriver until it stops at the last ring. 2.7-3.1 mm of rod then stands out of the slot: pull it out with fingers or flat-nose pliers. Lift out the cranks, then push each key in from the face.

**Other edits in the 4.26 README:**
- Line ~69 and the rod bullet (~114-118): the gate and the +X wall close the end play.
- Hardware (~574): no M2.5; 63.25 mm of filament; a paperclip for service.
- Parts table: add `gate (x1, print 2) | inner face down`.
- Checks (~266, ~270): the 3D contact is now "gate on its floor and lip faces".
- Open item (~289): the side screw's head becomes "the gate's flush 2.5 x 6.3 web and 1.3 mm pull hole show on the left side".
- Over-press (~240): add the edge-press numbers.
- Crank text: drop any mention of holding cranks while the rod goes in.

**3.68 README: the same replacements.**
- Lines 57, 124-145 ("The rod"), 162-165, 172-176, 214, 231 and 262.
- The comparison table (294-295: "Screws: 3 x M2 x 8").
- Step 5 reads "about -10 deg on this case".

**print/ROD.txt:** the 4.26 build.py writes it (~line 1035); have the 3.68 build write it too.
```
Bottom keys: the crank rod (not printed) and its gate (printed, gate.stl)

Rod: 1.75 mm PLA filament, cut to 63.25 +- 0.2 mm. One per case.
  - Take it from the spool's outer turns. Straighten it: on the bed at about 60 C under a flat plate for
    5 minutes, and let it cool under the plate.
  - Keep it only if it rolls freely on a flat surface with no gap over 0.1 mm under it.
  - Taper one end (the one that goes in first) like a pencil over 1.0-1.5 mm with a craft knife, then
    sand the very tip flat, leaving a flat about 0.8 mm across. Not a chamfer, not a needle point.
  - Cut the other end square (file it flat if the cutter leaves a chisel): it bears on the gate.
  - It goes in from the case's left side (-X): along the channel in the slot beside the chin, through
    the rings and the four cranks (don't hold them; the taper picks them up), until its tail is flush
    with the case side or just inside.
Gate: print two (inner face on the bed); one is a spare. Right after the rod, drop it into the slot from
  the open back, bevel down, small hole outward, and press it level with the rim: it pushes the rod the
  last 1.75 mm. If it stops proud, lift it, push the tail a little further in, press again.
  End play is then 0.3-0.7 mm. No screw.
  To take it out: a straightened paperclip in its small hole, lift. Then push the rod's right end
  toward -X with a small screwdriver until it stops; 2.7-3.1 mm stands out of the slot.
Cranks: crank-T for TS365ZJ boards (every JLC board), crank-M for APEM MJTP1117.
  Ream each crank's two bores with a 1.9 mm drill; the rod must slide and turn freely.
  Print the cranks, keys and gate with elephant-foot compensation 0 (OrcaSlicer, per object), no brim.
Before the first full print: the gate coupon (fit, cam, and the 5.5 kg push); since test 2 the chin
  coupon with one key is an optional fit check of the hook keys (it was the drag coupon); see the
  README, "Bottom keys".
```

**Builder actions for the rod:**
- New: 4 crank drops, 1 hand push and 1 gate press = **6**, with no tools and nothing held.
- Today: 4 drops, a feed with 4 crank holds, and 1 screw = 10.
- Service: a paperclip lift, a screwdriver push and a pull.

## 9. Checks (build.py / crank_checks.py / mechanics.py / slice_check.py / coupons.py; each prints PASS / FAIL / ACCEPTED)

1. **Parts.**
   - Remove `ref_side_screw` / `ref_screw`, `side_screw()` / `screw()`, the expected contact `('tub', 'side_screw')` (4.26 build.py ~289), and the "screw cuts its thread" check (3.68 crank_checks ~229).
   - Add `gate` as a printed part to the package and showcase lists.
   - Expected contact `('tub', 'gate')`: a touch of zero volume on the floor and the lip faces.
2. **Rod path and crank pickup.**
   - A d1.90 cylinder from X0-0.2 to `ROD_STOPS[1]`: 0 volume with the tub.
   - "Rod + 0.1" is empty except for the gate at X -2.34.
   - Pickup, using review 2's r2 method on the built cranks, keys and tub (keys lifted to their stop):
     - Drop poses: theta 0 / +4 / +10 x dy -0.4..+0.4.
     - Path: every pose from landing to frictionless rest.
     - For each pose, the bore's offset from the sagged rod (0, +0.175).
   - PASS if both hold:
     - the rest offset is <= 0.30, so the 0.3 lead-ins alone cover it;
     - every landing and path pose is <= 0.80, so the tip's 0.9 flat lands inside the 2.5 lead-in mouth.
   - Expected: rest 0.252 (4.26) / 0.200 (3.68); worst landing 0.445.
3. **Crank drop-in**, with the keys lifted to their stop, at theta 0 / +4 / +10 and dy -0.4..+0.4.
   - Report the first contact. Expected: the belly on the rail at dz +0.11..+0.41 (+0.33..+0.41 at dy 0).
   - The rail stays >= 0.30 away on the way in, as today.
   - FAIL if any pose is blocked or lands at dz < -0.05.
4. **Crank sweep and board insertion:** today's checks, re-run unchanged. There is no crank, rail or key change.
5. **Gate path:** lower the gate along +Z from z -10 to its seat, centred in X (0.075 each side) and Y.
   - Gate to tub >= 0.05 until seated (expected 0.075 in X, 0.10 web to mouth, 0.15 flange to cavity). Then it touches the floor only.
   - Gate to lid >= 0.05.
   - Gate to board, display, midplate and strip refs >= 0.5.
6. **Cam**, with the rod tail at X0 and at X0 + 0.3.
   - The gate's first contact with the rod is on the bevel.
   - Once the gate is seated, the tail is at -2.34 +- 0.01 and the flat covers the rod end past its axis.
   - With the tail 0.2 proud, the gate stops at least 1 mm proud.
7. **Bearing (new).** On the plan with every chamfer and the round ends, push the gate -X at Y offsets 0, +-0.05 and +-0.10:
   - zero overlap at rest;
   - flat bearing per side >= 0.25 centred and >= 0.15 at +-0.10 (c1: 0.30 and 0.20).
8. **mechanics:**
   - End play: 0.30-0.70 from the cut and 0.05-0.95 with the stack. ROD.txt prints it from the params.
   - 27 N drop, at every Y offset of check 7, using the section 7 model (lip on 25 MPa; gate on 50 in-plane):
     - lip SF >= 2.0;
     - gate flange SF >= 2.0 on 50 in-plane (expected 3.68 centred);
     - interlayer shear in the flange SF >= 2.0 on 25.
   - 33 N is reported and ACCEPTED at a lip SF >= 1.7.
   - Axial 9 N and 17.6 N: SF >= 3.
   - Rod FE with the new span: <= 14.6 MPa centred at 20 N. Record the edge-press numbers.
9. **slice_check:**
   - Tub:
     - These boxes are empty:
       - `gate_mouth_open!` (X -4.0..-3.1, y -3.7..-1.3, z -3.7..0.5);
       - `gate_cavity_open!` (X -2.9..-2.3, y -4.2..-0.8, z -3.7..0.8);
       - `gate_end_open!` (X -2.75..-2.45, y -4.65..-4.40 and -0.60..-0.35, z -3.7..0.8).
     - These are present:
       - `gate_floor` (X -2.9..-2.5, y -4.2..-3.9, from 0.05 to 0.35 below the floor surface);
       - `lip` (X -4.0..-3.1, y -4.30..-3.95 and -1.05..-0.70) from the rim to the floor.
     - The sliver hole reads back >= 1.90.
     - No bridges.
   - Gate:
     - its first layer is the flange;
     - the bevel is <= 45 deg;
     - the pull hole is present and reads back >= 1.15;
     - every wall is >= 0.45 (expected 0.60).
   - No cradle box. The 3.68 `slot{i}_open!` boxes stay as today.
10. **coupons.py: `coupon-gate`.**
    - **Coupon:** a 12 mm-tall piece of the -X wall, X -4.09..+2.0 and y -7..+2. It includes the slot, the sliver, the channel and the start of the left ring. It prints face down like the tub.
    - **Feet:** two 1.0 mm feet on its outer face at y < -5.5 and y > 0.5, so that standing on them the lips and the gate's web are 1 mm off the table.
    - **With a gate:**
      - the gate slides in at 0.10 per side;
      - it cams a 20 mm rod piece home;
      - it lifts out with a paperclip.
    - **Proof test:**
      - Stand it on its feet on a kitchen scale, with a strip of tape over the rim for the lid.
      - Press the rod piece straight down (at most 8 mm standing out) with a flat tool.
      - At 2.8 kg (27 N): no crack and no visible set, and the gate still lifts out.
      - Then take it to 5.5 kg (54 N, SF 2 on the real print): nothing breaks.

## 10. Open

1. **Nothing is built yet.** All numbers come from sections of today's STLs and hand models; the section 9 checks decide.
2. **Gate fit and the proof test (coupon):**
   - If 0.10 per side is too tight, go to 0.15.
     - Centred, the lip stays at 2.32 and the gate drops to 3.07.
     - At the +-0.15 shift the lip is 1.97 and the gate 2.34 (c1).
   - If the proof test cracks the gate where the web meets the flange, go to lips 1.05 / flange 0.70.
     - The gate becomes 4.27 / 3.44 on 50 and the lip 2.10 / 1.88 on 25.
     - The gate face, flat and tongue notch do not move.
   - If a lip cracks, there is no fix inside a 1.75 gate; that reopens the concept.
3. **Print scale:**
   - Convex corners (the flange ends, the lip tips) print with about R0.2. The real bearing is therefore narrower than 0.30, and it sits nearer the lip roots.
   - The inside corners where the web meets the flange print sharp. The p4b-style flange numbers carry no Kt there.
   - The proof test measures all of this on the real parts.
4. **3.68 standard, cosmetic:**
   - The mouth's floor meets the rounded front edge in the last 0.04 mm. That leaves a 0.25-tall notch, which the gate's tip fills.
   - The gate's outer bottom corner stands about 0.09 past the rounded edge (review 2, P6).
   - The tip is not chamfered, because a flush tail would then land on the blunt part instead of the bevel. Today's countersink cuts deeper.
5. **Pre-existing, not caused by this change:** at theta -17 with 0.265 toward 211 deg, the as-built SW2 +X cheek overlaps the old tub by 0.012 (j1). The sweep should say whether that pose is real.
6. **The gate is held only by gravity until the lid is on:** the tub must not be turned back-down before then, which assembly never does. A detent strip can be added if Ian wants one.
7. **The tail must be square.** Friction on a chisel end adds a small Z force, which the floor and the lid lip carry.
8. **Rattle:** end play can reach 0.95 at the worst stack.
9. **Edge over-press (pre-existing):** 24.4-26.9 MPa at 0.3x bearing stiffness against the 15-20 limit. This spec does not change it.

---

## Review responses (review 2)

- **C1 (gate never bears flat): accepted; fixed differently.** I re-ran the review's recommended geometry (c1_gate, variant R) and found two further problems:
  - **The chamfer clashes with the fillet off-centre.** A 0.05 chamfer only clears the R0.15 fillet with the gate centred in Y. The gate can sit 0.15 off, and past a 0.05 shift the flange corner overlaps the fillet: 0.0002 mm2 at 0.10 and 0.0036 at 0.15.
  - **The far side is weak at the extreme.** There the far side bears only 0.15 at the lip tip, which gives lip SF 1.88 (0.10 shift) and 1.74 (0.15).
  - **The review did not recompute the flange.** At 0.65 it runs at 16.3 MPa at 27 N: SF 3.07 on 50, below SPEC2's own "gate SF >= 4" check.

  Rev 3 does three things instead:
  - It replaces the fillets with round cavity ends. Nothing sits in the corners, and the root relief is R0.40.
  - It lets the web locate the gate at 0.10 per side, which caps the shift at 0.10 and moves the flange's root 0.05 toward its bearing.
  - It keeps lips 1.10 / flange 0.65 with only a 0.05 edge break.

  Results:
  - Lip SF 2.32 centred and 2.08 at the worst shift. Gate 3.68 / 2.97 on 50.
  - Zero overlap and zero travel at every allowed position.
  - The round ends are clear of the lid and in solid wall in all 4 builds (c1_ends, c1_lid).

  The gate is now judged on SF >= 2 against 50 MPa, not ">= 4 on 50". Its bending stresses lie in its layers, so 50 is the strength that applies; interlayer shear is checked separately on 25 (SF 2.7).

  The new coupon proof test measures what the hand model cannot: print rounding, the web-flange corner, and plate action in the lip. Check 7 is the bearing check the review asked for, at every allowed offset.
- **C2 (pull hole): accepted.** The hole is d1.30 x 1.0 deep at z -2.0. With the 2.50 web the walls are 0.60 in Y, 1.00 above and 0.70 at the chamfer (c1_gate; 0.90 and 0.70 since rev 3.1). The tool is a straightened paperclip. A 1.2 hex key is not a common metric size, so it is not named. slice_check gets the 0.45 minimum-wall rule.
- **C3 (cranks leave the cradles): accepted.** The fix goes further than the review's: the cradles and the crank cheek cut are removed. I ran review 2's r2 model with today's cranks and no cradles (r2n):
  - The 4.26 comes to rest at exactly the same pose (theta -28, 0.252 off).
  - The 3.68 rests at theta -8, 0.200 off, slightly better than with cradles (0.218).
  - Friction landings reach 0.40-0.445 off, against 0.40-0.43 with cradles.
  - So the cradles never held a bore on the rod's line. They only moved the landing from about 0.35 to 0.20, which nothing needs.

  Removing them deletes 8 tub features, a change to both cranks, P1, the cradle slice box and the cradle sweep items. Check 2 and check 3 are rewritten as the review asked, with the keys at their stop and limits taken from the real rest and landing poses. README step 5 now says the cranks tip onto their keys and are not to be held.

  On the tip I disagree in part. A true point concentrates the right-hand wall hits: 27 N on a 0.3 point is about 380 MPa, and it would blunt and dent the wall on the first drop. A flat about 0.8 across (0.7-0.9) still lands inside the 2.5 mouth up to 0.80 off (0.445 is needed) and carries the hit at 42-70 MPa. What matters is that it is a taper and not a chamfer, and ROD.txt says so.
- **C4 (checks): accepted.**
  - Check 5 (was 6) lowers the gate centred in X (0.075) with a >= 0.05 limit.
  - The cradle box is gone with the cradle.
  - section 4's seat text now says what r1(d) found: the web's full width carries the seat, and there is nothing under the flange within 0.1 of the flat.
- **P1:** moot, since the cradles are gone.
- **P2:** accepted. README step 6 says "flush or just inside" and step 7 gives the recovery. Check 6 now tests the tail at X0 + 0.3.
- **P3:** accepted. There is a check line in step 7 and a missing-gate line in step 9.
- **P4:** agreed, and self-revealing. The README says "bevel down".
- **P5:** carried as section 10.9.
- **P6:** carried as section 10.4, with the reason the tip is not chamfered.
