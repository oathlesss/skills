# Building a custom modpack from scratch (curated subset of an existing server)

When the user wants a NEW custom pack (a new itzg server, not more mods on an existing one),
the fastest path is usually to **curate a subset of an already-running pack** on the box
(ATM10aero) rather than fetch everything from CF/Modrinth. The wishlist is often ~90% already
on disk, version-matched to the same MC/loader.

## The lazy truth
- Copy the wishlist mods + their **libraries** from the existing server's `data/mods/`.
- Fetch only the genuinely-new mods (Modrinth is keyless).
- Boot, read the NeoForge ModSorter output, add the named missing deps, reboot. Converges in
  1-3 loops because the ModSorter names every missing dep + incompatibility in ONE pass.

## Workflow
1. `ls` the existing server's `data/mods/*.jar` and map wishlist -> exact filenames.
2. Copy curated subset + required libraries into the new server's `data/mods/`.
3. Fetch new mods from Modrinth with the version facet (keyless):
   `https://api.modrinth.com/v2/project/<slug>/version?game_versions=["1.21.1"]&loaders=["neoforge"]`
   — take `data[0]`, then `files[0].primary` (or filter filename for the right loader).
4. New container: `TYPE=NEOFORGE`, `VERSION=1.21.1`, `NEOFORGE_VERSION=<exact>` — read the
   source server's `.neoforge-manifest.json` `forgeVersion` (do NOT trust memory; it drifts).
   Drop mods in `data/mods/`. First boot installs NeoForge + generates world/configs.
5. Boot, then read the boot log for the ModSorter block:
   - `Missing or unsupported mandatory dependencies: Mod ID 'X', Requested by 'Y'` → add X.
   - `Incompatibilities between mods: Mod 'X' is incompatible with 'Y'` → remove one.
6. Fix, reboot, repeat until `Done (Ns)!`. A missing-dep crash reports in ~30-40s with the
   exact mod name every time. Detect success via the `Done (Ns)!` line, NOT `docker logs`
   grep on prior boots (the log is full history — old FATALs linger).

## Dependency matrix (1.21.1 NeoForge — verified via ModSorter)
- Tectonic → Lithostitched
- Biomes O' Plenty → TerraBlender + GlitchCore
- Ad Astra → common-storage-lib (Modrinth slug `common-storage-lib`)
- Iron Jetpacks → Cucumber
- XNet → RFToolsBase (+ McJtyLib)
- AE2, Powah, ExtendedAE → guideme (GuideME)
- AttributeFix → Prickle
- FastFurnace + FastWorkbench → Placebo (Placebo is NOT Apotheosis-only — keep it even if
  you remove Apotheosis)
- Occultism → Modonomicon; Ars Ocultas (Ars↔Occultism bridge) → Occultism (remove both)
- Rechiseled → Fusion (CLIENT-side rendering dep ONLY — the server boots fine without it,
  the client crashes with "rechiseled requires fusion")

## Compatibility traps (1.21.1 NeoForge)
- **Radium (Lithium port) is INCOMPATIBLE with Create** — NeoForge refuses both. Drop Radium;
  Noisium/Saturn/ServerCore/ModernFix carry the perf load.
- **Plasmo Voice + Create Aeronautics (Sable) UDP conflict**: Sable binds UDP on the MC port
  for physics sync; Plasmo Voice default `port=0` (ride MC port) then fails with
  `Failed to start the udp server`. Fix: set Plasmo Voice `[host] port` to a dedicated port
  (e.g. 25567) AND publish that UDP port in compose. Keep the MC-port UDP published for Sable.
  Net ports: `<game>/tcp` + `<game>/udp` (Sable) + `<voice>/udp` (Plasmo Voice).

## Client rendering stack (NeoForge 1.21.1, 2026 — CHANGED)
- **Iris now requires real Sodium, NOT Embeddium.** Embeddium is incompatible with Iris AND
  with Veil. Iris + Iris-Flywheel-Compat + Veil (jarjar'd inside Sable) all want `sodium`.
  A client ships: Sodium + Iris + Iris-Flywheel-Compat + Distant Horizons. NO Embeddium.
- Version floor: Veil needs Sodium >= 0.8.12-alpha.2; the newest stable Sodium release
  (0.8.13) satisfies Iris (0.6+), iris-flywheel-compat (0.6.9+), and Veil.
- Sodium has native NeoForge builds on Modrinth (slug `sodium`, loader `neoforge`).
- Oculus (the old Forge Iris port) has NO 1.21.1 files anywhere — use Iris.
- Distant Horizons Modrinth slug is `distanthorizons` (NO hyphen); CF slug is
  `distant-horizons` (hyphen). 3.3.3 is the stable line.
- Client-side perf mods that coexist with Sodium/Iris: ImmediatelyFast, Entity Culling,
  More Culling, Dynamic FPS, BadOptimizations. Shaders should be OFF by default (Iris present,
  no shaderpack bundled) so weak machines still run.

## Importable pack formats (self-contained — no CF/Modrinth ID resolution)
Both bundle every jar under `overrides/mods/` with an EMPTY `files[]`, so Prism/CF/Modrinth
import instantly with no network lookups (no per-mod projectID/fileID resolution needed for a
custom pack):
- **CurseForge-format `.zip`** (imported by CurseForge app + Prism): `manifest.json` at root
  with `{"minecraft":{"version":"1.21.1","modLoaders":[{"id":"neoforge-21.1.250","primary":true}]},
  "manifestType":"minecraftModpack","manifestVersion":1,"name":"...","version":"...",
  "author":"...","files":[],"overrides":"overrides"}` + `modlist.html` + `overrides/{mods,config,...}`.
- **`.mrpack`** (imported by Modrinth app + Prism): `modrinth.index.json` with
  `{"formatVersion":1,"game":"minecraft","versionId":"...","name":"...","files":[],
  "dependencies":{"minecraft":"1.21.1","neoforge":"21.1.250"}}` + `overrides/`.
- Build with Python `zipfile` (the `zip` CLI is absent on the box). ~360MB for a ~170-mod pack.
- CF app shows "0 mods to download" on import of an empty-`files[]` pack — expected, the jars
  are in `overrides/mods/` and get extracted regardless.

## Distribution
- Files >25MB can't go through Discord. Serve via Caddy `file_server` (see below) or commit to
  a Forgejo repo (see go-vue-fullstack `references/forgejo-repo-create.md`).
- Caddy static file serving: bind-mount a `./www` dir into caddy (`./www:/srv/www:ro`), then
  `handle_path /files/* { root * /srv/www; file_server }` on the apex domain. This requires a
  container RECREATE (new volume mount), not just a reload. Validate with
  `docker exec caddy caddy validate --config /etc/caddy/Caddyfile` before recreating.
  Directory browsing is off by default; `file_server` is sandboxed to the root.
- ⚠️ Before mounting an existing dir as a public file root, `find` it — a stray pre-existing
  `index.html`/subdir becomes public too. The user explicitly does NOT want anything beyond the
  intended files public.
