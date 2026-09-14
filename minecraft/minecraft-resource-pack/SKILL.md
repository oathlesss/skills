---
name: minecraft-resource-pack
description: Build auto-upscaled (Faithful-style) resource packs for modded Minecraft — either by 2x-scaling every texture from a modpack's jars, or by upscaling an existing 16x retexture pack into a 32x "Faithful variant".
triggers:
  - "make a resource pack like Faithful but for the mods in [pack]"
  - "upscale / 2x / 32x the textures in this modpack"
  - "make a Faithful variant of [retexture/resource pack]"
  - Any request to auto-generate texture coverage for a modded Minecraft instance
---

# Minecraft Resource Pack Generation

Generate a 32x (or other 2x) resource pack that covers an entire modpack's textures by programmatically upscaling every texture found in the pack's mod jars.

## Core insight

Faithful-style texturing is a **systematic transform** (16x → 32x, same layout, added edge detail), not freehand art. A batch pipeline that extracts + 2x-upscales every texture with a pixel-art scaler produces a real, installable, 100%-coverage pack. This is *exactly* what an LLM writing a batch pipeline is good at. The hand-painted residual (bevels/gradients/noise inside each 2x2 block) is the ~20% a scaler can't fully replicate — be upfront about that gap rather than overselling.

## Before you generate: check the Faithful ecosystem

Faithful mod support already exists for many mods — don't regenerate what's already hand-drawn:

- Base vanilla pack: **Classic Faithful 32x** (faithfulpack.net/classic32x, Modrinth, CurseForge).
- Mod support: **Faithful 32x Mods** (GitHub `Faithful-Resource-Pack/Faithful-32x-Mods`, per-MC-version branch) or bundled **"Faithful 32x Modded"** on CurseForge.
- Coverage is broad but NOT 100% — newest/niche mods (Create Aeronautics, 2026 releases) are usually missing. Offer an audit: cross-reference the pack's manifest mod list vs the Faithful repo, and only auto-upscale the gaps.

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
- Only upscale **16-wide** textures (`width == 16`) — this includes tall animated strips (`16x80`, `16x352` → `32x160`, `32x704`) that the naive `max(w,h) <= 32` test would wrongly skip and leave misaligned against the upscaled block faces. Leave everything else untouched (GUIs, atlases, already-32+).
- **Two input modes:** (a) extract from mod jars (default); (b) upscale an *existing* resource pack — e.g. a 16x dark-mode retexture like AE2 Blackout. In mode (b) preserve `.png.mcmeta` AND non-texture files (block/item model JSONs, `pack.png`) verbatim, and rewrite only `pack.mcmeta`.
- Copy `*.png.mcmeta` verbatim to preserve animated-texture metadata.
- `pack.mcmeta` `pack_format`: 34 = 1.21.1 (32 = 1.20.5/6, 42 = 1.21.2/3, 46 = 1.21.4).
- Convert to RGBA and run the scaler on all 4 channels with color equality so alpha edges stay aligned.

## Variant: upscale an existing retexture pack (a "Faithful variant")

When the user wants a 32x "Faithful variant" of an existing 16x *retexture* pack (e.g. AE2 Blackout / AE2 Dark Mode dark-mode themes), the source is a single resource-pack zip, NOT mod jars:

- **Upscale rule differs:** use `width == 16` (not `max(w,h) <= 32`) so you also catch tall animated strips — `16x80 → 32x160`, `16x32 → 32x64`. The `max(w,h) <= 32` rule would wrongly leave `16x80` untouched because 80 > 32.
- **Leave GUIs/atlases untouched:** 256x256, 512x512, 128x128, 64x64, and odd-sized GUI sprites (7x15/12x15 scrollers, 200x20 buttons) are already high-res — upscaling them is wrong and bloats the pack.
- **Copy `*.png.mcmeta` AND `models/**/*.json` verbatim** (retexture packs often ship block/item model overrides).
- Rewrite `pack.mcmeta` (keep `pack_format`; new description), keep `pack.png`.
- Full recipe + CurseForge fetch: `references/retexture-pack-variant.md`.

## Pitfalls

- **NumPy broadcasting bug (vectorized pixel-art scalers):** a boolean condition of shape `(H,W)` will NOT broadcast against pixel data of shape `(H,W,4)` — NumPy aligns shapes from the right, so the last axis (16 vs 4) fails with "operands could not be broadcast together with shapes (16,16) (16,16,4) (16,16,4)". Fix: add a trailing axis to the condition — `np.all(a == b, axis=-1)[..., None]` → `(H,W,1)`.
- **Scaler quality tiers:** Scale2x (baseline: correct, ~20 lines, smooths diagonals) < xBR/hq2x (crisper, closer to Faithful). **Pick by texture style, not uniformly:** for fine technical geometry (circuit traces, thin grid lines, thin borders — AE2, Mekanism, Create) Scale2x leaves staircase jaggies; Super-xBR (numba-jitted, `superxbr_numba.py`) comes out clearly cleaner and closer to hand-painted Faithful. For a single-namespace override pack (e.g. AE2 Blackout layered over the main pack) it's fine to use xBR even when the main pack shipped Scale2x — the override wins the namespace anyway. Ship Scale2x as the default, offer xBR as a one-function swap + re-run when the pack is geometry-heavy. **Concrete finding:** for technical/geometric pixel art — AE2 circuitry, thin 1px lines, grid-based machines — Super-xBR is clearly better (Scale2x leaves staircase jaggies on 1px lines); for organic shapes Scale2x is fine. Before shipping, verify with a 3-way contact sheet (orig nearest-neighbour / Scale2x / xBR) inspected via vision_analyze.
- **Corner guard (naive Scale2x rounds 90° corners):** plain Scale2x smooths *every* diagonal, so machine-block windows/frames become "squircles". Add `NE != SW` / `NW != SE` conditions so a diagonal is only smoothed when it *continues* (a real diagonal, not an isolated corner) — exact code in `references/corner-guard-scale2x.md`. Note the residual: ~2% of pixels still get neighbor color-bleed at gradient boundaries (the `==` guard reads `[196,255,216]` vs `[137,255,184]` as "different"), which is invisible in normal play.
- **Pure nearest-neighbor 2x is pointless** — Minecraft already nearest-upscales 16x at render time, so a plain 2x pack looks identical to vanilla. The smoothing is the entire value.
- Don't upscale already-large textures — 32x→64x or 64x→128x is wrong and bloats the pack.
- A modpack's jar list includes library/API mods with no textures; "fewer mods with textures than jars" is expected, not a bug.

## Verification

- `zipfile` sanity: `pack.mcmeta` present, spot-check a texture is now 32x32 (`Image.open(...).size`).
- Visual before/after: upscaled output must look clean/recognizable — sharp edges, smoothed diagonals — not blurry or garbled. (Pattern: `scripts/make_comparison.py`.)

## Files

- `scripts/build_pack.py` — full working pipeline (extract + Scale2x 2x + package to zip).
- `superxbr_numba.py` (in working dir, not skill-bundled) — numba-jitted Super-xBR 2x scaler (use for technical/circuitry textures).
- `references/upscaling-existing-resource-pack.md` — mode B: Faithful-variant of a published pack (AE2 Blackout example), plus Modrinth/CurseForge download patterns.
- `references/fetch-faithful-base.md` — Modrinth API recipe for downloading the official Faithful 32x base pack.
- `references/retexture-pack-variant.md` — upscaling an existing 16x retexture pack (AE2 Blackout case) + CurseForge API fetch recipe.
- `references/corner-guard-scale2x.md` — exact corner-guarded Scale2x numpy code + "nearest-neighbor is pointless" note + verify-item-AND-machine-block pitfall.
- `references/scaler-tradeoffs.md` — full empirical scaler comparison (Scale2x vs corner-guard vs xBR vs nearest-neighbor) with the vision-verification method. Note: this records an *earlier* session's "xBR over-smooths" verdict; the body above refines it (Super-xBR is better for fine technical geometry, Scale2x/corner-guard for organic).
