# Exporting a shareable PrismLauncher/CurseForge modpack from an itzg server

Goal: give friends a one-step-importable modpack that exactly matches the server, without
redistributing bundled mod jars (the manifest references CF project/file IDs; the launcher
downloads them at install time).

## The lazy truth first
The pack is already public on CurseForge. "Our own modpack" is almost always just
**pinned CF version + the few manually-added mods**. Friends can install the official
pack in PrismLauncher directly and drop in the extra jars. Only build a full zip when they
want a single-file import or you've added several mods.

## Metadata files itzg leaves in the server data dir
All in `<data>/` (host path `/home/ruben/homeserver/minecraft-atm10aero/data/`):

- `.curseforge-manifest.json` — `me.itzg.helpers.curseforge.CurseForgeManifest`.
  Top-level keys: `@type`, `timestamp`, `files` (a list of RELATIVE PATHS like
  `mods/foo.jar` — **paths, NOT CF project/file IDs**), `modpackName`, `modpackVersion`,
  `slug`, `modId` (CF project ID of the pack), `fileId` (CF file ID of the installed
  version), `minecraftVersion`, `modLoaderId`, `levelName`.
- `.install-curseforge.env` — `MODPACK_NAME`, `MODPACK_VERSION`, `TYPE=NEOFORGE`,
  `VERSION=1.21.1`, `SERVER`.
- `.neoforge-manifest.json` — `minecraftVersion` + `forgeVersion` (e.g. 21.1.248).

The `modId`/`fileId` pin the EXACT CF version the server runs. Use them to fetch the
official pack zip, and to warn friends off a newer "latest" on CF.

## Find the official pack download URL (without reading the key)
The CF API key is mounted in the container at `/run/secrets/cf_api_key`. Query through
it without exposing the value:

```bash
docker exec minecraft-atm10aero sh -c 'curl -s -H "x-api-key: $(cat /run/secrets/cf_api_key)" \
  "https://api.curseforge.com/v1/mods/<modId>/files/<fileId>"'
# → data.downloadUrl (edge.forgecdn.net), data.fileLength (~100MB)
```

## Determine the manual-add delta
Diff the mods dir against the itzg manifest's `files` (mods/*.jar paths):

```python
manifest_mods = {f.split('/',1)[1] for f in manifest['files'] if f.startswith('mods/') and f.endswith('.jar')}
dir_mods = {f for f in os.listdir('<data>/mods') if f.endswith('.jar')}
manual = dir_mods - manifest_mods   # the extra jars
```

Classify each manual jar:
- **Client-required (content)** — adds items/blocks; the client MUST have it to join.
  e.g. AppliedFlux, advancedae_addon. Bundle these.
- **Server-side-only** — Chunky (pregen), C2ME (chunk I/O), Distant Horizons server jar
  (shared LOD pregen). Clients don't need them to join; DH is optional both sides.

## Build the shareable zip
`unzip` may be missing — use Python `zipfile` (stdlib):

1. `curl -sL -o official.zip "<downloadUrl>"`.
2. Extract `manifest.json` + `modlist.html` + everything under `overrides/`.
3. Copy the client-required jars into `overrides/mods/` (CF/PrismLauncher apply
   `overrides/` after downloading the manifest files, so these jars land in the instance).
4. Re-zip `manifest.json` + `modlist.html` + `overrides/` → `<Pack>-<Version>-Custom.zip`.

Verify: `manifest.json` parses, `overrides/mods/` contains the extras, root has
`manifest.json` + `modlist.html`. Result is ~100MB (overrides = config + kubejs is the
bulk; the official zip does NOT bundle the actual mod jars).

## Pitfalls
- **Version pinning**: the server runs a specific CF version; CF's "latest" is often
  newer. Friends installing the newer version get a mod mismatch and can't join. Read
  `.install-curseforge.env` → `MODPACK_VERSION` and tell friends to pick that exact
  version (enable "old versions" in PrismLauncher's CurseForge tab if needed).
- **398 vs 438 mod count is not a bug**: the CF manifest `files[]` includes client-only
  mods (JEI, Jade, minimap, etc.) that itzg skips server-side; PrismLauncher (client)
  installs all of them. Correct by design.
- **Discord 25MB cap**: a ~100MB pack zip can't be sent as an attachment. Distribute via
  a Forgejo release / Caddy static file, or send only the tiny client-required jars
  (a few hundred KB) and have friends install the official pack + drop them in.
- **Don't read the CF key**; query through the container's mounted key (house rule).
