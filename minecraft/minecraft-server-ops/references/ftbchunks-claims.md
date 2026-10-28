# FTB Chunks claim-protection config (NeoForge / ATM packs)

## Trigger
"Claims block other players from building/interacting" — you want claims to keep
*damage* protection (explosions, mob griefing) but stop restricting other players.

## Core fact: it's a TWO-place change
FTB Chunks snapshots every team's property values into per-team files at team
creation. Editing config defaults alone does **not** change existing teams.

1. Config defaults (`team_prop_defaults`) → affect **new** teams only.
2. Per-team snapshots → must be edited for **existing** teams.

Verify whether a team has custom values: check `world/ftbteams/player/<uuid>.json5`
— the `properties` map holds the snapshotted values.

## File locations (itzg AUTO_CURSEFORGE container, world bind-mounted)
- Modpack default (overwritten on pack update):
  `data/config/ftbchunks-world.json5` → e.g. `~/homeserver/minecraft-atm11/data/config/`
- Persistent server override (survives pack update — write your edits here):
  `world/serverconfig/ftbchunks-world.json5` → e.g. `~/atm11-world/serverconfig/`
  (create it if absent; it takes precedence over `data/config/`)
- Per-team properties:
  `world/ftbteams/player/<team-uuid>.json5` → e.g. `~/atm11-world/ftbteams/player/*.json5`
  (the `ftbteams/player/<uuid>.json5` files, NOT the `ftbchunks/<uuid>.json5`
  chunk-list files — those only hold claimed-chunk coords + limits)

## Property semantics
`team_prop_defaults` config keys ↔ per-team `ftbchunks:*` keys:

| config key | team key | meaning |
|---|---|---|
| `def_block_edit` | `ftbchunks:block_edit_mode` | break/place blocks (NeoForge) |
| `def_block_interact` | `ftbchunks:block_interact_mode` | right-click blocks (NeoForge) |
| `def_entity_interact` | `ftbchunks:entity_interact_mode` | interact with entities |
| `def_entity_attack` | `ftbchunks:nonliving_entity_attack_mode` | left-click non-living (armor stands, item frames) |
| `def_allow_explosions` | `ftbchunks:allow_explosions` | `false` = explosions PROTECTED |
| `def_mob_griefing` | `ftbchunks:allow_mob_griefing` | `false` = mob griefing PROTECTED (endermen) |

PrivacyMode values: `allies` (default; teammates + allies), `private`, `public` (anyone).

To "let everyone build but keep damage protection": set the four `*_mode` keys to
`"public"`, leave `allow_explosions` / `allow_mob_griefing` = `false`.

DO NOT touch (map visibility, not a permission mode):
- `def_player_visibility` / `ftbchunks:location_mode`
- `def_claim_visibility` / `ftbchunks:claim_visibility` (already `public` by default)

No separate "fire damage" toggle exists: explosion protection already covers
fireball-type damage. `fire_spread_protection` (top-level) only stops fire spreading
*across claim borders*, is off by default, and has a perf cost — usually leave it off.

## Procedure (safe order)
1. **Stop the server first.** A graceful stop saves in-memory team data OVER your
   file edits, so editing team files before stop is pointless (they get clobbered).
2. Back up config + all team files.
3. Edit `team_prop_defaults` (four `def_*_mode` → `"public"`) in BOTH
   `data/config/` and `world/serverconfig/` (create the override if absent).
4. Edit each team file's `properties` map (four `ftbchunks:*_mode` → `"public"`),
   keep `allow_explosions`/`allow_mob_griefing` = `false`.
5. Start server; verify the values survived startup (server preserves them on load).

## Pitfall: graceful shutdown can hang on save
If Chunky pregen (or any bulk worldgen) was mid-run, a graceful stop can hang 20+
minutes at "Saving worlds" flushing hundreds of region files.

Detect a hang: `docker logs` stuck at "Saving worlds"; `iostat` shows 0 disk
activity; `find <world> -name '*.mca' -mmin -1` returns nothing (writes stopped).

Resolve: `docker stop -t 5 <container>` (SIGTERM grace then SIGKILL → exit 137).
Use `docker stop`, NOT `docker kill`, when restart policy is `unless-stopped` so it
doesn't auto-restart before you edit files. Already-flushed chunks are safe; the
world comes back clean. Note: after a forced kill, `level.dat` may be stale — check
whether autosave is actually firing (a month-old `level.dat` mtime while region
files are recent is a red flag worth flagging to the user).

## In-game alternative (no restart, no file edits)
Team owners can change these per-team via the FTB Chunks map (M) → settings gear →
Block Edit Mode / Block Interact Mode / Entity Interact / Non-living Entity Attack →
Public. Instant; no server restart needed. But it only affects that one team.
