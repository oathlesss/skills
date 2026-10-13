# Connection & Loader-Mismatch Debugging

Diagnostic playbook for "can't join the modded server" reports where the SERVER is
healthy (`Done (Ns)!`, `(healthy)`) and the failure is on the client side. Three
client-side signatures map to three different root causes. Get the player's exact
error text (and, for world crashes, their crash report) before assuming anything.

## Signature 1 — "mod X channel missing on server" + "Incompatible client! Please use NeoForge <ver>"

Example seen: `Channel [glitchcore:sync_config] failed to connect: This channel is
missing on the server side, but required on the client!` followed by
`Client disconnected with reason: Incompatible client! Please use NeoForge 21.1.250`.

Root cause: **the player connected to a DIFFERENT server** (wrong host/port), not the
one you're administering. A channel can only be "missing on the server" if the server
they actually reached lacks that mod. The NeoForge version quoted in the disconnect
reason is *that server's* version — not necessarily yours.

Verify which server they hit:
- `getent hosts <host>` / `dig +short <host> A` — what IP.
- `dig +short SRV _minecraft._tcp.<host>` — a bare hostname with NO SRV record defaults
  to port 25565, so `mc.oathless.dev` (no port) silently lands on whatever owns 25565.
- Cross-check the mod on each server: `python3 -c "import os; print([f for f in os.listdir('<data>/mods') if '<mod>' in f.lower()])"`.

Real case: client connected to `server.oathless.dev` (no port) → 25565 → retired
ATM10aero (NeoForge 21.1.250, no GlitchCore) while the new pack sat on 25566 *with*
GlitchCore. The "missing on server" was the tell: the server they reached genuinely
did not have the mod. Fix = point them at the correct port/host.

## Signature 2 — ConnectTimeoutException on a NEW port (old port still works)

`io.netty.channel.ConnectTimeoutException: connection timed out: <host>/<ip>:<newport>`
while the previous port connects fine.

Root cause: **router port-forwarding gap** — not a server/config problem. Confirm the
server side is clean first, then it must be the router:
1. `docker ps` — port mapping is `0.0.0.0:<port>-><port>/tcp` (not just an EXPOSE).
2. Host `ss -tlnp | grep ':<port>'` — LISTEN on `0.0.0.0` (all interfaces).
3. Server log `Starting Minecraft server on *:<port>`.
4. `ip -4 addr` — if the box has a private IP (192.168.x), it's behind a router and the
   router must forward the new port to it. A public IP directly on the box would need
   no forwarding.

You cannot fix this from the box. Hand the user the exact rule set (external port +
TCP/UDP → internal IP → internal port). For a NeoForge modpack with Create Aeronautics
(Sable) + voice, game = TCP, Sable rides the same port over UDP, voice = its own UDP.

## Signature 3 — crash during singleplayer world creation

Launch log ends: `#@!@# Game crashed! Crash report saved to: .../crash-reports/<ts>-server.txt`
then `Process exited with code 255`. The `-server` suffix = integrated (singleplayer)
server crashed, not a connection issue.

The Prism launch log does NOT contain the exception — it lives in the separate
`crash-reports/<ts>-server.txt` on the client. **Ask for that file** (first ~40 lines
get the Description + stack trace). Also: a log showing "system under high memory
pressure" / "Memory pressure level: Yellow" with a large `-Xmx` is an OOM-during-worldgen
suspect — world creation is the peak-RAM moment for a ~170-mod pack.

## Prism Launcher ignores the NeoForge version pin

When a player imports a CF zip / `.mrpack`, Prism installs the **LATEST** NeoForge for
the MC version, ignoring the manifest's pinned loader version. A pack pinned to
`neoforge-21.1.250` therefore produces a client on `21.1.259` (whatever is newest),
causing a version mismatch even though the manifest is correct.

Fix: **keep the server on the latest NeoForge for the MC version** (bump
`NEOFORGE_VERSION` in compose), so it matches what Prism installs by default. Bumping
within the same 21.1.x line is backwards-compatible for mods. Rebuild + redistribute
the pack with the new pin afterward. Do NOT have the user hand-pin their client — the
moment the server bumps again (or a friend imports), the mismatch returns.
