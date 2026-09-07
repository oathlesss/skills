# Swapping Between CurseForge Modpacks (itzg container)

Replacing one CurseForge modpack with another on the same `itzg/minecraft-server` container
(e.g. ATM10 To The Sky → ATM10 Aeronautics). Tested 2026-09-06.

## Decision gate: is this a fresh world?

1. Confirm the new modpack's `CF_SLUG` from its CurseForge URL: `curseforge.com/minecraft/modpacks/<slug>`.
2. Confirm MC version + loader match the current image tag (Java version). Both ATM10 variants
   are NeoForge 1.21.1 → `itzg/minecraft-server:java21`; no image change needed.
3. Check world compatibility. Skyblock variants (To The Sky) vs normal overworld packs
   (Aeronautics, Create + airships) are NOT world-compatible → fresh world required.
   If the packs share worldgen/mods you *might* reuse the world, but the safe default for a
   "replace" is a fresh data dir.

## Procedure (fresh data dir)

1. Edit `docker-compose.yml`: rename the service key AND `container_name` AND the data volume
   path, and swap `CF_SLUG`. Keep image/MEMORY/whitelist/RCON/port identical when MC version
   is unchanged.
2. Remove the OLD container **by name, not via compose**. After renaming the service in compose,
   `docker compose rm -f <old-service>` fails with "no such service" (compose no longer knows
   the old name). Use:
   ```bash
   docker rm -f <old-container-name>
   ```
3. Wipe old data. A root-owned PARENT dir blocks `rm -rf` ("Permission denied") even when the
   data subdir is user-owned. Use the Alpine container for the whole tree:
   ```bash
   docker run --rm -v /home/ruben/homeserver:/host alpine:latest rm -rf /host/<old-data-dir>
   ```
4. Clear the stray `secrets/cf_api_key.txt` DIRECTORY before re-decrypting. When the plaintext
   key file was cleaned up and the container later restarted, Docker creates a root-owned
   directory at the bind-mount path. `sops --decrypt ... > secrets/cf_api_key.txt` then fails
   (can't write to a directory). Remove it first:
   ```bash
   docker run --rm -v /home/ruben/homeserver:/host alpine:latest rm -rf /host/secrets/cf_api_key.txt
   ```
5. Decrypt secrets manually (or via `./deploy.sh`):
   ```bash
   ~/.local/bin/sops --decrypt secrets/cf_api_key.txt.sops > secrets/cf_api_key.txt && chmod 600 secrets/cf_api_key.txt
   ~/.local/bin/sops --input-type dotenv --output-type dotenv --decrypt secrets/mc.env.sops > secrets/mc.env && chmod 600 secrets/mc.env
   ```
6. Bring up the service. NOTE: the terminal tool flags `docker compose up -d` as a long-lived
   process — run it with `background=true` (it returns immediately; the container keeps
   downloading mods in the background).
7. Verify boot (~5-8 min first launch):
   ```bash
   docker ps --filter name=<svc> --format '{{.Status}}'                 # → "Up X minutes (healthy)"
   docker logs <svc> 2>&1 | grep -iE 'Done \(|RCON running'
   docker exec <svc> rcon-cli list                                     # player count
   docker exec <svc> rcon-cli whitelist list                           # whitelist carried over
   ss -tlnp | grep 25565                                               # port listening
   ```
8. Update stale Uptime Kuma monitors (old container name → new). Hostname changes require a
   `docker compose restart uptime-kuma`.
9. Clean up plaintext secrets (`rm -f secrets/cf_api_key.txt secrets/mc.env`) — matching
   deploy.sh's decrypt → up -d → cleanup flow.

## ATM10 Aeronautics facts

- `CF_SLUG`: `all-the-mods-10-aeronautics`
- CurseForge project ID: `1644918`; latest file (Sep 2026): Aeronautics-0.5.1
- NeoForge 1.21.1, ~437 mods, by ATMTeam ("ATM10.5", Create + Aeronautics airships, normal overworld)
- Same Java 21 image as ATM10 To The Sky — pure slug + dir swap.
