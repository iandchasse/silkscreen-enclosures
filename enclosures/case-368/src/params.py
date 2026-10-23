"""Design parameters for the Silkscreen x3 enclosure. Millimetres, CAD frame from hw.py:
X = KiCad X - 44.24, Y = 148.25 - KiCad Y, Z = 0 at the PCB rear face, +Z toward the screen.

x3 is Rev K (the printed-and-refined Silkscreen case) rebuilt around three changes Ian asked for:
  - the 3.68-inch 528 x 792 panel (0.87 thick, one 24-pin FPC) instead of the 4.26-inch touch/light panel
  - the board trimmed just above J5, with power moved to SW7 (UP2) and SW5 (DWN2) left off
  - the battery inside the case, as thin as possible, on a ~20 mm lead to J5

Everything that sets a fit or a stack height lives here, with the reason next to it. Where a value is
Rev K's, it is because a print proved it; the Rev K design notes are the numbered sections of ../case-426/README.md.

Two builds (variant.py): standard (x3 as designed, but for the parts it shares with the light-strip build) and
light-strip. Every printed part but the tub and the bottom keys is shared, so everything that shapes the lid, the
midplate and the cranks is the same in both; the tub reads LIGHT_STRIP (the raised face, the window, the strip's channel
and the rest), and the bottom keys stand a fixed height over their own tub's face (KEY_TOP_OVER_FACE).
"""
import math
import hw
import variant

VARIANT = variant.NAME
LIGHT_STRIP = variant.LIGHT_STRIP

# ---- printing -------------------------------------------------------------------------
NOZZLE = 0.4
LAYER = 0.2
FIT = 0.20            # sliding / drop-in clearance per side for printed-to-hardware fits
LOOSE = 0.30          # clearance for moving printed parts


def printed_top(h):
    """Where a face h over the bed prints: the slicer keeps a layer only if its mid-plane is inside the part, so the
    part's last layer is the one whose mid-plane is under h (a face between layer lines moves to the line under it or
    over it, whichever mid-plane it passes)."""
    return round(LAYER * (math.ceil(h / LAYER + 0.5 - 1e-9) - 1), 3)

# ---- Z stack (front to back) ------------------------------------------------------------
# The thickness is set behind the board. Nothing on the front but trimmed leads, so the front stack
# is just skin + panel + midplate. Behind the board, the deepest parts are J5 (-4.935), the side and
# bottom switches (-4.493), L1 (-4.085), J1 (-3.535) and the ESP32 module (-3.185); everything else is
# 1.635 or less. The battery therefore sits over that shallow middle (params BATT) and the back is set by
# the battery, not by anything else: 1.635 + 0.2 + the cell's 5.2 allowance + a 0.8 floor.
PCB_REAR = 0.0
PCB_FRONT = hw.PCB_T                      # 1.6
LEAD_TIP = 2.25                           # through-hole lead tips, trimmed to 0.65 proud (the MJTP1117 pins stand
                                          # 0.71 as supplied, J5's leads 1.72: both are trimmed to this)
MID_REAR = 1.8                            # midplate rear face: 0.2 above the PCB (the spring nubs' travel; 0.1 left
                                          # with the thickest panel). Rev K and x3's first passes: 0.3
MID_T = 0.8                               # four layers; the 0.4 bridge springs have 0.4 of room to deflect
DISP_REAR = MID_REAR + MID_T              # 2.60, 0.35 over the trimmed lead tips
DISP_FRONT = DISP_REAR + hw.PANEL_T       # 3.47 nominal (+-0.1 per drawing: the springs take it up)
LIP = DISP_FRONT                          # lip underside = the panel's front (its PS film)
SKIN = 0.6                                # front skin / screen lip: three layers (Rev K and x3's first passes: 0.8)
Z_FRONT_BASE = LIP + SKIN                 # 4.07: x3's front face (the standard build's until 2026-10). The screw
                                          # pilots stay referenced to it in both builds
# Light-strip variant: the strip's bar lies beside the panel at the panel-front plane with its LEDs 1.185 proud
# of it (LIP + STRIP_STACK + LED_H = 4.655), and the light has to pass under the skin to the window. The skin
# over the bar needs its underside above the LED tops (>= 0.1) and CHANNEL_SKIN of plastic over that: at least
# 4.655 + 0.1 + 0.4 = 5.155. The whole front goes up (a planar face prints face down with no support; a local
# hood would put a step in the bed face). 1.2 rather than 1.1: the face prints on the bed, so every plane that
# matters must sit a whole number of 0.2 layers from it. At +1.1 the lip (the panel's stop and the bar's seat)
# fell on a layer's middle and the slicer put it 0.1 off (out/x3/slice, first pass); at +1.2 the lip is 9 layers
# from the face and the LEDs clear the skin by 0.215.
FRONT_RAISE = 1.2
Z_FRONT_STRIP = Z_FRONT_BASE + FRONT_RAISE                      # 5.27: the light-strip tub's face. The strip's own
                                          # numbers below are set from it
# Standard: the face is raised STD_FACE_RAISE over x3's (2026-10, the screen bezel: Ian, 'longer and more exaggerated
# chamfer, rounded at the corners too'; the 4.26 takes 35 degrees). The skin over the panel's border goes 0.6 -> 1.0,
# the 4.26's (1.02), so the window takes the 4.26's bevel (WINDOW_BEVEL_*). In x3's 0.6 skin a 35-degree bevel is
# only 0.71 wide (0.5 / tan 35). Whole layers (two), one plane (it prints on the bed), so every plane below stays on
# the layer grid; the bottom keys stand KEY_TOP_OVER_FACE over it (key-x3std 0.4 taller, its hooks 0.4 higher with
# the slot roof); the screw pilots stay at Z_FRONT_BASE's depth. The case is 11.7 (x3: 11.3). The light-strip face
# (Z_FRONT_STRIP) does not move. Ian, 2026-10-10: 'go with +0.4 on the 3.68'. A tub, key-x3std or coupon printed
# before this does not mix with one printed after it: reprint them together.
STD_FACE_RAISE = 0.4
assert STD_FACE_RAISE >= 0 and abs(STD_FACE_RAISE / LAYER - round(STD_FACE_RAISE / LAYER)) < 1e-9, \
    f'STD_FACE_RAISE {STD_FACE_RAISE}: whole {LAYER} layers only (the face prints on the bed; every plane is on its grid)'
Z_FRONT = Z_FRONT_STRIP if LIGHT_STRIP else round(Z_FRONT_BASE + STD_FACE_RAISE, 3)   # this build's face: 5.27 / 4.47
SEAM = -3.75                              # tub / lid parting plane: just under the USB shell (-3.535), as Rev K

# ---- battery (x3) ------------------------------------------------------------------------------
# 500 mAh minimum (Ian). Reference cell: 503035 LiPo, 3.7 V 500 mAh, JST PH2.0 - the pack Rev K carried. Its
# model (hardware/battery-connected-mm.stl) is 31.1 x 37.3 x 5.18 with its wrap, the lead leaving the middle of a
# short edge. Amazon sells the same size, listed as 5 x 30 x 37 (e.g. B07S84SBV3, $7.99, 50 mm lead).
# Why this cell: the only place a cell adds no depth past its own is over the shallow middle of the board
# (nothing there deeper than 1.635), and it has to reach J5 on a ~20 mm lead. A rotated-rectangle search over
# that region (every angle, the lead end within reach of the plug) finds room for a 30 x 37 cell only; the
# thinner 500 mAh cells on Amazon (402050: 20 x 50 x 3.65, 403048: 30.5 x 50 x 4.3) are too long to reach J5
# from anywhere they fit. So: 5 mm, and the case is 12.2 mm.
# The cell lies in the lid, behind the board, portrait, lead end at the top, over J7, U1, U3, U9 and passives:
#   left   6.98: 0.6 clear of SW7's body (x <= 6.38); H2's lid post moves to SW5's empty site (SUPPORT_POSTS)
#   right  38.08: 2.3 short of J5's plug, whose rear face is at X 40.36
#   bottom 56.0: the bay's wall stands 0.35 above the ESP32 module's top edge (Y 54.75, 3.185 deep)
#   top    93.3: the lead end. The lead U-turns over it and runs back across the pack's face to J5, where the
#          board has been cut away (refs.lead_path): about 26 mm from a centre exit
# Not over the ESP32's antenna, but close: the cell's bottom-left corner is 1.25 mm above the module's top edge at
# the antenna end's inner corner (X 0.51-7.5). Moving BATT up buys room there at 1 mm of case height and of lead
# per mm. The charger (U11) and the module are beside the cell, not under it.
BATT_REF = dict(name='503035 LiPo 3.7 V 500 mAh, JST PH2.0', size=(31.1, 37.3, 5.18),
                url='https://www.amazon.com/dp/B07S84SBV3', lead='about 20 mm routed; PH2.0 plug into J5')
# 2026-10-19: the bay's air is judged against the thickest cell the datasheet allows (LiPol LP503035, FD_3855_10: 5.0 +-
# 0.3 thick, 30 +-0.5 wide, 36 +-1.0 long with the PCM, lead 35 +-3 mm) with two layers of 0.18 tape on each face:
# 5.3 + 4 x 0.18 = 6.02. bayread uses it; BATT_T_MAX (5.20) only places the pocket.
BATT_ENV_T = round(5.3 + 4 * 0.18, 2)   # 6.02
# Squeezed (Ian: "a little unsafer"): 0.1 from the parts over it (was 0.2), a 5.20 allowance (was 5.25) and two
# layers of floor under it (was 0.8). That left 0.12 mm for the pack to swell before it touched J7.
# 2026-10-12, LID_DROP: Ian's first print (2026-10-11) would not close: "the lid does not shut on the 368 ... worse with
# the battery inserted but still doesn't close even if the battery is not present ... we can survive with a slightly
# thicker device with some more air in it so long as it closes snugly". Two causes (lid_close.py): the latch arms,
# bent by the tongue on the way in, landed on the midplate's edge (SNAP['notch']), and 0.1 of air left nothing for
# the charging bodge wires a Rev 1.0 board needs (the GND wire lies on C6, 1.335 deep, under the pack). The lid's
# back and floor drop LID_DROP (whole layers), all of it air between the pack and the board: 1.1 from J7, 1.3 from
# C6. What holds the board and the pack stays where it was: the posts at Z 0, the screw heads' seats (M2_CB_DEPTH
# + LID_DROP), the backstops, the latch arms (on a pedestal, LATCH_ROOT_Z) and, relative to the pack, its pocket,
# lip and hooks (a pack of BATT_T_MAX still has 0.15 under them). The case is 12.7 (light strip 13.5), was 11.7.
# 2026-10-19 (the bay study): the datasheet's 5.3 mm cell with two layers of tape on each face is 6.02 mm (BATT_ENV_T),
# which left 0.245 of air under J7. LID_DROP 1.2 and LID_T 1.0 (five layers) give it 0.445; the case is 12.9 (light
# strip 13.7). The lip is raised to clear that cell (BATT_LIP clr_z), the hooks are gone, and what holds the board
# stays where it was (the posts at Z 0, the screws' seats, the backstops' ends, the latch arms' roots).
LID_DROP = 1.2
assert abs(LID_DROP / LAYER - round(LID_DROP / LAYER)) < 1e-9, 'LID_DROP: whole layers (the back prints on the bed)'
BATT_T_MAX = 5.20                         # Rev K's pack is 5.18 with its wrap; Amazon's are listed at 5.0
BATT_CLR_BOARD = round(0.1 + LID_DROP, 3) # cell's front face to the deepest part over it, at BATT_T_MAX (was 0.1)
BATT_DEEPEST = 1.535                      # J7, the real MEM2075; U1/U3/U9 are 1.45 by TI's drawings (hw.DATASHEET_DEPTH)
BATT = dict(x=(6.98, 38.08), y=(56.0, 93.3), z=(None, None))
BATT_FRONT = -(BATT_DEEPEST + BATT_CLR_BOARD)             # -2.835 (was -2.635 until 2026-10-19, -1.635)
BATT_FLOOR = round(BATT_FRONT - BATT_T_MAX, 3)            # -8.035: the cell rests on the floor of its pocket
BATT_FLOOR_T = 0.4                                        # two layers under the cell: its pocket is sunk into the floor
BATT['z'] = (BATT_FLOOR, BATT_FRONT)
Z_BACK = round(BATT_FLOOR - BATT_FLOOR_T, 3)              # -8.435 (was -8.235 until 2026-10-19, -7.235)
LID_T = 1.0                               # five layers (four until 2026-10-19), everywhere but under the cell;
                                          # LID_FLOOR_IN stays -7.435
LID_FLOOR_IN = round(Z_BACK + LID_T, 3)   # -7.435 (was -6.435): the lid's floor round the cell's pocket
BATT_POCKET_CLR = 0.3                     # plan clearance round the pack: the pocket is 31.7 x 37.9
# retention (Rev I's battery slot, turned over): the cell's bottom edge tucks under a lip - the strip of board
# over it is bare but for a row of 0603 resistors, which the lip steps round. Until 2026-10-19 two hooks held its
# top end, where the board has been cut away; they are gone (they pressed the cell and its lead, and with the
# lip raised to clear a 6.02 cell nothing on the lid presses it): the cell is pushed into the bottom-right
# corner under the lip and taped down.
# The top end is open for the lead but for a low wall (BATT_END_STOP) that keeps the cell from sliding out from
# under the lip: 1.5 mm tall, it stays below the lead wherever it leaves the pack (at mid-thickness).
BATT_LIP = dict(over=0.5, t=0.4, clr_z=0.95, skip=(13.9, 22.7))   # 2026-10-19: clr_z was 0.15 (a 5.2 cell); 0.95 clears
                                          # the 6.02 cell by 0.15+ (at 1.0 the lip's top sat on a mid-plane)
BATT_END_STOP = dict(clr=0.1, t=0.8, h=1.4)   # h was 1.5, which put its top on a mid-plane (bed 1.9)
BATT_WALL_T = 0.8
BATT_WALL_BOTTOM_T = 0.5
BATT_WALL_LOW = dict(y=(70.9, 80.1), top=-4.8)            # under SW7's body (X <= 6.38, down to -4.493)
BATT_RIGHT_WALL_TO = 78.0                 # the right wall stops short of the plug
# H2's lid post (Rev G-K) would stand in the bay. The board's top-left is carried instead by a post in SW5's
# site, which is empty since DWN2 is left off (between its four pads).
SUPPORT_POSTS = [(4.0, 61.5, 3.0)]

# ---- outline (plan) ---------------------------------------------------------------------
# The case is as wide as Rev K: its side walls are set by the board and the side switches, which have not
# moved. The panel is narrower than the board, so its pocket sits inside the walls.
POCKET_CLR = 0.15                         # per side, at the drawing's maximum panel size
POCKET_X0 = hw.PANEL_X0 - hw.PANEL_W_TOL / 2 - POCKET_CLR      # 0.877
POCKET_X1 = hw.PANEL_X1 + hw.PANEL_W_TOL / 2 + POCKET_CLR      # 57.617
POCKET_Y0 = hw.PANEL_Y0 - hw.PANEL_H_TOL / 2 - POCKET_CLR      # 6.80
POCKET_Y1 = hw.PANEL_Y1 + hw.PANEL_H_TOL / 2 + POCKET_CLR      # 93.84
# Side walls below the panel: Rev K's, set by the switches (the board's and the midplate's way in).
WALL_X0, WALL_X1 = -1.41, 61.41
SLIVER = 0.93                                                  # Rev G/I: the continuous inner sliver
TAB_T = 1.05                                                   # the side key's bar; its outer face is the case face
TAB_VOID = 0.70                                                # the key's travel before it bottoms on the sliver
                                                               # (the +X keys' TAB_GAP_SIDE 0.15 leaves 0.10 more;
                                                               # their board backs off that much, side_key_reach)
SIDE_WALL = SLIVER + TAB_VOID + TAB_T                          # 2.68
X0 = WALL_X0 - SIDE_WALL                                       # -4.09
X1 = WALL_X1 + SIDE_WALL                                       # 64.09   (68.18 wide, as Rev K)
INSERT_CLR = 0.05
INSERT_X0 = -1.31                                              # the midplate / board corridor (Rev K's)
INSERT_X1 = 61.31                                              # (the USB floor's inside, 0.115 in front of J1)
TOP_IN = 96.4                             # 2.56 above the panel's pocket: room for the 37 mm cell's lead to turn
                                          # under the top wall (the gallery) and for the rib that backs the midplate
TOP_WALL = 2.2                            # thick enough for the top screw's boss beside it
Y1 = TOP_IN + TOP_WALL                    # 98.60
BOT_IN = -8.2                             # chin: Rev K's -7.2 moved 1.0 down (Ian, 2026-09-26) to make room for the
                                          # crank keys' chin-side guide and drag leaf; the lid's chin wall moves too
BOT_WALL = 1.2
Y0 = BOT_IN - BOT_WALL                    # -9.40
CORNER_R = 5.0                            # plan-view corner radius
FRONT_EDGE_R = 1.8                        # front face to side: 9 layers at 0.2
BACK_EDGE_R = 2.0                         # back face to side
SEAM_CHAMFER = 0.4                        # small V at the parting line on both halves (the tub's half stops short of
                                          # the key row on the chin: KEY_SLOT relief)
POCKET_STEP_Z = LIP + 1.0                 # no step: the thin panel's layers are inset only 0.65 (kept for callers)
POCKET_STEP_CLR = 0.45
# The frame round the panel pocket (between the pocket and the walls) must never touch the midplate,
# which moves with the panel's thickness: its rear face stays this far in front of a -0.1 panel's rear.
FRAME_REAR = DISP_REAR + hw.PANEL_T_TOL + 0.15                 # 2.95

# ---- screen window ----------------------------------------------------------------------
WINDOW_MARGIN = 0.5                       # beyond the active area at the lip underside
# Light-strip variant: the skin over the borders is 1.8 (Z_FRONT - LIP). A 0.6 straight land (x3: 0.3), then a
# 45-degree bevel of 1.2. The land's top (4.07) is on a layer line, 1.2 from the face. The bevel meets the channel's
# ceiling (CHANNEL_TOP) at X 2.03, which leaves the hold-down pads (PAD_X) 0.33 of full-depth skin to hang from; a
# 0.4 land would move that line to X 1.83 and leave them almost none. At 45 degrees the land hides 0.1 of the
# active area beyond the 0.5 margin. Standard until 2026-10: x3's 0.3 land and 0.3 chamfer on the 0.6 skin.
# Standard (2026-10): one slope from the face down WINDOW_CHAMFER, to the last skin layer's mid-plane (LIP + 0.1),
# so that layer prints on the lip line and the screen seen is x3's (the active area + 0.5); below it the window
# goes straight to the lip. x3's 0.3 land + 0.3 bevel printed its last two layers straight at the window's edge (a
# notch). The tub prints face down, so the slope is an overhang: each 0.2 layer steps 0.2 / tan(angle) in over air.
# 35 degrees: 0.286 (68 % of the 0.42 outer wall), which Orca lays as an outer wall slowed to 36 mm/s (30: 0.346,
# 18 mm/s, finely terraced; 25: the whole wall over air, an overhang wall: too far). The 4.26's numbers exactly.
# Corners: WINDOW_CORNER_R at the lip, R + W on the face (a cone, tangent to the sides: it prints like them). The
# window is only 0.5 past the active area and the panel has 0.25-0.35 of play a side, so the smallest panel pushed
# into a corner puts the active corner 0.15 / 0.15 from the window's: R0.4 keeps that pixel 0.046 in view by the
# CAD and about 0.035 as sliced (Orca's 0.012 resolution prints the corner about 0.01 inside the arc; the STL is on
# it); R0.5 keeps 0.005 by the CAD and none as sliced, R0.6 clips it. Both are under FDM hole accuracy, so this is
# a margin choice, not a visible one (R1.69 vs R1.79 on the face). The 4.26 keeps R0.5 (0.18 of margin there).
# Light strip: x3's 45-degree bevel with sharp corners, unchanged.
WINDOW_LAND = 0.6 if LIGHT_STRIP else round(LAYER / 2, 3)
WINDOW_CHAMFER = round(Z_FRONT - LIP - WINDOW_LAND, 3)          # 1.2 / 0.9 (x3: 0.3)
WINDOW_BEVEL_ANGLE = 45.0 if LIGHT_STRIP else 35.0
WINDOW_BEVEL_W = round(WINDOW_CHAMFER / math.tan(math.radians(WINDOW_BEVEL_ANGLE)), 3)    # 1.2 / 1.285 on the face
WINDOW_CORNER_R = 0.0 if LIGHT_STRIP else 0.4

# ---- surface details --------------------------------------------------------------------
# Wordmark in the chin (Rev K's 40 mm, bold 0.055 so the e's crossbar prints) and the book icon on the
# back. The chin's skin is thickened inside (tub.chin_web), so a 0.3 engraving still leaves >= 1 mm there.
# depth: 0.3 puts the ink's floor on a layer's mid-plane; as sliced, x3's printed 0.4 deep (two layers), but on the
# raised standard face 0.3 sliced to one layer (0.2). The standard's is 0.4, on the layer grid: two layers again
LOGO = dict(svg='hardware/logo/silkscreen-logo.svg', part='wordmark', width=40.0, depth=0.3 if LIGHT_STRIP else 0.4,
            x=30.0, y=5.6,
            min_feature=0.24, bold=0.055)
LOGO_BACK = dict(svg='hardware/logo/silkscreen-icon.svg', painter=True, mirror=True, width=26.0, depth=0.2,   # 0.3 was a
                 # layer's mid-plane (2026-10-19): today's lid printed 0.2, a new back printed 0.4; 0.2 keeps the look
                 x=(X0 + X1) / 2, y=(Y0 + Y1) / 2, min_feature=0.36, bold=0.10)
                                          # centred on the back (30.0, 44.6): the icon (y 35.3..53.9) stays 1.8 clear of
                                          # the battery pocket's thin floor (crank_checks.logo_back_floor)
KEY_EDGE_CHAMFER = 0.3                    # key openings' front edge (both builds: the caps stand proud of their own
                                          # tub's face, so the light strip's 45-degree wells are gone)
GRIP_GROOVES_Y = (-5.6, -3.6, -1.6)       # shallow grooves across the back's lower edge
GRIP_GROOVE = dict(x=(8.0, 52.0), width=0.8, depth=0.2)    # was 0.3, a mid-plane (as LOGO_BACK)

# ---- display ribbon: see panel.py ----------------------------------------------------------
FPC_GAP_CLR = 0.5                         # tub clearance round the FPC where it folds past the glass edge

# ---- bottom keys: bell crank + straight key (2026-09-26; replaces Rev D-K's rocker) ---------------------------------
# Ian's decisions (enclosures/BUTTONS.md, "Decided"); the numbers are the reviewed crank spec's (stage 4). The finger
# presses a straight key toward -Z; its flat pusher rides the crowned pad of a bell crank that turns on a length of
# 1.75 mm PLA filament; the crank's crowned nose pushes the switch plunger toward +Y. Input arm 4.95, output arm 2.95,
# so the key needs 0.596 x the switch force before friction (mechanics.key_forces). The rocker's pivot had to sit on the
# board's face with no mechanical advantage at all (1.4-2.8 x the switch force); the rod sits below the skin in front of
# the board's edge, where the lever can be had.
# Frame: dx is X from the key's centre (the switch's plunger); Y and Z as the CAD frame.
KEY_REFS = hw.BOTTOM_SWITCHES             # SW9, SW8, SW3, SW2 left to right
PLUNGER_Y = -1.92                         # MJTP1117's plunger face (the board STEP's switch)
PLUNGER_Z = -2.709
# Both switch families (Ian): the DigiKey build's APEM MJTP1117 and JLC's SHOU HAN TS365ZJ. The TS365's numbers are
# its drawing's, with its worst tolerances where it has none (BUTTONS.md open item: measure a real part).
SWITCH_FORCE = {'MJTP1117': (1.27, 1.86), 'TS365ZJ': (1.96, 2.94)}      # operating force range, N
TS365 = dict(tip_y=(-2.4, -2.0), tip_y_nom=-2.2, plunger_z_nom=(-3.25, -1.75), plunger_z_worst=(-3.05, -1.05),
             plunger_half_x=1.85, housing_y=-1.65, housing_half_x=3.65, body_z=(-3.6, 0.0))
TUB_BOARD_DY = 0.2                        # tub-to-board play in Y the rest positions and sweeps are checked over
# The rod: a cut length of 1.75 mm PLA filament, carried on both sides of every crank cheek, so it works in shear and
# bearing (14.6 MPa bending at a 20 N over-press, mechanics.crank_stress). It goes in along its axis through the -X side
# wall, along a channel in the gate's slot; the printed gate (below) is the left stop and the +X wall's inner face the
# right one. No screw (SPEC2 rev 3, 2026-09-28: the M2.5 x 4 flat head and its countersink are gone).
ROD_AXIS = (-2.50, 0.60)                  # (y, z)
ROD_D = 1.75                              # nominal; real filament is 1.72-1.78
ROD_D_RANGE = (1.72, 1.78)
ROD_CUT = 63.25                           # +-0.2: between the gate's flat (X -2.34) and the +X wall (61.41), 0.3-0.7 play
ROD_CUT_TOL = 0.2
ROD_TIP = dict(taper=1.25, flat=0.8)      # the end that goes in first: a pencil taper 1.0-1.5 long to a flat 0.7-0.9
                                          # across (it picks up a crank up to 0.80 off; a 0.3 point would dent the +X
                                          # wall at a drop). The tail is cut square: it bears on the gate
ROD_HOLE_D = 2.10                         # ring bores, open seats, the side wall's channel: a slip fit for 1.72-1.78.
                                          # 2.10, not 1.95: the face-down print stair-steps these horizontal holes,
                                          # and a 1.95 bore read back from the G-code only 1.75-1.79 free; 2.10 keeps
                                          # them >= 1.90 free as printed (slice_check.bores)
ROD_TEARDROP_FLAT = 1.15                  # the teardrops' flat, from the axis (the tub prints face down: they point -Z)
# The side gate (SPEC2 rev 3; crank.gate, the same part in both sizes and all four builds: GATE_SLOT, GATE and the gate's
# code are the 4.26 project's, word for word). A slot in the -X wall, open to the rim, that a printed T drops into from
# the open back of the face-down tub. The mouth in the outside face takes the gate's web (0.10 a side: it locates the
# gate); behind the two lips (the wall beside the mouth, `lip` thick) the flange cavity takes its flange (0.15 a side and
# behind), with full R `end_r` round ends (the lips' root relief: no fillets, so nothing is left in the corners for the
# flange's to hit). The floor is the gate's 45-degree bevel plane, flat at floor_z (0.30 past the rod's axis) behind the
# flange; the rod's 2.10 teardrop runs through it, its edges chamfered channel_chamfer where it breaks the floor (X >
# -3.09), and the sliver left between the cavity and the ring (X -2.19..WALL_X0, 0.78) keeps the teardrop with a
# sliver_lead lead-in on its -X face. The gate's inner face (ROD_STOP_X0) is the rod's stop; its bevel cams the rod's
# square tail the last 1.75 mm home as it goes in, and the lid's rim closes 0.20 over its top. Every number is from X0
# (-4.09 in both sizes), the rim and the rod's axis. The rod's axial load goes rod -> flat -> flange -> lips: all tub.
GATE_SLOT = dict(lip=1.10, mouth=(-3.85, -1.15), cavity=(-4.35, -0.65), end_r=0.40, floor_z=0.90,
                 channel_chamfer=0.30, sliver_lead=0.50)
# the gate: web in the mouth, flange behind the lips; inner face flat at X0 + web + flange from the top (top_clr under
# the rim: 0.20, so the lid clears it by >= 0.05 wherever it sits on its floor, even printed on the floor's stairs) down
# to floor_z, then the 45-degree bevel to a sharp tip at the outer face. Chamfers: the web's outer top edge
# (top_chamfer, ending level with the tub's seam chamfer, z -3.35), the flange's bed-side vertical edges (bed_chamfer,
# elephant foot), a bearing_break on the two that bear on the lips. Pull hole (pull_d x pull_depth at pull_z, the web's
# centre): a straightened paperclip lifts it out.
GATE = dict(web=GATE_SLOT['lip'], flange=0.65, web_y=(-3.75, -1.25), flange_y=(-4.20, -0.80), top_clr=0.20, top_chamfer=0.20,
            bed_chamfer=0.40, bearing_break=0.05, pull_d=1.30, pull_depth=1.0, pull_z=-2.00)
ROD_STOP_X0 = X0 + GATE['web'] + GATE['flange']            # -2.34: the gate's inner face, the rod's left stop
ROD_SPAN = (ROD_STOP_X0, WALL_X1)
# In X: the case side, the lips' inner face and the cavity's +X wall (the round ends' diameter behind the lips): X0,
# -2.99, -2.19. The sliver behind the cavity is 0.78 (WALL_X0).
GATE_SLOT_X = (X0, X0 + GATE_SLOT['lip'], X0 + GATE_SLOT['lip'] + 2 * GATE_SLOT['end_r'])
assert abs(WALL_X0 - GATE_SLOT_X[2] - 0.78) < 1e-9 and abs(GATE_SLOT_X[2] - ROD_STOP_X0 - 0.15) < 1e-9
# The rail hangs from the skin in front of the board's edge. Ring segments (closed bores) beside the cranks, open seats
# under the switches: the TS365's housing comes within 0.065 of the bore there, so the seat's mouth faces it and the pin
# load (211 deg) goes into its solid wall. Each crank cheek runs in a slot with rail on both sides (0.15 gaps).
RAIL_Y = (-4.225, -0.45)                  # -Y face: the keys' +Y guide; +Y face 0.25 off a board edge 0.2 out
RING_BOTTOM = -1.20                       # ring blocks, 0.4 x 45 chamfers on their lower corners
RAIL_CHAMFER = 0.4
RAIL_X1 = 56.3                            # the right ring's end: X 56.3-61.41 stays open to push the rod out
SLOT = (3.60, 5.40)                       # |dx| of the cheek slots, open toward -Z
SLOT_ROOF = LIP                           # 3.47, the skin's underside (2026-10-12; was 3.15, under 0.32 of rail): Ian
                                          # felt a friction point turning a crank by hand in the open tub. Each
                                          # cheek's top corner (its z 2.5 flat on the second trim, r 2.42 from the
                                          # rod, 2.48 as sliced) passes under this roof at +40 in the free swing; 3.15
                                          # printed at 3.07 and, face down with the play and growth, the corner
                                          # scraped it. The slot now runs up to the skin (tub.rail: no rail over it),
                                          # a floor in the face-down print, on the layer grid in both builds:
                                          # crank_checks.free_swing
WEB = dict(z0=1.0, x_ends=(4.8, 55.2))    # rail to chin wall, from the skin down to z0 (between the cranks' slots)
KEY_OPENING = dict(half=5.30, y=(-7.95, RAIL_Y[0]), r=0.5)   # its +Y edge flush with the rail face; its chin edge a
                                          # 0.25 ledge over the chin wall (BOT_IN): the light strip's hooks stop under it
CHIN_LEAD_IN = 0.5                        # 45-degree chamfer on the chin wall's lower inner edge (the key's chin side
                                          # goes in past it; the hook slots cut through it)
# The crank (identical in both builds; crank-M and crank-T differ only in the nose). Profiles at theta 0 (the crank-M
# nose touching the MJTP's nominal face); theta > 0 is pressed.
CRANK_PAD_END = -7.70                     # the whole crank is clipped here: its bed face (printed on the pad end)
CRANK_CROWN = ((-7.45, -0.80), 0.6)       # the pad's crown (centre, R): its top at -0.20 carries the key's pusher
CRANK_NOSE_R = 1.0
CRANK_NOSE_C = {'M': (-2.92, -2.35), 'T': (-3.20, -2.35)}   # crank-M: MJTP1117 (face -1.92); crank-T: TS365ZJ (tip -2.2)
CRANK_HALF = 5.25                         # crossbar, pad and cheeks' outer faces
CRANK_CHEEK = (3.75, 5.25)                # |dx|
CRANK_LEG_HALF = 1.30                     # the leg and nose; the belly fills 1.30..5.25 under the crossbar
CRANK_CHEEK_TRIM_Y = -0.70                # cheeks clear a board edge at -0.4 by 0.07; on the layer grid (0.2 layers from
                                          # the pad end at -7.70), where -0.75 printed too (2026-09-30)
# and a second trim across the cheek's +Y top corner: n . ((y, z) - ROD_AXIS) <= d, so a crank hanging free in the
# face-down tub (about -17.5 degrees, pad toward the face) keeps its cheeks at y <= -0.45, off a board edge at -0.4
# (the bore's wall is untouched: 0.82 to this face)
CRANK_CHEEK_TRIM2 = ((0.954, 0.301), 2.0)
# The crossbar and belly (2026-09-27, torsion fix): the crossbar's underside runs 45 degrees from the bed face's lower
# corner down to CRANK_UNDERSIDE, flat, then 45 degrees up the belly's underside from its lower corner; every
# re-entrant corner of the section is rounded (CRANK_FILLET: top = the crossbar's +Y face on the belly's top at
# (-4.65, -1.3); under = the underside's flat on the belly's 45-degree underside (and the leg's); crown = the crown on
# the crossbar's top). Torsion + shear at a 20 N press 3.45 + 3.47 = 6.9 MPa (<= 8; mechanics.crank_stress, Prandtl's
# stress function on body_profile)
CRANK_UNDERSIDE = -2.20
CRANK_BELLY_FOOT = ((-2.92, -3.05), (-3.22, -3.35))           # the belly's 0.3 chamfer at its lower +Y corner
CRANK_TOP = -0.60                                              # the crossbar's top, and its +Y face at -4.65 down to
CRANK_BELLY_TOP = (-4.65, -2.92, -1.30)                        # the belly's top (y0, y1, z) under the rail
CRANK_FILLET = dict(top=0.4, under=0.4, crown=0.3)
CRANK_BORE = dict(d=2.0, ream=1.9, lead=0.3, flat=1.15)     # round in the ring, a teardrop pointing +Y in the lip
                                                             # (the crank prints pad end down)
# crank cheek, test 1 (2026-09-29): closed ring outboard of x0; today's open C only inboard, beside the TS365
# housing (its corner is 1.04 from the rod axis, inside any wall round the bore). x0 = housing 3.65 + float 0.15 + 0.25.
# The ring thicker where it holds the rod (Ian, 2026-09-30; the ring study's v2d): a round bore, its top at -1.50 (a
# layer boundary: a 0.80 cap of 4 layers under the -0.70 face), and the fill carried forward under the rod to the MJTP
# housing's frontier (ring_mj >= 0.03 to the 3.68's STEP and the 4.26's box). Least wall 0.57 -> 0.75.
CRANK_CHEEK_RING = dict(x0=4.05, top_r=2.20, roof_c=5.575,
                        fill=((-3.40, 0.0), (-1.50, 0.0), (-1.30, -0.70), (-1.70, -2.20), (-3.40, -2.20)))
# Rev L key fit (2026-09-29, Ian's first print: the keys jammed): the key's +Y face rides the rail with no play, so all
# FDM error in Y lands on the chin side. As printed, holes come out 0.10-0.20 small and parts 0.05-0.15 large (best /
# typical / worst below; flare: the key's first layer at elephant-foot compensation 0, per side). mechanics.key_fit
# stacks them on every key-to-tub pair; slice_check.key_fit reads the clearances back from the G-code.
KEY_FDM = dict(hole=(0.10, 0.15, 0.20), part=(0.05, 0.10, 0.15), flare=(0.10, 0.15, 0.30))
KEY_CHIN_GAP = 0.40      # cap chin face to the opening's chin edge, the pusher's chin end to the chin wall, and each
                         # hook's tip to its slot's back: 0.05 at KEY_FDM's worst (hole + part 0.35), the key on the rail
KEY_SIDE_GAP = 0.30      # cap to the opening's sides, per side (0.40 to the webs). The 50-layer key (2026-10-03, Ian;
                         # keyfit proposal 1): on its -X end the key's X is a stack of 0.20 layers, so 10.00 is 50
                         # whole layers. At 0.35 the 9.90 key printed 49 layers, 9.80 (Orca drops the 50th): 0.40 a
                         # side as sliced. Now 0.299 a side as sliced, 0.199 at KEY_FDM's worst
KEY_BED_END = (0.30, 0.10)     # the key prints on its -X end (test 1, 2026-09-29): its outline there comes in 0.30 in
                               # the first layer (x -h..-h+0.2) and 0.10 in the second, a 0.4 x 45 chamfer all round
                               # at the layers' mid-planes, so its elephant foot stays inside the cap's outline
# The key. Its +Y face rides the rail face; it rests on its crank and the crank on the switch (its rest height is the
# switch's), and two rigid hooks bound it outward (KEY_HOOK, below). Nothing preloads the chain (a Z spring has no room:
# BUTTONS.md; keystab RECOMMENDATION section 1).
KEY_HALF = round(KEY_OPENING['half'] - KEY_SIDE_GAP, 3)          # 5.00: 50 layers (4.95 to 2026-10-03; Rev L: 5.10)
KEY_Y = (round(KEY_OPENING['y'][0] + KEY_CHIN_GAP, 3), RAIL_Y[0])   # cap: -7.55 (was -7.80) .. -4.225
KEY_TOP_OVER_FACE = 1.50                  # cap top at rest over the build's face: the keys are tub-specific
KEY_CAP_Z0 = 1.60                         # the cap block above, the pusher below
KEY_PUSHER = dict(y=(round(BOT_IN + KEY_CHIN_GAP, 3), -6.55), z0=-0.20, stop_z1=0.55)
                                          # y -7.80..-6.55: its chin end below stop_z1 is the chin-side stop, 0.40 off
                                          # the chin wall (the old foot, -8.05..-7.90, 0.15 off it, is gone). Above
                                          # stop_z1 the key's chin side is the cap's chin face (KEY_Y[0]), all the way up
KEY_BODY = dict(half=3.30, z0=0.40)       # under the cap between the crank's cheeks: 0.45 to their inner faces (3.75),
                                          # over the key's 0.30 of X play, so the opening, not a cheek, stops a key
                                          # pushed sideways (was 3.45: 0.30, under the play; 2026-09-29). On the
                                          # 50-layer key its +-3.30 faces lie on layer mid-planes: Orca prints them
                                          # at +-3.40 (the worse case, which mechanics.key_fit's E takes)
KEY_CHEEK_ZONE = dict(y=-6.25, z0=2.70)   # over the cheeks (|dx| 3.30..5.00) the cap is cut up to z0 for y > y
KEY_CAP_CHAMFER = 0.4                     # all four top edges (test 1: the chin edge too, now the cap is closed there)
KEY_CORNER_R = (1.0, 0.3)                 # the cap's vertical corners (+Y, chin side) inside the opening's R0.5 corners.
                                          # +Y R1.0 since 2026-10-03 (R0.5 before): the key's X is a stack of layers,
                                          # each its section at the layer's mid-plane carried 0.10 past it, so an R0.5
                                          # (the opening's own) left the end layers 0.20 off the opening's arcs as
                                          # sliced, against 0.30 on the flat sides; R1.0 keeps them 0.46 off.
                                          # At the bed end (-X) the arc starts with its 45-degree tangent (keys._plan)
# Hook keys (test 2, 2026-09-30, Ian: "build the hook keys"; keystab RECOMMENDATION, concept C4-A). The drag leaf, its
# slit, its roof slot and its bump are gone: nothing on the key rubs. Each key has two rigid hooks on its chin side, one
# at each X end, and the tub two slots per key in the chin wall's inner face, open to the rim, that the hooks run in.
# The key still rests on its crank and the crank on the switch (no free travel face-up); the hooks only bound it: face
# down it drops KEY_W_OUT outward onto them, both hooks flat under the slot's roof, level and 2.5 proud. They cannot
# come out through the face: the key's +Y face rides the rail, so a hook can only move toward the chin, deeper under
# the roof. The key still prints on its -X end: the -X hook starts on the bed, the +X hook's -X face is a 45-degree lead
# (KEY_HOOK_LEAD in plan) so it builds up with no overhang.
KEY_W_OUT = 1.00          # hook top to the roof at rest: the face-down drop. It must clear the switch's rest scatter at
                          # the key (the crank's worst rest, board +-0.2 and TS365 tip +-0.2: 0.696; + the chain's print
                          # 0.14 + KEY_STOP_MARGIN 0.15: 0.986; mechanics.key_hooks), or the stop would press a plunger
KEY_CHAIN_PRINT = 0.14    # the key-crank chain's own print scatter at the key, for that budget (keystab C1's number)
KEY_STOP_MARGIN = 0.15    # and the stop's: its own print 0.10 and 0.05 (keystab C4, the stop window)
# the slots, |dx| from the key centre, the outer side flush with the web's face (SLOT[1], the X guide plane: the spec's
# 5.30, the opening's side, would leave a 0.10 step to the web), the inner side past the +X hook's lead where it crosses
# the chin wall's face with the key at its chin stop (tip on the back: 3.20 / 3.30), less the key's X play (0.35 when it
# was set; KEY_SIDE_GAP 0.30 since 2026-10-03) and 0.20 of print (the spec's 3.20 lets a key pushed to its chin stop and
# 0.35 sideways run its lead into the wall).
# back: the slot's depth, per build (x3std's roof sits in the chin wall's thin part, so its back stays at the 0.45 wall
# the flat chin leaves; x3ls: the spec's -8.85, 0.55 of wall); wall: the least chin wall left behind it, in every
# layer from the rim to the roof; above: the least material over the roof at the back.
# relief: the tub has no seam chamfer on the chin over the key row, from `relief` before the first slot to `relief`
# past the last (tub.rim_chamfer; hverify1 F1, 2026-09-30). With it the wall behind every slot thinned in the rim's
# last layers to 0.37 / 0.17 (x3std) and 0.27 (x3ls), which Orca does not print: 8 slits 2.7 wide in the seam's V, open
# into the slots, above the lid's rim. Without it the wall is the flat chin's 0.45 / 0.55 up to the rim. One relief,
# not one per slot: two keys' slots are 1.2 apart. 0.5 past a slot's end the step in the outer face lies where the chin
# is whole (at the slot's end it would leave a 0.17 / 0.27 neck between the slot's corner and the chamfered face).
KEY_SLOT = dict(dx=(2.65, SLOT[1]), back={'standard': -8.95, 'light-strip': -8.85}[VARIANT], wall=0.45, relief=0.50,
                above=0.50)
# hooks: |dx| 3.95-5.00 (centres 8.95 apart, to the cap's ends), h tall, from the cap's chin face to `tip`. The tip is
# KEY_CHIN_GAP (0.40) off the slot's back, as the pusher is off the chin wall: all FDM error in Y lands on the chin side
# (the key rides the rail), and 0.40 keeps a rigid pair >= +0.05 at KEY_FDM's worst (the spec's x3std tip -8.60, 0.35
# off its -8.95 back, would print 0.00). Bearing under the roof: the tip to the chin wall's face (x3std, 0.35) or to
# the opening's chin edge (x3ls, the roof is the skin's underside: 0.50).
KEY_HOOK = dict(dx=(3.95, KEY_HALF), h=0.80, tip=round(KEY_SLOT['back'] + KEY_CHIN_GAP, 3))   # tip -8.55 / -8.45
KEY_HOOK_LEAD = round(KEY_Y[0] - KEY_HOOK['tip'], 3)     # 1.00 / 0.90: the +X hook's -X face, 45 degrees in plan
# The key's root (as the 4.26's): over its first KEY_ROOT from the -X end (the bed) its chin side is solid out to the
# hooks' tip, from the pusher's underside up to the hooks' top, so the bed end's chamfer (KEY_BED_END: 0.30 in on layer
# 1) leaves no thin stub there. Without it layer 1 had only a 0.25 stub of the -X hook, and layer 2 printed the hook
# 0.98 (x3std) / 1.10 (x3ls) past layer 1 with nothing under it (slice_check.islands' reach). It lies in the -X slot,
# 0.40 off its back, its top the -X hook's.
KEY_ROOT = 0.60


def chin_outer_y(z):
    """The chin's outer face (y) at height z over the key row, as body.outer_body draws it: Y0, the FRONT_EDGE_R round
    up to the face (no SEAM_CHAMFER at the rim there: KEY_SLOT relief)."""
    import math
    zc = Z_FRONT - FRONT_EDGE_R
    if z > zc:
        return Y0 + FRONT_EDGE_R - math.sqrt(max(0.0, FRONT_EDGE_R ** 2 - (z - zc) ** 2))
    return Y0


def slot_roof():
    """The slot's roof (RECOMMENDATION 6: the highest z where the wall behind it stays >= KEY_SLOT['wall']), on the
    layers the face-down tub prints: a roof at zr opens every layer whose mid-plane (Z_FRONT - LAYER (k - 1/2)) is below
    it, so the wall is held at those planes. The skin's underside (LIP) unless the top open layer would leave less wall;
    then down a layer at a time. x3std: 2.27 (the spec's 2.40 is off the layer grid, so it would print at 2.47 with
    0.44 of wall: its chin's R1.8 round starts at 2.27); x3ls: LIP, 3.47."""
    import math
    zr = LIP
    while True:
        k = math.floor((Z_FRONT - zr) / LAYER + 0.5 + 1e-9) + 1          # the first layer whose mid-plane is below zr
        zm = Z_FRONT - LAYER * (k - 0.5)
        if KEY_SLOT['back'] - chin_outer_y(zm) >= KEY_SLOT['wall'] - 1e-9:
            return round(zr, 4)
        zr = round(Z_FRONT - LAYER * k, 4)


KEY_SLOT_ROOF = slot_roof()                                            # 2.27 / 3.47
KEY_HOOK_Z = (round(KEY_SLOT_ROOF - KEY_W_OUT - KEY_HOOK['h'], 3), round(KEY_SLOT_ROOF - KEY_W_OUT, 3))
                                          # at rest: x3std 0.47-1.27 (spec 0.60-1.40), x3ls 1.67-2.47

# ---- side keys (part of the lid: sidekeys.py) ---------------------------------------------
# Rev J/K's keys, unchanged: the lid's wall is 3.08 tall here (Rev K 2.95), so the bar is 0.13 taller.
TAB_GAP_SIDE = {+1: 0.15, -1: 0.25}   # nub to plunger at rest. The board's only X datums on the lid (the H5 pin
                                      # and J1's lid block) are on its +X half, so a press on a +X key lets it back
                                      # off 0.10 further than a -X key (test 1, 2026-09-29: +X keys did not click)
TAB_Z = (Z_BACK, 0.6)
TAB_BAR_TOP = SEAM - 0.15
TAB_BLOCK_MARGIN = 0.3
TAB_SLOT_CLR = 0.2
TAB_END_CLR = 0.3
TAB_END_FOOT = 0.4
TAB_ROOT_CLR = 0.2
TAB_FOOT_GAP = (0.75, 1.20)
TAB_PAD_PROUD = 1.5
TAB_PAD_FACE = (-3.4, -1.0)
TAB_PAD_LEN = 10.0
TAB_PAD_LENS = {'SW7': 8.0}               # power: a slightly smaller pad is harder to hit by accident
TAB_FREE_BEYOND = 0.2
# Roots (Y) where each flexure starts. SW1 and SW4 are Rev K's. SW7 (power, UP2) mirrors SW4: its Rev K root
# at 91.0 would now sit in the top-left corner's round.
TAB_ROOTS = {'SW1': 49.5, 'SW4': 87.3, 'SW7': 87.3}
TAB_FLEX_T = 0.74                         # x3: the lid's wall is 4.0 tall (Rev K 2.95), so the bar is thinner to keep the feel;
                                          # 2026-10-12, LID_DROP: its bar is 1.0 taller (4.335), so 0.85 -> 0.74 keeps k
                                          # at 0.86 / 0.90 / 0.88 N/mm (was 0.86 / 0.89 / 0.88; mechanics.side_keys)
# 2026-10-12, Ian printed that lid: "it really messed up around the side switches". As sliced with the plate file's
# CC2 presets (classic walls, elephant-foot compensation 0.1) no side key had a first layer: the foot's inner edge
# stood TAB_FLEX_T + TAB_FOOT = 1.79 in from the case face, where the 2.0 back round leaves a 0.31 strip on the bed
# (0.42 with the 0.85 flexure before LID_DROP), and Orca printed nothing there. Each key started at z 0.4, 0.2 over
# the bed, and from its hinge notch to its free end its first layers were tied to nothing. The 4.26's foot stands
# 2.0 in (0.95 + 1.05), a 0.52 strip, which prints; TAB_FOOT_BED puts the 3.68's there. The lid's cut behind the foot
# (TAB_FOOT_GAP) moves with it. The hinge notch keeps its height (TAB_NOTCH, until now TAB_FOOT): with its roof in the
# layer 1.2-1.4 Orca also laid a loose patch of support one layer over the grid, beside each key's root. The foot now
# starts where the hinge ends (it would stand 0.21 over the notch's roof), and the deeper foot stiffens the key past
# the hinge, so the hinge is 0.4 longer: 0.84 / 0.88 / 0.87 N/mm and 2.20 / 2.21 / 2.29 N (were 0.86 / 0.90 / 0.88 and
# 2.20 / 2.22 / 2.30; mechanics.side_keys reads its sections 0.25 apart, so 3.2-3.35 all read 0.88 / 0.92 / 0.91).
TAB_FOOT_BED = 2.0                        # the foot's inner edge on the bed, in from the case face (the 4.26's)
TAB_FOOT = round(TAB_FOOT_BED - TAB_FLEX_T, 3)   # 1.26 (was 1.05): the foot's depth past the flexure
TAB_NOTCH = 1.05                          # the hinge notch's height (the 4.26's): its roof prints in the layer 1.0-1.2
TAB_HINGE = 3.4                           # was 3.0
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
TAB_ROOT_FULL, TAB_ROOT_TAPER = 0.2, 0.5
NUB = dict(w=6.0, z=(-3.5, -1.20), lead=0.3)
NUB_W = {'SW7': 5.0}
# 2026-10-13 (Ian: SW7 prints badly at the nub or the pad). TAB_RELIEF_MAX relieves the key's inner face from the
# plunger toward the free end, but the nub's base stayed at the full face, so for its last 2.0 mm SW7's nub stood free
# of the relieved face across a slit 0.07-0.19 wide. As sliced with the CC2 presets that left a hole in the nub's
# free-end corner on the three layers under its tip (0.19 / 0.37 / 0.56 mm2 at bed z 4.0 / 4.2 / 4.4; ElegooSlicer
# and Orca alike) and put the outer wall's seam on the nub (22 loop starts, 44 re-primes; SW4 8 / 26). SW1 and SW4
# fill that corner with a 1.1 mm gap fill (their relief runs over 5.2 mm, SW7's over 4.2: its 8 mm pad makes it 1.0
# shorter). A NUB_BOND key's nub reaches 0.05 into the relieved face at its free-end end (sidekeys.nub), so it stays
# fused to the key over its whole width: +0.79 mm3 in the slit. Pressing is unchanged (the added material lies past
# the plunger and outside the full face). SW1/SW4 keep the slit: bonded, the core of their block turns to sparse
# infill at z 5.2-6.0.
NUB_BOND = ('SW7',)
NUB_WINDOW = dict(clr=0.5, top_clr=0.25)
TAB_RELIEF_MAX = 0.40

# ---- USB-C (Rev I-K; the port opened a layer toward the board 2026-10-22, below) --------
USB_PLUG_SPARE = 0.45
OVERMOLD = (12.35, 6.5)
OVERMOLD_CLR = 0.25
USB_RECESS = (11.5, 6.0)
USB_RECESS_R = 1.5
USB_RECESS_LEAD = 0.8
USB_FLOOR = dict(t=0.5, hole=0.10, notch_clr=0.1, lid_gap=0.055)
# 2026-10-22, the port fits board Rev 1.0 and Rev 1.02. Rev 1.02's J1 (the SMD USB4105) sits 0.14 mm nearer the board
# than Rev 1.0's through-hole USB4085 (the opening's centre z -1.815, was -1.955), and KiCad seats both about 0.085
# deeper than a real board rests, so a plug in a Rev 1.02 socket sat 0.015 from the hole's board-side edge as printed
# (-0.063 at the corners; interference once the seat is counted). The tub prints face down and the lid back down, so a
# plane counts in whole layers from the bed: the hole's board-side edge and the recess's move onto layer lines from the
# tub's face (the edge at z -0.575 printed at -0.53; the recess's 1.045 at 1.00), and the lid's port block, the hole's
# far edge, which stood at -3.335 on a layer's mid-plane (5.100 over the lid's back; it printed one layer high, 0.2),
# drops one layer onto a line from the lid's back. The hole keeps its width (8.54) and its corner radius (1.1). Both
# are drawn for the frozen Rev 1.0 board copy (assert in tub.usb_features); a regenerated case redoes them.
# slice_check reads the printed edges back against both sockets (asprinted.usb_fit; FAIL under 0.1 on any side).
USB_HOLE_TOP = -0.33                      # the hole's board-side edge (z): 4.47 + 0.33 = 4.80 (standard), 5.27 + 0.33 = 5.60
USB_RECESS_TOP = 1.27                     # the recess's board-side edge (z): 4.47 - 1.27 = 3.2 (standard), 5.27 - 1.27 = 4.0
J1_REV10 = dict(yc=41.30, zc=-1.955, mouth_x=61.195)   # the frozen Rev 1.0 board copy's J1 (tub.usb_features asserts it)
J1_REV102_DZ = 0.14                       # Rev 1.02's USB4105 opening sits this much nearer the board (z up): -1.815
J1_SEAT_DZ = 0.085                        # KiCad seats parts this far behind where a real board's rear face rests (both J1s)
USB_PLUG = (8.25, 2.40, 1.0)              # the nominal USB-C plug shell: width, height and its least corner radius
USB_FIT_MIN = 0.10                        # the plug's least clearance to the hole's printed edges, each flat, both boards
USB_BLOCK_DROP = 0.10                     # the lid's port block top: -3.335 -> -3.435, 5.0 over the lid's back (Z_BACK -8.435)

# ---- fasteners ---------------------------------------------------------------------------
# Four M2 x 8 socket head caps (ISO 4762, Ian's; a pan head, ISO 7045, also fits; three until 2026-10-13), thread-forming
# into printed pilots, from the back. Never M2 x 10: it would come out of the face. Each goes through a post in the lid
# into a pilot in the tub that ends PILOT_CAP under x3's face (Z_FRONT_BASE: the standard face is 0.4 over it, the light
# strip's 1.2):
#   bottom pair  in the chin's two bottom corners, below the rod (CORNER_SCREWS; Ian, 2026-10-13). Until then they went
#                through the board's H3/H4 holes into bosses in front of it, with only 2.0 mm of pilot (the board's front
#                to the pilot's end, as printed 1.67..3.67): an M2 x 8 ended at the pilot's end with about 1.2 mm of full
#                thread, and they never bit (Ian, 2026-10-12); no length does better there. In the corners the tub is
#                solid from the parting plane to the pilot's end (tub.corner_blocks): pressed home, 7.2 mm of screw in its
#                pilot, the tip 0.2 short of its end and 1.0 from the standard face (1.8 on the light strip). The seat is
#                18 layers up (Z -4.635). H3/H4 keep the lid's posts, now with a pin into the board's hole as H5's (the
#                board's X/Y stop at its bottom edge, beside the bottom keys), and the tub's bosses, without a pilot.
#   top          the top-right corner, beside the panel (whose path ends at X 57.62) and above the board's cut edge, its
#                boss merged into the right wall: 6.2 mm in its pilot. Unchanged.
#   top-left     the corner that had none (TOP_LEFT_SCREW; Ian, 2026-10-13; as the back is held, the top-right, above the
#                power key), built as the top one: a corner block in the tub (tub.top_left_boss), a 5.0 post in the lid
#                with the top screw's 2.6 counterbore and seat. At this corner the back's edge round leaves no room: its
#                counterbore opens a notch about 0.4 high in the round on the first two layers, as the 4.26's top screw
#                does (Ian: OK). Moving it in brings the pilot onto the panel's pocket: the tub's wall there is 0.70 (CAD;
#                0.64 as sliced), the thinnest of any screw. The midplate is notched round its block.
# Each seat is on the layer grid from the back face (the bed). Each counterbore's ceiling prints with no support: the
# two layers over the seat step from a slot to a square (lid.stepped_bridge; M2_CB_SLOT is the slot's direction).
# slice_check reads every screw back from the G-code (asprinted.screw): >= 3.0 in the pilot (also with the lid 0.3 open),
# the tip short of the pilot's end and >= 0.8 from the face, the lid at its as-printed home (LID_HOME_DZ), and neither a
# socket head's top nor a pan head's proud of the back (as sliced: 1.6 / 2.0 below it in the corners, 0.6 / 1.0 at the
# top two).
M2_PILOT = 1.7
M2_CLEAR = 2.4
M2_HEAD_D, M2_HEAD_H = 4.2, 1.7
M2_HEAD_CB = 4.2                          # counterbore for the head (socket head dk 3.8, pan head dk 4.0 max)
SCREW_L = 8.0
CORNER_SCREWS = ((2.0, -5.25), (58.0, -5.25))   # mirror images about the case's centre line (X 30): in the chin's
                                          # corners between the side wall and the end web (X 4.8 / 55.2), between the
                                          # chin wall and the rod. 8.25 below and 1.75 outboard of H3 / H4. Y -5.25, not
                                          # the study's -5.05: between the pilot and the block's face under the rod
                                          # (CORNER_BLOCK_Y1; at the right the push-out path, at the left below the ring)
                                          # -5.05 left 0.45 of plastic, one printed line, for the thread to form in;
                                          # -5.25 leaves 0.65 (the left one 0.85 to the rod's bore in the ring), while
                                          # the counterbore's first layer still closes 0.67 from the back's edge (0.87)
TOP_SCREW = (59.75, 90.6)
TOP_LEFT_SCREW = (-0.2, 94.95)            # 0.70 from its pilot to the max panel's pocket corner, about 2.1 to the outside
SCREWS = {'bottom-left': CORNER_SCREWS[0], 'bottom-right': CORNER_SCREWS[1], 'top': TOP_SCREW, 'top-left': TOP_LEFT_SCREW}
M2_CB_DEPTH = {'corner': round(2.6 + LID_DROP, 3), 'top': round(1.6 + LID_DROP, 3)}   # 3.8 / 2.8 since 2026-10-19: the
                                          # seats stay at Z -4.635 (19 layers) / -5.635 (14); the
                                          # top-left screw takes the top one's
M2_CB_SLOT = {'corner': 'x', 'top': 'x'}  # the first bridge layer's slot runs along this axis (a round counterbore:
                                          # either way, its bridges are <= 3.45 long)
PILOT_CAP = 0.4                           # solid skin left in front of a pilot's end
BOSS_D = 4.4                              # H3/H4 bosses, flattened on the screen side (POCKET_Y0); their faces stand H34_FLOAT
                                          # clear of the board (until 2026-10-20 the board's front stopped on them)
TOP_BOSS_D = 4.0                          # the top and top-left screws' bosses
# The corner blocks (tub.corner_blocks): each fills its chin corner from the side wall to the end web (WEB x_ends) and
# from the chin wall to CORNER_BLOCK_Y1, 0.2 under the rod's hole (its edge at -3.55) and 0.375 under the bare rod at
# the right, where X 56.3..61.41 stays open to push the rod out (README, Bottom keys: taking it apart), from the
# parting plane to the skin. In the lid each corner screw has a CORNER_POST_D post, D-shaped into the bottom wall.
CORNER_BLOCK_Y1 = round(ROD_AXIS[0] - ROD_HOLE_D / 2 - 0.2, 3)   # -3.75
CORNER_POST_D = 6.0
H34_PIN = dict(d=1.9, h=0.8, cone=(0.95, 0.6, 0.4))   # the board's X/Y stop on the H3/H4 posts: H5's pin (2.2 hole)
SNAP_POSTS = ('H2', 'H6')                 # H1 went with the board's upper extension
BOARD_SNAP = dict(d=1.90, crest=2.44, catch=-0.10, lead_deg=30.0, face_deg=45.0, slot=0.60, tip=-0.95)
                                          # x3: crest 2.44 (Rev K 2.50): the fingers are 3.55 long here (Rev K 3.95)
BOARD_SNAP_BORE = (3.0, -1.40)
BOARD_POST_D = {'H5': 4.3, 'H6': 5.0}   # H2: see SUPPORT_POSTS

# ---- tub / lid joint (joint.py), Rev G-K ---------------------------------------------------
# The lid's floor is deeper than Rev K's (-6.435 v -5.5; -7.435 since LID_DROP, the tongue unchanged), so the tongue
# is longer: 1.8 engaged clear of the switches, 0.85 alongside them (Rev K 1.4 and 0.45).
JOINT = dict(t=SLIVER, h=1.8, clr=0.15, end_clr=0.3, floor_clr=0.15, lead=0.2, mouth=0.3,
             lip=0.85, min_run=4.0)
#   right  stops either side of the lid's USB block, and before the top screw's post
#   top    corner to corner, but for the top screw's post
#   left / top (2026-10-13; were to 93.2 and from 1.3) stop JOINT end_clr short of the top-left screw's post and the 6.0
#          round under its seat (lid.py), which stand where the two tongues' ends were
TONGUE_RUNS = {'left': [(-5.2, 91.9)], 'right': [(-5.2, 34.25), (48.35, 87.4)], 'top': [(2.8, 56.6)]}
# The lid's home as printed (2026-10-13). The lid prints back face down and the tub face down, so the parting plane is
# SEAM - Z_BACK over the lid's bed and Z_FRONT - SEAM over the tub's, and neither is whole layers (printed_top): the
# lid's rim prints to Z -3.835 and the tub's to -3.73, so pressed home the lid sits LID_HOME_DZ forward of CAD. The
# board's chain says the same: the lid's posts print to -0.035 and the tub's bosses' faces to 1.67, with a 1.6 board
# between. (The 4.26's lid sits 0.10 behind CAD instead.) slice_check reads it back (asprinted.home).
LID_HOME_DZ = round((Z_FRONT - printed_top(Z_FRONT - SEAM)) - (Z_BACK + printed_top(SEAM - Z_BACK)), 3)   # 0.105
# 2026-10-20, the long sides (Ian chose the invisible change first): at H3/H4 the board was clamped line to line
# (tub bosses 1.67, lid posts 0.07 at home: 1.600 for a 1.600 board), 8.25 above the bottom screws with no screw in it,
# so any extra board thickness levered the lid open along its long sides. The bosses' faces now stand H34_FLOAT (two
# whole layers, counted from the tub's bed) lower: 0.40 of room as printed, 0.24 with a board 0.16 thicker
# (asprinted.board_room reads it back; FAIL under H34_ROOM_MIN with that board). The board does not move: it sits on
# the lid's posts under the midplate's springs, and their 1.9 pins in its holes keep its X/Y. The face is drawn on the
# layer line (printed_top of the old one, less H34_FLOAT), not on a mid-plane.
H34_FLOAT = 0.4
H34_FACE = round(Z_FRONT - (printed_top(Z_FRONT - PCB_FRONT) - H34_FLOAT), 3)      # 2.07 in both builds (was 1.6, printed 1.67)
H34_BOARD_PLUS = 0.16                     # the board's thickness tolerance (+-10 %)
H34_ROOM_MIN = 0.20                       # least room, board to boss, with that board at the as-printed home
assert abs((Z_FRONT - H34_FACE) / LAYER - round((Z_FRONT - H34_FACE) / LAYER)) < 1e-9, 'H34_FACE: whole layers from the bed'
# Latch arms stand on the lid floor (on a pedestal since LID_DROP) and hook pockets above the side keys' slots (Rev I).
# x3: the right wall's top latch (Rev K 82.3) gives way to a detent strip; the top screw is 8 mm above it.
# Two new latches on the top wall hold the top edge either side of the battery's lead.
SNAPS = {'left': [12.0, 26.0, 39.5, 54.0, 68.5, 83.0], 'right': [12.0, 24.0, 54.7, 68.5],
         'top': [8.0, 47.0]}
# 2026-10-19, Ian: thicker arms. 1.2 / 0.85 (x3round, bow.md) met the board's edge (lid_close: 6 of 12 arms, 1.6 mm
# before home): today's bent arm clears it by 0.16. So the arm is thicker only below the board: 1.3 at its root,
# straight to today's section (0.79) at Z -0.5 ('mid'), today's taper above, so from the board up (Z 0 to its top)
# it is today's arm. Pull-off 4.8 -> 8.0 N an arm, push-on 3.3 -> 5.45 N, root strain 0.90 -> 0.89 %.
SNAP = dict(w=4.5, gap=0.1, barb=0.55, t_root=1.3, t_tip=0.7, mid=(-0.5, 0.79), catch=1.5, flat=0.2, lead_deg=35.0,  # x3: thicker, the arms are 8.6 long
            gap_ends=1.0, pocket=0.6, notch=1.6)
# notch (2026-10-12, was 0.7): the midplate's edge steps back this far where each arm passes it. On the way in the
# barb rides the tongue and the sliver and bends its arm inward by its engagement (0.45; about 0.53 at the arm's
# top) until it drops into its pocket just before home. Bent, a 0.7 notch left the arm's flat top 0.42 over the
# plate's edge: 11 of the 12 arms landed on the plate 0.68 before home (lid_close.latch_arms; the left Y-83 one
# was clear, the light strip's fold relief cuts the plate back there), and the lid could not close. At 1.6 every
# arm clears it all the way home with the plate pushed its EDGE_CLR (0.2) toward the arm, and the notch's edge is
# still 0.74 (left), 1.0 (top) and 2.2 (right) outside the glass, so the plate backs all of it.
LATCH_ROOT_Z = round(LID_FLOOR_IN + 1.0 - 0.1, 3)         # -6.535: the arms stand on a pedestal from the floor
                                          # (1.0, not LID_DROP, since 2026-10-19: the LID_DROP formula would raise the roots)
                                          # (joint.lid_adds), so their root, length and forces are as before LID_DROP
# The barbs' phase (2026-10-13, Ian: take the play out). Each barb's 45-degree catch face was drawn 0.1 under its
# pocket's (SNAP catch 1.5), but both print as 0.2 stairs, and from the lid's as-printed home (LID_HOME_DZ) every barb
# step stood 0.005 inside the pocket step under it: the lid lifted 0.20 before a latch took anything, and the midplate's
# springs pushed it back through that wherever no screw bit (the 4.26's sit on their steps: none). Drawn one layer
# lower, the barb's face meets the pocket's at the as-printed home (0.005 apart) and its steps sit on the pocket's,
# 0.195 deep, as the 4.26's do. In CAD the lid then overlaps the pockets 0.1 at its CAD position, which it never
# reaches (build._designed). The pocket is unchanged (joint.pocket_profile); the arm and its flat are 0.2 lower.
# slice_check reads every latch's dead band from home (asprinted.latch). Only together with the backstops' fix
# (lid.BACKSTOP_TOP): with the backstops still proud, the lid would stop short and the barbs could not drop in.
LATCH_PHASE = -LAYER
# Light strip: the left wall's Y-83 arm (Y 80.75..85.25) stands under the hand-folded pair, and its inner top corner
# met the folded LED D1 when the bar lies against the wall (the stop ribs not printed): with a 0.9 LED or a stack
# 0.045 over nominal, in CAD and as printed, seated and while the lid snaps on. Its inner top corner is chamfered
# (along the top toward the barb, down the inner face): 0.2 x 0.2 still overlapped, 0.45 x 0.45 left 0.0155 as
# printed; 0.5 x 0.5 leaves >= 0.052 as printed and 0.0995 in CAD in all 16 cases (ribs / wall x LED 0.8 / 0.9 x
# stack nominal / +0.045, seated and snapping on), and a 0.2 flat on the arm's 0.7 top. The chamfer is on the arm's
# inner side and ends 0.2 short of the lead-in face and 0.29 above the barb's flat (Z 1.99 vs 1.70), so the barb,
# its catch and its lead-in are x3's (joint.snap_profile). Until 2026-10-12 only this arm had it. The lid is shared, so
# the standard build has it too; it takes 0.56 mm3 off above the barb's catch, so the latch holds as x3's
# (mechanics.latches).
# 2026-10-12: every arm has it (was the Y-83 arm only). With the board pushed toward a wall (its play on the snap
# posts and the midplate's), a bent arm's square top landed on the board's back face 2.48 before home; the chamfer
# meets the board's edge at 45 degrees instead, a cam that pushes it back (lid_close.latch_arms).
SNAP_INNER_CHAMFER = {(w, c): (0.5, 0.5) for w, cs in SNAPS.items() for c in cs}   # (wall, centre): (along the
                                                                                     # top, down the inner face)

# ---- stack detents (Rev K) -------------------------------------------------------------------
MID_DETENT = dict(w=0.7, slot=0.5, len=6.2, bump=0.45, bump_len=1.6, tip_slot=0.5, lead=0.3,
                  spans={'right': [14.9, 80.0], 'left': [14.9, 58.0]},
                  depth=0.35, clr=0.3, z0=1.4, z1=2.95)
# Light-strip variant: the left upper strip moves from 86.0 (its bump at 90.3..91.9, under the strip's fold loop)
# to 58.0, between the latch notches at 51.45..56.55 and 65.95..71.05, clear of the fold zone's relief. The midplate
# is shared, so the standard build's is the same and its tub's left upper pocket moves with it (tub.detent_pockets).

# ---- light strip: the 3.68in bar beside the panel's left edge -------------------------------------------------
# The strip's own geometry (outline, LED and diode positions, hinge, pieces) comes from
# hardware/reference/light-strip/strip-geometry.json (KiCad frame; refs.strip converts it). These are the
# numbers the case is built round. Stack from the surface the bar rests on: 3M 9077 tape 0.05 + PI stiffener
# 0.225 + flex 0.11 = 0.385 to the flex top, + the XL-4008 side-view LED's 0.8 = 1.185 to the LED tops.
# They are set from the light-strip face (Z_FRONT_STRIP), so they read the same in both builds. The standard tub
# uses none of them; the shared midplate uses FOLD_ZONE, MID_RELIEF, LOCATOR_Y / _Y_TOP and MID_STOP_NOTCH (its
# notches, which the standard build has too).
STRIP_JSON = 'hardware/reference/light-strip/strip-geometry.json'
STRIP_TAPE, STRIP_PI, STRIP_FLEX = 0.05, 0.225, 0.11
STRIP_STACK = STRIP_TAPE + STRIP_PI + STRIP_FLEX                # 0.385
STRIP_STACK_TOL = 0.045                   # assumed, the drawing gives none: PI stiffener +-0.03, flex +-0.03, tape
                                          # +-0.01, root-sum-square (mechanics.foot_stop)
STRIP_LED_H = 0.8
STRIP_LED_X = (-0.44, 0.96)               # LED body across the bar; the emitting face is at 0.96, facing +X
STRIP_BAR_X = (-1.24, 1.06)
STRIP_Z0 = LIP                            # the bar's tape side on the frame's seat, in the panel-front plane
STRIP_LED_TOP = STRIP_Z0 + STRIP_STACK + STRIP_LED_H           # 4.655
STRIP_LED_CLR = round(Z_FRONT_STRIP - 0.4 - STRIP_LED_TOP, 3)  # 0.215: LED tops to the skin (>= 0.1 asked; takes
                                          # the stack's tolerance, e.g. a 0.9 LED)
CHANNEL_SKIN = 0.4                        # plastic over the channel: two layers
CHANNEL_TOP = round(Z_FRONT_STRIP - CHANNEL_SKIN, 3)            # 4.87, the channel's ceiling
# The channel: from the side wall's inner face to the window's edge (the light reaches the screen under the
# skin), from the foot's pocket to the fold zone's end. The left lip over the panel's border is gone with it.
CHANNEL_X1 = round(hw.ACTIVE_CX - hw.ACTIVE_W / 2 - WINDOW_MARGIN + 0.01, 4)   # 2.8375: the window's left edge at
                                          # the lip (tub.window, 2.8275) + 0.01, so no sliver is left between them
CHANNEL_Y = (12.85, 92.7)                 # foot's top edge 12.75 + 0.1; the fold zone's end (FOLD_ZONE)
# The seat: the bar rests on a strip of the old frame along the side wall only. The bar goes in sideways from
# the pocket (LEDs on the skin, face-down tub, before the panel): it drops in beside the seat and slides -X by
# SEAT_X1 - STRIP_BAR_X[0] = 0.54 until it meets the stop ribs (STRIP_RIBS). The rest of the frame beside the panel
# is cut away over the bar's length so nothing is in its way. The seat is narrow so that the shift is small: the
# hold-down pads must stand clear of the bar while it drops in, yet reach back past the window's bevel to the skin
# they hang from (PAD_X). In the face-down print the seat is a 0.71 overhang off the wall.
SEAT_X1 = -0.70
# The seat runs from SEAT_Y[0] to the fold zone. Below it, under the foot's pocket and on past the channel's bottom
# end (Y 9.1..SEAT_Y[0]), the frame is cut away from the wall. While the bar slides in (face-down tub), its foot
# rests on the pocket's roof, which holds the tape side at FOOT_POCKET['top'] - stack: 0.015 over the seat's level
# nominal, 0.03 UNDER it with a +STRIP_STACK_TOL stack. Only past the roof's end (the channel, Y 12.85) does the bar
# rise, bending up to where D6's body (from 16.6) rests on the skin: its tape side there is 0.2 over the roof's
# level (0.1 with a STRIP_LED_H_MAX LED). mechanics.seat_entry models that span as a beam held flat at both ends
# and reads the tape side's height where the seat starts. From 12.85 the thick stack met the seat's edge by 0.03;
# from 14.0 it would clear it by 0.015, but a thick stack with a 0.9 LED would still touch it (-0.008); from 14.5
# every case clears (0.011 at worst, 0.052 thick with a 0.8 LED, 0.097 nominal). The foot, bonded to the PS film,
# carries the bar's end below the seat, and D6 still lies wholly on the seat: its copper starts at 15.95 (1.45 on),
# its body at 16.6 (2.1 on). build.strip_insertion also sweeps the bar bent this way along the slide.
SEAT_Y = (14.5, 73.4)                     # .. FOLD_ZONE[0]
STRIP_LED_H_MAX = 0.9                     # the tallest LED the checks take (STRIP_LED_CLR's allowance; the datasheet
                                          # gives 0.8 and no tolerance): the bar then lies 0.1 lower in the face-down tub
STRIP_D6_COPPER_Y = 15.95                 # D6's solder pads (1.6 long, 2.1 apart) start 0.65 below its body (16.6..20.6)
# Stop ribs: the bar is placed in X by short ribs on the channel's side wall, so it rests where the checks model it
# (STRIP_BAR_X) instead of against the wall 0.18 further left. Each stands from the wall's face in the channel
# (X -1.42: the channel is cut 0.01 into the wall) to the bar's left edge: 0.18 thick, 2.0 long. It prints as a
# 0.18 jog in the wall's outer perimeter, not as a free-standing feature (slice_check reads it back). Y centres
# between the lid's left latch arms (Y 9.75..14.25, 23.75..28.25, 37.25..41.75, 51.75..56.25, 66.25..70.75,
# 80.75..85.25), two of them on the fold zone, where the bar's top end would otherwise be free to swing sideways
# (in-plane the stiffened bar is soft: ~0.01 N moves its top end 0.1 from the last seat rib). In the fold zone
# they reach down to z_fold as well, so they stop the hand-folded pair's piece too (its LEDs are 0.163 from the
# Y-83 latch arm's inner face at the modelled place): 3.07, on a layer line (11 from the face) just under the folded
# piece's underside (3.085). From the seat (or z_fold) up to the ceiling.
STRIP_RIBS = dict(x0=-1.42, x1=-1.24, len=2.0, y=(19.0, 32.75, 46.75, 61.25, 75.75, 87.5), z_fold=round(Z_FRONT_STRIP - 11 * LAYER, 3))
# The strip-at-the-wall check case (build.STRIP_VARIANTS 'strip_wall', strip_insertion, strip_sections): the stiff
# front and the neck shifted this far -X, the bar's left edge then 0.01 off the wall's face, as if the ribs had
# not printed. Checked against the tub without its ribs.
STRIP_WALL_DX = -0.17
# The fold zone: the top pair folds back under the bar (tape to tape) round the bare hinge (strip Y 90.35..93.975,
# 3.625 long). Folded with the hinge's whole length in the loop, its inside radius is 0.63 and the folded piece
# lies at Y 73.98..89.16 (its LEDs facing -Z, down to Z 2.285; the loop to Y 91.10); folded tighter (inside 0.35),
# at 76.56..91.73 with the loop reaching Y 92.66. The frame is gone over this zone, and the midplate is notched
# under it.
FOLD_ZONE = (73.4, 92.7)
FOLD_RIN = 0.63                           # the modelled (relaxed) fold's inside radius; refs.strip also checks 0.45
# The midplate is notched right through under the fold zone, X from its edge to 1.3: a 0.5-deep relief would leave
# 0.3 of plate, which the slicer prints as one 0.2 layer (first pass). Through, the folded LEDs clear the board by
# 0.685 and the loop by 0.775 (no lead stands proud at X < 2 there); the glass's edge (X >= 1.1) overhangs it <= 0.2.
# SW7's two front lead holes (clearance circles r 1.25 at (2.747, 73.0) and (2.747, 78.0)) come within 0.2..0.28 of
# the notch's edge, which left webs narrower than one line: the notch runs into any hole that comes within
# web_min of it, over that hole's height (midplate.fold_relief).
MID_RELIEF = dict(x1=1.3, floor=MID_REAR - 0.5, web_min=0.42)
# The panel's left edge was held by the frame's wall (POCKET_X0). Beside the bar it now has no wall, so it is
# located at its two left corners, below the foot (Y 7.1..9.1) and above the fold zone (92.7..93.39), by stops at
# LOCATOR_X: the glass's edge then stays 0.04 clear of the folded piece (X <= 1.06, whose underside at 3.085 is below
# a -0.1 panel's glass top, 3.2) and 0.14 clear of the folded LEDs' faces (0.96) with the panel pushed left. A
# max-width panel (56.44) still has 0.077 of play, pushed 0.073 right of centre. Each stop is a block from the side
# wall out to LOCATOR_X, from LOCATOR_Z0 to LOCATOR_Z.
LOCATOR_X = 1.1
LOCATOR_Z = 3.27                          # on a layer line (10 from the face); a -0.1 panel's glass reaches 3.20
# The stops' rear (retention review, 2026-09-26). They stood from the frame's rear (2.85), which covers only the front
# 0.25 of the glass's 0.5 edge (2.60..3.10 nominal), 0.15 on a +0.1 panel (2.50..3.00): a sideways knock then bears on a
# 0.15 strip at the glass's front corner. From 2.47 (14 layers from the face, the first layer line under 2.50) they
# cover the whole edge on every panel: the contact is 2.69 x 0.5 = 1.345 mm2 in every case (0.40..0.94 before), and a
# 200 g leftward knock (16.3 N on the 8.32 g panel) bears at 12.1 MPa shared, 47 MPa on the 0.69-long top stop alone
# (24 / 40 MPa nominal / +0.1 shared, 158 MPa on the top stop alone at +0.1, before). The midplate (front face
# 2.5..2.7) is notched through under them (MID_STOP_NOTCH).
LOCATOR_Z0 = round(Z_FRONT_STRIP - 14 * LAYER, 3)               # 2.47
LOCATOR_Y = (7.1, 9.1)                    # 0.3 above the pocket's bottom edge (6.80, clear of its corner relief) to
                                          # 0.15 below the foot's bottom edge (9.25)
LOCATOR_Y_TOP = (FOLD_ZONE[1], round(POCKET_Y1 - 0.45, 3))      # 92.7..93.39: from the fold zone to the pocket's
                                          # corner relief
# The midplate's notches under the stops, through (a partial one would leave an unsupported shelf in the plate's
# face-down print), from its left edge to x1 (as MID_RELIEF: 0.2 past the stop's face, the plate's own X play to the
# walls), clr past the stop's ends in Y: more than the plate's +-0.3 of Y play in its detent pockets (MID_DETENT
# 'clr'). The bottom one then ends at 9.45, where the Y-9.45 latch notch starts, so no web is left between them; the
# top one runs on from the fold relief to 93.74.
MID_STOP_NOTCH = dict(x1=MID_RELIEF['x1'], clr=0.35)
# The foot (on the PS's bottom border) and the neck (over the PS end and the glass ledge) sit under a pocket in
# the lip. It runs 0.54 + 0.2 past the foot's right end (13.73) for the sideways insertion. Its top edge is the
# window's bottom edge (13.13): the 0.38 between the foot's top edge (12.75) and the window cannot hold a printable
# strip of lip with clearance (a 0.28 strip sliced to nothing: 0.42 lines, classic walls), so the pocket opens into
# the window there. With no lip over the panel's bottom-left border, the foot is its stop: the roof sits on the
# first layer line over the foot's top (3.855), 7 layers from the face, so the panel (pushed up by the midplate
# spring at (8.5, 11.5)) can lift at most 0.015 before the foot meets it. A strip stack up to 0.045 over nominal
# presses that corner of the panel back by as much, which the springs take (mechanics.springs 'foot_stop'). The
# next layer line up (4.07) would let the corner lift 0.215, past the spring's own 0.2 of preload.
FOOT_POCKET = dict(x1=14.5, y1=round(hw.ACTIVE_CY - hw.ACTIVE_H / 2 - WINDOW_MARGIN, 4),    # 13.13
                   top=round(Z_FRONT_STRIP - 7 * LAYER, 3))                                   # 3.87
# Hold-down pads: with the left lip gone, the panel's left border is held by pads between the pairs (and one at
# the top border), over the PS film (from X 1.777) and 0.07 of the bare glass border, from the skin to the panel's
# front. They start 0.1 past the bar's right edge while it drops in (1.60), and they hang from the skin over
# X 1.70..2.03, where the window's 45-degree bevel meets the channel's roof (the rest of each pad sits under the
# bevel, which it follows). Centres midway between pairs; 1.0 long.
PAD_X = (1.70, CHANNEL_X1)
PAD_LEN = 1.0
PAD_Y = (29.675, 45.225, 60.775, 76.325, 92.3)
# Pad ribs (retention review, 2026-09-26): pads 1-4 hung from the skin's thin tapered edge only, about 7 N/mm each
# (skin_plate.pad_stiffness, E 3000; the review's lighter model gave 10), so the springs lifted the panel's left border
# 0.09 proud of the lip's plane on a nominal panel, 0.14 on a +0.1 panel and 0.25 in a 200 g face-down knock (0.13 /
# 0.19 / 0.35 at E 2000, creeping; the review's glass-plate model, run outside the repo). Each now has a rib under the
# channel's ceiling from the side wall's face (X -1.42) to the pad (X 1.70), joined to the wall, the ceiling and the pad:
# 37 N/mm (24 at E 2000), and the border lifts 0.026 / 0.038 / 0.064 (0.034 / 0.051 / 0.089). The verifier's Ritz
# plate gives the same within 0.01. A 3D solid model of one pad gives about 17 % less stiffness (30.5 / 20.3 N/mm,
# 5.7 before, the same 5.3x gain), so the lifts may be up to about 15 % higher.
#   z0   4.27, the rib 0.6 deep (5 layers from the face). The review proposed 4.17 (0.7 deep), but that is half a layer
#        (the slicer would put it 0.1 either way); 4.07 would meet the bar's flex, which lies at 4.07 while the bar slides
#        in on its LEDs (0.8 LED). At 4.27 the flex clears it by 0.2 (0.3 with a 0.9 LED).
#   len  2.0 in Y, centred on the pad (the review proposed 1.0): stiffness goes with it (1.0: 21 N/mm, 1.5: 29, 2.0: 37),
#        and in the pad-shading ray model a longer rib costs nothing, because every in-plane ray that meets the part of
#        a rib beyond the pad's span would meet the pad anyway; only rays that cross the whole pad span before X 1.70
#        (80 deg or more off the LEDs' axis) are added: 0.15 % of the light (0.32 % if the rib were full height), the
#        same for 1.0, 1.5 and 2.0. 2.0 leaves 1.475 to the LED bodies either side and 0.825 to their solder pads
#        (2.65 from each LED's centre), more than the strip's placement range along Y (-0.67..+0.38: the foot on the PS
#        film's border and out of the window, with the panel's +-0.25 of play). 2.5 would leave 0.575 to the pads.
# The ribs on pads 2-4 merge with the stop ribs at 46.75 / 61.25 / 75.75; below z0 the stop faces are unchanged.
# Pad 5 (Y 92.3) is next to the channel's clamped end (about 300 N/mm) and has none.
PAD_RIBS = dict(y=PAD_Y[:4], len=2.0, z0=round(Z_FRONT_STRIP - 5 * LAYER, 3))
# The channel's skin under a fingertip (mechanics.channel_skin, a Kirchhoff plate model): SKIN_PRESS['F'] spread
# evenly over a disc of radius r, all of it on the skin (none on the side wall beside it), centred over an LED.
SKIN_PRESS = dict(F=5.0, r=3.0)
# The neck folds 90 deg over the glass's bottom edge into the board's slot, 6.5 left of the panel's FPC. Its gap
# in the chin's web takes the fold, a slack loop in the chin up to 1.8 past the glass edge, and the 0.54 shift
# of the sideways insertion (X 8.247..13.76 + 0.54 + 0.3). Its left edge (X 7.7) is left of SW9's pin (centre
# (8.0, 4.3)), but the pin is 0.9 below the gap's bottom edge (Y 5.2), so the gap stays clear of it.
STRIP_GAP = dict(x=(7.7, 14.6), y=(5.2, 6.9), z=(1.75, 3.67))
