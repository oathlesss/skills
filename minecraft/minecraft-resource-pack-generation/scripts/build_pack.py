#!/usr/bin/env python3
"""Build a Faithful-style 32x resource pack for a modded pack.

Extracts every texture from every mod jar, upscales 2x with Scale2x (the
crisp, Faithful-appropriate scaler), packages as an installable resource pack.
Skips the minecraft: namespace (base Faithful covers vanilla).
Requires: numpy, Pillow.

Usage:
    python build_pack.py --mods-dir /path/to/mods --out-dir /path/to/output [--limit N]
"""
import io
import os
import sys
import zipfile
import argparse
import json

import numpy as np
from PIL import Image


def scale2x(arr):
    """Scale an HxWxC uint8 array 2x using the Scale2x algorithm (crisp, faithful)."""
    H, W, C = arr.shape
    pad = np.pad(arr, ((1, 1), (1, 1), (0, 0)), mode="edge")
    N = pad[:-2, 1:-1]    # north
    S = pad[2:, 1:-1]     # south
    W_ = pad[1:-1, :-2]   # west
    E = pad[1:-1, 2:]     # east
    P = pad[1:-1, 1:-1]   # center

    # (H,W,1) so the mask broadcasts over the channel axis
    eq = lambda a, b: np.all(a == b, axis=-1)[..., None]

    e0 = np.where(eq(W_, N) & ~eq(W_, S) & ~eq(N, E), W_, P)  # top-left
    e1 = np.where(eq(N, E) & ~eq(N, W_) & ~eq(E, S), N, P)    # top-right
    e2 = np.where(eq(W_, S) & ~eq(W_, N) & ~eq(S, E), W_, P)  # bottom-left
    e3 = np.where(eq(S, E) & ~eq(S, W_) & ~eq(E, N), S, P)    # bottom-right

    out = np.empty((H * 2, W * 2, C), dtype=arr.dtype)
    out[0::2, 0::2] = e0
    out[0::2, 1::2] = e1
    out[1::2, 0::2] = e2
    out[1::2, 1::2] = e3
    return out


def upscale_png(data):
    """Read a PNG, upscale 2x if small (<=32px), else return unchanged. None = skip."""
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception:
        return None
    w, h = img.size
    if max(w, h) > 32:            # already high-res / atlas / GUI
        return data
    arr = np.asarray(img.convert("RGBA"), dtype=np.uint8)
    out = Image.fromarray(scale2x(arr), "RGBA")
    buf = io.BytesIO()
    out.save(buf, "PNG", optimize=False)
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mods-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--zip-name", default="modpack-32x")
    ap.add_argument("--limit", type=int, default=0, help="process at most N jars (0 = all)")
    ap.add_argument("--pack-format", type=int, default=34, help="resource pack format (1.21.x = 34)")
    args = ap.parse_args()

    jars = sorted(f for f in os.listdir(args.mods_dir) if f.endswith(".jar"))
    if args.limit:
        jars = jars[: args.limit]
    os.makedirs(args.out_dir, exist_ok=True)

    total = upscaled = kept = skip_v = 0
    for jar in jars:
        try:
            with zipfile.ZipFile(os.path.join(args.mods_dir, jar)) as z:
                for name in z.namelist():
                    if not name.startswith("assets/") or "/textures/" not in name:
                        continue
                    if name.split("/")[1] == "minecraft":
                        skip_v += 1
                        continue
                    if name.endswith(".png.mcmeta"):           # animated texture metadata
                        op = os.path.join(args.out_dir, name)
                        os.makedirs(os.path.dirname(op), exist_ok=True)
                        with open(op, "wb") as f:
                            f.write(z.read(name))
                        continue
                    if not name.endswith(".png"):
                        continue
                    data = z.read(name)
                    total += 1
                    res = upscale_png(data)
                    if res is None:
                        continue
                    if res is data:
                        kept += 1
                    else:
                        upscaled += 1
                    op = os.path.join(args.out_dir, name)
                    os.makedirs(os.path.dirname(op), exist_ok=True)
                    with open(op, "wb") as f:
                        f.write(res)
        except Exception as e:
            print(f"warn {jar}: {e}", file=sys.stderr)

    with open(os.path.join(args.out_dir, "pack.mcmeta"), "w") as f:
        json.dump({"pack": {"pack_format": args.pack_format, "description": "32x (auto-upscaled)"}}, f)

    zp = os.path.join(os.path.dirname(args.out_dir), args.zip_name + ".zip")
    if os.path.exists(zp):
        os.remove(zp)
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, fs in os.walk(args.out_dir):
            for fn in fs:
                fp = os.path.join(root, fn)
                zf.write(fp, os.path.relpath(fp, args.out_dir))

    print(f"jars={len(jars)} textures={total} upscaled={upscaled} kept={kept} skipped_vanilla={skip_v}")
    print(f"zip={zp} ({os.path.getsize(zp) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
