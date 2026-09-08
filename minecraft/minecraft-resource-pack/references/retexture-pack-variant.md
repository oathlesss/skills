# Faithful variant of an existing retexture pack

When the user runs a *retexture* resource pack (dark mode, themed overhaul — e.g. **AE2
Blackout** / **AE2 Dark Mode**) at 16x and wants it to sit on a Faithful 32x stack, build a
"Faithful variant": upscale the retexture pack's own textures 2x rather than pulling from mod jars.

## CurseForge fetch (retexture packs usually live on CurseForge, not Modrinth)

CurseForge API v1 requires `x-api-key`; Modrinth is keyless. In this environment the CF key is
available on the running Minecraft container (do NOT print it — pipe it straight into the header):

```bash
# search texture packs (gameId 432 = Minecraft, classId 12 = resource/texture pack)
docker exec minecraft-atm10aero sh -c 'curl -s -H "x-api-key: $(cat /run/secrets/cf_api_key)" \
  "https://api.curseforge.com/v1/mods/search?gameId=432&searchFilter=ae2-blackout&classId=12"' \
  | python3 -c "import sys,json; [print(m['id'],'|',m['slug'],'|',m['name']) for m in json.load(sys.stdin)['data']]"

# list files for a 1.21.1 target
docker exec minecraft-atm10aero sh -c 'curl -s -H "x-api-key: $(cat /run/secrets/cf_api_key)" \
  "https://api.curseforge.com/v1/mods/<MOD_ID>/files?gameVersion=1.21.1&pageSize=10"' \
  | python3 -c "import sys,json; [print(f['id'],'|',f['fileName']) for f in json.load(sys.stdin)['data']]"

# download URL (the actual CDN edge URL, no key needed once you have it)
docker exec minecraft-atm10aero sh -c 'curl -s -H "x-api-key: $(cat /run/secrets/cf_api_key)" \
  "https://api.curseforge.com/v1/mods/<MOD_ID>/files/<FILE_ID>"' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['downloadUrl'])"
```

AE2 Blackout = project id `1060372`; AE2 Blackout Extended = `1462913`. The returned
`downloadUrl` is an `edge.forgecdn.net/files/XXXX/YYY/name.zip` URL.

## Build recipe

Reference working script: `/home/ruben/faithful-pack/build_blackout.py`.

1. **Classify textures by size first** (PIL), don't blindly upscale. A 16x retexture pack has a
   few dozen sizes: the bulk are 16x16 (blocks/items), the rest are GUIs/atlases (256x256,
   512x512, 128x128, 64x64) and tall animated strips (16x80, 16x32, 16x352…).
2. **Upscale rule = `width == 16`.** This catches 16x16 *and* the tall animated strips
   (16x80 → 32x160). Do NOT use `max(w,h) <= 32` — it leaves 16x80 untouched.
3. **Scale2x vs xBR:** Super-xBR (`superxbr_numba.py`, numba-jitted, C-speed) for packs with
   fine geometry (AE2 circuitry, thin lines, grid machines) — visually much closer to
   hand-painted Faithful. Scale2x is the fallback for organic shapes. Build a 3-way contact
   sheet (orig NN / Scale2x / xBR) and inspect with `vision_analyze` before shipping.
4. **Copy verbatim:** every `*.png.mcmeta` (animated frames) AND `models/**/*.json` (block/item
   model overrides) — retexture packs ship these and they must not be dropped.
5. **Leave GUIs/atlases untouched** — 256x256 etc. are already high-res; upscaling bloats the
   pack and looks wrong.
6. **Rewrite `pack.mcmeta`** (keep `pack_format` = 34 for 1.21.1, new description); keep `pack.png`.

## Layer order (top → bottom in-game)

1. **<Retexture> 32x variant** (top — its dark/override namespace must win)
2. **Modpack 32x** (auto-upscaled mod textures)
3. **Faithful 32x** (vanilla base)

## Expectation setting

A retexture pack's source is 16x, so its "32x" variant is upscaled pixels, NOT hand-painted
Faithful art (no bevels/gradients). Say so — offer the hand-painted alternative if one exists.
