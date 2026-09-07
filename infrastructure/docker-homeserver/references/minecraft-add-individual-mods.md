# Adding individual mods to an itzg AUTO_CURSEFORGE server

How to add one or two specific mods (not a whole pack swap) to a running
`MOD_PLATFORM=AUTO_CURSEFORGE` container — e.g. a client-only mod the user also
wants server-side, or a missing AE2 addon.

## 1. Check whether it's already in the pack
Don't download blind. Grep the server's mods dir, and/or the itzg manifest:
```bash
ls -1 <data>/mods/ | grep -iE '<name>'
python3 -c "import json; d=json.load(open('<data>/.curseforge-manifest.json')); print([f for f in d['files'] if f.startswith('mods/') and 'KEYWORD' in f.lower()])"
```
The itzg `.curseforge-manifest.json` is NOT the standard CurseForge manifest — its
`files` is a flat list of relative path strings (`mods/foo.jar`, `config/...`),
plus top-level keys `modpackName`, `minecraftVersion`, `modLoaderId`.

## 2. Resolve the mod on the API
- **CurseForge** (`api.curseforge.com/v1`) needs `x-api-key` for EVERYTHING.
  Load the key in-process (execute_code) — never on a shell command line:
  ```python
  from hermes_tools import terminal
  key = terminal("sops --decrypt <homeserver>/secrets/cf_api_key.txt.sops")["output"].strip()
  ```
- **Modrinth** (`api.modrinth.com/v2`) is auth-free but needs a `User-Agent` header,
  and is useful for version/loader lookups (`/project/<slug>`, `/project/<slug>/version?...`).

## 3. Find the right file (CurseForge)
```python
# slug -> mod id
search = cf_get("mods/search", {"gameId": 432, "slug": slug})          # gameId 432 = Minecraft
mod_id = search["data"][0]["id"]
# files filtered by MC version + loader; modLoaderType 6 = NeoForge
files = cf_get(f"mods/{mod_id}/files", {"pageSize": 50, "gameVersion": "1.21.1", "modLoaderType": 6})
top = sorted([f for f in files["data"] if f.get("isAvailable")], key=lambda f: f["fileDate"], reverse=True)[0]
```
`cf_get` = urllib GET with headers `{"x-api-key": key, "Accept": "application/json", "User-Agent": "..."}`.

## 4. Download it
**Use `/download-url`, not `/download`** — the `/download` endpoint returns 404
(as of 2026-09). `/download-url` returns `{"data": "<direct CDN url>"}`; GET that
with the key header to fetch the jar.
```python
direct = cf_get(f"mods/{mod_id}/files/{fid}/download-url")["data"]
# urllib GET direct -> bytes -> write to <data>/mods/<fileName>
```

## 5. Install + restart
- Drop the jar into `<data>/mods/`. Extra mods survive restart — itzg only removes
  files not in the manifest when `REMOVE_OLD_MODS`/`CF_FORCE_SYNCHRONIZE` is set.
- **Re-decrypt the volume-mounted CF key before restarting.** The deploy flow cleans
  up plaintext secrets after `up -d`; on restart docker re-binds `./secrets/cf_api_key.txt`
  and, if the host file is gone, creates a **root-owned directory at that path**,
  breaking the mount (`Are you trying to mount a directory onto a file`). Clear the
  stray dir with an alpine container, then re-decrypt:
  ```bash
  docker run --rm -v <homeserver>:/host alpine:latest rm -rf /host/secrets/cf_api_key.txt
  sops --decrypt secrets/cf_api_key.txt.sops > secrets/cf_api_key.txt && chmod 600 secrets/cf_api_key.txt
  sops --input-type dotenv --output-type dotenv --decrypt secrets/mc.env.sops > secrets/mc.env && chmod 600 secrets/mc.env
  docker compose restart <service>
  ```
- Verify load: `docker logs <c> | grep -i "<modid or filename>"` → "Found mod file"
  line + the mod registering; confirm "Done (Xs)!" and `docker exec <c> rcon-cli list`.

## Matching the client
Tell the user the exact version you installed and have them match their client.
A server/client version mismatch on NeoForge 1.21.1 is usually tolerated but can
kick; exact match is safest.
