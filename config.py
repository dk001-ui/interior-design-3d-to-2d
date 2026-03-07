"""
config.py — Project configuration for 3D to 2D conversion.

Copy this file per project. Pass with --config flag:
    python extract.py --input model.dae --config my_project.py
"""

CONFIG = {
    # ── Project info (shown in title block) ────────────────────────────────────
    "project_name": "My Interior Design Project",
    "drawn_by": "",
    "date": "",

    # ── Architectural parameters (metres) ─────────────────────────────────
    "room_height":    3.0,    # floor to ceiling
    "sill_height":    0.9,    # bottom of window opening from floor
    "lintel_height":  2.1,    # top of window opening from floor
    "door_height":    2.1,    # top of door opening
    "wall_thickness": 0.23,   # standard brick: 230mm

    # ── Floor plan cut height ────────────────────────────────────────────
    "cut_height": 1.0,        # horizontal slice at 1m (standard)

    # ── Output ──────────────────────────────────────────────────────────
    "scale":         50,      # 1:50 (change to 100 for larger buildings)
    "output_dir":    "output",
    "add_dimensions": True,
    "add_title_block": True,

    # ── Section cuts (optional) ─────────────────────────────────────────
    # Define vertical slices through the model
    "sections": [
        # {"name": "section_AA", "axis": "y", "position": 3.0},
        # {"name": "section_BB", "axis": "x", "position": 2.5},
    ],

    # ── Slice tolerance (metres) ──────────────────────────────────────────
    "slice_tolerance": 0.05,
}
