# Visual verification: screenshots → contact sheet → vision_analyze

When a task needs "show me all variants" or side-by-side comparison of multiple
rendered states, screenshot each, then compose a labeled contact sheet. Ruben
reviews these for feedback (colors, layouts).

## Screenshot many variants (agent-browser)
The daemon persists across a loop — `open` re-navigates, the viewport setting survives:
```bash
export PATH="$HOME/.hermes/node/bin:$PATH"; export AGENT_BROWSER_ARGS="--no-sandbox,--disable-gpu"
agent-browser close --all 2>/dev/null; sleep 2
agent-browser --args "--no-sandbox,--disable-gpu" open "file:///path/index.html?variant=1"
agent-browser set viewport 3840 2160
for pair in "name:value" ...; do
  agent-browser open "file:///path/index.html?param=$value"
  agent-browser set viewport 3840 2160; sleep 1
  agent-browser screenshot "/tmp/variants/$name.png"
done
agent-browser close --all
```

## Runtime config checks via eval
Confirm a page actually read its JS config / a hide flag took effect, without
eyeballing pixels:
```bash
agent-browser eval "JSON.stringify({accent: getComputedStyle(document.documentElement).getPropertyValue('--accent').trim(), hidden: getComputedStyle(document.getElementById('x')).display})"
```
Essential for JS-driven config files (e.g. an OBS overlay `config.js`).

## Contact sheet (no ImageMagick)
ImageMagick is NOT installed and system Python has no Pillow on this box — use uv:
```bash
uv run --with pillow python3 /tmp/montage.py
```
Python recipe: `Image.open(...).convert("RGB").resize((W,H), Image.LANCZOS)` per tile,
paste into a grid on `Image.new("RGB", (W,H), bg)`, draw labels with `ImageDraw` +
a system TTF (`/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf`), save.
Then `vision_analyze` the sheet to sanity-check labels/colors, and send via MEDIA.
