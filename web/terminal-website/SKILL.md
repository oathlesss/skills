---
name: terminal-website
description: Build terminal/CLI-style websites with Go backend + Vue 3 frontend + Tailwind CSS. Monorepo structure, multi-stage Docker, piping support, theme switching, and common pitfalls.
triggers:
  - Building a terminal/CLI-style portfolio or website
  - Go + Vue + Tailwind monorepo project
  - Terminal emulator in the browser (not xterm.js, custom component)
  - Adding pipe/grep support to a command-based website
  - Theme switching for terminal websites
  - Deploying a Go+SPA app to Docker behind Caddy
---

# Terminal Website (Go + Vue + Tailwind)

Build a website that looks and behaves like a terminal — visitors type commands, backend processes them, output renders with ANSI-like formatting.

## Project Structure

```
project/
├── cmd/server/main.go          # Entry point, HTTP mux
├── internal/
│   ├── commands/commands.go    # Command registry, all built-in commands
│   ├── handler/
│   │   ├── api.go              # POST /api/command + pipe pipeline
│   │   ├── spa.go              # //go:embed dist + SPA fallback
│   │   └── dist/               # Built Vue SPA (copied from frontend/dist)
├── frontend/                   # Vue 3 + Vite + Tailwind
│   ├── src/
│   │   ├── components/Terminal.vue
│   │   ├── App.vue
│   │   ├── main.js
│   │   └── style.css
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── Dockerfile                  # Multi-stage: node → go → alpine
├── .gitignore
├── go.mod
└── go.sum                      # Can be empty if no external deps
```

## Key Architectural Decisions

**Custom Vue component over xterm.js:** For a portfolio (no real shell), a custom component is simpler, lighter, and gives full control over styling. xterm.js is overkill unless you need actual PTY/WebSocket shell access.

**Go embed over separate static serving:** Single binary with `//go:embed all:dist` embeds the Vue build. Go serves API at `/api/*` and falls back to `index.html` for SPA routing.

**go.sum can be empty:** If the Go module has zero external dependencies (only stdlib + local packages), `go.sum` will be empty. Docker's `COPY go.mod go.sum ./` still works with an empty file — just `touch go.sum`. The Dockerfile needs the file to exist even if it's empty.

## Frontend: Terminal Component

### Focus Management (Critical)

When using `v-if="!loading"` to hide the input during API calls, the `<input>` element is removed from the DOM. After `loading` becomes `false`, Vue re-creates the input — but focus is lost. **Always re-focus after the v-if remounts:**

```js
} finally {
    loading.value = false
    inputValue.value = ''
    scrollToBottom()
    await nextTick()    // wait for DOM update
    focusInput()        // re-focus the hidden input
}
```

### Prompt Spacing

Browsers collapse whitespace between inline elements. HTML entities in template content are the only reliable approach:

```html
<!-- WRONG: space collapses, mr-1 may not apply -->
<span>❯ </span>

<!-- RIGHT: non-breaking space never collapses -->
<span>❯&nbsp;</span>
```

The `&nbsp;` approach is bulletproof where Tailwind margin classes might fail due to CSS generation order or specificity issues.

### Theme Switching

Define palettes as JS objects, swap CSS custom properties on `:root`, persist to localStorage:

```js
const themes = {
  'rose-pine': { base: '#191724', text: '#e0def4', ... },
  green: { base: '#0d1117', text: '#c9d1d9', ... },
}

function applyTheme(name) {
  const t = themes[name] || themes['rose-pine']
  for (const [key, value] of Object.entries(t)) {
    document.documentElement.style.setProperty(`--rp-${key}`, value)
  }
  localStorage.setItem('theme', name)
}

// Load saved theme on mount
const saved = localStorage.getItem('theme')
if (saved && themes[saved]) applyTheme(saved)
```

Channel theme changes through the API response type (`"theme:green"`) so the backend controls which themes are valid.

### Local vs Server Commands

Commands that depend on browser state (`history`, `clear`) should be intercepted before the API call:

```js
if (trimmed === 'history') {
  // render history locally, return immediately
  return
}
if (trimmed.startsWith('history | grep ')) {
  // local pipe handling
  return
}

// Otherwise, send to API
fetch('/api/command', ...)
```

## Backend: Command Registry + Piping

### Command Registry Pattern

```go
type Registry struct {
    commands map[string]func(args []string) Response
}

type Response struct {
    Output string `json:"output"`
    Type   string `json:"type"` // "text", "error", "clear", "theme:green"
}
```

### Pipe Implementation

Split on `|`, execute stages sequentially, feed output forward:

```go
func (a *API) executePipeline(raw string) Response {
    stages := strings.Split(raw, "|")
    var input string
    for i, stage := range stages {
        cmd, args := parseCommand(strings.TrimSpace(stage))
        var result Response
        if i == 0 {
            result = a.registry.Execute(cmd, args)
        } else {
            result = a.registry.ExecuteWithInput(cmd, args, input)
        }
        // Special types propagate immediately
        if result.Type == "clear" || strings.HasPrefix(result.Type, "theme:") {
            return result
        }
        if result.Type == "error" {
            return result
        }
        input = result.Output
    }
    return Response{Output: input, Type: "text"}
}
```

Commands that accept piped input (like `grep`) need a separate `ExecuteWithInput` method — don't try to overload `Execute`.

### Docker Hostname Pitfall

`os.Hostname()` returns the Docker container ID, not the host machine name. Hardcode the domain name instead (`oathless.dev`).

### Real Uptime in Containers

Read `/proc/uptime` — it works inside containers and reflects the host's uptime:

```go
func formatUptime() string {
    data, _ := os.ReadFile("/proc/uptime")
    parts := strings.Fields(string(data))
    var seconds float64
    fmt.Sscanf(parts[0], "%f", &seconds)
    days := int(seconds) / 86400
    hours := (int(seconds) % 86400) / 3600
    minutes := (int(seconds) % 3600) / 60
    return fmt.Sprintf("%dd %dh %dm", days, hours, minutes)
}
```

## Docker

### Multi-Stage Dockerfile

```dockerfile
# Stage 1: Build Vue
FROM node:22-alpine AS frontend
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Build Go with embedded SPA
FROM golang:1.24-alpine AS backend
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
COPY --from=frontend /src/dist internal/handler/dist
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /app ./cmd/server/

# Stage 3: Runtime
FROM alpine:3.21
RUN adduser -D -h /home/app app
USER app
COPY --from=backend /app .
EXPOSE 8080
ENTRYPOINT ["./app"]
```

Final image: ~20 MB.

### Homelab Deployment

Add to `docker-compose.yml`:

```yaml
oathless-terminal:
  build: /path/to/project
  image: oathless-terminal:local
  container_name: oathless-terminal
  restart: unless-stopped
  networks:
    - homeserver
```

Caddy reverse proxy:

```caddy
oathless.dev, www.oathless.dev {
    reverse_proxy oathless-terminal:8080
}
```

Add Uptime Kuma monitor:
```bash
docker exec uptime-kuma sqlite3 /app/data/kuma.db \
  "INSERT INTO monitor (name, active, user_id, interval, url, type, ...) VALUES (...);"
```

### Development Workflow

Vite dev server proxies `/api` to Go backend on `:8080`:
```js
// vite.config.js
server: { proxy: { '/api': 'http://localhost:8080' } }
```

Run Go backend locally with `go run ./cmd/server/` (the `//go:embed` fails in dev — the SPA handler falls back to a dev-mode HTML message).

## Pitfalls

- **`v-if` + focus**: Always `await nextTick()` then refocus after remounting hidden inputs.
- **HTML whitespace collapse**: Use `&nbsp;` for spacing, not CSS margins or regular spaces.
- **`npm install` foreground detection**: The terminal tool may flag npm install as a server process. Use `background=true` with `notify_on_complete=true`.
- **`go.sum` missing**: If the module has no external deps, `go.sum` won't be created. `touch go.sum` before Docker build.
- **Docker hostname**: `os.Hostname()` returns container ID. Hardcode domain names.
- **`docker compose up -d` foreground detection**: Same as npm — use background mode.