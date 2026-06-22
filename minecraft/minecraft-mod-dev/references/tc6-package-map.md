# TC6 Source Code → thau mod Package Map

TC6 decompiled source: `/home/ruben/thaumcraft-reference-tc6-source/src/main/java/thaumcraft/`
Our mod: `/home/ruben/thaumcraft/src/main/java/com/thau/`

## Core Systems

| TC6 Package | TC6 Key Classes | Our thau Package | Our Classes |
|-------------|----------------|------------------|-------------|
| `api/aspects/` | Aspect, AspectList, IAspectContainer | `lib/aspect/` | Aspect, AspectList, AspectStack, Aspects, AspectRegistry, AspectRegistrationEvent, ScanEvent |
| `api/capabilities/` | IPlayerKnowledge, IPlayerWarp | `core/research/` | ResearchAttachment (combined both) |
| `api/research/` | ResearchCategories, ResearchEntry, ResearchStage, ResearchAddendum | `core/research/` | ResearchManager (merged) |
| `api/aura/` | AuraHelper | `core/aura/` | AuraAttachment, AuraManager |
| `api/crafting/` | CrucibleRecipe, InfusionRecipe, IThaumcraftRecipe | `core/recipe/` | CrucibleRecipe, ThauRecipes |
| `api/casters/` | IFocusElement, FocusNode, FocusEffect, FocusMedium, FocusEngine, FocusPackage | `core/item/wand/` | WandItem (simplified — no spell graph yet) |
| `api/golems/` | IGolemProperties, seals | `core/entity/` | GolemEntity (core-based without seal system) |
| `common/world/aura/` | AuraHandler, AuraChunk, AuraThread, AuraWorld | `core/aura/` | AuraManager (merged), AuraSyncPacket |
| `common/world/biomes/` | BiomeHandler, BiomeGenMagicalForest, BiomeGenEerie, BiomeGenEldritch | `core/world/` | FluxHandler, FluxWorldTick |
| `common/tiles/crafting/` | TileCrucible, TileInfusionMatrix, TileArcaneWorkbench, TileFocalManipulator | `core/block/entity/` | CrucibleBlockEntity, InfusionAltarBlockEntity |
| `common/tiles/essentia/` | TileJar, TileTube*, TileAlembic, TileCentrifuge | `core/block/entity/` | EssentiaJarBlockEntity (tubes/centrifuge not yet) |
| `common/tiles/devices/` | TileRechargePedestal, TileStabilizer | `core/block/entity/` | RechargePedestalBlockEntity |
| `common/lib/research/` | ResearchManager, ScanGeneric, theorycraft/ | `core/research/` | ResearchManager, ResearchSyncPacket |
| `common/lib/events/` | WarpEvents, EssentiaHandler | `core/world/` | WarpHandler, FluxHandler |
| `common/lib/network/` | PacketHandler, 37 packet classes | `core/` | ThauNetwork, AuraSyncPacket, ResearchSyncPacket |
| `common/entities/` | EntityGolem, EntityEldritchGuardian, EntityCultist*, EntityMindSpider | `core/entity/` | GolemEntity (no cultist/guardian yet) |
| `client/` | GuiResearchBrowser, GuiFocalManipulator, FXDispatcher | `core/client/` | ThaumonomiconScreen, ThaumometerBlockHud, AuraHudOverlay |

## Key Architecture Differences (TC6 vs our 1.21.1 port)

| TC6 (1.12.2) | Our (1.21.1) |
|--------------|--------------|
| `IProxy` + `CommonProxy` + `ClientProxy` | `Dist.CLIENT` checks + `@OnlyIn(Dist.CLIENT)` |
| `IMessage` + `IMessageHandler` | `CustomPacketPayload` + `StreamCodec` + `IPayloadContext` |
| Forge `Capability` system | NeoForge `AttachmentType` |
| `GameRegistry.register()` | `DeferredRegister` + `modEventBus.register()` |
| `ITickable` interface | `BlockEntityTicker<T>` lambda |
| `IInventory` | `SimpleContainer` / `Container` menu system |
| `FluidTank` (Forge fluids) | Simple `int waterLevel` (or `FluidStack` for full fluid support) |
| `WorldGenerator` + `IWorldGenerator` | Configured Feature + Placed Feature + Biome Modifier |
| NBT via `NBTTagCompound.writeToNBT` | `saveAdditional(CompoundTag, HolderLookup)` |

## Not Yet Ported (from TC6)

| Feature | TC6 Location | Priority |
|---------|-------------|----------|
| Essentia pipes/tubes | `tiles/essentia/TileTube*.java` (8 classes) | Medium |
| Alembic | `tiles/essentia/TileAlembic.java` | Medium |
| Centrifuge | `tiles/essentia/TileCentrifuge.java` | Medium |
| Focal Manipulator | `tiles/crafting/TileFocalManipulator.java` (318 lines) + GUI | High |
| Theorycraft GUI | `client/GuiResearchTable.java` | Medium |
| Infusion enchantments | `lib/crafting/InfusionEnchantmentRecipe.java`, `EnumInfusionEnchantment.java` | Medium |
| Custom potions (6 types) | `lib/potions/Potion*.java` | Low |
| Golem seals (full system) | `tiles/crafting/TileGolemBuilder.java`, seal networking | Low |
| Golem logistics | `ContainerLogistics.java`, `GuiLogistics.java` | Low |
| Eldritch dimension structures | `world/biomes/BiomeGenEldritch.java` | Medium |
| Cultist mobs | `entities/monster/cult/` (3+ classes) | Medium |
| Mind spiders | `entities/monster/EntityMindSpider.java` | Low |
| Eldritch Guardian boss | `entities/monster/EntityEldritchGuardian.java` | Medium |
| Custom particles (FXDispatcher) | `client/fx/FXDispatcher.java`, 16 packet types | Low |
| JEI/REI integration | N/A (not in TC6) | Medium |
