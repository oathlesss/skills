---
name: minecraft-modpack-creation
category: minecraft
description: "Design and assemble a custom Minecraft modpack from scratch (wishlist → verified mod list → distribution format → server+client perf stack) for Ruben's private/friends servers. Trigger on 'create/build a modpack', 'custom modpack', 'pack for friends', 'pick mods for a server', or a mod wishlist needing curation + version verification."
---

# Minecraft Modpack Creation (from-scratch curation)

Design a curated pack from a wishlist. Distinct from `minecraft-server-ops` (administering an
EXISTING itzg server) and `minecraft-modpack-guide` (writing player guides). This skill owns
the *selection → verification → assembly* pipeline.

## When to use
- User gives a mod wishlist and wants a pack built (vs. a guide written).
- "create a modpack for friends" / "leaner custom pack" / "should I include X?".
- Version/loader feasibility of a mod list needs verifying before building.

## Workflow

1. **Pin the target before anything else** — version + loader + platform. Ruben's default is
   **1.21.1 NeoForge** (matches ATM10aero; the whole tech-magic ecosystem has builds here).
   NOTE: Minecraft moved to a new versioning scheme in 2026 — "26.x" releases exist and most
   mods' *latest* builds now target 26.x. As of Oct 2026 the 26.1.2 NeoForge ecosystem is MOSTLY
   migrated — AE2 (26.1.13-beta), Distant Horizons (3.3.3), EnderIO, Refined Storage, Powah,
   Xycraft, Oritech, Just Dire Things, Energized Power, Thaumaturge, Tectonic/Terralith all have
   builds — BUT the "Create + Mekanism + Flux Networks + Ars Nouveau" core Ruben likes is still
   **1.21.1-ONLY**. So the version choice is a fork: 26.1.2 (native EnderIO/AE2/Powah/Xycraft
   stack) vs 1.21.1 (Create/Mekanism/Flux/Ars). Full verified matrix + Modrinth-modpack inspection
   recipe in `references/26.x-neoforge-mod-availability.md`. Confirm with the user; also confirm
   scope (fresh pack vs. extend an existing server) — it changes everything.

2. **Map wishlist → real mod names.** Disambiguate (see pitfalls: Dyson Cube vs Dyson Sphere
   Project; Create Aeronautics needs Sable).

3. **Verify every uncertain mod** via Modrinth API (below). Trust only the facet-filtered
   query — NOT the "latest" version.

4. **Decide distribution format by platform exclusivity:**
   - Core mods are CurseForge-only (AE2, Flux Networks, Productive Bees/Trees, Dyson Cube,
     Distant Horizons, Twilight Forest, FerriteCore, LaserIO, Advanced AE, MEGA Cells, Applied
     Flux, AE2 Things, Embeddium Extras, Connectivity, Cupboard) → **CurseForge-format
     self-contained zip** (every jar bundled; friends need no CF API key). Reuse
     `minecraft-server-ops` refs: `shareable-modpack-export.md` + `full-self-contained-zip.md`.
   - **Prism Launcher: a self-contained `.mrpack` works even with CurseForge-only mods.** Put every
     jar in `overrides/mods/` and leave `files: []` — no Modrinth API resolution, so AE2, FTB Quests,
     Distant Horizons, etc. are all fine. Prism imports it via Add Instance → Import. For Ruben's own
     packs, deliver by dropping the file in `~/homeserver/www/` → `https://oathless.dev/files/<name>`
     (his Caddy static route). Full schema + build recipe: `references/prism-mrpack-and-distribution.md`.
   - Modrinth-native-only mods (Create Aeronautics, Sable) go into `overrides/` for a CF zip.
     (The CurseForge-launcher format — `manifest.json` + project/file IDs — is a separate target,
     only needed if someone imports through the CurseForge app itself.)

5. **Bundle the perf stack** — server + client (see reference). Shaders are OPT-IN, not forced
   (FPS killer on low-end machines). The server perf stack can be copied jar-for-jar from
   ATM10aero (already 1.21.1 NeoForge, version-matched).

## Version/loader verification (Modrinth API, no key)

```bash
# EXISTS? search
curl -s "https://api.modrinth.com/v2/search?query=<q>&facets=[[%22project_type:mod%22]]"
# IS THERE a 1.21.1 NeoForge build? facet-filtered — this is the reliable query
curl -s "https://api.modrinth.com/v2/project/<slug>/version?game_versions=%5B%221.21.1%22%5D&loaders=%5B%22neoforge%22%5D"
```

⚠️ Reading the `/version` list's `data[0]` (latest) is MISLEADING: since Minecraft 26.x, the
latest release targets the new MC. A mod whose latest "fails" (e.g. enderio v9.0.6-alpha shows
26.1.2; oculus latest shows 1.19.2) still has a valid 1.21.1 build further down the list.
ALWAYS facet-filter by game_versions + loaders.

A `404` on `/project/<slug>` = NOT on Modrinth → CurseForge-only (or distributed elsewhere,
e.g. Distant Horizons via GitLab/CF). Confirm on CurseForge via the API (classId=6) or
cfwidget (no key).

## Does a specific PACK include mod X? (Modpack Index curl)

When the question is "which packs include/avoid mod X" (e.g. "ATM10-like but no Apotheosis"),
don't trust search snippets or pack descriptions. Query Modpack Index — its pack pages are
server-rendered, so a plain curl + grep is authoritative, no browser or web-extract backend:

```bash
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
curl -sL "https://www.modpackindex.com/modpack/<id>/<slug>" -A "$UA" -o /tmp/p.html
grep -io '<modname-prefix>[a-z]*' /tmp/p.html | sort | uniq -c   # 0 matches = absent
```

Find the `<id>/<slug>` via `web_search "<pack name> modpackindex"`. Two gotchas:
- An invalid slug returns `404`, but a *stale* slug can silently redirect to a DIFFERENT pack's
  page (seen: `enigmatica-10` → `Odystria II`). Always confirm the returned `<title>` matches
  the pack you asked about before trusting the grep.
- The GitHub-repo `modlist.html` for some packs (e.g. bigchadguys) is another curl-able source,
  but watch the loader — the main repo may list the Fabric/Cobblemon variant, not the NeoForge
  "Non-Cobblemon" one. Cross-check the title/loader.

## Pitfalls
- **Only ship what the user explicitly asked for — don't pad the pack.** Every mod must trace to
  the wishlist (or an explicitly requested add, e.g. Building Gadgets). Unrequested additions get
  rejected — Apotheosis/Apothic suite + Occultism/Modonomicon/Ars Ocultas were pulled after the user
  objected "you added a lot of mods without my input". Suggested-but-unrequested mods belong in a
  *proposal list* for the user to approve, never in the assembled pack. This extends to INCREMENTAL
  maintenance of a live pack: when the user asks "is there a perf/QoL mod we're missing?", answer
  with a proposal + an explicit ask, then WAIT for "yes" before adding OR removing any jar. Ruben
  corrected this hard — "dont add without asking" — after mods were auto-added during tuning. Every
  add/remove on an existing pack requires prior approval.
- **Curating a client build from a server install:** a server's `data/config/` dir reveals client-only
  mods — their `*-client.toml` / `sodium-mixins.properties` / `iris-excluded.json` / `entityculling.json`
  configs ship via pack `overrides/` even though the jars never load server-side. Grep it to reconstruct
  the client mod list when the FTB manifest API is unavailable. For a client+server split: `client/mods/`
  = full set, `server/mods/` = minus client-only render/QoL mods. Details + the expanded 26.1.2 tech
  inventory in `references/26.x-neoforge-mod-availability.md`.
- **Loader version pins get ignored by Prism** — a self-contained pack pinned to `neoforge-21.1.250`
  still installs the LATEST NeoForge on the client, causing "Incompatible client! Please use NeoForge
  X" + cascading channel errors (e.g. glitchcore:sync_config). See `minecraft-server-ops` pitfall
  "Incompatible client! Please use NeoForge" for the fix (bump server to latest 21.1.x or pin client).
- **Verify a jar's `META-INF/neoforge.mods.toml` before trusting it — versionRange isn't the whole story.**
  A mod can pass the NeoForge *version* check and still not load: (a) the `modLoader` field may name a
  feature your NeoForge lacks — e.g. Zoomify 2.17+ declares `modLoader = 'klf'` (Kotlin Language
  Features), which older NeoForge pins don't recognize; (b) extra hard deps are listed that you don't
  ship (e.g. Controlling requires the `searchables` library). Unzip the jar, read `mods.toml`, and
  check `modLoader` + every `[[dependencies]]` block, not just the neoforge versionRange.
  In 26.x a `-forge` filename suffix does NOT mean Forge-loader — Forge ended at 1.21.x, so any
  `26.1` build (e.g. `BadOptimizations-2.4.1-26.1-forge.jar`) is NeoForge. Trust the `mods.toml`
  (`modLoader: javafml` + `minecraft [26.1,)` + `side: CLIENT`), not the filename.
- **Merging a source pack's `config/` tree — don't nest it.** If you `copytree` the merge-output
  root into `overrides/config`, you silently get `overrides/config/config/…` (Prism installs to
  `.minecraft/config/config/`, which Minecraft never reads). Copy `…/config → overrides/config` and
  `…/defaultconfigs → overrides/defaultconfigs` separately, then assert no `'config/config/'` entry
  exists in the archive. Also: to reproduce a source pack's **worldgen**, copy its *config files*
  (Evo 2 ships non-default Tectonic `vertical_scale: 1.06` + Terralith `skylands: true`), not just
  its mod jars. See `references/prism-mrpack-and-distribution.md`.
- **FTB Quests ids MUST be positive 64-bit longs.** Quest/chapter/task/reward/group ids are stored as
  signed `long`s. A 16-hex id whose first digit is `8`–`F` parses as NEGATIVE, and FTB Quests silently
  REJECTS it — assigning a fresh id on server load. That breaks the matching `chapter.<ID>.title` /
  `quest.<ID>.title` lang keys, so every affected chapter renders "Unnamed". Generate ids with
  `format(secrets.randbits(63), '016X')` (always starts `0`–`7`), NOT `uuid4().hex[:16]` (which starts
  `8`–`F` ~50% of the time). Lang key format is `chapter.<ID>.title` / `chapter_group.<ID>.title` /
  `quest.<ID>.title` in `lang/en_us/*.json5` — NOT a bare `"<ID>": "Title"` map. After first server
  load, FTB Quests re-serializes these files to unquoted-key JSON5; verify live ids == source ids
  (no reassignment) before trusting titles.
- **Dyson Cube Project** (Buuz135, CurseForge, 1.21.1 NeoForge, "build a Dyson sphere around the
  sun") ≠ **The Dyson Sphere Project** (Modrinth, 1.20.1 Forge only). When a user says "Dyson",
  confirm which.
- **Create: Aeronautics** requires **Sable** (physics library) as a hard dependency. Sable's
  Modrinth "latest" is Fabric — grab the NeoForge 1.21.1 jar matching Aeronautics' requirement,
  don't copy from latest.
- **EnderIO on 1.21.1 is alpha-quality** (v8/v9.x alpha). Works but rough edges; Pipez/LaserIO/
  XNet cover the same ground if it breaks.
- **Radium (Lithium port) clashes with C2ME** — pick Radium for tick-loop perf and skip C2ME
  (Chunky pregen covers worldgen lag). Don't ship both.
- **Embeddium + Oculus + Distant Horizons must be version-aligned** or you get client crashes /
  "network protocol error" disconnects. Pin one compatible set.
- **Chunky is server-only — never ship it in the client build.** Chunky (world pre-generation) only
  registers its `ChunkyProvider` on a dedicated server. If the client jar is also present, Distant
  Horizons' `ChunkyAccessor.bindOnGenerationProgressEvent()` calls `ChunkyProvider.get()` the moment
  the client receives its first chunk packet → `IllegalStateException: Chunky is not loaded` →
  `Failed to handle packet ClientboundBundlePacket, disconnecting` → **"Network Protocol Error"** kick.
  Diagnosis signal: thousands of `ClientPayloadHandler: Received synced attachments from unknown entity`
  WARN lines right before the disconnect. Fix: keep Chunky in `server/mods/` only (delete the jar from
  the client instance). It's the same failure family as the Embeddium/Oculus/DH alignment pitfall but a
  distinct trigger — check this when the client crashes on *join* (not startup).
- **DH and Chunky also conflict SERVER-side.** Putting Distant Horizons in `server/mods/` (for
  server-side LOD generation) alongside Chunky fires the same `IllegalStateException: "Chunky is not
  loaded"` during chunk promotion (`ReportedException: Exception during promotion of chunk to FULL
  status`) while the server preps spawn/pregen. NON-fatal (boot completes, `Done (…)`, chunks still
  generate) but it spams the log. Rule: DH and Chunky must not coexist on the SAME side. To get Chunky
  pregen + DH LODs without the conflict, keep DH client-only and let the client build LODs from the
  server's pregen'd chunks — don't add DH server-side when Chunky is already present.
- **Apple Silicon Macs cap FPS on OpenGL — MetalForge is the 2× lever but excludes shaders + DH.** Ruben plays on an M2 Pro: ~90 fps unshaded is the OpenGL-on-Metal ceiling, NOT a pack problem. MetalForge (native Metal, NeoForge 26.1.2) ≈2× FPS but is mutually exclusive with Iris/shaders AND Distant Horizons. Full trade-off matrix, the DH×shader compatibility table (Complementary = opt-in toggle, BSL/Bliss = auto), macOS-safe shaderpacks, shaderpack `.mrpack` bundling, and the zoom/keybind-search loader gotchas (Zoomify `klf` vs Ok Zoomer `javafml`; Controlling needs `searchables`): `references/macos-apple-silicon-rendering.md`.
- **Shaders on low-end machines** tank FPS. Ship Oculus + shaderpack opt-in (off by default);
  low-end friends run Embeddium + DH with shaders disabled — DH is the cheap-render-distance
  answer.
- **Overlapping recipes** (Create + AE2 + EnderIO + Mekanism all add ingots/crafting) → always
  include Polymorph + Almost Unified.
- **Apotheosis is near-universal in 1.21 kitchen-sinks — verify before assuming a pack skips it.**
  ATM10, FTB Evolution, Craftoria, Enigmatica 10, TNP Limitless 8, Spellbound Engineering,
  Tecnomancia, and Firmament Industry ALL ship Apotheosis (+ the "Apothic" family: Apothic
  Attributes, Apothic Enchanting, Apothic Spawners, Apothic Attractions, + Placebo lib). To get an
  ATM10-scale pack without it you must strip it or nerf it — see
  `references/apotheosis-free-pack-options.md` for the jar list, strip/nerf recipe, and verified
  per-pack inclusion status. Ties into the "don't pad the pack" rule: Ruben has now pushed back on
  Apotheosis twice (removed it from his own pack, then asked for an Apotheosis-free ATM10
  alternative) — treat Apotheosis as opt-in, default OFF.

## Client/server build split & client-only mod discovery
- Deliver a pack as two folders: `client/mods/` (everything) and `server/mods/` (shared only).
  Client-only mods (Sodium, Iris, Distant Horizons, ImmediatelyFast, FlickerFix, Athena, Entity
  Culling, Mouse Tweaks, AppleSkin, Just Zoom, etc.) are excluded from `server/mods/`. Verify the
  diff is exactly the client-only set with `diff <(ls client | LC_ALL=C sort) <(ls server | LC_ALL=C sort)`
  — pass `LC_ALL=C sort`; bare `comm`/`sort` breaks on case-sensitivity and reports false diffs.
- **When you only have a server's files (no client manifest), the `config/` dir reveals client-only
  mods**: packs ship configs for client mods that get copied to the server even though the server never
  loads them (`sodium-mixins.properties`, `iris-excluded.json`, `entityculling.json`,
  `immediatelyfast.json`, plus `*-client.toml` suffixes like `appleskin-client.toml`). Grep `config/`
  for render/perf/client keywords to enumerate the client mod set the server mods/ folder omits.
- **Client-side required deps hide from server mods folders** (`side="CLIENT"` deps, e.g. Oritech→athena)
  — see `references/26.x-neoforge-mod-availability.md` "Client-pack assembly pitfalls".
- Quest authoring (FTB Quests JSON5) — see `references/ftb-quests-authoring.md`.

## Reference files
- `references/1.21.1-neoforge-mod-availability.md` — verified availability/loader matrix for
  common tech-magic wishlist mods (CF-only vs Modrinth vs both), confirmed 1.21.1 NeoForge
  version pins, and the low-end client + server perf stack with verified slugs.
- `references/26.x-neoforge-mod-availability.md` — verified 26.1.2 NeoForge availability matrix
  (what HAS/NOT migrated), the version-fork decision, the keyless Modrinth-modpack inspection
  recipe, and the BA+ ("Better Adventures+") pack identity + default 26.1.2 AE2 addon set.
- `references/apotheosis-free-pack-options.md` — the "Apothic" family jar list, strip/nerf recipe,
  and verified per-pack Apotheosis inclusion status for 1.21 kitchen-sinks. Use when the user asks
  for "ATM10-like but no Apotheosis" or any "which packs avoid mod X" question.
- `references/ftb-quests-authoring.md` — how to author an FTB Quests 2001.x JSON5 quest book for 26.1.2
  (chapter/quest/lang file structure, the `id: "..."` item-ID-oracle grep, Python `json.dump`
  generation), Ruben's reward preferences (no FTB coin currency, XP + small useful item rewards,
  per-player `team_reward: false`), PLUS the two non-obvious follow-throughs: deploying quest changes
  to a LIVE itzg server progress-safely (ID-diff check, stop/copy/start, verify the "Loaded N quests"
  log line) and surgically injecting updated quest files into existing zip/.mrpack archives without
  rebuilding the full generated config tree. Use when a pack needs quests/chapters, or when shipping
  a quest update.
- `references/puffish-skills-and-magic-integration.md` — Puffish Skills + Paxi datapack delivery,
  category.json required fields (incl. the mandatory `background` tile), per-category XP source event
  types (`mine_block`/`#c:ores`, `increase_stat`, `criterion`, `deal_damage`/`kill_entity`/
  `take_damage`), mod attribute namespaces (puffish_attributes / arsmagicalegacy / combat_roll),
  Combat Roll + Thaumaturge `crimsonPortalRarity` integration, and the "never reuse a kitchen-sink
  Puffish tree" pitfall. Use when adding skills/magic to a pack.
- `scripts/depcheck.py` — jar-metadata dependency-closure checker. Run `python3 depcheck.py <mods_dir>`
  after assembling any pack to catch missing hard deps (auto-confirms JiJ-bundled deps). Unresolved
  entries are either missing jars, GAMELIBRARY mods (MANIFEST `FMLModType`), or combined-jar fabric-*
  false positives — see the 26.x reference for the full decision tree.
- `references/prism-mrpack-and-distribution.md` — self-contained `.mrpack` schema for Prism import
  (`files: []`, jars+config in `overrides/`), the double-nested `config/config/` pitfall, copying a
  source pack's configs to reproduce worldgen, and Ruben's Caddy delivery route
  (`~/homeserver/www/` → `https://oathless.dev/files/<name>`). Use when building a client pack to
  import into Prism or delivering any pack over HTTP.
- `references/macos-apple-silicon-rendering.md` — Apple Silicon (MetalForge vs OpenGL ceiling), the
  DH×shader compatibility matrix, macOS-safe shaderpacks, shaderpack `.mrpack` bundling, and the
  26.1.2 client-QoL loader gotchas (zoom + keybind-search). Use when the user reports low FPS on a
  Mac, asks for shaders, or wants zoom/keybind-search on 26.1.2.
- `references/apple-silicon-client-performance.md` — why macOS FPS is capped (OpenGL-on-Metal),
  MetalForge (native Metal backend, ~2× FPS but incompatible with Iris shaders + Distant Horizons),
  no-trade-off FPS levers (RD 8–10, Retina resolution, entity shadows off, heap + `-XX:+UseZGC`),
  and the macOS + Distant Horizons shaderpack compatibility lists. Use when a user reports low FPS
  on a Mac or wants shaders that work with DH.

## Client/server split + client-only discovery (also see 26.x reference)
The server's `config/` dir reveals the full client+server mod list (packs ship pre-generated configs
for client-only mods too) — use it to discover client perf/QoL mods the server `mods/` omits, without
touching the FTB/CurseForge manifest. For dual builds, keep `client/mods/` + `server/mods/` + a
`client-only-mods.txt`, and verify with an `LC_ALL=C sort` diff that only the client-only jars differ.
