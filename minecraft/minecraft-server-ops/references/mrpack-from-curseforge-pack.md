# Building a Modrinth .mrpack from a CurseForge-only pack

ATM10 Aeronautics is on CurseForge but NOT on Modrinth. To hand Modrinth-app users an importable
pack, build a **self-contained `.mrpack`** (every mod bundled, no download resolution needed).

## Format

`modrinth.index.json` at zip root:
```json
{
  "formatVersion": 1, "game": "minecraft", "versionId": "0.6.1-stock",
  "name": "ATM10 Aeronautics (Oathless)",
  "summary": "All the Mods 10 Aeronautics 0.6.1 — stock",
  "files": [],
  "dependencies": {"minecraft": "1.21.1", "neoforge": "21.1.250"}
}
```
Everything else goes under `overrides/` — mirror the server `data/` dir (`mods/`, `config/`,
`defaultconfigs/`, `kubejs/`, `resourcepacks/`). The launcher copies `overrides/` verbatim into the
instance, so bundling jars there needs NO Modrinth project/file ID lookup. `files[]` stays empty
because nothing is downloaded from Modrinth.

Result ≈ 900 MB (jars are already compressed). This is the *importable* equivalent of the flat
full zip — prefer it over shipping a bare zip.

## Launcher-format coverage (why two files exist)

| Format | Imported by |
|---|---|
| CF `.zip` (manifest.json + modlist.html + overrides) | CurseForge app, PrismLauncher |
| `.mrpack` | Modrinth app, PrismLauncher |

PrismLauncher imports **both**; no single format covers all three launchers. CF-only packs (like
ATM10) can't be a native `.mrpack` reference, so you must bundle mods in `overrides/`.

When the pack is STOCK (no manual mods), skip custom files entirely — tell players to install the
official pack at the exact pinned version from CurseForge/Modrinth directly.

## Build script pattern

Use Python `zipfile` (the `zip` CLI is often absent on the box):
```python
import zipfile, os, json
SRC = '/home/ruben/homeserver/minecraft-atm10aero/data'
index = {"formatVersion":1,"game":"minecraft","versionId":"0.6.1","name":"...","files":[],
         "dependencies":{"minecraft":"1.21.1","neoforge":"21.1.250"}}
with zipfile.ZipFile('out.mrpack','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    z.writestr('modrinth.index.json', json.dumps(index, indent=2))
    for d in ['mods','config','defaultconfigs','kubejs','resourcepacks']:
        for dp,_,fn in os.walk(os.path.join(SRC,d)):
            for f in fn:
                p = os.path.join(dp,f)
                z.write(p, 'overrides/'+os.path.relpath(p,SRC))
```
Always assert the resulting jar count + absence of removed mods after a rebuild (e.g. after
removing Plasmo Voice, assert no `plasmo` entries remain).

## Updating the CF zip in place (swap one bundled jar)

When only one mod changes (e.g. DH 3.2.0 → 3.3.3), don't rebuild from scratch — stream the old
zip, drop the old jar entry, write the new jar into `overrides/mods/`. But first check whether the
mod is even bundled: DH is client-optional, so it lives in the `.mrpack` (server mirror) but NOT in
the CF zip (which carries only client-REQUIRED extras). Only swap in files that were actually there.
