# Homepage Config — Working Configs (Ruben's Homelab)

## settings.yaml

```yaml
---
title: Homelab
description: OptiPlex 3070 Micro
theme: dark
color: slate
headerStyle: boxedWidgets
layout:
  Infrastructure:
    style: row
    columns: 4
  Services:
    style: row
    columns: 4
```

## services.yaml

```yaml
---
- Infrastructure:
    - Caddy:
        href: https://caddyserver.com/docs/
        description: Reverse proxy & TLS — routing all *.oathless.dev traffic
        icon: caddy.png
    - Tailscale:
        href: https://login.tailscale.com/admin/machines
        description: Mesh VPN — remote access without port forwarding
        icon: tailscale.png
    - Minecraft:
        href: https://oathless.dev
        description: Forge 1.20.1 • Integrated MC modpack • :25565
        icon: minecraft.png

- Services:
    - Notes:
        href: https://notes.oathless.dev
        description: Markdown notes — plain .md files, web UI
        icon: mdi-notebook-edit-outline
    - Git:
        href: https://git.oathless.dev
        description: Self-hosted Git — Forgejo (soft fork of Gitea)
        icon: forgejo.png
    - Status:
        href: https://status.oathless.dev
        description: Uptime Kuma — service monitoring & alerts
        icon: uptime-kuma.png
    - Docker:
        href: https://docker.oathless.dev
        description: Dockge — manage compose stacks from browser
        icon: dockge.png
    - Logs:
        href: https://logs.oathless.dev
        description: Dozzle — real-time container log viewer
        icon: dozzle.png
```

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
```

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

These do NOT exist and need `mdi-*` or `abbr:` fallback:
- `notes.png`, generic service names without a known project

## Pitfalls Resolved

1. `HOMEPAGE_ALLOWED_HOSTS=home.oathless.dev` env var required (host validation)
2. `notes.png` icon doesn't exist → `mdi-notebook-edit-outline`
3. Docker widget doesn't work standalone → use `docker.yaml` provider
4. Widgets must be flat list, not grouped sections
5. Config directory root-owned → `docker run --rm -v ... alpine chown` before writing
