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
---

# ZenNotes Capture

Proactively save noteworthy discussions to Ruben's ZenNotes vault at `/home/ruben/obsidian-vault/inbox/`.

## When to capture

Save a note whenever we discuss something that has lasting value:

- **Decisions** — why we chose X over Y, architectural decisions, tool/tech choices
- **Ideas** — project concepts, feature ideas, things to explore later
- **Research** — findings, comparisons, benchmarks, things learned
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

- Don't over-capture — not every message is a note. Err on the side of quality over quantity.
- Don't capture things that are purely actionable (those go in memory/todos)
- If unsure whether something is note-worthy, ask quickly rather than skipping it
- The vault lives on the local filesystem — ensure the path is writable before writing
