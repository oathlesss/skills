# Uptime Kuma — Programmatic Monitor Management

## Architecture

Uptime Kuma v1.x uses **Socket.IO** for all admin operations (create/edit/delete monitors, settings, etc.). There is no REST API for admin tasks — `curl`/`POST` to `/api/*` will return the SPA HTML, not JSON. The only public REST endpoint is `/api/status-page/heartbeat/<slug>` which is read-only and depends on a configured status page.

## Creating Monitors Without the Web UI

When you don't have the user's Uptime Kuma password or an API key configured, insert monitors directly into the SQLite database:

### Step 1: Inspect the DB schema

```bash
docker compose exec -T uptime-kuma sqlite3 /app/data/kuma.db ".schema monitor"
```

Key columns (subset):
| Column | Type | Notes |
|--------|------|-------|
| `name` | VARCHAR(150) | Human-readable label |
| `active` | BOOLEAN | 1 = active |
| `user_id` | INTEGER | Owner (find via `SELECT id, username FROM user`) |
| `interval` | INTEGER | Check interval in **seconds** |
| `type` | VARCHAR(20) | `http`, `port`, `ping`, `dns`, `push`, `steam`, `gamedig`, `mqtt`, `docker`, `tailscale-ping`, etc. |
| `url` | TEXT | Full URL for HTTP type, NULL for port/ping/dns |
| `hostname` | VARCHAR(255) | Target hostname (for port, ping, dns) |
| `port` | INTEGER | Target port (for TCP port checks) |
| `method` | TEXT | HTTP method: `GET`, `POST`, etc. |
| `accepted_statuscodes_json` | TEXT | `["200"]` or `["200-299"]` |
| `ignore_tls` | BOOLEAN | 0 = validate TLS |
| `maxretries` | INTEGER | Retries before marking DOWN (default 3) |
| `retry_interval` | INTEGER | Seconds between retries |
| `timeout` | DOUBLE | Seconds before timeout (48 = 48s) |
| `dns_resolve_type` | VARCHAR(5) | `A`, `AAAA`, `MX`, etc. |
| `dns_resolve_server` | VARCHAR(255) | Explicit DNS server (empty = system default) |

### Step 2: Insert monitors via docker exec heredoc

```bash
docker compose exec -T uptime-kuma sqlite3 /app/data/kuma.db << 'EOSQL'
-- HTTPS check
INSERT INTO monitor (name, active, user_id, interval, url, type, weight, created_date, maxretries, ignore_tls, upside_down, maxredirects, accepted_statuscodes_json, retry_interval, method, timeout)
VALUES ('example.com', 1, 1, 60, 'https://example.com', 'http', 2000, datetime('now'), 3, 0, 0, 10, '["200"]', 60, 'GET', 48);

-- TCP port check (internal Docker hostname)
INSERT INTO monitor (name, active, user_id, interval, type, weight, hostname, port, created_date, maxretries, retry_interval, timeout)
VALUES ('Minecraft Server', 1, 1, 120, 'port', 2000, 'minecraft', 25565, datetime('now'), 3, 120, 48);

-- Ping check
INSERT INTO monitor (name, active, user_id, interval, type, weight, hostname, created_date, maxretries, retry_interval, timeout)
VALUES ('Internet', 1, 1, 300, 'ping', 2000, '1.1.1.1', datetime('now'), 3, 300, 48);

-- DNS check (use external domain + explicit server to avoid circular resolution)
INSERT INTO monitor (name, active, user_id, interval, type, weight, hostname, created_date, maxretries, dns_resolve_type, dns_resolve_server, retry_interval, timeout)
VALUES ('DNS Resolution', 1, 1, 300, 'dns', 2000, 'google.com', datetime('now'), 3, 'A', '1.1.1.1', 300, 48);
EOSQL
```

**⚠️ Always use `-T` (no TTY) when piping heredocs to `docker compose exec`.** Without `-T`, Docker may complain about the terminal.

### Step 3: Restart Uptime Kuma

Monitors are loaded into memory at startup. Inserting into the DB alone won't start them:

```bash
docker compose restart uptime-kuma
```

### Step 4: Verify monitors are running

Query the heartbeat table after ~10 seconds (first check interval):

```bash
docker compose exec -T uptime-kuma sqlite3 /app/data/kuma.db \
  "SELECT m.name, h.status, h.msg FROM monitor m 
   LEFT JOIN (SELECT monitor_id, status, msg, MAX(time) as max_time FROM heartbeat GROUP BY monitor_id) h 
   ON m.id = h.monitor_id ORDER BY m.id;"
```

Status codes: `0` = PENDING, `1` = UP, `2` = DOWN.

### Updating Existing Monitors

When a service's name, hostname, or port changes, update the monitor row instead of deleting and recreating:

```bash
# Update a single monitor — use docker exec, not docker compose exec
docker exec uptime-kuma sqlite3 /app/data/kuma.db \
  "UPDATE monitor SET name='Vanilla MC', hostname='minecraft-vanilla', port=25565,
   description='Minecraft 1.21.4 vanilla server' WHERE id=3;"
```

**⚠️ Use `docker exec` not `docker compose exec` for single SQL statements.** The compose variant requires `-T` and heredoc piping; plain `docker exec` accepts the SQL inline as a quoted argument, which is simpler for one-off commands.

**Verify the update:**
```bash
docker exec uptime-kuma sqlite3 /app/data/kuma.db \
  "SELECT id, name, hostname, port FROM monitor WHERE name LIKE '%MC%';"
```

**⚠️ HOSTNAME CHANGES REQUIRE A RESTART.** Most field updates (name, description, interval, timeout) take effect immediately — no restart needed. But Uptime Kuma caches DNS resolution internally. Changing `hostname` in the DB will update the field, but the monitor keeps resolving the OLD hostname until Uptime Kuma is restarted. Symptom: heartbeats show `getaddrinfo ENOTFOUND <old-hostname>` while the DB shows the new hostname.

**⚠️ CONTAINER RECREATE STALES DNS CACHE, TOO.** Docker assigns a new IP when a container is recreated (even with the same hostname). Uptime Kuma may cache the old IP and produce `connect EHOSTUNREACH <old-ip>:<port>` errors. Restart Uptime Kuma to flush the DNS cache. If heartbeats show successful UP records alongside stale DOWN records, delete the stale heartbeat rows (see \"Stale DOWN heartbeat\" pitfall below).

**Summary:** For new INSERTs → always restart. For hostname changes → always restart. For container recreates → restart Uptime Kuma. For other field updates (name, interval, description) → no restart needed.

## Pitfalls

### DNS from Docker containers

DNS monitors that target the server's own public domain (e.g. `oathless.dev`) will fail with `Invalid IP address` when run from inside a Docker container. The container's DNS can't resolve domains that point back to itself through the host's public IP. **Fix:** Use an external domain (`google.com`, `cloudflare.com`) with an explicit DNS server (`1.1.1.1` or `8.8.8.8`).

### DB ownership

The SQLite database at `./uptime-kuma/kuma.db` is owned by the container's root user (uid 0). Host-side writes from Python `sqlite3` will fail with "readonly database". Always use `docker compose exec -T uptime-kuma sqlite3 /app/data/kuma.db` for writes.

### Empty public status page

`curl https://status.domain.tld/api/status-page/heartbeat/status` returns empty `heartbeatList` and `uptimeList` until a status page is configured and monitors are assigned to it. This is expected — monitors are private by default. The dashboard is available at the web UI login.

### Port checks use Docker internal hostnames

TCP port monitors run inside the Uptime Kuma container, so use Docker Compose service names as hostnames (e.g. `minecraft`, `caddy`), not `localhost` or the public domain. The `port` type doesn't use the `url` field at all.

## Push Monitors for CLI-Based Health Checks

Push monitors accept heartbeats via a unique URL. Use them to monitor anything that can't be probed over the network: systemd services, CLI tools, internal health checks.

### Step 1: Create push monitors in the DB

Push monitors have `type = 'push'` and a unique `push_token` (VARCHAR(20)):

```bash
docker compose exec -T uptime-kuma sqlite3 /app/data/kuma.db << 'EOSQL'
INSERT INTO monitor (name, active, user_id, interval, type, weight, push_token, created_date, maxretries, retry_interval, timeout)
VALUES ('Discord Gateway', 1, 1, 180, 'push', 2000, '<random_hex_20>', datetime('now'), 0, 120, 48);
EOSQL
```

Generate the push token with `secrets.token_hex(10)[:20]`. Then restart Uptime Kuma.

### Step 2: Retrieve the push token

```bash
docker compose exec -T uptime-kuma sqlite3 /app/data/kuma.db \
  "SELECT id, name, push_token FROM monitor WHERE type='push';"
```

### Step 3: Create a liveness script

Push heartbeats by hitting `https://<kuma-domain>/api/push/<token>?status=up&msg=OK`. Write a shell script that checks the service and pushes:

```bash
#!/bin/bash
# ~/.hermes/scripts/push-gateway-status.sh
if hermes gateway status &>/dev/null; then
    curl -sk "https://status.oathless.dev/api/push/TOKEN?status=up&msg=OK" &>/dev/null
else
    curl -sk "https://status.oathless.dev/api/push/TOKEN?status=down&msg=Gateway%20not%20running" &>/dev/null
fi
```

### Step 4: Wire it into a Hermes cron job

Use `no_agent=true` + `deliver=local` — the script is the job, no LLM tokens burned:

```
cronjob action=create schedule="every 2m" script="push-gateway-status.sh"
      no_agent=true deliver=local name="Push Gateway health to Uptime Kuma"
```

The script's stdout goes nowhere (local delivery); only non-zero exits trigger error alerts. This pattern works for any CLI check: `hermes status`, `systemctl is-active <unit>`, `docker compose ps <service>`, etc.

### Pitfall: Push interval vs. monitor interval (MUST be staggered)

**⚠️ DO NOT match the cron interval to the monitor interval.** With cron at `every 2m` and monitor at `120s`, any scheduling jitter (which Hermes cron has — agent processing delays ticks) will miss the window and both push monitors will flap DOWN simultaneously in lockstep.

**The ratio rule:** `cron_interval ≤ monitor_interval / 2`. At minimum, the monitor interval should be at least **double** the cron interval. Practical combos:
- Cron `every 1m` + monitor `180s` (3 heartbeats per window, very safe)
- Cron `every 1m` + monitor `120s` (2 heartbeats per window)
- Cron `every 30s` + monitor `120s` (4 heartbeats per window)

**Diagnosing flapping:** The heartbeat table reveals the lockstep pattern — both push monitors going UP/DOWN together:

```bash
docker exec uptime-kuma sqlite3 /app/data/kuma.db \
  "SELECT m.name, h.status, h.msg
   FROM heartbeat h JOIN monitor m ON m.id = h.monitor_id
   WHERE m.type='push' ORDER BY h.time DESC LIMIT 20;"
```

Status `0` = DOWN (missed heartbeat window), `1` = UP. If both monitors show `0` on the same rows and `1` on the same rows, it's interval-matching flapping, not a real outage.

**Fix:** Either reduce the cron interval or widen the monitor interval (takes effect immediately, no restart needed):

```bash
docker exec uptime-kuma sqlite3 /app/data/kuma.db \
  "UPDATE monitor SET interval = 180 WHERE type = 'push';"
```

### Pitfall: Stale DOWN heartbeat after fixing a monitor

When you fix a misconfigured monitor (wrong hostname, missing DNS server) and restart Uptime Kuma, the UI may still show DOWN or PENDING with the old error message — even after successful new checks are recorded. This happens when the old heartbeat record persists alongside new UP records.

**Fix:** Delete the stale heartbeat rows from the DB:

```bash
# Check all heartbeats for the problematic monitor
docker compose exec -T uptime-kuma sqlite3 /app/data/kuma.db \
  "SELECT status, msg, time FROM heartbeat WHERE monitor_id = 5 ORDER BY time DESC LIMIT 10;"

# Remove the DOWN (status=2) records
docker compose exec -T uptime-kuma sqlite3 /app/data/kuma.db \
  "DELETE FROM heartbeat WHERE monitor_id = 5 AND status = 2;"
```

The UI updates on the next WebSocket event — no restart needed. If it still shows stale data, a browser hard refresh (Ctrl+Shift+R) should sync it.

## Suggested Monitor Intervals

| Type | Interval | Rationale |
|------|----------|-----------|
| HTTP/HTTPS | 60s | Fast feedback on front-end issues |
| TCP port | 120s | Game servers, databases |
| Ping | 300s | Internet connectivity, no need for granularity |
| DNS | 300s | DNS rarely changes quickly |
| Push | 180s | Service liveness via Hermes cron — must be ≥ 2× the cron schedule |
| Certificate | 86400s | Daily is sufficient |
