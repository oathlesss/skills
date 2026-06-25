---
name: fullstack-web-deploy
description: Build and deploy full-stack web apps (Go backend + Vue/React frontend) as single-binary Docker containers on the homelab. Covers project scaffolding, Go embed for SPA, multi-stage Dockerfiles, Vite dev proxy, homelab integration, and webhook-based auto-deploy pipelines with rollback.
triggers:
  - Building a new web app with Go backend + JS frontend
  - Deploying a Go+Vue or Go+React app to the homelab
  - Creating a multi-stage Dockerfile for a full-stack app
  - Embedding a frontend SPA into a Go binary
  - Setting up Vite proxy for local full-stack dev
  - Setting up an auto-deploy pipeline for a homelab Docker Compose service
  - Configuring webhook-based CI/CD with Forgejo + Docker Compose
---

# Full-Stack Web App Deployment

Pattern for building and deploying full-stack web apps (Go backend + Vue/React frontend) as single-binary Docker containers on the homelab.

## Prerequisites

**Go**: Install without sudo if needed: download binary tarball → extract to `~/.local/go` → `export PATH="$HOME/.local/go/bin:$PATH"`. The host may not have `go` on PATH by default.

```bash
curl -fsSL "https://go.dev/dl/go1.24.5.linux-amd64.tar.gz" -o /tmp/go.tar.gz
tar -xzf /tmp/go.tar.gz -C ~/.local/
export PATH="$HOME/.local/go/bin:$PATH"
go version
```

**Node**: Expected at `~/.local/bin/node` (user-local install, no sudo). If missing, install via `nvm` or download node binary.

## Project Structure

```
project/
├── cmd/server/main.go         # Entry point
├── internal/
│   ├── handler/               # HTTP handlers (API + SPA fallback)
│   │   ├── api.go             # POST /api/command etc.
│   │   └── spa.go             # //go:embed dist + index.html fallback
│   └── ...                    # Domain packages
├── frontend/                  # Vite project (vue or react template)
│   ├── src/
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   └── ...
├── Dockerfile                 # Multi-stage: node → go → alpine
├── .dockerignore
├── go.mod
└── go.sum
```

## Go Embed Pattern (SPA Fallback)

In `internal/handler/spa.go`:

```go
package handler

import (
    "embed"
    "io/fs"
    "net/http"
    "strings"
)

//go:embed all:dist
var dist embed.FS

type SPA struct {
    handler http.Handler
}

func NewSPA() *SPA {
    sub, err := fs.Sub(dist, "dist")
    if err != nil {
        return &SPA{handler: nil}  // dev mode fallback
    }
    return &SPA{handler: http.FileServer(http.FS(sub))}
}

func (s *SPA) Serve(w http.ResponseWriter, r *http.Request) {
    if s.handler == nil {
        // Dev mode — return a helpful message pointing to Vite
        return
    }
    path := r.URL.Path
    if strings.Contains(path, ".") {
        s.handler.ServeHTTP(w, r)       // static assets
    } else {
        r.URL.Path = "/"
        s.handler.ServeHTTP(w, r)       // SPA fallback
    }
}
```

**⚠️ PITFALL: `//go:embed` needs the `dist` directory at compile time.** Create a placeholder `dist/.gitkeep` so `go build` works before the frontend is built. During Docker build, copy the real `dist/` from the frontend stage into the Go build context.

**Alternative: filesystem-based SPA serving.** If you prefer NOT to embed the frontend into the binary, serve dist/ from the filesystem at runtime. See `go-vue-fullstack` skill section "Filesystem-Based SPA Serving" for the multi-path handler pattern. **Critical pitfall:** when using filesystem SPA, you MUST copy `dist/` to the Docker runtime stage — the binary alone won't serve the frontend. Missing this gives a white page with no errors.

**⚠️ PITFALL: `go.sum` may not exist if only stdlib imports are used.** `go mod tidy` doesn't create `go.sum` when there are no external deps. Touch an empty `go.sum` before Docker build, or the `COPY go.mod go.sum ./` step fails.

## Multi-Stage Dockerfile

```dockerfile
# Stage 1: Build frontend
FROM node:22-alpine AS frontend
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Build Go backend with embedded frontend
FROM golang:1.24-alpine AS backend
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
COPY --from=frontend /src/dist internal/handler/dist
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /app ./cmd/server/

# Stage 3: Minimal runtime
FROM alpine:3.21
RUN adduser -D -h /home/app app
USER app
WORKDIR /home/app
COPY --from=backend /app .
EXPOSE 8080
ENTRYPOINT ["./app"]
```

Typical final image: 15–25 MB.

## Vite Dev Proxy

In `frontend/vite.config.js`, proxy `/api` to the Go backend during development:

```js
export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://localhost:8080'
    }
  }
})
```

Dev workflow: `go run ./cmd/server/` in one terminal, `npm run dev` in another.

## Homelab Integration

Follow the docker-homeserver "Adding a New Service" checklist, but with these specifics:

1. **docker-compose.yml**: Use `build:` instead of pre-built images for local projects:

```yaml
oathless-terminal:
  build: /home/ruben/project-name
  image: project-name:local
  container_name: project-name
  restart: unless-stopped
  networks:
    - homeserver
```

2. **Caddyfile**: Replace any existing static file_server with reverse_proxy:

```caddy
sub.oathless.dev {
    reverse_proxy project-name:8080
}
```

3. **Build & deploy**: `docker compose build <service> && docker compose up -d <service>`

4. **Caddy restart**: `docker compose restart caddy` (not reload — bind mount caching)

5. **Uptime Kuma**: Add HTTP monitor for `https://sub.oathless.dev`

## Automated Deploy Pipeline (Webhook → Deploy → Rollback)

For services deployed via Docker Compose with `build:` on the homelab, a webhook-based auto-deploy pipeline is the simplest CI/CD option. No runner containers, no cron polling — a small Python receiver on the host listens for push events from Forgejo (which is on the same Docker network), validates an HMAC signature, and runs a deploy script.

### Architecture

```
git push → Forgejo → POST webhook (HMAC-signed) → receiver (host:9090) → deploy script
                                                                           ↓
                                                               git pull → docker compose build
                                                                       → docker compose up -d
                                                                       → health check (10 retries)
                                                                       → rollback on failure
```

### Deploy script pattern

The script does a staged deploy with a safety net:
1. `git pull` — bail early if no new commits
2. `docker tag <image>:local <image>:rollback` — save current image
3. `docker compose build --no-cache <service>` — fresh build
4. `docker compose up -d <service>` — redeploy
5. Health check — `docker exec <service> wget -q http://localhost:8080`, retry 10× with 2s delay
6. On failure: `docker tag <image>:rollback <image>:local && docker compose up -d <service>` — restore the known-good image

### Webhook receiver pattern

Python stdlib only, zero dependencies. Validates `X-Forgejo-Signature` (HMAC-SHA256) against a shared secret. Only acts on `push` events to `main`.

Run as a **systemd user service** so Docker commands work with the user's docker group membership. The receiver listens on `0.0.0.0:<port>`; Forgejo (inside Docker) reaches it via the Docker bridge gateway, typically `172.18.0.1` for a custom bridge network.

Enable lingering if not already: `loginctl enable-linger $USER`.

### ⚠️ PITFALL: Docker network gateway for intra-network webhooks

When Forgejo runs in a Docker container and the webhook receiver runs on the host, Forgejo can't use `localhost` — it resolves to its own container. Use the Docker bridge gateway IP instead. Find it:
```bash
docker network inspect <network> --format '{{range .IPAM.Config}}{{.Gateway}}{{end}}'
```
Then register the webhook URL as `http://<gateway>:<port>/`.

### ⚠️ PITFALL: Health check reachability

Docker Compose services are often only on internal networks (not port-mapped to the host). A `curl http://localhost:8080` from the host won't reach them. Use `docker exec <container> wget -q http://localhost:8080` instead — it runs inside the container's network namespace.

Full deploy script and webhook receiver code: see `references/webhook-deploy-pipeline.md`.

## ⚠️ PITFALL: Docker build context with external path

When `build:` points to an absolute path outside the compose directory (like `/home/ruben/project-name`), ensure `.dockerignore` blocks `node_modules/`, built artifacts, and `.git/`. The build context is the directory containing the Dockerfile, not the compose directory.

## Tailwind CSS Theme via Variables

Define theme colors as CSS custom properties in `style.css`:

```css
@import "tailwindcss";

:root {
  --rp-base: #191724;
  --rp-surface: #1f1d2e;
  --rp-text: #e0def4;
  --rp-love: #eb6f92;
  --rp-gold: #f6c177;
  --rp-iris: #c4a7e7;
  --rp-foam: #9ccfd8;
  --rp-pine: #31748f;
  --rp-rose: #ebbcba;
  --rp-subtle: #908caa;
}
```

Then reference via `style="color: var(--rp-iris)"` in components. This keeps the theme centralized and swappable (supporting `theme` commands at runtime).

## References

- `references/go-vue-terminal.md` — Full terminal website implementation: Vue 3 terminal component, Go command registry, Rose Pine theme details, keyboard handling patterns.
- `references/webhook-deploy-pipeline.md` — Deploy script, webhook receiver, systemd service, and Forgejo config for auto-deploy pipelines with health check + rollback.
- `references/spa-filesystem-handler.md` (in go-vue-fullstack skill) — Filesystem-based SPA handler alternative to embed, with multi-path support for Docker + local dev.
