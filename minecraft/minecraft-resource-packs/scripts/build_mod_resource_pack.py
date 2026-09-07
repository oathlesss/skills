#!/usr/bin/env python3
"""
Build a Faithful-style 32x resource pack for a modded Minecraft pack.

Walks every mod .jar in the pack's mods/ folder, extracts all textures,
upscales them 2x with a corner-preserving Scale2x scaler, and packages the
result as an installable resource pack (layer over a base Faithful/vanilla pack).

Requirements: pip install pillow numpy

Usage:
    python build_mod_resource_pack.py --mods-dir /path/to/mods \
        --out-dir /tmp/out --zip-name mypack-32x [--limit N] [--pack-format 34]
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
    """2x upscale with corner-preserving Scale2x (see SKILL.md for the trick)."""
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

    # corner guard: only smooth when the diagonal continues (NE != SW, NW != SE)
    e0 = np.where(eq(W_, N) & ~eq(W_, S) & ~eq(N, E) & ~eq(NE, SW), W_, P)
    e1 = np.where(eq(N, E) & ~eq(N, W_) & ~eq(E, S) & ~eq(NW, SE), N, P)
    e2 = np.where(eq(W_, S) & ~eq(W_, N) & ~eq(S, E) & ~eq(NW, SE), W_, P)
    e3 = np.where(eq(S, E) & ~eq(S, W_) & ~eq(E, N) & ~eq(NE, SW), S, P)

    out = np.empty((H * 2, W * 2, C), dtype=arr.dtype)
    out[0::2, 0::2] = e0
    out[0::2, 1::2] = e1
    out[1::2, 0::2] = e2
    out[1::2, 1::2] = e3
    return out


def upscale_png(data: bytes) -> bytes:
    """Read a PNG, upscale 2x if small (<=32px), return PNG bytes (or None to skip)."""
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception:
        return None
    w, h = img.size
    if max(w, h) > 32:          # already high-res / atlas / GUI — leave untouched
        return data
    img = img.convert("RGBA")
    arr = np.asarray(img, dtype=np.uint8)
    out_img = Image.fromarray(scale2x(arr), "RGBA")
    buf = io.BytesIO()
    out_img.save(buf, "PNG", optimize=False)
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mods-dir", required=True)
    ap.add_argument("--out-dir", default="/tmp/resourcepack")
    ap.add_argument("--zip-name", default="modpack-32x")
    ap.add_argument("--limit", type=int, default=0, help="process at most N jars (0 = all)")
    ap.add_argument("--pack-format", type=int, default=34, help="resource pack format (1.21.1 = 34)")
    args = ap.parse_args()

    jars = sorted(f for f in os.listdir(args.mods_dir) if f.endswith(".jar"))
    if args.limit:
        jars = jars[: args.limit]
    os.makedirs(args.out_dir, exist_ok=True)

    total = upscaled = kept = skipped_vanilla = errors = 0
    for jar_name in jars:
        try:
            with zipfile.ZipFile(os.path.join(args.mods_dir, jar_name)) as z:
                for name in z.namelist():
                    if not name.startswith("assets/") or "/textures/" not in name:
                        continue
                    if name.split("/")[1] == "minecraft":
                        skipped_vanilla += 1
                        continue
                    if name.endswith(".png.mcmeta"):
                        out = os.path.join(args.out_dir, name)
                        os.makedirs(os.path.dirname(out), exist_ok=True)
                        with open(out, "wb") as f:
                            f.write(z.read(name))
                        continue
                    if not name.endswith(".png"):
                        continue
                    data = z.read(name)
                    total += 1
                    result = upscale_png(data)
                    if result is None:
                        errors += 1
                        continue
                    if result is data:
                        kept += 1
                    else:
                        upscaled += 1
                    out = os.path.join(args.out_dir, name)
                    os.makedirs(os.path.dirname(out), exist_ok=True)
                    with open(out, "wb") as f:
                        f.write(result)
        except Exception as e:
            errors += 1
            print(f"  [warn] {jar_name}: {e}", file=sys.stderr)

    mcmeta = {"pack": {"pack_format": args.pack_format, "description": f"{args.zip_name} (auto-upscaled)"}}
    with open(os.path.join(args.out_dir, "pack.mcmeta"), "w") as f:
        json.dump(mcmeta, f)

    zip_path = os.path.join(os.path.dirname(args.out_dir), args.zip_name + ".zip")
    if os.path.exists(zip_path):
        os.remove(zip_path)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(args.out_dir):
            for fn in files:
                full = os.path.join(root, fn)
                zf.write(full, os.path.relpath(full, args.out_dir))

    print(f"jars {len(jars)} | textures {total} | upscaled {upscaled} | kept {kept} | "
          f"skipped-vanilla {skipped_vanilla} | errors {errors}")
    print(f"wrote {zip_path} ({os.path.getsize(zip_path) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
