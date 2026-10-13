#!/usr/bin/env python3
"""Report per-player playtime for an itzg Minecraft server.

Reads world/stats/<uuid>.json (play_time in ticks) + usercache.json (uuid->name)
and prints a sorted table of total playtime per player.

Player stats live in world/stats/*.json, NOT world/playerdata/*.dat (whose
`stats` compound is empty on modern 1.21.1). The stat is
`stats.minecraft:custom.minecraft:play_time` in ticks (20 ticks = 1s).

Usage: python3 player-playtime.py [DATA_DIR]
Default DATA_DIR: /home/ruben/homeserver/minecraft-e10/data
"""
import json
import os
import sys


def fmt(ticks):
    s = ticks / 20.0
    h = int(s // 3600)
    m = int(s % 3600 // 60)
    sec = int(s % 60)
    return f"{h}h {m}m {sec}s"


def main():
    data = sys.argv[1] if len(sys.argv) > 1 else "/home/ruben/homeserver/minecraft-e10/data"

    names = {}
    uc = os.path.join(data, "usercache.json")
    if os.path.isfile(uc):
        names = {e["uuid"]: e["name"] for e in json.load(open(uc))}

    sdir = os.path.join(data, "world", "stats")
    if not os.path.isdir(sdir):
        print(f"no stats dir at {sdir}")
        return

    rows = []
    for fn in os.listdir(sdir):
        if not fn.endswith(".json"):
            continue
        uuid = fn[:-5]
        d = json.load(open(os.path.join(sdir, fn)))
        custom = d.get("stats", {}).get("minecraft:custom", {})
        pt = custom.get("minecraft:play_time", 0)
        deaths = custom.get("minecraft:deaths", 0)
        rows.append((names.get(uuid, uuid), uuid[:8], pt, deaths))

    rows.sort(key=lambda r: -r[2])
    print(f"{'player':<20} {'playtime':<14} deaths")
    print("-" * 44)
    for name, u8, pt, deaths in rows:
        print(f"{name:<20} {fmt(pt):<14} {deaths}")


if __name__ == "__main__":
    main()
