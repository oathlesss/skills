---
name: llm-game-generation
description: >-
  Build an LLM-driven pipeline that turns natural-language prompts into playable
  games. Covers feasibility (one-shot vs. agentic loop), the three approaches
  (neural world models, no-code platforms, agentic engine pipelines), the staged
  build-test-inspect-revise architecture, model selection (incl. GLM 5.3), and
  concrete tooling (godogen, GodotPrompter, godot-mcp, OpenGame). Use whenever
  the user asks about one-shot/AI/LLM game generation or agentic game dev.
triggers:
  - one-shot prompt to game
  - build a game with AI / LLM
  - agentic game development pipeline
  - LLM game generation
  - can an LLM build a game
  - text-to-game
---

# LLM Game Generation Pipeline

## Honest verdict (state of the art, 2026)

**True "one prompt → finished shippable game" does NOT exist.** What exists:

| Goal | Feasible? | How |
|------|-----------|-----|
| One prompt → small playable prototype | ✅ | Frontier coding model + agentic scaffold |
| One prompt → polished shippable indie game | ❌ | Needs human design + playtesting + iteration |
| One prompt → playable *environment* (no logic) | ✅ research-grade | Neural world models (Genie 2/3, Oasis) |

Root cause (IEEE Spectrum / Togelius): **the LLM can't play the game, so it can't judge fun.** Game dev is iterative; LLMs collapse on cross-file inconsistencies and broken scene wiring when asked for a full game at once.

Framing to lead with: **"one-shot gets you a playable core; agentic iteration gets you to done."** Never promise a finished game from one prompt.

## Three approaches

1. **Neural world models** (Genie 2/3, GameNGen, Oasis, DIAMOND, MineWorld) — prompt → playable real-time *environment*. No game logic/UI/design, hallucinated physics, not editable/shippable. Track, don't build on.
2. **No-code text-to-game platforms** (Rosebud AI, MakeGamesWithAI, Summer Engine) — genuinely one-shot for tiny browser games, but hard quality ceiling, platform lock-in, no Godot, weak path to shipping.
3. **Agentic pipeline in a real engine** — THE path for a real game. godogen, GodotPrompter, godot-ai-builder, satelliteoflove/godot-mcp, OpenGame.

## The staged architecture (what actually works)

Never ask for "the whole game" in one mega-prompt. Stage it:

```
ONE PROMPT
  → [1] Design doc + scope + asset list (JSON)
  → [2] Scaffold (project.godot, scenes, input map, ColorRect placeholders)
  → [3] Mechanics — one prompt PER mechanic (Summer Engine's advice)
  → [4] Assets (Pillow procedural / SDXL-ComfyUI / Meshy-Tripo3D for 3D)
  → [5] godot --headless run → screenshot
  → [6] VLM critiques screenshot against intent → agent revises → LOOP
```

The loop at [5]–[6] is what matters most — it substitutes screenshot→VLM critique for the playtesting the LLM can't do. Key OpenGame finding: *the bottleneck is the agent workflow architecture, not prompt size or model capacity.* Pipeline design > model choice.

## Model selection

See `references/model-selection.md` for the full table + GLM 5.3 detail.

Rule of thumb: **hybrid beats one expensive model.** Frontier coding model (Claude Opus/Sonnet, or GLM 5.3) as the "brain" + a cheap model for bulk tasks + a vision model for the screenshot-critique stage.

⚠️ GLM 5.3 (full) is code/agentic-only, NOT multimodal — pair with GLM 5.3 Flash for the vision stage.

## Tooling (Godot-focused, matches Ruben's setup)

| Tool | What it does |
|------|--------------|
| godogen (htdt/godogen) | Scaffolding layer → Claude Code/Codex autonomously plans, codes, generates assets (Gemini/Grok/Tripo3D), runs engine headlessly, iterates on screenshots. Godot/Bevy/Babylon.js |
| GodotPrompter (jame581) | Agentic skills framework for Godot 4.x (GDScript/C#), Superpowers-based |
| godot-ai-builder (HubDev-AI) | Claude Code plugin → playable Godot 4 games from NL prompts |
| satelliteoflove/godot-mcp | Godot MCP (already wired in Hermes/Arachne): scene editing, input injection, deterministic playtesting, live state |
| OpenGame (arXiv 2604.18394) | Agentic web-game framework + OpenGame-Bench (Build Health / Visual Usability / Intent Alignment) |

## Roadmap (proven order)

1. Prove the loop on a tiny game (one mechanic) — one prompt → playable + screenshotted + critiqued in one session.
2. Harden: add OpenGame-style scoring, asset stage, pre-commit build+test hook (already standard in Arachne).
3. Scale scope — keep "one prompt per mechanic" discipline.
4. Human stays in the loop for fun/design decisions.

## References
- `references/model-selection.md` — model comparison table, GLM 5.3 facts, Hermes wiring (zai/openrouter providers + model IDs)
