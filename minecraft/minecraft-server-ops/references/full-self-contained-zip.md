# Building a FULL self-contained modpack zip (all jars bundled)

Distinct from the manifest-based PrismLauncher pack (which references CurseForge
downloads and is ~105MB): this is a flat zip containing every mod jar + config +
kubejs, so a friend can extract into a NeoForge instance and run with NO CurseForge
resolution. Result ≈ 1GB.

## When to use which artifact

- PrismLauncher one-click import → manifest pack (`shareable-modpack.md`)
- "Zip the ENTIRE modpack" → full self-contained flat zip (this doc)
- "Just the mods I added manually" → `extras.zip` (client-required jars only)

## Recipe

1. Server data dir: `/home/ruben/homeserver/minecraft-atm10aero/data`.
2. Include ONLY these dirs (exclude `world/`, `simplebackups/`, `logs/`,
   `libraries/`, `libraries-integratedscripting/`, `dynamic-data-pack-cache/`,
   `cache/`, `journeymap/` — server state or launcher-resolved):
   - `mods/` (all jars)
   - `config/`
   - `defaultconfigs/`
   - `kubejs/`
   - `resourcepacks/`
3. Build with `python3 zipfile` — the `zip` binary is NOT installed on this box
   (don't try `apt install zip` for a one-off):

```python
import zipfile, os
SRC = '/home/ruben/homeserver/minecraft-atm10aero/data'
OUT = 'ATM10-Aeronautics-Oathless-0.6.1-full.zip'
dirs = ['mods', 'config', 'defaultconfigs', 'kubejs', 'resourcepacks']
with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for d in dirs:
        for dp, dn, fn in os.walk(os.path.join(SRC, d)):
            for f in fn:
                full = os.path.join(dp, f)
                z.write(full, os.path.relpath(full, SRC))
```

4. Verify: jar count + total files + size (expect ~407 jars, ~4,900 files, ~950MB).

## Sizes observed (0.6.1)

- `mods/` 968MB (407 jars), `config/` 63MB, `kubejs/` 103MB, `resourcepacks/` 2.6MB
- Final zip ≈ 958MB — jars are already deflate-compressed, so zipping saves ~nothing.

## Voice chat check

ATM10 Aeronautics ships NO voice chat. The only grep hit for
`voice|chat|plasmo|audio|sound|talk` is `NoChatReports` — the OPPOSITE of voice
chat (it strips Mojang's chat-reporting telemetry). To add voice: Simple Voice Chat
(server + client mod) + open UDP port 24454 on the router.

## Pitfalls

- Flat zip is NOT a PrismLauncher import format — it's extract-into-a-NeoForge-1.21.1
  instance. Don't tell friends to "import" it; that's the manifest pack's job.
- `README.md` naming collisions when building multiple pack variants in the same dir —
  keep a distinct `README-full.md` (or per-variant name) and don't clobber the
  manifest pack's README.
