# Thaumcraft Recreation Plan for Modern Minecraft (1.21.x+)

Full 9-phase development plan for recreating Thaumcraft as a NeoForge 1.21.x mod.
Original plan written 2026-06-20. See `/home/ruben/thaumcraft-remake-plan.md` for live copy.

## Technical Foundation

- **Platform**: NeoForge 1.21.x (single-loader, no Architectury)
- **Build**: Gradle + ModDevGradle, Mixin for hooks, Datagen from day one
- **Key APIs**: AttachmentType, DataComponentType, datamap, NetworkChannel, BlockEntity/BER

## Architecture

- Package split: `lib/` (API surface) + `core/` (implementation)
- Data-driven: all aspects, recipes, research, foci via JSON datapacks
- Communication: NeoForge events + attachments + direct API calls

## Core Systems (dependency order)

1. **Aspect/Essentia Registry** — ~52 aspects, primal + compound, ITEM_ASPECTS datamap
2. **Vis/Aura World System** — per-chunk vis pools, regen, silverwood boost, Thaumometer overlay
3. **Research System** — Thaumonomicon knowledge graph, hex-grid rune-connecting minigame (3 tiers), scanning
4. **Crafting Systems**: Crucible (item→essentia, loose recipe matching), Arcane Workbench (vis-cost crafting), Infusion Altar (multiblock, symmetry detection, instability)
5. **Wand System** — cores + caps, vis storage, focus registry (Fire, Excavation, Shock, Equal Trade, etc.)
6. **Golem System** — material body + behavior core + upgrades, pathfinding, 6 core types
7. **Flux/Taint** — flux thresholds, events (flu/rain/miasma), taint biome spread, cleansing
8. **Eldritch Endgame** — warp mechanic, eldritch dimension, guardian bosses, void metal/primordial pearl

## Implementation Phases

| Phase | Content | Timeline |
|-------|---------|----------|
| 0 | Scaffolding: mod loads, placeholder block+item, CI | Week 1–2 |
| 1 | Aspect system + basic materials (ingots, crystals, shards) | Week 3–6 |
| 2 | Vis/aura world system + Silverwood/Greatwood trees | Week 7–10 |
| 3 | Research system + Thaumonomicon (~30 entries) | Week 11–16 |
| 4 | Crafting systems: Crucible → Arcane Workbench → Infusion Altar | Week 17–24 |
| 5 | Wand + focus system (8 initial foci) | Week 25–27 |
| 6 | Golem system (6 core behaviors) | Week 28–32 |
| 7 | Flux/Taint (biome spread, cleansing) | Week 33–36 |
| 8 | Eldritch endgame (warp, dimension, bosses) | Week 37–41 |
| 9 | Polish, balance, JEI integration, mod compat API | Week 42+ |

## Art Pipeline Strategy

- **Procedural generation (Pillow)** for geometric textures: ingots, crystals, shards, dusts, pattern blocks (~140 textures)
- **Manual pixel art (Aseprite)** for character textures: crafting stations, entities, organic blocks (~70 textures)
- **AI (ComfyUI/SDXL)** for concept art and mood boards only — not production textures

## Performance Strategy

- Chunk aura: only update within simulation distance, dirty-chunk sync
- Golem pathfinding: cap per player, only when tasked
- Taint spread: rate-limited globally, use vanilla random ticks
- Aspect lookup: HashMap cache, O(1)

## Key Risks

- Scope creep → strict phase gates
- Burnout → playable at every milestone
- Aspect data entry (800+ items) → batch by category + algorithmic fallback
- Infusion altar complexity → prototype early as standalone PoC
- Taint spread performance → rate-limit aggressively

## Mods to Study

Ars Nouveau (spell casting), Hex Casting (stack programming), Botania (in-world crafting), Blood Magic (altar multiblock), Create (UX polish).
