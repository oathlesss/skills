# Procedural Minecraft Texture Generation (Pillow)

Pattern for generating 16×16 item textures with Python + Pillow. No GPU, no AI tools, deterministic output.

## Setup (PEP 668 safe)

```bash
cd /path/to/project && uv venv && source .venv/bin/activate && uv pip install Pillow
```

## Pattern

```python
from PIL import Image, ImageDraw

SIZE = 16
OUT = Path("src/main/resources/assets/<modid>/textures/item")

def new_image() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)

def save(img: Image.Image, name: str):
    img.save(OUT / f"{name}.png")
```

## Shape templates

### Crystal/Gem (diamond with glow)
```python
c = SIZE // 2
outer = [(c, 1), (SIZE - 2, c), (c, SIZE - 2), (1, c)]      # outer diamond
inner = [(c, 3), (SIZE - 4, c + 1), (c, SIZE - 4), (3, c + 1)] # inner facet
glow_rect = [(c - 2, c - 2), (c + 2, c + 2)]                   # center glow

draw.polygon(outer, fill=colors["edge"])
draw.polygon(inner, fill=colors["fill"])
draw.polygon([(c, 2), (SIZE - 3, c), (c, c + 1), (3, c)], fill=colors["glow"])
draw.ellipse(glow_rect, fill=colors["glow"])
draw.polygon(outer, outline=(0, 0, 0, 80), width=1)
```

### Shard (jagged, asymmetrical)
```python
pts = [(7, 2), (13, 7), (10, 13), (3, 10)]          # outer
inner = [(7, 4), (11, 7), (9, 11), (5, 9)]           # inner

draw.polygon(pts, fill=colors["edge"])
draw.polygon(inner, fill=colors["fill"])
draw.line([(7, 2), (13, 7)], fill=colors["glow"], width=1)
draw.polygon(pts, outline=(0, 0, 0, 80), width=1)
```

### Ingot (horizontal bar with bevel)
```python
x0, y0, x1, y1 = 2, 5, 13, 10
draw.rounded_rectangle([x0, y0, x1, y1], radius=1, fill=base)
draw.line([(x0 + 1, y0), (x1 - 1, y0)], fill=highlight, width=1)  # top bevel
draw.line([(x0 + 1, y0 + 1), (x1 - 1, y0 + 1)], fill=highlight, width=1)
draw.line([(x0 + 1, y1), (x1 - 1, y1)], fill=shadow, width=1)     # bottom bevel
draw.rounded_rectangle([x0, y0, x1, y1], radius=1, outline=(0, 0, 0, 100), width=1)
```

### Sphere with cracks (dense/charged items)
```python
draw.ellipse([3, 2, 12, 13], fill=(200, 100, 10, 255))
draw.line([(5, 4), (9, 8)], fill=(40, 20, 5, 200), width=1)  # crack 1
draw.ellipse([3, 2, 12, 13], outline=(255, 180, 50, 220), width=1)  # glow edge
```

### Block item (stone with rune)
```python
draw.rectangle([2, 2, 13, 13], fill=(40, 35, 55, 255))   # dark base
draw.rectangle([4, 4, 11, 11], fill=(55, 48, 72, 255))   # lighter center
draw.line([(7, 4), (7, 11)], fill=(120, 100, 180, 100))  # rune cross
draw.line([(4, 7), (11, 7)], fill=(120, 100, 180, 100))
draw.rectangle([2, 2, 13, 13], outline=(20, 18, 30, 200))
```

## Verification

After generation, visually verify with `vision_analyze` at the intended scale. Key checks:
- Silhouette is readable at 16×16 (item inventory size)
- Colors don't blend into darkness or bloat into bright areas
- The item's identity is clear without text/tooltip

## Limitations

- Cannot produce organic/curved textures well (taint, fibrous growth, golem bodies)
- Pattern-based blocks work well; irregular natural textures need manual touch-up
- For organic textures: use procedural noise as a base, then manual Aseprite overlay

## Reference implementation

See `/home/ruben/thaumcraft-textures/generate_materials.py` for the full working script from the Thaumcraft Phase 1 batch — 19 textures across crystals, shards, ingots, and special items in a single deterministic script.
