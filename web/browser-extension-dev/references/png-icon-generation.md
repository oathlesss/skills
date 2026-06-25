# PNG Icon Generation (Pure Python)

Generate valid PNG icon files without Pillow, ImageMagick, or any external dependency. Uses only Python stdlib (`struct`, `zlib`).

## Script

```python
import struct, zlib

def create_png(width, height, r, g, b):
    """Create a solid-color PNG with a simple book/page icon shape."""
    def make_chunk(chunk_type, data):
        chunk = chunk_type + data
        return struct.pack('>I', len(data)) + chunk + struct.pack('>I', zlib.crc32(chunk) & 0xffffffff)

    # Generate RGBA pixel data with a simple icon shape
    raw = b''
    for y in range(height):
        raw += b'\x00'  # filter byte (none)
        for x in range(width):
            rel_x = x / width
            rel_y = y / height

            # Border margin
            if rel_x < 0.15 or rel_x > 0.85 or rel_y < 0.1 or rel_y > 0.9:
                raw += bytes([r, g, b, 255])
            # Left page (slightly darker)
            elif rel_x < 0.5:
                raw += bytes([min(255, int(r*0.8)), min(255, int(g*0.8)), min(255, int(b*0.8)), 255])
            # Spine (original color)
            elif rel_x < 0.53:
                raw += bytes([r, g, b, 255])
            # Right page (slightly lighter)
            else:
                raw += bytes([min(255, int(r*1.1)), min(255, int(g*1.1)), min(255, int(b*1.1)), 255])

    ihdr = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)  # 8-bit RGBA, no compression

    return (b'\x89PNG\r\n\x1a\n' +
            make_chunk(b'IHDR', ihdr) +
            make_chunk(b'IDAT', zlib.compress(raw)) +
            make_chunk(b'IEND', b''))

# Generate all three required sizes
for size, color in [(16, (196,167,231)), (48, (196,167,231)), (128, (196,167,231))]:
    with open(f'icons/icon{size}.png', 'wb') as f:
        f.write(create_png(size, size, *color))
```

## Usage

Save to `/tmp/make_icons.py`, run with `python3 /tmp/make_icons.py`. Creates `icons/icon16.png`, `icons/icon48.png`, `icons/icon128.png`.

## Customization

- Change the RGB tuple for different colors
- Modify the pixel logic inside the `for x in range(width)` loop for different shapes
- The script uses 8-bit RGBA (color type 6) — supports transparency if you set alpha < 255

## Limitations

- No antialiasing — small icons (16x16) will look blocky
- Simple geometric shapes only — no text, no curves
- For production icons, use a proper image editor or Pillow
