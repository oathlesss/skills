---
name: minecraft-resource-pack
description: Build auto-upscaled (Faithful-style) resource packs for modded Minecraft by extracting and 2x-scaling every texture from a modpack's jars.
triggers:
  - "make a resource pack like Faithful but for the mods in [pack]"
  - "upscale / 2x / 32x the textures in this modpack"
  - Any request to auto-generate texture coverage for a modded Minecraft instance
---

# Minecraft Resource Pack Generation

Generate a 32x (or other 2x) resource pack that covers an entire modpack's textures by programmatically upscaling every texture found in the pack's mod jars.

## Core insight

Faithful-style texturing is a **systematic transform** (16x → 32x, same layout, added edge detail), not freehand art. A batch pipeline that extracts + 2x-upscales every texture with a pixel-art scaler produces a real, installable, 100%-coverage pack. This is *exactly* what an LLM writing a batch pipeline is good at. The hand-painted residual (bevels/gradients/noise inside each 2x2 block) is the ~20% a scaler can't fully replicate — be upfront about that gap rather than overselling.

## Steps

1. **Venv** (system python has no pip; `uv` is available):
   ```bash
   uv venv .venv && uv pip install --python .venv/bin/python pillow numpy
   ```
2. Copy `scripts/build_pack.py` into the task dir and run:
   ```bash
   .venv/bin/python build_pack.py --mods-dir /path/to/mods
   ```
3. Verify (see below), then install: drop the zip in `resourcepacks/`, load it **above** a base 32x pack (e.g. Classic Faithful 32x) so vanilla keeps the hand-painted base and this pack only fills mod gaps.
4. Obtain the base Faithful 32x pack from Modrinth if you don't already have it — see `references/fetch-faithful-base.md` for the API recipe and quirks.

## Key implementation details

- Extract `assets/<ns>/textures/**/*.png` from every jar; write to the **same relative path** (that *is* the resource-pack layout).
- **Skip the `minecraft:` namespace** — the base Faithful pack covers vanilla better than an auto-upscale would.
- Only upscale textures with `max(w,h) <= 32`; leave larger (atlases, GUIs, already-high-res) untouched.
- Copy `*.png.mcmeta` verbatim to preserve animated-texture metadata.
- `pack.mcmeta` `pack_format`: 34 = 1.21.1 (32 = 1.20.5/6, 42 = 1.21.2/3, 46 = 1.21.4).
- Convert to RGBA and run the scaler on all 4 channels with color equality so alpha edges stay aligned.

## Pitfalls

- **NumPy broadcasting bug (vectorized pixel-art scalers):** a boolean condition of shape `(H,W)` will NOT broadcast against pixel data of shape `(H,W,4)` — NumPy aligns shapes from the right, so the last axis (16 vs 4) fails with "operands could not be broadcast together with shapes (16,16) (16,16,4) (16,16,4)". Fix: add a trailing axis to the condition — `np.all(a == b, axis=-1)[..., None]` → `(H,W,1)`.
- **Scaler quality tiers:** Scale2x (baseline: correct, ~20 lines, smooths diagonals) < xBR/hq2x (crisper, closer to Faithful). Ship Scale2x first, offer xBR as a one-function swap + re-run upgrade.
- Don't upscale already-large textures — 32x→64x or 64x→128x is wrong and bloats the pack.
- A modpack's jar list includes library/API mods with no textures; "fewer mods with textures than jars" is expected, not a bug.

## Verification

- `zipfile` sanity: `pack.mcmeta` present, spot-check a texture is now 32x32 (`Image.open(...).size`).
- Visual before/after: upscaled output must look clean/recognizable — sharp edges, smoothed diagonals — not blurry or garbled. (Pattern: `scripts/make_comparison.py`.)

## Files

- `scripts/build_pack.py` — full working pipeline (extract + Scale2x 2x + package to zip).
- `references/fetch-faithful-base.md` — Modrinth API recipe for downloading the official Faithful 32x base pack.
