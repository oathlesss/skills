---
name: arachne-design-decomposer
description: >-
  Decomposes high-level game design requests into structured, executable specs
  for Project Arachne — mechanics, art assets, code components, and test cases.
  Acts as the "Orchestrator Agent" in the Arachne multi-agent pipeline.
license: MIT
---

# Arachne Design Decomposer

Meta-prompt for the Orchestrator Agent: takes a natural-language game
design request and decomposes it into structured tasks that can be
delegated to specialist agents (Art Director, Code Agent, QA Agent).

Load this skill FIRST in any `delegate_task` orchestration — it provides
the decomposition framework that the subagents need.

## Context

Project Arachne: 2D pixel-art platformer brawler in Godot 4.6.3.
- **Theme:** Mechanical web/grappling equipment. No spiders, no insects.
- **Physics:** Screen-space gravity/jump, wall/ceiling sticking via `floor_max_angle=PI`
- **Art:** 32-color pixel art, SDXL via ComfyUI
- **Code:** Typed GDScript 2.0, CharacterBody2D
- **Ponytail:** Simplest solution wins

## When to Load This Skill

- User provides a high-level design request ("I need a lava-pit arena boss")
- Orchestrator Agent in the `delegate_task` pipeline
- Breaking down feature requests into sprint-ready task cards
- Generating the initial `.md` design spec for a new feature
- Planning what art assets + code components a mechanic needs

## Step 1: Parse the Design Request

Extract these dimensions from the user's request:

| Dimension | Questions to Answer |
|---|---|
| **Scope** | Is this a single asset, a mechanic, a level, or a system? |
| **Theme** | Does it fit the mechanical-web aesthetic? Reframe if not. |
| **Mechanics** | What does the player DO? (fight, traverse, collect, solve) |
| **Feel** | Speed/heaviness/floatiness? Screen shake? Particle feedback? |
| **Dependencies** | What existing systems does this touch? |
| **Constraints** | NES palette? Specific arena size? Must work with existing tests? |

## Step 2: Decompose into Task Categories

Map the design request to these output categories. NOT every request
needs all categories — only include what's relevant.

### A. Art Assets (→ arachne-art-director)

| Asset Type | When Needed |
|---|---|
| Character concept | New enemy, NPC, or player variant |
| Character poses | New character needs animation frames |
| Weapon sprite | New weapon type |
| Card icon | New ability/move card |
| Arena background | New level or arena |
| Particle/VFX texture | New visual effect (hit spark, death poof, etc.) |
| UI element | Health bar, card frame, menu element |

### B. Code Components (→ arachne-code-reviewer)

| Component Type | When Needed |
|---|---|
| New CharacterBody2D class | New enemy type, boss, NPC |
| Existing class extension | Adding mechanic to player/enemy |
| New autoload/singleton | Global system (combat manager, arena controller) |
| UI scene + script | New HUD, menu, card selection screen |
| Test update | New component needs tests |
| Signal wiring | Connecting new mechanic to existing systems |

### C. Design Specs (→ written to project-arachne/design/)

| Spec Type | Output |
|---|---|
| Mechanic spec | Detailed gameplay description, inputs, feedback |
| Balance spreadsheet | Stat ranges, damage values, cooldowns |
| Level layout | Arena dimensions, platform positions, hazards |
| Card/ability design | Move properties, synergies, counters |
| Progression curve | Unlock order, difficulty ramp |

### D. VFX/Audio Notes

| Type | Details |
|---|---|
| Screen shake | Intensity + duration per event |
| Particles | Spawn conditions, color, lifespan |
| Hitstop/freeze | Frames to freeze on impact |
| Audio cues | SFX triggers (attack, hit, death, ambient) |

## Step 3: Generate the Structured Output

Produce a markdown document with this structure:

```markdown
# [Feature Name] — Design Spec

**Scope:** [one-line summary]
**Dependencies:** [list of existing systems this touches]
**Theme check:** [confirms mechanical-web aesthetic, reframes if needed]

## Mechanics
### [Mechanic 1]
- **Input:** [what player does]
- **Response:** [what happens]
- **Feel:** [speed, weight, feedback]
- **Edge cases:** [unusual interactions to handle]

## Art Assets Needed
| Asset | Type | Quantity | Prompt Variables |
|---|---|---|---|
| [name] | [CHARACTER_CONCEPT/WEAPON/...] | [N variants] | archetype=[X], color=[Y] |

## Code Components Needed
| Component | Type | Extends | Key Methods |
|---|---|---|---|
| [name] | [new class/extension] | [parent] | [method signatures] |

## Test Cases
| Test | What It Verifies |
|---|---|
| [description] | [expected behavior] |

## VFX/Audio
- [screen shake / particles / hitstop / SFX notes]
```

## Step 4: Generate Delegation Plan

From the structured spec, produce the `delegate_task` plan:

```python
# Pseudocode for the orchestration
tasks = []

# Art Agent (if art assets needed)
if art_assets:
    tasks.append({
        "goal": "Generate SDXL art prompts for [asset list]",
        "context": "[spec excerpt with archetypes, colors, sizes]",
        "toolsets": ["terminal", "file"],
        "skills": ["arachne-art-director"]
    })

# Code Agent (if code components needed)
if code_components:
    tasks.append({
        "goal": "Generate GDScript for [component list]",
        "context": "[spec excerpt with mechanics, edge cases]",
        "toolsets": ["terminal", "file"],
        "skills": ["godot-player-controller", "arachne-code-reviewer"]
    })

# Design Agent (always, generates the spec doc)
tasks.append({
    "goal": "Write the design spec markdown for [feature]",
    "context": "[full decomposition]",
    "toolsets": ["file"],
    "skills": ["arachne-design-decomposer"]
})
```

## Step 5: Arachne-Theme Compliance Check

Before finalizing any decomposition, verify theme alignment:

- [ ] Does the mechanic use web/swing/grapple/tether mechanics? (not spider webs — mechanical webs)
- [ ] Is the visual theme mechanical, not organic? (gears, harnesses, silk strands, not spider bodies)
- [ ] Are enemy types humanoid with equipment, not creatures? (masked duelists, tiny robots, armored knights with web gear)
- [ ] Does the arena use industrial/cavern/mechanical aesthetics? (not organic web nests)
- [ ] Do weapon names use mechanical terminology? (Grapple Whip, Silk Scythe, Web Gauntlets — mechanical, not biological)

If any check fails, reframe the concept before delegating.

## Pitfalls

### Over-decomposing
Not every feature needs 4 agents. A "new card icon" request needs only
the Art Agent. A "jump feels floaty" request needs only the Code Agent.
Resist the urge to spawn agents for completeness — spawn only what the
request actually needs.

### Delegating without context
Subagents have NO memory of the conversation. Every `delegate_task`
must include the full style guide, physics rules, and theme constraints
in the `context` field. A subagent that doesn't know about the 32-color
palette will generate unusable art prompts.

### Theme drift in decomposition
When decomposing, it's easy to introduce spider/insect concepts because
"web" → "spider" is the cultural default. Every decomposition output
must pass the theme compliance check in Step 5.

### Skipping the spec document
The design spec `.md` is the source of truth that ties art + code + tests
together. Without it, generated assets drift apart. Always produce the
spec first, then delegate from it.

### Delegating without specifying output location
Subagents don't know the project structure. Always include the exact
file paths where output should be written (e.g., `characters/enemies/`,
`tools/prompts/generated/`, `design/specs/`).

## Verification

After decomposition:
- [ ] All 5 theme compliance checks pass
- [ ] No unnecessary agents spawned (only what the request needs)
- [ ] Each subagent's `context` is self-contained (style guide, physics, theme)
- [ ] Spec document has all relevant sections (Mechanics, Art, Code, Tests, VFX)
- [ ] File paths are explicit in delegation context
- [ ] Edge cases are listed for each mechanic
- [ ] Dependencies on existing systems are documented

## References

- `references/pipeline-pattern.md` — Live example: full pipeline execution (lava-pit boss, 2026-06-18)
- `arachne-art-director` skill — Art Agent meta-prompt
- `arachne-code-reviewer` skill — Code/QA Agent meta-prompt
- `godot-gamedev` skill — Physics conventions
- `ponytail-review` skill — Simplicity enforcement
- `/home/ruben/project-arachne/research/meta-prompting-game-development.md` — Full research doc, Section 6 (Agent Decomposition Architecture)
- `/home/ruben/project-arachne/tools/prompts/arachne_prompts.txt` — Current prompt templates
