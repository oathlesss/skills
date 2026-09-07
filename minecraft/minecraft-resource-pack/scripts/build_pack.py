#!/usr/bin/env python3
"""
Build a Faithful-style 2x resource pack for a modded Minecraft pack.

Walks every mod .jar in the pack's mods/ folder, extracts all textures,
upscales them 2x with the Scale2x pixel-art scaler, and packages the result
as an installable resource pack (layered over a base 32x pack).

Vanilla (minecraft:) namespace is skipped — the base pack covers it.
"""
import io
import os
import sys
import zipfile
import argparse
import json

import numpy as np
from PIL import Image


# ---------------------------------------------------------------------------
# 2x pixel-art upscaler (Scale2x baseline — correct, edge-smoothing)
# ---------------------------------------------------------------------------

def scale2x(arr: np.ndarray) -> np.ndarray:
    """Scale an HxWxC uint8 array 2x using the Scale2x algorithm."""
    H, W, C = arr.shape
    pad = np.pad(arr, ((1, 1), (1, 1), (0, 0)), mode="edge")
    N = pad[:-2, 1:-1]   # north
    S = pad[2:, 1:-1]    # south
    W_ = pad[1:-1, :-2]  # west
    E = pad[1:-1, 2:]    # east
    P = pad[1:-1, 1:-1]  # center

    def eq(a, b):
        # (H,W,1) so the boolean broadcasts over channels — REQUIRED, see pitfall
        return np.all(a == b, axis=-1)[..., None]

    # Scale2x rules (Mazzoleni): preserve flat areas, round single-pixel diagonals
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


def upscale_png(data: bytes) -> bytes:
    """Read a PNG, upscale 2x if small (<=32px), else return unchanged (None on error)."""
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
    out = scale2x(arr)
    out_img = Image.fromarray(out, "RGBA")
    buf = io.BytesIO()
    out_img.save(buf, "PNG", optimize=False)
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mods-dir", required=True)
    ap.add_argument("--out-dir", default="output")
    ap.add_argument("--zip-name", default="modpack-2x")
    ap.add_argument("--limit", type=int, default=0, help="process at most N jars (0 = all)")
    ap.add_argument("--pack-format", type=int, default=34, help="resource pack format (1.21.1 = 34)")
    args = ap.parse_args()

    jars = sorted(f for f in os.listdir(args.mods_dir) if f.endswith(".jar"))
    if args.limit:
        jars = jars[: args.limit]

    os.makedirs(args.out_dir, exist_ok=True)

    total_tex = upscaled = skipped_large = skipped_vanilla = errors = 0

    for jar_name in jars:
        jar_path = os.path.join(args.mods_dir, jar_name)
        try:
            with zipfile.ZipFile(jar_path) as z:
                for name in z.namelist():
                    if not name.startswith("assets/") or "/textures/" not in name:
                        continue
                    namespace = name.split("/")[1]
                    if namespace == "minecraft":
                        skipped_vanilla += 1
                        continue
                    if name.endswith(".png.mcmeta"):          # animated metadata
                        out_path = os.path.join(args.out_dir, name)
                        os.makedirs(os.path.dirname(out_path), exist_ok=True)
                        with open(out_path, "wb") as f:
                            f.write(z.read(name))
                        continue
                    if not name.endswith(".png"):
                        continue
                    data = z.read(name)
                    total_tex += 1
                    result = upscale_png(data)
                    if result is None:
                        errors += 1
                        continue
                    if result is data:
                        skipped_large += 1
                    else:
                        upscaled += 1
                    out_path = os.path.join(args.out_dir, name)
                    os.makedirs(os.path.dirname(out_path), exist_ok=True)
                    with open(out_path, "wb") as f:
                        f.write(result)
        except Exception as e:
            print(f"  [warn] failed on {jar_name}: {e}", file=sys.stderr)
            errors += 1

    mcmeta = {"pack": {"pack_format": args.pack_format, "description": f"{args.zip_name} (auto-upscaled 2x)"}}
    with open(os.path.join(args.out_dir, "pack.mcmeta"), "w") as f:
        json.dump(mcmeta, f)

    zip_path = os.path.join(os.path.dirname(args.out_dir) or ".", args.zip_name + ".zip")
    if os.path.exists(zip_path):
        os.remove(zip_path)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(args.out_dir):
            for fn in files:
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, args.out_dir)
                zf.write(full, rel)

    size_mb = os.path.getsize(zip_path) / 1e6
    print(f"jars processed:      {len(jars)}")
    print(f"textures found:      {total_tex}")
    print(f"upscaled 2x:         {upscaled}")
    print(f"kept (large/atlas):  {skipped_large}")
    print(f"skipped vanilla:     {skipped_vanilla}")
    print(f"errors/skipped:      {errors}")
    print(f"output zip:          {zip_path}  ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
