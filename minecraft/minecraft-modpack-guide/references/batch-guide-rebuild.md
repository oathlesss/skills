# Batch Guide Rebuild via Delegate Task

When the user asks to rebuild multiple failing guides, use this parallel delegate_task pattern. Proven at scale: 16 guides rebuilt in 6 waves (~45 min wall clock), all successful.

## Wave Planning

Group guides by priority and delegate them in waves of 3 (the parallel limit):

| Wave | Priority | Guides | Typical Size Target |
|---|---|---|---|
| 1 | Core tech/magic (12KB refs) | Mekanism, Apotheosis, Ars Nouveau | 50-77KB |
| 2 | Secondary systems (12KB refs) | Industrial Foregoing, Iron's Spells, Sophisticated Storage | 50-57KB |
| 3 | Infrastructure (8KB refs) | Powah, Extreme Reactors, HNN | 48-56KB |
| 4 | Magic + automation (8-16KB refs) | Occultism, EvilCraft, CC Tweaked | 36-72KB |
| 5 | Tools + endgame (8KB refs) | Just Dire Things, Silent Gear, Modern Industrialization | 39-60KB |
| 6 | Already passing | AE2, MA, Bees | Skip — no rebuild needed |

## Delegate Task Template

Each delegate gets this context structure — fill in the `<PLACEHOLDERS>` per guide:

```
You are rebuilding a Minecraft mod guide. ATM10 is All The Mods 10 (Minecraft 1.21.1, NeoForge, ~500 mods).

YOUR JOB: Rewrite the existing <MOD> reference sheet at `<PATH>` into a BUILD-ALONG MANUAL.

Read the existing guide FIRST — it has useful reference content to mine and restructure.
Also read `/path/to/mega-guide.md` for the <MOD> section and cross-reference context.
Also read `/path/to/ae2-standalone-guide.md` as a QUALITY TEMPLATE — that's the gold standard format you should match.

The vault uses [[WikiLinks]]. Frontmatter MUST have: tags: [minecraft, <pack>, <mod-slug>, <category>, guide, reference].
Frontmatter Related line links back to mega-guide and sibling guides.

NON-NEGOTIABLE REQUIREMENTS (all 7 must be met):
1. Stage-based progression — 3+ stages with time estimates
2. Shopping lists with EXACT quantities per stage — tables with Item | Qty | Notes
3. Block layout diagrams — ASCII art for key setups
4. Step-by-step build-along per stage — numbered, imperative, sequential instructions
5. Common Mistakes section — minimum 8 real community-reported mistakes, each with Problem → Why it's bad → Fix
6. Build This Now checklists — condensed per-stage checkbox lists
7. Pipe/Logistics comparison table — or explicit "not applicable" note if the mod has no pipes

RESEARCH REQUIREMENTS:
- Search YouTube for "<MOD> ATM10 guide", "<MOD> <pack> tips"
- Search Reddit r/allthemods and r/feedthebeast for "<MOD> tips", "<MOD> mistakes"
- Pull community consensus, flag contradictions with mod docs

<MOD>-specific topics to cover deeply:
- <LIST 5-8 key topics unique to this mod>

Write to the EXISTING file path (overwrite). Target <SIZE>KB.
```

## Key Parameters Per Guide Type

| Mod Type | Size Target | Pipe/Logistics req | Special Notes |
|---|---|---|---|
| Core tech (Mekanism) | 40-80KB | Full comparison table | Multiple multiblocks → need many diagrams |
| Magic (Ars, Iron's, Occultism) | 30-60KB | Usually "not pipe-focused" | Spell/glyph/ritual mechanics need deep explanation |
| Mob farm (Apotheosis, HNN) | 30-55KB | Comparison vs alternatives | Room layouts are critical |
| Power (Powah, Extreme Reactors) | 30-50KB | Cable/cable comparison | Tier tables are the backbone |
| Storage (Sophisticated, AE2) | 30-55KB | Transport comparison | Upgrade systems need careful documentation |
| Narrow utility (EvilCraft, JDT) | 20-40KB | "Not applicable" | Smaller scope — focus on most-used features |
| Programming (CC Tweaked) | 40-70KB | "Not pipe-focused" | Include working Lua code snippets |
| Greg-like (MI) | 40-60KB | Full pipe/voltage comparison | Resource requirements are massive — be specific |

## Pitfalls & Tips

### Pitfall: Delegates produce reference sheets anyway
If a delegate returns a guide that still reads like a wiki, the context was too vague. Be specific about "stage-based build-along" and "shopping lists with exact quantities." The phrase "someone without any modding experience should be able to walkthrough the entire mod" helps frame the target audience.

### Pitfall: web_extract fails with ddgs backend
All delegates using the ddgs backend will fail web_extract calls. They'll learn to rely on richer web_search snippets. This is expected — the key research data (Reddit threads, YouTube descriptions, wiki summaries) is visible in search snippets.

### Tip: Existing guides are gold mines
Even reference-sheet guides have useful content: tier tables, material lists, machine explanations. Tell delegates to "read the existing guide FIRST — mine it for reference content" — they'll build on existing work rather than starting from scratch.

### Tip: The AE2 guide is the quality template
Always point delegates to the 44KB AE2 guide as a format template. It has the exact structure (frontmatter → Why → Core Mechanics → Stages → Mistakes → Checklists → Quick Reference) that every other guide should follow.

## Throughput

| Metric | Value |
|---|---|
| Guides per wave | 3 |
| Time per wave | 350-470 seconds |
| Total for 16 guides (5 rebuild waves) | ~45 min wall clock |
| Delegates per session | 18 (6 waves × 3) |
| Success rate | 100% (18/18) |
| Final total size | ~896KB across 18 guides |
