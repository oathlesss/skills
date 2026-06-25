---
name: zennotes-capture
description: Automatically capture noteworthy discussions as notes in Ruben's ZenNotes vault. Every time we discuss something substantive — decisions, ideas, research findings, plans, technical discoveries — save a note.
triggers:
  - "create a note"
  - "save this to zennotes"
  - "make a note of this"
  - "note this"
  - "remember this for later"
  - "write this down"
  - "make a note in ZenNotes"
  - "you didn't make a note"  # self-correction: user called out missed capture — write it now
---

# ZenNotes Capture

Proactively save noteworthy discussions to Ruben's ZenNotes vault at `/home/ruben/obsidian-vault/inbox/`.

## When to capture

**MANDATORY: After completing substantive research or a knowledge-heavy task, capture automatically.** Do not wait for Ruben to ask. If you just did a multi-tool research session, produced a detailed answer with code/examples, or compiled technical reference material — write the note in the same turn you deliver the answer. He will call it out if you don't.

**Self-check (run before ending every research turn):**
1. Did I use web_search, delegate_task, or any research tooling in this turn?
2. Is the answer I'm about to deliver more than a short paragraph?
3. Did I already write this to ZenNotes?

If (1 AND 2) and NOT 3 → you are about to fail. Write the note NOW, before sending your final summary. This is the most common failure mode. If you skip this check and the user says "you didn't make a note," you've broken the contract — apologize immediately and write it.

Save a note whenever we discuss something that has lasting value:

- **Research** — findings, comparisons, benchmarks, things learned. **This is #1.** If you used web_search, delegate_task, or any research tooling and the answer is more than a paragraph, it's a note.
- **Decisions** — why we chose X over Y, architectural decisions, tool/tech choices
- **Ideas** — project concepts, feature ideas, things to explore later
- **Plans** — roadmaps, next steps, implementation strategies
- **Technical discoveries** — bugs and their root causes, workarounds, configuration quirks
- **References** — useful links, docs, commands worth remembering
- **User preferences** — anything Ruben explicitly says he wants to remember

Do NOT capture:
- Trivial chit-chat, greetings, casual banter
- Things already well-documented in memory or skills
- Temporary task state (that's what session search is for)

## Note format

Create notes as markdown files in `/home/ruben/obsidian-vault/inbox/`:

```
Filename: YYYY-MM-DD-topic-slug.md

# Title (clear, searchable)

Brief summary of what was discussed and why it matters.

Key points as bullet list if applicable.

## Context
- Date: YYYY-MM-DD
- Source: [Hermes / #channel-name]
- Status: draft | decision | reference | idea

## Details
(Whatever is relevant — expand on the topic here)
```

Use `write_file` to create the note.

## Procedure

1. After each substantive discussion (or when Ruben explicitly asks), identify what's note-worthy
2. Create a single note per topic (don't scatter one conversation across 5 notes)
3. Write it to `/home/ruben/obsidian-vault/inbox/YYYY-MM-DD-topic-slug.md`
4. Briefly confirm: "Saved to ZenNotes: filename.md"

If multiple distinct topics were discussed, create separate notes.

## Pitfalls

- **Don't forget to capture research.** This is the most common failure mode. If you just did a multi-tool research task, write the note immediately — don't wait for the user to ask. If the user says "you didn't make a note", apologize and write it now.
- Don't over-capture — not every message is a note. Err on the side of quality over quantity.
- Don't capture things that are purely actionable (those go in memory/todos)
- The vault lives on the local filesystem — ensure the path is writable before writing
- Filename convention is flexible — semantic names like `minecraft-modding-research-2026.md` are fine alongside the date-prefixed format. Just make it searchable and descriptive.

## Session Summary Notes

When summarizing inactive Discord sessions (manual or via the Session Summarizer cronjob), use this specific template:

```
---
tags: [session-summary]
created: YYYY-MM-DD
source: discord
session_id: <full_session_id>
---

# Session-YYYY-MM-DD-HH-MM — <topic-slug>

**Title:** <title>
**Messages:** <count>

## Summary
<2-4 sentences>

## Key Points
- <3-6 bullet points>

## Related
- [[Note Title]] — one-line reason
```

Key differences from standard notes:
- `session_id` in frontmatter preserves traceability back to the original conversation
- `tags: [session-summary]` (not `tags: [session-summary, ...]`) — these are a distinct class of note
- `## Related` section with `[[WikiLinks]]` to existing vault notes is mandatory when related notes exist
- Filename: `Session-YYYY-MM-DD-HH-MM-<topic-slug>.md` (capital S, hyphenated datetime, topic slug)

## Related-Note Linking

After creating any note, scan existing vault notes for topical overlap:

1. List notes in `inbox/` and `outbox/` — extract titles and tags from frontmatter
2. Match by topic domain (Minecraft → Minecraft references, Go/Vue → project notes, etc.)
3. Append `## Related` with `[[Exact Note Title]]` — exact title, not a guess
4. Add a one-line reason per link (e.g., `— the modding ecosystem explored here`)
5. Only add genuinely related links — skip if nothing matches

For retroactive batch linking (50+ notes), use `delegate_task` with 3 parallel subagents, each handling a chunk of file paths. Subagents use `read_file` + `patch` to append sections.

## References

- `references/research-refinement-pattern.md` — Multi-round research workflow: overview → deep-dive → plan. When to merge notes vs create separate ones.
- `references/session-summarizer-pattern.md` — Automated session → ZenNotes pipeline: DB queries, cronjob setup, deduplication, and batch processing.
