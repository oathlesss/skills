# Scaler tradeoffs — session findings

All conclusions come from actually running each scaler on real ATM10 Aeronautics
(Mekanism) textures and inspecting results with a vision model.

## Scale2x (base)
- **Crisp**, keeps palette *exactly*, no blur, no new colors.
- Smooths diagonals but **rounds 90° corners** → machine blocks with rectangular
  windows/frames look "rubbery"/"melted"; the window becomes a "squircle".
- Fine for items + organic blocks (ingots, ores, stone).

## Scale2x + corner guard (chosen)
Adds `NE != SW` / `NW != SE` conditions so a diagonal is only smoothed when it
*continues* (a real diagonal, not an isolated corner).
- Fixes the corner-rounding: windows/frames/bars stay crisp 90°.
- **Residual limitation**: ~2% of pixels still get a neighbor color bleeding in at
  *gradient boundaries*. Example: the dark-green "bar" in Mekanism's
  advanced_induction_cell — its mint surroundings are `[196,255,216]`,
  `[178,255,204]`, `[137,255,184]`, i.e. *different shades of the same mint*. The
  guard compares with exact `==`, so those read as "different" and smoothing slips
  through. 6 of 256 pixels affected on that texture.

## xBR / Super-xBR
- Hyllian's algorithm, MIT. Reference Python port: `tpainter/python-superxBR`
  (adaptation of the pastebin `cbH8ZQQT` original).
- On 16x Minecraft textures it **over-smooths and introduces new gradient colors**
  (blending), producing a soft "anti-aliased / smudged" look — *opposite* of
  Faithful's crisp pixel art. Wrong tool for this job.
- Porting to `numba @njit` keeps the algorithm byte-identical and runs at C speed
  (a pure-Python 3-pass loop is ~100x too slow for tens of thousands of textures).
  numba `math.ceil` returns int (verified), matching CPython.

## Nearest-neighbor 2x
- Zero artifacts, but visually identical to vanilla 16x (the game already
  nearest-upscales at render time). Pointless as a pack.

## The fundamental limit
Faithful = hand-drawn *interior detail* (bevels, gradients within each 2x2 block),
not edge-smoothing. It's produced by dozens of contributors over years. No
rule-based scaler reproduces it, and every edge-smoother artifacts on Minecraft's
fine patterns + color gradients. The honest ceiling for automated upscaling is
"~98% exact, subtle single-pixel artifacts on gradient edges — invisible in normal
play, visible when zoomed". Don't over-promise "clean Faithful" to the user.

## How to verify before shipping
Generate a before/after montage (original vs upscale, `Image.NEAREST` display
scale) and run `vision_analyze` on it asking specifically about crispness, blur,
color bleeding, and corner fidelity. This caught both the corner-rounding (Scale2x)
and the gradient-bleed (corner guard) that manual inspection missed.
