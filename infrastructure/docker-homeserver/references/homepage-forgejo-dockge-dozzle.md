# Homepage, Forgejo, Dockge & Dozzle — Compose + Caddy Snippets

Four lightweight services deployed together on the OptiPlex 3070 Micro homeserver.
All route through Caddy with auto-TLS. Three (`homepage`, `dockge`, `dozzle`) need
`/var/run/docker.sock:ro` for container introspection.

## Homepage — Service Dashboard

```yaml
homepage:
  image: ghcr.io/gethomepage/homepage:latest
  container_name: homepage
  restart: unless-stopped
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
    - ./homepage:/app/config
  networks:
    - homeserver
```

- Internal port: **3000**
- Caddy: `reverse_proxy homepage:3000`
- Docker auto-discovery works out of the box via socket bind
- YAML config in `./homepage/` — edit services.yaml, bookmarks.yaml, widgets.yaml, settings.yaml
- ~80 MB RAM idle
- Health check is built into the image (Docker reports `healthy`)
- **⚠️ GOTCHA: `HOMEPAGE_ALLOWED_HOSTS`.** When proxied through Caddy on a custom domain, Homepage rejects requests because the Host header doesn't match `localhost`. The container starts healthy but returns "Host validation failed." Fix by adding the env var:

```yaml
homepage:
  environment:
    - HOMEPAGE_ALLOWED_HOSTS=home.oathless.dev
```

## Forgejo — Git Hosting

```yaml
forgejo:
  image: codeberg.org/forgejo/forgejo:10
  container_name: forgejo
  restart: unless-stopped
  volumes:
    - ./forgejo/data:/data
    - ./forgejo/config:/etc/forgejo
  networks:
    - homeserver
```

- Internal port: **3000** (same as Homepage — no conflict, separate containers)
- Caddy: `reverse_proxy forgejo:3000`
- First visit launches web installer — pick **SQLite** for solo use (no separate DB container)
- No env vars needed; all setup is through the web UI
- ~100 MB RAM idle
- Forgejo 10 is the current stable major version (Go binary, soft fork of Gitea)

## Dockge — Compose Stack Manager

```yaml
dockge:
  image: louislam/dockge:1
  container_name: dockge
  restart: unless-stopped
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
    - ./dockge/data:/app/data
    - .:/opt/stacks/homeserver:ro    # includes stack name as subdirectory
  networks:
    - homeserver
```

- Internal port: **5001**
- Caddy: `reverse_proxy dockge:5001`
- First visit prompts for username/password
- **⚠️ GOTCHA: Mount path is critical.** Dockge requires compose files at `/opt/stacks/<stack-name>/docker-compose.yml`. Mounting at `/opt/stacks` without the stack subdirectory causes "This stack is not managed by Dockge.":
  ```yaml
  # WRONG — no stack name subdirectory:
  - .:/opt/stacks:ro
  
  # RIGHT — includes the stack name:
  - .:/opt/stacks/homeserver:ro
  ```
- ~25-35 MB RAM idle

## Dozzle — Log Viewer

```yaml
dozzle:
  image: amir20/dozzle:latest
  container_name: dozzle
  restart: unless-stopped
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
  networks:
    - homeserver
```

- Internal port: **8080**
- Caddy: `reverse_proxy dozzle:8080`
- No config needed — just works
- ~10-20 MB RAM idle
- Features: fuzzy search, regex filter, split-screen multi-container view

## Full Caddy Snippet

```
home.oathless.dev {
    reverse_proxy homepage:3000
}

git.oathless.dev {
    reverse_proxy forgejo:3000
}

docker.oathless.dev {
    reverse_proxy dockge:5001
}

logs.oathless.dev {
    reverse_proxy dozzle:8080
}
```

## Start Commands

```bash
# Pull + start all four
docker compose pull homepage forgejo dockge dozzle
docker compose up -d homepage forgejo dockge dozzle

# After adding Caddy entries, restart Caddy to pick them up
docker compose restart caddy

# Verify Caddy sees the new entries
docker compose exec caddy cat /etc/caddy/Caddyfile | tail -20

# Smoke test
curl -sk -o /dev/null -w "%{http_code}" https://home.oathless.dev/
```

## Combined Resource Footprint

| Service   | RAM (idle) |
|-----------|------------|
| Homepage  | ~80 MB     |
| Forgejo   | ~100 MB    |
| Dockge    | ~35 MB     |
| Dozzle    | ~20 MB     |
| **Total** | **~235 MB** |

Negligible on 30 GB total RAM, even with Minecraft's 10 GB allocation.

## Verified On

- OptiPlex 3070 Micro, i5-9500T, 30 GB RAM, Ubuntu 24.04
- Docker Compose v2, Caddy 2 (Alpine image)
- Deployed June 2026 — all images pulled and verified working
