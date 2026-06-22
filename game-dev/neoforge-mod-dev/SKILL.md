---
name: neoforge-mod-dev
description: NeoForge 1.21.x mod development — project scaffolding, rapid iteration loop, registry patterns, common pitfalls, and the "write→build→fix→verify→commit" workflow.
triggers:
  - User asks to create/expand a NeoForge or Forge Minecraft mod
  - User references Thaumcraft, Minecraft modding, or mod development
  - Any task involving Gradle + NeoForge build system
---

# NeoForge Mod Development

## Trigger Conditions
Load this skill when the user asks to build, extend, or fix a NeoForge/Minecraft mod, or when working in a project that uses NeoGradle/ModDevGradle.

## Core Workflow: Write → Build → Fix → Verify → Commit

The fundamental iteration loop for rapid mod development:

1. **Write** — create all new files in one batch (Java classes, JSON resources, textures). Don't stop to build after each file; batch them.
2. **Build** — `./gradlew build`. Expect errors on first pass (imports, API mismatches).
3. **Fix** — `./gradlew build 2>&1 | grep "error:" | head -20` to get error summary. Fix all errors before re-building. Common fixes:
   - Wrong import paths (see Pitfalls below)
   - API signature changes in 1.21.x vs 1.20.x
   - Registry method changes
4. **Verify** — `timeout 30 ./gradlew runServer 2>&1 | grep -E "Done|error"`. Must see `Done (N.NNs)!` with no errors.
5. **Commit** — `git add -A && git commit -m "descriptive message"`. Commit immediately after verification.

**Never** stop after writing files without building. The deliverable is a working artifact backed by real build output.

## NeoForge 1.21.x Pitfalls

### Import Paths
- Custom packages must be consistent. When refactoring, use `sed` to batch-fix: `sed -i 's/old.package/new.package/g' file1.java file2.java`
- **Do not** rely on IDE; use grep+sed for bulk import fixes.

### Registry API Changes (1.21.x)
- `BuiltInRegistries.ENCHANTMENT.get(ResourceLocation)` returns `Holder.Reference<Enchantment>`, NOT raw `Enchantment`. Access `.value()` on the holder.
- `BuiltInRegistries.ENCHANTMENT.getOptional(key)` returns `Optional<Holder.Reference<Enchantment>>`.
- `RecipeManager.getRecipeFor()` uses `SingleRecipeInput` in 1.21.x, not `SimpleContainer`.

### Entity Rendering
- `IronGolemModel<T>` requires `T extends IronGolem`. For custom entities extending `PathfinderMob`, use `HumanoidMobRenderer` + `HumanoidModel` instead.
- Register renderers in a client setup class via `EntityRenderersEvent.RegisterRenderers`.

### Deprecated Annotations
- `@EventBusSubscriber(bus = EventBusSubscriber.Bus.MOD)` is deprecated. Use `@EventBusSubscriber(modid = "...", value = Dist.CLIENT)` without the `bus` parameter.

### Attachment Types
- NeoForge `AttachmentType` replaces Forge capabilities. Register via `DeferredRegister.create(NeoForgeRegistries.ATTACHMENT_TYPES, modId)`.
- Access on chunk: `chunk.getData(ATTACHMENT_TYPE.get())`.
- Access on player: `player.getData(ATTACHMENT_TYPE.get())`.

## Project Structure Pattern

```
src/main/java/com/<modid>/
  lib/          ← API surface (events, registries other mods depend on)
  core/         ← implementation
    block/      ← blocks + block entities
    item/       ← items + item subclasses
    entity/     ← entities + renderers
    world/      ← worldgen, structures, biomes
    aura/       ← domain-specific subsystems
    research/
    compat/     ← JEI/REI integration
```

## Stubbing Pattern

When an item/block/entity needs complex behavior that can't be implemented immediately:
1. Create the class as a simple extension of the base type (e.g., `extends Item`).
2. Register it in the DeferredRegister and creative tab.
3. Add model/blockstate JSONs so it renders in-game.
4. The behavior can be filled in later without breaking the build.

This lets you close gaps rapidly while keeping the build green.

## Verification

```bash
# Always verify with JAVA_HOME set
export JAVA_HOME=/path/to/jdk-21
./gradlew build                          # must pass with 0 errors
timeout 30 ./gradlew runServer 2>&1 | grep "Done"  # must show "Done (N.NNs)!"
```

## References
- `references/tc6-tc4-feature-checklist.md` — Comprehensive Thaumcraft 4/6 feature inventory for gap analysis
