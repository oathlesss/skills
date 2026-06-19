# Crafty Controller — Setup & Migration Reference

## Environment

- **Machine:** OptiPlex 3070 Micro, Docker Compose homeserver at `/home/ruben/homeserver`
- **Crafty version:** 4.10.7 (image: `registry.gitlab.com/crafty-controller/crafty-4:latest`)
- **Existing server:** Forge 1.20.1-47.4.0, 100+ mods (~946MB mods, 35MB world, 208MB configs), formerly on itzg/minecraft-server:java17

## Migration Recipe (itzg → Crafty)

### Step 1: Stop the old server
```bash
cd /home/ruben/homeserver
docker compose stop minecraft
```

### Step 2: Copy files to Crafty's import directory
```bash
mkdir -p crafty/import/modded
cp -r minecraft/data/world crafty/import/modded/
cp -r minecraft/mods crafty/import/modded/
cp -r minecraft/config crafty/import/modded/
cp minecraft/data/server.properties crafty/import/modded/
cp minecraft/data/eula.txt crafty/import/modded/
cp minecraft/data/banned-*.json crafty/import/modded/ 2>/dev/null
cp minecraft/data/ops.json crafty/import/modded/ 2>/dev/null
cp minecraft/data/whitelist.json crafty/import/modded/ 2>/dev/null
```

### Step 3: Replace the itzg service with Crafty in docker-compose.yml
```yaml
crafty:
  image: registry.gitlab.com/crafty-controller/crafty-4:latest
  container_name: crafty
  restart: unless-stopped
  ports:
    - "25565:25565"     # Vanilla Minecraft
    - "25566:25566"     # Modded Minecraft
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

### Step 4: Add Caddy reverse proxy
```caddy
mc.oathless.dev {
    basic_auth {
        oathless $2a$14$8S2Ua8ch/xxrO0HWIdME.ebWwizQ5pxIr7aEgCEIkEHGmoRNcgIEi
    }
    reverse_proxy crafty-http:8000   # socat sidecar, NOT crafty directly
}
```

The proxy chain: `Browser → HTTPS → Caddy (auth) → HTTP → crafty-http:8000 (socat) → HTTPS → crafty:8443`

### Step 5: Start
```bash
docker compose up -d crafty crafty-http caddy
docker rm minecraft  # cleanup orphan
# Caddy auto-issues TLS cert for mc.oathless.dev on restart
```

### Step 6: Initial admin password
```bash
cat ./crafty/config/default-creds.txt
# Returns: {"username": "admin", "password": "...long random string..."}
```

### Step 7: Web UI — create servers
1. Browse to `https://mc.oathless.dev` (Caddy basic_auth first, then Crafty login)
2. **Vanilla server:** Create Server → Vanilla, latest version, 2GB, port 25565
3. **Modded server:** Create Server → Import → select "modded" directory → Forge 1.20.1, 10GB, port 25566

## Pitfalls

### 1. Crafty only serves HTTPS (8443) — ignores `http_port` config
Crafty 4 hardcodes HTTPS on port 8443 with a self-signed certificate. Adding `"http_port": 8000` to `config.json` has ZERO effect — Crafty ignores it and only binds HTTPS port 8443. The log confirms: `https://172.18.0.5:8443 is up and ready for connections`. No plain HTTP listener is ever created.

**Workaround:** Use the socat sidecar (see Step 3 above). Crafty's 8443 port does NOT need to be exposed to the host in docker-compose — the socat sidecar handles the internal HTTPS connection.

### 2. Caddy v2 cannot reverse-proxy to HTTPS upstream with self-signed cert
**This was the root cause of the persistent 502 errors.** Caddy v2.11.4 silently strips the `https://` scheme from `reverse_proxy` directives and ignores `transport http { tls; tls_insecure_skip_verify }` blocks. Every syntax variant produced the same adapted config: `{"dial": "crafty:8443"}` — plain TCP, no TLS.

Attempted syntaxes that ALL failed:
- `reverse_proxy https://crafty:8443` → scheme stripped, connection reset
- `reverse_proxy https://crafty:8443 { transport http { tls_insecure_skip_verify } }` → transport block ignored
- `reverse_proxy { to https://crafty:8443; transport http { tls_insecure_skip_verify } }` → transport block ignored
- `reverse_proxy { to crafty:8443; transport http { tls; tls_insecure_skip_verify } }` → transport block ignored

All produced the same adapted config: `reverse_proxy` with `upstreams: [{dial: "crafty:8443"}]` — no TLS transport, no scheme. Always verify adapted config with `docker exec caddy caddy adapt --config /etc/caddy/Caddyfile`.

**Solution:** The socat sidecar pattern (see Step 3). Caddy proxies plain HTTP to `socat`, which handles the TLS connection to Crafty with `verify=0`.

### 3. Import directory needs subdirectories
Crafty's import wizard expects each server in its own subdirectory under `/crafty/import/`. Flat files at the top level (`/crafty/import/world`, `/crafty/import/mods`, etc.) are not recognized. Each import must be in e.g. `/crafty/import/modded/`.

### 4. Caddy needs restart (not just reload) for new domains
After adding `mc.oathless.dev` to the Caddyfile, `caddy reload` was not sufficient — the TLS certificate was only issued after `docker compose restart caddy`. This aligns with the existing "Bind Mount Caching Pitfall" in the skill.

### 5. Crafty API is finicky on fresh install
The `/api/v2/servers` POST endpoint returned `INVALID_JSON_SCHEMA: Additional Properties are not allowed` even for empty `{}` payloads on a first-boot install. The API becomes functional after completing setup through the web UI. For initial server creation, always use the web UI.

### 6. basic_auth bcrypt hash — no quotes
Same rule as other services: the bcrypt hash goes unquoted in the Caddyfile `basic_auth` block. Single-quoting it makes Caddy treat the quotes as part of the hash, breaking authentication.

## Vehicle Architecture (Multiple Servers)

```
Browser ──HTTPS──▶ Caddy (basic_auth) ──HTTP──▶ crafty-http:8000 (socat) ──HTTPS──▶ crafty:8443
                                                                                      │
                                                                      ┌───────────────┴───────────────┐
                                                                      │                               │
                                                              Vanilla Server                  Modded Server
                                                              port 25565                      port 25566
                                                              (mc.oathless.dev)               (modded.oathless.dev)
```

The admin panel: `https://mc.oathless.dev` (behind Caddy basic_auth + Crafty login).
Players connect directly: `mc.oathless.dev:25565` (vanilla) or `modded.oathless.dev:25566` (modded). Both domains resolve to the same IP.

## Password Reset via Database

When the web UI password change fails (common with auto-generated passwords containing special characters like `%`, `$`, `*`, `@`):

### Generate a new Argon2 hash
Crafty uses Argon2id for password hashing. Use Crafty's OWN virtual environment to hash — the host may not have the `argon2-cffi` package installed.

```bash
docker exec crafty bash -c "source /crafty/.venv/bin/activate && python3 -c \"
from argon2 import PasswordHasher
print(PasswordHasher().hash('YourNewPassword'))
\""
```

This outputs something like:
```
$argon2id$v=19$m=65536,t=3,p=4$salt$hash...
```

### Update the SQLite database
```bash
python3 -c "
import sqlite3
db = sqlite3.connect('./crafty/config/db/crafty.sqlite')
db.execute('''UPDATE users SET password = ? WHERE username = ?''', 
    ('ARGON2_HASH_HERE', 'admin'))
db.commit()
db.close()
"
```

### Update the plaintext reference file
```bash
cat > ./crafty/config/default-creds.txt << 'EOF'
{
    "username": "admin",
    "password": "YourNewPassword",
    "info": "This is NOT where you change your password. This file is only a means to give you a default password."
}
EOF
```

### Verify
```bash
python3 -c "
import sqlite3
db = sqlite3.connect('./crafty/config/db/crafty.sqlite')
pwd = db.execute('SELECT password FROM users WHERE username = ?', ('admin',)).fetchone()
print('Password updated' if pwd and 'argon2id' in pwd[0] else 'FAILED')
"
```

### Crafty's users table schema
- Database: `/crafty/app/config/db/crafty.sqlite` (mounted to `./crafty/config/db/crafty.sqlite`)
- Table: `users`
- Key columns: `user_id` (INTEGER PK), `username`, `password` (Argon2id hash), `superuser` (1=admin), `enabled` (1=active)
- Other user tables: `user_roles` (links users to roles), `user_crafty` (extended user permissions)

- **Login:** `POST /api/v2/auth/login` → `{"data": {"token": "eyJ...", "user_id": 1}}`
- **List servers:** `GET /api/v2/servers` → `{"data": []}` (empty array on fresh install)
- **Create server:** `POST /api/v2/servers` — schema unknown, returns `INVALID_JSON_SCHEMA` on fresh install
- **Auth header:** `Authorization: Bearer <token>`
- **Crafty uses self-signed cert internally** — curl needs `-k` or Python ssl context with `check_hostname=False`

The API was explored but not successfully used for server creation. Saving these notes for when automation is attempted again.
