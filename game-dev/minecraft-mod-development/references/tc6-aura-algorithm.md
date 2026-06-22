# TC6 Aura Algorithm — Reference

Extracted from `thaumcraft.common.world.aura.AuraThread.processAuraChunk()`.

## Data Model

```
AuraChunk { short base; float vis; float flux; WeakReference<Chunk> chunkRef }
```

- **base**: set at chunk generation from biome averaging, clamped 0–500
- **vis**: current vis level (starts at base, regens toward base, capped at 32766)
- **flux**: pollution (starts at 0, grows from overspill, spills between chunks)

## Generation (AuraHandler.generateAura)

```java
// Average biome modifier over center chunk + 4 cardinal neighbors
float life = getBiomeAuraModifier(biome_center);
life += getBiomeAuraModifier(biome_north);
life += getBiomeAuraModifier(biome_south);
life += getBiomeAuraModifier(biome_east);
life += getBiomeAuraModifier(biome_west);
life /= 5f;

float noise = 1f + rand.nextGaussian() * 0.1f;
short base = (short) MathHelper.clamp(life * 500f * noise, 0, 500);
// vis starts at base, flux at 0
```

## Biome Modifiers (BiomeHandler)

| Tag | Multiplier | Aspect | Greatwood? |
|-----|-----------|--------|------------|
| MAGICAL | 0.75 | ORDER | yes, 1.0 |
| MUSHROOM | 0.75 | ORDER | no |
| JUNGLE | 0.60 | EARTH | no |
| FOREST | 0.50 | EARTH | yes, 1.0 |
| SWAMP | 0.50 | ENTROPY | yes, 0.2 |
| SPOOKY | 0.50 | FIRE | no |
| LUSH | 0.50 | WATER | yes, 0.5 |
| RIVER | 0.40 | WATER | no |
| DENSE | 0.40 | ORDER | no |
| WET | 0.40 | WATER | no |
| OCEAN/WATER | 0.33 | WATER | no |
| MESA/CONIFEROUS/HOT | 0.33 | FIRE | varies |
| MOUNTAIN | 0.30 | AIR | no |
| PLAINS | 0.30 | AIR | yes, 0.2 |
| HILLS | 0.33 | AIR | no |
| BEACH | 0.30 | EARTH | no |
| SAVANNA | 0.25 | AIR | yes, 0.2 |
| SNOWY/COLD/DRY | 0.25 | varies | no |
| SANDY | 0.25 | EARTH | no |
| SPARSE | 0.20 | ENTROPY | no |
| NETHER | 0.125 | FIRE | no |
| END | 0.125 | AIR | no |
| WASTELAND/DEAD | 0.10–0.125 | ENTROPY | no |

Our 1.21.1 implementation maps modern biome tags to these multipliers.

## Per-Second Processing (processAuraChunk)

Moon phase tables:
```
PHASE_VIS  = {0.25, 0.15, 0.10, 0.05, 0.00, 0.05, 0.10, 0.15}
PHASE_MAX  = {0.15, 0.05, 0.00, -0.05, -0.15, -0.05, 0.00, 0.05}
phaseFlux  = 0.25 - phaseVis
```

Each tick per loaded chunk:

1. **Vis equalization**: find neighbor with lowest vis (where vis+flux < base*phaseMax). If its vis < current*0.75, flow 1.0 vis to it.
2. **Flux equalization**: find neighbor with lowest flux. If current flux > max(5, base/10) and neighbor flux < current/1.75, flow 1.0 flux to it.
3. **Regen**: if vis+flux < base → add phaseVis to vis
4. **Overflow**: if vis > base*1.25 and rand < 0.1 → convert phaseFlux from vis to flux
5. **Instability**: if vis <= base*0.1 and vis >= flux and rand < 0.1 → add phaseFlux to flux
6. **Rift trigger**: if flux > base*0.75 and rand < flux/500/10 → trigger rift

## Key differences from our implementation

| Feature | TC6 | Our 1.21.1 implementation |
|---------|-----|--------------------------|
| Aura storage | Global ConcurrentHashMap | NeoForge AttachmentType on LevelChunk |
| Threading | Dedicated AuraThread per dimension | LevelTickEvent.Post (main thread, once/sec) |
| Chunk access | AuraWorld cache + WeakReference | Direct LevelChunk.getChunkNow() |
| Dirty tracking | CopyOnWriteArrayList per dimension | Simple boolean flag per attachment |
| Rifts | riftTrigger ConcurrentHashMap | Not yet implemented (Phase 7) |
