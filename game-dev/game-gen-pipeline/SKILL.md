---
name: game-gen-pipeline
description: >
  Turn a one-shot natural-language prompt into a small playable Godot 4 game
  via a tiered-LLM pipeline: GLM 5.3 designs + reviews, GLM 5.3 Flash critiques
  screenshots, and the orchestrating agent scaffolds, runs headless verification,
  and iterates. Implements the Yegge design→implement→review loop and the OpenGame
  six-stage workflow at single-developer scale.
triggers:
  - one-shot game generation
  - "build me a game"
  - "make a playable prototype from this prompt"
  - generate a Godot game from a description
  - game dev pipeline
  - turn this idea into a game
---

# Game Gen Pipeline

One-shot prompt → small playable Godot 4 game. This is the *agentic loop*, not a
mega-prompt: a frontier model designs and reviews, a cheaper model/agent implements,
and a vision model judges the result. (Steve Yegge's core insight, applied at
single-dev scale — you don't need his 40-agent fleet.)

## Model tiers (fixed — do not change the Hermes default)

| Role | Model | Why |
|------|-------|-----|
| Design + review (brain) | `z-ai/glm-5.3` | strong agentic coding, ~$4.40/M |
| Screenshot critique (eyes) | `z-ai/glm-5.3-flash` | multimodal (GLM 5.3 itself is text-only) |
| Orchestration (Hermes) | deepseek-v4-pro | cheap tokens, default model |

All LLM calls go through `scripts/llm.py` → OpenRouter (key auto-read from
`~/.hermes/.env`). **Never** flip the Hermes default model for this.

## The staged workflow

```
ONE-SHOT PROMPT
  → [1] DESIGN      GLM 5.3 → design.md + beads.json (title, mechanics, MVP bead list)
  → [2] SCAFFOLD    scripts/scaffold.py → project.godot + scenes/main.tscn + stub
  → [3] IMPLEMENT   GLM 5.3 → full scripts/main.gd (per bead, one at a time)
  → [4] REVIEW      orchestrator reads the generated code and patches the known
                    GLM codegen bug classes before running (see Pitfalls below)
  → [5] VERIFY      godot --headless --quit   (must exit 0, no script errors)
  → [6] SCREENSHOT  scripts/capture.py → PNG (REQUIRES xvfb)
  → [7] CRITIQUE    GLM 5.3 Flash sees PNG → issues list → feed back to [3]
```

Loop [3]–[7] until the headless build is clean and the screenshot matches intent.
Step [4] is the real correctness work — GLM's first-shot code is plausible but
wrong on physics; never let VERIFY be your only review.

## Commands

```bash
S=~/.hermes/skills/game-dev/game-gen-pipeline/scripts

# 1. Design (one-shot prompt → design doc + beads)
$S/llm.py chat z-ai/glm-5.3 "$DESIGN_SYSTEM" "$PROMPT" --max-tokens 3000

# 2. Scaffold
python3 $S/scaffold.py ~/mygame "My Game"

# 3. Implement (per bead — pass the bead + conventions, GLM writes main.gd)
$S/llm.py chat z-ai/glm-5.3 "$IMPL_SYSTEM" "$BEAD_PROMPT" --max-tokens 8000 --strip-fences > ~/mygame/scripts/main.gd

# 4. Verify (must exit 0)
~/.local/bin/godot --path ~/mygame --headless --quit 2>&1 | tail -20

# 5. Screenshot (needs xvfb: sudo apt install -y xvfb)
python3 $S/capture.py ~/mygame /tmp/shot.png 90

# 6. Critique
$S/llm.py vision z-ai/glm-5.3-flash /tmp/shot.png "$CRITIQUE_PROMPT"
```

## Prompt templates

**Design system prompt:**
```
You are a senior Godot 4 game designer and GDScript expert. Given a one-line game
idea, produce a design doc. Output JSON only with keys:
  title, description, mechanics (array of strings),
  beads (array of small implementation units, each a concrete single feature),
  implementation_notes (array of strings).
Keep MVP scope tiny (3-6 beads). Use ColorRect placeholder art, no external assets.
```

**Implement system prompt:**
```
You are a Godot 4 GDScript expert. Write COMPLETE, RUNNING code. Conventions:
- The scene is built programmatically in _ready() in scripts/main.gd (extends Node2D).
- Input via Input.is_key_pressed(KEY_A/KEY_D/KEY_W/KEY_S/KEY_LEFT/KEY_RIGHT/KEY_UP/KEY_DOWN/KEY_SPACE).
- World art via Polygon2D nodes (NEVER ColorRect — it's a Control and renders in screen space, not the camera world). UI text via Label under a CanvasLayer. No external sprites. No @export. No class_name.
- Use typed GDScript. Output ONLY the GDScript, no markdown fences.
```

**Critique prompt:**
```
This is a screenshot of a game with intent: {INTENT}. List concrete problems
(visual, layout, readability, missing elements) as a numbered list, then 3
highest-priority fixes.
```

## Pitfalls

- **NEVER use Control nodes (ColorRect/Label) as world-space visuals.** Controls
  render in UI/screen space, not the Camera2D world — a game whose visuals are all
  ColorRects under physics bodies will *run* (physics works headless) but render as
  a blank gray screen. Use `Polygon2D` for world art (walls, bodies, lava, sword)
  and put `Label`s under a `CanvasLayer` for UI. This is the #1 cause of
  "gray screen, nothing renders" in generated games.

- **Headless Godot cannot render.** `--headless` uses a dummy rendering server —
  `get_texture().get_image()` returns null. Screenshots REQUIRE `xvfb-run`
  (`sudo apt install -y xvfb`). The design→implement→verify loop works without it.
- **`.tscn` format is strict.** Use `format=3`, no UIDs, `load_steps = 1 + ext + sub`.
  For generated games, prefer building the scene in `_ready()` with code so GLM
  only writes `.gd` files — avoids .tscn hand-authoring errors entirely.
- **GLM 5.3 forces always-on reasoning — it CANNOT be disabled.** Only
  `reasoning_effort` low/high/max. `llm.py` sends `reasoning: {"effort": "low"}`
  + `include_reasoning: false` by default. Without this, the hidden reasoning
  silently eats the entire `max_tokens` budget and `content` comes back empty
  (`finish_reason=length`). Don't remove that.
- **GLM wraps output in markdown fences and appends "How it works" prose.** Always
  use `--strip-fences` (extracts the first fenced block) when generating code, or
  GDScript parsing fails on the stray ` ``` ` + markdown tail.
- **GLM 5.3 full is text-only.** Never pass an image to `z-ai/glm-5.3`; use
  `z-ai/glm-5.3-flash` for any vision call.
- **One bead at a time.** Never ask GLM for the whole game in one shot — it collapses
  on cross-file inconsistency. The design stage produces beads; implement each
  separately, verifying the build after each.
- **Verify after every implement** with `godot --headless --quit`. GDScript parse
  errors are the #1 failure mode; catch them immediately, not at the end.
- **GLM codegen is plausible-but-wrong on physics.** Review generated RigidBody2D
  code for: wrong property names (`lock_rotation` not `angular_lock`;
  `physics_ticks_per_second` is a project setting, not a node property);
  `setup()`/`_ready()` ordering (nodes built in `_ready()` don't exist when a
  pre-`add_child` `setup()` touches them); and surface-cling/tangent sign errors —
  fix with projection: `move -= normal * move.dot(normal)`.
- **Headless viewport is degenerate** — `get_viewport_rect().size` returns ~0 with
  the dummy display, so viewport-sized collision shapes go negative. Add a fallback
  size in `_ready()`: `if arena_size.x < 100: arena_size = Vector2(960, 640)`.
- **Body-mode changes in physics callbacks need `set_deferred`.** Setting `freeze`
  (or any body-mode) inside a `body_entered` handler throws "Can't change state
  while flushing queries." Use `node.set_deferred("freeze", true)`.

## Scripts

- `scripts/llm.py` — OpenRouter text + vision wrapper (`chat` / `vision` modes).
- `scripts/scaffold.py` — minimal Godot 4 project scaffold.
- `scripts/capture.py` + `scripts/capture.gd` — screenshot under xvfb.

## References

- `references/glm-5.3-api-quirks.md` — GLM 5.3/Flash provider gotchas (always-on
  reasoning, the `include_reasoning`+`effort:low` fix, model IDs, pricing, fences).

## References

- `references/glm-5.3-api-quirks.md` — full detail on GLM 5.3's always-on
  reasoning (empty-content failure + fix), fence-wrapping, and the vision split.

## Related skills

- `godot-gamedev` — Godot patterns, .tscn pitfalls, headless testing.
- `game-art-ai-pipeline` — replacing ColorRect placeholders with real assets later.
