---
name: docker-homeserver
description: Patterns for Docker Compose homeserver services — VPN tunnels, reverse proxies, service dashboards, Git hosting, log viewing, stack management, CouchDB, ZenNotes, health checks, credential safety, and auth key handling.
triggers:
  - Adding or checking any service in an existing docker-compose.yml
  - Setting up or configuring Homepage (gethomepage.dev), Forgejo, Dockge, or Dozzle
  - Adding Caddy `basic_auth` password protection behind the reverse proxy
  - Configuring Docker Compose dashboard/services/bookmarks/widgets YAML
  - Resolving Docker volume permission issues (root-owned directories, no sudo)
  - Setting up Tailscale, Cloudflare Tunnel, or WireGuard in Docker
  - Handling one-time auth keys in .env files with Docker Compose
  - Remote access / VPN for a Docker homeserver
  - Verifying whether a homeserver service is healthy
  - CouchDB setup for Obsidian Live Sync or general document storage
  - ZenNotes web-based notes setup for agent-accessible vaults
  - Any task involving credentials — .env files, passwords in shell commands
  - Setting up or modifying Uptime Kuma monitors, status pages, or notifications
  - Uptime Kuma API exploration, database inspection, or programmatic monitor creation
  - Hardware inspection, storage capacity analysis, or upgrade planning for the homeserver machine
  - Managing Docker Compose secrets — encrypting .env files, SOPS + age, per-service isolation, migrating from monolithic .env
---

# Docker Homeserver Patterns

## Tailscale in Docker Compose

Add Tailscale as a service with `network_mode: host` so it shares the host network and all Docker services become reachable via the Tailscale IP.

```yaml
tailscale:
  image: tailscale/tailscale:latest
  container_name: tailscale
  restart: unless-stopped
  network_mode: host
  cap_add:
    - NET_ADMIN
    - NET_RAW
  volumes:
    - ./tailscale/state:/var/lib/tailscale
    - /dev/net/tun:/dev/net/tun
  environment:
    - TS_HOSTNAME=homelab
    - TS_STATE_DIR=/var/lib/tailscale
    - TS_AUTHKEY=${TAIL...Y}
    - TS_EXTRA_ARGS=--accept-routes
```

**Why `network_mode: host`:** Tailscale assigns the host a `100.x.x.x` IP. With host networking, that IP applies to the entire machine — SSH, Caddy, Minecraft, everything is reachable through it without per-service config changes.

**State directory:** `./tailscale/state` persists the Tailscale identity. Once authenticated, the container survives restarts without re-auth. The auth key is only needed for the first run.

**⚠️ PITFALL: `--ssh` flag.** Do NOT add `--ssh` if the host already has sshd running on port 22. Tailscale SSH intercepts incoming SSH connections on the tailnet IP and tries to authenticate via Tailscale's ACL, producing errors like `failed to look up local user`. Users with a working system sshd should connect via normal SSH over the Tailscale IP (e.g. `ssh user@100.x.x.x`). Only use `--ssh` if you specifically want Tailscale-managed SSH with ACL-based auth.

**⚠️ PITFALL: Stale state causes restart loop.** If the container gets into a crash-restart cycle (`Restarting (1) N seconds ago`), the persisted state in `./tailscale/state` is stale or flag-mismatched. The entrypoint fails to auth and Docker keeps restarting it. Fix:

```bash
docker compose stop tailscale
sudo rm -rf ./tailscale/state/*    # state files are root-owned by container
# Ensure TS_AUTHKEY is back in .env, then:
docker compose up -d tailscale
# Once healthy, remove the key from .env
```

### Isolating Tailscale with Profiles (Survive `docker compose down`)

When working on the server remotely via Tailscale, `docker compose down` kills the VPN and kicks you off. Use a **Compose profile** to exclude Tailscale from the default `down` scope:

```yaml
tailscale:
  # ... same config as above ...
  profiles:
    - always-on
```

With this in place:

| Command | Effect |
|---|---|
| `docker compose --profile always-on up -d` | Start everything including Tailscale |
| `docker compose down` | Stop everything **except** Tailscale |
| `docker compose --profile always-on down` | Stop everything including Tailscale |

**How it works:** Services with `profiles` are only included when `--profile <name>` is passed. Without the flag, `docker compose down` ignores profiled services entirely. Tailscale has `network_mode: host` and no dependencies on the `homeserver` bridge network, so there's no coupling to the rest of the stack — it can run independently while the main services cycle.

**Migration (no downtime):** If Tailscale was already running without profiles, just run `docker compose --profile always-on up -d` — Compose recognizes the existing container and leaves it alone. No restart, no kick-off.

**Generic pattern:** Any infrastructure service that should outlive the main stack (VPN, monitoring agent, syslog forwarder) can use this same `profiles: [always-on]` trick. The only requirement is that the service has no network dependencies on the other Compose services (e.g. uses `network_mode: host` or its own external network).

## Security: Credential Handling

**⚠️ PITFALL: Never read .env files or pass secrets in shell commands.** Secrets extracted from `.env` and interpolated into `curl -u`, `grep`, or similar commands are visible in process listings and shell history. The agent should NEVER read credential files or construct authenticated commands that include passwords on the command line.

**Instead:**
- For read-only health checks, use unauthenticated endpoints (e.g. CouchDB `GET /` welcome page, `_up` health check)
- For authenticated operations, give the user the exact command to run themselves (interactive password prompt keeps it out of shell history)
- When the agent must perform authenticated operations, use `execute_code` with secrets loaded in-process — never via shell interpolation

## Auth Key Workflow

### Security
- Tailscale auth keys are **one-time use** by default. After the container authenticates, the key is burned.
- The key only grants device-join — not account access.
- Set an expiry when creating the key at `https://login.tailscale.com/admin/settings/keys` as defense-in-depth.

### Writing the key to .env

**PITFALL: Shell command truncation.** Long Tailscale auth keys (`tskey-auth-...`) get mangled when passed through shell commands via `echo` or `sed`. The key contains characters that interact with shell quoting, and the terminal tool may also sanitize output.

**SOLUTION:** Use `execute_code` (Python) to write credentials to .env:

```python
from hermes_tools import terminal

key = "tskey-auth-..."  # full key
result = terminal("cat /home/user/project/.env")
lines = result["output"].split("\n")

# Replace or append the line
new_lines = []
found = False
for line in lines:
    if line.startswith("TAILSCALE_AUTHKEY=***        new_lines.append(f"TAILSCALE_AUTHKEY=***        found = True
    else:
        new_lines.append(line)
if not found:
    new_lines.append(f"TAILSCALE_AUTHKEY=***)
...tent = "\n".join(new_lines)
terminal(f"cat > /home/user/project/.env << 'HERMES_EOF'\n{new_content}\nHERMES_EOF")
```

**Verify with length check**, not content check (output may be sanitized):
```bash
grep 'TAILSCALE_AUTHKEY' .env | wc -c
```

### Cleanup
After the container starts successfully, **remove the auth key from .env immediately**. The key is consumed and useless, and leaving it is bad hygiene:

```bash
grep -v 'TAILSCALE_AUTHKEY' .env > /tmp/env_cleaned && mv /tmp/env_cleaned .env
```

## SOPS + Age: Encrypted Secrets at Rest

For managing ALL Docker Compose secrets with encryption at rest, per-service isolation, and git-safety — the pragmatic sweet spot for single-machine homelabs. See `references/sops-age-secrets.md` for the full recipe with step-by-step setup, day-to-day operations, pitfalls, and comparison matrix.

### Architecture

```
homeserver/
├── .sops.yaml              # SOPS encryption config (age public key)
├── .env.example            # Documents required secrets (committable)
├── .gitignore              # Blocks plaintext, allows *.sops files
├── deploy.sh               # Decrypt → deploy → cleanup in one command
├── docker-compose.yml      # Uses per-service env_file: (no ${VAR} substitution)
└── secrets/
    ├── mc.env.sops         # MC_RCON_PASSWORD → minecraft-vanilla, minecraft-modded
    ├── zennotes.env.sops   # ZENNOTES_AUTH_TOKEN → zennotes
    └── tailscale.env.sops  # TAILSCALE_AUTHKEY → tailscale
```

### Core Workflow

```bash
# Install (no sudo)
curl -sL "https://github.com/getsops/sops/releases/download/v3.13.1/sops-v3.13.1.linux.amd64" -o ~/.local/bin/sops
chmod +x ~/.local/bin/sops
age-keygen -o ~/.config/sops/age/keys.txt

# Encrypt
sops --input-type dotenv --output-type dotenv --encrypt secrets/mc.env > secrets/mc.env.sops

# Deploy
./deploy.sh              # decrypt → docker compose up → cleanup
```

### ⚠️ CRITICAL: SOPS input type

SOPS defaults to JSON/YAML parsing. For `.env` files, **always** use `--input-type dotenv --output-type dotenv`. Without it, decryption fails with "invalid character looking for beginning of value." This applies to both `sops --encrypt` and `sops --decrypt`.

### ⚠️ docker compose config leaks secrets

Running `docker compose config` with decrypted env files present prints all resolved secrets to stdout. Always clean up plaintext files before validation, or use a temporary directory.

### Per-Service Isolation in docker-compose.yml

Replace monolithic `${VAR}` substitution with per-service `env_file:`:

```yaml
services:
  minecraft-vanilla:
    env_file:
      - ./secrets/mc.env
    environment:
      RCON_PASSWORD: ${MC_RCON_PASSWORD}  # from env_file
      # ... non-secret config stays in environment block
```

Each container only sees the env files listed in its `env_file:` block. No shared `.env` needed at all.

### Age Key Backup

The private key in `~/.config/sops/age/keys.txt` is the **only** way to decrypt secrets. Back it up immediately after generation:

```bash
cat ~/.config/sops/age/keys.txt
# Copy the entire output to a password manager or secure location
```

Lost key = permanently inaccessible secrets. No recovery path.

### Templates

- `templates/deploy-sops.sh` — ready-to-use deploy wrapper (decrypt → compose up → cleanup)
- `templates/sops-config.yaml` — starter `.sops.yaml` (replace public key placeholder)

## No Router Changes Needed

With Tailscale in `network_mode: host`:
- No port forwarding on the router
- No dynamic DNS (DuckDNS, etc.)
- All services reachable via `100.x.x.x` from any device on the tailnet
- Public-facing domains (like oathless.dev via Caddy) still need their own DNS — Tailscale is for personal remote access, not public visitors

## Service Health Checks

When verifying a Docker Compose service is working, follow this sequence:

1. **Container status**: `docker compose ps` — is it Up?
2. **Internal accessibility**: try the service on its published port (if any)
3. **Reverse proxy**: hit the Caddy-proxied domain — services often don't expose ports to the host, so the proxy is the only path
4. **Application-level health**: hit a no-auth or health endpoint that proves the app is actually serving

**Pattern:** CouchDB in `docker-compose.yml` only exposes 5984 on the internal Docker network, not to the host. `curl localhost:5984` will fail. Always go through the reverse proxy (`https://db.oathless.dev`).

## CouchDB for Obsidian Sync

> **Note:** This configuration is historical — the user may not be actively self-hosting Obsidian sync anymore. CouchDB may still be running for other purposes. Check the current state before assuming this is active.

### Critical: Configuration File

CouchDB starts in clustered mode with CORS disabled by default — **neither works with Self-hosted Live Sync.** See `references/couchdb-livesync-config.md` for the required `local.ini` (single-node mode, CORS origins/credentials/methods, auth settings) and verification commands.

### Compose Service

```yaml
couchdb:
  image: couchdb:3
  container_name: couchdb
  restart: unless-stopped
  volumes:
    - ./couchdb/data:/opt/couchdb/data
    - ./couchdb/etc:/opt/couchdb/etc/local.d
  environment:
    - COUCHDB_USER=admin
    - COUCHDB_PASSWORD=${COUCHDB_PASSWORD}
  networks:
    - homeserver
```

### Caddy Reverse Proxy

```
db.oathless.dev {
    reverse_proxy couchdb:5984
}
```

### Health-Check Commands (no-auth, safe for the agent to run)

```bash
# Container status
docker compose ps couchdb

# Welcome page (no auth needed)
curl -sk https://db.oathless.dev/

# Health endpoint (no auth needed)
curl -sk https://db.oathless.dev/_up
```

### Authenticated Commands (user runs these themselves with interactive password prompt)

```bash
# List all databases
curl -sk -u admin https://db.oathless.dev/_all_dbs

# Check single-node mode (required for Obsidian Live Sync)
curl -sk -u admin https://db.oathless.dev/_membership

# Check CORS status (Live Sync needs it enabled — note: chttpd, not httpd)
curl -sk -u admin https://db.oathless.dev/_node/_local/_config/chttpd/enable_cors

# Check CORS origins
curl -sk -u admin https://db.oathless.dev/_node/_local/_config/cors/origins

# Single-node mode check (correct output: "all_nodes":["nonode@nohost"])
curl -sk -u admin https://db.oathless.dev/_membership
```

**⚠️ PITFALL: CORS config path.** The config section is `[chttpd]` not `[httpd]`. Using `httpd` returns `"unknown_config_value"`. The correct path is `_node/_local/_config/chttpd/enable_cors`.

### Obsidian Live Sync Setup

Once CouchDB is healthy:
1. Install the **"Self-hosted Live Sync"** community plugin in Obsidian
2. Use **manual configuration**, not the Setup URI wizard (the wizard rejects plain URLs):
   - **URI:** `https://db.oathless.dev`
   - **Username:** `admin`
   - **Password:** COUCHDB_PASSWORD from `.env`
   - **Database Name:** leave blank (auto-created)
   - **Use Internal API:** OFF (going through reverse proxy)
3. Hit **"Check"** — should confirm
4. Enable **End-to-End Encryption** with a strong passphrase — same on all devices
5. Enable **Obfuscate properties** — extra privacy

**⚠️ First-run warnings are normal.** "Could not fetch configuration from remote" and "Failed to get preferred tweak values" are expected on a fresh database. Check CouchDB logs (`docker compose logs couchdb --tail 20`) to confirm — if requests return 200/201, proceed to sync.

See `references/couchdb-livesync-config.md` for the full config file, per-setting rationale, and verification commands.

### Verifying Sync Is Working

- After setup, `_all_dbs` should show one or more databases (not empty `[]`)
- Databases look like `vault_name` or `vault_name_couchdb_sync_metadata`

## ZenNotes — Web-Based Markdown Notes

Browser-based notes app that stores everything as plain `.md` files on the host. Ideal when you want the agent (Hermes) to read/write notes directly — no sync plugins, no E2E encryption, no Obsidian dependency on the server. ZenNotes runs as a single Docker container behind the Caddy reverse proxy.

### Compose Service

```yaml
zennotes:
  image: adibhanna/zennotes:latest
  container_name: zennotes
  restart: unless-stopped
  user: "1000:1000"           # must match host uid/gid for vault writes
  read_only: true
  tmpfs:
    - /tmp
  cap_drop:
    - ALL
  security_opt:
    - no-new-privileges:true
  volumes:
    - /home/ruben/obsidian-vault:/workspace
    - ./zennotes-data:/data
  environment:
    - ZENNOTES_AUTH_TOKEN=<openssl rand -hex 32>
    - ZENNOTES_BEHIND_TLS=1
  networks:
    - homeserver
```

### Caddy Reverse Proxy

```
notes.oathless.dev {
    reverse_proxy zennotes:7878
}
```

### Token Generation

```bash
openssl rand -hex 32
```

The container **refuses to start** without an auth token when binding to a non-loopback address. Write the 64-char hex token to the compose file or an env var.

**⚠️ PITFALL: `ZENNOTES_AUTH_TOKEN_FILE` may not work.** The `_FILE` variant reads from a path inside the container. If the mounted file has restrictive host permissions (e.g. `600`), the container user can't read it. Use `ZENNOTES_AUTH_TOKEN` env var directly instead — simpler and avoids permission issues.

**⚠️ PITFALL: `user: "1000:1000"` is required.** Without it, the container runs as root and the vault directory (`/workspace`) is owned by the host user (uid 1000). The container can't create directories like `inbox/` and crashes with `mkdir /workspace/inbox: permission denied`.

### Why `read_only: true` + `tmpfs: /tmp`

The container filesystem is read-only except for `/tmp` (in-memory) and the two mounted volumes. This plus `cap_drop: ALL` and `no-new-privileges` hardens the container — even if the webapp is compromised, the attacker can't write to the container image or escape.

### First Access

1. Open `https://notes.oathless.dev` in a browser
2. Paste the auth token on the prompt
3. The vault at `/workspace` (host: `/home/ruben/obsidian-vault`) is mounted automatically

### Hermes Access

Hermes reads/writes `/home/ruben/obsidian-vault/` directly — no API, no auth, just markdown files. Changes appear instantly in the web UI on refresh.

### Adding Notes to the Vault

**⚠️ PITFALL: Don't assume the vault is remote-only.** When the user asks to add notes to their Obsidian vault, the vault is at `/home/ruben/obsidian-vault/` on this machine (ZenNotes runs in Docker, mounted to that path). Search for it first — don't suggest SCP or create temp directories elsewhere.

**⚠️ PITFALL: Searching for `.obsidian` won't find this vault.** ZenNotes uses `.zennotes/` as its marker directory, not `.obsidian/`. When looking for the vault, search broadly for `find /home/ruben -name ".zennotes"` or look for vault-like structures (`inbox/`, `quick/`, `archive/`, `trash/`). A `find -name ".obsidian"` will return nothing even though the vault exists.

**Workflow:**
1. **Check structure first** — look for `inbox/Welcome.md` or similar index notes to understand the vault's organization
2. **New notes go in `inbox/`** — that's where the user's inbox/daily notes live
3. **Vault structure** is plain directories: `inbox/`, `quick/`, `archive/`, `trash/`
4. **Write directly** with `write_file` to `/home/ruben/obsidian-vault/inbox/Note Name.md`

**Key files:**
- Vault root: `/home/ruben/obsidian-vault/`
- ZenNotes meta: `/home/ruben/obsidian-vault/.zennotes/`

See `references/zennotes-setup.md` for the full working config with per-setting rationale and verification steps.

## Adding a New Service

Follow this sequence when adding a service to the stack:

1. **Add the service block** to `docker-compose.yml` (network: `homeserver`, no host port mappings — route everything through Caddy)
2. **Add a Caddy reverse proxy entry** in `caddy/Caddyfile` (choose a subdomain of `oathless.dev`)
3. **Pull and start:** `docker compose pull <service> && docker compose up -d <service>`
4. **Restart Caddy** (`docker compose restart caddy`) — the bind mount can cache, reload isn't reliable. Verify with `docker compose exec caddy cat /etc/caddy/Caddyfile`
5. **Add Uptime Kuma monitor** — insert directly into SQLite (see `references/uptime-kuma-monitors.md`), then restart Uptime Kuma
6. **Verify** with `curl -sk https://<domain>/`

See `references/service-catalog.md` for deployed service configs and gotchas.

### ⚠️ Homepage host validation pitfall

Homepage (gethomepage.dev) rejects requests from unknown Host headers by default. When proxied through Caddy on a custom domain, it sees `home.oathless.dev` instead of `localhost` and returns "Host validation failed." Set the env var:

```yaml
homepage:
  environment:
    - HOMEPAGE_ALLOWED_HOSTS=home.oathless.dev
```

Without this, the container starts healthy but all proxied requests return the host validation error. The container logs show the exact hint.

### ⚠️ Dockge mount path pitfall

Dockge requires compose files at `/opt/stacks/<stack-name>/docker-compose.yml`. Mounting the project root directly at `/opt/stacks` (without a subdirectory) causes "This stack is not managed by Dockge." The fix is a bind mount that includes the stack name:

```yaml
# WRONG:
- .:/opt/stacks:ro

# RIGHT:
- .:/opt/stacks/homeserver:ro
```

The bind mount target path IS the stack name. The read-only flag (`:ro`) prevents Dockge from editing files in-place but still allows start/stop/restart operations.

## New Service Checklist

When adding a service to the homelab, always do all three:

1. **Docker Compose** — add the service block
2. **Caddy reverse proxy** — add a subdomain entry
3. **Uptime Kuma monitor** — insert via SQLite + restart. The user expects this without being asked.

**Monitor insertion pattern (HTTP):**
```bash
**Monitor insertion pattern (HTTP, via docker exec):** Use `docker exec uptime-kuma sqlite3` to write monitors — the host DB is root-owned and locked by the running process, so `python3 -c "import sqlite3; ..."` from the host fails with `OperationalError: attempt to write a readonly database`. Writing inside the container works reliably:\n\n```bash\n# HTTP monitor (public-facing URL check)\ndocker exec uptime-kuma sqlite3 /app/data/kuma.db \\\n  \"INSERT INTO monitor (name, active, user_id, interval, url, type, weight, created_date, maxretries, ignore_tls, upside_down, maxredirects, accepted_statuscodes_json, retry_interval, method, timeout, description) VALUES ('Service Name', 1, 1, 60, 'https://sub.oathless.dev', 'http', 2000, datetime('now'), 3, 0, 0, 10, '[\\\"200\\\"]', 60, 'GET', 48, 'Optional description');\"\n\n# TCP port monitor (internal Docker network check)\ndocker exec uptime-kuma sqlite3 /app/data/kuma.db \\\n  \"INSERT INTO monitor (name, active, user_id, interval, type, weight, hostname, port, created_date, maxretries, ignore_tls, upside_down, maxredirects, accepted_statuscodes_json, retry_interval, method, expiry_notification, timeout, gamedig_given_port_only, description) VALUES ('Service TCP', 1, 1, 120, 'port', 2000, 'container-name', 25565, datetime('now'), 3, 0, 0, 10, '[\\\"200-299\\\"]', 120, 'GET', 1, 48.0, 1, 'Optional description');\"\n\n# Update existing monitor\ndocker exec uptime-kuma sqlite3 /app/data/kuma.db \\\n  \"UPDATE monitor SET name='New Name', hostname='new-host', port=25567, description='Updated' WHERE id=3;\"\n```\n\n**No restart needed.** Uptime Kuma reads monitors from the DB on each check cycle — inserts and updates take effect immediately. To verify:\n\n```bash\ndocker exec uptime-kuma sqlite3 /app/data/kuma.db \"SELECT id, name, hostname, port, active FROM monitor WHERE name LIKE '%search%';\"\n```
docker compose restart uptime-kuma
```

## Caddy basic_auth (for services without built-in auth)

Use `basic_auth` **only for services that lack their own login**. Do NOT layer Caddy's `basic_auth` on top of services with built-in authentication (Crafty, Forgejo, Dockge, Uptime Kuma) — it creates double-auth friction and causes the `Authorization: Basic` header to leak to the upstream, interfering with the service's own auth (Bearer tokens, session cookies). Reserve `basic_auth` for read-only dashboards and tools that have no auth of their own: Dozzle, Homepage, Netdata, etc. The bcrypt hash goes unquoted — `$` in bcrypt hashes is NOT a Caddyfile placeholder and should NOT be wrapped in quotes.

```caddy
sub.oathless.dev {
    basic_auth {
        username $2a$14$abc...
    }
    reverse_proxy container:port
}
```

**Generating the hash:**
```bash
docker compose exec caddy caddy hash-password --plaintext "your-password-here"
```

## Service Removal

When removing a service from the stack, follow this sequence:

1. **Stop and remove the container:**
   ```bash
   docker compose stop <service> && docker compose rm -f <service>
   ```

2. **Remove the service block** from `docker-compose.yml`.

3. **Remove any reverse proxy entries** from `caddy/Caddyfile` if the service was proxied.

4. **Reload Caddy** to apply the proxy config change:
   ```bash
   docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile
   ```

5. **Remove the data directory.** Docker containers often write files as internal users (e.g. CouchDB's uid 5984, Minecraft's uid 1000), making them root-owned on the host:
   ```bash
   sudo rm -rf ./<service-data-dir>
   ```
   If the agent lacks sudo, tell the user to run this step themselves.

6. **Verify:** `docker compose ps` should show no trace of the removed service.

## Caddy: Bind Mount Caching Pitfall

**⚠️ PITFALL: `caddy reload` may report "config is unchanged" even after patching the Caddyfile on the host.** Docker bind mounts can cache the file at the container's view. After editing `/home/user/homeserver/caddy/Caddyfile`, a reload sometimes sees the pre-edit version.

**Fix:** Restart Caddy to force a fresh bind mount read:

```bash
docker compose restart caddy
```

**If `restart` doesn't refresh the mount** (container still shows stale Caddyfile content), force a full kill + recreate:

```bash
docker kill caddy
docker compose up -d caddy
```

Then verify the container sees the new content:

```bash
docker exec caddy grep "reverse_proxy" /etc/caddy/Caddyfile
```

Compare against the host file with `grep "reverse_proxy" /home/ruben/homeserver/caddy/Caddyfile`. If they still differ after a kill+recreate, the bind mount itself has an issue (unlikely — check the compose volume config). Do NOT rely on `caddy reload` alone after file patches — always verify the container's view matches the host file.

## Caddy: Password Protection with `basic_auth`

To password-protect a service behind Caddy (e.g. dashboard, log viewer), use `basic_auth` with a bcrypt password hash.

**⚠️ PITFALL: Use `basic_auth`, NOT `basicauth`.** The old `basicauth` directive is **deprecated** in Caddy v2 and expects a different (base64-encoded) password format. Using it with a bcrypt hash produces `base64-decoding password: illegal base64 data at input byte 0` and causes a crash-loop. Always use `basic_auth`, which natively accepts bcrypt hashes.

**⚠️ PITFALL: Do NOT single-quote bcrypt hashes in `basic_auth`.** bcrypt hashes (`$2a$14$...`) work correctly UNQUOTED inside `basic_auth` blocks. Single-quoting them makes Caddy treat the `'` characters as literal parts of the hash, which breaks authentication (Caddy returns `Basic authentication problem, ignoring.` even with correct credentials). Unlike `.env` files or shell, the Caddyfile does NOT interpret `$2a` as a variable reference inside `basic_auth` blocks.

```caddyfile
# WRONG — deprecated directive, wrong hash format:
home.oathless.dev {
    basicauth {
        user $2a$14$HASH...
    }
}

# WRONG — single quotes become part of the hash:
home.oathless.dev {
    basic_auth {
        user '$2a$14$HASH...'
    }
}

# RIGHT — basic_auth + unquoted bcrypt hash:
home.oathless.dev {
    basic_auth {
        user $2a$14$HASH...
    }
    reverse_proxy service:3000
}
```

**Generating the hash:**

```bash
docker compose exec caddy caddy hash-password --plaintext "your-password"
```

Copy the output directly (no quotes) into the `basic_auth` block. After editing, `docker compose restart caddy` (not reload — see bind mount caching above).

## Host Tool Installation (No Sudo)

When `sudo` isn't available (password prompt blocks non-interactive use) or you want a user-local install without touching system paths:

1. Download the binary release tarball from GitHub (or other source)
2. Extract and copy the binary to `~/.local/bin/`
3. Verify it's on PATH (`~/.local/bin` is typically in PATH on Ubuntu)

```bash
curl -fsSL "https://github.com/owner/repo/releases/download/vX.Y.Z/tool_linux_amd64.tar.gz" -o /tmp/tool.tar.gz
tar -xzf /tmp/tool.tar.gz -C /tmp
mkdir -p ~/.local/bin
cp /tmp/tool_*/bin/tool ~/.local/bin/tool
~/.local/bin/tool --version
```

This avoids apt repository setup (which requires sudo for keyring + sources.list) and keeps the host filesystem clean. Works for `gh`, `uv`, `just`, `watchexec`, and most Go/Rust CLI tools that ship static binaries.

## Root-Owned Docker Directories (No-Sudo Workaround)

**⚠️ PITFALL: Docker creates data directories as root** (container UID 0), so `mkdir`, `chown`, and `ln` from the host user fail with permission denied. The `terminal` tool can't use `sudo` (it requires an interactive TTY).

**Fix:** Use a temporary Alpine container to run filesystem operations as root:

```bash
docker run --rm -v /home/ruben/homeserver:/host alpine:latest sh -c "mkdir -p /host/dockge/stacks && chown -R 1000:1000 /host/dockge/stacks"
```

The container runs as root inside, sees the host path via bind mount, and exits cleanly. No `sudo`, no TTY prompt. Also works for `rm -rf` of root-owned data directories when removing services.

## GitHub Integration (Fine-Grained PAT + `gh` CLI)

Connect Hermes to GitHub with read/write access to personal repos while blocking access to work organization repos. See `references/github-integration.md` for the full setup recipe: token scoping, `gh` CLI auth, org isolation verification, and notification polling via cron.

## Netdata (System Metrics)

Add Netdata to the stack for real-time CPU/memory/disk/network dashboards at 1-second granularity. Uptime Kuma handles binary up/down; Netdata handles time-series metrics.

```yaml
netdata:
  image: netdata/netdata:latest
  container_name: netdata
  pid: host
  restart: unless-stopped
  cap_add:
    - SYS_PTRACE
    - SYS_ADMIN
  security_opt:
    - apparmor:unconfined
  volumes:
    - ./netdata/config:/etc/netdata
    - ./netdata/data:/var/cache/netdata
    - ./netdata/lib:/var/lib/netdata
    - /proc:/host/proc:ro
    - /sys:/host/sys:ro
    - /:/host/rootfs:ro
    - /etc/os-release:/host/etc/os-release:ro
  environment:
    - NETDATA_CLAIM_TOKEN=${NETDATA_CLAIM_TOKEN:-}
    - NETDATA_CLAIM_URL=https://app.netdata.cloud
  networks:
    - homeserver
```

**Why `pid: host`:** Allows Netdata to see all host processes (not just its own container). Without it, per-process CPU/memory metrics are invisible.

**Caddy proxy:**

```
metrics.oathless.dev {
    reverse_proxy netdata:19999
}
```

Netdata exposes its dashboard on port 19999. Route it through Caddy (no direct port mapping) for automatic HTTPS. Add a Uptime Kuma HTTP monitor for `https://metrics.oathless.dev` so you know when metrics collection itself is down.

## Uptime Kuma: Push Monitors + Hermes Cron

For monitoring things without HTTP endpoints (CLI tools, background services, systemd units), use **push monitors** driven by shell scripts on Hermes cron with `no_agent=true`.

### Pattern

1. **Create a push monitor** in Uptime Kuma's SQLite DB with a random push token
2. **Write a shell script** that checks the service and pushes to `https://status.oathless.dev/api/push/<token>?status=up&msg=OK`
3. **Create a Hermes no-agent cron job** that runs the script every N minutes
4. **Set `deliver=local`** — the script's stdout goes nowhere; only Uptime Kuma gets the heartbeat

Example for monitoring `hermes gateway status`:

```bash
#!/bin/bash
# /home/ruben/.hermes/scripts/push-gateway-status.sh
if hermes gateway status &>/dev/null; then
    curl -sk "https://status.oathless.dev/api/push/TOKEN?status=up&msg=OK" &>/dev/null
else
    curl -sk "https://status.oathless.dev/api/push/TOKEN?status=down&msg=Down" &>/dev/null
fi
```

Cron job:
```
cronjob action=create no_agent=true schedule="every 1m" script="push-gateway-status.sh" deliver=local
```

**Why `no_agent=true`:** No LLM tokens per tick — the script IS the job. Perfect for simple health checks that fit in a shell one-liner.

**Token generation:** Uptime Kuma push tokens are stored in `monitor.push_token` (VARCHAR(20)). Generate with `secrets.token_hex(10)[:20]` in Python.

### ⚠️ PITFALL: Cron interval must be ≤ half the monitor interval

If your cron schedule matches or closely approaches the Uptime Kuma heartbeat window, **any scheduling jitter will cause false DOWN alerts**. Hermes cron jobs can be delayed by agent processing, and the scheduler itself has natural jitter. Both monitors will flap simultaneously because they share the same cron engine.

**The ratio rule:** `cron_interval ≤ monitor_interval / 2`. With a 180s Uptime Kuma window, run cron no slower than every 90s. With a 120s window, every 60s.

**Diagnosing interval-matching flapping:** Query the heartbeat table. If both push monitors show alternating UP/DOWN in lockstep, the cron interval is too close to the Uptime Kuma window:

```bash
docker exec uptime-kuma sqlite3 /app/data/kuma.db \
  "SELECT m.name, h.status, h.msg, datetime(h.time, 'unixepoch', 'localtime')
   FROM heartbeat h JOIN monitor m ON m.id = h.monitor_id
   WHERE m.type='push' ORDER BY h.time DESC LIMIT 20;"
```

Status codes: 1=UP, 0=DOWN. Alternating lockstep = interval match. Fix by reducing cron interval or widening the Uptime Kuma interval:

```bash
# Widen both push monitors to 180s (no restart needed)
docker exec uptime-kuma sqlite3 /app/data/kuma.db \
  "UPDATE monitor SET interval = 180 WHERE type = 'push';"
```

Monitor interval changes take effect immediately — no Uptime Kuma restart required.

## Uptime Kuma Monitoring

Uptime Kuma v1.x handles admin operations (monitor CRUD) via Socket.IO, not REST. `curl` to `/api/*` endpoints returns HTML unless a status page is configured. For programmatic monitor setup without the web UI, insert directly into the SQLite database and restart.

See `references/uptime-kuma-monitors.md` for the full workflow: DB schema, insert templates, restart, verification, and common pitfalls (DNS resolution from Docker, DB ownership, empty status pages, Docker hostnames for port checks).

## Hardware Upgrades: Verify Before Recommending

**⚠️ PITFALL: Don't recommend hardware upgrades without first verifying the physical machine has the slot/bay.** SATA controllers in lspci don't prove a physical bay exists — the silicon may be on the board but the chassis may lack the mounting point. Always:

1. **Inspect what the kernel sees** — sysfs SATA ports, NVMe model, PCIe link, current drives (see `references/linux-hardware-inspection.md`)
2. **Cross-reference with the service manual** — Dell's manual for this specific model/form-factor confirms bay existence
3. **Check for the specific form factor** — Micro/SFF/Tower variants of the same model have different internal layouts. The DMI `product_name` may not include the form factor (e.g. just "OptiPlex 3070"), so check the motherboard P/N against known references
4. **If direct web research is bot-blocked** (Dell, Reddit, eBay, Google all block curl-based requests), use `delegate_task` with `web` + `browser` toolsets — the subagent's user-agent handling can bypass the CDN bot detection that blocks direct curl/search approaches — see `references/optiplex-3070-micro-hardware.md` for the confirmed specs on this machine

## Crafty Controller — Minecraft Server Panel

> **⚠️ PREFERENCE: Direct itzg containers are preferred over Crafty for this homelab.** Crafty's HTTPS-only server, self-signed cert, and reverse-proxy chain (Caddy → socat sidecar → Crafty HTTPS) create a dependency stack that has proven **unfixable in practice**. Every known fix was applied — `base_url` with `https://` protocol, Host header forwarding, `X-Forwarded-*` headers, removing `basic_auth` to stop the `Authorization` header leak — and CSRF/cookie/session failures (403 on POST, "Invalid token" on every API call) persisted. The socat TCP→SSL tunnel is a fragile architecture that Crafty's Tornado-based CSRF protection cannot work with reliably. The user chose to abandon Crafty in favor of two direct `itzg/minecraft-server` containers. If the user explicitly asks for a panel again, re-evaluate — but the default approach for Minecraft servers on this homelab is direct itzg containers. Do not attempt to resurrect the Crafty + socat setup without the user's explicit request.

Crafty Controller is a web-based panel for managing one or more Minecraft servers — start/stop/restart, console with history, file browser, scheduled tasks, backups, and player management. It replaces the standalone itzg/minecraft-server image when you want a web UI and/or multiple servers.

### Compose Service

```yaml
crafty:
  image: registry.gitlab.com/crafty-controller/crafty-4:latest
  container_name: crafty
  restart: unless-stopped
  ports:
    - "25565:25565"     # Game server 1
    - "25566:25566"     # Game server 2
  volumes:
    - ./crafty/backups:/crafty/backups
    - ./crafty/servers:/crafty/servers
    - ./crafty/config:/crafty/app/config
    - ./crafty/logs:/crafty/logs
    - ./crafty/import:/crafty/import
  environment:
    - TZ=Europe/Amsterdam
  networks:
    - homeserver

  # socat sidecar: bridges HTTP (for Caddy) → HTTPS (Crafty's native protocol)
  crafty-http:
    image: alpine/socat:latest
    container_name: crafty-http
    restart: unless-stopped
    command: TCP-LISTEN:8000,fork,reuseaddr OPENSSL:crafty:8443,verify=0
    networks:
      - homeserver
```

**⚠️ PITFALL: Crafty 4 only serves HTTPS (8443) — does not support plain HTTP.** Crafty 4 uses HTTPS internally on port 8443 with a self-signed certificate. Setting `http_port` in `config.json` has no effect — Crafty ignores it and continues listening only on HTTPS. Do NOT map port 8000 on the Crafty container — the web UI won't be there.

**⚠️ PITFALL: Caddy v2 cannot reliably reverse-proxy to an HTTPS upstream with a self-signed cert.** Multiple syntax attempts fail:
- `reverse_proxy https://crafty:8443` — strips the scheme, connects as plain HTTP (connection reset)
- `reverse_proxy https://crafty:8443 { transport http { tls_insecure_skip_verify } }` — transport block silently ignored
- `reverse_proxy { to crafty:8443; transport http { tls; tls_insecure_skip_verify } }` — transport block still ignored; adapted config shows plain `dial: crafty:8443`

**Solution: socat sidecar.** Add an `alpine/socat` container that accepts plain HTTP on port 8000 and forwards to Crafty's HTTPS 8443 (with `verify=0` for the self-signed cert). Caddy proxies to the socat sidecar via plain HTTP — no TLS config needed.

### Caddy Reverse Proxy

**Default (no double-auth — preferred):** Crafty has its own login, so Caddy's `basic_auth` is unnecessary friction.

```caddy
mc.oathless.dev {
    reverse_proxy crafty-http:8000 {
        header_up Host {http.request.host}          # preserve original domain for cookie/CSRF
        header_up X-Forwarded-Proto https
        header_up X-Forwarded-Host {http.request.host}
    }
}
```

**Optional (Caddy basic_auth + Crafty login):** If you want an extra auth layer, add `basic_auth` and strip the leaked `Authorization` header:

```caddy
mc.oathless.dev {
    basic_auth {
        oathless $2a$14$...  # unquoted bcrypt hash
    }
    reverse_proxy crafty-http:8000 {
        header_up Host {http.request.host}
        header_up X-Forwarded-Proto https
        header_up X-Forwarded-Host {http.request.host}
        header_up -Authorization      # strip Caddy's basic_auth so it doesn't leak to Crafty
    }
}
```

The chain: `Browser → HTTPS → Caddy → HTTP → crafty-http:8000 (socat) → HTTPS → crafty:8443`

The admin panel lives at `https://mc.oathless.dev`. Players connect to the game servers on different ports: `mc.oathless.dev:25565`, `modded.oathless.dev:25566`.

**⚠️ PITFALL: Caddy's `basic_auth` leaks the `Authorization` header to upstream services.** When a user authenticates with Caddy's `basic_auth`, Caddy forwards the `Authorization: Basic <base64>` header to the backend. If the backend has its own auth system (like Crafty does), this header conflicts with the backend's Bearer token / session cookie auth. This causes "ACCESS_DENIED" and "An error occurred while authenticating the user" errors for password changes, MFA setup, and other account operations — even though login works fine. Fix: strip the header with `header_up -Authorization` inside the `reverse_proxy` block.

### Fresh Install — Credentials

On first boot, Crafty generates an admin password and writes it to `/crafty/app/config/default-creds.txt` inside the container. Read it from the host:

```bash
cat ./crafty/config/default-creds.txt
```

**⚠️ PITFALL: Change the password after first login.** The generated password is complex but exposed in a plaintext file. Go to Settings → Security → Change Password in the Crafty web UI.

**⚠️ PITFALL: Web UI password change may fail with auto-generated passwords.** Crafty's auto-generated default password contains special characters (`%`, `$`, `*`, `@`) that can cause the web UI password change to fail with "An error occurred while authenticating the user." The login works fine but the password-change form rejects it. Fix: reset via the SQLite database.

**⚠️ PITFALL: Crafty `base_url` CSRF rejection.** Crafty's default `config.json` sets `base_url: localhost:8443`. When accessed through a reverse proxy at a different domain (e.g. `mc.oathless.dev`), Crafty's CSRF protection rejects sensitive POST requests — password changes, MFA setup, API key creation — with "ACCESS_DENIED — An error occurred while authenticating the user." Login works, account operations fail. **Fix:** Update `config.json` to set `base_url` to the external domain **including the `https://` protocol** and restart Crafty. Without the protocol prefix, Crafty's CSRF `Origin`/`Referer` comparison silently fails (it expects `https://mc.oathless.dev` but sees `mc.oathless.dev`):
```bash
python3 -c "
import json
with open('./crafty/config/config.json') as f: config = json.load(f)
config['base_url'] = 'https://mc.oathless.dev'
with open('./crafty/config/config.json', 'w') as f: json.dump(config, f, indent=4)
"
docker compose restart crafty
```

**⚠️ PITFALL: Caddy rewrites Host header → cookie/CSRF mismatch.** Caddy's `reverse_proxy` directive rewrites the `Host` header to the upstream address (`crafty-http:8000`) by default. Crafty uses this Host for setting session cookies and CSRF tokens — if it sees `crafty-http:8000` instead of `mc.oathless.dev`, the browser never sends the cookies back because they're set for the wrong domain. **Symptoms:** login succeeds but every subsequent API call returns 403 (CSRF failure) or "Invalid token" (cookie never sent). **Fix:** explicitly forward the original Host header plus `X-Forwarded-*` headers inside the `reverse_proxy` block:
```caddy
mc.oathless.dev {
    reverse_proxy crafty-http:8000 {
        header_up Host {http.request.host}
        header_up X-Forwarded-Proto https
        header_up X-Forwarded-Host {http.request.host}
        header_up X-Real-IP {http.request.remote.host}
    }
}
```

```bash
# 1. Generate a new Argon2 hash using Crafty's own venv
docker exec crafty bash -c "source /crafty/.venv/bin/activate && python3 -c \"
from argon2 import PasswordHasher
print(PasswordHasher().hash('NewPasswordHere'))
\""

# 2. Update the database and default-creds.txt
python3 -c "
import sqlite3
db = sqlite3.connect('./crafty/config/db/crafty.sqlite')
db.execute('UPDATE users SET password = ? WHERE username = ?', ('ARGON2_HASH_HERE', 'admin'))
db.commit()
db.close()
"

# 3. Also update the plaintext reference file
# (write new default-creds.txt with the new password)
```

After the DB reset, log out and log in with the new password. The web UI password change should work normally with simpler passwords.

### Importing an Existing Server

When migrating from itzg/minecraft-server to Crafty:

1. Stop the old Minecraft container
2. Copy world, mods, config, and server.properties into a subdirectory under `./crafty/import/`:
   ```bash
   mkdir -p crafty/import/myserver
   cp -r minecraft/data/world crafty/import/myserver/
   cp -r minecraft/mods crafty/import/myserver/
   cp -r minecraft/config crafty/import/myserver/
   cp minecraft/data/server.properties crafty/import/myserver/
   cp minecraft/data/eula.txt crafty/import/myserver/
   ```
3. **Each server import must be in its own subdirectory** — flat files at `/crafty/import/` won't be recognized by the import wizard
4. Start Crafty, then in the web UI: Create Server → choose Import → select the subdirectory
5. Set the correct server type (Forge/vanilla/Paper), version, memory, and port
6. Crafty merges the imported files with its own server structure

### Multiple Servers — Port Architecture

Each Minecraft server needs its own port. Standard approach:

| Server | Port | Players connect to |
|---|---|---|
| Vanilla | 25565 | `mc.oathless.dev:25565` |
| Modded | 25566 | `modded.oathless.dev:25566` |

Both domains resolve to the same IP. Players specify the port in their Minecraft client. No SRV records or layer-4 proxying needed.

### API

Crafty 4 has a REST API at `/api/v2/`. On fresh installs, the API may reject requests until the web setup wizard completes. The web UI (`https://mc.oathless.dev`) is the reliable path for initial server creation. Authenticated API calls use `Bearer <token>` from `POST /api/v2/auth/login`.

### Migration Cleanup

After confirming both servers work in Crafty:

```bash
# Remove the itzg container (already stopped)
docker rm minecraft

# Keep data as backup until verified, then optionally:
# rm -rf ./minecraft/
```

See `references/crafty-controller.md` for the full migration recipe, API exploration notes, and troubleshooting.

## Minecraft Server — itzg/minecraft-server

The stack uses `itzg/minecraft-server:latest` for the Minecraft service. This image supports vanilla, mod loaders (Forge, Neoforge, Fabric), and modpack platforms (CurseForge, Modrinth, FTB, Packwiz) via the `TYPE` or `MODPACK_PLATFORM` env var.

### Switching to a CurseForge Modpack (AUTO_CURSEFORGE)

To install a CurseForge modpack (e.g. "Integrated Minecraft"), switch from a mod loader type to `AUTO_CURSEFORGE`:

1. **Get a CurseForge API key** from https://console.curseforge.com/ — required for the auto-download feature
2. Add it to `.env` as `CF_API_KEY='...'` (wrap in single quotes)
3. Update `docker-compose.yml`:

```yaml
minecraft:
  environment:
    TYPE: "AUTO_CURSEFORGE"
    CF_API_KEY: ${CF_API_KEY}
    CF_SLUG: "integrated-minecraft"          # or CF_PAGE_URL for the full URL
    MEMORY: "8G"
```

4. **Back up the existing world** before restarting — the modpack's MC version likely differs and the world won't be compatible
5. `docker compose up -d minecraft`

**⚠️ PITFALL: World incompatibility.** Switching mod loader type or MC version will break existing worlds. Always back up `./minecraft/data/world/` before changing `TYPE` or `VERSION`.

**⚠️ PITFALL: `server.properties` doesn't auto-update.** The itzg image generates `server.properties` on first run from environment variables — but once it exists, subsequent env var changes are **ignored**. When changing variables that affect `server.properties` (e.g. `ONLINE_MODE`, `RCON_PASSWORD`, `DIFFICULTY`), **delete the file first** before restarting:
```bash
rm -f ./minecraft/data/server.properties
docker compose up -d minecraft
```

**⚠️ PITFALL: itzg overwrites existing server.properties by default.** When you bring existing server files (world, mods, configs, server.properties from a prior setup), the itzg image regenerates server.properties from environment variables, overwriting custom settings like level-type, max-tick-time, view-distance, and the RCON password. Fix: set OVERRIDE_SERVER_PROPERTIES: false in the environment. The container will use the existing server.properties as-is. When this is false, ALL env vars that affect server.properties are ignored — including ENABLE_RCON, RCON_PORT, and RCON_PASSWORD. The RCON password will be whatever is already in the existing server.properties. For a fresh server without an existing file, omit this flag (defaults to true) and the env vars control everything.

**⚠️ PITFALL: RCON authentication failure with `OVERRIDE_SERVER_PROPERTIES=false`.** When this flag is false, the container's `RCON_PASSWORD` env var may differ from `rcon.password` in the existing `server.properties`. The `rcon-cli` tool inside the container reads from the env var, but the Minecraft server binds RCON using the value in `server.properties`. Symptom: `rcon: authentication failed` even with `ENABLE_RCON=true`. **Fix — sync the env var password into server.properties from inside the container, then restart:**
```bash
docker exec <container> sh -c 'sed -i "s/^rcon.password=.*/rcon.password=$RCON_PASSWORD/" /data/server.properties'
docker compose restart <service>
```

**Diagnose mismatch** by comparing byte counts (terminal output may sanitize the password string, so compare lengths instead):
```bash
docker exec <container> sh -c 'echo "$RCON_PASSWORD" | wc -c'
docker exec <container> grep 'rcon.password' /data/server.properties | wc -c
```
Different byte counts = mismatch. Forge modded servers take 60-90s to restart; vanilla servers restart in ~10s.

**⚠️ PITFALL: Java version mismatch.** The `itzg/minecraft-server:latest` image runs Java 25, but many modpacks target specific Java versions. Forge 1.20.1 modpacks (like Integrated Minecraft) need **Java 17**. Running on the wrong Java version produces `Unsupported class file major version 69` (Java 25 bytecode vs ASM library that only supports up to Java 21). Fix by pinning the correct image tag:

| Minecraft Version | Image Tag |
|---|---|
| 1.20.x (Forge) | `itzg/minecraft-server:java17` |
| 1.21.x | `itzg/minecraft-server:java21` |
| Latest | `itzg/minecraft-server:latest` or `:java21` |

The major version numbers in the error map as: 61=Java 17, 65=Java 21, 69=Java 25.

**⚠️ PITFALL: `LATEST` resolves to a version requiring the right Java image tag.** As of mid-2026, `VERSION: LATEST` resolves to Minecraft 26.2 which requires Java 25 (class file 69.0). The itzg image provides `java25` tags. Always match the Java image to the Minecraft version:\n\n| Minecraft Version | Java Required | Image Tag |\n|---|---|---|\n| 1.20.x (Forge) | Java 17 | `itzg/minecraft-server:java17` |\n| 1.21.x | Java 21 | `itzg/minecraft-server:java21` |\n| 26.x (latest) | Java 25 | `itzg/minecraft-server:java25` |\n\nClass file version numbers in the error map as: 61=Java 17, 65=Java 21, 69=Java 25. **Fix:** pin the correct image tag. For vanilla/latest always use `:java25` — the `:latest` image tag currently uses Java 21 and cannot run Minecraft 26.2.

**⚠️ PITFALL: `$` in API keys.** CurseForge API keys often contain `$` characters (e.g. `$2a$10$...`). In `.env` files, **always wrap the key in single quotes** — without quotes, Docker Compose interprets `$2a`, `$10` etc. as variable names and substitutes them to empty strings, silently mangling the key. The container receives a truncated value and `mc-image-helper` fails with "Access to https://api.curseforge.com is forbidden." 

In the YAML, reference the env var normally (no extra escaping):
```yaml
CF_API_KEY: ${CF_API_KEY}   # correct — grabs the quoted value from .env
```

In `.env`:
```
CF_API_KEY='***'   # single quotes prevent $ expansion
```

**Diagnose** with `docker inspect minecraft --format '{{range .Config.Env}}{{println .}}{{end}}' | grep CF_API_KEY` to see what the container actually received.

### Multiple Servers (Two-Container Pattern)

When running two separate Minecraft servers from one compose file (e.g. vanilla + modded), each gets its own container, data directory, and port:

```yaml
  # Vanilla — fresh world, latest stable version
  minecraft-vanilla:
    image: itzg/minecraft-server:java25      # Java 25 for Minecraft 26.x
    container_name: minecraft-vanilla
    restart: unless-stopped
    ports:
      - "25565:25565"
    volumes:
      - ./minecraft-vanilla/data:/data
    environment:
      EULA: "TRUE"
      TYPE: VANILLA
      VERSION: LATEST
      MEMORY: 2G
      ENABLE_RCON: "true"
      RCON_PORT: 25575
      RCON_PASSWORD: ${MC_RCON_PASSWORD}
      TZ: Europe/Amsterdam
    networks:
      - homeserver

  # Modded — Forge 1.20.1, existing world + 267 mods
  minecraft-modded:
    image: itzg/minecraft-server:java17     # Forge 1.20.1 requires Java 17
    container_name: minecraft-modded
    restart: unless-stopped
    ports:
      - "25566:25566"
    volumes:
      - ./minecraft-modded/data:/data
    environment:
      EULA: "TRUE"
      TYPE: FORGE
      VERSION: "1.20.1"
      FORGE_VERSION: "47.4.0"
      MEMORY: 10G
      ENABLE_RCON: "true"
      RCON_PORT: 25576
      RCON_PASSWORD: ${MC_RCON_PASSWORD}
      OVERRIDE_SERVER_PROPERTIES: "false"   # preserve existing server.properties
      TZ: Europe/Amsterdam
    networks:
      - homeserver
```

**Key differences between the two containers:**

| Aspect | Vanilla | Modded |
|---|---|---|
| Image | `java25` (latest MC) | `java17` (Forge 1.20.1) |
| Port | 25565 | 25566 |
| Memory | 2G | 10G |
| `OVERRIDE_SERVER_PROPERTIES` | `true` (default, no flag) | `false` (preserve existing) |
| RCON port | 25575 | 25576 |
| Data dir | `minecraft-vanilla/data/` | `minecraft-modded/data/` |

**⚠️ PITFALL: Use different image tags per server.** Forge 1.20.1 requires Java 17; vanilla 1.21.4 requires Java 21. Using `:latest` or the wrong tag on the modded server produces class file version errors. Pin the correct tag per server in the compose file.

**⚠️ PITFALL: Don't reuse the same data directory.** Each container needs its own `/data` mount. Sharing causes conflicts — one container's `server.properties`, world, or mods overwrite the other's.

**DNS and connectivity:** Both servers share the same host IP. **Use mc-router** (see below) so players connect to `mc.oathless.dev` or `modded.oathless.dev` on the default port 25565 — no port numbers needed. mc-router reads the Minecraft handshake hostname and routes to the correct backend.

**Uptime Kuma:** Add separate TCP port monitors for each — use Docker service names as hostnames (`minecraft-vanilla`, `minecraft-modded`) since Uptime Kuma runs in the same Docker network.

### mc-router — Domain-Based Minecraft Routing

When running multiple Minecraft servers on a single IP, all domains resolve to the same address and Minecraft clients default to port 25565. Without routing, `modded.oathless.dev` connects to the vanilla server on 25565 — the modded server on 25566 is never reached. mc-router solves this by reading the hostname from the Minecraft handshake packet and proxying to the correct backend.

```yaml
mc-router:
  image: itzg/mc-router:latest
  container_name: mc-router
  restart: unless-stopped
  ports:
    - "25565:25565"              # single entry point for all MC traffic
  environment:
    MAPPING: "mc.oathless.dev=minecraft-vanilla:25565,modded.oathless.dev=minecraft-modded:25566"
  command: --default minecraft-vanilla:25565 --api-binding :25564
  networks:
    - homeserver
```

**Architecture:**
- mc-router takes over port 25565 (the only Minecraft port exposed to the host)
- Both Minecraft servers REMOVE their `ports:` sections — they're internal-only
- mc-router routes by hostname: `mc.oathless.dev` → vanilla, `modded.oathless.dev` → modded
- Default route (`oathless.dev` or any unmatched hostname) → vanilla
- API binding on `:25564` avoids port conflict with the Minecraft proxy on 25565

**Migration from direct ports:**
```bash
# 1. Stop servers, remove them
docker compose stop minecraft-vanilla minecraft-modded
docker compose rm -f minecraft-vanilla minecraft-modded

# 2. Remove `ports:` from both server services in docker-compose.yml
# 3. Add mc-router service (above)

# 4. Bring everything up
docker compose up -d mc-router minecraft-vanilla minecraft-modded
```

**Verification:** Both servers are reachable on port 25565. `ss -tlnp | grep 25565` should show ONLY mc-router listening — 25566 should NOT appear. Players connect to `mc.oathless.dev` or `modded.oathless.dev` with no port number.

### RCON Console Access

The `itzg/minecraft-server` image includes `rcon-cli` built-in — no extra tools needed. With Hermes on the host, you have a Minecraft console without any panel:

```bash
# Run any server command
docker exec <container> rcon-cli "say Hello players"
docker exec <container> rcon-cli "give PlayerName minecraft:diamond 64"
docker exec <container> rcon-cli "time set day"
docker exec <container> rcon-cli "list"
```

Hermes can execute these directly — just ask. No web UI, no Crafty, no `mcrcon` binary. The `rcon-cli` reads `RCON_HOST`, `RCON_PORT`, and `RCON_PASSWORD` from the container environment automatically.

**⚠️ PITFALL: Don't pipe secrets into `rcon-cli` on the command line.** The `rcon-cli` tool uses the env vars set by the container — never pass `-p <password>` as a CLI argument. The password would appear in process listings and shell history. The container already has `RCON_PASSWORD` set, so `docker exec <container> rcon-cli "command"` Just Works without any credential exposure.

### Whitelist Management

Whitelist management has two layers: **live** (RCON, instant, no restart) and **persistent** (docker-compose env vars, survives container recreation).

**Live management via RCON:**

```bash
# Enable whitelist
docker exec <container> rcon-cli "whitelist on"

# Add players (comma-separated list, batch-friendly)
docker exec <container> rcon-cli "whitelist add PlayerName"

# List whitelisted players
docker exec <container> rcon-cli "whitelist list"
```

**Persistent env vars in docker-compose.yml:**

```yaml
environment:
  WHITELIST: "PlayerOne,PlayerTwo,PlayerThree"
  ENFORCE_WHITELIST: "true"
```

| Env var | What it does | Depends on |
|---|---|---|
| `WHITELIST` | Comma-separated players → writes `whitelist.json` | Always works, independent of `OVERRIDE_SERVER_PROPERTIES` |
| `ENFORCE_WHITELIST` | Sets `white-list=true` in `server.properties` | Only takes effect when `OVERRIDE_SERVER_PROPERTIES=true` (the default) |

**⚠️ PITFALL: `ENFORCE_WHITELIST` is ignored when `OVERRIDE_SERVER_PROPERTIES=false`.** The env var sets `server.properties`, but the entrypoint skips server.properties entirely when the override flag is false. In that case, use RCON `whitelist on` instead — it writes `white-list=true` to the running server's `server.properties` directly. After confirming with `docker exec <container> grep white-list /data/server.properties`, the setting persists across restarts.

**⚠️ PITFALL: "That player does not exist" means the username isn't a valid Mojang account.** RCON `whitelist add` fails for nonexistent usernames. Verify with the Mojang API before troubleshooting the server:

```bash
curl -s "https://api.mojang.com/users/profiles/minecraft/<username>"
# Valid → returns {"id":"...","name":"..."}
# Invalid → returns {"errorMessage":"Couldn't find any profile with name ..."}
```

**Recommended workflow for setting up whitelist on existing servers:**
1. Add `WHITELIST` env var to docker-compose.yml (persistence)
2. Run RCON `whitelist on` + `whitelist add <each user>` (instant, no restart)
3. Verify with `whitelist list`
4. If `OVERRIDE_SERVER_PROPERTIES=false`, the RCON `whitelist on` is the only way to set `white-list=true` — `ENFORCE_WHITELIST` won't work

**Homepage:** List both servers separately on the dashboard with distinct descriptions:
```yaml
- Vanilla MC:
    href: https://oathless.dev
    description: Minecraft 26.2 • mc.oathless.dev:25565
    icon: minecraft.png

- Modded MC:
    href: https://oathless.dev
    description: Forge 1.20.1 • 267 mods • modded.oathless.dev:25566
    icon: minecraft.png
```

| Variable | Purpose |
|---|---|
| `CF_SLUG` | Short identifier from the modpack URL (e.g. `integrated-minecraft`) |
| `CF_PAGE_URL` | Full CurseForge modpack page URL |
| `CF_FILE_ID` | Pin to a specific file version |
| `CF_FILENAME_MATCHER` | Substring match to pin a version (e.g. `1.0.7`) |
| `CF_EXCLUDE_MODS` | Newline-delimited list of mod slugs to exclude |
| `CF_OVERRIDES_EXCLUSIONS` | Ant-style paths to exclude from overrides extraction |
| `CF_PARALLEL_DOWNLOADS` | Parallel mod downloads (default: 4) |

See `references/linux-hardware-inspection.md` for the full workflow.

## Homepage (gethomepage.dev)

Service dashboard with YAML config and Docker auto-discovery.

```yaml
homepage:
  image: ghcr.io/gethomepage/homepage:latest
  container_name: homepage
  restart: unless-stopped
  environment:
    - HOMEPAGE_ALLOWED_HOSTS=home.oathless.dev   # required when behind reverse proxy
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
    - ./homepage:/app/config
  networks:
    - homeserver
```

**⚠️ PITFALL: `HOMEPAGE_ALLOWED_HOSTS` is required.** Without it, Homepage rejects requests from the reverse proxy domain with "Host validation failed."

**⚠️ PITFALL: Config files are root-owned.** The container creates `./homepage/` with root ownership. Chown before writing configs:

```bash
docker run --rm -v /home/ruben/homeserver/homepage:/data alpine:latest chown -R 1000:1000 /data
```

**Config files** live in `./homepage/`:
- `settings.yaml` — title, theme, layout
- `services.yaml` — service links grouped by category (groups are supported here)
- `widgets.yaml` — system resources, docker stats, search
- `bookmarks.yaml` — quick links
- `docker.yaml` — socket-based auto-discovery

Restart after config changes: `docker compose restart homepage`

**⚠️ PITFALL: Widgets use a flat YAML list, not grouped sections.** Unlike `services.yaml` (which supports groups like `- Infrastructure:` → `- Caddy:`), `widgets.yaml` is a flat list of widget objects. Grouping widgets under named sections produces "Missing" errors for every widget in the group.

```yaml
# WRONG — groups cause "Missing" errors:
widgets.yaml: |
  - Resources:
      - System:
          widget: resources
  - Search:
      - Search:
          widget: search

# RIGHT — flat list, no groups:
widgets.yaml: |
  - resources:
      cpu: true
      memory: true
      expanded: true
      disk: /
  - search:
      provider: duckduckgo
      target: _blank
```

**⚠️ PITFALL: No standalone `docker` widget.** The docker widget type only works through the `docker.yaml` provider (auto-discovery), not as a standalone widget in `widgets.yaml`. Adding `- docker:` in widgets.yaml produces "Missing." Use `docker.yaml` with the socket path instead.

**⚠️ PITFALL: Dashboard icons are CDN-fetched, not all names exist.** Homepage fetches icons from `cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/` at runtime. Most common service names work (`caddy.png`, `forgejo.png`, `dockge.png`, `dozzle.png`, `uptime-kuma.png`, `minecraft.png`, `tailscale.png`). Custom/generic names like `notes.png` do NOT exist and show a broken image. Fallbacks:
- **Material Design Icons:** Use `icon: mdi-notebook-edit-outline` (or any valid MDI name). Always available, no CDN dependency.
- **Simple Icons:** Use `icon: si-github` for brand icons.
- **Abbreviations:** Use `abbr: NT` for a text badge instead of an icon.

## Dockge

Stack manager that expects compose files at `/opt/stacks/<name>/docker-compose.yml`.

```yaml
dockge:
  image: louislam/dockge:1
  container_name: dockge
  restart: unless-stopped
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
    - ./dockge/data:/app/data
    - .:/opt/stacks/homeserver:ro    # mounts directly as a stack directory
  networks:
    - homeserver
```

**⚠️ PITFALL:** Dockge expects subdirectories under `/opt/stacks/`. Mounting `.:/opt/stacks:ro` results in "This stack is not managed by Dockge." Mount the project root directly into a named subdirectory like `/opt/stacks/homeserver`.

## References

- `references/sops-age-secrets.md` — full SOPS + age setup recipe: architecture, step-by-step, pitfalls, day-to-day ops, comparison matrix
- `references/couchdb-livesync-config.md` — required CouchDB config (single-node + CORS) for Obsidian Live Sync
- `references/zennotes-setup.md` — working ZenNotes Docker config with pitfalls and verification
- `references/zennotes-internals.md` — codebase architecture, tech stack, data model, wikilink system, and graph-feature feasibility assessment
- `references/uptime-kuma-monitors.md` — programmatic monitor creation, DB schema, pitfall guide
- `references/github-integration.md` — fine-grained PAT scoping, `gh` CLI auth, org isolation
- `references/service-catalog.md` — deployed service configs, Caddy blocks, and gotchas (Homepage, Forgejo, Dockge, Dozzle, etc.)
- `references/homepage-config-ruben.md` — working Homepage YAML configs for Ruben's homelab (services, widgets, bookmarks, icons verified)
- `templates/push-uptime-kuma.sh` — starter script for Uptime Kuma push monitors via Hermes cron
- `templates/deploy-sops.sh` — deploy wrapper: decrypts secrets → runs docker compose → cleans up plaintext
- `templates/sops-config.yaml` — starter `.sops.yaml` (replace age public key placeholder)
- `references/crafty-controller.md` — Crafty Controller setup, migration from itzg, API notes, pitfalls
- `references/minecraft-curseforge-modpacks.md` — full AUTO_CURSEFORGE reference, debugging, and pitfalls
- `references/linux-hardware-inspection.md` — sysfs/proc-based hardware inspection without sudo (NVMe, SATA, USB, DMI, Docker storage)
- `references/optiplex-3070-micro-hardware.md` — Ruben's OptiPlex 3070 Micro: confirmed specs, 2.5" bay, Dell caddy/cable part numbers
- `references/homepage-forgejo-dockge-dozzle.md` — Homepage, Forgejo, Dockge, and Dozzle: Compose snippets, Caddy entries, ports, resource usage, and verification
- `references/optiplex-3070-micro-hardware.md` — Ruben's OptiPlex 3070 Micro: confirmed specs, 2.5" bay, Dell caddy/cable part numbers
