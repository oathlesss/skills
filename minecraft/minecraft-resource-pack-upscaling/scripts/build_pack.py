#!/usr/bin/env python3
"""
Build a Faithful-style 32x resource pack from a modpack's mods/ directory.

Extracts assets/<ns>/textures/**/*.png from every .jar, 2x-upscales with a
corner-guarded Scale2x (smooths diagonals, preserves 90-degree corners), and
zips the result with a pack.mcmeta.

Requires: pillow, numpy   (uv pip install pillow numpy)
Run: python build_pack.py --mods-dir <mods dir> --out-dir <out dir>
"""
import io
import os
import sys
import zipfile
import argparse
import json

import numpy as np
from PIL import Image


def scale2x(arr: np.ndarray) -> np.ndarray:
    """2x upscale (H,W,C) uint8 with Scale2x + corner guard.

    Corner guard: only smooth a diagonal when it actually continues
    (NE != SW for top-left/bottom-right, NW != SE for top-right/bottom-left),
    which preserves 90-degree corners and straight edges.
    """
    H, W, C = arr.shape
    pad = np.pad(arr, ((1, 1), (1, 1), (0, 0)), mode="edge")
    NW = pad[:-2, :-2]
    N = pad[:-2, 1:-1]
    NE = pad[:-2, 2:]
    W_ = pad[1:-1, :-2]
    P = pad[1:-1, 1:-1]
    E = pad[1:-1, 2:]
    SW = pad[2:, :-2]
    S = pad[2:, 1:-1]
    SE = pad[2:, 2:]

    def eq(a, b):
        return np.all(a == b, axis=-1)[..., None]  # (H,W,1) broadcasts over channels

    e0 = np.where(eq(W_, N) & ~eq(W_, S) & ~eq(N, E) & ~eq(NE, SW), W_, P)  # top-left
    e1 = np.where(eq(N, E) & ~eq(N, W_) & ~eq(E, S) & ~eq(NW, SE), N, P)    # top-right
    e2 = np.where(eq(W_, S) & ~eq(W_, N) & ~eq(S, E) & ~eq(NW, SE), W_, P)  # bottom-left
    e3 = np.where(eq(S, E) & ~eq(S, W_) & ~eq(E, N) & ~eq(NE, SW), S, P)    # bottom-right

    out = np.empty((H * 2, W * 2, C), dtype=arr.dtype)
    out[0::2, 0::2] = e0
    out[0::2, 1::2] = e1
    out[1::2, 0::2] = e2
    out[1::2, 1::2] = e3
    return out


def upscale_png(data: bytes) -> bytes:
    """Upscale a PNG 2x if small (<=32px), else return unchanged."""
    try:
        img = Image.open(io.BytesIO(data)).convert("RGBA")
    except Exception:
        return data
    w, h = img.size
    if max(w, h) > 32:  # already high-res / atlas / GUI — leave untouched
        return data
    arr = np.asarray(img, dtype=np.uint8)
    out = Image.fromarray(scale2x(arr), "RGBA")
    buf = io.BytesIO()
    out.save(buf, "PNG", optimize=False)
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mods-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--zip-name", default="modpack-32x")
    ap.add_argument("--pack-format", type=int, default=34, help="1.21.1 = 34")
    ap.add_argument("--limit", type=int, default=0, help="process at most N jars (0=all)")
    args = ap.parse_args()

    jars = sorted(f for f in os.listdir(args.mods_dir) if f.endswith(".jar"))
    if args.limit:
        jars = jars[: args.limit]
    os.makedirs(args.out_dir, exist_ok=True)

    total = upscaled = skipped_large = skipped_vanilla = errors = 0
    for jar_name in jars:
        try:
            with zipfile.ZipFile(os.path.join(args.mods_dir, jar_name)) as z:
                for name in z.namelist():
                    if not name.startswith("assets/") or "/textures/" not in name:
                        continue
                    ns = name.split("/")[1]
                    if ns == "minecraft":
                        skipped_vanilla += 1
                        continue
                    if name.endswith(".png.mcmeta"):
                        out = os.path.join(args.out_dir, name)
                        os.makedirs(os.path.dirname(out), exist_ok=True)
                        open(out, "wb").write(z.read(name))
                        continue
                    if not name.endswith(".png"):
                        continue
                    data = z.read(name)
                    total += 1
                    result = upscale_png(data)
                    if result is data:
                        skipped_large += 1
                    else:
                        upscaled += 1
                    out = os.path.join(args.out_dir, name)
                    os.makedirs(os.path.dirname(out), exist_ok=True)
                    open(out, "wb").write(result)
        except Exception as e:
            print(f"[warn] {jar_name}: {e}", file=sys.stderr)
            errors += 1

    mcmeta = {"pack": {"pack_format": args.pack_format, "description": "Auto 32x upscale"}}
    json.dump(mcmeta, open(os.path.join(args.out_dir, "pack.mcmeta"), "w"))

    zip_path = os.path.join(os.path.dirname(args.out_dir), args.zip_name + ".zip")
    if os.path.exists(zip_path):
        os.remove(zip_path)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(args.out_dir):
            for fn in files:
                full = os.path.join(root, fn)
                zf.write(full, os.path.relpath(full, args.out_dir))

    print(f"textures={total} upscaled={upscaled} kept_large={skipped_large} "
          f"skipped_vanilla={skipped_vanilla} errors={errors}")
    print(f"zip={zip_path} ({os.path.getsize(zip_path)/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
