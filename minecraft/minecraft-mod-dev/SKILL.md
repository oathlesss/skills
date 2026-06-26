---
name: minecraft-mod-dev
description: >
  Develop a Minecraft NeoForge 1.21.x+ mod. Trigger when the user wants to create,
  modify, build, or review a NeoForge mod. Covers project scaffolding, registries,
  recipes, block entities, networking, attachments, worldgen, entities, rendering,
  datapack integration, and pitfalls specific to 1.21.x NeoForge.
trigger_keywords: [neo, neoforge, minecraft mod, regist, recip, block entity, attachment,
  gametest, worldgen, jar-in-jar, mixin, gradle moddev, thaumcraft, thau, data component,
  stream codec, payload, DeferredRegister]
---

# Minecraft NeoForge Mod Development

Target: NeoForge 1.21.x (ModDevGradle 2.0.x+). Single-loader unless user explicitly
requests multi-loader. JDK 21 required.

## Meta-Prompting (mandatory for this user)

Before any mod work, the user expects an explicit meta-prompt planning step.
Assess the task, plan the approach, check assumptions, then execute. For large
changes, go through a review→implement→verify cycle.

The user also expects the development loop to be continuous: when they say
"keep yourself in a loop" or "keep repeating until complete", they mean
review against reference source → identify gaps → implement → build → test → commit → repeat
without waiting for permission between cycles.

## Stubbing Pattern

When an item/block/entity needs complex behavior that can't be implemented immediately:
1. Create the class as a simple extension of the base type (e.g., `extends Item`).
2. Register it in the DeferredRegister and creative tab.
3. Add model/blockstate JSONs so it renders in-game.
4. The behavior can be filled in later without breaking the build.

This lets you close gaps rapidly while keeping the build green.

## Project Setup

```bash
# JDK 21 required
export JAVA_HOME=~/.local/java/jdk-21.0.11+10  # adjust to user's path

# Init gradle wrapper
gradle wrapper --gradle-version 8.12

# build.gradle essentials
plugins { id 'net.neoforged.moddev' version '2.0.141' }
neoForge { version = '21.1.234' }
```

Package structure: `com.<modid>.lib/` for API surface (events, interfaces,
datamaps), `com.<modid>.core/` for implementation (blocks, entities, worldgen).

## Build/Verify Cycle

After EVERY code change:
```bash
./gradlew build       # must pass with 0 errors
./gradlew runServer   # must show "Done (X.XXXs)!" with no ERROR lines
# Quick combined check:
./gradlew build 2>&1 | tail -5 && timeout 30 ./gradlew runServer 2>&1 | grep "Done"
```

Commit after each working subsystem with a descriptive message.

## Pre-commit Hook (strongly recommended)

Catch compilation errors BEFORE they reach a commit:

```bash
# .git/hooks/pre-commit
#!/bin/bash
set -e
export JAVA_HOME="${JAVA_HOME:-$HOME/.local/java/jdk-21.0.11+10}"
./gradlew build 2>&1 | tail -20
if ! ./gradlew build 2>&1 | grep -q "BUILD SUCCESSFUL"; then
    echo "❌ BUILD FAILED — commit blocked."
    exit 1
fi
echo "✓ Build passed — allowing commit."
```

The Thaumcraft project at `/home/ruben/thaumcraft` already has this hook installed.

### PITFALL: `./gradlew build` only catches compilation, not asset gaps

The build passes even when:
- Block models reference missing texture PNGs
- Items lack model JSONs entirely
- Entities have no registered renderer
- Structures have empty registries

These are runtime-only failures. After batch-creating blocks/items/entities,
always verify visually in-game or run the asset validation script:
`python3 scripts/validate-assets.py` (see `scripts/validate-assets.py` in this skill).
The gap audit at `/home/ruben/thaumcraft` (June 2026) found 15+ critical
asset-gap issues that all passed compilation.

## NeoForge 1.21.x Pitfalls

### Recipe JSON format
Raw string ingredient keys DO NOT WORK for mod items in NeoForge 1.21.1.
Always use object format:
```json
"key": {
  "S": { "item": "thau:arcane_stone_block" },
  "G": { "item": "minecraft:glass" }
}
```
NOT: `"S": "thau:arcane_stone_block"` — this will fail with
"Not a json array / Not a JSON object".

### RandomSource vs Random
`level.random` returns `RandomSource`, not `java.util.Random`.
For methods requiring `Random`, cast: `(Random) (Object) level.random`.

### ChunkEvent.Load.getChunk()
Returns `ChunkAccess`, not `LevelChunk`. Must cast:
```java
ChunkAccess chunkAccess = event.getChunk();
if (!(chunkAccess instanceof LevelChunk chunk)) return;
```

### ItemInteractionResult
No `PASS` constant. Use `ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION`.

### SmallFireball constructor (1.21.1)
Constructor is `SmallFireball(EntityType.SMALL_FIREBALL, Level)`, then use
`setPos()` and `setDeltaMovement()`. NOT the old `(Level, LivingEntity, dx, dy, dz)`.

### Packet handler @OnlyIn
Do NOT put `@OnlyIn(Dist.CLIENT)` on static packet handler methods. It causes
`NoSuchMethodError` on server due to class stripper. Remove the annotation
and guard internally if needed.

### PlayerInteractEvent.RightClickEmpty
This event does NOT have `getItemStack()`. Use `event.getEntity().getItemInHand(event.getHand())`.
Does NOT have `setCanceled()`.

### Collections.shuffle with RandomSource
Not supported. Use `new Random()` or skip shuffling if order doesn't matter.

### Datapack resource loading at server start
`AddServerReloadListenersEvent` does NOT exist in NeoForge 1.21.x.
For reading datapack resources when the server starts, use
`ServerAboutToStartEvent` — its `getServer().getResourceManager()` provides
the full datapack resource manager. Load JSON from it with `listResources()`
and `resource.open()`.  For continuous reload-on-datapack-change use a
`PreparableReloadListener` registered via the mod event bus.

### Import Paths (bulk fixes)
When refactoring packages, use `sed` for batch fixes — don't fix files one at a time:
```bash
sed -i 's/old.package/new.package/g' src/main/java/com/thau/**/*.java
```

### Registry API Changes (1.21.x)
- `BuiltInRegistries.ENCHANTMENT.get(ResourceLocation)` returns `Holder.Reference<Enchantment>`, NOT raw `Enchantment`. Access `.value()` on the holder.
- `BuiltInRegistries.ENCHANTMENT.getOptional(key)` returns `Optional<Holder.Reference<Enchantment>>`.
- `RecipeManager.getRecipeFor()` uses `SingleRecipeInput` in 1.21.x, not `SimpleContainer`.

### Deprecated Annotations
- `@EventBusSubscriber(bus = EventBusSubscriber.Bus.MOD)` is deprecated. Use `@EventBusSubscriber(modid = "modid", value = Dist.CLIENT)` without the `bus` parameter.

### Entity renderer for Monster-derived entities
`HumanoidMobRenderer` requires the entity to extend `HumanoidMob`.
Entities extending `Monster` directly (like CultistEntity) cannot use it.
Use `MobRenderer<EntityType, HumanoidModel<EntityType>>` instead — the
`HumanoidModel` is still valid, just the renderer base class differs:
```java
public class CultistRenderer extends MobRenderer<CultistEntity, HumanoidModel<CultistEntity>> {
    public CultistRenderer(EntityRendererProvider.Context ctx) {
        super(ctx, new HumanoidModel<>(ctx.bakeLayer(ModelLayers.PLAYER)), 0.5f);
    }
}
```

### Block item access across packages
When block items are registered in a separate `ThauBlocks` class (e.g.,
`com.thau.core.block.essentia.ThauBlocks`), access them in the creative tab
via the `item(String name)` accessor:
```java
output.accept(com.thau.core.block.essentia.ThauBlocks.item("alembic").get());
```
Make sure the `item()` method is `public static` and returns `Supplier<Item>`.

### Registries — custom vs vanilla
For custom registries (like aspects): register via `RegisterEvent` in a
`@EventBusSubscriber` class, not datapack JSON. NeoForge 1.21.x custom
registry loading from JSON has limitations; code-side registration is
more reliable and still extensible via events.

### Recipe type registration
```java
public static final DeferredRegister<RecipeType<?>> RECIPE_TYPES =
    DeferredRegister.create(Registries.RECIPE_TYPE, modId);
public static final DeferredRegister<RecipeSerializer<?>> RECIPE_SERIALIZERS =
    DeferredRegister.create(Registries.RECIPE_SERIALIZER, modId);
```

### Network packets
Use `CustomPacketPayload` + `StreamCodec` pattern. Encode/decode with
`FriendlyByteBuf.readVarInt()/writeVarInt()` and `readUtf()/writeUtf()`.
Register handler via `registrar.playToClient(payload.TYPE, payload.STREAM_CODEC, payload::handle)`.

## Pattern: AttachmentType for state

```java
// Registration
public static final DeferredRegister<AttachmentType<?>> ATTACHMENT_TYPES =
    DeferredRegister.create(NeoForgeRegistries.ATTACHMENT_TYPES, modId);
public static final Supplier<AttachmentType<MyAttachment>> MY_ATTACHMENT =
    ATTACHMENT_TYPES.register("name",
        () -> AttachmentType.builder(MyAttachment::new)
            .serialize(MyAttachment.CODEC).build());

// Usage
LevelChunk chunk = ...;
var data = chunk.getData(MY_ATTACHMENT.get());
data.doSomething();
chunk.setData(MY_ATTACHMENT.get(), data); // flush changes
```

## Pattern: BlockEntity with ticker

```java
public class MyBlock extends BaseEntityBlock {
    @Override public BlockEntity newBlockEntity(BlockPos pos, BlockState state) { ... }
    @Override public <T extends BlockEntity> BlockEntityTicker<T> getTicker(
            Level level, BlockState state, BlockEntityType<T> type) {
        return level.isClientSide() ? null :
            createTickerHelper(type, MY_ENTITY_TYPE.get(), MyBlockEntity::tick);
    }
}
```

## Pattern: Datamap (item→aspect, etc.)

```java
public static final DataMapType<Item, List<AspectStack>> ITEM_ASPECTS =
    DataMapType.builder(
        ResourceLocation.fromNamespaceAndPath(modId, "item_aspects"),
        Registries.ITEM,
        AspectStack.LIST_CODEC
    ).build();

// Usage
var data = item.builtInRegistryHolder().getData(ITEM_ASPECTS);
```

## Pattern: DataComponent registration (1.21.x)

For storing persistent data on items (like bound positions for a Magic Mirror):

```java
public static final DeferredRegister<DataComponentType<?>> DATA_COMPONENTS =
    DeferredRegister.create(Registries.DATA_COMPONENT_TYPE, modId);

// Define the component with Codec + StreamCodec
public record MirrorBinding(ResourceKey<Level> dim, BlockPos pos) {
    public static final Codec<MirrorBinding> CODEC = RecordCodecBuilder.create(i ->
        i.group(
            Level.RESOURCE_KEY_CODEC.fieldOf("dim").forGetter(MirrorBinding::dim),
            BlockPos.CODEC.fieldOf("pos").forGetter(MirrorBinding::pos)
        ).apply(i, MirrorBinding::new));
}

public static final Codec<List<MirrorBinding>> BINDINGS_CODEC =
    MirrorBinding.CODEC.listOf();

public static final Supplier<DataComponentType<List<MirrorBinding>>> BINDINGS =
    DATA_COMPONENTS.register("bindings",
        () -> DataComponentType.<List<MirrorBinding>>builder()
            .persistent(BINDINGS_CODEC)
            .networkSynchronized(ByteBufCodecs.fromCodecWithRegistriesTrusted(BINDINGS_CODEC))
            .build());

// Read/write on ItemStack
List<MirrorBinding> bindings = stack.getOrDefault(BINDINGS.get(), List.of());
stack.set(BINDINGS.get(), newBindings);
```

Register the `DATA_COMPONENTS` DeferredRegister in the mod constructor alongside
other registries.  Use `stack.getOrDefault(component, default)` to read safely.

## Pattern: Multipart blockstate (pipe/tube connections)

For blocks that connect to neighbors (pipes, tubes, cables), use multipart
blockstate JSON with BooleanProperty directions:

```java
public static final BooleanProperty NORTH = BooleanProperty.create("north");
// ... SOUTH, EAST, WEST, UP, DOWN

@Override
public BlockState getStateForPlacement(BlockPlaceContext ctx) {
    return defaultBlockState()
        .setValue(NORTH, canConnectTo(ctx.getLevel(), pos, Direction.NORTH))
        // ... other directions
        ;
}
```

Blockstate JSON using multipart:
```json
{
  "multipart": [
    { "apply": { "model": "mod:block/pipe_core" } },
    { "when": { "north": true }, "apply": { "model": "mod:block/pipe_side" } },
    { "when": { "south": true }, "apply": { "model": "mod:block/pipe_side", "y": 180 } }
  ]
}
```

## Reference: TC6 source code

The user keeps TC6 decompiled source at:
- `/home/ruben/thaumcraft-reference-tc6-source/` (main TC6 decompiled)
- `/home/ruben/thaumcraft-reference-thavma/` (small mixin-focused port)

When comparing against TC6, read the relevant files from these paths,
study the class structure, and adapt to 1.21.x patterns (e.g., capabilities
become attachments, IMessage becomes CustomPacketPayload, IWorldGenerator
becomes biome modifiers + placed features).

## References

- `references/tc6-package-map.md` — Map of TC6 source packages to our thau equivalents
- `references/nbt-structure-gen.md` — Python NBT generation script + structure datapack chain
- `references/mod-idea-bank.md` — 625 learning-mod ideas in Obsidian, organized by category and complexity
- `scripts/validate-assets.py` — Post-build checker: verifies every registered block/item has model JSONs and all texture references resolve to actual PNG files

## Companion Documents

- `/home/ruben/obsidian-vault/inbox/minecraft-mod-reference.md` — Condensed quick-reference (Tips & Tricks, Best Practices, Common Examples, Quick Reference table) in the same format as the Go reference doc. Use for fast lookups; use this skill for the deep reference and procedural workflows.
