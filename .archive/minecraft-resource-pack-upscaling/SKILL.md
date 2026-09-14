---
name: minecraft-resource-pack-upscaling
description: Build a Faithful-style / higher-resolution Minecraft resource pack from a modpack's textures. Extract textures from mod jars, 2x-upscale with pixel-art scalers (Scale2x with corner guard), package into an installable pack. Covers scaler tradeoffs and the hard limit of automated upscaling.
---

# Minecraft Resource Pack Upscaling

Make a "Faithful-style" 32x resource pack covering a modpack's textures by
batch-extracting and 2x-upscaling every texture. The result layers *above* the
base Faithful pack, filling the mod-texture gaps (vanilla stays Faithful's
hand-drawn art).

## When to use
- "make a Faithful-style / 32x pack for modpack X"
- "upscale all the textures in my modpack so they match a 32x pack"
- turning 16x mod textures into 32x for consistency

## Pipeline (reusable script: `scripts/build_pack.py`)
1. **Extract** — for each `mods/*.jar`, read `assets/<ns>/textures/**/*.png`.
   **Skip the `minecraft` namespace**: the base Faithful pack covers vanilla, and
   your upscale would override its hand-drawn art with a scaler result. Copy
   `.png.mcmeta` files verbatim (animated-texture metadata).
2. **Upscale 2x** — apply the corner-guarded Scale2x in the script (best
   artifact/quality tradeoff for Minecraft, see below).
3. **Package** — write `pack.mcmeta` + textures into a zip. `pack_format` MUST match
   the MC version: 1.21/1.21.1 = **34**, 1.20.5/6 = 32, 1.21.4 = 46.

Run: `python build_pack.py --mods-dir <mods dir> --out-dir <dir>`
(requires Pillow + numpy; `uv pip install pillow numpy` in a venv).

## Upscaler choice (the part that matters)
- **Nearest-neighbor 2x** — zero artifacts, but *visually identical to vanilla 16x*
  (Minecraft already nearest-upscales at render time). Pointless as a pack.
- **Scale2x** — crisp, preserves palette exactly, smooths diagonals. But rounds 90°
  corners → machine blocks look "rubbery".
- **Scale2x + corner guard** (in script) — only smooth when the diagonal actually
  *continues* (`NE != SW`, `NW != SE`). Fixes corner-rounding. Still leaves ~2% of
  pixels with color-bleed on gradient boundaries (see hard limit).
- **xBR / Super-xBR** — over-smooths 16x textures, *introduces new gradient colors*,
  looks blurry/"muddy". Wrong tool for Minecraft. (numba port notes in the reference.)

## The hard limit (set this expectation early, and push back if the user insists it's "easy")
Faithful is **NOT edge-smoothing** — it's *hand-drawn interior detail* (bevels,
gradients inside each 2x2 block), produced by dozens of contributors over years.
No rule-based scaler reproduces that, and every edge-smoother artifacts on
Minecraft's fine patterns and color gradients (which use slightly-different shades
of the same hue). A user who says "Faithful textures are predictable, an LLM can
just make them" is half-right: the *pipeline* is a great LLM task, but the
*quality ceiling* is "98% exact + subtle single-pixel artifacts on gradient edges"
— visible when zoomed, invisible in normal play. For truly clean results the
community's hand-drawn Faithful mod pack is the only option, and it covers only
the big mods.

## Pitfalls
- **numpy broadcasting** — a boolean mask of shape `(H,W)` won't broadcast against
  pixel data `(H,W,C)`; add `[..., None]` to the mask.
- **Exact-equality scalers misread gradients** — `(196,255,216)` vs `(137,255,184)`
  are "different" to `==` but the same mint to the eye. A threshold loose enough to
  treat them equal blurs genuinely-different colors, so don't chase it.
- **Pure-Python per-pixel loops are far too slow** for tens of thousands of
  textures. Vectorize with numpy, or JIT with `numba` `@njit` (numba's `math.ceil`
  returns int, matching CPython — verified in this session).
- **Wrong `pack_format`** → Minecraft rejects the pack or shows the wrong version.

See `references/scaler-tradeoffs.md` for the full comparison and the concrete
session data behind these conclusions.
