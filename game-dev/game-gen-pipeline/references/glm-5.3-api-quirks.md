# GLM 5.3 API quirks (OpenRouter)

Hard-won provider details for calling `z-ai/glm-5.3` / `z-ai/glm-5.3-flash` via
OpenRouter. Sourced 2026-09 from live API testing while building the game-gen
pipeline (each item below caused a real failed call before being nailed down).

## Model IDs

- `z-ai/glm-5.3` — full model, 743B. Text/code only, **NO vision**. ~$1.4 in / $4.4 out per M.
- `z-ai/glm-5.3-flash` — 320B-A18B MoE, **native multimodal** (image + video). ~$0.075 / $0.25.
- Batch variants exist: `z-ai/glm-5.3:batch`, `z-ai/glm-5.3-flash:batch`.

## Reasoning CANNOT be disabled (the big one)

GLM 5.3 forces always-on thinking. The Z.ai API removed `thinking.type="disabled"`;
only `reasoning_effort` (`low` / `high` / `max`) remains. This bites hard on code-gen:

- **Failure mode:** with default settings the hidden reasoning silently consumes the
  entire `max_tokens` budget, so `choices[0].message.content` comes back null/empty
  with `finish_reason=length`. Observed: 4k tokens → nothing at all; 12k → a lone
  ` ``` ` fence; the code never arrives.
- **`include_reasoning: false` alone is NOT enough** — it hides reasoning from the
  response but the model still *generates* it internally and burns the budget.
- **Fix (baked into `scripts/llm.py`):** send BOTH
  `{"include_reasoning": false, "reasoning": {"effort": "low"}}` so the model thinks
  minimally and returns only `content`.

## Output hygiene

GLM wraps code in ```gdscript fences AND appends a `**How it works:**` markdown
explanation after the closing fence. `--strip-fences` extracts the first fenced
block; without it the trailing prose breaks GDScript parsing.

## Vision goes to Flash only

`z-ai/glm-5.3` (full) is text-only — passing an image is ignored/errors. Use
`z-ai/glm-5.3-flash` for any screenshot/image critique.

## Pricing note (2026-09)

Full ~$1.4 in / $4.4 out; Flash ~$0.075 / $0.25. DeepSeek v4-pro (~$0.87 out) stays
the Hermes default; GLM is reserved for the pipeline's design/implement/review.
