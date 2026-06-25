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
4. Create the repo on Forgejo via the API (`references/forgejo-repo-create.md`), then push. Push-to-create is disabled on this instance — you MUST create the repo BEFORE pushing.
5. **⚠️ MANDATORY: Verify repo is private.** Although the API create call sets `"private":true`, verify anyway:

```bash
TOKEN=$(printf "protocol=https\nhost=git.oathless.dev\n" | git credential fill 2>/dev/null | grep password | cut -d= -f2)
VIS=$(curl -sf -H "Authorization: token $TOKEN" "https://git.oathless.dev/api/v1/repos/oathless/<repo>" | jq -r .private)
if [ "$VIS" != "true" ]; then
  curl -sf -X PATCH -H "Authorization: token $TOKEN" -H "Content-Type: application/json" \
    -d '{"private":true}' "https://git.oathless.dev/api/v1/repos/oathless/<repo>"
fi
```

If the token-redaction pitfall (see `references/forgejo-repo-create.md`) blocks multi-call patterns, chain extract+verify+flip in a single `terminal()` invocation.

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

### Database: jmoiron/sqlx (default)

For any project needing a database, use `jmoiron/sqlx` with `modernc.org/sqlite` as the driver (pure Go, no CGO). sqlx provides `StructScan`, named parameters, and `In()` expansion — cleaner than raw `database/sql`.

```go
import (
    "github.com/jmoiron/sqlx"
    _ "modernc.org/sqlite"
)

db, err := sqlx.Open("sqlite", "./data/app.db?_journal_mode=WAL")
```

**go.mod setup (minimal):**
```
module github.com/oathless/project
go 1.24
require (
    github.com/jmoiron/sqlx v1.4.0
    modernc.org/sqlite v1.34.0
)
```

Then `go mod tidy` to resolve indirect deps. Reuse a known-good `go.sum` from a sibling project (e.g., `github.com/oathless/fmtthis`) to avoid version-resolution churn.

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

## Go: Filesystem-Based SPA Serving (Alternative to Embed)

Full code and Dockerfile requirements in `references/spa-filesystem-handler.md`.

When `embed.go` is overkill (e.g., a simple project where the binary reads dist/ from disk at runtime), use a filesystem-based SPA handler instead. The handler tries multiple paths so it works both locally and in Docker:

```go
type spaHandler struct {
    roots []string
}

func (s *spaHandler) findRoot() string {
    for _, root := range s.roots {
        if info, err := os.Stat(root); err == nil && info.IsDir() {
            return root
        }
    }
    return s.roots[0]
}

func (s *spaHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
    root := s.findRoot()
    fs := http.FileServer(http.Dir(root))
    path := root + r.URL.Path
    if _, err := os.Stat(path); err == nil {
        fs.ServeHTTP(w, r)
        return
    }
    http.ServeFile(w, r, root+"/index.html")
}

// Wire up: spaHandler{roots: []string{"dist", "../frontend/dist"}}
```

**⚠️ PITFALL: When using filesystem SPA (not embed), the Dockerfile MUST copy dist/ to the runtime stage.** Embed bundles dist into the binary at compile time; filesystem SPA reads it from disk at runtime. If you only copy the binary but not dist/, the frontend serves a blank white page with no errors:

```dockerfile
# WRONG — only copies binary, dist/ is missing at runtime
COPY --from=backend-builder /myapp /app/myapp

# RIGHT — copy both the binary AND the dist directory
COPY --from=backend-builder /myapp /app/myapp
COPY --from=backend-builder /src/dist/ /app/dist/
```

The Go build stage has dist/ from `COPY --from=frontend-builder /src/frontend/dist/ ./dist/`. You need ANOTHER copy in the runtime stage. Without it, the multi-path handler finds nothing and `http.FileServer` returns empty responses.

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

### ⚠️ PITFALL: go.sum missing or stale

Two failure modes for the `COPY go.mod go.sum ./` step in the Dockerfile:

**A) Zero dependencies (stdlib only):** `go mod tidy` won't create a `go.sum`. Fix with `touch go.sum` to create an empty file that satisfies Docker's COPY.

**B) Newly added dependencies, no `go mod tidy` run yet:** `go.sum` exists but lacks entries for new deps. The `go mod download` step in Docker fails with `missing go.sum entry for module providing package <pkg>`. Fix: run `go mod tidy` on the host before `docker compose build`. The Docker build cannot generate `go.sum` — it must exist and be complete at `COPY` time.

Rule: after any `go get` or `go.mod` edit, run `go mod tidy` before building.

### ⚠️ PITFALL: Bind mount permissions for non-root containers (SQLite data)

When the Dockerfile uses `USER app` (non-root) and docker-compose bind-mounts a SQLite data directory, the mount inherits the host directory's ownership. If the host dir is owned by `root` (e.g., created by Docker Compose itself) and the container runs as `app` (uid 1000), the SQLite driver fails on first write:

```
unable to open database file: out of memory (14)
```

The `(14)` is SQLite error code `SQLITE_CANTOPEN` — a permission denied disguised as an OOM message.

**Fix — two approaches:**

**A) docker-compose `user:` directive (recommended for homelab):**
Remove `USER app` from the Dockerfile (keep the `adduser -D` line for home-dir setup). Set `user: "1000:1000"` in docker-compose to match the host user's UID. Pre-create the data directory with the host user's ownership:

```bash
mkdir -p data && chown ruben:ruben data   # or: chown 1000:1000 data
```

```yaml
# docker-compose.yml
services:
  app:
    user: "1000:1000"
    volumes:
      - ./data:/home/app/data
```

**B) Dockerfile chown before USER switch (for Hetzner/non-homelab):**
Create and chown the data dir as root, then switch to the app user. This works when no bind mount is used (Docker volume instead) — the volume inherits the permissions from the image layer:

```dockerfile
RUN adduser -D -h /home/app app && mkdir -p /home/app/data && chown app:app /home/app/data
USER app
```

Use approach A when bind-mounting a host directory that must persist across rebuilds. Use approach B for named Docker volumes or when the data dir is self-contained in the image.

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

### ⚠️ PITFALL: go:embed fails on empty dist/ during local builds

`//go:embed all:dist` requires the `dist/` directory to contain at least one file. The Dockerfile copies the Vue build output there before the Go stage, but a bare `go build ./cmd/server/` on the host fails with:

```
pattern all:dist: no matching files found
```

**Fix:** Create a stub `internal/handler/dist/index.html` so local builds work:

```bash
mkdir -p internal/handler/dist
echo '<!DOCTYPE html><html><body>SPA stub</body></html>' > internal/handler/dist/index.html
```

This gets overwritten by the real build output during Docker builds (via `COPY --from=frontend /src/dist/ internal/handler/dist/`). The stub exists only so `go build` doesn't reject the embed directive. Add `internal/handler/dist/` to `.gitignore` to avoid committing stale stubs after a real frontend build.

### ⚠️ PITFALL: SQLite + bind-mount permission error ("out of memory (14)")

When using `modernc.org/sqlite` with a bind-mounted data directory, Docker Compose creates the host directory as `root:root`. If the container runs as a non-root user (via `USER app` in Dockerfile), SQLite can't write to the data dir and fails with `unable to open database file: out of memory (14)` — a misleading error. The DB path is fine; it's a permission issue.

**Fix — two changes:**

1. **Dockerfile:** chown the data dir while still root, then drop privileges:
```dockerfile
RUN adduser -D -h /home/app app && mkdir -p /home/app/data && chown app:app /home/app/data
# Remove USER app — let docker-compose set the UID
```

2. **docker-compose.yml:** set `user: "1000:1000"` to match the host user's UID so bind-mount permissions align:
```yaml
services:
  app:
    user: "1000:1000"
    volumes:
      - ./data:/home/app/data
```

Pre-create the host data dir with the same ownership: `mkdir -p data && chown 1000:1000 data`.

Alternative: use a Docker named volume (`volumes: - app_data:/home/app/data` + `volumes: app_data:` at bottom), which Docker manages permissions for automatically. But bind mounts are simpler for backups and local dev.

### ⚠️ PITFALL: go.mod indirect dependency version errors

When using `modernc.org/sqlite` (or any module with many indirect deps), copying a `go.mod` from another project can introduce version mismatches. A dependency like `github.com/mattn/go-isatty v0.20.0` may not exist — the correct version for the resolution path may be `v0.0.20` or the dep may not be needed at all.

**Symptoms:**
```
go: downloading github.com/mattn/go-isatty v0.20.0
... reading go.mod at revision v0.20.0: unknown revision v0.20.0
```

**Fix — start minimal and let `go mod tidy` resolve everything:**

```bash
# Delete the broken go.mod and go.sum, write a minimal version
rm go.mod go.sum

cat > go.mod << 'EOF'
module github.com/oathless/project

go 1.24

require modernc.org/sqlite v1.34.0
EOF

go mod tidy   # resolves all indirect deps correctly
```

The minimal `go.mod` has only `module`, `go`, and `require` for direct deps. `go mod tidy` downloads and pins all transitive dependencies at working versions. Only after `go mod tidy` succeeds should you commit `go.sum`.

**Better approach — reuse a known-good go.sum from a sibling project:**
If you have another Go 1.24 project using the same direct deps (e.g., `github.com/oathless/fmtthis`), copy its `go.sum` instead of rebuilding from scratch. The versions are pinned and known to resolve.

### ⚠️ PITFALL: Don't scaffold without explicit project selection

When presenting project ideas (e.g., from an idea list), do NOT autonomously pick one and start building. Wait for the user to say which specific project to build. "Create" or "build something" is not enough — get the project name/number confirmed first. The user decides what gets built; present options, then wait.

### ⚠️ PITFALL: Cross-reference existing projects before suggesting ideas

Check the user's existing projects before presenting build ideas. Don't suggest building something that already exists (e.g., fmtthis.dev already covers JSON/YAML/TOML formatting). Check `/home/ruben/` for existing project directories and cross-reference with any idea lists.

### ⚠️ PITFALL: Don't jump to deployment before the product is ready

Build and verify the product first. Don't ask the user about hosting, domains, DNS, or deployment until the product is tested and working locally. The user handles hosting on their own schedule. Adding Caddy entries or Hetzner provisioning when the user just wants code is premature.

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

## Vue: Text Highlight Overlay

For regex playgrounds, code editors, or any UI that highlights spans inside a `<textarea>`: stack a read-only highlight `<div>` behind a transparent `<textarea>`. See `references/vue-text-highlight-overlay.md` for the full pattern, pitfalls, and when to use CodeMirror instead.

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
- `references/vue-text-highlight-overlay.md` — Regex/match highlighting in a `<textarea>` via stacked transparent layers.
