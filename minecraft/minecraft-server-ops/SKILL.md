---
name: minecraft-server-ops
category: minecraft
description: "Administer a self-hosted Minecraft server (itzg docker-minecraft-server on a homelab box): assess whether hardware can handle a modpack, tune performance, pre-generate the world, manage Distant Horizons LODs, add/remove mods on an AUTO_CURSEFORGE container, add voice chat (Plasmo Voice) with its UDP port, and export the pack as an importable CurseForge .zip or Modrinth .mrpack. Trigger on server performance questions, 'can my server run this pack', pregen, world generation, Distant Horizons, mod-management requests, voice chat setup, or 'make the pack importable'."
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
env is set; plain jar drops just work. RCON is on port 25575:
`docker exec minecraft-atm10aero rcon-cli "<command>"`.

C2ME shows harmless `@Mixin target ... not found` WARNs for client-side classes (server
has no client) — expected, not a bug. Detect boot-complete via RCON `list` responding,
not via log grep.

## Exporting a shareable PrismLauncher/CurseForge modpack

To hand friends an importable modpack matching the server, don't rebuild from scratch:
the official pack is already on CurseForge, so the pack = pinned version + the few
manually-added mods. Full workflow (read itzg metadata files, fetch the official zip via
the CF API, extract manifest.json + modlist.html + overrides/, bundle extra mods into
`overrides/mods/`, re-zip) lives in `references/shareable-modpack-export.md`. Key gotchas:
friends MUST install the server's exact CF version (CF shows a newer "latest" → mod
mismatch), content-mod extras need a client match while Chunky/C2ME/DH-server are
server-side-only, and the ~100MB pack zip exceeds Discord's 25MB limit (distribute via
Forgejo release / Caddy, or just send the tiny client-required jars).

## Building a shareable PrismLauncher modpack for players

To hand friends a one-import file with the server's exact mod set, see
`references/shareable-modpack.md`. Key facts: the pack is already public on CurseForge, so
"our own" pack = pinned official version + client-required manual jars bundled in
`overrides/mods/`; always pin the EXACT server version (CF "latest" drifts — server 0.5.1 vs CF
0.6.1 caused the mismatch risk). Full build recipe + the ~100 MB distribution problem + the
docker-exec CF API quoting pitfall are in the reference.

## CurseForge API (for finding/downloading exact files)

- Needs an API key — already mounted in the container at `/run/secrets/cf_api_key`
  (from `CF_API_KEY_FILE`). Query it WITHOUT reading the secret yourself:
  `docker exec minecraft-atm10aero sh -c 'curl -s -H "x-api-key: $(cat /run/secrets/cf_api_key)" "https://api.curseforge.com/v1/mods/search?gameId=432&searchFilter=<slug>&classId=<id>"'`
- `classId`: 6 = mod, 12 = resource pack, 4471 = modpack. ALWAYS pass `classId=6` when searching
  a mod — slug search is fuzzy and otherwise returns a wall of unrelated modpacks (e.g.
  `searchFilter=ars-sable` matched ~50 packs). If the exact slug still doesn't surface, retry
  space-separated (`ars sable`) or check Modrinth.
- Files by project: `.../v1/mods/<id>/files?gameVersion=1.21.1`; download URL via
  `.../v1/mods/<id>/files/<fileId>` → `downloadUrl` (edge.forgecdn.net).
- **Changelog:** `.../v1/mods/<id>/files/<fileId>/changelog` → `{"data":"<html>"}` (strip `<br>`/tags,
  html.unescape). The file-detail endpoint does NOT include the changelog. Use it to diff pack
  versions (e.g. 0.5.1 → 0.6.1). (The pack's GitHub `CHANGELOG.md` is usually a stub.)
- The CF *website* blocks curl/web_extract (Cloudflare challenge, ~5 KB stub). Go via the API
  (key required) or the pack's GitHub repo (`raw.githubusercontent.com/AllTheMods/ATM-10-a/...`
  mirrors config/kubejs + CHANGELOG.md; the mod-suggestion list lives in issue #1).
- Modrinth needs NO key and is easier for resource packs: `api.modrinth.com/v2/project/<slug>/version`.

## Pitfalls

- **Restart after `deploy.sh up` fails with `not a directory: ... cf_api_key.txt`.** `deploy.sh` decrypts SOPS secrets only for `up`, then CLEANS them up — so `docker compose restart minecraft-atm10aero` fails because the bind-mounted `cf_api_key.txt` is gone and Docker creates an empty *directory* in its place. Fix: (1) `sudo rmdir ~/homeserver/secrets/cf_api_key.txt` to remove the placeholder dir; (2) re-decrypt the secrets the container bind-mounts/env-files via `~/.local/bin/sops --decrypt ...` (don't read the values); (3) `docker start minecraft-atm10aero` (NOT `docker compose up -d` — the terminal tool flags that as a long-lived process and refuses; `docker start <name>` returns instantly).
- **Conflating DH pregen with world pregen** — DH LODs don't create real chunks. Chunky is the lag fix.
- **Watching boot logs: don't grep for "ERROR".** During mod loading, normal WARN lines contain the literal string `ERROR: No value present` (Moonlight / registry lookups). A crash-scan like `grep -iE "error|fatal|crash|caused by|failed to start"` false-positives on those. Detect boot-complete via the `Done (Ns)!` line or RCON actually responding (`rcon-cli list`); detect real crashes via `FATAL`, `This crash report`, or `A fatal error`. Also: `docker logs` is the *full history*, so `grep -c "Done"` can match a prior boot — confirm the current boot via RCON, not log grep.
- **Installing DH server-side on a small box** — wasteful; keep DH client-only, pregen LODs per-client.
- **Background watcher scripts: `exec >>log 2>&1` triggers false "completed" notifications.** A `terminal(background=true, notify_on_complete=true)` process gets reported as `exit code None` ~30s in if the script redirects stdout with `exec` — that closes the pipe the process manager watches. Use `log() { echo "$*" | tee -a "$LOG"; }` and keep the pipe open. Also: `docker logs` is the *full history*, so a completion grep can match a prior boot — poll for a fresh signal (RCON `list` returning `players online`) instead.
- **Long pregen watchers can get orphaned/reaped while sleeping.** A `sleep 300` polling loop may be reported dead even when the target task (Chunky, running *inside* the server process) is fine. Design the watcher to be re-runnable: killing and relaunching it loses nothing because the actual task lives in the server, not the watcher.
- **"No 'can't keep up' yet = fine"** — a fresh 5MB world proves nothing; stress only shows after exploration.
- **Recreating a container after a compose change (ports/env/volumes):** `docker compose up -d` is
  refused by the terminal tool (long-lived-process guard). And `docker start <name>` does NOT apply
  config changes — it just restarts the existing container. To apply a compose edit (e.g. adding or
  removing a UDP port mapping), recreate without the `up` keyword — all three return instantly:
  `docker rm -f <name> && docker compose create <name> && docker start <name>`. Data volumes persist
  across the rm/create (AUTO_CURSEFORGE re-syncs mods on boot; manual jar drops survive).
- **Removing a mod leaves a benign `modid (version X -> MISSING)` WARN** in the boot log under
  "version differences that were not resolved". It's NeoForge noticing the mod-list delta between
  boots — harmless, clears next boot. Don't chase it; confirm removal via `find /data -iname '*modname*'`
  (empty) + mod-count, not by grepping the log.
- **Trusting a modpack's bundled perf mods** — verify they actually load (servercore/ferrite present ≠ tuned).

## Reference files

- `references/pregen-and-distant-horizons.md` — exact CF file IDs/versions for Chunky/C2ME/DH on 1.21.1 NeoForge, full Chunky + DH LOD command sequence, radius/time guidance, client shader caveats.
- `references/shareable-modpack.md` — build a shareable PrismLauncher/CurseForge-format modpack from the itzg server: version pinning, full-zip recipe, client-vs-server extras, distribution, docker-exec CF API quoting pitfall.
- `references/shareable-modpack-export.md` — build a PrismLauncher-importable CurseForge-format pack from an itzg AUTO_CURSEFORGE server: metadata files to read, CF API downloadUrl, manifest+overrides rebuild, bundling extra mods into overrides/mods/, version-pinning and distribution pitfalls.
- `references/voice-chat-plasmo-voice.md` — add Plasmo Voice (proximity voice chat): the UDP-port gotcha (MC port is TCP-only; voice needs `25565/udp`), compose recreate sequence (`docker start` won't re-apply ports), config, verification, router/firewall flag.
- `references/pack-version-upgrade.md` — bump the pack version on an AUTO_CURSEFORGE server (restart pulls latest): backup-first sequence, "Re-installing Forge" signal, manual-mods-survive + removed-mods-cleaned, verification steps.
- `references/voice-chat.md` — add/remove Plasmo Voice or Simple Voice Chat: the UDP port (not TCP!) gotcha, config fields, removal procedure, and the benign `-> MISSING` WARN after removal.
- `references/full-self-contained-zip.md` — build the ~1GB flat zip with every jar bundled (no CurseForge resolution): which dirs to include/exclude, `python3 zipfile` recipe (the `zip` binary is absent on this box), observed sizes, voice-chat check, and distribution-vs-manifest-pack distinctions.
