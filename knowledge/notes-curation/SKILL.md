---
name: notes-curation
category: knowledge
description: "Structure, link, and maintain Ruben's Obsidian/ZenNotes vault. Two-stage pipeline: inbox (raw) to quick (structured + linked). Covers frontmatter, WikiLinks, graduation criteria, and common pitfalls."
---

# Notes Curation

Maintain Ruben's knowledge base at `/home/ruben/obsidian-vault/`. Plain `.md` files, served by ZenNotes at notes.oathless.dev.

## Vault Structure

Ruben's framing: *"Inbox: Quick notes put together. Quick: Structure the notes and link them where possible."*

```
inbox/   — Raw drafts, active projects, recently captured ideas. DEFAULT location.
quick/   — Structured, polished notes with [[WikiLinks]]. The finished product.
trash/   — Obsolete/superseded notes. Never delete — move here with explanation.
```

**Pipeline:** inbox (raw) → quick (structured + linked). A note only graduates when it has proper structure AND meaningful cross-links.

## Frontmatter

Every note must have YAML frontmatter at minimum:

```yaml
---
tags: [topic, subtopic]
created: 2026-06-18
---
```

Add `updated:` date when making significant changes to an existing note.

## WikiLinks

A note without links is not ready to graduate.

When processing a note:
1. Scan all notes in quick/ AND inbox/ for related topics
2. Add `[[WikiLinks]]` wherever content overlaps
3. Link new notes into the existing knowledge graph

**Two linking styles:**

**Inline** — links woven into the prose. Preferred for narrative notes, research, guides.
```markdown
The [[Modpack Landscape]] research showed that no single pack bundles all four mods.
```

**Related section** — links grouped at the bottom. Used for collection-type notes (session summaries, meeting notes) where links would disrupt the summary flow.
```markdown
## Related
- [[Modpack Landscape — Create, Ars Nouveau, Aeronautics]] — the ecosystem this search explored
- [[ATM10 Early Game Tips]] — tips relevant to the modpack setup discussed
```

Each link in a Related section gets a one-line reason — this is what makes the section useful vs. a bare link dump. If no genuinely related notes exist, omit the section entirely.

## Graduation Criteria (inbox to quick)

A note graduates to quick/ ONLY when ALL of these are true:
1. Proper frontmatter (tags, created date)
2. Clear structure with section headers, no walls of text
3. At least 2 [[WikiLinks]] to other notes
4. Topic is stable (not a rapidly-changing active project plan)
5. Note is at least 3 days old

**When in doubt, leave it in inbox/.** This is the most important rule.

If you graduate more than 2 notes in a single curation run, stop and reconsider — you're likely being too aggressive.

## Creating New Notes

New notes ALWAYS go to inbox/ first. Never create directly in quick/ — the graduation step is essential for quality.

When creating a note from session context or git activity:
1. Write to inbox/ with proper frontmatter
2. Add at least 1-2 [[WikiLinks]] to existing notes
3. Let the nightly curator handle graduation later

## Exporting Notes to PDF

See [[references/markdown-to-pdf.md]] for the working pipeline (xhtml2pdf) and documented dead ends. Use when a note needs to be shared as a formatted PDF outside the vault.

## Common Pitfalls

### Over-aggressive graduation
Moving too many notes from inbox/ to quick/ in one pass. The inbox/ should typically be the LARGEST directory. Most curation runs should graduate 0-1 notes.

### Skipping links
Adding frontmatter but not cross-links. A note with tags but no WikiLinks is not quick-ready. Links are the hardest and most valuable part of curation.

### New notes to wrong directory
Creating notes directly in quick/. New notes are always raw — they go to inbox/ where they can be linked and polished over time.

### Deleting instead of trashing
Never delete content. Move obsolete notes to trash/ with a comment explaining why.

### Prompt/skill drift
The Nightly Notes Curator cron job (`2e164fee3899`) currently has a self-contained prompt with all rules inline. If you update rules here in the skill, you MUST also update the cron job's prompt — otherwise they drift apart. Long-term fix: switch the cron job to `skills: ["notes-curation"]` with a short prompt that just references this skill.

### Session-summarizer notes are not authoritative
The Session Summarizer cronjob (`7852c13dd74b`) auto-generates `Session-YYYY-MM-DD-HH-MM-topic-slug.md` notes in inbox/. These are LLM-written summaries with no verification step — they can fabricate conclusions, claim tasks were completed that weren't, or misattribute decisions. **Always cross-reference these against actual system state** (cronjob list, git log, filesystem) before treating their claims as fact. They are useful pointers, not ground truth.

## Exporting Notes

To share a note as PDF or other format, see `references/pdf-export.md` for the conversion workflow (fpdf2-based, works without sudo or system PDF engines).

## Active Notes (keep in inbox/)

These topics are actively evolving and should stay in inbox/:
- Hermes Agent setup and skills
- Homelab infrastructure
- Project Arachne game development
- Project Arcanum (Minecraft modpack)
- Key lessons and patterns (growing list)
- Any project plan or active initiative

## Reference Notes (appropriate for quick/)

These are stable research/reference — good candidates for quick/:
- Completed AI/game-dev research documents
- LLM model comparisons
- Hardware specs and upgrade options
- Setup guides for stable services (once configured and not changing)
