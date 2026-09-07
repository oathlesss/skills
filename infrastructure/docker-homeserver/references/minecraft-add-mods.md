# Adding Individual Mods to a Running AUTO_CURSEFORGE Server

When the user wants extra mods added to an already-deployed CurseForge modpack
server (e.g. "add AppliedFlux and AdvancedAE Addon to my ATM10 Aeronautics
server, if not already present"), use this flow. itzg's AUTO_CURSEFORGE does
**not** remove manually-placed mods on restart (`REMOVE_OLD_MODS` defaults to
false), so dropping a JAR into `<data>/mods/` and restarting is enough.

## 1. Check what's already in the pack

The server's downloaded mods live in `<data>/mods/`:

```bash
ls -1 /home/ruben/homeserver/<service>/data/mods/ | grep -iE "<term>"
```

### ⚠️ PITFALL: `.curseforge-manifest.json` is itzg's own format

The itzg data dir has `.curseforge-manifest.json`, but it is **NOT** the standard
CurseForge `manifest.json` (`manifestType: minecraftModpack`, `files:
[{projectID, fileID, required}]`). itzg rewrites it. Its top-level keys are:

```
@type, timestamp, files, modpackName, modpackVersion, slug, modId, fileId,
fileName, minecraftVersion, modLoaderId, levelName
```

`files` is a flat list of **path strings** (e.g. `mods/foo-1.2.3.jar`,
`config/...`), not objects. Parsing it as the standard manifest throws
`AttributeError: 'str' object has no attribute 'get'`. Use it to enumerate the
full pack contents:

```bash
python3 -c "import json; d=json.load(open('.curseforge-manifest.json'));
mods=[f for f in d['files'] if f.startswith('mods/')];
print('\n'.join(m for m in mods if '<term>' in m.lower()))"
```

This reveals the full mod list — including client-only mods the server-side
`mods/` folder may have filtered out. (This is how you confirm a "shader mod"
question: grep the manifest for `oculus|iris|embeddium|sodium|shader`.)

## 2. Match the version to the pack's dependency

For addon mods, check the dependency's version in the pack first. AE2 addons
depend on the pack's AE2 build:

```bash
ls -1 <data>/mods/ | grep -iE "appliedenergistics|ae2"
# → appliedenergistics2-19.2.17.jar   → AE2 19.2.17
```

Then pick the latest addon build compatible with that (same MC version + loader).

## 3. Download via CurseForge API (needs key)

Load the CF key **in-process via execute_code** — never echo it into a shell
command (it's bcrypt-like `$2a$10$...`; must stay out of shell history/process
listings):

```python
from hermes_tools import terminal
key = terminal("sops --decrypt secrets/cf_api_key.txt.sops", workdir=HOME)["output"].strip()
```

CF v1 API — every endpoint needs the `x-api-key` header:
- `GET /v1/mods/search?gameId=432&slug=<slug>` → `data[0].id` = modId
- `GET /v1/mods/{modId}/files?gameVersion=1.21.1&modLoaderType=6` → files
- `GET /v1/mods/{modId}/files/{fileId}/download-url` → `{"data": "<CDN url>"}`

`gameId=432` is Minecraft. `modLoaderType`: 0=All, 1=Forge, 2=Cauldron,
3=LiteLoader, 4=Fabric, 5=Quilt, **6=NeoForge**.

### ⚠️ PITFALL: `/download` returns HTTP 404 — use `/download-url`

`GET /v1/mods/{id}/files/{fid}/download` returns 404. The working endpoints are
`/download-url` (returns `{"data": "<url>"}`) or the `downloadUrl` field on the
file object. The CDN URL is `edge.forgecdn.net` / `mediafilez.forgecdn.net` and
downloads fine with just the `x-api-key` header.

## 4. Download via Modrinth API (no auth) — check both platforms

Some mods are CurseForge-only (e.g. **AppliedFlux** — not on Modrinth at all)
and some are Modrinth-only. Check both. Modrinth is public:

```bash
curl -s -H "User-Agent: hermes-agent/1.0" "https://api.modrinth.com/v2/project/<slug>"
curl -s -H "User-Agent: hermes-agent/1.0" \
  "https://api.modrinth.com/v2/project/<slug>/version?game_versions=[\"1.21.1\"]&loaders=[\"neoforge\"]"
```

`versions[].files[0].url` is the direct download. ⚠️ Set a `User-Agent` header —
Modrinth returns empty responses without one.

## 5. Place the JAR + restart (with the SOPS re-decrypt dance)

Copy the JAR into `<data>/mods/`, then restart. ⚠️ The volume-mounted
`secrets/cf_api_key.txt` is cleaned up after each deploy, so **re-decrypt it
(and `mc.env`) before `docker compose restart`**, or the bind mount fails:

```bash
~/.local/bin/sops --decrypt secrets/cf_api_key.txt.sops > secrets/cf_api_key.txt && chmod 600 secrets/cf_api_key.txt
~/.local/bin/sops --input-type dotenv --output-type dotenv --decrypt secrets/mc.env.sops > secrets/mc.env && chmod 600 secrets/mc.env
docker compose restart <service>
```

Clean up the plaintext again after boot (`rm -f secrets/cf_api_key.txt secrets/mc.env`).

## 6. Verify

```bash
docker logs <container> 2>&1 | grep -i "Found mod file"
docker logs <container> 2>&1 | grep -i "Done ("
```

`Found mod file "<jar>"` + a `Done (Xs)!` line = loaded + booted. A ~3s "Done"
on restart = mods already cached; ~18s = first full load. Benign startup ERROR
lines (data-map warnings, config "correcting") are normal in big packs — the
`Done` marker is the real success signal.

## Stray root-owned dir at the secret mount path

If `docker compose up` ran while a plaintext secret file was absent, Docker
creates a **root-owned directory** at the mount source (e.g.
`secrets/cf_api_key.txt/`). Remove it before re-decrypting, else the
`sops --decrypt > secrets/cf_api_key.txt` redirect fails ("Is a directory"):

```bash
docker run --rm -v /home/ruben/homeserver:/host alpine:latest rm -rf /host/secrets/cf_api_key.txt
```

## Worked example (session)

Added AppliedFlux 2.1.5 + AdvancedAE Addon 21.1.0 to ATM10 Aeronautics
(NeoForge 1.21.1, AE2 19.2.17) via exactly this flow. Notes:
- **AppliedFlux** (slug `applied-flux`, GlodBlock) is CurseForge-only — a
  Modrinth `project/applied-flux` lookup returns 404.
- **AdvancedAE Addon** (slug `advancedae-addon`) is a *distinct* mod from
  **AdvancedAE** (base, already in the pack). Don't conflate them — verify the
  exact slug/name before assuming "already present".
