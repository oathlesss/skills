# Adding a single extra mod to an itzg AUTO_CURSEFORGE server

When the user wants ONE specific mod added to an already-running CurseForge modpack server (e.g. "add AppliedFlux"), do NOT switch the whole pack — drop the jar into the existing data dir and restart.

## 1. Check if it's already in the pack

```bash
ls -1 <data>/mods/ | grep -iE "<slug-pattern>"
# also check the manifest — NOTE itzg's format is NOT standard CurseForge
python3 -c "import json;d=json.load(open('<data>/.curseforge-manifest.json'));print([f for f in d['files'] if '<kw>' in f.lower()])"
```

The `.curseforge-manifest.json` in itzg's data dir has top-level keys `@type, timestamp, files, modpackName, modpackVersion, slug, modId, fileId, ...` and `files` is a flat list of **path strings** like `mods/<name>.jar` (not `{projectID, fileID}` objects). The "files" count (~3455) includes configs/scripts, not just mods; filter `files` for `mods/` prefix to get the real mod list (~398).

## 2. Find the CurseForge project + file (API, key kept in-process)

`gameId` 432 = Minecraft. `modLoaderType` **6 = NeoForge** (0=any, 1=Forge, 4=Fabric).

```python
from hermes_tools import terminal
key = terminal("sops --decrypt secrets/cf_api_key.txt.sops", workdir=HOME)["output"].strip()  # in-process, never printed
# GET /v1/mods/search?gameId=432&slug=<slug>            -> data[0].id (project id)
# GET /v1/mods/{id}/files?gameVersion=1.21.1&modLoaderType=6  -> sort by fileDate desc, filter isAvailable
# GET /v1/mods/{id}/files/{fid}/download-url            -> {"data": "https://edge.forgecdn.net/files/..."}
```

Pitfalls:
- The `/v1/mods/{id}/files/{fid}/download` endpoint **404s**. Use **`/download-url`** (returns a direct `edge.forgecdn.net` CDN URL), or the `downloadUrl` field on the file object.
- Send `x-api-key` + `Accept: application/json` + a `User-Agent` header on every request (and on the CDN download too).

## 3. Install + restart

1. Write the jar into `<data>/mods/`.
2. **Re-decrypt secrets** (`cf_api_key.txt` + `mc.env`) before restarting — the bind-mount cleanup pitfall (see SKILL.md) means `docker compose restart` fails if the plaintext files are gone.
3. `docker compose restart <service>`.
4. Verify: `docker logs <container> | grep -i "<modname>"` shows `Found mod file "...jar"` plus the mod's loaded id, and `Done (Ns)!` appears.

## 4. Version matching (addon mods)

For addon mods (AE2 addons, Mekanism addons, etc.), match to the pack's **core mod version**. Example: the pack's AE2 was `appliedenergistics2-19.2.17.jar`, so AppliedFlux / AdvancedAE-addon must be 1.21.1-NeoForge builds compatible with AE2 19.x. Grab the LATEST 1.21.1 NeoForge file (sort `files` by fileDate desc). Report the exact version back so the user can match their client — mismatched client versions cause join errors.

## 5. Survival across restarts

A manually-dropped jar survives `docker compose restart` because itzg's CurseForge sync does NOT delete extra mods (`REMOVE_OLD_MODS` defaults to false) — it only re-downloads missing manifest mods.

## Notes from the ATM10 Aeronautics session (2026-09)

- AE2-adjacent addons already shipped in that pack: ExtendedAE, AdvancedAE, MEGA Cells, Applied Mekanistics, ae2wtlib (wireless terminals), AE2 Network Analyzer, AE Infinity Booster, Expanded AE, Flux Networks. It is essentially "maxed out" on AE2 addons — AE2 Things (DISK drives) is stale (2024) and incompatible with AE2 19.2.x; AE2 Crystal Science and AE2 Lightning Tech are active but are content/progression mods, not QoL.
