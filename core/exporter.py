"""
core/exporter.py -- Export SliceResult objects to DXF files.

Now supports:
  - Per-layer DXF export (one DXF per CAD layer, or all layers in one file)
  - MEP, Electrical, Furniture, Structural layer colors
  - Layer visibility control (export only specified layers)
  - Combined multi-layer DXF for full drawing sets

Layer color scheme (AutoCAD Color Index):
    WALLS        ->  7   white/black
    FLOOR        ->  8   grey
    CEILING      ->  9   light grey
    DOORS        ->  30  orange
    WINDOWS      ->  140 light blue
    STAIRS       ->  50  brown
    FURNITURE    ->  2   yellow
    MEP          ->  5   blue
    ELECTRICAL   ->  1   red
    STRUCTURE    ->  6   magenta
    SITE         ->  3   green
    ANNOTATIONS  ->  8   grey
    DIMENSIONS   ->  7   white
    TITLE_BLOCK  ->  7   white
    MISC         ->  9   light grey
"""

import os
import logging
from typing import Dict, List, Optional
from pathlib import Path

try:
    import ezdxf
    from ezdxf import units
except ImportError:
    raise ImportError("ezdxf not installed. Run: pip install ezdxf")

from core.slicer import SliceResult, Segment

logger = logging.getLogger(__name__)

# Full layer color map (AutoCAD Color Index)
LAYER_COLORS = {
    "WALLS":        7,    # white/black
    "FLOOR":        8,    # grey
    "CEILING":      9,    # light grey
    "DOORS":        30,   # orange
    "WINDOWS":      140,  # light blue
    "STAIRS":       50,   # brown
    "FURNITURE":    2,    # yellow
    "MEP":          5,    # blue
    "ELECTRICAL":   1,    # red
    "STRUCTURE":    6,    # magenta
    "SITE":         3,    # green
    "ANNOTATIONS":  8,    # grey
    "DIMENSIONS":   7,    # white
    "TITLE_BLOCK":  7,    # white
    "MISC":         9,    # light grey
    # elevation/section layers
    "FLOOR_PLAN":         2,
    "ELEVATION_NORTH":    3,
    "ELEVATION_SOUTH":    3,
    "ELEVATION_EAST":     4,
    "ELEVATION_WEST":     4,
}

# Linetype per layer (for MEP/Electrical dashed lines)
LAYER_LINETYPES = {
    "MEP":         "DASHED",
    "ELECTRICAL":  "DASHED2",
    "ANNOTATIONS": "DOTTED",
}

# Lineweight per layer (mm * 100)
LAYER_LINEWEIGHTS = {
    "WALLS":      50,   # 0.50mm -- heavy
    "STRUCTURE":  70,   # 0.70mm -- heaviest
    "FLOOR":      25,   # 0.25mm
    "CEILING":    18,   # 0.18mm
    "FURNITURE":  18,   # 0.18mm
    "MEP":        18,   # 0.18mm
    "ELECTRICAL": 13,   # 0.13mm
    "DOORS":      35,   # 0.35mm
    "WINDOWS":    25,   # 0.25mm
    "DIMENSIONS": 13,   # 0.13mm
}


class Exporter:
    def __init__(self, config: dict, output_dir: str = "output"):
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.scale           = config.get("scale", 50)
        self.project_name    = config.get("project_name", "Project")
        self.drawn_by        = config.get("drawn_by", "")
        self.add_dimensions  = config.get("add_dimensions", True)
        self.add_title_block = config.get("add_title_block", True)
        # Layer filter: if set, only export these layers
        self.active_layers: Optional[List[str]] = config.get("layers", None)

    # ----------------------------------------------------------------------- #
    #  PUBLIC
    # ----------------------------------------------------------------------- #

    def export_floor_plan(self, result: SliceResult) -> str:
        path = self.output_dir / "floor_plan.dxf"
        doc = self._new_doc()
        msp = doc.modelspace()
        self._setup_layers(doc)
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
            self._setup_layers(doc)
            self._draw_segments(msp, result.segments, name.upper())
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
            self._setup_layers(doc)
            self._draw_segments(msp, result.segments, result.layer)
            if self.add_dimensions:
                self._add_dimensions(msp, result)
            if self.add_title_block:
                label = name.replace("_", " ").title() + " - Scale 1:%d" % self.scale
                self._add_title_block(msp, result, label)
            doc.saveas(str(path))
            logger.info(f"Saved section: {path}")
            paths.append(str(path))
        return paths

    def export_by_layer(self, results: Dict[str, SliceResult]) -> List[str]:
        """
        Export one DXF file per CAD layer.
        Results dict maps layer_name -> SliceResult.
        Respects active_layers filter from config.
        """
        paths = []
        for layer_name, result in results.items():
            if self.active_layers and layer_name not in self.active_layers:
                logger.info(f"Skipping layer {layer_name} (not in active_layers filter)")
                continue
            filename = f"layer_{layer_name.lower()}.dxf"
            path = self.output_dir / filename
            doc = self._new_doc()
            msp = doc.modelspace()
            self._setup_layers(doc)
            self._draw_segments(msp, result.segments, layer_name)
            if self.add_title_block:
                label = f"{layer_name} - Scale 1:{self.scale}"
                self._add_title_block(msp, result, label)
            doc.saveas(str(path))
            logger.info(f"Saved layer DXF: {path}")
            paths.append(str(path))
        return paths

    def export_combined(self, results: Dict[str, SliceResult], filename: str = "combined.dxf") -> str:
        """
        Export all layers into a single DXF file.
        Each CAD layer (WALLS, MEP, ELECTRICAL, etc.) is a separate DXF layer.
        Respects active_layers filter from config.
        """
        path = self.output_dir / filename
        doc = self._new_doc()
        msp = doc.modelspace()
        self._setup_layers(doc)

        drawn = 0
        for layer_name, result in results.items():
            if self.active_layers and layer_name not in self.active_layers:
                continue
            self._draw_segments(msp, result.segments, layer_name)
            drawn += len(result.segments)

        logger.info(f"Combined DXF: {drawn} segments across {len(results)} layers -> {path}")
        doc.saveas(str(path))
        return str(path)

    # ----------------------------------------------------------------------- #
    #  PRIVATE: DXF SETUP
    # ----------------------------------------------------------------------- #

    def _new_doc(self):
        doc = ezdxf.new("R2010")
        doc.units = units.M
        return doc

    def _setup_layers(self, doc):
        """Register all known CAD layers with correct colors, linetypes, lineweights."""
        # Load standard linetypes
        try:
            doc.linetypes.load_ltypes_into_table(
                "DASHED", force=False
            )
        except Exception:
            pass  # linetypes may already be loaded

        for layer_name, color in LAYER_COLORS.items():
            if layer_name not in doc.layers:
                attribs = {"color": color}
                ltype = LAYER_LINETYPES.get(layer_name)
                lw = LAYER_LINEWEIGHTS.get(layer_name)
                if ltype:
                    try:
                        attribs["linetype"] = ltype
                    except Exception:
                        pass
                if lw:
                    attribs["lineweight"] = lw
                doc.layers.add(layer_name, dxfattribs=attribs)

    def _draw_segments(self, msp, segments: List[Segment], layer: str):
        # Ensure layer exists
        if layer not in msp.doc.layers:
            msp.doc.layers.add(layer, dxfattribs={"color": LAYER_COLORS.get(layer, 7)})
        for seg in segments:
            (x1, y1), (x2, y2) = seg
            msp.add_line(
                start=(x1, y1),
                end=(x2, y2),
                dxfattribs={"layer": layer}
            )

    def _add_dimensions(self, msp, result: SliceResult):
        (min_x, min_y), (max_x, max_y) = result.bounds()
        w = max_x - min_x
        h = max_y - min_y
        if w < 0.01 or h < 0.01:
            return

        offset = 0.5
        msp.add_linear_dim(
            base=(min_x, min_y - offset),
            p1=(min_x, min_y - offset),
            p2=(max_x, min_y - offset),
            dimstyle="EZDXF",
            override={"dimtxt": 0.15, "dimasz": 0.1},
            dxfattribs={"layer": "DIMENSIONS"}
        ).render()

        msp.add_linear_dim(
            base=(min_x - offset, min_y),
            p1=(min_x - offset, min_y),
            p2=(min_x - offset, max_y),
            angle=90,
            dimstyle="EZDXF",
            override={"dimtxt": 0.15, "dimasz": 0.1},
            dxfattribs={"layer": "DIMENSIONS"}
        ).render()

    def _add_title_block(self, msp, result: SliceResult, label: str):
        (min_x, min_y), (max_x, max_y) = result.bounds()
        if max_x == min_x:
            return

        tb_y = min_y - 1.5
        tb_h = 0.8
        tb_w = max_x - min_x

        msp.add_lwpolyline(
            [(min_x, tb_y), (max_x, tb_y), (max_x, tb_y - tb_h),
             (min_x, tb_y - tb_h), (min_x, tb_y)],
            dxfattribs={"layer": "TITLE_BLOCK"}
        )
        msp.add_text(
            self.project_name,
            dxfattribs={"layer": "TITLE_BLOCK", "height": 0.25,
                        "insert": (min_x + 0.1, tb_y - 0.3)}
        )
        msp.add_text(
            label,
            dxfattribs={"layer": "TITLE_BLOCK", "height": 0.18,
                        "insert": (min_x + 0.1, tb_y - 0.55)}
        )
        if self.drawn_by:
            msp.add_text(
                f"Drawn by: {self.drawn_by}",
                dxfattribs={"layer": "TITLE_BLOCK", "height": 0.15,
                            "insert": (max_x - tb_w * 0.35, tb_y - 0.3)}
            )
        date_str = self.config.get("date", "")
        if date_str:
            msp.add_text(
                f"Date: {date_str}",
                dxfattribs={"layer": "TITLE_BLOCK", "height": 0.15,
                            "insert": (max_x - tb_w * 0.35, tb_y - 0.55)}
            )
