# Session Summarizer Pattern

Automated pipeline that finds inactive Discord sessions and summarizes them into ZenNotes with cross-linking.

## Cronjob (ID: 7852c13dd74b)

**Schedule:** Every hour  
**Inactivity threshold:** Last message > 2 hours ago  
**Dedup:** `/home/ruben/.hermes/cron/session-summarizer/processed.txt`  
**Cap:** 5 sessions per run (prevents token blowout on first run)  
**Toolsets:** terminal, file, session_search  

## Session DB Query

The session DB is at `/home/ruben/.hermes/state.db`. Key schema:

```
sessions: id, title, source, started_at, message_count, archived
messages: id, session_id, role, content, timestamp
```

**Query for inactive sessions** (subquery in WHERE, NOT HAVING — SQLite rejects HAVING without GROUP BY):

```sql
SELECT s.id, s.title, s.message_count,
       (SELECT MAX(m.timestamp) FROM messages m WHERE m.session_id = s.id) as last_ts
FROM sessions s
WHERE s.source = 'discord'
  AND s.archived = 0
  AND s.message_count >= 3
  AND (SELECT MAX(m.timestamp) FROM messages m WHERE m.session_id = s.id) IS NOT NULL
  AND (SELECT MAX(m.timestamp) FROM messages m WHERE m.session_id = s.id) < (unixepoch() - 7200)
ORDER BY last_ts DESC
LIMIT 5
```

**Pitfall:** `HAVING last_ts < ...` fails with `OperationalError: HAVING clause on a non-aggregate query`. Must use a subquery in WHERE instead.

## Session Summary Note Template

```markdown
---
tags: [session-summary]
created: YYYY-MM-DD
source: discord
session_id: <full_session_id>
---

# Session-YYYY-MM-DD-HH-MM — <topic-slug>

**Title:** <session title or descriptive title>
**Messages:** <count>

## Summary
<2-4 sentences>

## Key Points
- <3-6 bullet points>

## Related
- [[Note Title]] — one-line reason
```

- Filename: `Session-YYYY-MM-DD-HH-MM-<topic-slug>.md`
- `session_id` in frontmatter preserves the trace back to the original conversation
- `tags: [session-summary]` enables bulk queries in Obsidian

## Related-Note Linking

After writing a session note, scan existing vault notes for topical overlap:

1. List all notes in `inbox/` and `outbox/` — titles + tags from frontmatter
2. Match by topic domain: Minecraft → Minecraft references, Go/Vue → Go references, etc.
3. Append `## Related` section with `[[WikiLinks]]` using exact note titles
4. Only add genuinely related links — don't force connections

**Linking rules of thumb:**
- Session about Minecraft/modded MC → link to any Minecraft reference notes
- Session about web dev (Go, Vue, hosting) → link to related project notes
- Session about soundproofing/renovation → link to home reference notes
- Session about AI, programming career → link to AI/programming notes

## Batch Processing Large Backlogs

For retroactive processing of many sessions (50+):

1. Use `delegate_task` with 3 parallel subagents, each handling ~30-45 files
2. Each subagent gets: the list of file paths + the reference note catalog
3. Subagents use `read_file` + `patch` to append `## Related` sections
4. Deduplicate with `processed.txt` to avoid re-processing

## Deduplication Pattern

```bash
# Check if session was already processed
grep -qxF "$SESSION_ID" /home/ruben/.hermes/cron/session-summarizer/processed.txt

# Mark as processed after successful write
echo "$SESSION_ID" >> /home/ruben/.hermes/cron/session-summarizer/processed.txt
```
