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
- **web_extract FAILS with ddgs backend — it is search-only.** The ddgs backend returns error: `"DuckDuckGo (ddgs) is a search-only backend and cannot extract URL content."` for ALL web_extract calls. You cannot extract page content with ddgs. Either switch to firecrawl/tavily/exa in config, or rely on rich search snippets (they often contain enough detail for research tasks). Subagents inherit the same backend — they hit the same wall.
- **delegate_task can be interrupted before subagents finish.** When the parent agent sends a batch of 3 subagents and the first is still running when the parent's turn ends, the subagent returns `status: interrupted` and the remaining subagents never start (error: "Parent agent interrupted — child did not finish in time"). Fallback: when this happens, do NOT retry delegation. Switch to direct `web_search` calls from the parent — they're faster and more reliable for the same research goal. Run 4-6 searches across categories, compile from snippets. You lose parallelism but reliably get results in one turn.
- **Don't make subagents too broad.** "Research everything about topic X" produces shallow results. Split into focused sub-goals.
- **Parallel tasks can't coordinate.** If task B needs results from task A, run them sequentially instead.
- **Delegate tasks can time out or be interrupted.** When model latency is high or the parent agent is also making tool calls, subagents may return `status: interrupted` before completing. If the first subagent in a batch is interrupted and others never started, fall back to direct `web_search` calls — you'll get results faster and more reliably for time-sensitive research. Don't spend multiple turns retrying delegation when direct searches work.

- **Guide compilation requires DEEPER source targeting, not just broader topics.** When the user asks for a "very detailed guide" or comprehensive reference (especially for games, modpacks, community tools, or any topic with creator/community ecosystems), topic-split subagents produce shallow results. The user expects research pulled from SPECIFIC named sources, not general wiki summaries. Structure the research wave by SOURCE TYPE, not just by subtopic:
  - **YouTube**: search for specific creators by name (e.g. "Pilpoh ATM10 guide", "John Hall ATM10 tips") — target playthroughs, tutorials, tips videos
  - **Reddit**: search for community threads — pinned guides, tips megathreads, "things I wish I knew" posts, "share your tips" exchanges. Use `site:reddit.com/r/<subreddit>` in queries
  - **Wikis/official docs**: target specific wiki pages, not just general modpack description pages
  If the first compilation wave produces a guide that's mostly cross-referenced wiki summaries, it's too shallow. Do a second wave targeting community sources by name. A good litmus test: would someone watching Pilpoh's playthrough find strategies in your guide that a wiki-only reader wouldn't know? If not, go deeper.

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
