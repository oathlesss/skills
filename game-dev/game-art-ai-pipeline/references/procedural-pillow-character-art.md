# Procedural Character Art with Pillow

When AI image generation tools (ComfyUI, image_gen toolset) are unavailable and you need quick character/avatar concepts, Pillow + procedural polygon drawing is a viable fallback for stylized silhouettes.

## Setup (PEP 668 safe)

```bash
cd /tmp && uv venv bodygen
source bodygen/bin/activate
uv pip install Pillow
```

Then run generation scripts with `/tmp/bodygen/bin/python`.

## Core technique: polygon silhouette figures

Build figures from ordered polygon points tracing the body outline. Key principles:

1. **Define body landmarks as (x, y) tuples** — head_top, eye_y, chin_y, shoulder_y, chest_y, waist_y, hip_y, glute_peak_y, knee_y, ankle_y, etc.
2. **Trace clockwise around the figure** — front of face, down front of body, under feet, up back, over glutes, up back to head.
3. **Use separate polygons for body parts** — avoids smoothing algorithms merging limbs into blobs. Head, torso, each arm, each glute, each leg as distinct shapes.
4. **Add muscle/definition lines** — thin arcs and lines at chest, abs, glute fold, thigh, calf for anatomical readability.

## Critical pitfalls

- **Front view can't show glutes.** Side profile or 3/4 back view is required for posterior visibility. A front-facing "hip block" reads as pelvis, not glutes.
- **Smooth interpolation merges adjacent limbs.** Catmull-Rom or similar curve smoothing on a full-body outline will merge legs into a single pillar. Draw body parts as separate filled polygons instead.
- **Pillow arc angles are degrees, not radians.** `draw.arc(bbox, start, end)` uses degrees — 0 is 3 o'clock, increasing counterclockwise.
- **The vision model will critique honestly.** Use `vision_analyze` after each generation to catch proportion issues, merged limbs, and readability problems. The vision model caught: "legs merged into pillar," "glutes not visible from front," "figure looks like a penguin" (yellow delta mistaken for beak).

## Iteration workflow

1. Generate image with Pillow script
2. Call `vision_analyze(image, "Describe proportions, anatomy, readability...")` 
3. Read vision model feedback
4. Patch script to fix identified issues
5. Repeat until vision model confirms design intent

## Proven figure template (side profile)

See the side-profile silhouette pattern from this session for a working reference. The key is the glute curve:

```python
# Glute peak (maximum posterior projection)
profile_pts.append((bx + 50, glute_peak_y))
profile_pts.append((bx + 45, glute_peak_y - 30))  # upper curve
# ... then taper to lower back and back of thigh
```

With a separate glute fold line for definition:
```python
draw.line([(bx+15, glute_bottom_y+10), (bx+45, glute_bottom_y+10)],
          fill=(32, 44, 62, 80), width=2)
```

## Color palette (Diaktoros / Hermes theme)

- Body fill: `(18, 24, 48, 255)` — deep navy
- Body outline: `(60, 100, 210, 180)` — blue glow
- Core glow: `(70, 130, 230)` → `(150, 200, 255)` — layered circles for reactor effect
- Delta (Δ): `(255, 255, 255, 230)` fill, `(200, 160, 50, 140)` outline — white with gold accent
- Background: deep void gradient `(5,3,14)` → `(9,5,24)`
- Vein/circuit lines: `(80, 140, 235, 60)` — subtle blue
- Definition lines: `(30, 42, 65, 70)` — darker than body for muscle contour

## When to use vs AI generation

| Aspect | Pillow procedural | ComfyUI/SDXL |
|--------|------------------|--------------|
| Setup time | ~30s (uv + Pillow) | 30+ min (CUDA, models, nodes) |
| Output quality | Stylized geometric only | Photorealistic or varied styles |
| Iteration speed | Instant (script rerun) | Seconds per generation |
| Consistency | Perfect (deterministic) | Variable (seed-dependent) |
| Best for | Quick silhouettes, concept blocking, avatar placeholders | Production assets, final art, varied styles |
