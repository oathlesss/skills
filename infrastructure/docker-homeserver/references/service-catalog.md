# Homeserver Service Catalog — Deployed Configs

Services running on Ruben's OptiPlex 3070 Micro Docker host. Each entry includes the minimal working compose snippet, Caddy reverse proxy block, and any gotchas encountered during deployment.

---

## Homepage (gethomepage.dev)

Lightweight dashboard with Docker auto-discovery and 150+ API widget integrations.

```yaml
homepage:
  image: ghcr.io/gethomepage/homepage:latest
  restart: unless-stopped
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
    - ./homepage:/app/config
  networks:
    - homeserver
```

```caddy
home.oathless.dev {
    reverse_proxy homepage:3000
}
```

**Gotchas:**
- Needs `/var/run/docker.sock` (read-only) for auto-discovery
- **⚠️ `HOMEPAGE_ALLOWED_HOSTS`:** without this env var, proxied requests get "Host validation failed" because Homepage sees the custom domain instead of `localhost`. Add `HOMEPAGE_ALLOWED_HOSTS=home.oathless.dev` to the compose environment block.
- Config lives in `./homepage/` — YAML files (services.yaml, widgets.yaml, etc.)
- No built-in auth — use Caddy `basic_auth` to lock it behind a password

---

## Forgejo (Self-hosted Git)

Community fork of Gitea, single Go binary, SQLite by default.

```yaml
forgejo:
  image: codeberg.org/forgejo/forgejo:10
  restart: unless-stopped
  volumes:
    - ./forgejo/data:/data
    - ./forgejo/config:/etc/forgejo
  networks:
    - homeserver
```

```caddy
git.oathless.dev {
    reverse_proxy forgejo:3000
}
```

**⚠️ PITFALL: SSH port not exposed — `git@git.oathless.dev` will time out.** Forgejo runs SSH internally on port 22, but the compose config has no `ports:` mapping. Host SSH uses port 22, so `git@git.oathless.dev:22` is consumed by the host sshd (or nothing), not Forgejo. Fix — add a port mapping using a non-standard host port:

```yaml
forgejo:
  ports:
    - "2222:22"      # Forgejo SSH (host 2222 → container 22)
```

Then configure `~/.ssh/config`:

```
Host git.oathless.dev
    Port 2222
    IdentityFile ~/.ssh/id_ed25519
```

Alternatively, skip SSH entirely and use HTTPS with a Forgejo access token (no compose change needed): Settings → Applications → Generate Token with `write:repository` scope, then use `https://<token>@git.oathless.dev/...` or configure git credential helper.

**Gotchas:**
- First visit triggers web installer — set up admin account, pick SQLite
- Tag `10` is the latest major version (as of mid-2026); check for newer tags
- Forgejo and Homepage both use port 3000 internally — no conflict (different containers)

---

## Dockge (Docker Compose Stack Manager)

Web UI for managing compose stacks — start/stop/edit from browser.

```yaml
dockge:
  image: louislam/dockge:1
  restart: unless-stopped
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
    - ./dockge/data:/app/data
    - .:/opt/stacks/homeserver:ro
  networks:
    - homeserver
```

```caddy
docker.oathless.dev {
    reverse_proxy dockge:5001
}
```

**⚠️ PITFALL: Mount path is critical.** Dockge requires compose files at `/opt/stacks/<stack-name>/docker-compose.yml`. If you mount the project root at `/opt/stacks` directly (without the subdirectory), Dockge shows "This stack is not managed by Dockge." The fix is `.:/opt/stacks/homeserver:ro` — the bind mount target must include the stack name as a subdirectory.

**Gotchas:**
- First visit prompts for username/password
- Read-only mount (`:ro`) prevents Dockge from editing the compose file in-place (it can still start/stop)
- Port 5001

---

## Dozzle (Log Viewer)

Real-time Docker log viewer with fuzzy search and split-screen multi-container view.

```yaml
dozzle:
  image: amir20/dozzle:latest
  restart: unless-stopped
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
  networks:
    - homeserver
```

```caddy
logs.oathless.dev {
    reverse_proxy dozzle:8080
}
```

**Gotchas:**
- No config needed — works instantly
- No built-in auth — logs may contain sensitive data (IPs, error traces). Use Caddy `basic_auth` to lock it behind a password.
- Port 8080

---

## Resource Footprint (all four combined)

| Service | RAM (idle) |
|---------|-----------|
| Homepage | ~80 MB |
| Forgejo | ~100 MB |
| Dockge | ~35 MB |
| Dozzle | ~15 MB |
| **Total** | **~230 MB** |

Negligible on 30GB host even with Minecraft's 10GB allocation.
