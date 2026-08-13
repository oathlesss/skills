# Headless Chrome — system libraries (Ubuntu)

Chrome for Testing fails to launch until these GTK/X11/NSS libraries are present.
This is the exact list `agent-browser install --with-deps` auto-detects on Ubuntu 26.04.

## One-liner for the user (sudo requires their password)
```bash
sudo apt-get update && sudo apt-get install -y libxcb-shm0 libx11-xcb1 libx11-6 libxcb1 libxext6 libxrandr2 libxcomposite1 libxcursor1 libxdamage1 libxfixes3 libxi6 libgtk-3-0t64 libpangocairo-1.0-0 libpango-1.0-0 libatk1.0-0t64 libcairo-gobject2 libcairo2 libgdk-pixbuf-2.0-0 libxrender1 libasound2t64 libfreetype6 libfontconfig1 libdbus-1-3 libnss3 libnspr4 libatk-bridge2.0-0t64 libdrm2 libxkbcommon0 libatspi2.0-0t64 libcups2t64 libxshmfence1 libgbm1 fonts-noto-color-emoji fonts-noto-cjk fonts-freefont-ttf
```

## Notes
- Package names carry the `t64` suffix on Ubuntu 24.04+ (e.g. `libgtk-3-0t64`, `libatk1.0-0t64`); on older Ubuntu/Debian drop the `t64`.
- The `fonts-*` packages are for emoji/CJK glyph rendering in screenshots — include them or screenshots show tofu boxes.
- If the first launch error names a *different* missing `.so` than `libatk`, map it: the `libatk1.0` / `libatk-bridge2.0` pair is usually the first to trip, then `libnss3`/`libnspr4`, then the X11/GTK set.
- These libs are harmless to leave installed (standard for any headless Chrome usage), no need to `apt remove` later.
