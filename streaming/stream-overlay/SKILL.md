---
name: stream-overlay
description: Build, configure, and verify OBS browser-source stream overlays (HTML/CSS/JS) — 4K design, per-scene HTML files, config.js-driven (no URL params in OBS Local File mode), chat/alerts/follower widgets, and headless render verification.
---

# Stream Overlay (OBS browser source)

## When to use
- Building or editing Ruben's OBS stream overlay, or any HTML/CSS/JS browser-source overlay.
- Adding scenes (Starting Soon / BRB), widgets (chat, latest follower, alerts, webcam frame), or wiring real data (Twitch chat, StreamElements).
- "Show me variants", "make it 4K", "add a webcam frame", "wire alerts".

## The project
- Local: `/home/ruben/stream-overlay`
- Repo: `git.oathless.dev/oathless/stream-overlay` (private; remote name `forgejo` — see `go-vue-fullstack` skill).
- OBS runs on **Windows** (files copied to `C:/Users/ruben/Documents/stream-overlay/`). Edit on the Linux homelab, commit + push, user pulls/copies.

## Architecture (single source, per-scene files)
- `config.js` — ALL user settings (accent, game, cam, handle, show flags, socials). This is what Ruben edits.
- `index.html` / `starting.html` / `brb.html` — one file per OBS scene. Each sets `data-scene` on `<body>` and includes only its own scene markup + shared `<script src="config.js">` + `<script src="script.js">`.
- `script.js` — logic only (don't edit): reads `window.OVERLAY_CONFIG`, renders socials, applies accent, show/hide widgets, alerts, chat, Twitch IRC. Guard every DOM access (`if (has("id")) …`) because scene files don't all contain every element.
- `style.css` — 4K theme. `--accent` CSS variable drives the whole color scheme; `--accent-dim` is its 0.35-alpha variant.

## PITFALL: OBS "Local File" mode cannot take query params
OBS Local File points at a filesystem path, NOT a URL — `?accent=...` never reaches the page. Ruben hit this ("I cannot add params").
- Fix: put all settings in `config.js`, read at runtime. No params needed.
- Fix for scenes: one HTML file per scene (`?scene=starting` doesn't work in Local File either).
- URL params still work as OVERRIDES if the user unchecks "Local File" and uses a `file://` URL with `?accent=` etc.

## Design rules (Ruben's preferences)
- 4K native (3840×2160); OBS scales down to 1080p output cleanly.
- Webcam frame OFF by default, toggleable (`cam: true` in config / `?cam=1`). Ruben has no cam yet.
- Every widget toggleable via `config.js` `show: { nowPlaying, latestFollower, chat, goal, socials }`. Feature toggles too: `mythical`, `cam`, `goal`, `sound`.
- **Socials MUST show handle text + icon, not logos alone** — a bare Twitch logo tells a viewer nothing. Ruben called this out directly ("why even have the social logos there").
- Minimal/decorative-lean: Ruben questions the value of anything non-functional ("why even have them there").
- **Avoid the "template" look** — this is what makes him say "this feels off": system fonts (Segoe UI/Inter), dead-center symmetric layouts, and the accent color scattered everywhere all read as cheap. Use a real display font (Cinzel / Montserrat / Bebas Neue), ONE strong focal point, and restraint with the accent color.
- **Stop tweaking when a design "feels off" after one round.** Offer 2–4 genuinely distinct directions (different font + layout + palette) rendered side-by-side and let him pick — do not keep guessing with incremental tweaks.

## More pitfalls
- **Alert sound needs "Control audio via OBS"** ticked on the browser source, or the chime never reaches the stream mixer.
- **Anchor tags render with a default blue underline** in OBS — always `text-decoration: none` on `.social` / link styling.
- **Custom fonts must be self-hosted** (`@font-face` with a downloaded `.woff2`) for offline reliability in OBS; Google Fonts `@import` works for agent-browser previews but breaks without internet.

## config.js shape
```js
window.OVERLAY_CONFIG = {
  accent: "ffb800",            // hex, no #
  game: "Minecraft",           // Now Playing label
  cam: false,                  // webcam frame
  sound: true,                 // alert chime: true | "file.mp3" | false
  mythical: true,              // silhouettes/animations on full-screen scenes (false = clean)
  handle: "@Oathless",
  nextStream: "",              // "next stream" line on the outro screen ("" = hidden)
  show: { nowPlaying: true, latestFollower: true, chat: true, goal: true, socials: false },
  goal: { label: "Follower Goal", current: 43, target: 100 },  // top-center goal bar
  socials: [{ name, url, handle }],   // icon auto-matched by name (Twitch/X/YouTube/Discord)
};
```

## Scenes (one file each, all `3840×2160` OBS sources)
- `index.html` (in-game overlay) · `starting.html` · `brb.html` · `outro.html` ("Thanks for watching" + next-stream line) · `adbreak.html` · `tech.html`.
- Full-screen scenes get optional mythical decorations (columns/lightning/particles) injected by JS when `mythical` is true — toggle off for the clean look.

## Data wiring (follower / sub / chat)
- Overlay exposes a `postMessage` API: `{type:"follower",name}`, `{type:"sub",name,tier}`, `{type:"chat",user,message,color}`, `{type:"latest",name}`, or generic `{title,message}`.
- Followers/subs → StreamElements/Streamlabs "Custom Widget" forwarding into `postMessage`.
- Chat → built-in Twitch IRC client (`wss://irc-ws.chat.twitch.tv:443`), gated by `channel`/`nick`/`chat_token` in config. `chat_token` is a SECRET — keep it out of public git.
- `?demo=1` simulates chat + follower + sub for verification.

## Verification workflow (headless)
- Render each HTML with agent-browser → `set viewport 3840 2160` → `screenshot` → `vision_analyze` (see `browser-automation` skill for the `--no-sandbox` + viewport setup).
- Runtime checks: `agent-browser eval "JSON.stringify({...})"` to confirm config loaded / a hide flag took effect (`getComputedStyle(el).display === "none"`).
- "Show me variants" (accent colors etc.): loop render + screenshot, then build a labeled contact sheet with Pillow via `uv run --with pillow python3` (ImageMagick not installed). See `browser-automation` `references/visual-verification.md`.
