# Self-Hosted Service Catalog

Condensed comparison of self-hosted services for Docker Compose homelabs. Each entry includes RAM footprint, Docker gotchas, Caddy compatibility, and a verdict. Originally researched June 2026 against an OptiPlex 3070 Micro (i5-9500T, 30GB RAM, 233GB NVMe) but applies to any modest x86 Docker host.

---

## Dashboards: Homepage (winner) vs Heimdall vs Homarr

| | Homepage | Heimdall | Homarr |
|---|---|---|---|
| RAM idle | ~50-100 MB | ~30-50 MB | ~150-200 MB |
| Config | YAML files (git-versionable) | Web UI only (MySQL) | Drag-drop + JSON |
| Docker auto-discovery | ✅ reads labels | ❌ | ❌ |
| Widgets | ✅ 150+ API integrations | ❌ ping-only tiles | ✅ ~30 integrations |
| Gotcha | Needs docker.sock for discovery | Needs separate MySQL container | — |

**Verdict: Homepage.** Developer-friendly YAML config, richest widgets, Docker auto-discovery. Port 3000 internally.

---

## Git Hosting: Forgejo (winner) vs Gitea

Both are single Go binaries, ~80-120 MB idle, SQLite/Postgres/MySQL. Same port (3000), same `app.ini` layout, trivial migration between them.

**Verdict: Forgejo.** Identical resource footprint and features, but community-governed under non-profit Codeberg e.V. Gitea was acquired by a for-profit in 2022. For a privacy-conscious dev, governance matters.

---

## Bookmarks: Linkding (winner) vs Shiori

| | Linkding | Shiori |
|---|---|---|
| RAM | ~60-120 MB | ~25-50 MB |
| Browser extension | ✅ FF/Chrome | ❌ bookmarklet only |
| REST API | ✅ full | ❌ limited |
| Offline archiving | ❌ (optional plugin) | ✅ full HTML |
| Port | 9090 | 8080 |

**Verdict: Linkding.** Browser extension + REST API make it actually useful daily. The 50MB RAM difference is irrelevant on 30GB.

---

## Docker Management: Dockge + Dozzle (winner) vs Portainer CE

| | Dockge | Dozzle | Portainer CE |
|---|---|---|---|
| RAM | ~25-35 MB | ~10-20 MB | ~100-150 MB |
| Purpose | Compose stack management | Log viewer | Everything (heavy) |
| Best feature | Clean YAML editor for stacks | Real-time search, split-screen | Multi-host, Swarm, K8s |

**Verdict: Dockge + Dozzle together (~50 MB).** Each does its job better than Portainer, at 1/3 the RAM. Not mutually exclusive — solve different problems.

Dozzle gotcha: needs `/var/run/docker.sock` for log access. Ports: Dockge 5001, Dozzle 8080.

---

## DNS/Ad Blocking: AdGuard Home (winner) vs Pi-hole

| | AdGuard Home | Pi-hole |
|---|---|---|
| RAM | ~50-100 MB idle, ~150-200 MB with large blocklists | ~50-100 MB idle, ~150-250 MB active |
| Encrypted DNS (DoH/DoT/DoQ) | ✅ built-in | ❌ needs external proxy |
| Docker network mode | Bridge works fine | Often needs `network_mode: host` |
| Caddy | Clean `reverse_proxy adguardhome:80` | Tricky — expects `/admin` path |

**Verdict: AdGuard Home.** Works on Docker bridge (no host networking fight with Caddy), encrypted DNS built-in. Gotcha: Ubuntu's systemd-resolved binds port 53 — must disable it or use macvlan.

Ports needed: 53/tcp, 53/udp, 80/tcp (web UI after setup). Port 3000 for initial setup only.

---

## Media Automation: Sonarr + Radarr + Prowlarr + qBittorrent

| Service | RAM idle | RAM active |
|---|---|---|
| Sonarr | ~150-250 MB | ~400-600 MB |
| Radarr | ~150-250 MB | ~400-600 MB |
| Prowlarr | ~80-150 MB | ~200-300 MB |
| qBittorrent | ~100-200 MB | ~400-800 MB |
| Plex | ~300-500 MB | ~1-2 GB (transcoding) |
| **Total** | **~1-1.5 GB idle** | **~3-6 GB active** |

**Critical Docker gotcha — hardlinks:** All arr services + download client must share the SAME volume mount path. Use a single bind mount (`/mnt/media:/data`) across all containers and map subdirectories consistently. This enables atomic moves instead of copy+delete.

**Storage is the real constraint**, not RAM. Plex metadata alone can be 10-30GB. You need external storage (USB HDD or NAS). The 233GB NVMe fills fast.

**Privacy:** Route qBittorrent through a Gluetun VPN container to isolate torrent traffic.

---

## Password Manager: Vaultwarden

| | Vaultwarden | Official Bitwarden |
|---|---|---|
| RAM (solo user) | **~10-50 MB** | ~2-4 GB |
| Containers | 1 | 11 |
| Database | SQLite (default) | MS SQL Server required |
| Premium features | ✅ all included | 💰 paid |

**Verdict: Deploy it.** At 10-50 MB it's effectively free. Single container, SQLite, all premium features unlocked. Official Bitwarden clients (browser, mobile, desktop) connect seamlessly.

**Critical gotcha — HTTPS required:** Bitwarden clients refuse plain HTTP (WebCrypto API). Caddy's auto-TLS handles this. WebSocket support needed for live sync — Caddy's `reverse_proxy` handles it natively.

**Backups:** copy the `/data` directory (single SQLite DB + attachments). Admin panel at `/admin` — enable with `ADMIN_TOKEN` env var.

---

## File Sync: Syncthing + Tailscale

| | Syncthing |
|---|---|
| RAM idle | ~50-100 MB |
| RAM (large sync) | ~200-500 MB |
| Ports | 22000/tcp (sync), 21027/udp (discovery), 8384/tcp (web UI) |

**Recommended architecture:** Run Tailscale on the bare-metal host (not Docker). Syncthing in Docker on bridge network. Syncthing can reach Tailscale IPs through the Docker bridge → host network routing. Use Tailscale IPs (100.x.x.x) as Syncthing device addresses.

**Docker gotchas:**
- UID/GID must match host user (`PUID=1000`, `PGID=1000`)
- Local discovery (broadcast port 21027/udp) doesn't traverse Docker bridge — LAN devices need Tailscale relay instead
- If both Tailscale AND Syncthing are containerized, they need `network_mode: host` or shared network — gets messy fast

---

## Summary: Priority Stack

| Category | Pick | RAM | Priority |
|---|---|---|---|
| Password mgr | Vaultwarden | ~30 MB | 🔥 |
| Dashboard | Homepage | ~80 MB | 🔥 |
| Docker mgmt | Dockge + Dozzle | ~50 MB | 🔥 |
| Git hosting | Forgejo | ~100 MB | 🔥 |
| DNS/Ad block | AdGuard Home | ~100 MB | 🟡 |
| Bookmarks | Linkding | ~80 MB | 🟡 |
| File sync | Syncthing | ~80 MB | 🟡 |
| Media stack | Sonarr/Radarr/Prowlarr/qBit/Plex | ~1.3 GB idle | 🟠 storage-dependent |

Tier 1 essentials total ~260 MB. Adding Tier 2 brings it to ~520 MB. Full media stack is storage-constrained, not RAM-constrained.
