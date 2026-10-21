# Open work (as of 2026-10-21)

What is built but not printed, what is unproven, and the options that are studied but parked. The case READMEs have
the full records; the study notes named here are local (not in git).

## The 3.68 lid: rebuilt, not printed

Ian printed 5ef49dc (in the pre-split history; four screws): all four screws bite, but the lid bulged at the top middle (CAD +X, upper
middle), would not go fully down, and its long edges could be pried open. The study round and its fixes are in
`case-368/README.md` ("The battery bay (2026-10-19)"). Done, all lid only (read-backs in `bayread.py`, each shown
FAILing on the old lid and PASSing on the new one):
- The bay is one layer deeper (the back is 1.0 thick; the case is 12.9 mm, light strip 13.7), the lip is raised over a
  6.02 mm cell (a 5.3 mm cell with two layers of tape on each face), the hooks are gone.
- The lead has a route: one strip of tape on the midplate's bare back above J5 (the tape point), a coil well beside
  it, the top rib lowered to a fence, the backstops moved 3.45 mm past the board's cut and 0.33 mm under the midplate.
- Six internal ribs (bed 3.0) and thicker latch arms (1.3 at the root, today's section from Z -0.5 up): the springs'
  bow 0.148 -> 0.113 mm in the grillage model, the long edges let go at 19-22.5 N instead of 12-16 N. Ian asked for
  1.2 / 0.85 arms; `lid_close` showed 6 of 12 meeting the board's edge, so they are thick only below the board.
- Logo and grip grooves 0.2 deep (a layer's mid-plane flips between slices; whole layers do not).

Unproven (nothing is printed):
- That Ian's lid crept (PLA under 10 N of springs and a pinched lead), or that a board sliver or the 3V3 wire sat on
  the old posts past the cut. Ask him for the checks in the plan: lid alone on a table (rocks?), the old posts' tops
  (a shiny dent?) and the wire there, the back pressed with the cell out.
- The lead's reach (a limp string, 10 % slack, the lid stood up at 90 degrees), the ribs and arms on a printer.
- Next, if the new lid still bulges: ask for a photo of the top edge. (The bigger options for the long sides are in the
  next section.)

## The 3.68's long sides (2026-10-21): the tub-only fix, merged

Ian: with all four screws in, each long side is closed at the screws and bows open in the middle between them. The
study round (cause, cause-check, a stack study and alternatives, with their checks) found one proven rigid chain and no
proven cause. The board is clamped line to line at H3/H4 between the tub's bosses (printed 1.67) and the lid's posts
(0.07 at home): 1.600 of room for a 1.600 board, 8.25 mm above the bottom corner screws with no screw through it (the
4.26's go through), so any extra thickness levers the lid open along its long sides (0.07-0.10 mm per 0.1 mm of extra;
models, +-30 % to 2x). Candidates still open: the long-edge latches not holding, a lid or tub that took a set, the
lever. The cell is ruled out (it does not touch the bay lid: 1.1 mm of air).
- **Ian chose the invisible change first (2026-10-20):** the tub's H3/H4 boss faces two layers (0.4) lower
  (`params.H34_FLOAT`, `H34_FACE` 2.07), so the board floats: 0.40 of room to the bosses as printed, 0.24 with a +0.16
  board. **The midplate is the first stop, not the bosses:** its back (CAD 1.80) is 0.13 in front of the board at its
  bottom edge (0.03 with a thick panel), so that is the board's real float; a board more than about +0.13 thick still
  props the lid until the parked +0.4 spring room (option 3 below) is built. `board_room` reads only the bosses. Built
  with `asprinted.board_room` (FAILs on the old tub at 0.000, PASSes now), both builds, the plate file and the configs;
  only the tub (and the gate coupons, by 0.02 mm3) changed. **Reprint the tub only.** See `case-368/README.md`,
  "The long sides".
- **If the sides still bow, the parked options** (studied, not built; the study's plan, local, has the specs):
  1. **S5 / S6: a 5th and 6th M2 x 8 screw in the middle of each long side**, at CAD (-1.85, 26) and (61.85, 24) in place
     of the left-26 and right-24 latch arms: new tub bosses (wall carried into the latch channel, stopping 0.45 off the
     board's edge; pilot 1.7; a lead-in chamfer), lid posts from the floor to the seam, counterbores 4.2 wide and 2.0
     deep (seat at bed 2.0), midplate unchanged (its 1.6 notches clear the bosses). It holds the sides whatever the
     cause is (gap 3-10 times smaller in both models). Visible: two more heads a third of the way up each edge, and the
     back's round notched about 4 mm at each (show Ian first); a socket head sits flush with zero margin. Every 3.68
     configuration changes together (old lid on a new tub does not close). New read-backs: S5/S6 screws, rim-to-tub, the
     bosses' X clearance, `lid_close`, `midplane_ties`.
  2. **A bigger cell** (only if Ian wants more than 500 mAh): a 403048 (4.0 x 30 x 48, about 600 mAh; Enerforce
     LP403048 is 3.85 thick but has a Molex 5264 plug, a generic one a PH2.0) lying over the ESP32 shield, in a lid whose
     pocket moves there: about 13.3 mm (12.9 with a looser air rule) for a cell of at most 4.0, 13.7 for any "4 mm" cell
     up to 4.3. Needs the RF pre-test first (today's cell flat on the shield with paper under it, Wi-Fi sync with and
     without), its own design pass and read-backs. A 403450 does not fit; the 503035 does not suit that pocket.
  3. **+0.4 spring room** (MID_REAR +0.4: tub, midplate and the four bottom keys reprinted, 13.3 mm) only if Ian's
     checks show a solid stack. It is also what lets a board thicker than +0.13 (+0.03 with a thick panel) float.
  - The 4-layer case (a seat frame between the board and a tray lid) was studied and not recommended: it keeps the same
    latches and tongue, and its frame and lid are about half as stiff along the long edges.
  - Checks for Ian that decide between the candidates (no tools): press the middle of each long side (click and stay, or
    spring back); back the two bottom screws out two turns and press again (do the middles close?); lid alone on a flat
    table and tub alone face down (rock?); a shiny dent on the lid's two bottom posts or the tub's bosses; whether the
    GND bodge wire lies on C6.

## The side keys: teardrop base, both sizes rebuilt (2026-10-20)

Ian's photos showed scraggly keys in their free half, on both sizes. As sliced, every key of both sizes stood from its
hinge to its free end on one 0.52 bead (the back's round meets the foot's 45 degrees 2.0 in from the face), its second
layer 43 % on it; almost nothing on a key is over air, so more support could not help. `params.TAB_BASE` fills the
round's corner under each key (`sidekeys.bar`, both cases). Ian chose `'square'` (2026-10-19: 1.70 of bed, second layer
94 %), then `'teardrop'` (2026-10-20: the square edge looked sharp beside the bevels everywhere else, and the round had
printed fine most of the time): the round is kept down to its 45-degree point, then a 45 to the bed, so a key stands on
0.83 of bed and its second layer is 76 % on it (CC2 and generic presets, both sizes, every key). The press moves little
(3.68 k 0.90 / 0.94 / 0.93 N/mm; 4.26 0.87 / 0.91 / 0.77 / 0.44). `configs_slice.side_key_base` reads it back with limits
0.68 mm / 95 % of the length / 60 %: it FAILs on the round (every 3.68 key, and 112 of 112 key reads a printer on the
4.26's 32 configurations, 0.523 mm and 43 %) and PASSes on the teardrop and on the square.
- **Both sizes are rebuilt for the teardrop:** every configuration slices ok and `side_key_base` PASSes on all 112 key
  reads a printer (plus 5 on the lid-alone read; 3.68: 3 plus 3): 0.828 mm, 100 % of the length, 76 % on both printers.
  Only the lids changed. Both lids are ready to reprint (`3.68/lid`; `4.26/lid`, or `4.26/lid-chinless`); nothing is
  printed.
- Still unproven that the bead letting go was the cause. The decisive photo: a failed lid turned over, a scraggly
  key's bottom edge from the hinge notch to the free end (a flat strip, or missing, curled or ragged?), and whether a
  thin strip of plastic was left on the plate under it.
- If keys still print scraggly: a per-key speed modifier (walls 40, overhangs 25/15/10). It needs modifier-part
  support in `make_plates.py`'s writers.

## Other open items

- Hosting of the per-configuration 3MFs is still undecided (local `out/configs*/` for now).
- The 4.26's Y-102 midplate spring is riddled by J6 holes (`case-426/README.md` section 11).
- Optionally, take the 4.26 latch notch to 1.0.
- A cache speed-up branch (`tail3b`) is parked in the pre-split history; don't resume it unless Ian asks.
