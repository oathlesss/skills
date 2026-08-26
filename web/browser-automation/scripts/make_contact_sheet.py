#!/usr/bin/env python3
"""Montage N screenshots into one labeled contact sheet (Pillow).

Usage:
  uv run --with pillow python3 make_contact_sheet.py \
      "Gold=/tmp/v1.png" "Purple=/tmp/v2.png" /tmp/sheet.png

Each arg is `label=path` (or a bare path, in which case the label is derived from
the filename). A trailing bare .png/.jpg arg is treated as the output path
(default: /tmp/contact-sheet.png). Tiles left-to-right at ~640px wide, label bar below.

Why this exists: ImageMagick is not installed on this box; Pillow is pulled on
demand via `uv run --with pillow`. Used to compare variant renders (e.g. stream
overlay accent colors) side-by-side in one chat-sized image.
"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont

TW, TH = 640, 360      # tile size (scaled to 16:9)
LABEL_H = 56
PAD = 24


def find_font(size):
    for p in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def main(argv):
    if not argv:
        print(__doc__)
        sys.exit(1)

    out = "/tmp/contact-sheet.png"
    items = []
    for a in argv:
        if a.endswith((".png", ".jpg", ".jpeg")) and "=" not in a:
            out = a
        elif "=" in a:
            label, path = a.split("=", 1)
            items.append((label, path))
        else:
            items.append((os.path.splitext(os.path.basename(a))[0], a))

    if not items:
        print("no input images given", file=sys.stderr)
        sys.exit(1)

    font = find_font(26)
    tiles = []
    for label, path in items:
        img = Image.open(path).convert("RGB").resize((TW, TH), Image.LANCZOS)
        canvas = Image.new("RGB", (TW, TH + LABEL_H), (20, 22, 26))
        canvas.paste(img, (0, 0))
        d = ImageDraw.Draw(canvas)
        d.text((14, TH + (LABEL_H - 26) // 2), label, fill=(245, 246, 248), font=font)
        tiles.append(canvas)

    W = len(tiles) * TW + (len(tiles) + 1) * PAD
    H = TH + LABEL_H + 2 * PAD
    sheet = Image.new("RGB", (W, H), (13, 15, 19))
    for i, tile in enumerate(tiles):
        sheet.paste(tile, (PAD + i * (TW + PAD), PAD))

    sheet.save(out)
    print("saved", out, sheet.size)


if __name__ == "__main__":
    main(sys.argv[1:])
