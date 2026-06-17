---
name: hermes-operations
description: Config tuning, gateway setup, and provider management for Hermes Agent itself. Covers approvals, model/provider switching, Discord/Telegram setup, and config discovery patterns.
triggers:
  - Configuring or tuning Hermes Agent behavior (approvals, timeouts, modes)
  - Setting up messaging platforms (Discord, Telegram) via gateway
  - Adding, switching, or managing LLM providers and models
  - Questions about "how do I configure X in Hermes"
  - Provider fallback chain management
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