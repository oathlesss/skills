# macOS / Apple Silicon client rendering + shaders (Minecraft 26.1.2)

Ruben plays on an Apple Silicon Mac (M2 Pro, macOS 27, Java 25). This is a distinct
performance situation from Windows/Linux and drives FPS + shader choices.

## Root cause of low FPS on Apple Silicon

Sodium on macOS renders through Apple's **deprecated OpenGL-on-Metal layer (OpenGL 4.1)**.
That is a hard ceiling: expect ~90–150 fps on an M-series chip regardless of pack size,
vs 200–300+ on equivalent Windows/Linux hardware. It is NOT a "heavy pack" problem —
the M2 Pro is capable of far more.

## MetalForge — native Metal backend (the big lever)

[LeadFreeCandy/metalforge](https://github.com/LeadFreeCandy/metalforge) — a drop-in native
Apple Metal renderer for NeoForge **26.1.2** (client-only, arm64, macOS 14+, Java 25). Roughly
**2× FPS**: benchmark on a fanless M2 Air (FTB Evolution 2, 420 mods) went 124–151 → 287–294 fps
standing. Tell-tale it's active: F3 shows `Metal 3 (MetalForge/mcopt)`.

**Mutually exclusive — pick one:**

| Combination | Result |
|---|---|
| MetalForge + Sodium | ✅ 2× FPS on Metal |
| MetalForge + **Iris** | ⚠️ falls back to OpenGL (no boost) — shaders need OpenGL |
| MetalForge + **Distant Horizons** | ❌ DH calls OpenGL directly → LODs draw nothing |

So: **max FPS (MetalForge) = no shaders + no DH**. **Shaders + DH = stay on OpenGL/Iris.**

## OpenGL-path levers (keep Iris + DH, still raise FPS)

- Lower vanilla render distance to **8–10** — DH's own warning: RD > 12 eats CPU for little
  visual gain; DH carries the far view via LODs.
- Lower **Retina resolution** (native ~3K is brutal on Apple's GL 4.1) — run a window / lower res.
- Entity shadows off (Sodium → Video Settings).
- **`-XX:+UseZGC`** on Java 21+/25 — fixes DH's "G1 Garbage collector detected" stutter warning.
  (Do NOT add `-XX:+ZGenerational` — it's obsolete on Java 25 and just prints a warning.)
- Bump heap: `-Xmx8G`–`-Xmx10G` for a 180-mod pack (7G caused GC stalls during chunk loads).

## Distant Horizons × shader compatibility (per-pack, NOT automatic)

DH renders far terrain through its own LOD pipeline; a shaderpack must ship `dh_terrain` /
`dh_water` / `dh_shadow` programs to light it. Iris added the plumbing (~1.7.0+); each pack
opts in separately:

- **Complementary Reimagined / Unbound** — DH support, but **OPT-IN**: enable in shader settings
  → Other → Compatibility → "Distant Horizons Compatibility" (off by default — the #1 "why is
  my far terrain flat" cause).
- **BSL, Photon, Sildur's Vibrant, Bliss** — DH support built-in/automatic.
- **macOS-safe (GL 4.1)** shaders: Complementary, BSL, Sildur's, Bliss. **Avoid SEUS PTGI**
  (needs NVIDIA/RTX) and packs targeting GL 4.3+.

Shaderpacks are **version-agnostic** (GLSL; load via Iris across MC versions). Modrinth
`project_type=shader` slugs: `complementary-reimagined`, `complementary-unbound`, `bsl-shaders`,
`bliss-shader`, `photon-shader`. Download a version's `files[0].url` (keyless).

## Bundling shaderpacks into a client pack

- `.mrpack`: put the `.zip` shaderpacks in `overrides/shaderpacks/` (lands in the instance's
  `shaderpacks/` folder on import).
- Fast drop-in for an already-installed client: a standalone zip of `shaderpacks/*.zip` (~4 MB)
  the user extracts into their instance folder — avoids re-pulling the whole 300 MB pack.
- Both served via `~/homeserver/www/` → `https://oathless.dev/files/<name>`.

## Client QoL mods on NeoForge 26.1.2.109 (loader gotchas)

- **Zoom:** Zoomify 2.17.0 uses a non-standard `modLoader = 'klf'` (Kotlin Language Features) —
  risky on a pinned 26.1.2.109. **Ok Zoomer** uses standard `javafml` + `neoforge [26.1.0-alpha,)`
  (safe; default key `C`). Xaero Zoomout is a Xaero-map *companion*, not a standalone zoom.
- **Keybind search:** Controlling (`neoforge [26.1.2.7-beta,)`) has a hard dep on the
  `searchables` library — must ship both.
- **Always verify the declared NeoForge MINIMUM, not just the MC version** — Just Zoom required
  ≥26.1.2.114 while the pack pins .109, so it was rejected. Read the jar's
  `META-INF/neoforge.mods.toml` `[[dependencies]]` `versionRange` before adding.
