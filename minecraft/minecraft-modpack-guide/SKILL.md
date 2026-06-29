---
name: minecraft-modpack-guide
category: minecraft
description: "Research and create comprehensive Minecraft modpack player guides. Deep multi-source research (YouTube, Reddit, wikis, Discord), structured mega-guides with standalone deep-dives for major mods. Trigger when the user asks for a modpack guide, tips, best mods, or a deep-dive on a specific mod within a pack."
---

# Minecraft Modpack Guide Authoring

Create comprehensive player guides for Minecraft modpacks (ATM10, ATM9, Enigmatica, etc.). Ruben expects multi-source, multi-round research covering progression AND QoL/building/decor/fun sections — progression-only guides will be called incomplete.

## Trigger Conditions

Load this skill when the user:
- Asks for a modpack guide, "ultimate guide", "best start", or "tips" for a specific pack
- Asks which mods in a pack "deserve a standalone guide"
- Asks for a deep-dive on a specific mod within a modpack context
- References an existing modpack guide and wants more detail

## Research Pipeline

### Phase 1: Source Gathering (4+ sources required)

Run parallel research via delegate_task across these source types:

1. **YouTube playthroughs** — Search for "pack name playthrough", "pack name tips", "pack name best". Prioritize: Pilpoh, John Hall, AlfredGG, ChosenArchitect, SystemCollapse, Direwolf20. Extract progression order, mod rankings, hidden tips.
2. **Reddit** — Search r/feedthebeast, r/allthemods, r/ModdedMinecraft. Extract community consensus, bug workarounds, underrated mods, TPS optimization tips.
3. **Written guides/wikis** — Search official pack wikis (GPORTAL, allthemods.com, alltheguides), SiriusMC, Minecraft-Guides wiki.
4. **Discord** — Check if the pack has an official Discord (e.g., discord.gg/allthemods) and note it as a source. Community Discord often has pinned tips not found elsewhere.

### Phase 2: Synthesis into Mega-Guide

Write a single comprehensive note (`inbox/<pack-name>-ultimate-guide.md`) with these sections as applicable:

1. Flight Methods (every option, ranked)
2. Early Game (hour-by-hour playbook, keybinds, first mods to rush)
3. Mob Farms (Apotheosis spawners, HNN, Industrial Foregoing, MGU)
4. Resource Farms (Mystical Agriculture, Productive Bees, quarries)
5. Power Generation (full progression table from first generator to endgame)
6. Storage Systems (progression from backpacks to AE2)
7. Magic Mods (Ars Nouveau, Iron's Spells, Occultism, EvilCraft, Apotheosis enchanting)
8. Automation & Logistics (transport, Modular Routers, pipes)
9. Mid to Late Game (ore processing, dimension access, Modern Industrialization pain points)
10. Endgame (ATM Star or pack-specific completion)
11. **Building Tools, Decor & QoL** — REQUIRED. Ruben called progression-only guides incomplete.
12. Community Wisdom (aggregated tips, bug workarounds, TPS optimization)
13. Quick-Reference Cheat Sheet (condensed playbook + power/armor/storage per stage)

### Phase 3: Identify Standalone Guide Candidates

After the mega-guide is written, analyze which mods appear most frequently across sections. Offer the user a ranked list:

- **S-tier** (5+ sections) — backbone mods. Always deserve standalone guides.
- **A-tier** (3-4 sections) — deep standalone systems.
- **B-tier** (2-3 sections) — focused utility. Borderline.

Include a "borderline" category for mods that are important but narrow (e.g., EvilCraft = Fortune V trick + broom flight). Let the user decide scope.

### Phase 4: Standalone Mod Guides (on user request)

When the user asks for standalone guides, create one note per mod in `inbox/`. Each guide follows this structure:

```markdown
---
tags: [minecraft, <pack-shorthand>, <mod-slug>, <category>, guide, reference]
created: YYYY-MM-DD
---

# <Mod Name> — <Pack> Standalone Guide

> **Pack:** <Pack Name> (Minecraft <version>, <loader>)
> **Sources:** <attribution>
> **Related:** [[Parent mega-guide]], [[Related standalone guide 1]], ...

## Why <Mod Name>
<!-- 2-3 sentences on why this mod matters in this pack -->

## 1. Section (progression-based)
<!-- Deep detail extracted from mega-guide, expanded for standalone use -->

## N. Quick Reference — Must-Craft List
| Item | Priority | Why |
```

### Standalone Guide Content Rules

- **Extract AND expand.** Don't just copy-paste the mega-guide's section. Add depth that wouldn't fit in the mega-guide.
- **Include comparison tables** where the mod competes with alternatives (e.g., MA vs Bees, AE2 vs RS, Powah vs Mekanism power).
- **Include a "Must-Craft" quick-reference table** at the end — players use this as a checklist.
- **Include TPS notes** for any mod that affects server performance.
- **Cross-link aggressively.** Every guide links back to the mega-guide and to sibling guides that share topic overlap.
- **Update the mega-guide's frontmatter** to include `**Standalone Guides:**` line with all child WikiLinks.

## Vault Placement

- Write ALL guides to `inbox/`. Never directly to `quick/`.
- Guide cluster linking (see notes-curation skill § "Guide cluster cross-linking pattern"):
  - Parent mega-guide frontmatter: `**Standalone Guides:** [[Guide 1]], [[Guide 2]], ...`
  - Child guides frontmatter: `**Related:** [[Parent]], [[Sibling with overlap]], ...`

## Research Quality Standards

- **Minimum 4 distinct sources** (YouTube, Reddit, wiki, Discord)
- **Prefer consensus** — if all sources agree on something (e.g., "Ore Hammer is #1 first craft"), state it as consensus
- **Flag disagreements** — if Reddit says one thing and YouTube another, present both
- **Cite specific creators** — "Pilpoh (Ep 49)", "John Hall (144K views)", "AlfredGG chapter: 'Ars Nouveau is OP'"
- **Note unconfirmed claims** — Apotheosis Potion Charms, Environmental Tech Beacons, etc. — mark them as "unconfirmed/absent in regular pack"

## Common Pitfalls

### Progression-only guides
Ruben called a progression-only pack guide incomplete. Every mega-guide MUST include §11 (Building Tools, Decor & QoL) with Building Gadgets, Construction Wands, Framed Blocks, Chisel/Chipped, Macaw's suite, Handcrafted, Supplementaries, JDT, Sophisticated Backpacks, FTB Chunks, Akashic Tome, Waystones, Mega Torch, trash cans, and other QoL mods. This section is non-negotiable.

### Single-source research
Delegate tasks can produce confident-sounding summaries from one source. Verify consensus across sources. If one delegate worker timed out (common with broad research), supplement with direct web searches rather than accepting incomplete results.

### Mega-guide as final destination
A mega-guide is a map, not the destination. The real value is in standalone deep-dives for the most important mods. Always offer to create them after the mega-guide is written.

### Missing cross-links
Standalone guides that don't link back to the mega-guide become orphaned. Update the mega-guide's frontmatter immediately after creating child guides.

### Fabricated facts in session-summarizer notes
The Session Summarizer cronjob may claim notes exist that don't (e.g., `[[All the Mods 10 (ATM10) — Ultimate Guide]]` linking to a note never created). When the user asks about content "from a guide," verify the actual vault contents. The ultimate guide might exist as `atm10-ultimate-guide.md` under a different H1 than the summarizer guessed.

## Related Skills

- **notes-curation** — frontmatter, WikiLinks, graduation criteria, vault structure
- **parallel-research** — delegate_task patterns for multi-source research
- **youtube-video-summary** — extract captions from YouTube playthroughs
