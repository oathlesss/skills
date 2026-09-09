---
name: hermes-mcp-wiring
description: >
  Wire an MCP (Model Context Protocol) server into Hermes Agent — config, SDK
  install, CLI quirks, and smoke-testing the connection. Use when `hermes mcp add`
  fails, when adding an MCP server to a project, or when verifying an MCP chain.
---

# Wire an MCP server into Hermes

Use when connecting Hermes to an external MCP server (stdio or HTTP), or when
`hermes mcp add` misbehaves.

## Core commands
- Add (discovery-first): `hermes mcp add <name> --command npx --args <pkg...> [--env KEY=VALUE]`
- List: `hermes mcp list`  ·  Test: `hermes mcp test <name>`  ·  Remove: `hermes mcp remove <name>`
- Configure tool selection: `hermes mcp configure <name>`

## Critical gotchas

### 1. `~/.hermes/config.yaml` is security-guarded
The file/patch tools REFUSE to edit it ("Agent cannot modify security-sensitive
configuration"). Always use `hermes mcp add` / `hermes config`. The CLI writes the
`mcp_servers.<name>` block correctly.

### 2. `--args` chokes on dash-prefixed values
`hermes mcp add x --command npx --args -y pkg` → argparse error
("unrecognized arguments: -y") because nargs stops at option-like tokens.
Workarounds: drop the flag (npx packages are cached after first run, so bare
`npx pkg` no longer prompts), or bind it with `--args=-y`.

### 3. MCP SDK install can silently drop other extras
`hermes mcp add` fails with "requires the 'mcp' Python SDK" when it's missing.
Reinstall with the FULL extra, NOT `[mcp]`:
- WRONG: `uv tool install 'hermes-agent[mcp]' --reinstall` → drops yt-dlp, s3transfer, tabulate, etc.
- RIGHT: `uv tool install 'hermes-agent[all]==<version>' --reinstall` — `[all]` includes `[mcp]`.
- If the original install had orphan packages not in `[all]`, restore with `--with`:
  `uv tool install 'hermes-agent[all]==X' --reinstall --with yt-dlp --with s3transfer --with tabulate`
- Verify: `/home/ruben/.local/share/uv/tools/hermes-agent/bin/python -c "import mcp"`

### 4. Smoke-test the chain without a client (raw JSON-RPC)
Launch the server, speak newline-delimited stdio JSON-RPC: `initialize` →
`notifications/initialized` → `tools/list` → `tools/call`. A working Python harness
pattern (subprocess + select, parse lines, match on `id`) is in /tmp/mcp_smoke.py.

## godot-mcp (satelliteoflove/godot-mcp) specifics
- Install + enable: `npx @satelliteoflove/godot-mcp --install-addon <project>`, then add
  `[editor_plugins]\nenabled=PackedStringArray("res://addons/godot_mcp/plugin.cfg")` to project.godot.
- The editor must be OPEN (not headless); bridge listens on ws://127.0.0.1:6550.
- Scene/node/editor-state reads and project-info work headless; `run`-game/playtest needs a
  real display (the game subprocess can't create a DisplayServer without one).
- Disable local telemetry: `--env GODOT_MCP_USAGE_LOG=0`.
