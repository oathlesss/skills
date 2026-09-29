# Adding / removing voice chat (Plasmo Voice, Simple Voice Chat)

Proximity voice chat on the ATM10 Aeronautics (1.21.1 NeoForge) homelab server.

## Plasmo Voice (2.x, NeoForge)

Latest jar (check `api.modrinth.com/v2/project/plasmo-voice/version` for current):
`plasmovoice-neoforge-1.21.1-2.1.17.jar`. Modrinth is keyless — prefer it over the CF API.

Grab the primary file's `url` from the version object (`files[]` where `primary: true`),
download it, and drop it in `data/mods/`. Manual jar drops survive the AUTO_CURSEFORGE
re-sync (same rule as AppliedFlux etc.).

## Config (auto-generated on first boot)

`config/plasmovoice/server/config.toml`. Two fields that matter:

- `host.port = 0` — voice rides the SAME port as the MC server (25565), over **UDP**.
- `voice.client_mod_required = false` — players WITHOUT the mod can still join/play;
  they just don't get voice. Leave false for a friends server.

## Networking — the gotcha (this is the #1 failure)

Voice is **UDP**, on the same port *number* as the game's **TCP**. Two independent
requirements, and neither is satisfied by the other:

1. **Compose:** add `25565:25565/udp` alongside the existing `25565:25565`.
   `"25565:25565"` alone forwards **TCP only** — voice silently never reaches the server.
2. **Router:** a SEPARATE **UDP** 25565 port-forward to the homelab. The existing TCP
   25565 forward does NOT carry UDP traffic. "People can join but voice is dead" =
   missing UDP forward, almost always.

## Removal

1. `rm data/mods/plasmovoice-*.jar` and `rm -rf data/config/plasmovoice`.
2. Remove the `25565:25565/udp` compose line.
3. Recreate the container (see SKILL.md recreate pitfall):
   `docker rm -f <container> && docker compose create <container> && docker start <container>`.

After removal a benign WARN appears: `plasmovoice (version X -> MISSING)` under
"version differences that were not resolved". That's NeoForge noticing the mod-list
delta between boots — harmless, clears on the next clean boot. Don't chase it; verify
removal with `find /data -iname '*plasmo*'` (should be empty) and mod-count back to 407.

## Simple Voice Chat (alternative)

Default UDP **24454** (NOT the game port). Config `config/voicechat/voicechat-server.properties`.
Same UDP-forwarding rule applies: separate UDP forward; the TCP forward doesn't count.
