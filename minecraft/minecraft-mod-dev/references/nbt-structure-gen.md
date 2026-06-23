# NBT Structure Template Generation

When you need to create structure `.nbt` files for Minecraft worldgen without
building them in-game, use a Python script to write the GZip-compressed NBT
binary format.

## Minimal script

```python
#!/usr/bin/env python3
"""Generate a simple structure NBT for Minecraft 1.21.x."""
import gzip, struct, os

def write_str(buf, s):
    enc = s.encode('utf-8')
    buf += struct.pack('>H', len(enc))
    buf += enc
    return buf

def tag_byte(buf, name, value):
    buf.append(1); buf = write_str(buf, name); buf.append(value & 0xFF); return buf

def tag_int(buf, name, value):
    buf.append(3); buf = write_str(buf, name); buf += struct.pack('>i', value); return buf

def tag_string(buf, name, value):
    buf.append(8); buf = write_str(buf, name); buf = write_str(buf, value); return buf

def tag_compound_open(buf, name):
    buf.append(10); buf = write_str(buf, name); return buf

def tag_end(buf):
    buf.append(0); return buf

def tag_list_open(buf, name, elem_type, count):
    buf.append(9); buf = write_str(buf, name); buf.append(elem_type)
    buf += struct.pack('>i', count); return buf

# ── Build ──
buf = bytearray()
buf = tag_compound_open(buf, "")
buf = tag_int(buf, "DataVersion", 3953)

# Size: [width, height, depth]
buf = tag_list_open(buf, "size", 3, 3)
buf += struct.pack('>i', 3); buf += struct.pack('>i', 5); buf += struct.pack('>i', 3)

# Palette: [{Name: "minecraft:obsidian"}]
buf = tag_list_open(buf, "palette", 10, 1)
buf = tag_compound_open(buf, ""); buf = tag_string(buf, "Name", "minecraft:obsidian")
buf = tag_end(buf)

# Blocks: for x,y,z in range, write {state: 0, pos: [x,y,z]}
buf = tag_list_open(buf, "blocks", 10, 45)
for x in range(3):
    for z in range(3):
        for y in range(5):
            buf = tag_compound_open(buf, "")
            buf = tag_int(buf, "state", 0)
            buf = tag_list_open(buf, "pos", 3, 3)
            buf += struct.pack('>i', x) + struct.pack('>i', y) + struct.pack('>i', z)
            buf = tag_end(buf)

# Entities: empty
buf = tag_list_open(buf, "entities", 10, 0)
buf = tag_end(buf)  # close root

with gzip.open("output.nbt", 'wb') as f:
    f.write(bytes(buf))
```

## Key NBT format notes

- **TAG_Compound**: byte 10, then name, then children, then TAG_End (0)
- **TAG_List**: byte 9, then name, then element type byte, then int count, then elements
- Elements inside TAG_List have **no type byte and no name** — just the payload
- For TAG_Compound elements in a list: open compound, write children, end compound
- Structure blocks use state index (0 = first palette entry), not raw block IDs
- Structure files MUST be GZip-compressed (.nbt extension, GZip wrapper)

## Structure datapack chain

To make a structure generate in-world, you need 4-5 files:
1. `data/<ns>/structure/<name>.nbt` — the NBT template
2. `data/<ns>/worldgen/template_pool/<name>_pool.json` — references the NBT
3. `data/<ns>/worldgen/structure/<name>.json` — jigsaw structure config
4. `data/<ns>/worldgen/structure_set/<name>s.json` — placement config (spacing/separation)
5. `data/<ns>/neoforge/biome_modifier/add_<name>s.json` — biome modifier

Use `"type": "minecraft:jigsaw"` for structures that don't need a custom StructureType.
