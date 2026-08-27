---
name: browser-automation
description: Drive a real headless browser from the CLI for smoke-testing web apps, JS-heavy scraping, form/login flows, and screenshots. Covers agent-browser (Vercel's ref-based CLI) — install, the sudo-apt dependency blocker on headless Linux, and the ref-based snapshot→click→fill workflow. Use when web_extract/web_search can't render client-side content or when you need to actually click through a running app.
---

# Browser Automation (agent-browser)

## When to use
- **Smoke-testing Ruben's web apps** (oathless.dev, fmtthis.dev, regex-playground, apichangelog, docs-enhancer) — real form flows, JS rendering, then screenshot → vision_analyze.
- **JS-heavy research** when `web_extract` fails (its DuckDuckGo backend is search-only, can't render SPA content).
- Form submission, login-gated scraping, "does this page actually render" checks.

## What agent-browser is
Rust CLI by Vercel Labs (`vercel-labs/agent-browser`). Key difference from Playwright/Selenium: `snapshot` returns a **compact accessibility tree with refs** (`@e1`, `@e2`…) instead of a DOM/JSON dump — ~90% fewer tokens, deterministic element selection. No CSS selectors or XPaths needed. 50+ commands (nav, forms, screenshots, network, storage, tabs, frames, video). Runs as a plain CLI you drive from `terminal` (also has an MCP mode, but CLI is the point).

## Install (headless Linux, no sudo for the browser itself)
```bash
npm install -g agent-browser     # downloads prebuilt native Rust binary
agent-browser install            # downloads Chrome for Testing — no sudo needed
```
- Node 24+/pnpm/Rust are **only** needed when building from source, NOT for the npm install.
- Chrome for Testing lands at `~/.agent-browser/browsers/chrome-<ver>/`.
- `agent-browser install --with-deps` auto-detects the apt package list for missing libs, but the `apt-get install` itself needs sudo.

## PITFALL: headless Chrome needs GTK/X11 system libs (sudo)
On a fresh Ubuntu server, Chrome for Testing will fail with:
`error while loading shared libraries: libatk-1.0.so.0: cannot open shared object file`
This is NOT an agent-browser bug — headless Chrome needs the GTK/X11/NSS libraries. This is the **one step that requires the user** (sudo needs their password; never ask for it — hand them the one-liner). Exact apt package list: `references/linux-deps.md`.

## PITFALL #2: after libs install, Chrome hits "No usable sandbox"
On Ubuntu with AppArmor restricting unprivileged user namespaces, headless Chrome
fails with `FATAL: ... No usable sandbox!` even after the GTK libs are installed.
Fix: launch Chrome with `--no-sandbox`. agent-browser passes browser args via the
**global** `--args` flag (comma-separated, placed BEFORE the subcommand):

```bash
agent-browser --args "--no-sandbox,--disable-gpu" open <url>
```

More robust options (survive daemon restarts):
```bash
export AGENT_BROWSER_ARGS="--no-sandbox,--disable-gpu"
# or ~/.agent-browser/config.json → {"args": "--no-sandbox,--disable-gpu"}
```
(`~/.agent-browser/config.json` is already written on this box.)

**Daemon gotcha:** agent-browser keeps a daemon alive between commands. `--args`
is silently IGNORED if a daemon is already running ("⚠ --args ignored: daemon
already running"). Kill it first: `agent-browser close --all`, then launch fresh.
Also, `open` with NO URL is flaky for sandbox — always pass the URL directly.

**Viewport gotcha:** default viewport is 1280×577, NOT 1920×1080. Set it explicitly
after loading the page: `agent-browser set viewport 1920 1080`.

**Scroll gotcha (SPA inner scroll containers):** `agent-browser scroll down <px>` scrolls the
WINDOW, not an app's inner scroll container. Vue/React SPAs typically scroll a
`<div class="overflow-y-auto">` (or similar) while `body`/`html` stays fixed — so `scroll`
"✓ Done"s but the screenshot keeps showing the top, and below-the-fold sections (a match
timeline, a footer table) never appear. Fix: scroll the container directly via eval, then
screenshot:

```bash
agent-browser eval "document.querySelector('.overflow-y-auto').scrollTop = 99999"
sleep 0.6
agent-browser screenshot below-fold.png
```

Verify the scroll actually moved by checking the screenshot's byte size changed vs the
pre-scroll one (identical size = nothing scrolled).

## Core workflow (ref-based)
```bash
agent-browser open <url>              # launch + navigate (aliases: goto, navigate)
agent-browser snapshot                # → accessibility tree with @e1 @e2 ...
agent-browser click @e2               # click by ref from snapshot
agent-browser fill @e3 "text"         # clear + fill by ref
agent-browser type @e4 "text"         # type without clearing
agent-browser get text @e1            # read text by ref
agent-browser read [url]              # agent-readable text of page / active tab
agent-browser screenshot page.png     # then vision_analyze it
agent-browser close
```
- **Clicks fail early** when another element covers the click point (consent banner, modal). Dismiss or interact with the covering element, re-`snapshot`, then retry the ref.
- Traditional selectors still work as fallback: `agent-browser click "#submit"`, `agent-browser find role button click --name "Submit"`.
- Full command surface: `references/agent-browser-commands.md`.

### PITFALL: refs go stale after SPA re-render (state-based nav)

In a state-based SPA (Vue/React view switching with `v-if`/`v-show`, no URL router), clicking a nav button re-renders the main content and rebuilds the accessibility tree, so every previously-snapshotted `@eN` ref becomes invalid — the next `click @eN` fails with `✗ Unknown ref: eN`. Always re-`snapshot` after any click that changes the view, then use the fresh refs.

Related: state-based SPAs can't be deep-linked — to capture a specific view you must click through it (snapshot → click → re-snapshot), not `open http://host/#/view`. When screenshotting several views, re-snapshot between each and confirm the new view actually rendered (a change in screenshot byte size is a cheap sanity check).

## This user's environment
- **npm global prefix is `~/.hermes/node`** → binary at `~/.hermes/node/bin/agent-browser`, which is NOT on the default PATH. Prepend: `export PATH="$HOME/.hermes/node/bin:$PATH"`.
- Homelab is Ubuntu 26.04, headless OptiPlex 3070 Micro. `sudo` requires interactive auth → give Ruben the apt one-liner to run himself.
- Primary use case = smoke-testing the Go+Vue stack (see `go-vue-fullstack` skill).

## Verification
```bash
export PATH="$HOME/.hermes/node/bin:$PATH"
agent-browser --version
agent-browser open example.com && agent-browser snapshot && agent-browser close
```
If Chrome exits code 127 with a `shared libraries` error, the apt deps step hasn't run yet.

For screenshotting many variants, runtime config checks via `eval`, and composing
labeled comparison contact sheets (Pillow via uv — no ImageMagick), see
`references/visual-verification.md`.

## Visual comparison (contact sheets)
When the task is "show me all the variants / compare these renders", screenshot each
variant to its own file (change the URL param between runs, reuse the same daemon), then
montage into ONE labeled contact sheet. ImageMagick is NOT installed on this box — use
Pillow via `uv`:

```bash
uv run --with pillow python3 scripts/make_contact_sheet.py \
  "Gold=/tmp/v1.png" "Purple=/tmp/v2.png" "Cyan=/tmp/v3.png" /tmp/sheet.png
```

Args are `label=path` pairs; a trailing bare `.png`/`.jpg` is the output path (default
`/tmp/contact-sheet.png`). Tiles left-to-right at ~640px each with a label bar — compact
enough to drop straight into chat. Script: `scripts/make_contact_sheet.py`.
