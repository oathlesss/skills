# Pregen + Distant Horizons — verified versions & commands (1.21.1 NeoForge)

Verified 2026-09 against the running ATM10 Aeronautics instance (1.21.1, NeoForge 21.1.248).

## Exact files (CurseForge, MC 1.21.1, NeoForge)

| Mod | File | CF file ID | Size | Notes |
|---|---|---|---|---|
| Chunky | `Chunky-NeoForge-1.4.23.jar` | 6383261 | 340 KB | release (project `chunky-pregenerator-forge` id 485681) |
| C2ME | `c2me-neoforge-mc1.21.1-0.4.0-alpha.0.120.jar` | 8646869 | 3.7 MB | alpha — normal for 1.21.1 (project `c2me` id 533097) |
| Distant Horizons | `DistantHorizons-3.2.0-b-1.21.1-fabric-neoforge.jar` | 8389148 | 30 MB | beta (project id 508933) |

> C2ME and DH have NO stable release on 1.21.1 — alpha/beta is expected, not a red flag.
> DH 3.x is the current line; 2.3.0-b also exists for 1.21.1 if 3.x misbehaves.

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
