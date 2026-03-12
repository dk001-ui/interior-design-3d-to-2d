"""
tests/test_core.py
Unit tests for parser, slicer, and exporter.
These tests run on synthetic geometry — no real .dae file needed.
"""

import numpy as np
import pytest
import tempfile
import os
from pathlib import Path


# ─── Helpers ────────────────────────────────────────────────────────────────

def make_box_model(w=5.0, d=4.0, h=3.0):
    """
    Return a minimal Model with a single box mesh (a room).
    Vertices are the 8 corners of a box; faces are 12 triangles (2 per face).
    """
    from parser.collada import Model, Mesh

    v = np.array([
        [0, 0, 0], [w, 0, 0], [w, d, 0], [0, d, 0],   # floor
        [0, 0, h], [w, 0, h], [w, d, h], [0, d, h],   # ceiling
    ], dtype=np.float64)

    f = np.array([
        # floor
        [0, 1, 2], [0, 2, 3],
        # ceiling
        [4, 6, 5], [4, 7, 6],
        # front wall (y=0)
        [0, 1, 5], [0, 5, 4],
        # back wall (y=d)
        [2, 3, 7], [2, 7, 6],
        # left wall (x=0)
        [0, 3, 7], [0, 7, 4],
        # right wall (x=w)
        [1, 2, 6], [1, 6, 5],
    ], dtype=np.int32)

    mesh = Mesh(name="box", layer="default", vertices=v, faces=f)
    model = Model(meshes=[mesh], source_file="synthetic")
    return model


DEFAULT_CONFIG = {
    "project_name": "Test Project",
    "room_height": 3.0,
    "sill_height": 0.9,
    "lintel_height": 2.1,
    "door_height": 2.1,
    "wall_thickness": 0.23,
    "cut_height": 1.0,
    "scale": 50,
    "output_dir": "output",
    "add_dimensions": True,
    "add_title_block": True,
    "sections": [],
    "slice_tolerance": 0.05,
}


# ─── Model / Parser tests ────────────────────────────────────────────────────

class TestModel:
    def test_model_has_meshes(self):
        model = make_box_model()
        assert len(model.meshes) == 1

    def test_mesh_vertices_shape(self):
        model = make_box_model()
        verts = model.meshes[0].vertices
        assert verts.shape == (8, 3)

    def test_mesh_faces_shape(self):
        model = make_box_model()
        faces = model.meshes[0].faces
        assert faces.shape == (12, 3)

    def test_model_bounds(self):
        model = make_box_model(w=5.0, d=4.0, h=3.0)
        mn, mx = model.bounds
        np.testing.assert_allclose(mn, [0, 0, 0])
        np.testing.assert_allclose(mx, [5, 4, 3])

    def test_all_vertices_stacked(self):
        model = make_box_model()
        all_v = model.all_vertices
        assert all_v.shape[1] == 3
        assert len(all_v) == 8


# ─── Slicer tests ────────────────────────────────────────────────────────────

class TestSlicer:
    def setup_method(self):
        self.model = make_box_model(w=5.0, d=4.0, h=3.0)
        from core.slicer import Slicer
        self.slicer = Slicer(self.model, DEFAULT_CONFIG)

    def test_floor_plan_returns_slice_result(self):
        from core.slicer import SliceResult
        result = self.slicer.floor_plan()
        assert isinstance(result, SliceResult)

    def test_floor_plan_has_segments(self):
        result = self.slicer.floor_plan()
        assert len(result.segments) > 0, "Floor plan should produce segments"

    def test_floor_plan_layer(self):
        result = self.slicer.floor_plan()
        assert result.layer == "FLOOR_PLAN"

    def test_floor_plan_segments_are_2d(self):
        result = self.slicer.floor_plan()
        for seg in result.segments:
            assert len(seg) == 2
            assert len(seg[0]) == 2
            assert len(seg[1]) == 2

    def test_elevations_returns_four_views(self):
        elevations = self.slicer.elevations()
        assert set(elevations.keys()) == {
            "elevation_north", "elevation_south",
            "elevation_east", "elevation_west"
        }

    def test_elevations_have_segments(self):
        elevations = self.slicer.elevations()
        for name, result in elevations.items():
            assert len(result.segments) > 0, f"{name} should have segments"

    def test_section_cut(self):
        sections = self.slicer.sections([
            {"name": "section_AA", "axis": "y", "position": 2.0}
        ])
        assert "section_AA" in sections
        result = sections["section_AA"]
        assert len(result.segments) > 0

    def test_no_sections_defined(self):
        sections = self.slicer.sections([])
        assert sections == {}

    def test_slice_result_bounds(self):
        result = self.slicer.floor_plan()
        (min_x, min_y), (max_x, max_y) = result.bounds()
        assert max_x > min_x
        assert max_y > min_y


# ─── Exporter tests ──────────────────────────────────────────────────────────

class TestExporter:
    def setup_method(self):
        self.model = make_box_model()
        from core.slicer import Slicer
        from core.exporter import Exporter
        self.tmpdir = tempfile.mkdtemp()
        cfg = {**DEFAULT_CONFIG, "output_dir": self.tmpdir}
        self.slicer = Slicer(self.model, cfg)
        self.exporter = Exporter(cfg, output_dir=self.tmpdir)

    def test_export_floor_plan_creates_file(self):
        result = self.slicer.floor_plan()
        path = self.exporter.export_floor_plan(result)
        assert Path(path).exists(), "floor_plan.dxf should exist"
        assert path.endswith(".dxf")

    def test_export_floor_plan_is_valid_dxf(self):
        import ezdxf
        result = self.slicer.floor_plan()
        path = self.exporter.export_floor_plan(result)
        doc = ezdxf.readfile(path)
        assert doc is not None

    def test_export_elevations_creates_four_files(self):
        elevations = self.slicer.elevations()
        paths = self.exporter.export_elevations(elevations)
        assert len(paths) == 4
        for p in paths:
            assert Path(p).exists()

    def test_export_section_creates_file(self):
        sections = self.slicer.sections([
            {"name": "section_AA", "axis": "y", "position": 2.0}
        ])
        paths = self.exporter.export_sections(sections)
        assert len(paths) == 1
        assert Path(paths[0]).exists()

    def test_dxf_has_floor_plan_layer(self):
        import ezdxf
        result = self.slicer.floor_plan()
        path = self.exporter.export_floor_plan(result)
        doc = ezdxf.readfile(path)
        layer_names = [l.dxf.name for l in doc.layers]
        assert "FLOOR_PLAN" in layer_names

    def test_no_dimensions_flag(self):
        import ezdxf
        from core.exporter import Exporter
        cfg = {**DEFAULT_CONFIG, "output_dir": self.tmpdir, "add_dimensions": False, "add_title_block": False}
        exporter = Exporter(cfg, output_dir=self.tmpdir)
        from core.slicer import Slicer
        result = Slicer(self.model, cfg).floor_plan()
        path = exporter.export_floor_plan(result)
        doc = ezdxf.readfile(path)
        assert doc is not None


# ─── Config tests ────────────────────────────────────────────────────────────

class TestConfig:
    def test_default_config_loads(self):
        from config import CONFIG
        assert "cut_height" in CONFIG
        assert "scale" in CONFIG
        assert "room_height" in CONFIG

    def test_config_types(self):
        from config import CONFIG
        assert isinstance(CONFIG["scale"], int)
        assert isinstance(CONFIG["room_height"], float)
        assert isinstance(CONFIG["sections"], list)
