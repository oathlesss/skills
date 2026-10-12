# Building a from-scratch custom modpack (curated subset) on itzg

When the user wants a NEW custom pack (not extending an existing one), the laziest correct
path is to **curate a subset of an existing pack's mods already on disk** (e.g. ATM10aero)
rather than fetch 150 jars from CurseForge. Confirmed 2026-10: a wishlist of Create+
Aeronautics, Mekanism, EnderIO, AE2+addons, Ars Nouveau, Bees/Trees, Dyson Cube, Ad Astra,
BOP+Tectonic, Plasmo Voice was ~95% already present in ATM10aero's mods dir.

## ⚠️ Curation rule (user correction — first-class)

Only include the user's **explicit wishlist + essential deps/QoL/perf**. Do NOT pad with
"suggested" mods. The user pushed back: *"You added a lot of mods without my input. I don't
want Apotheosis, Apothic X, Occultism."* A bare "other mods you might suggest" is NOT a
license to add 40 extras. Present extras as a grouped list for approval and let them veto;
don't silently bundle. Kitchen-sink additions (Apotheosis, Occultism, extra decor/exploration)
were removed on request.

## Workflow

1. **List the source pack's mods** with Python (NOT `ls *.jar` — filenames contain
   apostrophes that break shell globbing):
   `python3 -c "import os; print('\n'.join(sorted(os.listdir('.../data/mods'))))"`
2. **Write a manifest.txt** of curated targets (one filename per line, `#` comments), copy
   with a Python script. Watch case — `OctoLib`, `Clumps`, `Glodium`, `SmartBrainLib`,
   `Patchouli` are capitalized; a lowercase transcription silently "misses" them.
3. **Fetch genuinely-new mods from Modrinth** (keyless API):
   `GET /v2/project/<slug>/version?game_versions=["1.21.1"]&loaders=["neoforge"]` → take
   `data[0]`, pick the `primary` file.
4. **Compose service**: `TYPE=NEOFORGE`, `VERSION=1.21.1`, `NEOFORGE_VERSION=<exact>`. Read
   the exact version from the source pack's `.neoforge-manifest.json` `forgeVersion` — it was
   **21.1.250**, not the 21.1.248 some notes carried.
5. **Boot → read the ModSorter block → fix → reboot.** Converges in 1-3 iterations.

## Boot-iterate debugging

- NeoForge's ModSorter prints **ALL missing mandatory deps in one block**
  (`Missing or unsupported mandatory dependencies:`), so fix them in one pass.
- Runtime deps that ModSorter does NOT flag surface later as `NoClassDefFoundError` in
  `crash-reports/crash-*.fml.txt` (e.g. Tectonic→Lithostitched). Read the crash report, not
  just the log tail.
- Detect boot-complete via the `Done (Ns)!` line. Do NOT grep for "error" — a dedicated
  server floods the log with benign client-class mixin WARNs ("AbstractContainerScreen for
  invalid dist DEDICATED_SERVER") that false-positive.

## Dependency gotchas (verified 1.21.1 NeoForge)

- **Radium (Lithium port) is incompatible with Create** — ModSorter: "create is incompatible
  with radium". Drop Radium; Noisium + Saturn + ServerCore cover the perf need.
- **Biomes O' Plenty** → TerraBlender + GlitchCore.
- **Tectonic** → Lithostitched (runtime `NoClassDefFoundError`, not in ModSorter).
- **Ad Astra** → `common-storage-lib` (Modrinth slug `common-storage-lib`; NOT botarium on
  1.21.1). The single jar bundles sub-modules (core/data/lookup/resources) as nested jars.
- **Iron Jetpacks** → Cucumber (shared with MA, but required even when MA is absent).
- **XNet** → RFToolsBase + McJtyLib. **ExtendedAE / Powah / AE2** → guideme. **attributefix**
  → prickle. **Occultism** → Modonomicon + Ars Ocultas (remove both together).
- **Placebo is required by BOTH Apotheosis AND FastFurnace/FastWorkbench** — removing
  Apotheosis does NOT orphan Placebo; deleting it crashes fastfurnace/fastbench.

## Voice chat: Plasmo Voice vs Sable UDP conflict

Create: Aeronautics' physics engine **Sable** also grabs UDP on the MC port
(`Sable: Adding UDP server channel`). With Plasmo Voice's default `port=0` ("same port as MC"),
the voice UDP fails: `[PlasmoVoice] Failed to start the udp server`. Fix: set
`[host] port = 25567` in `config/plasmovoice/server/config.toml`, publish `25567:25567/udp`,
and keep `25566:25566/udp` for Sable. Port change ⇒ recreate the container, not restart.

## Shaders on NeoForge 1.21.1 = Iris, not Oculus

Oculus (Asek3's Forge port of Iris) has **no 1.21.1 files** (CF id 581495 empty for 1.21.1;
Modrinth `oculus` has none). Iris added native NeoForge support — use `iris` (Modrinth,
1.8.12 stable, not the beta) + `iris-flw-compat` (Create + shaders).

## Distant Horizons sourcing

Modrinth slug is **`distanthorizons` (NO hyphen)** → 3.3.3 for 1.21.1 NeoForge. (CF slug is
`distant-horizons` WITH hyphen; GitLab project is `distant-horizons-team/distant-horizons`.)

## Self-contained importable packs (Prism + CurseForge)

Both formats can be fully self-contained: `files: []` + every jar under `overrides/mods/` +
config under `overrides/config/`. No per-mod ID lookup, installs instantly from the local file.

- **CF `.zip`**: `manifest.json` (needs `minecraft.modLoaders: [{"id":"neoforge-21.1.250",
  "primary":true}]`, `manifestType:"minecraftModpack"`, `manifestVersion:1`, `overrides:"overrides"`,
  `files:[]`) + optional `modlist.html`. Imports in **CurseForge app + Prism**.
- **`.mrpack`**: `modrinth.index.json` (`formatVersion:1`, `game:"minecraft"`,
  `dependencies:{"minecraft":"1.21.1","neoforge":"21.1.250"}`, `files:[]`) + `overrides/`.
  Imports in **Modrinth app + Prism**.

Verify after build: root has the manifest, `overrides/mods/*.jar` count == expected,
`overrides/config/` entry count sane. Both ≈358 MB for a ~160-mod pack (over Discord's 25 MB
limit — distribute via Caddy file_server or Forgejo).

## Forgejo distribution of large binaries

- **The release API fails on an EMPTY repo** (HTTP 422 `{"message":"repo is empty"}`) — a
  release needs a commit to tag. Push a README first, or skip the API and **commit the
  binaries directly** (git uses the stored credential natively — no `git credential fill`
  extraction, which dodges the secret-redaction mangling of `$(echo -e "protocol=…")`).
- Caddy `file_server` route (`handle_path /files/* { root * /srv/www; file_server }` +
  `./www:/srv/www:ro` volume) is the friend-facing download; a private Forgejo repo is the
  owner's storage. Validate Caddy config before recreating: `docker exec caddy caddy validate`.
