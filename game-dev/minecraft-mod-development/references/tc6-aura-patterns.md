# TC6 Aura System Reference (for NeoForge 1.21.1 implementation)

## TC6 Aura Architecture

```
AuraHandler    — static singleton, ConcurrentHashMap<Integer, AuraWorld>
AuraWorld      — holds ConcurrentHashMap<PosXY, AuraChunk> per dimension
AuraChunk      — short base, float vis, float flux, WeakReference<Chunk>
AuraThread     — background thread per dimension, 1s tick interval
```

## Key Mechanics (ported from TC6)

### Biome Generation (AuraHandler.generateAura)
```java
// Average biome modifier over center + 4 cardinal neighbors
float life = getBiomeModifier(chunk_center);
life += getBiomeModifier(north) + getBiomeModifier(south) 
     + getBiomeModifier(east) + getBiomeModifier(west);
life /= 5f;
float noise = 1f + rand.nextGaussian() * 0.1f;
short base = (short) MathHelper.clamp(life * 500 * noise, 0, 500);
// vis starts at base, flux at 0
```

### Neighbor Balancing (AuraThread.processAuraChunk)
- Vis flows from high to low neighbor if low/high < 0.75, 1.0f per tick
- Flux flows to lowest-flux neighbor if current > max(5, base/10) and lowest < current/1.75
- Natural regen: vis+flux < base → add phaseVis to vis
- Overflow: vis > base*1.25 → 10% chance to convert phaseFlux from vis to flux
- Low-vis instability: vis <= base*0.1 and vis >= flux → 10% chance to add phaseFlux
- Rift trigger: flux > base*0.75 → flux/5000 chance to set riftTrigger

### Moon Phase Tables
```java
phaseVis  = {0.25, 0.15, 0.10, 0.05, 0.00, 0.05, 0.10, 0.15}  // regen rate
phaseMax  = {0.15, 0.05, 0.00,-0.05,-0.15,-0.05, 0.00, 0.05}   // base multiplier
phaseFlux = 0.25 - phaseVis                                        // flux generation rate
```

### Biome Aura Multipliers (TC6 BiomeHandler)
Based on Forge BiomeDictionary types:
- MAGICAL: 0.75, MUSHROOM: 0.75
- JUNGLE: 0.60, FOREST: 0.50, LUSH: 0.50, SWAMP: 0.50, SPOOKY: 0.50
- RIVER: 0.40, DENSE: 0.40
- WATER/OCEAN: 0.33, MESA: 0.33, CONIFEROUS: 0.33, HILLS: 0.33
- HOT: 0.33, PLAINS: 0.30, MOUNTAIN: 0.30, BEACH: 0.30
- SANDY: 0.25, SNOWY/COLD: 0.25, DRY: 0.25, SAVANNA: 0.25
- NETHER: 0.125, END: 0.125, WASTELAND: 0.125
- DEAD: 0.10

## 1.21.1 Porting Notes

- BiomeDictionary doesn't exist in 1.21.1 — use BiomeTags instead
- AuraThread replaced with LevelTickEvent (server main thread, once/second)
- Forge Capabilities replaced with NeoForge AttachmentType
- WeakReference<Chunk> replaced with direct chunk attachment
- ConcurrentHashMap replaced with AttachmentType serialization (saved to chunk NBT)
