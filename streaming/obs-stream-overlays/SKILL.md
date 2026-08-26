---
name: obs-stream-overlays
description: Build and iterate OBS/Twitch stream overlays as HTML/CSS/JS browser sources — config-file pattern (Local File can't use URL params), scene-per-file, 4K transparent design, Twitch IRC chat, follower/sub alerts, headless-Chrome screenshot verification.
---

# OBS Stream Overlays (HTML/CSS/JS browser sources)

## When to use
- Building or iterating a stream overlay for OBS Studio / Twitch / YouTube: alerts, on-screen chat, now-playing pill, webcam frame, latest-follower widget, Starting Soon / BRB scenes.
- Wiring real data into an overlay (Twitch chat, follower/sub notifications).

## Architecture that works
- **One browser source per scene.** 4K native (3840×2160); OBS scales down cleanly to 1080p. Transparent `html, body` background so gameplay shows through.
- **Single accent color** via a `--accent` CSS variable (+ `--accent-dim` for translucent borders/glows) drives the whole theme — change one value to restyle everything.
- **Scene-per-file**, not one file + `?scene=` param: `index.html` (game), `starting.html`, `brb.html`. Each becomes its own OBS browser source (Local File).

## ⚠️ CRITICAL PITFALL: OBS "Local File" mode cannot use URL query params
"Local File" points at a filesystem path, not a URL, so `?accent=…`, `?cam=1` etc. never reach the page. Two ways to handle config:
1. **Config file (preferred):** the page loads a `config.js` defining `window.OVERLAY_CONFIG = { accent, game, cam, handle, socials }`. User edits one file; no params needed. URL params remain as *overrides* only (they work in URL mode, not Local File).
2. **URL mode:** uncheck "Local File" and type `file:///C:/.../index.html?accent=7c3aed&cam=1`.

Splitting scenes into separate files removes the need for a `scene` param entirely in Local File mode.

## Patterns
- **Shared `script.js` with defensive guards** — every scene file includes the same script, so guard each DOM touch (`if (has("chat-messages"))`) to avoid null errors on scenes lacking elements (starting/brb have no chat / latest-follower / webcam).
- **Social icons from a JS array** (`name → svg` map) injected into `.js-socials` slots, so links/URLs live in one place (config.js) and aren't duplicated across three HTML files.
- **Alerts** = one centered absolutely-positioned div (shared by all scenes), shown via a CSS animation class; `showAlert()` removes+re-adds the class and forces a reflow (`void el.offsetWidth`) to restart the animation for rapid events.
- **Chat box** keeps the last N messages and auto-fades; use `textContent` (never `innerHTML`) for user content to avoid XSS.

## Verifying without OBS
Screenshot the overlay with agent-browser (see `browser-automation` skill). On this headless box: `--no-sandbox` + `set viewport 3840 2160` (default viewport is 1280×577). `~/.agent-browser/config.json` already sets the sandbox flags.
For side-by-side color/layout variants, build a labeled contact sheet with Pillow via `uv run --with pillow`.

## Real data (chat / followers / subs)
- **Twitch chat:** WebSocket IRC client — see `references/twitch-irc-and-alerts.md` for the working connector.
- **Followers/subs/latest-follower:** a `postMessage` protocol (see reference). Caveat: OBS browser sources are separate CEF instances and can't postMessage each other directly — for StreamElements/Streamlabs the overlay itself usually becomes the "custom widget" so their SDK fires events inside the page.

## This user's setup (Ruben)
- Handle **@Oathless**. Streams **Minecraft + Smite 2**; **no webcam yet** (frame toggleable, off by default).
- Project: `/home/ruben/stream-overlay` → `git.oathless.dev/oathless/stream-overlay.git` (remote `forgejo`).
- OBS runs on **Windows**; files at `C:/Users/ruben/Documents/stream-overlay/`. After edits, user `git pull`s / copies files there. **Remind them to copy ALL files** (html + css + js + config.js), not just the entry HTML.

## Pitfalls
- Don't commit a real `chat_token` to git — keep it commented/empty in config.js and warn the user (it's a secret).
- OBS applies its own default "Custom CSS" (`body { background-color: rgba(0,0,0,0); … }`) — harmless and matches the transparent intent; don't fight it.
