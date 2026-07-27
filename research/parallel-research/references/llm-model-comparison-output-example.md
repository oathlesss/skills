# Example LLM Comparison Output Structure

This file shows the expected output format from the LLM model comparison recipe.
The structure prioritizes dense, scannable tables optimized for Discord display.

## Format conventions

- Use `|` markdown tables with aligned columns
- Bold model names — **Model Name**
- Bold standout numbers — **95.5%**, **$0.43**
- Use emoji headers: 🏆 🥈 💰 🆓 🎯 🧠 ✍️ 🔍 🎨 💸
- Keep tables to ~6-8 rows max per tier for readability
- Include `$0.00` or `FREE` for zero-cost models
- Use `—` for missing data, not "N/A"

## Tier structure

```
TIER 1: GOD TIER (Best of the Best)
- Arena Elo 1500+, SWE-bench 80%+
- 5 models max

TIER 2: FRONTIER (Professional-Grade)  
- Strong but not absolute top
- 6-8 models

TIER 3: HIGH-VALUE (Best Price/Performance)
- Good capability at lower cost
- 6-8 models

TIER 4: BUDGET CHAMPIONS (Cheapest Capable)
- Sub-$0.50/M input, or free
- 5-7 models
```

## Task section structure

Each "Best for X" section:
1. Table with Rank | Model | Key Metric | Cost
2. A value pick (💰) at the bottom
3. Brief justification in one line

## Quick recommendations format

```
| If you want... | Use... |
|----------------|--------|
| Absolute best | Claude Opus 4.8 |
| Best value | DeepSeek V4 Pro |
| Cheapest | Llama 3.1 8B |
| ... | ... |
```

## Key Insights section

Bullet points, one per model or finding, with the most surprising/actionable insight first.
Use bold for model names and standout numbers.
Keep to 8-10 bullets max.
