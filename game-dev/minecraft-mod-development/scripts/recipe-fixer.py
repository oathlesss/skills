#!/usr/bin/env python3
"""Fix recipe JSON files: convert string ingredient keys to object format.
NeoForge 1.21.1 requires {"item": "namespace:id"} — string shorthand breaks.

Usage: python3 reference/recipe-fixer.py <recipe_dir>
"""

import json, os, glob, sys

def fix_recipes(recipe_dir: str) -> int:
    fixed = 0
    for path in glob.glob(os.path.join(recipe_dir, "*.json")):
        with open(path) as f:
            data = json.load(f)
        changed = False
        if "key" in data:
            for k, v in data["key"].items():
                if isinstance(v, str):
                    data["key"][k] = {"item": v}
                    changed = True
        if changed:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
                f.write("\n")
            print(f"Fixed: {os.path.basename(path)}")
            fixed += 1
    return fixed

if __name__ == "__main__":
    d = sys.argv[1] if len(sys.argv) > 1 else "src/main/resources/data/thau/recipe"
    n = fix_recipes(d)
    print(f"\nFixed {n} recipes")
