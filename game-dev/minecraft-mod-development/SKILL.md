---
name: minecraft-mod-development
description: Minecraft mod development on NeoForge 1.21.x — project setup, architecture patterns, datapack design, procedural art pipeline, and phased development strategy.
triggers:
  - Minecraft mod
  - NeoForge mod
  - Thaumcraft remake
  - Minecraft mod architecture
  - Minecraft mod planning
  - Minecraft datapack
  - Forge mod
---

# Minecraft Mod Development

Use this skill when the user asks about Minecraft mod development, architecture, planning, or execution — specifically for modern NeoForge 1.21.x content mods.

## Platform decision

**NeoForge 1.21.x is the default.** Reasons:

- Mature APIs for large content mods (attachments, registries, datapacks, datagen)
- Built-in systems: `AttachmentType` for world/player state, `DataComponentType` for item data, `datamap` for item→data mappings, `NetworkChannel` for sync
- Largest ecosystem for magic/content mods (Ars Nouveau, Botania, Blood Magic)
- **Do not default to multi-loader** (Architectury). Single-loader is simpler. Port to Fabric later if there's traction.

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
