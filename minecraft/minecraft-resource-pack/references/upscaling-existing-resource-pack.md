# Upscaling an existing resource pack (mode B)

Faithful-variant of a *published* resource pack (not mod jars). Worked example: AE2 Blackout (16x dark-mode AE2 retexture) → `ae2-blackout-32x.zip`.

## Getting the source pack

Two APIs, one needs a key:

- **Modrinth** — open, no key. Version list + download URL:
  ```bash
  curl -s "https://api.modrinth.com/v2/project/<slug>/version?game_versions=%5B%221.21.1%22%5D&loaders=%5B%22minecraft%22%5D"
  # → d[0]['files'][0]['url']
  ```
- **CurseForge** — needs an API key. The key already lives inside the running itzg
  container at `/run/secrets/cf_api_key` (from `CF_API_KEY_FILE`). Query the API
  *without* reading the secret yourself:
  ```bash
  docker exec minecraft-atm10aero sh -c 'curl -s -H "x-api-key: $(cat /run/secrets/cf_api_key)" \
    "https://api.curseforge.com/v1/mods/search?gameId=432&searchFilter=ae2-blackout&classId=12"'
  ```
  `classId`: 6 = mod, 12 = resource pack, 4471 = modpack. Then fetch file list by project id:
  `.../v1/mods/<id>/files?gameVersion=1.21.1`, then `.../v1/mods/<id>/files/<fileId>`
  for the `downloadUrl` (an `edge.forgecdn.net` URL — download that directly with plain curl).

## Build recipe (mode B)

Input is a resource-pack zip laid out as `assets/<ns>/textures/...`. Rules:

1. Upscale 2x only textures with `width == 16` (this catches `16x16`, `16x32`, `16x80`,
   `16x352` etc. — tall animated strips must grow with the block faces they overlay).
2. Copy everything else verbatim: large GUI/atlas textures (256x256, 512x512),
   `.png.mcmeta` (animation frames/frametime stay valid at 2x because frame size is
   proportional), block/item model JSONs, and `pack.png`.
3. Rewrite only `pack.mcmeta` (keep `pack_format` 34 for 1.21.1, new description).
4. Layer it **above** the main modpack 32x pack so its namespace wins.

Full working script: `build_blackout.py` in `/home/ruben/faithful-pack/` (uses
`superxbr_numba.py`). AE2 Blackout source: CF project `1060372`, latest 1.21.1 file
`AE2Blackout-V1.2.8.zip` (file id 8393438).

## Verification

- Spot-check sizes: a 16x16 → 32x32, a 16x80 → 32x160, a 512 GUI → unchanged 512.
- Visual before/after: build a 3-way contact sheet (orig NN / Scale2x / xBR) with
  `Image.resize(..., Image.NEAREST)` so all three are at equal pixel scale, then read it
  with vision to judge scaler quality on *that* pack's art style.
