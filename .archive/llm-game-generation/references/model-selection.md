# Model Selection for Game Generation (2026-09)

## Comparison (March–Aug 2026 leaderboards; prices approximate USD/M)

| Model | AA Index | Output $/M | License | Context | Notes |
|---|---|---|---|---|---|
| Claude Opus 5 | 63 | $25 | closed | ~200K | Frontier leader, strong agentic + vision |
| GPT-5.6 "Sol" | 61 | $30 | closed | ~200K | Best terminal/new-problem; expensive |
| **GLM 5.3 (full)** | 60 | $4.40 | MIT | 1M | Code/agentic-only, NO vision. Best price/perf |
| **GLM 5.3 Flash** | 46 | $0.25 | MIT | 1M | Native multimodal (image+video). The "eyes" |
| Gemini 3 Pro | strong | low | closed | — | Leads GameDevBench (Godot tasks) |
| DeepSeek V4 Pro | — | $0.87 | — | — | Cheap bulk; weaker multi-step agentic |

## GLM 5.3 facts (released 2026-08-14, Z.ai / Zhipu)

- 743B base (same as GLM 5.2), **MIT weights on HuggingFace**. 1M-token context, 128K max output.
- Coding: 50% better than GLM 5.2 on Z.ai Code Bench; open-source SOTA on Terminal-Bench 3.0 + Agents' Last Exam (CLI).
- CyberGym 84.5% (beats Anthropic Mythos 5 83.8%, GPT-5.6 Sol 83.6%).
- **The full GLM 5.3 is text/code ONLY — no image input.** The first native multimodal model in the GLM-5 series is **GLM 5.3 Flash** (320B-A18B MoE, MIT, image+video input). For any screenshot-critique / vision step, use Flash (or Gemini 3 Pro / Claude).
- Self-host reality: 743B needs ~400GB+ VRAM multi-GPU. Not feasible on a no-GPU homelab (Ruben: OptiPlex 30GB, no GPU). Use API.

## Hermes wiring (verified against ~/.hermes/config.yaml)

- Built-in providers (from config comments): `zai` (ZAI_API_KEY → Z.AI/GLM), `openrouter` (OPENROUTER_API_KEY), `openai-codex`, `nous`, `kimi-coding`, `minimax`, `bedrock`.
- **OpenRouter model IDs** use prefix `z-ai` (hyphen, not `zai`): `z-ai/glm-5.3`, `z-ai/glm-5.3-flash`.
- **Z.ai direct** model IDs: `glm-5.3`, `glm-5.3-flash`. List price $1.4/M in, $4.4/M out (full); $0.15/$0.50 flash (OpenRouter resells flash at $0.075/$0.25).
- Ruben's config as of 2026-09-09: `model.default: deepseek-v4-pro`, `provider: deepseek`, `base_url: https://api.deepseek.com/v1`, `providers: {}`, fallback `openrouter → anthropic/claude-sonnet-4`. OpenRouter key already present — switching to GLM via OpenRouter needs no new key.

## Game-gen role split (recommended)

- **Brain** (design doc + GDScript + agentic loop): GLM 5.3 full, or Claude Opus/Sonnet.
- **Eyes** (screenshot critique / VLM judge): GLM 5.3 Flash or Gemini 3 Pro.
- **Bulk** (boilerplate, docs, asset lists): DeepSeek V4 Pro.

## Key source URLs

| Resource | URL |
|----------|-----|
| GLM-5 GitHub (Z.ai) | https://github.com/zai-org/GLM-5 |
| GLM 5.3 Flash VLM docs | https://docs.z.ai/guides/vlm/glm-5.3-flash |
| godogen | https://github.com/htdt/godogen |
| GodotPrompter | https://github.com/jame581/GodotPrompter |
| OpenGame | https://arxiv.org/abs/2604.18394 |
| GameDevBench | https://arxiv.org/abs/2602.11103 |
| Genie 3 | https://deepmind.google/models/genie/ |
