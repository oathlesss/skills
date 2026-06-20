---
name: hermes-operations
description: Config tuning, gateway setup, provider management, and personality customization for Hermes Agent itself. Covers approvals, model/provider switching, Discord/Telegram setup, SOUL.md identity, and config discovery patterns.
triggers:
  - Configuring or tuning Hermes Agent behavior (approvals, timeouts, modes)
  - Setting up messaging platforms (Discord, Telegram) via gateway
  - Adding, switching, or managing LLM providers and models
  - Questions about "how do I configure X in Hermes"
  - Provider fallback chain management
  - Customizing Hermes' identity, personality, tone, or behavioral directives via SOUL.md
  - Questions about making Hermes always do something (meta-prompting, style rules, etc.)
  - Questions about secrets, credentials, tokens, or encrypted files — "where is X" or "how do I find X" for secrets
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