# FTB Evolution 2 — pack ops notes (MC 26.1.2, NeoForge)

Deployed as `minecraft-evo2` (TYPE=FTBA, `FTB_MODPACK_ID=135`, `itzg/minecraft-server:java25`). Replaced Enigmatica 10 (world archived at `../minecraft-e10/data`). Deploy recipe + the `dsp` mod whitelist clobber are in SKILL.md § "Swapping to an FTB App pack".

## Identity (resolve via API)
`curl https://api.feed-the-beast.com/v1/modpacks/public/modpack/135` → `targets[]`: minecraft `26.1.2`, neoforge `26.1.2.109`, java `25.0.2+10-LTS`. Latest version `1.2.2` (version id `100561`). Pack page: `feed-the-beast.com/modpacks/135-ftb-evolution-2`. It does have a CF project id (`meta.curseforgeProjectId = 1731757`), and the same JSON carries `versions[]` (id/name/type/released per release). cfwidget returns empty for this pack — do NOT infer "not on CurseForge" from an empty cfwidget response.

## Pre-gen
Chunky **1.5.4 ships pre-bundled** — no download needed. Same command set as 1.4.x, but there is NO `chunky version` (returns "Incorrect argument for command"). Measured on the i5-9500T: **~12–20 chunks/sec WITHOUT C2ME** (63,001 chunks at radius 2000 in ~1h11m) — faster than the older ATM10aero estimate, so C2ME is unnecessary here. Completion detection: `chunky progress` returns `[Chunky] No tasks running.`; the `Task finished … (100.00%)` line lands in the server LOG, not the progress output. No `betterchunkloading` in this pack, so C2ME wouldn't conflict if ever wanted.

## Config toggles (data/config/, bind-mounted — edit host file then `docker restart`)
- **Waystones** → `waystones-common.toml` `[rules] enableXpCosts = false` (master switch for XP; siblings `enableDurability`, `enableCooldowns`). Balm "common" configs sync server→client automatically.
- `server.properties` is clobbered on FIRST boot by the `dsp` mod (see SKILL.md); override durable server settings via `/data/default-server.properties` (append keys) or via env on subsequent boots.

## Mod item IDs (for `/give`)
- `kindredspirits:golden_bone` — Golden Bone, Kindred Spirits' **Direwolf** taming item (33% tame chance per feed).
- Kindred Spirits: 7 species (Nightfox, T-Rex, Baby Dragon, Mini Player, Gremlin, Quokka, Direwolf). **ONE active bonded companion at a time** (not a pet army); the Kindred Charm summons/dismisses it, opens its storage, and deepens the bond. `config/kindredspirits-common.toml` has progression/bond/taming tuning (no companion-count knob).

## Resource-farming mod list (do NOT recommend the absent classics)
- In-pack: Mystical Agriculture (+ Agradditions/Tiered Crystals/Automation/Customization), Productive Bees (+ Mystian Apiary), Nautec 2 (bacteria farming), Hostile Neural Networks, Mob Flow Utilities, Agritech: Evolved (farm automation), BBL Dimensional Resources (interdimensional ore laser), Occultism miner spirits, Apotheosis/Apothic Spawners, Easy Villagers/Piglins.
- **Absent:** Mekanism, Industrial Foregoing, Immersive Engineering, Thermal, Create, Botania, RFTools, Actually Additions — don't suggest them for this pack; the passive-resource role is consolidated into MA + Bees + Nautec.

## Thaumaturge (magic mod — shipped 1.0.0, removed 1.0.1, re-addable)

FTB Evolution 2 originally shipped **Thaumaturge** (Thaumcraft-6-style magic mod, CF project 1628024, modid `thaumaturge`) + the **Applied Thaumaturge** AE2 addon in 1.0.0-rc.1 and 1.0.0, then removed both in 1.0.1 (Oct 8 2026, no reason given). The pack KEPT all its Thaumaturge integration — `config/thaumaturge/` + `config/thaumaturge-{common,server}.toml`, `config/attributefix/thaumaturge/`, KubeJS `server_scripts/systems/thaumaturge_research.js`, `datapacks/ftb/data/thaumaturge/` (aspects/loot/ores/recipes), `ftb-ores` amber oregen, and 4 Apotheosis eldritch bosses — behind a shim datapack `datapacks/thaumaturge-absent` whose `pack.mcmeta` literally says **"Delete this folder when Thaumaturge returns."**

**Re-add recipe (verified Oct 2026):** drop `thaumaturge-26.1.2-NeoForge-1.0.2.jar` into `data/mods/` (forgecdn `https://edge.forgecdn.net/files/9095/192/thaumaturge-26.1.2-NeoForge-1.0.2.jar`, SHA1 `f1d7445c4153eefd8797f498f97fa0138912f035`) and move `data/datapacks/thaumaturge-absent` OUT of the load path (it's a global datapack loaded by `ftb-pack-companion`; `world/datapacks` stays empty). Both required deps (Curios, Lithostitched) are already in the pack; optional JEI also present. Boot logs a benign `Missing data pack file/thaumaturge-absent` WARN (expected) and the mod comes up (`Serving N wand assembly recipes…`, Jade plugin, KubeJS research script, Refined-Types compat mixins activate). Client-side: players add the SAME jar (client+server content mod, gates joining); ~29 MB > Discord's 25 MB limit — distribute via the CF page or the forgecdn URL. The Applied Thaumaturge AE2 addon is re-added the same way: drop `appliedthaumaturge-1.0.0.jar` (CF project 1718689, forgecdn `https://edge.forgecdn.net/files/9090/736/appliedthaumaturge-1.0.0.jar`, SHA1 `e6f9cb1d198e7fbdf6d065a5f64c937119c72683`, ~1.5 MB); requires Thaumaturge + AE2 (`appliedenergistics2`) + Curios, all in-pack — no datapack changes. Both were re-added Oct 2026.

**Quests + material integrations (also removed in 1.0.1, re-addable):** the 1.0.0 pack shipped a `thaumaturge.json5` quest chapter (174 quests, chapter id `6EF52A92C93BE7E0`, group `4A2F4752A3C3721A` — that group still exists in `chapter_groups.json5`). Re-add = restore 10 files from the FTB 1.0.0 CDN and restart: `config/ftbquests/quests/chapters/thaumaturge.json5` + `config/ftbquests/quests/lang/en_us/chapters/thaumaturge.json5` + 8 textures (`kubejs/assets/ftb/textures/quests/renders/{at_infusion_provider,thaum_alchemy_rig,thaum_brass_golem,thaum_crimson_knight,thaum_infusion_altar,thaum_vis_crystals}.png`, `kubejs/assets/ftb/textures/quests/titles_and_logos/{thaumaturge,thaumaturge_title}.png`). FTB Quests reloads definitions from `config/ftbquests/quests/` on boot (`world/ftbquests/` is only per-player progress). Verified re-add → `Loaded … 42 chapters, 1851 quests`. Other removed Thaumaturge material integrations (optional — mod is playable without them): amber MA crop + ~10 ore→gem unification recipes + ore-source tag + hydroponic/garden recipes (~17 files), brass nugget unification (2), cinnabar ore loot tables (4). attributefix configs were only RENAMED `thaumcraft/`→`thaumaturge/` (still present). Thaumaturge materials: amber, cinnabar, brass, quicksilver, alumentum.

All of the above (mods + quests + amber/brass/cinnabar material files) were re-added Oct 2026. The cinnabar loot tables make `ftbmaterials:cinnabar_*_ore` drop `thaumaturge:quicksilver`; brass nugget recipe maps `#c:ingots/brass`→`ftbmaterials:brass_nugget`; amber MA crop + unification reference `thaumaturge:amber`/`ore_amber`. The 2 `kubejs/assets/mysticalagriculture/items/{amber_essence,amber_seeds}.json` are CLIENT-side tint overrides (amber color) — cosmetic only; add them to the client assets bundle for correct color. ⚠️ The crop's DEFINING config `config/mysticalcustomization/crops/amber.json` (registers `mysticalagriculture:amber_crop`/`amber_seeds`/`amber_essence`) is ALSO client-required — Mystical Customization configs are NOT synced server→client, so a client missing that file disconnects on join with `The server sent registries with unknown keys: ... amber_crop / amber_seeds / amber_essence`. Ship it at the same `config/` path alongside the tint overrides (see `references/connection-and-loader-mismatch-debugging.md` Signature 4).

**Client-side assets are NOT auto-served.** The pack's KubeJS web server (`config/kubejs/config/web_server.json`, `enabled: true`, port 61423) would serve `kubejs/assets/` to clients, but the container only publishes 25565 — so server-side `kubejs/assets/` (quest textures, custom item models) never reach clients. Any pack content in `kubejs/assets/` that you add server-side must ALSO be handed to players (drop into their client pack's `kubejs/assets/`). This is why re-adding the Thaumaturge quest chapter (server-side) left players seeing purple/black missing-texture quest images — the 8 `.png` files under `kubejs/assets/ftb/textures/quests/{renders,titles_and_logos}/` are client-side-only.

## Thaumaturge quests (removed with the mod in 1.0.1 — re-addable)

The old pack had a full Thaumaturge quest chapter, removed in 1.0.1 alongside the mod. Diffing the 1.0.0 vs 1.2.2 manifests (`…/modpack/135/100549` vs `…/100561`, `files[]`) shows exactly **10 files** removed:

- `config/ftbquests/quests/chapters/thaumaturge.json5` — **174 quests**, chapter id `6EF52A92C93BE7E0`, group `4A2F4752A3C3721A`, icon `thaumaturge:thaumonomicon`, `order_index: 7`.
- `config/ftbquests/quests/lang/en_us/chapters/thaumaturge.json5`
- 6 render textures → `kubejs/assets/ftb/textures/quests/renders/` (`thaum_infusion_altar.png`, `thaum_brass_golem.png`, `thaum_crimson_knight.png`, `thaum_alchemy_rig.png`, `thaum_vis_crystals.png`, `at_infusion_provider.png`)
- 2 title images → `kubejs/assets/ftb/textures/quests/titles_and_logos/` (`thaumaturge.png`, `thaumaturge_title.png`)

**Re-add:** fetch those 10 files from the 1.0.0 manifest (`files[]` URLs, all on `files.feed-the-beast.com`), place at matching paths, restart. No `chapter_groups.json5` change needed (group `4A2F4752A3C3721A` still exists); the `data.json5` diff between 1.0.0/1.2.2 is only autoclaim-reward settings — do NOT restore it. Server-side only (KubeJS serves the quest textures to clients automatically); quest item refs (`thaumaturge:thaumonomicon`, `essentia_crystal`, `salis_mundus`, …) resolve once the mod jar is present. Chapter `order_index` collisions are harmless (ties broken arbitrarily).

## FTB App API — version history, per-version mod lists, changelogs

To answer "was mod X ever in this pack" / "what changed between versions", the FTB App API
(`api.feed-the-beast.com`) exposes it with NO CF key:

- **Pack + version list:** `GET /v1/modpacks/public/modpack/<id>` → `versions[]` is
  metadata-only (`id`, `name`, `type` = release|archived, `released` unix ts). No mod lists here.
- **Full version manifest (the one with the mods):** `GET /v1/modpacks/public/modpack/<id>/<versionId>`
  → large JSON (~8 MB, 11k+ `files[]`). Each file = `{path, name, type, url, clientonly,
  serveronly, optional, sha1}`. Mods are the `path == "./mods"` entries; other path prefixes:
  `config`, `kubejs`, `datapacks`, `resourcepacks`, `shaderpacks`, `configureddefaults`. Diff the
  `./mods/*.jar` `name`s across versionIds to pin when a mod was added/removed.
- **Auto-generated changelog (fastest for add/remove/update):**
  `GET /v1/modpacks/modpack/<id>/<versionId>/changelog` → JSON `content` lists "Added/Removed/
  Updated" jar names. PITFALL: path is `modpack` (SINGULAR) with NO `public` segment —
  `.../public/modpack/<id>/version/<id>` and `.../public/modpack/<id>/<id>/changelog` both 404.
  The correct changelog URL is also present in the full manifest's `changelog` field.

Version IDs are discoverable from the pack endpoint's `versions[]`. (All FTB Evo 2 releases so
far target the same MC 26.1.2 / NeoForge 26.1.2.109 / Java 25.0.2.)

## Thaumaturge — was bundled, then removed in 1.0.1

`thaumaturge` (CF project 1628024, a Thaumcraft-6-style magic mod) + its `appliedthaumaturge`
addon shipped in 1.0.0-rc.1 and 1.0.0, then were dropped in 1.0.1 (changelog "Removed:
appliedthaumaturge-1.0.0.jar, thaumaturge-26.1.2-NeoForge-1.0.2.jar"). The pack STILL ships deep
Thaumaturge integration with the mod absent: `config/thaumaturge*`, KubeJS
`thaumaturge_research.js`, datapack content (base aspects, amber oregen,
`quicksilver_from_cinnabar_gem` recipe, 4 Apotheosis `thaumaturge_eldritch_*` bosses), gated
behind a `datapacks/thaumaturge-absent` shim. So re-adding the mod = drop
`thaumaturge-26.1.2-NeoForge-1.0.2.jar` (the exact jar FTB shipped, still the CF latest) into
`data/mods/`; the integration content is already present.
