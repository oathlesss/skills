# Performance mod gaps — what's worth adding vs already covered

For ATM10 Aeronautics (and similar 400-mod NeoForge 1.21.1 packs) on a modest CPU-bound
box (i5-9500T). Verified against the live server 2026-09-29.

## Already present (don't re-add — the ATM team ships these)

- Memory/RAM: FerriteCore, ModernFix, AllTheLeaks, FlickerFix, MemorySettings
- Recipe caching: FastFurnace, FastWorkbench, FastSuite
- Mob/tick AI: AI-Improvements, Clumps
- Chunk/worldgen: C2ME, Chunky, imFast
- Connection/login: Connectivity
- Profilers: Spark, Observable
- Misc: AttributeFix, Cupboard, InvasiveOpts, NetherPortalFix

That's ~18 perf mods — the *baseline* is solid. "Feels like perf mods are missing" is usually
the client-side rendering gap, not server-side.

## High-value server-side additions (NeoForge 1.21.1 builds exist)

- **Lithium** — the biggest single tick-loop optimization. Meaningfully cuts "Can't keep up" lag.
- **ServerCore** — bundled server optimizations (entity ticking, hoppers, etc.).
- **Noisium** — worldgen speedup (complements C2ME for exploration lag).

Verify version availability via Modrinth API before adding:
`curl -s "https://api.modrinth.com/v2/project/<slug>/version?game_versions=%5B%221.21.1%22%5D&loaders=%5B%22neoforge%22%5D"`

⚠️ Lithium can clash with C2ME — add one at a time and check the boot log for conflicts
before committing; don't blind-add all three.

NOT worth it: Krypton (Fabric-only), ScalableLux (alpha), Debugify (Fabric-only).

## Client-side rendering mods — DELIBERATELY absent from ATM packs

The biggest visual/FPS wins are client-side and shader-sensitive, so pack authors leave them
to the player:

- Sodium / Embeddium — large FPS boost
- Iris / Oculus — shaders
- EntityCulling, ImmediatelyFast, Dynamic FPS

These go in each player's client, NOT the server/pack. They conflict with a Distant Horizons +
Oculus shader setup (need matching versions). Don't add them to the shared pack — tell players
to install them client-side if they want them.
