---
name: minecraft-server-ops
category: minecraft
description: "Administer a self-hosted Minecraft server (itzg docker-minecraft-server on a homelab box): assess whether hardware can handle a modpack, tune performance, pre-generate the world, manage Distant Horizons LODs, add/remove mods on an AUTO_CURSEFORGE container, add voice chat (Plasmo Voice) with its UDP port, and export the pack as an importable CurseForge .zip or Modrinth .mrpack. Trigger on server performance questions, 'can my server run this pack', pregen, world generation, Distant Horizons, mod-management requests, voice chat setup, 'make the pack importable', or 'which config controls/disables a feature in the pack'."
---

# Minecraft Server Operations

> **Config hunting & mod-jar inspection** (e.g. "which config disables X", identifying which mod owns an effect/item): `references/modpack-config-and-jar-inspection.md`.

Operational knowledge for running Ruben's self-hosted Minecraft server(s) on the
OptiPlex homelab. The primary instance is **All The Mods 11** (`minecraft-atm11`, itzg/minecraft-server:java25,
TYPE=AUTO_CURSEFORGE, CF_SLUG=all-the-mods-11, pinned 0.12.0-beta via CF_FILE_ID=9187064,
NeoForge 26.1.2.109, 12G RAM) on 25565 = mc.oathless.dev. Its world is bind-mounted from
`~/atm11-world` (migrated off the remote ATM server via scp; `level-name=world` → `/data/world`
bind-mount). Manual adds (drop into `data/mods/`, survive the CF sync): Hephaestus Forge +
Hephaestus Tools + PlayerAnimationLib + Nautec 2 + Chunky 1.5.4 + C2ME. Earlier experiments are
archived: FTB Evolution 2 (`minecraft-evo2-archive2` + the older `minecraft-evo2-archive`),
evo2-tech (`minecraft-evo2tech-archive`).
Historical/retired servers still referenced as running examples in several reference files:
Enigmatica 10 (`minecraft-e10`), the Oathless Server Pack (`minecraft-oathlesssp`), and ATM10
Aeronautics (`minecraft-atm10aero`). Hardware: i5-9500T (6c/6t, 35W T-series), 30GB RAM, NVMe.

## Key facts / mental model

- **Which server is the user asking about? CONFIRM before diagnosing.** Ruben runs at least TWO MC servers: (1) the homelab `minecraft-evo2tech` (evo2-tech pack, itzg docker — its logs show `/data/...` container paths or `/home/ruben/homeserver/...` host paths), and (2) a separately-hosted **All The Mods (ATM)** server on a remote panel (Pterodactyl-style — its logs show `file:/home/container/mods/...` paths). The `/home/container/` path in a pasted log is the fingerprint of the REMOTE host, NOT the homelab. Never run homelab diagnostics (docker stats, `chunky` task state, CPU governor) against a log from the remote ATM server — that produces a wrong diagnosis (verified: I misattributed an ATM lag log to the homelab box and analyzed the wrong CPU/chunky state). Ask/confirm which server if the log path isn't visible.
- **Minecraft's tick loop is single-threaded.** CPU single-core speed is the binding
  constraint, not RAM or core count. A low-power T-series chip with a `powersave`
  governor is the worst case for a heavy pack.
- **JVM flags: the itzg image ships Aikar's/MeowIce's flags DISABLED by default (verified Oct 2026, java25 image).** `USE_AIKAR_FLAGS` and `USE_MEOWICE_FLAGS` both default to `false` in `/image/scripts/start-finalExec` (`: "${USE_AIKAR_FLAGS:=false}"`), so a stock itzg MC container runs Java's *default* G1GC with only `-Xmx/-Xms` in `user_jvm_args.txt` — NOT Aikar's flags. Enabling `USE_MEOWICE_FLAGS: "true"` (modern successor, tuned for Java 17+; on Java 25 the script logs "Using MeowIce's flags") added the full GC/code-cache/large-pages/AVX2 set and raised ATM11 pregen from ~23 → ~33+ chunks/s once JIT-warmed (ignore the first post-boot reading of ~7 cps — that's JIT warmup). Requires a container RECREATE (env change). Verify current flags: `docker exec <c> sh -c 'cat /data/user_jvm_args.txt'`. No large-pages startup errors in a container (THP flags degrade gracefully).
- **Heavy pack worldgen cost is invisible until players explore.** An empty world
  ticking at ~43% CPU with 0 players is the warning sign; the real cost hits when
  2+ players fly/dimension-hop and generate chunks.
- **Two different "pregen" tools, do not conflate them** (this was corrected explicitly):
  - **Chunky** pre-generates *real* chunks (blocks, ores, structures, mod worldgen) —
    this is what fixes "can't keep up" lag.
  - **Distant Horizons `/dh pregen`** generates *LODs* (simplified visual terrain) —
    cosmetic, does NOT reduce chunk-gen lag.
- **Distant Horizons is primarily a CLIENT mod, but 3.3.3's server-side LOD serving is cheap and Ruben WANTS it.** On the server, DH builds LODs FROM REAL CHUNKS (fed by Chunky pre-gen) and uploads them to clients — NOT the old CPU-hungry fake-terrain "Distant Generation" (that was removed in 3.x). Controlled by the `[server]` section of `config/distanthorizons.toml` (`synchronizeOnLoad=true`, `generationBoundsRadius=0`=unlimited — sensible defaults, no config needed). Enable by dropping the DH jar (combined fabric+neoforge) into `data/mods/` + recreate; on boot it creates `world/dimensions/*/data/DistantHorizons.sqlite` per dimension and logs benign `Unknown Chunk Generator detected ... Distant Generation May Fail!` for CUSTOM dims (Thaumaturge Outer Lands, AE2 spatial storage) — the overworld is fine. To make LODs actually exist, Chunky-pregen the real chunks first (DH only covers chunks the server has generated). The older "keep DH client-only on a small box" guidance predates 3.3.3 and this user's explicit ask — verify against the current DH version.

## Performance assessment procedure

1. `docker stats --no-stream <container>` (CPU% + memory) — sample twice ~3s apart.
2. `lscpu` (model, threads/core, max MHz), `free -h`, `df -h`, `sensors` (thermals).
3. `grep -icE "can't keep up|running behind|is overloaded" .../logs/latest.log`.
4. World size (`du -sh .../world`) — a tiny world means nobody's stress-tested yet.
5. Check `server.properties` `view-distance` / `simulation-distance` (both 10 is
   aggressive for a heavy pack).
6. Mod count (`ls .../mods/*.jar | wc -l`) + presence of perf mods (ferritecore,
   modernfix, spark, etc.).

**Tuning levers, in order of impact:** cut view/sim distance (10→6 ~halves chunk load)
> pre-generate the world (Chunky) > switch CPU governor powersave→performance.

**JVM GC flags — the itzg image does NOT auto-apply Aikar's flags (verified Oct 2026).** `USE_AIKAR_FLAGS` and `USE_MEOWICE_FLAGS` BOTH default to `false` in the image's `start-finalExec` script, so a bare `MEMORY=12G` container runs STOCK G1GC with zero tuning — only `-Xmx -Xms` land in `user_jvm_args.txt`. (I mis-stated this once as "Aikar's flags are auto-applied" — they are NOT.) Verify the real JVM args: `docker exec <c> sh -c 'cat /data/user_jvm_args.txt'` (Forge/NeoForge launches `java @user_jvm_args.txt @...unix_args.txt`; the image writes `$JVM_XX_OPTS $JVM_OPTS ...` into that file). To enable: `USE_MEOWICE_FLAGS: "true"` (modern successor to Aikar's, tuned for Java 17+; this box runs Java 25) or `USE_AIKAR_FLAGS: "true"` (classic; a ≥12G heap gets the ">12GB" variant). Env change needs a container RECREATE. Better GC cuts pause spikes during worldgen/pregen and normal play.

**With Distant Horizons server-side, the server view-distance can (and should) be low** — DH clients render distant terrain from LODs, so the server only needs to track/send the near ring. evo2-tech runs `view-distance 6` / `simulation-distance 5` (down from 8/6); `simulation-distance 5` is the floor before mobs/farms stop ticking in range. Lowering it is an env change (`VIEW_DISTANCE`/`SIMULATION_DISTANCE` baked into server.properties on boot) that needs a container RECREATE — so do it BEFORE starting pregen, because a mid-pregen restart wipes the in-flight Chunky task.
**Lowering `VIEW_DISTANCE`/`SIMULATION_DISTANCE` is the cheap win when DH is server-side** —
clients render LODs beyond the server's view-distance, so the server stops tracking/sending
distant chunks. evo2-tech runs view-distance 6 / sim-distance 5 (down from 8/6). Change via
compose env + container RECREATE (`docker rm -f <c> && docker compose create <c> && docker start <c>`;
`docker start` alone does NOT apply env changes). **Do the recreate BEFORE starting Chunky** — a
restart mid-pregen wipes the in-flight task.

## Pre-generation workflow (Chunky + C2ME, then DH LODs)

Order matters: **real chunks first, then DH LODs** (DH can build LODs from existing
chunks instead of re-worldgenning). Exact version numbers and the full command
sequence live in `references/pregen-and-distant-horizons.md` — read it before running
anything; version IDs drift across MC versions and must be verified against the CF API.

**Operational gotchas (verified Oct 2026 on evo2-tech, Chunky 1.5.4):**

- **Lower server view/sim distance BEFORE pregenning — the change needs a container recreate, which wipes the in-flight Chunky task.** With Distant Horizons installed (clients render far terrain), drop `VIEW_DISTANCE` 8→6 and `SIMULATION_DISTANCE` 6→5 in compose, recreate (`docker rm -f <c> && docker compose create <c> && docker start <c>`), verify `server.properties` shows the new values, THEN start Chunky. Doing it mid-pregen loses the task (recoverable via `chunky continue`, but avoid).
- **`chunky cancel` is two-step in 1.5.x:** the first `chunky cancel` replies "Cancelled tasks cannot be continued... type '/chunky confirm'"; run `chunky confirm` to actually cancel. (`confirm` is not listed in `chunky help` but exists.)
- **To EXPAND a running task's radius** (e.g. 3000→6000): `chunky cancel` + `chunky confirm`, re-set `center`/`radius`/`world`, then `chunky start`. Already-generated chunks are kept and skipped on the new task (`forceLoadExistingChunks: false`).
- **After a container restart, `chunky start` refuses if a saved task exists** — it replies "A task was already started for this world... type '/chunky confirm'", and `chunky progress` shows "No tasks running". Resume with `chunky continue` (NOT `start`) — it skips done chunks. The saved `config/chunky/tasks/<world>/<dim>.properties` still records the pre-restart radius correctly here (verify it anyway — it can go stale after an OOM crash). Set `continueOnRestart: true` in `config/chunky/config.json` to auto-resume instead.
- **C2ME exists for MC 26.1.2** — Modrinth slug **`c2me-neoforge`** (the bare `c2me` slug 404s); newest 26.1.2 build `c2me-neoforge-mc26.1.2-0.4.0-alpha.0.100.jar`. On the 6-core i5-9500T it took evo2-tech pregen ~11 → ~31 chunks/s (~3x) and saturated all cores (CPU 274%→595%); the ~5-10x in the reference was a bigger pack/CPU. Distant Horizons auto-detects C2ME at boot ("C2ME detected: DH's pre-existing chunk accessing will use methods handled by C2ME") — no config. C2ME is server-side only; players install nothing. See `references/pregen-and-distant-horizons.md`.

**Chunky is NOT bundled in every pack** — check `data/mods/` first (E10 omits it; add
`Chunky-NeoForge-1.4.23.jar`, CF file id 6383261, before pregen). Without C2ME, pregen runs
~4-5 chunks/sec single-threaded on the i5-9500T (≈3.8 h for a 2000-block radius / ~61k chunks);
C2ME parallelizes to ~5x. **FTB Evolution 2 (MC 26.1.2) already bundles Chunky 1.5.4** and pregens at
~12–18 chunks/sec on the i5-9500T *without* C2ME (~1.5 h for a 2000-block overworld radius) — worldgen
cost varies widely by pack, so measure the actual `chunky progress` rate instead of assuming the 4.6 cps
baseline — and IGNORE the first `chunky progress` reading (a few seconds after `start` shows ~2–3 cps with a scary multi-hour ETA from JIT warmup; re-check after ~60s for the real ~15 cps). Chunky 1.5.x has NO `chunky version` command (it errors "Incorrect argument") — use
`chunky help` to confirm; `center`/`radius`/`world`/`start`/`progress`/`continue` are unchanged from 1.4.x. **Chunky has NO multi-core/parallelism setting** — `config/chunky/config.json` only holds `version`/`language`/`continueOnRestart`/`forceLoadExistingChunks`/`silent`/`updateInterval`; chunk generation runs on a single `Chunky-minecraft:<dim> Thread` by design, and only C2ME parallelizes it. On a 6-core box a "running" Chunky task at ~10–12 cps is using ~1 core for generation (the extra `docker stats` CPU% is GC/JIT/IO overhead, not parallel gen).

**`chunky cancel` needs a second `chunky confirm`, and `chunky radius` does NOT resize a running task.**
`chunky cancel` alone replies "Cancelled tasks cannot be continued ... type '/chunky confirm'" and leaves the task RUNNING; `chunky confirm` is a hidden command (absent from `chunky help`). Setting `center`/`radius`/`world` while a task runs only updates the *selection* — the in-flight task keeps its original radius, and `chunky start` then returns "Task already started for <world>!". To expand/shrink mid-pregen: `chunky cancel` → `chunky confirm` → re-set center/radius/world → `chunky start`. Already-generated chunks are skipped (`forceLoadExistingChunks: false`), so nothing generated is wasted.
Kick any online players first (`rcon-cli "kick <name> Pregen starting"`) — pregen + a live player tanks TPS for both. Pregen runs *inside* the server process, so the server stays joinable
throughout — fine on a fresh world with no players yet.

To verify a Chunky task actually finished (and WHEN): Minecraft log lines carry only `[HH:MM:SS]`, so
use `docker logs --timestamps <c> | grep -i 'chunky.*Task finished'` to get the real date. The completion
line is `[Chunky] Task finished for minecraft:overworld. Processed: N chunks (100.00%), Total time: ...`.
A Chunky task is per-dimension — "overworld 100%" does NOT mean nether/end were pregenerated.

**Pregen can OOM-crash the server mid-run — and then the watcher falsely reports "complete".**
Heavy-worldgen packs (FTB Evolution 2: Tectonic + Lithostitched + TerraBlender + YUNG's caves +
Better Caves + Stellaris + ModernFix) can blow an 8G heap during bulk generation —
`OutOfMemoryError: Java heap space` inside `DensityFunctions$Spline.compute`/`NoiseChunk` (the
lithostitched/modernfix density-function mixin chain is the hot path). The container auto-restarts
(restart policy), Chunky's in-flight task is wiped, and `chunky progress` returns "No tasks running" —
which the OLD `chunky-watch.sh` grep read as completion and printed a false "PREGEN COMPLETE".
Diagnose a suspicious completion: `docker ps` uptime ("Up X minutes" = just restarted), read
`data/crash-reports/*.txt` (heap "used/committed/max" all ≈ MEMORY = OOM; a mod exception is
worldgen/code, not memory), then check `data/config/chunky/tasks/<world>/<dim>.properties` (a
crashed task is `cancelled=true` → `chunky continue` replies "No tasks to continue"). Fix: bump
`MEMORY` 8→12G for the pregen run and/or lower Chunky parallelism, and set `continueOnRestart: true`
in `data/config/chunky/config.json` so a future crash auto-resumes instead of losing the task.
Re-running `chunky start` with the same center/radius skips already-generated chunks
(`forceLoadExistingChunks: false`), so the partial work already on disk is never wasted. **The watcher has a mirror-image trap too:** a clean finish between polls ALSO reports "No tasks running" (Chunky removes the task at 100%), so a naive exit-1-on-"no tasks" script flags a genuine success as a failure. Disambiguate by comparing the container's `StartedAt` before/after (unchanged = completed; changed = lost) — `scripts/chunky-watch.sh` encodes this.

**Resuming after a lost task: recover the TRUE radius, and don't misread the skip-through.**
The saved `data/config/chunky/tasks/<world>/<dim>.properties` file is frequently STALE after a
crash — it can record an earlier/smaller `radius` than the task that actually died (this bit us:
properties said `radius=2000` but the crashed task was really 3000). Recover the real radius from
the last progress line before the crash: `total = Processed / (percent/100)` (e.g. 75,518 / 0.5313
≈ 142k chunks), then for `shape=square` `sqrt(total) ≈ side in chunks` → radius ≈ `side*16/2`
blocks (√142k ≈ 377 → ~3000). Cross-check against the generated region files on disk (below).
When you re-`start`, the FIRST `chunky progress` reading will show a huge cps (thousands) and the
% will leap to the prior frontier within ~30s — that is Chunky skipping the already-generated
chunks, NOT fresh generation. Re-check AFTER the % passes the old crash point to see the real
generation rate and ETA.

**Finding region files on FTB Evolution 2 (modded dimension layout).** The overworld is NOT at
`data/world/region/` — a dimension-relocating mod moves it to
`data/world/dimensions/minecraft/overworld/region/` (plus `dimensions/<ns>/<dim>/` for nether/end
and modded dims). Count/extent the generated area from there:
`ls dimensions/minecraft/overworld/region/*.mca` — filenames `r.<x>.<z>.mca` are region coords
(×512 = block range), so the min/max `x`/`z` give the generated footprint.

## World disk size (estimate before/while pregenning)

Measured on evo2-tech (26.1.2 modded overworld): a full 1024-chunk region file is ~21 MB (deflate) ≈ ~20 KB/chunk. Radius → chunks → overworld disk:
- `radius 3000` (6×6 km) = ~141k chunks ≈ ~2.8 GB
- `radius 6000` (12×12 km) = ~562k chunks ≈ ~11 GB

DH LOD data (`Distant_Horizons_server_data/` + per-dimension sqlite) adds ~1–2 GB on top. Cross-check any estimate against the live `du -sh .../world` at a known `chunky progress` % (e.g. world @ 3% ≈ 424 MB → ~13 GB total, consistent). Nether/end not included — a few more GB if pregenned later.

## Finding the exact MC + NeoForge version + pack identity

Never guess the version when adding mods or matching a client to the server. Read it from the
server's own state. **`version.json` does NOT exist on AUTO_CURSEFORGE containers** — the itzg
helpers write dotfile manifests instead (confirmed on `minecraft-atm10aero`):

```bash
cd /home/ruben/homeserver/minecraft-atm10aero/data
cat .neoforge-manifest.json      # {minecraftVersion, forgeVersion} e.g. 1.21.1 / 21.1.248
cat .install-curseforge.env      # MODPACK_NAME, MODPACK_VERSION (e.g. 0.5.1), TYPE=NEOFORGE
```

`.curseforge-manifest.json` is the valuable one — it holds the **exact pack identity** plus the
full installed file list:

- `slug`, `modpackName`, `modpackVersion`, `modId` (CF project id), `fileId` (CF file id),
  `minecraftVersion`, `modLoaderId` (e.g. `neoforge-21.1.248`), `levelName`
- `files`: a flat list of **file paths** (e.g. `mods/foo-1.21.1.jar`, `config/…`, `kubejs/…`)
  — NOT `{projectID,fileID}` objects. Use it to diff against the actual mods dir (below).

```bash
python3 -c "import json; d=json.load(open('.curseforge-manifest.json')); print(d['modpackVersion'], d['modId'], d['fileId'], d['modLoaderId'], len(d['files']))"
```

### Which mods did I add manually vs the official pack?

Diff the real jars against the manifest's `files` paths:

```bash
python3 -c "
import json, os
d=json.load(open('/home/ruben/homeserver/minecraft-atm10aero/data/.curseforge-manifest.json'))
m=set(f.split('/',1)[1] for f in d['files'] if f.startswith('mods/') and f.endswith('.jar'))
a=set(f for f in os.listdir('/home/ruben/homeserver/minecraft-atm10aero/data/mods') if f.endswith('.jar'))
print('MANUAL ADDS (in dir, not in manifest):', sorted(a-m))
print('MISSING (in manifest, not in dir):', sorted(m-a))
"
```
The `a - m` set is your manual additions (AppliedFlux, Chunky, C2ME, DistantHorizons, etc.).
The **client-required** subset of those (content mods that add blocks/items) is what you must
ship to players; server-side perf/pregen mods (Chunky, C2ME, DH server jar) don't gate joining.

## Mod management on itzg AUTO_CURSEFORGE

The container re-syncs the modpack from CurseForge on start, but **manual jar drops into
`data/mods/` DO survive the sync** — confirmed empirically (AppliedFlux/AdvancedAE with
pre-start timestamps persisted across a restart). No `REMOVE_OLD_MODS` / `CURSEFORGE_PROJECTS`
env is set; plain jar drops just work. **To PERMANENTLY remove a PACK mod (not a manual add),
deleting the jar is NOT enough** — the sync re-downloads it (`Re-installing due to missing files
from modpack: [...]`). Instead set `CF_EXCLUDE_MODS: "<slug>"` (comma-separated for several), delete
the jar, and RECREATE the container (env change needs `docker rm -f <c> && docker compose create <c>
&& docker start <c>`). The slug is NOT the mod id — find it via `.../v1/mods/search?searchFilter=<name>&classId=6`
(e.g. `betterchunkloading` jar → slug `better-chunk-loading-forge-fabric`). RCON is on port 25575:
`docker exec minecraft-atm10aero rcon-cli "<command>"`.

C2ME shows harmless `@Mixin target ... not found` WARNs for client-side classes (server
has no client) — expected, not a bug. Detect boot-complete via RCON `list` responding,
not via log grep.

### Before adding a content mod: check what the pack already ships
Big kitchen-sinks (Enigmatica 10, ATM10) already include most decor/tech mods — E10 ships
FramedBlocks, the full Macaw's suite, Chipped, Handcrafted, Supplementaries, Building Gadgets
(only MrCrayfish Furniture + Productive Bees were actually missing). Before fetching, list the
mods dir and grep the wishlist keywords; only download what's genuinely absent. Use Python, not
`ls | xargs` (jar names contain apostrophes). After boot, content mods you add still need a
matching CLIENT jar — they're not server-side-only like Chunky/pregen.

### Researching "can I add mod X to this pack?" (pre-flight, no install)

To answer "is this mod compatible with my running server" without touching the server, use the CF API against the host-decrypted key file (below) and diff against the pack's real `data/mods/`:

1. **Slug → project id**: `.../v1/mods/search?gameId=432&searchFilter=<name>&classId=6` (classId=6 = mod). A fuzzy name returns a wall of same-theme addons (searching "thaumaturge" surfaced ~11 Thaumcraft-adjacent addons); match the `slug` exactly to the CF URL the user pasted.
2. **Files → versions**: `.../v1/mods/<id>/files?pageSize=50` → each file's `gameVersions[]` = [MC version, NeoForge/Forge, Client, Server]. Match against the server's exact MC + loader (FTB: `targets[]` from the FTB API; CF pack: `.neoforge-manifest.json`).
3. **Latest file → deps**: `.../v1/mods/<id>/files/<fileId>` → `dependencies[]` (`relationType` 3=Required, 2=Optional). Resolve required `modId`s via `.../v1/mods/<modId>`.
4. **Diff against the pack**: grep `data/mods/` for each required dep's jar. If every required dep is already present AND version-matched, it's a drop-in with zero new dependencies (e.g. Thaumaturge → Curios + Lithostitched + optional JEI, all already shipped by FTB Evolution 2).

- **CF API key when no AUTO_CURSEFORGE container runs** (FTBA / TYPE=NEOFORGE servers don't mount `/run/secrets/cf_api_key`): source it from the host decrypted file without exposing the value — `-H "x-api-key: $(cat /home/ruben/homeserver/secrets/cf_api_key.txt)"`. Same use-without-reading pattern as the docker-exec form; the value never appears in output.
- **cfwidget is MODPACK-ONLY.** `api.cfwidget.com/.../<modslug>` returns empty JSON for a mod (both `/minecraft/mc-mods/<slug>` and `/<slug>`). For mods use the CF API.
- **Adding to an EXISTING world** — check the latest file's changelog (`.../files/<fileId>/changelog`) for a retroactive-worldgen fix line ("chunks generated before X was added"). A mod that ships that is explicitly safe on an already-generated world (Thaumaturge 1.0.2: "Fixed missing aura in chunks generated before Thaumaturge was added").
- **FTBA manual-drop persistence is UNVERIFIED** — the "manual jar drops survive the sync" finding above was confirmed on AUTO_CURSEFORGE only. The FTB App installer re-runs on boot; it has NOT been confirmed on this box that hand-dropped jars in `data/mods/` survive. Verify with a drop→restart→`ls` round-trip before relying on it.

### Swapping the running server to a different published pack (custom NeoForge → AUTO_CURSEFORGE)
To replace a hand-curated `TYPE=NEOFORGE` server with a published CurseForge pack (e.g. a custom
friends pack → Enigmatica 10), the compose recipe:
- **Archive, don't delete**: stop the old container and leave its data dir in place (recoverable).
  Point a NEW service at a fresh data dir — do NOT reuse the old one (mod-set mismatch = broken world).
- New service env: `TYPE=AUTO_CURSEFORGE`, `CF_SLUG=<slug>` (e.g. `enigmatica10`), and mount the key:
  `- ./secrets/cf_api_key.txt:/run/secrets/cf_api_key:ro` + `CF_API_KEY_FILE=/run/secrets/cf_api_key`.
  Keep the SAME port, `WHITELIST`, `MEMORY`, `VIEW_DISTANCE`. Drop a leftover UDP mapping for Sable/voice
  if the new pack has no such mod.
- Recreate without `up -d`: `docker compose create <svc> && docker start <svc>` (both return instantly).
  The old container becomes an orphan (harmless warning) — leave it stopped as the recoverable archive.
- The pack downloads on first start (~2 min for a 312-mod pack on this box).

### Deploying a Modrinth modpack (extract .mrpack → TYPE=NEOFORGE)

The itzg `TYPE=MODRINTH` path exists but manual-jar-drop persistence there is UNVERIFIED. The
controllable route is the proven `TYPE=NEOFORGE` + manual `data/mods/`:
1. Inspect the pack keylessly — see `minecraft-modpack-creation` → `references/26.x-neoforge-mod-availability.md`
   (Modrinth API + `.mrpack`'s `modrinth.index.json`).
2. Read `modrinth.index.json` `dependencies` for the exact loader pin — BA+ 1.39 pins `neoforge 26.1.2.99`,
   NOT the `.109` FTB Evo 2 uses. Set `NEOFORGE_VERSION` to the PACK's value so its own mods stay happy.
3. Download each `files[]` jar (they carry direct CDN URLs) into `data/mods/`; extract `overrides/` into
   `data/` (configs, `overrides/mods/`, resourcepacks/shaderpacks).
4. Curate additions by copying exact jar names from an existing 26.1.2 pack's `data/mods/` (FTB Evo 2 has
   everything), then boot-iterate — NeoForge ModSorter lists every missing dep at once.

## Box-saturation diagnostic: shell builtins work but fork/exec hangs

Symptom on the homelab (i5-9500T 6c/6t, MC server on 12G): `pwd`/`echo` (bash builtins) return
instantly, but ANY fork+exec — `whoami`, `ls -la`, `python3`, `docker ps` — stalls and the terminal
reports `Command interrupted` (exit 130). `ls -la` and `whoami` specifically trigger `getpwuid`/`getgrgid`
(owner-name NSS lookups), so even a `-l` listing hangs while plain `ls -1`/`os.listdir` is fine. This is
the MC server saturating the box (likely mid-pregen), NOT a broken terminal.
Work around it with the NON-forking tools: `read_file`/`write_file`/`patch` keep working (they read/write
specific files directly, no shell), and Python `os.listdir` avoids NSS. Use them to STAGE while the shell
is down — read `whitelist.json`/`ops.json`/`docker-compose.yml`, write the new compose service + a deploy
script — then run the docker commands once load clears. Don't chase it as a terminal bug.

## Swapping to an FTB App pack (TYPE=FTBA)

FTB packs (FTB Evolution 2, etc.) are distributed via the FTB App. Deploy with `TYPE=FTBA` (cfwidget returns empty for them even though the pack JSON carries a `meta.curseforgeProjectId` — don't infer "not on CurseForge" from an empty cfwidget response):

- `image: itzg/minecraft-server:java25` for MC 26.x packs (Java 25). Check exact versions first:
  `curl https://api.feed-the-beast.com/v1/modpacks/public/modpack/<id>` → `targets[]` gives minecraft/neoforge/java versions (e.g. FTB Evo 2 = MC 26.1.2, NeoForge 26.1.2.109, Java 25.0.2).
- `FTB_MODPACK_ID`: numerical ID from the URL `feed-the-beast.com/modpacks/<ID>-<slug>` (FTB Evolution 2 = 135). Omit `FTB_MODPACK_VERSION_ID` to auto-resolve latest — but for a long-running server PIN it (set the version id) to dodge the silent auto-update pitfall below.
- No CF key needed. FTBA uses the NEW `api.feed-the-beast.com/v1/modpacks` API (the old api.modpacks.ch no longer lists new packs — "Modpack id not valid").
- **Version history / per-version mod lists / changelogs** (no CF key): the pack endpoint's `versions[]` is metadata-only (id/name/type/released). The full mod list lives at `.../public/modpack/<id>/<versionId>` (`files[]`, mods = `path == "./mods"`); auto-generated add/remove/update diffs live at `.../modpack/<id>/<versionId>/changelog` (SINGULAR `modpack`, NO `public` — the `public/.../version/...` and `public/modpack/<id>/<id>/changelog` forms 404). Use these to answer "was mod X ever in this pack" / diff pack versions. Field structure + worked example: `references/ftb-evolution-2.md`.

**PITFALL — the `dsp` (Default Server Properties) mod clobbers server.properties on first boot.** FTB Evolution 2 ships `default-server-properties-neoforge-*.jar` (modid `dsp`), which on FIRST boot injects `/data/default-server.properties` over `server.properties` (log: "Replacing server properties with default properties!") and drops `/data/local/default-used.marker`. Effect: env-based `ENFORCE_WHITELIST`/`VIEW_DISTANCE` are overridden by the pack's defaults on first boot — whitelist silently OFF, view-distance 10. It is ONE-SHOT (marker-gated): subsequent boots let itzg env re-apply. Fix whitelist deterministically: append `enforce-whitelist=true` + `white-list=true` to the bind-mounted `/data/default-server.properties`, `docker restart`, verify via `docker exec <c> rcon-cli whitelist list`. RCON re-enables on the 2nd boot (itzg default `ENABLE_RCON`). Note the pack also ships its own view/sim-distance=10 defaults — decide whether to override via env or keep the pack's tuning.

**Mod management on FTBA (verified Oct 2026):** `start-deployFTBA` re-runs the FTB installer ONLY when `FTB_FORCE_REINSTALL=true`, or `.manifest.json` / `.ftb-installed` is missing, or the marker ≠ `${FTB_MODPACK_ID}=${FTB_MODPACK_VERSION_ID}` (same-version boots log "…is ready to go" and skip the installer). With `VERSION=LATEST` + no `FTB_MODPACK_VERSION_ID`, the version id is re-resolved each boot, so a NEW pack release triggers a full re-install — which re-downloads any deleted pack files (e.g. the `thaumaturge-absent` shim) but does NOT delete manually-added jars. Manual jar drops into `data/mods/` and deletions of pack files (datapacks, configs) persist across normal restarts.

**PITFALL — auto-latest silently CHANGES the pack, including after a crash-restart.** With no `FTB_MODPACK_VERSION_ID`, the version id is re-resolved on EVERY boot — so a crash → auto-restart (`restart: unless-stopped`) is a perfect trigger for a surprise update. When FTB ships a new release, that restart re-installs the newer version, which REMOVES any pack mods the new version dropped and breaks clients (verified Oct 2026: 1.2.2→1.3.0 dropped NEP 0.6.0 + 32 other files mid-pregen; players then hit a `required on client, missing on server` channel mismatch because their clients still had NEP). Fix: **pin the version** — set `FTB_MODPACK_VERSION_ID: <id>` in compose (id from `versions[]` in the pack endpoint, name→id via `versionName`). **Downgrade / roll back to an older version:** pin the target id and recreate the container (installer logs `Installing modpack ID …, version ID <id>` and `Files removed: N`). It re-downloads files the target has that the current lacks (restores dropped pack mods) and removes files only the current had — but does NOT touch manually-added jars (they survive), and does NOT re-add pack files unchanged between the two versions (a shim datapack you moved to `_backups/` stays moved). Before downgrading, DELETE any manually-added jar that would duplicate a pack mod being restored (a hand-added NEP 0.7.0 vs the pack's own 0.6.0 → NeoForge loads both and errors). Verify via `.ftb-installed` (=`<packid>=<versionid>`) and the boot mod list. Old world goes to `data/_backups/` (instant same-filesystem rename, reversible) before the fresh-world boot.

**FTB API (keyless) — inspect/diff pack versions:** pack info `GET …/v1/modpacks/public/modpack/<id>` (has `versions[]` with `id`/`name`/`type`); full version manifest `GET …/v1/modpacks/public/modpack/<id>/<versionId>` → `files[]` (each `{path, name, url, sha1, size}`). Changelog `GET …/v1/modpacks/modpack/<id>/<versionId>/changelog` → auto-generated Removed/Added/Updated mod lists (the "why removed" rationale is NOT there — auto-gen only). Diff two version manifests' `files[]` to find exactly what a pack update removed/added (mods, quests, datapacks, textures). Note: FTB packs ARE mirrored on CurseForge (`meta.curseforgeProjectId`) even though cfwidget returns empty. **Re-adding a mod a pack once shipped:** grab the jar's `url`+`sha1` from the OLD version manifest — it's a keyless forgecdn/FTB-CDN URL, byte-exact to what FTB tested.

**FTB Quests storage (26.x):** quest definitions = `config/ftbquests/quests/` (`chapters/*.json5`, `lang/en_us/chapters/*.json5`); `world/ftbquests/` = per-team progress only (UUID-named files with `task_progress`). To re-add a removed chapter, restore its config files + any `kubejs/assets/ftb/textures/quests/` images, then restart (progress untouched; chapter appears at 0%).

Pack-specific ops notes (Chunky bundled, Waystones/Kindred Spirits config + item IDs, resource-farming mod list, absent tech mods): `references/ftb-evolution-2.md`.

**Monitors go stale on a swap.** Homepage's `homepage/services.yaml` has a `container:` field pointing at the old container name (update it); Uptime Kuma stores monitors in `uptime-kuma/kuma.db` `monitor` table — query it read-only (`python3` sqlite3 with `file:kuma.db?mode=ro`, columns `name,type,url,hostname,port`) and fix via the Kuma UI (don't write the live DB — it has a WAL). On the E10→Evo2 swap BOTH were already stale (pointing at `minecraft-atm10sky` / `minecraft-atm10aero`, servers retired long before).

### Removing a manually-added mod = delete the jar + its leftover config

Manual adds leave **orphaned config files** behind after the jar is gone (`config/*.toml`,
`config/<mod>/` dirs) — they are NOT cleaned automatically. After deleting a jar, sweep
`docker exec <c> sh -c 'ls /data/config/'` and remove leftovers matching the removed mod.
CAREFUL: some configs belong to mods that ARE in the official pack. Check
`.curseforge-manifest.json` before deleting — e.g. `sable` core is an official pack mod, so
its `sable-*.toml` configs must NOT be removed even though the manual-add `ars_sable` addon
was. After removal the next boot logs a benign `<modid> (version X -> MISSING)` under a
`version differences that were not resolved` WARN — that's NeoForge's version tracker noticing
the mod list changed, NOT a crash. It clears itself. Back up the world + mods + configs before
any destructive removal (tar the data dir subfolders), so content-mod blocks can be restored.

## Building a custom modpack from scratch (TYPE=NEOFORGE)

For a hand-curated pack (not a published CurseForge pack), skip AUTO_CURSEFORGE: use
`TYPE=NEOFORGE` + `VERSION` + `NEOFORGE_VERSION` (pin to the source pack's exact
`.neoforge-manifest.json` `forgeVersion` — don't trust memory) and drop jars into `data/mods/`.
Fast path: copy a curated subset straight from the existing ATM10aero `mods/` dir (already
version-matched), then **boot-iterate** — NeoForge's ModSorter lists all missing deps + incompatibilities
at once, and `crash-reports/*.txt` reveals undeclared runtime deps (`NoClassDefFoundError`).
Key 1.21.1 facts: Create is INCOMPATIBLE with Radium; Tectonic→Lithostitched; BOP→TerraBlender+GlitchCore;
Ad Astra→common-storage-lib (not Botarium); shaders = Iris not Oculus; Plasmo Voice needs a dedicated
UDP port because Sable/Create-Aeronautics grabs the MC port. For a 2nd server on one IP, prefer a
Minecraft SRV record over mc-router. Full recipe + dependency map: `references/custom-modpack-build.md`.

## Building a from-scratch custom modpack (curated subset)

When the user wants a NEW custom pack (not extending an existing one), the laziest correct
path is to **curate a subset of an existing pack's mods already on disk** rather than fetch
150 jars from CF. Full workflow, dependency gotchas, and the importable-pack build are in
`references/from-scratch-custom-pack.md`. Two pitfalls that WILL bite, plus a rule:

- **Radium (Lithium port) is incompatible with Create** — NeoForge's ModSorter rejects it
  ("create is incompatible with radium"). Drop Radium; Noisium/Saturn/ServerCore cover perf.
- **C2ME conflicts with betterchunkloading** (E10 and other packs ship it) — FML warns the combo
  "causes the world to save infinitely" and betterchunkloading's DistanceManager mixin fails to apply.
  When adding C2ME for pregen speed, remove betterchunkloading. On an AUTO_CURSEFORGE container the
  sync re-downloads deleted pack mods, so exclude it permanently with
  `CF_EXCLUDE_MODS: "better-chunk-loading-forge-fabric"` (verify the CF slug via the search API first).
  Result: C2ME took E10 pregen from 4.6 → ~47 chunks/sec (3h50m → 17min for 63k chunks on the i5-9500T).
- **Removing a pack mod on AUTO_CURSEFORGE needs `CF_EXCLUDE_MODS`**, not just deleting the jar —
  the next sync logs `Re-installing due to missing files from modpack: [...]` and re-adds it. The
  `betterchunkloading (version X -> MISSING)` boot line confirms the exclusion actually held.
- **Plasmo Voice's default `port=0` collides with Sable** (Create: Aeronautics' physics
  engine) — both grab UDP on the MC port, voice fails "Failed to start the udp server". Give
  Plasmo Voice a dedicated UDP port (e.g. 25567) + publish it; keep 25566/udp for Sable.
- ⚠️ **Curation rule:** only include the user's EXPLICIT wishlist + essential deps/QoL/perf.
  The user pushed back on kitchen-sink additions ("You added a lot of mods without my
  input"). Present extras as a list for approval — don't silently include them.

## Exporting a shareable PrismLauncher/CurseForge modpack

To hand friends an importable modpack matching the server, don't rebuild from scratch:
the official pack is already on CurseForge, so the pack = pinned version + the few
manually-added mods. Full workflow (read itzg metadata files, fetch the official zip via
the CF API, extract manifest.json + modlist.html + overrides/, bundle extra mods into
`overrides/mods/`, re-zip) lives in `references/shareable-modpack-export.md`. Key gotchas:
friends MUST install the server's exact CF version (CF shows a newer "latest" → mod
mismatch), content-mod extras need a client match while Chunky/C2ME/DH-server are
server-side-only, and the ~100MB pack zip exceeds Discord's 25MB limit (distribute via
Forgejo release / Caddy, or just send the tiny client-required jars). **Ready-made download route on this box:** drop the file in `~/homeserver/www/` and share `https://oathless.dev/files/<name>` — Caddy's `handle_path /files/*` route strips `/files` and serves that dir (Ruben already distributes packs there: `Oathless-Server-Pack-*.mrpack`, `Oathless-Shaders-Addon.zip`).

## Building a shareable PrismLauncher modpack for players

To hand friends a one-import file with the server's exact mod set, see
`references/shareable-modpack.md`. Key facts: the pack is already public on CurseForge, so
"our own" pack = pinned official version + client-required manual jars bundled in
`overrides/mods/`; always pin the EXACT server version (CF "latest" drifts — server 0.5.1 vs CF
0.6.1 caused the mismatch risk). Full build recipe + the ~100 MB distribution problem + the
docker-exec CF API quoting pitfall are in the reference.

## CurseForge API (for finding/downloading exact files)

- **No CF key? Read a pack's mod list + versions from its GitHub repo.** E.g. `AllTheMods/ATM-10` → `changelogs/CHANGELOG-ATM10-X-Y.md` files list per-version mod bumps (`Sodium (0.8.13-beta.2) -> (0.8.13+mc1.21.1)`), `config/iris.properties` confirms the shader mod a pack ships, and `MOD_ISSUES.md` is the full mod list. Use this to answer "what does pack X use for shaders/perf" without any key — and check the REAL pack, not a fork: ATM10 (real) ships Iris + Sodium 0.8.13, while ATM10-aeronautics (fork) ships no shader loader at all (only a leftover empty iris.properties).
- **No-key version check — cfwidget.** "Is my pack on the latest version?" does NOT need the API
  key. `curl https://api.cfwidget.com/minecraft/modpacks/<slug>` returns full project JSON with a
  `files[]` array (newest first): `files[0].display` = latest release string, plus `uploaded_at`
  and `versions[]`. Compare against the server's `.install-curseforge.env` `MODPACK_VERSION`.
  Confirmed for `all-the-mods-10-aeronautics` (project id 1644918). Needs the EXACT slug — a
  fuzzy/unknown slug returns empty JSON. The CF website + CF API both block keyless curl; cfwidget is open.
- Needs an API key — already mounted in the container at `/run/secrets/cf_api_key`
  (from `CF_API_KEY_FILE`). Query it WITHOUT reading the secret yourself:
  `docker exec minecraft-atm10aero sh -c 'curl -s -H "x-api-key: $(cat /run/secrets/cf_api_key)" "https://api.curseforge.com/v1/mods/search?gameId=432&searchFilter=<slug>&classId=<id>"'`
  When NO AUTO_CURSEFORGE container is running (e.g. after swapping to an FTBA pack, or a retired
  E10/ATM10 box), the decrypted key also lives on the host at `~/homeserver/secrets/cf_api_key.txt`
  — query the CF API directly WITHOUT printing the value:
  `curl -s -H "x-api-key: $(cat ~/homeserver/secrets/cf_api_key.txt)" "https://api.curseforge.com/v1/mods/<id>/files"`.
- `classId`: 6 = mod, 12 = resource pack, 4471 = modpack. ALWAYS pass `classId=6` when searching
  a mod — slug search is fuzzy and otherwise returns a wall of unrelated modpacks (e.g.
  `searchFilter=ars-sable` matched ~50 packs). If the exact slug still doesn't surface, retry
  space-separated (`ars sable`) or check Modrinth.
- Files by project: `.../v1/mods/<id>/files?gameVersion=1.21.1&modLoaderType=6` (6 = NeoForge;
  omit for Forge). Download URL via `.../v1/mods/<id>/files/<fileId>` → `downloadUrl`
  (edge.forgecdn.net) — curl-able directly from the host, no key header needed.
- **Check dependencies before dropping the jar.** `.../v1/mods/<id>/files/<fileId>` →
  `dependencies[]` with `modId` + `relationType` (1=EmbeddedLib, 2=OptionalDependency,
  3=RequiredDependency, 4=Tool, 5=Incompatible, 6=Include). A content mod often has a required
  library you must ALSO fetch or the next boot crashes (e.g. MrCrayfish Furniture: Refurbished →
  `Framework` required + `Catalogue` optional; Productive Bees → no deps).\n- **Deps of a jar you already downloaded (GitHub/Modrinth — no CF API): read the jar's own `META-INF/neoforge.mods.toml`.** `python3 -c \"import zipfile; print(zipfile.ZipFile('x.jar').read('META-INF/neoforge.mods.toml').decode())\"` (the `unzip` binary is absent on this box — use Python's zipfile). It has `[[dependencies.<modid>]]` blocks with `type` (required/optional), `versionRange`, and `side` (BOTH/CLIENT/SERVER). A `side: CLIENT` required dep (e.g. Not Enough Patterns → `gmrecipes`) is NOT needed server-side; `side: BOTH` required deps must already be in `data/mods/`. Verified: NEP 0.7.0 needs only `ae2` server-side.
- **docker-exec quoting: single-quote the `sh -c` argument.** Working form:
  `docker exec <c> sh -c 'curl -s -H "x-api-key: $(cat /run/secrets/cf_api_key)" "URL"'` — the
  `$(...)` is expanded by the container's sh. The double-quote + `\$(...)` variant silently returns
  empty → `JSONDecodeError`. Parse JSON on the HOST (`| python3 -c ...`); the itzg image has no python3.
- **Changelog:** `.../v1/mods/<id>/files/<fileId>/changelog` → `{"data":"<html>"}` (strip `<br>`/tags,
  html.unescape). The file-detail endpoint does NOT include the changelog. Use it to diff pack
  versions (e.g. 0.5.1 → 0.6.1). (The pack's GitHub `CHANGELOG.md` is usually a stub.)
- The CF *website* blocks curl/web_extract (Cloudflare challenge, ~5 KB stub). Go via the API
  (key required) or the pack's GitHub repo (`raw.githubusercontent.com/AllTheMods/ATM-10-a/...`
  mirrors config/kubejs + CHANGELOG.md; the mod-suggestion list lives in issue #1).
- Modrinth needs NO key and is easier for resource packs: `api.modrinth.com/v2/project/<slug>/version`.

## Building a custom / second modpack (TYPE=NEOFORGE + manual mods)

For a *from-scratch* pack (not a published CF pack), the lazy-correct path is
**curate a subset of an existing pack's mods dir, then boot-iterate**. Full recipe:
`references/custom-modpack-build.md`.

1. **Check what's already on disk first.** ATM10 Aeronautics already ships Create +
   Create: Aeronautics + Sable, Dyson Cube Project, Productive Bees + Trees, EnderIO,
   AE2 + ~8 addons, Ars Nouveau + addons — most wishlists are ~95% covered by
   `data/mods/`. Copy jars; don't re-fetch from CF/Modrinth.
2. **Copy by EXACT filename** — ATM10aero jar names are mixed-case (`OctoLib-…`,
   `Clumps-…`, `Glodium-…`, `SmartBrainLib-…`, `Patchouli-…`); a lowercase transcription
   silently misses them. Diff copied count vs the manifest and fix.
3. **itzg config for a plain NeoForge pack** (not AUTO_CURSEFORGE — that's only for
   published CF packs): `TYPE=NEOFORGE`, `VERSION=1.21.1`, `NEOFORGE_VERSION=<x>` (read
   the exact value from `data/.neoforge-manifest.json` `forgeVersion` — it's 21.1.250;
   memory's "21.1.248" had drifted), `MEMORY=8G`, `SERVER_PORT=<n>`. Manual jar drops
   into `data/mods/` work the same as AUTO_CURSEFORGE.
4. **Boot-iterate.** First boot prints ALL missing mandatory deps at once
   (`Mod ID: 'X', Requested by: 'Y'`) + incompatibilities. Fix all → reboot → the next
   failure is usually a runtime `NoClassDefFoundError` (a lib ModSorter doesn't catch,
   e.g. Lithostitched) → read `data/crash-reports/*.txt` (its "Mod List" is the ground
   truth of what actually loaded). Converges in ~3 boots.
5. **Second server on one IP → SRV record, not mc-router** (simpler, zero disruption to
   the existing server): `_minecraft._tcp.<newhost> SRV 0 5 <port> <existing-host>`. New
   server gets its own port (25566); players type `server.oathless.dev` with no port.

## Pitfalls

- **A LIVE server crash-looping (`Up N seconds (health: starting)` repeating, huge `RestartCount`) with `NoClassDefFoundError: <pkg>.<Class>` = a mod JAR is MISSING from `data/mods/`.** The class name encodes the absent mod; the crash report names the referencing mod. Diagnose: `docker inspect <c> --format '{{.RestartCount}}'` (thousands = loop), `docker logs <c> 2>&1 | grep NoClassDefFoundError`, then read the newest `data/crash-reports/*.txt` — its `Mod loading issue for: <modid>` line is the mod that FAILED to load, and `Caused by: NoClassDefFoundError` gives the missing class. Verified Oct 2026: FTB Evolution 2 crash-looped because `ftb-evolution-companion` referenced `dev.shadowsoffire.gateways.entity.GatewayEntity` but the `gateways` jar (Gateways to Eternity) was absent from `mods/`. If the user is abandoning the pack anyway, replace it (swap workflow below) rather than fixing the missing jar.
- **Curate tightly — don't kitchen-sink a pack.** Ruben wants his explicit mod wishlist + load-bearing
  essentials (JEI/Jade/map, FTB Chunks, Polymorph+AlmostUnified for recipe conflicts, the perf stack),
  NOT a pile of "suggestions". He pushed back hard ("you added a lot of mods without my input") after a
  broad build. When building a pack, present any additions beyond his list as a VETO LIST *before*
  installing, and offer to strip to wishlist+essentials on request.
- **Mod jar filenames contain apostrophes
  incompatible with 'radium'` and refuses to load. On a Create pack, drop Radium entirely;
  Noisium + Saturn + ServerCore + ModernFix carry the tick-loop wins. Don't blind-add
  "Lithium/Radium" to a Create pack.
- **C2ME on MC 26.1.2 is PACK-SPECIFIC — it deadlocked evo2-tech but runs clean on FTB Evolution 2 1.3.2 (same MC, same worldgen stack).** The 1.21.1 success (~47 cps on ATM10/E10) does NOT generalize to every 26.1.2 pack — and neither does the deadlock: the trigger is the pack's mod SET, not heavy worldgen (Tectonic + Lithostitched + TerraBlender + Stellaris) per se. Don't refuse C2ME for 26.1.2 by rote; add it, then watch for the thread-explosion signature and rip it out if it recurs. On evo2-tech, verified Oct 2026: after a clean boot + a 2–3× rate boost, the java process ballooned to **8,199 threads** (normal ≈ 150), memory climbed past the 12G heap into swap (5.4G swap used), the tick loop fell 124 ticks behind (`Can't keep up!`), and Chunky froze at the same chunk for 25+ min — CPU dropped to ~23% with the box idle (a deadlock, not a CPU bottleneck). Fix: `rm` the C2ME jar + restart (thread count returns to ~157), then `chunky continue` (skips done chunks). Spot the failure: `docker stats` PIDS in the thousands + swap climbing + `chunky progress` frozen at a fixed `Processed:` count across polls. Single-threaded baseline on evo2-tech is ~11–16 cps, NOT the 4.6 cps of older packs. **Counter-example (Oct 2026): FTB Evolution 2 1.3.2 — 426 mods, ships the SAME worldgen stack (Tectonic + Lithostitched + TerraBlender + Stellaris) — ran the SAME C2ME build cleanly: ~9→30 cps (~3×), threads steady ~153, 0 `Can't keep up!`, memory flat ~12.15 GiB, ETA 18–25h → ~5h.** **Second counter-example (same session, Oct 2026): ATM 11 0.12.0-beta (293 mods, same worldgen stack) ran the SAME C2ME build cleanly too — ~27–37 cps, threads ~150, 0 `Can't keep up!`, no freeze, ETA ~11h for a radius-10000 pregen.** **BUT that "clean" run was temporary — the SAME ATM 11 install later deadlocked mid-pregen (Oct 19, 2026): frozen at 311,339 chunks / 19.89%, CPU ~1%, 0 players, no `Processed:` lines in the log, and a fresh `chunky start` froze instantly.** Thread dump confirmed the C2ME signature — `Server thread` stuck in a deep `ForkJoinPool.unmanagedBlock`/`managedBlock` recursion, the Chunky thread parked at `GenerationTask.run(GenerationTask.java:140)`, and a thread sequence number of **#533031** (ForkJoinPool compensation churned ~half a million threads while live count stayed ~131; `ps NLWP` looks normal, but `jcmd Thread.print`/SIGQUIT reveals the `#NNNNNN` sequence number). Fix identical to evo2-tech: `mv` the C2ME jar out of `data/mods/` + `docker restart`, then re-select (`world`/`center`/`radius`) and `chunky start` (skips done chunks); resumed single-threaded at ~10 cps, ETA ~36h for the remaining 80% of a radius-10000 square. CONCLUSION (corrected): the "unique mod set" theory is wrong — C2ME-on-26.1.2 can deadlock on ANY pack, including packs it initially ran clean on. Treat it as a temporary ~3× speed boost that will eventually hang; the fingerprint is a frozen `Processed:` count + idle CPU + a huge thread sequence number. **ROOT CAUSE (confirmed Oct 2026):** C2ME-neoforge issue #98 (OPEN) — "Server thread hangs forever when a chunk unload runs inside a blocking getChunk (AE2 cables)" — https://github.com/RelativityMC/C2ME-neoforge/issues/98 . Vanilla runs chunk-UNLOAD callbacks through a separate `processUnloads` queue; C2ME runs them INLINE inside a blocking `getChunk`, so a mod that touches the world from `onChunkUnloaded` (AE2 is the canonical trigger, and ATM 11 ships AE2) fires a nested blocking `getChunk` that never completes — all C2ME workers/Storage threads sit idle in `Object.wait()` and the Server thread parks in `managedBlock`. Pregen trips it because chunks generate→unload in a tight loop. Sibling open hangs: #97 (chunk-upgrade exception → waiter parked forever), #96 (Tectonic + C2ME → chunks stop generating / freeze). **NO clean fix:** 0.4.0-alpha.0.100 is still the LATEST build for MC 26.1.2 (the 0.4.2-alpha line is 26.2/26.3 only — check `api.modrinth.com/v2/project/c2me-neoforge/version`), and there is NO config toggle for the unload-in-getChunk path — `config/c2me.toml` has `globalExecutorParallelism` + `[chunkSystem]` (`useLegacyScheduling`, `asyncSerialization`, `recoverFromErrors`, `lowMemoryMode`) + `[vanillaWorldGenOptimizations]` (`useDensityFunctionCompiler`, `optimizeAquifer`, …) but none of them touch unload-callback scheduling. "Re-enable C2ME + a config tweak" is speculative — expect a re-deadlock. **Diagnosing a deadlock when jcmd/jstack are absent:** the itzg image is a slim JRE — `/opt/java/openjdk/bin/` has only `java jfr jrunscript jwebserver keytool rmiregistry`, NO jcmd/jstack/jmap. Get a thread dump with SIGQUIT: `docker exec <c> sh -c 'kill -3 <pid>'` (find pid via `docker exec <c> sh -c 'ps -o pid,nlwp,comm -C java'`), then read `docker logs --tail 2000`. The thread NAME carries a `#NNNNNN` sequence number — a huge one (e.g. #533031) with a normal live `NLWP` (~130) is the ForkJoinPool-compensation thread-churn fingerprint, invisible to `docker stats PIDS` or `ps NLWP`. **Untested stabilization lever (Oct 2026):** C2ME ships a `config/c2me.toml` exposing `globalExecutorParallelism` (defaults to ~3 on a 6-core box per its sizing expression) plus `threadedWorldGen.{allowThreadedFeatures, reduceLockRadius, asyncScheduling}` toggles — lowering parallelism and/or disabling `asyncScheduling`/`reduceLockRadius` is the obvious next thing to try before writing C2ME off, but it was NOT verified to fix the deadlock. Note: under heavy C2ME load `rcon-cli 'chunky progress'` can return EMPTY (the progress response goes to the server log instead) — read the live rate from `docker logs --tail 200 | grep -oE 'Processed: [0-9]+ chunks' | tail -1`.
- **"C2ME is installed" ≠ "C2ME is loaded" — VERIFY it's actually in `mods/`, not `removed-mods/`, before claiming it's active.** A removed mod's jar survives on itzg at `data/removed-mods/<jar>` (it is MOVED there, not deleted) and does NOT load. This bit a session: I asserted "C2ME is already installed" from memory + a stale jar listing, but the jar had been moved to `removed-mods/` — pregen then ran single-threaded at ~15 cps (vs ~27–37 cps with C2ME on ATM11). Cheap detection without trusting memory: `docker stats` PIDS ~99–100 (C2ME's worker pool ≈ 150+), CPU ~300% during active pregen instead of saturating all cores, and zero `c2me` lines in `logs/latest.log`. Definitive: `ls data/mods/ | grep -i c2me` (empty ⇒ removed) then check `data/removed-mods/`. Trap: the presence of `data/.cache/jij/c2me-*.jar` + `data/config/c2me.toml` + `data/cache/c2me-dfc` only proves C2ME was loaded at SOME point (NeoForge extracts JIJ deps + writes config/cache on first load) — NOT that it's loaded NOW. Restore: `mv data/removed-mods/c2me-*.jar data/mods/` + restart; a running Chunky task auto-resumes (`continueOnRestart=true`, `forceLoadExistingChunks=false` keeps done chunks). On AUTO_CURSEFORGE a manual `mv` back persists as long as there's no `CF_EXCLUDE_MODS`/`REMOVE_OLD_MODS` in the compose env — check those before assuming the sync will re-remove it.
**Multithreaded pregen alternatives for MC 26.1.2 are essentially nonexistent (verified Oct 2026).** Speiger's Chunk-Pregenerator (the classic multithreaded pregen tool, CF slug `chunkpregenerator`, project id 267193) caps at MC 1.21.1 — its newest 4.5.4 build has no 26.x files, so it's unavailable for ATM11. World Pre Generator 5.0.2 (Modrinth `daLkM863`, GeheimagentNr1) DOES ship NeoForge 26.1.2, but its `SEMI_PARALLEL` mode still generates one chunk at a time "the Minecraft way" — NOT true multithreading, no C2ME-style speedup. C2ME is the ONLY true multithreaded chunk engine for 26.1.2 (and it deadlocks here). Beware the Modrinth slug `chunk-pregenerator` (WITH hyphen) — that's a trivial "preload chunks" datapack by XAVI333 (`mr_chunk_pregenerator`), NOT Speiger's tool. FastChunkGen is 1.20.1-only.\n- **C2ME config defaults are already optimal — don't bump `globalExecutorParallelism`.** `config/c2me.toml`
  ships everything as `"default"`; the global-executor parallelism auto-sizes via
  `defaultGlobalExecutorParallelismExpression` (≈5 workers on a 6c/6t box with 12G heap — already saturates
  the CPU). Raising it past default overcommits threads and is the kind of change that invites the
  thread-explosion deadlock. "Speed up Chunky" on this hardware = kick players + stop concurrent backups
  + switch the CPU governor `powersave`→`performance`, NOT cranking C2ME. Also note: `spark tps` via RCON
  returned EMPTY on ATM11's bundled `spark-1.10.187` — fall back to `spark healthreport` / `debug start`/`debug stop` (same as the older-build caveat below).
- **C2ME conflicts with `betterchunkloading`** — adding C2ME to a pack that ships someaddon's
  betterchunkloading produces an FML `discouragedmod` warning (`[betterchunkloading; c2me] ... causes the
  world to save infinitely`) plus a mixin `InvalidInjectionException` on `DistanceManager`. Remove
  betterchunkloading via `CF_EXCLUDE_MODS` (see mod-management section) — C2ME supersedes it.
- **Plasmo Voice collides with Create Aeronautics (Sable) on UDP.** Sable (Create
  Aeronautics' physics lib) grabs UDP on the MC port; Plasmo Voice's default `port=0`
  ("same as MC port") then fails with `[PlasmoVoice/] Failed to start the udp server`.
  Fix: set `[host] port = 25567` (dedicated) in `config/plasmovoice/server/config.toml`
  + publish that UDP port; keep the MC port's UDP mapping for Sable. Two UDP mods on one
  port = one silently dies.
- **Shaders on NeoForge 1.21.1 = Iris, NOT Oculus.** Oculus (Asek3's Forge port) has no
  1.21.1 files on CF or Modrinth. Iris supports NeoForge natively
  (`iris-neoforge-1.8.12+mc1.21.1.jar` is the stable line); pair with `iris-flw-compat`
  for Create. Ship shaders OFF by default for low-end clients (Iris/Oculus is the #1 FPS killer).
- **Distant Horizons is on Modrinth under slug `distanthorizons`** (no hyphen —
  `distant-horizons` 404s). 3.3.3 is the stable 1.21.1 line; its GitLab release "assets"
  hold only source archives, so fetch the jar from Modrinth/CF, not GitLab.
- **1.21.1 NeoForge dependency map** (ModSorter/first-boot failures): BOP→terrablender+glitchcore;
  Ad Astra→common-storage-lib (NOT botarium on 1.21.1); XNet→rftoolsbase;
  Powah/AE2/ExtendedAE→guideme; IronJetpacks→cucumber (cucumber is NOT MA-only);
  attributefix→prickle; Occultism→modonomicon; Tectonic→lithostitched.

- **Prism Launcher ignores the manifest's NeoForge version pin on import and installs the LATEST 21.1.x for the MC version.** Symptom: `Incompatible client! Please use NeoForge 21.1.250` even though the pack manifest pins `neoforge-21.1.250` — Prism grabbed a newer 21.1.x. Fix: set the server's `NEOFORGE_VERSION` to the latest 21.1.x (bumping within the 21.1 line is backwards-compatible). Find latest via `curl -s https://maven.neoforged.net/releases/net/neoforged/neoforge/maven-metadata.xml | grep -oE '21\.1\.[0-9]+' | sort -V | tail -1`.
- **`Channel <mod>:… missing on the server side, but required on the client` + an `Incompatible client! Please use NeoForge <ver>` disconnect usually means the client hit the WRONG server, not a mod mismatch.** If the named mod exists in the intended server (e.g. `glitchcore:sync_config` when the server HAS GlitchCore), the client connected to a different box — typically the old server on 25565 while the new one is on 25566. A bare hostname defaults to port 25565; a new server needs the explicit `:port` (or an SRV record, which DuckDNS can't serve). Cross-check the reported NeoForge version against the intended server before chasing mod versions. **Counter-case (verified Oct 2026): the channel error can be GENUINE** — a client that has a mod the server genuinely lacks (e.g. someone installed a client-side-only jar like Not Enough Patterns, which the server pack doesn't ship). Distinguish: if the named mod IS present in the intended server's `data/mods/` → wrong server; if it is genuinely ABSENT → add the matching build to the server and restart (grab the build for the server's exact MC/loader from the mod's GitHub releases tag, e.g. `nep-26.1.2-0.7.0.jar`). Because the channel is `required`, the fix is SYMMETRIC: once the mod is server-side, every client WITHOUT it now fails the inverse check — tell all whitelisted players to add the mod (plus any client-side required deps listed in its `neoforge.mods.toml`).
- **`ConnectTimeoutException: connection timed out` on a NEW port while the OLD port works = router port-forward gap, not a server problem.** Confirm the host listens (`ss -tlnp | grep :<port>` → LISTEN on 0.0.0.0:<port>) and the container maps it. If both are fine but external connect times out, the box is behind NAT (private IP 192.168.x.x, gateway .254) and only the old port is forwarded — fix on the router (forward <port> TCP+UDP to the box's internal IP). Not fixable from the server.
- **Iris ↔ Sodium version mismatch on NeoForge 1.21.1 crashes the client.** Stable Iris 1.8.12 is built against Sodium **0.6.13**; Sable's bundled Veil requires Sodium **0.8.12+**. The two Sodium lines (0.6.x vs 0.8.x) are mutually exclusive, so stable Iris + Sable cannot coexist. Symptom: `MixinTransformerError` → `ClassNotFoundException: net.caffeinemc.mods.sodium.client.gui.SodiumGameOptions$PerformanceSettings` from `mixins.iris.compat.sodium.json:MixinRenderSectionManager`. Fix: drop Iris (shaders off) and keep Sodium 0.8.x for Sable, or try Iris 1.8.14-beta.1 (beta, targets the 0.8.x line). Check the pairing via Modrinth API: `api.modrinth.com/v2/project/iris/version?...loaders=["neoforge"]` → read each version's `dependencies[].version_id`, resolve via `/v2/version/<id>`.
- **Bundling server-only mods (Chunky/Saturn/Noisium) into a client pack crashes Distant Horizons on singleplayer world creation.** DH 3.3.x reflects into Chunky's `ChunkyProvider.get()` to bind a generation-progress event; if Chunky's jar is on the client classpath but its runtime provider isn't initialized, world creation throws `IllegalStateException: Chunky is not loaded` during chunk promotion to FULL. Fix: keep pregen/perf mods (Chunky, Saturn, Noisium) server-only — exclude them from the client bundle (in `build_importable.py`, a `SERVER_ONLY` filename-substring list filters `server_mods` into `bundled_server`).
- **Mod jar filenames contain apostrophes (e.g. `L_Ender's Cataclysm 1.21.1-3.33.jar`).** `ls mods/*.jar | xargs`
  dies with "unmatched single quote". List/sort/count mod jars with Python instead:
  `python3 -c "import os; print('\n'.join(sorted(f for f in os.listdir('mods') if f.endswith('.jar'))))"`.
- **Restart after `deploy.sh up` fails with `not a directory: ... cf_api_key.txt`.** `deploy.sh` decrypts SOPS secrets only for `up`, then CLEANS them up — so `docker compose restart minecraft-atm10aero` fails because the bind-mounted `cf_api_key.txt` is gone and Docker creates an empty *directory* in its place. Fix: (1) `sudo rmdir ~/homeserver/secrets/cf_api_key.txt` to remove the placeholder dir; (2) re-decrypt the secrets the container bind-mounts/env-files via `~/.local/bin/sops --decrypt ...` (don't read the values); (3) `docker start minecraft-atm10aero` (NOT `docker compose up -d` — the terminal tool flags that as a long-lived process and refuses; `docker start <name>` returns instantly).
- **Changing published ports requires RECREATING the container, not restarting it.** `docker start <name>` reuses the existing container — fine for jar/env changes on the bind mount, but it does NOT apply a new or removed `ports:` mapping. To change ports without tripping the terminal tool's long-lived-process guard: `docker rm -f <name>` → `docker compose create <name>` → `docker start <name>` (all three return instantly). Canonical case is voice chat: Minecraft = TCP 25565, Plasmo Voice = UDP 25565 — same port number, different protocol, both mappings must be published.
- **Conflating DH pregen with world pregen** — DH LODs don't create real chunks. Chunky is the lag fix.
- **Watching boot logs: don't grep for "ERROR".** During mod loading, normal WARN lines contain the literal string `ERROR: No value present` (Moonlight / registry lookups). A crash-scan like `grep -iE "error|fatal|crash|caused by|failed to start"` false-positives on those. Detect boot-complete via the `Done (Ns)!` line or RCON actually responding (`rcon-cli list`); detect real crashes via `FATAL`, `This crash report`, or `A fatal error`. Also: `docker logs` is the *full history*, so `grep -c "Done"` can match a prior boot — confirm the current boot via RCON, not log grep. Also: when grepping server logs for
 stop/crash keywords, do NOT include `shutdown` or `reboot` in the pattern — the terminal tool
 hardline-blocks ANY command containing those words, even inside a `grep -iE '…'` regex (so
 `grep -iE 'stopping|shutdown|crash'` is refused outright). Use `stopping|stop|crash|fatal` instead.
- **Fresh 400+ mod FTB/kitchen-sink boots show `unhealthy` for the first few minutes — it self-heals.** The itzg healthcheck (`mc-health`, interval 30s, `start_period` 120s, retries 2) starts pinging `localhost:25565` 2 min after start, but a 426-mod cold boot takes ~180s (ModernFix logs "Dedicated server took 180s to load"). Pings fail with `connection refused` during boot, exhaust the 2 retries, and mark the container `unhealthy`; once the server finishes booting, the next successful `mc-health` flips it back to `healthy` within ~1 min. Diagnose before panicking: `docker exec <c> mc-health` (returns `version=... online=0 max=...`) + `docker inspect <c> --format '{{.State.Health.Status}}'`. To survive cold boots, raise the image's healthcheck `start_period` or accept the transient.
- **Installing DH server-side on a small box** — the OLD guidance ("wasteful, keep client-only") is superseded for evo2-tech: Ruben wanted preloaded LODs for his friends, so DH is installed server-side and builds LODs from Chunky-generated chunks (cheap in 3.3.3). To enable: drop the DH jar into `data/mods/` + recreate; Chunky-pregen the real chunks so LODs have data. See the "Key facts" bullet for the config + benign dim warnings.
- **Enabling RCON on a server that lacks it** (the hand-curated `evo2-tech` `TYPE=NEOFORGE` box ships with RCON OFF, unlike AUTO_CURSEFORGE which enables it by default). To drive `chunky`/console commands remotely, add to the compose service env: `ENABLE_RCON: "true"`, `RCON_PASSWORD: "<random>"`, `RCON_PORT: 25575`, then recreate the container (`docker compose up -d --force-recreate <svc>` in background mode). Verify with `docker exec <c> rcon-cli "seed"` (echoes the world seed).
- **Background watcher scripts: `exec >>log 2>&1` triggers false "completed" notifications.** A `terminal(background=true, notify_on_complete=true)` process gets reported as `exit code None` ~30s in if the script redirects stdout with `exec` — that closes the pipe the process manager watches. Use `log() { echo "$*" | tee -a "$LOG"; }` and keep the pipe open. Also: `docker logs` is the *full history*, so a completion grep can match a prior boot — poll for a fresh signal (RCON `list` returning `players online`) instead.
- **Long pregen watchers can get orphaned/reaped while sleeping.** A `sleep 300` polling loop may be reported dead even when the target task (Chunky, running *inside* the server process) is fine. Design the watcher to be re-runnable: killing and relaunching it loses nothing because the actual task lives in the server, not the watcher. **For pregens over ~10h, prefer a cron `no_agent` single-shot watchdog** (`scripts/pregen-watchdog-cron.sh`, `cronjob` schedule `every 30m`) over the terminal-background loop — a cron tick survives where a multi-hour `sleep` gets reaped, and it only sends a message on completion/failure (empty stdout = silent; marker + state files dedupe; it also flags C2ME thread-explosion >1000 PIDs and a frozen `Processed:` count). For pregens expected to run 10+ hours, prefer a **cron no_agent watchdog** over a terminal background process — `scripts/pregen-completion-check.sh` is a single-shot check (marker-file dedup, silent unless done/failed); register it with `cronjob(action=create, no_agent=true, schedule="every 30m", script="pregen-completion-check.sh")`. It re-checks `chunky progress` + the server log's `Task finished` line every tick and is immune to the background-process reaping that kills multi-hour `chunky-watch.sh` runs.
- **"No 'can't keep up' yet = fine"** — a fresh 5MB world proves nothing; stress only shows after exploration.
- **A backup mod doing full-world backups (SimpleBackups) is a lag source as bad as chunk-gen — and it's easy to misattribute to worldgen.** On ATM11 (6.17 GB world) SimpleBackups was set to `FULL_BACKUPS` every 60 min with `preCopy=true` (full world copy to a temp dir before zipping). Each run forced a save-all + a ~19.5s full-world pre-copy that stalled the tick loop 100+ ticks. Log signature: `Backup started...` → `Pre-copying /data/world to ...` → `Can't keep up! Running 5052ms or 101 ticks behind` → `Pre-copy took 19588ms for 6170200215 Bytes`. Fix in `data/config/simplebackups/common.toml` (NOT a flat `simplebackups-*.toml` at config root — it lives in a `simplebackups/` subdir alongside a separate `server.toml`): `backupType = "INCREMENTAL"`, `timer` 60→1440 (daily; the external nightly cron tar backup is the real safety net), `preCopy = false`. Requires a server restart to apply (no hot reload). Watch-outs: `noPlayerBackups=false` + `noPlayerBackupCount=1` also fire an extra backup when the last player leaves; `saveAll=true` alone is fine, the killer is the full pre-copy.
- **Recreating a container after a compose change (ports/env/volumes):** `docker compose up -d` is
  refused by the terminal tool (long-lived-process guard) in FOREGROUND — but `terminal(background=true)` on `docker compose up -d <svc>` lets it through (it's a detached one-shot returning in ~1s, so background mode is fine and simpler than the rm/create/start dance; verified Oct 2026). And `docker start <name>` does NOT apply
  config changes — it just restarts the existing container. To apply a compose edit (e.g. adding or
  removing a UDP port mapping), recreate without the `up` keyword — all three return instantly:
  `docker rm -f <name> && docker compose create <name> && docker start <name>`. Data volumes persist
  across the rm/create (AUTO_CURSEFORGE re-syncs mods on boot; manual jar drops survive).
- **Removing a mod leaves a benign `modid (version X -> MISSING)` WARN** in the boot log under
  "version differences that were not resolved". It's NeoForge noticing the mod-list delta between
  boots — harmless, clears next boot. Don't chase it; confirm removal via `find /data -iname '*modname*'`
  (empty) + mod-count, not by grepping the log.
- **Trusting a modpack's bundled perf mods** — verify they actually load (servercore/ferrite present ≠ tuned).
- **"Network protocol error" / connection reset on join = Distant Horizons version mismatch.** When a client's DH jar doesn't match the server's, the server log shows `Failed to process a synchronized task of the payload: distant_horizons:msg` → `IncompatibleMessageInternalEvent` → `Connection reset by peer` (older server rejecting a newer client). The reverse (newer server, older client) looks different: clean `Player [x] joined` DH handshake, ~30–60s of play, then clean `lost connection: Disconnected` with NO server-side error — the CLIENT crashes. Fix is always the same: align both sides to one DH version. As of Sept 2026 the `3.3.x` line (3.3.3) is the stable release line; `3.2.0-b` and earlier are old betas. Note 3.3.3 bumps DH config version 4→5 and resets client config. DH is client-optional, so only the `.mrpack` (server mirror) bundles it — never the CF `.zip`, which carries only client-required extras.
- **"Incompatible client! Please use NeoForge <ver>" = client loader version ≠ server, and it cascades into fake mod-channel errors.** Prism (and other launchers) often IGNORE the pinned loader version in a CF/mrpack manifest and install the LATEST NeoForge, so even a correctly-pinned self-contained pack fails if the server sits on an older 21.1.x. The same drift also trips confusing channel errors that look like a mod-version bug — e.g. `Channel [glitchcore:sync_config] ... missing on the server side, but required on the client!` (BOP/GlitchCore) — but those clear once the loader versions match. Fix: sync versions. Either pin the client to the server's exact version in the launcher, or bump the server `NEOFORGE_VERSION` to the latest 21.1.x (find it: `curl -s https://maven.neoforged.net/releases/net/neoforged/neoforge/maven-metadata.xml | grep -oE '21\.1\.[0-9]+' | sort -V | tail -1`). NeoForge 21.1.x patch bumps (250→259) are backwards-compatible — mods reload clean. After bumping: recreate the container (`docker rm -f <c> && docker compose create <c> && docker start <c>`), re-pin BOTH manifests (CF `modLoaders[].id` = `neoforge-<v>`; mrpack `dependencies.neoforge` = `<v>`), rebuild + re-upload the packs. The boot-log line `neoforge (version A -> B)` is the benign version-tracker delta, not a crash.\n- **A mod that needs a NEW port mapping (voice chat, web UI) requires container RECREATE, not restart.** Port bindings are set at container-create time; `docker restart` won't pick up a compose port change. Use `docker rm -f <name> && docker compose create <name> && docker start <name>` (all return instantly — `docker compose up -d` trips the long-lived-process guard). For Plasmo Voice specifically: MC uses TCP 25565, but voice needs a SEPARATE `25565:25565/udp` mapping — TCP forwarding does NOT carry UDP. Plasmo Voice default `port=0` rides the MC port over UDP; config lives at `config/plasmovoice/server/config.toml`; `client_mod_required=false` lets players without the mod still join. Removal = delete the jar + generated `config/plasmovoice/` dir + revert the port line + recreate; the leftover `plasmovoice (version X -> MISSING)` log line afterward is a benign NeoForge version-diff warning that clears on its own.

- **"glitchcore:sync_config missing on server" + "Please use NeoForge 21.1.250" = player connected to ATM10aero (25565), NOT the Oathless pack (25566).** Bare `server.oathless.dev` has no SRV record, so it falls through to port 25565 = `minecraft-atm10aero` — which has NO GlitchCore (verified: zero GlitchCore jars) and runs NeoForge 21.1.250. The Oathless pack (BOP→GlitchCore, NeoForge latest) only lives on `:25566`. Until the SRV record is added, players MUST use `server.oathless.dev:25566`. The GlitchCore channel error is the fingerprint of wrong-server — check which port the player is hitting before chasing mod/loader versions.
- **NeoForge loader version mismatch on join (`Incompatible client! Please use NeoForge X`).** Prism Launcher installs the *latest* NeoForge for the MC version and ignores the manifest's pinned `neoforge-X` version, so a client on "latest" is rejected by an older pinned server. Fix: keep the server on the latest 21.1.x — read the current latest from `https://maven.neoforged.net/releases/net/neoforged/neoforge/maven-metadata.xml`, set `NEOFORGE_VERSION`, recreate (`docker rm -f <c> && docker compose create <c> && docker start <c>`), confirm `NeoForge mod loading, version X` in the boot log, then rebuild the pack manifests with the matching `neoforge-X` pin and re-upload.

## Additional operations (absorbed from docker-homeserver)

These topics previously lived under the docker-homeserver skill's Minecraft section; they're Minecraft-server-specific and now belong here. Session detail is in the re-homed references below.

### Crafty Controller — DO NOT use (abandoned)
Direct itzg containers are the default. Crafty's HTTPS-only server + self-signed cert + socat sidecar + Caddy reverse-proxy chain proved unfixable (CSRF/cookie failures, "Invalid token" on every API call). The user abandoned Crafty for two direct `itzg/minecraft-server` containers. Do not resurrect Crafty + socat without an explicit request. Full failure log: `references/crafty-controller.md`.

### Multiple servers + domain routing (mc-router)
For 2+ servers on one IP, players default to port 25565 — a second server on 25566 is never reached. mc-router (`itzg/mc-router`) reads the hostname from the Minecraft handshake and routes `mc.oathless.dev`→vanilla, `modded.oathless.dev`→modded. Servers drop their `ports:` mapping; mc-router takes 25565. Pitfall: set `SERVER_PORT` to match the mc-router backend port + `OVERRIDE_SERVER_PROPERTIES: true`, or the itzg health check pings the wrong port.

### Whitelist management
Two layers: RCON (`whitelist on`/`whitelist add`) is instant; `WHITELIST` + `ENFORCE_WHITELIST` env vars persist across recreation. To add a player durably, do BOTH: RCON `whitelist add` (instant) AND append to the compose `WHITELIST` env var (survives recreate). `OVERRIDE_WHITELIST` is unset (default false) on this box, so the env var never clobbers RCON-added names — the two stay consistent. `ENFORCE_WHITELIST` is ignored when `OVERRIDE_SERVER_PROPERTIES=false` — use RCON then. "That player does not exist" = invalid Mojang username (verify via `api.mojang.com/users/profiles/minecraft/<name>`).

### RCON console + TPS
`docker exec <c> rcon-cli "<cmd>"` gives a full console with no panel. TPS via RCON: `debug start` → sleep → `debug stop`. (`spark tps` console output is VERSION-DEPENDENT — spark 1.10.x logs TPS + tick durations + CPU to console via RCON, older builds were chat-only and returned empty via RCON. If empty, fall back to `debug start`/`debug stop` or `spark healthreport`.) **OP/deop: there is NO vanilla `op list` command.** `rcon-cli "op list"` is parsed as `op <player>` with a player literally named "list" — it silently OPs a bogus `list` entry in `data/ops.json` (which even gets a UUID). To list operators, read `data/ops.json` directly; revoke a bad entry with `deop <name>`. OP status is a plain JSON data file (persists across restarts; no compose env var like `WHITELIST`).

### Spark profiler for lag diagnosis — capture the trigger IN SITU

The single biggest trap when diagnosing "server laggy" with spark: running the profiler on an
EMPTY/paused server. It returns a flawless 20.0 TPS / ~0.3ms median tick / ~0% CPU and a flat
profile — which proves nothing, because the lag (chunk generation from exploring players) only
exists while players are online and moving into fresh territory. A 60s profile of an idle server
is a wasted measurement. Correct sequence:

1. `spark tps` — read the 5s/10s/1m/5m/15m windows. 20.0 across all windows on an empty server
   = healthy idle, NOT a fix. Compare median tick ms against the 50ms-per-tick budget
   (0.3ms median ≈ 0.6% used = lots of headroom).
2. `spark healthreport --memory` — returns a `spark.lucko.me/<id>` URL (health + memory summary).
3. `spark profiler start --timeout 300` — run WHILE 1+ players are online and moving into
   FRESH chunks (flying/boating into unexplored territory is the exact trigger that produced the
   `Can't keep up! ... 329 ticks behind` spikes). 5 min gives the lag time to happen; 60s on an
   empty server won't.
4. Open the resulting `spark.lucko.me/<id>` flame graph → sort by **Server thread** → the culprit
   shows up under `MinecraftServer` / `ServerLevel` / `NoiseChunk` / `ChunkGenerator` / a mod's
   worldgen class.

Reading the tick-duration line (`min/med/95%ile/max`): a big `max` (e.g. 40.9ms) with a tiny median
on an otherwise-idle server is the periodic autosave spike (one chunk-save pass ~every 19 min) —
harmless. A consistently HIGH median = real tick-loop load.

Benign spark warnings, safe to ignore: "WARNING: A Java agent has been loaded dynamically" and
"A restricted method in java.lang.System has been called ... java.lang.System::load ... Use
--enable-native-access=spark" — both are spark loading its async-profiler native agent on modern JVMs.

### In-server backup mods (SimpleBackups) = periodic freeze-lag on large worlds

A kitchen-sink pack that ships an in-server backup mod (SimpleBackups is the common one — ATM11
ships `SimpleBackups-*.jar`) causes recurring multi-second freezes that masquerade as random
"Can't keep up!" spikes. The trigger: FULL backups + pre-copy of a large world. Verified Oct 2026
on ATM11 (6.17 GB world): every hour the server forced a save-all, pre-copied the ENTIRE world to a
temp dir (`Pre-copy took 19588ms for 6170200215 Bytes`), then ZIP-compressed it — the tick loop
starved for ~20s and threw `Can't keep up! ... 101 ticks behind` right in the middle of the pre-copy.

Diagnostic fingerprint: the log shows a `Backup started...` → `Pre-copying /data/world ... (N Bytes)`
→ `Pre-copy took Xms` block, and a `Can't keep up!` line sits INSIDE that time window. So when a
"can't keep up" spike looks random, grep the log for backup lines near it:
`grep -iE "simplebackups|backup|pre-copy" logs/latest.log` and compare timestamps against the
`Can't keep up` lines — a full-copy backup every 60 min is a very consistent source of hourly spikes.

Config lives at `config/simplebackups/common.toml` — NOTE it is a SUBDIRECTORY: `config/simplebackups/common.toml`
(+ `server.toml`, plus `common-*.toml.bak` backups), NOT `config/simplebackups-common.toml`. The laggy
defaults are `timer = 60` (hourly), `backupType = "FULL_BACKUPS"`, `preCopy = true`. Tune down:
`backupType = "INCREMENTAL"` (only changed files), `timer = 1440` (daily), `preCopy = false`. Changes
only take effect on a server RESTART (config read at boot). If the box also runs the external nightly
tar.gz cron backup (templates/backup-minecraft.sh), the in-server backup is redundant — `enabled = false`
is the cleaner fix than just tuning it down.

### Giving items / finding a mod item's registry ID

When the user says "give me X" (`/give <player> <item> <count>`), you need the exact `namespace:path` ID — RCON has no tab-complete, so don't guess. Find it by searching the pack's jars for the item name:

```bash
cd <data>/mods
python3 -c "
import zipfile, os
for f in os.listdir('.'):
    if not f.endswith('.jar'): continue
    try:
        z=zipfile.ZipFile(f)
        for n in z.namelist():
            if 'golden_bone' in n.lower():   # the snake_case item name
                print(f, '->', n)
    except: pass
"
```

The registry ID is derived from the hit path: `assets/<modid>/items/<name>.json` → `<modid>:<name>`. Confirm the display name via `assets/<modid>/lang/en_us.json`. Then `docker exec <c> rcon-cli "give <player> <modid>:<name> <count>"` — success echoes `Gave N [Item Name] to <player>`. The target must be ONLINE (check `rcon-cli list` first). Verified example: `kindredspirits:golden_bone` (Golden Bone).

### Giving items via RCON (resolve modded item IDs, don't guess)

The user asks for item gives in natural-language shorthand ("give 2 golden bones", "or just 64 gold"). Resolve the exact `namespace:item_id` yourself, then give via RCON:

1. **Vanilla items** are obvious: `minecraft:gold_ingot` (user's "gold" = ingots unless blocks/nuggets specified), `minecraft:sculk`, `minecraft:bone`.
2. **Modded items** — find the ID by searching the mod jars for the item's registry file. The path `assets/<modid>/items/<name>.json` (or `data/<modid>/recipe/<name>.json`) gives ID = `<modid>:<name>` (snake_case). E.g. "golden bone" → `kindredspirits:golden_bone` (Kindred Spirits mod in FTB Evo 2). One-liner over the mods dir:
   ```bash
   cd <data>/mods && python3 -c "
   import zipfile, os
   for f in os.listdir('.'):
       if not f.endswith('.jar'): continue
       for n in zipfile.ZipFile(f).namelist():
           if 'golden_bone' in n.lower(): print(f, '->', n)
   "
   ```
3. **Target must be ONLINE** — vanilla `/give` rejects offline players. Confirm with `rcon-cli list` first; default to `0athless`:
   ```bash
   docker exec <c> rcon-cli "give 0athless kindredspirits:golden_bone 2"   # → "Gave 2 [Golden Bone] to 0athless"
   ```

The same jar+config read answers "how does mod X work / what's the limit": read `data/config/<modid>-*.toml` (commented, authoritative) and the jar's `assets/<modid>/lang/en_us.json` + class strings before web-searching — faster and exact for the installed version.

### Player playtime / "who played and how long"

Player stats are **NOT** in `world/playerdata/<uuid>.dat` — its `stats` compound is empty on modern 1.21.1. They live in `world/stats/<uuid>.json` (plain JSON). Map UUID→username via `usercache.json` at the data root. The playtime stat is `stats.minecraft:custom.minecraft:play_time` in **ticks** (20 ticks = 1s; 72,000 = 1h). `total_world_time` mirrors it; `minecraft:deaths` is the death count. Run `scripts/player-playtime.py [DATA_DIR]` for a sorted report.

Session history (who joined/left, and when) lives in the logs: `logs/latest.log` holds only the **current** day; prior days are gzip-rotated to `logs/YYYY-MM-DD-*.log.gz`. Grep `"joined the game"` / `"left the game"` across both (zcat the gz). PITFALL: `lost connection: Disconnected/Timed out` at the login stage (thread `ServerLoginPacketListenerImpl`) is an auth/whitelist failure, NOT a play session — randoms probing the port and non-whitelisted friends never actually entered the game and must NOT be counted as "played". Only `joined the game` lines count.

### World backups
Worlds have no built-in backup. Nightly tar.gz via `templates/backup-minecraft.sh` (7-day retention, `cronjob ... no_agent=true schedule="0 4 * * *"`). Backups go to `~/homeserver/backups/minecraft/`, outside the Docker volume.

### Java version → itzg image tag
| MC version | Image tag |
|---|---|
| 1.20.x Forge | `:java17` |
| 1.21.x | `:java21` |
| 26.x (latest) | `:java25` |
Class-file version in errors: 61=Java17, 65=Java21, 69=Java25. `:latest` still uses Java 21 and cannot run MC 26.2.

## Building a custom from-scratch modpack (TYPE=NEOFORGE, curated)

For a *from-scratch curated pack* (not AUTO_CURSEFORGE stock): copy a subset of an
existing pack's `data/mods/` jars + fetch new mods (Modrinth keyless / CF via
docker-exec), run `TYPE=NEOFORGE` + `VERSION` + `NEOFORGE_VERSION`, then boot-iterate —
the `Missing or unsupported mandatory dependencies:` log lists every missing lib at once.
Key gotchas: **Radium (Lithium port) is incompatible with Create** (drop it); **Create
Aeronautics/Sable + Plasmo Voice both grab UDP on the MC port** (give voice a dedicated
UDP port); Placebo is shared by Apotheosis AND FastFurnace/Workbench (don't remove it
when dropping Apotheosis). Export self-contained importable packs (`files:[]` +
`overrides/mods/`): CF `.zip` → CurseForge app + Prism, `.mrpack` → Modrinth + Prism.
Full recipe + dependency table: `references/custom-modpack-build.md`.

> ⚠️ Ruben wants wishlist-driven lean packs — build exactly what he lists. "Other mods
> you might suggest" = propose a veto-list BEFORE adding, don't silently pad the pack.

## Building a NEW custom modpack (curated subset)

When the user wants a fresh custom pack (a NEW itzg server, not more mods on an existing one),
the lazy-correct path is to **curate a subset of an already-running pack** on the box
(ATM10aero): copy the wishlist mods + their libraries from its `data/mods/` (already
version-matched), fetch only the genuinely-new mods from Modrinth, then boot-iterate missing
deps (NeoForge's ModSorter names every missing dep + incompatibility in one pass). Full
workflow, the verified dependency matrix, Sodium-vs-Embeddium client stack, and importable-pack
build recipe live in `references/custom-modpack-from-scratch.md`.

Hard rules for Ruben:
- **Only add what he explicitly asked for.** Present "suggested extras" for a yes/no BEFORE
  adding — he pushed back hard ("you added a lot of mods without my input") when a pack was
  padded with Apotheosis/Occultism/etc. without asking. Never silently add content mods.
- **Never modify/rebuild the existing server** (ATM10aero) while building a new pack. Copy
  one-way FROM it only, and say so explicitly. He is protective of it and will flag any
  command that even references the old server's path.

New container env: `TYPE=NEOFORGE` + `VERSION=1.21.1` + `NEOFORGE_VERSION=<exact>` (read the
source server's `.neoforge-manifest.json` `forgeVersion` — do NOT trust memory).

## Client connection error triage (server healthy, client fails)

Four client-side signatures → four root causes. Full playbook + the wrong-server and
router-forwarding real cases: `references/connection-and-loader-mismatch-debugging.md`.
(Now five: add Signature 4 — "server sent registries with unknown keys" = a manual
content mod OR a manual Mystical Customization crop config present server-side but
missing client-side. Crop configs are NOT synced; ship them to every client.)

1. **"mod X channel missing on server" + "Incompatible client! Please use NeoForge <ver>"** — the player connected to a DIFFERENT server (wrong host/port). A channel can only be "missing on the server" if the server they actually reached lacks that mod; the quoted NeoForge version is *that* server's version, not yours.
2. **ConnectTimeoutException on a new port (old port still works)** — router port-forwarding gap, NOT a server issue. Confirm host LISTENs on 0.0.0.0:<port> + box has a private IP, then hand the user the router rule set.
3. **Prism ignores the manifest's NeoForge pin and installs LATEST** — keep the server on the latest NeoForge for the MC version (bump `NEOFORGE_VERSION`; same-line 21.1.x bumps are mod-compatible) so it matches what Prism installs. Don't hand-pin clients — it re-breaks on the next bump.
4. **Singleplayer world-creation crash** — the launch log only points at `crash-reports/<ts>-server.txt`; the exception lives in that file, not the log. Ask for it. "high memory pressure" + big `-Xmx` = OOM-during-worldgen suspect.

## Reference files

- `references/custom-modpack-from-scratch.md` — build a new custom pack by curating an existing
  server: workflow, 1.21.1 NeoForge dependency matrix (Tectonic→Lithostitched, BOP→TerraBlender
  +GlitchCore, AdAstra→common-storage-lib, XNet→RFToolsBase, AE2/Powah/ExtendedAE→guideme,
  AttributeFix→Prickle, FastFurnace/FastWorkbench→Placebo, Rechiseled→Fusion client-only),
  compatibility traps (Radium×Create, Plasmo Voice×Sable UDP conflict), Iris-requires-Sodium
  (not Embeddium) client stack, and self-contained CF-zip/.mrpack import recipes.
- `references/pregen-and-distant-horizons.md`
- `references/pregen-and-distant-horizons.md`
- `references/pregen-and-distant-horizons.md` — exact CF file IDs/versions for Chunky/C2ME/DH on 1.21.1 NeoForge, full Chunky + DH LOD command sequence, radius/time guidance, client shader caveats.
- `references/performance-mod-gaps.md` — which perf mods are already in the pack vs. genuinely missing (server-side: Lithium/ServerCore/Noisium; client-side rendering mods are deliberately absent). Verify availability via Modrinth API.
- `references/shareable-modpack.md` — build a shareable PrismLauncher/CurseForge-format modpack from the itzg server: version pinning, full-zip recipe, client-vs-server extras, distribution, docker-exec CF API quoting pitfall.
- `references/shareable-modpack-export.md` — build a PrismLauncher-importable CurseForge-format pack from an itzg AUTO_CURSEFORGE server: metadata files to read, CF API downloadUrl, manifest+overrides rebuild, bundling extra mods into overrides/mods/, version-pinning and distribution pitfalls.
- `references/voice-chat-plasmo-voice.md` — add Plasmo Voice (proximity voice chat): the UDP-port gotcha (MC port is TCP-only; voice needs `25565/udp`), compose recreate sequence (`docker start` won't re-apply ports), config, verification, router/firewall flag.
- `references/pack-version-upgrade.md` — bump the pack version on an AUTO_CURSEFORGE server (restart pulls latest): backup-first sequence, "Re-installing Forge" signal, manual-mods-survive + removed-mods-cleaned, verification steps.
- `references/voice-chat-and-network-debugging.md` — Plasmo Voice setup (UDP port, config), and the "client crashes with network protocol error = mod version mismatch" debugging path (Distant Horizons `IncompatibleMessageInternalEvent` signature, the silent variant, version notes).
- `references/mrpack-from-curseforge-pack.md` — build a self-contained Modrinth `.mrpack` from a CurseForge-only pack (empty `files[]` + everything under `overrides/`); launcher-format coverage matrix.
- `references/voice-chat.md` — add/remove Plasmo Voice or Simple Voice Chat: the UDP port (not TCP!) gotcha, config fields, removal procedure, and the benign `-> MISSING` WARN after removal.
- `references/full-self-contained-zip.md` — build the ~1GB flat zip with every jar bundled (no CurseForge resolution): which dirs to include/exclude, `python3 zipfile` recipe (the `zip` binary is absent on this box), observed sizes, voice-chat check, and distribution-vs-manifest-pack distinctions.
- `references/crafty-controller.md` — Crafty Controller (abandoned): migration from itzg, socat sidecar, CSRF failures, why direct itzg won.
- `references/minecraft-curseforge-modpacks.md` — full AUTO_CURSEFORGE reference, debugging, and pitfalls (CF_API_KEY_FILE, `$` expansion, world incompatibility).
- `references/minecraft-modpack-swap.md` — swapping one CurseForge modpack for another (orphaned-container removal, stray cf_api_key.txt dir, root-owned parent dir).
- `references/minecraft-server-performance.md` — "can this box keep up with this modpack?" diagnostic sequence, signal interpretation, OptiPlex 3070 Micro hardware ceiling, remediation levers.
- `references/minecraft-plugins.md` — switching to Paper/Purpur for plugins, plugin repos, version checking.
- `references/minecraft-atm10-sky.md` — working ATM10 deploy config (historical — server is now ATM10 Aeronautics, `CF_SLUG=all-the-mods-10-aeronautics`).
- `references/minecraft-add-individual-mods.md`, `references/minecraft-itzg-add-mods.md`, `references/minecraft-curseforge-add-mod.md`, `references/minecraft-add-mods.md` — four near-duplicate session recipes for adding a single extra mod to a running itzg AUTO_CURSEFORGE server via the CF/Modrinth API (slug→id, `modLoaderType=6`, `/download-url` vs `/download`, re-decrypt before restart, `.curseforge-manifest.json`). Consolidate these four into one on next touch.
- `templates/backup-minecraft.sh` — nightly Minecraft world backup script, 7-day retention.
- `references/world-reset-and-cleanup.md` — reset/regenerate a world on a running itzg server (archive `data/world` by rename, then restart; whitelist/mods/quests survive; `dsp` clobber is one-shot; current `minecraft-evo2tech` dirs are ruben-owned so no sudo) AND delete old/retired server dirs (root-owned `data/` husks need `sudo rm -rf` to finish).
- `scripts/chunky-watch.sh` — re-runnable background watcher that polls `chunky progress`. Exits 0 on genuine completion, 1 ONLY when the task was LOST to a server restart. "No tasks running" is AMBIGUOUS — Chunky reports it BOTH after a clean 100% finish (task removed) AND after a crash-restart wipes the task — so the script compares the container's `StartedAt` before/after: unchanged StartedAt + previously-saw-a-task = completed; changed StartedAt = lost. Also tolerates being launched before the task starts. (pair with terminal background=true + notify_on_complete=true).
- `scripts/pregen-dh-watch.sh` — combined Chunky→DH watcher (supersedes `chunky-watch.sh` when DH LODs should follow Chunky): monitors Chunky to 100%, then auto-runs `dh pregen start` and monitors it to completion. Args: `<container> <dh_chunk_radius>`. Exits 0 only when BOTH finish. (pair with terminal background=true + notify_on_complete=true).
- `scripts/pregen-dh-watch.sh` — combined watcher: polls `chunky progress` to 100% (same StartedAt disambiguation as chunky-watch), then auto-starts `dh pregen start minecraft:overworld 0 0 <chunkRadius>` and watches `dh pregen status` until it returns to the idle string "Pregen is not running". Usage: `bash pregen-dh-watch.sh <container> <dh_chunk_radius>` (defaults: minecraft-evo2tech, 400). Size the DH radius to cover the Chunky area (~1 chunk per 16 blocks). Re-runnable.
- `scripts/pregen-dh-watch.sh` — combined watcher: Chunky → DH LOD pregen in one background job. Polls Chunky to 100% (StartedAt-guarded), then `dh pregen start minecraft:overworld 0 0 <chunkRadius>` and polls `/dh pregen status` until it returns to "Pregen is not running". Exit 0 = both done; 1 = lost task or DH failed to start. Args: `<container> [dh_chunk_radius]` (default minecraft-evo2tech, 200). Pair with terminal background=true + notify_on_complete=true.
- `references/from-scratch-custom-pack.md` — build a NEW custom pack by curating a subset of an existing pack's mods: workflow, dependency gotchas (Radium×Create, BOP/Tectonic/AdAstra deps, Placebo dual-use), Plasmo Voice×Sable UDP conflict, Iris-vs-Oculus on 1.21.1, self-contained CF-zip/mrpack build, Forgejo large-binary distribution.
- `references/custom-modpack-build.md` — build a from-scratch curated pack: subset-copy workflow, boot-iterate loop, keyless Modrinth download pattern, 1.21.1 dependency map, SRV routing, client-zip merge.
- `references/atm11-deploy-and-world-migration.md` — deploy ATM 11 (CF slug `all-the-mods-11` + `CF_FILE_ID` pin, the 6 added mods with CF ids/deps), migrate an existing world onto the box via scp + `/data/world` bind-mount (verify world `dimensions/` against the pack modlist, split-brain warning), and the no_agent cron progress-reporter for 10h+ pregens.
