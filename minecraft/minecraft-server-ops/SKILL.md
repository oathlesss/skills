---
name: minecraft-server-ops
category: minecraft
description: "Administer a self-hosted Minecraft server (itzg docker-minecraft-server on a homelab box): assess whether hardware can handle a modpack, tune performance, pre-generate the world, manage Distant Horizons LODs, and add/remove mods on an AUTO_CURSEFORGE container. Trigger on server performance questions, 'can my server run this pack', pregen, world generation, Distant Horizons, or mod-management requests."
---

# Minecraft Server Operations

Operational knowledge for running Ruben's self-hosted Minecraft server(s) on the
OptiPlex homelab. The primary instance is ATM10 Aeronautics (`minecraft-atm10aero`,
itzg/minecraft-server:java21, AUTO_CURSEFORGE, `CF_SLUG=all-the-mods-10-aeronautics`,
1.21.1 NeoForge 21.1.248, 10G RAM). Hardware: i5-9500T (6c/6t, 35W T-series),
30GB RAM, NVMe.

## Key facts / mental model

- **Minecraft's tick loop is single-threaded.** CPU single-core speed is the binding
  constraint, not RAM or core count. A low-power T-series chip with a `powersave`
  governor is the worst case for a heavy pack.
- **Heavy pack worldgen cost is invisible until players explore.** An empty world
  ticking at ~43% CPU with 0 players is the warning sign; the real cost hits when
  2+ players fly/dimension-hop and generate chunks.
- **Two different "pregen" tools, do not conflate them** (this was corrected explicitly):
  - **Chunky** pre-generates *real* chunks (blocks, ores, structures, mod worldgen) —
    this is what fixes "can't keep up" lag.
  - **Distant Horizons `/dh pregen`** generates *LODs* (simplified visual terrain) —
    cosmetic, does NOT reduce chunk-gen lag.
- **Distant Horizons is primarily a CLIENT mod.** The server-side jar exists only to
  pre-gen LODs shared across clients, and is CPU/RAM hungry — DH's own guidance says
  disable it server-side on modest boxes and let clients generate their own LODs.

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

## Pre-generation workflow (Chunky + C2ME, then DH LODs)

Order matters: **real chunks first, then DH LODs** (DH can build LODs from existing
chunks instead of re-worldgenning). Exact version numbers and the full command
sequence live in `references/pregen-and-distant-horizons.md` — read it before running
anything; version IDs drift across MC versions and must be verified against the CF API.

## Finding the exact MC + NeoForge version

Never guess the version when adding mods. Read it from the server's own state:

```bash
cat /home/ruben/homeserver/minecraft-atm10aero/data/version.json   # itzg ForgeManifest: minecraftVersion + forgeVersion
# or: docker exec minecraft-atm10aero cat /data/version.json
```

## Mod management on itzg AUTO_CURSEFORGE

The container re-syncs the modpack from CurseForge on start, but **manual jar drops into
`data/mods/` DO survive the sync** — confirmed empirically (AppliedFlux/AdvancedAE with
pre-start timestamps persisted across a restart). No `REMOVE_OLD_MODS` / `CURSEFORGE_PROJECTS`
env is set; plain jar drops just work. RCON is on port 25575:
`docker exec minecraft-atm10aero rcon-cli "<command>"`.

C2ME shows harmless `@Mixin target ... not found` WARNs for client-side classes (server
has no client) — expected, not a bug. Detect boot-complete via RCON `list` responding,
not via log grep.

## CurseForge API (for finding/downloading exact files)

- Needs an API key — already mounted in the container at `/run/secrets/cf_api_key`
  (from `CF_API_KEY_FILE`). Query it WITHOUT reading the secret yourself:
  `docker exec minecraft-atm10aero sh -c 'curl -s -H "x-api-key: $(cat /run/secrets/cf_api_key)" "https://api.curseforge.com/v1/mods/search?gameId=432&searchFilter=<slug>&classId=<id>"'`
- `classId`: 6 = mod, 12 = resource pack, 4471 = modpack.
- Files by project: `.../v1/mods/<id>/files?gameVersion=1.21.1`; download URL via
  `.../v1/mods/<id>/files/<fileId>` → `downloadUrl` (edge.forgecdn.net).
- Modrinth needs NO key and is easier for resource packs: `api.modrinth.com/v2/project/<slug>/version`.

## Pitfalls

- **Restart after `deploy.sh up` fails with `not a directory: ... cf_api_key.txt`.** `deploy.sh` decrypts SOPS secrets only for `up`, then CLEANS them up — so `docker compose restart minecraft-atm10aero` fails because the bind-mounted `cf_api_key.txt` is gone and Docker creates an empty *directory* in its place. Fix: (1) `sudo rmdir ~/homeserver/secrets/cf_api_key.txt` to remove the placeholder dir; (2) re-decrypt the secrets the container bind-mounts/env-files via `~/.local/bin/sops --decrypt ...` (don't read the values); (3) `docker start minecraft-atm10aero` (NOT `docker compose up -d` — the terminal tool flags that as a long-lived process and refuses; `docker start <name>` returns instantly).
- **Conflating DH pregen with world pregen** — DH LODs don't create real chunks. Chunky is the lag fix.
- **Watching boot logs: don't grep for "ERROR".** During mod loading, normal WARN lines contain the literal string `ERROR: No value present` (Moonlight / registry lookups). A crash-scan like `grep -iE "error|fatal|crash|caused by|failed to start"` false-positives on those. Detect boot-complete via the `Done (Ns)!` line or RCON actually responding (`rcon-cli list`); detect real crashes via `FATAL`, `This crash report`, or `A fatal error`. Also: `docker logs` is the *full history*, so `grep -c "Done"` can match a prior boot — confirm the current boot via RCON, not log grep.
- **Installing DH server-side on a small box** — wasteful; keep DH client-only, pregen LODs per-client.
- **Background watcher scripts: `exec >>log 2>&1` triggers false "completed" notifications.** A `terminal(background=true, notify_on_complete=true)` process gets reported as `exit code None` ~30s in if the script redirects stdout with `exec` — that closes the pipe the process manager watches. Use `log() { echo "$*" | tee -a "$LOG"; }` and keep the pipe open. Also: `docker logs` is the *full history*, so a completion grep can match a prior boot — poll for a fresh signal (RCON `list` returning `players online`) instead.
- **Long pregen watchers can get orphaned/reaped while sleeping.** A `sleep 300` polling loop may be reported dead even when the target task (Chunky, running *inside* the server process) is fine. Design the watcher to be re-runnable: killing and relaunching it loses nothing because the actual task lives in the server, not the watcher.
- **"No 'can't keep up' yet = fine"** — a fresh 5MB world proves nothing; stress only shows after exploration.
- **Trusting a modpack's bundled perf mods** — verify they actually load (servercore/ferrite present ≠ tuned).

## Reference files

- `references/pregen-and-distant-horizons.md` — exact CF file IDs/versions for Chunky/C2ME/DH on 1.21.1 NeoForge, full Chunky + DH LOD command sequence, radius/time guidance, client shader caveats.
