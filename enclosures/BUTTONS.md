# Bottom buttons: what is wrong and what could replace them

Decision record, 2026-09-26: why the bottom keys became a bell crank. It covers the four bottom keys (SW9, SW8, SW3, SW2) of both cases: the 4.26″ (now `case-426`, then at Rev K) and the 3.68″ (now `case-368`). The rocker it criticises is Rev K's; what was built from it is [BELL-CRANK-SPEC.md](BELL-CRANK-SPEC.md) with [SIDE-GATE-SPEC.md](SIDE-GATE-SPEC.md) (see Status below). The numbers come from force and geometry models of the built parts, checked by a second, independent pass. The design history they draw on (Rev D to K, x3, Ian's feedback on prints 1 to 5) is summarised at the end.

2026-10-04: the 4.26″ also builds a **chinless** case with no bottom keys at all (touch for OK/Back; the board without SW9, SW8, SW3 and SW2 fitted; 117.4 mm tall): `case-426/README.md`, "Builds".

## In short

- **Today's rocker has no mechanical advantage.**
  - Its pivot has to sit on the board's front face, because the switch pins at y 1.8 block anything higher. The plunger is 2.7 mm behind the board, so the output arm is 5.5 mm.
  - Pressed at the cap's centre the finger needs about **1.4 ×** the switch force; over the cap's upper third it needs **1.9–2.8 ×**. Friction takes another 18–25 %.
- **There is no free travel before the click.** The key rests already pressing the plunger, so the finger gets 0.06–0.18 mm of movement before the snap. It feels like a rigid surface that suddenly gives, which is the "baseline force" Ian describes.
- **The 3.68″ is worse for one reason: its caps are low.** They stand 0.5 / 1.1 mm proud of the standard x3 face, and flush in 1.2 mm wells on the light-strip tub. A fingertip is wider than the 4.7 mm cap, so 11–35 % of the press goes into the case face (22–53 % in the wells). The 4.26″'s 0.8 / 1.9 mm caps lose 3–19 %.
- **Fragility is real, but the spring arm isn't the main risk.**
  - The part most likely to break is the pivot ridge's 4.4 mm middle span. It is printed across layers and reaches 63–93 MPa under a 20 N thumb.
  - The 3.68″'s neck arms are half as tall as the 4.26″'s, so they take 4 × the bending stress.
  - Its 0.5 × 1.2 mm spring arm sits at 24–49 MPa all the time. That is a creep and fatigue risk, but the arm adds nothing at the click.
- **Which switch is fitted matters as much as the mechanism.**
  - The schematic's DigiKey part is the APEM MJTP1117: 1.27–1.86 N, 100k cycles. The cases were designed around it.
  - JLC fits its LCSC substitute, the SHOU HAN TS365ZJ: 250 ± 50 gf (1.96–2.94 N), 50k cycles. With it, every key force is about 1.56 × higher.
  - The presses so far were on the printed `pcba-dummy` with loose switches of unrecorded type. The Rev 1.0 boards had not arrived. **Stem colour tells them apart: the TS365ZJ's is white, the APEM's black.**

## Options

Forces are the finger force at the click, at the cap's bottom edge / centre / top edge, for a 1.57 N switch (the MJTP1117's nominal) and friction 0.3. They include the force the fingertip loses to the case face, for a cap about 1 mm proud.

| Option | Finger force, 1.57 N switch | Same, TS365ZJ (2.45 N) | Travel to the click | Parts per key | Fits | Main risks |
|---|---|---|---|---|---|---|
| **Today's rocker** | 2.2 N at the centre (1.4–3.0 over the cap); 2.5–3.1 N on the 3.68″ | about 3.0–3.5 N at the centre | 0.12–0.33 mm, no free travel | 1 + a thin spring arm | — | the ridge span, the 3.68″ necks and spring arm; the preload window is ±0.2 mm |
| **A. Right switch, same keys** | as above with the MJTP1117 fitted by hand (DigiKey) | — | same | same | now, no case change | only fixes the TS365ZJ penalty |
| **A2. Alps SKHLLCA010, same keys, spring arm removed** | about 0.9 / 1.2 / 1.7 N (the switch is 0.59–1.57 N) | — | same | 1 | now, same footprint and plunger position | LCSC only (not stocked at DigiKey); 50k cycles; any preload over ~0.1 N would hold it pressed |
| **B. Bell crank + straight key** | about **0.8 / 0.95 / 1.2–1.4 N** | 1.3 / 1.45 / 1.8–2.1 N | 0.58 mm | key + crank + pin | all four builds, no taller bezel | key height scatters ±0.35–0.47 mm with the board's position, so it needs a soft take-up leaf; no reliable hard stop (a 20 N press puts ~40–47 N into the switch); force rises toward the cap's top edge |
| C. Rocker v2 (pivot higher up the board) | 1.0–1.1 / 1.35–1.45 / 2.0–2.2 N | 1.6 / 2.1–2.25 / 3.1–3.4 N | 0.25–0.50 mm | 1 | only the 4.26″ standard and the 3.68″ light strip, each needing the chin 1 mm taller; not SW9 on the 4.26″ light strip | **dropped**: heavier than B and does not fit the standard 3.68″ |
| D. Keys printed into the tub (flexure) | loses 22–53 % to the face | — | — | 0 | would make the tub the only difference automatically | **dropped**: a tub printed face down can only have flush caps |
| **E. Switches facing the finger** (next board) | ≈ switch force: **about 1.0 N** with an Alps SKQGAFE010 | — | 0.25 mm | a plain cap | needs the board extended **≥ 6 mm into the chin** (7.5 mm for the SKRRAAE010) | a board change; the long-term answer |

### B. Bell crank + straight key, in more detail

```
                                                  Y ->  (up the board)
 face  ==+==[KEY]==+---------------------------- skin
         |   | |   |   the key slides straight down in the chin opening
         |   |_|  pushes the crank's input pad at y -6.3
         |  ===o=========o  <- crank, as wide as the cap
         |     input 4.0  \    pivot pin at (y -2.3, z -1.0) in hanger plates on the chin wall
         |                 |   output leg, crowned nose, 1.7 mm below the pivot: almost no scrub
         |                 |->[plunger] y -1.92, z -2.71
         |                      PCB ==== (y >= 0)
 chin    +-- y -7.2 (today's chin works)
```

- **Why it is light:** the output arm is 1.7 mm against a 4.0 mm input arm, so the crank alone needs 0.5 × the switch force. The pivot sits almost on the plunger's line, so the nose doesn't drag down the plunger face.
- **What it needs, from the fit check:**
  - the crank's hub cut back over the plunger;
  - a crowned nose on the output leg, or the contact runs to the plunger's lower edge and the force rises 38 %;
  - a pin that is not printed across layers: a Ø1.0 steel rod, or a length of 1.75 mm filament;
  - five hanger plates in the tub along the chin wall, in place of today's rib and ledge;
  - a soft take-up leaf on each key, since the lever turns ±0.15–0.2 mm of board position into ±0.35–0.47 mm of key height (built as a drag leaf; since test 2, 2026-09-30, the keys have rigid hooks and no take-up: the key rests on its switch, see [BELL-CRANK-SPEC.md](BELL-CRANK-SPEC.md));
  - the cap about 1.2 mm proud, with only its lower part (y −6.9 to −3.5) pressable;
  - a last-resort stop at about 1.0 mm of key travel.
- **Sharing:** the crank, pin and hanger geometry are identical in all four builds. Only the key's length follows the tub's face height, which is 1.2 mm apart on the 3.68″.

### E. Switches facing the finger, in more detail

This is what shipping readers and phones do. The Kindle Oasis uses dome switches on a flex behind the buttons. PocketBook puts its page buttons on the bottom bezel face, as Silkscreen does. Game controllers only use levers for long-travel shoulder buttons, and add a torsion spring when they do.

- **Candidates, all top-push SMD:**

  | Part | Force | Life | Size | Stock |
  |---|---|---|---|---|
  | Alps SKQGAFE010 | 0.98 N | 500k | 5.2 × 5.2 × 1.5 | DigiKey and LCSC C202424 |
  | Alps SKRRAAE010 | 1.0 N | 5M | 7.5 × 7.0 × 0.6 | DigiKey and LCSC C97437 |

- **Space:** neither fits today's board outline. The band between the board's bottom edge and the ribbon folds is only 3.5 mm. The board would have to grow about 6 mm (SKQG) or 7.5 mm (SKRR) into the chin, which reaches the chin wall.
- **Board layout:** they would sit on the front face, which makes the board double-sided for assembly, unless they are hand-soldered.
- **The existing front-mount option** (`HARDWARE.md` §9.1.1: a 4.3 mm-tall part in the mounting holes) doesn't fit the 4.26″ (it meets the glass and the skin). On the 3.68″ it only fits the light-strip tub.
- **Page-key life:** the page keys are on the sides (SW1/SW4, SW5/SW7). A heavy reader presses one 20k–90k times a year, so keep those at 100k cycles or more. The MJTP1117 is rated 100k; the TS365ZJ and the SKHL 50k.

## Before choosing

1. **Identify the switch that felt heavy** by stem colour, and measure a real TS365ZJ: plunger tip to the signal-pin row, and plunger height above the board. Its drawing suggests the tip sits about 0.28 mm further out than modelled, which would add preload.
2. **Settle the switch per build.** Either keep DigiKey's MJTP1117 as fitted (hand-soldered), or accept the heavier JLC part and size any new mechanism for it.

## Status (2026-09-27)

**Built into both case projects:** the bell crank with a straight key, from the reviewed spec in [BELL-CRANK-SPEC.md](BELL-CRANK-SPEC.md). Each project's README has a "Bottom keys" section covering what to print, the rod and its printed gate (2026-09-28, [SIDE-GATE-SPEC.md](SIDE-GATE-SPEC.md)), the tuning coupon and the assembly order. Both builds of both cases pass every check. The one accepted finding is a wrong-variant crank held at 0° while the board goes in; the fix is not to hold the cranks up.

- **Finger force at the key centre:** 1.15–1.66 N with the MJTP1117 and 1.75–2.60 N with the TS365ZJ (friction 0.3). Today's 4.26″ rocker needs 2.28 N with the MJTP.
- **Travel:** about 0.4 mm to the click. The keys stand 1.2–1.8 mm proud.
- **Rod at a 20 N press:** 14 MPa of bending.
- **Case size:** the chin grows 1 mm, so the 4.26″ is 125 mm tall and the 3.68″ is 108 mm tall.
- **Still to measure:** check a real TS365ZJ against its drawing before printing crank-T.

## Decided (Ian, 2026-09-26)

1. **Mechanism: B, the bell crank with a straight key**, in both cases.
2. **Switch:** unknown which one felt heavy, so the design must work with both the MJTP1117 (1.27–1.86 N) and the TS365ZJ (1.96–2.94 N, possibly offset).
3. **3.68″ sharing:** a key per tub. The light-strip build prints its tub and its own four keys; the crank and pin stay shared. On the 4.26″ both tubs share the face height, so the keys stay shared too.
4. **Pin:** a cut length of 1.75 mm filament, supported at short intervals along its whole length, across the gaps between keys too, and fully captured so it can't bow, turn out of its seats or walk sideways. It must carry the load in bearing and shear rather than bending, so it doesn't snap.

## Design history, in brief

- **Before the rocker:**
  - Codex's first 4.26″ keys (P03) had TPU shoes, a bridge, a keeper and foam: "incredibly fragile" (09-17).
  - A one-part "key comb" flexure concept was never printed.
- **Rev D (09-18):** the current V-seated rocker. A force check showed that the earlier pivot would pull out of its seat.
- **Print 1:** "you really have to press em into the case … I want easy presses". The caps were made prouder.
- **Print 2:** "just about as reliable as you can get".
- **Print 4:** "contact force is too high, try to lower it". Rev I made the ridge R0.6 and the spring arm 0.5 mm (Orca drops a 0.4 mm arm): 9 % lighter.
- **Print 5:** "I'd say it's good".
- **x3:** it inherited the rocker with shorter, lower caps and a narrower spring arm. No x3 print is recorded.
- **2026-09-26:** Ian found the 3.68″ keys heavy and fragile-looking, and the 4.26″ "a bit better, but still a good baseline of force".
- **Throughout:** no other bottom-key mechanism was studied after Rev D. Every revision tuned the same rocker.

## Sources

- **Switch data:**
  - APEM MJTP datasheet (`case-368/hardware/reference/switches/apem-mjtp-through-hole.pdf`): 160 ± 30 gf, 0.25 mm, 100k.
  - SHOU HAN TS365ZJ drawing (LCSC C557598): 250 ± 50 gf. LCSC and JLC list 50k cycles.
  - Alps SKHL series spec (KHL-701): 0.98 N +0.59/−0.39, return force ≥ 0.20 N, plunger static load 29.4 N, 50k.
  - https://tech.alpsalpine.com/e/products/detail/SKQGAFE010/
  - https://tech.alpsalpine.com/e/products/detail/SKRRAAE010/
- **Products:**
  - Kindle Oasis teardown (Electronics360): dome switches on a flex.
  - Game Boy Advance SP and Joy-Con shoulder buttons (iFixit): hinge pin plus torsion spring.
  - Good e-Reader's list of readers with page buttons (PocketBook's are on the bottom bezel).
- **Materials:**
  - Prusament PLA and PETG datasheets: E 2.3 / 1.5 GPa, HDT 55 / 68 °C.
  - OpenFlexure (arXiv 1509.05394): PLA flexures survive about 2.4 % strain only with hard stops.
  - Fictiv's button-design notes: keep printed springs at 20 MPa or less.
  - Ezeh & Susmel 2018: fatigue of printed PLA.
