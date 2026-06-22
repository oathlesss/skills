# Procedural Minecraft Textures with Pillow

Generate 16×16 item/block textures via Python + Pillow. Faster than AI for pixel art, deterministic output, instantly re-renderable.

## Setup

```bash
cd /path/to/project
uv venv && source .venv/bin/activate
uv pip install Pillow
```

## Template script structure

```python
from PIL import Image, ImageDraw
import random

SIZE = 16

def new_image():
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)

def save(img, path): img.save(path, "PNG")
```

## Pattern: Crystal (gem/diamond shape)

```python
def draw_crystal(draw, color_fill, color_edge, color_glow):
    c = SIZE // 2
    outer = [(c, 1), (SIZE - 2, c), (c, SIZE - 2), (1, c)]
    inner = [(c, 3), (SIZE - 4, c + 1), (c, SIZE - 4), (3, c + 1)]
    draw.polygon(outer, fill=color_edge)
    draw.polygon(inner, fill=color_fill)
    draw.ellipse([c-2, c-2, c+2, c+2], fill=color_glow)
    draw.polygon(outer, outline=(0,0,0,80))
```

## Pattern: Ingot (flat bar with bevel)

```python
def draw_ingot(draw, base, highlight, shadow):
    x0, y0, x1, y1 = 2, 5, 13, 10
    draw.rounded_rectangle([x0, y0, x1, y1], radius=1, fill=base)
    draw.line([(x0+1, y0), (x1-1, y0)], fill=highlight, width=1)
    draw.line([(x0+1, y1), (x1-1, y1)], fill=shadow, width=1)
    draw.rounded_rectangle([x0, y0, x1, y1], radius=1, outline=(0,0,0,100))
```

## Pattern: Shard (asymmetric, jagged)

```python
def draw_shard(draw, color_fill, color_edge, color_glow):
    pts = [(7, 2), (13, 7), (10, 13), (3, 10)]  # irregular
    inner = [(7, 4), (11, 7), (9, 11), (5, 9)]
    draw.polygon(pts, fill=color_edge)
    draw.polygon(inner, fill=color_fill)
    draw.line([(7, 2), (13, 7)], fill=color_glow, width=1)
    draw.polygon(pts, outline=(0,0,0,80))
```

## Pattern: Stone/block (noise base with pattern)

```python
def draw_stone(draw, base_rgb_range, accent_color, accent_alpha):
    for y in range(SIZE):
        for x in range(SIZE):
            r = random.randint(*base_rgb_range)
            g = random.randint(*base_rgb_range)
            b = random.randint(*base_rgb_range)
            draw.point((x, y), fill=(r, g, b, 255))
    # Add pattern (bricks, tiles, runes, etc.)
    draw.line([(7, 2), (7, 13)], fill=accent_color + (accent_alpha,), width=1)
```

## Pattern: Tree log (bark with cut ends)

```python
def draw_log(draw, bark_color, cut_color, vein_color=None):
    for y in range(SIZE):
        for x in range(SIZE):
            base = bark_color + random.randint(-8, 8)
            draw.point((x, y), fill=(base, base-10, base+5, 255))
    # Bark lines
    for i in range(3):
        draw.line([(0, random.randint(3,12)), (15, random.randint(3,12))], fill=(140,135,150,100))
    # Cut ends
    draw.rectangle([2, 0, 13, 2], fill=cut_color)
    draw.rectangle([2, 14, 13, 15], fill=cut_color)
```

## Full example script

See `/home/ruben/thaumcraft-textures/generate_materials.py` for a complete working example generating 19 textures (crystals, shards, ingots, nitor, alumentum, etc.).
