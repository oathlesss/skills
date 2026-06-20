# Minecraft CurseForge Modpack Setup (itzg/minecraft-server)

Condensed from the [itzg docker-minecraft-server docs](https://docker-minecraft-server.readthedocs.io/en/latest/types-and-platforms/mod-platforms/auto-curseforge/).

## Environment Variables

### Required

| Variable | Value |
|---|---|
| `TYPE` | `AUTO_CURSEFORGE` (or `MODPACK_PLATFORM`) |
| `CF_API_KEY` | CurseForge API key from https://console.curseforge.com/ |
| `CF_SLUG` or `CF_PAGE_URL` | Modpack identifier |

### Version Pinning

By default, the latest modpack file and its mod loader are installed on every startup (auto-upgrading). To pin:

- `CF_PAGE_URL` with a specific file URL: `https://www.curseforge.com/minecraft/modpacks/<slug>/files/<id>`
- `CF_FILE_ID`: numerical file ID (e.g. `"4248390"`)
- `CF_FILENAME_MATCHER`: substring match (e.g. `"1.0.7"`)

**Do not select a server file** — they lack the required manifest and break automation.

### Mod Loader Override

- `CF_MOD_LOADER_VERSION`: override the mod loader version declared by the modpack (e.g. `"43.4.22"`)

### Excluding Mods

- `CF_EXCLUDE_MODS`: newline-delimited list of mod slugs to exclude (useful for client-only mods not properly flagged)
- `CF_OVERRIDES_EXCLUSIONS`: comma or newline-delimited ant-style paths relative to `/data` (e.g. `mods/iris*.jar,mods/sodium*.jar`)

### World Data

- `CF_SET_LEVEL_FROM`: `WORLD_FILE` or `OVERRIDES` — auto-set `LEVEL` to the modpack's world save

### Other

- `CF_PARALLEL_DOWNLOADS`: parallel mod downloads (default: 4)
- `CF_OVERRIDES_SKIP_EXISTING`: skip existing files in overrides (default: false)
- `CF_FORCE_REINSTALL_MODLOADER`: force modloader reinstall (default: false)
- `CF_FORCE_SYNCHRONIZE`: force full re-download of all mods/overrides (default: false). Set to `"true"` when switching modpacks on an existing data directory to avoid stale file conflicts

## API Key Handling

### Docker Compose (.env)

```
# .env — single quotes, no $ escaping needed
CF_API_KEY='$11$22...aaaa'
```

```yaml
# compose.yaml
environment:
  CF_API_KEY: ${CF_API_KEY}
```

### Docker Run

```bash
# Single quotes required around the key
docker run ... -e CF_API_KEY='$11$22...aaaa'
```

### Docker Secrets (alternative)

```yaml
service:
  environment:
    CF_API_KEY_FILE: /run/secrets/cf_api_key
  secrets:
    - cf_api_key

secrets:
  cf_api_key:
    file: cf_api_key.secret
```

## Example: Full Compose Fragment

**⚠️ PITFALL: Java version matters.** `itzg/minecraft-server:latest` runs Java 25, but many modpacks target specific Java versions. Forge 1.20.1 needs Java 17; Neoforge 1.21.x needs Java 21. Running on the wrong Java produces `Unsupported class file major version 69`. Pin the correct image tag (class file version → Java version: 61=17, 65=21, 69=25).

```yaml
minecraft:
  image: itzg/minecraft-server:java17     # NOT :latest — Forge 1.20.1 needs Java 17
  container_name: minecraft
  restart: unless-stopped
  ports:
    - "25565:25565"
    - "25575:25575"     # RCON for programmatic control/stress testing
  volumes:
    - ./minecraft/data:/data
  environment:
    EULA: "TRUE"
    TYPE: "AUTO_CURSEFORGE"
    CF_API_KEY: ${CF_API_KEY}
    CF_SLUG: "integrated-minecraft"
    MEMORY: "8G"
    DIFFICULTY: "normal"
    MAX_PLAYERS: "10"
    ONLINE_MODE: "true"
    ENABLE_RCON: "true"
    RCON_PASSWORD: "${RCON_PASSWORD}"
  networks:
    - homeserver
```

## Debugging: Key Issues

### PITFALL: `env_file:` also has `$` expansion — use `CF_API_KEY_FILE` instead

**The problem:** Docker Compose expands `$` signs in `env_file:` values too, not just in `.env` files. When using `TYPE: AUTO_CURSEFORGE` with the API key in an env_file (e.g. SOPS-decrypted `secrets/mc.env`), `$` characters in the key get silently expanded to empty strings. The container's `mc-image-helper` logs:

```
ERROR : The API key should start with '$2a$10$' but yours looked like '$2a$10.*****82'. Make sure to escape dollar signs with two each.
```

**Why this happens:** Docker Compose processes `env_file:` values through the same variable substitution engine as `.env` and `environment:` blocks. Even though documentation suggests env_file values are passed literally, the shell parser in Docker Compose sees `$2a$10$ZOxGu...` and treats each `$...` segment as a variable reference.

**The fix: `CF_API_KEY_FILE` + SOPS plain-text secret.** Mount the raw API key as a file inside the container — no escaping games, no shell expansion:

```yaml
# docker-compose.yml
services:
  minecraft-modded:
    image: itzg/minecraft-server:java25
    env_file:
      - ./secrets/mc.env          # RCON_PASSWORD, other non-$ secrets
    volumes:
      - ./secrets/cf_api_key.txt:/run/secrets/cf_api_key:ro
    environment:
      TYPE: AUTO_CURSEFORGE
      CF_SLUG: "all-the-mods-10"
      CF_API_KEY_FILE: /run/secrets/cf_api_key   # ← reads raw key from file
      # No CF_API_KEY env var — avoids all $ expansion
```

The key file is SOPS-encrypted alongside other secrets:

```bash
# secrets/cf_api_key.txt (one line, no quotes, no env var syntax)
$2a$10$ZOxGuEU4zwq0M8FaNrLPP.aOO6NZxSKRmsEsUAKriiwQOi/wHSI82
```

```bash
# Encrypt it
sops --encrypt secrets/cf_api_key.txt > secrets/cf_api_key.txt.sops && rm secrets/cf_api_key.txt
```

**deploy.sh changes:** The deploy wrapper must handle both dotenv `.sops` files (`*.env.sops`) and plain-text `.sops` files (`*.txt.sops`). For `.txt.sops` files, decrypt without `--input-type dotenv`:

```bash
# In decrypt_secrets() — distinguish by extension
if [[ "$sops_file" == *.txt.sops ]]; then
    "$SOPS" --decrypt "$sops_file" > "$out_file"     # plain text
else
    "$SOPS" --input-type dotenv --output-type dotenv --decrypt "$sops_file" > "$out_file"
fi
```

Cleanup removes ALL decrypted files after deploy, including `cf_api_key.txt`.

**Diagnose:** Check what the container actually received:
```bash
# Wrong: shows truncated key
docker exec minecraft-modded sh -c 'echo $CF_API_KEY | wc -c'

# Right: with CF_API_KEY_FILE, the key is intact
docker exec minecraft-modded cat /run/secrets/cf_api_key | wc -c
```

**When to use this:** Any secret containing `$` that needs to survive Docker Compose processing. CurseForge API keys are the most common case (bcrypt-like `$2a$10$...` format). RCON passwords and other alphanumeric secrets don't need this — they work fine in env_file.

### PITFALL: Testing the key independently

Before restarting the container (which retries and burns rate limit), test the key directly:
```bash
CF_KEY=$(grep CF_API_KEY .env | cut -d= -f2- | tr -d "'")
curl -s -w "\nHTTP:%{http_code}" -H "x-api-key: $CF_KEY" \
  "https://api.curseforge.com/v1/mods/search?gameId=432&searchFilter=test&classId=4471"
```

- HTTP 200 = key works
- HTTP 403 = key invalid or expired
- Rate-limited = wait and retry

**Do not** test against `/v1/games` — that endpoint accepts invalid keys, giving false positives.

### PITFALL: Editing `.env` with sed/awk

Shell tools like `sed -i` can corrupt credential lines (special characters, unexpected substitution). Use `write_file` or `execute_code` (Python) to safely write credentials. If corruption happens, the user must re-paste the credential — there's no recovery.

### PITFALL: Testing with `docker compose run` before full startup

When debugging AUTO_CURSEFORGE issues, avoid the container's restart loop by testing `mc-image-helper` directly through docker compose (uses the same `.env` and config as the real service):

```bash
# Test the download without starting the full server
docker compose run --rm --entrypoint mc-image-helper minecraft \
  install-curseforge --slug integrated-minecraft --output-directory /tmp/test

# Check that the env vars are correctly interpolated
docker compose run --rm --entrypoint /bin/sh minecraft -c 'echo $CF_API_KEY | wc -c'
```

This is faster and safer than letting the container crash-loop. Once the test succeeds, `docker compose up -d minecraft` for the real run.

## Migration Checklist

When switching from a plain mod loader (e.g. `TYPE=NEOFORGE`) to `AUTO_CURSEFORGE`:

1. **Find the modpack's MC version** — check the CurseForge page to determine which Java image tag to use
2. **Pin the correct Java image tag**: `java17` for 1.20.x Forge, `java21` for 1.21.x
3. **Back up the world** (if keeping it): `cp -r ./minecraft/data/world ./minecraft/data/world.backup-$(date +%Y%m%d)`
4. **Remove `VERSION`**: AUTO_CURSEFORGE determines the MC version from the modpack
5. **Remove mod loader-specific configs**: old `config/` files may conflict with modpack overrides
6. **Add CF_API_KEY to .env** with single quotes
7. **Restart**: `docker compose up -d minecraft`
8. **Watch logs**: `docker compose logs -f minecraft` — first start downloads mods, takes a few minutes

## Stress Testing

### PITFALL: Forge servers reject vanilla clients

Forge modded servers require clients to negotiate mod channels during the handshake. Vanilla Minecraft clients (and bot libraries like `mineflayer`, `minecraft-protocol`) are rejected with:

```
Disconnecting VANILLA connection attempt: This server has mods that require Forge to be installed on the client.
```

This means you **cannot** use Node.js bot libraries (`mineflayer`, `minecraft-protocol`) to stress-test a Forge modded server. There are no practical Forge-compatible bot libraries in Python/Node.js.

**Workaround: Use RCON for stress testing.** RCON bypasses the client handshake entirely and can force chunk loading, spawn entities, and run commands to simulate player-like load.

### RCON Setup

The RCON port (25575) is **not published by default** in the compose example. Add it to the `ports` mapping to use from the host:

```yaml
ports:
  - "25565:25565"
  - "25575:25575"       # RCON — needed for programmatic stress testing
```

**PITFALL: Default RCON password.** When `RCON_PASSWORD` is set in the compose file but the `.env` value is a placeholder (e.g. `your-m...word`), the itzg image uses that literal string as the password. Check with:

```bash
docker exec minecraft cat /data/server.properties | grep rcon.password
```

**PITFALL: `server.properties` doesn't auto-update.** The itzg image generates `server.properties` on first run, but subsequent env var changes (like `ONLINE_MODE`, `RCON_PASSWORD`, `DIFFICULTY`) are **ignored** if the file already exists. Delete it before restarting to apply changes:

```bash
rm -f ./minecraft/data/server.properties
docker compose up -d minecraft
```

### RCON Stress Test Pattern

```python
from mcrcon import MCRcon

with MCRcon('localhost', 'your-rcon-password', port=25575) as mcr:
    # Force-load chunks in a grid around spawn
    for cx in range(-15, 15):
        for cz in range(-15, 15):
            mcr.command(f'forceload add {cx*16} {cz*16}')

    # Check TPS impact
    print(mcr.command('forge tps'))

    # Clean up
    mcr.command('forceload remove all')
```

**Install mcrcon:** `uv pip install mcrcon`

**PITFALL: RCON timeouts under heavy load.** When the server is genuinely stressed, RCON commands may timeout because the main thread is busy processing ticks. This is a signal that the stress test is working — not a failure. Use shorter batch sizes with delays between them to stay responsive.

### Realistic Multi-Player Stress Test

For a realistic simulation of N players exploring and building:

1. **Spawn marker armor stands** (fake players):
   ```python
   cmd(mcr, f'summon armor_stand ~ ~ ~ {NoGravity:1b,Invisible:1b,Marker:1b,CustomName:\'"P1"\'}')
   ```

2. **Teleport them to spread-out locations** — this forces actual chunk/terrain generation (unlike `forceload` which only prevents unloading):
   ```python
   cmd(mcr, 'tp @e[name=P1,limit=1] 500 100 500')
   ```

3. **Forceload 7×7 chunks around each "player"** (matches real player chunk loading radius)

4. **Spawn entity clusters** at each location to simulate base activity:
   ```python
   cmd(mcr, f'execute positioned {x} 40 {z} run summon zombie ~5 ~ ~5')
   cmd(mcr, f'execute positioned {x} 65 {z} run summon item ~2 65 ~2 {{Item:{{id:"cobblestone",Count:1b}}}}')
   ```

5. **Phase 2: Simultaneous movement** — teleport all players to new positions at once, then check TPS

6. **Phase 3: Combat waves** — spawn 16 mobs per player simultaneously (80 mobs for 5 players)

7. **Monitor with `forge tps`** between phases — tick times <50ms = solid 20 TPS

**Performance reference (Integrated MC on OptiPlex 3070 Micro, 10G RAM):**
- 5 players exploring + 80 zombies = 0.074ms tick time, 20.0 TPS (barely any load)
- 900+ forceloaded chunks = "Can't keep up! 330 ticks behind" (synthetic edge case)
- Normal 5-player gameplay: well within limits

## Project Discovery — Finding the Modpack Slug / ID

### PITFALL: CurseForge pages are JavaScript-rendered

The CurseForge website loads content via client-side JavaScript. The initial HTML source contains **no project IDs, no file IDs, no mod names**. Shell-based scraping (`curl | grep` for `project-id`, `data-project-id`, or numeric IDs) will return nothing. The HTML is an empty JS shell — all data arrives via XHR/fetch after page load in a browser.

**Symptoms:** `curl -sL "https://www.curseforge.com/minecraft/modpacks/<slug>" | grep -oP 'project.*\d+'` returns empty. No amount of regex or grep variation will find project metadata in the source.

**Workaround:** Use the CurseForge API (requires an API key — see below) or look up the slug manually in a browser.

### PITFALL: CF API requires a key for search/discovery — not just downloads

The CurseForge v1 API endpoints **all** require `x-api-key` header authentication. This includes:
- `GET /v1/mods/search` — searching for modpacks by name or slug
- `GET /v1/mods/{id}/files` — listing available files
- Every other v1 endpoint

Without a key, even read-only discovery returns `403 Forbidden: API Key missing or invalid`. You cannot look up a project ID, file ID, or version list via the API without a CF_API_KEY.

**Implication:** Getting a CurseForge API key (from https://console.curseforge.com/) is a **prerequisite for any CurseForge modpack deployment**, not just for downloading. Without one, you can't even determine the correct `CF_SLUG`, project ID, or available file versions programmatically.

### PITFALL: Some major modpacks are CurseForge-exclusive

Modrinth's API is public and requires no auth, making it a good fallback for discovery. However, many major kitchen-sink packs — including **All the Mods 10 (ATM10)** — are **exclusively on CurseForge**. Searching Modrinth for "ATM10" returns only individual add-on mods, not the pack itself. The same applies to ATM9, Enigmatica 9, and other large curated packs.

**Modrinth availability check:**
```bash
curl -s "https://api.modrinth.com/v2/search?query=<pack-name>&facets=%5B%5B%22project_type%3Amodpack%22%5D%5D" | python3 -c "
import json, sys
data = json.load(sys.stdin)
if not data.get('hits'):
    print('Not on Modrinth — CF API key required')
for hit in data.get('hits', []):
    print(f\"  {hit['title']} | {hit['slug']} | MC: {hit.get('versions',[])[:3]}\")
"
```

If Modrinth returns no hits or only unrelated packs, the modpack is CF-exclusive and you need a CF_API_KEY.

### Recommended Discovery Workflow

1. **Get a CF API key** first — it's needed for everything: discovery, file listing, and downloading
2. **Use the API to find the project:** `curl -s -H "x-api-key: $CF_KEY" "https://api.curseforge.com/v1/mods/search?gameId=432&classId=4471&searchFilter=<pack-name>"`
3. **Extract the slug** from the API response to use as `CF_SLUG`
4. **For ATM10 specifically:** the slug is `all-the-mods-10` — use `CF_SLUG: "all-the-mods-10"` or `CF_PAGE_URL: "https://www.curseforge.com/minecraft/modpacks/all-the-mods-10"`

## Client-Side Mod Handling

### PITFALL: Built-in exclusion list cannot be cleared

The itzg image has a **hardcoded list** of client-side mods to exclude (Status Effect Bars, Particular, Welcome Screen, etc.). Setting `CF_EXCLUDE_MODS: ""` does **not** override this built-in list — it only adds to it. The excluded mods will never be downloaded by AUTO_CURSEFORGE.

If a player's client has these mods, they'll see:
```
The server is missing the following mods, remove these mods from your client to join this server:
Status Effect Bars 1.0.3
Particular 1.2.7
```

### PITFALL: Fabric mods in Forge modpacks — manual placement doesn't work

Some CurseForge modpacks include **Fabric client-only mods** in their client distribution (loaded via Sinytra Connector on the client). These mods have `fabric.mod.json` metadata and depend on `fabricloader`. A Forge server **cannot load them** — even if you manually place the JAR in the mods folder, Forge silently ignores it because it looks for `META-INF/mods.toml`, not `fabric.mod.json`.

**Detection — check what loader a mod targets:**
```bash
# Copy the JAR out of the container
docker compose cp minecraft:/data/mods/suspicious-mod.jar /tmp/suspicious-mod.jar

# Check for Forge vs Fabric metadata
python3 -c "
import zipfile
z = zipfile.ZipFile('/tmp/suspicious-mod.jar')
names = [n for n in z.namelist() if 'mods.toml' in n or 'fabric.mod.json' in n]
print(names)
"
```

- `META-INF/mods.toml` → Forge mod (can be manually added to server)
- `fabric.mod.json` → Fabric mod (Forge server cannot load it; remove from client instead)
- Neither → likely a library/dependency, check the mod's CurseForge page

**The fix for Fabric client-only mods:** Delete the JAR from the **client's** mods folder. These are cosmetic mods (HUD overlays, particle effects) that have zero gameplay impact. The modpack author included them for visual flair; the server legitimately can't run them.

### PITFALL: Forge 1.20.1 is stricter about mod matching

Older Forge versions (1.19.x and below) allowed clients with extra client-side mods to connect with a warning. Forge 1.20.1 (47.x) **blocks the connection** if the client's mod list doesn't match the server's exactly. This means:

- Client-only Fabric mods that the server can't load → blocked
- Client-side rendering mods the server excluded → blocked  
- Any mod the server doesn't have → blocked

There's no server-side config to relax this. The only options are: (a) remove the extra mods from the client, or (b) ensure the server has matching Forge-compatible versions of every mod the client has.

### Workaround: Manual mod download (Forge mods only)

**Step 1:** Download the excluded mods from CurseForge or Modrinth.

From CurseForge API (requires CF_API_KEY):
```bash
# Find the mod's project ID and file ID
curl -s -H "x-api-key: ${CF_KEY}" \
  "https://api.curseforge.com/v1/mods/search?gameId=432&slug=status-effect-bars"

# Download from edge CDN: https://edge.forgecdn.net/files/{fileID_first4}/{remaining_fileID}/{filename}
# e.g. file ID 4585394 → https://edge.forgecdn.net/files/4585/394/status-effect-bars-1.0.3.jar
```

From Modrinth API (no auth required):
```bash
# List all versions for a project
curl -s "https://api.modrinth.com/v2/project/particular-reforged/version" | \
  python3 -c "import sys,json; ..."  # filter by game_versions and loaders

# Download from CDN: https://cdn.modrinth.com/data/{project_id}/versions/{version_id}/{filename}
```

**Step 2:** Place the .jar files directly in the mods directory:
```bash
# Compose maps ./minecraft/mods:/data/mods:rw
cp status-effect-bars-1.0.3.jar ./minecraft/mods/
cp particular-1.20.1-Forge-1.2.7.jar ./minecraft/mods/
```

**Step 3:** Restart the server. The manually-placed mods load alongside the auto-downloaded ones.

**⚠️ PITFALL: Client-side mods on the server produce harmless warnings.** Mods that reference `net/minecraft/client/...` classes will log errors like:
```
Attempted to load class net/minecraft/client/renderer/block/model/BlockModel for invalid dist DEDICATED_SERVER
```
These are **non-fatal** — Forge's RuntimeDistCleaner strips client-only code. The server starts and runs fine; the mods just have no server-side effect.

### PITFALL: Forcing re-download after changing exclusions

After modifying `CF_EXCLUDE_MODS`, the AUTO_CURSEFORGE cache prevents re-evaluation. To force a fresh download with the new exclusion list:

```bash
docker compose stop minecraft
rm -rf ./minecraft/data/mods ./minecraft/data/.cache
docker compose up -d minecraft
```

This deletes all downloaded mods and the cache index, triggering a full re-download on next startup.

## Modrinth as Fallback Source

Some mods exist on Modrinth but not CurseForge for specific versions. Particular for 1.20.1 Forge is one example — the CurseForge page only has 1.19.x Forge versions; the 1.20.1+ Forge versions are on Modrinth under "Particular ✨ Reforged".

### Modrinth API Quick Reference

```bash
# Search for a project
curl -s "https://api.modrinth.com/v2/search?query=particular"

# Get project details (game versions, loaders)
curl -s "https://api.modrinth.com/v2/project/particular-reforged"

# List all versions (returns JSON array)
curl -s "https://api.modrinth.com/v2/project/particular-reforged/version"

# Filter by game version and loader
curl -s "https://api.modrinth.com/v2/project/particular-reforged/version?loaders=[\"forge\"]&game_versions=[\"1.20.1\"]"

# Each version has a files array with primary file URL
# Download URL format: https://cdn.modrinth.com/data/{project_id}/versions/{version_id}/{filename}
```

**HTTP headers:** Modrinth API may return empty responses without a proper User-Agent. Set `User-Agent: ModrinthDownloader/1.0` or similar.
