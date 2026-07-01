# Hermes Maintenance Script Pitfalls

Recurring bugs and fixes encountered in Hermes maintenance scripts (cron jobs, archive scripts, DB maintenance). These patterns apply across any Python script that processes Hermes data (sessions.json, state.db, config files).

## 1. Naive vs Timezone-Aware Datetime Comparison

**Symptom:** `TypeError: can't compare offset-naive and offset-aware datetimes` when comparing a parsed timestamp to `datetime.now(timezone.utc)`.

**Root cause:** Hermes session timestamps in `sessions.json` may or may not include timezone info. `datetime.fromisoformat("2025-06-17T09:37:27.001155")` returns a **naive** datetime, while `datetime.now(timezone.utc)` returns an **aware** datetime. Python 3.x refuses to compare them.

**Fix pattern — always normalize to UTC after parsing:**

```python
from datetime import datetime, timezone

created = data.get("created_at") or data.get("started_at") or data.get("timestamp")
if created:
    try:
        created_dt = datetime.fromisoformat(str(created).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        created_dt = None

# CRITICAL: some timestamps lack timezone — attach UTC as default
if created_dt and created_dt.tzinfo is None:
    created_dt = created_dt.replace(tzinfo=timezone.utc)
```

The `.replace("Z", "+00:00")` trick handles ISO-8601 `Z` suffixes, but timestamps without any offset (e.g. `2025-06-17T09:37:27`) still produce naive objects. The explicit `tzinfo is None` check is the reliable fix.

## 2. `sqlite3` CLI Binary May Be Missing

**Symptom:** `sqlite3: command not found` when running maintenance scripts.

**Root cause:** Only `libsqlite3-0` (the C library) may be installed — not the `sqlite3` CLI package. Installing the CLI requires `sudo apt install sqlite3`, which may not be available in automated/headless contexts.

**Fix pattern — use Python's built-in `sqlite3` module instead:**

```bash
# Instead of: sqlite3 "$STATE_DB" "VACUUM;"
python3 -c "
import sqlite3
conn = sqlite3.connect('$STATE_DB')
conn.execute('VACUUM')
conn.close()
print('vacuum complete')
"
```

Python's `sqlite3` module is always available (it's in the standard library and uses the same `libsqlite3-0` that's already installed). This avoids an external dependency entirely.

**Also works for any SQL operation:**

```bash
python3 -c "
import sqlite3
db = sqlite3.connect('/home/user/.hermes/state.db')
rows = db.execute('SELECT COUNT(*) FROM sessions WHERE archived = 0').fetchall()
print(f'Active sessions: {rows[0][0]}')
db.close()
"
```

## 3. Session Archive Script

Location: `~/.hermes/scripts/archive-sessions.sh`

Archives sessions older than 90 days from `~/.hermes/sessions/sessions.json` into compressed JSONL archives under `~/.hermes/sessions/archive/`, then vacuums `state.db`. Both pitfall fixes above were applied to this script. Run it via cron monthly — it's safe to run more often (it's idempotent).
