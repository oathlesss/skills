# Decommission / replace a homelab Minecraft server

Engine-agnostic flow for retiring one MC server and handing its public port to another
(Java/itzg → native Horizon, or any swap). Goal: free the port, hand it over, and leave no
half-removed server that resurrects on the next deploy.

## Steps

1. **Free the port** — `docker stop <name> && docker rm <name>` (or `docker compose down <svc>`).
2. **Strip the service from `~/homeserver/docker-compose.yml`** — a leftover block means the
   next `deploy.sh` / `docker compose up -d` recreates it. Validate: `docker compose config --quiet`.
3. **Preserve world/data by default** — don't delete on the way out; report `du -sh` sizes and
   let the user decide to wipe. Reversible beats irreversible.
4. **Point the replacement at the port** — Horizon: edit `server.toml` (see
   `horizon-rust-server.md` §6); itzg: `SERVER_PORT` env.
5. **Migrate the whitelist** — carry over every name (`horizon-server whitelist add <name>`;
   itzg `WHITELIST=` env) so nobody gets silently locked out. Flag it so the user can trim.
6. **Verify** — protocol ping on the public port (expect the replacement's version/protocol).
7. **Flag follow-ups** — Uptime Kuma monitor (may still read "up" on the same port but now
   serving a different engine/version), restart persistence for native servers
   (`horizon-server service install`), and uncommitted compose edits.

## Pitfalls

- `mc.oathless.dev` is DNS → router port-forward, **not** a Caddy TCP route (the Caddyfile has
  no Minecraft entry). "Put server X on port Y" needs no Caddy change — just bind X to Y.
- The homelab compose repo (github.com/oathlesss/homeserver.git) often carries pre-existing
  uncommitted changes incl. SOPS-encrypted `secrets/*.sops`. Edit compose, but leave the
  commit to the user's normal flow — don't sweep secret changes into a commit.
- `0athless` (zero) and `Oathless` are two different accounts — both are usually whitelisted.
