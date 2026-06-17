# Project Arachne AI Art Pipeline — Session Notes

Concrete workflow created for Ruben's Project Arachne.

## Context

Project Arachne is a Godot 4.6 local physics brawler with roguelite card drafting. The user wants AI-generated game art eventually, but prototyping should use placeholders until gameplay stabilizes. User has a desktop PC with an NVIDIA RTX 4070.

## Repo artifacts created

In `/home/ruben/project-arachne`:

- `research/ai-art-pipeline.md` — full pipeline doc
- `tools/setup_comfyui_windows.ps1` — Windows/NVIDIA setup for RTX 4070
- `tools/setup_comfyui_linux.sh` — Linux/NVIDIA setup
- `tools/setup_comfyui_mac.sh` — Mac Apple Silicon fallback
- `tools/prompts/arachne_prompts.txt` — prompt templates and negative prompt
- `tools/arachne_palette.gpl` — 32-color palette in GIMP/Aseprite-compatible format
- `tools/templates/asset_provenance.csv` — provenance log template

## Important corrections made during review

Original pipeline had useful direction but needed hardening:

1. Added Windows setup because the user's 4070 desktop may run Windows.
2. Added required ComfyUI custom nodes; model files alone are insufficient.
3. Replaced optimistic MVP art estimate (~7h) with realistic 15–33h.
4. Clarified IP-Adapter improves consistency but does not guarantee it.
5. Added asset provenance tracking for Steam/licensing.
6. Added 1-day style spike before production batching.
7. Defaulted shippable assets to SDXL; treat Flux as optional until license/variant is verified.

## Setup command examples

Windows:

```powershell
git clone https://github.com/oathlesss/project-arachne.git
cd project-arachne
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\tools\setup_comfyui_windows.ps1
```

Linux:

```bash
git clone https://github.com/oathlesss/project-arachne.git
cd project-arachne
bash tools/setup_comfyui_linux.sh
```

## Commit history of relevant changes

- `0a0319c` — Add AI art pipeline research document
- `b1cffd1` — AI art pipeline: setup scripts, prompts, palette
- `1852c47` — Review and harden AI art pipeline

These commit SHAs are session-specific; do not store them in memory. Use them only if looking up this exact session/repo state.
