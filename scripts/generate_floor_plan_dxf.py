"""
Generate a professional 2BHK apartment floor plan DXF file.
All dimensions in meters. Wall thickness: 0.23m.
"""

import ezdxf
from ezdxf import colors
from ezdxf.enums import TextEntityAlignment
import math
import os

os.makedirs("docs", exist_ok=True)

doc = ezdxf.new(dxfversion="R2010")
doc.header["$INSUNITS"] = 6  # meters
msp = doc.modelspace()

# ─────────────────────────────────────────────
# LAYER SETUP
# ─────────────────────────────────────────────
def make_layer(name, color, ltype="Continuous", lineweight=25):
    if name not in doc.layers:
        layer = doc.layers.add(name)
    else:
        layer = doc.layers.get(name)
    layer.color = color
    layer.linetype = ltype
    layer.lineweight = lineweight

# Register linetypes
if "DASHED" not in doc.linetypes:
    doc.linetypes.add("DASHED", pattern=[0.5, 0.25, -0.25])
if "CENTER" not in doc.linetypes:
    doc.linetypes.add("CENTER", pattern=[1.0, 0.5, -0.25, 0.1, -0.25])

make_layer("WALLS",      color=7,   lineweight=50)   # white/black
make_layer("DOORS",      color=4,   lineweight=25)   # cyan
make_layer("WINDOWS",    color=2,   lineweight=25)   # yellow
make_layer("DIMENSIONS", color=1,   lineweight=18)   # red
make_layer("TEXT",       color=7,   lineweight=18)   # white
make_layer("FURNITURE",  color=5,   ltype="DASHED", lineweight=18)  # blue
make_layer("GRID",       color=8,   ltype="DASHED", lineweight=13)  # gray
make_layer("TITLEBLOCK", color=7,   lineweight=35)
make_layer("NORTHARROW", color=3,   lineweight=25)   # green

# ─────────────────────────────────────────────
# DIMSTYLE
# ─────────────────────────────────────────────
if "ARCH" not in doc.dimstyles:
    dimstyle = doc.dimstyles.new("ARCH")
else:
    dimstyle = doc.dimstyles.get("ARCH")
dimstyle.dxf.dimtxt  = 0.18
dimstyle.dxf.dimasz  = 0.15
dimstyle.dxf.dimexe  = 0.1
dimstyle.dxf.dimexo  = 0.05
dimstyle.dxf.dimgap  = 0.06
dimstyle.dxf.dimclrd = 1   # red
dimstyle.dxf.dimclrt = 1

# ─────────────────────────────────────────────
# WALL HELPER — draw two parallel lines (inner + outer face)
# ─────────────────────────────────────────────
W = 0.23   # wall thickness

def wall_h(x1, y1, x2, y2):
    """Horizontal or arbitrary wall as two parallel lines."""
    msp.add_line((x1, y1), (x2, y2),
                 dxfattribs={"layer": "WALLS", "lineweight": 50})
    msp.add_line((x1, y1 + W), (x2, y2 + W),
                 dxfattribs={"layer": "WALLS", "lineweight": 50})

def wall_v(x1, y1, x2, y2):
    msp.add_line((x1, y1), (x2, y2),
                 dxfattribs={"layer": "WALLS", "lineweight": 50})
    msp.add_line((x1 + W, y1), (x2 + W, y2),
                 dxfattribs={"layer": "WALLS", "lineweight": 50})

def wall(x1, y1, x2, y2, offset_x=0.0, offset_y=0.0):
    """Generic wall line pair (inner face + outer face offset)."""
    msp.add_line((x1, y1), (x2, y2),
                 dxfattribs={"layer": "WALLS", "lineweight": 50})
    msp.add_line((x1 + offset_x, y1 + offset_y),
                 (x2 + offset_x, y2 + offset_y),
                 dxfattribs={"layer": "WALLS", "lineweight": 50})

# ─────────────────────────────────────────────
# ROOM LAYOUT  (inner face coordinates)
#
#  Overall bounding box (inner): ~12.5m wide x 9.0m tall
#
#  Y
#  ^
#  |  [BALCONY 3.0x1.2]  [MBR 4.0x3.5]  [BR2 3.5x3.0]
#  |  [LIVING  5.5x4.0]  [BATH1 2x1.5]  [BATH2 1.8x1.5]
#  |  [FOYER 2x1.5]  [KITCHEN 3.0x3.5]
#  +-----> X
#
# Let's place everything on a neat grid:
# ─────────────────────────────────────────────

# Overall apartment outer boundary (inner edge)
APT_X  = 1.0   # left margin
APT_Y  = 3.0   # bottom margin (title block space)

# --- FOYER / ENTRY  (2.0 x 1.5)  bottom-left
FOY_X1, FOY_Y1 = APT_X,        APT_Y
FOY_X2, FOY_Y2 = APT_X + 2.0,  APT_Y + 1.5

# --- KITCHEN  (3.0 x 3.5)  bottom-centre
KIT_X1, KIT_Y1 = FOY_X2,        APT_Y
KIT_X2, KIT_Y2 = KIT_X1 + 3.0,  APT_Y + 3.5

# --- LIVING ROOM  (5.5 x 4.0)  left, above foyer
LIV_X1, LIV_Y1 = APT_X,         FOY_Y2
LIV_X2, LIV_Y2 = LIV_X1 + 5.5,  LIV_Y1 + 4.0

# --- BATHROOM 2  (1.8 x 1.5)  right of kitchen, bottom
B2_X1, B2_Y1 = KIT_X2,       APT_Y
B2_X2, B2_Y2 = B2_X1 + 1.8,  APT_Y + 1.5

# --- BATHROOM 1 (Master)  (2.0 x 1.5)  right of kitchen top
B1_X1, B1_Y1 = KIT_X2,       KIT_Y1 + 2.0
B1_X2, B1_Y2 = B1_X1 + 2.0,  B1_Y1 + 1.5

# --- MASTER BEDROOM  (4.0 x 3.5)  top-right of living
MBR_X1, MBR_Y1 = LIV_X2,        LIV_Y1
MBR_X2, MBR_Y2 = MBR_X1 + 4.0,  MBR_Y1 + 3.5

# --- BEDROOM 2  (3.5 x 3.0)  right of master bedroom
BR2_X1, BR2_Y1 = MBR_X2,        LIV_Y1
BR2_X2, BR2_Y2 = BR2_X1 + 3.5,  BR2_Y1 + 3.0

# --- BALCONY  (3.0 x 1.2)  above living room (front)
BAL_X1, BAL_Y1 = LIV_X1,        LIV_Y2
BAL_X2, BAL_Y2 = BAL_X1 + 3.0,  BAL_Y1 + 1.2

# Adjust kitchen top to match living bottom
# (Kitchen right side lines up to bathroom stack)
KIT_Y2 = LIV_Y1   # kitchen top = living room bottom  (= FOY_Y2 = APT_Y+1.5... let's recalc)
# Redefine consistent with actual foyer height
KIT_Y2 = LIV_Y1  # already = FOY_Y2

# ─────────────────────────────────────────────
# GRID LINES  (every 1 m, over apartment area)
# ─────────────────────────────────────────────
GRID_X1 = APT_X - 0.5
GRID_Y1 = APT_Y - 0.5
GRID_X2 = BR2_X2 + W + 0.5
GRID_Y2 = BAL_Y2 + W + 0.5

x = math.floor(GRID_X1)
while x <= GRID_X2:
    msp.add_line((x, GRID_Y1), (x, GRID_Y2),
                 dxfattribs={"layer": "GRID", "linetype": "DASHED",
                             "ltscale": 0.5})
    x += 1.0

y = math.floor(GRID_Y1)
while y <= GRID_Y2:
    msp.add_line((GRID_X1, y), (GRID_X2, y),
                 dxfattribs={"layer": "GRID", "linetype": "DASHED",
                             "ltscale": 0.5})
    y += 1.0

# ─────────────────────────────────────────────
# OUTER APARTMENT BOUNDARY WALLS
# ─────────────────────────────────────────────
# We draw the full perimeter as thick outer walls

def rect_walls(x1, y1, x2, y2):
    """Draw 4 double-line walls for a room rectangle."""
    # bottom
    wall(x1, y1, x2, y1, offset_y=-W)
    # top
    wall(x1, y2, x2, y2, offset_y=W)
    # left
    wall(x1, y1, x1, y2, offset_x=-W)
    # right
    wall(x2, y1, x2, y2, offset_x=W)


# Draw each room as a rectangle (shared walls will overlap — fine for DXF)
for room in [
    (FOY_X1, FOY_Y1, FOY_X2, FOY_Y2),
    (KIT_X1, KIT_Y1, KIT_X2, KIT_Y2),
    (LIV_X1, LIV_Y1, LIV_X2, LIV_Y2),
    (B1_X1,  B1_Y1,  B1_X2,  B1_Y2),
    (B2_X1,  B2_Y1,  B2_X2,  B2_Y2),
    (MBR_X1, MBR_Y1, MBR_X2, MBR_Y2),
    (BR2_X1, BR2_Y1, BR2_X2, BR2_Y2),
    (BAL_X1, BAL_Y1, BAL_X2, BAL_Y2),
]:
    rect_walls(*room)

# ─────────────────────────────────────────────
# DOORS  (quarter-circle swing arc + door line)
# ─────────────────────────────────────────────
def add_door(cx, cy, radius, start_angle, end_angle, door_dir_angle):
    """Door: arc swing + door leaf line."""
    msp.add_arc(center=(cx, cy), radius=radius,
                start_angle=start_angle, end_angle=end_angle,
                dxfattribs={"layer": "DOORS"})
    rad = math.radians(door_dir_angle)
    msp.add_line((cx, cy),
                 (cx + radius * math.cos(rad),
                  cy + radius * math.sin(rad)),
                 dxfattribs={"layer": "DOORS"})

# Foyer entry door (bottom wall, swings inward = upward)
add_door(FOY_X1 + 0.5, FOY_Y1, 0.9, 0, 90, 90)

# Living room to foyer (left wall of living, swings right)
add_door(LIV_X1, LIV_Y1 + 0.5, 0.9, 270, 360, 0)

# Kitchen door (top wall of kitchen, swings up)
add_door(KIT_X1 + 0.5, KIT_Y2, 0.9, 0, 90, 90)

# Master bedroom door (left wall of MBR, swings right)
add_door(MBR_X1, MBR_Y1 + 0.5, 0.9, 270, 360, 0)

# Master bath door (right wall of B1, swings right)
add_door(B1_X1, B1_Y1 + 0.5, 0.7, 270, 360, 0)

# Bedroom 2 door (left wall of BR2)
add_door(BR2_X1, BR2_Y1 + 0.5, 0.9, 270, 360, 0)

# Bath 2 door (left wall of B2, swings right)
add_door(B2_X1, B2_Y1 + 0.5, 0.7, 270, 360, 0)

# Balcony sliding door (bottom of balcony = top of living)
add_door(BAL_X1 + 0.5, BAL_Y1, 1.0, 0, 90, 90)

# ─────────────────────────────────────────────
# WINDOWS  (break in wall + 3 parallel lines)
# ─────────────────────────────────────────────
def window_h(wx, wy, width):
    """Horizontal window in a horizontal wall."""
    gap = 0.05
    for i in range(3):
        yy = wy - W/2 + (i - 1) * (W/2)
        msp.add_line((wx, yy), (wx + width, yy),
                     dxfattribs={"layer": "WINDOWS"})
    # end markers
    for xx in [wx, wx + width]:
        msp.add_line((xx, wy - W), (xx, wy + W),
                     dxfattribs={"layer": "WINDOWS"})

def window_v(wx, wy, height):
    """Vertical window in a vertical wall."""
    for i in range(3):
        xx = wx - W/2 + (i - 1) * (W/2)
        msp.add_line((xx, wy), (xx, wy + height),
                     dxfattribs={"layer": "WINDOWS"})
    for yy in [wy, wy + height]:
        msp.add_line((wx - W, yy), (wx + W, yy),
                     dxfattribs={"layer": "WINDOWS"})

# Living room: large window on bottom wall (south-facing)
window_h(LIV_X1 + 1.0, LIV_Y1, 2.5)

# Living room: window on left wall (west)
window_v(LIV_X1, LIV_Y1 + 1.5, 1.5)

# Master bedroom: window on top wall
window_h(MBR_X1 + 0.5, MBR_Y2, 2.0)

# Bedroom 2: window on right wall
window_v(BR2_X2, BR2_Y1 + 0.5, 1.8)

# Kitchen: window on bottom
window_h(KIT_X1 + 0.5, KIT_Y1, 1.5)

# Balcony: full front opening on top
window_h(BAL_X1 + 0.2, BAL_Y2, 2.4)

# ─────────────────────────────────────────────
# ROOM LABELS  (centered text)
# ─────────────────────────────────────────────
def label(text, cx, cy, height=0.22):
    msp.add_text(text, dxfattribs={
        "layer": "TEXT",
        "height": height,
        "style": "Standard",
        "halign": 4,  # MIDDLE_CENTER via insert
    }).set_placement((cx, cy), align=TextEntityAlignment.MIDDLE_CENTER)

def sublabel(text, cx, cy, height=0.15):
    msp.add_text(text, dxfattribs={
        "layer": "TEXT",
        "height": height,
        "color": 8,
    }).set_placement((cx, cy), align=TextEntityAlignment.MIDDLE_CENTER)


rooms = [
    ("LIVING ROOM",     "5.5 x 4.0 m",  (LIV_X1+LIV_X2)/2, (LIV_Y1+LIV_Y2)/2),
    ("KITCHEN",         "3.0 x 3.5 m",  (KIT_X1+KIT_X2)/2, (KIT_Y1+KIT_Y2)/2),
    ("MASTER BEDROOM",  "4.0 x 3.5 m",  (MBR_X1+MBR_X2)/2, (MBR_Y1+MBR_Y2)/2),
    ("BEDROOM 2",       "3.5 x 3.0 m",  (BR2_X1+BR2_X2)/2, (BR2_Y1+BR2_Y2)/2),
    ("MASTER BATH",     "2.0 x 1.5 m",  (B1_X1+B1_X2)/2,   (B1_Y1+B1_Y2)/2),
    ("BATH 2",          "1.8 x 1.5 m",  (B2_X1+B2_X2)/2,   (B2_Y1+B2_Y2)/2),
    ("BALCONY",         "3.0 x 1.2 m",  (BAL_X1+BAL_X2)/2, (BAL_Y1+BAL_Y2)/2),
    ("ENTRY / FOYER",   "2.0 x 1.5 m",  (FOY_X1+FOY_X2)/2, (FOY_Y1+FOY_Y2)/2),
]

for name, size, cx, cy in rooms:
    label(name, cx, cy + 0.12, height=0.20)
    sublabel(size, cx, cy - 0.12, height=0.14)

# ─────────────────────────────────────────────
# DIMENSIONS
# ─────────────────────────────────────────────
DIM_OFFSET = 0.6   # how far outside the room the dim line sits

def hdim(x1, y1, x2, y2_dim, text=""):
    """Horizontal dimension line."""
    dim = msp.add_linear_dim(
        base=(x1, y2_dim),
        p1=(x1, y1),
        p2=(x2, y1),
        dimstyle="ARCH",
        dxfattribs={"layer": "DIMENSIONS", "color": 1},
    )
    dim.render()

def vdim(xdim, ya, yb, text=""):
    """Vertical dimension line. xdim = offset position, ya/yb = y extents."""
    dim = msp.add_linear_dim(
        base=(xdim, ya),
        p1=(xdim + 0.01, ya),
        p2=(xdim + 0.01, yb),
        angle=90,
        dimstyle="ARCH",
        dxfattribs={"layer": "DIMENSIONS", "color": 1},
    )
    dim.render()

# Living room dims
hdim(LIV_X1, LIV_Y1 - DIM_OFFSET, LIV_X2, LIV_Y1 - DIM_OFFSET)
vdim(LIV_X1 - DIM_OFFSET, LIV_Y1, LIV_Y2)

# Kitchen
hdim(KIT_X1, KIT_Y1 - DIM_OFFSET - 0.3, KIT_X2, KIT_Y1 - DIM_OFFSET - 0.3)
vdim(KIT_X2 + DIM_OFFSET, KIT_Y1, KIT_Y2)

# Master bedroom
hdim(MBR_X1, MBR_Y2 + DIM_OFFSET, MBR_X2, MBR_Y2 + DIM_OFFSET)
vdim(MBR_X2 + DIM_OFFSET, MBR_Y1, MBR_Y2)

# Bedroom 2
hdim(BR2_X1, BR2_Y2 + DIM_OFFSET, BR2_X2, BR2_Y2 + DIM_OFFSET)
vdim(BR2_X2 + DIM_OFFSET, BR2_Y1, BR2_Y2)

# Balcony
hdim(BAL_X1, BAL_Y2 + DIM_OFFSET, BAL_X2, BAL_Y2 + DIM_OFFSET)
vdim(BAL_X1 - DIM_OFFSET, BAL_Y1, BAL_Y2)

# Foyer
hdim(FOY_X1, FOY_Y1 - DIM_OFFSET - 0.6, FOY_X2, FOY_Y1 - DIM_OFFSET - 0.6)

# ─────────────────────────────────────────────
# FURNITURE  (blue dashed, schematic)
# ─────────────────────────────────────────────
def furn_rect(x, y, w, h, label_text=""):
    pts = [(x,y),(x+w,y),(x+w,y+h),(x,y+h),(x,y)]
    msp.add_lwpolyline(pts, dxfattribs={"layer":"FURNITURE","linetype":"DASHED","ltscale":0.3})
    if label_text:
        cx, cy = x + w/2, y + h/2
        msp.add_text(label_text, dxfattribs={
            "layer": "FURNITURE", "height": 0.12, "color": 5
        }).set_placement((cx, cy), align=TextEntityAlignment.MIDDLE_CENTER)

def furn_circle(cx, cy, r):
    msp.add_circle((cx, cy), r, dxfattribs={"layer":"FURNITURE","linetype":"DASHED","ltscale":0.3})

# Living: sofa (L-shape approx)
furn_rect(LIV_X1 + 0.3, LIV_Y1 + 0.5, 2.2, 0.9, "SOFA")
furn_rect(LIV_X1 + 0.3, LIV_Y1 + 1.4, 0.9, 1.2, "")  # arm
# Coffee table
furn_rect(LIV_X1 + 1.5, LIV_Y1 + 1.6, 0.9, 0.5, "TABLE")
# TV unit
furn_rect(LIV_X2 - 1.8, LIV_Y1 + 0.3, 1.5, 0.4, "TV UNIT")

# Kitchen: counter along bottom
furn_rect(KIT_X1 + 0.1, KIT_Y1 + 0.1, KIT_X2 - KIT_X1 - 0.2, 0.6, "COUNTER")
# Dining table
furn_rect(KIT_X1 + 0.3, KIT_Y1 + 1.5, 1.4, 0.8, "DINING")

# Master bedroom: bed
furn_rect(MBR_X1 + 0.4, MBR_Y1 + 0.5, 1.6, 2.0, "BED")
# Wardrobe
furn_rect(MBR_X2 - 1.2, MBR_Y1 + 0.2, 1.0, 0.5, "WARDROBE")

# Bedroom 2: bed
furn_rect(BR2_X1 + 0.3, BR2_Y1 + 0.4, 1.4, 1.9, "BED")
furn_rect(BR2_X2 - 1.1, BR2_Y1 + 0.2, 0.9, 0.5, "WARDROBE")

# Bathrooms: toilet + sink schematic
# Bath 1
furn_rect(B1_X1 + 0.1, B1_Y1 + 0.1, 0.5, 0.6, "WC")
furn_circle(B1_X1 + 1.5, B1_Y1 + 0.4, 0.2)  # sink

# Bath 2
furn_rect(B2_X1 + 0.1, B2_Y1 + 0.1, 0.5, 0.6, "WC")
furn_circle(B2_X1 + 1.3, B2_Y1 + 0.4, 0.2)

# ─────────────────────────────────────────────
# NORTH ARROW  (top-right corner)
# ─────────────────────────────────────────────
NA_X = BR2_X2 + 1.5
NA_Y = BAL_Y2 + 0.5
NA_R = 0.5

msp.add_circle((NA_X, NA_Y), NA_R,
               dxfattribs={"layer": "NORTHARROW", "color": 3})
# Arrow pointing up (North)
msp.add_line((NA_X, NA_Y), (NA_X, NA_Y + NA_R * 1.3),
             dxfattribs={"layer": "NORTHARROW", "color": 3, "lineweight": 35})
msp.add_line((NA_X, NA_Y), (NA_X - 0.15, NA_Y - 0.2),
             dxfattribs={"layer": "NORTHARROW", "color": 3})
msp.add_line((NA_X, NA_Y), (NA_X + 0.15, NA_Y - 0.2),
             dxfattribs={"layer": "NORTHARROW", "color": 3})
msp.add_text("N", dxfattribs={"layer": "NORTHARROW", "height": 0.3, "color": 3})\
   .set_placement((NA_X, NA_Y + NA_R * 1.4), align=TextEntityAlignment.BOTTOM_CENTER)

# ─────────────────────────────────────────────
# TITLE BLOCK  (bottom of drawing)
# ─────────────────────────────────────────────
TB_X1 = APT_X - 0.5
TB_Y1 = APT_Y - 2.5
TB_X2 = BR2_X2 + W + 0.5
TB_Y2 = APT_Y - 0.3

# Outer border
border = [(TB_X1, TB_Y1), (TB_X2, TB_Y1), (TB_X2, TB_Y2),
          (TB_X1, TB_Y2), (TB_X1, TB_Y1)]
msp.add_lwpolyline(border, dxfattribs={"layer": "TITLEBLOCK", "lineweight": 50})

# Inner dividers
mid_x = (TB_X1 + TB_X2) / 2
msp.add_line((mid_x, TB_Y1), (mid_x, TB_Y2),
             dxfattribs={"layer": "TITLEBLOCK"})
mid_y = (TB_Y1 + TB_Y2) / 2
msp.add_line((TB_X1, mid_y), (TB_X2, mid_y),
             dxfattribs={"layer": "TITLEBLOCK"})

# Title block text
cx_l = (TB_X1 + mid_x) / 2
cx_r = (mid_x + TB_X2) / 2
cy_t = (mid_y + TB_Y2) / 2
cy_b = (TB_Y1 + mid_y) / 2

titles = [
    ("PROJECT: Sample 2BHK Apartment",        cx_l, cy_t, 0.22),
    ("interior-design-3d-to-2d",              cx_r, cy_t, 0.22),
    ("SCALE: 1:50  |  DRAWN BY: interior-design-3d-to-2d", cx_l, cy_b, 0.18),
    ("DATE: March 2026  |  SHEET: A-001",     cx_r, cy_b, 0.18),
]
for text, cx, cy, h in titles:
    msp.add_text(text, dxfattribs={"layer": "TITLEBLOCK", "height": h, "color": 7})\
       .set_placement((cx, cy), align=TextEntityAlignment.MIDDLE_CENTER)

# Drawing border (full sheet)
SHEET_X1 = TB_X1 - 0.3
SHEET_Y1 = TB_Y1 - 0.3
SHEET_X2 = NA_X + NA_R + 0.5
SHEET_Y2 = BAL_Y2 + W + 1.0

sheet = [(SHEET_X1, SHEET_Y1), (SHEET_X2, SHEET_Y1),
         (SHEET_X2, SHEET_Y2), (SHEET_X1, SHEET_Y2), (SHEET_X1, SHEET_Y1)]
msp.add_lwpolyline(sheet, dxfattribs={"layer": "TITLEBLOCK", "lineweight": 70})

# ─────────────────────────────────────────────
# DRAWING TITLE  (above title block)
# ─────────────────────────────────────────────
msp.add_text("FLOOR PLAN — SAMPLE 2BHK APARTMENT  (~1200 SQFT)",
             dxfattribs={"layer": "TEXT", "height": 0.35, "color": 7})\
   .set_placement(((APT_X + BR2_X2) / 2, APT_Y - 0.15),
                  align=TextEntityAlignment.BOTTOM_CENTER)

# ─────────────────────────────────────────────
# SAVE
# ─────────────────────────────────────────────
out_path = "docs/sample_floor_plan.dxf"
doc.saveas(out_path)
print(f"DXF saved to: {out_path}")

# Quick sanity check
doc2 = ezdxf.readfile(out_path)
entities = list(doc2.modelspace())
print(f"Total entities in modelspace: {len(entities)}")
layers = [l.dxf.name for l in doc2.layers]
print(f"Layers: {layers}")
