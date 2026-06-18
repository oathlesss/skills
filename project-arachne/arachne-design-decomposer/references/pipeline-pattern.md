# Pipeline Orchestration Pattern — Live Example

This reference documents the meta-prompting pipeline architecture as
proven in the lava-pit boss smoke test (2026-06-18).

## Architecture

```
User: "Design a lava-pit arena boss"
         │
         ▼
  ┌─ Design Decomposer ─┐   Phase 1: arachne-design-decomposer
  │   (subagent, 2.4m)  │   Parse → decompose → spec document
  │   21KB spec, 356 ln  │   Output: design/specs/<feature>.md
  └─────────────────────┘
         │
    ┌────┴────┐
    ▼         ▼              Phase 2: parallel specialist agents
┌─ Art Dir ─┐ ┌─ Code Agent ─┐
│ 3.2m      │ │ 7.2m         │
│ 56 SDXL   │ │ 3 .gd files  │
│ prompts   │ │ 6/6 tests ✓  │
└───────────┘ └──────────────┘
```

## delegate_task Invocation Pattern

Phase 1 is single-task delegation; Phase 2 is batch (2 parallel tasks).
Each subagent gets the full design spec excerpt as context plus
project-specific constraints (style guide, physics rules, theme).

## Proven Results

- **Design spec:** 356 lines, all 5 decomposition dimensions covered
- **Art prompts:** 56 SDXL-ready prompts across 5 asset types, theme-compliant
- **Code:** BossBase (91 ln) + LavaKnightBoss FSM (336 ln) + tests (190 ln)
- **Tests:** 6/6 passing in `godot --headless -s tests/test_lava_knight_boss.gd`
- **Theme:** All 7 compliance checks passed (no spider/insect bleed-through)

## When NOT to Use the Full Pipeline

- Single-asset requests ("generate a card icon") → load only `arachne-art-director`
- Mechanics-only requests ("jump feels floaty") → load only `godot-player-controller`
- Code review of existing code → load only `arachne-code-reviewer`

## File Manifest

| File | Lines | Purpose |
|---|---|---|
| `design/specs/lava-pit-boss.md` | 356 | Design spec (source of truth) |
| `tools/prompts/lava-pit-boss-prompts.txt` | 314 | 56 generated SDXL prompts |
| `scripts/enemies/boss_base.gd` | 91 | BossBase class |
| `scripts/enemies/lava_knight_boss.gd` | 336 | LavaKnightBoss FSM |
| `tests/test_lava_knight_boss.gd` | 190 | 6 unit tests |

> **Commit:** `2897214` on `main` at github.com/oathlesss/project-arachne
