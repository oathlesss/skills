# Nightly Notes Curator — Cron Job Reference

Job ID: `2e164fee3899`
Schedule: `0 2 * * *` (2 AM UTC daily)
Skills: `notes-curation` (desired — currently `ponytail`, pending cronjob update)
Toolsets: `file`, `terminal`, `session_search`
Deliver: `origin` (this Discord thread)

## Current Prompt (self-contained, Dec 2026)

The prompt is fully self-contained with vault structure, frontmatter rules, WikiLinks, graduation criteria, and execution steps inline. It does NOT depend on the notes-curation skill being loaded.

Long-term: switch to `skills: ["notes-curation"]` on the cron job and shorten the prompt to reference the skill (reduces token cost, keeps rules in one place).

## Evolution

- v1: Used `ponytail` skill, over-aggressively moved 14 notes to archive/ in first run. Prompt had loose criteria: "well-structured and polished" → anything with frontmatter qualified.
- v2: Tightened graduation criteria: ALL THREE required (>7 days + stable topic + polished), hard limit of 2 moves per run. Fixed by adding explicit guardrails: "If you move more than 2 notes out of inbox/ in a single run, you're being too aggressive."
- v3 (user-directed): Switched from `inbox/archive/quick/trash` to `inbox/outbox/trash`. User explicitly defined: "Inbox: Quick notes put together. Outbox: Structure the notes and link them where possible." This made the pipeline cleaner — two stages instead of four directories.
- v4: Made WikiLinks the graduation currency: ≥2 [[WikiLinks]] required for outbox/. New notes always land in inbox/ first. Graduation requires ALL: proper frontmatter, ≥2 links, ≥3 days old, stable topic.
- Current: Self-contained prompt with ponytail skill. Pending: switch to notes-curation skill for canonical rule source.
