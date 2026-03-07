"""
parser/skp.py — SketchUp .skp file handler.

.skp is a proprietary binary format. Two paths:

PATH A (Recommended): Export from SketchUp as COLLADA (.dae) then use parser/collada.py
PATH B (Headless):    Use the sketchup-api Docker image or trimesh loader

This module provides:
  1. A converter that calls SketchUp's CLI (if installed) to export .dae
  2. A trimesh-based fallback for basic geometry extraction
  3. Clear error messages guiding users to Path A if neither works

Usage:
    from parser.skp import SkpParser
    model = SkpParser("model.skp").parse()
"""

import subprocess
import os
import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class SkpParser:
    """
    Attempts to parse a .skp file via multiple strategies.
    Falls back gracefully with clear instructions.
    """

    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        if not self.filepath.exists():
            raise FileNotFoundError(f"SKP file not found: {filepath}")

    def parse(self):
        """
        Try strategies in order:
        1. trimesh direct load (works for some SKP versions)
        2. SketchUp CLI export to COLLADA
        3. Raise with instructions for manual export
        """
        # Strategy 1: trimesh
        try:
            return self._parse_via_trimesh()
        except Exception as e:
            logger.warning(f"trimesh SKP load failed: {e}")

        # Strategy 2: SketchUp CLI
        try:
            return self._parse_via_sketchup_cli()
        except Exception as e:
            logger.warning(f"SketchUp CLI export failed: {e}")

        # Strategy 3: fail with instructions
        raise RuntimeError(
            f"\n"
            f"Could not parse {self.filepath.name} automatically.\n\n"
            f"SOLUTION (30 seconds in SketchUp):\n"
            f"  1. Open {self.filepath.name} in SketchUp\n"
            f"  2. File > Export > 3D Model\n"
            f"  3. Choose COLLADA (.dae)\n"
            f"  4. Run: python extract.py --input model.dae\n\n"
            f"Or use the Docker path (no SketchUp needed):\n"
            f"  docker run -v $(pwd):/data dk001/skp-converter model.skp\n"
        )

    def _parse_via_trimesh(self):
        """Use trimesh's SKP loader (supports SKP 2021+)."""
        try:
            import trimesh
        except ImportError:
            raise ImportError("trimesh not installed. Run: pip install trimesh")

        scene = trimesh.load(str(self.filepath))
        from parser.collada import Model, Mesh
        import numpy as np

        model = Model(source_file=str(self.filepath))
        meshes = scene.geometry if hasattr(scene, 'geometry') else {"mesh": scene}

        for name, mesh in meshes.items():
            if hasattr(mesh, 'vertices') and hasattr(mesh, 'faces'):
                model.meshes.append(Mesh(
                    name=name,
                    layer="default",
                    vertices=np.array(mesh.vertices, dtype=np.float64),
                    faces=np.array(mesh.faces, dtype=np.int32)
                ))

        logger.info(f"trimesh loaded {len(model.meshes)} meshes from {self.filepath.name}")
        return model

    def _parse_via_sketchup_cli(self):
        """
        Use SketchUp's built-in CLI (macOS/Windows) to export COLLADA.
        SketchUp must be installed.
        """
        sketchup_paths = [
            "/Applications/SketchUp 2024/SketchUp.app/Contents/MacOS/SketchUp",
            "/Applications/SketchUp 2023/SketchUp.app/Contents/MacOS/SketchUp",
            r"C:\Program Files\SketchUp\SketchUp 2024\SketchUp.exe",
        ]

        sketchup_bin = None
        for path in sketchup_paths:
            if os.path.exists(path):
                sketchup_bin = path
                break

        if not sketchup_bin:
            raise FileNotFoundError("SketchUp not found in standard locations")

        with tempfile.TemporaryDirectory() as tmpdir:
            dae_path = os.path.join(tmpdir, "export.dae")
            cmd = [
                sketchup_bin,
                "-RubyStartupScript",
                f'Sketchup.open_file("{self.filepath}"); '
                f'Sketchup.active_model.export("{dae_path}"); '
                f'exit'
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=60)
            if result.returncode != 0 or not os.path.exists(dae_path):
                raise RuntimeError(f"SketchUp CLI export failed: {result.stderr}")

            from parser.collada import ColladaParser
            return ColladaParser(dae_path).parse()
