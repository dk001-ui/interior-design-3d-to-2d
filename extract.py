#!/usr/bin/env python3
"""
extract.py — CLI runner for interior-design-3d-to-2d

Usage:
    # COLLADA export from SketchUp (recommended)
    python extract.py --input model.dae

    # SKP directly (trimesh fallback)
    python extract.py --input model.skp

    # Custom config and output dir
    python extract.py --input model.dae --config my_project.py --output output/site_A

    # Override parameters inline
    python extract.py --input model.dae --room-height 3.2 --scale 100

    # Only generate floor plan (skip elevations + sections)
    python extract.py --input model.dae --only floor_plan
"""

import argparse
import logging
import sys
import importlib.util
from pathlib import Path
from config import CONFIG

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


def load_config(config_path: str) -> dict:
    """Load a custom config.py file."""
    spec = importlib.util.spec_from_file_location("custom_config", config_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.CONFIG


def main():
    parser = argparse.ArgumentParser(
        description="Convert 3D SketchUp/COLLADA model to 2D DXF drawings"
    )
    parser.add_argument("--input",        required=True, help="Path to .dae or .skp file")
    parser.add_argument("--config",       default=None,  help="Path to custom config.py")
    parser.add_argument("--output",       default=None,  help="Output directory (overrides config)")
    parser.add_argument("--room-height",  type=float,    help="Room height in metres")
    parser.add_argument("--sill-height",  type=float,    help="Sill height in metres")
    parser.add_argument("--lintel-height",type=float,    help="Lintel height in metres")
    parser.add_argument("--scale",        type=int,      help="Drawing scale (e.g. 50 for 1:50)")
    parser.add_argument("--cut-height",   type=float,    help="Floor plan cut height in metres")
    parser.add_argument("--only",         default=None,
                        choices=["floor_plan", "elevations", "sections"],
                        help="Generate only one type of drawing")
    args = parser.parse_args()

    # Load config
    config = load_config(args.config) if args.config else CONFIG.copy()

    # CLI overrides
    if args.output:       config["output_dir"]    = args.output
    if args.room_height:  config["room_height"]   = args.room_height
    if args.sill_height:  config["sill_height"]   = args.sill_height
    if args.lintel_height:config["lintel_height"] = args.lintel_height
    if args.scale:        config["scale"]         = args.scale
    if args.cut_height:   config["cut_height"]    = args.cut_height

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)

    # ── Parse ────────────────────────────────────────────────────────────
    logger.info(f"Parsing {input_path.name}...")
    suffix = input_path.suffix.lower()
    if suffix == ".dae":
        from parser.collada import ColladaParser
        model = ColladaParser(str(input_path)).parse()
    elif suffix == ".skp":
        from parser.skp import SkpParser
        model = SkpParser(str(input_path)).parse()
    else:
        logger.error(f"Unsupported format: {suffix}. Use .dae or .skp")
        sys.exit(1)

    logger.info(f"Loaded {len(model.meshes)} meshes")

    # ── Slice ───────────────────────────────────────────────────────────
    from core.slicer import Slicer
    slicer = Slicer(model, config)

    # ── Export ──────────────────────────────────────────────────────────
    from core.exporter import Exporter
    exporter = Exporter(config, output_dir=config["output_dir"])

    outputs = {}

    if args.only is None or args.only == "floor_plan":
        logger.info("Generating floor plan...")
        fp = slicer.floor_plan()
        outputs["floor_plan"] = exporter.export_floor_plan(fp)

    if args.only is None or args.only == "elevations":
        logger.info("Generating elevations...")
        elevs = slicer.elevations()
        outputs["elevations"] = exporter.export_elevations(elevs)

    if args.only is None or args.only == "sections":
        sections = config.get("sections", [])
        if sections:
            logger.info("Generating section cuts...")
            sects = slicer.sections()
            outputs["sections"] = exporter.export_sections(sects)

    # ── Summary ──────────────────────────────────────────────────────────
    print("\n" + "="*55)
    print("  DONE — output files:")
    print("="*55)
    if "floor_plan" in outputs:
        print(f"  Floor Plan  →  {outputs['floor_plan']}")
    if "elevations" in outputs:
        for p in outputs["elevations"]:
            print(f"  Elevation   →  {p}")
    if "sections" in outputs:
        for p in outputs["sections"]:
            print(f"  Section     →  {p}")
    print("="*55)
    print(f"  Open .dxf files in AutoCAD, FreeCAD, or LibreCAD")
    print("="*55 + "\n")


if __name__ == "__main__":
    main()
