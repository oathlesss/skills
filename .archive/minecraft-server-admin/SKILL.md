---
name: minecraft-server-admin
category: minecraft
description: "Administer a modded Minecraft server on the homelab (itzg Docker + AUTO_CURSEFORGE + NeoForge): add/remove mods, restart safely, pregenerate the world (Chunky + C2ME), set up Distant Horizons LODs, and monitor TPS via RCON/spark."
triggers:
  - "add a mod to the server"
  - "pregen or pregenerate the world"
  - "Distant Horizons server setup"
  - "restart the minecraft server"
  - "server can't keep up / lagging / TPS"
  - "how many mods does the server have"
  - "RCON or server.properties task on the homelab Minecraft server"
---

# Modded Minecraft Server Admin (homelab)

Administering the homelab Minecraft server. Current identity: **ATM10 Aeronautics** (not plain ATM10 — Ruben is firm on this distinction), MC 1.21.1, NeoForge, 400 mods, runs as `minecraft-atm10aero` container via itzg `minecraft-server:java21` with `MOD_PLATFORM: AUTO_CURSEFORGE` + `CF_SLUG: all-the-mods-10-aeronautics`. 10G RAM. i5-9500T (6c/6t) host — single-threaded tick loop is the bottleneck, not RAM.

## Finding the exact MC + NeoForge version

Never guess the version when adding mods. Read it from the server's own state:

```bash
cat /home/ruben/homeserver/minecraft-atm10aero/data/version.json   # itzg ForgeManifest: minecraftVersion + forgeVersion
# or: docker exec minecraft-atm10aero ...  /data/version.json
```

## CurseForge API (download mods / query versions) WITHOUT reading secrets

Ruben's rule: never read/decrypt secret files. But the CF API key is **already mounted inside the running container** at `/run/secrets/cf_api_key` — use it there via `docker exec`, which queries the API without ever printing the key value:

```bash
# search a mod (classId 6 = mod, 12 = texture/resource pack)
docker exec minecraft-atm10aero sh -c 'curl -s -H "x-api-key: $(cat /run/secrets/cf_api_key)" "https://api.curseforge.com/v1/mods/search?gameId=432&searchFilter=<name>&classId=6"'
# list files for a project filtered to a game version
docker exec minecraft-atm10aero sh -c 'curl -s -H "x-api-key: $(cat /run/secrets/cf_api_key)" "https://api.curseforge.com/v1/mods/<projectId>/files?gameVersion=1.21.1&pageSize=8"'
# a specific file (returns downloadUrl on edge.forgecdn.net + fileName)
docker exec minecraft-atm10aero sh -c 'curl -s -H "x-api-key: $(cat /run/secrets/cf_api_key)" "https://api.curseforge.com/v1/mods/<projectId>/files/<fileId>"'
```

The `downloadUrl` returned is a plain CDN URL (`https://edge.forgecdn.net/files/<a>/<b>/<file>.jar`) — curl it directly without auth. Always verify jar integrity after download: `python3 -c "import zipfile; z=zipfile.ZipFile(f); print('ok' if z.testzip() is None else 'corrupt')"`.

## Adding mods to an AUTO_CURSEFORGE server

Drop the `.jar` into `/home/ruben/homeserver/minecraft-atm10aero/data/mods/`. Manual jars **survive the AUTO_CURSEFORGE re-sync** (verified: AppliedFlux/AdvancedAE timestamps predate container start and persist). The itzg sync re-downloads the pack but does NOT wipe extra jars in `mods/`. No env change needed.

## ⚠️ Restarting the server: the deploy.sh secret-cleanup gotcha

This bit us hard and cost a fix round. `deploy.sh` decrypts SOPS secrets into `secrets/*.txt` only during `up`, then **cleans them up afterward**. So `cf_api_key.txt` (a bind-mount for the container) is normally ABSENT on disk. `docker compose restart minecraft-atm10aero` then fails:

```
OCI runtime create failed: error mounting .../secrets/cf_api_key.txt ... not a directory: Are you trying to mount a directory onto a file
```

Docker even creates an empty *directory* placeholder at that path, which then breaks subsequent decrypts ("Is a directory"). Correct restart sequence:

```bash
# 1. remove any empty placeholder dir docker may have created
sudo rmdir secrets/cf_api_key.txt 2>/dev/null || true
# 2. re-decrypt the secrets (sops), no value read
~/.local/bin/sops --decrypt secrets/cf_api_key.txt.sops > secrets/cf_api_key.txt && chmod 600 secrets/cf_api_key.txt
for s in mc.env tailscale.env zennotes.env; do
  ~/.local/bin/sops --input-type dotenv --output-type dotenv --decrypt secrets/$s.sops > secrets/$s && chmod 600 secrets/$s
done
# 3. start (docker start, NOT compose up -d, avoids the long-lived-process guard)
docker start minecraft-atm10aero
```

`docker start <name>` works because the container config is unchanged — only the bind-mount file was missing. Boot takes several minutes (400 mods); poll RCON until `rcon-cli list` returns "players online". Detect crashes with `docker logs ... | grep -E "FATAL|Encountered an error|Failed to start"` — but note many mod warnings contain the substring "ERROR", so grep for the specific fatal markers, not bare "ERROR".

## World pregeneration (Chunky + C2ME)

**Two DIFFERENT things — don't conflate:**
- **Chunky** = pre-generates REAL chunks (blocks, ores, structures, mod worldgen). This is what fixes exploration lag. Server-side only.
- **Distant Horizons** = renders far-away terrain as LODs (visual approximations). Primarily a CLIENT mod. Server-side DH only pre-generates LODs to share with clients — it does NOT pregen real chunks.

Order matters: pregen real chunks FIRST (Chunky), then build DH LODs from the existing chunks (fast) rather than making DH do full worldgen (slow, duplicate work).

Mods to add (verified 1.21.1 NeoForge, Sept 2026): **Chunky-NeoForge** (CF project 485681, `Chunky-NeoForge-1.4.23.jar`) + **C2ME** (CF project 533097, `c2me-neoforge-mc1.21.1-0.4.0-alpha.0.120.jar`). C2ME parallelizes chunk gen across cores — the rate goes from ~7 cps to ~50 cps once warmed up.

Pregen sequence (via `docker exec minecraft-atm10aero rcon-cli "<cmd>"`):

```bash
chunky world minecraft:overworld
chunky spawn            # center = world spawn (or `chunky center <x> <z>`)
chunky radius 2000      # in BLOCKS (2000 blocks ≈ 125-chunk radius ≈ ~200k chunks ≈ hours on a 6-core box)
chunky start
chunky progress         # monitor % + ETA
chunky pause / continue / cancel
```

Note: this Chunky version has NO `chunky config threads` subcommand — threading is handled via C2ME. Radius is in **blocks** by default.

## Distant Horizons (client LOD rendering + optional server LOD pregen)

- **Clients** (each player's PC) install the DH jar to see distant terrain — DH is fundamentally a client mod.
- **Server-side DH is optional** and CPU/RAM hungry; the DH team's own guidance for modest servers is to let clients generate LODs locally and NOT run server-side DH. On the i5-9500T, server-side DH pregen is a heavy one-time cost.
- If server-side LODs ARE wanted, add `DistantHorizons-3.2.0-b-1.21.1-fabric-neoforge.jar` (CF project 508933, file 8389148 — the fabric/neoforge jar is a single combined file), then after boot:

```bash
dh config common.generationMode INTERNAL_SERVER
dh config common.threadPreset I_PAID_FOR_THE_WHOLE_CPU
dh pregen start minecraft:overworld 0 0 256    # radius in CHUNKS
dh pregen status
```

DH 3.x changed config key names between versions (`common.generationMode` vs `generation.mode`). Always dump `dh help` / `dh config` first and adapt — don't trust hardcoded keys. Also: ATM10 Aeronautics ships Iris + Sodium, and DH + Iris only works with DH-compatible shaders (per the DH mod page's list) — the #1 cause of "DH won't render / crashes" reports.

## TPS / health monitoring

- `docker exec minecraft-atm10aero rcon-cli "spark tps"` (spark is in the pack) — may return empty over RCON; fall back to `docker logs` for "can't keep up" warnings and `docker stats --no-stream` for CPU/RAM.
- During Chunky pregen the CPU pegs ~600% (all 6 cores); playing on the server at the same time will lag. Recommend running pregen overnight.

## Reference Files

- `references/pregen-commands.md` — exact command sequences + version pins from the ATM10 Aeronautics setup session (Chunky/C2ME/DH flows, RCON patterns, boot-wait loop).
