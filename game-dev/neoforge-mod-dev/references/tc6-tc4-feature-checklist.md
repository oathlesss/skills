# Thaumcraft Feature Checklist (TC4 + TC6)
Reference for gap analysis when building Thaumcraft-inspired mods.

## Core Systems

### Aspect / Essentia Registry
- [ ] 6 primal aspects: Aer, Aqua, Ignis, Terra, Ordo, Perditio
- [ ] 46+ compound aspects (2-primal, 3-primal, recursive)
- [ ] Data-driven aspect assignment to items (datapack extensible)
- [ ] Aspect decomposition (compound → primal components)
- [ ] Item scanning (thaumometer shows aspects)
- [ ] Entity scanning (mobs grant research points)

### Vis / Aura World System
- [ ] Per-chunk vis storage (AttachmentType on LevelChunk)
- [ ] Base aura from biome + Gaussian noise
- [ ] Vis regeneration (toward base, slowed at extremes)
- [ ] Neighbor equalization (vis flows high→low)
- [ ] Moon phase modulation
- [ ] Flux tracking per chunk
- [ ] Network sync (client packet on chunk load/update)
- [ ] Aura HUD overlay (goggles of revealing)

### Research System
- [ ] Research entries (categories, prerequisites, stages)
- [ ] Thaumonomicon book GUI
- [ ] Research minigame (rune-connecting or card-based)
- [ ] Research points (acquired by scanning, deconstruction table)
- [ ] Knowledge fragments (loot items)
- [ ] Per-player research state (AttachmentType on Player)
- [ ] Client-server sync for research progress

### Crafting Systems
- [ ] Crucible (melt items → essentia, craft by essentia minimums)
- [ ] Arcane Workbench (vis-powered crafting grid + wand slot)
- [ ] Infusion Altar (multiblock, pedestals, symmetry detection, instability)
- [ ] Essentia piping (tubes connect jars ↔ machines)
- [ ] Alembic (distills specific essentia from crucible)
- [ ] Centrifuge (breaks items into primary aspect)

### Wand System
- [ ] Wand cores (material affects capacity/regen)
- [ ] Wand caps (material affects efficiency)
- [ ] Vis storage on wand (data component)
- [ ] Focus system (registered castable effects)
- [ ] 7+ focus types: Fire, Excavation, Shock, Frost, PortableHole, Warding, EqualTrade
- [ ] Focal Manipulator (craft foci from crystals)

### Golem System
- [ ] 4 materials: Straw, Wood, Clay, Thaumium (affect speed/health/slots)
- [ ] Golem cores: Gather, Guard, Use, Fill, Empty, Butcher, Sort
- [ ] Golem seals (program cores)
- [ ] Golem Bell (command/recall golems)
- [ ] Golem upgrades: Air (speed), Fire (lava immune), Water (vis transfer), Order (complex tasks)
- [ ] Golemancer's Table (seal programming station)
- [ ] Custom renderer with material-dependent textures

### Flux / Taint System
- [ ] Flux accumulation from failed crafting, essentia spillage
- [ ] Flux events: FluxFlu (liquid), FluxRain (weather), FluxMiasma (gas)
- [ ] Taint biome (custom biome, block spread mechanics)
- [ ] Fibrous taint (converts natural blocks)
- [ ] Tainted creature variants
- [ ] Ethereal Bloom (cleansing flower)
- [ ] Pure nodes / silverwood trees (passive cleansing)

### Eldritch Endgame
- [ ] Warp mechanic (hidden stat, accumulates from forbidden knowledge)
- [ ] Warp effects: hallucinations, whispers, sun scorned, guardians, mind spiders
- [ ] Crimson Cult mobs (hostile to high-warp players)
- [ ] Eldritch dimension (void world, eternal night)
- [ ] Eldritch obelisks (structure generation)
- [ ] Eldritch Guardian boss
- [ ] Void metal + void tools/armor
- [ ] Primordial Pearl
- [ ] Staff of the Primal

## TC4 Bonus Features
- [ ] Vis Nodes (natural aura sources, 100-250 vis storage)
- [ ] Axe of the Stream (tree felling, aqua + instrumentum)
- [ ] Pickaxe of the Core (3x3 mining, instrumentum + terra)
- [ ] Sword of the Zephyr (sweeping attacks, aer + telum)
- [ ] Shovel of the Earthmover (3x3 digging, terra + motus)
- [ ] Boots of the Traveller (step assist + speed)
- [ ] Thaumostatic Harness (creative flight, aer vis)
- [ ] Magic Mirror (reflective teleportation)
- [ ] Arcane Lamp (large area lighting, lux vis)
- [ ] Hungry Chest (auto-vacuum items)
- [ ] Infernal Furnace (vis-powered smelter, 2x speed)
- [ ] Arcane Bore (3x3 tunnel digger)
- [ ] Mirror Magic (reflective teleportation network)
- [ ] Warded blocks (unbreakable)
- [ ] Infusion enchanting (apply vanilla enchants via aspects)

## Integration / Polish
- [ ] Config file (TOML, all multipliers configurable)
- [ ] JEI/REI plugin (show item aspects, recipes)
- [ ] Custom particles (vis streams, flux rifts)
- [ ] Custom sounds
- [ ] Magical Forest biome
- [ ] Data-driven extensibility (datapack recipes, aspects, research)
- [ ] Mod compatibility API (events for other mods to register aspects)
