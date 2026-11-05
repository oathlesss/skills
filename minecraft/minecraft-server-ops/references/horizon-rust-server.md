# Horizon — native Rust Minecraft server (vanilla, no Java, no Docker)

Horizon (`horizon-rust/horizon`) is a from-scratch Rust reimplementation of Minecraft Java
Edition (targets **26.3**, protocol **777**). It ships three binaries: `horizon-client`
(the game, wgpu/Vulkan), `horizon-engine` (the game headless — what the server runs), and
`horizon-server` (a supervisor CLI that runs the engine + manages backups/updates/web panel).

**Key facts / limits:** vanilla-only — *Java mod jars do not run*, so no Forge/NeoForge/Fabric
packs and it **cannot load a modded world** (no registry entries for modded blocks/entities).
No official Docker image. Single author, very young project (Oct 2026). The dedicated server
loads the full client render assets at startup (hence the prepare step needs the whole client),
so idle RAM (~250 MB) is higher than vanilla-Java's but still tiny vs a modded pack.

## 1. Install (Linux x86-64)

```sh
curl -fsSL https://raw.githubusercontent.com/horizon-rust/horizon/main/packaging/server/install.sh | sh
```

Installs to `~/.local/share/horizon/releases/<tag>` (with `current` symlink) and puts
`horizon-server` + `horizon-prepare` in `~/.local/bin`. Downloads a prebuilt Nightly, verifies
signed SHA256 + Ed25519. No sudo, no Mojang downloads. `--version`, `--dir`, `--bin` options.

## 2. Prepare game files — THE GOTCHA

`horizon-prepare --prepare --server-jar PATH` requires the **full client install**
(client.jar + libraries + ~485 MB assets), and **Horizon refuses to download the game**
("Horizon does not download the game"). It wants one of: `~/.minecraft` (official launcher),
ATLauncher, or the CurseForge app — or the files named explicitly via
`--version-json --client-jar --libraries-dir --assets-dir`.

Two paths:

- **A (clean):** prepare on a machine that has the launcher + played 26.3 once, then
  `scp` the prepared `26.3` folder and run `horizon-server import-resources DIR`.
- **B (headless, do it here):** replicate the launcher's download from Mojang's public CDN
  and lay it out in `~/.minecraft` exactly like the official launcher would. Everything below.

### Replicate the launcher download (Mojang CDN, no auth needed)

All URLs are public — the launcher fetches the same files; auth is only needed to *play*.

1. Version manifest → pick latest release id:
   `https://piston-meta.mojang.com/mc/game/version_manifest_v2.json` (`.latest.release`)
2. Version JSON: `https://piston-meta.mojang.com/v1/packages/<sha1>/<id>.json`
3. Files, laid out under `~/.minecraft`:
   - **server.jar** — `.downloads.server.url` (public; sha1 in `.downloads.server.sha1`)
   - **client.jar** → `versions/<id>/<id>.jar` — `.downloads.client.url`
   - **version json** → `versions/<id>/<id>.json`
   - **asset index** → `assets/indexes/<assetIndex.id>.json` — `.assetIndex.url`
   - **asset objects** → `assets/objects/<hash[:2]>/<hash>` for each entry in the index's
     `objects`, fetched from `https://resources.download.minecraft.net/<hash[:2]>/<hash>`
   - **libraries** → `libraries/<maven path>` from `.libraries[].downloads.artifact`
4. **Library rule resolution** (MC 26.x version JSON has no `natives`/`classifiers` fields;
   natives are separate entries with the classifier baked into the name + OS rules):
   - no `rules` → include
   - has `rules` → default exclude; iterate; a rule matches when
     `os.name` is absent or `"linux"` AND `os.arch` is absent or `"x86_64"`; a matching
     rule sets include = (`action == "allow"`). This skips osx-only (e.g.
     `ca.weblite:java-objc-bridge`), windows natives, and downloads linux natives like
     `org.lwjgl:lwjgl:3.4.3:natives-linux` (both netty epoll x86_64 and aarch_64 match
     "linux" — downloading both is harmless).

The version JSON's `research-lock.json` (in the release dir) pins exact sha1s
(`client_sha1`, `server_sha1`, `asset_index_sha1`, `java_major`) — verify against those.

### Run prepare

```sh
export JAVA_HOME=~/.local/java/jdk-25.0.4.1+1   # 26.3 pins Java 25 (java_major); see research-lock.json
horizon-prepare --prepare --server-jar /path/to/server.jar
```

Emits `Done in ~22s`; resources land in `<release>/.local/horizon-client/26.3`
(symlinked to `~/.local/share/horizon/game-files/horizon-client` by the installer).

## 3. Init + run

```sh
horizon-server init --eula --world world --port 25566 --whitelist --player 0athless --op 0athless --yes
horizon-server start          # detached supervisor (survives the shell, not a reboot)
horizon-server status --json  # phase/tps/mspt/rss/players
```

`init` flags: `--eula --world NAME --seed N --port N --whitelist/--no-whitelist
--player NAME... --op NAME --offline --yes`. Defaults: online-mode=true (Microsoft account
auth), whitelist=true, view/simulation distance 10, difficulty easy, auto-backup every 6h.

## 4. Manage (all via the `horizon-server` CLI)

`run` (foreground console), `start`/`stop`/`restart`, `status [--json]`, `cmd <cmd>` (run one
console command), `console` (live), `logs [-n N]`, `backup`/`restore`, `op`/`deop`,
`whitelist on|off|add|remove`, `kick`/`ban`/`pardon`, `service install [--system]` (systemd/
launchd/logon — use this for boot persistence; `start` alone dies on reboot), `panel` (web
panel login link, default `127.0.0.1:8130`), `mcp` (agent control), `update`/`rollback`.

## 5. Verify joinability (server-list status ping)

Handshake (packet 0x00: varint protocol + host string + port u16 + next-state 1), then status
request (packet 0x00). Response JSON carries `version.protocol` (777 for 26.3), MOTD, players.
A working reference implementation lives at `~/horizon-setup/ping.py` on the homelab.
Gotcha: don't double the packet-id varint (packet id goes in the frame only, not the body).
Also: the status-response JSON string is length-prefixed by a **varint**, not a single byte —
MOTD/version JSON is usually >127 bytes so the length varint is 2 bytes; reading `payload[0]`
as the length yields a JSONDecodeError. Reuse `~/horizon-setup/ping.py` (parses it correctly).

## 6. Change port / replace an existing server

- The port is `server.toml` `[server] port = N`. **Edit `server.toml`, never `server.properties`**
  — Horizon regenerates `server.properties` from `server.toml` before every start, so a
  hand-edit there is silently overwritten. Then `horizon-server restart`.
- To take over a port vacated by another server, free it FIRST (`docker stop <old> && docker
  rm <old>`), then edit `server.toml`, then restart — otherwise the engine fails to bind.
- Binds IPv4 only (`0.0.0.0:<port>`, no `[::]`) — fine for a router port-forward to the
  internal IPv4.
- **Migrate the whitelist** so players aren't locked out: loop
  `horizon-server whitelist add <name>` per name (online-mode resolves UUIDs via Mojang),
  then `horizon-server whitelist list` to confirm. `whitelist.json` stores uuid+name;
  `ops.json` the op level (default op level 4).
- Full container-removal + compose-edit + data-preservation flow:
  `references/server-replacement-decommission.md`.
- **Mods, native server export, and far terrain (LOD/pregen):**
  `references/horizon-mods-far-terrain.md`.
