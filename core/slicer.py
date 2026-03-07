"""
core/slicer.py — Slice 3D geometry into 2D views.

Produces:
  - Floor plan: horizontal section cut at specified height (default 1.0m)
  - Elevations: orthographic projections (N/S/E/W)
  - Section cuts: vertical slices at user-defined positions

Each output is a list of 2D line segments ready for DXF export.

Usage:
    from core.slicer import Slicer
    from parser.collada import ColladaParser

    model = ColladaParser("model.dae").parse()
    slicer = Slicer(model, config)
    floor_plan = slicer.floor_plan()
    elevations = slicer.elevations()
    sections   = slicer.sections()
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# A 2D line segment: ((x1,y1), (x2,y2))
Segment = Tuple[Tuple[float, float], Tuple[float, float]]


@dataclass
class SliceResult:
    name: str
    segments: List[Segment] = field(default_factory=list)
    layer: str = "0"
    scale: float = 1.0

    def bounds(self):
        if not self.segments:
            return (0, 0), (0, 0)
        xs = [p[0] for seg in self.segments for p in seg]
        ys = [p[1] for seg in self.segments for p in seg]
        return (min(xs), min(ys)), (max(xs), max(ys))


class Slicer:
    def __init__(self, model, config: dict):
        self.model = model
        self.config = config
        self.cut_height = config.get("cut_height", 1.0)          # floor plan cut
        self.sill_height = config.get("sill_height", 0.9)
        self.lintel_height = config.get("lintel_height", 2.1)
        self.room_height = config.get("room_height", 3.0)
        self.tolerance = config.get("slice_tolerance", 0.05)      # 5cm tolerance for slice

    # ------------------------------------------------------------------ #
    #  PUBLIC API
    # ------------------------------------------------------------------ #

    def floor_plan(self) -> SliceResult:
        """Horizontal section cut at cut_height."""
        logger.info(f"Generating floor plan at z={self.cut_height}m")
        segments = []
        for mesh in self.model.meshes:
            segments.extend(self._slice_mesh_horizontal(mesh, self.cut_height))
        result = SliceResult(name="floor_plan", segments=segments, layer="FLOOR_PLAN")
        logger.info(f"Floor plan: {len(segments)} segments")
        return result

    def elevations(self) -> Dict[str, SliceResult]:
        """4 orthographic elevations: North, South, East, West."""
        results = {}
        min_b, max_b = self.model.bounds

        views = {
            "elevation_north": ("y", max_b[1], False),
            "elevation_south": ("y", min_b[1], True),
            "elevation_east":  ("x", max_b[0], False),
            "elevation_west":  ("x", min_b[0], True),
        }

        for name, (axis, position, flip) in views.items():
            logger.info(f"Generating {name}")
            segments = []
            for mesh in self.model.meshes:
                segments.extend(self._project_elevation(mesh, axis, flip))
            results[name] = SliceResult(name=name, segments=segments, layer=name.upper())
            logger.info(f"{name}: {len(segments)} segments")

        return results

    def sections(self) -> Dict[str, SliceResult]:
        """Vertical section cuts defined in config."""
        results = {}
        section_cuts = self.config.get("sections", [])

        for i, cut in enumerate(section_cuts):
            axis = cut.get("axis", "y")
            position = cut.get("position", 0.0)
            name = cut.get("name", f"section_{i+1}")
            logger.info(f"Generating {name} at {axis}={position}m")

            segments = []
            for mesh in self.model.meshes:
                segments.extend(self._slice_mesh_vertical(mesh, axis, position))
            results[name] = SliceResult(name=name, segments=segments, layer=f"SECTION_{i+1}")

        return results

    # ------------------------------------------------------------------ #
    #  INTERNAL — HORIZONTAL SLICE (floor plan)
    # ------------------------------------------------------------------ #

    def _slice_mesh_horizontal(self, mesh, z: float) -> List[Segment]:
        """Find all triangle edges that cross the z plane."""
        segments = []
        verts = mesh.vertices
        faces = mesh.faces

        for face in faces:
            try:
                tri = verts[face]   # (3, 3)
            except IndexError:
                continue
            seg = self._intersect_triangle_z(tri, z)
            if seg:
                segments.append(seg)

        return segments

    def _intersect_triangle_z(self, tri: np.ndarray, z: float) -> Optional[Segment]:
        """
        Find intersection of a triangle with the plane z=const.
        Returns a 2D line segment in XY, or None if no intersection.
        """
        above = tri[:, 2] >= z
        below = tri[:, 2] < z

        if above.all() or below.all():
            return None

        points = []
        edges = [(0, 1), (1, 2), (2, 0)]
        for i, j in edges:
            zi, zj = tri[i, 2], tri[j, 2]
            if (zi >= z) != (zj >= z):
                t = (z - zi) / (zj - zi + 1e-12)
                pt = tri[i] + t * (tri[j] - tri[i])
                points.append((float(pt[0]), float(pt[1])))

        if len(points) == 2:
            return (points[0], points[1])
        return None

    # ------------------------------------------------------------------ #
    #  INTERNAL — ELEVATION PROJECTION
    # ------------------------------------------------------------------ #

    def _project_elevation(self, mesh, axis: str, flip: bool) -> List[Segment]:
        """
        Project visible faces onto a 2D plane perpendicular to axis.
        axis='x' → project onto YZ plane  (horizontal=Y, vertical=Z)
        axis='y' → project onto XZ plane  (horizontal=X, vertical=Z)
        """
        segments = []
        verts = mesh.vertices
        faces = mesh.faces

        for face in faces:
            try:
                tri = verts[face]   # (3, 3)
            except IndexError:
                continue

            # Project to 2D: drop the axis dimension
            if axis == "x":
                pts_2d = [(float(v[1]), float(v[2])) for v in tri]
            else:
                pts_2d = [(float(v[0]), float(v[2])) for v in tri]

            if flip:
                pts_2d = [(-x, y) for x, y in pts_2d]

            # Add triangle edges as segments
            for i in range(3):
                segments.append((pts_2d[i], pts_2d[(i + 1) % 3]))

        return self._deduplicate_segments(segments)

    # ------------------------------------------------------------------ #
    #  INTERNAL — VERTICAL SECTION CUT
    # ------------------------------------------------------------------ #

    def _slice_mesh_vertical(self, mesh, axis: str, position: float) -> List[Segment]:
        """Vertical section cut at axis=position. Returns XZ or YZ segments."""
        segments = []
        verts = mesh.vertices
        faces = mesh.faces

        axis_idx = {"x": 0, "y": 1}[axis]
        other_idx = 1 - axis_idx  # the other horizontal axis

        for face in faces:
            try:
                tri = verts[face]
            except IndexError:
                continue
            seg = self._intersect_triangle_plane(tri, axis_idx, position, other_idx)
            if seg:
                segments.append(seg)

        return segments

    def _intersect_triangle_plane(self, tri, axis_idx, position, other_idx) -> Optional[Segment]:
        """Find intersection of triangle with axis_idx=position plane."""
        above = tri[:, axis_idx] >= position
        below = tri[:, axis_idx] < position

        if above.all() or below.all():
            return None

        points = []
        edges = [(0, 1), (1, 2), (2, 0)]
        for i, j in edges:
            ai, aj = tri[i, axis_idx], tri[j, axis_idx]
            if (ai >= position) != (aj >= position):
                t = (position - ai) / (aj - ai + 1e-12)
                pt = tri[i] + t * (tri[j] - tri[i])
                # Return (other_horizontal, Z)
                points.append((float(pt[other_idx]), float(pt[2])))

        if len(points) == 2:
            return (points[0], points[1])
        return None

    # ------------------------------------------------------------------ #
    #  UTILS
    # ------------------------------------------------------------------ #

    def _deduplicate_segments(self, segments: List[Segment], tol=0.001) -> List[Segment]:
        """Remove near-duplicate segments."""
        unique = []
        for seg in segments:
            is_dup = False
            for u in unique:
                if self._segments_equal(seg, u, tol):
                    is_dup = True
                    break
            if not is_dup:
                unique.append(seg)
        return unique

    def _segments_equal(self, a: Segment, b: Segment, tol: float) -> bool:
        def pt_eq(p, q):
            return abs(p[0] - q[0]) < tol and abs(p[1] - q[1]) < tol
        return (pt_eq(a[0], b[0]) and pt_eq(a[1], b[1])) or \
               (pt_eq(a[0], b[1]) and pt_eq(a[1], b[0]))
