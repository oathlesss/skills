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
