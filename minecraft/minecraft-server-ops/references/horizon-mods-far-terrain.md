# Horizon — mods, native server export, and far terrain (LOD / pregen)

Companion to `horizon-rust-server.md`. Covers the two things that come up after a vanilla
Horizon server is running: (a) what mods exist and how to get them onto the **server** (vs
the client), and (b) the built-in "see far" features (`/pregen`, `max_view_distance`,
`horizon-lod-distance`). Facts as of **Nov 2026** — the project is a month old and this
shifts fast, so re-check `playhorizon.dev/docs` before relying on it.

## Mods — two kinds, and "server-side" means something specific

| Kind | File | What it is | Runs where |
|---|---|---|---|
| Content mod | `.hmod` | data/assets: blocks, items, recipes, loot, tags, models, textures, structures. No code. | read at game start (client **and/or** server) |
| Native mod | `.hnmod` | Rust `horizon-mixins` bundle, compiled into a build | built into the **client** by the launcher (per-player) |

Java (Fabric/NeoForge/Forge) jars do **not** run. The registry is the GitHub repo
`horizon-rust/horizon-mods`; each project is a `mods/*.toml` whose `kind` field is `mod`
(content), `native-mod`, `modpack`, `resourcepack`, `shader`, `shaderpack`, or `datapack`.
Catalog: `playhorizon.dev/mods`. As of Nov 2026: 85 native mods, 3 content mods, 1 resource
pack, 5 shader packs, **0 modpacks, 0 datapacks**.

### Client-side (the overwhelming majority — zero server action)

Native mods are installed by **each player** in their own Horizon launcher (Mods page →
Build). Minimap, shaders, zoom, FPS counter, JEI, AppleSkin, Mouse Tricks, freecam,
TreeFall/Veinminer/Chop (they break via the ordinary mining path → send normal break
packets, so they're client-side), and "Distant Horizons for Horizon Client" (client-side
LOD renderer) all fall here. Nothing to do on the server.

### Server-side (change shared state — must run on the dedicated engine)

Content mods that add blocks/items/worldgen drop into the server's `horizon-mods/` folder
(**and** every client's) + restart. Native mods run on the server only via the **native
server export**:

```sh
horizon-launcher native-build FOLDER --server-output DIR --version TAG --trust-native-code
horizon-server --dir SERVER config set engine.path=/abs/export/horizon-engine
horizon-server --dir SERVER restart
```

Build on the same OS/arch as the server (Linux x86-64), needs the Rust toolchain, and
**runs unsandboxed** — "only build code you have read and trust." Updates do not rebuild a
pinned `engine.path`; build a new export and point `engine.path` at it for rollback.

Server-side mods known as of Nov 2026:
- **SMP** (official, `native/smp`) — economy, market, trades, claims. Native *server* mod.
- **Voice Chat server** (`native/voicechat-server`) — proximity-voice relay; pairs with the "Horizon Voice Chat" client mod (Simple Voice Chat compatible).
- **Tectonic-Horizon** — worldgen (mountains, underground rivers, configurable terrain). Worldgen happens server-side, so this runs on the server; clients just receive the terrain. No datapack version exists — Horizon refuses worldgen-only datapacks, so the native port is the only route.
- **Create for Horizon** — rotating machines (gears/belts/presses/fans). 0.7.0-**alpha**.
- **Wayfarer Stones** — waystone teleport blocks (native mod + a separate `.hmod` "assets" pack).
- **Deepbore Quarry** — automated bedrock quarry (native + `.hmod` assets pack).
- **Astral Cruiser** — pilotable starship vehicle.

WorldEdit in the catalog is a *client-side* port only — true server-side WorldEdit isn't
there yet. Baritone is client-side (an automation bot). `native/` also holds Horizon's own
client native-mod sources (coords-hud, fps-overlay, keystrokes, minimap, recipes, zoom).

## Far terrain / LOD / pregen (built-in settings, not mods)

| Setting (server.toml) | Section | What it does |
|---|---|---|
| `max_view_distance` | `[server]` | send already-saved chunks past `view_distance`, up to 32; read-only ring (never generated/ticked). 0 = off. |
| `horizon-lod-distance` | `[properties]` | server samples + serves far-terrain LOD tiles to Horizon clients (Video Settings → LOD Distance), up to 1024 chunks. 0 = off. On-demand per player, no cache; vanilla clients never get it. |
| `horizon-pregen = true` | `[properties]` | unlocks the `/pregen` command (off until set). |

**`/pregen`** is Horizon's Chunky: `horizon-server cmd pregen start 2500` generates the
world around spawn ahead of players.

**The key distinction to tell the user:** you can pre-generate **chunks** server-side
(`/pregen`) — yes — but **LOD tiles** are generated client-side (Distant Horizons for
Horizon Client) or served on-demand (`horizon-lod-distance`); there is no server-side LOD
pre-bake. To get "see far without lag": enable `horizon-pregen`, run `pregen start N`, set
`max_view_distance = 32` and `horizon-lod-distance = 1024`, then the client installs the
Distant Horizons native mod to render it.
