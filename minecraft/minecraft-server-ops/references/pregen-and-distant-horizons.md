# Pregen + Distant Horizons — verified versions & commands (1.21.1 NeoForge)

Verified 2026-09 against the running ATM10 Aeronautics instance (1.21.1, NeoForge 21.1.248).

## Exact files (CurseForge, MC 1.21.1, NeoForge)

| Mod | File | CF file ID | Size | Notes |
|---|---|---|---|---|
| Chunky | `Chunky-NeoForge-1.4.23.jar` | 6383261 | 340 KB | release (project `chunky-pregenerator-forge` id 485681) |
| C2ME | `c2me-neoforge-mc1.21.1-0.4.0-alpha.0.120.jar` | 8646869 | 3.7 MB | alpha — normal for 1.21.1 (project `c2me` id 533097) |
| Distant Horizons | `DistantHorizons-3.2.0-b-1.21.1-fabric-neoforge.jar` | 8389148 | 30 MB | beta (project id 508933) |

> C2ME has NO stable release on 1.21.1 — alpha is expected, not a red flag.
> Measured on a 281-mod pack (i5-9500T): Chunky single-threaded 4.6 chunks/s → ~47 chunks/s with
> C2ME (~10x), collapsing a 2000-block-radius pregen from ~3h50m to ~20min.
> **C2ME conflicts with `betterchunkloading`** (someaddon) — exclude it via `CF_EXCLUDE_MODS` before
> adding C2ME (FML warns the combo "causes the world to save infinitely").
> **DH: the 3.3.x line went STABLE in Sept 2026** (3.3.0 → 3.3.3, all `release`, not `-b-`).
> `3.3.3-1.21.1` (2026-09-29) is current. The older `3.2.0-b` is a *beta* from July 2026 —
> keep an eye on which build is actually installed, because DH's network protocol changes
> between versions (see the crash section below).

### C2ME on MC 26.1.2 (NeoForge)

C2ME now ships 26.1.2 builds (the 26.x line is current). Modrinth slug is **`c2me-neoforge`**
(the bare `c2me` slug 404s — that's the Fabric/legacy name). Newest 26.1.2 build:
`c2me-neoforge-mc26.1.2-0.4.0-alpha.0.100.jar` (2026-10-03, sha1 `a035b1b5...`, ~3.7 MB).
Measured on evo2-tech (6c/6t i5-9500T): ~11 → ~31 chunks/s (~3x), CPU 274%→595% (all 6 cores
saturated). The ~10x figure above was a bigger pack/CPU; on 6 physical cores C2ME's ideal ceiling
is ~5-6x, and heavy Tectonic/Lithostitched density functions bound the real gain to ~3x here.
DH 3.3.3 auto-detects C2ME at boot and coordinates chunk access — no config needed. C2ME is
server-side only (players install nothing); it also speeds chunk loading during normal play, so
leave it in after pregen.

### Chunky task management (1.5.x)

- `chunky cancel` is **two-step**: first call warns "Cancelled tasks cannot be continued... type
  '/chunky confirm'", then `chunky confirm` actually cancels (`confirm` isn't in `chunky help`).
- Expand a running task's radius: cancel+confirm → re-set `center`/`radius`/`world` → `chunky start`
  (old chunks kept + skipped via `forceLoadExistingChunks: false`).
- After a restart with `continueOnRestart: false`, a saved task makes `chunky start` REFUSE
  ("A task was already started for this world... type '/chunky confirm'") while `chunky progress`
  shows "No tasks running". Resume with `chunky continue`. The saved `tasks/<world>/<dim>.properties`
  recorded the pre-restart radius correctly in this case — still cross-check it (it goes stale after
  an OOM crash, per the main SKILL.md).
- Combined Chunky→DH watcher that chains both and notifies on completion:
  `scripts/pregen-dh-watch.sh` (supersedes `scripts/chunky-watch.sh` when DH LODs should follow).

## ⚠️ Client/server DH version mismatch → "network protocol error" on join

**Symptom (client):** player crashes joining with a generic "network protocol error" /
"internal exception" — the vanilla MC disconnection message.

**Root cause:** the client's Distant Horizons version is DIFFERENT from the server's. DH's
network protocol (`distant_horizons:msg` channel) changes between releases, so the handshake
fails and the server drops the connection.

**Diagnostic signature (server `latest.log`), in this order:**

```
[ERROR] NetworkRegistry: Failed to process a synchronized task of the payload: distant_horizons:msg
java.util.concurrent.CompletionException: java.lang.IllegalArgumentException: found 1 argument
  placeholders, but provided 0 for pattern `Message: [IncompatibleMessageInternalEvent{}]`
...
io.netty.channel.unix.Errors$NativeIoException: recvAddress(..) failed: Connection reset by peer
[INFO] <player> lost connection: Disconnected
```

The tell is `IncompatibleMessageInternalEvent` — DH explicitly rejecting the client because the
versions don't line up. (Note the weird log4j error message about "argument placeholders" is a
DH bug in how it logs the incompatibility, not the actual problem — ignore the message text,
the event name is the signal.)

**Fix:** make the server jar EXACTLY match what clients run. `ls data/mods | grep -i distanthorizons`
to see the server's build, then swap the jar + restart + rebuild the shareable pack. If you upgraded
the client to 3.3.3 (or the user did), upgrade the SERVER to 3.3.3 too — every other player on the
old client will then hit the same crash, so the pack must ship the new version.

**Generalize:** this applies to ANY client+server mod with a network channel (voice chat, DH, some
API mods). "network protocol error" on join in a modded pack = check for a client/server version
mismatch first, before anything else. Grep `latest.log` for the mod's payload channel to identify
which mod.

**DH config note:** 3.3.3 bumps config version 4 → 5 and CLEARS the old DH config (client render
settings reset to default; trivial to re-tweak). It also adds "only disable DH worldgen when Chunky
worldgen is active" — a coordination fix that matters when BOTH Chunky and DH run server-side.

## Order

Real chunks (Chunky) FIRST, then DH LODs. DH builds LODs from existing chunks instead
of doing its own full worldgen — running DH first duplicates work and doubles wall time.

## Chunky (real chunk pregen)

Install jar, restart server, then via `docker exec minecraft-atm10aero rcon-cli "..."`:

```
/chunky center 0 0
/chunky radius 2000                # BLOCKS. 2000 = ~125 chunk radius = ~200k chunks
/chunky world minecraft:overworld  # ATM10 Aeronautics has many dims — do overworld only first
/chunky start
```

Monitor: `/chunky progress`, `/chunky pause`, `/chunky cancel`.

> **Resume vs start:** if a previous task was interrupted (e.g. a restart to add C2ME),
> `/chunky start` returns `A task was already started for this world. To continue running it,
> type '/chunky continue'`. Use `/chunky continue` to resume — it skips already-generated chunks.

> **`chunky config threads N` does NOT exist in 1.4.x** (returns "Incorrect argument for command"). Parallelism comes from C2ME, not a Chunky setting — don't waste time hunting for a thread knob.

**Radius guidance for the i5-9500T:** 2000–3000 blocks is plenty for a few players and
runs overnight with C2ME. 5000+ (multi-day) only if players will fly far in one direction.
Expect ~200k chunks to take MANY HOURS on a T-series chip even with C2ME.

## Distant Horizons LOD pregen (after Chunky)

```
dh config common.threadPreset I_PAID_FOR_THE_WHOLE_CPU   # works — valid key
dh pregen start minecraft:overworld 0 0 256              # radius in CHUNKS
```

Monitor: `/dh pregen status`, `/dh pregen stop`.

### ⚠️ Generation mode: leave it at `FEATURES` (do NOT set INTERNAL_SERVER)

The generation-mode key is **`distantGeneratorMode`** in
`data/config/DistantHorizons.toml` — NOT `common.generationMode` (that key doesn't
exist; the CLI rejects it). The default value is **`FEATURES`**, and that is what you
want: it imports existing chunks (your Chunky pregen) and synthesizes a lightweight
surface beyond them, WITHOUT saving real chunks.

`INTERNAL_SERVER` (the "Full — Generate Chunks" mode) **saves real chunks to region
files** — it duplicates Chunky's work and costs disk + CPU. Only use it if you want DH
to ALSO do the real-chunk pregen instead of Chunky.

> Earlier drafts of this doc recommended `common.generationMode INTERNAL_SERVER`; that
> was wrong on both counts (bad key, and bad value for a server that already ran Chunky).

### CLI quirks in DH 3.x

- `dh help`, `dh config`, and `dh pregen` **with no args throw "Incorrect argument for
  command" / "Unknown or incomplete command"** — the parser rejects bare subcommands.
  Don't fight it; read `DistantHorizons.toml` directly instead.
- `dh config common.threadPreset I_PAID_FOR_THE_WHOLE_CPU` **does** work and logs
  `Changed the value of [common.threadPreset]`. The actual thread count lives at
  `[common.multiThreading] numberOfThreads` (defaults to core count).
- A `WARN ... Unknown Chunk Generator detected` for `ae2:spatial_storage` is harmless
  (tiny void dimension; DH won't render distant terrain there, nothing breaks).

LODs land in `Distant_Horizons_server_data/` under `/data`. Clients with DH fetch them
automatically. Run per-dimension only for dims the players actually visit (Nether, End,
Twilight Forest, etc.).

## Client-side + shader caveat

Players add the SAME DH jar to their client `mods/`. **ATM10 ships Iris + Sodium** — DH
only works with Iris when using a DH-compatible shader (see DH mod page's shader list).
This is the #1 source of "DH won't render / crashes" on ATM10. Non-shader DH is safe.

## Decision rule (repeated for emphasis)

- "Can my server handle this pack?" → assess single-core CPU + worldgen, then CHUNKY pregen.
- "I want distant terrain visuals" → DH on the CLIENT, pregen LODs per-client.
- Only put DH server-side if you specifically want shared LODs AND have CPU/RAM to spare.

## DH 3.3.3 CLI facts + auto-chaining Chunky → DH (26.1.2 / evo2-tech)

- `dh help` prints the full subcommand shapes. Key ones: `dh pregen start <dimension> <x> <z> <chunkRadius>` (radius in CHUNKS), `dh pregen status`, `dh pregen stop`.
- `/dh pregen status` prints exactly **`Pregen is not running`** when idle. Use that string as the idle/completion sentinel — but guard it with the same container-`StartedAt` comparison as Chunky, because a clean finish AND a crash-restart both land back on "not running" (identical ambiguity to Chunky's "No tasks running").
- **evo2-tech (MC 26.1.2) specifics:** DH jar `DistantHorizons-3.3.3-26.1.2-fabric-neoforge.jar`; Chunky `Chunky-NeoForge-1.5.4.jar` is bundled (NO C2ME) and pregens at ~16 cps on the i5-9500T (observed 765 chunks / 0.54% at 16.2 cps, ETA ~2.4 h for radius 3000 blocks / 141k chunks). Server mods dir also ships ferritecore + modernfix + servercore (perf stack present).
- **Auto-chain:** `scripts/pregen-dh-watch.sh` polls Chunky to 100%, then starts + monitors DH LOD pregen in one background job. Exit 0 = both done; exit 1 = lost task or DH failed to start.
