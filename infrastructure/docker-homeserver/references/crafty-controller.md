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
Basic config (Crafty has its own login — no double-auth needed):
```caddy
mc.oathless.dev {
    reverse_proxy crafty-http:8000 {
        header_up Host {http.request.host}
        header_up X-Forwarded-Proto https
        header_up X-Forwarded-Host {http.request.host}
    }
}
```
The Host header forwarding is CRITICAL — without it, cookies and CSRF tokens won't work (see Pitfall #9).

Optional: add Caddy `basic_auth` for an extra layer, but strip the leaked `Authorization` header so it doesn't conflict with Crafty's own auth:
```caddy
mc.oathless.dev {
    basic_auth {
        oathless $2a$14$8S2Ua8ch/xxrO0HWIdME.ebWwizQ5pxIr7aEgCEIkEHGmoRNcgIEi
    }
    reverse_proxy crafty-http:8000 {
        header_up Host {http.request.host}
        header_up X-Forwarded-Proto https
        header_up X-Forwarded-Host {http.request.host}
        header_up -Authorization
    }
}
```

The proxy chain: `Browser → HTTPS → Caddy → HTTP → crafty-http:8000 (socat) → HTTPS → crafty:8443`

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

### 7. Caddy `basic_auth` leaks the `Authorization` header to Crafty
When a user authenticates with Caddy's `basic_auth`, Caddy forwards the `Authorization: Basic <base64>` header to the upstream (Crafty). Crafty sees this header and tries to use it for its own authentication, which fails because Crafty uses Bearer tokens or session cookies — not HTTP Basic. This causes "ACCESS_DENIED" and "An error occurred while authenticating the user" errors specifically for account operations: password changes, MFA setup, API key creation. Login itself often works because Crafty's login endpoint may handle the conflict differently.

**Fix:** Strip the header before proxying with `header_up -Authorization` inside the `reverse_proxy` block. See the Caddy entry in Step 4.

**Better fix:** Don't use Caddy's `basic_auth` on services that have their own login (Crafty, Forgejo, etc.). Double-auth is friction for users and causes this header leak. Only use `basic_auth` for services without built-in auth (Dozzle, Homepage, etc.).

### 8. Crafty `base_url` must include protocol AND match the external domain — CSRF protection
Crafty's `config.json` has `"base_url": "localhost:8443"` by default. When the browser accesses Crafty through a reverse proxy at `mc.oathless.dev`, Crafty's CSRF protection rejects all sensitive POST requests (password change, MFA setup, API key creation) because the `Origin`/`Host` headers don't match `base_url`. The error shown is "ACCESS_DENIED — An error occurred while authenticating the user."

**Fix:** Update `base_url` to the full URL INCLUDING `https://` protocol. Without the protocol prefix, Crafty compares `Origin: https://mc.oathless.dev` against `base_url: mc.oathless.dev` and they silently don't match:

```bash
python3 -c "
import json
with open('./crafty/config/config.json') as f:
    config = json.load(f)
config['base_url'] = 'https://mc.oathless.dev'
with open('./crafty/config/config.json', 'w') as f:
    json.dump(config, f, indent=4)
"
docker compose restart crafty
```

### 9. Caddy rewrites Host header — cookie/CSRF domain mismatch
Caddy's `reverse_proxy` rewrites the `Host` header to the upstream address (`crafty-http:8000`) by default. Crafty uses this Host value for setting session cookies and CSRF tokens. If Crafty sees `Host: crafty-http:8000` instead of `Host: mc.oathless.dev`, cookies are set for the wrong domain and the browser never sends them back.

**Symptoms:** login succeeds (POST auth returns 200 + token), but every subsequent API call returns 403 Forbidden (CSRF) or "Invalid token" in the auth log. This tripped up debugging because login always worked — masking the real issue as an auth problem when it was a cookie domain problem.

**Fix:** Explicitly forward the original Host header and `X-Forwarded-*` headers in Caddy:
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

The `{http.request.host}` placeholder preserves the browser's original `mc.oathless.dev` Host header through the proxy chain. `X-Forwarded-Proto: https` tells Crafty the original request was HTTPS so it sets cookies with the `Secure` flag correctly.

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
