# Silkscreen enclosures

**The 3D-printed cases for the [Silkscreen](https://github.com/iandchasse/silkscreen-pcb) e-reader**: a 4.26″ case
([`enclosures/case-426`](enclosures/case-426)) and a 3.68″ case ([`enclosures/case-368`](enclosures/case-368)). They
are modelled in CadQuery, checked as they will be printed (the checks read the sliced G-code back), and sliced for
OrcaSlicer. One repo, one folder per size.

**Status.** Both cases are at **Rev L**: bell-crank bottom keys on a 1.75 mm filament rod, held by a printed side
gate. The author has printed both cases from the Elegoo Centauri Carbon 2 plate files in [`print/`](print/). The lid
and tub changes made since 2026-10-19 are not printed yet. The generic OrcaSlicer projects below were sliced and read
back with the OrcaSlicer command line; they have not been opened in the OrcaSlicer GUI, and the generic files
themselves have not been printed.

| To | Go to |
|---|---|
| **Print a case** | [Print a case](#print-a-case) below, then [`print/README.md`](print/README.md) for the steps |
| **Look at one part, or print it from the author's plate files** | [`print/`](print/) |
| **Change a case** | [`enclosures/`](enclosures/README.md): `case-426/` and `case-368/`, their build scripts and design records |
| **The board** | [silkscreen-pcb](https://github.com/iandchasse/silkscreen-pcb) |
| **A light for the reader** | [silkscreen-light-strip](https://github.com/iandchasse/silkscreen-light-strip) and [silkscreen-light-attachment](https://github.com/iandchasse/silkscreen-light-attachment) (see [In development](#in-development-the-light-strip-cases)) |

## Print a case

**The print file is meant to come from the case step of the builder at [silkscreenreader.com/builder](https://silkscreenreader.com/builder).**
It is to hand you one OrcaSlicer project (`.3mf`) for your options, named by its configuration:
`standard-rightkeys.3mf` for a 4.26″ with bottom keys and the right pair of side keys, `368-standard.3mf` for the
3.68″. The files are the generic projects that [`make_plates.py configs`](enclosures/make_plates.py) writes into each
case's `out/configs/` (build outputs, not in git).

**If the builder does not offer the file yet** (as of 2026-10-21 the site has not been updated to serve them), make it
yourself: set up the build as in [Building from source](#building-from-source), build the case, then from `enclosures/`
run `python -B make_plates.py configs --builds standard-rightkeys` (any slug from the table below; for the 3.68″,
`python -B make_plates.py configs --size 368`). The project lands in that case's `out/configs/`. Or print from the
author's [plate files](print/README.md), which are sliced for one printer.

**Use OrcaSlicer.** Open the project, pick your printer, and keep a **0.4 mm nozzle and 0.2 mm layers** (first layer
0.2 too). The keys are exactly 50 layers long, and the raft's air gap and the lid supports' gap are one layer each.
PrusaSlicer, Cura and the others do not read the per-part settings and are not supported.

### What every project contains

- **Presets:** Generic Marlin Printer (0.4 nozzle), 0.20mm Standard, Generic PLA. Every OrcaSlicer install has them.
- **Bed:** the plate layout fits a 220 × 210 mm bed (an Ender-3 class printer, a Prusa MK4, Bambu and larger).
- **Project settings:** no brim, and a one-loop skirt (1 layer, 3 mm away). The job starts on the skirt; peel it off.
  Global supports are off. Everything else is the generic preset (3 walls, 15 % crosshatch infill, 4 top and 3 bottom
  layers, aligned seam).
- **Settings that ride on the parts,** so changing the printer keeps them:
  - the bottom keys and the cranks sit on a **2-layer raft**, with elephant-foot compensation 0; the cranks also use
    Arachne walls;
  - the gates have elephant-foot compensation 0;
  - the lid has manual supports, build plate only, inside one enforcer per side key (5 on a four-key layout, 3 on a
    two-key layout and on the 3.68). Nothing else is supported.
- If OrcaSlicer asks on a printer change whether to keep the project's changed settings, keep them. Do not switch on
  automatic supports.
- **Plates:** plate 1 is the case. A case with bottom keys also has plate 2, four `crank-M` cranks, which you print
  **only for APEM MJTP1117 switches** and use in place of the `crank-T` cranks on plate 1. Boards with SHOU HAN TS365ZJ
  switches, which is every JLCPCB-assembled board, use `crank-T`. There are no test prints in the projects.

### The 4.26″ configurations (16 files)

All 16 are for the touch panel **GDEQ0426T82-FT01C** (touch and frontlight) on the full Silkscreen board. The file name
is the choice you make in the builder:

| Side keys (as you hold it) | Bottom keys, J6 opening | Bottom keys, no J6 | Chinless, J6 opening | Chinless, no J6 |
|---|---|---|---|---|
| All four | `standard` | `standard-nodev` | `chinless` | `chinless-nodev` |
| Left pair | `standard-leftkeys` | `standard-leftkeys-nodev` | `chinless-leftkeys` | `chinless-leftkeys-nodev` |
| Right pair | `standard-rightkeys` | `standard-rightkeys-nodev` | `chinless-rightkeys` | `chinless-rightkeys-nodev` |
| Upper pair | `standard-upperkeys` | `standard-upperkeys-nodev` | `chinless-upperkeys` | `chinless-upperkeys-nodev` |
| **Plate 1** | 41.2–41.6 g, 3 h 19–23 min | same | 32.8–33.1 g, 2 h 26–30 min | same |
| **Plate 2** | 4 `crank-M`: 0.8 g, 7 min | same | none | none |
| **File size** | 1.23–1.25 MB | same | 0.85–0.87 MB | same |

Weights and times are OrcaSlicer's estimates with the generic presets; your printer's times will differ. The exact
figure for every file is in the table under the list below.

- **Bottom keys** (`standard`): four bell-crank keys under the screen (SW9, SW8, SW3, SW2). The case is
  68.2 × 125.0 × 12.7 mm. Plate 1 holds the tub, the lid, the midplate, 4 keys (`key-426`), 4 `crank-T`, 2 gates (one
  is a spare) and the rod jig: 14 objects.
- **Chinless:** no bottom keys; touch does OK and Back. The case is 68.2 × 117.4 × 12.7 mm. Plate 1 holds the tub, the
  lid and the midplate: 3 objects. **The board must not have SW9, SW8, SW3 or SW2:** they hang 1.9 mm past its bottom
  edge into the chin wall. Keep R4.
- **Side keys,** as you hold the reader with the screen toward you: the left pair is SW7 (upper) and SW5 (lower), the
  right pair SW4 (upper) and SW1 (lower), the upper pair SW7 and SW4. Power (SW10, top of the right edge) is on every
  case. A key left out is plain wall; its switch may stay on the board.
- **No J6** (`-nodev`): no opening for the dev header. **The board must not have J6** (the lid's lip runs through it),
  so no clip-on light attachment. With the opening, a board with or without J6 fits.
- A fully populated board fits every bottom-key case with the J6 opening.

<details>
<summary>Exact figures for each of the 16 files (plate 1, generic presets)</summary>

| File | Case | Side keys | J6 opening | Size | Plate 1 |
|---|---|---|---|---|---|
| `standard` | bottom keys | all four | yes | 1.25 MB | 41.21 g, 3 h 22 min |
| `standard-nodev` | bottom keys | all four | no | 1.25 MB | 41.46 g, 3 h 23 min |
| `standard-leftkeys` | bottom keys | left pair | yes | 1.23 MB | 41.26 g, 3 h 19 min |
| `standard-leftkeys-nodev` | bottom keys | left pair | no | 1.24 MB | 41.52 g, 3 h 19 min |
| `standard-rightkeys` | bottom keys | right pair | yes | 1.23 MB | 41.30 g, 3 h 19 min |
| `standard-rightkeys-nodev` | bottom keys | right pair | no | 1.23 MB | 41.55 g, 3 h 20 min |
| `standard-upperkeys` | bottom keys | upper pair | yes | 1.23 MB | 41.28 g, 3 h 19 min |
| `standard-upperkeys-nodev` | bottom keys | upper pair | no | 1.23 MB | 41.53 g, 3 h 19 min |
| `chinless` | chinless | all four | yes | 0.87 MB | 32.76 g, 2 h 30 min |
| `chinless-nodev` | chinless | all four | no | 0.87 MB | 33.01 g, 2 h 30 min |
| `chinless-leftkeys` | chinless | left pair | yes | 0.85 MB | 32.81 g, 2 h 27 min |
| `chinless-leftkeys-nodev` | chinless | left pair | no | 0.85 MB | 33.06 g, 2 h 27 min |
| `chinless-rightkeys` | chinless | right pair | yes | 0.85 MB | 32.84 g, 2 h 26 min |
| `chinless-rightkeys-nodev` | chinless | right pair | no | 0.85 MB | 33.10 g, 2 h 27 min |
| `chinless-upperkeys` | chinless | upper pair | yes | 0.85 MB | 32.82 g, 2 h 26 min |
| `chinless-upperkeys-nodev` | chinless | upper pair | no | 0.85 MB | 33.08 g, 2 h 27 min |

Every bottom-key file also has plate 2: 4 `crank-M`, 0.84 g, 7 min. All 16 pass every slice read-back check (objects all
print, the job starts on the skirt, each key is 50 layers over its raft, a raft under every key and crank no higher
than 0.55 mm, supports only inside the lid's enforcers, side keys standing on a base at least 0.68 mm wide).

</details>

### The 3.68″ (1 file)

`368-standard.3mf`, 1.08 MB: the bare x3 3.68″ 528 × 792 panel, bottom keys, three side keys, no dev-header opening.

| | |
|---|---|
| Case | 68.2 × 108.0 × 12.9 mm (14.4 mm over the keys) |
| Plate 1 | tub, lid (3 side keys, 3 enforcers), midplate, 4 `key-x3std`, 4 `crank-T`, 2 gates (one is a spare), rod jig: 14 objects, 35.50 g, 3 h 14 min |
| Plate 2 | 4 `crank-M`, for APEM MJTP1117 boards only: 0.84 g, 7 min |
| Board | the trimmed x3 board (cut at KiCad y 62; see [silkscreen-pcb](https://github.com/iandchasse/silkscreen-pcb); boards made before its Rev 1.01 need two bodge wires). **No SW5** (a post stands where its key would be). The top key on the left edge, SW7, is the power key: fit R72 and R74, leave off R36 and R73. Side keys: SW7 on the left, SW4 and SW1 on the right. |
| Screws | 4 × M2 × 8 socket head cap (ISO 4762); a pan head also fits; never M2 × 10 |
| Battery | 503035 up to 5.3 mm thick with up to two layers of tape on each face. Push it right, then down until it stops under the lip; tape it. Check where its lead leaves the cell, and its polarity at J5. The lead route is in [`case-368/README.md`](enclosures/case-368/README.md), "The battery". |

### You also need

- **Screws:** 4.26″, three M2 × 10 socket head cap (ISO 4762); a pan head (ISO 7045) also fits. The heads sit flush
  with the back or below it. 3.68″, four M2 × 8 (above).
- **A rod** (bottom-key cases only; not printed): 63.25 mm of 1.75 mm PLA filament, straightened and cut in the rod
  jig that is on plate 1. The steps are in [`print/4.26/ROD.txt`](print/4.26/ROD.txt) and
  [`print/3.68/ROD.txt`](print/3.68/ROD.txt).
- **The gate coupon,** once per printer and filament (bottom-key cases): [`print/4.26/coupon-gate.stl`](print/4.26/coupon-gate.stl)
  or [`print/3.68/coupon-gate-x3std.stl`](print/3.68/coupon-gate-x3std.stl), or plate 3 of the author's plate file.
- **A battery:** a 503035 LiPo, 500 mAh, with a protection board and a JST PH 2.0 2-pin connector. The polarity is not
  standard, so meter it against J5's + before the first plug-in. On the 4.26″, wind the spare lead round the midplate's
  cleats.
- **Assembly:** lay the tub face down on a cloth until the board is in. [`print/README.md`](print/README.md) has the
  steps.

## The `print/` folder

[`print/`](print/) holds the author's own files and every part on its own. Start at [`print/README.md`](print/README.md),
which also lists what to reprint after each design change.

- [`silkscreen-426-plates.3mf`](print/silkscreen-426-plates.3mf) (5.6 MB) and
  [`silkscreen-368-plates.3mf`](print/silkscreen-368-plates.3mf) (3.6 MB): OrcaSlicer plate files set up for an Elegoo
  Centauri Carbon 2 (0.4 nozzle, 0.20 mm Standard, Elegoo PLA, textured PEI), sliced in ElegooSlicer by the author.
  They open in OrcaSlicer too. The 4.26 file has five plates: 1 the standard case, 3 test prints and extras (chin and
  gate coupons, a PCBA test-fit dummy, the rod jig, 4 `crank-M`), 4 the chinless case, and plates 2 and 5, which are
  for the light strip (in development). The 3.68 file has three plates, plate 2 being the light-strip one.
- [`print/4.26/`](print/4.26/) and [`print/3.68/`](print/3.68/): every part on its own, `<part>.stl` in print pose and
  `<part>.step` in the CAD frame, plus `ROD.txt`. A loose STL needs the per-part settings above set by hand.
- [`print/rod-jig.stl`](print/rod-jig.stl) and `.step`: the jig that straightens and cuts the filament rod.

The generic projects are not in `print/`: they are build outputs, meant to be served by the website. To make your own
copies, or CC2 versions of them (`--printer cc2`), run `make_plates.py configs` ([Building](#building-from-source)).

## Layout

| Path | What |
|---|---|
| [`enclosures/case-426/`](enclosures/case-426/) | The 4.26″ project: `src/` (the CadQuery model, the checks, `pipeline.py`), `hardware/` (the board copy, panel drawing, logo, light-strip geometry), `README.md` (the design reference: configurations, mechanisms, checks, history), `requirements.txt` |
| [`enclosures/case-368/`](enclosures/case-368/) | The 3.68″ project, the same shape; `src/build.py` is the entry point |
| [`enclosures/make_plates.py`](enclosures/make_plates.py), [`rod_jig.py`](enclosures/rod_jig.py) | The plate files and per-configuration projects; the rod jig |
| [`enclosures/BELL-CRANK-SPEC.md`](enclosures/BELL-CRANK-SPEC.md), [`SIDE-GATE-SPEC.md`](enclosures/SIDE-GATE-SPEC.md), [`BUTTONS.md`](enclosures/BUTTONS.md) | Design records of the bottom keys |
| [`enclosures/OPEN-WORK.md`](enclosures/OPEN-WORK.md) | Open design work |
| [`print/`](print/) | Files to print (above) |
| [`showcase/`](showcase/) | Source of an interactive 3D page of both cases (see [`showcase/API.md`](showcase/API.md)); its data is generated from each project's `out/` |
| [`docs/images/`](docs/images/) | Figures used by the READMEs |

[`enclosures/README.md`](enclosures/README.md) covers the two projects, what they share, the scripts and the rebuild
order.

## In development: the light-strip cases

Each project can also build a case for the
[Silkscreen light strip](https://github.com/iandchasse/silkscreen-light-strip), a flex PCB frontlight on the board's
J3: the 4.26″ has 16 such configurations, the 3.68″ one build. **These cases are in development and are not released.**
The strip is rev A and untested, and the website does not offer its cases. The builds exist in the source and in plates
2 and 5 of the author's plate files, but nothing here asks you to print them.

A different light, [silkscreen-light-attachment](https://github.com/iandchasse/silkscreen-light-attachment), clips on
to the board's J6. It needs a 4.26″ case with the dev-header opening (not `-nodev`).

## Building from source

- **Python 3.11:** one virtual environment per case, made from that case's `requirements.txt` (CadQuery 2.8, trimesh,
  ezdxf, manifold3d, shapely, scipy, matplotlib and others). Either environment can run the shared scripts.
- **OrcaSlicer 2.4** at its default install path, for the slicing read-backs and the per-configuration projects.
- **KiCad 9** only for `src/prepare_hardware.py`, which re-derives the board files in `hardware/` from a
  silkscreen-pcb checkout. The derived files are already in `hardware/`, so you do not need KiCad to build.
- Run every script with `python -B`. Outputs go to each project's `out/`, which is not in git.

The 4.26″, from `enclosures/case-426`: `src/pipeline.py` builds all 32 configurations and runs their checks (about an
hour from nothing, and cached after). Then, from `enclosures/`, `make_plates.py` writes the plate files,
`make_plates.py configs` writes one generic project per configuration, and `src/configs_slice.py` (back in
`case-426`) slices and checks them.

The 3.68″, from `enclosures/case-368`: `src/build.py`, then for each of the two builds `mechanics.py`, `dummy.py`,
`plates.py`, `slice_check.py` and `lid_close.py`; then, from `enclosures/`, `make_plates.py` and
`make_plates.py configs --size 368`, and `case-426/src/configs_slice.py --size 368`.

The full commands and options are in [`enclosures/README.md`](enclosures/README.md#rebuilding).

## Checks

The point of the checks is that parts fit as printed, so most read the sliced G-code, not the CAD. Each case's README has
a section on them.

- Parts that should be shared between builds are identical (`out/shared-parts.json`), and each of the 32 4.26″
  configurations matches its twins.
- `asprinted.py`: where the lid sits when pressed home, every screw's thread and tip, latch play, and the lid against
  the midplate.
- `lid_close.py`: the latch arms on the way in.
- `slice_check.py`: the as-printed read-back, the detents and the cranks' swing.
- `configs_slice.py`: every generic project, for key layers, side-key bases, supports only inside the enforcers, and a
  job that starts on the skirt.
- 3.68″ only, `bayread.py`: the battery bay and the mid-plane ties.
- `mechanics.py`: key forces and travel.

A few vendor reference files (the panel drawings and the switch datasheets) are not in this repo; each case's
`hardware/reference/SOURCES.md` says where to get them. The builds do not need them.

## Related

- [silkscreen-pcb](https://github.com/iandchasse/silkscreen-pcb): the board. The 4.26″ case takes the full board, the
  3.68″ the trimmed x3 board.
- [silkscreen-light-strip](https://github.com/iandchasse/silkscreen-light-strip): the J3 warm/cool flex frontlight
  (rev A, untested), with its own docs.
- [silkscreen-light-attachment](https://github.com/iandchasse/silkscreen-light-attachment): a clip-on warm/cool light on J6.
- [silkscreenreader.com](https://silkscreenreader.com): the Silkscreen site; its case builder is meant to serve the print files.

## License

CERN-OHL-S-2.0, © 2026 idc LLC. See [LICENSE](LICENSE) and [NOTICE](NOTICE), which also lists the third-party and
copied content (the board layout and the light strip's geometry). The Silkscreen name and logo are not licensed.
