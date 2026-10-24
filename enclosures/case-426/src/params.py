"""Design parameters for the Silkscreen enclosure. Millimetres, CAD frame from hw.py:
X = KiCad X - 44.24, Y = 148.25 - KiCad Y, Z = 0 at the PCB rear face, +Z toward the screen.

Everything that sets a fit or a stack height lives here, with the reason next to it.
"""
import math
import os
import hw

# ---- configuration -----------------------------------------------------------------------
# One project builds every configuration of the Rev K case (2026-10-07: 32 of them). variants.py holds the grammar
# and the tables; each axis is read from the slug here, once, and every geometry gate reads its flag, never the name:
#   panel  LIGHT_STRIP   standard: the GDEQ0426T82-FT01C touch + frontlight panel on the lip. light-strip: the
#                        plain GDEY0426T82 with the Silkscreen light strip on its left border (the light-strip block at
#                        the end of this file): its own tub, every other part the standard's
#   chin   BOTTOM_KEYS   bottom keys (BACK OK LEFT RIGHT: keys, cranks, rod, gate), or chinless (2026-10-04, Ian:
#                        "touch-centric"): no keys, cranks, rod, gate, rail, openings or slots. A chinless board must
#                        have SW9/SW8/SW3/SW2 NOT fitted (they hang 1.92 past the board's bottom edge). Its chin is the
#                        shortest safe one (BOT_IN): 117.4 mm tall, not 125.0. The light-strip chinless (Ian,
#                        2026-10-07: it "is the chinless build") is the chinless chin + the light-strip front: it has
#                        no touch and no bottom row, so its keys are the page keys and power
#   sides  TAB_ROOTS     the page keys the case has (variants.SIDE_SETS): all four, the left pair, the right pair or
#                        the upper pair; power (SW10: the RIGHT edge, at the top) on every case. LEFT/RIGHT as held,
#                        screen toward you: CAD +X is the user's RIGHT. A key left out is the plain wall in the tub
#                        and the lid; its switch may stay fitted (it is never pressed, and the lid's lip still ducks
#                        under it: joint.switch_spans), so every board fits every layout
#   dev    DEV_HEADER    nodev: J6 (the dev / expansion header) NOT fitted: the top wall's header opening in the tub
#                        and the lid is closed and the top tongue runs on past the top screw (TONGUE_RUNS). The lid's
#                        new lip there passes through a fitted J6's body, so the board must not have it (and so no
#                        light attachment)
# slug = <base>[-leftkeys|-rightkeys|-upperkeys][-nodev], base = standard | light-strip | chinless |
# light-strip-chinless (variants.py). Each process builds one, chosen by SILKSCREEN_VARIANT = <slug>, e.g.
# 'standard-nodev'; its parts go to out/<that slug>/. build.py with none set runs PRINT_BUILDS, checks the shared
# parts and writes print/4.26/. light-strip is the default: this project was the light-strip copy before it held
# both, so a script run on its own still builds what it built before.
import variants
PRINT_BUILDS = variants.PRINT_BUILDS       # build.py with no variant: these, and print/4.26/ from them


def parse_build(slug):
    """'<base>[-<option>...]' -> (base, options). Raises ValueError on anything else (variants.parse)."""
    c = variants.parse(slug)
    return c.base, c.opts


BUILD = os.environ.get('SILKSCREEN_VARIANT', 'light-strip')
CFG = variants.parse(BUILD)
VARIANT, OPTS = CFG.base, CFG.opts        # labels only (the showcase adapters assert on VARIANT)
PANEL = CFG.panel
LIGHT_STRIP = PANEL == 'light-strip'
BOTTOM_KEYS = CFG.bottom_keys             # the bottom row: keys, cranks, rod and gate (every bottom-key feature is
                                          # gated on this, never on an empty KEY_REFS)
DEV_HEADER = CFG.dev                      # J6 fitted: the header opening in the top wall
SIDES = CFG.sides                         # 'all' | 'leftkeys' | 'rightkeys' | 'upperkeys'
SIDE_REFS = variants.SIDE_SETS[SIDES]     # the side keys this case has, by ref (TAB_ROOTS, below, keeps only these)
OUT = hw.ROOT / 'out' / BUILD              # each build's parts, checks and print files, side by side
OUT.mkdir(parents=True, exist_ok=True)
# what the build's board does not have fitted: those parts leave the 3D hardware model (hw.solids), so no check
# sees them; the footprints (the midplate's lead holes) are never filtered
hw.DNP = frozenset(([] if BOTTOM_KEYS else hw.BOTTOM_SWITCHES) + ([] if DEV_HEADER else ['J6']))

# ---- printing -------------------------------------------------------------------------
NOZZLE = 0.4
LAYER = 0.2
FIT = 0.20            # sliding / drop-in clearance per side for printed-to-hardware fits
LOOSE = 0.30          # clearance for moving printed parts

# ---- Z stack (front to back) ------------------------------------------------------------
PCB_REAR = 0.0
PCB_FRONT = hw.PCB_T                      # 1.6
LEAD_TIP = 2.35                           # through-hole lead tips, trimmed (MJTP1117 pins stand 0.71 proud).
                                          # J5's leads stand 1.72 and J6's 1.47 as modelled: untrimmed they
                                          # reach the display's rear at DISP_REAR (build.interference does not
                                          # test the display against the board), so trim them to this

MID_REAR = 2.0                            # midplate rear face: 0.4 above the PCB, cut out around every lead
MID_T = 1.0
DISP_REAR = MID_REAR + MID_T              # 3.0  display rests on the midplate
DISP_FRONT = DISP_REAR + hw.PANEL_T       # 4.98 nominal (+-0.2 per drawing)
LIP = DISP_FRONT                          # lip underside = nominal touch-film surface
SKIN = 1.02                               # front skin / screen lip thickness
Z_FRONT = LIP + SKIN                      # 6.0
SEAM = -3.75                              # tub / lid parting plane: just under the USB shell (-3.535)
LID_FLOOR_IN = -5.5                       # 0.34 behind the deepest part (J6 header, -5.165)
LID_T = 1.2
Z_BACK = LID_FLOOR_IN - LID_T             # -6.7

# ---- outline (plan) ---------------------------------------------------------------------
POCKET_CLR = 0.15                         # per side, at the drawing's maximum panel size
POCKET_X0 = hw.PANEL_X0 - hw.PANEL_W_TOL / 2 - POCKET_CLR      # -1.41
POCKET_X1 = hw.PANEL_X1 + hw.PANEL_W_TOL / 2 + POCKET_CLR      # 61.41
POCKET_Y0 = hw.PANEL_Y0 - hw.PANEL_H_TOL / 2 - POCKET_CLR      # 5.035
POCKET_Y1 = hw.PANEL_Y1 + hw.PANEL_H_TOL / 2 + POCKET_CLR      # 110.865
# Rev F: the panel goes in from the back, so everything between the parting plane and the pocket
# must be at least as wide as the pocket (Rev E's walls below the screen reached 1.2 mm further
# in, and the real panel sat on them). The case is 1 mm wider each side (Ian's call), which keeps
# the walls below the pocket 2.0 mm thick around the button tabs, the joint and the latches.
# Rev G: the wall is three layers where a button tab cuts it - an outer flexure tab, the void it
# swings into, and a continuous INNER SLIVER that never breaks. The sliver is the tab's hard stop,
# it closes the inside of the case, and it is the root of the tongue that registers the lid. Rev F
# had no room for it: the whole inner 0.92 mm was cut away behind each tab, so over 79 mm of the
# right wall and 46 mm of the left there was nothing at the parting line but a 1.08 mm cantilever.
# Rev I: the tab is a separate printed part (sidekeys.py) sliding into a slot in the wall, so the wall
# at a button is the sliver, the void the key swings into, and the key itself where the outer layer
# was. The sliver is 0.13 thicker and the void 0.13 thinner because the nub now starts 0.25 from its
# plunger (Rev H 0.39); the total is unchanged, so the case is the same size.
SLIVER = 0.93                                                  # Rev G/H 0.80
TAB_T = 1.05                                                   # the side key's bar; its outer face is the case face
TAB_VOID = 0.70                                                # travel before the key bottoms on the sliver:
                                                               # the -X keys' TAB_GAP_SIDE plus the switch's own
                                                               # maximum travel, so the case takes an over-press,
                                                               # not the switch (the +X keys' 0.15 leaves 0.10 more;
                                                               # their board backs off that much, side_key_reach)
SIDE_WALL = SLIVER + TAB_VOID + TAB_T                          # 2.68 (Rev F: 2.0)
X0 = POCKET_X0 - SIDE_WALL                                     # -4.09
X1 = POCKET_X1 + SIDE_WALL                                     # 64.09
# Clear width the panel and the midplate need on their way in from the back: the drawing's
# largest panel (+-0.075 on 62.37) or the midplate (62.42), whichever is wider, plus a margin.
# Nothing in the tub may reach inside this below the pocket (build.insertion_check proves it).
INSERT_CLR = 0.05
INSERT_X0 = min(hw.PANEL_X0 - hw.PANEL_W_TOL / 2, POCKET_X0 + 0.2) - INSERT_CLR   # -1.31
INSERT_X1 = max(hw.PANEL_X1 + hw.PANEL_W_TOL / 2, POCKET_X1 - 0.2) + INSERT_CLR   # 61.31
TOP_IN = 113.4                            # J6 header face at 113.15, battery top at ~113.1
TOP_WALL = 2.2                            # thick enough to seat the top screw's boss and counterbore
Y1 = TOP_IN + TOP_WALL                    # 115.6
# chin, Rev L +1.0 (Ian): room for the crank's input arm. chinless: nothing is below the board but its own bottom
# edge (y 0, the bottom switches not fitted), so the chin wall's inner face goes to 0.6 off it: 0.6 / 0.4 / 0.2 with
# the board 0 / 0.2 / 0.4 toward it (the tub-board offset +-0.2, then the routed outline's +-0.2), 0.15 more than the
# keyed tub's rail face (0.45 off the edge, printed and assembled) everywhere in that stack. -0.4 would leave 0.0.
BOT_IN = -8.2 if BOTTOM_KEYS else -0.6
BOT_WALL = 1.2
Y0 = BOT_IN - BOT_WALL                    # -9.4
CORNER_R = 5.0                            # plan-view corner radius
FRONT_EDGE_R = 1.8                        # front face to side: 9 layers at 0.2, keeps >=0.8 wall at the pocket step
BACK_EDGE_R = 2.0                         # back face to side
SEAM_CHAMFER = 0.0                        # no V at the parting line (2026-10-23, Ian, after Emily B (mixmastermouse)'s edit: both
                                          # halves square; it was 0.4 x 45 degrees on each half)
POCKET_STEP_Z = 4.05                      # above the EPD glass the pocket steps in over the inset LGP/touch layers
POCKET_STEP_CLR = 0.45                    # to the touch film edge (its own position is +-0.15 on the drawing)

# ---- screen window ----------------------------------------------------------------------
WINDOW_MARGIN = 0.6                       # beyond the active area at the lip underside
# The bevel round the screen (Ian, 2026-10-10: "go for 35 on the 4.26"; he had asked for a "longer and more
# exaggerated chamfer, rounded at the corners too"). Rev K had 0.6 at 45 degrees down to a 0.42 straight land with
# sharp corners (WINDOW_CHAMFER): as printed, its last two skin layers stood straight at the window's edge.
# Now one slope runs from the face down to WINDOW_BEVEL_DEPTH under it, the last skin layer's mid-plane (5.10), so
# that layer prints on the lip line and the screen seen is Rev K's (the active area + 0.6, the panel's driven border
# ring); below it the window goes straight down to the lip.
# The tub prints face down, so the slope is an overhang: each 0.2 layer's edge steps in 0.2 / tan(angle) over air.
# 35 degrees: 0.286, 68 % of the 0.42 outer wall, which Orca lays as an outer wall slowed to 36 mm/s (30: 0.346,
# 18 mm/s, finely terraced; 25: the whole wall over air, an overhang wall: too far). The skin is only 1.02 (5
# layers), so the angle alone sets the width on the face, WINDOW_BEVEL_W (1.285; 1.24 as printed). The last 0.29 of
# the edge at the screen is one 0.2 layer (Rev K's was two); it rests on the touch film.
# Corners: WINDOW_CORNER_R at the lip and R + W on the face (1.785; a cone, tangent to the sides, so it prints like
# them). R0.5 is the X4 retro case's own (its bevel: 1.4 at 45, R0.5 at the screen, R1.9 on the face); with the
# smallest FT01C on its drawing pushed into a corner, the active area's corner comes 0.30 / 0.25 from the window's,
# and R0.5 keeps that corner pixel 0.18 in view (R0.9: 0.015; R1.0 would clip it).
# The light-strip builds keep Rev K's window for now (Ian, 2026-10-10: "leave all light strip builds alone"):
# WINDOW_BEVEL below, from WINDOW_CHAMFER; their tubs are byte for byte as before.
WINDOW_CHAMFER = 0.6                      # Rev K's bevel (45 degrees), the light-strip builds' window
WINDOW_BEVEL_DEPTH = 0.9                  # face to the last skin layer's mid-plane (Z_FRONT - 0.9 = 5.10)
WINDOW_BEVEL_ANGLE = 35.0                 # from the face
WINDOW_BEVEL_W = round(WINDOW_BEVEL_DEPTH / math.tan(math.radians(WINDOW_BEVEL_ANGLE)), 3)    # 1.285
WINDOW_CORNER_R = 0.5                     # at the lip; R + WINDOW_BEVEL_W (1.785) on the face
# how far the window reaches out on the face past its edge at the lip (the face below it ends there)
WINDOW_FACE_W = WINDOW_CHAMFER if LIGHT_STRIP else WINDOW_BEVEL_W

# ---- surface details --------------------------------------------------------------------
# Silkscreen wordmark (from the site repo's logo SVG) engraved in the chin between the keys and
# the screen. The icon's line work is 0.25-0.35 mm at this size, below what prints as a gap in
# a face-down first layer, so only the lettering is used. Thinner features are filtered out.
# Rev G: at width 40 the e's crossbar is only 0.273 mm of ink, and min_feature 0.36 deleted it in
# CAD before the STL was written - both counters opened into the aperture and the mark printed
# "silkscrccn". At width 50 with a small bold the crossbars are 0.455 mm, wider than the nozzle,
# and every other cut strip is at least 0.43. The filter drops to 0.24 so it only removes what a
# 0.4 nozzle genuinely cannot make.
# Rev K (Ian): back to the Rev D-F size. Even at 50 wide the first layers show artifacts, so the mark
# may as well be quieter. The bold keeps the e's crossbar (0.273 of ink at this width) at 0.38, above
# the filter, so it still reads "silkscreen".
# chinless: the face below the window runs from the front round's tangent (Y0 + FRONT_EDGE_R, 0.0) to the window's
# bevel on the face (WIN_Y0 - WINDOW_FACE_W: 13.215 at 35 degrees); y centres the ink (7.11 tall) on it (the ink's
# centre is y + 0.003): 6.605. The light-strip chinless builds keep Rev K's window, face to 13.9, and y 6.95. Keyed:
# y stays 6.29 (set by the keys below it, not centred).
_CHIN_FACE = (Y0 + FRONT_EDGE_R, hw.ACTIVE_CY - hw.ACTIVE_H / 2 - WINDOW_MARGIN - WINDOW_FACE_W)
LOGO_CHIN = dict(svg='hardware/logo/silkscreen-logo.svg', part='wordmark', width=40.0, depth=0.4, x=30.0,
            y=6.29 if BOTTOM_KEYS else 6.95 if LIGHT_STRIP else round(sum(_CHIN_FACE) / 2 - 0.003, 3),
            min_feature=0.24, bold=0.055)
# The site's book icon engraved in the centre of the back (the lid prints on it, like the chin
# wordmark on the tub). Mirrored so it reads right from behind. Its line work is thickened by
# `bold` so the screen outline (about 0.24 mm at this size) prints; the page lines (0.1 mm) still
# drop out with the thin-feature filter, as Ian expected.
LOGO_BACK = dict(svg='hardware/logo/silkscreen-icon.svg', painter=True, mirror=True, width=30.0, depth=0.4,
                 x=(X0 + X1) / 2, y=(Y0 + Y1) / 2, min_feature=0.36, bold=0.10)
# shallow grooves across the back's lower edge; chinless: the same distances from the bottom edge (Y0 + 3.8 / 5.8 /
# 7.8), between the H3 / H4 counterbores (x 8-52 stays 2.15 clear of them). Literals, not Y0 + ...: -9.4 + 3.8 is
# -5.599999999999999 in floats
GRIP_GROOVES_Y = (-5.6, -3.6, -1.6) if BOTTOM_KEYS else (2.0, 4.0, 6.0)
GRIP_GROOVE = dict(x=(8.0, 52.0), width=0.8, depth=0.35)
LOGO = None                              # the chin is plain since 2026-10-23 (the wordmark is on the back: LOGO_BACK_WORDMARK;
                                          # LOGO_CHIN keeps the old place for the checks that prove the chin plain)
# The wordmark on the back above the grip grooves (2026-10-23, Ian, after Emily B (mixmastermouse)'s edit), mirrored so it
# reads right from behind. Ink 7.11 tall, 40.0 wide: keyed y 4.95 (ink 1.40..8.51, 2.6 above the top groove's edge),
# chinless y 12.55 (ink 9.00..16.11; the grooves are at 2 / 4 / 6).
LOGO_BACK_WORDMARK = dict(LOGO_CHIN, mirror=True, x=(X0 + X1) / 2, y=max(GRIP_GROOVES_Y) + 6.55)

# ---- display ribbons: see panel.py (drawn 1:1 from the FT01C drawing) ----------------------
FPC_GAP_CLR = 0.5                         # tub clearance around each ribbon where it folds past the glass edge

# ---- keys (bottom row): bell crank + sliding key --------------------------------------------
# Rev L (Ian, 2026-09-26): the rocker keys went, for two reasons: they pressed too hard (2.2-3.1 N at the
# finger for a 1.57 N switch) and their press point was all on the chin side of a pivot that had to sit on
# the board. Now a straight key slides toward -Z in a guide and presses a bell crank, which turns on a
# length of 1.75 mm PLA filament and pushes the plunger +Y with its nose: 0.596 x the switch force at the
# finger before friction (lever 4.95 : 2.95). Spec: BUTTONS.md / the crank SPEC.md (stage 4); every number
# below is from its layout.json. Chin +1.0 (BOT_IN, above): the crank's input arm needs it.
KEY_REFS = hw.BOTTOM_SWITCHES if BOTTOM_KEYS else []    # SW9, SW8, SW3, SW2 left to right (none: chinless)
PLUNGER_Y = -1.92                         # MJTP1117 plunger face (the modelled switch)
PLUNGER_Z = -2.709
# the rod: fed in along X through the -X side wall; a printed gate dropped into a slot in that wall (SPEC2 rev 3,
# the side gate: no screw) closes its end play, the +X wall's inside face stops the other end. Nothing snaps,
# so nothing has to flex to hold it.
ROD_YZ = (-2.50, 0.60)
ROD_D = 1.75                              # filament, 1.72-1.78 real
ROD_CUT = 63.25                           # +-0.2; end play 0.3-0.7 between the stops (0.05-0.95 with the stack)
ROD_TIP = dict(taper=1.25, flat=0.8)      # the end that goes in first: a pencil taper 1.0-1.5 long to a flat
                                          # 0.7-0.9 across (it lands in a crank's 2.5 lead-in mouth up to 0.80
                                          # off; a 0.3 point would indent the +X wall at a drop); the tail is square
# side-wall hole, rail rings and open seats. The spec's 1.95 read back from the G-code at 1.77 free: a
# horizontal hole prints in steps, and the layer 0.9 above the axis leaves a corner 0.883 from it. 2.10
# gives 1.93, over the 1.90 the rod (1.72-1.78) needs to slide through five rings.
ROD_HOLE_D = 2.10
# The side gate (SPEC2 rev 3): a slot in the -X wall, open to the rim, that a printed T (keys.gate) drops into
# from the open back. The mouth in the outside face takes the gate's web; behind the two lips (the wall beside
# the mouth, `lip` thick) the flange cavity takes its flange, with full R `end_r` round ends (the lips' root
# relief: no fillets, so nothing is left in the corners for the flange to hit). The floor is the gate's 45-degree
# bevel plane (`floor_z` at the flat, 1.0 under the rod channel at the face), flat behind the flange; the rod's
# 2.10 teardrop runs through it, its edges chamfered where it breaks the floor, and the sliver left between the
# cavity and the pocket keeps the teardrop with a lead-in on its -X face. Every number is from X0, the rim and
# the rod's axis, so the slot and the gate are the same in both builds (and in the 3.68 project).
GATE_SLOT = dict(lip=1.10, mouth=(-3.85, -1.15), cavity=(-4.35, -0.65), end_r=0.40, floor_z=0.90,
                 channel_chamfer=0.30, sliver_lead=0.50)
# the gate: web in the mouth (0.10 per side in Y: it locates the gate), flange behind the lips (0.15 per side to
# the cavity's straight part and 0.15 behind it); inner face flat at X0 + web + flange (the rod's stop) from the
# top down to floor_z, then the 45-degree bevel to the outer face. Top 0.20 under the rim: off its lips (0.075 up
# when centred in X, 0.15 at the far end) or lifted by the printed floor's stairs it still clears the lid. Chamfers:
# the web's outer top edge (ending level with the tub's seam chamfer), the flange's bed-side vertical edges
# (elephant foot), a 0.05 break on its bearing edges. Pull hole: a straightened paperclip lifts it out.
GATE = dict(web=GATE_SLOT['lip'], flange=0.65, web_y=(-3.75, -1.25), flange_y=(-4.20, -0.80), top_clr=0.20, top_chamfer=0.20,
            bed_chamfer=0.40, bearing_break=0.05, pull_d=1.30, pull_depth=1.0, pull_z=-2.00)
ROD_STOP_X0 = X0 + GATE['web'] + GATE['flange']            # -2.34: the gate's inner face
ROD_STOPS = (ROD_STOP_X0, POCKET_X1)                       # gate's inner face, +X wall inside face (61.41)
# the rail: hangs from the skin between the keys and the board, one piece from the -X wall to X 56.3
# (the rest, to the +X wall, stays open so the rod can be pushed back out from there)
RAIL_Y = (-4.225, -0.45)                  # -Y face: the keys' +Y guide; +Y face 0.25 off the board edge
RAIL_END_X = 56.3
RAIL_RING_BOTTOM = -1.20                  # ring segments: closed round the rod
RAIL_SEAT_MOUTH = (262, 370)              # open seats (under each switch): the TS365 housing comes within
                                          # 0.065 of the bore, so the seat opens toward it; the pin load
                                          # (211 degrees) goes into the solid side
SLOT = (3.60, 5.40)                       # cheek slots, |dx| from the key centre, roof at SLOT_ROOF
SLOT_ROOF = 3.60                          # 2026-10-12 (was 3.15; Ian: a friction point turning a crank by hand in the
                                          # open tub). Each cheek's top corner (its z 2.5 flat on the second trim,
                                          # r 2.42 from the rod, 2.48 as sliced) passes under this roof at +40 in the
                                          # free swing; 3.15 printed at 3.20 and, face down with the play and growth,
                                          # the corner scraped it. 3.60 is a layer boundary of the face-down tub
                                          # (6.00 - 12 x 0.2), so it prints at 3.60: build.crank_free_swing

WEB_Z0 = 1.0                              # webs tie the rail to the chin wall (y BOT_IN..RAIL_Y[0])
WEB_OUTER = (4.8, 55.2)                   # the end webs' outer faces; the others fill between the slots
CHIN_LEAD_IN = 0.5                        # 45 degrees on the chin wall's inner lower edge (the old drag bump's
                                          # lead-in; kept: the key's chin side meets it first on its way in)
# the crank (crank-M for the MJTP1117, crank-T for the TS365ZJ: only the nose differs)
CRANK_CHEEK = (3.75, 5.25)                # |dx|: two cheeks round the rod, 1.5 thick, 0.15 in their slots
CRANK_LEG = 1.30                          # |dx| of the centre leg and its nose
CRANK_BORE = dict(d=2.0, ream=1.9, lead=0.3, flat=1.15)     # lip: teardrop pointing +Y (the crank prints pad end
                                                            # down); ring: the d circle alone (2026-09-30)
CRANK_BORE_D = CRANK_BORE['d']            # as modelled (the lip's teardrop, the ring's circle); reamed to 1.9
CRANK_REAM = CRANK_BORE['ream']
CRANK_NOSE = {'M': (-2.92, -2.35), 'T': (-3.20, -2.35)}   # crown centres: nose fronts at -1.92 / -2.20
CRANK_NOSE_R = 1.0
CRANK_PAD = dict(c=(-7.45, -0.80), r=0.6, end=-7.70)     # crowned pad the key presses; the crank is
                                                         # clipped at `end` (its face on the bed)
# The crank is the same solid in both case projects (the 3.68's case-368 has the same numbers).
# The crossbar and belly (2026-09-27, torsion fix): solved as Prandtl's stress function (mechanics.torsion), the
# stage-4 section (underside -1.8, sharp re-entrant corners) did not converge and sat at 10.6-12 MPa of torsion +
# shear at a 20 N press, against 8. Now the crossbar's underside runs 45 degrees from the bed face's lower corner
# down to CRANK_UNDERSIDE, flat, then 45 degrees up the belly's underside from its lower corner; every re-entrant
# corner is rounded (CRANK_FILLET: top = the crossbar's +Y face on the belly's top at (-4.65, -1.3); under = the
# flat on the belly's and the leg's 45-degree undersides; crown = the crown on the crossbar's top).
CRANK_UNDERSIDE = -2.20
CRANK_BELLY_FOOT = ((-2.92, -3.05), (-3.22, -3.35))           # the belly's 0.3 chamfer at its lower +Y corner
CRANK_TOP = -0.60                                              # the crossbar's top, and its +Y face at -4.65 down to
CRANK_BELLY_TOP = (-4.65, -2.92, -1.30)                        # the belly's top (y0, y1, z) under the rail
CRANK_FILLET = dict(top=0.4, under=0.4, crown=0.3)
CRANK_CHEEK_TRIM_Y = -0.70                # cheeks clear a board edge at -0.4 by 0.07. On the 0.2 layer grid from
                                          # the pad end (-7.70): -0.75 printed here anyway (the model is what prints)
# and a second trim across the cheek's +Y top corner: n . ((y, z) - ROD_YZ) <= d, so a crank hanging free in the
# face-down tub (about -17.5 degrees, pad toward the face) keeps its cheeks at y <= -0.45, off a board edge at -0.4
# (the bore's wall is untouched)
CRANK_CHEEK_TRIM2 = ((0.954, 0.301), 2.0)
# crank cheek, test 1 (2026-09-29): closed ring outboard of x0; today's open C only inboard, beside the TS365
# housing (its corner is 1.04 from the rod axis, inside any wall round the bore). x0 = housing 3.65 + float 0.15 + 0.25.
# 2026-09-30 (Ian: thicker where it holds the rod): the ring's bore is round (its top at y -1.50, a layer boundary:
# 0.80 of wall, 4 layers, up to the -0.70 face) and its fill runs forward under the rod to the MJTP housing's frontier
# (the 4.26 envelope's 16-degree front face, 0.03 clear over the swing); least wall 0.57 -> 0.75 (the R1.75 disc
# beside the axis and the 45-degree roof).
CRANK_CHEEK_RING = dict(x0=4.05, top_r=2.20, roof_c=5.575,
                        fill=((-3.40, 0.0), (-1.50, 0.0), (-1.30, -0.70), (-1.70, -2.20), (-3.40, -2.20)))
# the key: slides in Z between the rail face and the chin wall, rests on the crank's pad
# Rev L key fit (2026-09-29, Ian's first print: the keys jammed): the key's +Y face rides the rail with no play, so all
# FDM error in Y lands on the chin side. As printed, holes come out 0.10-0.20 small and parts 0.05-0.15 large (best /
# typical / worst below; flare: the key's first layer at elephant-foot compensation 0, per side).
KEY_FDM = dict(hole=(0.10, 0.15, 0.20), part=(0.05, 0.10, 0.15), flare=(0.10, 0.15, 0.30))
# chin side: skin = the cap's chin face to the opening's chin edge, pocket = the pusher's chin end to the chin wall.
# The skin gets 0.02 more: Orca simplifies the opening's R0.2 corners and slants its chin edge, so at the cap's -X end
# it reads 0.012 short (0.388 from 0.40, 0.038 as printed at worst); 0.42 reads >= 0.40 everywhere.
KEY_CHIN_GAP = dict(skin=0.42, pocket=0.40)
KEY_SIDE_GAP = 0.30      # cap to the opening's sides, per side (0.40 to the webs). 0.30 (2026-10-03, Ian, from the
                         # key-fit audit; 0.35 before): the key prints on its -X end, so its X is a stack of 0.20
                         # layers. At 0.35 (cap 9.90) Orca dropped the 50th and printed 9.80, 0.40 a side; at 0.30
                         # the cap is 10.00, exactly 50 layers: 0.30 a side as sliced, 0.20 as printed at worst
KEY_BED_END = (0.30, 0.10)     # the key prints on its -X end (test 1, 2026-09-29): its outline there comes in 0.30 in
                               # the first layer (x -half..-half+0.2) and 0.10 in the second, a 0.4 x 45 chamfer all
                               # round at the layers' mid-planes, so its elephant foot stays inside the cap's outline
# the chin edge stands 0.25 over the chin wall: the ledge. Its corners are R0.2 (the spec's 0.5 left the cap's
# chin corners 0.04 inside it; at the refit's gaps R0.5 would clear them too) and the +Y corners are square (the +Y
# edge is flush with the rail face). The key is drawn from it (KEY_CHIN_GAP, KEY_SIDE_GAP).
KEY_OPENING = dict(y=(-7.95, RAIL_Y[0]), half=5.30, r=0.2)
KEY_EDGE_CHAMFER = 0.3                    # key openings' front edge
# proud 1.35 (2026-10-03, Ian: the caps were "a small fraction of a mm too high"; 1.50 before, set it back to undo).
# 1.35 is the floor, never lower: the spec keeps the key 1.0-2.0 proud at board +-0.2 with the matching crank, and the
# board 0.2 away takes 0.33 off (1.02 here; mechanics.key_proud). The hooks hang from the slot's roof, so KEY_W_OUT and
# the stop do not move: face down the cap stands 2.37 proud (2.52 before).
KEY_CAP = dict(y=(round(KEY_OPENING['y'][0] + KEY_CHIN_GAP['skin'], 3), RAIL_Y[0]), half=round(KEY_OPENING['half'] - KEY_SIDE_GAP, 3),
               proud=1.35, chamfer=0.4)                  # y (-7.53, -4.225), half 5.00; chamfer: all four top edges
                                                         # (test 1: the chin edge too, now the cap is closed there)
# flat on the pad crown at rest. Its chin end below stop_z1 is the chin-side stop, 0.40 off the chin wall (the foot's
# job before 2026-09-29); above stop_z1 the key's chin side is the cap's chin face (KEY_CAP y0), all the way up.
KEY_PUSHER = dict(y=(round(BOT_IN + KEY_CHIN_GAP['pocket'], 3), -6.55), z=(-0.20, 1.60), stop_z1=0.55)   # y -7.80..-6.55
# the body: between the cheeks, 0.45 off their inner faces (CRANK_CHEEK 3.75). That is more than the key's X play in
# its opening (KEY_SIDE_GAP 0.30), so a key pushed sideways stops on the opening, never on its crank's cheek (at 3.45
# it met the cheek at 0.30, before the opening; mechanics.key_fit pair E). On the 50-layer key the body's +-3.30 faces
# fall on layer mid-planes, so Orca may print either one out to +-3.40 (it does, as sliced): key_fit takes 3.40.
KEY_BODY = dict(half=3.30, z0=0.40)                      # between the cheeks; outside it the cap stops at
KEY_CHEEK_ZONE = dict(y=-6.25, z0=2.70)                  # 2.70 over the cheeks for y > -6.25
# Hook keys (test 2, 2026-09-30, Ian: "build the hook keys"; keystab RECOMMENDATION, concept C4-A). The drag leaf, its
# slit and its bump are gone: nothing on the key rubs. Each key has two rigid hooks on its chin side, one at each X
# end, and the tub two slots per key in the chin wall's inner face, open to the rim, that the hooks run in. The key
# still rests on its crank and the crank on the switch (its rest height is the switch's, with no free travel face-up);
# the hooks only bound it: face down it drops KEY_W_OUT outward onto them, both hooks flat under the slot's roof, level
# and 2.37 proud (2.52 before 2026-10-03). They cannot come out through the face: the key's +Y face rides the rail,
# so a hook can only move toward the chin, deeper under the roof. The key still prints on its -X end: the -X hook starts on the bed, the +X
# hook's -X face is a 45-degree lead (KEY_HOOK_LEAD in plan) so it builds up with no overhang.
KEY_W_OUT = 1.00          # hook top to the roof at rest: the face-down drop. It must clear the switch's rest scatter at
                          # the key (1.678 x (board +-0.2 + TS365 tip +-0.2) + the chain's print 0.14, plus the stop's
                          # own print 0.10 and 0.05: 0.986; mechanics.key_hooks), or the stop would press a plunger
KEY_CHAIN_PRINT = 0.14    # the key-crank chain's own print scatter at the key, for that budget (C1's number)
# the slots, |dx| from the key centre: the inner side 0.5 past the +X hook's lead where it crosses the chin wall's face,
# the outer side flush with the web's face (SLOT[1], the X guide plane: 5.40 as built; the spec's 5.30, the opening's
# side, would leave a 0.10 fin of chin wall between the slot and the web). back: the slot's depth, wall: the least chin
# wall left behind it (in every layer, the rim's included), above: the least material over the roof at the back.
# relief: the tub has no seam chamfer on the chin over the key row, from `relief` before the first slot to `relief` past
# the last (tub.rim_chamfer; hverify2, 2026-09-30, as the 3.68's): with it the rim layer printed nothing behind the
# slots, a one-layer slit into each key's slots showing in the seam's V over every key (at HEAD too, over each opening)
KEY_SLOT = dict(dx=(3.20, SLOT[1]), back=-8.80, wall=0.45, relief=0.50, above=0.50)
# hooks: |dx| 3.95-5.00 (8.95 apart, to the cap's ends), h tall, from the cap's chin face to `tip`. The tip is
# KEY_CHIN_GAP['pocket'] (0.40) off the slot's back, as the pusher is off the chin wall: all FDM error in Y lands on the
# chin side (the key rides the rail), and 0.40 is what keeps a rigid pair >= +0.05 at KEY_FDM's worst (the spec's 0.35,
# tip -8.45, would print 0.00). Bearing under the roof: the tip to the opening's chin edge, 0.45. h 0.80 is two outer
# wall lines as the key prints (0.85-1.7 would leave a void between them).
KEY_HOOK = dict(dx=(3.95, KEY_CAP['half']), h=0.80, tip=round(KEY_SLOT['back'] + KEY_CHIN_GAP['pocket'], 3))   # tip -8.40
KEY_HOOK_LEAD = round(KEY_CAP['y'][0] - KEY_HOOK['tip'], 3)    # 0.87: the +X hook's -X face, 45 degrees in plan
# The key's root: over its first KEY_ROOT from the -X end (the bed) its chin side is solid out to the hooks' tip, from
# the pusher's underside up to the hooks' top, so the bed end's chamfer (KEY_BED_END: 0.30 in on layer 1) leaves no thin
# stub there. Without it, layer 1 had a 0.20 stub of the -X hook and a 0.15 shelf of the pusher's chin end, which Orca
# drops, and layer 2 hung 1.07 / 0.52 off nothing (slice_check.no_support). It lies in the -X slot, 0.40 off its back.
KEY_ROOT = 0.60


def chin_outer_y(z):
    """The chin's outer face (y) at height z, as outer_body draws it: Y0, the FRONT_EDGE_R round up to the face, the
    SEAM_CHAMFER at the rim."""
    import math
    zc = Z_FRONT - FRONT_EDGE_R
    if z > zc:
        return Y0 + FRONT_EDGE_R - math.sqrt(max(0.0, FRONT_EDGE_R ** 2 - (z - zc) ** 2))
    return Y0 + max(0.0, SEAM + SEAM_CHAMFER - z)


def slot_roof():
    """The slot's roof (RECOMMENDATION 6: the highest z where the wall behind it stays >= KEY_SLOT['wall']), on the
    layers the face-down tub prints: a roof at zr opens every layer whose mid-plane (Z_FRONT - LAYER (k - 1/2)) is below
    it, so the wall is held at those planes. The skin's underside (LIP) unless the top open layer would leave less wall;
    then down a layer at a time."""
    import math
    zr = LIP
    while True:
        k = math.floor((Z_FRONT - zr) / LAYER + 0.5 + 1e-9) + 1          # the first layer whose mid-plane is below zr
        zm = Z_FRONT - LAYER * (k - 0.5)
        if KEY_SLOT['back'] - chin_outer_y(zm) >= KEY_SLOT['wall'] - 1e-9:
            return round(zr, 4)
        zr = round(Z_FRONT - LAYER * k, 4)


# only with the bottom keys: with no key slots in a short chin, slot_roof() would walk down forever
KEY_SLOT_ROOF = slot_roof() if BOTTOM_KEYS else None                   # 4.98: the skin's underside
KEY_HOOK_Z = ((round(KEY_SLOT_ROOF - KEY_W_OUT - KEY_HOOK['h'], 3), round(KEY_SLOT_ROOF - KEY_W_OUT, 3))   # 3.18-3.98 at rest
              if BOTTOM_KEYS else None)

# ---- side buttons (side keys that grow out of the lid: sidekeys.py) -------------------------
# Rev J. Ian's fifth print: the Rev I keys were separate parts, and a clip that small could not hold
# them. Rev G/H cut the key out of the tub's wall instead, and its top edge - the first layer the
# face-down tub lays of it - was drawn over an air gap; that strung on every print. A key cut out of
# the tub has to be free along that edge, so it cannot avoid it.
# The lid prints back face down, and a key standing on that face is free along its top edge (the
# last layer printed) and sits on the bed along its bottom one. So each key is now part of the lid:
#   bar    the lid's own side wall below the parting line, cut free on three sides - it is the flexure,
#          rooted over its whole section in the wall
#   block  from the pad to the free end the key rises on past the parting line into a slot in the tub
#          (Rev I's slot, shortened to the block), carrying the pad and the nub
# Every surface grows straight up from the bed. The tub's wall is whole again over the flexure. The
# lid's back edge is square where a key stands on it, and behind the bar a slot runs through the back
# face: that is the key's travel.
TAB_GAP_SIDE = {+1: 0.15, -1: 0.25}       # nub to plunger at rest. The board's only X datums on the lid (the H5 pin
                                          # and J1's lid block) are on its +X half, so a press on a +X key lets it back
                                          # off 0.10 further than a -X key (test 1, 2026-09-29: +X keys did not click;
                                          # mechanics.side_key_reach). Rev H's 0.39 was set by SW1, whose nub had to
                                          # stop at the panel's insertion corridor; the keys go in after the panel
                                          # and the midplate, so nothing holds it back
TAB_Z = (Z_BACK, 0.6)                     # key's bottom (on the lid's bed) and the block's flat top
TAB_BAR_TOP = SEAM - 0.15                 # the bar's top: 0.15 under the tub's rim, so the rim clamped on the
                                          # lid cannot pinch it; its outer edge carried the seam's V until 2026-10-23 (TAB_BAR_V)
TAB_BAR_V = round(max(0.0, SEAM_CHAMFER - (SEAM - TAB_BAR_TOP)), 3)   # the key bar's share of the seam's V: 0.25 with the 0.4 V, 0 without
TAB_BLOCK_MARGIN = 0.3                    # the block starts this far before the pad
TAB_SLOT_CLR = 0.2                        # tub slot above the key's top: all there is to see over the pad
TAB_END_CLR = 0.3                         # free-end gap to the wall beyond, in the tub and in the lid
TAB_END_FOOT = 0.4                        # the lid wall's edge at that gap is chamfered this much at the bed,
                                          # so the first layer's squash cannot close it
TAB_ROOT_CLR = 0.2                        # the tub slot's end before the block
# Rev K (Ian: can the key's bottom be rounded like the rest of the lid?). The bar follows the lid's
# BACK_EDGE_R round, and to keep its first layer on the bed a FOOT runs along its inside at the bed: a
# 45-degree fillet TAB_FOOT deep, so the key's first layer is the strip from the round's tangent line
# out (0.6 wide) and every layer above it steps out along the round or in along the 45. Behind the foot
# the lid is cut back TAB_FOOT_GAP at the bed - its travel there, 0.75 up to the nub and opening to 1.2
# at the free end, which swings about 1.5 times as far - also along a 45, so the lid prints too.
# The round and the foot put material 2 mm inboard of the key's face along its whole length, which
# doubles its stiffness (press 2.8-3.0 N, 2 % strain at the stop). So for TAB_HINGE from the root the
# bottom is notched out up to the foot's height: there the key is the plain wall section again and
# bends; the notch's roof is a TAB_HINGE bridge between the lid's wall and the rest of the foot.
TAB_FOOT = 1.05
TAB_FOOT_GAP = (0.75, 1.20)
TAB_HINGE = 3.0
# 2026-10-19 (Ian's photos: the keys are scraggly in their free half, both sizes). As sliced with the CC2 presets each
# key stood, from its hinge's end to its free end, on one 0.52 bead (the BACK_EDGE_R round's tangent line meets the
# foot's 45 degrees 2.0 in from the case face), its second layer only 43 % on it; Ian's G-code shows the same on every
# key of both sizes. TAB_BASE fills the round's corner under the key, from the hinge's end to the free end
# (sidekeys.bar), so the key stands on the bed from the case face to the foot's edge. Sliced on mock-ups: 'square'
# (the corner filled to a right angle) 1.70 of bed, the second layer 94 % on it; 'chamfer' (TAB_BASE_C x 45) 1.00,
# 80 %; 'teardrop' (the round down to its 45-degree point, then a 45 to the bed) 0.83, 76 %. Ian chose 'square'
# (2026-10-19), then 'teardrop' (2026-10-20: the square edge looked sharp beside the bevels everywhere else, and the
# round had printed fine most of the time, so a small change was enough). Sliced
# (CC2 and generic presets, both sizes): 0.83 of bed (two beads), the second layer 76 % on it; the round 0.52 / 43 %.
# The hinge keeps its section, so the press moves little (mechanics.side_keys). None = the Rev K round to the bed (the
# 0.52 bead). TAB_BASE_C stays defined for every value (sidekeys evaluates its chamfer profile).
TAB_BASE = 'teardrop'
TAB_BASE_C = 1.0
TAB_PAD_PROUD = 1.2                       # 1.5 until 2026-10-23 (Emily B (mixmastermouse)'s edit: 1.2; our 45-degree faces kept). At the click
                                          # 0.80 (+X) / 0.70 (-X) proud (Rev E's 0.5 needed the thumb to sink in to reach the click)
TAB_PAD_FACE = (-3.4, -1.0)               # the pad's flat face, as Rev I's; below it a 45-degree face runs
                                          # back to the key (it is an overhang now, in the lid's print), above
                                          # it the Rev G-I upper face
TAB_PAD_LEN = 10.0                        # pad base along Y, centred on the plunger. Do NOT grow this:
                                          # the key's free end is derived from it, and at 12 the free ends
                                          # of neighbouring keys meet
TAB_PAD_LENS = {'SW10': 7.0}              # power: a smaller pad is harder to hit by accident
TAB_FREE_BEYOND = 0.2                     # bar runs this far past the pad's end (Rev H 0.5: on the separate
                                          # key that tail sliced as a single thin line)
# Root per switch (Y): where the flexure starts, in the lid's wall. SW1's keeps a wall post between it
# and the USB-C divot's lead-in, and SW4's stays put: SW10's free end is right behind it.
TAB_ROOTS_ALL = {'SW1': 49.5, 'SW4': 87.3, 'SW10': 106.0, 'SW5': 46.0, 'SW7': 91.0}
# the keys this layout has (SIDES), in TAB_ROOTS_ALL's order, so the all-keys builds iterate exactly as before.
# Every side-key feature follows TAB_ROOTS through body.side_tabs(): the key and its lid cut (sidekeys), the
# tub's slot and nub window (tub.key_cuts), the tongue and groove breaks (joint.runs), build.SIDE_KEYS,
# mechanics' side-key rows and make_plates' enforcers. Only joint.switch_spans walks every side SWITCH (hw).
TAB_ROOTS = {r: y for r, y in TAB_ROOTS_ALL.items() if r in SIDE_REFS}
# A key the layout leaves out is the plain wall, and its switch may stay fitted (it stays in the hardware model), so
# the closed wall must stay off the plunger and the lid off the switch (build.sides_check). Measured 2026-10-07:
# plunger to the tub 0.4375 (SW5, SW7), 0.4425 (SW4), 0.4875 (SW1); the switch to the lid 0.91-0.96 (its body; 0.29,
# under the plunger, if the lid's lip did not duck under a left-out key's switch: joint.switch_spans). The plunger
# clicks about 0.25 past contact, so a false press would need about 0.5 of error.
SIDE_SHUT_GAP_MIN = 0.40                  # plunger to the closed wall, nominal
SIDE_SHUT_WORST_MIN = 0.20                # the same with the board SIDE_SHUT_SHIFT toward that wall and the wall's face
                                          # SIDE_SHUT_GROWTH proud
SIDE_SHUT_SHIFT = 0.10                    # the board on its screws in their 2.2 holes (toward +X, J1 on the port floor
                                          # stops it at 0.115)
SIDE_SHUT_GROWTH = 0.075                  # a printed face standing proud of the CAD
SIDE_SHUT_LID_MIN = 0.5                   # the switch (body and plunger) to the lid
# Rev J: the flexure is the bar, 2.8 tall (the lid's wall, to 0.15 under the rim) where Rev I's bar was 4.2, so it
# can be 0.95 thick - a robust wall, not a thin one - and still press a little lighter than Rev I's.
# It flexes from the root to the block; the block is 7.3 tall and barely bends. The stretch at the nub
# keeps 1.05, and that is the stop.
TAB_FLEX_T = 0.95
TAB_ROOT_FULL, TAB_ROOT_TAPER = 0.2, 0.5  # full thickness at the root, then a taper down to TAB_FLEX_T
# The nub is the contact: 6.0 x 2.3 against a 2.88 x 1.50 plunger (z -3.46 .. -1.96). Its flat tip spans
# z[0] .. z[1] - lead. In the lid's print its underside is an overhang, so below the tip a 45-degree
# gusset runs down and out to the key's inner face (it passes over the lid's lip and floor, which the
# sweep checks); its top is the last layer and flat, with a lead.
NUB = dict(w=6.0, z=(-3.5, -1.20), lead=0.3)
NUB_W = {'SW10': 5.0}                     # power's pad is 7.0 long, so its window has to be narrower
# The nub has to cross the sliver, so the sliver has a window at each one, open to the parting line.
NUB_WINDOW = dict(clr=0.5, top_clr=0.25)
# The bar deflects more at its free end than at the nub, so its inner face is relieved from the nub
# outward. Rev I: 0.40 (Rev G/H 0.60), which keeps the free end 0.65 thick - at 0.45 it sliced as one
# line that stopped short of the end. The free end now meets the sliver at about 0.66 mm of nub travel,
# after the click at 0.50, and the nub's own stop is 0.70.
TAB_RELIEF_MAX = 0.40

# ---- USB-C ------------------------------------------------------------------------------
# A mated plug's overmold sits USB_PLUG_SPARE in front of J1's mouth, so whatever surrounds the
# port may stand at most 0.35-0.4 mm in front of it (Ian: "the official clearance"). The port is a
# recess - the divot - for the plug's overmold, sized for typical cables, and its floor closes round
# the port itself so no board shows.
# Rev I: the floor is the tub itself (Ian could not keep the Rev F-H printed bezel on the dummy's J1).
# J1's mouth sits at the panel's edge, and the panel passes there on its way in, so the floor's inside
# can come no closer than the insertion corridor, 0.115 in front of the mouth. At USB_FLOOR['t'] - about
# the thinnest wall a 0.4 nozzle lays as a single line - its face is 0.615 in front of the mouth, so a
# typical plug seats to within about 0.17 mm of full depth rather than all the way.
USB_PLUG_SPARE = 0.45
OVERMOLD = (12.35, 6.5)                   # USB-C plug overmold maximum (the recess is smaller; see below)
OVERMOLD_CLR = 0.25
USB_RECESS = (11.5, 6.0)                  # sized for typical cables (Ian's call); larger overmolds stop
USB_RECESS_R = 1.5                        # at the case face
USB_RECESS_LEAD = 0.8                     # 45-degree lead-in at the case face
# t          floor thickness; its inside is at INSERT_X1
# hole       clearance per side round J1's inner opening (8.34 x 2.56): the plug passes, the floor
#            hides the rest
# notch_clr  below the hole the tub's floor is open to the parting line, so the hole prints with no
#            bridge; a block on the lid rises into that notch, notch_clr narrower each side, and
#            closes the hole's lower edge
# lid_gap    that block's inside face in front of J1's mouth
USB_FLOOR = dict(t=0.5, hole=0.10, notch_clr=0.1, lid_gap=0.055)
# 2026-10-22, the port fits board Rev 1.0 and Rev 1.02. Rev 1.02's J1 (the SMD USB4105) sits 0.14 mm nearer the board
# than Rev 1.0's through-hole USB4085 (the opening's centre z -1.815, was -1.955), and KiCad seats both about 0.085
# deeper than a real board rests, so a plug in a Rev 1.02 socket sat 0.015 from the hole's board-side edge as printed
# (line to line at the corners; interference once the seat is counted). The tub prints face down, so a plane
# counts in whole layers from the face (Z_FRONT): the hole's board-side edge and the recess's both move one layer
# (the edge at z -0.575 printed at -0.60; the recess's 1.045 at 1.00) onto layer lines. Both are drawn for the frozen
# Rev 1.0 board copy (assert in tub.usb_features); a regenerated case redoes them. The hole keeps its width (8.54), its
# corner radius (1.1) and its far edge (the lid's block, the 4.26's -3.335, which prints -3.30 and sits -3.40 at home).
# slice_check reads the printed edges back against both sockets (asprinted.usb_fit; FAIL under 0.1 on any side).
USB_HOLE_TOP = -0.40                      # the hole's board-side edge (z), a whole layer line from the face: 6.0 + 0.4
USB_RECESS_TOP = 1.20                     # the recess's board-side edge (z): 6.0 - 1.2 = 4.8
J1_REV10 = dict(yc=41.30, zc=-1.955, mouth_x=61.195)   # the frozen Rev 1.0 board copy's J1 (tub.usb_features asserts it)
J1_REV102_DZ = 0.14                       # Rev 1.02's USB4105 opening sits this much nearer the board (z up): -1.815
J1_SEAT_DZ = 0.085                        # KiCad seats parts this far behind where a real board's rear face rests (both J1s)
USB_PLUG = (8.25, 2.40, 1.0)              # the nominal USB-C plug shell: width, height and its least corner radius
USB_FIT_MIN = 0.10                        # the plug's least clearance to the hole's printed edges, each flat, both boards
USB_BLOCK_DROP = 0.0                      # the lid's port block top, below the hole's far edge (the 3.68 lowers it a layer)

# ---- fasteners ---------------------------------------------------------------------------
M2_PILOT = 1.7                            # thread-forming into the printed PLA
M2_CLEAR = 2.4
M2_HEAD_D, M2_HEAD_H = 4.2, 1.7
BOSS_D = 4.4                              # H3/H4 bosses are flattened on the screen side (POCKET_Y0)
# Rev G: the board used to be clamped only at H3/H4, both at y = 3.0, and merely rested on posts
# at H1/H2/H5 - so its top end could lift, which is what moved the side switches' plungers out of
# their nubs. H1 and H2 now take a snap post hanging off the midplate: the board clips onto the
# midplate before the lid goes on, which is the "slotting in" that was missing. It captures, it
# does not clamp - with the lid on, the lid's posts still set Z and the barbs go slack - so it
# cannot fight the panel's +-0.2 mm thickness take-up.
# Rev H: Ian's new board adds H6 (24.96, 30.75) for another peg, so H6 gets a snap post too. H1, H2
# and H6 make a triangle that spans the board, so the PCBA clicks onto the midplate and is located
# at its lower end as well as its upper one before any screw goes in.
SNAP_POSTS = ('H1', 'H2', 'H6')
# 'pole' (2026-10-23, Ian, after Emily B (mixmastermouse)'s edit): a plain d1.90 pin, its tip edge rounded tip_r, no slot, no barb.
# As printed it locates the board +-0.155 both ways (the slotted post laid two fingers, 1.52 across X and 0.65 across Y each,
# its barb caught 0.09 in Y only). tip -1.00, not -0.95: the midplate prints screen side down from DISP_REAR, so -1.00 is a
# whole number of layers from the bed (a mid-plane at -0.90 / -0.95) and lays the pin's top where the barbs' tip laid, so
# the lid's bore floor and every overlap read stay as they are. The PCBA no longer clicks onto the midplate before the lid goes
# on; with the lid on nothing changes (the barbs were slack at home). 'barb': Rev G-K's two-finger snap (crest, catch, lead_deg,
# face_deg, slot).
BOARD_SNAP = dict(style='pole', d=1.90, tip=-1.00, tip_r=0.30,       # post in the board's 2.2 hole: 0.15 per side
                  crest=2.50, catch=-0.10, lead_deg=30.0, face_deg=45.0, slot=0.60)   # the barb style's numbers (unused by 'pole')
BOARD_SNAP_BORE = (3.0, -1.40)            # clearance bore in the lid's post for the barb, and its floor
# Lid posts. On the board: H1 is 2.68 from D8, H2 2.68 from J7, H5 2.75 from J5, H6 3.14 from R48.
# The dummy PCBA's switch cradles are closer still - SW7's rim is 2.30 from H2 and SW4's 2.26 from
# H5 - and the lid has to fit the dummy too, so H2 and H5 stay under those. H5 moved 0.5 mm clear
# of R56/C34 on the new board, which is what lets its post grow at all (Rev G 4.0).
BOARD_POST_D = {'H1': 4.4, 'H2': 4.4, 'H5': 4.3, 'H6': 5.0}
# Where each post stops (2026-10-24, Ian, after the lid-bulge study of 2026-10-23/24): H1 on the board's rear face as before (a layer
# mid-plane, it lays +0.10 and sits on the board at home), H2, H5 and H6 one layer short of it (-0.1 is 33 whole layers from the bed: it
# lays -0.10 and stands 0.2 off a nominal board at home). The four upper midplate springs push the board onto these posts and through
# them the lid's middle; H1 is the lid's stiffest point (0.03 mm/N, against 0.06 at H2 and H5 and 0.10 at H6), so the board now lands
# there first and the middle bows about 40 % less (model estimate, not measured on a print). Lowering all four also cuts the screen's hold
# at its top end on a thin panel, which is why H1 stays. H5's pin keeps its own absolute top, so it reaches into the board exactly as
# before (full section to +0.90 as laid, 0.80 into the board at home).
BOARD_POST_TOP = {'H1': PCB_REAR, 'H2': PCB_REAR - 0.1, 'H5': PCB_REAR - 0.1, 'H6': PCB_REAR - 0.1}
H5_PIN = dict(d=1.9, top=PCB_REAR + 1.19, cone=0.4, tip_d=1.2)      # the locating pin on H5: d1.9 cylinder, a 0.4 cone to d1.2, its tip at +1.19
TOP_SCREW = (40.2, 112.8)                 # between the battery's corner and J6; boss clears the screen pocket
TOP_SCREW_CLEAR_TO = PCB_FRONT              # 1.6: an M2_CLEAR bore from the rim to here, so the top screw thread-forms only the last 3.8 of its pilot, as H3/H4 do (2026-10-23)
TOP_BOSS_D = 3.4
# The screws: three M2 x 10 (SCREW_L, under the head), socket head caps (ISO 4762 / DIN 912: dk 3.8, k 2.0 max; Ian's,
# 2026-10-13) or pan heads (ISO 7045: dk 4.0, k 1.6 max). The counterbores take either head flush with the back or
# below it: 2.0 deep, 10 layers on the layer grid (until 2026-10-13 1.8, 9 layers, sized for a pan head, so a socket
# head stood 0.2 proud of the back). One layer deeper puts each screw 0.2 further in: H3 / H4 3.6 mm in the pilot (3.3
# with the lid 0.3 open), the tip 0.2 short of the pilot's end and 0.8 from the front face; the top screw 3.6 (3.3)
# since 2026-10-23: it had 9.0 (8.7) of thread-forming, which Emily B (mixmastermouse) reports stripped heads, until TOP_SCREW_CLEAR_TO gave it a clearance
# bore in front of its pilot (slice_check.as_printed reads all three on every build, as sliced).
SCREW_L = 10.0
M2_HEAD_CB = 4.2                          # counterbore for the head (dk 4.0 max)
M2_HEAD_CB_DEPTH = 2.0                    # its depth from the back face: 10 layers, so its ceiling is on the layer grid
# The lid prints back face down, so each counterbore's ceiling is over air with the clearance hole in it, and plain
# bridge lines across it would end in mid-air at the hole. Two-layer stepped bridge instead (lid.counterbore): the
# first layer over the ceiling leaves only a slot M2_CLEAR wide across the counterbore, so its lines bridge wall to
# wall along the slot; the next leaves only an M2_CLEAR square, so its lines bridge across the slot's ends; the
# round hole goes on from there. The head's seat is unchanged; the hole is square for those two layers only.
M2_CB_BRIDGE_LAYERS = 2

# ---- tub / lid joint (joint.py) ----------------------------------------------------------------
# Rev G inverts the joint. The tongue is now on the TUB - it is the inner sliver carried on below
# the parting plane - and it runs into a closed groove in the lid's rim. That one change is what
# makes the joint continuous: the sliver survives behind every button tab, so the tongue does too,
# where Rev F's lid tongue needed a rebate in a tub wall that simply is not there at a tab.
# One registration scheme only: Rev F's lid-tongue-into-tub-rebate is gone. Two X datums in series
# would either bind or rattle.
JOINT = dict(t=SLIVER, h=1.4, clr=0.15, end_clr=0.3, floor_clr=0.15, lead=0.2, mouth=0.3,
             lip=0.85, min_run=4.0)
# Where the tub carries a tongue (along Y for the sides, along X for the top). The side walls are
# free end to end except for the USB port; runs stop short of the cavity's R1.5 plan corners, and
# joint.runs() takes out the nub windows and the side keys' clip slots.
#   right  stops either side of the lid's solid USB block (y 34.55 .. 48.05), by 0.3
#   top    left corner .. the top screw's lid boss; J6's opening takes the rest. With J6 not fitted (nodev) the
#          wall is closed and a second run goes on from the top screw's boss to the right corner: the first one
#          mirrored about the top screw (2 x 40.2 - 37.0) and about the case's centre (60.0 - 1.3), so the lid's
#          boss and the right corner see exactly what they see on the left
#   left / right start  BOT_IN + 3.0: the lid's R3.8 tray corner reaches y BOT_IN + 1.832 at the tongue's outer face,
#          so the groove's end (end_clr 0.3) needs BOT_IN + 2.13 at least; + 3.0 keeps the keyed corner's 1.17. A
#          literal per build (-8.2 + 3.0 is -5.199999999999999 in floats)
_A0 = -5.2 if BOTTOM_KEYS else 2.4
TONGUE_RUNS = {'left': [(_A0, 111.9)], 'right': [(_A0, 34.25), (48.35, 111.9)],
               'top': [(1.3, 37.0)] + ([] if DEV_HEADER else [(43.4, 58.7)])}
# Latch arms stand on the lid floor and hook into pockets in the sliver's inner face.
# Rev I (Ian: "the side latches still do not hold"). They could not. Eight of Rev G/H's eleven barbs
# pulled on the sliver where a button tab's void was right behind it - a 0.8 mm skin with nothing
# backing it, which just bowed out of the way - and each caught only 0.2 mm. The pockets now sit above
# the key slots (their catch starts at z 0.95, the slots stop at 0.8), where the wall behind the sliver
# is solid, and they are 0.6 deep, so each barb catches 0.45. The arms reach up there by being 7 mm
# tall; the midplate is notched SNAP['notch'] where their tips pass its edge. Placed clear of the
# switch bodies, the nub windows, the keys' clips, the port and the reset trough.
SNAPS = {'left': [12.0, 26.0, 39.5, 54.0, 68.5, 83.0, 102.0], 'right': [12.0, 24.0, 54.7, 68.5, 82.3, 100.3]}
#   catch     z of the barb's retaining face at its tip (the flat runs from here up `flat`)
#   lead_deg  the barb's lead-in, from vertical: 35 degrees goes on at two-thirds the force it takes
#             to pull off (the retaining face is 45); its tip then stands at z 2.49, under the panel
#   barb      how far the barb stands off the arm; it catches barb - gap
#   pocket    pocket depth into the wall
#   notch     how far the midplate's edge steps back at each latch
SNAP = dict(w=4.5, gap=0.1, barb=0.55, t_root=0.85, t_tip=0.6, catch=1.5, flat=0.2, lead_deg=35.0,
            gap_ends=1.0, pocket=0.6, notch=0.85)
# notch and SNAP_INNER_CHAMFER (2026-10-12; the notch was 0.7 and the arms' tops square): the lid closed only under the
# screws' force. Over the last ~7 mm each barb rides the tub's tongue, which bends its arm 0.45 inward (0.54 at its
# top) until the barb drops into its pocket 0.1 before home. Bent, every arm's flat top landed on the midplate's back
# face 0.48 before home (0.266 over the notch's edge; 0.466 with the plate pushed its EDGE_CLR toward the arm), and
# with the board 0.35 toward a wall (its play on the snap posts plus the midplate's) ten arms' tops landed on the
# board's back face 2.48 before home (lid_close.latch_arms; the build's rigid sweep moves the arms unbent). The 3.68
# had the same fault (case-368: notch 1.6, chamfers 0.5 x 0.5). Here every arm's inner top corner is cut 0.4 x 0.4,
# the most that keeps a 0.2 flat on the 0.6 tip; it ends 0.39 above the barb's flat, so the barb, its catch and lead-in
# and the latch forces are as before (mechanics.latches). With the notch at 0.85 the arms clear the plate all the way
# home, 0.196 (0.053 with the plate pushed 0.2), and the board pushed toward a wall meets the chamfer, a 45-degree cam
# that pushes it back. Over each notch's 5.1 the plate stops 0.825 inside the nominal glass's edge (was 0.675). At
# left Y 83 / 102 the battery rail stands 1.26 in. At right Y 100.3 the Y-102 spring's window stands 0.51 behind a 0.7
# notch, 0.36 behind this one, under one printed line (OrcaSlicer's classic walls drop it), so there the notch runs on
# into the window (midplate.latch_notches, MIN_WEB).
SNAP_INNER_CHAMFER = {(w, c): (0.4, 0.4) for w, cs in SNAPS.items() for c in cs}   # (wall, centre): (along the
                                                                                     # top, down the inner face)

# ---- battery: the site's 503035 model (battery-connected-mm.stl) ------
# Cell with wrap is 37.20 x 31.10 x 5.18. Placed in the board notch, resting on the midplate,
# 1.25 clear of the notch's bottom edge and 0.3 below the tub's top wall.
BATT = dict(x=(1.11, 38.31), y=(82.0, 113.1), z=(MID_REAR - 5.18, MID_REAR))
BATT_MODEL_SHIFT = (0.30, 1.80, 0.61)     # from the site placement to this one
BATT_CLR = 0.3
FENCE = dict(t=0.8, len=2.0, z1=-1.0, clr=0.26, lead_in=0.4)   # battery rails on the midplate
# Rev H battery bay: a slot, not a cage. The left rail is continuous and the right one is posts (the
# lead leaves between them); both run out to the midplate's top edge, flared, so the cell can slide
# in from there before the midplate goes into the tub. The bottom is a STOP only STOP_H tall instead of
# Rev G's six 3 mm posts: J7's card mouth faces this edge 3.4 mm away, and the card travels 0.35-1.45
# mm behind the board's rear face, so a low stop (z 1.0-2.0) lets it eject straight past once the cell
# is out of the way.
# Two of the right posts are also CLEATS: they stand past the cell's back, capped along Y, so a
# long lead can be wound round them and let out again when the cell has to come out for a card.
# Rev I (Ian: "some sort of overhang structure to secure it while it's seated, like a proper slot in").
# The rails now reach past the cell's back and turn in over its edges:
#   left      a continuous LIP along the rail, lip_over over the cell's edge, lip_z clear of its back
#   right     the two plain posts become SNAPS: a 45-degree barb, snap_over over the edge, on a post
#             thin enough to flex out of the way. Tuck the left edge under the lip and press the right
#             side down and it clicks in; or slide it in from the top edge as before. To take it out
#             - for the microSD card - lift the right side past the snaps and swing it out from the lip.
# Every lip's underside is 45 degrees, so the midplate still prints without supports.
# Rev J (Ian: the bottom-most peg is in the way when pulling the battery plug out). The lower cleat's cap
# reached y 84.6, the plug's own edge, right where a thumbnail grips it on its way out of J5. The cleat
# moves up 3.0 mm, which leaves 2.95 mm between the plug and the cap, and the lower snap moves up 1.5
# to stay clear of it; the lead still leaves the cell above that snap, at y 96.8.
# ---- stack detents (Rev K) -------------------------------------------------------------------
# Ian puts the display, the midplate and the PCBA together first and pushes that stack into the tub.
# Until the lid was on nothing held it, so it slid in and out, and nothing said it was home - which
# matters, because the two bottom screws go past the ribbons' fold. Now the midplate clicks in. At four
# places its edge is a cantilever strip, cut free by a slot, with a bump on it that rides 0.25 into the
# tub's wall on the way in and snaps into a shallow pocket in the wall. The pocket is long enough in Z
# for the panel's +-0.2 thickness, so once the lid is on the bumps are slack and fight nothing; before
# that they hold the stack within a few tenths of seated. The pocket's roof is 45 degrees (it is a
# roof in the face-down tub), which is also what lets the stack come out again with a firm pull.
#   w, slot, len   the strip (in the plate's plane) and the slot behind it, 0.5 like the springs' slots
#                  so the squashed first layer cannot close it; root at spans' y, runs +y
#   bump           how far the bump stands past the plate's edge; the wall is EDGE_CLR (0.2) away, so
#                  it rides 0.25 into the wall on the way in, and that is also how much it catches
#   depth, clr     the wall pocket: how deep past the wall face, and its clearance round the bump in Y
#   z0, z1         the pocket's roof starts z0 at the wall face (the bump's tip meets it 0.25 higher,
#                  below where a +0.2 panel puts the plate); z1 its far end, past a -0.2 panel's plate
#   lead           a 45-degree chamfer on the bump's front edge, so it cams in past the tongue's tip
MID_DETENT = dict(w=0.7, slot=0.5, len=6.2, bump=0.45, bump_len=1.6, tip_slot=0.5, lead=0.3,
                  spans={'right': [14.9, 85.3], 'left': [14.9, 86.0]},
                  depth=0.35, clr=0.3, z0=1.4, z1=3.35)
BAY = dict(stop_h=1.0, flare=1.2, cleats=(89.5, 108.2), cleat_t=1.2, cleat_top=-4.6, cap=0.9, cap_h=0.4,
           lip_over=0.9, lip_z=0.2, lip_t=0.32, snap_over=0.5, snaps=((92.0, 94.0), (103.0, 105.0)))

# ---- light-strip variant (4.26in) ------------------------------------------------------------
# Used only when LIGHT_STRIP (VARIANT, at the top). That build carries the Silkscreen light strip
# (silkscreen-light-strip): a 2.3 mm flex bar with six warm/cool pairs of XL-4008 side-view LEDs, taped
# on the PLAIN GDEY0426T82's left border ("above the screen") and shining +X under the lip into the
# window. The strip's tail goes round the glass's bottom edge, through the board's ribbon slot and along
# the back into J3 (the FT01C's frontlight connector). The FT01C touch + frontlight panel does not fit
# that tub: its stops would press on the touch film. Only the tub changes; the lid, the midplate and the
# keys are the Rev K parts, shared with the standard build (build.py asserts it).
# Strip geometry (outline, LEDs, stiffener areas, diodes) is the strip's own export, copied here:
STRIP_GEOMETRY = 'hardware/reference/light-strip/strip-geometry.json'
# Plain GDEY0426T82 (strip docs/research/mechanical-fit.md): same glass outline and position as the
# FT01C's EPD, 0.926 +-0.1 thick = 0.5 TFT glass + 0.17 FPL + 0.256 PS. The PS (protective sheet, the
# top face) is inset from the glass edge 0.8 +-0.2 on the long sides, 0.5 +-0.2 at the top, 4.0 at the
# bottom (the bottom 4.0 is the bare-glass ledge with the COG IC and the EPD FPC's bond); the FPL
# under it is inset 2.0 / 2.0 / 1.7 / 5.2 +-0.2, so over the outer 1.2 mm of each long side the PS
# overhangs the FPL's edge. The EPD FPC leaves the bottom edge 15.45 +-0.3 from the left, 31.3 wide.
#   inset  (left, right, top, bottom) from the glass edge
PLAIN = dict(t=0.926, t_tol=0.1, glass=0.5, fpl=0.17, ps=0.256,
             ps_inset=(0.8, 0.8, 0.5, 4.0), fpl_inset=(2.0, 2.0, 1.7, 5.2), inset_tol=0.2,
             fpc_t=0.12,
             # EPD FPC outline beyond the glass edge (u, v as panel.RIBBONS): only the 31.3 width at the glass
             # and the 24 mm tail are from the drawing; the taper to the J2 end is the FT01C's (panel.py)
             fpc_poly=[(15.45, 0.0), (46.75, 0.0), (46.75, -3.03), (41.32, -14.68), (37.34, -16.45),
                       (37.34, -24.01), (24.81, -24.01), (24.81, -16.45), (17.87, -13.56), (15.45, -3.03)])
# Printed heights. The tub prints face down in LAYER layers from Z_FRONT and the slicer cuts each layer at
# its mid-plane, so a face that is not on a layer boundary (layer_z) prints at one: the first cut of this
# variant had the stops at 3.926 (they printed to 4.00), the pads at 4.311 (4.40) and the ceiling at 5.30
# (5.40: 5.30 is layer 4's own mid-plane, and that layer was dropped). Every Z face this variant adds or
# cuts is on a boundary, or on a 45-degree slope, so the model is what prints.
def layer_z(k):
    """The k-th layer boundary from the tub's face (k = 0 is the bed)."""
    return round(Z_FRONT - k * LAYER, 3)


# The stops (below) hold the plain panel's PS face at the layer boundary 4.00, the one nearest where the
# FT01C's rear would have put it (DISP_REAR + 0.926 = 3.926) and in front of it. The springs push the plate
# and the panel onto the stops, so the panel's rear sits at 3.074, 0.074 in front of the midplate's modelled
# seat (DISP_REAR), and the springs deflect 0.276 of their 0.6 travel (0.176 on a -0.1 panel, 0.376 on a
# +0.1 one; mechanics.py 'plain_stack'), not the FT01C's 0.35. The next boundary back, 3.80, would leave a
# +0.1 panel only 0.024 of travel.
PLAIN_FRONT = layer_z(10)                                      # 4.00
# The strip's stack on the PS, in its stiffened areas (the top-pair piece and the bar + foot): 3M 9077
# tape 0.05 + PI stiffener 0.225 on the flex's B side, flex 0.11; the LEDs (0.8 tall) on the F side.
# The hinge between the top pair and the bar is bare flex (no stiffener, no tape).
STRIP_STACK = dict(tape=0.05, pi=0.225, flex=0.11, led_h=0.8)
STRIP_FLEX_TOP = PLAIN_FRONT + STRIP_STACK['tape'] + STRIP_STACK['pi'] + STRIP_STACK['flex']   # 4.385
STRIP_LED_TOP = STRIP_FLEX_TOP + STRIP_STACK['led_h']                                         # 5.185
# Each LED's two solder pads (lib/silkscreen-light-strip.pretty/LED_SideView_XINGLIGHT_XL-4008.kicad_mod,
# paste over the whole pad; tools/build_pcb.py PAD_EDGE 2.65): from y[0] to y[1] either side of its centre
# along the bar, and x across it (CAD X -0.54..0.46 about the LEDs' line at -0.04). The hold-downs are sized
# from these, not from the 4.0 body: a pad must never press on a solder joint.
STRIP_COPPER = dict(y=(1.05, 2.65), x=(-0.5, 0.5))
# Where the strip is laid on the glass across the bar (README fitting step 3): the bar's outer (left) edge
# `inset` inside the glass's left edge, +-tol. As drawn (the strip's export, which refs.strip_front and every
# check use as the strip's reference position) that edge is at bar_x0 = -1.24, 0.055 PAST the glass's edge
# (PANEL_X0 -1.185). From the tub's back rim (Z -5.15) up to the wall relief (3.68) nothing of the pocket's left
# wall stands inside POCKET_X0 (no lead-in); it only steps OUT, at Rev K's latch windows (to -2.01, Z 0.95-2.63,
# square top ends) and lid-tab slots (Y 58-65, 72-79). The bar goes in 0.811 ahead of the glass (PS 0.256 +
# FPL 0.17 + tape, PI and flex 0.385). Laid on or past the glass's edge, the bar meets that wall first when
# the stack drifts left and rides it for the whole stroke, held only by its tape. 0.1 inside keeps it behind
# the glass's edge at both ends of its placement (0.0-0.2 in), so the glass is what meets the wall; with the
# glass kept from centred to the right as the stack goes in (fitting step 5) the bar is at least 0.175 clear,
# 0.275 at the 0.1-inside placement. A bar past the glass edge could also drop into a latch window and hit its
# square top end, one more reason for the placement rule.
# STRIP_DX_FIT: the move from the drawn position to the nominal placement (+0.155).
STRIP_PLACE = dict(inset=0.1, tol=0.1, bar_x0=-1.24)
STRIP_DX_FIT = round(hw.PANEL_X0 + STRIP_PLACE['inset'] - STRIP_PLACE['bar_x0'], 3)        # +0.155
# The plain glass's outline: 62.37 x 105.33 +-0.1 (the strip's mechanical-fit.md). The pocket is sized from
# the FT01C drawing's +-0.15 x +-0.2 (hw.PANEL_W_TOL, PANEL_H_TOL).
PLAIN_OUTLINE_TOL = 0.1
# The glass's left edge from its drawn (centred) position: against the left wall (-0.225, any size) to the
# smallest glass against the right wall (+0.325)
STRIP_GLASS_DX = (round(POCKET_X0 - hw.PANEL_X0, 3), round(POCKET_X1 - (hw.PANEL_W - PLAIN_OUTLINE_TOL) - hw.PANEL_X0, 3))
# Where the strip can sit relative to the tub. Y: the plain glass anywhere in the pocket (bottom edge
# 5.035..5.635, -0.25 / +0.35 from nominal) plus the strip's own placement on it (+-0.2). X: the glass's
# left edge (STRIP_GLASS_DX) plus the strip's placement on it (STRIP_DX_FIT +-tol): -0.17..+0.58. (Before the
# placement rule it was +-0.425: the panel +-0.225 at its nominal size plus +-0.2 on the glass.)
# strip_check moves the strip over this box.
STRIP_SWEEP = dict(dy=(-0.45, 0.55),
                   dx=(round(STRIP_GLASS_DX[0] + STRIP_DX_FIT - STRIP_PLACE['tol'], 3),
                       round(STRIP_GLASS_DX[1] + STRIP_DX_FIT + STRIP_PLACE['tol'], 3)))
# The stack pushed in across the pocket (build.insertion_check), the glass at its largest (62.47, so on the
# right its left edge is furthest left), with the strip at both ends and the middle of its placement. The
# glass's left edge in each case:
#   left wall   the glass against the left wall (-1.41): the case the placement rule is for
#   centred     -1.235
#   right side  its right edge on INSERT_X1 (61.31), the right side's narrowest point on the way in: the
#               USB-C port's floor (Rev K, tub.usb_features) stands 0.1 inside the right wall over Y 34.95-47.65,
#               from the parting plane (Z -3.75, a square end) up to Z 1.645
#   right wall  its right edge on the wall itself (61.41): the glass meets that floor's end (4.19 mm3), so
#               "against the right wall" in fitting step 5 means toward it, not pressed into it
STRIP_INSERT_GLASS_X0 = {'left wall': POCKET_X0,
                         'centred': round((hw.PANEL_X0 + hw.PANEL_X1 - hw.PANEL_W - PLAIN_OUTLINE_TOL) / 2, 3),
                         'right side': round(INSERT_X1 - (hw.PANEL_W + PLAIN_OUTLINE_TOL), 3),
                         'right wall': round(POCKET_X1 - (hw.PANEL_W + PLAIN_OUTLINE_TOL), 3)}
# Window edges at the lip (tub.window): active area + WINDOW_MARGIN
WIN_X0 = hw.ACTIVE_CX - hw.ACTIVE_W / 2 - WINDOW_MARGIN        # 1.56
WIN_X1 = hw.ACTIVE_CX + hw.ACTIVE_W / 2 + WINDOW_MARGIN        # 58.44
WIN_Y0 = hw.ACTIVE_CY - hw.ACTIVE_H / 2 - WINDOW_MARGIN        # 14.5
WIN_Y1 = hw.ACTIVE_CY + hw.ACTIVE_H / 2 + WINDOW_MARGIN        # 108.5
# The light-strip builds' window (tub.window), Rev K's: a 45-degree bevel per edge. Rev K bevels all four 0.6
# (WINDOW_CHAMFER) from the face down to the land at 5.40. Over the left border the raised ceiling (below) is at
# 5.40 too, so a 0.6 bevel there left a knife edge in front of the LEDs: one 0.2 layer at X 1.45-1.56. 0.2 keeps the
# skin in front of the LEDs 0.6 thick (three layers) to X 1.36 and 0.4 (two) at the edge; the first layer steps
# back 0.1 there as it prints. (The other builds' window: WINDOW_BEVEL_* above.)
WINDOW_BEVEL = dict(left=0.2, right=WINDOW_CHAMFER, bottom=WINDOW_CHAMFER, top=WINDOW_CHAMFER)
# Raised ceiling over the left border. The LED tops (5.185) stand 0.205 above the lip (4.98), and their
# light has to pass under the skin all the way to the window's edge, so over the bar and the hinge the
# skin's underside goes up to z, from the pocket's wall (the step wall above POCKET_STEP_Z goes: the bar
# overhangs the glass by 0.055, and its top, 4.385, is above the step) to the window. z is the layer
# boundary 5.40: 0.215 over the LED tops, 0.60 of skin (three layers).
#   y       the bar's run: 4.1 under the lowest LED's end (16.6) to 0.4 past the top piece's round end
#   step_y  where the step wall goes: also along the foot, whose left end (X -1.24) is past the glass edge,
#           from 0.1 below the foot's end (9.25) with the strip at -0.45 (STRIP_SWEEP)
STRIP_CEIL = dict(x=(POCKET_X0, WIN_X0), y=(12.5, 109.6), z=layer_z(3), step_y=(8.7, 109.6))
# Hold-down pads: the stops hold the other three borders, so with the ceiling raised only these keep the
# left edge down. Each hangs from the ceiling to z, the layer boundary 4.40, 0.015 over the bar's flex top
# (4.385) at nominal: the springs lift the left edge onto them, and they keep the strip down.
#   x     from the pocket's wall to 0.9 (0.6 before the panel-retention review). A pad presses the panel
#         through the bar, and only where the bar lies on PS with FPL under it does that go straight into
#         the glass. The FPL's edge is 2.0 +-0.2 in from the glass edge (X 0.815 with the glass centred);
#         over the PS's outer 1.2 (the overhang, carried only by the edge seal) and the bare glass the bar
#         is a lever on the PS flap and its own tape. Ending at 0.6 the pads reached no FPL-backed bar with
#         the glass centred or to the right of it (fitting step 5). At 0.9 they reach 0.085 of it with the
#         glass centred (1.1 mm2 over the seven pads, 0-3.7 mm2 with the FPL's +-0.2), and their inner ends
#         are 0.3 nearer the FPL edge; beyond 0.085 right of centre (step 5's nominal +0.125 included) they
#         reach none at the FPL's nominal inset. What 0.9 buys is a shorter lever on the PS/FPL edge, not less
#         lift: the PS overhang bends <= 0.025 under the pads' whole load. 0.9 is the largest end that stays behind every LED face with the glass
#         centred or to the right: a face is 2.2 in from the bar's drawn edge (X 0.96 as drawn, 1.115 as
#         placed, 1.015 at least with the glass centred and the bar on its edge), so 0.115 clear, and still
#         0.015 with an LED sitting 0.1 back on its pads. With the glass against the left wall and the bar
#         on its edge (STRIP_SWEEP dx -0.17) a face can be 0.11 behind the pads' ends; the pads are then
#         beside the LEDs, at least 0.75 from a body along the bar, so only light more than 80 degrees off
#         the LED's axis reaches them.
# In Y each stays off the LEDs' solder pads (STRIP_COPPER): 0.65 above the copper of the LED below it and
# 0.6 below the copper of the LED above it, so that across STRIP_SWEEP's -0.45..+0.55 the nearest copper is
# still 0.10 / 0.15 away. Between a pair's two LEDs the copper gap is 1.3, too short for a pad, so none goes there.
#   ys    (y0, y1): under D6 (copper from 15.95); between the pairs (copper 27.85|31.5, 43.4|47.05,
#         58.95|62.6, 74.5|78.15); just under D1 (copper from 95.15; its foot 94.0 is 0.025 over the hinge's
#         end, 93.975, so at nominal it is all on the top piece and none of it on the hinge's bare flex,
#         which is 0.275 lower); over the top piece's round end (D7's copper ends 107.05; the end is at 109.15).
#         The two on the top piece cannot be moved to bear fully over the whole Y sweep. The one under D1
#         bears on the top piece only up to the strip at +0.025 in Y; further up its lower part is over the
#         hinge, and at +0.55 only 0.025 of it is on the piece (0.05 mm2, against 1.1). The piece between
#         the hinge's end and D1's copper is 1.175 long, less than the sweep (1.0) plus the copper
#         clearances and any bearing length. The one over the round end runs off the rounded corners with
#         the strip down (1.43 mm2 on the piece at -0.45, 1.59 at +0.55) but always bears; it cannot start
#         lower without closing on D7's copper.
STRIP_HOLD = dict(x=(POCKET_X0, 0.9), z=layer_z(8),
                  ys=[(13.3, 15.35), (28.5, 30.9), (44.05, 46.45), (59.6, 62.0), (75.15, 77.55),
                      (94.0, 94.55), (107.7, 108.5)],
                  foot=dict(x=(2.0, 7.2), y=(9.8, 12.2)))
# Relief in the pocket's left wall, so the strip is never the panel's left stop: as drawn the bar and the
# foot overhang the glass's left edge by 0.055 (left end X -1.24, 0.17 from the wall with the panel centred),
# and with the panel 0.225 left in its pocket and the strip 0.2 left on it, the bar would reach -1.665, 0.255
# into the wall, where only the tape holds it. `depth` past the wall face (to -1.71: 0.045 clear at worst).
# With the placement rule (STRIP_PLACE: the bar 0.0-0.2 inside the glass's edge) the bar never gets past
# the wall face (-1.41), so the relief is now a backstop for a strip laid past the glass's edge. Its
# roof (a roof in the face-down tub) starts at the wall face at z0 and rises `rise` to full depth at 4.00,
# the tape's underside: 43 degrees from vertical, so it prints as a plain chamfer and stays inside
# plates.py's 45-degree overhang audit (an exact 45 lands on the audit's threshold). z0 is 0.106 over the
# glass's top (3.574), so the glass still bears on the wall below it. z1, the far end, is the layer
# boundary 4.60, 0.215 past the bar's top (4.385). y covers the foot's left end and the bar with the whole
# Y sweep (the foot starts at 9.25).
STRIP_WALL_RELIEF = dict(depth=0.3, rise=0.32, z0=3.68, z1=layer_z(7), y=(8.7, 109.6))
# Panel stops: rails hanging from the lip onto the PS at PLAIN_FRONT, just outside the window, each
# placed so it stays on the PS at the panel's worst size and position in the pocket (PS edge at least
# 59.91 on the right, 109.67 at the top, at most 9.79 at the bottom). The top and right rails are mostly
# over the FPL (its edge is 59.19 / 108.92 nominal); the bottom rail is always over it (edge <= 10.99).
# The bottom rail starts at x 14.3: 0.54 clear of the strip's neck (13.76) and foot; the ledge, the COG
# IC and the EPD FPC's bond are all below the PS's edge, which the rail never reaches.
PANEL_STOPS = dict(right=dict(x=(WIN_X1, 59.3), y=(11.0, 109.1)),
                   top=dict(x=(2.2, 59.3), y=(WIN_Y1, 109.1)),
                   bottom=dict(x=(14.3, 59.3), y=(11.0, WIN_Y0)))
# The strip's neck (X 8.247..13.76) goes over the glass's bottom edge 0.04 inside the ribbon gap's old left
# edge (8.285, sized from the FT01C's frontlight tail); the gap now starts here, 0.55 clear of it. The pocket's
# bottom wall left of it (to the H3 boss's flat at 5.95) still holds the glass's corner.
STRIP_GAP_X0 = 7.7
# The tail's modelled shapes (refs.strip_path): the U round the glass edge, R1 the U's inside radius,
# R2 the turn down into the slot, R3 the turn onto the board's back, yd the drop's mid-plane in the slot,
# tip the contact tip home in J3 (CAD Y 23.25 +-0.3). Whatever length the path does not use goes into the U,
# which then reaches further past the glass edge (tools/foldpath.py: 0.5-2.2 mm spare on the 4.26in).
#   nominal  foldpath's nominal radii, yd where the flex clears both slot edges with R2 = R3 = 0.8
#   reach    the U at its largest (its bottom leg 0.06 over the board: R1 0.9 with the glass's top at
#            3.574, the panel on the 4.00 stops) with the most spare (tip 0.3 short of home) and extra:
#            0.5 more flex than drawn (the outline's own tolerance, and the panel sitting 0.25 toward the
#            chin in its pocket, which moves the U 0.125 that way): the furthest the U reaches
STRIP_TAIL = {'nominal': dict(R1=0.8, R2=0.8, R3=0.8, yd=6.14, tip=23.25),
              'reach': dict(R1=0.9, R2=0.6, R3=0.6, yd=6.28, tip=22.95, extra=0.5)}
# SW9's left mounting-lug lead: its tip stands to Z 2.307 at X 7.77-8.15, Y 3.8-4.8, 0.10 left of the
# strip's neck; with the panel and the strip both left (STRIP_SWEEP dx) the U's lower leg lands on it, and
# the tub cannot move either. Fitting (README): trim it flush, to z at most (0.1 over the board's face),
# and cover it with Kapton (kapton thick; mechanical-fit.md section 4 already asks for Kapton here).
# strip_check measures the tail against the lead as it is and as trimmed (x, y: the stub with its tape).
SW9_LEAD_TRIM = dict(z=1.7, kapton=0.06, x=(7.71, 8.21), y=(3.74, 4.86))
STRIP_DRAPE = 2.0               # the bare neck leaves the foot (Y 9.25, flex on the stiffener) and lies on the
                                # ledge this far on, a straight 19-degree drop of 0.7
STRIP_J3_MID = -0.35            # the stack's centre in J3's mouth (the FT01C frontlight tail's, panel.py: -0.5..-0.2)
STRIP_DIODE = dict(w=2.2, l=2.2, h=1.1)   # SOT-323 envelope with its leads, on the tail's F side
