# CouchDB Configuration for Obsidian Self-hosted Live Sync

The default CouchDB Docker image starts in **clustered mode** with **CORS disabled** — both must be fixed for the Obsidian plugin to connect.

## Full local.ini

Place at `./couchdb/etc/local.ini` (mounted to `/opt/couchdb/etc/local.d/` in the container):

```ini
; Single-node mode — required for Self-hosted Live Sync
[couchdb]
single_node = true

; Enable CORS — required for Obsidian plugin to connect
[chttpd]
enable_cors = true
require_valid_user = false

[cors]
origins = *
credentials = true
methods = GET, PUT, POST, HEAD, DELETE
headers = accept, authorization, content-type, origin, referer, x-csrf-token

; Allow persistent connections for real-time sync
[chttpd_auth]
require_valid_user = true
```

## Why each section matters

| Setting | Without it |
|---------|-----------|
| `single_node = true` | CouchDB starts in clustered mode, Live Sync can't create databases |
| `enable_cors = true` | Obsidian's browser-based WebSocket connection is blocked by CORS policy |
| `cors.origins = *` | Only same-origin requests allowed; plugin connects from `app://obsidian.md` |
| `cors.credentials = true` | Auth headers stripped from cross-origin requests |
| `cors.methods` | PUT/DELETE needed for document sync; default only allows GET/POST |
| `chttpd_auth.require_valid_user = true` | Unauthenticated reads of the entire database — defense in depth |

## Verification (user runs these — interactive password prompt)

```bash
# Single-node mode (must show single node, not "cluster")
curl -sk -u admin https://db.oathless.dev/_membership

# CORS enabled (must return "true")
curl -sk -u admin https://db.oathless.dev/_node/_local/_config/chttpd/enable_cors

# CORS origins (must return "*")
curl -sk -u admin https://db.oathless.dev/_node/_local/_config/cors/origins

# All databases (should show vault database after plugin setup)
curl -sk -u admin https://db.oathless.dev/_all_dbs
```

## Obsidian Plugin Setup

**Use manual configuration, not the Setup URI wizard.** The wizard expects a special encoded URI format and will reject a plain URL. Manual config works identically:

1. Install **"Self-hosted Live Sync"** community plugin
2. In plugin settings → Remote Database (manual):
   - **URI:** `https://db.oathless.dev`
   - **Username:** `admin`
   - **Password:** COUCHDB_PASSWORD from `.env`
   - **Database Name:** leave blank (plugin auto-creates it)
   - **Use Internal API:** OFF (going through Caddy reverse proxy)
3. Hit **"Check"** — should confirm connection
4. Enable **End-to-End Encryption** — encrypts notes before they leave the device. Use the **same passphrase on all devices** or synced data is unrecoverable. Write it down.
5. Enable **Obfuscate properties** — hashes file/folder names in the database

**⚠️ First-run warnings are normal.** Messages like "Could not fetch configuration from remote" or "Failed to get preferred tweak values" appear because the database is brand new and doesn't have config documents yet. The plugin writes its config during the first setup cycle. Check CouchDB logs to confirm: if requests show 200/201 status codes, everything is working — proceed to Replicate/Sync.

## Single-Node Mode Output

The `_membership` endpoint returns `"all_nodes":["nonode@nohost"]` in single-node mode. This is correct — "nonode@nohost" means **no cluster is configured**, which is exactly what single-node mode looks like. Do not interpret this as an error.

## Pitfalls

**CouchDB CORS config not picked up:** The container reads from `/opt/couchdb/etc/local.d/*.ini` at startup. After changing the host file, restart the container (`docker compose restart couchdb`). A `caddy reload` is not enough — the config is inside CouchDB, not the reverse proxy.

**CouchDB appends its own settings:** The container may add `uuid` and `[admins]` sections to your `local.ini` on first start. This is normal — CouchDB writes its runtime state into the mounted config file. Don't remove these auto-added sections.

## Architecture: Where the Vault Lives

CouchDB stores **encrypted sync data** — not a readable folder of markdown files. The actual `.md` vault lives on each device's local filesystem:

```
[MacBook]  ←→  [CouchDB on server]  ←→  [Desktop]
 vault.md         (E2E encrypted docs)        vault.md
```

**If the server needs read/write access to the vault** (e.g. Hermes editing notes), the server must have its own Obsidian installation connected to the same CouchDB. On a headless server, use `xvfb` (virtual display) to run Obsidian for initial plugin setup, then the Live Sync plugin handles background sync:

```bash
# Install prerequisites
sudo apt install -y xvfb

# Download and run Obsidian headless for one-time plugin setup
xvfb-run /path/to/Obsidian.AppImage --disable-gpu
```

Once configured, Obsidian doesn't need to stay open — the Live Sync plugin syncs in the background as long as Obsidian is running. Files at `~/obsidian-vault/` are readable/writable by Hermes; changes sync back to all devices via CouchDB.

**⚠️ "Replication complete but vault empty" is normal** on a fresh setup. The vault is empty because no notes have been created yet. Create a note on any device and it syncs to all others.
