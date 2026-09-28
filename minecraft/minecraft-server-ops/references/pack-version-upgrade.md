# Upgrading the pack version on an itzg AUTO_CURSEFORGE server

When the pack author ships a new release (e.g. ATM10 Aeronautics 0.5.1 → 0.6.1), the running
container does NOT auto-update. But compose has `CF_SLUG` + `MOD_PLATFORM=AUTO_CURSEFORGE` and
NO `CF_VERSION`/`CF_FILE_ID` pin, so the next restart pulls the LATEST pack automatically.

## Procedure (backup-first)

1. Read the changelog first so you know the blast radius:
   `.../v1/mods/<modId>/files/<fileId>/changelog` (see SKILL.md CF API section). Note the NeoForge
   bump — a loader version change (e.g. 21.1.248 → 21.1.250) means the installer re-runs.
2. `docker stop -t 120 minecraft-atm10aero` — graceful save+shutdown (120s timeout; a 400-mod
   pack can take >10s to stop cleanly).
3. Back up world + configs BEFORE the bump (world was 2.3 GB here):
   ```bash
   cd <data> && tar cf ~/mc-backups/atm10aero-preNNN-$(date +%Y%m%d-%H%M%S).tar \
     world config kubejs defaultconfigs datapacks \
     whitelist.json ops.json banned-players.json banned-ips.json server.properties
   ```
4. `docker start minecraft-atm10aero` → mc-image-helper re-syncs. Key log lines:
   `Re-installing Forge due to version change from ... 21.1.248 to ... 21.1.250`, then the
   NeoForge installer runs, then new mods download and removed mods are dropped.
5. Verify the bump landed (do NOT trust `Done` in `docker logs` — it's full history, can match a
   prior boot):
   - RCON `list` responds (boot-complete).
   - `.install-curseforge.env` `MODPACK_VERSION` == target.
   - `.neoforge-manifest.json` `forgeVersion` == target.

## What survives / what gets cleaned (verified 0.5.1 → 0.6.1)

- **Manual jars SURVIVE a version bump** (no `REMOVE_OLD_MODS` set): AppliedFlux, advancedae_addon,
  Chunky, C2ME, Distant Horizons all persisted.
- **itzg cleans up mods REMOVED by the new pack**: the 5 mods dropped in 0.6.0 were gone afterward —
  zero stale jars. Final count = pack mods + manual mods exactly.
- Confirm with the delta diff in SKILL.md ("Which mods did I add manually"): `STALE` and `MISSING`
  should both be empty.
- Re-verify manual mods against the new loader version. 248 → 250 is same-minor (safe). A major
  loader bump warrants re-checking each manual jar's compat.

## After the bump

Rebuild the shareable pack to match (see `references/shareable-modpack.md`) or friends get a
mod-mismatch. New content mods (Create:Aero Mekanism Compatibility, Ars Sable) go on BOTH server
+ client pack; client-only QoL (Jade Sable Compat) goes client-only.
