# Minecraft Server Plugins

## Vanilla Can't Run Plugins

The `TYPE: VANILLA` itzg container runs the official Mojang server jar, which has no plugin API. To use plugins, switch to a Bukkit-compatible server type.

## Switching to Paper/Purpur on itzg

Change one env var — the image handles the rest:

```yaml
environment:
  # TYPE: VANILLA     # old
  TYPE: PAPER         # new
  VERSION: LATEST     # or pin a specific version
```

The world data is fully compatible. No migration needed.

**Paper vs Purpur:**

| | Paper | Purpur |
|---|---|---|
| What | Fork of Spigot, massive perf patches | Fork of Paper, even more config knobs |
| Plugin compat | Near-perfect Bukkit/Spigot/Paper | Same + a few Purpur-only |
| Update speed | Faster | Slightly behind |
| Default choice | ✅ | If you want max configurability |

## Where to Browse Plugins

| Site | Notes |
|---|---|
| [modrinth.com/plugins](https://modrinth.com/plugins) | Cleanest UI. Filter by server type, version, category. Modern standard. |
| [hangar.papermc.io](https://hangar.papermc.io) | Paper's official repo. Everything guaranteed Paper-compatible. |
| [spigotmc.org/resources](https://www.spigotmc.org/resources/) | The OG. Massive library, dated UI. Some plugins abandoned. |
| [bukkit.org](https://dev.bukkit.org/bukkit-plugins) | Mostly legacy. The above have superseded it. |

**Recommended starting point:** Modrinth — filter by `Server: Paper` and your Minecraft version, browse by category.

## Checking the Current Minecraft Version

When you need to know what version a running itzg container is using:

```bash
# Quick: check the log for the version string
docker logs <container> --tail 30 2>&1 | grep -i 'Starting minecraft server'

# Definite: read version.json from inside the jar
JAR=$(docker exec <container> ls /data/minecraft_server.*.jar 2>/dev/null | head -1)
docker exec <container> unzip -p "$JAR" version.json 2>/dev/null
```

The `version.json` inside the jar contains `id`, `protocol_version`, `world_version`, `build_time`, and `java_version`.

**Note:** As of mid-2026, Mojang dropped the "1." prefix. The `id` field shows just the number (e.g. `"26.2"`). When browsing plugins on Modrinth/Hangar, filter for this version number.

## Plugin Availability vs Minecraft Version

New Minecraft releases (like 26.2, built June 2026) have a **lag period** before Paper/Purpur and plugin devs catch up. If you need plugins immediately after a new version drops, pin to the previous stable version instead of `LATEST`.
