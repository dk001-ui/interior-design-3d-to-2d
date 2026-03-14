#!/usr/bin/env python3
"""
docker/skp_convert.py -- Headless SKP to COLLADA converter.

Runs inside the dk001/skp-converter Docker container.
Mounted volume is /data -- reads .skp from /data, writes .dae to /data.

Usage (from host):
    docker run --rm -v $(pwd):/data dk001/skp-converter model.skp
    docker run --rm -v /path/to/models:/data dk001/skp-converter model.skp output.dae
"""

import sys
import os
import logging
import argparse
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

DATA_DIR = Path("/data")


def convert_via_trimesh(skp_path: Path, dae_path: Path) -> bool:
    """Try trimesh SKP loader and export as COLLADA."""
    try:
        import trimesh
        import numpy as np

        logger.info(f"Loading {skp_path.name} via trimesh...")
        scene = trimesh.load(str(skp_path))

        if hasattr(scene, "geometry") and scene.geometry:
            meshes = list(scene.geometry.values())
        elif hasattr(scene, "vertices"):
            meshes = [scene]
        else:
            raise ValueError("No geometry found in SKP file")

        logger.info(f"Loaded {len(meshes)} mesh(es). Exporting to COLLADA...")

        # Build a trimesh Scene and export
        if hasattr(scene, "export"):
            result = scene.export(str(dae_path), file_type="dae")
        else:
            combined = trimesh.util.concatenate(meshes)
            combined.export(str(dae_path), file_type="dae")

        if dae_path.exists() and dae_path.stat().st_size > 0:
            logger.info(f"Exported: {dae_path.name} ({dae_path.stat().st_size // 1024}KB)")
            return True
        else:
            raise RuntimeError("Export produced empty or missing file")

    except Exception as e:
        logger.warning(f"trimesh conversion failed: {e}")
        return False


def convert_via_xvfb_sketchup(skp_path: Path, dae_path: Path) -> bool:
    """
    Attempt headless SketchUp export via Xvfb virtual display.
    Only works if SketchUp is installed in the container (enterprise builds).
    """
    import subprocess
    import shutil

    sketchup_exe = shutil.which("sketchup")
    if not sketchup_exe:
        # Common install paths
        candidates = [
            "/opt/sketchup/SketchUp",
            "/usr/local/bin/sketchup",
        ]
        for c in candidates:
            if os.path.exists(c):
                sketchup_exe = c
                break

    if not sketchup_exe:
        logger.info("SketchUp CLI not found — skipping xvfb strategy")
        return False

    logger.info(f"Attempting headless SketchUp export via Xvfb: {sketchup_exe}")
    try:
        # Start virtual display
        xvfb = subprocess.Popen(["Xvfb", ":99", "-screen", "0", "1024x768x24"])
        env = os.environ.copy()
        env["DISPLAY"] = ":99"

        result = subprocess.run(
            [sketchup_exe, "-export", str(dae_path), str(skp_path)],
            env=env,
            capture_output=True,
            text=True,
            timeout=180
        )
        xvfb.terminate()

        if result.returncode == 0 and dae_path.exists():
            logger.info(f"SketchUp CLI export succeeded: {dae_path.name}")
            return True
        else:
            logger.warning(f"SketchUp CLI failed (code {result.returncode}): {result.stderr}")
            return False

    except Exception as e:
        logger.warning(f"Xvfb/SketchUp strategy failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Convert .skp to .dae (runs inside Docker container)"
    )
    parser.add_argument("input", help=".skp file name (relative to /data)")
    parser.add_argument("output", nargs="?", default=None,
                        help=".dae output file name (default: same name as input)")
    args = parser.parse_args()

    skp_path = DATA_DIR / args.input
    if not skp_path.exists():
        logger.error(f"Input file not found: {skp_path}")
        logger.error(f"Make sure you mounted the correct directory with -v /your/path:/data")
        sys.exit(1)

    output_name = args.output or (skp_path.stem + ".dae")
    dae_path = DATA_DIR / output_name

    logger.info(f"Converting: {skp_path.name} -> {dae_path.name}")
    logger.info(f"Strategy 1: trimesh")

    if convert_via_trimesh(skp_path, dae_path):
        logger.info(f"SUCCESS: {dae_path}")
        sys.exit(0)

    logger.info("Strategy 2: Xvfb + SketchUp CLI")
    if convert_via_xvfb_sketchup(skp_path, dae_path):
        logger.info(f"SUCCESS: {dae_path}")
        sys.exit(0)

    logger.error(
        f"\nAll conversion strategies failed for {skp_path.name}.\n\n"
        f"Manual fallback:\n"
        f"  1. Open {skp_path.name} in SketchUp\n"
        f"  2. File > Export > 3D Model > COLLADA (.dae)\n"
        f"  3. Run: python extract.py --input model.dae\n"
    )
    sys.exit(1)


if __name__ == "__main__":
    main()
