---
name: minecraft-resource-pack-generation
description: Generate Faithful-style (2x upscaled) resource packs for modded Minecraft packs — extract textures from every mod jar, pixel-art upscale, and package into an installable resource pack.
triggers:
  - Making a Faithful-style or 32x or higher-resolution resource pack for a modpack
  - Upscaling modded Minecraft textures
  - Generating a resource pack that covers all mods in a modpack
  - Batch-transforming mod textures (extract, upscale, repackage)
---

# Minecraft Resource Pack Generation

## When this is tractable — don't reflexively say "too hard"

"Faithful-style pack for all 400 mods" *sounds* like freehand art (thousands of textures) but is actually a **systematic batch transform**: extract every texture from every mod jar → 2x pixel-art upscale → repackage. That's a great LLM/agent task and gets you ~80% of the Faithful look. What stays community-scale is *hand-painting* the interior detail (bevels/gradients/noise) inside each upscaled pixel — the upscale itself is fully automatable.

## THE key finding: Scale2x, NOT xBR

For Minecraft's 16×16 textures, **Scale2x beats xBR/Super-xBR** — the opposite of the usual assumption:

| Scaler | Result on 16x MC textures | Verdict |
|---|---|---|
| Nearest-neighbor 2x | Blocky, no real improvement | too crude |
| **Scale2x** (EPX/AdvMAME2x family) | Crisp edges, smooth diagonals, exact palette, zero color bleed | **use this** — closest to Faithful |
| xBR / Super-xBR / xBRZ | Soft, anti-aliased, introduces gradient colors, "smudged" | looks like a low-quality vector trace |

xBR-family scalers are built for *large retro-game sprites*; on tiny Minecraft textures they over-smooth and destroy the crisp pixel-art look Faithful preserves. Verified visually (vision check): Scale2x → "crisp, faithful 2x"; Super-xBR → "soft, blurry, color bleeding". So the counterintuitive lesson: the "higher-quality" scaler is the *wrong* one here.

## Pipeline

1. **Source jars** — the pack's `mods/` dir (server `/data/mods/` or client `mods/`).
2. **Extract** `assets/<namespace>/textures/**/*.png` from each jar.
3. **Upscale 2x** with Scale2x (numpy-vectorized — see `scripts/build_pack.py`).
4. **Package** into a zip with `pack.mcmeta`.

Rules that matter:
- **Skip the `minecraft` namespace.** Vanilla is covered by the base "Classic Faithful 32x" pack; your pack layers *on top* to fill the mod gaps. Upscaling vanilla yourself would override Faithful's nicer hand-drawn art with your automated output.
- **Only upscale textures whose max dimension ≤ 32px.** 64px+ are already high-res, atlases, or GUIs — leave them untouched.
- **Copy `.png.mcmeta` verbatim** (animated-texture metadata).
- **pack_format**: 34 for 1.21.0/1.21.1 (re-check per MC version).

## Performance

A pure-Python per-pixel scaler is ~1M ops/texture → ~1.5 h for ~57k textures. Scale2x vectorizes cleanly in numpy (no JIT). For xBR-class scalers that must stay per-pixel (Super-xBR), wrap in `numba @njit` → C speed (numba 0.67 works on Python 3.14). Full run is ~400 jars / ~69k textures / ~127 MB output zip in a few minutes.

## Pitfalls

- **NumPy broadcasting bug**: a boolean edge mask of shape `(H,W)` won't broadcast against `(H,W,4)` pixel data — append `[..., None]` to make it `(H,W,1)`.
- ~100 of 400 jars are libraries/API mods with no textures — nothing is "missing", that's expected.
- numba `math.ceil` returns int (matches CPython) and the float arithmetic is bit-identical to CPython, so a numba port of an xBR reference is safe to trust for branch logic — tiny ±1 pixel diffs on anti-aliased edges are expected float noise, not bugs.

## The "already exists" answer (Faithful ecosystem)

Before generating, check the Faithful project — mod support already exists for many mods:
- Base vanilla pack: **Classic Faithful 32x** (faithfulpack.net/classic32x, Modrinth, CurseForge).
- Mod support: **Faithful 32x Mods** (GitHub `Faithful-Resource-Pack/Faithful-32x-Mods`, per-MC-version branch) or bundled **"Faithful 32x Modded"** on CurseForge.
- Coverage is broad but NOT 100% — newest/niche mods (Create Aeronautics, 2026 releases) are usually missing. Offer an audit: cross-reference the pack's manifest mod list vs the Faithful repo.

## Verification

- `pack.mcmeta` present in the zip with the correct pack_format.
- Spot-check one texture is now 32×32.
- Generate a before/after comparison image (original 16x vs 2x output) and eyeball it.

## Scripts

- `scripts/build_pack.py` — working Scale2x extract→upscale→package pipeline (numpy + Pillow).
