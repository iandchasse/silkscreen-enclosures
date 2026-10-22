# 3.68in (x3) PCB trim audit

Audit date: 2026-09-24. This is a mechanical design audit of the user's proposed
removal of the narrow upper PCBA extension above the battery connector. It is not
an electrical sign-off or proof that a physically cut board will operate.

## Source and coordinate frame

Only copies already inside this workspace were read:

- `README.md`: existing Rev K assembly, mechanism and hardware description.
- `hardware/board-2026-09-21/silkscreen_pcb.kicad_pcb`: actual footprint pads,
  copper segments, vias and net names.
- `hardware/footprints.json`, `hardware/mechanical.json`, `hardware/outline.json`:
  local mechanical extraction and STEP component bounds.
- `src/hw.py`, `src/params.py`, `src/prepare_hardware.py`: existing geometry,
  component indexing and the local s-expression parser. The parser was imported
  with bytecode writing disabled; its export routine was not run.

The prior documentation is design evidence, not a new request from the user.
No external project was read, and no board file or CAD source was changed by this
audit. Coordinates below are millimetres in the existing CAD frame:
X = KiCad X - 44.24; Y = 148.25 - KiCad Y. Higher Y is the upper header end.

## Mechanical cut candidate

**Recommended design datum: retain material at Y <= 86.25 mm** (KiCad Y = 62.00).
The straight cut crosses only the narrow extension, from approximately
X = 40.1686 to 59.9975, a width of 19.8288 mm. It joins the existing sloped notch
edge to the right PCB edge. This is a nominal finished-edge location, not an
allowance for a particular cutting tool or kerf.

The battery connector J5 model reaches Y = 84.70, leaving 1.55 mm to this datum.
Its footprint courtyard reaches Y = 85.20, leaving 1.05 mm. The upper battery pad
centre is (50.6100, 82.7500), a 0.75 mm plated hole with 1.20 x 1.75 mm pad size.
R62's footprint, which stays on the board but is removed for the power rework (below), is around Y = 81.85. The first removed component
bodies start at Y = 88.00 (CR2) and 88.10 (D3).

An initially considered Y = 85.50 edge leaves only 0.80 mm above the connector
body and 0.30 mm above its courtyard. It also cuts a ground via: the board has a
0.60 mm via centred at (53.11, 85.55). The Y = 86.25 datum instead clears that
via's copper outer diameter by 0.40 mm. Neither datum avoids copper tracks.

## What is removed and retained

| Removed reference | Function / relevant net relationship |
|---|---|
| SW10 | Existing power/wake pushbutton; connects 3V3 to R62's input net when pressed |
| J6 | Upper expansion header |
| H1 | Upper mounting hole at (50.0011, 96.6043) |
| F2 | Fuse from P+ to the J6 `/P+_FUSE` branch |
| CR2 | 3V3-to-ground protection device |
| CR3 | `/P+_FUSE`-to-ground protection device |
| D3 | LED_SW-to-ground protection device |
| D8 | C-/W- protection device |
| U8 | Protection for UNUSED_GPIO_45, I2C_SCL, I2C_SDA, UNUSED_GPIO_3 |

The battery connector J5, microSD socket J7, USB connector J1, display connector
J2 and other lower-board components remain. H2/H3/H4/H5/H6 remain; H1 does not.
The retained PCB has SW1/SW4 on the right and SW5/SW7 footprints on the left.
For the user's 3.68in (x3) assembly, SW5 (DWN2) is unpopulated and SW7 (UP2) becomes
the power/wake button using the resistor population changes documented below.
The bottom row SW9/SW8/SW3/SW2 and reset SW11 remain.

## Copper crossing the proposed edge

The KiCad board has 12 routed segment centreline crossings at Y = 86.25,
representing 11 nets. Values below are derived from the segment endpoints,
not estimated from a picture. The board also contains GND copper zones on both
faces; ground copper must be treated as present at the cut, even where no routed
ground segment is listed. No cut-edge DRC or ground-plane continuity analysis
was performed.

| CAD X at crossing | Layer | Net | Track width |
|---:|---|---|---:|
| 41.0600 | B.Cu | UNUSED_GPIO_3 | 0.20 |
| 41.1600 | F.Cu | UNUSED_GPIO_46 | 0.20 |
| 41.5110 | F.Cu | UNUSED_GPIO_45 | 0.20 |
| 43.1600 | F.Cu | P+ | 0.40 |
| 43.2860 | B.Cu | 3V3 | 0.25 |
| 51.8600 | F.Cu | I2C_SCL | 0.20 |
| 53.6600 | F.Cu | I2C_SDA | 0.20 |
| 54.1600 | F.Cu | LED_SW | 0.20 |
| 56.3600 | B.Cu | 3V3 | 0.25 |
| 57.7090 | F.Cu | W- | 0.20 |
| 57.8725 | B.Cu | Net-(R62-Pad1) | 0.20 |
| 58.0600 | F.Cu | C- | 0.20 |

The inspected alternatives at Y = 85.0, 85.5, 86.0, 86.5 and 87.0 all have
the same crossing count and net set. There is no demonstrated copper-free cut
in that interval. Exposed power, signal and ground copper means the mechanical
clearance result cannot be presented as permission to energize an uninspected
trimmed board.

## Specific power-button and power-path impact

SW10 pad 2 is on 3V3. SW10 pad 1 joins R62 pad 1 through
`Net-(R62-Pad1)`, which is severed by the cut. R62 is a 10 kOhm resistor, still on the board
on a sawn stub; its pad 2 is `PWR_BUTTON`. That signal also reaches the retained ESP32-S3 U4
pad 11 and R76 (100 kOhm to GND), plus C29 and the DNP R72 alternative network.
Consequently **the existing physical SW10 power/wake button is removed**, and
its normal 3V3 assertion through R62 is lost. An enclosure must not retain an
apparently functional SW10 button. The user's subsequent instruction explicitly
supplies the alternative: reroute power/wake to UP2 with two resistor population
and two depopulation changes, leave DWN2 unpopulated, and use the other side for
page turns. The mapping and existing board provisions were verified as follows.

### User-selected UP2 power conversion

The board's explicit F.SilkS labels are `UP2`, `DWN2`, `UP1`, and `DWN1`.
Their positions relative to the switch pads, together with the unique SW7
power-selection resistor network, identify the switches; this mapping is not
based solely on assuming which physical side should carry which function.

| Board label | Reference | Plunger location in CAD frame | x3 role |
|---|---|---|---|
| UP2 | SW7 | left edge, Y = 75.5 | Power/wake |
| DWN2 | SW5 | left edge, Y = 61.5 | Unpopulated; no case key or opening |
| UP1 | SW4 | right edge, Y = 75.5 | Page up |
| DWN1 | SW1 | right edge, Y = 61.5 | Page down |

The two-populate/three-depopulate provision in this local board is:

| Change | Reference and board value | Local board status | Electrical connection |
|---|---|---|---|
| Populate | R72, 10 kOhm | DNP | SW7 pad 2 (`Net-(R36-Pad1)`) to `PWR_BUTTON` |
| Populate | R74, 0 Ohm | DNP | 3V3 to SW7 pad 1 (`Net-(R73-Pad2)`) |
| Depopulate | R36, 68 kOhm | Populated | Disconnects SW7 pad 2 from `BUTTON_ADC_2` |
| Depopulate | R73, 0 Ohm | Populated | Disconnects SW7 pad 1 from GND |
| Depopulate | R62, 10 kOhm | Populated | SW10's old series resistor; left in, it loads `PWR_BUTTON` (below) |

After those population changes, pressing SW7 provides the intended path
`3V3 -> R74 -> SW7 -> R72 -> PWR_BUTTON`, while the retained R76 supplies its
100 kOhm ground pull-down. R73 must be absent in that configuration: keeping it
while fitting R74 directly connects 3V3 to GND through the two zero-ohm links.
R72 is a **10 kOhm resistor in the source board**, not a zero-ohm jumper.

**R62 is removed for the rework** (Ian, 2026-10-22). It is SW10's series resistor and, after the cut, sits on a sawn
stub. Left in place, a saw burr bridging the stub to GND would make it a divider with R72 and hold `PWR_BUTTON` at
about 1.57 V, below what the ESP32-S3 reads as high. The case needs no R62; its footprint stays in the geometry facts
above and the CAD model keeps its body.

This verifies that the local PCB contains the exact selectable network needed
for the user's plan. It does not certify a completed rework, the user's actual
assembled resistor values, firmware behaviour, or operation after cutting.
No KiCad board population flags or physical hardware were changed by this audit.
The enclosure should therefore provide three side actuators: SW7 power on the
left, and SW4/SW1 page up/down on the right.

J5's B+ and B- battery nets do not cross the proposed cut. The principal lower
power components U11 (TP4056 charger), U2 (TPS2116 power mux), U3 (TLV75533
regulator), U5 (DW01A protection IC), Q1 (FS8205A) and Q3 remain physically
below it. F2 is the expansion-header P+ branch fuse, not a demonstrated series
fuse in the retained J5 battery connection: its pads are P+ and `/P+_FUSE`, and
the latter net goes to J6 and CR3. These net relationships support the intended
removal of the expansion branch, but do not prove post-cut routing continuity,
protection behaviour, booting, battery operation or charging. In particular,
3V3 crosses the edge twice and GND uses pours; pad membership alone is not a
full connectivity or physical damage analysis.

## Enclosure implications

- Clip the board reference and hardware model at the chosen cut datum, and
  omit the removed component solids in both inspection and interference checks.
- Remove H1's midplate snap and lid support, and remove the SW10 side-key
  actuator and wall opening. Also omit the SW5/DWN2 actuator and opening for
  the user-selected unpopulated switch. Keep SW7/UP2 as the power actuator and
  SW4/SW1 as page-turn actuators. Preserve H2/H3/H4/H5/H6 registration and
  lower connectors/buttons.
- J6 no longer sets rear clearance. J5 still reaches Z = -4.935 mm and its
  front-side leads reach Z = +3.315 mm in the raw model. Removing the header
  therefore saves at most about 0.23 mm of rear depth if the battery and other
  stack datums stay as before; it does not justify a large thickness reduction.
- The old battery placement occupies Y = 82.0..113.1. Keeping it there retains
  the old overall height even after shortening the PCB and display. A shorter
  case needs a deliberate battery relocation and revised retention/cable path.
  Do not resize the actual supplied cell to fit a desired envelope.
- Screen support, new glass pocket, aperture and single display tail need their
  own analysis from the new drawing. The PCB trim by itself does not establish
  FPC contact orientation, pin mapping or connector electrical compatibility.
- Exclude the cut edge from close-fitting hard stops until real edge finishing
  tolerance is established. Keep the enclosure assumptions visible in the
  prototype assembly notes.

## Verification boundary

This audit checked local component bounds, footprint and pad net assignments,
straight-track centreline intersections and nearby via position. It did not
alter or refill KiCad copper, run ERC/DRC, validate firmware, reconstruct every
pad-to-pad route, certify a safe cutting process, or test hardware. The CAD
variant may be built as a mechanical prototype while those electrical and
physical validations remain explicitly unresolved.
