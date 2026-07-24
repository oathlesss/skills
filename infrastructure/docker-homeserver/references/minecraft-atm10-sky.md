# ATM10 To The Sky — Working Docker Config

CurseForge modpack: skyblock variant of All the Mods 10, ~500 mods, NeoForge 1.21.1.

## Compose Service (working as of 2026-07-24)

```yaml
minecraft-atm10sky:
  image: itzg/minecraft-server:java21     # MC 1.21.1 = Java 21
  container_name: minecraft-atm10sky
  restart: unless-stopped
  ports:
    - "25565:25565"
  volumes:
    - ./minecraft-atm10sky/data:/data
    - ./secrets/cf_api_key.txt:/run/secrets/cf_api_key:ro   # SOPS-decrypted at deploy time
  environment:
    EULA: "TRUE"
    MOD_PLATFORM: AUTO_CURSEFORGE
    CF_SLUG: all-the-mods-10-sky          # from curseforge.com/minecraft/modpacks/all-the-mods-10-sky
    CF_API_KEY_FILE: /run/secrets/cf_api_key
    MEMORY: 10G
    WHITELIST: "Player1,Player2"
    ENFORCE_WHITELIST: "true"
    ENABLE_RCON: "true"
    RCON_PORT: 25575
    TZ: Europe/Amsterdam
  networks:
    - homeserver
```

## Resource Requirements

- **RAM:** 10G (machine: 30G total, 6 cores). Solo/2-player: 10G is sufficient. 4+ players: consider 12-14G.
- **Disk:** ~3-5GB for mods + world data. The skyblock world itself is small (<50MB), but mod downloads are ~2-3GB.
- **Java:** 21 (itzg/minecraft-server:java21). Do NOT use `:java25` or `:latest` — class file version mismatch.

## Startup Times

| Phase | Duration |
|---|---|
| Image pull | ~2 min |
| Mod download (~500 mods) | ~3-5 min |
| NeoForge installer | ~10s |
| Mod loading (server start) | ~80-90s |
| World generation | ~10-20s |

Total first launch: ~5-8 minutes. Subsequent restarts: ~80-90s (mod loading only, no re-download).

## SOPS Secrets Setup

```
secrets/
  mc.env.sops           # MC_RCON_PASSWORD (dotenv, one line)
  cf_api_key.txt.sops    # CurseForge API key (plain text, one line)
```

deploy.sh decrypts both formats: `.sops` dotenv files (with `--input-type dotenv`) and `.txt.sops` plain text files (straight decrypt). Always clean up plaintext files after deploy.

## Verification

```bash
# Port listening
ss -tlnp | grep 25565

# RCON — should return player count
docker exec minecraft-atm10sky rcon-cli list

# Health check
docker ps --filter name=minecraft-atm10sky --format '{{.Status}}'
# → "Up X minutes (healthy)"
```

## Known Mods (from startup logs)

Create 6.0.9, Mekanism 10.7.18, AE2, ExtendedAE, EnderIO 8.2.3, Pipez 1.2.19, Mystical Agriculture, Apotheosis, KubeJS, Immersive Engineering, PneumaticCraft, Railcraft Reborn, Steve's Carts, Chipped, Xtones Reworked, Functional Storage, Pylons, Bibliocraft, Epitaphs, MCW Furniture, and ~480 more.
