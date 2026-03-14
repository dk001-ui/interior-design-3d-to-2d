"""
parser/collada.py -- Parse COLLADA (.dae) files exported from SketchUp.

Now with full layer-aware parsing. SketchUp exports layer names into COLLADA
node attributes. This parser extracts them and maps to standard CAD layers:

    SketchUp Layer Name        ->  CAD Layer
    ------------------------------------------
    Layer0 / default / 0       ->  WALLS
    Walls / Wall                ->  WALLS
    Furniture / FF&E            ->  FURNITURE
    MEP / Services / Plumbing   ->  MEP
    Electrical / Lighting       ->  ELECTRICAL
    Ceiling / Roof              ->  CEILING
    Floor / Slab                ->  FLOOR
    Annotation / Text           ->  ANNOTATIONS
    (anything else)             ->  MISC

Usage:
    from parser.collada import ColladaParser
    model = ColladaParser("model.dae").parse()
    # model.meshes -> list of Mesh(vertices, faces, name, layer)
    # model.layers -> set of layer names present in model
"""

import xml.etree.ElementTree as ET
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Set
import logging

logger = logging.getLogger(__name__)

NS = {
    "c": "http://www.collada.org/2005/11/COLLADASchema"
}

# ---------------------------------------------------------------------------
# Layer name normalisation map
# Keys are lowercase substrings to match against the raw SketchUp layer name
# ---------------------------------------------------------------------------
LAYER_MAP = [
    (["wall"],                          "WALLS"),
    (["floor", "slab", "ground"],       "FLOOR"),
    (["ceiling", "roof", "soffit"],     "CEILING"),
    (["door"],                          "DOORS"),
    (["window", "glazing", "glass"],    "WINDOWS"),
    (["stair", "step", "ramp"],         "STAIRS"),
    (["furniture", "ffe", "ff&e",
      "cabinet", "wardrobe", "joinery",
      "kitchen", "bed", "sofa"],        "FURNITURE"),
    (["mep", "service", "plumbing",
      "hvac", "duct", "pipe",
      "sanitary", "water"],             "MEP"),
    (["electric", "lighting", "light",
      "power", "socket", "switch"],     "ELECTRICAL"),
    (["column", "beam", "struct",
      "slab", "concrete"],              "STRUCTURE"),
    (["site", "boundary", "plot",
      "landscape", "garden"],           "SITE"),
    (["annot", "text", "label",
      "dimension", "grid"],             "ANNOTATIONS"),
]

DEFAULT_LAYER = "WALLS"   # Layer0 / unnamed geometry -> walls


def normalise_layer(raw: str) -> str:
    """Map a raw SketchUp layer name to a standard CAD layer."""
    if not raw:
        return DEFAULT_LAYER
    lower = raw.lower().replace(" ", "").replace("_", "").replace("-", "")
    # Layer0 / default / "0" -> WALLS (SketchUp default layer)
    if lower in ("0", "layer0", "default", "defaultlayer", ""):
        return DEFAULT_LAYER
    for keywords, cad_layer in LAYER_MAP:
        for kw in keywords:
            if kw in lower:
                return cad_layer
    return "MISC"


@dataclass
class Mesh:
    name: str
    layer: str           # normalised CAD layer name e.g. "WALLS"
    layer_raw: str       # original SketchUp layer string
    vertices: np.ndarray  # shape (N, 3) float64 -- XYZ in metres
    faces: np.ndarray    # shape (M, 3) int    -- triangle indices


@dataclass
class Model:
    meshes: List[Mesh] = field(default_factory=list)
    source_file: str = ""

    @property
    def layers(self) -> Set[str]:
        return {m.layer for m in self.meshes}

    @property
    def all_vertices(self) -> np.ndarray:
        if not self.meshes:
            return np.empty((0, 3))
        return np.vstack([m.vertices for m in self.meshes])

    @property
    def bounds(self):
        verts = self.all_vertices
        return verts.min(axis=0), verts.max(axis=0)

    def meshes_for_layer(self, layer: str) -> List[Mesh]:
        return [m for m in self.meshes if m.layer == layer]

    def meshes_for_layers(self, layers: List[str]) -> List[Mesh]:
        layer_set = set(layers)
        return [m for m in self.meshes if m.layer in layer_set]


class ColladaParser:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.tree = ET.parse(filepath)
        self.root = self.tree.getroot()

    def parse(self) -> Model:
        model = Model(source_file=self.filepath)
        geometries = self._parse_geometries()
        nodes = self._parse_nodes()

        for node_name, geo_id, layer_raw, transform in nodes:
            if geo_id in geometries:
                verts, faces = geometries[geo_id]
                transformed = self._apply_transform(verts, transform)
                layer = normalise_layer(layer_raw)
                model.meshes.append(Mesh(
                    name=node_name,
                    layer=layer,
                    layer_raw=layer_raw,
                    vertices=transformed,
                    faces=faces
                ))

        # Log layer summary
        layer_counts = {}
        for m in model.meshes:
            layer_counts[m.layer] = layer_counts.get(m.layer, 0) + 1
        logger.info(f"Parsed {len(model.meshes)} meshes from {self.filepath}")
        for layer, count in sorted(layer_counts.items()):
            logger.info(f"  {layer}: {count} mesh(es)")

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
        pos_source = None
        for source in mesh_el.findall("c:source", NS):
            src_id = source.get("id", "")
            if "position" in src_id or "vertex" in src_id:
                float_arr = source.find(".//c:float_array", NS)
                if float_arr is not None:
                    pos_source = float_arr
                    break

        if pos_source is None:
            raise ValueError("No position source found in mesh")

        raw = list(map(float, pos_source.text.strip().split()))
        vertices = np.array(raw, dtype=np.float64).reshape(-1, 3)

        # SketchUp exports in inches -- convert to metres
        if vertices.max() > 50:
            vertices = vertices * 0.0254

        triangles_el = mesh_el.find("c:triangles", NS)
        polylist_el  = mesh_el.find("c:polylist", NS)

        faces = None
        if triangles_el is not None:
            faces = self._parse_triangles(triangles_el)
        elif polylist_el is not None:
            faces = self._parse_polylist(polylist_el)
        else:
            for tag in ["c:polygons", "c:lines"]:
                el = mesh_el.find(tag, NS)
                if el is not None:
                    faces = self._parse_triangles(el)
                    break

        if faces is None:
            raise ValueError("No triangle/polygon primitive found")

        return vertices, faces

    def _parse_triangles(self, el):
        p_el = el.find("c:p", NS)
        if p_el is None or not p_el.text:
            return np.empty((0, 3), dtype=np.int32)
        indices = list(map(int, p_el.text.strip().split()))
        inputs = el.findall("c:input", NS)
        stride = len(inputs) if inputs else 1
        vertex_offset = 0
        for inp in inputs:
            if inp.get("semantic") == "VERTEX":
                vertex_offset = int(inp.get("offset", 0))
                break
        vertex_indices = indices[vertex_offset::stride]
        n_triangles = len(vertex_indices) // 3
        return np.array(vertex_indices[:n_triangles * 3], dtype=np.int32).reshape(-1, 3)

    def _parse_polylist(self, el):
        vcount_el = el.find("c:vcount", NS)
        p_el      = el.find("c:p", NS)
        if p_el is None or not p_el.text:
            return np.empty((0, 3), dtype=np.int32)

        inputs = el.findall("c:input", NS)
        stride = len(inputs) if inputs else 1
        vertex_offset = 0
        for inp in inputs:
            if inp.get("semantic") == "VERTEX":
                vertex_offset = int(inp.get("offset", 0))
                break

        raw_indices = list(map(int, p_el.text.strip().split()))
        vcounts = list(map(int, vcount_el.text.strip().split())) if vcount_el is not None else []

        faces = []
        idx = 0
        for vc in vcounts:
            poly_verts = []
            for _ in range(vc):
                poly_verts.append(raw_indices[idx + vertex_offset])
                idx += stride
            for i in range(1, len(poly_verts) - 1):
                faces.append([poly_verts[0], poly_verts[i], poly_verts[i + 1]])

        return np.array(faces, dtype=np.int32) if faces else np.empty((0, 3), dtype=np.int32)

    def _parse_nodes(self):
        nodes = []
        for node in self.root.findall(".//c:node", NS):
            node_name = node.get("name", node.get("id", "unknown"))

            # SketchUp writes layer name in multiple possible attributes
            layer_raw = (
                node.get("layer") or
                node.get("name", "").split(":")[0] or
                "0"
            )

            # Also check for <extra><technique><layer> pattern (SketchUp 2020+)
            extra = node.find(".//c:extra//c:technique//c:layer", NS)
            if extra is not None and extra.text:
                layer_raw = extra.text.strip()

            matrix_el = node.find("c:matrix", NS)
            transform = np.eye(4)
            if matrix_el is not None and matrix_el.text:
                vals = list(map(float, matrix_el.text.strip().split()))
                if len(vals) == 16:
                    transform = np.array(vals).reshape(4, 4)

            instance_geom = node.find(".//c:instance_geometry", NS)
            if instance_geom is not None:
                geo_url = instance_geom.get("url", "").lstrip("#")
                nodes.append((node_name, geo_url, layer_raw, transform))

        return nodes

    def _apply_transform(self, vertices: np.ndarray, transform: np.ndarray) -> np.ndarray:
        ones = np.ones((len(vertices), 1))
        homogeneous = np.hstack([vertices, ones])
        transformed = (transform @ homogeneous.T).T
        return transformed[:, :3]
