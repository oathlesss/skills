# Hermes Session DB (`state.db`)

Location: `~/.hermes/state.db` (SQLite3). All session and message data lives here.

## Schema

### `sessions` table

| Column | Type | Notes |
|--------|------|-------|
| `id` | TEXT | Session ID, e.g. `20260624_074749_6d434884` or `cron_<jobid>_<timestamp>` |
| `source` | TEXT | `discord`, `cron`, `telegram`, etc. |
| `title` | TEXT | User/first-message-derived title; null for cron sessions |
| `started_at` | REAL | Unix timestamp (float) |
| `ended_at` | REAL | Null if session is still active |
| `message_count` | INTEGER | Total messages |
| `archived` | INTEGER | 0=active, 1=archived |
| `tool_call_count` | INTEGER | Total tool calls |
| `input_tokens` / `output_tokens` | INTEGER | Token counters |
| `estimated_cost_usd` / `actual_cost_usd` | REAL | Cost tracking |
| `parent_session_id` | TEXT | For forked/continued sessions |
| `model` / `model_config` | TEXT | Model used |

### `messages` table

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER | Auto-increment |
| `session_id` | TEXT | FK to `sessions.id` |
| `role` | TEXT | `user`, `assistant`, `tool` |
| `content` | TEXT | Message body |
| `timestamp` | REAL | Unix timestamp (float) |
| `tool_calls` / `tool_name` | TEXT | Tool invocation data |
| `reasoning` / `reasoning_content` | TEXT | Thinking traces |
| `platform_message_id` | TEXT | Platform-native message ID |

## Query Patterns

### Find inactive Discord sessions (>N seconds since last message)

```sql
SELECT s.id, s.title, s.started_at, s.message_count,
       (SELECT MAX(m.timestamp) FROM messages m WHERE m.session_id = s.id) as last_ts
FROM sessions s
WHERE s.source = 'discord'
  AND s.archived = 0
  AND s.message_count >= 3
HAVING last_ts IS NOT NULL AND last_ts < (unixepoch() - <seconds>)
ORDER BY last_ts DESC
LIMIT 5
```

### Get session metadata with last activity

```sql
SELECT s.*, 
       (SELECT MAX(m.timestamp) FROM messages m WHERE m.session_id = s.id) as last_active,
       (SELECT MIN(m.timestamp) FROM messages m WHERE m.session_id = s.id) as first_active
FROM sessions s
WHERE s.id = '<session_id>'
```

## Access from cron agents

Cron agents can query via `terminal` (Python + sqlite3 module):

```bash
python3 -c "
import sqlite3
db = sqlite3.connect('/home/ruben/.hermes/state.db')
rows = db.execute('SELECT ...').fetchall()
db.close()
"
```

`execute_code` is **blocked** in cron contexts — use `terminal` for direct DB queries.

## Session Summarizer Cronjob (`7852c13dd74b`)

Runs hourly, finds Discord sessions inactive >2h, summarizes to ZenNotes inbox.

**Pattern:** Query DB → dedup via tracking file → read session via `session_search()` → write note → record processed ID.

**Tracking file:** `~/.hermes/cron/session-summarizer/processed.txt` (one session ID per line).

**Notes output:** `/home/ruben/obsidian-vault/inbox/Session-YYYY-MM-DD-HH-MM-topic-slug.md` with frontmatter. The topic-slug is a 2-5 word hyphenated description derived from the session content (e.g. `wand-focus-audit`, `atm10-guide-research`). H1 heading follows the same pattern: `# Session-YYYY-MM-DD-HH-MM — Descriptive Title`.

**Tools:** `["terminal", "file", "session_search"]` — minimal set for efficiency.
