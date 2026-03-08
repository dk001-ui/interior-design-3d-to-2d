# interior-design-3d-to-2d

> Open-source Python library to convert SketchUp (.skp) and COLLADA (.dae) 3D models into clean 2D CAD drawings (.dxf/.dwg) for interior design and architecture projects.

## What it does

Drop in a 3D model → get back production-ready 2D drawings:

| Output | Description |
|---|---|
| `floor_plan.dxf` | Horizontal section cut at 1.0m (standard) |
| `elevation_north.dxf` | North-facing orthographic elevation |
| `elevation_south.dxf` | South-facing orthographic elevation |
| `elevation_east.dxf` | East-facing orthographic elevation |
| `elevation_west.dxf` | West-facing orthographic elevation |
| `section_AA.dxf` | Custom vertical section cuts (you define them) |

All drawings include:
- Correct line layers (Floor Plan, Elevations, Sections, Dimensions)
- Auto-dimensioned overall width and height
- Title block with project name, drawing label, scale

## Quickstart

```bash
git clone https://github.com/dk001-ui/interior-design-3d-to-2d
cd interior-design-3d-to-2d
pip install -r requirements.txt

# Export your SketchUp model as COLLADA (.dae) first:
# File > Export > 3D Model > COLLADA (.dae)

python extract.py --input model.dae
```

Output files appear in `output/` — open them in AutoCAD, FreeCAD, or LibreCAD.

## Parameters

Edit `config.py` (or pass a custom config with `--config`):

```python
CONFIG = {
    "project_name":  "Site A — Living Room",
    "room_height":    3.0,    # metres — floor to ceiling
    "sill_height":    0.9,    # metres — bottom of window
    "lintel_height":  2.1,    # metres — top of window
    "door_height":    2.1,    # metres
    "wall_thickness": 0.23,   # metres
    "cut_height":     1.0,    # floor plan section height
    "scale":          50,     # 1:50
}
```

## CLI options

```bash
# Basic
python extract.py --input model.dae

# Override parameters inline (no need to edit config.py)
python extract.py --input model.dae --room-height 3.2 --scale 100

# Custom output directory
python extract.py --input model.dae --output output/site_A

# Generate only floor plan
python extract.py --input model.dae --only floor_plan

# Custom config per project
python extract.py --input model.dae --config projects/site_B/config.py
```

## Adding section cuts

In `config.py`:

```python
"sections": [
    {"name": "section_AA", "axis": "y", "position": 3.0},
    {"name": "section_BB", "axis": "x", "position": 2.5},
]
```

## Supported input formats

| Format | How to get it | Quality |
|---|---|---|
| `.dae` (COLLADA) | File > Export > 3D Model in SketchUp | Best |
| `.skp` | Direct (trimesh fallback) | Good for SketchUp 2021+ |

## Output opens in

- AutoCAD (all versions)
- FreeCAD (free)
- LibreCAD (free)
- BricsCAD
- Any DXF-compatible viewer

## Architecture

```
interior-design-3d-to-2d/
├── extract.py          # CLI entrypoint
├── config.py           # Project parameters
├── parser/
│   ├── collada.py      # COLLADA (.dae) parser
│   └── skp.py          # SKP parser (trimesh + CLI fallback)
├── core/
│   ├── slicer.py       # 3D → 2D geometry slicer
│   └── exporter.py     # DXF writer with dimensions + title block
└── output/             # Generated .dxf files (gitignored)
```

## Contributing

PRs welcome. See open issues for roadmap items:
- [ ] Reflected ceiling plan
- [ ] Furniture schedule extraction
- [ ] IFC export (BIM format)
- [ ] Web UI (drag & drop .dae → download .dxf)
- [ ] Batch processing multiple rooms

## License

MIT

## Samples

| File | Description |
|---|---|
| [sample_floor_plan.dxf](samples/sample_floor_plan.dxf) | Sample 2BHK apartment floor plan — ready to open in AutoCAD or FreeCAD |
| [before_after.png](samples/before_after.png) | Before/after comparison — 3D SketchUp model vs clean 2D CAD output |
| [pitch_deck.pdf](samples/pitch_deck.pdf) | Client pitch deck with pricing and workflow overview |

### Before / After

![Before/After](samples/before_after.png)

## Research

| Topic | File |
|---|---|
| Solana Trading Strategies | [research/solana-trading-strategies.md](research/solana-trading-strategies.md) |
