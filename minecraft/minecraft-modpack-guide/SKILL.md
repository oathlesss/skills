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
> **Related:** [[Parent mega-guide]], [[Sibling with overlap]], ...

## Why <Mod Name>
<!-- 2-3 sentences on why this mod matters in this pack -->

## Core Mechanics Reference (if applicable)
<!-- Quick-reference table of key blocks/items/upgrades before the build-along -->

## Stage 1: Early Game — <Goal> (Hours X-Y)
### Shopping List (Exact Quantities)
| Item | Qty | Notes |
|---|---|---|

### Block Layout Diagram
<!-- ASCII art of the first setup -->

### Step-by-Step Build-Along
1. ...

## Stage 2: Mid Game — <Goal> (Hours X-Y)
<!-- Same structure: shopping list, layout, build-along -->

## Stage 3: End Game — <Goal> (Hours X+)
<!-- Same structure -->

## <Mod> vs. <Alternative>
<!-- Comparison table if the mod competes with another -->

## Pipe & Logistics (if automation mod)
<!-- Comparison table of transport systems with recommended progression -->

## Common Mistakes (From Community Help Threads)
<!-- Numbered list, minimum 8 entries. Problem → Why it's bad → Fix -->

## Quick Reference — Must-Craft List
| # | Item | Priority | Why |
|---|---|---|---|

## "Build This Now" — Stage Checklists
### Stage 1 (First Session)
- [ ] Item 1
- [ ] Item 2

### Stage 2 (After X)
- [ ] ...

## TPS Notes
```

### Standalone Guide Content Rules

- **Extract AND expand.** Don't just copy-paste the mega-guide's section. Add depth that wouldn't fit in the mega-guide.
- **Include comparison tables** where the mod competes with alternatives (e.g., MA vs Bees, AE2 vs RS, Powah vs Mekanism power).
- **Include a "Must-Craft" quick-reference table** at the end — players use this as a checklist.
- **Include TPS notes** for any mod that affects server performance.
- **Cross-link aggressively.** Every guide links back to the mega-guide and to sibling guides that share topic overlap.
- **Update the mega-guide's frontmatter** to include `**Standalone Guides:**` line with all child WikiLinks.

### Standalone Guide Format Requirements (NON-NEGOTIABLE)

Ruben called reference-style guides "very undetailed" and asked for "setup examples" with "tables to visualize." Every standalone guide for a major mod (S-tier and A-tier) MUST be a **build-along manual, not a reference exposition.** The player should be able to follow it step-by-step in-game.

**Required per guide:**

1. **Stage-based progression sections** — bucket content into time-tagged stages (e.g., "Stage 1: Early Game (Hours 0-5)", "Stage 2: Mid Game (Hours 5-20)", "Stage 3: End Game (Hours 20+)"). Each stage answers: what's the goal at this point, exactly what do I build, and what does success look like?

2. **Shopping lists with exact quantities** — every stage needs a table of items with specific quantities. Not "some Productivity Upgrades" — "4-16 Productivity Upgrades (Basic)." Not "a few hives" — "4 Advanced Hives." Players use these as literal checklists while crafting.

3. **Block layout diagrams** — use ASCII art for spatial setups (hive banks, farm layouts, checkerboard patterns, pipe routing). A text description of where blocks go is insufficient. Show the top-down or side-view layout.

4. **Step-by-step build-along** — numbered instructions within each stage that can be executed in sequence. "1. Find wild nests. 2. Craft 4 Advanced Hives. 3. Place Feeding Slabs..." — imperative, sequential, actionable.

5. **"Common Mistakes" section** — aggregate problems from community help threads (Reddit, Discord). Each mistake: what the player does wrong, why it's bad, and the exact fix. Minimum 8 entries for S-tier mods. Source from actual community reports, not speculation.

6. **"Build This Now" checklist** — stage-based checkbox lists at the end of the guide. Condensed version of the shopping lists so the player can scan "what do I need right now" without re-reading sections.

7. **Pipe/Logistics comparison table** (for mods with automation) — compare at least 3 transport systems (Pipez, LaserIO, XNet, SFM, Modular Routers, AE2) with pros/cons and a recommended progression order.

**Format priority:** tables > ASCII diagrams > prose. If information can be conveyed in a table or diagram, prefer that over paragraphs. Prose is for the "why" — tables and diagrams are for the "what" and "how."

The template in Phase 4 reflects this structure. A guide that hits all 7 requirements will typically be 20-25KB for an S-tier mod; if yours is under 10KB, it's probably a reference sheet, not a build-along guide.

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

### Reference-style standalone guides (Ruben's #1 complaint)
Ruben called standalone guides "very undetailed" when they explain what things do without showing what to build. A standalone guide that reads like a wiki page (here's what each block does, here are the tiers, here are the recipes) is a FAILED guide. The player already has JEI for recipes — they need **stage-based build-along with tables, quantities, layouts, and checklists.** See "Standalone Guide Format Requirements" above. A guide under 10KB for an S-tier mod is almost certainly a reference sheet, not a build-along manual.

### Community consensus contradicting mod documentation
The community often converges on strategies that contradict the mod's "obvious" progression. Examples: skip MA Growth Accelerators (exponentially expensive) and use AE2 Growth Accelerators instead; use Red Fertilizer over Essence Farmland (secondary seed drops ≠ growth speed); the Harvester Pylon covers 9×9 not 15×15 (that's the MA Harvester machine with Awakened Supremium). Always cross-check official mod docs against community practice. Flag these contradictions explicitly — "community consensus: do X even though the mod pushes Y." The player who follows the mod's intended path without checking Reddit will waste hours.

## Guide Auditing

When the user asks to review/audit existing guides for quality, use the systematic procedure in `references/audit-checklist.md`. The workflow is:

1. **File-size triage** — sort guides by size; under 10KB is a red flag for reference sheets
2. **Grep requirement scan** — check all 7 non-negotiable requirements via grep patterns
3. **Spot-read passed candidates** — verify content quality, not just header presence
4. **Duplicate detection** — multiple files covering the same mod with different filenames
5. **Tiered report** — pass table (with requirement columns) + fail table (with problem column)

Always offer to rebuild failing guides after the audit. The user may want all rebuilt, only the high-priority ones, or just the audit report.

## Related Skills

- **notes-curation** — frontmatter, WikiLinks, graduation criteria, vault structure
- **parallel-research** — delegate_task patterns for multi-source research
- **youtube-video-summary** — extract captions from YouTube playthroughs

## Mega-Guide Update After Rebuilds

After rebuilding standalone guides with fresh community research, the mega-guide's corresponding sections are often **factually stale.** The standalone guides found updated values that the mega-guide's older summaries don't reflect. Always follow a rebuild wave with a mega-guide update pass:

1. **Cross-check factual claims** — read the rebuilt standalone guide's core values (e.g., spawner entity caps, pylon ranges, growth accelerator consensus) and verify the mega-guide section matches. Common drift points: ATM10 rebalanced values, community consensus that shifted since the mega-guide was written, mod version changes.
2. **Add Deep Dive pointers** — insert `> 💡 **Deep Dive:** [[Guide Name]] (XXKB — key topics)` blocks at each section header that has a corresponding standalone guide. This makes the mega-guide a navigation hub: overview here, build-along there.
3. **Update the `updated` date** in mega-guide frontmatter.

Example of a Deep Dive pointer:
```markdown
## 3. Best Mob Farms

> 💡 **Deep Dive:** [[Apotheosis — ATM10 Standalone Guide]] (51KB build-along — spawners, enchanting library, gems, world tiers), [[Hostile Neural Networks — ATM10 Standalone Guide]] (53KB — data models, simulation chambers, automation)
```

### Pitfall: Mega-guide factual drift after standalone rebuilds
The mega-guide's summary sections were written when standalone guides were reference sheets. After rebuilding those guides with fresh YouTube/Reddit research, the mega-guide's older claims are likely wrong. Examples from ATM10: the mega-guide said spawner entity cap was 64 (standalone found 32 in ATM10), Prismarine Crystals for No AI (standalone found Chorus Fruit + Golden Apple), and 15×15 Harvester Pylon range (standalone found 9×9). Always re-sync the mega-guide after rebuilds — don't assume the old summaries are still accurate.

## Reference Files

- `references/audit-checklist.md` — systematic grep-driven audit procedure for scoring guides against the 7 format requirements. Use when the user asks "are these guides detailed enough?" Includes greppable scoring, spot-read verification steps, duplicate detection, and common audit finding patterns.
- `references/batch-guide-rebuild.md` — proven delegate_task wave pattern for rebuilding multiple failing guides in parallel. Covers wave planning, delegate context template, size targets per mod type, and throughput benchmarks.
