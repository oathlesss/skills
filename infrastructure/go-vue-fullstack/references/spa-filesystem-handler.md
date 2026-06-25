# Filesystem-Based Multi-Path SPA Handler

When you don't want to embed the frontend via `//go:embed` (e.g., to keep the binary small or avoid compile-time coupling), serve the SPA from the filesystem at runtime.

## The Pattern

```go
package main

import (
    "net/http"
    "os"
)

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
    // SPA fallback: serve index.html for all non-file routes
    http.ServeFile(w, r, root+"/index.html")
}
```

## Usage

```go
// Try dist/ first (Docker), then ../frontend/dist/ (local dev)
spa := spaHandler{roots: []string{"dist", "../frontend/dist"}}
mux.HandleFunc("/", spa.ServeHTTP)
```

## Dockerfile Requirements

Unlike embed (which bundles dist/ into the binary at compile time), filesystem SPA must have dist/ present at runtime:

```dockerfile
# Backend builder stage (already has dist from frontend copy)
FROM golang:1.24-alpine AS backend-builder
WORKDIR /src
COPY --from=frontend-builder /src/frontend/dist/ ./dist/
RUN CGO_ENABLED=0 go build -o /myapp .

# Runtime stage — MUST copy both binary AND dist/
FROM alpine:3.21
COPY --from=backend-builder /myapp /app/myapp
COPY --from=backend-builder /src/dist/ /app/dist/   # ← REQUIRED
```

**Without the second COPY, the app serves a blank white page with no errors** — the SPA handler finds nothing, and `http.FileServer` returns empty responses.

## Local Dev

With the multi-path handler, local dev works naturally:
- `cd backend && go run .` — finds `../frontend/dist/`
- `cd frontend && npm run dev` — Vite hot reload

No need to copy dist/ anywhere for local development.
