# Locating modpack configs & inspecting mod jars

## ATM11 data layout (homelab container `minecraft-atm11`)
- Data volume: `/home/ruben/homeserver/minecraft-atm11/data` (mapped to `/data` in the container; AUTO_CURSEFORGE).
  Reveal mounts with: `docker inspect minecraft-atm11 --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{"\n"}}{{end}}'`
- `config/` — one file per mod: `<modid>-server.toml`, `<modid>-common.toml`, `<modid>-client.toml`, plus `.json`/`.json5`. ~247 files.
- `mods/` — 260+ jars. `defaultconfigs/` — template configs applied on first run. `kubejs/server_scripts/` — pack scripts (per-mod tweaks, unification, etc.).
- World: `~/atm11-world` (bind-mounted to `/data/world`).

## Workflow: "which config controls/disables X?"
1. Identify the owning mod. Name-match the jar in `mods/`, or grep lang/class files (see scripts below).
2. Open `config/<modid>-server.toml` (server-side settings) or `-common.toml` (shared). NeoForge configs carry inline comments documenting every option's meaning, default, and range.
3. Server configs are read at startup → `docker restart minecraft-atm11` after editing. `-common`/`-server` vs `-client` distinction: server behavior lives in `-server`.

## Pylons — Infusion Pylon effect whitelist (worked example)
- File: `config/pylons-server.toml`, section `[infusion_pylon]`.
- `infusionAllowedEffects = ["minecraft"]` is a **whitelist**: only the `minecraft` (vanilla) namespace is allowed, so ANY modded effect (e.g. creative flight) is rejected. Inline comment confirms: an empty list `[]` = allow everything except the deny list.
- `infusionDeniedEffects = [...]` **overrides** the allow-list (always denied). A `pylons:infusion_banned` tag can also ban effects independently of config.
- Fix options: add the effect ID (`"reliquary:flight"`), add the whole namespace (`"reliquary"`), or empty the list (`[]`).
- Creative-flight potion-effect sources in ATM11: `reliquary:flight` (Reliquary — desc "Provides creative flight while active"), `arsmagicalegacy:flight` (Ars Magica Legacy). `occultism:bat_flight` is familiar-based, not a potion. ApothicAttributes' `creative_flight` is an **attribute** (`.desc` key), not a mob effect — no potion.

## Inspecting mod jars (no `unzip` on the box)
`unzip` is NOT installed on the homelab — use Python `zipfile` (stdlib). Note `unzip -p jar '*.json'` also fails to match *nested* lang paths (`assets/<modid>/lang/*.json`), so even if `unzip` existed, use `zipfile` and filter by `info.filename`.

Lang-key conventions:
- `effect.<modid>.<name>` → effect ID `<modid>:<name>` (what goes in Pylons `infusionAllowedEffects`)
- `item.<modid>.<name>` → item ID
- attribute keys end in `.desc` (e.g. `apothic_attributes:creative_flight.desc`) — these are attributes, not potion effects.

### Script A — which jars mention a term in lang/config files
```python
import zipfile, glob, os
mods = "/home/ruben/homeserver/minecraft-atm11/data/mods"
terms = ["creative flight", "flight"]  # lowercase
for path in sorted(glob.glob(os.path.join(mods, "*.jar"))):
    name = os.path.basename(path)
    try:
        z = zipfile.ZipFile(path)
    except Exception:
        continue
    for info in z.infolist():
        if info.is_dir() or not info.filename.endswith((".json", ".toml", ".cfg", ".snbt")):
            continue
        if "lang" not in info.filename and "config" not in info.filename:
            continue
        data = z.read(info).decode("utf-8", "ignore").lower()
        for t in terms:
            if t in data:
                print(name, "::", info.filename)
                break
```

### Script B — which jars register a string in compiled classes (effect/attribute IDs)
```python
import zipfile, glob, os
mods = "/home/ruben/homeserver/minecraft-atm11/data/mods"
terms = [b"creative_flight", b"creativeFlight", b"CreativeFlight"]
for path in sorted(glob.glob(os.path.join(mods, "*.jar"))):
    name = os.path.basename(path)
    try:
        z = zipfile.ZipFile(path)
    except Exception:
        continue
    for info in z.infolist():
        if info.is_dir() or not info.filename.endswith(".class"):
            continue
        data = z.read(info)
        for t in terms:
            if t in data:
                print(name, "::", info.filename)  # e.g. reliquary/potions/FlightEffect.class
                break
```
Script B reveals the actual registered class (e.g. `reliquary/potions/FlightEffect.class` = a real MobEffect) — confirms whether something is a potion effect vs an attribute/augment.
