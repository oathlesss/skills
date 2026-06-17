# Project Arachne AI Art Notes

Session context: Project Arachne is a Godot physics brawler with web/grapple mechanics and card drafting. The user asked for an AI art pipeline and corrected several assumptions.

## Durable user/project corrections

- The user has a Linux desktop with an NVIDIA RTX 4070. Lead with Linux/NVIDIA CUDA setup paths.
- Do **not** assume Windows just because the machine is a desktop PC.
- Project Arachne should **not** use spider player characters. Arachne/web/silk identity is mechanical/theme only unless the user later chooses otherwise.
- Character prompts should say stylized brawlers with grappling/web-swinging gear, not spiders/arachnids/eight-legged bodies.

## Concrete repo artifacts created in the session

These were added to the Project Arachne repo as examples of a practical AI art pipeline:

- `tools/setup_comfyui_linux.sh` — Linux/NVIDIA ComfyUI setup; downloads SDXL, IP-Adapter, CLIP Vision, ControlNet OpenPose, VAE; installs ComfyUI Manager, IPAdapter Plus, ControlNet Aux, Impact Pack.
- `tools/setup_comfyui_mac.sh` — Mac fallback.
- `tools/setup_comfyui_windows.ps1` — Windows fallback; do not lead with this for Ruben.
- `tools/prompts/arachne_prompts.txt` — prompt templates and negative prompt guardrails.
- `tools/arachne_palette.gpl` — 32-color Aseprite/GIMP palette.
- `tools/templates/asset_provenance.csv` — provenance template for accepted assets.
- `research/ai-art-pipeline.md` — full pipeline documentation.

## Prompt guardrail learned

Universal negative prompt should include:

```text
spider body, spider character, arachnid, insect body, eight legs
```

Character positive prompt should be closer to:

```text
pixel art brawler character, game sprite,
[CHARACTER_ARCHETYPE: masked duelist / tiny robot / cloak-wearing acrobat / slime fighter / tiny knight],
web-swinging gear or grappling harness,
64x64 sprite size, distinct silhouette,
no spider body, no insect body, two arms, two legs
```

## Review improvements applied

- Added a one-day style spike before production batching.
- Corrected overly optimistic MVP art estimate from ~7 hours to ~15–33 hours.
- Clarified that IP-Adapter improves consistency but does not guarantee it.
- Added provenance logging as a production gate.
- Corrected Flux guidance: variants differ; SDXL is the safer default for shippable assets.
- Ensured ComfyUI setup scripts install custom nodes, not just model weights.

## Future-use checklist

When asked to set up or review an AI art pipeline for game assets:

1. Ask/verify hardware and OS early.
2. Use Linux/CUDA path for Ruben's RTX 4070 desktop.
3. Avoid spider-character assumptions in Arachne.
4. Install both model files and custom nodes.
5. Create prompt templates, palette, provenance log, and setup script.
6. Include an in-engine style/readability spike before asset batching.
