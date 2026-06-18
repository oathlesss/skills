# ZenNotes — Self-Hosted Web Notes

ZenNotes is a keyboard-first Markdown notes web app. Notes are plain `.md` files in a host-mounted directory — no database, no sync plugins, no encryption layer between Hermes and the files.

## Docker Compose (working config)

```yaml
zennotes:
  image: adibhanna/zennotes:latest
  container_name: zennotes
  restart: unless-stopped
  user: "1000:1000"          # match host user for vault write access
  read_only: true            # container FS is read-only
  tmpfs:
    - /tmp                   # required by the server
  cap_drop:
    - ALL                    # drop all capabilities
  security_opt:
    - no-new-privileges:true
  volumes:
    - /home/ruben/obsidian-vault:/workspace
    - ./zennotes-data:/data
  environment:
    - ZENNOTES_AUTH_TOKEN=${ZENN...N}
    - ZENNOTES_BEHIND_TLS=1  # required behind Caddy/Nginx
  networks:
    - homeserver
```

## Caddy Reverse Proxy

```
notes.oathless.dev {
    reverse_proxy zennotes:7878
}
```

## Key Settings

| Setting | Why |
|---------|-----|
| `user: "1000:1000"` | Container needs write access to host-mounted vault directory |
| `ZENNOTES_AUTH_TOKEN` | Required — server refuses to start without it on non-loopback bind |
| `ZENNOTES_BEHIND_TLS=1` | Marks cookies Secure, sends HSTS headers |
| `read_only: true` | Defense in depth — container can only write to mounted volumes |

## Pitfalls

**Permission denied creating vault directories:** Container runs as root by default, but host vault is owned by uid 1000. Fix: add `user: "1000:1000"` to the service.

**ZENNOTES_AUTH_TOKEN_FILE not found:** The `_FILE` variant may not resolve correctly with volume mounts due to permission mismatch. Prefer `ZENNOTES_AUTH_TOKEN` directly (stored in `.env`, referenced via `${ZENNOTES_AUTH_TOKEN}` in compose).

**Token in plaintext in docker-compose.yml:** Reference it from `.env` instead — `ZENNOTES_AUTH_TOKEN=${ZENNOTES_AUTH_TOKEN}` in compose, actual value in `.env`.

## Auth Flow

First visit: browser prompts for the token. Paste it once. ZenNotes sets a session cookie. Subsequent visits auto-authenticate. To rotate: generate new token (`openssl rand -hex 32`), update `.env`, restart container.

## Hermes Integration

Hermes reads/writes files directly in the vault directory. No API, no auth, no plugins — just `.md` files on disk. Any note created via the web UI is immediately visible to Hermes, and vice versa.
