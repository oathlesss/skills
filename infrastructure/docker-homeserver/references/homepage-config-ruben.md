# Homepage Config — Working Configs (Ruben's Homelab)

Last updated: 2025-06-25

## settings.yaml

```yaml
---
title: Homelab
description: OptiPlex 3070 Micro
theme: dark
color: slate
headerStyle: boxedWidgets
cardBlur: sm
hideVersion: true
layout:
  Infrastructure:
    style: row
    columns: 4
  Services:
    style: row
    columns: 4
```

Settings notes:
- `cardBlur: sm` — frosted glass effect on cards (options: sm/md/lg/xl)
- `hideVersion: true` — removes version footer for cleaner look
- `color: slate` — closest built-in to Rose Pine cool tones

## services.yaml (with Docker status indicators)

All services use `server: my-docker` + `container: <name>` for live container status dots (green=running, red=stopped). `my-docker` references the Docker socket in `docker.yaml`.

```yaml
---
- Infrastructure:
    - Caddy:
        href: https://caddyserver.com/docs/
        description: Reverse proxy & TLS — routing all *.oathless.dev traffic
        icon: caddy.png
        server: my-docker
        container: caddy
    - Tailscale:
        href: https://login.tailscale.com/admin/machines
        description: Mesh VPN — remote access without port forwarding
        icon: tailscale.png
        server: my-docker
        container: tailscale
    - Vanilla MC:
        href: https://oathless.dev
        description: Minecraft 1.21.5 • mc.oathless.dev:25565
        icon: minecraft.png
        server: my-docker
        container: minecraft-vanilla

- Services:
    - Notes:
        href: https://notes.oathless.dev
        description: Markdown notes — plain .md files, web UI
        icon: mdi-notebook-edit-outline
        server: my-docker
        container: zennotes
    - Git:
        href: https://git.oathless.dev
        description: Self-hosted Git — Forgejo
        icon: forgejo.png
        server: my-docker
        container: forgejo
    - Status:
        href: https://status.oathless.dev
        description: Uptime Kuma — service monitoring & alerts
        icon: uptime-kuma.png
        server: my-docker
        container: uptime-kuma
    - Docker:
        href: https://docker.oathless.dev
        description: Dockge — manage compose stacks
        icon: dockge.png
        server: my-docker
        container: dockge
    - Logs:
        href: https://logs.oathless.dev
        description: Dozzle — real-time container log viewer
        icon: dozzle.png
        server: my-docker
        container: dozzle
    - Terminal:
        href: https://oathless.dev
        description: Go+Vue terminal-style personal site
        icon: mdi-console
        server: my-docker
        container: oathless-terminal
```

Status indicator notes:
- `server` references the key in `docker.yaml` (currently `my-docker`)
- `container` must match the `container_name` in `docker-compose.yml` exactly
- Container status shows as a colored dot on the service tile
- All 9 services have status dots — every web-facing container is tracked

## widgets.yaml

```yaml
---
- resources:
    cpu: true
    memory: true
    expanded: true
    disk: /

- search:
    provider: duckduckgo
    target: _blank

- openmeteo:
    latitude: 52.37
    longitude: 4.90
    units: metric
    cache: 5
    label: Netherlands
```

Weather notes:
- Open-Meteo is free, no API key needed
- Coordinates are Amsterdam — adjust for precise location
- `cache: 5` — updates every 5 minutes
- `label` shows above the weather display

## custom.css

See `references/homepage-custom-css.md` for the full class reference and working Rose Pine theme. The quick-start CSS:

```css
/* ── Rose Pine theme for Homepage ── */
body {
  background: linear-gradient(135deg, #191724 0%, #1f1d2e 40%, #191724 100%) !important;
  background-attachment: fixed !important;
}
.dark .service-card, .dark .bookmark a, .dark .widget-container {
  background-color: #1f1d2e !important;
  border: 1px solid #26233a !important;
  color: #e0def4 !important;
}
.dark .service-card:hover, .dark .bookmark a:hover, .dark .widget-container:hover {
  background-color: #26233a !important;
  border-color: #6e6a86 !important;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
}
.dark .bookmark-group-name, .dark h2 { color: #c4a7e7 !important; }
.dark a { color: #9ccfd8 !important; }
.dark a:hover { color: #ebbcba !important; }
.dark input { background-color: #26233a !important; color: #e0def4 !important; border-color: #6e6a86 !important; }
.dark input::placeholder { color: #6e6a86 !important; }
.dark .text-green-500, .dark .text-green-400 { color: #31748f !important; }
.dark .text-red-500, .dark .text-red-400 { color: #eb6f92 !important; }
```

Custom CSS/JS notes:
- `custom.css` and `custom.js` live in the config directory alongside YAML files
- Homepage picks them up on restart: `docker compose restart homepage`
- **Target actual component classes**, not guessed Tailwind utilities — Homepage uses `.service-card`, `.bookmark a`, `.widget-container`, NOT `[class*="bg-gray-800"]`
- `dark:bg-white/5` is a 5% white overlay (not a solid color) — override with `background-color: ... !important`
- `!important` is usually needed to override Homepage's built-in styles
- Background gradients need `background-attachment: fixed` to stay put on scroll

## docker.yaml

```yaml
---
my-docker:
  socket: /var/run/docker.sock
```

## bookmarks.yaml

```yaml
---
- Dev:
    - GitHub:
        - abbr: GH
          href: https://github.com/oathlesss
    - Godot Docs:
        - abbr: GD
          href: https://docs.godotengine.org/en/stable/
    - Project Arachne:
        - abbr: AR
          href: https://github.com/oathlesss/project-arachne

- Homelab:
    - Caddy Docs:
        - abbr: CA
          href: https://caddyserver.com/docs/
    - Homepage Docs:
        - abbr: HP
          href: https://gethomepage.dev/
    - Docker Hub:
        - abbr: DH
          href: https://hub.docker.com/

- Social:
    - Discord:
        - abbr: DC
          href: https://discord.com/app
    - YouTube:
        - abbr: YT
          href: https://youtube.com/
```

## Verified Icons

These dashboard-icons exist at CDN and work:
- `caddy.png`, `forgejo.png`, `dockge.png`, `dozzle.png`
- `uptime-kuma.png`, `minecraft.png`, `tailscale.png`
- `netdata.png` — likely exists (common service); if broken, fall back to `mdi-monitor-dashboard`

These do NOT exist and need `mdi-*` or `abbr:` fallback:
- `notes.png`, generic service names without a known project
- `terminal.png` → use `mdi-console`

## Pitfalls Resolved

1. `HOMEPAGE_ALLOWED_HOSTS=home.oathless.dev` env var required (host validation)
2. `notes.png` icon doesn't exist → `mdi-notebook-edit-outline`
3. Docker widget doesn't work standalone → use `docker.yaml` provider
4. Widgets must be flat list, not grouped sections
5. Config directory root-owned → `docker run --rm -v ... alpine chown` before writing
6. `cardBlur` setting — frosted glass effect, options: sm/md/lg/xl
7. Status indicators — use `server: my-docker` + `container: <name>` (matches docker-compose container_name)
8. Open-Meteo weather — free, no API key, just lat/long/units
9. Config changes need `docker compose restart homepage` (Homepage reads config at startup)
