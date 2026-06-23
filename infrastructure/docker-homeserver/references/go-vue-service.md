# Go + Vue SPA Service Pattern

## Project Structure

```
project/
├── cmd/server/main.go         # Entry point, wires API + SPA
├── internal/
│   ├── handler/
│   │   ├── api.go              # POST /api/command, pipe support
│   │   ├── spa.go              # //go:embed all:dist, SPA fallback
│   │   └── dist/               # Vue build output (copied here before Go build)
│   └── commands/               # Command registry, Execute + ExecuteWithInput
├── frontend/                   # Vue 3 + Vite + Tailwind
│   ├── src/components/
│   ├── vite.config.js          # Proxy /api → localhost:8080 in dev
│   └── package.json
├── Dockerfile                  # Multi-stage: node → go → alpine
├── go.mod
└── go.sum
```

## Dockerfile (Multi-Stage)

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

# Stage 3: Minimal runtime (~20 MB final image)
FROM alpine:3.21
RUN adduser -D -h /home/app app
USER app
WORKDIR /home/app
COPY --from=backend /app .
EXPOSE 8080
ENTRYPOINT ["./app"]
```

## Go Embed Pattern

```go
//go:embed all:dist
var dist embed.FS

func NewSPA() *SPA {
    sub, err := fs.Sub(dist, "dist")
    if err != nil {
        // Dev mode fallback
        return &SPA{handler: nil}
    }
    return &SPA{handler: http.FileServer(http.FS(sub))}
}
```

**⚠️ PITFALL: `go.sum` may be empty.** If the Go module has zero external dependencies (only stdlib + local packages), `go mod tidy` produces an empty `go.sum`. Docker `COPY go.sum ./` fails with "not found". Fix: `touch go.sum` before building.

**⚠️ PITFALL: `//go:embed` needs the dist directory at compile time.** In the Dockerfile, `COPY --from=frontend /src/dist internal/handler/dist` must happen before `go build`. Locally, copy `frontend/dist/` to `internal/handler/dist/` before building.

## Docker-Specific Go Quirks

**`os.Hostname()` returns the container ID**, not the host machine name. Hardcode the domain or pass it as an env var instead of relying on `os.Hostname()`.

**`/proc/uptime` works inside containers** and reflects the host's uptime (if the container uses the host's kernel, which Docker always does). Read it for real uptime: parse the first field (seconds), format as `"Nd Nh Nm"`.

## Vite Dev Proxy

```js
// vite.config.js
export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    proxy: { '/api': 'http://localhost:8080' }
  }
})
```

This lets the Vue dev server (`npm run dev`) forward API calls to the Go backend during development. In production, Go serves everything — the embed handles it.

## docker-compose Entry

```yaml
oathless-terminal:
  build: /home/ruben/oathless-terminal
  image: oathless-terminal:local
  container_name: oathless-terminal
  restart: unless-stopped
  networks:
    - homeserver
```

Caddy reverse-proxies to `oathless-terminal:8080`. No host port mapping — everything through Caddy.

## Vue Terminal UX Pitfalls

**⚠️ `opacity-0` input overlay breaks on mobile.** The pattern of a visible `<span>` for text + an `absolute inset-0 opacity-0` `<input>` on top for keystrokes fails on mobile browsers — the text underneath isn't rendered or the input steals the rendering layer. **Fix: use a real visible `<input>` styled to look like terminal text:**

```html
<input
  v-model="inputValue"
  class="w-full bg-transparent border-none outline-none font-mono"
  :style="{ color: 'var(--rp-text)', caretColor: 'var(--rp-iris)' }"
/>
```

**⚠️ `v-if` removes DOM → focus loss.** When the input is conditionally rendered with `v-if="!loading"`, the DOM element is destroyed during API calls and recreated afterward — focus is lost. **Fix: after setting `loading = false`, wait for DOM update, then refocus:**

```js
finally {
  loading.value = false
  inputValue.value = ''
  await nextTick()
  focusInput()
}
```

**⚠️ `&nbsp;` beats Tailwind margin for inline spacing.** A regular space character between inline flex children collapses in the browser. `mr-1` (Tailwind margin-right) depends on CSS generation and may not always apply. **Use `&nbsp;` in the template — it never collapses:** `❯&nbsp;`

## Pipe Implementation Pattern

For a command registry with pipe support (`command1 | command2`):

1. **Detect pipes in the handler:** `strings.Contains(raw, "|")`
2. **Split into stages, execute sequentially, feed output forward:**
```go
stages := strings.Split(raw, "|")
var input string
for i, stage := range stages {
    cmd, args := parseCommand(stage)
    var result Response
    if i == 0 {
        result = registry.Execute(cmd, args)
    } else {
        result = registry.ExecuteWithInput(cmd, args, input)
    }
    input = result.Output
}
```
3. **`ExecuteWithInput` routes to commands that accept stdin-like input** (e.g. `grep`):
```go
func (r *Registry) ExecuteWithInput(name string, args []string, input string) Response {
    switch name {
    case "grep":
        return r.grepWithInput(args, input)
    default:
        return r.Execute(name, args)
    }
}
```
4. **Handle commands that live in the browser separately.** Commands like `history` that depend on browser state should be intercepted on the frontend **before** the API call, including their piped variants (`history | grep x`):
```js
if (trimmed.startsWith('history | grep ')) {
  const pattern = trimmed.slice('history | grep '.length).trim().toLowerCase()
  const output = history.value
    .filter(line => line.toLowerCase().includes(pattern))
    .join('\n')
  lines.value.push({ type: 'output', text: output || '(no matches)' })
  return
}
```

## Theme Switching via CSS Custom Properties

Define theme palettes as JS objects, apply by setting `--rp-*` properties on `document.documentElement`:

```js
const themes = {
  'rose-pine': { base: '#191724', text: '#e0def4', iris: '#c4a7e7', /* ... */ },
  green:      { base: '#0d1117', text: '#c9d1d9', iris: '#3fb950', /* ... */ },
}

function applyTheme(name) {
  const t = themes[name] || themes['rose-pine']
  for (const [key, value] of Object.entries(t)) {
    document.documentElement.style.setProperty(`--rp-${key}`, value)
  }
  localStorage.setItem('theme', name)
}
```

Backend returns `type: "theme:<name>"` — frontend detects the prefix and calls `applyTheme()`. Persist to `localStorage` so the theme survives refreshes.

## Go Install (No Sudo, User-Local)

```bash
curl -fsSL "https://go.dev/dl/go1.24.5.linux-amd64.tar.gz" -o /tmp/go.tar.gz
tar -xzf /tmp/go.tar.gz -C /home/ruben/.local/
export PATH="$HOME/.local/go/bin:$PATH"
```

Go lives at `~/.local/go/`. Add to PATH in shell config for persistence.
