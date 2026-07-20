---
name: hermes-operations
description: Config tuning, gateway setup, provider management, personality customization, and GitHub integration for Hermes Agent itself. Covers approvals, model/provider switching, Discord/Telegram setup, SOUL.md identity, config discovery, secrets handling, and GitHub `gh` CLI setup with fine-grained PAT.
triggers:
  - Configuring or tuning Hermes Agent behavior (approvals, timeouts, modes)
  - Setting up messaging platforms (Discord, Telegram) via gateway
  - Adding, switching, or managing LLM providers and models
  - Questions about "how do I configure X in Hermes"
  - Provider fallback chain management
  - Customizing Hermes' identity, personality, tone, or behavioral directives via SOUL.md
  - Questions about making Hermes always do something (meta-prompting, style rules, etc.)
  - Questions about secrets, credentials, tokens, or encrypted files — "where is X" or "how do I find X" for secrets
  - Connecting Hermes to GitHub — `gh` CLI setup, fine-grained PAT, token scoping, org isolation
  - GitHub token or auth questions, skills sync or backup to GitHub
  - Resetting / starting fresh on a repo ("reset the repository", "start fresh")
  - Creating or managing GitHub issues / labels / milestones via `gh`
  - Forgejo / Gitea self-hosted Git — see references/forgejo-api-quirks.md
---

# Hermes Agent Operations

## Smart Approvals

Hermes has an LLM-powered approval mode that evaluates command safety automatically instead of asking you to approve every command.

```bash
# Check current mode
hermes config show | grep -A3 approvals

# Enable smart approvals
hermes config set approvals.mode smart

# Disable (every command needs manual approval)
hermes config set approvals.mode manual
```

Modes:
- `manual` — every command requires user approval
- `smart` — an LLM (configured under `auxiliary.approval`) evaluates risk; routine commands auto-approve, dangerous ones still prompt
- `deny` — blocks all commands (used for cron)

The approval model defaults to `auto` (same provider as your main model). To use a different model for approval evaluations:

```bash
hermes config set auxiliary.approval.provider openrouter
hermes config set auxiliary.approval.model anthropic/claude-haiku
```

## Discord Gateway Setup

Three-step process to connect Hermes to Discord:

**Step 1 — Get a bot token:**
- Go to https://discord.com/developers/applications
- Create an application, add a bot user, copy the token

**Step 2 — Configure (interactive):**
```bash
hermes gateway setup
```
Select Discord from the platform list. It prompts for the bot token and writes `discord.bot_token` to config.

**Step 3 — Install and start the gateway service:**
```bash
hermes gateway install    # installs systemd service
hermes gateway start      # starts it
hermes gateway status     # verify it's running
```

Key config options in `config.yaml` under `discord:`:

| Setting | Default | Effect |
|---------|---------|--------|
| `require_mention` | true | Only respond when @mentioned |
| `allowed_channels` | '' | Restrict to specific channel IDs (comma-separated) |
| `auto_thread` | true | Create threads for conversations |
| `reactions` | true | Add emoji reactions during processing |

## Discord Gateway Troubleshooting

**⚠️ PITFALL: `PrivilegedIntentsRequired` masquerades as timeout.** When the Discord gateway log shows `discord connect timed out after 30s`, the real error is often `discord.errors.PrivilegedIntentsRequired` — the bot is requesting intents that aren't enabled in the Discord Developer Portal. The gateway summary only shows "timed out" because the async exception isn't surfaced to the reconnect loop. Always check the full journal for the real error:

```bash
journalctl --user -u hermes-gateway.service --no-pager -n 100 | grep -A5 Privileged
```

**Fix:** Go to https://discord.com/developers/applications → your app → Bot → "Privileged Gateway Intents" and enable:
- **Message Content Intent** (required — bot can't read messages without it)
- **Server Members Intent** (usually needed)
- **Presence Intent** (usually needed)

Then restart: `hermes gateway restart`.

**Bot invite URL** (after setting up the bot, invite it to your server):
```
https://discord.com/api/oauth2/authorize?client_id=YOUR_APP_ID&permissions=326417526848&scope=bot
```
That permissions number covers: Read/Send Messages, Embed Links, Attach Files, Read Message History, Threads, Mentions, Slash Commands.

## Desktop App & Remote Dashboard

Hermes Desktop is a native Electron app (macOS/Linux/Windows) that can connect to a remote Hermes instance running on a homelab/VPS. It uses the **dashboard** as its backend — a separate process from the gateway.

### Enabling the dashboard on the remote host

The dashboard listens on port 9119 by default and must be started alongside the gateway:

```bash
# Start dashboard bound to all interfaces (not just localhost)
hermes dashboard --no-open --host 0.0.0.0 --port 9119
```

The command prints a **session token** on startup — copy this. It's what the desktop app uses to authenticate.

**⚠️ PITFALL: Dashboard is separate from gateway.** `hermes gateway run` handles messaging platforms (Discord, Telegram). `hermes dashboard` provides the web UI and remote-desktop API. Both must be running for Desktop to connect. The dashboard does NOT auto-start when the gateway starts.

### Installing Desktop on the client machine

Download from [GitHub Releases](https://github.com/NousResearch/hermes-agent/releases) — pick the `.AppImage`, `.deb`, `.dmg`, or `.exe` for your platform.

### Connecting Desktop to the remote dashboard

In the Desktop app:
1. **Settings → Gateway → Remote gateway**
2. Enter:
   - **Remote URL:** `http://<host-ip>:9119` (e.g. `http://100.64.x.x:9119`)
   - **Session Token:** the token printed by `hermes dashboard`
3. Click **Test Remote** → Save

### Security

Port 9119 has **no built-in auth** beyond the session token. Do not expose it to the open internet. Recommended approaches:

| Method | Setup | Best for |
|--------|-------|----------|
| **Tailscale** | Desktop connects to host's Tailscale IP; no port forwarding needed | Already using Tailscale mesh |
| **SSH tunnel** | `ssh -L 9119:localhost:9119 user@homelab` on client, connect to `http://localhost:9119` | Quick, no extra software |
| **Caddy reverse proxy** | Add HTTPS + basic auth in front of port 9119 | When Tailscale/SSH isn't an option |

### Verification

```bash
# On the remote host — check dashboard is listening
ss -tlnp | grep 9119

# Quick connectivity test from client
curl http://<host-ip>:9119/api/health
```

### Session token persistence

For long-running setups, pin the session token so it survives dashboard restarts:

```bash
# Set in the dashboard's environment
export HERMES_DASHBOARD_SESSION_TOKEN="your-token-here"
hermes dashboard --no-open --host 0.0.0.0 --port 9119
```

Without this, each dashboard restart generates a new token and Desktop must be reconfigured.

## Provider & Model Management

Hermes has one active primary provider/model. Switch between them:

```bash
# Interactive picker — browse all available models
hermes model

# Set specific model+provider
hermes config set model.provider deepseek
hermes config set model.default deepseek-chat

# Per-session override (flags)
hermes chat --provider openrouter --model deepseek/deepseek-v4-pro
```

### Fallback Chain

Fallback providers kick in automatically when the primary fails (rate limits, timeouts, connection errors). Not for on-demand model switching — for error recovery only.

```bash
hermes fallback add      # interactive picker: choose fallback provider+model
hermes fallback list     # show current chain
hermes fallback remove   # remove one entry
hermes fallback clear    # remove all
```

**Non-interactive alternative (for scripts/automation):**
```bash
hermes config set fallback_providers '[{"provider":"openrouter","model":"anthropic/claude-sonnet-4"}]'
```
Use this when the interactive picker is unavailable or you're setting up via config management.

### Multiple API Keys

API keys live in `~/.hermes/.env`:

```
OPENROUTER_API_KEY=sk-or-...
DEEPSEEK_API_KEY=sk-...
```

Switching providers re-uses the already-configured keys — no re-auth needed when you already have the key set.

**⚠️ PITFALL: `.env` is write-protected.** The `write_file` tool and direct shell writes to `~/.hermes/.env` are blocked. To store new credentials, use `hermes config set`:

```bash
hermes config set github.token ghp_...
```

This writes to `~/.hermes/config.yaml` instead. For provider API keys that Hermes is already wired to read from `.env`, the user should create/edit `.env` manually on the machine.

## Config Discovery

To explore available config keys:

```bash
hermes config show              # full config dump
hermes config show | grep -i <keyword>  # search for relevant section
hermes config set <key> <value> # set any key
```

**⚠️ PITFALL: `hermes config get` returns exit code 2 for unset keys.** Don't interpret exit code 2 as "command failed" — it means the key has no configured value (i.e., using defaults). Use `hermes config show | grep` to see what's actually set vs. defaulted.

## Secrets & Credential Handling

**⚠️ PITFALL: Never access, decrypt, or read secrets without explicit permission.** When the user asks "where is X" or "how do I find X" for a secret (SOPS-encrypted files, `.env` files, tokens, passwords, API keys), give the location and the command to run — do NOT execute the decryption or read the value yourself. Only decrypt when the user explicitly asks for the value (e.g. "what is my token?" or "show me the secret").

**Why:** `sops --decrypt` and similar commands reveal credentials to the agent's context, which the user may not want. The user may be asking about workflow/logistics, not the secret itself. Err on the side of not accessing secrets.

**Safe response pattern:** "The token is at `path/to/file.sops`. Decrypt it with: `sops --input-type dotenv --output-type dotenv --decrypt path/to/file.sops`"

## GitHub Integration (gh CLI + Fine-Grained PAT)

Connect Hermes to GitHub for repo management, issue tracking, PRs, and skills sync. The full setup workflow (install `gh`, create FG-PAT, auth, verify org isolation, credential helper, notification cron) is in:

→ `references/hermes-github-integration.md`

**Quick-start after `gh` is installed and authed:**

```bash
# Git push/pull — works after `gh auth setup-git`
git push origin main

# gh CLI — needs GH_TOKEN env var
export GH_TOKEN=$(python3 -c "import yaml; print(yaml.safe_load(open('$HOME/.hermes/config.yaml'))['github']['token'])")
gh repo list --limit 10
gh issue create --title "Bug report" --body "Description"
```

**⚠️ PITFALL: Smart approval blocks tokens in shell commands. Use `execute_code` for `gh auth login --with-token`.** See `references/python-3.14-subprocess-quirk.md` for the Python 3.14 `subprocess.run` encoding change.

**Forgejo / Gitea:** The `gh` CLI is GitHub-specific. For self-hosted Forgejo (like `git.oathless.dev`), use curl + Bearer token. See `references/forgejo-api-quirks.md` for the three critical API differences (auth, labels-on-create, PUT-vs-PATCH).

**Repo operations:** See `references/repo-fresh-start.md` (archive + wipe), `references/issue-management.md` (labels, milestones), `references/export-skills-to-repo.md` (skills export), `references/skills-sync-setup.md` (auto-sync cron).

## Session & Context Health

Config keys for keeping Hermes context fresh and manageable:

```bash
# Session reset — fresh context daily + after 24h idle
hermes config set session_reset.mode both
hermes config set session_reset.idle_minutes 1440
hermes config set session_reset.at_hour 4

# Smart compression — summarise long conversations at 50% context usage
hermes config set compression.enabled true
hermes config set compression.threshold 0.50
hermes config set compression.target_ratio 0.20
```

These are "set and forget" — they prevent context bloat and stale sessions without ongoing attention. The dossier used these values for months on the cloud VM instance without issues.

## Session Database & Cronjobs

Session data lives in SQLite at `~/.hermes/state.db`. Full schema (sessions + messages tables, all columns) and query patterns for finding inactive sessions, building summarization cronjobs, and programmatic access are documented in:

- `references/hermes-session-db.md`
- `references/hermes-github-integration.md` — full gh CLI + FG-PAT setup workflow: install, auth, org isolation, credential helper, cron polling
- `references/forgejo-api-quirks.md` — Forgejo/Gitea API differences vs GitHub (auth, labels, PUT vs PATCH)
- `references/export-skills-to-repo.md` — export skills from ~/.hermes/skills/ to a GitHub repo
- `references/skills-sync-setup.md` — 12-hour auto-sync cron for live skills directory
- `references/shell-script-patterns.md` — token extraction patterns for shell scripts
- `references/issue-management.md` — creating structured issues, labels, milestones via `gh`
- `references/repo-fresh-start.md` — archive current work, force-push orphan main
- `references/git-orphan-reset.md` — git orphan branch technique for repo reset
- `references/python-3.14-subprocess-quirk.md` — Python 3.14 `subprocess.run` encoding change

Common maintenance script pitfalls (datetime timezone handling, missing sqlite3 CLI) are documented in:

→ `references/hermes-maintenance-pitfalls.md`

Key patterns:
- **Inactivity detection:** `MAX(m.timestamp)` subquery with `HAVING last_ts < unixepoch() - N`
- **Cron agent access:** Use `terminal` (Python + sqlite3), not `execute_code` (blocked in cron context)
- **Deduplication:** Tracking file with one session ID per line, checked before each run
- **Minimal toolsets:** `["terminal", "file", "session_search"]` — only what the cronjob needs

## Personality & SOUL.md

`SOUL.md` is the agent's **primary identity file**. It occupies slot #1 of the system prompt — whatever you write there is injected verbatim into every conversation turn, before memory, before skills, before user messages. It's the most powerful mechanism for making Hermes consistently behave a certain way.

### Where it lives

```bash
~/.hermes/SOUL.md
# or $HERMES_HOME/SOUL.md for custom home directories
```

### How it works

- Hermes reads SOUL.md at session start and injects it directly into the system prompt
- No wrapper text is added — your content appears as-is
- Hermes seeds a default SOUL.md automatically if one doesn't exist
- Existing user SOUL.md files are **never overwritten** by Hermes
- SOUL.md loads only from HERMES_HOME, not from the working directory
- If SOUL.md is empty, the built-in Hermes Agent default identity is used instead

### When to use SOUL.md vs other mechanisms

| Mechanism | Use for | Persistence |
|-----------|---------|-------------|
| **SOUL.md** | Durable identity, tone, behavioral directives, meta-rules ("always do X") | Every session, every turn |
| **AGENTS.md** | Project conventions, architecture, code style rules | Per-project sessions |
| **Memory** | Facts about the user, environment, tool quirks | Cross-session recall |
| **Skills** | Procedural workflows, multi-step task patterns | Loaded on demand |
| **Personality presets** | Temporary session-level overlays (`/personality`) | Current session only |

### Examples of good SOUL.md content

- **Identity**: "You are Diaktoros, a direct and efficient assistant..."
- **Behavioral directives**: "Before answering, always think through your approach first..."
- **Tone rules**: "Be direct without being cold. Prefer substance over filler."
- **Anti-patterns**: "Never fabricate. Never overexplain obvious things."
- **Communication style**: "Keep explanations compact unless depth is useful."

### Examples of what NOT to put in SOUL.md

- One-off project instructions (use AGENTS.md instead)
- File paths and repo conventions (use AGENTS.md instead)
- Temporary workflow details (use a skill or AGENTS.md instead)
- Environment-specific facts (use memory instead)

### Editing SOUL.md

Edit it directly — no Hermes CLI command needed:

```bash
# Open in your editor
vim ~/.hermes/SOUL.md
nano ~/.hermes/SOUL.md
```

Changes take effect on the **next session** or after `/new` — not mid-session.

### Verifying it's loaded

```bash
# Check the file exists and has content
cat ~/.hermes/SOUL.md

# Verify personality config (should show 'none' unless a preset is active)
hermes config show | grep -i personality
```

### Common use cases

- **Meta-prompting**: Add a directive to always think through approach before answering
- **Name/identity**: Replace "Hermes Agent" with a custom name like "Diaktoros"
- **Style enforcement**: Mandate concise responses, prohibit certain patterns
- **Tool-use rules**: Require tool execution over description, ban fabrication
- **Domain posture**: "You are a pragmatic senior engineer" vs "You are a creative writer"

### ⚠️ PITFALL: SOUL.md not taking effect

If you edit SOUL.md but don't see changes:
1. SOUL.md is loaded at **session start** — use `/new` to start a fresh session
2. Check the file isn't empty (empty = fallback to default identity)
3. Check you're editing the right `HERMES_HOME` — `echo $HERMES_HOME` then check `$HERMES_HOME/SOUL.md`
4. Very large SOUL.md files are truncated at `context_file_max_chars` (default 20,000)