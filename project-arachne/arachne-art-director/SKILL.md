---
name: arachne-art-director
description: >-
  Generates SDXL/ComfyUI art prompts for Project Arachne assets — characters,
  weapons, backgrounds, VFX, and card icons. Uses the project's established
  pixel-art style guide, 32-color palette, and negative prompt conventions.
  Acts as the "Art Agent" in the Arachne multi-agent pipeline.
license: MIT
---

# Arachne Art Director

Meta-prompt for generating production-quality SDXL prompts for Project
Arachne's pixel-art brawler game. Load this skill when you need to generate
art prompts for ComfyUI/SDXL, batch concept exploration, or critique existing
generated assets against the style guide.

## Context & Constraints

Project Arachne uses a strict pixel-art style:
- **Palette:** 32-color flat palette, no gradients, distinct silhouettes
- **Style:** Pixel art, game sprite, flat shading, clean lines, game asset
- **Background:** Always white for sprites (transparent post-processed)
- **Sizes:** Characters 64×64, weapons 128×128, card icons 256×256, backgrounds 1920×1080
- **Theme:** Web/mechanical only — grappling harness, web-swinging gear, silk weapons.
  NO spider bodies, NO insect bodies, NO arachnid anatomy, NO eight legs.
  Characters are humanoid with mechanical web-themed equipment.
- **Mood:** Cute but fierce, dark atmospheric for arenas

Reference templates live at:
`/home/ruben/project-arachne/tools/prompts/arachne_prompts.txt`

## When to Load This Skill

- User asks for art prompts, character concepts, weapon designs, arena backgrounds
- User wants to batch-generate variants ("generate 20 character concepts")
- Orchestrator decomposes a design request and needs Art Agent output
- Reviewing AI-generated art against the Arachne style guide
- Building or updating the prompt engine's art templates

## Step 1: Determine Asset Type

Identify which asset category is needed:

| Asset Type | Size | Batch Size | Negative Emphasis |
|---|---|---|---|
| CHARACTER_CONCEPT | 64×64 | 20 variants | No spider/insect anatomy |
| CHARACTER_POSE | 64×64 | Use IP-Adapter+ControlNet | Consistent with reference |
| WEAPON | 128×128 | 15 variants | Keep weapon-focused |
| CARD_ICON | 256×256 | 5 per batch | No text, geometric |
| ARENA_BACKGROUND | 1920×1080 | 5 variants | Parallax-ready |
| PARTICLE/VFX | 32×32 or 64×64 | 10 variants | Transparent bg |

## Step 2: Build the Positive Prompt

Follow this structure for all Arachne art prompts:

```
[STYLE] + [SUBJECT] + [DETAILS] + [QUALIFIERS] + [FORMAT]

Style:   pixel art brawler character, game sprite
Subject: [ARCHETYPE], [BODY_SHAPE] body, [COLOR_SCHEME]
Details: [EQUIPMENT], web-swinging gear or grappling harness, [ACCESSORY]
Qualifiers: cute but fierce, distinct silhouette, flat shading, no gradients, clean lines
Format:   32-color palette, white background, [SIZE] sprite size, game asset, production ready
```

### Character Archetypes (supported by style guide)
- masked duelist / tiny robot / cloak-wearing acrobat / slime fighter / armored bug-like knight (without insect anatomy)

### Body Shapes
- small / medium / large / tall

### Color Schemes (examples)
- cyan with dark gray accents / crimson with gold / void purple with silver / ember orange with black

### Weapons (Arachne-specific)
- Grapple Whip (coiled energy whip with crackling end)
- Momentum Hammer (massive stone hammer with impact cracks)
- Silk Scythe (curved blade leaving sticky trail)
- Web Gauntlets (armored gauntlets shooting web strands)

## Step 3: Attach the Universal Negative Prompt

ALWAYS append this exact negative prompt to every generation:

```
blurry, anti-aliased, smooth gradient, realistic, 3D render, photo, text,
watermark, signature, logo, extra limbs, malformed limbs, inconsistent anatomy,
cluttered background, spider body, spider character, arachnid, insect body,
eight legs, copyrighted character, mario, sonic, pokemon, disney, marvel, nintendo
```

## Step 4: Batch Exploration Strategy

For concept generation, produce 20 prompts with controlled variation:

1. **Archetype variation** (5 prompts): Same base, rotate through 5 archetypes
2. **Color variation** (5 prompts): Same archetype, 5 color schemes
3. **Accessory variation** (5 prompts): Same base, 5 accessories (none, hat, crown, horns, scarf)
4. **Wildcard variation** (5 prompts): Cross-product of unused archetypes + colors

Output format: Numbered list with archetype/color/accessory metadata so the
human can log selections to `tools/templates/asset_provenance.csv`.

## Step 5: Pose Generation (requires reference)

When generating poses, note that this requires IP-Adapter + ControlNet
with the approved character concept as reference. The prompt must include:

```
same character as reference, consistent colors, consistent proportions,
[POSE: idle/run_frame_1/jump_up/attack_swing/death],
[ACTION_CONTEXT: standing still / running right / launching upward /
 swinging weapon / falling]
```

## Pitfalls

### Spider/insect bleed-through
SDXL knows "web" → spider association. Without explicit negatives,
characters will grow extra limbs or insect features. Always include
the full negative prompt, especially `spider body, insect body, eight legs`.

### Gradient creep
"Pixel art" alone isn't enough. SDXL defaults to smooth anti-aliased
rendering. Always include `flat shading, no gradients, clean lines, no anti-aliased`
in positives AND `anti-aliased, smooth gradient` in negatives.

### Size inconsistency
If you omit `[SIZE] sprite size`, SDXL produces inconsistent scales.
Always specify pixel dimensions.

### Color palette drift
Without `32-color palette`, SDXL uses millions of colors. The resulting
art can't be palette-swapped in engine.

### Background bleed
SDXL loves detailed backgrounds. `White background` must appear in
positives AND `cluttered background` in negatives.

### Copyrighted character leakage
Without explicit negatives, SDXL may pull from training data and
produce Mario/Sonic/Pokémon-like characters. Always include the
copyrighted character block in negatives.

## Verification

After generating prompts, check:
- [ ] Positive prompt follows the [STYLE]+[SUBJECT]+[DETAILS]+[QUALIFIERS]+[FORMAT] structure
- [ ] Universal negative prompt is appended in full
- [ ] Size spec is explicit (64×64, 128×128, etc.)
- [ ] No spider/insect anatomy in positives
- [ ] Spider/insect/copyrighted negatives are present
- [ ] 32-color palette constraint is in positives
- [ ] White background is in positives
- [ ] Flat shading / no gradients are in positives
- [ ] Each prompt variant has archetype/color/accessory metadata for logging

## References

- `references/arachne_prompts.txt` — Current prompt templates (symlink to project)
- `/home/ruben/project-arachne/research/meta-prompting-game-development.md` — Full research doc
- `/home/ruben/project-arachne/research/ai-art-pipeline.md` — Art pipeline research
- `/home/ruben/project-arachne/tools/templates/asset_provenance.csv` — Asset tracking log
