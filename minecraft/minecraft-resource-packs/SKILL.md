---
name: minecraft-resource-packs
description: Build Faithful-style (2x-upscaled) resource packs for modded Minecraft — extract mod textures from jars, upscale with a corner-preserving pixel-art scaler, and package into an installable pack.
triggers:
  - Making a "Faithful-style" or 32x resource pack for a modpack
  - Upscaling or bulk-transforming Minecraft mod textures
  - Building a resource pack that covers a modpack's items/blocks
  - Extracting textures from mod jars and repackaging them
---

# Minecraft Resource Pack Generation (Faithful-style upscaling)

## Set expectations first

A *true* Faithful pack is hand-repainted 2x textures produced by a multi-contributor team
over years — **not** automatable in one session. What IS automatable: a **clean 2x upscale of
every mod texture** with a pixel-art scaler ("Faithful-ish", the ~80% case). State this
upfront, then deliver the pipeline. The remaining 20% (hand-painted interior detail/bevels) is
the honest gap.

## Pipeline

1. Enumerate the pack's mod jars (e.g. `server/data/mods/*.jar`).
2. For each jar, walk `assets/<namespace>/textures/**/*.png`:
   - **SKIP the `minecraft` namespace** — the base Faithful/vanilla pack covers it, and a naive
     upscale would override the good hand-drawn vanilla textures.
   - Copy `*.png.mcmeta` verbatim (animated-texture metadata).
   - Only upscale textures with max dimension ≤ 32px; leave larger ones (atlases, GUI, already-hi-res) as-is.
3. Upscale each texture 2x with the **corner-guarded Scale2x** scaler (below).
4. Write `pack.mcmeta` (pack_format 34 for MC 1.21.1).
5. Zip the `assets/` tree + `pack.mcmeta` into `<name>.zip`.

Run `scripts/build_mod_resource_pack.py` (needs Pillow + numpy) — it implements all of the above.

## Scaler choice — the key findings (verified empirically)

- **Scale2x with a corner guard is the right scaler for Minecraft textures.** It preserves the
  palette exactly (no new colors) and stays crisp.
- **Super-xBR / xBR are WORSE here** — they target large retro-game sprites; on 16x16 Minecraft
  textures they over-smooth, introduce gradient colors, and look soft/"smudged" (confirmed via
  vision checks on real ingot + block textures). Don't reach for xBR as an "upgrade".
- **Naive Scale2x mangles 90° corners** — machine-block windows/frames become "squircles", stone
  noise becomes blobs. Fix with a **corner guard**: only smooth when the diagonal *continues*
  (`NE != SW` for top-left/bottom-right outputs, `NW != SE` for the other two). This keeps straight
  edges + corners crisp while still smoothing true diagonals.

Corner-guarded Scale2x (numpy, vectorized — the whole trick):

```python
def eq(a, b):
    return np.all(a == b, axis=-1)[..., None]  # (H,W,1) broadcasts over channels

def scale2x(arr):  # arr: HxWxC uint8
    H, W, C = arr.shape
    p = np.pad(arr, ((1,1),(1,1),(0,0)), mode="edge")
    NW=p[:-2,:-2]; N=p[:-2,1:-1]; NE=p[:-2,2:]
    W_=p[1:-1,:-2]; P=p[1:-1,1:-1]; E=p[1:-1,2:]
    SW=p[2:,:-2];  S=p[2:,1:-1];  SE=p[2:,2:]
    e0=np.where(eq(W_,N)&~eq(W_,S)&~eq(N,E)&~eq(NE,SW),W_,P)   # top-left
    e1=np.where(eq(N,E)&~eq(N,W_)&~eq(E,S)&~eq(NW,SE),N,P)     # top-right
    e2=np.where(eq(W_,S)&~eq(W_,N)&~eq(S,E)&~eq(NW,SE),W_,P)   # bottom-left
    e3=np.where(eq(S,E)&~eq(S,W_)&~eq(E,N)&~eq(NE,SW),S,P)     # bottom-right
    o=np.empty((H*2,W*2,C),dtype=arr.dtype)
    o[0::2,0::2]=e0; o[0::2,1::2]=e1; o[1::2,0::2]=e2; o[1::2,1::2]=e3
    return o
```

## Pitfalls

- **NumPy broadcasting bug**: a boolean condition of shape `(H,W)` used in `np.where` against
  `(H,W,C)` data raises "operands could not be broadcast together". Add `[..., None]` to the
  condition so it becomes `(H,W,1)`.
- **Pure nearest-neighbor 2x is pointless** as a resource pack — Minecraft already renders 16x
  textures with nearest upscale at draw time, so a plain 2x pack looks identical to vanilla.
  The *smoothing* is the entire value; the corner guard is what stops it from distorting geometry.
- **pack_format must match the MC version** (1.21.1 = 34). Wrong value → "incompatible pack" warning.
- **Verify visually before running the full batch** — test one *item* AND one *machine/tech block*.
  Items can look fine while tech blocks are silently distorted (the corner-rounding only shows on
  geometric textures).
- **Performance**: the full batch is ~70k textures / ~400 jars → runs in a few minutes in numpy
  (vectorized). If you port Super-xBR, numba JIT is the way (`@njit`); pure-Python per-pixel loops
  would take ~1.5h. Numba installs on recent Pythons; `math.ceil` returns `int` there, matching CPython.

## Verification

- After building, sanity-check the zip: `pack.mcmeta` present, a sample texture reads back at 32x32.
- Generate a before/after side-by-side and eyeball both an organic block AND a geometric machine block.

## Layering

The pack is designed to be loaded **above** a base vanilla-style pack (e.g. Classic Faithful 32x),
so vanilla keeps the hand-drawn base textures and this fills the mod gaps.
