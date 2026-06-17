# AI Game Art — Model & License Quick Reference

Condensed from `project-arachne/research/ai-game-art-comprehensive-guide.md` (72 KB full guide).
Last updated: 2025-06-17.

## Model Decision Matrix

| Model | Quality | Consistency | VRAM | License | Steam Safe | Recommendation |
|-------|---------|-------------|------|---------|------------|----------------|
| **SDXL** (Juggernaut/DreamShaper) | ★★★★ | ★★★ (with IP-Adapter) | 6-8 GB | OpenRAIL-M | ✅ Yes | **Primary — use this** |
| **Flux.1 [schnell]** | ★★★★★ | ★★ | 8-12 GB (Q5_K_M GGUF) | Apache 2.0 | ✅ Yes | Secondary (backgrounds) |
| **Flux.1 [dev]** | ★★★★★ | ★★ | 12+ GB | Non-commercial | ❌ No | **DO NOT USE** |
| **SD3 / SD3.5** | ★★★ | ★★★ | 8-12 GB | Revenue cap ($1M/yr) | ⚠️ Risky | Avoid for commercial |
| **Midjourney v6** | ★★★★★ | ★ (no ControlNet) | Cloud | Proprietary, ToS limits | ⚠️ Risky | Mood boards only |
| **DALL-E 3** | ★★★★ | ★ | Cloud | Proprietary | ⚠️ Risky | Mood boards only |
| **PixArt-Σ** | ★★★ | ★★ | 6-8 GB | OpenRAIL-M | ✅ Yes | Budget alternative |
| **Playground v2.5** | ★★★ | ★★ | 6-8 GB | Playground ToS | ⚠️ Check ToS | Niche option |

## Safe Stack for Steam / Commercial

```
SDXL (Juggernaut XL / DreamShaper XL)     ← primary model
+ IP-Adapter Plus (weight 0.6-0.8)        ← character consistency
+ ControlNet OpenPose / Canny             ← pose/composition control
+ Aseprite                                 ← pixel cleanup
+ Asset provenance logging                 ← Steam disclosure
= Steam-compatible, legally defensible
```

## Models to AVOID for Commercial Games

- **Flux.1 [dev]** — explicitly non-commercial license. Use [schnell] (Apache 2.0) instead.
- **SD3 / SD3.5** — Stability AI revenue cap ($1M/year). Fine for hobby, risk for commercial.
- **Midjourney** — no local control, no ControlNet, no IP-Adapter, ToS evolving, no reproducibility. Use for concept exploration only, never for production assets.
- **DALL-E** — same issues as Midjourney, plus OpenAI ToS ambiguity on derivative works.
- **Any "anime" fine-tune** based on Danbooru datasets — copyright contamination risk.

## When to Upgrade Beyond SDXL

| Scenario | Upgrade Path |
|----------|-------------|
| More photoreal backgrounds | Flux.1 [schnell] GGUF |
| Better prompt adherence | Flux.1 [schnell] (but lose ControlNet ecosystem) |
| Specific art style not in SDXL | Train a style LoRA on SDXL (cheaper, safer) |
| Need 3D assets | Skip image gen, use Meshy / TripoSR / Hunyuan3D |
| Need animation | AnimateDiff + SDXL, or Kling / Runway for keyframes |

## Provenance Row Template

Every production asset must log:
```csv
path, tool, base_model, base_license, loras, controlnet_ref, ip_adapter_ref, seed, prompt, negative_prompt, human_edits, steam_disclosure_notes
```

## Key Principle

**AI generation is cheap. Human selection, Aseprite cleanup, consistency enforcement, and Godot in-engine verification are the real work (15-33 hours MVP).** Never treat AI output as final — treat it as a curated candidate pool.
