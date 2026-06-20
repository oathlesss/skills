---
name: ai-game-art-pipeline
description: "Set up and review AI-assisted game art production pipelines using ComfyUI, SDXL, consistency workflows, palette cleanup, provenance, and Steam/licensing guardrails."
triggers:
  - AI game art pipeline
  - ComfyUI setup for game art
  - generating sprites with AI
  - AI card icons or game icons
  - AI art workflow review
  - Steam AI disclosure for game assets
  - IP-Adapter or ControlNet for character consistency
---

# AI Game Art Pipeline

Use this when a user wants to generate game art with AI, especially for a solo/indie game where the output must become production assets rather than one-off concept images.

## Core stance

AI generation is a **production pipeline**, not just prompting. The durable work is:

1. picking a safe model stack,
2. proving a readable style in-engine,
3. controlling consistency,
4. cleaning assets by hand,
5. tracking provenance for Steam/licensing.

Do not overpromise "AI makes all art in an evening." Generation is fast; selection, cleanup, animation consistency, and in-engine readability are the real work.

## Recommended baseline stack

- **ComfyUI** for repeatable node workflows.
- **SDXL** as the default production model when licensing clarity matters.
- **IPAdapter Plus** for character/reference consistency.
- **ControlNet Aux + ControlNet** for pose/edge/depth guidance.
- **Impact Pack** for common utility nodes.
- **Aseprite** for pixel cleanup, palette enforcement, and animation editing.
- **GIMP/Krita** for larger backgrounds and UI mockups.

For NVIDIA desktops, prefer Linux/CUDA when available. Windows is a valid fallback, but do not lead with it if the user says they run Linux.

## Workflow

### 1. Set up the tooling

A working ComfyUI production setup needs both model files **and custom nodes**. Do not stop after downloading SDXL/IP-Adapter/ControlNet weights.

Install or verify:

- ComfyUI
- CUDA PyTorch (for NVIDIA)
- ComfyUI Manager
- `ComfyUI_IPAdapter_plus`
- `comfyui_controlnet_aux`
- `ComfyUI-Impact-Pack`
- SDXL checkpoint
- SDXL VAE
- IP-Adapter model
- CLIP Vision model
- ControlNet model(s)

### 2. Run a one-day style spike before batching

Before producing final assets, make a small vertical slice of art and import it into the game:

- 1 character concept + 4-frame movement test
- 1 weapon sprite
- 3 card icons from different categories
- 1 arena/background crop
- 1 UI/card-frame mockup

Pass criteria:

- character readable at actual gameplay scale,
- player/team outline remains unmistakable,
- weapon silhouette reads at zoom,
- card icons read without text,
- background does not fight gameplay readability,
- palette reduction does not destroy important detail.

If this fails, adjust the art direction globally. Do not fix style one asset at a time.

### 3. Use placeholders during gameplay prototyping

Default to simple placeholders during early gameplay phases. Exception: a deliberately disposable style spike is worthwhile early to test readability. Batch-produce final art only when mechanics and asset requirements are stable.

### 4. Generate candidates, then curate

Typical production loop:

1. Generate many candidates from a fixed prompt template.
2. Pick a small shortlist.
3. Use img2img / IP-Adapter / ControlNet for refinements.
4. Clean and enforce palette manually in Aseprite/GIMP.
5. Import into the engine and verify readability at gameplay scale.
6. Log asset provenance before accepting the asset.

### 5. Track provenance from day one

For every accepted production asset, record:

- final file path,
- AI tool and workflow,
- base model and license,
- LoRAs / ControlNet / IP-Adapter references,
- seed,
- prompt/negative prompt,
- human edit tool and notes,
- source references,
- Steam disclosure notes.

This avoids launch-time panic around Steam AI disclosure and model licensing.

## Consistency techniques

- **IP-Adapter improves consistency, but does not guarantee it.** Phrase it that way.
- **ControlNet OpenPose** is best for humanoid-ish characters; use line art, depth, or sketches for non-humanoid forms.
- **Fixed prompt templates** help with weapon/card/icon batches.
- **Fixed palette/posterization** should be a final cleanup step, not necessarily the generation step.
- **Style LoRA** is worth considering only after enough approved assets exist (roughly 30–50+). Do not train it before the art direction is stable.

## Licensing and policy guardrails

- Prefer models with clear commercial terms.
- SDXL/OpenRAIL-style models are a pragmatic default; still verify exact checkpoint and LoRA licenses.
- Flux variants have different licenses; do not assume all are commercially equivalent.
- CivitAI models/LoRAs vary widely. Check each model.
- Avoid prompts containing living artists, copyrighted characters, franchise names, or recognizably protected IP.
- For Steam, distinguish pre-generated AI assets from live-generated AI content. Most game art is pre-generated, but it still needs disclosure and compliance.

## Practical estimates

For an MVP, plan a focused week rather than an evening. A realistic range is often **15–33 hours** for MVP art once gameplay is stable, with character animation consistency as the main time sink.

## Pitfalls learned

- **Minecraft mod textures / small pixel art (16×16 or 32×32)**: AI generation is often the wrong tool here. SDXL/ComfyUI blurs at these scales and doesn't understand pixel grids. For geometric items (ingots, crystals, shards, pattern-based blocks), procedural generation with Pillow scripts produces faster, cleaner, perfectly consistent results. Reserve AI pipelines for concept art, organic textures, and entity sheets — not batch production of pixel-art item textures.
- Do not infer character design from a project title or mechanics. If a game is web/silk/grapple themed, players do **not** necessarily want spider characters.
- Do not write setup scripts that download IP-Adapter/ControlNet weights but omit the custom nodes needed to use them.
- Do not put Windows first if the user says their RTX desktop runs Linux.
- Do not claim IP-Adapter "ensures" consistency; it biases toward consistency and still needs curation.
- Do not use raw AI outputs as final assets without manual cleanup and in-engine verification.

## References

- `references/project-arachne-ai-art.md` — concrete implementation notes from the Project Arachne session: Linux RTX 4070 setup, non-spider character guardrail, provenance template, and prompt pitfalls.
