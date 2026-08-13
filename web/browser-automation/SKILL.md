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
