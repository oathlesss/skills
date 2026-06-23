---
name: go-vue-fullstack
description: Build and deploy Go backend + Vue 3 frontend apps as a single Docker container behind Caddy. Covers monorepo layout, Go embed for SPA, multi-stage Dockerfile, Vite proxy, Tailwind v4 setup, focus-management for reactive UIs, and homelab deployment.
triggers:
  - Building a Go + Vue website or webapp
  - Deploying a fullstack app to the homelab behind Caddy
  - Setting up a Go project with an embedded Vue SPA
  - Creating a terminal-style, CLI-style, or portfolio website
---

# Go + Vue Fullstack App

Monorepo pattern for a Go backend + Vue 3 frontend deployed as a **single Docker container** behind Caddy on the homelab.

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

The `//go:embed all:dist` directive reads from a `dist/` directory relative to the source file. In the Dockerfile, copy the Vue build output there before the Go build.

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

## Development Workflow

```bash
# Terminal 1: Go backend (rebuild on change)
cd project && go run ./cmd/server/

# Terminal 2: Vue frontend (hot reload via Vite)
cd project/frontend && npm run dev
```

Vite proxies `/api` to `localhost:8080` in dev mode. Open `http://localhost:5173`.
