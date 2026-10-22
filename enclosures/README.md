# Enclosures

The two Silkscreen case projects, one per reader size. Each builds a **standard** case and a **light-strip** case
from one code base. The standard case is the released one; the light-strip case is for the
[Silkscreen light strip](https://github.com/iandchasse/silkscreen-light-strip), which is in development and untested,
so the light-strip cases are not released either. The 4.26 builds 32 configurations (since 2026-10-07): either panel, with the bottom keys or
**chinless** (for a board without the four bottom switches), all four page keys or only the left, right or upper pair,
and with or without the dev header (J6) ([`case-426/README.md`](case-426/README.md), "Builds"). What they make to
print goes into the repo's [`print/`](../print/) folder; start at [`print/README.md`](../print/README.md) if you only
want to print a case, and the [top-level README](../README.md#print-a-case) for the generic OrcaSlicer projects that
the website serves.

| | [`case-426/`](case-426/) | [`case-368/`](case-368/) |
|---|---|---|
| Reader | 4.26in: GDEQ0426T82-FT01C touch + frontlight (standard), plain GDEY0426T82 + light strip | 3.68in x3 panel: bare (standard), or with the light strip |
| Board | the Silkscreen board as built | the board cut at KiCad y 62 (`case-368/hardware/reference/board-trim.md`) |
| Differs between the builds | the tub (the lid too between chins, side-key layouts and dev header choices: 32 tubs and 16 lids over the 32 configurations) | the tub and the four bottom keys (`key-x3std`, `key-x3ls`) |
| Writes | [`print/4.26/`](../print/4.26/) | [`print/3.68/`](../print/3.68/) |
| Python | a 3.11 virtual environment made from `case-426/requirements.txt` | a 3.11 virtual environment made from `case-368/requirements.txt` |
| Design reference | [`case-426/README.md`](case-426/README.md) | [`case-368/README.md`](case-368/README.md) |

Current design: **Rev L** (2026-09-28): bell-crank bottom keys on a 63.25 mm filament rod, held by a printed side
gate. Modelled and checked in all builds. Both cases have been printed from the plate files in [`print/`](../print/);
the lid and tub changes made since 2026-10-19 have not.

The folders were renamed on 2026-09-28 (`case-426` and `case-368` were named after the tools that first made them). Each
project needs a Python 3.11 virtual environment made from its own `requirements.txt`; either environment can run the
scripts in this folder. The commands below call it `$py`.

## What is shared

- **Between the two builds of one size:** the lid (with its side keys), the midplate, both cranks and the gate. On the
  4.26 the bottom keys too. `src/build.py` checks this on every full build and stops if a shared part differs
  (`out/shared-parts.json`).
- **Between the 4.26's configurations:** each is checked against its *twins*, the same configuration with one choice at
  its default, and must share every part that choice does not touch: a light-strip case prints its touch twin's lid
  (so 16 lids serve all 32), a chinless case shares the midplate and side keys with its keyed twin, and a side-key
  layout or `-nodev` case shares everything but its tub and lid with its twin (`out/<build>/shared.json`, and every
  claim of a run in `out/shares-all.json`; `case-426/README.md`, "What the builds share").
- **Between the two sizes:** the crank and the gate are the same solids. Their code is kept in step by hand, between
  the `# >>> shared` markers in `case-426/src/keys.py` and `case-368/src/crank.py`. The rod is cut to the same
  length (`ROD_CUT` in both `params.py` files and in `rod_jig.py`: change the three together), so one rod jig serves
  both.
- **Not shared:** each project has its own `hardware/` copy of the board (`board-2026-09-21/`, with its CERN-OHL-S
  `LICENSE` and `NOTICE`, and `board.step`, `footprints.json`, `outline.json`) and of the light strip's geometry
  (`hardware/reference/light-strip/strip-geometry.json`, copied from the strip generator's `build/geometry.json`).

## Each project

| Path | What |
|---|---|
| `README.md` | the design reference: how each mechanism works, how it is checked, what to print, the history |
| `requirements.txt` | the Python packages |
| `src/` | the model (CadQuery) and its checks; `build.py` is the entry point |
| `hardware/` | the inputs: the board, the panel drawing, the logo, the light strip's geometry |
| `out/` | build outputs and reports, per build (`out/standard/`, `out/light-strip/`; on the 4.26 one `out/<slug>/` per configuration, and `out/configs/` with one OrcaSlicer project per configuration); not in git |

## Scripts in this folder

- [`make_plates.py`](make_plates.py) writes the two OrcaSlicer plate files, `print/silkscreen-426-plates.3mf` (four
  plates: the standard case, the APEM cranks, the chinless case, test prints) and `print/silkscreen-368-plates.3mf`
  (three: the case, the cranks, test prints), from each print build's oriented STLs. They are generic OrcaSlicer
  projects (Generic Marlin Printer, 0.20mm Standard, Generic PLA; a 220 x 210 mm bed) holding the released builds only;
  the plates are the per-configuration projects' plates. `make_plates.py --printer cc2` writes the author's Elegoo CC2
  versions, every build included (the light-strip ones too), into `print/cc2-local/` (not in git). A project's
  `Metadata/project_settings.config` holds OrcaSlicer's whole key set (`orca-project-defaults.json`, made by
  `make_plates.py defaults` with the installed OrcaSlicer's command line; remake it after an OrcaSlicer update), with
  the stock presets over it: OrcaSlicer 2.3.2 and later crash on a project that has no `filament_colour`. It also reads each build's CAD-frame
  `lid.stl` and `skey_*.stl` (from build.py) to place a support enforcer under each side key's hinge notch: the lid
  is the only object with supports, and only there (manual mode). Run it after build.py and plates.py.
  `make_plates.py configs [--builds a,b]` writes one OrcaSlicer project per 4.26 configuration (all 32 by default)
  into `case-426/out/configs/<slug>.3mf` (not in git): that configuration's parts on one plate, with the same
  settings, plus a plate of APEM cranks when it has bottom keys (`case-426/README.md`, "What the builds share").
  `make_plates.py configs --size 368` does the same for the 3.68's one released configuration, the standard build,
  into `case-368/out/configs/standard.3mf` (`case-368/README.md`, "Print files"). Both take `--printer generic` (the
  default: OrcaSlicer's generic presets, what the website serves) or `cc2` (Ian's Elegoo CC2, `out/configs-cc2/`);
  `case-426/src/configs_slice.py [--size 368]` slices them and reads them back.
- [`rod_jig.py`](rod_jig.py) writes the rod jig, `print/rod-jig.stl` and `.step`.

## Design records

- [`BELL-CRANK-SPEC.md`](BELL-CRANK-SPEC.md): the bottom keys' mechanism (bell crank, sliding key, filament rod), with
  the parts the side gate replaced marked "Superseded".
- [`SIDE-GATE-SPEC.md`](SIDE-GATE-SPEC.md): the rod's printed side gate, "SPEC2 rev 3" in the code's comments.
- [`BUTTONS.md`](BUTTONS.md): why the bell crank: the old rocker keys' problems, the options studied, and Ian's
  decisions of 2026-09-26.

## Rebuilding

Each project runs with its own Python, from its own folder. On the 4.26 one command runs the whole pipeline: all 32
configurations and their checks, then for each one `mechanics.py`, `dummy.py`, `plates.py` and `slice_check.py`, the
shared-part checks, `print/4.26/`, the cross-project crank check, both plate files (`make_plates.py`) and one
OrcaSlicer project per configuration, sliced and read back (`make_plates.py configs`, `src/configs_slice.py`, into
`case-426/out/configs/`). In PowerShell:

```powershell
cd case-426
$py = '<path to the 4.26 venv>\Scripts\python.exe'
& $py -B src/pipeline.py                 # everything (all 32: about 1 h from nothing; about 80 s when nothing changed)
& $py -B src/pipeline.py --builds six    # the six builds of before the variants and the print builds
& $py -B src/pipeline.py --builds chinless-upperkeys   # one configuration (and its twins) -> out/configs/<slug>.3mf
& $py -B src/pipeline.py --builds standard,chinless --steps build,mechanics   # part of it (and what that needs)
& $py -B src/pipeline.py --quick         # iterate: the parts, then only the checks whose parts changed
& $py -B src/pipeline.py --dry-run --why # what would run, and why
```

**It is cached** (`out/.cache/`, not in git). A step is one script for one build, as before. A step whose inputs
have not changed since a run that is in the cache does not run: its files are restored byte for byte. Its inputs are
the source of every `src/` module it imports (`params.py` is one of them, so any parameter edit reruns every step),
the `hardware/` files, the build, the Python packages, and the files it reads from the steps before it. The cache
never serves a result made from other inputs; `case-426/README.md`, "Building each", has the rules. Inside the
steps, OrcaSlicer's slices are also cached, and every build that slices the same file shares them. Steps
run side by side: a build's scripts start as soon as its parts are written, as many at once as the CPU cores and the
free memory allow (the pipeline keeps 8 GB of commit charge free). A check whose inputs are the same in
two builds (the strip check, the bottom keys' check, `mechanics.py`'s slow sweeps) runs once, behind a guard that
compares what the check reads in the regions it reads (the parts' triangles and solids there, the hardware near them,
the `params.py` values its code can reach); every shared result is byte-identical to the build's own. All 32 took 58 minutes
cold on 2026-10-10 (2 h 12 min before the scheduler and the shares) and 78-79 s when nothing had changed.
`--no-cache` runs everything again; `--verify` reruns the cached steps and checks they give the same files, and with
`--unshared` every build runs every check itself (with `--verify`, the audit of the shares: each build's own reports
and `mechanics.json` are compared with the shared ones).

The old commands still work. `build.py` with no variant (and with `--only`) runs its builds through the pipeline, so
it uses the cache too. `mechanics.py`, `dummy.py`, `plates.py` and `slice_check.py` with `SILKSCREEN_VARIANT` set run
in full as before; only their OrcaSlicer results come from the cache:

```powershell
& $py -B src/build.py            # the four print builds and their checks, the shared-part checks, then print/4.26/
foreach ($v in 'standard', 'light-strip', 'chinless', 'light-strip-chinless') {
    $env:SILKSCREEN_VARIANT = $v
    & $py -B src/mechanics.py    # forces and sweeps -> out/<build>/mechanics.json
    & $py -B src/dummy.py        # the PCBA test-fit dummy -> out/<build>/pcba-dummy.stl
    & $py -B src/plates.py       # print orientation and overhang audit -> out/<build>/print/
}
Remove-Item Env:SILKSCREEN_VARIANT   # or build.py builds only that one next time
& $py -B src/build.py --only standard-nodev,chinless-nodev   # other 4.26 builds, side by side; print/4.26/ untouched
```

The 4.26's third print build, `chinless`, has no bottom keys and a 117.4 mm case; its board must not have
SW9/SW8/SW3/SW2 fitted. It has its own tub and lid in `print/4.26/` (`tub-chinless`, `lid-chinless`) and is plate 4
of the 4.26 plate file. The fourth, `light-strip-chinless` (the same with the light strip's panel), has its own tub
(`tub-light-strip-chinless`) and prints the chinless lid: plate 5. So run `mechanics.py`, `dummy.py` and `plates.py`
for both too (the loop above) before `make_plates.py`. Any other configuration (`-nodev`: J6 not fitted; a side-key
layout) builds and checks, with no files in `print/`: its OrcaSlicer project is `case-426/out/configs/<slug>.3mf`
(build output, not in git; the website serves the generic ones at [silkscreenreader.com/builder](https://silkscreenreader.com/builder), see the [top-level README](../README.md#print-a-case)). See `case-426/README.md`, "Builds", for the
32 configurations and what each needs on the board.

The same for `case-368` with the 3.68's own Python, for its two builds
(`standard`, `light-strip`). Each README's
pipeline section lists the optional steps (slicing read-back, section drawings, comparison, the board import). Then,
from this folder (`pipeline.py` runs `make_plates.py` itself, so this is only needed after a 3.68 change):

```powershell
& $py -B rod_jig.py      # only when the rod changes
& $py -B make_plates.py  # the two public plate files (4.26: plates 1-4); --printer cc2: print/cc2-local/, the author's, every build
```

Last, the showcase reads both projects' `out/` and the repo's `print/4.26/` and `print/3.68/`: run its
two adapters and the bundler ([`../showcase/API.md`](../showcase/API.md)).
