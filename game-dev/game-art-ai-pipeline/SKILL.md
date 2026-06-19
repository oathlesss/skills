---
name: game-art-ai-pipeline
description: Set up, review, and harden AI-generated game art pipelines for indie games using ComfyUI/SDXL, with production guardrails for consistency, licensing, provenance, and Steam disclosure.
triggers:
  - AI game art pipeline
  - ComfyUI setup for game art
  - generate game sprites with AI
  - SDXL game asset workflow
  - Steam AI art disclosure
  - AI-generated sprites, card icons, UI, or backgrounds
---

# Game Art AI Pipeline

Use this skill when the user asks to research, set up, review, or improve an AI art workflow for game assets.

## Default recommendation

Use **ComfyUI + SDXL + Aseprite** for production game art.

- ComfyUI gives reproducible node workflows and batch generation.
- SDXL is the safest default model family for shippable assets: strong community support and relatively clear commercial use terms.
- Aseprite handles the part AI is bad at: readable pixel cleanup, silhouettes, palette enforcement, and animation polish.

Avoid committing to Midjourney/DALL-E as the production pipeline for game assets: they are useful for mood exploration but weak on reproducibility, local control, and traceable production workflows.

## Hardware guidance

- RTX 4070 12GB is strong enough for SDXL, IP-Adapter, ControlNet, card-icon batching, and modest LoRA work.
- Treat Flux and newer models as optional concept-art experiments unless license terms and VRAM workflow are verified.
- If user has a 4070 desktop, add Windows and Linux setup paths; do not assume the machine is Linux.

## Setup checklist

A production-ready ComfyUI install should include:

1. ComfyUI
2. CUDA PyTorch for NVIDIA desktops
3. ComfyUI Manager
4. IPAdapter Plus custom nodes
5. ControlNet Aux preprocessors
6. Impact Pack or equivalent batch/utility nodes
7. SDXL base checkpoint
8. SDXL VAE
9. IP-Adapter SDXL model
10. CLIP Vision model for IP-Adapter
11. ControlNet OpenPose or line-art model, depending on asset type

Pitfall: downloading IP-Adapter/ControlNet model files is not enough. The ComfyUI custom nodes must also be installed.

## Workflow strategy

### 1. Prototype with placeholders

For gameplay prototyping, use rectangles, stick figures, and simple geometric markers. Do not batch-generate final art before gameplay stabilizes.

### 2. Run a 1-day style spike early

Exception to placeholder rule: run one disposable style spike early to validate readability.

Deliverables:
- 1 character concept + 4-frame movement test
- 1 weapon sprite
- 3 card icons from different categories
- 1 arena background crop
- 1 UI card frame mockup
- All imported into-engine at intended size

Pass criteria:
- Character reads at gameplay scale
- Player outline colors remain obvious
- Weapon silhouette reads at gameplay zoom
- Card icons read without text
- Background does not compete with players or effects
- Palette reduction preserves important details

If the spike fails, change art direction before producing batches.

### 3. Produce final batches later

Once gameplay and asset list are stable, batch-generate production candidates and curate them.

Suggested order:
1. characters and readability tests
2. weapons
3. card icons
4. UI frames
5. arenas/background layers
6. VFX/particles

## Consistency guidance

- IP-Adapter improves identity consistency but does **not** guarantee it.
- ControlNet/OpenPose works better for humanoids than spiders or unusual creatures; use line-art/reference sketches when pose skeletons are awkward.
- Fixed prompts and fixed seeds help only after the style direction is clear.
- Once a frame is approved, treat it as source-of-truth; edit future frames toward it instead of endlessly regenerating.
- Train a style LoRA only after there are enough approved assets. Do not train from early rejected experiments.

## Time estimates

Be conservative. AI generation is cheap; cleanup, selection, consistency, and in-engine readability are the real work.

For an MVP, estimate roughly **15–33 hours** of human art work, not one evening:
- character frames: 6–16h
- weapons: 1–2h
- card icons: 3–5h
- arena backgrounds: 2–5h
- UI: 2–4h
- VFX: 0.5–1h

## Legal and provenance guardrails

Every accepted production asset should have a provenance row before entering `assets/`.

Track:
- final path
- AI tool/workflow
- base model and license
- LoRAs and custom models
- IP-Adapter/ControlNet references
- seed
- prompt and negative prompt
- human edit notes
- Steam disclosure notes

Use a universal negative prompt that excludes text, watermarks, logos, and famous/copyrighted characters. Keep prompts original and avoid named artists/franchises.

Steam AI disclosure requires explaining pre-generated AI content. Provenance prevents launch-time panic.

## References

- `references/project-arachne-ai-art-pipeline.md` — concrete Project Arachne implementation: RTX 4070 setup scripts, prompt templates, palette, provenance CSV, and review corrections.
- `references/model-license-quick-reference.md` — condensed model comparison table, legal/licensing decision matrix, and one-glance recommendations. Extracted from the full 72 KB comprehensive guide.
- `references/procedural-pillow-character-art.md` — fallback when ComfyUI/image_gen toolset is unavailable: procedural character/avatar generation using only Pillow polygon primitives, with vision_analyze self-critique loop. Covers setup (uv + Pillow PEP 668 safe), silhouette construction from body landmarks, side-profile glute technique, color palette, and pitfall list (smooth interpolation merges limbs, front view can't show glutes, arc angles are degrees not radians).
- Project Arachne `research/ai-game-art-comprehensive-guide.md` (72 KB) — the full deep-dive: 15 models compared, ComfyUI workflows for spritesheets/icons/backgrounds, pixel art tools, 3D asset generation, AI animation tools, character consistency techniques ranked, UI/UX generation, legal per model with revenue caps, RTX 4070 VRAM budget. Load this when the quick reference isn't enough or the user asks about a specific tool/technique not covered in the skill.
