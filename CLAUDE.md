# Notes for coding agents

Ian (idc LLC) owns this project: the two Silkscreen cases, `enclosures/case-426` (4.26", 32 configurations) and
`enclosures/case-368` (3.68", the x3 build). This file covers how to work here and how to check CAD so that it holds up
on the printer. Open design work is in `enclosures/OPEN-WORK.md`. Machine paths and other local notes are in
`CLAUDE.local.md` (not in git); read it first if it exists.

## Ground rules

- **Commits:** plain messages, with no `Co-Authored-By` or other attribution trailer (public repo).
- **Branches:** work on a branch in a git worktree on a short path (`CLAUDE.local.md` has an example). OrcaSlicer fails
  when a `.gcode` path is 244 characters or longer. Merge to `main` fast-forward only, after a verifier. Copy the
  untracked inputs (`enclosures/*/hardware/cache`, the board-derived files) into the worktree read-only.
- **One heavy CAD or slicer process per agent**, and mind the machine's memory (`CLAUDE.local.md`).
- **The website** (a separate private project) is not ours to push or deploy. Site changes go to the website agent as a
  written prompt; `print/SITE-BUILDER-NOTE.md` is the standing brief. It is a local file (git-ignored): keep it
  up to date on disk, never commit it. Light-strip configurations are unreleased: the site shows none.
- **Never commit** `out/`, `hardware/cache/`, `hardware/compare/`, `reference/retrocase/`, vendor PDFs or drawings,
  G-code, or `CLAUDE.local.md`. `.gitignore` covers them; don't force-add.
- **The light strip** is a separate repo (silkscreen-light-strip). Its geometry reaches the cases only through
  `hardware/reference/light-strip/strip-geometry.json` (one copy per case, identical); `docs/images/optics_heatmaps.png`
  is a copy of its optics model for the showcase.

## What Ian wants

- **Parts fit as printed.** No sanding, no tuning prints. Never ask him to measure anything.
- **Supports:** none, except the lid's side-key enforcers.
- **Simple:** few parts. Bought hardware is screws only: M2 socket head caps (ISO 4762) are what he uses, and a pan
  head must also fit. The 3.68 takes four M2 x 8, the 4.26 three M2 x 10.
- **Slicers:** OrcaSlicer only. Other slicers are not supported. Ian prints on an Elegoo Centauri Carbon 2 (CC2) and
  slices `print/cc2-local/*-plates.3mf` (git-ignored; `make_plates.py --printer cc2`, every build) in ElegooSlicer.
  The public `print/*-plates.3mf` and the site's projects (`make_plates.py configs`) are OrcaSlicer generic projects,
  the released builds only. Every public 3MF must open in a current OrcaSlicer: `project_settings()` writes the whole key
  set (`orca-project-defaults.json`) and asserts `filament_colour`; 2.3.2 and later crash without it. Don't launch a
  slicer GUI to check; use the OrcaSlicer CLI.
- **Pictures first.** Show him pictures before building anything he would see on the outside.
- **Verification in proportion.** Geometry and print files deserve proof from the G-code. Tooling tweaks get one check.
  One verifier, at most one fix round; don't loop auditors. Keep agent waves small, and have agents write their
  reports early and append as they go.

## How to inspect the CAD so it holds up on the printer

Every 3.68 failure in October 2026 passed in CAD and failed on the printer: latches bent onto the midplate, side keys
with no first layer, the crank rubbing the slot roof, bottom screws with 2 mm of thread, a slit in the power key's (SW7's) nub,
backstops 0.065 mm too tall. The method that caught each one:

1. **Judge the part as printed, not as drawn.** Slice with the CC2 plate file's presets (OrcaSlicer 2.4 CLI; the
   ElegooSlicer CLI refuses the plate files) and read the G-code back. Count only what the slicer lays.
2. **Use Ian's real G-code when it exists.** It records what he actually printed, including deleted objects and the
   order of the job. `CLAUDE.local.md` says where ElegooSlicer leaves an uploaded job; copy it at once, into
   `enclosures/<case>/out/ian-prints/` (out/ is git-ignored).
3. **Fit frames; don't assume them.**
   - Fit bed-to-CAD placement from features such as the counterbores and walls. For example, the 3.68 lid on plate 1
     sat at bed = CAD + (119.153, 129.35, 8.235) before the bay lid, and at Z + 8.435 since (the lid's Z is -Z_BACK, so
     it moves with Z_BACK); the tub at (x + 43.473, 218.55 - y, 4.47 - z).
   - Check the header's `extruder_offset`: on these files it adds 1.5 mm in Y.
   - Ian's "left/right facing the back" is mirrored: his left on the back is CAD +X.
4. **Check fits at the as-printed home.**
   - Slicers drop partial layers at rims and posts, so a lid pressed home does not sit at its CAD position. The 3.68
     sits +0.105 (`params.LID_HOME_DZ`), the 4.26 -0.100.
   - A feature prints to the layer whose mid-plane is under its CAD top (the backstops came out 0.065 tall).
   - Design heights in whole layers counted from the bed.
5. **Run the read-backs, and add one for each new kind of failure.**
   - `src/asprinted.py` (both cases, called from `slice_check`) covers the lid's home, every screw, latch play and
     lid-vs-midplate overlap. For each screw it checks:
     - at least 3.0 mm of thread in the pilot hole, with the lid home and with it 0.3 mm open (the last ~0.8 mm of
       the screw is its tapered point and doesn't count as thread);
     - the tip short of the pilot's end, and at least 0.8 mm of plastic left in front of it;
     - a socket head flush or below the back.
     It also reads (3.68 only) the board's room at the tub's bosses under its bottom mounting holes (H3/H4) (`board_room`: FAIL under 0.20 with a
     +0.16 board; bosses only, the midplate's 0.13 / 0.03 is not read).
   - `asprinted.usb_fit` (both cases, `slice_check`): the USB port as laid, against an 8.25 x 2.40 plug centred in the
     board Rev 1.0 socket and in Rev 1.02's (0.14 nearer the board), each seated 0.085 nearer the board than KiCad draws it,
     with the lid at home and the board on its posts. FAIL under 0.10 on any of the hole's four flats (the corners are
     printed, not graded). It failed on main (Rev 1.02 -0.07 on the board side) and passes in all 32 + 2 builds.
   - `community.py` (both cases, identical; `build.py` runs it on every build -> `community.json`) and `slice_check`'s rows for the
     2026-10-23 changes: no seam V, pads 1.2 proud, the midplate's pins (as laid: one piece, 1.80 or more across), the back
     wordmark open and the chin plain as laid, the two-colour inlays filling their recesses, and the 4.26 top screw's relief
     (its pilot starts at 1.6, 3.6 mm of thread). Their limits are Ian's literal numbers, so they failed on main and pass now.
     `configs_slice.two_colour()` reads the two-colour lid plate by tool.
   - `lid_close.py` (latch arms bent on the way in).
   - `slice_check.detent_join` and the crank free-swing check.
   - `case-426/src/configs_slice.py` (key layers, side-key zones, what each key stands on at the bed
     (`side_key_base`), and that the job starts on the skirt).
   - `case-368/src/bayread.py`, run by `slice_check` (the battery bay: cell air, lip, lead reach, the cut zone, the
     backstops' gap, ribs, and `midplane_ties`, which fails any height that sits on a layer's mid-plane).
   - A new check must FAIL on the old design and PASS on the new one, shown both ways.
6. **Measure walls in the built STL or the G-code, never from a plan.** A study said 0.70 mm round a new pilot; the
   built tub had 0.45 and 0.20.
7. **Mind the job's order and seams.**
   - The job's first line used to be SW7's support; the one-loop skirt fixes that.
   - Seam placement is a near tie on the side keys' nubs: any mesh change can move a seam onto a nub, and a painted
     seam enforcer doesn't help.
8. **Keep forces in the picture, not just interference.**
   - The midplate springs push the lid with about 10 N.
   - The 3.68 lid gives 0.27 mm per N at the back's centre.
   - Latches let go at about 0.45 mm of lift.
   - Plate-file settings can't stiffen the lid: its back and pocket floor already print 100% solid.
9. **Give every diagnosis a skeptic.** Re-derive it independently with your own scripts from the G-code. Mark a claim
   confirmed only with your own evidence, unproven when the evidence is thin. Then give Ian the one cheap test or
   photo that decides between the candidates. Never present a hypothesis as the cause.

## Building

Run every script with `-B`, with the Python named in `CLAUDE.local.md` (absolute paths, since relative ones break
from a worktree): one venv for the 3.68, one for the 4.26 and the shared tools (`make_plates.py`, `configs_slice.py`,
the showcase). Each is a Python 3.11 venv made from that case's `requirements.txt`.

The 3.68 chain, from `enclosures/case-368`:
1. Run `src/build.py`.
2. Then, for `SILKSCREEN_VARIANT` = `standard` and `light-strip`, run `src/mechanics.py`, `src/dummy.py`,
   `src/plates.py`, `src/slice_check.py` and `src/lid_close.py`.
3. From `enclosures/`, run `make_plates.py` and `make_plates.py configs --size 368`, adding `--printer cc2` for Ian's
   own files (`make_plates.py --printer cc2` writes his CC2 plate files, light strip included, into
   `print/cc2-local/`).
4. From `enclosures/case-426`, run `src/configs_slice.py --size 368`, with `--printer cc2` for Ian's files.
5. Afterwards, restore `print/3.68/key-x3*` from HEAD if only OCC byte noise changed them.

The 4.26:
1. From `enclosures/case-426`, run `src/pipeline.py`. It has a step cache and a memory-budget scheduler, so let it run
   alone. `--unshared --verify` runs the full audit. The step cache is keyed on the project's absolute path: after the
   folder moves, the first run is a cold one (about an hour for all 32); OrcaSlicer's slices are memoised by content
   and survive a move. Its `plates3mf` step writes only the public generic plate files, never Ian's CC2 files in
   `print/cc2-local/`: step 2 refreshes those, so don't skip it.
2. From `enclosures/`, run `make_plates.py`, then `make_plates.py configs` and `make_plates.py configs --printer cc2`
   (and `make_plates.py --printer cc2` for his CC2 plate files).
3. From `enclosures/case-426`, run `src/configs_slice.py`, and again with `--printer cc2`.

After a merge:
- `out/` is not in git. Sync the worktree's `enclosures/*/out` into the main checkout; `out/configs*` must mirror the
  build exactly, with no stale `library/*.dfl`.
- The showcase: `showcase/gen/adapt_368.py` and `adapt_426.py`, then `bundle.py --strict-page`, then
  `sc_contract.py --bundle` (see `showcase/API.md`). Only `docs/showcase/index.html` and `manifest.json` are tracked.
- When a 3.68 or 4.26 change reaches the site's files, add a dated entry to `print/SITE-BUILDER-NOTE.md` (local).

## Method lessons

- A height on a layer's mid-plane flips between slices (the end stop at 1.9, the bay walls at 5.1, the logo and
  grooves at 0.3). Design in whole layers counted from the bed, and keep `midplane_ties` green.
- A read-back must look at what a part stands on, not only at what floats: the keys passed `side_key_read` (nothing
  floats) while standing on a single bead.
- A thicker arm from a model study met the board in `lid_close`. Run `lid_close` on any latch change before proposing
  it to Ian.
- Run a new check on the old design first and show it FAIL; only then change the geometry.
