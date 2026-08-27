---
name: memory-hygiene
description: Audit and compact Hermes memory (MEMORY.md + USER.md). Removes stale, duplicate, or obsolete entries. Reports what was cleaned.
triggers:
  - "clean up memory"
  - "memory hygiene"
  - "audit memory"
  - "compact memory"
  - "memory is getting full"
---

# Memory Hygiene

Audit and compact the persistent memory store. Run weekly to keep memory lean and relevant.

## Procedure

### 1. Read current memory

Read `~/.hermes/memories/MEMORY.md` and `~/.hermes/memories/USER.md`. Note the current size in characters.

### 2. Identify problems

For each memory entry, check:

- **Stale** — references to things that no longer exist or have been replaced (old repos, old machines, resolved issues, completed migrations)
- **Duplicate** — same fact stated multiple ways; keep the clearest one
- **Too verbose** — can the same fact be stated in fewer characters without losing meaning?
- **Task progress** — entries like "fixed bug X", "PR #42 merged" — these are session artifacts, not durable facts. Remove them.
- **Obvious** — facts easily re-discovered (OS name, Python version, tool names that `which` reveals)

### 3. Compact

- Merge overlapping entries into one
- Remove qualifying fluff ("currently", "at the moment", "as of now" — memory implies current state)
- Rewrite verbosely stated facts more compactly

### 4. Apply changes

Use `memory(action='remove', ...)` for stale entries, `memory(action='replace', ...)` for compacted entries.

### 5. Report

Output a summary:
- Entries removed (count)
- Entries compacted (count)
- Characters saved
- Before/after sizes

## What NOT to remove

- User preferences and corrections (these are the highest-value entries)
- Stable environment facts that are hard to re-discover (static IPs, hostnames, domain config)
- Recurring conventions (project structure, preferred tools)
- Lessons learned about tool quirks or workflows

## Pitfalls

- `memory(action='replace')` swaps the WHOLE entry, not a substring. `old_text` only *identifies* which entry to replace; `content` must be the complete replacement entry text. Passing a fragment as `content` clobbers the rest of that entry — e.g. "fixing" one project in a long `Projects:` line by passing only the changed tail silently drops every other project in the line. Always reconstruct and pass the full entry.
- Don't remove entries just because they're old — age alone is not staleness
- Don't compact user profile facts without preserving the user's voice
- If uncertain whether a fact is still relevant, keep it
