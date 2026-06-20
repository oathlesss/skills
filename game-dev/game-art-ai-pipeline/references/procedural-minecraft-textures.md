# Procedural Minecraft Textures with Pillow

When the task is generating 16×16 or 32×32 pixel art textures for Minecraft mods (items, blocks, icons), procedural generation with Python Pillow is superior to AI pipelines (ComfyUI/SDXL). AI blurs at small scales, doesn't understand pixel grids, and needs manual cleanup anyway. Procedural scripts are deterministic, instant, and perfectly clean.

## Setup (PEP 668 safe)

```bash
uv venv && source .venv/bin/activate && uv pip install Pillow
```

No GPU. No CUDA. No model downloads. Runs in milliseconds.

## Architecture pattern

Organize scripts as:
```python
# Per-texture helper functions
def draw_crystal(draw, colors): ...     # diamond/octahedron gem
def draw_shard(draw, colors): ...       # irregular broken fragment
def draw_ingot(draw, base, hi, lo): ... # flat bar with bevel
```

Use a color dictionary for palette variants:
```python
PRIMALS = {
    "ignis": {"fill": (255,100,20), "edge": (200,50,10), "glow": (255,200,100)},
    "aqua":  {"fill": (60,130,255), "edge": (30,80,200), "glow": (180,220,255)},
    ...
}
```

Generate all variants by iterating the dictionary — change one color and all 6 crystals re-render.

## Proven texture shapes

### Gem/Crystal (16×16)
- Centered diamond polygon: `[(c,1), (15,c), (c,15), (1,c)]`
- Inner facet polygon (smaller, shifted up)
- Bright center ellipse for glow
- Darker outer polygon for edge definition
- Works for: vis crystals, gems, orbs

### Shard (16×16)
- Irregular asymmetric polygon: `[(7,2), (13,7), (10,13), (3,10)]`
- Smaller than a crystal, offset for organic feel
- Bright highlight on one edge only
- Works for: crystal fragments, broken pieces, splinters

### Ingot (16×16)
- Rounded rectangle: `(2,5) → (13,10)`, radius=1
- Top edge line in highlight color (bevel)
- Bottom edge line in shadow color (bevel)
- Optional rune line or glow detail
- Works for: all metal bars, processed materials

### Minor variations
- **Nitor**: Teardrop flame polygon with bright white-hot core dot
- **Alumentum**: Ellipse with dark crack lines and glowing outline
- **Book/Thaumonomicon**: Polygon cover (angled rectangle), page edge lines, cover rune
- **Stone block item**: Rectangle with pattern lines and outline

## Vision model verification

After generating, verify readability at scale:
```
vision_analyze(image, "What does this 16x16 pixel art look like? 
Is it readable as a [intended item] at Minecraft scale?")
```

The vision model reliably catches: shape ambiguity, readability issues, color confusion.

## Real-world throughput

| Asset type | Script time | Per-texture generation |
|------------|-------------|----------------------|
| 6 crystals (primal variants) | 1 script | <1s for all 6 |
| 6 shards | 1 script | <1s for all 6 |
| 3 ingots | 1 function call each | <1s for all 3 |
| Total batch (19 textures) | ~200 lines | <1 second |

Compare to AI pipeline: 30+ min setup, seconds per generation, 2–5 min manual cleanup per texture = ~1 hour for the same 19 textures, with worse results.

## When AI is still better (and when it isn't)

| Texture type | Procedural | AI pipeline |
|-------------|-----------|------------|
| Geometric items (ingots, crystals, shards) | ✅ Best | ❌ Blurred, inconsistent |
| Pattern blocks (bricks, tiles, planks) | ✅ Best | ❌ Can't maintain grid |
| Organic textures (taint growth, fibrous blocks) | ⚠️ Possible with noise | ✅ Better for organic shapes |
| Entity textures (golems, creatures) | ❌ Too complex | ⚠️ Needs heavy cleanup |
| GUI/layouts | ❌ Not applicable | ✅ Good for mockups |

## Pitfalls

- Pillow `draw.rounded_rectangle` needs Pillow ≥ 9.0 (modern versions fine)
- Always use RGBA mode — `Image.new("RGBA", (16,16), (0,0,0,0))`
- Outline with alpha for anti-aliased edges: `outline=(0,0,0,80)`
- At 16×16, 1-pixel offsets matter — test each shape against vision model
- Don't try to generate entity textures or complex UI procedurally — those need manual art
