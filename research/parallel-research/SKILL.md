---
name: parallel-research
description: Run parallel web research via delegate_task subagents, compile structured reports to disk, and synthesize findings. Use when research spans multiple topics or angles that can run independently.
triggers:
  - User asks to research multiple topics simultaneously
  - Research task has 2+ independent subtopics (e.g. "find X for A and Y for B")
  - Need fresh web data that training cutoff can't provide
  - User asks "research X" with broad scope
---

# Parallel Research via Delegate Task

## When to use this skill

- Research spans 2-3 independent topics that can run in parallel
- Each subtopic requires its own web_search/web_extract calls
- You want structured output files the user can reference later
- The task would flood your context window with raw search results

## NOT for

- Single-query lookups (just use web_search directly)
- Tasks needing user interaction during research
- Trivial lookups where training data suffices

## Workflow

### Step 1: Meta-prompt — assess and decompose

Before delegating, think through:
1. What are the independent subtopics? (max 3 for parallel)
2. What does each subagent need to know? (context: user's setup, location, preferences)
3. What output format do you want from each? (specify in the goal)
4. Any regional/product constraints to pass along?

### Step 2: Delegate in parallel

Use `delegate_task` with `tasks` array (batch mode). Each task gets:
- **goal**: Specific research question, including desired output format
- **context**: User's setup, location, constraints, anything the subagent can't infer
- **toolsets**: `["web", "terminal"]` for web research tasks

Example:
```
delegate_task(tasks=[
  {"goal": "Research X. Find A, B, C. Return structured summary with prices and links.",
   "context": "User in NL/BE, has Home Assistant, technically skilled...",
   "toolsets": ["web", "terminal"]},
  {"goal": "Research Y. Find D, E, F. ...",
   "context": "...",
   "toolsets": ["web", "terminal"]}
])
```

### Step 3: Review and verify

Subagent summaries are self-reports — verify:
- Were files actually written? `stat` them
- Do prices/sources look plausible?
- Any contradictions between subagents?

### Step 4: Write structured reports

Each subagent should write its findings to disk (e.g. `~/topic_research.md`). After review, optionally write a synthesis file.

### Step 5: Synthesize for user

Present the combined findings concisely. Don't dump raw reports — extract the actionable bits. Use tables for comparisons. Reference the full report file paths so the user can dive deeper.

## Pitfalls

- **Don't trust subagent summaries blindly.** If a subagent says "wrote file to /tmp/X", stat it. If it says "found product Y at €Z", spot-check.
- **Subagents can't see memory.** Pass all user context (location, setup, preferences) explicitly in the `context` field.
- **Web extraction may fail.** The ddgs backend doesn't always support content extraction. Subagents should cross-reference multiple search results for accuracy.
- **Don't make subagents too broad.** "Research everything about topic X" produces shallow results. Split into focused sub-goals.
- **Parallel tasks can't coordinate.** If task B needs results from task A, run them sequentially instead.

## Support files

- `references/delegate-structure.md` — concrete delegate_task call shape with annotated fields

## Report format convention

Research reports written to disk should follow this structure:
```
# Title
**Date:** YYYY-MM
**Context:** user setup summary

## 1. Section heading
(concise tables and bullets, not walls of text)

## 2. Section heading
...

## N. Key Links Summary
| Category | Resource | URL |
|----------|----------|-----|

---
*Research compiled YYYY-MM. Prices approximate EUR.*
```
