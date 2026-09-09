#!/usr/bin/env python3
"""
Capture a screenshot of a Godot project by running it under Xvfb.

Usage: capture.py <project_path> <output_png> [frames]

Requires xvfb-run (sudo apt install -y xvfb). Without it, Godot headless
has no rendering server and cannot produce a screenshot.
"""
import os
import shutil
import subprocess
import sys


def main():
    if len(sys.argv) < 3:
        raise SystemExit("usage: capture.py <project_path> <output_png> [frames]")
    proj, out = sys.argv[1], sys.argv[2]
    frames = sys.argv[3] if len(sys.argv) > 3 else "90"

    if not shutil.which("xvfb-run"):
        raise SystemExit(
            "xvfb-run not found. Screenshots require a virtual display.\n"
            "Install it:  sudo apt install -y xvfb\n"
            "(headless Godot has no rendering server — this is a hard requirement.)"
        )

    godot = os.path.expanduser("~/.local/bin/godot")
    cap_gd = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capture.gd")
    env = dict(os.environ, CAPTURE_OUT=out, CAPTURE_FRAMES=frames)
    cmd = ["xvfb-run", "-a", godot, "--path", proj,
           "--rendering-method", "gl_compatibility", "-s", cap_gd]
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if r.stdout:
        print(r.stdout)
    if r.returncode != 0:
        if r.stderr:
            print(r.stderr)
        raise SystemExit(r.returncode)
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
