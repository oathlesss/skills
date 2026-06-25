# Tailscale Reachability on the Homelab

## How It Works

Tailscale runs in `network_mode: host`, sharing the host's network stack. This means the Tailscale IP (`100.x.x.x`) is bound to the host's interfaces. Any port listening on `0.0.0.0` (all interfaces) or `[::]` (IPv6 all) is reachable from other Tailscale-connected devices via `http://<tailscale-ip>:<port>`.

## What's Reachable

Checked with `ss -tlnp` on the host:

| Port | Service | Via Tailscale IP? |
|---|---|---|
| 22 | SSH | Yes |
| 80 | Caddy HTTP → all proxied services | Yes |
| 443 | Caddy HTTPS → all proxied services | Yes |
| 25565 | Minecraft (or mc-router) | Yes |
| 2222 | Forgejo Git SSH | Yes |
| 9090 | Webhook receiver (if running) | Yes |

Any service mapped with `ports: "XXXX:XXXX"` in docker-compose (e.g. apichangelog's `8080:8080`) is also reachable.

## What's NOT Reachable

Services on the internal `homeserver` Docker network without host port mappings:

| Service | Why not reachable |
|---|---|
| oathless-terminal | Only on `homeserver` network, no host port |
| homepage | Only on `homeserver` network, no host port |
| zennotes | Only on `homeserver` network, no host port |
| uptime-kuma | Only on `homeserver` network, no host port |
| dockge | Only on `homeserver` network, no host port |
| forgejo | Only on `homeserver` network, no host port |

These are accessible **through Caddy** on ports 80/443, which IS reachable via Tailscale IP.

## How to Check

```bash
# List all listening ports on 0.0.0.0 or [::]
ss -tlnp | grep -E '0\.0\.0\.0|\[::\]'

# Filter to just the ports
ss -tlnp | awk '/0\.0\.0\.0|\[::\]/ && /LISTEN/ {print $4}'
```

## No Firewall

This host has no `ufw` or `iptables` rules blocking ports. Everything bound to `0.0.0.0` is exposed to the Tailscale network.

## When to Use Tailscale IP + Port

**Good for:**
- Quick testing a new service before wiring up Caddy/DNS
- SSH access (`ssh user@100.x.x.x`)
- Minecraft direct connections
- Services that don't need a domain or HTTPS

**Not a replacement for Caddy:**
- No automatic HTTPS
- No domain-based routing
- No auth (basic_auth, etc.)
- Port numbers required in URLs
