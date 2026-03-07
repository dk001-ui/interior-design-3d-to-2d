"""
Generate a professional 1920x1080 before/after comparison image:
  LEFT  — 3D isometric wireframe of the apartment (dark bg)
  RIGHT — Clean 2D architectural floor plan (white bg)
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patches as patches
from matplotlib.patches import FancyArrowPatch, Arc, FancyBboxPatch, Wedge
from matplotlib.lines import Line2D
import matplotlib.patheffects as pe
import numpy as np
import os

os.makedirs("docs", exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# FIGURE SETUP  — 1920x1080 at 96 dpi
# ─────────────────────────────────────────────────────────────────────────────
DPI = 96
fig = plt.figure(figsize=(1920/DPI, 1080/DPI), dpi=DPI)
fig.patch.set_facecolor("#0D0D0D")

# Three columns: left panel | arrow | right panel
gs = fig.add_gridspec(
    3, 3,
    left=0.01, right=0.99,
    top=0.88, bottom=0.04,
    width_ratios=[1.0, 0.08, 1.0],
    height_ratios=[0.06, 0.88, 0.06],
    hspace=0.0, wspace=0.02
)

ax3d   = fig.add_subplot(gs[1, 0])   # 3D wireframe panel
ax_mid = fig.add_subplot(gs[1, 1])   # arrow
ax2d   = fig.add_subplot(gs[1, 2])   # 2D plan panel

# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
fig.text(0.5, 0.955, "interior-design-3d-to-2d  |  Automated Conversion Pipeline",
         ha="center", va="center", fontsize=22, fontweight="bold",
         color="white", fontfamily="monospace",
         path_effects=[pe.withStroke(linewidth=4, foreground="#1A1A2E")])

fig.text(0.5, 0.918, "From 3D model to construction-ready 2D drawings in seconds",
         ha="center", va="center", fontsize=13, color="#A0A0C0",
         fontfamily="monospace")

# Thin separator line
line = plt.Line2D([0.03, 0.97], [0.905, 0.905], transform=fig.transFigure,
                  color="#2A2A4A", linewidth=1.5)
fig.add_artist(line)

# ─────────────────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════
#  LEFT PANEL — 3D Isometric wireframe
# ══════════════════════════════════════════════════════════
# ─────────────────────────────────────────────────────────────────────────────
ax3d.set_facecolor("#0A0A14")
ax3d.set_xlim(-1, 17)
ax3d.set_ylim(-1, 16)
ax3d.set_aspect("equal")
ax3d.axis("off")

# Isometric projection helper
def iso(x, y, z=0):
    """Convert 3D coords to 2D isometric screen coords."""
    angle = np.radians(30)
    sx = (x - y) * np.cos(angle)
    sy = (x + y) * np.sin(angle) + z * 0.85
    return sx, sy

# Scale factor to fit
def s(x, y, z=0):
    px, py = iso(x * 0.55, y * 0.55, z * 0.55)
    return px + 8, py + 1.5   # offset to center

H = 3.0   # wall height in meters

# Room definitions (x1,y1,x2,y2) — same layout as DXF script
rooms_3d = {
    "LIVING\nROOM":     (1.0, 4.5, 6.5, 8.5),
    "KITCHEN":          (1.0, 1.5, 4.0, 4.5),   # adjusted for visual
    "MASTER\nBEDROOM":  (6.5, 4.5, 10.5, 8.0),
    "BEDROOM 2":        (10.5, 4.5, 14.0, 7.5),
    "BATH 1":           (6.5, 2.0, 8.5, 3.5),
    "BATH 2":           (4.0, 1.5, 5.8, 3.0),
    "BALCONY":          (1.0, 8.5, 4.0, 9.7),
    "FOYER":            (1.0, 1.5, 3.0, 3.0),    # overlaps kitchen edge — fine
}

WALL_COLOR   = "#00BFFF"    # bright cyan
FLOOR_COLOR  = "#1A1A3A"
EDGE_COLOR   = "#003060"
LABEL_COLOR  = "#80D0FF"
GRID_COLOR   = "#0A1A2A"

def draw_room_3d(ax, x1, y1, x2, y2, wall_col, floor_col, label="", alpha=0.85):
    """Draw a single room as an isometric extruded box."""
    corners_bot = [(x1,y1,0),(x2,y1,0),(x2,y2,0),(x1,y2,0)]
    corners_top = [(x1,y1,H),(x2,y1,H),(x2,y2,H),(x1,y2,H)]

    # Floor fill
    fx = [s(*c)[0] for c in corners_bot] + [s(*corners_bot[0])[0]]
    fy = [s(*c)[1] for c in corners_bot] + [s(*corners_bot[0])[1]]
    ax.fill(fx, fy, color=floor_col, alpha=0.5, zorder=2)
    ax.plot(fx, fy, color=wall_col, linewidth=0.6, alpha=0.4, zorder=3)

    # Front walls (two visible faces)
    for face in [
        [corners_bot[0], corners_bot[1], corners_top[1], corners_top[0]],  # south
        [corners_bot[1], corners_bot[2], corners_top[2], corners_top[1]],  # east
    ]:
        px = [s(*p)[0] for p in face] + [s(*face[0])[0]]
        py = [s(*p)[1] for p in face] + [s(*face[0])[1]]
        ax.fill(px, py, color=FLOOR_COLOR, alpha=alpha, zorder=2)
        ax.plot(px, py, color=wall_col, linewidth=1.0, zorder=4)

    # Top face
    tx = [s(*c)[0] for c in corners_top] + [s(*corners_top[0])[0]]
    ty = [s(*c)[1] for c in corners_top] + [s(*corners_top[0])[1]]
    ax.fill(tx, ty, color="#0F0F28", alpha=0.7, zorder=3)
    ax.plot(tx, ty, color=wall_col, linewidth=1.0, alpha=0.7, zorder=4)

    # Vertical edges
    for c_b, c_t in zip(corners_bot, corners_top):
        bx, by = s(*c_b)
        tx2, ty2 = s(*c_t)
        ax.plot([bx, tx2], [by, ty2], color=wall_col, linewidth=0.9,
                alpha=0.6, zorder=4)

    # Room label (center of top face)
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    lx, ly = s(cx, cy, H + 0.1)
    if label:
        ax.text(lx, ly, label, ha="center", va="bottom",
                fontsize=5.5, color=LABEL_COLOR, fontweight="bold",
                fontfamily="monospace", zorder=10,
                bbox=dict(boxstyle="round,pad=0.15", facecolor="#020210",
                          alpha=0.7, edgecolor="none"))

# Draw ground grid
for gx in np.arange(0, 15, 1.0):
    for gy in np.arange(0, 11, 1.0):
        p1x, p1y = s(gx, gy, 0)
        p2x, p2y = s(gx+1, gy, 0)
        p3x, p3y = s(gx, gy+1, 0)
        ax3d.plot([p1x,p2x],[p1y,p2y], color=GRID_COLOR, lw=0.4, zorder=1)
        ax3d.plot([p1x,p3x],[p1y,p3y], color=GRID_COLOR, lw=0.4, zorder=1)

# Draw each room
colors_3d = ["#003A5C","#002A44","#003050","#003860","#002030","#002840","#003560","#002538"]
for i, (label, (x1,y1,x2,y2)) in enumerate(rooms_3d.items()):
    draw_room_3d(ax3d, x1, y1, x2, y2,
                 wall_col=WALL_COLOR,
                 floor_col=colors_3d[i % len(colors_3d)],
                 label=label)

# SketchUp-style axis indicator (bottom-left)
orig = s(0.2, 0.2, 0)
ax3d.annotate("", xy=s(1.2, 0.2, 0), xytext=orig,
              arrowprops=dict(arrowstyle="-|>", color="#FF4444", lw=1.5))
ax3d.annotate("", xy=s(0.2, 1.2, 0), xytext=orig,
              arrowprops=dict(arrowstyle="-|>", color="#44FF44", lw=1.5))
ax3d.annotate("", xy=s(0.2, 0.2, 1.0), xytext=orig,
              arrowprops=dict(arrowstyle="-|>", color="#4488FF", lw=1.5))
ex, ey = s(1.35, 0.2, 0);  ax3d.text(ex, ey, "X", color="#FF4444", fontsize=7, fontweight="bold", zorder=10)
ex, ey = s(0.2, 1.35, 0);  ax3d.text(ex, ey, "Y", color="#44FF44", fontsize=7, fontweight="bold", zorder=10)
ex, ey = s(0.2, 0.2, 1.15);ax3d.text(ex, ey, "Z", color="#4488FF", fontsize=7, fontweight="bold", zorder=10)

# Panel label & badge
ax3d.set_xlim(-1, 17); ax3d.set_ylim(-1, 16)
ax3d.text(0.5, 0.97, "INPUT: SketchUp 3D Model (.skp)",
          transform=ax3d.transAxes, ha="center", va="top",
          fontsize=10, color="#00BFFF", fontweight="bold", fontfamily="monospace",
          bbox=dict(boxstyle="round,pad=0.4", facecolor="#001020", edgecolor="#00BFFF", lw=1.5))

# Corner badge
ax3d.text(0.02, 0.03, "SketchUp  |  3D Perspective View",
          transform=ax3d.transAxes, ha="left", va="bottom",
          fontsize=7, color="#406080", fontfamily="monospace")

# Panel border
for spine in ax3d.spines.values():
    spine.set_edgecolor("#00BFFF")
    spine.set_linewidth(1.5)
    spine.set_visible(True)

# ─────────────────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════
#  MIDDLE — Arrow
# ══════════════════════════════════════════════════════════
# ─────────────────────────────────────────────────────────────────────────────
ax_mid.set_facecolor("#0D0D0D")
ax_mid.axis("off")
ax_mid.set_xlim(0, 1)
ax_mid.set_ylim(0, 1)

# Large bold arrow
ax_mid.annotate("", xy=(0.85, 0.5), xytext=(0.15, 0.5),
                xycoords="axes fraction", textcoords="axes fraction",
                arrowprops=dict(
                    arrowstyle="-|>",
                    color="#FFD700",
                    lw=4,
                    mutation_scale=28,
                ))

ax_mid.text(0.5, 0.38, "AUTO\nCONVERT", ha="center", va="top",
            fontsize=7, color="#FFD700", fontweight="bold",
            fontfamily="monospace", transform=ax_mid.transAxes)

# ─────────────────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════
#  RIGHT PANEL — Clean 2D Floor Plan
# ══════════════════════════════════════════════════════════
# ─────────────────────────────────────────────────────────────────────────────
ax2d.set_facecolor("white")
ax2d.set_xlim(-1.5, 18)
ax2d.set_ylim(-3.0, 13)
ax2d.set_aspect("equal")
ax2d.axis("off")

# Wall thickness
WT = 0.18

# ── Room geometry (same as DXF) ──
APT_X, APT_Y = 0.0, 0.0

FOY_X1,FOY_Y1,FOY_X2,FOY_Y2 = 0,0, 2.0,1.5
KIT_X1,KIT_Y1,KIT_X2,KIT_Y2 = 2.0,0, 5.0,3.5
LIV_X1,LIV_Y1,LIV_X2,LIV_Y2 = 0,1.5, 5.5,5.5
B2_X1,B2_Y1,B2_X2,B2_Y2     = 5.0,0, 6.8,1.5
B1_X1,B1_Y1,B1_X2,B1_Y2     = 5.0,2.0, 7.0,3.5
MBR_X1,MBR_Y1,MBR_X2,MBR_Y2 = 5.5,1.5, 9.5,5.0
BR2_X1,BR2_Y1,BR2_X2,BR2_Y2 = 9.5,1.5, 13.0,4.5
BAL_X1,BAL_Y1,BAL_X2,BAL_Y2 = 0,5.5, 3.0,6.7

ROOM_FILLS = {
    "LIVING ROOM":    ("#EFF6FF", (LIV_X1,LIV_Y1,LIV_X2,LIV_Y2)),
    "KITCHEN":        ("#FFF8EE", (KIT_X1,KIT_Y1,KIT_X2,KIT_Y2)),
    "MASTER BEDROOM": ("#F0FFF4", (MBR_X1,MBR_Y1,MBR_X2,MBR_Y2)),
    "BEDROOM 2":      ("#F5F0FF", (BR2_X1,BR2_Y1,BR2_X2,BR2_Y2)),
    "MASTER BATH":    ("#E8F4FD", (B1_X1,B1_Y1,B1_X2,B1_Y2)),
    "BATH 2":         ("#E8F4FD", (B2_X1,B2_Y1,B2_X2,B2_Y2)),
    "BALCONY":        ("#F0FAF0", (BAL_X1,BAL_Y1,BAL_X2,BAL_Y2)),
    "FOYER":          ("#FAFAFA", (FOY_X1,FOY_Y1,FOY_X2,FOY_Y2)),
}

def fill_room(ax, x1, y1, x2, y2, color):
    ax.add_patch(patches.Rectangle((x1,y1), x2-x1, y2-y1,
                 facecolor=color, edgecolor="none", zorder=1))

def draw_wall_rect(ax, x1, y1, x2, y2, lw=2.2, ec="#1A1A1A"):
    """Draw solid wall rectangle outline."""
    ax.add_patch(patches.Rectangle((x1,y1), x2-x1, y2-y1,
                 facecolor="none", edgecolor=ec, linewidth=lw, zorder=5))

def wall_line(ax, x1,y1,x2,y2, lw=2.2, color="#1A1A1A"):
    ax.plot([x1,x2],[y1,y2], color=color, lw=lw, solid_capstyle="round", zorder=5)

def draw_room_walls(ax, x1,y1,x2,y2):
    """Draw inner + outer wall lines for a room."""
    # outer
    draw_wall_rect(ax, x1-WT, y1-WT, x2+WT, y2+WT, lw=2.5, ec="#111")
    # inner
    draw_wall_rect(ax, x1, y1, x2, y2, lw=1.0, ec="#444")

# Fill rooms
for name,(color,rect) in ROOM_FILLS.items():
    fill_room(ax2d, *rect, color)

# Draw grid (light)
for gx in np.arange(-1, 14, 1.0):
    ax2d.plot([gx,gx],[-0.5,7.5], color="#DDDDDD", lw=0.4, linestyle="--", zorder=0)
for gy in np.arange(-0.5, 8, 1.0):
    ax2d.plot([-1,14],[gy,gy], color="#DDDDDD", lw=0.4, linestyle="--", zorder=0)

# Draw walls for each room
for name,(color,rect) in ROOM_FILLS.items():
    draw_room_walls(ax2d, *rect)

# ── DOORS (arc swing) ──
def draw_door_2d(ax, cx, cy, r, start_deg, end_deg, door_angle_deg):
    arc = Arc((cx,cy), 2*r, 2*r, angle=0,
              theta1=start_deg, theta2=end_deg,
              color="#007ACC", lw=1.4, zorder=7)
    ax2d.add_patch(arc)
    rad = np.radians(door_angle_deg)
    ax2d.plot([cx, cx+r*np.cos(rad)],[cy, cy+r*np.sin(rad)],
              color="#007ACC", lw=1.8, zorder=7)

draw_door_2d(ax2d, FOY_X1+0.5, FOY_Y1, 0.8, 0, 90, 90)       # foyer entry
draw_door_2d(ax2d, LIV_X1, LIV_Y1+0.5, 0.8, 270, 360, 0)     # living
draw_door_2d(ax2d, KIT_X1+0.5, KIT_Y2, 0.75, 0, 90, 90)      # kitchen
draw_door_2d(ax2d, MBR_X1, MBR_Y1+0.5, 0.8, 270, 360, 0)     # master bed
draw_door_2d(ax2d, B1_X1, B1_Y1+0.4, 0.6, 270, 360, 0)       # bath 1
draw_door_2d(ax2d, BR2_X1, BR2_Y1+0.5, 0.8, 270, 360, 0)     # bed 2
draw_door_2d(ax2d, B2_X1, B2_Y1+0.4, 0.6, 270, 360, 0)       # bath 2
draw_door_2d(ax2d, BAL_X1+0.5, BAL_Y1, 0.9, 0, 90, 90)       # balcony

# ── WINDOWS (3-line break) ──
def window_h_2d(ax, wx, wy, ww):
    offsets = [-0.06, 0, 0.06]
    for dy in offsets:
        ax.plot([wx, wx+ww],[wy+dy, wy+dy],
                color="#FFB300", lw=1.2, zorder=8)
    for xx in [wx, wx+ww]:
        ax.plot([xx,xx],[wy-0.12, wy+0.12], color="#FFB300", lw=1.2, zorder=8)

def window_v_2d(ax, wx, wy, wh):
    offsets = [-0.06, 0, 0.06]
    for dx in offsets:
        ax.plot([wx+dx, wx+dx],[wy, wy+wh],
                color="#FFB300", lw=1.2, zorder=8)
    for yy in [wy, wy+wh]:
        ax.plot([wx-0.12, wx+0.12],[yy,yy], color="#FFB300", lw=1.2, zorder=8)

window_h_2d(ax2d, LIV_X1+0.8, LIV_Y1, 2.2)
window_v_2d(ax2d, LIV_X1, LIV_Y1+1.3, 1.3)
window_h_2d(ax2d, MBR_X1+0.5, MBR_Y2, 1.8)
window_v_2d(ax2d, BR2_X2, BR2_Y1+0.4, 1.6)
window_h_2d(ax2d, KIT_X1+0.4, KIT_Y1, 1.3)
window_h_2d(ax2d, BAL_X1+0.3, BAL_Y2, 2.1)

# ── ROOM LABELS ──
room_labels = [
    ("LIVING ROOM",    "5.5 x 4.0 m",  (LIV_X1+LIV_X2)/2, (LIV_Y1+LIV_Y2)/2),
    ("KITCHEN",        "3.0 x 3.5 m",  (KIT_X1+KIT_X2)/2, (KIT_Y1+KIT_Y2)/2),
    ("MASTER\nBEDROOM","4.0 x 3.5 m",  (MBR_X1+MBR_X2)/2, (MBR_Y1+MBR_Y2)/2),
    ("BEDROOM 2",      "3.5 x 3.0 m",  (BR2_X1+BR2_X2)/2, (BR2_Y1+BR2_Y2)/2),
    ("MASTER\nBATH",   "2.0 x 1.5 m",  (B1_X1+B1_X2)/2,   (B1_Y1+B1_Y2)/2),
    ("BATH 2",         "1.8 x 1.5 m",  (B2_X1+B2_X2)/2,   (B2_Y1+B2_Y2)/2),
    ("BALCONY",        "3.0 x 1.2 m",  (BAL_X1+BAL_X2)/2, (BAL_Y1+BAL_Y2)/2),
    ("ENTRY /\nFOYER", "2.0 x 1.5 m",  (FOY_X1+FOY_X2)/2, (FOY_Y1+FOY_Y2)/2),
]

for name, size, cx, cy in room_labels:
    ax2d.text(cx, cy+0.12, name, ha="center", va="center",
              fontsize=5.8, fontweight="bold", color="#1A1A1A",
              fontfamily="sans-serif", zorder=9,
              multialignment="center")
    ax2d.text(cx, cy-0.22, size, ha="center", va="center",
              fontsize=4.8, color="#555555", fontfamily="monospace", zorder=9)

# ── DIMENSION LINES ──
DIM_COL = "#CC2200"
DIM_LW  = 0.9

def hdim_2d(ax, x1, x2, y, label):
    ax.annotate("", xy=(x2,y), xytext=(x1,y),
                arrowprops=dict(arrowstyle="<->", color=DIM_COL, lw=DIM_LW))
    ax.text((x1+x2)/2, y+0.12, label, ha="center", va="bottom",
            fontsize=4.5, color=DIM_COL, fontfamily="monospace", zorder=10)
    ax.plot([x1,x1],[y-0.08,y+0.08], color=DIM_COL, lw=0.8)
    ax.plot([x2,x2],[y-0.08,y+0.08], color=DIM_COL, lw=0.8)

def vdim_2d(ax, y1, y2, x, label):
    ax.annotate("", xy=(x,y2), xytext=(x,y1),
                arrowprops=dict(arrowstyle="<->", color=DIM_COL, lw=DIM_LW))
    ax.text(x-0.12, (y1+y2)/2, label, ha="right", va="center",
            fontsize=4.5, color=DIM_COL, fontfamily="monospace",
            rotation=90, zorder=10)
    ax.plot([x-0.08,x+0.08],[y1,y1], color=DIM_COL, lw=0.8)
    ax.plot([x-0.08,x+0.08],[y2,y2], color=DIM_COL, lw=0.8)

hdim_2d(ax2d, LIV_X1, LIV_X2, LIV_Y1-0.55, "5.5 m")
vdim_2d(ax2d, LIV_Y1, LIV_Y2, LIV_X1-0.55, "4.0 m")
hdim_2d(ax2d, KIT_X1, KIT_X2, KIT_Y1-0.55, "3.0 m")
vdim_2d(ax2d, KIT_Y1, KIT_Y2, KIT_X2+0.55, "3.5 m")
hdim_2d(ax2d, MBR_X1, MBR_X2, MBR_Y2+0.45, "4.0 m")
vdim_2d(ax2d, MBR_Y1, MBR_Y2, MBR_X2+0.55, "3.5 m")
hdim_2d(ax2d, BR2_X1, BR2_X2, BR2_Y2+0.45, "3.5 m")
vdim_2d(ax2d, BR2_Y1, BR2_Y2, BR2_X2+0.55, "3.0 m")
hdim_2d(ax2d, BAL_X1, BAL_X2, BAL_Y2+0.35, "3.0 m")

# ── FURNITURE (schematic, dashed blue) ──
FURN_COLOR = "#2255AA"
FURN_FILL  = "#EEF2FF"

def fbox(ax, x, y, w, h, label=""):
    ax.add_patch(patches.FancyBboxPatch((x,y), w, h,
                 boxstyle="round,pad=0.02",
                 facecolor=FURN_FILL, edgecolor=FURN_COLOR,
                 linewidth=0.8, linestyle="--", zorder=6))
    if label:
        ax.text(x+w/2, y+h/2, label, ha="center", va="center",
                fontsize=3.8, color=FURN_COLOR, fontfamily="monospace", zorder=7)

def fcircle(ax, cx, cy, r):
    ax.add_patch(plt.Circle((cx,cy), r, facecolor=FURN_FILL,
                 edgecolor=FURN_COLOR, linewidth=0.8, linestyle="--", zorder=6))

# Living
fbox(ax2d, LIV_X1+0.2, LIV_Y1+0.4, 2.0, 0.8, "SOFA")
fbox(ax2d, LIV_X1+0.2, LIV_Y1+1.2, 0.8, 1.0, "")
fbox(ax2d, LIV_X1+1.4, LIV_Y1+1.5, 0.8, 0.45, "TABLE")
fbox(ax2d, LIV_X2-1.6, LIV_Y1+0.2, 1.3, 0.35, "TV UNIT")

# Kitchen
fbox(ax2d, KIT_X1+0.1, KIT_Y1+0.1, KIT_X2-KIT_X1-0.2, 0.5, "COUNTER")
fbox(ax2d, KIT_X1+0.2, KIT_Y1+1.3, 1.2, 0.7, "DINING")

# Master bed
fbox(ax2d, MBR_X1+0.3, MBR_Y1+0.4, 1.5, 1.8, "BED")
fbox(ax2d, MBR_X2-1.1, MBR_Y1+0.15, 0.9, 0.45, "WARDROBE")

# Bed 2
fbox(ax2d, BR2_X1+0.25, BR2_Y1+0.3, 1.3, 1.7, "BED")
fbox(ax2d, BR2_X2-1.0, BR2_Y1+0.15, 0.85, 0.4, "WARDROBE")

# Baths
fbox(ax2d, B1_X1+0.1, B1_Y1+0.1, 0.45, 0.55, "WC")
fcircle(ax2d, B1_X1+1.4, B1_Y1+0.35, 0.18)
fbox(ax2d, B2_X1+0.1, B2_Y1+0.1, 0.45, 0.55, "WC")
fcircle(ax2d, B2_X1+1.2, B2_Y1+0.35, 0.18)

# ── NORTH ARROW ──
NA_CX, NA_CY = 15.5, 6.0
ax2d.add_patch(plt.Circle((NA_CX,NA_CY), 0.45,
               facecolor="none", edgecolor="#1A1A1A", lw=1.2, zorder=10))
ax2d.annotate("", xy=(NA_CX, NA_CY+0.6), xytext=(NA_CX, NA_CY),
              arrowprops=dict(arrowstyle="-|>", color="#1A1A1A", lw=2.0,
                              mutation_scale=12))
ax2d.plot([NA_CX, NA_CX-0.12],[NA_CY, NA_CY-0.22],
          color="#888", lw=1.2, zorder=10)
ax2d.plot([NA_CX, NA_CX+0.12],[NA_CY, NA_CY-0.22],
          color="#888", lw=1.2, zorder=10)
ax2d.text(NA_CX, NA_CY+0.68, "N", ha="center", va="bottom",
          fontsize=9, fontweight="bold", color="#1A1A1A", zorder=10)

# ── TITLE BLOCK (bottom of 2D panel) ──
tb_y = -2.5
ax2d.add_patch(patches.Rectangle((-1.2, tb_y), 16.5, 1.4,
               facecolor="#F8F8F8", edgecolor="#333", lw=1.5, zorder=8))
ax2d.plot([6.1, 6.1],[tb_y, tb_y+1.4], color="#333", lw=0.8, zorder=9)
ax2d.plot([-1.2, 15.3],[tb_y+0.7, tb_y+0.7], color="#333", lw=0.8, zorder=9)

title_entries = [
    ("PROJECT: Sample 2BHK Apartment",                   2.0, tb_y+1.05, 6.5),
    ("interior-design-3d-to-2d",                         10.0, tb_y+1.05, 6.5),
    ("SCALE: 1:50  |  DRAWN BY: interior-design-3d-to-2d", 2.0, tb_y+0.35, 5.5),
    ("DATE: March 2026  |  SHEET: A-001",                10.0, tb_y+0.35, 5.5),
]
for text, cx, cy, fs in title_entries:
    ax2d.text(cx, cy, text, ha="center", va="center",
              fontsize=4.8, color="#111", fontfamily="monospace", zorder=10)

# Drawing title
ax2d.text((LIV_X1+BR2_X2)/2, -1.7,
          "FLOOR PLAN — SAMPLE 2BHK APARTMENT  (~1,200 SQFT)",
          ha="center", va="center", fontsize=7.5, fontweight="bold",
          color="#1A1A1A", zorder=10)

# Panel label
ax2d.text(0.5, 0.97, "OUTPUT: AutoCAD Floor Plan (.dxf)",
          transform=ax2d.transAxes, ha="center", va="top",
          fontsize=10, color="#007ACC", fontweight="bold", fontfamily="monospace",
          bbox=dict(boxstyle="round,pad=0.4", facecolor="#E8F4FD",
                    edgecolor="#007ACC", lw=1.5))

ax2d.text(0.02, 0.03, "AutoCAD DXF  |  1:50 Scale  |  All dims in meters",
          transform=ax2d.transAxes, ha="left", va="bottom",
          fontsize=7, color="#888888", fontfamily="monospace")

# Panel border
for spine in ax2d.spines.values():
    spine.set_edgecolor("#007ACC")
    spine.set_linewidth(1.5)
    spine.set_visible(True)

# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
fig.text(0.5, 0.025,
         "interior-design-3d-to-2d  |  Automated 3D-to-2D Conversion  |  "
         "Supports: SketchUp (.skp), Revit (.rvt), Rhino (.3dm)  ->  AutoCAD (.dxf), PDF, PNG",
         ha="center", va="center", fontsize=8, color="#505070",
         fontfamily="monospace")

# ─────────────────────────────────────────────────────────────────────────────
# SAVE
# ─────────────────────────────────────────────────────────────────────────────
out_path = "docs/before_after.png"
fig.savefig(out_path, dpi=DPI, bbox_inches="tight",
            facecolor=fig.get_facecolor())
plt.close(fig)
print(f"PNG saved to: {out_path}")

# Verify file size
size_kb = os.path.getsize(out_path) / 1024
print(f"File size: {size_kb:.1f} KB  ({size_kb/1024:.2f} MB)")
