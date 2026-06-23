# oathless.dev Terminal Website

Specific configuration and deployment details for the terminal website at https://oathless.dev.

## Location
- Repo: /home/ruben/oathless-terminal (github.com/oathlesss/oathless-terminal)
- Docker image: oathless-terminal:local (~20.8 MB)

## Commands (18 total)
help, about, whoami, projects, contact, clear, date, echo, neofetch, banner, social, theme, ls, cat, history, uptime, hostname, grep

Piping: `command | grep pattern` — backend pipe for all commands, local intercept for `history | grep`.

## Theme Palettes
Rose Pine (default), Green, Amber, Matrix — defined in frontend Terminal.vue as `themes` object. Applied via CSS custom properties on `document.documentElement`.

## Rose Pine Colors
base: #191724, surface: #1f1d2e, overlay: #26233a
muted: #6e6a86, subtle: #908caa, text: #e0def4
love: #eb6f92, gold: #f6c177, rose: #ebbcba
pine: #31748f, foam: #9ccfd8, iris: #c4a7e7

## Key UX Decisions
- Banner (ASCII art) shows on first visit, disappears after first command
- `❯` prompt with &nbsp; gap before typed text
- Auto-focus after every command (nextTick + focusInput in finally block)
- History kept in browser (local), grep on history handled locally
- Theme persists in localStorage
- Clear and history handled locally (no API call)
- uptime reads /proc/uptime for real container uptime
- hostname hardcoded to "oathless.dev" (container hostname is useless)

## Deploy Command
```bash
cd /home/ruben/homeserver
docker compose build oathless-terminal && docker compose up -d oathless-terminal
# Caddy restart not needed unless Caddyfile changed
```
