---
name: docker-homeserver
description: Patterns for Docker Compose homeserver services — VPN tunnels, reverse proxies, CouchDB, health checks, credential safety, and auth key handling.
triggers:
  - Adding or checking any service in an existing docker-compose.yml
  - Setting up Tailscale, Cloudflare Tunnel, or WireGuard in Docker
  - Handling one-time auth keys in .env files with Docker Compose
  - Remote access / VPN for a Docker homeserver
  - Verifying whether a homeserver service is healthy
  - CouchDB setup for Obsidian Live Sync or general document storage
  - Any task involving credentials — .env files, passwords in shell commands
  - Setting up or modifying Uptime Kuma monitors, status pages, or notifications
  - Uptime Kuma API exploration, database inspection, or programmatic monitor creation
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

# Check CORS status (Live Sync needs it enabled)
curl -sk -u admin https://db.oathless.dev/_node/_local/_config/httpd/enable_cors
```

### Obsidian Live Sync Setup

Once CouchDB is healthy:
1. Install the "Self-hosted Live Sync" community plugin in Obsidian
2. Configure: URI `https://db.oathless.dev`, username `admin`, password from .env
3. The plugin auto-creates its databases on first sync

### Verifying Sync Is Working

- After setup, `_all_dbs` should show one or more databases (not empty `[]`)
- Databases look like `vault_name` or `vault_name_couchdb_sync_metadata`

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

Then verify the container sees the new content:

```bash
docker compose exec caddy tail -5 /etc/caddy/Caddyfile
```

Do NOT rely on `caddy reload` alone after file patches — always verify the container's view matches the host file with a `diff` or direct read.

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

## References

- `references/uptime-kuma-monitors.md` — programmatic monitor creation, DB schema, pitfall guide
- `references/compose-profiles-example.yaml` — full Tailscale compose snippet (with and without profiles)
- `templates/push-uptime-kuma.sh` — starter script for Uptime Kuma push monitors via Hermes cron
