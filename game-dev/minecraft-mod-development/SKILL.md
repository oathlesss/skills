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

## Procedural art pipeline for textures

**Default to procedural generation (Python + Pillow) for Minecraft pixel art.** Do not lead with AI image generation (SDXL/ComfyUI) for 16×16 or 32×32 textures.

- **Procedural**: ingots, crystals, shards, dusts, pattern-based blocks — geometric items. Scripts produce clean, consistent textures instantly.
- **Manual pixel art (Aseprite)**: crafting stations, entities, organic textures — anything needing character or personality.
- **AI generation**: concept art, mood boards, style reference only. Not for production textures.

Workflow: procedural scripts run first → manual touch-up in Aseprite where needed → verify in-game at actual size.

## Phased development strategy

Ship playable milestones, not back-end frameworks. Each phase should produce something the player can interact with in-game. Strict phase gating — finish one before starting the next.

## References

- `references/thaumcraft-remake-plan.md` — Full Thaumcraft recreation plan: system architecture, 9-phase roadmap with deliverables, performance strategy, risk analysis. This is the reference for large-scale Minecraft magic mod architecture.
- `references/procedural-textures.md` — Pillow-based 16×16 texture generation with shape templates (crystal, shard, ingot, sphere, block), color palettes, and verification workflow. Includes pointer to the Thaumcraft Phase 1 generation script at `/home/ruben/thaumcraft-textures/generate_materials.py`.
- `references/modrinth-api-research.md` — Modrinth v2 API workflow for discovering modpacks by mod combination. Covers search, dependency resolution, batch ID→name lookup, and the common cross-reference pattern. Use when the user asks "find me a modpack with X mods."
