# World reset & old-server cleanup (itzg MC containers)

## Reset/regenerate a world on a running server (keep the modpack)

1. `docker stop <c>` (clean save).
2. Delete ONLY the world subfolder: `rm -rf <data>/world`. Keep mods/config/kubejs/datapacks.
3. `docker start <c>` — boot logs `No existing world data, creating new world`.
4. Verify: RCON `list` responds + FTB Quests logs `Loaded N chapter groups, M chapters, K quests`.

- **Whitelist survives** — `whitelist.json`, mods, configs, quests, datapacks all live OUTSIDE `world/`.
- On FTBA the `dsp` mod's server.properties clobber is **marker-gated (one-shot)**, so it does NOT
  re-clobber on a world reset (marker `/data/local/default-used.marker` already exists).
- The world gets a NEW random seed (unless `server.properties` pins `level-seed`). Verify Chunky is
  still present before pregenning: `ls <data>/mods | grep -i chunky`.

## Delete old/retired server dirs — root-owned dirs pitfall

Old itzg servers (e10, atm10aero, oathlesssp, vanilla, etc.) were written by the container running
as root, so their **top-level dir (and sometimes `data/`) is root-owned**. `rm -rf <serverdir>` as
the user therefore:
- **DOES delete the world contents** (the `data/` subdir ends up EMPTY), but
- hits `cannot remove '<serverdir>/data': Permission denied` unlinking from the root-owned parent,
  leaving empty husks behind.

Finish the cleanup with sudo (world data is already gone; this just removes the empty dirs):

```bash
sudo rm -rf /home/ruben/homeserver/minecraft-atm10aero /home/ruben/homeserver/minecraft-e10
```

Diagnose first: `ls -lad <dir> <dir>/data` — an empty ruben-owned `data/` under a root-owned parent
is the signature. Only `minecraft-evo2` is live — never delete its top-level dir, only `data/world`.
The nightly backup script only tar'd the vanilla server (`backups/minecraft/vanilla-*.tar.gz`); the
modded servers have no backups, so this cleanup is unrecoverable.

## Chunky pregen: ignore the FIRST rate reading

The first `chunky progress` a few seconds after `chunky start` shows a misleading ~2–3 cps and a
multi-hour ETA (JIT warmup). Re-check after ~60s — FTB Evo2 stabilizes at **~15 cps**. Don't act on
the warmup number. Radius is in **blocks**: `chunky radius 3000` = 6000×6000 ≈ 141k chunks ≈ 2.6 h
at 15 cps. Chunky 1.5.4 commands: `center <x> <z>`, `radius <r>`, `world <w>`, `start`, `progress`,
`continue`, `cancel` (no `chunky version`). Watch completion with `scripts/chunky-watch.sh`.
