# Voice chat + "network protocol error" debugging

Two distinct problems that both surface as a client-side crash when joining a modded server.

## Plasmo Voice (proximity voice chat) — setup recipe

- Mod: **Plasmo Voice** (proximity voice chat). NeoForge 1.21.1 → `plasmovoice-neoforge-1.21.1-2.1.17.jar`
  (or newer — check `api.modrinth.com/v2/project/plasmo-voice/version?loaders=["neoforge"]&game_versions=["1.21.1"]`,
  keyless). Single jar works on server + client. CurseForge project id 467028.
- **Network:** needs **UDP**. Default config `port = 0` means "voice rides the SAME port as the
  Minecraft server, but UDP" → MC 25565 TCP + voice 25565 UDP. You must publish `25565/udp` in
  addition to `25565/tcp` in docker-compose (see the recreate-not-restart pitfall in SKILL.md).
  Clients also need the UDP port forwarded on the user's router — a separate rule from TCP.
- **Config:** generated at `config/plasmovoice/server/config.toml`. Key fields:
  `[host] ip = "0.0.0.0"`, `[host] port = 0`, `[voice] client_mod_required = false` (players
  WITHOUT the mod still join, just no voice). `client_mod_min_version` gates older clients.
- **Removal** = delete jar + `config/plasmovoice/` dir + drop the UDP port mapping.
- Verify loaded: log line `EpollDatagramChannel UDP server is started on ...:25565`.
- Alternative mod: Simple Voice Chat (default UDP 24454, separate port). Plasmo Voice chosen here
  because it rides the MC port (no second forwarded port).

## "network protocol error" on client join = mod version mismatch

The client shows "network protocol error" / "Internal Exception"; the SERVER log holds the real
cause. The server seeing a *clean* disconnect while the client crashes is itself the signature.

**Signature 1 — DH-style (network-registry mod version mismatch):**
```
[ERROR] NetworkRegistry: Failed to process a synchronized task of the payload: <modid>:msg
  ... IncompatibleMessageInternalEvent ...
  ... Connection reset by peer
```
Client and server run DIFFERENT versions of a mod that registers a network channel
(Distant Horizons is the usual culprit). Fix: align versions. The `<modid>` in `payload:
<modid>:msg` names the offending mod directly.

**Signature 2 — silent variant (direction flipped):** player joins, plays 30–60s, then "network
protocol error" with a CLEAN server log (no error at all). Still a version mismatch: the server
handshake succeeds but the client can't decode a later packet, so the server logs only a normal
`lost connection: Disconnected`. This happens when you upgrade the SERVER to match a newer client
but the client is actually still on the OLD version — same crash, opposite direction. Always
confirm BOTH sides' exact jar filenames, never assume from one side.

## Debugging path

1. `docker exec <c> sh -c 'grep -iE "Incompatible|protocol|decoder|reset|mismatch|payload" /data/logs/latest.log | tail'`
   — names the offending mod's channel (`<modid>:msg`).
2. Diff client vs server jar filenames for that mod.
3. Align to the version the user wants — don't assume newer-is-better (DH 3.3.x bumps its config
   version and resets configs; check the changelog for "config version" notes).
4. Rebuild the shareable pack AND warn other players to match, or they hit the same crash.

## Distant Horizons version notes (as of Sep 2026)

- 3.2.0-b-1.21.1 was the old beta; the 3.3.x line (3.3.0 → 3.3.3) is stable `release`.
- DH 3.3.3 changelog: "config version 4 -> 5, this will clear your config" + a Chunky-coordination fix
  ("only disable DH world gen when Chunky world gen is also active").
- DH is server-optional/client-optional. No DH on one side = no handshake = no crash. The crash only
  occurs when BOTH sides have DH at DIFFERENT versions.
- A server-side `Can't keep up! ... ticks behind` stall at join is a SEPARATE issue (CPU-bound box),
  not the network-protocol-error cause — don't conflate them.
