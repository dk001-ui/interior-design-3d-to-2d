#!/usr/bin/env python3
"""
extract.py -- CLI runner for interior-design-3d-to-2d

Usage:
    # COLLADA export from SketchUp (recommended)
    python extract.py --input model.dae

    # SKP directly (trimesh / Docker fallback)
    python extract.py --input model.skp

    # Custom config and output dir
    python extract.py --input model.dae --config my_project.py --output output/site_A

    # Override parameters inline
    python extract.py --input model.dae --room-height 3.2 --scale 100

    # Filter to specific layers only
    python extract.py --input model.dae --layers WALLS DOORS WINDOWS
    python extract.py --input model.dae --layers MEP ELECTRICAL

    # Export mode
    python extract.py --input model.dae --export-mode per_layer
    python extract.py --input model.dae --export-mode both

    # Only generate floor plan (skip elevations + sections)
    python extract.py --input model.dae --only floor_plan

    # List layers present in a model without exporting
    python extract.py --input model.dae --list-layers
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

VALID_LAYERS = [
    "WALLS", "FLOOR", "CEILING", "DOORS", "WINDOWS", "STAIRS",
    "FURNITURE", "MEP", "ELECTRICAL", "STRUCTURE", "SITE",
    "ANNOTATIONS", "MISC"
]


def load_config(config_path: str) -> dict:
    spec = importlib.util.spec_from_file_location("custom_config", config_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.CONFIG


def main():
    parser = argparse.ArgumentParser(
        description="Convert 3D SketchUp/COLLADA model to 2D DXF drawings"
    )
    parser.add_argument("--input",         required=True,  help="Path to .dae or .skp file")
    parser.add_argument("--config",        default=None,   help="Path to custom config.py")
    parser.add_argument("--output",        default=None,   help="Output directory")
    parser.add_argument("--room-height",   type=float,     help="Room height in metres")
    parser.add_argument("--sill-height",   type=float,     help="Sill height in metres")
    parser.add_argument("--lintel-height", type=float,     help="Lintel height in metres")
    parser.add_argument("--scale",         type=int,       help="Drawing scale (e.g. 50)")
    parser.add_argument("--cut-height",    type=float,     help="Floor plan cut height in metres")
    parser.add_argument("--layers",        nargs="+",      metavar="LAYER",
                        help=f"Only export these layers. Valid: {', '.join(VALID_LAYERS)}")
    parser.add_argument("--export-mode",   default=None,
                        choices=["combined", "per_layer", "both"],
                        help="combined (default) | per_layer | both")
    parser.add_argument("--only",          default=None,
                        choices=["floor_plan", "elevations", "sections"],
                        help="Generate only one drawing type")
    parser.add_argument("--list-layers",   action="store_true",
                        help="Print layers found in model and exit (no DXF output)")
    args = parser.parse_args()

    # Load config
    config = load_config(args.config) if args.config else CONFIG.copy()

    # CLI overrides
    if args.output:        config["output_dir"]    = args.output
    if args.room_height:   config["room_height"]   = args.room_height
    if args.sill_height:   config["sill_height"]   = args.sill_height
    if args.lintel_height: config["lintel_height"] = args.lintel_height
    if args.scale:         config["scale"]         = args.scale
    if args.cut_height:    config["cut_height"]    = args.cut_height
    if args.layers:
        invalid = [l for l in args.layers if l not in VALID_LAYERS]
        if invalid:
            logger.warning(f"Unknown layer(s) ignored: {invalid}")
        config["layers"] = [l for l in args.layers if l in VALID_LAYERS]
    if args.export_mode:   config["export_mode"]   = args.export_mode

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)

    # -- Parse ----------------------------------------------------------------
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

    # -- List layers mode -----------------------------------------------------
    if args.list_layers:
        print(f"\nLayers found in {input_path.name}:")
        for layer in sorted(model.layers):
            count = len(model.meshes_for_layer(layer))
            raw_names = sorted({m.layer_raw for m in model.meshes if m.layer == layer})
            print(f"  {layer:15s}  {count:4d} mesh(es)  [raw: {', '.join(raw_names)}]")
        print()
        sys.exit(0)

    # -- Filter model meshes by active layers ---------------------------------
    active_layers = config.get("layers")
    if active_layers:
        original_count = len(model.meshes)
        model.meshes = [m for m in model.meshes if m.layer in active_layers]
        logger.info(f"Layer filter: {original_count} -> {len(model.meshes)} meshes "
                    f"(keeping: {active_layers})")

    # -- Slice ----------------------------------------------------------------
    from core.slicer import Slicer
    slicer = Slicer(model, config)

    # -- Export ---------------------------------------------------------------
    from core.exporter import Exporter
    exporter = Exporter(config, output_dir=config["output_dir"])
    export_mode = config.get("export_mode", "combined")
    only = args.only
    outputs = []

    if only is None or only == "floor_plan":
        floor_plan = slicer.floor_plan()
        path = exporter.export_floor_plan(floor_plan)
        outputs.append(path)

    if only is None or only == "elevations":
        elevations = slicer.elevations()
        paths = exporter.export_elevations(elevations)
        outputs.extend(paths)

    if only is None or only == "sections":
        sections = slicer.sections()
        if sections:
            paths = exporter.export_sections(sections)
            outputs.extend(paths)

    logger.info(f"\nDone. {len(outputs)} file(s) written:")
    for p in outputs:
        logger.info(f"  {p}")


if __name__ == "__main__":
    main()
