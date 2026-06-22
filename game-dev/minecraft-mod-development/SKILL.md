---
name: minecraft-mod-development
description: Minecraft mod development on NeoForge 1.21.x — project setup, architecture patterns, datapack design, procedural art pipeline, phased development strategy, and modpack discovery/research via the Modrinth API.
triggers:
  - Minecraft mod
  - NeoForge mod
  - Thaumcraft remake
  - Minecraft mod architecture
  - Minecraft mod planning
  - Minecraft datapack
  - Forge mod
  - Minecraft modpack
  - find modpack
  - modpack with
---

# Minecraft Mod Development

Use this skill when the user asks about Minecraft mod development, architecture, planning, or execution — specifically for modern NeoForge 1.21.x content mods. Also load this skill when the user asks to find, search for, or compare Minecraft modpacks — the Modrinth API research reference covers that workflow.

## Platform decision

**NeoForge 1.21.x is the default.** Reasons:

- Mature APIs for large content mods (attachments, registries, datapacks, datagen)
- Built-in systems: `AttachmentType` for world/player state, `DataComponentType` for item data, `datamap` for item→data mappings, `NetworkChannel` for sync
- Largest ecosystem for magic/content mods (Ars Nouveau, Botania, Blood Magic)
- **Do not default to multi-loader** (Architectury). Single-loader is simpler. Port to Fabric later if there's traction.

## Environment setup (no-sudo path)

When Java isn't installed and `sudo` isn't available (e.g. headless server):

1. **Fetch JDK 21 from Adoptium API:**
   ```bash
   curl -sL "https://api.adoptium.net/v3/assets/latest/21/hotspot?os=linux&architecture=x64&image_type=jdk" \
     -o /tmp/jdk_info.json
   python3 -c "import json; d=json.load(open('/tmp/jdk_info.json')); print(d[0]['binary']['package']['link'])"
   ```
   Note: the key is `binary` (singular), not `binaries`.

2. **Extract to user-local path:**
   ```bash
   mkdir -p ~/.local/java
   tar xzf /tmp/jdk21.tar.gz -C ~/.local/java
   ```

3. **Persist in `~/.bashrc`:**
   ```bash
   export JAVA_HOME="$HOME/.local/java/jdk-21.0.11+10"
   export PATH="$JAVA_HOME/bin:$PATH"
   ```

4. **Bootstrap Gradle wrapper**: download a Gradle binary distribution (e.g. gradle-8.12-bin.zip), extract with Python's `zipfile` module if `unzip` isn't available, then run `gradle wrapper --gradle-version 8.12` from the project root.

## Project scaffolding

### Version pinning

Always check latest versions via Maven metadata before scaffolding:
```bash
# ModDevGradle plugin version
curl -sL "https://maven.neoforged.net/releases/net/neoforged/moddev/net.neoforged.moddev.gradle.plugin/maven-metadata.xml"
# NeoForge version (filter for 21.1.x)
curl -sL "https://maven.neoforged.net/releases/net/neoforged/neoforge/maven-metadata.xml"
```

### Key Gradle files

**settings.gradle** — only plugin repos + toolchain resolver. ModDevGradle goes in build.gradle, NOT in settings.gradle:
```groovy
pluginManagement {
    repositories {
        mavenLocal()
        gradlePluginPortal()
        maven { url = 'https://maven.neoforged.net/releases' }
    }
}
plugins {
    id 'org.gradle.toolchains.foojay-resolver-convention' version '0.9.0'
}
```

**build.gradle** — `id 'java-library'` must precede `id 'net.neoforged.moddev'`:
```groovy
plugins {
    id 'java-library'
    id 'net.neoforged.moddev' version '2.0.141'
}
```

**gradle.properties** — all version properties as key=value, referenced via `project.mod_id` or `${mod_version}` in mods.toml expansion.

### Mod registration

Use `DeferredRegister` for items and creative tabs:
```java
public static final DeferredRegister<Item> ITEMS =
    DeferredRegister.create(Registries.ITEM, MOD_ID);
public static final Supplier<Item> EXAMPLE = ITEMS.register("example",
    () -> new Item(new Item.Properties()));
```
Register on the mod event bus in the `@Mod` constructor: `ITEMS.register(modEventBus)`.

## Critical build pitfalls

### 1. `${mod_version}` not expanded in mods.toml
**Symptom**: `Illegal version number specified mod_version`
**Cause**: The `processResources` task must be configured to expand Gradle properties into `neoforge.mods.toml`.
**Fix**: Add to build.gradle:
```groovy
tasks.withType(ProcessResources).configureEach {
    var replaceProperties = [
            minecraft_version : minecraft_version,
            neo_version       : neo_version,
            mod_id            : mod_id,
            mod_version       : mod_version,
    ]
    inputs.properties replaceProperties
    filesMatching(['META-INF/neoforge.mods.toml']) {
        expand replaceProperties
    }
}
```

### 2. Mod not found in dev runs
**Symptom**: `File build/classes/java/main is not a valid mod file`
**Cause**: ModDevGradle puts `META-INF/neoforge.mods.toml` in `build/resources/main/` but NeoForge's dev classpath scanner looks in `build/classes/java/main/`.
**Fix**: Copy META-INF to classes output after compilation:
```groovy
tasks.named('classes') {
    doLast {
        copy {
            from layout.buildDirectory.dir('resources/main/META-INF')
            into layout.buildDirectory.dir('classes/java/main/META-INF')
        }
    }
}
```

### 3. Duplicate META-INF in jar
**Symptom**: `Entry META-INF/neoforge.mods.toml is a duplicate`
**Cause**: The classes copy (fix #2) puts META-INF in the classes directory, and the jar task picks up both `resources/main` and `classes/java/main`.
**Fix**: Set duplicates strategy on jar task:
```groovy
tasks.named('jar') {
    duplicatesStrategy = DuplicatesStrategy.EXCLUDE
}
```

### 4. Server exits immediately
**Cause**: EULA not accepted in the `runs/server/` directory.
**Fix**: `echo "eula=true" > runs/server/eula.txt`. Also set `online-mode=false` in `runs/server/server.properties` for dev.

## Verification

- **Build**: `./gradlew build`
- **Mod loading**: `./gradlew runServer` — confirm `Mod List: ... YourMod X.Y.Z (modid)` appears with no errors following it.
- **Jar contents**: `jar tf build/libs/<modid>-<version>.jar | sort`

## Build system

- **Gradle** with ModDevGradle (standard for NeoForge)
- **Mixin** for deep hooks (entity AI, chunk events, render layers)
- **Datagen** from day one — all recipes, tags, models via DataProvider
- **JUnit 5 + GameTest** for automated in-game testing
- **GitHub Actions** for CI

## Architecture patterns

### Package structure
```
com.modname.lib/     ← API surface (other mods depend on this)
com.modname.core/    ← implementation
```

### Communication
- NeoForge event bus for cross-system notifications
- Attachments (capabilities) for persistent state storage
- Direct API calls within the mod — no unnecessary abstraction layers

### Data-driven design
Everything configurable via datapack JSON:
- Custom registries for aspects, research entries, spells
- Datamaps for item → data mappings
- Recipe types via custom recipe serializers
- Community-extensible by design

## Block/Entity Registration Pitfalls

### BaseEntityBlock requires codec() override
**Symptom**: `YourBlock is not abstract and does not override abstract method codec() in BaseEntityBlock`
**Fix**: Add a `MapCodec` field. Constructor must take `BlockBehaviour.Properties`:
```java
public static final MapCodec<MyBlock> CODEC = simpleCodec(MyBlock::new);
public MyBlock(BlockBehaviour.Properties properties) { super(properties); }
@Override protected MapCodec<MyBlock> codec() { return CODEC; }
```
`simpleCodec(MyBlock::new)` requires a `BlockBehaviour.Properties` constructor — a no-arg constructor fails.

### Separate sub-packages need their own DeferredRegisters

When adding a new package (e.g., `block/essentia/`) with its own blocks and block entities, create separate `DeferredRegister` instances and register them in the main `@Mod` constructor:

```java
// In Thaumcraft.java:
com.thau.core.block.essentia.ThauBlocks.BLOCKS.register(modEventBus);
com.thau.core.block.essentia.ThauBlocks.BLOCK_ITEMS.register(modEventBus);
com.thau.core.block.essentia.ThauBlockEntities.REGISTRY.register(modEventBus);
```

Each sub-package's `ThauBlocks` class is self-contained — it owns its own `DeferredRegister<Block>` and `DeferredRegister<Item>`.

### Check existing API signatures BEFORE writing new code

This is the #1 cause of batch compile failures. Before writing any file that calls methods on existing classes, **read the actual source files** to confirm the real method signatures. Do not assume:

- Package paths (e.g., `com.thau.lib.aspect` vs `com.thau.core.lib.aspect` — a single wrong prefix caused 9 files to break)
- Method signatures (`AuraManager.drainVis` takes `(ServerLevel, BlockPos, float, boolean)`, not `(Level, BlockPos, int, int)`)
- Constructor parameters (1.21.1 `ArmorItem` needs `Holder<ArmorMaterial>`, not `ArmorMaterial` directly)
- Field names on records (`AspectStack` has `aspectId()` and `amount()`, not `.aspect()`)

**Workflow**: write the first new file → `./gradlew build` → fix errors → then write the next. Do not batch-write 10+ files at once. Each file you write should reference only APIs you've confirmed exist.

### Strip to minimal when compile errors appear anyway

When you DO hit errors (wrong method signatures, missing fields), strip each broken class to its absolute minimal form — remove every method body that references uncertain APIs, keep only the constructor and serialization. Build, get green, then add complexity back one method at a time. If a file has 5+ errors, delete it entirely and start over — it's faster than patching.

### CraftingTableBlock subclass cannot override codec()
`CraftingTableBlock.codec()` returns `MapCodec<CraftingTableBlock>`. Don't override — the parent handles it. Just pass `BlockBehaviour.Properties` to super.
`CraftingTableBlock.codec()` returns `MapCodec<CraftingTableBlock>`. Don't override — the parent handles it. Just pass `BlockBehaviour.Properties` to super.

### FenceGateBlock — illegal forward reference
`WoodType` must be declared ABOVE any block registration that references it in a lambda. Java's static initializer order matters.

### TreeGrower takes ResourceKey, not ResourceLocation
Use `ResourceKey.create(Registries.CONFIGURED_FEATURE, ResourceLocation.fromNamespaceAndPath(MODID, "name"))`.

### Configured feature: avoid fancy_foliage_placer with IntProvider radius
In 1.21.x, `fancy_foliage_placer`'s `radius` is a plain `int`, not `IntProvider`. Use `blob_foliage_placer` for reliability.

### ItemInteractionResult.PASS does not exist
Use `ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION`.

### Entity base class for AI
If entity uses `FloatGoal`, `HurtByTargetGoal`, or pathfinding goals, extend `PathfinderMob` not `Mob`. Use `createLivingAttributes()`.

### EventBusSubscriber.Bus.MOD deprecation
In NeoForge 21.1.234+, the `bus` parameter emits deprecation warnings. This is cosmetic — code still works.

## Recipe System

### Critical: Object ingredient format
NeoForge 1.21.1 requires object format for ALL ingredients — even vanilla:
```json
// ✓ CORRECT:
"key": { "S": { "item": "minecraft:stick" } }
// ✗ WRONG:
"key": { "S": "minecraft:stick" }
```
Batch-fix existing recipes with the Python script: `python3 scripts/recipe-fixer.py`.
See `templates/recipe-shaped.json` for the correct template.

### Custom recipe type + serializer
1. Recipe class implementing `Recipe<SingleRecipeInput>` with custom `matches()`
2. Static `Serializer` inner class with `MapCodec` and `StreamCodec`
3. Registry: `DeferredRegister<RecipeType<?>>` + `DeferredRegister<RecipeSerializer<?>>`
4. Register both in main mod constructor

## Modpack Research (Modrinth API)

For finding Minecraft modpacks by mod inclusion, version, or category. Full workflow in `references/modrinth-api-research.md`.

### Quick reference: key project IDs
| Mod | Project ID |
|-----|-----------|
| Ars Nouveau | `TKB6INcv` |
| Create | `LNytGWDc` |
| Create Aeronautics | `oWaK0Q19` |
| Farmer's Delight | `R2OftAxM` |

### Reverse-search pattern (most effective)
1. Search for the rarest mod to get candidate packs
2. For each candidate, fetch its dependency list
3. Check for the other required mods by project ID
4. Only resolve names for matches

### Pitfalls
- **Minecolonies on Modrinth is outdated** (only 1.18.2). Its addons confirm it exists for modern versions but distribution is on CurseForge.
- **CurseForge pages are Cloudflare-protected**. Check GitHub for published modlists of major packs.
- **Dependency listing is `embedded`** for modpack mods — don't filter by dependency type.
- **Rate limiting**: batch-resolve IDs in chunks of 20-50 with small delays.

## Project: Thaumcraft Recreation

**Project path**: `/home/ruben/thaumcraft` | **Mod ID**: `thau` | **MC**: 1.21.1 NeoForge 21.1.234
**Java**: JDK 21 at `/home/ruben/.local/java/jdk-21.0.11+10`

Build & test:
```bash
cd /home/ruben/thaumcraft
export JAVA_HOME=/home/ruben/.local/java/jdk-21.0.11+10
./gradlew build                    # compile + jar
timeout 35 ./gradlew runServer     # headless server test
```

### Package structure
```
src/main/java/com/thau/
  lib/           API surface — aspects, datamap, mod compat events
  core/          Implementation
    aura/        AuraAttachment, AuraManager, AuraSyncPacket, VisNodeBlockEntity, GogglesHudOverlay
    block/       Block classes + ThauBlocks (60+ blocks)
    block/entity/ CrucibleBlockEntity, InfusionAltarBlockEntity, ResearchTableBlockEntity
    block/essentia/ AlembicBlockEntity, CentrifugeBlockEntity, FocalManipulatorBlockEntity, HungryChestBlockEntity, InfernalFurnaceBlockEntity, ArcaneBoreBlockEntity
    client/      ThaumonomiconScreen, AuraHudOverlay, ThaumometerBlockHud
    command/     EldritchCommand (teleport)
    entity/      GolemEntity, ThauEntities
    item/        ThauItems, ThauSeals, WandItem, WardingFocusItem, GogglesOfRevealing, FocusDefinitions
    recipe/      CrucibleRecipe, ThauRecipes
    research/    ResearchAttachment, ResearchManager, ResearchSyncPacket
    world/       ThauStructures, ThauDimensions, FluxWorldTick, WarpHandler
    worldgen/    Tree features, placed features, biome modifiers, MagicalForest
  Thaumcraft.java   Main mod class
```

### Implemented systems (60+ Java files)
- **Vis/Aura** — per-chunk vis+flux floats, biome generation, neighbor balancing, moon phases, silverwood boost
- **Aspects** — 52 code-registered aspects (TC4 data), AspectList, ItemAspects datamap
- **Research** — multi-stage entries, scanning→points, warp tracking, ResearchTable card minigame
- **Crafting** — Crucible (item absorption→essentia), Arcane Workbench, Infusion Altar (symmetry, instability, essentia sourcing)
- **Wands** — 3 tiers (Wooden/Greatwood/Silverwood), 7 foci (Fire/Excavation/Shock/Frost/PortableHole/Warding/EqualTrade), vis drain from aura
- **Golems** — 4 materials, 3 core types (Gather/Guard/Sort), 3 upgrades, 7 seal items + Golem Bell
- **Flux/Taint** — taint spread, ethereal bloom cleansing, fibrous taint, tainted soil
- **Warp** — 10 effect tiers (heartbeat, whispers, guardians, mist, mind spiders, sun scorn), eldritch research auto-unlock
- **Eldritch** — void dimension, teleport, cultist spawns, obelisks
- **Essentia piping** — Alembic (distills crucible essentia), Centrifuge (item→aspect breakdown), tubes
- **Focal Manipulator** — crystal→focus crafting
- **Machines** — Hungry Chest (auto-vacuum), Infernal Furnace (vis smelter, 2x speed), Arcane Bore (3×3 tunnel digger)
- **Warded blocks** — indestructible via Warding Focus
- **Goggles of Revealing** — aura HUD overlay
- **Vis Nodes** — natural aura sources, TC4-style
- **Magical Forest** — custom biome JSON
- **Config** — TOML, all systems configurable

### Known gaps (post Phase 9 audit)

These systems are registered/exist but have partial implementations. Do not treat them as complete:

| Gap | Status | What's missing |
|-----|--------|----------------|
| Essentia tubes | Blocks exist, **no network code** | Tubes don't transport essentia between machines — tube networking classes were deleted during a compile fix |
| Eldritch structures | DeferredRegisters only | ThauStructures.java is just stubs — no NBT structure templates, no obelisk/maze/pillar generation |
| Golem rendering | No custom renderer | Golems use vanilla entity rendering; invisible without textures or model JSON |
| Cultist mobs | Deleted (compile error) | NearestAttackableTargetGoal type inference failed — fixable |
| Infusion enchantments | Deleted (Aspect API mismatch) | 15 enchantment→aspect mappings defined but not wired to infusion altar |
| Custom particles | Deleted (deprecated API) | Vis stream, flux rift particle classes exist but registration uses removed `@EventBusSubscriber(bus=…)` |
| JEI integration | Deleted (no JEI dependency) | Recipe/aspect display plugin removed until JEI is added to build.gradle
| Thaumonomicon GUI | Minimal | Research entry pages render but no category tabs or visual research tree |

### Post-implementation audit pattern

After a large batch session, run a systematic audit before reporting completeness:

1. `find src -name '*.java' | sort` — full file inventory
2. For each deleted/critical file from earlier commits, check `git show <commit> --stat` to see what was removed
3. Cross-reference meta-prompt batch items against current file list
4. Read key files to check whether they're functional or stubs
5. Report honestly with ✅ / ⚠️ / ❌ categories

Never claim "everything is done" without this audit. The user will catch it.

### Aura System (TC6-derived)
- Single vis/flux floats per chunk (not per-aspect arrays)
- Base set at chunk generation from biome tag averaging + Gaussian noise
- Regen, neighbor balancing, moon phase modulation
- Flux saturation > 75% triggers rifts
- Per-chunk state via AttachmentType on LevelChunk with dirty tracking
- See `references/tc6-aura-algorithm.md` for full TC6 comparison

### Recipe fixer script
`scripts/recipe-fixer.py` batch-fixes old string-format recipes to object format for NeoForge 1.21.1.

### Related project files
- Plan: `/home/ruben/thaumcraft-remake-plan.md`
- TC6 reference: `/home/ruben/thaumcraft-reference-tc6-source/`
- TC4 reference jar: `/home/ruben/thaumcraft-reference/Thaumcraft-1.7.10-4.2.3.5.jar`

## Procedural art pipeline for textures

**Default to procedural generation (Python + Pillow) for Minecraft pixel art.** Do not lead with AI image generation (SDXL/ComfyUI) for 16×16 or 32×32 textures.

- **Procedural**: ingots, crystals, shards, dusts, pattern-based blocks — geometric items. Scripts produce clean, consistent textures instantly.
- **Manual pixel art (Aseprite)**: crafting stations, entities, organic textures — anything needing character or personality.
- **AI generation**: concept art, mood boards, style reference only. Not for production textures.

Workflow: procedural scripts run first → manual touch-up in Aseprite where needed → verify in-game at actual size.

## Phased development strategy

Ship playable milestones, not back-end frameworks. Each phase should produce something the player can interact with in-game. Strict phase gating — finish one before starting the next.

### Continuous development loop (meta-prompt driven)

When executing a large multi-batch plan (10+ items), use this pattern:

1. **Write the meta-prompt first** — a self-contained prompt that lists ALL batch items, the working method (implement → build → verify → commit), and a stopping condition ("until there are no more gaps"). Give it to yourself.
2. **Execute all batches without stopping** — do not stop at 6/16 and report "remaining items are pending." The user said "continuous loop until there are no more gaps" — that means KEEP GOING until every item is done or you hit a genuine blocker you cannot resolve.
3. **Build after every subsystem** — `./gradlew build` must stay green. Fix compile errors before continuing.
4. **Verify server loads** — `timeout 35 ./gradlew runServer` and confirm `Done (N.Ns)!` with no errors.
5. **Commit after each batch** — atomic, well-described commits make rollback possible.
6. **Never give a pending-items status dump** when you could just continue implementing. The user wants completion, not a progress report.
7. **When the user asks to check again or verify completeness** — run the systematic gap audit (see Post-implementation audit pattern above), not a yes/no answer. Answer with the audit results.

Pitfall: The user corrected you did NOT finish when work stopped at 6 of 16 items. If the meta-prompt says continuous, it means continuous. If the user asks whether everything is done, do not say yes until you have actually checked every file.

## References

- `references/thaumcraft-remake-plan.md` — Full Thaumcraft recreation plan: system architecture, 9-phase roadmap with deliverables, performance strategy, risk analysis.
- `references/tc6-api-architecture.md` — Decompiled TC6 API design patterns from Azanor's original source.
- `references/tc6-implementation-comparison.md` — System-by-system gap analysis between `thau` mod and TC6 source. Scorecard, missing features, implementation benchmarks.
- `references/tc6-aura-patterns.md` — TC6 aura system mechanics (biome generation, neighbor balancing, moon phases, biome multipliers) with 1.21.1 porting notes.
- `references/tc6-aura-algorithm.md` — Full TC6 aura algorithm comparison for the Thaumcraft recreation.
- `references/attachment-patterns.md` — NeoForge AttachmentType patterns: per-chunk state with dirty tracking, ticking chunks near players, client-side LRU caching, and packet sync. Covers the gotcha that ChunkMap.getChunks() is protected in 1.21.x.
- `references/procedural-textures.md` — Pillow-based 16×16 texture generation with shape templates, color palettes, and verification workflow.
- `references/procedural-minecraft-textures.md` — Pillow texture generation patterns for ingots, crystals, shards, blocks, and tree items.
- `references/texture-extraction.md` — Extracting and remapping textures from old mod JARs with Python zipfile.
- `references/modrinth-api-research.md` — Modrinth v2 API workflow for discovering modpacks by mod combination.
- `references/modpack-landscape-ars-create-aeronautics.md` — Concrete modpack landscape analysis: Ars Nouveau + Create + Aeronautics intersection.
- `references/gap-analysis.md` — Systematic audit framework for mod projects. Steps for file inventory, batch cross-referencing, honest status reporting. Includes current Thaumcraft known gaps.

## Templates and Scripts

- `templates/recipe-shaped.json` — Correct NeoForge 1.21.1 shaped recipe JSON template (object ingredient format).
- `scripts/recipe-fixer.py` — Batch-fix old string-format recipes to object format for NeoForge 1.21.1.
