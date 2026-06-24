---
name: go-vue-fullstack
description: Build and deploy Go backend + Vue 3 frontend apps as a single Docker container behind Caddy. Covers monorepo layout, Go embed for SPA, multi-stage Dockerfile, Vite proxy, Tailwind v3/v4 setup, focus-management for reactive UIs, homelab and Hetzner Cloud deployment, and Forgejo repo creation.
triggers:
  - Building a Go + Vue website or webapp
  - Deploying a fullstack app to the homelab or Hetzner Cloud behind Caddy
  - Setting up a Go project with an embedded Vue SPA
  - Creating a terminal-style, CLI-style, or portfolio website
  - Scaffolding a new fullstack project with PLAN.md and Forgejo repo
---

# Go + Vue Fullstack App

Monorepo pattern for a Go backend + Vue 3 frontend deployed as a **single Docker container** behind Caddy on the homelab.

## Project Setup

### Scaffolding a new project

1. Create a `PLAN.md` first — architecture, tech choices, deployment, monetization strategy
2. Scaffold: `mkdir -p project/{backend/{handlers,db,auth},frontend/src/{components,lib,assets},scripts}`
3. `git init && git branch -m main`
4. Create the repo on Forgejo (see `references/forgejo-repo-create.md`) and push

## Project Structure

```
project/
├── cmd/server/main.go       # Entry point
├── internal/
│   ├── handler/
│   │   ├── api.go           # JSON API handlers
│   │   ├── spa.go           # SPA fallback with //go:embed
│   │   └── dist/            # Vue build output (copied in Dockerfile)
│   └── commands/            # Business logic
├── frontend/                # Vue 3 + Vite project
│   ├── src/
│   │   ├── components/
│   │   ├── App.vue
│   │   ├── main.js
│   │   └── style.css
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── Dockerfile               # Multi-stage: node → go → alpine
├── go.mod
└── go.sum
```

## Go: Embed Vue SPA + API + SPA Fallback

### Embed pattern (`internal/handler/spa.go`)

Two approaches — use the **file-existence pattern** (recommended) for robustness, or the **dot-check pattern** for simplicity when you're confident all static assets have file extensions.

**Recommended: file-existence pattern** (from `### Robust SPA handler` pitfall section above):

```go
package handler

import (
    "embed"
    "io/fs"
    "net/http"
    "path/filepath"
    "strings"
)

//go:embed all:dist
var dist embed.FS

func SPAHandler() http.HandlerFunc {
    staticFS, err := fs.Sub(dist, "dist")
    if err != nil {
        return func(w http.ResponseWriter, r *http.Request) {
            http.Error(w, "SPA not available", 503)
        }
    }

    return func(w http.ResponseWriter, r *http.Request) {
        path := strings.TrimPrefix(r.URL.Path, "/")
        f, err := staticFS.Open(path)
        if err == nil {
            defer f.Close()
            if stat, _ := f.Stat(); !stat.IsDir() {
                http.FileServer(http.FS(staticFS)).ServeHTTP(w, r)
                return
            }
        }
        // SPA fallback
        index, _ := fs.ReadFile(staticFS, "index.html")
        if ext := filepath.Ext(r.URL.Path); ext != "" {
            w.Header().Set("Content-Type", contentType(ext))
        }
        w.Write(index)
    }
}
```

**Simpler: dot-check pattern** (good enough when all static assets have file extensions and no partial-path routes exist):

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
        return &SPA{handler: nil} // dev fallback
    }
    return &SPA{handler: http.FileServer(http.FS(sub))}
}

func (s *SPA) Serve(w http.ResponseWriter, r *http.Request) {
    if strings.Contains(r.URL.Path, ".") {
        s.handler.ServeHTTP(w, r) // static assets
        return
    }
    r.URL.Path = "/"             // SPA fallback
    s.handler.ServeHTTP(w, r)
}
```

The `//go:embed all:dist` directive reads from a `dist/` directory relative to the source file. The `all:` prefix includes hidden files (starting with `.` or `_`). Without `all:`, hidden files are skipped — for frontend builds this rarely matters, but use `all:` to be safe.

In the Dockerfile, copy the Vue build output there before the Go build. See the pitfall above about COPY trailing slashes.

### API handler pattern

```go
func (a *API) HandleCommand(w http.ResponseWriter, r *http.Request) {
    var req Request
    json.NewDecoder(r.Body).Decode(&req)
    // ... process ...
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(Response{Output: "...", Type: "text"})
}
```

### main.go wiring

```go
mux := http.NewServeMux()
api := handler.NewAPI()
mux.HandleFunc("POST /api/command", api.HandleCommand)
spa := handler.NewSPA()
mux.HandleFunc("/", spa.Serve)
```

## Docker: Multi-Stage Build

```dockerfile
# Stage 1: Build Vue frontend
FROM node:22-alpine AS frontend
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit   # npm install works without lockfile; use npm ci when lockfile exists
COPY frontend/ ./
RUN npm run build
```

**⚠️ PITFALL: `npm ci` vs `npm install` in Docker:** `npm ci` requires a `package-lock.json` and fails if it's missing (e.g., new projects before `npm install` has been run locally). Use `npm install --no-audit` for the initial Dockerfile — it works with or without a lockfile. Once you have a committed lockfile, switch to `npm ci` for reproducible builds. The `*` glob in `COPY frontend/package-lock.json*` makes the COPY not fail when the file is absent.
# Stage 2: Build Go backend with embedded frontend
FROM golang:1.24-alpine AS backend
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
COPY --from=frontend /src/dist internal/handler/dist
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /app ./cmd/server/

# Stage 3: Minimal runtime (~20 MB)
FROM alpine:3.21
RUN adduser -D -h /home/app app
USER app
WORKDIR /home/app
COPY --from=backend /app .
EXPOSE 8080
ENTRYPOINT ["./app"]
```

If the module has no external dependencies, `go.sum` will be empty. Create it with `touch go.sum` so the Docker COPY doesn't fail.

## Vue Frontend: Vite + Tailwind v4

### vite.config.js

```js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://localhost:8080'  // dev: proxy API to Go
    }
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true
  }
})
```

### CSS with Tailwind v4

```css
@import "tailwindcss";

/* Custom properties for theming */
:root {
  --color-text: #e0def4;
  --color-accent: #c4a7e7;
  /* ... */
}
```

TL;DR: Tailwind v4 uses `@import "tailwindcss"` (not `@tailwind base/components/utilities`). Install with `npm install -D tailwindcss @tailwindcss/vite`. No `tailwind.config.js` needed — configure in CSS.

Apply to base elements with plain CSS selectors — Tailwind v4 generates utilities from the CSS, not a config file.

### ⚠️ PITFALL: Go install

Go may not be installed on the host. Install without sudo:

```bash
curl -fsSL "https://go.dev/dl/go1.24.5.linux-amd64.tar.gz" -o /tmp/go.tar.gz
tar -xzf /tmp/go.tar.gz -C ~/.local/
export PATH="$HOME/.local/go/bin:$PATH"
go version
```

Prepend `export PATH="$HOME/.local/go/bin:$PATH"` to any `go` command.

### ⚠️ PITFALL: go.sum missing with zero dependencies

If the Go module has no external dependencies (only stdlib), `go mod tidy` won't create a `go.sum`. The Dockerfile's `COPY go.mod go.sum ./` will fail. Fix:

```bash
touch go.sum
```

This creates an empty file that satisfies Docker's COPY.

### ⚠️ PITFALL: Docker COPY trailing slashes change behavior

When copying a directory between Docker stages, trailing slashes on source and destination change what gets copied:

```dockerfile
# WRONG — copies the dist directory INTO ./dist, creating ./dist/dist/
COPY --from=frontend /src/dist ./dist

# RIGHT — copies the CONTENTS of dist/ INTO ./dist/
COPY --from=frontend /src/dist/ ./dist/
```

- **No trailing slash on source:** copies the directory itself (e.g., `./dist/dist/`)
- **Trailing slash on source:** copies the directory contents (e.g., `./dist/index.html`)

This is especially dangerous when the destination directory already exists from a previous COPY — Docker merges, so the stub files remain alongside the real files buried one level deeper. The Go embed picks up the stub and the build succeeds silently with the wrong frontend. Always verify with `RUN ls -la dist/` after the COPY during debugging.

### ⚠️ PITFALL: embed.FS.Open rejects leading slash

`embed.FS.Open()` and `fs.Sub().Open()` reject paths with a leading `/` (per `fs.ValidPath`). But `r.URL.Path` always starts with `/`. A manual file-existence check **must** strip it:

```go
path := strings.TrimPrefix(r.URL.Path, "/")
f, err := staticFS.Open(path)
```

`http.FileServer(http.FS(fsys))` handles this internally — `http.FS.Open` strips the `/`. So the pre-check needs the trim but the FileServer call does not.

### Robust SPA handler (file-existence pattern)

The `strings.Contains(r.URL.Path, ".")` shortcut (serve static if path has a dot, else SPA fallback) works for simple cases but fails when a JS file doesn't actually exist — the handler silently serves `index.html` with a `.js` content type, and the browser gets a white page with no error.

A more robust pattern actually checks whether the file exists:

```go
func spaHandler(embedded embed.FS, root string) http.HandlerFunc {
    staticFS, err := fs.Sub(embedded, root)
    if err != nil {
        log.Fatalf("spa: %v", err)
    }

    return func(w http.ResponseWriter, r *http.Request) {
        path := strings.TrimPrefix(r.URL.Path, "/")

        // Try to serve the exact file
        f, err := staticFS.Open(path)
        if err == nil {
            defer f.Close()
            stat, _ := f.Stat()
            if !stat.IsDir() {
                http.FileServer(http.FS(staticFS)).ServeHTTP(w, r)
                return
            }
        }

        // SPA fallback: serve index.html
        index, err := fs.ReadFile(staticFS, "index.html")
        if err != nil {
            http.Error(w, "Not found", 404)
            return
        }

        if ext := filepath.Ext(r.URL.Path); ext != "" {
            w.Header().Set("Content-Type", contentType(ext))
        }
        w.Write(index)
    }
}
```

Key details:
- `fs.Sub(embedded, root)` strips the `dist/` prefix so `http.FileServer` finds files at their URL paths
- `r.URL.Path` → trim `/` → `staticFS.Open()` for the existence check
- `http.FileServer(http.FS(staticFS))` handles content types and range requests
- Fallback sets the correct Content-Type for any `.js`/`.css` files that land here (prevents MIME mismatch errors)
- The `//go:embed dist` directive (without `all:`) skips hidden files — use `//go:embed all:dist` if you need them

## Vue: Focus Management with v-if

When an input element is wrapped in `v-if`, it's removed from the DOM when the condition is false and re-created when true. Focus is lost on re-creation.

**Fix pattern:**

```js
async function submitCommand(cmd) {
  loading.value = true          // v-if hides the input
  try {
    await fetch(...)
  } finally {
    loading.value = false       // v-if re-creates the input
    inputValue.value = ''
    await nextTick()            // wait for DOM update
    focusInput()                // re-focus after re-mount
  }
}
```

Always `await nextTick()` before focusing an element that was just re-created by Vue.

### ⚠️ PITFALL: Whitespace collapsing in flex layouts

A trailing space inside a `<span>` in a flex container collapses when the next sibling starts. Use `&nbsp;` for a non-collapsible space:

```html
<!-- WRONG — space collapses -->
<span>❯ </span><span>{{ text }}</span>

<!-- RIGHT — non-breaking space preserved -->
<span>❯&nbsp;</span><span>{{ text }}</span>
```

Tailwind `mr-1` (margin-right) may also work but depends on the Tailwind version and build output. `&nbsp;` is the most reliable approach.

## Deploy to Homelab

### docker-compose.yml entry

```yaml
oathless-terminal:
  build: /home/ruben/project-name
  image: project-name:local
  container_name: project-name
  restart: unless-stopped
  networks:
    - homeserver
```

### Caddyfile entry

```caddy
domain.oathless.dev {
    reverse_proxy container-name:8080
}
```

Remove any old static file server entry for the same domain.

### Build and deploy sequence

```bash
cd /home/ruben/homeserver
docker compose build container-name
docker compose up -d container-name
docker compose restart caddy
```

Verify: `curl -sk https://domain.oathless.dev/ | head -5`

### Add Uptime Kuma monitor

```bash
docker exec uptime-kuma sqlite3 /app/data/kuma.db \
  "INSERT INTO monitor (name, active, user_id, interval, url, type, weight, created_date, maxretries, ignore_tls, upside_down, maxredirects, accepted_statuscodes_json, retry_interval, method, timeout, description) VALUES ('Service Name', 1, 1, 60, 'https://domain.oathless.dev', 'http', 2000, datetime('now'), 3, 0, 0, 10, '[\"200\"]', 60, 'GET', 48, 'Description');"
```

No restart needed — Uptime Kuma reads monitors from DB on each check cycle.

## Hetzner Cloud Deployment

When the project should NOT run on the homelab (e.g., a SaaS product), use Hetzner Cloud:

### Provision VM

```bash
# Hetzner Cloud CX22: 2 vCPU, 4GB RAM, 40GB SSD, ~€4.25/mo
# OS: Ubuntu 24.04 LTS, SSH key only
# Firewall: allow 80, 443; allow 22 from your IP only
```

### DNS

Point domain A record to Hetzner IP. Also add `www` → redirect to apex.

### Install on VM

```bash
ssh root@<ip>
apt-get update && apt-get install -y docker.io docker-compose-v2 unattended-upgrades
```

### Deploy

Same Docker approach as homelab but without the homeserver compose file. Ship the project directly:

```bash
# From local:
rsync -avz --exclude 'node_modules' --exclude 'frontend/dist' ./ root@<ip>:/opt/fmtthis/
ssh root@<ip> "cd /opt/fmtthis && docker compose up -d --build"
```

Or use a standalone `docker-compose.yml` in the project root:

```yaml
services:
  app:
    build: .
    image: project-name:local
    container_name: project-name
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./data:/home/app/data  # SQLite persistence
```

### Docker Compose env var interpolation

When setting environment variables in `docker-compose.yml`, Docker Compose tries to substitute `${VAR}` patterns from the shell or `.env` file. Hardcoded placeholder values like `***` can trigger interpolation errors. **Use bare variable references** that pull from `.env`:

```yaml
# WRONG — Compose tries to interpolate
environment:
  - STRIPE_SECRET_KEY=sk_live_***
# RIGHT — pulls from .env file, empty if unset
environment:
  - STRIPE_SECRET_KEY
```

The bare reference form (`VAR_NAME` without `=value`) tells Compose to look up the variable from the environment or `.env` file. If unset, the variable is empty — the app handles it gracefully (e.g., disables payments with a warning log).

Install Caddy directly or run in Docker. If directly:

```bash
apt-get install -y caddy
```

`/etc/caddy/Caddyfile`:
```caddy
fmtthis.dev {
    reverse_proxy localhost:8080
}
```

### Monthly Costs

| Item | Cost |
|------|------|
| Hetzner CX22 | ~€4.25 |
| Domain (.dev) | ~$12/year |
| **Total** | **~€5.50/mo** |

Break-even is typically 2-5 paid users.

### Tailwind v3 (alternative to v4)

The default setup above uses Tailwind v4 (`@import "tailwindcss"`, no config file). Some projects use Tailwind v3 with explicit config files — especially when using a theme palette like Rose Pine that benefits from `tailwind.config.js`:

```js
// tailwind.config.js (v3)
export default {
  content: ["./index.html", "./src/**/*.{vue,js}"],
  theme: {
    extend: {
      colors: {
        base: '#191724',
        surface: '#1f1d2e',
        text: '#e0def4',
        iris: '#c4a7e7',
        // ... full Rose Pine palette
      }
    }
  }
}
```

```css
/* style.css (v3) */
@tailwind base;
@tailwind components;
@tailwind utilities;
```

Install: `npm install -D tailwindcss@3 postcss autoprefixer` (no `@tailwindcss/vite`). Both v3 and v4 are valid — v3 is more explicit for custom themes, v4 is simpler for standard setups.

## Development Workflow

**Primary (Docker-first — zero local deps, preferred):**

```bash
# Build and run everything in Docker — no Node, no Go, no npm required locally
docker compose up -d --build

# Open http://localhost:8080
# Rebuild on changes: docker compose up -d --build
```

Use a simple `docker-compose.yml` without Caddy for local dev (just the app on `:8080`). Keep a separate `docker-compose.prod.yml` with Caddy for production.

**Alternative (for rapid frontend iteration):**

```bash
# Terminal 1: Go backend (rebuild on change)
cd project && go run ./cmd/server/

# Terminal 2: Vue frontend (hot reload via Vite)
cd project/frontend && npm run dev
```

Vite proxies `/api` to `localhost:8080` in dev mode. Open `http://localhost:5173`.

Prefer Docker-first for the build-test cycle — it's the same command for local and production and avoids environment-specific bugs.

## References

- `references/sqlite-stripe-patterns.md` — SQLite (modernc.org/sqlite, pure Go, WAL mode) + Stripe subscription checkout/webhook flow + API key generation for micro-SaaS backends.
- `references/forgejo-repo-create.md` — Creating repos on Forgejo via API.
- `references/domain-check.md` — Checking domain name availability with `dig +short NS` (no whois needed).
