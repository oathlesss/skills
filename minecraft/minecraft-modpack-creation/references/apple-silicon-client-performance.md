# Apple Silicon (macOS) client performance + shader/DH compatibility

How to diagnose and fix low FPS for a Minecraft client running on an Apple Silicon Mac, and which
shaderpacks work on macOS + Distant Horizons. Verified Oct 2026 on an M2 Pro / NeoForge 26.1.2 /
Sodium 0.9.2 / Iris 1.11.4 / DH 3.3.3.

## Root cause of "low" FPS on Macs: the OpenGL-on-Metal ceiling
Sodium (and Minecraft's whole renderer) on macOS goes through Apple's **deprecated
OpenGL-on-Metal translation layer (OpenGL 4.1)**. This is a hard performance ceiling — not a pack
problem, not a settings problem. An M2 Pro running a ~180-mod pack at **~90 FPS (no shaders)** is
normal for OpenGL. Shaders add more cost on top of that same ceiling.

## The fix: a native Metal backend (trade-off, not free)
- **MetalForge** — GitHub `LeadFreeCandy/metalforge`, "native Apple Metal renderer for Minecraft on
  NeoForge 26.1.2 (ported from mcopt), works with Sodium, smooth frame pacing". Client-only,
  arm64-only (Apple Silicon M1+, macOS 14+), Java 25. Roughly **2× FPS** (their bench: 124–151 → 287–294
  fps standing; 97–118 → 189–225 turning, on a *fanless* M2 Air with FTB Evolution 2 / 420 mods).
  Drop-in jar: `metalforge-26.1.2-<ver>.jar`.
- **Compatibility is the catch — MetalForge is mutually exclusive with shaders AND Distant Horizons:**
  - **Iris / shaderpacks** → with Iris installed, MetalForge silently falls back to OpenGL (no boost).
    Shader packs *require* OpenGL.
  - **Distant Horizons** → DH renders LODs via direct OpenGL calls, which "draw nothing on Metal".
  - So: max FPS (Metal) = no shaders + no DH. Shaders/far-render = stay on OpenGL.
- MetalForge settings worth remembering: **VSync ON** (its "smooth pacing" turns uneven 90 fps into
  evenly-spaced frames); on Java 25 use `-XX:+UseZGC`; give big packs 10–12 GB heap (8 GB stalls GC).
  Its benchmark ran render distance 20 — so it's not a low-settings trick.

## No-trade-off FPS levers (do these regardless of backend)
1. **Lower vanilla render distance to 8–10.** DH's own warning: RD above ~12 eats CPU for almost no
   visual gain; DH renders the distance for you. Single biggest win.
2. **Lower resolution.** MacBook Retina displays run at ~3K native; that's brutal on OpenGL 4.1.
   Windowed or a lower fullscreen res is a huge lever on Macs specifically.
3. **Entity Shadows OFF** (Sodium → Video Settings).
4. **Bump heap + `-XX:+UseZGC`** (Java 25). 4–7 GB is too little for a heavy pack; GC stalls show up
   as random frame drops during chunk loads.
5. **VSync ON** for even frame pacing (uneven 90–140 looks worse than steady 90).

## macOS shader compatibility (Iris = OpenGL 4.1)
- **Safe/established on macOS:** Complementary (Reimagined + Unbound), BSL, Sildur's Vibrant, Bliss.
- **NOT macOS:** SEUS PTGI (needs NVIDIA RTX); be cautious with newer packs targeting GL 4.3+ features.
- General rule: stick to the big, widely-used packs; they target GL 3.x–4.1.

## Distant Horizons shader compatibility (per-pack, opt-in for some)
DH renders far terrain through a *separate* LOD pipeline that shaders don't see by default. Iris added
the plumbing (dh_terrain/dh_water/dh_shadow programs + a `DISTANT_HORIZONS` compile flag), but each
pack's author must write support. Verified list (check each pack's changelog; not permanent):
- **Complementary Reimagined / Unbound** — support it, but it's an **opt-in toggle**: in-game Shader
  Settings → Other → Compatibility → "Distant Horizons Compatibility". Not automatic.
- **BSL** — support added (auto).
- **Bliss** — support added in 2.1.0+ (auto). (Its 2.0.3/2.0.4 files literally say "NOT DISTANT HORIZONS
  COMPATIBLE" in the name.)
- **Sildur's Vibrant**, **Photon** — support added.
- If far LOD terrain looks flat/unlit/seamy, 90% of the time the shader lacks DH support or the
  Complementary toggle is off.

## Sourcing shaderpacks (all of these are Modrinth "shader" projects, no API key needed)
`complementary-unbound`, `complementary-reimagined`, `bsl-shaders`, `bliss-shader`, `photon-shader`.
Modrinth shader version files are `.zip`; download the primary file URL and drop into the instance's
`shaderpacks/` folder (bundling into a `.mrpack` = put them under `overrides/shaderpacks/`).
