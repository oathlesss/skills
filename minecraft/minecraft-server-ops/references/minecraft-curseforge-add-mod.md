# Adding individual CurseForge mods to an itzg AUTO_CURSEFORGE server

When the user wants one or two specific mods added to a running modpack server (that aren't in the pack), don't switch the whole pack — fetch the mod jar via the CurseForge API and drop it into `/data/mods/`.

## Recipe (NeoForge 1.21.1 example)

All CurseForge v1 API calls need an `x-api-key` header (the same `CF_API_KEY` the server uses). Load it **in-process** so it never touches a shell command line:

```python
from hermes_tools import terminal
key = terminal("sops --decrypt secrets/cf_api_key.txt.sops", workdir="/home/ruben/homeserver")["output"].strip()
```

Endpoints (all under `https://api.curseforge.com/v1/`):

1. **Find mod id by slug:** `GET mods/search?gameId=432&slug=<slug>` → `data[0].id`
2. **List files:** `GET mods/{id}/files?gameVersion=1.21.1&modLoaderType=6` → sort by `fileDate` desc, filter `isAvailable`.
   - `modLoaderType`: 1=Forge, 4=Fabric, 6=NeoForge.
3. **Get direct URL:** `GET mods/{id}/files/{fid}/download-url` → `{"data": "<edge.forgecdn.net url>"}`.
   - ⚠️ The `/download` endpoint (no `-url`) returns **404** — use `/download-url`.
   - The file object also carries a `downloadUrl` field directly.
4. **Download** that URL → save to `<data>/mods/<fileName>` (jar filename from `fileName`).

## Key facts

- `gameId` for Minecraft = 432.
- Distinct mods with confusingly similar names (all AE2 addons here):
  - `advancedae` = AdvancedAE (base); `advancedae-addon` = AdvancedAE Addon (a *separate* addon on top of AdvancedAE).
  - `applied-flux` = AppliedFlux; `applied-mekanistics` = Applied Mekanistics; `megacells` = MEGA Cells.
- Modrinth search API works without a key and is useful for discovering a mod's slug/loader support, but many AE2 addons are **CurseForge-only** (return 404 on Modrinth).

## Adding the jar to a running server

1. Drop the jar into `/data/mods/`.
2. `docker compose restart <service>`.
3. Extra jars **survive restart** because itzg's AUTO_CURSEFORGE sync does NOT delete non-manifest mods (`REMOVE_OLD_MODS` defaults false).
4. **Re-decrypt the CF key + mc.env BEFORE restart** (the volume-mounted-secret pitfall — otherwise the bind mount source file is gone).
5. Verify: grep boot logs for the `Found mod file "..."` line, then `Done (...)`.

## Pitfall: secrets on the command line

Never pass the CF key via shell interpolation or a `curl -H "x-api-key: ..."` in a visible command. Use `execute_code` (Python) so the key lives only in process memory; print only `len(key)`, never the value.
