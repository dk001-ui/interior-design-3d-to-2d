"""
parser/collada.py — Parse COLLADA (.dae) files exported from SketchUp.

COLLADA is an open XML format that SketchUp can export natively:
  File > Export > 3D Model > COLLADA (.dae)

Usage:
    from parser.collada import ColladaParser
    model = ColladaParser("model.dae").parse()
    # model.meshes -> list of Mesh(vertices, faces, name, layer)
"""

import xml.etree.ElementTree as ET
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

NS = {
    "c": "http://www.collada.org/2005/11/COLLADASchema"
}


@dataclass
class Mesh:
    name: str
    layer: str
    vertices: np.ndarray   # shape (N, 3) float64 — XYZ in metres
    faces: np.ndarray      # shape (M, 3) int    — triangle indices


@dataclass
class Model:
    meshes: List[Mesh] = field(default_factory=list)
    source_file: str = ""

    @property
    def all_vertices(self) -> np.ndarray:
        if not self.meshes:
            return np.empty((0, 3))
        return np.vstack([m.vertices for m in self.meshes])

    @property
    def bounds(self):
        verts = self.all_vertices
        return verts.min(axis=0), verts.max(axis=0)


class ColladaParser:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.tree = ET.parse(filepath)
        self.root = self.tree.getroot()

    def parse(self) -> Model:
        model = Model(source_file=self.filepath)
        geometries = self._parse_geometries()
        nodes = self._parse_nodes()

        for node_name, geo_id, layer, transform in nodes:
            if geo_id in geometries:
                verts, faces = geometries[geo_id]
                # Apply transform matrix
                transformed = self._apply_transform(verts, transform)
                model.meshes.append(Mesh(
                    name=node_name,
                    layer=layer,
                    vertices=transformed,
                    faces=faces
                ))

        logger.info(f"Parsed {len(model.meshes)} meshes from {self.filepath}")
        return model

    def _parse_geometries(self):
        geometries = {}
        for geom in self.root.findall(".//c:geometry", NS):
            geo_id = geom.get("id")
            mesh_el = geom.find("c:mesh", NS)
            if mesh_el is None:
                continue
            try:
                verts, faces = self._extract_mesh(mesh_el)
                geometries[geo_id] = (verts, faces)
            except Exception as e:
                logger.warning(f"Skipping geometry {geo_id}: {e}")
        return geometries

    def _extract_mesh(self, mesh_el):
        # Find position source
        pos_source = None
        for source in mesh_el.findall("c:source", NS):
            src_id = source.get("id", "")
            if "position" in src_id or "vertex" in src_id:
                float_arr = source.find(".//c:float_array", NS)
                if float_arr is not None:
                    values = list(map(float, float_arr.text.split()))
                    pos_source = np.array(values).reshape(-1, 3)
                    break

        if pos_source is None:
            # fallback: first float array
            float_arr = mesh_el.find(".//c:float_array", NS)
            values = list(map(float, float_arr.text.split()))
            pos_source = np.array(values).reshape(-1, 3)

        # Find triangles or polygons
        faces = []
        for prim in mesh_el.findall("c:triangles", NS):
            p_el = prim.find("c:p", NS)
            if p_el is not None:
                indices = list(map(int, p_el.text.split()))
                # stride = number of inputs
                inputs = prim.findall("c:input", NS)
                stride = len(inputs)
                vert_offset = 0
                for inp in inputs:
                    if inp.get("semantic") == "VERTEX":
                        vert_offset = int(inp.get("offset", 0))
                tri_indices = [indices[i] for i in range(vert_offset, len(indices), stride)]
                faces = np.array(tri_indices).reshape(-1, 3)

        if len(faces) == 0:
            # polylist fallback
            for prim in mesh_el.findall("c:polylist", NS):
                p_el = prim.find("c:p", NS)
                vcount_el = prim.find("c:vcount", NS)
                if p_el is not None and vcount_el is not None:
                    indices = list(map(int, p_el.text.split()))
                    vcounts = list(map(int, vcount_el.text.split()))
                    inputs = prim.findall("c:input", NS)
                    stride = len(inputs)
                    # fan triangulate
                    tri_list = []
                    idx = 0
                    for vc in vcounts:
                        poly = [indices[idx + i * stride] for i in range(vc)]
                        for i in range(1, vc - 1):
                            tri_list.append([poly[0], poly[i], poly[i + 1]])
                        idx += vc * stride
                    faces = np.array(tri_list)

        return pos_source, np.array(faces) if len(faces) > 0 else np.empty((0, 3), dtype=int)

    def _parse_nodes(self):
        nodes = []
        for node in self.root.findall(".//c:node", NS):
            name = node.get("name", "unnamed")
            layer = node.get("layer", "default")

            # Get transform matrix
            matrix_el = node.find("c:matrix", NS)
            transform = np.eye(4)
            if matrix_el is not None and matrix_el.text:
                vals = list(map(float, matrix_el.text.split()))
                transform = np.array(vals).reshape(4, 4)

            # Find geometry reference
            for inst in node.findall("c:instance_geometry", NS):
                url = inst.get("url", "").lstrip("#")
                nodes.append((name, url, layer, transform))

        return nodes

    def _apply_transform(self, vertices: np.ndarray, matrix: np.ndarray) -> np.ndarray:
        n = len(vertices)
        ones = np.ones((n, 1))
        homogeneous = np.hstack([vertices, ones])   # (N, 4)
        transformed = (matrix @ homogeneous.T).T     # (N, 4)
        return transformed[:, :3]
