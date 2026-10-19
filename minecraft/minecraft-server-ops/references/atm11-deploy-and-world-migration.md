# ATM 11 deploy + migrating a world onto the homelab (verified Oct 2026)

## ATM 11 identity
- CF slug `all-the-mods-11`, project id **1148445**. "Super early alpha for 26.1.2" — updates fast, so PIN it.
- MC 26.1.2, NeoForge **26.1.2.109** (manifest pin), ~293 mods, ~117 MB zip.
- Latest at deploy: `All the Mods 11-0.12.0-beta` = CF file id **9187064**.
- Authoritative NAMED mod list: GitHub `AllTheMods/ATM-11` → `config/crash_assistant/modlist.json`
  (285 entries; has a UTF-8 BOM — parse with `encoding='utf-8-sig'`). Much faster than resolving
  293 CF project IDs from `manifest.json` (which is `{projectID, fileID}` pairs, no names).

## Deploy recipe (AUTO_CURSEFORGE, pinned)
```yaml
image: itzg/minecraft-server:java25
environment:
  TYPE: AUTO_CURSEFORGE
  CF_API_KEY_FILE: /run/secrets/cf_api_key      # avoids $ expansion; mount the key file :ro
  CF_SLUG: all-the-mods-11
  CF_FILE_ID: "9187064"                         # pin — alpha auto-update on restart would break the world
  MEMORY: 12G
volumes:
  - ./minecraft-atm11/data:/data
  - ./secrets/cf_api_key.txt:/run/secrets/cf_api_key:ro
  - /home/ruben/atm11-world:/data/world         # migrated world (below)
```

## Added mods (none in ATM 11 — verified vs manifest + GitHub modlist)
| mod | CF id | jar | required deps (in ATM 11?) |
|---|---|---|---|
| Hephaestus Forge | 1542467 | hephaestus-neoforge-26.1.2-1.0.17.jar | Athena ✓ |
| Hephaestus Tools | 1725286 | hephaestus_tools-neoforge-26.1.2-1.0.8.jar | PlayerAnimationLib ✗ (add) + Hephaestus Forge (optional) |
| Player Animation Library | 1283899 | PlayerAnimationLibMerged-1.2.8+mc.26.1.jar | — |
| Nautec 2 | 1727082 | nautec-26.1.2-NeoForge-2.0.14.jar | GeckoLib ✓, Curios ✓ |
| Chunky | — | Chunky-NeoForge-1.5.4.jar | — |
| C2ME | — | c2me-neoforge-mc26.1.2-0.4.0-alpha.0.100.jar | — |

**Naming trap:** "Hephaestus Forge" (titammods, id 1542467, metalworking) ≠ "Hephaestus"/"Hephaestus
Fabric" (thatguynamedalpha — Tinkers' *Fabric* port, won't load on NeoForge) ≠ "The Forge of
Hephaestus" (Greek-myth mod). Resolve by exact slug/CF id, never fuzzy name.

## Migrating an existing world (bind-mount, don't copy)
- World was scp'd off the remote Pterodactyl ATM server: `scp -r ...\world ruben@<homelab>:~/atm11-world`,
  then bind-mounted `~/atm11-world:/data/world`. `level-name` stays `world` (default) → resolves to the mount.
- **Verify the world's mod set matches the pack before trusting it.** List `~/atm11-world/dimensions/` —
  each folder is a dimension-defining mod (e.g. `thaumaturge`, `allthemodium`, `aether_ii`, `witchery`,
  `stellaris`, `undergarden`, `neovitae`, `mahoutsukai`). Grep those against the pack's `modlist.json`.
  All present = clean load. (ATM 11 ships Thaumaturge + Applied Thaumaturge.)
- **Split-brain warning:** the migrated world is still live on the remote — user must stop the remote
  before anyone connects here, or progress is lost. Can't be done from the homelab.
- First pregen SKIPS already-generated chunks at ~13k cps before settling to the real rate — don't trust
  the first `chunky progress` reading.

## Progress-reporter cron (no_agent) for 10h+ pregens
A `terminal(background=true)` watcher can be reaped over multi-hour runs. More robust: `cronjob
no_agent=true` running a single-shot script every 30m (`~/.hermes/scripts/minecraft-pregen-check.sh`)
that prints a progress line each tick (latest `Processed: N chunks (X%), ETA, Rate` from
`docker logs --tail 200`) plus one-shot alerts: completion (`[Chunky] Task finished for
minecraft:overworld` in the log), C2ME thread explosion (`docker stats PIDS > 1000`), frozen
(Processed unchanged across two ticks via a state file). A marker file suppresses duplicate
completion pings; empty stdout elsewhere = silent.
