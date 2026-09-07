# Minecraft Server Performance Feasibility

How to answer "can this box keep up with this modpack?" with evidence instead of
reputation. Written against the OptiPlex 3070 Micro running ATM10 Aeronautics, but the
method generalizes to any itzg Minecraft container on any host.

## Trigger

User asks some variant of: "will the server keep up?", "is this modpack too heavy?",
"will it lag with N players?", or asks to swap to a heavier/lighter pack and wants a
feasibility verdict.

## The One-Line Mental Model

Minecraft's tick loop is **single-threaded**. RAM is rarely the constraint (this host
has 30GB, allocates 10G). The two things that actually matter:

1. **Single-core CPU speed** — chunk generation and the tick loop both live here. A
   low-power "T"-series chip (35W) throttles hard under sustained load, especially with
   the `powersave` governor active.
2. **Chunk-gen load** — how much world the players generate as they explore/fly/dimension-hop.

Pack "weight" is driven by world-gen, not mod count. 400 mods in a skyblock is light;
200 mods with Twilight Forest + Aether + Undergarden is heavy.

## Diagnostic Sequence

Run these and interpret each:

```bash
# 1. Hardware ceiling
lscpu | grep -E "Model name|^CPU\(s\)|Thread|Core"
free -h
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor   # powersave = throttling risk

# 2. Live container load (sample twice — idle vs burst)
docker stats --no-stream <container> --format '{{.CPUPerc}} {{.MemUsage}}'

# 3. Mod count + performance mods already present
ls data/mods/*.jar | wc -l
ls data/mods/ | grep -iE "servercore|ferrite|modernfix|observable|spark|krypton|embeddium|radium"

# 4. World size (the stress-proxy)
du -sh data/world

# 5. Past lag evidence
grep -icE "can't keep up|running behind|is overloaded" data/logs/latest.log

# 6. Live TPS (spark returns empty via RCON — use /debug)
docker exec <container> rcon-cli "debug start" && sleep 5 && docker exec <container> rcon-cli "debug stop"

# 7. Thermal headroom
sensors | grep -iE "core|package"
```

## Interpretation

| Signal | Reading |
|---|---|
| `lscpu` shows "T" suffix / 35W / no hyperthreading | Weak sustained single-core — the real ceiling. |
| Governor = `powersave` | Clocks throttled under load. Switch to `performance` for a few watts of headroom. |
| Idle CPU% ~40%+ on an **empty** world | Already ~2.5 cores busy ticking nothing — exploration will saturate the single thread. |
| World folder ≤ ~10MB | Nobody explored yet. Idle CPU is misleading; the pack hasn't been stress-tested. |
| Perf mods present (ferritecore, modernfix, spark) | Pack ships with some mitigation — but they can't fix a slow core, only waste. |
| 0 "can't keep up" warnings | Not a clean bill of health if the world is ungenerated — the warnings come *after* players explore. |
| Temps low (~40°C) | Not thermal-throttling *yet*. The T chip throttles on power budget before temp, so this can still hide the limit. |

## This Machine (OptiPlex 3070 Micro)

- **CPU:** Intel i5-9500T — 6 cores / 6 threads (no HT), 2.2GHz base / 3.7GHz boost, 35W TDP.
- **RAM:** 30GB total, 10G allocated to Minecraft, 8G swap.
- **Disk:** NVMe (fast chunk loading, good).
- **Governor:** `powersave` (throttling risk — see remediation).
- **Verdict for ATM10 Aeronautics:** playable for 2–4 players doing normal progression;
  will lag if everyone explores separately or flies around generating terrain. About the
  minimum-spec floor for a full-worldgen pack of this size.

## Remediation (biggest wins first)

1. **Cut view/sim distance** — `view-distance: 10→6`, `simulation-distance: 10→6` in
   `server.properties`. Single biggest win (~halves chunk load). This is a
   `server.properties` edit; recall itzg regenerates that file on first run only, so edit
   the existing file directly (or delete + set env vars) and restart.
2. **Pre-generate the world** (chunky) so exploration hits disk cache instead of live-gen.
3. **Switch governor** `powersave`→`performance`:
   ```bash
   echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
   ```
   Costs a few watts; removes throttle-induced TPS dips. (Persist via `cpupower` or a
   systemd unit if desired — the `/sys` write resets on reboot.)
4. **Verify TPS after changes** via `rcon-cli "debug start"` / `"debug stop"` — `spark tps`
   returns empty over RCON (chat-only), so `/debug` is the reliable RCON path.

## Pack Weight Reference (ATM10 family)

| Pack | Worldgen | Weight on this box |
|---|---|---|
| ATM10 To The Sky | Void skyblock | Light — trivial chunk-gen |
| ATM10 Aeronautics | Full overworld + ~10 dimensions | Heavy — near ceiling |

When the user asks to swap between these, the *direction* matters: To The Sky → Aeronautics
is a large step up in load even though both are NeoForge 1.21.1 on `:java21` and the swap
is a pure slug + data-dir change. See `references/minecraft-modpack-swap.md` for the swap
procedure itself.
