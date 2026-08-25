---
name: stream-overlays
description: Build and iterate on OBS browser-source stream overlays (Twitch/YouTube) — transparent HTML/CSS/JS with now-playing pill, webcam frame, social bar, and a postMessage alert system. Covers OBS wiring, single-accent theming, per-scene game overrides, and verification.
---

# Stream Overlays (OBS browser source)

## When to use
- User asks to create, restyle, or extend a stream overlay (Twitch/YouTube/OBS).
- Any "now playing", "webcam frame", "socials bar", "follower/sub alert", "starting soon / BRB scene" request.
- Wiring alerts to StreamElements / Streamlabs custom widgets.

## Core pattern (this is the right default shape)
One **browser source** = one OBS source to manage. Not a pile of image files.

1. **Transparent background** — `html, body { background: transparent }` so it layers over gameplay.
2. **Fixed canvas** — `1920x1080`, elements absolutely positioned in corners. Scales to any stream output.
3. **One accent color drives the theme** — a `--accent` CSS variable in `:root`. Recoloring the whole overlay = changing one line. Offer this to the user as the "one knob" for theming.
4. **Game-agnostic theme by default** unless the user names a single game. Users who stream multiple games (see below) don't want a Minecraft-specific skin.

Standard element set (all optional, add as needed):
- **Now-playing pill** (top-left): pulsing live dot + game label.
- **Webcam frame** (bottom-left): styled border + nameplate under a 16:9 box. The camera itself is added in OBS on top of / sized to the box — the HTML just draws the frame.
- **Social bar** (bottom-right): inline-SVG icons (Twitch/X/YouTube/Discord), no external CDN so it works offline in OBS.
- **Alert box** (centered): hidden by default, shown by JS.

## OBS wiring (exact steps)
1. Sources → **+** → **Browser** → name it "Overlay".
2. Tick **Local file**, browse to `index.html`.
3. Width `1920`, Height `1080`.
4. Place the source **above** game capture.
5. Per-scene game label: append `?game=Smite%202` to the local-file URL — no code edit needed.

## Alert system
Expose `window.showAlert(title, message)` and listen for `postMessage` so external widgets (StreamElements/Streamlabs custom widget) can trigger it:
```js
window.addEventListener("message", (e) => {
  const d = e.data;
  if (d && typeof d === "object" && d.title !== undefined) showAlert(d.title, d.message || "");
});
```
- Preview with `?test=1` in the URL (fires a demo alert after ~800ms).
- The CSS animation carries fade-in/fade-out; JS just toggles a `.show` class and force-reflows (`void el.offsetWidth`) so rapid alerts still animate.

## Verification — what actually works
- `node --check script.js` + grep that every `getElementById` id exists in the HTML = cheap sanity checks, always do these.
- **Visual verification on this user's headless homelab is blocked** unless GTK/X11 libs are installed — see `browser-automation` skill (the `libatk-1.0.so.0` pitfall). Don't burn time on it; the honest path is: deliver the files, have the user drop `index.html` into OBS (30s) and look at it, which is the real test anyway.
- Note: a transparent overlay screenshots as white/black on a bare page — if you DO render it headlessly, put a test background behind it first.

## User context
- Streams **Minecraft + Smite 2** on **OBS Studio** → keep themes game-agnostic (dark + one accent) unless told otherwise.
- Handle **@Oathless** (Minecraft account is "0athless" with a zero). Placeholder socials default to Oathless.
- Default accent is amber-gold `#ffb800`; offer purple `#7c3aed` as the Smite "god" alternative.

## Templates (copy & modify)
- `templates/index.html` — layout (now-playing, webcam frame, socials, alert)
- `templates/style.css` — theme, `--accent` variable drives everything
- `templates/script.js` — `?game=` override + postMessage alert system

Start a new overlay by copying these three into a new dir and editing `--accent`, the `@Oathless` handle, and the four `href`s.
