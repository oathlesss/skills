### ⚠️ Docker bind-mount permission trap ("out of memory (14)")

When using a bind-mounted volume for SQLite data, Docker Compose creates the host directory as `root:root`. If the container runs non-root, SQLite fails with `unable to open database file: out of memory (14)` — misleading because the real problem is filesystem permissions, not memory.

**Fix — Dockerfile (pre-switch to non-root user):**
```dockerfile
RUN adduser -D -h /home/app app && mkdir -p /home/app/data && chown app:app /home/app/data
# Remove USER app line — let docker-compose set the UID via "user:" directive
```

**Fix — docker-compose.yml:**
```yaml
services:
  app:
    user: "1000:1000"   # matches host user UID
    volumes:
      - ./data:/home/app/data
```

Pre-create on host: `mkdir -p data && chown 1000:1000 data`

**Why this works:** The Dockerfile creates the directory as root then chowns it to the app user (UID 1000). At runtime, `user: "1000:1000"` runs the container as UID 1000, which matches the bind-mounted directory's owner. SQLite can write.

**Alternative:** Use a named Docker volume. Docker manages permissions automatically. Simpler but harder to back up.
