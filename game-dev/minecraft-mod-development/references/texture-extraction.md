# Extracting Textures from Old Mod JARs

When a classic mod's textures are needed, the simplest path is extracting them directly from the old JAR file using Python's `zipfile` module (no need for `unzip`).

## One-shot extraction with remapping

```python
import zipfile, os

z = zipfile.ZipFile('OldMod-1.7.10-4.2.3.5.jar')
out_base = '/path/to/mod/src/main/resources'

count = 0
for f in z.namelist():
    if not f.startswith('assets/oldmod/textures/'): continue
    if f.endswith('/'): continue

    # Remap: assets/oldmod/textures/... -> assets/newmod/textures/...
    rel = f[len('assets/oldmod/textures/'):]
    out_path = os.path.join(out_base, 'assets/newmod/textures', rel)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with z.open(f) as src, open(out_path, 'wb') as dst:
        dst.write(src.read())
    count += 1

print(f'Extracted {count} textures')
```

## Inventory check

```python
textures = [f for f in z.namelist() if 'textures' in f.lower() and f.endswith('.png')]
print(f'Total textures: {len(textures)}')
for t in sorted(textures)[:20]:
    print(f'  {t} ({z.getinfo(t).file_size} bytes)')
```

## Path conventions

Old Forge mods (1.7.10, 1.12.2) use:
- `assets/<modid>/textures/blocks/` (plural)
- `assets/<modid>/textures/items/` (plural)

Modern Minecraft (1.21.x) uses:
- `assets/<modid>/textures/block/` (singular)
- `assets/<modid>/textures/item/` (singular)

Rename the extracted directories after extraction, or handle the mapping in the Python script.

## Missing textures

If the old mod doesn't have every texture you need, generate placeholders:

```bash
for name in missing1 missing2 missing3; do
    cp _unknown.png ${name}.png
done
```

## TC4 specifics

Thaumcraft 4 (1.7.10) has ~940 PNG textures across:
- `aspects/` — 48 aspect icons (50 with UI placeholders)
- `blocks/` — 252 block textures
- `items/` — 268 item textures
- `gui/` — 23 GUI textures (Thaumonomicon pages, workbench, research table)
- `models/` — 165 entity/Armor textures (golems, wisps, armor)
- `foci/` — 21 wand focus icons
- `misc/` — 66 particle/environment textures

TC4 jar: Project 223628 on CurseForge, file ID 2247952 (Thaumcraft-1.7.10-4.2.3.5).
