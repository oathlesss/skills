# Adding Plasmo Voice (proximity voice chat) to the itzg server

Voice chat is a whole different beast from a normal content mod: it needs a **UDP** port
open, and the MC server's published port is TCP-only by default. This bites every time.

## The mod

- **Plasmo Voice** (project id `plasmo-voice`) — proximity voice chat with audio positioning.
  Single jar works for both server AND client (NeoForge/Fabric/Fabric). Latest NeoForge 1.21.1
  build was **2.1.17** (Sept 2026); confirm current at the Modrinth/CF API before pinning.
- Config generated at `config/plasmovoice/server/config.toml` after first boot. Key fields:
  - `[host] port = 0` → **voice rides the SAME port as the MC server, but on UDP**. If MC is on
    25565 TCP, the voice server listens on 25565 UDP. No dedicated port needed.
  - `[voice] client_mod_required = false` → players WITHOUT the mod still join (just no voice).
    Keep this false so the pack doesn't gate joining.

## UDP port is the gotcha

`docker-compose.yml` mapping `"25565:25565"` publishes **TCP only**. Voice needs UDP, so add:

```yaml
ports:
  - "25565:25565"
  - "25565:25565/udp"   # Plasmo Voice (voice chat, UDP)
```

Then **recreate** the container — `docker start` does NOT re-apply port mappings (they're baked
at container creation). The terminal tool refuses `docker compose up -d` as a long-lived process,
so use the recreate sequence:

```bash
docker rm -f minecraft-atm10aero        # data volume persists
docker compose create minecraft-atm10aero
docker start minecraft-atm10aero
```

Verify with `docker inspect <name> --format '{{json .HostConfig.PortBindings}}'` — both
`25565/tcp` and `25565/udp` must be present.

## Verify it loaded

- Boot-complete: poll `docker exec minecraft-atm10aero rcon-cli list` (NOT log grep).
- Voice server up: log line `EpollDatagramChannel UDP server is started on ...:25565`.
- Whitelist intact: `rcon-cli whitelist list`.

## Router / firewall

The homelab forwards TCP 25565 already (players join). **UDP 25565 is a SEPARATE router rule** —
TCP forwarding does NOT carry UDP. Voice silently fails without it. Flag this to the user; it's
outside the agent's reach. Note for monitoring: TCP-ping health checks won't catch a broken UDP
voice port.

## Manual-jar persistence

Drop `plasmovoice-*.jar` straight into `data/mods/` — manual drops survive the AUTO_CURSEFORGE
re-sync (same as AppliedFlux/AdvancedAE). No CF project/file lookup needed.
