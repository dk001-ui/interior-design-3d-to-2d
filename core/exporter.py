"""
core/exporter.py — Export SliceResult objects to DXF/DWG files.

Uses ezdxf (pure Python, no AutoCAD needed).
DXF files open directly in AutoCAD, FreeCAD, LibreCAD, BricsCAD.

Usage:
    from core.exporter import Exporter
    from core.slicer import Slicer

    exporter = Exporter(config, output_dir="output/")
    exporter.export_floor_plan(slicer.floor_plan())
    exporter.export_elevations(slicer.elevations())
    exporter.export_sections(slicer.sections())
"""

import os
import logging
from typing import Dict, List
from pathlib import Path

try:
    import ezdxf
    from ezdxf import units
    from ezdxf.enums import TextEntityAlignment
except ImportError:
    raise ImportError("ezdxf not installed. Run: pip install ezdxf")

from core.slicer import SliceResult, Segment

logger = logging.getLogger(__name__)

# Layer color map (AutoCAD color index)
LAYER_COLORS = {
    "FLOOR_PLAN":        2,   # yellow
    "ELEVATION_NORTH":   3,   # green
    "ELEVATION_SOUTH":   3,
    "ELEVATION_EAST":    4,   # cyan
    "ELEVATION_WEST":    4,
    "SECTION_1":         1,   # red
    "SECTION_2":         6,   # magenta
    "SECTION_3":         5,   # blue
    "DIMENSIONS":        7,   # white
    "ANNOTATIONS":       8,   # grey
    "TITLE_BLOCK":       7,
}


class Exporter:
    def __init__(self, config: dict, output_dir: str = "output"):
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.scale = config.get("scale", 50)          # 1:50 default
        self.project_name = config.get("project_name", "Project")
        self.drawn_by = config.get("drawn_by", "")
        self.add_dimensions = config.get("add_dimensions", True)
        self.add_title_block = config.get("add_title_block", True)

    # ------------------------------------------------------------------ #
    #  PUBLIC
    # ------------------------------------------------------------------ #

    def export_floor_plan(self, result: SliceResult) -> str:
        path = self.output_dir / f"floor_plan.dxf"
        doc = self._new_doc()
        msp = doc.modelspace()
        self._add_layer(doc, result.layer, LAYER_COLORS.get(result.layer, 7))
        self._draw_segments(msp, result.segments, result.layer)
        if self.add_dimensions:
            self._add_dimensions(msp, result)
        if self.add_title_block:
            self._add_title_block(msp, result, "Floor Plan - Scale 1:%d" % self.scale)
        doc.saveas(str(path))
        logger.info(f"Saved floor plan: {path}")
        return str(path)

    def export_elevations(self, elevations: Dict[str, SliceResult]) -> List[str]:
        paths = []
        for name, result in elevations.items():
            path = self.output_dir / f"{name}.dxf"
            doc = self._new_doc()
            msp = doc.modelspace()
            layer_key = name.upper()
            self._add_layer(doc, layer_key, LAYER_COLORS.get(layer_key, 3))
            self._draw_segments(msp, result.segments, layer_key)
            if self.add_dimensions:
                self._add_dimensions(msp, result)
            if self.add_title_block:
                label = name.replace("_", " ").title() + " - Scale 1:%d" % self.scale
                self._add_title_block(msp, result, label)
            doc.saveas(str(path))
            logger.info(f"Saved elevation: {path}")
            paths.append(str(path))
        return paths

    def export_sections(self, sections: Dict[str, SliceResult]) -> List[str]:
        paths = []
        for name, result in sections.items():
            path = self.output_dir / f"{name}.dxf"
            doc = self._new_doc()
            msp = doc.modelspace()
            idx = list(sections.keys()).index(name) + 1
            layer_key = f"SECTION_{idx}"
            self._add_layer(doc, layer_key, LAYER_COLORS.get(layer_key, 1))
            self._draw_segments(msp, result.segments, layer_key)
            if self.add_dimensions:
                self._add_dimensions(msp, result)
            if self.add_title_block:
                label = name.replace("_", " ").title() + " - Scale 1:%d" % self.scale
                self._add_title_block(msp, result, label)
            doc.saveas(str(path))
            logger.info(f"Saved section: {path}")
            paths.append(str(path))
        return paths

    def export_all(self, floor_plan: SliceResult,
                   elevations: Dict[str, SliceResult],
                   sections: Dict[str, SliceResult]) -> Dict:
        return {
            "floor_plan": self.export_floor_plan(floor_plan),
            "elevations": self.export_elevations(elevations),
            "sections":   self.export_sections(sections),
        }

    # ------------------------------------------------------------------ #
    #  INTERNAL
    # ------------------------------------------------------------------ #

    def _new_doc(self):
        doc = ezdxf.new("R2010")
        doc.units = units.M
        self._add_layer(doc, "DIMENSIONS", LAYER_COLORS["DIMENSIONS"])
        self._add_layer(doc, "ANNOTATIONS", LAYER_COLORS["ANNOTATIONS"])
        self._add_layer(doc, "TITLE_BLOCK", LAYER_COLORS["TITLE_BLOCK"])
        return doc

    def _add_layer(self, doc, name: str, color: int):
        if name not in doc.layers:
            doc.layers.add(name, color=color)

    def _draw_segments(self, msp, segments: List[Segment], layer: str):
        for (x1, y1), (x2, y2) in segments:
            msp.add_line((x1, y1), (x2, y2), dxfattribs={"layer": layer})

    def _add_dimensions(self, msp, result: SliceResult):
        """Add overall width and height dimensions."""
        if not result.segments:
            return
        (minx, miny), (maxx, maxy) = result.bounds()
        w = maxx - minx
        h = maxy - miny
        offset = max(w, h) * 0.05 + 0.5

        # Width dimension (bottom)
        msp.add_linear_dim(
            base=(minx, miny - offset),
            p1=(minx, miny - offset),
            p2=(maxx, miny - offset),
            angle=0,
            dxfattribs={"layer": "DIMENSIONS"}
        ).render()

        # Height dimension (right)
        msp.add_linear_dim(
            base=(maxx + offset, miny),
            p1=(maxx + offset, miny),
            p2=(maxx + offset, maxy),
            angle=90,
            dxfattribs={"layer": "DIMENSIONS"}
        ).render()

    def _add_title_block(self, msp, result: SliceResult, label: str):
        """Simple title block at bottom of drawing."""
        if not result.segments:
            return
        (minx, miny), (maxx, maxy) = result.bounds()
        tb_y = miny - 2.0
        tb_x = minx

        # Border
        msp.add_lwpolyline(
            [(tb_x, tb_y), (maxx, tb_y), (maxx, tb_y - 1.0), (tb_x, tb_y - 1.0)],
            close=True,
            dxfattribs={"layer": "TITLE_BLOCK"}
        )

        # Project name
        msp.add_text(
            self.project_name,
            dxfattribs={"layer": "TITLE_BLOCK", "height": 0.25}
        ).set_placement((tb_x + 0.1, tb_y - 0.3), align=TextEntityAlignment.LEFT)

        # Drawing label
        msp.add_text(
            label,
            dxfattribs={"layer": "TITLE_BLOCK", "height": 0.18}
        ).set_placement((tb_x + 0.1, tb_y - 0.6), align=TextEntityAlignment.LEFT)

        # Drawn by
        if self.drawn_by:
            msp.add_text(
                f"Drawn by: {self.drawn_by}",
                dxfattribs={"layer": "TITLE_BLOCK", "height": 0.15}
            ).set_placement((tb_x + 0.1, tb_y - 0.85), align=TextEntityAlignment.LEFT)
