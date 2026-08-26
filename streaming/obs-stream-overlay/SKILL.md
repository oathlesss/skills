---
name: obs-stream-overlay
description: Build and iterate Ruben's 4K OBS stream overlay (HTML/CSS/JS browser sources at /home/ruben/stream-overlay). Covers the config.js-driven architecture, per-scene files, goal bar + alert sound, postMessage wiring to StreamElements/Streamlabs, the built-in Twitch IRC chat connector, and headless render verification.
---

# OBS Stream Overlay (Ruben)

Ruben streams Minecraft + Smite 2 on OBS Studio, handle `@Oathless` (no face cam yet,
plans to add one). Project lives at `/home/ruben/stream-overlay/` (repo
`git.oathless.dev/oathless/stream-overlay`, remote name `forgejo`), **4K native
(3840×2160)**, dark theme driven by one `--accent` color. Iterate on these files; never
rewrite the whole thing unless the user asks.

## Architecture — config.js, NOT URL params
- **`config.js` is the single config file.** OBS "Local File" mode points at a filesystem
  *path*, so `?accent=…` query params NEVER reach the page (Ruben hit this: "I cannot add
  params"). All settings live in `window.OVERLAY_CONFIG` in `config.js`. URL params still
  work as overrides if the user switches to a `file://` URL, but the default workflow is
  Local File + edit config.js.
- **One HTML file per scene** — `index.html` (in-game), `starting.html`, `brb.html`,
  `outro.html` ("thanks for watching" + `nextStream` line), `adbreak.html`, `tech.html`
  ("technical difficulties"). Each is its own OBS browser source. All of them share
  `config.js` + `style.css` + `script.js`. The
  `<body data-scene="…">` attribute selects the active scene; `script.js` only overrides it
  when `?scene=` is present.
- **`script.js` guards every DOM touch** (`const has = id => !!$(id)`) because scene files
  omit widgets the others don't have (starting.html has no chat / now-playing / goal). A
  null `getElementById().textContent` throw is the classic failure mode — always guard when
  adding elements.

## Config surface (config.js)
`accent` (6-digit hex), `game`, `cam` (bool), `sound` (`true` = WebAudio chime |
`"file.mp3"` | `false`), `handle`, `mythical` (bool — silhouettes/animations on the
full-screen scenes; `false` = clean), `nextStream` (outro line, `""` hides it),
`show{nowPlaying,latestFollower,chat,goal,socials}` (per-widget on/off),
`goal{label,current,target}`, `socials[{name,url,handle}]`. Full schema: repo `README.md`
+ `config.js`.

## Mythical decorations (full-screen scenes only)
`script.js` injects a `.mythical-deco` layer (Greek column silhouettes left/right, a
lightning-bolt watermark behind the title, ~14 rising ember particles, a pulsing glow)
into `.scene-starting/.scene-brb/.scene-outro/.scene-adbreak/.scene-tech` when
`config.mythical !== false`. Original mythological motifs, NOT Hi-Rez's copyrighted
Smite god art. For real Smite character backdrops, the user drops their own GIF/video as
an OBS background source behind the transparent overlay.

## In-game overlay elements
Now Playing (top-left) · Latest follower (top-right) · Goal bar (top-center) · Chat (left,
mid-height, last ~12 messages, 25s fade) · Webcam (bottom-left, `cam: true`) · Alerts
(center, over every scene). Socials live only on Starting Soon/BRB (see design prefs).

## Alert sound
- Default: synthesized C–E–G chime via Web Audio API — no audio file to manage. Reuse a
  single `AudioContext` (create lazily, `ctx.resume()` if suspended) rather than newing one
  per alert.
- Custom: `sound: "alert.mp3"` plays a local file.
- **"Control audio via OBS" must be ticked** on the browser source or the audio never
  reaches the stream (Ruben's source had it unchecked — flag this).

## Real data wiring
Two paths for follower/sub/goal events (full detail in repo `WIRING.md`): **StreamElements**
(third-party, fastest) or **Twitch EventSub WebSocket** (self-hosted — recommended for Ruben,
fits his homelab; NOT yet implemented in the overlay, offer to build it). Chat is already
built in (IRC below).
- **Followers / subs / latest-follower / goal / custom alerts** arrive via `postMessage`
  from a StreamElements/Streamlabs **Custom Widget**. Protocol in `script.js`:
  - `{type:"follower", name}` — updates latest-follower pill AND fires the alert
  - `{type:"sub"|"subscriber", name, tier}`
  - `{type:"chat", user, message, color}`
  - `{type:"latest", name}` — latest-follower only
  - `{type:"goal", current, target}` — updates the goal bar
  - generic `{title, message}`
- **Chat** uses a built-in Twitch IRC client: WebSocket to `wss://irc-ws.chat.twitch.tv:443`,
  send `CAP REQ :twitch.tv/tags twitch.tv/commands`, `PASS oauth:TOKEN`, `NICK <login>`,
  `JOIN #<channel>`; parse `PRIVMSG` + IRCv3 tags for `display-name`/`color`; answer
  `PING`→`PONG`; auto-reconnect on close. Token is **chat-scoped**, user generates it
  (twitchtokengenerator.com or Twitch dev console). NEVER generate or read their token; keep
  it out of public git.

## Design preferences (Ruben — embed these)
- **Compact widgets.** Nothing should take over the screen ("I don't want them to take up
  the entire screen"). Small pills / thin bars, edge/corner placement.
- **Social icons must show the handle TEXT, not just logos.** A bare logo tells viewers
  nothing; `icon + "twitch.tv/oathless"` is the useful form.
- **Socials only on Starting Soon/BRB, not in-game** (default `show.socials: false`).
- **Webcam frame off by default** (no camera yet); toggle `cam: true` when he gets one.
- **Keep clean variants available via a toggle, never by overwriting.** When he asks for an
  effect (e.g. mythical silhouettes) *and* "keep a copy without it", implement it as a config
  flag (`mythical: false` = clean) so both look modes live in one file — don't delete or fork
  the clean version. Git history also preserves the old clean commits.

## Verify renders (headless)
Use the agent-browser recipe from the `browser-automation` skill (sandbox + viewport flags):
```bash
export PATH="$HOME/.hermes/node/bin:$PATH"
export AGENT_BROWSER_ARGS="--no-sandbox,--disable-gpu"
agent-browser close --all; sleep 2
agent-browser --args "--no-sandbox,--disable-gpu" open "file:///home/ruben/stream-overlay/index.html"
agent-browser set viewport 3840 2160   # default viewport is 1280×577 — always set
agent-browser screenshot /tmp/overlay.png
agent-browser eval "JSON.stringify({cfg: !!window.OVERLAY_CONFIG, accent: getComputedStyle(document.documentElement).getPropertyValue('--accent')})"
```
Then `vision_analyze` the PNG. The `eval` proves config.js actually loaded (not just that
the page rendered). For a contact sheet of variants, downscale the 4K PNGs with Pillow
(`uv run --with pillow`).

## Pitfalls
- OBS browser source must be sized **3840×2160**; OBS downscales cleanly to 1080p (upscaling blurs).
- Alert box is centered, briefly covers the crosshair — standard; offer top/bottom placement if he objects.
- Use `textContent` (NOT `innerHTML`) for chat/alert user text — chat is untrusted input (XSS).
- Webcam frame is a styled placeholder; the user points their OBS camera source at it (or uses it decoratively).
- `script.js` lint check: `node --check script.js` (node at `~/.local/bin/node`).
