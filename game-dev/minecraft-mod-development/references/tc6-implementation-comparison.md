# TC6 Implementation Comparison — Lessons from Source Code Review

Condensed from a full diff review of our `thau` mod (NeoForge 1.21.1) against the decompiled TC6 source (`TheDarkTower314/Thaumcraft-6-Source-Code`), 370+ Java files.

## Aura System

### TC6's model (simpler)
```java
// AuraChunk.java — single float each, not per-aspect
short base;      // natural level from biome generation
float vis;       // current vis (can exceed base)
float flux;      // current flux
```
- **Base vs current**: `base` is the chunk's "natural" vis (determined by biome, Gaussian noise, neighbor average). Regen targets `base`, not a hard cap.
- **Single float vis**: not per-aspect. TC6 simplified from TC4's per-aspect model.
- **AuraHandler** is a static singleton using `ConcurrentHashMap<Integer, AuraWorld>` keyed by dimension ID.
- **Biome generation**: `generateAura(Chunk, Random)` averages biome aura modifiers of this chunk + 4 neighbors, applies `nextGaussian() * 0.1`, clamps to 0-500.
- **AuraThread** (background thread) for async processing.

### Our model (more granular but missing base)
```java
int[] vis = new int[6];    // one per primal — better than TC6!
int[] flux = new int[6];
float baseRegenRate = 0.5f;
// Missing: base concept, biome generation
```
**Fix priorities**:
1. Add `base[]` concept — set on chunk load from biome, regen targets base not MAX_VIS
2. Silverwood trees call `addVis()` on their chunk
3. Crucible spills call `addFlux()`

## Crucible — The Biggest Gap

### TC6 TileCrucible (375 lines) — what it has that we don't:

| Feature | Implementation |
|---------|---------------|
| **Fluid tank** | `FluidTank(FluidRegistry.WATER, 0, 1000)` — buckets fill/drain via Forge fluid API |
| **Gradual heating** | `heat` goes 0→200 based on block below (lava, fire, nitor, magma). Visuals change at 150+ |
| **Craft-then-absorb** | `attemptSmelt()`: try recipe match first from essentia, if match → eject result, consume essentia. Only absorb items if NO recipe matches. |
| **Overflow** | When `aspects.visSize() > 500`, `spillRandom()` — removes random aspect, calls `AuraHelper.polluteAura()` |
| **Spill on break** | `spillRemnants()` — converts all remaining essentia to flux pollution, drains water |
| **Visual effects** | Boiling bubbles, colored essentia particles, froth, bamf on craft, boil particles on spill |
| **Sounds** | Bubble sound on item absorption, spill sound, craft sound via `SoundsTC` |
| **Bellows** | External bellows block reduces cook time (not essential) |
| **Fluid capabilities** | Implements `IFluidHandler`, `IFluidTankProperties` — pipes can fill/drain |

### What we have (functional skeleton)
```java
boolean hasHeat;         // simple boolean check via getLightEmission()
int waterLevel;          // simple int, not fluid system
// absorbItems() only — no recipe crafting from crucible
```
**Minimum to ship**: implement `attemptSmelt()` — try recipe match first, if match → eat essentia + output item, if no match → absorb aspects.

## Infusion Altar — The Cathedral

### TC6 TileInfusionMatrix (1,019 lines) — core loop:

```
1. Scan surrounding blocks for pedestals (up to 12)
2. Check symmetry: for each pedestal at (x,z), must exist one at (-x,-z)
3. Pedestals provide ingredients, recipe matched against central item
4. Source essentia from nearby jars via pipe network
5. Crafting phases with stability tracking:
   - stability replenish rate: 0.05/tick base, boosted by stabilizers
   - instability = asymmetricPedestals * 0.15 + insufficientEssentia * 0.25
   - Events: item knock-off (3%), lightning (1%), item void (0.1%), flux generation (10%)
6. Partial ingredient consumption during crafting
7. XP reward on completion
8. Custom particle system: essentia streams, arc beams, infusion source FX
```

**Key state** (25+ fields):
- `pedestals: ArrayList<BlockPos>` — discovered pedestal positions
- `recipeEssentia: AspectList` — required essentia (serves as progress tracker — decremented as essentia flows in)
- `recipeIngredients: ArrayList<ItemStack>` — pedestal items
- `recipeOutput: Object` — result
- `stability: float`, `stabilityCap: int`, `stabilityReplenish: float`
- `sourceFX: HashMap<String, SourceFX>` — essentia flow tracking for rendering
- `problemBlocks: ArrayList<BlockPos>` — blocks causing asymmetry

### Our state: plain `Block` with no `BlockEntity`. Zero logic.

## Research System — Stages, Addenda, Warp

### What TC6 has that we're missing

1. **Multi-stage research**: Each `ResearchEntry` has `ResearchStage[]` — sequential stages with per-stage requirements (craft item, obtain item, know research, complete research). We have single-binary completion.

2. **Addenda**: Extra pages unlocked when OTHER research completes. E.g., completing `INFUSION` adds a page to `ESSENTIA_TUBES`.

3. **Knowledge types**: `Observation`, `Theory`, `Epiphany` — different XP curves. We have single point pool.

4. **Research flags**: `POPUP` (show completion popup), `RESEARCH` (track for next stage), `PAGE` (addendum page). We have just `completed` boolean.

5. **Warp from research**: Certain entries add permanent/normal warp on stage completion. Not implemented.

6. **ResearchEvent**: Fires `Knowledge` and `Research` events for mod compat.

7. **JSON loading**: `parseAllResearch()` reads from classpath JSONs. Ours is hardcoded.

8. **Siblings**: Completing research A can auto-complete sibling B. Our `siblings` field exists but is unused.

9. **XP reward**: `player.addExperience(5)` on completion.

### Minimum to improve
- Add multi-stage support (even if most entries have 1 stage)
- Make clicking entries in GUI actually send server packet and spend points
- Fires `ResearchCompletedEvent` for mod compat

## Arcane Workbench — TC6's Vis Integration

TC6's `TileArcaneWorkbench`:
- Has wand slot + vis relay connection
- Vis cost is per-recipe, stored as `int vis` on `ShapedArcaneRecipe`
- Vis is drawn from wand or nearby vis relays
- Falls back to vanilla crafting for recipes without vis cost

Our `ArcaneWorkbenchBlock` extends `CraftingTableBlock` — literally just opens vanilla crafting GUI. No vis tracking.

## Essentia Transport (Missing Entirely)

TC6 has a full essentia pipe network:
- `TileTube` — base pipe (connects jars to altars, crucibles, etc.)
- `TileTubeValve` — toggleable (redstone)
- `TileTubeRestrict` — one-way flow
- `TileTubeOneway` — directional
- `TileTubeFilter` — aspect-filtered
- `TileTubeBuffer` — buffer storage
- `TileJar` / `TileJarFillable` / `TileJarFillableVoid` — storage jars
- `TileAlembic` — distills essentia from items in furnace
- `TileCentrifuge` — processes compound aspects
- `TileSmelter` — faster essentia extraction

**Ponytail minimum**: implement `TileJar` (stores one aspect, used by infusion altar to source essentia). No pipes needed initially — just have the altar scan for jars within range.

## Golem AI — Modular Design Pattern

TC6's golem architecture (worth adopting):
```
GolemMaterial → body (straw, wood, clay, thaumium, void)
GolemArm     → interaction (pickup, use, attack, harvest)
GolemLeg     → movement (speed, step height)
GolemHead    → cosmetic (expression, model)
GolemAddon   → upgrade (air ring, fire ring, water ring, etc.)
Seal         → behavior programming (block golems path to)
Task         → assigned action (GET, STORE, USE, FIGHT, GUARD)
```

The seal system is the key design pattern: behavior is a **block entity** (seal) in the world, not a hardcoded AI. Golems path to their assigned seal, read its config, and execute the task. This means:
- Players program golems by placing seal blocks
- Seal blocks have configurable area/filter/toggles
- New behaviors = new seal types (data-driven)

## Particles and Effects (Missing Entirely)

TC6 has `FXDispatcher` with:
- Beams: arcs, bolts, streams
- Particles: sparkles, swarms, runes, shields, bore streams
- Projectiles: sonic blasts, void streams
- Block effects: bamf (teleport), boil, mist, arc

## Scorecard Reference

When reviewing Thaumcraft mod completeness against TC6, these are the benchmarks:

| System | TC6 equivalent | Lines | What "complete" looks like |
|--------|---------------|-------|---------------------------|
| Crucible | `TileCrucible.java` | 375 | Fluid tank, gradual heat, craft+absorb, overflow, particles, sound |
| Infusion | `TileInfusionMatrix.java` | 1,019 | Pedestal scan, symmetry, stability, essentia sourcing, events |
| Research | `ResearchManager.java` | 608 | Multi-stage, addenda, warp, theorycraft, JSON loading |
| Aura | `AuraHandler.java` + `AuraChunk.java` | 250 | Base concept, biome gen, rift tracking, background thread |
| Golems | Entity + seals + tasks | ~2,000 | Modular parts, seal-based AI, task system |
| Essentia | Tubes + jars + alembic | ~1,500 | Pipe network, storage jars, processing devices |
| Focus | Node tree + engine | ~1,500 | Composable spell graph, trajectory system |

## Key Takeaways

1. **Every "real" system is 200-1000+ lines.** A placeholder block (extends Block, no BE) is 0% of the work. A placeholder with items registered is 5%.

2. **TC6's API/impl split is the right pattern** — we already have `lib/` and `core/` matching it.

3. **Loose recipe matching is essential** for crucible — minimums-based, not exact match. TC6 got this right.

4. **Multiblock systems need visual feedback FIRST** — infusion altar, essentia pipes, the player must SEE what's happening. Particles are not polish, they're gameplay.

5. **Don't build pipes until jars work** — the jar is the minimum essentia storage unit. Infusion altar can scan for nearby jars. Pipes are a convenience layer on top.
