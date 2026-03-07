"""
Pitch Deck Generator — interior-design-3d-to-2d
Premium A4 landscape PDF using ReportLab
"""

import os
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, white, black
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
import math

# ── Page setup ──────────────────────────────────────────────────────────────
PAGE_W, PAGE_H = landscape(A4)   # 841.89 x 595.28 pt

# ── Brand colours ───────────────────────────────────────────────────────────
NAVY      = HexColor("#0D1117")
DARK_GRAY = HexColor("#1A1A2E")
NAVY2     = HexColor("#111927")   # slightly lighter navy for card bg
CARD_BG   = HexColor("#161D2B")
CARD_BG2  = HexColor("#1C2333")
AMBER     = HexColor("#F0A500")
AMBER_DIM = HexColor("#C88A00")
GOLD      = HexColor("#FFD166")
WHITE     = HexColor("#FFFFFF")
LGRAY     = HexColor("#A0A0B0")
MGRAY     = HexColor("#6B7280")
DGRAY     = HexColor("#2A3244")
GREEN     = HexColor("#22C55E")
BLUE_ACC  = HexColor("#3B82F6")

OUTPUT_PATH = "docs/pitch_deck.pdf"
BEFORE_AFTER = "docs/before_after.png"

# ── Helper utilities ─────────────────────────────────────────────────────────

def draw_bg(c, color=None):
    """Fill entire page with background color."""
    c.setFillColor(color or NAVY)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)


def draw_amber_header_line(c, y=None):
    """Thin amber accent line near top of every slide."""
    if y is None:
        y = PAGE_H - 22
    c.setStrokeColor(AMBER)
    c.setLineWidth(2.2)
    c.line(30, y, PAGE_W - 30, y)


def draw_logo(c, x=36, y=None):
    """Small amber logo text top-left."""
    if y is None:
        y = PAGE_H - 17
    c.setFillColor(AMBER)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, "i3d\u21922d")


def draw_slide_number(c, n, total=7):
    """Slide number bottom-right."""
    c.setFillColor(MGRAY)
    c.setFont("Helvetica", 8)
    label = f"{n} / {total}"
    c.drawRightString(PAGE_W - 28, 14, label)


def draw_footer_line(c):
    """Subtle footer separator line."""
    c.setStrokeColor(DGRAY)
    c.setLineWidth(0.6)
    c.line(30, 28, PAGE_W - 30, 28)


def rounded_rect(c, x, y, w, h, r=8, fill_color=None, stroke_color=None, stroke_width=1.5):
    """Draw a rounded rectangle."""
    from reportlab.graphics.shapes import Rect
    p = c.beginPath()
    p.moveTo(x + r, y)
    p.lineTo(x + w - r, y)
    p.arcTo(x + w - 2*r, y, x + w, y + 2*r, startAng=-90, extent=90)
    p.lineTo(x + w, y + h - r)
    p.arcTo(x + w - 2*r, y + h - 2*r, x + w, y + h, startAng=0, extent=90)
    p.lineTo(x + r, y + h)
    p.arcTo(x, y + h - 2*r, x + 2*r, y + h, startAng=90, extent=90)
    p.lineTo(x, y + r)
    p.arcTo(x, y, x + 2*r, y + 2*r, startAng=180, extent=90)
    p.close()
    if fill_color:
        c.setFillColor(fill_color)
    if stroke_color:
        c.setStrokeColor(stroke_color)
        c.setLineWidth(stroke_width)
    c.drawPath(p, fill=1 if fill_color else 0, stroke=1 if stroke_color else 0)


def draw_text_wrapped(c, text, x, y, max_width, font="Helvetica", size=10,
                      color=WHITE, leading=None, align="left"):
    """Very lightweight word-wrap for short strings."""
    if leading is None:
        leading = size * 1.45
    words = text.split()
    lines = []
    current = ""
    c.setFont(font, size)
    for w in words:
        test = (current + " " + w).strip()
        if c.stringWidth(test, font, size) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    c.setFillColor(color)
    for i, line in enumerate(lines):
        ty = y - i * leading
        if align == "center":
            c.drawCentredString(x + max_width / 2, ty, line)
        elif align == "right":
            c.drawRightString(x + max_width, ty, line)
        else:
            c.drawString(x, ty, line)
    return y - len(lines) * leading


def gradient_rect(c, x, y, w, h, color1, color2, steps=40, vertical=True):
    """Simulate gradient by drawing thin strips."""
    for i in range(steps):
        t = i / steps
        r = color1.red   + t * (color2.red   - color1.red)
        g = color1.green + t * (color2.green - color1.green)
        b = color1.blue  + t * (color2.blue  - color1.blue)
        c.setFillColorRGB(r, g, b)
        if vertical:
            strip_h = h / steps
            c.rect(x, y + i * strip_h, w, strip_h + 0.5, fill=1, stroke=0)
        else:
            strip_w = w / steps
            c.rect(x + i * strip_w, y, strip_w + 0.5, h, fill=1, stroke=0)


def draw_diamond(c, cx, cy, size, fill_color):
    """Draw a small diamond shape."""
    p = c.beginPath()
    p.moveTo(cx, cy + size)
    p.lineTo(cx + size, cy)
    p.lineTo(cx, cy - size)
    p.lineTo(cx - size, cy)
    p.close()
    c.setFillColor(fill_color)
    c.drawPath(p, fill=1, stroke=0)


# ═══════════════════════════════════════════════════════════════════════════
#  SLIDE 1 — Cover
# ═══════════════════════════════════════════════════════════════════════════

def slide_cover(c):
    draw_bg(c, NAVY)

    # Background gradient overlay (top third)
    gradient_rect(c, 0, PAGE_H * 0.5, PAGE_W, PAGE_H * 0.5,
                  HexColor("#0D1117"), HexColor("#131B2E"), steps=30, vertical=True)

    # Decorative large circle top-right (faint)
    c.setFillColor(HexColor("#1A2540"))
    c.circle(PAGE_W - 80, PAGE_H + 30, 200, fill=1, stroke=0)
    c.setFillColor(HexColor("#0F1923"))
    c.circle(PAGE_W - 60, PAGE_H + 10, 140, fill=1, stroke=0)

    # Amber header line
    draw_amber_header_line(c)
    draw_logo(c)

    # ── Amber vertical accent bar (left) ───────────────────────────────────
    c.setFillColor(AMBER)
    c.rect(30, 80, 5, PAGE_H - 120, fill=1, stroke=0)

    # ── Main title ─────────────────────────────────────────────────────────
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 38)
    c.drawString(58, PAGE_H - 100, "interior-design-3d-to-2d")

    # Amber underline beneath title
    title_w = c.stringWidth("interior-design-3d-to-2d", "Helvetica-Bold", 38)
    c.setStrokeColor(AMBER)
    c.setLineWidth(3)
    c.line(58, PAGE_H - 108, 58 + title_w, PAGE_H - 108)

    # ── Subtitle ───────────────────────────────────────────────────────────
    c.setFillColor(LGRAY)
    c.setFont("Helvetica", 15)
    c.drawString(58, PAGE_H - 140,
                 "Automated 3D to 2D CAD Conversion for Architecture & Interior Design Firms")

    # ── Tagline box ────────────────────────────────────────────────────────
    tag_y = PAGE_H - 195
    rounded_rect(c, 55, tag_y - 14, 520, 36, r=6,
                 fill_color=HexColor("#1C2D14"), stroke_color=AMBER, stroke_width=1.2)
    c.setFillColor(AMBER)
    c.setFont("Helvetica-BoldOblique", 14)
    c.drawString(75, tag_y + 4, "\u26a1  From SketchUp model to construction-ready drawings. In seconds.")

    # ── Stats row ─────────────────────────────────────────────────────────
    stats = [
        ("< 5 sec", "conversion time"),
        ("100%", "AutoCAD compatible"),
        ("4-8 hrs", "saved per project"),
    ]
    sx = 58
    sy = PAGE_H - 275
    for val, lbl in stats:
        c.setFillColor(DGRAY)
        c.rect(sx, sy - 8, 140, 52, fill=1, stroke=0)
        c.setStrokeColor(AMBER)
        c.setLineWidth(1)
        c.rect(sx, sy - 8, 140, 52, fill=0, stroke=1)
        c.setFillColor(AMBER)
        c.setFont("Helvetica-Bold", 20)
        c.drawString(sx + 12, sy + 24, val)
        c.setFillColor(LGRAY)
        c.setFont("Helvetica", 9)
        c.drawString(sx + 12, sy + 8, lbl)
        sx += 156

    # ── Decorative right-side graphic ──────────────────────────────────────
    # Isometric-style grid dots
    gx0, gy0 = PAGE_W - 280, 60
    c.setFillColor(HexColor("#1E2D45"))
    for row in range(8):
        for col in range(12):
            dot_x = gx0 + col * 22 + (row % 2) * 11
            dot_y = gy0 + row * 14
            c.circle(dot_x, dot_y, 1.8, fill=1, stroke=0)

    # Large arrow →
    c.setFillColor(AMBER)
    c.setFont("Helvetica-Bold", 60)
    c.drawCentredString(PAGE_W - 110, PAGE_H / 2 - 10, "\u2192")

    # "3D" label
    c.setFillColor(HexColor("#3B82F6"))
    c.setFont("Helvetica-Bold", 22)
    c.drawString(PAGE_W - 260, PAGE_H / 2 + 20, "3D")
    c.setFillColor(WHITE)
    c.setFont("Helvetica", 9)
    c.drawString(PAGE_W - 260, PAGE_H / 2 + 6, "SketchUp Model")

    # "2D" label
    c.setFillColor(GREEN)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(PAGE_W - 68, PAGE_H / 2 + 20, "2D")
    c.setFillColor(WHITE)
    c.setFont("Helvetica", 9)
    c.drawString(PAGE_W - 78, PAGE_H / 2 + 6, "CAD Drawings")

    # ── Bottom bar ─────────────────────────────────────────────────────────
    c.setFillColor(DGRAY)
    c.rect(0, 0, PAGE_W, 44, fill=1, stroke=0)
    c.setStrokeColor(AMBER)
    c.setLineWidth(1.5)
    c.line(0, 44, PAGE_W, 44)

    c.setFillColor(LGRAY)
    c.setFont("Helvetica", 10)
    c.drawString(36, 16, "Prepared for:  \u25a0  [Architecture Firm Name]")
    c.setFillColor(MGRAY)
    c.drawRightString(PAGE_W - 36, 16, "March 2026  |  Confidential")

    draw_slide_number(c, 1)


# ═══════════════════════════════════════════════════════════════════════════
#  SLIDE 2 — The Problem
# ═══════════════════════════════════════════════════════════════════════════

def slide_problem(c):
    draw_bg(c, NAVY)
    draw_amber_header_line(c)
    draw_logo(c)
    draw_footer_line(c)

    # Section label
    c.setFillColor(HexColor("#FF4444"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(36, PAGE_H - 40, "PROBLEM")

    # Title
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 28)
    c.drawString(36, PAGE_H - 68, "The Manual Drafting Problem")

    # Amber underline
    c.setStrokeColor(AMBER)
    c.setLineWidth(2.5)
    c.line(36, PAGE_H - 76, 380, PAGE_H - 76)

    # ── 3 pain-point boxes ─────────────────────────────────────────────────
    pain_points = [
        ("01", "Time Drain",
         "Every 3D model has to be manually redrawn as 2D —\ncosting 4-8 hours per project",
         HexColor("#FF6B35")),
        ("02", "Human Error",
         "Human error in transcription leads to\ndimension mismatches and costly rework",
         HexColor("#F0A500")),
        ("03", "Wasted Talent",
         "Junior draughtsmen spend 60% of time on\nrepetitive conversion work instead of design",
         HexColor("#EF4444")),
    ]

    bx = 36
    bw = (PAGE_W - 36 * 2 - 24) / 3
    by = PAGE_H - 230
    bh = 140

    for num, title, body, accent in pain_points:
        # Card background
        rounded_rect(c, bx, by, bw, bh, r=8,
                     fill_color=CARD_BG, stroke_color=accent, stroke_width=1.8)

        # Accent top bar
        c.setFillColor(accent)
        # Top-left accent dot
        c.circle(bx + 20, by + bh - 20, 14, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(bx + 20, by + bh - 24, num)

        # Title
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(bx + 42, by + bh - 24, title)

        # Body text
        c.setFillColor(LGRAY)
        c.setFont("Helvetica", 10.5)
        lines = body.split("\n")
        ty = by + bh - 50
        for line in lines:
            c.drawString(bx + 14, ty, line)
            ty -= 16

        # Icon line
        c.setStrokeColor(accent)
        c.setLineWidth(0.8)
        c.line(bx + 14, by + 32, bx + bw - 14, by + 32)

        bx += bw + 12

    # ── Bottom stat banner ─────────────────────────────────────────────────
    stat_y = PAGE_H - 280
    rounded_rect(c, 36, stat_y - 22, PAGE_W - 72, 44, r=6,
                 fill_color=HexColor("#1A0A00"), stroke_color=AMBER, stroke_width=2)

    c.setFillColor(AMBER)
    c.setFont("Helvetica-Bold", 11)
    stat_text = "\u26a0  Average architecture firm loses 120+ hours/month to manual 2D drafting"
    tw = c.stringWidth(stat_text, "Helvetica-Bold", 11)
    c.drawCentredString(PAGE_W / 2, stat_y - 4, stat_text)

    draw_slide_number(c, 2)


# ═══════════════════════════════════════════════════════════════════════════
#  SLIDE 3 — The Solution
# ═══════════════════════════════════════════════════════════════════════════

def slide_solution(c):
    draw_bg(c, NAVY)
    draw_amber_header_line(c)
    draw_logo(c)
    draw_footer_line(c)

    c.setFillColor(GREEN)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(36, PAGE_H - 40, "SOLUTION")

    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 28)
    c.drawString(36, PAGE_H - 68, "One Command. Construction-Ready Drawings.")

    c.setStrokeColor(AMBER)
    c.setLineWidth(2.5)
    c.line(36, PAGE_H - 76, 460, PAGE_H - 76)

    # ── 3-step pipeline flow ───────────────────────────────────────────────
    steps = [
        ("01", "Export .dae\nfrom SketchUp", "\U0001f4e4", HexColor("#3B82F6")),
        ("02", "Run\nextract.py",   "\u2699",  AMBER),
        ("03", "Receive\n.dxf files",  "\u2705", GREEN),
    ]

    step_w = 160
    arrow_w = 60
    total_flow = len(steps) * step_w + (len(steps) - 1) * arrow_w
    fx = (PAGE_W - total_flow) / 2
    fy = PAGE_H - 205

    for i, (num, label, icon, color) in enumerate(steps):
        # Box
        rounded_rect(c, fx, fy - 40, step_w, 80, r=10,
                     fill_color=CARD_BG2, stroke_color=color, stroke_width=2)

        # Step number circle
        c.setFillColor(color)
        c.circle(fx + 22, fy + 28, 14, fill=1, stroke=0)
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(fx + 22, fy + 24, num)

        # Icon
        c.setFillColor(color)
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(fx + step_w / 2, fy + 14, icon)

        # Label
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 11)
        lines = label.split("\n")
        ly = fy - 8
        for line in lines:
            c.drawCentredString(fx + step_w / 2, ly, line)
            ly -= 14

        if i < len(steps) - 1:
            # Arrow connector
            ax = fx + step_w + 10
            ay = fy + 4
            c.setFillColor(AMBER)
            c.setFont("Helvetica-Bold", 26)
            c.drawCentredString(ax + arrow_w / 2, ay, "\u27a1")

        fx += step_w + arrow_w

    # ── Feature list (2 columns) ───────────────────────────────────────────
    feat_y = PAGE_H - 290
    c.setFillColor(LGRAY)
    c.setFont("Helvetica", 9.5)
    c.drawString(36, feat_y + 12, "WHAT YOU GET:")

    features_left = [
        "Floor plans with auto-dimensions",
        "North, South, East, West elevations",
        "Section cuts at any height",
    ]
    features_right = [
        "Correct sill & lintel heights",
        "Room labels & title block",
        "Opens in AutoCAD, FreeCAD, ArchiCAD",
    ]

    col1_x = 36
    col2_x = PAGE_W / 2 + 10
    fy2 = feat_y - 8
    row_h = 26

    for feat in features_left:
        rounded_rect(c, col1_x, fy2 - 18, PAGE_W / 2 - 56, 24, r=5,
                     fill_color=CARD_BG)
        c.setFillColor(AMBER)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(col1_x + 10, fy2 - 7, "\u2714")
        c.setFillColor(WHITE)
        c.setFont("Helvetica", 10)
        c.drawString(col1_x + 26, fy2 - 7, feat)
        fy2 -= row_h

    fy2 = feat_y - 8
    for feat in features_right:
        rounded_rect(c, col2_x, fy2 - 18, PAGE_W / 2 - 56, 24, r=5,
                     fill_color=CARD_BG)
        c.setFillColor(AMBER)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(col2_x + 10, fy2 - 7, "\u2714")
        c.setFillColor(WHITE)
        c.setFont("Helvetica", 10)
        c.drawString(col2_x + 26, fy2 - 7, feat)
        fy2 -= row_h

    draw_slide_number(c, 3)


# ═══════════════════════════════════════════════════════════════════════════
#  SLIDE 4 — Before / After
# ═══════════════════════════════════════════════════════════════════════════

def slide_before_after(c, img_path):
    draw_bg(c, DARK_GRAY)
    draw_amber_header_line(c)
    draw_logo(c)
    draw_footer_line(c)

    c.setFillColor(AMBER)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(36, PAGE_H - 40, "SAMPLE OUTPUT")

    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 26)
    c.drawString(36, PAGE_H - 68, "Real Output \u2014 2BHK Apartment")

    c.setStrokeColor(AMBER)
    c.setLineWidth(2.5)
    c.line(36, PAGE_H - 76, 360, PAGE_H - 76)

    # ── Embed image ────────────────────────────────────────────────────────
    img_x = 36
    img_y = 50
    img_w = PAGE_W - 72
    img_h = PAGE_H - 145

    # Border / frame for image
    rounded_rect(c, img_x - 4, img_y - 4, img_w + 8, img_h + 8, r=8,
                 fill_color=HexColor("#0A0A1A"), stroke_color=AMBER, stroke_width=1.5)

    if os.path.exists(img_path):
        try:
            c.drawImage(img_path, img_x, img_y, width=img_w, height=img_h,
                        preserveAspectRatio=True, anchor='c', mask='auto')
        except Exception as e:
            c.setFillColor(MGRAY)
            c.setFont("Helvetica", 11)
            c.drawCentredString(PAGE_W / 2, PAGE_H / 2, f"[Image load error: {e}]")
    else:
        c.setFillColor(MGRAY)
        c.setFont("Helvetica", 11)
        c.drawCentredString(PAGE_W / 2, PAGE_H / 2, "[before_after.png not found]")

    # Caption strip at bottom
    c.setFillColor(HexColor("#0D1117CC"))  # semi-transparent (not supported in PDF but used as color)
    # Use solid overlay instead
    c.setFillColor(HexColor("#0D1117"))
    c.rect(img_x, img_y, img_w, 22, fill=1, stroke=0)

    c.setFillColor(LGRAY)
    c.setFont("Helvetica", 9)
    c.drawString(img_x + 10, img_y + 7,
                 "Left: SketchUp 3D model   |   Right: Auto-generated floor plan DXF")

    c.setFillColor(AMBER)
    c.setFont("Helvetica-BoldOblique", 9)
    c.drawRightString(img_x + img_w - 10, img_y + 7,
                      "Sample generated in 3.2 seconds on a standard MacBook")

    draw_slide_number(c, 4)


# ═══════════════════════════════════════════════════════════════════════════
#  SLIDE 5 — Pricing
# ═══════════════════════════════════════════════════════════════════════════

def slide_pricing(c):
    draw_bg(c, NAVY)
    draw_amber_header_line(c)
    draw_logo(c)
    draw_footer_line(c)

    c.setFillColor(AMBER)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(36, PAGE_H - 40, "PRICING")

    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 28)
    c.drawString(36, PAGE_H - 68, "Simple Per-Project Pricing")

    c.setStrokeColor(AMBER)
    c.setLineWidth(2.5)
    c.line(36, PAGE_H - 76, 360, PAGE_H - 76)

    # ── 3 Pricing tiers ───────────────────────────────────────────────────
    tiers = [
        {
            "name": "STARTER",
            "volume": "1-10 projects/month",
            "price": "\u20b9 499",
            "per": "per project",
            "featured": False,
            "border": AMBER,
            "bg": CARD_BG,
            "features": [
                "Floor plan + 4 elevations",
                "DXF + PDF output",
                "Email delivery within 1 hour",
                "Up to 5 rooms per model",
            ],
        },
        {
            "name": "STUDIO",
            "volume": "11-30 projects/month",
            "price": "\u20b9 349",
            "per": "per project",
            "featured": True,
            "border": GOLD,
            "bg": HexColor("#1C1A00"),
            "features": [
                "Everything in Starter",
                "Section cuts included",
                "Same-day batch processing",
                "Up to 15 rooms per model",
                "Priority support",
            ],
        },
        {
            "name": "FIRM",
            "volume": "30+ projects/month",
            "price": "\u20b9 249",
            "per": "per project",
            "featured": False,
            "border": LGRAY,
            "bg": CARD_BG,
            "features": [
                "Everything in Studio",
                "Dedicated pipeline on your server",
                "Unlimited rooms",
                "Custom title block & templates",
                "Monthly invoice",
            ],
        },
    ]

    tw = (PAGE_W - 36 * 2 - 24) / 3
    tx = 36
    ty_top = PAGE_H - 92
    th = 240

    for tier in tiers:
        is_feat = tier["featured"]
        bg = tier["bg"]
        border = tier["border"]

        if is_feat:
            # Slightly taller for featured
            box_y = ty_top - th - 14
            box_h = th + 14
            # Glow effect (outer ring)
            rounded_rect(c, tx - 3, box_y - 3, tw + 6, box_h + 6, r=11,
                         fill_color=None, stroke_color=GOLD, stroke_width=2.5)
        else:
            box_y = ty_top - th
            box_h = th

        rounded_rect(c, tx, box_y, tw, box_h, r=9, fill_color=bg,
                     stroke_color=border, stroke_width=1.8)

        header_h = 46 if not is_feat else 52
        # Header band
        rounded_rect(c, tx, box_y + box_h - header_h, tw, header_h, r=9,
                     fill_color=border if is_feat else HexColor("#1A2333"))
        # Cover bottom radius of header
        c.setFillColor(border if is_feat else HexColor("#1A2333"))
        c.rect(tx, box_y + box_h - header_h, tw, header_h // 2, fill=1, stroke=0)

        # FEATURED badge
        if is_feat:
            badge_x = tx + tw / 2
            badge_y = box_y + box_h + 6
            rounded_rect(c, badge_x - 44, badge_y - 9, 88, 20, r=10,
                         fill_color=GOLD)
            c.setFillColor(NAVY)
            c.setFont("Helvetica-Bold", 9)
            c.drawCentredString(badge_x, badge_y + 4, "\u2605  MOST POPULAR")

        # Tier name
        name_color = NAVY if is_feat else WHITE
        c.setFillColor(name_color)
        c.setFont("Helvetica-Bold", 13)
        c.drawCentredString(tx + tw / 2, box_y + box_h - 20, tier["name"])

        # Volume
        c.setFillColor(NAVY if is_feat else LGRAY)
        c.setFont("Helvetica", 8.5)
        c.drawCentredString(tx + tw / 2, box_y + box_h - 34, tier["volume"])

        # Price
        c.setFillColor(AMBER if not is_feat else GOLD)
        c.setFont("Helvetica-Bold", 28)
        c.drawCentredString(tx + tw / 2, box_y + box_h - header_h - 36, tier["price"])

        # Per
        c.setFillColor(LGRAY)
        c.setFont("Helvetica", 9)
        c.drawCentredString(tx + tw / 2, box_y + box_h - header_h - 50, tier["per"])

        # Divider
        c.setStrokeColor(DGRAY)
        c.setLineWidth(0.6)
        c.line(tx + 14, box_y + box_h - header_h - 60,
               tx + tw - 14, box_y + box_h - header_h - 60)

        # Features
        fy = box_y + box_h - header_h - 78
        for feat in tier["features"]:
            c.setFillColor(AMBER if not is_feat else GOLD)
            c.setFont("Helvetica-Bold", 9)
            c.drawString(tx + 16, fy, "\u2714")
            c.setFillColor(WHITE)
            c.setFont("Helvetica", 9)
            c.drawString(tx + 30, fy, feat)
            fy -= 17

        tx += tw + 12

    # ── Footer note ───────────────────────────────────────────────────────
    note_y = 36
    c.setFillColor(DGRAY)
    c.rect(36, note_y - 6, PAGE_W - 72, 22, fill=1, stroke=0)
    c.setFillColor(LGRAY)
    c.setFont("Helvetica", 9)
    c.drawCentredString(PAGE_W / 2, note_y + 4,
                        "All tiers include: Open-source core, no vendor lock-in. You own the output.")

    draw_slide_number(c, 5)


# ═══════════════════════════════════════════════════════════════════════════
#  SLIDE 6 — Why Us
# ═══════════════════════════════════════════════════════════════════════════

def slide_why_us(c):
    draw_bg(c, NAVY)
    draw_amber_header_line(c)
    draw_logo(c)
    draw_footer_line(c)

    c.setFillColor(BLUE_ACC)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(36, PAGE_H - 40, "WHY US")

    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 28)
    c.drawString(36, PAGE_H - 68, "Built for How Architects Actually Work")

    c.setStrokeColor(AMBER)
    c.setLineWidth(2.5)
    c.line(36, PAGE_H - 76, 440, PAGE_H - 76)

    points = [
        ("\U0001f4bb", "No Learning Curve",
         "No new software to learn — works with your existing SketchUp workflow",
         HexColor("#3B82F6")),
        ("\U0001f513", "Open Source Core",
         "Open-source core — audit the code, self-host if needed",
         GREEN),
        ("\u2601", "Runs Anywhere",
         "Runs on Mac Mini, Windows PC, or cloud — your choice",
         AMBER),
        ("\U0001f3d7", "Built by Domain Experts",
         "Built by developers who've worked with architecture firms — not generic SaaS",
         HexColor("#A855F7")),
    ]

    # 2x2 grid layout
    bw = (PAGE_W - 36 * 2 - 20) / 2
    bh = 105
    positions = [
        (36, PAGE_H - 205),
        (36 + bw + 20, PAGE_H - 205),
        (36, PAGE_H - 205 - bh - 16),
        (36 + bw + 20, PAGE_H - 205 - bh - 16),
    ]

    for (px, py), (icon, title, body, color) in zip(positions, points):
        # Card
        rounded_rect(c, px, py, bw, bh, r=9,
                     fill_color=CARD_BG, stroke_color=DGRAY, stroke_width=1)

        # Left color bar
        c.setFillColor(color)
        c.rect(px, py, 5, bh, fill=1, stroke=0)
        # Re-draw top-left radius mask
        rounded_rect(c, px, py + bh - 12, 12, 12, r=0,
                     fill_color=CARD_BG)
        # Just use solid bar cleanly
        c.setFillColor(color)
        c.rect(px, py, 5, bh, fill=1, stroke=0)

        # Icon circle
        c.setFillColor(color)
        c.circle(px + 30, py + bh - 26, 16, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(px + 30, py + bh - 30, icon)

        # Title
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(px + 54, py + bh - 24, title)

        # Body text
        draw_text_wrapped(c, body, px + 14, py + bh - 50,
                          bw - 22, font="Helvetica", size=10,
                          color=LGRAY, leading=15)

        # Bottom accent line
        c.setStrokeColor(color)
        c.setLineWidth(1)
        c.line(px + 14, py + 14, px + bw - 14, py + 14)

    draw_slide_number(c, 6)


# ═══════════════════════════════════════════════════════════════════════════
#  SLIDE 7 — CTA / Next Steps
# ═══════════════════════════════════════════════════════════════════════════

def slide_cta(c):
    draw_bg(c, NAVY)

    # Large decorative gradient circle background
    gradient_rect(c, 0, 0, PAGE_W, PAGE_H,
                  NAVY, HexColor("#0A1929"), steps=30, vertical=True)

    # Decorative radial rings (simulated with concentric circles)
    cx_r, cy_r = PAGE_W * 0.72, PAGE_H * 0.5
    for r, alpha in [(200, "#0F1E30"), (155, "#132033"), (110, "#172438"),
                     (70, "#1B283D")]:
        c.setFillColor(HexColor(alpha))
        c.circle(cx_r, cy_r, r, fill=1, stroke=0)

    draw_amber_header_line(c)
    draw_logo(c)
    draw_footer_line(c)

    c.setFillColor(AMBER)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(36, PAGE_H - 40, "NEXT STEPS")

    # Title
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 30)
    c.drawString(36, PAGE_H - 72, "Let's Start With One Project")

    c.setStrokeColor(AMBER)
    c.setLineWidth(3)
    c.line(36, PAGE_H - 80, 370, PAGE_H - 80)

    # Body paragraph
    body = (
        "Send us any SketchUp model. We'll convert it to a complete 2D drawing set — "
        "free. No commitment.\nIf you like what you see, we'll discuss a monthly arrangement "
        "that works for your firm's volume."
    )
    c.setFillColor(LGRAY)
    c.setFont("Helvetica", 12)
    lines = body.split("\n")
    ty = PAGE_H - 108
    for line in lines:
        c.drawString(36, ty, line)
        ty -= 18

    # ── Contact info box ──────────────────────────────────────────────────
    contact_x = 36
    contact_y = PAGE_H - 230
    contact_w = 360
    contact_h = 100

    rounded_rect(c, contact_x, contact_y, contact_w, contact_h, r=10,
                 fill_color=CARD_BG, stroke_color=AMBER, stroke_width=1.5)

    c.setFillColor(AMBER)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(contact_x + 16, contact_y + contact_h - 18, "CONTACT")

    c.setStrokeColor(DGRAY)
    c.setLineWidth(0.6)
    c.line(contact_x + 16, contact_y + contact_h - 24,
           contact_x + contact_w - 16, contact_y + contact_h - 24)

    contact_items = [
        ("\u2709", "dk-yo@nebula.me"),
        ("\u2316", "github.com/dk001-ui/interior-design-3d-to-2d"),
        ("\u25b6", "Free trial: Send your .skp or .dae file to get started"),
    ]

    iy = contact_y + contact_h - 42
    for icon, text in contact_items:
        c.setFillColor(AMBER)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(contact_x + 16, iy, icon)
        c.setFillColor(WHITE)
        c.setFont("Helvetica", 9.5)
        c.drawString(contact_x + 32, iy, text)
        iy -= 18

    # ── CTA Button ────────────────────────────────────────────────────────
    btn_x = 36
    btn_y = contact_y - 56
    btn_w = 360
    btn_h = 44

    # Glow shadow
    c.setFillColor(HexColor("#3D2200"))
    c.roundRect(btn_x + 3, btn_y - 3, btn_w, btn_h, 8, fill=1, stroke=0)

    # Button fill
    rounded_rect(c, btn_x, btn_y, btn_w, btn_h, r=8,
                 fill_color=AMBER, stroke_color=AMBER_DIM, stroke_width=1)

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(btn_x + btn_w / 2, btn_y + 16,
                        "\u25b6  REQUEST FREE SAMPLE CONVERSION")

    # ── Right panel stats ─────────────────────────────────────────────────
    stats = [
        ("100%", "Free first project"),
        ("< 5 sec", "Conversion time"),
        ("0", "Commitments required"),
    ]
    rx = PAGE_W - 290
    ry = PAGE_H - 135
    for val, label in stats:
        rounded_rect(c, rx, ry - 38, 245, 50, r=8,
                     fill_color=CARD_BG2, stroke_color=DGRAY, stroke_width=1)
        c.setFillColor(GOLD)
        c.setFont("Helvetica-Bold", 22)
        c.drawString(rx + 16, ry + 4, val)
        c.setFillColor(LGRAY)
        c.setFont("Helvetica", 10)
        c.drawString(rx + 16, ry - 14, label)
        # Right arrow
        c.setFillColor(AMBER)
        c.setFont("Helvetica-Bold", 18)
        c.drawRightString(rx + 235, ry - 5, "\u2192")
        ry -= 64

    draw_slide_number(c, 7)


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN — build PDF
# ═══════════════════════════════════════════════════════════════════════════

def main():
    os.makedirs("docs", exist_ok=True)
    c = canvas.Canvas(OUTPUT_PATH, pagesize=landscape(A4))
    c.setTitle("interior-design-3d-to-2d — Pitch Deck")
    c.setAuthor("i3d→2d")
    c.setSubject("Automated 3D to 2D CAD Conversion")

    print("Generating slide 1 — Cover...")
    slide_cover(c)
    c.showPage()

    print("Generating slide 2 — Problem...")
    slide_problem(c)
    c.showPage()

    print("Generating slide 3 — Solution...")
    slide_solution(c)
    c.showPage()

    print("Generating slide 4 — Before/After...")
    slide_before_after(c, BEFORE_AFTER)
    c.showPage()

    print("Generating slide 5 — Pricing...")
    slide_pricing(c)
    c.showPage()

    print("Generating slide 6 — Why Us...")
    slide_why_us(c)
    c.showPage()

    print("Generating slide 7 — CTA...")
    slide_cta(c)
    c.showPage()

    c.save()
    size_kb = os.path.getsize(OUTPUT_PATH) / 1024
    print(f"\nPDF saved to: {OUTPUT_PATH}")
    print(f"File size: {size_kb:.1f} KB")
    print("Done.")


if __name__ == "__main__":
    main()
