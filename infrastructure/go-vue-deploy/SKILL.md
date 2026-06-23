---
name: go-vue-deploy
description: Build and deploy Go + Vue 3 + Tailwind full-stack apps to the Docker homelab — project structure, multi-stage Dockerfile, Go embed, Caddy config, and local/dev workflows.
triggers:
  - Building or deploying a Go + Vue website/app
  - "I want a website with Go backend and Vue frontend"
  - Deploying a full-stack app to the Docker homelab via Caddy
  - Adding a new web service behind the Caddy reverse proxy
  - Go embed + SPA fallback patterns
  - Terminal/CLI-style web app development
---

# Go + Vue + Docker Deployment

Build full-stack Go + Vue 3 + Tailwind apps and deploy them as a single Docker container behind Caddy.

## Project Structure

```
project/
├── cmd/server/main.go           # Entry point
├── internal/
│   ├── handler/
│   │   ├── api.go               # HTTP API handlers
│   │   ├── spa.go               # SPA fallback with go:embed
│   │   └── dist/                # Built Vue SPA (Docker build artifact)
│   └── commands/                # Business logic / command registry
├── frontend/                    # Vue 3 project (npm create vite@latest -- --template vue)
│   ├── src/
│   │   ├── components/
│   │   ├── App.vue
│   │   ├── main.js
│   │   └── style.css            # Tailwind + CSS custom properties
│   ├── index.html
│   ├── vite.config.js           # Tailwind plugin + API proxy for dev
│   └── package.json
├── Dockerfile                   # Multi-stage: node → go → alpine
├── .dockerignore
└── .gitignore
```

## Multi-Stage Dockerfile

```dockerfile
# Stage 1: Build Vue
FROM node:22-alpine AS frontend
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Build Go with embedded dist
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

## Go embed + SPA Fallback

```go
//go:embed all:dist
var dist embed.FS

func NewSPA() *SPA {
    sub, err := fs.Sub(dist, "dist")
    if err != nil {
        // Dev mode — dist not embedded yet
        return &SPA{handler: nil}
    }
    return &SPA{handler: http.FileServer(http.FS(sub))}
}

func (s *SPA) Serve(w http.ResponseWriter, r *http.Request) {
    if s.handler == nil {
        // Serve dev fallback HTML
        return
    }
    // Serve static files if they exist, otherwise index.html (SPA routing)
    if strings.Contains(r.URL.Path, ".") {
        s.handler.ServeHTTP(w, r)
        return
    }
    r.URL.Path = "/"
    s.handler.ServeHTTP(w, r)
}
```

## Vite Config (Dev Proxy)

```js
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    proxy: { '/api': 'http://localhost:8080' }
  }
})
```

## Homelab Integration

Add to `docker-compose.yml` (no host ports — routed through Caddy):

```yaml
app-name:
  build: /home/ruben/project-path
  image: app-name:local
  container_name: app-name
  restart: unless-stopped
  networks:
    - homeserver
```

Caddy entry:
```caddy
sub.oathless.dev {
    reverse_proxy app-name:8080
}
```

After adding, always add an Uptime Kuma monitor.

## Build & Deploy Workflow

```bash
cd /home/ruben/homeserver
docker compose build app-name
docker compose up -d app-name
docker compose restart caddy    # Pick up Caddyfile changes
```

## Common Pitfalls

### go.sum missing
Go modules with zero external dependencies produce no go.sum. Touch an empty file before Docker build:
```bash
touch go.sum
```

### Focus loss after DOM re-mount
When using `v-if` to show/hide an input, call `focusInput()` after `await nextTick()` in the `finally` block:
```js
finally {
  loading.value = false
  inputValue.value = ''
  await nextTick()
  focusInput()    // Re-focus after v-if re-creates the input
}
```

### CSS variable theme switching
Define theme palettes as JS objects, apply to `document.documentElement.style.setProperty()`. Persist to `localStorage`. Load saved theme on mount.

### Browser whitespace collapse
Trailing spaces in inline HTML elements collapse. Use `&amp;nbsp;` or CSS margin for visual gaps between inline spans.

### SPA fallback: hash vs history routing
Use `createWebHashHistory()` for simpler routing, or `createWebHistory()` with the Go SPA fallback pattern (serve index.html for all non-asset, non-API routes).

### Caddy restart vs reload
After editing Caddyfile, `docker compose restart caddy` — bind mount caching can cause `caddy reload` to report "config is unchanged" even after host-side edits.

## Reference

- `references/oathless-terminal-config.md` — oathless.dev specific config: commands, themes, UX decisions
