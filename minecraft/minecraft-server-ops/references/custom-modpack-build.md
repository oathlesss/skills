# Building a custom from-scratch modpack (curated, TYPE=NEOFORGE)

Distinct from AUTO_CURSEFORGE (stock pack + manual adds). This is: user gives a mod
wishlist → build a LEAN curated pack (copy a subset of an existing pack's jars + fetch a
few new ones) → boot-iterate missing deps → export self-contained importable packs.

## Workflow

1. **Pin target.** Late-2026 sweet spot is 1.21.1 NeoForge (all big mods have builds;
   newer "26.x" MC still has gaps — AE2, Productive Bees, Dyson Cube, Distant Horizons
   not all ported). Read the EXACT NeoForge version from an existing server's
   `.neoforge-manifest.json` (`forgeVersion`, e.g. `21.1.250`). Memory said 248; the live
   file said 250 — trust the file.
2. **Curate the subset.** List an existing pack's `data/mods/` with Python (NOT
   `ls *.jar | xargs` — apostrophes in filenames). Copy target jars + their libraries.
   Don't try to pre-map every library — the boot log names them (step 4).
3. **Fetch genuinely-new mods.** Modrinth is keyless:
   `/v2/project/<slug>/version?game_versions=["1.21.1"]&loaders=["neoforge"]` → take the
   `primary` file. CF-only mods: query THROUGH the running container's mounted key
   (`docker exec minecraft-atm10aero sh -c 'curl -s -H "x-api-key: $(cat /run/secrets/cf_api_key)" ...'`)
   — never read the key yourself.
4. **Compose + boot + iterate.** itzg env: `TYPE=NEOFORGE`, `VERSION=1.21.1`,
   `NEOFORGE_VERSION=<exact>`, `SERVER_PORT`, `MEMORY`, whitelist. Drop jars in
   `data/mods/`. On boot, `Missing or unsupported mandatory dependencies:` lists EVERY
   missing lib at once; the crash report (`crash-reports/*.txt`) names the failing mod.
   Add the named libs, reboot, repeat until `Done (Ns)!`. Usually 1–3 loops.
5. **Verify.** `docker ps` healthy + `ss -tulnp` shows the ports + no FATAL *since the
   last boot* (`docker logs` is full history — pre-fix FATAL lines are stale, ignore them).

## Dependency gotchas (non-obvious, durable)

| Mod | Needs | Notes |
|---|---|---|
| Create | — | **Radium (Lithium port) declares Create INCOMPATIBLE** → drop Radium when Create is present |
| Biomes O' Plenty | TerraBlender + GlitchCore | |
| Tectonic | Lithostitched | crash = `NoClassDefFoundError: .../lithostitched/...` |
| Ad Astra | common-storage-lib | (NOT Botarium, on 1.16.x) |
| Iron Jetpacks | Cucumber | Cucumber is NOT just Mystical Agriculture's lib |
| Apotheosis + FastFurnace + FastWorkbench | Placebo | all by Shadows_of_Fire — do NOT remove Placebo when dropping Apotheosis |
| Occultism + Ars Ocultas | Modonomicon | remove all three together |
| Create: Aeronautics | Sable (separate mod) | `create-aeronautics-bundled` jar embeds its own deps (Sauce, Sable Companion, etc.) |

## Two UDP mods on one port (voice + Create Aeronautics)

Create: Aeronautics / Sable bind UDP on the MC port. Plasmo Voice `config.toml`
`[host] port = 0` means "same port as MC" → collision → log `[PlasmoVoice] Failed to
start the udp server`. Fix: set Plasmo Voice `port = <dedicated>` (e.g. 25567) and publish
`25567:25567/udp`. A new port mapping needs container RECREATE, not restart. Clients learn
the voice port automatically from the server config packet — no client-side change needed.

## Shaders + Distant Horizons (client) — where they actually live

- **Oculus** (Asek3's Forge port) has NO 1.21.1 files anywhere → use **Iris** instead
  (native NeoForge support since 1.8.x; Modrinth slug `iris`, pick latest non-beta).
- **Distant Horizons**: Modrinth slug is `distanthorizons` (NO hyphen — `distant-horizons`
  404s); CF slug is `distant-horizons` (WITH hyphen); GitLab releases carry only source
  archives, not jars. 3.3.x is the stable line (3.3.3).
- **Embeddium Extras** is CF-only (Modrinth `embeddiumplusplus` 404s).

## Self-contained importable packs (no CF/Modrinth ID resolution)

Build BOTH — same jar set, different wrapper:

- **CurseForge-format `.zip`** → imported by CurseForge app + Prism Launcher.
  Root: `manifest.json` (`minecraft.version` + `minecraft.modLoaders:[{id:"neoforge-21.1.250",primary:true}]`,
  `manifestType:"minecraftModpack"`, `manifestVersion:1`, `files:[]`, `overrides:"overrides"`)
  + `modlist.html`. Everything under `overrides/` (mods/, config/, ...).
- **Modrinth `.mrpack`** → imported by Modrinth app + Prism Launcher.
  Root: `modrinth.index.json` (`formatVersion:1`, `game:"minecraft"`, `files:[]`,
  `dependencies:{minecraft,neoforge}`). Everything under `overrides/`.

Key: `files: []` + all jars in `overrides/mods/` = fully self-contained, NO per-mod
projectID/fileID lookup. The CurseForge app shows "0 mods to download" but extracts
`overrides/` anyway; Prism handles it silently. Sizes ≈ 360 MB for ~170 mods (jars are
already compressed — zipping saves ~nothing). Use Python `zipfile` (the `zip` binary is
absent on this box).

## Ruben's preference (first-class)

He wants a **wishlist-driven, lean pack** — build EXACTLY what he lists plus explicitly
requested additions. "Other mods you might suggest" is an invitation to PROPOSE, not to
silently include. Present extras as a grouped veto-list BEFORE adding them. He pushed back
on a padded pack ("you added a lot of mods without my input") — don't repeat it. Also:
commit+push infra changes immediately (his standing rule).
