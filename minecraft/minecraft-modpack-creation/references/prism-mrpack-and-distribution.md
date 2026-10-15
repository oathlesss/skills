# Prism-importable `.mrpack` + delivery to Ruben

## When
Building a client pack for Ruben to import into Prism Launcher, or delivering any
pack/zip to him over HTTP.

## Self-contained `.mrpack` format (Prism "Add Instance → Import")
Prism imports Modrinth `.mrpack` files natively. A *self-contained* pack puts EVERY jar in
`overrides/mods/` and leaves `files: []` — no Modrinth API resolution, so CurseForge-only
mods (AE2, FTB Quests, Distant Horizons…) work fine. This is the right format whenever the
target is Prism, regardless of platform exclusivity.

Archive layout (it's just a zip):
```
<name>.mrpack
├── modrinth.index.json
└── overrides/
    ├── mods/*.jar          ← all client jars
    ├── config/**           ← config files (NOT config/config/)
    └── defaultconfigs/**   ← only if the source pack ships one
```

`modrinth.index.json` — exact known-good schema (copy this):
```json
{
  "formatVersion": 1,
  "game": "minecraft",
  "versionId": "1.0.0",
  "name": "evo2-tech",
  "summary": "...",
  "files": [],
  "dependencies": { "minecraft": "26.1.2", "neoforge": "26.1.2.109" }
}
```
`dependencies.neoforge` = the bare NeoForge version (e.g. `26.1.2.109`, `21.1.259`).
`dependencies.minecraft` = the MC version string (26.1.2 in the new scheme, 1.21.1 in the old).
Ruben's existing `~/homeserver/www/Oathless-Server-Pack-1.0.0.mrpack` is a proven reference —
read it back with `zipfile` before authoring a new one.

## PITFALL — double-nested `config/config/`
When merging a source pack's config tree, the merge-output root is NOT the config dir — it
CONTAINS `config/` and `defaultconfigs/` subdirs. Doing `copytree(merge_root, overrides/config)`
silently produces `overrides/config/config/…`, which Prism installs to `.minecraft/config/config/`
— Minecraft never reads it, and the pack ships with zero effective config.

Fix: copy `merge_root/config → overrides/config` and
`merge_root/defaultconfigs → overrides/defaultconfigs` separately. After zipping, assert
`not any('config/config/' in n for n in archive.namelist())`.

## Copy the SOURCE pack's configs, not just its mods, to reproduce worldgen
"World generation from pack X" lives in X's config files, not the mod jars alone. FTB
Evolution 2 ships NON-default Tectonic (`vertical_scale: 1.06`, custom continent/erosion
scales, `ultrasmooth: false`) and Terralith (`skylands: true`, `terrain_slabs: true`,
`recipe_changes: false`) configs; the mods' own defaults would give vanilla-ish terrain.
So merge the source `config/` tree wholesale — but nuke the source's `ftbquests/` and overlay
your OWN quest book if you authored one, or its quests overwrite yours. Orphan configs for mods
NOT in your pack are inert (only ever read by their own mod), so a full-tree copy is safe.

## Delivery to Ruben over HTTP
Caddy (`~/homeserver/caddy/Caddyfile`) serves static files from `~/homeserver/www/` (mounted
`./www:/srv/www:ro`) at `https://oathless.dev/files/<filename>`:
```
handle_path /files/* {
    root * /srv/www
    file_server
}
```
`handle_path` strips the `/files` prefix, so `www/<name>` ↔ `oathless.dev/files/<name>`. Drop the
`.mrpack`/`.zip` into `~/homeserver/www/` and hand Ruben the URL. The route is PUBLIC (no auth) —
same as his existing `Oathless-Server-Pack` / `Oathless-Shaders-Addon` — flag it if he wants it
locked down. Verify with `curl -sI https://oathless.dev/files/<name>` (expect `HTTP/2 200` +
matching `content-length`).

## Java version pin (MC 26.1.2)
MC 26.1.2 requires **Java 25** (not 21). Client players must set Prism instance → Settings →
Java → 25. Server manifest pins `javaVersion: 25.0.2+10-LTS`; host JDK at
`~/.local/java/jdk-25.0.4.1+1`. Boot command pattern for headless smoke tests:
`JAVA_HOME=…/jdk-25.0.4.1+1 PATH=$JAVA_HOME/bin:$PATH sh run.sh`.
