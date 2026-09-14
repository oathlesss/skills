# ATM10 Aeronautics — Pregen / DH command reference (session detail)

Captured Sept 2026. Server: ATM10 Aeronautics, MC 1.21.1, NeoForge 21.1.248, itzg
`minecraft-server:java21`, AUTO_CURSEFORGE, `CF_SLUG=all-the-mods-10-aeronautics`.

## Mods added (verified CF files for 1.21.1 NeoForge)

| Mod | CF project | CF file ID | Jar | Role |
|---|---|---|---|---|
| Chunky | 485681 | 6383261 | `Chunky-NeoForge-1.4.23.jar` | real-chunk pregen |
| C2ME | 533097 | 8646869 | `c2me-neoforge-mc1.21.1-0.4.0-alpha.0.120.jar` | parallel chunk gen |
| Distant Horizons | 508933 | 8389148 | `DistantHorizons-3.2.0-b-1.21.1-fabric-neoforge.jar` | LODs (client + optional server) |

Note: C2ME + DH are alpha/beta builds on 1.21.1 — normal (no stable release exists).

## RCON helper

```bash
rcon() { docker exec minecraft-atm10aero rcon-cli "$1" 2>&1; }
```

## Chunky pregen (real chunks) — exact flow used

```bash
rcon "chunky world minecraft:overworld"
rcon "chunky spawn"          # center -> world spawn (0,0 in this case)
rcon "chunky radius 2000"    # BLOCKS
rcon "chunky selection"      # verify: World/Shape/Center/Radius
rcon "chunky start"
rcon "chunky progress"       # e.g. "Processed: N chunks (X%), ETA: ..., Rate: N cps"
```

Observed: rate ~7 cps cold → ~50 cps after C2ME warmup. 2000-block radius ≈
~63k chunks, ETA ~2.5h → ~18 min once warmed. CPU pegs ~600% (all 6 cores).

`chunky config threads` does NOT exist in 1.4.23 — skip it.

## Distant Horizons LOD pregen (after Chunky finishes)

```bash
# best-effort config (key names drift between DH versions — check `dh help`/`dh config` first)
rcon "dh config common.generationMode INTERNAL_SERVER"
rcon "dh config common.threadPreset I_PAID_FOR_THE_WHOLE_CPU"
rcon "dh pregen start minecraft:overworld 0 0 256"   # radius in CHUNKS
rcon "dh pregen status"
```

LODs land in a `Distant_Horizons_server_data/` folder under `/data`. Clients with DH
installed fetch them automatically on connect.

## Boot-wait pattern (400 mods, several minutes)

```bash
for i in $(seq 1 60); do
  sleep 20
  R=$(docker exec minecraft-atm10aero rcon-cli "list" 2>&1 | head -1)
  case "$R" in *"players online"*|*"online:"*) echo "RCON UP after ~$((i*20))s"; break;; esac
done
```

Crash detection: `docker logs minecraft-atm10aero | grep -E "FATAL|Encountered an error|Failed to start|A fatal error"`.
Do NOT grep bare "ERROR" — mod loaders log harmless "ERROR: No value present"-style warnings.

## Background-watcher gotcha

A `notify_on_complete` background watcher that sleeps in a long poll loop can be
reaped by its parent (Hermes gateway) while asleep, emitting a SPURIOUS "completed
(exit code None)" notification and leaving a zombie `bash` (`Zs` / defunct). The
Chunky task lives inside the server process, so this costs nothing — just re-launch
the watcher. Verify liveness with `ps -o pid,ppid,stat,etime,cmd -p <pid>` (look for
`Ss` = sleeping, not `Zs` = defunct).
